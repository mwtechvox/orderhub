import hashlib
import json
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables
from rest_framework.exceptions import ValidationError

from apps.meta.models import OAuthAttempt, PageSelection

from .encryption import TokenCipher
from .facebook import FacebookGraphClient

SCOPES = [
    "pages_show_list",
    "business_management",
    "pages_read_engagement",
    "pages_read_user_content",
    "pages_manage_engagement",
    "pages_manage_posts",
    "pages_messaging",
    "pages_manage_metadata",
]


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def begin(request):
    if (
        not settings.META_APP_ID
        or not settings.META_APP_SECRET
        or not settings.TOKEN_ENCRYPTION_KEY
    ):
        raise ValidationError("Meta тохиргоо хийгдээгүй байна.")
    state = secrets.token_urlsafe(32)
    OAuthAttempt.objects.create(
        company=request.active_company,
        user=request.user,
        state_hash=digest(state),
        session_hash=digest(request.session.session_key),
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    return f"https://www.facebook.com/{settings.META_GRAPH_VERSION}/dialog/oauth?" + urlencode(
        {
            "client_id": settings.META_APP_ID,
            "redirect_uri": settings.META_FACEBOOK_REDIRECT_URI,
            "state": state,
            "scope": ",".join(SCOPES),
            "response_type": "code",
        }
    )


@transaction.atomic
def consume_state(request, state):
    attempt = (
        OAuthAttempt.objects.select_for_update()
        .filter(
            state_hash=digest(state),
            user=request.user,
            company=request.active_company,
            session_hash=digest(request.session.session_key),
            consumed_at__isnull=True,
            expires_at__gt=timezone.now(),
        )
        .first()
    )
    if not attempt:
        raise ValidationError("OAuth хүсэлт хүчингүй эсвэл хугацаа дууссан.")
    attempt.consumed_at = timezone.now()
    attempt.save(update_fields=["consumed_at"])
    return attempt


@sensitive_variables()
def finish(request, code):
    client = FacebookGraphClient()
    short = client.request(
        "GET",
        "oauth/access_token",
        shape="access_token",
        params={
            "client_id": settings.META_APP_ID,
            "client_secret": settings.META_APP_SECRET,
            "redirect_uri": settings.META_FACEBOOK_REDIRECT_URI,
            "code": code,
        },
    )
    long = client.request(
        "GET",
        "oauth/access_token",
        shape="access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": settings.META_APP_ID,
            "client_secret": settings.META_APP_SECRET,
            "fb_exchange_token": short["access_token"],
        },
    )
    user_client = FacebookGraphClient(long["access_token"])
    scopes = [
        p["permission"] for p in user_client.get_permissions() if p.get("status") == "granted"
    ]
    pages = list(user_client.get_pages())
    PageSelection.objects.filter(company=request.active_company, user=request.user).delete()
    return PageSelection.objects.create(
        company=request.active_company,
        user=request.user,
        encrypted_pages=TokenCipher().encrypt(json.dumps(pages)),
        granted_scopes=scopes,
        expires_at=timezone.now() + timedelta(minutes=10),
    )
