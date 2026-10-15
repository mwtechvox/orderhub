import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from django.db import close_old_connections, connection, connections

from apps.inbox.models import Message
from apps.inbox.services import create_outbound
from apps.inbox.tasks import send_meta_message
from apps.social.models import (
    Comment,
    CommentAutomationRule,
    CommentPrivateReplyAttempt,
    CommentReplyAttempt,
    Post,
)
from apps.social.services import reply, run_post_publication, schedule_comment_automation

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        connection.vendor != "postgresql", reason="Real PostgreSQL row locks required"
    ),
]


def test_competing_idempotency_requests_create_one_message(tenant, conversation):
    key = uuid.uuid4()

    def submit():
        close_old_connections()
        try:
            message, _ = create_outbound(tenant[0], conversation.pk, "hi", key)
            return message.pk
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(lambda _: submit(), range(2)))
    assert ids[0] == ids[1]
    assert Message.objects.filter(company=tenant[0]).count() == 1


def test_competing_workers_send_once(tenant, conversation):
    message, _ = create_outbound(tenant[0], conversation.pk, "hi", uuid.uuid4())

    def send():
        close_old_connections()
        try:
            send_meta_message(str(tenant[0].pk), str(message.pk))
        finally:
            connections.close_all()

    with patch("apps.inbox.tasks.account_client") as factory:
        factory.return_value.send_message.return_value = {"message_id": "concurrent-mid"}
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: send(), range(2)))
        assert factory.return_value.send_message.call_count == 1
    message.refresh_from_db()
    assert message.status == "SENT"


def test_competing_comment_reply_idempotency_sends_once(tenant, account, frozen_now):
    post = Post.objects.create(
        company=tenant[0],
        social_account=account,
        external_id="post",
        created_at_platform=frozen_now,
    )
    comment = Comment.objects.create(
        company=tenant[0],
        social_account=account,
        post=post,
        external_id="comment",
        created_at_platform=frozen_now,
    )
    key = uuid.uuid4()

    def submit():
        close_old_connections()
        try:
            return reply(comment, "hi", key)[0].pk
        finally:
            connections.close_all()

    with patch("apps.social.services.account_client") as factory:
        factory.return_value.reply_to_comment.return_value = {"id": "reply"}
        with ThreadPoolExecutor(max_workers=2) as pool:
            ids = list(pool.map(lambda _: submit(), range(2)))
    assert ids[0] == ids[1]
    factory.return_value.reply_to_comment.assert_called_once()
    attempt = CommentReplyAttempt.objects.get(company=tenant[0], pk=ids[0])
    assert attempt.status == "SENT"


def test_competing_comment_automation_workers_send_each_action_once(tenant, account, frozen_now):
    from apps.social.tasks import process_comment_automation

    post = Post.objects.create(
        company=tenant[0],
        social_account=account,
        external_id="automation-post",
        created_at_platform=frozen_now,
    )
    comment = Comment.objects.create(
        company=tenant[0],
        social_account=account,
        post=post,
        external_id="automation-comment",
        author_external_id="customer-psid",
        created_at_platform=frozen_now,
    )
    CommentAutomationRule.objects.create(
        company=tenant[0],
        social_account=account,
        is_enabled=True,
        public_reply_text="public",
        private_reply_text="private",
    )
    with patch("apps.social.services.enqueue"):
        schedule_comment_automation(comment)

    def process():
        close_old_connections()
        try:
            process_comment_automation(str(tenant[0].pk), str(comment.pk))
        finally:
            connections.close_all()

    with patch("apps.social.services.account_client") as factory:
        graph = factory.return_value
        graph.reply_to_comment.return_value = {"id": "auto-public"}
        graph.send_comment_private_reply.return_value = {"message_id": "auto-private"}
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: process(), range(2)))
    assert graph.reply_to_comment.call_count == 1
    assert graph.send_comment_private_reply.call_count == 1
    assert CommentReplyAttempt.objects.get(comment=comment).status == "SENT"
    assert CommentPrivateReplyAttempt.objects.get(comment=comment).status == "SENT"


def test_competing_inbound_messages_keep_newest_provider_time(conversation, frozen_now):
    from datetime import timedelta

    from apps.inbox.services import store_message

    conversation.last_inbound_at = None
    conversation.save(update_fields=["last_inbound_at"])
    times = [frozen_now - timedelta(hours=2), frozen_now - timedelta(hours=1)]

    def receive(timestamp):
        close_old_connections()
        try:
            store_message(
                conversation,
                {
                    "id": timestamp.isoformat(),
                    "from": {"id": "psid"},
                    "created_time": timestamp.isoformat(),
                },
                notify=True,
            )
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(receive, times))
    conversation.refresh_from_db()
    assert conversation.last_inbound_at == max(times)
    assert conversation.unread_count == 2


def test_competing_sync_workers_claim_one_run(account):
    from apps.meta.exceptions import MetaPermissionError
    from apps.meta.tasks import sync_account

    def sync():
        close_old_connections()
        try:
            sync_account(str(account.company_id), str(account.pk))
        finally:
            connections.close_all()

    with (
        patch("apps.social.services.sync_feed", side_effect=MetaPermissionError()) as feed,
        patch("apps.inbox.services.sync_conversations") as inbox,
        ThreadPoolExecutor(max_workers=2) as pool,
    ):
        list(pool.map(lambda _: sync(), range(2)))
    feed.assert_called_once()
    inbox.assert_called_once()
    account.refresh_from_db()
    assert account.status == "NEEDS_REAUTH" and account.sync_failures == 1


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("first_writer", ["delete", "sync", "edit"])
def test_comment_delete_serializes_with_competing_writer(
    account, frozen_now, existing, first_writer
):
    from concurrent.futures import TimeoutError
    from datetime import timedelta
    from threading import Event

    from django.db import transaction

    from apps.meta.services.webhooks import process_change
    from apps.social.models import Comment, Post
    from apps.social.services import upsert_comment

    post = Post.objects.create(
        company=account.company,
        social_account=account,
        external_id="post",
        created_at_platform=frozen_now,
    )
    if existing:
        upsert_comment(post, {"id": "comment", "message": "original"})
    held = Event()
    release = Event()
    second_entered = Event()

    def write(kind):
        if kind == "sync":
            upsert_comment(post, {"id": "comment", "message": "stale snapshot"})
        else:
            when = frozen_now if kind == "delete" else frozen_now - timedelta(minutes=1)
            process_change(
                account,
                {
                    "field": "feed",
                    "value": {
                        "item": "comment",
                        "verb": "remove" if kind == "delete" else "edited",
                        "comment_id": "comment",
                        "post_id": "post",
                        "message": "old edit",
                    },
                },
                when.timestamp() * 1000,
            )

    def first():
        close_old_connections()
        try:
            with transaction.atomic():
                write(first_writer)
                held.set()
                assert release.wait(10), "Test did not release the first transaction"
        finally:
            connections.close_all()

    def second():
        close_old_connections()
        try:
            second_entered.set()
            write("sync" if first_writer == "delete" else "delete")
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first_result = pool.submit(first)
        try:
            assert held.wait(10), "First writer failed before holding its lock"
            second_result = pool.submit(second)
            assert second_entered.wait(10)
            # The competing writer must wait for the open row/unique-key transaction.
            with pytest.raises(TimeoutError):
                second_result.result(timeout=0.1)
        finally:
            release.set()
        first_result.result(timeout=10)
        second_result.result(timeout=10)
    comment = Comment.objects.get(
        company=account.company, social_account=account, external_id="comment"
    )
    assert comment.is_deleted and comment.message == "" and not comment.can_reply
    assert comment.last_event_at == frozen_now
    assert Comment.objects.filter(company=account.company).count() == 1


def test_competing_post_publish_workers_send_once(tenant, account, frozen_now):
    post = Post.objects.create(
        company=tenant[0],
        social_account=account,
        external_id="",
        origin=Post.Origin.ORDERHUB,
        status=Post.Status.SCHEDULED,
        message="publish once",
        created_at_platform=frozen_now,
        scheduled_at=frozen_now,
    )

    def publish():
        close_old_connections()
        try:
            run_post_publication(str(post.company_id), str(post.pk))
        finally:
            connections.close_all()

    with patch("apps.social.services.account_client") as factory:
        factory.return_value.create_page_post.return_value = {"id": "page_post"}
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: publish(), range(2)))
    assert factory.return_value.create_page_post.call_count == 1
    post.refresh_from_db()
    assert post.status == Post.Status.PUBLISHED and post.external_id == "page_post"
