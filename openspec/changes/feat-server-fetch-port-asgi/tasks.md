- [ ] **Task 1**: Add `is_self_site_url()` method to `FetchPort` ABC
  - Add `is_self_site_url(url: str) -> bool` **non-abstract** method to `FetchPort` in `webcompy/ports/_fetch.py` with a default implementation returning `False`
  - URLs starting with `/` or `.` are self-site; all others are external
  - `BrowserFetchPort` inherits the default `False` (browser always fetches externally); `ServerFetchPort` overrides to return `True` for self-site URLs
  - Estimated: 30 min

- [ ] **Task 2**: Rewrite `ServerFetchPort` with dual-client architecture
  - In `webcompy/ports/_server/_fetch.py`:
    - Keep `_external_client = httpx.AsyncClient()` for external URLs
    - Add `_self_site_client: httpx.AsyncClient | None = None` (created by `configure()`)
    - Add `_asgi_app: ASGIApp | None = None`, `_blocked_paths: list[str]`, `_base_url: str = "/"`
    - Implement `configure(asgi_app, blocked_paths)` method that creates `_self_site_client` with `httpx.ASGITransport(app=asgi_app)`
    - Implement `is_self_site_url()` returning `True` for `/` and `.` prefixed URLs
    - Update `fetch()` to:
      1. Classify URL (self-site vs external)
      2. If self-site and not configured → return 500 Response with error message
      3. If self-site and path is blocked → return 500 Response with blocking message
      4. If self-site → resolve path with `_base_url` prefix, use `_self_site_client`
      5. If external → use `_external_client`
    - Update `close()` to close both clients
    - Update `__del__` for both clients
  - Estimated: 1.5 hours

- [ ] **Task 3**: Expose `ServerFetchPort` from `WebComPyApp` and configure base_url
  - In `webcompy/app/_app.py`:
    - After creating `ServerFetchPort` in the server branch, store a reference to it (e.g., `self._server_fetch_port = server_fetch_port`)
    - Add a method or property to configure the fetch port's base_url from `app.config.base_url`
  - Estimated: 45 min

- [ ] **Task 4**: Configure `ServerFetchPort` in `create_asgi_app()`
  - In `webcompy/cli/_server.py`:
    - After `Starlette` app creation, extract `ServerFetchPort` from `app.di_scope`
    - Determine blocked paths from `app.routes` (page routes that return HTML)
    - Call `server_fetch_port.configure(asgi, blocked_paths)` with the Starlette app and blocked paths
    - Set `base_url` from `app.config.base_url`
  - Estimated: 1 hour

- [ ] **Task 5**: Configure `ServerFetchPort` in `generate_static_site()`
  - In `webcompy/cli/_generate.py`:
    - Create a temporary ASGI app via `create_asgi_app()` (or a lightweight equivalent)
    - Extract `ServerFetchPort` from `app.di_scope`
    - Determine blocked paths from `app.routes`
    - Call `server_fetch_port.configure(asgi_app, blocked_paths)`
    - Set `base_url` from `app.config.base_url`
  - Estimated: 1 hour

- [ ] **Task 6**: Add unit tests for URL classification
  - Test `is_self_site_url()` with various URL patterns:
    - `/api/data` → True
    - `./relative` → True
    - `../parent` → True
    - `https://example.com` → False
    - `http://localhost:3000` → False
    - `//cdn.example.com/file` → False
    - Empty string → False
  - Estimated: 30 min

- [ ] **Task 7**: Add unit tests for `ServerFetchPort.configure()` and self-site routing
  - Test that `configure()` creates the self-site client
  - Test that self-site fetch before `configure()` returns 500
  - Test that blocked paths return 500
  - Test that non-blocked self-site paths are routed through ASGI transport
  - Test that external URLs use the external client
  - Test that `close()` cleans up both clients
  - Estimated: 1.5 hours

- [ ] **Task 8**: Add integration test for base_url resolution
  - Test that with `base_url="/myapp/"`, self-site path `/api/data` resolves to `/myapp/api/data`
  - Test that with `base_url="/"` (default), self-site path `/api/data` resolves to `/api/data`
  - Estimated: 30 min

- [ ] **Task 9**: Run lint, typecheck, and tests
  - `uv run ruff check .`
  - `uv run ruff format .`
  - `uv run pyright`
  - `uv run python -m pytest tests/ --tb=short`
  - Estimated: 15 min