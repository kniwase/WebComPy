"""Unit coverage for the browser-tier pytest dispatch helpers in conftest."""

from types import SimpleNamespace

import pytest

from tests.browser.conftest import _parametrize_index


def _item(func, callspec_params: dict | None):
    return SimpleNamespace(
        function=func, callspec=None if callspec_params is None else SimpleNamespace(params=callspec_params)
    )


class TestParametrizeIndex:
    def test_no_callspec_returns_none(self):
        def func(value):
            return value

        func.pytestmark = [pytest.mark.parametrize("value", [1, 2])]

        assert _parametrize_index(_item(func, None)) is None

    def test_single_name_match(self):
        def func(value):
            return value

        func.pytestmark = [pytest.mark.parametrize("value", [1, 2])]

        assert _parametrize_index(_item(func, {"value": 2})) == 1

    def test_multiple_names_match(self):
        def func(a, b):
            return a, b

        func.pytestmark = [pytest.mark.parametrize(("a", "b"), [(1, "x"), (2, "y")])]

        assert _parametrize_index(_item(func, {"a": 2, "b": "y"})) == 1

    def test_duplicate_values_raise(self):
        def func(value):
            return value

        func.pytestmark = [pytest.mark.parametrize("value", [7, 7])]

        with pytest.raises(RuntimeError, match="ambiguous parametrize match"):
            _parametrize_index(_item(func, {"value": 7}))

    def test_unmatched_value_raises(self):
        def func(value):
            return value

        func.pytestmark = [pytest.mark.parametrize("value", [1, 2])]

        with pytest.raises(RuntimeError, match="could not match callspec params"):
            _parametrize_index(_item(func, {"value": 99}))

    def test_stacked_marks_raise(self):
        def func(value, other):
            return value, other

        func.pytestmark = [
            pytest.mark.parametrize("value", [1]),
            pytest.mark.parametrize("other", [9]),
        ]

        with pytest.raises(RuntimeError, match="stacked"):
            _parametrize_index(_item(func, {"value": 1, "other": 9}))
