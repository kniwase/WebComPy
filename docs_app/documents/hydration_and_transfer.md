---
title: Hydration & Data Transfer
description: How WebComPy adopts server-rendered DOM nodes, scopes state transfer to the initial hydration window, encodes Python types, compresses payloads, and avoids navigation flicker.
---

# Hydration & Data Transfer

When pre-rendered HTML arrives in the browser, WebComPy does not tear down the DOM and rebuild from scratch. Instead, `app.run()` runs a unified **adopt & render** hydration pass that attaches reactive bindings and event listeners directly to the existing HTML nodes while restoring server-resolved state without a flash of default or loading UI.

Use the transfer-capable composables (`use_state`, `use_reactive_list`, `use_reactive_dict`, `use_async_result`), resource helpers (`load_text`, `load_bytes`), and `register_type_handler` whenever data computed during SSR or SSG should hydrate cleanly into the browser session.

## What transfers across the boundary

During server HTML assembly (`generate_html()`), after the component tree and all pending async tasks settle, WebComPy collects a v3 `TransferPayload` and writes it as HTML-escaped JSON into `<script type="application/json" id="__webcompy_data__">`:

| Payload section | Collected from | Consumed by | Scope after initial hydration |
|---|---|---|---|
| `fetches` | `ServerFetchPort` self-site responses | `BrowserFetchPort` response cache | **App lifetime** (URL/method-keyed) |
| `async_results` | `use_async_result()` (`transfer=True`) | `HYDRATION_DATA_KEY` (`has_resolved_data`) | **Initial window only** |
| `signals` | `use_state`, `use_reactive_list`, `use_reactive_dict` | `HYDRATION_SIGNAL_DATA_KEY` | **Initial window only** |
| `resources` | `ServerResourcePort` (`load_text`/`load_bytes`) | `RESOURCE_DATA_KEY` / `BrowserResourcePort` | **App lifetime** (path-keyed) |

On startup in the browser, `app.run()` parses `#__webcompy_data__` (accepting v1, v2, and v3 payloads for backward compatibility), populates the DI keys and `BrowserFetchPort` cache **before** creating any components, and immediately removes the `<script>` tag from the DOM.

## Payload lifecycle and initial-window gating

Hydrated state (`signals` and `async_results`) belongs exclusively to the page snapshot rendered for the **initial browser window**:

```text
app.run() starts
  │
  ├─► Read & remove <script id="__webcompy_data__">
  │     provide HYDRATION_DATA_KEY, HYDRATION_SIGNAL_DATA_KEY, RESOURCE_DATA_KEY
  │     populate BrowserFetchPort cache
  │
  ▼  === INITIAL HYDRATION WINDOW OPEN ===
  ├─► Adopt SSR DOM nodes & run component setups
  │     use_state / use_reactive_*  ──► skip factory, restore copy from payload
  │     use_async_result            ──► restore AsyncState.SUCCESS (no LOADING)
  ├─► await scheduler.await_pending(only_render=True)
  │     deferred hydration tasks & Suspense adoption resolve within window
  ▼  === INITIAL HYDRATION WINDOW CLOSED === (always closes, even on error or hydrate=False)
  │
  ├─► Emit single aggregated hydration-mismatch warning (if any)
  ├─► Remove #webcompy-loading & preload lazy routes
  └─► Subsequent client-side navigation / dynamic mounts:
        factories & async fetches execute fresh (never read stale initial signals/results)
```

Why this matters: once a user clicks to another route via client-side routing, components created after the initial window close **never** restore values from `#__webcompy_data__`—even if the initial page happened to render an instance of the same component class. URL-keyed fetch caches (`fetches`) and path-keyed resource contents (`resources`), however, stay valid for the lifetime of the browser session.

## Per-instance transfer IDs and stable keys

To keep multiple instances of the same component from overwriting each other, every component instance is assigned a **per-instance transfer ID** before its setup function runs:

```text
<generate_id(component_name)>#<ordinal>
```

The `ordinal` is a 0-based creation-order counter scoped per `RenderContext` and per component name: the first `CounterCard` receives `#0`, the second `#1`, and so on. Scoped CSS attributes (`webcompy-cid-*`) and mismatch diagnostics continue to use the bare definition ID (`generate_id(component_name)`) without an ordinal suffix.

Because creation order matches between server rendering and the initial browser hydration pass, instance `#0` on the browser always restores instance `#0` from SSR.

### Auto keys vs explicit keys

When calling `use_state`, `use_reactive_list`, or `use_reactive_dict`, WebComPy identifies each signal slot inside the component by key:

- **Auto key**: `use_state(lambda: 0)` derives its key from the call site's module dotted name, line number, and column offset—never the local filesystem path—so SSR builds and bundled browser wheels produce identical keys even when multiple calls share one source line.
- **Explicit key**: `use_state("draft_title", lambda: "")` names the slot directly and survives line edits cleanly.

Auto-key matching relies on identical module dotted names in both environments, so organize transferable apps as an importable Python package rather than a `__main__` single-file script.

## Factory skip for signals and `AsyncResult`

Inside an open hydration window:

1. **`use_state`, `use_reactive_list`, `use_reactive_dict`** look up `signals[transfer_id][key]` before invoking your `factory`. When present, the factory is **skipped** and the signal is initialized with an independent deep-safe copy of the transferred Python value. Mutating a restored `ReactiveList` or `ReactiveDict` never mutates the underlying payload, and restoration fires no downstream notifications (`on_before_updating` / `on_after_updating` stay silent because the server snapshot already matches the DOM).
2. **`use_computed`** is **not** transferred—`Computed` signals re-derive deterministically in the browser from their restored source signals.
3. **`use_async_result`** checks `async_results[transfer_id]`. When `state == "success"`, it restores `data` and sets `AsyncState.SUCCESS` without entering `LOADING` or executing the coroutine again. Pass `transfer=False` on `use_async_result(..., transfer=False)` to opt a specific request out and force a fresh browser fetch instead.

You can check whether a component already has transferred async data via `has_resolved_data`:

```python
from webcompy.hydration import has_resolved_data
```

Passing `component_id` (the component's transfer ID) returns `True` when `HYDRATION_DATA_KEY` holds an entry for that ID and `False` otherwise.

## The 3-layer transfer codec

WebComPy extends JSON serialization across the hydration boundary without external dependencies (`webcompy.hydration`):

| Layer | Handled types | Wire representation |
|---|---|---|
| Layer 0 (passthrough) | `str`, `int`, `float`, `bool`, `None`, `list`, plain `dict` | Native JSON values with zero overhead |
| Layer 1 (built-in Python types) | `datetime`, `date`, `time`, `set`, `frozenset`, `enum.Enum`, `bytes`, `decimal.Decimal`, `@dataclass` (including nested dataclasses via `dataclasses.fields()`), `tuple`, `pathlib.Path`, `uuid.UUID` | `{"__webcompy_type__": "<tag>", "__webcompy_value__": ...}` |
| Layer 2 (custom registry) | Any user or library class registered via `register_type_handler` | Checked **before** Layer 1; tag uses `{module}.{qualname}` |

Register custom types at module import time so both server SSR and browser hydration register the same handler:

```python
from webcompy.hydration import register_type_handler


class Money:
    def __init__(self, cents: int, currency: str) -> None:
        self.cents = cents
        self.currency = currency


register_type_handler(
    Money,
    encoder=lambda m: {"cents": m.cents, "currency": m.currency},
    decoder=lambda data: Money(data["cents"], data["currency"]),
)
```

Your `encoder` returns only the inner JSON-safe payload and your `decoder` receives only that inner payload—the codec handles the `{"__webcompy_type__": ..., "__webcompy_value__": ...}` envelope automatically.

## Optional payload compression

For stateful pages or embedded text resources, enable or tune stdlib `zlib` gzip compression via `WebComPyAppConfig.compression_threshold` (default `1024` bytes):

```python
from webcompy.app import WebComPyApp, WebComPyAppConfig

app = WebComPyApp(
    root_component=AppRoot,
    config=WebComPyAppConfig(
        compression_threshold=1024,  # default; set to None or 0 to disable compression
    ),
)
```

When the encoded JSON exceeds `compression_threshold` bytes, WebComPy compresses it with `zlib.compress()`, base64-encodes it, and wraps it in `{"__webcompy_compressed__": true, "__webcompy_transfer_version__": 3, "data": "..."}`. Decompression in the browser uses stdlib `zlib` and `base64` with no extra wheel dependencies.

## Flicker-free navigation with resources

Use `load_text` and `load_bytes` (from `webcompy` or `webcompy.resources`) inside `async def` components or handlers to load package-relative files through `ResourcePort`:

- **`ServerResourcePort`** reads allow-listed files from the app package on disk and records every loaded path into the page's `resources` section (per `RenderContext`, never leaking across routes).
- **`BrowserResourcePort`** checks `RESOURCE_DATA_KEY` first (instant, zero network I/O) and falls back to fetching `{base_url}_webcompy-resource/{path}` on cache miss.

During static generation, configure `resource_transfer` on `WebComPyBuildConfig` in `webcompy_config.py`:

```python
config = WebComPyBuildConfig(
    app_module,
    resource_transfer="all-text",  # "used" (default) or "all-text"
)
```

- **`"used"` (default)**: each generated page embeds only the resources loaded while rendering that route.
- **`"all-text"`**: every generated page embeds all allow-listed text files matching the fixed extension allowlist (`.md`, `.markdown`, `.txt`, `.json`, `.csv`, `.yaml`, `.yml`, `.toml`, `.svg`, `.html`, `.xml`; binary files are excluded). Client-side navigation to another page resolves those resources straight from the transferred payload with zero network requests.

For selective warming on `"used"` builds (or runtime routes), call `preload()` on `RESOURCE_PORT_KEY` in browser code:

```python
from webcompy.di import inject
from webcompy.ports import RESOURCE_PORT_KEY

port = inject(RESOURCE_PORT_KEY)
await port.preload(["documents/next_guide.md"])
```

`preload()` is a no-op on the server, warms the client cache in the background, and drops fetch errors silently so prefetching never breaks the app.

## Hydration mismatch diagnostics

During adoption, WebComPy compares SSR DOM text, attributes, tags, and child counts against the client render pass inside the open hydration window. Once the window closes (before loading-screen teardown), if any mismatches were observed, WebComPy logs **one aggregated console warning** grouped by mismatch class (`text`, `attribute`, `tag`, `node-count`, `raw_html`) and owning component ID, and exposes full `HydrationMismatchRecord` entries on `RenderContext.hydration_report`.

Matching trees produce zero console warnings and an empty `hydration_report`.

## Pitfalls

- **Direct `Signal(...)` vs `use_state(...)`**: Standalone `Signal(0)` instantiated directly (or created outside component setup / inside `@on_after_rendering`) is **not** registered for transfer and emits a `UserWarning` if `use_state` is called outside setup.
- **Branching SSR vs browser component order**: Rendering different component trees on server and browser shifts `#ordinal` counters and causes hydration mismatches. Wrap browser-only subtrees in `ClientOnly` rather than branching conditionally on `ENVIRONMENT` mid-tree.
- **Reserved `__webcompy_` dictionary keys**: Do not store user dict keys named `"__webcompy_type__"`—the codec treats any dict containing that key as a typed value envelope and logs a warning during encoding.
- **Circular references & unencodable values**: Cyclic graphs or OS handles (sockets, file objects) cannot serialize; the codec logs a warning and drops unencodable entries (replacing cycles with `None`).

## Next steps

- Learn how the pre-rendered pipeline produces `#__webcompy_data__` in [SSR & SSG](/documents/advanced/ssr-and-ssg).
- Handle async boundaries (`Suspense`, `ClientOnly`) during hydration in [Async Rendering & Boundaries](/documents/advanced/async-rendering-and-boundaries).
- Combine transferred resources with build-time asset precaching and offline fallback in [Progressive Web App](/documents/advanced/pwa).
- Review reactive primitives and composables in [Reactive State](/documents/basic/reactive-state) and [HTTP & Async](/documents/basic/http-and-async).
