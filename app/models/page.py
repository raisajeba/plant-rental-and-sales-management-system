from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class Page(TimestampMixin, Base):
    """A system page / menu item that roles can be granted access to."""

    __tablename__ = "pages"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'inactive')", name="ck_pages_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    page_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    page_url: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", server_default="active"
    )

    role_links = relationship(
        "RolePage", back_populates="page", cascade="all, delete-orphan"
    )