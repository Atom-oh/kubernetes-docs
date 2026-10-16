# L2–L7 ネットワーキングとロードバランシング

> **レビュー基準**: Cilium 1.20.2、CLI 0.20.1。Istio の例では 1.31 API を使用します。
> **最終更新**: October 15, 2026

## ラボ環境のセットアップ

[インストール](README.md) および[ネットワーキング](03-networking.md)ガイドに従って用意した使い捨てクラスタを使用してください。プラットフォーム/カーネルのサポートおよび kubectl のバージョン差異を確認します。HTTP ラボには、スケジュール可能な Linux ノードが 2 台必要です。DSR/Maglev 実験にはさらに、準備済みの kube-proxy-free クラスタ、到達可能な実際の API-server エンドポイント、およびサポート対象のネットワークパスが必要です。

実験には完全なインストール値を選択してください。繰り返し実行する `cilium install --config ...` コマンドは、実行中の機能移行手順ではありません。また、任意のインストール後に kube-proxy を削除することは安全な近道ではありません。

## OSI レイヤーを理解する

OSI は概念モデルであり、7 つの Cilium プロセスや固定されたポリシーフックの順序ではありません。

| レイヤー | 役割 / 例 | Cilium との関係 |
|---|---|---|
| L1 物理 | ビット、媒体、トランシーバー、リピーター | 基盤となるハードウェア/ネットワーク要件 |
| L2 データリンク | Ethernet フレーム、MAC アドレス指定、ブリッジ/スイッチ | パケット処理および明示的に設定された L2 Service announcement |
| L3 ネットワーク | IP パケット、ルーティング、ICMP | ルーティング、identity/CIDR ポリシー、およびサポート対象のフラグメント処理 |
| L4 トランスポート | TCP セグメントと信頼性のあるストリーム、配信/順序保証のない UDP データグラム | ポート/プロトコルポリシー、接続状態、Service 変換 |
| L5 セッション | セッション/対話の編成 | 多くの場合アプリケーション/プロトコル内で実装される概念的な機能 |
| L6 プレゼンテーション | 表現、エンコーディング、暗号変換 | TLS は概念上ここにマッピングされることが多く、普遍的な独立 Linux レイヤーではない |
| L7 アプリケーション | HTTP、DNS、gRPC、その他のアプリケーションプロトコル | サポート対象のプロキシポリシー。アプリケーションプロトコルの存在は Cilium ポリシーパーサーの存在を意味しない |

### 実際のレイヤー固有機能

- **L2:** L2 Announcements は、対象となる Service IP に対するベータ版の設定済み ARP/NDP 応答メカニズムです。これには kube-proxy replacement と適切なデバイス/ローカルネットワーク到達可能性が必要です。選出されたノードがその Service のトラフィックを受信します。これは任意の MAC/VLAN ACL サポートでも、すべてのパケットをキャプチャする一般的な L2 ブリッジ/保証でもありません。`externalTrafficPolicy: Local` には文書化された非互換性があります。
- **L3:** IP/identity ポリシーとルーティングにはモード固有の要件があります。マルチキャストは、VXLAN を必要とする個別に有効化されるベータ機能です。文書化された最小カーネルは、AMD64 では 5.10、AArch64 では 6.0 です。すべてのルーティングモードで動作すると仮定しないでください。
- **L4:** TCP/UDP ポートポリシー、connection tracking、socket/packet Service load balancing、およびサポート対象の affinity は、異なるフックで動作します。socket の決定はパケット構築前に発生する場合があります。
- **L7:** 現在の組み込みポリシーグループは HTTP と DNS です。gRPC はサポート対象の HTTP/2 パスを使用します。Kafka L7 ルールは削除されています。TLS/SNI 機能には文書化されたプロキシ設定が必要です。暗号化されたアプリケーションコンテンツは自動的に検査可能にはなりません。

HTTP/gRPC ポリシーは Envoy を使用し、DNS ポリシーは Cilium の DNS proxy を使用します。Envoy は values/アップグレード互換性に応じて agent 管理プロセスまたは専用の `cilium-envoy` DaemonSet になります。L7 を有効にした新規 1.20 chart のデフォルトでは DaemonSet が優先され、以下のプロファイルでは明示的に設定します。ポリシーを追加しても、すべてのインストール設定が上書きされるわけではありません。

## HTTP ポリシーラボ

新しい namespace と対応する workload を作成します。イメージ/digest および既知の server readiness パスは、公式 CLI テスト Deployment 定義から取得しています。

```bash
set -euo pipefail
kubectl create namespace cilium-l2l7-demo
kubectl label namespace cilium-l2l7-demo docs-audit-lab=cilium-l2l7-05
```

namespace がすでに存在する場合は停止してください。別の実行のリソースを再利用するのではなく、一貫して新しい名前を選択してください。

**`l7-app.yaml`**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: cilium-l2l7-demo
  labels:
    app: client
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
  namespace: cilium-l2l7-demo
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
  name: app1
  namespace: cilium-l2l7-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: app1
  template:
    metadata:
      labels:
        app: app1
    spec:
      automountServiceAccountToken: false
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: client
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
  name: app1-service
  namespace: cilium-l2l7-demo
spec:
  selector:
    app: app1
  ports:
  - name: http
    port: 80
    targetPort: http
    protocol: TCP
```


```bash
kubectl apply -f l7-app.yaml
kubectl -n cilium-l2l7-demo wait --for=condition=Ready pod/client pod/outsider --timeout=120s
kubectl -n cilium-l2l7-demo rollout status deployment/app1 --timeout=120s
kubectl -n cilium-l2l7-demo get pods,services -o wide
kubectl -n cilium-l2l7-demo exec client -- \
  curl --fail --silent --show-error --max-time 5 http://app1-service/
```

outsider のベースライン接続性も確認してください。Service はポート 80 を公開しますが、その backend は **8080** でリッスンします。Pod ingress policy は backend ポートを使用します。これにより、存在しない/一致しない以前の application セットアップ、およびデフォルトの labels/entrypoint が例と一致しなかった client Pod を置き換えます。

**`app1-http.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: app1-http
  namespace: cilium-l2l7-demo
spec:
  endpointSelector:
    matchLabels:
      app: app1
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-l2l7-demo
        k8s:app: client
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/$
        - method: ^POST$
          path: ^/api/v1$
          headerMatches:
          - name: x-demo-tenant
            value: team-a
```


```bash
kubectl apply -f app1-http.yaml
kubectl -n cilium-l2l7-demo get cnp app1-http -o yaml
```

ポリシーの実現後、名前付き client は GET `/` リクエストを実行できます。POST `/api/v1` は、このルールにより正確な `x-demo-tenant: team-a` ヘッダーを持つ場合にのみ許可されます。backend は引き続きその API 操作を実装している必要があります。その他の method/path/peer は、ほかに適用可能なポリシーが許可していない範囲でのみ拒否されます。application response と同様に、実現されたポリシーおよびフローの証跡も検証してください。

このヘッダーは **デモ用フィルターであり、認証ではありません**。以前の 32 文字の「token」条件は、identity、signature、issuer、expiry、または authorization を検証しませんでした。リリース済み translator では、値を含む `headers` 文字列はその値にリテラル一致します。`X-Auth-Token: ^[a-zA-Z0-9]{32}$` は regex token validator ではありません。意図した正確な値/存在要件には明示的な `headerMatches` を使用し、ユーザーは application/適切な authentication layer で認証してください。

method と path は正規表現をサポートします。組み込み Cilium HTTP policy には任意の request-body predicate はありません。ヘッダーの存在、完全一致、URL filtering、および application authorization は異なる制御です。

## Service Mesh 統合

Cilium はネットワーキングとサポート対象の network policy を提供し、Istio は設定された proxy と mesh の動作を所有します。統合によって Istio sidecar が自動的にバイパスされたり、その mTLS コストが除去されたり、すべての trace が統合されたり、リクエストが高速になることが保証されたりするわけではありません。

```text
Configuration: istiod --> Istio Envoy proxies
Request: app --> source sidecar --> Cilium/network --> destination sidecar --> app
```

### Istio のトラフィックインターセプトを維持する

現在の Cilium integration guide では kube-proxy coexistence と、慎重に設定した full-replacement オプションが提供されています。coexistence のフラグメントは次のとおりです。

**`istio-cilium-values.yaml`**

```yaml
kubeProxyReplacement: false
socketLB:
  hostNamespaceOnly: true
cni:
  exclusive: false
```


意図的に準備された full-replacement セットアップの場合、`kubeProxyReplacement: true` にはさらに、到達可能な API endpoint と replacement の前提条件が必要です。Pod socket translation が Istio interception をバイパスしないように `socketLB.hostNamespaceOnly: true` を維持し、ノード CNI configuration を共有する場合は `cni.exclusive: false` を使用してください。

Istio sidecar redirection では init container または Istio CNI node agent を使用でき、ambient は対応する node/CNI パスを使用します。1 つのモードを選択して、[保守されている Istio インストールガイド](../../service-mesh/istio/01-installation.md)に従ってください。Kubernetes API server は Istio の admission webhook に到達できる必要があります。managed-control-plane/overlay network では、文書化された routing または host-network ソリューションが必要になる場合があります。すべての overlay cluster に対して `istiod hostNetwork: true` を指定しないでください。

### mTLS を保持し L7 の責務を割り当てる

Istio で暗号化された workload traffic に plaintext の Cilium HTTP inspection を適用しないでください。この例では Istio mTLS と L7 routing を Istio に保持し、Cilium の **L3/L4 のみ**の policy を使用します。以前の統合 L7 例を通すためだけに mTLS を無効にすると、security design が変更されます。

以下は、`productpage` と `reviews` workload、ポート 9080 上の reviews Service、および `version: v1`/`v2` の label を持つ reviews Pod を備えた、すでに準備済みの `istio-cilium-demo` namespace 用の **sidecar-mode** configuration です。完全な Bookinfo deployment ではありません。

**`istio-reviews.yaml`**

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-route
  namespace: istio-cilium-demo
spec:
  hosts:
  - reviews.istio-cilium-demo.svc.cluster.local
  http:
  - match:
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: reviews.istio-cilium-demo.svc.cluster.local
        subset: v2
        port:
          number: 9080
  - route:
    - destination:
        host: reviews.istio-cilium-demo.svc.cluster.local
        subset: v1
        port:
          number: 9080
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-subsets
  namespace: istio-cilium-demo
spec:
  host: reviews.istio-cilium-demo.svc.cluster.local
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
---
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-cilium-demo
spec:
  mtls:
    mode: STRICT
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: reviews-l4
  namespace: istio-cilium-demo
spec:
  endpointSelector:
    matchLabels:
      app: reviews
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: istio-cilium-demo
        k8s:app: productpage
    toPorts:
    - ports:
      - port: '9080'
        protocol: TCP
```


DestinationRule は VirtualService が参照する subset を定義します。`end-user: jason` ヘッダーはデモルートを選択します。これは認証済み identity ではありません。sidecar injection の成功、実際の endpoint label、subset readiness、および mesh telemetry を検証してください。

9080 Cilium ルールを ambient policy のレシピとして再利用しないでください。ambient HBONE はポート 15008 で暗号化トンネリングを使用し、可視の traffic/identity 境界を変更します。その topology に適切な Istio policy とプラットフォーム固有の Cilium network guard を適用してください。

## ロードバランシングアーキテクチャ

Cilium の service map、backend map、reverse-NAT state、および connection tracking は、異なる forwarding stage をサポートします。L7 Envoy load balancing は別のコンポーネントです。その algorithm リストを BPF service datapath と混同しないでください。

### BPF forwarding モードと algorithm

| 設定 / メカニズム | 意味と制限 |
|---|---|
| `loadBalancer.mode: snat` | デフォルトの forwarding mode。適用可能な external service path では、direct-return path ではなく source translation/reverse state を使用する |
| `dsr` | リモート backend の応答は ingress load-balancing node をバイパスできる。network はその return path を許可する必要があり、upstream proxy によってすでに変換された client IP を復元することはできない |
| `hybrid` | TCP は DSR、UDP は SNAT を使用する。これは有効な load-balancer 動作であり、無効な tunnel/auto-direct-routing の組み合わせとは異なる |
| Annotation-based forwarding | Service ごとにサポートされる opt-in 動作。forwarding annotation は作成時の選択であり、変更すると接続が切断される可能性がある |
| `loadBalancer.algorithm: random` | デフォルトの BPF backend-selection algorithm |
| `maglev` | サポート対象の XDP acceleration を含む、サポート対象の external N–S path の一貫した選択。通常の socket-LB E–W connection は Maglev の対象ではない |
| `sessionAffinity: ClientIP` | 個別の Kubernetes Service affinity。key は external source IP、または該当する in-cluster socket-LB traffic では client の network-namespace cookie |

Maglev は、backend removal 後も session が維持される保証ではありません。ノードには一貫した backend state、table size、および seed が必要です。デフォルトの table size は 16381 です。以下で使用する 65521 は許可された値であり、普遍的な推奨ではありません。より大きな table はメモリを消費します。affinity expiry と connection state は hashing とは別のものです。

DSR dispatch は、native-routing IP options、文書化された native/Geneve-overlay configuration での Geneve、または文書化された native-only の IPIP/IP6IP6 パスを使用できます。VXLAN overlay は Geneve DSR dispatch と交換可能ではありません。IPIP には独自の port/translation 制約があります。選択する前にリリースガイドを確認してください。

XDP acceleration にはサポート対象の device/driver が必要です。`native` は選択した device がそれをサポートしていることを想定し、`best-effort` はサポートされる場所で有効にします。以前の `enable-xdp-acceleration` key を書くだけで有効になるわけではありません。また、初期の XDP forwarding は tcpdump の後段の capture point では見えない場合があります。

### Cilium と kube-proxy

| 観点 | 正しい比較 |
|---|---|
| Linux Service 実装 | Cilium は BPF hook/map を使用する。kube-proxy には iptables および nftables モードがあり、IPVS は Kubernetes 1.35 以降非推奨 |
| プラットフォーム | Cilium が表明する Linux/kernel 要件が適用される。Windows kernelspace kube-proxy は異なる実装 |
| 接続状態 | Cilium BPF connection/NAT state は Linux netfilter conntrack とは異なる。「optional 対 always」という表現は広すぎる |
| L7 | Cilium はサポート対象の proxy を統合する。kube-proxy の Service forwarding は HTTP policy engine ではない |
| パフォーマンス | 同じ workload と configuration を測定する。どちらの製品名も固定順位を確立しない |

基盤となる Linux IPVS subsystem に direct-routing capabilities があるからといって、kube-proxy DSR configuration を推測しないでください。

## 準備済み DSR/Maglev ラボ

このプロファイルは、新しい準備済みの kube-proxy-free **IPv4 Geneve-overlay** テストクラスタ用です。既存 CNI の移行、kube-proxy の削除、または cloud anti-spoofing/routing control の設定は行いません。競合しない Pod CIDR を使用し、external return path を検証してください。

**`lb-values.yaml`**

```yaml
kubeProxyReplacement: true
routingMode: tunnel
tunnelProtocol: geneve
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
loadBalancer:
  mode: dsr
  dsrDispatch: geneve
  algorithm: maglev
  acceleration: disabled
maglev:
  tableSize: 65521
bpf:
  masquerade: true
enableIPv4Masquerade: true
enableIPv6Masquerade: false
l7Proxy: true
envoy:
  enabled: true
hubble:
  enabled: true
  relay:
    enabled: true
```


実際の API endpoint と、クラスタごとに永続化された Maglev seed を 1 つ指定してください。seed は 12 random byte の base64 encoding です。一度生成してクラスタの values と共に保存し、upgrade ごとに再生成するのではなく再利用してください。

```bash
: "${API_SERVER_HOST:?Set the reachable real API server host, not its ClusterIP}"
: "${API_SERVER_PORT:?Set the actual API server port}"
: "${MAGLEV_SEED:?Set the persisted base64 encoding of 12 random bytes}"
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
helm install cilium cilium/cilium --version 1.20.2 --namespace kube-system \
  --values lb-values.yaml \
  --set-string k8sServiceHost="$API_SERVER_HOST" \
  --set k8sServicePort="$API_SERVER_PORT" \
  --set-string maglev.hashSeed="$MAGLEV_SEED"
cilium status --wait
```

選択したクラスタでは、このガイドで作成した namespace を使用してください。これが別の使い捨てクラスタである場合は、最初にそこで namespace の作成/label 手順を繰り返してください。HTTP-policy application とこの external-LB backend では異なる label を使用するため、先行する client 専用 HTTP rule がこの実験を誤ってブロックすることはありません。

**`lb-echo.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lb-echo
  namespace: cilium-l2l7-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: lb-echo
  template:
    metadata:
      labels:
        app: lb-echo
    spec:
      automountServiceAccountToken: false
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
  name: lb-echo
  namespace: cilium-l2l7-demo
spec:
  type: NodePort
  selector:
    app: lb-echo
  ports:
  - name: http
    port: 80
    targetPort: http
    protocol: TCP
```


```bash
kubectl apply -f lb-echo.yaml
kubectl -n cilium-l2l7-demo rollout status deployment/lb-echo --timeout=120s
kubectl -n cilium-l2l7-demo get pods -l app=lb-echo -o wide
kubectl -n cilium-l2l7-demo get service lb-echo -o wide
NODEPORT=$(kubectl -n cilium-l2l7-demo get service lb-echo -o jsonpath='{.spec.ports[0].nodePort}')
```

backend node **とは異なる**到達可能な ingress node と、Cilium の in-cluster socket LB の対象ではない external client を使用してください。その client から、実際の値を使用して `http://ENTRY_NODE_IP:NODEPORT/` をリクエストします。Pod-to-ClusterIP curl は external DSR も Maglev の動作も証明しません。request/response path と backend/connection state を検証してください。HTTP response の成功だけからそれらを推測しないでください。

## マスカレード

Pod egress masquerading は、設定された external path に必要な場合に source address を変更します。これは encryption や firewall ではなく、Service DNAT および DSR forwarding とは異なります。

次のフラグメントは、network がそれらの Pod source/return route を実際にサポートする場合にのみ、例の `10.0.0.0/8` destination range を source masquerading から除外します。

**`masquerade-values.yaml`**

```yaml
bpf:
  masquerade: true
enableIPv4Masquerade: true
enableIPv6Masquerade: false
ipv4NativeRoutingCIDR: 10.0.0.0/8
```


`ipv4NativeRoutingCIDR` は想定される routable range と対応する masquerade exclusion を表します。これは route をインストールしたり、datapath 全体を native routing に切り替えたりするものではありません。動作する return route のない広範な除外は接続性を破壊する可能性があります。

- BPF masquerading は、このリリースでは BPF NodePort feature に依存し、BPF program を持つ device にのみ適用されます。選択された device を調べ、必要に応じて文書化された `devices` configuration を使用してください。
- iptables implementation は、文書化された `egressMasqueradeInterfaces` の動作を使用します。その field や、削除された汎用的な `masquerade-interfaces`/`masquerade-all` の例を、普遍的な BPF control とみなさないでください。
- IPv6 BPF masquerading はベータ版として文書化されています。どちらの implementation も Cilium の platform/kernel 要件を取り除くものではなく、最終的にはいずれも kernel 内で traffic を処理します。
- node-address exception、ip-masq-agent exclusion、および後段の cloud/NAT gateway が観測される source に影響する可能性があります。制御された observer と node 側の state/capture を使用してください。任意の public site に到達できても、特定の NAT implementation が証明されるわけではありません。

該当する agent 上で実行します。

```bash
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
export CILIUM_POD=cilium-REPLACE-WITH-AGENT-ON-TARGET-NODE
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf nat list
```

## フラグメント処理と MTU

リリース済み fragment tracker は、datagram identity と L4 source/destination port を、サイズ上限のある LRU map に保存します。L4 header を持たない後続 fragment の port context を復元できますが、**BPF payload-reassembly engine ではなく**、fragment attack に対する保証でもありません。

文書化された機能には IPv4 と IPv6 の tracking が含まれ、対応する flag によりデフォルトで有効化され、ベータ版とされています。有効な IPv4 flag は引き続き `enable-ipv4-fragment-tracking` です。`bpf-fragments-map-max` は追跡される datagram map capacity を制御します。以前の `fragment-tracking-timeout` および `max-fragments-per-flow` 設定はリリース済み configuration contract には含まれません。

chart の追加 configuration map を使用する明示的な例です。

**`fragment-values.yaml`**

```yaml
extraConfig:
  enable-ipv4-fragment-tracking: 'true'
  bpf-fragments-map-max: '8192'
```


8192 は capacity の例であり、flow あたりの fragment の最大数ではありません。capacity を診断する際は `cilium_ipv4_frag_datagrams` / `cilium_ipv6_frag_datagrams` とその pressure を調べてください。pressure は reassembly-success または attack-prevention のカウンターではありません。

正しい packet sizing と、動作する path MTU discovery path を優先してください。PMTUD は関連する error signaling と network behavior に依存しており、どこでも自動的な最適サイズ設定を保証するものではありません。Cilium の `MTU` は **underlying-network override** です。[ネットワーキングガイド](03-networking.md)で説明しているように、通常の VXLAN overhead は IPv4 underlay では 50 byte、IPv6 では 70 byte です。1500-byte path に対して base を盲目的に 1450 に設定すると、overhead を二重に差し引く可能性があります。

## 可観測性とトラブルシューティング

正しい node、実際の Envoy deployment mode、目的の policy、実現された endpoint state、および新しい traffic を調べてください。agent-local operation には `cilium-dbg` を、cluster operation には standalone CLI を使用します。削除された `policy trace` command や強制 endpoint regeneration は、この診断の出発点ではありません。

有効な Hubble Relay port-forward を別の terminal で実行したままにし、関連する flow を観察します。

```bash
cilium hubble port-forward
```

```bash
hubble observe --namespace cilium-l2l7-demo --protocol http --last 20
hubble observe --namespace cilium-l2l7-demo --verdict DROPPED --last 20
```

HTTP policy rejection は packet DROPPED verdict ではなく HTTP 403 として現れる場合があります。timeout だけでも readiness、DNS、routing、TLS、または observation の問題を意味することがあります。すべての error を policy success と解釈せず、レイヤーを相関付けてください。

## 検証の制限とソース

これらはリリースの source/schema を確認済みで、範囲を限定した local fixture を用いる例であり、production-tested platform や live-cluster benchmark ではありません。image execution、webhook reachability、mTLS traffic、DSR return path、NAT behavior、および fragmentation には、準備済み環境での検証が引き続き必要です。この実行で label 付けした application resource のみをクリーンアップしてください。ラボのクリーンアップとして cluster CNI を削除しないでください。

- [Cilium kube-proxy replacement/DSR/Maglev](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/kubeproxy-free.rst)、[masquerading](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/masquerading.rst)、[fragment handling](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/fragmentation.rst)、[fragment map implementation](https://github.com/cilium/cilium/blob/v1.20.2/pkg/maps/fragmap/fragmap.go)
- [L2 Announcements](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/l2-announcements.rst)、[multicast](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/multicast.rst)、[HTTP rule translator](https://github.com/cilium/cilium/blob/v1.20.2/pkg/envoy/policy/envoy_l7_rules_translator.go)、[Envoy chart defaults](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/templates/_helpers.tpl)
- [Cilium/Istio integration](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/servicemesh/istio.rst)、[Istio CNI/init-container modes](https://istio.io/latest/docs/setup/additional-setup/cni/)、[webhook requirements](https://istio.io/latest/docs/ops/configuration/mesh/webhook/)、[Istio 1.31 schemas](https://github.com/istio/istio/blob/1.31.0/manifests/charts/base/files/crd-all.gen.yaml)
- [Kubernetes Service proxy modes/affinity](https://kubernetes.io/docs/reference/networking/virtual-ips/)、[Cilium 1.20.2 values](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/values.yaml)


[メインページに戻る](README.md)

## クイズ

[L2–L7 とロードバランシングの問題を確認する](../../quizzes/networking/cilium/05-l2-l7-networking-quiz.md).
