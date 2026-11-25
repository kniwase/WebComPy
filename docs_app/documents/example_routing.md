---
title: Routing
description: Nested child routes with preserved parent layout state, dynamic path parameters, and a before_route_change redirect guard running in an isolated hash-mode router.
---

# Routing

This example demonstrates two core WebComPy routing capabilities in a single standalone app: persistent parent layouts across nested child routes (`children` + index `""`) and route protection using a `before_route_change` guard that redirects unauthorized visits to `/login`.

Use these patterns when building dashboards, documentation shells, or authenticated consoles where shared sidebars must preserve interactive state across sub-page navigation.

## What this demonstrates

- **Nested `RouterView` level reuse**: `WorkspaceLayout` holds a `sidebar_compact` signal in its own state. Navigating between `Overview` (`/workspace`), `Settings` (`/workspace/settings`), and `Item 42` (`/workspace/items/42`) updates only the inner child `RouterView()` — clicking `"Toggle Sidebar"` first proves the compact state stays intact across child switches.
- **Index child & dynamic params**: `{"path": "", "component": WorkspaceOverview}` renders the default workspace landing view, while `/workspace/items/{item_id}` extracts `context.props.path_params["item_id"]`.
- **Guard redirect and unlock flow**: Registering `router.before_route_change.append(_auth_guard)` intercepts navigation to `/admin`, returning `"/login"` when signed out (`replace_url` redirect) and allowing `/admin` once the user clicks `"Sign in as Admin"`.
- **Hash mode inside embedded iframes**: The demo configures `Router(..., mode="hash")` so in-demo route transitions update only the iframe URL fragment without altering the host query string or requiring server route rewrites.

## Key mechanisms and how to adapt

1. **History mode in full apps**: Switch to `mode="history"` and wrap dynamic route components with `lazy("pkg.module:Page", __file__)` when building top-level applications served with `webcompy start` or `webcompy generate`.
2. **Async auth checks**: Make `_auth_guard` an `async def` coroutine calling an API or reading session state — WebComPy handles latest-wins navigation cancellation if the user triggers another click mid-check.
3. **Never omit the `""` index child**: Whenever a parent route declares `"children"`, add a `{"path": "", ...}` entry if users can visit the bare parent URL (`/workspace`).

## Next steps

- Review flat routing, parameters, and `RouterLink` options in [Routing](/documents/basic/routing).
- Dive into chain level reuse rules, `lazy()` preloading, scroll restoration, and async guard cancellation in [Routing Deep Dive](/documents/advanced/routing-deep-dive).
- Synchronize state across multiple browser tabs in [Storage Sync](/documents/examples/storage-sync).
