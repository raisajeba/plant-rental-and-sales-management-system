"""Reusable FastAPI dependencies: authentication and role/page authorization."""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import RoleName, Status
from app.core.security import decode_access_token
from app.database import get_db
from app.models import Page, RevokedToken, RolePage, User

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> dict:
    """Validate the Bearer token (signature, expiry, not revoked)."""
    if credentials is None:
        raise _unauthorized("Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Token has expired")
    except jwt.PyJWTError:
        raise _unauthorized("Invalid authentication token")

    revoked = db.scalar(select(RevokedToken.id).where(RevokedToken.jti == payload["jti"]))
    if revoked:
        raise _unauthorized("Token has been revoked. Please log in again")
    return payload


def get_current_user(
    payload: dict = Depends(get_token_payload),
    db: Session = Depends(get_db),
) -> User:
    """Load the user from the token. The role is read from the DB (not the token),
    so role/status changes by an admin take effect immediately."""
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise _unauthorized("Invalid authentication token")

    user = db.get(User, user_id)
    if user is None:
        raise _unauthorized("User no longer exists")
    if user.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is not active")
    if user.role.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role is disabled")
    return user


def require_roles(*allowed_roles: RoleName):
    """Dependency factory.  Usage:
        Depends(require_roles(RoleName.ADMIN))
        Depends(require_roles(RoleName.NURSERY, RoleName.ADMIN))
    """
    allowed = {r.value for r in allowed_roles}

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.role_name not in allowed:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "You do not have permission to access this resource",
            )
        return current_user

    return checker


def require_page_access(page_url: str):
    """Fine-grained RBAC using the role_pages table.  Usage:
        Depends(require_page_access("/maintenance"))
    """

    def checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        allowed = db.scalar(
            select(RolePage.role_id)
            .join(Page, Page.id == RolePage.page_id)
            .where(
                RolePage.role_id == current_user.role_id,
                Page.page_url == page_url,
                Page.status == Status.ACTIVE.value,
            )
        )
        if allowed is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot access this page")
        return current_user

    return checker