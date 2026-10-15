import os

from cryptography.fernet import Fernet

os.environ["ORDERHUB_TESTING"] = "1"
os.environ.setdefault("DJANGO_SECRET_KEY", "isolated-test-key-not-for-deployment")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
from .settings import *  # noqa: E402,F403

DEBUG = False
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
TOKEN_ENCRYPTION_KEY = Fernet.generate_key().decode()
META_APP_SECRET = "test-app-secret"
META_APP_ID = "test-app"
META_WEBHOOK_VERIFY_TOKEN = "test-verify"
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
