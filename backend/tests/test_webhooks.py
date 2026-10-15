import hashlib
import hmac
import json
from unittest.mock import patch

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from apps.inbox.models import Conversation, Message
from apps.meta.models import RawWebhookEvent
from apps.meta.tasks import process_webhook_event
from apps.social.models import Comment

pytestmark = pytest.mark.django_db


def delivery(client, payload, valid=True):
    raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    signature = (
        "sha256=" + hmac.new(settings.META_APP_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    )
    return client.post(
        "/api/meta/webhook/",
        data=raw,
        content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256=signature if valid else "sha256=bad",
    )


def message_payload(mid="mid-1"):
    return {
        "object": "page",
        "entry": [
            {
                "id": "page",
                "time": 1791871800000,
                "messaging": [
                    {
                        "sender": {"id": "psid"},
                        "recipient": {"id": "page"},
                        "timestamp": 1791871800000,
                        "message": {"mid": mid, "text": "Сайн уу?"},
                    }
                ],
            }
        ],
    }


def process_all():
    for event in RawWebhookEvent.objects.filter(status="RECEIVED"):
        process_webhook_event(str(event.company_id), str(event.pk))


def test_verify():
    client = APIClient()
    assert (
        client.get(
            "/api/meta/webhook/",
            {
                "hub.mode": "subscribe",
                "hub.verify_token": settings.META_WEBHOOK_VERIFY_TOKEN,
                "hub.challenge": "123",
            },
        ).content
        == b"123"
    )
    assert (
        client.get(
            "/api/meta/webhook/", {"hub.mode": "subscribe", "hub.verify_token": "wrong"}
        ).status_code
        == 403
    )


@pytest.mark.parametrize("raw", [b"broken", b"[]", b'{"entry":{}}', b'{"entry":[42]}'])
def test_malformed_json(raw):
    assert delivery(APIClient(), raw).status_code == 400


def test_invalid_signature_before_parsing():
    assert delivery(APIClient(), b"not-json", valid=False).status_code == 403
    assert RawWebhookEvent.objects.count() == 0


def test_duplicate_message_and_envelope(account):
    client = APIClient()
    payload = message_payload()
    with patch("apps.meta.webhook_views.enqueue"):
        assert delivery(client, payload).status_code == 200
        assert delivery(client, payload).status_code == 200
        assert Message.objects.count() == 0  # HTTP request does not normalize or sync.
    assert RawWebhookEvent.objects.count() == 1
    process_all()
    payload["entry"][0]["time"] += 1000
    delivery(client, payload)
    process_all()
    assert Message.objects.count() == 1 and Conversation.objects.count() == 1
    conversation = Conversation.objects.get(company=account.company)
    assert conversation.unread_count == 1
    for event in RawWebhookEvent.objects.all():
        process_webhook_event(str(event.company_id), str(event.pk))
    assert Message.objects.count() == 1


def test_comment_add_edit_delete_unknown(account):
    client = APIClient()
    value = {
        "item": "comment",
        "verb": "add",
        "post_id": "page_post",
        "comment_id": "comment",
        "parent_id": "page_post",
        "message": "Үнэ?",
        "created_time": 1791871800,
    }
    payload = {
        "object": "page",
        "entry": [{"id": "page", "changes": [{"field": "feed", "value": value}]}],
    }
    delivery(client, payload)
    process_all()
    assert Comment.objects.get(company=account.company).message == "Үнэ?"
    value.update(verb="edited", message="Хэд вэ?")
    delivery(client, payload)
    process_all()
    assert Comment.objects.get(company=account.company).message == "Хэд вэ?"
    value.update(verb="remove")
    delivery(client, payload)
    process_all()
    assert Comment.objects.get(company=account.company).is_deleted
    assert Comment.objects.count() == 1
    payload["entry"][0]["changes"] = [{"field": "unknown", "value": {"new": "data"}}]
    delivery(client, payload)
    process_all()
    assert RawWebhookEvent.objects.filter(status="IGNORED").exists()


def test_unknown_object_preserved():
    payload = {"object": "future", "entry": [{"id": "unknown", "mystery": {"a": 1}}]}
    assert delivery(APIClient(), payload).status_code == 200
    event = RawWebhookEvent.objects.get()
    assert event.company_id is None and event.status == "IGNORED"
    assert event.payload == payload


def test_echo_does_not_open_response_window(account):
    payload = message_payload()
    entry = payload["entry"][0]["messaging"][0]
    entry["sender"]["id"] = "page"
    entry["recipient"]["id"] = "psid"
    entry["message"]["is_echo"] = True
    delivery(APIClient(), payload)
    process_all()
    assert Message.objects.get(company=account.company).status == "SENT"
    conversation = Conversation.objects.get(company=account.company)
    assert conversation.unread_count == 0 and conversation.last_inbound_at is None


def test_out_of_order_comment_does_not_undo_delete(account):
    payload = {
        "object": "page",
        "entry": [
            {
                "id": "page",
                "time": 2000000,
                "changes": [
                    {
                        "field": "feed",
                        "value": {
                            "item": "comment",
                            "verb": "remove",
                            "post_id": "post",
                            "comment_id": "comment",
                        },
                    }
                ],
            }
        ],
    }
    delivery(APIClient(), payload)
    process_all()
    payload["entry"][0]["time"] = 1000000
    payload["entry"][0]["changes"][0]["value"].update(verb="add", message="old")
    delivery(APIClient(), payload)
    process_all()
    assert Comment.objects.get(company=account.company).is_deleted


def test_unknown_message_shape_ignored(account):
    payload = message_payload()
    payload["entry"][0]["messaging"][0]["sender"] = []
    delivery(APIClient(), payload)
    process_all()
    assert RawWebhookEvent.objects.get(company=account.company).status == "IGNORED"


@pytest.mark.parametrize(
    "timestamp", [None, "bad", {}, [], True, 10**400, "2026-10-14T10:00:00Z", "future"]
)
def test_invalid_message_time_is_processed_without_eligibility(account, frozen_now, timestamp):
    from datetime import timedelta

    from apps.inbox.services import can_reply

    payload = message_payload()
    item = payload["entry"][0]["messaging"][0]
    if timestamp is None:
        del item["timestamp"]
    else:
        item["timestamp"] = (
            (frozen_now + timedelta(days=7)).timestamp() * 1000
            if timestamp == "future"
            else timestamp
        )
    with patch("apps.meta.webhook_views.enqueue"):
        assert delivery(APIClient(), payload).status_code == 200
    process_all()
    event = RawWebhookEvent.objects.get(company=account.company)
    assert event.status == "PROCESSED" and event.attempts == 1
    conversation = Conversation.objects.get(company=account.company)
    assert conversation.last_inbound_at is None and can_reply(conversation) is False
    assert Message.objects.get(conversation=conversation).sent_at == frozen_now


@pytest.mark.parametrize("prior_age", [None, 3600, 90000])
def test_echo_never_creates_advances_or_reopens_window(conversation, frozen_now, prior_age):
    from datetime import timedelta

    from apps.inbox.services import can_reply

    prior = None if prior_age is None else frozen_now - timedelta(seconds=prior_age)
    conversation.last_inbound_at = prior
    conversation.save(update_fields=["last_inbound_at"])
    payload = message_payload()
    item = payload["entry"][0]["messaging"][0]
    item.update(
        sender={"id": "page"}, recipient={"id": "psid"}, timestamp=frozen_now.timestamp() * 1000
    )
    item["message"]["is_echo"] = True
    delivery(APIClient(), payload)
    process_all()
    conversation.refresh_from_db()
    assert conversation.last_inbound_at == prior
    assert can_reply(conversation) is (prior_age == 3600)
    assert conversation.unread_count == 0


def test_webhook_time_monotonic_duplicate_and_invalid_preserve_valid(account, frozen_now):
    from datetime import timedelta

    from apps.inbox.services import can_reply

    valid = frozen_now - timedelta(hours=1)
    cases = [
        ("first", valid),
        ("first", frozen_now),
        ("older", valid - timedelta(hours=2)),
        ("invalid", None),
    ]
    for mid, timestamp in cases:
        payload = message_payload(mid)
        item = payload["entry"][0]["messaging"][0]
        item["timestamp"] = timestamp.timestamp() * 1000 if timestamp else "malformed"
        delivery(APIClient(), payload)
        process_all()
        conversation = Conversation.objects.get(company=account.company)
        assert conversation.last_inbound_at == valid
        assert can_reply(conversation) is True
    assert Message.objects.filter(company=account.company).count() == 3
    assert (
        not RawWebhookEvent.objects.filter(company=account.company)
        .exclude(status="PROCESSED")
        .exists()
    )


def test_distinct_and_duplicate_comment_envelopes_preserve_delete(account, frozen_now):
    from datetime import timedelta

    deleted_at = frozen_now - timedelta(minutes=1)
    value = {
        "item": "comment",
        "verb": "remove",
        "post_id": "post",
        "comment_id": "comment",
    }
    payload = {
        "object": "page",
        "entry": [
            {
                "id": "page",
                "time": deleted_at.timestamp() * 1000,
                "changes": [{"field": "feed", "value": value}],
            }
        ],
    }
    with patch("apps.meta.webhook_views.enqueue"):
        assert delivery(APIClient(), payload).status_code == 200
        assert delivery(APIClient(), payload).status_code == 200
    assert RawWebhookEvent.objects.filter(company=account.company).count() == 1
    process_all()
    value.update(verb="edited", message="delayed stale edit")
    payload["entry"][0]["time"] = (deleted_at - timedelta(minutes=1)).timestamp() * 1000
    with patch("apps.meta.webhook_views.enqueue"):
        assert delivery(APIClient(), payload).status_code == 200
    process_all()
    process_all()  # Replaying already processed task IDs is also safe.
    comment = Comment.objects.get(company=account.company, external_id="comment")
    assert comment.is_deleted and comment.message == "" and comment.last_event_at == deleted_at
    events = RawWebhookEvent.objects.filter(company=account.company)
    assert events.count() == 2
    assert all(event.status == "PROCESSED" and event.attempts == 1 for event in events)
