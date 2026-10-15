from rest_framework import serializers

from .models import SocialAccount


class SocialAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialAccount
        fields = [
            "id",
            "platform",
            "external_account_id",
            "display_name",
            "status",
            "last_synced_at",
            "last_token_check_at",
            "webhook_subscribed_at",
            "sync_status",
            "last_error",
        ]
        read_only_fields = fields


class PageChoice(serializers.Serializer):
    selection_id = serializers.UUIDField()
    page_id = serializers.CharField(max_length=200)
