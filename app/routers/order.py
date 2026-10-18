from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.constants import RoleName
from app.dependencies.auth import get_current_user, require_roles
from app.database import get_db
from app.models import Nursery, Order, OrderItem, Plant, User
from app.schemas.order import (
    OrderOut,
    OrderStatusUpdate,
    OwnerOrderItemOut,
    OwnerOrderOut,
)
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
    current_user: User = Depends(require_roles(RoleName.USER))
):
    return create_purchase_order_from_cart(db=db, user_id=current_user.id)


def _owner_order_query(owner_id: int):
    return (
        select(Order, User.name)
        .join(User, User.id == Order.user_id)
        .options(
            joinedload(Order.items)
            .joinedload(OrderItem.plant)
            .joinedload(Plant.nursery)
        )
        .where(
            Order.items.any(
                OrderItem.plant.has(
                    Plant.nursery.has(Nursery.owner_id == owner_id)
                )
            )
        )
    )


def _owner_order_output(
    order: Order,
    customer_name: str,
    owner_id: int,
) -> OwnerOrderOut:
    owner_items = [
        item
        for item in order.items
        if item.plant.nursery.owner_id == owner_id
    ]
    return OwnerOrderOut(
        id=order.id,
        customer_name=customer_name,
        total_price=sum(item.total_price for item in owner_items),
        status=order.status,
        order_date=order.created_at,
        items=[
            OwnerOrderItemOut(
                plant_id=item.plant_id,
                plant_name=item.plant.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
            )
            for item in owner_items
        ],
    )


@router.get("/owner", response_model=list[OwnerOrderOut])
def list_owner_orders(
    current_user: User = Depends(require_roles(RoleName.NURSERY)),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        _owner_order_query(current_user.id).order_by(
            Order.created_at.desc(), Order.id.desc()
        )
    ).unique().all()
    return [
        _owner_order_output(order, customer_name, current_user.id)
        for order, customer_name in rows
    ]


@router.get("/owner/{order_id}", response_model=OwnerOrderOut)
def get_owner_order(
    order_id: int,
    current_user: User = Depends(require_roles(RoleName.NURSERY)),
    db: Session = Depends(get_db),
):
    row = db.execute(
        _owner_order_query(current_user.id).where(Order.id == order_id)
    ).unique().first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    order, customer_name = row
    return _owner_order_output(order, customer_name, current_user.id)


@router.patch("/owner/{order_id}/status", response_model=OwnerOrderOut)
def update_owner_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    current_user: User = Depends(require_roles(RoleName.NURSERY)),
    db: Session = Depends(get_db),
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
