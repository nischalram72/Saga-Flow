# pyrefly: ignore [missing-import]
from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio

from app.core.rabbitmq import rabbitmq_client
from app.core.consumer import consume_orders

# Import models so Alembic can see them
import app.models.models

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup RabbitMQ connection
    await rabbitmq_client.connect()
    
    # Start consumer
    task = asyncio.create_task(consume_orders())
    
    yield
    
    # Cleanup
    task.cancel()
    await rabbitmq_client.close()

# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
from fastapi import WebSocket, WebSocketDisconnect
from app.core.websockets import manager

app = FastAPI(title="Saga Flow - Orchestrator Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/sagas/{order_id}")
async def websocket_endpoint(websocket: WebSocket, order_id: str):
    await manager.connect(websocket, order_id)
    try:
        while True:
            # We just keep the connection open, no need to receive messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, order_id)

@app.get("/")
async def root():
    return {"message": "Orchestrator Service is running"}

import json
# pyrefly: ignore [missing-import]
import aio_pika

@app.get("/dlq")
async def get_dlq():
    try:
        channel = await rabbitmq_client.get_channel()
        dlq_queue = await channel.declare_queue("dead_letter_queue", durable=True)
        
        messages = []
        while True:
            # Get message from the queue, return None if empty
            message = await dlq_queue.get(fail=False, no_ack=True)
            if not message:
                break
            
            try:
                payload_str = message.body.decode()
                try:
                    payload = json.loads(payload_str)
                except json.JSONDecodeError:
                    payload = payload_str
                messages.append(payload)
            except Exception as e:
                messages.append({"error": str(e)})
                
        return {"dlq_messages": messages, "count": len(messages)}
    except Exception as e:
        return {"error": str(e)}

from app.db.database import AsyncSessionLocal
from app.models.models import SagaInstance, SagaStep
# pyrefly: ignore [missing-import]
from sqlalchemy.future import select

@app.get("/sagas/{order_id}")
async def get_saga_history(order_id: str):
    async with AsyncSessionLocal() as session:
        # Fetch SagaInstance
        result = await session.execute(
            select(SagaInstance).filter(SagaInstance.order_id == order_id)
        )
        saga = result.scalar_one_or_none()
        
        if not saga:
            return {"error": f"Saga for order {order_id} not found."}
            
        # Fetch SagaSteps ordered by created_at
        steps_result = await session.execute(
            select(SagaStep)
            .filter(SagaStep.saga_id == saga.id)
            .order_by(SagaStep.created_at.asc())
        )
        steps = steps_result.scalars().all()
        
        return {
            "saga_id": str(saga.id),
            "order_id": saga.order_id,
            "current_step": saga.current_step,
            "status": saga.status,
            "created_at": saga.created_at.isoformat() if saga.created_at else None,
            "updated_at": saga.updated_at.isoformat() if saga.updated_at else None,
            "steps": [
                {
                    "id": str(step.id),
                    "step_name": step.step_name,
                    "status": step.status,
                    "created_at": step.created_at.isoformat() if step.created_at else None,
                    "compensated_at": step.compensated_at.isoformat() if step.compensated_at else None
                }
                for step in steps
            ]
        }

from typing import Optional

@app.get("/sagas")
async def get_sagas(status: Optional[str] = None):
    async with AsyncSessionLocal() as session:
        query = select(SagaInstance)
        if status:
            query = query.filter(SagaInstance.status == status)
            
        result = await session.execute(query.order_by(SagaInstance.created_at.desc()))
        sagas = result.scalars().all()
        
        return {
            "sagas": [
                {
                    "saga_id": str(saga.id),
                    "order_id": saga.order_id,
                    "current_step": saga.current_step,
                    "status": saga.status,
                    "created_at": saga.created_at.isoformat() if saga.created_at else None,
                    "updated_at": saga.updated_at.isoformat() if saga.updated_at else None,
                }
                for saga in sagas
            ],
            "count": len(sagas)
        }
