import asyncio

import pytest
from fastapi import HTTPException

from app.models import Role, User
from app.routers.users import MAX_PROFILE_IMAGE_SIZE, update_my_profile


class FakeUpload:
    content_type = "image/png"

    def __init__(self, contents):
        self.contents = contents
        self.read_sizes = []

    async def read(self, size=-1):
        self.read_sizes.append(size)
        return self.contents[:size]


@pytest.fixture
def profile_user(db_session):
    user = User(
        name="Profile User",
        email="profile@example.com",
        password="hashed-password",
        role=Role(role_name="User"),
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_invalid_email_does_not_mutate_or_commit_profile(db_session, profile_user):
    upload = FakeUpload(b"should not be read")

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            update_my_profile(
                name="Changed Name",
                email="not-an-email",
                profile_image=upload,
                current_user=profile_user,
                db=db_session,
            )
        )

    assert error.value.status_code == 422
    assert profile_user.name == "Profile User"
    assert profile_user.email == "profile@example.com"
    assert upload.read_sizes == []
    db_session.expire_all()
    persisted_user = db_session.get(User, profile_user.id)
    assert persisted_user.name == "Profile User"
    assert persisted_user.email == "profile@example.com"


def test_profile_image_read_is_limited_to_maximum_plus_one(db_session, profile_user):
    upload = FakeUpload(b"x" * (MAX_PROFILE_IMAGE_SIZE + 100))

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            update_my_profile(
                name=None,
                email=None,
                profile_image=upload,
                current_user=profile_user,
                db=db_session,
            )
        )

    assert error.value.status_code == 400
    assert upload.read_sizes == [MAX_PROFILE_IMAGE_SIZE + 1]
    assert profile_user.profile_image is None
