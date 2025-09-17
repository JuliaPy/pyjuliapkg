import importlib
import sys
from unittest.mock import patch

import pytest

from juliapkg.cli import cli


@pytest.fixture
def runner():
    try:
        from click.testing import CliRunner

        return CliRunner()
    except ImportError:
        pytest.skip("click is not available")


class TestCLI:
    def test_cli_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "JuliaPkg - Manage your Julia dependencies from Python." in result.output

    def test_cli_no_args(self, runner):
        result = runner.invoke(cli, [])
        assert "Usage:" in result.output

    def test_run_with_project(self, runner):
        result = runner.invoke(cli, ["run", "--project=/tmp/test"])
        assert result.exit_code != 0
        assert "Do not specify --project when using pyjuliapkg" in str(result.exception)

    def test_run_command(self, runner):
        result = runner.invoke(cli, ["run", "-e", "using Pkg; Pkg.status()"])
        assert result.exit_code == 0

    def test_basic_usage(self, runner):
        result = runner.invoke(
            cli, ["add", "Example", "--uuid", "7876af07-990d-54b4-ab0e-23690620f79a"]
        )
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

    def test_click_not_available(self):
        with patch.dict(sys.modules, {"click": None, "juliapkg.cli": None}):
            del sys.modules["juliapkg.cli"]
            cli_module = importlib.import_module("juliapkg.cli")

            with pytest.raises(ImportError) as exc_info:
                cli_module.cli()

            assert "`click` is required to use the juliapkg CLI" in str(exc_info.value)
