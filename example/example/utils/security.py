import hashlib
import json
import base64
import hmac

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

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
        if sig != expected:
            return None
        pad = 4 - len(body) % 4
        return json.loads(base64.urlsafe_b64decode(body + "=" * pad))
    except Exception:
        return None