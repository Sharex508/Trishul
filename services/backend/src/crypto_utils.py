import base64
import hashlib
from typing import Tuple
from cryptography.fernet import Fernet, InvalidToken
from .config import settings


def _fernet_from_secret(secret: str | None = None) -> Fernet:
    s = (secret or settings.SECRET_ENC_KEY).encode("utf-8")
    # Derive 32-byte key using SHA256, then urlsafe_b64encode for Fernet
    key = hashlib.sha256(s).digest()
    fkey = base64.urlsafe_b64encode(key)
    return Fernet(fkey)


def encrypt_pair(key_plain: str, secret_plain: str) -> Tuple[str, str]:
    f = _fernet_from_secret()
    return f.encrypt(key_plain.encode()).decode(), f.encrypt(secret_plain.encode()).decode()


def decrypt_pair(key_enc: str, secret_enc: str) -> Tuple[str, str]:
    f = _fernet_from_secret()
    try:
        k = f.decrypt(key_enc.encode()).decode()
        s = f.decrypt(secret_enc.encode()).decode()
        return k, s
    except InvalidToken:
        raise ValueError("Unable to decrypt stored credentials; check SECRET_ENC_KEY")


def mask_key(key_plain: str) -> str:
    if not key_plain:
        return ""
    if len(key_plain) <= 6:
        return "***"
    return key_plain[:3] + "***" + key_plain[-3:]
