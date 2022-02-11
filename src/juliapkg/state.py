import os

STATE = {}

def reset_state():
    global STATE
    STATE = {}

    # Are we running a dev version?
    STATE['dev'] = os.path.exists(os.path.join(os.path.dirname(__file__), '..', '..', 'pyproject.toml'))

    # Find the Julia depot
    depot_path = os.getenv('JULIA_DEPOT_PATH')
    if depot_path:
        sep = ';' if os.name == 'nt' else ':'
        STATE['depot'] = os.path.abspath(depot_path.split(sep)[0])
    else:
        STATE['depot'] = os.path.abspath(os.path.join(os.path.expanduser('~'), '.julia'))

    # Determine where to put the julia environment
    # TODO: Can we more direcly figure out the environment from which python was called? Maybe find the first PATH entry containing python?
    vprefix = os.getenv('VIRTUAL_ENV')
    cprefix = os.getenv('CONDA_PREFIX')
    if cprefix and vprefix:
        raise Exception('You are using both a virtual and conda environment, cannot figure out which to use!')
    elif cprefix:
        prefix = cprefix
    elif vprefix:
        prefix = vprefix
    else:
        prefix = None
    STATE['prefix'] = prefix
    if prefix is None:
        STATE['project'] = os.path.join(STATE['depot'], 'environments', 'pyjuliapkg')
    else:
        STATE['project'] = os.path.abspath(os.path.join(prefix, 'julia_env'))

    # meta file
    STATE['meta'] = os.path.join(STATE['project'], 'pyjuliapkgmeta.json')
    STATE['install'] = os.path.join(STATE['project'], 'install')

    # resolution
    STATE['resolved'] = False

reset_state()
