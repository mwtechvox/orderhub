import random
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.meta.exceptions import MetaError, MetaRateLimitError
from apps.meta.models import SocialAccount
from apps.meta.services.tokens import account_client, mark_auth_failure

from .models import Conversation, Message
from .services import can_reply


@shared_task
def send_meta_message(company_id, message_id):
    claimed = Message.objects.filter(
        company_id=company_id, pk=message_id, status="PENDING", next_attempt_at__lte=timezone.now()
    ).update(status="SENDING", updated_at=timezone.now(), attempts=F("attempts") + 1)
    if not claimed:
        return
    message = Message.objects.select_related("conversation__customer", "social_account").get(
        company_id=company_id, pk=message_id
    )
    account = message.social_account
    if account.status != "ACTIVE" or not can_reply(message.conversation):
        Message.objects.filter(company_id=company_id, pk=message_id).update(
            status="FAILED", provider_error={"code": "MESSAGE_NOT_ELIGIBLE"}
        )
        return
    try:
        result = account_client(account).send_message(
            account.external_account_id,
            message.conversation.customer.external_user_id,
            message.text,
        )
        mid = result.get("message_id")
        if not mid:
            from apps.meta.exceptions import MetaDeliveryUnknown

            raise MetaDeliveryUnknown()
        with transaction.atomic():
            # An echo can arrive before this task commits. Merge that known provider ID.
            Conversation.objects.select_for_update().get(
                pk=message.conversation_id, company_id=company_id
            )
            Message.objects.filter(
                company_id=company_id,
                social_account=account,
                external_id=mid,
                client_idempotency_key__isnull=True,
                direction="OUTBOUND",
            ).exclude(pk=message_id).delete()
            Message.objects.filter(company_id=company_id, pk=message_id).update(
                external_id=mid,
                status="SENT",
                provider_error=None,
                sent_at=timezone.now(),
                updated_at=timezone.now(),
            )
            Conversation.objects.filter(company_id=company_id, pk=message.conversation_id).update(
                last_message=message.text, last_message_at=timezone.now()
            )
    except MetaRateLimitError as error:
        # An explicit rejection can safely retry; ambiguous delivery never does.
        if message.attempts < 5:
            Message.objects.filter(company_id=company_id, pk=message_id).update(
                status="PENDING",
                provider_error=error.safe_payload,
                next_attempt_at=timezone.now()
                + timedelta(
                    seconds=max(error.retry_after, 2**message.attempts + random.uniform(0, 3))
                ),
                updated_at=timezone.now(),
            )
        else:
            Message.objects.filter(company_id=company_id, pk=message_id).update(
                status="FAILED", provider_error=error.safe_payload
            )
    except MetaError as error:
        mark_auth_failure(account, error)
        Message.objects.filter(company_id=company_id, pk=message_id).update(
            status="FAILED", provider_error=error.safe_payload, updated_at=timezone.now()
        )


@shared_task
def dispatch_pending_messages():
    # A crash after sending cannot be retried safely without provider idempotency.
    Message.objects.filter(
        status="SENDING", updated_at__lt=timezone.now() - timedelta(minutes=20)
    ).update(status="FAILED", provider_error={"code": "META_DELIVERY_UNKNOWN"})
    for company_id, pk in Message.objects.filter(
        status="PENDING", next_attempt_at__lte=timezone.now()
    ).values_list("company_id", "pk")[:500]:
        send_meta_message.delay(str(company_id), str(pk))


@shared_task
def sync_account_conversations(company_id, account_id):
    from .services import sync_conversations

    account = SocialAccount.objects.get(company_id=company_id, pk=account_id)
    if account.status == "ACTIVE":
        try:
            sync_conversations(account)
        except MetaError as error:
            mark_auth_failure(account, error)
            raise
