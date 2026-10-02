"""Password hashing (bcrypt) and JWT creation / decoding."""
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings

BCRYPT_MAX_BYTES = 72  # bcrypt ignores/rejects anything longer


def hash_password(plain_password: str) -> str:
    """Return a salted bcrypt hash. The plain password is never stored."""
    raw = plain_password.encode("utf-8")
    if len(raw) > BCRYPT_MAX_BYTES:
        raise ValueError("Password must be at most 72 bytes long")
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Constant-time check of a plain password against a stored hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


# Used to burn the same CPU time when the email doesn't exist,
# which prevents user enumeration through response timing.
DUMMY_HASH = hash_password("dummy-password-for-timing")


def create_access_token(user_id: int, role_name: str) -> tuple[str, datetime]:
    """Create a signed JWT. Returns (token, expiry datetime in UTC)."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "role": role_name,
        "jti": uuid.uuid4().hex,  # unique id, used for logout / revocation
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expires_at


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT. Raises jwt.PyJWTError subclasses on failure."""
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["exp", "sub", "jti"]},
    ) 