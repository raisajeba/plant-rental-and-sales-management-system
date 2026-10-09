import os

os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.constants import AvailabilityStatus
from app.database import Base, get_db
from app.dependencies.auth import get_current_user
from app.models import Nursery, Plant
from app.routers.plants import router


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    def override_get_db():
        with TestingSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: object()

    with TestingSession() as session:
        active = Nursery(
            owner_id=1,
            name="Green Leaf Nursery",
            address="12 Garden Road",
            city="Dhaka",
            phone="0123456789",
            status="active",
        )
        inactive = Nursery(
            owner_id=1,
            name="Closed Nursery",
            address="34 Garden Road",
            city="Dhaka",
            phone="0123456789",
            status="inactive",
        )
        session.add_all([active, inactive])
        session.flush()
        session.add_all(
            [
                Plant(
                    nursery_id=active.id,
                    name="Golden Pothos",
                    category="Indoor",
                    available_quantity=5,
                    availability_status=AvailabilityStatus.FOR_SALE.value,
                ),
                Plant(
                    nursery_id=active.id,
                    name="Silver Pothos",
                    category="Indoor",
                    available_quantity=2,
                    availability_status=AvailabilityStatus.FOR_BOTH.value,
                ),
                Plant(
                    nursery_id=active.id,
                    name="Garden Rose",
                    category="Outdoor",
                    available_quantity=4,
                    availability_status=AvailabilityStatus.FOR_RENT.value,
                ),
                Plant(
                    nursery_id=active.id,
                    name="Unavailable Fern",
                    category="Indoor",
                    available_quantity=0,
                    availability_status=AvailabilityStatus.UNAVAILABLE.value,
                ),
                Plant(
                    nursery_id=inactive.id,
                    name="Closed Nursery Pothos",
                    category="Indoor",
                    available_quantity=5,
                    availability_status=AvailabilityStatus.FOR_SALE.value,
                ),
            ]
        )
        session.commit()
        active_nursery_id = active.id

    with TestClient(app) as test_client:
        yield test_client, active_nursery_id

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_search_supports_partial_name_and_returns_nursery(client):
    test_client, _ = client

    response = test_client.get("/api/v1/plants/search", params={"name": "poth"})

    assert response.status_code == 200
    assert [plant["name"] for plant in response.json()] == [
        "Golden Pothos",
        "Silver Pothos",
    ]
    assert response.json()[0]["nursery_name"] == "Green Leaf Nursery"


def test_search_combines_name_category_and_nursery(client):
    test_client, nursery_id = client

    response = test_client.get(
        "/api/v1/plants/search",
        params={
            "name": "poth",
            "category": "indoor",
            "nursery": "green leaf",
            "nursery_id": nursery_id,
        },
    )

    assert response.status_code == 200
    assert [plant["name"] for plant in response.json()] == [
        "Golden Pothos",
        "Silver Pothos",
    ]


def test_search_by_nursery_name(client):
    test_client, _ = client

    response = test_client.get(
        "/api/v1/plants/search",
        params={"nursery": "green leaf"},
    )

    assert response.status_code == 200
    assert [plant["name"] for plant in response.json()] == [
        "Garden Rose",
        "Golden Pothos",
        "Silver Pothos",
    ]


def test_search_filters_inactive_and_unavailable_listings(client):
    test_client, _ = client

    response = test_client.get("/api/v1/plants/search", params={"category": "Indoor"})

    assert response.status_code == 200
    assert [plant["name"] for plant in response.json()] == [
        "Golden Pothos",
        "Silver Pothos",
    ]


def test_search_returns_empty_list_when_no_plants_match(client):
    test_client, _ = client

    response = test_client.get(
        "/api/v1/plants/search",
        params={"name": "does not exist"},
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("params", [{}, {"name": "   "}])
def test_search_rejects_missing_or_blank_criteria(client, params):
    test_client, _ = client

    response = test_client.get("/api/v1/plants/search", params=params)

    assert response.status_code == 422


def test_search_validates_pagination(client):
    test_client, _ = client

    response = test_client.get(
        "/api/v1/plants/search",
        params={"name": "fern", "limit": 101},
    )

    assert response.status_code == 422


def test_search_paginates_results(client):
    test_client, _ = client

    response = test_client.get(
        "/api/v1/plants/search",
        params={"name": "poth", "skip": 1, "limit": 1},
    )

    assert response.status_code == 200
    assert [plant["name"] for plant in response.json()] == ["Silver Pothos"]
