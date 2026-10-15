import json
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest
from django.utils import timezone

from apps.meta.models import PageSelection, SocialAccount
from apps.meta.services.encryption import TokenCipher
from apps.meta.services.oauth import SCOPES

pytestmark = pytest.mark.django_db


def test_token_roundtrip_and_no_api_exposure(tenant):
    company, _, client = tenant
    encrypted = TokenCipher().encrypt("PAGE-SECRET")
    assert encrypted != "PAGE-SECRET"
    assert TokenCipher().decrypt(encrypted) == "PAGE-SECRET"
    SocialAccount.objects.create(
        company=company,
        external_account_id="page",
        display_name="Shop",
        encrypted_access_token=encrypted,
    )
    payload = client.get("/api/meta/accounts/").content.decode()
    assert (
        "PAGE-SECRET" not in payload
        and encrypted not in payload
        and "token" not in payload.replace("last_token_check_at", "")
    )


def test_state_wrong_and_replay_rejected(tenant):
    _, _, client = tenant
    response = client.get("/api/meta/facebook/connect/")
    state = parse_qs(urlparse(response.url).query)["state"][0]
    assert (
        client.get("/api/meta/facebook/callback/", {"state": "wrong", "code": "x"}).status_code
        == 400
    )
    with patch("apps.meta.services.oauth.finish") as finish:
        assert (
            client.get("/api/meta/facebook/callback/", {"state": state, "code": "x"}).status_code
            == 302
        )
        assert (
            client.get("/api/meta/facebook/callback/", {"state": state, "code": "x"}).status_code
            == 400
        )
        assert finish.call_count == 1


def test_page_selection_only_server_candidates(tenant):
    company, user, client = tenant
    selection = PageSelection.objects.create(
        company=company,
        user=user,
        encrypted_pages=TokenCipher().encrypt(
            json.dumps([{"id": "page", "name": "Shop", "access_token": "SECRET"}])
        ),
        granted_scopes=SCOPES,
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    assert "SECRET" not in client.get("/api/meta/facebook/pages/").content.decode()
    assert (
        client.post(
            "/api/meta/facebook/pages/", {"selection_id": selection.pk, "page_id": "evil"}
        ).status_code
        == 400
    )
    with patch("apps.meta.services.facebook.FacebookGraphClient.subscribe"):
        response = client.post(
            "/api/meta/facebook/pages/", {"selection_id": selection.pk, "page_id": "page"}
        )
    assert response.status_code == 201
    assert "SECRET" not in response.content.decode()
    assert (
        TokenCipher().decrypt(SocialAccount.objects.get(company=company).encrypted_access_token)
        == "SECRET"
    )


def test_expired_state_rejected(tenant):
    from apps.meta.models import OAuthAttempt

    client = tenant[2]
    response = client.get("/api/meta/facebook/connect/")
    state = parse_qs(urlparse(response.url).query)["state"][0]
    OAuthAttempt.objects.filter(company=tenant[0]).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    assert (
        client.get("/api/meta/facebook/callback/", {"state": state, "code": "x"}).status_code == 400
    )


def test_invalid_ciphertext_fails_without_exposure(account):
    from apps.meta.exceptions import MetaError
    from apps.meta.services.tokens import account_client

    account.encrypted_access_token = "invalid-secret-ciphertext"
    with pytest.raises(MetaError) as exc:
        account_client(account)
    assert "invalid-secret" not in str(exc.value)
