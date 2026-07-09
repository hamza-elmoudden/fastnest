import base64
import hashlib
import hmac
import json
import os

PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> tuple[str, str]:
    """Hash a password with a fresh random salt. Returns (hash_hex, salt_hex)."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return digest.hex(), salt.hex()


def verify_password(password: str, password_hash: str, password_salt: str) -> bool:
    """Constant-time check that `password` matches a stored (hash, salt) pair."""
    salt = bytes.fromhex(password_salt)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return hmac.compare_digest(digest.hex(), password_hash)


def sign_jwt(payload: dict, secret: str) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    sig = base64.urlsafe_b64encode(
        hmac.new(secret.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{header}.{body}.{sig}"


def verify_jwt(token: str, secret: str):
    try:
        token = token.strip()
        header, body, sig = token.split(".")
        expected = base64.urlsafe_b64encode(
            hmac.new(secret.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
        ).rstrip(b"=").decode()
        if not hmac.compare_digest(sig, expected):
            return None
        pad = 4 - len(body) % 4
        return json.loads(base64.urlsafe_b64decode(body + "=" * pad))
    except Exception:
        return None
