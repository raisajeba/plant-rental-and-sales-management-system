"""Registration, login, logout."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    DUMMY_HASH,
    create_access_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.dependencies.auth import get_token_payload
from app.models import RevokedToken, Role, User
from app.schemas.auth import LoginRequest, MessageResponse, TokenResponse
from app.schemas.user import UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    # 1. Duplicate email check
    if db.scalar(select(User.id).where(User.email == payload.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email is already registered")

    # 2. Resolve the requested role (User / Nursery only, enforced by the schema)
    role = db.scalar(select(Role).where(Role.role_name == payload.role))
    if role is None or role.status != "active":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Selected role is not available")

    # 3. Hash BEFORE persisting
    user = User(
        name=payload.name,
        email=payload.email,
        password=hash_password(payload.password),
        role_id=role.id,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # two requests racing with the same email
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email is already registered")
    db.refresh(user)
    return user  # UserOut excludes password / hash


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))

    # Same error for unknown email and wrong password (no user enumeration)
    if user is None:
        verify_password(payload.password, DUMMY_HASH)  # equalize timing
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(payload.password, user.password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is not active")
    if user.role.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role is disabled")

    token, _ = create_access_token(user.id, user.role.role_name)
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/logout", response_model=MessageResponse)
def logout(payload: dict = Depends(get_token_payload), db: Session = Depends(get_db)):
    """Invalidate the current token. The frontend should also delete it locally
    and redirect to the login page."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)  # DB stores naive UTC
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc).replace(tzinfo=None)

    db.add(RevokedToken(jti=payload["jti"], expires_at=expires_at))
    db.execute(delete(RevokedToken).where(RevokedToken.expires_at < now))  # housekeeping
    try:
        db.commit()
    except IntegrityError:  # already revoked: logging out twice is harmless
        db.rollback()
    return MessageResponse(message="Logged out successfully")