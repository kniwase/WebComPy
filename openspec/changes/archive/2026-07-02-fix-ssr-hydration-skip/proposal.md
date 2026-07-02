# Proposal: SSR/SSG Hydration Skip

## Why

After `feat/async-rendering-pipeline`, both the SSG pipeline (`webcompy generate`) and the dev server (`webcompy start`) call `generate_html()` with `prerender=True`, so `AppDocumentRoot._render()` runs server-side. With the default `WebComPyAppConfig(hydrate=True)`, `AppDocumentRoot._render()` calls `child._hydrate_node()` on its children. `DynamicElement._hydrate_node()` recursively schedules `asyncio.ensure_future(child._render())` for each non-mounted child — a **fire-and-forget** task.

In a long-running browser event loop (`app.run()`), these fire-and-forget tasks complete eventually. In a single-shot server render (`await generate_html(...)` in either SSG or dev-server SSR), the await chain in `AppDocumentRoot._render()` returns from `for child in self._children: await child._render()` before the scheduled tasks complete. After `await generate_html` returns, `ctx.dispose()` runs and the DI scope is disposed. The still-pending tasks then execute and instantiate child `Component`s (`__init__` → `__setup` → `inject(_HEAD_PROPS_KEY)`) against a disposed DI scope, raising:

```
No provider found for InjectKey('webcompy-internal-head-props')
```

The user-visible symptom: SSG-generated HTML and dev-server SSR responses contain the `<div webcompy-component="HomePage">` shell but its children are empty. The browser's later `app.run()` re-renders, masking the defect in dev mode for end users, but the initial HTML is still incomplete and breaks SEO, OGP, and link previews.

The upcoming `feat/ssg-via-ssr` change shares the ASGI app between SSG and the dev server, but its scope is **CLI integration** (eliminating duplicate setup logic in `_generate.py` and `_server.py`). It does not address the fire-and-forget behavior in `_hydrate_node`. Once `feat/ssg-via-ssr` lands, the same SSR defect would be present in both SSG output and dev-server SSR output. This change therefore must land **before or alongside** the unification.

## What Changes

- **`WebComPyApp.__init__`** — Set `self._hydrate = self._config.hydrate and ENVIRONMENT == "pyscript"`. Hydration is fundamentally a browser concept (adopting prerendered DOM nodes in the JS runtime). The server is **generating** the prerendered content, not adopting it. By forcing `app._hydrate` to `False` in non-pyscript environments, the existing `AppDocumentRoot._render()` guard at line 92 short-circuits, and the `for child in self._children: await child._render()` await chain renders the subtree synchronously.
- **`AppDocumentRoot._render()`** — No code change. The existing `if self._app and self._app._hydrate and not self.__hydrated:` guard now correctly evaluates `False` server-side because `app._hydrate` is `False`.
- **Spec documentation** — `app-config` and `app-lifecycle` specs document that the `hydrate` config field is **only effective in the `pyscript` environment**; in `server` and any future SSR environment it is automatically disabled to guarantee a complete await-chain render.

## Capabilities

### Modified Capabilities

- `app-config`: The `hydrate` field of `WebComPyAppConfig` SHALL be effective only in the `pyscript` environment. In non-pyscript environments, `WebComPyApp.__init__` SHALL force `self._hydrate = False` regardless of the user-supplied config value.
- `app-lifecycle`: When `app._hydrate` is `False` (which is now the case in non-pyscript environments), `AppDocumentRoot._render()` SHALL skip the `child._hydrate_node()` recursion and SHALL render all children via the synchronous `await child._render()` path.

## Known Issues Addressed

- **SSG output missing routed content** — `<div webcompy-component="HomePage">` was rendered as an empty shell in the SSG-generated HTML. Caused by the fire-and-forget `asyncio.ensure_future(child._render())` task in `DynamicElement._hydrate_node()` running after `await generate_html` returned and `ctx.dispose()` was called.
- **Dev server SSR output missing routed content** — Same root cause as the SSG issue. The browser's later `app.run()` masked the defect for end users, but the initial HTML response was incomplete and broke SEO / link previews.
- **Upcoming `feat/ssg-via-ssr` SSR defect** — The upcoming SSR/SSG unification shares the ASGI app between SSG and the dev server, so the same defect would surface in both paths after unification. This change makes both paths produce complete output.

## Non-goals

- No changes to the public API of `WebComPyApp` or `WebComPyAppConfig` (only the internal `_hydrate` attribute is forced)
- No removal or refactoring of `DynamicElement._hydrate_node()` — the fire-and-forget path remains correct for the browser environment
- No changes to `app-lifecycle` spec's description of `hydrate=True` behavior in the browser
- No introduction of new ports or abstractions (see "Future work" below for the longer-term refactor)
- No changes to the SSG pipeline's `webcompy generate` CLI
- No coordination required with the upcoming `feat/ssg-via-ssr` change (this change is independent and provides a clean baseline for it)

## Future work (out of scope for this change)

This change applies a minimal, environment-conditional guard at the `WebComPyApp` initialization level. A more architecturally clean solution would address the root cause — `asyncio.ensure_future` being used for the initial render where the event loop may not survive the call. The following alternatives were considered and deferred:

- **Option B — DOM port abstraction for hydration**: Move hydration responsibility into the DOM port layer. `BrowserDOMPort._init_node` would adopt prerendered nodes; `ServerDOMPort._init_node` would always create new ones. This removes `_hydrate_node()` and its fire-and-forget task from the element tree entirely. Larger change with broad spec impact (`port-abstraction`, `elements`, `app-lifecycle`).
- **Option C — Render scheduler port**: Introduce a `RenderSchedulerPort` (browser: `asyncio.ensure_future`; server: synchronous, returned coroutine awaited by caller). `DynamicElement._hydrate_node()` would call `inject(RENDER_SCHEDULER_PORT_KEY).schedule(child._render())`. The `ensure_future` call is centralized into a single injectable port. Mid-sized change.

These alternatives are documented for future planning; this change takes the minimum-impact route to unblock the SSG/SSR output defect.

## Dependencies

- **Requires** `feat/async-rendering-pipeline` — the issue manifests specifically because `generate_html()` is `async` and the fire-and-forget tasks don't survive the `await` return.

## Impact

- **Affected modules**: `packages/webcompy/src/webcompy/app/_app.py` (1-line change), `packages/webcompy/src/webcompy/app/_root_component.py` (no change), `packages/webcompy/src/webcompy/elements/types/_dynamic.py` (no change)
- **Affected specs**: `app-config`, `app-lifecycle`, `async-rendering`
- **Backward compatible**: All existing user code continues to work. The `hydrate=True` config field is honored in the browser; in the server it has no effect (but also no negative impact — the SSG and dev server output is now correct).
- **Testing**: Existing E2E tests (`docs-home` group) verify `What is WebComPy` heading is visible in the SSG output. New E2E assertion confirms the `HomePage` DIV's children are non-empty in the SSG-generated HTML (pre-fix the DIV was `<div webcompy-component="HomePage" webcompy-cid-...=""></div>`).
