import os
import sys

STATE = {}

def get_config(name, default=None):
    # -X option
    key = 'juliapkg-' + name.lower().replace('_', '-')
    value = sys._xoptions.get(key)
    if value is not None:
        return value, f'-X {key}'
    # environment variable
    key = 'PYTHON_JULIAPKG_' + name.upper()
    value = os.getenv(key)
    if value is not None:
        return value, key
    # fallback
    return default, f'<default for option {name}>'

def get_config_opts(name, opts, default=None):
    value, key = get_config(name)
    if value in opts:
        if isinstance(opts, dict):
            value = opts[value]
        return value, key
    elif value is None:
        return default, key
    else:
        opts_str = ', '.join(x for x in opts if isinstance(x, str))
        raise ValueError(f'{key} must be one of: {opts_str}')

def get_config_bool(name, default=False):
    return get_config_opts(name, {'yes': True, True: True, 'no': False, False: False}, default)

def reset_state():
    global STATE
    STATE = {}

    # Are we running a dev version?
    STATE['dev'] = os.path.exists(os.path.join(os.path.dirname(__file__), '..', '..', 'pyproject.toml'))

    # Overrides
    STATE['override_executable'], _ = get_config('exe')

    # Find the Julia depot
    depot_path = os.getenv('JULIA_DEPOT_PATH')
    if depot_path:
        sep = ';' if os.name == 'nt' else ':'
        STATE['depot'] = os.path.abspath(depot_path.split(sep)[0])
    else:
        STATE['depot'] = os.path.abspath(os.path.join(os.path.expanduser('~'), '.julia'))

    # Determine where to put the julia environment
    # TODO: Can we more direcly figure out the environment from which python was called? Maybe find the first PATH entry containing python?
    project, project_key = get_config('project')
    if project:
        if not os.path.isabs(project):
            raise Exception(f'{project_key} must be an absolute path')
        STATE['project'] = project
    else:
        vprefix = sys.prefix if sys.prefix != sys.base_prefix else None
        cprefix = os.getenv('CONDA_PREFIX')
        if cprefix and vprefix:
            raise Exception('You are using both a virtual and conda environment, cannot figure out which to use!')
        elif cprefix:
            prefix = cprefix
        elif vprefix:
            prefix = vprefix
        else:
            prefix = None
        if prefix is None:
            STATE['project'] = os.path.join(STATE['depot'], 'environments', 'pyjuliapkg')
        else:
            STATE['project'] = os.path.abspath(os.path.join(prefix, 'julia_env'))

    # meta file
    STATE['prefix'] = os.path.join(STATE['project'], 'pyjuliapkg')
    STATE['deps'] = os.path.join(STATE['prefix'], 'juliapkg.json')
    STATE['meta'] = os.path.join(STATE['prefix'], 'meta.json')
    STATE['install'] = os.path.join(STATE['prefix'], 'install')

    # offline
    STATE['offline'], _ = get_config_bool('offline')

    # resolution
    STATE['resolved'] = False

reset_state()
