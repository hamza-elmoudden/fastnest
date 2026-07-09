[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "${project_name}"
version = "0.1.0"
description = "A FastNest application"
requires-python = ">=3.10"
dependencies = [
    "fastnest",
    "uvicorn[standard]>=0.29.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths    = ["tests"]

[tool.hatch.build.targets.wheel]
packages = ["src"]
