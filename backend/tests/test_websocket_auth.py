"""
Tests for — WebSocket accept-before-auth via short-lived tickets.

Verifies that:
1. Unauthenticated connections (missing or invalid/expired ticket) are
   rejected BEFORE accept() is called — ConnectionManager.connect() must
   never fire.
2. Authenticated connections go through manager.connect() exclusively —
   no direct dict writes to active_connections.
3. Tickets are single-use: redeeming twice fails the second time.
4. Tickets expire after their TTL.
5. After auth failure, no stale entry remains in active_connections.
6. send_personal_message and broadcast still work correctly.
7. broadcast handles a dead connection gracefully without raising.
8. ping/pong message handling continues to work.
9. POST /ws/ticket issues a ticket only for an authenticated caller.
"""
import time
import json
import pytest
from unittest.mock import AsyncMock, MagicMock


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_websocket(query_ticket=None):
    """Build a mock WebSocket with configurable query params."""
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.query_params = {"ticket": query_ticket} if query_ticket else {}
    return ws


# ── 1. Missing ticket is rejected pre-accept ─────────────────────────────────

class TestMissingTicket:
    async def test_no_ticket_closes_without_accept(self):
        ws = _make_websocket(query_ticket=None)

        from app.routes.websocket import websocket_endpoint, manager
        manager.active_connections.clear()

        await websocket_endpoint(ws)

        ws.accept.assert_not_called()
        ws.close.assert_called_once()
        close_kwargs = ws.close.call_args
        code = close_kwargs[1].get("code") or close_kwargs[0][0]
        assert code == 4001

    async def test_no_ticket_leaves_no_stale_connection(self):
        ws = _make_websocket(query_ticket=None)

        from app.routes.websocket import websocket_endpoint, manager
        manager.active_connections.clear()

        await websocket_endpoint(ws)

        assert manager.active_connections == {}


# ── 2. Invalid / expired / reused ticket is rejected pre-accept ─────────────

class TestInvalidTicket:
    async def test_unknown_ticket_closes_without_accept(self):
        ws = _make_websocket(query_ticket="not-a-real-ticket")

        from app.routes.websocket import websocket_endpoint, manager
        manager.active_connections.clear()

        await websocket_endpoint(ws)

        ws.accept.assert_not_called()
        ws.close.assert_called_once()
        assert manager.active_connections == {}

    async def test_expired_ticket_closes_without_accept(self):
        from app.services.ws_tickets import ticket_store

        ticket = ticket_store.issue("user-expired")
        # Force expiry without waiting out the real TTL.
        entry = ticket_store._tickets[ticket]
        entry.expires_at = time.time() - 1

        ws = _make_websocket(query_ticket=ticket)

        from app.routes.websocket import websocket_endpoint, manager
        manager.active_connections.clear()

        await websocket_endpoint(ws)

        ws.accept.assert_not_called()
        ws.close.assert_called_once()
        assert manager.active_connections == {}

    async def test_ticket_cannot_be_reused(self):
        """A ticket redeemed once must fail on a second connection attempt."""
        from app.services.ws_tickets import ticket_store
        from app.routes.websocket import websocket_endpoint, manager

        manager.active_connections.clear()
        ticket = ticket_store.issue("user-reuse")

        ws1 = _make_websocket(query_ticket=ticket)
        ws1.receive_text = AsyncMock(side_effect=Exception("stop loop"))
        await websocket_endpoint(ws1)
        ws1.accept.assert_called_once()

        manager.active_connections.clear()
        ws2 = _make_websocket(query_ticket=ticket)
        await websocket_endpoint(ws2)

        ws2.accept.assert_not_called()
        ws2.close.assert_called_once()

    async def test_redeem_error_closes_without_accept(self, monkeypatch):
        ws = _make_websocket(query_ticket="exploding-ticket")

        from app.routes import websocket as ws_module
        monkeypatch.setattr(
            ws_module.ticket_store,
            "redeem",
            MagicMock(side_effect=RuntimeError("store unavailable")),
        )

        from app.routes.websocket import websocket_endpoint, manager
        manager.active_connections.clear()

        await websocket_endpoint(ws)

        ws.accept.assert_not_called()
        ws.close.assert_called_once()
        assert manager.active_connections == {}


# ── 3. Valid ticket → connection registered through manager.connect() ───────

class TestValidTicket:
    async def test_valid_ticket_calls_manager_connect(self, monkeypatch):
        from fastapi import WebSocketDisconnect
        from app.services.ws_tickets import ticket_store

        ticket = ticket_store.issue("user-123")
        ws = _make_websocket(query_ticket=ticket)
        ws.receive_text = AsyncMock(
            side_effect=[json.dumps({"type": "ping"}), WebSocketDisconnect()]
        )

        connect_calls = []

        async def _mock_connect(socket, uid):
            connect_calls.append(uid)
            socket._accepted = True

        from app.routes import websocket as ws_module
        monkeypatch.setattr(ws_module.manager, "connect", _mock_connect)

        from app.routes.websocket import websocket_endpoint
        await websocket_endpoint(ws)

        assert connect_calls == ["user-123"], \
            "manager.connect() must be called exactly once with the authenticated user_id"

    async def test_valid_ticket_accept_called_via_manager_not_directly(self):
        from fastapi import WebSocketDisconnect
        from app.services.ws_tickets import ticket_store

        ticket = ticket_store.issue("user-456")
        ws = _make_websocket(query_ticket=ticket)
        ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())

        from app.routes.websocket import websocket_endpoint, manager
        manager.active_connections.clear()

        await websocket_endpoint(ws)

        ws.accept.assert_called_once()

    async def test_disconnect_cleans_up_active_connections(self):
        from fastapi import WebSocketDisconnect
        from app.services.ws_tickets import ticket_store

        ticket = ticket_store.issue("user-cleanup")
        ws = _make_websocket(query_ticket=ticket)
        ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())

        from app.routes.websocket import websocket_endpoint, manager
        manager.active_connections.clear()

        await websocket_endpoint(ws)

        assert "user-cleanup" not in manager.active_connections


# ── 4. ping/pong still works ──────────────────────────────────────────────────

class TestPingPong:
    async def test_ping_receives_pong(self):
        from fastapi import WebSocketDisconnect
        from app.services.ws_tickets import ticket_store

        ticket = ticket_store.issue("user-ping")
        ws = _make_websocket(query_ticket=ticket)
        ws.receive_text = AsyncMock(
            side_effect=[json.dumps({"type": "ping"}), WebSocketDisconnect()]
        )

        from app.routes.websocket import websocket_endpoint, manager
        manager.active_connections.clear()

        await websocket_endpoint(ws)

        ws.send_json.assert_called_once_with({"type": "pong"})


# ── 5. send_personal_message still works ─────────────────────────────────────

class TestSendPersonalMessage:
    async def test_sends_to_connected_user(self):
        ws = MagicMock()
        ws.send_json = AsyncMock()

        from app.routes.websocket import ConnectionManager
        mgr = ConnectionManager()
        mgr.active_connections["u1"] = ws

        await mgr.send_personal_message({"type": "update", "data": "hello"}, "u1")

        ws.send_json.assert_called_once_with({"type": "update", "data": "hello"})

    async def test_noop_for_unconnected_user(self):
        from app.routes.websocket import ConnectionManager
        mgr = ConnectionManager()

        await mgr.send_personal_message({"type": "update"}, "nonexistent-user")

    async def test_disconnects_on_send_failure(self):
        ws = MagicMock()
        ws.send_json = AsyncMock(side_effect=RuntimeError("broken pipe"))

        from app.routes.websocket import ConnectionManager
        mgr = ConnectionManager()
        mgr.active_connections["u-fail"] = ws

        await mgr.send_personal_message({"type": "update"}, "u-fail")

        assert "u-fail" not in mgr.active_connections


# ── 6. broadcast still works ─────────────────────────────────────────────────

class TestBroadcast:
    async def test_broadcasts_to_all_connected_users(self):
        ws1, ws2 = MagicMock(), MagicMock()
        ws1.send_json = AsyncMock()
        ws2.send_json = AsyncMock()

        from app.routes.websocket import ConnectionManager
        mgr = ConnectionManager()
        mgr.active_connections = {"u1": ws1, "u2": ws2}

        await mgr.broadcast({"type": "system", "msg": "hello everyone"})

        ws1.send_json.assert_called_once_with({"type": "system", "msg": "hello everyone"})
        ws2.send_json.assert_called_once_with({"type": "system", "msg": "hello everyone"})

    async def test_broadcast_removes_dead_connections(self):
        ws_dead = MagicMock()
        ws_dead.send_json = AsyncMock(side_effect=RuntimeError("broken"))
        ws_alive = MagicMock()
        ws_alive.send_json = AsyncMock()

        from app.routes.websocket import ConnectionManager
        mgr = ConnectionManager()
        mgr.active_connections = {"dead": ws_dead, "alive": ws_alive}

        await mgr.broadcast({"type": "ping"})

        assert "dead" not in mgr.active_connections
        ws_alive.send_json.assert_called_once()


# ── 7. No double-accept risk ──────────────────────────────────────────────────

class TestNoDoubleAccept:
    async def test_manager_connect_is_sole_accept_path(self):
        ws = MagicMock()
        ws.accept = AsyncMock()

        from app.routes.websocket import ConnectionManager
        mgr = ConnectionManager()
        await mgr.connect(ws, "u-double")

        ws.accept.assert_called_once()
        assert mgr.active_connections["u-double"] is ws


# ── 8. Ticket store semantics ─────────────────────────────────────────────────

class TestTicketStore:
    def test_issue_returns_unique_unguessable_tickets(self):
        from app.services.ws_tickets import WebSocketTicketStore

        store = WebSocketTicketStore()
        t1 = store.issue("user-a")
        t2 = store.issue("user-a")
        assert t1 != t2
        assert len(t1) > 20

    def test_redeem_valid_ticket_returns_user_id(self):
        from app.services.ws_tickets import WebSocketTicketStore

        store = WebSocketTicketStore()
        ticket = store.issue("user-b")
        assert store.redeem(ticket) == "user-b"

    def test_redeem_is_single_use(self):
        from app.services.ws_tickets import WebSocketTicketStore

        store = WebSocketTicketStore()
        ticket = store.issue("user-c")
        assert store.redeem(ticket) == "user-c"
        assert store.redeem(ticket) is None

    def test_redeem_expired_ticket_returns_none(self):
        from app.services.ws_tickets import WebSocketTicketStore

        store = WebSocketTicketStore(ttl_seconds=0)
        ticket = store.issue("user-d")
        time.sleep(0.01)
        assert store.redeem(ticket) is None

    def test_redeem_unknown_ticket_returns_none(self):
        from app.services.ws_tickets import WebSocketTicketStore

        store = WebSocketTicketStore()
        assert store.redeem("never-issued") is None


# ── 9. Ticket-issuing REST endpoint ───────────────────────────────────────────

class TestTicketEndpoint:
    async def test_requires_authorization_header(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from app.routes.ws_ticket import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        resp = client.post("/ws/ticket")
        assert resp.status_code == 401

    async def test_issues_ticket_for_valid_bearer_token(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from app.routes.ws_ticket import router
        from app.services.ws_tickets import ticket_store

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        resp = client.post(
            "/ws/ticket", headers={"Authorization": "Bearer valid-jwt"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "ticket" in body and "expires_in" in body
        # The issued ticket must actually be redeemable for the right user.
        assert ticket_store.redeem(body["ticket"]) == "user-123"

    async def test_rejects_invalid_bearer_token(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from app.routes.ws_ticket import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        resp = client.post(
            "/ws/ticket", headers={"Authorization": "Bearer garbage"}
        )
        assert resp.status_code == 401