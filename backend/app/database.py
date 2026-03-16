import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

load_dotenv()

# For DigitalOcean Managed DB, DATABASE_URL might start with postgres://
# asyncpg requires postgresql+asyncpg://
# Default to local SQLite for easier local development if no DATABASE_URL is provided
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./iam_detective.db")

def _preferred_postgres_driver() -> str:
    try:
        import asyncpg as _asyncpg
        _ = _asyncpg
        return "postgresql+asyncpg"
    except Exception:
        return "postgresql+psycopg"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", f"{_preferred_postgres_driver()}://", 1)
elif DATABASE_URL.startswith("postgresql://") and not (
    DATABASE_URL.startswith("postgresql+asyncpg://") or DATABASE_URL.startswith("postgresql+psycopg://")
):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", f"{_preferred_postgres_driver()}://", 1)

# Ensure SSL is used for DigitalOcean Managed Databases
connect_args = {}
if "postgresql+asyncpg" in DATABASE_URL:
    parsed = urlparse(DATABASE_URL)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))

    ssl_pref = (os.getenv("DB_SSL") or "auto").strip().lower()
    if ssl_pref not in {"auto", "require", "disable"}:
        ssl_pref = "auto"

    host = (parsed.hostname or "").lower()
    is_local_host = host in {"localhost", "127.0.0.1", "::1", "db"}

    if query.get("sslmode") == "require":
        query.pop("sslmode", None)
        query["ssl"] = "require"

    if ssl_pref == "disable":
        query.pop("ssl", None)
        query.pop("sslmode", None)
    elif ssl_pref == "require":
        query.setdefault("ssl", "require")
    else:
        if not is_local_host and host:
            query.setdefault("ssl", "require")

    DATABASE_URL = urlunparse(parsed._replace(query=urlencode(query)))

engine = create_async_engine(DATABASE_URL, echo=False, connect_args=connect_args)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
