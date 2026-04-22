# Router — Delta: feat-lazy-routing

## Changes

### Added: lazy() function for deferred module import

The `lazy()` helper SHALL accept a module path string (e.g., `"pages.docs:DocsPage"`) and return a `LazyComponentGenerator` (subclass of `ComponentGenerator`) that defers `importlib.import_module()` until the route is first matched. The `lazy()` function SHALL also accept an optional `shell` parameter for a loading placeholder component.

`LazyComponentGenerator._resolve()` SHALL perform the actual import and cache the result. `_preload()` SHALL resolve without rendering, enabling speculative loading.

### Added: Shell placeholder rendering

When a `LazyComponentGenerator` has a `shell` component and has not yet resolved, `RouterView` SHALL render the shell component as a placeholder. After resolution, the `SwitchElement._refresh()` mechanism naturally replaces the shell with the real component.

### Added: RouterLink hover preloading

`RouterLink` SHALL add a `@mouseenter` event handler that calls `_preload()` on the target `LazyComponentGenerator` when hovered, enabling speculative module import before the user clicks.