import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "apps.accounts",
    "apps.companies",
    "apps.meta",
    "apps.social",
    "apps.inbox",
]
MIDDLEWARE = [
    "apps.common.middleware.PrivateAPIMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
DATABASES = {"default": dj_database_url.parse(os.environ["DATABASE_URL"], conn_max_age=60)}
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql" and not os.getenv(
    "ORDERHUB_TESTING"
):
    raise ValueError("PostgreSQL is required outside isolated tests")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL}
}
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000").rstrip("/")
CSRF_TRUSTED_ORIGINS = [
    origin.rstrip("/")
    for origin in {
        FRONTEND_URL,
        BACKEND_PUBLIC_URL,
        *filter(None, os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")),
    }
]
CORS_ALLOWED_ORIGINS = [FRONTEND_URL]
CORS_ALLOW_CREDENTIALS = True
from corsheaders.defaults import default_headers  # noqa: E402

CORS_ALLOW_HEADERS = (*default_headers, "x-company-id")
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 86400
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_REFERRER_POLICY = "same-origin"
# Set only behind a trusted proxy that overwrites X-Forwarded-Proto.
if os.getenv("TRUST_PROXY", "false") == "true":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "mn"
TIME_ZONE = "Asia/Ulaanbaatar"
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user": "600/min",
        "anon": "60/min",
        "login": "10/min",
        "write": "30/min",
        "company": "120/min",
    },
    "EXCEPTION_HANDLER": "apps.common.errors.exception_handler",
}
SPECTACULAR_SETTINGS = {"TITLE": "OrderHub API", "VERSION": "1.0.0"}
META_GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v26.0")
META_APP_ID = os.getenv("META_APP_ID", "")
META_APP_SECRET = os.getenv("META_APP_SECRET", "")
META_WEBHOOK_VERIFY_TOKEN = os.getenv("META_WEBHOOK_VERIFY_TOKEN", "")
META_FACEBOOK_REDIRECT_URI = os.getenv(
    "META_FACEBOOK_REDIRECT_URI", BACKEND_PUBLIC_URL + "/api/meta/facebook/callback/"
)
TOKEN_ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY", "")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_TIME_LIMIT = 900
CELERY_BEAT_SCHEDULE = {
    # Slow reconciliation for posts/comments; Messenger messages arrive via webhook.
    "account-sync": {"task": "apps.meta.tasks.periodic_sync", "schedule": 60.0},
    "daily-maintenance": {"task": "apps.meta.tasks.daily_maintenance", "schedule": 86400.0},
    "pending-webhooks": {"task": "apps.meta.tasks.dispatch_webhooks", "schedule": 30.0},
    "pending-messages": {"task": "apps.inbox.tasks.dispatch_pending_messages", "schedule": 15.0},
    "pending-comment-automations": {
        "task": "apps.social.tasks.dispatch_pending_comment_automations",
        "schedule": 15.0,
    },
    "scheduled-social-posts": {
        "task": "apps.social.tasks.dispatch_scheduled_posts",
        "schedule": 15.0,
    },
}
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
# HTTP client debug logs can contain OAuth query credentials. Disable them.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "loggers": {
        name: {"handlers": ["null"], "propagate": False}
        for name in ["httpx", "httpcore", "django.server"]
    },
}
