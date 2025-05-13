import juliapkg


def test_openssl_compat():
    assert juliapkg.deps.openssl_compat((1, 2, 3)) == "1.2 - 1.2.3"
    assert juliapkg.deps.openssl_compat((2, 3, 4)) == "2.3 - 2.3.4"
    assert juliapkg.deps.openssl_compat((3, 0, 0)) == "3 - 3.0"
    assert juliapkg.deps.openssl_compat((3, 1, 0)) == "3 - 3.1"
    assert juliapkg.deps.openssl_compat((3, 1, 2)) == "3 - 3.1"
    assert isinstance(juliapkg.deps.openssl_compat(), str)
