from __future__ import annotations

import pytest

from webcompy.exception import WebComPyException
from webcompy.template._frontmatter import split_frontmatter


class TestFlatFrontmatter:
    def test_flat_extraction(self) -> None:
        source = "---\ntitle: Getting Started\nsection: guide\n---\n# Body\n"
        metadata, body = split_frontmatter(source)
        assert metadata == {"title": "Getting Started", "section": "guide"}
        assert body == "# Body\n"

    def test_value_with_colon_is_preserved(self) -> None:
        source = "---\nlink: https://example.com/docs\n---\nbody"
        metadata, body = split_frontmatter(source)
        assert metadata == {"link": "https://example.com/docs"}
        assert body == "body"

    def test_whitespace_stripped(self) -> None:
        source = "---\n  title  :   spaced  \n---\nbody"
        metadata, _body = split_frontmatter(source)
        assert metadata == {"title": "spaced"}

    def test_empty_lines_skipped(self) -> None:
        source = "---\ntitle: A\n\n---\nbody"
        metadata, body = split_frontmatter(source)
        assert metadata == {"title": "A"}
        assert body == "body"

    def test_empty_block(self) -> None:
        source = "---\n---\nbody"
        metadata, body = split_frontmatter(source)
        assert metadata == {}
        assert body == "body"

    def test_duplicate_keys_last_wins(self) -> None:
        source = "---\ntitle: A\ntitle: B\n---\nbody"
        metadata, _body = split_frontmatter(source)
        assert metadata == {"title": "B"}

    def test_crlf_line_endings(self) -> None:
        source = "---\r\ntitle: A\r\n---\r\nbody"
        metadata, body = split_frontmatter(source)
        assert metadata == {"title": "A"}
        assert body == "body"

    def test_malformed_line_raises(self) -> None:
        source = "---\ntitle: A\nno_colon_here\n---\nbody"
        with pytest.raises(WebComPyException, match="Malformed flat frontmatter"):
            split_frontmatter(source)

    def test_unterminated_block_raises(self) -> None:
        source = "---\ntitle: A\n# no closing delimiter"
        with pytest.raises(WebComPyException, match="Unterminated frontmatter"):
            split_frontmatter(source)


class TestTomlFrontmatter:
    def test_toml_nested_structures(self) -> None:
        source = '+++\ntitle = "Guide"\n[page]\norder = 2\n+++\n# Body\n'
        metadata, body = split_frontmatter(source)
        assert metadata == {"title": "Guide", "page": {"order": 2}}
        assert body == "# Body\n"

    def test_toml_arrays(self) -> None:
        source = '+++\ntags = ["a", "b"]\n+++\nbody'
        metadata, _body = split_frontmatter(source)
        assert metadata == {"tags": ["a", "b"]}

    def test_toml_typed_scalars(self) -> None:
        source = "+++\ncount = 3\nratio = 1.5\nenabled = true\n+++\nbody"
        metadata, _body = split_frontmatter(source)
        assert metadata == {"count": 3, "ratio": 1.5, "enabled": True}

    def test_invalid_toml_raises(self) -> None:
        source = "+++\nnot = = valid\n+++\nbody"
        with pytest.raises(WebComPyException, match="Invalid TOML frontmatter"):
            split_frontmatter(source)


class TestNoFrontmatter:
    def test_no_frontmatter_passthrough(self) -> None:
        source = "# Just a heading\n\nSome text."
        metadata, body = split_frontmatter(source)
        assert metadata == {}
        assert body == source

    def test_empty_source(self) -> None:
        metadata, body = split_frontmatter("")
        assert metadata == {}
        assert body == ""

    def test_delimiter_not_on_first_line(self) -> None:
        source = "text\n---\nmore"
        metadata, body = split_frontmatter(source)
        assert metadata == {}
        assert body == source
