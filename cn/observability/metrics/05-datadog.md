# Datadog

> **最后更新**: September 13, 2026
> Helm chart 3.244.0；匹配的 Agent/Cluster Agent 7.83.1。
> 下文说明配置、SDK 和本地验证的限制；未修改任何 Datadog tenant。

## 简介

Datadog 提供 SaaS 可观测性后端。团队仍需负责 collector、身份、网络访问、instrumentation、数据披露、保留、monitor 和成本。
Infrastructure Monitoring、APM、profiling、logs 及其他产品具有不同的授权和计费维度；安装 Agent 并不包含每一种产品。

| 主题 | Datadog | CloudWatch | 自管 Prometheus / Grafana |
| --- | --- | --- | --- |
| 后端 | Datadog SaaS，且可用性因 site 而异 | AWS 托管服务 | 自行运营的存储、查询和可视化 |
| 采集 | Agent/Cluster Agent、库和受支持的 OTel 路径 | AWS service metrics、agents/SDKs/OTLP | Exporters、scraping、agents 和 remote write |
| APM/logs | 选择并配置所需产品 | Application Signals、tracing 和 Logs integrations | 配置相关后端和 collectors |
| 运维 | collector/配置和应用程序责任仍由团队承担 | 采集/配置和响应责任仍由团队承担 | 后端和采集责任仍由团队承担 |
| 成本 | Host 及其他特定产品的使用量/保留单位 | Metric/observation/OTLP/log/query/alarm 单位 | 基础设施和运营投入 |

为组织及其凭据选择正确的 Datadog **site**；
API endpoints、数据驻留、可用产品和定价条款在不同 site 之间不可互换。使用
integration catalogue，而不是声称固定的 integration 数量，或给出通用的“简单/高级/便宜”排名。

## EKS integration 架构

| 组件 | 职责 / 边界 |
| --- | --- |
| Node Agent | Host/container checks；通常作为 DaemonSet 运行在受支持的 EC2 nodes 上 |
| Cluster Agent | 共享 Kubernetes metadata/checks、event 协调，以及可选的 admission/external-metric 功能 |
| Trace Agent | 接收应用程序 trace payloads 并转发 |
| Process collection / system-probe | 可选的 process/network/security 功能，具有各自的 OS、权限和产品要求 |
| Admission Controller | 注入连接设置，并在配置时将受支持的 client libraries 注入新 pods |

应用程序 instrumentation 会生成 traces/profiles；仅有 Agent listener 或 pod
label 并不能证明已经完成 instrumentation。Cluster Agent 不是常规的
application-log 或 trace forwarding 路径。

本章的安装目标是 **Linux EC2-backed EKS nodes**。EKS Fargate
使用文档规定的每 Pod/sidecar 采集模型，而不是此 host DaemonSet。
UDS 仅限于本地 host，且不受 Windows 支持。Windows、Bottlerocket、
Auto Mode 和混合计算环境需要其 distribution/feature-specific 设置及
受支持的 host 访问。不要禁用 TLS verification，也不要声称所有 eBPF/process
功能在任何环境都能运行。

Datadog 记录了 Agent 和 Cluster Agent 7.67+ 与 Kubernetes 1.33+ 的兼容性，
以支持 `AllocatedResources`，并建议使二者的版本匹配。此类最低功能要求
并非当前 EKS support matrix。

概览展示了可能的采集路径。Traces/profiles 需要 application instrumentation 和选定的产品；必须配置 Watchdog notification routing。

![Datadog node Agent telemetry 和 Cluster Agent metadata 到达配置的 SaaS 产品。](../../.gitbook/assets/en-observability-metrics-05-datadog-1.png)

[交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-metrics-05-datadog-1.html)

## Datadog Agent 安装

Datadog 建议使用其 Operator 进行更高层级的 lifecycle 配置，也支持通过 Helm 安装。此示例通过
**Datadog Agent Helm chart** 管理 node/Cluster Agents。Chart 3.244.0 捆绑了可选的 Operator dependency；
`datadog.operator.enabled: false` 会使该额外 controller 不包含在此示例中。
这并不意味着 Operator 已过时。

该 chart 默认使用 Agent/Cluster Agent 7.82.3。此示例显式固定两者为
**7.83.1**，以及已验证的 image-index digests。该 release 包含 network-test
billing、containerd snapshot cleanup 和 Cluster Agent leader-lock shutdown 修复。
Agent/Cluster Agent image indexes 包含 Linux amd64/arm64。成功的
template render 并非 Kubernetes deployment 或 runtime compatibility 测试。

### 凭据和安装所有权

基础 Agent ingestion 需要与 Agent 位于同一 namespace 的 API key。
application key 是 external metrics provider 等 API read/control 功能所需；
仅安装基础 Agent 不需要它。仅当所选功能需要时，使用 scoped application key。

将凭据保存在获批准的 Secret workflow 中。以下文件命令可避免旧版未加引号的
`<YOUR_API_KEY>` shell-redirection 问题，以及在 process arguments 中暴露 key。根据凭据
workflow 保护并删除临时 key 文件。Kubernetes Secrets 也需要适当的访问和加密控制。
不要在由其他 release 或 controller 所有的资源上运行此安装。

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

### 已审核的 values

将以下内容保存为 `datadog-values.yaml`。Logs 通过 container
configuration 选择性启用，APM/DogStatsD 使用 UDS，且此处未启用集群范围的 automatic library injection、
external HPA metrics、discovery network statistics 和可选的 process/network
collection。
应用程序 namespace 应与 Agent namespace 分开；SSI 不会对 Agent 自身 namespace 中的 pods 进行 instrumentation。

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

`processAgent.enabled` 已弃用；请使用各个 collection 选项。
该 chart 会在适用时挂载 `/etc/passwd`，因此不要添加重复的
手动 `passwd` volumes/mounts。Resource overrides 按组件设置，例如
`agents.containers.agent.resources`；应在负载下对实际 render 的 containers 进行 sizing。
两个 Cluster Agent replicas 不能替代 placement、disruption 和 failure testing。

原顶层的 `kubeStateMetricsEnabled` 和 `prometheus.enabled` 条目
并不会配置所声称的 integrations。旧版 KSM 选项嵌套在
`datadog` 下；该示例使用 `datadog.kubeStateMetricsCore.enabled`，并避免
重复的旧版 collection。显式 Datadog Autodiscovery checks 与开启 annotation-wide
`prometheusScrape` 是不同的配置。

`datadog.profiling.enabled` **有效**。它会向符合条件的 pods 注入 `DD_PROFILING_ENABLED`，
并需要已安装的 client libraries 和 Cluster Agent 7.57+。
它不会向任意未进行 instrumentation 的应用程序安装 profiler。
请有意识地选择其 `null`/`false`/`auto`/`true` 行为。同样，启用
external HPA metrics 需要其 application key、API permissions、service/CRDs
和实际的 metric 可用性；network monitoring 需要受支持的 system-probe access。

### AWS account integration 是单独的路径

SaaS AWS account integration 使用经授权的 cross-account role 和
Datadog 提供的 external ID，以及所选 integrations 需要的 permissions。
挂载到 node Agent SA 的任意 IRSA role 并不会配置该 SaaS
integration。普通 Kubernetes Agent collection 不需要此处先前展示的宽泛
CloudWatch/EC2/tag policy。

仅在确实调用 AWS 的 Agent/check 上使用 Pod Identity 或 IRSA，并配置其
特定 role、trust 和 permissions。解析 **rendered** service-account name；
为猜测的 `datadog-agent` SA 创建 IAM association 不会绑定 Helm release 使用的
另一个 SA。绝不要将本地 STS caller check 当作 workload identity 的证明。

## Infrastructure Monitoring

### 检查 metric 的 collector、unit 和 tags

| Metric / source | 含义 |
| --- | --- |
| `system.cpu.idle` / System check | CPU idle **percent**；适合基于百分比的 node threshold |
| `system.mem.total`, `system.mem.used`, `system.mem.free` | Memory measurements；free 与 usable/reclaimable memory 不可互换 |
| `kubernetes.cpu.usage.total` / Kubelet | **Nanocores**，不是 percent；一个 core 是 1,000,000,000 nanocores |
| `kubernetes.memory.usage`, `kubernetes.memory.limits` | Bytes；usage 与 limit 的比较需要匹配相同 entity/tag set |
| `kubernetes.pods.running`, `kubernetes.containers.restarts` | 有效的 Kubelet gauges：运行中的 pods 和累计 container restarts |
| `kubernetes_state.deployment.replicas_available`, `kubernetes_state.deployment.replicas_desired` | Kubernetes State Metrics Core Deployment state |
| `kubernetes_state.pod.status_phase`, `kubernetes_state.service.count` | Pod phase/service inventory；检查其文档化 grouping tags |
| `kubernetes_state.container.restarts` | State Core 的 restart gauge，带有 namespace/pod/container tags |

旧版 Kubernetes integration、Kubelet check 和 State Core 具有不同的
catalogues。某个 catalogue 中没有的 metric 不一定已从 Agent 中移除。
不要盲目重命名有效的 Kubelet metrics。Filesystem/network availability
和 rate units 取决于 collector/runtime；请阅读该 metric 的实际定义。

对此 Kubernetes 安装使用标准 `kube_cluster_name` tag，并在 grouping 前检查
真实 metric tags。以 cluster 为中心的 State Core metrics 不一定携带
`host` tag。`cluster_name` 和 `kube_cluster_name` 不可互换。
将原始 nanocore 值与 80 比较并不代表 80% CPU。

### OpenMetrics Autodiscovery

将以下 **metadata fragment** 合并到 container 名为
`app`、且在 port 9464 提供 gauge `queue_depth` 的 workload 中。它不会创建该
应用程序或 endpoint。annotation 的 container identifier 必须匹配。
如有需要，请保护 endpoint 并配置 TLS/authentication。

```yaml
metadata:
  annotations:
    ad.datadoghq.com/app.checks: "{\n  \"openmetrics\": {\n    \"init_config\": {},\n\
      \    \"instances\": [\n      {\n        \"openmetrics_endpoint\": \"http://%%host%%:9464/metrics\"\
      ,\n        \"namespace\": \"my_app\",\n        \"metrics\": [\n          {\n\
      \            \"queue_depth\": \"queue_depth\"\n          }\n        ]\n    \
      \  }\n    ]\n  }\n}"
```

当前 `openmetrics` check 使用 `openmetrics_endpoint`。这些 Datadog
Autodiscovery annotations 不需要单独的 Prometheus server 或 chart 的广泛
`prometheusScrape` discovery。限制所选 metrics/labels。
对于 counters 和 histograms，请验证 name normalization、发出的 `.count`/bucket
series 以及 check-version behavior，而不要假定 Prometheus name
也是最终的 Datadog name。

### DogStatsD：使用应用程序可访问的 endpoint

应用程序 pod 的 `localhost` 不是 node Agent。该 Linux 示例使用
host-local UDS directory。Admission Controller 的 `socket` mode 可以注入
`DD_DOGSTATSD_URL`、`DD_TRACE_AGENT_URL` 和 volume；否则请显式配置匹配的
mounts 和 permissions。Pod-specific `admission.datadoghq.com/config.mode`
是 **label**，不是 annotation。挂载父目录，以便在 Agent restart 后仍可看到
socket replacement。

该 Python helper 已使用 `datadog==0.53.0` 检查。向 `socket_path` 传递实际 filesystem
path，例如 `/var/run/datadog/dsd.socket`；其他 SDKs/environment settings 使用的 `unix://` URL
不是相同的 argument format。以实际 interval counts 调用 `emit_batch`，
包括为零的 good/error 值。

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

该 Go helper 使用 datadog-go/v5。使用 `WithNamespace("my_app.")`
和相同的 `env:demo,service:orders` tags 创建 client。检查 constructor、send 和 close
errors；不要丢弃 `statsd.New` error。该 helper 不会关闭 caller 提供的 shared
client。

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

| DogStatsD type | 解释 |
| --- | --- |
| Counter | Interval count；Datadog 可能将其存储为 rate。`.as_count()` 会为 query window 重建 counts |
| Gauge | queue depth 等 snapshot；对 snapshots 求和不是 processed-request count |
| Histogram | 由接收的 Agent 聚合；对每 host percentiles 求平均不会产生全局 percentile |
| Distribution | 支持 backend distribution aggregation；检查启用的 percentiles、tags 和 billing |
| Service check | 来自真实 health check 的状态：0 OK、1 warning、2 critical、3 unknown |

本地 datagram delivery 不确认 SaaS ingestion。UDP 可能丢包；还需监控
UDS/client buffering 和 Agent queues。示例 helper 不启用 DogStatsD client telemetry，
因此请为 deployment 选择单独的 collection-health signal。Counter retries/duplicate sends
不是 exactly-once business ledger。

### 基于文件的 Autodiscovery 配置

对于 Helm-owned configuration，`datadog.confd` 会创建并挂载 check files。
仅仅存在名为 `datadog-checks` 的 standalone ConfigMap 并不会被自动发现。
以下 NGINX fragment 需要匹配的 image identity 以及已配置、已授权的 `stub_status` endpoint。

```yaml
datadog:
  confd:
    nginx.yaml: "ad_identifiers:\n  - nginx\ninit_config: {}\ninstances:\n  - nginx_status_url:\
      \ http://%%host%%:80/nginx_status\n"
```

authenticated Redis check 还需要正确的 port/TLS 和 credential delivery。
`%%env_REDIS_PASSWORD%%` 读取的是 **Agent 的** environment，而不是 Redis
application pod 的 environment。优先使用已配置的 Datadog secret backend 或具有所需特定
permissions 的受保护文件 delivery；不要在公开 check examples 中暴露 passwords，
也不要只为 discovery 授予 cluster-wide Secret reads。

## APM 和 Distributed Tracing

### 本地 SDK injection 和 SSI 是明确的选择

admission opt-in label 允许 mutation/connection-setting injection。要安装
a tracing library，请配置 SSI targets 或受支持的 language/version annotation。
仅有该 label 并不能证明已安装 SDK 或 traces 已到达 Datadog。
Java/Python/Node.js local injection 需要 Cluster Agent 7.40+；.NET/Ruby 需要
7.44+。当前 7.83.1 还会将 `kube-system` 和自身 namespace 排除在 injection 之外。

对于受控的 Java 示例，请将以下 **pod-template fragment** 合并到 application namespace
中的现有 Deployment，保留其 selector、containers 和 security settings。它不是可以单独 apply 的完整 Deployment。
Java init image `gcr.io/datadoghq/dd-lib-java-init:v1.66.0` 已针对 Linux amd64/arm64 验证。
请验证实际应用程序的 JVM/framework/image compatibility。

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

`tags.datadoghq.com/*` labels 提供统一的 service/environment/version tagging。
不要仅将 label 放在 Deployment metadata 上并期待其 pods 继承。
injection 发生在 **新 pods** 被 admission 时。确认注入的 init
containers、library files、UDS mounts/permissions 和非 secret connectivity
settings，然后验证实际 traffic/traces。Namespace exclusions、webhook failures、
security policies 和不受支持的 images 都可能阻止 instrumentation。

Cluster-wide SSI 是通过 `datadog.apm.instrumentation` 配置的替代方案，
其中包含已审核的 namespace/pod targets 和 library versions。
避免无意中组合 manual 和 injected tracers：injected library 可能优先于手动安装的 library。
Profiler enablement 仍需要受支持的 client library 及其自身的 product/runtime conditions。

### 手动 Java instrumentation

在启动应用程序 JVM 时，使用分阶段、版本化的 `dd-java-agent.jar`，或使用上面经过
验证的 injection 路径。仅添加 `dd-trace-api` 会提供 annotation/API 的访问；它**不会**启动 runtime bytecode instrumentation。
以下 Maven dependency 和 Java source 是独立文件。

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

handler 表示由 caller 提供的 application code。使用有界的
operation/resource names。旧示例中的每订单/customer identifier tags
对此演示并非必要，且可能造成 disclosure/cardinality risks。
Manual span APIs 需要相应受支持的 bridge/library；不要向只有 annotation API 的项目添加
OpenTracing imports。

### 手动 Python instrumentation

对此已检查的 4.14.0 示例，使用当前的 `ddtrace.trace` import。将
dependency declaration 保留在 `requirements.txt` 中，而不是 Python code block 内。
对于 framework auto-instrumentation，请在 application imports 之前遵循所选的 `ddtrace-run`/SSI setup；
不要假定此 helper 会 patch 整个 framework。

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

等效的 `tracer.wrap` decorator 可用于 method tracing。handler 抛出的 exceptions
必须传播；记录 span 不是 application retry 或 success guarantee。
在受支持的 HTTP/message integrations 中使用正确的 service/env/version tags 和 context propagation。
Service maps 来自观察到的 instrumented relationships，而非仅来自任意 `DD_TAGS`。

默认不要 tag 原始 customer/order identifiers、tokens 或 request bodies。
检查实际应用程序的 instrumentation capture、error messages 和 sampling/redaction rules。
Auto-instrumentation 不保证完整移除 PII。

## Log Management

### 有意选择 collection 和 parsing

安装启用了 log collection，但保持 `containerCollectAll: false`。
将此 metadata 合并到 container 名为 `app` 的 pod template 中。
multiline rule 适用于**以日期开头的纯文本 Java records**。
它不是通用 JSON-log parser。Container runtime framing 和 application
message parsing 是独立阶段；请验证实际收集的 records。

```yaml
metadata:
  annotations:
    ad.datadoghq.com/app.logs: "[\n  {\n    \"source\": \"java\",\n    \"service\"\
      : \"orders\",\n    \"log_processing_rules\": [\n      {\n        \"type\": \"\
      multi_line\",\n        \"name\": \"java_timestamp_start\",\n        \"pattern\"\
      : \"^\\\\d{4}-\\\\d{2}-\\\\d{2}\"\n      }\n    ]\n  }\n]"
```

对于每行一个 JSON event 的应用程序，请使用受支持的 JSON path，而不是
用此 rule 合并不相关的 JSON events。File access、runtime paths、annotation
matching、exclusion settings 和 backend pipeline filters 都会影响 collection。
使用匹配的 application 和被排除的 application 一同检查 selective collection。

### Pipeline request 结构

此 request 使用实际 API fields **`match_rules` 和 `support_rules`**。
旧 camelCase fields 并非 Logs API model。示例 message 定义预期的 line format；
请使用应用程序实际的 format/timezone，并测试 unmatched/multiline/error cases。
有效的 request model 并不能证明 Datadog tenant 中的 Grok parsing 或 ingestion/indexing。

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

创建/重新排序 Pipeline 会改变匹配 logs 的 processing。请在正确的 site、
scoped API permissions 和现有 pipeline ownership 下进行配置。
此次审计期间未发送 pipeline request。

### Trace-log correlation 和 MDC ownership

尽可能使用受支持的 automatic log injection，并在 structured logs 中将 trace/span IDs
保留为 strings。还需要正确的 service/env/version、timestamps、parsing 和可用 trace data；
仅有两个 ID fields 并不能保证 correlation。当 process 未进行 instrumentation 时，不存在有用的 active trace ID。

对于显式管理 SLF4J MDC 的应用程序，此 helper 会在 success 和 failure 时恢复 caller 的
**整个先前 context**。旧的无条件 `MDC.clear()` 会丢失无关的 caller fields。
它是 synchronous helper，不是 async context propagation mechanism 或完整 servlet filter。

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

它需要 `dd-trace-api` 和应用程序兼容的 SLF4J API/provider。
logging pattern 或 JSON encoder 必须包含 MDC values。不要复制 servlet example，
除非同时具备 servlet API、imports 和 checked-exception contract。

## Dashboards 和 Alerts

### Dashboard request 构造

此 helper 使用 `datadog-api-client==2.60.0` 构造 request body。cluster
和 namespace template variables 实际被其 queries 引用。host
widget 使用 percent metric；pod widget 使用 memory bytes 及其 namespace
filter。检查所选 data 确实具有 grouping tags。

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

caller 提供正确配置的 `ApiClient`，并使用 `DashboardsApi`
创建或更新目标 dashboard。记录/协调其返回的 ID；按标题重复创建可能产生 duplicates。
site 和 scoped automation credentials 与 node Agent API key 相互独立。此次审计未调用 dashboard API。

### Monitor queries 和 units

使用已配置的 Datadog Terraform provider 以及 project version constraints/lock file。
这些是 resource fragments，而非完整的 provider/credential setup。Thresholds
仅为示例；请检查真实 metric units、tags、windows 和 application objectives。
第一个 monitor 直接评估 idle percent，而不是将 nanocores 与 80 比较并将结果称为“CPU percent”。

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

restart gauge 是 **total**。比较两个 windows 中重复 gauge samples 的 sums
无法可靠计算新的 restarts，尤其是在 resets、replacement
pods 或不等采样时。recent-restart monitor 需要经过验证的 delta/reset
design。此示例明确对 total 发出 alert。

error monitor 使用 `emit_batch` 发出的三个 counters，
包括 errors/good requests 的显式零值。对于 `.as_count()` evaluation，time
aggregation 发生在 **division 之前**：sum(errors)/sum(total)，而不是每个 time bucket's
ratio 的 sum。通过此路径使用 sum aggregator。

零 traffic、缺失 telemetry 和真正无 errors 的 traffic 是不同情况。
定义最小 traffic/collection-health conditions，并验证 monitor 的
no-data behavior。`notify_no_data: false` 不会建立 health；它只是不会在这些 fragments 中对 missing data 发出通知。

对于内置 APM metrics，使用所选 integration 生成的实际 `trace.<operation>.hits/errors` names 和
tags。Java、Python 和其他 integrations 并不都会发出 `trace.http.request.*`。
Trace analytics、生成的 trace metrics 和 custom DogStatsD metrics 是不同 sources。

### Watchdog 和 notification delivery

Watchdog 可在无需手动选择每个 threshold 的情况下呈现检测到的 anomalies/insights。
insight 并不能证明 notification 已送达。使用受支持的 Watchdog/monitor workflow，
并在目标 site 中验证 event source、product availability 和 notification routing。

以下 event-monitor fragment 假定该组织中存在与
`source:watchdog` 匹配的实际 events。它不会虚构 `story_category`
group tag，也不保证每个 Watchdog result 都出现在此 stream 中。启用 notifications 前，
请针对真实 events 验证 filter。

```hcl
resource "datadog_monitor" "watchdog_events" {
  name    = "Review matching Watchdog events"
  type    = "event-v2 alert"
  message = "Review the matching Watchdog event and affected services. Add an approved notification destination."
  query   = "events(\"source:watchdog\").rollup(\"count\").last(\"5m\") > 0"
  tags    = ["env:demo", "type:watchdog"]
}
```

### SLO request 构造

基于 Metric 的 SLOs 需要定义明确的 good/total counts。以下 helper 使用上方
显式 counters。“Good”必须符合应用程序的 SLI policy；仅统计 HTTP 2xx 并非通用的
availability 定义。验证 zero-traffic 和 missing-data behavior，而不是将 absence 视为 100% success。

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

这会构建 request，而不是 live SLO。配置好的 caller 可在验证 ownership、data 和
permissions 后，将其传递给 `ServiceLevelObjectivesApi.create_slo`。Datadog 也支持
monitor-based 和 time-slice SLOs；请选择与 SLI 匹配的模型，而不是强行将 gauge/restart total 用作 good-event count。

## 成本结构

### 使用实际的产品和合同 units

| 组件 | 估算输入 |
| --- | --- |
| Infrastructure | Billable hosts/containers 或适用的 platform model、plan 和 commitment terms |
| APM | Billable APM hosts 和所选 plan/model、included allotments、ingested 和 indexed spans |
| Logs | Ingested volume，加上 indexing/retention/search/archive 选择 |
| Custom metrics / distributions | 不同的 metric/tag combinations、启用的 aggregations 和适用的 included volumes |
| Additional products | Profiling、network/security、serverless 和其他启用产品的费用 |

不要将每种产品合并到通用的 Free/Pro/Enterprise 表中。定价页面区分
products、annual/on-demand terms 以及 attached 与 standalone
offerings。Infrastructure metrics、searchable traces 和 indexed logs 的 retention
不是一个共同的“15-month”设置。

对于旧的 100-node 示例，**50 services 并不意味着 50 APM hosts**。
在 host-priced agreement 下，首先确定实际 billable Infrastructure 和 APM
host counts。30 天内每天 100 GB，则 log ingestion 为 3,000 GB，但仅 ingestion
并非总 log bill。

```text
Estimated cost =
  billable infrastructure units × applicable rate
  + billable APM units × applicable rate
  + ingested/indexed span overages under the contract
  + 3,000 GB × applicable log-ingestion rate
  + indexed events/retention/search/archive charges
  + custom-metric and other enabled-product charges
```

先前约 $3,350 的总额使用了不匹配的 APM units，并遗漏了 billable dimensions。
它不是实际测量的 production bill。请使用当前 site/product quote 和
measured usage，而不要将该估算视为 budget guarantee。

### Metrics、logs 和 trace controls 执行不同的操作

- `dogstatsd.nonLocalTraffic` 控制 receiver reachability；它不是 custom-metric
  quota。关闭 receiver 可能只是丢失 telemetry。
- `ignoreAutoConfig` 禁用所选 automatic checks。Container exclusion filters
  选择 containers；二者都不是通用 tag-cardinality limiter。
- 在其 collection owner 处检查允许的 metrics 和 tag values。更改 origin
  tag cardinality 可能改变可用 grouping tags，因此请重新检查 monitors/SLOs。
- Source-side log exclusion 避免发送所选 records。Index exclusion 发生得更晚，
  并不会消除 ingestion costs。保留 incident evidence 和 failures；不要无论结果如何都丢弃每一条 health-check line。
- Sampling 与 indexing/retention 相互独立。`DD_TRACE_SAMPLE_RATE` 或 sampling
  rules 取决于 library/version 和 matching scope。文档化的 Python
  `DD_TRACE_RATE_LIMIT` 是 per process，并与配置的 sampling rules/rate 一同生效，
  不是 cluster-wide 或 dollar cap。10% trace rate 并不意味着整个 Datadog bill 减少 90%。

## 最佳实践

使用一致的 service/env/version labels 和有界 tags，并将 API-key ingestion
与 application-key automation permissions 分离。在收集所有 logs、process arguments
或 profiles 前，检查 application capture 和 secret/redaction paths。
监控 collector queues/drops，并在更改 filters 后验证真实 outputs。

与 operating team 就 alert severity、ownership 和 response targets 达成一致。
runbook 中的 P1/P2 labels 是 operational policy，而不是独立的 Datadog resource
definitions。测试实际 destinations、missing data 和 recovery notifications。
使用有文档记录的 SLI/SLO 和 traffic context，而不是仅因 thresholds 出现在 sample 中就选择它们。

## 故障排除

从 installation owner、实际 pod/container names 和目标 site 开始。
检查 API-key Secret references、Agent/Cluster Agent health、Kubelet/RBAC access、
scrape configuration 以及 queued/dropped telemetry。此 release render 的 node
Agent pod 包含 `agent` 和 `trace-agent` containers；旧的 `app=datadog` selector
不能可靠替代对当前 labels 的检查。

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

对于 traces，验证真实 library injection/startup、socket 或 host endpoint、
permissions 和一致的 tags。成功的 TCP check 并不能验证 UDS path，也不能证明 trace payloads 已被接受。
不要使用 `env | grep DD_`：它可能披露 API/application keys 或 proxy credentials。

对于 logs，检查实际 annotation/container identifier 和 file access，然后检查
collection exclusions、parsing 和 index filters。`agent configcheck`、status、
logs 和 archives 可能暴露 configuration 或 application data；在共享前检查/redact outputs。

`agent flare --local` 会创建供检查的 local bundle。上传或 remote flare
collection 是另一项需要授权的 support action。内置 redaction 很有用，但不能替代检查 archive
中由应用程序收集的数据。

## 验证范围

审计使用了 chart rendering 和官方 schema/source inspection、本地
DogStatsD Unix datagrams、在 Python 3.12 上运行且禁用 export/telemetry 的 ddtrace 4.14.0 manual spans、
用于 Java 17 的 dd-trace-api 1.66.0 compilation 和 synchronous MDC tests，以及 API client 2.60.0 request
models/serialization。这些检查未调用 Datadog tenant、未安装到 EKS、
未执行 admission webhook、未向 SaaS 发送 traces/logs、未创建 dashboards/monitors/
SLOs，也未测量 costs。

Monitor query 含义已根据文档化 metric units 和
aggregation rules 检查；未调用 Datadog query engine 或 Terraform provider plan。
Grok request schema 不同于 live parsing。Applications、credentials、
traffic、runtime support 和 destination ownership 仍是 deployment prerequisites。

## 参考资料

- [Kubernetes 安装和版本前提条件](https://docs.datadoghq.com/containers/kubernetes/installation.md)
- [Helm chart 3.244.0](https://github.com/DataDog/helm-charts/releases/tag/datadog-3.244.0)
- [Agent 7.83.1 release](https://github.com/DataDog/datadog-agent/releases/tag/7.83.1)
- [Kubernetes distributions](https://docs.datadoghq.com/containers/kubernetes/distributions.md)
- [Kubelet metrics](https://docs.datadoghq.com/integrations/kubelet.md)
- [Kubernetes State Metrics Core](https://docs.datadoghq.com/integrations/kubernetes_state_core.md)
- [System metrics](https://docs.datadoghq.com/integrations/system.md)
- [AWS account integration](https://docs.datadoghq.com/integrations/amazon-web-services.md)
- [Admission Controller](https://docs.datadoghq.com/containers/cluster_agent/admission_controller.md)
- [Local SDK injection](https://docs.datadoghq.com/tracing/guide/local_sdk_injection.md)
- [Kubernetes 上的 OpenMetrics](https://docs.datadoghq.com/containers/kubernetes/prometheus.md)
- [DogStatsD UDS](https://docs.datadoghq.com/extend/dogstatsd/unix_socket.md)
- [Python tracing 配置](https://docs.datadoghq.com/tracing/trace_collection/library_config/python.md)
- [Custom instrumentation](https://docs.datadoghq.com/tracing/trace_collection/custom_instrumentation/server-side.md)
- [Log parsing](https://docs.datadoghq.com/logs/log_configuration/parsing.md)
- [as_count monitor evaluation](https://docs.datadoghq.com/monitors/guide/as-count-in-monitor-evaluations.md)
- [基于 Metric 的 SLOs](https://docs.datadoghq.com/service_level_objectives/metric.md)
- [Datadog pricing 和 billing FAQs](https://www.datadoghq.com/pricing/)
- [Agent flare handling](https://docs.datadoghq.com/agent/troubleshooting/send_a_flare.md)

[测验](../../quizzes/observability/metrics/05-datadog-quiz.md)
