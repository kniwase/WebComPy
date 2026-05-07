## Why

全消費者がポート注入に移行したため、`browser` オブジェクトと `webcompy/_browser/` ディレクトリはもはや不要。削除してコードベースをクリーンにする。

## What Changes

- **REMOVED** `webcompy/_browser/_modules.py` — `browser` オブジェクト定義
- **REMOVED** `webcompy/_browser/__init__.py`
- **REMOVED** `webcompy/_browser/` ディレクトリ全体
- **REMOVED** `webcompy/__init__.py` 内の `browser` エクスポート
- **MODIFIED** `pyproject.toml`: `stubPath` を `_browser` から `ports` に変更

## Capabilities

### Modified Capabilities

- `browser-api`: `browser` オブジェクトと `_browser/` モジュールを削除。ブラウザAPIアクセスはポート注入のみに

## Impact

- **Breaking**: `browser` オブジェクトの削除 — 削除前に全消費者が移行済みであることが前提
- **Affected**: `webcompy/__init__.py`, `pyproject.toml`, `webcompy/_browser/` (削除)
