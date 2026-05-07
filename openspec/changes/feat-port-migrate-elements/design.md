## Context

`webcompy/elements/` の6ファイルで `browser` オブジェクトがインポートされ、DOM操作とイベントプロキシに使われている。`feat-port-definitions` で DOMPort、FFIPort が定義・実装済み。これらを DI 注入に切り替える。

## Goals / Non-Goals

**Goals:**
- `browser.pyscript.ffi.create_proxy(event_handler)` → `inject(FFI_PORT_KEY).create_proxy(event_handler)` （`ENVIRONMENT` ガード付き）
- `browser.document.createElement(tag)` → `inject(DOM_PORT_KEY).create_element(tag)`
- `browser.document.createTextNode(text)` → `inject(DOM_PORT_KEY).create_text_node(text)`
- `browser.window.setTimeout(cb, 0)` → `inject(DOM_PORT_KEY).schedule_macro_task(cb)`
- `if browser:` → `if ENVIRONMENT == "pyscript":`（等価な環境ガード）
- `browser is not None` → `ENVIRONMENT == "pyscript"`（等価な環境ガード）
- `not browser:` → `ENVIRONMENT != "pyscript":`（等価な環境ガード）

**Non-Goals:**
- `browser` オブジェクトの削除（後のフェーズ）
- 他のパッケージの移行（次のフェーズ）
- `Router` API の変更（後のフェーズ）

## Decisions

### Decision 1: ENVIRONMENT ガードを browser ガードと完全等価に保つ

`browser` は PyScript 環境で truthy、それ以外で falsy。`ENVIRONMENT == "pyscript"` と完全に等価なため、単純置換で十分。

### Decision 2: イベントハンドラは `_generate_event_handler` 内でのみ FFI プロキシを作成

`_generate_event_handler` はすでに `if browser:` ガードを持っている。これを `if ENVIRONMENT == "pyscript": inject(FFI_PORT_KEY).create_proxy(event_handler)` に置き換える。

## Risks / Trade-offs

- [Risk] サーバー側の `else: raise WebComPyException` パスが消える → Mitigation: サーバー側では `ENVIRONMENT != "pyscript"` のコードパスが別途存在し、DOM操作は実行されない
