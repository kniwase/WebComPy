# Loading Screen

## Purpose

The loading screen capability defines the boot-time waiting experience of a WebComPy application: how the loading element looks and behaves while the PyScript/Pyodide runtime downloads and initializes, how boot progress is communicated, how the pre-rendered page is treated during boot, and how developers customize or fully replace the loading experience.

## Requirements

### Requirement: Presentation modes

The loading screen SHALL support three presentation modes: `overlay` (centered spinner on a translucent backdrop covering the page), `content` (pre-rendered content remains fully visible; a slim top progress bar and a small status label communicate boot progress), and `auto`. The default mode SHALL be `auto`, which SHALL resolve to `content` when the generated page contains pre-rendered application content and to `overlay` otherwise. Mode resolution SHALL happen at HTML generation time.

#### Scenario: Default mode resolves to content for prerendered pages

- **WHEN** a page is generated with pre-rendered content and no explicit loading mode is configured
- **THEN** the loading screen SHALL be generated in `content` mode

#### Scenario: Default mode resolves to overlay without prerendered content

- **WHEN** a page is generated without pre-rendered content and no explicit loading mode is configured
- **THEN** the loading screen SHALL be generated in `overlay` mode

#### Scenario: Explicit mode overrides auto resolution

- **WHEN** the loading configuration sets `mode` to `"overlay"` on a pre-rendered page
- **THEN** the loading screen SHALL be generated in `overlay` mode

### Requirement: Grace period before loading chrome appears

All loading-related visual elements (spinner, progress bar, status label, dormant content treatment) SHALL be suppressed for an initial grace period after page parse. The default grace period SHALL be 350ms and SHALL be configurable via `reveal_delay_ms`. The suppression SHALL be implemented so that if boot completes within the grace period, no loading chrome is ever painted.

#### Scenario: Fast cached boot shows no loading chrome

- **WHEN** the app finishes booting before the grace period elapses
- **THEN** no spinner, progress bar, status label, or dormant treatment SHALL have been displayed

#### Scenario: Slow boot reveals loading chrome after the grace period

- **WHEN** boot is still in progress when the grace period elapses
- **THEN** the loading chrome for the active mode SHALL become visible

### Requirement: Staged progress driven by runtime events

The loading screen SHALL display staged progress derived from PyScript lifecycle events (`py:progress`, `py:ready`). The stage vocabulary SHALL consist of five keys: `runtime_prepare`, `runtime_download`, `packages`, `runtime_ready`, and `app_start`. Each stage SHALL have a default English label, and developers SHALL be able to override labels per stage via `messages` in the loading configuration (enabling full localization). An unknown key in `messages` SHALL be rejected as a configuration error. Progress events with unrecognized detail strings SHALL NOT cause stage transitions; micropip log lines received during package installation MAY be displayed as a secondary sub-status line. Staged progress SHALL be disableable via `stages: false`.

#### Scenario: Stage label follows runtime download

- **WHEN** the runtime emits the event corresponding to interpreter download
- **THEN** the status label SHALL display the label mapped to `runtime_download`

#### Scenario: Localized stage labels

- **WHEN** the loading configuration provides `messages` with custom labels
- **THEN** the status label SHALL display the configured label for each stage instead of the default

#### Scenario: Unknown message key rejected

- **WHEN** the loading configuration provides a `messages` entry whose key is not a known stage key
- **THEN** a configuration error SHALL be raised

#### Scenario: Stages disabled

- **WHEN** the loading configuration sets `stages` to `False`
- **THEN** no status label SHALL be rendered and no stage transitions SHALL occur

### Requirement: Progress bar reflects honest completion

In `content` mode, a progress bar SHALL communicate boot progress. The bar SHALL advance when stages complete and SHALL move smoothly toward the current stage's ceiling while a stage is in flight, without exceeding it. The bar SHALL reach 100% only when the application begins its first render. Bar animation SHALL be driven by compositor-safe properties (transform) so it continues animating during main-thread WASM work. When `stages` is `False`, the bar SHALL NOT use stage ceilings; it SHALL progress purely by smooth trickle, remaining below 100% until completion.

#### Scenario: Bar advances on stage completion

- **WHEN** a boot stage completes
- **THEN** the progress bar SHALL advance to at least that stage's ceiling

#### Scenario: Bar does not claim completion prematurely

- **WHEN** boot is in progress but the first render has not begun
- **THEN** the progress bar SHALL remain below 100%

#### Scenario: Stages disabled leaves the bar as pure trickle

- **WHEN** `stages` is `False` and boot is in progress
- **THEN** the progress bar SHALL progress smoothly without stage jumps
- **AND** it SHALL remain below 100% until completion

### Requirement: Interaction policy during boot

In `content` mode, the loading configuration SHALL support three interaction policies: `block` (default), `inert`, and `passthrough`. With `block`, a transparent full-screen element SHALL intercept pointer clicks while leaving document scrolling and reading unobstructed. With `inert`, the mount element SHALL carry the `inert` attribute during boot, blocking pointer, keyboard focus, and selection. With `passthrough`, no interception SHALL occur. The policy SHALL be lifted when boot completes.

#### Scenario: Default block policy intercepts clicks

- **WHEN** a user clicks a link in the pre-rendered content during boot with the default configuration
- **THEN** the click SHALL NOT reach the application content
- **AND** scrolling and reading SHALL remain possible

#### Scenario: Passthrough policy leaves content interactive

- **WHEN** `interaction` is `"passthrough"` and a user clicks an anchor link during boot
- **THEN** the browser SHALL perform its native navigation

#### Scenario: Policy lifted on boot completion

- **WHEN** boot completes
- **THEN** any interception element or `inert` attribute SHALL be removed and full interactivity SHALL be restored

### Requirement: Dormant content treatment and wake-up transition

In `content` mode, the pre-rendered application content SHALL be rendered in a visually muted ("dormant") state during boot — subtly reduced opacity and/or saturation, tunable via a CSS custom property. When boot completes, the content SHALL transition to full vibrancy over a short animation (the "wake-up"). The dormant treatment SHALL respect the grace period (it SHALL NOT be applied if boot completes within the grace period) and SHALL leave no persistent styling side effects on application content after removal. The dormant treatment SHALL be disableable via the `dormant` configuration key (default `True`); when disabled, the content SHALL remain at full vibrancy during boot.

#### Scenario: Content is muted during a slow boot

- **WHEN** boot is in progress beyond the grace period in `content` mode
- **THEN** the application content SHALL appear visually muted compared to its final state

#### Scenario: Wake-up transition on completion

- **WHEN** boot completes
- **THEN** the content SHALL animate to full vibrancy rather than snapping instantly
- **AND** the wake-up transition SHALL complete even when `fade_out_ms` is shorter than the transition duration

#### Scenario: No dormant flash on fast boot

- **WHEN** boot completes within the grace period
- **THEN** the dormant treatment SHALL never have been visually applied

#### Scenario: Dormant treatment with a custom mount selector

- **WHEN** the application mounts at a custom selector (e.g., `AppConfig(selector="#my-widget")`) in `content` mode and boot is in progress beyond the grace period
- **THEN** the application content SHALL appear visually muted compared to its final state
- **AND** on boot completion the content SHALL transition to full vibrancy

#### Scenario: Dormant treatment disabled

- **WHEN** the loading configuration sets `dormant` to `False`
- **THEN** the application content SHALL remain at full vibrancy during boot
- **AND** no wake-up transition SHALL occur

### Requirement: Removal transition

When the application finishes its first render, the loading element SHALL fade out over a configurable duration (`fade_out_ms`, default 250ms) before being removed from the DOM, instead of being removed instantaneously. The mount element SHALL carry `aria-busy="true"` during boot, which SHALL be removed as part of the removal sequence.

#### Scenario: Fade-out before removal

- **WHEN** the first render completes
- **THEN** the loading element SHALL transition to full transparency over the configured fade duration
- **AND** the element SHALL be removed from the DOM after the transition

#### Scenario: aria-busy lifecycle

- **WHEN** a page with pre-rendered application content is booting
- **THEN** the mount element SHALL have `aria-busy="true"`
- **AND** after the first render completes, the attribute SHALL be removed

### Requirement: Stall watchdog

The loading screen SHALL include a stall watchdog: if no boot progress event is observed for `timeout_seconds` (default 30; `0` disables), a "taking longer than usual" message SHALL be shown together with a reload affordance. The watchdog timer SHALL reset on every progress event. After boot completes, the watchdog SHALL NOT fire.

#### Scenario: Stall message after prolonged silence

- **WHEN** no progress event has been observed for the configured timeout during boot
- **THEN** a message indicating prolonged loading SHALL be displayed along with a way to reload the page

#### Scenario: Watchdog reset by progress

- **WHEN** progress events keep arriving
- **THEN** the stall message SHALL NOT appear

### Requirement: Theme-aware appearance

The default loading screen styles SHALL adapt to the application's theme: colors SHALL follow the `data-theme` attribute on the root `<html>` element when present and fall back to the user's `prefers-color-scheme` otherwise. All loading screen colors SHALL be overridable via documented CSS custom properties.

#### Scenario: Dark theme applied

- **WHEN** the page is rendered with `data-theme="dark"`
- **THEN** the loading screen SHALL use its dark color variant

### Requirement: Accessibility of the loading screen

The loading element SHALL carry `role="status"`. The stage label SHALL be announced politely to assistive technology (`aria-live="polite"`); the sub-status line SHALL NOT be announced. Under `prefers-reduced-motion: reduce`, all loading animations (rotation, trickle, fade, dormant transitions) SHALL be disabled while state information remains available. The grace period SHALL still apply under reduced motion.

#### Scenario: Screen reader hears stage transitions

- **WHEN** a stage transition occurs
- **THEN** the new stage label SHALL be exposed via the polite live region

#### Scenario: Reduced motion

- **WHEN** the user prefers reduced motion
- **THEN** no rotation, fade, or transition animations SHALL play, but the current stage SHALL still be conveyed

### Requirement: Custom loading templates and toolkit contract

Developers SHALL be able to replace the loading screen markup via `template` in the loading configuration, accepting a preset name, an HTML string, or a path to an HTML file resolved relative to the app package. The framework SHALL provide at least three presets: `overlay`, `bar`, and `splash`. A custom template MUST contain exactly one element with `id="webcompy-loading"`; HTML generation SHALL fail with a clear error otherwise. The framework's progress plumbing SHALL drive optional documented hooks when present in the template: `[data-wc-status]` (stage label), `[data-wc-substatus]` (package install lines), `[data-wc-bar]` (receives a `--wc-progress` custom property from 0 to 100), `[data-wc-timeout]` (revealed by the stall watchdog), and `[data-wc-reload]` (click reloads the page). Templates without any hooks SHALL still fade and remove correctly. Templates MAY set `data-wc-*` mechanic attributes (such as fade duration) to override behavior.

#### Scenario: Custom template replaces markup

- **WHEN** a developer configures a custom template containing `id="webcompy-loading"` and a `[data-wc-status]` element
- **THEN** the generated page SHALL contain the custom markup
- **AND** stage labels SHALL appear in the `[data-wc-status]` element during boot

#### Scenario: Template missing the required ID fails the build

- **WHEN** a custom template does not contain `id="webcompy-loading"`
- **THEN** HTML generation SHALL fail with an error identifying the missing contract element

#### Scenario: Preset template by name

- **WHEN** `template` is set to `"splash"`
- **THEN** the generated page SHALL use the framework-provided splash preset markup