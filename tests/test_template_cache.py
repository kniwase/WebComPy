from __future__ import annotations

from webcompy.template._cache import clear_cache, get_or_compile
from webcompy.template._parser import parse_template


class TestParseFnCacheIsolation:
    def setup_method(self) -> None:
        clear_cache()

    def test_default_and_custom_parser_do_not_collide(self) -> None:
        tagged: list = []

        def tag_parser(source: str) -> list:
            roots = parse_template(source)
            tagged.append(roots)
            return roots

        src = "<div>hello</div>"
        get_or_compile(src, parse_fn=tag_parser)
        get_or_compile(src)
        assert len(tagged) == 1

    def test_same_custom_parser_uses_cache(self) -> None:
        call_count = {"n": 0}

        def counting_parser(source: str) -> list:
            call_count["n"] += 1
            return parse_template(source)

        src = "<p>x</p>"
        get_or_compile(src, parse_fn=counting_parser)
        get_or_compile(src, parse_fn=counting_parser)
        get_or_compile(src, parse_fn=counting_parser)
        assert call_count["n"] == 1

    def test_two_different_custom_parsers_each_called(self) -> None:
        count_a = {"n": 0}
        count_b = {"n": 0}

        def parser_a(source: str) -> list:
            count_a["n"] += 1
            return parse_template(source)

        def parser_b(source: str) -> list:
            count_b["n"] += 1
            return parse_template(source)

        src = "<p>x</p>"
        get_or_compile(src, parse_fn=parser_a)
        get_or_compile(src, parse_fn=parser_b)
        get_or_compile(src, parse_fn=parser_a)
        get_or_compile(src, parse_fn=parser_b)
        assert count_a["n"] == 1
        assert count_b["n"] == 1
