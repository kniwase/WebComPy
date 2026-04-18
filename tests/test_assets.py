import pytest

from webcompy.assets import AssetNotFoundError, load_asset


class TestLoadAsset:
    def test_raises_when_no_registry(self, monkeypatch):
        import sys

        monkeypatch.delitem(sys.modules, "app._assets_registry", raising=False)
        with pytest.raises(AssetNotFoundError) as exc_info:
            load_asset("nonexistent")
        assert exc_info.value.key == "nonexistent"

    def test_raises_when_key_not_in_registry(self, monkeypatch):
        import types

        mod = types.ModuleType("app._assets_registry")
        mod._REGISTRY = {"existing": "app/existing.txt"}
        import sys

        monkeypatch.setitem(sys.modules, "app._assets_registry", mod)
        with pytest.raises(AssetNotFoundError) as exc_info:
            load_asset("missing")
        assert exc_info.value.key == "missing"


class TestAssetNotFoundError:
    def test_message(self):
        err = AssetNotFoundError("mykey")
        assert str(err) == "Asset not found: mykey"
        assert err.key == "mykey"
