This change introduces no new or modified capabilities at the spec level.

All changes are implementation optimizations and application configuration updates that operate entirely within existing capabilities:

- `docs_app/router.py` — configuration change (using `lazy()` for the `/` route)
- `webcompy/router/_router.py` — implementation optimization (batching `setTimeout` calls in `preload_lazy_routes()`)

Neither change alters any observable framework behavior defined in existing specs.
