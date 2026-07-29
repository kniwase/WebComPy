from __future__ import annotations

import time

import pytest

from webcompy.template._markdown_default import DefaultMarkdownParser
from webcompy.template._markdown_inline import render_inline


@pytest.fixture
def parser() -> DefaultMarkdownParser:
    return DefaultMarkdownParser()


class TestAdversarialInputs:
    def test_delimiter_sea_large(self):
        n = 2000
        src = "*" * n + "foo" + "*" * n
        t0 = time.perf_counter()
        result = render_inline(src, {})
        dt = time.perf_counter() - t0
        assert len(result) > 0
        assert dt < 5.0

    def test_delimiter_sea_very_large(self):
        n = 5000
        src = "*" * n + "foo" + "*" * n
        t0 = time.perf_counter()
        result = render_inline(src, {})
        dt = time.perf_counter() - t0
        assert len(result) > 0
        assert dt < 15.0

    def test_deep_bracket_nesting(self):
        n = 500
        src = "[" * n + "x" + "]" * n + "(u)"
        t0 = time.perf_counter()
        result = render_inline(src, {})
        dt = time.perf_counter() - t0
        assert len(result) > 0
        assert dt < 10.0

    def test_deep_emphasis_chars_via_parser(self, parser: DefaultMarkdownParser):
        n = 1000
        src = "*" * n + "foo" + "*" * n
        t0 = time.perf_counter()
        result = parser.render(src)
        dt = time.perf_counter() - t0
        assert len(result) > 0
        assert dt < 10.0

    def test_mixed_deep_nesting(self):
        cases = [
            "*" * 400 + "a" + "*" * 400,
            "[" * 200 + "a" + "]" * 200 + "(/)",
            "~" * 100 + "text" + "~" * 100,
        ]
        for src in cases:
            t0 = time.perf_counter()
            result = render_inline(src, {})
            dt = time.perf_counter() - t0
            assert len(result) > 0
            assert dt < 10.0

    def test_deep_nesting_no_recursion_error(self):
        n = 3000
        src = "*" * n + "x" + "*" * n
        render_inline(src, {})
