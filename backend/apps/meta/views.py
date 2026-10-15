import json

from django.conf import settings
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.queue import enqueue
from apps.common.throttles import CompanyThrottle, WriteThrottle
from apps.companies.permissions import CanManageIntegration, IsCompanyMember
from apps.social.models import CommentAutomationRule
from apps.social.serializers import (
    DEFAULT_PRIVATE_REPLY,
    DEFAULT_PUBLIC_REPLY,
    CommentAutomationRuleSerializer,
)

from .exceptions import MetaError
from .models import PageSelection, SocialAccount
from .serializers import PageChoice, SocialAccountSerializer
from .services import oauth
from .services.encryption import TokenCipher
from .services.facebook import FacebookGraphClient
from .tasks import sync_account


class ConnectView(APIView):
    permission_classes = [CanManageIntegration]

    def get(self, request):
        return HttpResponseRedirect(oauth.begin(request))


class CallbackView(APIView):
    permission_classes = [CanManageIntegration]

    def get(self, request):
        oauth.consume_state(request, request.query_params.get("state", ""))
        if request.query_params.get("error") or not request.query_params.get("code"):
            return HttpResponseRedirect(
                settings.FRONTEND_URL + "/settings/integrations?connection=cancelled"
            )
        oauth.finish(request, request.query_params["code"])
        return HttpResponseRedirect(
            settings.FRONTEND_URL + "/settings/integrations?connection=select"
        )


class PagesView(APIView):
    permission_classes = [CanManageIntegration]

    def get(self, request):
        selection = (
            PageSelection.objects.filter(
                company=request.active_company, user=request.user, expires_at__gt=timezone.now()
            )
            .order_by("-created_at")
            .first()
        )
        if not selection:
            return Response({"selection_id": None, "pages": []})
        pages = json.loads(TokenCipher().decrypt(selection.encrypted_pages))
        return Response(
            {
                "selection_id": selection.pk,
                "pages": [{"id": p["id"], "name": p["name"]} for p in pages],
            }
        )

    @sensitive_variables()
    @transaction.atomic
    def post(self, request):
        data = PageChoice(data=request.data)
        data.is_valid(raise_exception=True)
        selection = get_object_or_404(
            PageSelection.objects.select_for_update(),
            pk=data.validated_data["selection_id"],
            company=request.active_company,
            user=request.user,
            expires_at__gt=timezone.now(),
        )
        pages = json.loads(TokenCipher().decrypt(selection.encrypted_pages))
        page = next((p for p in pages if p["id"] == data.validated_data["page_id"]), None)
        if not page or not page.get("access_token"):
            raise ValidationError("Хуудсаа дахин сонгоно уу.")
        if not set(oauth.SCOPES).issubset(selection.granted_scopes):
            raise ValidationError("Шаардлагатай Facebook зөвшөөрлүүдийг олгоно уу.")
        FacebookGraphClient(page["access_token"]).subscribe(page["id"])
        account, _ = SocialAccount.objects.update_or_create(
            company=request.active_company,
            platform="FACEBOOK_PAGE",
            external_account_id=page["id"],
            defaults={
                "display_name": page["name"],
                "encrypted_access_token": TokenCipher().encrypt(page["access_token"]),
                "status": "ACTIVE",
                "granted_scopes": selection.granted_scopes,
                "webhook_subscribed_at": timezone.now(),
                "last_error": "",
                "sync_status": "QUEUED",
                "sync_failures": 0,
                "next_sync_at": None,
                "sync_started_at": None,
            },
        )
        selection.encrypted_pages = TokenCipher().encrypt(
            json.dumps([p for p in pages if p["id"] != page["id"]])
        )
        selection.save(update_fields=["encrypted_pages"])
        transaction.on_commit(
            lambda: enqueue(sync_account, str(account.company_id), str(account.pk))
        )
        return Response(SocialAccountSerializer(account).data, status=201)


class AccountViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SocialAccountSerializer
    permission_classes = [IsCompanyMember]

    def get_queryset(self):
        return SocialAccount.objects.filter(company=self.request.active_company).order_by(
            "display_name"
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[CanManageIntegration],
        throttle_classes=[WriteThrottle, CompanyThrottle],
    )
    def sync(self, request, pk=None):
        account = self.get_object()
        if account.status != "ACTIVE":
            raise ValidationError("Facebook хуудсаа дахин холбоно уу.")
        SocialAccount.objects.filter(company=request.active_company, pk=account.pk).exclude(
            sync_status="RUNNING"
        ).update(sync_status="QUEUED", sync_failures=0, next_sync_at=None)
        transaction.on_commit(
            lambda: enqueue(sync_account, str(account.company_id), str(account.pk))
        )
        return Response({"queued": True}, status=202)

    def get_permissions(self):
        if self.action == "destroy" or (
            self.action == "comment_automation" and self.request.method == "PUT"
        ):
            return [CanManageIntegration()]
        return super().get_permissions()

    @action(
        detail=True,
        methods=["get", "put"],
        url_path="comment-automation",
        throttle_classes=[WriteThrottle, CompanyThrottle],
    )
    def comment_automation(self, request, pk=None):
        account = self.get_object()
        rule = CommentAutomationRule.objects.filter(
            company=request.active_company, social_account=account
        ).first()
        if request.method == "GET":
            rule = rule or CommentAutomationRule(
                company=request.active_company,
                social_account=account,
                public_reply_text=DEFAULT_PUBLIC_REPLY,
                private_reply_text=DEFAULT_PRIVATE_REPLY,
            )
            return Response(CommentAutomationRuleSerializer(rule).data)
        if account.platform != "FACEBOOK_PAGE":
            raise ValidationError("Энэ тохиргоо зөвхөн Facebook Page-д хамаарна.")
        with transaction.atomic():
            rule, _ = CommentAutomationRule.objects.select_for_update().get_or_create(
                company=request.active_company,
                social_account=account,
                defaults={
                    "public_reply_text": DEFAULT_PUBLIC_REPLY,
                    "private_reply_text": DEFAULT_PRIVATE_REPLY,
                },
            )
            serializer = CommentAutomationRuleSerializer(rule, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        account = self.get_object()
        # Keep other authorized companies' subscription intact for the same Page.
        others = (
            SocialAccount.objects.filter(
                external_account_id=account.external_account_id, status="ACTIVE"
            )
            .exclude(pk=account.pk)
            .exists()
        )
        remote_removed = False
        if account.encrypted_access_token and not others:
            from .services.tokens import account_client

            try:
                if account.status == "ACTIVE":
                    account_client(account).unsubscribe(account.external_account_id)
                    remote_removed = True
            except MetaError:
                pass  # Local credential removal must still work for a revoked token.
        with transaction.atomic():
            SocialAccount.objects.filter(company=request.active_company, pk=account.pk).update(
                status="DISCONNECTED",
                encrypted_access_token="",
                webhook_subscribed_at=None,
                sync_status="IDLE",
            )
            PageSelection.objects.filter(company=request.active_company).delete()
            from apps.inbox.models import Message

            Message.objects.filter(
                company=request.active_company, social_account=account, status="PENDING"
            ).update(status="FAILED", provider_error={"code": "ACCOUNT_DISCONNECTED"})
        return Response(
            {"ok": True, "remote_unsubscribed": remote_removed, "shared_subscription": others}
        )
