from __future__ import annotations

from pathlib import Path

from webcompy.ui._styles import get_styles_file, get_styles_files


def test_get_styles_files_returns_all_six() -> None:
    files = get_styles_files()
    assert set(files.keys()) == {
        "index.css",
        "tokens.css",
        "reset.css",
        "components.css",
        "code-block.css",
        "syntax-theme.css",
    }


def test_get_styles_files_content_matches_source() -> None:
    files = get_styles_files()
    src_dir = Path(__file__).resolve().parent.parent / "packages" / "webcompy" / "src" / "webcompy" / "ui" / "_styles"
    for name, content in files.items():
        expected = (src_dir / name).read_bytes()
        assert content == expected, f"Content mismatch for {name}"


def test_get_styles_file_known_returns_bytes() -> None:
    content = get_styles_file("tokens.css")
    assert content is not None
    assert b"--color-bg" in content


def test_get_styles_file_unknown_returns_none() -> None:
    assert get_styles_file("nope.css") is None
    assert get_styles_file("..%2Fetc%2Fpasswd") is None


def test_get_styles_file_rejects_traversal() -> None:
    assert get_styles_file("../tokens.css") is None
    assert get_styles_file("subdir/tokens.css") is None
