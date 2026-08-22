# pyrefly: ignore [missing-import]
from fastapi import WebSocket
from typing import Dict, List
import json

class ConnectionManager:
    def __init__(self):
        # Maps order_id to a list of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, order_id: str):
        await websocket.accept()
        if order_id not in self.active_connections:
            self.active_connections[order_id] = []
        self.active_connections[order_id].append(websocket)
        print(f"WebSocket connected for order {order_id}")

    def disconnect(self, websocket: WebSocket, order_id: str):
        if order_id in self.active_connections:
            self.active_connections[order_id].remove(websocket)
            if not self.active_connections[order_id]:
                del self.active_connections[order_id]
        print(f"WebSocket disconnected for order {order_id}")

    async def broadcast_to_order(self, order_id: str, message: dict):
        if order_id in self.active_connections:
            # We convert dict to JSON string before sending
            json_str = json.dumps(message)
            for connection in self.active_connections[order_id]:
                try:
                    await connection.send_text(json_str)
                except Exception as e:
                    print(f"Failed to send WS message: {e}")

manager = ConnectionManager()
