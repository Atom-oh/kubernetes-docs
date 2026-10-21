# 運用と保守

< [前へ: ノードのライフサイクル管理](./07-node-lifecycle.md) | [目次](./README.md) | [次へ: ベアメタル OS のセットアップ](./09-bare-metal-os-setup.md) >

> **検証基準**: nodeadm 1.0.20、Cilium 1.18.3 CRD、Prometheus Operator 0.94.1、kube-prometheus-stack 92.9.0、Harbor 2.15.4。これらはレビュー済みの参照バージョンであり、すべてに適用できるサポートバージョン一覧ではありません。
> **最終更新日**: 2026年10月18日

このドキュメントでは、監視、バックアップ手順、トラブルシューティングなど、EKS Hybrid Nodes 環境の日常的な運用と保守のタスクについて説明します。

## Harbor の脆弱性スキャンの自動化

管理者パスワードを含み、最新のタグだけを列挙する CronJob を使う代わりに、Harbor に組み込まれた全件スキャンのスケジューラーを使用します。システム管理者 UI で、**Administration → Interrogation Services → Vulnerability → Schedule to scan all** を開きます。Hourly/Daily/Weekly/Custom のスケジュールがサポートされています。Daily は、ドキュメントに記載された UI では午前0時を意味します。02:00 のメンテナンス時間帯に実行する場合は、デプロイ済みバージョンの Custom スケジュールの構文、タイムゾーン、次回の実行時刻を確認してください。

Harbor 2.15.4 では GET/POST/PUT `/api/v2.0/system/scanAll/schedule` が公開されています。UI または、信頼できる CA の検証、保護された認証情報、必要なシステムレベルの権限を使用する承認済みの API 統合を利用してください。プロジェクトの robot 権限があっても、グローバルスキャンを設定する権限があるとは限りません。管理者パスワードを Pod の環境変数やコマンド引数に含めたり、TLS 検証を無効にしたりしないでください。

スキャナーの利用可否、脆弱性データベースの鮮度、実際のスキャン完了状況、失敗を記録してください。リクエストの送信や空の API 応答は、脆弱性評価の成功を意味しません。サポート対象外のアーティファクトには別途対処が必要であり、グローバルスキャンはリソースを消費します。選択したアーティファクトを対象とする自動化では、必要なページとダイジェストをすべて列挙し、リポジトリパスを正しくエンコードし、すべての応答を確認してください。最新のものだけを対象にするループでは、レジストリ全体を網羅できません。

[Harbor ガイド](../container-registry/03-harbor.md)および[公式スケジュール手順](https://github.com/goharbor/website/blob/main/docs/administration/vulnerability-scanning/schedule-scans.md)を参照してください。

## データベースのバックアップ手順

データをコピーする前に、復旧目標を定め、対象を棚卸ししてください。Harbor の復旧には、互換性のあるデータベースメタデータ、レジストリの blob／オブジェクトストレージ、設定、保護されたシークレット／暗号化キーが必要です。PostgreSQL のダンプだけでは完全なバックアップになりません。現在の Harbor には Notary v1 は含まれていません。notarysigner/notaryserver のデータベースがあると想定しないでください。

[公式の Harbor Velero 手順](https://github.com/goharbor/website/blob/main/docs/administration/backup-restore/_index.md)では、リポジトリを読み取り専用モードにし、選択した Kubernetes リソース／PV を使用します。このバックアップは**クラッシュ整合性があるもので、アプリケーション整合性があるものではありません**。Redis は対象外で、同期されていないメタデータ／セッションが失われる可能性があり、修復が必要なタスクが残る場合もあります。対象となるのは内部データベースであり、外部のマネージドデータベースではありません。サポートされているスナップショット／ファイルバックアップ／データ移動プラグインを選択し、復旧先から必要なすべてのボリューム／オブジェクトデータにアクセスできることを確認してください。スナップショットへの参照だけでは、必ずしも持ち運び可能なコピーにはなりません。

以下は、pg_dump/pg_restore とローカル認証の設定が済んでいることを前提とした、検証済みの内部 PostgreSQL Pod 用の**データベースコンポーネントのダンプ例のみ**です。外部データベースでは、独自の認証付きバックアップ／復元プロセスを使用してください。認証情報をコマンド引数に渡していません。エラーが発生したら停止し、途中の出力は非公開にしてください。完了済みのダンプとして公開しないでください。

```bash
set -euo pipefail
umask 077
: "${KUBE_CONTEXT:?Set the approved cluster context}"
: "${HARBOR_NAMESPACE:?Set the Harbor namespace}"
: "${HARBOR_DB_POD:?Set the verified internal PostgreSQL Pod}"
: "${HARBOR_DB_USER:?Set the approved backup database user}"
: "${HARBOR_DB_NAME:?Set the actual Harbor database name}"
: "${PRIVATE_BACKUP_ROOT:?Set an existing protected durable directory}"
BACKUP_DIR=$(mktemp -d "$PRIVATE_BACKUP_ROOT/harbor-db.XXXXXX")
kubectl --context "$KUBE_CONTEXT" -n "$HARBOR_NAMESPACE" exec "$HARBOR_DB_POD" -- \
  pg_dump --format=custom --username "$HARBOR_DB_USER" --dbname "$HARBOR_DB_NAME" \
  > "$BACKUP_DIR/registry.dump.partial"
test -s "$BACKUP_DIR/registry.dump.partial"
kubectl --context "$KUBE_CONTEXT" -n "$HARBOR_NAMESPACE" exec -i "$HARBOR_DB_POD" -- \
  pg_restore --list < "$BACKUP_DIR/registry.dump.partial" > "$BACKUP_DIR/archive-toc.private.txt"
mv "$BACKUP_DIR/registry.dump.partial" "$BACKUP_DIR/registry.dump"
printf 'Database archive created: %s; full Harbor recovery requires separate evidence.\n' "$BACKUP_DIR"
```

アーカイブの一覧を確認しても、復元に成功したことの証明にはなりません。互換性のある PostgreSQL/Harbor バージョンで復元をテストし、アーティファクトの pull、メタデータ、権限、統合を検証してください。完全なバックアップ対象一覧を保護／チェックサム検証し、読み取り専用モード、ジョブ、アップロード／GC の処理を調整してください。操作が失敗した場合、状態を評価せずに読み取り専用モードを自動解除しないでください。

Redis の BGSAVE は非同期です。直後に dump.rdb をコピーすると、古い世代のデータが取得される可能性があります。独立した設計に Redis の永続化を含める場合は、担当の Operator を使用して完了状況、状態、世代を確認してください。Redis を対象外とする公式チュートリアルと、その独自設計を暗黙に混在させないでください。この章ではバックアップも復元も実行していません。

## Prometheus によるメトリクス収集

ホスト、kubelet／コンテナ、GPU のメトリクスは分けてください。`node_cpu_seconds_total` と `node_memory_*` は Node Exporter から取得するもので、kubelet エンドポイントから取得するものではありません。インストール済みでレビュー済みの Node Exporter/DCGM プロファイルを使用し、実際のホストマウント、権限、ノード配置、メトリクスの利用可否を確認してください。Container Insights では、EC2 IMDS を通じて Hybrid のホストレベルメトリクスを取得できません。

以下の検出例では、kube-prometheus-stack 92.9.0 の Node Exporter Service ラベル／ポートを使用し、`monitoring` 内のリリース名を `kube-prom` としています。DCGM 部分は、`gpu-operator` 内で `app: nvidia-dcgm-exporter` のラベルが付いた検証済み Pod と、名前付きの `metrics` コンテナーポートがあることを前提としています。インストール済みの exporter に合わせて調整してください。どちらのリソースも exporter をインストールするものではありません。Prometheus リソースの monitor／namespace セレクターに一致させ、既存の monitor を通じて同じ exporter を二重にスクレイピングしないようにしてください。

`attachMetadata.node` により、Node 検出のメタデータが利用可能になります。メトリクスにラベルが自動的にコピーされるわけではありません。この機能には、ServiceMonitor では Prometheus >=2.37、PodMonitor では >=2.35 が必要であり、Prometheus に Node に対する `list`／`watch` 権限も必要です。以下の relabeling は、実際の `eks.amazonaws.com/compute-type=hybrid` ノードを維持し、安定した `node`／`compute_type` ターゲットラベルを作成します。SSM の Node 名のプレフィックスから Hybrid 配置を推測しないでください。

これらの例では、kubelet HTTPS エンドポイントではなく、保護された exporter の HTTP メトリクスエンドポイントを使用しています。collector からの接続を制限してください。信頼できない境界を越えて通信する場合は、exporter の TLS／認証、またはレビュー済みのプロキシと、それに対応する CA／認可設定を構成してください。`insecureSkipVerify` は使用しないでください。kubelet のスクレイピングは、別途認証と CA 検証を行う設定で維持してください。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: hybrid-node-exporter
  namespace: monitoring
  labels:
    release: kube-prom
spec:
  attachMetadata:
    node: true
  selector:
    matchLabels:
      app.kubernetes.io/name: prometheus-node-exporter
      app.kubernetes.io/instance: kube-prom
  namespaceSelector:
    matchNames: [monitoring]
  endpoints:
  - port: http-metrics
    interval: 30s
    relabelings:
    - sourceLabels: [__meta_kubernetes_node_label_eks_amazonaws_com_compute_type]
      regex: hybrid
      action: keep
    - sourceLabels: [__meta_kubernetes_pod_node_name]
      targetLabel: node
    - targetLabel: compute_type
      replacement: hybrid
---
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: hybrid-gpu-metrics
  namespace: monitoring
  labels:
    release: kube-prom
spec:
  attachMetadata:
    node: true
  selector:
    matchLabels:
      app: nvidia-dcgm-exporter
  namespaceSelector:
    matchNames: [gpu-operator]
  podMetricsEndpoints:
  - port: metrics
    interval: 30s
    relabelings:
    - sourceLabels: [__meta_kubernetes_node_label_eks_amazonaws_com_compute_type]
      regex: hybrid
      action: keep
    - sourceLabels: [__meta_kubernetes_pod_node_name]
      targetLabel: node
    - targetLabel: compute_type
      replacement: hybrid
```

### Grafana ダッシュボードのクエリ例

これらのクエリには、上記のターゲットラベルと互換性のある exporter メトリクスが必要です。単位、GPU/MIG の識別情報、未サポート値／エラーを示すセンチネル、スクレイピングの欠落、重複系列を確認してください。GPU framebuffer の使用率は、空き容量ではなく総容量（`used + free`）で割ります。容量がゼロの系列は除外されます。以下のクエリはローカルでテストできる式であり、この環境での測定値ではありません。

```promql
# Host CPU utilization percent
100 * (1 - avg by (node) (rate(node_cpu_seconds_total{mode="idle",compute_type="hybrid"}[5m])))

# Host memory utilization percent
100 * (1 - node_memory_MemAvailable_bytes{compute_type="hybrid"} / node_memory_MemTotal_bytes{compute_type="hybrid"})

# GPU utilization: this metric is already a percentage
DCGM_FI_DEV_GPU_UTIL{compute_type="hybrid"}

# GPU framebuffer usage: used / (used + free), excluding zero capacity
(100 * DCGM_FI_DEV_FB_USED{compute_type="hybrid"} /
 (DCGM_FI_DEV_FB_USED{compute_type="hybrid"} + DCGM_FI_DEV_FB_FREE{compute_type="hybrid"}))
and
((DCGM_FI_DEV_FB_USED{compute_type="hybrid"} + DCGM_FI_DEV_FB_FREE{compute_type="hybrid"}) > 0)
```

## Direct Connect のパフォーマンス検証

テスト計画と AWS サービスの保証を分けて考えてください。以前に示した RTT <5ms、変動 <2ms、損失 <0.01%、スループット >1Gbps という値は、計画用の例示的な目標であり、測定結果でも、Direct Connect が一律に保証する値でもありません。実際の場所、回線、エンドポイント、ワークロード、契約容量に応じた目標を選び、測定経路が VPN などではなく Direct Connect を使用していることを確認してください。

`ping` は ICMP RTT を報告し、Linux iputils では RTT mdev も報告します。このばらつきは、一方向の遅延変動や iperf3 の UDP jitter と同じ統計量ではありません。ICMP のフィルタリング／優先度引き下げは、アプリケーションのトラフィックとは異なる場合があります。1,000 パケットのテストで損失率が変化する幅は 0.1% です。損失がゼロでも、長期的な損失率が 0.01% 未満であることの証明にはなりません。

iperf3 がすでに稼働している承認済みのプライベートテストサーバー、調整済みの実行時間帯、明示的なトラフィック上限、保護された結果の保存先を使用してください。EKS API エンドポイントに対して iperf3 を実行しないでください。以下の上限付きサンプルでは、Bash、Python3、iputils ping、GNU timeout、記載のオプションに対応した iperf3 が必要です。失敗した場合は処理を中止します。ツールの不足、無効な JSON、iperf3 のエラーは、パフォーマンステストの合格を意味しません。

```bash
set -euo pipefail
umask 077
: "${PROBE_HOST:?Set the approved private test host}"
: "${TEST_BITRATE:?Set an approved traffic cap, for example 10M}"
: "${PRIVATE_RESULTS_ROOT:?Set an existing protected results directory}"
if [[ ! "$TEST_BITRATE" =~ ^[1-9][0-9]*[KMGT]?$ ]]; then
  printf 'TEST_BITRATE must be a positive integer with an optional K/M/G/T suffix.\n' >&2
  exit 2
fi
RUN_DIR=$(mktemp -d "$PRIVATE_RESULTS_ROOT/dx-check.XXXXXX")
date -u +%FT%TZ > "$RUN_DIR/started-at.txt"
LC_ALL=C ping -n -c 100 -W 2 "$PROBE_HOST" > "$RUN_DIR/ping.txt"
timeout 45s iperf3 --client "$PROBE_HOST" --connect-timeout 3000 \
  --time 10 --bitrate "$TEST_BITRATE" --json > "$RUN_DIR/iperf-tcp.json"
python3 - "$RUN_DIR/iperf-tcp.json" <<'PY'
import json, math, sys
with open(sys.argv[1]) as stream:
    result = json.load(stream)
if result.get("error") or not isinstance(result.get("end"), dict):
    raise SystemExit("iperf3 result is incomplete or reports an error")
received = result["end"].get("sum_received", {})
for field in ("bits_per_second", "bytes", "seconds"):
    value = received.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise SystemExit("Missing or invalid TCP receiver statistics")
if received["seconds"] <= 0:
    raise SystemExit("Invalid TCP test duration")
print("Saved a completed iperf3 result; compare receiver statistics with the approved test plan.")
PY
printf 'Private observations: %s; this does not establish an AWS latency/throughput guarantee.\n' "$RUN_DIR"
```

この上限付き TCP テストでは、リンクの最大容量は確認できません。受信側のスループット、再送、方向、実行時間、輻輳を確認してください。別途承認された UDP テストでは、`--udp` と明示的なビットレートを使用し、そのバージョンの JSON から受信側の損失／ジッターを保存して解釈してください。失敗または未実施のプローブは、そのように記録してください。この監査中にネットワーク負荷テストは実行していません。

## 証明書更新の管理

どの証明書を確認しているのかを特定してください。Harbor の TLS サーバー証明書、その CA チェーン、kubelet のサービング証明書、EKS コントロールプレーン CA、IAM Roles Anywhere のホスト証明書のいずれかです。有効な CA 証明書があっても、サーバーのリーフ証明書が有効であるとは限りません。また、Node の Ready ハートビートは、証明書の有効期限を示す証拠ではありません。EKS コントロールプレーンの証明書は AWS が管理します。EKS の修復手順として kubeadm の更新コマンドを実行しないでください。

このローカルの有効期限チェックは、証明書が存在しない、読み取り不能または無効な場合、あるいは例として示した30日間の警告期間内に期限切れとなる場合に失敗します。このチェックでは、チェーン、ホスト名、失効、サービスが実際にその証明書を提示しているかどうかは検証しません。提供されるエンドポイントには、以下の検証済み TLS 接続を使用してください。ホスト証明書の更新には[認証情報のライフサイクル手順](./07-node-lifecycle.md)を使用してください。

```bash
set -euo pipefail
: "${CERT_PATH:?Set the actual certificate file to inspect}"
test -r "$CERT_PATH"
openssl x509 -in "$CERT_PATH" -checkend 2592000 -noout
```

実際の発行者／所有者、設定された証明書パス、有効期限、アラート配信状況を追跡してください。kubelet のサービング／クライアント認証情報のパスは設定によって異なります。serverTLSBootstrap を有効にしただけでは、サービング CSR の承認や IAM Roles Anywhere 証明書のローテーションは行われません。

## Ingress の設定

### ALB Ingress（ip ターゲットモード）

セルフマネージドの AWS Load Balancer Controller では、`alb.ingress.kubernetes.io/target-type: ip` を使用して、ルーティング可能な Hybrid Pod IP を登録できます。ルート、戻りトラフィック、セキュリティグループ／ファイアウォール、EKS のリモート Pod ネットワーク設定が一致している必要があります。

AWS の混在モード向け webhook の手順では、Controller をクラウドノード上に配置します。これはその設計における配置の推奨事項であり、Hybrid Nodes 上では webhook を実行できないという一律の意味ではありません。アドオンのガイダンスでは、コントロールプレーンが設定されたリモート Pod CIDR に到達できる場合、Hybrid への配置も認められています。`compute-type NotIn [hybrid]` はそのようなラベルのないノードにも一致するため、明示的に割り当てる管理用の配置ラベルを優先してください。以下のラベル例は、適格性を確認したクラウドノードにのみ割り当ててください。

```yaml
# Fragment under the controller Deployment's spec.template.spec:
nodeSelector:
  infrastructure.example.com/location: aws
```

### Cilium Ingress Controller

このセクションの Cilium Ingress および Gateway API の例には、L7 を有効にした Cilium 設定が必要です。[EKS Hybrid Nodes Gateway](./10-hybrid-nodes-gateway.md) 用に設定された同じ Cilium インストールには適用できません。その[設定で AWS が必須としている VTEP 設定](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-gateway-cni.html)では、`vtep.enabled=true` および `l7Proxy=false` が設定されます。これらの機能を有効にする前に、ネットワーク設計を選択してください。この制約は Cilium の L7 プロキシ機能に関するものであり、HTTP アプリケーションが Gateway のルーティングされたネットワーク経路を使用することを禁止するものではありません。

Cilium 1.18.3 の上流 Ingress の前提条件には、NodePort のサポート（または kube-proxy の置き換え）、L7 プロキシのサポート、利用可能なロードバランサー公開経路が含まれます。以下の断片は、混在クラスター内のクラウドノードで CNI を変更する許可ではありません。レビュー済みの Hybrid Cilium 設定を維持し、追加機能について AWS のサポート範囲を確認してください。専用モードと共有モードを変更すると、アドレスが変わり、既存の接続が中断する場合があります。

```yaml
# Merge into the reviewed Cilium release values, not a full installation:
nodePort:
  enabled: true
l7Proxy: true
ingressController:
  enabled: true
  loadbalancerMode: dedicated
```

### Cilium Gateway API

選択した Controller リリースでサポートされている Gateway API の CRD とリソースバージョンをインストールし、NodePort／kube-proxy の置き換えと L7 の前提条件を確認し、GatewayClass/Gateway/Route の状態をチェックしてください。Helm フラグを1つ設定しただけでは、これらの CRD はインストールされず、外部から到達可能にもなりません。

```yaml
# Required Gateway API CRDs and controller prerequisites must already be met:
gatewayAPI:
  enabled: true
```

### LoadBalancer IPAM（Cilium）

以下のプールでは、1.18.3 の CRD に照らして検証済みの `cilium.io/v2` API を使用し、明示的にラベルが付けられた Service のみを選択します。例示用 CIDR は、ネットワークの棚卸しから予約済みで、重複しないアドレス範囲に置き換えてください。IP の割り当てによってルーターにアドレスが広報されるわけでも、データパスの動作が保証されるわけでもありません。

```yaml
apiVersion: cilium.io/v2
kind: CiliumLoadBalancerIPPool
metadata:
  name: on-prem-pool
spec:
  blocks:
  - cidr: "10.80.100.0/24"
  serviceSelector:
    matchLabels:
      exposure: onprem-bgp
```

## 負荷分散

### NLB（ip ターゲットモード）

セルフマネージドの AWS Load Balancer Controller では、`spec.loadBalancerClass: service.k8s.aws/nlb` と `service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip` を指定した、管理対象の `LoadBalancer` Service を使用します。または、選択した Controller に対して文書化された `aws-load-balancer-type: external` の所有権設定を使用してください。ターゲットタイプのアノテーションだけでは、Controller は選択されません。Hybrid Pod のターゲットと戻りルートが AWS から到達可能である必要があります。内部／パブリックの公開方法、サブネット、アクセス制御は慎重に選択してください。

これは EKS Auto Mode の所有権設定手順ではありません。置き換えとトラフィックへの影響を確認せずに、既存の Service のクラス／Controller をインプレースで移行しないでください。

### Cilium LB + BGP

インストール済みの `cilium.io/v2` Schema を使用してください。Service のアドレス種別は `advertisements[].service.addresses` の下に指定します。この例では、`exposure: onprem-bgp` のラベルが付いた Service の LoadBalancer IP のみを広報します。実質的にすべての Service が選択されてしまう `NotIn` セレクターは使用しません。

```yaml
apiVersion: cilium.io/v2
kind: CiliumBGPAdvertisement
metadata:
  name: hybrid-service-advertisement
  labels:
    advertise: hybrid-services
spec:
  advertisements:
  - advertisementType: Service
    service:
      addresses: [LoadBalancerIP]
    selector:
      matchLabels:
        exposure: onprem-bgp
```

CiliumBGPClusterConfig のノード／ピア選択と CiliumBGPPeerConfig のアドレスファミリーを設定してください。ピア設定の広報セレクターは `advertise: hybrid-services` に一致し、Service セレクターは実際の Service ラベルに一致する必要があります。レビュー済みの BGP コントロールプレーンを有効にし、ルーターのセッションを確立したうえで、受け入れられたルート、ネクストホップ、戻り経路、トラフィックポリシーを検証してください。IPPool／Advertisement だけでは設定が不完全です。変更を適用する前に、[ネットワーク設定の基礎](./02-network-configuration.md)と、インストール済みバージョンの BGP ドキュメントを参照してください。

## アドオンの詳細設定

### CloudWatch Observability Agent

サポートされている Pod Identity 設定を使用し、ワークロードの実際の IAM 関連付けと権限を確認してください。現在の AWS 手順では、Hybrid との互換性のために `RUN_WITH_IRSA` 変数が、名前に反して引き続き必要です。既存の `AmazonCloudWatchAgent` リソースの **spec.env リスト**に追加し、`K8S_NODE_NAME` などのエントリーは維持してください。EKS アドオンの configurationValues に任意のトップレベル `env` を追加するものではありません。

```yaml
# Add this item to the existing AmazonCloudWatchAgent.spec.env list:
- name: RUN_WITH_IRSA
  value: "True"
```

編集する前に、`amazon-cloudwatch` 名前空間の `amazoncloudwatchagents/cloudwatch-agent` を調べ、この設定をアドオン／Operator がどのように調整するかを確認してください。その後、Agent のロールアウトと収集状況を確認します。Hybrid のクラスター／ワークロード／Pod／コンテナーメトリクスは利用できますが、EC2 IMDS への依存先がないため、ノードレベルの Container Insights メトリクスは利用できません。Operator が Hybrid Nodes 上で動作する場合は、コントロールプレーンから webhook に到達できるようにしてください。

### EKS Pod Identity Agent

| ホスト OS | 文書に記載された最小バージョン | Hybrid DaemonSet／認証情報のパス |
| --- | --- | --- |
| Ubuntu、RHEL、AL2023 | アドオン 1.3.3-eksbuild.1 | `hybrid`; `/eks-hybrid/.aws/credentials` |
| Bottlerocket（サポート対象の VMware バリアント） | アドオン 1.3.7-eksbuild.2 および OS 1.39.0 | `hybrid-bottlerocket`; `/var/eks-hybrid/.aws/credentials` |

これらは機能の最低要件であり、古いリリースのインストールを推奨するものではありません。現在互換性のあるアドオンバージョンを選択し、その設定 Schema を確認してください。Ubuntu/RHEL/AL2023 では、各ホストの既存の完全な NodeConfig に以下の断片をマージします。

```yaml
# Merge this fragment into each host's complete, protected NodeConfig:
spec:
  hybrid:
    enableCredentialsFile: true
```

AWS では、すでに参加済みのノードも含め、影響を受ける各ホストで `nodeadm init -c file:///path/to/nodeconfig.yaml` による調整を計画的に実施する必要があります。すべての本番ノードを無計画に再初期化しないでください。ID／設定を維持し、ライフサイクル手順に従って、一度に1台ずつ検証してください。Bottlerocket では、この nodeadm 断片ではなく、文書化された設定方法を使用します。これらの一時的な認証情報ファイルは機密情報です。出力しないでください。

Bottlerocket 以外の Hybrid DaemonSet では、アドオンの設定に以下が含まれます。

```json
{
  "daemonsets": {
    "hybrid": {
      "create": true
    }
  }
}
```

Bottlerocket では、選択したバージョン向けに文書化された `hybrid-bottlerocket` 設定を使用します。既存の設定を調べてマージしてください。アドオンが存在しない場合にのみ作成します。既存のアドオンは、create や OVERWRITE を無条件に使用するのではなく、レビュー済みの競合処理で更新してください。Agent と認証情報ファイルだけでは、すべてのアプリケーションの Pod Identity 関連付けは作成されません。namespace、ServiceAccount、IAM ロールの信頼関係／権限、SDK の認証情報解決、認可の成功を確認してください。

## 混在モードでの Webhook 運用

AWS がサポートする混在モードのパターンでは、VPC CNI はクラウドノード上で、Cilium/Calico は Hybrid Nodes 上で動作します。このパターンでは、AWS は webhook をクラウドノードに配置することを推奨しています。Hybrid 上で動作する webhook には、ルーティング可能なリモート Pod CIDR とコントロールプレーンからの到達性も必要です。すべての webhook がどこでも実行できる、または実行しなければならないと想定せず、実際のエンドポイントを確認してください。

### CoreDNS の配置

この混在モード設計では、CoreDNS のレプリカを少なくとも1つクラウドノードに、もう1つを Hybrid Nodes に配置することを AWS は推奨しています。希望するレプリカ数が2以上であること、適格な容量、セレクター、toleration、実際のエンドポイントを確認してください。`maxSkew: 1` だけでは、2つのドメインは作成されず、ドメインごとに1つの Pod が配置される保証もありません。また、クラウドノードには `eks.amazonaws.com/compute-type` ラベルがない場合があります。

`minDomains` をサポートするクラスターでは、この Pod spec の断片で管理者が明示する2ドメインのラベルを使用します。対象の DNS ノードのみにラベルを付け、適格なノードごとに `location` の値が正確に `aws` または `onprem` であることを確認してください。既存の affinity／toleration に互換性を持たせ、CoreDNS Pod のラベルを確認し、アドオンがサポートする設定方法で変更を反映してください。

```yaml
# Fragment under CoreDNS Deployment.spec.template.spec.
# Label eligible nodes with exactly aws or onprem in this administrative domain.
nodeSelector:
  infrastructure.example.com/dns-eligible: "true"
topologySpreadConstraints:
- maxSkew: 1
  minDomains: 2
  topologyKey: infrastructure.example.com/location
  whenUnsatisfiable: DoNotSchedule
  labelSelector:
    matchLabels:
      k8s-app: kube-dns
```

適格なドメインが2つあり、レプリカが2つ以上の場合、厳密な分散によって各ドメインへのスケジューリングが制約されます。あるドメインに容量がない場合、新しいレプリカが Pending のままになることがあります。これは可用性とのトレードオフであり、フェイルオーバーの保証ではありません。実際の DNS Service／EndpointSlices と、ローカル／リモートの名前解決をテストしてください。Auto Mode を含むクラスターでは、ノードローカル DNS のシステムサービスと、非 Auto ノードで引き続き必要な Deployment を区別してください。

<span id="per-add-on-nodeaffinity-settings-guide"></span>

### アドオンごとの配置ガイド

| アドオン | この設計での配置 | 必要な確認 |
| --- | --- | --- |
| AWS Load Balancer Controller | AWS の混在モード手順に従いクラウドノードに配置 | Webhook の到達性、明示的なラベル、ルーティング可能な Hybrid IP ターゲット |
| CloudWatch Agent／Operator | Agent はサポート対象のターゲットノードに配置。Operator の webhook はクラウドへの配置を推奨 | IAM／Agent の健全性。Hybrid のノードレベルメトリクスは対象外 |
| cert-manager | Webhook はクラウドへの配置を推奨。ルーティング可能であれば Hybrid への配置も可能 | コントロールプレーンのアクセスとリモート Pod ネットワーク |
| Metrics Server | クラウドに配置するか、到達可能な Hybrid Pod エンドポイントを使用 | コントロールプレーンから Pod への経路、および Metrics Server から kubelet への経路 |
| CoreDNS | クラウドノードと Hybrid ノードへのレプリカ配置を確認 | 適格なドメイン、容量、実際の DNS トラフィック |
| Cilium/Calico | AWS がサポートする混在 CNI 設計では Hybrid ノードに配置 | クラウドノード上の VPC CNI を維持 |

## ネットワーク切断時の動作と備え

このセクションでは、Direct Connect または VPN が一時的に切断された場合や、ネットワークが応答しなくなった場合に、何が動作し続け、何が停止するのかを説明します。Hybrid Nodes は、頻繁な切断が発生する DDIL 環境を想定しておらず、AWS への安定した接続を前提としています（[概要](./README.md)を参照）。

### 切断中のクラスターとワークロード

| 項目 | 動作 |
|---|---|
| 実行中の Pod | ノード上で実行を続けます。kubelet は Lease を更新できないため、Node の Ready 条件は `Unknown` になり、`node.kubernetes.io/unreachable` taint が追加されます（`NoSchedule`。条件を満たす場合は `NoExecute` も追加）。 |
| Pod のフェイルオーバー | 通常の Pod には、`not-ready` および `unreachable` の NoExecute taint に対するデフォルトの300秒の toleration が適用されます。該当する NoExecute taint が適用され、その toleration の期限が切れると、コントロールプレーンは Pod に削除マークを付けます。その後、Controller が適格なノードに置き換えの Pod を作成できます。一致する toleration のない Pod は、この300秒の待機を経ずに退避されます。到達不能なノード上の元のコンテナは、kubelet が再接続するまで実行を続ける場合があります。DaemonSet の Pod はデフォルトで、これらの taint を無期限に許容します。 |
| Zone ラベル | Zone ラベルだけでは退避を防げません。Zone 全体が到達不能でも、別の Zone に Ready ノードが残っていれば、退避が進む場合があります。どの Zone にも Ready ノードがない場合、Kubernetes は退避を取り消します。他の Zone の健全性しきい値やクラスターサイズも動作に影響します。[AWS Pod フェイルオーバーガイド](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-kubernetes-pod-failover.html)のシナリオを参照してください。Hybrid ノードには cloud-controller-manager がないため、nodeadm の `--node-labels` でデータセンターごとの Zone を設定してください。 |
| Cilium | Agent の健全性はコントロールプレーンへのアクセスと連動しているため、切断中も Agent は再起動を繰り返し、Cilium BGP Control Plane のセッションが停止する場合があります（CFP #31702、Cilium 1.17 のオプトイン改善）。AWS の例で使用された MetalLB L2 モードは、切断中も安定していました。 |
| AWS サービスへの依存 | ECR イメージの pull、CloudWatch、Amazon Managed Service for Prometheus、ALB/NLB、S3、RDS などのリージョンサービスは、切断中は利用できません。 |
| ローカルでのトラブルシューティング | API サーバーに到達できないため、`kubectl` の代わりにホスト上で `crictl pods`、`crictl ps`、`crictl logs <container>` を使用してください。 |

### 認証情報と再接続

| 項目 | SSM ハイブリッドアクティベーション | IAM Roles Anywhere |
|---|---|---|
| 一時認証情報 | 有効期間は1時間固定で、変更できません。通常の運用ではノードやアプリケーションに影響を与えず、有効期限前に自動ローテーションされます。 | デフォルトは1時間で、プロファイルの `durationSeconds` により最長12時間です。ノード IAM ロールの `MaxSessionDuration` は、それより長く設定する必要があります。 |
| 切断中 | SSM のリージョナルエンドポイントに到達できないため更新に失敗し、長時間の切断中に認証情報が期限切れになる場合があります。 | AWS に接続できないため、新しい認証情報を取得できません。 |
| 復旧後 | 再試行では指数バックオフが使用され、SSM Agent **3.3.808.0 以降**では最大30分に制限されます。**ネットワーク復旧後、ノードの再接続には最大30分かかる場合があり**、再接続のタイミングもノードごとに異なるため、先に再接続したノードへ Pod がフェイルオーバーすることがあります。 | kubelet は `aws_signing_helper credential-process` を通じて必要に応じて認証情報を取得するため、通常は**数秒以内**に再接続します。 |
| より速い復旧 | SSM Agent を再起動して更新を強制します（以下のコマンド）。 | 証明書が有効な間は対応不要です。証明書の有効期限通知を設定してください。 |

SSM Agent のバージョン、再起動、ログ:

```bash
# Version (AL2023, RHEL / Ubuntu)
yum info amazon-ssm-agent
snap list amazon-ssm-agent

# Force a credential refresh after the network is restored
systemctl restart amazon-ssm-agent                          # AL2023, RHEL
systemctl restart snap.amazon-ssm-agent.amazon-ssm-agent    # Ubuntu

# Watch the CredentialRefresher lines
tail -f /var/log/amazon/ssm/amazon-ssm-agent.log
```

切断中は、ログに `Retrieve credentials produced error: RequestError: send request failed` と `Sleeping for ... before retrying retrieve credentials` が繰り返し記録されます。更新が成功すると `Credentials ready` が記録されます。

### 事前準備チェックリスト

- **冗長な接続性:** Direct Connect を冗長化するか、バックアップとして Site-to-Site VPN を維持します。
- **切断の検出:** EKS コントロールプレーンの Controller Manager ログを有効にし、`Recording status change event message for node` メッセージと `status="NodeNotReady"` を対象に CloudWatch メトリクスフィルターとアラームを作成します。TGW の `BytesIn`／`BytesOut`、または VGW の `TunnelDataIn`／`TunnelDataOut` が通常の水準を下回った場合にアラームを設定してください。CloudWatch Network Monitor では、損失とレイテンシを確認できます。
- **SSM Agent のバージョン:** 再試行間隔を最大30分に制限できるよう、3.3.808.0 以降を維持します。
- **Zone ラベル:** データセンターごとに `topology.kubernetes.io/zone` を設定します。
- **退避の調整:** 移動が難しいアプリケーションでは、`tolerationSeconds` を増やします。値を大きくすると、実際に障害が発生したノードから Pod を移動するまでの時間も長くなります。

```yaml
# Fragment under the Deployment's spec.template.spec
tolerations:
  - key: "node.kubernetes.io/unreachable"
    operator: "Exists"
    effect: "NoExecute"
    tolerationSeconds: 1800
```

- **認証情報プロバイダー:** 切断が頻繁で、迅速な再接続が重要な場合は、`durationSeconds` を長く設定した IAM Roles Anywhere を検討してください。クラスター内では単一のプロバイダーを使用します。
- **セカンダリ監視経路:** リージョンサービスに到達できない場合も状況を把握できるよう、複数のバックエンドに送信するよう ADOT collector を設定します。

参考資料:
- [ネットワーク切断時のホスト認証情報](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-host-creds.html)
- [ネットワーク切断時の安定性に関するベストプラクティス](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-network-disconnection-best-practices.html)
- [ネットワーク切断時の Kubernetes Pod フェイルオーバー](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-kubernetes-pod-failover.html)

## よくあるトラブルシューティング

### ImagePullBackOff の診断

Pod のイベントを確認し、レジストリ認証情報をデコードしたり表示したりせずに、参照されている Secret の名前／種類を調べます。Secret は Pod と同じ namespace にある必要があります。レジストリのホスト名、必要なリポジトリ権限、認証情報の有効期限を、認証情報の管理者を通じて確認してください。メタデータだけでは認証の成功を証明できません。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the approved cluster context}"
: "${NAMESPACE:?Set the workload namespace}" "${POD:?Set the affected Pod}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" describe pod "$POD"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD" \
  -o jsonpath='{.spec.imagePullSecrets[*].name}{"\n"}'
: "${PULL_SECRET:?Set a referenced imagePullSecret in that namespace}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get secret "$PULL_SECRET" \
  -o jsonpath='{.type}{"\n"}'
```

信頼された CA とホスト名検証を有効にした状態で、実際のホスト／ネットワーク経路から TLS を確認してください。curl -k を使用したり、認証されていないレジストリの 401 応答を TLS の失敗と解釈したりしないでください。この例では Bash、OpenSSL、GNU timeout が必要です。

```bash
set -euo pipefail
: "${HARBOR_HOST:?Set the registry DNS name, without scheme or port}"
: "${HARBOR_CA_FILE:?Set the approved CA bundle file}"
timeout 10s openssl s_client -connect "$HARBOR_HOST:443" \
  -servername "$HARBOR_HOST" -verify_hostname "$HARBOR_HOST" \
  -verify_return_error -CAfile "$HARBOR_CA_FILE" </dev/null
```

Pod 内で DNS／ネットワークをテストするには、ダイジェストで固定した承認済みの診断イメージ、専用 namespace、影響を受けた Hybrid Node への明示的な配置を使用してください。任意のイメージを固定せずに起動したデバッグ Pod はクラウドノード上で実行され、誤った経路をテストする場合があります。Pod の作成／削除は別途レビューし、対象を限定した結果を保存してください。

### DNS 名前解決の問題

実際の CoreDNS Deployment／Pod、Service、EndpointSlices、それらのクラウド／オンプレミスでの配置、DNS 設定、ネットワーク到達性を調べてください。影響を受けているワークロード環境から、レジストリ名と `kubernetes.default.svc.cluster.local` をテストしてください。API、DNS、ログへのアクセスに失敗した場合は、成功ではなく観測できていないことを意味します。

診断の既定手順として CoreDNS の全 Pod を再起動しないでください。まず障害が発生している層を特定し、冗長性と復旧確認を考慮して再起動を調整してください。Auto Mode を含む混在クラスターでは、ノードローカル DNS の動作がある場合があります。問題の Pod が実際に使用しているリゾルバー経路を特定してください。

### ノード接続の問題

棚卸しに記録された実際の Node 名と対応するホストを使用してください。SSM を使用する Node 名は hybrid- で始まるとは限らず、ホスト名として解決できるとも限りません。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the approved cluster context}" "${NODE:?Set the actual registered Node name}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE" -o wide
kubectl --context "$KUBE_CONTEXT" describe node "$NODE"
```

```bash
# Run on the mapped host, not a hostname guessed from the Node name.
sudo systemctl status kubelet containerd --no-pager
sudo journalctl -u kubelet -u containerd --since '10 minutes ago' \
  --no-pager -n 200
```

認証情報プロバイダーと、OS 固有の Agent ユニットを確認してください（該当する場合は Ubuntu の snap ベースの SSM インストールも含みます）。ネットワーク／認証の診断には、root 権限と非公開での出力保管を前提に、検証済みの `nodeadm debug -c file:///etc/eks/nodeconfig.yaml` 手順を使用してください。これは AWS とクラスターに接続します。発行された認証情報をログに出力したり、TLS 検証を無効にしたりしないでください。

レビュー済みの 1.0.20 CLI には `nodeadm reset` サブコマンドはありません。NotReady だからといって、ホストの登録解除や再初期化を無条件に行わないでください。原因を特定した後、マウント／データを保持し、ノード／SSM の ID を記録したうえで、[復旧と ID の調整](./07-node-lifecycle.md)に従ってください。

## 検証範囲と参考資料

ローカルでの確認では、固定したリソース Schema、合成サンプルを使った4つの PromQL 式、バックアップ／ネットワーク関連のコマンドを模擬した11ケースを対象としました。AWS／Kubernetes の変更、実際のバックアップ／復元、ネットワーク負荷テスト、BGP セッション、exporter のスクレイピング、本番環境へのロールアウトは実行していません。デプロイ前に、最新の AWS サポートドキュメントから EKS／OS／CNI／アドオンの組み合わせを選択してください。

- [AWS Hybrid アドオン](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)
- [AWS Hybrid webhook](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-webhooks.html)
- [AWS Hybrid のアップグレード](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-upgrade.html)
- [Prometheus Operator API](https://prometheus-operator.dev/docs/api-reference/api/)
- [Cilium 1.18.3 Ingress の前提条件](https://github.com/cilium/cilium/blob/v1.18.3/Documentation/network/servicemesh/ingress.rst)
- [Cilium 1.18.3 LoadBalancer IPPool CRD](https://github.com/cilium/cilium/blob/v1.18.3/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumloadbalancerippools.yaml)
- [iperf3 の実行方法](https://software.es.net/iperf/invoking.html)
- [Kubernetes の taint と toleration](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)


---

< [前へ: ノードのライフサイクル管理](./07-node-lifecycle.md) | [目次](./README.md) | [次へ: ベアメタル OS のセットアップ](./09-bare-metal-os-setup.md) >
