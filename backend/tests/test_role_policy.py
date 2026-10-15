import uuid
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.companies.models import Company, CompanyMembership
from apps.inbox.models import Conversation, Customer
from apps.meta.models import SocialAccount
from apps.social.models import Comment, Post

pytestmark = pytest.mark.django_db


def set_role(tenant, role):
    membership = CompanyMembership.objects.get(company=tenant[0], user=tenant[1])
    membership.role = role
    membership.save(update_fields=["role"])


@pytest.mark.parametrize(
    "role",
    [
        CompanyMembership.Role.OWNER,
        CompanyMembership.Role.ADMIN,
    ],
)
def test_manager_roles_can_manage_and_sync_integrations(tenant, account, role):
    set_role(tenant, role)
    client = tenant[2]
    assert client.get("/api/meta/facebook/connect/").status_code == 302
    assert client.get("/api/meta/facebook/pages/").status_code == 200
    with (
        patch("apps.meta.views.enqueue"),
        patch("apps.social.views.enqueue"),
        patch("apps.meta.services.tokens.account_client") as account_client,
    ):
        assert client.post(f"/api/meta/accounts/{account.pk}/sync/").status_code == 202
        assert client.post("/api/posts/sync/").status_code == 202
        assert client.delete(f"/api/meta/accounts/{account.pk}/").status_code == 200
    account_client.return_value.unsubscribe.assert_called_once_with("page")


def test_agent_cannot_bypass_management_endpoints(tenant, account):
    set_role(tenant, CompanyMembership.Role.AGENT)
    client = tenant[2]
    for path in [
        "/api/meta/facebook/connect/",
        "/api/meta/facebook/pages/",
        f"/api/meta/accounts/{account.pk}/sync/",
        f"/api/meta/accounts/{account.pk}/",
        "/api/posts/sync/",
    ]:
        method = client.get if path.endswith(("connect/", "pages/")) else client.post
        if path.endswith(f"{account.pk}/"):
            method = client.delete
        assert method(path).status_code == 403


def test_agent_can_perform_daily_post_and_inbox_work(tenant, account, conversation):
    set_role(tenant, CompanyMembership.Role.AGENT)
    post = Post.objects.create(
        company=tenant[0],
        social_account=account,
        external_id="post",
        created_at_platform=timezone.now(),
    )
    comment = Comment.objects.create(
        company=tenant[0],
        social_account=account,
        post=post,
        external_id="comment",
        created_at_platform=timezone.now(),
    )
    client = tenant[2]
    assert client.get("/api/posts/").status_code == 200
    assert client.get(f"/api/posts/{post.pk}/comments/").status_code == 200
    assert client.get("/api/conversations/").status_code == 200
    assert client.get(f"/api/conversations/{conversation.pk}/messages/").status_code == 200
    with patch("apps.social.services.account_client") as graph:
        graph.return_value.reply_to_comment.return_value = {"id": "reply"}
        assert (
            client.post(
                f"/api/comments/{comment.pk}/reply/",
                {"message": "Сайн байна уу?", "idempotency_key": str(uuid.uuid4())},
            ).status_code
            == 201
        )
    response = client.post(
        "/api/messages/send/",
        {
            "conversation_id": str(conversation.pk),
            "text": "Сайн байна уу?",
            "idempotency_key": str(uuid.uuid4()),
        },
    )
    assert response.status_code == 201


@pytest.mark.parametrize(
    "role",
    [
        CompanyMembership.Role.OWNER,
        CompanyMembership.Role.ADMIN,
    ],
)
def test_manager_cannot_manage_another_company_account(tenant, account, role):
    set_role(tenant, role)
    other = Company.objects.create(name="Other", slug="other")
    other_account = SocialAccount.objects.create(
        company=other, external_account_id="other-page", display_name="Other"
    )
    client = tenant[2]
    assert client.post(f"/api/meta/accounts/{other_account.pk}/sync/").status_code == 404
    assert client.delete(f"/api/meta/accounts/{other_account.pk}/").status_code == 404


def test_agent_cannot_access_another_company_data(tenant, account):
    set_role(tenant, CompanyMembership.Role.AGENT)
    other = Company.objects.create(name="Other", slug="other")
    other_account = SocialAccount.objects.create(
        company=other, external_account_id="other-page", display_name="Other"
    )
    post = Post.objects.create(
        company=other,
        social_account=other_account,
        external_id="other-post",
        created_at_platform=timezone.now(),
    )
    customer = Customer.objects.create(
        company=other,
        social_account=other_account,
        external_user_id="other-user",
    )
    conversation = Conversation.objects.create(
        company=other,
        social_account=other_account,
        customer=customer,
    )
    client = tenant[2]
    assert client.get(f"/api/posts/{post.pk}/").status_code == 404
    assert client.get(f"/api/conversations/{conversation.pk}/").status_code == 404
    client.credentials(HTTP_X_COMPANY_ID=str(other.pk))
    assert client.get("/api/posts/").status_code == 403


def test_me_and_company_selection_expose_only_the_active_role(tenant):
    membership = CompanyMembership.objects.get(company=tenant[0], user=tenant[1])
    membership.role = CompanyMembership.Role.ADMIN
    membership.save(update_fields=["role"])
    response = tenant[2].post(f"/api/companies/{tenant[0].pk}/select/")
    assert response.status_code == 200 and response.data == {"ok": True, "role": "ADMIN"}
    assert tenant[2].get("/api/auth/me/").data["active_company_role"] == "ADMIN"
    other = Company.objects.create(name="Other", slug="other")
    CompanyMembership.objects.create(
        company=other, user=tenant[1], role=CompanyMembership.Role.AGENT
    )
    response = tenant[2].post(f"/api/companies/{other.pk}/select/")
    assert response.status_code == 200 and response.data == {"ok": True, "role": "AGENT"}
    assert tenant[2].get("/api/auth/me/").data["active_company_role"] == "AGENT"
