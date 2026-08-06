"""Tests for use_local_storage() / use_session_storage() composables."""

import logging as std_logging
import warnings
from typing import Any

import pytest

import webcompy.storage._composable as storage_composable
from webcompy import use_local_storage, use_session_storage
from webcompy.components import define_component
from webcompy.components._context_manager import ComponentRenderState, component_context
from webcompy.signal import Signal
from webcompy.signal._effect import EffectScope
from webcompy.template import render_template
from webcompy_testing import TestRenderer


class FakeStorage:
    def __init__(self, initial: dict[str, str] | None = None, *, fail_on_set: bool = False) -> None:
        self._data: dict[str, str] = dict(initial or {})
        self._fail_on_set = fail_on_set
        self.set_calls: list[tuple[str, str]] = []

    def getItem(self, key: str) -> Any:
        return self._data.get(key)

    def setItem(self, key: str, value: str) -> None:
        if self._fail_on_set:
            raise RuntimeError("quota exceeded")
        self.set_calls.append((key, value))
        self._data[key] = value


class FakeCtx:
    def __init__(self, name: str = "TestComp") -> None:
        self._component_name = name
        self._transferable_signals: dict = {}


def make_state(component_name: str = "TestComp") -> ComponentRenderState:
    return ComponentRenderState(
        context=FakeCtx(component_name),
        effect_scope=EffectScope(),
        framework_cleanup=lambda: None,
    )


class TestReadWriteHelpers:
    def test_round_trip(self):
        fake = FakeStorage()
        sig = storage_composable._make("k", 0, fake)
        assert sig.value == 0
        sig.value = 5
        assert fake.getItem("k") == "5"
        sig2 = storage_composable._make("k", 0, fake)
        assert sig2.value == 5

    def test_missing_key_uses_default_value(self):
        sig = storage_composable._make("theme", "light", FakeStorage())
        assert sig.value == "light"

    def test_missing_key_with_js_null_proxy(self, monkeypatch):
        class NullProxy:
            pass

        fake = FakeStorage()
        monkeypatch.setattr(storage_composable, "ENVIRONMENT", "pyscript")
        monkeypatch.setattr(storage_composable, "_pyscript_ffi_is_none", lambda raw: isinstance(raw, NullProxy))

        def getitem(key):
            return NullProxy() if key not in fake._data else fake._data[key]

        monkeypatch.setattr(fake, "getItem", getitem)
        sig = storage_composable._make("missing", "fallback", fake)
        assert sig.value == "fallback"

    def test_is_missing_helpers(self, monkeypatch):
        assert storage_composable._is_missing(None) is True
        assert storage_composable._is_missing("x") is False
        monkeypatch.setattr(storage_composable, "ENVIRONMENT", "pyscript")
        monkeypatch.setattr(storage_composable, "_pyscript_ffi_is_none", lambda raw: raw == "jsnull")
        assert storage_composable._is_missing("jsnull") is True
        assert storage_composable._is_missing("x") is False

    def test_missing_key_uses_default_factory(self):
        calls: list = []

        def factory() -> int:
            calls.append("called")
            return 42

        sig = storage_composable._make("missing", factory, FakeStorage())
        assert sig.value == 42
        assert calls == ["called"]

    def test_stored_null_is_legitimate_value(self):
        fake = FakeStorage({"k": "null"})
        sig = storage_composable._make("k", "fallback", fake)
        assert sig.value is None

    def test_corrupted_json_warns_and_uses_default(self, caplog):
        fake = FakeStorage({"settings": "{not json"})
        with caplog.at_level(std_logging.WARNING, logger="uvicorn"):
            sig = storage_composable._make("settings", lambda: {}, fake)
        assert sig.value == {}
        assert any("corrupted" in r.message for r in caplog.records)
        assert fake.getItem("settings") == "{not json"

    def test_non_serializable_value_warns_and_skips_write(self, caplog):
        fake = FakeStorage()
        sig = storage_composable._make("data", None, fake)
        with caplog.at_level(std_logging.WARNING, logger="uvicorn"):
            sig.value = object()
        assert any("not JSON-serializable" in r.message for r in caplog.records)
        assert fake.set_calls == []
        assert isinstance(sig.value, object)

    def test_setitem_failure_swallowed(self, caplog):
        fake = FakeStorage(fail_on_set=True)
        sig = storage_composable._make("k", 0, fake)
        with caplog.at_level(std_logging.WARNING, logger="uvicorn"):
            sig.value = 1
        assert any("failed to write" in r.message for r in caplog.records)
        assert sig.value == 1

    def test_same_value_set_does_not_write(self):
        fake = FakeStorage()
        sig = storage_composable._make("k", 1, fake)
        sig.value = 1
        assert fake.set_calls == []

    def test_write_back_uses_stored_value_on_read(self):
        fake = FakeStorage({"k": '{"nested": [1, 2]}'})
        sig = storage_composable._make("k", None, fake)
        assert sig.value == {"nested": [1, 2]}


class TestServerPath:
    def test_returns_signal_with_default_value(self):
        sig = use_local_storage("theme", "light")
        assert isinstance(sig, Signal)
        assert sig.value == "light"

    def test_returns_signal_with_default_factory(self):
        sig = use_session_storage("k", lambda: 42)
        assert sig.value == 42

    def test_no_storage_access_on_server(self, monkeypatch):
        import unittest.mock as mock

        getter = mock.MagicMock()
        monkeypatch.setattr(storage_composable, "_local_storage", getter)
        use_local_storage("k", 0)
        getter.assert_not_called()

    def test_none_default_returns_none(self):
        sig = use_local_storage("k", None)
        assert sig.value is None


class TestBrowserPath:
    def _patch(self, monkeypatch, fake, *, session: bool = False):
        monkeypatch.setattr(storage_composable, "ENVIRONMENT", "pyscript")
        monkeypatch.setattr(storage_composable, "_pyscript_ffi_is_none", lambda raw: False)
        monkeypatch.setattr(
            storage_composable,
            "_session_storage" if session else "_local_storage",
            lambda: fake,
        )
        return fake

    def test_reads_stored_value_on_creation(self, monkeypatch):
        fake = FakeStorage({"theme": '"dark"'})
        self._patch(monkeypatch, fake)
        sig = use_local_storage("theme", "light")
        assert sig.value == "dark"

    def test_updates_write_through_public_api(self, monkeypatch):
        fake = FakeStorage()
        self._patch(monkeypatch, fake)
        sig = use_local_storage("theme", "light")
        sig.value = "dark"
        assert fake.getItem("theme") == '"dark"'

    def test_session_storage_round_trip(self, monkeypatch):
        fake = FakeStorage()
        self._patch(monkeypatch, fake, session=True)
        sig = use_session_storage("draft", "")
        sig.value = "hello"
        assert fake.getItem("draft") == '"hello"'
        sig2 = use_session_storage("draft", "")
        assert sig2.value == "hello"

    def test_none_default_restores_stored_value(self, monkeypatch):
        fake = FakeStorage({"k": '"dark"'})
        self._patch(monkeypatch, fake)
        sig = use_local_storage("k", None)
        assert sig.value == "dark"


class TestOutsideSetup:
    def test_no_user_warning_emitted(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            sig = use_local_storage("k", 0)
        userwarnings = [x for x in w if issubclass(x.category, UserWarning)]
        assert userwarnings == []
        assert sig.value == 0

    def test_factory_requiring_args_warns_and_raises(self):
        def factory(*, required):
            return required

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with pytest.raises(TypeError):
                use_local_storage("k", factory)
        assert any("arguments" in str(x.message).lower() for x in w)


class TestNoTransferRegistration:
    def test_setup_call_does_not_register_transferable(self):
        state = make_state()
        with component_context(state):
            use_local_storage("k", 0)
            use_session_storage("j", lambda: 1)
        assert len(state.context._transferable_signals) == 0


class TestComponentIntegration:
    def test_signal_usable_in_template_and_writes_on_update(self, monkeypatch):
        fake = FakeStorage()
        monkeypatch.setattr(storage_composable, "ENVIRONMENT", "pyscript")
        monkeypatch.setattr(storage_composable, "_local_storage", lambda: fake)
        captured: dict[str, Signal] = {}

        @define_component
        def Page(context):
            theme = use_local_storage("theme", lambda: "light")
            captured["theme"] = theme
            return render_template('<span data-testid="t">{{ theme }}</span>', {"theme": theme})

        with TestRenderer.render(Page) as result:
            el = result.find_by_attribute("data-testid", "t")
            assert el is not None
            assert el.textContent == "light"
            captured["theme"].value = "dark"
            assert el.textContent == "dark"
            assert fake.getItem("theme") == '"dark"'
