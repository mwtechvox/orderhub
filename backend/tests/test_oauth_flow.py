import json
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from apps.meta.models import PageSelection
from apps.meta.services.encryption import TokenCipher
from apps.meta.services.oauth import SCOPES

pytestmark = pytest.mark.django_db


def test_full_oauth_keeps_tokens_server_side(tenant, respx_mock):
    client = tenant[2]
    token = respx_mock.get("https://graph.facebook.com/v26.0/oauth/access_token").mock(
        side_effect=[
            httpx.Response(200, json={"access_token": "SHORT"}),
            httpx.Response(200, json={"access_token": "LONG"}),
        ]
    )
    respx_mock.get("https://graph.facebook.com/v26.0/me/permissions").respond(
        200, json={"data": [{"permission": scope, "status": "granted"} for scope in SCOPES]}
    )
    respx_mock.get("https://graph.facebook.com/v26.0/me/accounts").respond(
        200, json={"data": [{"id": "page", "name": "Shop", "access_token": "PAGE-SECRET"}]}
    )
    state = parse_qs(urlparse(client.get("/api/meta/facebook/connect/").url).query)["state"][0]
    response = client.get("/api/meta/facebook/callback/", {"state": state, "code": "CODE"})
    assert response.status_code == 302 and "token" not in response.url
    assert response["Cache-Control"] == "no-store" and response["Referrer-Policy"] == "no-referrer"
    assert token.calls[1].request.url.params["fb_exchange_token"] == "SHORT"
    selection = PageSelection.objects.get(company=tenant[0])
    assert "SECRET" not in selection.encrypted_pages
    assert (
        json.loads(TokenCipher().decrypt(selection.encrypted_pages))[0]["access_token"]
        == "PAGE-SECRET"
    )
    public = client.get("/api/meta/facebook/pages/").content.decode()
    assert "SECRET" not in public and "LONG" not in public and "SHORT" not in public
