# Elements (Virtual DOM)

## Overview

The element system is a Python-side virtual DOM that renders to real DOM nodes when in the browser. There is no virtual DOM diffing algorithm — the approach is direct DOM manipulation with reactive updates.

## Element Hierarchy

```
ElementAbstract (ReactiveReceivable)
  ├── _node_cache, _mounted, _remount_to
  ├── _mount_node() / _detach_node() / _get_node()
  ├── _render() → _mount_node()
  └── _remove_element() → unregister callbacks, remove node

ElementWithChildren(ElementAbstract)
  ├── _tag_name, _attrs, _event_handlers, _children, _parent
  ├── _proc_attr() → process Reactive/bool/int/str attrs
  ├── _get_processed_attrs() → inject component-scoping attributes
  ├── _append_child / _insert_child / _pop_child / _re_index_children
  ├── _render_html() → SSR string generation
  └── _create_child_element() → wraps str/Reactive as TextElement

ElementBase(ElementWithChildren)
  ├── _ref: DomNodeRef, _event_handlers_added
  ├── _init_node() → Create or reuse DOM node
  └── _generate_attr_updater() → callback for reactive attr updates

Element(ElementBase)
  └── Constructor takes tag_name, attrs, events, ref, children

DynamicElement(ElementWithChildren)
  ├── No own DOM node (_init_node raises)
  ├── _node_count = sum of children's node counts
  ├── _on_set_parent() abstract hook
  └── Nested DynamicElement raises WebComPyException

RepeatElement(DynamicElement)
  └── Reactive list rendering with template function

SwitchElement(DynamicElement)
  └── Conditional rendering (like v-if/v-switch)

TextElement(ElementAbstract)
  └── Wraps str or Reactive, updates DOM text content

NewLine(ElementAbstract)
  └── Renders <br>

MultiLineTextElement(RepeatElement)
  └── Splits text on \n, interleaves with NewLine elements
```

## DOM Node Lifecycle

### Browser Environment

- `_init_node()` checks for existing pre-rendered node (`__webcompy_prerendered_node__`):
  - If found with matching tag name, reuses it (hydration)
  - Otherwise, removes existing node and creates new with `browser.document.createElement()`
- Sets `__webcompy_node__ = True` marker on the node
- For reactive attributes, registers `on_after_updating` callbacks via `_generate_attr_updater()`
- Event handlers are proxied via `browser.pyscript.ffi.create_proxy()`

### SSR (Server-Side Rendering)

- `_render_html()` generates HTML strings
- `ElementWithChildren._render_html()` produces `<tag attrs>children</tag>` format
- `DynamicElement._render_html()` concatenates children's HTML
- `AppDocumentRoot._render_html()` sets `hidden=True` on the app div during SSG

## Hydration

- `AppDocumentRoot._init_node()` finds `#webcompy-app` and marks all children as pre-rendered via `__webcompy_prerendered_node__ = True`
- Pre-rendered nodes are reused during `_init_node()` if the tag name matches
- After first render, `#webcompy-loading` element is removed from DOM

## Reactive DOM Updates

- **Attribute updates**: `ElementBase._init_node()` registers `on_after_updating` callbacks on reactive attrs. The callback updates the DOM attribute directly.
- **Text updates**: `TextElement.__init__()` registers `on_after_updating` for reactive text content. The callback updates `node.textContent`.
- **List updates**: `RepeatElement` registers `on_after_updating` on its sequence reactive. On change, all children are removed and regenerated.
- **Switch updates**: `SwitchElement` tracks `_rendered_idx` to avoid unnecessary re-renders. Only regenerates when the active case changes.

## Helper Functions (generators.py)

- **`create_element(tag_name, attrs, *children)`**: Parses attribute dict, separates `@event` handlers and `:ref` DomNodeRefs
- **`event(name)`**: Prefixes with `@` for event attribute key
- **`noderef`**: Special key `":ref"` for DomNodeRef
- **`repeat(sequence, template)`**: Creates `RepeatElement`
- **`switch(*cases, default)`**: Creates `SwitchElement` from case tuples
- **`text(text, enable_multiline)`**: Creates `MultiLineTextElement` or `TextElement`
- **`break_line()`**: Creates `NewLine`

## DomNodeRef

- Proxy object for accessing real DOM nodes
- `element` property raises `WebComPyException` if not initialized
- `__getattr__` / `__setattr__` delegate to the underlying DOM node
- `__init_node__(node)` / `__reset_node__()` manage the underlying reference

## Design Constraints

- **No virtual DOM diffing**: `RepeatElement` and `SwitchElement` completely regenerate children on change — no key-based reconciliation
- **DynamicElement nesting is forbidden**: `DynamicElement._create_child_element()` raises `WebComPyException` if a child is also a `DynamicElement`
- **Boolean attribute handling**: `True` renders as attribute present with empty string value, `False` removes the attribute
- **Event handler proxying**: All event handlers are proxied via `pyscript.ffi.create_proxy()` in browser, and `destroy()` is called on removal