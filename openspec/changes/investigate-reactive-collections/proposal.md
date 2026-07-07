## Why

`ReactiveList` and `ReactiveDict` are collection types that fuse reactive notification with Python's `list` and `dict` interfaces. Unlike Vue's `reactive()` (which uses Proxy for transparent method interception) or Angular's signals (which require explicit mutation calls), these types require manual method wrapping (`append`, `remove`, `__setitem__`, etc.) because Python lacks Proxy. This makes them costly to maintain and conceptually "floating" — they don't fit cleanly into the `signal()` / `computed()` reactive vocabulary established by Phase 2.

Before deciding whether to deprecate, replace, or retain them, a structured investigation is needed to evaluate whether `Signal[list]` / `Signal[dict]` (with whole-value replacement) is a viable alternative for real-world usage patterns.

## What Changes

- Audit all usages of `ReactiveList` and `ReactiveDict` across the framework, docs_app, and test code
- Evaluate the developer experience trade-off between method-level reactivity (`items.append(x)`) and whole-value replacement (`items.value = [*items.value, x]`)
- Document migration patterns if deprecation is recommended
- Produce a decision document (in `design.md`) with one of three outcomes: **Deprecate**, **Retain**, or **Partial Deprecate** (retain with simplified API)
- No production code changes in this change — investigation only

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none — this is an investigation; implementation changes, if any, will be a separate change)

## Impact

- Investigation covers: `packages/webcompy/src/webcompy/signal/_collection.py` (or wherever ReactiveList/Dict are defined), all import sites, docs_app usage, and test coverage
- Outcome determines the scope of a future `refactor-reactive-collections` implementation change
- No runtime impact from this change itself

## Known Issues Addressed

- "No element-level reactivity in ReactiveList/ReactiveDict — any mutation triggers full change notification" — this investigation evaluates whether this limitation justifies deprecation

## Non-goals

- Implementing the deprecation or replacement (separate change based on this investigation's outcome)
- Changing `Signal`, `signal()`, or `computed()` APIs
- Reducing test coverage of ReactiveList/ReactiveDict during the investigation
