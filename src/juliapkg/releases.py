import json

from urllib.request import urlopen
from .compat import Version

RELEASES_URL = 'https://julialang-s3.julialang.org/bin/versions.json'
RELEASES = None

def releases(refresh=False):
    """The parsed contents of Julia's versions.json."""
    global RELEASES
    if RELEASES is None or refresh:
        with urlopen(RELEASES_URL) as fp:
            RELEASES = json.load(fp)
    return RELEASES

def best_release(compat=None, stable=True):
    """The best release compatible with compat."""
    # TODO: check the arch/os/etc is compatible too.
    # TODO: query juliaup for this information?
    versions = []
    for (verstr, info) in releases().items():
        version = Version(verstr)
        if compat is None or version in compat:
            if info['stable'] or not stable:
                versions.append((version, info))
    if versions:
        return max(versions, key=lambda x: x[0])
