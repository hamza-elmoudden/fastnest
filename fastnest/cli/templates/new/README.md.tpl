# ${project_name}

A [FastNest](https://github.com/hamza-elmoudden/fastnest) application.

## Getting Started

```bash
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Run the app:

```bash
uvicorn src.main:app --reload
# or
python -m src.main
```

Run the tests:

```bash
pytest
```

## Adding features

Use the FastNest CLI to scaffold new modules as the project grows:

```bash
fastnest generate module <name>
# or, shorter:
fastnest g mo <name>
```

See `fastnest --help` for the full list of schematics (`module`, `controller`, `service`, `dto`,
`resource`, `guard`, `gateway`).
