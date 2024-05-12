import os

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


def test_add():
    pass


def test_rm():
    pass


def test_require_julia():
    pass
