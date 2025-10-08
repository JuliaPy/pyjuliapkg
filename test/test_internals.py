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
