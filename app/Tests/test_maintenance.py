from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.dependencies.auth import get_current_user
from app.models import (
    MaintenanceRequest,
    Nursery,
    Order,
    OrderItem,
    Plant,
    Role,
    User,
)
from app.routers.maintenance import router


@pytest.fixture
def maintenance_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    current_user = {"user": None}

    def override_get_db():
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user["user"]

    with testing_session() as session:
        user_role = Role(role_name="User")
        nursery_role = Role(role_name="Nursery")
        owner = User(
            name="Owner",
            email="maintenance-owner@example.test",
            password="hashed-password",
            role=nursery_role,
        )
        other_owner = User(
            name="Other Owner",
            email="maintenance-other-owner@example.test",
            password="hashed-password",
            role=nursery_role,
        )
        customer = User(
            name="Customer",
            email="maintenance-customer@example.test",
            password="hashed-password",
            role=user_role,
        )
        unrelated_customer = User(
            name="Unrelated Customer",
            email="maintenance-unrelated@example.test",
            password="hashed-password",
            role=user_role,
        )
        nursery = Nursery(
            owner=owner,
            name="Owner Nursery",
            address="1 Garden Road",
            city="Dhaka",
            phone="0123456789",
        )
        other_nursery = Nursery(
            owner=other_owner,
            name="Other Nursery",
            address="2 Garden Road",
            city="Dhaka",
            phone="0123456788",
        )
        plant = Plant(
            nursery=nursery,
            name="Monstera",
            category="Indoor",
            available_quantity=1,
        )
        other_plant = Plant(
            nursery=other_nursery,
            name="Fern",
            category="Indoor",
            available_quantity=1,
        )
        session.add_all([owner, other_owner, customer, unrelated_customer, plant, other_plant])
        session.flush()
        order = Order(
            user_id=customer.id,
            total_amount=10,
            status="Completed",
            items=[
                OrderItem(
                    plant_id=plant.id,
                    quantity=1,
                    unit_price=10,
                    total_price=10,
                )
            ],
        )
        session.add(order)
        session.add_all(
            [
                MaintenanceRequest(
                    user_id=customer.id,
                    plant_name=plant.name,
                    request_type="watering",
                    description="Please inspect the leaves and soil.",
                    preferred_date=date.today() + timedelta(days=2),
                ),
                MaintenanceRequest(
                    user_id=unrelated_customer.id,
                    plant_name=plant.name,
                    request_type="pruning",
                    description="This unrelated record must remain private.",
                ),
            ]
        )
        session.commit()
        current_user["user"] = SimpleNamespace(
            id=owner.id, role=SimpleNamespace(role_name="Nursery")
        )
        ids = {
            "owner": owner.id,
            "other_owner": other_owner.id,
            "customer": customer.id,
            "plant": plant.id,
            "nursery": nursery.id,
        }

    with TestClient(app) as client:
        yield client, current_user, ids, testing_session

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_owner_records_are_limited_to_ordered_plants_and_customer(maintenance_client):
    client, current_user, ids, _ = maintenance_client

    plants = client.get("/api/v1/maintenance/owner/plant-customers")
    assert plants.status_code == 200
    assert plants.json() == [
        {
            "plant_id": ids["plant"],
            "plant_name": "Monstera",
            "customer_id": ids["customer"],
            "customer_name": "Customer",
        }
    ]

    records = client.get("/api/v1/maintenance/owner/records")
    assert records.status_code == 200
    assert len(records.json()) == 1
    assert records.json()[0]["status"] == "scheduled"

    current_user["user"] = SimpleNamespace(
        id=ids["other_owner"], role=SimpleNamespace(role_name="Nursery")
    )
    assert client.get("/api/v1/maintenance/owner/records").json() == []
    assert client.patch(
        f"/api/v1/maintenance/owner/records/{records.json()[0]['id']}",
        json={"status": "completed"},
    ).status_code == 404


def test_user_request_is_associated_with_selected_nursery_and_visible_to_owner(
    maintenance_client,
):
    client, current_user, ids, testing_session = maintenance_client
    current_user["user"] = SimpleNamespace(
        id=ids["customer"], role=SimpleNamespace(role_name="User")
    )
    created = client.post(
        "/api/v1/maintenance/requests",
        json={
            "nursery_id": ids["nursery"],
            "request_type": "pest_control",
            "description": "Please inspect this plant for pests.",
        },
    )
    assert created.status_code == 201
    request_id = created.json()["id"]
    assert created.json()["nursery_id"] == ids["nursery"]

    created_by_name = client.post(
        "/api/v1/maintenance/requests",
        json={
            "nursery_name": "Owner Nursery",
            "request_type": "watering",
            "description": "Please check the soil moisture.",
        },
    )
    assert created_by_name.status_code == 201
    assert created_by_name.json()["nursery_id"] == ids["nursery"]

    with testing_session() as session:
        request = session.get(MaintenanceRequest, request_id)
        assert request.nursery_id == ids["nursery"]
        assert request.plant_name is None
        name_request = session.get(MaintenanceRequest, created_by_name.json()["id"])
        assert name_request.nursery_id == ids["nursery"]

    current_user["user"] = SimpleNamespace(
        id=ids["owner"], role=SimpleNamespace(role_name="Nursery")
    )
    records = client.get("/api/v1/maintenance/owner/records")
    assert records.status_code == 200
    assert {
        request_id,
        created_by_name.json()["id"],
    }.issubset({record["id"] for record in records.json()})
    matching = next(record for record in records.json() if record["id"] == request_id)
    assert matching["plant_id"] is None
    assert matching["status"] == "pending"


def test_owner_can_schedule_and_update_records_visible_in_customer_history(maintenance_client):
    client, current_user, ids, testing_session = maintenance_client
    scheduled_date = (date.today() + timedelta(days=4)).isoformat()
    created = client.post(
        "/api/v1/maintenance/owner/records",
        json={
            "plant_id": ids["plant"],
            "customer_id": ids["customer"],
            "request_type": "fertilizing",
            "description": "Apply the seasonal fertilizer carefully.",
            "preferred_date": scheduled_date,
        },
    )
    assert created.status_code == 201
    assert created.json()["status"] == "scheduled"

    request_id = created.json()["id"]
    in_progress = client.patch(
        f"/api/v1/maintenance/owner/records/{request_id}",
        json={"status": "in_progress", "response_note": "Work has started."},
    )
    assert in_progress.status_code == 200
    assert in_progress.json()["status"] == "in_progress"

    completed = client.patch(
        f"/api/v1/maintenance/owner/records/{request_id}",
        json={"status": "completed"},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    current_user["user"] = SimpleNamespace(
        id=ids["customer"], role=SimpleNamespace(role_name="User")
    )
    history = client.get("/api/v1/maintenance/requests/my")
    assert history.status_code == 200
    assert any(record["id"] == request_id for record in history.json())

    with testing_session() as session:
        assert session.get(MaintenanceRequest, request_id).status == "resolved"


def test_owner_cannot_create_records_for_unassociated_customers(maintenance_client):
    client, _, ids, _ = maintenance_client
    response = client.post(
        "/api/v1/maintenance/owner/records",
        json={
            "plant_id": ids["plant"],
            "customer_id": ids["other_owner"],
            "request_type": "watering",
            "description": "Water and inspect this plant weekly.",
        },
    )
    assert response.status_code == 404


def test_customers_cannot_access_nursery_maintenance_management(maintenance_client):
    client, current_user, ids, _ = maintenance_client
    current_user["user"] = SimpleNamespace(
        id=ids["customer"], role=SimpleNamespace(role_name="User")
    )

    assert client.get("/api/v1/maintenance/owner/records").status_code == 403
    assert client.post("/api/v1/maintenance/owner/records", json={}).status_code == 403