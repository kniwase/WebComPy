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

- Step 5's mock: a `FetchMiddleware` registered via `add_fetch_middleware(...)` inside root component (`TodoApp`) setup answering `GET`, `POST`, and `PATCH` requests for `/api/tasks` from memory — identical behavior on dev and static; also serves as the middleware teaching moment with a pointer to Advanced middleware topics.
- `standard.html` package map gains `"todo_tutorial/step1": []` … `"todo_tutorial/step6": []` entries (webcompy wheel only), matching `standard.html`'s `/_demos/<app>/app.py` path resolution.

### 4. Page shape

```
frontmatter: title "Step N — <name>", description
lead: what the step adds; time estimate
narrative sections mirroring the code (H2s = TOC)
"Next steps" links (alongside Prev/Next pager)
live demo & full source (DemoDisplay below narrative via extra_content)
```

Markdown body does not need `render_template` component embeds: pages use the standard `docs_page_template`, and the wrapper component passes `DemoDisplay(...)` as `extra_content=` so it renders below the Markdown narrative (`doc.content`) with zero new rendering machinery.

### 5. Manifest placement

`DOCS_SECTIONS`: insert `Guides` between `Getting Started` and `Basic Usage` — this is the moment the previously-omitted empty category gets its section (compliant with ③-0's "no empty sections").

## Risks / Trade-offs

- [Step code duplication across 6 apps] → accepted for pedagogy; per-step unit tests in `tests/test_docs_demos.py` verify each standalone app boots and passes its feature checks.
- [Tutorial pages grow stale faster than reference pages] → tie E2E (demo loads, mocked fetch returns) to the CI docs group so breakage surfaces.
- [Iframe apps can't import docs_app code] → duplication above; no helper extraction attempted.

## Migration Plan

Additive. Merge after ③-0 (category model) and ideally after ③-2 (Basic pages) so step pages can link to settled Basic URLs.

## Open Questions

None.
