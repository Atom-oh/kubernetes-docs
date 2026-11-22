# Kubernetes/EKS 故障排查手册：症状 → 诊断 → 原因 → 修复

> **原始示例记录的版本**：原始 Amazon EKS 1.36 输出示例（控制平面 v1.36.2-eks-bca9cf6，平台版本 eks.9，Karpenter 1.4，VPC CNI v1.21，CoreDNS v1.14）
> **最后审阅日期**：2026年9月11日

< [上一页：可用区集群运维](15-zonal-operations-guide.md) | [目录](./README.md) >

***

凌晨 3 点，寻呼器响起，你打开终端时，需要的不是概念说明，而是“**根据我眼下看到的情况，接下来该输入什么命令**。” 本文从**症状**而非概念入手。每种症状都在一个区块中汇总“你看到什么 → 运行什么 → 输出是什么样 → 最常见的原因及修复方法”。

以下输出展示的是原始 2026 年 9 月 2 日文档中记录的环境，以及官方文档中的信息。本次审阅没有重新运行该集群，也没有独立核验原始捕获的日志。特别要注意，[Karpenter 兼容性矩阵](https://karpenter.sh/docs/upgrading/compatibility/)要求 Kubernetes 1.36 使用 Karpenter 1.13 或更高版本。不要把记录的 1.4.0 组合重新用于受支持的部署。

深入的根因分析（控制平面日志、CloudWatch Logs Insights 查询、节点加入失败的八种原因等）已经在 [EKS 故障排查](../eks/09-eks-troubleshooting.md)和 [EKS 高级调试](../eks/11-eks-advanced-debugging.md)中介绍。本文位于这些文档之前：它的作用是**在 30 秒内决定该打开哪一篇文档**，因此会链接到相关文档，而不会重复其中的内容。

## 目录

1. [30 秒摘要：症状 → 首条命令 → 最常见原因](#30-second-summary-symptom--first-command--most-common-cause)
2. [诊断决策树](#diagnostic-decision-tree)
3. [按症状分类的故障排查手册](#playbook-by-symptom)
4. [kubectl 诊断速查表](#kubectl-diagnostic-cheat-sheet)
5. [深入排查：相关文档](#going-deeper-related-documents)
6. [参考资料](#references)

***

<span id="30-second-summary-symptom--first-command--most-common-cause"></span>

## 30 秒摘要：症状 → 首条命令 → 最常见原因

每个症状单元格都链接到下方对应的故障排查章节。

| 症状（`kubectl get pods`/`nodes` 显示的内容） | 首条命令 | 最常见原因 |
|---|---|---|
| [`Pending`](#1-pod-stuck-in-pending) | `kubectl describe pod <pod>` → Events 中的 `FailedScheduling` 消息 | 资源不足（`Insufficient cpu/memory`）、缺少容忍、nodeSelector 不匹配、PVC 未绑定 |
| [`ImagePullBackOff` / `ErrImagePull`](#2-imagepullbackoff--errimagepull) | `kubectl describe pod <pod>` → `Failed to pull image` 行 | 标签拼写错误、私有仓库身份验证失败（imagePullSecrets/节点 IAM）、ECR 区域/账户不匹配 |
| [`CrashLoopBackOff`](#3-crashloopbackoff-exit-137-oomkilled-probe-failures-config-errors) | `kubectl logs <pod> --previous` + 检查 `lastState.terminated` | 应用启动失败（exit 1）、`OOMKilled`（exit 137）、存活探针失败、缺少 ConfigMap/Secret |
| [`Running` 但 READY 为 `0/1`](#4-running-but-not-ready--empty-endpoints) | `kubectl describe pod <pod>` → `Readiness probe failed` | 就绪探针路径/端口错误、正在等待依赖项、sidecar 未就绪 |
| [请求始终无法到达 Service](#5-service-is-unreachable) | `kubectl get endpointslices -l kubernetes.io/service-name=<svc>` | 选择器标签不匹配、`targetPort` 错误、NetworkPolicy 阻断、CoreDNS 故障 |
| [节点 `NotReady`](#6-node-notready--kubelet-pressure-diskpressure-memorypressure-pidpressure) | `kubectl describe node <node>` → Conditions | kubelet 已停止/网络分区、`DiskPressure`、`MemoryPressure`、`PIDPressure` |
| [PVC `Pending`](#7-pvc-stuck-in-pending) | `kubectl describe pvc <pvc>` → Events | `WaitForFirstConsumer`（正常等待）、StorageClass 缺失/拼写错误、可用区不匹配 |
| [应用日志中出现 `AccessDenied`（AWS API）](#8-eks-irsa--pod-identity-accessdenied) | `kubectl get sa <sa> -o yaml` + 检查注入的凭证提供程序字段 | IRSA（IAM Roles for Service Accounts）注解/信任策略错误、缺少 Pod Identity 关联、Pod 未重启 |
| [卡在 `ContainerCreating` 并出现 `failed to assign an IP address`](#9-eks-enivpc-cni-ip-exhaustion) | `kubectl describe pod <pod>` → `FailedCreatePodSandBox` | 子网 IP 耗尽、节点达到 max-pods 上限、`aws-node` 不健康 |
| [Karpenter 未启动节点](#10-eks-karpenter-does-not-launch-a-node) | `kubectl get events -A --field-selector reason=FailedScheduling` | NodePool 的 `limits` 已达到、requirements/taint 不匹配、实例类型限制 |
| [创建 Service 时因 `failed calling webhook` 被拒绝](#11-no-service-can-be-created-failed-calling-webhook) | `kubectl -n kube-system get endpointslices -l kubernetes.io/service-name=aws-load-balancer-webhook-service` | 在匹配所有命名空间的 `failurePolicy: Fail` webhook 后方，Webhook Deployment 不健康（CrashLoop） |

***

## 诊断决策树

![用于区分节点分配、镜像和设置等待、反复退出、Pod Ready 状态以及 EndpointSlice/网络诊断的决策树。](../.gitbook/assets/en-ops-16-troubleshooting-playbook-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-16-troubleshooting-playbook-0.html)

先确认上下文和命名空间。将 `<pod>` 和 `<ns>` 等占位符替换为实际值。Pod phase 与容器状态不同：排除所有 `Running` Pod 会漏掉一些 CrashLoop 和就绪探针故障。下面的查询排除了已完成的 Pod，并筛选出异常 phase 或 Ready 条件缺失/为 false 的 Pod。

```bash
# Inspect phase and Ready condition together
kubectl get pods -A -o json | jq -r '
  .items[]
  | select(.status.phase != "Succeeded")
  | select(.status.phase != "Running" or
      ([.status.conditions[]? | select(.type == "Ready" and .status == "True")] | length == 0))
  | [.metadata.namespace, .metadata.name, .status.phase,
     ([.status.initContainerStatuses[]?, .status.containerStatuses[]?
       | .state.waiting.reason // empty] | join(","))] | @tsv
'

# Recent Warning events (cluster-wide, sorted by lastTimestamp)
kubectl get events -A --field-selector type=Warning --sort-by=.lastTimestamp | tail -30
```

***

## 按症状分类的故障排查手册

<span id="1-pod-stuck-in-pending"></span>

### 1. Pod 卡在 `Pending`

**症状**：`Pending` 既可能表示正在等待调度，也可能表示正在下载镜像/设置容器。先检查 `.spec.nodeName` 和 `PodScheduled` 条件。对于尚未绑定节点的 Pod，检查调度事件；对于已绑定节点的 Pod，检查容器、挂载和 CNI 状态。

**诊断**：对于尚未调度的 Pod，检查 `FailedScheduling`。该消息按失败原因汇总节点数量；不同分组可能存在重叠。

```bash
kubectl describe pod <pod> -n <ns> | sed -n '/^Events:/,$p'
```

```
Warning  FailedScheduling  default-scheduler  0/15 nodes are available: 1 Insufficient cpu, 1 Insufficient memory,
  6 node(s) didn't match Pod's node affinity/selector, 8 node(s) had untolerated taint(s).
  no new claims to deallocate, preemption: 0/15 nodes are available:
  1 No preemption victims found for incoming pod, 14 Preemption is not helpful for scheduling.
```

不要仅凭这段摘要就推断 CPU 和内存不足一定发生在同一个节点上，也不要推断恰好有一个节点满足所有其他约束。[调度器聚合代码](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/scheduler/framework/types.go)可能会对同一节点计入多个原因。请对照实际节点标签、污点和资源分配情况；结合 ResourceClaim 的使用情况解读 DRA 消息。

**原因和修复方法**：

| 消息片段 | 原因 | 修复方法 |
|---|---|---|
| `Insufficient cpu` / `Insufficient memory` | 请求量超过节点剩余容量 | 调整请求量，检查自动扩缩器（→ [10. Karpenter](#10-eks-karpenter-does-not-launch-a-node)），检查 `kubectl describe node` 中的 `Allocated resources` |
| `Too many pods` | 节点达到配置的 max-pods 上限；应单独检查 CNI IP 容量 | → [9. ENI/IP 耗尽](#9-eks-enivpc-cni-ip-exhaustion) |
| `node(s) had untolerated taint(s)` | 没有容忍节点污点 | 使用 `kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints[*].key` 列出污点，然后添加容忍或调整 NodePool |
| `node(s) didn't match Pod's node affinity/selector` | 没有节点带有所需的 nodeSelector/affinity 标签 | 检查 `kubectl get nodes --show-labels`。使用 Karpenter 时，检查 NodePool 模板标签或 requirements 提供的众所周知的键和值 |
| `pod has unbound immediate PersistentVolumeClaims` | PVC 处于 `Pending` 状态 | → [7. PVC Pending](#7-pvc-stuck-in-pending) |
| `node(s) had volume node affinity conflict` | PV（EBS）所在的可用区没有可调度节点 | 查看 PV 的 `nodeAffinity` 可用区，并在该可用区提供容量 |
| `node(s) didn't match pod topology spread constraints` / `pod anti-affinity rules` | 没有节点满足拓扑分布约束 | 添加合适的节点。对于拓扑分布约束，只有在审查可用性目标后才考虑使用 ScheduleAnyway；Pod 反亲和性有单独的 required/preferred 规则 |
| 完全没有事件 | 调度器有问题，或 `schedulerName` 拼写错误 | 检查 `kubectl get pod <pod> -o jsonpath='{.spec.schedulerName}'` |

<span id="2-imagepullbackoff--errimagepull"></span>

### 2. `ImagePullBackOff` / `ErrImagePull`

**症状**：STATUS 最初显示 `ErrImagePull`，重试几次后变成 `ImagePullBackOff`。kubelet 的拉取退避时间会逐渐增加，最高为 5 分钟。

**诊断**：

```bash
kubectl describe pod <pod> -n <ns> | grep -A2 -E "Failed to pull|Back-off pulling"
kubectl get pod <pod> -n <ns> -o jsonpath='{range .spec.containers[*]}{.name}{"\t"}{.image}{"\n"}{end}'
kubectl get pod <pod> -n <ns> -o jsonpath='{.spec.imagePullSecrets}'
```

```
Warning  Failed   kubelet  Failed to pull image "123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/app:v1.2.3": ... not found
Warning  Failed   kubelet  Error: ErrImagePull
Normal   BackOff  kubelet  Back-off pulling image "123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/app:v1.2.3"
Warning  Failed   kubelet  Error: ImagePullBackOff
```

健康的拉取会留下 `Pulling image "..."` → `Successfully pulled image "..." in 4.501s ...` 这一对日志；如果镜像已缓存，则会记录 `Container image "..." already present on machine`。拉取成功可以证明镜像已下载，但不能排除镜像内容、架构或入口点方面的问题。

**原因和修复方法**：

| `Failed to pull image` 后面的内容 | 原因 | 修复方法 |
|---|---|---|
| `not found` / `manifest unknown` | 标签拼写错误、标签尚未推送、仓库错误 | 使用 `aws ecr describe-images --repository-name <repo> --image-ids imageTag=<tag>` 验证 |
| `401 Unauthorized` / `no basic auth credentials` | 私有仓库身份验证失败 | 对于 ECR，节点 IAM 角色需要 `AmazonEC2ContainerRegistryPullOnly`（或 `ReadOnly`）；对于外部仓库，请检查 `imagePullSecrets` |
| 从另一个 ECR 区域/账户拉取失败 | 地址不同本身并非错误；应检查跨账户策略和区域端点访问 | 将拉取主体添加到 ECR 仓库策略中 |
| `dial tcp ... i/o timeout` | 私有子网没有 NAT/VPC 端点 | 检查 `com.amazonaws.<region>.ecr.api`、`ecr.dkr` 和 S3 网关端点 |
| `toomanyrequests` | Docker Hub 限流 | 通过 ECR 拉取缓存进行镜像 |

诊断节点时，先检查 kubelet 事件/日志以及用于拉取镜像的凭证提供程序。`crictl pull` 不会自动复用 kubelet 的 ECR 凭证提供程序或 Pod 的 imagePullSecrets，因此无法复现相同的身份验证路径。Fargate 拉取镜像时使用 Pod 执行角色，与应用的 IRSA 角色分开。

<span id="3-crashloopbackoff-exit-137-oomkilled-probe-failures-config-errors"></span>

### 3. `CrashLoopBackOff`（exit 137 `OOMKilled`、探针失败、配置错误）

**症状**：容器反复退出，RESTARTS 数字不断增加。通常退避时间会从 10 秒开始翻倍，最高达到 300 秒，但 feature gate 和 kubelet 配置可能会改变这一行为。请检查 [Pod 生命周期](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)中的重启策略。

**诊断**：按顺序检查三项：**终止原因和退出码**、**上一个容器的日志**、**Events**。

```bash
# (1) Why did it die: lastState.terminated
kubectl get pod <pod> -n <ns> -o jsonpath='{range .status.containerStatuses[*]}{.name}{"\t"}restarts={.restartCount}{"\t"}reason={.lastState.terminated.reason}{"\t"}exit={.lastState.terminated.exitCode}{"\n"}{end}'

# (2) Logs right before death (the previous container, not the current one)
kubectl logs <pod> -n <ns> -c <container> --previous --tail=100

# (3) Probe/kill events
kubectl describe pod <pod> -n <ns> | sed -n '/^Events:/,$p'
```

原始文档中记录的一个容器输出，其内存限制为 128Mi：

```
    Last State:     Terminated
      Reason:       OOMKilled
      Exit Code:    137
      Started:      Mon, 31 Aug 2026 08:55:27 +0000
      Finished:     Tue, 01 Sep 2026 21:13:37 +0000
    Restart Count:  3
```

大约 36 小时的运行时间与即时启动失败不同；但这并不能证明存在内存泄漏。还应使用内存时间序列以及内核/cgroup 事件，排查流量峰值、批处理任务、节点 OOM 和限制变更。

**解读退出码**：

| 退出码 | 原因 | 含义 | 修复方法 |
|---|---|---|---|
| `0` | `Completed` | 进程正常退出；在 Deployment 中，这表示应用没有以前台方式持续运行 | 让长时间运行的入口进程保持前台运行，或改用 Job |
| `1` | `Error` | 应用自行退出（配置错误、依赖连接失败） | 堆栈跟踪位于 `logs --previous` 中 |
| `126` | `Error` | shell 入口点下找到了命令，但无法执行：缺少执行权限位，或者 shell 报告 `cannot execute binary file: Exec format error`（架构不匹配） | 在 Dockerfile 中运行 `chmod +x`；使用 `kubectl get nodes -L kubernetes.io/arch` 检查 arm64/amd64，并使用多架构镜像 |
| `127` | `Error` | shell 入口点下找不到命令：路径拼写错误，或二进制文件从未复制到最终镜像阶段 | 将 `command`/`args` 与镜像中的实际内容进行比较（`kubectl debug ... -- ls <path>`） |
| `137` | `OOMKilled` | OOM 终止；区分容器限制与节点内存压力 | 提高限制或修复泄漏。对于 JVM，检查 `-XX:MaxRAMPercentage` → [资源优化](10-resource-optimization.md) |
| `137` | `Error` | 因其他原因收到 SIGKILL：存活探针失败，且容器未能在 `terminationGracePeriodSeconds` 内退出 | 检查 preStop/优雅关闭 |
| `143` | `Error` | 收到 SIGTERM 后退出（可能是正常滚动更新/驱逐） | 如果反复发生，请在 Events 中查明是谁终止了它 |

- 如果镜像直接执行二进制文件（中间没有 shell），架构不匹配根本不会产生退出码 126。容器不会启动，`lastState.terminated` 会显示原因 `StartError`，消息中包含 `exec format error`。修复方法相同：使用多架构镜像，或通过 `kubernetes.io/arch` 设置 nodeSelector。

**探针失败**：这些事件表示存活探针失败触发了重启。原因包括路径/端口错误，也可能是真正的应用故障、过载或死锁。放宽探针配置之前，先检查响应和应用状态。

```
Warning  Unhealthy  kubelet  Liveness probe failed: HTTP probe failed with statuscode: 503
Normal   Killing    kubelet  Container app failed liveness probe, will be restarted
```

- 如果应用启动较慢，应添加 **`startupProbe`**，而不是增大存活探针的 `initialDelaySeconds`（只有 startup probe 成功后，存活探针才会启动）。
- 如果出现类似 `Readiness probe failed: dial tcp 10.0.2.45:8080: connect: connection refused` 的 TCP 拒绝，首先应检查容器端口和探针端口是否不同。

**配置引用错误**：严格来说，这不属于崩溃循环；Pod 会停在 `CreateContainerConfigError` 状态。

```
Warning  Failed  kubelet  Error: configmap "app-config" not found
Warning  Failed  kubelet  Error: secret "db-credentials" not found
```

使用 `kubectl get cm,secret -n <ns>` 对照名称和命名空间即可。如果引用用于卷挂载，则会显示为 `FailedMount` 事件（`MountVolume.SetUp failed for volume "cfg" : configmap "app-config" not found`）。

<span id="4-running-but-not-ready--empty-endpoints"></span>

### 4. `Running` 但未 Ready / Endpoints 为空

**症状**：STATUS 为 `Running`，但 READY 是 `0/1`（有 sidecar 时为 `1/2`）。普通 Service 路由会排除未就绪的端点。应另行检查 publishNotReadyAddresses、正在终止的端点和 LB fail-open 等例外情况；客户端可能会遇到错误或超时，具体取决于代理。

**诊断**：

```bash
kubectl describe pod <pod> -n <ns> | grep -E "Ready|Readiness probe"
kubectl get endpointslices -n <ns> -l kubernetes.io/service-name=<svc>
```

**EndpointSlice 的地址和就绪状态是分开的。** 匹配的未就绪 Pod 可能会带有地址，并显示 `ready: false`。不要根据 ENDPOINTS 列推断就绪状态；应检查 `ready`、`serving` 和 `terminating`。

```bash
kubectl get endpointslices -n <ns> -l kubernetes.io/service-name=<svc> -o json | jq -r '
  .items[] as $slice | $slice.endpoints[]?
  | [$slice.metadata.name, (.addresses | join(",")), (.conditions | tojson)] | @tsv
'
```

未设置的 `ready` 表示状态未知，消费者必须将其解读为就绪。`publishNotReadyAddresses: true` 会改变就绪状态筛选；代理也可以在端点终止期间处理仍在提供服务的端点。对于没有选择器的 Service，请手动检查 EndpointSlice。自 Kubernetes 1.33 起，v1 Endpoints API 已弃用；新的诊断应使用 EndpointSlice。

**原因和修复方法**：

| 观察结果 | 原因 | 修复方法 |
|---|---|---|
| Events 中反复出现 `Readiness probe failed` | 探针路径/端口错误，或应用仍在等待依赖项（数据库等） | 将探针指向应用实际的健康检查端点。依赖项等待应放在 readiness 中，而不是 liveness 中 |
| Condition 为 `Ready False`，原因是 `ReadinessGatesNotReady` | 正在等待 Pod 就绪门控，通常是 AWS Load Balancer Controller 的 `target-health.elbv2.k8s.aws/*` 门控 | 查明 Target Group 健康检查失败的原因 → [AWS Load Balancer Controller](../networking/03-aws-lb-controller.md) |
| `1/2` Running，只有应用容器 Ready | sidecar（如 istio-proxy）未就绪，或 sidecar 在应用之后启动且初始连接失败 | 检查 sidecar 日志；检查注入器/版本支持的启动顺序和就绪状态；仅进行 native-sidecar 转换不能解决就绪问题 |
| Ready，但 EndpointSlice 为空 | Service 选择器与 Pod 标签不匹配 | → [5. Service 无法访问](#5-service-is-unreachable) |

<span id="5-service-is-unreachable"></span>

### 5. Service 无法访问

**症状**：容器显示 `1/1 Running`，但 `curl http://<svc>.<ns>.svc.cluster.local` 超时或报告连接被拒绝，或者名称解析失败。

**将诊断拆分为三层**：(a) Service → Pod 映射，(b) 网络策略，(c) DNS。

```bash
# (a) Compare the selector with actual labels
kubectl get svc <svc> -n <ns> -o jsonpath='{.spec.selector}{"\n"}{.spec.ports}{"\n"}'
kubectl get pods -n <ns> -l <key>=<value> -o wide
kubectl get endpointslices -n <ns> -l kubernetes.io/service-name=<svc>

# (b) NetworkPolicies applied to the namespace
kubectl get networkpolicies -n <ns>
kubectl describe networkpolicy <policy> -n <ns>

# (c) CoreDNS status and logs
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl logs -n kube-system -l k8s-app=kube-dns --tail=50
kubectl get cm -n kube-system coredns -o jsonpath='{.data.Corefile}'
```

**原因和修复方法**：

| 观察结果 | 原因 | 修复方法 |
|---|---|---|
| 选择器是 `{"app":"api"}`，但 Pod 的标签是 `app=api-server` | 标签不匹配 → EndpointSlice 为空 | 统一标签/选择器。在 Helm Chart 中，`selectorLabels` 和 `podLabels` 不一致是常见原因 |
| EndpointSlice 中有 IP，但出现 `connection refused` | `targetPort` 与容器实际监听的端口不同 | 使用 `kubectl get pod <pod> -n <ns> -o jsonpath='{.spec.containers[*].ports}'` 进行对比。应用只绑定到 `127.0.0.1` 时也会出现相同症状 |
| 只从特定命名空间访问失败 | 存在 `default-deny` NetworkPolicy，但缺少允许入站的规则 | 检查 `podSelector`/`namespaceSelector`。使用 VPC CNI 网络策略时，`kubectl get policyendpoints -n <ns>` 会显示实际生效的内容 → [网络策略](../security/04-network-policies.md) |
| `nslookup <svc>` 返回 `NXDOMAIN` | 在其他命名空间中使用了短名称，或 CoreDNS 故障 | 使用 FQDN（`<svc>.<ns>.svc.cluster.local`）。确认 CoreDNS Pod 处于 `Running` 状态，并且 `/etc/resolv.conf` 中的 `nameserver` 是 kube-dns ClusterIP（在此集群中为 `172.20.0.10`） |
| 外部域名解析缓慢 | 使用默认的 `ndots:5` 时，任何点号少于 5 个的名称都会先尝试与每个搜索域（`<ns>.svc.cluster.local`、`svc.cluster.local`、`cluster.local`、节点的 VPC 域名）拼接后查询，之后才会作为绝对名称查询 | 在外部名称末尾添加 `.`，或者检查 dnsConfig.options 中名为 ndots、字符串值为 "2" 的条目 |
| 通过部分节点访问 NodePort/LB 才能成功 | 使用了 `externalTrafficPolicy: Local`，但该节点上没有 Pod | 这是预期行为。只有在审查客户端 IP 保留和跨节点流量后，才考虑使用 Cluster |

要从 Pod 的视角复现 DNS 查询，请启动一个临时 Pod：`kubectl run -it --rm dns-test --image=busybox:1.36 --restart=Never -- nslookup kubernetes.default.svc.cluster.local`。CoreDNS 概念和 Corefile 见[服务和网络](../core/03-services-networking.md#coredns)。

同时检查目标端入站和源端出站 NetworkPolicy。声明 containerPort 并不会创建监听套接字；请检查应用日志或套接字状态。使用 NodeLocal DNSCache 时，resolv.conf 可以正确地配置为使用不同于 kube-dns ClusterIP 的 nameserver。

**Auto Mode DNS：**[当前 Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html) 将 CoreDNS 作为节点系统服务运行。在纯 Auto Mode 环境中，单凭缺少 kube-dns Pod/Service 并不能说明发生了故障。混合集群中的普通节点仍需要 CoreDNS Deployment。上面的 Pod/ConfigMap 命令用于检查基于 Deployment 的 DNS；对于 Auto Mode，请检查实际 Pod 名称解析、节点 DNS 日志和上游解析器的可达性。

<span id="6-node-notready--kubelet-pressure-diskpressure-memorypressure-pidpressure"></span>

### 6. 节点 `NotReady` / kubelet 压力（`DiskPressure`、`MemoryPressure`、`PIDPressure`）

**症状**：`kubectl get nodes` 显示 `NotReady`，或者节点为 `Ready`，但 Pod 被 `Evicted`，或新 Pod 因 `node(s) had untolerated taint(s)` 而避开该节点。

**诊断**：

```bash
# One-line summary of node conditions
kubectl get nodes -o custom-columns='NAME:.metadata.name,READY:.status.conditions[?(@.type=="Ready")].status,MEM:.status.conditions[?(@.type=="MemoryPressure")].status,DISK:.status.conditions[?(@.type=="DiskPressure")].status,PID:.status.conditions[?(@.type=="PIDPressure")].status'

# Conditions with their reason
kubectl get node <node> -o jsonpath='{range .status.conditions[*]}{.type}{"="}{.status}{" ("}{.reason}{")\n"}{end}'

# Taints the node picked up automatically
kubectl get node <node> -o jsonpath='{.spec.taints}'
```

健康节点的输出（安装 EKS Node Monitoring Agent 后，还会看到 `ContainerRuntimeReady`/`NetworkingReady`/`KernelReady`/`StorageReady` 条件）：

```
MemoryPressure=False (KubeletHasSufficientMemory)
DiskPressure=False (KubeletHasNoDiskPressure)
PIDPressure=False (KubeletHasSufficientPID)
Ready=True (KubeletReady)
ContainerRuntimeReady=True (ContainerRuntimeIsReady)
NetworkingReady=True (NetworkingIsReady)
KernelReady=True (KernelIsReady)
StorageReady=True (DiskIsReady)
```

**原因和修复方法**：

| 条件/原因 | 自动添加的污点 | 原因 | 修复方法 |
|---|---|---|---|
| `Ready=Unknown`（`NodeStatusUnknown`，“Kubelet stopped posting node status.”） | `node.kubernetes.io/unreachable` | kubelet 进程崩溃、实例停止/网络分区、API server 身份验证失败 | 检查 EC2 实例状态 → 如果节点有响应，使用受支持的日志访问方式；kubelet 已停止的节点可能无法启动调试 Pod |
| `Ready=False` | `node.kubernetes.io/not-ready` | 容器运行时已停止、CNI 未初始化（`aws-node` 不健康） | 使用 `kubectl get pods -n kube-system -l k8s-app=aws-node -o wide` 检查该节点上的 aws-node |
| `DiskPressure=True`（`KubeletHasDiskPressure`） | `node.kubernetes.io/disk-pressure` | 镜像缓存/容器日志占满根卷 | 运行 `crictl rmi --prune`，轮转日志，扩展根 EBS。Pod 会因 `The node was low on resource: ephemeral-storage` 而被 `Evicted` |
| `MemoryPressure=True`（`KubeletHasInsufficientMemory`） | `node.kubernetes.io/memory-pressure` | 实际用量超过预留量，或系统预留量不足；未指定 request 的 limit 可能会被默认用作 request | 使用 LimitRange 强制设置 requests，检查 `kube-reserved`/`system-reserved` |
| `PIDPressure=True`（`KubeletHasInsufficientPID`） | `node.kubernetes.io/pid-pressure` | 派生进程激增（线程泄漏） | 找到并重启导致问题的 Pod，设置 `podPidsLimit` |

下面的命令会创建一个特权调试 Pod，并假设使用的是常规 Linux 工作节点，且主机上提供 shell、journalctl 和 crictl。不要假设在不可变的 Bottlerocket/EKS Auto Mode 主机上使用相同的 chroot 流程也有效。请使用 [Auto Mode 故障排查](https://docs.aws.amazon.com/eks/latest/userguide/auto-troubleshoot.html)中的调试容器和控制台日志流程。

```bash
kubectl debug node/<node> -it --image=busybox --profile=sysadmin -- chroot /host
# once inside
journalctl -u kubelet --since "10 min ago" | tail -50
df -h /var/lib/containerd
crictl ps -a | head
```

如果节点**从未出现在** `kubectl get nodes` 中（加入失败：IAM 角色/访问条目、子网路由、安全组、AMI 不匹配），这是另一个问题 → [EKS 高级调试：节点加入失败诊断](../eks/11-eks-advanced-debugging.md#node-join-diagnosis)、[EKS 故障排查：节点和 Pod 问题](../eks/09-eks-troubleshooting.md#node-and-pod-issues)。对于 Karpenter 节点，请先按照[第 10 节](#10-eks-karpenter-does-not-launch-a-node)检查 NodeClaim。

<span id="7-pvc-stuck-in-pending"></span>

### 7. PVC 卡在 `Pending`

**症状**：`kubectl get pvc` 显示 `Pending`，使用该 PVC 的 Pod 也处于 `Pending`，并显示 `pod has unbound immediate PersistentVolumeClaims`。

**诊断**：

```bash
kubectl get pvc -n <ns>
kubectl describe pvc <pvc> -n <ns> | sed -n '/^Events:/,$p'
kubectl get storageclass
kubectl get pods -n kube-system -l app=ebs-csi-node -o wide     # is the CSI node plugin on that node?
```

```
NAME   PROVISIONER             RECLAIMPOLICY   VOLUMEBINDINGMODE      ALLOWVOLUMEEXPANSION   AGE
gp2    kubernetes.io/aws-ebs   Delete          WaitForFirstConsumer   false                  145d
gp3    ebs.csi.aws.com         Delete          WaitForFirstConsumer   true                   76d
```

StorageClass 列表只是环境示例。请区分 Auto Mode 的 ebs.csi.eks.amazonaws.com 与单独安装的 ebs.csi.aws.com 驱动。在 Auto Mode 中，普通 ebs-csi-node DaemonSet 缺失本身并不代表故障。显式设置 storageClassName: "" 表示不使用默认 StorageClass；这与省略该字段不同。

**原因和修复方法**：`describe pvc` 中的 Events 消息就是诊断依据。

| Events 消息 | 原因 | 修复方法 |
|---|---|---|
| `WaitForFirstConsumer: waiting for first consumer to be created before binding` | **正常情况。** `volumeBindingMode: WaitForFirstConsumer` 会将卷创建推迟到 Pod 已调度之后 | 如果 PVC 因尚无 Pod 使用它而处于 Pending 状态，请保持不变。如果 Pod 也处于 Pending，请查看 Pod 的 `FailedScheduling` |
| `FailedBinding: no persistent volumes available for this claim and no storage class is set` | 没有设置 `storageClassName`，且没有默认 StorageClass | 在 PVC 上设置 `storageClassName: gp3`，或为某个 SC 添加注解 `storageclass.kubernetes.io/is-default-class: "true"` |
| `ProvisioningFailed: storageclass.storage.k8s.io "<name>" not found` | StorageClass 拼写错误，清单从其他集群复制而来 | 使用 `kubectl get sc` 查到的真实名称 |
| `ProvisioningFailed: error generating accessibility requirements: no topology key found for node <node>` | Pod 所在节点上的 EBS CSI 节点插件尚未注册（`CSINode` 中没有驱动） | 检查 `kubectl get csinode <node>` 的 DRIVERS 列；确认该节点上的 `ebs-csi-node` DaemonSet 正在运行 |
| `ProvisioningFailed` + `UnauthorizedOperation`/`AccessDenied` | EBS CSI 控制器的 IRSA/Pod Identity 缺少权限 | → [8. IRSA/Pod Identity](#8-eks-irsa--pod-identity-accessdenied)（相关主体为 `ebs-csi-controller-sa`） |
| Pod 侧出现 `node(s) had volume node affinity conflict` | 现有 PV（EBS）位于 `ap-northeast-2a` 可用区，但可调度节点位于其他可用区 | EBS 卷不能跨可用区。使用 `kubectl get pv <pv> -o jsonpath='{.spec.nodeAffinity}'` 查看可用区，并在该处提供容量（NodePool 可用区要求或 nodeSelector） |
| Pod 侧出现 `FailedAttachVolume: Multi-Attach error for volume` | RWO 卷仍连接到先前的节点上（StatefulSet 在节点故障后重新调度） | 使用 `kubectl get volumeattachments` 检查过期的挂载。如果节点已不存在，请等待几分钟以便清理 |

`WaitForFirstConsumer`、StorageClass 和动态置备的概念见[存储](../core/04-storage.md#storage-classes)；EBS/EFS CSI 错误模式见 [EKS 高级调试：存储故障排查](../eks/11-eks-advanced-debugging.md#6-storage-troubleshooting)。

<span id="8-eks-irsa--pod-identity-accessdenied"></span>

### 8. EKS：IRSA / Pod Identity `AccessDenied`

**症状**：Pod 正常处于 `Running`，但应用日志中出现 AWS SDK 错误。

```
An error occurred (AccessDenied) when calling the AssumeRoleWithWebIdentity operation:
  Not authorized to perform sts:AssumeRoleWithWebIdentity
```

也可能是 S3/DynamoDB 调用本身被拒绝，错误类似 `... is not authorized to perform: s3:GetObject`，且被拒绝的主体不是服务账户角色，而是**节点 IAM 角色**（`assumed-role/<node-role>/i-0abc...`）。这表明 SDK 选择了节点凭证。请检查注入情况、SDK 版本、提供程序优先级和显式凭证；如果 IMDS 访问被阻止，则无法回退到节点角色。

**诊断**：首先确定使用的是哪种机制。Pod 的环境变量会告诉你答案。

```bash
# Service account annotation (IRSA)
kubectl get sa <sa> -n <ns> -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}{"\n"}'

# Credential-related env injected into the pod
kubectl get pod <pod> -n <ns> -o json | jq -r '
  (.spec.initContainers[]?, .spec.containers[]?) as $container
  | $container.env[]?
  | select(.name == "AWS_ROLE_ARN" or .name == "AWS_WEB_IDENTITY_TOKEN_FILE"
        or .name == "AWS_CONTAINER_CREDENTIALS_FULL_URI"
        or .name == "AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE")
  | [$container.name, .name, (.value // "valueFrom")] | @tsv
'
```

| 注入的环境变量 | 机制 | 含义 |
|---|---|---|
| `AWS_ROLE_ARN=arn:aws:iam::...:role/<role>` + `AWS_WEB_IDENTITY_TOKEN_FILE=/var/run/secrets/eks.amazonaws.com/serviceaccount/token` | **IRSA** | 由 pod-identity-webhook 注入。如果缺少这些变量，则可能是在创建 Pod **之后**才添加 SA 注解，或者 SA 名称不一致 |
| `AWS_CONTAINER_CREDENTIALS_FULL_URI` + `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE` | **EKS Pod Identity** | `eks-pod-identity-agent` 在 `169.254.170.23` 提供凭证。只有存在关联时才会注入 |
| 两者都没有 | 其他提供程序或没有凭证 | 请参阅下表 |

```bash
# Pod Identity: agent and association
kubectl get pods -n kube-system -l app.kubernetes.io/name=eks-pod-identity-agent
aws eks list-pod-identity-associations --cluster-name <cluster> --namespace <ns> --service-account <sa>

# IRSA: OIDC condition in the trust policy
aws eks describe-cluster --name <cluster> --query 'cluster.identity.oidc.issuer' --output text
aws iam get-role --role-name <role> --query 'Role.AssumeRolePolicyDocument'
```

**原因和修复方法**：

| 观察结果 | 原因 | 修复方法 |
|---|---|---|
| 没有环境变量，但存在 SA 注解 | 创建顺序、实际的 serviceAccountName，或 webhook 注入配置有误 | 验证/修复配置，然后在考虑滚动更新影响后，于正确的命名空间中重新创建 Pod |
| 没有环境变量，也没有关联 | 尚未创建 Pod Identity 关联，或关联使用了其他 SA/命名空间 | 运行 `aws eks create-pod-identity-association ...`，然后重启 Pod |
| `Not authorized to perform sts:AssumeRoleWithWebIdentity` | IRSA 信任策略中的 `Federated` OIDC 提供程序 ARN 错误，或 `sub`（`system:serviceaccount:<ns>:<sa>`）/`aud`（`sts.amazonaws.com`）条件不匹配 | 修复信任策略。如果集群已重新创建，OIDC issuer 也随之更改，因此也必须重新创建提供程序 |
| 使用 Pod Identity，但 `AssumeRole` 被拒绝 | 信任策略主体不是 `pods.eks.amazonaws.com`，或缺少 `sts:TagSession` | 在信任策略中同时允许 `sts:AssumeRole` 和 `sts:TagSession` |
| 环境变量正常，但只有特定 API 返回 `AccessDenied` | 身份/资源策略、SCP、边界、会话或 VPC 端点策略导致拒绝 | 检查调用方/资源和显式 Deny；相关 CloudTrail 数据事件可能需要配置日志记录 |
| 存在 Pod Identity 环境变量，但 SDK 报告 `Unable to locate credentials` | SDK 过旧，不支持容器凭证提供程序（`FULL_URI`） | 升级 SDK（EKS 文档中列出了最低受支持版本） |

IRSA 和 Pod Identity 的工作原理及设置方法见 [EKS 安全最佳实践](../security/06-eks-security-best-practices.md#irsa-iam-roles-for-service-accounts)和 [EKS Pod Identity](../eks/05-eks-security-pod-identity.md)；令牌过期和 webhook 问题见 [EKS 高级调试：控制平面调试](../eks/11-eks-advanced-debugging.md#2-control-plane-debugging)。

<span id="9-eks-enivpc-cni-ip-exhaustion"></span>

### 9. EKS：ENI/VPC CNI IP 耗尽

**症状**：Pod 卡在 `ContainerCreating`，Events 中出现 `FailedCreatePodSandBox`：

```
Warning  FailedCreatePodSandBox  kubelet  Failed to create pod sandbox: rpc error: code = Unknown desc =
  failed to setup network for sandbox "...": plugin type="aws-cni" name="aws-cni" failed (add):
  add cmd: failed to assign an IP address to container
```

在调度阶段，`Too many pods` 表示已达到 kubelet 的 Pod 数量上限。这可能与 IP 容量有关，但并不能证明 IP 已耗尽。CNI 的 `FailedCreatePodSandBox` 会在节点分配之后发生。

**诊断**：

```bash
# Read the actual pod ceiling; distinguish secondary-IP defaults from prefix/custom networking configuration
kubectl get node <node> -o jsonpath='{.status.allocatable.pods}{"\n"}'
kubectl get pods -A --field-selector spec.nodeName=<node>,status.phase!=Succeeded,status.phase!=Failed --no-headers | wc -l

# aws-node status and IPAM settings
kubectl get pods -n kube-system -l k8s-app=aws-node -o wide
kubectl get ds -n kube-system aws-node -o jsonpath='{range .spec.template.spec.containers[?(@.name=="aws-node")].env[*]}{.name}={.value}{"\n"}{end}' | grep -E "PREFIX|WARM|MINIMUM|CUSTOM_NETWORK"

# Free IPs in the subnet
aws ec2 describe-subnets --subnet-ids <subnet-id> --query 'Subnets[].{id:SubnetId,az:AvailabilityZone,free:AvailableIpAddressCount}' --output table
```

在 IPv4 次级 IP 模式下，`WARM_ENI_TARGET=1` 是预留 ENI 容量的默认目标。每个 ENI 也会占用一个主 IP：m5.xlarge 的每个 ENI 有 15 个 IPv4 地址，其中 14 个次级地址供普通 Pod 使用。正数 `WARM_IP_TARGET`/`MINIMUM_IP_TARGET` 会覆盖 warm-ENI 规则。warm=3 且 minimum=6 时，一个已使用 IP 可能需要总计六个 IP，其中五个空闲；五个已使用 IP 则目标为总计八个 IP，其中三个空闲。空闲容量不一定恰好为三个。IPAM 协调、ENI 限制和前缀分配粒度都会影响实际数量。

**原因和修复方法**：

| 观察结果 | 原因 | 修复方法 |
|---|---|---|
| 子网的 `AvailableIpAddressCount` 只有个位数 | 子网本身已耗尽；warm 池预先占用了 IP | 使用 `WARM_IP_TARGET`/`MINIMUM_IP_TARGET`（如上述设置）缩小 warm 池，通过**自定义网络**（`ENIConfig`）添加次级 CIDR（例如 100.64.0.0/16），并从长远考虑使用 IPv6 |
| 节点上的 Pod 数量 = 可分配 Pod 数量 | 已达到配置的 Pod 数量上限；应单独检查 IP 容量 | 验证支持和子网容量后使用**前缀委派**（`ENABLE_PREFIX_DELEGATION=true`，分配 /28 前缀，需要受支持的实例和连续的 /28 块），并重新计算 max-pods，或改用更大的实例 |
| 该节点上的 `aws-node` 处于 `CrashLoopBackOff` | CNI 本身故障（缺少 `AmazonEKS_CNI_Policy`、版本不匹配） | 运行 `kubectl logs -n kube-system <aws-node-pod> -c aws-node`，并检查节点上的 `/var/log/aws-routed-eni/ipamd.log` |
| 使用 Security Groups for Pods，且 `vpc.amazonaws.com/pod-eni` 不足 | Branch ENI 数量达到上限 | 改用支持 trunk ENI 的实例；确认 `ENABLE_POD_ENI=true` |

IPAM 行为（warm 池、前缀委派、自定义网络）见 [VPC CNI：IP 地址管理](../networking/01-vpc-cni.md#ip-address-management)；逐步处理 IP 耗尽的说明见 [EKS 高级调试：网络诊断](../eks/11-eks-advanced-debugging.md#5-networking-diagnostics)和 [EKS 故障排查：VPC CNI 问题](../eks/09-eks-troubleshooting.md#networking-issues)。

<span id="10-eks-karpenter-does-not-launch-a-node"></span>

### 10. EKS：Karpenter 未启动节点

**症状**：Pod 处于 `Pending`，且 `kubectl get nodeclaims` 中没有出现新的 NodeClaim。与默认调度器的 `FailedScheduling` 不同，Karpenter 会在同一个 Pod 上记录自己的原因作为事件。

**诊断**：

```bash
# Events emitted by Karpenter (source is karpenter)
kubectl get events -n <ns> --field-selector involvedObject.name=<pod> -o custom-columns=REASON:.reason,SRC:.source.component,MSG:.message

# NodePool limits vs current usage
kubectl get nodepool -o custom-columns='NAME:.metadata.name,CPU_LIMIT:.spec.limits.cpu,CPU_USED:.status.resources.cpu,MEM_LIMIT:.spec.limits.memory,MEM_USED:.status.resources.memory,READY:.status.conditions[?(@.type=="Ready")].status'

# NodeClaim progress
kubectl get nodeclaims -o custom-columns='NAME:.metadata.name,TYPE:.metadata.labels.node\.kubernetes\.io/instance-type,LAUNCHED:.status.conditions[?(@.type=="Launched")].status,REGISTERED:.status.conditions[?(@.type=="Registered")].status,READY:.status.conditions[?(@.type=="Ready")].status'

kubectl logs -n kube-system -l app.kubernetes.io/name=karpenter --tail=100
```

原始文档中记录的一条 Karpenter 事件，列出了被拒绝的 NodePool：

```
FailedScheduling  karpenter  Failed to schedule pod, incompatible with nodepool "system",
  daemonset overhead={"cpu":"821m","memory":"1350Mi","pods":"10"}, incompatible requirements,
  label "nvidia.com/device-plugin.config" does not have known values;
  incompatible with nodepool "runner-arm", ..., did not tolerate workload-type=ci-runner:NoSchedule;
  all available instance types exceed limits for nodepool "graviton";
  incompatible with nodepool "gpu-ner", ..., incompatible requirements, key node.kubernetes.io/instance-type,
  node.kubernetes.io/instance-type In [g6e.4xlarge] not in node.kubernetes.io/instance-type In [g6.2xlarge g6.4xlarge g6.xlarge]
```

记录的示例中 CPU_LIMIT 为 8 / CPU_USED 为 8，但 `exceed limits` 并不要求当前用量等于上限。当每个候选实例都超过剩余空间时，即使当前用量低于上限也会出现此消息。`Nominated` 表示调度提名，而非已完成；请验证 NodeClaim 的 Launched、Registered、Initialized、Ready 状态以及 Pod 的实际分配情况。

**原因和修复方法**：

| 消息片段 | 原因 | 修复方法 |
|---|---|---|
| `all available instance types exceed limits for nodepool "<np>"` | 添加任何候选实例都会超过 NodePool 限制 | 提高限制，或检查是否有节点整合正在回收空闲节点 |
| `label "<key>" does not have known values` | NodePool 模板标签/requirements 未提供请求的自定义标签值 | 在 NodePool 的 `spec.template.spec.requirements` 中添加该键（及其值列表） |
| `did not tolerate <key>=<value>:NoSchedule` | 没有容忍 NodePool 的 `taints` | 如果隔离是有意设置的，请使用其他 NodePool；否则添加容忍 |
| `key node.kubernetes.io/instance-type, ... In [X] not in ... In [Y Z]` | Pod 要求的实例类型不在 NodePool 允许范围内 | 调整其中一侧。通常是 Pod 侧的要求过于狭窄 |
| `daemonset overhead={...}` 数值较大且出现 `Insufficient` | 扣除 DaemonSet 预留量后，剩余容量不足 | 在 requirements 中加入更大的实例 |
| NodeClaim 的 `LAUNCHED=True, REGISTERED=False` 持续数分钟 | EC2 已启动，但节点无法加入（EC2NodeClass 子网/SG 选择器、节点 IAM 角色访问条目、AMI） | 检查 `kubectl describe nodeclaim <name>` 中的 Conditions/Events，以及 EC2 控制台系统日志 |
| Karpenter 日志中出现 `InsufficientInstanceCapacity` | 该可用区/实例类型没有 EC2 容量（ICE：Insufficient Capacity Error） | 扩大实例类型、可用区和 capacity-type（spot/on-demand）的范围 |
| 没有事件，Karpenter 日志也没有内容 | 该 Pod 不属于 Karpenter 候选对象（`nodeSelector` 指向 MNG 标签，或调度约束与 Karpenter 无关） | 重新检查 Pod spec 中所有与节点相关的约束 |

NodePool/EC2NodeClass 结构和详细故障排查见 [Karpenter：故障排查](../autoscaling/02-karpenter.md#troubleshooting)和 [EKS 高级调试：Karpenter 置备问题](../eks/11-eks-advanced-debugging.md#karpenter-provisioning-issues)。

<span id="11-no-service-can-be-created-failed-calling-webhook"></span>

### 11. 无法创建 Service：调用 webhook 失败

**症状**：API server 拒绝在任何命名空间中执行的 Service `kubectl apply`/`create` 操作，包括与负载均衡器毫无关系的 Service。包含 Service 的 Deployment、Helm 安装和 ArgoCD 同步都会卡在这里；与此同时，**现有 Service 仍能正常工作**，因此从 Pod 层面看不出任何异常。

```
Internal error occurred: failed calling webhook "mservice.elbv2.k8s.aws": failed to call webhook:
  ... no endpoints available for service "aws-load-balancer-webhook-service"
```

**诊断**：错误消息已经指出了 webhook 及其后方的 Service。沿着 webhook 配置 → webhook Service 的端点 → 后方的 Deployment 逐层检查。

```bash
# (1) Which webhooks are registered, and what each does on failure (rules, namespaceSelector, objectSelector, failurePolicy)
kubectl get mutatingwebhookconfigurations,validatingwebhookconfigurations
kubectl get mutatingwebhookconfiguration aws-load-balancer-webhook -o jsonpath='{range .webhooks[*]}{.name}{"\t"}failurePolicy={.failurePolicy}{"\t"}ns={.namespaceSelector}{"\t"}obj={.objectSelector}{"\t"}{.rules[*].operations}{" "}{.rules[*].resources}{"\n"}{end}'

# (2) Is there a Ready pod behind the webhook Service?
kubectl -n kube-system get endpointslices -l kubernetes.io/service-name=aws-load-balancer-webhook-service

# (3) Why does that Deployment keep dying?
kubectl -n kube-system get pods -l app.kubernetes.io/name=aws-load-balancer-controller
kubectl -n kube-system logs deploy/aws-load-balancer-controller --previous
```

原始文档记录了 LBC v3.2.1 反复重启，以及 2026 年 9 月 2 日的以下日志。本次审阅未独立核验历史重启次数或持续时间，因此不将其作为复现结果呈现。可采取行动的证据是已安装的 CRD 与控制器请求的 API 版本不匹配。

```
{"ts":"2026-09-02T07:54:42Z","logger":"setup","msg":"Disabling NLBGatewayAPI: missing required Gateway API CRDs","missing":["TLSRoute","TCPRoute","UDPRoute"]}
{"level":"error","logger":"controller-runtime.source.Kind","msg":"if kind is a CRD, it should be installed before calling Start","kind":"ListenerSet.gateway.networking.k8s.io","error":"no matches for kind \"ListenerSet\" in version \"gateway.networking.k8s.io/v1\""}
{"ts":"2026-09-02T07:57:00Z","level":"error","logger":"setup","msg":"problem running manager","error":"failed to wait for gateway.k8s.aws/alb caches to sync kind source: *v1.ListenerSet: timed out waiting for cache to be synced for Kind *v1.ListenerSet"}
```

这些日志表明，缓存同步失败的原因是找不到 ListenerSet.gateway.networking.k8s.io/v1。**Gateway API 1.5.0 的标准通道中包含 ListenerSet**。请在 [LBC v3.2.1 指南](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.2.1/docs/guide/gateway/gateway.md)中检查版本要求、标准 CRD 和 LBC 专用 CRD。需要 TCPRoute/UDPRoute 等其他 API 时，请检查实验性安装要求。影响范围取决于实际 webhook 规则、选择器和 failurePolicy。在目标更新和新资源协调受到影响时，现有 LB 数据路径仍可能继续工作。

**原因和修复方法**：

| 观察结果 | 原因 | 修复方法 |
|---|---|---|
| `no endpoints available for service "aws-load-balancer-webhook-service"` | Webhook Deployment 中没有 Ready Pod（CrashLoop、无法调度、副本数为 0） | **先让控制器恢复健康**（见下一行）。在 EndpointSlice 中确认地址和就绪条件，并测试实际的 webhook 请求 |
| 日志中出现 `no matches for kind "ListenerSet"` → `timed out waiting for cache to be synced` | 未安装此控制器版本所需的 Gateway API CRD | (a) 安装控制器版本所需的 Gateway API CRD（ListenerSet 位于 Gateway API 1.5.0 的标准通道中）；(b) 在 CRD 安装完成之前，通过 Helm feature-gate 值禁用控制器的 Gateway API 功能（在该版本的 `values.yaml` 中确认准确的 gate 名称）；(c) 固定使用与已安装 CRD 相匹配的控制器版本 |
| 端点存在，但出现 `connection refused` / `context deadline exceeded` / `x509` | 通向 webhook 端口的路径被阻断（NetworkPolicy/安全组），证书已过期或不匹配 | 检查 API server → Pod webhook 端口的路径、`clientConfig.caBundle` 和证书续期 |
| 你必须立即创建 Service | - | **只有在充分了解影响范围后，才可将其作为有意识的紧急措施**：将 `mservice.elbv2.k8s.aws` 的 `failurePolicy` 改为 `Ignore`。此期间创建的 Service 不会获得控制器的变更（不会注入默认的 `loadBalancerClass`），因此恢复后**要改回 `Fail`**，并审查期间创建的 Service |

不要采取以下做法：通过给 Service 添加 `app.kubernetes.io/name=aws-load-balancer-controller` 标签来绕过 `objectSelector`。这样虽然能通过 webhook，但该 Service **不会获得变更**，而且这个标签也会变得不真实。该选择器的存在只是为了允许创建控制器自身的 Service。

如果决定暂时禁用未使用的 Gateway API 功能，请将以下 v3.2.1 Chart 值与现有配置合并，并审查 Helm diff。首先检查现有 Gateway 资源是否依赖这些控制器。

```yaml
controllerConfig:
  featureGates:
    ALBGatewayAPI: false
    NLBGatewayAPI: false
```

**预防措施**：针对 webhook Deployment 的可用副本数和 CrashLoop 状态设置告警。例如，可使用以下 kube-state-metrics 表达式设置一个持续五分钟后触发的告警。

```promql
kube_deployment_status_replicas_available{
  namespace="kube-system", deployment="aws-load-balancer-controller"
} < 1
```

如果没有指标，该表达式同样不会返回任何时间序列；应另外监控 absent_over_time(...[5m]) 或抓取失败。如果 Deployment 可用，并不能证明 Service 选择器、证书或网络路径均正确：还要检查 EndpointSlice 条件和 webhook 路径。将副本分散到多个可用区并配置 PDB 有助于应对节点故障，但无法解决所有副本共有的配置错误。

原始[Pod 网络基准测试](../networking/06-pod-network-benchmark.md)说明了它为何排除了 ClusterIP 测量。这仍是已记录基准测试的局限；本次审阅没有复现该事件。

***

## kubectl 诊断速查表

将检查操作与调试操作区分开：get/describe/logs/top 用于检查资源；kubectl debug 和 kubectl run 会创建容器或 Pod。确保复制出的调试 Pod 标签不会意外匹配 Service 选择器，并在使用后删除调试 Pod。临时容器会继续记录在原始 Pod 上。

```bash
# ── Status scan ────────────────────────────────────────────────────────
# Unhealthy pods only
kubectl get pods -A -o json | jq -r '
  .items[]
  | select(.status.phase != "Succeeded")
  | select(.status.phase != "Running" or
      ([.status.conditions[]? | select(.type == "Ready" and .status == "True")] | length == 0))
  | [.metadata.namespace, .metadata.name, .status.phase,
     ([.status.initContainerStatuses[]?, .status.containerStatuses[]?
       | .state.waiting.reason // empty] | join(","))] | @tsv
'
# Restart counts ascending, so the 15 worst pods come LAST (after tail) + last termination reason.
# Reads the first container only ([0]); for multi-container pods check the others separately.
kubectl get pods -A --sort-by='.status.containerStatuses[0].restartCount' \
  -o custom-columns='NS:.metadata.namespace,NAME:.metadata.name,RESTARTS:.status.containerStatuses[0].restartCount,REASON:.status.containerStatuses[0].lastState.terminated.reason' | tail -15
# Pods on a given node
kubectl get pods -A --field-selector spec.nodeName=<node> -o wide
# Node conditions + zone + instance type
kubectl get nodes -o custom-columns='NAME:.metadata.name,READY:.status.conditions[?(@.type=="Ready")].status,DISK:.status.conditions[?(@.type=="DiskPressure")].status,MEM:.status.conditions[?(@.type=="MemoryPressure")].status,ZONE:.metadata.labels.topology\.kubernetes\.io/zone,TYPE:.metadata.labels.node\.kubernetes\.io/instance-type'

# ── Events ─────────────────────────────────────────────────────────────
kubectl get events -A --field-selector type=Warning --sort-by=.lastTimestamp | tail -30
kubectl get events -n <ns> --field-selector involvedObject.name=<pod>,reason=FailedScheduling
kubectl events -n <ns> --for pod/<pod> --watch          # follow one object live
kubectl events -A --types=Warning                       # kubectl events subcommand (1.26+)

# ── jsonpath for exactly the fields you need ──────────────────────────
kubectl get pod <pod> -o jsonpath='{.status.containerStatuses[*].lastState.terminated}'
kubectl get pod <pod> -o jsonpath='{range .spec.containers[*]}{.name}{": "}{.resources}{"\n"}{end}'
kubectl get svc <svc> -o jsonpath='{.spec.selector}'
kubectl get sa <sa> -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}'
kubectl get pv <pv> -o jsonpath='{.spec.nodeAffinity.required.nodeSelectorTerms[0].matchExpressions}'

# ── Logs ───────────────────────────────────────────────────────────────
kubectl logs <pod> -c <container> --previous --tail=100   # logs of the dead container
kubectl logs -n kube-system -l k8s-app=kube-dns --tail=50  # several pods by label
kubectl logs deploy/<name> --all-containers --since=10m

# ── Debug containers ───────────────────────────────────────────────────
# Attach an ephemeral container (target process namespace requires runtime support)
kubectl debug -it <pod> --image=nicolaka/netshoot --target=<container>
# Copy with an approved shell-capable debug-image; review copied labels and volume access
kubectl debug <pod> -it --copy-to=<pod>-debug --container=<container> --set-image=<container>=<debug-image> -- sh
# Node shell without SSH. --profile=sysadmin is a privileged container
kubectl debug node/<node> -it --image=busybox --profile=sysadmin -- chroot /host

# ── Resource usage (requires metrics-server) ───────────────────────────
kubectl top nodes
kubectl top pods -n <ns> --sort-by=memory
# Without metrics-server: "error: Metrics API not available"

# ── Schema lookup ──────────────────────────────────────────────────────
kubectl explain pod.status.containerStatuses.lastState.terminated
kubectl explain nodepool.spec.limits        # works for CRDs too
kubectl api-resources | grep -E "karpenter|k8s.aws"

# ── Rollouts ───────────────────────────────────────────────────────────
kubectl rollout status deploy/<name> -n <ns>
kubectl rollout history deploy/<name> -n <ns>
```

`kubectl debug` 的有效 `--profile` 值包括 `legacy`、`general`、`baseline`、`restricted`、`netadmin` 和 `sysadmin`（默认值为 `legacy` 或 `general`，具体取决于 kubectl 版本；请检查 `kubectl debug --help`）；在受限策略下，使用与 `--profile=restricted` 兼容的镜像/安全上下文；其他准入策略仍可能拒绝该操作。特权节点调试需要单独授权。

***

## 深入排查：相关文档

本手册是用于决定“下一步该去哪里”的入口。缩小原因范围后，请转到以下文档。

| 已缩小范围的问题 | 概念文档 | 深入故障排查 |
|---|---|---|
| Pod 生命周期、探针、重启策略 | [Pod 和工作负载](../core/02-pods-and-workloads.md#pod-lifecycle) | [EKS 高级调试：工作负载调试](../eks/11-eks-advanced-debugging.md#4-workload-debugging) |
| Service、EndpointSlice、CoreDNS、NetworkPolicy | [服务和网络](../core/03-services-networking.md)、[网络策略](../security/04-network-policies.md) | [EKS 故障排查：网络问题](../eks/09-eks-troubleshooting.md#networking-issues) |
| PV/PVC/StorageClass、EBS CSI | [存储](../core/04-storage.md) | [EKS 故障排查：存储问题](../eks/09-eks-troubleshooting.md#storage-issues) |
| 节点加入、kubelet、资源压力 | [集群架构](../core/01-cluster-architecture.md) | [EKS 故障排查：节点和 Pod 问题](../eks/09-eks-troubleshooting.md#node-and-pod-issues) |
| Karpenter NodePool/NodeClaim | [Karpenter](../autoscaling/02-karpenter.md) | [扩缩容策略](06-scaling-strategies.md) |
| VPC CNI IPAM、前缀委派、自定义网络 | [VPC CNI](../networking/01-vpc-cni.md) | [EKS 网络第 3 部分：故障排查](../eks/03-eks-networking-part3.md) |
| IRSA、Pod Identity、RBAC | [EKS 安全最佳实践](../security/06-eks-security-best-practices.md)、[Kubernetes 身份验证和授权](../security/02-kubernetes-auth-authz.md) | [EKS 故障排查：IAM 和身份验证问题](../eks/09-eks-troubleshooting.md#iam-and-authentication-issues) |
| 日志的位置及查找方法 | [日志记录概述](../observability/logging/README.md) | [可观测性分析](08-observability-analysis.md) |
| requests/limits、OOM、JVM 内存 | [资源优化](10-resource-optimization.md) | [EKS 故障排查：性能问题](../eks/09-eks-troubleshooting.md#performance-issues) |
| 事件响应流程、严重程度、前 5 分钟检查清单 | - | [EKS 高级调试：事件响应框架](../eks/11-eks-advanced-debugging.md#1-incident-response-framework) |

***

## 参考资料

本页引用的字符串和经验规则所依据的官方文档。

**Kubernetes**

- [污点和容忍](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)：节点控制器自动添加的 `node.kubernetes.io/*` 污点（第 6 节）
- [使用 kubectl 调试 Kubernetes 节点](https://kubernetes.io/docs/tasks/debug/debug-cluster/kubectl-node-debug/)和 [`kubectl debug` 参考](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_debug/)：节点调试 Pod 和 `--profile` 值（第 2 节、第 6 节、速查表）
- [调试正在运行的 Pod](https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/)：临时容器、`--copy-to`、`--target`（速查表）
- [EndpointSlice](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)：`v1 Endpoints` 自 1.33 起弃用的原因（第 4 节）
- [调试 Service](https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/)和[调试 DNS 解析](https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/)：选择器/端口/DNS 检查和 `ndots`（第 5 节）

**Amazon EKS / AWS**

- [Amazon VPC CNI 插件 README](https://github.com/aws/amazon-vpc-cni-k8s/blob/master/README.md)：`WARM_ENI_TARGET`、`WARM_IP_TARGET`、`MINIMUM_IP_TARGET`、`ENABLE_PREFIX_DELEGATION` 的语义和优先级（第 9 节）
- [通过前缀为 Amazon EKS 节点分配更多 IP 地址](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses.html)：前缀委派和 max-pods 重新计算（第 9 节）
- [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)和[服务账户的 IAM 角色](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)：信任策略格式和注入的环境变量（第 8 节）
- [检测节点运行状况问题并启用自动节点修复](https://docs.aws.amazon.com/eks/latest/userguide/node-health.html)：第 6 节中展示的 Node Monitoring Agent 条件
- [排查 Amazon EKS 集群和节点问题](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html)：节点加入失败、`AccessDenied`、CNI 错误
- [Karpenter：故障排查](https://karpenter.sh/docs/troubleshooting/)：NodePool 限制、要求不匹配、NodeClaim 启动/注册失败（第 10 节）

***

< [上一页：可用区集群运维](15-zonal-operations-guide.md) | [目录](./README.md) >
