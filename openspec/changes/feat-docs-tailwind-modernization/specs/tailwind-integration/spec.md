# Tailwind CSS Integration

## Purpose

Enable WebComPy applications to use Tailwind CSS utility classes for styling. This includes CDN-based usage with local asset management for standalone/offline support, and demonstrates how Tailwind can coexist with WebComPy's `scoped_style` feature.

## ADDED Requirements

### Requirement: Tailwind CSS SHALL be loadable from local assets

When `standalone=True`, Tailwind CSS CDN JS SHALL be served from local files rather than external CDN.

#### Scenario: Standalone mode with local Tailwind
- **WHEN** `app_config.standalone=True` and Tailwind JS is placed in `static/tailwindcss.js`
- **AND** the app references it via `app.append_script({"src": "tailwindcss.js"}, in_head=True)`
- **THEN** the generated site SHALL serve `tailwindcss.js` from the local `_webcompy-assets/` directory
- **AND** no external CDN requests SHALL be made for Tailwind CSS

### Requirement: Utility classes SHALL work alongside scoped_style

Components using Tailwind utility classes SHALL continue to work with components using `scoped_style`. Both styling methods SHALL coexist without conflicts.

#### Scenario: Mixed styling in one app
- **WHEN** component A uses Tailwind classes (`class="p-4 bg-gray-100"`)
- **AND** component B uses `scoped_style` with custom selectors
- **THEN** both components SHALL render correctly
- **AND** their styles SHALL not interfere with each other

### Requirement: Tailwind dark mode SHALL work with class strategy

When using Tailwind's `darkMode: 'class'` configuration, applying `.dark` to the `<html>` element SHALL activate dark mode utility classes (`dark:bg-gray-900`, etc.).

#### Scenario: Dark mode class activation
- **WHEN** the `<html>` element has `class="dark"`
- **AND** an element has `class="bg-white dark:bg-gray-900"`
- **THEN** the element SHALL render with dark background in dark mode
- **AND** light background in light mode
