import json
import os
import subprocess
import tempfile
from multiprocessing import Pool

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
