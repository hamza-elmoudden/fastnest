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

# Global (applies to entire app)
from fastnest.core.factory import add_global_guard
add_global_guard(AuthGuard)
```

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
Exception Filters   (catch unhandled errors)
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

```
🛰️ Real-time with WebSockets (New!)

FastNest now supports real-time communication out of the box. You can create WebSocket gateways just as easily as HTTP controllers.
Example Gateway
Python

```
from fastnest.core import WebSocketGateway, OnGatewayConnection, OnGatewayDisconnect
from fastapi import WebSocket

@WebSocketGateway("/chat")
class ChatGateway(OnGatewayConnection, OnGatewayDisconnect):
    
    async def on_connection(self, websocket: WebSocket):
        print(f"Client connected: {websocket.client}")

    async def on_disconnect(self, websocket: WebSocket):
        print("Client disconnected")

    @SubscribeMessage("message")
    async def handle_message(self, client: WebSocket, data: any):
        await client.send_json({"event": "reply", "data": "Message received!"})
```

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


## Roadmap

- [ ] Microservices transport (Redis, RabbitMQ, TCP)
- [ ] CLI generator (`fastnest generate module users`)
- [ ] Testing utilities (`TestingModule.create_testing_module()`)
- [ ] Swagger / OpenAPI auto-generation from decorators

---

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT — see [LICENSE](LICENSE).
