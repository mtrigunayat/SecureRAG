"""
Database seed script

Creates initial departments, users, and documents for development and testing.

DEVELOPMENT CREDENTIALS (POC ONLY):
- alice@company.com / password123
- bob@company.com / password123
- charlie@company.com / password123

WARNING: These are development-only credentials. Never use in production.
"""
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.department import Department
from app.models.user import User
from app.models.document import Document, DocumentSensitivity
from app.services.password_service import hash_password
from app.core.logging import get_logger

logger = get_logger(__name__)


def seed_departments(db: Session) -> dict:
    """
    Seed departments.
    
    Returns:
        Dictionary mapping department names to Department objects
    """
    departments_data = [
        {"name": "engineering", "description": "Engineering and development team"},
        {"name": "sales", "description": "Sales and customer relations team"},
        {"name": "hr", "description": "Human resources team"},
        {"name": "general", "description": "General company information"},
    ]
    
    departments = {}
    for dept_data in departments_data:
        # Check if department already exists
        existing = db.query(Department).filter(Department.name == dept_data["name"]).first()
        if existing:
            logger.info(f"Department '{dept_data['name']}' already exists, skipping")
            departments[dept_data["name"]] = existing
        else:
            department = Department(**dept_data)
            db.add(department)
            departments[dept_data["name"]] = department
            logger.info(f"Created department: {dept_data['name']}")
    
    db.commit()
    return departments


def seed_users(db: Session, departments: dict) -> dict:
    """
    Seed users with development credentials.
    
    Args:
        departments: Dictionary of department objects
        
    Returns:
        Dictionary mapping usernames to User objects
        
    Development Credentials (POC ONLY):
        - alice@company.com / password123
        - bob@company.com / password123
        - charlie@company.com / password123
    """
    # Development password (POC ONLY - never use in production)
    dev_password = "password123"
    dev_password_hash = hash_password(dev_password)
    
    users_data = [
        {
            "username": "alice",
            "email": "alice@company.com",
            "full_name": "Alice Johnson",
            "password_hash": dev_password_hash,
            "department_id": departments["engineering"].id
        },
        {
            "username": "bob",
            "email": "bob@company.com",
            "full_name": "Bob Smith",
            "password_hash": dev_password_hash,
            "department_id": departments["sales"].id
        },
        {
            "username": "charlie",
            "email": "charlie@company.com",
            "full_name": "Charlie Williams",
            "password_hash": dev_password_hash,
            "department_id": departments["hr"].id
        },
    ]
    
    users = {}
    for user_data in users_data:
        # Check if user already exists
        existing = db.query(User).filter(User.username == user_data["username"]).first()
        if existing:
            logger.info(f"User '{user_data['username']}' already exists, updating password")
            # Update existing user's password hash
            existing.password_hash = user_data["password_hash"]
            existing.email = user_data["email"]
            existing.full_name = user_data["full_name"]
            existing.department_id = user_data["department_id"]
            users[user_data["username"]] = existing
        else:
            user = User(**user_data)
            db.add(user)
            users[user_data["username"]] = user
            logger.info(f"Created user: {user_data['username']} ({user_data['full_name']})")
    
    db.commit()
    return users


def seed_documents(db: Session, departments: dict) -> list:
    """
    Seed documents.
    
    Args:
        departments: Dictionary of department objects
        
    Returns:
        List of Document objects
    """
    documents_data = [
        # Engineering documents
        {
            "name": "Deployment Guidelines",
            "department_id": departments["engineering"].id,
            "sensitivity": DocumentSensitivity.INTERNAL.value,
            "source": "docs/engineering/deployment_guidelines.md"
        },
        {
            "name": "Coding Standards",
            "department_id": departments["engineering"].id,
            "sensitivity": DocumentSensitivity.INTERNAL.value,
            "source": "docs/engineering/coding_standards.md"
        },
        {
            "name": "Architecture Guide",
            "department_id": departments["engineering"].id,
            "sensitivity": DocumentSensitivity.INTERNAL.value,
            "source": "docs/engineering/architecture_guide.md"
        },
        # Sales documents
        {
            "name": "Pricing Policy",
            "department_id": departments["sales"].id,
            "sensitivity": DocumentSensitivity.CONFIDENTIAL.value,
            "source": "docs/sales/pricing_policy.md"
        },
        {
            "name": "Discount Policy",
            "department_id": departments["sales"].id,
            "sensitivity": DocumentSensitivity.CONFIDENTIAL.value,
            "source": "docs/sales/discount_policy.md"
        },
        {
            "name": "Sales Playbook",
            "department_id": departments["sales"].id,
            "sensitivity": DocumentSensitivity.INTERNAL.value,
            "source": "docs/sales/sales_playbook.md"
        },
        # HR documents
        {
            "name": "Leave Policy",
            "department_id": departments["hr"].id,
            "sensitivity": DocumentSensitivity.INTERNAL.value,
            "source": "docs/hr/leave_policy.md"
        },
        {
            "name": "Employee Benefits",
            "department_id": departments["hr"].id,
            "sensitivity": DocumentSensitivity.INTERNAL.value,
            "source": "docs/hr/employee_benefits.md"
        },
        {
            "name": "Performance Review Guidelines",
            "department_id": departments["hr"].id,
            "sensitivity": DocumentSensitivity.CONFIDENTIAL.value,
            "source": "docs/hr/performance_review_guidelines.md"
        },
        # General documents
        {
            "name": "Company Overview",
            "department_id": departments["general"].id,
            "sensitivity": DocumentSensitivity.PUBLIC.value,
            "source": "docs/general/company_overview.md"
        },
        {
            "name": "Security Policy",
            "department_id": departments["general"].id,
            "sensitivity": DocumentSensitivity.INTERNAL.value,
            "source": "docs/general/security_policy.md"
        },
        {
            "name": "Code of Conduct",
            "department_id": departments["general"].id,
            "sensitivity": DocumentSensitivity.PUBLIC.value,
            "source": "docs/general/code_of_conduct.md"
        },
    ]
    
    documents = []
    for doc_data in documents_data:
        # Check if document already exists (by name and department)
        existing = db.query(Document).filter(
            Document.name == doc_data["name"],
            Document.department_id == doc_data["department_id"]
        ).first()
        
        if existing:
            logger.info(f"Document '{doc_data['name']}' already exists, skipping")
            documents.append(existing)
        else:
            document = Document(**doc_data)
            db.add(document)
            documents.append(document)
            logger.info(f"Created document: {doc_data['name']}")
    
    db.commit()
    return documents


def seed_database() -> None:
    """
    Seed the database with initial data.
    
    This function is idempotent - it can be run multiple times safely.
    Existing records will be skipped.
    """
    logger.info("Starting database seed...")
    
    db = SessionLocal()
    try:
        # Seed departments
        departments = seed_departments(db)
        logger.info(f"Seeded {len(departments)} departments")
        
        # Seed users
        users = seed_users(db, departments)
        logger.info(f"Seeded {len(users)} users")
        
        # Seed documents
        documents = seed_documents(db, departments)
        logger.info(f"Seeded {len(documents)} documents")
        
        logger.info("Database seed completed successfully")
        
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # Allow running this script directly
    from app.core.logging import setup_logging
    setup_logging()
    seed_database()
