from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import get_settings
from app.models.order import Base
import structlog
import time

settings = get_settings()
logger = structlog.get_logger()

# Create engine - using psycopg2 for PostgreSQL
engine = create_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False  # Disable SQLAlchemy query logging
)

# Create session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def wait_for_db(max_retries=30, delay=2):
    """Wait for database to be available with retries"""
    for attempt in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection established")
            return True
        except Exception as e:
            logger.warning(
                f"Database connection attempt {attempt + 1}/{max_retries} failed", 
                error=str(e)
            )
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                logger.error("Failed to connect to database after all retries")
                raise
    return False


def init_db():
    """Initialize database tables"""
    try:
        # Wait for database to be available
        wait_for_db()
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error("Database session error", error=str(e))
        raise
    finally:
        db.close()


def close_db():
    """Close database connection"""
    engine.dispose()
    logger.info("Database connection closed")