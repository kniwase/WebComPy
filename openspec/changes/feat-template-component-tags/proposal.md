## Why

Currently, components must be invoked via Python API (`Card({"title": "Hi"}, slots={...})`) and embedded in templates as variables (`{{ card }}`). This makes component usage look like data interpolation rather than explicit component invocation. Being able to write `<user-card title="Hi">` directly in templates gives developers a declarative, HTML-like way to compose components — matching the experience of Vue, Svelte, and Angular — while keeping the import-based registration explicit in Python.

## What Changes

- Template engine resolves non-HTML tags as component references via `ComponentStore` (DI-based lookup)
- Kebab-case tag names (`<user-card>`) convert to PascalCase (`UserCard`) for ComponentStore lookup
- Static props: `title="Hello"` → `props["title"] = "Hello"`
- Dynamic props: `:count="my_signal"` → `props["count"] = context["my_signal"]` (Signal preserved)
- Prop name kebab→snake_case conversion: `:item-count="x"` → `props["item_count"]`
- Component body content becomes the default slot
- Self-closing syntax (`<user-card />`) supported for slotless components
- Hyphenated unknown tags raise error (likely missing import), non-hyphenated unknown tags treated as HTML (lenient)

## Capabilities

### New Capabilities
_None — extends `template-engine`_

### Modified Capabilities
- `template-engine`: Tag resolution extended to support component lookup via ComponentStore, with static/dynamic prop binding and default slot passthrough

## Known Issues Addressed
_None — this is a new capability layered on Changes 1-3_

## Non-goals
- Named slots (only default slot in MVP)
- Event handlers on component tags (`@click` on `<card>`) — requires special emitter semantics
- Expression evaluation in static props (always literal strings)
- Auto-import of component modules (developer must import explicitly for registration)

## Impact

- **Modified file**: `template/_binder.py` — `bind_element` extended with component tag resolution logic
- **Integration**: ComponentStore accessed via `inject(_COMPONENT_STORE_KEY)` from DI
- **New helper functions**: `kebab_to_pascal`, `kebab_to_snake` for name conversions
- **Existing code leveraged**: ComponentGenerator `__call__`, slot generators, Component lifecycle
- **No breaking changes**: HTML tag handling unchanged, component resolution is a new code path

## Dependencies

- **Depends on**: Change 1 (parser + binder infrastructure including `resolve_attr` with Computed generation for `{{ }}` in component attributes) [required]; Change 2 (FragmentElement for multi-child default slot wrapping) [required]
- **Required by**: Change 6 (markdown — component tags `<user-card>` in Markdown HTML blocks)
- **Recommended implementation order**: Third template-engine change (0 → 1 → 2 → **3** → 4 → 5 → 6 → 7)
