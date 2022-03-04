import json
import os
import shutil

from subprocess import run
from .install_julia import best_julia_version, install_julia, log
from .compat import Version, Compat
from .state import STATE

def julia_version(exe):
    try:
        words = run([exe, '--version'], check=True, capture_output=True, encoding='utf8').stdout.strip().split()
        if words[0].lower() == 'julia' and words[1].lower() == 'version':
            return Version(words[2])
    except:
        pass

def find_julia(compat=None, prefix=None, install=False, upgrade=False):
    """Find a Julia executable compatible with compat.

    Args:
        compat: A juliapkg.compat.Compat giving bounds on the allowed version of Julia.
        prefix: An optional prefix in which to look for or install Julia.
        install: If True, install Julia if it is not found. This will use JuliaUp if
            available, otherwise will install into the given prefix.
        upgrade: If True, find the latest compatible release. Implies install=True.

    As a special case, upgrade=True does not apply when Julia is found in the PATH, because
    if it is already installed then the user is already managing their own Julia versions.
    """
    bestcompat = None
    if upgrade:
        install = True
    # env var PYTHON_JULIACALL_EXE
    ev_exe = os.getenv('PYTHON_JULIACALL_EXE')
    if ev_exe:
        ev_ver = julia_version(ev_exe)
        if ev_ver is None:
            raise Exception(f'PYTHON_JULIACALL_EXE={ev_exe} is not a Julia executable.')
        else:
            if compat is not None and ev_ver not in compat:
                log(f'WARNING: PYTHON_JULIACALL_EXE={ev_exe} is Julia {ev_ver} but {compat} is required.')
            return (ev_exe, ev_ver)
    # first look in the prefix
    if prefix is not None:
        ext = '.exe' if os.name == 'nt' else ''
        pr_exe = shutil.which(os.path.join(prefix, 'bin', 'julia' + ext))
        pr_ver = julia_version(pr_exe)
        if pr_ver is not None:
            if compat is None or pr_ver in compat:
                if upgrade and bestcompat is None:
                    bestcompat = Compat.parse('==' + best_julia_version(compat)[0])
                if bestcompat is None or pr_ver in bestcompat:
                    return (pr_exe, pr_ver)
    # see if juliaup is installed
    ju_exe = shutil.which('juliaup')
    if ju_exe:
        if upgrade and bestcompat is None:
            bestcompat = Compat.parse('==' + best_julia_version(compat)[0])
        ans = ju_find_julia(bestcompat if upgrade else compat, install=install)
        if ans:
            return ans
    else:
        # see if julia is installed
        jl_exe = shutil.which('julia')
        jl_ver = julia_version(jl_exe)
        if jl_ver is not None and (compat is None or jl_ver in compat):
            return (jl_exe, jl_ver)
        else:
            log(f'WARNING: You have Julia {jl_ver} installed but {compat} is required.')
            log(f'  It is recommended that you upgrade Julia or install JuliaUp.')
    # install into the prefix
    if install and prefix is not None:
        if upgrade and bestcompat is None:
            bestcompat = Compat.parse('==' + best_julia_version(compat)[0])
        ver, info = best_julia_version(bestcompat if upgrade else compat)
        log(f'WARNING: About to install Julia {ver} to {prefix}.')
        log(f'  If you use juliapkg in more than one environment, you are likely to have Julia')
        log(f'  installed in multiple locations. It is recommended to install JuliaUp')
        log(f'  (https://github.com/JuliaLang/juliaup) or Julia (https://julialang.org/downloads)')
        log(f'  yourself.')
        install_julia(info, prefix)
        pr_exe = shutil.which(os.path.join(prefix, 'bin', 'julia' + ext))
        pr_ver = julia_version(pr_exe)
        assert pr_ver is not None
        assert compat is None or pr_ver in compat
        assert bestcompat is None or pr_ver in bestcompat
        return (pr_exe, pr_ver)
    # failed
    compatstr = '' if compat is None else f' {compat}'
    raise Exception(f'could not find Julia{compatstr}')

def ju_find_julia(compat=None, install=False):
    # see if it is already installed
    ans = ju_find_julia_noinstall(compat)
    if ans:
        return ans
    # install it
    if install:
        ver, _ = best_julia_version(compat)
        run(['juliaup', 'add', ver], check=True)
        ans = ju_find_julia_noinstall(compat)
        if ans:
            return ans
        Exception(f'JuliaUp just installed Julia {ver} but cannot find it')

def ju_find_julia_noinstall(compat=None):
    judir = os.path.join(STATE['depot'], 'juliaup')
    metaname = os.path.join(judir, 'juliaup.json')
    if os.path.exists(metaname):
        with open(metaname) as fp:
            meta = json.load(fp)
        versions = []
        for (verstr, info) in meta.get('InstalledVersions', {}).items():
            ver = Version(verstr.split('~')[0])
            ver = Version(major=ver.major, minor=ver.minor, patch=ver.patch, prerelease=ver.prerelease, build=tuple(x for x in ver.build if x != '0'))
            if compat is None or ver in compat:
                if 'Path' in info:
                    ext = '.exe' if os.name == 'nt' else ''
                    exe = os.path.abspath(os.path.join(judir, info['Path'], 'bin', 'julia'+ext))
                    versions.append((exe, ver))
        versions.sort(key=lambda x: x[1], reverse=True)
        for (exe, _) in versions:
            ver = julia_version(exe)
            if compat is None or ver in compat:
                return (exe, ver)
