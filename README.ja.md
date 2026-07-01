# WebComPy

[![en](https://img.shields.io/badge/lang-en-red.svg)](README.md)
[![ja](https://img.shields.io/badge/lang-ja-green.svg)](README.ja.md)

## WebComPy とは

[WebComPy](https://github.com/kniwase/WebComPy) は [PyScript](https://github.com/pyscript/pyscript) のための Python フロントエンドフレームワークです。
リアクティブなコンポーネントモデルをブラウザ上で — すべて Python で — 実現します。

### 機能

- **コンポーネントベースの宣言的レンダリング** — `@define_component` で UI コンポーネントを純粋な Python 関数として定義
- **リアクティブな状態管理** — `Signal`、`Computed`、`ReactiveList`、`ReactiveDict` による自動 DOM 差分更新
- **ビルトインルーター** — History モード / Hash モード、パスパラメータ対応
- **依存性注入** — `provide()` / `inject()` パターンによるスコープ付きサービス管理
- **非同期レンダリングパイプライン** — `async` ライフサイクルフック、`AsyncResult`、コンポーザブルな非同期データ取得
- **HTTP クライアント** — ブラウザネイティブ fetch の async/await ラッパー
- **プラグインシステム** — `WebComPyPlugin` 基底クラスによる機能拡張
- **UI ツールキット** — テーマシステム（ライト/ダーク）、`CodeBlock` コンポーネント、CSS デザイントークン
- **テストモジュール** — `TestRenderer` とフェイクポートによるブラウザレスコンポーネントテスト — `webcompy-testing` が必要
- **インスペクタ CLI** — ヘッドレスブラウザでのスクリーンショット、コンソールログ、DOM クエリ、クリック、ナビゲーション
- **CLI ツール** — プロジェクトスキャフォールディング (`init`)、開発サーバー (`start`)、静的サイトジェネレーター (`generate`) — `webcompy-cli` が必要
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

    @define_component
    def Counter(context: ComponentContext[None]):
        count = Signal(0)

        def increment(ev):
            count.value += 1

        return html.DIV(
            {},
            html.P({}, "Count: ", count),
            html.BUTTON({"@click": increment}, "+1"),
        )

    app = WebComPyApp(root_component=Counter)
    app.run()
  </py-script>
</body>
</html>
```

任意の HTTP サーバーでファイルを配信し、ブラウザで開いてください。
マシンに Python のインストールは不要です — PyScript がブラウザ上で全てを実行します。

### CLI で開発する

```bash
pip install webcompy-cli
python -m webcompy init
python -m webcompy start --dev
python -m webcompy generate
```

### テスト

```bash
pip install webcompy-testing
```

## ドキュメントとデモ

- [webcompy.net](https://webcompy.net/)
    * [ソースコード](https://github.com/kniwase/WebComPy/tree/main/docs_app/)

## サンプルコード

```python
from webcompy.signal import Signal, computed
from webcompy.elements import html, repeat, switch, DOMEvent
from webcompy.router import RouterContext
from webcompy.components import (
    define_component,
    ComponentContext,
    on_before_rendering,
)


@define_component
def FizzbuzzList(context: ComponentContext[Signal[int]]):
    @computed
    def fizzbuzz():
        li: list[str] = []
        for n in range(1, context.props.value + 1):
            if n % 15 == 0:
                li.append("FizzBuzz")
            elif n % 5 == 0:
                li.append("Fizz")
            elif n % 3 == 0:
                li.append("Buzz")
            else:
                li.append(str(n))
        return li

    return html.DIV(
        {},
        html.UL(
            {},
            repeat(fizzbuzz, lambda s: html.LI({}, s)),
        ),
    )


FizzbuzzList.scoped_style = {
    "ul": {
        "border": "dashed 2px #668ad8",
        "background": "#f1f8ff",
        "padding": "0.5em 0.5em 0.5em 2em",
    },
    "ul > li:nth-child(3n)": {
        "color": "red",
    },
    "ul > li:nth-child(5n)": {
        "color": "blue",
    },
    "ul > li:nth-child(15n)": {
        "color": "purple",
    },
}


@define_component
def Fizzbuzz(context: ComponentContext[RouterContext]):
    opened = Signal(True)
    count = Signal(10)

    @computed
    def toggle_button_text():
        return "Hide" if opened.value else "Open"

    @on_before_rendering
    def reset_count():
        count.value = 10

    def add(ev: DOMEvent):
        count.value += 1

    def pop(ev: DOMEvent):
        if count.value > 0:
            count.value -= 1

    def toggle(ev: DOMEvent):
        opened.value = not opened.value

    return html.DIV(
        {},
        html.H3(
            {},
            "FizzBuzz",
        ),
        html.P(
            {},
            html.BUTTON(
                {"@click": toggle},
                toggle_button_text,
            ),
            html.BUTTON(
                {"@click": add},
                "Add",
            ),
            html.BUTTON(
                {"@click": pop},
                "Pop",
            ),
        ),
        html.P(
            {},
            "Count: ",
            count,
        ),
        switch(
            {
                "case": opened,
                "generator": lambda: FizzbuzzList(props=count),
            },
            default=lambda: html.H5(
                {},
                "FizzBuzz Hidden",
            ),
        ),
    )
```

## コントリビューション

開発ワークフロー、AI エージェントの使い方、PR プロセスについては [CONTRIBUTING.ja.md](CONTRIBUTING.ja.md) を参照してください。
コマンドや技術規約の詳細は [AGENTS.md](AGENTS.md)（英語）を参照してください。

## ライセンス

このプロジェクトは MIT ライセンスの下で提供されます。詳細は LICENSE.txt を参照してください。
