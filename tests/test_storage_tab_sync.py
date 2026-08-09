"""Tests for use_local_storage(sync_tabs=True) cross-tab synchronization."""

import logging as std_logging
from types import SimpleNamespace
from typing import Any

import pytest

import webcompy.storage._composable as storage_composable
from webcompy import use_local_storage
from webcompy.components._context_manager import ComponentRenderState, component_context
from webcompy.di._keys import _STORAGE_SYNC_REGISTRY_KEY
from webcompy.di._scope import DIScope
from webcompy.signal import Signal
from webcompy.signal._effect import EffectScope


class FakeStorage:
    def __init__(self, initial: dict[str, str] | None = None) -> None:
        self._data: dict[str, str] = dict(initial or {})
        self.set_calls: list[tuple[str, str]] = []

    def getItem(self, key: str) -> Any:
        return self._data.get(key)

    def setItem(self, key: str, value: str) -> None:
        self.set_calls.append((key, value))
        self._data[key] = value


class FakeProxy:
    def __init__(self, handler: Any) -> None:
        self.handler = handler
        self.destroyed = False

    def __call__(self, event: Any) -> None:
        self.handler(event)

    def destroy(self) -> None:
        self.destroyed = True


class FakeWindow:
    def __init__(self) -> None:
        self.listeners: dict[str, list[Any]] = {}

    def addEventListener(self, name: str, proxy: Any) -> None:
        self.listeners.setdefault(name, []).append(proxy)

    def removeEventListener(self, name: str, proxy: Any) -> None:
        self.listeners.get(name, []).remove(proxy)

    def dispatch_storage(self, key: str | None, new_value: str | None) -> None:
        event = SimpleNamespace(key=key, newValue=new_value, url="http://localhost/")
        for proxy in list(self.listeners.get("storage", [])):
            proxy(event)


class FakeCtx:
    def __init__(self, name: str = "TestComp") -> None:
        self._component_name = name
        self._transferable_signals: dict = {}

    def on_before_destroy(self, func: Any) -> None:
        self._destroy_hook = func

    def __get_lifecyclehooks__(self) -> dict[str, Any]:
        return {"on_before_destroy": self._destroy_hook} if getattr(self, "_destroy_hook", None) else {}


def make_state(component_name: str = "TestComp") -> ComponentRenderState:
    return ComponentRenderState(
        context=FakeCtx(component_name),
        effect_scope=EffectScope(),
        framework_cleanup=lambda: None,
    )


@pytest.fixture
def sync_env(monkeypatch):
    scope = DIScope()
    window = FakeWindow()
    fake = FakeStorage()
    monkeypatch.setattr(storage_composable, "ENVIRONMENT", "pyscript")
    monkeypatch.setattr(storage_composable, "_pyscript_ffi_is_none", lambda raw: False)
    monkeypatch.setattr(storage_composable, "_local_storage", lambda: fake)
    monkeypatch.setattr(storage_composable, "_browser_window", lambda: window)
    monkeypatch.setattr(storage_composable, "_create_event_proxy", lambda h: FakeProxy(h))
    monkeypatch.setattr(storage_composable, "_get_app_di_scope", lambda: scope)
    return SimpleNamespace(scope=scope, window=window, storage=fake)


class TestRemoteApply:
    def test_remote_write_updates_signal_and_notifies(self, sync_env):
        sig = use_local_storage("theme", "light", sync_tabs=True)
        notified: list = []
        sig.on_after_updating(lambda v: notified.append(v))
        sync_env.window.dispatch_storage("theme", '"dark"')
        assert sig.value == "dark"
        assert notified == ["dark"]

    def test_remote_apply_does_not_write_back(self, sync_env):
        sig = use_local_storage("theme", "light", sync_tabs=True)
        sync_env.window.dispatch_storage("theme", '"dark"')
        assert sig.value == "dark"
        assert sync_env.storage.set_calls == []

    def test_remote_removal_resets_to_value_default(self, sync_env):
        sig = use_local_storage("theme", "light", sync_tabs=True)
        sync_env.window.dispatch_storage("theme", '"dark"')
        sync_env.window.dispatch_storage("theme", None)
        assert sig.value == "light"

    def test_remote_removal_resets_to_factory_default(self, sync_env):
        calls: list = []

        def factory() -> dict[str, int]:
            calls.append("called")
            return {"n": len(calls)}

        sig = use_local_storage("settings", factory, sync_tabs=True)
        sync_env.window.dispatch_storage("settings", '{"n": 99}')
        assert sig.value == {"n": 99}
        sync_env.window.dispatch_storage("settings", None)
        assert sig.value == {"n": 2}
        assert calls == ["called", "called"]

    def test_corrupted_remote_payload_warns_and_resets(self, sync_env, caplog):
        sig = use_local_storage("theme", "light", sync_tabs=True)
        with caplog.at_level(std_logging.WARNING, logger="uvicorn"):
            sync_env.window.dispatch_storage("theme", "{not json")
        assert sig.value == "light"
        assert any("corrupted" in r.message for r in caplog.records)

    def test_unregistered_key_event_ignored(self, sync_env):
        sig = use_local_storage("theme", "light", sync_tabs=True)
        sync_env.window.dispatch_storage("other", '"x"')
        assert sig.value == "light"

    def test_equal_value_delivery_is_noop(self, sync_env):
        sig = use_local_storage("theme", "light", sync_tabs=True)
        notified: list = []
        sig.on_after_updating(lambda v: notified.append(v))
        sync_env.window.dispatch_storage("theme", '"dark"')
        assert notified == ["dark"]
        sync_env.window.dispatch_storage("theme", '"dark"')
        assert notified == ["dark"]

    def test_clear_resets_all_registered_keys(self, sync_env):
        sig1 = use_local_storage("theme", "light", sync_tabs=True)
        sig2 = use_local_storage("settings", 0, sync_tabs=True)
        sync_env.window.dispatch_storage("theme", '"dark"')
        sync_env.window.dispatch_storage("settings", "5")
        sync_env.window.dispatch_storage(None, None)
        assert sig1.value == "light"
        assert sig2.value == 0

    def test_dispatch_isolates_callback_failures(self, sync_env, caplog):
        registry = storage_composable._StorageSyncRegistry()
        received: list = []

        def boom(raw):
            raise RuntimeError("boom")

        registry.subscribe("k", boom)
        registry.subscribe("k", lambda raw: received.append(raw))
        with caplog.at_level(std_logging.WARNING, logger="uvicorn"):
            registry._dispatch(SimpleNamespace(key="k", newValue='"x"', url="http://localhost/"))
        assert received == ['"x"']
        assert any("failed; continuing dispatch" in r.message for r in caplog.records)


class TestRegistrationPolicy:
    def test_sync_tabs_false_registers_nothing(self, sync_env):
        sig = use_local_storage("theme", "light")
        assert sig.value == "light"
        assert sync_env.window.listeners == {}
        assert sync_env.scope.inject(_STORAGE_SYNC_REGISTRY_KEY, default=None) is None

    def test_server_path_creates_no_listener(self, monkeypatch):
        import unittest.mock as mock

        getter = mock.MagicMock()
        monkeypatch.setattr(storage_composable, "_browser_window", getter)
        sig = use_local_storage("theme", "light", sync_tabs=True)
        assert sig.value == "light"
        getter.assert_not_called()


class TestRegistryScoping:
    def test_registry_scoped_per_app_di_scope(self, monkeypatch):
        scope_a, window_a, fake_a = DIScope(), FakeWindow(), FakeStorage()
        scope_b, window_b, fake_b = DIScope(), FakeWindow(), FakeStorage()
        monkeypatch.setattr(storage_composable, "ENVIRONMENT", "pyscript")
        monkeypatch.setattr(storage_composable, "_pyscript_ffi_is_none", lambda raw: False)
        monkeypatch.setattr(storage_composable, "_create_event_proxy", lambda h: FakeProxy(h))
        monkeypatch.setattr(storage_composable, "_local_storage", lambda: fake_a)
        monkeypatch.setattr(storage_composable, "_get_app_di_scope", lambda: scope_a)
        monkeypatch.setattr(storage_composable, "_browser_window", lambda: window_a)
        sig_a = use_local_storage("theme", "light", sync_tabs=True)
        monkeypatch.setattr(storage_composable, "_local_storage", lambda: fake_b)
        monkeypatch.setattr(storage_composable, "_get_app_di_scope", lambda: scope_b)
        monkeypatch.setattr(storage_composable, "_browser_window", lambda: window_b)
        sig_b = use_local_storage("theme", "light", sync_tabs=True)

        window_b.dispatch_storage("theme", '"dark"')
        assert sig_b.value == "dark"
        assert sig_a.value == "light"

        registry_a = scope_a.inject(_STORAGE_SYNC_REGISTRY_KEY, default=None)
        registry_b = scope_b.inject(_STORAGE_SYNC_REGISTRY_KEY, default=None)
        assert registry_a is not registry_b

        window_a.dispatch_storage("theme", '"other"')
        assert sig_a.value == "other"
        assert sig_b.value == "dark"

    def test_unregister_on_component_destroy(self, sync_env):
        state = make_state()
        with component_context(state):
            sig = use_local_storage("theme", "light", sync_tabs=True)
        sync_env.window.dispatch_storage("theme", '"dark"')
        assert sig.value == "dark"
        state.context.__get_lifecyclehooks__()["on_before_destroy"]()
        sync_env.window.dispatch_storage("theme", '"light"')
        assert sig.value == "dark"

    def test_multiple_instances_all_unregister_on_destroy(self, sync_env):
        state = make_state()
        with component_context(state):
            sig1 = use_local_storage("k1", "a", sync_tabs=True)
            sig2 = use_local_storage("k2", "b", sync_tabs=True)
        sync_env.window.dispatch_storage("k1", '"x"')
        sync_env.window.dispatch_storage("k2", '"y"')
        assert sig1.value == "x"
        assert sig2.value == "y"
        state.context.__get_lifecyclehooks__()["on_before_destroy"]()
        sync_env.window.dispatch_storage("k1", '"p"')
        sync_env.window.dispatch_storage("k2", '"q"')
        assert sig1.value == "x"
        assert sig2.value == "y"

    def test_prior_user_destroy_hook_preserved(self, sync_env):
        state = make_state()
        destroyed: list[str] = []
        with component_context(state):
            state.context.on_before_destroy(lambda: destroyed.append("user"))
            sig = use_local_storage("theme", "light", sync_tabs=True)
        sync_env.window.dispatch_storage("theme", '"dark"')
        assert sig.value == "dark"
        state.context.__get_lifecyclehooks__()["on_before_destroy"]()
        assert destroyed == ["user"]
        sync_env.window.dispatch_storage("theme", '"light"')
        assert sig.value == "dark"

    def test_no_app_scope_warns_and_skips(self, monkeypatch, caplog):
        window = FakeWindow()
        fake = FakeStorage()
        monkeypatch.setattr(storage_composable, "ENVIRONMENT", "pyscript")
        monkeypatch.setattr(storage_composable, "_pyscript_ffi_is_none", lambda raw: False)
        monkeypatch.setattr(storage_composable, "_local_storage", lambda: fake)
        monkeypatch.setattr(storage_composable, "_browser_window", lambda: window)
        monkeypatch.setattr(storage_composable, "_create_event_proxy", lambda h: FakeProxy(h))
        monkeypatch.setattr(storage_composable, "_get_app_di_scope", lambda: None)
        with caplog.at_level(std_logging.WARNING, logger="uvicorn"):
            sig = use_local_storage("theme", "light", sync_tabs=True)
        assert sig.value == "light"
        assert any("no app DI scope" in r.message for r in caplog.records)
        assert window.listeners == {}


class TestTypeChecks:
    def test_returns_signal(self, sync_env):
        sig = use_local_storage("theme", "light", sync_tabs=True)
        assert isinstance(sig, Signal)
        assert sig.value == "light"
