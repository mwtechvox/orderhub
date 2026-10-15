import uuid
from unittest.mock import patch

import pytest

from apps.meta.exceptions import MetaDeliveryUnknown, MetaError
from apps.social.models import Comment, CommentReplyAttempt, Post

pytestmark = pytest.mark.django_db


@pytest.fixture
def comment(tenant, account):
    post = Post.objects.create(
        company=tenant[0],
        social_account=account,
        external_id="post",
        created_at_platform="2026-10-14T10:00Z",
    )
    return Comment.objects.create(
        company=tenant[0],
        social_account=account,
        post=post,
        external_id="comment",
        message="Үнэ хэд вэ?",
        created_at_platform="2026-10-14T10:00Z",
    )


def payload(key):
    return {"message": "89,000₮", "idempotency_key": str(key)}


def test_successful_comment_reply_is_durable_and_sent(tenant, comment):
    with patch("apps.social.services.account_client") as factory:
        factory.return_value.reply_to_comment.return_value = {"id": "reply"}
        response = tenant[2].post(f"/api/comments/{comment.pk}/reply/", payload(uuid.uuid4()))
    assert response.status_code == 201 and response.data["status"] == "SENT"
    attempt = CommentReplyAttempt.objects.get(company=tenant[0])
    assert attempt.provider_reply_id == "reply" and attempt.text == "89,000₮"
    assert Comment.objects.filter(company=tenant[0], external_id="reply").exists()


def test_clear_provider_rejection_is_failed_and_can_use_a_new_key(tenant, comment):
    first_key, second_key = uuid.uuid4(), uuid.uuid4()
    with patch("apps.social.services.account_client") as factory:
        graph = factory.return_value
        graph.reply_to_comment.side_effect = [MetaError(provider_code=100), {"id": "reply"}]
        failed = tenant[2].post(f"/api/comments/{comment.pk}/reply/", payload(first_key))
        sent = tenant[2].post(f"/api/comments/{comment.pk}/reply/", payload(second_key))
    assert failed.status_code == 201 and failed.data["status"] == "FAILED"
    assert sent.status_code == 201 and sent.data["status"] == "SENT"
    assert graph.reply_to_comment.call_count == 2


@pytest.mark.parametrize(
    "outcome",
    [MetaDeliveryUnknown(), {}],
    ids=["timeout-or-connection-ambiguity", "malformed-success"],
)
def test_ambiguous_comment_reply_stays_delivery_unknown(tenant, comment, outcome):
    key = uuid.uuid4()
    with patch("apps.social.services.account_client") as factory:
        factory.return_value.reply_to_comment.side_effect = (
            outcome if isinstance(outcome, Exception) else None
        )
        if not isinstance(outcome, Exception):
            factory.return_value.reply_to_comment.return_value = outcome
        response = tenant[2].post(f"/api/comments/{comment.pk}/reply/", payload(key))
    assert response.status_code == 201 and response.data["status"] == "DELIVERY_UNKNOWN"
    attempt = CommentReplyAttempt.objects.get(company=tenant[0])
    assert attempt.status == "DELIVERY_UNKNOWN" and attempt.provider_reply_id == ""


def test_same_idempotency_key_returns_existing_attempt_without_a_second_write(tenant, comment):
    key = uuid.uuid4()
    with patch("apps.social.services.account_client") as factory:
        factory.return_value.reply_to_comment.return_value = {"id": "reply"}
        first = tenant[2].post(f"/api/comments/{comment.pk}/reply/", payload(key))
        repeated = tenant[2].post(f"/api/comments/{comment.pk}/reply/", payload(key))
    assert first.status_code == 201 and repeated.status_code == 200
    assert first.data["id"] == repeated.data["id"] and repeated.data["status"] == "SENT"
    factory.return_value.reply_to_comment.assert_called_once()
    assert CommentReplyAttempt.objects.filter(company=tenant[0]).count() == 1


def test_new_key_cannot_bypass_an_existing_unknown_delivery(tenant, comment):
    first_key, fresh_key = uuid.uuid4(), uuid.uuid4()
    with patch("apps.social.services.account_client") as factory:
        factory.return_value.reply_to_comment.side_effect = MetaDeliveryUnknown()
        unknown = tenant[2].post(f"/api/comments/{comment.pk}/reply/", payload(first_key))
        bypass = tenant[2].post(f"/api/comments/{comment.pk}/reply/", payload(fresh_key))
    assert unknown.status_code == 201 and bypass.status_code == 200
    assert bypass.data["id"] == unknown.data["id"] and bypass.data["status"] == "DELIVERY_UNKNOWN"
    factory.return_value.reply_to_comment.assert_called_once()
    assert CommentReplyAttempt.objects.filter(company=tenant[0]).count() == 1


def test_reused_idempotency_key_with_changed_text_is_rejected(tenant, comment):
    key = uuid.uuid4()
    with patch("apps.social.services.account_client") as factory:
        factory.return_value.reply_to_comment.return_value = {"id": "reply"}
        assert tenant[2].post(f"/api/comments/{comment.pk}/reply/", payload(key)).status_code == 201
        conflict = tenant[2].post(
            f"/api/comments/{comment.pk}/reply/", {"message": "өөр", "idempotency_key": str(key)}
        )
    assert conflict.status_code == 400
    factory.return_value.reply_to_comment.assert_called_once()


def test_deleted_comment_cannot_create_reply_attempt(tenant, comment):
    comment.is_deleted = True
    comment.save(update_fields=["is_deleted"])
    with patch("apps.social.services.account_client") as factory:
        response = tenant[2].post(f"/api/comments/{comment.pk}/reply/", payload(uuid.uuid4()))
    assert response.status_code == 404
    factory.assert_not_called()
    assert not CommentReplyAttempt.objects.filter(company=tenant[0]).exists()
