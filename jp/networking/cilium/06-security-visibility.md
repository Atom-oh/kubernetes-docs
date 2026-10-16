# セキュリティと可視性

> **レビュー基準**: Cilium 1.20.2; Cilium CLI 0.20.1; Hubble CLI 1.20.2。
> **最終更新**: October 15, 2026。Kubernetes 1.33–1.36 は Cilium 1.20 の互換性範囲です。kubectl は API server でサポートされるバージョンスキューの範囲内で選択してください。

## ラボ環境のセットアップ

少なくとも 2 台のスケジュール可能な Linux node、正常に動作する DNS、および有効な policy enforcement を備えた既存の Cilium 1.20.2 テストクラスターを使用します。EKS の制限事項と検証済み CLI ダウンロードを含む、[インストールおよびプラットフォームの前提条件](README.md)に従ってください。これらの例では CNI をインストールまたは置換しません。Helm、kubectl、Cilium および Hubble CLI、jq が必要です。

このラボは、`kube-system` 内で `k8s-app=kube-dns` のラベルを持つ CoreDNS Pod を前提としています。実際の resolver パスを確認してください。NodeLocal DNS または別の distribution では、異なる宛先または port が必要です。クラスターにすでに存在する policy、proxy 設定、プラットフォーム制御は結果に影響する可能性があります。

### Hubble のインストールとセットアップ

`hubble-values.yaml` を保存します。このフラグメントは、ローカル server、Relay、UI、および選択した metric plugin を有効にします。**同じ chart version の既存 release** に適用してください。最初に保持されるインストール値を確認します。version upgrade では、古い値を無批判に再利用するのではなく upgrade 手順を使用してください。

```yaml
# hubble-values.yaml
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
    - httpV2
    serviceMonitor:
      enabled: false
```
```bash
helm upgrade cilium cilium/cilium --namespace kube-system \
  --version 1.20.2 --reuse-values --values hubble-values.yaml --wait
cilium status --wait
# Terminal 1: keep this process running; stop it with Ctrl-C.
cilium hubble port-forward
```

別の terminal で API 接続を確認します。port forwarding はローカルに留まり、Relay または UI をパブリック LoadBalancer 経由で公開しません。

```bash
# Terminal 2
hubble status
hubble observe --last 20
# Optional UI; keep its local forwarding process running while using it.
cilium hubble ui
```

## Cilium のセキュリティ機能

Cilium は network policy を endpoint identity およびオプションの encryption と組み合わせます。Hubble は結果として生じる network event を可視化します。セキュリティ要件を評価する際には、その境界を理解することが重要です。

### Cilium セキュリティアーキテクチャ

| 責務 | コンポーネントと範囲 |
| --- | --- |
| ネットワークマイクロセグメンテーション | Cilium L3/L4 policy は identity、address、port、direction を選択します。namespaced CiliumNetworkPolicy はその namespace 内の endpoint を選択します。 |
| HTTP policy | Cilium の Envoy 統合は、proxy が HTTP を確認できる場合に method、path、header をフィルタリングします。DNS policy は DNS proxy を使用します。 |
| DNS/FQDN 制御 | DNS rule は query を制御します。`toFQDNs` は、観測された DNS answer から学習した destination IP を許可します。これは自動的な悪意ある domain の reputation feed ではありません。 |
| Node 間トランスポート暗号化 | IPsec または WireGuard は node 間のサポート対象 traffic を保護します。対象範囲は mode と設定に依存します。 |
| ネットワーク調査 | Hubble は flow metadata と policy verdict を記録し、Relay、CLI、UI がそれらを公開します。 |
| Process と syscall のセキュリティ | **Tetragon** は runtime event と設定済み enforcement のための別プロジェクトです。Hubble を有効にしてもインストールされません。 |
| 脅威検知と対応 | 意図した検知とアクションのためには、外部 alert rule、SIEM/WAF、response controller を設定する必要があります。 |

### ネットワークおよびアプリケーションセキュリティ

最小権限 policy を使用して lateral movement を制限し、明示的な egress によって dependency を限定します。security identity はセキュリティ関連 label から導出されます。必ずしも Pod ごとに一意ではなく、end user を認証しません。

現在の Cilium policy は HTTP および DNS L7 rule をサポートします。gRPC は HTTP/2 traffic が可視である場合、HTTP の method/path/header rule を使用できます。Kafka topic policy はサポートされなくなりました。値を含む HTTP `headers` エントリは literal match であり、regular-expression authentication ではありません。`Authorization` header の存在または形式は、JWT、その issuer、signature、authorization claim を検証しません。そのためにはアプリケーションの authentication layer または設定済み gateway を使用してください。

port 8443 の HTTP rule は HTTPS を復号しません。HTTP policy が暗号化された application data を評価するには、TLS termination または別途サポートされる inspection 構成が必要です。L7 inspection を機能させるためだけに service mesh の encryption をバイパスしないでください。

### Identity、Authentication、Encryption

Cilium の SPIRE ベース **mutual authentication は Beta ですが、1.20 では deprecated です**（1.21 pre-release で削除されました。upgrade note では代替として ztunnel が示されているため、新しい設計には選択しないでください）。これは security identity のために out-of-band handshake を実行します。この handshake 単独では application traffic を暗号化しません。文書化されている制約には、ClusterMesh のサポートなし、および任意の外部 mTLS system との相互運用性なしが含まれます。別機能の **ztunnel workload mTLS feature も Beta** です。独自の enrollment および certificate 前提条件があります。いずれの機能も identity selector の自動的な結果として提示すべきではありません。

### Encryption 設定

以下は**代替となる Helm フラグメント**であり、同時に有効化する 2 つの設定ではありません。計画済みの installation/change に対して 1 つを選択し、kernel、routing、platform の前提条件を検証してください。

```yaml
# wireguard-values.yaml
encryption:
  enabled: true
  type: wireguard
  nodeEncryption: false
```
```yaml
# ipsec-values.yaml
encryption:
  enabled: true
  type: ipsec
  nodeEncryption: false
  ipsec:
    secretName: cilium-ipsec-keys
```

WireGuard には kernel support と port 51871 上の node-to-node UDP path が必要です。IPsec を有効にする前には、Cilium の namespace 内に正しく形式化され、安全に管理された `cilium-ipsec-keys` Secret が必要です。公式の key 作成および rotation 手順に従ってください。ConfigMap 内で key file に名前を付けるだけでは、その key または volume は provision されません。

デフォルトでは、これらの mode は node をまたぐサポート対象の Cilium 管理 Pod traffic を保護します。同一 node の traffic はこれらの node tunnel では暗号化されません。任意の外部 destination への traffic は自動的には対象になりません。WireGuard node-to-node encryption（`encryption.nodeEncryption`）は別の Beta option であり、1.21 pre-release で deprecated、1.22 での削除が予定されています。この拡張では control-plane node はデフォルトで除外されますが、それらの Cilium 管理 cross-node Pod traffic は引き続き暗号化できます。実際の packet path を確認し、必要に応じて application TLS を使用してください。host firewall の互換性も encryption mode に依存します。host policy は IPsec と併用できません（1.21 pre-release の host-policy known issue に記載）。

## Hubble によるネットワーク可視性

Hubble は datapath、proxy、agent event を受け取り、Kubernetes metadata で拡充します。すべての eBPF map を定期的に poll するだけの reader ではありません。

```text
Kernel/datapath events + proxy/agent events
                  |
                  v
       Hubble server in each Cilium agent
          |             |                |
   bounded flow      metric endpoint   optional file exporter
      buffer          TCP 9965            |
          |             ^             log collector/storage
     Relay query        | scrape
          ^          Prometheus <--- Grafana queries
          |
       CLI / UI
```

server は上限のある in-memory history を維持します。Relay は複数の server に query します。永続 database ではありません。UI は flow exploration と service dependency map を提供し、CLI は明示的な filter をサポートします。一致する record がないことは、traffic がない、filter が誤っている、peer が利用不可、L7 visibility がない、または event が上書き・喪失したことを意味する可能性があります。

### Hubble CLI 使用例

```bash
hubble observe --namespace cilium-security-demo --last 100
hubble observe --from-pod cilium-security-demo/frontend \
  --to-service cilium-security-demo/backend --last 100
hubble observe --namespace cilium-security-demo --protocol http \
  --http-status '4+' --http-status '5+' --last 100
hubble observe --namespace cilium-deny-demo --verdict DROPPED \
  --drop-reason-desc POLICY_DENIED --last 100
hubble observe --pod cilium-security-demo/frontend --follow
```

`--pod namespace/name` はいずれかの endpoint に一致します。direction には `--from-pod`/`--to-pod` を使用してください。Pod 名は label selector ではありません。label を選択する場合は `--from-label` または `--to-label` を使用してください。`--namespace` と `--from-pod`/`--to-pod` を組み合わせないでください。CLI はその組み合わせを拒否します。

`DROPPED` は verdict です。`POLICY_DENIED` は drop reason であり、`--drop-reason-desc` で選択します。HTTP status prefix には `4..` と `5..` ではなく `4+` と `5+` を使用します。HTTP filter には proxy 由来の L7 event が必要です。drop された TCP connection には HTTP status がない場合があります。

## ネットワーク可視性と監視

### Hubble Metrics

有効な plugin は異なる観測結果を公開します。

| Plugin | メトリクス例 | 意味と制限 |
| --- | --- | --- |
| `flow` | `hubble_flows_processed_total` | protocol/type/verdict 別の処理済み flow event。すべての path における一意の request や packet ではありません。 |
| `drop` | `hubble_drop_total{reason="POLICY_DENIED"}` | 観測された drop。reason label は enum 名です。 |
| `tcp` | `hubble_tcp_flags_total` | 観測された TCP flag。一般的な RTT、retransmission、concurrent connection の metric ではありません。 |
| `dns` | `hubble_dns_queries_total`, `hubble_dns_responses_total` | 観測された DNS query/response と response code。汎用的な DNS latency histogram ではありません。 |
| `httpV2` | `hubble_http_requests_total`, `hubble_http_request_duration_seconds` | HTTP response-flow 由来の request count/status と秒単位の duration。HTTP visibility が必要です。 |

`http` と `httpV2` を同時に有効化しないでください。cardinality を制御するため source/destination label を慎重に選択し、理由なく request header や機密 identity を追加しないでください。event がないことを traffic が発生しなかった証拠と扱う前に、`hubble_lost_events_total` と peer availability を確認してください。

### Prometheus 統合

chart は Cilium namespace に headless `hubble-metrics` Service を作成し、デフォルトで port **9965** を公開します。検出には Service label `k8s-app=hubble` が使用され、Service は `k8s-app=cilium` の label を持つ agent Pod を選択します。Prometheus は静的な DNS target 1 つに依存するのではなく、個々の endpoint を検出する必要があります。

既存の Prometheus Operator と ServiceMonitor CRD がある場合、このフラグメントを release values にマージします。`release: monitoring` は例です。Prometheus の `serviceMonitorSelector` と一致させ、その namespace selector には ServiceMonitor の namespace を含める必要があります。Prometheus が選択しない resource は scrape されません。

```yaml
# hubble-servicemonitor-values.yaml
hubble:
  metrics:
    serviceMonitor:
      enabled: true
      labels:
        release: monitoring
```

chart の ServiceMonitor は named port `hubble-metrics` と Cilium namespace の endpoint を使用します。Operator がない場合は、実際の Prometheus 設定で同等の Kubernetes service discovery を構成してください。無関係な ConfigMap を作成しても Prometheus は設定されません。`*.hubble-metrics.cilium.io` は metrics TLS identity 設定で使用されます。port 9091 上のパブリック scrape target ではありません。

Grafana dashboard は Prometheus metrics に query し、Hubble UI の service map は Relay に query します。有効な plugin と label に一致する dashboard を import してください。HTTP payload が観測不能な traffic では HTTP dashboard は空になります。

### Flow Export と保持

node-local rotated file には、必要に応じて `hubble-export-values.yaml` をマージします。field mask は意図的に network metadata を保持しており、完全な HTTP header は export しません。

```yaml
# hubble-export-values.yaml
hubble:
  export:
    static:
      enabled: true
      filePath: /var/run/cilium/hubble/events.log
      fileMaxSizeMb: 10
      fileMaxBackups: 5
      fieldMask:
      - time
      - source.namespace
      - source.pod_name
      - destination.namespace
      - destination.pod_name
      - l4
      - IP
      - node_name
      - is_reply
      - verdict
      - drop_reason_desc
```

static exporter は各 node に書き込み、その file 設定に従って rotation します。event が node loss を超えて残る必要がある場合は、別の collector、access control、storage retention を用意してください。static 設定の変更には agent rollout が必要です。dynamic exporter は異なる update behavior をサポートします。exporter filter と field mask は意図的に event/field を省略でき、有限の buffer により依然として観測結果が失われる可能性があります。

## リアルタイム脅威検知

Hubble は調査のための証拠を提供します。完全な IDS、WAF、または自動 quarantine system にする switch は含まれません。`enable-threat-detection`、`enable-anomaly-detection`、`alert-to-slack` という名前のサポート対象 Cilium 設定はありません。

繰り返される denied destination は scanning を示唆することがあり、traffic spike は調査を正当化する可能性があります。これらの観測は攻撃の証拠ではありません。アプリケーション authentication log、workload の変更、API audit event、および導入されている場合は Tetragon runtime event と相関付けてください。SQL injection、XSS、command injection には適切な application/WAF/detection rule が必要です。通常の HTTP flow record だけではこれらを分類しません。

alert には、通常の traffic、欠損データ、event loss に対して外部 Prometheus/SIEM rule を定義してテストしてください。rate limit、firewall isolation、response automation は別途設定する制御です。response scope を制限し、recovery path を用意してください。drop packet を記録したすべての Pod を自動的に隔離しないでください。

## ラボ: Hubble のインストールと使用

このラボでは、広範な allow rule が default-deny の演習を無効にできないように、**新規で分離された 2 つの namespace** を使用します。database または外部 API は作成しません。command はテストクラスター用の例です。ドキュメント監査では schema とローカル fixture を確認しており、live deployment は確認していません。

### 1. Workload の作成と確認

`visibility-app.yaml` を保存します。client と server の image は Cilium CLI の versioned test default に一致します。Backend anti-affinity は 2 台目のスケジュール可能 node を必要とし、frontend-to-backend path を cross-node にします。

```yaml
# visibility-app.yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend
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
spec:
  selector:
    app: backend
  ports:
  - name: http
    port: 8080
    targetPort: http
    protocol: TCP
```
```bash
set -eu
for ns in cilium-security-demo cilium-deny-demo; do
  kubectl create namespace "$ns"
  kubectl label namespace "$ns" audit-lab=security-visibility
  kubectl --namespace "$ns" apply -f visibility-app.yaml
  kubectl --namespace "$ns" wait --for=condition=Ready pod/frontend pod/outsider --timeout=120s
  kubectl --namespace "$ns" rollout status deployment/backend --timeout=120s
  for client in frontend outsider; do
    kubectl --namespace "$ns" exec "$client" -- \
      curl --fail --silent --show-error --max-time 5 http://backend:8080/
  done
done
```

policy を適用する前に、両方の namespace の両方の client が backend に到達できなければなりません。到達できない場合は、まず readiness、scheduling、DNS、network の問題を解決してください。任意の curl error から policy denial を推論しないでください。

### 2. HTTP Policy の適用と観測

`backend-http.yaml` を保存します。これは `frontend` identity が backend TCP 8080 に `GET /` を送ることを許可します。この例と重複する広範な ingress rule は作成しないでください。L4 allow は意図した L7 restriction をバイパスできます。

```yaml
# backend-http.yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-http
  namespace: cilium-security-demo
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-security-demo
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: GET
          path: /
```
```bash
kubectl apply -f backend-http.yaml
# After the endpoint has realized the policy:
kubectl -n cilium-security-demo exec frontend -- \
  curl --fail --silent --show-error --max-time 5 http://backend:8080/
# Display the HTTP response code; do not use --fail here.
kubectl -n cilium-security-demo exec frontend -- \
  curl --silent --show-error --max-time 5 --output /dev/null \
    --write-out '%{http_code}\n' --request POST http://backend:8080/
# A separate client is not in the allowed identity selector.
kubectl -n cilium-security-demo exec outsider -- \
  curl --silent --show-error --max-time 5 http://backend:8080/
hubble observe --namespace cilium-security-demo --verdict DROPPED --last 100
```

policy の実現後は、frontend の `GET /` は成功し、その `POST /` は proxy の HTTP 403 を受信するはずです。outsider の新しい connection は L3/L4 で拒否されるはずです。request 時刻、endpoint、Hubble event を相関付けてください。DNS error、欠落した container、無関係な HTTP error は、denial test の成功を意味しません。Hubble UI を使用して、生成された dependency edge と drop を確認してください。

実際に database と外部 API を必要とする backend では、次の**任意の dependency policy**が egress を例示します。このラボでは適用されません。`database` と `api.example.com` は実際の dependency に置き換える必要があります。最初に DNS endpoint を確認してください。

```yaml
# backend-dependencies.yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-dependencies
  namespace: cilium-security-demo
spec:
  endpointSelector:
    matchLabels:
      app: backend
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
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-security-demo
        k8s:app: database
    toPorts:
    - ports:
      - port: '3306'
        protocol: TCP
  - toFQDNs:
    - matchName: api.example.com
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

TCP と UDP の DNS が許可され、DNS proxy rule により Cilium は `toFQDNs` で使用される answer を観測できます。DNS query の許可は、解決された IP への後続 connection の許可とは異なります。この policy の DNS `*` はすべての query 名を許可します。domain blocklist ではありません。

### 3. Default Deny を個別に検証

`deny-except-dns.yaml` を保存します。明示的な `policyTypes` により両方向の isolation が有効になります。`ingress: []` には**ingress allow rule がありません**。単一の egress exception は、一致した resolver Pod への DNS のみを許可します。

```yaml
# deny-except-dns.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-except-dns
  namespace: cilium-deny-demo
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```
```bash
kubectl apply -f deny-except-dns.yaml
kubectl -n cilium-deny-demo exec frontend -- \
  curl --silent --show-error --max-time 5 http://backend:8080/
hubble observe --namespace cilium-deny-demo --verdict DROPPED \
  --drop-reason-desc POLICY_DENIED --last 100
```

空の ingress list を `ingress: [{}]` に置き換えないでください。これは allow-all ingress rule です。標準 NetworkPolicy の allow は加算的であるため、別の policy が traffic を開放する可能性があります。Cilium deny rule と cluster policy はさらに制限を課すことがあります。この namespace の演習は、host-network traffic またはすべての host-originated path を隔離すると主張するものではありません。

### 4. JSON の検査とローカル概要の Export

以下を `flow-summary.jq` として保存します。`--output jsonpb` は `.flow` を持つ protobuf response envelope を提供します。これにより CLI の legacy `json` compatibility 設定への依存を回避します。

```text
[.[] | select(.flow != null) | .flow] as $flows
| {
    flow_records: ($flows | length),
    other_records: (length - ($flows | length)),
    policy_denied_records: (
      [$flows[] | select(.verdict == "DROPPED"
                        and .drop_reason_desc == "POLICY_DENIED")] | length
    ),
    dropped_by_reason: (
      [$flows[] | select(.verdict == "DROPPED")]
      | group_by(.drop_reason_desc // "UNKNOWN")
      | map({reason: (.[0].drop_reason_desc // "UNKNOWN"), records: length})
    )
  }
```

```bash
set -eu
hubble observe --namespace cilium-deny-demo --last 100 --output jsonpb > flows.jsonl
jq --slurp --from-file flow-summary.jq flows.jsonl
```

結果は**この有限の sample 内の flow record**を数えます。一意の attack、connection、またはすべての cluster packet ではありません。non-flow record は個別に数えます。loss/status 情報についてそれらを確認してください。live のローカル filter には次を使用します。

```bash
hubble observe --namespace cilium-deny-demo --follow --output jsonpb |
  jq --unbuffered -c 'select(.flow.verdict == "DROPPED"
    and .flow.drop_reason_desc == "POLICY_DENIED")'
```

この pipeline はローカルに出力します。notification には、別途設定した integration、credential、retry/deduplication policy、および stream failure の処理が必要です。

### 5. テスト Namespace のクリーンアップ

namespace 名を確認した後、このラボの workload と policy のみを削除します。ownership check は lookup failure または異なる label で停止します。

```bash
set -eu
for ns in cilium-security-demo cilium-deny-demo; do
  LAB_OWNER=$(kubectl get namespace "$ns" -o jsonpath='{.metadata.labels.audit-lab}')
  test "$LAB_OWNER" = security-visibility
  kubectl delete namespace "$ns"
done
```

## 主なリファレンス

- [Cilium policy enforcement](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/security/policy/intro.rst)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [HTTP policy](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/security/policy/layer7.rst)
- [DNS policy](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/security/dns.rst)
- [Hubble セットアップ](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/observability/hubble/setup.rst)
- [Metrics](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/observability/metrics.rst)
- [Flow exporter](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/observability/hubble/configuration/export.rst)
- [WireGuard](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/security/network/encryption-wireguard.rst)
- [IPsec](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/security/network/encryption-ipsec.rst)
- [Mutual authentication](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
- [ztunnel](https://raw.githubusercontent.com/cilium/cilium/v1.20.2/Documentation/security/network/encryption-ztunnel.rst)
- [Tetragon](https://raw.githubusercontent.com/cilium/tetragon/main/README.md)
- [Hubble CLI filter](https://raw.githubusercontent.com/cilium/hubble/v1.20.2/vendor/github.com/cilium/cilium/hubble/cmd/observe/flows.go)

[メインページに戻る](README.md)

## クイズ

[トピッククイズ](../../quizzes/networking/cilium/06-security-visibility-quiz.md)で policy、encryption、observability の境界をテストしてください。
