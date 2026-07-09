from pathlib import Path
from string import Template

import typer

from fastnest.cli import ast_utils
from fastnest.cli.naming import singularize, to_pascal_case

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

app = typer.Typer(
    help="Generate FastNest building blocks: module, controller, service, dto, resource, guard, gateway.",
    no_args_is_help=True,
)


def build_context(name: str) -> dict:
    singular = singularize(name)
    return {
        "name": name,
        "ClassName": to_pascal_case(name),
        "singular": singular,
        "SingularClass": to_pascal_case(singular),
    }


def render(template_name: str, context: dict) -> str:
    text = (TEMPLATES_DIR / template_name).read_text()
    return Template(text).substitute(context)


def write_file(path: Path, content: str) -> Path:
    if path.exists():
        typer.echo(
            f"Error: '{path}' already exists. Choose a different name or edit it manually.",
            err=True,
        )
        raise typer.Exit(code=1)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def print_created(paths: list[Path]) -> None:
    for path in paths:
        typer.echo(f"CREATE {path}")


def warn_if_module_missing(base: Path, name: str) -> None:
    module_file = base / f"{name}_module.py"
    if not module_file.exists():
        typer.echo(
            f"Warning: '{module_file}' not found — make sure this belongs to an existing module."
        )


def require_existing_dir(base: Path, name: str) -> None:
    if not base.exists():
        typer.echo(
            f"Error: directory '{base}' does not exist. "
            f"Run 'fastnest generate module {name}' first, or create the directory manually.",
            err=True,
        )
        raise typer.Exit(code=1)


def offer_registration(feature_name: str, class_name: str, search_root: Path) -> None:
    module_class = f"{class_name}Module"
    import_line = f"from .{feature_name}.{feature_name}_module import {module_class}"

    def print_manual_instructions() -> None:
        typer.echo("Add these manually:")
        typer.echo(f"  {import_line}")
        typer.echo(f"  imports=[..., {module_class}]")

    app_module_path = ast_utils.find_app_module(search_root)
    if app_module_path is None:
        typer.echo("\nNo app_module.py found nearby — skipping auto-registration.")
        print_manual_instructions()
        return

    typer.echo(f"\nFound {app_module_path}")
    register = typer.confirm(
        f"Register {module_class} in app_module.py? "
        f"(adds import + adds to imports=[...])",
        default=False,
    )
    if not register:
        print_manual_instructions()
        return

    try:
        ast_utils.register_module(app_module_path, module_class, import_line)
    except ValueError as exc:
        typer.echo(f"Could not update {app_module_path} automatically: {exc}")
        print_manual_instructions()
        return

    typer.echo(f"UPDATE {app_module_path}")


def _generate_module_like(
    name: str,
    path: str,
    controller_template: str,
    service_template: str,
) -> None:
    ctx = build_context(name)
    base = Path(path) / name
    if base.exists():
        typer.echo(
            f"Error: '{base}' already exists. Choose a different name or edit the module manually.",
            err=True,
        )
        raise typer.Exit(code=1)

    created = [
        write_file(base / f"{name}_module.py", render("module.py.tpl", ctx)),
        write_file(base / f"{name}_controller.py", render(controller_template, ctx)),
        write_file(base / f"{name}_service.py", render(service_template, ctx)),
        write_file(
            base / "dto" / f"create_{ctx['singular']}_dto.py",
            render("dto.py.tpl", {**ctx, "DtoClassName": f"Create{ctx['SingularClass']}Dto"}),
        ),
        write_file(
            base / "dto" / f"update_{ctx['singular']}_dto.py",
            render("dto.py.tpl", {**ctx, "DtoClassName": f"Update{ctx['SingularClass']}Dto"}),
        ),
    ]
    print_created(created)
    offer_registration(name, ctx["ClassName"], Path(path))


def module_command(
    name: str = typer.Argument(..., help="Feature name, e.g. 'users'"),
    path: str = typer.Option(".", "--path", "-p", help="Directory to create the module in"),
) -> None:
    _generate_module_like(name, path, "controller.py.tpl", "service.py.tpl")


def resource_command(
    name: str = typer.Argument(..., help="Feature name, e.g. 'products'"),
    path: str = typer.Option(".", "--path", "-p", help="Directory to create the resource in"),
) -> None:
    _generate_module_like(
        name, path, "resource/controller.py.tpl", "resource/service.py.tpl"
    )


def controller_command(
    name: str = typer.Argument(..., help="Feature name, e.g. 'users'"),
    path: str = typer.Option(".", "--path", "-p", help="Directory containing the feature module"),
) -> None:
    ctx = build_context(name)
    base = Path(path) / name
    require_existing_dir(base, name)
    target = write_file(base / f"{name}_controller.py", render("controller.py.tpl", ctx))
    print_created([target])
    warn_if_module_missing(base, name)


def service_command(
    name: str = typer.Argument(..., help="Feature name, e.g. 'users'"),
    path: str = typer.Option(".", "--path", "-p", help="Directory containing the feature module"),
) -> None:
    ctx = build_context(name)
    base = Path(path) / name
    require_existing_dir(base, name)
    target = write_file(base / f"{name}_service.py", render("service.py.tpl", ctx))
    print_created([target])
    warn_if_module_missing(base, name)


def dto_command(
    name: str = typer.Argument(..., help="Feature name, e.g. 'users'"),
    dto_name: str = typer.Argument(..., help="Dto kind, e.g. 'create' or 'update'"),
    path: str = typer.Option(".", "--path", "-p", help="Directory containing the feature module"),
) -> None:
    ctx = build_context(name)
    base = Path(path) / name
    require_existing_dir(base, name)

    dto_class = f"{to_pascal_case(dto_name)}{ctx['SingularClass']}Dto"
    filename = f"{dto_name}_{ctx['singular']}_dto.py"
    target = write_file(
        base / "dto" / filename, render("dto.py.tpl", {**ctx, "DtoClassName": dto_class})
    )
    print_created([target])
    warn_if_module_missing(base, name)


def guard_command(
    name: str = typer.Argument(..., help="Guard name, e.g. 'auth'"),
    path: str = typer.Option(".", "--path", "-p", help="Project root"),
) -> None:
    ctx = build_context(name)
    base = Path(path) / "common" / "guards"
    target = write_file(base / f"{name}_guard.py", render("guard.py.tpl", ctx))
    print_created([target])


def gateway_command(
    name: str = typer.Argument(..., help="Gateway name, e.g. 'chat'"),
    path: str = typer.Option(".", "--path", "-p", help="Directory to create the gateway in"),
) -> None:
    ctx = build_context(name)
    target = write_file(Path(path) / f"{name}_gateway.py", render("gateway.py.tpl", ctx))
    print_created([target])


app.command("module")(module_command)
app.command("mo")(module_command)

app.command("controller")(controller_command)
app.command("co")(controller_command)

app.command("service")(service_command)
app.command("se")(service_command)

app.command("dto")(dto_command)
app.command("dt")(dto_command)

app.command("resource")(resource_command)
app.command("res")(resource_command)

app.command("guard")(guard_command)
app.command("gu")(guard_command)

app.command("gateway")(gateway_command)
app.command("ga")(gateway_command)
