"""Локал хөгжүүлэлтийн нууц түлхүүр үүсгэнэ. Байгаа .env файлыг өөрчлөхгүй."""

import secrets
from pathlib import Path

from cryptography.fernet import Fernet

root = Path(__file__).resolve().parents[1]
target = root / ".env"
if target.exists():
    raise SystemExit(".env байна; өөрчилсөнгүй.")
content = (
    (root / ".env.example")
    .read_text()
    .replace("replace-with-random-key", secrets.token_urlsafe(48))
)
content = content.replace(
    "TOKEN_ENCRYPTION_KEY=", "TOKEN_ENCRYPTION_KEY=" + Fernet.generate_key().decode()
)
content = content.replace(
    "META_WEBHOOK_VERIFY_TOKEN=", "META_WEBHOOK_VERIFY_TOKEN=" + secrets.token_urlsafe(32)
)
target.write_text(content)
target.chmod(0o600)
print(".env үүслээ. Meta App ID/Secret-ээ тохируулна уу.")
