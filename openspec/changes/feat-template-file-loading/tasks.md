## 1. ResourcePort ABC and exception

- [x] 1.1 Create `packages/webcompy/src/webcompy/ports/_resource.py` defining `ResourcePort(ABC)` with two abstract methods: `async def load_text(self, path: str) -> str` and `async def load_bytes(self, path: str) -> bytes`
- [x] 1.2 Define `ResourceNotFoundError(Exception)` in the same module — message SHALL include the resource path and the implementation context (server / browser)
- [x] 1.3 Add `RESOURCE_PORT_KEY = InjectKey[ResourcePort]("webcompy-port-resource")` to `webcompy/ports/_keys.py`
- [x] 1.4 Add `RESOURCE_DATA_KEY = InjectKey[dict[str, str]]("webcompy-resource-data")` to `webcompy/di/_keys.py` (mirrors `HYDRATION_DATA_KEY` and `HYDRATION_SIGNAL_DATA_KEY`)
- [x] 1.5 Deferred to archive-time spec sync (M13): the `port-abstraction/spec.md` import-surface scenario is updated when this change's delta is synced to main specs. Do **not** edit the main spec during implementation.
- [x] 1.6 Add unit test verifying `ResourcePort` cannot be instantiated directly (ABC enforcement)

## 2. ServerResourcePort implementation

- [ ] 2.1 Create `webcompy_server/ports/_resource.py` defining `class ServerResourcePort(ResourcePort)`
- [ ] 2.2 Constructor accepts `(app_package_path: pathlib.Path, allow_list: frozenset[str])`; internalize a per-instance `recorded: dict[str, bytes]` accumulator
- [ ] 2.3 Implement `async load_text(self, path: str) -> str`: validate membership in `allow_list`; resolve `(app_package_path / path).resolve()`; check containment inside `app_package_path` via `realpath`; read with `Path.read_text(encoding="utf-8")`; record `(path, bytes(text, "utf-8"))`; return decoded text
- [ ] 2.4 Implement `async load_bytes(self, path: str) -> bytes`: same validation chain; read with `Path.read_bytes()`; record `(path, content)`; return content
- [ ] 2.5 All failure paths (not in allow-list, traversal, missing file, decode error) raise `ResourceNotFoundError`
- [ ] 2.6 Add `get_recorded_resources() -> dict[str, bytes]` returning the accumulator (used by payload generator)
- [ ] 2.7 Add unit tests: (a) happy path text, (b) happy path bytes, (c) missing file, (d) traversal, (e) outside allow-list, (f) recorded-resources accumulator

## 3. BrowserResourcePort implementation

- [ ] 3.1 Create `webcompy/ports/_browser/_resource.py` defining `class BrowserResourcePort(ResourcePort)`
- [ ] 3.2 Constructor requires `ENVIRONMENT == "pyscript"` and asserts it
- [ ] 3.3 Implement `async load_text(self, path) -> str`: first try `inject(RESOURCE_DATA_KEY, default={}).get(path)`; if present, decode base64 → bytes → utf-8 → return; else fetch `{base_url}_webcompy-resource/{path}` via `inject(FETCH_PORT_KEY).fetch(...)` and return response text
- [ ] 3.4 Implement `async load_bytes(self, path) -> bytes`: same priority chain, return base64-decoded bytes (payload) or response bytes (fetch)
- [ ] 3.5 On fetch failure (HTTP non-2xx or exception), raise `ResourceNotFoundError` mentioning both the payload miss and the fetch failure
- [ ] 3.6 Base URL is threaded via constructor: `BrowserRenderContext._register_ports` (in `webcompy/app/_render_context.py:277` area, where `BrowserFetchPort()` is already provided) has access to `self._config.base_url`; pass it positionally to `BrowserResourcePort(self._config.base_url)`. (M1: `HostPort` does not expose `base_url`; `app.config` is not reachable inside a port constructor.)
- [ ] 3.7 Add unit tests for the lookup-priority logic using `monkeypatch`-injected `RESOURCE_DATA_KEY` and a fake `FetchPort`; full browser integration test deferred to E2E

## 4. RenderContext port provisioning

- [ ] 4.1 Modify `webcompy_server/_context.py` (`ServerRenderContext._register_ports` at line 28): read `resource_port = getattr(self._app, "_server_resource_port", None)`; if non-`None`, `self._di_scope.provide(RESOURCE_PORT_KEY, resource_port)`. When `None`, **do not** provide the key (mirrors the absence of fallback for `_server_fetch_port`); `inject(RESOURCE_PORT_KEY, default=None)` returns `None` cleanly for tests. `RESOURCE_DATA_KEY` is **not** provided server-side (no payload on the server).
- [ ] 4.2 Modify `webcompy/app/_render_context.py` (`BrowserRenderContext._register_ports`): provide `RESOURCE_PORT_KEY` with `BrowserResourcePort(self._config.base_url)` (see task 3.6 for the base_url threading rationale)
- [ ] 4.3 In `BrowserRenderContext._load_hydration_payload` (or equivalent hook), populate `RESOURCE_DATA_KEY` from `payload.resources` after the existing fetch/async_result/signal population
- [ ] 4.4 Modify `webcompy_server/__init__.configure_server_context(app, *, resource_port: ServerResourcePort | None = None)`: when `resource_port` is non-`None`, set `app._server_resource_port = resource_port` (mirrors the existing `app._server_fetch_port = ServerFetchPort()` assignment). **Single owner**: only `webcompy_cli._build.resolve_build_artifacts` constructs `ServerResourcePort(build_config.app_package_path, allow_list)` and calls `configure_server_context(app, resource_port=port)`. `create_asgi_app` does **not** call `configure_server_context` (M2/M3 resolution). The optional-with-default signature preserves all 14 existing test-helper call sites that pass only `app`.
- [ ] 4.5 Add unit test for ServerRenderContext injection via TestRenderer

## 5. Hydration payload: resources field

- [ ] 5.1 Modify `packages/webcompy/src/webcompy/hydration/_payload.py`: bump **both** version constants — the dataclass default `TransferPayload.__webcompy_transfer_version__: int = 3` (line 31) **and** the module-level `CURRENT_TRANSFER_VERSION: int = 3` (line 38, used by `collect_transfer_data`). Add `resources: dict[str, str] = field(default_factory=dict)` to `TransferPayload`.
- [ ] 5.2 Update `_SUPPORTED_VERSIONS` frozenset to `{1, 2, 3}`
- [ ] 5.3 Update `serialize_payload()` to include the `resources` field via the codec path (base64-encode raw bytes → str)
- [ ] 5.4 Update `deserialize_payload()` to read the `resources` field when present in v3; default to empty dict for v1/v2
- [ ] 5.5 Add test cases: v3 roundtrip, v2 deserializes with empty resources, v1 deserializes with empty resources, unknown version rejected
- [ ] 5.6 Verify backward compat: existing tests still pass for v2/v1 payloads

## 6. SSR payload population

- [ ] 6.1 In `packages/webcompy/src/webcompy/hydration/_collect.py` (`collect_transfer_data` at line 24): after the existing `fetch_port = inject(FETCH_PORT_KEY, default=None)` block (lines 31-33), add `resource_port = inject(RESOURCE_PORT_KEY, default=None)`; if non-`None` and `hasattr(resource_port, "get_recorded_resources")`, call it to obtain `dict[str, bytes]`; base64-encode each value into `dict[str, str]`; pass `resources=...` into the `TransferPayload(...)` constructor at lines 51-56. (M5: payload assembly lives in `_collect.py`, **not** `_html.py:_generate_html_impl`. The latter only builds the HTML envelope; payload is injected as a `<script>` block at `_html.py:212-213`.) **Note**: there is exactly ONE `ServerResourcePort` per `RenderContext` (DI scope is per-request, not per-component), so no merging is needed (M6).
- [ ] 6.2 ~~Multiple `ServerResourcePort` instances may exist in nested scopes~~ **DELETED (M6)**: DI scope is per-`RenderContext`, not per-component; there is exactly one `ServerResourcePort` per render context. No merging logic required.
- [ ] 6.3 Add test: SSR'd component using `load_text("a.html")` produces a hydration payload whose `resources` key contains the base64 encoding of the file's content

## 7. CLI server endpoint

- [ ] 7.1 In `webcompy_cli/config/_build_config.py`: add `resources: list[str] | None = None` and `resource_exclude: list[str] | None = None`; REMOVE `assets: dict[str, str] | None` field
- [ ] 7.2 Add `_detect_resources(app_package_path, include_patterns, exclude_patterns) -> frozenset[str]` helper in `webcompy_cli/_build.py`: walk the package directory, match patterns via `pathlib.PurePath.match`, subtract excludes, return POSIX-relative paths
- [ ] 7.3 Default include patterns when `resources is None`: `["**/*.html", "**/*.css", "**/*.md", "**/*.svg", "**/*.txt"]`; empty list disables auto-detection
- [ ] 7.4 Always-excluded paths: `__pycache__`, `.git`, `.webcompy_modules`, any path matching `*.pyc` / `*.tmp`
- [ ] 7.5 In `webcompy_cli/_build.py` `resolve_build_artifacts`: compute the allow-list at startup; pass it to `_server.py` and `_generate.py` via `BuildArtifacts`
- [ ] 7.6 In `webcompy_cli/_server.py` (`create_asgi_app`): register `GET {base_url}_webcompy-resource/{path:path}` route when `artifacts.resource_allow_list` is non-empty
- [ ] 7.7 Endpoint handler: validate path is in allow-list (404 if not); resolve `(app_package_path / path).resolve()` and verify containment (`realpath` containment check, 403 on failure); read file; return with `Content-Type` from `mimetypes.guess_type` and `Cache-Control` per dev/prod mode
- [ ] 7.8 Add unit tests: (a) allow-listed file is served with correct Content-Type, (b) non-allow-listed returns 404, (c) traversal returns 404/403, (d) symlink escape returns 403

## 8. SSG resource static copy

- [ ] 8.1 In `webcompy_cli/_generate.py`: the resource-copy step runs **after** `create_asgi_app(app, build_config, mode="prod")` populates `serving.artifacts` (current line 86-87), specifically between the runtime-asset copy block end (line 111) and the framework-UI-styles block start (line 113). Walk `artifacts.resource_allow_list` and copy each file to `{dist_dir}/_webcompy-resource/{path}` via `shutil.copy2` with `dst.parent.mkdir(parents=True, exist_ok=True)`. (M7: the allow-list only becomes available after `create_asgi_app`; placing the copy alongside the other artifact-driven copies at lines 89-111 is the natural slot.)
- [ ] 8.2 Preserve relative directory layout (parent directories auto-created via `os.makedirs`)
- [ ] 8.3 Add test invoking `generate_static_site(app)` and verifying that allowed resources appear in `dist/_webcompy-resource/` with correct content

## 9. Public helpers `webcompy.resources.load_text` / `load_bytes`

- [ ] 9.1 Create `packages/webcompy/src/webcompy/resources.py` with two async functions: `load_text(source: str | Path) -> str` and `load_bytes(source: str | Path) -> bytes`
- [ ] 9.2 Helper logic: normalize `str` (pass through) or `Path` (use `as_posix()` if relative, raise if absolute); reject `..` segments; `inject(RESOURCE_PORT_KEY)`; raise `WebComPyException` if missing; delegate to the port method
- [ ] 9.3 Re-export `load_text` and `load_bytes` from `webcompy` (top-level `__init__.py`)
- [ ] 9.4 Add unit tests: (a) str path, (b) relative Path → POSIX, (c) absolute Path raises, (d) traversal raises, (e) missing RESOURCE_PORT_KEY raises, (f) integration with a fake ResourcePort

## 10. Remove legacy `load_asset` and assets machinery

- [ ] 10.1 Delete `packages/webcompy/src/webcompy/assets.py`
- [ ] 10.2 Delete `tests/test_assets.py`
- [ ] 10.3 From `webcompy/__init__.py` remove any import/export of `load_asset` and `AssetNotFoundError`
- [ ] 10.4 Confirm no internal imports of `load_asset` remain (search `webcompy/`, `webcompy-cli/`, `webcompy-server/`, `webcompy-testing/`, `docs_app/`, `tests/`)
- [ ] 10.5 In `webcompy_cli/_wheel_builder.py`: remove **three** helpers — `_generate_assets_registry` (lines 174-179), `_assets_to_package_data` (lines 153-171, becomes dead code after `assets=` removal per M12), and the `assets: dict[str, str] | None = None` parameter on `make_webcompy_app_package` (lines 300-308). Remove the `if assets:` block at lines 313-317. Also update `tests/test_wheel_builder.py`: remove import at line 9; remove or rewrite the test functions at lines 415, 423, 448, 449, 470 that exercise the removed helper (M8).
- [ ] 10.6 In `webcompy_cli/_build.py`: stop passing `build_config.assets` to `make_webcompy_app_package`
- [ ] 10.7 ~~Update `webcompy-cli/src/webcompy_cli/template_data/webcompy_config.py` scaffold~~ **DELETED (M9)**: confirmed the scaffold does not reference `assets`; the field was never added there. No-op.
- [ ] 10.8 Run `grep -r "load_asset\|_assets_registry\|\.assets(" .` to confirm zero remaining references before merge

## 11. CI review updates

- [ ] 11.1 Update `AGENTS.md` **File → Spec Mapping** table (heading at line 214, table at lines 218-241): **add two new rows** for `webcompy/ports/_resource.py` → `resource-port` and `webcompy_server/ports/_resource.py` → `resource-port`. (M10: there is no existing entry for `webcompy/assets.py` to "mark as removed" — that file simply no longer exists, so no row is added or modified for it.)
- [ ] 11.2 Update the **Current Specs List** in `AGENTS.md` (heading at line 301, table at lines 303-360): add a new row for `resource-port`. (M11: the on-disk AGENTS.md may differ from the system-prompt version — re-read the file immediately before editing to find the correct insertion line.)
- [ ] 11.3 Update `.opencode/agents/ci-review.md` invariants to note: (a) `load_text` / `load_bytes` require `RESOURCE_PORT_KEY` in DI scope; (b) failed resource load must surface as `ResourceNotFoundError` not silent fallback; (c) hydration payload `resources` field must not be omitted from v3; (d) `load_asset` must not be re-introduced

## 12. Main spec sync (archive time)

- [ ] 12.1 Run `openspec sync feat-template-file-loading` to merge the delta specs into main specs: add `resource-port/spec.md` (new), update `cli/spec.md` (ADDED), update `hydration-data-transfer/spec.md` (MODIFIED), update `wheel-builder/spec.md` (REMOVED)
- [ ] 12.2 Run `openspec validate` against the merged specs to confirm consistency

## 13. Future / Deferred (out of scope)

- [ ] 13.1 ETag / `If-None-Match` on the resource endpoint — defer to a separate change for production-side optimization
- [ ] 13.2 Compression-tuning specific to the `resources` field — defer until payload-size profiling demonstrates the default threshold is suboptimal
- [ ] 13.3 Change 5 (`feat-template-css-text`) and Change 6 (`feat-template-markdown`) revisions to consume `ResourcePort` — separate changes
