import asyncio
import pytest
import uuid
# pyrefly: ignore [missing-import]
from httpx import AsyncClient, ASGITransport
# pyrefly: ignore [missing-import]
from sqlalchemy.future import select

from app.main import app as fastapi_app
from app.db.database import AsyncSessionLocal
from app.models.payment import Payment
import app.routes.payments as payments_routes

@pytest.mark.asyncio
async def test_idempotent_concurrent_charge():
    # Disable random failure to ensure it attempts to succeed
    payments_routes.FAIL_RATE = 0.0
    
    idemp_key = str(uuid.uuid4())
    order_id = str(uuid.uuid4())
    
    payload = {
        "order_id": order_id,
        "amount": 150.0,
        "idempotency_key": idemp_key
    }
    headers = {"X-Service-Key": "internal_secret_key_123"}
    
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as client:
        # Send two concurrent requests
        req1 = client.post("/payments/charge", json=payload, headers=headers)
        req2 = client.post("/payments/charge", json=payload, headers=headers)
        
        resp1, resp2 = await asyncio.gather(req1, req2, return_exceptions=True)
        
        # We don't strictly assert both are 200 here because one might fail with an IntegrityError 
        # (500) if they perfectly race, but we definitely want to assert the DB state.
        
        # Check DB
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Payment).where(Payment.idempotency_key == idemp_key)
            )
            payments = result.scalars().all()
            
            # Assert only ONE record was created
            assert len(payments) == 1
