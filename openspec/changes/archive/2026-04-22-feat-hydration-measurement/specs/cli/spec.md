# CLI — Delta: feat-hydration-measurement

## Changes

### Added: Profiling bootstrap in generated HTML

When `AppConfig.profile=True`, the generated `<script type="py">` tag SHALL include inline profiling code:

```python
import time
_pyscript_ready = time.perf_counter()
from <app>.bootstrap import app
app._profile_data["pyscript_ready"] = _pyscript_ready
app.run()
```

When `profile=False` (default), no profiling code SHALL be included and the bootstrap SHALL remain unchanged.