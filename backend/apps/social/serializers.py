from django.utils import timezone
from rest_framework import serializers

from apps.meta.models import SocialAccount

from .models import (
    Comment,
    CommentAutomationRule,
    CommentReplyAttempt,
    Post,
    SocialPostCommentAutomation,
)

DEFAULT_PUBLIC_REPLY = "Мэдээллийг чат руу илгээлээ. Чатаа шалгаарай 😊"
DEFAULT_PRIVATE_REPLY = (
    "Сайн байна уу 👋\n\n"
    "Манай бүтээгдэхүүний дэлгэрэнгүй мэдээллийг танд чат руу илгээлээ.\n\n"
    "Захиалах бол энэ чатад хариу бичээрэй."
)


class PostSerializer(serializers.ModelSerializer):
    page_name = serializers.CharField(source="social_account.display_name")
    platform = serializers.CharField(source="social_account.platform")
    comment_automation = serializers.SerializerMethodField()
    publish_error_code = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "social_account",
            "platform",
            "page_name",
            "origin",
            "status",
            "message",
            "permalink_url",
            "media",
            "comment_count",
            "reaction_count",
            "created_at_platform",
            "scheduled_at",
            "published_at",
            "publish_error_code",
            "comment_automation",
        ]

    def get_comment_automation(self, obj):
        try:
            rule = obj.comment_automation
        except SocialPostCommentAutomation.DoesNotExist:
            return None
        return SocialPostCommentAutomationSerializer(rule).data

    def get_publish_error_code(self, obj):
        return obj.provider_error.get("code") if isinstance(obj.provider_error, dict) else None


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = [
            "id",
            "post",
            "parent_comment",
            "author_name",
            "message",
            "can_reply",
            "created_at_platform",
        ]


class ReplyInput(serializers.Serializer):
    message = serializers.CharField(max_length=8000, allow_blank=False)
    idempotency_key = serializers.UUIDField()


class CommentReplyAttemptSerializer(serializers.ModelSerializer):
    error_code = serializers.SerializerMethodField()

    class Meta:
        model = CommentReplyAttempt
        fields = ["id", "comment", "text", "status", "error_code", "created_at", "updated_at"]
        read_only_fields = fields

    def get_error_code(self, obj):
        return obj.provider_error.get("code") if isinstance(obj.provider_error, dict) else None


class AutomationValidationMixin:
    def validate(self, attrs):
        current = self.instance
        values = {
            "is_enabled": getattr(current, "is_enabled", False),
            "public_reply_enabled": getattr(current, "public_reply_enabled", True),
            "public_reply_text": getattr(current, "public_reply_text", DEFAULT_PUBLIC_REPLY),
            "private_reply_enabled": getattr(current, "private_reply_enabled", True),
            "private_reply_text": getattr(current, "private_reply_text", DEFAULT_PRIVATE_REPLY),
            **attrs,
        }
        if values["is_enabled"] and not (
            values["public_reply_enabled"] or values["private_reply_enabled"]
        ):
            raise serializers.ValidationError("Автомат хариунд дор хаяж нэг үйлдэл сонгоно уу.")
        if values["public_reply_enabled"] and not values["public_reply_text"].strip():
            raise serializers.ValidationError(
                {"public_reply_text": "Нийтийн хариуны текст оруулна уу."}
            )
        if values["private_reply_enabled"] and not values["private_reply_text"].strip():
            raise serializers.ValidationError(
                {"private_reply_text": "Хувийн мессежийн текст оруулна уу."}
            )
        attrs["public_reply_text"] = values["public_reply_text"].strip()
        attrs["private_reply_text"] = values["private_reply_text"].strip()
        return attrs


class CommentAutomationRuleSerializer(AutomationValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = CommentAutomationRule
        fields = [
            "is_enabled",
            "public_reply_enabled",
            "public_reply_text",
            "private_reply_enabled",
            "private_reply_text",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
        extra_kwargs = {
            "public_reply_text": {"max_length": 8000, "allow_blank": True},
            "private_reply_text": {"max_length": 2000, "allow_blank": True},
        }


class SocialPostCommentAutomationSerializer(AutomationValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = SocialPostCommentAutomation
        fields = [
            "is_enabled",
            "public_reply_enabled",
            "public_reply_text",
            "private_reply_enabled",
            "private_reply_text",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
        extra_kwargs = {
            "public_reply_text": {"max_length": 8000, "allow_blank": True},
            "private_reply_text": {"max_length": 2000, "allow_blank": True},
        }


class PostWriteSerializer(serializers.Serializer):
    class PublishMode:
        DRAFT = "DRAFT"
        PUBLISH_NOW = "PUBLISH_NOW"
        SCHEDULE = "SCHEDULE"

    social_account = serializers.PrimaryKeyRelatedField(queryset=SocialAccount.objects.all())
    message = serializers.CharField(max_length=63206, allow_blank=True, required=False, default="")
    media = serializers.JSONField(required=False, default=list)
    publish_mode = serializers.ChoiceField(
        choices=[PublishMode.DRAFT, PublishMode.PUBLISH_NOW, PublishMode.SCHEDULE],
        default=PublishMode.DRAFT,
        write_only=True,
    )
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)
    comment_automation = SocialPostCommentAutomationSerializer(required=False, allow_null=True)

    def validate_social_account(self, account):
        request = self.context["request"]
        if account.company_id != request.active_company.id:
            raise serializers.ValidationError("Facebook Page олдсонгүй.")
        if account.platform != "FACEBOOK_PAGE" or account.status != "ACTIVE":
            raise serializers.ValidationError("Идэвхтэй Facebook Page сонгоно уу.")
        return account

    def validate_media(self, media):
        if not isinstance(media, list) or len(media) > 1:
            raise serializers.ValidationError("V1 хувилбарт нэг зураг ашиглана уу.")
        normalized = []
        for item in media:
            if not isinstance(item, dict) or item.get("type") != "image":
                raise serializers.ValidationError("Зургийн мэдээлэл хүчингүй байна.")
            field = serializers.URLField(max_length=2000)
            url = field.run_validation(item.get("url"))
            if not url.startswith("https://"):
                raise serializers.ValidationError("Зураг HTTPS хаягтай байна.")
            normalized.append({"type": "image", "url": url})
        return normalized

    def validate(self, attrs):
        message = attrs.get("message", "").strip()
        media = attrs.get("media", [])
        mode = attrs.get("publish_mode", self.PublishMode.DRAFT)
        scheduled_at = attrs.get("scheduled_at")
        if not message and not media:
            raise serializers.ValidationError("Нийтлэлийн текст эсвэл зураг оруулна уу.")
        if mode == self.PublishMode.SCHEDULE:
            if not scheduled_at or scheduled_at <= timezone.now():
                raise serializers.ValidationError(
                    {"scheduled_at": "Ирээдүйн нийтлэх хугацаа сонгоно уу."}
                )
        else:
            attrs["scheduled_at"] = None
        attrs["message"] = message
        return attrs
