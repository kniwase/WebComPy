## Why

`Location` と `HistoryPort` は責務が重複している（どちらもリアクティブなパス状態 + ナビゲーション操作）。`Location` を `HistoryPort` に統合し、`Router` が `HistoryPort` を外部から受け取るようにする。また `CookiePort` のブラウザ/サーバー実装を追加する。

## What Changes

- **REMOVED** `Location` クラス — 全機能が `HistoryPort` に統合される
- **MODIFIED** `Router`: `location: Location` → `history: HistoryPort` をコンストラクタで受け取る。**BREAKING**
- **MODIFIED** `RouterLink._on_click`: `inject(HISTORY_PORT_KEY).navigate()` を使用
- **MODIFIED** `WebComPyApp`: `CookiePort` も DI スコープに提供
- **REMOVED** `webcompy/router/_browser_history.py`, `_server_history.py`, `_history_port.py` (古い HistoryPort 定義)
- **NEW** `BrowserCookiePort`, `ServerCookiePort` （すでに feat-port-definitions で追加済みのため、本フェーズでは提供のみ）

## Capabilities

### Modified Capabilities

- `router`: Router が Location の代わりに HistoryPort を受け取る。API 破壊的変更
- `browser-api`: Location クラスを削除、HistoryPort に統合

## Impact

- **Breaking**: `Router(...)` の呼び出し側をすべて更新する必要がある
- **Breaking**: `Location` の全参照を `HistoryPort` に置き換え
- **Affected**: router/ (4ファイル), app/_app.py, E2E テストアプリ
