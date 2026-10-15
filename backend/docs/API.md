# REST API

Browser зөвхөн Django API-тай харилцана. JSON, session cookie (`credentials: include`), unsafe method-д `X-CSRFToken`. Tenant endpoint-д `X-Company-ID` эсвэл сонгосон session company шаардлагатай. Membership шалгагдана.

| Method | Path | Зориулалт |
|---|---|---|
| GET | `/api/auth/csrf/` | CSRF cookie/token |
| POST | `/api/auth/login/` | `{username,password}`; session + шинэ csrfToken |
| POST | `/api/auth/logout/` | Session устгах |
| GET | `/api/auth/me/` | Хэрэглэгч, active_company |
| GET/POST | `/api/companies/` | Гишүүн компаниуд / `{name,slug}`-аар компани үүсгэх |
| GET | `/api/companies/{uuid}/` | Өөрийн компани |
| POST | `/api/companies/{uuid}/select/` | Active company сонгох |
| GET | `/api/meta/facebook/connect/` | OWNER/ADMIN; Meta OAuth redirect |
| GET | `/api/meta/facebook/callback/` | Нэг удаагийн state шалгаж server-side exchange |
| GET | `/api/meta/facebook/pages/` | Түр selection_id болон token-гүй Page сонголтууд |
| POST | `/api/meta/facebook/pages/` | `{selection_id,page_id}`; server candidate-оос resolve |
| GET | `/api/meta/accounts/` | Token-гүй connection list |
| GET/DELETE | `/api/meta/accounts/{uuid}/` | Connection / disconnect |
| POST | `/api/meta/accounts/{uuid}/sync/` | Feed + inbox queue; 202 |
| GET | `/api/meta/accounts/{uuid}/comment-automation/` | Гишүүн; тухайн Page-ийн static comment automation тохиргоо эсвэл default утга |
| PUT | `/api/meta/accounts/{uuid}/comment-automation/` | OWNER/ADMIN; `{is_enabled,public_reply_enabled,public_reply_text,private_reply_enabled,private_reply_text}` бүтнээр хадгална |
| GET | `/api/posts/` | `page`, `search`, `social_account`, `platform` filter; synced болон OrderHub-authored posts |
| POST | `/api/posts/` | OWNER/ADMIN; draft/save-now/schedule + optional nested per-post automation |
| POST | `/api/posts/sync/` | Active accounts sync queue; 202 |
| GET | `/api/posts/{uuid}/` | Локал post |
| PATCH/PUT | `/api/posts/{uuid}/` | OWNER/ADMIN; зөвхөн OrderHub DRAFT/SCHEDULED/FAILED content, media, schedule, automation засах |
| GET | `/api/posts/{uuid}/comment-automation/` | Post-specific override эсвэл JSON `null`; гишүүн уншина |
| PUT | `/api/posts/{uuid}/comment-automation/` | OWNER/ADMIN; published post дээр ч automation override үүсгэх/засах |
| GET | `/api/posts/{uuid}/comments/` | Хавтгай жагсаалт; parent_comment UUID-аар nested reply |
| GET | `/api/posts/{uuid}/reactions/` | `{total_count,items:[]}` |
| POST | `/api/comments/{uuid}/reply/` | `{message,idempotency_key}`; durable `SENT` / `FAILED` / `DELIVERY_UNKNOWN` attempt; 201 new, 200 existing/replay/unknown-comment block |
| GET | `/api/conversations/` | `page`, `search` |
| GET | `/api/conversations/{uuid}/` | Customer, preview, unread, can_reply |
| GET | `/api/conversations/{uuid}/messages/` | Newest-first message page |
| POST | `/api/conversations/{uuid}/read/` | Unread reset |
| POST | `/api/messages/send/` | `{conversation_id,text,idempotency_key}`; 201 pending / 200 давтагдсан хүсэлт |
| GET/POST | `/api/meta/webhook/` | Provider verification / signed event ingestion |

List response: `{count,next,previous,results}`, page size 25, `?page=2`. Provider cursor болон access token-ийг frontend-д дамжуулахгүй.

Safe error: `{code,message,details?}`. 400 validation, 403 auth/membership/CSRF, 404 tenant-аас гадуурх object, 429 local throttle, 502 provider error. Browser-д provider raw error message харуулахгүй. Message-ийн `error_code` нь local code.

Send key-ийг request timeout болсон ч ижил хүсэлт дээр дахин ашиглана. Амжилттай POST болгонд шинэ key үүсгэж давтан илгээж болохгүй. UI transport retry үед өмнөх key-ийг хадгалдаг; backend provider send-ийг asynchronous гүйцэтгэнэ. Comment-ийн `DELIVERY_UNKNOWN` attempt байвал шинэ key ч дахин provider write хийхгүй, Facebook дээр шалгах хүртэл тухайн comment-д 200 unknown attempt буцаана. Text 2000 тэмдэгт; comment 8000 тэмдэгт.

## OrderHub post publishing

`POST /api/posts/` болон editable post update body:

```json
{
  "social_account": "<Page account UUID>",
  "message": "Нийтлэлийн текст",
  "media": [{"type": "image", "url": "https://cdn.example/image.jpg"}],
  "publish_mode": "DRAFT | PUBLISH_NOW | SCHEDULE",
  "scheduled_at": "2026-10-15T09:00:00+08:00",
  "comment_automation": {
    "is_enabled": true,
    "public_reply_enabled": true,
    "public_reply_text": "Чатаа шалгаарай 😊",
    "private_reply_enabled": true,
    "private_reply_text": "Дэлгэрэнгүй мэдээллийг хүргэж байна."
  }
}
```

`comment_automation`-г орхивол тусдаа post rule үүсэхгүй, Page default-г ашиглана. Rule үүсгээд `is_enabled=false` бол энэ post дээр automation-г зориуд хааж, Page default руу fallback хийхгүй. V1 media нь нэг public HTTPS image URL эсвэл text-only байна; binary upload/storage ороогүй.

`PUBLISH_NOW` болон due `SCHEDULE` нь Celery worker-ээр нэг provider write хийнэ. Text-only нь `POST /{page-id}/feed`, нэг image URL нь `POST /{page-id}/photos`. Provider I/O-оос өмнө post `DELIVERY_UNKNOWN` болж claim хийгдэнэ: тодорхой success → `PUBLISHED`, clear rejection → `FAILED`, timeout/connection/malformed success → terminal `DELIVERY_UNKNOWN`. `FAILED` post-ийг засч дахин publish хүсэлт гаргаж болно; unknown post-ийг сохроор давтахгүй. Published/unknown content read-only, харин dedicated endpoint-оор comment automation-г засч болно.

## Сэтгэгдлийн автомат хариу

V1 нь зөвхөн Facebook Page-ийн webhook-оор орж ирсэн шинэ, устгагдаагүй, top-level customer comment-д ажиллана. Page өөрийн comment, nested reply, давтагдсан webhook, өмнө боловсруулсан comment автомат хариу үүсгэхгүй. Keyword, variable, AI байхгүй.

Effective rule resolution:

1. Post-specific rule record байвал enabled үед түүнийг ашиглана.
2. Post-specific rule record disabled бол тухайн post дээр юу ч хийхгүй.
3. Post-specific rule байхгүй бол enabled Page default-г ашиглана.
4. Аль нь ч enabled биш бол automation үүсэхгүй.

Action text attempt үүсэх мөчид snapshot хийгдэнэ. Rule edit нь зөвхөн дараагийн шинэ comment-д нөлөөлнө; өмнөх comment-ийн uniqueness/history-г reset хийхгүй. Facebook дээр шууд үүсгээд sync хийсэн post-д override байхгүй тул Page default ажиллана.

Webhook нь comment-ийг хадгалсны дараа public/private хоёр action-ийн текстийг durable attempt дээр snapshot хийгээд Celery task queue-д оруулна. Public reply нь одоогийн `CommentReplyAttempt`-ийг ашиглана; private DM нь `CommentPrivateReplyAttempt` байна. Хоёул `PENDING → SENT | FAILED | DELIVERY_UNKNOWN` төлөвтэй бөгөөд provider write эхлэхийн өмнө `DELIVERY_UNKNOWN` болгон claim хийдэг. Timeout, connection loss эсвэл malformed successful response гарвал дахин автоматаар илгээхгүй. Public failure нь private action-г, private failure нь public action-г rollback/skip хийхгүй.

Private write:

```http
POST /{comment-id}/private_replies
Authorization: Bearer <encrypted Page access token resolved server-side>
Content-Type: application/json

{"message":"static configured text"}
```

Provider ID нь non-empty `message_id` эсвэл `id` байвал success гэж хүлээн авна; бусад HTTP 2xx shape нь `DELIVERY_UNKNOWN`. Нэг comment-д нэг автомат public attempt болон нэг automatic private attempt гэсэн PostgreSQL uniqueness constraint бий. Хэрэглэгч private reply-д Messenger-ээр хариулбал шинэ subsystem үүсгэхгүй: одоогийн `Customer → Conversation → Message` webhook урсгал үргэлжлүүлнэ.
