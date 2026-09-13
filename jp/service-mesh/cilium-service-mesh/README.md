# Ciliumサービスメッシュの概要

> **最終更新**: September 11, 2026 · Cilium/chart 1.20.1 · CLI 0.20.0 · Hubble CLI 1.19.4

CiliumはKubernetesネットワーキング、eBPFポリシー/負荷分散、任意のアプリケーション層プロキシ機能を組み合わせます。選択したL7通信はCiliumのEnvoy統合が扱います。アプリごとのサイドカーをなくしても、プロキシ、カーネル要件、運用コンポーネントがなくなるわけではありません。

## アーキテクチャとセキュリティ境界

![Istioサイドカーモードとの論理比較。CiliumはeBPFデータパスを使い、選択L7通信を共有Envoyへリダイレクトする。暗号化/性能保証でもIstio ambientの図でもない。](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-readme-0.png)

[インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-readme-0.html)

EnvoyはCiliumエージェント内のプロセスか、別管理の`cilium-envoy` DaemonSetで動作できます。選択チャートの通常レンダリング設定は専用DaemonSetを使います。実配置とL7ホップ数は有効な機能/ポリシーに依存し、全パケットがEnvoyを通るわけではありません。

| コンポーネント | 役割 |
|---|---|
| Cilium agent | ノードデータパス、エンドポイントID、ポリシー適用 |
| Cilium operator | 選択モードのIPAMと他のクラスター/コントローラー責務 |
| Envoy | 一致するL7ポリシー、Ingress、Gateway API処理 |
| Hubble | フロー観測。L7記録には関連プロキシ可視性が必要 |
| Hubble Relay / UI | 追加の集約と可視化コンポーネント |
| SPIRE（設定時） | ベータ相互認証機能のID基盤 |

### 相互認証は自動的な通信暗号化ではない

Cilium 1.20.1は**帯域外相互認証をベータかつ未完成**としています。mTLSベースのIDハンドシェイクは、CiliumセキュリティIDについてエージェント間で帯域外に行われます。全アプリ接続をIstio/Linkerdワークロードプロキシと同じTLS転送モデルで包むものではありません。

WireGuard/IPsecは独自の対応モードと範囲を持つ別暗号化機構です。WireGuardはTLSではなく、SPIRE有効化だけではアプリデータ暗号化や全エンドポイントの認証ルール有効化はしません。選択リリースは相互認証がClusterMeshや外部メッシュmTLSと非互換とも文書化しています。

Cilium 1.20.1は別の[ztunnel透過暗号化ベータ](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst)も提供し、`encryption.type: ztunnel`で選びます。名前空間参加によりTCPワークロードmTLSを提供し、両端参加が必要です。ClusterMeshとホストネットワークPodは対象外です。リリースガイドはHBONE 15008を対象とする場合以外、通常L4ポリシーがこの経路で動かないと警告します。独自CA/ブートストラップ要件を持つ別のデプロイ選択肢です。

このベータ経路の採用前に[セキュリティガイド](03-security.md)とリリースのセキュリティモデル/制限を確認します。ルーティング、認証、認可、暗号化は別要件として扱います。

CiliumはIstioデプロイの基盤CNIにもなれます。このネットワーク統合で認証方式が交換可能になるわけではありません。モード固有のソケット負荷分散、CNI共存、L7ポリシー所有権を確認します。

## 機能と実測費用の比較

| 項目 | Cilium | Istio | Linkerd |
|---|---|---|---|
| データプレーンモデル | eBPFと選択L7処理用共有Envoy | サイドカー、またはambientのztunnel/waypoint | ネイティブサイドカー配置を含むPodごとのプロキシ |
| Podネットワーク | モードによりCNIを提供またはチェイニング | 基盤Podネットワークが必要。独自CNIはメッシュ通信をリダイレクト | 基盤Podネットワークが必要。任意CNIはメッシュ通信をリダイレクト |
| ポリシー | Kubernetes/CiliumネットワークポリシーとL7機能 | 別のネットワークポリシー層を伴うメッシュ認可/ルーティング | Server/ルート認可と送信ルーティング。L4専用ポリシーではない |
| Gateway API | 任意有効化コントローラーと文書化された適合性/機能 | Gatewayとメッシュルーティングの役割 | 対応するService/Server親ルートの役割 |
| セキュリティ | 帯域外認証と別暗号化。制限付きの別ztunnel mTLSベータ | ワークロードメッシュmTLSとポリシー | ワークロードメッシュmTLSとポリシー |

ワークロードや設定に依存しない普遍的なCPU/メモリ/レイテンシー順位を持つ製品はありません。以前の固定ノード/Pod別数値や100 Podメモリ図は出典付きベンチマークでなく、コンポーネント、ノード数、ワークロード詳細が欠けていました。エージェント/プロキシ、コントローラー、テレメトリー、ID基盤を含め、同じ基準に対する実測追加費用を比較します。

ネットワークモデルと必要L7機能が環境に合う場合、特にすでに運用中ならCiliumは有用です。CNI移行、カーネル/プラットフォーム対応、共有ノード障害の影響、セキュリティ要件、既存ポリシー依存を評価します。「サイドカーなし」「eBPF」のどちらも、金融/リアルタイムワークロードの遅延や費用目標の証明にはなりません。

広い機能境界は保守されている[サービスメッシュ比較](../istio/comparison/01-service-mesh-comparison.md)を参照してください。

## バージョンとプラットフォームの前提条件

選択リリースについて:

- 一般Kubernetes e2e互換リストは**1.33–1.36**です。リリースEKS CIファイルは**1.33–1.35**を列挙し、デフォルトは1.35です。別々の証拠であり、新版/プロバイダー未掲載の組み合わせは別途検証が必要です。
- Helmチャートの緩い`kubeVersion >=1.21.0-0`はテスト済みサポート表ではなく、新Kubernetesリリースが自動的に対象になるわけではありません。
- ホストは対応AMD64/AArch64 Linuxと通常カーネル5.10以降、または文書化された同等バックポートが必要です。L7リダイレクトなど高度機能には追加カーネル/モジュール要件があります。
- このCiliumリリースのGateway API参照版は**v1.6.1**です。変更前に必須/任意CRDと1.20 TLSRoute更新注意点を確認し、互換レビューなしで最新カタログ版に置き換えないでください。

```bash
cilium version --client
cilium version
cilium status --wait --wait-duration 5m
kubectl -n kube-system get daemonset cilium
# For the dedicated Envoy mode selected below:
kubectl -n kube-system get daemonset cilium-envoy
```

CLI自身の版と稼働Ciliumイメージ版は別情報です。全状態出力と失敗を保持します。「Envoy」「Hubble」に一致するgrepは準備完了を証明しません。組み込みモードなら専用Envoy DaemonSetがないことは想定どおりの場合があります。

### EKSインストールの選択肢

| モード/プラットフォーム | 必要な区別 |
|---|---|
| Cilium AWS ENIモード | CiliumがENI IPAM/ネイティブルーティングを管理。IAM、経路、ノード/Pod参加計画が必要。一般1.20.1 ENI参照はIPv6 Betaを文書化する一方、EKSインストールページはまだIPv4専用としている。ここではIPv4例を使い、プラットフォーム固有IPv6要件/対応を別途確認 |
| AWS VPC CNIチェイニング | AWS VPC CNIがインターフェース/IPAMを担当し、Ciliumが後からデータパスを接続。高度L7/IPsec制限を評価 |
| EKS Fargate | 代替CNIは非対応。AWS VPC CNI必須 |
| EKS Auto Mode | 代替CNIとネットワークポリシープラグインは非対応 |
| EKS Hybrid Nodes | EC2 ENI引数でなく、別のAWS対応Cilium版/設定/機能ガイダンスに従う |

EC2ノードCNIのAWSサポートはAmazon VPC CNIに限定され、互換代替CNIは独自の運用/ベンダーサポートが必要です。別のHybrid Nodesサポート境界を汎用Cilium互換表から推測してはいけません。

1行のHelmインストールは既存AWS VPC CNIクラスターの移行計画ではありません。APIブートストラップアクセス、kube-proxy置換、CNI所有権、IAM、ノード準備Taint、既存未管理Podの再作成を検証済み手順で扱います。この監査ではクラスター作成やCNI置換を行っていません。

## 選択機能の有効化

正しく導入済みのCiliumでは、次の機能オーバーレイを`cilium-mesh-features.yaml`として保存します。

```yaml
l7Proxy: true
envoy:
  enabled: true
hubble:
  enabled: true
  relay:
    enabled: true
  ui:
    enabled: true
```

対応L7フラグは`l7Proxy`で、`proxy.enabled`は代替ではありません。ネイティブチャート確認で、`proxy.enabled:false`はL7を有効のままにし、`l7Proxy:false`は無効にすることを確認しました。

```bash
set -euo pipefail
umask 077
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
# Preview only: reviewed-cni-values.yaml must describe the existing intended CNI mode.
helm template cilium cilium/cilium --version 1.20.1 \
  --namespace kube-system --kube-version 1.35.0 \
  -f reviewed-cni-values.yaml -f cilium-mesh-features.yaml \
  > cilium-mesh-rendered.yaml
```

互換Kubernetes版の例をプレビューし、レビュー済みCNI valuesとマージします。結果を確認し、既存所有者の下で対応アップグレード手順に従います。完全CNIインストールやネットワークモード変更許可ではありません。

| 任意機能 | 追加要件 |
|---|---|
| Gateway API | kube-proxy置換、L7プロキシ、必須v1.6.1 CRD、適切なLB/ホストネットワーク設計 |
| Ingressコントローラー | 対応設定と公開モデル。自動的に全メッシュ通信を扱うわけではない |
| Hubbleメトリクス | 選択メトリクス群と設定済みcollector。Relay/UI自体はPrometheusを作らない |
| 相互認証 | ベータのレビュー、明示有効化、SPIRE/ストレージ/接続、該当認証ポリシー、別評価の暗号化 |

**隔離したベータ認証評価**では、旧例に欠けた最上位フラグを含める必要があります。

```yaml
authentication:
  enabled: true
  mutual:
    spire:
      enabled: true
      install:
        enabled: true
```

チャートは`authentication.enabled:true`なしのSPIRE統合を拒否します。同梱SPIREサーバーはデフォルトで永続ストレージを使い、適切なPVCプロビジョニングが前提です。この断片は本番セキュリティ、クラスター間認証、アプリ通信暗号化を成立させません。

## L7ポリシーと観測の例

`bookinfo`に`app:productpage`ラベル付きCilium管理HTTPアプリと、同じ名前空間に`app:frontend`のCilium管理クライアントを準備します。Bookinfoなら必要なアプリ依存を完全にデプロイしてください。productpageだけのDeploymentは完全Bookinfoではありません。検証済みイメージとアプリに適した準備確認を使います。

次のポリシーはそのエンドポイントを選び、示したクライアント/メソッド/パスの組み合わせを許可します。どちらのワークロードも作成しません。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: productpage-l7
  namespace: bookinfo
spec:
  endpointSelector:
    matchLabels:
      k8s:app: productpage
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: bookinfo
    toPorts:
    - ports:
      - port: '9080'
        protocol: TCP
      rules:
        http:
        - method: GET
          path: ^/productpage$
        - method: GET
          path: ^/health$
```

所有者を通じて適用する前に、他ポリシーと期待されるデフォルト拒否効果を評価します。例は2パスを許可し、完全ブラウザーフローの全静的資産/依存は許可しません。認証/暗号化はこのL7 Allowと別です。

```bash
# Keep this terminal running; configure the intended kube context first.
cilium hubble port-forward --port-forward 4245

# In another terminal, use the selected Hubble CLI:
hubble status --server localhost:4245
hubble observe --server localhost:4245 --namespace bookinfo --protocol http --follow
# Service-name filters are an alternative to --namespace in this CLI.
hubble observe --server localhost:4245 --to-service bookinfo/productpage
```

選択Hubble CLIは`--namespace`と`--to-service`の併用を拒否します。名前空間観測か、名前空間付きService名プレフィックスのどちらかを使います。L7記録には実一致通信とプロキシ可視性が必要です。L7プロキシ前の破棄には広いフロー/破棄検査が必要な場合があります。観測フローがないことは、アプリ経路の許可、拒否、健全性の証明ではありません。

## 文書構成と参考資料

| ガイド | 範囲 |
|---|---|
| [アーキテクチャ](01-architecture.md) | データパス、Envoy、APIモデル |
| [トラフィック管理](02-traffic-management.md) | ルーティングと負荷分散 |
| [セキュリティ](03-security.md) | ポリシー、認証、暗号化の境界 |
| [可観測性](04-observability.md) | Hubbleとメトリクス |
| [Ingress/Gateway](05-ingress-gateway.md) | 外部通信とGateway API |
| [ベストプラクティス](06-best-practices.md) | 運用、移行、検証 |

- [リリースのKubernetes互換性](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/kubernetes/compatibility.rst)
- [システム要件](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/operations/system_requirements.rst)
- [IstioとCiliumネットワーキング](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/istio.rst)
- [Envoyモード](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/proxy/envoy.rst)
- [相互認証の制限](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
- [Gateway APIの前提条件](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/gateway-api/installation.rst)
- [EKS ENI要件](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/installation/requirements-eks.rst)と[AWS VPC CNIチェイニング](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/installation/cni-chaining-aws-cni.rst)
- [EKS代替CNI](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)と[Hybrid Nodes CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Cilium 1.20.1 ENI IPAM / IPv6 Beta](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/eni.rst)
