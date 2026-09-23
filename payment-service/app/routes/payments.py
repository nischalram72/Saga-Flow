# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
# pyrefly: ignore [missing-import]
from sqlalchemy.future import select
import os
import random
import json
# pyrefly: ignore [missing-import]
import redis.asyncio as redis

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(redis_url, decode_responses=True)

from app.db.database import get_db
from app.models.payment import Payment, PaymentStatus
from app.schemas.payment import ChargeRequest, RefundRequest, PaymentResponse
from app.api.deps import verify_service_key

router = APIRouter(prefix="/payments", tags=["payments"], dependencies=[Depends(verify_service_key)])

FAIL_RATE = float(os.getenv("FAIL_RATE", "0.2"))

@router.post("/charge", response_model=PaymentResponse, status_code=status.HTTP_200_OK)
async def charge_payment(request: ChargeRequest, db: AsyncSession = Depends(get_db)):
    # Check Redis cache for idempotency
    cached_response = await redis_client.get(f"idempotency:{request.idempotency_key}")
    if cached_response:
        data = json.loads(cached_response)
        if data.get("status") == PaymentStatus.FAILED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment failed previously"
            )
        return data
        
    # Check idempotency in DB (fallback)
    result = await db.execute(select(Payment).where(Payment.idempotency_key == request.idempotency_key))
    existing_payment = result.scalar_one_or_none()
    
    if existing_payment:
        # Cache it for next time
        response_data = {
            "id": str(existing_payment.id),
            "order_id": existing_payment.order_id,
            "amount": existing_payment.amount,
            "status": existing_payment.status.value,
            "idempotency_key": existing_payment.idempotency_key
        }
        await redis_client.set(f"idempotency:{request.idempotency_key}", json.dumps(response_data), ex=86400)
        
        if existing_payment.status == PaymentStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment failed previously"
            )
        return existing_payment
        
    # Simulate failure based on FAIL_RATE
    payment_status = PaymentStatus.SUCCESS
    if random.random() < FAIL_RATE:
        payment_status = PaymentStatus.FAILED

    payment = Payment(
        order_id=request.order_id,
        amount=request.amount,
        status=payment_status,
        idempotency_key=request.idempotency_key
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    
    # Cache the response (success or failure)
    response_data = {
        "id": str(payment.id),
        "order_id": payment.order_id,
        "amount": payment.amount,
        "status": payment.status.value,
        "idempotency_key": payment.idempotency_key
    }
    await redis_client.set(f"idempotency:{request.idempotency_key}", json.dumps(response_data), ex=86400)
    
    if payment_status == PaymentStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment failed due to simulated random failure"
        )
        
    return payment

@router.post("/refund", status_code=status.HTTP_200_OK)
async def refund_payment(request: RefundRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Payment)
        .where(Payment.order_id == request.order_id)
        .where(Payment.status == PaymentStatus.SUCCESS)
    )
    payment = result.scalar_one_or_none()
    
    if not payment:
        return {"message": "No successful payment found to refund"}
        
    payment.status = PaymentStatus.REFUNDED
    await db.commit()
    
    return {"message": "Payment refunded successfully"}
