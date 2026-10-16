# パート 1: はじめに

> **レビュー済みベースライン**: Cilium 1.20.2 / Cilium CLI 0.20.1 / Hubble CLI 1.20.2。**最終更新**: October 15, 2026

## ラボ環境のセットアップ

分離され、準備済みの Kubernetes 環境を使用してください。Cilium 1.20 では、Kubernetes **1.33–1.36** がテスト済みとして記載されています。Node には、カーネル **5.10+** を備えた AMD64/AArch64 Linux、または RHEL 8.10 のバックポートされた 4.18 カーネルなど、文書化された同等の環境が必要です。kind/minikube の VM またはコンテナはその Node/VM のカーネルを使用します。ワークステーションの OS 名だけでは互換性は判断できません。機能固有の要件も引き続き適用されます。

API server と同じマイナーバージョン内の kubectl を使用してください。[メインガイド](README.md)に記載されているとおり、適切な OS/アーキテクチャ向けの Cilium CLI および Hubble CLI アセットを、チェックサム検証付きでインストールします。Helm は設定をレンダリング/レビューできます。監査では Helm 3.21.3 を使用しました。未検証の `latest` AMD64 ダウンロードを繰り返したり、各章でリリースを再インストールしたりしないでください。

### 選択したプロファイルで一度だけインストールする

EKS ENI、VPC CNI chaining、および通常の cluster-pool 設定では前提条件が異なります。[メインガイド](README.md)を参照してください。次のラボ値は、kube-proxy と DNS がすでに動作し、準備済みの CNI オーナーが 1 つある場合の、**通常の IPv4 cluster-pool の代替案**です。これは EKS 移行のレシピではありません。Pod CIDR が Service、Node、または接続済みネットワークの範囲と重複していないことを確認してください。

`cilium-lab-values.yaml` として保存します:

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
cilium install --context "$CILIUM_LAB_CONTEXT" --version 1.20.2 \
  --values cilium-lab-values.yaml
cilium status --context "$CILIUM_LAB_CONTEXT" --wait
```

Cilium がすでにインストールされている場合は、バージョン/設定を確認し、そのオーナーのアップグレードプロセスに従ってください。インストール/ステータスコマンドおよび後述の接続テストは、本番環境との互換性を示す証拠ではありません。この監査では cluster はプロビジョニングされていません。

## Cilium とは

Cilium は、Linux eBPF dataplane と Kubernetes 統合を通じて、ネットワーキング、セキュリティ、オブザーバビリティを提供します。endpoint policy、モード依存の IPAM/routing、Service 処理、および Hubble flow の可視化を提供します。Docker libnetwork 統合は 1.20 で削除されました。Kubernetes、Docker、Mesos を、現在の相互交換可能なインストール対象として扱うべきではありません。

### コアコンポーネントと機能

| コンポーネント / 機能 | 役割と適用条件 |
| --- | --- |
| Cilium Agent | Node ごとの endpoint および dataplane 管理。すべての host/networking 機能を所有するわけではありません |
| Cilium Operator | cluster レベルの割り当て/identity/controller 処理。複数 replica がサポートされ、該当する場合は leader election が行われます。レビュー済み chart のデフォルトは 2 replica です |
| eBPF | 検証および機能要件の対象となる kernel hook 上の program/map。パフォーマンスは測定する必要があります |
| L3/L4 および L7 policy | L7 にはサポートされる Envoy/DNS proxy パスが必要です。Kafka 対応 L7 policy は 1.20 で削除されましたが、L4 rule は引き続き Kafka 接続を制御できます |
| kube-proxy replacement | 任意の Service 処理。DSR、Maglev、XDP にはそれぞれ固有の設定/topology 制約があります |
| Encryption | `encryption.type` は `ipsec`、`wireguard`、または beta の `ztunnel` を選択します。ztunnel workload mTLS には、固有の enrollment、bootstrap、traffic、policy の前提条件があります |
| Hubble | network/proxy flow の観測および service map。自動的な end-to-end application tracing ではありません |
| ClusterMesh / BGP | ClusterMesh には identity、trust、network reachability が必要です。BGP は route を広告しますが、内部 cluster routing をプログラムするものではありません |

コンポーネントの関係は次のとおりです。kubelet は **CRI** を通じて Pod sandbox 操作をリクエストし、container runtime は設定済みの **CNI plugin** を呼び出し、Cilium は endpoint セットアップを調整して agent が dataplane をプログラムします。CNI はパケットごとの forwarding hop ではありません。Envoy は設定された L7 proxy traffic を処理し、Hubble は Prometheus metric scraping とは別に flow event を公開します。

### セキュリティ identity

セキュリティ identity とは、関連する割り当てスコープ内で endpoint の **security-relevant label set** に割り当てられる数値 identifier です。これらの label はフィルタリング/設定され、namespace 由来の label を含む場合があります。同じ `app` label だけでは、namespace や cluster をまたいで同じ identity が保証されません。数値 ID は、永続的でグローバルに意味を持つ hash でも Pod IP でもありません。ほかの endpoint type も identity を使用します。

## コンテナネットワーキングの基本

Host networking は host network namespace を共有します。bridge は host 上の interface を接続し、overlay は underlay を越えて traffic をカプセル化します。native routing は、underlay が Pod address に到達できることに依存します。これらの概念は共存でき、eBPF 実装と Netfilter 実装の選択と混同すべきではありません。

運用上の論点には、address capacity、routing/MTU、Service の挙動、tenant policy、オブザーバビリティ、および障害復旧が含まれます。network model だけでパフォーマンスやセキュリティが決まるわけではありません。

## CNI を理解する

CNI は、container network 設定のための CNCF の仕様/library/plugin エコシステムです。plugin は JSON で設定/結果を交換し、IP address の割り当てを IPAM plugin に委任できます。CNI のセットアップ/削除契約は、kubelet が container runtime と通信するために使用する CRI とは異なります。Kubernetes 1.24 以降、kubelet は削除された `--network-plugin`/`--cni-bin-dir` 設定 flag を所有しなくなりました。

| プロジェクト | 関連する相違点 |
| --- | --- |
| Cilium | Linux eBPF dataplane、複数の routing/IPAM モード、proxy 支援の L7 policy、および Hubble |
| Calico | Linux Iptables/Nftables/BPF とサポート対象の Windows HNS、OSS WireGuard、staged policy、および別途設定する L7 統合 |
| Flannel | VXLAN/host-gw/WireGuard などの connectivity backend。policy は任意の chart controller または別の実装で提供できます |
| AWS VPC CNI | VPC address allocation/networking、サポート対象の EC2 Linux Node 上の native policy、および独立した SG-for-Pods control |
| Weave Net | 元の `weaveworks/weave` repository は archive されています。これを歴史的な選択肢として扱い、提案する保守済み distribution は個別に確認してください |

サポート境界については[現在の比較](README.md)を参照してください。無制限の Kubernetes 互換性や「very high/high/medium」のパフォーマンス順位を deployment の証拠として使用しないでください。Service mesh は任意の統合であり、通常の Pod networking の前提条件ではありません。

## ラボ: スコープを限定した L4 policy

選択した context と専用の namespace を使用してください。この例は policy を定義するものであり、application server や client image をデプロイするものではありません。承認済みの image/tool を使用して、controller 管理のテスト workload を準備してください:

- TCP 8080 で listen する、`app=backend` label を持つ backend Pod。
- `app=frontend` label を持つ frontend Pod と、別の label を持つ別の client。いずれも適切なテスト client を備えていること。
- 通常の管理対象 Pod interface、default label 処理、既知の DNS/Service 設定、および意図した分離を無効にする、ほかに一致する allow policy がないこと。

namespace 定義を `cilium-intro-namespace.yaml` として保存して適用し、その後テスト workload を準備してください:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cilium-intro-demo
```

```bash
kubectl --context "$CILIUM_LAB_CONTEXT" apply -f cilium-intro-namespace.yaml
```

次の policy を `cilium-intro-policy.yaml` として保存します:

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

これらの前提条件が満たされ、ほかに一致する allow がない場合、想定される **通常の Pod 間 ingress** の結果は次のとおりです:

| 送信元 / 宛先 | 想定される結果 |
| --- | --- |
| 同一 namespace の frontend → backend TCP 8080 | 許可 |
| 別の client label → backend TCP 8080 | 拒否 |
| Frontend → backend の別の port/protocol | この policy では許可されない |
| 別の namespace からの同一 app label | この policy では許可されない |

policy の実現後に、肯定的および否定的な接続の両方を検証してください。ほかの allow/deny policy、host traffic、probe によって、有効な結果が変わる場合があります。この ingress rule は frontend egress を制限せず、HTTP method/path filtering も提供しません。API の受け入れが enforcement と等しいと想定するのではなく、実際の traffic と endpoint state を確認してください。

`cilium connectivity test` は、workload と policy を作成する追加のテスト runner です。必要な permission を備えた、レビュー済みのテスト環境でのみ実行してください。これは read-only status コマンドではありません。別の performance runner には `cilium connectivity perf` を使用し、benchmarking の際は実際の version/topology/result を保存してください。

## 参考資料と次のステップ

- [Cilium requirements and setup](README.md)
- [CNI project](https://github.com/containernetworking/cni)
- [Kubernetes network plugins and runtime ownership](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes client version skew](https://kubernetes.io/releases/version-skew-policy/)
- [Cilium identities and terminology](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/gettingstarted/terminology.rst)
- [Original Weave repository metadata](https://api.github.com/repos/weaveworks/weave)

[eBPF](02-ebpf.md)に進むか、[Introduction Quiz](../../quizzes/networking/cilium/01-introduction-quiz.md)で理解度を確認してください。
