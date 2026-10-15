# Аюулгүй байдал

## Tenant ба эрх

Бизнесийн model бүр Company FK-тай. `X-Company-ID` нь зөвхөн selector; сервер CompanyMembership-ийг шалгана. Header байхгүй бол session-ийн active company-г ашиглана. Read болон mutation query бүр company-аар шүүнэ. Worker-д object UUID-тай хамт company UUID дамжуулна. Webhook л баталгаажсан provider Page ID-аас account-ийг resolve хийнэ; нэг Page-ийг хоёр компани өөрсдийн эрхээр холбосон бол тус бүрд тусдаа event хадгална.

OWNER/ADMIN Facebook connect/select/reconnect/disconnect болон account/post manual sync удирдана. AGENT posts, comments, inbox харж, comment болон Messenger reply илгээнэ; integration удирдах API-г шууд дуудах үед 403 авна. Django admin нь системийн superuser-д зориулагдсан; ердийн staff business models-д хандахгүй. Raw webhook payload болон token талбар admin-д харагдахгүй.

## Session ба CSRF

Django DB session; HttpOnly session cookie; production Secure, SameSite=Lax. Login өөрөө CSRF-protected. Browser `/api/auth/csrf/`-ээс CSRF token авч unsafe хүсэлтдээ илгээнэ; login дараа rotated token шинэчилнэ. CSRF token нь Meta/auth credential биш. Logout POST. CORS зөвхөн FRONTEND_URL; wildcard биш. Session 24 цаг хүчинтэй. API response `Cache-Control: no-store`, `Referrer-Policy: no-referrer`.

Rate limit: login IP 10/min; authenticated 600/min; sensitive mutations user 30/min/company 120/min. Эдгээр нь app-ийн хамгаалалт; Meta quota гэж үзэхгүй. Shared Redis cache ашиглана. Reverse proxy-доо зөв клиент IP тохируулж нэмэлт perimeter rate limit хэрэгжүүлнэ.

## Token

Fernet key `.env`-д зөвхөн local/MVP. User access token зөвхөн exchange хийх хугацаанд memory-д байна. Page сонголтын бүх temporary payload шифрлэгдэж 10 минутад хүчинтэй байдлаа алдана; daily cleanup устгана. Page token шифрлэгдэж DB-д хадгалагдана. Serializer explicit allowlist-тай; ciphertext ч API-д гаргахгүй.

HTTP client debug logging болон query-string агуулдаг Django dev request log-ийг хаасан. Provider error-оос зөвхөн numeric code/subcode, шалгасан fbtrace_id хадгална. Provider message, request URL, response body-г error log/API-д дамжуулахгүй. Reverse proxy/APM-доо OAuth callback query string, Authorization, cookies, request body, local-variable capture-ийг redaction хийнэ. Production-д DEBUG=false заавал.

Production secret manager/KMS ашиглахыг зөвлөе. Fernet key-ийг алдах нь token сэргээх боломжгүй болгоно. Key rotation: worker/API write-ийг түр зогсоох → encrypted backup → хуучин түлхүүрээр decrypt, шинэ түлхүүрээр бүх SocialAccount/PageSelection утгыг transaction-аар re-encrypt → шинэ env key deploy → шалгах. Зөвхөн env key солих нь хуучин өгөгдлийг эвдэнэ. DB backup encryption болон хандалтын хяналт бас шаардлагатай.

## Webhook, idempotency, хүргэлт

Raw request bytes дээр App Secret HMAC-SHA256 шалгасны дараа JSON parse хийнэ. Canonical envelope + account-аар raw event dedupe, Page+provider message/comment ID-аар domain dedupe. Event processing transaction/row lock-той. Unknown data хадгалагдаж IGNORED болно; tenant нь тодорхойгүй event public API-д гардаггүй. Raw payload PII агуулж болдог тул 30 хоногийн retention-тэй, админд задлахгүй. DB болон backups-ийг encryption-at-rest хамгаалалттай байлгана.

Outbound idempotency key нь company хэмжээнд unique; ижил key өөр text/conversation-д 400 буцаана. Worker PENDING-ийг atomic compare/update-аар SENDING болгоно. SENT эсвэл SENDING дахин илгээхгүй. Explicit 429 rejection bounded retry-тэй; timeout/5xx зэрэг ambiguous outcome автоматаар retry хийхгүй. Worker тасарч upstream амжилттай явсан ч local SENT бичигдээгүй бол **exactly-once delivery батлах боломжгүй**. 20 минутад delivery unknown FAILED болж, оператор Messenger дээр шалгана. UI-д сохроор retry хийх товч байхгүй.

Disconnect local token-ийг устгаж pending message-ийг FAILED болгоно. Provider unsubscribe best effort; хүчингүй token үед Meta Dashboard-оос шалгана. Аль хэдийн provider руу явсан in-flight хүсэлтийг буцаахгүй. Түүхийг хадгална; data deletion нь тусдаа админы ажиллагаа.

## Өгөгдөл устгах

Privacy policy-д бодит байгууллагын устгах хүсэлт хүлээн авах холбоо барих хаяг өгнө. Хүсэгчийн эрхийг шалгаад холболтыг салгаж, супер админ Company-ийг устгавал FK cascade тухайн tenant-ийн posts/comments/customers/conversations/messages/events-ийг устгана. Бусад tenant-ийн data-г өөрчлөхгүй. Backup retention хугацаа болон Meta app deauthorization-ийг privacy policy-д тусгана. Автомат Meta data-deletion callback энэ MVP-д ороогүй; Dashboard-д deletion instructions URL ашиглана.
