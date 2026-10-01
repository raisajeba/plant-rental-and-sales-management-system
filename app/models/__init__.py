"""Import every model here so Base.metadata knows about all tables."""
from app.models.page import Page
from app.models.revoked_token import RevokedToken
from app.models.role import Role
from app.models.role_page import RolePage
from app.models.user import User

__all__ = ["User", "Role", "Page", "RolePage", "RevokedToken"]