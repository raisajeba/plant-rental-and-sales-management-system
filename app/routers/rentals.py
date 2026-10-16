from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import SessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter(prefix="/rentals", tags=["Plant Rentals"])

@router.post("/", response_model=schemas.PlantRentalOrderResponse, status_code=status.HTTP_201_CREATED)
def create_rental_order(order: schemas.PlantRentalOrderCreate, db: Session = Depends(get_db)):
    # 1. Check if User exists
    user = db.query(models.User).filter(models.User.id == order.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {order.user_id} not found."
        )

    # 2. Check if Plant exists
    plant = db.query(models.Plant).filter(models.Plant.id == order.plant_id).first()
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plant with id {order.plant_id} not found."
        )

    # 3. Calculation: Duration
    duration_days = (order.rental_end_date - order.rental_start_date).days
    if duration_days <= 0:
        duration_days = 1

    # 4. Total Amount Calculation
    total_price = order.quantity * order.rental_price_per_day * duration_days

    # 5. Create Order Entry
    db_order = models.PlantRentalOrder(
        user_id=order.user_id,
        plant_id=order.plant_id,
        quantity=order.quantity,
        rental_start_date=order.rental_start_date,
        rental_end_date=order.rental_end_date,
        rental_duration_days=duration_days,
        rental_price_per_day=order.rental_price_per_day,
        total_amount=total_price,
        status=models.RentalStatus.PENDING
    )

    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order