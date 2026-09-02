from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from docs_app.docs_manifest import (
    DOCS_INDEX,
    DOCS_ROOT,
    DOCS_SECTIONS,
    flatten_pages,
    page_component_ref,
    prev_next,
    route_children,
    route_pages,
    validate_manifest,
)
from webcompy.components._generator import ComponentGenerator
from webcompy.exception import WebComPyException
from webcompy.router._lazy import LazyComponentGenerator

DOCS_APP_DIR = Path(__file__).parent.parent / "docs_app"


def _page(overrides: dict) -> dict:
    entry = {
        "label": "Test",
        "path": "/documents/basic/test",
        "source": "documents/test.md",
    }
    entry.update(overrides)
    return entry


def _section(pages: list[dict], title: str = "Basic Usage") -> dict:
    return {"title": title, "pages": pages}


class TestValidateManifest:
    def test_manifest_paths_are_unique(self) -> None:
        validate_manifest(DOCS_SECTIONS)

    def test_entry_with_both_source_and_component_rejected(self) -> None:
        entry = _page({"component": "docs_app.pages.document.test:TestPage"})
        with pytest.raises(WebComPyException, match="exactly one"):
            validate_manifest([_section([entry])])

    def test_entry_with_neither_shall_rejected(self) -> None:
        entry = {"label": "Test", "path": "/documents/basic/test"}
        with pytest.raises(WebComPyException, match="exactly one"):
            validate_manifest([_section([entry])])  # type: ignore[typeddict-item]

    def test_entry_without_label_rejected(self) -> None:
        entry = _page({})
        del entry["label"]
        with pytest.raises(WebComPyException, match="must include 'label'"):
            validate_manifest([_section([entry])])  # type: ignore[typeddict-item]

    def test_entry_without_path_rejected(self) -> None:
        entry = _page({})
        del entry["path"]
        with pytest.raises(WebComPyException, match="must include 'path'"):
            validate_manifest([_section([entry])])  # type: ignore[typeddict-item]

    def test_duplicate_paths_rejected(self) -> None:
        sections = [
            _section(
                [
                    _page({}),
                    {
                        "label": "Other",
                        "path": "/documents/basic/test",
                        "component": "docs_app.pages.document.test:TestPage",
                    },
                ]
            )
        ]
        with pytest.raises(WebComPyException, match="Duplicate"):
            validate_manifest(sections)  # type: ignore[arg-type]

    def test_path_outside_docs_root_rejected(self) -> None:
        entry = _page({"path": "/outside"})
        with pytest.raises(WebComPyException, match="must be under"):
            validate_manifest([_section([entry])])

    def test_path_equal_to_docs_root_passes_prefix_check(self) -> None:
        entry = _page({"path": DOCS_ROOT})
        with pytest.raises(WebComPyException, match="Duplicate"):
            validate_manifest([_section([entry])])

    def test_page_path_without_category_prefix_rejected(self) -> None:
        entry = _page({"path": "/documents/test"})
        with pytest.raises(WebComPyException, match="category prefix"):
            validate_manifest([_section([entry])])

    def test_unknown_section_title_rejected(self) -> None:
        with pytest.raises(WebComPyException, match="Unknown docs section title"):
            validate_manifest([_section([_page({})], title="Misc")])

    def test_section_category_order_enforced(self) -> None:
        with pytest.raises(WebComPyException, match="category order"):
            validate_manifest(
                [
                    _section([_page({"path": "/documents/advanced/test"})], title="Advanced Usage"),
                    _section([], title="Basic Usage"),
                ]
            )


class TestManifestContent:
    def test_source_files_exist_on_disk(self) -> None:
        for page in flatten_pages():
            if "source" in page:
                resource = DOCS_APP_DIR / page["source"]
                assert resource.is_file(), f"Missing markdown resource: {resource}"

    def test_all_component_references_are_importable(self) -> None:
        for page in route_pages():
            module_path, attr_name = page_component_ref(page).rsplit(":", 1)
            module = importlib.import_module(module_path)
            resolved = getattr(module, attr_name)
            assert isinstance(resolved, ComponentGenerator), f"{page_component_ref(page)} is not a component"

    def test_markdown_source_reference_derived_from_stem(self) -> None:
        for page in flatten_pages():
            if "source" not in page:
                continue
            derived = page_component_ref(page)
            stem = page["source"].rsplit("/", 1)[-1].removesuffix(".md")
            attr = "".join(part.capitalize() for part in stem.split("_")) + "Page"
            assert derived == f"docs_app.pages.document.{stem}:{attr}"

    def test_route_children_match_manifest(self) -> None:
        children = route_children()
        pages = route_pages()
        assert len(children) == len(pages)
        for child, page in zip(children, pages, strict=True):
            expected_path = "" if page["path"] == DOCS_ROOT else page["path"].removeprefix(DOCS_ROOT + "/")
            assert child["path"] == expected_path
            assert isinstance(child["component"], LazyComponentGenerator)
            assert child["component"]._import_path == page_component_ref(page)

    def test_route_children_start_with_index_route(self) -> None:
        children = route_children()
        assert children[0]["path"] == ""
        assert children[0]["component"]._import_path == DOCS_INDEX["component"]

    def test_index_excluded_from_nav_and_pager_pages(self) -> None:
        assert DOCS_INDEX["path"] not in [page["path"] for page in flatten_pages()]

    def test_sections_are_categories_in_order(self) -> None:
        assert [section["title"] for section in DOCS_SECTIONS] == ["Getting Started", "Basic Usage", "Advanced Usage"]

    def test_boundary_pages(self) -> None:
        paths = [page["path"] for page in flatten_pages()]
        assert paths[0] == "/documents/getting-started/installation"
        assert paths[-1] == "/documents/advanced/pwa"


class TestPrevNext:
    def _paths(self) -> list[str]:
        return [page["path"] for page in flatten_pages()]

    def test_first_page_has_no_prev(self) -> None:
        prev, next_page = prev_next(self._paths()[0])
        assert prev is None
        assert next_page is not None
        assert next_page["path"] == self._paths()[1]

    def test_middle_page_has_both(self) -> None:
        prev, next_page = prev_next(self._paths()[1])
        assert prev is not None
        assert prev["path"] == self._paths()[0]
        assert next_page is not None
        assert next_page["path"] == self._paths()[2]

    def test_last_page_has_no_next(self) -> None:
        prev, next_page = prev_next(self._paths()[-1])
        assert prev is not None
        assert prev["path"] == self._paths()[-2]
        assert next_page is None

    def test_trailing_slash_normalized(self) -> None:
        path = self._paths()[1]
        prev, next_page = prev_next(path + "/")
        assert prev is not None
        assert prev["path"] == self._paths()[0]
        assert next_page is not None
        assert next_page["path"] == self._paths()[2]

    def test_unknown_path_yields_no_neighbors(self) -> None:
        assert prev_next("/documents") == (None, None)
        assert prev_next("/outside") == (None, None)
