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

`active_class` is stored RAW (`self._active_class` — the `str` or the `SignalBase[str]` exactly as given). It is NOT resolved to a cached string: the live value is read dynamically inside `_compute_class_attr()` (D5) whenever the merged-class `Computed` recomputes, so a `SignalBase` `active_class` that changes at runtime is always reflected in the rendered output.

### D2. Match computation

A private method on `TypedRouterLink`:

```python
def _target_path(self) -> str:
    to = self._to.value if isinstance(self._to, SignalBase) else self._to
    if self._path_params is not None:
        to = to.format(**self._path_params.value)
    to = to.split("?", 1)[0].split("#", 1)[0]
    stripped = to.strip("/")
    return f"/{stripped}" if stripped else "/"

def _is_active(self) -> bool:
    match = self._router.current_match.value
    if match is None:
        return False
    target = self._target_path()
    current = "/" + match.path.strip("/")
    if target == "/":
        return current == "/"
    if self._exact:
        return current == target
    return current == target or current.startswith(target + "/")
```

- `_target_path()`: resolve `to` (signal or str), apply `path_params` formatting, split off `?`/`#`, normalize to leading slash + no trailing slash (`""` → `"/"`). Matching is always on the bare path — NO mode prefix (`#`) and NO base_url prefix, because `RouteMatch.path` is already base_url-stripped in history mode (`_router.py:117-118`) and never carries a hash prefix.
- `current = "/" + match.path.strip("/")`: `RouteMatch.path` is the raw request path (`_router.py:134-135`), so it MUST be normalized identically to `_target_path()` before comparison. Without this, `to="/docs"` would not match the current path `/docs/` even though both address the same page.
- Query strings never participate: `RouteMatch.path` excludes the query (`_router.py:200-204`).
- Reading `self._router.current_match` inside `_compute_class_attr()` (a `Computed`) makes navigation a tracked dependency: `current_match` is a `@computed_property` (`_router.py:105-113`) whose recomputation is driven by the underlying `HistoryPort` signal, so every navigation (pushState, popstate, programmatic `set_path`) dirties the merged-class `Computed`.

### D3. Reactive updates via `Computed` attribute values

The `class` and `aria-current` attributes are `Computed` instances created ONCE in `TypedRouterLink.__init__` (only when `active_class is not None`) and stored as instance attributes. This is the framework's native reactive-attribute mechanism, and the empirical reason it is required here is central:

- Element attributes are applied to the DOM node ONLY at mount time (`_init_new_node` / `_adopt_node`, `elements/types/_element.py:103-118`). Re-assigning `self._attrs` and re-rendering via `_refresh()` does NOT update an already-mounted node's attributes — `_render()` only mounts/unmounts.
- Attribute updates on a mounted element flow exclusively through `SignalBase` attribute values: `_init_new_node` registers `value.on_after_updating(self._generate_attr_updater(name))` for each signal-backed attr (`_element.py:108-110`), and the updater writes/removes the DOM attribute.
- This is exactly how `href` stays reactive today: `self._href` is a `computed_property` `Computed` (`_link.py:130-144`). The active state reuses the same machinery.

A plain-string merge written into `_generate_attrs()` would therefore render correctly in SSR HTML but go stale on the client after navigation — the initial render works, the reactive update silently fails. Consequently:

- `current_match` is NEVER subscribed to `_refresh()`; instead the merged-class/`aria-current` `Computed`s read `current_match.value` and `_target_path()` (which reads `self._to` / `self._path_params`) inside their calc, so navigation, `to` changes, `path_params` changes, `active_class` signal changes, and user-`class` signal changes ALL recompute the same attributes through the single attr-updater path.
- `Computed` lifecycle needs no manual wiring: `SignalReceivable.__setattr__` (`signal/_container.py:10-15`) auto-registers any `SignalBase` assigned to an attribute as a signal member, and `__purge_signal_members__` (`_container.py:22-26`, invoked from `_remove_element` and `_detach_from_node`) destroys them on teardown — the same lifecycle as `_href` (`signal/_computed.py:99-110`).
- The existing `self._to.on_after_updating(self._refresh)` subscription (`_link.py:65-66`) is unchanged; it still handles child-text re-rendering for `to` changes.

### D4. SSR/SSG correctness

`RouteMatch.path` is computed from the request path on the server (`_compute_current_match`, `_router.py:115+`), so the FIRST render already carries the correct active class and `aria-current` in generated HTML — no client correction flash. `_is_active()` is called synchronously from the `Computed` calcs at construction (`Computed.__init__` evaluates eagerly, `_computed.py:28-32`); on the server this is a pure path comparison with no browser API access (framework invariant preserved).

`_is_active()` MUST NOT touch browser APIs — no `ENVIRONMENT` branch, no `context.window` access. (The only `ENVIRONMENT == "pyscript"` branch in `_link.py` today lives in `_on_click`, which is a browser-only event handler and never runs on the server.) The match input comes exclusively from `self._router.current_match`, whose value derives from the `HistoryPort` signal — the request path via `_compute_current_match` on the server, `history.value` in the browser.

### D5. Attribute merging in `_generate_attrs`

Two `Computed` helpers (created in `__init__`, D3):

```python
def _compute_class_attr(self) -> str | bool:
    user_class: AttrValue | None = (self._given_attrs or {}).get("class")
    base = user_class.value if isinstance(user_class, SignalBase) else user_class
    if isinstance(base, str):
        base_str = base
    elif base is None or isinstance(base, bool):
        base_str = ""
    else:
        base_str = str(base)
    ac = self._active_class
    ac_str = (ac.value if isinstance(ac, SignalBase) else ac) or ""
    if self._is_active() and ac_str:
        return f"{base_str} {ac_str}" if base_str else ac_str
    return base_str if base_str else False

def _compute_aria_current_attr(self) -> str | bool:
    return "page" if self._is_active() else False
```

And `_generate_attrs()` merges them (replacing `_link.py:122-128`):

```python
def _generate_attrs(self) -> dict[str, AttrValue]:
    attrs = self._given_attrs if self._given_attrs else {}
    if self._aria_current_attr is None:
        return {
            **{k: v for k, v in attrs.items() if not k.startswith("@")},
            "href": self._href,
            "webcompy-routerlink": True,
        }
    out: dict[str, AttrValue] = {
        **{k: v for k, v in attrs.items() if not k.startswith("@") and k != "class"},
        "href": self._href,
        "webcompy-routerlink": True,
        "aria-current": self._aria_current_attr,
    }
    if self._class_attr is not None:
        out["class"] = self._class_attr
    return out
```

Design notes:

- **Return values drive attribute removal.** `_proc_attr` (`elements/types/_base.py:152-159`) maps `False` → `None` → attribute removed, and passes `"page"` through as-is. So `_compute_class_attr` returns `False` (no `class` attribute at all) when nothing is merged, and `_compute_aria_current_attr` returns `False` when inactive. `aria-current` is therefore absent — never emptied — while inactive (D6).
- **`active_class` is never cached.** `_compute_class_attr` reads the live value (`.value` when `SignalBase`). A construction-time cached string would go stale after the signal changed.
- **User `class` stays reactive in both modes.** With `active_class` configured, the user's `SignalBase` class is read inside the merged-class `Computed` (tracked dependency). With `active_class=None`, the signal passes through unchanged and the element's own attr subscription (`_element.py:108-110`) handles it — identical to today.
- **Unsupported class types are surfaced.** When the resolved user `class` value is not `str`/`bool`/`int`/`None` (i.e., outside `AttrValue` after resolution), `_compute_class_attr` logs a `logging.warning` before the `str()` fallback, so mis-typed input is not silently swallowed. `int` converts silently to match the framework's `_proc_attr` behavior; `bool`/`None` are handled by the earlier branches.
- **Ordering:** user classes first, active class last (predictable specificity for CSS authors).

### D6. `aria-current`

`"page"` is the correct token for navigation links within a set of pages (WAI-ARIA). It is present only while active; the attribute is omitted entirely (not emptied) when inactive. `exact` does not change the token.

### D7. Edge cases

| Case | Behavior |
|---|---|
| `active_class=None` (default) | zero overhead: no subscription, no matching, no `aria-current`; rendering identical to today |
| `to="/"` | active only on exactly `/` |
| `to="/docs"` on `/docs` | active (prefix rule includes self) |
| `to="/docs"` on `/docs/` | active (both sides normalized to no trailing slash, D2) |
| `to="/docs"` on `/docsx` | NOT active (segment boundary enforced via `target + "/"`) |
| `to="/docs"` on `/docs/a?x=1` | active (query ignored) |
| 404 / no match | never active |
| `active_class=""` | treated as configured-but-empty: `aria-current` still toggles, class list unchanged |
| hash mode | matching on bare path; mode prefix never compared |

### D8. Testing approach

`webcompy_testing` provides TestRenderer + fake ports; existing router tests (`tests/test_router*.py`, `tests/test_router_view*.py`) show how to build an app with routes and drive `router.set_path`/`__set_path__` server-side. Tests assert rendered `class`/`aria-current` attributes (via `_proc_attr` on `_generate_attrs()` output) before/after navigation — no browser required. One e2e assertion can ride on the docs demo later; not required for this change.

## Code Structure

Single-file change in `packages/webcompy/src/webcompy/router/_link.py`:

- `__init__`: store `active_class`/`exact` raw; create `self._class_attr` / `self._aria_current_attr` `Computed`s when `active_class is not None` (D3).
- `_target_path()`: normalization helper (D2, trailing-slash included).
- `_is_active()`: match logic (D2, D7).
- `_compute_class_attr()` / `_compute_aria_current_attr()`: `Computed` calcs for merged class and `aria-current` (D5, D6).
- `_generate_attrs()`: merging (D5) + `aria-current` (D6).

No new module, no DI changes, no port changes, no spec changes outside `router`.
