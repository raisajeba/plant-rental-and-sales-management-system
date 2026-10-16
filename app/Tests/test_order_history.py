from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.constants import AvailabilityStatus, ListingApprovalStatus
from app.database import Base, get_db
from app.dependencies.auth import get_current_user
from app.models import CartItem, Nursery, Order, OrderItem, Plant, RentalOrder, Role, User
from app.routers.cart import router as cart_router
from app.routers.order import router


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
    app.include_router(cart_router, prefix="/api/v1")

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
        yield client, customer.id, *ids, testing_session

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_my_orders_returns_only_current_users_purchase_and_rental_history(order_client):
    client, _, purchase_id, rental_id, other_purchase_id, _, _ = order_client

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


def test_order_detail_is_scoped_to_current_user_and_order_type(order_client):
    client, _, purchase_id, rental_id, other_purchase_id, _, _ = order_client

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
    client, customer_id, _, _, _, plant_id, _ = order_client

    response = client.post(
        "/api/v1/orders/rentals",
        json={"plant_id": plant_id, "quantity": 2, "rental_months": 4},
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == customer_id
    assert response.json()["total_amount"] == 40


def test_nursery_role_cannot_read_or_create_customer_orders(order_client):
    client, _, _, _, _, plant_id, _ = order_client
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


def test_pending_plant_cannot_be_purchased_or_rented(order_client):
    client, customer_id, _, _, _, plant_id, testing_session = order_client
    with testing_session() as session:
        plant = session.get(Plant, plant_id)
        plant.approval_status = ListingApprovalStatus.PENDING.value
        session.add(CartItem(user_id=customer_id, plant_id=plant_id, quantity=1))
        session.commit()

    purchase_response = client.post("/api/v1/orders/checkout")
    rental_response = client.post(
        "/api/v1/orders/rentals",
        json={"plant_id": plant_id, "quantity": 1, "rental_months": 1},
    )

    assert purchase_response.status_code == 404
    assert rental_response.status_code == 404
