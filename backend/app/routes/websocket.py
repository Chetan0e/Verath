from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
import json

from app.services.ws_tickets import ticket_store

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept the handshake and register the connection.

        This is the single path that calls websocket.accept() — callers
        must not call accept() themselves beforehand.
        """
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
        disconnected = []
        for user_id, connection in list(self.active_connections.items()):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {user_id}: {e}")
                disconnected.append(user_id)
        for user_id in disconnected:
            self.disconnect(user_id)


manager = ConnectionManager()


@router.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.

    Authentication is performed BEFORE accept() using a short-lived,
    single-use `ticket` query parameter (e.g.
    wss://host/ws/updates?ticket=<ticket>), minted in advance via
    POST /ws/ticket. Unlike a raw JWT, a leaked ticket in an access log
    or proxy trace is worthless: it expires in a few seconds and can
    only ever be redeemed once.

    Rejecting pre-accept avoids allocating a file descriptor, I/O
    buffers, or an entry in active_connections for unauthenticated
    clients. All connection lifecycle operations are routed through
    ConnectionManager so that accept() is called in exactly one place.
    """
    ticket = websocket.query_params.get("ticket", "")

    # ── Authenticate before accepting the handshake ───────────────────────
    if not ticket:
        await websocket.close(code=4001, reason="Missing ticket")
        return

    try:
        user_id = ticket_store.redeem(ticket)
    except Exception as e:
        logger.error(f"WebSocket ticket redemption error: {e}")
        await websocket.close(code=4001, reason="Authentication failed")
        return

    if not user_id:
        await websocket.close(code=4001, reason="Invalid or expired ticket")
        return

    # ── Accept and register through the single authoritative path ────────
    await manager.connect(websocket, user_id)

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