import hashlib
import hmac
import json
from unittest.mock import Mock, patch

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from apps.common.provider import media_items
from apps.inbox.models import Conversation, Customer, Message
from apps.inbox.services import resolve_conversation, sync_conversations
from apps.meta.models import RawWebhookEvent
from apps.meta.tasks import process_webhook_event
from apps.social.models import Comment, Post
from apps.social.services import sync_feed, upsert_comment, upsert_post

pytestmark = pytest.mark.django_db


def deliver(payload):
    raw = json.dumps(payload).encode()
    signature = (
        "sha256=" + hmac.new(settings.META_APP_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    )
    return APIClient().post(
        "/api/meta/webhook/",
        data=raw,
        content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256=signature,
    )


def process_events():
    for event in RawWebhookEvent.objects.filter(status="RECEIVED"):
        process_webhook_event(str(event.company_id), str(event.pk))


@pytest.mark.parametrize(
    "attachments",
    [
        None,
        {},
        {"data": None},
        {"data": [None, "not-an-object", {"media": None}, {"payload": None}]},
        "not-a-list",
    ],
)
def test_media_items_skips_malformed_optional_values(attachments):
    assert media_items(attachments) == []


def test_media_items_keeps_valid_url_alongside_malformed_items():
    assert media_items(
        {
            "data": [
                {"media": None},
                {"media": {"image": None}},
                {"payload": []},
                {"type": None, "payload": {"url": "https://example.test/file"}},
            ]
        }
    ) == [{"type": "attachment", "url": "https://example.test/file"}]


def test_feed_skips_invalid_id_and_normalizes_optional_nested_values(account):
    graph = Mock()
    graph.get_page_feed.return_value = [
        None,
        [],
        {"id": None, "message": "must not be stored"},
        {
            "id": "post",
            "message": None,
            "attachments": {"data": [None, {"media": None}]},
            "comments": {"summary": None},
            "reactions": {"summary": {"total_count": "nine"}},
        },
    ]
    graph.get_post_comments.return_value = [
        None,
        {"id": []},
        {"id": "comment", "from": None, "message": None, "can_comment": "yes"},
    ]
    graph.get_comment_replies.return_value = [None, {"id": "reply", "from": [], "message": None}]

    with patch("apps.social.services.account_client", return_value=graph):
        sync_feed(account)

    post = Post.objects.get(company=account.company, external_id="post")
    assert post.message == "" and post.media == []
    assert post.comment_count == 0 and post.reaction_count == 0
    comment = Comment.objects.get(company=account.company, external_id="comment")
    assert comment.author_external_id == "" and comment.author_name == ""
    assert comment.message == "" and comment.can_reply is True
    assert Comment.objects.filter(company=account.company).count() == 2
    assert not Post.objects.filter(company=account.company, external_id="").exists()


@pytest.mark.parametrize("invalid_id", [None, "", "   ", [], {}])
def test_invalid_post_and_comment_ids_create_no_rows(account, invalid_id):
    assert upsert_post(account, {"id": invalid_id}) is None
    post = Post.objects.create(
        company=account.company,
        social_account=account,
        external_id="post",
        created_at_platform="2026-10-14T10:00:00Z",
    )
    assert upsert_comment(post, {"id": invalid_id}) is None
    assert Post.objects.filter(company=account.company).count() == 1
    assert Comment.objects.filter(company=account.company).count() == 0


def test_conversation_sync_skips_invalid_metadata_and_message_id(account):
    graph = Mock()
    graph.get_conversations.return_value = [
        None,
        {"id": None, "participants": {"data": [{"id": "psid"}]}},
        {"id": "missing-participants", "participants": None},
        {
            "id": "thread",
            "participants": {"data": [None, {"id": []}, {"id": "psid", "name": None}]},
        },
    ]
    graph.get_conversation_messages.return_value = [
        None,
        {"id": None, "from": {"id": "psid"}},
        {"id": "wrong-sender", "from": None},
        {
            "id": "message",
            "from": {"id": "psid"},
            "message": None,
            "attachments": None,
            "created_time": "not-a-time",
        },
    ]

    with patch("apps.inbox.services.account_client", return_value=graph):
        sync_conversations(account)

    conversation = Conversation.objects.get(company=account.company)
    message = Message.objects.get(company=account.company)
    assert conversation.external_id == "thread" and conversation.last_inbound_at is None
    assert message.external_id == "message" and message.text == "" and message.attachments == []
    assert Customer.objects.filter(company=account.company).count() == 1
    assert resolve_conversation(account, None) is None
    assert Customer.objects.filter(company=account.company).count() == 1


def test_webhook_optional_nested_values_are_processed_once_and_raw_event_is_preserved(account):
    payload = {
        "object": "page",
        "entry": [
            {
                "id": "page",
                "time": None,
                "messaging": [
                    None,
                    {
                        "sender": {"id": "psid"},
                        "recipient": {"id": "page"},
                        "message": {"mid": "message", "text": None, "attachments": None},
                    },
                ],
                "changes": [
                    None,
                    {
                        "field": "feed",
                        "value": {
                            "item": "comment",
                            "verb": "add",
                            "post_id": "post",
                            "comment_id": "comment",
                            "parent_id": [],
                            "message": None,
                            "from": None,
                        },
                    },
                ],
            }
        ],
    }

    with patch("apps.meta.webhook_views.enqueue"):
        assert deliver(payload).status_code == 200
    process_events()

    event = RawWebhookEvent.objects.get(company=account.company)
    message = Message.objects.get(company=account.company)
    comment = Comment.objects.get(company=account.company)
    assert event.status == "PROCESSED" and event.attempts == 1 and event.payload == payload
    assert message.text == "" and message.attachments == []
    assert comment.message == "" and comment.author_external_id == ""


@pytest.mark.parametrize(
    "message,change",
    [
        ({"text": "missing mid"}, None),
        (None, {"item": "comment", "verb": "add", "post_id": "post"}),
    ],
)
def test_webhook_required_ids_are_ignored_without_rows_or_retries(account, message, change):
    entry = {"id": "page", "messaging": [], "changes": []}
    if message is not None:
        entry["messaging"].append(
            {"sender": {"id": "psid"}, "recipient": {"id": "page"}, "message": message}
        )
    if change is not None:
        entry["changes"].append({"field": "feed", "value": change})
    payload = {"object": "page", "entry": [entry]}

    with patch("apps.meta.webhook_views.enqueue"):
        assert deliver(payload).status_code == 200
    process_events()

    event = RawWebhookEvent.objects.get(company=account.company)
    assert event.status == "IGNORED" and event.attempts == 1 and event.payload == payload
    assert not Message.objects.filter(company=account.company).exists()
    assert not Post.objects.filter(company=account.company).exists()
    assert not Comment.objects.filter(company=account.company).exists()
