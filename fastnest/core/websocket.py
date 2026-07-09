# fastnest/core/websocket.py
"""
WebSocket Gateway support for FastNest.

Usage:
    @WebSocketGateway(path="/chat")
    class ChatGateway:

        @SubscribeMessage("message")
        async def handle_message(self, data: str, client: WebSocketClient):
            await client.send(f"Echo: {data}")

        @OnConnect()
        async def on_connect(self, client: WebSocketClient):
            print(f"Client connected: {client.id}")

        @OnDisconnect()
        async def on_disconnect(self, client: WebSocketClient):
            print(f"Client disconnected: {client.id}")
"""

from __future__ import annotations

import asyncio
import inspect
import json
import uuid
from typing import Any, Callable, Dict, List, Optional, Set, TYPE_CHECKING

from fastapi import WebSocket, WebSocketDisconnect
from fastnest.core.metadata import get_meta, set_meta


# ── WebSocketClient — wraps a single connection ────────────────────────────
class WebSocketClient:
    """Represents a single connected WebSocket client."""

    def __init__(self, ws: WebSocket, manager: Optional["ConnectionManager"] = None):
        self._ws      = ws
        self.id       = str(uuid.uuid4())
        self.data: Dict[str, Any] = {}   # arbitrary metadata per client
        self._manager = manager

    async def send(self, message: Any) -> None:
        """Send a message — dict/list → JSON, anything else → text."""
        if isinstance(message, (dict, list)):
            await self._ws.send_text(json.dumps(message))
        else:
            await self._ws.send_text(str(message))

    async def send_json(self, data: Any) -> None:
        await self._ws.send_json(data)

    async def send_bytes(self, data: bytes) -> None:
        await self._ws.send_bytes(data)

    async def close(self, code: int = 1000) -> None:
        await self._ws.close(code)

    async def join(self, room: str) -> None:
        """Join a room on the owning ConnectionManager."""
        if self._manager is None:
            raise RuntimeError(f"WebSocketClient {self.id} has no ConnectionManager attached")
        self._manager.join_room(self, room)

    async def leave(self, room: str) -> None:
        """Leave a room on the owning ConnectionManager."""
        if self._manager is None:
            raise RuntimeError(f"WebSocketClient {self.id} has no ConnectionManager attached")
        self._manager.leave_room(self, room)

    @property
    def raw(self) -> WebSocket:
        return self._ws


# ── ConnectionManager — manages all connected clients ──────────────────────
class ConnectionManager:
    """Global connection manager — one instance per Gateway."""

    def __init__(self):
        self._clients: Dict[str, WebSocketClient] = {}
        self._rooms: Dict[str, Set[str]] = {}

    def add(self, client: WebSocketClient) -> None:
        self._clients[client.id] = client

    def remove(self, client: WebSocketClient) -> None:
        self._clients.pop(client.id, None)
        for room in list(self._rooms.keys()):
            self._rooms[room].discard(client.id)
            if not self._rooms[room]:
                del self._rooms[room]

    @property
    def clients(self) -> List[WebSocketClient]:
        return list(self._clients.values())

    @property
    def count(self) -> int:
        return len(self._clients)

    async def broadcast(self, message: Any, exclude: Optional[str] = None) -> None:
        """Send a message to all connected clients."""
        for client in self.clients:
            if exclude and client.id == exclude:
                continue
            try:
                await client.send(message)
            except Exception:
                pass

    async def send_to(self, client_id: str, message: Any) -> bool:
        """Send to a specific client by ID. Returns True if found."""
        client = self._clients.get(client_id)
        if client:
            await client.send(message)
            return True
        return False

    def join_room(self, client: WebSocketClient, room: str) -> None:
        """Add a client to a room."""
        self._rooms.setdefault(room, set()).add(client.id)

    def leave_room(self, client: WebSocketClient, room: str) -> None:
        """Remove a client from a room."""
        members = self._rooms.get(room)
        if not members:
            return
        members.discard(client.id)
        if not members:
            del self._rooms[room]

    def room_clients(self, room: str) -> List[WebSocketClient]:
        """All currently-connected clients in a room."""
        return [
            self._clients[cid] for cid in self._rooms.get(room, ())
            if cid in self._clients
        ]

    async def broadcast_to_room(self, room: str, message: Any, exclude: Optional[str] = None) -> None:
        """Send a message to every client in a room."""
        for client in self.room_clients(room):
            if exclude and client.id == exclude:
                continue
            try:
                await client.send(message)
            except Exception:
                pass


# ── Decorators ──────────────────────────────────────────────────────────────

def WebSocketGateway(path: str = "/ws", *, namespace: str = ""):
    """
    Marks a class as a WebSocket gateway.

    @WebSocketGateway("/chat")
    class ChatGateway: ...
    """
    def decorator(cls):
        set_meta(cls, "is_ws_gateway", True)
        set_meta(cls, "ws_path",       path.rstrip("/") or "/ws")
        set_meta(cls, "ws_namespace",  namespace.strip("/"))
        return cls
    return decorator


def get_gateway_route(gateway_cls) -> tuple[str, str, str]:
    """
    Resolves a gateway class's routing info.

    Returns (path, namespace, mount_path). `(path, namespace)` is the identity
    used to detect route collisions between gateways; `mount_path` is the
    actual ASGI websocket route — namespaced gateways get isolated from
    unnamespaced (or differently-namespaced) ones sharing the same `path`.
    """
    path      = get_meta(gateway_cls, "ws_path", "/ws")
    namespace = get_meta(gateway_cls, "ws_namespace", "")
    mount_path = f"{path}/{namespace}" if namespace else path
    return path, namespace, mount_path


def SubscribeMessage(event: str):
    """
    Marks a method as a handler for a specific WebSocket event.

    @SubscribeMessage("message")
    async def handle_message(self, data: str, client: WebSocketClient): ...
    """
    def decorator(fn):
        fn._ws_event    = event
        fn._ws_handler  = True
        fn._ws_type     = "message"
        return fn
    return decorator


def OnConnect():
    """Called when a client connects."""
    def decorator(fn):
        fn._ws_event    = "__connect__"
        fn._ws_handler  = True
        fn._ws_type     = "connect"
        return fn
    return decorator


def OnDisconnect():
    """Called when a client disconnects."""
    def decorator(fn):
        fn._ws_event    = "__disconnect__"
        fn._ws_handler  = True
        fn._ws_type     = "disconnect"
        return fn
    return decorator


# ── Message protocol ────────────────────────────────────────────────────────
# Clients send JSON: {"event": "message", "data": "hello"}
# Or plain text treated as event="message"

def _parse_message(raw: str) -> tuple[str, Any]:
    """Returns (event, data)."""
    try:
        msg = json.loads(raw)
        if isinstance(msg, dict) and "event" in msg:
            return msg["event"], msg.get("data")
        return "message", msg
    except (json.JSONDecodeError, TypeError):
        return "message", raw


# ── Gateway registration ────────────────────────────────────────────────────

def register_gateway(gateway_instance, gateway_cls, app, logger=None):
    """
    Registers a WebSocket gateway on the FastAPI app.
    Called from factory._register_module().
    """
    path, namespace, mount_path = get_gateway_route(gateway_cls)
    manager   = ConnectionManager()

    # Collect handlers
    handlers: Dict[str, Callable] = {}           # event -> bound method
    connect_handler    = None
    disconnect_handler = None

    for name, method in inspect.getmembers(gateway_instance, predicate=inspect.ismethod):
        if not getattr(method, "_ws_handler", False):
            continue
        ws_type = getattr(method, "_ws_type", "message")
        event   = getattr(method, "_ws_event", "message")

        if ws_type == "connect":
            connect_handler = method
        elif ws_type == "disconnect":
            disconnect_handler = method
        else:
            handlers[event] = method

    if logger:
        ns_suffix = f" (namespace={namespace!r})" if namespace else ""
        logger.debug(f"[FastNest] Gateway  WS  {mount_path}{ns_suffix}  "
                     f"({len(handlers)} event(s))")

    # Attach manager to gateway instance so handlers can use it
    gateway_instance.manager = manager

    @app.websocket(mount_path)
    async def websocket_endpoint(ws: WebSocket):
        await ws.accept()
        client = WebSocketClient(ws, manager=manager)
        manager.add(client)

        # on_connect
        if connect_handler:
            try:
                if inspect.iscoroutinefunction(connect_handler):
                    await connect_handler(client)
                else:
                    connect_handler(client)
            except Exception as e:
                if logger:
                    logger.error(f"[FastNest] on_connect error: {e}")

        try:
            while True:
                raw = await ws.receive_text()
                event, data = _parse_message(raw)

                handler = handlers.get(event)  # no fallback — unknown events are ignored
                if handler:
                    try:
                        if inspect.iscoroutinefunction(handler):
                            await handler(data, client)
                        else:
                            handler(data, client)
                    except Exception as e:
                        if logger:
                            logger.error(f"[FastNest] handler '{event}' error: {e}")
                        try:
                            await client.send({"error": str(e)})
                        except Exception:
                            pass

        except WebSocketDisconnect:
            pass
        except Exception as e:
            if logger:
                logger.error(f"[FastNest] WebSocket error: {e}")
        finally:
            manager.remove(client)
            if disconnect_handler:
                try:
                    if inspect.iscoroutinefunction(disconnect_handler):
                        await disconnect_handler(client)
                    else:
                        disconnect_handler(client)
                except Exception as e:
                    if logger:
                        logger.error(f"[FastNest] on_disconnect error: {e}")