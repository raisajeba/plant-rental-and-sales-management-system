"""Profile view and update for the authenticated user."""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.user import UserOut

router = APIRouter(prefix="/users", tags=["Profile"])


# Folder where profile pictures will be stored
UPLOAD_DIR = Path("uploads/profile_images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Allowed image types
ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_PROFILE_IMAGE_SIZE = 5 * 1024 * 1024
EMAIL_ADAPTER = TypeAdapter(EmailStr)


@router.get("/me", response_model=UserOut)
def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    """Returns only the logged-in user's own data."""
    return current_user


@router.put("/me", response_model=UserOut)
async def update_my_profile(
    name: str | None = Form(default=None),
    email: str | None = Form(default=None),
    profile_image: UploadFile | None = File(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update the authenticated user's name, email and/or profile picture.

    Role and status cannot be changed here.
    """

    # Validate every supplied field before mutating the user or writing an image.
    if email is not None:
        email = email.strip()

        if not email:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Email cannot be empty",
            )

        try:
            email = str(EMAIL_ADAPTER.validate_python(email))
        except ValidationError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Enter a valid email address",
            )

    if name is not None:
        name = name.strip()

        if len(name) < 2:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Name must be at least 2 characters",
            )

        if len(name) > 100:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Name must not exceed 100 characters",
            )

    file_data = None
    if profile_image is not None:
        if profile_image.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only JPG, PNG and WEBP images are allowed",
            )

        file_data = await profile_image.read(MAX_PROFILE_IMAGE_SIZE + 1)
        if len(file_data) > MAX_PROFILE_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Profile picture must not exceed 5 MiB",
            )

    # -----------------------------------------
    # Update email
    # -----------------------------------------
    if email is not None:
        if email != current_user.email:
            taken = db.scalar(
                select(User.id).where(
                    User.email == email,
                    User.id != current_user.id,
                )
            )

            if taken:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email is already in use",
                )

            current_user.email = email

    # -----------------------------------------
    # Update name
    # -----------------------------------------
    if name is not None:
        current_user.name = name

    # -----------------------------------------
    # Update profile picture
    # -----------------------------------------
    if profile_image is not None:
        # Delete old profile picture if one exists
        if current_user.profile_image:
            old_file = Path(current_user.profile_image.lstrip("/"))

            if old_file.exists() and old_file.is_file():
                old_file.unlink()

        # Generate a unique filename
        extension = ALLOWED_CONTENT_TYPES[profile_image.content_type]
        filename = f"user_{current_user.id}_{uuid4().hex}{extension}"

        file_path = UPLOAD_DIR / filename

        # Save image
        file_path.write_bytes(file_data)

        # Save the URL/path in database
        current_user.profile_image = f"/uploads/profile_images/{filename}"

    # -----------------------------------------
    # Save changes
    # -----------------------------------------
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already in use",
        )

    db.refresh(current_user)

    return current_user