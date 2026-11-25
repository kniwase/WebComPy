# WebComPy

[![en](https://img.shields.io/badge/lang-en-red.svg)](README.md)
[![ja](https://img.shields.io/badge/lang-ja-green.svg)](README.ja.md)

## WebComPy とは

[WebComPy](https://github.com/kniwase/WebComPy) は [PyScript](https://github.com/pyscript/pyscript) 上で動作する Python フロントエンドフレームワークです。
リアクティブなコンポーネントモデルを、すべて Python だけでブラウザ上に実現します。

### 機能

- **コンポーネントベースの宣言的レンダリング** — `@define_component` で UI コンポーネントを純粋な Python 関数として定義
- **リアクティブな状態管理** — `Signal`、`Computed`、`ReactiveList`、`ReactiveDict` による自動 DOM 差分更新
- **ビルトインルーター** — History モード / Hash モード、パスパラメータ対応
- **依存性注入** — `provide()` / `inject()` パターンによるスコープ付きサービス管理
- **非同期レンダリングパイプライン** — `async` ライフサイクルフック、`AsyncResult`、コンポーザブルによる非同期データ取得
- **HTTP クライアント** — ブラウザネイティブ fetch の async/await ラッパー
- **プラグインシステム** — `WebComPyPlugin` 基底クラスによる機能拡張
- **UI ツールキット** — テーマシステム（ライト/ダーク）、`CodeBlock` コンポーネント、CSS デザイントークン
- **テストモジュール** — `TestRenderer` とフェイクポートによる、ブラウザを使わないコンポーネントテスト。`webcompy-testing` パッケージが必要
- **インスペクタ CLI** — ヘッドレスブラウザでのスクリーンショット、コンソールログ、DOM クエリ、クリック、ナビゲーション
- **CLI ツール** — プロジェクトのひな形生成（`init`）、開発サーバー（`start`）、静的サイト生成（`generate`）。`webcompy-cli` パッケージが必要
- **型アノテーション** — `.pyi` スタブによる完全な型ヒント

## はじめ方

### PyScript で使う

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <script
    type="module"
    src="https://pyscript.net/releases/2026.3.1/core.js">
  </script>
</head>
<body>
  <py-config>
    packages = ["webcompy"]
  </py-config>
  <py-script>
    from webcompy.signal import Signal
    from webcompy.elements import html
    from webcompy.app import WebComPyApp
    from webcompy.components import define_component, ComponentContext

    @define_component("counter-app")
    def CounterApp(context: ComponentContext[None]):
        count = Signal(0)

        def increment(ev):
            count.value += 1

        return html.DIV(
            {},
            html.P({}, "Count: ", count),
            html.BUTTON({"@click": increment}, "+1"),
        )

    app = WebComPyApp(root_component=CounterApp)
    app.run()
  </py-script>
</body>
</html>
```

任意の HTTP サーバーでファイルを配信し、ブラウザで開いてください。
手元の環境に Python をインストールする必要はありません。PyScript がブラウザ上ですべて実行します。

### CLI で開発する

**uv（推奨）**

```bash
uv init my-project && cd my-project
uv add webcompy-cli
uv run python -m webcompy init       # プロジェクト構成を作成
uv run python -m webcompy start --dev # 開発サーバー起動（ホットリロード）
uv run python -m webcompy generate   # 静的サイトを生成
```

**poetry**

```bash
poetry new my-project && cd my-project
poetry add webcompy-cli
poetry run python -m webcompy init   # プロジェクト構成を作成
poetry run python -m webcompy start --dev  # 開発サーバー起動（ホットリロード）
poetry run python -m webcompy generate     # 静的サイトを生成
```

**pip**

```bash
mkdir my-project && cd my-project
pip install webcompy-cli
python -m webcompy init              # プロジェクト構成を作成
python -m webcompy start --dev       # 開発サーバー起動（ホットリロード）
python -m webcompy generate          # 静的サイトを生成
```

### テスト

```bash
pip install webcompy-testing
```

## ドキュメントとデモ

- [webcompy.net](https://webcompy.net/)
    * [ドキュメント](https://webcompy.net/documents/)
    * [ライブサンプル](https://webcompy.net/documents/examples/todo)
    * [ソースコード](https://github.com/kniwase/WebComPy/tree/main/docs_app/)

## サンプルコード

```python
import uuid

from webcompy.app import WebComPyApp
from webcompy.components import ComponentContext, define_component
from webcompy.elements import DOMEvent, DomNodeRef, html, repeat
from webcompy.signal import Signal, use_computed, use_reactive_dict, use_state


@define_component()
def ToDoItem(context: ComponentContext[dict]):
    input_ref = DomNodeRef()

    def on_change_state(_: DOMEvent):
        context.props["done"].value = input_ref.checked

    return html.LI(
        {},
        html.LABEL(
            {},
            html.INPUT(
                {
                    "type": "checkbox",
                    "@change": on_change_state,
                    ":ref": input_ref,
                },
            ),
        ),
        " ",
        html.SPAN(
            {"style": use_computed(lambda: "text-decoration: line-through;" if context.props["done"].value else "")},
            context.props["title"],
        ),
    )


ToDoItem.scoped_style = {
    "li": {
        "color": "#2d8fdd",
        "border-left": "solid 6px #2d8fdd",
        "background": "#f1f8ff",
        "line-height": "1.5",
        "margin": "5px",
        "padding": "5px",
        "list-style-type": "none",
    }
}


@define_component()
def TodoApp(_: ComponentContext[None]):
    input_ref = DomNodeRef()
    data = use_reactive_dict(
        lambda: {
            str(uuid.uuid4()): {
                "title": use_state(lambda: "Try WebComPy"),
                "done": use_state(lambda: False),
            },
            str(uuid.uuid4()): {
                "title": use_state(lambda: "Create WebComPy project"),
                "done": use_state(lambda: False),
            },
        }
    )

    def append_item(_: DOMEvent):
        title = input_ref.value
        if title:
            data[str(uuid.uuid4())] = {
                "title": Signal(title),
                "done": Signal(False),
            }
        input_ref.value = ""

    def remove_done_items(_: DOMEvent):
        keys_to_remove = [k for k, v in data.value.items() if v["done"].value]
        for k in keys_to_remove:
            del data[k]

    return html.DIV(
        {},
        html.P(
            {},
            "Title: ",
            html.INPUT({":ref": input_ref}),
            html.BUTTON({"@click": append_item}, "Add ToDo"),
            html.BUTTON({"@click": remove_done_items}, "Remove Done Items"),
        ),
        html.UL(
            {},
            repeat(
                data,
                lambda v, k: ToDoItem(v),
            ),
        ),
    )


app = WebComPyApp(root_component=TodoApp)
```

## コントリビューション

開発ワークフロー、AI エージェントの使い方、PR プロセスについては [CONTRIBUTING.ja.md](CONTRIBUTING.ja.md) を参照してください。
コマンドや技術規約の詳細は [AGENTS.md](AGENTS.md)（英語）を参照してください。

## ライセンス

このプロジェクトは MIT ライセンスで公開されています。詳細は LICENSE.txt を参照してください。
