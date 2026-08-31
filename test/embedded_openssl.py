#!/usr/bin/env python3
"""Exercise embedded Julia when Python and Julia use different OpenSSL builds.

JULIAPKG_TEST_JULIA optionally constrains Julia. JULIAPKG_TEST_SSL_FIRST selects
whether Python creates a TLS context before juliacall (default "1") or resolves in
a child before importing juliacall ("0").
"""

import importlib.metadata
import os
import socket
import subprocess
import sys

_juliacall = importlib.metadata.version("juliacall")
if tuple(int(part) for part in _juliacall.split(".")[:3]) < (0, 9, 35):
    sys.exit(f"juliacall {_juliacall} is too old for this check; need 0.9.35 or newer")

results = []


def check(name, ok, detail=""):
    results.append(ok)
    suffix = f" | {detail}" if detail else ""
    print(f"[{'PASS' if ok else 'FAIL'}] {name}{suffix}", flush=True)


compat = os.environ.get("JULIAPKG_TEST_JULIA")
if os.environ.get("JULIAPKG_TEST_SSL_FIRST", "1") == "1":
    import ssl

    ssl.create_default_context()
    print(f"python TLS context before juliacall: {ssl.OPENSSL_VERSION}", flush=True)
    import juliapkg

    if compat:
        juliapkg.require_julia(compat)
else:
    script = "import juliapkg" + (
        f"; juliapkg.require_julia({compat!r})" if compat else ""
    )
    subprocess.run([sys.executable, "-c", script + "; juliapkg.resolve()"], check=True)
    check(
        "ssl untouched by this script before importing juliacall",
        "ssl" not in sys.modules,
    )

from juliacall import Main as jl  # noqa: E402, I001

import ssl  # noqa: E402

print(f"python {sys.version.split()[0]} | {ssl.OPENSSL_VERSION}", flush=True)
jl.seval("using Pkg, OpenSSL_jll, Downloads, Libdl")

version = jl.seval("string(VERSION)")
print(f"julia version: {version}", flush=True)
if compat:
    from juliapkg.compat import Compat, Version

    wanted = Compat.parse(compat)
    check(
        f"julia version satisfies {wanted}", Version.parse(version) in wanted, version
    )
check("Pkg usable", bool(jl.seval("Pkg.project().path")))
size = jl.seval('filesize(Downloads.download("https://julialang.org"))')
check("julia HTTPS download", size > 0, f"{size} bytes")

if jl.seval('Sys.islinux() && VERSION >= v"1.12"'):
    names = list(jl.seval("[OpenSSL_jll.libcrypto, OpenSSL_jll.libssl]"))
    check(
        "OpenSSL_jll exposes private names",
        names == ["libcrypto.jl.3", "libssl.jl.3"],
        ", ".join(names),
    )

jl.seval("""
function _openssl_libs()
    dirs = [joinpath(Sys.BINDIR, "..", "lib", "julia"), Sys.BINDIR]
    libs = String[]
    for d in dirs, f in (isdir(d) ? readdir(d, join=true) : String[])
        b = basename(f)
        if (startswith(b, "libssl") || startswith(b, "libcrypto")) && !islink(f)
            push!(libs, abspath(f))
        end
    end
    unique(libs)
end
""")
libs = list(jl.seval("_openssl_libs()"))
libs += list(
    jl.seval("[abspath(OpenSSL_jll.libcrypto_path), abspath(OpenSSL_jll.libssl_path)]")
)
for lib in dict.fromkeys(libs):
    try:
        jl.seval(f'Libdl.dlopen(raw"{lib}")')
        check(f"dlopen {os.path.basename(lib)}", True, lib)
    except Exception as error:
        detail = str(error).strip().splitlines()[0][:120]
        check(f"dlopen {os.path.basename(lib)}", False, detail)

try:
    jll_path, jll_is_own = jl.seval("""
        let path = realpath(Libdl.dlpath(OpenSSL_jll.libcrypto)),
            roots = [realpath(p) for p in [joinpath(Sys.BINDIR, ".."); DEPOT_PATH]
                     if ispath(p)]
            path, any(roots) do root
                try
                    relative = relpath(path, root)
                    relative == "." || first(splitpath(relative)) != ".."
                catch
                    false
                end
            end
        end
    """)
    check("OpenSSL_jll is Julia's own", bool(jll_is_own), str(jll_path))
except Exception as error:
    check("OpenSSL_jll is Julia's own", False, str(error))

version_call = (
    "unsafe_string(ccall((:OpenSSL_version, OpenSSL_jll.libcrypto), "
    "Cstring, (Cint,), 0))"
)
print("julia openssl in use:", jl.seval(version_call), flush=True)

try:
    context = ssl.create_default_context()
except Exception as error:
    check("python TLS context after Julia", False, str(error)[:120])
    check("python HTTPS handshake after Julia", False, "TLS context unavailable")
else:
    check("python TLS context after Julia", True, ssl.OPENSSL_VERSION)
    try:
        with socket.create_connection(("pypi.org", 443), timeout=60) as sock:
            with context.wrap_socket(sock, server_hostname="pypi.org") as tls:
                check("python HTTPS handshake after Julia", True, tls.version())
    except Exception as error:
        check("python HTTPS handshake after Julia", False, str(error)[:120])

passed = all(results)
print("VERDICT:", "PASS" if passed else "FAIL", flush=True)
sys.exit(0 if passed else 1)
