# IPAM とネットワークポリシー

> **レビュー基準**: Cilium 1.20.3、検証対象の Kubernetes 1.33–1.36。リソース API バージョンとプラットフォーム要件は個別に確認しています。
> **最終レビュー日**: October 16, 2026

## ラボ環境の準備

使い捨ての Linux クラスターを準備するには、[インストールプロファイル](README.md)と[ネットワークの前提条件](03-networking.md)を参照してください。kubectl のバージョンは、API サーバーでサポートされるバージョンスキューの範囲内に保ちます。以下の IPAM プロファイルは、インストール時または文書化された移行時に選択する代替設定です。稼働中のクラスターに ConfigMap の切り替えを順番に適用する手順ではありません。

ポリシーのラボでは専用の namespace と、以下のポリシーに一致するワークロードを使用します。これは、ラベルがポリシーに一致していなかった古い Cilium 1.14 の Star Wars manifest に代わるものです。既存の Kubernetes/Cilium クラスター全体のポリシーと admission 設定を先に確認してください。新しい namespace を作っても、それらの設定は上書きされません。

```bash
cilium status --wait
kubectl -n kube-system get configmap cilium-config -o yaml
kubectl get ciliumnodeconfigs --all-namespaces -o yaml
helm -n kube-system get values cilium --all
```

namespace/release 名が異なる場合は実際の名前を使ってください。期待する Helm values と ConfigMap、node の上書き設定、operator 設定、実際に反映された agent の状態は、それぞれ異なる情報を示します。`ipam` を含む grep 結果だけでは、有効な設定全体を確認したことにはなりません。

## IP アドレス管理の方式

Cilium の Pod IPAM はワークロードのアドレスを割り当てます。Service の **ClusterIP** は Kubernetes が割り当てます。Cilium の **LoadBalancer IPAM** は LoadBalancer アドレスを割り当てる別の機能です。`CiliumPodIPPool` は Service の ClusterIP を割り当てません。

### 割り当て元と信頼できる状態

| 設定 | node の容量 / Pod IP を割り当てるもの | 確認する状態 |
|---|---|---|
| `cluster-pool`（一般的なデフォルト） | Cilium Operator が node ごとの CIDR を割り当て、各 agent がその範囲のアドレスを割り当てる | `CiliumNode.spec.ipam.podCIDRs` と operator の状態 |
| `kubernetes` / host scope | Kubernetes が node の PodCIDR を提供し、各 agent がその範囲内で割り当てる | Kubernetes `Node.spec.podCIDRs` / `spec.podCIDR` と、サポート対象のプロバイダー annotation |
| `multi-pool` | agent の要求に応じて Operator が名前付き pool からブロックを割り当て、agent が Pod IP を割り当てる | `CiliumPodIPPool`、`CiliumNode.spec.ipam.pools.requested` / `allocated` |
| `crd` | 外部 allocator が利用可能なアドレスを提供し、agent が使用・解放する | `CiliumNode.spec.ipam.pool` / `status.ipam.used`（該当する IPv6 フィールドも確認） |
| `eni` | Operator が AWS ENI/IP/prefix を管理し、agent が interface の状態を multi-pool allocator 用に変換する | `CiliumNode.status.eni.enis` と mode 固有の pool / demand 状態 |
| `azure` | 自主管理の Azure VM/VMSS クラスター向けの upstream operator/agent 統合 | Azure / CiliumNode の割り当て状態 |
| `delegated-plugin` | Cilium CNI が、managed AKS の Azure IPAM など別の IPAM plugin を呼び出す | provider / plugin の状態。upstream Azure IPAM の設定で代用しない |
| GKE 統合 | upstream GKE 統合は host-scope の `kubernetes` IPAM を使う。managed Dataplane V2 の割り当て主体は別 | provider 設定と Node CIDR。`gke` という独立した IPAM 値ではない |

`cluster-pool` と Kubernetes host scope のどちらも、各 Pod のアドレスは node 上で個別に割り当てられます。異なるのは、**node の prefix** を誰が割り当てるかです。いずれも調整作業を不要にするものではなく、ユーザー指定の pool が VPC、node network、Service 範囲、または別クラスターと重複しないことを保証するものでもありません。

リリース済みの CRD/type 定義では、一般的な CRD ベース割り当てに `pool` と `used` を使います。一部の説明文には `available` / `inuse` と記載されていますが、古い名前をコピーせず、インストール済みの schema と mode 固有のフィールドを使ってください。1.20.3 の ENI は interface/multi-pool 経路を使うため、汎用 CRD ベースのフィールドが常にその状態を示すとは限りません。

### Kubernetes / CNI との統合

kubelet は container runtime を通じて Pod sandbox の操作を要求し、CNI 対応 runtime が Cilium CNI plugin を呼び出します。アドレス割り当ては選択した backend によって決まり、その後 plugin/agent が endpoint network を設定します。host-scope mode では、Kubernetes が必要な address family の CIDR を提供する必要があります。たとえば node-CIDR allocator を適切に設定します。

## IPAM の設定

以下は、該当するインストールプロファイルにマージする **Helm values の断片**です。最初に Pod / Service / node / 外部 network のアドレス範囲を確認してください。

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


Operator は各 Pod のアドレス要求を中央で処理するのではなく、node ごとのブロック割り当てを調整します。`clusterPoolIPv4PodCIDRList` に複数の CIDR を指定すると共通の割り当て範囲が広がります。これはワークロードごとに名前付き pool を選択する方式とは異なります。

稼働中のクラスターを拡張する際、既存の pool-list の項目を置き換えないでください。文書化された拡張手順に従い、重複しない CIDR を追加します。node mask size は通常の運用で変更する設定ではありません。各ブロックのアドレス数は、予約済みアドレスや node 内の機能で使用されるアドレスがあるため、利用可能な Pod 容量と同じではありません。

Kubernetes/Cilium の dual stack 対応がすでに準備されているクラスターでは、次を使います。

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


この 2 つの Cilium address-family flag を有効にしても、それだけで Kubernetes Service CIDR、underlay の IPv6 接続性、または cloud のサポートが設定されるわけではありません。

### Multi-Pool と CiliumPodIPPool

文書化されている mode 名は `multi-pool` です。1.20 の resource API は引き続き `cilium.io/v2alpha1` です（**[1.21 pre-release]** では `CiliumPodIPPool` が `cilium.io/v2` で提供され、storage version になります。`v2alpha1` は deprecated となり、`spec.ipv4.pool` / `spec.ipv6.pool` に CIDR ごとの `reservedRanges` が追加されます。これらのフィールドは `v2` にのみあります）。API suffix だけから機能の成熟度を推測しないでください。upstream の multi-pool tutorial では `kubeProxyReplacement=true` と `bpf.masquerade=true` も必要です（iptables masquerade を使う場合は `egressMasqueradeInterfaces` が必要です）。以下の例にはこれらを含めています。割り当ての内部動作、pool のサイズ設計、移行については [IPAM の詳細](10-ipam-deep-dive.md)を参照してください。この mode を使う新規クラスターでは、通常の割り当て用に default pool を指定します。

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


次の名前付き pool では、現在の `cidrs` と `maskSize` フィールドを使います。

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


pool resource は cluster-scoped です。`podSelector` と `namespaceSelector` は別々のフィールドであり、両方を設定した場合は両方とも一致する必要があります。以前の `ipv4.cidr`、`blockSize`、汎用 `selector` を使った例は無効でした。

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


これらは multi-pool のインストールが準備済みの場合にのみ適用してください。namespace の `require-pool-match` annotation を設定すると、non-default selector との一致が必要な場合に default pool へ自動的にフォールバックするのを防げます。

pool の選択順序は、Pod / namespace に明示された `ipam.cilium.io/ip-pool` または address-family pool annotation、自動 selector、default pool です。自動選択では、その address family に対して pool が 1 つだけ一致する必要があります。selector が重複すると割り当てに失敗します。pool annotation が影響するのは **新しい割り当て**であり、すでに実行中の Pod IP ではありません。node ごとの default は `CiliumNodeConfig` でも設定できます。

pool 選択は network authorization の代わりにはなりません。ワークロードの label / annotation を変更できる主体を制御し、traffic policy は別途適用してください。pool の CIDR は重複させないでください。使用中の範囲 / pool を安易に削除してはなりません。`maskSize`、`allowFirstIP`、`allowLastIP` は変更不可です。先頭 / 末尾アドレスの予約には、小さな prefix に対する文書化された例外があります。

**cluster-pool から multi-pool への**、現在文書化されているオンライン移行手順があります。それによって、任意の稼働中 IPAM の変更や、計画されていない逆方向の移行が許可されるわけではありません。前提条件とワークロード / 容量の確認に従ってください。この章では移行を実行しません。

### AWS ENI

routing、operator IAM、subnet / instance の容量、node の準備を含む EKS/ENI 用の完全なインストールプロファイルを使用してください。次の断片は、オプションの IPv4 prefix delegation を含む現在の key を示します。

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

`eni.enabled=true` によって chart はすでに `routingMode` を `native` にし、endpoint route を有効にするため、ここではそれらの key を省略しています（1.20.2 の Helm template `cilium-configmap.yaml`）。


`eni.awsEnablePrefixDelegation` を使うには、instance/subnet の設定が要求された prefix に対応している必要があります。IPv4 `/28` は 16 アドレスを含みますが、どの設定でも追加の Pod を 16 個スケジュールできることを保証するわけではありません。デフォルトでは無効です。存在しない `eni-prefix-delegation-enabled` key を追加しないでください。

EC2 API 呼び出しは Operator が行います。pre-allocation は Pod ごとの遅延を減らしますが、quota、API、subnet の枯渇をなくすものではありません。`eni.eniTags` は管理対象 interface に tag を付けます。意図があり、妥当性を検証した `eni.ec2APIEndpoint` override を使う場合を除き、適切な EC2 endpoint は SDK に解決させてください。

この例は IPv4 です。ENI の reference では、IPv6 は異なる prefix / 割り当て動作を持つ beta 機能として説明されています。プラットフォームの検証は `ipv6.enabled` を有効にするだけでは完了しません。AWS VPC CNI chaining では、アドレスの所有者は AWS VPC CNI のままです。通常の EC2、Hybrid Nodes、Fargate、Auto Mode ではインストール方法とサポート範囲が異なります。Fargate と Auto Mode では、この置き換え用 profile は使用できません。

<span id="querying-per-node-podcidrs-via-ciliumnode-cr"></span>


## node ごとの割り当て状態を確認する

### CiliumNode の例

これは Operator が所有する状態に適用する manifest ではなく、**読み取り専用のオブジェクト例**です。

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


最初のアドレスは、underlay node の `InternalIP` ではなく `CiliumInternalIP` の場合があります。複数の InternalIP / address family と複数の割り当て項目が存在する場合もあります。型が InternalIP であっても、すべての router から有効な next hop として使えることが自動的に保証されるわけではありません。

### mode ごとの一覧

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

異なる IPAM mode では、field が存在しない、または空でも正常なことがあります。Kubernetes host scope の場合は、代わりに Kubernetes Node を確認してください。

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

これらの query は `[0]` を使って暗黙に 1 件を選ぶのではなく、関連するすべてのアドレス / CIDR を保持します。出力されるのは一覧であり、`ip route add` コマンドではありません。interface / next hop を選び、network の routing 手順に従って転送経路と戻り経路を検証してください。無関係な router で、すべての CIDR を最初のアドレス経由で設定すべきだと想定しないでください。

この一覧は[EKS Hybrid Nodes のネットワーク計画](../../eks-hybrid-nodes/02-network-configuration.md)に役立ちますが、その環境で必要な routing と到達性の確認に代わるものではありません。

## ネットワークポリシーの設計と実装

### リソースとルールの意味

- namespaced な `CiliumNetworkPolicy` は、その namespace 内の endpoint を選択します。`CiliumClusterwideNetworkPolicy` はクラスター全体を対象にします。Host firewall の `nodeSelector` は、host firewall が設定された状態で、後者でのみサポートされます。
- `endpointSelector` は対象 endpoint を特定し、ingress / egress はその対象を基準にした通信方向を表します。Cilium rule の `spec.labels` は識別 / metadata 用であり、別の policy を継承する参照ではありません。Kubernetes `metadata.labels` は policy resource 自体に付く label です。
- 適用される複数の policy の許可ルールは組み合わされ、明示的な deny rule には文書化された優先順位があります。別の制限のない L4 allow によって、L7 制限付き allow と重複する通信が許可されることがあります。
- default deny は方向ごとに適用されます。必要な DNS / アプリケーション通信経路を意図的に維持し、実際に反映された policy と flow を確認してください。default deny を無効にしても、あらゆる L7 policy の dry-run になるわけではありません。

### ラボで一致させたポリシー

使い捨てのクラスターで、これらの手順を 1 つの shell から実行してください。

```bash
set -euo pipefail
kubectl create namespace cilium-ipam-policy-demo
kubectl label namespace cilium-ipam-policy-demo docs-audit-lab=cilium-ipam-policy-04
```

namespace がすでに存在する場合は停止し、一貫して使う新しい名前を選んでください。以下のワークロードでは公式 CLI のテスト用 image と、ポリシーで使用する label を使います。

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

outsider からの baseline 接続性も、最初に確認してください。backend の anti-affinity には、条件を満たす別の node が必要です。以下の database rule は追加のアプリケーション依存関係を示す例です。このラボでは database server をデプロイも検証もしません。

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


`backend-l4.yaml` を適用し、backend の agent で policy が反映されるまで待ってから、新しい request を確認してください。frontend は引き続きアクセスできる必要があります。outsider が拒否されたことは、curl の終了コードがゼロ以外というだけでは証明できず、flow の証拠を確認してください。

### L7 HTTP ポリシー

これは同じ `backend-access` resource に対する**代替定義**であり、重複する allow policy を追加するものではありません。適用すると、このラボの L4 版を置き換えます。他に適用される policy も引き続き確認してください。

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

反映後、この policy は GET `/` と、`content-type: application/json` の値が完全一致する場合の POST `/` を許可します。他の path / method への request は proxy によって拒否されます。許可された操作を実装するのはアプリケーション自体です。policy が許可しても、アプリケーションの成功が保証されるわけではありません。demo server で readiness に使われる path は GET `/` です。

HTTP の method / path field は regular expression です。例では明示的に anchor を付け、応用時はメタ文字を escape してください。HTTP/gRPC rule には Envoy と、可視化できるアプリケーショントラフィックが必要です。必要に応じて TLS termination / interception を設定してください。gRPC の service / method 情報は HTTP/2 path と header metadata に含まれます。独立した `rules.grpc` field や、任意の protobuf payload filtering を使うわけではありません。

### Kafka ポリシーの境界

現在の Cilium には、削除された `rules.kafka` API はありません。古い topic/API-key/client-ID の YAML を適用しないでください。broker の**実際の listener port**への L4 接続ルールを使い、topic access などの認証 / 認可は broker 側で設定します。NetworkPolicy は broker の認可に代わるものではなく、暗号化を有効にするものでもありません。

### DNS / FQDN ポリシー

以下の例では、選択した resolver が `kube-system` 内の CoreDNS/kube-dns Pod で、TCP/UDP 53 を使用するものとします。resolver の実態を先に確認してください。NodeLocal DNS、OpenShift、managed DNS では、それぞれに一致した設定が必要です。

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

DNS L7 rule は、一致した resolver 通信を Cilium の DNS proxy にリダイレクトし、応答から名前と IP の対応を学習できるようにします。port 53 を許可するだけでは、その観測は行われません。`matchPattern: "*"` は選択した resolver への DNS query を許可し、HTTPS egress は `toFQDNs` に指定した名前から学習した IP に別途制限されます。外部テストが成功したと主張する前に、`api.example.com` を名前解決できる管理下のテスト名に置き換えてください。

`*.googleapis.com` は suffix の下にある 1 階層の label に一致します。apex や複数階層には一致しません。このリリースで `**.googleapis.com` は 1 階層以上の subdomain に一致しますが、apex は引き続き対象外です。DNS TTL/cache の状態と、新しい lookup の実施が重要です。名前から IP への許可は、HTTP hostname、URL、またはアプリケーション利用者の認可確認ではありません。

デフォルトの DNS proxy は agent 内で動作します。独立した standalone DNS proxy は alpha として文書化されています。DNS policy に常に Envoy が必要なわけではありません。OpenShift では、公式例が `openshift-dns` resolver 設定と port 5353 を使っています。このルールをそのままコピーしないでください。

### CIDR、Service、entity

| ルール | 対象範囲 |
|---|---|
| `toCIDR` / `toCIDRSet` | 主に外部 peer の IP prefix を選択します。デフォルトでは Cilium 管理の Pod / node に対する selector の代用にはなりません。`pods` / `nodes` に対する文書化済み opt-in CIDR matching は beta で、identity を消費します |
| `toServices` | Service selector または selector のない EndpointSlice address を policy selector に解決します。Service の作成や route 設定は行いません。selector のない場合は CIDR mode の制約を引き継ぎます |
| `world` | クラスター外の広い identity category です。「public Internet のみ」を意味せず、名前付きの remote-cluster selector でもありません |
| `cluster` / `cluster-mesh` | `cluster` はローカルクラスターの endpoint と、文書化された予約済み entity / remote node を対象とします。`cluster-mesh` はさらに mesh 接続済みクラスターの endpoint も対象にします |
| `all` | cluster / mesh と外部 peer を含む広い組み合わせです。最小権限を実現する近道ではありません |

API server へのアクセスでは、`toServices: default/kubernetes` が通常のワークロード selector と同じ意味だと想定せず、文書化されている `kube-apiserver` entity の動作を使ってください。

## マルチクラスターのシナリオ

Cluster Mesh は状態を共有しますが、Kubernetes cluster と network namespace は分離されたままです。remote node はローカルの Kubernetes Node object にはならず、policy resource も自動配布されません。

```text
State:  cluster A Cluster Mesh control plane <-- mTLS --> cluster B control plane
Data:   Pod A --> node A datapath --> reachable network --> node B datapath --> Pod B
```

Cluster Mesh API server は状態を同期します。Pod packet が API server を経由する必要はありません。control-plane mTLS だけでは、Pod 間の通信は暗号化されません。

### セットアップの前提条件と一部の手順

別々のクラスターを、重複しない Pod CIDR、到達可能な node InternalIP、許可された network path、同じ datapath mode、および文書化された 1 minor 以内の Cilium version 差で準備してください。native routing では、すべての remote Pod 範囲への到達性と、設定済み native-routing CIDR による包含も必要です。インストール時に一意な Cilium 名 / ID（例: `cluster-a` / 1 と `cluster-b` / 2）を割り当て、peer certificate の trust を設定してください。

以下は、それらの前提条件と private NodePort の control-plane 経路を準備した**後に行う一部の手順**です。kubeconfig context 名は Cilium cluster 名と同じである必要はありません。

```bash
export CTX_A=prepared-context-a
export CTX_B=prepared-context-b
cilium clustermesh enable --context "$CTX_A" --service-type NodePort
cilium clustermesh enable --context "$CTX_B" --service-type NodePort
cilium clustermesh connect --context "$CTX_A" --destination-context "$CTX_B"
cilium clustermesh status --context "$CTX_A" --wait
cilium clustermesh status --context "$CTX_B" --wait
```

この手順では VPC peering/VPN、route、firewall、private endpoint、certificate trust は用意しません。プラットフォーム固有の完全なセットアップに従ってください。稼働中のクラスターの name / ID を安易に変更しないでください。

### Global Service とクラスター間ポリシー

準備済みの各クラスターに同じ namespace と実際の backend workload を作成し、**同じ Service 名と namespace**を使って、互換性のある port を設定します。

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

現在の annotation は `service.cilium.io/global` です。デフォルトでは global service はローカル backend を共有します。`service.cilium.io/shared: "false"` を設定すると peer との共有を止めますが、ローカル client が remote backend を使うことまで必ずしも防ぐものではありません。ローカルの ClusterIP は同一である必要はありません。

この annotation だけで自動 failover を保証しないでください。デフォルトでは到達不能なクラスターの状態は保持されます（`clustermesh.cacheTTL: 0s`）。正の TTL を設定すると、control-plane 切断後に古い remote data を失効させられます。それはアプリケーションの health probe でも、zero-downtime の保証でもありません。

`cluster-a` に指定された送信元 workload がある場合、宛先クラスターの `mesh-demo` namespace に次の ingress policy を適用します。

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

cluster label には kubeconfig context ではなく、設定済みの **Cilium cluster name** を使います。現在の Cilium では、peer を明示的に選択しない endpoint selector はデフォルトでローカルクラスターを対象にします。必要な policy を各クラスターに個別にインストールし、両方向の通信をテストしてください。

## 検証とクリーンアップ

例は、リリース固有の schema、設定 / source contract、および範囲を限定したローカル fixture に照らして確認しています。この監査は、実際の IP 割り当て、kernel policy の適用、cloud provisioning、稼働中の database、またはクラスター間通信の成功を主張するものではありません。

期待する状態と実際に反映された状態を確認し、baseline で通信が成功することを検証してから、予想される拒否結果を該当する flow と照合してください。所有者を確認したうえで、この実行が作成した namespaced policy workload のみを削除します。別の multi-pool 演習では、pool の削除を検討する前に workload を解放し、pool allocation が使用中ではないことを確認してください。近道として、稼働中の CiliumNode / pool state を削除しないでください。

## 参照資料

- [IPAM mode / 移行](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/index.rst)、[cluster pool](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/cluster-pool.rst)、[host scope](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/kubernetes.rst)、[multi-pool](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/multi-pool.rst)、[移行手順](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/cluster-pool-to-multi-pool.rst)
- [PodIPPool schema](https://github.com/cilium/cilium/blob/v1.20.3/pkg/k8s/apis/cilium.io/client/crds/v2alpha1/ciliumpodippools.yaml)、[CiliumNode schema](https://github.com/cilium/cilium/blob/v1.20.3/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnodes.yaml)、[ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/eni.rst)、[Helm values](https://github.com/cilium/cilium/blob/v1.20.3/install/kubernetes/cilium/values.yaml)、[EKS CNI の境界](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [Policy rule API](https://github.com/cilium/cilium/blob/v1.20.3/pkg/policy/api/rule.go)、[L3 rule](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/policy/layer3.rst)、[L7 rule](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/policy/layer7.rst)、[DNS policy](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/dns.rst)、[wildcard の実装](https://github.com/cilium/cilium/blob/v1.20.3/pkg/fqdn/matchpattern/matchpattern.go)
- [Cluster Mesh のセットアップ](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/clustermesh/setup.rst)、[アーキテクチャ](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/clustermesh/intro.rst)、[global service](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/clustermesh/global-services.rst)、[クラスター間 policy](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/clustermesh/policy.rst)


[メインページに戻る](README.md)

## クイズ

[IPAM とポリシーの理解度を確認するクイズ](../../quizzes/networking/cilium/04-ipam-policy-quiz.md)に挑戦してください。
