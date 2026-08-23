#!/usr/bin/env python3
"""Validate that universal docs reference existing OpenSpec specs and avoid retired API names.

Scans the universal documentation files (AGENTS.md, CONTRIBUTING.*, and the
`.opencode/skills/*/SKILL.md` files) and verifies:

1. Every `openspec/specs/<name>` reference resolves to an existing
   `openspec/specs/<name>/spec.md`.
2. No retired API name from the blocklist appears in the docs (the blocklist
   encodes rename history; a rename adds the old name here so docs referencing
   it fail validation).

Usage:
    python3 scripts/check-doc-spec-refs.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECS_DIR = ROOT / "openspec" / "specs"

DOC_FILES = [
    ROOT / "AGENTS.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "CONTRIBUTING.ja.md",
    *(ROOT / ".opencode" / "skills").glob("*/SKILL.md"),
    *(ROOT / "docs_app" / "documents").glob("*.md"),
]

RETIRED_API_NAMES = [
    "webcompy.reactive",
    "ReactiveBase",
    "ReactiveNode",
    "ReactiveEdge",
    "ReactiveReceivable",
    "ReadonlyReactive",
    "__reactive_members__",
    "Reactive(",
    "Reactive[",
]

RETIRED_PATTERNS = [
    r"\bapp\.rpc\.register\b",
    r"\bapp\.rpc\.procedure\b",
    r"\brpc\.call\b",
    r"\brpc\.notify\b",
    r"\brpc\.stream\b",
    r"\bregister_subscription\b",
    r"\bRpcWsClient\.call\b",
    r"\bRpcWsClient\.subscribe\b",
]

SPEC_REF_RE = re.compile(r"openspec/specs/([\w-]+)(?:/spec\.md)?")
RETIRED_RE = re.compile("|".join(re.escape(name) for name in RETIRED_API_NAMES) + "|" + "|".join(RETIRED_PATTERNS))


def main() -> int:
    errors: list[str] = []

    for path in DOC_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for match in SPEC_REF_RE.finditer(text):
            name = match.group(1)
            if not (SPECS_DIR / name / "spec.md").exists():
                line = text.count("\n", 0, match.start()) + 1
                errors.append(f"{path.relative_to(ROOT)}:{line}: dangling spec reference `{name}`")
        for match in RETIRED_RE.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            errors.append(f"{path.relative_to(ROOT)}:{line}: retired API name `{match.group(0)}`")

    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        print(f"{len(errors)} violation(s) found", file=sys.stderr)
        return 1

    print("OK: all spec references resolve and no retired API names present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
