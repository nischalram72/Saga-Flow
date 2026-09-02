from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from app.models.order import OrderStatus

class OrderItemCreate(BaseModel):
    product_id: str
    quantity: int = Field(gt=0, description="Quantity must be greater than 0")
    price: float = Field(gt=0, description="Price must be greater than 0")

class OrderItemResponse(OrderItemCreate):
    id: UUID
    order_id: UUID
    model_config = ConfigDict(from_attributes=True)

class OrderCreate(BaseModel):
    user_id: str
    total_amount: float
    address: Optional[str] = None
    phone: Optional[str] = None
    pincode: Optional[str] = None
    items: List[OrderItemCreate] = Field(min_length=1)
    simulate_payment_failure: Optional[bool] = False

    @model_validator(mode='after')
    def check_total_amount(self):
        calculated_total = sum(item.quantity * item.price for item in self.items)
        if abs(calculated_total - self.total_amount) > 0.01:
            raise ValueError(f"total_amount ({self.total_amount}) does not match sum of items ({calculated_total})")
        return self

class OrderResponse(BaseModel):
    id: UUID
    user_id: str
    status: OrderStatus
    total_amount: float
    address: Optional[str] = None
    phone: Optional[str] = None
    pincode: Optional[str] = None
    created_at: datetime
    items: List[OrderItemResponse]
    model_config = ConfigDict(from_attributes=True)
