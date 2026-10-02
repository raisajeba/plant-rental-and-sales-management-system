"""SQLAlchemy engine, session factory, declarative Base, and FastAPI dependency."""
import logging
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

# URL.create() escapes special characters in the password safely.
DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=settings.DB_USER,
    password=settings.DB_PASSWORD,
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    database=settings.DB_NAME,
    query={"charset": "utf8mb4"},
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # drop dead connections automatically
    pool_recycle=3600,    # avoid MySQL "gone away" on idle connections
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request, always closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()  # never leave a half-finished transaction behind
        raise
    finally:
        db.close()


def check_db_connection() -> bool:
    """Used at startup and by /health. Logs the error type only, never credentials."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Database connection failed (%s)", type(exc).__name__)
        return False