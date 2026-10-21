# 运维与维护

< [上一章：节点生命周期管理](./07-node-lifecycle.md) | [目录](./README.md) | [下一章：裸机操作系统设置](./09-bare-metal-os-setup.md) >

> **验证基线**：nodeadm 1.0.20；Cilium 1.18.3 CRD；Prometheus Operator 0.94.1；kube-prometheus-stack 92.9.0；Harbor 2.15.4。这些是经过审查的参考版本，并非通用的支持版本矩阵。
> **最后更新**：2026年10月18日

本文介绍 EKS Hybrid Nodes 环境的日常运维任务，包括监控、备份流程和故障排查。

## Harbor 漏洞扫描自动化

请使用 Harbor 内置的扫描全部计划任务，而不要使用携带管理员密码、且只枚举最新标签的 CronJob。在系统管理员界面中，打开 **Administration → Interrogation Services → Vulnerability → Schedule to scan all**。支持每小时/每日/每周/自定义计划；文档所述界面中的“每日”表示午夜。若维护窗口为 02:00，请核实已部署版本的自定义计划语法、时区和下一次执行时间。

Harbor 2.15.4 提供 GET/POST/PUT `/api/v2.0/system/scanAll/schedule`。请使用界面，或使用经过批准的 API 集成，并验证可信 CA、保护凭证且具备所需的系统级权限。项目机器人权限并不代表有权配置全局扫描。不要将管理员密码放入 Pod 环境变量/命令参数中，也不要禁用 TLS 验证。

记录扫描器可用性、漏洞数据库的新鲜度、扫描是否实际完成以及失败情况。提交请求或 API 返回空响应并不代表漏洞评估成功。不受支持的制品需要单独处理，而且全局扫描会消耗资源。自动化扫描所选制品时，必须枚举所有必需的分页和摘要、正确编码仓库路径并检查每个响应；仅扫描最新标签的循环无法覆盖整个仓库。

请参阅 [Harbor 指南](../container-registry/03-harbor.md)和[官方计划流程](https://github.com/goharbor/website/blob/main/docs/administration/vulnerability-scanning/schedule-scans.md)。

## 数据库备份流程

在复制数据之前，先明确恢复目标并完成清单盘点。恢复 Harbor 需要兼容的数据库元数据、Registry Blob/对象存储、配置以及受保护的密钥/加密密钥。仅导出 PostgreSQL 并不构成完整备份。现代 Harbor 已不再包含 Notary v1；不要假定存在 notarysigner/notaryserver 数据库。

[官方 Harbor Velero 流程](https://github.com/goharbor/website/blob/main/docs/administration/backup-restore/_index.md)会将仓库设为只读模式，并备份选定的 Kubernetes 资源/PV。此备份是**崩溃一致性备份，而非应用一致性备份**，不包含 Redis，可能丢失尚未同步的元数据/会话，也可能留下需要修复的任务。它涵盖内部数据库，不涵盖外部托管数据库。请选择受支持的快照/文件备份/数据迁移插件，并验证恢复站点能访问所有所需的卷/对象数据；仅有快照引用未必是可移植的副本。

以下仅是针对已验证的内部 PostgreSQL Pod 的**数据库组件转储示例**，其中 pg_dump/pg_restore 和本地身份验证已配置完成。外部数据库应使用各自经过身份验证的备份/恢复流程。命令参数中不会传递凭证。发生错误时停止操作并妥善保护部分输出；不要将其发布为已完成的转储。

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

列出归档内容并不能证明恢复成功。请使用兼容的 PostgreSQL/Harbor 版本测试恢复，并验证制品拉取、元数据、权限和集成。保护并校验完整备份清单，并协调只读模式、作业以及上传/GC 活动。操作失败后，不要未经状态评估就自动取消只读模式。

Redis BGSAVE 是异步操作；立即复制 dump.rdb 可能会得到较旧的一代数据。如果单独设计中包含 Redis 持久化，请通过其 Operator 验证操作完成情况、状态和数据代次。不要将这种自定义设计与排除 Redis 的官方教程混为一谈。本章未执行任何备份或恢复。

## Prometheus 指标采集

请分别处理主机、kubelet/容器和 GPU 指标。`node_cpu_seconds_total` 和 `node_memory_*` 来自 Node Exporter，而不是 kubelet 端点。使用已安装且经过审查的 Node Exporter/DCGM 配置，并验证实际主机挂载、权限、节点放置和指标可用性。Container Insights 无法通过 EC2 IMDS 提供 Hybrid 主机级指标。

以下发现示例使用 kube-prometheus-stack 92.9.0 中 Node Exporter Service 的标签/端口，发布版本为 `kube-prom`，位于 `monitoring` 命名空间。DCGM 部分假设 `gpu-operator` 中存在带有 `app: nvidia-dcgm-exporter` 标签的已验证 Pods，并且这些 Pods 有一个名为 `metrics` 的容器端口；请根据已安装的 exporter 进行调整。这两个资源都不会安装 exporter。请匹配 Prometheus 资源的 monitor/命名空间选择器，并避免通过现有 monitor 重复抓取同一个 exporter。

`attachMetadata.node` 会提供 Node 发现元数据；它不会自动将标签复制到指标。ServiceMonitor 需要 Prometheus >=2.37，PodMonitor 需要 >=2.35，并且 Prometheus 需要具备 Node 的 `list`/`watch` 权限。重标记会保留实际具有 `eks.amazonaws.com/compute-type=hybrid` 标签的节点，并创建稳定的 `node`/`compute_type` 目标标签。不要根据 SSM Node 名称前缀推断 Hybrid 节点放置情况。

这些示例使用 exporter 受保护的 HTTP 指标端点，而不是 kubelet HTTPS 端点。请限制采集器的网络连接。如果流量经过不可信边界，请配置 exporter TLS/身份验证，或使用经过审查的代理及相应的 CA/授权设置；不要使用 `insecureSkipVerify`。kubelet 抓取应保留在单独配置的身份验证和 CA 验证机制中。

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

### Grafana 仪表板查询示例

这些查询需要上述目标标签以及兼容的 exporter 指标。请验证单位、GPU/MIG 标识、不支持值/错误哨兵值、抓取缺失情况和重复序列。GPU 帧缓冲区用量应除以总容量（`used + free`），而不是可用容量；容量为零的序列会被排除。这些查询是可在本地测试的表达式，并非此环境中的测量结果。

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

## Direct Connect 性能验证

请将测试计划与 AWS 服务保证区分开来。此前给出的 RTT <5ms、波动 <2ms、丢包 <0.01% 和吞吐量 >1Gbps 示例仅是说明性的规划目标，并非测量结果或 Direct Connect 的通用承诺。应根据实际位置、电路、端点、工作负载和合同容量选定目标；并确认测量路由确实使用 Direct Connect，而非 VPN 或其他路径。

`ping` 会报告 ICMP RTT；在 Linux iputils 中，还会报告 RTT mdev。该离散程度与单向时延变化或 iperf3 的 UDP 抖动不是同一统计量。ICMP 的过滤/降优先级处理可能不同于应用流量。包含 1,000 个数据包的测试，其丢包率增量为 0.1%；观察到零丢包并不能证明长期丢包率低于 0.01%。

请使用已获批准且已运行 iperf3 的私有测试服务器、协调好的测试窗口、明确的流量上限以及受保护的结果存储。不要对 EKS API 端点运行 iperf3。以下有界示例需要 Bash、Python3、iputils ping、GNU timeout 和支持所示选项的 iperf3。任何一步失败都会停止后续流程；缺少工具、JSON 无效或 iperf3 出错，都不代表性能测试通过。

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

此限速 TCP 测试不能证明链路的最大容量。请检查接收端吞吐量、重传、方向、持续时间和拥塞情况。如需单独获批的 UDP 测试，请使用 `--udp` 和明确的比特率，然后保留并解读该版本 JSON 中接收端的丢包/抖动数据。应如实记录失败/跳过的探测。本次审计未执行网络负载测试。

## 证书续期管理

请明确要检查的是哪张证书：Harbor TLS 服务器证书、其 CA 链、kubelet 服务证书、EKS 控制平面 CA，还是 IAM Roles Anywhere 主机证书。CA 证书有效并不能证明服务器叶证书有效，Node Ready 心跳也不能作为证书过期的证据。EKS 控制平面证书由 AWS 管理；不要将 kubeadm 续期命令用作 EKS 修复流程。

如果证书缺失、不可读、无效，或将在示例设定的 30 天警告窗口内过期，以下本地过期检查会失败。它不会验证证书链、主机名、吊销状态，也不会检查服务实际提供的证书是否就是该证书。请使用以下经过验证的 TLS 连接检查服务端点，并参考[凭证生命周期流程](./07-node-lifecycle.md)续期主机证书。

```bash
set -euo pipefail
: "${CERT_PATH:?Set the actual certificate file to inspect}"
test -r "$CERT_PATH"
openssl x509 -in "$CERT_PATH" -checkend 2592000 -noout
```

跟踪实际签发者/所有者、配置的证书路径、到期时间和告警投递情况。kubelet 服务端/客户端凭证路径取决于配置；仅启用 serverTLSBootstrap 并不代表已批准服务端 CSR，也不会轮换 IAM Roles Anywhere 证书。

## Ingress 配置

### ALB Ingress（ip 目标模式）

自管理的 AWS Load Balancer Controller 可以使用 `alb.ingress.kubernetes.io/target-type: ip` 注册可路由的 Hybrid Pod IP。路由、返回流量、安全组/防火墙以及 EKS 远程 Pod 网络配置必须相互匹配。

AWS 的混合模式 Webhook 配方会将控制器放置在云节点上。这是该设计的放置建议，并不意味着 Webhook 绝不能在 Hybrid Nodes 上运行：附加组件指南允许将其放置在 Hybrid Nodes 上，前提是控制平面能够访问配置的远程 Pod CIDR。优先使用明确的管理放置标签，不要使用 `compute-type NotIn [hybrid]`，因为它也会匹配没有此类标签的节点。以下示例标签只能分配给已验证符合条件的云节点。

```yaml
# Fragment under the controller Deployment's spec.template.spec:
nodeSelector:
  infrastructure.example.com/location: aws
```

### Cilium Ingress Controller

本节中的 Cilium Ingress 和 Gateway API 示例要求 Cilium 配置启用 L7。它们不适用于配置为 [EKS Hybrid Nodes Gateway](./10-hybrid-nodes-gateway.md) 的同一 Cilium 安装：[AWS 要求的 VTEP 配置](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-gateway-cni.html)会设置 `vtep.enabled=true` 和 `l7Proxy=false`。启用这些功能之前，请先选择网络设计。此限制针对的是 Cilium 的 L7 代理功能；它并不禁止 HTTP 应用使用网关的路由网络路径。

Cilium 1.18.3 的上游 Ingress 前提条件包括 NodePort 支持（或 kube-proxy 替代）、L7 代理支持以及可用的负载均衡器暴露路径。以下片段并不授权在混合集群中更改云节点的 CNI。请保留经过审查的 Hybrid Cilium 配置，并确认 AWS 对额外功能的支持边界。更改专用/共享模式可能会改变地址并中断现有连接。

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

请安装所选控制器版本支持的 Gateway API CRD 和资源版本，验证其 NodePort/kube-proxy 替代方案及 L7 前提条件，并检查 GatewayClass/Gateway/Route 状况。仅设置一个 Helm 标志并不会安装这些 CRD，也不能确保外部可达。

```yaml
# Required Gateway API CRDs and controller prerequisites must already be met:
gatewayAPI:
  enabled: true
```

### 负载均衡器 IPAM（Cilium）

以下地址池使用 `cilium.io/v2` API，该 API 已根据 1.18.3 CRD 验证，并且只选择带有明确标签的 Service。请将示例 CIDR 替换为网络清单中预留且不重叠的地址范围。分配 IP 并不会向路由器通告该地址，也不保证数据路径可用。

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

## 负载均衡

### NLB（ip 目标模式）

对于自管理的 AWS Load Balancer Controller，请使用由该控制器管理的 `LoadBalancer` Service，并设置 `spec.loadBalancerClass: service.k8s.aws/nlb` 和 `service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip`；或者对所选控制器使用文档所述的 `aws-load-balancer-type: external` 所有权路径。仅设置目标类型注解并不能选择控制器。Hybrid Pod 目标和返回路由必须能从 AWS 访问；请审慎选择内部/公共暴露方式、子网和访问控制。

这不是 EKS Auto Mode 的所有权配置方案。未经审查替换和流量影响，不要将现有 Service 的 class/controller 作为原位迁移来切换。

### Cilium LB + BGP

请使用已安装的 `cilium.io/v2` Schema。Service 地址类型应位于 `advertisements[].service.addresses` 下。示例仅通告带有 `exposure: onprem-bgp` 标签的 Service 的 LoadBalancer IP；它不会使用实际上会选中所有 Service 的 `NotIn` 选择器。

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

配置 CiliumBGPClusterConfig 节点/对等体选择，以及 CiliumBGPPeerConfig 地址族。对等体配置中的通告选择器必须匹配 `advertise: hybrid-services`；Service 选择器必须匹配实际的 Service 标签。启用经过审查的 BGP 控制平面，建立路由器会话，并验证已接受的路由、下一跳、返回路径和流量策略。仅配置 IPPool/Advertisement 并不完整。应用更改前，请参阅[网络基础](./02-network-configuration.md)和已安装版本的 BGP 文档。

## 附加组件详细设置

### CloudWatch Observability Agent

请使用受支持的 Pod Identity 配置，并验证工作负载实际的 IAM 关联和权限。尽管名称如此，当前 AWS 流程仍要求设置 Hybrid 兼容变量 `RUN_WITH_IRSA`。请将其添加到现有 `AmazonCloudWatchAgent` 资源的 **spec.env 列表**中，并保留 `K8S_NODE_NAME` 等条目；它并不是 EKS 附加组件 configurationValues 中任意位置的顶级 `env`。

```yaml
# Add this item to the existing AmazonCloudWatchAgent.spec.env list:
- name: RUN_WITH_IRSA
  value: "True"
```

编辑前，请检查 `amazon-cloudwatch` 命名空间中的 `amazoncloudwatchagents/cloudwatch-agent`，并审查附加组件/Operator 如何协调该配置。之后确认 Agent 已完成滚动更新并开始采集。Hybrid 集群/工作负载/Pod/容器指标可用，但由于缺少对 EC2 IMDS 的依赖，无法获取节点级 Container Insights 指标。如果其 Operator 运行在 Hybrid Nodes 上，请确保控制平面能够访问 Webhook。

### EKS Pod Identity Agent

| 主机操作系统 | 文档所述最低版本 | Hybrid DaemonSet / 凭证路径 |
| --- | --- | --- |
| Ubuntu、RHEL、AL2023 | 附加组件 1.3.3-eksbuild.1 | `hybrid`；`/eks-hybrid/.aws/credentials` |
| Bottlerocket（受支持的 VMware 变体） | 附加组件 1.3.7-eksbuild.2 和 OS 1.39.0 | `hybrid-bottlerocket`；`/var/eks-hybrid/.aws/credentials` |

这些是功能最低版本，并非建议安装旧版本。请选择当前兼容的附加组件版本，并检查其配置 Schema。在 Ubuntu/RHEL/AL2023 上，请将以下片段合并到每台主机现有的完整 NodeConfig 中：

```yaml
# Merge this fragment into each host's complete, protected NodeConfig:
spec:
  hybrid:
    enableCredentialsFile: true
```

AWS 要求在每台受影响的主机上按计划执行 `nodeadm init -c file:///path/to/nodeconfig.yaml` 以协调配置，包括已加入集群的节点。不要盲目重新初始化每个生产节点：应保留其身份/配置，遵循生命周期流程，并逐台验证。Bottlerocket 应使用其文档所述的设置路径，而不是此 nodeadm 片段。这些临时凭证文件属于敏感信息；不要将其打印出来。

对于非 Bottlerocket Hybrid DaemonSet，附加组件配置包括：

```json
{
  "daemonsets": {
    "hybrid": {
      "create": true
    }
  }
}
```

对于 Bottlerocket，请使用所选版本文档中所述的 `hybrid-bottlerocket` 配置。检查并合并现有设置。仅当附加组件不存在时才创建；更新现有附加组件时，应使用经过审查的冲突处理方式，不要盲目使用 create 或 OVERWRITE。Agent 和凭证文件不会自动创建每个应用的 Pod Identity 关联：请验证命名空间、ServiceAccount、IAM 角色信任/权限、SDK 凭证解析和授权是否成功。

## 混合模式 Webhook 运维

在 AWS 支持的混合模式方案中，VPC CNI 在云节点上运行，Cilium/Calico 在 Hybrid Nodes 上运行。AWS 建议在此方案中将 Webhook 放置在云节点上。托管在 Hybrid 节点上的 Webhook 还需要可路由的远程 Pod CIDR 和控制平面可达性；应检查实际端点，而不要假定每个 Webhook 都必须或都能在任意位置运行。

### CoreDNS 放置

针对这种混合模式设计，AWS 建议至少在云节点上运行一个 CoreDNS 副本，并在 Hybrid Nodes 上运行一个副本。请验证期望副本数至少为两个、具备符合条件的容量、选择器、容忍度以及真实端点。单独使用 `maxSkew: 1` 不会创建两个域，也不保证每个域各有一个 Pod；此外，云节点可能没有 `eks.amazonaws.com/compute-type` 标签。

对于支持 `minDomains` 的集群，此 Pod-spec 片段使用明确的双域管理标签。只为指定的 DNS 节点添加标签，并为每个符合条件的节点设置经过验证且值恰为 `aws` 或 `onprem` 的 `location`。确保现有亲和性/容忍度兼容，验证 CoreDNS Pod 标签，并通过附加组件支持的配置机制协调更改。

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

在有两个符合条件的域且至少有两个副本时，严格分散调度会限制 Pod 跨这两个域分布。如果某个域没有容量，新副本可能会一直处于 Pending；这是可用性方面的取舍，并不保证故障转移。请测试实际的 DNS Service/EndpointSlices 以及本地/远程解析。在包含 Auto Mode 的集群中，应将其节点本地 DNS 系统服务与非 Auto 节点仍然需要的 Deployment 区分开来。

<span id="per-add-on-nodeaffinity-settings-guide"></span>

### 各附加组件放置指南

| 附加组件 | 此设计中的放置方式 | 必要检查 |
| --- | --- | --- |
| AWS Load Balancer Controller | 按照 AWS 混合模式方案放置在云节点上 | Webhook 可达性、正向标签、Hybrid IP 目标可路由 |
| CloudWatch Agent/Operator | Agent 运行在受支持的目标节点上；Operator Webhook 最好放置在云节点上 | IAM/Agent 健康状况；不包含 Hybrid 节点级指标 |
| cert-manager | Webhook 最好放置在云节点上；也可以放置在可路由的 Hybrid 节点上 | 控制平面访问和远程 Pod 网络 |
| Metrics Server | 放置在云节点上，或使用可访问的 Hybrid Pod 端点 | 控制平面到 Pod、Metrics Server 到 kubelet 的路径 |
| CoreDNS | 验证云节点和 Hybrid 节点上都有副本 | 符合条件的域、容量和实际 DNS 流量 |
| Cilium/Calico | 在 AWS 支持的混合 CNI 设计中放置在 Hybrid 节点上 | 保留云节点上的 VPC CNI |

## 网络中断期间的行为和准备工作

本节介绍 Direct Connect 或 VPN 短暂中断或网络停止响应时，哪些功能会继续运行、哪些会停止。Hybrid Nodes 并非为频繁断连的 DDIL 环境而设计，并且假设与 AWS 之间的连接可靠（参见[概述](./README.md)）。

### 集群和工作负载在断连期间的情况

| 区域 | 行为 |
|---|---|
| 正在运行的 Pod | 会继续在节点上运行。kubelet 无法续租 Lease，因此 Node 的 Ready 状况会变为 `Unknown`，并添加 `node.kubernetes.io/unreachable` 污点（`NoSchedule`，满足相应条件时还会添加 `NoExecute`）。 |
| Pod 故障转移 | 普通 Pod 默认具有 300 秒的 `not-ready` 和 `unreachable` NoExecute 污点容忍时间。应用相关的 NoExecute 污点并且该容忍时间到期后，控制平面会将 Pod 标记为待删除；控制器可以在符合条件的节点上创建替代 Pod。没有匹配容忍度的 Pod 会被驱逐，无需等待这 300 秒。不可达节点上的原始容器可能会继续运行，直到 kubelet 重新连接。DaemonSet Pod 默认会无限期容忍这些污点。 |
| Zone 标签 | 仅有 Zone 标签并不能阻止驱逐。如果整个 Zone 不可达，但另一个 Zone 仍有 Ready 节点，驱逐仍可能继续。如果所有 Zone 都没有 Ready 节点，Kubernetes 会取消驱逐；其他 Zone 健康阈值和集群规模也会影响行为。请参阅 [AWS Pod 故障转移指南](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-kubernetes-pod-failover.html)中的场景。Hybrid 节点没有 cloud-controller-manager，因此请使用 nodeadm `--node-labels` 设置每个数据中心的 Zone。 |
| Cilium | Agent 健康状况与控制平面访问相关，因此断连期间 Agent 会持续重启，Cilium BGP Control Plane 会话也可能中断（CFP #31702，这是 Cilium 1.17 中的可选改进）。AWS 示例使用的 MetalLB L2 模式在断连期间保持稳定。 |
| AWS 服务依赖项 | 断连期间，ECR 镜像拉取、CloudWatch 和 Amazon Managed Service for Prometheus、ALB/NLB、S3 及 RDS 等区域性服务不可用。 |
| 本地故障排查 | API Server 不可达，因此请在主机上使用 `crictl pods`、`crictl ps` 和 `crictl logs <container>`，而不要使用 `kubectl`。 |

### 凭证和重新连接

| 项目 | SSM 混合激活 | IAM Roles Anywhere |
|---|---|---|
| 临时凭证 | 固定为一小时（不可更改）。正常运行时会在到期前自动轮换，不影响节点或应用。 | 默认一小时；通过配置文件的 `durationSeconds` 最长可达 12 小时。节点 IAM 角色的 `MaxSessionDuration` 必须更长。 |
| 断连期间 | 因无法访问 SSM 区域端点，刷新会失败；长时间断连时凭证可能过期。 | 无法访问 AWS 时无法获取新凭证。 |
| 恢复连接后 | 重试使用指数退避，SSM Agent **3.3.808.0 及更高版本**的退避上限为 30 分钟。**网络恢复后，节点可能需要长达 30 分钟才能重新连接**；节点的重连时间各不相同，因此 Pod 可能会故障转移到先恢复连接的节点。 | kubelet 会通过 `aws_signing_helper credential-process` 按需获取凭证，因此通常会在**几秒内**重新连接。 |
| 加快恢复 | 重启 SSM Agent 以强制刷新（见下方命令）。 | 证书有效时无需操作。请配置证书到期通知。 |

SSM Agent 版本、重启和日志：

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

断连期间，日志会重复显示 `Retrieve credentials produced error: RequestError: send request failed` 和 `Sleeping for ... before retrying retrieve credentials`；刷新成功后会记录 `Credentials ready`。

### 准备工作清单

- **冗余连接**：为 Direct Connect 配置冗余，或保留 Site-to-Site VPN 作为备份。
- **检测断连**：启用 EKS 控制平面 Controller Manager 日志，并为包含 `status="NodeNotReady"` 的 `Recording status change event message for node` 消息创建 CloudWatch 指标筛选器和告警。当 TGW `BytesIn`/`BytesOut` 或 VGW `TunnelDataIn`/`TunnelDataOut` 低于正常值时发出告警。CloudWatch Network Monitor 可显示丢包和延迟。
- **SSM Agent 版本**：保持版本为 3.3.808.0 或更高，以将重试间隔上限设为 30 分钟。
- **Zone 标签**：为每个数据中心设置 `topology.kubernetes.io/zone`。
- **调整驱逐设置**：对于不易迁移的应用，请增加 `tolerationSeconds`。较长的值也会延迟从实际发生故障的节点迁移 Pod。

```yaml
# Fragment under the Deployment's spec.template.spec
tolerations:
  - key: "node.kubernetes.io/unreachable"
    operator: "Exists"
    effect: "NoExecute"
    tolerationSeconds: 1800
```

- **凭证提供程序**：如果断连频繁且快速重连很重要，可考虑使用较长 `durationSeconds` 的 IAM Roles Anywhere。在一个集群中只使用一个提供程序。
- **次要可观测性路径**：配置 ADOT Collector 将数据发送到多个后端，以便在区域性服务不可达时仍能保持可见性。

参考资料：
- [网络断连期间的主机凭证](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-host-creds.html)
- [网络断连期间保持稳定的最佳实践](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-network-disconnection-best-practices.html)
- [网络断连期间的 Kubernetes Pod 故障转移](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-kubernetes-pod-failover.html)

## 常见故障排查

### ImagePullBackOff 诊断

读取 Pod 事件，并检查所引用 Secret 的名称/类型；不要解码或打印仓库凭证。Secret 必须位于 Pod 所在的命名空间。请通过凭证所有者确认 Registry 主机名、所需的仓库权限和凭证到期时间；仅凭元数据无法证明身份验证成功。

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

请从实际主机/网络路径执行 TLS 检查，并启用可信 CA 和主机名验证。不要使用 curl -k，也不要将未经身份验证的 Registry 401 响应解读为 TLS 故障。此示例需要 Bash、OpenSSL 和 GNU timeout。

```bash
set -euo pipefail
: "${HARBOR_HOST:?Set the registry DNS name, without scheme or port}"
: "${HARBOR_CA_FILE:?Set the approved CA bundle file}"
timeout 10s openssl s_client -connect "$HARBOR_HOST:443" \
  -servername "$HARBOR_HOST" -verify_hostname "$HARBOR_HOST" \
  -verify_return_error -CAfile "$HARBOR_CA_FILE" </dev/null
```

若要在 Pod 内测试 DNS/网络，请使用经批准且按摘要固定的诊断镜像、专用命名空间，并明确将其放置在受影响的 Hybrid Node 上。任意使用未固定版本的调试 Pod 可能会运行在云节点上，从而测试错误的网络路径。请分别审查 Pod 创建/删除操作，并保留限定范围内的测试结果。

### DNS 解析问题

请检查实际的 CoreDNS Deployment/Pods、Service 和 EndpointSlices、云端/本地放置情况、DNS 配置和网络可达性。在受影响工作负载的环境中测试 Registry 名称和 kubernetes.default.svc.cluster.local。API、DNS 或日志访问失败属于未知观测结果，并不代表检查成功。

不要将重启所有 CoreDNS Pod 作为默认诊断操作。应先确定故障层，然后协调任何重启，并检查冗余和恢复情况。包含 Auto Mode 的混合集群可能具有节点本地 DNS 行为；请确认故障 Pod 实际使用的解析路径。

### 节点连接问题

请使用清单中记录的实际 Node 名称和对应主机。由 SSM 支持的 Node 名称不一定以 hybrid- 开头，也不一定能解析为主机名。

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

检查凭证提供程序和特定于操作系统的 Agent 单元（包括适用情况下基于 snap 安装的 Ubuntu SSM）。对于网络/身份验证诊断，请按照已验证的 `nodeadm debug -c file:///etc/eks/nodeconfig.yaml` 流程，以 root 权限运行并私下保留输出。该操作会连接 AWS 和集群；不要记录已签发的凭证，也不要禁用 TLS 验证。

经过审查的 1.0.20 CLI 中没有 `nodeadm reset` 子命令。NotReady 并不是盲目注销/重新初始化主机的理由。确定故障原因后，请按照[恢复和身份协调流程](./07-node-lifecycle.md)操作，同时保留挂载/数据并记录节点/SSM 身份。

## 验证范围和参考资料

本地检查涵盖固定版本的资源 Schema、使用合成样本测试的四个 PromQL 表达式，以及十一个备份/网络命令替身案例。未执行任何 AWS/Kubernetes 更改、实际备份/恢复、网络负载测试、BGP 会话、exporter 抓取或生产环境滚动更新。部署前，请依据 AWS 当前支持文档选择 EKS/OS/CNI/附加组件组合。

- [AWS Hybrid 附加组件](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)
- [AWS Hybrid Webhook](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-webhooks.html)
- [AWS Hybrid 升级](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-upgrade.html)
- [Prometheus Operator API](https://prometheus-operator.dev/docs/api-reference/api/)
- [Cilium 1.18.3 Ingress 前提条件](https://github.com/cilium/cilium/blob/v1.18.3/Documentation/network/servicemesh/ingress.rst)
- [Cilium 1.18.3 LoadBalancer IPPool CRD](https://github.com/cilium/cilium/blob/v1.18.3/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumloadbalancerippools.yaml)
- [iperf3 调用方式](https://software.es.net/iperf/invoking.html)
- [Kubernetes 污点容忍度](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)


---

< [上一章：节点生命周期管理](./07-node-lifecycle.md) | [目录](./README.md) | [下一章：裸机操作系统设置](./09-bare-metal-os-setup.md) >
