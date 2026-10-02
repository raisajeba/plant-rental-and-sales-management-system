"""Profile view and update for the authenticated user."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.user import UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["Profile"])


@router.get("/me", response_model=UserOut)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Returns only the logged-in user's own data."""
    return current_user


@router.put("/me", response_model=UserOut)
def update_my_profile(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update name and/or email. Role and status can NOT be changed here."""
    if payload.email and payload.email != current_user.email:
        taken = db.scalar(
            select(User.id).where(User.email == payload.email, User.id != current_user.id)
        )
        if taken:
            raise HTTPException(status.HTTP_409_CONFLICT, "Email is already in use")
        current_user.email = payload.email

    if payload.name:
        current_user.name = payload.name

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email is already in use")
    db.refresh(current_user)
    return current_user