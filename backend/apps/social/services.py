from datetime import timedelta
from uuid import UUID, uuid5

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.common.provider import (
    as_dict,
    as_iterable,
    media_items,
    provider_id,
    provider_time,
    safe_bool,
    safe_count,
    safe_text,
    safe_url,
)
from apps.common.queue import enqueue
from apps.meta.exceptions import MetaDeliveryUnknown, MetaError
from apps.meta.services.tokens import account_client, mark_auth_failure

from .models import (
    Comment,
    CommentAutomationRule,
    CommentPrivateReplyAttempt,
    CommentReplyAttempt,
    Post,
    SocialPostCommentAutomation,
)

AUTOMATION_KEY_NAMESPACE = UUID("720f6d4f-24ba-4fe1-9dc3-90d5245f8630")
PRIVATE_REPLY_WINDOW = timedelta(days=7)


def upsert_post(account, data):
    data = as_dict(data)
    external_id = provider_id(data.get("id"))
    if external_id is None:
        return None
    comments = as_dict(data.get("comments"))
    reactions = as_dict(data.get("reactions"))
    created_at = provider_time(data.get("created_time")) or timezone.now()
    return Post.objects.update_or_create(
        company_id=account.company_id,
        social_account=account,
        external_id=external_id,
        defaults={
            "message": safe_text(data.get("message")),
            "permalink_url": safe_url(data.get("permalink_url", "")),
            "media": media_items(data.get("attachments", {})),
            # Social display timestamps never authorize Messenger replies.
            "created_at_platform": created_at,
            "published_at": created_at,
            "comment_count": safe_count(as_dict(comments.get("summary")).get("total_count")),
            "reaction_count": safe_count(as_dict(reactions.get("summary")).get("total_count")),
        },
    )[0]


def run_post_publication(company_id, post_id):
    """Claim and publish one locally authored post exactly once."""

    now = timezone.now()
    with transaction.atomic():
        post = (
            Post.objects.select_for_update()
            .select_related("social_account")
            .filter(company_id=company_id, pk=post_id)
            .first()
        )
        if (
            not post
            or post.origin != Post.Origin.ORDERHUB
            or post.status != Post.Status.SCHEDULED
            or not post.scheduled_at
            or post.scheduled_at > now
        ):
            return
        if post.social_account.status != "ACTIVE":
            post.status = Post.Status.FAILED
            post.provider_error = {"code": "ACCOUNT_INACTIVE"}
            post.save(update_fields=["status", "provider_error", "updated_at"])
            return
        # A crash or lost response after this commit is terminally ambiguous.
        post.status = Post.Status.DELIVERY_UNKNOWN
        post.provider_error = None
        post.save(update_fields=["status", "provider_error", "updated_at"])

    image_url = post.media[0]["url"] if post.media else ""
    try:
        result = account_client(post.social_account).create_page_post(
            post.social_account.external_account_id, post.message, image_url
        )
        external_id = provider_id(as_dict(result).get("id"))
        if external_id is None:
            raise MetaDeliveryUnknown()
    except MetaDeliveryUnknown as error:
        Post.objects.filter(pk=post.pk, company_id=post.company_id).update(
            provider_error=error.safe_payload, updated_at=timezone.now()
        )
    except MetaError as error:
        mark_auth_failure(post.social_account, error)
        Post.objects.filter(pk=post.pk, company_id=post.company_id).update(
            status=Post.Status.FAILED,
            provider_error=error.safe_payload,
            updated_at=timezone.now(),
        )
    except Exception:
        Post.objects.filter(pk=post.pk, company_id=post.company_id).update(
            provider_error={"code": MetaDeliveryUnknown.code}, updated_at=timezone.now()
        )
    else:
        published_at = timezone.now()
        Post.objects.filter(pk=post.pk, company_id=post.company_id).update(
            external_id=external_id,
            status=Post.Status.PUBLISHED,
            provider_error=None,
            published_at=published_at,
            created_at_platform=published_at,
            updated_at=published_at,
        )


@transaction.atomic
def upsert_comment(post, data, parent=None, *, event_at=None, deleted=False):
    """Serialize comment snapshots/events, including first-seen deletions.

    Creation time is display metadata, never a revision. An unversioned snapshot
    cannot supersede a timed webhook. Deletion is terminal for this provider ID:
    no restore contract is verified here, even for a later add/edit notification.
    """
    data = as_dict(data)
    external_id = provider_id(data.get("id"))
    if external_id is None:
        return None
    event_at = provider_time(event_at)
    if event_at and (event_at.timestamp() <= 0 or event_at > timezone.now() + timedelta(seconds=5)):
        event_at = None
    created_at = provider_time(data.get("created_time"))
    # The unique account/external-ID constraint handles concurrent first inserts;
    # select_for_update also locks the row returned after a get_or_create collision.
    comment, _ = Comment.objects.select_for_update().get_or_create(
        company_id=post.company_id,
        social_account=post.social_account,
        external_id=external_id,
        defaults={"post": post, "created_at_platform": created_at or timezone.now()},
    )
    if deleted:
        comment.is_deleted = True
        comment.can_reply = False
        comment.message = ""
        if event_at and (not comment.last_event_at or event_at > comment.last_event_at):
            comment.last_event_at = event_at
        comment.save(update_fields=["is_deleted", "can_reply", "message", "last_event_at"])
        return comment
    if comment.is_deleted:
        return comment
    if comment.last_event_at and (event_at is None or event_at <= comment.last_event_at):
        return comment

    author = as_dict(data.get("from"))
    comment.post = post
    comment.parent_comment = parent
    comment.author_external_id = provider_id(author.get("id")) or ""
    comment.author_name = safe_text(author.get("name"))
    comment.message = safe_text(data.get("message"))
    comment.can_reply = safe_bool(data.get("can_comment"), default=True)
    if created_at:
        comment.created_at_platform = created_at
    if event_at:
        comment.last_event_at = event_at
    comment.save(
        update_fields=[
            "post",
            "parent_comment",
            "author_external_id",
            "author_name",
            "message",
            "can_reply",
            "created_at_platform",
            "last_event_at",
        ]
    )
    return comment


def sync_comments(post, client=None):
    client = client or account_client(post.social_account)
    for data in as_iterable(client.get_post_comments(post.external_id)):
        comment = upsert_comment(post, data)
        if comment is None or comment.is_deleted:
            continue
        for reply in as_iterable(client.get_comment_replies(comment.external_id)):
            upsert_comment(post, reply, parent=comment)


def sync_feed(account):
    client = account_client(account)
    for data in as_iterable(client.get_page_feed(account.external_account_id)):
        post = upsert_post(account, data)
        if post is not None:
            sync_comments(post, client)


def _save_reply_outcome(attempt, status, *, provider_reply_id="", provider_error=None):
    CommentReplyAttempt.objects.filter(pk=attempt.pk, company_id=attempt.company_id).update(
        status=status,
        provider_reply_id=provider_reply_id,
        provider_error=provider_error,
        updated_at=timezone.now(),
    )
    attempt.refresh_from_db()
    return attempt


def _execute_public_reply(attempt, comment):
    """Perform the one allowed provider write for a durable public attempt."""

    try:
        result = account_client(comment.social_account).reply_to_comment(
            comment.external_id, attempt.text
        )
        reply_id = provider_id(as_dict(result).get("id"))
        if reply_id is None:
            raise MetaDeliveryUnknown()
        # A local write failure after Meta accepts the request is also ambiguous.
        upsert_comment(
            comment.post,
            {
                "id": reply_id,
                "message": attempt.text,
                "from": {
                    "id": comment.social_account.external_account_id,
                    "name": comment.social_account.display_name,
                },
                "created_time": timezone.now().isoformat(),
            },
            parent=comment,
        )
    except MetaDeliveryUnknown as error:
        return _save_reply_outcome(
            attempt,
            CommentReplyAttempt.Status.DELIVERY_UNKNOWN,
            provider_error=error.safe_payload,
        )
    except MetaError as error:
        mark_auth_failure(comment.social_account, error)
        return _save_reply_outcome(
            attempt, CommentReplyAttempt.Status.FAILED, provider_error=error.safe_payload
        )
    except Exception:
        return _save_reply_outcome(
            attempt,
            CommentReplyAttempt.Status.DELIVERY_UNKNOWN,
            provider_error={"code": MetaDeliveryUnknown.code},
        )
    return _save_reply_outcome(attempt, CommentReplyAttempt.Status.SENT, provider_reply_id=reply_id)


def reply(comment, text, idempotency_key):
    """Send one comment reply and retain an unambiguous outcome.

    The row is committed as DELIVERY_UNKNOWN *before* the provider write. A
    process crash after Meta accepts the write therefore remains conservative:
    the same key returns the existing unknown attempt and never sends again.
    """
    with transaction.atomic():
        comment = (
            Comment.objects.select_for_update()
            .select_related("social_account", "post")
            .get(company_id=comment.company_id, pk=comment.pk)
        )
        existing = CommentReplyAttempt.objects.filter(
            company_id=comment.company_id,
            comment=comment,
            client_idempotency_key=idempotency_key,
        ).first()
        if existing:
            if existing.text != text:
                raise ValidationError("Idempotency key өөр хүсэлтэд ашиглагдсан байна.")
            return existing, False
        # A fresh browser key must not bypass an earlier ambiguous provider write.
        # Reconciliation/resolution is intentionally a later, explicit workflow.
        unresolved = (
            CommentReplyAttempt.objects.filter(
                company_id=comment.company_id,
                comment=comment,
                status__in=[
                    CommentReplyAttempt.Status.PENDING,
                    CommentReplyAttempt.Status.DELIVERY_UNKNOWN,
                ],
            )
            .order_by("-updated_at", "-id")
            .first()
        )
        if unresolved:
            if unresolved.status == CommentReplyAttempt.Status.PENDING:
                raise ValidationError("Автомат хариу илгээх дараалалд байна.")
            return unresolved, False
        if comment.is_deleted:
            raise ValidationError("Устгасан сэтгэгдэлд хариулах боломжгүй.")
        if not comment.can_reply:
            raise ValidationError("Энэ сэтгэгдэлд хариулах боломжгүй.")
        if comment.social_account.status != "ACTIVE":
            raise ValidationError("Facebook хуудсаа дахин холбоно уу.")
        attempt = CommentReplyAttempt.objects.create(
            company_id=comment.company_id,
            comment=comment,
            social_account=comment.social_account,
            text=text,
            client_idempotency_key=idempotency_key,
            # Until a response is safely recorded, delivery must be treated as unknown.
            status=CommentReplyAttempt.Status.DELIVERY_UNKNOWN,
        )

    return _execute_public_reply(attempt, comment), True


def automation_eligible(comment):
    """V1 handles only new top-level customer comments on an active Page."""

    now = timezone.now()
    return bool(
        not comment.is_deleted
        and comment.parent_comment_id is None
        and comment.can_reply
        and comment.author_external_id
        and comment.author_external_id != comment.social_account.external_account_id
        and now - PRIVATE_REPLY_WINDOW < comment.created_at_platform <= now + timedelta(seconds=5)
        and comment.social_account.platform == "FACEBOOK_PAGE"
        and comment.social_account.status == "ACTIVE"
    )


def effective_automation_rule(comment):
    """Resolve explicit post override before the Page default.

    An existing disabled post rule is an explicit opt-out and therefore blocks
    fallback to an enabled Page-level rule.
    """

    try:
        post_rule = comment.post.comment_automation
    except SocialPostCommentAutomation.DoesNotExist:
        post_rule = None
    if post_rule is not None:
        return post_rule if post_rule.is_enabled else None
    return CommentAutomationRule.objects.filter(
        company_id=comment.company_id,
        social_account=comment.social_account,
        is_enabled=True,
    ).first()


def _rule_links(rule):
    if isinstance(rule, SocialPostCommentAutomation):
        return {"automation_rule": None, "post_automation_rule": rule}
    return {"automation_rule": rule, "post_automation_rule": None}


def _automatic_attempts():
    return Q(automation_rule__isnull=False) | Q(post_automation_rule__isnull=False)


@transaction.atomic
def schedule_comment_automation(comment):
    """Persist action snapshots, then enqueue after the webhook transaction commits."""

    comment = (
        Comment.objects.select_for_update()
        .select_related("social_account", "post")
        .get(company_id=comment.company_id, pk=comment.pk)
    )
    if not automation_eligible(comment):
        return False
    rule = effective_automation_rule(comment)
    if not rule:
        return False
    links = _rule_links(rule)

    created = False
    if rule.public_reply_enabled and rule.public_reply_text.strip():
        _, was_created = CommentReplyAttempt.objects.get_or_create(
            company_id=comment.company_id,
            comment=comment,
            defaults={
                "social_account": comment.social_account,
                **links,
                "text": rule.public_reply_text.strip(),
                "client_idempotency_key": uuid5(AUTOMATION_KEY_NAMESPACE, f"public:{comment.pk}"),
                "status": CommentReplyAttempt.Status.PENDING,
            },
        )
        created = created or was_created
    if rule.private_reply_enabled and rule.private_reply_text.strip():
        _, was_created = CommentPrivateReplyAttempt.objects.get_or_create(
            company_id=comment.company_id,
            comment=comment,
            defaults={
                "social_account": comment.social_account,
                **links,
                "message": rule.private_reply_text.strip(),
                "status": CommentPrivateReplyAttempt.Status.PENDING,
            },
        )
        created = created or was_created
    if created:
        from .tasks import process_comment_automation

        transaction.on_commit(
            lambda: enqueue(process_comment_automation, str(comment.company_id), str(comment.pk))
        )
    return created


def _fail_pending_automation(comment, code):
    error = {"code": code}
    CommentReplyAttempt.objects.filter(
        company_id=comment.company_id,
        comment=comment,
        status=CommentReplyAttempt.Status.PENDING,
    ).filter(_automatic_attempts()).update(
        status=CommentReplyAttempt.Status.FAILED, provider_error=error
    )
    CommentPrivateReplyAttempt.objects.filter(
        company_id=comment.company_id,
        comment=comment,
        status=CommentPrivateReplyAttempt.Status.PENDING,
    ).update(status=CommentPrivateReplyAttempt.Status.FAILED, provider_error=error)


def process_public_automation(comment, rule):
    links = _rule_links(rule)
    if not rule.public_reply_enabled:
        CommentReplyAttempt.objects.filter(
            company_id=comment.company_id,
            comment=comment,
            **links,
            status=CommentReplyAttempt.Status.PENDING,
        ).update(
            status=CommentReplyAttempt.Status.FAILED,
            provider_error={"code": "AUTOMATION_ACTION_DISABLED"},
        )
        return
    with transaction.atomic():
        attempt = (
            CommentReplyAttempt.objects.select_for_update()
            .filter(
                company_id=comment.company_id,
                comment=comment,
                **links,
                status=CommentReplyAttempt.Status.PENDING,
            )
            .first()
        )
        if not attempt:
            return
        attempt.status = CommentReplyAttempt.Status.DELIVERY_UNKNOWN
        attempt.save(update_fields=["status", "updated_at"])
    _execute_public_reply(attempt, comment)


def _save_private_outcome(attempt, status, *, provider_message_id="", provider_error=None):
    sent_at = timezone.now() if status == CommentPrivateReplyAttempt.Status.SENT else None
    CommentPrivateReplyAttempt.objects.filter(pk=attempt.pk, company_id=attempt.company_id).update(
        status=status,
        provider_message_id=provider_message_id,
        provider_error=provider_error,
        sent_at=sent_at,
        updated_at=timezone.now(),
    )


def process_private_automation(comment, rule):
    links = _rule_links(rule)
    if not rule.private_reply_enabled:
        CommentPrivateReplyAttempt.objects.filter(
            company_id=comment.company_id,
            comment=comment,
            **links,
            status=CommentPrivateReplyAttempt.Status.PENDING,
        ).update(
            status=CommentPrivateReplyAttempt.Status.FAILED,
            provider_error={"code": "AUTOMATION_ACTION_DISABLED"},
        )
        return
    with transaction.atomic():
        attempt = (
            CommentPrivateReplyAttempt.objects.select_for_update()
            .filter(
                company_id=comment.company_id,
                comment=comment,
                **links,
                status=CommentPrivateReplyAttempt.Status.PENDING,
            )
            .first()
        )
        if not attempt:
            return
        attempt.status = CommentPrivateReplyAttempt.Status.DELIVERY_UNKNOWN
        attempt.save(update_fields=["status", "updated_at"])
    try:
        result = account_client(comment.social_account).send_comment_private_reply(
            comment.external_id, attempt.message
        )
        result = as_dict(result)
        message_id = provider_id(result.get("message_id")) or provider_id(result.get("id"))
        if message_id is None:
            raise MetaDeliveryUnknown()
    except MetaDeliveryUnknown as error:
        _save_private_outcome(
            attempt,
            CommentPrivateReplyAttempt.Status.DELIVERY_UNKNOWN,
            provider_error=error.safe_payload,
        )
    except MetaError as error:
        mark_auth_failure(comment.social_account, error)
        _save_private_outcome(
            attempt,
            CommentPrivateReplyAttempt.Status.FAILED,
            provider_error=error.safe_payload,
        )
    except Exception:
        _save_private_outcome(
            attempt,
            CommentPrivateReplyAttempt.Status.DELIVERY_UNKNOWN,
            provider_error={"code": MetaDeliveryUnknown.code},
        )
    else:
        _save_private_outcome(
            attempt,
            CommentPrivateReplyAttempt.Status.SENT,
            provider_message_id=message_id,
        )


def run_comment_automation(company_id, comment_id):
    comment = (
        Comment.objects.select_related("social_account", "post", "parent_comment")
        .filter(company_id=company_id, pk=comment_id)
        .first()
    )
    if not comment:
        return
    public_attempt = (
        CommentReplyAttempt.objects.filter(company_id=company_id, comment=comment)
        .filter(_automatic_attempts())
        .select_related("automation_rule", "post_automation_rule")
        .first()
    )
    private_attempt = (
        CommentPrivateReplyAttempt.objects.filter(company_id=company_id, comment=comment)
        .select_related("automation_rule", "post_automation_rule")
        .first()
    )
    attempt = public_attempt or private_attempt
    rule = (
        (attempt.post_automation_rule or attempt.automation_rule)
        if attempt
        else effective_automation_rule(comment)
    )
    if not rule or not rule.is_enabled:
        _fail_pending_automation(comment, "AUTOMATION_DISABLED")
        return
    if not automation_eligible(comment):
        _fail_pending_automation(comment, "AUTOMATION_INELIGIBLE")
        return
    # Independent provider writes: one clear failure never rolls back the other.
    process_public_automation(comment, rule)
    process_private_automation(comment, rule)
