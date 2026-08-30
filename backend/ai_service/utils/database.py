# Use: Decoupled async PostgreSQL client for the AI service.
# Used only for writing ai_conversations and audit_logs — does NOT import from app.*

from collections.abc import AsyncIterator

from sqlalchemy.engine import URL, make_url

from ai_service.config import get_ai_settings
from ai_service.utils.logger import StructuredLogger

logger = StructuredLogger("ai_service.utils.database")

_engine = None
_session_factory = None


def _build_async_url(raw_url: str) -> URL:
    """
    Transforms plain postgresql:// URLs to postgresql+asyncpg:// and strips
    unsupported query parameters like sslmode and channel_binding.
    """
    url = make_url(raw_url)
    query = dict(url.query)
    query.pop("sslmode", None)
    query.pop("channel_binding", None)
    return url.set(drivername="postgresql+asyncpg", query=query)


def get_async_engine():
    """
    Returns a lazy-initialized SQLAlchemy async engine.
    Returns None if DATABASE_URL is not configured.
    """
    global _engine
    if _engine is not None:
        return _engine

    settings = get_ai_settings()
    if not settings.database_url:
        logger.warning(
            "database.not_configured",
            detail="DATABASE_URL is missing. Conversation persistence and audit logging will be skipped.",
        )
        return None

    try:
        from sqlalchemy.ext.asyncio import create_async_engine

        async_url = _build_async_url(settings.database_url)
        _engine = create_async_engine(
            async_url,
            connect_args={"ssl": "require"},
            pool_pre_ping=True,
            pool_size=3,
            max_overflow=5,
        )
        logger.info("database.engine_created", url_scheme="postgresql+asyncpg")
        return _engine
    except Exception as exc:
        logger.error("database.engine_creation_failed", error=str(exc))
        return None


def get_async_session_factory():
    """
    Returns the SQLAlchemy async session factory or None if unavailable.
    """
    global _session_factory
    if _session_factory is not None:
        return _session_factory

    engine = get_async_engine()
    if engine is None:
        return None

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    _session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return _session_factory


async def get_db_session() -> AsyncIterator:
    """
    Async generator yielding a SQLAlchemy AsyncSession.
    Yields None if the database is not configured.
    """
    factory = get_async_session_factory()
    if factory is None:
        yield None
        return

    async with factory() as session:
        yield session
