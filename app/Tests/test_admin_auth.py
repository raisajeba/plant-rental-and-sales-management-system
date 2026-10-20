import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.constants import RoleName
from app.core.security import create_access_token, hash_password
from app.database import Base, get_db
from app.models import Role, User
from app.routers.admin import auth_router as admin_auth_router
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router


@pytest.fixture
def admin_test_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(bind=engine, expire_on_commit=False)
    db_session = test_session()

    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(admin_auth_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, db_session
    db_session.close()
    engine.dispose()


def test_admin_login_and_logout_revoke_access(admin_test_client):
    client, db_session = admin_test_client
    admin_role = Role(role_name=RoleName.ADMIN.value)
    db_session.add(admin_role)
    db_session.flush()
    db_session.add(
        User(
            name="Garden Admin",
            email="admin@example.com",
            password=hash_password("StrongPassword123"),
            role_id=admin_role.id,
        )
    )
    db_session.commit()

    login = client.post(
        "/api/v1/admin/login",
        json={"email": "admin@example.com", "password": "StrongPassword123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/v1/admin/users", headers=headers).status_code == 200
    logout = client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 200
    assert client.get("/api/v1/admin/users", headers=headers).status_code == 401
    bad_password = client.post(
        "/api/v1/admin/login",
        json={"email": "admin@example.com", "password": "WrongPassword123"},
    )
    assert bad_password.status_code == 401


def test_non_admin_cannot_login_or_access_admin_routes(admin_test_client):
    client, db_session = admin_test_client
    user_role = Role(role_name=RoleName.USER.value)
    admin_role = Role(role_name=RoleName.ADMIN.value)
    db_session.add_all([user_role, admin_role])
    db_session.flush()
    normal_user = User(
        name="Garden User",
        email="user@example.com",
        password=hash_password("StrongPassword123"),
        role_id=user_role.id,
    )
    db_session.add(normal_user)
    db_session.commit()

    login = client.post(
        "/api/v1/admin/login",
        json={"email": "user@example.com", "password": "StrongPassword123"},
    )
    assert login.status_code == 403

    token, _ = create_access_token(normal_user.id, RoleName.USER.value)
    response = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
