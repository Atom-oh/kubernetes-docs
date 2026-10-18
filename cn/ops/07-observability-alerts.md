# Operational Alert 配置

> **审查基线**：Prometheus 3.15.0、Alertmanager 0.34.1、kube-prometheus-stack 92.9.0 / Prometheus Operator 0.94.1\
> **最后审阅**：2026年10月16日。本地已验证规则评估、模板、路由、抑制范围和 chart 配置。未配置真实集群告警，也未执行 Slack/PagerDuty 通知。

< [上一章：扩缩容](06-scaling-strategies.md) | [目录](README.md) | [下一章：可观测性分析](08-observability-analysis.md) >

配置告警不只是复制指标名称。请先验证采集器、指标类型、标签、单位和缺失数据时的行为，再根据服务影响和运维响应要求选择阈值。以下阈值仅为示例；请选择或调整规则，避免与现有 kube-prometheus-stack 默认规则重叠。

## 告警架构

![Operator 选择 PrometheusRule 资源并生成配置；Prometheus 评估规则，Alertmanager 则将更新发送给已配置的接收器。](../.gitbook/assets/en-ops-07-observability-alerts-0.png)

[交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-07-observability-alerts-0.html)

PrometheusRule 是一种 Kubernetes 资源。**Prometheus Operator 根据命名空间/标签选择器选择资源，并生成规则配置**。Prometheus 会根据采集到的时间序列评估生成的规则。

此示例使用命名空间和 Helm 发布名称 `monitoring`，并将 Rule 的 `release: monitoring` 标签与生成的选择器相匹配。如果实际发布或选择器不同，请同时修改两者。

| 字段/概念 | 含义 |
|---|---|
| `labels` | 告警实例身份，以及分组/路由/抑制所需的输入 |
| `annotations` | 摘要、描述和实际的运行手册链接 |
| `for` | 针对特定标签集，条件必须持续满足的时间 |
| `keep_firing_for` | 条件解除后可选的持续触发时间 |
| 严重级别 | 组织定义的标签值和响应策略 |

`critical`、`warning` 和 `info` 是常见约定，并非固定枚举值，也不是由工具强制执行的 SLA。评估间隔、`for`、传输方式、group_wait 和接收器处理都会影响通知时间。

### 评估状态与解除

![Prometheus 的 Inactive、Pending 和 Firing 状态，包括可选的保持时间以及独立的解除通知语义。](../.gitbook/assets/en-ops-07-observability-alerts-1.png)

[状态图](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-07-observability-alerts-1.html)

请区分规则评估和通知发送。`Firing` 并不能证明 Slack 已收到消息。告警停止触发时，可以发送解除更新；外部恢复消息则取决于 `send_resolved`、路由、静默设置和消息发送情况。

当表达式返回**向量元素**时，告警会激活；这也包括数值为零的元素。`Ready == 0` 会有意返回此类元素。不要在告警表达式中添加 `bool`，导致误将比较结果保留为 false。

序列消失可能会使表达式不再返回结果，但这并不代表服务确实已恢复。`ALERTS` 有助于观察 Pending/Firing 状态，但不能完整记录节点终止或 Operator 操作的历史。

## 已验证的基线规则

这些示例要求实际采集 node-exporter、kubelet/cAdvisor 和 kube-state-metrics 指标。请检查指标名称、job、标签以及相关节点/卷模式。基线假设每个 Prometheus 只监控一个集群；集中式查询必须确保**采集到的序列本身带有集群标签**，以免混淆多个集群。

```yaml
# prometheusrule.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: reviewed-operational-alerts
  namespace: monitoring
  labels:
    release: monitoring
spec:
  groups:
  - name: docs.network
    rules:
    - alert: NodeNetworkReceiveDropsHigh
      expr: rate(node_network_receive_drop_total{device!~"lo|veth.*|docker.*|br-.*|cali.*"}[5m]) > 100
      for: 5m
      labels:
        severity: warning
        alert_family: network_receive_drop
        team: network
      annotations:
        summary: Elevated receive drops on {{ $labels.instance }}
        description: '{{ $labels.device }} reports {{ printf "%.2f" $value }} dropped packets/s. Correlate with
          workload symptoms.'
        runbook_url: https://www.atomai.click/kubernetes-docs/en/ops/16-troubleshooting-playbook
    - alert: NodeNetworkTransmitDropsHigh
      expr: rate(node_network_transmit_drop_total{device!~"lo|veth.*|docker.*|br-.*|cali.*"}[5m]) > 100
      for: 5m
      labels:
        severity: warning
        alert_family: network_transmit_drop
        team: network
      annotations:
        summary: Elevated transmit drops on {{ $labels.instance }}
        description: '{{ $labels.device }} reports {{ printf "%.2f" $value }} dropped packets/s. Check the actual
          interface and path.'
        runbook_url: https://www.atomai.click/kubernetes-docs/en/ops/16-troubleshooting-playbook
  - name: docs.cpu
    rules:
    - alert: NodeCPUUsageHigh
      expr: (1 - avg by (cluster, instance, job) (rate(node_cpu_seconds_total{mode="idle"}[5m]))) > 0.85
      for: 5m
      labels:
        severity: warning
        alert_family: node_cpu
        team: platform
      annotations:
        summary: Elevated CPU utilization on {{ $labels.instance }}
        description: '{{ $value | humanizePercentage }} non-idle CPU time. This alone does not establish CPU pressure
          or customer impact.'
        runbook_url: https://www.atomai.click/kubernetes-docs/en/ops/16-troubleshooting-playbook
    - alert: NodeCPUUsageCritical
      expr: (1 - avg by (cluster, instance, job) (rate(node_cpu_seconds_total{mode="idle"}[5m]))) > 0.95
      for: 5m
      labels:
        severity: critical
        alert_family: node_cpu
        team: platform
      annotations:
        summary: Elevated CPU utilization on {{ $labels.instance }}
        description: '{{ $value | humanizePercentage }} non-idle CPU time. This alone does not establish CPU pressure
          or customer impact.'
        runbook_url: https://www.atomai.click/kubernetes-docs/en/ops/16-troubleshooting-playbook
    - alert: ContainerCPUThrottlingHigh
      expr: (sum by (cluster, namespace, pod, container) (rate(container_cpu_cfs_throttled_periods_total{container!="",container!="POD"}[5m])))
        / ((sum by (cluster, namespace, pod, container) (rate(container_cpu_cfs_periods_total{container!="",container!="POD"}[5m])))
        > 0) > 0.25
      for: 5m
      labels:
        severity: warning
        alert_family: container_cpu_throttling
        team: platform
      annotations:
        summary: CPU throttling on {{ $labels.namespace }}/{{ $labels.pod }}/{{ $labels.container }}
        description: '{{ $value | humanizePercentage }} of observed CFS periods included throttling. Correlate with
          latency and CPU quota before changing limits.'
        runbook_url: https://www.atomai.click/kubernetes-docs/en/ops/16-troubleshooting-playbook
    - alert: ContainerCPUThrottlingCritical
      expr: (sum by (cluster, namespace, pod, container) (rate(container_cpu_cfs_throttled_periods_total{container!="",container!="POD"}[5m])))
        / ((sum by (cluster, namespace, pod, container) (rate(container_cpu_cfs_periods_total{container!="",container!="POD"}[5m])))
        > 0) > 0.5
      for: 5m
      labels:
        severity: critical
        alert_family: container_cpu_throttling
        team: platform
      annotations:
        summary: CPU throttling on {{ $labels.namespace }}/{{ $labels.pod }}/{{ $labels.container }}
        description: '{{ $value | humanizePercentage }} of observed CFS periods included throttling. Correlate with
          latency and CPU quota before changing limits.'
        runbook_url: https://www.atomai.click/kubernetes-docs/en/ops/16-troubleshooting-playbook
    - alert: ContainerCPUAboveRequest
      expr: (sum by (cluster, namespace, pod, container) (rate(container_cpu_usage_seconds_total{container!="",container!="POD"}[5m])))
        / ((max by (cluster, namespace, pod, container) (kube_pod_container_resource_requests{resource="cpu",unit="core",container!=""}))
        > 0) > 1.5
      for: 30m
      labels:
        severity: info
        alert_family: container_cpu_request
        team: platform
      annotations:
        summary: CPU use exceeds request on {{ $labels.namespace }}/{{ $labels.pod }}
        description: '{{ printf "%.2f" $value }} times the request. CPU requests are not a hard usage limit; review
          sustained demand.'
        runbook_url: https://www.atomai.click/kubernetes-docs/en/ops/16-troubleshooting-playbook
  - name: docs.storage
    rules:
    - alert: NodeFilesystemUsageHigh
      expr: ((1 - node_filesystem_avail_bytes{fstype!~"tmpfs|overlay|squashfs|nsfs|tracefs"} / (node_filesystem_size_bytes{fstype!~"tmpfs|overlay|squashfs|nsfs|tracefs"}
        > 0)) > 0.85) and (node_filesystem_readonly{fstype!~"tmpfs|overlay|squashfs|nsfs|tracefs"} == 0)
      for: 5m
      labels:
        severity: warning
        alert_family: node_filesystem
        team: storage
      annotations:
        summary: Filesystem usage on {{ $labels.instance }} {{ $labels.mountpoint }}
        description: '{{ $value | humanizePercentage }} of reported capacity is unavailable. Check actual mount
          layout and workload storage.'
        runbook_url: https://www.atomai.click/kubernetes-docs/en/ops/16-troubleshooting-playbook
    - alert: NodeFilesystemUsageCritical
      expr: ((1 - node_filesystem_avail_bytes{fstype!~"tmpfs|overlay|squashfs|nsfs|tracefs"} / (node_filesystem_size_bytes{fstype!~"tmpfs|overlay|squashfs|nsfs|tracefs"}
        > 0)) > 0.95) and (node_filesystem_readonly{fstype!~"tmpfs|overlay|squashfs|nsfs|tracefs"} == 0)
      for: 5m
      labels:
        severity: critical
        alert_family: node_filesystem
        team: storage
      annotations:
        summary: Filesystem usage on {{ $labels.instance }} {{ $labels.mountpoint }}
        description: '{{ $value | humanizePercentage }} of reported capacity is unavailable. Check actual mount
          layout and workload storage.'
        runbook_url: https://www.atomai.click/kubernetes-docs/en/ops/16-troubleshooting-playbook
    - alert: PVCUsageHigh
      expr: (max by (cluster, namespace, persistentvolumeclaim) (kubelet_volume_stats_used_bytes{persistentvolumeclaim!=""}
        / (kubelet_volume_stats_capacity_bytes{persistentvolumeclaim!=""} > 0))) > 0.85
      for: 5m
      labels:
        severity: warning
        alert_family: pvc_usage
        team: storage
      annotations:
        summary: PVC usage on {{ $labels.namespace }}/{{ $labels.persistentvolumeclaim }}
        description: '{{ $value | humanizePercentage }} filesystem usage. This is not an EBS IOPS/throughput measurement.'
        runbook_url: https://www.atomai.click/kubernetes-docs/en/ops/16-troubleshooting-playbook
    - alert: PVCUsageCritical
      expr: (max by (cluster, namespace, persistentvolumeclaim) (kubelet_volume_stats_used_bytes{persistentvolumeclaim!=""}
        / (kubelet_volume_stats_capacity_bytes{persistentvolumeclaim!=""} > 0))) > 0.95
      for: 5m
      labels:
        severity: critical
        alert_family: pvc_usage
        team: storage
      annotations:
        summary: PVC usage on {{ $labels.namespace }}/{{ $labels.persistentvolumeclaim }}
        description: '{{ $value | humanizePercentage }} filesystem usage. This is not an EBS IOPS/throughput measurement.'
        runbook_url: https://www.atomai.click/kubernetes-docs/en/ops/16-troubleshooting-playbook
    - alert: PVCInodesHigh
      expr: max by (cluster, namespace, persistentvolumeclaim) (kubelet_volume_stats_inodes_used{persistentvolumeclaim!=""}
        / (kubelet_volume_stats_inodes{persistentvolumeclaim!=""} > 0)) > 0.9
      for: 5m
      labels:
        severity: warning
        alert_family: pvc_inodes
        team: storage
      annotations:
        summary: PVC inode usage on {{ $labels.namespace }}/{{ $labels.persistentvolumeclaim }}
        description: '{{ $value | humanizePercentage }} of reported inodes are used. The driver/filesystem must
          support these statistics.'
        runbook_url: https://www.atomai.click/kubernetes-docs/en/ops/16-troubleshooting-playbook
    - alert: PVCGrowthProjectionHigh
      expr: max by (cluster, namespace, persistentvolumeclaim) ((predict_linear(kubelet_volume_stats_used_bytes{persistentvolumeclaim!=""}[6h],
        24*3600) / (kubelet_volume_stats_capacity_bytes{persistentvolumeclaim!=""} > 0)) and (kubelet_volume_stats_used_bytes{persistentvolumeclaim!=""}
        / (kubelet_volume_stats_capacity_bytes{persistentvolumeclaim!=""} > 0) > 0.7)) > 1
      for: 1h
      labels:
        severity: warning
        alert_family: pvc_growth
        team: storage
      annotations:
        summary: PVC growth projection on {{ $labels.namespace }}/{{ $labels.persistentvolumeclaim }}
        description: A linear fit projects usage beyond current capacity within 24h. Check data coverage, resizing
          and nonlinear changes.
        runbook_url: https://www.atomai.click/kubernetes-docs/en/ops/16-troubleshooting-playbook
  - name: docs.nodes
    rules:
    - alert: NodeNotReady
      expr: max by (cluster, node) (kube_node_status_condition{condition="Ready",status="true"}) == 0
      for: 5m
      labels:
        severity: warning
        alert_family: node_ready
        team: platform
      annotations:
        summary: Node {{ $labels.node }} is not Ready
        description: An observed Node has Ready=false or unknown. Inspect conditions and events; this is not proof
          of termination.
        runbook_url: https://www.atomai.click/kubernetes-docs/en/ops/16-troubleshooting-playbook
    - alert: NodeDiskPressure
      expr: max by (cluster, node) (kube_node_status_condition{condition="DiskPressure",status="true"}) == 1
      for: 5m
      labels:
        severity: critical
        alert_family: node_disk_pressure
        team: storage
      annotations:
        summary: Node {{ $labels.node }} reports DiskPressure
        description: Kubelet reports disk pressure. Correlate filesystem space/inodes and eviction events.
        runbook_url: https://www.atomai.click/kubernetes-docs/en/ops/16-troubleshooting-playbook
    - alert: PDBHealthyBelowDesired
      expr: max by (cluster, namespace, poddisruptionbudget) (kube_poddisruptionbudget_status_desired_healthy -
        kube_poddisruptionbudget_status_current_healthy) > 0
      for: 5m
      labels:
        severity: warning
        alert_family: pdb_health
        team: platform
      annotations:
        summary: PDB healthy count below desired in {{ $labels.namespace }}
        description: '{{ printf "%.0f" $value }} fewer healthy Pods than desired for {{ $labels.poddisruptionbudget
          }}. This does not prove a policy was bypassed.'
        runbook_url: https://www.atomai.click/kubernetes-docs/en/ops/16-troubleshooting-playbook
  - name: docs.collection
    rules:
    - alert: KnownScrapeTargetDown
      expr: up == 0
      for: 5m
      labels:
        severity: warning
        alert_family: scrape
        team: platform
      annotations:
        summary: Cannot scrape {{ $labels.job }} at {{ $labels.instance }}
        description: A known target failed scraping. A target removed from discovery needs separate absence/inventory
          monitoring.
        runbook_url: https://www.atomai.click/kubernetes-docs/en/ops/16-troubleshooting-playbook
```

比率使用 `humanizePercentage`。Prometheus 告警注释不支持任意 Sprig `mul`/`div` 函数。不要把 `0.96` 格式化为 `0.96%`，也不要读取不存在的 `$labels.used_bytes`。`$value` 是表达式结果；其他操作数不会自动变成标签。

### 网络

对丢包计数器使用 `rate()`；其单位是包/秒。不要混淆每秒包数和每分钟包数。某些策略拒绝或瞬时丢包属于预期情况，因此应结合持续时间、流量和服务症状进行判断。

请以 bit/s 检查带宽：

```promql
rate(node_network_transmit_bytes_total{device!~"lo|veth.*|docker.*|br-.*"}[5m]) * 8
```

请根据实际 EC2 基线/突发合同、网络路径和 PPS 限制进行比较。要区分 Gbps 中的 `10^9` bit 与二进制 Gi 单位。`node_network_speed_bytes` 可能为零/未知，也可能是虚拟 NIC 声明的速度。RX+TX 并不总能作为全双工饱和比率。不要假设每个节点的分母都是 10 Gbps。

### CPU

CFS throttled-period 比率表示**发生限流的周期占比**，而不是损失的 CPU 时间。限流秒数除以实际 CPU 使用量，也不是简单的墙钟时间百分比。请使用能正确处理计数器的函数，并排除分母为零的情况。

超过 CPU requests 可能是正常的突发使用。仅凭高利用率、限流、iowait 或 steal，无法证明客户受到影响或确定根因。评估 limits/requests 时，应同时考虑服务延迟、配额、调度和 HPA 的影响。

类似 `process_cpu_seconds_total{job="containerd"}` 的表达式要求存在实际的进程 exporter/job。不要假设托管的 Auto Mode 服务会暴露与常规安装相同的 Deployment/DaemonSet 指标。

### 文件系统、PVC 和 inode

`kubelet_volume_stats_*` 为受支持的驱动程序/文件系统提供统计信息。PVC 使用量并不代表 EBS IOPS/吞吐量饱和情况，而且并非所有卷模式都会公开相同的统计信息。

容量为零或缺失不等于“已使用 0%”。应根据用途排除只读/虚拟文件系统，并检查实际挂载情况；`/var/lib/kubelet` 不一定是独立挂载点。

`container_fs_limit_bytes` 不一定等于 Kubernetes `resources.limits.ephemeral-storage`。应区分可写层、日志、emptyDir 和节点文件系统的计量方式。

`predict_linear` 会根据拟合趋势进行外推。调整大小、删除、缺失样本和非线性增长都会改变其解释方式。它不能保证在精确的期限内耗尽，也不能作为无条件自动扩容的依据。

## 根据安装情况匹配 CNI、DNS 和策略指标

### VPC CNI

常规 VPC CNI IPAM 端点和 cni-metrics-helper 的 CloudWatch 聚合使用不同的路径/名称。以下 gauge/counter 定义存在于 v1.23.1 中；使用前请验证已安装的版本和实际的 `/metrics`。

```promql
# Spare addresses in the currently allocated pool
awscni_total_ip_addresses - awscni_assigned_ip_addresses

# IPAM error counter
rate(awscni_ipamd_error_count[5m])

# Failure to obtain an available IP address
rate(awscni_no_available_ip_addresses[5m])
```

预留 IP 池没有剩余空间，本身并不能证明子网地址已耗尽，也不能证明所有新 Pod 都无法创建。请检查额外分配、前缀委派、ENI 限制、实际错误和子网容量。

不要给 `awscni_add_ip_req_count` 添加不存在的 `status="failed"` 标签，也不要杜撰 ENI 延迟直方图。请区分 Prometheus 原始指标名称与 cni-metrics-helper 重命名后的集群级 CloudWatch 聚合指标。

### DNS

`NXDOMAIN` 可能是合理的否定查询结果。请审慎定义失败和流量阈值。在采集 CoreDNS 指标的情况下，以下诊断表达式可计算 SERVFAIL/REFUSED 比率：

```promql
(
  sum by (cluster) (rate(coredns_dns_responses_total{rcode=~"SERVFAIL|REFUSED"}[5m]))
  or on (cluster)
  (0 * sum by (cluster) (rate(coredns_dns_responses_total[5m])))
)
/
(sum by (cluster) (rate(coredns_dns_responses_total[5m])) > 0)
```

采集失败和 DNS 查询失败是不同的情况。仅凭 `absent(up{job="coredns"} == 1)` 不能证明集群 DNS 无法使用。**纯 EKS Auto Mode 会将 CoreDNS 作为节点系统服务运行**；不要套用常规 CoreDNS Deployment 的假设。混合节点安装应检查其 DNS 架构。

### 网络策略丢弃

启用丢弃指标后，Cilium 1.20.3 Hubble 会导出包含原因/协议和已配置上下文标签的 `hubble_drop_total`。

```promql
sum by (cluster, reason) (
  rate(hubble_drop_total{reason="POLICY_DENIED"}[5m])
)
```

只有经过配置后才会提供命名空间上下文。策略丢弃本身并不意味着配置错误。请检查实际的 Cilium/Calico 发行版、功能和指标配置，不要杜撰通用的 `denied_packets` 指标。请参阅[经过审阅的 Cilium 可观测性章节](../service-mesh/cilium-service-mesh/04-observability.md)。

## Auto Mode 节点状态和终止原因

`NodeNotReady` 表示已观察到的 Node 的 Ready 状态为 false/unknown。它本身不能证明节点已终止、已替换或容量已耗尽。还应区分清单中缺少节点与 exporter 故障。

```promql
# Previously observed Nodes missing from current inventory: diagnostic only
max by (cluster, node) (kube_node_info offset 5m)
unless on (cluster, node)
max by (cluster, node) (kube_node_info)

# Currently retained Evicted Pod state, not a historical event counter
sum by (cluster, namespace) (kube_pod_status_reason{reason="Evicted"} == 1)
```

Pod 阶段/原因和删除时间戳都不是事件计数器。不要使用 `increase()` 将它们转换为某段时间内的驱逐次数，也不要添加不存在的 `reason="NodeDrain"` 标签。Pod 垃圾回收后，应保留 Kubernetes Events 和审计/运维日志以供追溯。

PDB 的 currentHealthy 数量低于 desiredHealthy 表示健康实例不足，并不能证明有人违反了其策略。应分别调查非自愿故障、直接更改副本数及其他原因。

### 托管的 Auto Mode 和自管理的 Karpenter

不要假设 Auto Mode 会公开自管理 Karpenter 控制器的采集端点。请使用受支持的 Node 状态、NodeClaim/NodePool 状态以及托管控制平面的审计日志。

AWS 的 Auto Mode 故障排查指南介绍了控制平面审计日志中的 `DisruptionBlocked`、`DisruptionTerminating`、`FailedScheduling` 和 `FailedDraining` 等事件。启用审计日志后，可将查询范围限定为实际集群日志组：

```text
fields @timestamp, @message
| filter @logStream like /kube-apiserver-audit/
| filter @message like /DisruptionBlocked|DisruptionTerminating|FailedScheduling|FailedDraining|NodeRepairBlocked/
| sort @timestamp desc
| limit 100
```

对于自管理的 Karpenter，请使用已安装版本的指标目录。当前 NodeClaim 终止计数器是聚合数据，并非完整的逐节点/逐原因审计记录。中断队列计数器可能包含 Spot 以外的消息类型。

`karpenter_nodepools_usage` 衡量的是**已配置资源**，而不是 CPU 繁忙程度。与 limits 比较前，请检查资源标签、单位、集群身份，以及 limits 是否缺失/为零。有待调度的 Pod 和空闲容量指标并不能证明 Pod 可被调度；亲和性、taints、拓扑和卷仍会产生影响。

## Alertmanager 配置和 Chart 接线

以下是**原生 Alertmanager YAML**。不要将其与 AlertmanagerConfig CRD 的结构化 matchers/驼峰式字段混用。原生 Alertmanager 不会自动替换 `${NAME}` 环境变量占位符。

### 准备文件和 Secrets

请在命名空间 `monitoring` 中准备以下对象：

| 对象 | 内容 |
|---|---|
| Secret `reviewed-alertmanager-config` | `alertmanager.yaml` 键 |
| ConfigMap `notification-templates` | `notifications.tmpl` 键 |
| Secret `notification-credentials` | `slack-default`、`slack-network`、`slack-storage`、`slack-info`、`pagerduty-routing-key` |

请使用已批准的 Secret 管理流程处理凭据。不要将真实 URL/密钥放入 Git、Helm values 或 PR 日志中。现代 Slack incoming webhook 会绑定到安装时所选的频道；修改 `channel` 字段并不能让一个 URL 对应多个频道。此示例使用单独的 URL 文件。

此处 PagerDuty 使用 Events API v2 routing key。`service_key`/`service_key_file` 仍是受支持的独立 v1 集成方式；请根据实际集成类型选择相应凭据。

```yaml
# alertmanager.yaml
global:
  resolve_timeout: 5m
route:
  receiver: default-slack
  group_by: [cluster, alertname, namespace, severity]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - receiver: oncall
      matchers: ['severity="critical"']
      group_wait: 10s
      repeat_interval: 1h
      continue: true
    - receiver: low-priority
      matchers: ['severity="info"']
      mute_time_intervals: [nightly-maintenance]
    - receiver: network-team
      matchers: ['team="network"']
    - receiver: storage-team
      matchers: ['team="storage"']
    # Explicit sibling fallback: a matched critical route does not fall back
    # to the root receiver merely because its continue flag is true.
    - receiver: default-slack

inhibit_rules:
  - source_matchers: ['severity="critical"', 'cluster!=""', 'alert_family!=""', 'instance!=""']
    target_matchers: ['severity="warning"', 'cluster!=""', 'alert_family!=""', 'instance!=""']
    equal: [cluster, alert_family, instance, job, device, mountpoint, fstype]
  - source_matchers: ['severity="critical"', 'cluster!=""', 'alert_family!=""', 'namespace!=""', 'pod!=""', 'container!=""']
    target_matchers: ['severity="warning"', 'cluster!=""', 'alert_family!=""', 'namespace!=""', 'pod!=""', 'container!=""']
    equal: [cluster, alert_family, namespace, pod, container]
  - source_matchers: ['severity="critical"', 'cluster!=""', 'alert_family!=""', 'namespace!=""', 'persistentvolumeclaim!=""']
    target_matchers: ['severity="warning"', 'cluster!=""', 'alert_family!=""', 'namespace!=""', 'persistentvolumeclaim!=""']
    equal: [cluster, alert_family, namespace, persistentvolumeclaim]

receivers:
  - name: default-slack
    slack_configs:
      - api_url_file: /etc/alertmanager/secrets/notification-credentials/slack-default
        send_resolved: true
        title: '{{ template "docs.title" . }}'
        text: '{{ template "docs.text" . }}'
  - name: network-team
    slack_configs:
      - api_url_file: /etc/alertmanager/secrets/notification-credentials/slack-network
        send_resolved: true
        title: '{{ template "docs.title" . }}'
        text: '{{ template "docs.text" . }}'
  - name: storage-team
    slack_configs:
      - api_url_file: /etc/alertmanager/secrets/notification-credentials/slack-storage
        send_resolved: true
        title: '{{ template "docs.title" . }}'
        text: '{{ template "docs.text" . }}'
  - name: low-priority
    slack_configs:
      - api_url_file: /etc/alertmanager/secrets/notification-credentials/slack-info
        send_resolved: true
        title: '{{ template "docs.title" . }}'
        text: '{{ template "docs.text" . }}'
  - name: oncall
    pagerduty_configs:
      - routing_key_file: /etc/alertmanager/secrets/notification-credentials/pagerduty-routing-key
        send_resolved: true
        severity: critical
        description: '{{ template "docs.title" . }}'
        details:
          alerts: '{{ template "docs.text" . }}'

templates:
  - /etc/alertmanager/configmaps/notification-templates/*.tmpl

time_intervals:
  - name: nightly-maintenance
    time_intervals:
      - location: Asia/Seoul
        times:
          - start_time: "02:00"
            end_time: "04:00"
```

严重告警会发送给 oncall，然后继续走团队专属的 Slack 路由。显式配置的最后一个同级回退路由也会将没有团队标签的严重告警发送到 Slack。匹配子路由后，仅设置 `continue: true` 并不会使告警回退到根接收器。

Info 使用单独的路径，并在**韩国首尔时区每天 02:00–04:00**静默。这不会累积每日摘要。重复/分组延迟不能代替基于日历的摘要处理流程。

抑制规则要求存在实际的集群/实体标识。Warning 和 critical 告警名称可以不同，但必须共享 `alert_family` 和预期的节点/容器/PVC 范围。缺少的标签可能会被视为空值并视为相等；未加限定的 `equal: [node]` 可能会抑制无关告警。

`resolve_timeout` 不会改变 `for`，也不会改变带有 EndsAt 的 Prometheus 告警的解除延迟。请单独检查接收器的实际行为，包括 `send_resolved`。

### 通知模板

`notifications.tmpl`：

```text
{{ define "docs.title" -}}
[{{ .Status | toUpper }}] {{ .GroupLabels.alertname }} — {{ .CommonLabels.cluster }}
{{- end }}

{{ define "docs.text" -}}
{{ range .Alerts -}}
[{{ .Status | toUpper }}] {{ .Annotations.summary }}
{{ .Annotations.description }}
{{ if .Labels.namespace }}Namespace: {{ .Labels.namespace }}
{{ end -}}
{{ if .Annotations.runbook_url }}Runbook: {{ .Annotations.runbook_url }}
{{ end -}}
{{ end -}}
{{ if .ExternalURL }}Alertmanager: {{ .ExternalURL }}
{{ end -}}
{{- end }}
```

即使 Firing/Resolved 告警属于同一分组，模板也会显示每个告警各自的状态。避免无条件显示空的运行手册按钮，也不要手动拼接包含未转义标签值的静默 URL。请使用经过身份验证的 Alertmanager UI 选择并静默特定告警。

例如，可通过以下 Kubernetes 对象提供配置和模板。此操作不会创建凭据 Secret：

```bash
kubectl --context "$TARGET_CONTEXT" -n monitoring create secret generic \
  reviewed-alertmanager-config --from-file=alertmanager.yaml \
  --dry-run=client -o yaml |
  kubectl --context "$TARGET_CONTEXT" -n monitoring apply -f -

kubectl --context "$TARGET_CONTEXT" -n monitoring create configmap \
  notification-templates --from-file=notifications.tmpl \
  --dry-run=client -o yaml |
  kubectl --context "$TARGET_CONTEXT" -n monitoring apply -f -
```

### kube-prometheus-stack values

```yaml
# alerting-values.yaml
# Merge into the reviewed full values for the actual release named "monitoring".
alertmanager:
  enabled: true
  alertmanagerSpec:
    useExistingSecret: true
    configSecret: reviewed-alertmanager-config
    secrets: [notification-credentials]
    configMaps: [notification-templates]
    externalUrl: https://alertmanager.example.com
    # No AlertmanagerConfig object is supplied in this example.
    # Adding one with this label is an explicit, separately reviewed choice.
    alertmanagerConfigSelector:
      matchLabels:
        alertmanager-config: platform-approved
    alertmanagerConfigNamespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: monitoring
prometheus:
  prometheusSpec:
    externalLabels:
      cluster: REPLACE_CLUSTER_NAME
    additionalAlertRelabelConfigs:
      - action: labeldrop
        regex: prometheus_replica
```

请将此内容合并到该发布的**完整审阅版 values**中，并替换集群名称和访问 URL。不要只用此片段覆盖现有安装。Chart 92.9.0 会将额外告警 relabel 配置渲染为 Prometheus 引用的 Secret。

```bash
helm template monitoring prometheus-community/kube-prometheus-stack \
  --version 92.9.0 --namespace monitoring \
  --values monitoring-values.yaml --values alerting-values.yaml \
  > rendered-monitoring.yaml
```

请先准备 Helm 仓库并审查 CRD/chart 升级。通过运维部署流程应用之前，请检查重复的默认规则，以及对不可用的托管控制平面/Auto Mode jobs 的假设。

外部标签用于标识发出的告警；它们不会自动为每个本地查询样本添加标签。如需进行 HA 去重，请移除每副本的身份标识，同时保留真实的集群身份。

此示例选择其基础 Secret 和带有明确标签的其他 AlertmanagerConfig 资源。添加匹配的 CRD 属于另一项配置合并，需要进行审慎审查。

## 验证和维护

如果已安装 PyYAML，可将 PrometheusRule spec 提取为原生规则文件：

```bash
python3 - <<'PY'
from pathlib import Path
import yaml
resource = yaml.safe_load(Path("prometheusrule.yaml").read_text())
Path("rules.yaml").write_text(yaml.safe_dump(resource["spec"], sort_keys=False))
PY
promtool check rules rules.yaml
```

请使用包含已准备模板/凭据路径的验证副本检查 Alertmanager 配置：

```bash
amtool check-config alertmanager.yaml --enable-feature=utf8-strict-mode
amtool config routes test --config.file=alertmanager.yaml \
  --verify.receivers=oncall,network-team severity=critical team=network
```

本地检查时，可用合成文件代替真实凭据。本章在移除所有出站集成的本地 Alertmanager 上验证了 17 条规则、18 个评估场景、10 种路由情况、2 个原生模板和 16 种抑制情况。实际 exporter 数据、频道身份验证和消息发送需要在连接环境后另行验证。

创建/到期一个静默会改变通知策略。请确认 Alertmanager URL、集群/命名空间/实体匹配器、负责人、原因和持续时间。静默不会停止 Prometheus 评估；长期处于静默状态的告警也不等于事件已解决。

OOMKilled 最近一次终止状态 gauge 可能会保留历史状态。请结合重启计数、终止时间和 Events 进行判断，不要总是增加 limits 或断定存在内存泄漏。

## 参考资料

- [Prometheus 告警规则](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [Alertmanager 配置](https://prometheus.io/docs/alerting/latest/configuration/)
- [VPC CNI v1.23.1 指标定义](https://github.com/aws/amazon-vpc-cni-k8s/blob/v1.23.1/utils/prometheusmetrics/prometheusmetrics.go)
- [Auto Mode 故障排查](https://docs.aws.amazon.com/eks/latest/userguide/auto-troubleshoot.html)
- [Karpenter 指标](https://karpenter.sh/docs/reference/metrics/)
- [Slack incoming webhooks](https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks/)
- [章节测验](../quizzes/ops/07-observability-alerts-quiz.md)

< [上一章：扩缩容](06-scaling-strategies.md) | [目录](README.md) | [下一章：可观测性分析](08-observability-analysis.md) >
