# pyrefly: ignore [missing-import]
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.consumer import process_message
import os

class DummyAsyncContextManager:
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        pass

@pytest.mark.asyncio
async def test_process_payment_success():
    payload = {
        "action": "PaymentRequested",
        "saga_id": "saga-123",
        "order_id": "order-123",
        "amount": 100.0,
        "simulate_payment_failure": False
    }
    
    mock_message = MagicMock()
    mock_message.body = json.dumps(payload).encode()
    mock_message.process = MagicMock(return_value=DummyAsyncContextManager())
    
    mock_channel = AsyncMock()
    mock_exchange = AsyncMock()
    mock_channel.declare_exchange.return_value = mock_exchange
    
    with patch('app.core.consumer.rabbitmq_client.get_channel', return_value=mock_channel), \
         patch('random.random', return_value=0.9), \
         patch.dict(os.environ, {"FAIL_RATE": "0.2"}):
        
        await process_message(mock_message)
        
        assert mock_exchange.publish.called
        published_message = mock_exchange.publish.call_args[0][0]
        published_payload = json.loads(published_message.body.decode())
        
        assert published_payload["action"] == "PaymentCompleted"

@pytest.mark.asyncio
async def test_process_payment_simulated_failure():
    payload = {
        "action": "PaymentRequested",
        "saga_id": "saga-123",
        "order_id": "order-123",
        "amount": 100.0,
        "simulate_payment_failure": False
    }
    
    mock_message = MagicMock()
    mock_message.body = json.dumps(payload).encode()
    mock_message.process = MagicMock(return_value=DummyAsyncContextManager())
    
    mock_channel = AsyncMock()
    mock_exchange = AsyncMock()
    mock_channel.declare_exchange.return_value = mock_exchange
    
    with patch('app.core.consumer.rabbitmq_client.get_channel', return_value=mock_channel), \
         patch('random.random', return_value=0.1), \
         patch.dict(os.environ, {"FAIL_RATE": "0.2"}):
        
        await process_message(mock_message)
        
        assert mock_exchange.publish.called
        published_message = mock_exchange.publish.call_args[0][0]
        published_payload = json.loads(published_message.body.decode())
        
        assert published_payload["action"] == "PaymentFailed"

@pytest.mark.asyncio
async def test_process_payment_forced_failure():
    payload = {
        "action": "PaymentRequested",
        "saga_id": "saga-123",
        "order_id": "order-123",
        "amount": 100.0,
        "simulate_payment_failure": True
    }
    
    mock_message = MagicMock()
    mock_message.body = json.dumps(payload).encode()
    mock_message.process = MagicMock(return_value=DummyAsyncContextManager())
    
    mock_channel = AsyncMock()
    mock_exchange = AsyncMock()
    mock_channel.declare_exchange.return_value = mock_exchange
    
    with patch('app.core.consumer.rabbitmq_client.get_channel', return_value=mock_channel), \
         patch('random.random', return_value=0.9), \
         patch.dict(os.environ, {"FAIL_RATE": "0.2"}):
        
        await process_message(mock_message)
        
        assert mock_exchange.publish.called
        published_message = mock_exchange.publish.call_args[0][0]
        published_payload = json.loads(published_message.body.decode())
        
        assert published_payload["action"] == "PaymentFailed"
