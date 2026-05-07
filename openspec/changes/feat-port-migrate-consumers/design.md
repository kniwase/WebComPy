## Context

`feat-port-migrate-elements` で要素システムの移行が完了し、残りの非要素系消費者（ajax, aio, signal/effect, logging, components）を同様にポート注入へ移行する。

## Goals / Non-Goals

**Goals:**
- ajax: `BrowserFetchPort` を `inject(FETCH_PORT_KEY)` で取得
- aio: `browser` → `ENVIRONMENT` ガードに置換
- signal/effect: `browser.window.setTimeout` → `inject(DOM_PORT_KEY).schedule_macro_task`
- logging: `browser.console.log` → `pyscript.context.window.console.log`
- components: `browser` truthiness → `ENVIRONMENT == "pyscript"`

**Non-Goals:**
- `browser` オブジェクトの削除

## Decisions

### Decision 1: logging はポート注入を使わず pyscript.context を直接使用

logging は軽量で環境に依存しない。`pyscript.context.window.console.log` を直接呼び出す。ポートを追加するほどの複雑さはない。

### Decision 2: ajax.fetch はポート注入を使用

FetchPort はブラウザとサーバーで実装が異なるため、DI 注入が適切。

## Risks / Trade-offs

- リスクなし — 純粋な置換のみ
