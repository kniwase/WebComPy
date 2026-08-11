# Tasks: fix-docs-mobile-sidebar-contract

## 1. Spec Delta

- [x] 1.1 MODIFY the `docs-site-documents` requirement "The docs section shall use a nested-route shared layout": state in the body that the layout instance and section-open state survive sibling navigation while the transient mobile overlay closes on navigation, and update the "Layout persists across sibling navigation" scenario's THEN clause accordingly

## 2. Verification

- [x] 2.1 Run `openspec validate fix-docs-mobile-sidebar-contract --strict`
- [x] 2.2 Run `python3 scripts/check-doc-spec-refs.py`

## 3. Archive

- [x] 3.1 Archive the change so the delta syncs into `openspec/specs/docs-site-documents/spec.md`
- [x] 3.2 Re-run `openspec validate --all` and `python3 scripts/check-doc-spec-refs.py` after the sync