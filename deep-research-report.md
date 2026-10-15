# OrderHub MVP — Meta Social Commerce системийн архитектур, Meta API судалгаа, Codex хэрэгжүүлэлтийн prompt

## Гүйцэтгэх хураангуй

OrderHub-ийн эхний MVP-г **хоёр тусдаа repository**-той хийх нь хамгийн цэвэр шийдэл байна:

```text
backend/
    Django + Django REST Framework
    PostgreSQL
    Celery
    Redis
    Meta Graph API integration

web/
    Next.js + TypeScript
    Inbox
    Posts / Comments
    Customer / Order panel
```

MVP-ийн үндсэн урсгал:

```text
                FACEBOOK / INSTAGRAM
                         │
             ┌───────────┴───────────┐
             │                       │
          REST API                Webhooks
             │                       │
             └───────────┬───────────┘
                         ▼
                 Django / DRF
                         │
           ┌─────────────┼──────────────┐
           │             │              │
        PostgreSQL     Celery         Redis
           │             │
           │             ├── send message
           │             ├── sync comments
           │             ├── sync posts
           │             └── token refresh
           │
           ▼
       REST API
           │
           ▼
        Next.js
           │
     ┌─────┴─────────────┐
     │                   │
   Inbox             Posts
     │                   │
 Facebook DM       Post → Comments
 Instagram DM     Reply → Customer
     │
 Chat → Customer → Order
```

Facebook Page-ийн хувьд Meta Pages API нь Page-ийн өгөгдлийг унших, engagement/comment удирдах, real-time update авах зэрэг боломж олгодог. Messenger API-аар Page болон хэрэглэгчийн conversation-уудыг авч, conversation-ийн messages-ийг уншиж, `/{PAGE_ID}/messages` endpoint-оор хариу илгээж болно. citeturn15search25turn18search3

Instagram талд одоогийн шинэ **Instagram API with Instagram Login** нь `instagram_business_basic`, `instagram_business_manage_messages`, `instagram_business_manage_comments` permission-үүдийг ашигладаг; API-ийн үндсэн host нь `graph.instagram.com`. citeturn18search0turn20search7

2026 оны аравдугаар сарын 13-ны байдлаар Meta-ийн одоогийн Graph API баримт бичиг `v26.0`-ийг харуулж байгаа тул MVP-д:

```env
META_GRAPH_VERSION=v26.0
```

гэж pin хийж, код дотор version hard-code хийхгүй байх нь зөв. citeturn15search11

Энд нэг чухал архитектурын шийдвэр бий: **Meta access token-уудыг Next.js browser руу огт өгөхгүй.** Next.js зөвхөн OrderHub-ийн Django API-тай ярьж, Django л Meta API-г дуудна.

```text
BAD

Browser
   │
   └── Page Access Token ──→ graph.facebook.com


GOOD

Browser / Next.js
        │
        │ OrderHub auth
        ▼
      Django
        │
        │ encrypted Page Access Token
        ▼
  Meta Graph API
```

Facebook Page access token нь Page-ийн өгөгдлийг read/write/modify хийхэд хэрэглэгддэг бөгөөд эхлээд User Access Token авч, дараа нь Page token гаргана. Meta-ийн одоогийн баримт бичигт long-lived User Access Token-оос гаргасан long-lived Page token нь expiration-гүй гэж тэмдэглэсэн ч access revoke, password/security change, permission removal зэрэг шалтгаанаар хүчингүй болж болно; иймээс “refresh cron” гэхээсээ илүү **token health check + reconnect flow** хийх нь зөв. citeturn18search3turn18search12

Instagram Login-ийн long-lived token бол өөр: Meta нь `refresh_access_token` endpoint өгдөг бөгөөд хүчинтэй, дор хаяж 24 цаг болсон long-lived token-ийг refresh хийхэд шинэ 60 хоногийн хугацаа өгдөг. citeturn19search2turn21search10

## Codex-д шууд өгөх master prompt

Доорх prompt-ыг шинэ Codex task/project-д **бүтнээр нь copy-paste** хийхээр зориулав.

```text
You are a senior full-stack engineer and system architect.

Build a production-minded MVP called "OrderHub".

IMPORTANT:
- All developer-facing README files and user-visible UI copy should be in Mongolian (mn-MN), except code identifiers.
- Produce TWO separate projects/repositories:
    1. backend/
    2. web/
- Do not create a mobile app yet.
- Do not mock Meta integration as the final implementation. Create real integration service classes, while using mocked HTTP responses in automated tests.
- Keep the architecture simple: modular monolith, not microservices.
- Do not expose Meta access tokens to the browser.
- Use PostgreSQL, not SQLite except optionally in isolated unit tests.
- Make Graph API version configurable with META_GRAPH_VERSION.
- Default currently to v26.0.
- Before relying on a Meta field/permission that may have changed, check current official Meta documentation.

============================================================
PRODUCT GOAL
============================================================

OrderHub is a social-commerce inbox/order-management MVP for Mongolian
Facebook/Instagram sellers.

A company should be able to:

1. Sign in to OrderHub.
2. Connect a Facebook Page.
3. Optionally connect an Instagram Professional account.
4. See Facebook Page posts.
5. See comments and reaction/like counts.
6. Reply to comments without opening Facebook/Instagram.
7. See Facebook Messenger conversations.
8. Read conversation history.
9. Reply to customer DMs from OrderHub.
10. See Instagram comments and reply to them.
11. Store customers based on social identities.
12. Create an Order directly while viewing a conversation.
13. Maintain Products and OrderItems.
14. Support multiple companies securely.
15. Receive Meta webhooks and update the local DB.
16. Fall back to periodic sync where appropriate.

The MVP should optimize for:

- correctness
- simple architecture
- debuggability
- tenant isolation
- secure token storage
- idempotent webhook handling
- good local development experience

Do NOT implement:
- AI auto replies
- QPay
- eBarimt
- delivery integrations
- inventory accounting
- native mobile app
- microservices
- Kafka
- Kubernetes

Leave extension points for these later.

============================================================
TECH STACK
============================================================

Backend:
- Python
- Django
- Django REST Framework
- PostgreSQL
- Celery
- Redis
- django-cors-headers
- JWT authentication OR secure HttpOnly cookie-based token auth
- pytest + pytest-django
- requests or httpx for Meta HTTP requests
- cryptography/Fernet or another reviewed application-level encryption
  mechanism for Meta tokens
- drf-spectacular for OpenAPI if practical

Frontend:
- Next.js
- App Router
- TypeScript
- Tailwind CSS
- TanStack Query if useful
- React Hook Form + Zod if useful
- fetch-based typed API client

Deployment:
- Docker
- Docker Compose
- PostgreSQL
- Redis
- Backend
- Celery worker
- Celery beat
- Next.js

============================================================
META ARCHITECTURE
============================================================

Use two provider/auth paths internally.

FACEBOOK PAGE:
Host:
https://graph.facebook.com

Version:
META_GRAPH_VERSION, default v26.0

Facebook minimum requested permissions for this MVP:

- pages_show_list
- pages_read_engagement
- pages_read_user_content
- pages_manage_engagement
- pages_messaging

Do NOT request business_management unless the selected onboarding/business
asset flow actually requires it.

Explain in README why each permission is used.

Suggested mapping:

pages_show_list
    Select Pages that the authenticated user can manage.

pages_read_engagement
    Read Page-authored content and engagement-related Page data.

pages_read_user_content
    Read user-generated content associated with the Page where required.

pages_manage_engagement
    Reply/manage comments and Page engagement.

pages_messaging
    Read/reply to Messenger conversations according to Messenger policies.

Optional future permissions must not be requested by default.

INSTAGRAM:
Prefer current "Instagram API with Instagram Login".

Host:
https://graph.instagram.com

Permissions:
- instagram_business_basic
- instagram_business_manage_comments
- instagram_business_manage_messages

Keep Instagram Login token handling separate from Facebook Page token handling.

Do NOT mix graph.facebook.com tokens and graph.instagram.com tokens
implicitly.

Create a SocialAccount/MetaConnection model with:
- platform
- auth_mode
- graph_host
- external_account_id
- access token
- token expiry
- granted scopes

============================================================
OFFICIAL META DOCUMENTATION
============================================================

Use official Meta documentation as the source of truth.

Pages API:
https://developers.facebook.com/documentation/pages-api

Permissions:
https://developers.facebook.com/documentation/development/permissions

Facebook Access Tokens:
https://developers.facebook.com/documentation/facebook-login/guides/access-tokens

Facebook Long-Lived Tokens:
https://developers.facebook.com/documentation/facebook-login/guides/access-tokens/get-long-lived

Page Conversations:
https://developers.facebook.com/docs/graph-api/reference/page/conversations/

Conversation Messages:
https://developers.facebook.com/docs/graph-api/reference/conversation/messages/

Messenger Platform:
https://developers.facebook.com/documentation/business-messaging/messenger-platform/

Messenger Send Messages:
https://developers.facebook.com/documentation/business-messaging/messenger-platform/send-messages

Messenger Webhooks:
https://developers.facebook.com/documentation/business-messaging/messenger-platform/webhooks

Generic Meta Webhooks:
https://developers.facebook.com/docs/graph-api/webhooks/getting-started/

Instagram API with Instagram Login:
https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login

Instagram Conversations:
https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/conversations-api

Instagram Messaging:
https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/messaging-api

Instagram IG Media Comments:
https://developers.facebook.com/documentation/instagram-platform/instagram-graph-api/reference/ig-media/comments

Instagram IG Comment Replies:
https://developers.facebook.com/documentation/instagram-platform/instagram-graph-api/reference/ig-comment/replies

Instagram Token Refresh:
https://developers.facebook.com/documentation/instagram-platform/reference/refresh_access_token

Instagram App Review:
https://developers.facebook.com/documentation/instagram-platform/app-review

Instagram Webhooks:
https://developers.facebook.com/documentation/instagram-platform/webhooks/fields

Graph API v26:
https://developers.facebook.com/docs/graph-api/changelog/version26.0/

============================================================
META APP SETUP DOCUMENTATION
============================================================

Assume NO Meta App currently exists.

Create docs/META_SETUP.md.

Document this process:

1. Go to Meta for Developers.
2. Create a Meta App appropriate for business integration.
3. Configure Facebook Login/use case required for Pages access.
4. Add Messenger functionality.
5. Add Webhooks.
6. Add Instagram API with Instagram Login if Instagram is enabled.
7. Add OAuth redirect URLs:
   BACKEND_PUBLIC_URL/api/meta/facebook/callback/
   BACKEND_PUBLIC_URL/api/meta/instagram/callback/
8. Configure webhook callback:
   BACKEND_PUBLIC_URL/api/meta/webhook/
9. Configure META_WEBHOOK_VERIFY_TOKEN.
10. Add development/test users and owned test assets while the app is
    in development.
11. Request only required permissions.
12. Implement and test every permission use-case before App Review.
13. Prepare App Review screencasts and written reviewer instructions.
14. Provide a valid Privacy Policy URL.
15. Provide user-data deletion instructions/callback as required.
16. Complete business/access verification if the Meta dashboard requires it.
17. Request Advanced Access/App Review for production access to businesses
    outside the app's own developer/test assets.
18. Switch/publish the app to Live only after requirements are met.

For App Review provide a matrix:

Permission:
pages_show_list
Reviewer action:
Connect Facebook -> show the selectable Page list.

Permission:
pages_read_engagement
Reviewer action:
Open /posts -> show Page posts and reaction/comment counts.

Permission:
pages_read_user_content
Reviewer action:
Show Page user-generated comments/content that the product needs.

Permission:
pages_manage_engagement
Reviewer action:
Open a post -> reply to a comment -> show reply on Facebook.

Permission:
pages_messaging
Reviewer action:
Customer messages Page -> open /inbox -> reply from OrderHub ->
show reply in Messenger.

Instagram:
instagram_business_basic
instagram_business_manage_comments
instagram_business_manage_messages

Provide corresponding Instagram reviewer flows.

Do not falsely claim a permission is approved until App Review actually
approves it.

============================================================
FACEBOOK TOKEN FLOW
============================================================

Implement a backend-only OAuth flow.

Do NOT return access tokens to the browser.

Flow:

Next.js:
GET /api/meta/facebook/connect

Django:
- Generate signed/random OAuth state.
- Store state associated with user/company.
- Redirect to Meta OAuth.

Callback:
GET /api/meta/facebook/callback?code=...&state=...

Django:
1. Validate state.
2. Exchange code for short-lived User Access Token.
3. Exchange it for a long-lived User Access Token.

Token exchange form:

GET
https://graph.facebook.com/v26.0/oauth/access_token

Query params:
grant_type=fb_exchange_token
client_id={META_APP_ID}
client_secret={META_APP_SECRET}
fb_exchange_token={SHORT_LIVED_USER_TOKEN}

Then fetch managed Pages, e.g.:

GET
https://graph.facebook.com/v26.0/me/accounts

fields:
id,name,access_token,tasks

Authorization:
Bearer {LONG_LIVED_USER_TOKEN}

Allow the user to select the Page(s).

Store each Page as a SocialAccount / MetaConnection.

Long-lived Page Access Token:
- encrypt at rest
- never return in serializers
- never write into logs
- associate with company_id
- record granted scopes
- record last token check
- support disconnected/invalid status

Meta documentation states long-lived Page Access Tokens generated from
a long-lived User Access Token do not have a normal expiration.

Therefore:
DO NOT invent a standard OAuth "refresh_token" flow for Facebook Page tokens.

Instead implement:
- token_health_check task
- mark connection invalid when Meta returns auth/token errors
- reconnect endpoint
- optional re-authorization before important expiry/revocation scenarios

============================================================
INSTAGRAM TOKEN FLOW
============================================================

Implement Instagram Login as a separate provider.

Store:
- encrypted access token
- expires_at
- scopes
- ig_user_id
- username/account metadata

Support long-lived token refresh using:

GET
https://graph.instagram.com/refresh_access_token

Query:
grant_type=ig_refresh_token
access_token={CURRENT_LONG_LIVED_TOKEN}

Store the new token and expires_in atomically.

Celery beat should schedule Instagram token refresh well before expiry.

Do not refresh an expired token.
If refresh fails permanently, mark the connection NEEDS_REAUTH.

============================================================
META GRAPH API CLIENT
============================================================

Create:

apps/meta/services/facebook.py
apps/meta/services/instagram.py
apps/meta/services/tokens.py
apps/meta/services/webhooks.py

Provide typed methods rather than calling requests directly throughout views.

FacebookGraphClient:
- get_page_feed()
- get_conversations()
- get_conversation_messages()
- send_message()
- get_post_comments()
- reply_to_comment()
- get_reactions()

InstagramGraphClient:
- get_media_comments()
- reply_to_comment()
- get_conversations()
- get_messages()
- send_message()
- refresh_token()

All API clients:
- use timeouts
- have structured exceptions
- include Meta error code/subcode/fbtrace_id in internal error logs
- never log access_token
- support pagination
- retry only retryable failures
- respect 429 / Retry-After where returned
- do not retry permission/auth failures forever

============================================================
EXACT FACEBOOK REQUESTS
============================================================

Use graph version from settings.

A. PAGE FEED

GET
https://graph.facebook.com/{VERSION}/{page_id}/feed

Example query:

fields=
id,
message,
created_time,
permalink_url,
attachments{media,type,url},
comments.limit(10){id,message,created_time,from},
reactions.limit(0).summary(true)

limit=25

Authorization:
Bearer {PAGE_ACCESS_TOKEN}

Example normalized upstream shape:

{
  "data": [
    {
      "id": "123456789_987654321",
      "message": "Шинэ бараа ирлээ",
      "created_time": "2026-10-13T05:30:00+0000",
      "permalink_url": "https://www.facebook.com/...",
      "comments": {
        "data": [
          {
            "id": "987654321_111111",
            "message": "M размер байна уу?",
            "created_time": "2026-10-13T05:35:00+0000"
          }
        ],
        "paging": {}
      },
      "reactions": {
        "data": [],
        "summary": {
          "total_count": 23,
          "viewer_reaction": "NONE"
        }
      }
    }
  ],
  "paging": {
    "cursors": {
      "before": "...",
      "after": "..."
    },
    "next": "..."
  }
}

Note in the code/comments:
- /feed and /posts are not semantically identical.
- This MVP explicitly implements /{page_id}/feed because that is the
  required endpoint.
- If the UI later needs only Page-authored posts, evaluate /{page_id}/posts.

B. PAGE CONVERSATIONS

GET
https://graph.facebook.com/{VERSION}/{page_id}/conversations

Example fields:
id,
updated_time,
participants,
messages.limit(1){id,message,from,to,created_time}

Example:

GET /v26.0/{PAGE_ID}/conversations
    ?fields=id,updated_time,participants,messages.limit(1){id,message,from,to,created_time}
    &limit=25

Authorization:
Bearer {PAGE_ACCESS_TOKEN}

Representative response:

{
  "data": [
    {
      "id": "t_1000000000001",
      "updated_time": "2026-10-13T06:10:00+0000",
      "participants": {
        "data": [
          {
            "id": "PAGE_SCOPED_USER_ID",
            "name": "Бат"
          },
          {
            "id": "PAGE_ID",
            "name": "OrderHub Demo Store"
          }
        ]
      },
      "messages": {
        "data": [
          {
            "id": "mid.$cAA...",
            "message": "M размер байна уу?",
            "created_time": "2026-10-13T06:10:00+0000"
          }
        ]
      }
    }
  ],
  "paging": {
    "cursors": {
      "before": "...",
      "after": "..."
    },
    "next": "..."
  }
}

Do NOT rely on participant array ordering.
Determine the Page vs customer using known page_id.

C. CONVERSATION MESSAGES

GET
https://graph.facebook.com/{VERSION}/{conversation_id}/messages

Example:

GET /v26.0/{CONVERSATION_ID}/messages
    ?fields=id,message,from,to,created_time,attachments
    &limit=50

Authorization:
Bearer {PAGE_ACCESS_TOKEN}

Representative response:

{
  "data": [
    {
      "id": "mid.$cAA...",
      "message": "M размер байна уу?",
      "from": {
        "id": "PSID",
        "name": "Бат"
      },
      "to": {
        "data": [
          {
            "id": "PAGE_ID",
            "name": "OrderHub Demo Store"
          }
        ]
      },
      "created_time": "2026-10-13T06:10:00+0000"
    }
  ],
  "paging": {
    "cursors": {
      "before": "...",
      "after": "..."
    }
  }
}

Normalize upstream ordering into local sent_at ordering.
Use pagination; never assume one page contains full history.

D. SEND FACEBOOK MESSENGER MESSAGE

POST
https://graph.facebook.com/{VERSION}/{page_id}/messages

Authorization:
Bearer {PAGE_ACCESS_TOKEN}

Content-Type:
application/json

Body:

{
  "recipient": {
    "id": "PAGE_SCOPED_USER_ID"
  },
  "messaging_type": "RESPONSE",
  "message": {
    "text": "Байгаа шүү. M размер 89,000₮."
  }
}

Representative success response:

{
  "recipient_id": "PAGE_SCOPED_USER_ID",
  "message_id": "mid.$cAA..."
}

The public OrderHub endpoint must NOT accept PAGE_SCOPED_USER_ID and
page_id blindly from the browser.

Instead:

POST /api/messages/send/

{
  "conversation_id": "<local UUID>",
  "text": "...",
  "idempotency_key": "<uuid>"
}

Backend:
- resolve company
- resolve conversation
- resolve Page
- resolve recipient
- resolve token
- enforce tenant permission
- create outbound Message as PENDING
- enqueue Celery send task

E. FACEBOOK REACTIONS

For a post/object use the reactions edge where supported:

GET
https://graph.facebook.com/{VERSION}/{post_id}/reactions

Suggested:
fields=id,name,type
summary=total_count
limit=25

For MVP, reaction total_count is more important than storing every actor.

The Reaction model may store individual reactions only when Meta actually
returns that data.

Never fabricate actor identities when the API only provides aggregate count.

F. FACEBOOK COMMENT REPLY

For Facebook comments, encapsulate the relevant comment-edge API inside
FacebookGraphClient.reply_to_comment().

The OrderHub public API is:

POST /api/comments/{local_comment_id}/reply/

{
  "message": "M размер байгаа шүү."
}

The server must derive the Meta comment ID and correct Page token.

Before final implementation, confirm the current v26 Meta comment reply
contract against the official Pages/Graph API documentation.

============================================================
INSTAGRAM REQUESTS
============================================================

Use Instagram API with Instagram Login.

Host:
https://graph.instagram.com

A. GET MEDIA COMMENTS

GET
https://graph.instagram.com/{VERSION}/{ig_media_id}/comments

Example:

GET /v26.0/{IG_MEDIA_ID}/comments
    ?fields=id,text,username,timestamp,replies{id,text,username,timestamp}
    &limit=50

Authorization:
Bearer {IG_ACCESS_TOKEN}

Representative response:

{
  "data": [
    {
      "id": "18000000000000000",
      "text": "Үнэ хэд вэ?",
      "username": "customer_name",
      "timestamp": "2026-10-13T06:20:00+0000"
    }
  ],
  "paging": {
    "cursors": {
      "before": "...",
      "after": "..."
    },
    "next": "..."
  }
}

B. REPLY TO INSTAGRAM COMMENT

POST
https://graph.instagram.com/{VERSION}/{comment_id}/replies

Authorization:
Bearer {IG_ACCESS_TOKEN}

Content-Type:
application/x-www-form-urlencoded
or the encoding currently required by official Meta docs.

message=89,000₮ байгаа шүү.

Representative response:

{
  "id": "18000000000000999"
}

Implement:
InstagramGraphClient.reply_to_comment(comment_external_id, message)

and expose:

POST /api/comments/{local_id}/reply/

The backend detects the platform and dispatches to Facebook or Instagram.

============================================================
WEBHOOK ENDPOINT
============================================================

Create:

GET  /api/meta/webhook/
POST /api/meta/webhook/

GET verification:

Inputs:
hub.mode
hub.verify_token
hub.challenge

Behavior:
- verify META_WEBHOOK_VERIFY_TOKEN using constant-time comparison where
  practical
- if valid return hub.challenge as plain text
- otherwise return HTTP 403

POST:
1. Read RAW request bytes.
2. Read X-Hub-Signature-256.
3. Calculate HMAC-SHA256 using META_APP_SECRET and raw body.
4. Expected header format:
   sha256=<hex digest>
5. Compare with hmac.compare_digest().
6. Reject bad/missing signatures.
7. Parse JSON only AFTER preserving raw bytes/signature validity.
8. Persist RawWebhookEvent.
9. Calculate deduplication key.
10. Enqueue process_webhook_event Celery task.
11. Return 200 quickly.
12. Do not perform slow Graph API sync inline in webhook request.

Representative Messenger webhook:

{
  "object": "page",
  "entry": [
    {
      "id": "PAGE_ID",
      "time": 1791871800000,
      "messaging": [
        {
          "sender": {
            "id": "PAGE_SCOPED_USER_ID"
          },
          "recipient": {
            "id": "PAGE_ID"
          },
          "timestamp": 1791871800000,
          "message": {
            "mid": "mid.$cAA...",
            "text": "M размер байна уу?"
          }
        }
      ]
    }
  ]
}

Representative Facebook Page feed/comment event:

{
  "object": "page",
  "entry": [
    {
      "id": "PAGE_ID",
      "time": 1791871800000,
      "changes": [
        {
          "field": "feed",
          "value": {
            "item": "comment",
            "verb": "add",
            "post_id": "PAGE_ID_POST_ID",
            "comment_id": "COMMENT_ID",
            "parent_id": "PAGE_ID_POST_ID",
            "message": "Үнэ хэд вэ?",
            "created_time": 1791871800
          }
        }
      ]
    }
  ]
}

Representative Instagram comment webhook shape:

{
  "object": "instagram",
  "entry": [
    {
      "id": "IG_USER_ID",
      "time": 1791871800000,
      "changes": [
        {
          "field": "comments",
          "value": {
            "id": "IG_COMMENT_ID",
            "text": "Үнэ хэд вэ?",
            "from": {
              "id": "IG_SCOPED_USER_ID",
              "username": "customer_name"
            },
            "media": {
              "id": "IG_MEDIA_ID",
              "media_product_type": "FEED"
            }
          }
        }
      ]
    }
  ]
}

IMPORTANT:
Webhook payload shapes can vary by field/event type.

Therefore:
- never deserialize into one rigid payload schema
- safely use .get()
- preserve raw payload JSON
- tolerate unknown fields
- dispatch by object + field/event type
- write fixture tests using representative payloads
- make processing idempotent

============================================================
DJANGO WEBHOOK IMPLEMENTATION
============================================================

Implement something equivalent to:

import hashlib
import hmac
import json

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from apps.meta.models import RawWebhookEvent
from apps.meta.tasks import process_webhook_event


def verify_meta_signature(raw_body: bytes, signature: str | None) -> bool:
    if not signature:
        return False

    expected = "sha256=" + hmac.new(
        settings.META_APP_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


@csrf_exempt
def meta_webhook(request):
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if (
            mode == "subscribe"
            and token
            and hmac.compare_digest(
                token,
                settings.META_WEBHOOK_VERIFY_TOKEN,
            )
        ):
            return HttpResponse(challenge or "", content_type="text/plain")

        return HttpResponse(status=403)

    if request.method != "POST":
        return HttpResponse(status=405)

    raw_body = request.body

    if not verify_meta_signature(
        raw_body,
        request.headers.get("X-Hub-Signature-256"),
    ):
        return HttpResponse(status=403)

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    event = RawWebhookEvent.create_idempotently(payload=payload)

    if event.was_created:
        process_webhook_event.delay(str(event.id))

    return JsonResponse({"ok": True})


Refine this into production-quality Django code.

Tests must include:
- valid GET verify
- invalid GET verify token
- valid POST signature
- invalid POST signature
- malformed JSON
- duplicate webhook event
- unknown webhook event type

============================================================
DATABASE DESIGN
============================================================

All IDs should use UUID where practical.

COMPANY

Company:
- id UUID PK
- name varchar
- slug unique
- timezone default "Asia/Ulaanbaatar"
- created_at
- updated_at

CompanyMembership:
- id
- company FK
- user FK
- role: OWNER | ADMIN | AGENT
- unique(company, user)

META / SOCIAL ACCOUNT

SocialAccount:
- id UUID
- company FK
- platform:
    FACEBOOK_PAGE
    INSTAGRAM
- auth_mode:
    FACEBOOK_LOGIN
    INSTAGRAM_LOGIN
- graph_host
- external_account_id
- page_id nullable
- ig_user_id nullable
- display_name
- username nullable
- encrypted_access_token TEXT
- token_expires_at nullable
- granted_scopes JSONB
- status:
    ACTIVE
    NEEDS_REAUTH
    DISCONNECTED
- last_token_check_at nullable
- last_synced_at nullable
- webhook_subscribed_at nullable
- metadata JSONB
- created_at
- updated_at

Constraints:
unique(company, platform, external_account_id)

Never expose encrypted_access_token via DRF serializer.

CUSTOMER

Customer:
- id UUID
- company FK
- platform
- social_account FK
- external_user_id
- name nullable
- username nullable
- avatar_url nullable
- metadata JSONB
- created_at
- updated_at

Constraint:
unique(company, social_account, external_user_id)

Do NOT globally merge Facebook PSID and Instagram scoped ID.
They are provider/account-scoped identities.

CONVERSATION

Conversation:
- id UUID
- company FK
- social_account FK
- customer FK nullable until resolved
- external_id
- platform
- status:
    OPEN
    CLOSED
- unread_count integer
- last_message_at
- last_synced_at
- raw JSONB
- created_at
- updated_at

Constraint:
unique(social_account, external_id)

Index:
(company, last_message_at DESC)

MESSAGE

Message:
- id UUID
- company FK
- conversation FK
- social_account FK
- external_id nullable until sent
- client_idempotency_key nullable
- direction:
    INBOUND
    OUTBOUND
- sender_external_id
- recipient_external_id
- text
- attachments JSONB
- status:
    RECEIVED
    PENDING
    SENDING
    SENT
    FAILED
- provider_error JSONB nullable
- sent_at
- raw JSONB
- created_at
- updated_at

Unique where external_id is not null:
(social_account, external_id)

Unique where idempotency key exists:
(company, client_idempotency_key)

Indexes:
(conversation, sent_at)
(company, status)

POST

Post:
- id UUID
- company FK
- social_account FK
- platform
- external_id
- message nullable
- caption nullable
- permalink_url nullable
- media JSONB
- comment_count integer
- reaction_count integer
- created_at_platform
- raw JSONB
- created_at
- updated_at

Constraint:
unique(social_account, external_id)

COMMENT

Comment:
- id UUID
- company FK
- social_account FK
- post FK nullable
- parent_comment FK self nullable
- external_id
- platform
- author_external_id nullable
- author_name nullable
- author_username nullable
- message
- can_reply boolean default true
- created_at_platform
- raw JSONB
- created_at
- updated_at

Constraint:
unique(social_account, external_id)

Indexes:
(post, created_at_platform)
(parent_comment, created_at_platform)

REACTION

Reaction:
- id UUID
- company FK
- social_account FK
- post FK
- external_id nullable
- actor_external_id nullable
- reaction_type nullable
- created_at_platform nullable
- raw JSONB
- created_at

Individual reactions may not always be available.

Also keep summary count on Post.reaction_count.

PRODUCT

Product:
- id UUID
- company FK
- sku
- name
- description
- price Decimal
- currency default MNT
- stock_qty Decimal
- is_active
- created_at
- updated_at

Constraint:
unique(company, sku)

ORDER

Order:
- id UUID
- company FK
- customer FK
- conversation FK nullable
- status:
    DRAFT
    CONFIRMED
    PAID
    FULFILLING
    COMPLETED
    CANCELLED
- currency default MNT
- subtotal
- total
- notes
- created_by FK User
- created_at
- updated_at

OrderItem:
- id
- order FK
- product FK nullable
- product_name snapshot
- sku snapshot
- quantity
- unit_price
- line_total

RAW WEBHOOK

RawWebhookEvent:
- id UUID
- company FK nullable initially
- social_account FK nullable initially
- object_type
- external_account_id nullable
- dedupe_key unique
- signature_valid
- payload JSONB
- status:
    RECEIVED
    PROCESSING
    PROCESSED
    IGNORED
    FAILED
- error TEXT nullable
- received_at
- processed_at nullable

============================================================
MULTI-TENANCY
============================================================

This is mandatory.

Every business domain model must be scoped by company.

A user can belong to multiple companies.

Implement request active-company context, for example:
X-Company-ID header
or a company slug in the session/JWT.

However:
- never trust X-Company-ID by itself
- verify CompanyMembership
- every queryset must be tenant-filtered
- every mutation must re-check object belongs to active company
- SocialAccount token lookup must include company_id

BAD:
Conversation.objects.get(id=id)

GOOD:
Conversation.objects.get(
    id=id,
    company=request.active_company,
)

Create reusable:
- ActiveCompanyMiddleware or equivalent
- TenantQueryMixin
- IsCompanyMember permission
- IsCompanyAdmin where needed

Write cross-tenant security tests.

A user from Company A must receive 404/403 when requesting:
- Company B conversation
- Company B messages
- Company B posts
- Company B comments
- Company B orders
- Company B Meta connection

============================================================
TOKEN ENCRYPTION
============================================================

Do not store plain access tokens.

Implement a service similar to:

from cryptography.fernet import Fernet
from django.conf import settings


class TokenCipher:
    def __init__(self):
        self.fernet = Fernet(
            settings.TOKEN_ENCRYPTION_KEY.encode("utf-8")
        )

    def encrypt(self, token: str) -> str:
        return self.fernet.encrypt(
            token.encode("utf-8")
        ).decode("utf-8")

    def decrypt(self, encrypted_token: str) -> str:
        return self.fernet.decrypt(
            encrypted_token.encode("utf-8")
        ).decode("utf-8")


Production README must say:
- .env encryption key is acceptable for MVP
- production should preferably use a managed secret/KMS strategy
- rotating TOKEN_ENCRYPTION_KEY requires a migration/rotation procedure

NEVER:
- expose tokens via admin list_display
- include tokens in __str__
- include them in error monitoring
- print Graph URLs containing access_token query parameter

Prefer Authorization: Bearer header where supported.

============================================================
CELERY TASKS
============================================================

Implement:

process_webhook_event(event_id)

sync_page_feed(social_account_id)

sync_post_comments(post_id)

sync_reactions(post_id)

sync_conversations(social_account_id)

sync_conversation_messages(conversation_id)

send_meta_message(message_id)

reply_to_comment(comment_id, text, outbound_action_id)

refresh_instagram_token(social_account_id)

check_meta_token_health(social_account_id)

periodic_incremental_sync()

Rules:
- exponential backoff + jitter
- bounded retries
- retry network timeouts / 429 / appropriate 5xx
- do not endlessly retry permission/auth 4xx
- persist final provider error
- mark token NEEDS_REAUTH where appropriate
- idempotent upserts

Example send task:

@shared_task(bind=True, max_retries=5)
def send_meta_message(self, message_id: str):
    msg = (
        Message.objects
        .select_related(
            "conversation",
            "social_account",
            "company",
        )
        .get(id=message_id)
    )

    if msg.status == Message.Status.SENT:
        return

    account = msg.social_account

    try:
        token = token_cipher.decrypt(account.encrypted_access_token)

        client = FacebookGraphClient(
            access_token=token,
            graph_version=settings.META_GRAPH_VERSION,
        )

        msg.status = Message.Status.SENDING
        msg.save(update_fields=["status", "updated_at"])

        result = client.send_message(
            page_id=account.page_id,
            recipient_id=msg.recipient_external_id,
            text=msg.text,
        )

        msg.external_id = result["message_id"]
        msg.status = Message.Status.SENT
        msg.provider_error = None
        msg.save(
            update_fields=[
                "external_id",
                "status",
                "provider_error",
                "updated_at",
            ]
        )

    except MetaRateLimitError as exc:
        raise self.retry(
            exc=exc,
            countdown=min(2 ** self.request.retries, 300),
        )

    except MetaAuthError as exc:
        account.status = SocialAccount.Status.NEEDS_REAUTH
        account.save(update_fields=["status", "updated_at"])

        msg.status = Message.Status.FAILED
        msg.provider_error = exc.safe_payload
        msg.save(
            update_fields=[
                "status",
                "provider_error",
                "updated_at",
            ]
        )

    except MetaTemporaryError as exc:
        raise self.retry(
            exc=exc,
            countdown=min(2 ** self.request.retries, 300),
        )

Refine this implementation.

============================================================
ORDERHUB REST API
============================================================

AUTH:

POST /api/auth/register/
POST /api/auth/login/
POST /api/auth/refresh/
POST /api/auth/logout/
GET  /api/auth/me/

COMPANIES:

GET  /api/companies/
POST /api/companies/
GET  /api/companies/{id}/

META:

GET  /api/meta/accounts/
GET  /api/meta/facebook/connect/
GET  /api/meta/facebook/callback/
GET  /api/meta/instagram/connect/
GET  /api/meta/instagram/callback/
POST /api/meta/accounts/{id}/sync/
DELETE /api/meta/accounts/{id}/

WEBHOOK:

GET  /api/meta/webhook/
POST /api/meta/webhook/

CONVERSATIONS:

GET /api/conversations/
GET /api/conversations/{id}/
GET /api/conversations/{id}/messages/

Filters:
platform
social_account
status
search

Cursor pagination preferred.

MESSAGES:

POST /api/messages/send/

Body:

{
  "conversation_id": "uuid",
  "text": "Хаягаа явуулаарай.",
  "idempotency_key": "uuid"
}

Return immediately after creating PENDING message:

{
  "id": "uuid",
  "status": "PENDING",
  "text": "Хаягаа явуулаарай."
}

Use Celery for actual upstream sending.

POSTS:

GET  /api/posts/
GET  /api/posts/{id}/
POST /api/posts/sync/

Filter:
social_account
platform
search

COMMENTS:

GET  /api/posts/{post_id}/comments/

POST /api/comments/{comment_id}/reply/

Body:
{
  "message": "M размер байгаа шүү."
}

REACTIONS:

GET /api/posts/{post_id}/reactions/

At minimum return:

{
  "total_count": 23,
  "items": []
}

CUSTOMERS:

GET /api/customers/
GET /api/customers/{id}/

PRODUCTS:

GET  /api/products/
POST /api/products/
GET  /api/products/{id}/
PATCH /api/products/{id}/

ORDERS:

GET  /api/orders/
POST /api/orders/
GET  /api/orders/{id}/
PATCH /api/orders/{id}/

Example create:

{
  "customer_id": "uuid",
  "conversation_id": "uuid",
  "items": [
    {
      "product_id": "uuid",
      "quantity": 1
    }
  ],
  "notes": "Facebook Messenger захиалга"
}

Server calculates price and totals.

Never trust total sent by browser.

============================================================
NEXT.JS UI
============================================================

Create:

/login
/inbox
/posts
/posts/[id]
/products
/orders
/settings/integrations

Primary MVP pages are:
/inbox
/posts/[id]

Use responsive desktop-first UI.

------------------------------------------------------------
INBOX WIREFRAME
------------------------------------------------------------

┌──────────────────────────────────────────────────────────────────────┐
│ OrderHub                    Company: Demo Shop             User ▼    │
├───────────────┬─────────────────────────┬────────────────────────────┤
│ NAVIGATION    │ CONVERSATIONS           │ CHAT                       │
│               │                         │                            │
│ Inbox         │ 🔵 Бат                  │ Бат                        │
│ Posts         │ M размер байна уу?      │ Facebook Messenger         │
│ Orders        │ 2m                      │                            │
│ Products      │                         │ Бат:                       │
│               │ 🟣 @naraa               │ M размер байна уу?         │
│ Settings      │ Үнэ хэд вэ?             │                            │
│               │ 12m                     │ Та:                        │
│               │                         │ Байгаа шүү.                │
│               │                         │                            │
│               │                         │ ┌────────────────────────┐ │
│               │                         │ │ Message...             │ │
│               │                         │ └───────────────────Send─┘ │
├───────────────┴─────────────────────────┼────────────────────────────┤
│                                         │ CUSTOMER / ORDER           │
│                                         │ Бат                        │
│                                         │ Previous orders: 2         │
│                                         │                            │
│                                         │ Product: [ Hoodie M ▼ ]    │
│                                         │ Qty:     [ 1 ]             │
│                                         │ Price:   89,000₮           │
│                                         │                            │
│                                         │ [ Create Draft Order ]     │
└─────────────────────────────────────────┴────────────────────────────┘

For smaller screens, customer/order panel can become drawer.

Requirements:
- conversation list
- platform badge
- last message
- last message timestamp
- active conversation
- message bubbles
- pending/sent/failed status for outbound
- retry button for failed message if safe
- reply box
- Create Order panel
- optimistic UI optional, but server status is authoritative

------------------------------------------------------------
POST DETAIL WIREFRAME
------------------------------------------------------------

┌───────────────────────────────────────────────────────────────────┐
│ ← Posts                                           Demo Shop       │
├───────────────────────────────────────────────────────────────────┤
│ POST                                                              │
│                                                                   │
│ [image]                                                           │
│ Шинэ hoodie ирлээ                                                 │
│                                                                   │
│ 👍 124        💬 36                   View on Facebook ↗          │
├──────────────────────────────┬────────────────────────────────────┤
│ COMMENTS                     │ COMMENT DETAIL / CUSTOMER          │
│                              │                                    │
│ Бат                          │ Бат                                │
│ M размер байна уу?           │ Facebook                           │
│ 2m                           │                                    │
│ [Reply]                      │ Comment:                           │
│                              │ M размер байна уу?                 │
│ Naraa                        │                                    │
│ Үнэ хэд вэ?                  │ Reply:                             │
│ 5m                           │ ┌────────────────────────────────┐ │
│ [Reply]                      │ │ M байгаа шүү, 89,000₮.        │ │
│                              │ └────────────────────────────────┘ │
│                              │ [ Send reply ]                     │
└──────────────────────────────┴────────────────────────────────────┘

Requirements:
- post text/media
- permalink
- comment count
- reaction count
- comments
- nested replies where available
- comment reply form
- loading/error states
- disabled button while sending
- provider error shown in safe user language

============================================================
NEXT.JS API CLIENT
============================================================

Create a shared API client.

Example:

const API_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    public payload: unknown,
  ) {
    super(`API error: ${status}`);
  }
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
  });

  if (!response.ok) {
    let payload: unknown = null;

    try {
      payload = await response.json();
    } catch {
      payload = null;
    }

    throw new ApiError(response.status, payload);
  }

  return response.json() as Promise<T>;
}

If JWT is used instead of cookie auth, do not store long-lived auth
credentials insecurely in localStorage without documenting the decision.

Prefer secure HttpOnly cookie-based authentication if implementation remains
simple.

============================================================
EXAMPLE NEXT.JS INBOX LOGIC
============================================================

Create typed components.

Example shape:

type Conversation = {
  id: string;
  platform: "FACEBOOK_PAGE" | "INSTAGRAM";
  customer: {
    id: string;
    name: string | null;
    username: string | null;
  } | null;
  last_message_at: string | null;
  unread_count: number;
};

type Message = {
  id: string;
  direction: "INBOUND" | "OUTBOUND";
  text: string;
  status:
    | "RECEIVED"
    | "PENDING"
    | "SENDING"
    | "SENT"
    | "FAILED";
  sent_at: string;
};

async function sendMessage(
  conversationId: string,
  text: string,
) {
  return apiFetch<Message>("/api/messages/send/", {
    method: "POST",
    body: JSON.stringify({
      conversation_id: conversationId,
      text,
      idempotency_key: crypto.randomUUID(),
    }),
  });
}

Implement:
- ConversationList
- ConversationHeader
- MessageList
- MessageBubble
- MessageComposer
- CustomerPanel
- CreateOrderForm

Use TanStack Query polling at approximately 3-5 seconds for MVP if a
dedicated browser WebSocket layer would add unnecessary complexity.

Do NOT implement frontend WebSockets solely because this is a chat UI.

Meta -> Django already uses webhooks.

Browser real-time transport can be added later.

============================================================
POST DETAIL COMPONENTS
============================================================

Implement:
- PostCard
- PostStats
- CommentList
- CommentItem
- CommentReplyForm

Example:

async function replyToComment(
  commentId: string,
  message: string,
) {
  return apiFetch(`/api/comments/${commentId}/reply/`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

On success:
- invalidate post comments query
- refresh relevant post stats
- show success state

On failure:
- preserve input
- show a safe provider error
- do not leak Meta token/error internals

============================================================
SECURITY REQUIREMENTS
============================================================

Mandatory:

1. Multi-tenant isolation.
2. Meta access tokens backend-only.
3. Access tokens encrypted at rest.
4. X-Hub-Signature-256 verification.
5. OAuth state validation.
6. Exact redirect URL configuration.
7. CORS allow-list, not "*", in production.
8. Secure cookies in production.
9. CSRF protection if cookie/session auth requires it.
10. HTTPS production-only.
11. Rate limiting.
12. Object-level authorization.
13. Webhook deduplication.
14. Outbound message idempotency.
15. Audit-safe logging.
16. Never log secrets.
17. Validate all user input.
18. Never allow browser to select an arbitrary Page ID/token pair.
19. Totals/prices computed server-side.
20. Use database transactions when creating Order + OrderItems.

DRF throttles:

- standard authenticated API per-user/per-company
- stricter /messages/send
- stricter comment reply endpoint
- stricter auth endpoints

Do not invent a fake fixed Meta API quota.

Instead:
- observe Meta error responses
- handle HTTP 429
- store safe usage/error metadata where useful
- exponential backoff

============================================================
WEBHOOK SECURITY TEST
============================================================

Implement a test helper:

def sign_meta_payload(payload: bytes, app_secret: str) -> str:
    return "sha256=" + hmac.new(
        app_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

Then test:

raw = b'{"object":"page","entry":[]}'

signature = sign_meta_payload(
    raw,
    settings.META_APP_SECRET,
)

client.post(
    "/api/meta/webhook/",
    data=raw,
    content_type="application/json",
    HTTP_X_HUB_SIGNATURE_256=signature,
)

Expected:
200

Changing one byte of raw body:
Expected:
403

============================================================
LOCAL DEVELOPMENT
============================================================

Provide README steps.

Backend:

cp .env.example .env
docker compose up --build

Run migrations:
docker compose exec backend python manage.py migrate

Create superuser:
docker compose exec backend python manage.py createsuperuser

Frontend:

cp .env.example .env.local
npm install
npm run dev

Use ngrok for Meta callbacks/webhooks:

ngrok http 8000

Example:
https://orderhub-dev.ngrok.app

Set:

BACKEND_PUBLIC_URL=https://orderhub-dev.ngrok.app

Meta webhook:
https://orderhub-dev.ngrok.app/api/meta/webhook/

Facebook OAuth callback:
https://orderhub-dev.ngrok.app/api/meta/facebook/callback/

Instagram callback:
https://orderhub-dev.ngrok.app/api/meta/instagram/callback/

Document:
- free ngrok URLs can change
- changing domain means Meta callback/redirect configuration may need update
- a reserved static development domain is easier

Provide a management command for fixture/demo data:

python manage.py seed_demo

Provide another command if useful:

python manage.py sync_meta_account <uuid>

============================================================
ENVIRONMENT VARIABLES
============================================================

backend/.env.example:

DJANGO_SETTINGS_MODULE=config.settings.local
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,.ngrok-free.app

DATABASE_URL=postgresql://orderhub:orderhub@postgres:5432/orderhub
REDIS_URL=redis://redis:6379/0

FRONTEND_URL=http://localhost:3000
BACKEND_PUBLIC_URL=http://localhost:8000

META_GRAPH_VERSION=v26.0
META_APP_ID=
META_APP_SECRET=
META_WEBHOOK_VERIFY_TOKEN=

META_FACEBOOK_REDIRECT_URI=http://localhost:8000/api/meta/facebook/callback/
META_INSTAGRAM_REDIRECT_URI=http://localhost:8000/api/meta/instagram/callback/

TOKEN_ENCRYPTION_KEY=

CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

SENTRY_DSN=

web/.env.example:

NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

Do NOT put:
META_APP_SECRET
META_PAGE_ACCESS_TOKEN
META_INSTAGRAM_ACCESS_TOKEN
TOKEN_ENCRYPTION_KEY

into NEXT_PUBLIC_* variables.

============================================================
DOCKER COMPOSE
============================================================

backend/docker-compose.yml should have:

services:
  postgres
  redis
  backend
  celery
  celery-beat

Suggested ports:
postgres internal 5432
redis internal 6379
backend localhost:8000

Backend must wait/retry DB availability cleanly.

Optional:
adminer/pgadmin should NOT be included by default unless clearly marked
development-only.

web/ should have its own Dockerfile.

Also provide an optional root/local orchestration example in documentation
showing how backend and web can run together.

============================================================
BACKEND ADMIN
============================================================

Register:

Company
CompanyMembership
SocialAccount
Customer
Conversation
Message
Post
Comment
Product
Order
OrderItem
RawWebhookEvent

Security:
- token field never displayed raw
- token admin field shown only as:
  "configured"
  "missing"
  "needs reauth"

Add useful filters:
- company
- platform
- status
- created date

============================================================
TESTING
============================================================

Backend:
pytest

Required unit/integration tests:

AUTH:
- login
- unauthorized access

MULTI TENANT:
- Company A cannot read Company B conversation
- Company A cannot send using Company B social account
- Company A cannot access Company B order
- Company A cannot reply to Company B comment

WEBHOOK:
- verification GET
- bad verify token
- valid signature
- invalid signature
- duplicate event
- messenger message fixture
- Facebook comment fixture
- Instagram comment fixture
- unknown event safely ignored

META CLIENT:
Mock HTTP with responses/respx equivalent.

Test:
- feed pagination
- conversations pagination
- messages pagination
- message send success
- 400 permission failure
- auth failure
- 429 rate limit
- retryable 500
- IG comment reply
- IG token refresh

ORDERS:
- create order from conversation
- server calculates totals
- stock not required yet
- customer ownership validated

CELERY:
- outbound message transition:
  PENDING -> SENDING -> SENT
- failure:
  PENDING -> FAILED
- idempotent SENT message is not re-sent

TOKEN:
- encrypted DB value does not equal plaintext token
- decrypt roundtrip
- token not returned by API

Frontend:
- use Vitest/Jest + React Testing Library
- list conversations
- select conversation
- render message
- submit message
- disabled sending state
- comment reply form
- API error state
- tenant/company selector where applicable

Optional Playwright:
- login
- inbox
- post/comment flow using mocked backend

============================================================
API DOCUMENTATION
============================================================

Generate:
- OpenAPI schema
- Swagger/Redoc in development
- docs/API.md

Document pagination and errors.

Standard safe error shape:

{
  "code": "META_PERMISSION_ERROR",
  "message": "Facebook холболтын зөвшөөрөл хүчингүй байна.",
  "details": {}
}

Do not return raw access tokens or entire provider payload errors to browser.

============================================================
IMPLEMENTATION ORDER
============================================================

Implement in this exact order.

PHASE A
- Create backend repo
- Django project
- Postgres
- Redis
- Celery
- Docker
- auth
- Company + membership
- tests

PHASE B
- SocialAccount
- token encryption
- Facebook OAuth
- Page selection
- Meta API client
- token tests

PHASE C
- Post
- Comment
- Reaction
- feed sync
- comment sync
- comment reply
- tests

PHASE D
- Customer
- Conversation
- Message
- conversations sync
- messages sync
- send Messenger message
- tests

PHASE E
- webhook verification
- RawWebhookEvent
- Messenger event processor
- Page feed/comment event processor
- idempotency
- tests

PHASE F
- Instagram Login
- IG tokens
- media comments
- comment reply
- messaging
- token refresh
- tests

PHASE G
- Product
- Order
- OrderItem
- Create order from conversation
- tests

PHASE H
- Next.js repo
- auth
- app shell
- company context
- /inbox
- /posts
- /posts/[id]
- /products
- /orders
- /settings/integrations

PHASE I
- Docker
- local dev docs
- ngrok docs
- App Review docs
- deployment docs
- final integration tests

============================================================
ACCEPTANCE CRITERIA
============================================================

The implementation is complete only when all of these are true:

1. docker compose up starts backend/Postgres/Redis/Celery.
2. migrations run cleanly from an empty DB.
3. user can authenticate.
4. company can be created.
5. Facebook connect flow exists.
6. Page token is encrypted in PostgreSQL.
7. /posts shows locally synced Meta Page feed data.
8. /posts/[id] shows comments.
9. comment reply hits the appropriate Meta integration.
10. /inbox lists Facebook Messenger conversations.
11. selecting a conversation loads messages.
12. reply creates a PENDING local Message.
13. Celery sends the message and records provider message_id.
14. webhook receives customer messages.
15. webhook signature is verified before processing.
16. duplicate webhook does not create duplicate local messages.
17. Instagram comments/replies work through provider abstraction.
18. IG token refresh logic exists and is tested.
19. Company A can never read/write Company B resources.
20. no Meta access token is exposed through frontend API/browser.
21. automated tests pass.
22. README explains exact local setup.
23. docs/META_SETUP.md explains Meta App setup/App Review.
24. .env.example exists in both repos.
25. code contains no real Meta secret/token.

============================================================
FINAL OUTPUT FROM CODEX
============================================================

Do not only describe what should be built.

Actually create the files.

At the end provide:

1. Summary of architecture.
2. Complete file tree.
3. Database migrations created.
4. Commands to run backend.
5. Commands to run frontend.
6. Commands to run tests.
7. Exact remaining manual Meta Developer Dashboard steps.
8. Permissions requested.
9. Any Meta endpoint/field whose current official v26 behavior required
   adjustment from this specification.
10. Known MVP limitations.

Before finishing:
- run backend tests
- run frontend tests
- run lint/typecheck
- fix errors
- show final command results.

Output explanations in Mongolian (mn-MN).
```

## Шаардлагатай файлын бүтэц

Codex-ийн үүсгэх ёстой **хоёр repo**-г би дараах байдлаар зохион байгуулна. Backend-ийг “social” гэсэн нэг аварга app болгохоос илүү domain-аар салгах нь дараа нь OrderHub өргөжихөд цэвэр.

```text
orderhub/
│
├── backend/
│   ├── .env.example
│   ├── .gitignore
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── manage.py
│   ├── pyproject.toml
│   ├── README.md
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   ├── wsgi.py
│   │   ├── celery.py
│   │   └── settings/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── local.py
│   │       └── production.py
│   │
│   ├── apps/
│   │   ├── accounts/
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── urls.py
│   │   │   └── tests/
│   │   │
│   │   ├── companies/
│   │   │   ├── models.py
│   │   │   ├── permissions.py
│   │   │   ├── middleware.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   └── tests/
│   │   │
│   │   ├── meta/
│   │   │   ├── models.py
│   │   │   ├── admin.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── urls.py
│   │   │   ├── tasks.py
│   │   │   ├── exceptions.py
│   │   │   ├── constants.py
│   │   │   │
│   │   │   ├── services/
│   │   │   │   ├── facebook.py
│   │   │   │   ├── instagram.py
│   │   │   │   ├── tokens.py
│   │   │   │   ├── oauth.py
│   │   │   │   ├── encryption.py
│   │   │   │   └── webhooks.py
│   │   │   │
│   │   │   └── tests/
│   │   │       ├── fixtures/
│   │   │       │   ├── fb_message.json
│   │   │       │   ├── fb_comment.json
│   │   │       │   └── ig_comment.json
│   │   │       ├── test_webhook.py
│   │   │       ├── test_facebook_client.py
│   │   │       ├── test_instagram_client.py
│   │   │       ├── test_tokens.py
│   │   │       └── test_tasks.py
│   │   │
│   │   ├── inbox/
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── services.py
│   │   │   ├── urls.py
│   │   │   └── tests/
│   │   │
│   │   ├── social/
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   ├── urls.py
│   │   │   └── tests/
│   │   │
│   │   ├── catalog/
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   └── tests/
│   │   │
│   │   └── orders/
│   │       ├── models.py
│   │       ├── serializers.py
│   │       ├── services.py
│   │       ├── views.py
│   │       └── tests/
│   │
│   ├── docs/
│   │   ├── META_SETUP.md
│   │   ├── APP_REVIEW.md
│   │   ├── API.md
│   │   ├── SECURITY.md
│   │   └── LOCAL_DEVELOPMENT.md
│   │
│   └── scripts/
│       └── entrypoint.sh
│
└── web/
    ├── .env.example
    ├── .gitignore
    ├── Dockerfile
    ├── package.json
    ├── tsconfig.json
    ├── next.config.ts
    ├── README.md
    │
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx
    │   │
    │   ├── login/
    │   │   └── page.tsx
    │   │
    │   ├── inbox/
    │   │   └── page.tsx
    │   │
    │   ├── posts/
    │   │   ├── page.tsx
    │   │   └── [id]/
    │   │       └── page.tsx
    │   │
    │   ├── products/
    │   │   └── page.tsx
    │   │
    │   ├── orders/
    │   │   ├── page.tsx
    │   │   └── [id]/
    │   │       └── page.tsx
    │   │
    │   └── settings/
    │       └── integrations/
    │           └── page.tsx
    │
    ├── components/
    │   ├── layout/
    │   │   ├── AppSidebar.tsx
    │   │   └── CompanySwitcher.tsx
    │   │
    │   ├── inbox/
    │   │   ├── ConversationList.tsx
    │   │   ├── ConversationItem.tsx
    │   │   ├── ConversationHeader.tsx
    │   │   ├── MessageList.tsx
    │   │   ├── MessageBubble.tsx
    │   │   ├── MessageComposer.tsx
    │   │   ├── CustomerPanel.tsx
    │   │   └── CreateOrderForm.tsx
    │   │
    │   ├── posts/
    │   │   ├── PostCard.tsx
    │   │   ├── PostStats.tsx
    │   │   ├── CommentList.tsx
    │   │   ├── CommentItem.tsx
    │   │   └── CommentReplyForm.tsx
    │   │
    │   └── ui/
    │       ├── Button.tsx
    │       ├── Input.tsx
    │       ├── Modal.tsx
    │       └── Spinner.tsx
    │
    ├── lib/
    │   ├── api.ts
    │   ├── auth.ts
    │   ├── query-client.ts
    │   └── format.ts
    │
    ├── hooks/
    │   ├── useConversations.ts
    │   ├── useMessages.ts
    │   ├── usePosts.ts
    │   └── useComments.ts
    │
    └── types/
        ├── auth.ts
        ├── inbox.ts
        ├── posts.ts
        ├── orders.ts
        └── products.ts
```

`SocialAccount` model-ийг тусад нь оруулсан нь user-ийн анх хүссэн model жагсаалтаас нэгээр нэмэгдсэн боловч зайлшгүй хэрэгтэй. Учир нь нэг `Company` хэд хэдэн Facebook Page болон Instagram account холбож болох бөгөөд token-ыг `Company` дээр ганц field болгон хадгалбал multi-page, multi-platform архитектур шууд эвдэрнэ.

## Meta API contract, permissions ба token lifecycle

### Permission-үүдийг хамгийн бага хүрээнд авах

Facebook MVP-ийн permission зураглал:

| Permission | OrderHub-д юунд хэрэглэх |
|---|---|
| `pages_show_list` | Login хийсэн хэрэглэгчийн удирдах Page-уудаас сонгох |
| `pages_read_engagement` | Page content, post болон engagement мэдээлэл унших |
| `pages_read_user_content` | Page дээрх хэрэглэгчийн үүсгэсэн content/comment хэрэгтэй тохиолдолд унших |
| `pages_manage_engagement` | Comment/reply болон Page engagement удирдах |
| `pages_messaging` | Messenger conversation/message унших, хариу өгөх |

Meta-ийн permission reference нь `pages_read_engagement`, `pages_show_list` зэрэг Page permission-уудыг одоогоор тусад нь тодорхойлдог бөгөөд Page management documentation нь `pages_manage_engagement`, `pages_read_engagement` зэрэг permission-уудыг Page ажиллагаанд ашигладаг. citeturn15search13turn15search1

`business_management`-ийг **зүгээр байж магадгүй гээд MVP-д шууд авах хэрэггүй**. Тухайн Business Manager asset onboarding flow бодитоор шаардвал нэмж App Review хийх нь зөв. Permission бүр App Review-ийг илүү төвөгтэй болгодог тул least-privilege зарчим хэрэгтэй.

Instagram-ийн шинэ login flow-д:

```text
instagram_business_basic
instagram_business_manage_comments
instagram_business_manage_messages
```

гэж авах нь зөв; эдгээр scope-ийг Meta одоогийн Instagram Login API дээр тодорхой заасан. citeturn18search0turn18search7turn18search10

### App Review-ийн бодит дараалал

Development үеэр app developer/tester болон өөрийн test assets дээр integration-аа эхлээд ажиллуулна. Харин бусад дэлгүүрүүд OrderHub-д өөрсдийн Page/Instagram account-аа холбоно гэвэл production access-д шаардлагатай permissions/features-ийн **Advanced Access / App Review** шаардлага орж ирнэ. Instagram-ийн Meta App Review documentation мөн `instagram_business_*` permissions-ийг review-д оруулах flow-ийг тусгайлан заадаг. citeturn6search12turn18search0

App Review-д Codex-оор `APP_REVIEW.md` үүсгүүлж, permission бүрт тусгай demo flow бэлтгэнэ:

```text
pages_read_engagement
Reviewer:
Connect Facebook
→ select Demo Page
→ Posts
→ post list харагдана

pages_manage_engagement
Reviewer:
Posts
→ open a post
→ reply "Test reply"
→ Facebook дээр reply үүссэнийг үзүүлнэ

pages_messaging
Reviewer:
Test customer → Messenger → "Hello"
→ OrderHub /inbox
→ conversation харагдана
→ OrderHub-аас reply
→ Messenger дээр reply ирнэ
```

Энэ нь “манай app-д permission хэрэгтэй” гэж ерөнхий бичсэнээс хамаагүй review-friendly.

### Facebook token lifecycle

Flow:

```text
Facebook OAuth
      │
      ▼
Short-lived User Token
      │
      │ fb_exchange_token
      ▼
Long-lived User Token
      │
      │ /me/accounts
      ▼
Page Access Token
      │
      ▼
Encrypted PostgreSQL
```

Meta-ийн Access Token documentation-аар Page access token авахын тулд эхлээд User Access Token авдаг. Long-lived Page token-ийг long-lived User token-оос гаргаж болдог бөгөөд одоогийн Meta documentation түүнийг expiration-гүй гэж тэмдэглэсэн. citeturn18search3turn18search12

Тиймээс Facebook token scheduler:

```text
❌ Every 30 days refresh page token

✅ Every day:
   check connection health
        ↓
   active → nothing
   auth error → NEEDS_REAUTH
        ↓
   user presses Reconnect Facebook
```

байх нь илүү зөв.

### Instagram token lifecycle

Instagram Login:

```text
IG OAuth
  ↓
token
  ↓
long-lived token
  ↓
encrypted DB
  ↓
Celery Beat
  ↓
refresh_access_token before expiry
```

Meta-ийн current endpoint:

```http
GET https://graph.instagram.com/refresh_access_token
    ?grant_type=ig_refresh_token
    &access_token={LONG_LIVED_TOKEN}
```

Meta-ийн documentation-аар хүчинтэй, 24 цагаас дээш настай long-lived token refresh хийж болох ба refreshed token нь 60 хоногийн хугацаатай. citeturn19search2turn21search10

Иймд DB дээр:

```text
token_expires_at
last_token_check_at
status
```

заавал хадгал.

### Instagram API-г Facebook Graph API-тай битгий холь

Шинэ Instagram Login API-ийн үндсэн host:

```text
https://graph.instagram.com
```

гэдгийг Meta одоогийн reference дээр шууд тодорхойлдог. citeturn20search7turn21search4

Тиймээс ийм код муу:

```python
BASE_URL = "https://graph.facebook.com"
```

бүх provider дээр.

Харин:

```python
class SocialPlatform(models.TextChoices):
    FACEBOOK_PAGE = "FACEBOOK_PAGE"
    INSTAGRAM = "INSTAGRAM"


class AuthMode(models.TextChoices):
    FACEBOOK_LOGIN = "FACEBOOK_LOGIN"
    INSTAGRAM_LOGIN = "INSTAGRAM_LOGIN"
```

болгоод:

```text
Facebook
graph.facebook.com
Page Access Token

Instagram Login
graph.instagram.com
Instagram User Access Token
```

гэж provider-specific байлгах хэрэгтэй.

## Endpoint-үүд, webhook flow ба өгөгдлийн дизайн

### Facebook Page feed

Хэрэглэгчийн хүссэн үндсэн endpoint:

```http
GET https://graph.facebook.com/v26.0/{PAGE_ID}/feed
```

Meta Pages documentation `/{page-id}/feed` edge-ийг Page ажиллагаанд ашигладаг. citeturn18search6

OrderHub-д:

```http
GET /v26.0/{PAGE_ID}/feed
    ?fields=id,message,created_time,permalink_url,
            attachments{media,type,url},
            comments.limit(10){id,message,created_time,from},
            reactions.limit(0).summary(true)
    &limit=25
```

гэсэн shape тохиромжтой.

`/feed` болон `/posts`-ыг ижил гэж үзэж болохгүй. MVP requirement нь `feed` тул эхний implementation үүнийг ашиглана; дараа нь зөвхөн Page өөрөө нийтэлсэн post хэрэгтэй бол `/posts` edge-ийг тусдаа үнэлнэ.

Internal API:

```http
GET /api/posts/?platform=FACEBOOK_PAGE
```

Frontend Facebook рүү шууд хандахгүй.

### Facebook Messenger conversations

OrderHub:

```text
Meta
 GET /PAGE_ID/conversations
        ↓
Conversation upsert

Meta
 GET /CONVERSATION_ID/messages
        ↓
Message upsert
```

Messenger conversations нь Page болон хэрэглэгчийн харилцан яриаг Page түвшинд авах боломж олгодог; Instagram professional messaging-ийн conversation API ч мөн Meta дээр тусдаа дэмжигддэг. citeturn18search7

Frontend:

```http
GET /api/conversations/
```

Django шаардлагатай үед:

```http
GET https://graph.facebook.com/v26.0/{PAGE_ID}/conversations
```

Frontend conversation нээвэл:

```http
GET /api/conversations/{uuid}/messages/
```

харин sync task:

```http
GET https://graph.facebook.com/v26.0/{META_CONVERSATION_ID}/messages
```

дуудна.

### Messenger message илгээх

Архитектурын хамгийн чухал security rule:

```text
❌ Browser:
POST {
   page_id: "123",
   psid: "456",
   access_token: "..."
}

✅ Browser:
POST {
   conversation_id: "local-uuid",
   text: "Байгаа шүү.",
   idempotency_key: "uuid"
}
```

Django дотроо:

```text
conversation
   ↓
company
   ↓
social_account
   ↓
page_id
   ↓
customer PSID
   ↓
decrypt page token
   ↓
POST /PAGE_ID/messages
```

хийдэг байх ёстой.

Ингэснээр хэрэглэгч browser DevTools-оос өөр tenant-ийн `page_id`, `PSID`, token оруулж abuse хийх боломж эрс багасна.

### Instagram comments

Meta-ийн current Instagram Login API нь `graph.instagram.com` host ашигладаг бөгөөд IG Comment object/reply edge одоогийн reference-д бий. citeturn20search6turn18search2

Унших:

```http
GET https://graph.instagram.com/v26.0/{IG_MEDIA_ID}/comments
    ?fields=id,text,username,timestamp
```

Reply:

```http
POST https://graph.instagram.com/v26.0/{IG_COMMENT_ID}/replies

message=Байгаа шүү.
```

`/{comment-id}/replies` нь тухайн IG Comment дээр reply comment үүсгэх edge гэдгийг Meta тодорхойлдог. citeturn18search2

OrderHub-ийн frontend-д Facebook/Instagram ялгах шаардлагагүй:

```http
POST /api/comments/{LOCAL_UUID}/reply/

{
  "message": "Байгаа шүү."
}
```

Backend:

```python
if comment.platform == Platform.FACEBOOK_PAGE:
    facebook.reply_to_comment(...)
elif comment.platform == Platform.INSTAGRAM:
    instagram.reply_to_comment(...)
```

### Webhook flow

Polling-оор DM шалгах биш, webhook-ийг үндсэн event source болгоно:

```text
Customer sends Messenger message
              │
              ▼
            Meta
              │
              │ HTTPS webhook
              ▼
POST /api/meta/webhook/
              │
        verify signature
              │
        store raw event
              │
         return 200
              │
              ▼
            Celery
              │
      resolve SocialAccount
              │
       upsert Customer
              │
      upsert Conversation
              │
        upsert Message
              │
              ▼
           Postgres
              │
              ▼
          Next.js poll
```

Meta webhook documentation нь payload authenticity-г `X-Hub-Signature-256`-тай харьцуулж шалгахыг заадаг. citeturn19search5turn19search13

Шалгахдаа **parsed JSON биш raw HTTP bytes** дээр HMAC хийх ёстой:

```python
raw_body = request.body

digest = hmac.new(
    META_APP_SECRET.encode(),
    raw_body,
    hashlib.sha256,
).hexdigest()

expected = f"sha256={digest}"

valid = hmac.compare_digest(
    expected,
    request.headers["X-Hub-Signature-256"],
)
```

Webhook request дээр бүх sync хийх нь буруу:

```text
Webhook
  ↓
call Meta
  ↓
call more Meta
  ↓
create customer
  ↓
download media
  ↓
200
```

Харин:

```text
Webhook
  ↓
verify
  ↓
persist
  ↓
Celery.delay()
  ↓
200

          Celery worker
              ↓
          actual work
```

гэнэ.

### Webhook-ийн event idempotency

Meta нэг delivery-г дахин илгээх, эсвэл таны worker нэг task-ийг retry хийх боломжтой тул:

```text
RawWebhookEvent
dedupe_key UNIQUE
```

байх ёстой.

Жишээ:

```python
dedupe_key = sha256(
    canonical_event_identity.encode()
).hexdigest()
```

Messenger message дээр илүү хүчтэй key:

```text
social_account_id + message.mid
```

Comment дээр:

```text
social_account_id + external_comment_id + event_action
```

Хэрэв баталгаатай provider event ID байхгүй бол raw event-ийн stable subset-ээр fallback hash гаргаж болно.

### DB relationships

Гол холбоос:

```text
Company
   │
   ├───────────────┐
   │               │
   ▼               ▼
SocialAccount    Product
   │               │
   │               │
   ├─ Post          │
   │    │           │
   │    └─ Comment  │
   │                │
   └─ Conversation  │
          │         │
          ├─ Message│
          │         │
          ▼         │
       Customer     │
          │         │
          └────┬────┘
               ▼
             Order
               │
               ▼
           OrderItem
```

`Company`-г бүх business object дээр шууд FK болгож давхар хадгалах нь бага зэрэг denormalization боловч multi-tenant query/security дээр ашигтай:

```python
Message.objects.filter(
    company=request.company,
    conversation_id=conversation_id,
)
```

гэсэн defense-in-depth query хийх боломжтой.

## Backend, frontend, security ба deployment-ийн шийдэл

### Django provider abstraction

Meta HTTP call-уудаа view дотор бичиж болохгүй:

```python
# BAD
class SendMessageView(APIView):
    def post(...):
        requests.post("https://graph.facebook.com/...")
```

Харин:

```python
class FacebookGraphClient:
    def __init__(
        self,
        *,
        access_token: str,
        version: str,
    ):
        self.access_token = access_token
        self.version = version
        self.base_url = "https://graph.facebook.com"

    def send_message(
        self,
        *,
        page_id: str,
        recipient_id: str,
        text: str,
    ) -> dict:
        url = f"{self.base_url}/{self.version}/{page_id}/messages"

        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            json={
                "recipient": {"id": recipient_id},
                "messaging_type": "RESPONSE",
                "message": {"text": text},
            },
            timeout=15,
        )

        return self._handle_response(response)
```

болговол дараа нь testing маш амар болно.

### Message send-ийг asynchronous болгох

UX:

```text
User clicks Send
      │
      ▼
POST /api/messages/send
      │
      ├─ validate tenant
      ├─ create Message(status=PENDING)
      ├─ enqueue Celery
      │
      ▼
HTTP 201 immediately
      │
      ▼
Frontend
"Sending..."
```

Worker:

```text
PENDING
   ↓
SENDING
   ↓
Meta API
  ├──────── success ─────→ SENT
  │                       external_id = mid...
  │
  └──────── fail ────────→ FAILED
```

Энэ нь Meta temporarily удаашрах үед Next.js request timeout болохоос хамгаална.

### Realtime-ийн хувьд MVP дээр WebSocket хэрэггүй

Энд хоёр тусдаа realtime асуудал бий.

Meta → backend:

```text
Webhook
```

Backend → browser:

```text
3–5 second polling
```

MVP-д хангалттай.

Жишээ:

```typescript
useQuery({
  queryKey: ["messages", conversationId],
  queryFn: () => getMessages(conversationId),
  refetchInterval: 3000,
});
```

Дараа нь хэрэглэгч олширвол:

```text
Meta Webhook
    ↓
Django
    ↓
Redis / WebSocket
    ↓
Next.js
```

болгож болно. Эхний release дээр Channels/WebSocket нэмэх нь MVP-ийн хамгийн эрсдэлтэй хэсэг болох Meta App Review, token lifecycle, webhook integration-оос анхаарал сарниулна.

### Rate limiting

Meta-ийн quota-г өөрсдөө нэг “100 request/minute” мэт hard-code хийх хэрэггүй. Provider-ийн upstream rate/error responses-ийг хүндэтгэж, retry/backoff хий.

OrderHub API дээр өөрийн хамгаалалт хэрэгтэй:

```text
/messages/send
    per user
    per company

/comments/:id/reply
    per user
    per company

/auth/login
    per IP/account
```

Celery:

```python
countdown = min(
    2 ** self.request.retries + random.randint(0, 3),
    300,
)
```

гэсэн exponential backoff + jitter ашиглаж болно.

### Docker Compose

Backend repo:

```yaml
services:
  postgres:
    image: postgres:17
    environment:
      POSTGRES_DB: orderhub
      POSTGRES_USER: orderhub
      POSTGRES_PASSWORD: orderhub
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  backend:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    env_file:
      - .env
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

  celery:
    build: .
    command: celery -A config worker -l info
    env_file:
      - .env
    depends_on:
      - postgres
      - redis

  celery-beat:
    build: .
    command: celery -A config beat -l info
    env_file:
      - .env
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
```

Production-д `runserver` биш WSGI/ASGI production server ашиглана.

### Environment variables

Backend:

```dotenv
DJANGO_SECRET_KEY=
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=

DATABASE_URL=
REDIS_URL=

FRONTEND_URL=
BACKEND_PUBLIC_URL=

META_GRAPH_VERSION=v26.0
META_APP_ID=
META_APP_SECRET=
META_WEBHOOK_VERIFY_TOKEN=

META_FACEBOOK_REDIRECT_URI=
META_INSTAGRAM_REDIRECT_URI=

TOKEN_ENCRYPTION_KEY=

CELERY_BROKER_URL=
CELERY_RESULT_BACKEND=
```

Frontend:

```dotenv
NEXT_PUBLIC_API_BASE_URL=
```

**Эдгээрийг frontend env-д хэзээ ч хийж болохгүй:**

```dotenv
NEXT_PUBLIC_META_APP_SECRET=        # NO
NEXT_PUBLIC_PAGE_ACCESS_TOKEN=     # NO
NEXT_PUBLIC_IG_ACCESS_TOKEN=       # NO
NEXT_PUBLIC_TOKEN_ENCRYPTION_KEY=  # NO
```

`NEXT_PUBLIC_*` нь browser bundle-д харагдана.

### ngrok development flow

Meta webhook болон OAuth callback нь гаднаас reachable URL шаардах учраас local development-д:

```bash
docker compose up --build
```

дараа нь:

```bash
ngrok http 8000
```

Жишээ public backend:

```text
https://orderhub-dev.ngrok.app
```

Meta Dashboard:

```text
Webhook callback:
https://orderhub-dev.ngrok.app/api/meta/webhook/

Facebook callback:
https://orderhub-dev.ngrok.app/api/meta/facebook/callback/

Instagram callback:
https://orderhub-dev.ngrok.app/api/meta/instagram/callback/
```

Free ngrok URL солигддог бол OAuth redirect болон webhook URL-аа Meta Dashboard дээр дахин тохируулах ажил гарна. Тиймээс Meta integration дээр тогтмол ажиллаж эхэлсний дараа reserved dev hostname ашиглах нь ажиллагааны хувьд амар.

## MVP-ийн бодит хэрэгжүүлэлтийн дараалал ба acceptance test

Би Codex-д **Instagram + Facebook + Orders бүгдийг зэрэг бичүүлж эхлүүлэхгүй**. Эхлээд Facebook-ийн нэг complete vertical slice ажилладаг болгох нь зөв.

### Эхний vertical slice

```text
Facebook Login
     ↓
Connect Page
     ↓
Store encrypted Page token
     ↓
GET /feed
     ↓
Show /posts
     ↓
Open post
     ↓
Show comments
     ↓
Reply to comment
```

Энэ ажилласны дараа:

```text
Customer sends Messenger DM
     ↓
Webhook
     ↓
Conversation
     ↓
Message
     ↓
/inbox
     ↓
Reply
     ↓
Customer receives reply
```

Эдгээр хоёр flow Meta App Review-ийн хамгийн чухал demo болно.

Дараа нь:

```text
Instagram Login
     ↓
Comments
     ↓
DM
```

хамгийн сүүлд:

```text
Conversation
     ↓
Customer
     ↓
Product
     ↓
Create Order
```

### Codex-ийн build дууссан гэж үзэх integration test

**Facebook Post test**

```text
Facebook Page дээр:
"Шинэ Hoodie 89,000₮"

        ↓ sync/webhook

OrderHub /posts:
Шинэ Hoodie 89,000₮
👍 14
💬 3
```

**Comment test**

Customer:

```text
"M размер байна уу?"
```

OrderHub:

```text
Бат
M размер байна уу?

[ M байгаа шүү. ] [Reply]
```

Reply дарахад Facebook дээр:

```text
Demo Shop:
M байгаа шүү.
```

үүсэх ёстой.

**Messenger test**

Customer Messenger:

```text
Сайн байна уу?
```

OrderHub:

```text
Inbox
  Бат
  Сайн байна уу?
```

OrderHub-аас:

```text
Сайн байна уу. Юугаар туслах вэ?
```

явуулахад customer Messenger дээр авах ёстой. Messenger platform-ийн messaging боломжийг ашиглахдаа Meta-ийн одоогийн platform policy болон message eligibility/window хязгаарлалтыг API error-level дээр хүндэтгэх хэрэгтэй; түүнийг тойрох логик хийж болохгүй. Meta-ийн messaging API нь Instagram professional messaging дээр ч current `instagram_business_manage_messages` scope ашиглаж байна. citeturn18search10turn20search4

**Order test**

Conversation-ийн баруун талд:

```text
Customer
Бат

Product
[ Hoodie / M ]

Qty
[ 1 ]

Price
89,000₮

[ Create Draft Order ]
```

дарвал:

```text
Order #OH-000123
Customer: Бат
Source: Facebook Messenger
Status: DRAFT
1 × Hoodie M
Total: 89,000₮
```

үүснэ.

### Release хийхээс өмнөх хамгийн чухал тестүүд

Энд functional test-ээс илүү **tenant security test** хамгийн чухал.

Жишээ нь:

```python
def test_company_a_cannot_read_company_b_conversation(...):
    response = client.get(
        f"/api/conversations/{company_b_conversation.id}/",
        HTTP_X_COMPANY_ID=str(company_a.id),
    )

    assert response.status_code in (403, 404)
```

Мөн:

```python
def test_company_a_cannot_send_via_company_b_page(...):
    ...
```

заавал байх хэрэгтэй. Учир нь нэг компанийн Facebook access token нөгөө компанид алдагдах нь жирийн UI bug биш, ноцтой tenant-isolation breach болно.

### MVP-ийн “done” шалгуур

Эхний production candidate-г дараах бүх зүйл ажиллаж байж done гэж үзнэ:

| Шалгуур | Шаардлага |
|---|---|
| Meta App | Development setup бүрэн |
| Facebook OAuth | ✅ |
| Page selection | ✅ |
| Encrypted Page token | ✅ |
| Page feed | ✅ |
| Comments | ✅ |
| Comment reply | ✅ |
| Reaction count | ✅ |
| Messenger conversations | ✅ |
| Message history | ✅ |
| Messenger reply | ✅ |
| Webhook signature | ✅ |
| Webhook deduplication | ✅ |
| Company isolation | ✅ |
| Instagram Login | ✅ эсвэл Facebook MVP дараах milestone |
| IG comments | ✅ |
| IG comment reply | ✅ |
| IG token refresh | ✅ |
| Products | ✅ |
| Orders | ✅ |
| Docker | ✅ |
| pytest | ✅ |
| frontend tests | ✅ |
| `.env.example` | ✅ |
| Meta setup README | ✅ |
| App Review README | ✅ |

## Судалгааны дүгнэлт ба албан ёсны эх сурвалжууд

Энэ төслийн **хамгийн хэцүү хэсэг Django эсвэл Next.js биш**. Техникийн хувьд post list, comment UI, inbox, order creation нь энгийн. Бодит integration risk нь:

```text
Meta OAuth
+
permission scope
+
App Review
+
Page/IG token lifecycle
+
webhook correctness
+
multi-tenant token isolation
```

эдгээр дээр төвлөрнө.

Тиймээс OrderHub-ийн MVP-г **Facebook-first vertical slice**-аар эхлүүлэх нь хамгийн бага эрсдэлтэй:

```text
Connect Page
     ↓
Posts
     ↓
Comments
     ↓
Reply
     ↓
Messenger Inbox
     ↓
Reply
     ↓
Create Order
```

Үүнийг бүрэн ажиллуулсны дараа Instagram provider нэмэхэд core data model болон UI-г дахин бичих шаардлагагүй болно.

Meta-ийн current Pages API нь Page management, comment moderation, real-time update зэрэг use case-ийг дэмжиж байгаа бөгөөд Facebook Page token-ууд Page data дээр read/write хийхэд зориулагдсан. citeturn15search25turn18search3 Instagram-ийн одоогийн API with Instagram Login нь business basic, comment management, messaging scopes болон `graph.instagram.com` host ашигладаг. citeturn18search0turn20search7 Webhook payload authenticity-г `X-Hub-Signature-256` ашиглан шалгах нь Meta-ийн албан ёсны webhook guidance-тэй нийцнэ. citeturn19search5turn19search13

2026 оны аравдугаар сарын 13-ны байдлаар implementation-аа `v26.0` дээр pin хийх нь Meta-ийн одоогийн Graph API documentation-тэй нийцэж байна; гэхдээ version-ийг environment variable болгосноор дараагийн Meta migration-д кодын бүх URL-ийг засах шаардлагагүй болно. citeturn15search11

Codex implementation хийхдээ эх сурвалжийн тэргүүлэх дараалал:

1. **Meta official Pages API / Permissions / Access Tokens** — Facebook Page authorization, post/comment access, token lifecycle. citeturn18search21turn15search13turn18search12
2. **Meta official Messenger/Webhooks** — inbox, outbound messages, webhook verification. citeturn19search13turn19search5
3. **Meta official Instagram API with Instagram Login** — шинэ scope naming, comments, messaging, host. citeturn18search0turn18search10turn20search7
4. **Meta official Instagram Comment APIs** — media comments болон reply edge. citeturn20search6turn18search2
5. **Meta official Instagram token refresh** — long-lived token renewal. citeturn19search2

Энд зориуд нэг зүйл хийсэн: Facebook-ийн Page token болон Instagram Login token-ийг нэг “MetaToken” гэсэн ойлголтоор хольж өгөөгүй. **Facebook Page = long-lived Page access token + reconnect/health-check**, харин **Instagram Login = expiring long-lived token + explicit refresh** гэсэн хоёр өөр lifecycle-ийг тусгаарлах нь OrderHub-ийн production архитектурын хамгийн чухал шийдвэрүүдийн нэг юм. citeturn18search12turn19search2