# セキュリティと可視性

> **レビュー時の基準**: Cilium 1.20.3、Cilium CLI 0.20.1、Hubble CLI 1.20.2。
> **最終レビュー日**: 2026年10月16日。Kubernetes 1.33～1.36がCilium 1.20の互換範囲です。kubectlはAPIサーバーがサポートするバージョンスキューの範囲内で選択してください。

## ラボ環境の準備

Cilium 1.20.3を導入済みのテストクラスターを使用します。少なくとも2台のスケジュール可能なLinuxノードがあり、DNSが機能し、ポリシーの適用が有効であることを確認してください。[インストールとプラットフォームの前提条件](README.md)に従い、EKS上の制限事項と検証済みCLIのダウンロード方法も確認します。この例ではCNIをインストールしたり置き換えたりしません。Helm、kubectl、Cilium CLI、Hubble CLI、jqが必要です。

このラボでは、`kube-system`内に`k8s-app=kube-dns`ラベルが付いたCoreDNS Podがあることを前提にしています。実際の名前解決経路を確認してください。NodeLocal DNSや別のディストリビューションを使う場合、宛先やポートが異なります。クラスターにすでに適用されているポリシー、プロキシ設定、プラットフォーム制御によって結果が変わる場合があります。

### Hubbleのインストールと設定

`hubble-values.yaml`を保存します。この設定断片は、ローカルサーバー、Relay、UI、および選択したメトリクスプラグインを有効にします。**同じチャートバージョンの既存リリース**に適用してください。先に、現在のインストール値と保持する設定を確認します。バージョンをアップグレードする場合は、古い値をそのまま再利用せず、アップグレード手順に従ってください。

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
  --version 1.20.3 --reuse-values --values hubble-values.yaml --wait
cilium status --wait
# Terminal 1: keep this process running; stop it with Ctrl-C.
cilium hubble port-forward
```

別のターミナルでAPI接続を確認します。ポートフォワードはローカル接続のままです。RelayやUIをパブリックなLoadBalancer経由で公開するものではありません。

```bash
# Terminal 2
hubble status
hubble observe --last 20
# Optional UI; keep its local forwarding process running while using it.
cilium hubble ui
```

## Ciliumのセキュリティ機能

Ciliumはネットワークポリシー、エンドポイントのアイデンティティ、オプションの暗号化を組み合わせます。Hubbleを使うと、それらによって生じたネットワークイベントを観測できます。セキュリティ要件を評価する際は、それぞれの適用範囲を把握してください。

### Ciliumのセキュリティアーキテクチャ

| 責務 | コンポーネントと適用範囲 |
| --- | --- |
| ネットワークのマイクロセグメンテーション | CiliumのL3/L4ポリシーでアイデンティティ、アドレス、ポート、通信方向を選択します。名前空間スコープのCiliumNetworkPolicyは、その名前空間内のエンドポイントを選択します。 |
| HTTPポリシー | EnvoyからHTTPを確認できる場合、CiliumのEnvoy連携でメソッド、パス、ヘッダーをフィルタリングします。DNSポリシーではDNSプロキシを使います。 |
| DNS/FQDN制御 | DNSルールでクエリを制御します。`toFQDNs`は、観測したDNS応答から学習した宛先IPアドレスへの通信を許可します。悪意あるドメインの評判情報を自動的に提供する機能ではありません。 |
| ノード間通信の暗号化 | IPsecまたはWireGuardで、サポート対象となるノード間通信を保護します。保護範囲はモードと設定によって異なります。 |
| ネットワークの調査 | Hubbleはフローメタデータとポリシーの判定結果を記録し、Relay、CLI、UIから参照できるようにします。 |
| プロセスとシステムコールのセキュリティ | **Tetragon**は、ランタイムイベントと設定済みの強制制御を扱う別のプロジェクトです。Hubbleを有効にしてもTetragonはインストールされません。 |
| 脅威の検知と対応 | 想定する検知と対応を実現するには、外部アラートルール、SIEM/WAF、対応コントローラーを別途設定する必要があります。 |

### ネットワークとアプリケーションのセキュリティ

最小権限のポリシーで横方向の移動を制限し、明示的な送信先制御で依存関係を絞ります。セキュリティアイデンティティはセキュリティ上意味のあるラベルから導かれますが、Podごとに一意とは限らず、エンドユーザーを認証するものでもありません。

現在のCiliumポリシーはHTTPとDNSのL7ルールをサポートします。HTTP/2の通信を確認できる場合、gRPCにはHTTPのメソッド、パス、ヘッダーのルールを適用できます。Kafkaトピックポリシーは現在サポートされていません。値を指定したHTTPの`headers`項目はリテラル一致であり、正規表現による認証ではありません。`Authorization`ヘッダーが存在するか、その形式が正しいかだけでは、JWTの発行者、署名、認可クレームは検証できません。アプリケーションの認証レイヤーまたは設定済みゲートウェイを使用してください。

ポート8443にHTTPルールを設定してもHTTPSは復号されません。暗号化されたアプリケーションデータをHTTPポリシーで評価するには、TLS終端、または別途サポートされる検査方式が必要です。L7検査を可能にするためだけにサービスメッシュの暗号化を迂回しないでください。

### アイデンティティ、認証、暗号化

CiliumのSPIREベースの**相互認証はBetaですが、1.20で非推奨です**（1.21のプレリリースで削除されました。1.20のアップグレードノートでは相互認証を非推奨とし、代替としてztunnel透過暗号化を案内しています。そのため新しい設計では選択しないでください）。この機能はセキュリティアイデンティティのための帯域外ハンドシェイクを行いますが、ハンドシェイクだけでアプリケーション通信が暗号化されるわけではありません。文書化された制約として、ClusterMeshをサポートせず、任意の外部mTLSシステムとも相互運用できません。別機能である**ztunnelワークロードmTLSもBeta**であり、独自の登録と証明書の前提条件があります。どちらの機能も、アイデンティティセレクターを指定すれば自動的に有効になるものとして説明してはいけません。

### 暗号化の設定

以下は**相互に代替となるHelm設定断片**であり、両方を同時に有効にする設定ではありません。計画したインストールまたは変更に対して一方を選び、カーネル、ルーティング、プラットフォームの前提条件を検証してください。

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

WireGuardにはカーネルのサポートと、ノード間UDPポート51871への経路が必要です。IPsecを有効にする前に、適切な形式で安全に管理された`cilium-ipsec-keys` SecretをCiliumの名前空間に用意してください。公式の鍵作成・ローテーション手順に従います。ConfigMapで鍵ファイル名を指定するだけでは、その鍵やボリュームは作成されません。

既定では、これらのモードはノードをまたぐ、サポート対象のCilium管理下Pod通信を保護します。同一ノード内の通信は、これらのノードトンネルでは暗号化されません。任意の外部宛て通信も自動的には保護されません。WireGuardのノード間暗号化（`encryption.nodeEncryption`）は別のBetaオプションで、1.21プレリリースでは非推奨となり、1.22で削除予定です。既定ではコントロールプレーンノードはこの拡張の対象外ですが、Cilium管理下のPodによるノード間通信は引き続き暗号化できます。実際のパケット経路を確認し、必要に応じてアプリケーションTLSを使用してください。ホストファイアウォールとの互換性も暗号化モードに依存します。1.21プレリリースのホストポリシー既知の問題に記載されているとおり、ホストポリシーとIPsecは併用できません。

## Hubbleによるネットワーク可視性

Hubbleはデータパス、プロキシ、エージェントのイベントを受け取り、Kubernetesメタデータを付加します。すべてのeBPFマップを定期的にポーリングするだけの仕組みではありません。

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

サーバーは上限付きのインメモリ履歴を保持します。Relayは複数のサーバーに問い合わせますが、永続データベースではありません。UIではフローの調査やサービス依存関係マップを確認でき、CLIでは明示的なフィルターを指定できます。一致する記録がない場合、通信がなかったほかに、フィルターが誤っている、ピアが利用できない、L7可視性がない、イベントが上書きまたは消失した可能性があります。

### Hubble CLIの使用例

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

`--pod namespace/name`はどちらかの通信端点に一致します。通信方向を指定するには`--from-pod`または`--to-pod`を使います。Pod名はラベルセレクターではありません。ラベルで選択する場合は`--from-label`または`--to-label`を使用してください。CLIが拒否するため、`--namespace`と`--from-pod`/`--to-pod`を同時に指定しないでください。

`DROPPED`は判定結果です。`POLICY_DENIED`はドロップ理由で、`--drop-reason-desc`を使って選択します。HTTPステータスの接頭辞には`4..`や`5..`ではなく、`4+`と`5+`を使います。HTTPフィルターにはプロキシ由来のL7イベントが必要です。TCP接続がドロップされても、HTTPステータスが記録されるとは限りません。

## ネットワークの可視性と監視

### Hubbleメトリクス

有効にしたプラグインごとに観測できる内容が異なります。

| プラグイン | メトリクスの例 | 意味と制約 |
| --- | --- | --- |
| `flow` | `hubble_flows_processed_total` | プロトコル、種別、判定結果ごとに処理したフローイベント数です。あらゆる経路の一意なリクエスト数やパケット数ではありません。 |
| `drop` | `hubble_drop_total{reason="POLICY_DENIED"}` | 観測されたドロップ数です。reasonラベルには列挙値の名前が入ります。 |
| `tcp` | `hubble_tcp_flags_total` | 観測されたTCPフラグです。汎用的なRTT、再送、同時接続数のメトリクスではありません。 |
| `dns` | `hubble_dns_queries_total`, `hubble_dns_responses_total` | 観測されたDNSクエリ、応答、応答コードです。汎用的なDNSレイテンシーヒストグラムではありません。 |
| `httpV2` | `hubble_http_requests_total`, `hubble_http_request_duration_seconds` | HTTPレスポンスフローから得られるリクエスト数、ステータス、秒単位の処理時間です。HTTP可視性が必要です。 |

`http`と`httpV2`を同時に有効にしないでください。カーディナリティを抑えるために送信元・宛先ラベルを慎重に選び、理由もなくリクエストヘッダーや機密性のあるアイデンティティを追加しないでください。イベントがないことを通信がなかった証拠とみなす前に、`hubble_lost_events_total`とピアの可用性を確認してください。

### Prometheusとの連携

チャートはCilium名前空間にヘッドレスの`hubble-metrics` Serviceを作成し、既定でポート**9965**を公開します。検出にはServiceラベル`k8s-app=hubble`が使われ、このServiceは`k8s-app=cilium`ラベルの付いたエージェントPodを選択します。Prometheusでは単一の固定DNSターゲットに依存せず、個々のエンドポイントを検出してください。

Prometheus OperatorとServiceMonitor CRDがすでにある場合は、この設定断片をリリース値にマージします。`release: monitoring`は例です。利用環境のPrometheusの`serviceMonitorSelector`に一致させ、namespace selectorにServiceMonitorの名前空間を含める必要があります。Prometheusに選択されないリソースはスクレイプされません。

```yaml
# hubble-servicemonitor-values.yaml
hubble:
  metrics:
    serviceMonitor:
      enabled: true
      labels:
        release: monitoring
```

チャートのServiceMonitorは名前付きポート`hubble-metrics`とCilium名前空間内のエンドポイントを使用します。Operatorがない場合は、実際のPrometheus設定で同等のKubernetesサービス検出を設定してください。無関係なConfigMapを作ってもPrometheusの設定にはなりません。`*.hubble-metrics.cilium.io`はメトリクスのTLSアイデンティティ設定に使われるもので、ポート9091上のパブリックスクレイプ先ではありません。

GrafanaダッシュボードはPrometheusメトリクスを問い合わせ、Hubble UIのサービスマップはRelayを問い合わせます。有効なプラグインとラベルに合うダッシュボードをインポートしてください。HTTPペイロードを観測できない通信では、HTTPダッシュボードにデータが表示されません。

### フローのエクスポートと保持

ノードごとのローテーションファイルが必要な場合は、任意で`hubble-export-values.yaml`をマージします。フィールドマスクは意図的にネットワークメタデータを保持し、HTTPヘッダー全体はエクスポートしません。

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

静的エクスポーターは各ノードに書き込み、ファイル設定に従ってローテーションします。ノード障害後もイベントを保持する必要がある場合は、別途コレクター、アクセス制御、ストレージの保持期間を用意してください。静的設定を変更するにはエージェントのロールアウトが必要です。動的エクスポーターでは更新方法が異なります。エクスポーターのフィルターやフィールドマスクによって、イベントやフィールドが意図的に除外される場合があります。また、バッファーには容量上限があるため、観測結果が失われる可能性もあります。

## リアルタイムの脅威検知

Hubbleは調査のための証拠を提供しますが、完全なIDS、WAF、自動隔離システムにするスイッチはありません。`enable-threat-detection`、`enable-anomaly-detection`、`alert-to-slack`というCilium設定はサポートされていません。

宛先への拒否が繰り返されればスキャンの可能性を考えられ、通信量の急増は調査のきっかけになります。ただし、これらの観測だけでは攻撃の証明になりません。アプリケーションの認証ログ、ワークロードの変更、API監査イベント、導入済みであればTetragonのランタイムイベントと照合してください。SQLインジェクション、XSS、コマンドインジェクションを検知するには、適切なアプリケーション、WAF、検知ルールが必要です。通常のHTTPフロー記録だけでは、それらを分類できません。

アラートを作成する場合は、通常の通信、データ欠落、イベント消失を考慮した外部Prometheus/SIEMルールを定義し、テストしてください。レート制限、ファイアウォールによる分離、対応の自動化は、それぞれ別途設定する制御です。対応範囲を限定し、復旧手段を用意してください。パケットのドロップが記録されたPodをすべて自動隔離してはいけません。

## ラボ: Hubbleのインストールと利用

このラボでは**新規の独立した名前空間を2つ**使用します。これにより、広範な許可ルールがデフォルト拒否の演習を無効にするのを防ぎます。データベースや外部APIは作成しません。コマンドはテストクラスター用の例です。ドキュメント監査ではスキーマとローカルのフィクスチャを確認しており、実環境へのライブデプロイは検証していません。

### 1. ワークロードを作成して確認する

`visibility-app.yaml`を保存します。クライアントとサーバーのイメージは、Cilium CLIのバージョン付きテスト既定値に合わせています。バックエンドのPod非親和性によって、2台目のスケジュール可能なノードが必要となり、フロントエンドからバックエンドへの通信はノード間になります。

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

ポリシーを適用する前に、両方の名前空間にある両方のクライアントからバックエンドへ到達できることを確認します。到達できなければ、まず準備状態、スケジューリング、DNS、ネットワークの問題を解決してください。任意のcurlエラーをポリシーによる拒否と判断しないでください。

### 2. HTTPポリシーを適用して観測する

`backend-http.yaml`を保存します。この設定は`frontend`アイデンティティからバックエンドのTCP 8080番ポートへの`GET /`を許可します。この例と重複する広範なIngress許可ルールがないことを確認してください。L4許可によって意図したL7制限が迂回される場合があります。

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

ポリシーが反映された後は、フロントエンドからの`GET /`は成功し、`POST /`はプロキシからHTTP 403を返す想定です。第三者の新規接続はL3/L4で拒否されるはずです。リクエスト時刻、エンドポイント、Hubbleイベントを照合してください。DNSエラー、コンテナ不足、無関係なHTTPエラーは、拒否のテストに成功したことを意味しません。Hubble UIで生成された依存関係のエッジとドロップを確認します。

実際のバックエンドでデータベースと外部APIが必要な場合は、以下の**任意の依存先ポリシー**で送信を制御できます。このラボでは適用しません。`database`と`api.example.com`を実際の依存先に置き換えてください。先にDNSエンドポイントを確認します。

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

TCPとUDPのDNS通信を許可し、DNSプロキシルールによってCiliumが`toFQDNs`で使う応答を観測できるようにします。DNSクエリの許可と、解決されたIPアドレスへの後続接続の許可は別の制御です。このポリシーのDNS `*`はすべてのクエリ名を許可し、ドメインのブロックリストではありません。

### 3. デフォルト拒否を別に確認する

`deny-except-dns.yaml`を保存します。明示的な`policyTypes`によってIngressとEgressの両方向で隔離を有効にします。`ingress: []`には**Ingress許可ルールがありません**。Egressの唯一の例外では、選択されたリゾルバーPod宛てのDNSだけを許可します。

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

空のIngressリストを`ingress: [{}]`に置き換えないでください。これはすべてのIngressを許可するルールです。標準のNetworkPolicyでは許可ルールが累積するため、別のポリシーが通信を許可することもあります。Ciliumの拒否ルールやクラスター全体のポリシーによって、さらに制限される場合があります。この名前空間での演習は、ホストネットワーク通信やホストから開始されるすべての通信経路を隔離すると主張するものではありません。

### 4. JSONを調べ、ローカルの概要を出力する

以下を`flow-summary.jq`として保存します。`--output jsonpb`は`.flow`を含むProtocol Buffersのレスポンスエンベロープを返すため、CLIの旧式な`json`互換設定に依存せずに済みます。

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

結果が数えるのは**この有限サンプル内のフローレコード**であり、一意な攻撃、接続、クラスター内のすべてのパケットではありません。フロー以外のレコードは別に数えるため、損失やステータスの情報を確認してください。ローカルでライブフィルターを使う場合は、次のようにします。

```bash
hubble observe --namespace cilium-deny-demo --follow --output jsonpb |
  jq --unbuffered -c 'select(.flow.verdict == "DROPPED"
    and .flow.drop_reason_desc == "POLICY_DENIED")'
```

このパイプラインはローカルに出力します。通知を送るには、連携設定、認証情報、再試行・重複排除のポリシー、ストリーム障害への対応が別途必要です。

### 5. テスト用の名前空間を削除する

名前空間名を確認した後、このラボのワークロードとポリシーだけを削除します。所有権チェックでは、検索に失敗した場合や想定と異なるラベルが見つかった場合に処理を停止します。

```bash
set -eu
for ns in cilium-security-demo cilium-deny-demo; do
  LAB_OWNER=$(kubectl get namespace "$ns" -o jsonpath='{.metadata.labels.audit-lab}')
  test "$LAB_OWNER" = security-visibility
  kubectl delete namespace "$ns"
done
```

## 主な参考資料

- [Ciliumポリシーの適用](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/policy/intro.rst)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [HTTPポリシー](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/policy/layer7.rst)
- [DNSポリシー](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/dns.rst)
- [Hubbleのセットアップ](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/observability/hubble/setup.rst)
- [メトリクス](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/observability/metrics.rst)
- [フローエクスポーター](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/observability/hubble/configuration/export.rst)
- [WireGuard](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/network/encryption-wireguard.rst)
- [IPsec](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/network/encryption-ipsec.rst)
- [相互認証](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
- [ztunnel](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/security/network/encryption-ztunnel.rst)
- [Tetragon](https://raw.githubusercontent.com/cilium/tetragon/main/README.md)
- [Hubble CLIフィルター](https://raw.githubusercontent.com/cilium/hubble/v1.20.2/vendor/github.com/cilium/cilium/hubble/cmd/observe/flows.go)

[メインページに戻る](README.md)

## クイズ

ポリシー、暗号化、可観測性の適用範囲を、[このトピックのクイズ](../../quizzes/networking/cilium/06-security-visibility-quiz.md)で確認してください。
