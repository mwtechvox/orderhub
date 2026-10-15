"""Facebook-only contracts. See docs/META_SETUP.md for verification limits.

Never follow provider paging.next URLs: they can contain tokens or different hosts.
Reads retry transient failures; writes never retry ambiguous network/5xx outcomes.
"""

import logging
import random
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import httpx
from django.conf import settings
from django.views.decorators.debug import sensitive_variables

from apps.meta.exceptions import (
    MetaAuthError,
    MetaDeliveryUnknown,
    MetaError,
    MetaPermissionError,
    MetaRateLimitError,
    MetaTemporaryError,
)

logger = logging.getLogger(__name__)


def retry_after_seconds(value):
    try:
        return max(0, int(value))
    except (ValueError, TypeError):
        try:
            return max(
                0, int((parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
            )
        except (ValueError, TypeError, OverflowError):
            return 1


POST_FIELDS = "id,message,created_time,permalink_url,attachments{media,type,url},comments.limit(0).summary(true),reactions.limit(0).summary(true)"
COMMENT_FIELDS = "id,message,created_time,from,parent,can_comment"


class FacebookGraphClient:
    def __init__(self, access_token: str = ""):
        self._token = access_token
        self.base = f"https://graph.facebook.com/{settings.META_GRAPH_VERSION}"

    @staticmethod
    def node(value):
        return quote(str(value), safe="")

    @staticmethod
    def valid_success(data, shape):
        if not isinstance(data, dict):
            return False
        if shape == "page":
            rows = data.get("data")
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                return False
            paging = data.get("paging", {})
            if not isinstance(paging, dict):
                return False
            cursors = paging.get("cursors", {})
            return isinstance(cursors, dict) and (
                not paging.get("next")
                or (
                    isinstance(paging["next"], str)
                    and isinstance(cursors.get("after"), str)
                    and bool(cursors["after"])
                )
            )
        if shape in ("id", "access_token", "message_id"):
            return isinstance(data.get(shape), str) and bool(data[shape])
        if shape == "private_message_id":
            return any(
                isinstance(data.get(field), str) and bool(data[field])
                for field in ("message_id", "id")
            )
        if shape == "ack":
            return data.get("success") is True or data.get("success") == "true"
        if shape == "reactions":
            summary = data.get("summary")
            return (
                isinstance(summary, dict)
                and isinstance(summary.get("total_count"), int)
                and not isinstance(summary["total_count"], bool)
                and summary["total_count"] >= 0
            )
        return bool(data)

    @sensitive_variables()
    def request(self, method, path, *, params=None, body=None, shape=None):
        attempts = 3 if method == "GET" else 1
        for attempt in range(attempts):
            try:
                with httpx.Client(
                    timeout=httpx.Timeout(20, connect=5), follow_redirects=False
                ) as client:
                    response = client.request(
                        method,
                        f"{self.base}/{path}",
                        params=params,
                        json=body,
                        headers={"Authorization": f"Bearer {self._token}"} if self._token else {},
                    )
                try:
                    data = response.json()
                except ValueError:
                    data = None
                if response.is_success and (
                    not isinstance(data, dict)
                    or "error" not in data
                    and not self.valid_success(data, shape)
                    or "error" in data
                    and not isinstance(data["error"], dict)
                ):
                    logger.warning(
                        "meta_response_invalid method=%s status=%s shape=%s",
                        method,
                        response.status_code,
                        shape or "object",
                    )
                    raise (MetaTemporaryError if method == "GET" else MetaDeliveryUnknown)()
                if not isinstance(data, dict):
                    data = {}
                if response.is_success and "error" not in data:
                    return data
                error = data.get("error", {})
                if not isinstance(error, dict):
                    error = {}
                code = error.get("code") if isinstance(error, dict) else None
                trace = error.get("fbtrace_id", "") if isinstance(error, dict) else ""
                # Diagnostics are allowlisted; never retain the provider's error message.
                info = {
                    "provider_code": code if isinstance(code, int) else None,
                    "subcode": error.get("error_subcode")
                    if isinstance(error.get("error_subcode"), int)
                    else None,
                    "trace_id": trace
                    if isinstance(trace, str) and re.fullmatch(r"[A-Za-z0-9_-]{0,100}", trace)
                    else None,
                }
                logger.warning(
                    "meta_request_failed method=%s status=%s code=%s subcode=%s fbtrace_id=%s",
                    method,
                    response.status_code,
                    info["provider_code"],
                    info["subcode"],
                    info["trace_id"],
                )
                if code in (102, 190) or response.status_code == 401:
                    raise MetaAuthError(**info)
                if code in (10, 200, 299) or response.status_code == 403:
                    raise MetaPermissionError(**info)
                if response.status_code == 429 or code in (4, 17, 32, 613):
                    retry = response.headers.get("Retry-After", "1")
                    raise MetaRateLimitError(**info, retry_after=retry_after_seconds(retry))
                if response.status_code >= 500 or error.get("is_transient"):
                    raise (MetaTemporaryError if method == "GET" else MetaDeliveryUnknown)(**info)
                raise MetaError(**info)
            except httpx.RequestError:
                exc = MetaTemporaryError() if method == "GET" else MetaDeliveryUnknown()
            except (MetaTemporaryError, MetaRateLimitError) as err:
                exc = err
            if attempt == attempts - 1 or exc.retry_after > 30:
                raise exc from None
            time.sleep(max(exc.retry_after, 2**attempt + random.random()))
        raise MetaError()

    def paginate(self, path, **params):
        seen = set()
        while True:
            result = self.request("GET", path, params=params, shape="page")
            for item in result["data"]:
                yield item
            paging = result.get("paging", {})
            after = paging.get("cursors", {}).get("after")
            if not paging.get("next"):
                return
            if not after or after in seen:
                raise MetaError()  # Fail visibly instead of silently truncating a broken cursor loop.
            seen.add(after)
            params["after"] = after

    def get_pages(self):
        return self.paginate("me/accounts", fields="id,name,access_token,tasks", limit=100)

    def get_permissions(self):
        return self.paginate("me/permissions")

    def get_page_feed(self, page_id):
        # /feed intentionally includes visitor content; /posts is not equivalent.
        return self.paginate(f"{self.node(page_id)}/feed", fields=POST_FIELDS, limit=25)

    def get_post(self, post_id):
        return self.request("GET", self.node(post_id), params={"fields": POST_FIELDS}, shape="id")

    def get_post_comments(self, object_id):
        return self.paginate(
            f"{self.node(object_id)}/comments", fields=COMMENT_FIELDS, filter="toplevel", limit=100
        )

    def get_comment_replies(self, comment_id):
        return self.paginate(f"{self.node(comment_id)}/comments", fields=COMMENT_FIELDS, limit=100)

    def get_reactions(self, post_id):
        return self.request(
            "GET",
            f"{self.node(post_id)}/reactions",
            params={"limit": 0, "summary": "true"},
            shape="reactions",
        )

    def reply_to_comment(self, comment_id, message):
        return self.request(
            "POST", f"{self.node(comment_id)}/comments", body={"message": message}, shape="id"
        )

    def create_page_post(self, page_id, message, image_url=""):
        """Publish one text post or one public URL image to a Page.

        Writes intentionally have a single HTTP attempt. The caller persists an
        ambiguous result as DELIVERY_UNKNOWN and never blindly publishes again.
        """
        if image_url:
            return self.request(
                "POST",
                f"{self.node(page_id)}/photos",
                body={"url": image_url, "message": message},
                shape="id",
            )
        return self.request(
            "POST", f"{self.node(page_id)}/feed", body={"message": message}, shape="id"
        )

    def send_comment_private_reply(self, comment_id, message):
        """Send the single comment-triggered Messenger private reply.

        Meta has returned both ``id`` and ``message_id`` across published
        examples. The caller normalizes either non-empty identifier, while a
        malformed successful write remains delivery-unknown and is never retried.
        """
        return self.request(
            "POST",
            f"{self.node(comment_id)}/private_replies",
            body={"message": message},
            shape="private_message_id",
        )

    def get_conversations(self, page_id):
        return self.paginate(
            f"{self.node(page_id)}/conversations", fields="id,updated_time,participants", limit=25
        )

    def get_conversation_messages(self, conversation_id):
        return self.paginate(
            f"{self.node(conversation_id)}/messages",
            fields="id,message,from,to,created_time,attachments",
            limit=50,
        )

    def send_message(self, page_id, recipient_id, text):
        return self.request(
            "POST",
            f"{self.node(page_id)}/messages",
            body={
                "recipient": {"id": recipient_id},
                "messaging_type": "RESPONSE",
                "message": {"text": text},
            },
            shape="message_id",
        )

    def subscribe(self, page_id):
        return self.request(
            "POST",
            f"{self.node(page_id)}/subscribed_apps",
            body={
                "subscribed_fields": [
                    "messages",
                    "message_echoes",
                    "messaging_postbacks",
                    "feed",
                ]
            },
            shape="ack",
        )

    def unsubscribe(self, page_id):
        return self.request("DELETE", f"{self.node(page_id)}/subscribed_apps", shape="ack")

    def health(self, page_id):
        return self.request("GET", self.node(page_id), params={"fields": "id"}, shape="id")
