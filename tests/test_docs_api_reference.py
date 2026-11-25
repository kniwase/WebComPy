from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"


def _import_script(module_name: str, filename: str):
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_check_docstrings():
    return _import_script("check_docstrings_mod", "check-docstrings.py")


def _load_api_surface():
    return _import_script("_api_surface", "_api_surface.py")


def _load_generator():
    return _import_script("generate_api_reference", "generate_api_reference.py")


def _write_fixture_package(
    root: Path, *, signature: str = "def greet(name: str, excited: bool = False) -> str:"
) -> Path:
    pkg = root / "sample_pkg"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text(
        '"""Sample package."""\n\n'
        "from sample_pkg._core import DEFAULT_PREFIX, greet\n\n"
        '__all__ = ["DEFAULT_PREFIX", "greet"]\n',
        encoding="utf-8",
    )
    (pkg / "_core.py").write_text(
        '"""Core implementation module."""\n\n'
        'DEFAULT_PREFIX = "Hello"\n'
        '"""Default greeting prefix."""\n\n\n'
        f"{signature}\n"
        '    """Format a greeting message.\n\n'
        "    Args:\n"
        "        name: Recipient name.\n"
        "        excited: Whether to emphasize the greeting.\n\n"
        "    Returns:\n"
        "        Rendered greeting string.\n\n"
        "    Raises:\n"
        "        ValueError: When name is empty.\n"
        '    """\n'
        "    if not name:\n"
        '        raise ValueError("empty name")\n'
        '    suffix = "!" if excited else "."\n'
        '    return f"{DEFAULT_PREFIX}, {name}{suffix}"\n',
        encoding="utf-8",
    )
    return pkg


class TestCheckDocstringsAndSurface:
    def test_live_check_docstrings_passes(self) -> None:
        mod = _load_check_docstrings()
        assert mod.main([]) == 0

    def test_detects_missing_docstring_and_reexports(self, tmp_path: Path) -> None:
        pkg = tmp_path / "mini_pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text(
            '"""Mini package."""\n\nfrom mini_pkg._impl import documented, undocumented\n',
            encoding="utf-8",
        )
        (pkg / "_impl.py").write_text(
            '"""Impl module."""\n\n'
            "def documented() -> None:\n"
            '    """Okay."""\n\n'
            "def undocumented() -> None:\n"
            "    return None\n",
            encoding="utf-8",
        )
        mod = _load_check_docstrings()
        missing_baseline = tmp_path / "missing_baseline.txt"
        assert mod.main(["--root", str(pkg), "--baseline", str(missing_baseline)]) == 1

        surface = _load_api_surface().collect_public_surface(roots=[pkg], important_internals=[])
        assert set(surface) == {"mini_pkg._impl:documented", "mini_pkg._impl:undocumented"}
        assert surface["mini_pkg._impl:documented"].parsed_docstring.summary == "Okay."

    def test_detects_pep224_constant_and_forbidden_comment(self, tmp_path: Path) -> None:
        pkg = tmp_path / "const_pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text(
            '"""Const package."""\n\nfrom const_pkg._defs import TOKEN\n',
            encoding="utf-8",
        )
        forbidden_word = "open" + "spec"
        (pkg / "_defs.py").write_text(
            f'"""Defs."""\n\nTOKEN = "abc"\n"""Constant token."""\n\n# {forbidden_word} artifact note\n',
            encoding="utf-8",
        )
        mod = _load_check_docstrings()
        missing_baseline = tmp_path / "missing_baseline.txt"
        assert mod.main(["--root", str(pkg), "--baseline", str(missing_baseline)]) == 1

        (pkg / "_defs.py").write_text(
            '"""Defs."""\n\nTOKEN = "abc"\n"""Constant token."""\n',
            encoding="utf-8",
        )
        assert mod.main(["--root", str(pkg), "--baseline", str(missing_baseline)]) == 0


class TestApiReferenceGenerator:
    def _fixture_pages(self):
        gen = _load_generator()
        return (
            gen.ApiPageSpec(
                filename="api_sample.md",
                slug="sample",
                title="Sample API",
                description="Fixture API reference page.",
                clusters=(gen.ApiClusterRule("Core", ("sample_pkg",)),),
                default_intro="Generated fixture intro.",
                default_see_also="- See conceptual guide.",
            ),
        )

    def test_generates_skeleton_and_preserves_author_regions(self, tmp_path: Path) -> None:
        gen = _load_generator()
        pkg = _write_fixture_package(tmp_path)
        out_dir = tmp_path / "docs"
        pages = self._fixture_pages()

        written = gen.generate_reference(output_dir=out_dir, roots=[pkg], important_internals=[], pages=pages)
        page_path = out_dir / "api_sample.md"
        assert written == [page_path]

        initial = page_path.read_text(encoding="utf-8")
        assert "### greet" in initial
        assert "def greet(name: str, excited: bool = False) -> str" in initial
        assert "**Args:**" in initial
        assert "- `name`: Recipient name." in initial
        assert "**Returns:** Rendered greeting string." in initial
        assert "**Raises:**" in initial
        assert "- `ValueError`: When name is empty." in initial
        assert "### DEFAULT_PREFIX" in initial
        assert gen.check_reference(output_dir=out_dir, roots=[pkg], important_internals=[], pages=pages) == []

        custom_page = initial.replace(
            "<!-- author:start:intro -->\nGenerated fixture intro.\n<!-- author:end:intro -->",
            "<!-- author:start:intro -->\nHand-authored custom intro.\n<!-- author:end:intro -->",
        )
        page_path.write_text(custom_page, encoding="utf-8")

        assert gen.check_reference(output_dir=out_dir, roots=[pkg], important_internals=[], pages=pages) == []

        bare_author = (
            "---\ntitle: Sample API\ndescription: Custom\n---\n\n# Sample API\n\n"
            "<!-- author:start -->\nCustom bare author note.\n<!-- author:end -->\n"
        )
        page_path.write_text(bare_author, encoding="utf-8")
        gen.generate_reference(output_dir=out_dir, roots=[pkg], important_internals=[], pages=pages)
        regenerated_bare = page_path.read_text(encoding="utf-8")
        assert "<!-- author:start -->\nCustom bare author note.\n<!-- author:end -->" in regenerated_bare
        assert "### greet" in regenerated_bare

    def test_check_detects_signature_drift_with_page_and_symbol(
        self,
        tmp_path: Path,
        capsys,
    ) -> None:
        gen = _load_generator()
        pkg = _write_fixture_package(tmp_path)
        out_dir = tmp_path / "docs"
        pages = self._fixture_pages()

        gen.generate_reference(output_dir=out_dir, roots=[pkg], important_internals=[], pages=pages)

        _write_fixture_package(tmp_path, signature="def greet(name: str, polite: bool = True) -> str:")

        drifts = gen.check_reference(output_dir=out_dir, roots=[pkg], important_internals=[], pages=pages)
        assert len(drifts) == 1
        drift_path, drift_symbols = drifts[0]
        assert drift_path == out_dir / "api_sample.md"
        assert "greet" in drift_symbols

        page_path = out_dir / "api_sample.md"
        custom_intro = page_path.read_text(encoding="utf-8").replace(
            "Generated fixture intro.",
            "Preserved custom notes.",
        )
        page_path.write_text(custom_intro, encoding="utf-8")

        gen.generate_reference(output_dir=out_dir, roots=[pkg], important_internals=[], pages=pages)
        updated = page_path.read_text(encoding="utf-8")
        assert "Preserved custom notes." in updated
        assert "polite: bool = True" in updated
        assert gen.check_reference(output_dir=out_dir, roots=[pkg], important_internals=[], pages=pages) == []

        assert gen.main(["--check", "--output-dir", str(out_dir)]) == 1
        captured = capsys.readouterr()
        assert "error:" in captured.err


class TestLiveApiReferenceCoverage:
    def test_every_public_symbol_covered_exactly_once(self) -> None:
        surf = _load_api_surface()
        gen = _load_generator()
        surface = surf.collect_public_surface()
        assigned = gen.assign_symbols_to_pages(surface)
        assigned_keys = [sym.key for clusters in assigned.values() for syms in clusters.values() for sym in syms]
        assert len(assigned_keys) == len(set(assigned_keys)) == len(surface)

        docs_dir = ROOT / "docs_app" / "documents"
        key_pattern = re.compile(r"(?:Key: |\| )`([^`:]+:[^`]+)`")
        occurrences: dict[str, list[str]] = {key: [] for key in surface}
        for page in gen.API_PAGES:
            text = (docs_dir / page.filename).read_text(encoding="utf-8")
            for found_key in key_pattern.findall(text):
                if found_key in occurrences:
                    occurrences[found_key].append(page.filename)

        missing = [k for k, pages_list in occurrences.items() if len(pages_list) == 0]
        duplicates = {k: pages_list for k, pages_list in occurrences.items() if len(pages_list) > 1}
        assert not missing, f"Missing API symbols: {missing[:10]}"
        assert not duplicates, f"Duplicate API symbols: {list(duplicates.items())[:10]}"

    def test_committed_api_reference_has_no_drift(self) -> None:
        gen = _load_generator()
        assert gen.check_reference() == []
