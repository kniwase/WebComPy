# Design: fix-init-node-sibling-removal

## Context

Every `ElementAbstract` knows `_node_idx`, the index of its first DOM node within its nearest real-DOM-node ancestor's `childNodes`. When an element's node is first requested (`_get_node()` → `_init_node()`), the element looks at the node currently occupying its index via `_get_existing_node()` and decides:

1. If it is a prerendered node (`__webcompy_prerendered_node__`) matching this element → adopt it.
2. Otherwise → `existing_node.remove()`, create a fresh node, and let `_mount_node` insert it.

Branch 2 assumes the occupant is a stale copy of the element itself. That is true during prerender adoption (the SSR DOM is a static snapshot; a tag mismatch means the slot content is obsolete) but false for fresh renders into a live DOM: after a dynamic container refresh removes old children, the node at a new child's index is typically the container's *following static sibling*. Removing it destroys unrelated content permanently.

Concrete sequence (unkeyed `{% for %}` full-rebuild refresh, correct indices throughout):

```
1. Old children removed        DOM: [pA, pB]     ← pB is the repeat's following sibling
2. New li0._render()
3.   _init_node → _get_existing_node(idx=1)
4.     → childNodes[1] = pB (innocent sibling)
5.     → not prerendered → pB.remove()           ← BUG
6.   _mount_node → append
Result: [pA, li0, li1, li2]                      ← pB permanently lost
```

The same hazard fires in keyed reconciliation (`RepeatElement._reconcile_children` renders fresh children at assigned indices), `SwitchElement._refresh` (non-patchable branch replacement), `SuspenseElement` patch paths, and `MarkdownForElement._refresh`.

Notably, `NewLine._init_node` (`_text.py:33`) already has the correct guard:

```python
elif not getattr(existing_node, "__webcompy_node__", False):
    existing_node.remove()
```

`ElementBase._init_node`, `TextElement._init_node`, and `RawHTMLElement._init_node` lack it and remove unconditionally.

Key fact enabling the fix: prerendered SSR nodes never carry `__webcompy_node__` — `_mark_as_prerendered` (`app/_root_component.py`) sets only `__webcompy_prerendered_node__`, and `__webcompy_node__` is set by `_init_new_node`/`_adopt_node` only for webcompy-managed nodes. So gating removal on `not __webcompy_node__` preserves the prerender-mismatch removal path exactly.

## Goals / Non-Goals

**Goals:**

- Fresh node initialization must never remove a webcompy-managed DOM node
- Preserve prerender adoption semantics (mismatched prerendered nodes still removed and recreated)
- Pin behavior with regression tests (repeat/switch/keyed-repeat followed by static siblings)

**Non-Goals:**

- `_node_idx` arithmetic (covered by `fix-dynamic-child-node-index` and `fix-node-index-base-consistency`)
- Reconciliation algorithm changes; hydration flow changes beyond what the guard preserves
- Any public API change

## Decisions

### D1: Adopt NewLine's guard verbatim in the three unguarded `_init_node` implementations

`ElementBase._init_node` (`_element.py:72-85`), `TextElement._init_node` (`_text.py:69-82`), and `RawHTMLElement._init_node` (`_text.py:110-123`) change their `else: existing_node.remove()` branch to:

```python
elif not getattr(existing_node, "__webcompy_node__", False):
    existing_node.remove()
```

For `ElementBase._init_node` the structure is already `if prerendered and tag-match: adopt / else: remove` — the `else` becomes the guarded `elif`. When the guard blocks removal (managed node at the slot), the element falls through to create its own node; `_mount_node` then inserts it at `_node_idx` via `insertBefore`, which is exactly the correct live-DOM insertion behavior.

*Alternatives considered*: (a) Removing the `remove()` entirely — rejected: prerendered tag-mismatch slots (SSR snapshot no longer matching the client tree) must still be discarded, and those nodes lack `__webcompy_node__`, so the guard keeps that path. (b) Making `_get_existing_node` return `None` when the occupant is managed — rejected: `_get_existing_node` is also used by `_hydrate_node`, where encountering a managed node has its own handling; changing the shared lookup conflates two call sites with different needs. (c) Fixing every refresh path to render fresh children before old ones are removed — rejected: treats the symptom at N call sites instead of the single root cause.

### D2: Audit of legitimate stale-managed-node removal instead of a behavior carve-out

`_init_node` runs only on `_node_cache` miss. Managed nodes at the target index arise in two ways: (i) innocent siblings (the bug — must not be removed), (ii) genuinely stale nodes of this same element after `_clear_node_cache`. For (ii), the stale node would now survive, producing a duplicate until the next reconciliation; remount flows (`_mount_node` `_remount_to`/`replaceChild`, `_detach_from_node`) do not route through `_init_node`, and `_remove_element` explicitly `remove()`s nodes. No currently-passing path depends on `_init_node` deleting a managed node; the full unit + e2e suite (prod and static, including hydration groups) is the safety net.

### D3: Regression tests via TestRenderer with trailing siblings

The bug needs no fragments and no index corruption: a plain single-line `{% for %}` with a trailing `<p>` after `{% endfor %}` reproduces it. Tests assert the trailing element's presence and position after signal-driven refresh, following existing `TestRenderer` patterns from `tests/test_template_ssr.py` and `tests/test_tier2_interactive.py`. Each test is verified RED against unfixed code before the guard is applied.

The pop direction and the ClientOnly/Suspense materialization variants are already pinned by `tests/test_dynamic_child_node_index.py` (`TestRepeatRefreshWithFollowingSibling`, `TestDynamicChildMaterialization`), so this change adds the previously uncovered `MarkdownForElement._refresh` path: a `MarkdownForElement` over an empty `ReactiveList` followed by a static sibling `<span>`. Appending the first item renders a fresh `<ul>` at index 0 — where the sibling sits — which destroys the sibling without the guard (verified RED on pre-fix code).

## Risks / Trade-offs

- [A managed node that should legitimately be replaced is now left in the DOM] → No such live path identified in the audit (D2); failure mode is a benign duplicate, not data loss. Full unit + e2e suite validates.
- [Guard relies on `__webcompy_node__` being set on all managed nodes] → `_init_new_node` and `_adopt_node` set it on every creation/adoption path; server `VirtualDOMNode` supports the same attributes (TestRenderer covers this).
- [Interaction with `fix-dynamic-child-node-index` (index changes) and `fix-node-index-base-consistency` (base changes)] → Independent root causes; guard behavior is index-value-agnostic. Whichever lands first, the other's tests add coverage.

## Migration Plan

No migration. Previously-broken cases (siblings destroyed) start behaving correctly; previously-working cases are unchanged because the guard only blocks removals that destroyed live managed content. Rollback is a plain revert.

## Open Questions

None — the fix was validated by reproduction scripts against current code before this design was written (removal chain traced to `_init_node`; guard condition confirmed compatible with prerender adoption).
