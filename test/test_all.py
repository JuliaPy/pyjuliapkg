import json
import os
import subprocess
import tempfile
from multiprocessing import Pool

import tomli

import juliapkg


def test_import():
    import juliapkg

    juliapkg.status
    juliapkg.add
    juliapkg.rm
    juliapkg.executable
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


def test_status():
    assert juliapkg.status() is None


def test_executable():
    exe = juliapkg.executable()
    assert isinstance(exe, str)
    assert os.path.isfile(exe)
    assert "julia" in exe.lower()


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
            # Try both TOML and JSON files
            toml_fn = os.path.join(tdir, "juliapkg.toml")
            json_fn = os.path.join(tdir, "juliapkg.json")

            if os.path.exists(toml_fn):
                with open(toml_fn, "rb") as fp:
                    return tomli.load(fp)
            elif os.path.exists(json_fn):
                with open(json_fn) as fp:
                    return json.load(fp)
            return None

        assert deps() is None

        # Test adding with default TOML
        juliapkg.add(
            "Example1",
            target=tdir,
            uuid="0001",
        )

        assert deps() == {"packages": {"Example1": {"uuid": "0001"}}}
        assert os.path.exists(os.path.join(tdir, "juliapkg.toml"))

        juliapkg.add("Example2", target=tdir, uuid="0002")

        assert deps() == {
            "packages": {"Example1": {"uuid": "0001"}, "Example2": {"uuid": "0002"}}
        }

        juliapkg.require_julia("~1.5, 1.7", target=tdir)

        assert deps() == {
            "julia": "~1.5, ^1.7",
            "packages": {"Example1": {"uuid": "0001"}, "Example2": {"uuid": "0002"}},
        }

        juliapkg.require_julia(None, target=tdir)

        assert deps() == {
            "packages": {"Example1": {"uuid": "0001"}, "Example2": {"uuid": "0002"}}
        }

        juliapkg.rm("Example1", target=tdir)

        assert deps() == {"packages": {"Example2": {"uuid": "0002"}}}

        # Verify JSON wasn't created
        assert not os.path.exists(os.path.join(tdir, "juliapkg.json"))


def test_json_fallback():
    with tempfile.TemporaryDirectory() as tdir:
        # Create a JSON file first
        json_fn = os.path.join(tdir, "juliapkg.json")
        with open(json_fn, "w") as fp:
            json.dump({"packages": {"Example1": {"uuid": "0001"}}}, fp)

        # Load should read from JSON
        deps = juliapkg.deps.load_cur_deps(target=tdir)
        assert deps == {"packages": {"Example1": {"uuid": "0001"}}}

        # Add should write to JSON since it exists
        juliapkg.add("Example2", target=tdir, uuid="0002")

        with open(json_fn) as fp:
            deps = json.load(fp)
        assert deps == {
            "packages": {"Example1": {"uuid": "0001"}, "Example2": {"uuid": "0002"}}
        }

        # Verify TOML wasn't created
        assert not os.path.exists(os.path.join(tdir, "juliapkg.toml"))
