from pydantic import BaseModel
from datetime import datetime

class ReviewCreate(BaseModel):
    plant_id: int
    rating: int
    comment: str

class ReviewResponse(BaseModel):
    id: int
    plant_id: int
    user_id: int
    rating: int
    comment: str
    created_at: datetime

    class Config:
        from_attributes = True