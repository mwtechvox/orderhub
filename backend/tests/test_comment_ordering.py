import uuid
from datetime import timedelta
from unittest.mock import Mock, patch

import pytest

from apps.meta.services.webhooks import process_change
from apps.social.models import Comment, Post
from apps.social.services import sync_comments, upsert_comment

pytestmark = pytest.mark.django_db


@pytest.fixture
def post(account, frozen_now):
    return Post.objects.create(
        company=account.company,
        social_account=account,
        external_id="post",
        created_at_platform=frozen_now - timedelta(days=1),
    )


def change(account, verb, time, *, message="text", comment_id="comment", **fields):
    return process_change(
        account,
        {
            "field": "feed",
            "value": {
                "item": "comment",
                "verb": verb,
                "post_id": "post",
                "comment_id": comment_id,
                "message": message,
                **fields,
            },
        },
        time,
    )


def test_delete_then_stale_sync_retains_tombstone(post, account, frozen_now):
    upsert_comment(post, {"id": "comment", "message": "original"})
    change(account, "remove", frozen_now.timestamp() * 1000)
    comment = upsert_comment(post, {"id": "comment", "message": "stale", "can_comment": True})
    assert comment.is_deleted and comment.message == "" and not comment.can_reply


def test_normal_sync_is_repeatable_and_preserves_nested_replies(post):
    graph = Mock()
    graph.get_post_comments.return_value = [{"id": "comment", "message": "first"}]
    graph.get_comment_replies.return_value = [{"id": "reply", "message": "reply"}]
    sync_comments(post, graph)
    graph.get_post_comments.return_value = [{"id": "comment", "message": "updated"}]
    sync_comments(post, graph)
    parent = Comment.objects.get(company=post.company, external_id="comment")
    child = Comment.objects.get(company=post.company, external_id="reply")
    assert Comment.objects.filter(company=post.company).count() == 2
    assert not parent.is_deleted and parent.message == "updated"
    assert not child.is_deleted and child.parent_comment_id == parent.pk


@pytest.mark.parametrize("verb", ["add", "edit", "edited"])
@pytest.mark.parametrize("relative_seconds", [-60, 0, 60])
def test_no_add_or_edit_restores_deleted_id(post, account, frozen_now, verb, relative_seconds):
    deleted_at = frozen_now - timedelta(minutes=2)
    change(account, "remove", deleted_at.timestamp() * 1000)
    change(account, verb, (deleted_at + timedelta(seconds=relative_seconds)).timestamp() * 1000)
    comment = Comment.objects.get(company=account.company, external_id="comment")
    assert comment.is_deleted and comment.message == "" and not comment.can_reply
    assert comment.last_event_at == deleted_at


@pytest.mark.parametrize("initial_verb", ["add", "edited"])
def test_add_or_edit_followed_by_duplicate_delete(post, account, frozen_now, initial_verb):
    change(account, initial_verb, (frozen_now - timedelta(minutes=1)).timestamp() * 1000)
    for verb in ["remove", "remove", "delete"]:
        change(account, verb, frozen_now.timestamp() * 1000)
    comment = Comment.objects.get(company=account.company, external_id="comment")
    assert comment.is_deleted and comment.last_event_at == frozen_now
    assert Comment.objects.filter(company=account.company).count() == 1


def test_active_events_use_monotonic_watermark_not_creation_time(post, account, frozen_now):
    t1 = frozen_now - timedelta(minutes=2)
    t2 = frozen_now - timedelta(minutes=1)
    change(account, "add", t1.timestamp() * 1000, message="first", created_time=1)
    change(account, "edited", t2.timestamp() * 1000, message="newest", created_time=1)
    change(
        account, "edited", t1.timestamp() * 1000, message="old", created_time=frozen_now.timestamp()
    )
    # Same timestamp is a duplicate/tie, not proof of a newer revision.
    change(account, "edited", t2.timestamp() * 1000, message="tie")
    # Neither creation time nor receipt time makes a sync snapshot newer.
    comment = upsert_comment(
        post, {"id": "comment", "message": "snapshot", "created_time": frozen_now.isoformat()}
    )
    assert comment.message == "newest" and comment.last_event_at == t2
    change(account, "edited", frozen_now.timestamp() * 1000, message="latest")
    comment.refresh_from_db()
    assert comment.message == "latest" and comment.last_event_at == frozen_now


@pytest.mark.parametrize("invalid_time", [None, "bad", True, float("inf"), 10**400, 0, "future"])
def test_invalid_event_time_never_replaces_watermark_but_delete_still_tombstones(
    post, account, frozen_now, invalid_time
):
    if invalid_time == "future":
        invalid_time = (frozen_now + timedelta(days=7)).timestamp() * 1000
    change(account, "add", frozen_now.timestamp() * 1000, message="known")
    change(account, "edited", invalid_time, message="unknown order")
    comment = Comment.objects.get(company=account.company, external_id="comment")
    assert comment.message == "known" and comment.last_event_at == frozen_now
    change(account, "remove", invalid_time)
    comment.refresh_from_db()
    assert comment.is_deleted and comment.last_event_at == frozen_now
    upsert_comment(post, {"id": "comment", "message": "stale"})
    comment.refresh_from_db()
    assert comment.is_deleted and comment.message == ""


def test_first_seen_untimed_delete_stays_deleted(post, account, frozen_now):
    change(account, "remove", None)
    change(account, "add", frozen_now.timestamp() * 1000, message="later delivery")
    comment = upsert_comment(post, {"id": "comment", "message": "stale"})
    assert comment.is_deleted and comment.last_event_at is None


def test_delayed_delete_is_terminal_without_restore_contract(post, account, frozen_now):
    change(account, "edited", frozen_now.timestamp() * 1000)
    change(account, "remove", (frozen_now - timedelta(minutes=1)).timestamp() * 1000)
    comment = Comment.objects.get(company=account.company, external_id="comment")
    assert comment.is_deleted and comment.last_event_at == frozen_now


def test_snapshot_fetched_before_delete_cannot_resurrect(post, account, frozen_now):
    graph = Mock()

    def snapshot():
        old_payload = {"id": "comment", "message": "snapshot before deletion"}
        change(account, "remove", frozen_now.timestamp() * 1000)
        yield old_payload

    graph.get_post_comments.return_value = snapshot()
    sync_comments(post, graph)
    comment = Comment.objects.get(company=account.company, external_id="comment")
    assert comment.is_deleted and comment.message == ""
    graph.get_comment_replies.assert_not_called()


def test_deleted_parent_placeholder_is_never_reactivated(post, account, frozen_now):
    change(account, "remove", frozen_now.timestamp() * 1000, comment_id="parent")
    change(account, "add", frozen_now.timestamp() * 1000, comment_id="child", parent_id="parent")
    parent = Comment.objects.get(company=account.company, external_id="parent")
    child = Comment.objects.get(company=account.company, external_id="child")
    assert parent.is_deleted and child.parent_comment_id == parent.pk
    change(account, "remove", frozen_now.timestamp() * 1000, comment_id="child")
    result = upsert_comment(post, {"id": "child", "message": "old child"}, parent=parent)
    assert result.is_deleted and result.parent_comment_id == parent.pk


def test_deleted_comment_is_hidden_and_cannot_be_replied_to(tenant, post, account, frozen_now):
    from rest_framework.exceptions import ValidationError

    from apps.social.services import reply

    stale_instance = upsert_comment(post, {"id": "comment", "message": "old"})
    upsert_comment(post, {"id": "visible", "message": "visible"})
    change(account, "remove", frozen_now.timestamp() * 1000)
    result = tenant[2].get(f"/api/posts/{post.pk}/comments/")
    assert result.status_code == 200 and result.data["count"] == 1
    assert result.data["results"][0]["message"] == "visible"
    with patch("apps.social.services.account_client") as factory:
        result = tenant[2].post(f"/api/comments/{stale_instance.pk}/reply/", {"message": "reply"})
        assert result.status_code == 404
        with pytest.raises(ValidationError):
            reply(stale_instance, "reply", uuid.uuid4())
        factory.assert_not_called()


def test_comment_identity_and_tombstone_are_tenant_scoped(post, account, frozen_now):
    from apps.companies.models import Company
    from apps.meta.models import SocialAccount

    other = Company.objects.create(name="Other", slug="other")
    other_account = SocialAccount.objects.create(company=other, external_account_id="page")
    other_post = Post.objects.create(
        company=other,
        social_account=other_account,
        external_id="post",
        created_at_platform=frozen_now,
    )
    live = upsert_comment(other_post, {"id": "comment", "message": "other tenant"})
    change(account, "remove", frozen_now.timestamp() * 1000)
    upsert_comment(post, {"id": "comment", "message": "stale"})
    live.refresh_from_db()
    assert not live.is_deleted and live.message == "other tenant"
