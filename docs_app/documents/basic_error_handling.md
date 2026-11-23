---
title: Error Handling
description: Isolate subtree rendering and event errors with ErrorBoundary, render custom fallback UI, and allow users to retry via reset().
---

# Error Handling

An uncaught exception inside one widget should not break an entire page. `ErrorBoundary` (`webcompy.elements`) wraps a component or element subtree, catches errors thrown while rendering its children, renders a fallback view in place, and gives you a `reset` callback so users can recover without reloading the page.

## At a glance

```python
from webcompy import use_state
from webcompy.components import ComponentContext, define_component
from webcompy.elements import ErrorBoundary, html


@define_component()
def RiskyPanel(context: ComponentContext[dict[str, bool]]):
    broken = context.props.get("broken", True) if context.props else False
    if broken:
        raise RuntimeError("Could not build panel")
    return html.P({}, "Panel rendered cleanly.")


@define_component()
def ProtectedSection(context: ComponentContext[None]):
    should_fail = use_state(lambda: True)

    def recover(reset):
        should_fail.value = False
        reset()

    return ErrorBoundary(
        children=lambda: RiskyPanel({"broken": should_fail.value}),
        fallback=lambda error, reset: html.DIV(
            {"class": "error-box"},
            html.P({}, f"Something went wrong: {error}"),
            html.BUTTON({"type": "button", "@click": lambda _ev: recover(reset)}, "Try again"),
        ),
        on_error=lambda err: print("Captured error:", err),
    )
```

## `ErrorBoundary` parameters

`ErrorBoundary` takes two required lazy callables and two optional controls:

| Parameter | Type | Description |
|---|---|---|
| `children` | `() -> ElementChildren` | Zero-argument generator building the protected subtree |
| `fallback` | `(Exception, () -> None) -> ElementChildren` | Generator called with `(error, reset)` when an error is caught |
| `on_error` | `(Exception) -> Any \| None` | Optional callback invoked whenever the boundary catches an exception (useful for logging or telemetry) |
| `catch_events` | `bool` | When `True`, also catches exceptions raised inside descendant `@event` handlers (default `False`) |

Passing `children` as a `lambda: ...` lets `ErrorBoundary` catch errors thrown during child evaluation as well as subsequent reactive swaps inside that boundary.

## Recovering with `reset()` and `catch_events`

- **Retrying via `reset()`**: calling `reset()` inside a fallback button handler tears down the fallback UI and invokes `children()` again. Update whatever broken signal or input caused the failure before calling `reset()`, otherwise the retry will re-enter the fallback.
- **Event handler errors (`catch_events=True`)**: by default (`catch_events=False`), exceptions raised inside DOM event callbacks (`@click`, `@submit`) bubble to global reporting rather than unmounting the component tree. Set `catch_events=True` when an interactive subtree should swap to the fallback UI if a user action throws.

```python
ErrorBoundary(
    children=lambda: InteractiveEditor({}),
    fallback=lambda err, reset: html.DIV(
        {},
        html.P({}, f"Action failed: {err}"),
        html.BUTTON({"@click": lambda _ev: reset()}, "Reload editor"),
    ),
    catch_events=True,
)
```

## Notes & caveats

- Exceptions raised inside the `fallback` generator itself propagate past that boundary (or to an outer ancestor `ErrorBoundary`, if present).
- Asynchronous operations started via `use_async_result()` track failures on `result.is_error` / `result.error` so you can handle network errors inline rather than throwing during render.

## Next steps

- Handle network and API errors inline with `use_async_result()` in [HTTP & Async](/documents/basic/http-and-async).
- Render accessible inline status banners using `Alert` in [Disclosure & Feedback](/documents/basic/disclosure).
- See how SSR-tolerant boundaries vs SSG fail-fast builds behave in [SSR & SSG](/documents/advanced/ssr-and-ssg) and how `Suspense(error_fallback=...)` escalates to boundaries in [Async Rendering & Boundaries](/documents/advanced/async-rendering-and-boundaries).
- Advanced topics coming in Advanced Usage: `WebComPyAppConfig.on_error` and `@on_error_captured` lifecycle hooks.
