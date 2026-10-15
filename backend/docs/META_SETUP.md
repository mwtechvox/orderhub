# Facebook хөгжүүлэлтийн Page — бодит холболтын заавар

Энэ заавар нь OrderHub-ийн Facebook-only урсгалыг өөрийн Meta development/test Page дээр шалгахад зориулагдсан. Token, App Secret, verify token, encryption key-г chat, issue, browser console, screenshot, Git-д бүү оруул.

## Одоогийн бодит байдал

**BLOCKED — USER META CONFIGURATION REQUIRED.** 2026-10-14-нд same-origin frontend tunnel-ээр `/health/`, `/api/meta/webhook/`, `/api/meta/facebook/callback/` Django-д хүрч буйг баталсан. Гэхдээ Meta Dashboard role/test Page/tester assets болон real OAuth consent одоогоор хийгдээгүй; бодит Graph request, Page subscription, comment reply, Messenger delivery-г батлаагүй.

OrderHub нь Graph API version-ийг `META_GRAPH_VERSION`-аас авдаг бөгөөд одоогийн тохиргоо `v26.0` байна. Энэ нь кодын pin болохоос тухайн өдрийн Meta-ийн дэмждэг хамгийн шинэ version гэдгийг батлах нотолгоо биш. Dashboard болон Graph API Explorer дээр туршилтын App/Page-ээр баталгаажуулсны дараа л өөрчилнө.

## CODEX CAN DO

- OAuth state-ийг хэрэглэгч, компани, server session-тэй холбож, 10 минутын дараа хүчингүй болгоно. State-г нэг удаа хэрэглэнэ.
- OAuth code-оос user token, long-lived user token авч, `/me/permissions` болон `/me/accounts`-аар Page choice үүсгэнэ. User token-г database-д хадгалахгүй.
- Сонгосон Page-ийн token болон түр Page choices-г Fernet-ээр шифрлэж, browser/API response-д token гаргахгүй.
- Сонгосон Page-д `subscribed_apps` edge-ээр webhook subscription хийж, локал post/comment/reaction/conversation/message read model-ийг sync хийнэ.
- Comment reply болон Messenger outbound-г server талд Page token-оор илгээнэ. Messenger-ийн 24 цагийн response window-г API, worker хоёул шалгана.
- OWNER/ADMIN нь Page бүрт static comment automation тохируулж болно. Шинэ eligible comment-д public reply болон `/{comment-id}/private_replies` private DM-ийг webhook request-ээс гадуур Celery-ээр тус тус нэг удаа оролдоно.
- OWNER/ADMIN нь OrderHub-с text-only эсвэл нэг public HTTPS image URL бүхий post-ийг draft хадгалах, локал хуваарьт оруулах, нийтлэх боломжтой. Post бүр Page default-г ашиглах эсвэл тусдаа static comment automation override-той байж болно.
- Webhook-ийн raw body-г HMAC SHA-256-аар шалгаж, durable event болгон хадгалж, idempotent processing хийнэ.
- Код, automated regression, локал Docker/Vite/Celery, мөн энэ зааврыг засаж чадна. Meta Dashboard role, App Review, Page ownership, consent, production publishing-г Code/CI автоматаар хийхгүй.

## I MUST DO IN META DEVELOPER DASHBOARD

1. [Meta for Developers](https://developers.facebook.com/) дээр өөрийн Business portfolio-д development App үүсгэнэ. Dashboard-ын нэршил use case-аас хамаарч өөрчлөгддөг; Facebook Login болон Pages/Messenger/Webhooks ашиглах боломжтой тохиргоог нэмнэ.
2. App-аа development mode-д үлдээнэ. Live mode руу бүү шилж; development mode-д зөвхөн App role-той хүмүүс болон тэдний test asset-уудыг ашиглана.
3. Өөрийн Facebook account-г **Roles** хэсэгт Admin, Developer, эсвэл Tester болгон нэмээд invitation-г тухайн account-аар зөвшөөрнө. Page-ийг удирдах account болон Messenger test customer account нь App role-ийн хүрээнд ажиллах ёстой.
4. Өөрийн удирддаг development/test Facebook Page сонгоно. Холбох account-д Page-ийн шаардлагатай task, ялангуяа Page access token авч Messenger-д хариулахад хэрэгтэй `MESSAGE` task байгаа эсэхийг шалгана.
5. App-ийн Facebook Login settings-д доорх **яг ижил** redirect URL-г **Valid OAuth Redirect URIs**-д оруулна. Scheme, host, path, trailing slash нь `.env`-ийн `META_FACEBOOK_REDIRECT_URI`-тай byte-for-byte ижил байна.

   ```text
   https://<public-orderhub-origin>/api/meta/facebook/callback/
   ```

6. Webhooks бүтээгдэхүүн/тохиргоонд Page object callback URL-г доорх байдлаар оруулна. Verify token нь backend-ийн `META_WEBHOOK_VERIFY_TOKEN`-ийн утга байна; энэ нууцыг Dashboard-аас гадуур бүү нийтэл.

   ```text
   https://<public-orderhub-origin>/api/meta/webhook/
   ```

7. Page object-д эдгээр field-үүдийг subscribe хийнэ: `messages`, `message_echoes`, `messaging_postbacks`, `feed`.
   - `messages`: customer-оос ирсэн Messenger message.
   - `message_echoes`: Page/Business Suite/OrderHub-с илгээсэн outbound echo.
   - `messaging_postbacks`: одоогийн код postback-г үл тоомсорлодог ч Page subscription-ийн одоогийн багцад байна.
   - `feed`: Page post/comment update-г sync hint болгоно.

   Dashboard callback verification нь Page subscription биш. OrderHub Page сонгосны дараа `POST /{page-id}/subscribed_apps` хийж тухайн Page-ийг app-д subscribe хийнэ.
8. Dashboard-ийн permission/access screen дээр development test-д дараах permission-ууд App role-той account-д grant болохыг шалгана. Production-д бусдын Page ашиглахын өмнө Meta шаардсан Advanced Access/App Review/Business Verification-г тусад нь хийнэ.
9. Privacy Policy, Terms болон user-data deletion callback/instructions шаардлагатай бол бодит HTTPS URL-уудыг байршуулж Dashboard-д оруулна. Энэ repository тэдгээр public policy URL-ыг байршуулдаггүй.

## Одоогийн кодын permission contract

OrderHub Page сонгохдоо дараах **найман** permission бүгд granted байхыг шаарддаг. `pages_manage_posts` нь OrderHub post publishing нэмэгдсэнээр шинээр шаардлагатай болсон. `business_management` кодод өмнө нь байсан. Бодит App/Page дээр permission бүрийн access level болон Page task-ийг Dashboard/Graph API Explorer-ээр батална.

| Permission | Кодын хэрэглээ / гар аргаар шалгах үйлдэл |
|---|---|
| `pages_show_list` | Connect хийсний дараа managed Page-ууд гарна. |
| `business_management` | Одоогийн OAuth selection policy шаарддаг; grant болохыг батална. |
| `pages_read_engagement` | Feed дээр post text, aggregate reaction/comment counts. |
| `pages_read_user_content` | Page-ийн visitor comments болон nested replies унших. |
| `pages_manage_engagement` | OrderHub-с comment reply илгээх. |
| `pages_manage_posts` | OrderHub-с Page feed/photo post нийтлэх. |
| `pages_messaging` | Messenger history/reply болон comment-triggered private reply-г Page access token-оор илгээх. |
| `pages_manage_metadata` | Page webhook subscription (`subscribed_apps`). |

Instagram permission, messaging tag, Human Agent window, order/payment permission бүү нэм.

### Page post publishing contract

OrderHub нь configurable Graph version болон encrypted Page token ашиглаж дараах write-уудын аль нэгийг нэг удаа хийдэг:

```text
Text only:       POST /{page-id}/feed   {message}
One image URL:   POST /{page-id}/photos {url, message}
```

2026-10-14-нд `developers.facebook.com` Pages reference нь `HTTP 429` өгсөн. Meta-ийн official Business SDK codegen дахь current `Page` spec-д `feed` ба `photos` POST edge, `message`, `url`, `published`, `scheduled_publish_time` параметрүүд хэвээр байгааг шалгасан. OrderHub Meta-side scheduling ашиглахгүй: draft/schedule-г локал database/Celery удирдаж, due үед шууд publish хийнэ. Ингэснээр publish болохоос өмнө content болон automation-г нэг transaction-safe local workflow-оор засна.

V1 image нь public HTTPS URL байна. Local binary upload, album/carousel/video байхгүй. Response-ийн non-empty `id`-г success гэж үзнэ. Timeout, connection loss, 5xx эсвэл malformed 2xx нь `DELIVERY_UNKNOWN`; automatic retry хийхгүй. Exact v26 live behavior, Page task болон `pages_manage_posts` access-г development Page дээр доорх checklist-ээр батална.

## Local болон public HTTPS тохиргоо

OAuth session cookie-г хадгалахын тулд callback/webhook-г backend-ийн тусдаа tunnel биш, **frontend-ийн same-origin HTTPS tunnel-аар** оруулахыг зөвлөе. Vite-ийн `/api/*` proxy нь request-ийг private Django backend руу дамжуулдаг. Browser эхлээд public frontend дээр login хийж cookie авна; OAuth callback мөн тэр host-ийн `/api/meta/facebook/callback/`-аар буцвал cookie ирнэ.

### Route map

| Хэрэглээ | Local URL | Public HTTPS URL |
|---|---|---|
| React/Vite frontend | `http://localhost:3000/` | `https://<public-orderhub-origin>/` |
| Django health | `http://localhost:8000/health/` | `https://<public-orderhub-origin>/health/` |
| Facebook OAuth callback | `http://localhost:8000/api/meta/facebook/callback/` | `https://<public-orderhub-origin>/api/meta/facebook/callback/` |
| Meta webhook GET/POST | `http://localhost:8000/api/meta/webhook/` | `https://<public-orderhub-origin>/api/meta/webhook/` |

`/api/*` болон `/health/*` нь Vite proxy-гоор Django руу дамжина. Webhook POST body-г browser code уншдаггүй; proxy нь Django-ийн signature validation-д шаардлагатай raw bytes-г шууд дамжуулна. GET webhook нь зөв verify parameter байхгүй үед Django-ээс `403` буцаах нь зөв бөгөөд frontend 404 биш гэдгийг нотолно.

1. Backend-ийг ажиллуулна:

   ```bash
   cd backend
   docker compose up --build -d
   docker compose logs -f backend celery celery-beat
   ```

2. Frontend-ийн `.env`-д private backend URL-г тохируулж frontend-ийг ажиллуулна:

   ```bash
   cd frontend
   cp .env.example .env
   # VITE_BACKEND_PROXY_TARGET=http://127.0.0.1:8000
   pnpm install
   pnpm dev
   ```

3. Frontend port 3000-ыг нэг HTTPS tunnel-аар гаргана. Аль нэгийг нь хэрэглэнэ:

   ```bash
   cloudflared tunnel --url http://127.0.0.1:3000
   # эсвэл
   ngrok http 3000
   ```

4. Tunnel-аас гарсан HTTPS origin-г `https://<public-orderhub-origin>` гэж нэрлээд `backend/.env`-д дараах Meta/Public утгуудыг оруулна. Temporary tunnel URL солигдвол бүгдийг шинэчилж, backend containers-ийг restart хийнэ.

   ```dotenv
   FRONTEND_URL=https://<public-orderhub-origin>
   BACKEND_PUBLIC_URL=https://<public-orderhub-origin>
   META_FACEBOOK_REDIRECT_URI=https://<public-orderhub-origin>/api/meta/facebook/callback/
   CSRF_TRUSTED_ORIGINS=http://localhost:3000
   TRUST_PROXY=true
   ```

   Эдгээр нь Meta Dashboard-д бүртгүүлэх хоёр URL-тай ижил байна. `FRONTEND_URL`-ийг localhost хэвээр үлдээвэл OAuth callback дээр session cookie ирэхгүй байж болно. `CSRF_TRUSTED_ORIGINS` нь comma-separated нэмэлт browser origin-уудын жагсаалт. Local Vite dev proxy нь `Origin: http://localhost:3000`-г Django руу дамжуулж болох тул энэ local origin-ийг public tunnel origin-той хамт trusted байлгана.

### Quick-tunnel URL солигдсон үед realtime Messenger сэргээх

`cloudflared tunnel --url ...`-ийн `trycloudflare.com` hostname нь түр зуурынх. Hostname солигдоход `.env`-ийг ганцааранг нь засахад хангалтгүй: Meta нь хуучин callback host руу webhook POST илгээсээр байх тул OrderHub шинэ inbound message авахгүй, харин **Синк** нь Graph API history-г татаж conversation-ийг хожим харуулна.

1. Шинэ public origin дээр `https://<public-orderhub-origin>/health/` нь `200` өгч байгааг шалгана.
2. Dashboard → **Webhooks** → **Page** дээр Callback URL-г яг `https://<public-orderhub-origin>/api/meta/webhook/` болгон солиод, одоо байгаа `META_WEBHOOK_VERIFY_TOKEN`-оор дахин **Verify and save** хийнэ.
3. `messages` болон `message_echoes` field-үүд сонгогдсон хэвээр байгааг шалгана. `feed` нь Page post/comment update-д, `messaging_postbacks` нь одоогийн subscription багцад хэрэгтэй.
4. Dashboard save амжилттай бол test customer-оос нэг шинэ Messenger message илгээнэ. Inbox page нээлттэй үед OrderHub 2 секунд тутам жагсаалт болон message-ийг refresh хийдэг тул шинэ conversation/message гарч ирэх ёстой. **Синк** дарах шаардлагагүй.

Dashboard callback verification амжилтгүй бол Meta inbound delivery огт эхлэхгүй. Quick tunnel-ийг дахин асаах бүрт энэ алхмыг давтахгүйн тулд real acceptance болон тогтмол хэрэглээнд reserved Cloudflare/ngrok hostname эсвэл тогтвортой HTTPS deployment ашиглана.

5. Meta-н нууц болон локал шаардлагатай бүх variable-г `backend/.env`-д л оруулна. Утгыг энд бичихгүй:

   | Variable | Хэн/юу бөглөх вэ |
   |---|---|
   | `DJANGO_SECRET_KEY` | Deployment secret. |
   | `DATABASE_URL`, `REDIS_URL` | Local Docker/default service тохиргоо. |
   | `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS` | Public host болон local host-уудыг зөвшөөрнө. |
   | `FRONTEND_URL`, `BACKEND_PUBLIC_URL`, `TRUST_PROXY` | Дээрх same-origin HTTPS tunnel/deployment тохиргоо. |
   | `META_GRAPH_VERSION` | Одоогийн pin `v26.0`; live contract баталгаажуулж байж солино. |
   | `META_APP_ID`, `META_APP_SECRET` | Meta Dashboard-ийн App settings. |
   | `META_WEBHOOK_VERIFY_TOKEN` | Өөрөө үүсгэсэн хүчтэй нууц; Dashboard webhook verifier-д оруулна. |
   | `META_FACEBOOK_REDIRECT_URI` | Dashboard-ийн Valid OAuth Redirect URI-тэй яг ижил URL. |
   | `TOKEN_ENCRYPTION_KEY` | Fernet key; Page token-г encrypt хийх backend-only key. |

6. `.env` өөрчилсний дараа backend/Celery/beat-г дахин үүсгэнэ:

   ```bash
   cd backend
   docker compose up --build -d
   ```

7. Dashboard-д URL хадгалахаас өмнө public origin-оор `/api/auth/csrf/` болон webhook verification ажиллаж байгааг шалгана. Meta verification хийхэд `GET /api/meta/webhook/?hub.mode=subscribe&hub.verify_token=…&hub.challenge=…` нь `200` болон challenge text буцаах ёстой. Verify token-г shell history, proxy log, screenshot-д бүү үлдээ; Dashboard-ийн built-in Verify action-г хэрэглэ.

## Official contract notes

Meta-ийн public developer pages-ийг 2026-10-14-нд нээх оролдлого rate-limited (`HTTP 429`) байсан тул бүх Pages/Webhooks endpoint contract-ыг тухайн сайтаас шууд дахин баталж чадсангүй. Кодыг documentation wording-оор өөрчлөөгүй.

Meta-ийн нийтэлсэн [Messenger Platform API Postman collection](https://www.postman.com/meta/messenger-platform-api/documentation/iyp204x/messenger-platform-api)-д `pages_messaging`, `MESSAGE` Page task, `POST /{page-id}/messages` + PSID recipient + `messaging_type=RESPONSE`, мөн ердийн 24-hour window-ийн шаардлага тодорхой байна. Энэ нь OrderHub-ийн Messenger send/window implementation-тэй нийцэж байна.

Live acceptance-ийн өмнө Dashboard/Graph API Explorer дээр дараахыг тухайн App-ийн сонгосон API version-тэй нь дахин шалгана: Facebook Login OAuth, `/me/accounts` Page discovery, Page access-token/tasks, `subscribed_apps`, feed/comment fields, `POST /{comment-id}/comments`, Page conversations/messages, Page webhook payload fields. Хэрэв бодит response contract өөр байвал redacted response shape болон smallest code change-ийг `PLANS.md`-д тэмдэглэнэ.

### Facebook comment private reply

OrderHub V1 дараах provider write-г configurable `META_GRAPH_VERSION` болон encrypted Page access token-оор хийдэг:

```http
POST https://graph.facebook.com/{META_GRAPH_VERSION}/{comment-id}/private_replies
{"message":"<static configured text>"}
```

Current official evidence-ийн хязгаар:

- Meta-ийн v26 official Business SDK codegen дахь `Comment` object нь `can_reply_privately` болон `private_reply_conversation` field-үүдийг хэвээр нийтэлж байна.
- Meta-ийн official Messenger Platform Postman collection нь Page access token, Page-ийн `MESSAGE` task болон `pages_messaging` permission шаарддагийг баталж байна.
- Харин `developers.facebook.com` дээрх private-replies reference-г 2026-10-14-нд шууд дахин нээхэд 404/429 өгсөн. Тиймээс exact v26 live endpoint response болон policy-г бодит development Page дээр батлахаас өмнө “live verified” гэж үзэхгүй.

OrderHub-ийн хамгаалалт нь өмнөх/currently published private-reply contract-ийн дараах хязгаарыг хамгийн консерватив байдлаар мөрдөнө:

- зөвхөн Page-owned post-ийн top-level customer comment;
- comment үүссэнээс хойш 7 хоногийн дотор нэг text-only private reply;
- нэг comment-д нэг private reply; database constraint нь давхар write-г хаана;
- `pages_messaging` бүхий Page token;
- success response-ийн non-empty `message_id` эсвэл `id`;
- customer хариулсны дараа л existing Messenger 24-hour reply window нээгдэнэ.

Эдгээрийн exact current Meta enforcement, provider error code/subcode, `id` эсвэл `message_id` response shape-г доорх test Page checklist-ээр redacted хэлбэрээр батална. Code default-аар automation **унтраалттай** тул live acceptance хийгдээгүй Page дээр provider action өөрөө эхлэхгүй.

## Гар аргын acceptance checklist

Доорх үйлдлүүд нь Meta дээр representational action (reply/send/subscription) хийдэг. Test Page, test customer, test comment ашиглаж, илгээхийн яг өмнө owner зөвшөөрөлтэй байна.

- [ ] Public same-origin HTTPS URL callback болон webhook verifier-д 200 өгч Dashboard дээр verify болсон.
- [ ] OrderHub owner/admin-оор public frontend дээр login хийсэн.
- [ ] **Connect Facebook** OAuth dialog нээгдсэн.
- [ ] Callback амжилттай болж managed Page-ууд харагдсан.
- [ ] Development Page-ийг сонгосон.
- [ ] Page token backend-д encrypted хэлбэрээр хадгалагдсан; UI/API/log дээр token гараагүй.
- [ ] Post sync хийж Page posts харагдсан.
- [ ] OrderHub дээр draft post болон per-post automation-г хадгалахад Meta write хийгдээгүй.
- [ ] Draft content/automation-г засч чадсан.
- [ ] Нэг text-only post болон нэг HTTPS image post OrderHub-с нийтлэгдэж Facebook дээр яг нэг удаа гарсан.
- [ ] Future local schedule due болохоос өмнө засагдаж, due үед яг нэг удаа нийтлэгдсэн.
- [ ] Published post content read-only боловч post-specific automation засагдсан.
- [ ] Post rule enabled үед Page default-аас түрүүлж, disabled override үед Page default ажиллаагүй.
- [ ] Post detail дээр comments харагдсан.
- [ ] Reaction aggregate count харагдсан.
- [ ] Test comment-д OrderHub-с reply илгээж Facebook дээр гарсныг баталсан.
- [ ] Холболтууд → Page → **Сэтгэгдлийн автомат хариу** дээр public/private static text тохируулж enable хийсэн.
- [ ] Test customer Page-ийн өөрийн post дээр шинэ top-level comment бичихэд public automatic reply Facebook дээр яг нэг удаа гарсан.
- [ ] Тухайн comment-оос private Messenger reply яг нэг удаа ирсэн; response ID shape болон redacted error/trace evidence тэмдэглэсэн.
- [ ] Ижил webhook/task-г давтахад public/private аль аль нь дахин илгээгдээгүй.
- [ ] Page-ийн өөрийн comment, automatic Page reply болон nested reply automation loop үүсгээгүй.
- [ ] Public action-г зориудаар clear failure болгоход private action тусдаа оролдсон; эсрэг тохиолдлыг мөн шалгасан.
- [ ] Timeout/connection-loss simulation `DELIVERY_UNKNOWN` болж automatic retry хийгээгүй.
- [ ] Customer private reply-д хариулахад existing OrderHub Inbox conversation/message урсгалд орсон.
- [ ] Test customer-ийн existing Messenger conversation/history inbox-д орсон.
- [ ] OrderHub reply Messenger дээр харагдсан.
- [ ] Test customer шинэ Messenger message илгээж webhook-оор inbox-д орсон.
- [ ] Нэг delivery-г дахин хүргэхэд local message давхардаагүй.
- [ ] Reconnect хийж permission/Page selection/subscription дахин амжилттай болсон.
- [ ] Disconnect хийж connection inactive болсон; sync/outbound дахин ажиллаагүй.

## Бодит туршилтын дараа тэмдэглэх зүйл

`PLANS.md`-д test хийсэн огноо, redacted App/Page test asset (нэр/ID/secret биш), Graph version, permission grant, callback verification, checklist-ийн үр дүн, response/payload contract mismatch, болон дараагийн **нэг** ажил л бичнэ. OAuth consent, comment reply, Messenger reply, webhook subscription нь гадаад системд нөлөөлөх үйлдэл тул хийсэн test action бүрийг test asset дээр л гүйцэтгэнэ.
