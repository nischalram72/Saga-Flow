import asyncio
import json
import logging
# pyrefly: ignore [missing-import]
import aio_pika
from app.core.rabbitmq import rabbitmq_client

logger = logging.getLogger(__name__)

async def process_message(message: aio_pika.IncomingMessage):
    async with message.process():
        payload = json.loads(message.body.decode())
        print(f"Payment Service received event: {payload}")
        
        action = payload.get("action")
        if action == "PaymentRequested":
            saga_id = payload.get("saga_id")
            order_id = payload.get("order_id")
            amount = payload.get("amount", 0.0)
            
            max_retries = 3
            for attempt in range(max_retries + 1):
                try:
                    # Mock processing payment
                    print(f"Processing payment of {amount} for order {order_id}...")
                    await asyncio.sleep(1) # Simulate delay
                    
                    import os
                    import random
                    fail_rate = float(os.getenv("FAIL_RATE", "0.2"))
                    force_fail = payload.get("simulate_payment_failure", False)
                    
                    channel = await rabbitmq_client.get_channel()
                    exchange = await channel.declare_exchange("orchestrator_exchange", aio_pika.ExchangeType.FANOUT, durable=True)
                    
                    if force_fail or random.random() < fail_rate:
                        if force_fail:
                            print(f"Payment FAILED for order {order_id} (Forced via UI toggle)")
                        else:
                            print(f"Payment FAILED for order {order_id} (simulated based on FAIL_RATE={fail_rate})")
                        result_payload = {
                            "saga_id": saga_id,
                            "order_id": order_id,
                            "action": "PaymentFailed"
                        }
                        message_body = aio_pika.Message(
                            body=json.dumps(result_payload).encode(),
                            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                        )
                        await exchange.publish(message_body, routing_key="")
                        print(f"Payment Service published PaymentFailed for saga {saga_id}")
                    else:
                        print(f"Payment successful for order {order_id}")
                        result_payload = {
                            "saga_id": saga_id,
                            "order_id": order_id,
                            "action": "PaymentCompleted"
                        }
                        message_body = aio_pika.Message(
                            body=json.dumps(result_payload).encode(),
                            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                        )
                        await exchange.publish(message_body, routing_key="")
                        print(f"Payment Service published PaymentCompleted for saga {saga_id}")
                    
                    # If we reach here without exceptions, break out of retry loop
                    break
                    
                except Exception as e:
                    if attempt < max_retries:
                        backoff = 2 ** attempt  # 1s, 2s, 4s
                        print(f"Transient error processing payment (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {backoff}s...")
                        await asyncio.sleep(backoff)
                    else:
                        print(f"Error processing payment message after {max_retries} retries: {e}")
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
    channel = await rabbitmq_client.get_channel()
    exchange = await channel.declare_exchange("orchestrator_exchange", aio_pika.ExchangeType.FANOUT, durable=True)
    
    queue = await channel.declare_queue("payment_saga_queue", durable=True)
    await queue.bind(exchange)
    
    print("Payment Service listening for Saga events...")
    await queue.consume(process_message)

def start_consumer():
    asyncio.create_task(consume_orders())
