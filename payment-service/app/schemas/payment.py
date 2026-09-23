from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from app.models.payment import PaymentStatus

class ChargeRequest(BaseModel):
    order_id: str
    amount: float
    idempotency_key: str

class RefundRequest(BaseModel):
    order_id: str

class PaymentResponse(BaseModel):
    id: UUID
    order_id: str
    amount: float
    status: PaymentStatus
    idempotency_key: str

    class Config:
        from_attributes = True
