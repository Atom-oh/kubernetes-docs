# Datadog

> **最后更新**: September 13, 2026
> Helm chart 3.244.0；对应的 Agent/Cluster Agent 为 7.83.1。
> 下文说明配置、SDK 和本地验证限制；未修改任何 Datadog 租户。

## 简介

Datadog 提供 SaaS 可观测性后端。团队仍需负责采集器、身份、
网络访问、埋点、数据披露、保留策略、监控器和成本。
Infrastructure Monitoring、APM、性能分析、日志及其他产品拥有不同的
权益和计费维度；安装 Agent 并不包含所有产品。

| 主题 | Datadog | CloudWatch | 自行管理的 Prometheus / Grafana |
| --- | --- | --- | --- |
| 后端 | Datadog SaaS，且可用性因站点而异 | AWS 托管服务 | 自行运营的存储、查询和可视化 |
| 采集 | Agent/Cluster Agent、库和受支持的 OTel 路径 | AWS 服务指标、agents/SDKs/OTLP | Exporters、抓取、agents 和 remote write |
| APM/日志 | 选择并配置所需产品 | Application Signals、tracing 和 Logs 集成 | 配置相关后端和采集器 |
| 运维 | 仍由采集器/配置和应用负责 | 仍由采集器/配置和响应负责 | 仍由后端和采集负责 |
| 成本 | 主机和其他特定产品的用量/保留单位 | Metric/observation/OTLP/log/query/alarm 单位 | 基础设施和运维投入 |

为组织及其凭证选择正确的 Datadog **站点**；
API 端点、数据驻留、可用产品和定价条款不可在各站点之间
互换。请使用集成目录，而不是声称固定的集成数量，或采用通用的
“简单/高级/便宜”排名。

## EKS 集成架构

| 组件 | 职责 / 边界 |
| --- | --- |
| Node Agent | 主机/容器检查；通常是在受支持 EC2 节点上运行的 DaemonSet |
| Cluster Agent | 共享 Kubernetes 元数据/检查、事件协调以及可选的 admission/external-metric 功能 |
| Trace Agent | 接收应用 trace payload 并转发 |
| Process collection / system-probe | 可选的进程/网络/安全功能，各自具有 OS、权限和产品要求 |
| Admission Controller | 将连接设置以及（配置后）受支持的客户端库注入新 Pod |

应用埋点会生成 traces/profiles；仅有 Agent listener 或 Pod
label 并不能证明已完成埋点。Cluster Agent 并非普通的
应用日志或 trace 转发路径。

本章安装面向 **Linux EC2 支持的 EKS 节点**。EKS Fargate
使用文档规定的按 Pod/sidecar 采集模型，而不是此主机 DaemonSet。
UDS 仅限本地主机且不支持 Windows。Windows、Bottlerocket、
Auto Mode 和混合计算需要各自发行版/功能特定的设置及
受支持的主机访问。不要禁用 TLS 验证，也不要声称所有 eBPF/process
功能在任何环境中都可用。

Datadog 针对 Kubernetes 1.33+ 的 `AllocatedResources` 兼容性记录了
Agent 和 Cluster Agent 7.67+，并建议其版本匹配。此类最低
功能要求并非当前 EKS 支持矩阵。

概览展示了可能的采集路径。traces/profiles 需要应用埋点及所选产品；必须配置 Watchdog 通知路由。

![Datadog 节点 Agent 遥测数据和 Cluster Agent 元数据到达已配置的 SaaS 产品。](../../.gitbook/assets/en-observability-metrics-05-datadog-1.png)

[交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-metrics-05-datadog-1.html)

## Datadog Agent 安装

Datadog 建议对更高层生命周期配置使用其 Operator，同时也
支持 Helm 安装。本示例通过 **Datadog Agent Helm chart** 管理
node/Cluster Agents。Chart 3.244.0 打包了一个可选的 Operator 依赖；
`datadog.operator.enabled: false` 会将该附加 controller 排除在本示例之外。
这并不意味着 Operator 已过时。

Chart 默认使用 Agent/Cluster Agent 7.82.3。本示例明确将两者固定到
**7.83.1** 和已验证的 image-index digests。该版本包含网络测试
计费、containerd snapshot 清理以及 Cluster Agent leader-lock 关闭修复。
Agent/Cluster Agent image indexes 包含 Linux amd64/arm64。成功的
模板渲染并不代表 Kubernetes 部署或运行时兼容性测试。

### 凭证和安装所有权

此配置文件通过原生 `aws.secrets` 后端从
AWS Secrets Manager 获取 Datadog API key 和共享的 Cluster Agent token。基线摄取
不需要 application key；external metrics 保持禁用。

在 `ap-northeast-2` 中准备 `observability/datadog`，其中包含 JSON 字符串键 `api-key`
和 `cluster-token`；token 必须使用密码学安全的随机值，且至少
32 个字符。API key 必须与 Datadog 站点匹配。位于命名空间 `datadog` 中的两个 ServiceAccounts，
`datadog` 和 `datadog-cluster-agent`，都需要范围受限的 IRSA
roles、区域 STS/Secrets Manager 连通性，以及适用时的 KMS 权限。
替换两个示例 role ARNs。已禁用 EC2 metadata credential fallback。
参阅[完整前置条件和可重用配置文件](https://github.com/Atom-oh/kubernetes-docs/blob/5ff787faed758902c12a74e8429466f434bb26ae/examples/observability/secret-profiles/README.md)。

请使用 Python 3/PyYAML 6.0.3 以及该仓库目录中的可执行
固定 chart postrenderer。它会将恰好七个硬编码的 SecretKeyRef 条目替换为
**字面量 `ENC[...]` handles**，并保留 node、trace、init 和 Cluster Agent
消费者。原生解析会更新内存中的配置，而非环境变量。
init script 需要非空 `DD_API_KEY`，因此没有有效替代方案时将其删除会导致启动失败。
`must-use-secret-postrenderer` Secret 被刻意省略；不要创建它来绕过缺失的 renderer。
每次 install/upgrade 都应保留 renderer，并审查对固定 chart、images 或 profile contract 的更改。

这些命令仅会在安装时变更集群；审计中未执行部署。
在准备 IAM/secret 前置条件后，请从仓库根目录、已有的 `datadog` 命名空间中，
使用由您拥有的 release 运行。

```bash
PROFILE=examples/observability/secret-profiles
helm repo add datadog https://helm.datadoghq.com
helm repo update datadog
helm template datadog datadog/datadog --version 3.244.0 \
  --namespace datadog --include-crds -f "$PROFILE/datadog-values.yaml" \
  --post-renderer "$PROFILE/datadog_postrender.py" > datadog-reviewed-render.yaml
# Review resources and ownership first; retain the renderer on EVERY upgrade.
helm upgrade --install datadog datadog/datadog --version 3.244.0 \
  --namespace datadog -f "$PROFILE/datadog-values.yaml" \
  --post-renderer "$PROFILE/datadog_postrender.py"
```

### 经审核的 values

以下内容与可重用的 `datadog-values.yaml` 一致。日志需通过容器
配置选择启用，APM/DogStatsD 使用 UDS，且未在此处启用集群范围的自动库注入、
external HPA metrics、discovery network statistics 和可选的 process/network
采集。
应用命名空间应与 Agent 命名空间分开；SSI 不会对 Agent 自身命名空间中的 Pod 进行埋点。

```yaml
# datadog 3.244.0: postrenderer required; replace example IRSA role ARNs.
targetSystem: linux
registry: gcr.io/datadoghq
datadog:
  apiKeyExistingSecret: must-use-secret-postrenderer
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
  secretBackend:
    type: aws.secrets
    config:
      aws_session:
        aws_region: ap-northeast-2
    enableGlobalPermissions: false
  env: &id001
  - name: AWS_EC2_METADATA_DISABLED
    value: 'true'
  - name: DD_SECRET_REFRESH_INTERVAL
    value: '0'
  - name: DD_SECRET_REFRESH_ON_API_KEY_FAILURE_INTERVAL
    value: '0'
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
  tokenExistingSecret: must-use-secret-postrenderer
  rbac:
    create: true
    serviceAccountAnnotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/datadog-cluster-agent-secrets
  env: *id001
agents:
  image:
    tag: 7.83.1
    digest: sha256:ed0bd588e955d82f661d1b8dd1cdf179c1023e74a2817e7a812c99d52f05c319
  rbac:
    create: true
    serviceAccountAnnotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/datadog-agent-secrets
```

postrendering 后，唯一与凭证相关的环境值为
`ENC[observability/datadog;api-key]` 和 `ENC[observability/datadog;cluster-token]`。
`DD_SECRET_BACKEND_TYPE`/`CONFIG` 仅携带后端类型和区域。没有 shell
导出已解析的值，没有真实 key 被放入 Helm values，并且 profile
不需要 Kubernetes credential Secret。两个 init-volume containers 仅
复制 image 配置；init-config 使用 API-key handle 执行其 bootstrap
检查。实际的原生后端授权和 Datadog 摄取仍需要运行时验证。

已明确禁用计划性和 API-failure secret refresh。请通过经批准的 node/trace
和 Cluster Agent Pods 协调重启进行轮换；在整个集群使用新 key 前，保持旧
API key 有效。cluster-token 变更可能会在混合版本 rollout 期间中断
node/Cluster Agent 认证，因此请规划维护窗口或单独验证过的过渡方案。
不声称支持零停机轮换。参阅 [Datadog secret backends](https://docs.datadoghq.com/agent/guide/secrets-management/)。

`processAgent.enabled` 已弃用；请使用单独的 collection options。
Chart 已在适用时挂载 `/etc/passwd`，因此不要添加重复的手动
`passwd` volumes/mounts。资源覆盖按组件设置，例如
`agents.containers.agent.resources`；应在负载下为实际渲染出的 containers 确定大小。
两个 Cluster Agent replicas 不能替代 placement、disruption 和 failure 测试。

原有顶层 `kubeStateMetricsEnabled` 和 `prometheus.enabled` 条目
并不能配置所声称的 integrations。旧版 KSM 选项嵌套在
`datadog` 下；示例使用 `datadog.kubeStateMetricsCore.enabled` 并避免
重复的旧版采集。显式 Datadog Autodiscovery checks 与启用 annotation 范围的
`prometheusScrape` 是分开的。

`datadog.profiling.enabled` **有效**。它会向符合条件的 Pod 注入
`DD_PROFILING_ENABLED`，并且需要已安装的 client libraries 和 Cluster Agent 7.57+。
它不会将 profiler 安装到任意未埋点应用中。
请有意识地选择其 `null`/`false`/`auto`/`true` 行为。同样，启用
external HPA metrics 需要其 application key、API permissions、service/CRDs
以及实际的 metric 可用性；network monitoring 需要受支持的 system-probe access。

### AWS 账户集成是独立路径

SaaS AWS account integration 使用经授权的 cross-account role 和
Datadog 提供的 external ID，并具有所选 integrations 所需的权限。
附加到 node Agent SA 的任意 IRSA role 并不会配置该 SaaS
integration。普通 Kubernetes Agent 采集不需要此处之前显示的宽泛
CloudWatch/EC2/tag policy。

仅在实际调用 AWS 的 Agent/check 中使用 Pod Identity 或 IRSA，并为其配置
特定的 role、trust 和 permissions。请解析**渲染后的** service-account name；
为猜测的 `datadog-agent` SA 创建 IAM association 不会绑定 Helm release 所用的
不同 SA。绝不要将本地 STS caller check 视为 workload identity 的证明。

## Infrastructure Monitoring

### 检查 metric 的 collector、unit 和 tags

| Metric / source | 含义 |
| --- | --- |
| `system.cpu.idle` / System check | CPU idle **百分比**；适合基于百分比的 node threshold |
| `system.mem.total`, `system.mem.used`, `system.mem.free` | Memory 测量值；free 不能与 usable/reclaimable memory 互换 |
| `kubernetes.cpu.usage.total` / Kubelet | **Nanocores**，而非百分比；一个 core 为 1,000,000,000 nanocores |
| `kubernetes.memory.usage`, `kubernetes.memory.limits` | Bytes；usage 与 limit 的比较需要匹配相同 entity/tag set |
| `kubernetes.pods.running`, `kubernetes.containers.restarts` | 有效的 Kubelet gauges：运行中的 Pods 和容器累积重启数 |
| `kubernetes_state.deployment.replicas_available`, `kubernetes_state.deployment.replicas_desired` | Kubernetes State Metrics Core Deployment 状态 |
| `kubernetes_state.pod.status_phase`, `kubernetes_state.service.count` | Pod phase/service inventory；请检查其文档化的 grouping tags |
| `kubernetes_state.container.restarts` | State Core 的 restart gauge，带有 namespace/pod/container tags |

旧版 Kubernetes integration、Kubelet check 和 State Core 拥有不同的
catalogues。一个 catalogue 中缺失的 metric 并不一定表示它已从
Agent 移除。不要盲目重命名有效 Kubelet metrics。Filesystem/network 可用性
和 rate units 取决于 collector/runtime；请阅读该 metric 的实际定义。

对此 Kubernetes 安装使用标准 `kube_cluster_name` tag，并在分组前检查
真实 metric tags。以集群为中心的 State Core metrics 并不总是带有 `host` tag。
`cluster_name` 和 `kube_cluster_name` 不可互换。将原始 nanocore 值与 80 比较
并不表示 80% CPU。

### OpenMetrics Autodiscovery

将以下**元数据片段**合并到一个 container 名为
`app` 且在 port 9464 上提供 gauge `queue_depth` 的 workload 中。它不会创建该
应用或 endpoint。annotation 的 container identifier 必须匹配。
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
Autodiscovery annotations 不需要单独的 Prometheus server，也不需要 chart 的广泛
`prometheusScrape` discovery。请限制所选 metrics/labels。
对于 counters 和 histograms，请验证 name normalization、发出的 `.count`/bucket
series 及 check-version 行为，不要假设 Prometheus 名称也是最终的 Datadog 名称。

### DogStatsD：使用应用可访问的 endpoint

应用 Pod 的 `localhost` 并不是 node Agent。此 Linux 示例使用
host-local UDS directory。Admission Controller 的 `socket` mode 可注入
`DD_DOGSTATSD_URL`、`DD_TRACE_AGENT_URL` 和 volume；否则请明确配置匹配的
mounts 和 permissions。Pod 特定的 `admission.datadoghq.com/config.mode`
是 **label**，而非 annotation。请挂载 parent directory，以便在 Agent 重启后
socket replacement 仍然可见。

已使用 `datadog==0.53.0` 检查 Python helper。向 `socket_path` 传入实际的
filesystem path，例如 `/var/run/datadog/dsd.socket`；其他 SDKs/environment settings
使用的 `unix://` URL 并非相同的 argument format。
使用实际 interval counts 调用 `emit_batch`，包括值为零的 good/error 值。

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

Go helper 使用 datadog-go/v5。使用 `WithNamespace("my_app.")`
和相同的 `env:demo,service:orders` tags 创建 client。请检查 constructor、send 和 close
errors；不要丢弃 `statsd.New` error。helper 不会关闭调用方提供的共享
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

| DogStatsD type | 解读 |
| --- | --- |
| Counter | 区间计数；Datadog 可能将其存储为 rate。`.as_count()` 会重建 query window 的 counts |
| Gauge | 如 queue depth 的快照；对快照求和并不是已处理请求数 |
| Histogram | 由接收 Agent 聚合；对 per-host percentiles 求平均不能产生全局 percentile |
| Distribution | 支持后端 distribution aggregation；请审查启用的 percentiles、tags 和 billing |
| Service check | 来自真实 health check 的状态：0 OK、1 warning、2 critical、3 unknown |

本地 datagram delivery 不会确认 SaaS ingestion。UDP 可能丢包；
UDS/client buffering 和 Agent queues 也需要监控。示例 helper
未启用 DogStatsD client telemetry，因此请为部署选择单独的 collection-health signal。
Counter retries/duplicate sends 并不是 exactly-once business ledger。

### 基于文件的 Autodiscovery 配置

对于 Helm 管理的配置，`datadog.confd` 会创建并挂载 check files。
仅因存在名为 `datadog-checks` 的独立 ConfigMap，并不会自动发现它。
以下 NGINX fragment 需要匹配的 image identity 以及已配置、已授权的
`stub_status` endpoint。

```yaml
datadog:
  confd:
    nginx.yaml: "ad_identifiers:\n  - nginx\ninit_config: {}\ninstances:\n  - nginx_status_url:\
      \ http://%%host%%:80/nginx_status\n"
```

经认证的 Redis check 还需要正确的 port/TLS 和 credential
delivery。`%%env_REDIS_PASSWORD%%` 读取的是 **Agent 的** environment，而非 Redis
应用 Pod 的 environment。请优先使用已配置的 Datadog secret backend 或具备所需特定
permissions 的受保护文件交付；不要在公开 check examples 中暴露 passwords，
也不要仅为 discovery 授予集群范围的 Secret reads。

## APM 和 Distributed Tracing

### 本地 SDK 注入和 SSI 是明确选择

admission opt-in label 允许 mutation/connection-setting injection。要安装
a tracing library，请配置 SSI targets 或受支持的 language/version annotation。
仅有 label 并不能证明 SDK 已安装或 traces 已到达 Datadog。
Java/Python/Node.js 本地注入需要 Cluster Agent 7.40+；.NET/Ruby 需要
7.44+。当前 7.83.1 还会将 `kube-system` 和其自身 namespace 排除在注入之外。

对于受控 Java 示例，请将以下 **pod-template fragment** 合并到应用命名空间中已有的
Deployment，保留其 selector、containers 和 security settings。它不是可单独 apply 的完整
Deployment。已验证 Java init image `gcr.io/datadoghq/dd-lib-java-init:v1.66.0`
可用于 Linux amd64/arm64。请验证实际应用的 JVM/framework/image compatibility。

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
不要仅将 label 放在 Deployment metadata 上，并期望其 pods 继承它。
注入发生在**新 Pod** 被 admission 时。请确认注入的 init
containers、library files、UDS mounts/permissions 和非 secret connectivity
settings，然后验证实际 traffic/traces。namespace exclusions、webhook failures、
security policies 和 unsupported images 都可能阻止 instrumentation。

集群范围的 SSI 是通过 `datadog.apm.instrumentation` 配置的替代方案，
其中包含经过审查的 namespace/pod targets 和 library versions。
避免无意中组合手动和注入的 tracers：注入的 library 可能优先于手动安装的 library。
Profiler 启用仍需要受支持的 client library 及其自身的 product/runtime conditions。

### 手动 Java instrumentation

启动应用 JVM 时，使用分阶段、已版本化的 `dd-java-agent.jar`，或使用上面
已验证的 injection 路径。仅添加 `dd-trace-api` 可访问
annotation/API；它**不会**启动 runtime bytecode instrumentation。
以下 Maven dependency 和 Java source 是不同文件。

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

handler 代表由调用方提供的应用代码。请使用有界的
operation/resource names。旧示例中按 order/customer identifier 设置的 tags
对于本演示并非必需，并可能造成 disclosure/cardinality risks。
手动 span APIs 需要其相应的受支持 bridge/library；不要向只有 annotation API 的项目
添加 OpenTracing imports。

### 手动 Python instrumentation

此已检查的 4.14.0 示例使用当前的 `ddtrace.trace` import。请将
dependency declaration 保留在 `requirements.txt` 中，而非 Python code block 内。
对于 framework auto-instrumentation，请在 application imports 前遵循所选
`ddtrace-run`/SSI setup；不要认为此 helper 会 patch 整个 framework。

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

等效的 `tracer.wrap` decorator 可用于 method tracing。来自 handler 的 exceptions
必须传播；记录 span 并不是应用 retry 或 success guarantee。请在受支持的
HTTP/message integrations 中使用正确的 service/env/version tags 和 context propagation。
Service maps 来自观察到的 instrumented relationships，而非仅来自任意 `DD_TAGS`。

默认不要标记原始 customer/order identifiers、tokens 或 request bodies。
请审查实际应用的 instrumentation capture、error messages 和 sampling/redaction rules。
Auto-instrumentation 不保证完全移除 PII。

## Log Management

### 审慎选择采集和解析

安装启用了 log collection，但保留 `containerCollectAll: false`。
将此 metadata 合并到名为 `app` 的 container 的 pod template 中。
multiline rule 适用于**以日期开头的纯文本 Java records**。
它不是通用 JSON-log parser。Container runtime framing 和 application
message parsing 是不同阶段；请验证实际采集的 records。

```yaml
metadata:
  annotations:
    ad.datadoghq.com/app.logs: "[\n  {\n    \"source\": \"java\",\n    \"service\"\
      : \"orders\",\n    \"log_processing_rules\": [\n      {\n        \"type\": \"\
      multi_line\",\n        \"name\": \"java_timestamp_start\",\n        \"pattern\"\
      : \"^\\\\d{4}-\\\\d{2}-\\\\d{2}\"\n      }\n    ]\n  }\n]"
```

对于每行一个 JSON event 的应用，请使用受支持的 JSON path，而不要
通过此 rule 将不相关的 JSON events 合并。File access、runtime paths、annotation
matching、exclusion settings 和 backend pipeline filters 都会影响 collection。
请使用一个匹配的应用和一个被排除的应用检查选择性采集。

### Pipeline 请求结构

此请求使用实际的 API fields **`match_rules` 和 `support_rules`**。
旧的 camelCase fields 并非 Logs API model。样例 message 定义预期的行格式；
请使用应用的实际 format/timezone，并测试 unmatched/multiline/error cases。
有效 request model 并不能证明 Datadog tenant 中的 Grok parsing 或 ingestion/indexing。

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

创建/重新排序 Pipeline 会改变匹配 logs 的处理。请在正确站点下，使用
范围受限的 API permissions 和已有 pipeline ownership 进行配置。
此次审计中未发送任何 pipeline request。

### Trace-log correlation 和 MDC ownership

尽可能使用受支持的 automatic log injection，并在 structured logs 中将 trace/span IDs
保留为 strings。还需要正确的 service/env/version、timestamps、parsing 和可用的 trace data；
仅有两个 ID fields 并不能保证 correlation。当一个 process 尚未完成 instrumentation 时，
没有有用的 active trace ID。

对于明确管理 SLF4J MDC 的应用，此 helper 会在成功和失败时恢复调用方的
**整个先前 context**。旧版无条件 `MDC.clear()` 会丢失不相关的 caller fields。
它是 synchronous helper，而非 async context propagation mechanism 或完整 servlet filter。

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

它需要 `dd-trace-api` 和应用兼容的 SLF4J API/provider。
logging pattern 或 JSON encoder 必须包含 MDC values。不要在没有 servlet API、imports 和
已检查 exception contract 的情况下复制 servlet 示例。

## Dashboards 和 Alerts

<span id="dashboard-creation-api"></span>

### Dashboard 请求构建

此 helper 使用 `datadog-api-client==2.60.0` 构建 request body。cluster
和 namespace template variables 确实被其 queries 引用。host
widget 使用 percent metric；pod widget 使用 memory bytes 及其 namespace
filter。请检查所选数据是否确实具有 grouping tags。

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

调用方提供正确配置的 `ApiClient`，并使用 `DashboardsApi`
创建或更新目标 dashboard。记录/协调其返回的 ID；按标题重复创建可能产生 duplicates。
站点和范围受限的 automation credentials 独立于 node Agent API key。
此次审计中未调用 dashboard API。

<span id="monitor-alert-configuration"></span>

### Monitor queries 和 units

请使用已配置的 Datadog Terraform provider 和项目 version constraints/lock file。
这些是 resource fragments，并非完整的 provider/credential setup。thresholds
只是示例；请检查真实 metric units、tags、windows 和 application objectives。
第一个 monitor 直接评估 idle percent，而不是将 nanocores 与 80 比较并称结果为“CPU percent”。

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

restart gauge 是**总数**。对两个 windows 中重复的 gauge samples 求和再比较，
无法可靠地统计新重启数，尤其在发生 resets、replacement
pods 或采样不均等时。recent-restart monitor 需要经过验证的 delta/reset
design。本示例明确针对 total 发出 alert。

error monitor 使用 `emit_batch` 发出的三个 counters，
包括 errors/good requests 的显式零值。对于 `.as_count()` evaluation，time
aggregation 发生在**除法之前**：sum(errors)/sum(total)，而不是对每个 time bucket 的 ratio
求和。请在此路径中使用 sum aggregator。

零流量、缺失 telemetry 和真正无 error 的流量是不同情况。
请定义 minimum traffic/collection-health conditions 并验证 monitor 的
no-data behavior。`notify_no_data: false` 并不建立 health；它只是在这些 fragments 中
不会对缺失数据发出通知。

对于内置 APM metrics，请使用所选 integration 生成的实际
`trace.<operation>.hits/errors` names 和 tags。Java、Python 和其他 integrations
并非都会发出 `trace.http.request.*`。Trace analytics、generated trace metrics 和
custom DogStatsD metrics 是不同 sources。

<span id="watchdog-ai"></span>

### Watchdog 和通知交付

Watchdog 可以呈现检测到的 anomalies/insights，而无需手动选择每一个
threshold。insight 并不证明通知已交付。请使用受支持的 Watchdog/monitor workflow，
并验证目标站点中的 event source、product availability 和 notification routing。

以下 event-monitor fragment 假定该组织中存在匹配
`source:watchdog` 的实际 events。它不会杜撰 `story_category`
group tag，也不保证每个 Watchdog result 都会出现在此 stream 中。启用通知前，
请根据真实 events 验证 filter。

```hcl
resource "datadog_monitor" "watchdog_events" {
  name    = "Review matching Watchdog events"
  type    = "event-v2 alert"
  message = "Review the matching Watchdog event and affected services. Add an approved notification destination."
  query   = "events(\"source:watchdog\").rollup(\"count\").last(\"5m\") > 0"
  tags    = ["env:demo", "type:watchdog"]
}
```

<span id="_3-slo-configuration"></span>

### SLO 请求构建

基于 metric 的 SLOs 需要定义明确的 good/total counts。以下 helper 使用上述显式
counters。“Good”必须与应用的 SLI policy 匹配；仅统计 HTTP 2xx 并非通用的
availability definition。请验证 zero-traffic 和 missing-data behavior，而不要将缺失视为
100% success。

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

这会构建 request，而非实时 SLO。验证 ownership、data 和 permissions 后，
已配置的调用方可将其传递给 `ServiceLevelObjectivesApi.create_slo`。
Datadog 也支持 monitor-based 和 time-slice SLOs；请选择与 SLI 匹配的 model，
而不是强行将 gauge/restart total 用作 good-event count。

## Cost Structure

<span id="pricing-overview"></span>

### 使用实际 product 和 contract units

| 组件 | 估算输入 |
| --- | --- |
| Infrastructure | 可计费 hosts/containers 或适用的 platform model、plan 和 commitment terms |
| APM | 可计费 APM hosts 和所选 plan/model、包含的 allotments、摄取和已索引 spans |
| Logs | 摄取 volume，以及 indexing/retention/search/archive 选择 |
| Custom metrics / distributions | 不同的 metric/tag combinations、启用的 aggregations 和适用的 included volumes |
| Additional products | Profiling、network/security、serverless 和其他已启用的 product charges |

不要将每种 product 合并为通用的 Free/Pro/Enterprise table。定价
页面区分 products、annual/on-demand terms 以及 attached 与 standalone
offerings。infrastructure metrics、searchable traces 和 indexed logs 的保留期
不是一个共同的“15-month”设置。

<span id="cost-calculation-example"></span>

对于旧的 100-node 示例，**50 services 并不意味着 50 APM hosts**。在按
host 定价的 agreement 下，先确定实际可计费的 Infrastructure 和 APM
host counts。对于 30 天每天 100 GB，log ingestion 为 3,000 GB，但仅 ingestion
并不是 total log bill。

```text
Estimated cost =
  billable infrastructure units × applicable rate
  + billable APM units × applicable rate
  + ingested/indexed span overages under the contract
  + 3,000 GB × applicable log-ingestion rate
  + indexed events/retention/search/archive charges
  + custom-metric and other enabled-product charges
```

之前约 $3,350 的 total 使用了不匹配的 APM units，并遗漏可计费维度。
它不是测量得到的生产 bill。请使用当前 site/product quote 和已测量的 usage，
而不要将该估算视为 budget guarantee。

<span id="cost-optimization-strategies"></span>

### Metrics、logs 和 trace controls 的作用不同

<span id="_1-metric-optimization"></span>

- `dogstatsd.nonLocalTraffic` 控制 receiver reachability；它不是 custom-metric
  quota。关闭 receiver 可能只会丢失 telemetry。
- `ignoreAutoConfig` 禁用选定 automatic checks。container exclusion filters
  选择 containers；两者都不是通用 tag-cardinality limiter。
- 请在其 collection owner 处审查允许的 metrics 和 tag values。改变 origin
  tag cardinality 可能改变可用 grouping tags，因此应重新检查 monitors/SLOs。
<span id="_2-log-optimization"></span>

- Source-side log exclusion 可避免发送选定 records。Index exclusion 发生在
  更晚阶段，且不会消除 ingestion costs。请保留 incident evidence 和 failures；
  不要不论结果如何都丢弃每条 health-check line。
<span id="_3-apm-sampling"></span>

- Sampling 与 indexing/retention 是分开的。`DD_TRACE_SAMPLE_RATE` 或 sampling
  rules 取决于 library/version 和 matching scope。文档化的 Python
  `DD_TRACE_RATE_LIMIT` 按 process 生效，并与已配置的 sampling rules/rate 一起应用，
  而不是集群范围或 dollar cap。10% trace rate 并不意味着整个 Datadog bill 减少 90%。

## Best Practices

<span id="_1-tagging-strategy"></span>

使用一致的 service/env/version labels 和有界 tags，并将 API-key
ingestion 与 application-key automation permissions 分开。收集所有 logs、process
arguments 或 profiles 前，请审查 application capture 和 secret/redaction paths。
监控 collector queues/drops，并在更改 filters 后验证真实 outputs。

<span id="_2-alert-layering"></span>

与运维团队就 alert severity、ownership 和 response targets 达成一致。
runbook 中的 P1/P2 labels 是运维 policy，而非独立的 Datadog resource
definitions。测试实际 destinations、missing data 和 recovery notifications。
请使用有文档记录的 SLI/SLO 和 traffic context，而不是仅因为它们出现在样例中就选择 thresholds。

<span id="common-issues"></span>

## Troubleshooting

<span id="_1-agent-not-sending-metrics"></span>

从 installation owner、实际 pod/container names 和目标 site 开始检查。
检查字面原生后端 handles、Secrets Manager IRSA 和必需的 postrenderer、
Agent/Cluster Agent health、Kubelet/RBAC access、
scrape configuration 以及 queued/dropped telemetry。此版本渲染出的 node
Agent pod 包含 `agent` 和 `trace-agent` containers；旧的 `app=datadog` selector
并非检查当前 labels 的可靠替代方案。

<span id="debugging-commands"></span>

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

<span id="_2-missing-apm-traces"></span>

对于 traces，请验证真实的 library injection/startup、socket 或 host endpoint、
permissions 和一致的 tags。成功的 TCP check 无法验证 UDS
path，也不能证明 trace payloads 已被接受。不要使用 `env | grep DD_`：它可能披露
API/application keys 或 proxy credentials。

<span id="_3-logs-not-collected"></span>

对于 logs，请检查实际 annotation/container identifier 和 file access，然后检查
collection exclusions、parsing 和 index filters。`agent configcheck`、status、
logs 和 archives 可能暴露配置或应用数据；分享前请检查/遮蔽输出。

`agent flare --local` 会创建用于检查的本地 bundle。上传或 remote flare
collection 是单独的、经授权的 support action。内置敏感数据遮蔽很有用，
但不能替代审查 archive 中由应用采集的数据。

## 验证范围

审计使用了 chart rendering 和官方 schema/source 检查、local
DogStatsD Unix datagrams、在 Python 3.12 上运行并禁用 export/telemetry 的 ddtrace 4.14.0 manual spans、
用于 Java 17 的 dd-trace-api 1.66.0 compilation 和 synchronous MDC tests，以及 API client 2.60.0 request
models/serialization。这些检查未调用 Datadog tenant、未在 EKS 上安装、
未执行 admission webhook、未向 SaaS 发送 traces/logs、未创建 dashboards/monitors/
SLOs，也未测量 costs。

已根据文档化的 metric units 和 aggregation rules 检查 monitor query 含义；
未调用 Datadog query engine 或 Terraform provider plan。
Grok request schema 与实时 parsing 不同。应用、凭证、
traffic、runtime support 和 destination ownership 仍是部署前置条件。

## 参考资料

- [Kubernetes 安装和版本前置条件](https://docs.datadoghq.com/containers/kubernetes/installation.md)
- [Helm chart 3.244.0](https://github.com/DataDog/helm-charts/releases/tag/datadog-3.244.0)
- [Agent 7.83.1 版本](https://github.com/DataDog/datadog-agent/releases/tag/7.83.1)
- [Kubernetes 发行版](https://docs.datadoghq.com/containers/kubernetes/distributions.md)
- [Kubelet metrics](https://docs.datadoghq.com/integrations/kubelet.md)
- [Kubernetes State Metrics Core](https://docs.datadoghq.com/integrations/kubernetes_state_core.md)
- [System metrics](https://docs.datadoghq.com/integrations/system.md)
- [AWS 账户集成](https://docs.datadoghq.com/integrations/amazon-web-services.md)
- [Admission Controller](https://docs.datadoghq.com/containers/cluster_agent/admission_controller.md)
- [本地 SDK 注入](https://docs.datadoghq.com/tracing/guide/local_sdk_injection.md)
- [Kubernetes 上的 OpenMetrics](https://docs.datadoghq.com/containers/kubernetes/prometheus.md)
- [DogStatsD UDS](https://docs.datadoghq.com/extend/dogstatsd/unix_socket.md)
- [Python tracing 配置](https://docs.datadoghq.com/tracing/trace_collection/library_config/python.md)
- [自定义 instrumentation](https://docs.datadoghq.com/tracing/trace_collection/custom_instrumentation/server-side.md)
- [Log parsing](https://docs.datadoghq.com/logs/log_configuration/parsing.md)
- [as_count monitor 评估](https://docs.datadoghq.com/monitors/guide/as-count-in-monitor-evaluations.md)
- [基于 metric 的 SLOs](https://docs.datadoghq.com/service_level_objectives/metric.md)
- [Datadog 定价和计费常见问题](https://www.datadoghq.com/pricing/)
- [Agent flare 处理](https://docs.datadoghq.com/agent/troubleshooting/send_a_flare.md)

<span id="quiz"></span>

[测验](../../quizzes/observability/metrics/05-datadog-quiz.md)
