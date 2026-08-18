import os
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import declarative_base, sessionmaker
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Construct absolute path to .env file
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env')
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True, pool_pre_ping=True, pool_recycle=3600)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
