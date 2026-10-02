from sqlalchemy import CheckConstraint, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import TimestampMixin


class ContactMessage(TimestampMixin, Base):
    """Message sent from the public Contact Us form."""

    __tablename__ = "contact_messages"
    __table_args__ = (
        CheckConstraint("status IN ('new', 'read', 'resolved')", name="ck_contact_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(150), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="new", server_default="new"
    )