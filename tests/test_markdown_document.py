from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import pytest

from webcompy.components._generator import define_component
from webcompy.di._keys import _HEAD_PROPS_KEY
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.elements import create_element
from webcompy.elements.types._element import Element
from webcompy.ports._keys import MARKDOWN_PORT_KEY, RESOURCE_PORT_KEY
from webcompy.template import load_markdown_document
from webcompy.template._cache import clear_cache
from webcompy.template._markdown_default import DefaultMarkdownParser
from webcompy_server.ports._resource import ServerResourcePort
from webcompy_testing import TestRenderer


class _FakeResourcePort:
    def __init__(self, responses: dict[str, str]) -> None:
        self._responses = responses
        self._text_calls: list[str] = []

    async def load_text(self, path: str) -> str:
        self._text_calls.append(path)
        if path not in self._responses:
            raise KeyError(path)
        return self._responses[path]


@pytest.fixture(autouse=True)
def _reset_template_cache():
    clear_cache()
    yield
    clear_cache()


@contextmanager
def _document_di_scope(resource_port):
    scope = DIScope()
    scope.provide(MARKDOWN_PORT_KEY, DefaultMarkdownParser())
    scope.provide(RESOURCE_PORT_KEY, resource_port)
    token = _active_di_scope.set(scope)
    try:
        yield scope
    finally:
        _active_di_scope.reset(token)
        scope.dispose()


class TestLoadMarkdownDocumentPipeline:
    @pytest.mark.asyncio
    async def test_full_pipeline(self) -> None:
        port = _FakeResourcePort({"docs/a.md": "---\ntitle: Getting Started\nsection: guide\n---\n# Intro\n\n## Sub\n"})
        with _document_di_scope(port):
            doc = await load_markdown_document("docs/a.md")
        assert doc.metadata == {"title": "Getting Started", "section": "guide"}
        assert port._text_calls == ["docs/a.md"]
        assert [(h.level, h.text, h.id) for h in doc.toc] == [(1, "Intro", "intro"), (2, "Sub", "sub")]

    @pytest.mark.asyncio
    async def test_toc_ids_match_content(self) -> None:
        port = _FakeResourcePort({"docs/a.md": "# Alpha\n\n## Beta\n\n## Beta"})
        with _document_di_scope(port):
            doc = await load_markdown_document("docs/a.md")
        heading_ids = [
            h._attrs["id"]
            for h in _walk(
                doc.content, lambda n: isinstance(n, Element) and n._tag_name in {"h1", "h2", "h3", "h4", "h5", "h6"}
            )
        ]
        assert [h.id for h in doc.toc] == heading_ids

    @pytest.mark.asyncio
    async def test_toml_metadata(self) -> None:
        port = _FakeResourcePort({"docs/a.md": '+++\ntitle = "Guide"\n[page]\norder = 2\n+++\n# Body'})
        with _document_di_scope(port):
            doc = await load_markdown_document("docs/a.md")
        assert doc.metadata == {"title": "Guide", "page": {"order": 2}}

    @pytest.mark.asyncio
    async def test_context_passed_through(self) -> None:
        port = _FakeResourcePort({"docs/a.md": "# Hello {{ name }}"})
        with _document_di_scope(port):
            doc = await load_markdown_document("docs/a.md", context={"name": "World"})
        assert doc.toc[0].text == "Hello World"

    @pytest.mark.asyncio
    async def test_transform_options_overridable(self) -> None:
        port = _FakeResourcePort({"docs/a.md": "# No Id\n\n```python\nx\n```"})
        with _document_di_scope(port):
            doc = await load_markdown_document("docs/a.md", heading_ids=False, code_blocks=False)
        assert doc.toc[0].text == "No Id"
        assert doc.toc[0].id == ""
        assert doc.content is not None
        assert not any(
            h._attrs.get("id") for h in _walk(doc.content, lambda n: isinstance(n, Element) and n._tag_name == "h1")
        )

    @pytest.mark.asyncio
    async def test_pathlib_source(self) -> None:
        port = _FakeResourcePort({"docs/a.md": "# Hi"})
        with _document_di_scope(port):
            doc = await load_markdown_document(Path("docs") / "a.md")
        assert port._text_calls == ["docs/a.md"]
        assert doc.toc[0].text == "Hi"


class TestSSRResourceRecording:
    @pytest.mark.asyncio
    async def test_resource_read_recorded(self, tmp_path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "a.md").write_text("# Recorded", encoding="utf-8")
        port = ServerResourcePort(tmp_path, frozenset({"docs/a.md"}))
        scope = DIScope()
        scope.provide(MARKDOWN_PORT_KEY, DefaultMarkdownParser())
        scope.provide(RESOURCE_PORT_KEY, port)
        token = _active_di_scope.set(scope)
        try:
            doc = await load_markdown_document("docs/a.md")
        finally:
            _active_di_scope.reset(token)
            scope.dispose()
        assert doc.toc[0].text == "Recorded"
        assert "docs/a.md" in port.get_recorded_resources()


class TestLoadMarkdownInComponentSetup:
    def test_async_setup_with_set_title(self) -> None:
        port = _FakeResourcePort({"docs/a.md": "---\ntitle: Getting Started\n---\n# Intro\n"})

        @define_component()
        async def DocPage(context):
            doc = await load_markdown_document("docs/a.md")
            context.set_title(f"{doc.metadata['title']} - WebComPy Docs")
            return create_element("article", {}, doc.content)

        scope = DIScope()
        scope.provide(MARKDOWN_PORT_KEY, DefaultMarkdownParser())
        scope.provide(RESOURCE_PORT_KEY, port)
        with TestRenderer.render(DocPage, parent_scope=scope) as result:
            html_out = result.to_html()
            assert 'id="intro"' in html_out
            assert "Intro" in html_out
            head_props = result._scope.inject(_HEAD_PROPS_KEY)
            assert "Getting Started - WebComPy Docs" in head_props.titles.values()


def _walk(node, predicate):
    results = []
    if predicate(node):
        results.append(node)
    for lst in _children_lists(node):
        for child in lst:
            results.extend(_walk(child, predicate))
    return results


def _children_lists(node):
    lists = []
    children = getattr(node, "_children", None)
    if isinstance(children, list):
        lists.append(children)
    pending = getattr(node, "_pending_children", None)
    if isinstance(pending, list):
        lists.append(pending)
    return lists
