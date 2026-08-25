"""
Models package

Imports all SQLAlchemy models. Import order is important for relationships.
"""
# Import order matters: Department must be imported before User
# because User has a relationship to Department
from app.models.department import Department
from app.models.user import User
from app.models.document import Document

__all__ = ["Department", "User", "Document"]
