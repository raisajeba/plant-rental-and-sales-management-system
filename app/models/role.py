from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class Role(TimestampMixin, Base):
    """RBAC role: User, Nursery, Admin."""

    __tablename__ = "roles"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'inactive')", name="ck_roles_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", server_default="active"
    )

    # 1:N  Role -> Users
    users = relationship("User", back_populates="role")
    # N:N  Role <-> Page through the role_pages junction table
    page_links = relationship(
        "RolePage", back_populates="role", cascade="all, delete-orphan"
    ) 