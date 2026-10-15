from django.conf import settings
from django.db import models

from apps.common.models import TenantModel


class SocialAccount(TenantModel):
    platform = models.CharField(max_length=30, default="FACEBOOK_PAGE", editable=False)
    auth_mode = models.CharField(max_length=30, default="FACEBOOK_LOGIN", editable=False)
    graph_host = models.CharField(
        max_length=100, default="https://graph.facebook.com", editable=False
    )
    external_account_id = models.CharField(max_length=200)
    display_name = models.CharField(max_length=200)
    encrypted_access_token = models.TextField(blank=True)
    granted_scopes = models.JSONField(default=list)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        default="ACTIVE",
        choices=[(s, s) for s in ["ACTIVE", "NEEDS_REAUTH", "DISCONNECTED"]],
    )
    last_token_check_at = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    webhook_subscribed_at = models.DateTimeField(null=True, blank=True)
    sync_status = models.CharField(max_length=20, default="IDLE")
    last_error = models.CharField(max_length=80, blank=True)
    sync_started_at = models.DateTimeField(null=True, blank=True)
    next_sync_at = models.DateTimeField(null=True, blank=True)
    sync_failures = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "platform", "external_account_id"], name="social_account_unique"
            )
        ]

    def __str__(self):
        return self.display_name


class OAuthAttempt(TenantModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    state_hash = models.CharField(max_length=64, unique=True)
    session_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True)


class PageSelection(TenantModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    encrypted_pages = models.TextField()
    granted_scopes = models.JSONField(default=list)
    expires_at = models.DateTimeField()


class RawWebhookEvent(models.Model):
    import uuid

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "companies.Company", on_delete=models.CASCADE, null=True, blank=True
    )
    social_account = models.ForeignKey(
        SocialAccount, on_delete=models.CASCADE, null=True, blank=True
    )
    object_type = models.CharField(max_length=100)
    external_account_id = models.CharField(max_length=200, blank=True)
    dedupe_key = models.CharField(max_length=64, unique=True)
    signature_valid = models.BooleanField(default=True)
    payload = models.JSONField()
    status = models.CharField(max_length=20, default="RECEIVED")
    error = models.CharField(max_length=100, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True)
