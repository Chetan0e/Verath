from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
import json
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"WebSocket connected for user {user_id}")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending WebSocket message to {user_id}: {e}")
                self.disconnect(user_id)

    async def broadcast(self, message: dict):
        """Send message to all connected users."""
        for user_id, connection in self.active_connections.items():
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {user_id}: {e}")


manager = ConnectionManager()


@router.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    Clients must send {"type": "auth", "token": "<jwt>"} as the first message.
    Token is never passed in the URL to avoid server log exposure.
    """
    await websocket.accept()

    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        message = json.loads(raw)
    except asyncio.TimeoutError:
        await websocket.close(code=4001, reason="Auth timeout")
        return
    except Exception:
        await websocket.close(code=4001, reason="Invalid auth frame")
        return

    if not isinstance(message, dict) or message.get("type") != "auth":
        await websocket.close(code=4001, reason="Expected auth frame")
        return

    token = message.get("token", "")

    try:
        from app.services.auth import verify_access_token
        user_id = await verify_access_token(token)
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
    except Exception as e:
        logger.error(f"WebSocket auth failed: {e}")
        await websocket.close(code=4001, reason="Authentication failed")
        return

    manager.active_connections[user_id] = websocket
    logger.info(f"WebSocket connected for user {user_id}")

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(user_id)