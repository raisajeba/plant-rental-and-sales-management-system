"""Contact Us: public submission form."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ContactMessage
from app.schemas.auth import MessageResponse
from app.schemas.contact import ContactCreate

router = APIRouter(prefix="/contact", tags=["Contact Us"])


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def submit_contact_form(payload: ContactCreate, db: Session = Depends(get_db)):
    """Public (no login needed). Messages are stored in the contact_messages table.
    Production tip: add rate limiting here, because public forms attract spam."""
    db.add(ContactMessage(**payload.model_dump()))
    db.commit()
    return MessageResponse(message="Thank you! We have received your message.")