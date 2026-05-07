## Context

`Location` (`SignalBase[str]`) はリアクティブなパス状態と popstate リスナーを提供する。`HistoryPort` は ABC として同様の責務を持つ。両者は重複しており、統合する。

## Goals / Non-Goals

**Goals:**
- `Location` を削除し、全機能を `HistoryPort` に統合
- `Router` が `history: HistoryPort` をコンストラクタで受け取る
- `RouterLink` が `inject(HISTORY_PORT_KEY).navigate()` でナビゲーション
- `CookiePort` を DI スコープに提供

**Non-Goals:**
- RouterMode や base_url の API 変更

## Decisions

### Decision 1: HistoryPort extends SignalBase[str]

`SignalBase[str]` を継承することで、`value` プロパティがリアクティブになる。`producer_accessed()` で依存関係を追跡し、`navigate()` で epoch/version/consumer 通知を行う。

### Decision 2: navigate() は Browser API で pushState せず、値更新のみ

`RouterLink._on_click` が `pushState` を呼び、`Router.__set_path__` が `HistoryPort.navigate()` を呼ぶ。`navigate()` は値の更新とリアクティブ通知のみを行い、二重 `pushState` を避ける。

### Decision 3: Router は history を必須の外部注入パラメータとして受け取る

旧コードでは Router が内部で Location を生成していた。新コードでは DI スコープ有効後に外部から注入する。

## Risks / Trade-offs

- [Risk] `Router(mode=...)` の既存呼び出しがすべて壊れる → Mitigation: 全呼び出し箇所を特定して修正
