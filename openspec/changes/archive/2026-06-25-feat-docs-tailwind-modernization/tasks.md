> **Status: Superseded.** This task list is **superseded by [`feat-ui-toolkit-foundation`](../feat-ui-toolkit-foundation/tasks.md)**. The tasks below are not actionable; they are retained as a historical record of the abandoned Tailwind approach.

- [ ] **Task 1**: Download and place Tailwind CSS and highlight.js assets
  - Download `https://cdn.tailwindcss.com` to `static/tailwindcss.js`
  - Download highlight.js `github.min.css` (light theme) and `github-dark-dimmed.min.css` (dark theme) to `static/highlightjs/`
  - Estimated: 15 min

- [ ] **Task 2**: Update `docs_app/bootstrap.py`
  - Remove Bootstrap CSS link and JS script
  - Remove `eruda` script (dev-only, not needed for docs)
  - Add Tailwind CDN script tag — use local path `static/tailwindcss.js` (served via `static_files_dir`)
  - Add highlight.js light theme CSS as default
  - **Note**: Static files in `static/` are automatically copied by SSG and served by dev server via `ServerConfig.static_files_dir`; no `AppConfig.assets` registration needed for these files
  - Estimated: 20 min

- [ ] **Task 3**: Rewrite `docs_app/components/navigation.py` with Tailwind
  - Replace all Bootstrap classes with Tailwind utilities
  - Add responsive mobile menu (hamburger + collapsible menu)
  - Add theme toggle button (sun/moon icon or text)
  - Maintain dropdown functionality from `feat-navbar-dropdown-reactive`
  - Add ARIA attributes for accessibility
  - Estimated: 45 min

- [ ] **Task 4**: Rewrite `docs_app/components/demo_display.py` with Tailwind
  - Replace card classes with Tailwind utilities
  - Maintain two-card layout (demo + code)
  - Estimated: 20 min

- [ ] **Task 5**: Rewrite `docs_app/pages/not_found.py` with Tailwind
  - Simple centered layout with Tailwind
  - Estimated: 10 min

- [ ] **Task 6**: Rewrite `docs_app/templates/home.py` with Tailwind
  - Replace container/content/heading/body classes
  - Style tables with Tailwind utilities
  - Maintain `scoped_style` for table styling (demonstrates coexistence)
  - Estimated: 30 min

- [ ] **Task 7**: Implement theme switching logic
  - Create theme Signal in `docs_app/bootstrap.py` or shared module
  - Use `app.set_html_attr("class", computed(...))` (requires `feat-html-attrs-control`)
  - Switch highlight.js theme link reactively
  - Persist theme preference (optional: localStorage)
  - Estimated: 30 min

- [ ] **Task 8**: Test and verify
  - Start dev server: `uv run python -m webcompy start --dev --app docs_app.bootstrap:app`
  - Verify light theme default
  - Toggle dark theme and verify all components update
  - Verify dropdowns still work
  - Verify code highlighting switches themes
  - Test responsive design (mobile width)
  - Estimated: 30 min

- [ ] **Task 9**: Test standalone generation
  - Run `uv run python -m webcompy generate --app docs_app.bootstrap:app`
  - Verify `dist/` contains all local assets
  - Verify no external CDN requests needed
  - Estimated: 15 min

- [ ] **Task 10**: Run lint and typecheck
  - `uv run ruff check .`
  - `uv run pyright`
  - Estimated: 10 min
