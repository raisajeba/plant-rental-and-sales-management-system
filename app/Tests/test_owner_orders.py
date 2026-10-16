from datetime import datetime
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
from app.models import Nursery, Order, OrderItem, Plant, Role, User
from app.routers.order import router


@pytest.fixture
def owner_order_client():
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
        email="customer.one@orders-test.example.com",
        password="hashed-password",
        role=user_role,
    )
    other_customer = User(
        name="Customer Two",
        email="customer.two@orders-test.example.com",
        password="hashed-password",
        role=user_role,
    )
    owner = User(
        name="Owner One",
        email="owner.one@orders-test.example.com",
        password="hashed-password",
        role=nursery_role,
    )
    other_owner = User(
        name="Owner Two",
        email="owner.two@orders-test.example.com",
        password="hashed-password",
        role=nursery_role,
    )
    first_nursery = Nursery(
        owner=owner,
        name="Owner One Nursery",
        address="1 Garden Road",
        city="Dhaka",
        phone="0123456789",
    )
    second_nursery = Nursery(
        owner=other_owner,
        name="Owner Two Nursery",
        address="2 Garden Road",
        city="Dhaka",
        phone="0123456788",
    )
    first_plant = Plant(
        nursery=first_nursery,
        name="Monstera",
        category="Indoor",
        buy_price=10,
        available_quantity=8,
        availability_status=AvailabilityStatus.FOR_SALE.value,
    )
    second_plant = Plant(
        nursery=second_nursery,
        name="Fern",
        category="Indoor",
        buy_price=20,
        available_quantity=8,
        availability_status=AvailabilityStatus.FOR_SALE.value,
    )

    current_user = {"user": owner}

    def override_get_db():
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user["user"]

    with testing_session() as session:
        session.add_all(
            [
                customer,
                other_customer,
                owner,
                other_owner,
                first_plant,
                second_plant,
            ]
        )
        session.flush()
        own_order = Order(
            user_id=customer.id,
            total_amount=20,
            status="Pending",
            created_at=datetime(2026, 1, 1),
            items=[
                OrderItem(
                    plant_id=first_plant.id,
                    quantity=2,
                    unit_price=10,
                    total_price=20,
                )
            ],
        )
        mixed_order = Order(
            user_id=customer.id,
            total_amount=30,
            status="Pending",
            created_at=datetime(2026, 1, 2),
            items=[
                OrderItem(
                    plant_id=first_plant.id,
                    quantity=1,
                    unit_price=10,
                    total_price=10,
                ),
                OrderItem(
                    plant_id=second_plant.id,
                    quantity=1,
                    unit_price=20,
                    total_price=20,
                ),
            ],
        )
        other_customer_order = Order(
            user_id=other_customer.id,
            total_amount=10,
            status="Pending",
            items=[
                OrderItem(
                    plant_id=first_plant.id,
                    quantity=1,
                    unit_price=10,
                    total_price=10,
                )
            ],
        )
        session.add_all([own_order, mixed_order, other_customer_order])
        session.commit()
        ids = {
            "customer_id": customer.id,
            "owner_id": owner.id,
            "other_owner_id": other_owner.id,
            "own_order_id": own_order.id,
            "mixed_order_id": mixed_order.id,
            "other_customer_order_id": other_customer_order.id,
        }

    with TestClient(app) as client:
        yield client, current_user, ids, testing_session

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_owner_order_list_and_details_only_include_their_plants(owner_order_client):
    client, _, ids, _ = owner_order_client

    response = client.get("/api/v1/orders/owner")

    assert response.status_code == 200
    orders = {order["id"]: order for order in response.json()}
    assert set(orders) == {ids["own_order_id"], ids["mixed_order_id"], ids["other_customer_order_id"]}
    assert orders[ids["own_order_id"]]["customer_name"] == "Customer One"
    assert orders[ids["own_order_id"]]["items"][0]["plant_name"] == "Monstera"
    assert orders[ids["own_order_id"]]["items"][0]["quantity"] == 2
    assert orders[ids["own_order_id"]]["total_price"] == 20
    assert orders[ids["own_order_id"]]["order_date"].startswith("2026-01-01")
    assert orders[ids["mixed_order_id"]]["items"] == [
        {
            "plant_id": orders[ids["mixed_order_id"]]["items"][0]["plant_id"],
            "plant_name": "Monstera",
            "quantity": 1,
            "unit_price": 10,
            "total_price": 10,
        }
    ]
    assert orders[ids["mixed_order_id"]]["total_price"] == 10

    details = client.get(f"/api/v1/orders/owner/{ids['mixed_order_id']}")
    assert details.status_code == 200
    assert [item["plant_name"] for item in details.json()["items"]] == ["Monstera"]


def test_owner_status_update_validates_and_is_visible_to_customer(owner_order_client):
    client, current_user, ids, testing_session = owner_order_client
    order_id = ids["own_order_id"]

    updated = client.patch(
        f"/api/v1/orders/owner/{order_id}/status",
        json={"status": "Confirmed"},
    )

    assert updated.status_code == 200
    assert updated.json()["status"] == "Confirmed"
    invalid = client.patch(
        f"/api/v1/orders/owner/{order_id}/status",
        json={"status": "Shipped"},
    )
    assert invalid.status_code == 422
    current_user["user"] = SimpleNamespace(
        id=ids["customer_id"],
        role=SimpleNamespace(role_name="User"),
    )
    customer_history = client.get("/api/v1/orders/my-orders")
    assert next(
        order for order in customer_history.json() if order["id"] == order_id
    )["status"] == "Confirmed"
    with testing_session() as session:
        assert session.get(Order, order_id).status == "Confirmed"


def test_owner_cannot_access_or_update_another_owners_order(owner_order_client):
    client, current_user, ids, testing_session = owner_order_client
    current_user["user"] = SimpleNamespace(
        id=ids["other_owner_id"],
        role=SimpleNamespace(role_name="Nursery"),
    )

    assert client.get(
        f"/api/v1/orders/owner/{ids['own_order_id']}"
    ).status_code == 404
    assert client.patch(
        f"/api/v1/orders/owner/{ids['own_order_id']}/status",
        json={"status": "Processing"},
    ).status_code == 404
    with testing_session() as session:
        assert session.get(Order, ids["own_order_id"]).status == "Pending"


def test_customer_cannot_access_nursery_order_endpoints(owner_order_client):
    client, current_user, ids, _ = owner_order_client
    current_user["user"] = SimpleNamespace(
        id=ids["customer_id"],
        role=SimpleNamespace(role_name="User"),
    )

    assert client.get("/api/v1/orders/owner").status_code == 403
    assert client.patch(
        f"/api/v1/orders/owner/{ids['own_order_id']}/status",
        json={"status": "Cancelled"},
    ).status_code == 403


def test_owner_can_update_shared_order_for_their_plant_and_customer_sees_status(
    owner_order_client,
):
    client, current_user, ids, _ = owner_order_client
    response = client.patch(
        f"/api/v1/orders/owner/{ids['mixed_order_id']}/status",
        json={"status": "Processing"},
    )

    assert response.status_code == 200
    assert [item["plant_name"] for item in response.json()["items"]] == ["Monstera"]
    assert response.json()["status"] == "Processing"

    current_user["user"] = SimpleNamespace(
        id=ids["customer_id"],
        role=SimpleNamespace(role_name="User"),
    )
    customer_order = client.get("/api/v1/orders/my-orders").json()
    assert next(
        order for order in customer_order
        if order["id"] == ids["mixed_order_id"]
    )["status"] == "Processing"
