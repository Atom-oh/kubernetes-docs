# Amazon EKS 高级调试测验

> **最后更新**：2026 年 9 月 12 日

[源章节](../../eks/11-eks-advanced-debugging.md)定义了当前 API、范围和安全假设。示例不是实时集群/基准测试结果。本次审查未执行云端或集群操作。

本测验考查你对 Amazon EKS 高级调试技术的理解，包括事件响应、控制平面调试、节点故障排查、kubectl debug、PromQL 查询和可观测性。

## 测验概览
- 事件响应流程
- EKS 控制平面调试
- 节点和 kubelet 故障排查
- kubectl debug 命令用法
- PromQL 查询和指标分析
- 分布式追踪和日志分析

## 选择题

### 1. 已启用的 EKS 控制平面审计日志通常在哪里查询？

A. 客户管理的 /var/log/kubernetes 目录
B. Amazon CloudWatch Logs
C. 直接访问托管 etcd
D. 在 AWS 控制平面 Pod 上运行 kubectl logs

<details>
<summary>查看答案</summary>

**答案：B. Amazon CloudWatch Logs**

在正确的区域/账户中使用 `/aws/eks/<cluster-name>/cluster`。五种可用类型为 api、audit、authenticator、controllerManager 和 scheduler；它们需显式启用，启用日志也不会恢复旧日志。403 表示授权失败的证据，不会自动证明 IAM 身份验证失败。应在 Logs Insights QL 中单独运行查询，并指定明确的时间窗口。

```bash
# Read-only: confirm logging is enabled before searching the owned group.
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query cluster.logging
```
```text
fields @timestamp, user.username, verb, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 403
| sort @timestamp desc
| limit 100
```

</details>

### 2. 哪个 kubectl debug 标志会请求创建 Pod 的独立副本？

A. --attach
B. --copy-to
C. --ephemeral
D. --sidecar

<details>
<summary>查看答案</summary>

**答案：B. --copy-to**

上一题错误地将其描述为向原 Pod 添加容器。--copy-to 会创建另一个 Pod；使用 ephemeral container 调试原 Pod 时，不需要该标志，也没有 --ephemeral 标志。若运行时支持，--target 会请求使用进程命名空间。副本可能保留 ServiceAccount、环境变量/Secret 引用、卷及其他普通容器；禁用 init container 并更改一个命令，并不会使副本成为隔离的数据副本。

```bash
# MUTATION: separate reviewed reproduction Pod, not an ephemeral container in the original.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
: "${DEBUG_POD_NAME:?Choose a new owned name}"; : "${DEBUG_IMAGE:?Reviewed image providing sleep}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" debug "$POD_NAME" \
  --copy-to="$DEBUG_POD_NAME" --container="$CONTAINER_NAME" --image="$DEBUG_IMAGE" \
  --keep-init-containers=false --share-processes=true --profile=general -- sleep 3600
```

</details>

### 3. 检查 NotReady 节点的 condition 和 heartbeat 后，哪些证据有用？

A. 仅查看无关的应用程序日志
B. 查看适用的 kubelet/运行时状态和日志，并与网络/EC2 证据关联
C. 直接操作 AWS 管理的 etcd
D. 仅用 CoreDNS 日志作为证明

<details>
<summary>查看答案</summary>

**答案：B. 查看适用的 kubelet/运行时状态和日志，并与网络/EC2 证据关联**

没有实测频率支持此前“最常见原因”的说法。Ready=False、heartbeat 丢失/Unknown、资源压力和实例故障是不同信号。对兼容节点使用获准的主机访问，或采用 NodeDiagnostic/文档说明的 Auto Mode 调试方式；SSH/systemctl 并非通用方法。执行任何另行审查的重启或替换之前，先收集有界日志。

```bash
# Read-only Kubernetes evidence first; no automatic kubelet restart.
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o json | jq '{
  uid:.metadata.uid,providerID:.spec.providerID,nodeInfo:.status.nodeInfo,conditions:.status.conditions
}'
```

</details>

### 4. 哪项计算能衡量容器 CPU 使用量相对于大于零的已配置 CPU limit 的比例？

A. 假设存在的 cpu_usage 指标 >80
B. 每秒 CPU 秒数 >0.8，但没有分母
C. 以核为单位的 CPU 使用量 / 对应的正数 CPU limit（核）
D. 假设存在的 container_cpu_percent 指标

<details>
<summary>查看答案</summary>

**答案：C. 以核为单位的 CPU 使用量 / 对应的正数 CPU limit（核）**

rate(cpu_usage_seconds_total) 的单位是 CPU 核数，本身不是百分比。应按 cluster 范围、命名空间、Pod 和容器进行关联，并使用对应的正数 limit；没有 limit 或 limit 未知的容器不能视为 0% 利用率。HPA 的利用率通常相对于 requests 计算，这是另一种计算方式。以下查询假设使用源章节规定的单集群/标签/抓取约定，并以高于 0.8 的分数表示。

```promql
(sum by (namespace,pod,container) (
  rate(container_cpu_usage_seconds_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])
)
/ on (namespace,pod,container)
max by (namespace,pod,container) (
  kube_pod_container_resource_limits{namespace="diagnostics-example",resource="cpu",unit="core"} > 0
)) > 0.8
```
```promql
(max by (namespace,pod,container) (container_memory_working_set_bytes{namespace="diagnostics-example",container!="",container!="POD"})
/ on (namespace,pod,container)
max by (namespace,pod,container) (kube_pod_container_resource_limits{namespace="diagnostics-example",resource="memory",unit="byte"} > 0)) > 0.8
```

</details>

### 5. 哪种工具通常不用于客户诊断托管 EKS 中节点间的网络问题？

A. 在授权范围内使用 tcpdump 抓包
B. 使用 Wireshark 分析获准保存的数据包捕获
C. 从工作负载中执行有范围限制的 curl/DNS 测试
D. 使用 etcdctl 访问 AWS 管理的 etcd 端点

<details>
<summary>查看答案</summary>

**答案：D. 使用 etcdctl 访问 AWS 管理的 etcd 端点**

客户无法获得托管 etcd 的直接端点。这不表示 etcdctl 永远不能用于诊断自我管理 etcd 系统的网络问题。抓包需要适当的能力/主机环境、范围限制和数据保护；新建的调试 Pod 可能采用与故障工作负载不同的策略/DNS 路径。吞吐量计数器不是延迟测量值。

```bash
# Deliberate bounded request from an owned workload with curl installed.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
: "${HEALTH_URL:?Set a reviewed safe health URL}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- curl --silent --show-error --connect-timeout 5 --max-time 10 \
  --output /dev/null --write-out 'HTTP status: %{http_code}\n' "$HEALTH_URL"
```

</details>

### 6. 哪种方法能够在不一味降低所有阈值的情况下缩短检测延迟？

A. 只增加人工观察
B. 将每项指标的阈值都设为尽可能低
C. 采用经过测量的适当告警、覆盖率检查和升级流程
D. 仅延长保留期

<details>
<summary>查看答案</summary>

**答案：C. 采用经过测量的适当告警、覆盖率检查和升级流程**

根据实际 SLO 和故障模式调整；阈值过低会造成告警疲劳。以下 HTTP counter 和 status 标签需要应用程序埋点；请求分母为零/缺失并不代表成功。CrashLoopBackOff 应根据 waiting reason 判断，不能把每次重启都视为 crash loop。Prometheus 必须选取该规则/命名空间，通知送达还需单独验证。本次未测量 MTTD 结果。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: reviewed-quiz-alerts
  namespace: monitoring
  labels:
    release: REPLACE_WITH_SELECTED_PROMETHEUS_RELEASE
spec:
  groups:
  - name: reviewed-quiz-alerts
    rules:
    - alert: HighErrorRate
      expr: "(\n  sum(rate(http_requests_total{namespace=\"diagnostics-example\",job=\"\
        owned-app\",status=~\"5..\"}[5m]))\n  / sum(rate(http_requests_total{namespace=\"\
        diagnostics-example\",job=\"owned-app\"}[5m]))\n) > 0.05\nand on() (sum(rate(http_requests_total{namespace=\"\
        diagnostics-example\",job=\"owned-app\"}[5m])) > 0)"
      for: 2m
      labels:
        severity: critical
    - alert: PodCrashLooping
      expr: max by (namespace,pod,container) (kube_pod_container_status_waiting_reason{namespace="diagnostics-example",reason="CrashLoopBackOff"}
        == 1)
      for: 5m
      labels:
        severity: warning
```

</details>

### 7. 哪种命令格式会在某节点上创建诊断 Pod？

A. `kubectl debug node/<node-name> --image=<reviewed-image>`
B. `kubectl exec node/<node-name> -- sh`
C. `kubectl attach node/<node-name>`
D. `kubectl run debug --node=<node-name>`

<details>
<summary>查看答案</summary>

**答案：A. `kubectl debug node/<node-name> --image=<reviewed-image>`**

已测试的通用配置会挂载 /host 并使用 host namespaces，但 privileged 为 false。显式的 sysadmin profile 会授予更广泛的权限；chroot/nsenter/tool/SELinux 行为取决于平台和权限。创建 Pod 是一种变更，不是被动检查；kubelet/运行时故障可能导致 Pod 无法启动。记录创建的名称/UID，并采用经过审查的清理流程。

```bash
# MUTATION: creates a node diagnostic Pod; general is not automatically privileged.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${NODE_NAME:?}"; : "${NODE_DEBUG_IMAGE:?Reviewed image}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" debug "node/$NODE_NAME" \
  --image="$NODE_DEBUG_IMAGE" --profile=general --attach=false -- true
```

</details>

### 8. 在分布式追踪中，Span 表示什么？

A. 仅表示端到端请求的总时长
B. 一个带有计时信息和相关元数据的工作单元
C. 仅表示网络延迟
D. 日志时间戳

<details>
<summary>查看答案</summary>

**答案：B. 一个带有计时信息和相关元数据的工作单元**

Span 可以描述 HTTP 调用、数据库操作或其他工作单元。Trace ID 用于关联 spans；父子关系和 links 表示相关工作。传播和采样决定实际能看到哪些内容。Baggage 是传播的上下文，不会自动成为 span 属性，也不得包含密钥。以下 JSON 是便于人阅读的示例记录，不是 OTLP 线上负载，也不是实测请求。配置 Collector 时，请使用当前 v1beta1 对象形式的源示例，以及受支持的后端/OTLP 路径；旧 jaeger exporter/14250 方案已不是当前指导。

```json
{
  "exampleOnly": true,
  "trace_id": "0123456789abcdef0123456789abcdef",
  "span_id": "0123456789abcdef",
  "parent_span_id": "fedcba9876543210",
  "name": "GET /api/products",
  "kind": "SERVER",
  "duration_ms": 85
}
```

</details>

### 9. 对基于 Deployment 的 CoreDNS，调查 DNS 错误时哪些证据有用？

A. 范围明确的 CoreDNS Pod 日志/状态以及工作负载 resolver 检查
B. 仅执行 describe service kubernetes
C. 仅查看 AWS 集群元数据
D. 仅查看旧版 Endpoints 列表

<details>
<summary>查看答案</summary>

**答案：A. 范围明确的 CoreDNS Pod 日志/状态以及工作负载 resolver 检查**

默认情况下，不会记录所有 DNS 查询。应关联 resolver 配置、Pod/Service 健康状况和上游错误。纯 Auto Mode 使用节点系统 DNS；混合集群仍会为非 Auto 节点保留 Deployment。工具可用时，应从相关 Pod/容器内测试，而不是从无关的 default 命名空间旧镜像 Pod 测试。特定工具的 nslookup debug 标志并非通用选项。

```bash
# Deployment-based CoreDNS only; use the Auto Mode path when applicable.
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods -l k8s-app=kube-dns -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=kube-dns --since=15m --tail=100
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- nslookup kubernetes.default.svc.cluster.local.
```

</details>

### 10. 哪个命令会从 resource-metrics API 显示 Pod 最近的资源样本？

A. kubectl describe pod
B. kubectl top pods
C. kubectl get pods -o wide
D. kubectl logs

<details>
<summary>查看答案</summary>

**答案：B. kubectl top pods**

kubectl top 需要可用的 metrics.k8s.io provider，常见实现是 Metrics Server。它报告近期采样的 CPU/内存数据，不是瞬时测量值，也不提供历史记录。指标缺失不等于使用量为零。应分别比较适用的 requests/limits；历史分析应使用监控后端。

```bash
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods --containers
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods --sort-by=memory
kubectl --context "$KUBE_CONTEXT" top nodes
```

</details>

## 简答题

### 1. 已启用的 EKS 控制平面日志使用什么 CloudWatch Logs 组名模式？

<details>
<summary>查看答案</summary>

**答案：** `/aws/eks/<cluster-name>/cluster`。必须为集群启用相应日志类型；启用日志不会恢复早前的事件。请选择正确的账户、区域、日志组和时间窗口。以下 Logs Insights QL 查询应分开运行。审计用户名是已记录的身份标识，不一定是简短的 IAM 角色名称。

```sql
fields @timestamp, @message
| filter @logStream like /kube-apiserver/
| filter @logStream not like /kube-apiserver-audit/
| filter @message like /error|Error|ERROR/
| sort @timestamp desc
| limit 50
```

```sql
fields @timestamp, user.username, verb, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter user.username = "REPLACE_WITH_EXACT_AUDIT_USERNAME"
| sort @timestamp desc
| limit 100
```

</details>

### 2. 当前 Kubernetes 是否要求启用旧版 EphemeralContainers feature gate？

<details>
<summary>查看答案</summary>

**答案：** 不需要。`EphemeralContainers` 是历史 feature gate；此功能在 1.23 成为 beta，并在 1.25 稳定。在当前版本中，应改为检查 `pods/ephemeralcontainers` 的 RBAC、准入策略、镜像访问和运行时支持。添加 ephemeral container 会更改 Pod，之后不能更改或移除该条目。`--target` 是否能看到进程取决于运行时支持。复用源章节中明确审查过的创建流程；以下命令只列出元数据。

```bash
# Read-only inventory; adding an ephemeral container is a separate mutation.
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE" \
  get pod "$POD_NAME" -o json | jq '{
    uid:.metadata.uid,
    ephemeralContainers:[.spec.ephemeralContainers[]? | {name,image,targetContainerName}],
    ephemeralStatuses:.status.ephemeralContainerStatuses
  }'
```

</details>

### 3. PromQL 中的 rate() 和 irate() 有何区别？

<details>
<summary>查看答案</summary>

`rate()` 根据选定范围估算 counter 每秒增量，处理 counter 重置，并向范围边界外推。`irate()` 只使用该范围内最后两个样本，也会处理重置。两者都需要足够的样本；都无法看到未采样的尖峰。应先对每条时间序列应用函数再聚合，这样仍能检测每条序列各自的重置。告警通常使用 `rate()`；`irate()` 可用于检查波动较大的 counter，但不保证更好地检测故障。这些是 counter 函数，不是通用 gauge 导数。前两个示例使用有埋点的应用程序 counter；最后一个返回 CPU 核数，而非百分比。使用单集群及源章节所述的标签/抓取约定。

```promql
sum by (namespace,service) (
  rate(http_requests_total{namespace="diagnostics-example",service="api-gateway"}[5m])
)
```

```promql
sum by (namespace,service) (
  irate(http_requests_total{namespace="diagnostics-example",service="api-gateway"}[5m])
)
```

```promql
rate(container_cpu_usage_seconds_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])
```

</details>

### 4. kubectl debug node 会将主机文件系统挂载到哪里？这允许执行什么操作？

<details>
<summary>查看答案</summary>

**答案：** `/host`。`general` profile 不会自动启用 privileged。挂载主机目录并不保证 `chroot`、`systemctl` 或读取受保护主机文件一定可行。镜像必须包含所需工具，准入策略、能力、SELinux、操作系统和节点健康状况也会产生影响。显式 privileged 的 `sysadmin` profile 需要单独获准的诊断流程。Auto Mode 支持文档说明的节点调试程序；直接 SSH 和普通主机路径并非通用方法。创建和清理请参见选择题 7 和源章节，切勿打印 kubeconfig 或凭证文件。

</details>

### 5. 如何分解事故恢复时间，同时避免重复计算？

<details>
<summary>查看答案</summary>

使用“MTTR”前先定义约定：有些团队从检测开始计时，另一些从事故开始计时；resolve、repair、recover 的含义也不同。这里定义 `t0 = service impact starts`（服务影响开始）、`t1 = detected`（检测到）、`t2 = actionable diagnosis`（得到可执行的诊断）、`t3 = service restored`（服务恢复）。不重叠的时间段分别是检测时间 `t1−t0`、调查时间 `t2−t1` 和恢复时间 `t3−t2`；三者相加等于 `t3−t0`。按这些定义对相同事故取平均，仍能保持总和。一宗 45 分钟的事故是一次持续时长，不是已证明的平均值。根因确认和后续工作可能发生在服务恢复之后，因此不要强行让每宗事故都套入此顺序。改进监控覆盖、运行手册和经过测试的恢复流程，并测量实际结果。

</details>

## 动手练习

### 1. 查找五分钟内估算重启增量至少为两次的 production 容器。

<details>
<summary>查看答案</summary>

使用单个集群和包含 `namespace`、`pod`、`uid`、`container` 标签的 kube-state-metrics。`increase()` 会处理 counter 重置并进行外推，因此结果可能是小数，也不是完整事件账本。`max` 可避免将相同的 exporter 副本相加，但不是通用的 HA 去重方案；请验证抓取健康状况和后端去重行为。保留 Pod UID，以便同名替代 Pod 仍可区分。以下变体依次显示生命周期计数 >5、一小时内按容器重启增量求和后排名前十的**Pod**，以及用于绘图的每秒速率。序列缺失不表示没有重启。

```promql
max by (namespace,pod,uid,container) (
  increase(kube_pod_container_status_restarts_total{namespace="production"}[5m])
) >= 2
```

```promql
max by (namespace,pod,uid,container) (
  kube_pod_container_status_restarts_total{namespace="production"}
) > 5
```

```promql
topk(10,
  sum by (namespace,pod,uid) (
    max by (namespace,pod,uid,container) (
      increase(kube_pod_container_status_restarts_total{namespace="production"}[1h])
    )
  )
)
```

```promql
max by (namespace,pod,uid,container) (
  rate(kube_pod_container_status_restarts_total{namespace="production"}[5m])
)
```

</details>

### 2. 在更改工作负载前，为处于 CrashLoopBackOff 的容器收集有范围限制的证据。

<details>
<summary>查看答案</summary>

`CrashLoopBackOff` 是容器的 waiting reason；Pod 的 phase 仍可能是 `Running`。选择实际 context、命名空间、Pod 和故障容器。收集日志前检查其当前 UID；按名称调用日志并不能保证与 UID 检查是原子操作。先执行以下有界检查。调查退出代码/原因、应用程序错误、配置引用、节点压力和依赖故障。startup/liveness probe 失败可能重启容器；只有 readiness 失败则不会。Secret/configuration 缺失也可能阻止容器创建，而不是导致 crash loop。不要输出所有环境变量、Secret 值或配置文件。

```bash
# Read-only, bounded evidence for one owned Pod and container.
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
k=(kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$NAMESPACE")
pod_state=$("${k[@]}" get pod "$POD_NAME" -o json | jq '{
  uid:.metadata.uid, phase:.status.phase, conditions:.status.conditions,
  containers:[.status.containerStatuses[]? | {name,ready,restartCount,state,lastState}],
  initContainers:[.status.initContainerStatuses[]? | {name,ready,restartCount,state,lastState}]
}')
printf '%s\n' "$pod_state"
pod_uid=$(jq -er '.uid' <<<"$pod_state")
"${k[@]}" get events --field-selector "involvedObject.uid=$pod_uid" \
  --sort-by='.metadata.creationTimestamp'
# These logs can contain sensitive application data; keep the terminal/evidence private.
# A missing previous instance/log is an evidence gap, not an empty successful result.
if ! "${k[@]}" logs "$POD_NAME" -c "$CONTAINER_NAME" --previous \
  --tail=100 --limit-bytes=65536 --timestamps; then
  printf '%s\n' 'Previous container log unavailable; retain this limitation.' >&2
fi
"${k[@]}" logs "$POD_NAME" -c "$CONTAINER_NAME" \
  --since=15m --tail=100 --limit-bytes=65536 --timestamps
```

如必须重现，只有在检查副本的身份、Secret 引用、卷、其他容器和外部副作用后，才能遵循选择题 2/源章节的说明。仅替换一个镜像/命令并禁用 init container 并不能隔离这些资源。优先在适当环境中创建已清理敏感数据的复现；记录新名称/UID，并单独审查清理操作。休眠的调试容器不能证明应用已修复。

</details>

### 3. 查询最近一小时内 EKS 审计日志中的 403 事件，并等待结果完成。

<details>
<summary>查看答案</summary>

必须已启用审计日志。选择所属账户/区域和 `/aws/eks/<cluster-name>/cluster`；在控制台中选择过去一小时的时间范围。每个代码块都是独立的 Logs Insights QL 查询。使用发现的 JSON 字段，不要假定键顺序固定。这些查询统计审计事件，不一定是唯一请求：一个审计 ID 可能对应重复的审计阶段。403 表示授权拒绝，本身不能证明具体 IAM/RBAC 策略是责任方。CLI 示例需要 AWS CLI、Bash、jq 和 Python；最多查询 100 条记录，并将结果保存在私有位置。只有 `Complete` 才是最终状态，即使运行中的查询已有结果行。轮询超时不会取消服务端查询。

```sql
fields @timestamp, user.username, verb, objectRef.namespace, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 403
| sort @timestamp desc
| limit 100
```

```sql
filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 403
| stats count(*) as deniedEvents by user.username, verb, objectRef.resource
| sort deniedEvents desc
| limit 100
```

```bash
# Read-only query with possible CloudWatch scan charges; no log configuration changes.
set -euo pipefail
umask 077
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"
evidence_dir=$(mktemp -d "$PWD/eks-audit403.XXXXXX")
printf 'Private evidence directory: %s\n' "$evidence_dir"
read -r start_epoch end_epoch < <(python3 - <<'PY'
import time
end = int(time.time())
print(end - 3600, end)
PY
)
query_string='fields @timestamp, user.username, verb, objectRef.namespace, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 403
| sort @timestamp desc
| limit 100'
query_id=$(aws logs start-query --region "$AWS_REGION" --no-cli-pager \
  --log-group-name "/aws/eks/$CLUSTER_NAME/cluster" \
  --start-time "$start_epoch" --end-time "$end_epoch" \
  --query-string "$query_string" --query queryId --output text)
if [[ ! "$query_id" =~ ^[0-9a-fA-F-]{36}$ ]]; then
  printf '%s\n' 'No valid query ID returned.' >&2
  exit 1
fi
printf '%s\n' "$query_id" > "$evidence_dir/query-id.txt"
for attempt in {1..15}; do
  aws logs get-query-results --region "$AWS_REGION" --no-cli-pager \
    --query-id "$query_id" --output json > "$evidence_dir/result.json"
  status=$(jq -er '.status' "$evidence_dir/result.json")
  case "$status" in
    Complete)
      printf 'Query complete; inspect private file %s/result.json\n' "$evidence_dir"
      exit 0
      ;;
    Scheduled|Running) sleep 2 ;;
    *)
      printf 'Query ended without complete results: %s\n' "$status" >&2
      exit 1
      ;;
  esac
done
printf 'Polling limit reached; query %s may still run. Partial results are not final.\n' "$query_id" >&2
exit 2
```

</details>

## 高级问题

### 1. 针对间歇性 API 延迟，制定结合追踪、指标和日志的策略。

<details>
<summary>查看答案</summary>

**1. 定义测量约定。** 使用单集群；`diagnostics-example` 命名空间中有埋点的 `api-gateway`；以及以秒为单位、带有有界 `endpoint` 标签和 `le="0.5"` bucket 的 classic histogram。确认 bucket 与 count 的序列范围一致。Kubernetes 不会自动提供这些应用程序指标。比较受影响的路由、流量量和时间范围。以下查询分别显示 p99、用于热图的累计 bucket rate，以及超过 0.5 秒的比例；仅相减 rate 会得到请求/秒，而不是比率。流量为零时，该比率没有定义。

```promql
histogram_quantile(0.99, sum by (le,namespace,service,endpoint) (
  rate(http_request_duration_seconds_bucket{namespace="diagnostics-example",service="api-gateway"}[5m])
))
```

```promql
sum by (le,namespace,service,endpoint) (rate(http_request_duration_seconds_bucket{namespace="diagnostics-example",service="api-gateway"}[1m]))
```

```promql
(
  (sum by (namespace,service,endpoint) (rate(http_request_duration_seconds_count{namespace="diagnostics-example",service="api-gateway"}[5m])) - sum by (namespace,service,endpoint) (rate(http_request_duration_seconds_bucket{namespace="diagnostics-example",service="api-gateway",le="0.5"}[5m])))
  / sum by (namespace,service,endpoint) (rate(http_request_duration_seconds_count{namespace="diagnostics-example",service="api-gateway"}[5m]))
)
and on (namespace,service,endpoint) (sum by (namespace,service,endpoint) (rate(http_request_duration_seconds_count{namespace="diagnostics-example",service="api-gateway"}[5m])) > 0)
```

**2. 检查 traces。** 在后端 UI 中选择服务 `api-gateway`、受影响的时间范围、时长 >2 秒以及相关操作，例如 `GET /api/products`。使用后端实际的属性名称检查错误 spans 和下游调用。这些是 UI 搜索条件，不是可导入的 Jaeger YAML 配置。先验证传播和采样；没有 span 并不能证明没有发生调用。不能简单地把并行 spans 的时长相加作为请求时长。

**3. 关联日志。** 如果结构化日志包含 `trace_id`，将占位符替换为实际 trace ID，并在所属的应用程序日志组/时间范围中单独运行以下 Logs Insights QL 查询。这需要应用程序埋点；避免记录令牌、请求正文或传播的密钥。关联结果只能缩小假设范围，不能证明因果关系。

```sql
fields @timestamp, @message
| filter trace_id = "REPLACE_WITH_ACTUAL_TRACE_ID"
| sort @timestamp asc
| limit 100
```

**4. 比较基础设施证据。** 以下查询依次返回 CPU throttled 秒/秒、接收字节/秒，以及 JVM GC pause 秒/秒。网络吞吐量**不是网络延迟**；如需测量延迟，应使用范围和标签正确的客户端/服务器 span，或经授权且有范围限制的 RTT 测试。GC pause rate 不是每个请求的延迟。指标名称/标签取决于 exporter 和运行时。应比较实际节点/Pod 和时间区间，而不是无关的集群总量。

```promql
rate(container_cpu_cfs_throttled_seconds_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])
```

```promql
rate(container_network_receive_bytes_total{namespace="diagnostics-example",pod!=""}[5m])
```

```promql
rate(jvm_gc_pause_seconds_sum{namespace="diagnostics-example",service="api-gateway"}[5m])
```

**5. 设计 dashboard。** 下表是 panel 设计，不是 Grafana 仪表板导入文件。使用已安装 Grafana 版本的编辑器/导出格式和实际 datasource UID。

| 面板 | 测量内容 |
|---|---|
| p50/p95/p99 延迟 | 分别使用 0.50、0.95 和 0.99 的三条 histogram-quantile 查询 |
| 按状态码统计请求率 | 对有埋点的请求 counter 计算 rate，并按实际状态标签分组 |
| 热图 | 使用匹配的 classic histogram bucket rates，保留 `le` 和路由范围 |
| 下游延迟 | 下游服务自己的 histogram 和标签约定 |
| Pod 资源 | CPU counter rate（核）；内存 working-set gauge（字节） |

```promql
rate(container_cpu_usage_seconds_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])
```

```promql
container_memory_working_set_bytes{namespace="diagnostics-example",container!="",container!="POD"}
```

**6. 评估对比告警。** 在 Prometheus 中选择此规则/命名空间并替换 release 标签。50% 阈值和五分钟 hold 只是示例，需要结合流量/SLO 调整。较长时间窗口的 p99 **不是一小时平均延迟**，且包含最近五分钟。此规则用于对比，并非预测模型。需要正数基线；缺失/NaN 数据不能证明健康。应分别检查数据收集和低流量情况，并测试通知是否送达。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: latency-comparison-example
  namespace: monitoring
  labels:
    release: REPLACE_WITH_SELECTED_PROMETHEUS_RELEASE
spec:
  groups:
  - name: latency-comparison-example
    rules:
    - record: diagnostics:http_duration_seconds:p99_5m
      expr: "histogram_quantile(0.99, sum by (le,namespace,service,endpoint) (\n \
        \ rate(http_request_duration_seconds_bucket{namespace=\"diagnostics-example\"\
        ,service=\"api-gateway\"}[5m])\n))"
    - record: diagnostics:http_duration_seconds:p99_1h
      expr: "histogram_quantile(0.99, sum by (le,namespace,service,endpoint) (\n \
        \ rate(http_request_duration_seconds_bucket{namespace=\"diagnostics-example\"\
        ,service=\"api-gateway\"}[1h])\n))"
    - alert: LatencyComparedWithLongerWindow
      expr: "(\n  diagnostics:http_duration_seconds:p99_5m\n  / diagnostics:http_duration_seconds:p99_1h\
        \ > 1.5\n)\nand on (namespace,service,endpoint) (diagnostics:http_duration_seconds:p99_1h\
        \ > 0)"
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Five-minute p99 exceeds one-hour p99 by over 50%; investigate.
```

应分别验证各项假设：特定端点行为、下游调用、CPU throttling、GC、网络路径和流量变化都需要相应证据。本次未测量到延迟下降，也未执行基准测试。

</details>

### 2. 为间歇性 NotReady 节点建立有证据支持的 RCA 流程。

<details>
<summary>查看答案</summary>

**1. 收集身份和时间信息。** 区分 `Ready=False` 与 heartbeat 丢失/`Unknown`。记录节点 UID、provider ID、操作系统/运行时版本、condition 转换时间和 lease 续订情况。事件保留时间有限；列表为空不能排除早前发生故障。已停止的节点可能根本无法进行 node-debug。

```bash
# Read-only scoped node evidence; confirm account/cluster/Region first.
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?}"
k=(kubectl --context "$KUBE_CONTEXT" --request-timeout=15s)
node_state=$("${k[@]}" get node "$NODE_NAME" -o json | jq '{
  uid:.metadata.uid,providerID:.spec.providerID,
  nodeInfo:.status.nodeInfo,conditions:.status.conditions
}')
printf '%s\n' "$node_state"
node_uid=$(jq -er '.uid' <<<"$node_state")
"${k[@]}" get events --all-namespaces \
  --field-selector "involvedObject.uid=$node_uid" --sort-by='.metadata.creationTimestamp'
"${k[@]}" -n kube-node-lease get lease "$NODE_NAME" \
  -o jsonpath='{.spec.renewTime}{"\n"}'
```

对于对应的 EC2 实例，`Maximum=1` 表示该时间桶中至少有一个状态检查样本失败。`Sum` 不是故障持续时间；数据点缺失也不代表成功。Fargate 和 Hybrid Nodes 需要各自的基础设施证据。

```bash
# EC2-backed nodes only: resolve the actual instance from providerID, not a guessed name.
: "${AWS_REGION:?}"; : "${INSTANCE_ID:?Verified EC2 instance ID}"
read -r start_time end_time < <(python3 - <<'PY'
from datetime import datetime, timedelta, timezone
end = datetime.now(timezone.utc)
print((end-timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"),
      end.strftime("%Y-%m-%dT%H:%M:%SZ"))
PY
)
aws cloudwatch get-metric-statistics --region "$AWS_REGION" --no-cli-pager \
  --namespace AWS/EC2 --metric-name StatusCheckFailed \
  --dimensions "Name=InstanceId,Value=$INSTANCE_ID" \
  --start-time "$start_time" --end-time "$end_time" --period 300 \
  --statistics Maximum --query 'sort_by(Datapoints,&Timestamp)'
```

**2. 收集适用的主机证据。** 使用经批准的主机访问、NodeDiagnostic，或源章节文档说明的 Auto Mode 诊断路径。`general` 不是 privileged chroot 快捷方式。以下读取操作适用于兼容的 systemd Linux 主机，不适用于所有调试镜像或 Bottlerocket/Auto Mode 路径。日志可能包含敏感数据；在另行审查修复方案前，应私下收集。

```bash
# Only inside an already authorized, compatible systemd Linux host context.
# These are bounded reads, not instructions to restart or prune the node.
journalctl -u kubelet --since '24 hours ago' -n 200 --no-pager
journalctl -u containerd --since '24 hours ago' -n 200 --no-pager
dmesg | tail -n 100
free -h
vmstat 1 5
cat /proc/pressure/memory /proc/pressure/cpu
```

**3. 检查相关网络路径。** 此请求使用选定的 kubeconfig 验证 TLS，且需要对 `/readyz` 的授权。它测试调用方的路径，不一定是故障节点的路径。401/403 证明收到 HTTP 响应，但不能证明就绪；DNS、超时和证书错误应分别诊断。不要使用 `curl -k` 隐藏信任问题。

```bash
# Uses the selected kubeconfig CA and authentication; do not disable TLS verification.
: "${KUBE_CONTEXT:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=10s get --raw='/readyz'
```

仅对标准 VPC CNI，检查实际 aws-node Pod 和受影响实例的 ENI。Auto Mode 使用其托管网络路径；不要仅凭缺少 DaemonSet 就推断故障。

```bash
# Standard VPC CNI on an EC2 node; choose the aws-node Pod on the affected node.
: "${KUBE_CONTEXT:?}"; : "${AWS_NODE_POD:?}"; : "${AWS_REGION:?}"; : "${INSTANCE_ID:?}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n kube-system \
  logs "$AWS_NODE_POD" -c aws-node --since=15m --tail=100 --limit-bytes=65536
aws ec2 describe-network-interfaces --region "$AWS_REGION" --no-cli-pager \
  --filters "Name=attachment.instance-id,Values=$INSTANCE_ID" \
  --query 'NetworkInterfaces[].{ENI:NetworkInterfaceId,Subnet:SubnetId,Status:Status,IPv4Prefixes:Ipv4Prefixes,PrivateIPs:PrivateIpAddresses[].PrivateIpAddress}'
```

**4. 解读资源信号。** 以下单集群查询显示内存余量、root 文件系统容量、系统线程上限利用率，以及实际 kubelet pressure condition。它们需要对应的 Node Exporter/kube-state-metrics 序列以及正确的主机挂载/标签。Node Exporter 默认禁用 `processes`；`node_processes_max_threads` 指 Linux `threads-max`。该比率既不是 kubelet 的 PIDPressure 判定，也不是容器的 `pids.max`。文件系统/inode/imagefs/cgroup 限制和抓取失败需要单独检查。这里的阈值只是示例，并非默认值。

```promql
(1 - node_memory_MemAvailable_bytes / (node_memory_MemTotal_bytes > 0)) * 100 > 90
```

```promql
(1 - node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|overlay"} / (node_filesystem_size_bytes{mountpoint="/",fstype!~"tmpfs|overlay"} > 0)) * 100 > 85
```

```promql
node_processes_threads / (node_processes_max_threads > 0) * 100 > 80
```

```promql
max by (node) (kube_node_status_condition{condition=~"MemoryPressure|DiskPressure|PIDPressure",status="true"}) == 1
```

**5. 验证假设。** 将内核 OOM 记录与被杀进程、工作负载内存和限制关联；将磁盘/inode 耗尽与受影响文件系统关联。在相同时间戳对照 kubelet/运行时日志、节点到 API 的可达性、CNI/IP 证据和 EC2 健康状态。内存高或探针失败本身不能证明内存泄漏或基础设施故障。

**6. 按实际计算模型防止复发。** Auto Mode 包含节点监控和修复功能。托管节点组需要检查其修复配置。自行管理的 Karpenter 修复需要兼容版本、`NodeRepair=true` 和适用的 condition/修复策略；诊断 Agent 可提供额外 conditions。当前 Karpenter 策略对 `Ready=False/Unknown` 允许 30 分钟；当 NodePool 中超过 20% 不健康时会阻止修复；修复可能强制终止，而非执行普通的优雅 drain。不要把自愿中断预算/PDB 视为通用修复保证。EKS 默认不会修复 `MemoryPressure`、`DiskPressure` 或 `PIDPressure`；应解决工作负载压力问题。这些 EKS 监控/修复功能仅适用于 Linux，且 Fargate 不提供监控 Agent。应使用源章节和当前 provider 配置，而不是部署不完整的特权 Node Problem Detector DaemonSet 或重复安装现有 Agent。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: node-health-example
  namespace: monitoring
  labels:
    release: REPLACE_WITH_SELECTED_PROMETHEUS_RELEASE
spec:
  groups:
  - name: node-health-example
    rules:
    - alert: NodeHighMemoryUse
      expr: (1 - node_memory_MemAvailable_bytes / (node_memory_MemTotal_bytes > 0))
        * 100 > 90
      for: 5m
      labels:
        severity: warning
    - alert: NodeRootFilesystemLowSpace
      expr: (1 - node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|overlay"}
        / (node_filesystem_size_bytes{mountpoint="/",fstype!~"tmpfs|overlay"} > 0))
        * 100 > 85
      for: 5m
      labels:
        severity: warning
    - alert: NodeNotReady
      expr: max by (node) (kube_node_status_condition{condition="Ready",status="true"})
        == 0
      for: 2m
      labels:
        severity: critical
```

Prometheus 必须选取这些规则；condition/exporter 序列缺失时，需要独立的收集/清单告警。容量告警没有命名为 kubelet pressure condition，因为它们测量的是不同信号。

若你管理可配置的 Linux kubelet，以下是**需要审查并合并到现有配置中的片段**，不是完整配置，也不是覆盖 EKS 节点文件的命令。使用操作系统/配置器支持的 bootstrap 机制。`mergeDefaultEvictionSettings` 会保留未指定的 hard defaults；否则部分覆盖可能把省略的阈值设为零。Soft threshold 需要匹配的 grace period，而 `evictionMaxPodGracePeriod` 会限制终止宽限期。示例值仍需结合工作负载/容量验证，不是 Auto Mode 定制说明。

```json
{
  "mergeDefaultEvictionSettings": true,
  "evictionHard": {
    "memory.available": "500Mi",
    "nodefs.available": "10%",
    "imagefs.available": "15%"
  },
  "evictionSoft": {
    "memory.available": "1Gi",
    "nodefs.available": "15%"
  },
  "evictionSoftGracePeriod": {
    "memory.available": "1m",
    "nodefs.available": "1m"
  },
  "evictionMaxPodGracePeriod": 60
}
```

**历史 RCA 模板：未经验证的示例，不是事故报告。** 保留原始日期、数量和原始地区对应的时区；PST 与 KST 示例并不声称表示同一时刻。源材料没有证据支持所称的内存泄漏、实际修复或完成状态。用于运维前，请用证据替换占位符。

```markdown
## Incident summary (illustrative)
- Start: 2024-01-15 14:30 PST
- Example impact: 3 nodes, 45 Pods
- Example restoration: 2024-01-15 15:15 PST (duration 45 minutes, not a measured mean)

## Example timeline (evidence required for every entry)
- 14:30 NodeNotReady alert
- 14:35 Investigation starts
- 14:50 Hypothesis: memory pressure killed kubelet; confirm with kernel/process evidence
- 15:00 Proposed drain/restart; record actual authorization, effects and data safety checks
- 15:15 Proposed restoration point; supply workload/SLO verification

## Root-cause hypothesis
A memory leak could exhaust node memory; not established by this template.

## Follow-up proposals (no completion asserted)
1. Validate application memory behavior and appropriate requests/limits.
2. Evaluate alert threshold change from 90% to 80% against noise and capacity.
3. Review existing node monitoring before considering Node Problem Detector.
```

</details>

**这些练习的主要参考资料：**

- [Prometheus functions](https://prometheus.io/docs/prometheus/latest/querying/functions/)
- [Karpenter disruption and node repair](https://karpenter.sh/docs/concepts/disruption/)
- [EKS node monitoring and repair](https://docs.aws.amazon.com/eks/latest/userguide/node-health.html)
- [Kubelet node-pressure eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [Node Exporter collectors](https://github.com/prometheus/node_exporter#disabled-by-default)
