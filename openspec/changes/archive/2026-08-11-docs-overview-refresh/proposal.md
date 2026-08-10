## Why

The overview spec is the entry-point document for the framework and will be
the face of the v1 release, but it is stale. Its Purpose section states that
WebComPy "does not yet provide" dependency injection, plugin systems, or
fine-grained DOM patching — all three have since been implemented and are
governed by their own specs (`di-injection`, `plugin-system`,
`list-reconciliation`). The Known Issues block in `openspec/config.yaml` is
similarly out of date: two entries describe limitations that no longer
exist (Router singleton, missing plugin system), one overstates the
current element system, and the popstate entry attributes cleanup to a
manual `destroy()` call that no longer matches the code.

## What Changes

- Remove the stale "What WebComPy does not yet provide" paragraph from the
  Purpose section of `openspec/specs/overview/spec.md`. No replacement
  "missing capabilities" statement is added; capability descriptions live in
  the owning specs (single source of truth).
- Clean up the Known Issues block in `openspec/config.yaml`, verified
  against the current code:
  - Remove "RouterView singleton removed ... Router singleton remains" —
    the Router is created per app (`Router._clone_for_request`) and provided
    via DI (`_ROUTER_KEY` in the root component scope).
  - Reword "Location popstate proxy must be manually destroy()ed" — cleanup
    relies on `BrowserHistoryPort.__del__`, which may never run because the
    browser event target can retain the proxy and its callback; the entry
    stays until an explicit port/context disposal path removes the listener
    and destroys the proxy.
  - Remove "No plugin system" — `plugin-system` and `plugin-script` specs
    exist and are implemented.
  - Reword "No virtual DOM diffing — direct DOM manipulation only" to
    reflect that `RepeatElement` supports key-based reconciliation
    (`list-reconciliation`), and correct the SwitchElement entry: it
    replaces children only when branch structures differ, reusing DOM nodes
    via patching for matching structures.
  - Keep the five entries that are still accurate as-is (element-level
    signal reactivity, `__purge_signal_members__` note, MD5 component IDs,
    binary browser detection, module-level app fallbacks). Together with
    the three reworded entries (two element-system and the popstate
    cleanup), the final list contains eight entries.
- Add a governance requirement to the `overview` capability: the Purpose
  section shall not enumerate missing capabilities, so gap claims cannot
  rot against implemented specs again.
- Synchronize the new invariant into the review-knowledge references
  (Framework Invariants in `AGENTS.md` and Critical Framework Invariants in
  `.opencode/skills/webcompy-review/SKILL.md`) per the Review Knowledge
  Maintenance rules.

## Known Issues Addressed

This change does not fix any known issue in code. It removes Known Issues
entries that no longer describe reality and corrects other entries, so the
remaining list accurately reflects open work.

## Non-goals

- Fixing any of the remaining known issues (MD5 component IDs, module-level
  app fallbacks, binary browser detection, SwitchElement branch replacement,
  element-level signal reactivity). They stay documented as open work.
- Adding new "not yet provided" statements to the overview. New negative
  claims would risk the same staleness; capabilities are described by their
  owning specs.
- Rewriting overview requirements. The only requirement-level change is the
  added governance requirement (the Purpose shall not enumerate missing
  capabilities); all other requirements remain unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `overview` — adds one governance requirement: the overview Purpose
  section shall not enumerate missing capabilities (prevents this class of
  staleness from recurring). The stale Purpose prose itself is not a
  requirement and is removed by a direct edit (see design.md).

## Impact

- `openspec/specs/overview/spec.md` — Purpose section prose edited
  directly; one requirement added via delta
- `openspec/config.yaml` — `context` block Known Issues list only
- `AGENTS.md`, `.opencode/skills/webcompy-review/SKILL.md` — new invariant
  heading referencing `overview/spec.md` (review-knowledge sync)
- No code, API, or dependency changes
