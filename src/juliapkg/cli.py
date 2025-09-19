"""Command-line interface for juliapkg."""

import os
import subprocess
import sys

from .deps import STATE, add, resolve, rm, status, update

try:
    import click
except ImportError:
    click = None

if click is None:

    def cli():
        raise ImportError(
            "`click` is required to use the juliapkg CLI. "
            "Please install it with `pip install click` or "
            '`pip install "pyjuliapkg[cli]".'
        )

else:

    class JuliaPkgGroup(click.Group):
        """Custom group to avoid long stacktraces when Julia exits with an error."""

        @property
        def always_show_python_error(self) -> bool:
            return (
                os.environ.get("PYTHON_JULIAPKG_CLI_ALWAYS_SHOW_PYTHON_ERROR", "0")
                == "1"
            )

        @staticmethod
        def _is_graceful_exit(e: subprocess.CalledProcessError) -> bool:
            """Try to guess if a CalledProcessError was Julia gracefully exiting."""
            return e.returncode == 1

        def invoke(self, ctx):
            try:
                return super().invoke(ctx)
            except subprocess.CalledProcessError as e:
                # Julia already printed an error message
                if (
                    JuliaPkgGroup._is_graceful_exit(e)
                    and not self.always_show_python_error
                ):
                    click.get_current_context().exit(1)
                else:
                    raise

    cli = JuliaPkgGroup(help="JuliaPkg - Manage your Julia dependencies from Python.")

    @cli.command(name="add")
    @click.argument("package")
    @click.option("--uuid", help="UUID of the package")
    @click.option("--version", help="Version constraint")
    @click.option("--dev", is_flag=True, help="Add as development dependency")
    @click.option("--path", help="Local path to package")
    @click.option("--subdir", help="Subdirectory within the package")
    @click.option("--url", help="Git URL for the package")
    @click.option("--rev", help="Git revision/branch/tag")
    @click.option("--target", help="Target environment")
    def add_cli(package, uuid, version, dev, path, subdir, url, rev, target):
        """Add a Julia package to the project."""
        add(
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
        click.echo(f"Queued addition of {package}. Run `resolve` to apply changes.")

    @cli.command(name="resolve")
    @click.option("--force", is_flag=True, help="Force resolution")
    @click.option("--dry-run", is_flag=True, help="Dry run (don't actually install)")
    @click.option("--update", is_flag=True, help="Update dependencies")
    def resolve_cli(force, dry_run, update):
        """Resolve and install Julia dependencies."""
        resolve(force=force, dry_run=dry_run, update=update)
        click.echo("Resolved dependencies.")

    @cli.command(name="remove")
    @click.argument("package")
    @click.option("--target", help="Target environment")
    def remove_cli(package, target):
        """Remove a Julia package from the project."""
        rm(package, target=target)
        click.echo(f"Queued removal of {package}. Run `resolve` to apply changes.")

    @cli.command(name="status")
    @click.option("--target", help="Target environment")
    def status_cli(target):
        """Show the status of Julia packages in the project."""
        status(target=target)

    @cli.command(name="update")
    @click.option("--dry-run", is_flag=True, help="Dry run (don't actually install)")
    def update_cli(dry_run):
        """Update Julia packages in the project."""
        update(dry_run=dry_run)

    @cli.command(name="run", context_settings=dict(ignore_unknown_options=True))
    @click.argument("args", nargs=-1)
    def run_cli(args):
        """Pass-through to Julia CLI.

        For example, use `run` to launch a REPL or `run script.jl` to run a script.
        """
        resolve()
        executable = STATE["executable"]
        project = STATE["project"]

        env = os.environ.copy()
        if sys.executable:
            # prefer PythonCall to use the current Python executable
            # TODO: this is a hack, it would be better for PythonCall to detect that
            #   Julia is being called from Python
            env.setdefault("JULIA_PYTHONCALL_EXE", sys.executable)
        cmd = [
            executable,
            "--project=" + project,
        ]
        for arg in args:
            if arg.startswith("--project"):
                raise ValueError("Do not specify --project when using pyjuliapkg.")
            cmd.append(arg)
        subprocess.run(
            cmd,
            check=True,
            env=env,
        )


if __name__ == "__main__":
    cli()
