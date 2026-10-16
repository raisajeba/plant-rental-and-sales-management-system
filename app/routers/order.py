from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user  # Your auth dependency
from app.schemas.order import OrderOut, OrderStatusUpdate
from app.crud.order import (
    create_purchase_order_from_cart,
    get_orders_for_nursery_owner,
    get_order_by_id_for_owner,
    update_order_status
)

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


@router.get("/nursery", response_model=List[OrderOut])
def view_nursery_owner_orders(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Allow nursery owners to view current status of purchase orders
    related to plants from their nursery.
    """
    return get_orders_for_nursery_owner(db=db, owner_id=current_user.id)


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_nursery_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Allow nursery owners to update status of purchase orders for their plants.
    - Validates predefined order statuses (Pending, Confirmed, Processing, Completed, Cancelled).
    - Access Control: Prevents unauthorized updates on orders not belonging to their plants.
    """
    order = get_order_by_id_for_owner(db=db, order_id=order_id, owner_id=current_user.id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or you are not authorized to update this order status."
        )

    return update_order_status(db=db, order=order, new_status=status_update.status)