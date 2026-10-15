from django.contrib import admin

from apps.common.admin import ReadOnlyBusinessAdmin

from .models import RawWebhookEvent, SocialAccount


@admin.register(SocialAccount)
class AccountAdmin(ReadOnlyBusinessAdmin):
    exclude = ["encrypted_access_token"]
    list_display = ["display_name", "company", "status", "last_synced_at", "token_configured"]
    list_filter = ["company", "status"]
    readonly_fields = ["token_configured"]

    def token_configured(self, obj):
        return bool(obj.encrypted_access_token)


@admin.register(RawWebhookEvent)
class WebhookAdmin(ReadOnlyBusinessAdmin):
    exclude = ["payload"]
    list_display = ["id", "company", "object_type", "status", "received_at"]
    list_filter = ["company", "status"]
