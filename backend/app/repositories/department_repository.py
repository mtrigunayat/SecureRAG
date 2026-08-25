"""
Department repository

Provides data access methods for Department entities.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.department import Department
from app.core.errors import DatabaseError


class DepartmentRepository:
    """
    Repository for Department entity database operations.
    
    Encapsulates database access logic for departments.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def get_by_id(self, department_id: int) -> Optional[Department]:
        """
        Get department by ID.
        
        Args:
            department_id: Department ID
            
        Returns:
            Department if found, None otherwise
        """
        return self.db.query(Department).filter(Department.id == department_id).first()
    
    def get_by_name(self, name: str) -> Optional[Department]:
        """
        Get department by name.
        
        Args:
            name: Department name
            
        Returns:
            Department if found, None otherwise
        """
        return self.db.query(Department).filter(Department.name == name.lower()).first()
    
    def get_all(self) -> List[Department]:
        """
        Get all departments.
        
        Returns:
            List of all departments
        """
        return self.db.query(Department).all()
    
    def create(self, name: str, description: Optional[str] = None) -> Department:
        """
        Create a new department.
        
        Args:
            name: Department name (will be lowercased)
            description: Optional description
            
        Returns:
            Created department
            
        Raises:
            DatabaseError: If department with name already exists
        """
        try:
            department = Department(
                name=name.lower(),
                description=description
            )
            self.db.add(department)
            self.db.commit()
            self.db.refresh(department)
            return department
        except IntegrityError as e:
            self.db.rollback()
            raise DatabaseError(f"Department '{name}' already exists") from e
    
    def update(self, department_id: int, description: Optional[str] = None) -> Optional[Department]:
        """
        Update department.
        
        Args:
            department_id: Department ID
            description: New description
            
        Returns:
            Updated department if found, None otherwise
        """
        department = self.get_by_id(department_id)
        if department:
            if description is not None:
                department.description = description
            self.db.commit()
            self.db.refresh(department)
        return department
    
    def delete(self, department_id: int) -> bool:
        """
        Delete department.
        
        Args:
            department_id: Department ID
            
        Returns:
            True if deleted, False if not found
            
        Note:
            Will cascade delete all users and documents in this department.
        """
        department = self.get_by_id(department_id)
        if department:
            self.db.delete(department)
            self.db.commit()
            return True
        return False
