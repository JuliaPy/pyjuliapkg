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
    import juliapkg

    juliapkg.resolve()
