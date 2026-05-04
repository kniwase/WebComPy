## Context

WebComPy's SSG pipeline builds a single app wheel containing webcompy (minus `cli/`), the application package, and any bundled pure-Python dependencies not available on the Pyodide CDN. The wheel discovery logic (`_discover_packages`) currently only detects directories containing `__init__.py` — single-file modules like `six.py` are invisible to it. This silently omits them from the wheel.

On the router side, lazy route preloading was tied to `RouterView._on_set_parent()`, which fires during component init. This predates `DynamicElement` being used for `RouterView` and was the only lifecycle hook available. In the browser, `setTimeout(0)` schedules the preload — when Pyodide is cached (2nd+ access), this fires before `dateutil.parser` and its dependency `six` are loadable, causing a crash.

### Current Flow (broken)
```
app.__init__()
  → AppDocumentRoot.__init__()
    → RouterView.__init__()
      → RouterView._on_set_parent()
        → preload_lazy_routes()
          → setTimeout(_do_preload, 0)
            → LazyComponentGenerator._preload()
              → import docs_app.pages.demo.matplotlib_sample
                → template imports matplotlib.pyplot
                  → matplotlib.category imports dateutil.parser
                    → six import → 💥 ModuleNotFoundError
```

## Goals / Non-Goals

**Goals:**
- Bundle single-file `.py` modules (no `__init__.py`) alongside package-directory modules in the app wheel.
- Defer browser-side lazy route preloading until after `app.run()` and the initial render complete.
- Isolate preload failures so one failing lazy route does not crash the application.

**Non-Goals:**
- Change the public API surface.
- Modify Pyodide package declaration or lockfile format.
- Add new test infrastructure.

## Decisions

### Decision 1: Detect single-file modules in `_discover_packages()` and handle them in `_collect_package_files()`

**Rationale:** The extraction step (`extract_wheel`) correctly returns `(pkg_name, dest)` entries for both directory packages and single-file modules. The gap is only in wheel assembly — `_discover_packages` needs to recognize single `.py` files at the package root level, and `_collect_package_files` needs to include them as top-level wheel entries (`{module_name}.py` rather than `{module_name}/{module_name}.py`).

A bundled dependency directory may contain both a same-named `.py` file and subdirectory entries (e.g. an extracted wheel with `six.py` plus `six-1.17.0.dist-info/` alongside it). Discovery must distinguish the module file from the dist-info artifacts. The guard `(pkg_dir / f"{pkg_name}.py").is_file()` ensures only actual Python modules are treated as single-file.

**Alternatives considered:**
- Separate collection pass for single-file modules: More code duplication; rejected.
- Require all transitive deps to be directory packages: Unrealistic constraint; rejected.

### Decision 2: Schedule preload in `AppDocumentRoot._render()` after loading-screen removal

**Rationale:** At this point, `app.run()` has completed, the DOM is rendered, and the loading spinner is removed. Pyodide's package initialization has had enough time even in the cached (fast) case. This is also the point where `AppDocumentRoot` already performs post-render cleanup — adding preload here keeps the lifecycle cohesive. The existing `__loading` guard ensures preload fires only once, on the first render cycle.

**Alternatives considered:**
- Wait for Pyodide `loadPackage` completion explicitly: Would require PyScript/Pyodide internal APIs; fragile and not portable across PyScript versions.
- Increase timeout: Papering over a race, not fixing it.

### Decision 3: Contextlib.suppress + `_resolve_error` flag for error isolation

**Rationale:** `contextlib.suppress(Exception)` is Pythonic and lint-friendly (ruff SIM105). The `_resolve_error` flag on `LazyComponentGenerator` provides observability without runtime cost. When the user actually navigates to the lazy route later, `_resolve()` is re-invoked cleanly (the flag is informational only).

**Alternatives considered:**
- `console.warn` in the error handler: Adds browser-specific logging to framework code; could be a follow-up if needed.
- Retry loop: Adds complexity without clear benefit — if a module fails once due to missing dependency, retrying immediately won't help.

## Risks / Trade-offs

- **Risk:** Non-directory extracted CDN packages that aren't `.py` single-file modules. → **Mitigation:** The `elif (pkg / f"{name}.py").is_file()` guard ensures only actual Python modules are treated as single-file.
- **Risk:** Deferred preload might cause a slight delay when the user navigates to a lazy route immediately after initial render. → **Mitigation:** The preload still fires via `setTimeout(0)` — it just starts slightly later, well within the typical idle period after page load.
- **Risk:** `_resolve_error` flag is never consumed by application code. → **Mitigation:** Acceptable as a debug hook; can be exposed via console diagnostics in a future iteration.
