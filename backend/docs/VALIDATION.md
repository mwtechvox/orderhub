# Баталгаажуулалт

2026-10-13, Asia/Ulaanbaatar. Mac host, Python 3.12.14, Django 5.2.18, PostgreSQL 17 Docker, Next.js 16.4.0.

| Шалгалт | Үр дүн |
|---|---|
| PostgreSQL `uv run pytest` | **51 passed**; жинхэнэ row-lock/concurrent request/worker тестүүд орсон |
| Тусгаарласан SQLite `uv run pytest` | **49 passed, 2 skipped**; хоёр PostgreSQL concurrency тест зориудаар skip |
| Ruff lint | PASS |
| Ruff format | PASS, 90 Python файл |
| Django `check` | No issues |
| `makemigrations --check --dry-run` | No changes detected |
| Empty PostgreSQL migrations | PASS, бүх migration дарааллаар хэрэглэсэн |
| Next TypeScript typecheck | PASS |
| ESLint | PASS |
| Prettier | PASS |
| Vitest | **8 passed** |
| Next production build | PASS; login/inbox/posts/post detail/integrations routes |
| Chrome mocked workflow | PASS: яриа сонгох, send, pending bubble, post comment reply, Page сонголт, 390px mobile overflow шалгалт |
| Chrome live Django workflow | PASS: same-origin Next proxy → CSRF login → HttpOnly cookie → integrations → logout |
| Docker Compose config | PASS |
| Backend Docker image build | PASS |
| PostgreSQL / Redis / Gunicorn / Celery / Beat | Бүгд ажиллаж байгааг шалгасан; PostgreSQL, Redis healthy |
| `/health/` | HTTP 200, `{"ok":true}` |
| Beat → Redis → worker | Pending messages/webhooks/account sync dispatcher tasks амжилттай ажилласан |
| Desktop/mobile visual inspection | Inbox, post detail, login layout шалгасан |

Live browser шалгалт түр үүсгэсэн account/нууц үг ашигласан; шалгалтын дараа account болон temporary credential file-ийг устгасан. Source-д бодит Meta secret/token байхгүй. Локал `backend/.env` random app/encryption/verify key-тэй, `.gitignore` ба `.dockerignore`-д хасагдсан. Meta App ID/Secret хоосон.

## Хязгаарлалт

Бодит Meta OAuth approval, Page token, Graph v26 field availability, live webhook delivery, Facebook comment reply болон Messenger хүргэлтийг баталгаажуулаагүй. Automated provider тестүүд HTTP mock ашигладаг. Үүнийг [META_SETUP.md](META_SETUP.md)-ийн Dashboard тохиргоо болон бодит Page acceptance шалгалтаар гүйцээнэ. Meta official documentation fetch нь 429/access error өгсөн.

## Дахин ажиллуулах

Backend: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`. PostgreSQL URL тохируулбал хоёр concurrency тест мөн ажиллана.

Frontend: `npm run typecheck`, `npm run lint`, `npm test`, `npm run format:check`, `npm run build`, `npm run test:e2e`.

Ердийн E2E run нь live-auth тестийг skip хийнэ. Django ажиллаж байгаа үед `ORDERHUB_SMOKE_CREDENTIALS=/absolute/path/to/local-credentials.json npm run test:e2e` гэж өгвөл live-auth ажиллана. Local file нь `{"username":"...","password":"..."}` бүтэцтэй, chmod 600, Git-д орохгүй байхаар байрлуулна. Зөвхөн тусгай test account ашиглаж, дараа нь файл болон account-ийг устгана. Playwright failure artifacts нууц үг агуулж болдог тул public CI artifact болгож upload хийхгүй.
