from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.sql import func

from app.database import Base


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    __table_args__ = (
        CheckConstraint(
            "order_type IN ('purchase', 'rental')",
            name="ck_payment_transactions_order_type",
        ),
        CheckConstraint(
            "status IN ('Pending', 'Paid', 'Failed', 'Cancelled')",
            name="ck_payment_transactions_status",
        ),
        Index("ix_payment_transactions_order", "order_type", "order_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(64), nullable=False, unique=True, index=True)
    order_type = Column(String(16), nullable=False)
    order_id = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="BDT", server_default="BDT")
    status = Column(String(20), nullable=False, default="Pending", server_default="Pending")
    validation_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
