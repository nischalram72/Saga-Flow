# pyrefly: ignore [missing-import]
import pytest
from httpx import AsyncClient
from app.core.security import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from datetime import timedelta

def get_token(email: str, role: str) -> str:
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_access_token(
        data={"sub": email, "role": role}, expires_delta=access_token_expires
    )

@pytest.fixture
def customer1_headers():
    token = get_token("customer1@test.com", "customer")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def customer2_headers():
    token = get_token("customer2@test.com", "customer")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def admin_headers():
    token = get_token("admin@test.com", "admin")
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_create_and_view_own_order(client: AsyncClient, customer1_headers: dict):
    # Create order
    order_data = {
        "user_id": "ignored",  # Should be overridden by deps
        "total_amount": 100.50,
        "items": [
            {"product_id": "prod-1", "quantity": 2, "price": 50.25}
        ]
    }
    response = await client.post("/orders/", json=order_data, headers=customer1_headers)
    assert response.status_code == 201
    created_order = response.json()
    order_id = created_order["id"]

    # View own order
    response = await client.get(f"/orders/{order_id}", headers=customer1_headers)
    assert response.status_code == 200

    # List own orders
    response = await client.get("/orders/", headers=customer1_headers)
    assert response.status_code == 200
    orders = response.json()
    assert len(orders) >= 1
    assert any(o["id"] == order_id for o in orders)

@pytest.mark.asyncio
async def test_cannot_view_others_order(client: AsyncClient, customer1_headers: dict, customer2_headers: dict):
    # Customer 1 creates an order
    order_data = {
        "user_id": "ignored",
        "total_amount": 50.0,
        "items": [
            {"product_id": "prod-2", "quantity": 1, "price": 50.0}
        ]
    }
    response = await client.post("/orders/", json=order_data, headers=customer1_headers)
    assert response.status_code == 201
    order_id = response.json()["id"]

    # Customer 2 attempts to view it
    response = await client.get(f"/orders/{order_id}", headers=customer2_headers)
    assert response.status_code == 403
    
    # Customer 2 lists orders, shouldn't see Customer 1's order
    response = await client.get("/orders/", headers=customer2_headers)
    orders = response.json()
    assert not any(o["id"] == order_id for o in orders)

@pytest.mark.asyncio
async def test_admin_can_view_all_orders(client: AsyncClient, customer1_headers: dict, admin_headers: dict):
    # Customer 1 creates an order
    order_data = {
        "user_id": "ignored",
        "total_amount": 25.0,
        "items": [
            {"product_id": "prod-3", "quantity": 1, "price": 25.0}
        ]
    }
    response = await client.post("/orders/", json=order_data, headers=customer1_headers)
    assert response.status_code == 201
    order_id = response.json()["id"]

    # Admin views the order directly
    response = await client.get(f"/orders/{order_id}", headers=admin_headers)
    assert response.status_code == 200

    # Admin lists orders
    response = await client.get("/orders/", headers=admin_headers)
    assert response.status_code == 200
    orders = response.json()
    assert any(o["id"] == order_id for o in orders)
