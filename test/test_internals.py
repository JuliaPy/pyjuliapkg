import json
import os

import pytest

import juliapkg
from juliapkg.deps import PkgSpec


def test_openssl_compat():
    assert juliapkg.deps.openssl_compat((1, 2, 3)) == ("1.2 - 1.2.3", "1 - 1.11")
    assert juliapkg.deps.openssl_compat((2, 3, 4)) == ("2.3 - 2.3.4", "1 - 1.11")
    assert juliapkg.deps.openssl_compat((3, 0, 0)) == ("3 - 3.0", "1 - 1.11")
    assert juliapkg.deps.openssl_compat((3, 1, 0)) == ("3 - 3.1", "1 - 1.11")
    assert juliapkg.deps.openssl_compat((3, 1, 2)) == ("3 - 3.1", "1 - 1.11")
    assert juliapkg.deps.openssl_compat((3, 5, 0)) == ("3 - 3.5", None)
    c = juliapkg.deps.openssl_compat()
    assert isinstance(c, tuple)
    assert len(c) == 2
    assert isinstance(c[0], str)
    assert c[1] is None or isinstance(c[1], str)


def test_pkgspec_validation():
    # Test valid construction
    spec = PkgSpec(name="Example", uuid="123e4567-e89b-12d3-a456-426614174000")
    assert spec.name == "Example"
    assert spec.uuid == "123e4567-e89b-12d3-a456-426614174000"
    assert spec.dev == False
    assert spec.version is None
    assert spec.path is None
    assert spec.subdir is None
    assert spec.url is None
    assert spec.rev is None

    # Test with all parameters
    spec = PkgSpec(
        name="Example",
        uuid="123e4567-e89b-12d3-a456-426614174000",
        dev=True,
        version="1.0.0",
        path="/path/to/pkg",
        subdir="subdir",
        url="https://example.com/pkg.git",
        rev="main",
    )
    assert spec.name == "Example"
    assert spec.uuid == "123e4567-e89b-12d3-a456-426614174000"
    assert spec.dev == True
    assert spec.version == "1.0.0"
    assert spec.path == "/path/to/pkg"
    assert spec.subdir == "subdir"
    assert spec.url == "https://example.com/pkg.git"
    assert spec.rev == "main"

    # Test invalid name
    with pytest.raises(TypeError, match="package name must be a 'str', got 'int'"):
        PkgSpec(name=123, uuid=spec.uuid)
    with pytest.raises(ValueError, match="package name cannot be empty"):
        PkgSpec(name="", uuid=spec.uuid)
    with pytest.raises(ValueError, match="package name cannot end with '.jl'"):
        PkgSpec(name="Foo.jl", uuid=spec.uuid)
    with pytest.raises(
        ValueError, match="package name contains invalid characters '.-'"
    ):
        PkgSpec(name="Foo.Bar-Baz!", uuid=spec.uuid)
    with pytest.raises(
        ValueError, match="package name has invalid first character '0'"
    ):
        PkgSpec(name="0Foo", uuid=spec.uuid)
    with pytest.raises(
        ValueError, match="package name has invalid first character '!'"
    ):
        PkgSpec(name="!Foo", uuid=spec.uuid)

    # Test invalid UUID
    with pytest.raises(TypeError, match="package uuid must be a 'str', got 'int'"):
        PkgSpec(name="Example", uuid=123)
    with pytest.raises(
        ValueError,
        match="package uuid must be of form XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
    ):
        PkgSpec(name="Example", uuid="")

    # Test invalid dev flag
    with pytest.raises(TypeError, match="package dev must be a 'bool'"):
        PkgSpec(name="Example", uuid=spec.uuid, dev="not-a-boolean")

    # Test invalid version type
    with pytest.raises(
        TypeError, match="package version must be a 'str', 'Version', or 'None'"
    ):
        PkgSpec(name="Example", uuid=spec.uuid, version=123)

    # Test invalid path type
    with pytest.raises(TypeError, match="package path must be a 'str' or 'None'"):
        PkgSpec(name="Example", uuid=spec.uuid, path=123)

    # Test invalid subdir type
    with pytest.raises(TypeError, match="package subdir must be a 'str' or 'None'"):
        PkgSpec(name="Example", uuid=spec.uuid, subdir=123)

    # Test invalid url type
    with pytest.raises(TypeError, match="package url must be a 'str' or 'None'"):
        PkgSpec(name="Example", uuid=spec.uuid, url=123)

    # Test invalid rev type
    with pytest.raises(TypeError, match="package rev must be a 'str' or 'None'"):
        PkgSpec(name="Example", uuid=spec.uuid, rev=123)

    # Test invalid preferences type
    with pytest.raises(
        TypeError, match="package preferences must be a 'dict' or 'None', got 'int'"
    ):
        PkgSpec(name="Example", uuid=spec.uuid, preferences=123)


def test_pkgspec_preferences():
    uuid = "123e4567-e89b-12d3-a456-426614174000"

    # Preferences are absent by default
    spec = PkgSpec(name="Example", uuid=uuid)
    assert spec.preferences is None
    assert "preferences" not in spec.dict()
    assert "preferences" not in spec.depsdict()

    # Preferences round-trip through dict() and depsdict()
    prefs = {"precompile_float64": False, "mode": "fast", "levels": [1, 2]}
    spec = PkgSpec(name="Example", uuid=uuid, preferences=prefs)
    assert spec.preferences == prefs
    assert spec.dict()["preferences"] == prefs
    assert spec.depsdict()["preferences"] == prefs

    # An empty preferences dict is kept (explicitly provided)
    spec = PkgSpec(name="Example", uuid=uuid, preferences={})
    assert spec.dict()["preferences"] == {}
    assert spec.depsdict()["preferences"] == {}


def test_run_script(monkeypatch):
    call = {}
    result = object()

    def run(command, **kwargs):
        call["command"] = command
        call["kwargs"] = kwargs
        return result

    monkeypatch.setattr(juliapkg.deps, "run", run)
    env = {"EXAMPLE": "yes"}

    actual = juliapkg.deps.run_script(
        ["line one", "line two"],
        executable="/bin/julia",
        project="/project",
        julia_args=["--check-bounds=yes", "--threads=2"],
        env=env,
        capture_output=True,
        text=True,
    )

    assert actual is result
    assert call["command"] == [
        "/bin/julia",
        "--check-bounds=yes",
        "--threads=2",
        "--project=/project",
        "--startup-file=no",
        "-e",
        "line one\nline two",
    ]
    assert call["kwargs"]["check"] is True
    assert call["kwargs"]["capture_output"] is True
    assert call["kwargs"]["text"] is True
    assert call["kwargs"]["env"]["EXAMPLE"] == "yes"
    assert call["kwargs"]["env"]["JULIA_PYTHONCALL_EXE"]
    assert "JULIA_PYTHONCALL_EXE" not in env


def _write_juliapkg_json(dirpath, packages):
    fn = os.path.join(dirpath, "juliapkg.json")
    with open(fn, "w") as fp:
        json.dump({"packages": packages}, fp)
    return fn


def test_find_requirements_preferences(monkeypatch, tmp_path):
    uuid = "123e4567-e89b-12d3-a456-426614174000"
    dir1 = tmp_path / "a"
    dir2 = tmp_path / "b"
    dir1.mkdir()
    dir2.mkdir()
    _write_juliapkg_json(
        dir1,
        {
            "Example": {
                "uuid": uuid,
                "preferences": {"use_jl_def": True, "mode": "fast"},
            }
        },
    )
    _write_juliapkg_json(
        dir2,
        {
            "Example": {
                "uuid": uuid,
                "preferences": {"mode": "fast", "extra": [1, 2]},
            }
        },
    )
    monkeypatch.setattr(
        juliapkg.deps,
        "deps_files",
        lambda: [
            os.path.join(str(dir1), "juliapkg.json"),
            os.path.join(str(dir2), "juliapkg.json"),
        ],
    )
    compat, pkgs = juliapkg.deps.find_requirements()
    assert compat is None
    assert len(pkgs) == 1
    assert pkgs[0].name == "Example"
    # union of preference keys across files
    assert pkgs[0].preferences == {
        "use_jl_def": True,
        "mode": "fast",
        "extra": [1, 2],
    }


def test_find_requirements_preferences_conflict(monkeypatch, tmp_path):
    uuid = "123e4567-e89b-12d3-a456-426614174000"
    dir1 = tmp_path / "a"
    dir2 = tmp_path / "b"
    dir1.mkdir()
    dir2.mkdir()
    _write_juliapkg_json(
        dir1,
        {"Example": {"uuid": uuid, "preferences": {"mode": "fast"}}},
    )
    _write_juliapkg_json(
        dir2,
        {"Example": {"uuid": uuid, "preferences": {"mode": "slow"}}},
    )
    monkeypatch.setattr(
        juliapkg.deps,
        "deps_files",
        lambda: [
            os.path.join(str(dir1), "juliapkg.json"),
            os.path.join(str(dir2), "juliapkg.json"),
        ],
    )
    with pytest.raises(Exception, match="'preferences' entries for key 'mode'"):
        juliapkg.deps.find_requirements()
