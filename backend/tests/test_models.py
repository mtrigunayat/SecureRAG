"""
Tests for database models
"""
import pytest
from sqlalchemy.exc import IntegrityError
import bcrypt

from app.models.department import Department
from app.models.user import User
from app.models.document import Document, DocumentSensitivity


def test_create_department(test_db):
    """Test creating a department."""
    department = Department(
        name="engineering",
        description="Engineering team"
    )
    test_db.add(department)
    test_db.commit()
    
    assert department.id is not None
    assert department.name == "engineering"
    assert department.description == "Engineering team"
    assert department.created_at is not None
    assert department.updated_at is not None


def test_department_name_unique(test_db):
    """Test that department names must be unique."""
    dept1 = Department(name="engineering")
    test_db.add(dept1)
    test_db.commit()
    
    dept2 = Department(name="engineering")
    test_db.add(dept2)
    
    with pytest.raises(IntegrityError):
        test_db.commit()


def test_create_user(test_db):
    """Test creating a user."""
    # Create department first
    department = Department(name="engineering")
    test_db.add(department)
    test_db.commit()
    
    # Create user
    password_hash = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user = User(
        username="mohit",
        email="mohit@aithinkers.com",
        full_name="Mohit Trigunayat",
        password_hash=password_hash,
        department_id=department.id
    )
    test_db.add(user)
    test_db.commit()
    
    assert user.id is not None
    assert user.username == "mohit"
    assert user.email == "mohit@aithinkers.com"
    assert user.full_name == "Mohit Trigunayat"
    assert user.department_id == department.id
    assert user.created_at is not None


def test_user_email_unique(test_db):
    """Test that user emails must be unique."""
    department = Department(name="engineering")
    test_db.add(department)
    test_db.commit()
    
    password_hash = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user1 = User(
        username="mohit",
        email="mohit@aithinkers.com",
        full_name="Alice",
        password_hash=password_hash,
        department_id=department.id
    )
    test_db.add(user1)
    test_db.commit()
    
    user2 = User(
        username="alice2",
        email="mohit@aithinkers.com",
        full_name="Alice 2",
        password_hash=password_hash,
        department_id=department.id
    )
    test_db.add(user2)
    
    with pytest.raises(IntegrityError):
        test_db.commit()


def test_user_requires_department(test_db):
    """Test that user must belong to a department."""
    password_hash = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user = User(
        username="mohit",
        email="mohit@aithinkers.com",
        full_name="Mohit Trigunayat",
        password_hash=password_hash,
        department_id=999  # Non-existent department
    )
    test_db.add(user)
    
    with pytest.raises(IntegrityError):
        test_db.commit()


def test_create_document(test_db):
    """Test creating a document."""
    # Create department first
    department = Department(name="engineering")
    test_db.add(department)
    test_db.commit()
    
    # Create document
    document = Document(
        name="Deployment Guidelines",
        department_id=department.id,
        sensitivity=DocumentSensitivity.INTERNAL.value,
        source="docs/deployment.md"
    )
    test_db.add(document)
    test_db.commit()
    
    assert document.id is not None
    assert document.name == "Deployment Guidelines"
    assert document.department_id == department.id
    assert document.sensitivity == DocumentSensitivity.INTERNAL.value
    assert document.source == "docs/deployment.md"
    assert document.indexed_at is None  # Not indexed yet
    assert document.created_at is not None


def test_document_requires_department(test_db):
    """Test that document must belong to a department."""
    document = Document(
        name="Test Document",
        department_id=999,  # Non-existent department
        sensitivity=DocumentSensitivity.INTERNAL.value
    )
    test_db.add(document)
    
    with pytest.raises(IntegrityError):
        test_db.commit()


def test_department_user_relationship(test_db):
    """Test department-user relationship."""
    department = Department(name="engineering")
    test_db.add(department)
    test_db.commit()
    
    password_hash = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user1 = User(
        username="mohit",
        email="mohit@aithinkers.com",
        full_name="Alice",
        password_hash=password_hash,
        department_id=department.id
    )
    user2 = User(
        username="karthik",
        email="karthik@aithinkers.com",
        full_name="Bob",
        password_hash=password_hash,
        department_id=department.id
    )
    test_db.add_all([user1, user2])
    test_db.commit()
    
    # Test relationship from department side
    assert len(department.users) == 2
    assert user1 in department.users
    assert user2 in department.users
    
    # Test relationship from user side
    assert user1.department == department
    assert user2.department == department


def test_department_document_relationship(test_db):
    """Test department-document relationship."""
    department = Department(name="engineering")
    test_db.add(department)
    test_db.commit()
    
    doc1 = Document(
        name="Doc 1",
        department_id=department.id,
        sensitivity=DocumentSensitivity.INTERNAL.value
    )
    doc2 = Document(
        name="Doc 2",
        department_id=department.id,
        sensitivity=DocumentSensitivity.INTERNAL.value
    )
    test_db.add_all([doc1, doc2])
    test_db.commit()
    
    # Test relationship from department side
    assert len(department.documents) == 2
    assert doc1 in department.documents
    assert doc2 in department.documents
    
    # Test relationship from document side
    assert doc1.department == department
    assert doc2.department == department


def test_cascade_delete_department(test_db):
    """Test that deleting a department cascades to users and documents."""
    department = Department(name="engineering")
    test_db.add(department)
    test_db.commit()
    
    password_hash = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user = User(
        username="mohit",
        email="mohit@aithinkers.com",
        full_name="Alice",
        password_hash=password_hash,
        department_id=department.id
    )
    document = Document(
        name="Doc",
        department_id=department.id,
        sensitivity=DocumentSensitivity.INTERNAL.value
    )
    test_db.add_all([user, document])
    test_db.commit()
    
    dept_id = department.id
    
    # Delete department
    test_db.delete(department)
    test_db.commit()
    
    # Verify users and documents were also deleted
    assert test_db.query(User).filter(User.department_id == dept_id).count() == 0
    assert test_db.query(Document).filter(Document.department_id == dept_id).count() == 0
