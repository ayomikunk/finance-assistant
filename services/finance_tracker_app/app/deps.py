import uuid

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_access_token

COOKIE_NAME = "access_token"


def _extract_token(authorization: str | None, cookie_token: str | None) -> str | None:
    if authorization:
        parts = authorization.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
    return cookie_token


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    access_token: str | None = Cookie(default=None),
) -> User:
    """Resolve the current user from a Bearer header or session cookie."""
    token = _extract_token(authorization, access_token)
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise unauthorized

    subject = decode_access_token(token)
    if not subject:
        raise unauthorized

    try:
        user_id = uuid.UUID(subject)
    except (ValueError, TypeError):
        raise unauthorized

    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user
