import asyncio
import httpx
# pyrefly: ignore [missing-import]
import pytest

@pytest.mark.asyncio
async def test_successful_saga_flow():
    # Service URLs
    ORDER_SERVICE = "http://127.0.0.1:8001"
    ORCHESTRATOR_SERVICE = "http://127.0.0.1:8004"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Register a test user
        print("\n[1] Registering user...")
        # Ignore error if user already exists
        await client.post(f"{ORDER_SERVICE}/auth/register", json={
            "email": "pytest_e2e@example.com",
            "password": "password123",
            "role": "customer"
        })
        
        # 2. Login to get token
        print("[2] Logging in...")
        resp = await client.post(f"{ORDER_SERVICE}/auth/login", data={
            "username": "pytest_e2e@example.com",
            "password": "password123"
        })
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        token = resp.json().get("access_token")
        assert token is not None
        
        # 3. Create an order with fail_rate: 0
        print("[3] Creating order...")
        headers = {"Authorization": f"Bearer {token}"}
        order_payload = {
            "user_id": "ignored",
            "total_amount": 50.0,
            "items": [
                {"product_id": "prod-1", "quantity": 2, "price": 25.0}
            ],
            "fail_rate": 0
        }
        
        resp = await client.post(f"{ORDER_SERVICE}/orders/", json=order_payload, headers=headers)
        assert resp.status_code == 201, f"Order creation failed: {resp.text}"
        
        order_data = resp.json()
        order_id = order_data["id"]
        print(f"Created order: {order_id}")
        
        # 4. Poll saga status until it finishes
        print("[4] Polling saga status...")
        saga_completed = False
        max_attempts = 15
        
        for attempt in range(max_attempts):
            await asyncio.sleep(2)  # Wait for saga steps to execute
            
            saga_resp = await client.get(f"{ORCHESTRATOR_SERVICE}/sagas/{order_id}")
            if saga_resp.status_code == 200:
                saga_data = saga_resp.json()
                status = saga_data.get("status")
                print(f"Saga attempt {attempt + 1}: status = {status}")
                
                if status == "COMPLETED":
                    saga_completed = True
                    break
                elif status == "FAILED":
                    pytest.fail(f"Saga failed instead of completing: {saga_data}")
            else:
                print(f"Saga not found yet (attempt {attempt + 1})")
                
        assert saga_completed, "Saga did not complete within the expected time."
        
        # 5. Assert the final order status is CONFIRMED
        print("[5] Verifying final order status...")
        order_resp = await client.get(f"{ORDER_SERVICE}/orders/{order_id}", headers=headers)
        assert order_resp.status_code == 200, f"Failed to fetch order: {order_resp.text}"
        
        final_order = order_resp.json()
        print(f"Final order status: {final_order['status']}")
        assert final_order["status"] == "CONFIRMED", f"Expected order status CONFIRMED, got {final_order['status']}"

@pytest.mark.asyncio
async def test_failed_saga_flow():
    # Service URLs
    ORDER_SERVICE = "http://127.0.0.1:8001"
    ORCHESTRATOR_SERVICE = "http://127.0.0.1:8004"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("\n[1] Registering user for failure test...")
        await client.post(f"{ORDER_SERVICE}/auth/register", json={
            "email": "fail_e2e@example.com",
            "password": "password123",
            "role": "customer"
        })
        
        print("[2] Logging in...")
        resp = await client.post(f"{ORDER_SERVICE}/auth/login", data={
            "username": "fail_e2e@example.com",
            "password": "password123"
        })
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        token = resp.json().get("access_token")
        
        print("[3] Creating order with fail_rate: 1.0...")
        headers = {"Authorization": f"Bearer {token}"}
        order_payload = {
            "user_id": "ignored",
            "total_amount": 50.0,
            "items": [
                {"product_id": "prod-1", "quantity": 1, "price": 50.0}
            ],
            "fail_rate": 1.0
        }
        
        resp = await client.post(f"{ORDER_SERVICE}/orders/", json=order_payload, headers=headers)
        assert resp.status_code == 201, f"Order creation failed: {resp.text}"
        
        order_data = resp.json()
        order_id = order_data["id"]
        print(f"Created order: {order_id}")
        
        print("[4] Polling saga status...")
        saga_failed = False
        max_attempts = 15
        
        for attempt in range(max_attempts):
            await asyncio.sleep(2)
            
            saga_resp = await client.get(f"{ORCHESTRATOR_SERVICE}/sagas/{order_id}")
            if saga_resp.status_code == 200:
                saga_data = saga_resp.json()
                status = saga_data.get("status")
                print(f"Saga attempt {attempt + 1}: status = {status}")
                
                if status == "FAILED":
                    saga_failed = True
                    break
                elif status == "COMPLETED":
                    pytest.fail(f"Saga completed instead of failing: {saga_data}")
        
        assert saga_failed, "Saga did not fail within the expected time."
        
        print("[5] Verifying order status is FAILED/REJECTED...")
        order_resp = await client.get(f"{ORDER_SERVICE}/orders/{order_id}", headers=headers)
        assert order_resp.status_code == 200
        final_order = order_resp.json()
        print(f"Final order status: {final_order['status']}")
        assert final_order["status"] in ["FAILED", "REJECTED"], f"Expected order status FAILED or REJECTED, got {final_order['status']}"
        
        print("[6] Verifying saga_steps contains a compensated_at timestamp...")
        saga_resp = await client.get(f"{ORCHESTRATOR_SERVICE}/sagas/{order_id}")
        saga_data = saga_resp.json()
        steps = saga_data.get("steps", [])
        
        # At least one step should be COMPENSATED
        compensated_step = next((s for s in steps if s.get("status") == "COMPENSATED"), None)
        assert compensated_step is not None, "No step was compensated!"
        assert compensated_step.get("compensated_at") is not None, "compensated_at timestamp is missing!"
        
        print("[7] Verifying inventory reservation was released...")
        import os
        # pyrefly: ignore [missing-import]
        from sqlalchemy.ext.asyncio import create_async_engine
        # pyrefly: ignore [missing-import]
        from sqlalchemy import text
        from dotenv import load_dotenv
        
        load_dotenv("orchestrator-service/.env")
        db_url = os.getenv("DATABASE_URL")
        
        if db_url:
            engine = create_async_engine(db_url)
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT status FROM reservations WHERE order_id = :order_id"), {"order_id": order_id})
                reservations = result.fetchall()
                if reservations:
                    for res in reservations:
                        assert res[0] == "CANCELLED", f"Reservation status is not CANCELLED: {res[0]}"
                else:
                    print("No reservations found (maybe it failed before reservation).")
            await engine.dispose()
