"""
Database session management
"""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
from app.core.errors import DatabaseError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Create SQLAlchemy engine
try:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,  # Verify connections before using
        echo=settings.app_env == "development"  # Log SQL in development
    )
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    raise DatabaseError(f"Failed to create database engine: {e}")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database sessions in FastAPI endpoints.
    
    Yields:
        Database session
        
    Example:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    from app.core.errors import AuthenticationError, AuthorizationError, DatabaseError
    from fastapi.exceptions import RequestValidationError
    from pydantic import ValidationError
    
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except (AuthenticationError, AuthorizationError, RequestValidationError, ValidationError):
        # Re-raise authentication, authorization, and validation errors without converting to 503
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise DatabaseError("Database operation failed")
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database tables.
    
    Creates all tables defined in models.
    Called during application startup.
    
    Note: In production, use Alembic migrations instead of create_all().
    This is kept for development convenience and backward compatibility.
    """
    try:
        # Import all models here to ensure they're registered with Base
        from app.models import department, user, document
        
        # Create tables (use Alembic migrations in production)
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise DatabaseError(f"Failed to initialize database: {e}")


def check_db_connection() -> bool:
    """
    Check if database connection is healthy.
    
    Returns:
        True if connection is healthy, False otherwise
    """
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
