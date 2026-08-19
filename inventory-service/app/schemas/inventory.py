from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from app.models.inventory import ReservationStatus

class ReserveItem(BaseModel):
    product_id: str
    quantity: int

class ReserveRequest(BaseModel):
    order_id: str
    items: List[ReserveItem]

class ReleaseRequest(BaseModel):
    order_id: str

class ReservationResponse(BaseModel):
    id: UUID
    order_id: str
    product_id: str
    qty: int
    status: ReservationStatus
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True

class InventoryResponse(BaseModel):
    product_id: str
    available_qty: int
    reserved_qty: int

    class Config:
        from_attributes = True
