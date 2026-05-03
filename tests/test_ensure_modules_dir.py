from __future__ import annotations

from webcompy.cli._utils import ensure_webcompy_modules_dir


def test_ensure_webcompy_modules_dir_creates_directory_and_gitignore(tmp_path):
    modules_dir = tmp_path / ".webcompy_modules"
    ensure_webcompy_modules_dir(modules_dir)

    assert modules_dir.is_dir()
    gitignore = modules_dir / ".gitignore"
    assert gitignore.is_file()
    assert gitignore.read_text(encoding="utf-8") == "*\n"


def test_ensure_webcompy_modules_dir_does_not_overwrite_existing_gitignore(tmp_path):
    modules_dir = tmp_path / ".webcompy_modules"
    modules_dir.mkdir(parents=True, exist_ok=True)
    existing_gitignore = modules_dir / ".gitignore"
    existing_gitignore.write_text("*.pyc\n", encoding="utf-8")

    ensure_webcompy_modules_dir(modules_dir)

    assert existing_gitignore.read_text(encoding="utf-8") == "*.pyc\n"
