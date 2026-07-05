from __future__ import annotations

import dataclasses
import enum
import html as html_module
import json
from unittest.mock import MagicMock

from webcompy.components._component import Component
from webcompy.hydration._collect import (
    _collect_component_signals,
    collect_transfer_data,
)
from webcompy.hydration._payload import (
    CURRENT_TRANSFER_VERSION,
    TransferPayload,
    deserialize_payload,
    serialize_payload,
)
from webcompy.hydration._restore import restore_signal_values
from webcompy.signal import (
    Computed,
    ReactiveDict,
    ReactiveList,
    Signal,
    computed_property,
)
from webcompy.signal._container import SignalReceivable


class _CodecIntEnum(enum.IntEnum):
    LOW = 1
    HIGH = 10


@dataclasses.dataclass
class _CodecPoint:
    x: int
    y: int


class Receiver(SignalReceivable):
    def __init__(self):
        self.count = Signal(0)
        self.name = Signal("alice")

    @computed_property
    def doubled(self):
        return self.count.value * 2


def _stub_component(members=None, component_id="stub-cmp"):
    component = MagicMock(spec=Component)
    component.__signal_members__ = members or {}
    component._property = {"component_id": component_id}
    component._async_results = []
    return component


class TestSignalReceivableKeying:
    def test_signal_assigned_to_self_is_tracked_by_name(self):
        component = Receiver()
        reactive = Signal(0)
        component.count = reactive
        assert component.__signal_members__["count"] is reactive

    def test_computed_property_registered_by_method_name(self):
        component = Receiver()
        _ = component.doubled
        assert "doubled" in component.__signal_members__
        assert "count" in component.__signal_members__

    def test_reassigning_signal_attribute_updates_registry(self):
        component = Receiver()
        first = component.count
        new_count = Signal(5)
        component.count = new_count
        assert component.__signal_members__["count"] is new_count
        assert first not in component.__signal_members__.values()

    def test_non_signal_attributes_are_not_tracked(self):
        class Sub(SignalReceivable):
            def __init__(self):
                self.count = Signal(0)

        s = Sub()
        s.name = "Alice"
        assert "name" not in s.__signal_members__
        assert "count" in s.__signal_members__


class TestCollectComponentSignals:
    def test_collects_signal_value(self):
        component = _stub_component({"count": Signal(7)}, "cmp")
        result = _collect_component_signals(component)
        assert result == {"count": 7}

    def test_collects_string_signal_value(self):
        component = _stub_component({"name": Signal("Alice")}, "cmp")
        result = _collect_component_signals(component)
        assert result == {"name": "Alice"}

    def test_collects_computed_cached_value(self):
        source = Signal(5)
        comp = Computed(lambda: source.value * 2)
        _ = comp.value
        component = _stub_component({"doubled": comp}, "cmp")
        result = _collect_component_signals(component)
        assert result == {"doubled": 10}

    def test_collects_reactive_list(self):
        component = _stub_component({"items": ReactiveList([1, 2, 3])}, "cmp")
        result = _collect_component_signals(component)
        assert result == {"items": [1, 2, 3]}

    def test_collects_reactive_dict(self):
        component = _stub_component({"settings": ReactiveDict({"a": 1, "b": 2})}, "cmp")
        result = _collect_component_signals(component)
        assert result == {"settings": {"a": 1, "b": 2}}

    def test_drops_non_serializable_signal_value(self, caplog):
        class NonSerializable:
            pass

        bad = Signal(NonSerializable())
        component = _stub_component({"bad": bad, "good": Signal("ok")}, "cmp")
        with caplog.at_level("WARNING", logger="webcompy.hydration._collect"):
            result = _collect_component_signals(component)
        assert "bad" not in result
        assert result["good"] == "ok"

    def test_empty_members_returns_empty_dict(self):
        component = _stub_component({}, "cmp")
        assert _collect_component_signals(component) == {}

    def test_component_with_no_members_attr(self):
        component = MagicMock(spec=Receiver)
        component.__signal_members__ = {}
        component._property = {"component_id": "cmp"}
        assert _collect_component_signals(component) == {}


class TestCollectTransferDataSignals:
    def test_collects_signals_into_payload(self):
        count_signal = Signal(8)
        name_signal = Signal("Bob")
        child = _stub_component(
            {"count": count_signal, "name": name_signal},
            component_id="cmp-a",
        )
        parent = MagicMock()
        parent._children = [child]
        parent._property = {"component_id": "root"}
        payload = collect_transfer_data(parent)
        assert "cmp-a" in payload.signals
        assert payload.signals["cmp-a"]["count"] == 8
        assert payload.signals["cmp-a"]["name"] == "Bob"

    def test_component_with_no_signals_excluded(self):
        child = _stub_component({}, component_id="empty-cmp")
        parent = MagicMock()
        parent._children = [child]
        parent._property = {"component_id": "root"}
        payload = collect_transfer_data(parent)
        assert "empty-cmp" not in payload.signals

    def test_component_with_only_failing_signals_excluded(self, caplog):
        class NonSerializable:
            pass

        child = _stub_component(
            {"bad": Signal(NonSerializable())},
            component_id="bad-cmp",
        )
        parent = MagicMock()
        parent._children = [child]
        parent._property = {"component_id": "root"}
        with caplog.at_level("WARNING", logger="webcompy.hydration._collect"):
            payload = collect_transfer_data(parent)
        assert "bad-cmp" not in payload.signals

    def test_version_is_current(self):
        parent = MagicMock()
        parent._children = []
        parent._property = {"component_id": "root"}
        payload = collect_transfer_data(parent)
        assert payload.__webcompy_transfer_version__ == CURRENT_TRANSFER_VERSION
        assert payload.__webcompy_transfer_version__ == 2


class TestRestoreSignalValues:
    def test_restores_value_directly(self):
        component = Receiver()
        restore_signal_values(component, {"count": 42})
        assert component.count._value == 42

    def test_restores_without_triggering_callbacks(self):
        component = Receiver()
        callbacks = []
        component.count.on_after_updating(lambda v: callbacks.append(v))
        restore_signal_values(component, {"count": 99})
        assert callbacks == []
        assert component.count._value == 99

    def test_restores_computed_cached_value_without_recompute(self, monkeypatch):
        component = Receiver()
        _ = component.doubled
        recomputed = []
        monkeypatch.setattr(
            component.doubled,
            "producer_recompute_value",
            lambda: recomputed.append(True),
        )
        restore_signal_values(component, {"doubled": 50})
        assert component.doubled._value == 50
        assert recomputed == []

    def test_missing_attr_name_is_handled_gracefully(self, caplog):
        component = Receiver()
        original_count = component.count._value
        with caplog.at_level("DEBUG", logger="webcompy.hydration._restore"):
            restore_signal_values(component, {"missing_attr": 1})
        assert component.count._value == original_count

    def test_empty_signals_data_is_noop(self):
        component = Receiver()
        restore_signal_values(component, {})
        assert component.count._value == 0

    def test_none_signals_data_is_noop(self):
        component = Receiver()
        restore_signal_values(component, None)
        assert component.count._value == 0


class TestPayloadVersioning:
    def test_payload_default_version_is_2(self):
        payload = TransferPayload()
        assert payload.__webcompy_transfer_version__ == 2
        assert payload.signals == {}

    def test_serialize_includes_signals_section(self):
        payload = TransferPayload(
            signals={"cmp-1": {"count": 5}},
        )
        serialized = serialize_payload(payload)
        raw = json.loads(html_module.unescape(serialized))
        assert raw["__webcompy_transfer_version__"] == 2
        assert raw["signals"]["cmp-1"]["count"] == 5

    def test_deserialize_v2_with_signals(self):
        payload = TransferPayload(
            signals={"cmp-a": {"count": 7, "items": [1, 2]}},
        )
        serialized = serialize_payload(payload)
        result = deserialize_payload(serialized)
        assert result is not None
        assert result.__webcompy_transfer_version__ == 2
        assert result.signals["cmp-a"]["count"] == 7
        assert result.signals["cmp-a"]["items"] == [1, 2]

    def test_deserialize_v1_has_empty_signals(self):
        raw = {
            "__webcompy_transfer_version__": 1,
            "fetches": {},
            "async_results": {},
            "signals": {},
        }
        encoded = html_module.escape(json.dumps(raw, ensure_ascii=False), quote=True)
        result = deserialize_payload(encoded)
        assert result is not None
        assert result.signals == {}


class TestRoundTrip:
    def test_collect_serialize_deserialize_restore_round_trip(self):
        count_signal = Signal(11)
        name_signal = Signal("Carol")
        items_signal = ReactiveList([1, 2, 3])
        child = _stub_component(
            {
                "count": count_signal,
                "name": name_signal,
                "items": items_signal,
            },
            component_id="cmp-round",
        )
        parent = MagicMock()
        parent._children = [child]
        parent._property = {"component_id": "root"}

        payload = collect_transfer_data(parent)
        serialized = serialize_payload(payload)
        deserialized = deserialize_payload(serialized)
        assert deserialized is not None
        signals_data = deserialized.signals["cmp-round"]

        browser = Receiver()
        restore_signal_values(browser, signals_data)
        assert browser.count._value == 11
        assert browser.name._value == "Carol"


class TestCodecTypedRoundTrip:
    def _make_browser(self, **signals):
        class _Browser(SignalReceivable):
            pass

        browser = _Browser()
        for name, value in signals.items():
            setattr(browser, name, Signal(value))
        return browser

    def test_datetime_signal_round_trip(self):
        from datetime import datetime

        from webcompy.hydration import decode

        dt = datetime(2025, 6, 1, 12, 30, 0)
        child = _stub_component(
            {"last_seen": Signal(dt)},
            component_id="cmp-dt",
        )
        parent = MagicMock()
        parent._children = [child]
        parent._property = {"component_id": "root"}

        payload = collect_transfer_data(parent)
        serialized = serialize_payload(payload)
        deserialized = deserialize_payload(serialized)
        assert deserialized is not None
        signals_data = deserialized.signals["cmp-dt"]

        browser = self._make_browser(last_seen=None)
        restore_signal_values(browser, signals_data)
        assert browser.last_seen._value == decode(dt)

    def test_int_enum_signal_round_trip(self):
        from webcompy.hydration import decode

        child = _stub_component(
            {"priority": Signal(_CodecIntEnum.HIGH)},
            component_id="cmp-ie",
        )
        parent = MagicMock()
        parent._children = [child]
        parent._property = {"component_id": "root"}

        payload = collect_transfer_data(parent)
        serialized = serialize_payload(payload)
        deserialized = deserialize_payload(serialized)
        assert deserialized is not None
        signals_data = deserialized.signals["cmp-ie"]

        browser = self._make_browser(priority=None)
        restore_signal_values(browser, signals_data)
        assert browser.priority._value == decode(_CodecIntEnum.HIGH)

    def test_dataclass_signal_round_trip(self):
        from webcompy.hydration import decode

        pt = _CodecPoint(3, 4)
        child = _stub_component(
            {"origin": Signal(pt)},
            component_id="cmp-dc",
        )
        parent = MagicMock()
        parent._children = [child]
        parent._property = {"component_id": "root"}

        payload = collect_transfer_data(parent)
        serialized = serialize_payload(payload)
        deserialized = deserialize_payload(serialized)
        assert deserialized is not None
        signals_data = deserialized.signals["cmp-dc"]

        browser = self._make_browser(origin=None)
        restore_signal_values(browser, signals_data)
        assert browser.origin._value == decode(pt)

    def test_set_signal_round_trip(self):
        from webcompy.hydration import decode

        child = _stub_component(
            {"tags": Signal({"a", "b"})},
            component_id="cmp-set",
        )
        parent = MagicMock()
        parent._children = [child]
        parent._property = {"component_id": "root"}

        payload = collect_transfer_data(parent)
        serialized = serialize_payload(payload)
        deserialized = deserialize_payload(serialized)
        assert deserialized is not None
        signals_data = deserialized.signals["cmp-set"]

        browser = self._make_browser(tags=None)
        restore_signal_values(browser, signals_data)
        assert browser.tags._value == decode({"a", "b"})

    def test_decimal_signal_round_trip(self):
        from decimal import Decimal

        from webcompy.hydration import decode

        child = _stub_component(
            {"price": Signal(Decimal("19.99"))},
            component_id="cmp-dec",
        )
        parent = MagicMock()
        parent._children = [child]
        parent._property = {"component_id": "root"}

        payload = collect_transfer_data(parent)
        serialized = serialize_payload(payload)
        deserialized = deserialize_payload(serialized)
        assert deserialized is not None
        signals_data = deserialized.signals["cmp-dec"]

        browser = self._make_browser(price=None)
        restore_signal_values(browser, signals_data)
        assert browser.price._value == decode(Decimal("19.99"))

    def test_no_reserved_key_warning_during_round_trip(self, caplog):
        from datetime import datetime

        dt = datetime(2025, 1, 1)
        child = _stub_component(
            {"when": Signal(dt)},
            component_id="cmp-rk",
        )
        parent = MagicMock()
        parent._children = [child]
        parent._property = {"component_id": "root"}

        with caplog.at_level("WARNING"):
            payload = collect_transfer_data(parent)
            serialized = serialize_payload(payload)

        reserved_warnings = [msg for msg in caplog.messages if "Reserved key" in msg]
        assert reserved_warnings == [], (
            f"Double-encode detected — unexpected 'Reserved key' warnings: {reserved_warnings}"
        )

        deserialized = deserialize_payload(serialized)
        assert deserialized is not None
        assert deserialized.signals["cmp-rk"]["when"] == dt
