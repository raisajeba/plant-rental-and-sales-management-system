from app.core.constants import AvailabilityStatus
from app.models import Nursery, Plant, Role, User


def make_plant(db_session, *, name, quantity, availability):
    role = Role(role_name="Nursery")
    owner = User(
        name="Nursery Owner",
        email=f"{name.lower().replace(' ', '.')}@example.com",
        password="hashed-password",
        role=role,
    )
    nursery = Nursery(
        owner=owner,
        name=f"{name} Nursery",
        address="12 Garden Road",
        city="Dhaka",
        phone="0123456789",
    )
    plant = Plant(
        nursery=nursery,
        name=name,
        category="Indoor",
        available_quantity=quantity,
        availability_status=availability.value,
    )
    db_session.add(plant)
    db_session.commit()
    return plant


def test_available_stock_uses_active_plant_fields(db_session):
    plant = make_plant(
        db_session,
        name="Aloe Vera",
        quantity=1,
        availability=AvailabilityStatus.FOR_SALE,
    )

    plant.available_quantity -= 1
    plant.availability_status = AvailabilityStatus.UNAVAILABLE.value
    db_session.commit()
    db_session.refresh(plant)

    assert plant.available_quantity == 0
    assert plant.availability_status == AvailabilityStatus.UNAVAILABLE.value


def test_unavailable_plant_can_have_zero_stock(db_session):
    plant = make_plant(
        db_session,
        name="Cactus",
        quantity=0,
        availability=AvailabilityStatus.UNAVAILABLE,
    )

    assert plant.available_quantity == 0
    assert plant.availability_status == AvailabilityStatus.UNAVAILABLE.value