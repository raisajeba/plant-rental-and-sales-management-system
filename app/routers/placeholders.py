"""Plant, Rent and Buy are placeholders until the next sprint.
Each returns HTTP 200 with a clear message and an empty list, so the frontend can
show a friendly 'coming soon' state instead of an error."""
from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.placeholder import FeatureStatusOut


def _placeholder_router(prefix: str, feature: str, tag: str) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])

    @router.get("", response_model=FeatureStatusOut)
    def under_development(_: User = Depends(get_current_user)):
        # TODO (next sprint): replace with the real implementation
        return FeatureStatusOut(
            feature=feature,
            status="under_development",
            message=f"The {feature} feature is under development and will be available soon.",
        )

    return router


plants_router = _placeholder_router("/plants", "Plants", "Plants (placeholder)")
rent_router = _placeholder_router("/rent", "Rent", "Rent (placeholder)")
buy_router = _placeholder_router("/buy", "Buy", "Buy (placeholder)")