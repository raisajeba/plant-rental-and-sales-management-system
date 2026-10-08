from pydantic import BaseModel


class AboutOut(BaseModel):
    app_name: str
    tagline: str
    description: str
    mission: str
    features: list[str]
    contact_email: str