## Why

`webcompy/elements/` の6ファイルは `browser` オブジェクトから DOM 操作とイベントプロキシを取得しています。`feat-port-definitions` でポートが利用可能になったため、要素システムのみをポート注入に移行します。`browser` ガードは等価な `ENVIRONMENT == "pyscript"` ガードに置き換え、サーバーコードパスは維持します。

## What Changes

- **MODIFIED** `_element.py`: `browser` → `inject(FFI_PORT_KEY)` と `inject(DOM_PORT_KEY)`。`if browser:` → `if ENVIRONMENT == "pyscript":`
- **MODIFIED** `_text.py`: `browser` → `inject(DOM_PORT_KEY)`
- **MODIFIED** `_abstract.py`: `browser` → `inject(DOM_PORT_KEY)`
- **MODIFIED** `_switch.py`: `browser.window.setTimeout` → `inject(DOM_PORT_KEY).schedule_macro_task`
- **MODIFIED** `_dynamic.py`: `if browser:` → `if ENVIRONMENT == "pyscript:`
- **MODIFIED** `_repeat.py`: `if browser/not browser` → `ENVIRONMENT` check

## Capabilities

### Modified Capabilities

- `browser-api`: 6つの要素ファイルがポート注入に移行。`inject(DOM_PORT_KEY)`/`inject(FFI_PORT_KEY)` 経由でのみブラウザAPIにアクセス。`browser` インポートは残るがガードのみに使用。

## Impact

- **Affected**: `webcompy/elements/types/` 内の 6 ファイル
- **No breaking changes**: 既存の全テストが変更なしでパス
- **Dependencies**: `feat-port-definitions` が先に実装されていること
