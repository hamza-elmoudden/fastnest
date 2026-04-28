# Contributing to FastNest

Thanks for your interest in contributing! This guide explains how to get started.

---

## Before You Begin

- Check [Issues](https://github.com/hamza-elmoudden/fastnest/issues) — someone may have already reported it.
- For large features, open an Issue first so we can discuss the approach before writing code.
- For small fixes and bugs, feel free to open a PR directly.

---

## Development Setup

```bash
git clone https://github.com/hamza-elmoudden/fastnest.git
cd fastnest

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

pip install -e ".[dev]"
```

---

## Running the Example

```bash
uvicorn example.main:app --reload
```

---

## Running Tests

```bash
pytest
pytest -v                          # verbose output
pytest tests/test_guards.py        # specific file
pytest -k "test_validation"        # filter by name
```

Every PR must pass all existing tests and include new tests for any added feature or fix.

---

## Project Structure

```
## Project Structure

fastnest/
├── core/
│   ├── decorators.py         # @Module, @Controller, @Injectable, HTTP methods[cite: 1]
│   ├── di.py                 # Dependency Injection Container[cite: 1]
│   ├── factory.py            # create_app, route registration, middleware bridge[cite: 1]
│   ├── websocket.py          # WebSocketGateway, Message Subscriptions[cite: 1]
│   ├── metadata.py           # metadata storage with MRO inheritance[cite: 1]
│   ├── middleware.py         # NestMiddleware, MiddlewareConfig[cite: 1]
│   ├── params.py             # Body, Query, Param, etc.[cite: 1]
│   ├── reflector.py          # Reflector for Guards and Interceptors[cite: 1]
│   ├── signature_cache.py    # signature caching for performance[cite: 1]
│   ├── signature_rewriter.py # rewrites handler signatures for FastAPI[cite: 1]
│   └── dynamic_module.py     # DynamicModule for forRoot() pattern[cite: 1]
├── common/
│   ├── interfaces.py         # PipeTransform, CanActivate, NestInterceptor, ExceptionFilter, Gateway Hooks[cite: 1]
│   ├── pipes.py              # Built-in Validation and Transformation pipes[cite: 1]
│   ├── decorators.py         # SetMetadata, Roles, @UseGuards, @UseInterceptors[cite: 1]
│   ├── exceptions.py         # HttpException and subclasses[cite: 1]
│   ├── lifecycle.py          # Module and Application lifecycle hooks[cite: 1]
│   └── guards/
│       └── roles_guard.py    # Reference RolesGuard implementation[cite: 1]```

---

## Code Guidelines

**1. Type hints are required** on all public functions.

```python
# correct
def get(self, cls: type) -> Any:

# incorrect
def get(self, cls):
```

**2. Sync/async flexibility** — any Guard, Pipe, or Interceptor must work whether it is `sync` or `async`.

**3. Do not break the public API** — any change to decorators or interfaces requires discussion first.

**4. Commit messages** must follow this format:

```
feat: add WebSocket gateway support
fix: resolve signature rewrite for custom extractors
docs: update CONTRIBUTING guide
test: add integration tests for DI container
refactor: simplify middleware config builder
```

---

## Adding a New Feature

1. **New Pipe**: add it in `common/pipes.py` and inherit from `PipeTransform`.
2. **New Guard**: add it in `common/guards/` and inherit from `CanActivate`.
3. **New Decorator**: add it in `core/decorators.py` or `common/decorators.py` depending on its scope.
4. **Update `__init__.py`**: make sure the new export is included.

---

## Opening a Pull Request

1. Fork the repo and create a new branch:
   ```bash
   git checkout -b feat/my-feature
   ```
2. Write your code and tests.
3. Make sure all tests pass:
   ```bash
   pytest
   ```
4. Open a PR with a clear description of what changed and why.

---

## Questions

Open a [Discussion](https://github.com/hamza-elmoudden/fastnest/discussions) for any question that is not related to a specific bug.