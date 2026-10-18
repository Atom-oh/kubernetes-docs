# 運用とメンテナンス

< [前へ: ノードのライフサイクル管理](./07-node-lifecycle.md) | [目次](./README.md) | [次へ: ベアメタルOSのセットアップ](./09-bare-metal-os-setup.md) >

> **検証基準**: nodeadm 1.0.20; Cilium 1.18.3 CRDs; Prometheus Operator 0.94.1; kube-prometheus-stack 92.9.0; Harbor 2.15.4。ここに示すのは確認済みの参照バージョンであり、あらゆる環境に適用できるサポート対象バージョン一覧ではありません。
> **最終更新**: 2026年10月18日

このページでは、EKS Hybrid Nodes環境の日常的な運用と保守として、監視、バックアップ、トラブルシューティングを説明します。

## Harborの脆弱性スキャンを自動化する

管理者パスワードを保持し、最新タグだけを列挙するCronJobではなく、Harbor組み込みの全件スキャンスケジューラーを使ってください。システム管理者用UIで **Administration → Interrogation Services → Vulnerability → Schedule to scan all** を開きます。Hourly、Daily、Weekly、Customのスケジュールを利用できます。文書化されたUIでDailyを選ぶと、午前0時に実行されます。午前2時の保守時間帯に合わせる場合は、導入済みバージョンにおけるCustomの書式、タイムゾーン、次回実行時刻を確認してください。

Harbor 2.15.4ではGET/POST/PUT `/api/v2.0/system/scanAll/schedule` が提供されています。UI、または信頼できるCAを検証し、認証情報を保護し、必要なシステムレベルの権限を使う承認済みAPI連携を利用してください。Project robotの権限があっても、グローバルスキャンを設定する権限があるとは限りません。Podの環境変数やコマンド引数に管理者パスワードを含めたり、TLS検証を無効化したりしないでください。

Scannerが利用可能か、脆弱性データベースが最新か、スキャンが実際に完了したか、失敗していないかを記録してください。要求を送信できたことやAPIが空の応答を返したことは、脆弱性評価の成功を意味しません。未対応のartifactは別途扱う必要があり、全件スキャンはリソースを消費します。対象artifactだけを自動化する場合は、必要なすべてのページとdigestを列挙し、repository pathを正しくencodeし、すべての応答を確認してください。最新タグだけを処理するループではregistry全体を網羅できません。

[Harborガイド](../container-registry/03-harbor.md)と[公式スケジュール手順](https://github.com/goharbor/website/blob/main/docs/administration/vulnerability-scanning/schedule-scans.md)を参照してください。

## データベースのバックアップ手順

データをコピーする前に、復旧目標と対象inventoryを定義してください。Harborを復旧するには、互換性のあるdatabase metadata、registry blob/object storage、設定、保護されたsecretや暗号化キーが必要です。PostgreSQL dumpだけでは完全なバックアップになりません。現行HarborにはNotary v1は含まれないため、notarysigner/notaryserver databaseが存在すると想定しないでください。

[Harbor公式Velero手順](https://github.com/goharbor/website/blob/main/docs/administration/backup-restore/_index.md)では、repositoryをread-only modeにし、選択したKubernetes resource/PVをバックアップします。このバックアップは**crash-consistentであり、application-consistentではありません**。Redisは対象外で、同期前のmetadata/sessionが失われたり、修復が必要なtaskが残ったりする可能性があります。対象は内部databaseであり、外部managed databaseは含みません。サポートされるsnapshot/file backup/data movement pluginを選び、復旧先から必要なすべてのvolume/object dataへアクセスできることを確認してください。snapshotの参照情報だけでは、別環境へ移行可能なコピーとは限りません。

次は、pg_dump/pg_restoreとローカル認証の設定を確認済みの内部PostgreSQL Podを対象とする、**database componentだけのdump例**です。外部databaseは、それぞれの認証済みバックアップ/復元手順を使ってください。認証情報をコマンド引数に渡していません。エラー時は停止し、途中までの出力を非公開に保ってください。不完全な出力を完成したdumpとして公開してはいけません。

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

archiveの一覧を表示できても、復元に成功した証拠にはなりません。互換性のあるPostgreSQL/Harborバージョンで復元を試し、artifactのpull、metadata、権限、integrationsを検証してください。バックアップ対象全体を保護してchecksumを確認し、read-only mode、job、upload/GCの稼働と調整してください。失敗した処理の状態を調べずにread-only modeを自動解除しないでください。

RedisのBGSAVEは非同期です。直後にdump.rdbをコピーすると、古い世代のデータを取得することがあります。別途設計した構成でRedisの永続化を含める場合は、担当者とともに処理の完了、status、世代を確認してください。Redisを除外する公式tutorialと、独自のRedis構成を混同しないでください。この章のために実際のバックアップや復元は実施していません。

## Prometheusでメトリクスを収集する

Host、kubelet/container、GPUのメトリクスは別々に扱ってください。`node_cpu_seconds_total`と`node_memory_*`はNode Exporterが提供するもので、kubelet endpointのメトリクスではありません。導入済みで内容を確認したNode Exporter/DCGM設定を使い、実際のhost mount、権限、配置node、メトリクスの有無を検証してください。Container InsightsはEC2 IMDSを介してHybrid host levelのメトリクスを提供しません。

次のdiscovery例は、monitoring namespaceでreleaseを`kube-prom`としたkube-prometheus-stack 92.9.0のNode Exporter Service label/portを使います。DCGM部分は、`gpu-operator` namespaceにあり`app: nvidia-dcgm-exporter` labelを持つPodと、`metrics`という名前付きcontainer portが確認済みであることを前提とします。導入済みexporterに合わせて調整してください。どちらのresourceもexporterをインストールするものではありません。Prometheus resourceのmonitor/namespace selectorと一致させ、既存monitor経由のscrapeと重複しないようにしてください。

`attachMetadata.node`を設定するとNode discoveryのmetadataが利用可能になりますが、labelが自動的にmetricsへコピーされるわけではありません。ServiceMonitorではPrometheus 2.37以上、PodMonitorでは2.35以上が必要で、PrometheusにはNodeに対する`list`/`watch`権限も必要です。relabelingでは、実際の`eks.amazonaws.com/compute-type=hybrid` nodeを選び、安定した`node`/`compute_type` target labelを作成します。SSM Node名のprefixからHybrid配置を推測しないでください。

これらの例では、kubeletのHTTPS endpointではなく、exporterが保護しているHTTP metrics endpointを使います。collectorからの接続範囲を制限してください。信頼できないnetwork境界を越える場合は、exporterのTLS/authenticationまたは内容を確認したproxyと、対応するCA/authorization設定を使ってください。`insecureSkipVerify`は使用しないでください。kubeletのscrapeは、認証とCA検証を行う別の設定に保ちます。

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

### Grafana dashboardのquery例

これらのqueryには、上記のtarget labelと互換性のあるexporter metricsが必要です。unit、GPU/MIG identity、未対応値やerrorを示すsentinel、scrape欠損、重複seriesを確認してください。GPU framebufferの使用率は空き容量ではなく総容量（`used + free`）で割ります。容量が0のseriesは除外されます。ここに示すqueryはローカルで実行確認できる式であり、この環境で実際に計測した結果ではありません。

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

## Direct Connectの性能を検証する

テスト計画とAWSサービスの保証を区別してください。以前の例にあったRTT <5ms、variation <2ms、loss <0.01%、throughput >1Gbpsは、計測結果でもDirect Connect全般に適用される保証でもなく、計画用の例示目標です。実際のlocation、circuit、endpoint、workload、契約容量に応じて目標を決め、計測経路がVPNなど別経路ではなくDirect Connectを通ることを確認してください。

`ping`はICMP RTTを報告し、Linux iputilsではRTT mdevも表示します。このばらつきは、one-way delay variationやiperf3のUDP jitterと同じ統計量ではありません。ICMPへのfilteringや優先度低下はapplication trafficと異なる場合があります。1,000 packetのテストでlossを計測すると、刻み幅は0.1%です。lossが0回でも、長期的なloss rateが0.01%未満だと証明できるわけではありません。

承認済みのprivate test serverでiperf3が実行済みであることを確認し、時間帯を調整し、traffic上限を設定し、結果を保護して保存してください。iperf3をEKS API endpointに対して実行してはいけません。以下の上限付き例には、Bash、Python3、iputilsのping、GNU timeout、指定optionを備えたiperf3が必要です。途中で失敗したら残りの処理を停止します。必要なtoolがない、JSONが不正、iperf3がerrorを返す場合は、性能テストの合格とは扱いません。

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

この上限付きTCP testでlinkの最大容量が分かるわけではありません。receiver側のthroughput、再送、方向、実行時間、congestionを確認してください。別途承認されたUDP testでは、`--udp`と明示的なbitrateを指定し、そのiperf3版のJSONからreceiver側loss/jitterを保存して解釈してください。失敗またはskipしたprobeは、そのように記録してください。この監査中にnetwork負荷testは実施していません。

## 証明書の更新管理

どの証明書を確認するかを特定してください。Harbor TLS server証明書、CA chain、kubelet serving certificate、EKS control plane CA、IAM Roles Anywhere host certificateは、それぞれ別の対象です。CA証明書が有効でも、server leaf certificateが有効だとは限りません。また、NodeのReady heartbeatは、証明書の有効期限を示す証拠ではありません。EKS control plane証明書はAWSが管理します。EKSの修復手順としてkubeadmの更新commandを実行しないでください。

次のローカル有効期限確認は、証明書がない、読めない、不正、または例示の警告期間30日以内に期限切れとなる場合に失敗します。certificate chain、hostname、失効状態、serviceが実際にその証明書を提示しているかは検証しません。提供中のendpointには、以下の検証済みTLS接続を使ってください。host certificateの更新は[credential lifecycle手順](./07-node-lifecycle.md)を参照してください。

```bash
set -euo pipefail
: "${CERT_PATH:?Set the actual certificate file to inspect}"
test -r "$CERT_PATH"
openssl x509 -in "$CERT_PATH" -checkend 2592000 -noout
```

実際のissuer/owner、設定されたcertificate path、有効期限、alertが届くことを記録してください。kubelet serving/client credentialのpathは設定により異なります。serverTLSBootstrapを有効にしただけではserving CSRが承認されず、IAM Roles Anywhere certificateもローテーションされません。

## Ingressの設定

### ALB Ingress（ip target mode）

Self-managed AWS Load Balancer Controllerでは、`alb.ingress.kubernetes.io/target-type: ip`を使って、network上で到達可能なHybrid Pod IPを登録できます。route、戻り通信、security group/firewall、EKSのremote Pod network設定が互いに整合している必要があります。

AWSのmixed-mode webhook手順では、controllerをcloud nodeに配置します。これはその設計における配置推奨であり、Hybrid Nodesでwebhookを実行できないという一般論ではありません。add-onの案内では、control planeから設定済みremote Pod CIDRに到達できる場合、Hybrid配置も認められています。`compute-type NotIn [hybrid]`はlabelのないnodeにも一致するため、これより明示的な管理用配置labelを優先してください。以下の例のlabelは、適格であることを確認したcloud nodeだけに付与します。

```yaml
# Fragment under the controller Deployment's spec.template.spec:
nodeSelector:
  infrastructure.example.com/location: aws
```

### Cilium Ingress Controller

この節のCilium Ingress/Gateway API例を使うには、L7を有効にしたCilium設定が必要です。次の[EKS Hybrid Nodes Gateway](./10-hybrid-nodes-gateway.md)用に設定されたCiliumと同じinstallでは使えません。[AWSが要求するVTEP設定](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-gateway-cni.html)では`vtep.enabled=true`、`l7Proxy=false`が設定されるためです。これらの機能を有効にする前にnetwork設計を決めてください。この制約はCiliumのL7 proxy機能に関するもので、gatewayのroute経路を通るHTTP applicationを禁止するものではありません。

Cilium 1.18.3 upstreamのIngress前提条件には、NodePort対応（またはkube-proxy replacement）、L7 proxy対応、load balancerを公開する経路が含まれます。次のfragmentは、mixed cluster内のcloud nodeでCNIを変更する許可を意味しません。レビュー済みHybrid Cilium設定を維持し、追加機能がAWSのsupport範囲内か確認してください。dedicated/shared modeの変更はaddressを変え、既存connectionを中断する可能性があります。

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

選択したcontroller releaseが対応するGateway API CRD/resource versionをインストールしてください。NodePort/kube-proxy replacementとL7の前提を確認し、GatewayClass/Gateway/Routeのconditionも調べます。Helm flagを一つ設定しただけではCRDはインストールされず、外部からの到達性も確立されません。

```yaml
# Required Gateway API CRDs and controller prerequisites must already be met:
gatewayAPI:
  enabled: true
```

### LoadBalancer IPAM（Cilium）

次のpoolはCilium 1.18.3 CRDで検証した`cilium.io/v2` APIを使い、明示的にlabelを付けたServiceだけを選択します。例示CIDRを、network inventoryで予約済みの重複しないaddress rangeに置き換えてください。IPを割り当てても、routerへaddressが広告されたり、data pathが動作したりする保証はありません。

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

## Load Balancing

### NLB（ip target mode）

Self-managed AWS Load Balancer Controllerを使う場合、controllerが管理する`LoadBalancer` Serviceに`spec.loadBalancerClass: service.k8s.aws/nlb`と`service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip`を設定します。選択したcontrollerについて、文書化された`aws-load-balancer-type: external`のownership経路を使う方法もあります。target typeのannotationだけでは、どのcontrollerがServiceを管理するかは決まりません。Hybrid Pod targetと戻りrouteがAWSから到達可能であることを確認し、internal/public exposure、subnet、access controlを意図的に選択してください。

これはEKS Auto Modeのownership手順ではありません。既存Serviceのclass/controllerを置き換えるときは、置換やtrafficへの影響を確認せずにin-place migrationしないでください。

### Cilium LB + BGP

インストール済みの`cilium.io/v2` schemaを使ってください。Service address typeは`advertisements[].service.addresses`の下に指定します。この例では、`exposure: onprem-bgp` labelがあるServiceのLoadBalancer IPだけを広告します。実質的にすべてのServiceを選択してしまう`NotIn` selectorは使いません。

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

CiliumBGPClusterConfigでnode/peerの選択を設定し、CiliumBGPPeerConfigでaddress familyを設定してください。peer configurationのadvertisement selectorは`advertise: hybrid-services`に一致する必要があります。Service selectorも、実際のService labelに一致させてください。レビュー済みBGP control planeを有効化し、router sessionを確立したうえで、受理されたroute、next hop、戻り経路、traffic policyを検証します。IPPool/Advertisementだけでは設定は完了しません。[ネットワーク設定の基礎](./02-network-configuration.md)と、インストール済みバージョンのBGP文書を確認してから変更を適用してください。

## Add-onの詳細設定

### CloudWatch Observability Agent

サポートされているPod Identity設定を使い、実際のIAM associationとpermissionを確認してください。Hybrid対応で使う変数`RUN_WITH_IRSA`は名前にかかわらず、現在のAWS手順でも必要です。既存`AmazonCloudWatchAgent` resourceの**spec.env list**に追加し、`K8S_NODE_NAME`などの既存entryを維持してください。EKS add-onのconfigurationValuesにある任意のトップレベル`env`ではありません。

```yaml
# Add this item to the existing AmazonCloudWatchAgent.spec.env list:
- name: RUN_WITH_IRSA
  value: "True"
```

編集前に`amazon-cloudwatch` namespaceの`amazoncloudwatchagents/cloudwatch-agent`を調べ、add-on/operatorがどのように設定をreconcileするかを確認してください。変更後はagentのrolloutとcollectionを確認します。Hybrid cluster/workload/Pod/container metricsは利用できますが、EC2 IMDS依存がないため、node-level Container Insights metricsは利用できません。operatorがHybrid Nodes上で動作する場合は、control planeからwebhookへ到達できることも確保してください。

### EKS Pod Identity Agent

| Host OS | 文書に記載された最小バージョン | Hybrid DaemonSet / credential path |
| --- | --- | --- |
| Ubuntu、RHEL、AL2023 | Add-on 1.3.3-eksbuild.1 | `hybrid`; `/eks-hybrid/.aws/credentials` |
| Bottlerocket（サポート対象のVMware variant） | Add-on 1.3.7-eksbuild.2およびOS 1.39.0 | `hybrid-bottlerocket`; `/var/eks-hybrid/.aws/credentials` |

これらは機能の最低バージョンであり、古いreleaseのインストールを推奨するものではありません。現在互換性のあるadd-on versionを選び、configuration schemaを確認してください。Ubuntu/RHEL/AL2023では、次のfragmentを各hostの既存の完全なNodeConfigへmergeします。

```yaml
# Merge this fragment into each host's complete, protected NodeConfig:
spec:
  hybrid:
    enableCredentialsFile: true
```

AWSは、すでにjoin済みのnodeも含め、対象hostごとに`nodeadm init -c file:///path/to/nodeconfig.yaml`を計画的に再適用することを求めています。本番nodeを無計画にすべて再初期化しないでください。identity/configurationを維持し、lifecycle手順に従って、一度に1台ずつ検証します。Bottlerocketでは、このnodeadm fragmentではなく、文書化された設定経路を使ってください。これらの一時credential fileは機密情報です。内容を表示しないでください。

Bottlerocket以外のHybrid DaemonSetでは、add-on configurationに次の設定が含まれます。

```json
{
  "daemonsets": {
    "hybrid": {
      "create": true
    }
  }
}
```

Bottlerocketでは、選択したversionに対応する文書化済み`hybrid-bottlerocket` configurationを使い、既存設定を確認してmergeしてください。add-onが存在しない場合にだけ作成します。既存add-onは、競合を確認してから更新してください。無条件にcreateやOVERWRITEを使わないでください。Agentとcredential fileだけでは、すべてのapplicationのPod Identity associationは作成されません。namespace、ServiceAccount、IAM role trust/permission、SDKのcredential解決、authorizationの成功を確認してください。

## Mixed-mode webhookの運用 {#mixed-mode-webhook-operations}

AWSがサポートするmixed-mode構成では、cloud nodeでVPC CNIを、Hybrid NodeでCilium/Calicoを動作させます。この構成でAWSはwebhookをcloudに配置することを推奨しています。Hybrid上のwebhookには、到達可能なremote Pod CIDRとcontrol planeからの接続性が別途必要です。すべてのwebhookがどこでも動く、またはどこでも動かせないと決めつけず、実際のendpointを確認してください。

### CoreDNSの配置

このmixed-mode設計では、少なくとも1つのCoreDNS replicaをcloud nodeに、もう1つをHybrid Nodeに配置することをAWSは推奨しています。desired replicaが2以上であること、配置可能なcapacity、selector、toleration、実際のendpointを確認してください。`maxSkew: 1`だけでは2つのdomainが作られず、各domainに1 Podずつ配置される保証もありません。また、cloud nodeに`eks.amazonaws.com/compute-type` labelがない場合があります。

`minDomains`をサポートするclusterでは、次のPod spec fragmentで、管理者が明示的に定義した2つのdomainを使います。対象DNS nodeだけにlabelを付け、配置可能なすべてのnodeに`aws`または`onprem`のいずれか正確な`location`値があることを検証してください。既存affinity/tolerationとの互換性を保ち、add-onがサポートする設定方法で変更を反映します。

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

配置対象となるdomainが2つあり、replicaが2つ以上あれば、strict spreadingにより両domainに分散してscheduleされます。片方のdomainにcapacityがなければ、新しいreplicaはPendingのままになる場合があります。これは可用性とのtrade-offであり、failoverの保証ではありません。実際のDNS Service/EndpointSliceと、local/remote両方の名前解決を検証してください。Auto Modeを含むclusterでは、node-local DNSというsystem serviceと、Auto Mode対象外node向けに引き続き必要なDeploymentを区別してください。

<span id="per-add-on-nodeaffinity-settings-guide"></span>

### Add-onごとの配置ガイド

| Add-on | この設計での配置 | 必要な確認事項 |
| --- | --- | --- |
| AWS Load Balancer Controller | AWSのmixed-mode手順ではcloud node | webhook到達性、明示的な配置label、到達可能なHybrid IP target |
| CloudWatch agent/operator | agentはサポート対象node、operator webhookはcloudを優先 | IAM/agent health、Hybridのnode-level metricsは対象外 |
| cert-manager | webhookはcloudを優先。到達可能なHybrid配置も可能 | control planeの接続性とremote Pod network |
| Metrics Server | cloudに配置するか、到達可能なHybrid Pod endpointを使う | control planeからPod、およびMetrics Serverからkubeletへの経路 |
| CoreDNS | cloud nodeとHybrid Nodeの両方にreplicaを確認 | 配置可能なdomain、capacity、実際のDNS traffic |
| Cilium/Calico | AWSがサポートするmixed-CNI設計ではHybrid Node | cloud nodeではVPC CNIを維持 |

## ネットワーク切断時の挙動と備え

この節では、Direct ConnectまたはVPNが短時間切断された場合やnetworkが応答しなくなった場合に、何が継続し何が停止するかを説明します。Hybrid Nodesは頻繁な切断が起きるDDIL環境を想定しておらず、AWSへの安定した接続を前提としています（[概要](./README.md)を参照）。

### 切断中のclusterとworkload

| 項目 | 挙動 |
|---|---|
| 稼働中Pod | node上で実行を続けます。kubeletはLeaseを更新できず、NodeのReady conditionは`Unknown`になり、`node.kubernetes.io/unreachable` taintが追加されます（`NoSchedule`、条件を満たす場合は`NoExecute`も追加）。 |
| Pod failover | tolerationのないPodは、control planeにより既定300秒後にevictされ、別nodeにreplacement Podが作成されます。DaemonSet Podは既定でこのtaintをtolerateするため、元node上に残ります。 |
| Zone label | nodeに`topology.kubernetes.io/zone`が設定されている場合、そのzoneの全nodeがunreachableになるとKubernetesはzone内のevictionを取り消します。Hybrid Nodeにはcloud-controller-managerがないため、nodeadmの`--node-labels`でdata centerごとのzoneを設定します。 |
| Cilium | agent healthはcontrol planeへの接続性に依存するため、切断中はagentがrestartを繰り返し、Cilium BGP Control Plane sessionが停止する場合があります（CFP #31702、Cilium 1.17でopt-inの改善）。AWSの例で使われたMetalLB L2 modeは、切断中も安定していました。 |
| AWS serviceへの依存 | ECR image pull、CloudWatch、Amazon Managed Service for Prometheus、ALB/NLB、S3、RDSなどのRegional serviceは、切断中に利用できません。 |
| local troubleshooting | API serverへ接続できません。`kubectl`の代わりにhost上で`crictl pods`、`crictl ps`、`crictl logs <container>`を使います。 |

### Credentialと再接続

| 項目 | SSM hybrid activation | IAM Roles Anywhere |
|---|---|---|
| 一時credential | 有効期間は固定の1時間で、変更できません。通常運用中はnodeやapplicationに影響せず、期限前に自動更新されます。 | 既定は1時間です。profileの`durationSeconds`により最大12時間まで延長できます。node IAM roleの`MaxSessionDuration`は、それより長く設定する必要があります。 |
| 切断中 | SSM Regional endpointへ到達できずrefreshに失敗します。長時間切断するとcredentialが期限切れになる場合があります。 | AWSへ接続できないため、新しいcredentialを取得できません。 |
| 復旧後 | SSM agent **3.3.808.0以降**は、最大30分のexponential backoffでretryします。**network復旧後もnodeの再接続に最大30分かかる場合があり**、nodeごとに再接続時刻が異なるため、先に復帰したnodeへPodがfailoverすることがあります。 | kubeletは必要に応じて`aws_signing_helper credential-process`でcredentialを取得するため、通常は**数秒以内**に再接続します。 |
| 復旧を早める方法 | 以下のcommandでSSM agentをrestartし、refreshを強制します。 | certificateが有効な間は操作不要です。certificateの有効期限通知を設定してください。 |

SSM agentのversion、restart、log:

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

切断中はlogに`Retrieve credentials produced error: RequestError: send request failed`と`Sleeping for ... before retrying retrieve credentials`が繰り返し記録されます。refreshが成功すると`Credentials ready`が記録されます。

### 事前準備のチェックリスト

- **接続の冗長化:** Direct Connectを冗長化するか、backupとしてSite-to-Site VPNを用意します。
- **切断の検知:** EKS control planeのController Manager logを有効にします。`Recording status change event message for node` messageに`status="NodeNotReady"`が含まれる場合のCloudWatch metric filterとalarmを作成してください。TGWの`BytesIn`/`BytesOut`、またはVGWの`TunnelDataIn`/`TunnelDataOut`が平常値より低下した場合もalertします。CloudWatch Network Monitorでlossとlatencyを確認できます。
- **SSM agentのversion:** retry間隔が30分で上限となる3.3.808.0以降を使います。
- **Zone label:** data centerごとの`topology.kubernetes.io/zone`を設定します。
- **evictionの調整:** 移動が難しいapplicationでは`tolerationSeconds`を長くします。ただし、nodeが実際に故障した場合にPodを退避するまでの時間も延びます。

```yaml
# Fragment under the Deployment's spec.template.spec
tolerations:
  - key: "node.kubernetes.io/unreachable"
    operator: "Exists"
    effect: "NoExecute"
    tolerationSeconds: 1800
```

- **Credential provider:** 切断が頻繁で迅速な再接続が必要な場合は、`durationSeconds`を長くしたIAM Roles Anywhereを検討してください。cluster内で使うproviderは一つに統一してください。
- **監視の副経路:** Regional serviceへ接続できない間も監視を続けられるよう、ADOT collectorから複数のbackendへ送信する構成にします。

参考資料:
- [ネットワーク切断時のhost credential](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-host-creds.html)
- [ネットワーク切断時の安定性に関するベストプラクティス](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-network-disconnection-best-practices.html)
- [ネットワーク切断時のKubernetes Pod failover](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-kubernetes-pod-failover.html)

## よくあるトラブルシューティング

### ImagePullBackOffの診断

Pod eventを読み、参照されたSecretのname/typeを調べてください。registry credentialをdecodeしたり表示したりしてはいけません。SecretはPodと同じnamespaceになければなりません。registry hostname、repositoryに必要なpermission、credentialの有効期限を担当者に確認します。metadataを見るだけでは、認証が実際に成功することは証明できません。

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

実際のhost/network経路から、信頼するCAとhostname検証を有効にしてTLSを検査してください。`curl -k`を使わないでください。また、認証していないregistryが返す401 responseをTLS失敗と解釈しないでください。この例ではBash、OpenSSL、GNU timeoutが必要です。

```bash
set -euo pipefail
: "${HARBOR_HOST:?Set the registry DNS name, without scheme or port}"
: "${HARBOR_CA_FILE:?Set the approved CA bundle file}"
timeout 10s openssl s_client -connect "$HARBOR_HOST:443" \
  -servername "$HARBOR_HOST" -verify_hostname "$HARBOR_HOST" \
  -verify_return_error -CAfile "$HARBOR_CA_FILE" </dev/null
```

Pod内でDNS/networkを検査するには、digestを固定した承認済みdiagnostic imageを、専用namespaceに配置し、障害のあるHybrid Node上で実行してください。任意のdebug Podをtag固定なしで作ると、cloud nodeで実行され、誤った経路を検査する可能性があります。Podの作成/削除は別途確認し、対象を限定した結果を保存してください。

### DNS名前解決の問題

実際のCoreDNS Deployment/Pod、Service、EndpointSlice、cloud/on-premisesの配置、DNS設定、network到達性を確認してください。障害が起きているworkload環境からregistry nameと`kubernetes.default.svc.cluster.local`を検査します。API、DNS、log accessに失敗して観測できなかった場合は「確認成功」ではなく「状態不明」です。

診断の最初にすべてのCoreDNS Podをrestartしないでください。まず障害の層を特定し、restartする場合は冗長性と復旧確認を考慮して調整します。Auto Modeを含むmixed clusterではnode-local DNSの挙動もあり得るため、障害Podが実際にどのresolver経路を使っているか確認してください。

### Node接続の問題

inventoryに記載された実際のNode nameと対応するhostを使ってください。SSM管理のNode nameが`hybrid-`で始まるとは限らず、hostnameとして名前解決できるとも限りません。

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

credential providerとOS固有のagent unitを確認してください。該当する場合は、Ubuntuのsnap版SSM installationも確認します。network/authenticationの診断には、root権限で検証済みの`nodeadm debug -c file:///etc/eks/nodeconfig.yaml`手順を使い、出力を非公開で保存してください。AWSとclusterに接続します。発行されたcredentialをlogに出したり、TLS検証を無効にしたりしないでください。

確認済みのnodeadm 1.0.20 CLIに`nodeadm reset` subcommandはありません。NotReadyだけを理由に、hostを無条件でderegister/reinitializeしないでください。原因を特定した後、mount/dataを維持し、Node/SSM identityを記録しながら[復旧とidentityの整合](./07-node-lifecycle.md)に従ってください。

## 検証範囲と参考資料

ローカル検証では、固定したresource schema、合成sampleを使う4つのPromQL式、11のbackup/network command-double caseを確認しました。AWS/Kubernetesの変更、実際のbackup/restore、network負荷test、BGP session、exporter scrape、本番rolloutは実行していません。deploy前に、現在のAWSサポート文書に基づきEKS/OS/CNI/add-onの組み合わせを選択してください。

- [AWS Hybrid add-on](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)
- [AWS Hybrid webhook](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-webhooks.html)
- [AWS Hybrid upgrade](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-upgrade.html)
- [Prometheus Operator API](https://prometheus-operator.dev/docs/api-reference/api/)
- [Cilium 1.18.3 Ingressの前提条件](https://github.com/cilium/cilium/blob/v1.18.3/Documentation/network/servicemesh/ingress.rst)
- [Cilium 1.18.3 LoadBalancer IPPool CRD](https://github.com/cilium/cilium/blob/v1.18.3/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumloadbalancerippools.yaml)
- [iperf3の実行方法](https://software.es.net/iperf/invoking.html)
- [Kubernetes taintとtoleration](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)


---

< [前へ: ノードのライフサイクル管理](./07-node-lifecycle.md) | [目次](./README.md) | [次へ: ベアメタルOSのセットアップ](./09-bare-metal-os-setup.md) >
