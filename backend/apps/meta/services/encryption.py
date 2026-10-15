from cryptography.fernet import Fernet
from django.conf import settings


class TokenCipher:
    def __init__(self):
        self.fernet = Fernet(settings.TOKEN_ENCRYPTION_KEY.encode())

    def encrypt(self, token: str) -> str:
        return self.fernet.encrypt(token.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        return self.fernet.decrypt(encrypted.encode()).decode()
