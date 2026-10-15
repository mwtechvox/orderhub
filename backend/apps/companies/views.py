from django.db import transaction
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Company, CompanyMembership


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name", "slug", "timezone"]


class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return Company.objects.filter(memberships__user=self.request.user).order_by("name")

    @transaction.atomic
    def perform_create(self, serializer):
        company = serializer.save()
        CompanyMembership.objects.create(company=company, user=self.request.user, role="OWNER")
        self.request.session["active_company"] = str(company.pk)

    @action(detail=True, methods=["post"])
    def select(self, request, pk=None):
        company = self.get_object()
        membership = CompanyMembership.objects.get(company=company, user=request.user)
        request.session["active_company"] = str(company.pk)
        return Response({"ok": True, "role": membership.role})
