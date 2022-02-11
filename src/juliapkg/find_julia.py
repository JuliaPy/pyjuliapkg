import juliaup
import shutil

from subprocess import run
from .releases import best_release
from .compat import Version, Compat

def version(exe):
    """The version of the Julia executable."""
    try:
        words = run([exe, '--version'], check=True, capture_output=True, encoding='utf8').stdout.strip().split()
        if words[0].lower() == 'julia' and words[1].lower() == 'version':
            return Version(words[2])
    except:
        pass

def find_julia(compat=None, best=False, install=False):
    """Find a Julia executable compatible with compat.

    Args:
        compat: A juliapkg.compat.Compat specifying the allowed versions of Julia.
        install: If True, Julia will be installed (using JuliaUp) automatically if there
            is no compatible version.
        best: Use the best released compatible version of Julia. Implies install=True.

    As a special case, if best=True but JuliaUp is not installed and a compatible version
    of Julia is found in the PATH, that is used. The rationale is that if Julia is already
    installed, then the user is managing their own versions.
    """
    # try juliaup if already installed
    jup = shutil.which('juliaup')
    if jup:
        return jup_find(compat, best=best, install=install)
    # try the PATH
    exe = shutil.which('julia')
    ver = version(exe)
    if ver is not None:
        if compat is None or ver in compat:
            return (exe, ver)
    # finally install juliaup and try that
    return jup_find(compat, best=best, install=install)

def jup_find_best(compat=None):
    # find the best compatible release
    release = best_release(compat)
    if not release:
        raise Exception(f'no Julia release satisfies {compat}')
    v, _ = release
    compat = Compat.parse(f'=={v}')
    print(compat)
    # see if it is already installed
    ans = jup_find_current(compat)
    if ans:
        return ans
    # otherwise install it
    channel = f'{v.major}.{v.minor}.{v.patch}'
    juliaup.add(channel)
    # now find it
    ans = jup_find_current(compat)
    if ans:
        return ans
    # installing didn't work
    raise Exception(f'added JuliaUp channel {channel} but could not find Julia {version}')

def jup_find_current(compat=None):
    meta = juliaup.meta()
    versions = []
    for (verstr, info) in meta.get('InstalledVersions', {}).items():
        # juliaup records '1.2.3' as '1.2.3+0~ARCH'
        # so we filter out the ARCH and any zeros in the build
        ver = Version(verstr.split('~')[0])
        ver = Version(major=ver.major, minor=ver.minor, patch=ver.patch, partial=ver.partial, build=tuple(x for x in ver.build if x != '0'))
        if compat is None or ver in compat:
            exe = info['Executable']
            ver = version(exe)
            if ver is not None:
                if compat is None or ver in compat:
                    versions.append((exe, ver))
    if versions:
        return max(versions, key=lambda x: x[1])

def jup_find(compat=None, best=False, install=False):
    if best:
        return jup_find_best(compat)
    ans = jup_find_current(compat)
    if ans:
        return ans
    if install:
        return jup_find_best(compat)
    raise Exception(f'JuliaUp does not have Julia {compat} installed')
