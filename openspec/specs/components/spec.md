# Component System

## Overview

WebComPy supports two component definition styles: function-style and class-style. Both produce `ComponentGenerator` objects that can be invoked to create `Component` instances (which extend `ElementBase` and render to the DOM).

## Function-Style Components

- Created via `@define_component` decorator on a setup function
- Setup function receives a `ComponentContext[PropsType]` and returns `ElementChildren`
- The function gets a `__webcompy_componet_definition__` attribute (note: "componet" typo)
- Lifecycle hooks registered via context methods: `context.on_before_rendering(func)`, `context.on_after_rendering(func)`, `context.on_before_destroy(func)`
- Slot access via `context.slots(name, fallback?)`
- Document head management via `context.get_title()`, `context.set_title()`, `context.get_meta()`, `context.set_meta()`

## Class-Style Components

- Subclass `ComponentAbstract[PropsType]` (or `NonPropsComponentBase` / `TypedComponentBase(PropsType)`)
- **Cannot instantiate directly** (`__new__` raises `WebComPyComponentException`); use `__get_component_instance__(context)` instead
- Template method decorated with `@component_template`
- Lifecycle decorators: `@on_before_rendering`, `@on_after_rendering`, `@on_before_destroy`
- Class name is converted to kebab-case for the component tag name via `_camel_to_kebab_pattern`
- Component ID generated via MD5 hash of the name

## ComponentGenerator

- Wrapper that produces `Component` instances when called
- Manages **scoped CSS** via `scoped_style` property (dict syntax)
- CSS selectors are augmented with `[webcompy-cid-{id}]` attribute selectors
- The `_combinator_pattern` regex handles CSS selector combinators (`,`, `>`, `+`, `~`, space) for scoping
- **`ComponentStore`** (singleton): Global registry of all component generators by name; raises exception on duplicate names

## Component (Runtime Instance)

- Subclass of `ElementBase`, wrapping either a function-style or class-style component definition
- **`__init_component(property)`**: Takes the rendered Element from the template, copies its tag/attrs/events/children, adds `webcompy-component` and `webcompy-cid-*` attributes
- **`HeadPropsStore`** (class variable): Global `ReactiveDict` for `titles` and `head_metas`
  - `title` is a `computed_property` returning the last title value
  - `head_meta` is a `computed_property` flattening all meta dicts
- **Lifecycle**: `_render()` calls `on_before_rendering`, then parent `_render()`, then `on_after_rendering`
- **`_remove_element()`**: Removes title/meta entries from `HeadPropsStore` first, then calls `on_before_destroy`, then parent cleanup

## Context Types

### ComponentContext[PropsType] (Protocol)

- `props`, `slots()`, lifecycle hook registration, title/meta management

### Context[PropsType] (Implementation)

- Concrete class implementing `ComponentContext`
- Stores props, slots, component name, and callbacks
- `__get_lifecyclehooks__()`: Returns dict of registered lifecycle callbacks

### ClassStyleComponentContenxt[PropsType] (Protocol)

- Subset of `ComponentContext` without lifecycle hook registration (those are class decorators)

## Scoped CSS

- Set via `ComponentGenerator.scoped_style = {...}` (dict of selector → declaration dict)
- Each CSS rule selector is prefixed with `[webcompy-cid-{md5hash}]` to scope styles to the component
- Combinators (`,`, `>`, `+`, `~`, space) are preserved in the transformation
- The combined scoped style string is available via `ComponentGenerator.scoped_style` (property)

## ComponentProperty (TypedDict)

- `component_id`: str (MD5 hash)
- `component_name`: str (kebab-case or function name)
- `template`: ElementChildren
- `on_before_rendering`, `on_after_rendering`, `on_before_destroy`: callbacks