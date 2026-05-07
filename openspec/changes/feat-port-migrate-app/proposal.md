## Why

ポート実装が存在し全消費者が `inject(PORT_KEY)` を使用できるようになった。`WebComPyApp.__init__` で DI スコープにポートを提供し、アプリ起動時に全ポートが利用可能になるようにする。

## What Changes

- **MODIFIED** `webcompy/app/_app.py`: `__init__` 内の `_register_deferred_components()` 呼び出し後に、環境に応じて5つのポート実装を `self._di_scope.provide()` で注入

## Capabilities

### Modified Capabilities

- `app-config`: `WebComPyApp` のブートストラップが環境に応じたポートを DI スコープに提供する

## Impact

- **Affected**: `webcompy/app/_app.py` のみ
- **No breaking changes**: 既存の全テストが変更なしでパス。ポートはすでに利用可能であり、アプリが提供を開始するだけ
