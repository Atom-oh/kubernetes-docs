# Cilium サービスメッシュの概要

> **最終更新**: 2026年10月16日 · Cilium/chart 1.20.3 · CLI 0.20.1 · Hubble CLI 1.20.2

Cilium は、Kubernetes ネットワーキング、eBPF によるポリシー適用と負荷分散、および任意のアプリケーション層プロキシ機能を組み合わせます。選択された L7 トラフィックは Cilium の Envoy 統合で処理されます。アプリケーションごとのサイドカーをなくしても、プロキシ、カーネル要件、運用コンポーネントが不要になるわけではありません。

## アーキテクチャとセキュリティ境界

![Istio のサイドカーモードとの論理的な比較。Cilium は eBPF データパスを使い、選択された L7 トラフィックを共有 Envoy にリダイレクトする。暗号化や性能を保証する図ではなく、Istio ambient の構成図でもない。](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-readme-0.png)

[インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-readme-0.html)

Envoy は Cilium エージェントと同じプロセス内で動作させることも、専用の `cilium-envoy` DaemonSet として別管理することもできます。選択した Helm チャートの標準的なレンダリング設定では、専用 DaemonSet を使います。実際の配置と L7 のホップ数は、有効にした機能やポリシーによって異なり、すべてのパケットが Envoy を通るわけではありません。

| コンポーネント | 役割 |
|---|---|
| Cilium agent | ノードのデータパス、エンドポイント ID、ポリシー適用 |
| Cilium operator | 選択したモードの IPAM など、クラスターやコントローラーに関する役割 |
| Envoy | 該当する L7 ポリシー、Ingress、Gateway API の処理 |
| Hubble | フローの観測。L7 記録には該当プロキシの可視性が必要 |
| Hubble Relay / UI | フロー集約と可視化を追加するコンポーネント |
| SPIRE（設定時） | ベータ版の相互認証機能で使う ID 基盤 |

### 相互認証は自動的な通信暗号化ではない

Cilium 1.20.3 では、**帯域外相互認証はベータ版で、未完成**とされています。mTLS ベースの ID ハンドシェイクは、Cilium のセキュリティ ID に関してエージェント間で帯域外に行われます。これは、Istio や Linkerd のワークロードプロキシと同じ TLS トランスポートで、すべてのアプリケーション接続を保護する仕組みではありません。

WireGuard と IPsec は、それぞれ固有の対応モードと適用範囲を持つ別の暗号化機構です。WireGuard は TLS ではありません。また、SPIRE を有効にするだけでは、アプリケーションデータは暗号化されず、すべてのエンドポイントで認証ルールが有効になるわけでもありません。選択したリリースでは、相互認証は ClusterMesh や外部サービスメッシュの mTLS と併用できないことも明記されています。

Cilium 1.20.3 には、別の[ztunnel 透過暗号化ベータ版](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/network/encryption-ztunnel.rst)もあり、`encryption.type: ztunnel` で選択します。名前空間単位の登録により TCP ワークロード mTLS を提供し、通信する両方のエンドポイントを登録する必要があります。ClusterMesh とホストネットワーク Pod は対象外です。リリースガイドによると、HBONE ポート 15008 を対象とする場合を除き、通常の L4 ポリシーはこの経路では機能しません。CA とブートストラップにも独自の要件がある、別のデプロイ方式です。

このベータ方式を採用する前に、[セキュリティガイド](03-security.md)と、リリースのセキュリティモデルおよび制限を確認してください。ルーティング、認証、認可、暗号化は、それぞれ別の要件として扱います。

Cilium は Istio 環境の基盤 CNI としても利用できます。ただし、ネットワークの統合によって両製品の認証方式が相互に置き換え可能になるわけではありません。モード固有のソケット負荷分散、CNI の共存、L7 ポリシーの管理主体を確認してください。

## 機能と実測費用の比較

| 項目 | Cilium | Istio | Linkerd |
|---|---|---|---|
| データプレーンモデル | eBPF と、選択された L7 処理用の共有 Envoy | サイドカーモード、または ambient の ztunnel／waypoint | ネイティブサイドカー配置を含む Pod ごとのプロキシ |
| Pod ネットワーク | モードに応じて CNI を提供、またはチェイニング | 基盤となる Pod ネットワークが必要。CNI がメッシュ通信をリダイレクト | 基盤となる Pod ネットワークが必要。任意の CNI がメッシュ通信をリダイレクト |
| ポリシー | Kubernetes／Cilium のネットワークポリシーと L7 機能 | 別のネットワークポリシー層を伴うメッシュ認可とルーティング | Server／Route の認可と送信ルーティング。L4 専用ポリシーではない |
| Gateway API | オプトインのコントローラーと、文書化された適合性および機能 | Gateway とメッシュルーティングの役割 | Service または Server を親として指定するルートに対応 |
| セキュリティ | 帯域外認証と別の暗号化。制限のある ztunnel mTLS ベータ版も別途提供 | ワークロードメッシュの mTLS とポリシー | ワークロードメッシュの mTLS とポリシー |

ワークロードや設定を問わずに成り立つ CPU、メモリー、レイテンシーの優劣はありません。以前掲載されていたノード別／Pod 別の固定値や 100 Pod のメモリー図は、出典が確認できるベンチマークではなく、コンポーネント、ノード数、ワークロードの詳細も示していませんでした。エージェントやプロキシ、コントローラー、テレメトリー、ID 基盤を含め、同じ基準構成からの増分コストを実測して比較してください。

Cilium のネットワークモデルと必要な L7 機能が環境に合う場合、特にすでに運用している場合には有力な選択肢になります。CNI 移行、カーネルとプラットフォームの対応状況、共有ノード障害の影響、セキュリティ要件、既存ポリシーへの依存を評価してください。「サイドカーなし」も「eBPF」も、金融やリアルタイムのワークロードで目標のレイテンシーやコストを達成できる証拠にはなりません。

機能の境界を広く比較するには、継続的に更新されている[サービスメッシュ比較](../istio/comparison/01-service-mesh-comparison.md)を参照してください。

## バージョンとプラットフォームの前提条件

選択したリリースでは、次の点を確認してください。

- 一般的な Kubernetes の e2e 互換性リストは **1.33～1.36** です。リリースの EKS CI ファイルが列挙するのは **1.33～1.35** で、デフォルトは 1.35 です。これは別々の根拠です。より新しいバージョンやプロバイダーのリストにない組み合わせは、個別に検証してください。
- Helm チャートの緩い制約 `kubeVersion >=1.21.0-0` は、テスト済みのサポート対象を示すものではありません。Kubernetes の新しいリリースが自動的にサポート対象になるわけでもありません。
- ホストには、対応する AMD64／AArch64 の Linux と、通常はカーネル 5.10 以降が必要です。文書化された同等のバックポートも利用できます。L7 リダイレクトなどの高度な機能には、追加のカーネルやモジュール要件があります。
- この Cilium リリースで参照される Gateway API は **v1.6.3** です。変更前に必須／任意 CRD と 1.20 の TLSRoute 更新時の注意事項を確認してください。互換性を確認せず、最新のカタログバージョンに置き換えないでください。

```bash
cilium version --client
cilium version
cilium status --wait --wait-duration 5m
kubectl -n kube-system get daemonset cilium
# For the dedicated Envoy mode selected below:
kubectl -n kube-system get daemonset cilium-envoy
```

CLI 自体のバージョンと稼働中の Cilium イメージのバージョンは、別々の情報です。ステータス出力全体とエラーを保存してください。出力を `grep` して「Envoy」や「Hubble」という文字列が見つかっても、準備完了の証明にはなりません。組み込みモードでは、専用 Envoy DaemonSet が存在しないのが想定どおりの場合があります。

### EKS へのインストール方式

| モード/プラットフォーム | 必要な区別 |
|---|---|
| Cilium AWS ENI モード | Cilium が ENI の IPAM とネイティブルーティングを管理します。IAM、ルーティング、ノードと Pod の登録を計画してください。Cilium 1.20.3 の一般的な ENI リファレンスは IPv6 ベータ版を説明していますが、EKS のインストールページは引き続き IPv4 のみとしています。ここでは IPv4 の例を使い、プラットフォーム固有の IPv6 要件とサポート状況を別途確認してください。 |
| AWS VPC CNI チェイニング | AWS VPC CNI がインターフェイスと IPAM を引き続き管理し、Cilium が後段にデータパスを接続します。高度な L7 機能と IPsec の制約を評価してください。 |
| EKS Fargate | 代替 CNI はサポートされません。AWS VPC CNI が必要です。 |
| EKS Auto Mode | 代替 CNI とネットワークポリシープラグインはサポートされません。 |
| EKS Hybrid Nodes | EC2 ENI の説明を当てはめず、AWS が個別に示す Cilium のバージョン、設定、機能のガイダンスに従ってください。 |

EC2 ノードの CNI について AWS がサポートするのは Amazon VPC CNI に限られます。互換性のある別の CNI には、その CNI 独自の運用サポートやベンダーサポートが必要です。Hybrid Nodes の別個のサポート範囲を、一般的な Cilium 互換性表から推測しないでください。

Helm の1行コマンドだけでは、既存の AWS VPC CNI クラスターを移行できません。API への初期接続、kube-proxy の置き換え、CNI の管理主体、IAM、ノード準備用の taint、既存の未管理 Pod の再作成について、検証済みの手順を用意してください。このレビューでは、クラスターの作成や CNI の置き換えは行っていません。

## 選択した機能を有効にする

Cilium が適切にインストール済みの場合は、次の機能オーバーレイを `cilium-mesh-features.yaml` として保存します。

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

L7 機能を制御する正式なフラグは `l7Proxy` であり、`proxy.enabled` では代用できません。チャートを直接検証したところ、`proxy.enabled:false` では L7 機能が有効のままになり、`l7Proxy:false` で無効になりました。

```bash
set -euo pipefail
umask 077
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
# Preview only: reviewed-cni-values.yaml must describe the existing intended CNI mode.
helm template cilium cilium/cilium --version 1.20.3 \
  --namespace kube-system --kube-version 1.35.0 \
  -f reviewed-cni-values.yaml -f cilium-mesh-features.yaml \
  > cilium-mesh-rendered.yaml
```

これは互換性のある Kubernetes バージョンを指定したプレビューで、インストール時にレビュー済みの CNI values と機能設定をマージします。出力を確認し、既存の管理主体のもとで、そのリリースがサポートするアップグレード手順に従ってください。これは CNI の完全なインストール手順でも、ネットワークモードを変更する許可でもありません。

| 任意機能 | 追加要件 |
|---|---|
| Gateway API | kube-proxy の置き換え、L7 プロキシ、必須の v1.6.3 CRD、適切なロードバランサーまたはホストネットワーク設計 |
| Ingress コントローラー | サポートされる設定と公開方式が必要です。自動的にすべてのメッシュ通信を処理するわけではありません。 |
| Hubble メトリクス | 対象のメトリクス群と設定済みのコレクターが必要です。Relay と UI だけでは Prometheus は作成されません。 |
| 相互認証 | ベータ機能のレビューと明示的な有効化、SPIRE、ストレージ、接続性、該当する認証ポリシーが必要です。暗号化は別途評価してください。 |

**ベータ版の認証機能を隔離環境で評価する場合**は、以前の例に欠けていた最上位のフラグを含める必要があります。

```yaml
authentication:
  enabled: true
  mutual:
    spire:
      enabled: true
      install:
        enabled: true
```

チャートは `authentication.enabled:true` がなければ SPIRE 統合を拒否します。同梱の SPIRE サーバーはデフォルトで永続ストレージを使うため、適切な PVC のプロビジョニングが前提です。この設定例だけで、本番環境のセキュリティ、クラスター間認証、アプリケーション通信の暗号化が実現するわけではありません。

## L7 ポリシーと観測の例

`bookinfo` 名前空間に、`app:productpage` ラベルを持つ Cilium 管理下の HTTP アプリケーションと、`app:frontend` ラベルを持つ Cilium 管理下のクライアントを用意します。Bookinfo を使う場合は、必要な依存アプリケーションもすべてデプロイしてください。productpage の Deployment だけでは Bookinfo アプリケーション全体になりません。検証済みのイメージを使い、アプリケーションに適した readiness 設定を用意します。

次のポリシーは該当するエンドポイントを選択し、記載したクライアント、メソッド、パスの組み合わせを許可します。このポリシーは、どちらのワークロードも作成しません。

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

ポリシーの管理者を通じて適用する前に、ほかのポリシーと、想定されるデフォルト拒否の影響を評価してください。この例が許可するのは2つのパスだけで、ブラウザー操作全体に必要な静的アセットや依存先すべてを許可するものではありません。認証と暗号化は、この L7 許可ルールとは別の要件です。

```bash
# Keep this terminal running; configure the intended kube context first.
cilium hubble port-forward --port-forward 4245

# In another terminal, use the selected Hubble CLI:
hubble status --server localhost:4245
hubble observe --server localhost:4245 --namespace bookinfo --protocol http --follow
# Service-name filters are an alternative to --namespace in this CLI.
hubble observe --server localhost:4245 --to-service bookinfo/productpage
```

選択した Hubble CLI では、`--namespace` と `--to-service` を同時に指定できません。名前空間を指定した観測か、名前空間を含む Service 名のどちらかを使います。L7 の記録には、ポリシーに一致する実際の通信とプロキシの可視性が必要です。L7 プロキシより前で破棄された通信を調べるには、フローや破棄をより広く確認する必要があります。フローが観測されないからといって、アプリケーション経路が許可、拒否、または正常であるとは証明できません。

## ガイドの構成と参考資料

| ガイド | 範囲 |
|---|---|
| [アーキテクチャ](01-architecture.md) | データパス、Envoy、API モデル |
| [トラフィック管理](02-traffic-management.md) | ルーティングと負荷分散 |
| [セキュリティ](03-security.md) | ポリシー、認証、暗号化の境界 |
| [可観測性](04-observability.md) | Hubble とメトリクス |
| [Ingress／Gateway](05-ingress-gateway.md) | 外部トラフィックと Gateway API |
| [ベストプラクティス](06-best-practices.md) | 運用、移行、検証 |

- [リリースの Kubernetes 互換性](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/kubernetes/compatibility.rst)
- [システム要件](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/operations/system_requirements.rst)
- [Istio と Cilium のネットワーキング](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/servicemesh/istio.rst)
- [Envoy のモード](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/network/proxy/envoy.rst)
- [相互認証の制限](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
- [Gateway API の前提条件](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/servicemesh/gateway-api/installation.rst)
- [EKS ENI の要件](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/installation/requirements-eks.rst)と[AWS VPC CNI のチェイニング](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/installation/cni-chaining-aws-cni.rst)
- [EKS代替CNI](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)と[Hybrid Nodes CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Cilium 1.20.3 ENI IPAM／IPv6 ベータ版](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/eni.rst)
