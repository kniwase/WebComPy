# Proposal: Scroll Restoration

## Why

In a client-side routed app, the browser's native scroll handling breaks: navigating "Back" no longer returns the user to where they were on a long page, because the SPA re-renders content after the browser's own restoration attempt, and new-page navigations leave the scroll wherever the previous page had it. Users experience this as "the back button is broken." Every major router ships a solution (Vue Router `scrollBehavior`, React Router `<ScrollRestoration>`, Angular `scrollPositionRestoration`, SvelteKit built-in). WebComPy currently has no scroll management at all — no scroll code exists anywhere in the codebase.

## What Changes

- **Default-on scroll restoration** for browser apps (user decision: enabled by default, opt-out via config):
  - **New navigation** (push: `RouterLink` click, programmatic `set_path`) → scroll to the top of the new page.
  - **History traversal** (popstate: Back/Forward) → restore the scroll position saved when that page was left; first visit to a path scrolls to top.
- **`history.scrollRestoration = "manual"`** is set once at startup so the framework (not the browser) owns scroll behavior — the standard SPA approach, required because re-rendering happens after the browser's native restore.
- **Position storage**: in-memory per-session map of `path → (x, y)`, captured on the outgoing page at every navigation. No `history.state` patching, no persistence.
- **Post-render timing**: restoration is scheduled via `HostPort.schedule_macro_task` so it runs after the synchronous navigation + render pipeline; if the document is still shorter than the saved offset (async content such as `Suspense` or lazy routes), restoration retries on subsequent macro tasks (bounded retries, then gives up).
- **Opt-out**: `WebComPyAppConfig.scroll_restoration: bool = True`; setting it to `False` disables all behavior and leaves `scrollRestoration` untouched.
- **SSR/SSG unaffected**: the controller exists only in the browser; server rendering performs no scroll operations.

## Capabilities

### New Capabilities

- `scroll-restoration`: the scroll manager, save/restore semantics, post-render scheduling and retry policy, default-on behavior with config opt-out.

### Modified Capabilities

- `app-config`: adds `WebComPyAppConfig.scroll_restoration`.
- `port-abstraction`: adds the `HistoryPort` navigation-classification hook (push vs pop) used by the scroll manager.

## Impact

- **Code**: new `packages/webcompy/src/webcompy/router/_scroll.py` (scroll manager); small hooks in `ports/_history.py` (`HistoryPort.navigate`) and `ports/_browser/_history.py` (`BrowserHistoryPort._on_popstate`); controller wiring where the browser history port is provisioned; `app/_config.py` new field.
- **Specs**: new `openspec/specs/scroll-restoration/spec.md`; deltas to `app-config`, `port-abstraction`.
- **Docs**: routing/basics page in `docs_app` documents the default behavior and opt-out.
- **Tests**: unit tests with a fake window/history (server-side, no browser) for save/restore logic and retry policy; e2e assertion on a long page navigating away and back.
- **Behavior change (intentional)**: browser apps now scroll to top on navigation and restore on Back/Forward. This matches user expectations from multi-page sites and every major SPA framework; apps that built their own scroll handling can opt out via config.

## Known Issues Addressed

- Back/Forward navigation loses the user's reading position (no scroll management exists).
- New-page navigation preserves the previous page's scroll offset (page appears "scrolled halfway down" on arrival).

## Non-goals

- **Fragment/anchor scrolling** (`/docs#section` → scroll to element): the router currently does not preserve URL fragments in `to`/href generation at all; fragment support is a separate routing concern.
- Per-route or per-component scroll behavior customization (Vue's `scrollBehavior(to, from)` callback API): the default policy covers the common case; a callback API can be added later if demanded.
- Scroll restoration for nested scroll containers (only `window` scroll is managed).
- Persisting scroll positions across sessions/reloads.
