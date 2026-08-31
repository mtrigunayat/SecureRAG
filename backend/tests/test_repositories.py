"""
Tests for database repositories
"""
import pytest

from app.repositories.department_repository import DepartmentRepository
from app.repositories.user_repository import UserRepository
from app.repositories.document_repository import DocumentRepository
from app.models.document import DocumentSensitivity
from app.core.errors import DatabaseError


def test_department_repository_create(test_db):
    """Test creating a department via repository."""
    repo = DepartmentRepository(test_db)
    
    dept = repo.create("engineering", "Engineering team")
    
    assert dept.id is not None
    assert dept.name == "engineering"
    assert dept.description == "Engineering team"


def test_department_repository_get_by_name(test_db):
    """Test getting department by name."""
    repo = DepartmentRepository(test_db)
    
    repo.create("engineering")
    dept = repo.get_by_name("engineering")
    
    assert dept is not None
    assert dept.name == "engineering"


def test_department_repository_duplicate_name(test_db):
    """Test that creating duplicate department name fails."""
    repo = DepartmentRepository(test_db)
    
    repo.create("engineering")
    
    with pytest.raises(DatabaseError):
        repo.create("engineering")


def test_user_repository_create(test_db):
    """Test creating a user via repository."""
    dept_repo = DepartmentRepository(test_db)
    user_repo = UserRepository(test_db)
    
    dept = dept_repo.create("engineering")
    user = user_repo.create(
        username="testuser1",
        email="testuser1@example.com",
        full_name="Test User 1",
        department_id=dept.id
    )
    
    assert user.id is not None
    assert user.username == "testuser1"
    assert user.email == "testuser1@example.com"
    assert user.department_id == dept.id


def test_user_repository_get_by_username(test_db):
    """Test getting user by username."""
    dept_repo = DepartmentRepository(test_db)
    user_repo = UserRepository(test_db)
    
    dept = dept_repo.create("engineering")
    user_repo.create("testuser2", "testuser2@example.com", "Test User 2", dept.id)
    
    user = user_repo.get_by_username("testuser2")
    
    assert user is not None
    assert user.username == "testuser2"


def test_user_repository_get_by_department(test_db):
    """Test getting all users in a department."""
    dept_repo = DepartmentRepository(test_db)
    user_repo = UserRepository(test_db)
    
    dept = dept_repo.create("engineering")
    user_repo.create("testuser3", "testuser3@example.com", "Test User 3", dept.id)
    user_repo.create("testuser4", "testuser4@example.com", "Test User 4", dept.id)
    
    users = user_repo.get_by_department(dept.id)
    
    assert len(users) == 2
    assert all(u.department_id == dept.id for u in users)


def test_document_repository_create(test_db):
    """Test creating a document via repository."""
    dept_repo = DepartmentRepository(test_db)
    doc_repo = DocumentRepository(test_db)
    
    dept = dept_repo.create("engineering")
    doc = doc_repo.create(
        name="Deployment Guidelines",
        department_id=dept.id,
        sensitivity=DocumentSensitivity.INTERNAL.value,
        source="docs/deployment.md"
    )
    
    assert doc.id is not None
    assert doc.name == "Deployment Guidelines"
    assert doc.department_id == dept.id
    assert doc.indexed_at is None


def test_document_repository_get_by_department(test_db):
    """Test getting all documents in a department."""
    dept_repo = DepartmentRepository(test_db)
    doc_repo = DocumentRepository(test_db)
    
    dept = dept_repo.create("engineering")
    doc_repo.create("Doc 1", dept.id)
    doc_repo.create("Doc 2", dept.id)
    
    docs = doc_repo.get_by_department(dept.id)
    
    assert len(docs) == 2
    assert all(d.department_id == dept.id for d in docs)


def test_document_repository_mark_as_indexed(test_db):
    """Test marking a document as indexed."""
    dept_repo = DepartmentRepository(test_db)
    doc_repo = DocumentRepository(test_db)
    
    dept = dept_repo.create("engineering")
    doc = doc_repo.create("Doc", dept.id)
    
    assert doc.indexed_at is None
    
    doc_repo.mark_as_indexed(doc.id)
    updated_doc = doc_repo.get_by_id(doc.id)
    
    assert updated_doc.indexed_at is not None


def test_document_repository_get_not_indexed(test_db):
    """Test getting documents not yet indexed."""
    dept_repo = DepartmentRepository(test_db)
    doc_repo = DocumentRepository(test_db)
    
    dept = dept_repo.create("engineering")
    doc1 = doc_repo.create("Doc 1", dept.id)
    doc2 = doc_repo.create("Doc 2", dept.id)
    
    # Mark one as indexed
    doc_repo.mark_as_indexed(doc1.id)
    
    not_indexed = doc_repo.get_not_indexed()
    
    assert len(not_indexed) == 1
    assert not_indexed[0].id == doc2.id
