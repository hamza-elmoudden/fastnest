"""
FastNest CLI — Tests
=====================
Run: pytest tests/test_cli.py -v
"""

import importlib.util
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fastnest.cli.main import app

runner = CliRunner()


@pytest.fixture
def project_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class TestModuleGeneration:
    def test_generate_module_creates_all_four_files(self, project_dir):
        result = runner.invoke(app, ["generate", "module", "users"], input="n\n")
        assert result.exit_code == 0, result.output

        base = project_dir / "users"
        assert (base / "users_module.py").is_file()
        assert (base / "users_controller.py").is_file()
        assert (base / "users_service.py").is_file()
        assert (base / "dto" / "create_user_dto.py").is_file()
        assert (base / "dto" / "update_user_dto.py").is_file()

        module_src = (base / "users_module.py").read_text()
        assert "@Module(controllers=[UsersController], providers=[UsersService])" in module_src
        assert "class UsersModule" in module_src

        controller_src = (base / "users_controller.py").read_text()
        assert "@Controller(\"users\")" in controller_src
        assert "class UsersController" in controller_src
        assert "class UsersService" in (base / "users_service.py").read_text()

        create_dto_src = (base / "dto" / "create_user_dto.py").read_text()
        assert "class CreateUserDto(BaseModel)" in create_dto_src
        update_dto_src = (base / "dto" / "update_user_dto.py").read_text()
        assert "class UpdateUserDto(BaseModel)" in update_dto_src


class TestAliases:
    @pytest.mark.parametrize(
        "long_form, alias, args",
        [
            ("module", "mo", ["a_users"]),
            ("controller", "co", ["b_users"]),
            ("service", "se", ["c_users"]),
            ("dto", "dt", ["d_users", "create"]),
            ("resource", "res", ["e_users"]),
            ("guard", "gu", ["f_auth"]),
            ("gateway", "ga", ["g_chat"]),
        ],
    )
    def test_alias_matches_long_form(self, project_dir, long_form, alias, args):
        long_dir = project_dir / "long"
        alias_dir = project_dir / "alias"
        long_dir.mkdir()
        alias_dir.mkdir()

        if long_form in ("controller", "service", "dto"):
            (long_dir / args[0]).mkdir()
            (alias_dir / args[0]).mkdir()

        long_result = runner.invoke(
            app, ["generate", long_form, *args, "--path", str(long_dir)], input="n\n"
        )
        alias_result = runner.invoke(
            app, ["g", alias, *args, "--path", str(alias_dir)], input="n\n"
        )

        assert long_result.exit_code == 0, long_result.output
        assert alias_result.exit_code == 0, alias_result.output

        long_files = sorted(p.relative_to(long_dir) for p in long_dir.rglob("*") if p.is_file())
        alias_files = sorted(p.relative_to(alias_dir) for p in alias_dir.rglob("*") if p.is_file())
        assert long_files == alias_files

        for rel in long_files:
            assert (long_dir / rel).read_text() == (alias_dir / rel).read_text()


class TestResource:
    def test_resource_generates_working_crud(self, project_dir):
        result = runner.invoke(app, ["generate", "resource", "products"], input="n\n")
        assert result.exit_code == 0, result.output

        service_path = project_dir / "products" / "products_service.py"
        controller_path = project_dir / "products" / "products_controller.py"
        controller_src = controller_path.read_text()
        for method in ("find_all", "find_one", "create", "update", "remove"):
            assert f"def {method}" in controller_src

        service_module = load_module(service_path, "generated_products_service")
        service = service_module.ProductsService()

        class FakeDto:
            def model_dump(self):
                return {"name": "Widget"}

        created = service.create(FakeDto())
        assert created["name"] == "Widget"
        assert service.find_one(created["id"])["name"] == "Widget"
        assert service.find_all() == [created]

        updated = service.update(created["id"], FakeDto())
        assert updated["name"] == "Widget"

        removed = service.remove(created["id"])
        assert removed == {"deleted": created["id"]}
        assert service.find_all() == []


class TestAutoRegistration:
    APP_MODULE_SRC = '''from fastnest.core.decorators import Module
from .users.users_module import UsersModule


@Module(
    imports=[
        UsersModule,
    ],
)
class AppModule:
    pass
'''

    def test_registration_accepted(self, project_dir):
        (project_dir / "app_module.py").write_text(self.APP_MODULE_SRC)

        result = runner.invoke(app, ["generate", "module", "orders"], input="y\n")
        assert result.exit_code == 0, result.output

        updated_src = (project_dir / "app_module.py").read_text()
        assert "from .orders.orders_module import OrdersModule" in updated_src
        assert "OrdersModule," in updated_src
        assert "UsersModule," in updated_src  # existing entry preserved

    def test_registration_declined(self, project_dir):
        (project_dir / "app_module.py").write_text(self.APP_MODULE_SRC)

        result = runner.invoke(app, ["generate", "module", "orders"], input="n\n")
        assert result.exit_code == 0, result.output

        untouched_src = (project_dir / "app_module.py").read_text()
        assert untouched_src == self.APP_MODULE_SRC
        assert "from .orders.orders_module import OrdersModule" in result.output
        assert "imports=[..., OrdersModule]" in result.output


class TestErrorHandling:
    def test_generate_into_existing_directory_errors(self, project_dir):
        (project_dir / "users").mkdir()

        result = runner.invoke(app, ["generate", "module", "users"], input="n\n")
        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_controller_without_module_dir_errors(self, project_dir):
        result = runner.invoke(app, ["generate", "controller", "ghost"], input="n\n")
        assert result.exit_code != 0
        assert "does not exist" in result.output
