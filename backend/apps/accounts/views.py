from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.throttles import LoginThrottle


class LoginInput(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=256, trim_whitespace=False)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CSRFView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        data = LoginInput(data=request.data)
        data.is_valid(raise_exception=True)
        user = authenticate(request, **data.validated_data)
        if not user:
            return Response(
                {"code": "INVALID_LOGIN", "message": "Нэвтрэх нэр эсвэл нууц үг буруу."}, status=400
            )
        login(request, user)
        membership = user.companymembership_set.order_by("created_at").first()
        if membership:
            request.session["active_company"] = str(membership.company_id)
        return Response({"id": user.pk, "username": user.username, "csrfToken": get_token(request)})


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({"ok": True})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        active_company = request.session.get("active_company")
        membership = None
        if active_company:
            from apps.companies.models import CompanyMembership

            membership = CompanyMembership.objects.filter(
                company_id=active_company, user=request.user
            ).first()
        return Response(
            {
                "id": request.user.pk,
                "username": request.user.username,
                "active_company": active_company,
                "active_company_role": membership.role if membership else None,
            }
        )
