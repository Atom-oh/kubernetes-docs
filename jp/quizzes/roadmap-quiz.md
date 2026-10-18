# ガイドブックのロードマップクイズ

1. ドメインマップで、Storage ドメインと Database ドメインが属するレイヤーはどれですか？
   - A) Foundations
   - B) Connectivity
   - C) State
   - D) Cross-cutting
<details>
<summary>解答を表示</summary>

**解答: C) State**

**解説:**
ドメインマップの表では、Storage（fio で測定した EBS gp2 と gp3 の比較）と Database（オペレーターの動向と 1 億行の ClickHouse ベンチマーク）は、どちらも「State」レイヤーに属します。Foundations には Linux と Container、Connectivity には Networking と Service Mesh、Cross-cutting には Security & Policy、GitOps、Platform Engineering、Container Registry、Observability、Operations Guide が含まれます。

</details>

2. ロードマップの学習フローマップに沿ったレイヤーの順序はどれですか？
   - A) Orchestration → Foundations → Connectivity → State → Data & AI → Cross-cutting
   - B) Foundations → Orchestration → Connectivity → State → Data & AI → Cross-cutting
   - C) Foundations → Connectivity → Orchestration → Data & AI → State → Cross-cutting
   - D) Cross-cutting → Foundations → Orchestration → Connectivity → State → Data & AI
<details>
<summary>解答を表示</summary>

**解答: B) Foundations → Orchestration → Connectivity → State → Data & AI → Cross-cutting**

**解説:**
学習フローマップでは、ガイドブックの 15 のドメインが、「Foundations（Linux/Container）から Orchestration（Kubernetes/EKS）、Connectivity（Networking/Service Mesh）、State（Storage/Database）、Data & AI（Data Pipeline/AI-ML）を経て、Cross-cutting の関心事（Security/GitOps/Platform/Container Registry/Observability/Operations）へ」と流れる構成になっています。Linux カーネルからクラウドネイティブスタック全体を扱う、一続きの学習ストーリーです。

</details>

3. 次のうち、ロードマップの測定済みベンチマークシリーズに**含まれない**ドメインはどれですか？
   - A) Service Mesh（Istio sidecar と ambient）
   - B) Storage（EBS gp2 と gp3）
   - C) Database（EKS 上の ClickHouse）
   - D) GitOps（ArgoCD、Flux）
<details>
<summary>解答を表示</summary>

**解答: D) GitOps（ArgoCD、Flux）**

**解説:**
測定済みベンチマークシリーズは、「過去に AWS リソース上で実行した結果を報告するドキュメント」で構成されています。具体的には、Istio sidecar と ambient（mTLS データプレーンごとの P50/P99 レイテンシーと、ロールアウト中の 503 発生率）、EBS gp2 と gp3 のベンチマーク（容量が同じ場合の IOPS が 10 倍異なる点と、gp2 のバーストクレジット枯渇）、EKS 上の ClickHouse ベンチマーク（1 億行の取り込みスループット、圧縮率、クエリレイテンシー）、Kafka on EKS のベンチマーク（単一実行における RF3/RF1 のスループット記録など）、および Pod Network Benchmark です。このリストには 5 項目あります。GitOps は Cross-cutting ドメインですが、このシリーズに測定済みページはありません。

</details>

4. 推奨パス③「Data & AI platform」の推奨される読む順序はどれですか？
   - A) AI/ML → Data Pipeline → Database → Storage
   - B) Storage → Database → Data Pipeline (Kafka → Spark → Airflow → Flink) → AI/ML (vLLM → Ray → Kubeflow)
   - C) Data Pipeline → Storage → AI/ML → Database
   - D) Database → Storage → AI/ML → Data Pipeline
<details>
<summary>解答を表示</summary>

**解答: B) Storage → Database → Data Pipeline (Kafka → Spark → Airflow → Flink) → AI/ML (vLLM → Ray → Kubeflow)**

**解説:**
パス③は「Storage → Database → Data Pipeline (Kafka → Spark → Airflow → Flink) → AI/ML (vLLM → Ray → Kubeflow)」の順に進みます。また、GPU とスケジューリング制御が必要な場合は、Kubernetes Core Concepts の Custom Scheduler の各パートも含めるよう勧めています。State レイヤーから Data & AI レイヤーへと進む経路です。

</details>

5. 推奨パス①「Infrastructure onboarding」では、理解度をどのように確認するようロードマップが勧めていますか？
   - A) 各ドキュメントのクイズに取り組みながら、ラボも並行して進める
   - B) 測定済みベンチマークシリーズ全体を先に読む
   - C) ダイアグラムの Share Card をエクスポートする
   - D) `llms.txt` の URL を LLM に渡して要約を依頼する
<details>
<summary>解答を表示</summary>

**解答: A) 各ドキュメントのクイズに取り組みながら、ラボも並行して進める**

**解説:**
パス①は「Linux Basics → Container Technology → Introduction to Kubernetes → Core Concepts（Pod/Service/ストレージ/構成）→ EKS Cluster Creation → Network Fundamentals」の順に進み、「各ドキュメントのクイズで理解度を確認し、ラボも並行して進める」よう勧めています。ラボは `labs/README.md` から始められます。測定済みベンチマークシリーズは、パス② Platform / SRE の根拠として紹介されています。

</details>

6. LinkedIn のフィードで実際に動くダイアグラムを投稿したいとします。ロードマップにある 30 秒の手順はどれですか？
   - A) ビューアーを画面録画し、GIF に変換する
   - B) ツールバーの Live/Still 切り替えが Live になっていることを確認し、Export（`E`）→ WebM で 6 秒のトレースアニメーションをダウンロードする
   - C) Export → SVG でエクスポートし、動画として LinkedIn にアップロードする
   - D) Route Probe（`R`）でパスを解決し、「Copy diagram」でクリップボードにコピーする
<details>
<summary>解答を表示</summary>

**解答: B) ツールバーの Live/Still 切り替えが Live になっていることを確認し、Export（`E`）→ WebM で 6 秒のトレースアニメーションをダウンロードする**

**解説:**
各インタラクティブダイアグラムは `https://www.atomai.click/kubernetes-docs/archmaps/<name>.html` で開きます。ビューアーツールバーの **Export** ボタン（ショートカット `E`）から、その場で共有用ファイルを作成できます。利用できる形式はビューアーのバージョン、ブラウザーのサポート、現在の選択によって異なります。手順は次のとおりです。(1) ダイアグラムを開く。(2) 矢印に沿って流れる動きが録画されるよう、**Live/Still** 切り替えが Live になっていることを確認する。(3) 動きのある投稿には **Export → WebM**、静的な 1200×630 のプレビューには **Export → Share Card** を選ぶ。(4) 元のドキュメントの URL と一緒に投稿する。WebM では「6 秒間の動きを録画しています…」と表示された後にファイルがダウンロードされます。トレースアニメーション付きのダイアグラムと、ブラウザーの MediaRecorder サポートが必要です。SVG はスライド用のデュアルテーマ対応ベクター形式です。

</details>

7. Export メニューの **Route Share Card** に関する説明として正しいものはどれですか？
   - A) すべてのダイアグラムに常に表示され、近くにある図形の間の経路を自動的に推測する
   - B) Route Probe（`R`）で 2 つのノード間のパスを解決した後にのみ表示され、作成者が定義した有向関係だけをたどる
   - C) ノードの上流／下流の到達可能性を、影響範囲分析として表示する
   - D) クリップボードへのコピーだけに対応し、ダウンロードには対応しない
<details>
<summary>解答を表示</summary>

**解答: B) Route Probe（`R`）で 2 つのノード間のパスを解決した後にのみ表示され、作成者が定義した有向関係だけをたどる**

**解説:**
Export メニューの表によると、Route Share Card は 1200×630 の PNG で、ダウンロードのみ可能です。「Route Probe（`R`）で 2 つのノード間のパスを解決した後にのみ表示」されます。真実性の境界に関するセクションでは、「Route Share Card は作成者が定義した有向関係だけをたどる。図形の配置から経路を推測せず、古い、または到達不能な経路のエクスポートを拒否する」と説明しています。上流／下流の到達可能性を示すのは別の Reach Share Card であり、それも影響分析、影響範囲、障害、またはランタイムの因果関係として提示してはいけません。

</details>

8. Share Card などのエクスポートファイルについて、ロードマップは「真実性の境界」でどのような立場を示していますか？
   - A) エクスポートは情報共有用の素材であり（アーキテクチャが検証された証拠ではない）、Share Card は検証済みだと主張しない
   - B) Share Card には「検証済み」のバッジが自動で付与され、検証の証拠として使える
   - C) エクスポートが正式な成果物となり、公開 HTML に置き換わる
   - D) Reach Share Card はランタイムの障害伝播を測定するため、インシデント報告書にそのまま使える
<details>
<summary>解答を表示</summary>

**解答: A) エクスポートは情報共有用の素材であり（アーキテクチャが検証された証拠ではない）、Share Card は検証済みだと主張しない**

**解説:**
このセクションの最初の箇条書きには、「エクスポートは情報共有用の素材です。アーキテクチャが検証された証拠ではなく、公開 HTML や作成者自身による検証に取って代わるものでもありません。Share Card が検証済みだと主張することはありません」とあります。同様に、Reach Share Card が示すのは*作成者の定義した到達可能性*だけです。影響分析、影響範囲、障害、またはランタイムの因果関係として提示してはいけません。

</details>
