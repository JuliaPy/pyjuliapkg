import json
import os

import pytest

import juliapkg
from juliapkg.compat import Compat, Version
from juliapkg.deps import PkgSpec


def test_old_meta_forces_one_resolve(monkeypatch, tmp_path):
    meta = tmp_path / "meta.json"
    monkeypatch.setitem(juliapkg.deps.STATE, "meta", str(meta))
    body = {
        "meta_version": juliapkg.deps.META_VERSION,
        "override_executable": None,
        "executable": str(tmp_path / "bin" / "julia"),
        "version": "1.11.9",
        "offline": False,
        "deps_files": {},
        "libjulia": None,
        "pkgs": [],
    }
    meta.write_text(json.dumps(body))
    assert juliapkg.deps.load_meta() == body
    meta.write_text(json.dumps({**body, "meta_version": 7}))
    assert juliapkg.deps.load_meta() is None
    assert juliapkg.deps.can_skip_resolve() is False


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


_PROVIDERS = ("libcrypto.so.3", "libssl.so.3")
_ALIASES = ("libcrypto.jl.3", "libssl.jl.3")
_OPENSSL_JLL_UUID = "458c3c95-2e84-50aa-8efc-19380b2a3a95"


def _hardening_elf(*names):
    return b"\x7fELF" + bytes(60) + b"\0" + b"\0".join(names) + b"\0"


def _hardening_jll(root, source="old"):
    names = {
        "old": (b"libcrypto.so.3", b"libssl.so.3"),
        "partial": (b"libcrypto.jl.3", b"libssl.so.3"),
        "private": (b"libcrypto.jl.3", b"libssl.jl.3"),
    }
    if source in names:
        crypto, ssl = names[source]
        contents = (
            b'const libcrypto = "' + crypto + b'"\nconst libssl = "' + ssl + b'"\n'
        )
    else:
        contents = b"module OpenSSL_jll\nend\n"
    path = root / "share/julia/stdlib/v1.12/OpenSSL_jll/src/OpenSSL_jll.jl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(contents)
    return path


def _hardening_julia(root, providers=_PROVIDERS, rewritten=False, wrapper="old"):
    exe = root / "bin/julia"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"")
    libdir = root / "lib/julia"
    libdir.mkdir(parents=True)
    for name in providers:
        old = name.encode()
        embedded = juliapkg.openssl.PRIVATE_NAMES[old] if rewritten else old
        (libdir / name).write_bytes(_hardening_elf(embedded))
    source = _hardening_jll(root, wrapper) if wrapper is not None else None
    return exe, libdir, source


@pytest.fixture
def linux_openssl(monkeypatch):
    if os.name == "nt":
        pytest.skip("requires POSIX symlinks")
    monkeypatch.setattr(juliapkg.openssl.sys, "platform", "linux")


def _hardening_shield(exe, owned=True):
    return juliapkg.openssl.shield(str(exe), Version.parse("1.12.7"), owned=owned)


def _state(paths):
    return {
        path: path.read_bytes() for path in paths if path is not None and path.exists()
    }


def test_rewrite_names_is_exact_size_preserving_and_idempotent(tmp_path):
    path = tmp_path / "libmine.so"
    original = _hardening_elf(
        b"libcrypto.so.3", b"libssl.so.3", b"mylibssl.so.3", b"libssl.so.3x"
    )
    expected = original
    for old, new in juliapkg.openssl.PRIVATE_NAMES.items():
        expected = expected.replace(b"\0" + old + b"\0", b"\0" + new + b"\0")
    path.write_bytes(original)

    assert juliapkg.openssl.rewrite_names(str(path))
    assert path.read_bytes() == expected
    assert len(path.read_bytes()) == len(original)
    assert not juliapkg.openssl.rewrite_names(str(path))
    assert path.read_bytes() == expected


def test_rewrite_names_ignores_non_elf(tmp_path):
    path = tmp_path / "script"
    original = b"\0libcrypto.so.3\0"
    path.write_bytes(original)
    assert not juliapkg.openssl.rewrite_names(str(path))
    assert path.read_bytes() == original


@pytest.mark.parametrize(
    ("platform", "safe"), [("darwin", True), ("win32", True), ("freebsd14", False)]
)
def test_non_linux_platform_is_immutable(monkeypatch, tmp_path, platform, safe):
    exe, libdir, source = _hardening_julia(tmp_path)
    paths = (source, *(libdir / name for name in _PROVIDERS))
    before = _state(paths)
    monkeypatch.setattr(
        juliapkg.openssl, "sys", type("Platform", (), {"platform": platform})
    )

    assert _hardening_shield(exe)[0] is safe
    assert _state(paths) == before
    assert not any(os.path.lexists(libdir / name) for name in _ALIASES)


def test_owned_linux_shield_is_complete_and_idempotent(tmp_path, linux_openssl):
    exe, libdir, source = _hardening_julia(tmp_path)
    source.chmod(0o640)
    assert _hardening_shield(exe)[0]

    wrapper = source.read_bytes()
    for old, new in juliapkg.openssl.PRIVATE_NAMES.items():
        provider = libdir / old.decode()
        assert os.path.samefile(provider, libdir / new.decode())
        assert b"\0" + old + b"\0" not in provider.read_bytes()
        assert b"\0" + new + b"\0" in provider.read_bytes()
        assert b'"' + old + b'"' not in wrapper
        assert b'"' + new + b'"' in wrapper
    assert source.stat().st_mode & 0o777 == 0o640
    paths = (source, *(libdir / name for name in _PROVIDERS))
    first = _state(paths)
    assert _hardening_shield(exe)[0]
    assert _state(paths) == first


@pytest.mark.parametrize(
    ("providers", "wrapper", "missing", "message"),
    [
        (_PROVIDERS, "old", True, "incomplete"),
        ((_PROVIDERS[0],), "old", False, "incomplete"),
        (_PROVIDERS, None, False, "could not privatize"),
        (_PROVIDERS, "unknown", False, "unrecognized"),
    ],
)
def test_missing_incomplete_or_unrecognized_layout_is_immutable(
    tmp_path, linux_openssl, providers, wrapper, missing, message
):
    if missing:
        exe, libdir, source = tmp_path / "bin/julia", tmp_path / "lib/julia", None
    else:
        exe, libdir, source = _hardening_julia(tmp_path, providers, wrapper=wrapper)
    paths = [source, *(libdir / name for name in providers)]
    before = _state(paths)

    safe, note = _hardening_shield(exe)
    assert not safe and message in note
    assert _state(paths) == before
    assert not any(os.path.lexists(libdir / name) for name in _ALIASES)


@pytest.mark.parametrize("kind", ["file", "wrong", "dangling"])
def test_existing_private_path_fails_closed(tmp_path, linux_openssl, kind):
    exe, libdir, source = _hardening_julia(tmp_path)
    private = libdir / "libcrypto.jl.3"
    if kind == "file":
        private.write_bytes(b"foreign")
        private_state = private.read_bytes()
    else:
        private.symlink_to("libssl.so.3" if kind == "wrong" else "missing")
        private_state = os.readlink(private)
    paths = (source, *(libdir / name for name in _PROVIDERS))
    before = _state(paths)

    safe, note = _hardening_shield(exe)
    assert not safe and "private OpenSSL" in note
    assert _state(paths) == before
    assert (
        private.read_bytes() if kind == "file" else os.readlink(private)
    ) == private_state


def test_partial_shield_is_retry_safe(tmp_path, linux_openssl):
    exe, libdir, source = _hardening_julia(tmp_path, rewritten=True, wrapper="partial")
    assert _hardening_shield(exe)[0]
    wrapper = source.read_bytes()
    for old, new in juliapkg.openssl.PRIVATE_NAMES.items():
        assert os.path.samefile(libdir / old.decode(), libdir / new.decode())
        assert b'"' + old + b'"' not in wrapper
        assert b'"' + new + b'"' in wrapper


def test_atomic_wrapper_interruption_preserves_source(
    monkeypatch, tmp_path, linux_openssl
):
    exe, _, source = _hardening_julia(tmp_path)
    original = source.read_bytes()

    def interrupt(*_):
        raise OSError("interrupted replacement")

    monkeypatch.setattr(juliapkg.openssl.os, "replace", interrupt)
    safe, note = _hardening_shield(exe)
    assert not safe and "interrupted replacement" in note
    assert source.read_bytes() == original
    assert list(source.parent.iterdir()) == [source]


def test_walk_error_fails_closed(monkeypatch, tmp_path, linux_openssl):
    exe, libdir, source = _hardening_julia(tmp_path)
    paths = (source, *(libdir / name for name in _PROVIDERS))
    before = _state(paths)

    def fail_walk(root, onerror=None):
        onerror(OSError("walk failed"))

    monkeypatch.setattr(juliapkg.openssl.os, "walk", fail_walk)
    safe, note = _hardening_shield(exe)
    assert not safe and "walk failed" in note
    assert _state(paths) == before


def test_shield_refuses_foreign_install_without_mutation(tmp_path, linux_openssl):
    exe, libdir, source = _hardening_julia(tmp_path)
    paths = (source, *(libdir / name for name in _PROVIDERS))
    before = _state(paths)
    assert not _hardening_shield(exe, owned=False)[0]
    assert _state(paths) == before
    assert not any(os.path.lexists(libdir / name) for name in _ALIASES)


@pytest.mark.skipif(os.name == "nt", reason="requires POSIX symlinks")
def test_installed_by_juliapkg_rejects_symlink_escape(monkeypatch, tmp_path):
    install = tmp_path / "install"
    outside = tmp_path / "outside"
    (outside / "bin").mkdir(parents=True)
    (outside / "bin/julia").write_bytes(b"")
    install.mkdir()
    (install / "escape").symlink_to(outside, target_is_directory=True)
    monkeypatch.setitem(juliapkg.deps.STATE, "install", str(install))
    assert juliapkg.deps._installed_by_juliapkg(str(install / "bin/julia"))
    assert not juliapkg.deps._installed_by_juliapkg(str(install / "escape/bin/julia"))


def _hardening_reconcile(monkeypatch, tmp_path, version, **options):
    deps = juliapkg.deps
    install = tmp_path / "install"
    ours, theirs = str(install / "bin/julia"), "/usr/local/bin/julia"
    owned = options.get("owned", True)
    monkeypatch.setitem(deps.STATE, "install", str(install))
    monkeypatch.setitem(deps.STATE, "offline", options.get("offline", False))
    monkeypatch.setitem(deps.STATE, "override_executable", options.get("override"))
    monkeypatch.setattr(deps.sys, "platform", "linux")
    pin, cap = options.get("pin", "3 - 3.0"), options.get("cap", "1 - 1.11")
    monkeypatch.setattr(deps, "openssl_compat", lambda *_: (pin, cap))

    def shield(*_, owned):
        return owned and options.get("shield_ok", True), "note"

    monkeypatch.setattr(juliapkg.openssl, "shield", shield)
    found, calls = iter(options.get("found", ())), []

    def find(compat=None, system=True, **kwargs):
        calls.append((compat, system, kwargs.get("prefix")))
        is_ours, selected = next(found)
        return (ours if is_ours else theirs), Version.parse(selected)

    monkeypatch.setattr(deps, "find_julia", find)
    pkg = PkgSpec(name="OpenSSL_jll", uuid=_OPENSSL_JLL_UUID, version=pin)
    pkg._openssl_python_bound = True
    exe, selected = deps._reconcile_openssl(
        ours if owned else theirs, Version.parse(version), Compat.parse("1"), [pkg]
    )
    return exe, selected, pkg, calls, ours, str(install)


def _case(version, selected, bound, searches="", ours=True, **options):
    if options.pop("uncapped", False):
        options.update(pin="3 - 3.5", cap=None)
    return version, options, selected, bound, searches.split(), ours


_OLD, _MODERN = (((True, "1.11.9"),), ((True, "1.12.7"),))
_FAILED = dict(owned=False, shield_ok=False, found=(*_MODERN, *_OLD))
_OFFLINE = dict(owned=False, offline=True, found=_OLD)
_FORCED = dict(owned=False, uncapped=True, override="/usr/local/bin/julia")
_UNCAPPED = dict(shield_ok=False, uncapped=True, found=_OLD)
_FUTURE = dict(_FAILED, uncapped=True, found=((True, "1.13.1"), *_OLD))
_RESOLVER_CASES = [
    _case("1.11.9", "1.11.9", "3 - 3.0"),
    _case("1.12.7", "1.12.7", None),
    _case("1.12.6", "1.12.7", None, "prefix", owned=False, found=_MODERN),
    _case("1.12.6", "1.11.9", "3 - 3.0", "prefix fallback", **_FAILED),
    _case("1.12.7", "1.11.9", "3 - 3.0", "fallback", shield_ok=False, found=_OLD),
    _case("1.12.7", "1.11.9", "3 - 3.0", "fallback", **_OFFLINE),
    _case("1.12.7", "1.12.7", None, ours=False, **_FORCED),
    _case("1.12.7", "1.11.9", "3 - 3.5", "fallback", **_UNCAPPED),
    _case("1.13.0", "1.11.9", "3 - 3.5", "prefix fallback", **_FUTURE),
]


@pytest.mark.parametrize(
    ("version", "options", "selected", "bound", "searches", "ours"), _RESOLVER_CASES
)
def test_resolver_state_matrix(
    monkeypatch, tmp_path, version, options, selected, bound, searches, ours
):
    exe, actual, pkg, calls, own_exe, install = _hardening_reconcile(
        monkeypatch, tmp_path, version, **options
    )
    assert exe == (own_exe if ours else "/usr/local/bin/julia")
    assert str(actual) == selected
    assert pkg.version == bound
    assert [("fallback" if system else "prefix") for _, system, _ in calls] == searches
    safe = Compat.parse("1") & Compat.parse("1 - 1.11")
    assert all(prefix == install for _, _, prefix in calls)
    assert all((compat == safe) is system for compat, system, _ in calls)


def test_unsafe_forced_modern_julia_has_actionable_error(monkeypatch, tmp_path):
    with pytest.raises(Exception) as excinfo:
        _hardening_reconcile(
            monkeypatch,
            tmp_path,
            "1.12.7",
            owned=False,
            override="/usr/local/bin/julia",
        )
    message = str(excinfo.value)
    for choice in (
        "juliapkg_exe",
        "Julia 1.11 or earlier",
        "OpenSSL 3.5 or newer",
        "unset juliapkg_exe",
    ):
        assert choice in message


def _openssl_requirement(monkeypatch, tmp_path, versions):
    deps, files = juliapkg.deps, []
    for index, version in enumerate(versions):
        path = tmp_path / str(index) / "juliapkg.json"
        path.parent.mkdir()
        package = {"uuid": _OPENSSL_JLL_UUID, "version": version}
        path.write_text(json.dumps({"packages": {"OpenSSL_jll": package}}))
        files.append(str(path))
    monkeypatch.setattr(deps, "deps_files", lambda: files)
    monkeypatch.setattr(deps, "openssl_compat", lambda *_: ("3 - 3.0", "1 - 1.11"))
    pkg = deps.find_requirements()[1][0]
    install = tmp_path / "install"
    exe = str(install / "bin/julia")
    monkeypatch.setitem(deps.STATE, "install", str(install))
    monkeypatch.setitem(deps.STATE, "override_executable", None)
    monkeypatch.setattr(juliapkg.openssl, "shield", lambda *_, **__: (True, "note"))
    deps._reconcile_openssl(exe, Version.parse("1.12.7"), Compat.parse("1"), [pkg])
    return pkg


@pytest.mark.parametrize(
    ("versions", "expected"),
    [
        (("<=python",), None),
        (("3 - 3.0",), "~3.0"),
        (("<=python", "3 - 3.0"), "~3.0"),
    ],
)
def test_generated_and_explicit_openssl_bound_wiring(
    monkeypatch, tmp_path, versions, expected
):
    assert _openssl_requirement(monkeypatch, tmp_path, versions).version == expected


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
