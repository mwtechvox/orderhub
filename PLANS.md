# OrderHub — Living Implementation Plan

Last audited: **2026-10-13, Asia/Ulaanbaatar**.
Last implementation update: **2026-10-14 — new React/Vite workspace UI connected to the backend**, Asia/Ulaanbaatar.

## Purpose and scope

This plan records the actual repository state. It does not override the user's instructions, `AGENTS.md`, or `deep-research-report.md`. Update evidence, remaining work, blockers, and the single recommended next task after subsequent implementation work. Explain significant changes under **Plan Changes**, preserving previous decision history.

The original Facebook-first prompt narrows the research report to:

```text
Login → Facebook OAuth → select managed Page → encrypted Page token
→ local posts → comments/reaction counts → comment reply
→ Messenger conversations/history → reply from OrderHub
```

Instagram, products/orders, payments, delivery, accounting, AI and mobile remain outside the authorized MVP. The 2026-10-13 audit changed only this plan. Separate 2026-10-14 implementations address F1–F7, static Page automation, and the explicitly requested Facebook post publishing/per-post automation extension; the research report and Facebook-first provider scope remain unchanged.

Status definitions:

- **DONE**: the specifically named local capability exists and is supported by code and verification recorded here. This does not imply live Meta acceptance or exhaustive security assurance.
- **PARTIAL**: implementation exists, but identified behavior, coverage or acceptance work remains.
- **NOT_STARTED**: no implementation of the named capability exists. Intentional deferrals are identified.
- **BLOCKED**: the named work needs an unavailable external prerequisite. Independent work can continue.

## Current state

**Overall Facebook-first MVP: PARTIAL. Current stage: new workspace UI is backend-connected; provider acceptance remains required.**

The previous `DISCOVERY / INITIAL IMPLEMENTATION` placeholder was stale. Code exists across all six original phases. Rebuilding foundation or starting another product domain would ignore that implementation. Passing mocked tests does not establish that the complete journey works against Facebook.

Audit scope: root instructions, entire research report and original attached prompt; backend models/migrations, services, tasks, permissions, serializers/routes, commands/admin; frontend routes/components/client/styles; tests; dependency manifests/locks; environment examples; Docker/build configuration; repository documentation. Generated dependencies, caches and build output are excluded from source inventory. Local Meta credential presence was checked without exposing values. No `.git` directory exists at this root, so Git history and previously committed secrets were not assessed.

### Original phase mapping

| Original phase | Status | Actual position |
|---|---|---|
| 1 — Foundation/auth/company/tenancy | PARTIAL | Stack, migrations, login, company context and tenant tests exist; F6 aligns manual integration/content sync to OWNER/ADMIN and preserves AGENT daily work. |
| 2 — Facebook connection/provider | PARTIAL | Real OAuth, encrypted Page selection/storage, Graph client and mocked tests exist; F4 top-level protocol validation and F5 nested normalization are verified; live acceptance remains. |
| 3 — Posts/comments/reactions/replies | PARTIAL | Local sync plus OrderHub draft/schedule/publish UI and APIs exist; Page/default and per-post static public-reply/private-DM automation, F3 and F7 are verified locally. Live post/private-reply acceptance and deletion reconciliation remain. |
| 4 — Messenger | PARTIAL | Normalized inbox, async outbound, idempotency and concurrency tests exist; F1 timestamp eligibility is fixed and verified; recovery coverage remains. |
| 5 — Webhooks | PARTIAL | Signature verification, persistence, worker processing and deduplication exist; F3 comment writers share a database lock and F5 safely ignores malformed optional nested values; reconciliation gaps remain. |
| 6 — Integrations/frontend/docs/final cleanup | PARTIAL | Required screens and docs exist; mocked browser workflow passes, but live acceptance and other recorded gaps remain. |

### Capability inventory

Paths are relative to this repository. Tests are detailed in the next section.

| Area | Status | Actually implemented and evidence | Remaining work / limits |
|---|---|---|---|
| Backend foundation and local infrastructure | DONE | Django/DRF modular monolith; PostgreSQL, Redis, Celery/beat, Gunicorn; Dockerfiles and Compose migration service. `backend/config/`, `backend/docker-compose.yml`; runtime and clean migration checks pass. | DONE covers local foundation; production deployment is separate. |
| Database model baseline | DONE | All required MVP models plus CommentReplyAttempt, CommentAutomationRule, CommentPrivateReplyAttempt and SocialPostCommentAutomation. Eleven domain migrations; UUID business IDs, provider uniqueness, one-rule-per-account and one automatic public/private action per comment constraints. PostgreSQL tests/migration consistency pass. | Denormalized company/FK consistency relies on application paths and tenant-scoped creation, not cross-table database constraints. Wider report fields are simplified below. |
| Login/session/CSRF | DONE | `backend/apps/accounts/views.py`: CSRF, login, rotated CSRF response, logout, me; HttpOnly DB session. `create_owner` bootstraps owner; authenticated company creation exists. Auth/API-client tests pass. | No public registration, refresh-token API, password reset or membership UI. Real browser auth was not rerun in this audit. |
| Tenant isolation and role policy | PARTIAL | `companies/permissions.py` centralizes OWNER/ADMIN integration management; both account and post manual sync now enforce it. AGENT may view posts/inbox and send comment/Messenger replies. Same-tenant denials are 403; cross-tenant account management/data access tests pass. | Company switching still lacks a dedicated browser test; no membership-management UI exists. |
| Token encryption and API exclusion | DONE | `meta/services/encryption.py`, explicit serializers, encrypted temporary Page choices, backend-only exchange, safe errors/logging. Roundtrip, API exclusion and invalid-ciphertext tests pass. | Scoped completion, not an exhaustive secret audit. No automated rotation tool or comprehensive admin/logging deployment tests. |
| OAuth, Page discovery and selection | PARTIAL | `meta/services/oauth.py`, `meta/views.py`: hashed, session/user/company-bound one-use 10-minute state; short→long token exchange; permission/Page discovery; encrypted candidates; server-side selection and subscription. Mocked OAuth tests pass. | Live app/Page acceptance absent. F2 tests missing scopes, expired/foreign selection and subscription rejection during reconnect; F4 validates token-exchange and Page-list response shapes. Denied OAuth scopes and other-session state need broader tests. Page tasks are fetched but not explicitly validated. |
| Graph API client | PARTIAL | `meta/services/facebook.py`: configurable v26.0, bearer auth where used, safe cursor traversal, timeouts, three-attempt transient reads, structured errors/trace IDs, Retry-After, one-attempt writes. Twenty-three existing client cases plus 30 F4 protocol cases pass; success requires decoded JSON and the expected top-level contract, with safe retry/ambiguous-write classification. | F5 keeps nested JSON normalization in domain services; live v26 contracts remain unverified. |
| Connection lifecycle | PARTIAL | List/status/sync/reconnect/disconnect, daily health and NEEDS_REAUTH for auth/permission failures. F2 verifies scheduler exclusion, safe errors, retained data and reconnect after validated selection/subscription. Disconnect clears token/selection, fails pending sends and attempts remote unsubscribe; retains shared Page subscription. Main integration tests pass. | No Page refresh-token flow is intended. Token expiry field is not populated. F2 tests in-flight account-sync result guards; shared subscription, in-flight sends/disconnect and cleanup recovery need broader tests; real revocation/reconnect unverified. |
| Page posts and media | PARTIAL | `social/services.py`, `social/views.py`, `components/posts.tsx`: full feed cursor sync/upsert; local paginated list/detail, search/account filter, media/permalink/time/counts and sync UI. F5 skips malformed optional media/count data and records only valid-ID posts. | No incremental watermark. UI renders all media as images. Full sync does not remove missing posts; post-delete webhook does delete locally. |
| OrderHub Facebook post publishing | PARTIAL | OWNER/ADMIN create text-only or one-public-HTTPS-image drafts, edit/schedule them locally, and publish through one-shot `/{page-id}/feed` or `/{page-id}/photos` writes. `DRAFT/SCHEDULED/PUBLISHED/FAILED/DELIVERY_UNKNOWN`, due dispatcher, row locking, provider ID validation, content lock after publish/ambiguity, composer/detail/edit UI and 15 focused tests exist. | Live v26 Page publishing, `pages_manage_posts` access/Page task and image fetching remain unverified. V1 has no binary upload, carousel/video, Meta-side schedule, delete, analytics or unknown-delivery reconciliation. |
| Aggregate reactions | DONE | Feed summary persists Post.reaction_count; local reactions endpoint returns `{total_count, items: []}`; UI renders count. Client/social/UI tests verify this minimum. | Freshness depends on sync; live field availability unverified. Individual actors intentionally absent, as permitted by original prompt. |
| Comments/nested replies/comment reply | PARTIAL | Separate top-level/reply cursor sync, parent FK, local pagination, server-resolved Page/token and local normalization; UI reply form. F7 persists a company/comment/key-unique attempt before its one synchronous provider write, returning SENT, FAILED or DELIVERY_UNKNOWN. | F3 DONE: shared atomic upsert preserves terminal tombstones and monotonic webhook time, including first-insert races; unversioned sync cannot replace timed webhook state. F7 unknown delivery is terminal locally and has no automatic reconciliation. Counts update later. UI indents flat chronological pages, not complete grouped threads. |
| Static Facebook comment automation | PARTIAL | OWNER/ADMIN configure a Page default and an optional provider-neutral `SocialPostCommentAutomation` override per post. Existing post rule wins; an explicit disabled rule blocks Page fallback; absent rule uses Page default. New eligible comments snapshot public/private text into durable one-shot attempts, so edits affect only future comments and processed comments never resend. | Local priority/disable/edit/idempotency behavior is verified. Exact v26 private-reply response, seven-day/one-message enforcement and Page publishing/private-reply access still require development-Page acceptance. No keyword/variable/AI/Instagram behavior. |
| Customer identity and Messenger history | PARTIAL | `inbox/models.py`, `inbox/services.py`: Page-scoped PSID customers, participant resolution, nullable thread ID merged later, paginated history, provider message dedupe, timestamps/unread counts. F5 ignores malformed participant/message identities and defaults optional text/attachments safely. | F1 DONE: only validated provider times advance eligibility; exact 24h boundary and future skew are tested. Imported history is unread; opening a conversation resets unread but later visible inbound messages do not automatically reset it. Groups are skipped. |
| Messenger outbound state/idempotency | PARTIAL | Server-resolved conversation/Page/recipient; PENDING→SENDING→SENT/FAILED; company-scoped key/payload conflict check, atomic worker claim, eligibility recheck, echo merge. Explicit rate rejection retries up to five attempts; ambiguous writes stop. PostgreSQL concurrency tests pass. | F1 DONE: API/worker independently enforce validated time. Echo-before-result merge now tested; broader crash/broker/disconnect recovery needs coverage. Client key lasts only while chat component is mounted. SENT means provider acceptance, not customer delivery receipt. |
| Webhook verification and durable ingress | DONE | `meta/webhook_views.py`, `meta/services/webhooks.py`: constant-time verification, raw-byte HMAC before parse, envelope validation, canonical per-account hash dedupe, DB persistence and enqueue after commit. Signature/malformed/duplicate tests pass. | JSON envelope stored, not original byte serialization. Unknown tenant/object is quarantined with no public API. Live callback delivery unverified. |
| Webhook normalization/reconciliation | PARTIAL | Celery handles messages/echoes, comment add/edit/remove, unknown events and placeholders. Valid new comment adds persist automation snapshots and enqueue only after transaction commit; durable action uniqueness makes duplicate envelopes/tasks harmless. F5 normalization and F3 comment ordering remain intact. | Post-level deletion/reconciliation remains. Subscribed postbacks are ignored; delivery/read receipts absent. Live comment/private-reply webhook flow remains unverified. |
| Scheduling/retry/durable recovery | PARTIAL | Existing message/webhook/account recovery remains; 15-second dispatchers recover PENDING comment actions and due local social posts. Comment actions and post publishing claim terminal DELIVERY_UNKNOWN before provider I/O; competing PostgreSQL workers produce one provider write. | Clear automatic action rejection remains FAILED without automatic provider retry; operator-facing retry/reconciliation UI is intentionally absent. Large histories may exceed 900s worker limit and webhook retries use fixed intervals. |
| Required frontend screens | PARTIAL | The new Figma-derived React/Vite UI is now the active `frontend/` and is split into `features`, `layouts`, `lib`, `components` and `types` like the `mak_portal` reference. Login/onboarding, company selection, inbox polling/send, posts/detail/reply, draft/schedule/publish, OAuth/Page selection, sync/disconnect and Page/per-post automation call the real Django API. Same-origin `/api` and `/health` proxy preserves session/CSRF/OAuth behavior. | Three focused Vite tests cover tenant/CSRF request headers and filters; the legacy Next regression/e2e sources remain under `frontendd/` and do not exercise the active UI. Add active-browser company switching, role visibility, reply and mobile workflow coverage. Live Meta acceptance remains blocked. |
| Documentation/API documentation | PARTIAL | Existing docs plus API and META_SETUP now describe rule endpoints, Celery behavior, private-reply write, one-comment/one-DM constraint, provider uncertainty and the exact manual acceptance steps. | Schema/Swagger/Redoc routes remain absent. Current developer private-replies reference was inaccessible, and live acceptance remains blocked. |
| Standalone customer API / wider report filters | NOT_STARTED | Customers exist and are embedded in conversations; no `/api/customers/` routes/customer panel. Posts and conversations now have account/platform filters plus search. | Conversation status filter or close/reopen mutation and a standalone customer panel remain report-level omissions; do not add them without a separate product request. |
| CI and production operations | NOT_STARTED | No CI workflow, production provisioning, monitored readiness or automated backup/restore validation found. Local Docker/docs exist. `/health/` is static liveness. | Operational follow-ups, not missing local foundation. Backend Docker flow lacks admin static collection/serving configuration. |
| Live Facebook acceptance | BLOCKED | The active runtime was intentionally returned to local-only on 2026-10-14: frontend `http://localhost:3000`, backend `http://localhost:8000`, local CSRF origin and no proxy trust. Local health and CSRF endpoint checks pass; backend, Celery and beat are running. Previous inspection found no new Meta envelope since 2026-10-13 (10 PROCESSED, one IGNORED), so manual sync can pull Messenger history while realtime delivery is absent. | A local-only machine cannot receive Meta's public webhook POSTs. Re-enable a persistent public HTTPS origin, update and re-verify the Dashboard Page callback, verify `messages` and `message_echoes`, then send a test inbound message before claiming realtime acceptance. Dashboard role/test Page configuration and an authenticated OWNER test session remain required. Direct developer-document pages rate-limited; live v26 contracts remain unverified. See blockers. |
| Instagram, products/orders, QPay/eBarimt, delivery, AI, accounting, mobile | NOT_STARTED | No corresponding provider/domain implementations or screens. | Intentionally deferred by original prompt/AGENTS.md. Do not start without a new explicit request. |

## Tests currently present

Backend collected cases including parametrization: **300 total**. Post publishing/per-post automation adds 15 focused API/model/provider/resolution tests plus one PostgreSQL competing-publisher test; the prior 284 cases and F1–F7 coverage remain intact. Historical results remain below.

| File under `backend/tests/` | Cases | Existing assertions |
|---|---:|---|
| `test_auth.py` | 3 | Unauthorized access, CSRF login/logout, company creation/access isolation. |
| `test_tokens_oauth.py` | 5 | Encryption/API exclusion; wrong/replayed/expired state; Page candidate restriction; invalid ciphertext redaction. |
| `test_oauth_flow.py` | 1 | Mocked token exchange, permissions/Pages, encrypted temporary storage, token-free redirect/API headers. |
| `test_meta_protocol.py` | 30 | Malformed/empty/non-object successful JSON, collection/paging shapes, direct reads and token exchange contract, second-page failure, retained local state and bounded F2 account retry, safe write ambiguity/idempotency, valid recovery and structured Meta errors. |
| `test_meta_client.py` | 23 | Four paginated read methods; auth/permission/rate/temporary errors; reaction/send/comment success; ambiguous write timeout; transient recovery; safe Retry-After logging; structured failure categories, existing auth-code/subcode fixtures, bounded read timeout. |
| `test_integrations.py` | 4 | Sync success, disconnect/pending failure, agent management denial, token revocation health check. |
| `test_comment_ordering.py` | 27 | Terminal tombstones, repeated active sync, ordered edits/ties, invalid-time preservation, delayed snapshots, first-seen deletion, nested replies, deleted reply denial and tenant-scoped identities. |
| `test_social.py` | 4 | Repeat feed/comment/reply upsert, aggregate API/reply, cross-tenant restrictions, invalid account and account/platform filter. |
| `test_comment_replies.py` | 8 | Durable successful/failed/unknown outcomes, malformed write result, key replay/conflict, fresh-key unknown-delivery block, deleted-comment block and one-attempt provider safety. |
| `test_comment_automation.py` | 30 | OWNER/ADMIN/AGENT and tenant policy; enabled/disabled/cancelled triggers; valid provider time and seven-day/Page/nested/deleted filters; manual/automation race block; broker recovery; one public/one private write; independent failures; ambiguous terminal outcomes; text snapshots; inbox continuation; private-reply provider success/error/timeout/protocol shapes. |
| `test_social_post_publishing.py` | 15 | Draft/no-Meta behavior; publish/schedule/edit/content lock; role/tenant policy; post override priority/fallback/explicit disable; future-only edits/no resend; clear/ambiguous publish outcomes; feed/photo provider request and response shapes. |
| `test_inbox_timestamps.py` | 29 | Controlled 24h/skew boundaries and API rejection; invalid times preserve prior eligibility; monotonic/deduplicated customer updates; old/invalid history; delayed worker rejection; echo-before-result merge. |
| `test_provider_time.py` | 20 | Explicit parse failure, seconds/milliseconds/offsets, booleans/non-finite/overflow/invalid dates, naive time rejection, five-second skew and non-positive epoch rejection. |
| `test_provider_normalization.py` | 16 | Null/wrong-shaped media, malformed nested post/comment counts and author data, missing/blank/wrong-type provider IDs, participant/history normalization, signed webhook optional-field processing and required-ID quarantine. |
| `test_role_policy.py` | 8 | OWNER/ADMIN management and sync matrix; AGENT 403 direct-management requests; AGENT posts/inbox/comment/Messenger work; cross-tenant management/data denial; active-company role response. |
| `test_inbox.py` | 9 | Send states/key conflicts, auth/ambiguous failures, bounded rate failure, expired window/arbitrary-field rejection, cross-tenant send, repeated history sync, disconnected eligibility and account/platform filter. |
| `test_webhooks.py` | 25 | Verification/signature gate; four malformed envelopes; envelope/message dedupe; comment CRUD/unknown event; quarantine; echoes; sequential stale deletion; unknown sender shape; invalid timestamp processing without authorization/retries; echo create/advance/reopen prevention; monotonic/deduplicated webhook time; distinct stale comment envelopes and duplicate task/delivery replay preserve deletion. |
| `test_concurrency.py` | 13 | Existing Messenger/comment/account/comment-order races plus competing comment-automation and post-publish workers proving one provider write on PostgreSQL. Skipped on SQLite. |
| `test_sync_policy.py` | 29 | Permanent stop and data preservation; due/backoff/exhaustion/manual recovery; scheduler/health population; validated reconnect/rejection; webhook hints; stale worker results; tenant claim; unusable local credentials; send permission failure. |
| `test_queue.py` | 1 | Mocked broker OperationalError is caught. Despite its name, the test creates no durable database row. |

Active React/Vite frontend: `src/tests/api-client.test.ts` (2) and `src/tests/filters.test.tsx` (1): **3 cases**. They verify CSRF-before-write, `X-Company-ID` propagation and controlled channel/account/search filters. The former Next implementation and its 16 unit/browser cases remain in `frontendd/` as legacy reference; those results are historical and do not count as validation of the active Vite UI. No frontend test uses live Meta.

Important remaining coverage gaps: durable comment-attempt reconciliation against live Page data; broader post deletion/reconciliation and batch-event lock interactions; broader OAuth-denial/partial-scope flows; company switching; broker outage→durable recovery; worker crash and broader echo races; key rotation/admin restrictions; production cookie/proxy behavior; real Meta acceptance. No coverage percentage was measured.

### Historical checks — 2026-10-13 audit

`backend/docs/VALIDATION.md` contains historical results. The following results belong to the original audit; see the F4 record below for current backend validation:

| Check | Result and scope |
|---|---|
| `.venv/bin/pytest -q --tb=short`, default isolated SQLite | **49 passed, 2 skipped**. |
| Same suite with PostgreSQL DATABASE_URL | **51 passed, 1 warning**, disposable PostgreSQL 17. Teardown could not drop test_orderhub because four connections remained. Assertions passed; teardown is not clean. Disposable container removed afterward. |
| PostgreSQL clean `manage.py migrate --noinput` | PASS; all Django/seven domain migrations applied to empty disposable DB. |
| `manage.py makemigrations --check --dry-run` | PASS, no changes; checked with PostgreSQL and isolated test settings. |
| `.venv/bin/ruff check .` / `ruff format --check .` | PASS / PASS; 91 Python files already formatted. |
| Django `check` | PASS with test settings and running backend container. |
| Running backend `migrate --check` | PASS; no unapplied migrations. |
| `docker compose config --quiet` / existing services | PASS; backend, worker, beat running; PostgreSQL/Redis healthy. Images not rebuilt in this audit. |
| Existing backend `/health/` | HTTP 200, `{"ok":true}`. Does not check dependencies. |
| `npm run typecheck`, `npm run lint`, `npm run format:check` | PASS for each. |
| `npm test -- --run` | **8 passed**, four files. |
| `npm run build` | PASS, required routes generated. Build-generated next-env.d.ts restored to exact pre-audit content. |
| `npm run test:e2e` | Initial run: **1 failed before assertions**, Chrome context creation timed out at 30s; **1 skipped**. |
| `npm run test:e2e -- --workers=1 --timeout=60000` | **1 passed, 1 skipped**. Mocked browser flow passed; live Django auth skipped without ORDERHUB_SMOKE_CREDENTIALS. Existing local server reused. No real accounts created by audit. |

The documented host PostgreSQL example on port 55439 initially failed: 13 non-DB cases passed, 38 DB setup errors (connection refused). Current Compose does not expose that port. The running backend image also lacks pytest because it installs runtime requirements only. Verification used the host dev venv and a disposable PostgreSQL container instead; application configuration/running service ports were not changed.

### Findings and current resolution

Disposable in-memory probes used synthetic data and mocked HTTP to exercise existing functions. These were additional audit evidence, **not committed regression tests** or additions to the original 51-case suite. F1–F7 now have repository regression coverage.

| ID | Finding/evidence | Consequence |
|---|---|---|
| F1 — DONE (2026-10-14) | Original defect: missing/unparsed time became now and future time passed the lower-only bound. Fixed: parser returns aware UTC or None; numeric webhook milliseconds parsed safely; shared inbox validator rejects invalid/non-positive/materially future time; display fallback never updates last_inbound_at. | Verified with 62 added cases including parser, webhook/history, API/worker, boundary, echo merge and PostgreSQL inbound concurrency. Exact 24h is expired; explicit five-second skew limit. |
| F2 — DONE (2026-10-14) | Original defect: permanent permission failure stayed ACTIVE and requeued indefinitely; feed failure starved inbox. Fixed: centralized error categories, NEEDS_REAUTH for auth/permission, explicit sync pause for other permanent errors/exhaustion, persisted five-failure bound, due-aware worker/scheduler and independent domain attempts unless auth is unusable. | Verified with 41 added cases, full SQLite/PostgreSQL suites and clean PostgreSQL migrations. Reconnect validates server selection/scopes/subscription before ACTIVE; temporary recovery also supports existing manual sync. See exact policy below. |
| F3 — DONE (2026-10-14) | Original regression reproduced in a failing test: deletion followed by sync revived the comment. Shared atomic upsert now locks the unique account/comment row, retains terminal tombstones, clears reply eligibility, and preserves monotonic webhook ordering. | 34 added cases; 188 PostgreSQL tests pass including six competing comment writer cases. No schema change. Untimed sync never outranks timed webhook state; no restoration semantics inferred. See limitations below. |
| F4 — DONE (2026-10-14) | Original defect: a successful non-JSON response became `{}` and pagination returned `[]`. Graph client now rejects malformed/empty/non-object JSON and validates the expected top-level collection, ID, token, count or write-result shape before accepting HTTP success. | 30 new protocol tests; full SQLite/PostgreSQL suites pass. Malformed reads use existing bounded temporary policy; malformed successful writes yield delivery-unknown after one attempt. A mid-page failure marks the account sync FAILED; earlier valid rows may remain as partial local observations. |
| F5 — DONE (2026-10-14) | Original defect: `media_items([{"media": None}])` raised AttributeError; social, inbox and webhook writers also assumed nested objects/lists. Fixed: small shape helpers distinguish JSON lists/dicts, safe text/count/boolean defaults, and client iterators; malformed optional values are skipped/defaulted, while absent, blank or malformed provider IDs create no rows. | Verified with 16 regression cases covering null/wrong nested values, valid data alongside bad media, feed/comment/message/conversation normalization, signed webhook one-attempt processing and no-row required-ID rejection. F1 authorization timestamps remain validated-only, F3 tombstones still win, and F4 owns top-level protocol validation. |
| F6 — DONE (2026-10-14) | Original mismatch: account sync required OWNER/ADMIN while post sync allowed any company member. Fixed: CanManageIntegration centralizes OWNER/ADMIN enforcement for Page lifecycle and both manual-sync endpoints; AGENT daily operations retain member access. | Verified with eight role-policy tests, full SQLite/PostgreSQL suites, and owner/agent browser workflows. Direct AGENT management requests return 403; cross-tenant account management remains 404. |
| F7 — DONE (2026-10-14) | Synchronous replies now create a durable CommentReplyAttempt before exactly one provider write. Clear provider rejection becomes FAILED; timeout, connection, malformed write response or local uncertainty after the write remains DELIVERY_UNKNOWN; verified ID is SENT. | Replaying the same company/comment/key returns the existing attempt without another write. Any existing unknown attempt also blocks a fresh key, so only a clear FAILED UI state can issue a new write. Unknown remains visible, disables the composer and has no retry/reconciliation claim. |

## Architectural decisions already made

These describe existing choices; the original audit introduced no architecture. F1 timestamp, F2 error, F3 comment-ordering and F4 response policies are recorded in the dated completed-work entries.

1. **Modular monolith with separate backend/frontend.** Django owns business/provider state. React/Vite calls OrderHub only. No microservices, GraphQL, Kafka or Kubernetes.
2. **Session auth and verified company context.** HttpOnly DB sessions/CSRF; membership-validated header/session company. Tenant-filtered business queries; maintenance intentionally scans across tenants. Unknown webhooks have nullable-tenant non-public quarantine.
3. **Normalized local read model.** Local posts/comments/conversations/messages, Page-scoped customer identities, provider uniqueness and no global customer merge. Some report metadata/raw fields omitted.
4. **Backend-only credentials.** Fernet encrypts Page tokens and temporary choices. User tokens exchanged in memory. Environment key; rotation documented as manual re-encryption, not automated tooling.
5. **Facebook-only client.** Configurable version defaults to report v26.0. Eight current scopes including pages_manage_posts, pages_manage_metadata and business_management. These are implemented contracts, not claims of current Meta verification. Health/reconnect instead of invented Facebook refresh tokens.
6. **Durable async work.** Database state before enqueue, pending-row recovery, atomic send claim and tenant idempotency key. No exactly-once delivery claim. Explicit rate rejection may retry; ambiguous writes stop.
7. **Full reconciliation plus webhooks.** Five-minute full cursor scans after success; feed before inbox, but a feed failure no longer skips inbox unless credentials are unusable. Required-permission failures suspend the whole connection after this run, not a per-capability subsystem. Comment replies remain synchronous but create a durable pre-write attempt; Messenger remains asynchronous. These tradeoffs need the hardening above.
8. **REST/UI.** Page-number local pagination (25), upstream cursors kept internal; same-origin Vite proxy for cookie/OAuth context; TanStack Query polls inbox every 2s and integrations every 5s. Text-only outbound; inbound attachment links. UTC storage, Asia/Ulaanbaatar display, Mongolian UI/docs.
9. **Local deployment.** PostgreSQL 17, Redis 7, Python 3.12+, Django 5.2; active frontend uses React 19, Vite 8 and pnpm. Vite runs on port 3000 and proxies private Django requests during local development. Compose is local backend infrastructure.

10. **F2 failure and recovery policy.** Exception categories are centralized on existing subclasses. Reuse NEEDS_REAUTH for auth/permission with safe last_error; retain encrypted credentials/history. ACTIVE + FAILED + next_sync_at=None means sync requires operator action (unknown permanent failure or five failed runs). One persisted sync_failures counter avoids resetting the retry budget at every beat tick. Existing manual sync resets an ACTIVE account cycle; reconnect validates selection/scopes/subscription before resetting status/counter. No new status enum, refresh token, infrastructure or frontend contract.

11. **F3 comment state.** Reuse is_deleted and last_event_at with atomic row locks and the existing account/external-ID uniqueness constraint. Deletion is terminal; add/edit/sync cannot restore an ID. Validated event times advance monotonically, equal-time non-delete events keep the existing version, and creation/receipt time never rank revisions. Unversioned snapshots cannot replace timed webhook state. No additional revision field or restore API.

12. **F4 provider response gate.** Graph HTTP success is accepted only after JSON decoding and validation of the caller’s expected top-level shape. Collection reads require data as a list, safe paging shape and object entries; direct methods require their known ID/token/message/count/ack fields. Malformed GET responses are MetaTemporaryError within the existing three-attempt read policy. Malformed successful writes are MetaDeliveryUnknown with one attempt. No token, raw body or request URL is logged. Existing structured provider errors still use F2 categories.

13. **F5 nested normalization policy.** Nested JSON fields are normalized only where their provider meaning is known. Optional malformed dictionaries, lists, text, counts and booleans become empty/safe defaults or are skipped; valid client iterators remain supported. A nonempty string provider ID is required before creating or identifying a Post, Comment, Customer, Conversation or Message. Invalid identity data is ignored without manufacturing IDs, timestamps or tenant rows. F1 trusted timestamp policy, F3 comment ordering and F4 HTTP/protocol validation remain separate concerns.

14. **F6 role policy.** OWNER and ADMIN are integration managers: they alone connect/select/reconnect/disconnect Facebook Pages and trigger manual account or post synchronization. AGENT is the existing normal operator role: it can read Page/inbox data and send comment/Messenger replies. CanManageIntegration is backend authority; the active-company role in the session response only gates matching UI controls. Same-tenant denied management requests are 403; tenant-scoped querysets make cross-tenant object management 404.

15. **F7 comment reply delivery policy.** A CommentReplyAttempt is committed as DELIVERY_UNKNOWN before its one Meta write, with a unique `(company, comment, client_idempotency_key)` constraint. A valid provider reply ID changes it to SENT; clear Meta errors become FAILED; timeout, malformed write success and unexpected post-write local failure remain DELIVERY_UNKNOWN. Replaying a key returns its original attempt and never writes again; an existing unknown attempt blocks a new key too. Only FAILED is eligible for a user-initiated fresh-key retry. No claim of reconciliation against a later feed sync is made.

## Deviations from deep-research-report.md

Also consult `backend/docs/DEVIATIONS.md` and `META_SETUP.md`. Authorized simplifications and unfinished behavior are distinct.

| Report/expectation | Actual implementation | Disposition |
|---|---|---|
| Two repositories, backend/web; wider Facebook/Instagram/orders product | One backend/frontend workspace, Facebook only | Authorized original-prompt/AGENTS scope override. |
| Register/login/refresh examples | Session login/logout/me/CSRF, owner CLI, superuser-managed users/memberships | Deliberate simpler auth; no pending JWT requirement. |
| Five minimum Facebook scopes | Current code also requires pages_manage_metadata, business_management and pages_manage_posts; all eight must be granted at selection | pages_manage_posts supports the explicitly requested Page publishing feature. Current access level/Page-task requirements remain subject to real development-Page acceptance. Tests use the actual SCOPES constant. |
| Wider account/customer/platform/raw metadata | Page ID is external_account_id; other domains inherit platform through account; simplified name/PSID customer; no repeated raw JSON | Schema reduction; required models exist, full report schema does not. |
| Conversation external ID / unresolved customer | Immediate PSID customer, nullable thread ID until sync, extra account/customer uniqueness | Existing merge strategy; single customer conversation only. |
| Reaction model/actors when available | Aggregate count and empty reaction items | Explicitly allowed minimum; no fabricated identities. |
| Cursor-preferred REST; customer API/richer filters | Page-number local API, no standalone customer endpoint, limited filters/status control | Pagination documented; other omissions recorded, not declared complete. |
| Async comment outbound action; temporary POST retry example | Synchronous comment reply with durable attempt/idempotency; async Messenger; no blind ambiguous retry | Synchronous UX is retained, but Meta delivery ambiguity is now explicit and non-retryable. |
| Incremental sync and bounded/permanent-error policy | Full scans; F2 stops auth/permission scheduling and bounds retryable failed runs | Full scans remain a tradeoff; permanent-error loop is corrected. Per-capability long-term scheduling is deliberately not introduced. |
| Raw payload preservation | Signed bytes verified; JSON envelopes stored per account; unknown quarantine | Raw JSON preserved, not original byte serialization; no duplicate raw fields on normalized models. |
| Idempotent/correct events | Envelope/message dedupe plus F3 row-serialized comment tombstones/order | Stale sync and competing comment writers now tested on PostgreSQL. Terminal deletion is a conservative local rule; provider restoration is unverified and unsupported. |
| Inbox/customer/order panel and broad filters | Facebook two-pane inbox/simple reply panel | Orders intentionally deferred; customer/filter gaps listed separately. |
| OpenAPI, development Swagger/Redoc, API.md | Manual API.md plus schema settings only | Schema publication NOT_STARTED; docs PARTIAL. |
| Backend-only ngrok example | Frontend same-origin HTTPS tunnel/proxy | Existing intentional session-preserving change. |
| Admin/operations | Superuser-only admin; business add/change disabled, deletion allowed; secrets/raw fields hidden | More permissive than docs' “read-only” wording, narrower than full CRUD. |
| Finished Meta setup/acceptance | Detailed manual guide, verified same-origin public routing and local credential-name/readiness check; no live result | External acceptance remains BLOCKED on Dashboard/Page/role state and a persistent public URL. Local tests cannot close it. |

Facebook health/reconnect and polling are aligned with the report, not deviations. Missing Instagram refresh, orders and payments are not defects in the authorized Facebook slice.

## Current blockers

| Work | Status | Evidence / unblocking prerequisite |
|---|---|---|
| Real development-Page OAuth, publishing, subscription, comment/Messenger acceptance | BLOCKED | Public route blocker resolved for the active Cloudflare quick tunnel: health is 200; webhook and callback GETs reach Django and return its expected 403 validation/auth responses rather than frontend 404. Dashboard app roles, Page/tester access, callback verification and Page fields were not inspectable here. | Use a persistent public HTTPS origin before registering Dashboard URLs; then add authorized test assets and perform the checklist. Secrets stay only in backend configuration. |
| Acceptance for non-app-role production businesses | BLOCKED | No evidence of applicable App Review/Advanced Access, business verification or published privacy/deletion URLs. Check requirements for actual app and have owner complete what applies. This does not block local work or necessarily require review before development-role testing. |

The 2026-10-14 official-document check again found direct Meta developer pages rate-limited (HTTP 429). Meta’s published Messenger Postman collection confirms the standard response-window/send prerequisites used by the code, but does not replace real Page v26 acceptance. Full provider acceptance remains outstanding. Browser login credentials were not invented, OAuth consent was not initiated, and no external post/comment/message/subscription was made.

## Current working order

F1–F7, Page-default static automation and the local post publishing/per-post override workflow are DONE as local implementations as of 2026-10-14. The single recommended next task is **run one controlled Facebook development-Page acceptance covering Page publishing and per-post automation** after restoring a persistent public callback/webhook URL. Do not start AI or another provider while these writes are unproven.

## Plan Changes

### 2026-10-13 — Replace discovery placeholder with audited state

- **Previous plan:** Foundation → connection → content → Messenger → webhooks → frontend, labelled DISCOVERY / INITIAL IMPLEMENTATION. Other sections contained examples, not completed-work history.
- **New plan:** Preserve implemented domains; harden confirmed defects, close coverage/contract gaps, then verify live Facebook acceptance and production readiness.
- **Reason:** Every original phase has substantial implementation. Fresh checks pass within recorded limits, but probes show correctness gaps missed by existing tests, and live Meta prerequisites/acceptance are absent. Reimplementing local capabilities or adding future domains is unjustified.
- **Impact:** No application/API/schema changes. Existing architecture retained. Local implementation, test evidence and external acceptance separated. Facebook-first product goal unchanged.
- **Status:** ACCEPTED for planning; implementation under this revised order has not started.

### 2026-10-14 — Advance from verified F1 to F2

- **Previous plan:** F1 was the single recommended next task.
- **New plan:** F1 is DONE for new ingestion and reply-window enforcement; F2 permanent-permission scheduling is next.
- **Reason:** Focused tests, full SQLite and full PostgreSQL suites verify F1, including API/worker rejection, monotonic inbound time and echo behavior. The remaining legacy-data provenance limitation is recorded rather than silently rewriting existing data.
- **Impact:** Four narrowly scoped production files changed; non-authorization timestamp fallbacks made explicit for compatibility. Existing schema, frontend and product scope retained. No F2–F7 implementation.
- **Status:** ACCEPTED.

### 2026-10-14 — Advance from verified F2 to F3

- **Previous plan:** F2 permanent-permission scheduling was next.
- **New plan:** F2 is DONE; F3 comment deletion/order protection is the single next task.
- **Reason:** Regression tests prove permanent scheduler exclusion, bounded temporary retries, domain isolation, retained data and intentional recovery. Full PostgreSQL suite and clean migrations pass, with F1 preserved.
- **Impact:** Existing account states reused; one counter field/migration added because previous account retries had no persistent bound. No frontend, dependency, F3–F7 or product expansion. Scope/subscription additions discovered in existing source are preserved and recorded, not attributed to F2.
- **Status:** ACCEPTED.

### 2026-10-14 — Advance from verified F3 to F4

- **Previous plan:** F3 comment tombstones/order was next.
- **New plan:** F3 is DONE for retained comment rows; F4 successful-response validation is the single next task.
- **Reason:** The original stale-sync test failed before the change and passes afterward. Full SQLite/PostgreSQL suites verify ordering, tenant isolation, replies, duplicate deliveries and concurrent inserts/updates while retaining F1/F2.
- **Impact:** Two production service files changed; existing fields/constraints reused, no migration or frontend/API-shape change. Terminal deletion and unversioned-sync precedence are explicit conservative choices. Counts, post-level cascading and F4–F7 are not bundled.
- **Status:** ACCEPTED.

### 2026-10-14 — Advance from verified F4 to F5

- **Previous plan:** F4 malformed successful provider-response handling was next.
- **New plan:** F4 is DONE for top-level Graph response validation; F5 nested/null normalization is the single next task.
- **Reason:** Regression tests verify rejected malformed/empty JSON, invalid collection/paging shape, failed second-page account sync, bounded retry and one-attempt ambiguous writes. Full SQLite/PostgreSQL suites retain F1–F3 behavior.
- **Impact:** Graph client and OAuth token-exchange call sites changed; no model, migration, dependency, frontend or public API-shape change. Nested optional provider fields remain outside F4.
- **Status:** ACCEPTED.

### 2026-10-14 — Advance from verified F5 to F6

- **Previous plan:** F5 nested/null normalization was next.
- **New plan:** F5 is DONE; F6 sync-role alignment is the single next task.
- **Reason:** Focused normalization cases and complete SQLite/PostgreSQL suites show that malformed optional nested values no longer abort valid records or webhook processing, while missing provider identities do not create rows. F1–F4 behavior remains covered.
- **Impact:** Four backend service modules and one new regression suite changed. No model, migration, dependency, frontend, public API or provider-client protocol change was introduced. F7 and product expansion remain out of scope.
- **Status:** ACCEPTED.

### 2026-10-14 — Advance from verified F6 to F7

- **Previous plan:** F6 sync-role alignment was next.
- **New plan:** F6 is DONE; F7 comment-reply delivery safety is the single next task.
- **Reason:** One shared backend permission now covers Page connection lifecycle and both manual sync endpoints. The owner/admin and AGENT matrix, direct denied requests, tenant isolation, role-aware UI and documentation all pass verification.
- **Impact:** No schema, provider, token, task or product-domain change. The active-company role is returned to the frontend only to hide matching controls; backend permissions remain authoritative.
- **Status:** ACCEPTED.

### 2026-10-14 — Advance from verified F7 to integration onboarding feedback

- **Previous plan:** F7 comment-reply delivery safety was next.
- **New plan:** F7 is DONE; surface OAuth/Page-selection errors in the integration UI as the single next visible-product task.
- **Reason:** Durable attempts, exact idempotency and explicit ambiguous delivery behavior now prevent unsafe duplicate Facebook comments. The next locally actionable gap is a visible integration failure state; live acceptance remains externally blocked.
- **Impact:** F7 adds one social model/migration, API response shape, frontend outcome UI and regression coverage. It does not add provider retries, reconciliation, Messenger features or future domains.
- **Status:** ACCEPTED.

### 2026-10-14 — Prepare real Facebook Page acceptance

- **Previous plan:** Surface integration Page-choice/OAuth errors before attempting provider acceptance.
- **New plan:** First complete the documented real development-Page acceptance checklist once a reachable same-origin HTTPS callback/webhook and authorized Dashboard assets exist.
- **Reason:** F1–F7 are complete and the user prioritized proof against a real Page. The audit found local Meta configuration names and running services, but the configured public origin returned 404 for safe verifier and health probes. There is no basis to initiate OAuth or claim a live result.
- **Impact:** META_SETUP.md was rewritten as the Dashboard/tunnel/manual-test runbook, including the current seven-scope code contract. No application source, schema, provider scope, secret or external Meta state changed.
- **Status:** BLOCKED — USER META CONFIGURATION REQUIRED.

### 2026-10-14 — Resolve public same-origin routing and CSRF blocker

- **Root cause:** the configured public hostname belonged to an inactive tunnel, so it returned frontend/proxy 404. The frontend already rewrote `/api/*` to Django, but Django's `/health/` had no public rewrite. Once the public origin was made the frontend origin, Next forwarded local development's `Origin: http://localhost:3000`; the earlier settings trusted only the public origin and rejected that request during CSRF origin validation.
- **Implementation:** Next now also rewrites `/health/*` to Django. `CSRF_TRUSTED_ORIGINS` adds an explicit comma-separated allowlist to the existing public frontend/backend origins; local development config includes `http://localhost:3000`. The public Cloudflare quick tunnel targets Next on port 3000, preserving browser cookies and forwarding existing `/api/*` requests without a body-parsing handler.
- **Validation:** public health returned 200; public webhook GET and OAuth callback GET returned Django's expected 403 validation/auth responses, proving they no longer end in Next 404. A local login POST with `Origin: http://localhost:3000` is no longer rejected for origin mismatch. Existing webhook tests cover raw-body HMAC verification.
- **Limit:** a Cloudflare quick tunnel URL changes when the process restarts. It is suitable for the current routing proof, not Dashboard registration; use a named/reserved tunnel or deployed domain for real Meta acceptance.
- **Status:** public route blocker RESOLVED for the active tunnel. Live Meta acceptance remains BLOCKED on external Dashboard assets.

### 2026-10-14 — Add OrderHub post publishing and per-post automation

- **Previous plan:** Static comment automation was Page-scoped; posts were a read-only Facebook sync model/API with no `/posts/new`, draft, schedule or publish lifecycle.
- **New plan:** Keep the Page default and add an explicit provider-neutral post override. Add the smallest Facebook authoring lifecycle required by the request: local DRAFT/SCHEDULED state, text or one public HTTPS image, one-shot Celery publish, content lock after publish/ambiguity, and automation editing after publication.
- **Reason:** The user explicitly required configuring automation while creating, scheduling and later managing an OrderHub-created post. The referenced Social Post Publishing feature did not exist in the repository, so a post rule alone could not satisfy the journey.
- **Impact:** `social.0005` extends Post and adds SocialPostCommentAutomation plus attempt source links. OAuth now requests `pages_manage_posts`. No AI, keyword matching, binary media storage, Instagram, orders, payments or new infrastructure.
- **Status:** ACCEPTED; local implementation and mocked provider contracts verified. Live Meta Page publishing/private-reply acceptance remains blocked on user Dashboard/test assets and public HTTPS configuration.

### 2026-10-14 — Connect the new Figma React/Vite UI to Django

- **Previous implementation:** The active `frontend/` was a single 1,400-line Figma Make demo with hard-coded people, posts, comments, messages and timers. The working Next backend client had been moved to `frontendd/`.
- **New implementation:** Preserve the new visual system while adopting the `mak_portal` feature-oriented structure. Session auth, active company context, typed API/CSRF client, TanStack Query data flows and React Router routes now drive every product screen. Vite proxies `/api/*` and `/health/*` to Django on the same browser origin.
- **Reason:** A static visual demo could not enforce tenant context, role policy, idempotency or provider delivery states. The user explicitly selected the new UI and required it to be connected without reverting its design.
- **Impact:** Active frontend technology changes from Next to React/Vite. Backend API/schema/provider behavior and F1–F7 are unchanged. The legacy Next source stays in `frontendd/` for reference; its tests no longer validate the active UI.
- **Status:** ACCEPTED; local API routing, build and focused client regressions are verified. Active-browser end-to-end coverage remains to be rebuilt.

## Completed work record

### 2026-10-13 — Repository-state audit

- Inspected original prompt, instructions/report, source/configuration/migrations/tests and docs.
- Recorded actual capabilities, architecture, deviations, coverage gaps and blockers.
- Reran checks/clean PostgreSQL migrations; reproduced F1–F5 using disposable probes; recorded warnings, initial failures and successful fallback/retry.
- Updated only PLANS.md. Application source, tests, dependencies, environment configuration and research report unchanged. Temporary PostgreSQL container removed; normal services left running.
- No live Meta acceptance, App Review submission, deployment or next-phase implementation performed.

### 2026-10-14 — Real Facebook acceptance preparation and verification

- **Repository/config inspection:** reviewed OAuth, Page discovery/selection, encrypted token storage, Graph client, webhook ingress/processing, Messenger send/window enforcement, runtime settings, environment examples, API and Meta documentation. Required Meta environment variable names are locally configured, without reading or exposing their values. Backend, Celery and beat are running locally.
- **Official-contract result:** direct Meta developer-document pages were rate-limited (HTTP 429), so no wording-only code change was made. Meta public Messenger Postman collection confirms the Page-token MESSAGE task, pages_messaging, POST /{page-id}/messages with PSID and messaging_type=RESPONSE, and the ordinary 24-hour response window. It does not prove live v26 Pages contracts.
- **Documentation correction:** META_SETUP.md now records all seven scopes actually required by the current selection code, including business_management; the prior statement that it was not required was inaccurate. It adds exact callback/webhook paths, Dashboard roles/test Page instructions, same-origin frontend tunnel instructions, environment-variable names, manual run commands and the requested acceptance checklist.
- **Live result:** BLOCKED — USER META CONFIGURATION REQUIRED. The configured public HTTPS origin returned HTTP 404 for safe webhook-verifier and health probes. Dashboard roles, development Page/tester assets and an authenticated OWNER test session were unavailable. No OAuth consent, token exchange, Page selection, Graph request, webhook subscription, comment reply, Messenger reply or external message was performed or claimed.
- **Code changes:** none. Only META_SETUP.md and this plan changed. No token, app secret, authorization header or encryption key was read, printed, modified or committed.

Commands run from the repository:

| Command | Actual result |
|---|---|
| backend/.venv/bin/pytest -q --tb=short | **240 passed, 11 skipped**; PostgreSQL-only concurrency tests skipped on SQLite. F1–F7 are included. |
| DATABASE_URL=postgresql://orderhub:orderhub@127.0.0.1:58549/orderhub backend/.venv/bin/pytest -q --tb=short | **251 passed**, no warnings, including all concurrency tests. Disposable PostgreSQL 17 removed afterward. |
| Backend Ruff, formatting, migration consistency and Django check | PASS; 101 files already formatted, no migration changes and no system issues. |
| frontend: npm run typecheck; npm run lint; npm test -- --run; npm run build | PASS; **11** unit tests and production build passed. |
| frontend: npm run test:e2e -- --workers=1 --timeout=60000 | **2 passed, 1 skipped**; mocked owner/AGENT workflows pass. Live Django session remains skipped because no test credential file was supplied. |

### 2026-10-14 — Same-origin tunnel routing correction

- Added a `/health/*` rewrite beside the existing `/api/*` rewrite, so public health checks reach Django while ordinary frontend routes remain handled by Next.
- Added `CSRF_TRUSTED_ORIGINS` to settings and the environment example. The active local configuration keeps `http://localhost:3000` trusted in addition to its public tunnel origin; no wildcard origin was used.
- Rebuilt backend, Celery and beat images so the settings correction is running. Started a temporary frontend Cloudflare quick tunnel and configured the local backend public/redirect URLs to its origin. The prior quick tunnel expired after its process stopped; no permanent URL or Meta Dashboard state was changed.
- Safe probes: public `/health/` => 200; public `/api/meta/webhook/` => 403 from Django without a verify token; public `/api/meta/facebook/callback/` => 403 from Django without an authenticated session. Local health through Next => 200. A dummy local-origin login POST no longer contains Django's `Origin checking failed` rejection.
- Validation: backend `pytest` => 240 passed, 11 PostgreSQL-only skipped; Ruff/format/Django check pass. Frontend typecheck, lint, 11 unit tests and production build pass. The running backend confirms both the local and public origins are trusted for CSRF.

### 2026-10-14 — F1 inbound timestamp eligibility implemented and verified

- **Implemented:** shared parser returns aware UTC datetime or None, safely handles numeric seconds/milliseconds and invalid/overflowing values, rejects naive times instead of guessing timezone. Shared inbox validator rejects non-positive epoch and time more than five seconds ahead. Missing/invalid time uses local receipt time only for Message.sent_at / conversation preview display; never for last_inbound_at. Valid customer time advances under the existing conversation lock only for newly inserted messages. Echoes/duplicates/older messages preserve it.
- **Authorization decision:** five seconds is a small explicit local skew allowance, not a Meta guarantee. The exact 24-hour boundary is ineligible. Both the existing API gate and existing worker gate call the hardened can_reply; no worker lifecycle or public API change was needed. Existing trusted timestamps survive invalid arrivals.
- **Compatibility:** non-authorization post/comment display fallbacks are explicit at their call sites because the shared parser no longer invents time. F2–F7 behavior is untouched. No frontend, dependency, schema or migration changes.
- **Tests added:** 20 parser/validation cases, 29 inbox timestamp/API/worker/history/echo-merge cases, 12 signed-webhook time cases, one PostgreSQL concurrent inbound case; frozen clock uses unittest.mock, no new dependency. Existing tenant/send-idempotency tests pass unchanged.
- **External contract check:** [Meta's published Messenger API collection](https://www.postman.com/meta/messenger-platform-api/documentation/iyp204x/messenger-platform-api) confirms the standard 24-hour message window. Direct [Send Messages](https://developers.facebook.com/docs/messenger-platform/send-messages/) fetch returned HTTP 429; [messages webhook reference](https://developers.facebook.com/docs/messenger-platform/webhooks/webhook-events/messages/) was inaccessible. Existing numeric-millisecond webhook / offset-bearing history conventions are retained; current v26 field-level/live acceptance is not claimed. Boundary/skew are explicit conservative local policy decisions.
- **Remaining limitation:** no automatic reconstruction of previously stored last_inbound_at values. Legacy values have no timestamp-provenance flag, so a plausible value produced by the old fallback cannot be distinguished from valid provider time. Existing materially future values are rejected by the new gate; a future legacy value may prevent a newer valid inbound time from replacing it under the monotonic rule. Review/reset affected legacy data from trustworthy source evidence if needed; no destructive data cleanup was performed. This does not affect new ingestion's timestamp invariant.
- **Deployment:** source/tests validated locally; existing application containers were not rebuilt/restarted. Deploy the updated backend/worker together to activate the correction. Local secret values and environment files were not read/changed for this task.

Commands run from `backend/` (final results):

| Command | Actual result |
|---|---|
| `.venv/bin/pytest -q --tb=short tests/test_provider_time.py tests/test_inbox_timestamps.py tests/test_webhooks.py tests/test_inbox.py tests/test_social.py` | 84 passed. Earlier focused run before final echo/concurrency additions: 83 passed. |
| `.venv/bin/pytest -q --tb=short tests/test_inbox_timestamps.py` | Final targeted rerun: 29 passed after making test queue timestamps explicit (model defaults retain their original clock callable). |
| `.venv/bin/pytest -q --tb=short` | 110 passed, 3 skipped (PostgreSQL-only concurrency cases). |
| `DATABASE_URL=postgresql://orderhub:orderhub@localhost:60904/orderhub .venv/bin/pytest -q --tb=short` | 113 passed, including all three concurrency cases; no warnings. Disposable PostgreSQL 17, same database setup pattern documented in backend README; normal Compose services unchanged. |
| `.venv/bin/ruff check .` | PASS. Initial check identified one extra blank line after imports; corrected, then rerun passed. |
| `.venv/bin/ruff format --check .` | PASS, 93 Python files. Changed files were formatted before validation. |
| `.venv/bin/python manage.py makemigrations --check --dry-run --settings=config.test_settings` | PASS, no changes detected. |
| `.venv/bin/python manage.py check --settings=config.test_settings` | PASS, no issues. |

Frontend checks were not rerun because no frontend/API-contract changes were made. Live Meta requests were not performed. Temporary test database container removed after verification.

### 2026-10-14 — F2 permanent failure scheduling implemented and verified

- **Classification:** existing Meta exception subclasses now expose RETRYABLE, AUTH_REQUIRED, PERMISSION_REQUIRED or PERMANENT_OTHER. Existing Graph HTTP/code mapping, three-attempt transient reads, Retry-After and single-attempt writes remain unchanged. Generic/unknown errors are conservatively permanent; no new provider code mapping was invented. Missing/undecryptable local credentials are auth failures.
- **State policy:** auth and permission => NEEDS_REAUTH / FAILED / no next_sync_at, retaining encrypted token and normalized history. Safe last_error stores only existing application error codes. The existing API exposes status/error; no secret, raw exception or provider message is added to storage/logs. Generic permanent errors => ACTIVE / FAILED / no next_sync_at; this pauses synchronization for operator action without falsely declaring a token invalid.
- **Transient policy:** sync_failures persists consecutive failed account runs, capped at five. Attempts 1–4 schedule at max(Retry-After, 300 × 2^(failure−1)) seconds plus 0–3s jitter. The fifth pauses automatic synchronization. Successful full sync resets the counter/error and schedules five minutes later. Due checks also apply inside the worker, so duplicate deliveries cannot bypass backoff. No Celery autoretry loop was added. Health checks retain the client's bounded read attempts and daily cadence for eligible accounts; paused/non-active accounts are excluded and health never reactivates a connection.
- **Domain policy:** feed and inbox are attempted separately. Feed permission, transient or other non-auth failure permits an inbox attempt; auth failure stops the run. The strongest recorded error wins (auth, permission, other permanent, retryable), so inbox success cannot erase a feed failure. All currently required scopes remain an onboarding contract; no long-term per-capability scheduling was introduced. Connection status and sync failure are finalized together under the claimed account/credential/start-time guard.
- **Recovery:** existing manual sync actions reset the retry cycle only for ACTIVE accounts; NEEDS_REAUTH requires reconnect. Page selection must belong to the company/user, remain unexpired, contain the server-side Page token and all current scopes, and successfully subscribe before replacing credentials/marking ACTIVE. Reconnect clears prior count/schedule/lease. Existing roles remain unchanged (F6). Webhook sync hints only queue ACTIVE/IDLE accounts, preserving pauses/backoff. Shared credential-failure handling also suspends sends/replies/standalone inbox sync on permission failure.
- **Schema:** `meta.0004_socialaccount_sync_failures` adds a default-zero positive small integer. No new account state, model or dependency. Existing FAILED rows with no next attempt now require manual action; rows with a due retry are classified on their next failure. No history or credential cleanup was performed.
- **Tests added:** 29 policy cases, 11 client classification/read-timeout cases, one PostgreSQL competing-sync-worker case. Includes retained posts/conversation/messages, repeated dispatch without loops, retry exhaustion/reset, long Retry-After, API error visibility, rejected reconnect/foreign selection, paused webhook hints, stale worker results and unusable local credentials. F1 assertions remain unchanged and pass; existing concurrency worker-thread connections are now explicitly closed during test cleanup.
- **Provider verification limit:** fetching the official [Graph API error handling guide](https://developers.facebook.com/docs/graph-api/guides/error-handling/) returned HTTP 429; official-domain searches did not yield usable confirmation. Preserve existing HTTP/code classification; code 190 is auth regardless of subcode (463/467 fixtures exercise that existing rule, not newly inferred distinctions). No current provider/live acceptance claim.
- **Additional findings:** existing OAuth source requests business_management and subscribe includes message_echoes; neither was added/changed by F2. Older six-scope documentation needs later provider acceptance review. Stale RUNNING recovery still has no separate crash counter, and large histories may repeatedly exceed worker limits before returning a classified error; crash/performance recovery is distinct remaining work. At that time, the existing F1 legacy timestamp-provenance limitation and F3–F7 remained open. Normalization defects were not fixed by the conservative pause policy.
- **Deployment:** migration and source verified on disposable PostgreSQL only. Normal application containers were not rebuilt/restarted and their database was not migrated. Apply migrations and deploy matching backend/worker code together. No environment/secret files changed; no authorized-asset Meta acceptance was attempted.

Commands run from `backend/`:

| Command | Actual result |
|---|---|
| `.venv/bin/pytest -q --tb=short tests/test_sync_policy.py tests/test_meta_client.py tests/test_integrations.py tests/test_tokens_oauth.py tests/test_queue.py tests/test_social.py tests/test_inbox.py` | **73 passed**. Initial run had 3 test-harness failures: mocked delay instead of the view enqueue helper, allowing eager dispatch (including one rejected request using a synthetic token). Corrected helper mocking and blocked unmocked HTTP in the new policy suite; final runs do not depend on live Meta. |
| `.venv/bin/pytest -q --tb=short tests/test_provider_time.py tests/test_inbox_timestamps.py tests/test_webhooks.py` | **73 passed**; F1 regression verification. |
| `.venv/bin/pytest -q --tb=short` | **150 passed, 4 skipped**; only PostgreSQL concurrency tests skipped on SQLite. |
| `DATABASE_URL=postgresql://orderhub:orderhub@127.0.0.1:61539/orderhub .venv/bin/pytest -q --tb=short` | **154 passed**, no warnings; disposable PostgreSQL 17, clean teardown. |
| `DATABASE_URL=postgresql://orderhub:orderhub@127.0.0.1:61539/orderhub .venv/bin/pytest -q --tb=short tests/test_concurrency.py` | **4 passed**, no warnings after test thread cleanup. Initial standalone run passed all assertions but warned about three open connections during database teardown; corrected the two existing tests to close thread connections, then reran this command and the full PostgreSQL suite. |
| `DATABASE_URL=postgresql://orderhub:orderhub@127.0.0.1:61539/orderhub .venv/bin/python manage.py migrate --noinput --settings=config.test_settings` | PASS on empty PostgreSQL DB, including all eight domain migrations and new meta.0004. |
| `.venv/bin/ruff check .` | PASS. |
| `.venv/bin/ruff format --check .` | PASS, 95 files; initial check found one changed file needing formatting, corrected before final check. |
| `.venv/bin/python manage.py makemigrations --check --dry-run --settings=config.test_settings` | PASS, no changes detected. |
| `.venv/bin/python manage.py check --settings=config.test_settings` | PASS, no issues. |

Disposable database setup: `docker run --rm -d --name orderhub-f2-test-db -e POSTGRES_USER=orderhub -e POSTGRES_PASSWORD=orderhub -e POSTGRES_DB=orderhub -p 127.0.0.1::5432 postgres:17-alpine`; Docker assigned port 61539. These are disposable test credentials. Container removed after validation. Frontend checks not rerun because frontend source/API shape were unchanged. No CI, live acceptance or F3 implementation.

### 2026-10-14 — F3 comment tombstones and ordering implemented and verified

- **Implementation:** `backend/apps/social/services.py` routes sync, reply-result and webhook comment writes through one atomic upsert using select_for_update().get_or_create() with the existing unique `(social_account, external_id)` constraint. Existing-row updates lock before reading state; competing first inserts wait on uniqueness and lock the returned row. No provider HTTP call is made within that upsert lock. `backend/apps/meta/services/webhooks.py` delegates deletion and add/edit state to that writer rather than reading/writing ordering separately.
- **Deletion rule:** an authenticated remove/delete action is terminal for the retained comment ID. It preserves the row/relationships, clears message and can_reply, and cannot be undone by sync, an older/equal/newer add/edit, or a missing timestamp. A delayed deletion also wins over a newer non-delete notification because no restoration semantics have been verified; last_event_at never moves backwards. This intentionally prioritizes deletion knowledge over an unproven restore interpretation.
- **Active ordering:** reuse last_event_at; a strictly newer valid event can update an active row. Equal-time non-delete events keep the existing state. Missing/malformed/non-positive or more-than-five-seconds-future time cannot replace a known watermark. The five-second allowance is local policy, not a Meta guarantee. Creation time is display metadata and local receipt time is never a revision. Unversioned sync cannot supersede a timed webhook. When no watermark exists, ordinary active sync and untimed events retain existing update behavior; their relative order cannot be proven.
- **Reply and nested behavior:** API already filtered is_deleted=False and still returns 404 without provider I/O for deleted rows. The reply service now also rechecks persisted deletion for a stale loaded instance. Sync skips fetching replies for a tombstoned parent returned by a stale feed; nested child tombstones and parent references remain intact. Concurrent deletion after the final reply check can still race an already-started upstream call; no remote atomicity or F7 durability redesign is claimed.
- **Schema:** unchanged; existing is_deleted, last_event_at and uniqueness suffice. `makemigrations --check` reports no changes. No migration was added or manually applied to the running application database.
- **Files changed:** `backend/apps/social/services.py`, `backend/apps/meta/services/webhooks.py`, new `backend/tests/test_comment_ordering.py`, `backend/tests/test_webhooks.py`, `backend/tests/test_concurrency.py`, and `PLANS.md`. F1 parser/inbox logic, F2 tasks/classification, Graph client, OAuth, dependencies, environment files and frontend source remain unchanged.
- **Regression evidence:** 27 ordering cases, one signed webhook/deduplication case, six PostgreSQL concurrency cases. Concurrency covers existing and absent comment rows, sync/delete in both transaction orders, and older edit versus newer deletion; the competing writer is asserted to wait while the first transaction is open. Includes delete-first snapshots, repeated deletion, invalid-time handling, future add/edit not restoring, active newer edits, tenant identity isolation, nested replies, hidden deleted rows and reply denial. The initial single stale-sync test failed on the original implementation; final focused/full suites pass.
- **Provider documentation limit:** official [Page webhook reference](https://developers.facebook.com/docs/graph-api/webhooks/reference/page/) and [Comment reference](https://developers.facebook.com/docs/graph-api/reference/comment/) returned HTTP 429; alternate official documentation URLs were inaccessible. No restoration/version field was inferred from third-party sources. Existing research-report and code convention of numeric-millisecond entry.time is preserved via the safe parser; live Page-feed timestamp units/order remain to be validated. Terminal deletion protection does not depend on those units. A provider envelope timestamp is not claimed to be an object revision guarantee.
- **Remaining limitations:** count reconciliation is unchanged; Post.comment_count may lag. Post deletion currently physically cascades to comments, removing tombstones; a later stale post snapshot can recreate that whole hierarchy. This post-level reconciliation defect is separate from retained-comment-row F3 and is not fixed here. No repair of previously resurrected comments or invalid legacy ordering timestamps was attempted. A timed active webhook can keep content stale if a later edit webhook is missed, because current sync has no trustworthy revision field. Oppositely ordered multi-comment batches can still require normal transaction retry on deadlock; tests cover competing writes to one identity, not every batch graph. At that time, F4–F7 remained open.
- **Deployment:** source validated locally; application containers were not rebuilt/restarted. Deploy matching backend/worker source to activate. No live Meta acceptance or real-credential requests performed by the tests.

Commands run from `backend/`:

| Command | Actual result |
|---|---|
| `.venv/bin/pytest -q --tb=short tests/test_comment_ordering.py` (before production change) | **1 failed**, reproducing resurrection (`is_deleted=False`). |
| `.venv/bin/pytest -q --tb=short tests/test_comment_ordering.py tests/test_social.py tests/test_webhooks.py tests/test_sync_policy.py` | Final focused run: **84 passed**. Earlier intermediate runs: 57 and 83 passed as coverage was added. |
| `.venv/bin/pytest -q --tb=short` | **178 passed, 10 skipped**; PostgreSQL-only concurrency cases skipped on SQLite. Includes F1 and F2 regression suites. |
| `DATABASE_URL=postgresql://orderhub:orderhub@127.0.0.1:62000/orderhub .venv/bin/pytest -q --tb=short tests/test_concurrency.py` | **10 passed**, no warnings. |
| `DATABASE_URL=postgresql://orderhub:orderhub@127.0.0.1:62000/orderhub .venv/bin/pytest -q --tb=short` | **188 passed**, no warnings, clean teardown. |
| `.venv/bin/ruff check .` | PASS. |
| `.venv/bin/ruff format --check .` | PASS, 96 Python files. |
| `.venv/bin/python manage.py makemigrations --check --dry-run --settings=config.test_settings` | PASS, no changes detected. |
| `.venv/bin/python manage.py check --settings=config.test_settings` | PASS, no issues. |

PostgreSQL setup: `docker run --rm -d --name orderhub-f3-test-db -e POSTGRES_USER=orderhub -e POSTGRES_PASSWORD=orderhub -e POSTGRES_DB=orderhub -p 127.0.0.1::5432 postgres:17-alpine`; Docker assigned port 62000. Disposable test credentials only. Test databases were created/migrated by pytest; no separate clean-migration command required/run because the schema is unchanged. Container removed after verification. Frontend checks not rerun; no frontend changes.

### 2026-10-14 — F4 successful-response validation implemented and verified

- **Implementation:** `FacebookGraphClient.request` no longer replaces JSON decode failures with `{}` for HTTP success. Every successful Graph response must decode to a JSON object and match the expected top-level shape. Collection methods require `data` as a list of objects, optional `paging`/`cursors` as objects, and a cursor when `paging.next` is present. Direct methods check ID, access token, reaction total, Messenger message ID or subscription acknowledgment as applicable. OAuth token exchange supplies its access-token expectation. HTTP error responses retain their existing structured error-code classification.
- **Read policy:** malformed successful GET responses raise MetaTemporaryError and use the existing maximum of three request attempts. A later valid retry can recover. When the second page fails, iteration raises; account sync records FAILED, retains ACTIVE and the encrypted token, increments the F2 failure counter and schedules a bounded retry. Valid rows observed before failure may already be stored locally; they are not called a completed reconciliation and existing local rows are not deleted. This task does not make the entire feed transaction atomic across network requests.
- **Write policy:** malformed successful send/reply/subscribe results raise MetaDeliveryUnknown. Writes remain one attempt; outbound worker marks the message FAILED with a safe code and does not resend the same idempotency key. Synchronous comment reply ambiguity remains F7. Subscription acceptance uses a truthy success acknowledgment (`true` boolean or string); live Page-subscription shape still needs provider acceptance.
- **Safety:** diagnostic logging records only method, status and expected response category; no raw response body, credential, Authorization header or sensitive URL. Generic successful JSON objects must be nonempty. Tests include HTML containing a synthetic token and verify its absence from logs. Existing F1–F3 source paths are unchanged and all regression suites pass.
- **Provider evidence:** [Meta's Facebook Postman collection](https://www.postman.com/meta/facebook/documentation/r56bjfd/facebook-api?entity=request-23987686-0b79260c-96bd-49de-875b-6076213785fc) shows collection `data` and `paging.cursors`; [Meta's Messenger Postman collection](https://www.postman.com/meta/messenger-platform-api/documentation/iyp204x/messenger-platform-api?entity=request-22794852-31d80e54-aa3d-4c64-9e01-14925626797e) shows successful `message_id`. These support local top-level checks; no live v26 Page/app acceptance was performed. Page subscription acknowledgment and optional nested fields remain integration validation items.
- **Files changed:** `backend/apps/meta/services/facebook.py`, `backend/apps/meta/services/oauth.py`, new `backend/tests/test_meta_protocol.py`, and `PLANS.md`. No schema/migration change or environment/secret modification.
- **Remaining limits:** F5 media/null/nested content normalization remains open. A valid top-level collection with malformed optional nested fields can still fail during domain normalization; account sync then follows its existing F2 unknown-error policy. This change does not fix that separate defect. F6 role inconsistency and F7 comment reply durability/ambiguity remain open. No frontend or application container rebuild/restart occurred.

Commands run from `backend/` (final results):

| Command | Actual result |
|---|---|
| `.venv/bin/pytest -q --tb=short tests/test_meta_protocol.py tests/test_meta_client.py tests/test_oauth_flow.py tests/test_sync_policy.py tests/test_comment_ordering.py tests/test_inbox_timestamps.py tests/test_provider_time.py` | **159 passed**. An earlier focused run after adding the second-page account case failed because its first post comments request was unmocked; after supplying that mock, the intended provider failure was verified. |
| `.venv/bin/pytest -q --tb=short` | **208 passed, 10 skipped**; PostgreSQL-only concurrency cases skipped on SQLite. |
| `DATABASE_URL=postgresql://orderhub:orderhub@127.0.0.1:61028/orderhub .venv/bin/pytest -q --tb=short` | **218 passed**, no warnings. Disposable PostgreSQL 17; includes all F1–F3 and F4 cases. |
| `DATABASE_URL=postgresql://orderhub:orderhub@127.0.0.1:61028/orderhub .venv/bin/pytest -q --tb=short tests/test_concurrency.py` | **10 passed**, no warnings. |
| `.venv/bin/ruff check .` | PASS. Initial run caught two unused imports in the new test file; removed before final check. |
| `.venv/bin/ruff format --check .` | PASS, 97 Python files. |
| `.venv/bin/python manage.py makemigrations --check --dry-run --settings=config.test_settings` | PASS, no changes detected. |
| `.venv/bin/python manage.py check --settings=config.test_settings` | PASS, no issues. |

Disposable PostgreSQL setup: `docker run --rm -d --name orderhub-f4-test-db -e POSTGRES_USER=orderhub -e POSTGRES_PASSWORD=orderhub -e POSTGRES_DB=orderhub -p 127.0.0.1::5432 postgres:17-alpine`; Docker assigned port 61028. No separate clean migration was run because there is no schema change. Container removed after validation. Frontend commands not rerun because frontend source/API shape was unchanged.

### 2026-10-14 — F5 nested provider normalization implemented and verified

- **Implementation:** Added small explicit helpers for trusted dict/list/client-iterator handling and safe text/count/boolean/provider-ID normalization. Social feed/comment sync, Messenger history/message storage, and webhook message/comment processing now use them at nested provider boundaries. A valid paginated Graph iterator remains supported; JSON nested arrays remain list-only.
- **Required vs optional policy:** malformed optional media, attachments, author metadata, participant names, text, counts, booleans and nested list/object containers are skipped or defaulted safely. A provider identity must be a nonempty string before a post, comment, customer, conversation or message can be created or deduplicated. The code never invents an ID or authorization timestamp. Required-ID webhook events are retained as signed raw events then marked IGNORED after one processing attempt; valid events with malformed optional values are PROCESSED without retry loops.
- **Safety:** F1 still permits only validated provider time to update `last_inbound_at`; receipt-time display fallback remains non-authorizing. F3 tombstone and ordering writes still flow through the locked comment upsert. F4 remains responsible for successful HTTP/JSON top-level protocol validation. Signature verification, webhook deduplication, tenant filters and message uniqueness are unchanged.
- **Schema/deployment:** no migration, dependency, environment, frontend or public API change. Application containers were not rebuilt or restarted. No live Meta call or credential was used.

Commands run from `backend/`:

| Command | Actual result |
|---|---|
| `.venv/bin/pytest -q --tb=short tests/test_provider_normalization.py tests/test_social.py tests/test_inbox.py tests/test_webhooks.py tests/test_comment_ordering.py tests/test_inbox_timestamps.py tests/test_meta_protocol.py` | **138 passed**. An intermediate implementation incorrectly rejected the Graph client’s pagination generator; it was corrected by separating safe client iterators from strict nested JSON lists. |
| `.venv/bin/pytest -q --tb=short` | **224 passed, 10 skipped**; skips are PostgreSQL-only concurrency tests. |
| `DATABASE_URL=postgresql://orderhub:orderhub@127.0.0.1:61395/orderhub .venv/bin/pytest -q --tb=short` | **234 passed**, no warnings. |
| `DATABASE_URL=postgresql://orderhub:orderhub@127.0.0.1:61395/orderhub .venv/bin/pytest -q --tb=short tests/test_concurrency.py` | **10 passed**, no warnings. |
| `.venv/bin/ruff check .` / `.venv/bin/ruff format --check .` | PASS / PASS; 98 files formatted. |
| `.venv/bin/python manage.py makemigrations --check --dry-run --settings=config.test_settings` | PASS, no changes detected. |
| `.venv/bin/python manage.py check --settings=config.test_settings` | PASS, no issues. |
| `DATABASE_URL=postgresql://orderhub:orderhub@127.0.0.1:61395/orderhub .venv/bin/python manage.py migrate --noinput --settings=config.test_settings` | PASS on empty disposable PostgreSQL 17; all existing migrations applied. |

Disposable database container `orderhub-f5-final-test-db` was removed after verification. Frontend checks were not rerun because no frontend code or API contract changed.

### 2026-10-14 — F6 role-policy alignment implemented and verified

- **Policy:** OWNER and ADMIN can connect, select, reconnect, disconnect and manually sync Facebook integrations. AGENT is the existing operator role: it can view posts/comments/inbox and send comment or Messenger replies, but cannot manage integrations or request provider synchronization.
- **Backend:** Added one shared CanManageIntegration permission and applied it to connect/callback/Page selection, account sync/disconnect and post sync. Existing company-scoped querysets preserve 404 for cross-tenant objects; same-tenant AGENT management requests receive 403. Account listing and daily operator endpoints remain member-accessible.
- **Frontend:** The active-company role is supplied by the authenticated session response and updated when switching companies. AGENT hides connect, select, reconnect, disconnect and both sync controls; it does not request Page choices. This is presentation only; the backend remains the authorization authority.
- **Documentation/schema:** SECURITY.md now records the matrix. No model, migration, dependency, token, worker, provider-client or public resource shape change was made beyond adding the active-company role to existing session/company-selection responses.

Commands run from the repository:

| Command | Actual result |
|---|---|
| `backend/.venv/bin/pytest -q --tb=short tests/test_role_policy.py tests/test_auth.py tests/test_integrations.py tests/test_social.py tests/test_inbox.py` | **26 passed**. |
| `backend/.venv/bin/pytest -q --tb=short` | **232 passed, 10 skipped**; skips are PostgreSQL-only concurrency tests. |
| `DATABASE_URL=postgresql://orderhub:orderhub@127.0.0.1:62805/orderhub backend/.venv/bin/pytest -q --tb=short` | **242 passed**, no warnings. |
| `DATABASE_URL=postgresql://orderhub:orderhub@127.0.0.1:62805/orderhub backend/.venv/bin/pytest -q --tb=short tests/test_concurrency.py` | **10 passed**, no warnings. |
| Backend Ruff, formatting, migration consistency and Django check | PASS; 99 files formatted and no migration generated. |
| `frontend: npm run typecheck; npm run lint; npm test -- --run; npm run build` | PASS; 8 unit tests and production build passed. |
| `frontend: npm run test:e2e -- --workers=1 --timeout=60000` | **2 passed, 1 skipped**; owner and AGENT mocked workflows pass, real Django auth remains skipped without credentials. |

Disposable PostgreSQL container orderhub-f6-test-db was removed. Application containers were not rebuilt/restarted and no live Meta credentials were used.

### 2026-10-14 — F7 durable comment-reply delivery implemented and verified

- **Policy:** Each `POST /api/comments/{id}/reply/` requires an idempotency UUID. The server commits a `CommentReplyAttempt` before making exactly one Meta write. A valid reply ID records `SENT`; a clear Meta rejection records `FAILED`; timeout, connection loss, malformed write success or unexpected post-write uncertainty records `DELIVERY_UNKNOWN`. The existing key returns the same attempt with no provider I/O. A different payload for that key is rejected. Deleted and cross-tenant comments remain blocked before a new attempt is created.
- **Safety and recovery:** `DELIVERY_UNKNOWN` is deliberately not converted to FAILED and has no automatic retry or feed-based reconciliation. It remains available in the durable row so neither the same key nor a fresh key for that comment can produce a duplicate outbound write after a browser/network failure, remount or process crash. `FAILED` is the only UI state offering a retry, which sends a fresh key because Meta definitively rejected the preceding attempt. Provider tokens and raw provider messages stay server-only.
- **Frontend/API:** The reply response is an attempt object (`SENT`, `FAILED` or `DELIVERY_UNKNOWN`) rather than a synthesized comment. The post-detail composer shows sent feedback, offers retry after only `FAILED`, and displays a persistent warning while disabling normal retry after `DELIVERY_UNKNOWN`. `backend/docs/API.md` records the required key and 201-new/200-replay response semantics.
- **Schema:** `social.0003_commentreplyattempt` adds the tenant-owned CommentReplyAttempt model, social-account/comment foreign keys, text, UUID key, status, optional provider reply ID/safe error payload, `(company, comment, client_idempotency_key)` uniqueness and a company/status index. The clean PostgreSQL migration applied successfully. No secrets, environment configuration, dependencies, workers or provider retry policy changed.
- **Remaining limitation:** A later Page feed sync does not reconcile an unknown attempt by provider content/ID. An attempt stays unknown until an operator checks Facebook; no delivery guarantee beyond a Meta response is claimed. The normal Meta test client is mocked, so live provider acceptance remains blocked.

Commands run from the repository:

| Command | Actual result |
|---|---|
| `backend/.venv/bin/pytest -q --tb=short` | **240 passed, 11 skipped**; PostgreSQL-only concurrency tests skipped on SQLite. |
| `DATABASE_URL=postgresql://orderhub:orderhub@127.0.0.1:63924/orderhub backend/.venv/bin/python manage.py migrate --noinput --settings=config.test_settings` | PASS on an empty disposable PostgreSQL 17 database, including `social.0003_commentreplyattempt`. |
| `DATABASE_URL=postgresql://orderhub:orderhub@127.0.0.1:63924/orderhub backend/.venv/bin/pytest -q --tb=short` | **251 passed**, no warnings. |
| `DATABASE_URL=postgresql://orderhub:orderhub@127.0.0.1:63924/orderhub backend/.venv/bin/pytest -q --tb=short tests/test_concurrency.py` | **11 passed**, including competing comment-key submission. |
| Backend Ruff, formatting, migration consistency and Django check | PASS; 101 Python files formatted, no model changes pending and no system issues. |
| `frontend: npm run typecheck; npm run lint; npm test -- --run; npm run build` | PASS; **11** unit tests and production build passed. |
| `frontend: npm run test:e2e -- --workers=1 --timeout=60000` | **2 passed, 1 skipped**; mocked owner/AGENT flows pass and live Django auth remains skipped without credentials. |

Disposable PostgreSQL container `orderhub-f7-final-test-db` was removed after verification. Application containers were not rebuilt/restarted and no live Meta credentials were used.

### 2026-10-14 — Social workspace UI redesign implemented and verified

- **UI:** Replaced the Facebook-specific visual treatment with provider-neutral `PostCard`, `PlatformBadge`, `ConversationList`, `AccountSelector`, `ChannelSelector`, `FilterBar`, `StatusBadge`, `AppSidebar` and `AppHeader` components. Desktop has grouped navigation and a contextual header; mobile has a compact header and bottom navigation. Posts, conversations and integrations share spacing, colors, cards, controls and state treatment.
- **Visual system:** The workspace now uses the selected eping-inspired palette: navy navigation, an emerald/cyan action gradient, pink unread emphasis, yellow brand accents and a pale mint canvas. This is a frontend-only visual refresh; routes, API data and real Facebook scope remain unchanged.
- **Contract:** Post and conversation API responses now include their social account `platform`. Both list endpoints accept optional `platform` and `social_account` filters after the active-company queryset is established. No model/migration, token, OAuth, webhook, Instagram provider, placeholder or external Meta change was introduced.
- **Safety:** Manager-only integration/sync controls, AGENT daily work, tenant isolation, CSRF/session behavior, 24-hour Messenger eligibility, message idempotency and F7 comment-delivery states are unchanged.

| Command | Actual result |
|---|---|
| `backend/.venv/bin/ruff check . && backend/.venv/bin/ruff format --check .` | PASS; 101 Python files formatted. |
| `backend/.venv/bin/pytest -q --tb=short` | **242 passed, 11 skipped** on SQLite; skips are PostgreSQL-only concurrency cases. |
| `DATABASE_URL=postgresql://orderhub:orderhub@127.0.0.1:61395/orderhub backend/.venv/bin/pytest -q --tb=short` | **253 passed** on disposable PostgreSQL 17. |
| `frontend: npm run typecheck; npm run lint; npm test -- --run` | PASS; **13** unit tests. |
| `frontend: npm run build` | PASS; all existing routes generated. |
| `frontend: npm run test:e2e -- --workers=1 --timeout=60000` | **2 passed, 1 skipped**; mocked owner/AGENT desktop/mobile workflows pass, live Django auth remains skipped without credentials. |

### 2026-10-14 — Static Facebook comment automation implemented and verified

- **Behavior:** One Page-scoped rule supplies static public and private texts. Only new webhook `add` events for top-level customer comments are eligible. Page-authored, automatic Page reply, nested, deleted, malformed and duplicate events cannot start another automation.
- **Durability:** `CommentReplyAttempt` now supports automatic PENDING public actions; `CommentPrivateReplyAttempt` stores the private action. Database constraints allow one automatic public and one private action per company/comment. The worker claims each as DELIVERY_UNKNOWN before one provider write; clear rejection is FAILED, valid ID is SENT and ambiguous outcomes remain terminal. Public/private actions execute independently.
- **API/UI:** `GET/PUT /api/meta/accounts/{id}/comment-automation/`; GET is member-readable and PUT is OWNER/ADMIN-only. Холболтууд contains the Page configuration form. The rule is disabled by default and editing snapshots affects future comments only.
- **Provider:** `FacebookGraphClient.send_comment_private_reply` posts static text to `/{comment-id}/private_replies` with the existing encrypted Page token and accepts only a non-empty `message_id` or `id`. `pages_messaging` is already in OAuth scopes. Current Meta developer private-reply pages returned 404/429; official v26 codegen still exposes private-reply comment fields, so exact endpoint/policy acceptance remains blocked on a real development Page.
- **Scope:** No AI, keyword matching, variables, per-post rules, Instagram, order/payment or new conversation subsystem. A customer's Messenger response continues through the existing Customer/Conversation/Message webhook path.

| Command | Actual result |
|---|---|
| `backend/.venv/bin/ruff check .; backend/.venv/bin/ruff format --check .; manage.py makemigrations --check; manage.py check` | PASS; 103 Python files formatted, no pending model changes, no Django issues. |
| `backend/.venv/bin/pytest -q --tb=short` | **272 passed, 12 skipped** on isolated SQLite. |
| Clean disposable PostgreSQL 17 migrate + full pytest | Migration `social.0004` applied; **284 passed**. |
| PostgreSQL `tests/test_concurrency.py` | **12 passed**, including competing automation workers. |
| `frontend: npm run typecheck; npm run lint; npm test -- --run` | PASS; **14** unit tests. |
| `frontend: npm run build` | PASS; all routes generated. |
| `frontend: npm run test:e2e -- --workers=1 --timeout=60000` | Final **2 passed, 1 skipped**. First run had one locator ambiguity after adding a second status element; the locator was narrowed and the complete browser suite passed. Live Django auth remains skipped without credentials. |
| Local Docker rebuild/migrate/runtime check | PASS; backend, Celery and beat rebuilt, `social.0004` applied, both automation tasks registered, backend health and frontend integrations route returned HTTP 200. |

Disposable PostgreSQL was removed after validation. Local application services remain running with the new source. No live Meta access token or customer/Page action was used, so provider delivery is not claimed.

### 2026-10-14 — OrderHub post publishing and per-post automation implemented and verified

- **Authoring:** OWNER/ADMIN can create a draft, edit draft/scheduled content, publish now, or select a local schedule. The composer supports text-only or one public HTTPS image URL. Published and delivery-unknown content is read-only; FAILED can be corrected and explicitly retried.
- **Delivery safety:** Due posts are row-claimed as DELIVERY_UNKNOWN before one `/{page-id}/feed` or `/{page-id}/photos` write. A nonempty provider ID records PUBLISHED, clear rejection records FAILED, and timeout/connection/malformed success remains terminal unknown. Beat dispatches due posts every 15 seconds; PostgreSQL concurrency proves one write.
- **Automation hierarchy:** SocialPostCommentAutomation is a one-to-one explicit override. Enabled override wins, disabled override blocks the Page default, and no override falls back to the Page rule. Existing public/private attempt uniqueness remains comment-based; snapshots make edits future-only and prevent resend. Synced Facebook posts can also receive an override through the detail endpoint.
- **UI/API:** `/posts/new`, `/posts/{id}/edit`, post status treatment and post-detail automation edit were added. `POST/PATCH /api/posts/` manages authoring, while `GET/PUT /api/posts/{id}/comment-automation/` remains editable after publish. AGENT can view state but backend and UI deny mutation.
- **Provider evidence:** Direct developer Pages docs returned HTTP 429. Meta's official Business SDK codegen current Page spec contains POST feed/photos and message/url/published/scheduled parameters. OrderHub intentionally schedules locally. Live v26 permissions, Page tasks, image fetch and private-reply behavior are not claimed.
- **Validation:** Ruff/format/migrations/Django checks pass. SQLite: **287 passed, 13 skipped**. Clean PostgreSQL 17 migration/full suite: **300 passed**; concurrency: **13 passed**. Frontend typecheck/lint/format, **16 unit tests**, build and Playwright **2 passed, 1 credential-gated skipped** pass. The first Playwright run timed out because the collapsed automation section was not opened; the test was corrected to exercise the visible user interaction and the complete suite passed.
- **Runtime:** Docker backend/Celery/beat rebuilt, `social.0005` applied, publishing tasks registered, migrate check and `/health/` pass. No live Meta credential or provider write was used.

### 2026-10-14 — New workspace UI backend integration

- Reorganized the active frontend into `components`, `features`, `layouts`, `lib`, `types` and `tests`, following the reference portal's separation without copying its business domain.
- Connected login/logout, company creation/switching, role-aware controls, account/platform/search filters, inbox read/poll/send, posts/comments/replies, authoring, automation and Facebook connection lifecycle to the existing tenant-scoped APIs.
- Preserved comment reply and Messenger idempotency keys, delivery-unknown UI, 24-hour eligibility, backend-only tokens and OWNER/ADMIN mutation rules. No backend model/provider change, Instagram, AI, order or payment feature was added.
- Frontend typecheck, 3 Vitest cases, production build and format check pass. Vite runtime `/health/` returned Django 200, unauthenticated `/api/auth/me/` returned the expected Django 403, and a deep SPA route returned 200. UI automation was unavailable for localhost because the browser surface rejected the URL, so no authenticated visual-flow claim is made.
- Backend SQLite regression: **287 passed, 13 PostgreSQL-only skipped**. Disposable PostgreSQL 17 full regression: **300 passed**. Ruff and Django checks pass; the temporary database was removed.

## Recommended Next Task

**Run one controlled development-Page acceptance for OrderHub publishing and the effective per-post automation rule.**

Restore one stable public HTTPS origin and Dashboard test assets, reconnect with `pages_manage_posts`, publish one harmless text post and one public-HTTPS-image post, then verify an enabled override wins, a disabled override blocks Page fallback, each eligible comment receives at most one public reply/private DM, and Messenger continuation still works. Record only redacted v26 response/error shapes; do not start AI or another provider until these provider writes are proven.
