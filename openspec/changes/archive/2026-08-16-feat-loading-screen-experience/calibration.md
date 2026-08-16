# Boot Phase Calibration

Measured 2026-08-16 against the pinned PyScript 2026.3.1 (Pyodide 0.29.3), e2e core app
(aiofiles dependency, CDN runtime, fast local network), via a throwaway Playwright script
recording `py:progress` events with `performance.now()` timestamps.

## Cold boot (fresh browser context)

| Event | Cumulative (s) | Delta (s) |
|---|---|---|
| (page parse → engine start) | 0.00 | 2.08 |
| `Loading Pyodide` | 2.08 | 0.00 |
| `Loading Packages Graph` → `Loaded` | 2.08 | 0.00 |
| `Loading Storage` → `Loaded` | 2.08 | 0.00 |
| `Loading interpreter` | 2.08 | 0.00 |
| `Loaded interpreter` | 3.70 | 1.62 |
| (micropip wheel install window) | — | 0.60 |
| `Loaded Pyodide` | 4.30 | 0.60 |
| `py:ready` | 4.30 | 0.00 |
| **Total boot (incl. 250ms fade)** | **5.34** | |

## Warm boot (same browser context, cached assets)

| Event | Cumulative (s) | Delta (s) |
|---|---|---|
| (parse → engine start) | 0.00 | 0.15 |
| `Loading interpreter` | 0.15 | 0.00 |
| `Loaded interpreter` | 1.61 | 1.46 |
| (micropip wheel install window) | — | 0.61 |
| `Loaded Pyodide` | 2.22 | 0.61 |
| `py:ready` | 2.22 | 0.00 |
| **Total boot (incl. 250ms fade)** | **3.27** | |

## Findings

- The **interpreter window** (`Loading interpreter` → `Loaded interpreter`, the
  `loadPyodide()` WASM download+instantiate) is the longest single measurable stage:
  1.5–1.6s here, and scales with network for the WASM payload. Stage ceilings should
  weight this phase the most.
- The **pre-event window** (page parse → `Loading Pyodide`, core.js module load + engine
  setup) is 2.08s cold / 0.15s warm — extremely variable (CDN download). It maps to
  `runtime_prepare`.
- **Packages** (micropip wheel install, `Loaded interpreter` → `Loaded Pyodide`) is
  ~0.6s here (single wheel URL; larger installs scale).
- **Storage/Packages Graph** phases are instant — correctly excluded from stage mapping.
- No micropip `console.log` lines surfaced as `py:progress` in this app (wheel URL
  packages install silently); sub-status remains a best-effort fallback.

## Adopted calibration

- Stage ceilings: `runtime_prepare: 35`, `runtime_download: 60`, `packages: 85`,
  `runtime_ready: 93`, `app_start: 97` (100 only on completion). Compromise between the
  cold profile (prepare ≈ 48% of boot) and warm profile (download ≈ 66%).
- `reveal_delay_ms` default 350ms: confirmed — cached sub-second boots rarely occur
  (warm boot here was 3.3s), so chrome legitimately shows; 350ms still suppresses
  flicker on very fast loads.
- `timeout_seconds` default 30: cold boot 5.3s on a fast link; slow links can take
  20-60s. 30s is an honest middle ground.
- Trickle time constant: `atan(elapsed / 6)` reaches ≈ 50% of the ceiling at ~6s,
  ≈ 90% at ~20s — never exceeds the ceiling without a stage event.
