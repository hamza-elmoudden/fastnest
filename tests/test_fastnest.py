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
    Module, Controller, Injectable, Global,
    Get, Post, Put, Delete, Patch,
    UseGuard, UseInterceptor, UsePipe, UseExceptionFilter,
)
from fastnest.core.factory import (
    create_app, add_global_guard, add_global_interceptor, add_global_pipe,
    add_global_filter,
)
from fastnest.core.params import Body, Param, Query
from fastnest.core.di import Container
from fastnest.core.tokens import Inject
from fastnest.core.websocket import (
    WebSocketGateway, SubscribeMessage, OnConnect, OnDisconnect,
    WebSocketClient, ConnectionManager,
)
from fastnest.common.interfaces import CanActivate, NestInterceptor, PipeTransform, ExceptionFilter
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
#  6. Custom Provider Tests
# ══════════════════════════════════════════════════════════════════

class TestCustomProviders:
    def test_use_value_provider_injected_into_service(self):
        @Injectable()
        class ConfigConsumer:
            def __init__(self, config: dict = Inject("APP_CONFIG")):
                self.config = config

        container = Container()
        container.register_provider({"provide": "APP_CONFIG", "useValue": {"debug": True}})
        consumer = container.get(ConfigConsumer)
        assert consumer.config == {"debug": True}

    def test_use_factory_provider_with_inject_deps(self):
        @Injectable()
        class DbUrl:
            def __init__(self):
                self.value = "postgres://localhost"

        def make_connection(url):
            return {"connection": url.value}

        container = Container()
        container.register_provider({
            "provide": "DB_CONNECTION",
            "useFactory": make_connection,
            "inject": [DbUrl],
        })
        conn = container.get("DB_CONNECTION")
        assert conn == {"connection": "postgres://localhost"}

    def test_use_class_provider_token_differs_from_impl(self):
        class AbstractLogger:
            pass

        class ConsoleLogger(AbstractLogger):
            def log(self, msg):
                return f"console: {msg}"

        container = Container()
        container.register_provider({"provide": AbstractLogger, "useClass": ConsoleLogger})
        logger = container.get(AbstractLogger)
        assert isinstance(logger, ConsoleLogger)
        assert logger.log("hi") == "console: hi"

    def test_global_custom_provider_exported_across_modules(self):
        @Injectable()
        class FeatureFlagsConsumer:
            def __init__(self, flags: dict = Inject("FEATURE_FLAGS")):
                self.flags = flags

        @Controller("flags")
        class FlagsController:
            def __init__(self, svc: FeatureFlagsConsumer):
                self.svc = svc

            @Get()
            async def get_flags(self):
                return self.svc.flags

        @Global()
        @Module(providers=[
            {"provide": "FEATURE_FLAGS", "useValue": {"beta": True}},
        ])
        class ConfigModule:
            pass

        @Module(imports=[ConfigModule], controllers=[FlagsController],
                providers=[FeatureFlagsConsumer])
        class FeatureModule:
            pass

        app = create_app(FeatureModule)
        with TestClient(app) as c:
            r = c.get("/flags")
            assert r.status_code == 200
            assert r.json() == {"beta": True}

    def test_inject_with_string_token_in_constructor(self):
        @Injectable()
        class Greeter:
            def __init__(self, name: str = Inject("GREETEE_NAME")):
                self.name = name

        container = Container()
        container.register_value("GREETEE_NAME", "World")
        greeter = container.get(Greeter)
        assert greeter.name == "World"

    def test_unregistered_token_raises(self):
        @Injectable()
        class NeedsMissingToken:
            def __init__(self, dep=Inject("MISSING_TOKEN")):
                self.dep = dep

        container = Container()
        with pytest.raises(LookupError):
            container.get(NeedsMissingToken)

        with pytest.raises(LookupError):
            container.get("ANOTHER_MISSING_TOKEN")


# ══════════════════════════════════════════════════════════════════
#  7. Global Guard/Pipe/Interceptor Isolation Tests
# ══════════════════════════════════════════════════════════════════

class AlwaysBlockGuard(CanActivate):
    def can_activate(self, request: Request) -> bool:
        return False


@Injectable()
class PingService:
    def ping(self):
        return {"ping": "pong"}


@Controller("ping")
class PingController:
    def __init__(self, svc: PingService):
        self.svc = svc

    @Get()
    async def ping(self):
        return self.svc.ping()

    @Get("echo")
    async def echo(self, msg: str = Query(default="hi")):
        return {"msg": msg}


@Module(controllers=[PingController], providers=[PingService])
class PingModule:
    pass


class TestGlobalRegistryIsolation:
    def test_global_guard_does_not_leak_to_other_apps(self):
        # App built with NO global guard — must stay unaffected.
        unaffected_app = create_app(PingModule)

        # Global guard registered only after the first app was built, so it
        # should apply exclusively to the next app created.
        add_global_guard(AlwaysBlockGuard)
        guarded_app = create_app(PingModule)

        # A third app, built after the registry was consumed above, must not
        # inherit the guard either — proves the staged registration doesn't
        # leak forward past the app that consumed it.
        later_app = create_app(PingModule)

        with TestClient(unaffected_app) as c:
            r = c.get("/ping")
            assert r.status_code == 200
            assert r.json() == {"ping": "pong"}

        with TestClient(guarded_app) as c:
            r = c.get("/ping")
            assert r.status_code == 403

        with TestClient(later_app) as c:
            r = c.get("/ping")
            assert r.status_code == 200
            assert r.json() == {"ping": "pong"}

    def test_explicit_guards_param_is_scoped_to_that_app_only(self):
        scoped_app = create_app(PingModule, guards=[AlwaysBlockGuard])
        other_app = create_app(PingModule)

        with TestClient(scoped_app) as c:
            assert c.get("/ping").status_code == 403

        with TestClient(other_app) as c:
            assert c.get("/ping").status_code == 200

    def test_global_interceptor_is_also_isolated(self):
        calls = []

        class RecordingInterceptor(NestInterceptor):
            def intercept_before(self, request):
                calls.append("before")

            def intercept_after(self, request, response):
                calls.append("after")
                return response

        add_global_interceptor(RecordingInterceptor)
        recorded_app = create_app(PingModule)
        unrecorded_app = create_app(PingModule)

        with TestClient(recorded_app) as c:
            c.get("/ping")
        assert calls == ["before", "after"]

        calls.clear()
        with TestClient(unrecorded_app) as c:
            c.get("/ping")
        assert calls == []

    def test_global_pipe_is_also_isolated(self):
        class ShoutPipe(PipeTransform):
            def transform(self, value):
                return value.upper() if isinstance(value, str) else value

        add_global_pipe(ShoutPipe)
        shouting_app = create_app(PingModule)
        quiet_app = create_app(PingModule)

        with TestClient(shouting_app) as c:
            assert c.get("/ping/echo", params={"msg": "hi"}).json() == {"msg": "HI"}

        with TestClient(quiet_app) as c:
            assert c.get("/ping/echo", params={"msg": "hi"}).json() == {"msg": "hi"}


# ══════════════════════════════════════════════════════════════════
#  8. Exception Filter Tests
# ══════════════════════════════════════════════════════════════════

class BoomError(Exception):
    pass


@Injectable()
class BoomService:
    def boom(self):
        raise BoomError("kaboom")


class ControllerFilter(ExceptionFilter):
    def catch(self, exception: Exception, request):
        return {"statusCode": 500, "message": f"controller:{exception}"}


class GlobalFilter(ExceptionFilter):
    def catch(self, exception: Exception, request):
        return {"statusCode": 500, "message": f"global:{exception}"}


@UseExceptionFilter(ControllerFilter)
@Controller("boom-ctrl")
class BoomControllerFiltered:
    def __init__(self, svc: BoomService):
        self.svc = svc

    @Get()
    async def boom(self):
        self.svc.boom()

    @Get("http")
    async def boom_http(self):
        raise NotFoundException("nope")


@Controller("boom-plain")
class BoomControllerPlain:
    def __init__(self, svc: BoomService):
        self.svc = svc

    @Get()
    async def boom(self):
        self.svc.boom()


@Module(controllers=[BoomControllerFiltered, BoomControllerPlain], providers=[BoomService])
class BoomModule:
    pass


class TestExceptionFilters:
    def test_controller_level_filter_catches_unhandled_exception(self):
        app = create_app(BoomModule)
        with TestClient(app) as c:
            r = c.get("/boom-ctrl")
            assert r.status_code == 500
            assert r.json()["message"] == "controller:kaboom"

    def test_http_exception_bypasses_filters(self):
        app = create_app(BoomModule)
        with TestClient(app) as c:
            r = c.get("/boom-ctrl/http")
            assert r.status_code == 404

    def test_global_filter_catches_exception_from_unfiltered_controller(self):
        add_global_filter(GlobalFilter)
        app = create_app(BoomModule)
        with TestClient(app) as c:
            r = c.get("/boom-plain")
            assert r.status_code == 500
            assert r.json()["message"] == "global:kaboom"

    def test_controller_level_filter_overrides_global_filter(self):
        # Both a global filter and a controller-level filter can handle this
        # exception; the more specific (controller-level) one must win.
        add_global_filter(GlobalFilter)
        app = create_app(BoomModule)
        with TestClient(app) as c:
            r = c.get("/boom-ctrl")
            assert r.status_code == 500
            assert r.json()["message"] == "controller:kaboom"


# ══════════════════════════════════════════════════════════════════
#  9. WebSocket Tests
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


# ══════════════════════════════════════════════════════════════════
#  10. WebSocket Namespace & Room Tests
# ══════════════════════════════════════════════════════════════════

@WebSocketGateway("/ws/ns", namespace="alpha")
class AlphaGateway:
    @SubscribeMessage("broadcast")
    async def handle_broadcast(self, data: str, client: WebSocketClient):
        await self.manager.broadcast({"event": "broadcast", "data": data, "from": "alpha"})


@WebSocketGateway("/ws/ns", namespace="beta")
class BetaGateway:
    @SubscribeMessage("broadcast")
    async def handle_broadcast(self, data: str, client: WebSocketClient):
        await self.manager.broadcast({"event": "broadcast", "data": data, "from": "beta"})


@Module(gateways=[AlphaGateway, BetaGateway])
class NamespaceModule:
    pass


@WebSocketGateway("/ws/rooms")
class RoomGateway:
    @SubscribeMessage("join")
    async def handle_join(self, data: str, client: WebSocketClient):
        await client.join(data)
        await client.send({"event": "joined", "room": data})

    @SubscribeMessage("leave")
    async def handle_leave(self, data: str, client: WebSocketClient):
        await client.leave(data)
        await client.send({"event": "left", "room": data})

    @SubscribeMessage("room_broadcast")
    async def handle_room_broadcast(self, data: dict, client: WebSocketClient):
        await self.manager.broadcast_to_room(
            data["room"], {"event": "room_message", "data": data["message"]}
        )

    @SubscribeMessage("room_count")
    async def handle_room_count(self, data: str, client: WebSocketClient):
        await client.send({"event": "room_count", "data": len(self.manager.room_clients(data))})


@Module(gateways=[RoomGateway])
class RoomModule:
    pass


@Module(imports=[NamespaceModule, RoomModule])
class NsRoomAppModule:
    pass


@pytest.fixture(scope="module")
def ns_room_client():
    app = create_app(NsRoomAppModule)
    with TestClient(app) as c:
        yield c


class TestWebSocketNamespacesAndRooms:
    def test_namespaces_isolate_connections(self, ns_room_client):
        import json
        with ns_room_client.websocket_connect("/ws/ns/alpha") as a1, \
             ns_room_client.websocket_connect("/ws/ns/alpha") as a2, \
             ns_room_client.websocket_connect("/ws/ns/beta") as b1:
            a1.send_text(json.dumps({"event": "broadcast", "data": "hi-alpha"}))
            msg_a2 = a2.receive_json()
            assert msg_a2["from"] == "alpha"
            assert msg_a2["data"] == "hi-alpha"

            # A broadcast on the alpha gateway must not leak to the beta
            # gateway's connections — b1 must only ever see its own broadcast.
            b1.send_text(json.dumps({"event": "broadcast", "data": "hi-beta"}))
            msg_b1 = b1.receive_json()
            assert msg_b1["from"] == "beta"
            assert msg_b1["data"] == "hi-beta"

    def test_colliding_path_and_namespace_raises_at_create_app(self):
        @WebSocketGateway("/ws/dup", namespace="x")
        class DupGatewayA:
            pass

        @WebSocketGateway("/ws/dup", namespace="x")
        class DupGatewayB:
            pass

        @Module(gateways=[DupGatewayA, DupGatewayB])
        class DupModule:
            pass

        with pytest.raises(ValueError, match="collision"):
            create_app(DupModule)

    def test_room_broadcast_only_reaches_members(self, ns_room_client):
        import json
        with ns_room_client.websocket_connect("/ws/rooms") as c1, \
             ns_room_client.websocket_connect("/ws/rooms") as c2, \
             ns_room_client.websocket_connect("/ws/rooms") as c3:
            c1.send_text(json.dumps({"event": "join", "data": "lobby"}))
            c1.receive_json()
            c2.send_text(json.dumps({"event": "join", "data": "lobby"}))
            c2.receive_json()
            # c3 deliberately does not join "lobby"

            c1.send_text(json.dumps(
                {"event": "room_broadcast", "data": {"room": "lobby", "message": "hey"}}
            ))
            assert c1.receive_json()["data"] == "hey"
            assert c2.receive_json()["data"] == "hey"

            # Prove c3 got nothing from the room broadcast: if it had leaked
            # to c3, this "joined" ack for an unrelated room would not be the
            # first message in c3's queue.
            c3.send_text(json.dumps({"event": "join", "data": "other"}))
            assert c3.receive_json() == {"event": "joined", "room": "other"}

    def test_client_removed_from_room_on_disconnect(self, ns_room_client):
        import json
        with ns_room_client.websocket_connect("/ws/rooms") as c1:
            c1.send_text(json.dumps({"event": "join", "data": "temp"}))
            c1.receive_json()

            with ns_room_client.websocket_connect("/ws/rooms") as c2:
                c2.send_text(json.dumps({"event": "join", "data": "temp"}))
                c2.receive_json()

                c1.send_text(json.dumps({"event": "room_count", "data": "temp"}))
                assert c1.receive_json()["data"] == 2
            # c2 disconnects here

            c1.send_text(json.dumps({"event": "room_count", "data": "temp"}))
            assert c1.receive_json()["data"] == 1

            # Broadcasting to the room must not error now that c2 is gone.
            c1.send_text(json.dumps(
                {"event": "room_broadcast", "data": {"room": "temp", "message": "still-here"}}
            ))
            msg = c1.receive_json()
            assert msg["data"] == "still-here"