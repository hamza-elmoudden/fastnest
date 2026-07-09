<div align="center">

# 🪺 FastNest

**A NestJS-inspired framework for Python, built on FastAPI.**

Bring the architecture you love from Node.js — Modules, Controllers, Guards, Pipes, Interceptors, and Dependency Injection — to the Python ecosystem.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square)](https://python.org)
[![FastAPI](https://img.shields.io/badge/built%20on-FastAPI-009688?style=flat-square)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-orange?style=flat-square)]()

</div>

---

## Why FastNest?

FastAPI is great — but as your project grows, you end up inventing your own structure. FastNest gives you that structure out of the box, inspired by the battle-tested patterns of NestJS:

| Feature | FastAPI alone | FastNest |
|---|---|---|
| Dependency Injection | Manual | `@Injectable()` + automatic |
| Modules | — | `@Module()` with imports/exports |
| Guards | Depends() | `@UseGuard()` on method or controller |
| Pipes | Depends() | `@UsePipe()` with transform chain |
| Interceptors | Middleware | `@UseInterceptor()` before/after |
| Lifecycle hooks | lifespan manually | `OnModuleInit`, `OnApplicationBootstrap` |

---

## Installation

```bash
pip install fastnest
```

Or for development:

```bash
pip install "fastnest[dev]"
```

---

## Quick Start

```python
from fastnest.core.decorators import Module, Controller, Injectable, Get, Post
from fastnest.core.factory import create_app
from fastnest.core.params import Body, Param
from fastnest.common.interfaces import CanActivate
from fastnest.common.pipes import ValidationPipe
from pydantic import BaseModel
from fastapi import Request


# ── DTO ──────────────────────────────────────────────────────────────────────
class CreateUserDto(BaseModel):
    name: str
    email: str


# ── Guard ─────────────────────────────────────────────────────────────────────
class AuthGuard(CanActivate):
    def can_activate(self, request: Request) -> bool:
        return request.headers.get("Authorization", "").startswith("Bearer ")


# ── Service ───────────────────────────────────────────────────────────────────
@Injectable()
class UsersService:
    def __init__(self):
        self._users = []

    def find_all(self):
        return self._users

    def create(self, dto: CreateUserDto):
        user = {"id": len(self._users) + 1, **dto.model_dump()}
        self._users.append(user)
        return user


# ── Controller ────────────────────────────────────────────────────────────────
@Controller("users")
class UsersController:
    def __init__(self, service: UsersService):
        self.service = service

    @Get()
    async def find_all(self, request: Request):
        return self.service.find_all()

    @Post()
    @UseGuard(AuthGuard)
    @UsePipe(ValidationPipe)
    async def create(self, body: CreateUserDto = Body()):
        return self.service.create(body)


# ── Module ────────────────────────────────────────────────────────────────────
@Module(controllers=[UsersController], providers=[UsersService])
class AppModule:
    pass


# ── Bootstrap ─────────────────────────────────────────────────────────────────
app = create_app(AppModule)
```

```bash
uvicorn main:app --reload
```

---

## Core Concepts

### Modules

Modules are the building blocks. Each feature lives in its own module.

```python
@Module(
    imports=[DatabaseModule],      # import providers from other modules
    controllers=[UsersController],
    providers=[UsersService],
    exports=[UsersService],        # share with other modules
)
class UsersModule:
    pass
```

### Dependency Injection

Mark a class with `@Injectable()` and FastNest injects it automatically based on type annotations.

```python
@Injectable()
class UsersService:
    def __init__(self, db: DatabaseService):  # ← injected automatically
        self.db = db
```

#### Custom providers

Beyond plain `@Injectable()` classes, a module's `providers` list also accepts NestJS-style custom
provider entries — bind a fixed value, a factory function, or an alternate implementation to a token:

```python
from fastnest import Module, Inject

@Module(
    providers=[
        {"provide": "APP_CONFIG", "useValue": {"debug": True}},
        {"provide": "DB_CONNECTION", "useFactory": lambda url: connect(url), "inject": [DbUrl]},
        {"provide": AbstractLogger, "useClass": ConsoleLogger},
    ],
    exports=["APP_CONFIG"],
)
class ConfigModule:
    pass
```

A `provide` token can be a class or a plain string. Use `Inject(token)` as a parameter default to pull
a token-based dependency into a constructor when a type annotation alone can't express it:

```python
@Injectable()
class UsersService:
    def __init__(self, config: dict = Inject("APP_CONFIG")):
        self.config = config
```

### Guards

```python
class AuthGuard(CanActivate):
    def can_activate(self, request: Request) -> bool:
        return bool(request.headers.get("Authorization"))

# Method-level
@Get()
@UseGuard(AuthGuard)
async def profile(self, request: Request): ...

# Controller-level (applies to all routes)
@UseGuard(AuthGuard)
@Controller("users")
class UsersController: ...

# Global (applies to the entire app)
from fastnest.core.factory import add_global_guard
add_global_guard(AuthGuard)
app = create_app(AppModule)

# Equivalently, scope it explicitly to one app via create_app():
app = create_app(AppModule, guards=[AuthGuard])
```

> **Scoping:** `add_global_guard()` (and `add_global_interceptor()` / `add_global_pipe()`) stage
> registrations for the *next* `create_app()` call only. Each `create_app()` call consumes and clears
> the staged guards/interceptors/pipes, so registrations never leak into apps built afterward —
> creating multiple independent apps in the same process (e.g. in tests) is safe. If you'd rather avoid
> the global staging functions entirely, pass `guards=`, `interceptors=`, or `pipes=` directly to
> `create_app()`.

### Pipes

```python
from fastnest.common.pipes import ValidationPipe, ParseIntPipe

@Post()
@UsePipe(ValidationPipe)
async def create(self, body: CreateUserDto = Body()): ...

@Get("{id}")
@UsePipe(ParseIntPipe)
async def find_one(self, id = Param("id")): ...
```

### Interceptors

```python
import time
from fastnest.common.interfaces import NestInterceptor

class LoggingInterceptor(NestInterceptor):
    def intercept_before(self, request: Request):
        request.state.start = time.time()

    def intercept_after(self, request: Request, response):
        elapsed = time.time() - request.state.start
        print(f"{request.method} {request.url.path} — {elapsed:.3f}s")
        return response
```

### Exception Filters

```python
from fastnest.common.interfaces import ExceptionFilter

class HttpErrorFilter(ExceptionFilter):
    def catch(self, exception: Exception, request: Request) -> dict:
        return {"statusCode": 500, "message": str(exception)}

# Method-level
@Get()
@UseExceptionFilter(HttpErrorFilter)
async def risky(self): ...

# Controller-level (applies to every route in the controller)
@UseExceptionFilter(HttpErrorFilter)
@Controller("users")
class UsersController: ...

# Global (applies to the entire app)
from fastnest.core.factory import add_global_filter
add_global_filter(HttpErrorFilter)
app = create_app(AppModule)

# Equivalently, scope it explicitly to one app via create_app():
app = create_app(AppModule, filters=[HttpErrorFilter])
```

A filter's `catch()` is only invoked for *unhandled* exceptions raised inside a handler —
`HTTPException` (and FastNest's built-in exceptions like `NotFoundException`) bypass filters
entirely and are handled by FastAPI's normal HTTP error response. Return `None` from `catch()`
to let a broader filter (or FastAPI's default 500 handler) take over instead.

> **Precedence:** when a global, controller-level, and method-level filter are all registered for
> the same route, they're tried narrowest-first — method → controller → global — and the first one
> whose `catch()` returns a non-`None` result wins. This is the opposite traversal order from
> Guards/Interceptors/Pipes (which all run global → controller → method), but it matches the
> intuition that a filter registered closer to the handler knows more about that specific error
> and should be able to override a broader, catch-all filter.
>
> **Scoping:** like `add_global_guard()`, `add_global_filter()` stages a registration for the
> *next* `create_app()` call only — see the note under [Guards](#guards) for details.

### Custom Param Decorators

```python
from fastnest.common.decorators import createParamDecorator

CurrentUser = createParamDecorator(
    lambda data, request: request.state.user
)

@Get("me")
async def me(self, user=CurrentUser()):
    return user
```

### Dynamic Modules

```python
@Module({})
class ConfigModule:
    @classmethod
    def for_root(cls, config: dict):
        return DynamicModule(
            module=cls,
            providers=[ConfigService],
            exports=[ConfigService],
            is_global=True,
        )

# Usage
@Module(imports=[ConfigModule.for_root({"debug": True})])
class AppModule:
    pass
```

### Lifecycle Hooks

```python
from fastnest.common.lifecycle import OnModuleInit, OnModuleDestroy

@Injectable()
class DatabaseService(OnModuleInit, OnModuleDestroy):
    async def on_module_init(self):
        await self.connect()

    async def on_module_destroy(self):
        await self.disconnect()
```

### Middleware

```python
from fastnest.core.middleware import NestMiddleware

class CorsMiddleware(NestMiddleware):
    async def use(self, request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

@Module({})
class AppModule:
    def configure(self, consumer):
        consumer.apply(CorsMiddleware).for_all()
```

---

## Request Pipeline

Every request flows through this pipeline in order:

```
Request
   │
   ▼
Middleware          (global, applied before routing)
   │
   ▼
Guards              (Global → Controller → Method)
   │
   ▼
Interceptors Before (Global → Controller → Method)
   │
   ▼
Pipes               (transform & validate params)
   │
   ▼
Handler             (your controller method)
   │
   ▼
Interceptors After  (Method → Controller → Global, reversed)
   │
   ▼
Exception Filters   (Method → Controller → Global, narrowest wins)
   │
   ▼
Response
```

---

## Built-in Exceptions

```python
from fastnest.common.exceptions import (
    BadRequestException,        # 400
    UnauthorizedException,      # 401
    ForbiddenException,         # 403
    NotFoundException,          # 404
    ConflictException,          # 409
    UnprocessableEntityException, # 422
    InternalServerErrorException, # 500
)

def find_one(self, id: int):
    user = self.db.find(id)
    if not user:
        raise NotFoundException(f"User #{id} not found")
    return user
```

---

### 🛰️ Real-time with WebSockets

FastNest supports real-time communication out of the box. You can create WebSocket gateways just as easily as HTTP controllers.

```python
from fastnest.core.websocket import WebSocketGateway, SubscribeMessage, OnConnect, OnDisconnect, WebSocketClient

@WebSocketGateway("/chat")
class ChatGateway:

    @OnConnect()
    async def on_connect(self, client: WebSocketClient):
        print(f"Client connected: {client.id}")

    @OnDisconnect()
    async def on_disconnect(self, client: WebSocketClient):
        print(f"Client disconnected: {client.id}")

    @SubscribeMessage("message")
    async def handle_message(self, data: str, client: WebSocketClient):
        await client.send({"event": "reply", "data": "Message received!"})
```

#### Namespaces

Pass `namespace=` to isolate two gateways that share the same base `path` — each namespace gets its own connection pool and its own route (`{path}/{namespace}`), so clients on one namespace never see traffic from another:

```python
@WebSocketGateway("/chat", namespace="support")
class SupportGateway: ...

@WebSocketGateway("/chat", namespace="sales")
class SalesGateway: ...
```

Registering two gateways that resolve to the same `(path, namespace)` pair raises a clear error at `create_app()` time instead of silently dropping one of them.

#### Rooms

Group a subset of a gateway's connected clients under a named room and broadcast only to them:

```python
@WebSocketGateway("/chat")
class ChatGateway:

    @SubscribeMessage("join_room")
    async def join_room(self, data: str, client: WebSocketClient):
        await client.join(data)   # data is the room name

    @SubscribeMessage("room_message")
    async def room_message(self, data: dict, client: WebSocketClient):
        await self.manager.broadcast_to_room(
            data["room"], {"event": "room_message", "data": data["message"]}
        )
```

Clients are automatically removed from every room they joined when they disconnect.

---
🛠️ Quick Start
1. Installation
Bash

pip install fastnest

2. Create a Module
Python

from fastnest.core import Module
from .app.controller import AppController
from .app.service import AppService

@Module(
    controllers=[AppController],
    providers=[AppService]
)
class AppModule:
    pass

3. Bootstrap the App
Python

from fastnest.core import FastNestFactory
from .app_module import AppModule

app = FastNestFactory.create(AppModule)

📂 Project Structure

FastNest encourages a clean structure to keep your project maintainable:

    core/: The engine (DI, Module discovery, Factory).  

    common/: Shared decorators, guards, and pipes.  

    dist/: Ready-to-use distribution packages.  

🤝 Contributing

We welcome contributions! Please check our CONTRIBUTING.md for guidelines on how to submit issues and pull requests.  
📄 License

This project is licensed under the MIT License.
```


## CLI

FastNest ships a `fastnest` command (built with [Typer](https://typer.tiangolo.com/)) for scaffolding
new building blocks. It's installed automatically alongside the `fastnest` package.

```bash
fastnest generate <schematic> <name>
# or, shorter:
fastnest g <alias> <name>
```

| Schematic    | Alias | What it generates                                                       |
|--------------|-------|--------------------------------------------------------------------------|
| `module`     | `mo`  | `<name>_module.py`, `<name>_controller.py`, `<name>_service.py`, `dto/`   |
| `controller` | `co`  | `<name>_controller.py` only (target `<name>/` dir must already exist)    |
| `service`    | `se`  | `<name>_service.py` only (target `<name>/` dir must already exist)       |
| `dto`        | `dt`  | `dto/<dto-name>_<singular>_dto.py` (e.g. `create_user_dto.py`)            |
| `resource`   | `res` | Same as `module`, but with a working in-memory CRUD implementation       |
| `guard`      | `gu`  | `common/guards/<name>_guard.py` — a `CanActivate` template                |
| `gateway`    | `ga`  | `<name>_gateway.py` — a `@WebSocketGateway` template                      |

All commands accept `--path` / `-p` to target a directory other than the current one.

### Example: `fastnest g res products`

```bash
$ fastnest g res products
CREATE products/products_module.py
CREATE products/products_controller.py
CREATE products/products_service.py
CREATE products/dto/create_product_dto.py
CREATE products/dto/update_product_dto.py

Found ./app_module.py
Register ProductsModule in app_module.py? (adds import + adds to imports=[...]) [y/N]: y
UPDATE ./app_module.py
```

`products_service.py` comes with working CRUD backed by an in-memory list (`self._items = []`),
matching the pattern used in the Quick Start above — not database-backed. A comment in the
generated file explains how to swap in a real `DatabaseService` later. `products_controller.py`
wires up `Body()` / `Param()` / `Query()` the same way.

### Auto-registering the module

After generating a `module` or `resource`, FastNest looks for `app_module.py` in the current
directory (and up to 3 parent directories) and, if found, asks for confirmation before touching it:

```
Register ProductsModule in app_module.py? (adds import + adds to imports=[...]) [y/N]
```

- **`y`** — parses `app_module.py` with Python's `ast` module (not regex) to safely add the import
  and append `ProductsModule` to the `@Module(imports=[...])` list, preserving existing formatting.
- **`N` / no input** — nothing is touched; the exact two lines to add by hand are printed instead:
  ```
  from .products.products_module import ProductsModule
  imports=[..., ProductsModule]
  ```
- If no `app_module.py` is found nearby, the same manual instructions are printed and the step is
  skipped entirely.

Generating into a directory/file that already exists is a hard error (never silently overwritten).
`controller` / `service` / `dto` schematics print a warning (not an error) if `<name>_module.py`
isn't found nearby, since you may be intentionally adding to a differently-organized module.

### Creating a new project

`fastnest new <project-name>` scaffolds a brand-new, runnable FastNest project (as opposed to
`fastnest generate`, which adds building blocks to a project that already exists):

```bash
fastnest new my-app
```

```
my-app/
├── src/
│   ├── __init__.py
│   ├── main.py              # create_app(AppModule) + uvicorn entrypoint
│   ├── app_module.py        # AppModule + a GET /health route
│   ├── config/              # ConfigModule + ConfigService (.env-based, safe defaults)
│   └── common/               # empty guards/interceptors/decorators dirs, ready to fill in
├── tests/
│   └── test_health.py
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

There is no `database/` folder and no required secrets by default — `ConfigService` only has
`app_name` and `debug`, both with safe defaults, so the project runs immediately with no `.env`
setup. Add a database module later with `fastnest g module database`, and add fields without a
default to `ConfigService` once you have real secrets to fail fast on (see
`example/example/config/config_service.py` for that fuller pattern).

If `my-app/` already exists, you're asked to confirm before anything is overwritten:

```
Directory 'my-app' already exists. Overwrite its contents? [y/N]
```

Pass `--yes` / `-y` to skip that prompt. `fastnest new` never runs `git init`, `pip install`, or any
other command on your behalf — it only prints the next steps:

```
✓ Created project 'my-app'

Next steps:
  cd my-app
  python -m venv venv && source venv/bin/activate
  pip install -e ".[dev]"
  cp .env.example .env
  uvicorn src.main:app --reload
  pytest
```

---

## Roadmap

- [ ] Microservices transport (Redis, RabbitMQ, TCP)
- [x] CLI generator (`fastnest generate module users`)
- [ ] Testing utilities (`TestingModule.create_testing_module()`)
- [ ] Swagger / OpenAPI auto-generation from decorators

---

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT — see [LICENSE](LICENSE).
