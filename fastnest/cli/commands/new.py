import shutil
from pathlib import Path
from string import Template

import typer

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "new"


def render(template_name: str, context: dict) -> str:
    text = (TEMPLATES_DIR / template_name).read_text()
    return Template(text).substitute(context)


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def new_command(
    project_name: str = typer.Argument(..., help="Name of the new project directory"),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Overwrite an existing directory without prompting"
    ),
) -> None:
    target = Path(project_name)
    context = {"project_name": project_name}

    if target.exists():
        if not yes:
            overwrite = typer.confirm(
                f"Directory '{target}' already exists. Overwrite its contents?",
                default=False,
            )
            if not overwrite:
                typer.echo("Aborted.")
                raise typer.Exit(code=1)
        shutil.rmtree(target)

    src = target / "src"
    tests = target / "tests"
    config = src / "config"
    common = src / "common"

    write_file(src / "__init__.py", "")
    write_file(src / "main.py", render("main.py.tpl", context))
    write_file(src / "app_module.py", render("app_module.py.tpl", context))

    write_file(config / "__init__.py", "")
    write_file(config / "config_module.py", render("config_module.py.tpl", context))
    write_file(config / "config_service.py", render("config_service.py.tpl", context))

    touch(common / "guards" / ".gitkeep")
    touch(common / "interceptors" / ".gitkeep")
    touch(common / "decorators" / ".gitkeep")

    write_file(tests / "__init__.py", "")
    write_file(tests / "test_health.py", render("test_health.py.tpl", context))

    write_file(target / ".env.example", render("env.example.tpl", context))
    write_file(target / ".gitignore", render("gitignore.tpl", context))
    write_file(target / "pyproject.toml", render("pyproject.toml.tpl", context))
    write_file(target / "README.md", render("README.md.tpl", context))

    typer.echo(f"\n✓ Created project '{project_name}'\n")
    typer.echo("Next steps:")
    typer.echo(f"  cd {project_name}")
    typer.echo("  python -m venv venv && source venv/bin/activate")
    typer.echo('  pip install -e ".[dev]"')
    typer.echo("  cp .env.example .env")
    typer.echo("  uvicorn src.main:app --reload")
    typer.echo("  pytest")
