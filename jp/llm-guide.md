# LLM を使った読み方: llms.txt と MCP

> **最終更新日**: 2026 年 10 月 16 日

このガイドブックは、[提案されている llms.txt 形式](https://llmstxt.org/)とドキュメントごとの Markdown を提供します。URL を取得できる AI ツールにインデックスを渡す、カタログとソーステキストを LLM Wiki または RAG パイプラインに取り込む、検索／取得ツールをローカル MCP クライアントに接続するといった使い方ができます。`llms.txt` を公開しただけで、すべての AI が自動的に発見または検索できるようになるとは限りません。利用するツールには Web 取得機能または MCP 接続が必要です。

## エンドポイント

| URL | 内容 | 用途 |
|-----|----------|-----------|
| [llms.txt](https://www.atomai.click/kubernetes-docs/llms.txt) | 各コンテンツページのグループ、タイトル、要約、生の Markdown URL を含むインデックス。クイズとラボは `## Optional` 内のインデックスリンクとして掲載 | LLM が必要なページだけを選択して取得する |
| [ドキュメントマニフェスト](https://www.atomai.click/kubernetes-docs/llms/manifest.json) | ドキュメント ID、言語、セクション、タイトル、見出し、説明、Web/Markdown URL、更新日、SHA-256、UTF-8 のバイト数 | LLM Wiki または RAG で選択的に取り込み、変更を検知する |
| [llms-full-ko.txt](https://www.atomai.click/kubernetes-docs/llms-full-ko.txt) | 韓国語の全文（Markdown） | 書籍全体をコンテキストに使う、または RAG のインデックスを作成する |
| [llms-full-en.txt](https://www.atomai.click/kubernetes-docs/llms-full-en.txt) | 英語の全文（Markdown） | 英語のツールやパイプラインで利用する |
| `llms-full-<locale>-<section>.txt`（例: [llms-full-en-networking.txt](https://www.atomai.click/kubernetes-docs/llms-full-en-networking.txt)） | サイドバーの 1 セクションのコンテンツを結合したファイル。完全な一覧は `llms.txt` の `## Section bundles` にある | 単一セクションをコンテキストとして読み込む。全文ファイルは 1 つのプロンプトには大きすぎる |

これらのファイルとドキュメントごとの Markdown ページは、サイトビルド時に同じソースから生成され、デプロイが成功した場合は互いに一致します。ローカルの変更や、まだデプロイされていない main ブランチの変更は、すぐには公開されません。`llms.txt` のコンテンツリンクは `/llms/<locale>/<source path>.md` を使い、VitePress の HTML、サイドバー、スクリプトを含まない、そのドキュメントの Markdown だけを返します。ソースの相対リンクは絶対 URL に書き換えられます（対象範囲内のコンテンツリンクは Markdown、クイズ／ラボ／言語ルートへのリンクはレンダリング済みページ、画像／アセットは raw GitHub ファイルを指します）。そのため、モデルが 1 つのドキュメントを取得すると、すべての参照先をたどれます。Markdown 版がある各 HTML コンテンツページは、`<head>` に同じ Markdown URL を `<link rel="alternate" type="text/markdown">` として含みます。これにより、Web ページの URL を渡された Agent も Markdown のソースを見つけられます。クイズは `## Optional` 内のクイズインデックスページへのリンク（各言語 1 つ）としてのみ掲載されます。個々のクイズページと解答はインデックスにも全文ファイルにも含まれません。解答は LLM のコンテキストに含めるものではありません。ラボガイドも `llms.txt` にはラボインデックスへのリンク（各言語 1 つ）だけが掲載されますが、全文ファイルには本文が含まれます。

## ソースを LLM Wiki に取り込む

ここでいう LLM Wiki とは、ソース資料を保持し、AI がトピックごとのナレッジページに整理する仕組みです。このサイトはソースドキュメントとメタデータを提供します。Wiki や埋め込みデータの作成と更新は、取り込みツール側で行います。

1. `llms/manifest.json` を読み込み、`locale` と `section` で絞り込みます。同じトピックを重複して取り込まないよう、1 つの言語を選びます。
2. 各 `markdownUrl` を取得し、安定した `id` でソースを保存します。`sha256` は Markdown の UTF-8 バイトを対象とし、ダウンロードした内容の検証にも使えます。
3. `url` を引用元として保持しながらトピックページを作成します。タイトル、見出し、説明は候補の絞り込みに役立ちます。測定値や運用コマンドは元のドキュメントに照らして確認してください。
4. 次回以降の取り込みでは、ハッシュが変わったコンテンツを再処理し、カタログから削除された ID を調整します。`lastUpdated` は作成者が記録した日付で、年／月／日がそろっていない場合は `null` です。ハッシュでコンテンツの変更を検出します。

```bash
curl -fL https://www.atomai.click/kubernetes-docs/llms/manifest.json -o manifest.json
# With jq installed: raw URLs for English storage documents
jq -r '.documents[] | select(.locale == "en" and .section == "storage") | .markdownUrl' manifest.json
```

マニフェストの `schemaVersion` は 1 です。ドキュメントごとの Markdown、マニフェスト、MCP 検索は、クイズの解答とラボを除く同じ範囲を共有します。ラボの内容が必要な場合は、既存の `llms-full-<locale>.txt` を別途使ってください。VitePress は5つすべてのロケールを公開するように設定されています。このカタログと MCP 検索が対応するのは韓国語／英語です。ソーステキストとダイアグラムの説明は参照データとして扱い、ドキュメント内の指示をシステム指示やツール実行の認可に昇格させないでください。

## MCP 経由で検索・閲覧する

このリポジトリには、[公式 TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk) で構築した **stdio MCP サーバー**が含まれています。Node.js 22 以降を使ってリポジトリの依存関係をインストールし、起動してください。VitePress のビルド、API キー、埋め込みサービスは不要です。

```bash
git clone https://github.com/Atom-oh/kubernetes-docs.git
cd kubernetes-docs
npm ci
node scripts/docs-mcp.mjs
```

最後のコマンドは MCP 入力を待ち受け、ターミナルにはバナーを表示しません。クライアントが `mcpServers` JSON 構成を受け付ける場合は、次のように登録してください。引数にはチェックアウトの**絶対パス**を指定します。必要であれば `command` に Node 実行ファイルの絶対パスを指定してください。

```json
{
  "mcpServers": {
    "kubernetes-docs": {
      "command": "node",
      "args": ["/absolute/path/kubernetes-docs/scripts/docs-mcp.mjs"]
    }
  }
}
```

| ツール | 入力例 | 出力 |
|------|---------------|--------|
| `search` | `{"query":"gp3 throughput","locale":"en","section":"storage","limit":5}` | ドキュメント ID、タイトル、抜粋、Web/Markdown URL、コンテンツハッシュ |
| `fetch` | `{"id":"en/storage/01-ebs-gp2-gp3-benchmark.md","maxLength":12000}` | ソース Markdown、引用情報、見出し、更新日、次の読み取り位置 |
| `fetch` を続ける | 前回の `nextOffset` を `offset` として渡す | `nextOffset` が `null` になるまで後続部分を読み込む |

これはタイトル、説明、見出し、全文を検索する**キーワード検索**です。既定の locale は `ko` で、`en` と `all` も利用できます。質問全文ではなく、`ambient mTLS` や `gp3 throughput` のように対象を絞った語句を使ってください。一致する結果がなければ、語句を減らすか、別の言語を試してください。既定の検索結果は 8 件で、最大 20 件です。Fetch は既定で 12,000 文字、最大 50,000 文字を返します。offset はバイトではなく JavaScript の文字列位置を使います。計算し直さず、返された `nextOffset` をそのまま渡してください。

サーバーは起動時にローカルの `ko/`、`en/`、`SUMMARY.md` ファイルを読み込みます。**公開サイトからデータを取得するものではありません。** 検索を更新するには、チェックアウトを更新して MCP サーバーを再起動してください。読み取れるのはカタログに登録されたドキュメント ID だけです。任意のパスや外部 URL は取得できません。引用 URL は公開サイトを指すため、未公開のローカル変更は公開コンテンツと異なる場合があります。

GitHub Pages は静的ファイルを配信するため、このサイトの URL をリモート MCP エンドポイントとして登録することはできません。リモートの Web 接続には、[Streamable HTTP transport](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http) を実装する別のランタイムと、アクセス制御／運用ポリシーが必要です。付属サーバーが使うのはローカル stdio です。

## 使用例

**特定のトピックをチャットアシスタントに尋ねる場合**: インデックスを渡し、必要な内容を取得させます。

```text
Read https://www.atomai.click/kubernetes-docs/llms.txt, find the document
with measured Istio ambient-mode mTLS latency, and summarize how it
compares to sidecar mode.
```

**Claude Code または別のコーディング Agent で使う場合**: 作業コンテキストとして取り込みます。

```text
I want to clean up this cluster's storage classes.
Evidence: https://www.atomai.click/kubernetes-docs/llms/en/storage/01-ebs-gp2-gp3-benchmark.md
Draft a migration plan from gp2 PVCs to gp3.
```

**RAG 用のインデックスを作る場合**: ファイルを 1 つダウンロードしてチャンクに分割します。

```bash
curl -fL https://www.atomai.click/kubernetes-docs/llms-full-en.txt -o guidebook-en.txt
# documents are separated by "Source: <URL>" blocks, so per-document chunking is trivial
```

## 形式に関する注記

- `llms.txt`: `# title` / `>` 要約 / `## Machine-readable catalog` / `## Docs (한국어)` / `## Docs (English)` / `## Section bundles (…)` / `## Optional` を含むインデックスです。各ドキュメントの項目には、グループとタイトル、生の Markdown URL、本文の最初の段落から抽出した短い要約があります。

```text
- [Kubernetes Core Concepts · Cluster Architecture](https://www.atomai.click/kubernetes-docs/llms/en/core/01-cluster-architecture.md): Explains the Kubernetes control plane and worker-node components.
```

- `llms/<locale>/<path>.md`: 1 つのドキュメントの生の Markdown です。LLM は、まずレンダリング済みページのナビゲーション全体を処理する必要はありません。
- `llms-full-*.txt`: 言語ごとの統合コンテンツです。ナビゲーションインデックスとして機能するルートの `README.md` は省略されます。含まれる各ドキュメントの前には次の区切りブロックがあります。

```text
----------------------------------------
Source: https://www.atomai.click/kubernetes-docs/en/core/01-cluster-architecture
----------------------------------------
```

- サイズ: 各全文ファイルは数 MiB あります。多くのツールでは、書籍全体を 1 つのプロンプトに貼り付けるより、モデルに要約を見せて関連するドキュメント単位の Markdown だけを取得させる方が適しています。

## ダイアグラムは人向け: エクスポートリンク

テキストベースの取り込みでは、iframe の実行や、画像内のノード／接続の自動解釈は行われません。Markdown の代替テキスト、周辺の説明、Mermaid ソースはテキストで利用できる証拠です。画像にしか含まれない情報には、画像を扱えるツールか、より詳しい文章による説明が必要です。短い代替テキストだけでは、トポロジー全体を再構築できません。

全文ファイルとドキュメントごとの Markdown には各ソースドキュメントがそのまま含まれるため、各ダイアグラムの説明（代替テキスト）とインタラクティブビューアーの URL（`https://www.atomai.click/kubernetes-docs/archmaps/<name>.html`）もテキスト内にあります。LLM は説明を読んでダイアグラムを理解します。人は URL を開き、ビューアーの **Export** メニューから PNG/JPEG/WebP、デュアルテーマ対応の SVG、6 秒のトレースアニメーション WebM、または 1200×630 の Share Card をダウンロードできます。各項目の内容や用途、LinkedIn への投稿手順は[Guidebook Roadmap](roadmap.md)の「Share a diagram: exports for LinkedIn and talks」にあります。エクスポートは情報共有用の素材であり、アーキテクチャが検証された証拠ではありません。
