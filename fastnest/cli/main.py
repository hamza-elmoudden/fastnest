import typer

from fastnest.cli.commands.generate import app as generate_app
from fastnest.cli.commands.new import new_command

app = typer.Typer(name="fastnest", help="FastNest CLI — scaffolding for FastNest projects.")

app.add_typer(generate_app, name="generate", help="Generate a building block (alias: g)")
app.add_typer(generate_app, name="g", help="Alias for 'generate'")
app.command("new", help="Scaffold a brand-new FastNest project")(new_command)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
