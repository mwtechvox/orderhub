from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import TenantModel


class Customer(TenantModel):
    social_account = models.ForeignKey("meta.SocialAccount", on_delete=models.CASCADE)
    external_user_id = models.CharField(max_length=200)
    name = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["social_account", "external_user_id"], name="customer_provider_unique"
            )
        ]


class Conversation(TenantModel):
    social_account = models.ForeignKey("meta.SocialAccount", on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    external_id = models.CharField(max_length=200, null=True, blank=True)
    status = models.CharField(max_length=10, default="OPEN")
    unread_count = models.PositiveIntegerField(default=0)
    last_message = models.TextField(blank=True)
    last_message_at = models.DateTimeField(null=True)
    last_inbound_at = models.DateTimeField(null=True)
    last_synced_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["social_account", "customer"], name="conversation_customer_unique"
            ),
            models.UniqueConstraint(
                fields=["social_account", "external_id"],
                condition=Q(external_id__isnull=False),
                name="conversation_provider_unique",
            ),
        ]
        indexes = [models.Index(fields=["company", "-last_message_at"])]


class Message(TenantModel):
    class Status(models.TextChoices):
        RECEIVED = "RECEIVED"
        PENDING = "PENDING"
        SENDING = "SENDING"
        SENT = "SENT"
        FAILED = "FAILED"

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    social_account = models.ForeignKey("meta.SocialAccount", on_delete=models.CASCADE)
    external_id = models.CharField(max_length=200, null=True, blank=True)
    client_idempotency_key = models.UUIDField(null=True, blank=True)
    direction = models.CharField(
        max_length=10, choices=[("INBOUND", "INBOUND"), ("OUTBOUND", "OUTBOUND")]
    )
    sender_external_id = models.CharField(max_length=200, blank=True)
    recipient_external_id = models.CharField(max_length=200, blank=True)
    text = models.TextField(blank=True)
    attachments = models.JSONField(default=list)
    status = models.CharField(max_length=10, choices=Status, default=Status.RECEIVED)
    provider_error = models.JSONField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["social_account", "external_id"],
                condition=Q(external_id__isnull=False),
                name="message_provider_unique",
            ),
            models.UniqueConstraint(
                fields=["company", "client_idempotency_key"],
                condition=Q(client_idempotency_key__isnull=False),
                name="message_client_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["conversation", "-sent_at"]),
            models.Index(fields=["company", "status"]),
        ]
