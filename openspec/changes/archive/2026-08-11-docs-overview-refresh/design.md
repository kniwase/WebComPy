## Context

OpenSpec deltas operate at the requirement level
(ADDED/MODIFIED/REMOVED/RENAMED requirement blocks with scenarios). The
staleness addressed here lives in two places that are outside that
mechanism: the Purpose prose of `openspec/specs/overview/spec.md` and the
`context` block of `openspec/config.yaml`. No archived change has ever
modified an existing spec's Purpose prose via a delta.

## Goals / Non-Goals

Goals:

- Make the overview Purpose section accurate for the v1 release.
- Make the Known Issues list in `config.yaml` match the current code, with
  every kept entry verified against a concrete code location.

Non-goals:

- Any requirement-level change to the overview spec beyond the single
  governance requirement introduced in D1.
- Code fixes for the remaining known issues.

## Decisions

### D1: Direct prose edits plus one governance delta

OpenSpec validation requires at least one delta per change, and the stale
content itself is prose, not requirements. The change therefore combines
two mechanisms:

- The Purpose paragraph removal and the `config.yaml` cleanup are applied
  as direct edits (implementation tasks).
- A single ADDED requirement is introduced in the `overview` capability:
  the Purpose section shall not enumerate missing capabilities. This is not
  an invented formality — it codifies D2 as a durable rule and prevents
  this staleness class from recurring. Precedent: the `fix-typos` change
  created the `internal-naming` governance spec from a cleanup change.

Alternative considered: force the correction into a MODIFIED requirement
(e.g. restate that the framework provides DI/plugins/reconciliation).
Rejected — it would transcribe content owned by `di-injection`,
`plugin-system`, and `list-reconciliation`, violating the spec
single-source-of-truth rule, and the stale paragraph itself is not inside
any requirement.

### D2: Delete the stale paragraph without replacement

The "What WebComPy does not yet provide" paragraph is removed entirely
rather than rewritten with an updated gap list.

Alternative considered: replace it with current gaps (e.g. realtime
communication). Rejected — negative claims rot the same way; the realtime
roadmap is already expressed through its own change proposals, and
capability descriptions belong in the owning specs.

### D3: Verify-then-edit for Known Issues

Each `config.yaml` entry was checked against the code before classifying it
as remove/reword/keep:

- Router per-app: `Router._clone_for_request` (`router/_router.py`), DI
  provision of `_ROUTER_KEY` (`app/_root_component.py`).
- Popstate cleanup: cleanup relies on `BrowserHistoryPort.__del__`
  (`ports/_browser/_history.py`), which may never run because the browser
  event target can retain the proxy and its callback; the entry is kept
  until an explicit port/context disposal path exists.
- Plugin system: `plugin-system` / `plugin-script` specs implemented.
- Reconciliation: `list-reconciliation` spec; SwitchElement reuses DOM
  nodes via patching for matching structures and replaces children only
  when branch structures differ.
- Kept entries re-checked: `_last_mutation` (`signal/_dict.py`),
  `__purge_signal_members__` (`signal/_container.py`), MD5 component IDs
  (`components/_libs.py`), binary Emscripten detection
  (`utils/_environment.py`), module-level fallbacks (`di/_scope.py`,
  `components/_component.py`).

## Risks / Trade-offs

- [Removing Known Issues entries loses historical context] → The entries
  describe states that no longer exist; git history preserves the record.
- [OpenSpec validation requires at least one delta] → Resolved by the
  governance requirement in D1; no invented requirements.
