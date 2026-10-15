# OrderHub backend

Python 3.12+, Django 5.2 LTS, DRF, PostgreSQL 17, Redis 7, Celery. Нэг modular monolith; `accounts`, `companies`, `meta`, `social`, `inbox` домэйнтэй.

## Эхлүүлэх

Repository root-оос:

```bash
cd backend
uv sync --frozen
uv run python scripts/init_env.py
docker compose up --build -d
docker compose exec backend python manage.py create_owner owner demo-shop --name "Миний дэлгүүр"
```

`create_owner` нууц үгийг терминалаас хоёр удаа авна. Нууц үгийг command line argument эсвэл Git-д хадгалахгүй. Migration service эхлээд бүх migration-ийг ажиллуулна; дараа нь Gunicorn, Celery worker, beat эхэлнэ. Backend: `http://localhost:8000`, health: `/health/`.

`uv` байхгүй бол Python 3.12 venv үүсгээд `pip install -r requirements.txt` ашиглаж болно. `scripts/init_env.py` байгаа `.env`-ийг өөрчлөхгүй. Энэ ажлын үеэр локал `.env` үүссэн бол шууд дараагийн командаас үргэлжлүүлнэ.

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
docker compose logs -f backend celery celery-beat
docker compose down
```

Superuser бол системийн оператор. Django admin-аас CompanyMembership үүсгэж өөр хэрэглэгчид OWNER/ADMIN/AGENT эрх өгнө. Бизнесийн өгөгдлийн admin нь зөвхөн superuser-д, read-only. OWNER хэрэглэгч Django admin-д нэвтрэх шаардлагагүй.

## Орчны тохиргоо

`.env.example` бүх хувьсагчийг агуулна:

| Хувьсагч | Утга |
|---|---|
| `DJANGO_SECRET_KEY` | Санамсаргүй нууц түлхүүр; init script үүсгэнэ |
| `TOKEN_ENCRYPTION_KEY` | Fernet key; init script үүсгэнэ, хадгалж хамгаална |
| `DATABASE_URL` | Compose: `postgresql://orderhub:orderhub@postgres:5432/orderhub` |
| `REDIS_URL` | `redis://redis:6379/0` |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/1` |
| `FRONTEND_URL` | Локал: `http://localhost:3000`; tunnel үед нийтийн HTTPS origin |
| `BACKEND_PUBLIC_URL` | OAuth/webhook-д харагдах origin; same-origin proxy үед frontend-тэй ижил |
| `DJANGO_ALLOWED_HOSTS` | Локал: `localhost,127.0.0.1`; public hostname-оо нэмнэ |
| `DJANGO_DEBUG` | Локал `true`; production заавал `false` |
| `META_GRAPH_VERSION` | Судалгааны default `v26.0` |
| `META_APP_ID`, `META_APP_SECRET` | Meta Dashboard-оос авах; backend-only |
| `META_WEBHOOK_VERIFY_TOKEN` | Өөрийн санамсаргүй утга; init script үүсгэнэ; Dashboard-д ижил утга оруулна |
| `META_FACEBOOK_REDIRECT_URI` | `https://<public-origin>/api/meta/facebook/callback/` |
| `TRUST_PROXY` | Зөвхөн trusted reverse proxy header-ийг өөрөө дарж тохируулдаг үед `true` |

Meta App ID/Secret-гүй үед нэвтрэлт болон локал өгөгдлийн UI ажиллана. Бодит Facebook connect/send-д [META_SETUP.md](docs/META_SETUP.md)-ийн ажиллагаа шаардлагатай.

## Тест ба lint

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Default тестүүд тусгаарласан memory SQLite ашиглана. Production/local app PostgreSQL шаардана. PostgreSQL integration тест:

```bash
DATABASE_URL=postgresql://orderhub:orderhub@localhost:55439/orderhub uv run pytest
```

Үүнд localhost дээр port нээсэн PostgreSQL instance хэрэгтэй; үндсэн Compose DB port-ийг нийтэд гаргахгүй. Python dependencies `uv.lock`, Docker dependencies `requirements.txt`-д pin хийгдсэн.

## DEMO, синк

```bash
docker compose exec backend python manage.py seed_demo demo-shop
docker compose exec backend python manage.py sync_meta_account <company-uuid> <account-uuid>
```

`seed_demo` зөвхөн харах sample үүсгэж, Page-ийг `DISCONNECTED` байлгана. Fake token, fake live delivery байхгүй. Бодит Facebook холбоход жинхэнэ account үүснэ. DEMO өгөгдлийг production-д бүү seed хий.

Дэлгэрэнгүй: [API](docs/API.md), [Security](docs/SECURITY.md), [Local](docs/LOCAL_DEVELOPMENT.md), [ялгаа](docs/DEVIATIONS.md).
