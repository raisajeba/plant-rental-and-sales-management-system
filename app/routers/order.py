import logging
from collections.abc import Mapping
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.constants import RoleName
from app.dependencies.auth import get_current_user, require_roles
from app.database import get_db
from app.models import (
    Nursery,
    Order,
    OrderItem,
    Plant,
    PlantRentalOrder,
    RentalOrder,
    User,
)
from app.schemas.order import (
    CustomerOrderHistoryOut,
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
nursery_sell_orders_router = APIRouter(prefix="/nursery", tags=["Nursery Orders"])
logger = logging.getLogger(__name__)


@router.post("/checkout", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def checkout_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.USER))
):
    return create_purchase_order_from_cart(db=db, user_id=current_user.id)


def _purchase_history(order: Order) -> dict:
    return {
        "id": order.id,
        "order_type": "Purchase",
        "total_amount": order.total_amount,
        "status": order.status,
        "payment_status": order.payment_status,
        "created_at": order.created_at,
        "items": [
            {
                "plant_id": item.plant_id,
                "plant_name": item.plant.name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_price": item.total_price,
            }
            for item in order.items
        ],
    }


def _legacy_rental_history(rental: RentalOrder) -> dict:
    return {
        "id": rental.id,
        "order_type": "Rental",
        "total_amount": rental.total_amount,
        "status": rental.status,
        "payment_status": "Pending",
        "created_at": rental.created_at,
        "items": [
            {
                "plant_id": rental.plant_id,
                "plant_name": rental.plant.name,
                "quantity": rental.quantity,
                "unit_price": rental.total_amount / rental.quantity,
                "total_price": rental.total_amount,
                "rental_months": rental.rental_months,
            }
        ],
    }


def _plant_rental_history(rental: Mapping[str, object]) -> dict:
    return {
        "id": rental["rental_id"],
        "order_type": "Rent",
        "total_amount": rental["total_amount"],
        "status": getattr(rental["status"], "value", rental["status"]),
        "payment_status": rental["payment_status"],
        "created_at": rental["created_at"],
        "items": [
            {
                "plant_id": rental["plant_id"],
                "plant_name": rental["plant_name"],
                "quantity": rental["quantity"],
                "unit_price": rental["rental_price_per_day"],
                "total_price": rental["total_amount"],
                "rental_duration_days": rental["rental_duration_days"],
            }
        ],
    }


def _plant_rental_history_query():
    return (
        select(
            PlantRentalOrder.rental_id,
            PlantRentalOrder.plant_id,
            PlantRentalOrder.quantity,
            PlantRentalOrder.rental_duration_days,
            PlantRentalOrder.rental_price_per_day,
            PlantRentalOrder.total_amount,
            PlantRentalOrder.payment_status,
            PlantRentalOrder.status,
            PlantRentalOrder.created_at,
            Plant.name.label("plant_name"),
        )
        .join(Plant, Plant.id == PlantRentalOrder.plant_id)
    )


@router.get(
    "/my-orders",
    response_model=list[CustomerOrderHistoryOut],
    status_code=status.HTTP_200_OK,
)
def list_my_orders(
    current_user: User = Depends(require_roles(RoleName.USER)),
    db: Session = Depends(get_db),
):
    try:
        purchases = db.scalars(
            select(Order)
            .options(joinedload(Order.items).joinedload(OrderItem.plant))
            .where(Order.user_id == current_user.id)
        ).unique().all()
        legacy_rentals = db.scalars(
            select(RentalOrder)
            .options(joinedload(RentalOrder.plant))
            .where(RentalOrder.user_id == current_user.id)
        ).unique().all()
        rentals = db.execute(
            _plant_rental_history_query().where(
                PlantRentalOrder.user_id == current_user.id
            )
        ).mappings().all()
        history = [
            *(_purchase_history(order) for order in purchases),
            *(_legacy_rental_history(rental) for rental in legacy_rentals),
            *(_plant_rental_history(rental) for rental in rentals),
        ]
        if not history:
            return []
        return sorted(
            history,
            key=lambda item: item["created_at"].isoformat(),
            reverse=True,
        )
    except Exception:
        logger.exception("Failed to fetch order history for user_id=%s", current_user.id)
        raise


@router.get("/my-orders/{order_type}/{order_id}")
def get_my_order_details(
    order_type: str,
    order_id: int,
    current_user: User = Depends(require_roles(RoleName.USER)),
    db: Session = Depends(get_db),
):
    if order_type == "purchase":
        order = db.scalar(
            select(Order)
            .options(joinedload(Order.items).joinedload(OrderItem.plant))
            .where(Order.id == order_id, Order.user_id == current_user.id)
        )
        if order is not None:
            return _purchase_history(order)
    elif order_type == "rental":
        legacy_rental = db.scalar(
            select(RentalOrder)
            .options(joinedload(RentalOrder.plant))
            .where(RentalOrder.id == order_id, RentalOrder.user_id == current_user.id)
        )
        if legacy_rental is not None:
            return _legacy_rental_history(legacy_rental)
        rental = db.execute(
            _plant_rental_history_query()
            .where(
                PlantRentalOrder.rental_id == order_id,
                PlantRentalOrder.user_id == current_user.id,
            )
        ).mappings().first()
        if rental is not None:
            return _plant_rental_history(rental)
    elif order_type == "rent":
        rental = db.execute(
            _plant_rental_history_query()
            .where(
                PlantRentalOrder.rental_id == order_id,
                PlantRentalOrder.user_id == current_user.id,
            )
        ).mappings().first()
        if rental is not None:
            return _plant_rental_history(rental)
    else:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")


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
            or_(
                func.lower(Order.payment_status) == "paid",
                and_(
                    func.lower(Order.payment_status) == "cod",
                    Order.status != "Cancelled",
                ),
            ),
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
        payment_status=order.payment_status,
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
@nursery_sell_orders_router.get("/sell-orders", response_model=list[OwnerOrderOut])
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
    row = db.execute(
        _owner_order_query(current_user.id).where(Order.id == order_id)
    ).unique().first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    order, customer_name = row
    updated_order = update_order_status(db=db, order=order, new_status=payload.status)
    return _owner_order_output(updated_order, customer_name, current_user.id)


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
