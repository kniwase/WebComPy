# Tasks: feat-typed-api-client

## 1. Deserializer core

- [ ] 1.1 Implement `from_json(cls, data, *, strict=False) -> T` in a new module (packages/webcompy/src/webcompy/ajax/_serde.py): dataclass reconstruction via `dataclasses.fields()` + `typing.get_type_hints()`, with per-class hint caching
- [ ] 1.2 Support containers: `list[T]`, `dict[str, T]`, `Optional[T]`, `Union` (structural match in declaration order)
- [ ] 1.3 Support leaf coercion: `datetime`/`date`/`time` (ISO-8601 via `fromisoformat`), `UUID`, `Enum` (by value)
- [ ] 1.4 Implement strict/lenient modes (unknown-key handling, missing-field errors) with descriptive error messages naming field and expected type
- [ ] 1.5 Re-export the public API from `webcompy.ajax` and add a dedicated `TypedResponseError` (or similarly named) framework exception

## 2. HttpClient integration

- [ ] 2.1 Add keyword-only `response_type` parameter with `@overload` + `TypeVar` signatures to `HttpClient` verb methods (get/post/put/delete/patch/head/options), preserving `Response` return when omitted
- [ ] 2.2 Wire typed calls through the existing FetchPort path; raise on non-2xx before deserialization; raise the dedicated exception on JSON/schema mismatch

## 3. Transfer opt-out

- [ ] 3.1 Add `transfer: bool = True` to `use_async_result` (packages/webcompy/src/webcompy/components/_hooks.py) and mark the entry non-transferable
- [ ] 3.2 Make `collect_transfer_data()` (packages/webcompy/src/webcompy/hydration/_collect.py) skip non-transferable async-result entries
- [ ] 3.3 Verify browser hydration falls back to client-side execution when no transferred entry exists

## 4. Tests

- [ ] 4.1 Serde unit tests: flat/nested dataclasses, list/dict/Optional/Union, datetime/date/UUID/Enum coercion, top-level list/scalar targets, strict vs lenient, error messages
- [ ] 4.2 Serde test: schema module using `from __future__ import annotations`
- [ ] 4.3 HttpClient tests: untyped call returns `Response`; typed call returns `T`; type inference verified via pyright
- [ ] 4.4 Integration test (webcompy_testing): typed self-site fetch during SSR uses ASGITransport and populates the transfer cache
- [ ] 4.5 Integration test: `transfer=False` result absent from hydration payload; browser executes the fetch after hydration; SSG artifact does not contain the data

## 5. Docs and verification

- [ ] 5.1 Add docs/example: shared dataclass schema used from both a FastAPI endpoint and a WebComPy component via `response_type` (per `doc-spec-references`: docs reference the owning specs as source of truth rather than transcribing requirement prose)
- [ ] 5.2 `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run python -m pytest tests/ --tb=short` all pass

## 6. Spec reference sync

- [ ] 6.1 Update AGENTS.md: add `typed-api-client` to the Current Specs list; add File→Spec Mapping entries for the new serde module (`webcompy/ajax/_serde.py` → `typed-api-client/spec.md`) and the modified `webcompy/ajax/` (`HttpClient`), `webcompy/components/` (`use_async_result`), and `webcompy/hydration/` (`_collect.py`) rows (`typed-api-client` + `composables`)
- [ ] 6.2 Check `.opencode/skills/webcompy-review/SKILL.md` for stale assumptions and sync invariant headings/spec references
- [ ] 6.3 Run `python3 scripts/check-doc-spec-refs.py` and confirm it passes
