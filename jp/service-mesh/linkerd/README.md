# Linkerd

> **最終更新**: September 11, 2026 · 公開CLI例はedge-26.9.1で確認

上流はedge成果物を公開し、stableディストリビューションとサポート期間はベンダーが提供します。Linkerd 2.20は機能上の節目で、取得CLIの普遍的な版文字列ではありません。正確な配布/版を選びKubernetes/Gateway API互換性を確認します。ここの公開例はSeptember 4, 2026公開のedge-26.9.1で、multiclusterのremote credential exec-auth-provider受付と、再試行可能なdestination-IP競合処理を修正します。[リリース](https://github.com/linkerd/linkerd2/releases/tag/edge-26.9.1)と[リリースモデル](https://linkerd.io/releases/)を参照します。

以下は過去のrelease背景を保持します。edge-26.8.2のテスト済みKubernetes最大版は、stableベンダー対応表を自動拡張しません。

### 2026年8月更新: edge-26.8.4

August 25, 2026公開のedge-26.8.4はopaque処理のnil ExternalWorkloadを防ぎ、policy controllerがclusterとTLSRoute API版をネゴシエートし、Goを1.26.7へ更新します。詳細は[リリースノート](https://github.com/linkerd/linkerd2/releases/tag/edge-26.8.4)を参照してください。

### 2026年8月更新: edge-26.8.2 — Gateway API 1.5.1対応

August 14, 2026公開のedge-26.8.2はlinkerd-kubert 0.27.0でGateway API 1.5.1対応を追加し、テストKubernetes最大を1.36へ上げます。destinationの重複Job informer削除とlease watch task停止時のpolicy controller終了という安定性修正も含みます。詳細は[リリースノート](https://github.com/linkerd/linkerd2/releases/tag/edge-26.8.2)を参照してください。

### 2026年7月更新: edge-26.7.1 — 未定義Serviceポートへの要求を禁止

edge-26.7.1のGitHub releaseはJuly 21, 2026公開です。ServiceProfileがあっても宛先Service未宣言portへの要求を拒否する動作変更を含みます。更新前に実Service port宣言を確認します。Gateway API導入チェックも追加します。[リリースノート](https://github.com/linkerd/linkerd2/releases/tag/edge-26.7.1)を参照してください。

## 概要

LinkerdはRustデータプレーンproxyを持つCNCF卒業サービスメッシュです。CNCF記録では初commitは2016、卒業は2021です。「単純」「軽量」を保証とせず、実workloadに対する運用、protocol対応、resource使用を評価します。

### 中核的な価値

| 機能 | 確認事項 |
|---|---|
| 既定workload mTLS | 両peerが参加しproxyを迂回しない。未参加平文には明示認可policyが必要 |
| Rust proxy | 期待接続/通信下のメモリ/CPU requests、limits、使用量 |
| HTTP/gRPC routing | 対応Gateway API型、接続、protocol検出 |
| 運用 | 証明書ライフサイクル、HA、更新互換性、拡張所有権 |
| 性能 | 固有の遅延/エラー/負荷測定。普遍的10MB/1ms未満の約束はない |

## Linkerdアーキテクチャ概要

| コンポーネント | 役割 |
|---|---|
| Destination/policy controller | endpoint検出とrouting/認可policy配布 |
| Identity | ID要求を検証し設定trust認証情報で短命workload証明書を発行 |
| Proxy Injector | 新規適格Podを変更しproxy追加 |
| linkerd-proxy | 設定TCP捕捉、適格mesh経路の認証/暗号化、対応L7動作 |
| 任意拡張/backend | Viz metrics/dashboard、multicluster、別設定trace収集/保存 |

固定メモリ占有や遅延負荷を意味しません。選択workload/設定で測定します。

## サービスメッシュ比較

| 観点 | Linkerd | Istio | Cilium |
|---|---|---|---|
| データプレーン | Rust sidecar | Envoy sidecar、またはztunnelとwaypoint | eBPFネットワークと対応L7用Envoy |
| HTTP routing | Gateway API。旧手順にServiceProfile対応継続 | Istio APIまたは対応Gateway API接続 | Gateway APIとCilium policy/controller機能 |
| セキュリティ | 適格mesh TCP間自動mTLS。他sourceは認可制御 | Auto mTLS、受信強制、認可は別制御 | Peer認証とpayload暗号化を別評価 |
| 可観測性 | Proxy metricsと設定Viz/他backend | mode別telemetryと設定backend | Hubbleと設定L7/metrics backend |
| Multicluster | Mirroring/federationと明示trust/network | 対応topology固有mesh構成 | ClusterMeshとplatform/network要件 |
| 選択 | 必要機能/運用をテスト | 必要機能/運用をテスト | 必要機能/運用をテスト |

SMI TrafficSplitは旧手順で、現Linkerd routingの全説明ではありません。Gateway APIでHTTP/gRPCを要求特性により送れます。固定メモリ、p99、人員/複雑さの順位は再現可能workloadと版付き測定なしに比較できません。

## Linkerdを選ぶ場合

既定Kubernetes統合、workload ID、対応HTTP/gRPC/TCPがアプリ要件に合う場合の候補です。実負荷でresource効率/遅延を測り、CA rotation、アクセスpolicy、更新を計画します。自動転送暗号化だけでは完全ゼロトラスト/コンプライアンスではありません。

mesh選択前に必要routing/filter/拡張性を正確に検証します。非HTTPはTCPとしてproxyできますがHTTPレベルrouting/metricsは得られません。server-first/idle接続はopaque-portやappProtocolが必要な場合があり、アプリTLSはHTTP検査に不透明です。opaqueはproxyを通り、skip portは迂回します。

VM/物理機器統合はExternalWorkload登録と外部ID/bootstrapを含む[メッシュ拡張](https://linkerd.io/docs/tasks/adding-non-kubernetes-workloads/)で可能で、一律非対応ではありません。network、DNS、proxy導入、trustは通常Pod注入を超える要件です。上流チュートリアルのbootstrap簡略手順は本番設計ではありません。

## 文書構成

| 文書 | 説明 |
|---|---|
| [導入と設定](01-installation.md) | 正確な版/互換性、CLI/Helm、trust認証情報、HA、拡張 |
| [アーキテクチャ](02-architecture.md) | Controller、proxy、証明書階層 |
| [トラフィック管理](03-traffic-management.md) | Gateway API、旧ServiceProfile、再試行/timeout、分割 |
| [セキュリティ](04-security.md) | mTLS境界、認可、CA rotation |
| [可観測性](05-observability.md) | Metrics、Viz、外部backend、tracing |
| [マルチクラスター](06-multi-cluster.md) | Mirroring/federation、経路、trust、認証情報 |
| [ベストプラクティス](07-best-practices.md) | 運用検証、性能、トラブルシューティング |

## クイックスタート

### 1. CLIと前提条件の選択

選択OS/architectureと正確なreleaseの[導入ガイド](01-installation.md)に従います。CLI出力が意図配布か確認し、未固定installerが旧stableを出すと想定しません。Gateway API CRDは前提で、全利用controllerと互換である必要があります。

```bash
linkerd version --client
kubectl config current-context
kubectl get crd httproutes.gateway.networking.k8s.io   -o 'jsonpath={.metadata.annotations.gateway\.networking\.k8s\.io/bundle-version}'
linkerd check --pre
```

### 2. レンダリング、レビュー、導入

選択CLIと前提を持つ管理された新演習で、CLIがマニフェストを生成します。

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

既定CLIは有限寿命のtrust認証情報を生成します。完成済み共有trust multicluster設定ではありません。反復可能な長期導入はHelm/CAライフサイクル手順に従います。このレビューはオフラインrenderと構文確認で実導入ではありません。

### 3. 対象アプリ追加

選択した既存namespace/Deploymentに合わせ、両my-appを実targetへ置換します。

```bash
kubectl annotate namespace my-app linkerd.io/inject=enabled
kubectl -n my-app rollout restart deployment/my-app
kubectl -n my-app rollout status deployment/my-app
linkerd check --proxy -n my-app
```

競合アノテーションを自動上書きせずreviewします。注入は新Podだけで、rolling restartにはreadiness/容量の保護策が必要です。manual注入はreviewしたアプリmanifestにも使えます。汎用修正として全稼働Deploymentをinject/applyに往復させないでください。

### 4. 必要ならVizを追加

```bash
linkerd viz install > linkerd-viz.yaml
# Review the extension's backend, resources and retention.
kubectl apply -f linkerd-viz.yaml
linkerd viz check
linkerd viz dashboard
```

Vizは任意で独自ライフサイクルが必要です。既定metricsは普遍的本番保持/HA設計ではありません。

## Linkerdコンポーネント状態確認

```bash
# Core installation/control-plane checks.
linkerd check
# Data-plane proxy checks in the selected namespace.
linkerd check --proxy -n my-app
# Requires the configured Viz extension.
linkerd viz stat deploy -n my-app
linkerd viz tap deploy/my-app -n my-app
```

Tapは対応HTTP要求イベントを観測し、全TCP経路/packet/暗号化境界の証明ではありません。

## 中核概念

### データプレーンプロキシ

Rust linkerd-proxyは参加workloadに併設され、設定TCP経路を処理します。skip、未参加先、platform制限は別確認です。HTTP動作には可視/検出済みHTTPが必要です。Pod別固定占有を想定せずresource/遅延を測ります。

### サービス検出

Destination/policyがService/endpoint状態を監視しrouting情報を提供します。ServiceProfileとGateway APIは版別優先/対応を持つ別経路です。全対象Service portを宣言してください。上の過去の破壊的変更を参照します。

### 自動mTLS

文書化されたworkload証明書既定寿命は24時間、自動更新です。IDはPodのServiceAccountに結び付き、Podごと一意ではありません。trust anchor/issuerは別寿命で、CLI既定生成は1年で切れ、計画rotationが必要です。

mesh TCP peerはmTLSを使いますが、未参加peerとskip portは自動保証の外です。既定受信policyは未参加平文を許し、拒否が必要なら認可policyを使います。multiclusterには共有trustと明示接続が必要です。

## 次のステップ

1. [導入と設定](01-installation.md)
2. [アーキテクチャ](02-architecture.md)
3. [導入クイズ](../../quizzes/service-mesh/linkerd/installation.md)、[アーキテクチャクイズ](../../quizzes/service-mesh/linkerd/architecture.md)、[通信クイズ](../../quizzes/service-mesh/linkerd/traffic-management.md)
4. [セキュリティクイズ](../../quizzes/service-mesh/linkerd/security.md)、[可観測性クイズ](../../quizzes/service-mesh/linkerd/observability.md)、[マルチクラスタークイズ](../../quizzes/service-mesh/linkerd/multi-cluster.md)

## 参考資料

- [Linkerdドキュメント](https://linkerd.io/docs/overview/)
- [リリース系列](https://linkerd.io/releases/)と[導入](https://linkerd.io/docs/tasks/install/)
- [Gateway API](https://linkerd.io/docs/features/gateway-api/)と[要求routing](https://linkerd.io/docs/features/request-routing/)
- [自動mTLSと注意点](https://linkerd.io/docs/features/automatic-mtls/)と[TCP/protocol処理](https://linkerd.io/docs/features/protocol-detection/)
- [CNCFプロジェクト記録](https://www.cncf.io/projects/linkerd/)
- [Linkerd GitHub](https://github.com/linkerd/linkerd2)、[コミュニティ](https://slack.linkerd.io/)、[Buoyantブログ](https://buoyant.io/blog)
