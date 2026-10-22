from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.constants import AvailabilityStatus
from app.database import Base, get_db
from app.dependencies.auth import get_current_user
from app.models import (
    Nursery,
    Order,
    OrderItem,
    Plant,
    PlantRentalOrder,
    RentalOrder,
    Role,
    User,
)
from app.routers.order import list_my_orders, router


@pytest.fixture
def order_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    user_role = Role(role_name="User")
    nursery_role = Role(role_name="Nursery")
    customer = User(
        name="Customer One",
        email="customer.one@example.com",
        password="hashed",
        role=user_role,
    )
    other_customer = User(
        name="Customer Two",
        email="customer.two@example.com",
        password="hashed",
        role=user_role,
    )
    owner = User(
        name="Nursery Owner",
        email="owner@example.com",
        password="hashed",
        role=nursery_role,
    )
    nursery = Nursery(
        owner=owner,
        name="Test Nursery",
        address="12 Garden Road",
        city="Dhaka",
        phone="0123456789",
    )
    plant = Plant(
        nursery=nursery,
        name="Monstera",
        category="Indoor",
        buy_price=20,
        rent_price=5,
        available_quantity=8,
        availability_status=AvailabilityStatus.FOR_BOTH.value,
    )
    def override_get_db():
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: customer

    with testing_session() as db_session:
        db_session.add_all([customer, other_customer, owner, plant])
        db_session.flush()
        purchase = Order(
            user_id=customer.id,
            total_amount=40,
            status="Pending",
            created_at=datetime(2026, 1, 1),
            items=[
                OrderItem(
                    plant_id=plant.id,
                    quantity=2,
                    unit_price=20,
                    total_price=40,
                )
            ],
        )
        another_users_order = Order(
            user_id=other_customer.id,
            total_amount=20,
            status="Pending",
            items=[
                OrderItem(
                    plant_id=plant.id,
                    quantity=1,
                    unit_price=20,
                    total_price=20,
                )
            ],
        )
        rental = RentalOrder(
            user_id=customer.id,
            plant_id=plant.id,
            quantity=2,
            rental_months=3,
            total_amount=30,
            status="Pending",
        )
        db_session.add_all([purchase, another_users_order, rental])
        db_session.commit()
        ids = (purchase.id, rental.id, another_users_order.id, plant.id)

    with TestClient(app) as client:
        yield client, testing_session, customer.id, *ids

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_my_orders_returns_only_current_users_purchase_and_rental_history(order_client):
    client, _, _, purchase_id, rental_id, other_purchase_id, _ = order_client

    response = client.get("/api/v1/orders/my-orders")

    assert response.status_code == 200
    orders = response.json()
    assert {(order["order_type"], order["id"]) for order in orders} == {
        ("Purchase", purchase_id),
        ("Rental", rental_id),
    }
    assert ("Purchase", other_purchase_id) not in {
        (order["order_type"], order["id"]) for order in orders
    }
    assert all(order["items"][0]["plant_name"] == "Monstera" for order in orders)
    assert all(order["status"] == "Pending" for order in orders)
    assert all(order["items"][0]["plant_id"] for order in orders)
    for order in orders:
        assert {
            "id",
            "order_type",
            "total_amount",
            "created_at",
            "status",
            "payment_status",
            "items",
        } <= order.keys()
        assert {
            "plant_name",
            "quantity",
            "unit_price",
            "total_price",
        } <= order["items"][0].keys()

    rental = next(order for order in orders if order["order_type"] == "Rental")
    assert rental["items"][0]["rental_months"] == 3


def test_my_orders_returns_empty_list_when_customer_has_no_history(order_client):
    client, *_ = order_client
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=999,
        role=SimpleNamespace(role_name="User"),
    )

    response = client.get("/api/v1/orders/my-orders")

    assert response.status_code == 200
    assert response.json() == []


def test_my_orders_works_without_rejection_reason_column(order_client):
    client, testing_session, _, _, _, _, plant_id = order_client
    with testing_session() as db:
        customer = db.query(User).filter_by(email="customer.one@example.com").one()
        db.add(
            PlantRentalOrder(
                user_id=customer.id,
                plant_id=plant_id,
                quantity=2,
                rental_start_date=date(2026, 1, 1),
                rental_end_date=date(2026, 1, 3),
                rental_duration_days=2,
                rental_price_per_day=Decimal("5.00"),
                total_amount=Decimal("20.00"),
                status="Pending",
            )
        )
        db.commit()

    response = client.get("/api/v1/orders/my-orders")

    assert response.status_code == 200, response.text
    rental = next(order for order in response.json() if order["order_type"] == "Rent")
    assert rental["items"][0]["plant_name"] == "Monstera"
    assert rental["items"][0]["quantity"] == 2
    assert rental["items"][0]["unit_price"] == 5.0
    assert rental["items"][0]["total_price"] == 20.0


def test_my_orders_logs_query_errors_and_reraises(caplog):
    def fail_query(_statement):
        raise RuntimeError("database query failed")

    with pytest.raises(RuntimeError, match="database query failed"):
        list_my_orders(
            current_user=SimpleNamespace(id=42),
            db=SimpleNamespace(scalars=fail_query),
        )

    assert "Failed to fetch order history for user_id=42" in caplog.text
    assert "database query failed" in caplog.text


def test_order_detail_is_scoped_to_current_user_and_order_type(order_client):
    client, _, _, purchase_id, rental_id, other_purchase_id, _ = order_client

    purchase_response = client.get(
        f"/api/v1/orders/my-orders/purchase/{purchase_id}"
    )
    rental_response = client.get(
        f"/api/v1/orders/my-orders/rental/{rental_id}"
    )
    unauthorized_response = client.get(
        f"/api/v1/orders/my-orders/purchase/{other_purchase_id}"
    )

    assert purchase_response.status_code == 200
    assert purchase_response.json()["items"][0]["plant_name"] == "Monstera"
    assert rental_response.status_code == 200
    assert rental_response.json()["items"][0]["rental_months"] == 3
    assert unauthorized_response.status_code == 404


def test_rental_checkout_creates_history_record_for_customer(order_client):
    client, _, customer_id, _, _, _, plant_id = order_client

    response = client.post(
        "/api/v1/orders/rentals",
        json={"plant_id": plant_id, "quantity": 2, "rental_months": 4},
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == customer_id
    assert response.json()["total_amount"] == 40


def test_nursery_role_cannot_read_or_create_customer_orders(order_client):
    client, _, _, _, _, _, plant_id = order_client
    nursery_user = SimpleNamespace(
        id=999,
        role=SimpleNamespace(role_name="Nursery"),
    )
    client.app.dependency_overrides[get_current_user] = lambda: nursery_user

    assert client.get("/api/v1/orders/my-orders").status_code == 403
    assert client.post(
        "/api/v1/orders/rentals",
        json={"plant_id": plant_id, "quantity": 1, "rental_months": 1},
    ).status_code == 403
