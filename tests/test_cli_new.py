"""
FastNest CLI — `fastnest new` tests
=====================================
Run: pytest tests/test_cli_new.py -v
"""

import pytest
from typer.testing import CliRunner

from fastnest.cli.main import app

runner = CliRunner()

EXPECTED_FILES = [
    "src/__init__.py",
    "src/main.py",
    "src/app_module.py",
    "src/config/__init__.py",
    "src/config/config_module.py",
    "src/config/config_service.py",
    "src/common/guards/.gitkeep",
    "src/common/interceptors/.gitkeep",
    "src/common/decorators/.gitkeep",
    "tests/__init__.py",
    "tests/test_health.py",
    ".env.example",
    ".gitignore",
    "pyproject.toml",
    "README.md",
]


@pytest.fixture
def project_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestNewProjectStructure:
    def test_creates_all_expected_files(self, project_dir):
        result = runner.invoke(app, ["new", "demo"])
        assert result.exit_code == 0, result.output

        base = project_dir / "demo"
        for rel in EXPECTED_FILES:
            assert (base / rel).is_file(), f"missing {rel}"

    def test_pyproject_has_correct_project_name(self, project_dir):
        result = runner.invoke(app, ["new", "demo"])
        assert result.exit_code == 0, result.output

        pyproject_src = (project_dir / "demo" / "pyproject.toml").read_text()
        assert 'name = "demo"' in pyproject_src

    def test_config_service_has_safe_defaults(self, project_dir):
        result = runner.invoke(app, ["new", "demo"])
        assert result.exit_code == 0, result.output

        config_src = (project_dir / "demo" / "src" / "config" / "config_service.py").read_text()
        assert 'app_name: str = "my-app"' in config_src
        assert "debug: bool = False" in config_src
        # Unlike example/example/config/config_service.py, nothing here is a
        # bare required field (e.g. `db_url: str` with no default) — the
        # names may appear in an explanatory comment, but not as field
        # declarations.
        field_lines = [
            line.strip()
            for line in config_src.splitlines()
            if ":" in line and not line.strip().startswith(("#", '"'))
        ]
        assert not any(line.startswith("db_url:") for line in field_lines)
        assert not any(line.startswith("jwt_secret:") for line in field_lines)

    def test_health_test_file_has_expected_structure(self, project_dir):
        result = runner.invoke(app, ["new", "demo"])
        assert result.exit_code == 0, result.output

        test_src = (project_dir / "demo" / "tests" / "test_health.py").read_text()
        assert "def test_health_check" in test_src
        assert '"/health"' in test_src
        assert '{"status": "ok"}' in test_src

    def test_generated_health_endpoint_actually_works(self, project_dir):
        result = runner.invoke(app, ["new", "demo"])
        assert result.exit_code == 0, result.output

        base = project_dir / "demo"
        import sys

        sys.path.insert(0, str(base))
        try:
            for mod in list(sys.modules):
                if mod == "src" or mod.startswith("src."):
                    del sys.modules[mod]

            from fastapi.testclient import TestClient
            from src.app_module import AppModule

            from fastnest.core.factory import create_app

            app_instance = create_app(AppModule)
            with TestClient(app_instance) as client:
                response = client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
        finally:
            sys.path.remove(str(base))
            for mod in list(sys.modules):
                if mod == "src" or mod.startswith("src."):
                    del sys.modules[mod]


class TestNewProjectOverwrite:
    def test_second_run_without_confirmation_aborts(self, project_dir):
        first = runner.invoke(app, ["new", "demo"])
        assert first.exit_code == 0, first.output

        marker = project_dir / "demo" / "src" / "main.py"
        original_content = marker.read_text()
        marker.write_text(original_content + "\n# local edit\n")

        second = runner.invoke(app, ["new", "demo"], input="n\n")
        assert second.exit_code != 0
        assert "already exists" in second.output
        assert marker.read_text() == original_content + "\n# local edit\n"

    def test_second_run_with_confirmation_overwrites(self, project_dir):
        first = runner.invoke(app, ["new", "demo"])
        assert first.exit_code == 0, first.output

        marker = project_dir / "demo" / "src" / "main.py"
        marker.write_text(marker.read_text() + "\n# local edit\n")

        second = runner.invoke(app, ["new", "demo"], input="y\n")
        assert second.exit_code == 0, second.output
        assert "# local edit" not in marker.read_text()

    def test_second_run_with_yes_flag_overwrites(self, project_dir):
        first = runner.invoke(app, ["new", "demo"])
        assert first.exit_code == 0, first.output

        marker = project_dir / "demo" / "src" / "main.py"
        marker.write_text(marker.read_text() + "\n# local edit\n")

        second = runner.invoke(app, ["new", "demo", "--yes"])
        assert second.exit_code == 0, second.output
        assert "# local edit" not in marker.read_text()
