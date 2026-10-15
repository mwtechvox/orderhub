from rest_framework import serializers

from .models import Conversation, Customer, Message


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "name"]


class ConversationSerializer(serializers.ModelSerializer):
    can_reply = serializers.SerializerMethodField()

    def get_can_reply(self, obj):
        from .services import can_reply

        return bool(can_reply(obj))

    customer = CustomerSerializer()
    page_name = serializers.CharField(source="social_account.display_name")
    platform = serializers.CharField(source="social_account.platform")

    class Meta:
        model = Conversation
        fields = [
            "id",
            "customer",
            "social_account",
            "platform",
            "page_name",
            "status",
            "last_message",
            "last_message_at",
            "last_inbound_at",
            "unread_count",
            "can_reply",
        ]


class MessageSerializer(serializers.ModelSerializer):
    error_code = serializers.SerializerMethodField()

    def get_error_code(self, obj):
        return (obj.provider_error or {}).get("code")

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation",
            "direction",
            "text",
            "attachments",
            "status",
            "sent_at",
            "error_code",
        ]


class SendInput(serializers.Serializer):
    conversation_id = serializers.UUIDField()
    text = serializers.CharField(max_length=2000, allow_blank=False)
    idempotency_key = serializers.UUIDField()

    def to_internal_value(self, data):
        if set(data) - set(self.fields):
            raise serializers.ValidationError({"non_field_errors": ["Зөвшөөрөөгүй талбар байна."]})
        return super().to_internal_value(data)
