# Design: RouterLink Active State

## Decisions

### D1. API

```python
class TypedRouterLink(...):
    def __init__(
        self,
        *,
        to: str | SignalBase[str],
        text: list[str | SignalBase[Any]],
        params: SignalBase[ParamsType] | None = None,
        query: SignalBase[QueryParamsType] | None = None,
        path_params: SignalBase[PathParamsType] | None = None,
        attrs: dict[str, AttrValue] | None = None,
        active_class: str | SignalBase[str] | None = None,   # NEW
        exact: bool = False,                                  # NEW
    ) -> None: ...
```

`RouterLink` (the `TypeAlias`) inherits the new kwargs automatically.

### D2. Match computation

A private method on `TypedRouterLink`:

```python
def _is_active(self) -> bool:
    if self._active_class_value is None:          # no active_class configured
        return False
    match = self._router.current_match            # Computed; tracked when read in a Computed context
    if match is None:
        return False
    target = self._target_path()                  # normalized path portion of `to` (+ path_params)
    current = _normalize(match.path)              # strip base_url already handled by RouteMatch.path; see D4
    if target == "/":
        return current == "/"
    if self._exact:
        return current == target
    return current == target or current.startswith(target + "/")
```

- `_target_path()`: resolve `to` (signal or str), apply `path_params` formatting, split off `?`/`#`, strip base_url prefix in history mode, normalize to leading slash + no trailing slash (`""` → `"/"`). Reuses the same normalization philosophy as `_href` (`_link.py:130-144`) but WITHOUT mode prefix (`#`) — matching is always on the bare path.
- Query strings never participate (Vue Router behavior).

### D3. Reactive updates via the existing `_refresh` pattern

`TypedRouterLink.__init__` already subscribes to `self._to` (`_link.py:65-66`). Add, only when `active_class is not None`:

```python
self._add_callback_node(self._router.current_match.on_after_updating(self._refresh))
```

`current_match` is a `@computed_property` (`_router.py:105-113`) whose recomputation is driven by the underlying `HistoryPort` signal, so every navigation (pushState, popstate, programmatic `set_path`) triggers `_refresh()`. `_refresh()` regenerates attrs via `_generate_attrs()` and re-renders — the exact same proven path as `to` changes, including correct event-handler/proxy lifecycle. No new render machinery is introduced.

If `active_class` is a `SignalBase`, subscribe to it as well (same pattern) so runtime changes to the class name propagate.

### D4. SSR/SSG correctness

`RouteMatch.path` is computed from the request path on the server (`_compute_current_match`, `_router.py:115+`), so the FIRST render already carries the correct active class and `aria-current` in generated HTML — no client correction flash. `_is_active()` is called synchronously from `_generate_attrs()`; on the server this is a pure path comparison with no browser API access (framework invariant preserved).

### D5. Attribute merging in `_generate_attrs`

Current implementation (`_link.py:122-128`) passes user `attrs` through and adds `href` + `webcompy-routerlink`. Extend:

```python
def _generate_attrs(self) -> dict[str, AttrValue]:
    attrs = dict(self._given_attrs) if self._given_attrs else {}
    user_class = attrs.pop("class", None)
    out: dict[str, AttrValue] = {
        **{k: v for k, v in attrs.items() if not k.startswith("@")},
        "href": self._href,
        "webcompy-routerlink": True,
    }
    classes: list[str] = []
    if isinstance(user_class, str) and user_class:
        classes.append(user_class)
    if self._is_active():
        ac = self._active_class_value
        if ac:
            classes.append(ac)
        out["aria-current"] = "page"
    if user_class is not None and not isinstance(user_class, str):
        out["class"] = user_class            # signal/Computed class passes through unchanged
        if self._is_active() and self._active_class_value:
            out["class"] = _MergedClass(user_class, self._active_class_value)  # see below
    elif classes:
        out["class"] = " ".join(classes)
    return out
```

Simplification (preferred in implementation): when the user `class` is a `SignalBase`, wrap it with the active class in a `Computed` (`Computed(lambda: f"{base} {ac}" if active else base)`) — the Element attr system already renders `Computed` attribute values reactively (template engine contract). This keeps one code path and full reactivity. When user `class` is a plain str or absent, plain string merging suffices.

Ordering: user classes first, active class last (predictable specificity for CSS authors).

### D6. `aria-current`

`"page"` is the correct token for navigation links within a set of pages (WAI-ARIA). It is present only while active; the attribute is omitted entirely (not emptied) when inactive. `exact` does not change the token.

### D7. Edge cases

| Case | Behavior |
|---|---|
| `active_class=None` (default) | zero overhead: no subscription, no matching, no `aria-current`; rendering identical to today |
| `to="/"` | active only on exactly `/` |
| `to="/docs"` on `/docs` | active (prefix rule includes self) |
| `to="/docs"` on `/docsx` | NOT active (segment boundary enforced via `target + "/"`) |
| `to="/docs"` on `/docs/a?x=1` | active (query ignored) |
| 404 / no match | never active |
| `active_class=""` | treated as configured-but-empty: `aria-current` still toggles, class list unchanged |
| hash mode | matching on bare path; mode prefix never compared |

### D8. Testing approach

`webcompy_testing` provides TestRenderer + fake ports; existing router tests (`tests/test_router*.py`, `tests/test_router_view*.py`) show how to build an app with routes and drive `router.set_path`/`__set_path__` server-side. Tests assert rendered `class`/`aria-current` attributes before/after navigation — no browser required. One e2e assertion can ride on the docs demo later; not required for this change.

## Code Structure

Single-file change in `packages/webcompy/src/webcompy/router/_link.py`:

- `__init__`: store `active_class`/`exact`, resolve `_active_class_value` (str from signal or literal), add subscriptions (D3).
- `_target_path()`: normalization helper.
- `_is_active()`: match logic (D2).
- `_generate_attrs()`: merging (D5) + `aria-current` (D6).

No new module, no DI changes, no port changes, no spec changes outside `router`.
