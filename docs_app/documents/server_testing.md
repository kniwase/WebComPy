---
title: Testing
description: Test WebComPy components, signals, HTTP clients, and SSR/ASGI apps without a browser using webcompy_testing, TestRenderer, and fake ports.
---

# Testing

The `webcompy-testing` package (`import webcompy_testing`) lets you mount components into an in-memory virtual DOM, trigger signal-driven event handlers, stub network/realtime ports, and render full SSR HTML responses under standard `pytest` — without booting Chromium or PyScript.

Use browserless `webcompy_testing` unit tests as your fast default for component logic, state updates, DI wiring, and HTML rendering; reserve PyScript evaluation (`inspect pyexec`) and Playwright E2E checks for browser-specific DOM layout, custom-element connection hooks, and end-to-end navigation.

## Application testing tiers

| Tier | Tools | When to use | Speed |
|---|---|---|---|
| **Tier 1: Unit & SSR** | `pytest` + `webcompy_testing` (`TestRenderer`, fake ports, `create_test_asgi_app`) | Component markup, events, signals, DI overrides, typed HTTP handling, SSR output | Milliseconds |
| **Tier 2: Browser PyScript** | `python -m webcompy inspect pyexec` (or PyScript harness tests) | Verifying behavior specific to Pyodide/Emscripten or JS interop | Seconds |
| **Tier 3: End-to-end** | Playwright / `python -m webcompy inspect` against `start` or `dist/` | Real browser hydration, navigation, CSS, worker registration, `@on_mounted` DOM hooks | Seconds per suite |

Import utilities directly from `webcompy_testing` (`webcompy.testing` exists only as a legacy compatibility re-export shim and should not be used in new code).

## Rendering components with `TestRenderer`

`TestRenderer.render(component, parent_scope=None)` builds a browser-style `DIScope` populated with fake browser ports, mounts the root element inside a synthetic document `<body>`, drains pending scheduler tasks (`FakeAsyncSchedulerPort.await_pending()`), and returns a `TestRendererResult`. Use it as a context manager so `scope.dispose()` runs cleanly at teardown:

```python
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.signal import use_computed, use_state
from webcompy_testing import TestRenderer, VirtualDOMEvent


@define_component()
def CounterButton(context: ComponentContext[None]):
    count = use_state(lambda: 0)

    def _increment(_ev) -> None:
        count.value += 1

    return html.DIV(
        {"class": "counter"},
        html.SPAN({}, use_computed(lambda: f"Count: {count.value}")),
        html.BUTTON({"type": "button", "@click": _increment}, "Increment"),
    )


def test_counter_updates_on_click() -> None:
    with TestRenderer.render(CounterButton) as result:
        result.assert_element_count("button", 1)
        assert result.find_by_attribute("class", "counter") is not None
        span = result.query_selector("span")
        assert span is not None and span.textContent == "Count: 0"

        button = result.query_selector("button")
        assert button is not None
        button.dispatchEvent(VirtualDOMEvent("click"))

        assert span.textContent == "Count: 1"
```

Because Signal bindings mutate the `VirtualDOMNode` tree directly inside the fake DOM, no separate `rerender()` call is needed after `dispatchEvent(...)`.

### `TestRendererResult` methods and properties

| Member | Returns | Purpose |
|---|---|---|
| `query_selector(tag)` | `VirtualDOMNode \| None` | First descendant matching tag name (case-insensitive) |
| `query_selector_all(tag)` | `list[VirtualDOMNode]` | All descendants matching tag name |
| `find_by_text(text)` | `VirtualDOMNode \| None` | First non-comment node whose `textContent` equals `text` |
| `find_by_attribute(name, value)` | `VirtualDOMNode \| None` | First node with attribute `name == value` |
| `to_html(pretty=False)` | `str` | Serializes mounted tree (`pretty=True` normalizes through `format_html`) |
| `assert_element_count(tag, count)` | `None` | Raises `AssertionError` if tag count differs from `count` |
| `assert_has_class(cls)` | `None` | Raises `AssertionError` if `cls` is absent from the mounted root node's `class` attribute |
| `body_node` | `VirtualDOMNode \| None` | Synthetic document `<body>` node owning the mounted root |
| `transition_port` | `FakeTransitionPort \| None` | Installed transition double (`flush_frame()`, `advance_time()`, `flush_all()`) |
| `media_query_port` | `FakeMediaQueryPort \| None` | Installed media-query double (`set_prefers_dark()`, `set_prefers_reduced_motion()`) |
| `event_source_port` | `FakeEventSourcePort \| None` | Installed SSE double (`emit_open()`, `emit_event()`, `emit_error()`, `emit_close()`) |
| `websocket_port` | `FakeWebSocketPort \| None` | Installed WebSocket double (`emit_open()`, `emit_message()`, `emit_close()`, `sent_frames()`) |
| `close()` | `None` | Disposes the render `DIScope` and resets `_active_di_scope` |

## Fake ports inventory

`TestRenderer.render()` installs browser-like fakes automatically for DOM, host, FFI, custom elements, transitions, media queries, event sources, WebSockets, and task scheduling. Provide network mocks like `FakeFetchPort` via `parent_scope=DIScope({FETCH_PORT_KEY: ...})`.

| Fake class (`webcompy_testing`) | Port DI key (`webcompy.ports`) | Capabilities & test hooks |
|---|---|---|
| `FakeFetchPort` + `RecordedRequest` | `FETCH_PORT_KEY` | Maps `(method, url)` to canned `Response` or `streams` chunk lists; records `requests` and `aborted_streams`; raises `KeyError` for unregistered requests |
| `FakeBrowserDOMPort` + `FakeDOMNode` | `DOM_PORT_KEY` | In-memory `<html>`/`<head>`/`<body>` tree with `query_selector`, `get_element_by_id`, document listener tracking (`dispatch_document_event`), `splitText`, and mutation counters (`textContent_write_count`, `setAttribute_count`) |
| `FakeBrowserHostPort` | `HOST_PORT_KEY` | Runs `schedule_macro_task` synchronously; records window listeners (`dispatch_window_event`) and JS global getters |
| `FakeBrowserFFIPort` | `FFI_PORT_KEY` | Wraps callbacks with `unittest.mock.MagicMock` proxies; no-op JS conversion and dictionary assignment |
| `FakeCustomElementPort` | `CUSTOM_ELEMENT_PORT_KEY` | Records `ensure_defined_calls`, `bind_calls`, and `disposed_bindings`; configurable `connected` flag |
| `FakeAsyncSchedulerPort` | `ASYNC_SCHEDULER_PORT_KEY` | Queues scheduled coroutines into `_PendingTask` stand-ins; deterministic `drain()` and `await_pending(only_render=...)` |
| `FakeHistoryPort` | `HISTORY_PORT_KEY` | Records `pushed_urls` and `replaced_urls` for `push_url()` and `replace_url()` |
| `FakeEventSourcePort` | `EVENT_SOURCE_PORT_KEY` | Instance-local connection map (`open_calls`, `open_connections`) with `emit_open`, `emit_event`, `emit_error`, `emit_close` |
| `FakeWebSocketPort` | `WEBSOCKET_PORT_KEY` | Instance-local connection map recording sent text frames (`sent_frames(url)`) plus `emit_*` helpers |
| `FakeTransitionPort` | `TRANSITION_PORT_KEY` | Logical frame queue and virtual clock (`flush_frame`, `advance_time`, `flush_all`, `set_style`, `set_enabled`) |
| `FakeMediaQueryPort` | `MEDIA_QUERY_PORT_KEY` | Controllable `prefers_dark` and `prefers_reduced_motion` flags |

## App, SSR, and ASGI test helpers

| Helper (`webcompy_testing`) | Purpose |
|---|---|
| `create_test_app(root_component=..., **config_overrides)` | Creates a minimal `WebComPyApp` configured with `configure_server_context(app)` and filters keyword overrides to valid `WebComPyAppConfig` fields |
| `create_test_asgi_app(app)` | Wraps a `WebComPyApp` in a lightweight Starlette ASGI app (`{path:path}` in history mode, `/` in hash mode) that allocates and disposes a `ServerRenderContext` per request without building wheels or downloading runtime assets — ready for `httpx.AsyncClient(transport=httpx.ASGITransport(app=asgi))` |
| `render_app_html(app, path="/", **kwargs)` | Synchronously runs one SSR render (`app.create_render_context` -> `generate_html` -> `ctx.dispose()`) |
| `format_html(html)` | Normalizes HTML whitespace and attribute ordering via `beautifulsoup4` for deterministic comparisons |
| `mock_app_run()` | Context manager turning `WebComPyApp.run` into a no-op so modules calling `app.run()` at top level can be imported in tests |
| `restore_signal_values(component, signals_data)` | Low-level test helper assigning decoded values onto `component.__signal_members__` |
| `run_sync(coro)` | Runs async coroutines from sync tests cleanly (`asyncio.run`, or `nest_asyncio2.apply(loop)` when called inside an active event loop) |

## Recipe: testing a component that fetches data

Combine `FakeFetchPort`, `Response` (`webcompy.ports`), `FETCH_PORT_KEY`, `DIScope`, and `TestRenderer.render(..., parent_scope=scope)` to test an async data-loading component synchronously with zero real HTTP calls:

```python
from webcompy.ajax import HttpClient
from webcompy.components import ComponentContext, define_component, use_async_result
from webcompy.di import DIScope
from webcompy.elements import html
from webcompy.ports import FETCH_PORT_KEY, Response
from webcompy.signal import use_computed
from webcompy_testing import FakeFetchPort, TestRenderer


@define_component()
def TaskSummary(context: ComponentContext[None]):
    tasks = use_async_result(lambda: HttpClient.get("/api/tasks", response_type=list[dict]))
    return html.DIV(
        {"class": "task-summary"},
        use_computed(
            lambda: (
                f"Loaded {len(tasks.data.value or [])} tasks"
                if not tasks.is_error.value
                else "Request failed"
            )
        ),
    )


def test_task_summary_fetches_and_renders() -> None:
    fake_fetch = FakeFetchPort(
        responses={
            ("GET", "/api/tasks"): Response(
                text='[{"title": "Docs"}, {"title": "Tests"}]',
                headers={"content-type": "application/json"},
                status_code=200,
                status_text="OK",
                ok=True,
            )
        }
    )
    scope = DIScope({FETCH_PORT_KEY: fake_fetch})

    with TestRenderer.render(TaskSummary, parent_scope=scope) as result:
        assert "Loaded 2 tasks" in result.to_html()
        assert len(fake_fetch.requests) == 1
        assert fake_fetch.requests[0].url == "/api/tasks"
```

Pass the same `FakeFetchPort` pattern (or `create_test_asgi_app(app)` with `app.provide(FETCH_PORT_KEY, fake_fetch)`) when verifying full-route SSR output with `httpx`.

## Behavior notes and pitfalls

- **`on_mounted` vs fake DOM connection**: `FakeCustomElementPort.is_document_connected()` returns `False` by default and synthetic appends to `FakeDOMNode` do not fire browser `connectedCallback` hooks automatically unless driving adoption; validate real browser DOM connection lifecycles in Playwright E2E tests (see [Custom Elements](/documents/advanced/custom-elements)).
- **Closing fetch-backed realtime loops before `await_pending()`**: Non-GET `use_event_source` and WebSocket reconnect loops schedule ongoing background coroutines. Calling `await_pending()` / `drain()` on `FakeAsyncSchedulerPort` waits until scheduled tasks complete, so close the handle before draining (or run such tests on an `asyncio` event loop without the fake scheduler).
- **Sharing test scopes**: Never share a mutated `DIScope` across unrelated tests; construct a fresh `DIScope` per test case and rely on `with TestRenderer.render(...) as result:` to dispose child scopes and reset `_active_di_scope`.

## Next steps

- Learn how `DIScope` child scoping and port injection work internally in [Dependency Injection Deep Dive](/documents/advanced/dependency-injection-deep-dive).
- Test HTTP status codes and error states alongside typed responses in [HTTP & Async](/documents/basic/http-and-async).
- Embed or mount full ASGI applications under test in [ASGI Integration](/documents/server/asgi-integration).
- Run browser assertions and headless PyScript checks with `webcompy inspect` in [CLI Reference](/documents/server/cli-reference).
- Full API: [Testing API](/documents/api/testing).
