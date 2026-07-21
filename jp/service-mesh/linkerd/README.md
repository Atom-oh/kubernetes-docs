# Linkerd

> **対応バージョン**: Linkerd 2.16+ **最終更新**: July 21, 2026

### 2026年7月アップデート: edge-26.7.1 — 未定義の Service ポートへのリクエストを禁止

2026年7月16日に公開された edge-26.7.1 リリースには、**動作を変更する（破壊的な）修正**が含まれています。これまで、対象 Service に ServiceProfile が定義されている場合、Service に定義されていないポートへのリクエストも許可されていました。Destination controller は、Service に定義されていないポートに対する `GetProfile` リクエストに空の `DestinationProfile` を返すようになり、proxy は client policy API にフォールバックします。この API は適切に Forbidden フィルターを返して接続を拒否します。いずれかの workload が Service resource で宣言されていないポートを使用して通信している場合は、アップグレード前にポート定義を整理してください。詳細については、[リリースノート](https://github.com/linkerd/linkerd2/releases/tag/edge-26.7.1) を参照してください。

## 概要

Linkerd は CNCF（Cloud Native Computing Foundation）の卒業プロジェクトであり、軽量な service mesh ソリューションです。2016年に Buoyant によって開発され、「service mesh」という用語を初めて生み出したプロジェクトです。Linkerd の中核的な価値は、シンプルさ、デフォルトでのセキュリティ、最小限のリソースオーバーヘッドであり、Kubernetes 環境におけるサービス間通信を安全かつ信頼性の高いものにします。

### 主な価値提案

| 価値                   | 説明                                                              |
| ----------------------- | ------------------------------------------------------------------------ |
| **シンプルさ**          | 複雑な設定なしでそのまま利用できる、合理的なデフォルト設定 |
| **デフォルトでのセキュリティ** | 設定不要の自動 mTLS 暗号化                      |
| **軽量**         | 最小限のリソース使用量（メモリ \~10MB）の Rust 製マイクロプロキシ  |
| **高速なパフォーマンス**    | p99 レイテンシーオーバーヘッドは 1ms 未満                                       |
| **運用の容易さ**    | シンプルなアップグレードと直感的なデバッグツール                            |

## Linkerd アーキテクチャの概要

```mermaid
graph TB
    subgraph "Control Plane"
        D[Destination<br/>Service Discovery]
        I[Identity<br/>Certificate Issuance]
        P[Proxy Injector<br/>Sidecar Injection]
    end

    subgraph "Data Plane"
        subgraph "Pod A"
            A1[Application]
            AP[linkerd-proxy]
        end
        subgraph "Pod B"
            B1[Application]
            BP[linkerd-proxy]
        end
    end

    subgraph "Extensions"
        V[Viz<br/>Dashboard/Metrics]
        J[Jaeger<br/>Distributed Tracing]
        M[Multicluster<br/>Multi-cluster]
    end

    AP -->|mTLS| BP
    AP --> D
    AP --> I
    P -->|Inject| AP
    P -->|Inject| BP
    V --> AP
    V --> BP
```

## Service Mesh の比較

各ソリューションの特性を理解するために、Linkerd、Istio、Cilium Service Mesh を比較します。

| 機能                | Linkerd               | Istio                  | Cilium Service Mesh     |
| ---------------------- | --------------------- | ---------------------- | ----------------------- |
| **Proxy**              | linkerd2-proxy (Rust) | Envoy (C++)            | eBPF + Envoy (optional) |
| **リソース使用量**     | 非常に少ない (\~10MB)     | 多い (\~50-100MB)      | 少ない (eBPF モード)         |
| **レイテンシーオーバーヘッド**   | <1ms p99              | 2-5ms p99              | <1ms (eBPF モード)        |
| **複雑さ**         | 低い                   | 高い                   | 中程度                  |
| **mTLS**               | 自動（デフォルト）   | 設定が必要 | 設定が必要  |
| **トラフィック管理** | 基本（SMI）           | 非常に豊富              | 基本                   |
| **可観測性**      | 良好（組み込み）       | 優れている              | 良好（Hubble）                  |
| **マルチクラスター**      | Service Mirroring     | 複雑なセットアップ          | ClusterMesh             |
| **CNI 統合**    | 個別              | 個別               | ネイティブ                  |
| **CNCF ステータス**        | 卒業済み             | 卒業済み              | 卒業済み               |
| **学習曲線**     | 緩やか                | 急峻                  | 中程度                  |
| **コミュニティ**          | 活発                | 非常に活発            | 活発                  |

## Linkerd を選ぶべき場合

### 適したユースケース

1. **シンプルさが重要な場合**
   * 複雑なトラフィック管理機能よりも基本的な service mesh 機能が必要な場合
   * 小規模な運用チーム、または service mesh の経験が限られているチーム
   * 迅速な導入と低い学習曲線を優先する場合
2. **リソース効率が重要な場合**
   * node あたり多数の Pod を実行する環境
   * sidecar のオーバーヘッドを最小限に抑える必要がある場合
   * レイテンシーに敏感なアプリケーション
3. **セキュリティをデフォルトにすべき場合**
   * 設定なしの自動 mTLS が必要な場合
   * ゼロトラストネットワークの実装
   * コンプライアンスのための暗号化要件
4. **運用のシンプルさが必要な場合**
   * シンプルなアップグレードプロセスを優先する場合
   * 最小限の CRD と設定
   * 直感的な CLI ツール

### あまり適していないユースケース

1. **高度なトラフィック管理が必要な場合**
   * 複雑なルーティングルール、ヘッダー操作
   * 高度なロードバランシングアルゴリズム
   * 広範なプロトコルサポート（gRPC 以外）
2. **VM workload の統合**
   * Kubernetes 外部の workload との統合
   * VM とコンテナが混在する環境
3. **大規模なマルチプロトコル環境**
   * さまざまなプロトコルのサポートが必要な場合（Kafka、MongoDB など）
   * 複雑な Wasm 拡張要件

## ドキュメント構成

このセクションでは、Linkerd の主な機能と運用方法について説明します。

| ドキュメント                                       | 説明                                                                         |
| ---------------------------------------------- | ----------------------------------------------------------------------------------- |
| [インストールとセットアップ](01-installation.md)   | CLI のインストール、control plane のインストール、HA 構成、拡張機能          |
| [アーキテクチャ](02-architecture.md)             | control plane、data plane、証明書階層の詳細                            |
| [トラフィック管理](03-traffic-management.md) | ServiceProfile、TrafficSplit、リトライ、タイムアウト、canary deployment                 |
| [セキュリティ](04-security.md)                     | mTLS、認可ポリシー、証明書管理、外部 CA 統合       |
| [可観測性](05-observability.md)           | メトリクス、ダッシュボード、CLI ツール、Prometheus/Grafana 統合、分散トレーシング |
| [マルチクラスター](06-multi-cluster.md)           | Service mirroring、クラスターリンク、フェイルオーバー                                        |
| [ベストプラクティス](07-best-practices.md)         | 本番チェックリスト、パフォーマンスチューニング、トラブルシューティング                           |

## クイックスタート

### 1. Linkerd CLI をインストールする

```bash
# Linux/macOS
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh
export PATH=$HOME/.linkerd2/bin:$PATH

# Verify installation
linkerd version
```

### 2. 事前フライトクラスター検証

```bash
# Verify cluster meets Linkerd requirements
linkerd check --pre
```

### 3. Linkerd をインストールする

```bash
# Install CRDs
linkerd install --crds | kubectl apply -f -

# Install control plane
linkerd install | kubectl apply -f -

# Verify installation
linkerd check
```

### 4. アプリケーションを Mesh に追加する

```bash
# Enable automatic injection for namespace
kubectl annotate namespace my-app linkerd.io/inject=enabled

# Restart existing deployments to inject proxy
kubectl rollout restart deployment -n my-app

# Or manually inject
kubectl get deploy -n my-app -o yaml | linkerd inject - | kubectl apply -f -
```

### 5. Dashboard をインストールしてアクセスする

```bash
# Install Viz extension
linkerd viz install | kubectl apply -f -

# Open dashboard
linkerd viz dashboard
```

## Linkerd コンポーネントのステータスを確認する

```bash
# Full status check
linkerd check

# Control plane status
linkerd check --proxy

# Data plane proxy status
linkerd viz stat deploy -n my-app

# Real-time traffic monitoring
linkerd viz tap deploy/my-app -n my-app
```

## コアコンセプト

### Data Plane Proxy

Linkerd は、`linkerd-proxy` という sidecar コンテナを各 Pod に注入します。この proxy は以下の特性を持ちます。

* メモリ安全性と高パフォーマンスのために Rust で記述されている
* 使用メモリは約 10MB のみ
* 追加するレイテンシーは 1ms 未満
* すべてのインバウンド/アウトバウンドトラフィックを処理する
* mTLS 暗号化を自動的に適用する

### Service Discovery

Destination コンポーネントは Kubernetes Service を監視し、proxy に endpoint 情報を提供します。

* リアルタイムの endpoint 更新
* ServiceProfile ベースのルーティング情報
* トラフィック分割ポリシーの配布

### 自動 mTLS

Linkerd は、設定なしですべての mesh トラフィックを自動的に暗号化します。

1. Identity コンポーネントが各 proxy に証明書を発行する
2. proxy 間の相互 TLS 認証
3. 自動証明書更新（デフォルトは 24 時間）

## 次のステップ

1. [**インストールとセットアップ**](01-installation.md): クラスターへの Linkerd インストールに関する詳細ガイド
2. [**アーキテクチャ**](02-architecture.md): Linkerd の内部構造を理解する
3. [**クイズ**](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/service-mesh/linkerd/README.md): 知識をテストする

## 参考資料

* [Linkerd 公式ドキュメント](https://linkerd.io/2/overview/)
* [Linkerd GitHub](https://github.com/linkerd/linkerd2)
* [CNCF Linkerd プロジェクトページ](https://www.cncf.io/projects/linkerd/)
* [Linkerd Slack コミュニティ](https://slack.linkerd.io/)
* [Buoyant ブログ](https://buoyant.io/blog)
