# WebComPy Specification Index

`openspec/specs/` is the single source of truth for WebComPy requirements and API naming. Always start with `openspec/specs/overview/spec.md` and `openspec/specs/architecture/spec.md`, then consult the tables below for subsystem specs and invariants.

## Framework Invariants

These are rules that apply across the entire codebase. Violations are 🔴 Must Fix.
The authoritative requirements live in the owning specs — see the File → Spec Mapping
table below and the `.agents/skills/webcompy-review/SKILL.md` invariant headings for
the per-area reference.

- **Dual Environment** — `architecture/spec.md`
- **No New Globals** — `architecture/spec.md`, `di-scope/spec.md`
- **RenderContext Isolation** — `render-context/spec.md`
- **Reactive Contracts** — `reactive/spec.md`, `effect/spec.md`
- **Element Signal Ownership** — `elements/spec.md`, `reactive/spec.md`
- **Event Handler Leaks** — `elements/spec.md`
- **Error Handling** — `error-handling/spec.md`
- **Lifecycle Ordering** — `components/spec.md`, `async-rendering/spec.md`
- **Async Rendering Pipeline** — `async-rendering/spec.md`
- **DI Scope Rules** — `di-scope/spec.md`
- **Hydration** — `hydration-data-transfer/spec.md`, `elements/spec.md`, `async-rendering/spec.md`
- **Hydration Adopt & Render** — `elements/spec.md`, `async-rendering/spec.md`
- **Hydration Mismatch Diagnostics** — `elements/spec.md`, `async-rendering/spec.md`
- **Scheduler Render-Task Scoping** — `async-scheduler/spec.md`
- **Metadata Type-Tag Decoding** — `typed-response/spec.md`, `typed-api-client/spec.md`
- **JSON-RPC Allowlist Decoding** — `json-rpc/spec.md`
- **RPC Contract Binding** — `rpc-contracts/spec.md`, `json-rpc/spec.md`, `rpc-websocket/spec.md`, `rpc-streaming/spec.md`
- **RPC WebSocket Rejoin & Cursor Integrity** — `rpc-websocket/spec.md`, `json-rpc/spec.md`
- **RouterView Depth and Level Reuse** — `router/spec.md`
- **Teleport Anchor Slot, SSR Block Emission and Rejection** — `teleport/spec.md`
- **Custom Element Components** — `custom-element-components/spec.md`, `components/spec.md`
- **UI Primitives Two-Layer Contract** — `ui-primitives/spec.md`
- **Overlay Instance Identity & Toggle Ownership** — `ui-overlay/spec.md`
- **Form Control Binding & FormField Context Confinement** — `ui-form-controls/spec.md`
- **Disclosure State & Panel Persistence** — `ui-disclosure/spec.md`, `ui-primitives/spec.md`
- **Transition Sequence Contract** — `transition/spec.md`
- **Composable Usage** — `composables/spec.md`
- **Realtime Connection Lifecycle** — `sse-composable/spec.md`, `websocket-composable/spec.md`, `sse-parser/spec.md`
- **FetchPort Streaming Contract** — `port-abstraction/spec.md`
- **Fetch/RPC Middleware Ordering and Delegation** — `fetch-middleware/spec.md`, `rpc-middleware/spec.md`
- **Realtime Type Allowlist Decoding** — `typed-realtime/spec.md`
- **Scoped CSS** — `scoped-css-incremental/spec.md`, `reactive-scoped-style/spec.md`
- **Head VDOM** — `head-vdom/spec.md`
- **Loading Screen DOM Contract** — `loading-screen/spec.md`
- **Node Cache Strict is-None Check** — `async-rendering/spec.md`
- **Browser Test Tier Importability** — `browser-test-harness/spec.md`
- **Dual-Run Eligibility Classification** — `browser-dualrun/spec.md`
- **Probe Authority & Hard Gate** — `browser-probes/spec.md`
- **PyExec Harness Confinement** — `inspect-pyexec/spec.md`
- **No Overview Gap List** — `overview/spec.md`
- **Docstring Coverage & OpenSpec Reference Ban** — `api-docstrings/spec.md`
- **PWA Worker Generation, Precache & Scope** — `pwa/spec.md`
- **I18n Cookie-Only Locale Parity** — `i18n/spec.md`
- **Theme & Design Token Contrast Parity** — `theme-system/spec.md`, `design-tokens/spec.md`, `demo-iframe-isolation/spec.md`

## File → Spec Mapping

When modifying code, read the relevant specs from `openspec/specs/`:

| Changed files | Specs to read |
|---|---|
| `webcompy/signal/` | `reactive/spec.md`, `effect/spec.md`, `signal-value-transfer/spec.md`, `error-handling/spec.md` |
| `webcompy/signal/_readonly.py` | `readonly-signal/spec.md`, `reactive/spec.md` |
| `webcompy/events/` | `readonly-signal/spec.md` |
| `webcompy/storage/` | `composables/spec.md` |
| `webcompy/ui/_styles/` | `css-architecture/spec.md`, `design-tokens/spec.md`, `markdown-document/spec.md`, `ui-overlay/spec.md`, `code-block/spec.md` |
| `webcompy/ui/theme/` | `theme-system/spec.md`, `design-tokens/spec.md` |
| `webcompy/ui/headless/`, `webcompy/ui/components/` | `ui-primitives/spec.md` |
| `webcompy/ui/headless/_overlay_utils.py`, `webcompy/ui/headless/_modal.py`, `_drawer.py`, `_dropdown.py`, `_toast.py`, `webcompy/ui/components/_modal.py`, `_drawer.py`, `_dropdown.py`, `_toast.py`, `webcompy/ui/composables/_toast.py` | `ui-overlay/spec.md`, `ui-primitives/spec.md` |
| `webcompy/ui/headless/_input.py`, `_textarea.py`, `_select.py`, `_checkbox.py`, `_switch.py`, `_radio.py`, `_form_field.py`, `_form_field_context.py`, `_form_utils.py`, `webcompy/ui/components/_input.py`, `_textarea.py`, `_select.py`, `_checkbox.py`, `_switch.py`, `_radio.py`, `_form_field.py` | `ui-form-controls/spec.md`, `ui-primitives/spec.md`, `forms/spec.md`, `elements/spec.md` |
| `webcompy/ui/headless/_dom_id.py`, `_tabs.py`, `_collapse.py`, `_accordion.py`, `_alert.py`, `_progress.py`, `_badge.py`, `_skeleton.py`, `_card.py`, `webcompy/ui/components/_tabs.py`, `_collapse.py`, `_accordion.py`, `_alert.py`, `_progress.py`, `_badge.py`, `_skeleton.py`, `_card.py`, `webcompy/ui/_styles/primitives.css` | `ui-disclosure/spec.md`, `ui-primitives/spec.md`, `transition/spec.md` |
| `webcompy/ui/code_block/` | `code-block/spec.md`, `syntax-highlight-lexers/spec.md` |
| `webcompy/template/_css_parser.py`, `webcompy/template/_css_template.py` | `template-engine/spec.md` |
| `webcompy/template/`, `webcompy/template/_expression.py` | `template-engine/spec.md`, `markdown-document/spec.md` |
| `webcompy/template/_markdown_default.py` | `template-engine/spec.md`, `markdown-conformance/spec.md` |
| `webcompy/template/_markdown_for.py` | `template-engine/spec.md` |
| `tests/conformance/` | `markdown-conformance/spec.md`, `template-engine/spec.md`, `test-execution-paths/spec.md` |
| `webcompy/components/` | `components/spec.md`, `composables/spec.md`, `async-rendering/spec.md`, `reactive-scoped-style/spec.md`, `async-component-setup/spec.md`, `signal-value-transfer/spec.md`, `typed-api-client/spec.md`, `error-handling/spec.md`, `custom-element-components/spec.md` |
| `webcompy/components/_css_utils.py` | `components/spec.md`, `reactive-scoped-style/spec.md`, `custom-element-components/spec.md` |
| `webcompy/app/` | `app/spec.md`, `app-lifecycle/spec.md`, `app-config/spec.md`, `render-context/spec.md`, `scoped-css-incremental/spec.md`, `async-rendering/spec.md`, `app-styles/spec.md`, `async-scheduler/spec.md`, `error-handling/spec.md`, `loading-screen/spec.md`, `theme-system/spec.md` |
| `webcompy/elements/` | `elements/spec.md`, `list-reconciliation/spec.md`, `nested-dynamic-element/spec.md`, `dict-repeat-overload/spec.md`, `head-vdom/spec.md`, `element-preserve-children/spec.md`, `async-rendering/spec.md`, `client-only/spec.md`, `suspense/spec.md`, `async-scheduler/spec.md`, `error-handling/spec.md` |
| `webcompy/elements/_bind.py` | `elements/spec.md` |
| `webcompy/elements/types/_error_boundary.py` | `error-handling/spec.md` |
| `webcompy/elements/types/_suspense.py` | `suspense/spec.md`, `async-scheduler/spec.md`, `error-handling/spec.md` |
| `webcompy/elements/types/_dynamic.py` | `async-scheduler/spec.md` |
| `webcompy/elements/types/_fragment.py` | `elements/spec.md` |
| `webcompy/elements/types/_switch.py` | `elements/spec.md`, `async-rendering/spec.md` |
| `webcompy/elements/types/_teleport.py` | `teleport/spec.md`, `elements/spec.md`, `async-rendering/spec.md` |
| `webcompy/elements/types/_transition.py`, `webcompy/ports/_transition.py`, `webcompy/ports/_browser/_transition.py`, `webcompy/ports/_media_query.py`, `webcompy_server/ports/_transition.py` | `transition/spec.md`, `port-abstraction/spec.md` |
| `webcompy/forms/` | `forms/spec.md` |
| `webcompy/i18n/` | `i18n/spec.md`, `di-scope/spec.md`, `port-abstraction/spec.md`, `reactive/spec.md`, `template-engine/spec.md` |
| `webcompy/hydration/` | `hydration-data-transfer/spec.md`, `transfer-codec/spec.md`, `signal-value-transfer/spec.md`, `payload-compression/spec.md`, `typed-api-client/spec.md`, `typed-response/spec.md`, `async-rendering/spec.md` |
| `webcompy/router/` | `router/spec.md`, `router-hooks/spec.md`, `error-handling/spec.md` |
| `webcompy/router/_scroll.py` | `scroll-restoration/spec.md` |
| `webcompy/rpc/` | `json-rpc/spec.md`, `rpc-websocket/spec.md`, `rpc-streaming/spec.md`, `rpc-contracts/spec.md`, `rpc-middleware/spec.md` |
| `webcompy/rpc/_contracts.py` | `rpc-contracts/spec.md`, `json-rpc/spec.md`, `rpc-websocket/spec.md`, `rpc-streaming/spec.md` |
| `webcompy/rpc/_ws_client.py` | `rpc-websocket/spec.md`, `websocket-composable/spec.md`, `typed-realtime/spec.md`, `typed-api-client/spec.md`, `typed-response/spec.md`, `json-rpc/spec.md`, `rpc-streaming/spec.md` |
| `webcompy/rpc/_client.py` | `json-rpc/spec.md`, `rpc-streaming/spec.md`, `rpc-middleware/spec.md` |
| `webcompy/rpc/_stream.py` | `rpc-streaming/spec.md` |
| `webcompy/ports/_browser/` | `browser-api/spec.md`, `custom-element-components/spec.md` |
| `webcompy/ports/_event_source.py`, `webcompy/ports/_browser/_event_source.py` | `port-abstraction/spec.md`, `port-provisioning/spec.md`, `sse-composable/spec.md` |
| `webcompy/ports/_websocket.py`, `webcompy/ports/_browser/_websocket.py` | `port-abstraction/spec.md`, `port-provisioning/spec.md`, `websocket-composable/spec.md` |
| `webcompy/ports/` | `port-abstraction/spec.md`, `port-provisioning/spec.md`, `async-scheduler/spec.md`, `scroll-restoration/spec.md`, `custom-element-components/spec.md`, `fetch-middleware/spec.md` |
| `webcompy/ports/_markdown.py` | `port-abstraction/spec.md` |
| `webcompy/ports/_resource.py`, `webcompy/ports/_browser/_resource.py`, `webcompy_server/ports/_resource.py` | `resource-port/spec.md` |
| `webcompy_server/ports/` | `virtual-dom/spec.md`, `server-fetch-asgi/spec.md`, `asgi-embed/spec.md`, `async-scheduler/spec.md`, `custom-element-components/spec.md` |
| `webcompy_server/__init__.py` | `asgi-embed/spec.md`, `server-fetch-asgi/spec.md` |
| `webcompy_server/_context.py`, `webcompy_server/_html.py`, `webcompy_server/_teleport_emission.py` | `teleport/spec.md`, `virtual-dom/spec.md`, `elements/spec.md`, `async-scheduler/spec.md`, `app-lifecycle/spec.md`, `loading-screen/spec.md`, `pwa/spec.md`, `cli/spec.md`, `css-architecture/spec.md` |
| `webcompy_server/contrib/` | `typed-response/spec.md` |
| `webcompy_server/rpc/` | `json-rpc/spec.md`, `rpc-websocket/spec.md`, `rpc-streaming/spec.md` |
| `webcompy_server/rpc/_dispatcher.py` | `json-rpc/spec.md`, `rpc-streaming/spec.md` |
| `webcompy_server/rpc/_streams.py` | `rpc-streaming/spec.md` |
| `webcompy_server/rpc/_ws_endpoint.py` | `rpc-websocket/spec.md`, `rpc-streaming/spec.md` |
| `webcompy/plugin/` | `plugin-system/spec.md`, `plugin-script/spec.md`, `fetch-middleware/spec.md`, `rpc-middleware/spec.md` |
| `webcompy/di/` | `di-scope/spec.md`, `di-injection/spec.md`, `dependency-resolver/spec.md` |
| `webcompy/ajax/`, `webcompy/aio/` | `async/spec.md`, `async-rendering/spec.md`, `async-scheduler/spec.md`, `typed-api-client/spec.md`, `typed-response/spec.md`, `signal-stream/spec.md`, `fetch-middleware/spec.md` |
| `webcompy/realtime/` | `sse-composable/spec.md`, `websocket-composable/spec.md`, `signal-stream/spec.md`, `typed-realtime/spec.md`, `reactive/spec.md`, `di-scope/spec.md` |
| `webcompy/realtime/_typed.py` | `typed-realtime/spec.md`, `typed-response/spec.md`, `typed-api-client/spec.md` |
| `webcompy/ajax/_serde.py` | `typed-api-client/spec.md`, `typed-response/spec.md` |
| `webcompy/ajax/_sse.py` | `sse-parser/spec.md` |
| `webcompy/ports/_fetch.py`, `webcompy/ports/_browser/_fetch.py` | `port-abstraction/spec.md` |
| `webcompy_server/ports/_fetch.py` | `port-abstraction/spec.md` |
| `webcompy_cli/` | `cli/spec.md`, `project-config/spec.md`, `config-separation/spec.md`, `inspect-cli/spec.md`, `ssg-via-ssr/spec.md`, `asgi-embed/spec.md`, `async-scheduler/spec.md`, `error-handling/spec.md`, `json-rpc/spec.md`, `loading-screen/spec.md`, `pwa/spec.md` |
| `webcompy_testing/` | `testing-module/spec.md`, `async-scheduler/spec.md`, `custom-element-components/spec.md` |
| `tests/` (unit), `e2e/` (E2E) | `test-execution-paths/spec.md`, `markdown-document/spec.md` |
| `tests/browser/`, `webcompy_testing/browser_runner/` | `browser-test-harness/spec.md`, `test-execution-paths/spec.md` |
| `webcompy_cli/_browser_test_harness.py` | `browser-test-harness/spec.md`, `cli/spec.md` |
| `webcompy_cli/_browser_probes.py`, `webcompy_cli/_dualrun_pytest_plugin.py`, `tests/.dualrun/` | `browser-dualrun/spec.md`, `browser-probes/spec.md` |
| `webcompy_cli/_version_sweep.py`, `scripts/run-browser-version-sweep.sh` | `browser-probes/spec.md` |
| `webcompy_cli/_inspect_pyexec.py`, `webcompy_testing/browser_runner/` (evaluate) | `inspect-pyexec/spec.md`, `browser-test-harness/spec.md` |
| `tests/browser/probes/` | `browser-probes/spec.md`, `browser-test-harness/spec.md` |
| `docs_app/` | `docs-site-home/spec.md`, `docs-site-documents/spec.md`, `docs-migration-guide/spec.md`, `docs-api-reference/spec.md`, `docs-e2e/spec.md`, `demo-iframe-isolation/spec.md`, `loading-screen/spec.md` |
| `scripts/check-docstrings.py`, `scripts/_api_surface.py`, `[tool.pydoclint]` in `pyproject.toml` | `api-docstrings/spec.md`, `docs-api-reference/spec.md` |
| `scripts/generate_api_reference.py` | `docs-api-reference/spec.md` |
| other directories (`exception/`, `utils/`) | `overview/spec.md`, `architecture/spec.md` |

Always start with `openspec/specs/overview/spec.md` and `openspec/specs/architecture/spec.md`.

## Current Specs

| Spec | Description |
|---|---|
| `overview` | Framework purpose, core promises, development lifecycle; Purpose-section governance (no gap lists) |
| `architecture` | Dual-environment model, project structure, CLI workflows, hydration |
| `reactive` | Reactive state primitives and change propagation |
| `effect` | Side-effecting functions with automatic reactive dependency tracking |
| `components` | Component definition styles, props, slots, scoped CSS, lifecycle |
| `custom-element-components` | Named Light DOM custom elements: wrapper boundaries, multiple roots, document-connection hooks, observed attributes, registration/hydration ordering |
| `composables` | Reusable stateful logic functions for function-style component setup |
| `i18n` | Reactive internationalization core: DI-managed `I18nManager` with locale Signal and `use_i18n` controller, dot-path catalogs with `{param}` interpolation, CLDR plurals via a built-in table with pipe shorthand and opt-in Babel adapter, fallback chain, and cookie-only locale persistence with deterministic SSR/hydration parity |
| `template-engine` | HTML template parsing and variable interpolation that produces reactive WebComPy Element trees |
| `markdown-document` | Markdown frontmatter parsing, `load_markdown_document` (with scrollable table wrapping and opt-in heading permalinks), TOC extraction (excluding anchor glyphs), opt-in `prose.css` typography preset and overflow containment |
| `markdown-conformance` | Byte-exact cmark-gfm compatibility of `DefaultMarkdownParser` HTML output, strict-xfail suite |
| `elements` | DOM element creation, reactive updates, conditional/list rendering |
| `list-reconciliation` | Key-based reconciliation for efficient DOM reuse |
| `nested-dynamic-element` | Nesting of `repeat` and `switch` at arbitrary depth |
| `dict-repeat-overload` | Efficient DOM reconciliation for `ReactiveDict` with `repeat()` |
| `element-preserve-children` | `:preserve_children` attribute for externally-managed child DOM nodes |
| `error-handling` | `ErrorBoundary` element, error propagation walk, SSR-tolerant/SSG-fail-fast policy, RouterView implicit boundaries |
| `forms` | Field wrapper, built-in validators, Form aggregation, `:bind` integration |
| `head-vdom` | Declarative head element management via `HeadElement` VDOM |
| `router` | Client-side routing, hash/history modes, path params, RouterLink active state |
| `router-hooks` | Navigation lifecycle callbacks |
| `scroll-restoration` | Window scroll management across navigations: scroll-to-top on push, position restore on Back/Forward, `scrollRestoration="manual"`, config opt-out, post-render scheduling with bounded retry |
| `app` | Application bootstrapping, hydration, head management |
| `app-lifecycle` | App start/run/shutdown across browser and server entry points |
| `app-config` | AppConfig, ServerConfig, GenerateConfig dataclasses |
| `config-separation` | Separation of browser-relevant config from server-only build config |
| `project-config` | Two-file project configuration |
| `cli` | Dev server, SSG, project scaffolding, configuration, prod/SSG static and UI CSS cache busting (`?v=<hash>`), and immutable wheel/WASM cache headers |
| `browser-api` | Browser environment detection and API abstraction |
| `port-abstraction` | Typed, injectable port ABCs replacing monolithic `browser` |
| `fetch-middleware` | Stackable `FetchMiddleware` chains around `FetchPort.fetch/stream`: registries on DI, plugin hooks, `next(response=...)` interception with hydration/blocked-path delegation, header-commit-time streaming resolution |
| `resource-port` | Async `ResourcePort` ABC + `ServerResourcePort`/`BrowserResourcePort` for app-package resource files (replaces legacy `load_asset`) |
| `virtual-dom` | Server-side virtual DOM tree for SSG and testing, with CSS selector resolution over the virtual tree |
| `async` | Async operations, HTTP client integration |
| `async-scheduler` | `AsyncSchedulerPort` task scheduling interface with render-task scoping (`schedule(coro, *, render=False)` / `await_pending(*, only_render=False)`); browser drain gates the hydration reveal while non-render tasks stay fire-and-forget |
| `typed-api-client` | Schema-driven typed deserialization (`from_json`) and `response_type` typed requests on `HttpClient`, including validation strictness and container/scalar coercion |
| `typed-response` | Metadata-augmented responses: framework-neutral `encode_with_meta`, JSON Pointer type-tag maps, header (`X-WebComPy-Transfer-Meta`) and body (`__webcompy_transfer_meta__`) wire modes, `TypedJSONResponse` FastAPI contrib, and client-side metadata consumption layered on schema-driven coercion |
| `async-component-setup` | Async component definition support via two-phase initialization during `_render()` |
| `async-rendering` | Async rendering pipeline, async lifecycle hooks, sequential sibling rendering |
| `client-only` | ClientOnly element for browser-only rendering with optional SSR fallback |
| `di-scope` | Resolution boundary and lifecycle for DI values |
| `di-injection` | Provide/inject pattern for scoped dependency resolution |
| `dependency-resolver` | Classification of app dependencies for browser deployment |
| `e2e-testing` | Browser-based validation of WebComPy apps |
| `docs-e2e` | E2E testing for docs_app pages |
| `docs-site-home` | docs_app Home landing page: four-band landing layout (hero, balanced feature-card grid without margin drift, quick-start teaser, footer), deduplication from installation guides, and symmetric CodeBlock vertical spacing via docs_app stylesheet |
| `docs-site-documents` | docs_app documentation section: category section model manifest (`Getting Started` / `Guides` / `Basic Usage` / `Advanced Usage` / `Server & Tooling` / `Examples` / `Migration` / `API Reference`), manifest-driven routes and grouped scrollable dropdown, deduplicated layout CSS, inline `DocsRoot` skip-link styling, viewport-bounded sticky sidebar and TOC, Prev/Next paging, `resource_transfer="used"` payload minimization, Cloudflare Pages immutable `_headers`, client-side search, ARIA landmarks/controls/`404` recovery layout, copyable `CodeBlock` and heading permalinks, and current `@define_component()` example convention |
| `docs-migration-guide` | Migration guides under `/documents/migration/`: FastAPI + Jinja2 architecture shift, ASGI strangler strategies, live mocked before/after comparison, conversion tables, exact template compatibility/error matrix, and phased exit-criteria checklist |
| `docs-api-reference` | Generated-plus-authored `/documents/api/` reference skeletons (`scripts/_api_surface.py`, `scripts/generate_api_reference.py`, `--check` CI drift gate, full public API coverage across all four packages, author-region preservation, and non-duplication with conceptual guides) |
| `internal-naming` | Correct English spelling of internal/private API identifiers |
| `package-kind` | `PackageKind` enum for classifying browser dependencies |
| `lockfile` | Reproducible builds via `webcompy-lock.json` |
| `pyscript-bundle` | Local serving of complete PyScript offline bundle |
| `wheel-builder` | PEP 427-compliant Python wheel production |
| `project-local-cache` | Per-app `.webcompy_modules/` cache for runtime assets |
| `plugin-system` | Extension mechanism via `WebComPyPlugin` base class |
| `plugin-script` | Declarative loading of JavaScript resources |
| `reactive-dropdown` | Demonstration of reactive dropdown menus |
| `demo-iframe-isolation` | Isolated iframe PyScript contexts for demos, parent theme sync, design-token contrast parity, component-scoped style boundaries, and responsive auto-sizing |
| `inspect-cli` | CLI tool for browser inspection of WebComPy apps |
| `json-rpc` | JSON-RPC 2.0 dispatcher, procedure registry, metadata extension, allowlist type decoding, typed browser client |
| `rpc-middleware` | Stackable `RpcMiddleware` chains over HTTP RPC: typed args/headers context with batch/streaming metadata, validated `next(response=...)` synthesis through `_resolve_single`, registries on DI and plugin hooks |
| `rpc-contracts` | Declarative RPC contracts (`Procedure`/`StreamingProcedure`/`Subscription`/`RpcCall`/`batch`/`notify`/`RpcTransport`/`RpcHttpClient`/`bind`) with registration validation and transport dispatch |
| `rpc-streaming` | Finite, call-scoped streaming RPC responses: generator-function procedure registration with element-schema extraction, `RpcStream` typed async iterator with state and close semantics, HTTP SSE and WebSocket transport, mid-stream error propagation, client cancellation, and SSR degradation to an empty finished stream |
| `rpc-websocket` | JSON-RPC 2.0 over WebSocket: WS dispatcher endpoint, `RpcWsClient`, subscription streams with cursors, rejoin/catch-up/`resync_required`, application-level heartbeat, `force_close` |
| `scoped-css-incremental` | Per-component `<style data-webcompy-cid="...">` injection |
| `loading-screen` | Boot-time loading experience: presentation modes, interaction policies, staged progress, grace period and fade-out timing, dormant/wake-up treatment, stall watchdog, accessibility, custom-template toolkit contract |
| `reactive-scoped-style` | Per-component reactive scoped style via dedicated style element |
| `app-styles` | App-level reactive style injection via `@layer webcompy-dynamic` |
| `css-architecture` | Fixed CSS `@layer` order (`reset, tokens, components, prose, webcompy-scope`), layered reset/components/code-block stylesheets, unlayered dynamic styles, and versioned `index.css` link placement before scoped styles |
| `design-tokens` | Light/dark CSS custom property token system (`tokens.css` / `_tokens.py`), WCAG 2.1 AA contrast, `:root` `color-scheme` and native form control defaults |
| `theme-system` | Reactive `ThemeManager`, explicit `color-scheme` declarations, `webcompy-theme` cookie persistence, static/SSG theme hydration parity |
| `testing-module` | TestRenderer, fake ports, scope helpers for browserless testing |
| `server-fetch-asgi` | Self-site fetch via ASGI transport during SSR/SSG, page-route blocking |
| `asgi-embed` | Embedding a WebComPy serving app into a host ASGI application, including fetch-port wiring (`root_app`), `base_url`/prefix alignment, and blocked-path behavior |
| `suspense` | Declarative async boundary showing fallback while children load, with SSR awaiting and hydration integration |
| `teleport` | Teleport element relocating a subtree via a single anchor placeholder, with default-on SSR block emission, marker-delimited hydration consumption and stable-target rejection |
| `transition` | CSS-class-driven enter/leave animations for a single conditional child via the `Transition` element, with delayed removal, duration resolution, node accounting, and reduced-motion support |
| `hydration-data-transfer` | Server-to-browser data transfer for `AsyncResult` states, `FetchPort` response caches, and `Signal` values via versioned payload injection |
| `signal-value-transfer` | Collection and restoration of `Signal`/`Computed`/`ReactiveList`/`ReactiveDict` values across the hydration boundary via `__signal_members__` |
| `signal-stream` | Bidirectional conversion between occurrence-based streams and signals: `to_signal`, `to_reactive_list`, `to_async_iter`, with AsyncResult-style error/completion signals, drop-oldest capping, and lifecycle cleanup |
| `sse-composable` | `use_event_source` composable sharing per-app SSE connections: reference-counted registry keyed by `(transport, url)`, per-subscriber pull-based queues, connection-handle async iterator with `.state` signal and `.close()`, `SSEvent` dataclass, SSR no-op fallback, and fetch-based POST support with EventSource-style reconnection |
| `sse-parser` | Framework-internal `text/event-stream` codec: incremental, boundary-safe parser (`event`/`data`/`id`, comments, CRLF, id persistence, trailing-partial discard) and a matching frame formatter, both pure Python |
| `websocket-composable` | `use_websocket` composable for bidirectional text messaging over a shared, reference-counted connection: protocols-aware registry keying, client-side reconnection with exponential backoff and jitter, `.last_close` close introspection, disconnected send policy with opt-in buffering, and SSR no-op fallback |
| `typed-realtime` | Typed message send/receive for realtime composables: `message_type` dataclass contract, typed-response body wire envelope, strict-by-default reconstruction, skip-on-error `.last_error` surfacing, and app-scoped realtime type allowlist |
| `readonly-signal` | Read-only reactive values with an external-only update channel: `use_readonly_signal`, `use_window_event`, `use_document_event`, with lifecycle-bound listener cleanup and no hydration transfer |
| `transfer-codec` | Layered serialization engine (encode/decode) preserving Python type fidelity across the hydration boundary via `__webcompy_`-tagged JSON |
| `payload-compression` | Optional gzip compression of the hydration data transfer payload via stdlib `zlib`/`base64`, threshold-based activation, `__webcompy_compressed__` envelope flag |
| `ssg-via-ssr` | SSG via SSR: shared build artifacts, ASGITransport route fetching, prod/dev ASGI app modes |
| `pwa` | Declarative Progressive Web App support: Web App Manifest generation/serving/injection, build-time framework-owned Service Worker template (no user JS, no third-party libraries), precache enumeration of build output with clean-URL index resolution and opt-in runtime precache, same-origin runtime caching rules (cache-first/network-first/stale-while-revalidate) with isolated caches and eviction, immediate activation with old-cache cleanup, offline navigation fallback, base-URL-scoped registration injection, and dev-mode-off-by-default |
| `test-execution-paths` | Physical separation between unit (`tests/`), browser (`tests/browser/`), and E2E (`e2e/`) tiers; opt-in `WEBCOMPY_RUN_E2E=1` / `WEBCOMPY_RUN_BROWSER=1` gates; `scripts/run-e2e-tests.sh` and `scripts/run-browser-tests.sh` canonical entry points |
| `browser-dualrun` | Classification of `tests/` modules for PyScript dual-run eligibility (read-only AST pass with pragma overrides), in-page execution of the eligible subset via the harness mount, and bucketed CPython-vs-PyScript divergence reporting (`artifacts/browser-dualrun.json`, informational) |
| `browser-probes` | Environment probe battery under `tests/browser/probes/` codifying PyScript-only contracts as a hard-gate suite, plus a manually-triggered version-bump sweep diffing probe outcomes across the pinned and a candidate PyScript version |
| `inspect-pyexec` | `webcompy inspect pyexec`: single-shot and REPL evaluation of Python code inside the harness PyScript interpreter with structured JSON output; confined to the harness session, independent from `inspect-cli` |
| `browser-test-harness` | PyScript-native in-browser unit testing: harness server (runtime assets, py-config, manifest, harness page), in-page runner with `app`/`dom_root` fixtures and per-test isolation, pytest dispatch over `window.__webcompy_test__.run_one`, wheel vs source-mount supply modes, crash containment, and console-error capture |
| `doc-spec-references` | Governance of how universal docs reference `openspec/specs/`; retired API-name blocklist; `scripts/check-doc-spec-refs.py` guardrail |
| `api-docstrings` | Docstring coverage and Google-style structure for public interfaces of all four packages; ban on OpenSpec artifact references in docstrings and comments; stdlib-only strict checker with migration baseline (`scripts/check-docstrings.py`); same-PR docstring-implementation sync with must-fix inconsistency blocking approval |
| `code-block` | `CodeBlock` component rendering syntax-highlighted code as framework-managed token spans (direct children of `<code>`, no `raw_html` injection), opt-in `copyable` clipboard button, plus the `highlight()` HTML-string API with dual `tok-*`/Pygments classes |
| `ui-primitives` | Two-layer first-party UI components: headless contract (behavior-only with structural CSS, `data-state` vocabularies, `class_name` pass-through), themed composition with token-based defaults, three import paths, stylesheet delivery through `/_webcompy-ui/`, and the Spinner pair |
| `ui-form-controls` | First-party form controls (Input, Textarea, Select, Checkbox, Switch, Radio/RadioGroup, FormField) as headless/themed pairs: Field/raw binding via `:bind` (including select support), native elements in custom-element wrappers, Switch ARIA pattern, RadioGroup shared generated name, FormField DI-confined association ids with `aria-invalid`/`aria-describedby`/`data-state` touched-invalid gating, and themed defaults in the primitives stylesheet |
| `ui-overlay` | First-party overlay components (Modal, Drawer, Dropdown, Toast) as headless/themed pairs: dialog accessibility contract, dimmed dark backdrop scrim, tokenized panel surfaces/elevation (`--shadow-lg`), menu button keyboard model with propagation-owned toggle and capture-phase outside close, per-instance hydration-stable DOM ids, optional `render_closed` static menu mode, trigger-anchored menu positioning (`align`, `positioning` escape hatch) with scroll/resize re-measurement, and the toast queue with live region and auto-dismiss |
| `ui-disclosure` | Disclosure and feedback components (Tabs, Collapse/Accordion, Alert, Progress, Badge, Skeleton, Card) as headless/themed pairs: tablist contract with roving tabindex and hidden persistent panels, key-based `tabs`/`items` props, per-instance hydration-stable DOM ids, Collapse/expand animated through the Transition capability via a CSS natural-height technique, Accordion open policy, variant-to-role Alert mapping, determinate/indeterminate Progress ARIA, decorative Skeleton, structural Card |
| `syntax-highlight-lexers` | `Lexer` protocol, lexer registry (name/alias/file-extension lookup), built-in Python/Bash/TOML lexers, `LexerInfo` introspection, Pygments adapter skeleton |
