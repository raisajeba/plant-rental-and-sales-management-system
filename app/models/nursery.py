from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class Nursery(TimestampMixin, Base):
    __tablename__ = "nurseries"
    __table_args__ = (
        UniqueConstraint("owner_id", "name", name="uq_nurseries_owner_name"),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    owner_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(150), nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    address: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    city: Mapped[str] = mapped_column(
        String(100), nullable=False
    )

    phone: Mapped[str] = mapped_column(
        String(30), nullable=False
    )

    email: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    image_url: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
    )

    owner = relationship("User")

    plants = relationship(
        "Plant",
        back_populates="nursery",
        cascade="all, delete-orphan",
    )