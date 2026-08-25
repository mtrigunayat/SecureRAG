"""
Pytest configuration and fixtures
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import Base


def get_db_dependency():
    """Import get_db from correct location"""
    from app.db.session import get_db
    return get_db


# Test database URL (use in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_db():
    """
    Create a test database session.
    
    Yields:
        Test database session
    """
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},  # SQLite specific
        poolclass=StaticPool,
    )
    
    # Enable foreign key constraints in SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Import all models to ensure they're registered with Base
    from app.models import department, user, document
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_db):
    """
    Alias for test_db fixture (for clarity in unit tests).
    
    Yields:
        Test database session
    """
    yield test_db


@pytest.fixture(scope="function")
def client(test_db):
    """
    Create a test client with database override and seeded data.
    
    Args:
        test_db: Test database session fixture
        
    Yields:
        FastAPI test client
    """
    from app.db.session import get_db
    from app.models.department import Department
    from app.models.user import User
    from app.models.document import Document
    from app.services.password_service import hash_password
    
    # Seed test database with departments, users, and documents
    # This matches the production seed data
    
    # Create departments
    engineering = Department(id=1, name="engineering", description="Engineering and development team")
    sales = Department(id=2, name="sales", description="Sales and business development team")
    hr = Department(id=3, name="hr", description="Human resources team")
    general = Department(id=4, name="general", description="General company documents")
    
    test_db.add_all([engineering, sales, hr, general])
    test_db.flush()
    
    # Create users (alice, bob, charlie)
    dev_password = "password123"  # POC ONLY
    dev_password_hash = hash_password(dev_password)
    
    alice = User(
        id=2,  # Match production seed (user id=1 might be reserved)
        username="alice",
        email="alice@company.com",
        full_name="Alice Johnson",
        password_hash=dev_password_hash,
        department_id=engineering.id
    )
    bob = User(
        id=3,
        username="bob",
        email="bob@company.com",
        full_name="Bob Smith",
        password_hash=dev_password_hash,
        department_id=sales.id
    )
    charlie = User(
        id=4,
        username="charlie",
        email="charlie@company.com",
        full_name="Charlie Brown",
        password_hash=dev_password_hash,
        department_id=hr.id
    )
    
    test_db.add_all([alice, bob, charlie])
    test_db.flush()
    
    # Create documents
    # Engineering docs (1-3)
    test_db.add(Document(id=1, name="Deployment Guidelines", department_id=engineering.id))
    test_db.add(Document(id=2, name="Coding Standards", department_id=engineering.id))
    test_db.add(Document(id=3, name="Architecture Guide", department_id=engineering.id))
    
    # Sales docs (4-6)
    test_db.add(Document(id=4, name="Pricing Policy", department_id=sales.id))
    test_db.add(Document(id=5, name="Discount Policy", department_id=sales.id))
    test_db.add(Document(id=6, name="Sales Playbook", department_id=sales.id))
    
    # HR docs (7-9)
    test_db.add(Document(id=7, name="Leave Policy", department_id=hr.id))
    test_db.add(Document(id=8, name="Employee Benefits", department_id=hr.id))
    test_db.add(Document(id=9, name="Performance Review Guidelines", department_id=hr.id))
    
    # General docs (10-12)
    test_db.add(Document(id=10, name="Company Overview", department_id=general.id))
    test_db.add(Document(id=11, name="Security Policy", department_id=general.id))
    test_db.add(Document(id=12, name="Code of Conduct", department_id=general.id))
    
    test_db.commit()
    
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()
