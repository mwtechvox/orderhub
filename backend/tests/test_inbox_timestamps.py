import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest

from apps.inbox.models import Conversation, Message
from apps.inbox.services import can_reply, create_outbound, store_message, sync_conversations
from apps.inbox.tasks import send_meta_message

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "age,eligible",
    [
        (86399, True),
        (86400, False),
        (86401, False),
        (0, True),
        (-5, True),
        (-5.001, False),
        (-604800, False),
        (None, False),
    ],
)
def test_reply_boundary_and_api_gate(tenant, conversation, frozen_now, age, eligible):
    conversation.last_inbound_at = None if age is None else frozen_now - timedelta(seconds=age)
    conversation.save(update_fields=["last_inbound_at"])
    assert can_reply(conversation) is eligible
    assert tenant[2].get(f"/api/conversations/{conversation.pk}/").data["can_reply"] is eligible
    body = {
        "conversation_id": str(conversation.pk),
        "text": "hi",
        "idempotency_key": str(uuid.uuid4()),
    }
    with patch("apps.inbox.tasks.account_client") as provider, patch("apps.inbox.views.enqueue"):
        response = tenant[2].post("/api/messages/send/", body)
        provider.assert_not_called()
        if eligible:
            assert response.status_code == 201 and response.data["status"] == "PENDING"
            assert tenant[2].post("/api/messages/send/", body).status_code == 200
        else:
            assert response.status_code == 400
    assert Message.objects.filter(company=tenant[0], direction="OUTBOUND").count() == int(eligible)


@pytest.mark.parametrize("prior_age", [None, 3600, 90000])
@pytest.mark.parametrize("raw", [None, "bad", "2026-02-30T10:00:00Z", "2026-10-21T10:00:00Z"])
def test_untrusted_history_time_preserves_prior_eligibility(
    conversation, frozen_now, prior_age, raw
):
    prior = None if prior_age is None else frozen_now - timedelta(seconds=prior_age)
    conversation.last_inbound_at = prior
    conversation.save(update_fields=["last_inbound_at"])
    message = store_message(
        conversation, {"id": "invalid", "from": {"id": "psid"}, "created_time": raw}
    )
    conversation.refresh_from_db()
    assert conversation.last_inbound_at == prior
    assert can_reply(conversation) is (prior_age == 3600)
    assert message.sent_at == frozen_now  # Display fallback only.


def test_inbound_time_advances_only_for_newer_customer_messages(conversation, frozen_now):
    original = frozen_now - timedelta(hours=2)
    newer = frozen_now - timedelta(hours=1)
    conversation.last_inbound_at = original
    conversation.save(update_fields=["last_inbound_at"])

    def ingest(mid, time, sender="psid"):
        result = store_message(
            conversation,
            {"id": mid, "from": {"id": sender}, "created_time": time.isoformat()},
            notify=True,
        )
        conversation.refresh_from_db()
        return result

    ingest("new", newer)
    assert conversation.last_inbound_at == newer
    ingest("new", frozen_now)  # Same provider ID with a changed timestamp is still duplicate.
    ingest("older", original)
    ingest("page-echo", frozen_now, "page")
    assert ingest("stranger", frozen_now, "another-customer") is None
    assert conversation.last_inbound_at == newer
    assert conversation.unread_count == 2
    assert Message.objects.filter(conversation=conversation).count() == 3


@pytest.mark.parametrize("history_time", ["old", "missing", "malformed", "future"])
def test_history_import_does_not_reopen_window(account, frozen_now, history_time):
    old = frozen_now - timedelta(days=7)
    raw = {
        "old": old.isoformat(),
        "missing": None,
        "malformed": "bad",
        "future": (frozen_now + timedelta(days=7)).isoformat(),
    }[history_time]
    with patch("apps.inbox.services.account_client") as factory:
        factory.return_value.get_conversations.return_value = [
            {"id": "thread", "participants": {"data": [{"id": "page"}, {"id": "psid"}]}}
        ]
        factory.return_value.get_conversation_messages.return_value = [
            {"id": "historical", "from": {"id": "psid"}, "created_time": raw, "message": "history"}
        ]
        sync_conversations(account)
        sync_conversations(account)
    conversation = Conversation.objects.get(company=account.company)
    assert conversation.last_inbound_at == (old if history_time == "old" else None)
    assert can_reply(conversation) is False
    assert Message.objects.get(conversation=conversation).sent_at == (
        old if history_time == "old" else frozen_now
    )
    assert conversation.unread_count == 1


@pytest.mark.parametrize("state", ["expired", "missing", "future"])
def test_worker_rechecks_time_after_queueing(tenant, conversation, frozen_now, state):
    conversation.last_inbound_at = frozen_now - timedelta(hours=23, minutes=59, seconds=59)
    conversation.save(update_fields=["last_inbound_at"])
    message, _ = create_outbound(tenant[0], conversation.pk, "hi", uuid.uuid4())
    # Model defaults retain the original clock callable; make queue time explicit.
    Message.objects.filter(company=tenant[0], pk=message.pk).update(next_attempt_at=frozen_now)
    if state != "expired":
        conversation.last_inbound_at = (
            None if state == "missing" else frozen_now + timedelta(days=7)
        )
        conversation.save(update_fields=["last_inbound_at"])
    with (
        patch("django.utils.timezone.now", return_value=frozen_now + timedelta(seconds=1)),
        patch("apps.inbox.tasks.account_client") as provider,
    ):
        send_meta_message(str(tenant[0].pk), str(message.pk))
        send_meta_message(str(tenant[0].pk), str(message.pk))
        provider.assert_not_called()
    message.refresh_from_db()
    assert message.status == "FAILED" and message.provider_error == {"code": "MESSAGE_NOT_ELIGIBLE"}
    assert message.attempts == 1
    # A replay returns the same record, never creates a new send after expiry.
    replay, created = create_outbound(
        tenant[0], conversation.pk, "hi", message.client_idempotency_key
    )
    assert replay.pk == message.pk and not created


def test_echo_before_send_result_merges_without_advancing_inbound(tenant, conversation, frozen_now):
    from apps.meta.services.webhooks import process_message

    inbound = frozen_now - timedelta(hours=1)
    conversation.last_inbound_at = inbound
    conversation.save(update_fields=["last_inbound_at"])
    message, _ = create_outbound(tenant[0], conversation.pk, "hi", uuid.uuid4())
    Message.objects.filter(company=tenant[0], pk=message.pk).update(next_attempt_at=frozen_now)

    def provider_send(*args):
        process_message(
            conversation.social_account,
            {
                "sender": {"id": "page"},
                "recipient": {"id": "psid"},
                "timestamp": frozen_now.timestamp() * 1000,
                "message": {"mid": "echo-mid", "text": "hi", "is_echo": True},
            },
        )
        return {"message_id": "echo-mid"}

    with patch("apps.inbox.tasks.account_client") as provider:
        provider.return_value.send_message.side_effect = provider_send
        send_meta_message(str(tenant[0].pk), str(message.pk))
        send_meta_message(str(tenant[0].pk), str(message.pk))
        assert provider.return_value.send_message.call_count == 1
    message.refresh_from_db()
    conversation.refresh_from_db()
    assert message.status == "SENT" and message.external_id == "echo-mid"
    assert Message.objects.filter(conversation=conversation).count() == 1
    assert conversation.last_inbound_at == inbound and conversation.unread_count == 0
