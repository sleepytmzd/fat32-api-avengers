"""
Database migration script for Notification Service
Run this to initialize the database tables
"""
import asyncio
from database import init_db, engine
from models import Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_tables():
    """Create all tables"""
    logger.info("Creating database tables...")
    try:
        async with engine.begin() as conn:
            # Drop all tables (use with caution in production!)
            # await conn.run_sync(Base.metadata.drop_all)
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Database tables created successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_tables())
