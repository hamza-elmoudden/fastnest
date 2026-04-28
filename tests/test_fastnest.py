"""
FastNest — Integration Tests
=============================
Run: pytest tests/test_fastnest.py -v

Requires: pip install httpx pytest pytest-asyncio
"""

import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from fastnest.core.decorators import (
    Module, Controller, Injectable,
    Get, Post, Put, Delete, Patch,
    UseGuard, UseInterceptor, UsePipe,
)
from fastnest.core.factory import create_app
from fastnest.core.params import Body, Param, Query
from fastnest.core.websocket import (
    WebSocketGateway, SubscribeMessage, OnConnect, OnDisconnect,
    WebSocketClient, ConnectionManager,
)
from fastnest.common.interfaces import CanActivate, NestInterceptor
from fastnest.common.pipes import ValidationPipe, ParseIntPipe
from fastnest.common.exceptions import (
    NotFoundException, ForbiddenException, UnauthorizedException,
)
from fastnest.common.decorators import Roles, createParamDecorator
from fastnest.common.guards.roles_guard import RolesGuard
from pydantic import BaseModel, field_validator
from fastapi import Request


# ══════════════════════════════════════════════════════════════════
#  Shared fixtures
# ══════════════════════════════════════════════════════════════════

class ItemDto(BaseModel):
    name:  str
    price: float

    @field_validator("price")
    @classmethod
    def price_positive(cls, v):
        if v <= 0:
            raise ValueError("price must be positive")
        return v


@Injectable()
class ItemsService:
    def __init__(self):
        self._items: list = []

    def find_all(self, q: str = None):
        if q:
            return [i for i in self._items if q.lower() in i["name"].lower()]
        return self._items

    def find_one(self, item_id: int):
        for i in self._items:
            if i["id"] == item_id:
                return i
        raise NotFoundException(f"Item #{item_id} not found")

    def create(self, dto: ItemDto):
        item = {"id": len(self._items) + 1, **dto.model_dump()}
        self._items.append(item)
        return item

    def update(self, item_id: int, dto: ItemDto):
        item = self.find_one(item_id)
        item.update(dto.model_dump())
        return item

    def remove(self, item_id: int):
        item = self.find_one(item_id)
        self._items.remove(item)
        return {"deleted": item_id}


class AuthGuard(CanActivate):
    def can_activate(self, request: Request) -> bool:
        token = request.headers.get("Authorization", "")
        if token != "Bearer valid-token":
            raise UnauthorizedException("Invalid token")
        request.state.user = {"id": 1, "roles": ["admin", "user"]}
        return True


CurrentUser = createParamDecorator(
    lambda data, request: getattr(request.state, "user", None)
)


class LogInterceptor(NestInterceptor):
    calls: list = []

    def intercept_before(self, request):
        LogInterceptor.calls.append(f"before:{request.url.path}")

    def intercept_after(self, request, response):
        LogInterceptor.calls.append(f"after:{request.url.path}")
        return response


@UseGuard(AuthGuard)
@UseInterceptor(LogInterceptor)
@Controller("items")
class ItemsController:
    def __init__(self, svc: ItemsService):
        self.svc = svc

    @Get()
    async def find_all(self, q: str = Query(default=None)):
        return self.svc.find_all(q)

    @Get("{item_id}")
    @UsePipe(ParseIntPipe)
    async def find_one(self, item_id=Param("item_id")):
        return self.svc.find_one(item_id)

    @Post()
    @UsePipe(ValidationPipe)
    async def create(self, body: ItemDto = Body()):
        return self.svc.create(body)

    @Put("{item_id}")
    @UsePipe(ValidationPipe)
    async def update(self, item_id=Param("item_id"), body: ItemDto = Body()):
        return self.svc.update(int(item_id), body)

    @Delete("{item_id}")
    async def remove(self, item_id=Param("item_id")):
        return self.svc.remove(int(item_id))

    @Get("me/profile")
    async def profile(self, user=CurrentUser()):
        return user


@Module(controllers=[ItemsController], providers=[ItemsService])
class ItemsModule:
    pass


@Module(imports=[ItemsModule])
class AppModule:
    pass


@pytest.fixture(scope="module")
def client():
    app = create_app(AppModule)
    with TestClient(app) as c:
        yield c


AUTH = {"Authorization": "Bearer valid-token"}


# ══════════════════════════════════════════════════════════════════
#  1. Guard Tests
# ══════════════════════════════════════════════════════════════════

class TestGuards:
    def test_blocked_without_token(self, client):
        r = client.get("/items")
        assert r.status_code == 401

    def test_blocked_with_wrong_token(self, client):
        r = client.get("/items", headers={"Authorization": "Bearer wrong"})
        assert r.status_code == 401

    def test_allowed_with_valid_token(self, client):
        r = client.get("/items", headers=AUTH)
        assert r.status_code == 200

    def test_custom_param_decorator(self, client):
        r = client.get("/items/me/profile", headers=AUTH)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == 1
        assert "admin" in data["roles"]


# ══════════════════════════════════════════════════════════════════
#  2. CRUD Tests
# ══════════════════════════════════════════════════════════════════

class TestCRUD:
    def test_create_item(self, client):
        r = client.post("/items", json={"name": "Book", "price": 9.99}, headers=AUTH)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Book"
        assert data["price"] == 9.99
        assert "id" in data

    def test_find_all(self, client):
        client.post("/items", json={"name": "Pen", "price": 1.5}, headers=AUTH)
        r = client.get("/items", headers=AUTH)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 1

    def test_find_one(self, client):
        r = client.post("/items", json={"name": "Cup", "price": 5.0}, headers=AUTH)
        item_id = r.json()["id"]
        r2 = client.get(f"/items/{item_id}", headers=AUTH)
        assert r2.status_code == 200
        assert r2.json()["name"] == "Cup"

    def test_find_one_not_found(self, client):
        r = client.get("/items/9999", headers=AUTH)
        assert r.status_code == 404

    def test_update_item(self, client):
        r = client.post("/items", json={"name": "Old", "price": 1.0}, headers=AUTH)
        item_id = r.json()["id"]
        r2 = client.put(f"/items/{item_id}",
                        json={"name": "New", "price": 2.0}, headers=AUTH)
        assert r2.status_code == 200
        assert r2.json()["name"] == "New"

    def test_delete_item(self, client):
        r = client.post("/items", json={"name": "Temp", "price": 0.5}, headers=AUTH)
        item_id = r.json()["id"]
        r2 = client.delete(f"/items/{item_id}", headers=AUTH)
        assert r2.status_code == 200
        assert r2.json()["deleted"] == item_id
        r3 = client.get(f"/items/{item_id}", headers=AUTH)
        assert r3.status_code == 404

    def test_query_filter(self, client):
        client.post("/items", json={"name": "Python Book", "price": 30.0}, headers=AUTH)
        client.post("/items", json={"name": "Java Book",   "price": 25.0}, headers=AUTH)
        r = client.get("/items?q=python", headers=AUTH)
        assert r.status_code == 200
        results = r.json()
        assert all("python" in i["name"].lower() for i in results)


# ══════════════════════════════════════════════════════════════════
#  3. Validation Tests
# ══════════════════════════════════════════════════════════════════

class TestValidation:
    def test_missing_field(self, client):
        r = client.post("/items", json={"name": "X"}, headers=AUTH)
        assert r.status_code == 422

    def test_wrong_type(self, client):
        r = client.post("/items", json={"name": "X", "price": "not-a-number"}, headers=AUTH)
        assert r.status_code == 422

    def test_custom_validator_negative_price(self, client):
        r = client.post("/items", json={"name": "X", "price": -5.0}, headers=AUTH)
        assert r.status_code == 422

    def test_parse_int_pipe(self, client):
        r = client.get("/items/abc", headers=AUTH)
        assert r.status_code == 400


# ══════════════════════════════════════════════════════════════════
#  4. Interceptor Tests
# ══════════════════════════════════════════════════════════════════

class TestInterceptor:
    def test_interceptor_called(self, client):
        LogInterceptor.calls.clear()
        client.get("/items", headers=AUTH)
        assert any("before:/items" in c for c in LogInterceptor.calls)
        assert any("after:/items"  in c for c in LogInterceptor.calls)

    def test_interceptor_order(self, client):
        LogInterceptor.calls.clear()
        client.get("/items", headers=AUTH)
        calls = LogInterceptor.calls
        before_idx = next(i for i, c in enumerate(calls) if "before" in c)
        after_idx  = next(i for i, c in enumerate(calls) if "after"  in c)
        assert before_idx < after_idx


# ══════════════════════════════════════════════════════════════════
#  5. Dependency Injection Tests
# ══════════════════════════════════════════════════════════════════

class TestDI:
    def test_service_singleton_per_module(self, client):
        """Same service instance shared across requests."""
        client.post("/items", json={"name": "A", "price": 1.0}, headers=AUTH)
        client.post("/items", json={"name": "B", "price": 2.0}, headers=AUTH)
        r = client.get("/items", headers=AUTH)
        # Items persist across requests → same service instance
        assert len(r.json()) >= 2

    def test_not_injectable_raises(self):
        class NotInjectable:
            pass

        from fastnest.core.di import Container
        container = Container()
        # Raises LookupError (or Exception in older versions) — both are errors
        with pytest.raises((LookupError, Exception)):
            container.get(NotInjectable)


# ══════════════════════════════════════════════════════════════════
#  6. WebSocket Tests
# ══════════════════════════════════════════════════════════════════

connected_clients: list = []
disconnected_clients: list = []
received_messages: list = []


@Injectable()
class ChatService:
    def broadcast_count(self, manager: ConnectionManager) -> int:
        return manager.count


@WebSocketGateway("/ws/chat")
class ChatGateway:
    def __init__(self, svc: ChatService):
        self.svc = svc

    @OnConnect()
    async def on_connect(self, client: WebSocketClient):
        connected_clients.append(client.id)
        await client.send({"event": "connected", "id": client.id})

    @OnDisconnect()
    async def on_disconnect(self, client: WebSocketClient):
        disconnected_clients.append(client.id)

    @SubscribeMessage("message")
    async def handle_message(self, data: str, client: WebSocketClient):
        received_messages.append(data)
        await client.send({"event": "echo", "data": data})

    @SubscribeMessage("count")
    async def handle_count(self, data, client: WebSocketClient):
        await client.send({"event": "count", "data": self.manager.count})

    @SubscribeMessage("broadcast")
    async def handle_broadcast(self, data: str, client: WebSocketClient):
        await self.manager.broadcast(
            {"event": "broadcast", "data": data},
            exclude=client.id,
        )


@Module(gateways=[ChatGateway], providers=[ChatService])
class ChatModule:
    pass


@Module(imports=[ItemsModule, ChatModule])
class FullAppModule:
    pass


@pytest.fixture(scope="module")
def ws_client():
    app = create_app(FullAppModule)
    with TestClient(app) as c:
        yield c


class TestWebSocket:
    def test_connect_and_receive_welcome(self, ws_client):
        with ws_client.websocket_connect("/ws/chat") as ws:
            msg = ws.receive_json()
            assert msg["event"] == "connected"
            assert "id" in msg

    def test_echo_message(self, ws_client):
        import json
        with ws_client.websocket_connect("/ws/chat") as ws:
            ws.receive_json()   # welcome
            ws.send_text(json.dumps({"event": "message", "data": "hello"}))
            echo = ws.receive_json()
            assert echo["event"] == "echo"
            assert echo["data"] == "hello"

    def test_plain_text_treated_as_message(self, ws_client):
        with ws_client.websocket_connect("/ws/chat") as ws:
            ws.receive_json()   # welcome
            ws.send_text("plain text")
            echo = ws.receive_json()
            assert echo["event"] == "echo"
            assert echo["data"] == "plain text"

    def test_on_connect_called(self, ws_client):
        before = len(connected_clients)
        with ws_client.websocket_connect("/ws/chat") as ws:
            ws.receive_json()
        assert len(connected_clients) == before + 1

    def test_on_disconnect_called(self, ws_client):
        before = len(disconnected_clients)
        with ws_client.websocket_connect("/ws/chat") as ws:
            ws.receive_json()
        assert len(disconnected_clients) == before + 1

    def test_connection_count(self, ws_client):
        import json
        with ws_client.websocket_connect("/ws/chat") as ws:
            ws.receive_json()   # welcome
            ws.send_text(json.dumps({"event": "count"}))
            resp = ws.receive_json()
            assert resp["event"] == "count"
            assert isinstance(resp["data"], int)
            assert resp["data"] >= 1

    def test_messages_received(self, ws_client):
        import json
        before = len(received_messages)
        with ws_client.websocket_connect("/ws/chat") as ws:
            ws.receive_json()
            ws.send_text(json.dumps({"event": "message", "data": "test_msg"}))
            ws.receive_json()
        assert len(received_messages) == before + 1
        assert received_messages[-1] == "test_msg"

    def test_unknown_event_no_crash(self, ws_client):
        """Unknown events should not crash the server."""
        import json
        with ws_client.websocket_connect("/ws/chat") as ws:
            ws.receive_json()
            ws.send_text(json.dumps({"event": "unknown_event", "data": "x"}))
            # No response expected — but no crash either
            # Connection should still be alive for another message
            ws.send_text(json.dumps({"event": "message", "data": "still alive"}))
            echo = ws.receive_json()
            assert echo["data"] == "still alive"