## 1. Apply CSS Fix

- [ ] 1.1 Change `left: 0` to `right: 0` on `.navbar-dropdown` in `docs_app/components/navigation.py`

## 2. Verify

- [ ] 2.1 Run lint check (`uv run ruff check .`)
- [ ] 2.2 Run formatter check (`uv run ruff format --check .`)
- [ ] 2.3 Start dev server and visually verify dropdown does not overflow viewport on desktop
- [ ] 2.4 Verify mobile layout (≤768px) is unaffected
- [ ] 2.5 Verify the fix renders correctly in both light and dark themes
