"""
SQLAlchemy async database session setup.
Supports both SQLite (local dev, no Docker) and PostgreSQL (production).
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
from app.core.logging import logger

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# SQLite doesn't support pool_size/max_overflow
_engine_kwargs = {
    "echo": settings.DEBUG,
}
if not _is_sqlite:
    _engine_kwargs["pool_pre_ping"] = True
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20
else:
    # SQLite requires check_same_thread=False
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables. Enables pgvector on Postgres; skips on SQLite."""
    # Import all models so Base knows about them before create_all
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        if not _is_sqlite:
            try:
                import sqlalchemy
                await conn.execute(sqlalchemy.text("CREATE EXTENSION IF NOT EXISTS vector"))
                logger.info("✅ pgvector extension enabled")
            except Exception as e:
                logger.warning(f"pgvector not available (OK for dev): {e}")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created")

