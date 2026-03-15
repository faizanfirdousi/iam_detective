import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

# For DigitalOcean Managed DB, DATABASE_URL might start with postgres://
# asyncpg requires postgresql+asyncpg://
# Default to local SQLite for easier local development if no DATABASE_URL is provided
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./iam_detective.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Ensure SSL is used for DigitalOcean Managed Databases
connect_args = {}
if "postgresql+asyncpg" in DATABASE_URL:
    # DigitalOcean requires SSL. asyncpg uses 'ssl' param.
    if "sslmode=" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("sslmode=require", "ssl=require")
    elif "ssl=" not in DATABASE_URL:
        if "?" in DATABASE_URL:
            DATABASE_URL += "&ssl=require"
        else:
            DATABASE_URL += "?ssl=require"

engine = create_async_engine(DATABASE_URL, echo=False, connect_args=connect_args)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
