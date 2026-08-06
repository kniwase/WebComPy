# Scroll Restoration

## Purpose

Client-side routing breaks the browser's native scroll handling: Back/Forward loses the user's reading position (the SPA re-renders after the browser's own restoration attempt) and new-page navigations leave the scroll wherever the previous page had it. This capability restores multi-page-site scroll expectations by setting `history.scrollRestoration = "manual"` at startup and managing window scroll itself — new pages scroll to the top, and history traversal restores the position saved when each page was left. The behavior is enabled by default and can be disabled via `WebComPyAppConfig.scroll_restoration = False`.

## Requirements

### Requirement: The framework shall manage window scroll position across client-side navigations by default

In the browser environment, the framework SHALL set `history.scrollRestoration = "manual"` at startup and manage window scroll position itself. On a push navigation (new history entry: `RouterLink` activation or programmatic path change), the framework SHALL scroll the window to the top after the navigation renders. On a pop navigation (history traversal: Back/Forward), the framework SHALL save the outgoing page's scroll position at every navigation and, after the destination renders, restore the destination's previously saved position when one exists, scrolling to top otherwise.

The behavior SHALL be enabled by default and SHALL be disabled entirely (including the `scrollRestoration` mutation) via `WebComPyAppConfig.scroll_restoration = False`. Server-side rendering and static generation SHALL perform no scroll operations.

#### Scenario: New navigation scrolls to top
- **GIVEN** the user has scrolled down on page `/a`
- **WHEN** the user clicks a `RouterLink` to `/b`
- **THEN** after `/b` renders, the window scroll position SHALL be `(0, 0)`

#### Scenario: Back restores saved position
- **GIVEN** the user scrolled to position `(0, 1200)` on `/a`, then navigated to `/b`
- **WHEN** the user presses the browser Back button
- **THEN** after `/a` re-renders, the window scroll position SHALL be restored to `(0, 1200)`

#### Scenario: First visit via Back/Forward scrolls to top
- **WHEN** a pop navigation arrives at a path with no saved position
- **THEN** the window SHALL scroll to the top

#### Scenario: Outgoing position saved on every navigation
- **GIVEN** the user navigated `/a` → `/b` → Back to `/a` → `/c`
- **WHEN** the user later returns to `/a` via history traversal
- **THEN** the position saved at the most recent departure from `/a` SHALL be restored

#### Scenario: Opt-out disables all behavior
- **GIVEN** `WebComPyAppConfig(scroll_restoration=False)`
- **THEN** the framework SHALL NOT set `history.scrollRestoration`
- **AND** SHALL NOT save or restore any scroll position

#### Scenario: SSR performs no scroll operations
- **WHEN** a page is server-rendered or statically generated
- **THEN** no scroll API SHALL be accessed and no scroll manager SHALL be created

### Requirement: Scroll restoration shall run after rendering with bounded retry for async content

Scroll actions SHALL be scheduled asynchronously (via `HostPort.schedule_macro_task`) so they execute after the navigation's render pass. When the saved vertical offset exceeds the currently scrollable range (content still loading, e.g. `Suspense` fallback or lazy route), restoration SHALL retry on subsequent macro tasks up to a bounded number of attempts (3), after which the position SHALL be clamped to the maximum scrollable offset.

#### Scenario: Restore waits for async content
- **GIVEN** a saved position `(0, 2000)` for `/a`, where `/a` renders async content that initially produces a document only 800px tall
- **WHEN** the user navigates Back to `/a`
- **THEN** restoration SHALL retry while the document is too short
- **AND** once the document reaches sufficient height, the position `(0, 2000)` SHALL be applied

#### Scenario: Bounded retry gives up gracefully
- **GIVEN** a saved position `(0, 2000)` whose target page never grows beyond 800px
- **WHEN** restoration is attempted
- **THEN** after 3 attempts the scroll position SHALL be clamped to the maximum scrollable offset
- **AND** no error SHALL be raised
