from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.constants import AvailabilityStatus
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models import CartItem, Plant, User
from app.schemas.cart import CartItemCreate, CartItemOut, CartItemUpdate

router = APIRouter(prefix="/cart", tags=["Cart"])

_SALE_STATUSES = {
    AvailabilityStatus.FOR_SALE.value,
    AvailabilityStatus.FOR_BOTH.value,
}


@router.get("/items", response_model=list[CartItemOut])
def get_cart_items(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    statement = (
        select(CartItem)
        .options(joinedload(CartItem.plant))
        .where(CartItem.user_id == user.id)
        .order_by(CartItem.created_at, CartItem.id)
    )
    return db.scalars(statement).all()


@router.post(
    "/items",
    response_model=CartItemOut,
    status_code=status.HTTP_201_CREATED,
)
def add_cart_item(
    payload: CartItemCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plant = db.scalar(
        select(Plant).where(Plant.id == payload.plant_id).with_for_update()
    )
    if plant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")
    if plant.nursery.status != "active":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This plant is not currently available.",
        )
    if plant.availability_status not in _SALE_STATUSES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This plant is not currently available for sale.",
        )
    if plant.available_quantity <= 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This plant is currently out of stock.",
        )
    if plant.buy_price is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This plant is not currently available for sale.",
        )

    cart_item = db.scalar(
        select(CartItem)
        .where(
            CartItem.user_id == user.id,
            CartItem.plant_id == plant.id,
        )
        .with_for_update()
    )
    updated_quantity = payload.quantity + (cart_item.quantity if cart_item else 0)
    if updated_quantity > plant.available_quantity:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            (
                f"Requested cart quantity ({updated_quantity}) exceeds "
                f"available stock ({plant.available_quantity})."
            ),
        )

    if cart_item is None:
        cart_item = CartItem(
            user_id=user.id,
            plant_id=plant.id,
            quantity=payload.quantity,
            plant=plant,
        )
        db.add(cart_item)
    else:
        cart_item.quantity = updated_quantity

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The cart item could not be updated because it changed concurrently. Please retry.",
        ) from exc

    db.refresh(cart_item)
    return cart_item


@router.patch("/items/{cart_item_id}", response_model=CartItemOut)
def update_cart_item_quantity(
    cart_item_id: int,
    payload: CartItemUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cart_item = db.scalar(
        select(CartItem)
        .where(CartItem.id == cart_item_id, CartItem.user_id == user.id)
    )
    if cart_item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cart item not found")

    plant = db.scalar(
        select(Plant)
        .where(Plant.id == cart_item.plant_id)
        .with_for_update()
    )
    if plant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")
    if plant.nursery.status != "active" or plant.availability_status not in _SALE_STATUSES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This plant is not currently available for sale.",
        )
    if plant.buy_price is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This plant is not currently available for sale.",
        )
    cart_item = db.scalar(
        select(CartItem)
        .where(CartItem.id == cart_item_id, CartItem.user_id == user.id)
        .with_for_update()
    )
    if cart_item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cart item not found")
    if payload.quantity > plant.available_quantity:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            (
                f"Requested cart quantity ({payload.quantity}) exceeds "
                f"available stock ({plant.available_quantity})."
            ),
        )

    cart_item.quantity = payload.quantity
    db.commit()
    db.refresh(cart_item)
    return cart_item
