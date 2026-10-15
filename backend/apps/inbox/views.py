from django.db import transaction
from django.db.models import F, Q
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.queue import enqueue
from apps.common.throttles import CompanyThrottle, WriteThrottle
from apps.companies.permissions import IsCompanyMember

from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer, SendInput
from .services import create_outbound
from .tasks import send_meta_message


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsCompanyMember]
    serializer_class = ConversationSerializer

    def get_queryset(self):
        query = (
            Conversation.objects.filter(company=self.request.active_company)
            .select_related("customer", "social_account")
            .order_by(F("last_message_at").desc(nulls_last=True), "id")
        )
        search = self.request.query_params.get("search")
        if search:
            query = query.filter(
                Q(customer__name__icontains=search) | Q(last_message__icontains=search)
            )
        if self.request.query_params.get("social_account"):
            query = query.filter(
                social_account_id=serializers.UUIDField().run_validation(
                    self.request.query_params["social_account"]
                )
            )
        if self.request.query_params.get("platform"):
            query = query.filter(social_account__platform=self.request.query_params["platform"])
        return query

    @action(detail=True)
    def messages(self, request, pk=None):
        conversation = self.get_object()
        query = Message.objects.filter(
            company=request.active_company, conversation=conversation
        ).order_by("-sent_at", "-id")
        return self.get_paginated_response(
            MessageSerializer(self.paginate_queryset(query), many=True).data
        )

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        conversation = self.get_object()
        Conversation.objects.filter(company=request.active_company, pk=conversation.pk).update(
            unread_count=0
        )
        return Response({"ok": True})


class SendMessageView(APIView):
    permission_classes = [IsCompanyMember]
    throttle_classes = [WriteThrottle, CompanyThrottle]

    def post(self, request):
        data = SendInput(data=request.data)
        data.is_valid(raise_exception=True)
        message, created = create_outbound(request.active_company, **data.validated_data)
        if created:
            transaction.on_commit(
                lambda: enqueue(send_meta_message, str(request.active_company.pk), str(message.pk))
            )
        return Response(MessageSerializer(message).data, status=201 if created else 200)
