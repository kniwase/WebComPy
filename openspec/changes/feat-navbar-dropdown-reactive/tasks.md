- [ ] **Task 1**: Remove Bootstrap JS dependency from docs_app
  - Remove `bootstrap.bundle.min.js` script from `docs_app/bootstrap.py`
  - Remove Bootstrap CSS link from `docs_app/bootstrap.py`
  - Estimated: 15 min

- [ ] **Task 2**: Rewrite `docs_app/components/navigation.py` with reactive dropdown
  - Replace Bootstrap classes with semantic HTML
  - Add `Signal[bool]` for each dropdown's open state
  - Implement `@click` handler on toggle buttons
  - Add click-outside detection using `browser.document.addEventListener`
  - Add proper ARIA attributes (`aria-expanded`, `aria-haspopup`, `aria-controls`)
  - Maintain existing `Page` typed dict structure
  - Estimated: 45 min

- [ ] **Task 3**: Add minimal styling for dropdown visibility
  - Use `display: none/block` or `hidden` attribute for show/hide
  - Add basic positioning styles via scoped_style or inline styles
  - Keep it minimal since Tailwind migration follows
  - Estimated: 15 min

- [ ] **Task 4**: Test dropdown functionality
  - Start dev server and verify dropdown open/close
  - Verify click-outside closes dropdowns
  - Verify navigation links still work
  - Verify mobile hamburger menu (if applicable)
  - Estimated: 30 min

- [ ] **Task 5**: Run lint and typecheck
  - `uv run ruff check .`
  - `uv run pyright`
  - Estimated: 10 min
