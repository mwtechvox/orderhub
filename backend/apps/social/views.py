from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.queue import enqueue
from apps.common.throttles import CompanyThrottle, WriteThrottle
from apps.companies.permissions import CanManageIntegration, IsCompanyMember
from apps.meta.models import SocialAccount
from apps.meta.tasks import sync_account

from .models import Comment, Post, SocialPostCommentAutomation
from .serializers import (
    CommentReplyAttemptSerializer,
    CommentSerializer,
    PostSerializer,
    PostWriteSerializer,
    ReplyInput,
    SocialPostCommentAutomationSerializer,
)
from .services import reply


class PostViewSet(viewsets.ModelViewSet):
    permission_classes = [IsCompanyMember]
    serializer_class = PostSerializer
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "comment_automation"}:
            if self.request.method not in {"GET", "HEAD", "OPTIONS"}:
                return [CanManageIntegration()]
        return super().get_permissions()

    def get_queryset(self):
        query = (
            Post.objects.filter(company=self.request.active_company)
            .select_related("social_account", "comment_automation")
            .order_by("-created_at_platform", "-id")
        )
        if self.request.query_params.get("search"):
            query = query.filter(message__icontains=self.request.query_params["search"])
        if self.request.query_params.get("social_account"):
            query = query.filter(
                social_account_id=serializers.UUIDField().run_validation(
                    self.request.query_params["social_account"]
                )
            )
        if self.request.query_params.get("platform"):
            query = query.filter(social_account__platform=self.request.query_params["platform"])
        return query

    def _validated_write(self, request, post=None):
        payload = request.data.copy()
        if post is not None:
            payload.setdefault("social_account", str(post.social_account_id))
            payload.setdefault("message", post.message)
            payload.setdefault("media", post.media)
            if post.status == Post.Status.SCHEDULED:
                payload.setdefault("publish_mode", PostWriteSerializer.PublishMode.SCHEDULE)
                payload.setdefault("scheduled_at", post.scheduled_at)
            else:
                payload.setdefault("publish_mode", PostWriteSerializer.PublishMode.DRAFT)
        serializer = PostWriteSerializer(data=payload, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    @staticmethod
    def _save_automation(post, automation):
        if automation is None:
            return
        SocialPostCommentAutomation.objects.update_or_create(
            company_id=post.company_id,
            social_post=post,
            defaults=automation,
        )

    @staticmethod
    def _publication_state(mode, scheduled_at):
        if mode == PostWriteSerializer.PublishMode.DRAFT:
            return Post.Status.DRAFT, None
        if mode == PostWriteSerializer.PublishMode.PUBLISH_NOW:
            return Post.Status.SCHEDULED, timezone.now()
        return Post.Status.SCHEDULED, scheduled_at

    def create(self, request, *args, **kwargs):
        from .tasks import publish_social_post

        data = self._validated_write(request)
        automation = data.pop("comment_automation", None)
        mode = data.pop("publish_mode")
        post_status, scheduled_at = self._publication_state(mode, data.pop("scheduled_at", None))
        with transaction.atomic():
            post = Post.objects.create(
                company=request.active_company,
                social_account=data["social_account"],
                external_id="",
                origin=Post.Origin.ORDERHUB,
                status=post_status,
                message=data["message"],
                media=data["media"],
                created_at_platform=timezone.now(),
                scheduled_at=scheduled_at,
            )
            self._save_automation(post, automation)
            if mode == PostWriteSerializer.PublishMode.PUBLISH_NOW:
                transaction.on_commit(
                    lambda: enqueue(publish_social_post, str(post.company_id), str(post.pk))
                )
        post = self.get_queryset().get(pk=post.pk)
        return Response(PostSerializer(post).data, status=status.HTTP_201_CREATED)

    def _update(self, request, pk):
        from .tasks import publish_social_post

        with transaction.atomic():
            post = get_object_or_404(
                Post.objects.select_for_update().select_related("social_account"),
                pk=pk,
                company=request.active_company,
            )
            if post.origin != Post.Origin.ORDERHUB or post.status not in {
                Post.Status.DRAFT,
                Post.Status.SCHEDULED,
                Post.Status.FAILED,
            }:
                raise ValidationError(
                    "Нийтлэгдсэн нийтлэлийн агуулгыг засах боломжгүй. Автомат хариуг тусад нь засна уу."
                )
            data = self._validated_write(request, post)
            automation_present = "comment_automation" in request.data
            automation = data.pop("comment_automation", None)
            mode = data.pop("publish_mode")
            post_status, scheduled_at = self._publication_state(
                mode, data.pop("scheduled_at", None)
            )
            post.social_account = data["social_account"]
            post.message = data["message"]
            post.media = data["media"]
            post.status = post_status
            post.scheduled_at = scheduled_at
            post.provider_error = None
            post.save(
                update_fields=[
                    "social_account",
                    "message",
                    "media",
                    "status",
                    "scheduled_at",
                    "provider_error",
                    "updated_at",
                ]
            )
            if automation_present:
                self._save_automation(post, automation)
            if mode == PostWriteSerializer.PublishMode.PUBLISH_NOW:
                transaction.on_commit(
                    lambda: enqueue(publish_social_post, str(post.company_id), str(post.pk))
                )
        return Response(PostSerializer(self.get_queryset().get(pk=post.pk)).data)

    def update(self, request, *args, **kwargs):
        return self._update(request, kwargs["pk"])

    def partial_update(self, request, *args, **kwargs):
        return self._update(request, kwargs["pk"])

    @action(
        detail=True,
        methods=["get", "put"],
        url_path="comment-automation",
        throttle_classes=[WriteThrottle, CompanyThrottle],
    )
    def comment_automation(self, request, pk=None):
        post = self.get_object()
        rule = SocialPostCommentAutomation.objects.filter(
            company=request.active_company, social_post=post
        ).first()
        if request.method == "GET":
            return Response(SocialPostCommentAutomationSerializer(rule).data if rule else None)
        serializer = SocialPostCommentAutomationSerializer(
            rule, data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        rule = serializer.save(company=request.active_company, social_post=post)
        return Response(SocialPostCommentAutomationSerializer(rule).data)

    @action(detail=True)
    def comments(self, request, pk=None):
        post = self.get_object()
        query = Comment.objects.filter(
            company=request.active_company, post=post, is_deleted=False
        ).order_by("created_at_platform", "id")
        return self.get_paginated_response(
            CommentSerializer(self.paginate_queryset(query), many=True).data
        )

    @action(detail=True)
    def reactions(self, request, pk=None):
        return Response({"total_count": self.get_object().reaction_count, "items": []})

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[CanManageIntegration],
        throttle_classes=[WriteThrottle, CompanyThrottle],
    )
    def sync(self, request):
        accounts = SocialAccount.objects.filter(company=request.active_company, status="ACTIVE")
        accounts.exclude(sync_status="RUNNING").update(
            sync_status="QUEUED", sync_failures=0, next_sync_at=None
        )
        for account in accounts:
            transaction.on_commit(
                lambda a=account: enqueue(sync_account, str(a.company_id), str(a.pk))
            )
        return Response({"queued": accounts.count()}, status=202)


class CommentReplyView(APIView):
    permission_classes = [IsCompanyMember]
    throttle_classes = [WriteThrottle, CompanyThrottle]

    def post(self, request, pk):
        comment = get_object_or_404(
            Comment.objects.select_related("social_account", "post"),
            pk=pk,
            company=request.active_company,
            is_deleted=False,
        )
        if not comment.can_reply:
            raise ValidationError("Энэ сэтгэгдэлд хариулах боломжгүй.")
        data = ReplyInput(data=request.data)
        data.is_valid(raise_exception=True)
        attempt, created = reply(
            comment, data.validated_data["message"], data.validated_data["idempotency_key"]
        )
        return Response(CommentReplyAttemptSerializer(attempt).data, status=201 if created else 200)
