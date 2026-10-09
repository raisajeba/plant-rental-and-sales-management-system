from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.plant import PlantOut


class CartItemCreate(BaseModel):
    plant_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=1_000_000)


class CartItemOut(BaseModel):
    id: int
    plant_id: int
    quantity: int
    created_at: datetime
    updated_at: datetime
    plant: PlantOut

    model_config = ConfigDict(from_attributes=True)
