from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from .models import CommentPrivateReplyAttempt, CommentReplyAttempt, Post
from .services import run_comment_automation, run_post_publication


@shared_task
def process_comment_automation(company_id, comment_id):
    run_comment_automation(company_id, comment_id)


@shared_task
def dispatch_pending_comment_automations():
    """Recover durable attempts when the initial broker publish was unavailable."""

    pending_public = (
        CommentReplyAttempt.objects.filter(
            status=CommentReplyAttempt.Status.PENDING,
        )
        .filter(Q(automation_rule__isnull=False) | Q(post_automation_rule__isnull=False))
        .values_list("company_id", "comment_id")
    )
    pending_private = CommentPrivateReplyAttempt.objects.filter(
        status=CommentPrivateReplyAttempt.Status.PENDING
    ).values_list("company_id", "comment_id")
    pairs = list(pending_public.union(pending_private)[:500])
    for company_id, comment_id in pairs:
        process_comment_automation.delay(str(company_id), str(comment_id))


@shared_task
def publish_social_post(company_id, post_id):
    run_post_publication(company_id, post_id)


@shared_task
def dispatch_scheduled_posts():
    rows = Post.objects.filter(
        origin=Post.Origin.ORDERHUB,
        status=Post.Status.SCHEDULED,
        scheduled_at__lte=timezone.now(),
    ).values_list("company_id", "id")[:500]
    for company_id, post_id in rows:
        publish_social_post.delay(str(company_id), str(post_id))
