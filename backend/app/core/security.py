import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    """Sign a JWT. ``iat`` is a float so a token minted right after a password change
    is distinguishable from one minted just before it (see ``password_changed_at``)."""
    payload = data.copy()
    now = datetime.now(timezone.utc)
    payload.update({"exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), "iat": now.timestamp()})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def hash_token(raw: str) -> str:
    """SHA-256 of a high-entropy random token. Fast hashing is correct here: the input
    is 256 random bits, not a human password, so there is nothing to brute-force."""
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_token() -> tuple[str, str]:
    """Return ``(raw, hash)``. Email the raw value; store only the hash."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)
