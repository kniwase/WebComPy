## 1. Create SuspenseElement class

- [ ] 1.1 Create `webcompy/elements/types/_suspense.py` with `SuspenseElement` class extending `DynamicElement`
- [ ] 1.2 Implement `__init__` accepting `fallback`, `children`, `error_fallback`, and `timeout` parameters
- [ ] 1.3 Implement `_on_set_parent()` to register signal callbacks
- [ ] 1.4 Implement `_render()` with dual behavior: server environment awaits async children (with timeout), browser environment renders fallback first then swaps
- [ ] 1.5 Implement `_resolve()` method for browser-side async completion callback — replaces fallback with children using `_patch_children()`
- [ ] 1.6 Implement `_handle_error()` method for browser-side error handling — renders `error_fallback` if provided, otherwise keeps fallback and logs warning
- [ ] 1.7 Implement `_remove_element()` with proper cleanup of pending async tasks and signal callbacks
- [ ] 1.8 Implement `_hydrate_node()` for SSR/SSG hydration — detects whether content is fallback or resolved and hydrates accordingly

## 2. Add suspense() generator function

- [ ] 2.1 Add `suspense()` function to `webcompy/elements/generators.py` with parameters: `fallback`, `children`, `error_fallback=None`, `timeout=10.0`
- [ ] 2.2 Add `SuspenseElement` import to `webcompy/elements/generators.py`
- [ ] 2.3 Add `Suspense` export to `webcompy/elements/__init__.py`

## 3. Integrate async setup detection

- [ ] 3.1 Add async pending tracking to `Component.__setup()` — set a flag on the component when the setup function is async, so `Suspense` can detect pending async operations
- [ ] 3.2 Add a mechanism for `Suspense` to query whether its children subtree has pending async operations (e.g., traverse children looking for components with the async pending flag)
- [ ] 3.3 Ensure async task references are accessible so `Suspense` can `await` them in SSR/SSG and cancel them on removal

## 4. Server-side rendering integration

- [ ] 4.1 Implement the server-side render path in `SuspenseElement._render()`: use `asyncio.wait_for()` with the configured timeout to await children's async operations
- [ ] 4.2 If async operations complete within timeout, render children directly (no fallback in output)
- [ ] 4.3 If timeout expires, render fallback content and log a warning
- [ ] 4.4 If an exception occurs and `error_fallback` is provided, render error fallback; otherwise log the exception

## 5. Browser-side rendering integration

- [ ] 5.1 Implement the browser-side render path in `SuspenseElement._render()`: render fallback content immediately, then schedule async children resolution
- [ ] 5.2 When async operations complete, call `_resolve()` to replace fallback with children using `_patch_children()`
- [ ] 5.3 When async operations fail, call `_handle_error()` to render error fallback or keep fallback with logged warning
- [ ] 5.4 Ensure DOM transitions use `_patch_children()` for efficient DOM reuse when possible

## 6. Unit tests

- [ ] 6.1 Test `SuspenseElement` creation and parameter storage
- [ ] 6.2 Test that sync children render immediately without fallback
- [ ] 6.3 Test that fallback is shown when async children are pending (mock async component)
- [ ] 6.4 Test that children replace fallback when async completes (browser path)
- [ ] 6.5 Test server-side awaiting with successful resolution
- [ ] 6.6 Test server-side timeout falls back to fallback content
- [ ] 6.7 Test error fallback rendering on async failure
- [ ] 6.8 Test cleanup on element removal (signal callbacks destroyed, async tasks cancelled)
- [ ] 6.9 Test sibling Suspense elements resolve independently
- [ ] 6.10 Test `suspense()` generator function creates correct `SuspenseElement`

## 7. Spec updates and documentation

- [ ] 7.1 Update `openspec/specs/elements/spec.md` to reference the Suspense element type
- [ ] 7.2 Update `.opencode/agents/ci-review.md` file→spec mapping to include `webcompy/elements/types/_suspense.py` → `suspense` spec
- [ ] 7.3 Update `openspec/specs/async/spec.md` to mention `Suspense` as a complementary approach to `useAsyncResult`