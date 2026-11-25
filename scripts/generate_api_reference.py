#!/usr/bin/env python3
"""Generate and verify WebComPy API Reference Markdown pages from the public API surface."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _api_surface import (  # noqa: E402
    IMPORTANT_INTERNALS,
    PACKAGE_ROOTS,
    ROOT,
    DocstringSections,
    ResolvedMember,
    ResolvedSymbol,
    clean_rst_markup,
    collect_public_surface,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

DEFAULT_OUTPUT_DIR = ROOT / "docs_app" / "documents"

GENERATED_START = "<!-- generated:start -->"
GENERATED_END = "<!-- generated:end -->"
_AUTHOR_NAMED_RE = re.compile(r"<!-- author:start:([a-zA-Z0-9_-]+) -->(.*?)<!-- author:end:\1 -->", re.DOTALL)
_AUTHOR_BARE_RE = re.compile(r"<!-- author:start -->(.*?)<!-- author:end -->", re.DOTALL)
_SECTION_HEADING_RE = re.compile(r"^### (.+)$", re.MULTILINE)
_TABLE_ROW_RE = re.compile(r"^\| `([^`]+)` \| (.+) \|$", re.MULTILINE)
_ARG_ITEM_RE = re.compile(r"^([A-Za-z0-9_*]+)\s*:\s*(.*)$")


@dataclass(frozen=True)
class ApiClusterRule:
    """Clustering rule assigning symbols matching module prefixes to a topic section."""

    heading: str
    prefixes: tuple[str, ...]
    exclude_prefixes: tuple[str, ...] = ()
    compact_table: bool = False


@dataclass(frozen=True)
class ApiPageSpec:
    """Page definition mapping canonical API modules into one reference document."""

    filename: str
    slug: str
    title: str
    description: str
    clusters: tuple[ApiClusterRule, ...]
    default_intro: str
    default_see_also: str


API_PAGES: tuple[ApiPageSpec, ...] = (
    ApiPageSpec(
        filename="api_core_app_components.md",
        slug="app-and-components",
        title="App & Components API",
        description="API reference for webcompy.app, webcompy.components, webcompy.plugin, webcompy.exception, and webcompy.utils.",
        clusters=(
            ApiClusterRule("Application & Configuration", ("webcompy.app",)),
            ApiClusterRule("Components & Lifecycle", ("webcompy.components",)),
            ApiClusterRule("Plugins", ("webcompy.plugin",)),
            ApiClusterRule("Exceptions & Utilities", ("webcompy.exception", "webcompy.utils")),
        ),
        default_intro="Reference for application bootstrap, configuration, components, lifecycle hooks, plugins, exceptions, and shared utilities.",
        default_see_also="- Concept guides: [Components](/documents/basic/components), [Plugins](/documents/advanced/plugins), and [Project Configuration](/documents/server/project-configuration).",
    ),
    ApiPageSpec(
        filename="api_core_template_markdown.md",
        slug="template-and-markdown",
        title="Template & Markdown API",
        description="API reference for webcompy.template including HTML template rendering, AST nodes, CSS helpers, and Markdown parsing.",
        clusters=(
            ApiClusterRule(
                "Template Rendering & AST",
                ("webcompy.template",),
                exclude_prefixes=("webcompy.template._css_template", "webcompy.template._markdown_document"),
            ),
            ApiClusterRule("CSS Helpers", ("webcompy.template._css_template",)),
            ApiClusterRule("Markdown Documents", ("webcompy.template._markdown_document",)),
        ),
        default_intro="Reference for the HTML template engine, expressions, directive AST types, CSS helpers, and Markdown document loading.",
        default_see_also="- Concept guides: [Template & HTML](/documents/basic/template-html) and [Markdown Documents](/documents/basic/markdown-documents).",
    ),
    ApiPageSpec(
        filename="api_core_reactivity.md",
        slug="reactivity",
        title="Reactivity API",
        description="API reference for webcompy.signal reactive containers, computed signals, effects, collections, and composables.",
        clusters=(
            ApiClusterRule(
                "Signals, Computed & Collections",
                (
                    "webcompy.signal._base",
                    "webcompy.signal._computed",
                    "webcompy.signal._dict",
                    "webcompy.signal._list",
                    "webcompy.signal._readonly",
                ),
            ),
            ApiClusterRule(
                "Effects & Composables",
                ("webcompy.signal._composable", "webcompy.signal._effect"),
            ),
            ApiClusterRule("Internal Reactivity Graph", ("webcompy.signal._graph",)),
        ),
        default_intro="Reference for mutable signals, computed values, reactive collections, readonly signals, effects, and reactive composables.",
        default_see_also="- Concept guides: [Reactive State](/documents/basic/reactive-state), [Read-only Signals and Events](/documents/advanced/readonly-signal), and [Signal Stream](/documents/advanced/signal-stream).",
    ),
    ApiPageSpec(
        filename="api_core_elements_routing.md",
        slug="elements-and-routing",
        title="Elements, Routing & DI API",
        description="API reference for webcompy.elements, webcompy.router, and webcompy.di.",
        clusters=(
            ApiClusterRule(
                "Elements, Control Flow & Head",
                ("webcompy.elements",),
                exclude_prefixes=("webcompy.elements.html.html_tags",),
            ),
            ApiClusterRule("Router & Navigation", ("webcompy.router",)),
            ApiClusterRule("Dependency Injection", ("webcompy.di",)),
            ApiClusterRule("HTML Tag Factories", ("webcompy.elements.html.html_tags",), compact_table=True),
        ),
        default_intro="Reference for element construction, control-flow primitives, document head helpers, client-side routing, dependency injection, and HTML tag factories.",
        default_see_also="- Concept guides: [Elements & Events](/documents/basic/elements-and-events), [Routing](/documents/basic/routing), and [Dependency Injection Deep Dive](/documents/advanced/dependency-injection-deep-dive).",
    ),
    ApiPageSpec(
        filename="api_core_data.md",
        slug="data",
        title="Data, Forms & i18n API",
        description="API reference for webcompy.ajax, webcompy.aio, webcompy.forms, webcompy.storage, webcompy.events, webcompy.resources, webcompy.realtime, and webcompy.i18n.",
        clusters=(
            ApiClusterRule("HTTP, Async & Resources", ("webcompy.ajax", "webcompy.aio", "webcompy.resources")),
            ApiClusterRule("Forms & Validation", ("webcompy.forms",)),
            ApiClusterRule("Storage & Browser Events", ("webcompy.storage", "webcompy.events")),
            ApiClusterRule("Realtime (SSE & WebSocket)", ("webcompy.realtime",)),
            ApiClusterRule("Internationalization (i18n)", ("webcompy.i18n",)),
        ),
        default_intro="Reference for HTTP requests, async utilities, resources, form state and validation, browser storage, document events, realtime streams, and i18n.",
        default_see_also="- Concept guides: [HTTP & Async](/documents/basic/http-and-async), [Forms](/documents/basic/forms), [Storage](/documents/basic/storage), [Typed Realtime](/documents/advanced/typed-realtime), and [Internationalization](/documents/advanced/i18n).",
    ),
    ApiPageSpec(
        filename="api_ui.md",
        slug="ui",
        title="UI & Theme API",
        description="API reference for webcompy.ui components, headless primitives, theme management, styles, and code blocks.",
        clusters=(
            ApiClusterRule("Themed Components", ("webcompy.ui.components",)),
            ApiClusterRule("Headless Primitives", ("webcompy.ui.headless",)),
            ApiClusterRule(
                "Theme, Composables & Styles",
                ("webcompy.ui.theme", "webcompy.ui.composables", "webcompy.ui._styles"),
            ),
            ApiClusterRule("Code Block & Syntax Highlighting", ("webcompy.ui.code_block",)),
        ),
        default_intro="Reference for WebComPy UI themed components, accessible headless primitives, theme controls, UI composables, CSS helpers, and code block lexers.",
        default_see_also="- Concept guides: [UI Primitives](/documents/basic/ui-primitives), [Styling & Themes](/documents/basic/styling-and-themes), and [UI Headless Contract](/documents/advanced/ui-headless-contract).",
    ),
    ApiPageSpec(
        filename="api_server_cli.md",
        slug="server-and-cli",
        title="Server, CLI, RPC & Ports API",
        description="API reference for webcompy_server, webcompy_cli, webcompy.rpc, webcompy.hydration, and webcompy.ports.",
        clusters=(
            ApiClusterRule(
                "Server & CLI Configuration",
                ("webcompy_server", "webcompy_cli"),
                exclude_prefixes=("webcompy_server.rpc", "webcompy_server.ports"),
            ),
            ApiClusterRule("Typed RPC (Client & Server)", ("webcompy.rpc", "webcompy_server.rpc")),
            ApiClusterRule("Hydration & State Transfer", ("webcompy.hydration",)),
            ApiClusterRule("Port Interfaces & Server Implementations", ("webcompy.ports", "webcompy_server.ports")),
        ),
        default_intro="Reference for ASGI server integration, CLI configuration types, typed RPC contracts and dispatch, SSR/hydration metadata, and environment ports.",
        default_see_also="- Concept guides: [CLI Reference](/documents/server/cli-reference), [ASGI Integration](/documents/server/asgi-integration), [RPC Contracts](/documents/advanced/rpc-contracts), and [Hydration & Transfer](/documents/advanced/hydration-and-transfer).",
    ),
    ApiPageSpec(
        filename="api_testing.md",
        slug="testing",
        title="Testing API",
        description="API reference for webcompy_testing component rendering, ASGI helpers, fake ports, and browser test runner.",
        clusters=(
            ApiClusterRule(
                "Test Renderer, ASGI Client & Fake Ports",
                ("webcompy_testing",),
                exclude_prefixes=("webcompy_testing.browser_runner",),
            ),
            ApiClusterRule("Browser Test Runner", ("webcompy_testing.browser_runner",)),
        ),
        default_intro="Reference for component test rendering, fake environment ports, DI scope helpers, ASGI test clients, and browser test harness utilities.",
        default_see_also="- Concept guides: [Testing](/documents/server/testing) and [Serving Modes](/documents/server/serving-modes).",
    ),
)


def _matches_prefix(module: str, prefixes: tuple[str, ...], exclude_prefixes: tuple[str, ...] = ()) -> bool:
    for ex in exclude_prefixes:
        if module == ex or module.startswith(ex + "."):
            return False
    return any(module == prefix or module.startswith(prefix + ".") for prefix in prefixes)


def assign_symbols_to_pages(
    surface: dict[str, ResolvedSymbol],
    pages: Sequence[ApiPageSpec] = API_PAGES,
) -> dict[str, dict[str, list[ResolvedSymbol]]]:
    """Partition resolved public symbols cleanly into page clusters.

    Args:
        surface: Canonical public symbol table keyed by ``module:name``.
        pages: Page definitions specifying module prefix clusters.

    Returns:
        Nested mapping ``{filename: {cluster_heading: [ResolvedSymbol, ...]}}``.

    Raises:
        ValueError: If any symbol matches zero clusters or more than one cluster.

    """
    assigned: dict[str, dict[str, list[ResolvedSymbol]]] = {
        page.filename: {cluster.heading: [] for cluster in page.clusters} for page in pages
    }

    unmapped: list[str] = []
    ambiguous: list[tuple[str, list[str]]] = []

    for sym in surface.values():
        matches: list[tuple[str, str]] = []
        for page in pages:
            for cluster in page.clusters:
                if _matches_prefix(sym.def_module, cluster.prefixes, cluster.exclude_prefixes):
                    matches.append((page.filename, cluster.heading))
        if not matches:
            unmapped.append(sym.key)
        elif len(matches) > 1:
            ambiguous.append((sym.key, [f"{p}:{c}" for p, c in matches]))
        else:
            page_name, cluster_name = matches[0]
            assigned[page_name][cluster_name].append(sym)

    if unmapped or ambiguous:
        problems: list[str] = []
        if unmapped:
            problems.append("unmapped symbols: " + ", ".join(unmapped[:20]))
        if ambiguous:
            formatted = "; ".join(f"{k} -> {v}" for k, v in ambiguous[:10])
            problems.append(f"ambiguous symbols: {formatted}")
        raise ValueError("API surface page mapping error: " + " | ".join(problems))

    for page_clusters in assigned.values():
        for symbols in page_clusters.values():
            symbols.sort(key=lambda s: (s.name.lower(), s.name, s.def_module))

    return assigned


def _display_symbol_heading(sym: ResolvedSymbol, page_name_counts: dict[str, int]) -> str:
    if page_name_counts.get(sym.name, 0) > 1 and sym.exports:
        primary_mod, primary_name = sym.exports[-1]
        short_mod = primary_mod.rsplit(".", 1)[-1]
        if short_mod != primary_mod:
            return f"{short_mod}.{primary_name}"
        return f"{primary_mod}.{primary_name}"
    return sym.name


def _format_google_section(header: str, content: str) -> list[str]:
    if header in {"Args", "Attributes", "Raises"}:
        entries: list[tuple[str, list[str]]] = []
        fallback_lines: list[str] = []
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if not line.startswith((" ", "\t")):
                match = _ARG_ITEM_RE.match(stripped)
                if match:
                    desc = [match.group(2).strip()] if match.group(2).strip() else []
                    entries.append((match.group(1), desc))
                    continue
            if entries:
                entries[-1][1].append(stripped)
            else:
                fallback_lines.append(stripped)
        if entries and not fallback_lines:
            rendered = [f"**{header}:**", ""]
            for name, parts in entries:
                desc_text = clean_rst_markup(" ".join(parts)).strip()
                rendered.append(f"- `{name}`: {desc_text}" if desc_text else f"- `{name}`")
            return rendered

    paragraphs = [
        clean_rst_markup(" ".join(line.strip() for line in para.splitlines() if line.strip()))
        for para in re.split(r"\n\s*\n", content.strip())
        if para.strip()
    ]
    if len(paragraphs) == 1:
        return [f"**{header}:** {paragraphs[0]}"]
    out: list[str] = [f"**{header}:**"]
    for para in paragraphs:
        out.extend(["", para])
    return out


def _render_docstring_body(parsed: DocstringSections) -> list[str]:
    out: list[str] = []
    if parsed.summary:
        out.append(parsed.summary)
    if parsed.description:
        out.extend(["", parsed.description])
    for header, content in parsed.sections:
        out.append("")
        out.extend(_format_google_section(header, content))
    return out


def _render_member_lines(member: ResolvedMember, *, nested: bool = False) -> list[str]:
    header = f"#### Nested `{member.name}` ({member.kind})" if nested else f"**`{member.name}`** ({member.kind})"
    lines = [header, ""]
    lines.extend(["```python", member.signature, "```"])
    if member.parsed_docstring.summary:
        lines.extend(["", member.parsed_docstring.summary])
    for section_name, content in member.parsed_docstring.sections:
        lines.append("")
        lines.extend(_format_google_section(section_name, content))
    for sub in member.nested_members:
        lines.append("")
        lines.extend(_render_member_lines(sub, nested=True))
    return lines


def _render_symbol_block(sym: ResolvedSymbol, heading: str) -> list[str]:
    lines: list[str] = [f"### {heading}", ""]
    lines.extend(["```python", sym.signature, "```", ""])

    export_refs = ", ".join(f"`from {mod} import {name}`" for mod, name in sym.exports)
    meta_parts = [f"Key: `{sym.key}`"]
    if not sym.is_internal and export_refs:
        meta_parts.append(f"Exports: {export_refs}")
    else:
        meta_parts.append("Internal allowlist entry")
    lines.append(" · ".join(meta_parts))

    body_lines = _render_docstring_body(sym.parsed_docstring)
    if body_lines:
        lines.append("")
        lines.extend(body_lines)

    if sym.members:
        lines.extend(["", "#### Members", ""])
        for idx, member in enumerate(sym.members):
            if idx > 0:
                lines.append("")
            lines.extend(_render_member_lines(member))

    return lines


def _render_compact_table(symbols: list[ResolvedSymbol]) -> list[str]:
    lines = [
        "| Symbol | Key | Signature | Summary |",
        "| --- | --- | --- | --- |",
    ]
    for sym in symbols:
        sig = sym.signature.replace("|", "\\|").replace("`", "\\`")
        summary = sym.parsed_docstring.summary.replace("|", "\\|")
        lines.append(f"| `{sym.name}` | `{sym.key}` | `{sig}` | {summary} |")
    return lines


def render_generated_section(
    page: ApiPageSpec,
    clusters: dict[str, list[ResolvedSymbol]],
) -> str:
    """Render the generated Markdown body inside ``<!-- generated:start/end -->``.

    Args:
        page: Page definition metadata.
        clusters: Clustered symbol lists belonging to ``page``.

    Returns:
        Full generated block text including start/end HTML comment markers.

    """
    name_counts: dict[str, int] = {}
    for syms in clusters.values():
        for sym in syms:
            name_counts[sym.name] = name_counts.get(sym.name, 0) + 1

    blocks: list[str] = [GENERATED_START]
    for cluster in page.clusters:
        syms = clusters.get(cluster.heading, [])
        if not syms:
            continue
        blocks.extend(["", f"## {cluster.heading}", ""])
        if cluster.compact_table:
            blocks.extend(_render_compact_table(syms))
        else:
            for idx, sym in enumerate(syms):
                if idx > 0:
                    blocks.append("")
                heading = _display_symbol_heading(sym, name_counts)
                blocks.extend(_render_symbol_block(sym, heading))
    blocks.extend(["", GENERATED_END])
    return "\n".join(blocks)


def extract_author_regions(markdown_text: str) -> dict[str, str]:
    """Extract preserved author prose blocks keyed by region identifier.

    Args:
        markdown_text: Existing page Markdown content.

    Returns:
        Dictionary mapping named regions (and ``"__bare__"`` if unnamed) to raw inner content.

    """
    regions: dict[str, str] = {}
    for match in _AUTHOR_NAMED_RE.finditer(markdown_text):
        regions[match.group(1)] = match.group(2)
    bare_match = _AUTHOR_BARE_RE.search(markdown_text)
    if bare_match is not None:
        regions["__bare__"] = bare_match.group(1)
    return regions


def render_page_markdown(
    page: ApiPageSpec,
    clusters: dict[str, list[ResolvedSymbol]],
    existing_text: str | None = None,
) -> str:
    """Render a complete API Reference Markdown page while preserving author regions.

    Args:
        page: Page definition metadata.
        clusters: Clustered symbol lists belonging to ``page``.
        existing_text: Existing Markdown content on disk, if present.

    Returns:
        Complete page Markdown string ready to write or diff.

    """
    generated_block = render_generated_section(page, clusters)
    if existing_text is not None and GENERATED_START in existing_text and GENERATED_END in existing_text:
        start_idx = existing_text.index(GENERATED_START)
        end_idx = existing_text.index(GENERATED_END) + len(GENERATED_END)
        return existing_text[:start_idx] + generated_block + existing_text[end_idx:]

    regions = extract_author_regions(existing_text) if existing_text is not None else {}
    intro_body = regions.get("intro")
    if intro_body is not None:
        intro_section = f"<!-- author:start:intro -->{intro_body}<!-- author:end:intro -->"
    elif "__bare__" in regions:
        intro_section = f"<!-- author:start -->{regions['__bare__']}<!-- author:end -->"
    else:
        intro_section = f"<!-- author:start:intro -->\n{page.default_intro}\n<!-- author:end:intro -->"

    see_also_body = regions.get("see-also")
    if see_also_body is not None:
        see_also_section = f"<!-- author:start:see-also -->{see_also_body}<!-- author:end:see-also -->"
    else:
        see_also_section = f"<!-- author:start:see-also -->\n{page.default_see_also}\n<!-- author:end:see-also -->"

    lines = [
        "---",
        f"title: {page.title}",
        f"description: {page.description}",
        "---",
        "",
        f"# {page.title}",
        "",
        intro_section,
        "",
        generated_block,
        "",
        "## Next steps",
        "",
        see_also_section,
        "",
    ]
    return "\n".join(lines)


def _extract_symbol_chunks(generated_block: str) -> dict[str, str]:
    chunks: dict[str, str] = {}
    matches = list(_SECTION_HEADING_RE.finditer(generated_block))
    for idx, match in enumerate(matches):
        name = match.group(1).strip()
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(generated_block)
        chunk = generated_block[start:end].strip()
        chunks[name] = chunk
    for row_match in _TABLE_ROW_RE.finditer(generated_block):
        sym_name = row_match.group(1).strip()
        chunks[sym_name] = row_match.group(0).strip()
    return chunks


def _extract_generated_slice(markdown_text: str) -> str:
    if GENERATED_START in markdown_text and GENERATED_END in markdown_text:
        start = markdown_text.index(GENERATED_START)
        end = markdown_text.index(GENERATED_END) + len(GENERATED_END)
        return markdown_text[start:end]
    return markdown_text


def _drifted_symbols(disk_text: str, expected_text: str) -> list[str]:
    old_chunks = _extract_symbol_chunks(_extract_generated_slice(disk_text))
    new_chunks = _extract_symbol_chunks(_extract_generated_slice(expected_text))
    drifted: list[str] = []
    for sym in sorted(set(old_chunks) | set(new_chunks)):
        if old_chunks.get(sym) != new_chunks.get(sym):
            drifted.append(sym)
    return drifted


def generate_reference(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    roots: list[Path] = PACKAGE_ROOTS,
    important_internals: list[str] = IMPORTANT_INTERNALS,
    pages: Sequence[ApiPageSpec] = API_PAGES,
) -> list[Path]:
    """Generate or update all API Reference Markdown pages on disk.

    Args:
        output_dir: Directory where ``api_*.md`` pages are written.
        roots: Package source root directories to resolve.
        important_internals: Additional allowlisted internal symbols.
        pages: Page partition definitions.

    Returns:
        List of written or updated Markdown file paths.

    """
    surface = collect_public_surface(roots=roots, important_internals=important_internals)
    assigned = assign_symbols_to_pages(surface, pages=pages)
    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for page in pages:
        target = output_dir / page.filename
        existing = target.read_text(encoding="utf-8") if target.is_file() else None
        rendered = render_page_markdown(page, assigned[page.filename], existing_text=existing)
        if existing != rendered:
            target.write_text(rendered, encoding="utf-8")
            written.append(target)
    return written


def check_reference(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    roots: list[Path] = PACKAGE_ROOTS,
    important_internals: list[str] = IMPORTANT_INTERNALS,
    pages: Sequence[ApiPageSpec] = API_PAGES,
) -> list[tuple[Path, list[str]]]:
    """Verify committed API Reference pages match the current public API surface.

    Args:
        output_dir: Directory containing committed ``api_*.md`` pages.
        roots: Package source root directories to resolve.
        important_internals: Additional allowlisted internal symbols.
        pages: Page partition definitions.

    Returns:
        List of ``(page_path, drifted_symbols)`` pairs for every drifted or missing page.

    """
    surface = collect_public_surface(roots=roots, important_internals=important_internals)
    assigned = assign_symbols_to_pages(surface, pages=pages)
    drifts: list[tuple[Path, list[str]]] = []

    for page in pages:
        target = output_dir / page.filename
        clusters = assigned[page.filename]
        expected = render_page_markdown(
            page, clusters, existing_text=target.read_text(encoding="utf-8") if target.is_file() else None
        )
        if not target.is_file():
            all_syms = [sym.name for syms in clusters.values() for sym in syms]
            drifts.append((target, all_syms))
            continue
        disk_text = target.read_text(encoding="utf-8")
        if disk_text != expected:
            drifts.append((target, _drifted_symbols(disk_text, expected)))

    return drifts


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser for ``generate_api_reference``.

    Returns:
        Configured ``ArgumentParser`` instance.

    """
    parser = argparse.ArgumentParser(
        prog="generate_api_reference",
        description="Generate or verify WebComPy API Reference Markdown skeletons.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="check committed API reference files for drift without modifying disk",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="target directory for generated api_*.md files",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run skeleton generation or drift verification from the command line.

    Args:
        argv: Optional CLI argument list.

    Returns:
        Process exit status code (0 on success, 1 on drift or mapping error).

    """
    args = build_arg_parser().parse_args(argv)
    output_dir = args.output_dir.resolve()

    if args.check:
        drifts = check_reference(output_dir=output_dir)
        if not drifts:
            print("OK: API reference pages match the current public API surface")
            return 0
        for path, symbols in drifts:
            try:
                rel = path.relative_to(ROOT)
            except ValueError:
                rel = path
            sym_list = ", ".join(symbols) if symbols else "<missing or structural drift>"
            print(f"error: {rel}: drifted symbols: {sym_list}", file=sys.stderr)
        print(f"{len(drifts)} API reference page(s) out of date", file=sys.stderr)
        return 1

    written = generate_reference(output_dir=output_dir)
    if written:
        for path in written:
            try:
                rel = path.relative_to(ROOT)
            except ValueError:
                rel = path
            print(f"updated {rel}")
    else:
        print("OK: all API reference pages are already up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
