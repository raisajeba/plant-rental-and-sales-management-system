import pytest
from models.plant import Plant, AvailabilityStatus
from services.plant_service import PlantStockService

def test_automatic_out_of_stock(db_session):
    plant = Plant(name="Aloe Vera", quantity=1)
    plant.update_availability_status()
    db_session.add(plant)
    db_session.commit()

    assert plant.availability_status == AvailabilityStatus.AVAILABLE

    # Deduct 1 item
    updated = PlantStockService.process_transaction(db_session, plant.id, 1)
    assert updated.quantity == 0
    assert updated.availability_status == AvailabilityStatus.OUT_OF_STOCK

def test_prevent_out_of_stock_purchase(db_session):
    plant = Plant(name="Cactus", quantity=0, availability_status=AvailabilityStatus.OUT_OF_STOCK)
    db_session.add(plant)
    db_session.commit()

    with pytest.raises(Exception):
        PlantStockService.process_transaction(db_session, plant.id, 1)