- [ ] **Task 1**: Remove Bootstrap JS dependency from docs_app
  - Remove only `bootstrap.bundle.min.js` script from `docs_app/bootstrap.py`
  - **Keep** Bootstrap CSS link (`bootstrap.min.css`) in `docs_app/bootstrap.py` — removing it now would leave the navbar unstyled until Tailwind migration
  - Estimated: 10 min

- [ ] **Task 2**: Rewrite `docs_app/components/navigation.py` with reactive dropdown
  - Replace Bootstrap navbar classes with semantic HTML + minimal inline styles
  - Add `Signal[bool]` for each dropdown's open state
  - Implement `@click` handler on toggle buttons to toggle state
  - Add click-outside detection using `browser.document.addEventListener`
  - Add proper ARIA attributes (`aria-expanded`, `aria-haspopup`, `aria-controls`)
  - Maintain existing `Page` typed dict structure
  - Estimated: 45 min

- [ ] **Task 3**: Implement mobile responsive hamburger menu
  - Add a hamburger toggle button for mobile viewports
  - Use `Signal[bool]` for mobile menu open/close state
  - Show/hide navigation links based on menu state
  - Estimated: 30 min

- [ ] **Task 4**: Add event listener cleanup on component destroy
  - Store reference to document click handler
  - Remove the handler when the navbar component is destroyed to prevent memory leaks
  - Use `context.on_before_destroying` or equivalent lifecycle hook
  - Estimated: 15 min

- [ ] **Task 5**: Test dropdown functionality
  - Start dev server and verify dropdown open/close
  - Verify click-outside closes dropdowns
  - Verify navigation links still work
  - Verify mobile hamburger menu works
  - Estimated: 30 min

- [ ] **Task 6**: Run lint and typecheck
  - `uv run ruff check .`
  - `uv run pyright`
  - Estimated: 10 min
