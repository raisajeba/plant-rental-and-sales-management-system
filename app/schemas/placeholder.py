from pydantic import BaseModel


class FeatureStatusOut(BaseModel):
    feature: str
    status: str            # "under_development" for now
    message: str
    items: list = []       # stays empty until the real feature exists