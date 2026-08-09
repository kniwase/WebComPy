# Tasks: feat-typed-response

## 1. Core encoder

- [x] 1.1 Implement `encode_with_meta(value) -> tuple[json_data, meta]` in a framework-neutral module: dataclasses, pydantic (duck-typed `model_dump()`), plain structures; type tags for bytes/set/tuple/decimal/datetime/date/time/uuid
- [x] 1.2 Define and implement the path grammar (leading candidate: JSON Pointer RFC 6901) with escaping tests for keys containing dots/brackets/slashes
- [x] 1.3 Implement body-mode validation: top-level object required, explicit error for array/scalar with guidance message
- [x] 1.4 Ensure no `__webcompy_` keys or inline tags appear in pristine bodies (regression test)

## 2. FastAPI contrib

- [x] 2.1 Create `packages/webcompy-server/src/webcompy_server/contrib/__init__.py` and `contrib/fastapi.py` with `TypedJSONResponse(JSONResponse)` (lazy imports, header mode default, body mode option)
- [x] 2.2 Verify importing `webcompy_server` without FastAPI installed does not fail; importing the contrib module without FastAPI raises a clear error

## 3. Client consumption

- [x] 3.1 Extend `from_json` with an optional `meta` parameter applying metadata-driven restoration at recorded paths before schema-driven reconstruction
- [x] 3.2 Wire metadata recognition into the `HttpClient` `response_type` path: read `__webcompy_transfer_meta__` (precedence) or `X-WebComPy-Transfer-Meta` header; closed-set tag decoding only
- [x] 3.3 Ensure browser `FetchPort` responses expose headers sufficiently for header-mode recognition (adjust `Response` wrapper if needed)

## 4. Tests

- [x] 4.1 Encoder unit tests: each type tag, nested paths, pydantic input, empty-meta case
- [x] 4.2 Body-mode contract tests: object injection, array/scalar explicit error, no fallback wrapper
- [x] 4.3 Contrib test (FastAPI installed in dev deps): `TypedJSONResponse` header/body modes; non-WebComPy client sees ordinary JSON
- [x] 4.4 Client tests: bytes/set/tuple/Decimal restoration, precedence rules, unknown-tag behavior (lenient default, strict error), absent-metadata parity
- [ ] 4.5 Integration test: mounted FastAPI endpoint returning `TypedJSONResponse` consumed by a component via `response_type`, in SSR and browser paths

## 5. Verification

- [ ] 5.1 `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run python -m pytest tests/ --tb=short` all pass

## 6. Spec reference sync

- [ ] 6.1 Update AGENTS.md: add `typed-response` to the Current Specs list; add File→Spec Mapping entries for the metadata-encoder module and `webcompy_server/contrib/` (`typed-response/spec.md`), and the `typed-api-client` client-consumption rows
- [ ] 6.2 Check `.opencode/skills/webcompy-review/SKILL.md` for stale assumptions and sync invariant headings/spec references
- [ ] 6.3 Run `python3 scripts/check-doc-spec-refs.py` and confirm it passes
