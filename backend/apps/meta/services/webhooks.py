import hashlib
import hmac
import json

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.common.provider import as_dict, as_list, provider_id, provider_time, safe_text
from apps.inbox.services import resolve_conversation, store_message
from apps.meta.models import RawWebhookEvent, SocialAccount
from apps.social.models import Comment, Post
from apps.social.services import schedule_comment_automation, upsert_comment


def verify_signature(raw, signature):
    if not settings.META_APP_SECRET or not signature:
        return False
    expected = (
        "sha256=" + hmac.new(settings.META_APP_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    )
    return hmac.compare_digest(expected, signature)


@transaction.atomic
def persist_events(payload):
    events = []
    payload = as_dict(payload)
    entries = as_list(payload.get("entry"))
    if not entries:
        entries = [{}]
    for raw_entry in entries:
        entry = as_dict(raw_entry)
        page_id = provider_id(entry.get("id")) or ""
        accounts = (
            list(
                SocialAccount.objects.filter(
                    platform="FACEBOOK_PAGE", external_account_id=page_id, status="ACTIVE"
                )
            )
            if payload.get("object") == "page"
            else []
        )
        # Unknown account/object stays quarantined and has no tenant-facing API.
        for account in accounts or [None]:
            envelope = {**payload, "entry": [entry]}
            identity = json.dumps(envelope, sort_keys=True, separators=(",", ":")) + str(
                account.pk if account else ""
            )
            event, created = RawWebhookEvent.objects.get_or_create(
                dedupe_key=hashlib.sha256(identity.encode()).hexdigest(),
                defaults={
                    "company": account.company if account else None,
                    "social_account": account,
                    "external_account_id": page_id,
                    "object_type": (safe_text(payload.get("object")) or "unknown")[:100],
                    "payload": envelope,
                    "status": "RECEIVED" if account else "IGNORED",
                },
            )
            if created and account:
                events.append(event)
    return events


def process_message(account, event):
    event = as_dict(event)
    message = as_dict(event.get("message"))
    message_id = provider_id(message.get("mid"))
    if message_id is None:
        return False
    sender = provider_id(as_dict(event.get("sender")).get("id"))
    recipient = provider_id(as_dict(event.get("recipient")).get("id"))
    if sender is None or recipient is None:
        return False
    echo = message.get("is_echo") is True
    if echo:
        if sender != account.external_account_id:
            return False
        psid = recipient
    else:
        if recipient != account.external_account_id:
            return False
        psid = sender
    if psid is None:
        return False
    conversation = resolve_conversation(account, psid)
    if conversation is None:
        return False
    timestamp = provider_time(event.get("timestamp"), milliseconds=True)
    return (
        store_message(
            conversation,
            {
                "id": message_id,
                "message": safe_text(message.get("text")),
                "from": {"id": sender},
                "created_time": timestamp,
                "attachments": message.get("attachments", []),
            },
            notify=not echo,
        )
        is not None
    )


def process_change(account, change, entry_time):
    change = as_dict(change)
    if change.get("field") != "feed" or not isinstance(change.get("value"), dict):
        return False
    value = change["value"]
    if value.get("item") != "comment":
        if value.get("item") == "post" and value.get("verb") in ("remove", "delete"):
            post_id = provider_id(value.get("post_id"))
            if post_id:
                Post.objects.filter(
                    company_id=account.company_id,
                    social_account=account,
                    external_id=post_id,
                ).delete()
        # Periodic reconciliation refreshes post/reaction changes via the Graph API.
        SocialAccount.objects.filter(pk=account.pk, company_id=account.company_id).filter(
            status="ACTIVE", sync_status="IDLE"
        ).update(sync_status="QUEUED")
        return True
    comment_id = provider_id(value.get("comment_id"))
    post_id = provider_id(value.get("post_id"))
    if comment_id is None or post_id is None:
        return False
    post, _ = Post.objects.get_or_create(
        company_id=account.company_id,
        social_account=account,
        external_id=post_id,
        # Non-authorization display fallback for social placeholders only.
        defaults={
            "created_at_platform": provider_time(value.get("created_time")) or timezone.now()
        },
    )
    # Retain the report/current integration's numeric-millisecond convention.
    # The shared writer rejects invalid/future times; receipt time is never ordering.
    event_at = provider_time(entry_time, milliseconds=True)
    if value.get("verb") in ("remove", "delete"):
        upsert_comment(
            post,
            {"id": comment_id, "created_time": value.get("created_time")},
            event_at=event_at,
            deleted=True,
        )
        return True
    parent = None
    parent_id = provider_id(value.get("parent_id"))
    if parent_id and parent_id != post.external_id and parent_id != comment_id:
        parent, _ = Comment.objects.get_or_create(
            company_id=account.company_id,
            social_account=account,
            external_id=parent_id,
            defaults={
                "post": post,
                "created_at_platform": provider_time(value.get("created_time")) or timezone.now(),
            },
        )
    comment = upsert_comment(
        post,
        {
            "id": comment_id,
            "message": safe_text(value.get("message")),
            "from": as_dict(value.get("from"))
            or {
                "id": provider_id(value.get("sender_id")) or "",
                "name": safe_text(value.get("sender_name")),
            },
            "created_time": value.get("created_time"),
        },
        parent,
        event_at=event_at,
    )
    if (
        value.get("verb") == "add"
        and comment is not None
        and provider_time(value.get("created_time")) is not None
    ):
        schedule_comment_automation(comment)
    SocialAccount.objects.filter(pk=account.pk, company_id=account.company_id).filter(
        status="ACTIVE", sync_status="IDLE"
    ).update(sync_status="QUEUED")
    return True


def process_payload(event):
    account = SocialAccount.objects.filter(
        pk=event.social_account_id, company_id=event.company_id, status="ACTIVE"
    ).first()
    if not account or event.object_type != "page":
        return False
    handled = False
    payload = as_dict(event.payload)
    for raw_entry in as_list(payload.get("entry")):
        entry = as_dict(raw_entry)
        for message in as_list(entry.get("messaging")):
            if isinstance(message, dict):
                handled = process_message(account, message) or handled
        for change in as_list(entry.get("changes")):
            if isinstance(change, dict):
                handled = process_change(account, change, entry.get("time")) or handled
    return handled
