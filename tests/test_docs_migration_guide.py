from __future__ import annotations

import re
from pathlib import Path

import pytest

from webcompy.exception import WebComPyException
from webcompy.template import render_template
from webcompy.template._expression import FILTERS
from webcompy.template._parser import _KNOWN_UNSUPPORTED_DIRECTIVES, REJECTED_TAGS, parse_template

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs_app" / "documents"
MAIN_GUIDE = DOCS_DIR / "migration_from_jinja2_fastapi.md"
COMPAT_NOTES = DOCS_DIR / "migration_compatibility_notes.md"


def test_compatibility_notes_documents_all_rejected_directives_with_exact_errors() -> None:
    content = COMPAT_NOTES.read_text(encoding="utf-8")
    for directive in sorted(_KNOWN_UNSUPPORTED_DIRECTIVES):
        expected_msg = f"{{% {directive} %}} is not supported in WebComPy templates"
        with pytest.raises(WebComPyException) as exc_info:
            parse_template(f"<div>{{% {directive} %}}</div>")
        assert expected_msg in str(exc_info.value)
        assert expected_msg in content, f"Missing exact error for {{% {directive} %}} in {COMPAT_NOTES.name}"


def test_compatibility_notes_documents_all_builtin_filters() -> None:
    content = COMPAT_NOTES.read_text(encoding="utf-8")
    for name in sorted(FILTERS):
        assert f"`{name}`" in content, f"Missing built-in filter `{name}` in {COMPAT_NOTES.name}"


def test_compatibility_notes_exact_for_else_and_parser_errors() -> None:
    content = COMPAT_NOTES.read_text(encoding="utf-8")

    with pytest.raises(WebComPyException, match=r"\{% else %\} outside of \{% if %\} block"):
        parse_template("<ul>{% for x in items %}{% else %}{% endfor %}</ul>")
    assert "{% else %} outside of {% if %} block" in content

    for tag in sorted(REJECTED_TAGS):
        with pytest.raises(WebComPyException, match=f"<{tag}> is not allowed in templates"):
            parse_template(f"<div><{tag}></{tag}></div>")
        assert f"<{tag}>" in content

    with pytest.raises(WebComPyException, match=r"Invalid template expression 'first ~ \" \" ~ last'"):
        parse_template('<div>{{ first ~ " " ~ last }}</div>')
    assert "Invalid template expression 'first ~ \" \" ~ last'" in content

    with pytest.raises(WebComPyException, match="Template must have exactly one root element"):
        render_template("<h1>Hi</h1><p>World</p>", {})
    assert "Template must have exactly one root element" in content

    with pytest.raises(
        WebComPyException,
        match=re.escape("Event modifiers are not supported in templates: '@click.prevent'"),
    ):
        render_template('<button @click.prevent="save">Save</button>', {"save": lambda _ev: None})
    assert "Event modifiers are not supported in templates: '@click.prevent'" in content

    with pytest.raises(KeyError, match="Template variable 'defined' not found in context"):
        render_template("<p>{{ user is defined }}</p>", {"user": "Alice"})
    assert "Template variable 'defined' not found in context" in content

    with pytest.raises(KeyError, match="Template variable 'safe' not found in context"):
        render_template("<p>{{ snippet | safe }}</p>", {"snippet": "<b>hi</b>"})
    assert "Template variable 'safe' not found in context" in content


def test_main_migration_guide_structure_and_scope_note() -> None:
    content = MAIN_GUIDE.read_text(encoding="utf-8")
    required_fragments = [
        "## Architecture shift",
        "## Choosing an integration strategy",
        "/documents/server/asgi-integration#embedding-webcompy-in-a-fastapi-or-starlette-host",
        "base_url",
        "## Live before/after: user-list search",
        "## Why each line changed",
        "## Directive-by-directive conversion table",
        "## Concern-by-concern migration",
        "## Phased strangler checklist",
        "## Gotchas and what stays server-side",
        "Phase 0",
        "Phase N",
        "Transactional email bodies",
    ]
    for fragment in required_fragments:
        assert fragment in content, f"Missing expected section/content {fragment!r} in {MAIN_GUIDE.name}"
