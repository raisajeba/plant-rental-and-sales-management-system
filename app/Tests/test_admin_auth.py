from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.constants import RoleName
from app.core.security import create_access_token, hash_password, verify_password
from app.database import Base, get_db
from app.models import Nursery, Role, User
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.nurseries import router as nurseries_router
from app.routers.users import router as users_router
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
    app.include_router(nurseries_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: admin_db_session

    with TestClient(app) as client:
        yield client, admin, customer, admin_db_session

    app.dependency_overrides.clear()


def test_admin_api_rejects_anonymous_and_non_admin_users(admin_api):
    client, _, customer, _ = admin_api

    assert client.get("/api/v1/admin/users").status_code == 401
    assert client.get("/api/v1/admin/users/1").status_code == 401
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
    denied_details = client.get(
        "/api/v1/admin/users/1",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert denied_details.status_code == 403


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


def test_admin_can_view_and_manage_accounts_and_inactive_users_are_blocked(admin_api):
    client, admin, customer, db_session = admin_api
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": admin.email, "password": "AdminPassword123"},
    )
    admin_headers = {
        "Authorization": f"Bearer {admin_login.json()['access_token']}"
    }
    customer_login = client.post(
        "/api/v1/auth/login",
        json={"email": customer.email, "password": "CustomerPassword123"},
    )
    customer_headers = {
        "Authorization": f"Bearer {customer_login.json()['access_token']}"
    }

    details = client.get(
        f"/api/v1/admin/users/{customer.id}", headers=admin_headers
    )
    assert details.status_code == 200
    assert details.json()["id"] == customer.id
    assert details.json()["name"] == customer.name
    assert details.json()["email"] == customer.email
    assert details.json()["role"]["role_name"] == "User"
    assert details.json()["status"] == "active"
    assert details.json()["created_at"]

    nursery_role = db_session.scalar(
        select(Role).where(Role.role_name == RoleName.NURSERY.value)
    )
    update = client.patch(
        f"/api/v1/admin/users/{customer.id}",
        headers=admin_headers,
        json={"role_id": nursery_role.id, "status": "inactive"},
    )
    assert update.status_code == 200
    assert update.json()["role"]["role_name"] == "Nursery"
    assert update.json()["status"] == "inactive"

    denied = client.get("/api/v1/users/me", headers=customer_headers)
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Account is not active"

    reactivate = client.patch(
        f"/api/v1/admin/users/{customer.id}",
        headers=admin_headers,
        json={"status": "active"},
    )
    assert reactivate.status_code == 200
    profile = client.get("/api/v1/users/me", headers=customer_headers)
    assert profile.status_code == 200
    assert profile.json()["role"]["role_name"] == "Nursery"

    missing = client.get("/api/v1/admin/users/99999", headers=admin_headers)
    assert missing.status_code == 404


def test_registration_waits_for_admin_approval_and_rejection_blocks_access(admin_api):
    client, admin, _, _ = admin_api
    pending_registration = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Pending Person",
            "email": "pending@example.com",
            "password": "PendingPassword123",
        },
    )
    rejected_registration = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Rejected Person",
            "email": "rejected@example.com",
            "password": "RejectedPassword123",
        },
    )
    assert pending_registration.status_code == 201
    assert pending_registration.json()["status"] == "inactive"
    assert pending_registration.json()["approval_status"] == "pending"
    pending_id = pending_registration.json()["id"]
    rejected_id = rejected_registration.json()["id"]

    pending_login = client.post(
        "/api/v1/auth/login",
        json={"email": "pending@example.com", "password": "PendingPassword123"},
    )
    assert pending_login.status_code == 403
    assert pending_login.json()["detail"] == "Account is not approved"

    pending_token, _ = create_access_token(pending_id, "User")
    protected_before_approval = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {pending_token}"},
    )
    assert protected_before_approval.status_code == 403

    assert client.get("/api/v1/admin/users/pending").status_code == 401
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": admin.email, "password": "AdminPassword123"},
    )
    admin_headers = {
        "Authorization": f"Bearer {admin_login.json()['access_token']}"
    }
    customer_login = client.post(
        "/api/v1/auth/login",
        json={"email": "customer@example.com", "password": "CustomerPassword123"},
    )
    customer_headers = {
        "Authorization": f"Bearer {customer_login.json()['access_token']}"
    }
    unauthorized_approval = client.post(
        f"/api/v1/admin/users/{pending_id}/approve",
        headers=customer_headers,
    )
    assert unauthorized_approval.status_code == 403
    assert client.get(
        "/api/v1/admin/users/pending", headers=customer_headers
    ).status_code == 403

    pending_list = client.get("/api/v1/admin/users/pending", headers=admin_headers)
    assert pending_list.status_code == 200
    assert {user["id"] for user in pending_list.json()} == {
        pending_id,
        rejected_id,
    }
    assert all(user["approval_status"] == "pending" for user in pending_list.json())

    approved = client.post(
        f"/api/v1/admin/users/{pending_id}/approve", headers=admin_headers
    )
    assert approved.status_code == 200
    assert approved.json()["approval_status"] == "approved"
    assert approved.json()["status"] == "active"
    assert [user["id"] for user in client.get(
        "/api/v1/admin/users/pending", headers=admin_headers
    ).json()] == [rejected_id]

    approved_login = client.post(
        "/api/v1/auth/login",
        json={"email": "pending@example.com", "password": "PendingPassword123"},
    )
    assert approved_login.status_code == 200
    approved_access = client.get(
        "/api/v1/users/me",
        headers={
            "Authorization": f"Bearer {approved_login.json()['access_token']}"
        },
    )
    assert approved_access.status_code == 200

    rejected = client.post(
        f"/api/v1/admin/users/{rejected_id}/reject", headers=admin_headers
    )
    assert rejected.status_code == 200
    assert rejected.json()["approval_status"] == "rejected"
    assert rejected.json()["status"] == "inactive"
    rejected_token, _ = create_access_token(rejected_id, "User")
    rejected_access = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {rejected_token}"},
    )
    assert rejected_access.status_code == 403
    assert rejected_access.json()["detail"] == "Account is not approved"
    rejected_login = client.post(
        "/api/v1/auth/login",
        json={"email": "rejected@example.com", "password": "RejectedPassword123"},
    )
    assert rejected_login.status_code == 403

    repeated_approval = client.post(
        f"/api/v1/admin/users/{rejected_id}/approve", headers=admin_headers
    )
    assert repeated_approval.status_code == 409
    assert client.get(
        "/api/v1/admin/users/pending", headers=admin_headers
    ).json() == []


def test_admin_can_list_view_and_update_nursery_status(admin_api):
    client, admin, customer, db_session = admin_api
    nursery = Nursery(
        owner_id=customer.id,
        name="Customer Nursery",
        description="A nursery account",
        address="12 Garden Road",
        city="Dhaka",
        phone="+8801712345678",
        email="nursery@example.com",
    )
    db_session.add(nursery)
    db_session.commit()

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": admin.email, "password": "AdminPassword123"},
    )
    admin_headers = {
        "Authorization": f"Bearer {admin_login.json()['access_token']}"
    }
    customer_login = client.post(
        "/api/v1/auth/login",
        json={"email": customer.email, "password": "CustomerPassword123"},
    )
    customer_headers = {
        "Authorization": f"Bearer {customer_login.json()['access_token']}"
    }

    assert client.get("/api/v1/admin/nurseries").status_code == 401
    assert client.get("/api/v1/admin/nurseries/1").status_code == 401
    assert client.patch(
        "/api/v1/admin/nurseries/1",
        json={"status": "inactive"},
    ).status_code == 401
    assert client.get(
        "/api/v1/admin/nurseries", headers=customer_headers
    ).status_code == 403
    assert client.get(
        "/api/v1/admin/nurseries/1", headers=customer_headers
    ).status_code == 403
    assert client.patch(
        "/api/v1/admin/nurseries/1",
        headers=customer_headers,
        json={"status": "inactive"},
    ).status_code == 403

    listed = client.get("/api/v1/admin/nurseries", headers=admin_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == nursery.id
    assert listed.json()[0]["name"] == "Customer Nursery"
    assert listed.json()[0]["status"] == "active"
    assert listed.json()[0]["owner"]["email"] == customer.email
    assert listed.json()[0]["created_at"]

    details = client.get(
        f"/api/v1/admin/nurseries/{nursery.id}", headers=admin_headers
    )
    assert details.status_code == 200
    assert details.json()["address"] == "12 Garden Road"
    assert details.json()["owner"]["id"] == customer.id

    updated = client.patch(
        f"/api/v1/admin/nurseries/{nursery.id}",
        headers=admin_headers,
        json={"status": "inactive"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "inactive"
    db_session.refresh(nursery)
    assert nursery.status == "inactive"
    assert client.get(
        f"/api/v1/nurseries/{nursery.id}", headers=customer_headers
    ).status_code == 404

    invalid_status = client.patch(
        f"/api/v1/admin/nurseries/{nursery.id}",
        headers=admin_headers,
        json={"status": "suspended"},
    )
    assert invalid_status.status_code == 422
    missing = client.get("/api/v1/admin/nurseries/99999", headers=admin_headers)
    assert missing.status_code == 404
    missing_update = client.patch(
        "/api/v1/admin/nurseries/99999",
        headers=admin_headers,
        json={"status": "active"},
    )
    assert missing_update.status_code == 404


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
