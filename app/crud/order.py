from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.plant import Plant
from app.models.cart import Cart, CartItem
from app.models.order import Order, OrderItem
from app.schemas.order import OrderStatus


def create_purchase_order_from_cart(db: Session, user_id: int) -> Order:
    # 1. Validate Cart
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if not cart or not cart.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your cart is empty. Add plants before placing an order."
        )

    order_items_to_create = []
    total_order_amount = 0.0

    # 2. Check Plant Availability and Calculate Amounts
    for cart_item in cart.items:
        plant = db.query(Plant).filter(Plant.id == cart_item.plant_id).with_for_update().first()
        
        if not plant:
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
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()

    db.commit()
    db.refresh(new_order)

    return new_order