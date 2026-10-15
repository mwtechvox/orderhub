from cryptography.fernet import InvalidToken
from rest_framework.exceptions import ValidationError

from apps.meta.exceptions import MetaAuthError, MetaErrorKind
from apps.meta.models import SocialAccount

from .encryption import TokenCipher
from .facebook import FacebookGraphClient


def account_client(account):
    if account.status != "ACTIVE":
        raise ValidationError("Facebook хуудсаа дахин холбоно уу.")
    if not account.encrypted_access_token:
        raise MetaAuthError()
    try:
        token = TokenCipher().decrypt(account.encrypted_access_token)
    except (InvalidToken, ValueError):
        raise MetaAuthError() from None
    return FacebookGraphClient(token)


def mark_auth_failure(account, error):
    """Auth and required-permission errors both require reauthorization.

    Keep the existing helper entry point for send/reply callers. Never overwrite
    a disconnected account or a newly replaced credential with an old failure.
    """
    if error.kind in (MetaErrorKind.AUTH_REQUIRED, MetaErrorKind.PERMISSION_REQUIRED):
        SocialAccount.objects.filter(
            pk=account.pk,
            company_id=account.company_id,
            status="ACTIVE",
            encrypted_access_token=account.encrypted_access_token,
        ).update(
            status="NEEDS_REAUTH",
            last_error=error.code,
            sync_status="FAILED",
            next_sync_at=None,
        )
