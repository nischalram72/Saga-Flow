# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
# pyrefly: ignore [missing-import]
from sqlalchemy.future import select
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID

import json
# pyrefly: ignore [missing-import]
import aio_pika

from app.db.database import get_db
from app.models.order import Order, OrderItem
from app.models.user import User
from app.schemas.order import OrderCreate, OrderResponse
from app.api.deps import get_current_user
from app.core.rabbitmq import rabbitmq_client
from app.schemas.order import OrderCreate, OrderResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(order_in: OrderCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_order = Order(
        user_id=str(current_user.id),
        total_amount=order_in.total_amount,
        address=order_in.address,
        phone=order_in.phone,
        pincode=order_in.pincode
    )
    db.add(new_order)
    await db.flush()

    for item in order_in.items:
        new_item = OrderItem(
            order_id=new_order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.price
        )
        db.add(new_item)

    await db.commit()
    
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).filter(Order.id == new_order.id)
    )
    order_res = result.scalar_one()
    
    # Publish OrderCreated event
    try:
        channel = await rabbitmq_client.get_channel()
        exchange = await channel.declare_exchange("orders_exchange", type=aio_pika.ExchangeType.FANOUT)
        
        # Serialize the order to JSON
        # We need a dict representation to serialize
        order_dict = {
            "id": str(order_res.id),
            "user_id": order_res.user_id,
            "total_amount": order_res.total_amount,
            "status": order_res.status.value,
            "simulate_payment_failure": order_in.simulate_payment_failure,
            "items": [{"product_id": item.product_id, "quantity": item.quantity, "price": item.price} for item in order_res.items]
        }
        message_body = json.dumps(order_dict).encode()
        
        await exchange.publish(
            aio_pika.Message(body=message_body),
            routing_key=""
        )
    except Exception as e:
        print(f"Failed to publish OrderCreated event: {e}")
        
    return order_res

@router.get("/{id}", response_model=OrderResponse)
async def get_order(id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).filter(Order.id == id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail={"error": "Order not found"})
    
    if current_user.role.value != "admin" and order.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail={"error": "Not enough permissions"})
        
    return order

@router.get("/", response_model=List[OrderResponse])
async def list_orders(user_id: Optional[str] = None, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = select(Order).options(selectinload(Order.items))
    
    if current_user.role.value == "admin":
        if user_id:
            query = query.filter(Order.user_id == user_id)
    else:
        # Customer can only see their own orders
        query = query.filter(Order.user_id == str(current_user.id))
    
    result = await db.execute(query)
    return result.scalars().all()
