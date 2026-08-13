"""Tests for use_readonly_signal() and the ReadonlySignal type."""

from __future__ import annotations

import warnings

import pytest

from webcompy import use_readonly_signal as use_readonly_signal_top
from webcompy.signal import Computed, ReadonlySignal, use_readonly_signal


class TestUseReadonlySignal:
    def test_initial_value_readable_immediately(self):
        view, _ = use_readonly_signal(10)
        assert view.value == 10

    def test_update_is_sole_write_path(self):
        view, update = use_readonly_signal(0)
        notified: list[int] = []
        view.on_after_updating(lambda v: notified.append(v))
        result = update(42)
        assert result == 42
        assert view.value == 42
        assert notified == [42]

    def test_update_returns_current_value(self):
        view, update = use_readonly_signal(5)
        notified: list[int] = []
        view.on_after_updating(lambda v: notified.append(v))
        result = update(5)
        assert result == 5
        assert view.value == 5
        assert notified == []

    def test_equal_consecutive_updates_are_not_re_notified(self):
        view, update = use_readonly_signal(5)
        notified: list[int] = []
        view.on_after_updating(lambda v: notified.append(v))
        update(5)
        update(7)
        update(7)
        assert view.value == 7
        assert notified == [7]

    def test_reactive_consumers_are_notified(self):
        view, update = use_readonly_signal(1)
        doubled = Computed(lambda: view.value * 2)
        assert doubled.value == 2
        update(21)
        assert doubled.value == 42

    def test_readonly_signal_exposes_no_write_access(self):
        view, _ = use_readonly_signal(0)
        assert isinstance(view, ReadonlySignal)
        with pytest.raises(AttributeError):
            view.value = 1
        with pytest.raises(AttributeError):
            view.set_value(1)

    def test_standalone_usage_emits_no_user_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            view, update = use_readonly_signal(0)
        userwarnings = [x for x in w if issubclass(x.category, UserWarning)]
        assert userwarnings == []
        update(1)
        assert view.value == 1

    def test_callable_initial_is_treated_as_plain_value(self):
        def factory() -> str:
            return "factory"

        view, update = use_readonly_signal(factory)
        assert view.value is factory
        update("value")
        assert view.value == "value"

    def test_import_identity_between_top_level_and_signal(self):
        assert use_readonly_signal is use_readonly_signal_top

    def test_readonly_signal_type_annotation_is_usable(self):
        view: ReadonlySignal[int]
        view, _ = use_readonly_signal(0)
        assert view.value == 0
