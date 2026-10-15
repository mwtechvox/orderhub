import uuid
from unittest.mock import patch

import pytest

from apps.inbox.models import Message
from apps.inbox.services import create_outbound
from apps.meta.exceptions import MetaAuthError
from apps.meta.tasks import check_token_health, sync_account

pytestmark = pytest.mark.django_db


def test_sync_status(tenant, account):
    with (
        patch("apps.social.services.sync_feed") as feed,
        patch("apps.inbox.services.sync_conversations") as inbox,
    ):
        sync_account(str(account.company_id), str(account.pk))
    account.refresh_from_db()
    assert account.sync_status == "IDLE" and account.last_synced_at
    feed.assert_called_once()
    inbox.assert_called_once()


def test_disconnect_removes_credential_and_pending(tenant, account, conversation):
    create_outbound(tenant[0], conversation.pk, "hi", uuid.uuid4())
    with patch("apps.meta.services.tokens.account_client") as factory:
        response = tenant[2].delete(f"/api/meta/accounts/{account.pk}/")
        factory.return_value.unsubscribe.assert_called_once_with("page")
    assert response.status_code == 200
    account.refresh_from_db()
    assert account.status == "DISCONNECTED" and account.encrypted_access_token == ""
    assert Message.objects.get(company=tenant[0]).status == "FAILED"


def test_agent_cannot_manage_connections(tenant, account):
    membership = tenant[0].memberships.get(user=tenant[1])
    membership.role = "AGENT"
    membership.save()
    assert tenant[2].get("/api/meta/facebook/connect/").status_code == 403
    assert tenant[2].delete(f"/api/meta/accounts/{account.pk}/").status_code == 403
    assert tenant[2].post(f"/api/meta/accounts/{account.pk}/sync/").status_code == 403


def test_health_revocation(account):
    with patch("apps.meta.services.tokens.account_client") as factory:
        factory.return_value.health.side_effect = MetaAuthError()
        check_token_health(str(account.company_id), str(account.pk))
    account.refresh_from_db()
    assert account.status == "NEEDS_REAUTH" and account.last_token_check_at
