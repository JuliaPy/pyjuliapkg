import os
import sys
from subprocess import run as _run

def run(*args):
    from .deps import STATE, resolve

    resolve()
    executable = STATE["executable"]
    project = STATE["project"]

    env = os.environ.copy()
    if sys.executable:
        # NOTE: this is from deps/run_julia.py
        # prefer PythonCall to use the current Python executable
        # TODO: this is a hack, it would be better for PythonCall to detect that
        #   Julia is being called from Python
        env.setdefault("JULIA_PYTHONCALL_EXE", sys.executable)
    cmd = [
        executable,
        "--project=" + project,
    ]
    for arg in args:
        cmd.append(arg)
    _run(
        cmd,
        check=True,
        env=env,
    )
