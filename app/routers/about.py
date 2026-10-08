"""About Us: static content, no database. Edit the text below."""
from fastapi import APIRouter

from app.schemas.about import AboutOut

router = APIRouter(prefix="/about", tags=["About Us"])

ABOUT_CONTENT = AboutOut(
    app_name="Green Forest",
    tagline="Bring nature home: buy, rent and care for plants.",
    description=(
        "Green Forest connects plant lovers with local nurseries. "
        "Buy plants, rent them for events or short stays, and keep them healthy "
        "with scheduled care reminders."
    ),
    mission="Make greener living simple and accessible for everyone.",
    features=[
        "Buy plants from trusted nurseries",
        "Rent plants for a day, a month or longer",
        "Maintenance schedules with clear care instructions",
        "Maintenance requests when your plant needs help",
    ],
    contact_email="hello@greenforest.example",
)


@router.get("", response_model=AboutOut)
def get_about():
    return ABOUT_CONTENT