"""Give an owned Linux Julia install private OpenSSL sonames.

CPython and embedded Julia share glibc's link map, where an already loaded
bare soname wins. Rewriting Julia's exact NUL-delimited names prevents the
host OpenSSL from being substituted for Julia's copy.
"""

import mmap
import os
import stat
import sys
import tempfile

# Each replacement has the same byte length as the name it replaces.
PRIVATE_NAMES = {
    b"libcrypto.so.3": b"libcrypto.jl.3",
    b"libssl.so.3": b"libssl.jl.3",
}

assert all(len(old) == len(new) for old, new in PRIVATE_NAMES.items())


def _name_offsets(path):
    offsets = []
    with open(path, "rb") as fp:
        if fp.read(4) != b"\x7fELF":
            return offsets
        with mmap.mmap(fp.fileno(), 0, access=mmap.ACCESS_READ) as contents:
            for old, new in PRIVATE_NAMES.items():
                needle = b"\0" + old + b"\0"
                start = 0
                while (found := contents.find(needle, start)) >= 0:
                    offsets.append((found + 1, new))
                    start = found + len(needle)
    return offsets


def rewrite_names(path):
    """Rewrite every exact old OpenSSL name in one ELF file."""
    offsets = _name_offsets(path)
    if not offsets:
        return False
    with open(path, "r+b") as fp:
        for offset, new in offsets:
            fp.seek(offset)
            if fp.write(new) != len(new):
                raise OSError(f"short write while rewriting {path}")
    if _name_offsets(path):
        raise OSError(f"old OpenSSL name remains in {path}")
    return True


def _jll_source(root, version):
    path = os.path.join(
        root,
        "share",
        "julia",
        "stdlib",
        f"v{version.major}.{version.minor}",
        "OpenSSL_jll",
        "src",
        "OpenSSL_jll.jl",
    )
    with open(path, "rb") as fp:
        source = fp.read()

    candidate = source
    for old, new in PRIVATE_NAMES.items():
        candidate = candidate.replace(b'"' + old + b'"', b'"' + new + b'"')
    old_literals = (b'"' + old + b'"' for old in PRIVATE_NAMES)
    private_literals = (b'"' + new + b'"' for new in PRIVATE_NAMES.values())
    if any(literal in candidate for literal in old_literals) or not all(
        literal in candidate for literal in private_literals
    ):
        raise OSError("unrecognized OpenSSL_jll wrapper")
    return path, source, candidate


def _replace_atomic(path, contents):
    """Replace one file without exposing a partial write."""
    mode = stat.S_IMODE(os.stat(path).st_mode)
    directory = os.path.dirname(path)
    prefix = f".{os.path.basename(path)}."
    fd, temporary = tempfile.mkstemp(dir=directory, prefix=prefix, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fp:
            os.fchmod(fp.fileno(), mode)
            if fp.write(contents) != len(contents):
                raise OSError(f"short write while replacing {path}")
            fp.flush()
            os.fsync(fp.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _ensure_alias(provider, old, new):
    link = os.path.join(os.path.dirname(provider), new.decode())
    if os.path.lexists(link):
        try:
            if os.path.samefile(provider, link):
                return
        except OSError:
            pass
        raise OSError(f"private OpenSSL alias has the wrong target: {link}")
    os.symlink(old.decode(), link)
    if not os.path.samefile(provider, link):
        raise OSError(f"private OpenSSL alias has the wrong target: {link}")


def _install_files(root):
    providers = {old: [] for old in PRIVATE_NAMES}
    files = []

    def raise_walk_error(error):
        raise error

    for directory, _, names in os.walk(root, onerror=raise_walk_error):
        for name in names:
            path = os.path.join(directory, name)
            old = name.encode()
            if old in providers:
                providers[old].append(path)
            if not os.path.islink(path):
                files.append(path)
    return providers, files


def shield(exe, version, *, owned):
    """Privatize OpenSSL in an owned Julia install, failing closed on Linux."""
    if sys.platform == "darwin":
        return True, "not needed on macOS"
    if sys.platform == "win32":
        return True, "not needed on Windows"
    if not sys.platform.startswith("linux"):
        return False, "unsupported platform"
    if not owned:
        return False, "Julia was not installed by juliapkg"
    if not os.path.isfile(exe):
        return False, "incomplete Julia OpenSSL layout"

    root = os.path.dirname(os.path.dirname(os.path.realpath(exe)))
    try:
        source_path, source, repointed = _jll_source(root, version)
        providers, files = _install_files(root)
        if any(not paths for paths in providers.values()):
            return False, "incomplete Julia OpenSSL layout"
        for old, paths in providers.items():
            for provider in paths:
                _ensure_alias(provider, old, PRIVATE_NAMES[old])
        for path in files:
            rewrite_names(path)
        if repointed != source:
            _replace_atomic(source_path, repointed)
    except OSError as error:
        return False, f"could not privatize Julia's OpenSSL ({error})"
    return True, "private OpenSSL names ready"
