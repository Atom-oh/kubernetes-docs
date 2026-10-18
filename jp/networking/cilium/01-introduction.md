# パート 1: はじめに

> **レビュー済みのベースライン**: Cilium 1.20.3 / Cilium CLI 0.20.1 / Hubble CLI 1.20.2。**最終更新日**: 2026年10月16日

## ラボ環境のセットアップ

分離され、準備済みの Kubernetes 環境を使用してください。Cilium 1.20 でテスト済みの Kubernetes バージョンは **1.33～1.36** です。ノードには AMD64／AArch64 の Linux と **5.10 以降**のカーネルが必要です。または、RHEL 8.10 のバックポート済み 4.18 カーネルなど、ドキュメントに記載された同等環境を使用できます。kind／minikube の VM やコンテナでは、ワークステーションの OS 名ではなく、ノード／VM のカーネルが使われます。機能ごとに追加要件がある場合もあります。

kubectl のバージョンは API サーバーのバージョンから 1 マイナーバージョン以内にしてください。[メインガイド](README.md)に従い、OS／アーキテクチャに合う Cilium CLI と Hubble CLI のアセットを、チェックサムを検証してインストールします。Helm を使って設定をレンダリングし、レビューできます。この監査では Helm 3.21.3 を使用しました。AMD64 用の `latest` を未検証のままダウンロードしたり、各章でリリースを再インストールしたりしないでください。

### 選択したプロファイルで一度だけインストールする

EKS ENI、VPC CNI chaining、通常の cluster-pool 構成では前提条件が異なります。[メインガイド](README.md)を参照してください。以下のラボ値は、kube-proxy と DNS がすでに動作しており、CNI の管理主体が 1 つ用意された環境で使う**通常の IPv4 cluster-pool の代替構成**です。EKS 移行手順ではありません。Pod CIDR が Service、ノード、接続済みネットワークの範囲と重複しないことを確認してください。

`cilium-lab-values.yaml` として保存します。

```yaml
routingMode: tunnel
tunnelProtocol: vxlan
kubeProxyReplacement: false
ipv4:
  enabled: true
ipv6:
  enabled: false
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
hubble:
  enabled: true
  relay:
    enabled: true
  ui:
    enabled: true
  metrics:
    enabled:
    - dns
    - drop
    - tcp
    - flow
    - icmp
    - httpV2
```

```bash
CILIUM_LAB_CONTEXT=replace-with-nonproduction-context
kubectl --context "$CILIUM_LAB_CONTEXT" get nodes -o wide
cilium version --client

# Fresh installation only, after preparing the cluster/CNI ownership and values.
cilium install --context "$CILIUM_LAB_CONTEXT" --version 1.20.3 \
  --values cilium-lab-values.yaml
cilium status --context "$CILIUM_LAB_CONTEXT" --wait
```

すでに Cilium がインストールされている場合は、バージョンと設定を確認し、所有者のアップグレード手順に従ってください。インストール／状態確認コマンドや後続の接続テストは、本番互換性の証拠にはなりません。この監査のためにクラスターはプロビジョニングしていません。

## Cilium とは？

Cilium は、Linux の eBPF データプレーンと Kubernetes 統合を通じて、ネットワーキング、セキュリティ、可観測性を提供します。エンドポイントポリシー、動作モードに応じた IPAM／ルーティング、Service 処理、Hubble によるフロー可視化を提供します。Docker libnetwork 統合は 1.20 で削除されました。Kubernetes、Docker、Mesos を現在のインストール対象として同列に扱わないでください。

### 主なコンポーネントと機能

| コンポーネント／機能 | 役割と条件 |
| --- | --- |
| Cilium Agent | ノードごとのエンドポイントとデータプレーンを管理します。ホスト／ネットワーク機能のすべてを管理するわけではありません。 |
| Cilium Operator | クラスター単位の割り当て、identity、コントローラー処理を担います。複数レプリカに対応し、該当する場合はリーダー選出を使います。確認済みのチャートでは既定で 2 レプリカです。 |
| eBPF | カーネルフックにプログラムと map を配置します。検証要件や機能要件があり、性能は測定が必要です。 |
| L3/L4 および L7 ポリシー | L7 には、サポートされる Envoy／DNS proxy 経路が必要です。Kafka を認識する L7 ポリシーは 1.20 で削除されましたが、L4 ルールは引き続き Kafka 接続を制御できます。 |
| kube-proxy 置き換え | 任意の Service 処理方式です。DSR、Maglev、XDP にはそれぞれ構成やトポロジー上の制約があります。 |
| 暗号化 | `encryption.type` は `ipsec`、`wireguard`、またはベータ版の `ztunnel` を選択します。ztunnel によるワークロード mTLS には、参加登録、ブートストラップ、トラフィック、ポリシーごとの前提条件があります。 |
| Hubble | ネットワーク／proxy のフロー観測とサービスマップを提供します。エンドツーエンドのアプリケーショントレースを自動で行うものではありません。 |
| ClusterMesh／BGP | ClusterMesh には identity、信頼関係、ネットワーク到達性が必要です。BGP は経路を広告しますが、クラスター内部のルーティングを設定するものではありません。 |

コンポーネント間の関係は次のとおりです。kubelet は **CRI** を通じて Pod sandbox 操作を要求し、コンテナランタイムは設定された **CNI plugin** を呼び出します。Cilium はエンドポイントの設定を調整し、agent がデータプレーンをプログラムします。CNI はパケットごとの転送ホップではありません。Envoy は設定された L7 proxy トラフィックを処理し、Hubble は Prometheus のメトリクス収集とは別にフローイベントを公開します。

### セキュリティ identity

セキュリティ identity は、該当する割り当て範囲内で、エンドポイントの**セキュリティに関係するラベル集合**に割り当てられる数値 ID です。ラベルはフィルタリング／設定され、namespace 由来のラベルが含まれることがあります。同じ `app` ラベルだけでは、namespace やクラスターをまたいで同じ identity になるとは限りません。この数値 ID は、永続的でグローバルな意味を持つ hash でも Pod IP でもありません。他の種類のエンドポイントにも identity が使われます。

## コンテナネットワーキングの基礎

ホストネットワーキングでは、コンテナはホストのネットワーク namespace を共有します。bridge はホスト上のインターフェイスを接続し、overlay は underlay 上でトラフィックをカプセル化します。ネイティブルーティングでは、underlay が Pod アドレスに到達できる必要があります。これらの概念は共存する場合があり、eBPF と Netfilter のどちらを実装に選ぶかとは区別してください。

運用上は、アドレス容量、ルーティング／MTU、Service の動作、テナントポリシー、可観測性、障害復旧を検討します。ネットワークモデルだけで性能やセキュリティが決まるわけではありません。

## CNI の理解

CNI はコンテナネットワーク構成に関する CNCF の仕様／ライブラリ／plugin のエコシステムです。plugin は JSON 形式で設定／結果を交換でき、アドレス割り当てを IPAM plugin に委譲できます。CNI によるセットアップ／削除の契約は、kubelet がコンテナランタイムと通信するための CRI とは別です。Kubernetes 1.24 以降、kubelet は削除された `--network-plugin`／`--cni-bin-dir` 設定フラグを管理しません。

| プロジェクト | 関連する違い |
| --- | --- |
| Cilium | Linux eBPF データプレーン、複数のルーティング／IPAM モード、proxy を介した L7 ポリシー、Hubble |
| Calico | Linux の Iptables／Nftables／BPF と、サポート対象の Windows HNS。OSS WireGuard、段階的なポリシー、別途設定する L7 統合 |
| Flannel | VXLAN／host-gw／WireGuard などの接続 backend。任意のチャートコントローラー、または別実装でポリシーを提供できます。 |
| AWS VPC CNI | VPC のアドレス割り当て／ネットワーキング。サポート対象の EC2 Linux ノードでのネイティブポリシーと、別個の Pod 用 Security Group 制御 |
| Weave Net | 元の `weaveworks/weave` リポジトリはアーカイブ済みです。歴史的な選択肢として扱い、保守されている配布物を提案する場合は別途確認してください。 |

サポート範囲は[現在の比較表](README.md)を参照してください。Kubernetes との互換性を無条件に広くうたう説明や、「非常に高い／高い／中程度」といった性能ランキングを、デプロイの根拠にしないでください。Service Mesh は任意の統合機能であり、通常の Pod ネットワーキングの前提ではありません。

## ラボ: 範囲を限定した L4 ポリシー

選択した context と専用 namespace を使います。この例はポリシーを定義するだけで、アプリケーションサーバーやクライアントのイメージをデプロイしません。承認済みイメージを使い、コントローラーが管理するテストワークロードを準備してください。

- TCP 8080 をリッスンする、`app=backend` ラベル付きの backend Pod。
- `app=frontend` ラベル付きの frontend Pod と、異なるラベルを持つ別のクライアント。どちらにも適切なテストクライアントを用意します。
- 通常の管理対象 Pod インターフェイス、既定のラベル処理、既知の DNS／Service 構成を使用します。意図した分離を無効にする他の一致許可ポリシーがないことも確認してください。

namespace 定義を `cilium-intro-namespace.yaml` として保存し、適用した後でテストワークロードを準備します。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cilium-intro-demo
```

```bash
kubectl --context "$CILIUM_LAB_CONTEXT" apply -f cilium-intro-namespace.yaml
```

以下のポリシーを `cilium-intro-policy.yaml` として保存します。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-frontend-backend
  namespace: cilium-intro-demo
spec:
  endpointSelector:
    matchLabels:
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: cilium-intro-demo
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
```

```bash
kubectl --context "$CILIUM_LAB_CONTEXT" get pods -n cilium-intro-demo --show-labels
kubectl --context "$CILIUM_LAB_CONTEXT" apply -f cilium-intro-policy.yaml
kubectl --context "$CILIUM_LAB_CONTEXT" get cnp -n cilium-intro-demo
```

これらの前提を満たし、一致する許可ポリシーが他にない場合に期待される**通常の Pod 間 ingress** の結果は次のとおりです。

| 送信元／宛先 | 期待される結果 |
| --- | --- |
| 同一 namespace の frontend → backend TCP 8080 | 許可 |
| 別のクライアントラベル → backend TCP 8080 | 拒否 |
| frontend → backend の別ポート／プロトコル | このポリシーでは許可されない |
| 別 namespace の同じ app ラベル | このポリシーでは許可されない |

ポリシーが適用されたことを確認した後、許可される接続と拒否される接続の両方を検証してください。他の許可／拒否ポリシー、ホストトラフィック、probe によって実際の結果が変わる場合があります。この ingress ルールは frontend の egress を制限せず、HTTP メソッド／パスによるフィルタリングも行いません。API がポリシーを受理したことを強制適用の証拠とみなさず、実際のトラフィックとエンドポイントの状態を調べてください。

`cilium connectivity test` は、ワークロードとポリシーを作成する追加のテストランナーです。必要な権限がある、レビュー済みのテスト環境でのみ実行してください。読み取り専用の状態確認コマンドではありません。性能測定には別のランナー `cilium connectivity perf` を使い、ベンチマーク時の実際のバージョン／トポロジー／結果を記録してください。

## 参考資料と次のステップ

- [Cilium の要件とセットアップ](README.md)
- [CNI プロジェクト](https://github.com/containernetworking/cni)
- [Kubernetes のネットワークプラグインとランタイムの責務](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes クライアントのバージョン差](https://kubernetes.io/releases/version-skew-policy/)
- [Cilium identity と用語](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/gettingstarted/terminology.rst)
- [Weave 元リポジトリのメタデータ](https://api.github.com/repos/weaveworks/weave)

[eBPF](02-ebpf.md) に進むか、[はじめにのクイズ](../../quizzes/networking/cilium/01-introduction-quiz.md)で理解度を確認してください。
