import logging

from celery import shared_task
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import RawWebhookEvent
from .services.webhooks import process_payload

logger = logging.getLogger(__name__)


@shared_task
def process_webhook_event(company_id, event_id):
    try:
        with transaction.atomic():
            event = RawWebhookEvent.objects.select_for_update().get(
                company_id=company_id, pk=event_id
            )
            if event.status in ("PROCESSED", "IGNORED") or event.attempts >= 5:
                return
            event.attempts += 1
            event.status = "PROCESSING"
            event.save(update_fields=["attempts", "status"])
            handled = process_payload(event)
            event.status = "PROCESSED" if handled else "IGNORED"
            event.processed_at = timezone.now()
            event.error = ""
            event.save(update_fields=["status", "processed_at", "error"])
    except Exception:
        # Never log payloads, tokens, customer text, or unsanitized exception values.
        RawWebhookEvent.objects.filter(company_id=company_id, pk=event_id).update(
            status="FAILED", error="PROCESSING_FAILED", attempts=F("attempts") + 1
        )
        logger.warning("webhook_processing_failed event_id=%s", event_id)


@shared_task
def dispatch_webhooks():
    for company_id, event_id in RawWebhookEvent.objects.filter(
        status__in=["RECEIVED", "FAILED"], company__isnull=False, attempts__lt=5
    ).values_list("company_id", "id")[:500]:
        process_webhook_event.delay(str(company_id), str(event_id))


# A sync cycle stops after five failed runs, even if beat keeps running.
MAX_SYNC_FAILURES = 5


def automatic_accounts():
    from .models import SocialAccount

    # FAILED + no next attempt means operator action, not an immediately due job.
    return SocialAccount.objects.filter(status="ACTIVE").exclude(
        sync_status="FAILED", next_sync_at__isnull=True
    )


@shared_task
def sync_account(company_id, account_id):
    import random
    from datetime import timedelta

    from django.db.models import Q

    from apps.inbox.services import sync_conversations
    from apps.meta.exceptions import MetaError, MetaErrorKind
    from apps.social.services import sync_feed

    from .models import SocialAccount

    now = timezone.now()
    claimed = (
        automatic_accounts()
        .filter(company_id=company_id, pk=account_id)
        .exclude(sync_status="RUNNING")
        .filter(Q(sync_status="QUEUED") | Q(next_sync_at__isnull=True) | Q(next_sync_at__lte=now))
        .update(sync_status="RUNNING", sync_started_at=now)
    )
    if not claimed:
        return
    account = SocialAccount.objects.get(company_id=company_id, pk=account_id)
    # A concurrent reconnect/disconnect or another worker must own its own result.
    current = SocialAccount.objects.filter(
        company_id=company_id,
        pk=account_id,
        status="ACTIVE",
        encrypted_access_token=account.encrypted_access_token,
        sync_started_at=now,
        sync_status="RUNNING",
    )
    errors = []
    for sync in (sync_feed, sync_conversations):
        if not current.exists():
            return
        try:
            sync(account)
        except MetaError as error:
            errors.append(error)
            if error.kind == MetaErrorKind.AUTH_REQUIRED:
                break  # No further capability can safely use this credential.
        except Exception:
            # Unexpected local failures are not assumed to be retryable Meta errors.
            errors.append(MetaError())
            logger.warning("account_sync_failed account_id=%s", account_id)

    if not errors:
        current.update(
            sync_status="IDLE",
            sync_failures=0,
            last_synced_at=timezone.now(),
            last_error="",
            next_sync_at=timezone.now() + timedelta(minutes=5),
        )
        return

    # Keep the most actionable failure; success in one domain never erases another's error.
    priority = {
        MetaErrorKind.AUTH_REQUIRED: 0,
        MetaErrorKind.PERMISSION_REQUIRED: 1,
        MetaErrorKind.PERMANENT_OTHER: 2,
        MetaErrorKind.RETRYABLE: 3,
    }
    error = min(errors, key=lambda item: priority[item.kind])
    failures = min(account.sync_failures + 1, MAX_SYNC_FAILURES)
    next_sync = None
    if error.kind == MetaErrorKind.RETRYABLE and failures < MAX_SYNC_FAILURES:
        delay = max(max(item.retry_after for item in errors), 300 * 2 ** (failures - 1))
        next_sync = timezone.now() + timedelta(seconds=delay + random.uniform(0, 3))
    current.update(
        status=(
            "NEEDS_REAUTH"
            if error.kind in (MetaErrorKind.AUTH_REQUIRED, MetaErrorKind.PERMISSION_REQUIRED)
            else "ACTIVE"
        ),
        sync_status="FAILED",
        sync_failures=failures,
        last_error=error.code,
        next_sync_at=next_sync,
    )


@shared_task
def periodic_sync():
    from datetime import timedelta

    from django.db.models import Q

    automatic_accounts().filter(
        sync_status="RUNNING", sync_started_at__lt=timezone.now() - timedelta(minutes=20)
    ).update(sync_status="QUEUED")
    query = (
        automatic_accounts()
        .exclude(sync_status="RUNNING")
        .filter(
            Q(sync_status="QUEUED")
            | Q(next_sync_at__isnull=True)
            | Q(next_sync_at__lte=timezone.now())
        )
    )
    for company_id, account_id in query.values_list("company_id", "pk"):
        sync_account.delay(str(company_id), str(account_id))


@shared_task
def check_token_health(company_id, account_id):
    from apps.meta.exceptions import MetaError, MetaErrorKind
    from apps.meta.services.tokens import account_client, mark_auth_failure

    from .models import SocialAccount

    account = SocialAccount.objects.get(company_id=company_id, pk=account_id)
    if not automatic_accounts().filter(company_id=company_id, pk=account_id).exists():
        return
    try:
        account_client(account).health(account.external_account_id)
    except MetaError as error:
        mark_auth_failure(account, error)
        updates = {"last_error": error.code}
        if error.kind == MetaErrorKind.PERMANENT_OTHER:
            updates.update(sync_status="FAILED", next_sync_at=None)
        SocialAccount.objects.filter(
            company_id=company_id,
            pk=account_id,
            status="ACTIVE",
            encrypted_access_token=account.encrypted_access_token,
        ).update(**updates)
    SocialAccount.objects.filter(company_id=company_id, pk=account_id).update(
        last_token_check_at=timezone.now()
    )


@shared_task
def daily_maintenance():
    from datetime import timedelta

    from .models import OAuthAttempt, PageSelection

    for company_id, account_id in automatic_accounts().values_list("company_id", "pk"):
        check_token_health.delay(str(company_id), str(account_id))
    OAuthAttempt.objects.filter(expires_at__lt=timezone.now()).delete()
    PageSelection.objects.filter(expires_at__lt=timezone.now()).delete()
    RawWebhookEvent.objects.filter(received_at__lt=timezone.now() - timedelta(days=30)).delete()
