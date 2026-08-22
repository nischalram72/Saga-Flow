import json
import asyncio
# pyrefly: ignore [missing-import]
import aio_pika
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
# pyrefly: ignore [missing-import]
from sqlalchemy.future import select

from app.core.rabbitmq import rabbitmq_client
from app.db.database import AsyncSessionLocal
from app.models.models import SagaInstance, SagaStep
from app.core.websockets import manager

async def process_message(message: aio_pika.IncomingMessage):
    async with message.process():
        payload = json.loads(message.body.decode())
        print(f"Orchestrator Service received event: {payload}")
        
        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                async with AsyncSessionLocal() as session:
                    # 1. Handle OrderCreated (from order-service)
                    if "total_amount" in payload and "action" not in payload:
                        order_id = payload.get("id")
                        if not order_id:
                            print("Missing order_id in payload.")
                            return
                            
                        existing = await session.execute(select(SagaInstance).filter(SagaInstance.order_id == order_id))
                        saga = existing.scalar_one_or_none()
                        if saga:
                            print(f"Saga for order {order_id} already exists.")
                            return
                        
                        saga = SagaInstance(
                            order_id=order_id,
                            current_step="INVENTORY_RESERVE_REQUESTED",
                            status="PENDING",
                            simulate_payment_failure=payload.get("simulate_payment_failure", False)
                        )
                        session.add(saga)
                        await session.flush()
                        
                        session.add(SagaStep(saga_id=saga.id, step_name="ORDER_CREATED_RECEIVED", status="SUCCESS"))
                        
                        channel = await rabbitmq_client.get_channel()
                        exchange = await channel.declare_exchange("orchestrator_exchange", aio_pika.ExchangeType.FANOUT, durable=True)
                        
                        inventory_payload = {
                            "saga_id": str(saga.id),
                            "order_id": order_id,
                            "items": payload.get("items", []),
                            "action": "InventoryReserveRequested"
                        }
                        
                        await exchange.publish(
                            aio_pika.Message(body=json.dumps(inventory_payload).encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
                            routing_key=""
                        )
                        print(f"Published InventoryReserveRequested for saga {saga.id}")
                        
                        session.add(SagaStep(saga_id=saga.id, step_name="INVENTORY_RESERVE_REQUESTED", status="SUCCESS"))
                        await session.commit()
                        
                        await manager.broadcast_to_order(order_id, {
                            "type": "SAGA_UPDATE",
                            "current_step": saga.current_step,
                            "status": saga.status,
                            "step_name": "INVENTORY_RESERVE_REQUESTED"
                        })
                        
                    # 2. Handle Saga Responses
                    action = payload.get("action")
                    if not action:
                        return
    
                    saga_id = payload.get("saga_id")
                    if not saga_id:
                        return
    
                    existing = await session.execute(select(SagaInstance).filter(SagaInstance.id == saga_id))
                    saga = existing.scalar_one_or_none()
                    if not saga:
                        print(f"Saga {saga_id} not found.")
                        return
    
                    if action == "InventoryReserved":
                        session.add(SagaStep(saga_id=saga.id, step_name="INVENTORY_RESERVED", status="SUCCESS"))
                        saga.current_step = "PAYMENT_REQUESTED"
                        
                        channel = await rabbitmq_client.get_channel()
                        exchange = await channel.declare_exchange("orchestrator_exchange", aio_pika.ExchangeType.FANOUT, durable=True)
                        
                        payment_payload = {
                            "saga_id": str(saga.id),
                            "order_id": saga.order_id,
                            "action": "PaymentRequested",
                            "simulate_payment_failure": saga.simulate_payment_failure
                        }
                        
                        await exchange.publish(
                            aio_pika.Message(body=json.dumps(payment_payload).encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
                            routing_key=""
                        )
                        print(f"Published PaymentRequested for saga {saga.id}")
                        
                        session.add(SagaStep(saga_id=saga.id, step_name="PAYMENT_REQUESTED", status="SUCCESS"))
                        await session.commit()
                        
                        await manager.broadcast_to_order(saga.order_id, {
                            "type": "SAGA_UPDATE",
                            "current_step": saga.current_step,
                            "status": saga.status,
                            "step_name": "INVENTORY_RESERVED"
                        })
    
                    elif action == "PaymentCompleted":
                        session.add(SagaStep(saga_id=saga.id, step_name="PAYMENT_COMPLETED", status="SUCCESS"))
                        saga.current_step = "ORDER_CONFIRMED"
                        saga.status = "COMPLETED"
                        
                        channel = await rabbitmq_client.get_channel()
                        exchange = await channel.declare_exchange("orchestrator_exchange", aio_pika.ExchangeType.FANOUT, durable=True)
                        
                        confirm_payload = {
                            "saga_id": str(saga.id),
                            "order_id": saga.order_id,
                            "action": "OrderConfirmed"
                        }
                        
                        await exchange.publish(
                            aio_pika.Message(body=json.dumps(confirm_payload).encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
                            routing_key=""
                        )
                        print(f"Published OrderConfirmed for saga {saga.id}")
                        
                        session.add(SagaStep(saga_id=saga.id, step_name="ORDER_CONFIRMED", status="SUCCESS"))
                        await session.commit()
                        
                        await manager.broadcast_to_order(saga.order_id, {
                            "type": "SAGA_UPDATE",
                            "current_step": saga.current_step,
                            "status": saga.status,
                            "step_name": "PAYMENT_COMPLETED"
                        })
    
                    elif action == "PaymentFailed":
                        session.add(SagaStep(saga_id=saga.id, step_name="PAYMENT_FAILED", status="FAILED"))
                        saga.current_step = "INVENTORY_RELEASE_REQUESTED"
                        saga.status = "COMPENSATING"
                        
                        channel = await rabbitmq_client.get_channel()
                        exchange = await channel.declare_exchange("orchestrator_exchange", aio_pika.ExchangeType.FANOUT, durable=True)
                        
                        release_payload = {
                            "saga_id": str(saga.id),
                            "order_id": saga.order_id,
                            "action": "InventoryReleaseRequested"
                        }
                        
                        await exchange.publish(
                            aio_pika.Message(body=json.dumps(release_payload).encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
                            routing_key=""
                        )
                        print(f"Published InventoryReleaseRequested for saga {saga.id}")
                        
                        session.add(SagaStep(saga_id=saga.id, step_name="INVENTORY_RELEASE_REQUESTED", status="SUCCESS"))
                        await session.commit()
                        
                        await manager.broadcast_to_order(saga.order_id, {
                            "type": "SAGA_UPDATE",
                            "current_step": saga.current_step,
                            "status": saga.status,
                            "step_name": "PAYMENT_FAILED"
                        })

                    elif action == "InventoryReleased":
                        from datetime import datetime
                        # Mark INVENTORY_RESERVED as compensated
                        reserved_step = await session.execute(
                            select(SagaStep).filter(SagaStep.saga_id == saga.id, SagaStep.step_name == "INVENTORY_RESERVED")
                        )
                        reserved_step = reserved_step.scalar_one_or_none()
                        if reserved_step:
                            reserved_step.compensated_at = datetime.utcnow()
                            reserved_step.status = "COMPENSATED"
                            
                        session.add(SagaStep(saga_id=saga.id, step_name="INVENTORY_RELEASED", status="SUCCESS"))
                        saga.current_step = "ORDER_REJECT_REQUESTED"
                        saga.status = "FAILED"
                        
                        channel = await rabbitmq_client.get_channel()
                        exchange = await channel.declare_exchange("orchestrator_exchange", aio_pika.ExchangeType.FANOUT, durable=True)
                        
                        reject_payload = {
                            "saga_id": str(saga.id),
                            "order_id": saga.order_id,
                            "action": "OrderRejectRequested"
                        }
                        
                        await exchange.publish(
                            aio_pika.Message(body=json.dumps(reject_payload).encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
                            routing_key=""
                        )
                        print(f"Published OrderRejectRequested for saga {saga.id}")
                        
                        session.add(SagaStep(saga_id=saga.id, step_name="ORDER_REJECT_REQUESTED", status="SUCCESS"))
                        await session.commit()
                        
                        await manager.broadcast_to_order(saga.order_id, {
                            "type": "SAGA_UPDATE",
                            "current_step": saga.current_step,
                            "status": saga.status,
                            "step_name": "INVENTORY_RELEASED"
                        })
                # If we reach here without exceptions or returns, break out of retry loop
                break
                
            except Exception as e:
                if attempt < max_retries:
                    backoff = 2 ** attempt  # 1s, 2s, 4s
                    print(f"Transient error processing orchestrator message (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                else:
                    print(f"Error processing orchestrator message after {max_retries} retries: {e}")
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

async def consume_orders():
    try:
        channel = await rabbitmq_client.get_channel()
        
        # 1. Listen to OrderCreated (from order-service, FANOUT)
        orders_exchange = await channel.declare_exchange("orders_exchange", aio_pika.ExchangeType.FANOUT)
        orders_queue = await channel.declare_queue("orchestrator_orders_queue", durable=True)
        await orders_queue.bind(orders_exchange)
        await orders_queue.consume(process_message)
        
        # 2. Listen to Saga Events (from inventory/payment, FANOUT)
        events_exchange = await channel.declare_exchange("orchestrator_exchange", aio_pika.ExchangeType.FANOUT, durable=True)
        events_queue = await channel.declare_queue("orchestrator_saga_queue", durable=True)
        await events_queue.bind(events_exchange)
        await events_queue.consume(process_message)
        
        print("Orchestrator Service is waiting for messages...")
    except Exception as e:
        print(f"Error in consume_orders: {e}")
