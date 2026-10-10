from sqlalchemy import ForeignKey, Integer, String, Text, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class Plant(TimestampMixin, Base):
    __tablename__ = "plants"
    __table_args__ = (
        UniqueConstraint(
            "nursery_id",
            "name",
            name="uq_plants_nursery_name",
        ),
        {'extend_existing': True}
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    nursery_id: Mapped[int] = mapped_column(
        ForeignKey(
            "nurseries.id",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(150), nullable=False
    )

    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )

    size: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )

    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    buy_price: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )

    rent_price: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )

    available_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    availability_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="unavailable",
        server_default="unavailable",
    )

    care_instructions: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    image_url: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    nursery = relationship(
        "Nursery",
        back_populates="plants",
    )