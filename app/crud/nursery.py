from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.nursery import Nursery
from app.schemas.nursery import NurseryUpdate


def get_nursery_by_id(db: Session, nursery_id: int) -> Nursery | None:
    return db.scalar(select(Nursery).where(Nursery.id == nursery_id))


def get_nursery_by_owner_id(db: Session, owner_id: int) -> Nursery | None:
    return db.scalar(select(Nursery).where(Nursery.owner_id == owner_id))


def update_nursery(db: Session, db_nursery: Nursery, nursery_in: NurseryUpdate) -> Nursery:
    update_data = nursery_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_nursery, field, value)

    db.add(db_nursery)
    db.commit()
    db.refresh(db_nursery)
    return db_nursery