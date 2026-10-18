# ガイドブックのロードマップ

> **最終更新日**: 2026 年 10 月 16 日

このガイドブックでは、Linux カーネルからコンテナ、Kubernetes、Amazon EKS、ネットワーキング、サービスメッシュ、ストレージ、データベース、データパイプライン、AI/ML までを一続きのストーリーとして扱います。さらに、セキュリティ、GitOps、プラットフォームエンジニアリング、コンテナレジストリ、オブザーバビリティ、運用という横断的な分野も扱います。このページは全体のマップであり、推奨する学習経路を示します。

![ガイドブックの 15 ドメインが、Foundations（Linux/Container）から Orchestration（Kubernetes/EKS）、Connectivity（Networking/Service Mesh）、State（Storage/Database）、Data & AI（Data Pipeline/AI-ML）を経て、Cross-cutting（Security/GitOps/Platform/Container Registry/Observability/Operations）へ流れる学習フローマップ。](.gitbook/assets/en-roadmap-0.png)

[🔍 インタラクティブダイアグラムを表示](https://www.atomai.click/kubernetes-docs/archmaps/en-roadmap-0.html)

## ドメインマップ

| レイヤー | ドメイン | ここから始める | 概要 |
|-------|--------|-----------|-----------|
| Foundations | Linux & Container | [Linux の基礎](basics/01-linux-basics.md) | カーネル、namespace、cgroup: コンテナの実体 |
| Orchestration | Kubernetes Core Concepts | [Kubernetes 入門](basics/04-kubernetes-introduction.md) | ワークロード、スケジューリング、自動スケーリング: Kubernetes 自体を学ぶ |
| Orchestration | Amazon EKS | [EKS 入門](eks/01-eks-introduction.md) | クラスタ作成から Hybrid Nodes、Auto Mode まで |
| Connectivity | Networking | [ネットワークの基礎](basics/06-network-fundamentals-part1.md) | 25 のプロトコルから CNI（Cilium/Calico）まで |
| Connectivity | Service Mesh | [Istio](service-mesh/istio/README.md) | Istio/Linkerd/Cilium Mesh と、mTLS レイテンシーの測定 |
| State | Storage | [ストレージの概要](storage/README.md) | fio で測定した EBS gp2 と gp3 の比較 |
| State | Database | [データベースの概要](database/README.md) | Operator の動向と 1 億行の ClickHouse ベンチマーク |
| Data & AI | Data Pipeline | [Data on EKS の概要](data-on-eks/README.md) | Kafka、Spark、Airflow、Flink の詳細と、Kafka の単一実行ベンチマーク記録 |
| Data & AI | AI/ML | [AI/ML ワークロード](ai-ml/01-ai-ml-workloads.md) | EKS 上の vLLM、Ray、Kubeflow、MLflow |
| Cross-cutting | Security & Policy | [Kyverno](security/01-kyverno-policy-management.md) | 認証／認可、ポリシー、ランタイムセキュリティ、サプライチェーン |
| Cross-cutting | GitOps | [GitOps](gitops/README.md) | ArgoCD、Flux、段階的なデリバリー |
| Cross-cutting | Platform Engineering | [概要](platform-engineering/00-platform-engineering-overview.md) | ACK、KRO、Crossplane、Backstage |
| Cross-cutting | Container Registry | [概要](container-registry/README.md) | ECR、Harbor、イメージサプライチェーン |
| Cross-cutting | Observability | [概要](observability/README.md) | メトリクス、ログ、トレース、アラートのスタック |
| Cross-cutting | Operations Guide | [運用ガイド](ops/README.md) | 容量計画、FinOps、アップグレード、症状から調べる[トラブルシューティング手順書](ops/16-troubleshooting-playbook.md) |

## 測定済みベンチマークシリーズ

AWS リソースで以前に実行した結果を報告するドキュメントです。現在の容量計画に使う前に、環境、反復回数、キャッシュ状態、生データの有無、制約を確認し、改めて測定してください。

- [測定済み: Istio sidecar と ambient の比較](service-mesh/istio/comparison/03-sidecar-vs-ambient.md): mTLS データプレーンごとの P50/P99 レイテンシーと、ロールアウト中の 503 発生率
- [EBS gp2 と gp3 の測定済みベンチマーク](storage/01-ebs-gp2-gp3-benchmark.md): 容量がともに 100 GiB の場合の IOPS が 10 倍異なる点と、gp2 のバーストクレジット枯渇
- [EKS 上の ClickHouse の測定済みベンチマーク](database/01-clickhouse-on-eks.md): 1 億行の取り込みスループット、圧縮率、クエリレイテンシー
- [EKS 上の Kafka の測定済みベンチマーク](data-on-eks/kafka/09-kafka-benchmark.md): RF3/acks=all で 134.74 MiB/s、RF1/acks=1 で 337.81 MiB/s という単一実行の記録（RF3 の持続的な上限として確認された値ではない）、acks 設定ごとの p99、再生データの消費中に記録されたプロデューサースループット 44.49% 低下
- [Pod ネットワークのベンチマーク](networking/06-pod-network-benchmark.md): RTT が 0.040 → 0.339 → 0.544 ms と段階的に増加する結果（同一ノード → 同一 AZ → AZ 間）、AZ に関係なく単一フローが 4.96 Gbps で頭打ちになり 8 フローでは 9.94 Gbps となった結果、`ndots:5` による 10 クエリ／8 NXDOMAIN への増幅

## ダイアグラムを共有する: LinkedIn や講演向けのエクスポート

このガイドブックのインタラクティブダイアグラムは `https://www.atomai.click/kubernetes-docs/archmaps/<name>.html` で開きます。ビューアーツールバーの **Export** ボタン（ショートカット `E`）を使うと、その場で共有用ファイルを作成できます。利用できるエクスポート項目は、ビューアーのバージョン、ブラウザーの機能、選択状態によって異なります。

### Export メニューで利用できる項目

| グループ | メニュー項目 | 出力 | 用途 |
|-------|-----------|--------|-----------|
| Share | **Share Card** / **Copy Share Card** | 1200×630 PNG（ダウンロード／クリップボード） | LinkedIn と X のリンクプレビュー、README、リリースノート |
| Share | **Route Share Card** | 1200×630 PNG（ダウンロードのみ） | Route Probe（`R`）で 2 つのノード間のパスを解決した後にのみ表示 |
| Share | **Reach Share Card** | 1200×630 PNG（ダウンロードのみ） | Semantic Passport からノードの上流／下流の到達可能性を追跡した後にのみ表示 |
| Share | **Copy diagram** | ダイアグラム全体の PNG をクリップボードにコピー | スライドやドキュメントへ直接貼り付ける |
| Image | **PNG** / **JPEG** / **WebP** | ダイアグラム全体のラスター画像 | 可逆形式が必要な場合は PNG、ファイルサイズを抑えたい場合は JPEG/WebP |
| Vector & motion | **SVG** | デュアルテーマ（ライト＋ダーク）対応のベクター | 任意のズーム倍率でも鮮明なスライド |
| Vector & motion | **WebM** | 6 秒のトレースアニメーション録画 | フィード上で実際にフローが動く LinkedIn 投稿 |

エクスポートでは、ビューアーの状態（Guide パネル、Lens、finder、focus、route、story、カメラ位置、radar、presentation mode、一時的なオーバーレイ）がすべて除かれ、ダイアグラム本体だけが残ります。Share Card は現在のテーマとビジュアルプリセットを保持し、切り抜かずにダイアグラム全体を含みます。WebM の録画には、トレースアニメーション付きのダイアグラムとブラウザーの MediaRecorder サポートが必要です。サポートされていないブラウザーでは、メニューにその旨が表示されます。

### LinkedIn に投稿する 30 秒の手順

1. **ダイアグラムを開く**: 埋め込みダイアグラムの下にある「Open full screen ↗」リンクをクリックします（GitBook では「🔍 View interactive diagram」）。
2. **トレースが再生中か確認する**: ツールバーの **Live/Still** 切り替えが Live になっていることを確認してください。矢印に沿って流れる動きが録画されます。講演のリハーサルをする場合は、**Presentation stage**（`F`）でダイアグラムをビューポート全体に表示できます。
3. 動きのある投稿には **Export → WebM**、静的な 1200×630 プレビューには **Export → Share Card** を選択します。WebM では「6 秒間の動きを録画しています…」と表示された後、ファイルがダウンロードされます。
4. **投稿する**: 投稿先のプラットフォームが現在受け付ける形式を確認し、必要であれば WebM を変換します。Share Card は画像としてアップロードし、ソースドキュメントの URL を記載してください。特定のノード、パス、ストーリーの場面を示すには、Semantic Passport または Route Probe の **Copy link**、あるいは Story Beat の **Copy moment**（ストーリー章を定義したダイアグラムにのみ表示）を使い、詳細リンクをコメントやスライドに貼り付けます。

### 表現できる内容の境界

- エクスポートは**情報共有用の素材**です。アーキテクチャが検証された証拠ではなく、公開 HTML や作成者自身による検証にも取って代わりません。Share Card が検証済みだと主張することはありません。
- Route Share Card がたどるのは、**作成者が定義した有向関係**だけです。図形の配置から経路を推測せず、古い、または到達不能な経路のエクスポートを拒否します。
- Reach Share Card が示すのは、*作成者が定義した到達可能性*です。影響分析、影響範囲、障害、またはランタイムの因果関係として提示しないでください。

## 推奨する学習経路

### ① インフラの導入:「コンテナから EKS まで」

Linux Basics → Container Technology → Introduction to Kubernetes → Core Concepts（Pod/Service/ストレージ／構成）→ EKS Cluster Creation → Network Fundamentals の順に進みます。各ドキュメントのクイズで理解を確認し、[ラボ](labs/README.md)も並行して進めてください。

### ② Platform / SRE:「運用できるクラスタ」

EKS の運用（アップグレード／トラブルシューティング／レジリエンス）→ Networking（VPC CNI、Cilium）→ Service Mesh の比較ガイド → Security & Policy → Observability スタック → GitOps → Operations Guide の容量計画と FinOps の順に進みます。この経路の根拠となるのが、測定済みベンチマークシリーズです。

### ③ Data & AI プラットフォーム:「ステートフルな世界」

Storage → Database → Data Pipeline（Kafka → Spark → Airflow → Flink）→ AI/ML（vLLM → Ray → Kubeflow）の順に進みます。GPU とスケジューリング制御が必要な場合は、Kubernetes Core Concepts の Custom Scheduler の各パートも加えてください。

## LLM を使った読み方

このガイドブックは、提案されている llms.txt 形式でインデックスとソーステキストを提供します。AI ツールが内容を取得するには、Web 検索または MCP 接続も必要です。URL を 1 つ指定しただけで、書籍全体の読み込みやインデックス作成が自動的に行われるとは限りません。エンドポイントと使用例については、[LLM を使った読み方](llm-guide.md)を参照してください。
