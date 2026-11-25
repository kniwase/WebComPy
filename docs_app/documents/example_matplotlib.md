---
title: Matplotlib
description: Running WASM scientific libraries (NumPy and Matplotlib) inside an isolated PyScript iframe and rendering reactive base64 charts.
---

# Matplotlib

This example runs NumPy and Matplotlib directly inside the browser via PyScript WebAssembly wheels (`APP_PACKAGES.matplotlib_sample = ["numpy", "matplotlib"]`), recomputing a Fourier square wave and updating an inline PNG chart as you move the slider or press `+` and `-`.

Use isolated package manifests and WASM wheels whenever a specific page needs heavy scientific libraries without forcing every route in your application to download them up front.

## What this demonstrates

- **On-demand WASM package isolation**: The host docs shell avoids declaring `numpy` or `matplotlib` globally; instead, only the isolated `matplotlib_sample` iframe requests those CDN WASM wheels.
- **Reactive chart regeneration**: Inside `@use_computed def fig_data()`, reading `count.value` recomputes harmonic partial sums in NumPy, updates the Matplotlib `Line2D` series, renders PNG bytes into a `BytesIO` buffer, and returns a `data:image/png;base64,...` URI bound to `html.IMG({"src": fig_data})`.
- **Uncontrolled range slider synchronization**: Updating `count.value` updates the slider `value` attribute cleanly alongside manual button clicks (`+` / `-`).

## Key mechanisms and how to adapt

1. **Declare WASM packages in top-level apps via `pyproject.toml`**: In your own project, add `"numpy"` and `"matplotlib"` under `dependencies`, run `python -m webcompy lock` to classify them as `PackageKind.WASM`, and choose between CDN (`wasm_serving="cdn"`) or self-hosted offline delivery (`standalone=True`).
2. **Debounce expensive redraws if needed**: Keep expensive numerical redraws responsive on slider movement by binding `@change` (fires on release) rather than `@input` (fires on every pixel).
3. **Run heavy third-party packages selectively**: Keep heavy libraries out of your main shell's startup dependencies when only a single route needs them.

## Next steps

- Learn how `PackageKind.WASM`, `runtime_serving`, `wasm_serving`, and offline deployments work in [Serving Modes](/documents/server/serving-modes).
- Configure `pyproject.toml` dependencies and lockfiles in [Project Configuration](/documents/server/project-configuration).
- See lightweight static HTTP data loading next in [HTTP Fetch](/documents/examples/http-fetch).
