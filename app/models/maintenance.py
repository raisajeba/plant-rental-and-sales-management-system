from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import TimestampMixin

_TASKS = "'watering','fertilizing','pruning','repotting','pest_control','other'"


class MaintenanceSchedule(TimestampMixin, Base):
    """A care task on a user's plant: WHEN (due_date) and HOW (instructions).
    plant_name is plain text for now.
    TODO (next sprint): add an optional plant_id FK once the Plant module exists.
    If frequency_days is set, completing the task creates the next one."""

    __tablename__ = "maintenance_schedules"
    __table_args__ = (
        CheckConstraint(f"task_type IN ({_TASKS})", name="ck_maint_sched_task"),
        CheckConstraint(
            "status IN ('pending', 'completed', 'skipped')", name="ck_maint_sched_status"
        ),
        CheckConstraint(
            "frequency_days IS NULL OR frequency_days > 0", name="ck_maint_sched_freq"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    plant_name: Mapped[str] = mapped_column(String(100), nullable=False)
    task_type: Mapped[str] = mapped_column(String(30), nullable=False)
    instructions: Mapped[str] = mapped_column(String(1000), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    frequency_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MaintenanceRequest(TimestampMixin, Base):
    """A help / service request submitted by a user."""

    __tablename__ = "maintenance_requests"
    __table_args__ = (
        CheckConstraint(f"request_type IN ({_TASKS})", name="ck_maint_req_type"),
        CheckConstraint(
            "status IN ('open', 'in_progress', 'resolved', 'cancelled')",
            name="ck_maint_req_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    plant_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    request_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    preferred_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open", server_default="open"
    )
    response_note: Mapped[str | None] = mapped_column(String(500), nullable=True)