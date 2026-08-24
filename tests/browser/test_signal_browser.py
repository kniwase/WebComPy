"""Pure reactive propagation validated under the real PyScript runtime.

Top-level imports must stay CPython-importable: browser-only modules are
imported inside function bodies (CPython-importability invariant).
"""

import pytest

from webcompy.signal import Computed, Signal


@pytest.mark.parametrize("value", [1, "a", None])
def test_signal_roundtrip(app, value):
    signal = Signal(value)

    assert signal.value == value


def test_signal_propagates_to_computed(app):
    base = Signal(2)
    doubled = Computed(lambda: base.value * 2)

    assert doubled.value == 4

    base.value = 5

    assert doubled.value == 10


def test_on_after_updating_callback(app):
    seen = []
    signal = Signal(0)
    signal.on_after_updating(lambda value: seen.append(value))

    signal.value = 42
    signal.value = 7

    assert seen == [42, 7]
