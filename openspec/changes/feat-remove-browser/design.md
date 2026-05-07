## Context

`browser` オブジェクトは `webcompy/_browser/_modules.py` で定義され、18の消費者ファイルからインポートされていた。事前のフェーズで全消費者がポート注入に移行済みのため、安全に削除できる。

## Goals / Non-Goals

**Goals:**
- `webcompy/_browser/` ディレクトリとその内容を削除
- `webcompy/__init__.py` から `browser` エクスポートを削除
- `pyproject.toml` の `stubPath` を更新

**Non-Goals:**
- `webcompy/_browser/_modules.pyi` の移行（不要 — ポートが型チェックを提供）

## Decisions

### Decision 1: _browser/ 全体を削除

旧バージョンの `browser` オブジェクトの痕跡は残さない。WebComPy は不安定リリースのため、非推奨期間なしで削除。

## Risks / Trade-offs

- [Risk] 移行し忘れた消費者が存在する → Mitigation: E2E テストで検出
