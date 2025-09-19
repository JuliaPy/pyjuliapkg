# JuliaPkg

[![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)
[![Tests](https://github.com/JuliaPy/pyjuliapkg/actions/workflows/tests.yml/badge.svg)](https://github.com/JuliaPy/pyjuliapkg/actions/workflows/tests.yml)
[![Codecov](https://codecov.io/gh/JuliaPy/pyjuliapkg/branch/main/graph/badge.svg?token=A813UUIHGS)](https://codecov.io/gh/JuliaPy/pyjuliapkg)

Do you want to use [Julia](https://julialang.org/) in your Python script/project/package?
No problem! JuliaPkg will help you out!
- Declare the version of Julia you require in a `juliapkg.json` file.
- Add any packages you need too.
- Call `juliapkg.resolve()` et voila, your dependencies are there.
- Use `juliapkg.executable()` to find the Julia executable and `juliapkg.project()` to
  find the project where the packages were installed.
- Virtual environments? PipEnv? Poetry? Conda? No problem! JuliaPkg will set up a
  different project for each environment you work in, keeping your dependencies isolated.

## Install

```sh
pip install juliapkg
```

## Declare dependencies

### Functional interface

- `status(target=None)` shows the status of dependencies.
- `require_julia(version, target=None)` declares that you require the given version of
  Julia. The `version` is a Julia compat specifier, so `1.5` matches any `1.*.*` version at
  least `1.5`.
- `add(pkg, uuid=None, dev=False, version=None, path=None, subdir=None, url=None, rev=None, target=None)`
  adds a required package.
- `rm(pkg, target=None)` remove a package.

Note that these functions edit `juliapkg.json` but do not actually install anything until
`resolve()` is called, which happens automatically in `executable()` and `project()`.

The `target` specifies the `juliapkg.json` file to edit, or the directory containing it.
If not given, it will be your virtual environment or Conda environment if you are using one,
otherwise `~/.pyjuliapkg.json`.

### juliapkg.json

You can also edit `juliapkg.json` directly if you like. Here is an example which requires
Julia v1.*.* and the Example package v0.5.*:
```json
{
    "julia": "1",
    "packages": {
        "Example": {
            "uuid": "7876af07-990d-54b4-ab0e-23690620f79a",
            "version": "0.5"
        }
    }
}
```

### Command line interface

You can also use the CLI, some examples:
```sh
python -m juliapkg --help
python -m juliapkg add Example --version=0.5
python -m juliapkg resolve
python -m juliapkg status
python -m juliapkg run -E 'using Example; Example.hello("world")'
python -m juliapkg remove Example
```

## Using Julia

- `juliapkg.executable()` returns a compatible Julia executable.
- `juliapkg.project()` returns the project into which the packages have been installed.
- `juliapkg.resolve(force=False, dry_run=False)` ensures all the dependencies are installed. You don't
  normally need to do this because the other functions resolve automatically.
- `juliapkg.update(dry_run=False)` updates the dependencies.

## Details

### Configuration

JuliaPkg does not generally need configuring, but for advanced usage the following options
are available. Options can be specified either as an environment variable or as an `-X`
option to `python`. The `-X` option has higher precedence.

| Environment Variable | `-X` Option | Description |
| --- | --- | --- |
| `PYTHON_JULIAPKG_EXE=<exe>` | `-X juliapkg-exe=<exe>` | The Julia executable to use. |
| `PYTHON_JULIAPKG_PROJECT=<project>` | `-X juliapkg-project=<project>` | The Julia project where packages are installed. |
| `PYTHON_JULIAPKG_OFFLINE=<yes/no>` | `-X juliapkg-offline=<yes/no>` | Work in Offline Mode - does not install Julia or any packages. |

### Which Julia gets used?

JuliaPkg tries the following strategies in order to find Julia on your system:
- If the `-X juliapkg-exe` argument to `python` is set, that is used.
- If the environment variable `PYTHON_JULIAPKG_EXE` is set, that is used.
- If `julia` is in your `PATH`, and is compatible, that is used.
- If [`juliaup`](https://github.com/JuliaLang/juliaup) is in your `PATH`, it is used to install a compatible version of Julia.
- Otherwise, JuliaPkg downloads a compatible version of Julia and installs it into the
  Julia project.

More strategies may be added in a future release.

### Where are Julia packages installed?

JuliaPkg installs packages into a project whose location is determined by trying the
following strategies in order:
- If the `-X juliapkg-project` argument to `python` is set, that is used.
- If the environment variable `PYTHON_JULIAPKG_PROJECT` is set, that is used.
- If you are in a Python virtual environment or Conda environment, then `{env}/julia_env`
  subdirectory is used.
- Otherwise `~/.julia/environments/pyjuliapkg` is used (respects `JULIA_DEPOT`).

More strategies may be added in a future release.

If the project is explicitly specified (with `-X juliapkg-project` or
`PYTHON_JULIAPKG_PROJECT`) then it is considered "shared" and dependencies will only
ever be added, not removed.

### Adding Julia dependencies to Python packages

JuliaPkg looks for `juliapkg.json` files in many locations, namely:
- `{project}/pyjuliapkg` where project is as above (depending on your environment).
- Every installed package (looks through `sys.path` and `sys.meta_path`).

The last point means that if you put a `juliapkg.json` file in a package, then install that
package, then JuliaPkg will find those dependencies and install them.

You can use `add`, `rm` etc. above with `target='/path/to/your/package'` to modify the
dependencies of your package.

### Offline mode

If you set the environment variable `PYTHON_JULIAPKG_OFFLINE=yes` (or call `python` with the
option `-X juliapkg-offline=yes`) then JuliaPkg will operate in offline mode. This means it
will not attempt to download Julia or any packages.

Resolving will fail if Julia is not already installed. It is up to you to install any
required Julia packages.
