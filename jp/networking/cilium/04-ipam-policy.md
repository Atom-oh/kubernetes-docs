# IPAM とネットワークポリシー

> **レビュー基準**: Cilium 1.20.2、Kubernetes 1.33～1.36 でテスト済み。リソース API バージョンおよびプラットフォーム要件は別途確認しています。
> **最終更新**: October 15, 2026

## ラボ環境のセットアップ

[インストールプロファイル](README.md)および[ネットワーク前提条件](03-networking.md)を使用して、使い捨ての Linux クラスターを準備します。kubectl はサポート対象の API サーバーのバージョンスキュー内に維持してください。以下の IPAM プロファイルは、インストールまたは文書化された移行のための代替手段であり、稼働中クラスターに順番に適用する ConfigMap の切り替えではありません。

ポリシーラボでは、ポリシーとラベルが一致しなかった従来の Cilium 1.14 Star Wars マニフェストを置き換え、専用の namespace と以下の対応する workload を使用します。まず、既存の Kubernetes/Cilium クラスター全体のポリシーおよび admission 設定を確認してください。新しい namespace でそれらを上書きすることはできません。

```bash
cilium status --wait
kubectl -n kube-system get configmap cilium-config -o yaml
kubectl get ciliumnodeconfigs --all-namespaces -o yaml
helm -n kube-system get values cilium --all
```

異なる場合は実際の namespace/release 名を使用してください。目的の Helm values と ConfigMaps、node オーバーライド、operator 設定、および実現済み agent 状態は、それぞれ異なる問いに答えるものです。`ipam` を含む grep 結果だけでは、有効な設定を完全に確認できません。

## IP アドレス管理戦略

Cilium Pod IPAM は workload アドレスを割り当てます。Kubernetes は Service **ClusterIPs** を割り当てます。Cilium **LoadBalancer IPAM** は LoadBalancer アドレスのための別機能です。`CiliumPodIPPool` は Service ClusterIPs を割り当てません。

### アロケーターと権威ある状態

| 設定 | node 容量 / Pod IPs を割り当てるのは誰か？ | 確認する状態 |
|---|---|---|
| `cluster-pool`（汎用デフォルト） | Cilium Operator が node ごとの CIDRs を割り当て、各 agent がローカルアドレスを割り当てる | `CiliumNode.spec.ipam.podCIDRs` および operator 状態 |
| `kubernetes` / host scope | Kubernetes が node PodCIDRs を提供し、各 agent がその範囲内で割り当てる | Kubernetes `Node.spec.podCIDRs` / `spec.podCIDR` およびサポート対象 provider annotations |
| `multi-pool` | Operator が agent の要求に応じて名前付き pool から block を割り当て、agent が Pod IPs を割り当てる | `CiliumPodIPPool`、`CiliumNode.spec.ipam.pools.requested` / `allocated` |
| `crd` | 外部アロケーターが使用可能なアドレスを提供し、agent がそれらを消費/解放する | `CiliumNode.spec.ipam.pool` / `status.ipam.used`（および該当する IPv6 fields） |
| `eni` | Operator が AWS ENIs/IPs/prefixes を管理し、agent が interface 状態を自身の multi-pool allocator に変換する | `CiliumNode.status.eni.enis` およびモード固有の pool/demand 状態 |
| `azure` | 自己管理 Azure VM/VMSS クラスター向けの upstream operator/agent 統合 | Azure/CiliumNode 割り当て状態 |
| `delegated-plugin` | Cilium CNI が、managed AKS の Azure IPAM など別の IPAM plugin を呼び出す | Provider/plugin 状態。upstream Azure IPAM 設定で代用しないこと |
| GKE 統合 | Upstream GKE 統合は host-scope `kubernetes` IPAM を使用し、managed Dataplane V2 には独自の所有権がある | Provider 設定および Node CIDRs。別個の `gke` IPAM value ではない |

cluster-pool と Kubernetes host scope はどちらも個々の Pod アドレスをローカルで割り当てます。違いは、**node prefixes** を誰が割り当てるかです。どちらも協調を不要にするものではなく、ユーザー提供の pool が VPC、node network、Service range、または別クラスターと重複しないことを保証するものでもありません。

リリース済みの CRD/type 定義では、汎用的な CRD ベース割り当てに `pool` と `used` を使用します。一部の解説ドキュメントでは依然として `available`/`inuse` と記載されています。これらの古い名前をコピーするのではなく、インストール済みの schema とモード固有の fields を使用してください。1.20.2 の ENI は interface/multi-pool パスを使用するため、汎用 CRD ベース fields はその普遍的な信頼できる情報源ではありません。

### Kubernetes/CNI 統合

kubelet は container runtime を通じて Pod sandbox 操作を要求し、CNI 対応 runtime が Cilium CNI plugin を呼び出します。割り当ては選択した backend に依存し、その後 plugin/agent が endpoint network を設定します。host-scope モードでは、Kubernetes が必要なアドレスファミリー CIDRs を提供する必要があります。たとえば、正しく構成された node-CIDR allocator を介して提供します。

## IPAM 設定

これらは対応するインストールプロファイルにマージする **Helm value fragments** です。まず Pod/Service/node/external アドレス範囲を確認してください。

### Cluster Pool

**`cluster-pool-values.yaml`**

```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
ipv4:
  enabled: true
ipv6:
  enabled: false
```


Operator は node block を協調しますが、各 Pod アドレスに対して中央要求を行うわけではありません。`clusterPoolIPv4PodCIDRList` の複数 CIDRs は共通の割り当て空間を拡張します。これは workload ごとに名前付き pool を選択することとは異なります。

稼働中クラスターを拡張するために、既存の pool-list entries を置き換えないでください。文書化された拡張手順で、競合しない CIDR を追加してください。node mask size は通常変更可能な設定ではありません。block あたりのアドレス数は、アドレスが予約されたり node-local facilities に使用されたりするため、使用可能な Pod 容量と同一ではありません。

すでに Kubernetes/Cilium dual stack 用に準備済みのクラスターの場合:

**`dual-stack-values.yaml`**

```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
    clusterPoolIPv6PodCIDRList:
    - fd00:10:244::/104
    clusterPoolIPv6MaskSize: 120
ipv4:
  enabled: true
ipv6:
  enabled: true
```


この 2 つの Cilium アドレスファミリー flags を有効にしても、Kubernetes Service CIDRs、underlay IPv6 接続性、または cloud support が単独で設定されるわけではありません。

### Multi-Pool と CiliumPodIPPool

文書化されたモードは `multi-pool` です。リソース API は 1.20 では依然として `cilium.io/v2alpha1` です（**[1.21 pre-release]** では `CiliumPodIPPool` は `cilium.io/v2` として提供され、これが storage version となり、`v2alpha1` は非推奨となり、`spec.ipv4.pool`/`spec.ipv6.pool` に CIDR ごとの `reservedRanges` が追加されます。これらの fields は `v2` にのみ存在します）。機能の成熟度を、その API suffix だけから推測しないでください。upstream multi-pool tutorial には `kubeProxyReplacement=true` および `bpf.masquerade=true` も必要です（iptables masquerade には `egressMasqueradeInterfaces` が必要です）。以下の例にはこれらを含めています。割り当ての内部動作、pool サイズ設定、移行については、[IPAM deep dive](10-ipam-deep-dive.md)を参照してください。このモードを使用する新規クラスターでは、通常の割り当て用に default pool を提供してください。

**`multi-pool-values.yaml`**

```yaml
kubeProxyReplacement: true
bpf:
  masquerade: true
ipam:
  mode: multi-pool
  operator:
    autoCreateCiliumPodIPPools:
      default:
        ipv4:
          cidrs:
          - 10.244.0.0/16
          maskSize: 24
```


この追加の名前付き pool は、現在の `cidrs` および `maskSize` fields を使用します。

**`blue-pool.yaml`**

```yaml
apiVersion: cilium.io/v2alpha1
kind: CiliumPodIPPool
metadata:
  name: blue-pool
spec:
  ipv4:
    cidrs:
    - 10.245.0.0/16
    maskSize: 24
  namespaceSelector:
    matchLabels:
      ipam-pool: blue
  podSelector:
    matchLabels:
      role: blue
```


pool resource は cluster-scoped です。`podSelector` と `namespaceSelector` は別の fields であり、両方が設定されている場合は両方が一致する必要があります。古い `ipv4.cidr`、`blockSize`、および汎用 `selector` の例は無効でした。

selector の例:

**`blue-namespace.yaml`**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ipam-selection-demo
  labels:
    ipam-pool: blue
  annotations:
    ipam.cilium.io/require-pool-match: 'true'
```


**`blue-pod.yaml`**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: blue-client
  namespace: ipam-selection-demo
  labels:
    role: blue
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
```


これらは準備済みの multi-pool インストールにのみ適用してください。namespace の `require-pool-match` annotation は、非デフォルト selector の一致が必要な場合に default pool への自動フォールバックを防止します。

pool の選択では、明示的な Pod/namespace `ipam.cilium.io/ip-pool` またはアドレスファミリー pool annotations、次に自動 selectors、最後に default pool の順に従います。自動選択では、アドレスファミリーに対して pool がちょうど 1 つ一致する必要があります。selector の重複は割り当て失敗を引き起こします。pool annotations は**新しい割り当て**に影響し、すでに稼働中の Pod IPs には影響しません。node 固有の defaults も `CiliumNodeConfig` を通じて設定できます。

pool 選択はネットワーク認可の代替ではありません。workload labels/annotations を変更できるユーザーを制御し、トラフィックポリシーは別途強制してください。pool に CIDRs の重複があってはなりません。使用中の ranges/pools を軽率に削除してはなりません。`maskSize`、`allowFirstIP`、`allowLastIP` は不変です。最初/最後のアドレス予約には、文書化された small-prefix 例外があります。

現在、**cluster-pool から multi-pool への**文書化済みオンライン移行が存在します。これは任意のライブ IPAM 変更や、無計画な逆移行を許可するものではありません。前提条件と workload/capacity チェックに従ってください。この章では移行を実行しません。

### AWS ENI

ルーティング、operator IAM、subnet/instance 容量、および node 準備には完全な EKS/ENI インストールプロファイルを使用してください。次の fragment は、オプションの IPv4 prefix delegation を含む現在の keys を示しています。

**`eni-values-fragment.yaml`**

```yaml
ipam:
  mode: eni
eni:
  enabled: true
  eniTags:
    team: platform
  awsEnablePrefixDelegation: true
ipv4:
  enabled: true
ipv6:
  enabled: false
```

`eni.enabled=true` はすでに chart の `routingMode` のデフォルトを `native` にし、endpoint routes を有効にします。そのため、ここではこれらの keys を省略しています（1.20.2 の Helm template `cilium-configmap.yaml`）。


`eni.awsEnablePrefixDelegation` には、要求された prefixes をサポートする instance/subnet 設定が必要です。IPv4 `/28` には 16 個のアドレスがありますが、すべての設定で追加のスケジュール可能な Pods が 16 個保証されるわけではありません。デフォルトは無効です。架空の `eni-prefix-delegation-enabled` key を追加しないでください。

Operator が EC2 API calls を実行します。事前割り当ては Pod ごとの遅延を削減しますが、quota、API、または subnet の枯渇をなくすことはできません。`eni.eniTags` は managed interfaces をタグ付けします。意図的で検証済みの `eni.ec2APIEndpoint` オーバーライドがない限り、SDK に適切な EC2 endpoint を解決させてください。

この例は IPv4 です。ENI reference では IPv6 を、prefix/割り当て動作が異なる beta として説明しています。プラットフォーム検証は `ipv6.enabled` を有効にすることとは別です。AWS VPC CNI chaining はアドレス所有権を AWS VPC CNI に維持します。通常の EC2、Hybrid Nodes、Fargate、Auto Mode には異なるインストール/サポート境界があります。Fargate と Auto Mode はこの置換プロファイルを使用できません。

<span id="querying-per-node-podcidrs-via-ciliumnode-cr"></span>


## Node ごとの割り当て状態の照会

### CiliumNode の例

これは **読み取り専用のオブジェクト形状の例**であり、Operator が所有する状態に適用する manifest ではありません。

**`ciliumnode-example.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNode
metadata:
  name: hybrid-node-001
spec:
  addresses:
  - ip: 10.85.0.1
    type: CiliumInternalIP
  - ip: 10.80.1.10
    type: InternalIP
  ipam:
    podCIDRs:
    - 10.85.0.0/25
```


最初のアドレスは underlay node の `InternalIP` ではなく、`CiliumInternalIP` になり得ます。複数の InternalIPs/address families および複数の allocation entries が存在する場合があります。型指定された InternalIP であっても、あらゆる router から自動的に有効な next hop になるのではなく、ネットワーク設計の候補にすぎません。

### モード固有のインベントリ

この query を `ciliumnode-inventory.jq` として保存します。

**`ciliumnode-inventory.jq`**

```text
.items[] | {
  name: .metadata.name,
  internalNodeIPs: ([.spec.addresses[]? |
    select(.type == "InternalIP") | .ip] | unique),
  clusterPoolPodCIDRs: (.spec.ipam.podCIDRs // []),
  multiPoolAllocations: (.spec.ipam.pools.allocated // []),
  eniInterfaceIDs: ((.status.eni.enis // {}) | keys),
  operatorStatus: (.status.ipam["operator-status"] // {})
}
```


```bash
kubectl get ciliumnodes -o json | jq -f ciliumnode-inventory.jq
```

存在しない/空の field は、異なる IPAM モードでは正常な場合があります。Kubernetes host scope では、代わりに Kubernetes Node を確認してください。

**`kubernetes-node-inventory.jq`**

```text
.items[] | {
  name: .metadata.name,
  internalNodeIPs: ([.status.addresses[]? |
    select(.type == "InternalIP") | .address] | unique),
  podCIDRs: (.spec.podCIDRs // []),
  legacyPodCIDR: (.spec.podCIDR // null)
}
```


```bash
kubectl get nodes -o json | jq -f kubernetes-node-inventory.jq
```

これらの queries は、暗黙的に `[0]` を選択するのではなく、関連するすべての addresses/CIDRs を保持します。これらはインベントリを生成するものであり、`ip route add` commands ではありません。ネットワークのルーティング手順を通じて interfaces/next hops を選択し、forwarding/return paths を検証してください。無関係な router 上の最初のアドレスを介して、すべての CIDR をインストールすべきだと想定しないでください。

インベントリは [EKS Hybrid Nodes のネットワーク計画](../../eks-hybrid-nodes/02-network-configuration.md)に役立ちますが、その環境のルーティングおよび到達可能性チェックに取って代わるものではありません。

## ネットワークポリシーの設計と実装

### リソースとルールのセマンティクス

- namespaced `CiliumNetworkPolicy` はその namespace 内の endpoints を選択します。`CiliumClusterwideNetworkPolicy` は cluster-wide scope を提供します。host-firewall `nodeSelector` は、host firewall が構成された後者でのみサポートされます。
- `endpointSelector` は対象を識別し、ingress/egress はそれらに対するトラフィックを記述します。Cilium rule の `spec.labels` は、別の policy を継承参照するものではなく、任意の識別/metadata を保存します。Kubernetes `metadata.labels` は resource 自体にラベルを付けます。
- 適用される policies からの許可トラフィックは結合されます。明示的な deny rules には文書化された優先順位があります。別の制限なし L4 allow は、重複する L7 制限付き allow をバイパスできます。
- default deny は方向固有です。必要な DNS/application paths を意図的に維持し、実現済み policy と実際の flows を確認してください。単に default deny を無効にしても、汎用的な L7 dry-run モードにはなりません。

### 一致するポリシーラボ

使い捨てクラスターで、これらの手順を 1 つの shell で実行します。

```bash
set -euo pipefail
kubectl create namespace cilium-ipam-policy-demo
kubectl label namespace cilium-ipam-policy-demo docs-audit-lab=cilium-ipam-policy-04
```

namespace がすでに存在する場合は停止し、一貫して新しい名前を選択してください。これらの workloads は、policies で使用される official CLI の test images と labels を使用します。

**`policy-app.yaml`**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend
  namespace: cilium-ipam-policy-demo
  labels:
    app: frontend
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: v1
kind: Pod
metadata:
  name: outsider
  namespace: cilium-ipam-policy-demo
  labels:
    app: outsider
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: cilium-ipam-policy-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      automountServiceAccountToken: false
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: frontend
            topologyKey: kubernetes.io/hostname
      containers:
      - name: http
        image: quay.io/cilium/json-mock:v1.4.1@sha256:6a66df90808a39c02e7a9d58af7bf0e54d8f8b7d4bc528f48c891969a7049195
        ports:
        - containerPort: 8080
          name: http
        readinessProbe:
          httpGet:
            path: /
            port: http
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: cilium-ipam-policy-demo
spec:
  selector:
    app: backend
  ports:
  - name: http
    port: 8080
    targetPort: http
    protocol: TCP
---
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: cilium-ipam-policy-demo
  labels:
    app: client
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
```


```bash
kubectl apply -f policy-app.yaml
kubectl -n cilium-ipam-policy-demo wait --for=condition=Ready \
  pod/frontend pod/outsider pod/client --timeout=120s
kubectl -n cilium-ipam-policy-demo rollout status deployment/backend --timeout=120s
kubectl -n cilium-ipam-policy-demo get pods -o wide --show-labels
BACKEND_IP=$(kubectl -n cilium-ipam-policy-demo get service backend -o jsonpath='{.spec.clusterIP}')
test -n "$BACKEND_IP"
kubectl -n cilium-ipam-policy-demo exec frontend -- \
  curl --fail --silent --show-error --max-time 5 "http://$BACKEND_IP:8080/"
```

まず outsider からの baseline connectivity も確認します。backend anti-affinity には別の eligible node が必要です。以下の database rule は追加の application dependency を示します。このラボでは database server をデプロイまたは検証しません。

### L3/L4 ポリシー

**`backend-l4.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-access
  namespace: cilium-ipam-policy-demo
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-ipam-policy-demo
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-ipam-policy-demo
        k8s:app: database
    toPorts:
    - ports:
      - port: '3306'
        protocol: TCP
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
```


`backend-l4.yaml` を適用し、backend の agent で policy realization を待ってから、新しい requests を確認してください。frontend はアクセスを維持するはずです。outsider の拒否には、単なるゼロ以外の curl exit ではなく flow evidence が必要です。

### L7 HTTP ポリシー

これは、同じ `backend-access` resource の**代替定義**であり、2 番目の重複する allow policy ではありません。適用すると、このラボの L4 version を置き換えます。引き続き他の適用可能な policies を確認してください。

**`backend-http.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-access
  namespace: cilium-ipam-policy-demo
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-ipam-policy-demo
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/$
        - method: ^POST$
          path: ^/$
          headerMatches:
          - name: content-type
            value: application/json
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-ipam-policy-demo
        k8s:app: database
    toPorts:
    - ports:
      - port: '3306'
        protocol: TCP
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
```


```bash
kubectl apply -f backend-http.yaml
kubectl -n cilium-ipam-policy-demo get cnp backend-access -o yaml
```

realization 後、この policy は GET `/` と、正確に `content-type: application/json` の値を持つ POST `/` のみを許可します。別の path/method への request は proxy によって拒否されるはずです。application 自体が許可された operation を実装している必要があります。policy の許可は application の成功を保証しません。demo server の既知の readiness path は GET `/` です。

HTTP method/path fields は正規表現です。例は anchor 付きのままにし、適応する場合は metacharacters を escape してください。HTTP/gRPC rules には Envoy と可視の application traffic が必要です。必要な場合は TLS termination/interception を設定する必要があります。gRPC service/method 情報は HTTP/2 path および headers 内の metadata に格納され、別個の `rules.grpc` field や任意の protobuf-payload filtering には格納されません。

### Kafka ポリシー境界

現在の Cilium には、削除された `rules.kafka` API はありません。古い topic/API-key/client-ID YAML を適用しないでください。broker の**実際の listener port**への適切な L4 connectivity rules を使用し、topic access などの authentication/authorization を broker に設定してください。NetworkPolicy は broker authorization を置き換えるものでも、encryption を有効にするものでもありません。

### DNS/FQDN ポリシー

この例では、選択した resolver が `kube-system` 内の TCP/UDP 53 上の CoreDNS/kube-dns Pod であることを前提としています。まず Pod の実際の resolver を確認してください。NodeLocal DNS、OpenShift、managed DNS paths にはそれぞれ対応する設定が必要です。

**`dns-egress.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: dns-egress
  namespace: cilium-ipam-policy-demo
spec:
  endpointSelector:
    matchLabels:
      app: client
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
      rules:
        dns:
        - matchPattern: '*'
  - toFQDNs:
    - matchName: api.example.com
    - matchPattern: '*.googleapis.com'
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```


DNS L7 rule は、名前から IP への応答を学習できるよう、対応する resolver traffic を Cilium の DNS proxy 経由にリダイレクトします。port 53 を許可するだけでは、その観測は提供されません。`matchPattern: "*"` は選択した resolver への DNS queries を許可します。HTTPS egress は `toFQDNs` names に対して学習した IPs に個別に制限されます。外部テストの成功を主張する前に、`api.example.com` を解決可能で制御された test name に置き換えてください。

`*.googleapis.com` はその suffix の直下の 1 label に一致し、apex や複数 labels には一致しません。このリリースでは、`**.googleapis.com` は 1 つ以上の subdomain levels に一致できますが、apex は引き続き除外されます。DNS TTL/cache 状態と新しい lookups が重要です。名前から IP への許可は、HTTP hostname、URL、または application-user authorization のチェックではありません。

デフォルトの DNS proxy は agent 内で実行されます。別個の standalone DNS proxy は alpha として文書化されています。DNS policy に Envoy が常に必要なわけではありません。OpenShift では、公式の例はこの rule をそのままコピーするのではなく、`openshift-dns` resolver 設定と port 5353 を使用します。

### CIDRs、Services、Entities

| Rule | 境界 |
|---|---|
| `toCIDR` / `toCIDRSet` | 主に外部 peers の IP prefixes を選択します。デフォルトでは、Cilium 管理下の Pods/nodes の selectors の代替にはなりません。`pods`/`nodes` の文書化済み opt-in CIDR matching は beta で、identities を消費します |
| `toServices` | Service selectors または selectorless EndpointSlice addresses を policy selectors に解決します。Service を作成したり route したりするものではありません。selectorless cases は CIDR-mode の制限を継承します |
| `world` | 広範なクラスター外 identity category であり、「public Internet のみ」や名前付き remote-cluster selector ではありません |
| `cluster` / `cluster-mesh` | `cluster` はローカルクラスターの endpoints に加え、文書化された reserved entities/remote nodes を対象にします。`cluster-mesh` はさらに meshed-cluster endpoints を選択します |
| `all` | cluster/mesh および外部 peers を含む広範な組み合わせであり、least-privilege の近道ではありません |

API-server access には、`toServices: default/kubernetes` が通常の workload-selector semantics を持つと想定するのではなく、文書化された `kube-apiserver` entity behavior を使用してください。

## マルチクラスターシナリオ

Cluster Mesh は、Kubernetes clusters と network namespaces を分離したまま状態を共有します。remote nodes はローカル Kubernetes Node objects にはならず、policy resources も自動的に配布されません。

```text
State:  cluster A Cluster Mesh control plane <-- mTLS --> cluster B control plane
Data:   Pod A --> node A datapath --> reachable network --> node B datapath --> Pod B
```

Cluster Mesh API server は状態を同期します。Pod packets がそれを通過する必要はありません。control-plane mTLS 単独では Pod-to-Pod traffic は暗号化されません。

### セットアップ前提条件と部分的な手順

重複しない Pod CIDRs、到達可能な node InternalIPs、許可された network paths、同じ datapath mode、および文書化された one-minor difference 内の Cilium versions を備えた別々の clusters を準備します。native routing では、すべての remote Pod ranges が到達可能であり、構成済み native-routing CIDR に含まれている必要があります。インストール時に一意の Cilium names/IDs（例: `cluster-a`/1 および `cluster-b`/2）を割り当て、peer certificate trust を設定してください。

以下は、これらの前提条件と private NodePort control-plane path を準備**した後**の部分的な手順です。Kubeconfig context names は Cilium cluster names と等しい必要はありません。

```bash
export CTX_A=prepared-context-a
export CTX_B=prepared-context-b
cilium clustermesh enable --context "$CTX_A" --service-type NodePort
cilium clustermesh enable --context "$CTX_B" --service-type NodePort
cilium clustermesh connect --context "$CTX_A" --destination-context "$CTX_B"
cilium clustermesh status --context "$CTX_A" --wait
cilium clustermesh status --context "$CTX_B" --wait
```

これによって VPC peering/VPNs、routes、firewalls、private endpoints、または certificate trust がプロビジョニングされるわけではありません。完全なプラットフォーム固有セットアップに従ってください。稼働中クラスターの name/ID を軽率に変更しないでください。

### グローバル Services とクロスクラスターポリシー

準備済みの各クラスターに一致する namespaces と実際の backend workloads を作成し、互換性のある ports を持つ**同じ Service name と namespace**を使用します。

**`global-service.yaml`**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: global-service
  namespace: mesh-demo
  annotations:
    service.cilium.io/global: 'true'
spec:
  type: ClusterIP
  selector:
    app: global-app
  ports:
  - name: http
    port: 80
    targetPort: 8080
    protocol: TCP
```


`service.cilium.io/global` は現在の annotation です。global service はデフォルトでローカル backends を共有します。`service.cilium.io/shared: "false"` は、ローカル clients が remote backends を使用することを必ずしも防ぐことなく、peers への共有を停止します。ローカル ClusterIPs が同一である必要はありません。

この annotation だけで自動 failover を約束しないでください。デフォルトでは、到達不能なクラスター状態は保持されます（`clustermesh.cacheTTL: 0s`）。正の TTL を構成すると、control-plane 接続断の後に stale remote data を取り消せます。これは application health probe やゼロダウンタイムの保証ではありません。

名前付き source workload が `cluster-a` に存在する場合、宛先クラスターの `mesh-demo` namespace にこの ingress policy を適用してください。

**`cross-cluster-policy.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-cluster-a-frontend
  namespace: mesh-demo
spec:
  endpointSelector:
    matchLabels:
      app: global-app
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: frontend-ns
        k8s:io.cilium.k8s.policy.cluster: cluster-a
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
```


cluster label は kubeconfig context ではなく、構成済みの **Cilium cluster name** を使用します。現在の Cilium では、endpoint selectors は peers が明示的に選択されない限りローカルクラスターがデフォルトです。各クラスターに必要な policies を個別にインストールし、両方向の traffic をテストしてください。

## 検証とクリーンアップ

例は、リリース固有の schemas、configuration/source contracts、および範囲を限定した local fixtures に対して確認しました。この監査は、ライブ IP allocation、kernel policy enforcement、cloud provisioning、稼働中の database、または成功した cross-cluster traffic を主張するものではありません。

目的の状態と実現済み状態を確認し、成功した baseline を検証してから、予期される denials を関連する flow と関連付けてください。所有権を検証した後、この実行の namespaced policy workloads のみをクリーンアップしてください。別の multi-pool 演習では、pool removal を検討する前に workloads を解放し、pool allocations が使用中でなくなったことを確認してください。近道として active CiliumNode/pool state を削除しないでください。

## ソース

- [IPAM modes/migration](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/index.rst)、[cluster pool](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/cluster-pool.rst)、[host scope](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/kubernetes.rst)、[multi-pool](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/multi-pool.rst)、[migration procedure](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/cluster-pool-to-multi-pool.rst)
- [PodIPPool schema](https://github.com/cilium/cilium/blob/v1.20.2/pkg/k8s/apis/cilium.io/client/crds/v2alpha1/ciliumpodippools.yaml)、[CiliumNode schema](https://github.com/cilium/cilium/blob/v1.20.2/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnodes.yaml)、[ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/eni.rst)、[Helm values](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/values.yaml)、[EKS CNI boundaries](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [Policy rule API](https://github.com/cilium/cilium/blob/v1.20.2/pkg/policy/api/rule.go)、[L3 rules](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/policy/layer3.rst)、[L7 rules](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/policy/layer7.rst)、[DNS policies](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/dns.rst)、[wildcard implementation](https://github.com/cilium/cilium/blob/v1.20.2/pkg/fqdn/matchpattern/matchpattern.go)
- [Cluster Mesh setup](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/clustermesh/setup.rst)、[architecture](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/clustermesh/intro.rst)、[global services](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/clustermesh/global-services.rst)、[cross-cluster policy](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/clustermesh/policy.rst)


[メインページに戻る](README.md)

## クイズ

[IPAM とポリシーの理解を確認する](../../quizzes/networking/cilium/04-ipam-policy-quiz.md)。