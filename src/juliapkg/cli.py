"""Command-line interface for juliapkg."""

try:
    import click

    from .deps import (
        add as _add,
    )
    from .deps import (
        resolve as _resolve,
    )
    from .deps import (
        rm as _rm,
    )
    from .deps import (
        status as _status,
    )
    from .deps import (
        update as _update,
    )
    from .repl import run as _run

    @click.group()
    def cli():
        """JuliaPkg - Julia version manager and package manager."""
        pass

    @cli.command()
    @click.argument("package")
    @click.option("--uuid", required=True, help="UUID of the package")
    @click.option("--version", help="Version constraint")
    @click.option("--dev", is_flag=True, help="Add as development dependency")
    @click.option("--path", help="Local path to package")
    @click.option("--subdir", help="Subdirectory within the package")
    @click.option("--url", help="Git URL for the package")
    @click.option("--rev", help="Git revision/branch/tag")
    @click.option("--target", help="Target environment")
    def add(package, uuid, version, dev, path, subdir, url, rev, target):
        """Add a Julia package to the project."""
        _add(
            package,
            uuid=uuid,
            version=version,
            dev=dev,
            path=path,
            subdir=subdir,
            url=url,
            rev=rev,
            target=target,
        )

    @cli.command()
    @click.option("--force", is_flag=True, help="Force resolution")
    @click.option("--dry-run", is_flag=True, help="Dry run (don't actually install)")
    @click.option("--update", is_flag=True, help="Update dependencies")
    def resolve(force, dry_run, update):
        """Resolve and install Julia dependencies."""
        _resolve(
            force=force,
            dry_run=dry_run,
            update=update,
        )

    @cli.command(name="remove")
    @click.argument("package")
    @click.option("--target", help="Target environment")
    def remove(package, target):
        """Remove a Julia package from the project."""
        _rm(
            package,
            target=target,
        )
    cli.add_command(remove, name="rm")

    @cli.command(name="status")
    @click.option("--target", help="Target environment")
    def status(target):
        """Show the status of Julia packages in the project."""
        _status(
            target=target,
        )
    cli.add_command(status, name="st")

    @cli.command(name="update")
    @click.option("--dry_run", help="Dry run (don't actually install)")
    def update(dry_run):
        """Update Julia packages in the project."""
        _update(
            dry_run=dry_run,
        )
    cli.add_command(update, name="up")

    @cli.command(name="run", context_settings=dict(ignore_unknown_options=True))
    @click.argument("args", nargs=-1)
    def run(args):
        """Pass-through to Julia CLI.
        
        For example, use `run` to launch a REPL or `run script.jl` to run a script.
        """
        _run(*args)
    cli.add_command(run, name="repl")

except ImportError:

    def cli():
        raise ImportError(
            "click is required to use the juliapkg CLI. "
            "Please install it with `pip install click` or "
            '`pip install "pyjuliapkg[cli]".'
        )


if __name__ == "__main__":
    cli()
