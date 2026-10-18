# Linkerd

> **最終更新日**: 2026年10月16日 · 公開 CLI の例は edge-26.10.1 で確認

上流プロジェクトは edge 成果物を公開し、stable ディストリビューションとそのサポート期間はベンダーが提供します。Linkerd 2.20 は機能上の節目であり、ダウンロードする CLI に共通するバージョン文字列ではありません。正確なディストリビューション／リリースを選び、Kubernetes および Gateway API との互換性を確認してください。ここで示す最新の公開例は、2026年10月5日公開の edge-26.10.1（proxy v2.370.0）です。multicluster でのリモート認証情報を使う exec-auth-provider の受け入れと、再試行可能な宛先 IP 競合の処理は edge-26.9.1 で修正されました。[リリース](https://github.com/linkerd/linkerd2/releases/tag/edge-26.10.1)と[リリースモデル](https://linkerd.io/releases/)を参照してください。

以下の項目は、過去のリリース情報を残しています。edge-26.8.2 でテストされた Kubernetes の最大バージョンが、stable なベンダーディストリビューションのサポート対象バージョンまで自動的に広がるわけではありません。

### 2026年8月の更新: edge-26.8.4

2026年8月25日公開の edge-26.8.4 は、opaque protocol の処理で nil の ExternalWorkload を扱う際の問題を防ぎ、policy controller がクラスターと TLSRoute API バージョンをネゴシエートするようにし、Go を 1.26.7 に更新します。詳しくは[リリースノート](https://github.com/linkerd/linkerd2/releases/tag/edge-26.8.4)を参照してください。

### 2026年8月の更新: edge-26.8.2（Gateway API 1.5.1 対応）

2026年8月14日公開の edge-26.8.2 は、linkerd-kubert 0.27.0 を通じて Gateway API 1.5.1 に対応し、テスト済みの Kubernetes 最大バージョンを 1.36 に引き上げます。また、destination controller の重複した Job informer を削除し、lease watch task が停止した場合に policy controller を終了させる安定性修正も含まれます。詳しくは[リリースノート](https://github.com/linkerd/linkerd2/releases/tag/edge-26.8.2)を参照してください。

### 2026年7月の更新: edge-26.7.1（未定義の Service ポートへのリクエストを拒否）

edge-26.7.1 の GitHub リリースは2026年7月21日に公開されました。ServiceProfile が存在しても、宛先 Service に宣言されていないポートへのリクエストを拒否する、動作に影響する修正が含まれます。アップグレード前に実際の Service ポート宣言を確認してください。このリリースでは Gateway API のインストール確認も追加されました。[リリースノート](https://github.com/linkerd/linkerd2/releases/tag/edge-26.7.1)を参照してください。

## 概要

Linkerd は Rust 製データプレーンプロキシを備えた、CNCF の卒業プロジェクトであるサービスメッシュです。CNCF の記録では、最初のコミットは2016年、卒業は2021年です。「シンプル」や「軽量」を保証とみなさず、実際のワークロードに照らして運用モデル、プロトコル対応、リソース使用量を評価してください。

### 主な価値と確認事項

| 機能 | 確認事項 |
|---|---|
| ワークロードのデフォルト mTLS | 通信する両方の peer が mesh に参加し、proxy を迂回する通信がないこと。mesh に参加していない peer からの平文通信には明示的な認可ポリシーが必要 |
| Rust proxy | 想定する接続数と通信量におけるメモリ／CPU の requests、limits、実使用量 |
| HTTP／gRPC ルーティング | 対応する Gateway API の型、attachment、プロトコル検出 |
| 運用 | 証明書のライフサイクル、HA、アップグレード互換性、拡張機能の管理主体 |
| 性能 | ワークロード固有のレイテンシ、エラー、負荷の測定。10 MB やサブミリ秒を普遍的に保証するものではない |

## Linkerd のアーキテクチャ概要

| コンポーネント | 役割 |
|---|---|
| Destination／policy controller | エンドポイントを検出し、ルーティング／認可ポリシーを proxy に配布する |
| Identity | ID 要求を検証し、設定された trust 認証情報を使って有効期間の短いワークロード証明書を発行する |
| Proxy Injector | 対象となる新規 Pod を変更して proxy を追加する |
| linkerd-proxy | 設定された TCP 通信を捕捉し、対象の mesh 経路を認証／暗号化して、サポートされる L7 動作を提供する |
| 任意の拡張機能／バックエンド | Viz のメトリクス／ダッシュボード、multicluster 連携、別途設定するトレース収集／保存を提供する |

このアーキテクチャだけで、メモリ使用量やレイテンシの固定値が決まるわけではありません。選択したワークロードと設定で測定してください。

## サービスメッシュの比較

| 観点 | Linkerd | Istio | Cilium |
|---|---|---|---|
| データプレーン | Rust sidecar | Envoy sidecar、または ztunnel と waypoint | eBPF ネットワークと、対応する L7 機能用の Envoy |
| HTTP ルーティング | Gateway API route。以前からのワークフローでは ServiceProfile も引き続き利用可能 | Istio API またはサポート対象の Gateway API attachment | Gateway API と Cilium の policy／controller 機能 |
| セキュリティ | mesh に参加する対象 TCP peer 間では自動 mTLS。その他の接続元は認可制御で扱う | Auto mTLS、受信時の強制、認可はそれぞれ別の制御 | peer 認証とペイロード暗号化を別々に評価する |
| 可観測性 | proxy メトリクスと、設定した Viz／他のバックエンド | モード固有のテレメトリと、設定したバックエンド | Hubble と、設定した L7／メトリクスバックエンド |
| マルチクラスター | mirroring／federation と、明示的な trust／ネットワーク設定 | トポロジーに応じてサポートされる mesh 構成 | ClusterMesh と、それに必要なプラットフォーム／ネットワーク要件 |
| 選定 | 必要な機能と運用をテストする | 必要な機能と運用をテストする | 必要な機能と運用をテストする |

SMI TrafficSplit は旧来のワークフローであり、現在の Linkerd ルーティング全体を説明するものではありません。Linkerd は Gateway API を通じて、リクエストの特性に基づく HTTP／gRPC ルーティングができます。再現可能なワークロードとバージョンを明記した測定がなければ、固定のメモリ使用量、p99、人員配置／複雑さの順位を比較することはできません。

## Linkerd を選ぶ場合

標準の Kubernetes 統合、ワークロード ID、サポートされる HTTP／gRPC／TCP の動作がアプリケーション要件に合う場合、Linkerd は選択肢になります。現実的な負荷でリソース効率とレイテンシを測定し、CA ローテーション、アクセス制御、アップグレードを計画してください。転送時の暗号化が自動化されるだけで、完全なゼロトラストやコンプライアンスが実現するわけではありません。

mesh を選ぶ前に、必要なルーティング、filter、拡張性の機能を正確に検証してください。非 HTTP プロトコルは TCP として proxy できますが、HTTP レベルのルーティングやメトリクスが得られるわけではありません。server-first やアイドル状態の接続には opaque port または appProtocol の設定が必要な場合があり、アプリケーションが開始する TLS は HTTP 検査からは見えません。opaque traffic も proxy を通過しますが、skip port は proxy を迂回します。

VM と物理マシンとの統合は、ExternalWorkload の登録と外部 ID／bootstrap 経路を含む[mesh 拡張](https://linkerd.io/docs/tasks/adding-non-kubernetes-workloads/)で利用できます。これは一律に非対応ということではありません。ネットワーク到達性、DNS、proxy のインストール、trust の設計が、通常の Pod 注入にはない要件として加わります。上流チュートリアルの bootstrap を簡略化した手順は、本番環境の設計ではありません。

## ドキュメント構成

| ドキュメント | 説明 |
|---|---|
| [インストールと設定](01-installation.md) | 正確なリリース／互換性、CLI／Helm、trust 認証情報、HA、拡張機能 |
| [アーキテクチャ](02-architecture.md) | controller、proxy、証明書階層 |
| [トラフィック管理](03-traffic-management.md) | Gateway API、旧 ServiceProfile、再試行／timeout、トラフィック分割 |
| [セキュリティ](04-security.md) | mTLS の境界、認可、CA ローテーション |
| [可観測性](05-observability.md) | メトリクス、Viz、外部バックエンド、トレース |
| [マルチクラスター](06-multi-cluster.md) | mirroring／federation、ネットワーク経路、trust、認証情報 |
| [ベストプラクティス](07-best-practices.md) | 運用検証、性能、トラブルシューティング |

## クイックスタート

### 1. CLI と前提条件を選ぶ

選択した OS／アーキテクチャと正確なリリースに対応する[インストールガイド](01-installation.md)に従ってください。CLI の出力が意図したディストリビューションのものか確認し、バージョンを固定しないインストーラーが古い stable 版をインストールすると想定しないでください。Gateway API CRD は前提条件であり、インストールする bundle はそれを利用するすべての controller と互換でなければなりません。

```bash
linkerd version --client
kubectl config current-context
kubectl get crd httproutes.gateway.networking.k8s.io   -o 'jsonpath={.metadata.annotations.gateway\.networking\.k8s\.io/bundle-version}'
linkerd check --pre
```

### 2. マニフェストを生成、確認してインストールする

選択した CLI と前提条件を用意した新規の管理されたラボ環境では、CLI がマニフェストを生成します。

```bash
set -euo pipefail
linkerd install --crds > linkerd-crds.yaml
# Review CRD ownership/version before applying.
kubectl apply -f linkerd-crds.yaml
linkerd install > linkerd-control-plane.yaml
# Review trust credentials and deployment settings before applying.
kubectl apply -f linkerd-control-plane.yaml
linkerd check
```

デフォルトの CLI 設定では、有効期間が限られた trust 認証情報が生成されます。これは共有 trust を使う完成済みの multicluster 設定ではありません。再現可能で長期運用するインストールには、文書化された Helm／CA ライフサイクルの手順に従ってください。このレビューで確認したのはオフラインでのレンダリングと CLI 構文であり、実環境へのインストールではありません。

### 3. 対象のアプリケーションを追加する

既存の namespace と Deployment を使う場合は、`my-app` の名前を両方とも実際の対象に置き換えてください。

```bash
kubectl annotate namespace my-app linkerd.io/inject=enabled
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
linkerd check --proxy -n my-app
```

競合する annotation がすでにある場合は、自動的に上書きせず内容を確認してください。注入されるのは新しい Pod だけです。ローリング再起動には、ワークロードの readiness とキャパシティを守る対策が必要です。手動注入をレビュー済みのアプリケーションマニフェストに対して実施する方法もあります。すべての稼働中 Deployment に対し、一律の修正として inject／apply を往復させないでください。

### 4. 必要な場合に Viz を追加する

```bash
linkerd viz install > linkerd-viz.yaml
# Review the extension's backend, resources and retention.
kubectl apply -f linkerd-viz.yaml
linkerd viz check
linkerd viz dashboard
```

Viz は任意の機能で、独自のライフサイクル管理が必要です。デフォルトのメトリクス設定は、あらゆる本番環境に適用できる保持期間／HA 設計ではありません。

## Linkerd コンポーネントの状態確認

```bash
# Core installation/control-plane checks.
linkerd check
# Data-plane proxy checks in the selected namespace.
linkerd check --proxy -n my-app
# Requires the configured Viz extension.
linkerd viz stat deploy -n my-app
linkerd viz tap deploy/my-app -n my-app
```

Tap が観測するのはサポート対象の HTTP リクエストイベントです。すべての TCP 経路、パケット、暗号化境界を証明するものではありません。

## 中核概念

### データプレーン proxy

Rust 製の linkerd-proxy は mesh に参加するワークロードと並んで動作します。設定された TCP 経路を処理しますが、skip port、mesh に参加していないエンドポイント、プラットフォーム上の制約は別途確認してください。HTTP レベルの動作には、HTTP が可視であるか検出されている必要があります。Pod ごとのリソース使用量が一定だと想定せず、使用量とレイテンシを測定してください。

### サービス検出

Destination と policy のコンポーネントは Service／endpoint の状態を監視し、ルーティング情報を提供します。ServiceProfile と Gateway API は別々の設定経路であり、優先順位と機能対応はバージョンによって異なります。対象とするすべての Service port を宣言してください。上記の過去の破壊的変更に関する注意も参照してください。

### 自動 mTLS

文書化されたデフォルトでは、ワークロード証明書の有効期間は24時間で、自動更新されます。ID は Pod の ServiceAccount に結び付き、Pod ごとに一意の ID が割り当てられるわけではありません。trust anchor と issuer 認証情報には別々のライフサイクルがあります。デフォルトの CLI が生成する認証情報は1年で期限切れとなるため、計画的なローテーションが必要です。

mesh に参加する TCP peer 間では mTLS が使われますが、mesh に参加していない peer との通信と skip port は、この自動保証の対象外です。受信側のデフォルトポリシーは mesh に参加していない peer からの平文通信を許可します。拒否する必要がある場合は認可ポリシーを使ってください。マルチクラスター通信には、共有 trust と明示的な接続設定が必要です。

## 次のステップ

1. [インストールと設定](01-installation.md)
2. [アーキテクチャ](02-architecture.md)
3. [インストールクイズ](../../quizzes/service-mesh/linkerd/installation.md)、[アーキテクチャクイズ](../../quizzes/service-mesh/linkerd/architecture.md)、[トラフィッククイズ](../../quizzes/service-mesh/linkerd/traffic-management.md)
4. [セキュリティクイズ](../../quizzes/service-mesh/linkerd/security.md)、[可観測性クイズ](../../quizzes/service-mesh/linkerd/observability.md)、[マルチクラスタークイズ](../../quizzes/service-mesh/linkerd/multi-cluster.md)

## 参考資料

- [Linkerd ドキュメント](https://linkerd.io/docs/overview/)
- [リリース系列](https://linkerd.io/releases/)と[インストール](https://linkerd.io/docs/tasks/install/)
- [Gateway API](https://linkerd.io/docs/features/gateway-api/)と[リクエストルーティング](https://linkerd.io/docs/features/request-routing/)
- [自動 mTLS と注意事項](https://linkerd.io/docs/features/automatic-mtls/)と[TCP／プロトコル処理](https://linkerd.io/docs/features/protocol-detection/)
- [CNCF プロジェクト記録](https://www.cncf.io/projects/linkerd/)
- [Linkerd GitHub](https://github.com/linkerd/linkerd2)、[コミュニティ](https://slack.linkerd.io/)、[Buoyant ブログ](https://buoyant.io/blog)
