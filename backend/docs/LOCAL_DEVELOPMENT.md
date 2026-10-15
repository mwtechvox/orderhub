# Локал хөгжүүлэлт

1. [Backend README](../README.md)-ийн `uv sync`, `init_env.py`, `docker compose up --build -d`, `create_owner` командыг ажиллуулна.
2. [Frontend README](../../frontend/README.md)-ийн `pnpm install`, `pnpm dev` ажиллуулна.
3. `http://localhost:3000/login` нээж, компаниа сонгоно.
4. Meta App ID/Secret болон permission/App Review-ийг [META_SETUP.md](META_SETUP.md)-ийн дагуу тохируулна.

## Meta туршилтын HTTPS tunnel

OAuth session cookie алдахгүйн тулд frontend болон callback-ийг **нэг origin**-оор ашиглана. Vite `/api/` ба `/health/` proxy аль хэдийн бий.

```bash
ngrok http 3000
```

Public origin-ийг жишээ нь `https://your-reserved-name.ngrok.app` гэж үзвэл:

```dotenv
# backend/.env
FRONTEND_URL=https://your-reserved-name.ngrok.app
BACKEND_PUBLIC_URL=https://your-reserved-name.ngrok.app
META_FACEBOOK_REDIRECT_URI=https://your-reserved-name.ngrok.app/api/meta/facebook/callback/
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,your-reserved-name.ngrok.app
# frontend/.env
VITE_BACKEND_PROXY_TARGET=http://localhost:8000
```

Backend containers болон Vite dev server-ээ restart хийнэ. Нэвтрэхдээ `localhost` биш **public HTTPS URL**-аа нээнэ. Meta Dashboard redirect нь дээрх callback, webhook нь `https://your-reserved-name.ngrok.app/api/meta/webhook/`. Verify token backend `.env`-тэй ижил. Public host солигдвол Dashboard болон env-ээ хамтад нь шинэчилнэ.

Tunnel зөвхөн local test. Production-д `DJANGO_DEBUG=false`, HTTPS termination, trusted proxy header sanitization, secure cookies, хүчтэй PostgreSQL/Redis credentials болон network isolation хэрэгтэй. Compose-ийн `orderhub` DB password нь зөвхөн local development-д зориулагдсан. Production secret manager ашиглана.

## PostgreSQL-ийг host test-д түр гаргах

Жишээ override (үндсэн Compose файлд DB port нээхгүй):

```yaml
services:
  postgres:
    ports: ["127.0.0.1:55439:5432"]
  redis:
    ports: ["127.0.0.1:56389:6379"]
```

```bash
docker compose -f docker-compose.yml -f /path/to/override.yml up -d
DATABASE_URL=postgresql://orderhub:orderhub@localhost:55439/orderhub uv run pytest
```

## Өгөгдөл ба worker

- Beat pending messages-ийг 15 секунд, webhook-ийг 30 секунд тутам шалгана.
- Account queue-ийг 60 секунд тутам шалгаж, account бүрийг 5 минутын зайтай reconcile хийнэ.
- Feed/comment болон conversation history эхний MVP-д бүрэн cursor pagination-аар уншигдана. Их history-тэй account-д урт ажиллах боломжтой; incremental watermark дараагийн сайжруулалт.
- Worker 900 секундийн hard limit-тэй. 20 минутаас удаан RUNNING sync-ийг дахин queue хийнэ. SENDING message-ийг автоматаар давтан илгээхгүй, delivery unknown FAILED болгоно.
- `.env`, `node_modules`, `.venv`, `dist`, тестийн cache-ууд Git-д орохгүй.
