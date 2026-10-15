# Судалгаанаас ялгаа ба хязгаарлалт

`deep-research-report.md` өөрчлөгдөөгүй. Хэрэглэгчийн Facebook-first хүсэлт судалгааны өргөн scope-оос давуу.

1. `backend/` + `frontend/` нэг workspace; судалгааны `web/`, хоёр тусдаа Git repository гэсэн хувилбарыг хэрэглээгүй.
2. Instagram, mobile, catalog/orders, AI, QPay, eBarimt, delivery, accounting байхгүй. Хоосон fake provider байгуулаагүй.
3. Session/HttpOnly + CSRF auth. JWT refresh/register public endpoint байхгүй. Анхны OWNER `create_owner`, нэмэлт users/membership superuser admin-аар үүснэ.
4. Facebook webhook subscription-д `pages_manage_metadata` нэмсэн. Албан v26 docs HTTP 429/хандах боломжгүй байсан тул баталгаажуулалтын хязгаарлалтыг [META_SETUP.md](META_SETUP.md)-д бичсэн; version default v26.0 хэвээр.
5. Aggregate reactions хадгална. Individual reaction actor model байхгүй. Feed embedded comments биш тусдаа бүх comment/reply cursor pagination ашиглана.
6. Conversation webhook-д provider thread ID ирдэггүй тул түр `external_id=NULL`; account/customer unique constraint-ээр history sync-тэй нэгтгэнэ. Group conversations энэ MVP-д дэмжигдэхгүй.
7. Page-number REST pagination (25) ашигласан; Graph API cursor pagination бүрэн. Message API newest-first; browser тухайн хуудсыг chronological харуулна. DB timestamps UTC, UI Asia/Ulaanbaatar.
8. Comment reply нь synchronous, bounded timeout-той. Messenger reply нь durable PENDING + Celery. Ambiguous POST алдааг автоматаар retry хийхгүй; delivery unknown гэж ил тод тэмдэглэнэ. Энэ нь судалгааны бүх temporary POST-г retry хийх жишээг зассан.
9. Full history reconciliation 5 минут тутам; incremental sync watermark одоогоор байхгүй. Их history-тэй Page-уудын performance-ийг production onboarding-оос өмнө хэмжинэ.
10. Browser/company context session-д хадгалагдана. Same-origin Next proxy/tunnel ашиглаж OAuth session cookie-г хадгална; зөвхөн backend руу ngrok хийх жишээг өөрчилсөн.
11. Raw event account-аар хуваагдана; unknown event tenant NULL quarantine-д орно. Raw envelope хадгалдаг боловч normalized Post/Message дээр давхар provider raw JSON хадгалахгүй. PII болон нууц өгөгдөл давхардахыг багасгасан.
12. Token health daily, OAuth temporary cleanup daily, raw webhook retention 30 хоног. Facebook refresh-token урсгал зохиогоогүй.
13. Durable queue recovery pending rows-оос ажиллана; frontend 3–5 секунд polling. WebSocket, Kafka байхгүй.
14. Meta live credentials, Page ownership, permissions/App Review, privacy/deletion policy URL нийтлэх нь эзэмшигчийн ажиллагаа. Бодит Facebook end-to-end acceptance одоогоор батлагдаагүй.
15. Provider permission constraints-ээс хамаарч comment author/media байхгүй байж болно. UI “Facebook хэрэглэгч” гэж харуулна; actor identity зохиохгүй. Outbound нь зөвхөн text; inbound attachment link харуулна.
