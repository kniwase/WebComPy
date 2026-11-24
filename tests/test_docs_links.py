from __future__ import annotations

import re
from pathlib import Path

from docs_app.docs_manifest import DOCS_INDEX, DOCS_ROOT, flatten_pages

DOCS_DIR = Path(__file__).parent.parent / "docs_app" / "documents"
_LINK_TARGET_RE = re.compile(r"\]\(([^)\s]+)")


def _body_link_targets() -> list[tuple[str, int, str]]:
    md_files = sorted(DOCS_DIR.glob("*.md"))
    assert md_files, f"No docs Markdown bodies found under {DOCS_DIR}"
    targets: list[tuple[str, int, str]] = []
    for md_file in md_files:
        for lineno, line in enumerate(md_file.read_text(encoding="utf-8").splitlines(), start=1):
            for match in _LINK_TARGET_RE.finditer(line):
                targets.append((md_file.name, lineno, match.group(1)))
    return targets


def test_docs_bodies_do_not_link_to_md_sources() -> None:
    failures = [f"{name}:{lineno}: {target}" for name, lineno, target in _body_link_targets() if target.endswith(".md")]
    assert not failures, "docs bodies must link to rendered-site URLs:\n" + "\n".join(failures)


def test_docs_body_links_resolve_to_manifest_paths() -> None:
    valid_paths = {DOCS_INDEX["path"], *(page["path"] for page in flatten_pages())}
    failures: list[str] = []
    for name, lineno, target in _body_link_targets():
        path = target.split("#", 1)[0]
        if path != DOCS_ROOT and not path.startswith(DOCS_ROOT + "/"):
            continue
        if path.rstrip("/") not in valid_paths:
            failures.append(f"{name}:{lineno}: {target}")
    assert not failures, "docs body links must resolve to manifest page paths:\n" + "\n".join(failures)


def test_basic_and_advanced_split_policy_pairs_are_reciprocal() -> None:
    pairs = [
        (
            "basic_routing.md",
            "/documents/basic/routing",
            "routing_deep_dive.md",
            "/documents/advanced/routing-deep-dive",
        ),
        (
            "basic_forms.md",
            "/documents/basic/forms",
            "ui_headless_contract.md",
            "/documents/advanced/ui-headless-contract",
        ),
        (
            "basic_storage.md",
            "/documents/basic/storage",
            "persistence_patterns.md",
            "/documents/advanced/persistence-patterns",
        ),
        (
            "basic_components.md",
            "/documents/basic/components",
            "custom_elements.md",
            "/documents/advanced/custom-elements",
        ),
        (
            "basic_http_async.md",
            "/documents/basic/http-and-async",
            "typed_api_deep_dive.md",
            "/documents/advanced/typed-api-deep-dive",
        ),
        (
            "ui_primitives.md",
            "/documents/basic/ui-primitives",
            "ui_headless_contract.md",
            "/documents/advanced/ui-headless-contract",
        ),
        (
            "overlay.md",
            "/documents/basic/overlay",
            "ui_headless_contract.md",
            "/documents/advanced/ui-headless-contract",
        ),
        (
            "disclosure.md",
            "/documents/basic/disclosure",
            "ui_headless_contract.md",
            "/documents/advanced/ui-headless-contract",
        ),
        (
            "basic_http_async.md",
            "/documents/basic/http-and-async",
            "middleware.md",
            "/documents/advanced/middleware",
        ),
    ]
    by_file: dict[str, set[str]] = {}
    for name, _lineno, target in _body_link_targets():
        by_file.setdefault(name, set()).add(target.split("#", 1)[0].rstrip("/"))

    for basic_file, basic_path, adv_file, adv_path in pairs:
        assert adv_path in by_file.get(basic_file, set()), f"{basic_file} missing link to {adv_path}"
        assert basic_path in by_file.get(adv_file, set()), f"{adv_file} missing back-link to {basic_path}"
