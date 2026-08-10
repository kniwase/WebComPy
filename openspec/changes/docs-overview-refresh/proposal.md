## Why

The overview spec is the entry-point document for the framework and will be
the face of the v1 release, but it is stale. Its Purpose section states that
WebComPy "does not yet provide" dependency injection, plugin systems, or
fine-grained DOM patching — all three have since been implemented and are
governed by their own specs (`di-injection`, `plugin-system`,
`list-reconciliation`). The Known Issues block in `openspec/config.yaml` is
similarly out of date: three entries describe limitations that no longer
exist (Router singleton, manual popstate proxy disposal, missing plugin
system) and one overstates the current element system.

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
  - Remove "Location popstate proxy must be manually destroy()ed" — cleanup
    is automatic via `BrowserHistoryPort.__del__`.
  - Remove "No plugin system" — `plugin-system` and `plugin-script` specs
    exist and are implemented.
  - Reword "No virtual DOM diffing — direct DOM manipulation only" to
    reflect that `RepeatElement` supports key-based reconciliation
    (`list-reconciliation`), while SwitchElement still regenerates children.
  - Keep the six entries that are still accurate (element-level signal
    reactivity, `__purge_signal_members__` note, MD5 component IDs, binary
    browser detection, module-level app fallbacks).
- Add a governance requirement to the `overview` capability: the Purpose
  section shall not enumerate missing capabilities, so gap claims cannot
  rot against implemented specs again.

## Known Issues Addressed

This change does not fix any known issue in code. It removes Known Issues
entries that no longer describe reality and corrects one entry, so the
remaining list accurately reflects open work.

## Non-goals

- Fixing any of the remaining known issues (MD5 component IDs, module-level
  app fallbacks, binary browser detection, SwitchElement regeneration,
  element-level signal reactivity). They stay documented as open work.
- Adding new "not yet provided" statements to the overview. New negative
  claims would risk the same staleness; capabilities are described by their
  owning specs.
- Rewriting overview requirements. Only the Purpose prose is affected; all
  requirements remain unchanged.

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
- No code, API, or dependency changes
