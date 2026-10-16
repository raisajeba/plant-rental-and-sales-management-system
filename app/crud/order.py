from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.core.constants import ListingApprovalStatus
from app.models.plant import Plant
from app.models.cart_item import CartItem
from app.models.order import Order, OrderItem, RentalOrder
from app.schemas.order import OrderStatus


def create_purchase_order_from_cart(db: Session, user_id: int) -> Order:
    # 1. Validate Cart
    cart_items = db.query(CartItem).filter(CartItem.user_id == user_id).all()
    if not cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your cart is empty. Add plants before placing an order."
        )

    order_items_to_create = []
    total_order_amount = 0.0

    # 2. Check Plant Availability and Calculate Amounts
    for cart_item in cart_items:
        plant = db.query(Plant).filter(Plant.id == cart_item.plant_id).with_for_update().first()
        
        if not plant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plant with ID {cart_item.plant_id} not found."
            )
        if plant.approval_status != ListingApprovalStatus.APPROVED.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plant with ID {cart_item.plant_id} not found."
            )

        if cart_item.quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid quantity for plant '{plant.name}'."
            )

        # Check stock & status
        if (
            plant.available_quantity < cart_item.quantity 
            or plant.availability_status.lower() in ["out of stock", "unavailable"]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Plant '{plant.name}' is out of stock or requested quantity exceeds available stock."
            )

        # Calculate Price
        unit_price = float(plant.buy_price) if plant.buy_price is not None else 0.0
        item_total = unit_price * cart_item.quantity
        total_order_amount += item_total

        # 3. Deduct Plant Quantity & Update Status
        plant.available_quantity -= cart_item.quantity
        if plant.available_quantity == 0:
            plant.availability_status = "unavailable"

        order_items_to_create.append(
            OrderItem(
                plant_id=plant.id,
                quantity=cart_item.quantity,
                unit_price=unit_price,
                total_price=item_total
            )
        )

    # 4. Create Purchase Order
    new_order = Order(
        user_id=user_id,
        total_amount=total_order_amount,
        status=OrderStatus.PENDING,
        items=order_items_to_create
    )

    db.add(new_order)

    # Clear Cart Items after order creation
    db.query(CartItem).filter(CartItem.user_id == user_id).delete()

    db.commit()
    db.refresh(new_order)

    return new_order


def create_rental_order(
    db: Session,
    *,
    user_id: int,
    plant_id: int,
    quantity: int,
    rental_months: int,
) -> RentalOrder:
    plant = (
        db.query(Plant)
        .filter(Plant.id == plant_id)
        .with_for_update()
        .first()
    )
    if (
        plant is None
        or plant.approval_status != ListingApprovalStatus.APPROVED.value
        or plant.nursery.status != "active"
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plant not found",
        )
    if (
        plant.rent_price is None
        or plant.rent_price <= 0
        or plant.availability_status not in ("available_for_rent", "available_for_both")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This plant is not available for rent",
        )
    if plant.available_quantity < quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Requested quantity exceeds available stock",
        )

    rental_order = RentalOrder(
        user_id=user_id,
        plant_id=plant.id,
        quantity=quantity,
        rental_months=rental_months,
        total_amount=float(plant.rent_price) * quantity * rental_months,
        status="Pending",
    )
    db.add(rental_order)
    db.commit()
    db.refresh(rental_order)
    return rental_order