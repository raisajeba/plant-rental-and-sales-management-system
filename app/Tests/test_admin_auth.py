import pytest
from datetime import date, timedelta
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.constants import RoleName
from app.core.security import create_access_token, hash_password
from app.database import Base, get_db
from app.models import (
    MaintenanceRequest,
    MaintenanceSchedule,
    Nursery,
    Order,
    Plant,
    PlantRentalOrder,
    PurchaseOrder,
    RentalOrder,
    Role,
    User,
)
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


def test_admin_can_monitor_orders_and_maintenance(admin_test_client):
    client, db_session = admin_test_client
    admin_role = Role(role_name=RoleName.ADMIN.value)
    user_role = Role(role_name=RoleName.USER.value)
    nursery_role = Role(role_name=RoleName.NURSERY.value)
    db_session.add_all([admin_role, user_role, nursery_role])
    db_session.flush()

    admin_user = User(
        name="Order Admin",
        email="orders-admin@example.com",
        password=hash_password("StrongPassword123"),
        role_id=admin_role.id,
    )
    customer = User(
        name="Order Customer",
        email="orders-customer@example.com",
        password=hash_password("StrongPassword123"),
        role_id=user_role.id,
    )
    owner = User(
        name="Order Nursery Owner",
        email="orders-owner@example.com",
        password=hash_password("StrongPassword123"),
        role_id=nursery_role.id,
    )
    db_session.add_all([admin_user, customer, owner])
    db_session.flush()

    nursery = Nursery(
        owner_id=owner.id,
        name="Order Nursery",
        address="12 Garden Road",
        city="Dhaka",
        phone="0123456789",
    )
    db_session.add(nursery)
    db_session.flush()
    plant = Plant(
        nursery_id=nursery.id,
        name="Admin Test Fern",
        category="Indoor",
        buy_price=25,
        rent_price=5,
        available_quantity=4,
        availability_status="available_for_both",
    )
    db_session.add(plant)
    db_session.flush()

    purchase = PurchaseOrder(
        user_id=customer.id,
        plant_id=plant.id,
        quantity=1,
        total_amount=25,
    )
    checkout = Order(user_id=customer.id, total_amount=25)
    rental = PlantRentalOrder(
        user_id=customer.id,
        plant_id=plant.id,
        quantity=1,
        rental_start_date=date.today() + timedelta(days=1),
        rental_end_date=date.today() + timedelta(days=2),
        rental_duration_days=2,
        rental_price_per_day=5,
        total_amount=10,
    )
    schedule = MaintenanceSchedule(
        user_id=customer.id,
        plant_name=plant.name,
        task_type="watering",
        instructions="Water the plant.",
        due_date=date.today(),
    )
    request = MaintenanceRequest(
        user_id=customer.id,
        plant_name=plant.name,
        request_type="watering",
        description="Please water and inspect the plant.",
    )
    db_session.add_all([purchase, checkout, rental, schedule, request])
    db_session.add(
        RentalOrder(
            user_id=customer.id,
            plant_id=plant.id,
            quantity=1,
            rental_months=1,
            total_amount=5,
        )
    )
    db_session.commit()

    login = client.post(
        "/api/v1/admin/login",
        json={"email": "orders-admin@example.com", "password": "StrongPassword123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    assert client.get("/api/v1/admin/orders", headers=headers).status_code == 200
    assert client.get("/api/v1/admin/purchase-orders", headers=headers).json()[0]["order_id"] == purchase.order_id
    assert client.get("/api/v1/admin/rental-orders", headers=headers).json()[0]["rental_id"] == rental.rental_id
    assert client.get("/api/v1/admin/legacy-rental-orders", headers=headers).status_code == 200
    assert client.get("/api/v1/admin/maintenance/schedules", headers=headers).status_code == 200
    assert client.get("/api/v1/admin/maintenance/requests", headers=headers).status_code == 200

    assert client.patch(
        f"/api/v1/admin/purchase-orders/{purchase.order_id}/status",
        json={"status": "Confirmed"},
        headers=headers,
    ).json()["order_status"] == "Confirmed"
    assert client.patch(
        f"/api/v1/admin/rental-orders/{rental.rental_id}/status",
        json={"status": "Approved"},
        headers=headers,
    ).json()["status"] == "Approved"
    assert client.patch(
        f"/api/v1/admin/maintenance/schedules/{schedule.id}",
        json={"status": "completed"},
        headers=headers,
    ).json()["status"] == "completed"
    assert client.patch(
        f"/api/v1/admin/maintenance/requests/{request.id}",
        json={"status": "in_progress", "response_note": "Work started."},
        headers=headers,
    ).json()["status"] == "in_progress"

    assert client.patch(
        "/api/v1/admin/purchase-orders/99999/status",
        json={"status": "Confirmed"},
        headers=headers,
    ).status_code == 404
    assert client.patch(
        f"/api/v1/admin/rental-orders/{rental.rental_id}/status",
        json={"status": "unknown"},
        headers=headers,
    ).status_code == 422

    user_token, _ = create_access_token(customer.id, RoleName.USER.value)
    assert client.get(
        "/api/v1/admin/maintenance/requests",
        headers={"Authorization": f"Bearer {user_token}"},
    ).status_code == 403


def test_admin_can_filter_and_approve_users(admin_test_client):
    client, db_session = admin_test_client
    admin_role = Role(role_name=RoleName.ADMIN.value)
    user_role = Role(role_name=RoleName.USER.value)
    db_session.add_all([admin_role, user_role])
    db_session.flush()

    admin_user = User(
        name="Garden Admin",
        email="admin@example.com",
        password=hash_password("StrongPassword123"),
        role_id=admin_role.id,
        status="active",
    )
    pending_user = User(
        name="New Grower",
        email="grower@example.com",
        password=hash_password("StrongPassword123"),
        role_id=user_role.id,
        status="inactive",
    )
    db_session.add_all([admin_user, pending_user])
    db_session.commit()

    login = client.post(
        "/api/v1/admin/login",
        json={"email": "admin@example.com", "password": "StrongPassword123"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    filtered = client.get("/api/v1/admin/users?status=inactive", headers=headers)
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1
    assert filtered.json()[0]["email"] == "grower@example.com"

    approve = client.post(f"/api/v1/admin/users/{pending_user.id}/approve", headers=headers)
    assert approve.status_code == 200
    assert approve.json()["status"] == "active"

    active_users = client.get("/api/v1/admin/users?status=active", headers=headers)
    assert active_users.status_code == 200
    emails = {user["email"] for user in active_users.json()}
    assert {"admin@example.com", "grower@example.com"}.issubset(emails)


def test_admin_can_manage_nurseries_and_plant_catalog(admin_test_client):
    client, db_session = admin_test_client
    admin_role = Role(role_name=RoleName.ADMIN.value)
    nursery_role = Role(role_name=RoleName.NURSERY.value)
    db_session.add_all([admin_role, nursery_role])
    db_session.flush()

    admin_user = User(
        name="Garden Admin",
        email="admin2@example.com",
        password=hash_password("StrongPassword123"),
        role_id=admin_role.id,
        status="active",
    )
    db_session.add(admin_user)
    db_session.flush()

    login = client.post(
        "/api/v1/admin/login",
        json={"email": "admin2@example.com", "password": "StrongPassword123"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    nursery_user = User(
        name="Nursery Owner",
        email="nursery@example.com",
        password=hash_password("StrongPassword123"),
        role_id=nursery_role.id,
        status="active",
    )
    db_session.add(nursery_user)
    db_session.commit()

    nursery = Nursery(
        owner_id=nursery_user.id,
        name="Sunrise Plants",
        description="A test nursery",
        address="12 Garden Road",
        city="Dhaka",
        phone="+8801712345678",
        email="nursery@example.com",
        status="inactive",
    )
    db_session.add(nursery)
    db_session.flush()

    plant = Plant(
        nursery_id=nursery.id,
        name="Monstera",
        category="Indoor",
        size="Medium",
        buy_price=150,
        rent_price=40,
        available_quantity=12,
        availability_status="unavailable",
    )
    db_session.add(plant)
    db_session.commit()

    nursery_list = client.get("/api/v1/admin/nurseries?status=inactive", headers=headers)
    assert nursery_list.status_code == 200
    assert any(item["id"] == nursery.id for item in nursery_list.json())

    approve_nursery = client.post(f"/api/v1/admin/nurseries/{nursery.id}/approve", headers=headers)
    assert approve_nursery.status_code == 200
    assert approve_nursery.json()["status"] == "active"

    plant_list = client.get("/api/v1/admin/plants?status=unavailable", headers=headers)
    assert plant_list.status_code == 200
    assert any(item["id"] == plant.id for item in plant_list.json())

    approve_plant = client.post(f"/api/v1/admin/plants/{plant.id}/approve", headers=headers)
    assert approve_plant.status_code == 200
    assert approve_plant.json()["availability_status"] in {"available_for_sale", "available_for_rent", "available_for_both"}
