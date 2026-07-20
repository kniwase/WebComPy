from __future__ import annotations

from webcompy_cli._build import _detect_resources


def _make_pkg(tmp_path, files: dict[str, str]) -> None:
    """Create files at given POSIX-relative paths inside ``tmp_path/<pkg>``."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    for rel, content in files.items():
        target = pkg / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


class TestDetectResourcesDefaults:
    def test_default_patterns_pick_html_css_md_svg_txt(self, tmp_path) -> None:
        _make_pkg(
            tmp_path,
            {
                "templates/card.html": "<p>hi</p>",
                "styles/main.css": "body{}",
                "README.md": "# title",
                "icons/star.svg": "<svg/>",
                "notes.txt": "hello",
                "ignored/data.bin": "x",
                "scripts/app.py": "import x",
            },
        )
        result = _detect_resources(tmp_path / "pkg", None, None)
        assert result == frozenset(
            {
                "templates/card.html",
                "styles/main.css",
                "README.md",
                "icons/star.svg",
                "notes.txt",
            }
        )

    def test_excluded_paths_always_excluded(self, tmp_path) -> None:
        _make_pkg(
            tmp_path,
            {
                "__pycache__/cached.html": "x",
                ".git/HEAD.html": "x",
                ".webcompy_modules/foo.html": "x",
                "ok.html": "y",
                "data.tmp": "z",
                "module.pyc": "w",
            },
        )
        result = _detect_resources(tmp_path / "pkg", None, None)
        assert "ok.html" in result
        assert "__pycache__/cached.html" not in result
        assert ".git/HEAD.html" not in result
        assert ".webcompy_modules/foo.html" not in result
        assert "data.tmp" not in result
        assert "module.pyc" not in result

    def test_explicit_empty_list_disables_auto_detection(self, tmp_path) -> None:
        _make_pkg(tmp_path, {"a.html": "x", "b.md": "y"})
        result = _detect_resources(tmp_path / "pkg", [], None)
        assert result == frozenset()


class TestDetectResourcesCustomPatterns:
    def test_include_patterns_overrides_defaults(self, tmp_path) -> None:
        _make_pkg(
            tmp_path,
            {
                "logo.png": "x",
                "data/file.csv": "x",
                "page.html": "y",
            },
        )
        result = _detect_resources(tmp_path / "pkg", ["**/*.png", "**/*.csv"], None)
        assert result == frozenset({"logo.png", "data/file.csv"})

    def test_exclude_patterns_filters_matches(self, tmp_path) -> None:
        _make_pkg(
            tmp_path,
            {
                "public/page.html": "x",
                "internal/secret.html": "y",
            },
        )
        result = _detect_resources(
            tmp_path / "pkg",
            None,
            ["internal/**"],
        )
        assert result == frozenset({"public/page.html"})

    def test_combined_include_and_exclude(self, tmp_path) -> None:
        _make_pkg(
            tmp_path,
            {
                "templates/public.html": "x",
                "templates/draft.html": "y",
            },
        )
        result = _detect_resources(
            tmp_path / "pkg",
            ["**/*.html"],
            ["**/draft.html"],
        )
        assert result == frozenset({"templates/public.html"})

    def test_returned_paths_are_posix_relative(self, tmp_path) -> None:
        _make_pkg(tmp_path, {"sub/nested/page.html": "x"})
        result = _detect_resources(tmp_path / "pkg", None, None)
        for p in result:
            assert "\\" not in p
            assert not p.startswith("/")
