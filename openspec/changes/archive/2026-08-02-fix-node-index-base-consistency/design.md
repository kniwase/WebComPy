# Design: fix-node-index-base-consistency

## Context

`_node_idx` semantics: offset of an element's first DOM node within its **nearest real-DOM-node ancestor's `childNodes`**. Two container kinds differ:

```
Regular element (owns a DOM node)             Dynamic container (no own DOM node)
  children live in THE ELEMENT'S OWN node      children live in the PARENT'S node
  → base 0                                     → base = container's _node_idx
```

The codebase's index-assignment producers split three ways in practice:

| Producer | Base | Correct for |
|---|---|---|
| `ElementWithChildren._render` (`_base.py:38`) | `self._node_idx` | dynamic ❌ (regular) |
| `DynamicElement._render` (`_dynamic.py:67`), `DynamicElement._hydrate_node` (`:90`) | `self._node_idx` | dynamic ✓ |
| `ElementWithChildren._re_index_children` (`_base.py:99`), `ElementWithChildren._hydrate_node` (`_base.py:48` calls it) | `0` | regular ✓ ❌ (dynamic) |

So `ElementWithChildren._render` and `_re_index_children` disagree for each container kind. `_re_index_children` is called on dynamic parents by:

- `SwitchElement._refresh` (`_switch.py:112`) — `self._parent._re_index_children(False)`. For `RouterView`, `self._switch._parent = self` is set in `RouterView._on_set_parent`, so the parent is the dynamic `RouterView`; re-index resets `switch._node_idx` to 0.
- `MarkdownForElement._refresh` (`_markdown_for.py:524`) — `self._parent._re_index_children(False)`. `MarkdownForElement`'s children's `_parent` skips dynamics (the binder passes `self._parent`), so here the parent is typically regular — but the same path is reached for nested cases.

Reproduction (current code, dynamic parent at index 1 containing a switch): after the initial render `switch._node_idx` is already `0` (corrupted); the first `flag` toggle renders the new branch at index 0 and the preceding `<span>` is permanently lost. `RouterView` placed at non-zero offset exhibits the same on the first navigation. Current e2e passes only because every test/docs layout puts `RouterView` as the sole child of its parent (offset 0), so corruption equals the correct value.

Note: B2's symptom intersects `fix-init-node-sibling-removal` (that change's guard prevents the destructive removal when the guard is in place), but the underlying base corruption remains and must be fixed in its own right: correct `_node_idx` keeps `_mount_node`'s `insertBefore` choosing the right reference even where removal is blocked.

## Goals / Non-Goals

**Goals:**

- `ElementWithChildren._render` assigns regular-element children with base 0 (matching `_re_index_children`/`_hydrate_node`).
- `_re_index_children` does not corrupt a dynamic parent: indices it writes are consistent with the parent's container kind.
- Preserve all existing passing behavior, including router e2e where `RouterView` is at offset 0.

**Non-Goals:**

- Enumerate-vs-cumulative algorithm (`fix-dynamic-child-node-index`).
- `_init_node` removal hazard (`fix-init-node-sibling-removal`).
- Changes to `_get_existing_node`, `_patch_children`, or hydration adoption.

## Decisions

### D1: B1 — `ElementWithChildren._render` uses base 0

Replace the enumerate-based loop's base with a fresh counter from 0, accumulating by `child._node_count`. This composes directly with `fix-dynamic-child-node-index`'s cumulative rewrite at the same site: that change keeps base `self._node_idx`; once both land, the final form is `idx = 0; for child: child._node_idx = idx; idx += child._node_count`. **Sequencing**: if `fix-dynamic-child-node-index` lands first, this change amends the base from `self._node_idx` to `0` at line ~38; if this change lands first, it amends both the base and the offset arithmetic together.

*Alternatives considered*: Keep base `self._node_idx` and accept healed-by-re-index — rejected: the contradiction is the defect, and re-index healing depends on timing (it does not fire for `ElementWithChildren._render` paths that never trigger a dynamic refresh).

### D2: B2 — make `_re_index_children` base-aware by container kind

Auditing `_re_index_children producers`: only `ElementWithChildren._re_index_children` exists (one implementation). Callers — `ElementWithChildren._hydrate_node`, `_insert_child`, `_pop_child`, `RouterView._on_set_parent` — operate on regular parents, where base 0 is correct. The corrupting callers are `SwitchElement._refresh` and `MarkdownForElement._refresh`, whose `self._parent` may be dynamic.

Chosen approach: **make `_re_index_children` start from a base that depends on the receiver's kind** — `0` for `ElementWithChildren` (regular, current behavior) and `self._node_idx` for `DynamicElement`. Implemented by overriding `_re_index_children` on `DynamicElement` to start at `self._node_idx`:

```python
# DynamicElement
def _re_index_children(self, recursive: bool = False):
    idx = self._node_idx
    for c in self._children:
        c._node_idx = idx
        idx += c._node_count
    if recursive:
        for child in self._children:
            if isinstance(child, ElementWithChildren):
                child._re_index_children(True)
```

`ElementWithChildren._re_index_children` stays at base 0 (no change). `RouterView._on_set_parent`'s `self._re_index_children()` then correctly keys `switch._node_idx` off `RouterView._node_idx`; `SwitchElement._refresh`'s `self._parent._re_index_children(False)` keys off the parent's actual offset whether the parent is regular or dynamic. `MarkdownForElement._refresh` likewise.

*Alternatives considered*: (a) Guard the call sites (`if not isinstance(self._parent, DynamicElement): self._parent._re_index_children(False)`) — rejected: dynamic parents still need their children re-indexed after a refresh; the correct index base is what's wrong, not the call itself. (b) Stop re-indexing dynamic parents entirely — rejected: the dynamic parent's siblings rely on the post-refresh re-index for their own correctness.

### D3: Regression coverage for non-zero-offset containers

Tests via TestRenderer and direct element construction (mirroring `tests/test_keyed_repeat.py`'s `fake_browser_full` pattern):

- An element at index ≥ 1 containing a dynamic child followed by static siblings; after a signal-driven refresh the static siblings remain in correct order.
- A `RouterView`-analog (switch inside a dynamic element at non-zero offset) toggled multiple times preserves the preceding sibling.

Each is verified RED before the fix. RED depends on `fix-init-node-sibling-removal` **not** having landed first (once the removal guard is in, the symptom shifts to *misplacement* rather than *loss*). Tests assert DOM **order**, which is wrong in both cases pre-fix and correct post-fix, so they pin this change regardless of ordering.

## Risks / Trade-offs

- [Interaction with `fix-dynamic-child-node-index` at `_base.py:38`] → Both edits touch the same loop. Sequencing note (D1) keeps them composable; whichever lands second applies a small targeted amendment.
- [Router e2e regression] → All existing router/layouts put `RouterView` at offset 0 where base 0 == `self._node_idx`; the `DynamicElement._re_index_children` override yields identical values there. Full router + docs e2e groups validate.
- [Other `DynamicElement` subclasses relying on base-0 re-index] → `FragmentElement`, `RepeatElement`, `SuspenseElement`, `ClientOnlyElement`, `RouterView`, `MarkdownForElement` all inherit `DynamicElement`; the override is correct for all (children live in parent's node at the container offset). Unit + e2e suites cover.
- [`_re_index_children(recursive=True)` into dynamic children] → regular parent's recursive path recurses into dynamic children and now dispatches to the dynamic base — also correct.

## Migration Plan

No migration. Behavior for currently-working cases (offset 0 or healed-by-append) is unchanged; previously-corrupt cases start indexing correctly. Rollback is a plain revert.

## Open Questions

None — base semantics confirmed by `_re_index_children` (regular: 0) and `DynamicElement._hydrate_node` (dynamic: `self._node_idx`), and reproductions validate the failure and the proposed fix path.