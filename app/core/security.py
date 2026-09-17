import re
from typing import Any, Dict
from cryptography.fernet import Fernet
from app.core.config import settings

# Global or lazy-loaded Fernet cipher
_fernet_instance = None


def get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is None:
        key = settings.UDI_FERNET_KEY
        if isinstance(key, str):
            key = key.encode("utf-8")
        try:
            _fernet_instance = Fernet(key)
        except Exception:
            new_key = Fernet.generate_key()
            _fernet_instance = Fernet(new_key)
    return _fernet_instance


def encrypt_secret(secret_text: str) -> str:
    """Encrypts plaintext string with Fernet."""
    if not secret_text:
        return ""
    cipher = get_fernet()
    return cipher.encrypt(secret_text.encode("utf-8")).decode("utf-8")


def decrypt_secret(encrypted_text: str) -> str:
    """Decrypts encrypted string back to plaintext."""
    if not encrypted_text:
        return ""
    cipher = get_fernet()
    try:
        return cipher.decrypt(encrypted_text.encode("utf-8")).decode("utf-8")
    except Exception:
        # If decryption fails (e.g. key changed), return safe empty
        return ""


def mask_secret(secret: str, show_chars: int = 2) -> str:
    """Masks a secret string preserving only edge characters if long enough."""
    if not secret:
        return "********"
    if len(secret) <= show_chars:
        return "********"
    return f"{secret[:show_chars]}****{secret[-1]}"


def mask_connection_url(url: str) -> str:
    """Masks password embedded within connection URI string.
    Example: postgresql://user:my_secret_pass@localhost:5432/mydb -> postgresql://user:****@localhost:5432/mydb
    """
    if not url:
        return ""
    pattern = r"://([^:]+):([^@]+)@"
    return re.sub(pattern, r"://\1:****@", url)


def mask_dict_secrets(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively clones and masks keys that resemble passwords/tokens."""
    sensitive_keys = {"password", "secret", "token", "auth", "key", "credential", "conn_url"}
    sanitized = {}
    for k, v in data.items():
        if isinstance(v, dict):
            sanitized[k] = mask_dict_secrets(v)
        elif isinstance(v, str) and any(s in k.lower() for s in sensitive_keys):
            if "url" in k.lower():
                sanitized[k] = mask_connection_url(v)
            else:
                sanitized[k] = "********"
        else:
            sanitized[k] = v
    return sanitized
