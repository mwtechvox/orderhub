from django.db import models
from django.db.models import Q

from apps.common.models import TenantModel


class Post(TenantModel):
    class Origin(models.TextChoices):
        FACEBOOK_SYNC = "FACEBOOK_SYNC"
        ORDERHUB = "ORDERHUB"

    class Status(models.TextChoices):
        DRAFT = "DRAFT"
        SCHEDULED = "SCHEDULED"
        PUBLISHED = "PUBLISHED"
        FAILED = "FAILED"
        DELIVERY_UNKNOWN = "DELIVERY_UNKNOWN"

    social_account = models.ForeignKey("meta.SocialAccount", on_delete=models.CASCADE)
    external_id = models.CharField(max_length=200, blank=True)
    origin = models.CharField(max_length=20, choices=Origin, default=Origin.FACEBOOK_SYNC)
    status = models.CharField(max_length=20, choices=Status, default=Status.PUBLISHED)
    message = models.TextField(blank=True)
    permalink_url = models.URLField(max_length=2000, blank=True)
    media = models.JSONField(default=list)
    comment_count = models.PositiveIntegerField(default=0)
    reaction_count = models.PositiveIntegerField(default=0)
    created_at_platform = models.DateTimeField()
    scheduled_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    provider_error = models.JSONField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["social_account", "external_id"],
                condition=~Q(external_id=""),
                name="post_provider_unique",
            )
        ]
        indexes = [
            models.Index(fields=["company", "-created_at_platform"]),
            models.Index(fields=["status", "scheduled_at"]),
        ]


class SocialPostCommentAutomation(TenantModel):
    """An explicit per-post override of the Page-level automation."""

    social_post = models.OneToOneField(
        Post, on_delete=models.CASCADE, related_name="comment_automation"
    )
    is_enabled = models.BooleanField(default=False)
    public_reply_enabled = models.BooleanField(default=True)
    public_reply_text = models.TextField(blank=True)
    private_reply_enabled = models.BooleanField(default=True)
    private_reply_text = models.TextField(blank=True)


class Comment(TenantModel):
    social_account = models.ForeignKey("meta.SocialAccount", on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    parent_comment = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="replies"
    )
    external_id = models.CharField(max_length=200)
    author_external_id = models.CharField(max_length=200, blank=True)
    author_name = models.CharField(max_length=200, blank=True)
    message = models.TextField(blank=True)
    can_reply = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    last_event_at = models.DateTimeField(null=True, blank=True)
    created_at_platform = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["social_account", "external_id"], name="comment_provider_unique"
            )
        ]
        indexes = [models.Index(fields=["post", "created_at_platform"])]


class CommentAutomationRule(TenantModel):
    """One static comment automation configuration per connected Page."""

    social_account = models.OneToOneField(
        "meta.SocialAccount", on_delete=models.CASCADE, related_name="comment_automation_rule"
    )
    is_enabled = models.BooleanField(default=False)
    public_reply_enabled = models.BooleanField(default=True)
    public_reply_text = models.TextField(blank=True)
    private_reply_enabled = models.BooleanField(default=True)
    private_reply_text = models.TextField(blank=True)


class CommentReplyAttempt(TenantModel):
    """One durable, client-idempotent attempt to reply to a Page comment."""

    class Status(models.TextChoices):
        PENDING = "PENDING"
        SENT = "SENT"
        FAILED = "FAILED"
        DELIVERY_UNKNOWN = "DELIVERY_UNKNOWN"

    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="reply_attempts")
    social_account = models.ForeignKey("meta.SocialAccount", on_delete=models.CASCADE)
    automation_rule = models.ForeignKey(
        CommentAutomationRule,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="public_reply_attempts",
    )
    post_automation_rule = models.ForeignKey(
        SocialPostCommentAutomation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="public_reply_attempts",
    )
    text = models.TextField()
    client_idempotency_key = models.UUIDField()
    status = models.CharField(max_length=20, choices=Status, default=Status.DELIVERY_UNKNOWN)
    provider_reply_id = models.CharField(max_length=200, blank=True)
    provider_error = models.JSONField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "comment", "client_idempotency_key"],
                name="comment_reply_attempt_key_unique",
            ),
            models.UniqueConstraint(
                fields=["company", "comment"],
                condition=Q(automation_rule__isnull=False) | Q(post_automation_rule__isnull=False),
                name="comment_auto_public_once",
            ),
            models.CheckConstraint(
                condition=~Q(
                    automation_rule__isnull=False,
                    post_automation_rule__isnull=False,
                ),
                name="comment_public_single_rule_source",
            ),
        ]
        indexes = [models.Index(fields=["company", "status"])]


class CommentPrivateReplyAttempt(TenantModel):
    """Durable one-shot Messenger private reply initiated from a Page comment."""

    class Status(models.TextChoices):
        PENDING = "PENDING"
        SENT = "SENT"
        FAILED = "FAILED"
        DELIVERY_UNKNOWN = "DELIVERY_UNKNOWN"

    comment = models.ForeignKey(
        Comment, on_delete=models.CASCADE, related_name="private_reply_attempts"
    )
    social_account = models.ForeignKey("meta.SocialAccount", on_delete=models.CASCADE)
    automation_rule = models.ForeignKey(
        CommentAutomationRule,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="private_reply_attempts",
    )
    post_automation_rule = models.ForeignKey(
        SocialPostCommentAutomation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="private_reply_attempts",
    )
    message = models.TextField()
    status = models.CharField(max_length=20, choices=Status, default=Status.PENDING)
    provider_message_id = models.CharField(max_length=200, blank=True)
    provider_error = models.JSONField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "comment"], name="comment_auto_private_once"
            ),
            models.CheckConstraint(
                condition=(
                    Q(automation_rule__isnull=False, post_automation_rule__isnull=True)
                    | Q(automation_rule__isnull=True, post_automation_rule__isnull=False)
                ),
                name="comment_private_one_rule_source",
            ),
        ]
        indexes = [models.Index(fields=["company", "status"])]
