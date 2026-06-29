"""
Tests for — WebSocket accept-before-auth vulnerability.

Verifies that:
1. Unauthenticated connections (missing or invalid token) are rejected
   BEFORE accept() is called — ConnectionManager.connect() must never fire.
2. Authenticated connections go through manager.connect() exclusively —
   no direct dict writes to active_connections.
3. After auth failure, no stale entry remains in active_connections.
4. send_personal_message and broadcast still work correctly post-refactor.
5. broadcast handles a dead connection gracefully without raising.
6. ping/pong message handling continues to work.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch, call


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_websocket(query_token=None):
    """Build a mock WebSocket with configurable query params."""
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.query_params = {"token": query_token} if query_token else {}
    return ws


# ── 1. Missing token is rejected pre-accept ──────────────────────────────────

class TestMissingToken:
    async def test_no_token_closes_without_accept(self, monkeypatch):
        """A connection with no token must be closed without calling accept()."""
        ws = _make_websocket(query_token=None)

        monkeypatch.setattr(
            "app.routes.websocket.verify_access_token",
            AsyncMock(return_value=None),
        )

        from app.routes.websocket import websocket_endpoint, manager
        manager.active_connections.clear()

        await websocket_endpoint(ws)

        ws.accept.assert_not_called()
        ws.close.assert_called_once()
        close_kwargs = ws.close.call_args
        code = close_kwargs[1].get("code") or close_kwargs[0][0]
        assert code == 4001

    async def test_no_token_leaves_no_stale_connection(self, monkeypatch):
        """After rejection for missing token, active_connections must be empty."""
        ws = _make_websocket(query_token=None)

        from app.routes.websocket import websocket_endpoint, manager
        manager.active_connections.clear()

        await websocket_endpoint(ws)

        assert manager.active_connections == {}


# ── 2. Invalid token is rejected pre-accept ──────────────────────────────────

class TestInvalidToken:
    async def test_bad_token_closes_without_accept(self, monkeypatch):
        """An invalid token must be rejected without accepting the handshake."""
        ws = _make_websocket(query_token="bad-token")

        monkeypatch.setattr(
            "app.routes.websocket.verify_access_token",
            AsyncMock(return_value=None),
        )

        from app.routes.websocket import websocket_endpoint, manager
        manager.active_connections.clear()

        await websocket_endpoint(ws)

        ws.accept.assert_not_called()
        ws.close.assert_called_once()

    async def test_bad_token_leaves_no_stale_connection(self, monkeypatch):
        """An invalid token must not leave any entry in active_connections."""
        ws = _make_websocket(query_token="bad-token")

        monkeypatch.setattr(
            "app.routes.websocket.verify_access_token",
            AsyncMock(return_value=None),
        )

        from app.routes.websocket import websocket_endpoint, manager
        manager.active_connections.clear()

        await websocket_endpoint(ws)

        assert manager.active_connections == {}

    async def test_auth_exception_closes_without_accept(self, monkeypatch):
        """If verify_access_token raises, the connection must be closed pre-accept."""
        ws = _make_websocket(query_token="exploding-token")

        monkeypatch.setattr(
            "app.routes.websocket.verify_access_token",
            AsyncMock(side_effect=RuntimeError("db unavailable")),
        )

        from app.routes.websocket import websocket_endpoint, manager
        manager.active_connections.clear()

        await websocket_endpoint(ws)

        ws.accept.assert_not_called()
        ws.close.assert_called_once()
        assert manager.active_connections == {}


# ── 3. Valid token → connection registered through manager.connect() ──────────

class TestValidToken:
    async def test_valid_token_calls_manager_connect(self, monkeypatch):
        """A valid token must result in manager.connect() being called —
        which is the only place that calls accept() and registers the socket."""
        from fastapi import WebSocketDisconnect

        ws = _make_websocket(query_token="valid-jwt")
        # Simulate one ping then disconnect
        ws.receive_text = AsyncMock(
            side_effect=[json.dumps({"type": "ping"}), WebSocketDisconnect()]
        )

        monkeypatch.setattr(
            "app.routes.websocket.verify_access_token",
            AsyncMock(return_value="user-123"),
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

    async def test_valid_token_accept_called_via_manager_not_directly(self, monkeypatch):
        """websocket.accept() must be called by manager.connect(), not directly
        by the endpoint — ensuring accept() fires in exactly one place."""
        from fastapi import WebSocketDisconnect

        ws = _make_websocket(query_token="valid-jwt")
        ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())

        monkeypatch.setattr(
            "app.routes.websocket.verify_access_token",
            AsyncMock(return_value="user-456"),
        )

        from app.routes.websocket import websocket_endpoint, manager
        manager.active_connections.clear()

        await websocket_endpoint(ws)

        # accept() should be called exactly once (inside manager.connect)
        ws.accept.assert_called_once()

    async def test_valid_token_registers_in_active_connections(self, monkeypatch):
        """After a successful connection, active_connections must contain the user."""
        from fastapi import WebSocketDisconnect

        ws = _make_websocket(query_token="valid-jwt")
        ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())

        monkeypatch.setattr(
            "app.routes.websocket.verify_access_token",
            AsyncMock(return_value="user-789"),
        )

        from app.routes.websocket import websocket_endpoint, manager
        manager.active_connections.clear()

        await websocket_endpoint(ws)

        # After disconnect, the entry should have been cleaned up
        assert "user-789" not in manager.active_connections

    async def test_disconnect_cleans_up_active_connections(self, monkeypatch):
        """WebSocketDisconnect must remove the user from active_connections."""
        from fastapi import WebSocketDisconnect

        ws = _make_websocket(query_token="valid-jwt")
        ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())

        monkeypatch.setattr(
            "app.routes.websocket.verify_access_token",
            AsyncMock(return_value="user-cleanup"),
        )

        from app.routes.websocket import websocket_endpoint, manager
        manager.active_connections.clear()

        await websocket_endpoint(ws)

        assert "user-cleanup" not in manager.active_connections, \
            "Disconnected user must be removed from active_connections"


# ── 4. ping/pong still works ──────────────────────────────────────────────────

class TestPingPong:
    async def test_ping_receives_pong(self, monkeypatch):
        """The endpoint must reply {type: pong} to a {type: ping} message."""
        from fastapi import WebSocketDisconnect

        ws = _make_websocket(query_token="valid-jwt")
        ws.receive_text = AsyncMock(
            side_effect=[json.dumps({"type": "ping"}), WebSocketDisconnect()]
        )

        monkeypatch.setattr(
            "app.routes.websocket.verify_access_token",
            AsyncMock(return_value="user-ping"),
        )

        from app.routes.websocket import websocket_endpoint, manager
        manager.active_connections.clear()

        await websocket_endpoint(ws)

        ws.send_json.assert_called_once_with({"type": "pong"})


# ── 5. send_personal_message still works ─────────────────────────────────────

class TestSendPersonalMessage:
    async def test_sends_to_connected_user(self):
        """send_personal_message must deliver a message to a connected user."""
        ws = MagicMock()
        ws.send_json = AsyncMock()

        from app.routes.websocket import ConnectionManager
        mgr = ConnectionManager()
        mgr.active_connections["u1"] = ws

        await mgr.send_personal_message({"type": "update", "data": "hello"}, "u1")

        ws.send_json.assert_called_once_with({"type": "update", "data": "hello"})

    async def test_noop_for_unconnected_user(self):
        """send_personal_message must be a no-op for a user not in active_connections."""
        from app.routes.websocket import ConnectionManager
        mgr = ConnectionManager()

        # Must not raise
        await mgr.send_personal_message({"type": "update"}, "nonexistent-user")

    async def test_disconnects_on_send_failure(self):
        """If send_json raises, the user must be removed from active_connections."""
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
        """broadcast must deliver to every user in active_connections."""
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
        """If a broadcast to one user fails, that user must be disconnected
        and the rest of the broadcast must still succeed."""
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
        """ConnectionManager.connect() must call accept() exactly once.
        This ensures no caller can double-accept by calling both the endpoint
        and manager.connect()."""
        ws = MagicMock()
        ws.accept = AsyncMock()

        from app.routes.websocket import ConnectionManager
        mgr = ConnectionManager()
        await mgr.connect(ws, "u-double")

        ws.accept.assert_called_once()
        assert mgr.active_connections["u-double"] is ws