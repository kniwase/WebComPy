from __future__ import annotations

from docs_app.components.docs_page import _toc_href


class TestTocHref:
    def test_preserves_trailing_slash(self) -> None:
        href = _toc_href("/documents/getting-started/installation/", "install-with-uv-recommended")
        assert href == "/documents/getting-started/installation/#install-with-uv-recommended"

    def test_without_trailing_slash(self) -> None:
        href = _toc_href("/documents/getting-started/installation", "install-with-uv-recommended")
        assert href == "/documents/getting-started/installation#install-with-uv-recommended"

    def test_relative_current_path_normalized(self) -> None:
        href = _toc_href("documents/getting-started/installation", "intro")
        assert href == "/documents/getting-started/installation#intro"

    def test_root_path(self) -> None:
        assert _toc_href("/", "intro") == "/#intro"
