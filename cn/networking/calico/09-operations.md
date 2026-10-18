# 第 9 部分：Calico 运维指南

> **已审阅基线**：Calico 3.32.2 / Operator 1.42.6 / Kubernetes 1.34–1.36（经 Calico 测试）。
> **最后更新**：2026 年 9 月 12 日

## 概述

本章为 Calico 部署提供全面的运维指南，涵盖安装、监控、故障排查、升级以及生产环境最佳实践。

运维是一个反馈循环：验证安装、观察其行为、诊断变化，并在升级前保留可恢复的配置和状态。配置导出与经过测试的数据存储恢复承担不同职责。

## 安装指南

使用一个安装管理方，并选择与平台匹配的配置方案。以下示例适用于**全新、自行管理的 Linux 集群，使用完整 Calico CNI、iptables 和 VXLAN**。准备互不重叠的 Pod CIDR、兼容的节点操作系统/内核、Kubernetes API 连通性，以及符合条件的节点之间可用的底层 UDP 4789 连通性。这不是 VPC CNI 的仅策略配置；EKS 请参阅[第 8 部分](08-eks-integration.md)。选择其他 overlay/BGP 设计前，请先查看[网络模式](03-networking-modes.md)。

### Tigera Operator 清单

Calico 3.32 除 Operator 清单外，还需要单独的 Calico CRD：

```bash
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/v1_crd_projectcalico_org.yaml
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/tigera-operator.yaml
kubectl wait --for=condition=Available deployment/tigera-operator \
  -n tigera-operator --timeout=300s
```

将以下内容保存为 `installation.yaml`，并将示例 Pod CIDR 替换为集群准备使用的 CIDR。省略 MTU 时由 Operator 自动检测；不要用猜测的 MTU 代替对实际路径的测量。

```yaml
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  variant: Calico
  cni:
    type: Calico
  calicoNetwork:
    bgp: Disabled
    linuxDataplane: Iptables
    ipPools:
    - cidr: 10.244.0.0/16
      blockSize: 26
      encapsulation: VXLAN
      natOutgoing: Enabled
      nodeSelector: all()
    nodeAddressAutodetectionV4:
      kubernetes: NodeInternalIP
  nodeUpdateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
---
apiVersion: operator.tigera.io/v1
kind: APIServer
metadata:
  name: default
spec: {}
---
apiVersion: operator.tigera.io/v1
kind: Goldmane
metadata:
  name: default
spec: {}
---
apiVersion: operator.tigera.io/v1
kind: Whisker
metadata:
  name: default
spec: {}
```

```bash
kubectl apply -f installation.yaml
```

此 VXLAN 示例禁用了 BGP；只有所选配置启用了 BGP 时，才需要关注 BGP 诊断。Calico API server 和 Goldmane/Whisker 是开源组件。当前 OSS flow-logs 指南将可观测性功能标记为技术预览；依赖它进行运维前，应先评估该状态。

在测量证明有必要且有受支持的覆盖设置之前，应由 Operator 管理组件资源规格和 Typha 扩展。任意固定内存限制、不受支持的 `typhaDeployment.spec.replicas`/`minReadySeconds` 覆盖，或在旧式 `componentResources` 列表中添加 `KubeControllers` 条目，都不是生产配置。使用版本对应的 Installation API；请参阅[架构](02-architecture.md)和[扩展](07-advanced-topics.md)。

### Helm 替代方式

Helm chart 会安装相同的 Operator。将以下内容保存为 `calico-values.yaml`；使用此方式时，不要再用清单安装第二个 Operator。

```yaml
installation:
  enabled: true
  variant: Calico
  cni:
    type: Calico
  calicoNetwork:
    bgp: Disabled
    linuxDataplane: Iptables
    ipPools:
    - cidr: 10.244.0.0/16
      blockSize: 26
      encapsulation: VXLAN
      natOutgoing: Enabled
      nodeSelector: all()
    nodeAddressAutodetectionV4:
      kubernetes: NodeInternalIP
  nodeUpdateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
apiServer:
  enabled: true
goldmane:
  enabled: true
whisker:
  enabled: true
manageCRDs: true
```

```bash
helm repo add projectcalico https://docs.tigera.io/calico/charts
helm repo update projectcalico
helm template calico projectcalico/tigera-operator \
  --namespace tigera-operator --version v3.32.2 \
  -f calico-values.yaml > calico-rendered.yaml

# Apply only after reviewing the prepared cluster and rendered resources.
helm install calico projectcalico/tigera-operator \
  --namespace tigera-operator --create-namespace --version v3.32.2 \
  -f calico-values.yaml
```

顶层 `podAnnotations` 只会作用于 Operator Pod，不会启用 Felix 指标，也不会为所有组件配置 Prometheus 抓取。请在下面的监控部分显式配置指标。`manageCRDs: true` 允许 Operator 在启动后管理 CRD；新增字段的升级顺序将在后文说明。

### 直接清单替代方式

若现有安装由直接清单管理，请使用匹配的发布版本/配置，并保留已有定制。应用前请检查下载的文件：

```bash
curl -fL https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/calico.yaml \
  -o calico.yaml
```

编辑相关配置，包括 Pod CIDR 和启用的网络模式。全局 `sed` 替换可能只改动示例或注释值，而没有配置实际 IP 池。不要将 `kube-system` 中由直接清单管理的资源与 `calico-system` 中的 Operator 安装混用。

### 验证安装

```bash
kubectl get tigerastatus
kubectl get installation default -o yaml
kubectl rollout status daemonset/calico-node -n calico-system --timeout=300s
kubectl get pods -n calico-system -o wide
kubectl get nodes -o wide
```

对于直接清单安装，请检查实际使用的命名空间和资源名称。组件 Ready 并不能证明策略已生效或应用可以连通。使用由控制器管理的工作负载测试必要的 Service/DNS 路径，以及允许和拒绝的应用连接。检查 API 访问时，应使用实际 API server 的 HTTPS 端点和适当的身份验证；对 `kubernetes.default` 发起 HTTP 请求并不能验证 API 是否健康且可访问。

## calicoctl 命令参考

从官方发布版本安装匹配的 **3.32.2** 二进制文件，并按照[安装章节](01-introduction.md)验证校验和。发布包包含 Linux AMD64/ARM64、macOS AMD64/ARM64 和 Windows AMD64；请按实际主机架构选择。不要在 Bash 中执行 PowerShell 下载命令；升级后若继续使用旧客户端，应先调查兼容性警告。

访问 Kubernetes 数据存储时，常见的 Unix shell 配置如下：

```bash
export DATASTORE_TYPE=kubernetes
export KUBECONFIG="$HOME/.kube/config"
calicoctl version
calicoctl get nodes -o wide
calicoctl get networkpolicy -A
calicoctl get globalnetworkpolicy
calicoctl get tier
calicoctl get networkset -A
calicoctl get globalnetworkset
calicoctl get workloadendpoint -A
calicoctl get hostendpoint
calicoctl get ippool -o yaml
calicoctl get bgpconfiguration default -o yaml
calicoctl get bgppeer -o wide
calicoctl get felixconfiguration default -o yaml
```

kubeconfig 必须选择目标集群并具有适当的 RBAC。可以通过 `--config` 显式提供 Calico API 配置文件；不要假定 `~/.config` 下任意路径都会被自动发现。直接访问 etcdv3 数据存储时，应使用受支持的配置并验证证书。这是另一种部署配置，并不意味着可以访问 EKS 管理的 etcd 服务。

### 本地节点诊断

`calicoctl node status` 报告的是**本地节点的 BGP 状态**。即使设置了 kubeconfig，它也不会因此成为远程的集群级就绪检查。应在目标节点上按文档要求执行，或按下方示例检查该节点的 BIRD socket。

`calicoctl node diags` 会在所选节点上收集诊断归档。其受支持的 `--log-dir` 标志用于选择**输入日志目录**；3.32.2 中没有 `--output-dir` 标志。该实现需要 root 权限，并可能调用特权诊断容器及向 Felix 发送信号以转储状态。应将其视为有意执行的证据收集操作，而非被动健康探测。保护生成的归档，并使用命令输出的路径。

### Calico IPAM

仅当地址由 **Calico IPAM** 分配时才运行这些命令。若使用 VPC CNI、host-local 或其他 IPAM，请排查实际使用的分配器。

```bash
calicoctl ipam show
calicoctl ipam show --show-blocks
calicoctl ipam show --show-borrowed
calicoctl ipam show --show-configuration
calicoctl ipam show --ip=10.244.0.15
calicoctl ipam check --show-problem-ips -o ipam-report.json
```

`--show-blocks` 报告 block 的利用情况。应使用 BlockAffinity 记录查看 block 与节点的关联；它与 Kubernetes Node PodCIDR 不同。`--ip` 是只读的分配查询。报告可以帮助找出待调查对象，但单凭 Pod 缺失不能证明某项分配可以安全释放。

经过审阅的 CLI 不支持 `ipam release --block` 或 `--handle` 标志。基于报告释放地址时会检查分配序列，而且仍须遵循[高级 IPAM](07-advanced-topics.md)中的清理流程。`ipam split NUMBER --cidr=...` 是有效命令，但它拆分的是 **IP 池**，不是分配 block；该操作要求数据存储已锁定，并且拆分数量必须是 2 的幂。这属于计划内迁移操作，不能作为 Pod 卡住时的日常修复方法。

### 资源变更和导出

`get`、`create`、`apply`、`replace`、`patch` 和 `delete` 会操作受支持的资源类型。优先显式指定类型/命名空间；修改前应审阅完整策略集，并在 patch 时保留无关字段。例如，修改日志配置时，应更新现有的 FelixConfiguration 或其 GitOps 管理方，而不是用只包含新字段的对象替换原对象。

`calicoctl get all` 并不是所有资源的备份。应枚举所需资源类型，并分别纳入 Kubernetes 策略和 Operator 资源。`calicoctl get ... --export` 确实存在，但未指定资源名称时，经审阅的 CLI 会忽略它。它不会将列表导出变成完整、可移植的灾难恢复备份。请参阅下方备份部分。

## Prometheus 指标

请从**已安装版本的 `/metrics` 输出**确认指标名称、类型和标签。特定数据平面的时间序列并不保证在所有配置中都存在；缺失的时间序列不等于零。下列名称已根据 Calico 3.32.2 源码和官方指标参考核对。

### 启用组件指标

Felix 指标默认禁用；其默认端口为 **9091**。Typha 指标也默认禁用；Typha 二进制文件的默认指标端口为 **9091**，而此 Operator 示例显式选择 **9093**。kube-controllers 指标默认在 **9094** 启用。

对于现有 Operator 安装，请通过其配置管理方合并以下设置：

```bash
kubectl patch felixconfiguration default --type=merge \
  -p '{"spec":{"prometheusMetricsEnabled":true,"prometheusMetricsPort":9091}}'
kubectl patch installation default --type=merge \
  -p '{"spec":{"typhaMetricsPort":9093}}'
kubectl get service calico-typha-metrics -n calico-system
kubectl get service calico-kube-controllers-metrics -n calico-system
```

配置 `typhaMetricsPort` 后，Operator 会创建 Typha 指标 Service。不要替换它并创建冲突的 Service。直接清单安装需要单独配置 Typha 环境变量和 Service。应适当限制指标访问；对 host-network 端点而言，仅有工作负载 NetworkPolicy 可能不够，还需要主机/网络安全控制。

### 指标名称和含义

| 指标 | 类型/含义 |
| --- | --- |
| `felix_active_local_endpoints` | Gauge；本地工作负载**和主机**端点。为零可能是正常状态，不可用作就绪检查 |
| `felix_active_local_policies` | Gauge；此节点上生效的策略数。求和会统计各节点本地的策略实例，而非集群内唯一策略 |
| `felix_cluster_num_hosts`、`felix_cluster_num_policies` | 每个 Felix 都能观测到的集群级 Gauge；不要将各节点上相同的副本求和 |
| `felix_int_dataplane_failures` | Counter；失败但会重试的数据平面更新；经审阅的指标名称不带 `_total` 后缀 |
| `felix_int_dataplane_apply_time_seconds` | **Summary**，表示增量数据平面更新耗时；导出分位数、`_sum` 和 `_count`，而非 Histogram bucket |
| `felix_iptables_restore_calls`、`felix_iptables_restore_errors` | iptables 数据平面中 iptables-restore 调用次数/错误数的 Counter |
| `felix_log_errors`、`felix_logs_dropped` | 写入进程日志时的错误数/因输出受阻而丢弃的日志数；不是 ERROR 级别条目数，也不是被拒绝的数据包数 |
| `typha_connections_active` | Gauge；打开的连接数，包含握手中的连接 |
| `typha_connections_streaming{syncer="..."}` | Gauge；已完成握手并正在传输的客户端数 |
| `typha_connections_accepted` | Counter；已接受的连接数 |
| `typha_connections_dropped` | Counter；因**重新平衡**而丢弃的连接数，不是通用网络故障计数 |
| `typha_cache_size{syncer="..."}` | Gauge；缓存中的键值条目数 |
| `typha_updates_total{syncer="..."}` | Counter；从数据存储 syncer **接收**的更新数 |
| `ipam_allocations_in_use{ippool="...",node="..."}` | kube-controllers Gauge；分配给工作负载/接口的 Calico IPAM 地址数 |
| `ipam_ippool_size{ippool="..."}` | kube-controllers Gauge；池 CIDR 中的总地址数 |
| `ipam_allocations_gc_candidates` | 正在调查的潜在泄漏；不是释放地址的许可 |

BIRD 控制 socket 不是 Prometheus exporter。`bird_protocol_up` 或 `calico_bgp_peer_status` 等名称需要另行选定 exporter/collector，并核实其标签和语义；此安装不会生成这些时间序列。请使用下方的 BGP 诊断，或采用 [CalicoNodeStatus 方法](04-bgp-deep-dive.md)；只有在检查实际输出后，才添加 exporter 告警。

### ServiceMonitor 接线

此示例假设 Prometheus Operator CRD 和 `monitoring` 命名空间已存在。ServiceMonitor 标签必须与 Prometheus 资源的 `serviceMonitorSelector` 匹配，并确保其 `serviceMonitorNamespaceSelector` 包含此命名空间。PrometheusRule 标签也须与其 `ruleSelector` 匹配。自定义资源本身有效但没有被选中时，不会产生抓取或规则。

以下**彼此独立的 Service**不会更改 Operator 管理的 Service，并为三个组件都提供名为 `http-metrics` 的端口。如果安装已抓取这些端点，应复用现有配置，而不是重复抓取。ServiceMonitor 的 `jobLabel` 会生成下方使用的 `calico-felix`、`calico-typha` 和 `calico-kube-controllers` job。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: calico-audit-felix-metrics
  namespace: calico-system
  labels:
    audit.calico/component: calico-felix
spec:
  clusterIP: None
  selector:
    k8s-app: calico-node
  ports:
  - name: http-metrics
    port: 9091
    targetPort: 9091
    protocol: TCP
---
apiVersion: v1
kind: Service
metadata:
  name: calico-audit-typha-metrics
  namespace: calico-system
  labels:
    audit.calico/component: calico-typha
spec:
  clusterIP: None
  selector:
    k8s-app: calico-typha
  ports:
  - name: http-metrics
    port: 9093
    targetPort: 9093
    protocol: TCP
---
apiVersion: v1
kind: Service
metadata:
  name: calico-audit-kube-controllers-metrics
  namespace: calico-system
  labels:
    audit.calico/component: calico-kube-controllers
spec:
  clusterIP: None
  selector:
    k8s-app: calico-kube-controllers
  ports:
  - name: http-metrics
    port: 9094
    targetPort: 9094
    protocol: TCP
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: calico-components
  namespace: monitoring
  labels:
    app.kubernetes.io/part-of: calico-monitoring
spec:
  jobLabel: audit.calico/component
  selector:
    matchExpressions:
    - key: audit.calico/component
      operator: Exists
  namespaceSelector:
    matchNames:
    - calico-system
  endpoints:
  - port: http-metrics
    interval: 30s
    scrapeTimeout: 10s
    path: /metrics
```

检查端点发现/RBAC、网络访问和 Prometheus Targets 页面。ServiceMonitor 的 `endpoints.port` 选择的是 **Service 端口名称**，不是容器端口号。应确认每个发现到的目标，而不能只抓取负载均衡 Service 地址并假定它代表了每个节点。

## Grafana 仪表板

使用已配置的 Prometheus datasource 和适用于当前时间序列的 stat panel。下列是 panel 查询，不是可完整导入的仪表板。选择单个集群的指标；集中式多集群 datasource 需要在选择器和聚合中保留 cluster 标签。

| 面板 | PromQL |
| --- | --- |
| 每节点端点数 | `felix_active_local_endpoints{job="calico-felix"}` |
| 每节点生效策略数 | `felix_active_local_policies{job="calico-felix"}` |
| 观测到的集群策略数 | `max(felix_cluster_num_policies{job="calico-felix"})` |
| 每秒数据平面重试次数 | `rate(felix_int_dataplane_failures{job="calico-felix"}[5m])` |
| Typha 流式连接数 | `typha_connections_streaming{job="calico-typha"}` |
| 本地 Summary 的 p99 | `felix_int_dataplane_apply_time_seconds{job="calico-felix",quantile="0.99"}` |

单个进程的 Summary 分位数并不是集群范围的 p99，也不能用 `histogram_quantile` 合并。要计算发生更新期间的平均增量应用耗时：

```promql
rate(felix_int_dataplane_apply_time_seconds_sum{job="calico-felix"}[5m])
/ rate(felix_int_dataplane_apply_time_seconds_count{job="calico-felix"}[5m])
```

没有观测值时，平均值未定义（`0/0`），不代表延迟为零。不要为此 Summary 虚构 `_bucket` 时间序列，也不要保留未经验证的 `felix_iptables_restore_time_seconds` 查询。请使用可用的操作计数器和数据平面计时指标。

可通过以下查询检查 Calico IPAM 地址利用率：

```promql
sum by (ippool) (
  max by (ippool, node) (ipam_allocations_in_use{job="calico-kube-controllers",ippool!="no_ippool"})
)
/ max by (ippool) (ipam_ippool_size{job="calico-kube-controllers",ippool!="no_ippool"})
```

按池/节点取 `max` 可避免将控制器观测到的相同数据重复计算；之后求和可得到各节点分配数的总和。这表示**地址利用率**，不是已使用的 block 数，也不保证某个节点仍有可分配容量。池选择器、strict affinity、block 上限、保留地址/隧道地址及其他约束仍然会影响结果。它也不表示 VPC CNI 分配情况；指标为空、缺失或容量为零时，需要另行调查。

## 告警规则

以下规则示例假设使用上面的 job、单个选定集群，并使用 kube-state-metrics 获取 DaemonSet 指标。只有确实预期运行的组件才启用缺失目标规则。若复用现有监控配置，应调整选择器；阈值/持续时间也应按工作负载调优。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: calico-alerts
  namespace: monitoring
  labels:
    app.kubernetes.io/part-of: calico-monitoring
spec:
  groups:
  - name: calico.rules
    rules:
    - alert: CalicoDaemonSetUnavailable
      expr: kube_daemonset_status_number_unavailable{namespace="calico-system",daemonset="calico-node"}
        > 0
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: Calico DaemonSet has unavailable Pods
        description: Inspect the affected node, rollout and kube-state-metrics data.
    - alert: CalicoMetricsScrapeFailed
      expr: up{job=~"calico-(felix|typha|kube-controllers)"} == 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Calico scrape failed for {{ $labels.job }} on {{ $labels.instance
          }}
    - alert: CalicoMetricsTargetsMissing
      expr: |-
        absent(up{job="calico-felix"})
        or absent(up{job="calico-typha"})
        or absent(up{job="calico-kube-controllers"})
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: No discovered metrics targets for {{ $labels.job }}
    - alert: CalicoDataplaneRetries
      expr: rate(felix_int_dataplane_failures{job="calico-felix"}[5m]) > 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Dataplane updates are being retried on {{ $labels.instance }}
    - alert: CalicoDataplaneMeanSlow
      expr: |-
        (rate(felix_int_dataplane_apply_time_seconds_sum{job="calico-felix"}[5m])
        / rate(felix_int_dataplane_apply_time_seconds_count{job="calico-felix"}[5m])) > 0.5
        and (rate(felix_int_dataplane_apply_time_seconds_count{job="calico-felix"}[5m]) > 0)
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Mean dataplane update time exceeds 0.5s on {{ $labels.instance }}
    - alert: CalicoIPAMHighAddressUsage
      expr: |-
        (sum by (ippool) (
          max by (ippool, node) (ipam_allocations_in_use{job="calico-kube-controllers",ippool!="no_ippool"})
        )
        / max by (ippool) (ipam_ippool_size{job="calico-kube-controllers",ippool!="no_ippool"})) > 0.8
        and on (ippool)
        (max by (ippool) (ipam_ippool_size{job="calico-kube-controllers",ippool!="no_ippool"}) > 0)
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: High address utilization in Calico IP pool {{ $labels.ippool }}
        description: Address utilization is {{ $value | humanizePercentage }}; inspect
          per-node eligibility and block constraints.
```

`up == 0` 检测的是已发现但抓取失败的目标，无法检测目标完全消失；`absent` 规则用于检测某个预期组件的**全部**目标丢失。若要发现健康节点中仅有一个节点缺失，需要与预期的节点/DaemonSet 清单比较。告警未出现在界面中，并不能证明系统健康；对应指标或规则可能根本没有加载。

扩缩容期间 Typha 连接数下降或 rebalance 计数增加都可能是预期行为。应将持续的 streaming/client 延迟及组件可用性结合起来，再判定是否为事故。同样，本地端点数为零并不意味着 Felix 未就绪。应检查实际就绪/滚动更新状态，并分别执行合成的允许/拒绝测试。

## 日志分析与故障排查

### 从受影响的工作负载和节点开始

Pod 处于 Pending 时，可能还未调度，因此尚未调用任何 CNI。先检查事件和 `spec.nodeName`。若是 CNI/IP 分配错误，应确认实际分配器，并查看受影响节点的 kubelet/CNI 日志；并非每个 Pod IPAM 错误都来自 Felix 进程日志。

```bash
CALICO_NAMESPACE=calico-system
WORKLOAD_NAMESPACE=calico-demo
WORKLOAD_POD=replace-with-actual-pod

kubectl describe pod "$WORKLOAD_POD" -n "$WORKLOAD_NAMESPACE"
CALICO_NODE=$(kubectl get pod "$WORKLOAD_POD" -n "$WORKLOAD_NAMESPACE" \
  -o jsonpath='{.spec.nodeName}')
test -n "$CALICO_NODE" || { echo "Pod is not scheduled to a node" >&2; exit 1; }
kubectl get pods -n "$CALICO_NAMESPACE" -l k8s-app=calico-node \
  --field-selector "spec.nodeName=$CALICO_NODE" -o wide

# Select the actual agent Pod on this node, including during a rollout.
CALICO_POD=replace-with-actual-calico-node-pod
kubectl logs -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node \
  --since=15m --tail=200 --timestamps
```

明确指定时间范围和 tail 限制。使用 selector 时，`kubectl logs` 默认可能只返回较短的尾部；指定时间窗口并不代表窗口中的所有行都已返回。若容器重启过，在可用时应查看其上一个实例的日志。保留日志获取错误，不要将其转换成“没有错误”。

Felix 进程日志描述配置写入和组件活动。将 `logSeverityScreen` 设为 Debug 不会产生逐数据包的策略决策日志。临时更改前，应记录原字段及其配置管理方；之后要恢复原值或原先缺省的状态，不能想当然地恢复到 Info。文件/syslog 输出还取决于配置的路径和运行时环境。

### 地址分配与连通性

| 症状 | 变更状态前先检查 |
| --- | --- |
| 没有已调度节点 | 调度器事件、容量、affinity 和 taint；此时还不能判断为 IPAM 问题 |
| CNI 分配失败 | 实际分配器的日志、池/地址容量、selector 资格、block/affinity 限制和 API 访问 |
| Pod IP 可达但 Service 失败 | Endpoint/EndpointSlice、Service 端口、kube-proxy 或 BPF Service 处理、DNS 和策略 |
| 小包正常、大包失败 | 底层/overlay MTU、分片/PMTUD 及返回路径 |
| 预期的策略未能阻止流量 | 实际端点身份/标签、方向、命名空间 selector、tier/顺序、先前的 allow 规则、host-network/其他接口限制及已建立连接 |

```bash
kubectl exec -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node -- ip route show
kubectl exec -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node -- ip -d link show
calicoctl get networkpolicy -n "$WORKLOAD_NAMESPACE" -o yaml
calicoctl get globalnetworkpolicy -o yaml
calicoctl get tier -o yaml
calicoctl get workloadendpoint -n "$WORKLOAD_NAMESPACE" -o yaml
kubectl get pod "$WORKLOAD_POD" -n "$WORKLOAD_NAMESPACE" --show-labels
```

不要随便选择集群中的第一个 `calico-node` Pod 并假定它位于故障工作负载所在节点。ICMP 成功/失败不能单独验证 TCP 或 HTTP 策略。使用获准的诊断工作负载，确保工具可用且协议/端口与应用实际使用的一致。

对于 Calico IPAM，使用上面的只读命令和 [IPAM 清理流程](07-advanced-topics.md)。Pool CIDR 和 blockSize 不可变；添加一个不重叠且符合条件的池属于计划内容量变更，不是原地扩展 CIDR。尚未证明原因前，不要释放地址或重启 Agent。

对于 Operator 安装，MTU 和地址自动检测属于 `Installation.spec.calicoNetwork`；只有文档说明时才能使用隧道专用的 Felix 字段。`FelixConfiguration.spec.mtu` 和 `ipAutoDetectionMethod` 不是经审阅的 API。遵循 [MTU/网络指南](03-networking-modes.md)，保留其他设置，并分别验证新建和已有的 Pod。

### BGP 诊断

仅对使用 BGP 的配置执行 BGP 检查。在选定的 `calico-node` Pod 上使用实际 BIRD socket：

```bash
kubectl exec -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node -- \
  birdcl -s /var/run/calico/bird.ctl show protocols all
kubectl exec -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node -- \
  birdcl -s /var/run/calico/bird.ctl show route
calicoctl get bgpconfiguration -o yaml
calicoctl get bgppeer -o yaml
calicoctl get bgpfilter -o yaml
```

若部署了对应的 IPv6 daemon，请使用 `bird6.ctl`。核对本地/对端 ASN、选定的源地址、双向 TCP 179、身份验证/TTL 设置、路由过滤以及预期通告的路由。TCP 连接成功并不能证明 BGP 会话已建立，也不能证明所需前缀已被接受。不要想当然地认为日志文件存在；应检查镜像附带的日志配置，以及所发布容器的 BIRD run/log 脚本，确认实际写入位置。请参阅 [BGP 深入介绍](04-bgp-deep-dive.md)。

## 健康检查自动化

以下**Operator 安装状态检查**从管理环境运行，需要 Bash、jq 和兼容版本的 kubectl。它只读地请求 API/日志，检查观测到的 DaemonSet generation 和副本可用性，并在请求失败时返回失败。它不会检查 BGP socket、验证数据包转发，也不能证明每项策略都正确。

```bash
#!/usr/bin/env bash
# calico-status-check.sh: operator component status and bounded log collection.
set -euo pipefail
CALICO_NAMESPACE=${CALICO_NAMESPACE:-calico-system}

if ! calico_ds_json=$(kubectl get daemonset calico-node -n "$CALICO_NAMESPACE" \
  --request-timeout=20s -o json); then
  echo "Unable to read calico-node DaemonSet status" >&2
  exit 2
fi
if ! jq -e '
  .status.desiredNumberScheduled as $desired
  | ($desired > 0)
    and (.status.observedGeneration >= .metadata.generation)
    and (.status.updatedNumberScheduled == $desired)
    and (.status.numberReady == $desired)
    and (.status.numberAvailable == $desired)
    and ((.status.numberUnavailable // 0) == 0)
' <<<"$calico_ds_json" >/dev/null; then
  echo "Calico DaemonSet is not fully observed, updated and available" >&2
  exit 1
fi

if ! calico_status_json=$(kubectl get tigerastatus --request-timeout=20s -o json); then
  echo "Unable to read operator component status" >&2
  exit 2
fi
if ! jq -e '
  (.items | length) > 0 and all(.items[];
    any(.status.conditions[]?; .type == "Available" and .status == "True")
    and any(.status.conditions[]?; .type == "Progressing" and .status == "False")
    and any(.status.conditions[]?; .type == "Degraded" and .status == "False")
  )
' <<<"$calico_status_json" >/dev/null; then
  echo "Operator components are unavailable, progressing, degraded or missing conditions" >&2
  exit 1
fi

if ! calico_logs=$(kubectl logs -n "$CALICO_NAMESPACE" -l k8s-app=calico-node \
  -c calico-node --since=15m --tail=200 --timestamps --prefix \
  --request-timeout=20s); then
  echo "Unable to retrieve selected Calico logs; do not report no errors" >&2
  exit 2
fi
printf '%s\n' "$calico_logs"
echo "Component status checks passed; review these bounded logs and test application policy separately."
```

空/未调度的 DaemonSet、过期状态或缺失的组件条件都不算检查成功。日志仅限于选定的时间窗口/tail，仍需要解释。仅凭计数器或日志中的 ERROR 字样，并不等于正在发生故障。

若要将其安排为 CronJob，首先应在获准的镜像中打包并验证这些工具和脚本。使用具有 DaemonSet、Pod/Pod 日志和 TigeraStatus 只读权限的专用 ServiceAccount；不要复用特权较高的 `calico-node` 身份。配置并发策略、截止时间和失败报告。`calico/ctl` 镜像不是通用的 Bash/kubectl 诊断环境；普通 Job 若没有额外的、经过慎重设计的访问权限，也无法检查其他节点的 BIRD socket。此本地脚本并未隐含一个可工作的集群内 CronJob。

## 版本升级与恢复

### 准备过渡

```bash
calicoctl version
kubectl version --output=yaml
kubectl get deployment tigera-operator -n tigera-operator \
  -o jsonpath='{.spec.template.spec.containers[*].image}'
kubectl get tigerastatus
kubectl get daemonset calico-node -n calico-system -o wide
helm get values calico -n tigera-operator -o yaml
```

Helm 命令只适用于由 Helm 管理的安装。应盘点实际安装的镜像、CRD、数据存储、节点操作系统/内核、数据平面和 Kubernetes 兼容性。保留由安装管理方维护的清单/values、策略和经测试的恢复计划。`kubectl version --short` 已不是当前命令选项。

根据实际源版本和安装方式，遵循 [3.32 升级流程](https://docs.tigera.io/calico/latest/operations/upgrading/kubernetes-upgrade)。跨越相关版本时，检查 OwnerReference/UID 迁移说明。固定目标版本，并同时更新 calicoctl。

对于 Helm，可以先由对应管理方应用匹配的 Calico CRD，再升级 Operator；或者设置 `manageCRDs: true`，并等 Operator 安装好 CRD 后再使用新字段。升级 Operator 并不意味着应该盲目使用 `--force-conflicts` 覆盖字段所有权。完成审阅后的变更后，监控 Operator、calico-node 和其他已配置组件，并在滚动更新期间及之后测试允许/拒绝路径。

Operator 会协调其管理的 DaemonSet。通过 affinity patch 从“canary”节点移除 Agent 并不能构成安全的 canary 部署，还可能让这些节点失去策略执行能力。应在有代表性的隔离环境中测试版本/配置，并遵循受支持的发布控制。不要临时创建第二个互相竞争的节点 DaemonSet。

### 恢复限制

`helm rollback`、应用旧 Operator 或应用配置导出，并不会自动撤销 CRD/数据迁移，也不会恢复数据包处理状态。选择恢复方式前，应检查源/目标版本支持的降级路径和已存数据。Installation 资源仍然存在，并不能证明没有数据丢失。

EKS 控制平面恢复须遵守[第 8 部分](08-eks-integration.md)所述的当前资格要求和七天回滚限制。Calico/附加组件以及应用的兼容性仍是各自独立的责任。

## 备份与灾难恢复

### 将配置清单与状态恢复分开

| 材料 | 目的与限制 |
| --- | --- |
| Git 管理的清单/Helm values 和版本记录 | 期望配置和所有权；保留匹配的 CRD 定义和镜像 |
| Calico 策略、tier、set、pool、BGP/过滤器和控制器配置 | 配置清单；纳入实际使用的命名空间级、staged 和全局资源 |
| Kubernetes NetworkPolicy、命名空间/ServiceAccount 标签及相关 RBAC | 策略身份/依赖项，Calico 专属导出不会包含这些 |
| 主机/节点/端点和 IPAM 状态 | 依赖运行时/拓扑的数据；不要不加审查地将旧节点地址或分配重放到另一个集群 |
| 数据存储备份和应用数据 | 一致的恢复机制，以及单独保护的凭证/数据；YAML 列表不是原子性的数据存储快照 |

没有 `kubectl export` 命令。`calicoctl get TYPE -o yaml` 会导出资源；`--export` 标志受前述具名资源限制。对于自我管理的 Kubernetes/etcd，应遵循版本匹配且经过恢复测试的 [Kubernetes etcd 备份/恢复流程](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/)。托管服务必须使用其支持的恢复方式；这并不提供 EKS etcd 访问权限。

### 受保护配置清单示例

此脚本为使用 Calico IPAM 的 3.32 Operator 安装导出**明确列出的一部分资源**。需要 Bash、calicoctl、kubectl 和 sha256sum。目标目录必须不存在；部分导出会保留 `STATE=incomplete`。它不收集 Secrets、外部 IAM/网络设备、所有 Operator 自定义资源或完整 IPAM 分配状态。应根据已安装功能，有计划地扩展清单，并安全保护单独备份的凭证。

```bash
#!/usr/bin/env bash
# calico-config-inventory.sh: protected configuration inventory, not a datastore snapshot.
set -euo pipefail
umask 077
CALICO_EXPORT_DIR=${1:?Usage: calico-config-inventory.sh NEW_EXPORT_DIRECTORY}
mkdir -m 700 -- "$CALICO_EXPORT_DIR"
printf '%s\n' incomplete > "$CALICO_EXPORT_DIR/STATE"

for calico_kind in node ippool ipreservation bgpconfiguration bgppeer bgpfilter \
  globalnetworkpolicy stagedglobalnetworkpolicy globalnetworkset \
  felixconfiguration kubecontrollersconfiguration ipamconfiguration \
  tier hostendpoint profile; do
  calicoctl get "$calico_kind" -o yaml > "$CALICO_EXPORT_DIR/$calico_kind.yaml"
done
for calico_kind in networkpolicy stagednetworkpolicy stagedkubernetesnetworkpolicy \
  networkset workloadendpoint; do
  calicoctl get "$calico_kind" -A -o yaml > "$CALICO_EXPORT_DIR/$calico_kind.yaml"
done
kubectl get installation default -o yaml > "$CALICO_EXPORT_DIR/installation.yaml"
kubectl get networkpolicies.networking.k8s.io -A -o yaml \
  > "$CALICO_EXPORT_DIR/kubernetes-networkpolicies.yaml"
kubectl get namespaces -o yaml > "$CALICO_EXPORT_DIR/namespaces.yaml"
kubectl get serviceaccounts -A -o yaml > "$CALICO_EXPORT_DIR/serviceaccounts.yaml"
(
  cd -- "$CALICO_EXPORT_DIR"
  sha256sum ./*.yaml > SHA256SUMS
)
printf '%s\n' complete > "$CALICO_EXPORT_DIR/STATE"
echo "Configuration inventory completed: $CALICO_EXPORT_DIR"
```

`complete` 标记表示所声明的查询和校验和计算已完成，不表示快照具有事务一致性或已通过灾难恢复测试。应将导出内容视为敏感的基础设施数据。验证校验和，将副本保存在故障域之外，并使用实际数据存储/版本演练恢复。

### 恢复计划

1. 通过所选恢复方式恢复兼容的控制平面/数据存储及所需 CRD/Operator。新集群和同一集群内恢复对身份/IPAM 的要求不同。
2. 审阅命名空间/ServiceAccount 身份、标签和 RBAC，然后按依赖顺序恢复由你管理的声明式配置，包括先恢复 tier 和 set，再恢复依赖它们的策略。
3. 检查集群专属元数据、生成的/控制器管理的对象、旧节点地址和分配。不要把原始转储直接重放为可移植的期望状态清单。
4. 恢复正常变更前，验证 IP 分配唯一性、路由、加密、Service/DNS 行为，以及允许和拒绝的流量。

`calicoctl datastore migrate export/import` 是真实的 **etcd 到 Kubernetes 的迁移**工作流，具有数据存储锁定和回滚边界。它不是现有 Kubernetes 数据存储的通用备份捷径。锁定会影响新建 Pod；按文档操作，在 Kubernetes 数据存储解锁后便不能回滚。请参阅[迁移流程](https://docs.tigera.io/calico/latest/operations/datastore-migration)。

## 运维最佳实践

### 策略与访问权限

应先在选定的测试命名空间中验证默认拒绝策略，并明确所需 DNS、API、身份、监控和应用依赖。全局 `all()` 策略或臆造的 API server/节点标签 selector 可能切断必要流量。Pod 端点和主机端点走不同的策略路径；有关作用范围示例、tier 语义和主机端点控制，请参阅[第 5 部分](05-network-policy.md)。保留一个独立可用的恢复路径，并在扩大范围前测试负向用例。

### 流量可观测性

当前 OSS Operator/Helm 安装可使用 Goldmane 和 Whisker。[OSS flow logs 指南](https://docs.tigera.io/calico/latest/observability/view-flow-logs)将此功能标为技术预览，并描述聚合流，而非每个数据包/连接一条记录。旧式文件/DNS logger 字段和虚构的 `FlowLogsFileReporter` 名称都不是有效的 OSS 配置。

```bash
kubectl get goldmane,whisker
kubectl port-forward -n calico-system service/whisker 8081:8081
```

默认情况下，端口转发只绑定本机地址。Whisker/Goldmane 包含敏感的工作负载/网络数据；在其他位置公开之前，应配置身份验证和访问控制。若从这些组件尚不存在的版本升级，应有意启用相关自定义资源。进程 Debug 日志、策略 Log 动作、聚合流日志和 Prometheus 指标解决的是不同问题。

### 性能与资源

应测量端点/策略变化量、数据平面编程时间、排队、内存和实际应用流量。重新同步/刷新间隔不是 Kubernetes API 轮询间隔；增大它并不是通用的 API 负载优化手段。应使用实际的 `iptablesPostWriteCheckInterval` duration 字段，而不是已移除的 `...Secs` 拼写。保留安装管理方支持的资源覆盖和 Operator 扩展配置。

不要将启用 BPF、DSR 或猜测的接口匹配模式当成通用调优预设。[第 6 部分](06-ebpf-dataplane.md)介绍内核/平台要求、Service 处理、kube-proxy 冲突和回滚。更大的 conntrack map 会占用内存，也不会消除所有瓶颈。只有在确有理由进行数据平面或资源变更时，才重新执行相关工作负载和故障测试。

本指南附带的检查仅验证离线 schema、查询和脚本 fixture。它们不能证明生产容量足够、集群升级成功或灾难恢复可用。

## 参考资料

- [Calico 要求](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements)
- [Calico Installation API](https://docs.tigera.io/calico/latest/reference/installation/api)
- [监控组件指标](https://docs.tigera.io/calico/latest/operations/monitor/monitor-component-metrics)
- [Felix 指标](https://docs.tigera.io/calico/latest/reference/felix/prometheus)
- [Typha 指标](https://docs.tigera.io/calico/latest/reference/typha/prometheus)
- [kube-controllers 指标](https://docs.tigera.io/calico/latest/reference/kube-controllers/prometheus)
- [Calico 故障排查](https://docs.tigera.io/calico/latest/operations/troubleshoot/troubleshooting)
- [Calico 升级流程](https://docs.tigera.io/calico/latest/operations/upgrading/kubernetes-upgrade)
- [Prometheus Operator API](https://prometheus-operator.dev/docs/api-reference/api/)

## 后续步骤与测验

请查看[术语表](glossary.md)、[高级主题](07-advanced-topics.md)、[EKS 集成](08-eks-integration.md)和[运维测验](../../quizzes/networking/calico/09-operations-quiz.md)。
