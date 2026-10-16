from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.routers.cart import router as cart_router
from app.routers.maintenance import router as maintenance_router
from app.routers.nurseries import router as nurseries_router
from app.routers.plants import router as plants_router


class EmptyDB:
    def all(self):
        return []

    def execute(self, *_):
        return self

    def scalars(self, *_):
        return self


@pytest.fixture
def role_client():
    app = FastAPI()
    for router in (cart_router, maintenance_router, nurseries_router, plants_router):
        app.include_router(router, prefix="/api/v1")

    user = SimpleNamespace(id=1, role=SimpleNamespace(role_name="User"))
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = EmptyDB

    with TestClient(app) as client:
        yield client, user

    app.dependency_overrides.clear()


def test_customer_can_use_customer_routes_but_not_nursery_management(role_client):
    client, _ = role_client

    assert client.get("/api/v1/plants").status_code == 200
    assert client.get("/api/v1/maintenance/care-guide").status_code == 200
    assert client.get("/api/v1/nurseries/mine").status_code == 403
    assert client.get("/api/v1/nurseries/mine/plants").status_code == 403
    assert client.post(
        "/api/v1/nurseries",
        json={
            "name": "Customer Nursery",
            "address": "12 Garden Road",
            "city": "Dhaka",
            "phone": "0123456789",
        },
    ).status_code == 403
    assert client.put(
        "/api/v1/plants/1",
        json={"name": "Updated Plant"},
    ).status_code == 403


def test_nursery_owner_can_use_nursery_routes_but_not_customer_routes(role_client):
    client, user = role_client
    user.role.role_name = "Nursery"

    assert client.get("/api/v1/nurseries/mine").status_code == 200
    assert client.get("/api/v1/nurseries/mine/plants").status_code == 200
    assert client.get("/api/v1/plants").status_code == 403
    assert client.get("/api/v1/cart/items").status_code == 403
    assert client.get("/api/v1/maintenance/care-guide").status_code == 403
