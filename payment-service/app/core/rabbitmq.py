import os
import aio_pika
import logging

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@127.0.0.1/")

logger = logging.getLogger(__name__)

class RabbitMQClient:
    def __init__(self):
        self.connection = None
        self.channel = None

    async def connect(self):
        import asyncio
        max_retries = 5
        for attempt in range(max_retries):
            try:
                self.connection = await aio_pika.connect_robust(RABBITMQ_URL)
                self.channel = await self.connection.channel()
                logger.info("Connected to RabbitMQ successfully.")
                return
            except Exception as e:
                logger.error(f"Failed to connect to RabbitMQ (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2)

    async def close(self):
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("RabbitMQ connection closed.")

    async def get_channel(self) -> aio_pika.abc.AbstractChannel:
        if not self.channel:
            await self.connect()
        return self.channel

rabbitmq_client = RabbitMQClient()
