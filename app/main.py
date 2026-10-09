"""FastAPI entry point."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import OperationalError, SQLAlchemyError

import app.models  # noqa: F401
from app.core.config import settings
from app.database import Base, SessionLocal, check_db_connection, engine
from app.routers import (
    about,
    auth,
    cart,
    contact,
    maintenance,
    nurseries,
    pages,
    placeholders,
    plants,
    users,
)
from app.seed import seed_initial_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("greennest")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if check_db_connection():
        logger.info("Database connection established")

        # Dev convenience. For production use Alembic migrations instead.
        Base.metadata.create_all(bind=engine)

        with SessionLocal() as db:
            seed_initial_data(db)
    else:
        logger.error("Database is unavailable. Check DB settings in .env")

    yield
    engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------
# Serve uploaded profile images
# ---------------------------------------------------------
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app.mount(
    "/uploads",
    StaticFiles(directory=str(UPLOAD_DIR)),
    name="uploads",
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Routers
# ---------------------------------------------------------
for r in (
    auth.router,
    users.router,
    nurseries.router,  # Added here
    plants.router,     # Added here
    cart.router,
    pages.router,
    maintenance.router,
    contact.router,
    about.router,
    placeholders.rent_router,
    placeholders.buy_router,
):
    app.include_router(r, prefix=settings.API_V1_PREFIX)


# ---------------------------------------------------------
# Database error handlers
# ---------------------------------------------------------
@app.exception_handler(OperationalError)
async def db_unavailable_handler(_: Request, exc: OperationalError):
    logger.error(
        "Database operational error (%s)",
        type(exc.orig).__name__ if exc.orig else "unknown",
    )
    return JSONResponse(
        status_code=503,
        content={"detail": "Service temporarily unavailable"},
    )


@app.exception_handler(SQLAlchemyError)
async def db_error_handler(_: Request, exc: SQLAlchemyError):
    logger.error("Database error (%s)", type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ---------------------------------------------------------
# Health check
# ---------------------------------------------------------
@app.get("/health", tags=["Health"])
def health():
    if check_db_connection():
        return {"status": "ok", "database": "up"}

    return JSONResponse(
        status_code=503,
        content={"status": "degraded", "database": "down"},
    )