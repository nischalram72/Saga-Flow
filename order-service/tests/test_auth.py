# pyrefly: ignore [missing-import]
import pytest
from httpx import AsyncClient
import time
# pyrefly: ignore [missing-import]
import jwt
from app.core.security import SECRET_KEY, ALGORITHM

@pytest.mark.asyncio
async def test_valid_login(client: AsyncClient):
    response = await client.post("/auth/login", data={"username": "customer1@test.com", "password": "testpass"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_invalid_login(client: AsyncClient):
    response = await client.post("/auth/login", data={"username": "customer1@test.com", "password": "wrongpassword"})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_expired_token(client: AsyncClient):
    # Manually craft an expired token
    payload = {
        "sub": "customer1@test.com",
        "role": "customer",
        "exp": time.time() - 3600  # Expired an hour ago
    }
    expired_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await client.get("/orders/", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"
