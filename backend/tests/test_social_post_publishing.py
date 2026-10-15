from datetime import timedelta
from unittest.mock import patch

import httpx
import pytest
from django.utils import timezone

from apps.companies.models import Company, CompanyMembership
from apps.meta.exceptions import MetaDeliveryUnknown, MetaError
from apps.meta.models import SocialAccount
from apps.meta.services.facebook import FacebookGraphClient
from apps.social.models import (
    Comment,
    CommentAutomationRule,
    CommentPrivateReplyAttempt,
    CommentReplyAttempt,
    Post,
    SocialPostCommentAutomation,
)
from apps.social.services import run_comment_automation, run_post_publication
from apps.social.tasks import dispatch_scheduled_posts

pytestmark = pytest.mark.django_db

PUBLIC = "Энэ нийтлэлийн мэдээллийг чат руу илгээлээ."
PRIVATE = "Сайн байна уу. Энэ нийтлэлийн дэлгэрэнгүй мэдээлэл."


def automation_payload(*, enabled=True, public=PUBLIC, private=PRIVATE):
    return {
        "is_enabled": enabled,
        "public_reply_enabled": True,
        "public_reply_text": public,
        "private_reply_enabled": True,
        "private_reply_text": private,
    }


def post_payload(account, *, mode="DRAFT", automation=True):
    payload = {
        "social_account": str(account.pk),
        "message": "OrderHub нийтлэл",
        "media": [{"type": "image", "url": "https://cdn.example.com/post.jpg"}],
        "publish_mode": mode,
    }
    if automation is not None:
        payload["comment_automation"] = automation_payload(enabled=automation)
    return payload


def customer_comment(post, suffix="one"):
    return Comment.objects.create(
        company=post.company,
        social_account=post.social_account,
        post=post,
        external_id=f"comment-{suffix}",
        author_external_id=f"customer-{suffix}",
        author_name="Бат",
        message="Үнэ хэд вэ?",
        created_at_platform=timezone.now(),
    )


def test_create_draft_with_automation_is_local_only(tenant, account):
    with patch("apps.social.views.enqueue") as queue:
        response = tenant[2].post("/api/posts/", post_payload(account), format="json")
    assert response.status_code == 201
    post = Post.objects.get(pk=response.data["id"])
    assert post.origin == Post.Origin.ORDERHUB
    assert post.status == Post.Status.DRAFT
    assert post.external_id == ""
    assert post.comment_automation.public_reply_text == PUBLIC
    queue.assert_not_called()


def test_publish_now_keeps_automation_and_sends_one_provider_write(
    tenant, account, django_capture_on_commit_callbacks
):
    with (
        patch("apps.social.views.enqueue") as queue,
        django_capture_on_commit_callbacks(execute=True),
    ):
        response = tenant[2].post(
            "/api/posts/", post_payload(account, mode="PUBLISH_NOW"), format="json"
        )
    post = Post.objects.get(pk=response.data["id"])
    assert post.status == Post.Status.SCHEDULED
    assert post.comment_automation.private_reply_text == PRIVATE
    queue.assert_called_once()

    with patch("apps.social.services.account_client") as factory:
        factory.return_value.create_page_post.return_value = {"id": "page_post"}
        run_post_publication(str(post.company_id), str(post.pk))
        run_post_publication(str(post.company_id), str(post.pk))
    assert factory.return_value.create_page_post.call_count == 1
    post.refresh_from_db()
    assert post.status == Post.Status.PUBLISHED
    assert post.external_id == "page_post"
    assert post.published_at is not None


def test_schedule_must_be_future_and_dispatches_when_due(tenant, account):
    invalid = post_payload(account, mode="SCHEDULE")
    invalid["scheduled_at"] = (timezone.now() - timedelta(minutes=1)).isoformat()
    assert tenant[2].post("/api/posts/", invalid, format="json").status_code == 400

    valid = post_payload(account, mode="SCHEDULE")
    valid["scheduled_at"] = (timezone.now() + timedelta(hours=1)).isoformat()
    response = tenant[2].post("/api/posts/", valid, format="json")
    post = Post.objects.get(pk=response.data["id"])
    with patch("apps.social.tasks.publish_social_post.delay") as queue:
        dispatch_scheduled_posts()
        queue.assert_not_called()
        Post.objects.filter(pk=post.pk).update(scheduled_at=timezone.now() - timedelta(seconds=1))
        dispatch_scheduled_posts()
        queue.assert_called_once_with(str(post.company_id), str(post.pk))


def test_draft_and_scheduled_content_are_editable_but_published_content_is_locked(tenant, account):
    response = tenant[2].post("/api/posts/", post_payload(account), format="json")
    path = f"/api/posts/{response.data['id']}/"
    edited = tenant[2].patch(path, {"message": "Зассан ноорог"}, format="json")
    assert edited.status_code == 200 and edited.data["message"] == "Зассан ноорог"

    post = Post.objects.get(pk=response.data["id"])
    post.status = Post.Status.PUBLISHED
    post.external_id = "published"
    post.save(update_fields=["status", "external_id"])
    assert tenant[2].patch(path, {"message": "Хориотой"}, format="json").status_code == 400


def test_published_post_automation_remains_editable_and_agent_cannot_edit(tenant, account):
    post = Post.objects.create(
        company=tenant[0],
        social_account=account,
        external_id="published",
        origin=Post.Origin.ORDERHUB,
        status=Post.Status.PUBLISHED,
        message="Нийтлэгдсэн",
        created_at_platform=timezone.now(),
    )
    path = f"/api/posts/{post.pk}/comment-automation/"
    response = tenant[2].put(path, automation_payload(public="Шинэ текст"), format="json")
    assert response.status_code == 200
    assert response.data["public_reply_text"] == "Шинэ текст"

    membership = CompanyMembership.objects.get(company=tenant[0], user=tenant[1])
    membership.role = CompanyMembership.Role.AGENT
    membership.save(update_fields=["role"])
    assert tenant[2].get(path).status_code == 200
    assert tenant[2].put(path, automation_payload(), format="json").status_code == 403


def test_cross_tenant_post_create_and_automation_edit_are_blocked(tenant):
    other = Company.objects.create(name="Other", slug="other-post-authoring")
    account = SocialAccount.objects.create(
        company=other, external_account_id="other-page", display_name="Other"
    )
    assert tenant[2].post("/api/posts/", post_payload(account), format="json").status_code == 400
    post = Post.objects.create(
        company=other,
        social_account=account,
        external_id="other-post",
        created_at_platform=timezone.now(),
    )
    assert (
        tenant[2]
        .put(
            f"/api/posts/{post.pk}/comment-automation/",
            automation_payload(),
            format="json",
        )
        .status_code
        == 404
    )


def test_post_rule_wins_and_new_text_only_affects_future_comments(tenant, account):
    account_rule = CommentAutomationRule.objects.create(
        company=tenant[0],
        social_account=account,
        is_enabled=True,
        public_reply_text="Page public",
        private_reply_text="Page private",
    )
    post = Post.objects.create(
        company=tenant[0],
        social_account=account,
        external_id="created-post",
        origin=Post.Origin.ORDERHUB,
        created_at_platform=timezone.now(),
    )
    rule = SocialPostCommentAutomation.objects.create(
        company=tenant[0], social_post=post, **automation_payload()
    )
    first = customer_comment(post)
    with patch("apps.social.services.enqueue"):
        from apps.social.services import schedule_comment_automation

        schedule_comment_automation(first)
    assert CommentReplyAttempt.objects.get(comment=first).text == PUBLIC
    assert CommentPrivateReplyAttempt.objects.get(comment=first).message == PRIVATE
    assert not CommentReplyAttempt.objects.filter(
        comment=first, automation_rule=account_rule
    ).exists()

    rule.public_reply_text = "Ирээдүйн public"
    rule.private_reply_text = "Ирээдүйн private"
    rule.save(update_fields=["public_reply_text", "private_reply_text"])
    second = customer_comment(post, "two")
    with patch("apps.social.services.enqueue"):
        schedule_comment_automation(second)
    assert CommentReplyAttempt.objects.get(comment=first).text == PUBLIC
    assert CommentReplyAttempt.objects.get(comment=second).text == "Ирээдүйн public"


def test_missing_post_rule_falls_back_but_explicit_disabled_rule_blocks_default(tenant, account):
    CommentAutomationRule.objects.create(
        company=tenant[0],
        social_account=account,
        is_enabled=True,
        public_reply_text="Page public",
        private_reply_text="Page private",
    )
    fallback_post = Post.objects.create(
        company=tenant[0],
        social_account=account,
        external_id="fallback-post",
        created_at_platform=timezone.now(),
    )
    from apps.social.services import schedule_comment_automation

    fallback_comment = customer_comment(fallback_post, "fallback")
    with patch("apps.social.services.enqueue"):
        assert schedule_comment_automation(fallback_comment)
    assert CommentReplyAttempt.objects.get(comment=fallback_comment).text == "Page public"

    disabled_post = Post.objects.create(
        company=tenant[0],
        social_account=account,
        external_id="disabled-post",
        created_at_platform=timezone.now(),
    )
    SocialPostCommentAutomation.objects.create(
        company=tenant[0], social_post=disabled_post, **automation_payload(enabled=False)
    )
    disabled_comment = customer_comment(disabled_post, "disabled")
    with patch("apps.social.services.enqueue"):
        assert schedule_comment_automation(disabled_comment) is False
    assert not CommentReplyAttempt.objects.filter(comment=disabled_comment).exists()
    assert not CommentPrivateReplyAttempt.objects.filter(comment=disabled_comment).exists()


def test_processed_comment_is_not_resent_after_post_rule_edit(tenant, account):
    post = Post.objects.create(
        company=tenant[0],
        social_account=account,
        external_id="post",
        origin=Post.Origin.ORDERHUB,
        created_at_platform=timezone.now(),
    )
    rule = SocialPostCommentAutomation.objects.create(
        company=tenant[0], social_post=post, **automation_payload()
    )
    comment = customer_comment(post)
    from apps.social.services import schedule_comment_automation

    with patch("apps.social.services.enqueue"):
        schedule_comment_automation(comment)
    with patch("apps.social.services.account_client") as factory:
        graph = factory.return_value
        graph.reply_to_comment.return_value = {"id": "public"}
        graph.send_comment_private_reply.return_value = {"id": "private"}
        run_comment_automation(str(comment.company_id), str(comment.pk))
        rule.public_reply_text = "edited"
        rule.save(update_fields=["public_reply_text"])
        schedule_comment_automation(comment)
        run_comment_automation(str(comment.company_id), str(comment.pk))
    assert graph.reply_to_comment.call_count == 1
    assert graph.send_comment_private_reply.call_count == 1


def test_publish_failure_classification_and_ambiguous_result_are_terminal(tenant, account):
    post = Post.objects.create(
        company=tenant[0],
        social_account=account,
        external_id="",
        origin=Post.Origin.ORDERHUB,
        status=Post.Status.SCHEDULED,
        message="publish",
        created_at_platform=timezone.now(),
        scheduled_at=timezone.now(),
    )
    with patch("apps.social.services.account_client") as factory:
        factory.return_value.create_page_post.side_effect = MetaDeliveryUnknown()
        run_post_publication(str(post.company_id), str(post.pk))
        run_post_publication(str(post.company_id), str(post.pk))
    post.refresh_from_db()
    assert post.status == Post.Status.DELIVERY_UNKNOWN
    assert factory.return_value.create_page_post.call_count == 1

    other = Post.objects.create(
        company=tenant[0],
        social_account=account,
        external_id="",
        origin=Post.Origin.ORDERHUB,
        status=Post.Status.SCHEDULED,
        message="publish",
        created_at_platform=timezone.now(),
        scheduled_at=timezone.now(),
    )
    with patch("apps.social.services.account_client") as factory:
        factory.return_value.create_page_post.side_effect = MetaError(provider_code=100)
        run_post_publication(str(other.company_id), str(other.pk))
    other.refresh_from_db()
    assert other.status == Post.Status.FAILED


@pytest.mark.parametrize(
    "image_url,path,body",
    [
        ("", "page/feed", {"message": "hello"}),
        (
            "https://cdn.example.com/image.jpg",
            "page/photos",
            {"url": "https://cdn.example.com/image.jpg", "message": "hello"},
        ),
    ],
)
def test_page_publish_client_contract(respx_mock, image_url, path, body):
    route = respx_mock.post(f"https://graph.facebook.com/v26.0/{path}").respond(
        200, json={"id": "page_post"}
    )
    result = FacebookGraphClient("TOKEN").create_page_post("page", "hello", image_url)
    assert result == {"id": "page_post"}
    assert route.calls[0].request.headers["Authorization"] == "Bearer TOKEN"
    assert route.calls[0].request.content == httpx.Request("POST", "https://x", json=body).content


@pytest.mark.parametrize(
    "response",
    [httpx.Response(200, json={}), httpx.Response(200, text="bad"), httpx.ReadTimeout("timeout")],
)
def test_page_publish_ambiguous_response_is_not_retried(respx_mock, response):
    route = respx_mock.post("https://graph.facebook.com/v26.0/page/feed").mock(side_effect=response)
    with pytest.raises(MetaDeliveryUnknown):
        FacebookGraphClient("TOKEN").create_page_post("page", "hello")
    assert route.call_count == 1
