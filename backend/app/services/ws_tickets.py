"""
Short-lived, single-use ticket store for WebSocket authentication.

Rationale
---------
Putting a long-lived JWT in a WebSocket URL query parameter (``?token=``)
means that token ends up in access logs, reverse-proxy logs, browser
history, and any request-tracing/monitoring infrastructure sitting in
front of the app — for as long as those logs are retained.

A "ticket" fixes this by decoupling the *credential* from the
*connection parameter*:

1. The client, already authenticated via the normal REST auth flow
   (e.g. ``Authorization: Bearer <access_token>``), calls
   ``POST /ws/ticket`` to mint a ticket.
2. The ticket is a random, unguessable, single-use, short-TTL value —
   not a JWT, and not something that grants any access beyond opening
   one WebSocket connection within the next few seconds.
3. The client opens ``wss://host/ws/updates?ticket=<ticket>``.
4. The server redeems (looks up *and deletes*) the ticket. A leaked
   ticket in a log is worthless a few seconds later and can't be
   replayed even within that window.

Deployment note
----------------
This implementation stores tickets in an in-process dict, which is
sufficient for a single backend process. If you run multiple backend
instances behind a load balancer, replace the storage with something
shared (e.g. Redis with ``SET ticket user_id EX <ttl> NX`` for issue
and a ``GETDEL``/Lua script for atomic redeem) so a ticket issued by
one instance can be redeemed by another.
"""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from threading import Lock

TICKET_TTL_SECONDS = 10
TICKET_BYTES = 32  # 256 bits of entropy


@dataclass
class _TicketEntry:
    user_id: str
    expires_at: float


class WebSocketTicketStore:
    """Thread-safe, single-use, TTL-bound ticket store."""

    def __init__(self, ttl_seconds: int = TICKET_TTL_SECONDS):
        self._ttl = ttl_seconds
        self._tickets: dict[str, _TicketEntry] = {}
        self._lock = Lock()

    def issue(self, user_id: str) -> str:
        """Mint a new single-use ticket for user_id. Opportunistically
        prunes expired tickets so the store doesn't grow unbounded if
        some tickets are never redeemed (e.g. client never connects)."""
        self._prune_expired()
        ticket = secrets.token_urlsafe(TICKET_BYTES)
        with self._lock:
            self._tickets[ticket] = _TicketEntry(
                user_id=user_id, expires_at=time.time() + self._ttl
            )
        return ticket

    def redeem(self, ticket: str) -> str | None:
        """Validate and consume a ticket in one atomic step.

        Returns the associated user_id, or None if the ticket is
        missing, unknown, already used, or expired. Because the entry
        is popped under the lock regardless of expiry outcome, a
        ticket can never be redeemed twice — even if two requests race
        on the same ticket concurrently, only one can win the pop.
        """
        with self._lock:
            entry = self._tickets.pop(ticket, None)
        if entry is None:
            return None
        if entry.expires_at < time.time():
            return None
        return entry.user_id

    def _prune_expired(self) -> None:
        now = time.time()
        with self._lock:
            expired = [t for t, e in self._tickets.items() if e.expires_at < now]
            for t in expired:
                del self._tickets[t]

    @property
    def ttl_seconds(self) -> int:
        return self._ttl


# Module-level singleton used by the REST issuing endpoint and the
# WebSocket endpoint alike.
ticket_store = WebSocketTicketStore()