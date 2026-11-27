"""Generate a static search metadata index for ``docs_app``."""

from __future__ import annotations

import argparse
import pprint
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_DOCS_APP_DIR = _REPO_ROOT / "docs_app"
_OUTPUT_PATH = _DOCS_APP_DIR / "docs_search_index.py"

_COMPONENT_MARKDOWN_SOURCES: dict[str, str] = {
    "/documents/basic/ui-primitives": "documents/ui_primitives.md",
    "/documents/basic/overlay": "documents/overlay.md",
    "/documents/basic/disclosure": "documents/disclosure.md",
}

_EXCLUDED_HEADINGS = frozenset({"at a glance", "next steps", "notes & caveats"})
_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_HEADING_RE = re.compile(r"^(#{2,3})\s+(.+?)\s*$", re.MULTILINE)
_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_CODE_SPAN_RE = re.compile(r"`([^`]*)`")


def _clean_heading_text(raw: str) -> str:
    text = _LINK_RE.sub(r"\1", raw)
    text = _CODE_SPAN_RE.sub(r"\1", text)
    return " ".join(text.split())


def collect_search_metadata() -> dict[str, dict[str, str | tuple[str, ...]]]:
    """Collect frontmatter descriptions and H2/H3 headings per docs page path."""
    from docs_app.docs_manifest import DOCS_SECTIONS
    from webcompy.template._frontmatter import split_frontmatter

    metadata: dict[str, dict[str, str | tuple[str, ...]]] = {}
    for section in DOCS_SECTIONS:
        for page in section["pages"]:
            path = page["path"]
            source = page.get("source") or _COMPONENT_MARKDOWN_SOURCES.get(path)
            if not source:
                continue
            md_path = _DOCS_APP_DIR / source
            if not md_path.is_file():
                continue
            raw_text = md_path.read_text(encoding="utf-8")
            fm, body = split_frontmatter(raw_text)
            description = " ".join(str(fm.get("description", "")).split())
            stripped_body = _FENCE_RE.sub("", body)
            headings: list[str] = []
            seen: set[str] = set()
            for match in _HEADING_RE.finditer(stripped_body):
                heading = _clean_heading_text(match.group(2))
                lower = heading.lower()
                if not heading or lower in _EXCLUDED_HEADINGS or lower in seen:
                    continue
                seen.add(lower)
                headings.append(heading)
            metadata[path] = {
                "description": description,
                "headings": tuple(headings),
            }
    return metadata


def render_search_index_module() -> str:
    """Render the Python source for ``docs_app/docs_search_index.py``."""
    data = collect_search_metadata()
    formatted = pprint.pformat(data, width=116, sort_dicts=False)
    return "\n".join(
        [
            "from __future__ import annotations",
            "",
            "from typing import TypedDict",
            "",
            "",
            "class DocsSearchMetadata(TypedDict):",
            "    description: str",
            "    headings: tuple[str, ...]",
            "",
            "",
            f"DOCS_SEARCH_METADATA: dict[str, DocsSearchMetadata] = {formatted}",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate or verify docs_app search metadata index.")
    parser.add_argument("--check", action="store_true", help="Exit non-zero if docs_search_index.py is stale.")
    args = parser.parse_args(argv)

    rendered = render_search_index_module()
    if args.check:
        import subprocess

        fmt_proc = subprocess.run(
            [sys.executable, "-m", "ruff", "format", "--stdin-filename", str(_OUTPUT_PATH), "-"],
            input=rendered,
            text=True,
            capture_output=True,
            check=False,
        )
        expected = fmt_proc.stdout if fmt_proc.returncode == 0 else rendered
        if not _OUTPUT_PATH.is_file() or _OUTPUT_PATH.read_text(encoding="utf-8") != expected:
            print(
                "docs_app/docs_search_index.py is out of date. Run: uv run python scripts/generate_docs_search_index.py",
                file=sys.stderr,
            )
            return 1
        print("OK: docs_app/docs_search_index.py is up to date")
        return 0

    _OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
