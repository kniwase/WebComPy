# Tasks: feat-teleport-ssr-emission

## 1. Spike and groundwork

- [ ] 1.1 Spike: render a scaffold with the planned two-phase flow in a scratch branch and confirm custom loading template marker replacement, payload/loader injection, head/scoped-style injection all compose cleanly after single serialization; record findings in this change's design.md (append "Spike results" note) or adjust ordering
- [ ] 1.2 Add `create_comment` coverage check for FakeBrowserDOMPort/test renderer parity already in place from #267; confirm hydrate-side comment adoption helpers are reusable and note gaps

## 2. Virtual DOM selector engine

- [ ] 2.1 Implement selector tokenizer/parser subset (type/class/id/compound/descendant/child/comma) as pure functions over `VirtualDOMNode` in `webcompy_server`; `ValueError` on unsupported syntax
- [ ] 2.2 Implement read-only depth-first matching returning first match; comments never match
- [ ] 2.3 Unit tests: id/class/type/compound/descendant/child/comma cases, document-order first-match (nested same-class), unsupported syntax raises, no-tree-attached returns None, query does not mutate tree

## 3. Server DOM port document attachment

- [ ] 3.1 Add attach-document-root mechanism to `ServerDOMPort` (context-scoped); `query_selector` resolves via engine once attached, `None` before attachment; `get_element_by_id` stays `None`
- [ ] 3.2 Update port docstrings (`packages/webcompy-server/src`) to describe resolution contract and ValueError behavior
- [ ] 3.3 Unit tests for attached/unattached resolution paths through the port API

## 4. Teleport server-side emission

- [ ] 4.1 Extend `_TeleportTargetRegistry` (per-DI-scope) with ordered pending entries + ordinal counter + consumed-id set shared by both environments; keep existing registration semantics intact
- [ ] 4.2 Add `ssr` key to `TeleportProps` (default True) threading into element state; opted-out teleports register nothing and emit anchor only
- [ ] 4.3 During non-PyScript render, mount anchor as today and enqueue `{ordinal, to, ssr, children}` into registry instead of returning immediately unregistered
- [ ] 4.4 Implement registry drain in `_html.py`: resolve selector → reject app-subtree/head targets by parent-chain walk (warn, skip) → unresolved warn+skip → else render children under target wrapped in start/end marker comments with sequential child indices; run second `await_pending()` after drain before transfer-data collection
- [ ] 4.5 Capture html/body node references during assembly and attach document root to the port before drain; serialize tree once at the end
- [ ] 4.6 Unit tests: emission string contains markers+content under body; opted-out path unchanged; unresolvable/app-subtree/head rejections log warning and stay anchor-only; async child settles before serialization; repeated `<repeat>` inside teleport emits N items; signal values of teleported components appear in hydration payload (ordering vs collect)

## 5. Hydration consumption

- [ ] 5.1 Implement block discovery on client: scan resolved target's children for start markers, selector+ordinal sequence match, exclusive claim via consumed set; warn+fallback to existing self-scheduled render when absent/mismatched
- [ ] 5.2 On claim: record insertion index, remove start/end markers plus enclosed nodes, mark indices updated for following target siblings, then run normal client render inserting at recorded index
- [ ] 5.3 Rework `_re_index_shared_target` to marker/slot-anchored bases (drop tail assumption) covering fresh-mount blocks and recreated blocks uniformly
- [ ] 5.4 Destruction sweep: teleport destroyed during hydration removes its uniquely identifiable unconsumed block; otherwise leaves inert content
- [ ] 5.5 Unit tests (fake HTML parser round-trip): exactly-once consumption single & shared target; stale-HTML fallback keeps one live copy; double-consumption prevented across mixed selectors hitting one target; destruction sweep; inline-fallback regression suite still green

## 6. Docs site updates

- [ ] 6.1 Update `/sample/teleport` demo page copy (SSR section now describes default emission, opt-out, markers)
- [ ] 6.2 Update navbar-related docs text if any page describes anchor-only SSR of dropdowns
- [ ] 6.3 Verify docs_app SSG output contains hidden dropdown link lists under body (manual spot-check or script assertion)

## 7. Spec sync and governance

- [ ] 7.1 Sync deltas into `openspec/specs/teleport/spec.md`, `virtual-dom/spec.md`, `port-abstraction/spec.md`, `elements/spec.md` per openspec-sync workflow when archiving
- [ ] 7.2 Update AGENTS.md Framework Invariants list and `.opencode/skills/webcompy-review/SKILL.md` critical-invariants headings referencing teleport/hydration/elements specs
- [ ] 7.3 Run `python3 scripts/check-doc-spec-refs.py` and fix dangling references (e.g. "anchor-only" phrasing in universal docs)

## 8. E2E and full verification

- [ ] 8.1 Extend `e2e/core/test_teleport.py`: prod and static modes assert `page.content()` (pre-hydration) contains emitted block + markers; post-boot no duplicates; conditional removal cleans content+markers
- [ ] 8.2 Extend docs-home E2E: initial HTML contains navbar dropdown links (crawlability acceptance criterion) alongside the existing pre-hydration height equality test
- [ ] 8.3 Update any unit/E2E assertions broken by default-on output change (search for `\u200b` / anchor-only / marker-count expectations repo-wide)
- [ ] 8.4 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run python -m pytest tests/ --tb=short --cov=webcompy`, and browser test scripts; fix fallout
- [ ] 8.5 Run `scripts/run-e2e-tests.sh` full matrix locally; confirm green
