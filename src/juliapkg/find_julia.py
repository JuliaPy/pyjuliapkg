import json
import os
import shutil
from subprocess import PIPE, run

from .compat import Compat, Version
from .install_julia import best_julia_version, get_short_arch, install_julia, log
from .state import STATE


def julia_version(exe):
    try:
        words = (
            run([exe, "--version"], check=True, capture_output=True, encoding="utf8")
            .stdout.strip()
            .split()
        )
        if words[0].lower() == "julia" and words[1].lower() == "version":
            return Version.parse(words[2])
    except Exception:
        pass


def find_julia(compat=None, prefix=None, install=False, upgrade=False):
    """Find a Julia executable compatible with compat.

    Args:
        compat: A juliapkg.compat.Compat giving bounds on the allowed version of Julia.
        prefix: An optional prefix in which to look for or install Julia.
        install: If True, install Julia if it is not found. This will use JuliaUp if
            available, otherwise will install into the given prefix.
        upgrade: If True, find the latest compatible release. Implies install=True.

    As a special case, upgrade=True does not apply when Julia is found in the PATH,
    because if it is already installed then the user is already managing their own Julia
    versions.
    """
    bestcompat = None
    if STATE["offline"]:
        upgrade = False
        install = False
    if upgrade:
        install = True
    # configured executable
    ev_exe = STATE["override_executable"]
    if ev_exe:
        ev_ver = julia_version(ev_exe)
        if ev_ver is None:
            raise Exception(f"juliapkg_exe={ev_exe} is not a Julia executable.")
        else:
            if compat is not None and ev_ver not in compat:
                log(
                    f"WARNING: juliapkg_exe={ev_exe} is Julia {ev_ver} but {compat} is"
                    " required."
                )
            return (ev_exe, ev_ver)
    # first look in the prefix
    if prefix is not None:
        ext = ".exe" if os.name == "nt" else ""
        pr_exe = shutil.which(os.path.join(prefix, "bin", "julia" + ext))
        pr_ver = julia_version(pr_exe)
        if pr_ver is not None:
            if compat is None or pr_ver in compat:
                if upgrade and bestcompat is None:
                    bestcompat = Compat.parse("=" + best_julia_version(compat)[0])
                if bestcompat is None or pr_ver in bestcompat:
                    return (pr_exe, pr_ver)
    # see if juliaup is installed
    try_jl = True
    ju_exe = shutil.which("juliaup")
    if ju_exe:
        ju_compat = (
            Compat.parse("=" + ju_best_julia_version(compat)[0]) if upgrade else compat
        )
        ans = ju_find_julia(ju_compat, install=install)
        if ans:
            return ans
        try_jl = install
    if try_jl:
        # see if julia is installed
        jl_exe = shutil.which("julia")
        jl_ver = julia_version(jl_exe)
        if jl_ver is not None:
            if compat is None or jl_ver in compat:
                return (jl_exe, jl_ver)
            else:
                log(
                    f"WARNING: You have Julia {jl_ver} installed but {compat} is"
                    " required."
                )
                log("  It is recommended that you upgrade Julia or install JuliaUp.")
    # install into the prefix
    if install and prefix is not None:
        if upgrade and bestcompat is None:
            bestcompat = Compat.parse("=" + best_julia_version(compat)[0])
        ver, info = best_julia_version(bestcompat if upgrade else compat)
        log(f"WARNING: About to install Julia {ver} to {prefix}.")
        log("  If you use juliapkg in more than one environment, you are likely to")
        log("  have Julia installed in multiple locations. It is recommended to")
        log("  install JuliaUp (https://github.com/JuliaLang/juliaup) or Julia")
        log("  (https://julialang.org/downloads) yourself.")
        install_julia(info, prefix)
        pr_exe = shutil.which(os.path.join(prefix, "bin", "julia" + ext))
        pr_ver = julia_version(pr_exe)
        assert pr_ver is not None
        assert compat is None or pr_ver in compat
        assert bestcompat is None or pr_ver in bestcompat
        return (pr_exe, pr_ver)
    # failed
    compatstr = "" if compat is None else f" {compat}"
    raise Exception(f"could not find Julia{compatstr}")


def ju_list_julia_versions(compat=None):
    proc = run(["juliaup", "list"], check=True, stdout=PIPE)
    vers = {}
    arch = get_short_arch()
    for line in proc.stdout.decode("utf-8").splitlines():
        words = line.strip().split()
        if len(words) == 2:
            c, v = words
            try:
                ver = Version.parse(v)
            except Exception:
                continue
            if ver.prerelease:
                continue
            if arch not in ver.build:
                continue
            ver = Version(ver.major, ver.minor, ver.patch)
            if compat is None or ver in compat:
                vers.setdefault(f"{ver.major}.{ver.minor}.{ver.patch}", []).append(c)
    return vers


def ju_best_julia_version(compat=None):
    vers = ju_list_julia_versions(compat)
    if not vers:
        raise Exception(
            f"no version of Julia is compatible with {compat} - perhaps you need to"
            " update JuliaUp"
        )
    v = sorted(vers.keys(), key=Version.parse, reverse=True)[0]
    return v, vers[v]


def ju_find_julia(compat=None, install=False):
    # see if it is already installed
    ans = ju_find_julia_noinstall(compat)
    if ans:
        return ans
    # install it
    if install:
        ver, channels = ju_best_julia_version(compat)
        log(f"Installing Julia {ver} using JuliaUp")
        msgs = []
        for channel in channels:
            proc = run(["juliaup", "add", channel], stderr=PIPE)
            if proc.returncode == 0:
                msgs = []
                break
            else:
                msg = proc.stderr.decode("utf-8").strip()
                if msg not in msgs:
                    msgs.append(msg)
        if msgs:
            log(f"WARNING: Failed to install Julia {ver} using JuliaUp: {msgs}")
        ans = ju_find_julia_noinstall(Compat.parse("=" + ver))
        if ans:
            return ans
        Exception(f"JuliaUp just installed Julia {ver} but cannot find it")


def ju_find_julia_noinstall(compat=None):
    # juliaup does not follow JULIA_DEPOT_PATH, but instead defines its
    # own env var for overriding ~/.julia
    ju_depot_path = os.getenv("JULIAUP_DEPOT_PATH")
    if not ju_depot_path:
        ju_depot_path = os.path.abspath(os.path.join(os.path.expanduser("~"), ".julia"))
    judir = os.path.join(ju_depot_path, "juliaup")
    metaname = os.path.join(judir, "juliaup.json")
    arch = get_short_arch()
    if os.path.exists(metaname):
        with open(metaname) as fp:
            meta = json.load(fp)
        versions = []
        for verstr, info in meta.get("InstalledVersions", {}).items():
            ver = Version.parse(
                verstr.replace("~", ".")
            )  # juliaup used to use VER~ARCH
            if ver.prerelease or arch not in ver.build:
                continue
            ver = Version(ver.major, ver.minor, ver.patch)
            if compat is None or ver in compat:
                if "Path" in info:
                    ext = ".exe" if os.name == "nt" else ""
                    exe = os.path.abspath(
                        os.path.join(judir, info["Path"], "bin", "julia" + ext)
                    )
                    versions.append((exe, ver))
        versions.sort(key=lambda x: x[1], reverse=True)
        for exe, _ in versions:
            ver = julia_version(exe)
            if ver is None:
                raise Exception(
                    f"{exe} (installed by juliaup) is not a valid Julia executable"
                )
            if compat is None or ver in compat:
                return (exe, ver)
