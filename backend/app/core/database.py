from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import ssl
from app.core.config import get_settings

settings = get_settings()


def _ensure_asyncpg_url(url: str) -> str:
    """Convert standard postgresql:// URL to asyncpg driver URL.

    Managed DBs (DigitalOcean, etc.) give you:
        postgresql://user:pass@host:25060/db?sslmode=require
    SQLAlchemy async needs:
        postgresql+asyncpg://user:pass@host:25060/db
    """
    # Strip sslmode param — asyncpg doesn't understand it; we handle SSL via connect_args
    if "sslmode=" in url:
        url = url.split("?")[0]
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def _get_connect_args() -> dict:
    """Return SSL connect args for managed databases (DigitalOcean, etc.)."""
    url = settings.DATABASE_URL
    # If connecting to a remote host (not localhost/docker-compose), use SSL
    if url and "localhost" not in url and "127.0.0.1" not in url and "@postgres:" not in url:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return {"ssl": ssl_context}
    return {}


engine = create_async_engine(
    _ensure_asyncpg_url(settings.DATABASE_URL),
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args=_get_connect_args(),
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:  # type: ignore[misc]
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
