"""Test suite for juliapkg CLI using Click's testing infrastructure."""

import os
import subprocess

import pytest
from click.testing import CliRunner

from juliapkg.cli import cli


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


class TestCLI:
    def test_cli_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "JuliaPkg -  Manage your Julia dependencies from Python." in result.output

    def test_cli_no_args(self, runner: CliRunner):
        result = runner.invoke(cli, [])
        assert result.exit_code == 2
        assert "Usage:" in result.output
        assert "JuliaPkg" in result.output

    def test_repl_with_project(self, runner: CliRunner):
        result = runner.invoke(cli, ["repl", "--project=/tmp/test"])
        assert result.exit_code != 0

    def test_run_command(self, runner: CliRunner):
        result = runner.invoke(cli, ["run", "-e", "using Pkg; Pkg.status()"])
        assert result.exit_code == 0

    def test_graceful_add(self, runner: CliRunner):
        result = runner.invoke(cli, ["add", "Example", "--uuid", "7876af07-990d-54b4-ab0e-23690620f79a"])
        assert result.exit_code == 0
        assert "Queued addition of Example" in result.output
        
        result = runner.invoke(cli, ["resolve"])
        assert result.exit_code == 0

        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "Example" in result.output

        result = runner.invoke(cli, ["remove", "Example"])
        assert result.exit_code == 0
        assert "Queued removal of Example" in result.output

        result = runner.invoke(cli, ["resolve", "--force"])
        assert result.exit_code == 0

    def test_error_handling_with_fake_package(self, runner: CliRunner):
        result = runner.invoke(cli, ["add", "FakePackage", "--uuid", "0"])
        assert result.exit_code == 0
        assert "Queued addition of FakePackage" in result.output

        result = runner.invoke(cli, ["resolve"])
        assert result.exit_code != 0
        assert not isinstance(result.exception, subprocess.CalledProcessError)

        os.environ["JULIAPKG_ALWAYS_SHOW_PYTHON_ERROR_CLI"] = "1"
        result = runner.invoke(cli, ["resolve"])
        assert result.exit_code != 0
        assert isinstance(result.exception, subprocess.CalledProcessError)

        # clean up
        del os.environ["JULIAPKG_ALWAYS_SHOW_PYTHON_ERROR_CLI"]
        result = runner.invoke(cli, ["rm", "FakePackage"])
        assert result.exit_code == 0
        assert "Queued removal of FakePackage" in result.output
        result = runner.invoke(cli, ["resolve", "--force"])
        assert result.exit_code == 0


if __name__ == "__main__":
    pytest.main([__file__]) 