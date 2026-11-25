# Design: feat-docs-examples

## Context

Demo infrastructure: isolated PyScript iframes (`static/_demos/standard.html?app=<name>`, per-app package allow-list) surfaced by `DemoDisplay` (iframe + fetched source CodeBlock). Nine `/sample/*` pages exist (incl. #250 teleport, #252 transition, #292-era form controls, #291 i18n). Middleware (#283) enables fully client-side mocks. FizzBuzz overlaps ToDo coverage.

## Goals / Non-Goals

**Goals:** one consistent Examples page shape; networked demos work identically on dev + static; every showcase maps to a Basic/Advanced page it illustrates (front- and back-links).

**Non-Goals:** real server endpoints; tutorial narrative.

## Decisions

### 1. Examples page composition = Markdown + composed DemoDisplay

Page wrapper (thin async component) renders `docs_page_template(doc)` and inserts a `DemoDisplay`-equivalent live section between lead and narrative: `examples_page_template(doc, demo=<app_name>)`. Narrative lives in the `.md` (editable without touching components); demo slot position fixed (after lead) so the page keeps the "explanation + code + live app" trio. **Rejected**: full Python page composition per example (loses the Markdown authoring benefit).

### 2. `/sample/*` removal is total

Routes, pages, Navbar "Demos" dropdown, and the demo test files migrate to the Examples category. Old URLs 404 (no redirects, per ③-0 policy). The shared `static/_demos/<app>/` apps that survive keep their paths (iframe internals are not public URLs).

### 3. Mock strategy for networked examples

| Example | Mock mechanism | Notes |
|---|---|---|
| http-fetch | static JSON files (current) | existing `sample_object.json` pattern |
| fetch-middleware | `FetchMiddleware` in the demo app answering `/api/*` | teaches the mechanism AND uses it |
| rpc-middleware | `RpcMiddleware` returning `next(ctx, response=...)` typed syntheses for `Procedure` contracts; page includes the real server-side `app.rpc.bind` snippet as reference | typed decoding path exercised in-browser |
| storage-sync | `use_local_storage(sync_tabs=True)` + second iframe button "open demo in new tab" | cross-tab proof across two iframe instances on same origin |
| routing | in-app nested demo incl. guard redirect | no server needed |

### 4. FizzBuzz retirement

Delete `static/_demos/fizzbuzz/` and its pages/tests; the ToDo example absorbs its list-mutation beat (add/remove with counts in the narrative).

### 5. Ordering within Examples

Pedagogical: hello-world → todo → form-controls (labeled "Forms") → routing → storage-sync → transition → teleport → i18n-playground → matplotlib → http-fetch → fetch-middleware → rpc-middleware (simple state → navigation → styling/motion → i18n → heavy deps → networking → mocks).

## Risks / Trade-offs

- [Two-iframe storage demo could confuse on mobile] → narrative explains; E2E desktop-only for the cross-tab step.
- [In-app mocks hide the real transport] → each mock example's page carries an explicit "this is a client-side mock; here is the real server wiring" section with links to ③-4/③-6 pages.
- [12 example pages is the largest single-change content load] → tasks grouped 3-4 pages each; reviewable incrementally.

## Migration Plan

Merge after ③-0 (category model), ③-2 (targets to link), ③-4 (rpc page for the reference links), ③-7 (i18n). `/sample` cleanup lands with the Examples entries to avoid a docs dead zone mid-merge.

## Open Questions

None.
