import os
from types import SimpleNamespace

os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.constants import AvailabilityStatus
from app.database import Base, get_db
from app.dependencies.auth import get_current_user
from app.models import CartItem, Nursery, Plant
from app.routers.cart import router


@pytest.fixture
def cart_api():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    current_user_id = {"value": 11}

    def override_get_db():
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=current_user_id["value"]
    )

    with testing_session() as session:
        nursery = Nursery(
            owner_id=1,
            name="Green Leaf Nursery",
            address="12 Garden Road",
            city="Dhaka",
            phone="0123456789",
            status="active",
        )
        session.add(nursery)
        session.flush()
        plants = [
            Plant(
                nursery_id=nursery.id,
                name="Golden Pothos",
                category="Indoor",
                buy_price=15,
                available_quantity=5,
                availability_status=AvailabilityStatus.FOR_SALE.value,
            ),
            Plant(
                nursery_id=nursery.id,
                name="Silver Pothos",
                category="Indoor",
                buy_price=8,
                available_quantity=3,
                availability_status=AvailabilityStatus.FOR_BOTH.value,
            ),
            Plant(
                nursery_id=nursery.id,
                name="Rental Fern",
                category="Indoor",
                rent_price=4,
                available_quantity=5,
                availability_status=AvailabilityStatus.FOR_RENT.value,
            ),
            Plant(
                nursery_id=nursery.id,
                name="Out of Stock Rose",
                category="Outdoor",
                buy_price=12,
                available_quantity=0,
                availability_status=AvailabilityStatus.FOR_SALE.value,
            ),
        ]
        session.add_all(plants)
        session.commit()
        plant_ids = {plant.name: plant.id for plant in plants}

    with TestClient(app) as client:
        yield client, current_user_id, plant_ids, testing_session

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_add_cart_item_returns_item_and_plant_details(cart_api):
    client, _, plant_ids, _ = cart_api

    response = client.post(
        "/api/v1/cart/items",
        json={"plant_id": plant_ids["Golden Pothos"], "quantity": 2},
    )

    assert response.status_code == 201
    assert response.json()["plant_id"] == plant_ids["Golden Pothos"]
    assert response.json()["quantity"] == 2
    assert response.json()["plant"]["name"] == "Golden Pothos"
    assert response.json()["plant"]["buy_price"] == 15


def test_adding_same_plant_increments_quantity(cart_api):
    client, _, plant_ids, _ = cart_api
    plant_id = plant_ids["Golden Pothos"]

    first = client.post(
        "/api/v1/cart/items",
        json={"plant_id": plant_id, "quantity": 2},
    )
    second = client.post(
        "/api/v1/cart/items",
        json={"plant_id": plant_id, "quantity": 1},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["quantity"] == 3


def test_different_plants_remain_separate_cart_items(cart_api):
    client, _, plant_ids, _ = cart_api

    for plant_name in ("Golden Pothos", "Silver Pothos"):
        response = client.post(
            "/api/v1/cart/items",
            json={"plant_id": plant_ids[plant_name], "quantity": 1},
        )
        assert response.status_code == 201

    cart = client.get("/api/v1/cart/items")

    assert cart.status_code == 200
    assert [item["plant"]["name"] for item in cart.json()] == [
        "Golden Pothos",
        "Silver Pothos",
    ]


def test_requested_quantity_cannot_exceed_available_stock(cart_api):
    client, _, plant_ids, testing_session = cart_api
    plant_id = plant_ids["Silver Pothos"]

    response = client.post(
        "/api/v1/cart/items",
        json={"plant_id": plant_id, "quantity": 4},
    )

    assert response.status_code == 409
    assert "exceeds available stock" in response.json()["detail"]
    with testing_session() as session:
        assert session.scalar(
            select(CartItem).where(CartItem.plant_id == plant_id)
        ) is None


def test_existing_cart_quantity_cannot_be_incremented_past_stock(cart_api):
    client, _, plant_ids, _ = cart_api
    plant_id = plant_ids["Silver Pothos"]
    client.post(
        "/api/v1/cart/items",
        json={"plant_id": plant_id, "quantity": 2},
    )

    response = client.post(
        "/api/v1/cart/items",
        json={"plant_id": plant_id, "quantity": 2},
    )
    cart = client.get("/api/v1/cart/items")

    assert response.status_code == 409
    assert cart.json()[0]["quantity"] == 2


@pytest.mark.parametrize(
    ("plant_name", "detail"),
    [
        ("Rental Fern", "not currently available for sale"),
        ("Out of Stock Rose", "out of stock"),
    ],
)
def test_non_sale_or_out_of_stock_plants_cannot_be_added(cart_api, plant_name, detail):
    client, _, plant_ids, _ = cart_api

    response = client.post(
        "/api/v1/cart/items",
        json={"plant_id": plant_ids[plant_name], "quantity": 1},
    )

    assert response.status_code == 400
    assert detail in response.json()["detail"]


@pytest.mark.parametrize("quantity", [0, -1])
def test_cart_quantity_must_be_positive(cart_api, quantity):
    client, _, plant_ids, _ = cart_api

    response = client.post(
        "/api/v1/cart/items",
        json={"plant_id": plant_ids["Golden Pothos"], "quantity": quantity},
    )

    assert response.status_code == 422


def test_unknown_plant_returns_not_found(cart_api):
    client, _, _, _ = cart_api

    response = client.post(
        "/api/v1/cart/items",
        json={"plant_id": 9999, "quantity": 1},
    )

    assert response.status_code == 404


def test_inactive_nursery_listing_cannot_be_added_to_cart(cart_api):
    client, _, plant_ids, testing_session = cart_api
    plant_id = plant_ids["Golden Pothos"]
    with testing_session() as session:
        plant = session.get(Plant, plant_id)
        plant.nursery.status = "inactive"
        session.commit()

    response = client.post(
        "/api/v1/cart/items",
        json={"plant_id": plant_id, "quantity": 1},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "This plant is not currently available."


def test_cart_routes_require_authentication(cart_api):
    client, _, _, _ = cart_api
    app = client.app
    app.dependency_overrides.pop(get_current_user)

    response = client.get("/api/v1/cart/items")

    assert response.status_code == 401


def test_cart_items_are_isolated_by_authenticated_user(cart_api):
    client, current_user_id, plant_ids, testing_session = cart_api
    plant_id = plant_ids["Golden Pothos"]
    client.post(
        "/api/v1/cart/items",
        json={"plant_id": plant_id, "quantity": 2},
    )

    current_user_id["value"] = 22
    other_users_cart = client.get("/api/v1/cart/items")
    other_user_item = client.post(
        "/api/v1/cart/items",
        json={"plant_id": plant_id, "quantity": 1},
    )

    assert other_users_cart.status_code == 200
    assert other_users_cart.json() == []
    assert other_user_item.status_code == 201
    assert other_user_item.json()["quantity"] == 1
    with testing_session() as session:
        rows = session.scalars(
            select(CartItem).where(CartItem.plant_id == plant_id).order_by(CartItem.user_id)
        ).all()
        assert [(item.user_id, item.quantity) for item in rows] == [(11, 2), (22, 1)]


def test_adding_to_cart_does_not_reserve_or_modify_stock(cart_api):
    client, _, plant_ids, testing_session = cart_api
    plant_id = plant_ids["Golden Pothos"]

    response = client.post(
        "/api/v1/cart/items",
        json={"plant_id": plant_id, "quantity": 2},
    )

    assert response.status_code == 201
    with testing_session() as session:
        plant = session.get(Plant, plant_id)
        assert plant.available_quantity == 5


def test_cart_item_database_constraint_rejects_nonpositive_quantity(cart_api):
    _, _, plant_ids, testing_session = cart_api

    with testing_session() as session:
        session.add(
            CartItem(
                user_id=11,
                plant_id=plant_ids["Golden Pothos"],
                quantity=0,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_cart_item_database_constraint_prevents_duplicate_user_plant(cart_api):
    _, _, plant_ids, testing_session = cart_api
    plant_id = plant_ids["Golden Pothos"]

    with testing_session() as session:
        session.add_all(
            [
                CartItem(user_id=11, plant_id=plant_id, quantity=1),
                CartItem(user_id=11, plant_id=plant_id, quantity=2),
            ]
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
