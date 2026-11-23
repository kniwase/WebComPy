# WebComPy コントリビューションガイド

## はじめに

WebComPy は PyScript 上で動作する Python フロントエンドフレームワークです。
このプロジェクトでは AI エージェントを活用した開発を前提としています。
人間・AI エージェントを問わず、すべてのコントリビューターが同じワークフローで協業します。

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
- 関連する Discussion や PR を確認する
- `/opsx-explore`（OpenCode / Claude Code）または `/openspec-explore`（Antigravity / Claude Code）を実行する

### 提案（Propose）

変更提案を作成し、設計・スペック・タスクを定義します。

1. **変更に名前を付ける**: `<type>-<short-description>` 形式（例: `feat-list-reconciliation`）。
   タイプは `feat`、`fix`、`refactor`、`docs`、`chore`、`test`、`perf` のいずれかを使用します。
2. **アーティファクトを作成する**: OpenSpec スキルを使って `openspec/changes/<name>/` 配下に各ファイルを作成します。
   - `openspec-new-change` で変更用ディレクトリのひな形を作成
   - `openspec-propose` で各アーティファクトを順に作成（または `openspec-ff-change` で一括作成）
   - `proposal.md` — 背景・動機、スコープ、対象外（Non-goals）、既知の課題
   - `design.md` — 技術的アプローチと設計判断
   - `specs/` — 開発者視点での振る舞い定義
   - `tasks.md` — 実装タスク（各 2 時間以内の粒度）
3. **アーティファクトをコミットする**: コミットメッセージ規約（`<type>: <description>`）に従い、`git add` と `git commit` を実行します。

### 実装（Apply Changes）

`openspec-apply-change` スキルを使って提案のタスクを実装します。

- `tasks.md` の順にタスクを進め、1 タスク 1 コミットを目安にします
- すべてのタスクが完了すると、変更のステータスが `complete` になります
- プロポーザルと実装を 1 つの PR にまとめる場合、同じブランチ上で「仕様同期」より前に実装を行います
- プロポーザル単独 PR の場合、プロポーザル PR がマージされてから実装を開始します

### 仕様同期（Sync Specs）

実装 PR を提出する前（変更のステータスが `complete` になった後）に必ず実行します:

1. `openspec-sync-specs` で差分スペック（delta specs）を `openspec/changes/<name>/specs/` から
   メインスペック `openspec/specs/<capability>/spec.md` にマージします
2. `openspec/specs/` 配下の変更をコミットメッセージ規約に従ってコミットします

プロポーザル単独 PR では不要です（ステータスは `in-progress` のままにします）。

### アーカイブ（Archive）

実装 PR を提出する前（変更のステータスが `complete` になった後）に必ず実行します:

1. `openspec-archive-change` で変更ディレクトリを `openspec/changes/<name>/` から
   `openspec/changes/archive/YYYY-MM-DD-<name>/` に移動します
2. 移動をコミットメッセージ規約に従ってコミットします

完了済み（`complete`）の変更がアーカイブされていない場合、CI の `openspec-check` ジョブによってマージがブロックされます。PR 提出前に必ずアーカイブを完了してください。

プロポーザル単独 PR では不要です（ステータスは `in-progress` のままにします）。

PR 提出の具体的な手順については、**プルリクエストプロセス** セクションを参照してください。

### スペック記述ガイドライン

- **開発者またはエンドユーザーの視点**から記述します（内部実装の詳細ではなく利用側の視点）
- `## Purpose` で目的と解決する課題を説明します
- `## Requirements` に `### Requirement:` と `#### Scenario:` ブロックを `WHEN/THEN/AND` 形式で記述します
- クラス階層やメソッドシグネチャではなく、**外から観測できる振る舞い**を記述します
- ユーザー視点の挙動が変わらない内部リファクタリングでは、スペックの変更は不要です

---

## AI エージェントの活用

再利用可能なドメイン知識は `.agents/skills/`、スラッシュコマンドは `.agents/commands/` を唯一の正本（SSOT）として管理しています。権限サンドボックスが必要な場面向けに 2 つの薄いラッパーエージェント（`webcompy-reviewer`、`webcompy-inspector`）を用意していますが、サンドボックスが不要な場合はスキルを直接読み込んでください。

### 対応コーディングハーネス

| ハーネス | プロジェクトルール | スキル検出 | スラッシュコマンド | サンドボックス付きエージェント |
|---|---|---|---|---|
| **OpenCode** | `AGENTS.md` | `.agents/skills/`（ネイティブ） | `.opencode/commands/` → `.agents/commands/`（`/opsx-*`） | `.opencode/agents/*.md`（CI でも使用） |
| **Antigravity** | `AGENTS.md` | `.agents/skills/`（ネイティブ） | `/<skill-name>`（例: `/openspec-propose`、`/webcompy-review`） | 組み込みサブエージェント + スキル |
| **Claude Code** | `CLAUDE.md` → `AGENTS.md` | `.claude/skills/` → `.agents/skills/` | `.claude/commands/` → `.agents/commands/`（`/opsx-*`、`/<skill-name>`） | `.claude/agents/*.md` |
| **Codex CLI / Cursor / Gemini CLI** | `AGENTS.md` | `.agents/skills/`（ネイティブ） | 各ハーネス標準またはスキル呼び出し | 各ハーネス固有 |

### 利用可能なスキルとエージェント

スキル（対応ハーネスが `description` に応じて自動で読み込みます。直接呼び出すことも可能です）:

| スキル | 用途 |
|---|---|
| `webcompy-review` | WebComPy 変更のスペック駆動コードレビュー |
| `webcompy-inspect` | `webcompy inspect` CLI によるブラウザ検証 |
| `webcompy-browser-development` | ブラウザサイドランタイム（reactive、elements、router、browser API） |
| `webcompy-server-development` | サーバーサイド（CLI、開発サーバー、SSG） |
| `webcompy-component-development` | UI コンポーネントと docs_app |
| `webcompy-docs-development` | docs_app のドキュメントサイト |
| `webcompy-local-ci` | ローカルでの lint / typecheck / ユニットテスト実行 |

エージェント（権限サンドボックス付き、対応スキルをロード）:

| エージェント | 責務 |
|---|---|
| `webcompy-reviewer` | OpenSpec スペックに基づく PR レビュー（CI は OpenCode で実行、ローカルの Claude Code は `.claude/agents/` を利用） |
| `webcompy-inspector` | `webcompy inspect` によるブラウザ検証（サブエージェント専用） |

### タスク委譲の例

```text
"リアクティブリストのリコンシリエーションを実装して"
→ webcompy-browser-development スキル

"CLI のヘルプテキストを更新して"
→ webcompy-server-development スキル

"プッシュ前に CI チェックを実行して"
→ webcompy-local-ci スキル

"この差分をスペックに対してレビューして"
→ webcompy-review スキル（サンドボックス付きで呼び出すなら webcompy-reviewer サブエージェント）
```

### AI エージェントとの言語について

- AI エージェントとのコミュニケーションは**日本語で問題ありません**
- AI エージェントは内部処理を英語で行いますが、日本語での指示を理解します
- コードや公式ドキュメントは英語です（AGENTS.md の言語ルールに従う）
- Discussions への投稿は英語・日本語のどちらでも構いません（PR のタイトル・本文は英語で記述します）

### レビューの仕組み

すべての PR は CI 通過後、CI 上の OpenCode `webcompy-reviewer` エージェントによってレビューされます。レビュアーは:

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

Co-Authored-By: <harness-name> <noreply@...>
```

タイプ: `feat`、`fix`、`refactor`、`docs`、`chore`、`test`、`style`、`perf`

AI アシストによるコミットでは、使用したコーディングハーネスの標準 `Co-Authored-By:` フッター（例: `opencode <noreply@opencode.ai>`、`Claude <noreply@anthropic.com>`、`Antigravity <noreply@google.com>`）を付与してください。人間のみのコミットでは省略可能です。

### コード規約

- Python 3.12+、型アノテーション必須
- `uv` によるパッケージ管理（`uv add` + `uv lock`）
- コード内コメント禁止（明示的に指示された場合を除く）
- コンポーネントクラスは `@component_template`、`@on_before_rendering` を使用
- リアクティブ状態のプリミティブは `openspec/specs/reactive/spec.md` と `openspec/specs/composables/spec.md` で規定

重要な不変条件（デュアル環境アーキテクチャ、DI スコープルール、リアクティブ契約など）については
[openspec/SPEC_INDEX.md](openspec/SPEC_INDEX.md#framework-invariants)（英語）を参照してください。

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

- **テンプレート**: `.github/PULL_REQUEST_TEMPLATE.md`（すべての PR で共通）
- **PR タイトルと本文の言語**: `AGENTS.md` の Language Rules に従い、PR のタイトルと本文（Description、Related Resources、チェックリストの説明など）は **必ず英語で** 作成してください。AI エージェントが PR を下書きする場合も、チャット上の使用言語にかかわらず英語で出力します。
- **PR タイトルのプレフィックス**によって CI の挙動が変わります:
  - `chore:` — コードチェック（lint、typecheck、test、E2E）をスキップし、CI は OpenSpec 検証と AI レビューのみを実行します。プロポーザル単独 PR に適しています。
  - `feat:`、`fix:`、`refactor:`、`docs:`、`chore:`、`test:`、`style:`、`perf:` — すべてのチェックを実行します。実装 PR に適しています。
- **PR の構成**（プロポーザル単独にするか、実装とまとめるか）は PR 作成時に判断します:
  - 大規模または議論が必要な変更 → `chore:` で先にプロポーザル PR を出し、マージ後に実装 PR を作成します
  - 小規模または単体で完結する変更 → プロポーザルと実装を 1 つの PR にまとめます
- **プロポーザル単独 PR の CI 挙動**: PR タイトルが `chore:` で始まりコード変更を含まない場合、lint・typecheck・test はスキップされ、OpenSpec 検証と AI レビューのみが実行されます。

### プッシュ前の確認

1. **ローカル CI チェック** — `webcompy-local-ci` スキルを使用（lint、typecheck、ユニットテスト）
2. **コードレビュー** — `webcompy-review` スキルを使用（サンドボックス付きで呼び出す場合は `webcompy-reviewer` エージェント）

### PR のライフサイクル

1. `.github/PULL_REQUEST_TEMPLATE.md` を使って PR を作成します
2. CI がバリデーションとコードチェックを実行します（`chore:` PR はコードチェックをスキップ）
3. AI レビューが PR コメントとして結果を投稿します
4. レビュー指摘に対応します
5. すべてのチェックが通ったらマージします

### マージ条件

- すべての CI チェックを通過していること
- AI レビューによる承認を得ていること（または指摘への対応が完了していること）
- 完了済みで未アーカイブの OpenSpec 変更が残っていないこと（CI で確認）

---

## バグ報告・機能要望・質問

このリポジトリでは GitHub Issues を無効化しています。バグ報告・機能要望・質問は
[GitHub Discussions](https://github.com/kniwase/WebComPy/discussions)
をご利用ください（投稿言語は英語・日本語のどちらでも構いません。テンプレート定義は
[.github/DISCUSSION_TEMPLATE/](.github/DISCUSSION_TEMPLATE/) にあります）。

- **バグ報告**（[`Bug Reports`](https://github.com/kniwase/WebComPy/discussions/new?category=bug-reports)）:
  環境（ブラウザ／サーバー）、バージョン、再現手順を明記してください。
- **機能要望・アイデア**（[`Ideas`](https://github.com/kniwase/WebComPy/discussions/new?category=ideas)）:
  解決したい課題と提案内容を記載してください。大きな機能追加は OpenSpec ワークフローに沿って進めます。
- **質問**（[`Q&A`](https://github.com/kniwase/WebComPy/discussions/new?category=q-a)）:
  使い方や環境構築、設計に関する質問を投稿してください。

---

## ヘルプ

- [Discussions](https://github.com/kniwase/WebComPy/discussions) — バグ報告、機能要望・アイデア、Q&A、お知らせ、事例紹介
- [WebComPy Docs](https://webcompy.net/) — フレームワークのドキュメントとデモ
