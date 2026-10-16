from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.constants import RoleName
from app.core.security import hash_password, verify_password
from app.database import Base, get_db
from app.models import Role, User
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.seed import seed_initial_data


@pytest.fixture
def admin_db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    with testing_session() as session:
        yield session
    engine.dispose()


@pytest.fixture
def admin_api(admin_db_session, monkeypatch):
    monkeypatch.setattr(
        settings, "SECRET_KEY", "test-admin-auth-secret-key-at-least-32-bytes"
    )
    roles = {role.value: Role(role_name=role.value) for role in RoleName}
    admin_db_session.add_all(roles.values())
    admin_db_session.flush()

    admin = User(
        name="Site Admin",
        email="admin@example.com",
        password=hash_password("AdminPassword123"),
        role_id=roles[RoleName.ADMIN.value].id,
    )
    customer = User(
        name="Test Customer",
        email="customer@example.com",
        password=hash_password("CustomerPassword123"),
        role_id=roles[RoleName.USER.value].id,
    )
    admin_db_session.add_all([admin, customer])
    admin_db_session.commit()

    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: admin_db_session

    with TestClient(app) as client:
        yield client, admin, customer, admin_db_session

    app.dependency_overrides.clear()


def test_admin_api_rejects_anonymous_and_non_admin_users(admin_api):
    client, _, customer, _ = admin_api

    assert client.get("/api/v1/admin/users").status_code == 401
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Self Registered Admin",
            "email": "self-admin@example.com",
            "password": "StrongPassword123",
            "role": "Admin",
        },
    )
    assert registration.status_code == 422

    response = client.post(
        "/api/v1/auth/login",
        json={"email": customer.email, "password": "CustomerPassword123"},
    )
    assert response.status_code == 200
    customer_token = response.json()["access_token"]
    denied = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert denied.status_code == 403


def test_admin_can_login_use_admin_api_and_revoke_token(admin_api):
    client, admin, _, _ = admin_api

    invalid = client.post(
        "/api/v1/auth/login",
        json={"email": admin.email, "password": "WrongPassword123"},
    )
    assert invalid.status_code == 401
    assert invalid.json()["detail"] == "Invalid email or password"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin.email, "password": "AdminPassword123"},
    )
    assert login.status_code == 200
    assert "password" not in login.json()["user"]
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/admin/users", headers=headers)
    assert response.status_code == 200
    assert {user["email"] for user in response.json()} == {
        "admin@example.com",
        "customer@example.com",
    }

    self_update = client.patch(
        f"/api/v1/admin/users/{admin.id}",
        headers=headers,
        json={"role_id": admin.role_id, "status": "inactive"},
    )
    assert self_update.status_code == 400

    logout = client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 200
    revoked_request = client.get("/api/v1/admin/users", headers=headers)
    assert revoked_request.status_code == 401
    assert revoked_request.json()["detail"] == (
        "Token has been revoked. Please log in again"
    )


def test_admin_bootstrap_is_hashed_idempotent_and_never_promotes(
    admin_db_session, monkeypatch
):
    monkeypatch.setattr(settings, "ADMIN_NAME", "First Admin")
    monkeypatch.setattr(settings, "ADMIN_EMAIL", "FIRST.ADMIN@example.com")
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", "StrongAdminPassword123")

    seed_initial_data(admin_db_session)
    admin_role = admin_db_session.scalar(
        select(Role).where(Role.role_name == RoleName.ADMIN.value)
    )
    admin = admin_db_session.scalar(
        select(User).where(User.email == "first.admin@example.com")
    )
    assert admin.role_id == admin_role.id
    assert admin.password != "StrongAdminPassword123"
    assert verify_password("StrongAdminPassword123", admin.password)

    seed_initial_data(admin_db_session)
    assert admin_db_session.scalar(
        select(User.id).where(User.email == "first.admin@example.com")
    ) == admin.id

    user_role = admin_db_session.scalar(
        select(Role).where(Role.role_name == RoleName.USER.value)
    )
    admin.role_id = user_role.id
    admin_db_session.commit()

    with pytest.raises(ValueError, match="already belongs to a non-admin account"):
        seed_initial_data(admin_db_session)

    admin_db_session.refresh(admin)
    assert admin.role_id == user_role.id
