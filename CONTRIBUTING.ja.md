# WebComPy コントリビューションガイド

## ようこそ

WebComPy は PyScript 上で動作する Python フロントエンドフレームワークです。
このプロジェクトでは AI エージェントを活用した開発を前提としています。
コントリビューター（人間・AI エージェントを問いません）は同じワークフローを通じて協業します。

**AI エージェントへ**: 技術的な詳細（コマンド、フレームワークの不変条件、ファイル→スペックマッピング、Git 規約）については [AGENTS.md](AGENTS.md)（英語）を参照してください。

---

## 開発環境のセットアップ

### 前提条件

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

### インストール

```bash
git clone https://github.com/kniwase/WebComPy.git
cd WebComPy
uv sync
```

このプロジェクトは [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/)
構成で、`packages/` 以下に4つのパッケージがあります:
- `packages/webcompy/` — コアブラウザランタイム（外部依存ゼロ）
- `packages/webcompy-server/` — サーバーサイドレンダリング
- `packages/webcompy-cli/` — CLIツール（開発サーバー、SSG、プロジェクト生成）
- `packages/webcompy-testing/` — テストユーティリティ

個別パッケージのwheelをビルドする場合（例: PyScript用）:

```bash
uv build --package webcompy
uv build --package webcompy-server
```

E2E テストに Playwright が必要な場合（任意）:

```bash
uv sync --group dev
uv run playwright install chromium
```

### クイックコマンド

```bash
uv run python -m webcompy start --dev --app docs_app.bootstrap:app     # 開発サーバー
uv run python -m webcompy generate --app docs_app.bootstrap:app         # 静的サイト生成
uv run ruff check .                                                   # リンター
uv run ruff format .                                                   # フォーマッター
uv run pyright                                                         # 型チェック
uv run python -m pytest tests/ --tb=short                             # ユニットテストのみ
scripts/run-e2e-tests.sh                                               # E2Eテスト (core + docs, prod + static)
```

コマンドの詳細は [AGENTS.md](AGENTS.md#commands-reference)（英語）を参照してください。

---

## 開発ワークフロー

WebComPy は [OpenSpec](https://github.com/fission-ai/openspec) によるスペック駆動開発を採用しています。
重要な変更は以下のライフサイクルに従います。

```
探索 → 提案 → 実装 → 仕様同期 → アーカイブ
```

### 探索（Explore）

問題の調査、アプローチの比較、要件の明確化を行います。

- [Discussions](https://github.com/kniwase/WebComPy/discussions) で質問する
- `openspec/specs/` 以下の既存スペックを確認する
- 関連する Issue や PR を確認する
- OpenCode 利用時は `/opsx-explore` を実行する

### 提案（Propose）

変更提案を作成し、設計・スペック・タスクを定義します。

1. **変更に名前をつける**: `<type>-<short-description>`（例: `feat-list-reconciliation`）。
   タイプは `feat`、`fix`、`refactor`、`docs`、`chore`、`test`、`perf` のいずれか。
2. **アーティファクトを作成する** OpenSpec スキルを使い `openspec/changes/<name>/` 以下に:
   - `openspec-new-change` で変更ディレクトリをスキャフォールド
   - `openspec-propose` で各アーティファクトを順に作成（または `openspec-ff-change`
     で全アーティファクトを一度に作成）
   - `proposal.md` — 動機、スコープ、非目標、既知の課題
   - `design.md` — 技術的アプローチと設計判断
   - `specs/` — 開発者視点での振る舞い定義
   - `tasks.md` — 実装タスク（各 2 時間以内）
3. **アーティファクトをコミットする** `git add` と `git commit` をコミットメッセージ規約
   （`<type>: <description>`）に従って実行。

### 実装（Apply Changes）

`openspec-apply-change` スキルを使って提案のタスクを実装します。

- `tasks.md` の順にタスクを進め、1 タスク 1 コミットを目安にする
- 全タスク完了で change の status が `complete` になる
- combined PR（プロポーザルと実装を 1 つの PR）の場合、Apply Changes は
  同じブランチで Sync Specs より前に行う
- プロポーザル単独 PR の場合、Apply Changes はプロポーザル PR マージ後に開始

### 仕様同期（Sync Specs）

実装 PR 提出前（change の status が `complete` の場合）に必ず実行:

1. `openspec-sync-specs` で delta specs を `openspec/changes/<name>/specs/` から
   メインスペック `openspec/specs/<capability>/spec.md` にマージ
2. `openspec/specs/` 配下の変更をコミットメッセージ規約に従ってコミット

プロポーザル単独 PR には適用されません（status は `in-progress` のまま）。

### アーカイブ（Archive）

実装 PR 提出前（change の status が `complete` の場合）に必ず実行:

1. `openspec-archive-change` で変更を `openspec/changes/<name>/` から
   `openspec/changes/archive/YYYY-MM-DD-<name>/` に移動
2. 移動をコミットメッセージ規約に従ってコミット

CI の `openspec-check` ジョブは `complete` な変更が未アーカイブだとマージを
ブロックするため、PR 提出前にこのステップを完了させる必要があります。

プロポーザル単独 PR には適用されません（status は `in-progress` のまま）。

PR 提出の mechanics については **プルリクエストプロセス** セクションを参照。

### スペック記述ガイドライン

- **開発者またはエンドユーザの視点**から書く（実装の視点ではない）
- `## Purpose` で目的と解決する問題を説明
- `## Requirements` に `### Requirement:` と `#### Scenario:` ブロックを
  `WHEN/THEN/AND` 形式で記述
- **観測可能な振る舞い**を記述（クラス階層やメソッドシグネチャではない）
- 内部リファクタリング（ユーザー視点の変更なし）はスペック変更不要

---

## AI エージェントの活用

### 利用可能なエージェント

| エージェント | 責務 |
|---|---|
| `ci-review` | OpenSpec スペックに基づく自動 PR レビュー |
| `ci-local` | ローカルでの lint / typecheck / ユニットテスト実行 |
| `browser-developer` | ブラウザサイドランタイム（reactive、elements、router、browser API） |
| `server-developer` | サーバーサイド（CLI、開発サーバー、SSG） |
| `component-developer` | UI コンポーネントと docs_app |
| `docs-developer` | docs_app のドキュメンテーションサイト |
| `browser-inspector` | `webcompy inspect` によるブラウザ検証 |

### タスク委譲（OpenCode）

```text
"リアクティブリストのリコンシリエーションを実装して"
→ @browser-developer

"CLI のヘルプテキストを更新して"
→ @server-developer

"プッシュ前に CI チェックを実行して"
→ @ci-local

"この差分をスペックに対してレビューして"
→ @ci-review
```

### AI エージェントとの言語について

- AI エージェントとのコミュニケーションは**日本語で問題ありません**
- AI エージェントは内部処理を英語で行いますが、日本語での指示を理解します
- コードや公式ドキュメントは英語です（AGENTS.md の言語ルールに従う）
- Issue や PR の記述言語は日本語でも英語でも構いません

### レビューの仕組み

すべての PR は CI 通過後、`ci-review` エージェントによってレビューされます。レビュアーは:

1. 変更ファイルをサブシステムごとに分類
2. 対応する OpenSpec スペックを参照
3. スペック違反、ロジックバグ、設計上の問題をチェック
4. 構造化されたレビューを PR に投稿

レビューの判定は `approved`（承認）または `changes_requested`（変更要求）です。
`changes_requested` の場合は対応するまでマージできません。

---

## 変更の作成

### ブランチ命名

```
<type>/<description>        # 例: feat/add-di-system, fix/reactive-update-order
```

### コミットメッセージ

```
<type>: <description>

🤖 Generated with opencode

Co-Authored-By: opencode <noreply@opencode.ai>
```

タイプ: `feat`、`fix`、`refactor`、`docs`、`chore`、`test`、`style`、`perf`

`Co-Authored-By` フッターはすべてのコミットで必須です。

### コード規約

- Python 3.12+、型アノテーション必須
- `uv` によるパッケージ管理（`uv add` + `uv lock`）
- コード内コメント禁止（明示的に要求された場合を除く）
- コンポーネントクラスは `@component_template`、`@on_before_rendering` を使用
- リアクティブ値は `Reactive`、`Computed`、`ReactiveList`、`ReactiveDict` で定義
重要な不変条件（デュアル環境アーキテクチャ、DI スコープルール、リアクティブ契約など）については
[AGENTS.md](AGENTS.md#framework-invariants)（英語）を参照してください。

### テスト

ユニットテストと E2E テストは物理的に別のディレクトリに配置され、異なる
コマンドで実行します:

- ユニットテスト: `uv run python -m pytest tests/ --tb=short`（`tests/` 配下のみ実行）
- E2E テスト: `scripts/run-e2e-tests.sh`（正規のエントリポイント。`WEBCOMPY_RUN_E2E=1` を自動設定）
- 単一グループの E2E: `scripts/run-e2e-tests.sh <group-name>`
- E2E テストを直接実行（`uv run pytest e2e/` など）すると、環境変数
  `WEBCOMPY_RUN_E2E=1` 未設定時は `pytest.UsageError` で失敗します。
- E2E テストファイルを追加したら `scripts/run-e2e-tests.sh` のグループ定義と
  `.github/workflows/ci.yml` の両方を更新してください。

---

## プルリクエストプロセス

### PR 提出（Submit）

- **テンプレート**: `.github/PULL_REQUEST_TEMPLATE.md`（すべての PR で唯一のテンプレート）
- **PR タイトルプレフィックス**で CI の挙動が変わる:
  - `chore:` — code check（lint、typecheck、test、E2E）をスキップ。CI は
    OpenSpec 検証と AI レビューのみ実行。プロポーザル単独 PR に適する。
  - `feat:`、`fix:`、`refactor:`、`docs:`、`chore:`、`test:`、`style:`、`perf:` —
    すべてのチェックを実行。実装 PR に適する。
- **PR の形**（プロポーザル単独か、実装と組み合わせるか）は PR 作成時点で判断:
  - 大規模または要議論な変更 → `chore:` で先行提案し、プロポーザル PR マージ後に
    実装 PR を出す
  - 小規模または自己完結的な変更 → プロポーザルと実装を 1 つの PR にまとめる
- **PR ライフサイクルのプロポーザル側**では、PR タイトルが `chore:` で始まる場合、
  コード変更がないため CI は OpenSpec バリデーションと AI レビューのみ実行し、
  lint/typecheck/test はスキップされる。

### プッシュ前の確認

1. **ローカル CI チェック** — `@ci-local` に委譲（lint、typecheck、ユニットテスト）
2. **コードレビュー** — `@ci-review` に委譲（スペック駆動の差分レビュー）

### PR のライフサイクル

1. `.github/PULL_REQUEST_TEMPLATE.md` を使って PR を開く
2. CI がバリデーションと code check を実行（`chore:` PR は code check をスキップ）
3. AI レビューが PR コメントとして結果を投稿
4. レビュー指摘に対応
5. すべてのチェックが通ったらマージ

### マージ条件

- 全 CI チェック通過
- AI レビュー承認（または指摘対応済み）
- 完了済みで未アーカイブの OpenSpec 変更がないこと（CI で確認）

---

## Issue の報告

[Issue テンプレート](.github/ISSUE_TEMPLATE/) を参照してください:

- **バグ報告**: バグ報告フォームを使用。環境（ブラウザ/サーバー）、バージョン、再現手順を明記してください。
  日本語での報告も歓迎します。
- **機能要望**: 機能要望フォームを使用。主要な機能は OpenSpec ワークフローを通じた提案を期待しています。

---

## ヘルプ

- [Discussions](https://github.com/kniwase/WebComPy/discussions) — 質問、アイデア、議論
- [Issues](https://github.com/kniwase/WebComPy/issues) — バグ報告と機能要望
- [WebComPy Docs](https://webcompy.net/) — フレームワークのドキュメントとデモ
