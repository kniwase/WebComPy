## Context

`WebComPyApp.__init__` は現在 `app.di_scope` を作成し `ComponentStore` を提供する。ポートのブラウザ/サーバー実装は `feat-port-definitions` で追加済み。アプリ初期化時にそれらを DI スコープに提供する。

## Goals / Non-Goals

**Goals:**
- PyScript 環境で `BrowserDOMPort`, `BrowserFFIPort`, `BrowserFetchPort`, `BrowserHistoryPort` を提供
- サーバー環境で `ServerDOMPort`, `ServerFFIPort`, `ServerFetchPort`, `ServerHistoryPort` を提供

**Non-Goals:**
- 既存の `browser` インポートの削除（次のフェーズ）
- Router API の変更（次のフェーズ）

## Decisions

### Decision 1: ポート提供は `_register_deferred_components()` の後、`AppDocumentRoot` 構築の前

`_register_deferred_components()` は DI スコープが必要なため先に実行し、その後にポートを提供する。ポートは `AppDocumentRoot` のレンダリング前に利用可能になる。

## Risks / Trade-offs

- リスクなし — ポートはまだどのコンポーネントからも要求されていない。追加のみ
