from datetime import date, datetime
from decimal import Decimal
import pytest
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.dependencies.auth import get_current_user
from app.models import (
    Nursery,
    Order,
    OrderItem,
    PaymentTransaction,
    Plant,
    PlantRentalOrder,
    Role,
    User,
)
from app.routers import payment


@pytest.fixture
def payment_client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    role = Role(role_name="User")
    customer = User(
        name="Payment Customer",
        email="payment.customer@example.com",
        password="test-hash",
        role=role,
    )
    with testing_session() as db:
        db.add(customer)
        db.flush()
        nursery = Nursery(
            owner=customer,
            name="Payment Test Nursery",
            address="12 Green Road",
            city="Dhaka",
            phone="01700000000",
        )
        plant = Plant(
            nursery=nursery,
            name="Payment Plant",
            category="Indoor",
            buy_price=100,
            rent_price=10,
            available_quantity=4,
            availability_status="available_for_both",
        )
        db.add(plant)
        db.flush()
        order = Order(
            user_id=customer.id,
            total_amount=100,
            status="Pending",
            payment_status="Pending",
            created_at=datetime(2026, 1, 1),
            items=[
                OrderItem(
                    plant_id=plant.id,
                    quantity=1,
                    unit_price=100,
                    total_price=100,
                )
            ],
        )
        db.add(order)
        rental = PlantRentalOrder(
            user_id=customer.id,
            plant_id=plant.id,
            quantity=1,
            rental_start_date=date(2026, 1, 1),
            rental_end_date=date(2026, 1, 2),
            rental_duration_days=1,
            rental_price_per_day=Decimal("10.00"),
            total_amount=Decimal("10.00"),
            status="Pending",
        )
        db.add(rental)
        db.commit()
        order_id = order.id
        rental_id = rental.rental_id
        user_id = customer.id

    app = FastAPI()
    app.include_router(payment.router, prefix="/api/v1")

    def override_get_db():
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: customer
    monkeypatch.setattr(payment.settings, "SSLCOMMERZ_STORE_ID", "sandbox-store")
    monkeypatch.setattr(payment.settings, "SSLCOMMERZ_STORE_PASSWORD", "sandbox-secret")
    monkeypatch.setattr(payment.settings, "PUBLIC_BASE_URL", "http://testserver")

    with TestClient(app, follow_redirects=False) as client:
        yield client, testing_session, order_id, rental_id, user_id

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_initiation_uses_saved_order_total_and_persists_attempt(payment_client, monkeypatch):
    client, testing_session, order_id, _, user_id = payment_client

    class GatewayResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "status": "SUCCESS",
                "GatewayPageURL": "https://sandbox.sslcommerz.com/gwprocess/checkout",
            }

    def fake_post(url, *, data, timeout, headers):
        assert url == "https://sandbox.sslcommerz.com/gwprocess/v4/api.php"
        assert data["store_id"] == "sandbox-store"
        assert data["store_passwd"] == "sandbox-secret"
        assert data["total_amount"] == "100.00"
        assert data["currency"] == "BDT"
        assert data["cus_name"] == "Payment Customer"
        assert data["cus_email"] == "payment.customer@example.com"
        assert data["cus_phone"] == "01700000000"
        assert headers["Content-Type"] == "application/x-www-form-urlencoded"
        return GatewayResponse()

    monkeypatch.setattr(payment.httpx, "post", fake_post)
    response = client.post(
        "/api/v1/payment/initiate",
        json={
            "order_type": "purchase",
            "order_id": order_id,
            "cart_items": [{"plant_id": 1, "quantity": 1}],
            "phone": "01700000000",
            "address": "12 Green Road",
            "city": "Dhaka",
            "postcode": "1200",
        },
    )

    assert response.status_code == 200
    assert response.json()["GatewayPageURL"].startswith("https://sandbox.sslcommerz.com/")
    with testing_session() as db:
        transaction = db.scalar(select(PaymentTransaction))
        order = db.get(Order, order_id)
        assert transaction.user_id == user_id
        assert transaction.amount == Decimal("100.00")
        assert order.payment_transaction_id == transaction.transaction_id
        assert order.payment_status == "PENDING"


def test_rental_initiation_uses_saved_rental_total(payment_client, monkeypatch):
    client, testing_session, _, rental_id, user_id = payment_client
    payment_data = {
        "order_type": "rental",
        "order_id": rental_id,
        "cart_items": [{"plant_id": 1, "quantity": 1}],
        "phone": "01700000000",
        "address": "12 Green Road",
        "city": "Dhaka",
        "postcode": "1200",
    }
    pending_response = client.post("/api/v1/payment/initiate", json=payment_data)
    assert pending_response.status_code == 409

    with testing_session() as db:
        db.get(PlantRentalOrder, rental_id).status = "Approved"
        db.commit()

    class GatewayResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "status": "SUCCESS",
                "GatewayPageURL": "https://sandbox.sslcommerz.com/gwprocess/checkout",
            }

    def fake_post(url, *, data, timeout, headers):
        assert data["total_amount"] == "10.00"
        return GatewayResponse()

    monkeypatch.setattr(payment.httpx, "post", fake_post)
    response = client.post(
        "/api/v1/payment/initiate",
        json=payment_data,
    )

    assert response.status_code == 200
    with testing_session() as db:
        rental = db.get(PlantRentalOrder, rental_id)
        transaction = db.scalar(select(PaymentTransaction))
        assert transaction.user_id == user_id
        assert transaction.order_type == "rental"
        assert rental.payment_transaction_id == transaction.transaction_id


def test_initiation_rejects_cart_items_that_do_not_match_saved_order(payment_client):
    client, _, order_id, _, _ = payment_client

    response = client.post(
        "/api/v1/payment/initiate",
        json={
            "order_type": "purchase",
            "order_id": order_id,
            "cart_items": [{"plant_id": 999, "quantity": 1}],
            "phone": "01700000000",
            "address": "12 Green Road",
            "city": "Dhaka",
            "postcode": "1200",
        },
    )

    assert response.status_code == 409


def test_initiation_logs_gateway_error_response_without_leaking_password(
    payment_client, monkeypatch, caplog
):
    client, testing_session, order_id, _, _ = payment_client

    monkeypatch.setattr(
        payment.httpx,
        "post",
        lambda *args, **kwargs: httpx.Response(
            200,
            json={
                "status": "FAILED",
                "code": "invalid_store",
                "failedreason": "Store credentials are invalid",
                "store_passwd": "sandbox-secret",
            },
            request=httpx.Request(
                "POST", "https://sandbox.sslcommerz.com/gwprocess/v4/api.php"
            ),
        ),
    )
    response = client.post(
        "/api/v1/payment/initiate",
        json={
            "order_type": "purchase",
            "order_id": order_id,
            "cart_items": [{"plant_id": 1, "quantity": 1}],
            "phone": "01700000000",
            "address": "12 Green Road",
            "city": "Dhaka",
            "postcode": "1200",
        },
    )

    assert response.status_code == 502
    assert '"failedreason":"Store credentials are invalid"' in caplog.text
    assert "[REDACTED]" in caplog.text
    assert "sandbox-secret" not in caplog.text
    with testing_session() as db:
        order = db.get(Order, order_id)
        transaction = db.scalar(select(PaymentTransaction))
        assert order.payment_status == "Failed"
        assert transaction.status == "Failed"


def test_success_callback_validates_transaction_before_marking_paid(
    payment_client, monkeypatch
):
    client, testing_session, order_id, _, user_id = payment_client
    transaction_id = "GN0123456789abcdef01234567"
    with testing_session() as db:
        transaction = PaymentTransaction(
            transaction_id=transaction_id,
            order_type="purchase",
            order_id=order_id,
            user_id=user_id,
            amount=Decimal("100.00"),
            currency="BDT",
            status="Pending",
        )
        order = db.get(Order, order_id)
        order.payment_transaction_id = transaction_id
        db.add(transaction)
        db.commit()

    monkeypatch.setattr(
        payment,
        "_validation_response",
        lambda validation_id, transaction: {
            "status": "VALID",
            "tran_id": transaction_id,
            "amount": "100.00",
            "currency": "BDT",
        },
    )
    response = client.post(
        "/api/v1/payment/success",
        data={"tran_id": transaction_id, "val_id": "gateway-validation-id"},
    )

    assert response.status_code == 303, response.text
    assert response.headers["location"].endswith(
        f"/customer-history.html?status=success&order_id={transaction_id}"
    )
    with testing_session() as db:
        assert db.get(Order, order_id).payment_status == "PAID"
        assert db.get(Order, order_id).status == "Processing"
        transaction = db.scalar(
            select(PaymentTransaction).where(
                PaymentTransaction.transaction_id == transaction_id
            )
        )
        assert transaction.status == "Paid"
        assert transaction.validation_id == "gateway-validation-id"


def test_fail_callback_updates_only_known_transaction(payment_client):
    client, testing_session, order_id, _, user_id = payment_client
    transaction_id = "GN0123456789abcdef01234567"
    with testing_session() as db:
        order = db.get(Order, order_id)
        order.payment_transaction_id = transaction_id
        db.add(
            PaymentTransaction(
                transaction_id=transaction_id,
                order_type="purchase",
                order_id=order_id,
                user_id=user_id,
                amount=Decimal("100.00"),
                currency="BDT",
                status="Pending",
            )
        )
        db.commit()

    response = client.post("/api/v1/payment/fail", data={"tran_id": transaction_id})

    assert response.status_code == 303, response.text
    assert response.headers["location"].endswith(
        f"/customer-history.html?status=error&order_id={transaction_id}"
    )
    with testing_session() as db:
        assert db.get(Order, order_id).payment_status == "FAILED"
        transaction = db.scalar(
            select(PaymentTransaction).where(
                PaymentTransaction.transaction_id == transaction_id
            )
        )
        assert transaction.status == "Failed"
