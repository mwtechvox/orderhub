import uuid
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.companies.models import Company
from apps.meta.models import SocialAccount
from apps.social.models import Comment, Post
from apps.social.services import sync_feed

pytestmark = pytest.mark.django_db


def test_feed_comments_reply_and_reactions(tenant, account):
    client = tenant[2]
    with patch("apps.social.services.account_client") as factory:
        graph = factory.return_value
        graph.get_page_feed.return_value = [
            {"id": "post", "message": "Шинэ бараа", "reactions": {"summary": {"total_count": 9}}}
        ]
        graph.get_post_comments.return_value = [{"id": "comment", "message": "Үнэ?"}]
        graph.get_comment_replies.return_value = [{"id": "reply", "message": "100"}]
        sync_feed(account)
        sync_feed(account)
    assert Post.objects.count() == 1 and Comment.objects.count() == 2
    post = Post.objects.get(company=tenant[0])
    comment = Comment.objects.get(company=tenant[0], external_id="comment")
    assert client.get(f"/api/posts/{post.pk}/reactions/").data == {"total_count": 9, "items": []}
    assert len(client.get(f"/api/posts/{post.pk}/comments/").data["results"]) == 2
    with patch("apps.social.services.account_client") as factory:
        factory.return_value.reply_to_comment.return_value = {"id": "reply2"}
        response = client.post(
            f"/api/comments/{comment.pk}/reply/",
            {"message": "Сайн байна уу?", "idempotency_key": str(uuid.uuid4())},
        )
    assert response.status_code == 201
    assert response.data["comment"] == comment.pk
    assert response.data["status"] == "SENT"


def test_cross_tenant_posts_comments_accounts(tenant):
    company = Company.objects.create(name="Other", slug="other")
    account = SocialAccount.objects.create(
        company=company, external_account_id="other", display_name="Other"
    )
    post = Post.objects.create(
        company=company,
        social_account=account,
        external_id="other-post",
        created_at_platform=timezone.now(),
    )
    comment = Comment.objects.create(
        company=company,
        social_account=account,
        post=post,
        external_id="other-comment",
        created_at_platform=timezone.now(),
    )
    client = tenant[2]
    for path in [
        f"/api/posts/{post.pk}/",
        f"/api/posts/{post.pk}/comments/",
        f"/api/meta/accounts/{account.pk}/",
    ]:
        assert client.get(path).status_code == 404
    with patch("apps.social.services.account_client") as factory:
        assert (
            client.post(f"/api/comments/{comment.pk}/reply/", {"message": "hack"}).status_code
            == 404
        )
        factory.assert_not_called()
    client.credentials(HTTP_X_COMPANY_ID=str(company.pk))
    assert client.get("/api/posts/").status_code == 403


def test_invalid_account_filter_returns_validation_error(tenant):
    assert tenant[2].get("/api/posts/?social_account=invalid").status_code == 400


def test_post_platform_and_account_filters_are_tenant_scoped(tenant, account):
    post = Post.objects.create(
        company=tenant[0],
        social_account=account,
        external_id="post",
        created_at_platform=timezone.now(),
    )
    payload = (
        tenant[2]
        .get(f"/api/posts/?platform=FACEBOOK_PAGE&social_account={account.pk}")
        .data["results"]
    )
    assert [item["id"] for item in payload] == [str(post.pk)]
    assert payload[0]["platform"] == "FACEBOOK_PAGE"
