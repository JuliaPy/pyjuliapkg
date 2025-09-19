import os
import tarfile

# we can switch to tomllib when we require python 3.11+
import tomli


def _find_registries():
    depots = os.environ.get("JULIA_DEPOT_PATH", "").split(os.pathsep)
    depots.append(os.path.join(os.path.expanduser("~"), ".julia"))
    registries = []
    for depot in depots:
        if not depot:
            continue
        regdir = os.path.join(depot, "registries")
        for fn in os.listdir(regdir):
            if fn.endswith(".toml"):
                regmetafile = os.path.join(regdir, fn)
                with open(regmetafile, "rb") as fp:
                    regmeta = tomli.load(fp)
                regmeta["path"] = os.path.join(regdir, regmeta["path"])
                registries.append(regmeta)
    return registries


_REGISTRY_INDEX_CACHE = {}


def _load_registry_index(reg):
    # look it up in the cache
    reghash = reg["git-tree-sha1"]
    regidx = _REGISTRY_INDEX_CACHE.get(reghash, None)
    if regidx is not None:
        return regidx
    # cache miss, do some parsing
    regpath = reg["path"]
    if not os.path.exists(regpath):
        raise ValueError(f"registry does not exist: {regpath}")
    if regpath.endswith(".tar.gz"):
        with tarfile.open(regpath) as reg:
            regidx = tomli.load(reg.extractfile("Registry.toml"))
    elif os.path.isdir(regpath):
        with open(os.path.join(regpath, "Registry.toml"), "rb") as fp:
            regidx = tomli.load(fp)
    else:
        raise ValueError(f"unsupported registry type: {regpath}")
    _REGISTRY_INDEX_CACHE[reghash] = regidx
    return regidx


def _find_uuid(pkgname):
    uuids = {}
    for reg in _find_registries():
        regpath = reg["path"]
        if not os.path.exists(regpath):
            continue
        regidx = _load_registry_index(reg)
        for uuid, info in regidx["packages"].items():
            if info["name"] != pkgname:
                continue
            uuids.setdefault(uuid, []).append(regpath)
    return uuids
