"""
Tests for database seeding
"""
import pytest

from app.db.seed import seed_database
from app.models.department import Department
from app.models.user import User
from app.models.document import Document


def test_seed_database(test_db):
    """Test that seed creates expected data."""
    # Note: seed_database uses SessionLocal, not test_db
    # For testing, we'll call the seed functions directly
    from app.db.seed import seed_departments, seed_users, seed_documents
    
    # Seed departments
    departments = seed_departments(test_db)
    
    assert len(departments) == 4
    assert "engineering" in departments
    assert "sales" in departments
    assert "hr" in departments
    assert "general" in departments
    
    # Seed users
    users = seed_users(test_db, departments)
    
    assert len(users) == 3
    assert "alice" in users
    assert "bob" in users
    assert "charlie" in users
    
    # Verify user-department relationships
    assert users["alice"].department == departments["engineering"]
    assert users["bob"].department == departments["sales"]
    assert users["charlie"].department == departments["hr"]
    
    # Seed documents
    documents = seed_documents(test_db, departments)
    
    assert len(documents) >= 6  # At least 6 documents
    
    # Verify at least one document per department
    eng_docs = [d for d in documents if d.department_id == departments["engineering"].id]
    sales_docs = [d for d in documents if d.department_id == departments["sales"].id]
    hr_docs = [d for d in documents if d.department_id == departments["hr"].id]
    
    assert len(eng_docs) > 0
    assert len(sales_docs) > 0
    assert len(hr_docs) > 0


def test_seed_idempotent(test_db):
    """Test that seed can be run multiple times safely."""
    from app.db.seed import seed_departments, seed_users, seed_documents
    
    # First seed
    departments1 = seed_departments(test_db)
    users1 = seed_users(test_db, departments1)
    documents1 = seed_documents(test_db, departments1)
    
    # Second seed (should skip existing records)
    departments2 = seed_departments(test_db)
    users2 = seed_users(test_db, departments2)
    documents2 = seed_documents(test_db, departments2)
    
    # Verify counts haven't changed
    assert test_db.query(Department).count() == len(departments1)
    assert test_db.query(User).count() == len(users1)
    assert test_db.query(Document).count() == len(documents1)
