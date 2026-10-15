from uuid import UUID

from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import BasePermission

from .models import CompanyMembership


class IsCompanyMember(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        company_id = request.headers.get("X-Company-ID") or request.session.get("active_company")
        try:
            company_id = UUID(str(company_id))
        except ValueError:
            raise ValidationError("Компаниа сонгоно уу.") from None
        membership = (
            CompanyMembership.objects.select_related("company")
            .filter(company_id=company_id, user=request.user)
            .first()
        )
        if not membership:
            raise PermissionDenied("Энэ компанид хандах эрхгүй.")
        request.active_company = membership.company
        request.membership = membership
        return True


class CanManageIntegration(IsCompanyMember):
    """OWNER and ADMIN may change provider connections or request provider sync."""

    roles = (
        CompanyMembership.Role.OWNER,
        CompanyMembership.Role.ADMIN,
    )

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.membership.role in self.roles


class IsCompanyAdmin(CanManageIntegration):
    """Backward-compatible name for the shared integration-management rule."""
