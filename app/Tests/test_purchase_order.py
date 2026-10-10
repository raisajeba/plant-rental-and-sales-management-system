import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.core.constants import AvailabilityStatus
from app.models import Nursery, OrderStatus, Plant, PurchaseOrder, Role, User


def create_user_and_plant(db_session, suffix=""):
    role = Role(role_name=f"User{suffix}")
    user = User(
        name="Test User",
        email=f"test{suffix}@example.com",
        password="hashed-password",
        role=role,
    )
    nursery_role = Role(role_name=f"Nursery{suffix}")
    nursery_owner = User(
        name="Nursery Owner",
        email=f"nursery{suffix}@example.com",
        password="hashed-password",
        role=nursery_role,
    )
    nursery = Nursery(
        owner=nursery_owner,
        name=f"Test Nursery{suffix}",
        address="12 Garden Road",
        city="Dhaka",
        phone="0123456789",
    )
    plant = Plant(
        nursery=nursery,
        name=f"Orchid{suffix}",
        category="Indoor",
        buy_price=15.0,
        available_quantity=10,
        availability_status=AvailabilityStatus.FOR_SALE.value,
    )
    db_session.add_all([user, plant])
    db_session.commit()
    return user, plant


def test_create_and_retrieve_purchase_order(db_session):
    user, plant = create_user_and_plant(db_session)
    # Create Purchase Order
    order = PurchaseOrder(
        user_id=user.id,
        plant_id=plant.id,
        quantity=2,
        total_amount=30.0,
        order_status=OrderStatus.PENDING
    )
    db_session.add(order)
    db_session.commit()

    # Retrieve & Assert
    retrieved_order = db_session.query(PurchaseOrder).filter_by(order_id=order.order_id).first()
    assert retrieved_order is not None
    assert retrieved_order.quantity == 2
    assert retrieved_order.total_amount == 30.0
    assert retrieved_order.order_status == OrderStatus.PENDING
    assert isinstance(retrieved_order.order_date, datetime)
    assert retrieved_order.user.id == user.id
    assert retrieved_order.plant.id == plant.id
    assert retrieved_order in user.purchase_orders
    assert retrieved_order in plant.purchase_orders

def test_positive_quantity_constraint(db_session):
    user, plant = create_user_and_plant(db_session)

    # Invalid Quantity (<= 0)
    invalid_order = PurchaseOrder(
        user_id=user.id,
        plant_id=plant.id,
        quantity=0,
        total_amount=10.0
    )
    db_session.add(invalid_order)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

def test_invalid_foreign_key_user(db_session):
    _, plant = create_user_and_plant(db_session)

    # Invalid User ID reference
    invalid_order = PurchaseOrder(
        user_id=99999,  # Non-existent user
        plant_id=plant.id,
        quantity=1,
        total_amount=10.0
    )
    db_session.add(invalid_order)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()