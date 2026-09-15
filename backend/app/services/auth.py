"""
Auth primitives: password hashing (bcrypt) and JWT creation/verification.

Scope note (MVP): this covers register/login with a single long-lived
access token. NOT included: refresh tokens, password reset, email
verification, rate limiting on login attempts. Fine for a personal
portfolio project with one user per account; a multi-user production app
would want all of those, especially rate limiting to slow brute-force
login attempts.

SECRET_KEY MUST be overridden via the JWT_SECRET_KEY env var in any real
deployment — the default here is only for local dev and is not a secret
worth protecting (it's committed to the repo).
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-only-insecure-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week — long-lived since there's no refresh flow


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Returns the user_id from a valid token, or None if invalid/expired."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
