import io
import sys
import tarfile

import pytest

from juliapkg import registry


@pytest.fixture(autouse=True)
def clear_registry_cache(monkeypatch):
    monkeypatch.setattr(registry, "_REGISTRY_INDEX_CACHE", {})


@pytest.mark.parametrize("compression", ["gz", "zst"])
def test_load_registry_index(tmp_path, compression):
    archive = tarfile
    if compression == "zst" and sys.version_info < (3, 14):
        archive = pytest.importorskip("backports.zstd.tarfile")
    path = tmp_path / f"registry.tar.{compression}"
    content = b'[packages]\nexample-uuid = {name = "Example"}\n'
    with archive.open(path, f"w:{compression}") as tar:
        info = archive.TarInfo("Registry.toml")
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
    assert registry._load_registry_index(
        {"path": str(path), "git-tree-sha1": "example"}
    ) == {"packages": {"example-uuid": {"name": "Example"}}}


def test_missing_backport(tmp_path, monkeypatch):
    monkeypatch.setattr(registry.sys, "version_info", (3, 13))
    monkeypatch.setitem(sys.modules, "backports.zstd", None)
    path = tmp_path / "registry.tar.zst"
    path.touch()
    with pytest.raises(ImportError, match=r"juliapkg\[zstd\]"):
        registry._load_registry_index({"path": str(path), "git-tree-sha1": "example"})


def test_invalid_registry_is_not_skipped(tmp_path, monkeypatch):
    bad = tmp_path / "bad.tar.gz"
    bad.write_bytes(b"invalid archive")
    good = tmp_path / "good"
    good.mkdir()
    (good / "Registry.toml").write_text('[packages]\nexample = {name = "Example"}')
    monkeypatch.setattr(
        registry,
        "_find_registries",
        lambda: [
            {"path": str(bad), "git-tree-sha1": "bad"},
            {"path": str(good), "git-tree-sha1": "good"},
        ],
    )
    with pytest.raises(tarfile.ReadError):
        registry._find_uuid("Example")
