import os
import sys
import subprocess

def run(*args: str):
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
        if arg.startswith("--project"):
            raise ValueError("Do not specify --project when using pyjuliapkg.")
        cmd.append(arg)
    subprocess.run(
        cmd,
        check=True,
        env=env,
    )
