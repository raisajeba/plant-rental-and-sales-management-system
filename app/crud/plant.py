from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.plant import Plant
from app.schemas.plant import PlantCreate, PlantUpdate
from app.core.constants import AvailabilityStatus

class CRUDPlant:
    def create_plant(self, db: Session, plant_in: PlantCreate, nursery_id: int) -> Plant:
        plant_data = plant_in.model_dump()
        db_plant = Plant(**plant_data, nursery_id=nursery_id)
        db.add(db_plant)
        db.commit()
        db.refresh(db_plant)
        return db_plant

    def get_plant_by_id(self, db: Session, plant_id: int) -> Optional[Plant]:
        return db.query(Plant).filter(Plant.id == plant_id).first()

    def get_plants(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 10,
        category: Optional[str] = None,
        only_available: bool = True
    ) -> List[Plant]:
        query = db.query(Plant)
        if only_available:
            query = query.filter(
                Plant.availability_status != AvailabilityStatus.UNAVAILABLE,
                Plant.available_quantity > 0
            )
        if category:
            query = query.filter(Plant.category == category)
        return query.offset(skip).limit(limit).all()

    def update_plant(self, db: Session, db_plant: Plant, plant_in: PlantUpdate) -> Plant:
        update_data = plant_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_plant, field, value)
        
        # Quantity ০ হয়ে গেলে আউটোমেটিক সংগতি রেখে AvailabilityStatus আপডেট করা
        if db_plant.available_quantity == 0:
            db_plant.availability_status = AvailabilityStatus.UNAVAILABLE

        db.add(db_plant)
        db.commit()
        db.refresh(db_plant)
        return db_plant

    def delete_plant(self, db: Session, db_plant: Plant) -> None:
        db.delete(db_plant)
        db.commit()

crud_plant = CRUDPlant()