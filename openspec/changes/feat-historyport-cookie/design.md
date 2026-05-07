## Context

`Location` (`SignalBase[str]`) はリアクティブなパス状態と popstate リスナーを提供する。`HistoryPort` は ABC として同様の責務を持つ。両者は重複しており、統合する。

## Goals / Non-Goals

**Goals:**
- `Location` を削除し、全機能を `HistoryPort` に統合
- `Router` が `history: HistoryPort` をコンストラクタで受け取る
- `RouterView._on_set_parent` を HistoryPort 対応に更新
- `RouterLink` が `inject(HISTORY_PORT_KEY).navigate()` でナビゲーション
- `CookiePort` を DI スコープに提供
- `MockHistoryPort` (HistoryPort 継承) をテスト用に追加
- `_change_event_handler.py` を `_history_events.py` にリネーム（後方互換エイリアス `Location = HistoryPort` 付き）

**Non-Goals:**
- RouterMode や base_url の API 変更

## Decisions

### Decision 1: HistoryPort extends SignalBase[str]

`SignalBase[str]` を継承することで、`value` プロパティがリアクティブになる。`producer_accessed()` で依存関係を追跡し、`navigate()` で epoch/version/consumer 通知を行う。

### Decision 2: navigate() は Browser API で pushState せず、値更新のみ

`RouterLink._on_click` が `pushState` を呼び、`Router.__set_path__` が `HistoryPort.navigate()` を呼ぶ。`navigate()` は値の更新とリアクティブ通知のみを行い、二重 `pushState` を避ける。

### Decision 3: Router は history を必須の外部注入パラメータとして受け取る

旧コードでは Router が内部で Location を生成していた。新コードでは DI スコープ有効後に外部から注入する。

### Decision 4: Update RouterView._on_set_parent

RouterView SHALL use `HistoryPort`-aware logic. It injects `_ROUTER_KEY` to get the Router (which holds `HistoryPort` via constructor), and delegates route case evaluation through `router.__cases__` (a `computed_property` that reads from `router._history.value`). No direct `HistoryPort` injection needed in RouterView.

### Decision 5: Rename _change_event_handler.py

`webcompy/router/_change_event_handler.py` を `_history_events.py` にリネーム。Location コードを削除し、型エイリアス `type Location = HistoryPort` を残す（`Location()` でのインスタンス化は不可。参照は `BrowserHistoryPort`/`ServerHistoryPort` を使用）。

### Decision 6: MockHistoryPort for testing

`tests/conftest.py` に `MockHistoryPort` (HistoryPort 継承) を追加。DI スコープなしでテスト内で Router を構築可能にする。

### Decision 7: Public API exports

`webcompy/ports/__init__.py` で全 ABC、DOMNodeList、DI キーをエクスポート。`webcompy/router/__init__.py` から Location エクスポートを削除。

## Risks / Trade-offs

- [Risk] `Router(mode=...)` の既存呼び出しがすべて壊れる → Mitigation: 全呼び出し箇所を特定して修正
