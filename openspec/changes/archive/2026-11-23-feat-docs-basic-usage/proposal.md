# Proposal: feat-docs-basic-usage

## Why

After the restructure, `Basic Usage` holds only the three UI component pages; everything a first-day developer needs (components, template syntax, reactive state, elements, routing, forms, HTTP, styling, storage, error boundaries) is either undocumented or scattered. The tutorial (③-3) and Examples (③-9) both reference Basic pages, so the category has to land before them.

## What Changes

- Add 11 Basic Usage Markdown pages under `/documents/basic/`, in dependency order:
  - Core: `components` (`@define_component` derivation/props/slots/lifecycle/scoped-style basics/`:host` basics), `template-html` (interpolation, safe expressions, filters, `{% if %}`/`{% for %}` + `loop`, comments/`{% raw %}`, `@click`/`:ref`/`:bind`, component tags, Jinja2-subset notes), `reactive-state` (Signal/Computed/ReactiveList/ReactiveDict, `use_*` transfer-capable family, equality contract, effect basics), `elements-and-events` (html namespace, fragments, `repeat`/`switch`, keyed lists, DOM events, refs), `markdown-documents` (`render_markdown` options, `load_markdown_document`, frontmatter, `prose.css`, authoring docs pages)
  - App: `routing` (flat routes, `Router` modes, `RouterLink` + active state, path/query params, `use_router`), `forms` (`use_field`/`use_form`, validators, `:bind` wiring, plus the UI form controls `Input`/`Textarea`/`Select`/`Checkbox`/`Switch`/`Radio`/`FormField`), `http-and-async` (`HttpClient`, `use_async_result`, `AsyncResult` states, `response_type` basics), `styling-and-themes` (scoped dict, `css_text` intro, `display` kwarg, `use_theme`), `storage` (`use_local_storage`/`use_session_storage`), `error-handling` (`ErrorBoundary`, fallback/reset)
- Revise the three existing Basic pages (`ui-primitives`, `overlay`, `disclosure`) into a coherent trio: shared two-layer (headless/themed) intro on `ui-primitives`, consistent component tables, cross-links.
- Each page ends with "Next steps" links to its Advanced counterpart where topics split (nested/lazy routing, middleware DI, `sync_tabs`, reactive scoped styles, SSR error policy).
- Add a "split policy" section to `docs-site-documents`: pages whose topic spans levels keep the beginner slice in Basic, the deeper slice in Advanced, linked both ways.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `docs-site-documents`: Basic Usage coverage requirements (required page set per concern area, dependency ordering, cross-level links) and shared page-content conventions. Dedicated E2E files for new pages follow the existing `docs-e2e` requirements without spec change.

## Impact

- `docs_app/documents/` (11 new `.md`, 3 revised), `docs_app/docs_manifest.py` (entries in order), thin page wrappers under `docs_app/pages/document/`, `e2e/docs/` additions
- No framework changes; code samples validated against current APIs at authoring time

## Known Issues Addressed

None.

## Non-goals

- Advanced Usage content (③-4/5/6), tutorials (③-3), demos (③-9)
- API Reference pages (③-11) — Basic pages summarize usage, not signatures
- Rewriting Getting Started pages (done in ③-1)
