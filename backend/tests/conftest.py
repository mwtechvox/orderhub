import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.companies.models import Company, CompanyMembership


@pytest.fixture
def frozen_now():
    from datetime import datetime, timezone
    from unittest.mock import patch

    now = datetime(2026, 10, 14, 10, tzinfo=timezone.utc)
    with patch("django.utils.timezone.now", return_value=now):
        yield now


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


@pytest.fixture
def tenant(db):
    user = get_user_model().objects.create_user(username="agent", password="test-password")
    company = Company.objects.create(name="Дэлгүүр", slug="shop")
    CompanyMembership.objects.create(company=company, user=user, role="OWNER")
    client = APIClient()
    client.force_login(user)
    client.credentials(HTTP_X_COMPANY_ID=str(company.pk))
    return company, user, client


@pytest.fixture
def account(tenant):
    from apps.meta.models import SocialAccount
    from apps.meta.services.encryption import TokenCipher

    return SocialAccount.objects.create(
        company=tenant[0],
        external_account_id="page",
        display_name="Demo Shop",
        encrypted_access_token=TokenCipher().encrypt("PAGE-TOKEN"),
    )


@pytest.fixture
def conversation(account):
    from django.utils import timezone

    from apps.inbox.services import resolve_conversation

    conversation = resolve_conversation(account, "psid", "Бат", "thread")
    conversation.last_inbound_at = timezone.now()
    conversation.save()
    return conversation
