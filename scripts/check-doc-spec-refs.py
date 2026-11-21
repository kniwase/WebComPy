#!/usr/bin/env python3
"""Validate doc spec references, retired API names, AGENTS.md size, and SSOT symlinks.

Scans universal documentation files (AGENTS.md, CONTRIBUTING.*,
openspec/SPEC_INDEX.md, .agents/skills/*/SKILL.md, and docs_app/documents/*.md)
and verifies:

1. Every `openspec/specs/<name>` reference resolves to an existing
   `openspec/specs/<name>/spec.md`.
2. No retired API name from the blocklist appears in the docs.
3. `AGENTS.md` stays at or below 24,000 UTF-8 bytes so rule loaders with
   per-file caps ingest the full file without truncation.
4. `CLAUDE.md` is a relative symlink to `AGENTS.md`, and `.claude/skills/`,
   `.claude/commands/`, and `.opencode/commands/` are physical directories
   mirroring `.agents/` 1-to-1 via non-dangling relative symlinks.

Usage:
    python3 scripts/check-doc-spec-refs.py
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECS_DIR = ROOT / "openspec" / "specs"
AGENTS_MD_MAX_BYTES = 24_000

DOC_FILES = [
    ROOT / "AGENTS.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "CONTRIBUTING.ja.md",
    ROOT / "openspec" / "SPEC_INDEX.md",
    *(ROOT / ".agents" / "skills").glob("*/SKILL.md"),
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


def _check_agents_size(errors: list[str]) -> None:
    agents_md = ROOT / "AGENTS.md"
    if not agents_md.exists():
        errors.append("AGENTS.md is missing")
        return
    size = len(agents_md.read_bytes())
    if size > AGENTS_MD_MAX_BYTES:
        errors.append(f"AGENTS.md exceeds {AGENTS_MD_MAX_BYTES} bytes ({size} bytes)")


def _check_root_symlinks(errors: list[str]) -> None:
    agents_md = ROOT / "AGENTS.md"
    claude_md = ROOT / "CLAUDE.md"
    if not claude_md.is_symlink():
        errors.append("CLAUDE.md must be a relative symlink to AGENTS.md")
        return
    target = os.readlink(claude_md)
    if target != "AGENTS.md":
        errors.append(f"CLAUDE.md symlink target `{target}` != expected `AGENTS.md`")
    if not claude_md.exists() or claude_md.resolve() != agents_md.resolve():
        errors.append("CLAUDE.md symlink does not resolve to AGENTS.md")


def _expected_ssot_entries(ssot_dir: Path, kind: str) -> set[str]:
    if kind == "dir":
        return {p.name for p in ssot_dir.iterdir() if p.is_dir() and (p / "SKILL.md").exists()}
    return {p.name for p in ssot_dir.iterdir() if p.is_file() and p.suffix == ".md"}


def _check_symlink_mirrors(errors: list[str]) -> None:
    mirrors = [
        (ROOT / ".agents" / "skills", ROOT / ".claude" / "skills", "dir", "../../.agents/skills"),
        (ROOT / ".agents" / "commands", ROOT / ".claude" / "commands", "file", "../../.agents/commands"),
        (ROOT / ".agents" / "commands", ROOT / ".opencode" / "commands", "file", "../../.agents/commands"),
    ]
    for ssot_dir, mirror_dir, kind, expected_prefix in mirrors:
        rel_mirror = mirror_dir.relative_to(ROOT)
        if not ssot_dir.is_dir():
            errors.append(f"SSOT directory `{ssot_dir.relative_to(ROOT)}` is missing")
            continue
        if mirror_dir.is_symlink():
            errors.append(f"{rel_mirror} must be a physical directory, not a symlink")
            continue
        if not mirror_dir.is_dir():
            errors.append(f"mirror directory `{rel_mirror}` is missing")
            continue

        expected = _expected_ssot_entries(ssot_dir, kind)
        actual_entries = {p.name: p for p in mirror_dir.iterdir()}

        for missing in sorted(expected - actual_entries.keys()):
            errors.append(f"{rel_mirror}/{missing}: missing symlink to {expected_prefix}/{missing}")
        for extra in sorted(actual_entries.keys() - expected):
            errors.append(f"{rel_mirror}/{extra}: unexpected entry not in {ssot_dir.relative_to(ROOT)}")

        for name in sorted(expected & actual_entries.keys()):
            entry = actual_entries[name]
            rel_entry = entry.relative_to(ROOT)
            expected_target = f"{expected_prefix}/{name}"
            if not entry.is_symlink():
                errors.append(f"{rel_entry} must be a relative symlink to `{expected_target}`")
                continue
            target = os.readlink(entry)
            if target != expected_target:
                errors.append(f"{rel_entry}: symlink target `{target}` != expected `{expected_target}`")
            if not entry.exists() or entry.resolve() != (ssot_dir / name).resolve():
                errors.append(f"{rel_entry}: symlink does not resolve to {(ssot_dir / name).relative_to(ROOT)}")


def main() -> int:
    """Run all universal doc, size, and symlink checks."""
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

    _check_agents_size(errors)
    _check_root_symlinks(errors)
    _check_symlink_mirrors(errors)

    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        print(f"{len(errors)} violation(s) found", file=sys.stderr)
        return 1

    print("OK: all spec references resolve, AGENTS.md within size cap, and SSOT symlinks valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
