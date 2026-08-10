import json
import os
import subprocess
import tempfile
from multiprocessing import Pool

try:
    import tomllib
except ImportError:
    import tomli as tomllib

import juliapkg


def test_import():
    import juliapkg

    juliapkg.status
    juliapkg.add
    juliapkg.rm
    juliapkg.executable
    juliapkg.libjulia
    juliapkg.project
    juliapkg.offline
    juliapkg.require_julia


def test_resolve():
    assert juliapkg.resolve() is True


def resolve_in_tempdir(tempdir):
    subprocess.run(
        ["python", "-c", "import juliapkg; juliapkg.resolve()"],
        env=dict(os.environ, PYTHON_JULIAPKG_PROJECT=tempdir),
    )


def test_resolve_contention():
    with tempfile.TemporaryDirectory() as tempdir:
        with open(os.path.join(tempdir, "juliapkg.json"), "w") as f:
            f.write("""
{
"julia": "1",
"packages": {
"BenchmarkTools": {
    "uuid": "6e4b80f9-dd63-53aa-95a3-0cdb28fa8baf",
    "version": "1.5"
}
}
}
""")
        Pool(5).map(resolve_in_tempdir, [tempdir] * 5)


def test_resolve_preferences():
    with tempfile.TemporaryDirectory() as tempdir:
        # the default deps file for a project is <project>/pyjuliapkg/juliapkg.json
        depsdir = os.path.join(tempdir, "pyjuliapkg")
        os.makedirs(depsdir)
        with open(os.path.join(depsdir, "juliapkg.json"), "w") as f:
            f.write("""
{
"julia": "1",
"packages": {
"Example": {
    "uuid": "7876af07-990d-54b4-ab0e-23690620f79a",
    "version": "0.5",
    "preferences": {
        "use_jl_def": true,
        "greeting": "hello"
    }
}
}
}
""")
        subprocess.run(
            ["python", "-c", "import juliapkg; juliapkg.resolve()"],
            env=dict(os.environ, PYTHON_JULIAPKG_PROJECT=tempdir),
            check=True,
        )
        with open(os.path.join(tempdir, "Project.toml"), "rb") as f:
            proj = tomllib.load(f)
        assert proj["preferences"]["Example"] == {
            "use_jl_def": True,
            "greeting": "hello",
        }


EXAMPLE_UUID = "7876af07-990d-54b4-ab0e-23690620f79a"
CRAYONS_UUID = "a8cc5b0e-0ffa-5ad4-8c14-923d3ee1735f"


def _write_pins_project(tempdir, pinned_version):
    depsdir = os.path.join(tempdir, "pyjuliapkg")
    os.makedirs(depsdir)
    with open(os.path.join(depsdir, "juliapkg.json"), "w") as f:
        json.dump(
            {
                "julia": "1",
                "packages": {
                    "Example": {"uuid": EXAMPLE_UUID, "version": "0.5"},
                },
            },
            f,
        )
    with open(os.path.join(depsdir, "juliapkg.pinned.json"), "w") as f:
        json.dump(
            {
                "packages": {
                    "Example": {"uuid": EXAMPLE_UUID, "version": pinned_version},
                    "Crayons": {"uuid": CRAYONS_UUID, "version": "4.1.1"},
                }
            },
            f,
        )


def _manifest(tempdir):
    with open(os.path.join(tempdir, "Manifest.toml"), "rb") as f:
        manifest = tomllib.load(f)
    return manifest.get("deps", manifest)


def test_resolve_pinned():
    with tempfile.TemporaryDirectory() as tempdir:
        # Example is pinned to 0.5.4, which is not the latest 0.5.x
        _write_pins_project(tempdir, "0.5.4")
        subprocess.run(
            ["python", "-c", "import juliapkg; juliapkg.resolve()"],
            env=dict(os.environ, PYTHON_JULIAPKG_PROJECT=tempdir),
            check=True,
        )
        deps = _manifest(tempdir)
        assert deps["Example"][0]["version"] == "0.5.4"
        # pin-only packages are pruned again
        assert "Crayons" not in deps
        with open(os.path.join(tempdir, "Project.toml"), "rb") as f:
            proj = tomllib.load(f)
        assert "Crayons" not in proj["deps"]


def test_resolve_pinned_shared_preserves_user_deps():
    with tempfile.TemporaryDirectory() as tempdir:
        # a pre-existing user project with Crayons as a direct dependency, which
        # is also pinned; the pin cleanup must not remove it
        with open(os.path.join(tempdir, "Project.toml"), "w") as f:
            f.write(f'[deps]\nCrayons = "{CRAYONS_UUID}"\n')
        _write_pins_project(tempdir, "0.5.4")
        subprocess.run(
            ["python", "-c", "import juliapkg; juliapkg.resolve()"],
            env=dict(os.environ, PYTHON_JULIAPKG_PROJECT=tempdir),
            check=True,
        )
        with open(os.path.join(tempdir, "Project.toml"), "rb") as f:
            proj = tomllib.load(f)
        assert "Crayons" in proj["deps"]
        deps = _manifest(tempdir)
        assert deps["Crayons"][0]["version"] == "4.1.1"
        assert deps["Example"][0]["version"] == "0.5.4"


def test_resolve_pinned_relaxes_on_conflict():
    with tempfile.TemporaryDirectory() as tempdir:
        # the pin is incompatible with the required compat "0.5", so it gets
        # dropped with a warning and resolution proceeds
        _write_pins_project(tempdir, "0.4.1")
        subprocess.run(
            ["python", "-c", "import juliapkg; juliapkg.resolve()"],
            env=dict(os.environ, PYTHON_JULIAPKG_PROJECT=tempdir),
            check=True,
        )
        deps = _manifest(tempdir)
        assert deps["Example"][0]["version"].startswith("0.5.")


def test_resolve_pinned_strict_errors_on_conflict():
    with tempfile.TemporaryDirectory() as tempdir:
        _write_pins_project(tempdir, "0.4.1")
        proc = subprocess.run(
            ["python", "-c", "import juliapkg; juliapkg.resolve()"],
            env=dict(
                os.environ,
                PYTHON_JULIAPKG_PROJECT=tempdir,
                PYTHON_JULIAPKG_PINS="strict",
            ),
        )
        assert proc.returncode != 0


def test_freeze():
    with tempfile.TemporaryDirectory() as tempdir:
        depsdir = os.path.join(tempdir, "pyjuliapkg")
        os.makedirs(depsdir)
        with open(os.path.join(depsdir, "juliapkg.json"), "w") as f:
            json.dump(
                {
                    "julia": "1",
                    "packages": {
                        "Example": {"uuid": EXAMPLE_UUID, "version": "0.5"},
                    },
                },
                f,
            )
        subprocess.run(
            [
                "python",
                "-c",
                "import juliapkg; print(juliapkg.freeze())",
            ],
            env=dict(os.environ, PYTHON_JULIAPKG_PROJECT=tempdir),
            check=True,
        )
        with open(os.path.join(depsdir, "juliapkg.pinned.json")) as f:
            pins = json.load(f)
        assert pins["packages"]["Example"]["uuid"] == EXAMPLE_UUID
        assert pins["packages"]["Example"]["version"].startswith("0.5.")


def test_status():
    assert juliapkg.status() is None


def test_executable():
    exe = juliapkg.executable()
    assert isinstance(exe, str)
    assert os.path.isfile(exe)
    assert os.path.basename(exe).lower() in ("julia", "julia.exe")


def test_libjulia():
    lib = juliapkg.libjulia()
    assert isinstance(lib, str)
    assert os.path.isfile(lib)
    assert os.path.basename(lib).lower().startswith("libjulia.")


def test_project():
    proj = juliapkg.project()
    assert isinstance(proj, str)
    assert os.path.isdir(proj)
    assert os.path.isfile(os.path.join(proj, "Project.toml"))


def test_offline():
    offline = juliapkg.offline()
    assert isinstance(offline, bool)


def test_add_rm():
    with tempfile.TemporaryDirectory() as tdir:

        def deps():
            fn = os.path.join(tdir, "juliapkg.json")
            if not os.path.exists(fn):
                return None
            with open(os.path.join(tdir, "juliapkg.json")) as fp:
                return json.load(fp)

        assert deps() is None

        uuid1 = "00000000-0000-0000-0000-000000000001"
        uuid2 = "00000000-0000-0000-0000-000000000002"

        juliapkg.add(
            "Example1",
            target=tdir,
            uuid=uuid1,
        )

        assert deps() == {"packages": {"Example1": {"uuid": uuid1}}}

        juliapkg.add("Example2", target=tdir, uuid=uuid2)

        assert deps() == {
            "packages": {"Example1": {"uuid": uuid1}, "Example2": {"uuid": uuid2}}
        }

        juliapkg.require_julia("~1.5, 1.7", target=tdir)

        assert deps() == {
            "julia": "~1.5, ^1.7",
            "packages": {"Example1": {"uuid": uuid1}, "Example2": {"uuid": uuid2}},
        }

        juliapkg.require_julia(None, target=tdir)

        assert deps() == {
            "packages": {"Example1": {"uuid": uuid1}, "Example2": {"uuid": uuid2}}
        }

        juliapkg.rm("Example1", target=tdir)

        assert deps() == {"packages": {"Example2": {"uuid": uuid2}}}


def test_editable_setuptools():
    # test that editable deps files are found for setuptools packages
    fn = os.path.join(
        os.path.dirname(__file__),
        "juliapkg_test_editable_setuptools",
        "juliapkg_test_editable_setuptools",
        "juliapkg.json",
    )
    assert os.path.exists(fn)
    assert any(os.path.samefile(fn, x) for x in juliapkg.deps.deps_files())
