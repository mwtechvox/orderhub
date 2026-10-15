from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.common.provider import (
    as_dict,
    as_iterable,
    as_list,
    media_items,
    provider_id,
    provider_time,
    safe_text,
)
from apps.meta.services.tokens import account_client

from .models import Conversation, Customer, Message

# Local clock-skew allowance, not an extension to Meta's messaging policy.
INBOUND_CLOCK_SKEW = timedelta(seconds=5)
REPLY_WINDOW = timedelta(hours=24)


def trusted_inbound_time(value, *, now):
    timestamp = provider_time(value)
    if timestamp is None or timestamp.timestamp() <= 0 or timestamp > now + INBOUND_CLOCK_SKEW:
        return None
    return timestamp


def can_reply(conversation):
    now = timezone.now()
    timestamp = trusted_inbound_time(conversation.last_inbound_at, now=now)
    # Exactly 24 hours is expired. Future values must pass the same ingestion guard.
    return bool(
        conversation.social_account.status == "ACTIVE"
        and timestamp is not None
        and timestamp > now - REPLY_WINDOW
    )


def resolve_conversation(account, psid, name="", external_id=None):
    psid = provider_id(psid)
    if psid is None:
        return None
    name = safe_text(name)
    external_id = provider_id(external_id)
    customer, _ = Customer.objects.get_or_create(
        company_id=account.company_id,
        social_account=account,
        external_user_id=psid,
        defaults={"name": name},
    )
    if name and customer.name != name:
        customer.name = name
        customer.save(update_fields=["name"])
    conversation, _ = Conversation.objects.get_or_create(
        company_id=account.company_id, social_account=account, customer=customer
    )
    if external_id and conversation.external_id != external_id:
        conversation.external_id = external_id
        conversation.save(update_fields=["external_id"])
    return conversation


@transaction.atomic
def store_message(conversation, data, *, notify=False):
    conversation = Conversation.objects.select_for_update().get(
        pk=conversation.pk, company_id=conversation.company_id
    )
    account = conversation.social_account
    data = as_dict(data)
    external_id = provider_id(data.get("id"))
    sender = provider_id(as_dict(data.get("from")).get("id"))
    if external_id is None or sender is None:
        return None
    if sender not in (account.external_account_id, conversation.customer.external_user_id):
        return None
    inbound = sender != account.external_account_id
    received_at = timezone.now()
    inbound_time = trusted_inbound_time(data.get("created_time"), now=received_at)
    # sent_at is also the UI's display/order field. Its receipt-time fallback
    # must never flow into last_inbound_at (the authorization timestamp).
    display_time = inbound_time or received_at
    message, created = Message.objects.get_or_create(
        company_id=conversation.company_id,
        social_account=account,
        external_id=external_id,
        defaults={
            "conversation": conversation,
            "direction": "INBOUND" if inbound else "OUTBOUND",
            "sender_external_id": sender,
            "recipient_external_id": account.external_account_id
            if inbound
            else conversation.customer.external_user_id,
            "text": safe_text(data.get("message")),
            "attachments": media_items(data.get("attachments", {})),
            "status": "RECEIVED" if inbound else "SENT",
            "sent_at": display_time,
        },
    )
    if created:
        if not conversation.last_message_at or display_time >= conversation.last_message_at:
            conversation.last_message_at = display_time
            conversation.last_message = message.text or "[Хавсралт]"
        if (
            inbound
            and inbound_time is not None
            and (not conversation.last_inbound_at or inbound_time > conversation.last_inbound_at)
        ):
            conversation.last_inbound_at = inbound_time
        if notify and inbound:
            conversation.unread_count += 1
        conversation.save()
    return message


def sync_conversations(account):
    client = account_client(account)
    for raw_data in as_iterable(client.get_conversations(account.external_account_id)):
        data = as_dict(raw_data)
        external_id = provider_id(data.get("id"))
        participants = as_list(as_dict(data.get("participants")).get("data"))
        customers = []
        for raw_person in participants:
            person = as_dict(raw_person)
            psid = provider_id(person.get("id"))
            if psid and psid != account.external_account_id:
                customers.append((psid, safe_text(person.get("name"))))
        if external_id is None or len(customers) != 1:
            continue  # This MVP supports Page/customer conversations only.
        psid, name = customers[0]
        conversation = resolve_conversation(account, psid, name, external_id)
        if conversation is None:
            continue
        for message in as_iterable(client.get_conversation_messages(external_id)):
            store_message(conversation, message, notify=True)
        Conversation.objects.filter(pk=conversation.pk, company_id=account.company_id).update(
            last_synced_at=timezone.now()
        )


@transaction.atomic
def create_outbound(company, conversation_id, text, idempotency_key):
    # A tenant row lock serializes competing uses of the same idempotency key.
    from django.shortcuts import get_object_or_404

    from apps.companies.models import Company

    Company.objects.select_for_update().get(pk=company.pk)
    conversation = get_object_or_404(
        Conversation.objects.select_related("social_account", "customer"),
        pk=conversation_id,
        company=company,
    )
    existing = Message.objects.filter(
        company=company, client_idempotency_key=idempotency_key
    ).first()
    if existing:
        if existing.conversation_id != conversation.pk or existing.text != text:
            raise ValidationError("Idempotency key өөр хүсэлтэд ашиглагдсан байна.")
        return existing, False
    if conversation.social_account.status != "ACTIVE":
        raise ValidationError("Facebook хуудсаа дахин холбоно уу.")
    if not can_reply(conversation):
        raise ValidationError(
            "Сүүлийн хэрэглэгчийн мессежээс хойш 24 цаг өнгөрсөн. Шинэ мессеж ирсний дараа хариулна уу."
        )
    return Message.objects.create(
        company=company,
        conversation=conversation,
        social_account=conversation.social_account,
        client_idempotency_key=idempotency_key,
        text=text,
        direction="OUTBOUND",
        status="PENDING",
        sender_external_id=conversation.social_account.external_account_id,
        recipient_external_id=conversation.customer.external_user_id,
    ), True
