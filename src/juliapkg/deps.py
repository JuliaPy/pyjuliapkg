import json
import logging
import os
import sys
import time
# https://github.com/hukkin/tomli#building-a-tomlitomllib-compatibility-layer
try:
        import tomllib
except ModuleNotFoundError:
        import tomli as tomllib
import tomli_w

from subprocess import run

from .compat import Compat, Version
from .state import STATE
from .find_julia import julia_version, find_julia
from .install_julia import log

logger = logging.getLogger('juliapkg')

### META

META_VERSION = 2  # increment whenever the format changes

def load_meta():
    fn = STATE['meta']
    if os.path.exists(fn):
        with open(fn) as fp:
            meta = json.load(fp)
            if meta.get('meta_version') == META_VERSION:
                return meta

def save_meta(meta):
    assert isinstance(meta, dict)
    assert meta.get('meta_version') == META_VERSION
    fn = STATE['meta']
    os.makedirs(os.path.dirname(fn), exist_ok=True)
    with open(fn, 'w') as fp:
        json.dump(meta, fp)

### RESOLVE

class PkgSpec:
    def __init__(self, name, uuid, dev=False, version=None, path=None, url=None, rev=None):
        self.name = name
        self.uuid = uuid
        self.dev = dev
        self.version = version
        self.path = path
        self.url = url
        self.rev = rev

    def jlstr(self):
        args = ['name="{}"'.format(self.name), 'uuid="{}"'.format(self.uuid)]
        if self.path is not None:
            args.append('path=raw"{}"'.format(self.path))
        if self.url is not None:
            args.append('url=raw"{}"'.format(self.url))
        if self.rev is not None:
            args.append('rev=raw"{}"'.format(self.rev))
        return "Pkg.PackageSpec({})".format(', '.join(args))

    def dict(self):
        ans = {
            "name": self.name,
            "uuid": self.uuid,
            "dev": self.dev,
            "version": str(self.version),
            "path": self.path,
            "url": self.url,
            "rev": self.rev,
        }
        return {k:v for (k,v) in ans.items() if v is not None}

    def depsdict(self):
        ans = {}
        ans['uuid'] = self.uuid
        if self.dev:
            ans['dev'] = self.dev
        if self.version is not None:
            ans['version'] = str(self.version)
        if self.path is not None:
            ans['path'] = self.path
        if self.url is not None:
            ans['url'] = self.url
        if self.rev is not None:
            ans['rev'] = self.rev
        return ans

def can_skip_resolve():
    # resolve if we haven't resolved before
    deps = load_meta()
    if deps is None:
        logger.debug('no meta file')
        return False
    # resolve whenever Julia changes
    exe = deps["executable"]
    ver = deps["version"]
    exever = julia_version(exe)
    if exever is None or ver != str(exever):
        logger.debug('changed version %s to %s', ver, exever)
        return False
    # resolve when going from offline to online
    offline = deps['offline']
    if offline and not STATE['offline']:
        logger.debug('was offline now online')
        return False
    # resolve whenever swapping between dev/not dev
    isdev = deps['dev']
    if isdev != STATE["dev"]:
        logger.debug('changed dev %s to %s', isdev, STATE['dev'])
        return False
    # resolve whenever anything in sys.path changes
    timestamp = deps["timestamp"]
    timestamp = max(os.path.getmtime(STATE["meta"]), timestamp)
    sys_path = deps["sys_path"]
    if sys_path != sys.path:
        logger.debug('sys.path changed %s to %s', sys_path, sys.path)
        return False
    for path in sys.path:
        here = not path
        if here:
            path = os.getcwd()
        if not os.path.exists(path):
            continue
        if (not here) and (os.path.getmtime(path) > timestamp):
            logger.debug('directory changed %r', path)
            return False
        if os.path.isdir(path):
            fn = os.path.join(path, "juliapkg.json")
            if os.path.exists(fn) and os.path.getmtime(fn) > timestamp:
                logger.debug('file changed %r', fn)
                return False
    return deps

def deps_files():
    ans = []
    # the default deps file
    ans.append(cur_deps_file())
    # look in sys.path
    for path in sys.path:
        if not path:
            path = os.getcwd()
        if not os.path.isdir(path):
            continue
        fn = os.path.join(path, "juliapkg.json")
        ans.append(fn)
        for subdir in os.listdir(path):
            fn = os.path.join(path, subdir, "juliapkg.json")
            ans.append(fn)
    return list(set(os.path.normcase(os.path.normpath(os.path.abspath(fn))) for fn in ans if os.path.isfile(fn)))

def required_packages():
    # read all dependencies into a dict: name -> key -> file -> value
    import json
    all_deps = {}
    for fn in deps_files():
        with open(fn) as fp:
            deps = json.load(fp)
        for (name, kvs) in deps.get("packages", {}).items():
            dep = all_deps.setdefault(name, {})
            for (k, v) in kvs.items():
                if k == 'path':
                    # resolve paths relative to the directory containing the file
                    v = os.path.normcase(os.path.normpath(os.path.join(os.path.dirname(fn), v)))
                dep.setdefault(k, {})[fn] = v
    # merges non-unique values
    def merge_unique(dep, kfvs, k):
        fvs = kfvs.pop(k, None)
        if fvs is not None:
            vs = set(fvs.values())
            if len(vs) == 1:
                dep[k], = vs
            elif vs:
                raise Exception("'{}' entries are not unique:\n{}".format(k, '\n'.join(['- {!r} at {}'.format(v,f) for (f,v) in fvs.items()])))
    # merges compat entries
    def merge_compat(dep, kfvs, k):
        fvs = kfvs.pop(k, None)
        if fvs is not None:
            compats = list(map(Compat.parse, fvs.values()))
            compat = compats[0]
            for c in compats[1:]:
                compat &= c
            if not compat:
                raise Exception("'{}' entries have empty intersection:\n{}".format(k, '\n'.join(['- {!r} at {}'.format(v,f) for (f,v) in fvs.items()])))
            else:
                dep[k] = str(compat)
    # merges booleans with any
    def merge_any(dep, kfvs, k):
        fvs = kfvs.pop(k, None)
        if fvs is not None:
            dep[k] = any(fvs.values())
    # merge dependencies: name -> key -> value
    deps = []
    for (name, kfvs) in all_deps.items():
        kw = {'name': name}
        merge_unique(kw, kfvs, 'uuid')
        merge_unique(kw, kfvs, 'path')
        merge_unique(kw, kfvs, 'url')
        merge_unique(kw, kfvs, 'rev')
        merge_compat(kw, kfvs, 'version')
        merge_any(kw, kfvs, 'dev')
        deps.append(PkgSpec(**kw))
    return deps

def required_julia():
    import json
    compats = {}
    for fn in deps_files():
        with open(fn) as fp:
            deps = json.load(fp)
            c = deps.get("julia")
            if c is not None:
                compats[fn] = Compat.parse(c)
    compat = None
    for c in compats.values():
        if compat is None:
            compat = c
        else:
            compat &= c
    if compat is not None and not compat:
        raise Exception("'julia' compat entries have empty intersection:\n{}".format('\n'.join(['- {!r} at {}'.format(v,f) for (f,v) in compats.items()])))
    return compat

def resolve(force=False, dry_run=False):
    # see if we can skip resolving
    if not force:
        if STATE['resolved']:
            return True
        deps = can_skip_resolve()
        if deps:
            STATE['resolved'] = True
            STATE['executable'] = deps['executable']
            STATE['version'] = Version(deps['version'])
            return True
    if dry_run:
        return False
    STATE['resolved'] = False
    # get julia compat
    compat = required_julia()
    # get required packages
    pkgs = required_packages()
    # find a compatible julia executable
    log(f'Locating Julia{"" if compat is None else " "+str(compat)}')
    exe, ver = find_julia(compat=compat, prefix=STATE['install'], install=True, upgrade=True)
    log(f'Using Julia {ver} at {exe}')
    # set up the project
    project = STATE['project']
    log(f'Using Julia project at {project}')
    os.makedirs(project, exist_ok=True)
    if not STATE['offline']:
        if os.getenv("PYTHON_JULIAPKG_MERGE_PROJECT", default=False):
            log(f"Merging found Julia dependencies into Julia project at {project}")
            # Read in the existing Project.toml
            try:
                with open(os.path.join(project, "Project.toml"), "rb") as fp:
                    p1toml = tomllib.load(fp)
            except FileNotFoundError:
                # Existing Project.toml doesn't exist, so create an empty dictionary.
                p1toml = {"deps": {}, "compat": {}}

            # Make sure everything in the existing Project.toml is compatible with the Julia packages juliapkg found.
            for pkg in pkgs:
                if pkg.name in p1toml["deps"].keys():
                    # pkg is a Julia dependency that already exists in the Julia project.
                    # Check that the UUIDs match.
                    assert pkg.uuid == p1toml["deps"][pkg.name]

                    if (pkg.name in p1toml["compat"].keys()) and pkg.version:
                        # So, if there's an existing [compat] entry for the current package, merge them.
                        compat1 = p1toml["compat"][pkg.name]
                        version_merged = str(Compat.parse(pkg.version) & Compat.parse(compat1))
                        if version_merged:
                            p1toml["compat"][pkg.name] = version_merged
                        else:
                            raise(Exception(f'empty intersection between dep {pkg.name} {compat1} found in {os.path.join(project, "Project.toml")} and {pkg.name} {pkg.version} found by juliapkg'))
                    elif pkg.version:
                        # There's a compat for the new Julia dependency found by juliapkg, but not one in the exsting Project.toml, so just use the new one.
                        p1toml["compat"][pkg.name] = pkg.version

                else:
                    # New Julia dependency, so add it.
                    p1toml["deps"][pkg.name] = pkg.uuid
                    if pkg.version:
                        p1toml["compat"][pkg.name] = pkg.version

            # Write out the new Project.toml.
            with open(os.path.join(project, "Project.toml"), "wb") as fp:
                tomli_w.dump(p1toml, fp)

        else:
            # write a Project.toml specifying UUIDs and compatibility of required packages
            with open(os.path.join(project, "Project.toml"), "wt") as fp:
                print('[deps]', file=fp)
                for pkg in pkgs:
                    print(f'{pkg.name} = "{pkg.uuid}"', file=fp)
                print(file=fp)
                print('[compat]', file=fp)
                for pkg in pkgs:
                    if pkg.version:
                        print(f'{pkg.name} = "{pkg.version}"', file=fp)
                print(file=fp)
            # remove Manifest.toml
            manifest_path = os.path.join(project, "Manifest.toml")
            if os.path.exists(manifest_path):
                os.remove(manifest_path)
        # install the packages
        dev_pkgs = ', '.join([pkg.jlstr() for pkg in pkgs if pkg.dev])
        add_pkgs = ', '.join([pkg.jlstr() for pkg in pkgs if not pkg.dev])
        script = ['import Pkg']
        if dev_pkgs:
            script.append(f'Pkg.develop([{dev_pkgs}])')
        if add_pkgs:
            script.append(f'Pkg.add([{add_pkgs}])')
        script.append('Pkg.resolve()')
        log(f'Installing packages:')
        for line in script:
            log('julia>', line, cont=True)
        run([exe, '--project='+project, '--startup-file=no', '-e', '; '.join(script)], check=True)
    # record that we resolved
    save_meta({
        "meta_version": META_VERSION,
        "dev": STATE["dev"],
        "version": str(ver),
        "executable": exe,
        "timestamp": time.time(),
        "sys_path": sys.path,
        "pkgs": [pkg.dict() for pkg in pkgs],
        "offline": bool(STATE['offline']),
    })
    STATE['resolved'] = True
    STATE['executable'] = exe
    STATE['version'] = ver
    return True

def executable():
    resolve()
    return STATE['executable']

def project():
    resolve()
    return STATE['project']

def cur_deps_file(target=None):
    if target is None:
        return STATE['deps']
    elif os.path.isdir(target):
        return os.path.abspath(os.path.join(target, 'juliapkg.json'))
    elif os.path.isfile(target) or (os.path.isdir(os.path.dirname(target)) and not os.path.exists(target)):
        return os.path.abspath(target)
    else:
        raise ValueError('target must be an existing directory, or a file name in an existing directory')

def load_cur_deps(target=None):
    fn = cur_deps_file(target=target)
    if os.path.exists(fn):
        with open(fn) as fp:
            deps = json.load(fp)
    else:
        deps = {}
    return deps

def write_cur_deps(deps, target=None):
    fn = cur_deps_file(target=target)
    if deps:
        os.makedirs(os.path.dirname(fn), exist_ok=True)
        with open(fn, 'w') as fp:
            json.dump(deps, fp)
    else:
        if os.path.exists(fn):
            os.remove(fn)

def status(target=None):
    res = resolve(dry_run=True)
    print('JuliaPkg Status')
    fn = cur_deps_file(target=target)
    if os.path.exists(fn):
        with open(fn) as fp:
            deps = json.load(fp)
    else:
        deps = {}
    st = '' if deps else ' (empty project)'
    print(f'{fn}{st}')
    if res:
        exe = STATE['executable']
        ver = STATE['version']
    else:
        print('Not resolved (resolve for more information)')
    jl = deps.get('julia')
    if res or jl:
        print('Julia', end='')
        if res:
            print(f' {ver}', end='')
        if jl:
            print(f' ({jl})', end='')
        if res:
            print(f' @ {exe}', end='')
        print()
    pkgs = deps.get('packages')
    if pkgs:
        print(f'Packages:')
        for (name, info) in pkgs.items():
            print(f'  {name}: {info}')

def require_julia(compat, target=None):
    deps = load_cur_deps(target=target)
    if compat is None:
        if 'julia' in deps:
            del deps['julia']
    else:
        if isinstance(compat, str):
            compat = Compat.parse(compat)
        elif not isinstance(compat, Compat):
            raise TypeError
        deps['julia'] = str(compat)
    write_cur_deps(deps, target=target)
    STATE['resolved'] = False

def add(pkg, *args, target=None, **kwargs):
    deps = load_cur_deps(target=target)
    _add(deps, pkg, *args, **kwargs)
    write_cur_deps(deps, target=target)
    STATE['resolved'] = False

def _add(deps, pkg, uuid=None, **kwargs):
    if isinstance(pkg, PkgSpec):
        pkgs = deps.setdefault('packages', {})
        pkgs[pkg.name] = pkg.depsdict()
    elif isinstance(pkg, str):
        if uuid is None:
            raise TypeError('uuid is required')
        pkg = PkgSpec(pkg, uuid, **kwargs)
        _add(deps, pkg)
    else:
        for p in pkg:
            _add(deps, p)

def rm(pkg, target=None):
    deps = load_cur_deps(target=target)
    _rm(deps, pkg)
    write_cur_deps(deps, target=target)
    STATE['resolved'] = False

def _rm(deps, pkg):
    if isinstance(pkg, PkgSpec):
        _rm(deps, pkg.name)
    elif isinstance(pkg, str):
        pkgs = deps.setdefault('packages', {})
        if pkg in pkgs:
            del pkgs[pkg]
        if not pkgs:
            del deps['packages']
    else:
        for p in pkg:
            _rm(deps, p)

def offline(value=True):
    if value is not None:
        STATE['offline'] = value
    if value:
        STATE['resolved'] = False
    return STATE['offline']
