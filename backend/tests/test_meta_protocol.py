import uuid
from unittest.mock import patch

import httpx
import pytest

from apps.inbox.services import create_outbound
from apps.inbox.tasks import send_meta_message
from apps.meta.exceptions import MetaDeliveryUnknown, MetaTemporaryError
from apps.meta.services.facebook import FacebookGraphClient
from apps.meta.tasks import periodic_sync, sync_account
from apps.social.models import Post


@pytest.mark.parametrize(
    "body",
    [
        "<html>upstream SECRET-TOKEN</html>",
        "{broken",
        "",
        "null",
        "[]",
        '"unexpected"',
        "{}",
        '{"unexpected":"shape"}',
        '{"data":null}',
        '{"data":{}}',
        '{"data":[null]}',
        '{"data":[],"paging":null}',
        '{"data":[],"paging":{"cursors":null}}',
    ],
)
def test_malformed_successful_page_is_retryable_and_safe(respx_mock, body, caplog):
    route = respx_mock.get("https://graph.facebook.com/v26.0/page/feed").respond(
        200, text=body, headers={"Content-Type": "text/html"}
    )
    with (
        patch("apps.meta.services.facebook.time.sleep"),
        pytest.raises(MetaTemporaryError) as raised,
    ):
        list(FacebookGraphClient("SECRET-TOKEN").get_page_feed("page"))
    assert raised.value.kind == "RETRYABLE" and route.call_count == 3
    assert "SECRET-TOKEN" not in caplog.text
    assert body not in caplog.text if body else True


def test_valid_empty_page_and_valid_id_read(respx_mock):
    respx_mock.get("https://graph.facebook.com/v26.0/page/feed").respond(200, json={"data": []})
    respx_mock.get("https://graph.facebook.com/v26.0/page").respond(200, json={"id": "page"})
    client = FacebookGraphClient("TOKEN")
    assert list(client.get_page_feed("page")) == []
    assert client.health("page") == {"id": "page"}


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, json={"unexpected": "shape"}),
        httpx.Response(200, json={"data": None}),
        httpx.Response(200, text="not-json"),
    ],
)
def test_second_malformed_page_fails_whole_iteration(respx_mock, response):
    route = respx_mock.get("https://graph.facebook.com/v26.0/page/feed").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "data": [{"id": "first"}],
                    "paging": {
                        "next": "https://evil.test/?access_token=SECRET",
                        "cursors": {"after": "cursor"},
                    },
                },
            ),
            response,
            response,
            response,
        ]
    )
    with patch("apps.meta.services.facebook.time.sleep"), pytest.raises(MetaTemporaryError):
        list(FacebookGraphClient("TOKEN").get_page_feed("page"))
    assert route.call_count == 4
    assert all(call.request.url.host == "graph.facebook.com" for call in route.calls)
    assert all(call.request.url.params.get("after") == "cursor" for call in route.calls[1:])


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("health", "page", '{"unexpected":true}'),
        ("get_post", "page", "null"),
        ("get_reactions", "page/reactions", '{"summary":null}'),
    ],
)
def test_direct_read_shape_is_retryable(respx_mock, method, path, body):
    route = respx_mock.get(f"https://graph.facebook.com/v26.0/{path}").respond(200, text=body)
    with patch("apps.meta.services.facebook.time.sleep"), pytest.raises(MetaTemporaryError):
        getattr(FacebookGraphClient("TOKEN"), method)("page")
    assert route.call_count == 3


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("send_message", "page/messages", "<html>upstream</html>"),
        ("send_message", "page/messages", "{}"),
        ("reply_to_comment", "comment/comments", "null"),
        ("reply_to_comment", "comment/comments", "{}"),
        ("subscribe", "page/subscribed_apps", '{"success":false}'),
    ],
)
def test_malformed_write_success_is_ambiguous_and_not_retried(respx_mock, method, path, body):
    route = respx_mock.post(f"https://graph.facebook.com/v26.0/{path}").respond(200, text=body)
    client = FacebookGraphClient("TOKEN")
    with pytest.raises(MetaDeliveryUnknown) as raised:
        if method == "send_message":
            client.send_message("page", "customer", "hello")
        elif method == "reply_to_comment":
            client.reply_to_comment("comment", "hello")
        else:
            client.subscribe("page")
    assert raised.value.code == "META_DELIVERY_UNKNOWN" and route.call_count == 1


@pytest.mark.django_db
def test_malformed_feed_keeps_local_data_and_f2_retry_budget(account, frozen_now, respx_mock):
    post = Post.objects.create(
        company=account.company,
        social_account=account,
        external_id="existing",
        message="keep",
        created_at_platform=frozen_now,
    )
    route = respx_mock.get("https://graph.facebook.com/v26.0/page/feed").respond(
        200, text="<html>bad</html>"
    )
    now = frozen_now
    with (
        patch("apps.inbox.services.sync_conversations") as inbox,
        patch("apps.meta.services.facebook.time.sleep"),
        patch("django.utils.timezone.now") as clock,
    ):
        for number in range(1, 6):
            clock.return_value = now
            sync_account(str(account.company_id), str(account.pk))
            account.refresh_from_db()
            assert account.status == "ACTIVE" and account.sync_status == "FAILED"
            assert account.sync_failures == number
            assert account.last_error == "META_TEMPORARY_ERROR"
            assert account.last_synced_at is None
            assert Post.objects.get(pk=post.pk, company=account.company).message == "keep"
            if number < 5:
                assert account.next_sync_at > now
                now = account.next_sync_at
            else:
                assert account.next_sync_at is None
        with patch("apps.meta.tasks.sync_account.delay") as queue:
            for _ in range(3):
                periodic_sync()
                sync_account(str(account.company_id), str(account.pk))
            queue.assert_not_called()
    assert route.call_count == 15 and inbox.call_count == 5


@pytest.mark.django_db
def test_malformed_successful_send_preserves_outbound_idempotency(tenant, conversation, respx_mock):
    message, _ = create_outbound(tenant[0], conversation.pk, "hello", uuid.uuid4())
    route = respx_mock.post("https://graph.facebook.com/v26.0/page/messages").respond(
        200, text="<html>bad</html>"
    )
    send_meta_message(str(tenant[0].pk), str(message.pk))
    send_meta_message(str(tenant[0].pk), str(message.pk))
    message.refresh_from_db()
    assert message.status == "FAILED" and message.attempts == 1
    assert message.provider_error["code"] == "META_DELIVERY_UNKNOWN"
    assert route.call_count == 1


@pytest.mark.django_db
def test_account_sync_marks_second_page_protocol_failure_without_erasing_posts(
    account, frozen_now, respx_mock
):
    existing = Post.objects.create(
        company=account.company,
        social_account=account,
        external_id="existing",
        message="preserved",
        created_at_platform=frozen_now,
    )
    route = respx_mock.get("https://graph.facebook.com/v26.0/page/feed").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "data": [{"id": "first", "message": "valid page"}],
                    "paging": {
                        "next": "https://graph.facebook.com/next",
                        "cursors": {"after": "cursor"},
                    },
                },
            ),
            httpx.Response(200, text="bad page"),
            httpx.Response(200, text="bad page"),
            httpx.Response(200, text="bad page"),
        ]
    )
    respx_mock.get("https://graph.facebook.com/v26.0/first/comments").respond(
        200, json={"data": []}
    )
    with (
        patch("apps.inbox.services.sync_conversations") as inbox,
        patch("apps.meta.services.facebook.time.sleep"),
    ):
        sync_account(str(account.company_id), str(account.pk))
    account.refresh_from_db()
    assert account.status == "ACTIVE" and account.sync_status == "FAILED"
    assert account.sync_failures == 1 and account.last_synced_at is None
    assert account.last_error == "META_TEMPORARY_ERROR" and account.next_sync_at
    assert Post.objects.get(pk=existing.pk, company=account.company).message == "preserved"
    assert route.call_count == 4 and inbox.call_count == 1


def test_malformed_read_recovers_on_next_attempt(respx_mock):
    route = respx_mock.get("https://graph.facebook.com/v26.0/page/feed").mock(
        side_effect=[
            httpx.Response(200, text="bad page"),
            httpx.Response(200, json={"data": [{"id": "valid"}]}),
        ]
    )
    with patch("apps.meta.services.facebook.time.sleep"):
        assert list(FacebookGraphClient("TOKEN").get_page_feed("page")) == [{"id": "valid"}]
    assert route.call_count == 2


def test_success_status_with_structured_provider_error_keeps_error_classification(respx_mock):
    from apps.meta.exceptions import MetaAuthError

    route = respx_mock.get("https://graph.facebook.com/v26.0/page").respond(
        200, json={"error": {"code": 190, "message": "SECRET"}}
    )
    with pytest.raises(MetaAuthError):
        FacebookGraphClient("TOKEN").health("page")
    assert route.call_count == 1
