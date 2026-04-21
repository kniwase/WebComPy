# Design: Hydration Performance Measurement

## Design Decisions

### D1: Opt-in profiling only
Profiling SHALL be opt-in (`profile=False` by default) to avoid any runtime overhead in production. The `profile` parameter is accepted by `WebComPyApp.__init__()` and forwarded from `AppConfig.profile` when constructed via CLI/SSG.

### D2: Store timestamps in a dict, emit at completion
Timestamps are recorded at capture points into `self._profile_data: dict[str, float]`. The final formatted output is emitted only once, when the loading indicator is removed (i.e., the app is fully visible). This avoids interleaving profile output with other logs during noisy initialization.

### D3: Use `time.perf_counter()` in browser (via Python JS bridge)
In the browser, `time.perf_counter()` is backed by the High-Resolution Time API and is the best available monotonic clock. It works in both standard Python and Pyodide without importing browser-specific APIs. On the server, it functions identically.

### D4: Bootstrap profiling code is inlined in generated HTML
When `profile=True`, the generated `<script type="py">` tag starts with a `perf_counter()` capture before any imports. The profile data object is passed to the Python bootstrap so that the browser-side `WebComPyApp` can use the first timestamp as its baseline.

### D5: Preserve one-line output format for readability
The final report is a 5-line summary showing elapsed time between consecutive phases, plus a total. This is concise enough for console inspection but detailed enough for regression tracking.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│ Browser entry: <script type="py">                     │
│  1. Record pyscript_ready (perf_counter)              │
│  2. Import modules                                    │
│  3. Call app.run()                                    │
├─────────────────────────────────────────────────────┤
│ WebComPyApp.__init__(..., profile=True)               │
│  ─ Record init_start                                  │
│  ─ DI setup, component registration                   │
│  ─ Record imports_done                                │
│  ─ Build AppDocumentRoot                                │
│  ─ Record init_done                                   │
├─────────────────────────────────────────────────────┤
│ AppDocumentRoot._render()   (inside app.run())          │
│  ─ Record run_start                                     │
│  ─ Walk tree, mount nodes, hydrate                    │
│  ─ Record run_done                                      │
│  ─ Remove #webcompy-loading                             │
│  ─ Record loading_removed                             │
│  ─ Emit formatted summary if profile=True               │
└─────────────────────────────────────────────────────┘
```

## API Design

### `AppConfig` field addition

```python
@dataclass
class AppConfig:
    app_package: Path | str = "."
    base_url: str = "/"
    dependencies: list[str] = field(default_factory=list)
    assets: dict[str, str] | None = None
    profile: bool = False  # NEW
```

### `WebComPyApp` extension

```python
class WebComPyApp:
    def __init__(self, ..., profile: bool = False):
        self._profile = profile
        self._profile_data: dict[str, float] = {}
        if self._profile:
            self._record_phase("init_start")
        ...

    @property
    def profile_data(self) -> dict[str, float] | None:
        return self._profile_data if self._profile else None

    def _record_phase(self, name: str) -> None:
        if self._profile:
            self._profile_data[name] = time.perf_counter()

    def _emit_profile_summary(self) -> None:
        if not self._profile:
            return
        data = self._profile_data
        pairs = [
            ("pyscript_ready", "imports_done", "pyscript_ready → imports_done"),
            ("imports_done", "init_done", "imports_done  → init_done"),
            ("init_done", "run_start", "init_done     → run_start"),
            ("run_start", "run_done", "run_start     → run_done"),
            ("run_done", "loading_removed", "run_done      → loading_off"),
        ]
        lines = ["[WebComPy Profile]"]
        total = 0.0
        for start_key, end_key, label in pairs:
            if start_key in data and end_key in data:
                elapsed = data[end_key] - data[start_key]
                total += elapsed
                lines.append(f"  {label}:  {elapsed:.3f}s")
        lines.append("  ─" * 16)
        lines.append(f"  Total:                          {total:.3f}s")
        output = "\n".join(lines)
        if platform.system() == "Emscripten":
            browser = _get_browser_module()
            browser.console.log(output)
        else:
            print(output)
```

## Bootstrap Integration

When `profile=True`, the generated `<script type="py">` includes an inline `perf_counter()` call at the very top. The value is passed to `WebComPyApp` via a keyword argument that exists only for internal use:

```python
# In generated HTML (profile mode)
<script type="py">
import time
_pyscript_ready = time.perf_counter()
# ... imports ...
app = WebComPyApp(..., profile=True)
app._profile_data["pyscript_ready"] = _pyscript_ready
app.run()
</script>
```

The `_profile_data["pyscript_ready"]` assignment happens before any other `_record_phase` calls. All subsequent timestamps are recorded relative to the same clock.

## Server / SSG Behavior

- `WebComPyApp(profile=True)` works identically on the server; `run()` raises as usual, but profile data can still be inspected via `app.profile_data` after initialization if desired.
- `_emit_profile_summary()` checks the environment and falls back to `print()` on the server.
- SSG HTML generation does **not** include the profiling bootstrap code even when `profile=True`, because the generated HTML is a production artifact. However, the `AppConfig.profile` value and `WebComPyApp` profile state are still valid.

## Output Example

```
[WebComPy Profile]
  pyscript_ready → imports_done:  0.234s
  imports_done  → init_done:     0.156s
  init_done     → run_start:     0.002s
  run_start     → run_done:      0.089s
  run_done      → loading_off:   0.001s
  ─────────────────────────────────
  Total:                          0.482s
```
