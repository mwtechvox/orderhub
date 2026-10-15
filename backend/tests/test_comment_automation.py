from unittest.mock import patch

import httpx
import pytest
from django.utils import timezone

from apps.companies.models import Company, CompanyMembership
from apps.inbox.models import Conversation, Message
from apps.meta.exceptions import (
    MetaAuthError,
    MetaDeliveryUnknown,
    MetaError,
    MetaPermissionError,
    MetaRateLimitError,
)
from apps.meta.models import SocialAccount
from apps.meta.services.facebook import FacebookGraphClient
from apps.meta.services.webhooks import process_change, process_message
from apps.social.models import (
    Comment,
    CommentAutomationRule,
    CommentPrivateReplyAttempt,
    CommentReplyAttempt,
    Post,
)
from apps.social.services import schedule_comment_automation
from apps.social.tasks import dispatch_pending_comment_automations, process_comment_automation

pytestmark = pytest.mark.django_db


PUBLIC_TEXT = "Мэдээллийг чат руу илгээлээ. Чатаа шалгаарай 😊"
PRIVATE_TEXT = "Сайн байна уу 👋 Дэлгэрэнгүй мэдээллийг хүргэж байна."


@pytest.fixture
def rule(tenant, account):
    return CommentAutomationRule.objects.create(
        company=tenant[0],
        social_account=account,
        is_enabled=True,
        public_reply_enabled=True,
        public_reply_text=PUBLIC_TEXT,
        private_reply_enabled=True,
        private_reply_text=PRIVATE_TEXT,
    )


@pytest.fixture
def customer_comment(tenant, account):
    post = Post.objects.create(
        company=tenant[0],
        social_account=account,
        external_id="page_post",
        created_at_platform=timezone.now(),
    )
    return Comment.objects.create(
        company=tenant[0],
        social_account=account,
        post=post,
        external_id="customer-comment",
        author_external_id="customer-psid",
        author_name="Бат",
        message="Үнэ хэд вэ?",
        created_at_platform=timezone.now(),
    )


def set_role(tenant, role):
    membership = CompanyMembership.objects.get(company=tenant[0], user=tenant[1])
    membership.role = role
    membership.save(update_fields=["role"])


@pytest.mark.parametrize("role", ["OWNER", "ADMIN"])
def test_owner_and_admin_can_update_rule(tenant, account, role):
    set_role(tenant, role)
    response = tenant[2].put(
        f"/api/meta/accounts/{account.pk}/comment-automation/",
        {
            "is_enabled": True,
            "public_reply_enabled": True,
            "public_reply_text": PUBLIC_TEXT,
            "private_reply_enabled": True,
            "private_reply_text": PRIVATE_TEXT,
        },
        format="json",
    )
    assert response.status_code == 200 and response.data["is_enabled"] is True
    saved = CommentAutomationRule.objects.get(company=tenant[0], social_account=account)
    assert saved.public_reply_text == PUBLIC_TEXT and saved.private_reply_text == PRIVATE_TEXT


def test_agent_can_read_but_cannot_update_rule(tenant, account):
    set_role(tenant, "AGENT")
    path = f"/api/meta/accounts/{account.pk}/comment-automation/"
    assert tenant[2].get(path).status_code == 200
    assert tenant[2].put(path, {"is_enabled": False}, format="json").status_code == 403


def test_cross_company_rule_is_inaccessible(tenant):
    other = Company.objects.create(name="Other", slug="other-automation")
    account = SocialAccount.objects.create(
        company=other, external_account_id="other-page", display_name="Other"
    )
    path = f"/api/meta/accounts/{account.pk}/comment-automation/"
    assert tenant[2].get(path).status_code == 404
    assert tenant[2].put(path, {"is_enabled": False}, format="json").status_code == 404


def test_new_customer_comment_queues_durable_actions(
    account, rule, django_capture_on_commit_callbacks
):
    change = {
        "field": "feed",
        "value": {
            "item": "comment",
            "verb": "add",
            "post_id": "page_post",
            "comment_id": "comment",
            "parent_id": "page_post",
            "message": "Үнэ хэд вэ?",
            "sender_id": "customer-psid",
            "sender_name": "Бат",
            "created_time": 1791972000,
        },
    }
    with (
        patch("apps.social.services.enqueue") as queue,
        django_capture_on_commit_callbacks(execute=True),
    ):
        assert process_change(account, change, 1791972000000)
    comment = Comment.objects.get(company=account.company, external_id="comment")
    assert comment.parent_comment_id is None
    assert CommentReplyAttempt.objects.get(comment=comment).status == "PENDING"
    assert CommentPrivateReplyAttempt.objects.get(comment=comment).status == "PENDING"
    queue.assert_called_once()


def test_disabled_rule_creates_no_attempts(account, rule):
    rule.is_enabled = False
    rule.save(update_fields=["is_enabled"])
    change = {
        "field": "feed",
        "value": {
            "item": "comment",
            "verb": "add",
            "post_id": "page_post",
            "comment_id": "comment",
            "parent_id": "page_post",
            "sender_id": "customer-psid",
        },
    }
    with patch("apps.social.services.enqueue") as queue:
        process_change(account, change, 1791972000000)
    assert not CommentReplyAttempt.objects.exists()
    assert not CommentPrivateReplyAttempt.objects.exists()
    queue.assert_not_called()


def test_invalid_provider_comment_time_does_not_authorize_automation(account, rule):
    change = {
        "field": "feed",
        "value": {
            "item": "comment",
            "verb": "add",
            "post_id": "page_post",
            "comment_id": "comment",
            "parent_id": "page_post",
            "sender_id": "customer-psid",
            "created_time": "invalid",
        },
    }
    with patch("apps.social.services.enqueue") as queue:
        process_change(account, change, 1791972000000)
    assert Comment.objects.filter(company=account.company, external_id="comment").exists()
    assert not CommentReplyAttempt.objects.exists()
    assert not CommentPrivateReplyAttempt.objects.exists()
    queue.assert_not_called()


def test_disabling_rule_before_worker_cancels_pending_actions(rule, customer_comment):
    with patch("apps.social.services.enqueue"):
        schedule_comment_automation(customer_comment)
    rule.is_enabled = False
    rule.save(update_fields=["is_enabled"])
    with patch("apps.social.services.account_client") as factory:
        process_comment_automation(str(customer_comment.company_id), str(customer_comment.pk))
    factory.assert_not_called()
    assert CommentReplyAttempt.objects.get(comment=customer_comment).status == "FAILED"
    assert CommentPrivateReplyAttempt.objects.get(comment=customer_comment).status == "FAILED"


def test_public_and_private_actions_send_once(rule, customer_comment):
    with patch("apps.social.services.enqueue"):
        assert schedule_comment_automation(customer_comment)
    with patch("apps.social.services.account_client") as factory:
        graph = factory.return_value
        graph.reply_to_comment.return_value = {"id": "public-reply"}
        graph.send_comment_private_reply.return_value = {"message_id": "private-message"}
        process_comment_automation(str(customer_comment.company_id), str(customer_comment.pk))
        process_comment_automation(str(customer_comment.company_id), str(customer_comment.pk))
    assert graph.reply_to_comment.call_count == 1
    assert graph.send_comment_private_reply.call_count == 1
    assert CommentReplyAttempt.objects.get(comment=customer_comment).status == "SENT"
    private = CommentPrivateReplyAttempt.objects.get(comment=customer_comment)
    assert private.status == "SENT" and private.provider_message_id == "private-message"


@pytest.mark.parametrize("kind", ["page", "nested", "deleted", "missing-author", "expired"])
def test_ineligible_comments_never_trigger(rule, customer_comment, kind):
    from datetime import timedelta

    if kind == "page":
        customer_comment.author_external_id = customer_comment.social_account.external_account_id
    elif kind == "nested":
        parent = Comment.objects.create(
            company=customer_comment.company,
            social_account=customer_comment.social_account,
            post=customer_comment.post,
            external_id="parent",
            author_external_id="customer-psid",
            created_at_platform=timezone.now(),
        )
        customer_comment.parent_comment = parent
    elif kind == "deleted":
        customer_comment.is_deleted = True
    elif kind == "expired":
        customer_comment.created_at_platform = timezone.now() - timedelta(days=7)
    else:
        customer_comment.author_external_id = ""
    customer_comment.save()
    with patch("apps.social.services.enqueue") as queue:
        assert schedule_comment_automation(customer_comment) is False
    assert not CommentReplyAttempt.objects.exists()
    assert not CommentPrivateReplyAttempt.objects.exists()
    queue.assert_not_called()


def test_public_failure_does_not_block_private(rule, customer_comment):
    with patch("apps.social.services.enqueue"):
        schedule_comment_automation(customer_comment)
    with patch("apps.social.services.account_client") as factory:
        graph = factory.return_value
        graph.reply_to_comment.side_effect = MetaError(provider_code=100)
        graph.send_comment_private_reply.return_value = {"id": "private-message"}
        process_comment_automation(str(customer_comment.company_id), str(customer_comment.pk))
    assert CommentReplyAttempt.objects.get(comment=customer_comment).status == "FAILED"
    assert CommentPrivateReplyAttempt.objects.get(comment=customer_comment).status == "SENT"


def test_private_failure_does_not_rollback_public(rule, customer_comment):
    with patch("apps.social.services.enqueue"):
        schedule_comment_automation(customer_comment)
    with patch("apps.social.services.account_client") as factory:
        graph = factory.return_value
        graph.reply_to_comment.return_value = {"id": "public-reply"}
        graph.send_comment_private_reply.side_effect = MetaError(provider_code=100)
        process_comment_automation(str(customer_comment.company_id), str(customer_comment.pk))
    assert CommentReplyAttempt.objects.get(comment=customer_comment).status == "SENT"
    assert CommentPrivateReplyAttempt.objects.get(comment=customer_comment).status == "FAILED"


def test_ambiguous_writes_are_terminal_and_not_retried(rule, customer_comment):
    with patch("apps.social.services.enqueue"):
        schedule_comment_automation(customer_comment)
    with patch("apps.social.services.account_client") as factory:
        graph = factory.return_value
        graph.reply_to_comment.side_effect = MetaDeliveryUnknown()
        graph.send_comment_private_reply.side_effect = MetaDeliveryUnknown()
        process_comment_automation(str(customer_comment.company_id), str(customer_comment.pk))
        process_comment_automation(str(customer_comment.company_id), str(customer_comment.pk))
    assert graph.reply_to_comment.call_count == 1
    assert graph.send_comment_private_reply.call_count == 1
    assert CommentReplyAttempt.objects.get(comment=customer_comment).status == "DELIVERY_UNKNOWN"
    assert (
        CommentPrivateReplyAttempt.objects.get(comment=customer_comment).status
        == "DELIVERY_UNKNOWN"
    )


def test_rule_edit_affects_only_future_comments(rule, customer_comment):
    with patch("apps.social.services.enqueue"):
        schedule_comment_automation(customer_comment)
    rule.public_reply_text = "Шинэ нийтийн текст"
    rule.private_reply_text = "Шинэ хувийн текст"
    rule.save(update_fields=["public_reply_text", "private_reply_text"])
    assert CommentReplyAttempt.objects.get(comment=customer_comment).text == PUBLIC_TEXT
    assert CommentPrivateReplyAttempt.objects.get(comment=customer_comment).message == PRIVATE_TEXT


def test_manual_public_reply_cannot_race_pending_automation(rule, customer_comment, tenant):
    import uuid

    with patch("apps.social.services.enqueue"):
        schedule_comment_automation(customer_comment)
    with patch("apps.social.services.account_client") as factory:
        response = tenant[2].post(
            f"/api/comments/{customer_comment.pk}/reply/",
            {"message": "manual", "idempotency_key": str(uuid.uuid4())},
            format="json",
        )
    assert response.status_code == 400
    factory.assert_not_called()
    assert CommentReplyAttempt.objects.filter(comment=customer_comment).count() == 1


def test_pending_dispatch_recovers_broker_publish_loss(rule, customer_comment):
    with patch("apps.social.services.enqueue"):
        schedule_comment_automation(customer_comment)
    with patch("apps.social.tasks.process_comment_automation.delay") as queue:
        dispatch_pending_comment_automations()
    queue.assert_called_once_with(str(customer_comment.company_id), str(customer_comment.pk))


def test_customer_reply_after_private_message_uses_existing_inbox(rule, customer_comment):
    with patch("apps.social.services.enqueue"):
        schedule_comment_automation(customer_comment)
    with patch("apps.social.services.account_client") as factory:
        factory.return_value.reply_to_comment.return_value = {"id": "public-reply"}
        factory.return_value.send_comment_private_reply.return_value = {"id": "private-message"}
        process_comment_automation(str(customer_comment.company_id), str(customer_comment.pk))
    assert process_message(
        customer_comment.social_account,
        {
            "sender": {"id": "customer-psid"},
            "recipient": {"id": "page"},
            "timestamp": timezone.now().timestamp() * 1000,
            "message": {"mid": "customer-follow-up", "text": "Захиалъя"},
        },
    )
    conversation = Conversation.objects.get(company=customer_comment.company)
    assert conversation.customer.external_user_id == "customer-psid"
    assert Message.objects.get(conversation=conversation).text == "Захиалъя"


@pytest.mark.parametrize(
    "body,provider_id",
    [({"message_id": "mid"}, "mid"), ({"id": "legacy-mid"}, "legacy-mid")],
)
def test_private_reply_client_accepts_documented_identifier_shapes(respx_mock, body, provider_id):
    route = respx_mock.post("https://graph.facebook.com/v26.0/comment/private_replies").respond(
        200, json=body
    )
    result = FacebookGraphClient("TOKEN").send_comment_private_reply("comment", "hello")
    assert (result.get("message_id") or result.get("id")) == provider_id
    assert route.calls[0].request.headers["Authorization"] == "Bearer TOKEN"
    assert route.calls[0].request.content == b'{"message":"hello"}'


@pytest.mark.parametrize(
    "status,code,exception",
    [
        (400, 100, MetaError),
        (403, 200, MetaPermissionError),
        (401, 190, MetaAuthError),
        (429, 4, MetaRateLimitError),
    ],
)
def test_private_reply_client_preserves_clear_error_classification(
    respx_mock, status, code, exception
):
    route = respx_mock.post("https://graph.facebook.com/v26.0/comment/private_replies").respond(
        status, json={"error": {"code": code, "message": "SECRET"}}
    )
    with pytest.raises(exception):
        FacebookGraphClient("TOKEN").send_comment_private_reply("comment", "hello")
    assert route.call_count == 1


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, json={}),
        httpx.Response(200, text="not-json"),
        httpx.ReadTimeout("timeout"),
    ],
)
def test_private_reply_ambiguous_result_is_not_retried(respx_mock, response):
    route = respx_mock.post("https://graph.facebook.com/v26.0/comment/private_replies").mock(
        side_effect=response
    )
    with pytest.raises(MetaDeliveryUnknown):
        FacebookGraphClient("TOKEN").send_comment_private_reply("comment", "hello")
    assert route.call_count == 1
