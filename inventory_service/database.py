from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from . import  config
from .config import DATABASE_URL
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

try:
    logger.info(f"Attempting to create engine with URL: {DATABASE_URL.replace(config.DATABASE_PASSWORD, '***')}") # Hide password
    engine = create_async_engine(DATABASE_URL, echo=True, pool_pre_ping=True)
    # Use async_sessionmaker for SQLAlchemy 2.0+
    AsyncSessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    logger.info("Async database engine and session factory created successfully.")
except Exception as e:
    logger.error(f"FATAL: Failed to create database engine or session factory: {e}")
    # In a real app, might want to exit or prevent startup
    raise RuntimeError(f"Could not initialize database connection: {e}")

Base = declarative_base()

async def get_db_session() -> AsyncSession:
    """FastAPI dependency to inject DB session."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Rolling back session due to error: {e}")
            await session.rollback()
            raise
        # No automatic commit/close here, managed by 'async with'