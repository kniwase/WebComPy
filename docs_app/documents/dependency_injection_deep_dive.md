---
title: Dependency Injection Deep Dive
description: Understand WebComPy's hierarchical DIScope tree, lazy component child scopes, per-render-context port isolation, and clean service/fake overrides in unit tests.
---

# Dependency Injection Deep Dive

WebComPy replaces global singletons with a lexical tree of `DIScope` containers. An app-level root provides router and application configuration, each `RenderContext` isolates browser/server ports and middleware registries per request, and components calling `provide()` lazily spawn child scopes that descend only down their own subtree.

## When to use

- **Sharing services, stores, repositories, or configuration across deeply nested subtrees without prop drilling** — use `provide()` and `inject()`.
- **Swapping production services or ports (`FETCH_PORT_KEY`, API clients) for fakes in unit tests** — wrap `TestRenderer.render(..., parent_scope=...)` or `with DIScope(...):`.
- **Keeping state strictly local to one component** — use [`use_state`](/documents/basic/reactive-state) or pass props ([Components](/documents/basic/components)).
- **Intercepting all HTTP/RPC requests globally or per request** — add interceptors in [Middleware](/documents/advanced/middleware) or [Plugins](/documents/advanced/plugins).

## Setup

Create unique typed tokens with `InjectKey[T]` (or use a custom Python class as a key), register values with `provide()` / `app.provide()`, and resolve them via `inject()` (`webcompy.di`):

```python
from typing import Protocol

from webcompy import WebComPyApp
from webcompy.components import ComponentContext, define_component
from webcompy.di import InjectKey, InjectionError, inject, provide
from webcompy.elements import html


class UserService(Protocol):
    def current_name(self) -> str: ...


UserServiceKey = InjectKey[UserService]("user-service")


class LiveUserService:
    def current_name(self) -> str:
        return "Ada Lovelace"


@define_component()
def GreetingBanner(context: ComponentContext[None]):
    # Walks upward from component scope -> ancestors -> RenderContext root scope
    user_service = inject(UserServiceKey)
    return html.P({}, f"Signed in as {user_service.current_name()}")


app = WebComPyApp(root_component=GreetingBanner)
app.provide(UserServiceKey, LiveUserService())
```

Pass `default=` (`inject(OptionalKey, default=None)`) when an unprovided dependency should fall back gracefully rather than raising `InjectionError`.

## Recipes

### 1. Swap services and ports cleanly in tests (`service + fake`)

Override `UserServiceKey` — or framework ports like `FETCH_PORT_KEY` — inside an explicit `DIScope` passed to `TestRenderer.render(..., parent_scope=scope)` without modifying production code or leaking state across test cases:

```python
from webcompy.di import DIScope
from webcompy.ports import FETCH_PORT_KEY, Response
from webcompy_testing import FakeFetchPort, TestRenderer


class FakeUserService:
    def current_name(self) -> str:
        return "Test Runner"


def test_greeting_uses_injected_service() -> None:
    fake_fetch = FakeFetchPort(
        responses={
            ("GET", "/api/status"): Response(
                text='{"ok": true}',
                headers={"Content-Type": "application/json"},
                status_code=200,
                status_text="OK",
                ok=True,
            )
        }
    )
    parent_scope = DIScope(
        {
            UserServiceKey: FakeUserService(),
            FETCH_PORT_KEY: fake_fetch,
        }
    )

    with TestRenderer.render(GreetingBanner, parent_scope=parent_scope) as result:
        assert "Signed in as Test Runner" in result.to_html()
```

You can also use `create_test_app(root_component=...)` from `webcompy_testing` when testing full server-render HTML output (`render_app_html(app)`).

### 2. Shadow a provider inside a component subtree with reactive signals

`provide(key, value)` inside a parent component creates one child scope for that component, leaving sibling subtrees untouched. Providing a `Signal` shares live reactive updates downward:

```python
from webcompy import Signal, use_computed, use_state
from webcompy.components import ComponentContext, define_component
from webcompy.di import InjectKey, inject, provide
from webcompy.elements import html

AccentKey = InjectKey[Signal[str]]("accent-color")


@define_component()
def ThemedButton(context: ComponentContext[None]):
    accent = inject(AccentKey)
    return html.BUTTON(
        {"style": use_computed(lambda: f"border-color: {accent.value}")},
        "Action",
    )


@define_component()
def SubtreeThemeOverride(context: ComponentContext[None]):
    local_accent = use_state(lambda: "#0ea5e9")
    provide(AccentKey, local_accent)
    return ThemedButton(None)
```

### 3. Enter standalone scopes with `DIScope` and `RenderContext`

`DIScope` implements `__enter__` / `__exit__` to bind and unwind `_active_di_scope` cleanly via Python `ContextVar` tokens. On a `WebComPyApp`, obtain an isolated server render scope via `app.create_render_context("/")`:

```python
from webcompy.di import DIScope, InjectKey, inject

ConfigUrlKey = InjectKey[str]("config-url")

with DIScope({ConfigUrlKey: "https://api.example.com"}) as outer:
    assert inject(ConfigUrlKey) == "https://api.example.com"
    with outer.create_child() as inner:
        inner.provide(ConfigUrlKey, "https://staging.example.com")
        assert inject(ConfigUrlKey) == "https://staging.example.com"
    assert inject(ConfigUrlKey) == "https://api.example.com"
```

When the `with` block exits, `_active_di_scope` automatically restores to the prior context even if child scopes were entered inside it.

## Behavior notes

- **Lazy component child scopes**: Components that never call `provide()` allocate no `DIScope` at all and resolve directly through their parent scope. The first `provide()` inside a component setup lazily creates a child scope; subsequent `provide()` calls in the same setup share that single child scope.
- **Lazy callable factories**: When a non-class callable (`lambda: HeavyClient()`) is stored directly inside a `DIScope` (`DIScope({ClientKey: lambda: HeavyClient()})`), `DIScope.inject()` invokes the factory once on first lookup and caches the resulting value in that scope. Class objects stored as values or keys (`isinstance(val, type)`) are never auto-instantiated.
- **Per-request `RenderContext` isolation & port provisioning**: Every SSR request in `create_asgi_app()` runs inside its own `RenderContext` (`_register_ports()` populates browser, server, or testing ports for the 15 framework port keys before running plugin `get_providers()` / `on_render_context_init()`), and tears down its entire scope tree in `finally: ctx.dispose()`. Overlapping async render contexts unwind predecessor chains cleanly without unbinding live sibling contexts.
- **`DIScope.dispose()` lifecycle**: Disposing a scope recursively disposes all descendant scopes and clears provider maps (subsequent `provide()` / `create_child()` raise `RuntimeError`, while `inject()` skips disposed nodes). Provided objects are **not** automatically closed on dispose — register cleanup callbacks with `on_before_destroy` inside components.
- **`app.provide(...)` deferral & `app.di_scope`**: Calling `app.provide(key, value)` before rendering queues the registration and replays it onto every newly created `RenderContext`. `app.di_scope` is a convenience property exposing the active context's `DIScope` while a `RenderContext` is entered (`app.run()` or `app.create_render_context(...)`) and raises `AttributeError` otherwise.

## Pitfalls

- **Accessing `app.di_scope` outside a `RenderContext`**: Calling `app.di_scope` at module import time before rendering starts raises `AttributeError`. Use `app.provide(key, value)` at startup, `with app.create_render_context("/")`, or standalone `with DIScope(...):` in tests.
- **Using built-in types (`str`, `int`, `dict`) as DI keys**: Built-in classes collide across unrelated packages and make resolution ambiguous. Always define `InjectKey[T]("descriptive-name")` (each `InjectKey` instance compares by unique identity even if two keys share a display string) or a dedicated application class.
- **Re-providing framework middleware registries**: Calling `provide(FETCH_MIDDLEWARE_KEY, ...)` overwrites middlewares added by plugins or earlier setup. Use `add_fetch_middleware` / `add_rpc_middleware` (see [Middleware](/documents/advanced/middleware)).
- **Expecting plain injected variables to stay reactive**: Assigning a new object to a local variable (`theme = Signal("light")`) after `provide(ThemeKey, theme)` does not update callers that already resolved `ThemeKey`. Provide a `Signal` and mutate `.value` instead.
- **Relying on `DIScope.dispose()` for resource teardown**: Open connections or timers stored in DI are not automatically closed when a scope disposes; wire teardown explicitly with `on_before_destroy`.

## Next steps

- Register request/response interceptors through DI registries in [Middleware](/documents/advanced/middleware).
- Supply providers, ports, and lifecycle hooks from external modules in [Plugins](/documents/advanced/plugins).
- Trace per-request `RenderContext` creation and teardown during SSR/SSG in [SSR & SSG](/documents/advanced/ssr-and-ssg).
- Revisit component trees and reactive primitives in [Components](/documents/basic/components) and [Reactive State](/documents/basic/reactive-state).
