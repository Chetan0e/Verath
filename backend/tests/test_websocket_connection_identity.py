"""
Tests for ConnectionManager's per-connection identity tracking.

Verifies that a user can hold multiple simultaneous WebSocket connections
(e.g. during a quick reconnect) and that disconnecting one connection never
drops a different, still-active connection for the same user_id.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.routes.websocket import ConnectionManager

def make_socket():
    """Return a fresh mock WebSocket with an async send_json."""
    socket = MagicMock()
    socket.send_json = AsyncMock()
    return socket


@pytest.fixture
def manager():
    return ConnectionManager()


class TestConnectionIdentity:
    """Two overlapping connections for the same user must be tracked independently."""

    async def test_connect_tracks_multiple_sockets_for_same_user(self, manager):
        """Both sockets must be active after connecting twice for one user_id."""
        old_socket, new_socket = make_socket(), make_socket()

        await manager.connect(old_socket, "user-1")
        await manager.connect(new_socket, "user-1")

        assert manager.active_connections["user-1"] == {old_socket, new_socket}

    async def test_disconnecting_older_socket_keeps_newer_socket_active(self, manager):
        """Regression test for #229: closing the older connection must not
        remove the newer, still-active connection from routing."""
        old_socket, new_socket = make_socket(), make_socket()
        await manager.connect(old_socket, "user-1")
        await manager.connect(new_socket, "user-1")

        manager.disconnect("user-1", old_socket)

        assert old_socket not in manager.active_connections["user-1"]
        assert new_socket in manager.active_connections["user-1"]

    async def test_disconnecting_last_socket_removes_user_entry(self, manager):
        """Once no sockets remain for a user, the dict entry itself is cleaned up."""
        socket = make_socket()
        await manager.connect(socket, "user-1")

        manager.disconnect("user-1", socket)

        assert "user-1" not in manager.active_connections

    async def test_disconnect_is_noop_for_unknown_socket(self, manager):
        """Disconnecting a socket that was never registered must not raise
        or affect other active connections for that user."""
        active_socket, unknown_socket = make_socket(), make_socket()
        await manager.connect(active_socket, "user-1")

        manager.disconnect("user-1", unknown_socket)

        assert manager.active_connections["user-1"] == {active_socket}

    async def test_disconnect_is_noop_for_unknown_user(self, manager):
        """Disconnecting for a user_id with no active connections must not raise."""
        manager.disconnect("ghost-user", make_socket())


class TestMessageFanOut:
    """send_personal_message and broadcast must reach every connection a user holds."""

    async def test_send_personal_message_reaches_all_sockets_for_user(self, manager):
        """A message sent to a user_id must reach every socket that user holds."""
        first, second = make_socket(), make_socket()
        await manager.connect(first, "user-1")
        await manager.connect(second, "user-1")

        await manager.send_personal_message({"type": "update"}, "user-1")

        first.send_json.assert_awaited_once_with({"type": "update"})
        second.send_json.assert_awaited_once_with({"type": "update"})

    async def test_send_personal_message_drops_only_failing_socket(self, manager):
        """A send failure on one socket must not affect a sibling socket for
        the same user, and must remove only the socket that failed."""
        healthy, broken = make_socket(), make_socket()
        broken.send_json.side_effect = RuntimeError("connection reset")
        await manager.connect(healthy, "user-1")
        await manager.connect(broken, "user-1")

        await manager.send_personal_message({"type": "update"}, "user-1")

        assert manager.active_connections["user-1"] == {healthy}

    async def test_broadcast_reaches_every_connection_across_users(self, manager):
        """broadcast() must reach every socket for every user, not just one per user."""
        u1_socket, u2_first, u2_second = make_socket(), make_socket(), make_socket()
        await manager.connect(u1_socket, "user-1")
        await manager.connect(u2_first, "user-2")
        await manager.connect(u2_second, "user-2")

        await manager.broadcast({"type": "announcement"})

        u1_socket.send_json.assert_awaited_once_with({"type": "announcement"})
        u2_first.send_json.assert_awaited_once_with({"type": "announcement"})
        u2_second.send_json.assert_awaited_once_with({"type": "announcement"})
