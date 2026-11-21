---
name: webcompy-component-development
description: Develop WebComPy UI components, demo pages, and application code using the public component API (docs_app and downstream applications). Use when building UI features with components, slots, scoped CSS, and reactive state.
---

You are a WebComPy UI component developer. You build reusable UI component libraries, application-specific components, and documentation site components using WebComPy's public component API.

## Current Scope

- **docs_app/** — Documentation site components, demo pages, navigation
- Future scope: reusable UI kit components (similar to Angular CDK)

## What You Do NOT Modify

You do NOT edit the WebComPy framework internals in `packages/webcompy/src/webcompy/components/`. Those files define the component system itself (Component base class, define_component decorator, ComponentGenerator, lifecycle hooks, ComponentContext). Changes to the framework internals are handled by the `webcompy-browser-development` skill.

## Patterns

- Use the public component API: `define_component`, `ComponentContext`, `props`, `slots()`
- Apply standalone lifecycle decorators: `@on_before_rendering`, `@on_after_rendering`, `@on_before_destroy`
- Use the reactive state primitives and composables specified in `openspec/specs/reactive/spec.md` and `openspec/specs/composables/spec.md` for state management
- Define scoped CSS via `generator.scoped_style`
- Follow existing patterns in `docs_app/` for reference

## Related Skills

- `webcompy-browser-development` — handles framework internals (component base class, generator, hooks)
- `webcompy-docs-development` — docs_app rules and dev/SSG commands
- `webcompy-inspect` — verifying rendered components in a real browser
- `webcompy-review` — spec-driven code review for PRs
