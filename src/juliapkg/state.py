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
    project = os.getenv('JULIA_PROJECT')
    if project:
        if project == '@.':
            project = os.getcwd()
            while True:
                for fn in ['Project.toml', 'JuliaProject.toml']:
                    if os.path.exists(os.path.join(project, fn)):
                        STATE['project'] = project
                        break
                else:
                    project2 = os.path.dirname(project)
                    if project2 == project:
                        # TODO: actually here we should fall back to the defaut v#.# environment, not error
                        raise Exception('JULIA_PROJECT=@. but could not find the project directory')
                    project = project2
                    continue
                break
        else:
            STATE['project'] = project
    else:
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
    STATE['offline'] = os.getenv('PYTHON_JULIAPKG_OFFLINE', 'no').lower() == 'yes'

    # resolution
    STATE['resolved'] = False

reset_state()
