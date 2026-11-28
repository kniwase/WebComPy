from __future__ import annotations

from typing import TypedDict


class DocsSearchMetadata(TypedDict):
    description: str
    headings: tuple[str, ...]


DOCS_SEARCH_METADATA: dict[str, DocsSearchMetadata] = {
    "/documents/getting-started/what-is-webcompy": {
        "description": "Framework positioning, the dual-environment "
        "model, core promises, and the relationship to "
        "FastAPI and Starlette.",
        "headings": ("The dual-environment model", "Core promises", "Relationship to FastAPI and Starlette"),
    },
    "/documents/getting-started/why-webcompy": {
        "description": "Why you might choose WebComPy — and an honest account of when you should not.",
        "headings": ("Why WebComPy", "Why not WebComPy", "The short version"),
    },
    "/documents/getting-started/installation": {
        "description": "How to install WebComPy and set up a project with uv or Poetry.",
        "headings": (
            "Prerequisites",
            "Install with uv (Recommended)",
            "Browser dependencies",
            "Project configuration",
            "Lock file & dev server",
            "Install with Poetry",
        ),
    },
    "/documents/getting-started/quickstart": {
        "description": "Create a WebComPy project, start the dev server, and render your first component.",
        "headings": ("Create a project", "Start the dev server", "Your first component"),
    },
    "/documents/getting-started/project-structure": {
        "description": "The layout of a WebComPy app package, build vs "
        "server configuration, static files, resources, "
        "and the lockfile.",
        "headings": ("The app package", "Configuration: build vs server", "Static files and resources", "The lockfile"),
    },
    "/documents/guides/overview": {
        "description": "Build a complete six-step ToDo application with WebComPy, covering "
        "reactive state, components, routing, forms, remote data, and "
        "static deployment.",
        "headings": ("Prerequisites", "Tutorial roadmap", "How each step builds on the last"),
    },
    "/documents/guides/todo-app-shell": {
        "description": "Model tasks in a ReactiveList, track a filter signal with "
        "use_state, derive counts and filtered views with "
        "use_computed, and render keyed lists with repeat().",
        "headings": (
            "Defining task state with use_reactive_list() and Signal",
            "Deriving counts and filtered views with use_computed()",
            "Rendering keyed lists with repeat() and filter buttons",
        ),
    },
    "/documents/guides/todo-components": {
        "description": "Extract TodoItem and TodoToolbar into reusable "
        "@define_component() components using props, named slots, "
        "and component-scoped styles.",
        "headings": (
            "Defining multi-word components with @define_component()",
            "Passing props and default slots into TodoToolbar",
        ),
    },
    "/documents/guides/todo-navigation": {
        "description": "Add client-side routes for All, Active, and Done views "
        "using flat Router definitions, RouterLink active classes, "
        "and RouterView inside TodoApp.",
        "headings": ("Sharing tasks across routed views", "Wiring Router, RouterLink, and RouterView"),
    },
    "/documents/guides/todo-forms": {
        "description": "Add a validated task-creation form with use_field(), use_form(), "
        "FormField, and Input, and toggle task completion with Checkbox.",
        "headings": (
            "Validating input with use_field() and use_form()",
            "Rendering controls with FormField, Input, and :bind",
            "Toggling completion with Checkbox",
        ),
    },
    "/documents/guides/todo-remote-data": {
        "description": "Load and mutate tasks over HTTP using HttpClient, "
        "dataclass decoding, and use_async_result(), backed by a "
        "client-side FetchMiddleware mock.",
        "headings": (
            "Typed API payloads with @dataclass and HttpClient",
            "Rendering loading and error UI with switch()",
            "Client-side API mocking with FetchMiddleware",
        ),
    },
    "/documents/guides/todo-deploy": {
        "description": "Wrap routed views in ErrorBoundary for runtime resilience, "
        "generate a static site bundle with webcompy generate, and "
        "understand hydration versus browser fetching.",
        "headings": (
            "Guarding runtime views with ErrorBoundary",
            "Building static output with webcompy generate",
            "What pre-rendering bakes vs what fetches at runtime",
        ),
    },
    "/documents/basic/components": {
        "description": "Define Light DOM components with @define_component(), receive "
        "props and slots, hook into lifecycle events, and apply static "
        "scoped styles.",
        "headings": (
            "Defining components and tag names",
            "Returning multiple roots",
            "Props and slots",
            "Lifecycle hooks",
            "Scoped styles and host display",
            "The display keyword argument and :host",
        ),
    },
    "/documents/basic/template-html": {
        "description": "Render WebComPy Element trees from HTML strings with reactive "
        "{{ }} interpolation, safe expressions, filters, conditionals, "
        "loops, events, and component tags.",
        "headings": (
            "Interpolation and reactivity",
            "Safe expression subset and built-in filters",
            "Conditionals and loops",
            "Conditionals ({% if %})",
            "Loops ({% for %}) and loop metadata",
            "Comments and raw blocks",
            "Events, :ref, and :bind attributes",
            "Component tags in templates",
        ),
    },
    "/documents/basic/reactive-state": {
        "description": "Manage fine-grained UI state with Signal, Computed, "
        "ReactiveList, ReactiveDict, transfer-capable use_* "
        "composables, and effect().",
        "headings": (
            "Reactive primitives",
            "Transfer-capable use_* composables",
            "The equality contract",
            "Side effects with effect()",
        ),
    },
    "/documents/basic/elements-and-events": {
        "description": "Build reactive DOM trees directly in Python with the "
        "html namespace, repeat(), switch(), DOMEvent handlers, "
        "and DomNodeRef.",
        "headings": (
            "The html namespace and element structure",
            "Text, line breaks, raw HTML, and fragments",
            "Conditional rendering with switch()",
            "Lists and keyed reconciliation with repeat()",
            "DOM events and DOMEvent",
            "Capturing DOM nodes with DomNodeRef",
        ),
    },
    "/documents/basic/markdown-documents": {
        "description": "Render Markdown strings with render_markdown(), load "
        "frontmatter-backed documents with "
        "load_markdown_document(), extract TOC headings, and apply "
        "prose.css.",
        "headings": (
            "Inline rendering vs document loading",
            "Frontmatter formats",
            "MarkdownDocument and table of contents (toc)",
            "Opt-in typography with prose.css",
            "Authoring docs pages for your own app",
        ),
    },
    "/documents/basic/routing": {
        "description": "Configure client-side routes with Router, RouterView, RouterLink, "
        "route parameters, query strings, hash vs history modes, and "
        "use_router().",
        "headings": (
            "Flat route table and RouterView",
            "Routing modes: hash vs history",
            "Dynamic parameters, query strings, and navigation state",
            "RouterLink and active styling",
            "Reading the active match with use_router()",
        ),
    },
    "/documents/basic/forms": {
        "description": "Manage reactive form state and validation with use_field(), "
        "use_form(), two-way :bind attributes, and first-party UI form "
        "controls.",
        "headings": (
            "Reactive fields and validators",
            "Grouping fields with use_form()",
            "Native two-way :bind wiring",
            "First-party UI form controls",
        ),
    },
    "/documents/basic/http-and-async": {
        "description": "Fetch HTTP endpoints with HttpClient, decode responses into "
        "Python types with response_type, and render "
        "loading/success/error UI with use_async_result().",
        "headings": (
            "Making requests with HttpClient",
            "Typed decoding with response_type",
            "Managing UI states with use_async_result()",
        ),
    },
    "/documents/basic/styling-and-themes": {
        "description": "Style components with scoped dicts or css_text(), "
        "understand the CSS @layer cascade, register app-level "
        "styles, and toggle themes with use_theme().",
        "headings": (
            "Scoped styles: Python dicts vs css_text()",
            "How the CSS @layer cascade works",
            "Switching light, dark, and system themes with use_theme()",
            "App-level stylesheets and head links",
        ),
    },
    "/documents/basic/storage": {
        "description": "Persist reactive Signal state in browser localStorage and "
        "sessionStorage with use_local_storage() and use_session_storage().",
        "headings": ("use_local_storage() vs use_session_storage()", "Server-side rendering behavior"),
    },
    "/documents/basic/error-handling": {
        "description": "Isolate subtree rendering and event errors with "
        "ErrorBoundary, render custom fallback UI, and allow users to "
        "retry via reset().",
        "headings": ("ErrorBoundary parameters", "Recovering with reset() and catch_events"),
    },
    "/documents/basic/ui-primitives": {
        "description": "The two-layer first-party component model — headless behavior "
        "cores and token-themed skins — with the Spinner as the worked "
        "example.",
        "headings": (
            "Three import paths",
            "Stylesheet delivery and cascade",
            "The headless contract",
            "The themed layer",
            "Live example",
        ),
    },
    "/documents/basic/overlay": {
        "description": "Build accessible Modal, Drawer, Dropdown, and Toast overlays with "
        "Teleport, Transition animations, and keyboard management.",
        "headings": ("Component overview", "Modal", "Drawer", "Dropdown", "Toast", "Live example"),
    },
    "/documents/basic/disclosure": {
        "description": "Show/hide content with Tabs, Collapse, and Accordion, and surface "
        "status with Alert, Progress, Badge, Skeleton, and Card "
        "components.",
        "headings": (
            "Component overview",
            "Tabs",
            "Collapse and Accordion",
            "Alert and Progress",
            "Badge, Skeleton, and Card",
            "Headless variants",
            "Live example",
        ),
    },
    "/documents/advanced/readonly-signal": {
        "description": "Expose reactive state to consumers without letting them "
        "mutate it — use_readonly_signal, use_window_event, "
        "use_document_event, lifecycle chaining, and SSR behavior.",
        "headings": (
            "When to use",
            "Setup",
            "Recipes",
            "Track window events with use_window_event()",
            "Track document state with use_document_event()",
            "Share module-level external state without a component context",
            "Behavior notes",
            "Pitfalls",
        ),
    },
    "/documents/advanced/signal-stream": {
        "description": "Bridge occurrence-based async streams and reactive cell "
        "state — choose between cells and occurrences, convert feeds "
        "with to_signal and to_reactive_list, and stream signal "
        "updates with to_async_iter.",
        "headings": (
            "Choosing between cells and streams",
            "When to use",
            "Setup",
            "Recipes",
            "Accumulate an SSE or WebSocket feed with a bounded window",
            "Track the latest item and stream status with to_signal()",
            "React to signal writes sequentially with to_async_iter()",
            "Behavior notes",
            "Pitfalls",
        ),
    },
    "/documents/advanced/event-source": {
        "description": "Stream unidirectional server events into WebComPy components "
        "with use_event_source — shared registries, named event "
        "filtering, POST streaming, Last-Event-ID resumption, and SSR "
        "degradation.",
        "headings": (
            "When to use",
            "Setup",
            "Recipes",
            "Subscribe to named event types and track connection state",
            "Share one connection across components",
            "Stream POST SSE endpoints (e.g., AI prompts or filtered queries)",
            "Behavior notes",
            "Pitfalls",
        ),
    },
    "/documents/advanced/websocket": {
        "description": "Open bidirectional text connections with use_websocket — "
        "connection sharing, exponential backoff with jitter, close "
        "introspection, disconnected send buffering, and gap recovery.",
        "headings": (
            "When to use",
            "Setup",
            "Recipes",
            "Share connections by (url, protocols)",
            "Configure reconnection backoff and inspect CloseInfo",
            "Buffer sends while connecting or reconnecting",
            "The gap/refetch recipe",
            "Bridge WebSocket frames with signal streams",
            "Behavior notes",
            "Pitfalls",
        ),
    },
    "/documents/advanced/typed-realtime": {
        "description": "Send and receive dataclass-typed WebSocket messages with "
        "use_websocket(message_type=...) — metadata-typed fields, "
        "strict reconstruction, error signals, and custom "
        "allowlisted codecs.",
        "headings": (
            "When to use",
            "Setup",
            "Recipes",
            "Inspect decode failures via .last_error",
            "Allow extra server fields with strict=False",
            "Register custom types on both client and server",
            "Behavior notes",
            "Pitfalls",
        ),
    },
    "/documents/advanced/rpc-contracts": {
        "description": "Primary entry point for typed WebComPy RPC — transport "
        "routing guide, shared "
        "Procedure/StreamingProcedure/Subscription contracts, batch "
        "and notify helpers, server binding, and middleware.",
        "headings": (
            "Choosing the right transport",
            "When to use",
            "Setup",
            "Recipes",
            "Call a Procedure and handle RpcError",
            "Batch multiple calls and send notifications",
            "Add auth headers or test mocks with RpcMiddleware",
            "Register custom types on the RPC registry",
            "Behavior notes",
            "Pitfalls",
        ),
    },
    "/documents/advanced/rpc": {
        "description": "HTTP transport for WebComPy JSON-RPC — RpcHttpClient, Starlette "
        "dispatcher mounting, strict typed decoding, error handling, SSR "
        "baking, and manual transport appendix.",
        "headings": (
            "When to use",
            "Setup",
            "Recipes",
            "Mount on a custom path and compute base_url-aware endpoints",
            "Handle structured JSON-RPC errors with RpcError",
            "Inspect or decorate HTTP RPC calls with add_rpc_middleware",
            "Behavior notes",
            "Pitfalls",
            "Manual transport (rarely needed)",
        ),
    },
    "/documents/advanced/rpc-websocket": {
        "description": "Run typed RPC calls, batches, notifications, and "
        "cursor-replayed subscriptions over a single shared "
        "auto-reconnecting WebSocket with RpcWsClient.",
        "headings": (
            "When to use",
            "Setup",
            "Recipes",
            "Recover cleanly with cursor rejoin and RESYNC_REQUIRED",
            "Multiplex Procedure, batch, and notify over RpcWsClient",
            "Tune heartbeat and reconnection backoff",
            "Run finite StreamingProcedure calls over WebSocket",
            "Behavior notes",
            "Pitfalls",
        ),
    },
    "/documents/advanced/rpc-streaming": {
        "description": "Stream finite, call-scoped typed responses from server "
        "generators with StreamingProcedure and RpcStream over HTTP "
        "SSE or WebSocket, including lifecycle states, cancellation, "
        "and SSR fallback.",
        "headings": (
            "When to use",
            "Setup",
            "Recipes",
            "Bridge stream chunks and lifecycle state with to_reactive_list",
            "Cancel a stream early and clean up server resources",
            "Switch transport to RpcWsClient with zero contract changes",
            "Mock or inspect HTTP streams in RpcMiddleware",
            "Behavior notes",
            "Pitfalls",
        ),
    },
    "/documents/advanced/ssr-and-ssg": {
        "description": "Understand WebComPy's dual-environment render pipeline, "
        "dev/prod/generate modes, per-request RenderContext isolation, "
        "and self-site fetch handling during pre-rendering.",
        "headings": (
            "The dual-environment pipeline",
            "Dev, prod, and static generation modes",
            "Per-request RenderContext isolation",
            "Self-site fetches and blocked paths",
            "Embedding into an existing ASGI host",
            "Behavior notes & pitfalls",
        ),
    },
    "/documents/advanced/hydration-and-transfer": {
        "description": "How WebComPy adopts server-rendered DOM nodes, "
        "scopes state transfer to the initial hydration "
        "window, encodes Python types, compresses payloads, "
        "and avoids navigation flicker.",
        "headings": (
            "What transfers across the boundary",
            "Payload lifecycle and initial-window gating",
            "Per-instance transfer IDs and stable keys",
            "Auto keys vs explicit keys",
            "Factory skip for signals and AsyncResult",
            "The 3-layer transfer codec",
            "Optional payload compression",
            "Flicker-free navigation with resources",
            "Hydration mismatch diagnostics",
            "Pitfalls",
        ),
    },
    "/documents/advanced/async-rendering-and-boundaries": {
        "description": "Author async components cleanly, "
        "coordinate Suspense and ClientOnly across "
        "SSR and hydration, and understand how "
        "AsyncSchedulerPort gates the initial page "
        "reveal.",
        "headings": (
            "Async component setup and lifecycle hooks",
            "Coordinating async trees with Suspense",
            "SSR and hydration behavior",
            "Skipping SSR with ClientOnly",
            "How AsyncSchedulerPort gates the reveal",
            "Behavior notes & pitfalls",
        ),
    },
    "/documents/advanced/transition": {
        "description": "Animate appearing and disappearing conditional elements using "
        "WebComPy's Vue-compatible Transition class protocol, duration "
        "resolution, and reduced-motion support.",
        "headings": (
            "Basic usage",
            "Enter and leave class protocol",
            "Props and configuration",
            "How durations are resolved",
            "Single-child rule and replacement behavior",
            "prefers-reduced-motion support",
            "Pitfalls",
        ),
    },
    "/documents/advanced/teleport": {
        "description": "Relocate modals, drawers, and overlays to external DOM "
        "containers like body with Teleport, preserving reactive "
        "bindings, SSR block emission, and hydration order.",
        "headings": (
            "How anchoring and relocation work",
            "Basic usage",
            "SSR block emission and hydration",
            "Target rules and rejection diagnostics",
            "Multiple Teleports sharing a target",
            "Pitfalls",
        ),
    },
    "/documents/advanced/loading-screen": {
        "description": "Configure the boot-time loading experience — presentation "
        "modes, interaction policies, staged progress, dormant "
        "wake-up timing, custom templates, and accessibility.",
        "headings": (
            "Presentation modes and configuration",
            "Mode resolution",
            "Grace period, interaction policies, and wake-up",
            "Dormant treatment and fade-out",
            "Staged progress and stall watchdog",
            "Custom templates and the toolkit contract",
            "Theme tokens, accessibility, and CSP",
            "Pitfalls",
        ),
    },
    "/documents/advanced/styling-deep-dive": {
        "description": "Master WebComPy's full CSS @layer cascade, "
        "css_text_template(), reactive component styles, "
        "unlayered app.append_style() helpers, incremental style "
        "injection, and :host patterns.",
        "headings": (
            "The full CSS @layer cascade model",
            "css_text() and css_text_template()",
            "Reactive component styles (reactive_scoped_style)",
            "Unlayered app styles: append_style, reactive_style, reactive_block",
            "Incremental scoped styles & lazy routes",
            "Advanced :host host-wrapper patterns",
            "Pitfalls",
        ),
    },
    "/documents/advanced/pwa": {
        "description": "Enable installability and offline support declaratively with "
        "PWAConfig — build-time Web App Manifest and framework-owned Service "
        "Worker generation, precaching, runtime caching decision rules, and "
        "offline navigation fallback.",
        "headings": (
            "When to use",
            "Setup",
            "What gets generated",
            "Web App Manifest",
            "Framework-owned Service Worker",
            "Precache",
            "Service Worker registration",
            "What runs in the browser",
            "Runtime caching",
            "Activation, updates, and cache cleanup",
            "Offline fallback",
            "Recipes",
            "1. Fully offline cold start with local runtime precaching",
            "2. Prefixed deployment with a custom offline page",
            "3. Observing install, activation, and update rotation locally",
            "Behavior notes",
            "Pitfalls",
        ),
    },
    "/documents/advanced/dependency-injection-deep-dive": {
        "description": "Understand WebComPy's hierarchical DIScope "
        "tree, lazy component child scopes, "
        "per-render-context port isolation, and "
        "clean service/fake overrides in unit "
        "tests.",
        "headings": (
            "When to use",
            "Setup",
            "Recipes",
            "1. Swap services and ports cleanly in tests (service + fake)",
            "2. Shadow a provider inside a component subtree with reactive signals",
            "3. Enter standalone scopes with DIScope and RenderContext",
            "Behavior notes",
            "Pitfalls",
        ),
    },
    "/documents/advanced/middleware": {
        "description": "Intercept HTTP and JSON-RPC operations with stackable "
        "FetchMiddleware and RpcMiddleware chains, DI-scoped additive "
        "registries, streaming header resolution, and plugin hooks.",
        "headings": (
            "When to use",
            "Setup",
            "Recipes",
            "1. Inject authentication or tracing headers (FetchMiddleware & RpcMiddleware)",
            "2. Log timings and cache responses around await next(...)",
            "3. Build offline mocks without losing schema validation",
            "Behavior notes",
            "Pitfalls",
        ),
    },
    "/documents/advanced/routing-deep-dive": {
        "description": "Build multi-level layouts and guarded navigation with "
        "nested RouterPage children, RouterView depth reuse, "
        "lazy() preloading, async route guards, and automatic "
        "scroll restoration.",
        "headings": (
            "When to use",
            "Setup",
            "Recipes",
            "1. Guard an admin console with async checks, redirects, and error hooks",
            "2. Defer bundle imports with lazy() and control preloading",
            "3. Configure RouterLink active styling and scroll restoration",
            "Behavior notes",
            "Pitfalls",
        ),
    },
    "/documents/advanced/plugins": {
        "description": "Extend WebComPy applications with WebComPyPlugin subclasses — "
        "lifecycle hooks, DI providers, fetch and RPC middleware "
        "aggregation, and conditional PluginScript tags.",
        "headings": (
            "When to use",
            "Setup",
            "Recipes",
            "1. Bundle middlewares, providers, and router hooks in one plugin",
            "2. Inject static or runtime-conditional <script> tags with PluginScript",
            "3. Provide fresh per-request values in on_render_context_init()",
            "Behavior notes",
            "Pitfalls",
        ),
    },
    "/documents/advanced/typed-api-deep-dive": {
        "description": "Decode plain JSON endpoints with from_json strictness "
        "modes, preserve non-JSON Python types via "
        "encode_with_meta and FastAPI TypedJSONResponse, and "
        "submit multipart forms through FetchPort.",
        "headings": (
            "When to use",
            "Setup",
            "Recipes",
            "1. Validate external APIs with from_json strictness and coercion",
            "2. Choose header mode vs. body mode with TypedJSONResponse",
            "3. Apply encode_with_meta() in non-FastAPI servers",
            "4. Submit multipart forms through HttpClient across SSR and tests",
            "Behavior notes",
            "Pitfalls",
        ),
    },
    "/documents/advanced/ui-headless-contract": {
        "description": "Understand WebComPy's two-layer UI architecture — "
        "zero-style webcompy.ui.headless behavior primitives, "
        "data-state vocabularies, class_name pass-through, "
        "DI-scoped FormField wiring, and custom theme "
        "authoring.",
        "headings": (
            "When to use",
            "Setup",
            "Data-state vocabulary and part-class hooks",
            "Recipes",
            "1. Author a custom themed component pair over a headless core",
            "2. Wire accessible labels and touched-invalid styling via FormField",
            "3. Override themed primitives cleanly via class_name and part hooks",
            "Behavior notes",
            "Pitfalls",
        ),
    },
    "/documents/advanced/custom-elements": {
        "description": "Author Light DOM custom-element components with "
        "@define_component() — multi-root wrappers, document "
        "connection hooks, observed attributes, registry reuse, "
        "hydration upgrade order, and :host styling.",
        "headings": (
            "When to use",
            "Setup",
            "Recipes",
            "1. Return multiple roots with a single parent-facing DOM node",
            "2. Run DOM integration code with on_mounted and on_unmounted",
            "3. Bridge external JavaScript attributes with observed_attributes",
            "4. Control wrapper layout boxes and :host cascade precedence",
            "Behavior notes",
            "Pitfalls",
        ),
    },
    "/documents/advanced/persistence-patterns": {
        "description": "Share state safely across browser tabs and page "
        "reloads — compare localStorage, sessionStorage, "
        "hydration transfer, cookies, and URL state, and "
        "understand sync_tabs=True event coalescing and SSR "
        "semantics.",
        "headings": (
            "Choosing a persistence mechanism",
            "When to use",
            "Setup",
            "Recipes",
            "1. Synchronize structured preferences with factory defaults and remote resets",
            "2. Share one setting inside the same tab via DI",
            "Behavior notes",
            "Pitfalls",
        ),
    },
    "/documents/advanced/i18n": {
        "description": "Add multi-language support with webcompy.i18n — DI-managed "
        "I18nManager, dot-path catalogs with interpolation and CLDR plurals, "
        "fallback chains, cookie-only persistence, and deterministic "
        "SSR/hydration parity.",
        "headings": (
            "When to use",
            "Setup",
            "Deterministic SSR and hydration parity",
            "Cookie persistence and normalization rules",
            "Recipes",
            "1. Nested catalogs, dot paths, and {param} interpolation",
            "2. Pluralization with CLDR categories and pipe shorthand",
            "3. Opt-in full CLDR plural rules with Babel",
            "4. Regional overrides and the fallback chain",
            "5. Locale switcher component and explicit server seeding",
            "Behavior notes",
            "Pitfalls",
            "Late client-side locale mutation breaks parity",
            "Providing a pre-built instance instead of a factory",
            "Evaluating t() directly in html.* children without use_computed",
            'Missing "other" key or duplicate rule registration',
        ),
    },
    "/documents/server/cli-reference": {
        "description": "Complete command and flag reference for python -m webcompy, "
        "exit behavior, lockfile workflows, and browser inspection via "
        "webcompy inspect.",
        "headings": (
            "Subcommands at a glance",
            "Server and build commands",
            "start",
            "generate",
            "init",
            "lock",
            "Inspect subcommands",
            "Server lifecycle: serve and stop",
            "DOM, console, and interaction checks",
            "In-browser Python evaluation: pyexec",
            "Exit codes and automation contracts",
            "Worked examples",
            "Local development server on a custom port",
            "Static production build with local runtime assets",
            "Lock, audit against pyproject.toml, and export pinned requirements",
            "Headless browser inspection workflow with inspect",
        ),
    },
    "/documents/server/project-configuration": {
        "description": "Structure browser and server settings across "
        "pyproject.toml and webcompy_config.py, configure "
        "resource allow-lists, and manage webcompy-lock.json.",
        "headings": (
            "The two-file configuration model",
            "Config discovery rules",
            "WebComPyBuildConfig field reference",
            "WebComPyServerConfig and LockfileSyncConfig",
            "WebComPyServerConfig",
            "LockfileSyncConfig",
            "Runtime vs build configuration boundary",
            "Resource allow-list and static files",
            "Lockfile lifecycle (webcompy-lock.json)",
        ),
    },
    "/documents/server/asgi-integration": {
        "description": "Embed WebComPy inside an existing FastAPI or Starlette "
        "host ASGI application with base_url alignment, or mount "
        "child ASGI apps under WebComPy.",
        "headings": (
            "Embedding WebComPy in a FastAPI or Starlette host",
            "URL prefixing, base_url, and blocked paths",
            "Mounting ASGI apps under WebComPy",
            "Mount validation and routing behavior",
            "Interaction with static site generation (webcompy generate)",
        ),
    },
    "/documents/server/serving-modes": {
        "description": "Understand dependency classification, CDN vs local "
        "runtime/WASM serving, standalone builds, bundled vs split "
        "wheel modes, and offline deployments.",
        "headings": (
            "Dependency classification",
            "Runtime, WASM, and dependency serving matrix",
            "Wheel modes: bundled vs split",
            "Cache integrity and .webcompy_modules/",
            "Offline and firewall deployment checklist",
        ),
    },
    "/documents/server/testing": {
        "description": "Test WebComPy components, signals, HTTP clients, and SSR/ASGI apps "
        "without a browser using webcompy_testing, TestRenderer, and fake "
        "ports.",
        "headings": (
            "Application testing tiers",
            "Rendering components with TestRenderer",
            "TestRendererResult methods and properties",
            "Fake ports inventory",
            "App, SSR, and ASGI test helpers",
            "Recipe: testing a component that fetches data",
            "Behavior notes and pitfalls",
        ),
    },
    "/documents/examples/hello-world": {
        "description": "Minimal WebComPy application demonstrating @define_component, "
        "ComponentContext, html helpers, and WebComPyApp "
        "bootstrapping.",
        "headings": ("What this demonstrates", "Key mechanisms and how to adapt"),
    },
    "/documents/examples/todo": {
        "description": "Reactive list and dictionary mutations, fine-grained derived counts, "
        "DomNodeRef inputs, child components, and scoped CSS in a browser "
        "ToDo app.",
        "headings": ("What this demonstrates", "Key mechanisms and how to adapt"),
    },
    "/documents/examples/forms": {
        "description": "Complete form built with use_field, use_form, validators, and "
        "accessible first-party WebComPy UI form controls (Input, Select, "
        "Textarea, Checkbox, Switch, RadioGroup, FormField).",
        "headings": ("What this demonstrates", "Key mechanisms and how to adapt"),
    },
    "/documents/examples/routing": {
        "description": "Nested child routes with preserved parent layout state, dynamic "
        "path parameters, and a before_route_change redirect guard running "
        "in an isolated hash-mode router.",
        "headings": ("What this demonstrates", "Key mechanisms and how to adapt"),
    },
    "/documents/examples/storage-sync": {
        "description": "Live cross-tab and cross-window state synchronization using "
        "use_local_storage(sync_tabs=True) demonstrated with two "
        "same-origin demo windows.",
        "headings": ("What this demonstrates", "Key mechanisms and how to adapt"),
    },
    "/documents/examples/transition": {
        "description": "CSS-driven enter and leave animations for conditional elements "
        "using WebComPy's Transition wrapper, timed cleanup, and "
        "reduced-motion support.",
        "headings": ("What this demonstrates", "Key mechanisms and how to adapt"),
    },
    "/documents/examples/teleport": {
        "description": "Relocate modals and floating dropdowns into document.body using "
        "Teleport while preserving component signals, event handlers, and "
        "scoped CSS.",
        "headings": ("What this demonstrates", "Key mechanisms and how to adapt"),
    },
    "/documents/examples/i18n-playground": {
        "description": "Reactive internationalization demo showing webcompy.i18n "
        "factory provisioning, use_i18n() catalogs, parameter "
        "interpolation, and CLDR pluralization.",
        "headings": ("What this demonstrates", "Key mechanisms and how to adapt"),
    },
    "/documents/examples/matplotlib": {
        "description": "Running WASM scientific libraries (NumPy and Matplotlib) "
        "inside an isolated PyScript iframe and rendering reactive "
        "base64 charts.",
        "headings": ("What this demonstrates", "Key mechanisms and how to adapt"),
    },
    "/documents/examples/http-fetch": {
        "description": "Fetching JSON endpoints with HttpClient and decoding objects, "
        "lists, scalars, and raw responses using dataclass "
        "response_type annotations.",
        "headings": ("What this demonstrates", "Key mechanisms and how to adapt"),
    },
    "/documents/examples/fetch-middleware": {
        "description": "Stackable FetchMiddleware chains adding trace headers "
        "and mocking a /api/notes REST endpoint inside a "
        "serverless static app.",
        "headings": ("What this demonstrates", "Key mechanisms and how to adapt", "Real server wiring"),
    },
    "/documents/examples/rpc-middleware": {
        "description": "Contract-first typed Procedure and batch() RPC calls "
        "answered in-browser by RpcMiddleware response synthesis, "
        "plus server registration reference.",
        "headings": ("What this demonstrates", "Key mechanisms and how to adapt", "Real server wiring"),
    },
    "/documents/migration/from-jinja2-fastapi": {
        "description": "Architecture guide, ASGI strangler integration, live "
        "before/after comparison, and phase-by-phase "
        "checklist for teams migrating from Jinja2 templates "
        "and FastAPI.",
        "headings": (
            "Architecture shift",
            "Choosing an integration strategy",
            "Strategy 1: Standalone WebComPy",
            "Strategy 2: Mount FastAPI under WebComPy (mounts)",
            "Strategy 3: Host mounts WebComPy (Strangler pattern)",
            "Live before/after: user-list search",
            "Before: Jinja2 templates + FastAPI route",
            "Why each line changed",
            "Directive-by-directive conversion table",
            "Concern-by-concern migration",
            "1. Routing split: pages vs data routes",
            "2. Context dicts → HttpClient, typed RPC, and hydration baking",
            "3. Forms: POST-Redirect-GET → use_field / use_form + :bind",
            "4. Global CSS → component scoped_style and cascade layers",
            "5. Auth and sessions via cookies + middleware headers",
            "6. Reusing FastAPI SSE and WebSocket endpoints",
            "Phased strangler checklist",
            "Gotchas and what stays server-side",
            "Common migration gotchas",
            "What stays server-side (honest scope note)",
        ),
    },
    "/documents/migration/compatibility-notes": {
        "description": "Complete matrix mapping Jinja2 directives, filters, "
        "expressions, tests, and HTML behavior to WebComPy's "
        "reactive template compiler with exact exception "
        "messages.",
        "headings": (
            "Supported constructs",
            "Rejected directives and exact errors",
            "Built-in filters and filter differences",
            "Missing and custom Jinja2 filters (| safe, | escape, | sort, ...)",
            "Expressions, tests, and template differences",
            "Jinja2 is tests (is defined, is odd, is none)",
            "String concatenation with ~",
            "Missing variables (strict KeyError, not silent Undefined)",
            "Disallowed Python AST syntax inside {{ ... }}",
            "Unsupported loop.* methods",
            "HTML container, tag, and binding restrictions",
        ),
    },
    "/documents/api/app-and-components": {
        "description": "API reference for webcompy.app, webcompy.components, "
        "webcompy.plugin, webcompy.exception, and webcompy.utils.",
        "headings": (
            "Application & Configuration",
            "PluginScript",
            "reactive_block",
            "reactive_style",
            "RenderContext",
            "WebComPyApp",
            "WebComPyAppConfig",
            "Components & Lifecycle",
            "Component",
            "component_context",
            "ComponentContext",
            "ComponentDisplay",
            "ComponentGenerator",
            "ComponentProperty",
            "ComponentRenderState",
            "ComponentStore",
            "define_component",
            "on_after_rendering",
            "on_before_destroy",
            "on_before_rendering",
            "on_error_captured",
            "on_mounted",
            "on_unmounted",
            "reactive_scoped_style",
            "ReactiveScopedStyle",
            "use_async",
            "use_async_result",
            "WebComPyComponentException",
            "Plugins",
            "PluginManager",
            "WebComPyPlugin",
            "WebComPyPluginException",
            "Exceptions & Utilities",
            "ENVIRONMENT",
            "is_json_seriarizable",
            "kebab_to_pascal",
            "kebab_to_snake",
            "pascal_to_kebab",
            "strip_multiline_text",
            "WebComPyException",
        ),
    },
    "/documents/api/template-and-markdown": {
        "description": "API reference for webcompy.template including HTML "
        "template rendering, AST nodes, CSS helpers, and Markdown "
        "parsing.",
        "headings": (
            "Template Rendering & AST",
            "AttrSpec",
            "bind_children",
            "format_value",
            "get_or_compile",
            "Hole",
            "LiteralText",
            "render_markdown",
            "render_template",
            "resolve_holes",
            "resolve_tag",
            "resolve_var",
            "split_text",
            "TagResolution",
            "TemplateElement",
            "TemplateNode",
            "TemplateText",
            "CSS Helpers",
            "css_text",
            "css_text_template",
            "Markdown Documents",
            "HeadingInfo",
            "load_markdown_document",
            "MarkdownDocument",
        ),
    },
    "/documents/api/reactivity": {
        "description": "API reference for webcompy.signal reactive containers, computed "
        "signals, effects, collections, and composables.",
        "headings": (
            "Signals, Computed & Collections",
            "Computed",
            "computed_property",
            "DictMutation",
            "ListMutation",
            "ReactiveDict",
            "ReactiveList",
            "readonly",
            "ReadonlySignal",
            "Signal",
            "SignalBase",
            "use_computed",
            "use_readonly_signal",
            "Effects & Composables",
            "effect",
            "EffectHandle",
            "EffectScope",
            "use_reactive_dict",
            "use_reactive_list",
            "use_state",
            "Internal Reactivity Graph",
            "SignalNode",
        ),
    },
    "/documents/api/elements-and-routing": {
        "description": "API reference for webcompy.elements, webcompy.router, and webcompy.di.",
        "headings": (
            "Elements, Control Flow & Head",
            "AttrValue",
            "break_line",
            "client_only",
            "ClientOnlyElement",
            "create_element",
            "DomNodeRef",
            "Element",
            "ElementAbstract",
            "ElementBase",
            "ElementChildren",
            "ErrorBoundaryElement",
            "event",
            "EventHandler",
            "FragmentElement",
            "HeadElement",
            "HtmlTags",
            "MultiLineTextElement",
            "NewLine",
            "noderef",
            "raw_html",
            "repeat",
            "RepeatElement",
            "suspense",
            "SuspenseElement",
            "switch",
            "SwitchCases",
            "SwitchElement",
            "TeleportElement",
            "text",
            "TextElement",
            "TransitionElement",
            "Router & Navigation",
            "create_typed_route",
            "lazy",
            "LazyComponentGenerator",
            "RoutedComponent",
            "Router",
            "RouterContext",
            "RouterKey",
            "RouterLink",
            "RouterView",
            "use_router",
            "Dependency Injection",
            "DIScope",
            "HYDRATION_DATA_KEY",
            "HYDRATION_SIGNAL_DATA_KEY",
            "inject",
            "InjectionError",
            "InjectKey",
            "provide",
            "RESOURCE_DATA_KEY",
            "RPC_MIDDLEWARE_KEY",
            "SUSPENSE_RESOLVING_KEY",
            "HTML Tag Factories",
        ),
    },
    "/documents/api/data": {
        "description": "API reference for webcompy.ajax, webcompy.aio, webcompy.forms, "
        "webcompy.storage, webcompy.events, webcompy.resources, webcompy.realtime, "
        "and webcompy.i18n.",
        "headings": (
            "HTTP, Async & Resources",
            "AsyncResult",
            "AsyncState",
            "AsyncWrapper",
            "from_json",
            "HttpClient",
            "load_bytes",
            "load_text",
            "resolve_async",
            "Response",
            "sleep",
            "StreamAsyncIterator",
            "StreamListResult",
            "StreamResult",
            "to_async_iter",
            "to_reactive_list",
            "to_signal",
            "TypedResponseError",
            "WebComPyHttpClientException",
            "Forms & Validation",
            "email",
            "Field",
            "Form",
            "max_length",
            "max_value",
            "min_length",
            "min_value",
            "pattern",
            "required",
            "use_field",
            "use_form",
            "Validator",
            "Storage & Browser Events",
            "use_document_event",
            "use_local_storage",
            "use_session_storage",
            "use_window_event",
            "Realtime (SSE & WebSocket)",
            "CloseInfo",
            "ConnectionState",
            "EventSourceHandle",
            "register_realtime_type_handler",
            "SSEvent",
            "TypedWebSocketHandle",
            "use_event_source",
            "use_websocket",
            "WebSocketHandle",
            "Internationalization (i18n)",
            "I18N_KEY",
            "I18nController",
            "I18nManager",
            "read_locale_from_cookie",
            "register_plural_rule",
            "resolve_locale",
            "use_i18n",
        ),
    },
    "/documents/api/ui": {
        "description": "API reference for webcompy.ui components, headless primitives, theme "
        "management, styles, and code blocks.",
        "headings": (
            "Themed Components",
            "components.Accordion",
            "components.Alert",
            "components.Badge",
            "components.Card",
            "components.Checkbox",
            "components.Collapse",
            "components.Drawer",
            "components.Dropdown",
            "components.FormField",
            "components.Input",
            "components.Modal",
            "components.Progress",
            "components.Radio",
            "components.RadioGroup",
            "components.Select",
            "components.Skeleton",
            "components.Spinner",
            "components.Switch",
            "components.Tabs",
            "components.Textarea",
            "components.ToastHost",
            "Headless Primitives",
            "headless.Accordion",
            "headless.Alert",
            "headless.Badge",
            "headless.Card",
            "headless.Checkbox",
            "headless.Collapse",
            "headless.Drawer",
            "headless.Dropdown",
            "headless.FormField",
            "headless.Input",
            "headless.Modal",
            "headless.Progress",
            "headless.Radio",
            "headless.RadioGroup",
            "headless.Select",
            "headless.Skeleton",
            "headless.Spinner",
            "headless.Switch",
            "headless.Tabs",
            "headless.Textarea",
            "headless.ToastHost",
            "Theme, Composables & Styles",
            "get_styles_dir",
            "get_styles_file",
            "get_styles_files",
            "read_theme_from_cookie",
            "Theme",
            "THEME_KEY",
            "ThemeManager",
            "ToastRecord",
            "ToastState",
            "use_theme",
            "use_toast",
            "Code Block & Syntax Highlighting",
            "BashLexer",
            "CodeBlock",
            "get_lexer",
            "highlight",
            "Lexer",
            "LexerInfo",
            "LexerNotFoundError",
            "list_lexers",
            "PYGMENTS_SHORT_CLASS",
            "PythonLexer",
            "register_builtin_lexers",
            "register_lexer",
            "Token",
            "TokenType",
            "TomlLexer",
        ),
    },
    "/documents/api/server-and-cli": {
        "description": "API reference for webcompy_server, webcompy_cli, webcompy.rpc, "
        "webcompy.hydration, and webcompy.ports.",
        "headings": (
            "Server & CLI Configuration",
            "configure_server_context",
            "create_asgi_app",
            "discover_config",
            "generate_html",
            "generate_static_site",
            "LockfileSyncConfig",
            "ManifestConfig",
            "ManifestIcon",
            "PWAConfig",
            "run_inspect",
            "run_server",
            "RuntimeCachingRule",
            "RuntimeCachingStrategy",
            "ServerRenderContext",
            "WebComPyBuildConfig",
            "WebComPyServerConfig",
            "Typed RPC (Client & Server)",
            "add_rpc_middleware",
            "batch",
            "create_dispatcher_app",
            "create_rpc_ws_endpoint",
            "dispatch_payload",
            "notify",
            "Procedure",
            "ProcedureRegistry",
            "RpcBatchEntry",
            "RpcCall",
            "RpcContext",
            "RpcError",
            "RpcHttpClient",
            "RpcMiddleware",
            "RpcMiddlewareRegistry",
            "RpcStream",
            "RpcStreamState",
            "RpcSubscription",
            "RpcSubscriptionState",
            "RpcTransport",
            "RpcWsClient",
            "StreamingProcedure",
            "Subscription",
            "Hydration & State Transfer",
            "apply_transfer_meta",
            "decode",
            "encode",
            "encode_with_meta",
            "has_resolved_data",
            "HydrationMismatchRecord",
            "merge_meta_into_body",
            "META_BODY_KEY",
            "META_HEADER_NAME",
            "record_mismatch",
            "register_type_handler",
            "Port Interfaces & Server Implementations",
            "add_fetch_middleware",
            "ASYNC_SCHEDULER_PORT_KEY",
            "AsyncSchedulerPort",
            "COOKIE_PORT_KEY",
            "CookiePort",
            "CUSTOM_ELEMENT_PORT_KEY",
            "CustomElementPort",
            "DOM_PORT_KEY",
            "DOMEvent",
            "DOMNode",
            "DOMNodeList",
            "DOMPort",
            "EVENT_SOURCE_PORT_KEY",
            "EventSourcePort",
            "FETCH_MIDDLEWARE_KEY",
            "FETCH_PORT_KEY",
            "FetchMiddleware",
            "FetchMiddlewareRegistry",
            "FetchNext",
            "FetchPort",
            "FetchRequest",
            "FetchStream",
            "FFI_PORT_KEY",
            "FFIPort",
            "HISTORY_PORT_KEY",
            "HistoryPort",
            "HOST_PORT_KEY",
            "HostPort",
            "MARKDOWN_PORT_KEY",
            "MarkdownPort",
            "MEDIA_QUERY_PORT_KEY",
            "MediaQueryPort",
            "RESOURCE_PORT_KEY",
            "ResourceNotFoundError",
            "ResourcePort",
            "Response",
            "ServerAsyncSchedulerPort",
            "ServerCookiePort",
            "ServerCustomElementPort",
            "ServerDOMPort",
            "ServerEventSourcePort",
            "ServerFetchPort",
            "ServerFFIPort",
            "ServerHistoryPort",
            "ServerHostPort",
            "ServerMediaQueryPort",
            "ServerResourcePort",
            "ServerTransitionPort",
            "ServerWebSocketPort",
            "TRANSITION_PORT_KEY",
            "TransitionPort",
            "VirtualDOMEvent",
            "VirtualDOMNode",
            "WEBSOCKET_PORT_KEY",
            "WebSocketConnection",
            "WebSocketPort",
        ),
    },
    "/documents/api/testing": {
        "description": "API reference for webcompy_testing component rendering, ASGI helpers, "
        "fake ports, and browser test runner.",
        "headings": (
            "Test Renderer, ASGI Client & Fake Ports",
            "create_test_app",
            "create_test_asgi_app",
            "FakeAsyncSchedulerPort",
            "FakeBrowserDOMPort",
            "FakeBrowserFFIPort",
            "FakeBrowserHostPort",
            "FakeCustomElementPort",
            "FakeDOMNode",
            "FakeEventSourcePort",
            "FakeFetchPort",
            "FakeHistoryPort",
            "FakeMediaQueryPort",
            "FakeTransitionPort",
            "FakeWebSocketPort",
            "format_html",
            "mock_app_run",
            "RecordedRequest",
            "render_app_html_sync",
            "restore_signal_values",
            "run_sync",
            "TestRenderer",
            "TestRendererResult",
            "Browser Test Runner",
            "bootstrap",
            "evaluate",
            "normalize_traceback",
            "parse_test_id",
            "resolve_parametrize_payload",
            "resolve_qualname_target",
            "run_one",
            "skip",
            "UnknownFixtureError",
        ),
    },
}
