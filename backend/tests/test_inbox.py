import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.companies.models import Company
from apps.inbox.models import Message
from apps.inbox.services import create_outbound, sync_conversations
from apps.inbox.tasks import send_meta_message
from apps.meta.exceptions import MetaAuthError, MetaDeliveryUnknown, MetaRateLimitError

pytestmark = pytest.mark.django_db


def test_send_pending_sent_idempotent(tenant, conversation):
    company, _, client = tenant
    body = {
        "conversation_id": str(conversation.pk),
        "text": "Сайн байна уу?",
        "idempotency_key": str(uuid.uuid4()),
    }
    response = client.post("/api/messages/send/", body)
    assert response.status_code == 201 and response.data["status"] == "PENDING"
    assert client.post("/api/messages/send/", body).status_code == 200
    assert client.post("/api/messages/send/", {**body, "text": "different"}).status_code == 400
    message = Message.objects.get(company=company)
    with patch("apps.inbox.tasks.account_client") as factory:

        def sent(*args):
            message.refresh_from_db()
            assert message.status == "SENDING"
            return {"message_id": "mid-1"}

        factory.return_value.send_message.side_effect = sent
        send_meta_message(str(company.pk), str(message.pk))
        send_meta_message(str(company.pk), str(message.pk))
        assert factory.return_value.send_message.call_count == 1
    message.refresh_from_db()
    assert message.status == "SENT" and message.external_id == "mid-1"


@pytest.mark.parametrize("error", [MetaAuthError(), MetaDeliveryUnknown()])
def test_send_failure(tenant, conversation, error):
    message, _ = create_outbound(tenant[0], conversation.pk, "hi", uuid.uuid4())
    with patch("apps.inbox.tasks.account_client") as factory:
        factory.return_value.send_message.side_effect = error
        send_meta_message(str(tenant[0].pk), str(message.pk))
    message.refresh_from_db()
    assert message.status == "FAILED"
    if isinstance(error, MetaAuthError):
        conversation.social_account.refresh_from_db()
        assert conversation.social_account.status == "NEEDS_REAUTH"


def test_rate_limit_pending_then_failed(tenant, conversation):
    message, _ = create_outbound(tenant[0], conversation.pk, "hi", uuid.uuid4())
    with patch("apps.inbox.tasks.account_client") as factory:
        factory.return_value.send_message.side_effect = MetaRateLimitError(retry_after=30)
        send_meta_message(str(tenant[0].pk), str(message.pk))
        message.refresh_from_db()
        assert message.status == "PENDING" and message.next_attempt_at > timezone.now()
        Message.objects.filter(pk=message.pk, company=tenant[0]).update(
            attempts=4, next_attempt_at=timezone.now()
        )
        send_meta_message(str(tenant[0].pk), str(message.pk))
    message.refresh_from_db()
    assert message.status == "FAILED"


def test_window_and_arbitrary_ids(tenant, conversation):
    client = tenant[2]
    body = {
        "conversation_id": str(conversation.pk),
        "text": "hi",
        "idempotency_key": str(uuid.uuid4()),
    }
    assert client.post("/api/messages/send/", {**body, "page_id": "evil"}).status_code == 400
    conversation.last_inbound_at = timezone.now() - timedelta(hours=25)
    conversation.save()
    assert client.post("/api/messages/send/", body).status_code == 400


def test_cross_tenant_conversation_send(tenant, conversation):
    client = tenant[2]
    other = Company.objects.create(name="Other", slug="other")
    from django.contrib.auth import get_user_model

    from apps.companies.models import CompanyMembership

    outsider = get_user_model().objects.create_user("other")
    CompanyMembership.objects.create(company=other, user=outsider)
    client.force_login(outsider)
    client.credentials(HTTP_X_COMPANY_ID=str(other.pk))
    assert client.get(f"/api/conversations/{conversation.pk}/").status_code == 404
    assert client.get(f"/api/conversations/{conversation.pk}/messages/").status_code == 404
    assert (
        client.post(
            "/api/messages/send/",
            {
                "conversation_id": str(conversation.pk),
                "text": "hack",
                "idempotency_key": str(uuid.uuid4()),
            },
        ).status_code
        == 404
    )


def test_sync_participants_and_history(tenant, account):
    with patch("apps.inbox.services.account_client") as factory:
        factory.return_value.get_conversations.return_value = [
            {
                "id": "thread",
                "participants": {"data": [{"id": "psid", "name": "Бат"}, {"id": "page"}]},
            }
        ]
        factory.return_value.get_conversation_messages.return_value = [
            {
                "id": "mid",
                "from": {"id": "psid"},
                "message": "hi",
                "created_time": timezone.now().isoformat(),
            }
        ]
        sync_conversations(account)
        sync_conversations(account)
    assert Message.objects.count() == 1
    result = tenant[2].get("/api/conversations/").data["results"][0]
    assert result["customer"]["name"] == "Бат" and result["unread_count"] == 1


def test_conversation_platform_and_account_filters_are_tenant_scoped(tenant, account, conversation):
    payload = (
        tenant[2]
        .get(f"/api/conversations/?platform=FACEBOOK_PAGE&social_account={account.pk}")
        .data["results"]
    )
    assert [item["id"] for item in payload] == [str(conversation.pk)]
    assert payload[0]["platform"] == "FACEBOOK_PAGE"
    assert tenant[2].get("/api/conversations/?social_account=invalid").status_code == 400


def test_disconnected_account_cannot_reply(tenant, conversation):
    from apps.inbox.serializers import ConversationSerializer

    conversation.social_account.status = "DISCONNECTED"
    conversation.social_account.save()
    assert ConversationSerializer(conversation).data["can_reply"] is False
