# Tasks

## 1. Signal Ownership & Element Runtime Fix

- [x] 1.1 Add single-owner claiming (`_OwnedComputed._claimed` + `_claim_owned_computed`) in `packages/webcompy/src/webcompy/signal/_computed.py` and verify unit tests compile cleanly.
- [x] 1.2 Override `ElementAbstract.__setattr__ = object.__setattr__` (under `if not TYPE_CHECKING:`), update `ElementAbstract` docstring, and clear `_callback_nodes` in `_remove_element` in `packages/webcompy/src/webcompy/elements/types/_abstract.py`.
- [x] 1.3 Update `Element` and `ElementBase` (`_element.py`), radio `:bind` (`_bind.py`), `Component._init_component` (`_component.py`), `TextElement`/`RawHTMLElement` (`_text.py`), `RepeatElement`/`MultiLineTextElement` (`_repeat.py`), and `SwitchElement` (`_switch.py`) to claim only framework-owned `_OwnedComputed` signals and transfer root element members on `AppDocumentRoot`.
- [x] 1.4 Update template and router elements (`template/_binder.py`, `template/_markdown_for.py`, `router/_link.py`, `router/_view.py`) to convert internal derived computeds to `_OwnedComputed`, pre-claim component-tag `_OwnedComputed` props safely, guard `MarkdownForElement` against duplicate allocation, and explicitly register router internal computeds.
- [x] 1.5 Check docstring coverage and API reference sync (`scripts/check-docstrings.py`, `scripts/generate_api_reference.py --check`, `uv run pydoclint`) and regenerate API reference skeleton if needed.

## 2. Regression Tests & Dual-Run Classification

- [x] 2.1 Add comprehensive unit tests in `tests/test_element_signal_ownership.py` verifying caller-owned signal preservation (all 6 affected element classes, `Switch` patching, `RouterLink._refresh`, component-tag prop isolation) and framework-owned signal cleanup without consumer-edge leaks.
- [x] 2.2 Add a real-PyScript browser-tier regression test in `tests/browser/` obeying `scripts/check-browser-imports.py`, and verify `tests/.dualrun/ineligible.json` stays in sync via `uv run python -m pytest tests/test_dualrun_classifier.py`.

## 3. Spec Sync, Verification & Archiving

- [x] 3.1 Sync delta specs into `openspec/specs/elements/spec.md` and `openspec/specs/reactive/spec.md`, update `openspec/SPEC_INDEX.md` and `.agents/skills/webcompy-review/SKILL.md`, and verify `npx --no-install openspec validate --specs` and `python3 scripts/check-doc-spec-refs.py` pass.
- [x] 3.2 Run full local CI (`ruff`, `pydoclint`, `check-browser-imports.py`, `pyright`, `pytest tests/`, `webcompy generate`, `scripts/run-browser-tests.sh`, and core E2E groups `reactive-lists dynamic-control template router`), verify 0 failures, and archive the change to `openspec/changes/archive/`.
