from __future__ import annotations

import re
from pathlib import Path

DOCS_DIR = Path(__file__).parent.parent / "docs_app" / "documents"
_LINK_TARGET_RE = re.compile(r"\]\(([^)\s]+)")


def test_docs_bodies_do_not_link_to_md_sources() -> None:
    failures: list[str] = []
    for md_file in sorted(DOCS_DIR.glob("*.md")):
        for lineno, line in enumerate(md_file.read_text(encoding="utf-8").splitlines(), start=1):
            for match in _LINK_TARGET_RE.finditer(line):
                if match.group(1).endswith(".md"):
                    failures.append(f"{md_file.name}:{lineno}: {match.group(1)}")
    assert not failures, "docs bodies must link to rendered-site URLs:\n" + "\n".join(failures)
