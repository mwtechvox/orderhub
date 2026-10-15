import json
from datetime import timedelta
from unittest.mock import patch

import pytest

from apps.inbox.models import Message
from apps.meta.exceptions import (
    MetaAuthError,
    MetaError,
    MetaPermissionError,
    MetaRateLimitError,
    MetaTemporaryError,
)
from apps.meta.models import PageSelection, SocialAccount
from apps.meta.services.encryption import TokenCipher
from apps.meta.services.oauth import SCOPES
from apps.meta.services.webhooks import process_change
from apps.meta.tasks import check_token_health, daily_maintenance, periodic_sync, sync_account
from apps.social.models import Post

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def block_provider_http(respx_mock):
    """All provider I/O in these policy tests must be explicitly mocked."""
    yield


@pytest.mark.parametrize("error", [MetaAuthError(), MetaPermissionError(), MetaError()])
def test_permanent_failure_stops_jobs_and_preserves_data(
    tenant, account, conversation, frozen_now, error
):
    credential = account.encrypted_access_token
    post = Post.objects.create(
        company=tenant[0],
        social_account=account,
        external_id="post",
        created_at_platform=frozen_now,
    )
    message = Message.objects.create(
        company=tenant[0],
        social_account=account,
        conversation=conversation,
        direction="INBOUND",
        text="retained",
        external_id="mid",
    )
    with (
        patch("apps.social.services.sync_feed", side_effect=error) as feed,
        patch("apps.inbox.services.sync_conversations") as inbox,
        patch("apps.meta.tasks.sync_account.delay") as queued,
        patch("apps.meta.tasks.check_token_health.delay") as health,
    ):
        sync_account(str(tenant[0].pk), str(account.pk))
        for _ in range(3):
            periodic_sync()
            daily_maintenance()
            sync_account(str(tenant[0].pk), str(account.pk))
        feed.assert_called_once()
        assert inbox.call_count == (0 if isinstance(error, MetaAuthError) else 1)
        queued.assert_not_called()
        health.assert_not_called()
    account.refresh_from_db()
    assert account.status == ("ACTIVE" if type(error) is MetaError else "NEEDS_REAUTH")
    assert account.sync_status == "FAILED" and account.next_sync_at is None
    assert account.sync_failures == 1 and account.last_error == error.code
    assert account.encrypted_access_token == credential
    assert Post.objects.filter(pk=post.pk, company=tenant[0]).exists()
    conversation.refresh_from_db()
    message.refresh_from_db()
    assert message.text == "retained"
    response = tenant[2].get(f"/api/meta/accounts/{account.pk}/")
    assert response.json()["status"] == account.status
    assert response.json()["last_error"] == error.code
    assert credential not in response.content.decode()
    if account.status == "NEEDS_REAUTH":
        assert tenant[2].post(f"/api/meta/accounts/{account.pk}/sync/").status_code == 400


@pytest.mark.parametrize("error", [MetaTemporaryError(), MetaRateLimitError(retry_after=1800)])
def test_transient_retry_is_due_bounded_and_manually_recoverable(
    tenant, account, frozen_now, error, django_capture_on_commit_callbacks
):
    now = frozen_now
    with (
        patch("apps.social.services.sync_feed", side_effect=error) as feed,
        patch("apps.inbox.services.sync_conversations") as inbox,
        patch("random.uniform", return_value=0),
        patch("apps.meta.tasks.sync_account.delay") as queued,
        patch("django.utils.timezone.now") as clock,
    ):
        for attempt in range(1, 6):
            clock.return_value = now
            sync_account(str(account.company_id), str(account.pk))
            account.refresh_from_db()
            assert account.status == "ACTIVE" and account.sync_status == "FAILED"
            assert account.sync_failures == attempt
            assert account.last_synced_at is None
            if attempt < 5:
                assert account.next_sync_at == now + timedelta(
                    seconds=max(error.retry_after, 300 * 2 ** (attempt - 1))
                )
                periodic_sync()
                queued.assert_not_called()
                sync_account(str(account.company_id), str(account.pk))  # stale duplicate delivery
                assert feed.call_count == attempt
                now = account.next_sync_at
                clock.return_value = now
                periodic_sync()
                queued.assert_called_once_with(str(account.company_id), str(account.pk))
                queued.reset_mock()
            else:
                assert account.next_sync_at is None
                for _ in range(3):
                    periodic_sync()
                    sync_account(str(account.company_id), str(account.pk))
                queued.assert_not_called()
        assert feed.call_count == inbox.call_count == 5
        with (
            patch("apps.meta.views.enqueue") as enqueue,
            django_capture_on_commit_callbacks(execute=True),
        ):
            response = tenant[2].post(f"/api/meta/accounts/{account.pk}/sync/")
        assert response.status_code == 202
        account.refresh_from_db()
        assert account.sync_failures == 0 and account.sync_status == "QUEUED"
        enqueue.assert_called_once_with(sync_account, str(account.company_id), str(account.pk))
    with patch("apps.social.services.sync_feed"), patch("apps.inbox.services.sync_conversations"):
        sync_account(str(account.company_id), str(account.pk))
    account.refresh_from_db()
    assert account.sync_status == "IDLE" and account.sync_failures == 0
    assert account.last_error == "" and account.last_synced_at == frozen_now


@pytest.mark.parametrize("status", ["ACTIVE", "NEEDS_REAUTH", "DISCONNECTED"])
def test_scheduler_and_health_population(account, frozen_now, status):
    account.status = status
    account.save()
    with patch("apps.meta.tasks.sync_account.delay") as queue:
        periodic_sync()
        assert queue.call_count == (1 if status == "ACTIVE" else 0)
    with patch("apps.meta.services.tokens.account_client") as factory:
        check_token_health(str(account.company_id), str(account.pk))
        assert factory.call_count == (1 if status == "ACTIVE" else 0)
    account.refresh_from_db()
    assert account.status == status
    if status != "ACTIVE":
        account.sync_status = "RUNNING"
        account.sync_started_at = frozen_now - timedelta(hours=1)
        account.save()
        with patch("apps.meta.tasks.sync_account.delay") as queue:
            periodic_sync()
            queue.assert_not_called()
        account.refresh_from_db()
        assert account.sync_status == "RUNNING"


@pytest.mark.parametrize(
    "error",
    [
        MetaAuthError(),
        MetaPermissionError(),
        MetaError(),
        MetaTemporaryError(),
        MetaRateLimitError(),
    ],
)
def test_health_uses_same_failure_policy(account, error):
    with patch("apps.meta.services.tokens.account_client") as factory:
        factory.return_value.health.side_effect = error
        check_token_health(str(account.company_id), str(account.pk))
        account.refresh_from_db()
        assert account.last_error == error.code and account.last_token_check_at
        assert account.status == (
            "NEEDS_REAUTH" if isinstance(error, (MetaAuthError, MetaPermissionError)) else "ACTIVE"
        )
        factory.return_value.health.side_effect = None
        check_token_health(str(account.company_id), str(account.pk))
        assert factory.call_count == (
            2 if isinstance(error, (MetaTemporaryError, MetaRateLimitError)) else 1
        )
    account.refresh_from_db()
    assert account.last_error == error.code  # health success cannot silently recover sync


@pytest.mark.parametrize("failure", [None, "scopes", "subscribe", "expired", "foreign"])
def test_reconnect_requires_valid_selection_scopes_and_subscription(
    tenant, account, frozen_now, failure, django_capture_on_commit_callbacks
):
    from apps.companies.models import Company

    old_token = account.encrypted_access_token
    account.status = "NEEDS_REAUTH"
    account.sync_status = "FAILED"
    account.sync_failures = 5
    account.last_error = "META_PERMISSION_ERROR"
    account.save()
    selection = PageSelection.objects.create(
        company=Company.objects.create(name="Other", slug="other")
        if failure == "foreign"
        else tenant[0],
        user=tenant[1],
        granted_scopes=[] if failure == "scopes" else SCOPES,
        encrypted_pages=TokenCipher().encrypt(
            json.dumps([{"id": "page", "name": "Shop", "access_token": "NEW-SECRET"}])
        ),
        expires_at=frozen_now + timedelta(minutes=-1 if failure == "expired" else 10),
    )
    with (
        patch(
            "apps.meta.services.facebook.FacebookGraphClient.subscribe",
            side_effect=MetaPermissionError() if failure == "subscribe" else None,
        ) as subscribe,
        patch("apps.meta.views.enqueue") as queue,
        django_capture_on_commit_callbacks(execute=True),
    ):
        response = tenant[2].post(
            "/api/meta/facebook/pages/", {"selection_id": selection.pk, "page_id": "page"}
        )
    account.refresh_from_db()
    assert "NEW-SECRET" not in response.content.decode()
    if failure:
        assert response.status_code >= 400
        assert account.status == "NEEDS_REAUTH" and account.sync_failures == 5
        assert account.encrypted_access_token == old_token
        queue.assert_not_called()
        if failure != "subscribe":
            subscribe.assert_not_called()
    else:
        assert response.status_code == 201
        subscribe.assert_called_once_with("page")
        queue.assert_called_once_with(sync_account, str(account.company_id), str(account.pk))
        assert account.status == "ACTIVE" and account.sync_status == "QUEUED"
        assert account.sync_failures == 0 and account.last_error == ""
        assert account.next_sync_at is None and account.sync_started_at is None
        assert TokenCipher().decrypt(account.encrypted_access_token) == "NEW-SECRET"
        with (
            patch("apps.social.services.sync_feed") as feed,
            patch("apps.inbox.services.sync_conversations"),
        ):
            sync_account(str(account.company_id), str(account.pk))
            feed.assert_called_once()


@pytest.mark.parametrize("backoff", [False, True])
@pytest.mark.parametrize("comment", [False, True])
def test_webhook_hint_cannot_restart_paused_or_backing_off_sync(
    account, frozen_now, backoff, comment
):
    account.sync_status = "FAILED"
    account.next_sync_at = frozen_now + timedelta(hours=1) if backoff else None
    account.save()
    value = (
        {"item": "comment", "post_id": "post", "comment_id": "comment", "verb": "add"}
        if comment
        else {"item": "reaction"}
    )
    assert process_change(account, {"field": "feed", "value": value}, frozen_now.timestamp())
    account.refresh_from_db()
    assert account.sync_status == "FAILED"
    assert account.next_sync_at == (frozen_now + timedelta(hours=1) if backoff else None)


@pytest.mark.parametrize("change", ["disconnect", "reconnect"])
def test_inflight_sync_cannot_overwrite_new_connection_state(account, change):
    def replace(_):
        SocialAccount.objects.filter(company_id=account.company_id, pk=account.pk).update(
            status="DISCONNECTED" if change == "disconnect" else "ACTIVE",
            encrypted_access_token=""
            if change == "disconnect"
            else TokenCipher().encrypt("REPLACED"),
            sync_status="IDLE" if change == "disconnect" else "QUEUED",
            sync_started_at=None,
        )
        raise MetaAuthError()

    with (
        patch("apps.social.services.sync_feed", side_effect=replace),
        patch("apps.inbox.services.sync_conversations") as inbox,
    ):
        sync_account(str(account.company_id), str(account.pk))
        inbox.assert_not_called()
    account.refresh_from_db()
    assert account.status == ("DISCONNECTED" if change == "disconnect" else "ACTIVE")
    assert account.last_error == ""


def test_inbox_auth_error_takes_precedence_over_feed_temporary_error(account):
    with (
        patch("apps.social.services.sync_feed", side_effect=MetaTemporaryError()),
        patch("apps.inbox.services.sync_conversations", side_effect=MetaAuthError()),
    ):
        sync_account(str(account.company_id), str(account.pk))
    account.refresh_from_db()
    assert account.status == "NEEDS_REAUTH" and account.last_error == "META_AUTH_ERROR"
    assert account.next_sync_at is None


def test_sync_tenant_id_cannot_claim_another_company_account(account):
    from apps.companies.models import Company

    other = Company.objects.create(name="Other", slug="other")
    with (
        patch("apps.social.services.sync_feed") as feed,
        patch("apps.inbox.services.sync_conversations"),
    ):
        sync_account(str(other.pk), str(account.pk))
    feed.assert_not_called()
    account.refresh_from_db()
    assert account.sync_status == "IDLE"


@pytest.mark.parametrize("credential", ["", "invalid-ciphertext"])
def test_unusable_local_credential_requires_reauth(account, credential):
    account.encrypted_access_token = credential
    account.save()
    with patch("apps.inbox.services.sync_conversations") as inbox:
        sync_account(str(account.company_id), str(account.pk))
    inbox.assert_not_called()
    account.refresh_from_db()
    assert account.status == "NEEDS_REAUTH" and account.last_error == "META_AUTH_ERROR"


def test_outbound_permission_failure_stops_future_account_sync(tenant, account, conversation):
    import uuid

    from apps.inbox.services import create_outbound
    from apps.inbox.tasks import send_meta_message

    message, _ = create_outbound(tenant[0], conversation.pk, "hi", uuid.uuid4())
    with patch("apps.inbox.tasks.account_client") as factory:
        factory.return_value.send_message.side_effect = MetaPermissionError()
        send_meta_message(str(tenant[0].pk), str(message.pk))
    account.refresh_from_db()
    message.refresh_from_db()
    assert message.status == "FAILED" and account.status == "NEEDS_REAUTH"
    with patch("apps.meta.tasks.sync_account.delay") as queue:
        periodic_sync()
        queue.assert_not_called()
