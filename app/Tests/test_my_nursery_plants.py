from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.dependencies.auth import get_current_user
from app.models import Nursery, Plant
from app.routers.nurseries import router


@pytest.fixture
def nursery_plants_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    owner = SimpleNamespace(
        id=1,
        role=SimpleNamespace(role_name="Nursery"),
    )

    def override_get_db():
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: owner

    with testing_session() as db:
        own_nursery = Nursery(
            owner_id=owner.id,
            name="Owner nursery",
            address="1 Garden Road",
            city="Dhaka",
            phone="01700000000",
        )
        other_nursery = Nursery(
            owner_id=2,
            name="Other nursery",
            address="2 Garden Road",
            city="Dhaka",
            phone="01800000000",
        )
        db.add_all([own_nursery, other_nursery])
        db.flush()
        db.add_all(
            [
                Plant(
                    nursery_id=own_nursery.id,
                    name="Owner plant",
                    category="Indoor",
                    available_quantity=1,
                ),
                Plant(
                    nursery_id=other_nursery.id,
                    name="Other nursery plant",
                    category="Indoor",
                    available_quantity=1,
                ),
            ]
        )
        db.commit()

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_my_plants_contains_only_listings_in_owned_nurseries(nursery_plants_client):
    response = nursery_plants_client.get("/api/v1/nurseries/mine/plants")

    assert response.status_code == 200
    assert [plant["name"] for plant in response.json()] == ["Owner plant"]
