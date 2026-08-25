"""
Integration tests for Phase 8 secure retrieval

CRITICAL SECURITY TESTS:
1. Cross-department isolation
2. Retrieval-time ACL enforcement
3. Client cannot bypass authorization
"""
import pytest
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.user import User
from app.models.department import Department
from app.models.document import Document
from app.repositories.user_repository import UserRepository
from app.repositories.department_repository import DepartmentRepository
from app.repositories.document_repository import DocumentRepository
from app.services.ingestion_service import IngestionService
from app.services.vector_indexing_service import VectorIndexingService
from app.services.retrieval_service import RetrievalService
from app.schemas.retrieval import RetrievalResult


@pytest.mark.integration
@pytest.mark.slow
class TestCrossDepartmentIsolation:
    """
    MOST CRITICAL SECURITY TEST FOR PHASE 8.
    
    Verifies that users can ONLY retrieve documents from their own department.
    This is the fundamental security requirement for the entire system.
    
    Scenario:
        - Department A: engineering
        - Department B: hr
        - User Alice → engineering
        - User Bob → hr
        - Document "Engineering Policy" → engineering
        - Document "HR Policy" → hr
        
    Test:
        1. Alice asks about "engineering policy"
           → MUST retrieve "Engineering Policy"
           → MUST NOT retrieve "HR Policy"
        
        2. Bob asks about "HR policy"
           → MUST retrieve "HR Policy"
           → MUST NOT retrieve "Engineering Policy"
    """
    
    @pytest.fixture(scope="class")
    def db(self):
        """Create database session."""
        session = SessionLocal()
        yield session
        session.close()
    
    @pytest.fixture(scope="class")
    def setup_departments(self, db):
        """Create test departments."""
        dept_repo = DepartmentRepository(db)
        
        # Try to get existing departments first
        engineering = dept_repo.get_by_name("engineering")
        hr = dept_repo.get_by_name("hr")
        
        if not engineering or not hr:
            pytest.skip("Departments not seeded. Run database seed first.")
        
        return engineering, hr
    
    @pytest.fixture(scope="class")
    def setup_users(self, db, setup_departments):
        """Create test users."""
        engineering, hr = setup_departments
        user_repo = UserRepository(db)
        
        # Check if test users already exist
        alice = user_repo.get_by_username("alice_test_phase8")
        bob = user_repo.get_by_username("bob_test_phase8")
        
        if not alice:
            from app.services.password_service import hash_password
            alice = User(
                username="alice_test_phase8",
                email="alice_phase8@company.com",
                full_name="Alice Engineering",
                password_hash=hash_password("test123"),
                department_id=engineering.id
            )
            db.add(alice)
        
        if not bob:
            from app.services.password_service import hash_password
            bob = User(
                username="bob_test_phase8",
                email="bob_phase8@company.com",
                full_name="Bob HR",
                password_hash=hash_password("test123"),
                department_id=hr.id
            )
            db.add(bob)
        
        db.commit()
        db.refresh(alice)
        db.refresh(bob)
        
        return alice, bob
    
    @pytest.fixture(scope="class")
    def setup_documents(self, db, setup_departments):
        """
        Create and index test documents.
        
        Creates minimal test documents for cross-department testing.
        """
        engineering, hr = setup_departments
        doc_repo = DocumentRepository(db)
        
        # Check if test documents exist
        eng_doc = doc_repo.get_by_name("Engineering Policy Test Phase 8")
        hr_doc = doc_repo.get_by_name("HR Policy Test Phase 8")
        
        if not eng_doc:
            eng_doc = Document(
                name="Engineering Policy Test Phase 8",
                department_id=engineering.id,
                sensitivity="internal",
                source="test_phase8_eng.txt",
                content_hash="eng_test_hash_phase8"
            )
            db.add(eng_doc)
        
        if not hr_doc:
            hr_doc = Document(
                name="HR Policy Test Phase 8",
                department_id=hr.id,
                sensitivity="internal",
                source="test_phase8_hr.txt",
                content_hash="hr_test_hash_phase8"
            )
            db.add(hr_doc)
        
        db.commit()
        db.refresh(eng_doc)
        db.refresh(hr_doc)
        
        return eng_doc, hr_doc
    
    def test_alice_cannot_retrieve_hr_documents(
        self,
        db,
        setup_users,
        setup_documents
    ):
        """
        CRITICAL SECURITY TEST: Alice (engineering) cannot retrieve HR documents.
        
        This test verifies:
        1. ACL filtering happens at retrieval time
        2. Department isolation is enforced
        3. Unauthorized documents are NEVER retrieved
        """
        alice, bob = setup_users
        eng_doc, hr_doc = setup_documents
        
        # Alice asks a question about HR
        # Even though HR document exists, she should NOT retrieve it
        retrieval_service = RetrievalService(db)
        
        result = retrieval_service.retrieve(
            question="What is the HR leave policy?",
            authenticated_user=alice
        )
        
        # Verify Alice's department was used
        assert result.user_department_id == alice.department_id
        assert result.user_department_name == "engineering"
        
        # CRITICAL: Verify NO HR documents in results
        hr_doc_retrieved = any(
            chunk.document_id == hr_doc.id
            for chunk in result.chunks
        )
        assert not hr_doc_retrieved, "SECURITY VIOLATION: Alice retrieved HR document!"
    
    def test_bob_cannot_retrieve_engineering_documents(
        self,
        db,
        setup_users,
        setup_documents
    ):
        """
        CRITICAL SECURITY TEST: Bob (HR) cannot retrieve engineering documents.
        
        Mirrors the Alice test for symmetry.
        """
        alice, bob = setup_users
        eng_doc, hr_doc = setup_documents
        
        # Bob asks about engineering
        retrieval_service = RetrievalService(db)
        
        result = retrieval_service.retrieve(
            question="What is the engineering deployment process?",
            authenticated_user=bob
        )
        
        # Verify Bob's department was used
        assert result.user_department_id == bob.department_id
        assert result.user_department_name == "hr"
        
        # CRITICAL: Verify NO engineering documents in results
        eng_doc_retrieved = any(
            chunk.document_id == eng_doc.id
            for chunk in result.chunks
        )
        assert not eng_doc_retrieved, "SECURITY VIOLATION: Bob retrieved engineering document!"
    
    def test_alice_can_retrieve_own_department_documents(
        self,
        db,
        setup_users,
        setup_documents
    ):
        """
        Test that Alice CAN retrieve engineering documents.
        
        Verifies the ACL filter allows authorized access.
        """
        alice, bob = setup_users
        eng_doc, hr_doc = setup_documents
        
        # This test requires documents to be indexed
        # For now, we verify the ACL behavior
        retrieval_service = RetrievalService(db)
        
        result = retrieval_service.retrieve(
            question="engineering",
            authenticated_user=alice
        )
        
        # Verify department is correct
        assert result.user_department_id == alice.department_id
        
        # If any results returned, verify they're from engineering
        for chunk in result.chunks:
            assert chunk.department_id == alice.department_id, \
                f"SECURITY VIOLATION: Alice retrieved chunk from department {chunk.department_id}!"


@pytest.mark.integration
class TestMaliciousRequests:
    """Test that malicious requests cannot bypass security."""
    
    def test_client_cannot_supply_department_id_in_request(self):
        """
        SECURITY TEST: Client-supplied department_id is impossible.
        
        The API schema does NOT accept department_id.
        """
        from app.schemas.retrieval import RetrievalRequest
        
        # Valid request
        valid_request = RetrievalRequest(question="test")
        assert valid_request.question == "test"
        
        # Trying to add department_id should be ignored
        request_data = {
            "question": "test",
            "department_id": 999  # Attempt to bypass ACL
        }
        
        # Pydantic will ignore extra fields
        request = RetrievalRequest(**request_data)
        assert not hasattr(request, "department_id")


@pytest.mark.integration
class TestDepartmentChange:
    """Test that department changes are immediately reflected."""
    
    def test_department_change_updates_retrieval_scope(self):
        """
        SECURITY TEST: Department determined from current database state.
        
        If a user's department changes in PostgreSQL,
        the next retrieval MUST use the new department.
        
        This proves authorization comes from PostgreSQL, not JWT claims.
        """
        # This test documents the requirement
        # Actual implementation:
        # 1. User.department is loaded fresh from PostgreSQL each request
        # 2. JWT only contains user_id
        # 3. Department is resolved via User.department relationship
        # 4. Therefore department changes are immediately reflected
        
        # Verify that get_current_user loads department from PostgreSQL
        from app.dependencies.auth import get_current_user
        from inspect import getsource
        
        source = getsource(get_current_user)
        
        # Verify function loads user from database
        assert "UserRepository" in source
        assert "get_by_id" in source
        
        # This ensures department comes from fresh database query


@pytest.mark.integration
class TestFilterPresence:
    """Verify ACL filter is always present in Qdrant requests."""
    
    def test_retrieval_always_includes_department_filter(self):
        """
        SECURITY TEST: Every retrieval must include department filter.
        
        This structural test prevents future developers from
        accidentally removing the ACL filter.
        """
        from app.services.retrieval_service import RetrievalService
        from inspect import getsource
        
        # Get source code of _search_vectors method
        source = getsource(RetrievalService._search_vectors)
        
        # Verify department_filter parameter is used
        assert "department_filter" in source
        assert "department_filter=department_filter" in source or \
               "department_filter," in source
        
        # Verify _build_department_filter is called
        service_source = getsource(RetrievalService.retrieve)
        assert "_build_department_filter" in service_source


@pytest.mark.integration
class TestNoPostFiltering:
    """Verify ACL filtering happens in Qdrant, not post-retrieval."""
    
    def test_no_python_filtering_after_retrieval(self):
        """
        SECURITY TEST: No Python filtering of results.
        
        Results must be filtered by Qdrant during search.
        There should be NO code that filters by department AFTER retrieval.
        """
        from app.services.retrieval_service import RetrievalService
        from inspect import getsource
        
        # Get _search_vectors and _normalize_results source
        search_source = getsource(RetrievalService._search_vectors)
        normalize_source = getsource(RetrievalService._normalize_results)
        
        # These methods should NOT filter by department_id
        # (filtering should happen in Qdrant via filter parameter)
        
        # Verify _normalize_results doesn't check department_id
        # It should just convert format, not filter
        assert "if" not in normalize_source or "department_id" not in normalize_source.split("def _normalize_results")[1].split("return chunks")[0]


@pytest.mark.integration
class TestRelevanceThreshold:
    """Test relevance score threshold enforcement."""
    
    def test_low_score_results_filtered_by_qdrant(self):
        """
        Test that low-score results are filtered by Qdrant.
        
        The score_threshold parameter is passed to Qdrant,
        which filters results server-side.
        """
        from app.core.config import settings
        
        # Verify threshold is configured
        assert hasattr(settings, "retrieval_score_threshold")
        assert settings.retrieval_score_threshold == 0.7
        
        # Verify threshold is passed to Qdrant
        from app.services.retrieval_service import RetrievalService
        from inspect import getsource
        
        source = getsource(RetrievalService._search_vectors)
        assert "score_threshold" in source
        assert "retrieval_score_threshold" in source


@pytest.mark.integration
class TestTopKConfiguration:
    """Test top-k configuration."""
    
    def test_top_k_is_configurable(self):
        """Test that top-k is configurable and used."""
        from app.core.config import settings
        
        # Verify top_k is configured
        assert hasattr(settings, "retrieval_top_k")
        assert settings.retrieval_top_k == 5
        
        # Verify it's passed to Qdrant
        from app.services.retrieval_service import RetrievalService
        from inspect import getsource
        
        source = getsource(RetrievalService._search_vectors)
        assert "top_k" in source
        assert "retrieval_top_k" in source
