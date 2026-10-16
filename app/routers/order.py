from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from app.core.constants import RoleName
from app.database import get_db
from app.dependencies.auth import require_roles
from app.models import Nursery, Order, OrderItem, Plant, RentalOrder, User
from app.schemas.order import (
    OrderHistoryItemOut,
    OrderHistoryOut,
    OrderOut,
    OrderStatusUpdate,
    OwnerOrderItemOut,
    OwnerOrderOut,
    RentalOrderCreate,
    RentalOrderOut,
)
from app.crud.order import create_purchase_order_from_cart, create_rental_order

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
    row = db.execute(
        _owner_order_query(current_user.id)
        .where(Order.id == order_id)
    ).unique().first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")

    order, customer_name = row
    order.status = payload.status.value
    db.commit()
    db.refresh(order)
    return _owner_order_output(order, customer_name, current_user.id)


@router.get("/my-orders", response_model=list[OrderHistoryOut])
def list_my_orders(
    current_user: User = Depends(require_roles(RoleName.USER)),
    db: Session = Depends(get_db),
):
    purchase_orders = db.scalars(
        select(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.plant))
        .where(Order.user_id == current_user.id)
    ).unique().all()
    rental_orders = db.scalars(
        select(RentalOrder)
        .options(joinedload(RentalOrder.plant))
        .where(RentalOrder.user_id == current_user.id)
    ).all()

    history = [
        OrderHistoryOut(
            id=order.id,
            order_type="Purchase",
            total_amount=order.total_amount,
            status=order.status,
            created_at=order.created_at,
            items=[
                OrderHistoryItemOut(
                    id=item.id,
                    plant_id=item.plant_id,
                    plant_name=item.plant.name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total_price=item.total_price,
                )
                for item in order.items
            ],
        )
        for order in purchase_orders
    ]
    history.extend(
        OrderHistoryOut(
            id=order.id,
            order_type="Rental",
            total_amount=order.total_amount,
            status=order.status,
            created_at=order.created_at,
            items=[
                OrderHistoryItemOut(
                    id=order.id,
                    plant_id=order.plant_id,
                    plant_name=order.plant.name,
                    quantity=order.quantity,
                    unit_price=float(order.plant.rent_price),
                    total_price=order.total_amount,
                    rental_months=order.rental_months,
                )
            ],
        )
        for order in rental_orders
    )
    return sorted(history, key=lambda order: order.created_at, reverse=True)


@router.post(
    "/rentals",
    response_model=RentalOrderOut,
    status_code=status.HTTP_201_CREATED,
)
def checkout_rental(
    payload: RentalOrderCreate,
    current_user: User = Depends(require_roles(RoleName.USER)),
    db: Session = Depends(get_db),
):
    return create_rental_order(
        db,
        user_id=current_user.id,
        plant_id=payload.plant_id,
        quantity=payload.quantity,
        rental_months=payload.rental_months,
    )


@router.get("/my-orders/{order_type}/{order_id}", response_model=OrderHistoryOut)
def get_my_order(
    order_type: str,
    order_id: int,
    current_user: User = Depends(require_roles(RoleName.USER)),
    db: Session = Depends(get_db),
):
    if order_type == "purchase":
        purchase_order = db.scalar(
            select(Order)
            .options(joinedload(Order.items).joinedload(OrderItem.plant))
            .where(Order.id == order_id, Order.user_id == current_user.id)
        )
        if purchase_order is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
        return OrderHistoryOut(
            id=purchase_order.id,
            order_type="Purchase",
            total_amount=purchase_order.total_amount,
            status=purchase_order.status,
            created_at=purchase_order.created_at,
            items=[
                OrderHistoryItemOut(
                    id=item.id,
                    plant_id=item.plant_id,
                    plant_name=item.plant.name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total_price=item.total_price,
                )
                for item in purchase_order.items
            ],
        )

    if order_type == "rental":
        rental_order = db.scalar(
            select(RentalOrder)
            .options(joinedload(RentalOrder.plant))
            .where(RentalOrder.id == order_id, RentalOrder.user_id == current_user.id)
        )
        if rental_order is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
        return OrderHistoryOut(
            id=rental_order.id,
            order_type="Rental",
            total_amount=rental_order.total_amount,
            status=rental_order.status,
            created_at=rental_order.created_at,
            items=[
                OrderHistoryItemOut(
                    id=rental_order.id,
                    plant_id=rental_order.plant_id,
                    plant_name=rental_order.plant.name,
                    quantity=rental_order.quantity,
                    unit_price=float(rental_order.plant.rent_price),
                    total_price=rental_order.total_amount,
                    rental_months=rental_order.rental_months,
                )
            ],
        )
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")