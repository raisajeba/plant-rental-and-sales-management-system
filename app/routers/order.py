from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies.auth import get_current_user  # Your auth dependency
from app.schemas.order import OrderOut
from app.crud.order import create_purchase_order_from_cart

router = APIRouter(
    prefix="/orders",
    tags=["Orders"]
)

@router.post("/checkout", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def checkout_cart(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return create_purchase_order_from_cart(db=db, user_id=current_user.id)