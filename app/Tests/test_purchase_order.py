import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.models.purchase_order import PurchaseOrder, OrderStatus
from app.models.plant import Plant
from app.models.user import User  # User model import 

def test_create_and_retrieve_purchase_order(db_session):
    # Setup test user and plant
    user = User(name="Test User", email="test@example.com")
    plant = Plant(name="Orchid", quantity=10, price=15.0)
    db_session.add_all([user, plant])
    db_session.commit()

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

def test_positive_quantity_constraint(db_session):
    user = User(name="Test User 2", email="test2@example.com")
    plant = Plant(name="Fern", quantity=5, price=10.0)
    db_session.add_all([user, plant])
    db_session.commit()

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
    plant = Plant(name="Bamboo", quantity=5, price=10.0)
    db_session.add(plant)
    db_session.commit()

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