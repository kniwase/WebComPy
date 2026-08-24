## 1. Spec

- [x] 1.1 Add sync Requirement to `api-docstrings` delta

## 2. Governance docs

- [x] 2.1 Amend `AGENTS.md` (+1 line for same-PR sync)
- [x] 2.2 Amend `.opencode/skills/webcompy-review/SKILL.md` Docstring coverage perspective to flag inconsistency as must-fix and block approval

## 3. Verify

- [x] 3.1 Run `openspec validate --specs && openspec validate --changes && python3 scripts/check-doc-spec-refs.py && uv run pyright`
