import pytest

import juliapkg
from juliapkg.deps import PkgSpec


def test_openssl_compat():
    assert juliapkg.deps.openssl_compat((1, 2, 3)) == "1.2 - 1.2.3"
    assert juliapkg.deps.openssl_compat((2, 3, 4)) == "2.3 - 2.3.4"
    assert juliapkg.deps.openssl_compat((3, 0, 0)) == "3 - 3.0"
    assert juliapkg.deps.openssl_compat((3, 1, 0)) == "3 - 3.1"
    assert juliapkg.deps.openssl_compat((3, 1, 2)) == "3 - 3.1"
    assert isinstance(juliapkg.deps.openssl_compat(), str)


def test_pkgspec_validation():
    # Test valid construction
    spec = PkgSpec(name="Example", uuid="123e4567-e89b-12d3-a456-426614174000")
    assert spec.name == "Example"
    assert spec.uuid == "123e4567-e89b-12d3-a456-426614174000"
    assert spec.dev is False
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
    assert spec.dev is True
    assert spec.version == "1.0.0"
    assert spec.path == "/path/to/pkg"
    assert spec.subdir == "subdir"
    assert spec.url == "https://example.com/pkg.git"
    assert spec.rev == "main"

    # Test invalid name
    with pytest.raises(ValueError, match="name must be a non-empty string"):
        PkgSpec(name="", uuid="0000")
    with pytest.raises(ValueError, match="name must be a non-empty string"):
        PkgSpec(name=123, uuid="0000")

    # Test invalid UUID
    with pytest.raises(ValueError, match="uuid must be a non-empty string"):
        PkgSpec(name="Example", uuid="")
    with pytest.raises(ValueError, match="uuid must be a non-empty string"):
        PkgSpec(name="Example", uuid=123)

    # Test invalid dev flag
    with pytest.raises(TypeError, match="dev must be a boolean"):
        PkgSpec(name="Example", uuid="0000", dev="not-a-boolean")

    # Test invalid version type
    with pytest.raises(TypeError, match="version must be a string, Version, or None"):
        PkgSpec(name="Example", uuid="0000", version=123)

    # Test invalid path type
    with pytest.raises(TypeError, match="path must be a string or None"):
        PkgSpec(name="Example", uuid="0000", path=123)

    # Test invalid subdir type
    with pytest.raises(TypeError, match="subdir must be a string or None"):
        PkgSpec(name="Example", uuid="0000", subdir=123)

    # Test invalid url type
    with pytest.raises(TypeError, match="url must be a string or None"):
        PkgSpec(name="Example", uuid="0000", url=123)

    # Test invalid rev type
    with pytest.raises(TypeError, match="rev must be a string or None"):
        PkgSpec(name="Example", uuid="0000", rev=123)
