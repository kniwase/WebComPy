## Why

`ajax/`, `aio/`, `signal/`, `logging.py`, `components/_component.py` の5ファイルが `browser` オブジェクトを直接インポートしている。`feat-port-definitions` と `feat-port-migrate-elements` の完了により、残りの全消費者をポート注入に移行する。

## What Changes

- **MODIFIED** `ajax/_fetch.py`: `browser.pyscript.fetch` → `inject(FETCH_PORT_KEY)`
- **MODIFIED** `aio/_aio.py`: `browser` truthiness → `ENVIRONMENT == "pyscript"`
- **MODIFIED** `signal/_effect.py`: `browser.window.setTimeout` → `inject(DOM_PORT_KEY).schedule_macro_task`
- **MODIFIED** `logging.py`: `browser.console.log` → `pyscript.context.window.console.log`
- **MODIFIED** `components/_component.py`: `browser` truthiness → `ENVIRONMENT == "pyscript"`

## Capabilities

### Modified Capabilities

- `browser-api`: ajax、aio、signal、logging、components の各サブシステムがポート注入に移行

## Impact

- **Affected**: ajax (1), aio (1), signal (1), logging (1), components (1)
- **No breaking changes**: 移行は等価な置換のみ
