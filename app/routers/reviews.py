from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.review import Review
from app.schemas.review import ReviewCreate, ReviewResponse
from app.dependencies import get_current_user  # ba sothik active user dependency

router = APIRouter(prefix="/reviews", tags=["Reviews"])

@router.post("", response_model=ReviewResponse)
def create_review(
    payload: ReviewCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    review = Review(
        plant_id=payload.plant_id,
        user_id=current_user.id,
        rating=payload.rating,
        comment=payload.comment
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review

@router.get("/plant/{plant_id}", response_model=list[ReviewResponse])
def get_plant_reviews(plant_id: int, db: Session = Depends(get_db)):
    reviews = db.query(Review).filter(Review.plant_id == plant_id).all()
    return reviews