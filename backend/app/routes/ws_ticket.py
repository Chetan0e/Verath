"""
REST endpoint for minting short-lived WebSocket connection tickets.

This sits in front of the WebSocket handshake: a client that is already
authenticated over normal HTTP (Authorization: Bearer <access_token>)
calls this endpoint to get a one-time ticket, then opens
``wss://host/ws/updates?ticket=<ticket>``. The long-lived access token
never appears in a URL or a WebSocket upgrade log line.

NOTE: This reuses `verify_access_token` from app.services.auth — the
same function the WebSocket endpoint used previously — so no new trust
boundary is introduced. If the project already has a shared
`get_current_user` FastAPI dependency used by other REST routes,
swap the body of `_get_current_user_id` to call that instead, to avoid
duplicating bearer-parsing logic.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.services.auth import verify_access_token
from app.services.ws_tickets import ticket_store

router = APIRouter()


async def _get_current_user_id(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    scheme, _, token = auth_header.partition(" ")

    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
        )

    try:
        user_id = await verify_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        )

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return user_id


@router.post("/ws/ticket")
async def issue_websocket_ticket(user_id: str = Depends(_get_current_user_id)):
    """Issue a single-use, short-lived ticket for opening a WebSocket
    connection at /ws/updates?ticket=<ticket>."""
    ticket = ticket_store.issue(user_id)
    return {"ticket": ticket, "expires_in": ticket_store.ttl_seconds}