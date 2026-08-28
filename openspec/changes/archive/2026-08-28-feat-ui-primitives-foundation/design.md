# Design: feat-ui-primitives-foundation

## Context

`webcompy.ui` already provides the skeleton of a toolkit: `theme/` (DI-managed `ThemeManager`, `use_theme()`, cookie persistence, SSR-safe), `code_block/` (themed component with pluggable lexer protocol — the precedent for "component + shipped CSS"), and `_styles/` served automatically at `/_webcompy-ui/` with a declared cascade: `@layer reset, tokens, components, webcompy-scope;` importing `tokens.css` (full light/dark design tokens), `reset.css`, `components.css`, `code-block.css`, `syntax-theme.css`. What is missing is a general-purpose component layer; reusable pieces currently live ad hoc in docs_app (`docs_app/components/ui.py` Button/Card/Section/Link with scoped styles).

Grounded facts (verified in codebase):

- Function-style component pattern: `@define_component` over `def Name(context: ComponentContext[Props])` with `TypedDict(total=False)` props (`docs_app/components/ui.py:65-105`); this is the composables-era convention the primitives follow.
- Stylesheet delivery: `_styles/index.css` declares the layer order and imports; the framework injects `/_webcompy-ui/index.css` into the document head during SSR (`webcompy_server/_html.py:336-339`).
- Design tokens are comprehensive (`tokens.css`: colors incl. semantic states, spacing scale, font sizes/families, radii, shadows) and theme-switchable.
- `components.css` currently holds minimal shared styles (~54 lines) — room for a dedicated primitives stylesheet.

## Goals / Non-Goals

**Goals:**

- Define and implement the two-layer architecture: `webcompy.ui.headless` (behavior core) and `webcompy.ui.components` (themed skin), with themed re-exports at `webcompy.ui`.
- Specify the headless contract precisely (a11y + state via `data-state`, structural-only CSS, class pass-through) so the overlay/disclosure/form changes build uniformly.
- Ship the first component pair (`Spinner`) proving the contract end-to-end, including stylesheet delivery.

**Non-Goals:**

- The remaining component families (separate changes).
- Layout-level components, design-system opinions, i18n label integration (see proposal Non-goals).

## Decisions

### D1: Two layers — headless core plus themed skin

Two user profiles exist: "just make it work" and "I want full design control". A single styled library serves only the first; a headless-only library serves only the second. The architecture therefore ships both layers: headless components own all behavior (state, ARIA, keyboard, focus), themed components are thin compositions adding token-based visuals. Precedent: Radix/shadcn in the JS ecosystem proves the split; `CodeBlock` proves WebComPy can ship component + CSS together. Alternative (themed-only with class overrides) rejected: overrides cannot remove embedded visual opinions cleanly, and design-heavy users would fight the defaults. Alternative (headless-only) rejected: it abandons the zero-effort profile despite tokens/theme infrastructure already existing.

### D2: Headless contract — behavior only, state via data-state

Headless components SHALL provide logic, ARIA roles/attributes, keyboard interaction, and focus management, and SHALL NOT emit visual styles (colors, spacing, typography, borders, shadows). Structural CSS is permitted where behavior requires it (e.g. positioning for overlays, `display` toggling). Component state SHALL be exposed on the DOM through `data-state` attributes (e.g. `data-state="open" | "closed"`, `data-state="loading"`), following the Radix pattern, so user CSS can style state without framework coupling. Rationale: attribute-driven state keeps the styling surface declarative and works with scoped CSS, plain CSS, and third-party CSS alike.

### D3: Styling hooks — class pass-through per part

Every headless component accepts a `class` prop applied to its root element and, for multi-part components, part-specific props (`class_panel`, `class_overlay`, etc., named per component). User classes are appended after framework classes so user rules win at equal specificity. This is the sole styling extension point in the headless layer; combined with `data-state`, it covers both simple and stateful styling needs.

### D4: Themed layer as composition over headless

A themed component renders the corresponding headless component, supplying default class names whose rules live in the shipped primitives stylesheet and consume design tokens (`var(--color-*)`, `var(--space-*)`, ...). Themed components pass user `class`/part-class props through, so overrides work identically at both layers. Rationale: composition (not inheritance or duplication) keeps a single behavioral implementation per component; the themed layer carries zero logic.

### D5: Stylesheet delivery via the existing cascade

Themed primitive styles ship in a new `_styles/primitives.css`, imported by `index.css` inside the existing `@layer components` ordering. Because layered rules lose to unlayered user CSS, user stylesheets naturally override themed defaults without specificity wars; `@layer webcompy-scope` remains reserved for scoped component styles. No new delivery mechanism is needed — the framework already injects `/_webcompy-ui/index.css`.

### D6: Namespaces and exports

- `webcompy.ui.headless` — headless components (`from webcompy.ui.headless import Spinner`).
- `webcompy.ui.components` — themed components (`from webcompy.ui.components import Spinner`).
- `webcompy.ui` top level re-exports the themed components as the default convenient path (`from webcompy.ui import Spinner`).
Naming collisions between layers are resolved by module path; the top level always means themed.

### D7: Spinner as the proving component

`Spinner` is the simplest meaningful pair: headless emits `role="status"` with an accessible label (prop-driven, visually hidden text or `aria-label`) and `data-state="loading"`; themed adds a token-based animated indicator (border/spin using `--color-*` tokens, honoring `prefers-reduced-motion` by pausing animation). It exercises the contract (a11y, data-state, class pass-through, themed CSS delivery) without depending on Teleport or Transition, keeping this change independent. Later families bring those dependencies.

### D8: Function-style authoring

All primitives use the established function-style pattern (`@define_component`, `ComponentContext[Props]`, `TypedDict(total=False)` props), consistent with the composables-era convention. Props naming follows existing conventions (snake_case, `aria_*` mapped to `aria-*` attributes).

## Risks / Trade-offs

- **API surface duplication**: two import paths per component. Accepted — the profiles are genuinely different; docs make the default path (themed, top-level) prominent.
- **Headless/themed drift**: a behavior fix must land in the headless component only; themed components carry no logic by contract (D4), enforced in review.
- **Layer cascade surprises**: user CSS outside layers overrides themed rules (intended); user CSS inside `@layer components` at equal specificity follows source order. Documented in the primitives guide.
- **data-state vocabulary**: each component defines its own state values; the foundation spec fixes the mechanism, per-component specs fix vocabularies, keeping consistency reviewable.
