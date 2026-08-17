import asyncio
import json
import logging
# pyrefly: ignore [missing-import]
import aio_pika
# pyrefly: ignore [missing-import]
from sqlalchemy.future import select

from app.core.rabbitmq import rabbitmq_client
from app.db.database import AsyncSessionLocal
from app.models.inventory import Inventory, Reservation, ReservationStatus

logger = logging.getLogger(__name__)

async def process_message(message: aio_pika.IncomingMessage):
    async with message.process():
        payload = json.loads(message.body.decode())
        print(f"Inventory Service received event: {payload}")
        
        action = payload.get("action")
        if action == "InventoryReserveRequested":
            saga_id = payload.get("saga_id")
            items = payload.get("items", [])
            
            max_retries = 3
            for attempt in range(max_retries + 1):
                try:
                    async with AsyncSessionLocal() as session:
                        success = True
                        for item in items:
                            product_id = item.get("product_id")
                            qty = item.get("quantity", 1)
                            
                            existing = await session.execute(select(Inventory).filter(Inventory.product_id == product_id))
                            product = existing.scalar_one_or_none()
                            
                            if product and product.available_qty >= qty:
                                product.available_qty -= qty
                                product.reserved_qty += qty
                                
                                reservation = Reservation(
                                    order_id=payload.get("order_id"),
                                    product_id=product_id,
                                    qty=qty,
                                    status=ReservationStatus.CONFIRMED
                                )
                                session.add(reservation)
                            else:
                                print(f"Failed to reserve {qty} of {product_id}")
                                success = False
                                break
                        
                        if success:
                            await session.commit()
                            
                            # Publish InventoryReserved event
                            channel = await rabbitmq_client.get_channel()
                            exchange = await channel.declare_exchange("orchestrator_exchange", aio_pika.ExchangeType.FANOUT, durable=True)
                            
                            result_payload = {
                                "saga_id": saga_id,
                                "order_id": payload.get("order_id"),
                                "action": "InventoryReserved"
                            }
                            
                            message_body = aio_pika.Message(
                                body=json.dumps(result_payload).encode(),
                                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                            )
                            await exchange.publish(message_body, routing_key="")
                            print(f"Inventory Service published InventoryReserved for saga {saga_id}")
                        else:
                            await session.rollback()
                            print(f"Inventory reservation failed for saga {saga_id}")
                            # In a real app we'd publish InventoryReserveFailed here.
                        
                    # If we reach here without exceptions, break out of retry loop
                    break
                except Exception as e:
                    if attempt < max_retries:
                        backoff = 2 ** attempt  # 1s, 2s, 4s
                        print(f"Transient error processing message (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {backoff}s...")
                        await asyncio.sleep(backoff)
                    else:
                        print(f"Error processing inventory message after {max_retries} retries: {e}")
                        try:
                            channel = await rabbitmq_client.get_channel()
                            dlq_exchange = await channel.declare_exchange("dlq_exchange", aio_pika.ExchangeType.FANOUT, durable=True)
                            dlq_queue = await channel.declare_queue("dead_letter_queue", durable=True)
                            await dlq_queue.bind(dlq_exchange)
                            
                            await dlq_exchange.publish(
                                aio_pika.Message(
                                    body=message.body,
                                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                                ),
                                routing_key=""
                            )
                            print(f"Published failed message to DLQ: {payload}")
                        except Exception as dlq_e:
                            print(f"Failed to publish to DLQ: {dlq_e}")
                            
        elif action == "InventoryReleaseRequested":
            saga_id = payload.get("saga_id")
            order_id = payload.get("order_id")
            
            max_retries = 3
            for attempt in range(max_retries + 1):
                try:
                    async with AsyncSessionLocal() as session:
                        reservations_result = await session.execute(
                            select(Reservation).filter(
                                Reservation.order_id == order_id, 
                                Reservation.status == ReservationStatus.CONFIRMED
                            )
                        )
                        reservations = reservations_result.scalars().all()
                        
                        for res in reservations:
                            res.status = ReservationStatus.CANCELLED
                            
                            product_result = await session.execute(select(Inventory).filter(Inventory.product_id == res.product_id))
                            product = product_result.scalar_one_or_none()
                            if product:
                                product.available_qty += res.qty
                                product.reserved_qty -= res.qty
                        
                        await session.commit()
                        
                        channel = await rabbitmq_client.get_channel()
                        exchange = await channel.declare_exchange("orchestrator_exchange", aio_pika.ExchangeType.FANOUT, durable=True)
                        
                        result_payload = {
                            "saga_id": saga_id,
                            "order_id": order_id,
                            "action": "InventoryReleased"
                        }
                        
                        message_body = aio_pika.Message(
                            body=json.dumps(result_payload).encode(),
                            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                        )
                        await exchange.publish(message_body, routing_key="")
                        print(f"Inventory Service published InventoryReleased for saga {saga_id}")
                        
                    break
                except Exception as e:
                    if attempt < max_retries:
                        backoff = 2 ** attempt  # 1s, 2s, 4s
                        print(f"Transient error processing message (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {backoff}s...")
                        await asyncio.sleep(backoff)
                    else:
                        print(f"Error processing inventory message after {max_retries} retries: {e}")
                        try:
                            channel = await rabbitmq_client.get_channel()
                            dlq_exchange = await channel.declare_exchange("dlq_exchange", aio_pika.ExchangeType.FANOUT, durable=True)
                            dlq_queue = await channel.declare_queue("dead_letter_queue", durable=True)
                            await dlq_queue.bind(dlq_exchange)
                            
                            await dlq_exchange.publish(
                                aio_pika.Message(
                                    body=message.body,
                                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                                ),
                                routing_key=""
                            )
                            print(f"Published failed message to DLQ: {payload}")
                        except Exception as dlq_e:
                            print(f"Failed to publish to DLQ: {dlq_e}")
        
# pyrefly: ignore [parse-error]
async def consume_orders():
    channel = await rabbitmq_client.get_channel()
    exchange = await channel.declare_exchange("orchestrator_exchange", aio_pika.ExchangeType.FANOUT, durable=True)
    
    queue = await channel.declare_queue("inventory_saga_queue", durable=True)
    await queue.bind(exchange)
    
    print("Inventory Service listening for Saga events...")
    await queue.consume(process_message)

def start_consumer():
    asyncio.create_task(consume_orders())
