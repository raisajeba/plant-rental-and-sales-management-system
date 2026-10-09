import enum
from datetime import datetime
from sqlalchemy import Column, Integer, Float, DateTime, Enum, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from app.database import Base  

class OrderStatus(str, enum.Enum):
    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    # Primary Key
    order_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    plant_id = Column(Integer, ForeignKey("plants.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    # Required Fields & Constraints
    quantity = Column(Integer, nullable=False)
    total_amount = Column(Float, nullable=False)
    order_status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    order_date = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Table Validation Constraints (Positive Values)
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_quantity_positive'),
        CheckConstraint('total_amount > 0.0', name='check_total_amount_positive'),
    )

    # Relationships (Assumes 'User' and 'Plant' models exist)
    user = relationship("User", back_populates="purchase_orders")
    plant = relationship("Plant", back_populates="purchase_orders")