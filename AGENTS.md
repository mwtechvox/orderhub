# OrderHub — Codex Repository Instructions

## Project

OrderHub is a multi-tenant social-commerce operations platform for Mongolian businesses.

The initial product focuses on Facebook Page commerce workflows:

- Facebook Page connection
- Page posts
- comments and replies
- reaction counts
- Messenger conversations
- Messenger replies
- customer records

Future phases may include:

- Instagram
- Products
- Orders
- QPay
- eBarimt
- delivery integrations
- AI-assisted replies

Do not implement future features unless the current task explicitly requests them.

---

## Source of Truth

The main product and architecture specification is:

```text
deep-research-report.md
```

Before making architectural decisions or implementing a new major feature, read the relevant sections of this file.

Do NOT modify `deep-research-report.md` unless the user explicitly requests it.

If implementation details conflict with the research report:

1. identify the conflict;
2. prefer current official provider/framework documentation when external behavior has changed;
3. implement the safest current behavior;
4. document the deviation.

For Meta API behavior, official Meta documentation takes precedence over assumptions in the research report.

---

## Architecture

Use a modular monolith.

Expected repository structure:

```text
OrderHub/
├── AGENTS.md
├── deep-research-report.md
├── PLANS.md
├── backend/
└── frontend/
```

Backend:

```text
Django
Django REST Framework
PostgreSQL
Redis
Celery
pytest
```

Frontend:

```text
Next.js
React
TypeScript
Tailwind CSS
TanStack Query
```

Do NOT introduce microservices, Kafka, Kubernetes, GraphQL, or unnecessary infrastructure unless explicitly requested.

Prefer the simplest production-sensible architecture.

---

## Current Development Strategy

Do not try to implement the entire research report in one uncontrolled change.

Work in small vertical phases.

Preferred implementation order:

```text
Phase 1
Foundation
Django + PostgreSQL + Redis + Celery
Authentication
Company
CompanyMembership
Tenant isolation

Phase 2
Facebook connection
SocialAccount
Token encryption
OAuth
Page discovery
Meta API client

Phase 3
Facebook Page content
Posts
Comments
Reactions
Comment replies

Phase 4
Messenger
Customer
Conversation
Message
Inbound sync
Outbound replies

Phase 5
Webhooks
Signature verification
RawWebhookEvent
Deduplication
Celery processing

Phase 6
Frontend integration
Inbox
Posts
Post detail
Integrations settings

Phase 7+
Only when explicitly requested:
Instagram
Products
Orders
payments
delivery
AI
```

Finish and validate the current phase before expanding scope.

---

## Multi-Tenancy

Multi-tenant isolation is mandatory.

All business-domain records must belong to a Company either directly or through a clearly enforced ownership chain.

Never fetch tenant-owned objects using only their object ID.

Bad:

```python
Conversation.objects.get(id=conversation_id)
```

Good:

```python
Conversation.objects.get(
    id=conversation_id,
    company=request.active_company,
)
```

Every API queryset and mutation must enforce active-company membership.

Never trust a company ID supplied by the browser without verifying `CompanyMembership`.

Cross-tenant access tests are mandatory.

Company A must never be able to read, modify, send through, or otherwise access Company B resources.

---

## Meta Security

Meta credentials and access tokens are backend-only secrets.

Never expose any of the following to the frontend:

```text
META_APP_SECRET
Facebook Page Access Token
Facebook User Access Token
Instagram Access Token
TOKEN_ENCRYPTION_KEY
```

Never place secrets in `NEXT_PUBLIC_*`.

Meta access tokens must be encrypted at rest.

Never print or log access tokens.

Never include tokens in:

- serializers
- API responses
- admin list views
- exceptions returned to clients
- URLs written to logs

Prefer `Authorization: Bearer` when supported.

---

## Meta API Architecture

Do not call Meta HTTP APIs directly from Django views.

Provider access must go through service/client classes.

Expected structure:

```text
backend/apps/meta/services/
    facebook.py
    oauth.py
    tokens.py
    encryption.py
    webhooks.py
```

Views should coordinate application behavior.

Provider clients should handle Meta HTTP contracts.

Keep Graph API version configurable using:

```text
META_GRAPH_VERSION
```

Never scatter a hard-coded Graph API version across the codebase.

When a Meta endpoint, permission, field, webhook payload, or token rule is uncertain, verify it against current official Meta documentation when network access is available.

Do not guess provider contracts.

---

## Facebook-First Scope

The first production-quality vertical slice is:

```text
User login
    ↓
Connect Facebook
    ↓
Select managed Page
    ↓
Store encrypted Page token
    ↓
Sync Page posts
    ↓
View posts
    ↓
View comments / reaction count
    ↓
Reply to comment
    ↓
Receive Messenger conversation
    ↓
View message history
    ↓
Reply from OrderHub
```

Prioritize making this entire flow correct before adding Instagram or order-management features.

---

## Webhooks

Meta webhooks must:

```text
receive request
    ↓
verify signature
    ↓
preserve raw payload
    ↓
deduplicate
    ↓
persist event
    ↓
enqueue Celery task
    ↓
return HTTP 200 quickly
```

Validate `X-Hub-Signature-256` using the raw request bytes.

Do not perform long Meta synchronization inside the webhook HTTP request.

Webhook processing must be idempotent.

Unknown webhook event types must not crash the application.

---

## Background Tasks

Use Celery for slow/retryable provider operations such as:

```text
send Meta message
sync conversations
sync messages
sync posts
sync comments
process webhook
token health checks
```

Retries must be bounded.

Retry:

```text
network errors
timeouts
HTTP 429
appropriate temporary 5xx errors
```

Do not endlessly retry:

```text
permission errors
invalid credentials
permanent 4xx errors
```

Persist safe provider errors where useful.

---

## Messaging

Outbound messages should follow:

```text
API request
    ↓
validate tenant
    ↓
create local Message(PENDING)
    ↓
enqueue Celery task
    ↓
SENDING
    ↓
Meta API
    ↓
SENT or FAILED
```

Outbound messaging must support idempotency.

A message already marked `SENT` must not be sent again.

Never trust browser-provided Page IDs, PSIDs, or provider tokens when they can be resolved from a local Conversation.

---

## Database

Prefer UUID primary keys for business-domain models.

Use database constraints for provider identifiers and idempotency where appropriate.

Examples:

```text
unique social account external ID
unique provider message ID
unique webhook dedupe key
unique client idempotency key
```

Use transactions where several records must succeed or fail together.

Do not rely only on application code when PostgreSQL constraints can protect data integrity.

---

## Backend Code Quality

Keep Django apps domain-focused.

Prefer:

```text
models
serializers
views
services
tasks
permissions
tests
```

Avoid giant views, serializers, or utility modules.

Business/provider logic should not live inside DRF serializers unless it is genuinely serialization-specific.

Use type hints for service-layer code where practical.

Use structured exceptions for provider failures.

Do not silently swallow exceptions.

---

## Frontend

The frontend talks only to the OrderHub backend.

Never call Meta directly from browser code.

Use a shared typed API client.

Keep server state in TanStack Query where appropriate.

For the MVP, polling every few seconds is acceptable for inbox updates.

Do not add WebSockets unless explicitly requested or clearly justified.

Prioritize:

```text
correctness
clarity
responsive UI
error states
loading states
safe retries
```

over decorative UI.

---

## Testing

Tests are part of implementation, not optional cleanup.

Backend tests should cover relevant changes.

Security-sensitive areas require tests.

Mandatory categories include:

```text
authentication
tenant isolation
token encryption
provider clients
webhook verification
webhook deduplication
message idempotency
API permissions
```

Meta HTTP calls must be mocked in automated tests.

Do not require real Meta credentials for the automated test suite.

For every significant backend change, run the relevant pytest suite.

For frontend changes, run:

```text
lint
typecheck
tests
build
```

when those scripts exist.

Fix failures caused by the change before declaring the task complete.

---

## Environment

Do not commit real credentials.

Maintain `.env.example` files.

Backend environment configuration should include variables such as:

```text
DATABASE_URL
REDIS_URL
DJANGO_SECRET_KEY

META_GRAPH_VERSION
META_APP_ID
META_APP_SECRET
META_WEBHOOK_VERIFY_TOKEN
META_FACEBOOK_REDIRECT_URI

TOKEN_ENCRYPTION_KEY

CELERY_BROKER_URL
CELERY_RESULT_BACKEND
```

Frontend public configuration should contain only values safe to expose to the browser.

---

## Dependency Policy

Before adding a dependency:

1. check whether the existing stack already solves the problem;
2. prefer mature and maintained packages;
3. avoid dependencies for trivial functionality;
4. keep backend/frontend dependency files updated;
5. explain significant new infrastructure dependencies.

Do not replace core technologies without explicit instruction.

---

## Working With Existing Code

Before modifying an existing feature:

1. inspect the relevant models;
2. inspect service/provider code;
3. inspect existing tests;
4. understand the current API contract;
5. make the smallest coherent change.

Do not rewrite unrelated working code.

Do not delete existing behavior merely because another implementation seems cleaner.

Preserve backwards compatibility unless the current task explicitly changes the contract.

---

## Task Execution

For each user task:

1. read this `AGENTS.md`;
2. inspect relevant repository files;
3. consult `deep-research-report.md` when the task affects product architecture or Meta integration;
4. check `PLANS.md` when present;
5. identify the smallest complete scope;
6. implement it;
7. add/update tests;
8. run relevant validation;
9. report what changed and what remains.

Do not stop after writing a plan when the user asked for implementation.

Do not claim success if tests/build were not actually run.

If a command cannot be run, state that clearly.

---

## Documentation

Keep implementation documentation close to the code.

Expected documentation may include:

```text
backend/docs/
    META_SETUP.md
    SECURITY.md
    LOCAL_DEVELOPMENT.md
```

Manual actions that Codex cannot perform, especially Meta Developer Dashboard configuration, must be clearly documented separately from code changes.

---

## Scope Control

Do not opportunistically add unrelated features.

Especially do not implement these unless explicitly requested:

```text
Instagram
QPay
eBarimt
delivery providers
AI auto replies
advanced inventory
accounting
mobile app
Kafka
Kubernetes
microservices
```

A clean, tested Facebook-first MVP is more valuable than a partially implemented large system.

---

## Completion Report

At the end of a significant task report:

```text
Implemented
Files changed
Tests run
Test results
Known limitations
Manual steps required
Recommended next task
```

Keep the report concise and factual.