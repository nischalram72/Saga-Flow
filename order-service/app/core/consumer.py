import asyncio
import json
import logging
# pyrefly: ignore [missing-import]
import aio_pika
# pyrefly: ignore [missing-import]
from sqlalchemy.future import select

from app.core.rabbitmq import rabbitmq_client
from app.db.database import AsyncSessionLocal
from app.models.order import Order, OrderStatus

logger = logging.getLogger(__name__)

async def process_message(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            payload = json.loads(message.body.decode())
            print(f"Order Service received event: {payload}")
            
            action = payload.get("action")
            if action == "OrderConfirmed":
                order_id = payload.get("order_id")
                
                async with AsyncSessionLocal() as session:
                    existing = await session.execute(select(Order).filter(Order.id == order_id))
                    order = existing.scalar_one_or_none()
                    
                    if order:
                        order.status = OrderStatus.CONFIRMED
                        await session.commit()
                        print(f"Order {order_id} status updated to CONFIRMED")
                    else:
                        print(f"Order {order_id} not found")
            elif action == "OrderRejectRequested":
                order_id = payload.get("order_id")
                
                async with AsyncSessionLocal() as session:
                    existing = await session.execute(select(Order).filter(Order.id == order_id))
                    order = existing.scalar_one_or_none()
                    
                    if order:
                        order.status = OrderStatus.REJECTED
                        await session.commit()
                        print(f"Order {order_id} status updated to REJECTED")
                    else:
                        print(f"Order {order_id} not found")

        except Exception as e:
            print(f"Error processing order message: {e}")
        
async def consume_saga_events():
    channel = await rabbitmq_client.get_channel()
    exchange = await channel.declare_exchange("orchestrator_exchange", aio_pika.ExchangeType.FANOUT, durable=True)
    
    queue = await channel.declare_queue("order_saga_events_queue", durable=True)
    await queue.bind(exchange)
    
    print("Order Service listening for Saga events...")
    await queue.consume(process_message)

def start_consumer():
    asyncio.create_task(consume_saga_events())
