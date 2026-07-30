from __future__ import annotations

from webcompy.elements.generators import repeat
from webcompy.elements.types._repeat import RepeatElement
from webcompy.elements.types._switch import SwitchElement
from webcompy.elements.types._text import TextElement
from webcompy.signal import Computed, ReactiveList, Signal


class TestRepeatAcceptsComputed:
    def test_repeat_accepts_computed_over_slice(self):
        items = ReactiveList([1, 2, 3, 4])
        sliced = Computed(lambda: items.value[:2])
        el = repeat(sliced, lambda v: TextElement(str(v)))
        assert isinstance(el, RepeatElement)
        assert el._sequence is sliced

    def test_repeat_accepts_computed_over_filtered(self):
        items = ReactiveList([1, 2, 3, 4])
        filtered = Computed(lambda: [x for x in items.value if x > 2])
        el = repeat(filtered, lambda v: TextElement(str(v)))
        assert isinstance(el, RepeatElement)
        assert el._sequence is filtered

    def test_computed_over_slice_tracks_list_mutation(self):
        items = ReactiveList([1, 2, 3, 4])
        sliced = Computed(lambda: items.value[:2])
        assert sliced.value == [1, 2]
        items.value = [9, 8, 7, 6]
        assert sliced.value == [9, 8]


class TestSwitchAcceptsComputed:
    def test_switch_accepts_computed_condition(self):
        count = Signal(5)
        cond = Computed(lambda: count.value > 3)
        cases = [(cond, lambda: TextElement("big"))]
        sw = SwitchElement(
            cases,
            default=lambda: TextElement("small"),
        )
        assert isinstance(sw, SwitchElement)
        assert sw._cases is cases
        assert sw._cases[0][0] is cond

    def test_switch_multiple_computed_cases(self):
        count = Signal(5)
        big = Computed(lambda: count.value > 5)
        small = Computed(lambda: count.value <= 5)
        cases = [(big, lambda: TextElement("big")), (small, lambda: TextElement("small"))]
        sw = SwitchElement(cases, default=None)
        assert isinstance(sw, SwitchElement)
        assert sw._cases is cases

    def test_select_generator_toggles_on_threshold(self):
        count = Signal(5)
        cond = Computed(lambda: count.value > 3)
        sw = SwitchElement(
            [(cond, lambda: TextElement("big"))],
            default=lambda: TextElement("small"),
        )
        idx, _ = sw._select_generator()
        assert idx == 0
        count.value = 1
        idx, _ = sw._select_generator()
        assert idx == -1
        count.value = 10
        idx, _ = sw._select_generator()
        assert idx == 0
