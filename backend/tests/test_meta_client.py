from unittest.mock import patch

import httpx
import pytest

from apps.meta.exceptions import (
    MetaAuthError,
    MetaDeliveryUnknown,
    MetaPermissionError,
    MetaRateLimitError,
    MetaTemporaryError,
)
from apps.meta.services.facebook import FacebookGraphClient


@pytest.mark.parametrize(
    "method,path",
    [
        ("get_page_feed", "page/feed"),
        ("get_post_comments", "page/comments"),
        ("get_conversations", "page/conversations"),
        ("get_conversation_messages", "page/messages"),
    ],
)
def test_paginated_reads(respx_mock, method, path):
    route = respx_mock.get(f"https://graph.facebook.com/v26.0/{path}").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "data": [{"id": "1"}],
                    "paging": {
                        "next": "https://evil.test/?access_token=SECRET",
                        "cursors": {"after": "next"},
                    },
                },
            ),
            httpx.Response(200, json={"data": [{"id": "2"}]}),
        ]
    )
    assert list(getattr(FacebookGraphClient("TOKEN"), method)("page")) == [{"id": "1"}, {"id": "2"}]
    assert route.calls[1].request.url.params["after"] == "next"
    assert route.calls[0].request.headers["Authorization"] == "Bearer TOKEN"


@pytest.mark.parametrize(
    "status,code,exc",
    [
        (400, 190, MetaAuthError),
        (400, 200, MetaPermissionError),
        (429, 4, MetaRateLimitError),
        (503, 1, MetaTemporaryError),
    ],
)
def test_errors(respx_mock, status, code, exc):
    route = respx_mock.get("https://graph.facebook.com/v26.0/p/reactions").respond(
        status, json={"error": {"code": code, "message": "SECRET", "fbtrace_id": "trace"}}
    )
    with patch("apps.meta.services.facebook.time.sleep"), pytest.raises(exc) as error:
        FacebookGraphClient("TOKEN").get_reactions("p")
    assert "SECRET" not in str(error.value.safe_payload)
    assert route.call_count == (3 if status in (429, 503) else 1)


def test_send_reply_reactions(respx_mock):
    respx_mock.post("https://graph.facebook.com/v26.0/p/messages").respond(
        200, json={"message_id": "mid"}
    )
    respx_mock.post("https://graph.facebook.com/v26.0/c/comments").respond(
        200, json={"id": "reply"}
    )
    respx_mock.get("https://graph.facebook.com/v26.0/p/reactions").respond(
        200, json={"summary": {"total_count": 3}}
    )
    client = FacebookGraphClient("TOKEN")
    assert client.send_message("p", "customer", "hi")["message_id"] == "mid"
    assert client.reply_to_comment("c", "hi")["id"] == "reply"
    assert client.get_reactions("p")["summary"]["total_count"] == 3


def test_write_timeout_not_retried(respx_mock):
    route = respx_mock.post("https://graph.facebook.com/v26.0/p/messages").mock(
        side_effect=httpx.ReadTimeout("SECRET")
    )
    with pytest.raises(MetaDeliveryUnknown):
        FacebookGraphClient("TOKEN").send_message("p", "customer", "hi")
    assert route.call_count == 1


def test_transient_read_recovers(respx_mock):
    respx_mock.get("https://graph.facebook.com/v26.0/p").mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json={"id": "p"})]
    )
    with patch("apps.meta.services.facebook.time.sleep"):
        assert FacebookGraphClient().health("p") == {"id": "p"}


def test_http_date_retry_after_and_safe_logging(respx_mock, caplog):
    from datetime import datetime, timedelta, timezone
    from email.utils import format_datetime

    respx_mock.get("https://graph.facebook.com/v26.0/p/reactions").respond(
        429,
        headers={"Retry-After": format_datetime(datetime.now(timezone.utc) + timedelta(minutes=2))},
        json={"error": {"code": 4, "message": "SECRET-TOKEN", "fbtrace_id": "safe-trace"}},
    )
    with pytest.raises(MetaRateLimitError) as error:
        FacebookGraphClient("SECRET-TOKEN").get_reactions("p")
    assert error.value.retry_after >= 110
    assert "safe-trace" in caplog.text and "SECRET-TOKEN" not in caplog.text


@pytest.mark.parametrize(
    "status,code,subcode,kind,attempts",
    [
        (400, 190, None, "AUTH_REQUIRED", 1),
        (400, 190, 463, "AUTH_REQUIRED", 1),
        (400, 190, 467, "AUTH_REQUIRED", 1),
        (400, 102, None, "AUTH_REQUIRED", 1),
        (403, 10, None, "PERMISSION_REQUIRED", 1),
        (400, 200, None, "PERMISSION_REQUIRED", 1),
        (400, 299, None, "PERMISSION_REQUIRED", 1),
        (429, 4, None, "RETRYABLE", 3),
        (503, 1, None, "RETRYABLE", 3),
        (400, 99999, None, "PERMANENT_OTHER", 1),
    ],
)
def test_structured_error_policy(respx_mock, status, code, subcode, kind, attempts):
    from apps.meta.exceptions import MetaError

    route = respx_mock.get("https://graph.facebook.com/v26.0/p").respond(
        status, json={"error": {"code": code, "error_subcode": subcode, "message": "SECRET"}}
    )
    with patch("apps.meta.services.facebook.time.sleep"), pytest.raises(MetaError) as raised:
        FacebookGraphClient("SECRET").health("p")
    assert raised.value.kind == kind
    assert raised.value.safe_payload["subcode"] == subcode
    assert route.call_count == attempts
    assert "SECRET" not in str(raised.value.safe_payload)


def test_read_timeout_is_bounded_retryable(respx_mock):
    route = respx_mock.get("https://graph.facebook.com/v26.0/p").mock(
        side_effect=httpx.ReadTimeout("SECRET")
    )
    with (
        patch("apps.meta.services.facebook.time.sleep"),
        pytest.raises(MetaTemporaryError) as raised,
    ):
        FacebookGraphClient("SECRET").health("p")
    assert raised.value.kind == "RETRYABLE"
    assert route.call_count == 3
