# Design: feat-docs-guides-tutorial

## Context

Docs categories: Getting Started (toolchain + orientation), Basic Usage (per-feature), Advanced Usage (deep). The middle layer — a linear tutorial producing a working app — does not exist. iframe demos (`docs_app/static/_demos/<app>/app.py` + `standard.html?app=<name>`) run isolated PyScript apps on both dev and static hosting; `FetchMiddleware` (#283) can intercept `/api/*` inside an app so mocked network features work without any server.

## Goals / Non-Goals

**Goals:** one app grown across six steps; each step page independently runnable and self-contained (demo + full source); teach exactly the Basic subset (no Advanced concepts smuggled in).

**Non-Goals:** real server, authentication, routing guards, multiple apps.

## Decisions

### 1. Subject: a ToDo app

Chosen over chat (needs realtime = Advanced) and notes (same as todo with less UI variety). Reuses reader familiarity; covers state, components, routing, forms, fetching, deploy with zero filler. The existing `/sample/todo` demo is the visual target; the tutorial app is built fresh so its stepwise code is clean.

### 2. Step curriculum (feature gates)

| Step | App gains | Concepts (Basic-only) |
|---|---|---|
| 0 overview | — | roadmap of steps, what you'll end up with |
| 1 shell + reactive state | static seed tasks, count/filter (`use_state`, `use_computed`, `ReactiveList`) | reactivity, rendering lists with `repeat` |
| 2 components | `todo-item`, `todo-toolbar` extraction | props, slots, `@define_component()` derived form |
| 3 navigation | `/active` and `/done` pages | `Router`, flat routes, `RouterLink` active class, `RouterView` in shell |
| 4 forms | add-task form, per-item complete toggle | `use_field`/`use_form`, validators, `Input`/`Checkbox`/`FormField`, `:bind` |
| 5 remote data | persistence to `/api/tasks` | `use_async_result`, `HttpClient`, loading state UI; **`FetchMiddleware` mock** in the demo app |
| 6 deploy | `webcompy generate`, dist output | static vs dev serving, hydration basics mention, next steps |

Ordering rationale: step 3 before 4 so navigation demos the router while forms (the largest step) is the last feature addition before deploy.

### 3. Step apps are real standalone WebComPy apps per step

`docs_app/static/_demos/todo_tutorial/step1/...step6/app.py` — six self-contained files (no cross-imports; PyScript iframe can't share modules). Duplication across steps is intentional: each page shows the complete app at that step. A small `scripts/` guard isn't warranted; review checks step N+1 = step N + declared additions.

- Step 5's mock: a `FetchMiddleware` registered in the demo's `AppConfig` (via a tiny plugin or `provide` in setup) answering `GET/POST /api/tasks` from memory — identical behavior on dev and static; also serves as the middleware teaching moment with a one-paragraph pointer to Advanced middleware docs.
- `standard.html` package map gains `todo_tutorial_stepN: []` entries (webcompy wheel only).

### 4. Page shape

```
frontmatter: title "Step N — <name>", description
lead: what the step adds; time estimate
demo iframe (DemoDisplay pattern) of the step app
narrative sections mirroring the code (H2s = TOC)
full source CodeBlock at the end (single tab, ~<120 lines per step kept)
"Next step" / "Previous step" links (relies on Prev/Next too)
```

Markdown body can embed `render_template`-resolved component tags? Not needed: pages use the standard `docs_page_template`, and the demo iframe is inserted by the wrapper component around the rendered markdown via a slot — the page component composes `DemoDisplay(...)` above `doc.content`. No new rendering machinery.

### 5. Manifest placement

`DOCS_SECTIONS`: insert `Guides` between `Getting Started` and `Basic Usage` — this is the moment the previously-omitted empty category gets its section (compliant with ③-0's "no empty sections").

## Risks / Trade-offs

- [Step code duplication across 6 apps] → accepted for pedagogy; a shared "final app" drift check test compares step 6 to a golden file.
- [Tutorial pages grow stale faster than reference pages] → tie E2E (demo loads, mocked fetch returns) to the CI docs group so breakage surfaces.
- [Iframe apps can't import docs_app code] → duplication above; no helper extraction attempted.

## Migration Plan

Additive. Merge after ③-0 (category model) and ideally after ③-2 (Basic pages) so step pages can link to settled Basic URLs.

## Open Questions

None.
