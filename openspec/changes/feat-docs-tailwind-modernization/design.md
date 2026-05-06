## Context

The docs_app serves as both the documentation site and the primary demonstration of WebComPy's capabilities. Its current design uses Bootstrap 5 CSS with custom `scoped_style` CSS-in-Python. While functional, this appears dated compared to modern documentation sites like GitHub Docs, VitePress, or Astro Starlight.

This change migrates the entire docs_app to Tailwind CSS with a GitHub-like aesthetic. The migration must:
1. Maintain all existing functionality (navigation, demos, code highlighting)
2. Preserve `scoped_style` as a framework feature demonstration
3. Work in standalone mode (all assets local)
4. Add light/dark theme switching

## Goals / Non-Goals

**Goals:**
- Modernize docs_app visual design with Tailwind CSS utility classes
- Implement GitHub-like light/dark theme with toggle in navbar
- Manage highlight.js themes locally for offline support
- Maintain all existing content and functionality
- Preserve `scoped_style` usage in demo components

**Non-Goals:**
- Creating reusable Tailwind components or plugin system
- Removing `scoped_style` (intentionally preserved)
- System-level dark mode preference detection
- Custom Tailwind configuration or plugins
- Complex animations or transitions

## Decisions

### Decision: Use Tailwind CDN with local copy for standalone

Tailwind CDN (`https://cdn.tailwindcss.com`) is a ~3MB JS file that compiles utility classes in the browser. For standalone mode, download it to `static/tailwindcss.js` and serve locally.

**Alternatives considered:**
- Tailwind CLI build step: requires Node.js, contradicts Python-only philosophy
- Tailwind CSS file directly: CDN JS version includes JIT compiler and is simpler to integrate
- Windi CSS / UnoCSS: less mature, smaller ecosystem

### Decision: Class-based dark mode with `html.dark`

Use Tailwind's `darkMode: 'class'` strategy. The `.dark` class is applied to the `<html>` element via `app.set_html_attr("class", computed(...))` from `feat-html-attrs-control`.

```python
theme = Signal("light")
app.set_html_attr("class", computed(lambda: theme.value))
```

**Alternatives considered:**
- `darkMode: 'media'` (system preference): simpler but no manual toggle
- `data-theme` attribute: works but Tailwind's `dark:` prefix requires `.dark` or `[data-theme="dark"]` config
- Toggle only inside `#webcompy-app`: doesn't affect highlight.js theme or global scrollbars

### Decision: GitHub dark theme for highlight.js

Use `github-dark-dimmed` for dark mode and `github` (default) for light mode. Store both CSS files locally in `static/highlightjs/`.

**Alternatives considered:**
- Single theme: simpler but less polished
- `atom-one-dark`: popular but less "GitHub-like"
- `vs2015`: not matching the GitHub aesthetic

### Decision: scoped_style and Tailwind coexist

`scoped_style` continues to work alongside Tailwind classes. `scoped_style` is best for complex selectors and animations; Tailwind handles layout, spacing, colors, and typography.

**Rationale:** This demonstrates WebComPy's flexibility and doesn't break existing code.

### Decision: Minimal inline styles for dropdown visibility

Since dropdowns were just implemented without Bootstrap in `feat-navbar-dropdown-reactive`, use minimal inline styles or `hidden` attribute for show/hide rather than Tailwind classes. This avoids a circular dependency between changes.

## Risks / Trade-offs

- **[Risk]** Tailwind CDN JS is ~3MB, increasing page load time → **Mitigation:** Only loaded once, cached by browser; standalone mode ensures no external network dependency
- **[Risk]** `scoped_style` and Tailwind may have specificity conflicts → **Mitigation:** `scoped_style` uses component-scoped selectors which typically have higher specificity; document the coexistence pattern
- **[Risk]** Dark mode toggle without `feat-html-attrs-control` won't work → **Mitigation:** Document dependency; implement toggle UI but only enable after prerequisite change is merged
- **[Risk]** Visual regression during migration period → **Mitigation:** Make all class changes atomically in one commit; test thoroughly before merge

## Migration Plan

1. Download `tailwindcss.js` to `static/tailwindcss.js`
2. Download highlight.js themes to `static/highlightjs/`
3. Update `bootstrap.py` to remove Bootstrap, add Tailwind and local assets
4. Rewrite all component class names from Bootstrap to Tailwind
5. Add theme toggle to navbar
6. Test light/dark switching
7. Verify standalone generation works

## Open Questions

1. Should we pin a specific Tailwind CDN version? (Currently: latest)
2. Should `scoped_style` docs mention Tailwind coexistence? (Yes, in a follow-up docs change)
