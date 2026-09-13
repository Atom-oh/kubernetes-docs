# Datadog

> **最終更新**: September 13, 2026
> Helm chart 3.244.0、対応する Agent/Cluster Agent 7.83.1。
> 設定、SDK、ローカル検証の制限事項は以下に記載しています。Datadog tenant は変更していません。

## はじめに

Datadog は SaaS observability backend を提供します。チームは引き続き collector、identity、
network access、instrumentation、データ開示、retention、monitor、コストに責任を持ちます。
Infrastructure Monitoring、APM、profiling、logs などの product にはそれぞれ異なる
entitlement と課金単位があります。Agent をインストールしても、すべての product が含まれるわけではありません。

| 項目 | Datadog | CloudWatch | Self-managed Prometheus / Grafana |
| --- | --- | --- | --- |
| Backend | site 固有の可用性を持つ Datadog SaaS | AWS 管理サービス | 運用する storage、query、visualization |
| Collection | Agent/Cluster Agent、library、対応する OTel path | AWS service metric、agent/SDK/OTLP | Exporter、scraping、agent、remote write |
| APM/logs | 必要な product を選択して設定 | Application Signals、tracing、Logs integration | 関連する backend と collector を設定 |
| Operations | collector/configuration と application の責任は引き続き残る | collection/configuration と response の責任は引き続き残る | backend と collection の責任は引き続き残る |
| Cost | Host および product 固有の usage/retention 単位 | Metric/observation/OTLP/log/query/alarm 単位 | Infrastructure と運用労力 |

組織とその credentials に適した Datadog **site** を選択してください。
API endpoint、data residency、利用可能な product、価格条件は site 間で
相互に交換可能ではありません。固定的な integration 数の主張や、普遍的な「easy/advanced/cheap」の順位付けではなく、
integration catalogue を使用してください。

## EKS integration architecture

| Component | 責任範囲 / 境界 |
| --- | --- |
| Node Agent | Host/container check。通常は対応する EC2 node 上の DaemonSet |
| Cluster Agent | 共有する Kubernetes metadata/check、event coordination、および任意の admission/external-metric 機能 |
| Trace Agent | application trace payload を受信して転送 |
| Process collection / system-probe | 独自の OS、privilege、product 要件を持つ任意の process/network/security 機能 |
| Admission Controller | connection setting と、設定時には対応する client library を新しい Pod に inject |

Application instrumentation は trace/profile を生成します。Agent listener または Pod
label だけでは instrumentation の証明にはなりません。Cluster Agent は通常の
application-log または trace forwarding path ではありません。

この章のインストール対象は **Linux EC2-backed EKS node** です。EKS Fargate
では、この host DaemonSet ではなく、文書化された Pod 単位の sidecar collection model を使用します。
UDS は host にローカルであり、Windows ではサポートされません。Windows、Bottlerocket、
Auto Mode、および mixed compute には、distribution/feature 固有の設定と
対応する host access が必要です。TLS verification を無効化したり、すべての eBPF/process
機能がどこでも動作すると主張したりしないでください。

Datadog は、`AllocatedResources` を使用する Kubernetes 1.33+ 互換性のために Agent と
Cluster Agent 7.67+ を文書化しており、これらの version を一致させることを推奨しています。
このような最小機能要件は、現在の EKS support matrix ではありません。

概要は可能な collection path を示しています。trace/profile には application instrumentation と選択した product が必要です。Watchdog notification routing は設定する必要があります。

![Datadog node Agent telemetry と Cluster Agent metadata は、設定された SaaS product に到達します。](../../.gitbook/assets/en-observability-metrics-05-datadog-1.png)

[インタラクティブ図](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-metrics-05-datadog-1.html)

## Datadog Agent のインストール

Datadog は上位レベルの lifecycle configuration には Operator を推奨し、Helm installation も
サポートしています。この例では、**Datadog Agent Helm chart** を介して node/Cluster Agent を管理します。
Chart 3.244.0 は任意の Operator dependency を bundle します。
`datadog.operator.enabled: false` は、この例からその追加 controller を除外します。
これは Operator が obsolete であることを意味しません。

Chart のデフォルトは Agent/Cluster Agent 7.82.3 です。この例では両方を
**7.83.1** と検証済み image-index digest に明示的に pin します。release には network-test
billing、containerd snapshot cleanup、Cluster Agent leader-lock shutdown の修正が含まれます。
Agent/Cluster Agent image index には Linux amd64/arm64 が含まれます。template render の成功は
Kubernetes deployment または runtime compatibility test ではありません。

### Credentials と installation ownership

基本的な Agent ingestion には、Agent と同じ namespace にある API key が必要です。
external metrics provider など API read/control 機能には application key が必要ですが、
基本 Agent をインストールするだけでは不要です。選択した機能が必要とする場合にのみ、
scoped application key を使用してください。

credentials は承認済みの Secret workflow で管理してください。以下の file command は、
従来の引用符なしの `<YOUR_API_KEY>` による shell-redirection 問題と、process
argument での key 露出を回避します。credential workflow に従って一時 key file を
保護し、削除してください。Kubernetes Secrets にも適切な access および encryption control が必要です。
別の release または controller が所有する resource に対して、この installation を実行しないでください。

```bash
helm repo add datadog https://helm.datadoghq.com
helm repo update datadog
kubectl create namespace datadog --dry-run=client -o yaml | kubectl apply -f -

# The protected file contains only the API key; obtain it through your approved secret process.
# Do not put the key in command-line literals, Git or terminal output.
: "${DATADOG_API_KEY_FILE:?Set the path to the protected API-key file}"
kubectl create secret generic datadog-secret --namespace datadog \
  --from-file="api-key=$DATADOG_API_KEY_FILE" --dry-run=client -o yaml | kubectl apply -f -

helm template datadog datadog/datadog --version 3.244.0 \
  --namespace datadog --include-crds --values datadog-values.yaml > datadog-rendered.yaml

# This changes the cluster. Review the rendered resources and installation ownership first.
helm upgrade --install datadog datadog/datadog --version 3.244.0 \
  --namespace datadog --values datadog-values.yaml
```

### レビュー済み values

以下を `datadog-values.yaml` として保存します。logs は container
configuration により opt-in です。APM/DogStatsD は UDS を使用し、cluster-wide automatic library injection、
external HPA metrics、discovery network statistics、および任意の process/network
collection はここでは有効化していません。application namespace は Agent namespace と
分離する必要があります。SSI は Agent 自身の namespace の Pod を instrument しません。

```yaml
targetSystem: linux
registry: gcr.io/datadoghq
datadog:
  apiKeyExistingSecret: datadog-secret
  clusterName: my-eks-cluster
  site: datadoghq.com
  tags:
  - env:demo
  - team:platform
  logs:
    enabled: true
    containerCollectAll: false
    containerCollectUsingFiles: true
  apm:
    socketEnabled: true
    portEnabled: false
    instrumentation:
      enabled: false
  dogstatsd:
    useSocketVolume: true
    useHostPort: false
    nonLocalTraffic: false
  processAgent:
    processCollection: false
    processDiscovery: false
    containerCollection: true
  networkMonitoring:
    enabled: false
  discovery:
    enabled: false
    networkStats:
      enabled: false
  autoscaling:
    workload:
      enabled: false
  profiling:
    enabled: null
  collectEvents: true
  prometheusScrape:
    enabled: false
  kubeStateMetricsCore:
    enabled: true
    collectSecretMetrics: false
    collectConfigMaps: false
  operator:
    enabled: false
clusterAgent:
  enabled: true
  replicas: 2
  image:
    tag: 7.83.1
    digest: sha256:8e420c81e68abec34ab792c72a6513b739dcba8f7682c52e1e7e276363827b1a
  metricsProvider:
    enabled: false
    useDatadogMetrics: false
  admissionController:
    enabled: true
    mutateUnlabelled: false
agents:
  image:
    tag: 7.83.1
    digest: sha256:ed0bd588e955d82f661d1b8dd1cdf179c1023e74a2817e7a812c99d52f05c319
```

`processAgent.enabled` は deprecated です。個別の collection option を使用してください。
chart は該当時にすでに `/etc/passwd` を mount するため、重複する手動の
`passwd` volume/mount を追加しないでください。resource override は
`agents.containers.agent.resources` など component ごとです。実際に render された container を負荷時に sizing してください。
2 つの Cluster Agent replica は placement、disruption、failure test の代替にはなりません。

元の top-level `kubeStateMetricsEnabled` および `prometheus.enabled` entry は、
主張された integration を設定しません。legacy KSM option は `datadog` の下に nest されています。
この例は `datadog.kubeStateMetricsCore.enabled` を使用し、重複する legacy collection を回避します。
明示的な Datadog Autodiscovery check は、annotation-wide `prometheusScrape` を有効化することとは別です。

`datadog.profiling.enabled` は **有効** です。これは eligible Pod に `DD_PROFILING_ENABLED` を inject し、
インストール済み client library と Cluster Agent 7.57+ を必要とします。
任意の uninstrumented application に profiler をインストールするものではありません。
`null`/`false`/`auto`/`true` の動作を意図的に選択してください。同様に、external HPA metrics の有効化には
application key、API permission、service/CRD、実際の metric availability が必要です。network monitoring には対応する system-probe access が必要です。

### AWS account integration は別の path です

SaaS AWS account integration は、選択した integration に必要な permission を持つ、
authorized cross-account role と Datadog 提供の external ID を使用します。
node Agent SA に付与した任意の IRSA role は、その SaaS integration を設定しません。
通常の Kubernetes Agent collection には、ここで以前示した広範な
CloudWatch/EC2/tag policy は必要ありません。

実際に AWS を呼び出す Agent/check に対してのみ、その固有の role、trust、permission と共に
Pod Identity または IRSA を使用してください。**render された** service-account 名を解決してください。
推測した `datadog-agent` SA 用に IAM association を作成しても、Helm release が使用する
別の SA は bind されません。local STS caller check を workload の identity の証明として扱わないでください。

## Infrastructure Monitoring

### metric の collector、unit、tag を確認する

| Metric / source | 意味 |
| --- | --- |
| `system.cpu.idle` / System check | CPU idle **percent**。percentage-based node threshold に適している |
| `system.mem.total`, `system.mem.used`, `system.mem.free` | Memory measurement。free は usable/reclaimable memory と同一ではない |
| `kubernetes.cpu.usage.total` / Kubelet | **Nanocore**。percent ではない。1 core は 1,000,000,000 nanocore |
| `kubernetes.memory.usage`, `kubernetes.memory.limits` | Byte。usage と limit の比較には同一 entity/tag set の一致が必要 |
| `kubernetes.pods.running`, `kubernetes.containers.restarts` | 有効な Kubelet gauge。実行中 Pod と累積 container restart |
| `kubernetes_state.deployment.replicas_available`, `kubernetes_state.deployment.replicas_desired` | Kubernetes State Metrics Core の Deployment state |
| `kubernetes_state.pod.status_phase`, `kubernetes_state.service.count` | Pod phase/service inventory。文書化された grouping tag を確認する |
| `kubernetes_state.container.restarts` | namespace/pod/container tag を持つ State Core の restart gauge |

legacy Kubernetes integration、Kubelet check、State Core には異なる catalogue があります。
ある catalogue にない metric が、必ずしも Agent から削除されたわけではありません。
有効な Kubelet metric を無造作に rename しないでください。filesystem/network availability
および rate unit は collector/runtime に依存します。その metric の実際の定義を読んでください。

この Kubernetes installation には標準の `kube_cluster_name` tag を使用し、grouping の前に
実際の metric tag を確認してください。cluster-centric State Core metric が常に
`host` tag を持つとは限りません。`cluster_name` と `kube_cluster_name` は交換可能ではありません。
生の nanocore 値を 80 と比較しても、80% CPU を意味しません。

### OpenMetrics Autodiscovery

以下の **metadata fragment** を、container 名が `app` で port 9464 に gauge
`queue_depth` を公開する workload に merge してください。これはその application または endpoint を作成するものではありません。
annotation の container identifier は一致する必要があります。endpoint を保護し、必要に応じて TLS/authentication を設定してください。

```yaml
metadata:
  annotations:
    ad.datadoghq.com/app.checks: "{\n  \"openmetrics\": {\n    \"init_config\": {},\n\
      \    \"instances\": [\n      {\n        \"openmetrics_endpoint\": \"http://%%host%%:9464/metrics\"\
      ,\n        \"namespace\": \"my_app\",\n        \"metrics\": [\n          {\n\
      \            \"queue_depth\": \"queue_depth\"\n          }\n        ]\n    \
      \  }\n    ]\n  }\n}"
```

現在の `openmetrics` check は `openmetrics_endpoint` を使用します。これらの Datadog
Autodiscovery annotation には、別の Prometheus server や chart の広範な
`prometheusScrape` discovery は必要ありません。選択する metric/label を制限してください。
counter と histogram では、Prometheus 名が最終的な Datadog 名でもあると仮定せず、
name normalization、出力される `.count`/bucket series、check-version behavior を検証してください。

### DogStatsD: application から到達可能な endpoint を使用する

application Pod の `localhost` は node Agent ではありません。Linux の例では
host-local UDS directory を使用します。Admission Controller の `socket` mode は
`DD_DOGSTATSD_URL`、`DD_TRACE_AGENT_URL`、および volume を inject できます。それ以外の場合は一致する
mount と permission を明示的に設定してください。Pod 固有の `admission.datadoghq.com/config.mode`
は annotation ではなく **label** です。Agent restart 後の socket replacement が引き続き見えるよう、
parent directory を mount してください。

Python helper は `datadog==0.53.0` で確認済みです。`socket_path` には
`/var/run/datadog/dsd.socket` のような実際の filesystem path を渡してください。
他の SDK/environment setting で使用する `unix://` URL は同じ argument format ではありません。
ゼロの good/error 値を含む実際の interval count で `emit_batch` を呼び出してください。

```python
from datadog import DogStatsd


def emit_batch(client, total, errors):
    """Report one real interval; send zeros instead of omitting counters."""
    if any(isinstance(x, bool) or not isinstance(x, int) for x in (total, errors)):
        raise ValueError("counts must be integers")
    if not 0 <= errors <= total:
        raise ValueError("require 0 <= errors <= total")
    client.increment("requests.total", total)
    client.increment("requests.error", errors)
    client.increment("requests.good", total - errors)


# Create once in an application with the Agent's UDS directory mounted.
# This construction does not mean that the socket or receiving Agent is ready.
def make_metrics_client(socket_path):
    return DogStatsd(
        socket_path=socket_path,
        namespace="my_app",
        constant_tags=["env:demo", "service:orders"],
        disable_telemetry=True,
        disable_buffering=True,
    )
```

Go helper は datadog-go/v5 を使用します。`WithNamespace("my_app.")` と同じ
`env:demo,service:orders` tag で client を作成してください。constructor、send、close の
error を確認し、`statsd.New` error を破棄しないでください。helper は caller が提供する
shared client を close しません。

```go
package metrics

import (
    "fmt"

    "github.com/DataDog/datadog-go/v5/statsd"
)

// The caller creates/reuses the client, checks New's error, and closes it at shutdown.
// For the Linux UDS example, use unix:///var/run/datadog/dsd.socket.
func EmitBatch(client *statsd.Client, total, errors int64) error {
    if errors < 0 || total < errors {
        return fmt.Errorf("require 0 <= errors <= total")
    }
    for _, item := range []struct {
        name string
        value int64
    }{
        {"requests.total", total},
        {"requests.error", errors},
        {"requests.good", total - errors},
    } {
        if err := client.Count(item.name, item.value, nil, 1); err != nil {
            return err
        }
    }
    return nil
}
```

| DogStatsD type | 解釈 |
| --- | --- |
| Counter | Interval count。Datadog はこれを rate として保存する場合がある。`.as_count()` は query window の count を再構成する |
| Gauge | queue depth などの snapshot。snapshot を合計しても processed-request count にはならない |
| Histogram | 受信する Agent により aggregate される。host ごとの percentile を平均しても global percentile にはならない |
| Distribution | backend distribution aggregation をサポート。有効化した percentile、tag、billing を確認する |
| Service check | 実際の health check の status: 0 OK、1 warning、2 critical、3 unknown |

local datagram delivery は SaaS ingestion を acknowledge しません。UDP は packet を失う可能性があります。
UDS/client buffering と Agent queue も監視が必要です。sample helper は DogStatsD client telemetry を
有効化しないため、deployment 用に別の collection-health signal を選択してください。
Counter retry/duplicate send は exactly-once business ledger ではありません。

### File-based Autodiscovery configuration

Helm 所有の configuration では、`datadog.confd` が check file を作成して mount します。
`datadog-checks` という名前の standalone ConfigMap は、存在するだけで自動的に discover されるわけではありません。
次の NGINX fragment には、一致する image identity と設定済みかつ authorized な `stub_status` endpoint が必要です。

```yaml
datadog:
  confd:
    nginx.yaml: "ad_identifiers:\n  - nginx\ninit_config: {}\ninstances:\n  - nginx_status_url:\
      \ http://%%host%%:80/nginx_status\n"
```

authenticated Redis check には、正しい port/TLS と credential delivery も必要です。
`%%env_REDIS_PASSWORD%%` は Redis application Pod の environment ではなく、**Agent の** environment を読み取ります。
設定済みの Datadog secret backend または必要な specific permission を持つ protected
file delivery を優先してください。public check example で password を露出したり、discovery のためだけに
cluster-wide Secret read を付与したりしないでください。

## APM と Distributed Tracing

### Local SDK injection と SSI は明示的な選択である

admission opt-in label は mutation/connection-setting injection を許可します。tracing library を
インストールするには、SSI target または対応する language/version annotation を設定してください。
label だけでは SDK がインストールされた、または trace が Datadog に到達した証明にはなりません。
Java/Python/Node.js local injection には Cluster Agent 7.40+ が必要です。.NET/Ruby には
7.44+ が必要です。現在の 7.83.1 も、`kube-system` と自身の namespace を injection から除外します。

制御された Java の例では、以下の **pod-template fragment** を application namespace 内の
既存 Deployment に merge し、selector、container、security setting を保持してください。
これは単独で apply する完全な Deployment ではありません。Java init image
`gcr.io/datadoghq/dd-lib-java-init:v1.66.0` は Linux amd64/arm64 向けに検証済みです。
実際の application の JVM/framework/image compatibility を確認してください。

```yaml
spec:
  template:
    metadata:
      labels:
        admission.datadoghq.com/enabled: 'true'
        admission.datadoghq.com/config.mode: socket
        tags.datadoghq.com/env: demo
        tags.datadoghq.com/service: orders
        tags.datadoghq.com/version: 1.0.0
      annotations:
        admission.datadoghq.com/java-lib.version: v1.66.0
```

`tags.datadoghq.com/*` label は unified service/environment/version tagging を提供します。
label を Deployment metadata のみに配置して、その Pod が継承すると期待しないでください。
injection は**新しい Pod** が admission されたときに行われます。inject された init
container、library file、UDS mount/permission、non-secret connectivity setting を確認し、
その後で実際の traffic/trace を検証してください。namespace exclusion、webhook failure、
security policy、unsupported image は instrumentation を妨げる場合があります。

cluster-wide SSI は、レビュー済み namespace/Pod target と library version による
`datadog.apm.instrumentation` を通じて設定する代替手段です。manual tracer と injected tracer を
意図せず組み合わせないでください。injected library は manually installed のものより優先される場合があります。
profiler の有効化には、引き続き対応する client library と独自の product/runtime condition が必要です。

### Manual Java instrumentation

application JVM の開始時に、staged で version 管理された `dd-java-agent.jar`、または上記の
検証済み injection route を使用してください。単に `dd-trace-api` を追加しても annotation/API へアクセスできるだけで、
runtime bytecode instrumentation は**開始しません**。以下の Maven dependency と Java source は別ファイルです。

```xml
<dependency>
  <groupId>com.datadoghq</groupId>
  <artifactId>dd-trace-api</artifactId>
  <version>1.66.0</version>
</dependency>
```
```java
import java.util.function.Supplier;
import datadog.trace.api.Trace;

public final class TraceMethods {
    private TraceMethods() {}

    @Trace(operationName = "order.process", resourceName = "process_order")
    public static <T> T process(Supplier<T> handler) {
        return handler.get();
    }
}
```

handler は caller が提供する application code を表します。operation/resource 名は bounded にしてください。
以前の例にある order/customer identifier tag は、このデモには不要であり、
disclosure/cardinality risk を生む可能性があります。manual span API には対応する supported bridge/library が必要です。
annotation API しかない project に OpenTracing import を追加しないでください。

### Manual Python instrumentation

この確認済みの 4.14.0 例では、現在の `ddtrace.trace` import を使用してください。
dependency declaration は Python code block 内ではなく `requirements.txt` に保持してください。
framework auto-instrumentation では、application import 前に選択した `ddtrace-run`/SSI setup に従ってください。
この helper が framework 全体を patch するとは想定しないでください。

```text
ddtrace==4.14.0
```
```python
from ddtrace.trace import tracer


def process_order(handler):
    with tracer.trace("order.process", service="orders", resource="process_order") as span:
        span.set_tag("operation.kind", "order")
        return handler()
```

同等の `tracer.wrap` decorator は method tracing に使用できます。handler からの exception は伝播する必要があります。
span の記録は application retry や成功の保証ではありません。対応する HTTP/message integration 間で、
正しい service/env/version tag と context propagation を使用してください。service map は任意の
`DD_TAGS` だけではなく、観測された instrumented relationship から生成されます。

raw customer/order identifier、token、request body をデフォルトで tag 付けしないでください。
実際の application について instrumentation capture、error message、sampling/redaction rule をレビューしてください。
auto-instrumentation は PII の完全な除去を保証しません。

## Log Management

### collection と parsing を意図的に選択する

installation は log collection を有効化しますが、`containerCollectAll: false` のままです。
この metadata を、container 名が `app` の Pod template に merge してください。
multiline rule は、**日付で始まる plain-text Java record** に適用されます。
汎用的な JSON-log parser ではありません。container runtime framing と application
message parsing は別段階です。実際に収集された record を検証してください。

```yaml
metadata:
  annotations:
    ad.datadoghq.com/app.logs: "[\n  {\n    \"source\": \"java\",\n    \"service\"\
      : \"orders\",\n    \"log_processing_rules\": [\n      {\n        \"type\": \"\
      multi_line\",\n        \"name\": \"java_timestamp_start\",\n        \"pattern\"\
      : \"^\\\\d{4}-\\\\d{2}-\\\\d{2}\"\n      }\n    ]\n  }\n]"
```

1 行につき 1 JSON event の application では、この rule で無関係な JSON event を結合するのではなく、
対応する JSON path を使用してください。file access、runtime path、annotation matching、exclusion setting、
backend pipeline filter はすべて collection に影響します。一致する application と除外された application の両方で
selective collection を確認してください。

### Pipeline request structure

この request は実際の API field **`match_rules` および `support_rules`** を使用します。
以前の camelCase field は Logs API model ではありませんでした。sample message は期待する line format を定義します。
application の実際の format/timezone を使用し、unmatched/multiline/error case を test してください。
有効な request model は、Datadog tenant での Grok parsing や ingestion/indexing を証明しません。

```json
{
  "name": "Java application logs",
  "is_enabled": true,
  "filter": {
    "query": "source:java service:orders"
  },
  "processors": [
    {
      "type": "grok-parser",
      "name": "Parse the documented Java line format",
      "is_enabled": true,
      "source": "message",
      "samples": [
        "2026-09-13 12:00:00,123 INFO [main] example.Service - completed"
      ],
      "grok": {
        "support_rules": "",
        "match_rules": "java_log %{date(\"yyyy-MM-dd HH:mm:ss,SSS\"):timestamp} %{word:level} \\[%{notSpace:thread}\\] %{notSpace:logger} - %{data:message}"
      }
    },
    {
      "type": "status-remapper",
      "name": "Use level as status",
      "is_enabled": true,
      "sources": [
        "level"
      ]
    },
    {
      "type": "date-remapper",
      "name": "Use parsed timestamp",
      "is_enabled": true,
      "sources": [
        "timestamp"
      ]
    }
  ]
}
```

Pipeline の作成/並べ替えは、一致する log の processing を変更します。
正しい site、scoped API permission、既存 pipeline ownership の下で設定してください。
この audit 中に pipeline request は送信されませんでした。

### Trace-log correlation と MDC ownership

可能な場合は対応する automatic log injection を使用し、structured log では trace/span ID を string として保持してください。
正しい service/env/version、timestamp、parsing、利用可能な trace data も必要です。2 つの ID field だけでは correlation を保証しません。
process が instrument されていない場合、有用な active trace ID はありません。

SLF4J MDC を明示的に管理する application では、この helper は成功時と失敗時に caller の
**以前の context 全体**を復元します。以前の無条件の `MDC.clear()` は無関係の caller field を失わせていました。
これは synchronous helper であり、async context propagation mechanism や完全な servlet filter ではありません。

```java
import java.util.Map;
import java.util.function.Supplier;
import datadog.trace.api.CorrelationIdentifier;
import org.slf4j.MDC;

public final class TraceLogContext {
    private TraceLogContext() {}

    public static <T> T withTraceContext(Supplier<T> handler) {
        Map<String, String> previous = MDC.getCopyOfContextMap();
        try {
            MDC.put("dd.trace_id", CorrelationIdentifier.getTraceId());
            MDC.put("dd.span_id", CorrelationIdentifier.getSpanId());
            return handler.get();
        } finally {
            if (previous == null) {
                MDC.clear();
            } else {
                MDC.setContextMap(previous);
            }
        }
    }
}
```

これには `dd-trace-api` と application に互換性のある SLF4J API/provider が必要です。
logging pattern または JSON encoder は MDC value を含める必要があります。servlet API、import、
checked-exception contract を確認せずに servlet example をコピーしないでください。

## Dashboard と Alert

### Dashboard request construction

この helper は `datadog-api-client==2.60.0` を使用して request body を構築します。cluster と
namespace の template variable は実際に query から参照されます。host widget は percent metric を使用し、
pod widget は memory byte と namespace filter を使用します。選択した data が実際に grouping tag を持つことを確認してください。

```python
from datadog_api_client.v1.model.dashboard import Dashboard
from datadog_api_client.v1.model.dashboard_layout_type import DashboardLayoutType


def build_dashboard(cluster_name):
    return Dashboard(
        title="EKS observability example",
        layout_type=DashboardLayoutType.ORDERED,
        widgets=[
            {"definition": {
                "type": "timeseries",
                "title": "CPU idle by host (%)",
                "requests": [{"q": "avg:system.cpu.idle{$cluster} by {host}", "display_type": "line"}],
            }},
            {"definition": {
                "type": "toplist",
                "title": "Top 10 pod memory series by mean (bytes)",
                "requests": [{"q": "top(sum:kubernetes.memory.usage{$cluster,$namespace} by {pod_name,kube_namespace}, 10, 'mean', 'desc')"}],
            }},
        ],
        template_variables=[
            {"name": "cluster", "prefix": "kube_cluster_name", "default": cluster_name},
            {"name": "namespace", "prefix": "kube_namespace", "default": "*"},
        ],
    )
```

caller は正しく設定された `ApiClient` を提供し、意図した dashboard を作成または更新するために
`DashboardsApi` を使用します。返された ID を記録/reconcile してください。title による作成の繰り返しは duplicate を作成する場合があります。
site と scoped automation credentials は node Agent API key とは別です。この audit では dashboard API を呼び出していません。

### Monitor query と unit

設定済みの Datadog Terraform provider と project version constraint/lock file を使用してください。
これらは resource fragment であり、完全な provider/credential setup ではありません。threshold は例です。
実際の metric unit、tag、window、application objective を確認してください。最初の monitor は、nanocore を
80 と比較して結果を「CPU percent」と呼ぶのではなく、idle percent を直接評価します。

```hcl
# Fragments for a configured, version-pinned Datadog Terraform provider.
# Replace notification destinations with approved, tested destinations.
resource "datadog_monitor" "low_cpu_idle" {
  name    = "Low CPU idle on EKS nodes"
  type    = "metric alert"
  message = "CPU idle on {{host.name}} is {{value}}%. Inspect the host and collection health."
  query   = "avg(last_5m):avg:system.cpu.idle{kube_cluster_name:my-eks-cluster} by {host} < 20"
  monitor_thresholds {
    warning  = 30
    critical = 20
  }
  require_full_window = false
  notify_no_data      = false
  tags               = ["env:demo", "team:platform"]
}

resource "datadog_monitor" "restart_total" {
  name    = "Container restart total exceeds example threshold"
  type    = "metric alert"
  message = "Inspect {{pod_name.name}} / {{kube_container_name.name}}. This is a restart total, not a count of new restarts in five minutes."
  query   = "max(last_5m):max:kubernetes_state.container.restarts{kube_cluster_name:my-eks-cluster} by {pod_name,kube_namespace,kube_container_name} > 3"
  monitor_thresholds {
    warning  = 2
    critical = 3
  }
  require_full_window = false
  notify_no_data      = false
  tags               = ["env:demo", "team:platform"]
}

resource "datadog_monitor" "request_error_rate" {
  name    = "High request error ratio"
  type    = "metric alert"
  message = "Error ratio for {{service.name}} is {{value}}%. Check traffic volume and the reporting path."
  query   = "sum(last_5m):sum:my_app.requests.error{env:demo} by {service}.as_count() / sum:my_app.requests.total{env:demo} by {service}.as_count() * 100 > 5"
  monitor_thresholds {
    warning  = 2
    critical = 5
  }
  require_full_window = false
  notify_no_data      = false
  tags               = ["env:demo", "type:application"]
}
```

restart gauge は**累計**です。特に reset、Pod replacement、不均等な sampling がある場合、
2 つの window で繰り返された gauge sample の合計を比較しても、新しい restart を確実に count できません。
recent-restart monitor には検証済みの delta/reset design が必要です。この例は代わりに total に対して明示的に alert します。

error monitor は error/good request に明示的なゼロ値を含め、`emit_batch` が出力する 3 つの counter を使用します。
`.as_count()` evaluation では、time aggregation は division **より前に**行われます。各 time bucket の ratio の合計ではなく、
sum(errors)/sum(total) です。この path では sum aggregator を使用してください。

zero traffic、missing telemetry、真に error-free な traffic は異なります。
minimum traffic/collection-health condition を定義し、monitor の no-data behavior を検証してください。
`notify_no_data: false` は health を確立しません。これらの fragment で missing data に通知しないだけです。

built-in APM metric には、選択した integration が生成する実際の `trace.<operation>.hits/errors` 名と
tag を使用してください。Java、Python、その他の integration がすべて `trace.http.request.*` を出力するわけではありません。
Trace analytics、生成された trace metric、custom DogStatsD metric は異なる source です。

### Watchdog と notification delivery

Watchdog は、すべての threshold を手動で選ばなくても、検出された anomaly/insight を示せます。
insight は notification が配信された証明ではありません。対応する Watchdog/monitor workflow を使用し、
意図した site で event source、product availability、notification routing を検証してください。

以下の event-monitor fragment は、その組織に `source:watchdog` に一致する実際の event が存在することを前提とします。
`story_category` group tag を作り出すことも、すべての Watchdog result がこの stream に現れることを保証することもありません。
notification を有効化する前に、実際の event に対して filter を検証してください。

```hcl
resource "datadog_monitor" "watchdog_events" {
  name    = "Review matching Watchdog events"
  type    = "event-v2 alert"
  message = "Review the matching Watchdog event and affected services. Add an approved notification destination."
  query   = "events(\"source:watchdog\").rollup(\"count\").last(\"5m\") > 0"
  tags    = ["env:demo", "type:watchdog"]
}
```

### SLO request construction

metric-based SLO には、明確に定義された good/total count が必要です。以下の helper は上記の明示的な counter を使用します。
「Good」は application の SLI policy と一致する必要があります。HTTP 2xx のみを count することは普遍的な availability 定義ではありません。
absence を 100% success として扱うのではなく、zero-traffic と missing-data behavior を検証してください。

```python
from datadog_api_client.v1.model.service_level_objective_request import ServiceLevelObjectiveRequest


def build_success_slo():
    return ServiceLevelObjectiveRequest(
        name="Orders successful-request SLO",
        type="metric",
        description="Successful requests divided by all reported requests",
        query={
            "numerator": "sum:my_app.requests.good{env:demo,service:orders}.as_count()",
            "denominator": "sum:my_app.requests.total{env:demo,service:orders}.as_count()",
        },
        thresholds=[{"timeframe": "30d", "target": 99.9, "warning": 99.95}],
        tags=["env:demo", "service:orders"],
    )
```

これは request を構築するものであり、live SLO ではありません。設定済み caller は、ownership、data、permission が
検証された後で `ServiceLevelObjectivesApi.create_slo` にこれを渡すことができます。Datadog は monitor-based と
time-slice SLO もサポートします。gauge/restart total を good-event count に無理に当てはめるのではなく、
SLI に一致する model を選択してください。

## Cost Structure

### 実際の product と contract unit を使用する

| Component | 見積もりの input |
| --- | --- |
| Infrastructure | Billable host/container または該当する platform model、plan、commitment term |
| APM | Billable APM host と選択した plan/model、included allotment、ingested/indexed span |
| Logs | Ingested volume と indexing/retention/search/archive の選択 |
| Custom metrics / distributions | Distinct metric/tag combination、有効な aggregation、該当する included volume |
| Additional products | Profiling、network/security、serverless、その他の有効な product charge |

すべての product を普遍的な Free/Pro/Enterprise table に統合しないでください。pricing
page は product、annual/on-demand term、attached と standalone の offering を区別しています。
infrastructure metric、searchable trace、indexed log の retention は、共通の「15-month」設定ではありません。

以前の 100-node の例では、**50 service は 50 APM host を意味しません**。
host-priced agreement では、まず実際の billable Infrastructure および APM host count を決定してください。
30 日間で 100 GB/day の場合、log ingestion は 3,000 GB ですが、ingestion だけが log bill の総額ではありません。

```text
Estimated cost =
  billable infrastructure units × applicable rate
  + billable APM units × applicable rate
  + ingested/indexed span overages under the contract
  + 3,000 GB × applicable log-ingestion rate
  + indexed events/retention/search/archive charges
  + custom-metric and other enabled-product charges
```

以前の約 $3,350 の合計は、APM unit の不一致と billable dimension の欠落がありました。
これは測定済み production bill ではありませんでした。その見積もりを budget guarantee として扱わず、
現在の site/product quote と測定済み usage を使用してください。

### metrics、logs、trace の control は異なることを行う

- `dogstatsd.nonLocalTraffic` は receiver reachability を制御します。custom-metric
  quota ではありません。receiver を閉じると単に telemetry を失う場合があります。
- `ignoreAutoConfig` は選択した automatic check を無効化します。container exclusion filter は
  container を選択します。どちらも汎用的な tag-cardinality limiter ではありません。
- collection owner で許可された metric と tag value をレビューしてください。origin
  tag cardinality を変更すると利用可能な grouping tag が変わる場合があるため、monitor/SLO を再確認してください。
- source-side log exclusion は選択した record の送信を回避します。index exclusion はその後に発生し、
  ingestion cost を消去しません。incident evidence と failure を保持してください。結果にかかわらず
  すべての health-check line を drop しないでください。
- sampling と indexing/retention は別です。`DD_TRACE_SAMPLE_RATE` または sampling
  rule は library/version と matching scope に依存します。文書化された Python の
  `DD_TRACE_RATE_LIMIT` は process ごとであり、設定済み sampling rule/rate と共に適用されます。
  cluster-wide または dollar cap ではありません。10% trace rate は Datadog bill 全体の 90% 削減を意味しません。

## Best Practices

一貫した service/env/version label と bounded tag を使用し、API-key ingestion と
application-key automation permission を分離してください。すべての log、process argument、profile を収集する前に、
application capture と secret/redaction path をレビューしてください。collector queue/drop を監視し、
filter の変更後に実際の output を検証してください。

operating team と alert severity、ownership、response target について合意してください。
runbook の P1/P2 label は operational policy であり、単体の Datadog resource definition ではありません。
実際の destination、missing data、recovery notification を test してください。
sample に現れるという理由だけで threshold を選ぶのではなく、文書化された SLI/SLO と traffic context を使用してください。

## Troubleshooting

installation owner、実際の Pod/container 名、意図した site から始めてください。
API-key Secret reference、Agent/Cluster Agent health、Kubelet/RBAC access、
scrape configuration、queued/dropped telemetry を確認してください。この release で render された node
Agent Pod には `agent` と `trace-agent` container があります。以前の `app=datadog` selector は、
現在の label を確認する代わりとして信頼できません。

```bash
kubectl get pods -n datadog \
  -l app.kubernetes.io/instance=datadog,app.kubernetes.io/component=agent -o wide

# Select the actual node Agent pod after inspecting the list.
: "${DD_AGENT_POD:?Set the node Agent pod name}"
kubectl exec -n datadog "$DD_AGENT_POD" -c agent -- agent status
kubectl logs -n datadog "$DD_AGENT_POD" -c agent --tail=100
kubectl logs -n datadog "$DD_AGENT_POD" -c trace-agent --tail=100

# Check new application pods without dumping credentials/environment values.
: "${APP_NAMESPACE:?Set the application namespace}"
: "${APP_POD:?Set the application pod name}"
kubectl get pod -n "$APP_NAMESPACE" "$APP_POD" \
  -o jsonpath='{.spec.initContainers[*].image}'
kubectl get pod -n "$APP_NAMESPACE" "$APP_POD" \
  -o jsonpath='{range .spec.containers[*]}{.name}{": "}{.env[*].name}{"\n"}{end}'

# Create a local diagnostic archive only; review it before any authorized sharing.
kubectl exec -n datadog "$DD_AGENT_POD" -c agent -- agent flare --local
```

trace については、実際の library injection/startup、socket または host endpoint、
permission、一貫した tag を確認してください。TCP check の成功は UDS path を検証したり、
trace payload が受理された証明にはなりません。`env | grep DD_` は使用しないでください。
API/application key や proxy credential が開示される可能性があります。

log については、実際の annotation/container identifier と file access、次に collection exclusion、
parsing、index filter を確認してください。`agent configcheck`、status、log、archive は configuration
または application data を露出する可能性があります。共有する前に output を確認し、redact してください。

`agent flare --local` は確認用の local bundle を作成します。upload または remote flare
collection は、別の承認された support action です。built-in redaction は有用ですが、
application が収集した data について archive をレビューする代わりにはなりません。

## Validation scope

この audit では chart rendering と official schema/source inspection、local
DogStatsD Unix datagram、Python 3.12 上で export/telemetry を無効化した ddtrace 4.14.0 manual span、
Java 17 向けの dd-trace-api 1.66.0 compilation と synchronous MDC test、API client 2.60.0 request
model/serialization を使用しました。これらの check は Datadog tenant の呼び出し、EKS への install、
admission webhook の実行、SaaS への trace/log 送信、dashboard/monitor/
SLO の作成、コスト測定を行っていません。

Monitor query の意味は文書化された metric unit と aggregation rule に対して確認しました。
Datadog query engine または Terraform provider plan は実行していません。Grok request schema は live parsing とは別です。
application、credential、traffic、runtime support、destination ownership は deployment prerequisite のままです。

## 参考資料

- [Kubernetes installation と version prerequisite](https://docs.datadoghq.com/containers/kubernetes/installation.md)
- [Helm chart 3.244.0](https://github.com/DataDog/helm-charts/releases/tag/datadog-3.244.0)
- [Agent 7.83.1 release](https://github.com/DataDog/datadog-agent/releases/tag/7.83.1)
- [Kubernetes distribution](https://docs.datadoghq.com/containers/kubernetes/distributions.md)
- [Kubelet metric](https://docs.datadoghq.com/integrations/kubelet.md)
- [Kubernetes State Metrics Core](https://docs.datadoghq.com/integrations/kubernetes_state_core.md)
- [System metric](https://docs.datadoghq.com/integrations/system.md)
- [AWS account integration](https://docs.datadoghq.com/integrations/amazon-web-services.md)
- [Admission Controller](https://docs.datadoghq.com/containers/cluster_agent/admission_controller.md)
- [Local SDK injection](https://docs.datadoghq.com/tracing/guide/local_sdk_injection.md)
- [Kubernetes 上の OpenMetrics](https://docs.datadoghq.com/containers/kubernetes/prometheus.md)
- [DogStatsD UDS](https://docs.datadoghq.com/extend/dogstatsd/unix_socket.md)
- [Python tracing configuration](https://docs.datadoghq.com/tracing/trace_collection/library_config/python.md)
- [Custom instrumentation](https://docs.datadoghq.com/tracing/trace_collection/custom_instrumentation/server-side.md)
- [Log parsing](https://docs.datadoghq.com/logs/log_configuration/parsing.md)
- [as_count monitor evaluation](https://docs.datadoghq.com/monitors/guide/as-count-in-monitor-evaluations.md)
- [Metric-based SLO](https://docs.datadoghq.com/service_level_objectives/metric.md)
- [Datadog pricing と billing FAQ](https://www.datadoghq.com/pricing/)
- [Agent flare の処理](https://docs.datadoghq.com/agent/troubleshooting/send_a_flare.md)

[クイズ](../../quizzes/observability/metrics/05-datadog-quiz.md)
