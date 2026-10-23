import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.constants import AvailabilityStatus
from app.database import Base, get_db
from app.dependencies.auth import get_current_user
from app.models import (
    Nursery,
    Plant,
    PlantRentalOrder,
    Role,
    User,
)
from app.routers.rentals import router


@pytest.fixture
def rental_api():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(connection, _):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    user_role = Role(role_name="User")
    nursery_role = Role(role_name="Nursery")
    customer = User(
        name="Rental Customer",
        email="rental.customer@example.com",
        password="test-hash",
        role=user_role,
    )
    owner = User(
        name="Nursery Owner",
        email="rental.owner@example.com",
        password="test-hash",
        role=nursery_role,
    )
    other_owner = User(
        name="Other Nursery Owner",
        email="rental.other-owner@example.com",
        password="test-hash",
        role=nursery_role,
    )

    with testing_session() as session:
        session.add_all([customer, owner, other_owner])
        session.flush()
        nursery = Nursery(
            owner_id=owner.id,
            name="Rental Nursery",
            address="12 Garden Road",
            city="Dhaka",
            phone="0123456789",
            status="active",
        )
        closed_nursery = Nursery(
            owner_id=other_owner.id,
            name="Closed Rental Nursery",
            address="34 Garden Road",
            city="Dhaka",
            phone="0123456788",
            status="inactive",
        )
        session.add_all([nursery, closed_nursery])
        session.flush()
        plants = [
            Plant(
                nursery_id=nursery.id,
                name="Rentable Fern",
                category="Indoor",
                rent_price=Decimal("5.50"),
                available_quantity=5,
                availability_status=AvailabilityStatus.FOR_BOTH.value,
            ),
            Plant(
                nursery_id=nursery.id,
                name="Sale Only Fern",
                category="Indoor",
                rent_price=Decimal("5.00"),
                available_quantity=5,
                availability_status=AvailabilityStatus.FOR_SALE.value,
            ),
            Plant(
                nursery_id=nursery.id,
                name="Out of Stock Fern",
                category="Indoor",
                rent_price=Decimal("5.00"),
                available_quantity=0,
                availability_status=AvailabilityStatus.FOR_RENT.value,
            ),
            Plant(
                nursery_id=closed_nursery.id,
                name="Closed Nursery Fern",
                category="Indoor",
                rent_price=Decimal("5.00"),
                available_quantity=5,
                availability_status=AvailabilityStatus.FOR_RENT.value,
            ),
        ]
        session.add_all(plants)
        session.commit()
        plant_ids = {plant.name: plant.id for plant in plants}
        customer_id = customer.id
        owner_id = owner.id
        other_owner_id = other_owner.id

    current_user = {
        "value": SimpleNamespace(
            id=customer_id,
            role=SimpleNamespace(role_name="User"),
        )
    }

    def override_get_db():
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user["value"]

    with TestClient(app) as client:
        yield (
            client,
            current_user,
            plant_ids,
            testing_session,
            customer_id,
            owner_id,
            other_owner_id,
        )

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def rental_dates():
    start = datetime.now(timezone.utc).date() + timedelta(days=3)
    return start, start + timedelta(days=4)


def rental_payload(plant_id, *, quantity=2, start=None, end=None, **extra):
    if start is None or end is None:
        start, end = rental_dates()
    return {
        "plant_id": plant_id,
        "quantity": quantity,
        "rental_start_date": start.isoformat(),
        "rental_end_date": end.isoformat(),
        **extra,
    }


def test_browse_lists_only_available_rental_plants(rental_api):
    client, _, plant_ids, *_ = rental_api

    response = client.get("/api/v1/rentals/plants")

    assert response.status_code == 200
    assert [plant["id"] for plant in response.json()] == [
        plant_ids["Rentable Fern"]
    ]


def test_browse_returns_empty_list_when_none_are_available(rental_api):
    client, _, _, testing_session, *_ = rental_api
    with testing_session() as session:
        for plant in session.scalars(select(Plant)):
            plant.availability_status = AvailabilityStatus.FOR_SALE.value
        session.commit()

    response = client.get("/api/v1/rentals/plants")

    assert response.status_code == 200
    assert response.json() == []


def test_get_plant_details_returns_available_rental_plant(rental_api):
    client, _, plant_ids, *_ = rental_api

    response = client.get(
        f"/api/v1/rentals/plants/{plant_ids['Rentable Fern']}"
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Rentable Fern"
    assert response.json()["rent_price"] == 5.5


@pytest.mark.parametrize(
    "plant_name",
    ["Sale Only Fern", "Out of Stock Fern", "Closed Nursery Fern"],
)
def test_unavailable_plant_is_not_returned_by_details_api(rental_api, plant_name):
    client, _, plant_ids, *_ = rental_api

    response = client.get(f"/api/v1/rentals/plants/{plant_ids[plant_name]}")

    assert response.status_code == 404


def test_details_api_returns_not_found_for_unknown_plant(rental_api):
    client, *_ = rental_api

    response = client.get("/api/v1/rentals/plants/99999")

    assert response.status_code == 404


def test_rental_request_rejects_unavailable_plant(rental_api):
    client, _, plant_ids, *_ = rental_api

    response = client.post(
        "/api/v1/rentals/requests",
        json=rental_payload(plant_ids["Sale Only Fern"]),
    )

    assert response.status_code == 409


def test_rental_request_rejects_unknown_plant(rental_api):
    client, *_ = rental_api

    response = client.post(
        "/api/v1/rentals/requests",
        json=rental_payload(99999),
    )

    assert response.status_code == 404


def test_rental_request_requires_authentication(rental_api):
    client, _, plant_ids, *_ = rental_api
    client.app.dependency_overrides.pop(get_current_user)

    response = client.post(
        "/api/v1/rentals/requests",
        json=rental_payload(plant_ids["Rentable Fern"]),
    )

    assert response.status_code == 401


def test_rental_request_persists_server_calculated_amount(rental_api):
    client, _, plant_ids, testing_session, customer_id, *_ = rental_api
    start, end = rental_dates()

    response = client.post(
        "/api/v1/rentals/requests",
        json=rental_payload(
            plant_ids["Rentable Fern"], quantity=2, start=start, end=end
        ),
    )

    assert response.status_code == 201
    rental = response.json()
    assert rental["user_id"] == customer_id
    assert rental["plant_id"] == plant_ids["Rentable Fern"]
    assert rental["quantity"] == 2
    assert rental["rental_duration_days"] == 4
    assert rental["rental_price_per_day"] == 5.5
    assert rental["total_amount"] == 44
    assert rental["status"] == "Pending"
    assert rental["payment_status"] == "PENDING"
    assert rental["rejection_reason"] is None
    with testing_session() as session:
        saved = session.get(PlantRentalOrder, rental["rental_id"])
        assert saved is not None
        assert saved.user_id == customer_id
        assert saved.total_amount == Decimal("44.00")
        assert saved.payment_transaction_id is None


def test_same_day_rental_has_minimum_one_day_duration(rental_api):
    client, _, plant_ids, *_ = rental_api
    same_day = datetime.now(timezone.utc).date() + timedelta(days=1)

    response = client.post(
        "/api/v1/rentals/requests",
        json=rental_payload(
            plant_ids["Rentable Fern"], quantity=3, start=same_day, end=same_day
        ),
    )

    assert response.status_code == 201
    assert response.json()["rental_duration_days"] == 1
    assert response.json()["total_amount"] == 16.5


def test_client_cannot_override_authoritative_rental_price(rental_api):
    client, _, plant_ids, *_ = rental_api

    response = client.post(
        "/api/v1/rentals/requests",
        json=rental_payload(
            plant_ids["Rentable Fern"], rental_price_per_day=0.01, total_amount=0.02
        ),
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"plant_id": 1, "quantity": 1},
        {
            "plant_id": 1,
            "quantity": 1,
            "rental_start_date": "not-a-date",
            "rental_end_date": "2027-01-01",
        },
        {
            "plant_id": 1,
            "quantity": 1,
            "rental_start_date": "2027-01-02",
            "rental_end_date": "2027-01-01",
        },
    ],
)
def test_missing_or_invalid_rental_dates_are_rejected(rental_api, payload):
    client, *_ = rental_api

    response = client.post("/api/v1/rentals/requests", json=payload)

    assert response.status_code == 422


def test_past_rental_start_date_is_rejected(rental_api):
    client, _, plant_ids, *_ = rental_api
    yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)

    response = client.post(
        "/api/v1/rentals/requests",
        json=rental_payload(
            plant_ids["Rentable Fern"],
            start=yesterday,
            end=yesterday + timedelta(days=1),
        ),
    )

    assert response.status_code == 422


@pytest.mark.parametrize("quantity", [0, -1])
def test_nonpositive_rental_quantity_is_rejected(rental_api, quantity):
    client, _, plant_ids, *_ = rental_api

    response = client.post(
        "/api/v1/rentals/requests",
        json=rental_payload(plant_ids["Rentable Fern"], quantity=quantity),
    )

    assert response.status_code == 422


def test_quantity_overlapping_existing_rental_capacity_is_rejected(rental_api):
    client, _, plant_ids, *_ = rental_api
    start, end = rental_dates()
    first = client.post(
        "/api/v1/rentals/requests",
        json=rental_payload(
            plant_ids["Rentable Fern"], quantity=4, start=start, end=end
        ),
    )
    second = client.post(
        "/api/v1/rentals/requests",
        json=rental_payload(
            plant_ids["Rentable Fern"], quantity=2, start=start, end=end
        ),
    )

    assert first.status_code == 201
    assert second.status_code == 409


def test_owner_rental_list_is_scoped_to_owned_plants(rental_api):
    client, current_user, plant_ids, *_rest = rental_api
    start, end = rental_dates()
    created = client.post(
        "/api/v1/rentals/requests",
        json=rental_payload(plant_ids["Rentable Fern"], start=start, end=end),
    )
    current_user["value"] = SimpleNamespace(
        id=_rest[2],
        role=SimpleNamespace(role_name="Nursery"),
    )

    response = client.get("/api/v1/rentals/owner")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == created.json()["rental_id"]
    assert response.json()[0]["customer_name"] == "Rental Customer"


def test_owner_can_advance_owned_rental_status(rental_api):
    client, current_user, plant_ids, *_rest = rental_api
    start, end = rental_dates()
    created = client.post(
        "/api/v1/rentals/requests",
        json=rental_payload(plant_ids["Rentable Fern"], start=start, end=end),
    )
    current_user["value"] = SimpleNamespace(
        id=_rest[2],
        role=SimpleNamespace(role_name="Nursery"),
    )

    response = client.patch(
        f"/api/v1/rentals/owner/{created.json()['rental_id']}/status",
        json={"status": "Approved"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Approved"


def test_owner_cannot_update_another_nurserys_rental_status(rental_api):
    client, current_user, plant_ids, *_rest = rental_api
    start, end = rental_dates()
    created = client.post(
        "/api/v1/rentals/requests",
        json=rental_payload(plant_ids["Rentable Fern"], start=start, end=end),
    )
    current_user["value"] = SimpleNamespace(
        id=_rest[3],
        role=SimpleNamespace(role_name="Nursery"),
    )

    response = client.patch(
        f"/api/v1/rentals/owner/{created.json()['rental_id']}/status",
        json={"status": "Confirmed"},
    )

    assert response.status_code == 404


def test_user_rental_history_returns_empty_current_and_previous_lists(rental_api):
    client, *_ = rental_api

    response = client.get("/api/v1/rentals/my-orders")

    assert response.status_code == 200
    assert response.json() == {"current_orders": [], "previous_orders": []}


def test_user_rental_history_includes_owned_order_details(rental_api):
    client, _, plant_ids, *_ = rental_api
    created = client.post(
        "/api/v1/rentals/requests",
        json=rental_payload(plant_ids["Rentable Fern"]),
    )

    response = client.get("/api/v1/rentals/my-orders")

    assert response.status_code == 200
    history = response.json()
    assert len(history["current_orders"]) == 1
    order = history["current_orders"][0]
    assert order["id"] == created.json()["rental_id"]
    assert order["order_identifier"] == created.json()["order_identifier"]
    assert order["plant_name"] == "Rentable Fern"
    assert order["quantity"] == 2
    assert order["total_amount"] == 44
    assert history["previous_orders"] == []


def test_user_rental_history_separates_previous_orders(rental_api):
    client, _, plant_ids, testing_session, *_ = rental_api
    created = client.post(
        "/api/v1/rentals/requests",
        json=rental_payload(plant_ids["Rentable Fern"]),
    )
    with testing_session() as session:
        saved = session.get(PlantRentalOrder, created.json()["rental_id"])
        saved.rental_start_date = datetime.now(timezone.utc).date() - timedelta(days=5)
        saved.rental_end_date = datetime.now(timezone.utc).date() - timedelta(days=1)
        saved.status = "Completed"
        session.commit()

    response = client.get("/api/v1/rentals/my-orders")

    assert response.status_code == 200
    assert response.json()["current_orders"] == []
    assert len(response.json()["previous_orders"]) == 1
    assert response.json()["previous_orders"][0]["status"] == "Completed"


def test_owner_can_view_owned_rental_request_details(rental_api):
    client, current_user, plant_ids, *_rest = rental_api
    created = client.post(
        "/api/v1/rentals/requests",
        json=rental_payload(plant_ids["Rentable Fern"]),
    )
    current_user["value"] = SimpleNamespace(
        id=_rest[2],
        role=SimpleNamespace(role_name="Nursery"),
    )

    response = client.get(
        f"/api/v1/rentals/owner/{created.json()['rental_id']}"
    )

    assert response.status_code == 200
    assert response.json()["plant_name"] == "Rentable Fern"
    assert response.json()["customer_name"] == "Rental Customer"


def test_owner_cannot_view_another_nurserys_rental_details(rental_api):
    client, current_user, plant_ids, *_rest = rental_api
    created = client.post(
        "/api/v1/rentals/requests",
        json=rental_payload(plant_ids["Rentable Fern"]),
    )
    current_user["value"] = SimpleNamespace(
        id=_rest[3],
        role=SimpleNamespace(role_name="Nursery"),
    )

    response = client.get(
        f"/api/v1/rentals/owner/{created.json()['rental_id']}"
    )

    assert response.status_code == 404


def test_owner_approval_rechecks_available_quantity(rental_api):
    client, current_user, plant_ids, testing_session, *_rest = rental_api
    created = client.post(
        "/api/v1/rentals/requests",
        json=rental_payload(plant_ids["Rentable Fern"], quantity=2),
    )
    with testing_session() as session:
        plant = session.get(Plant, plant_ids["Rentable Fern"])
        plant.available_quantity = 1
        session.commit()
    current_user["value"] = SimpleNamespace(
        id=_rest[1],
        role=SimpleNamespace(role_name="Nursery"),
    )

    response = client.patch(
        f"/api/v1/rentals/owner/{created.json()['rental_id']}/status",
        json={"status": "Approved"},
    )

    assert response.status_code == 409


def test_owner_can_approve_available_rental_request(rental_api):
    client, current_user, plant_ids, *_rest = rental_api
    created = client.post(
        "/api/v1/rentals/requests",
        json=rental_payload(plant_ids["Rentable Fern"]),
    )
    current_user["value"] = SimpleNamespace(
        id=_rest[2],
        role=SimpleNamespace(role_name="Nursery"),
    )

    response = client.patch(
        f"/api/v1/rentals/owner/{created.json()['rental_id']}/status",
        json={"status": "Approved"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Approved"


def test_owner_cannot_activate_rental_before_customer_payment(rental_api):
    client, current_user, plant_ids, *_rest = rental_api
    created = client.post(
        "/api/v1/rentals/requests",
        json=rental_payload(plant_ids["Rentable Fern"]),
    )
    current_user["value"] = SimpleNamespace(
        id=_rest[2],
        role=SimpleNamespace(role_name="Nursery"),
    )
    approval = client.patch(
        f"/api/v1/rentals/owner/{created.json()['rental_id']}/status",
        json={"status": "Approved"},
    )
    activation = client.patch(
        f"/api/v1/rentals/owner/{created.json()['rental_id']}/status",
        json={"status": "Active"},
    )

    assert approval.status_code == 200
    assert activation.status_code == 409
    assert "complete payment" in activation.json()["detail"]


def test_owner_rejection_requires_reason_and_returns_safe_null(rental_api):
    client, current_user, plant_ids, *_rest = rental_api
    created = client.post(
        "/api/v1/rentals/requests",
        json=rental_payload(plant_ids["Rentable Fern"]),
    )
    current_user["value"] = SimpleNamespace(
        id=_rest[2],
        role=SimpleNamespace(role_name="Nursery"),
    )
    status_url = f"/api/v1/rentals/owner/{created.json()['rental_id']}/status"

    missing_reason = client.patch(status_url, json={"status": "Rejected"})
    rejected = client.patch(
        status_url,
        json={"status": "Rejected", "rejection_reason": "  Not enough stock  "},
    )

    assert missing_reason.status_code == 422
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "Rejected"
    assert rejected.json()["rejection_reason"] is None
    assert not hasattr(PlantRentalOrder, "rejection_reason")
