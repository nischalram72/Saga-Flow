# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import sessionmaker
# pyrefly: ignore [missing-import]
from sqlalchemy.pool import StaticPool
import asyncio

from app.main import app
from app.db.database import Base, get_db
from app.core.security import get_password_hash
from app.models.user import User, Role

# Use in-memory sqlite for tests
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

# Removed event_loop fixture to use pytest-asyncio default

@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Seed users
    async with TestingSessionLocal() as session:
        admin = User(email="admin@test.com", hashed_password=get_password_hash("testpass"), role=Role.admin)
        customer1 = User(email="customer1@test.com", hashed_password=get_password_hash("testpass"), role=Role.customer)
        customer2 = User(email="customer2@test.com", hashed_password=get_password_hash("testpass"), role=Role.customer)
        session.add_all([admin, customer1, customer2])
        await session.commit()
    
    yield
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
