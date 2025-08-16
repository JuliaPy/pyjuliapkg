"""Test suite for juliapkg CLI using Click's testing infrastructure."""

import importlib
import os
import subprocess
import sys
from unittest.mock import patch

import pytest

from juliapkg.cli import cli


@pytest.fixture
def runner():
    """Create a Click test runner."""
    try:
        from click.testing import CliRunner

        return CliRunner()
    except ImportError:
        pytest.skip("click is not available")


@pytest.fixture
def fake_package_test(runner):
    result = runner.invoke(cli, ["add", "FakePackage", "--uuid", "0"])
    assert result.exit_code == 0
    assert "Queued addition of FakePackage" in result.output

    yield runner

    result = runner.invoke(cli, ["rm", "FakePackage"])
    assert result.exit_code == 0
    assert "Queued removal of FakePackage" in result.output
    result = runner.invoke(cli, ["resolve", "--force"])
    assert result.exit_code == 0


class TestCLI:
    def test_cli_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert (
            "JuliaPkg -  Manage your Julia dependencies from Python." in result.output
        )

    def test_cli_no_args(self, runner):
        result = runner.invoke(cli, [])
        assert result.exit_code == 2
        assert "Usage:" in result.output

    def test_repl_with_project(self, runner):
        result = runner.invoke(cli, ["repl", "--project=/tmp/test"])
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

    def test_error_handling_with_fake_package(self, fake_package_test):
        runner = fake_package_test

        result = runner.invoke(cli, ["resolve", "--force"])
        assert result.exit_code != 0
        assert not isinstance(result.exception, subprocess.CalledProcessError)

        k = "JULIAPKG_ALWAYS_SHOW_PYTHON_ERROR_CLI"
        old_k, os.environ[k] = os.environ[k], "1"
        try:
            result = runner.invoke(cli, ["resolve", "--force"])
            assert result.exit_code != 0
            assert isinstance(result.exception, subprocess.CalledProcessError)
        finally:
            os.environ[k] = old_k

    def test_click_not_available(self):
        with patch.dict(sys.modules, {"click": None}):
            importlib.invalidate_caches()
            if "juliapkg.cli" in sys.modules:
                del sys.modules["juliapkg.cli"]
            cli_module = importlib.import_module("juliapkg.cli")

            with pytest.raises(ImportError) as exc_info:
                cli_module.cli()

            assert "`click` is required to use the juliapkg CLI" in str(exc_info.value)
            assert "pip install click" in str(exc_info.value)
            assert 'pip install "pyjuliapkg[cli]"' in str(exc_info.value)
