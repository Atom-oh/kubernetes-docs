# Amazon EKS 存储 - 第 3 部分：监控、故障排查、成本优化与安全

> **最后更新**: October 16, 2026

本文档是 Amazon EKS 存储系列的第三部分，也是最后一部分，涵盖存储监控、故障排查、成本优化和安全。

## 目录

1. [存储监控](#storage-monitoring)
2. [存储故障排查](#storage-troubleshooting)
3. [存储成本优化](#storage-cost-optimization)
4. [存储安全](#storage-security)
5. [存储管理最佳实践](#storage-management-best-practices)

## 存储监控

结合后端、Kubernetes 和应用层的观测数据。后端 I/O 计数器无法测量文件系统可用空间，Kubernetes 就绪状态也不能证明数据库一致性。创建告警前，记录单位、维度、聚合周期以及缺失数据的处理方式。

<!-- Diagram repair pending: ServiceMonitor configures Prometheus discovery; node-exporter is not a PVC usage exporter.
![Diagram showing three parallel EKS storage-monitoring pipelines: AWS CloudWatch turning EBS, EFS and FSx for Lustre metrics into key monitoring metrics, alarms and a dashboard; Prometheus feeding ServiceMonitor/PodMonitor discovery into Grafana plus PrometheusRule alert rules; and a volume-usage exporter DaemonSet driving custom metrics and alerts.](../.gitbook/assets/en-eks-04-eks-storage-part3-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part3-0.html)
-->

### 使用 CloudWatch 进行监控

EBS/EFS/FSx 无需 Kubernetes exporter 即可发布其服务指标。访问 CloudWatch 查询和可视化功能仍需要相应的 IAM 权限。get-dashboard 调用会检索已存在的 dashboard 定义；它不会创建 dashboard，也不会启用指标。

#### EBS 卷指标

| 指标 | 正确解读 |
|---|---|
| VolumeReadBytes / VolumeWriteBytes | Sum 是所选周期内传输的字节数；除以周期秒数即可得到字节/秒 |
| VolumeReadOps / VolumeWriteOps | Sum 是已完成的操作数；除以周期秒数即可得到 IOPS |
| VolumeTotalReadTime / VolumeTotalWriteTime | Sum 是累积的操作秒数；除以对应操作的 Sum 可得平均秒数/操作，计算时应防止操作数为零 |
| VolumeQueueLength | 待处理 I/O 量规；Average/Maximum 有助于区分持续排队和峰值 |
| BurstBalance | gp2、st1 和 sc1 的剩余积分；不是 gp3 的积分指标 |

对于受支持的 Nitro 附加卷，当前指标还包括 VolumeAvgIOPS (Ops/s)、VolumeAvgThroughput (KiB/s)、VolumeAvgReadLatency/VolumeAvgWriteLatency（毫秒）以及超限/停滞 I/O 检查。请检查每项指标在 Multi-Attach、计算资源和可用区方面的限制。已附加的卷会发布标准卷指标；缺失数据不会自动视为零使用量。当操作重叠时，已有的时间计数器可能会超过实际经过的时间周期。

#### EFS 文件系统指标

TotalIOBytes、DataReadIOBytes、DataWriteIOBytes 和 MetadataIOBytes 描述的是字节数，而不是已经标准化的传输速率。将相应的 Sum 除以周期即可得到字节/秒。MeteredIOBytes 反映 EFS 吞吐量计量，包括读取折扣；它不能与原始传输字节数互换。PermittedThroughput 是速率。比较周期和单位一致的指标，并根据需要监控 ClientConnections、与模式相适应的 PercentIOLimit 以及存储类别。BurstCreditBalance 适用于 Bursting 吞吐量，不适用于 Elastic 吞吐量。

#### FSx for Lustre 指标

DataReadBytes/DataWriteBytes 和 DataReadOperations/DataWriteOperations 使用 FileSystemId；Sum/周期可得吞吐量或操作数/秒。**NetworkThroughputUtilization 是有效指标**：它按对象存储服务器 (OSS) 统计，维度包括 FileSystemId 和 FileServer，并报告利用率百分比。FreeDataStorageCapacity 按 OST 统计，维度包括 FileSystemId 和 StorageTargetId。检查每个目标的不平衡情况以及时间对齐的容量量规；对量规随时间求和无法得出当前可用容量。

LogicalDiskUsage 和 PhysicalDiskUsage 也是有效指标：它们分别描述未压缩的逻辑字节数和压缩后的物理字节数。文件系统级聚合有助于评估压缩效果，但不会将按预置容量计费变成仅按使用量计费。

### 使用 Prometheus 和 Grafana 进行监控

复用监控负责人已有的技术栈。对于经过审查的新安装，已发布的 kube-prometheus-stack92.9.0 chart 是经验证的参考版本，搭配 operator0.94.1；这并不是现有集群的自动升级指令。以下命令只渲染清单。准备 `monitoring/grafana-admin`，其中包含 admin-user/admin-password 键，并使用本章中可展开的 ebs-gp3 类。根据实际集群版本、存储容量和保留期限进行调整。告警传递、Grafana 持久化、可用性以及 kubelet TLS/身份验证默认值仍需结合具体部署进行审查：

```yaml
grafana:
  admin:
    existingSecret: grafana-admin
    userKey: admin-user
    passwordKey: admin-password
prometheus:
  prometheusSpec:
    retention: 14d
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: ebs-gp3
          accessModes:
          - ReadWriteOnce
          resources:
            requests:
              storage: 20Gi
```



```bash
set -euo pipefail
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update prometheus-community
helm template prometheus prometheus-community/kube-prometheus-stack \
  --version 92.9.0 --namespace monitoring --kube-version 1.36.0 \
  --include-crds -f monitoring-values.yaml > monitoring-review.yaml
```

ServiceMonitor 会先选择 **Service**，再选择其端点；其 namespaceSelector 和 Prometheus 实例的 ServiceMonitor 选择器必须同时匹配。EBS CSI1.66 的 Helm chart 默认将 controller.enableMetrics 设为 false。对于由该 chart 管理的安装，请与现有负责人一起审查这些配置；它们会启用驱动的3301指标端点、sidecar 指标 Service 和生成的 ServiceMonitor。release 标签须与实际 Prometheus 选择器匹配：

```yaml
controller:
  enableMetrics: true
  serviceMonitor:
    labels:
      release: prometheus
```

EKS 托管 add-on 可能提供不同的配置选项；请检查其版本、配置和实际资源，而不要将 Helm 配置应用到该 add-on。只有在负责人已公开下方所示 Service，且尚未创建匹配的 monitor 时，以下独立 ServiceMonitor 才是**替代方案**。不要将它与功能等效的已生成 monitor 一起部署：

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: csi-metrics-reviewed
  namespace: monitoring
  labels:
    release: prometheus
spec:
  namespaceSelector:
    matchNames:
    - kube-system
  selector:
    matchLabels:
      app: ebs-csi-controller
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
```



```bash
set -euo pipefail
kubectl -n kube-system get svc ebs-csi-controller -o yaml
kubectl -n kube-system get endpointslice \
  -l kubernetes.io/service-name=ebs-csi-controller -o wide
kubectl -n monitoring get prometheus -o yaml
```

确认选定的目标状态为 Up，并且公开了预期指标。驱动和 provisioner/attacher/resizer/snapshotter 各自有独立的指标端点；单个驱动 Service 不会采集所有 sidecar 的指标。CSI API 操作延迟不同于应用/EBS 数据 I/O 延迟。

### 文件系统使用量与告警

对于 CSI 驱动实现了所需卷统计信息的卷，使用经过身份验证的 kubelet 指标 kubelet_volume_stats_*。kube-state-metrics 提供对象状态/请求信息，node-exporter 提供主机文件系统指标；安装另一个 node-exporter DaemonSet 并不会产生每个 PVC 的使用量指标。kube-prometheus-stack 已包含 node-exporter 选项。避免重复配置其主机挂载和权限。

原始块卷以及不支持统计信息的驱动可能不会发布文件系统容量。EFS access point/PVC 请求不是按目录配额；报告的容量可能描述的是共享文件系统。container_fs_usage_bytes 并非通用的 PVC 测量指标。请核实采集器、挂载以及命名空间/claim 映射，并单独处理缺失指标。

以下规则使用 max 而非求和来去重等效的抓取数据。联邦数据必须包含可靠的 cluster 标签。容量为零的序列会被排除。预测使用量规和近期趋势；采取行动前，请检查抓取缺口、claim 重建/扩容以及工作负载变化。对于只读/静态数据集或其他不应触发操作员告警的 claim，请调整选择器：

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: storage-alerts
  namespace: monitoring
  labels:
    release: prometheus
spec:
  groups:
  - name: storage-reviewed
    rules:
    - record: pvc:storage_used_bytes:max
      expr: max by (cluster, namespace, persistentvolumeclaim) (kubelet_volume_stats_used_bytes)
    - record: pvc:storage_capacity_bytes:max
      expr: max by (cluster, namespace, persistentvolumeclaim) (kubelet_volume_stats_capacity_bytes)
    - alert: VolumeUsageHigh
      expr: (pvc:storage_used_bytes:max / pvc:storage_capacity_bytes:max > 0.85) and
        (pvc:storage_capacity_bytes:max > 0)
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Volume usage high ({{ $value | humanizePercentage }})
        description: PVC {{ $labels.namespace }}/{{ $labels.persistentvolumeclaim
          }} requires capacity review.
    - alert: VolumeMayFillIn24Hours
      expr: (predict_linear(pvc:storage_used_bytes:max[6h], 86400) > pvc:storage_capacity_bytes:max)
        and (pvc:storage_capacity_bytes:max > 0) and (delta(pvc:storage_used_bytes:max[1h])
        > 0)
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Recent trend projects capacity exhaustion
        description: Review the trend and workload for PVC {{ $labels.namespace }}/{{
          $labels.persistentvolumeclaim }}; this is not a guarantee.
```

namespace/release 标签必须与 Prometheus 规则选择器匹配。请验证规则语法和模拟场景，然后在目标部署中确认实际指标覆盖情况和告警路由。本次审查未执行实时指标采集或告警传递。

## 存储故障排查

从对象身份和事件着手。Pending、ContainerCreating 和 I/O 缓慢可能有不同原因；拉取镜像、调度和应用就绪状态不一定是存储故障。该图是分诊指南，并未详尽列出各种症状及其原因。

![图示展示四种常见 EKS 存储问题（PVC Pending、配置失败、挂载问题、性能问题），分为两组并指向共享诊断检查和修复操作：配置问题检查 CSI driver 日志、IAM 权限和 StorageClass；挂载和性能问题检查节点状态。](../.gitbook/assets/en-eks-04-eks-storage-part3-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part3-1.html)

### 配置与 WaitForFirstConsumer

使用工作负载实际所在的命名空间、claim 和预期的使用者。检查所引用的类、控制器事件、驱动身份/KMS 权限、配额和节点附加限制，不要凭猜测授予宽泛权限：

```bash
set -euo pipefail
: "${NAMESPACE:?Set the workload namespace}"
: "${PVC_NAME:?Set the claim name}"
: "${POD_NAME:?Set its intended consumer Pod}"
kubectl -n "$NAMESPACE" get pvc "$PVC_NAME" -o yaml
kubectl -n "$NAMESPACE" describe pvc "$PVC_NAME"
kubectl -n "$NAMESPACE" describe pod "$POD_NAME"
kubectl get storageclass
kubectl get nodes -L topology.kubernetes.io/zone
```



```bash
set -euo pipefail
: "${CSI_CONTROLLER_POD:?Select the actual controller Pod}"
: "${CSI_CONTAINER:?Select the relevant driver/sidecar container}"
kubectl -n kube-system get pod "$CSI_CONTROLLER_POD" \
  -o jsonpath='{.spec.containers[*].name}'
kubectl -n kube-system logs "$CSI_CONTROLLER_POD" -c "$CSI_CONTAINER" --since=15m --tail=200
```

WaitForFirstConsumer 会有意让新 PVC 保持 Pending，直到可调度的使用者确定拓扑。新的未绑定 PVC 尚未有可用区，因此无需为了它而迁移节点池。检查 Pod 选择器、亲和性、污点、资源和存储拓扑。使用 spec.nodeName 会绕过调度器，并可能阻断此绑定流程；请使用受支持的调度约束。绑定后，EBS PV 的可用区/节点亲和性便会生效。不要仅为清除 Pending 而删除 claim 或编辑 PV 容量。

### 挂载故障

区分附加错误、节点发布/挂载错误、缺少文件系统客户端、身份/权限错误以及应用权限问题。读取日志时，应选择相关的 CSI driver/sidecar 容器；多容器 Pod 的默认日志并不包含所有组件。必要时检查 VolumeAttachment、已绑定 PV 的驱动/handle 以及分配的节点。

对于节点日志，请使用节点负责方支持的访问/诊断方式。通过 SSH 使用 ec2-user 和 journalctl 并不适用于所有 Bottlerocket、Auto Mode 或其他托管计算环境。特权 amazonlinux:2 辅助容器不能替代正确的 CSI/客户端配置；AL2 已于2026年结束 OS 支持。请复用本章中受支持的 CSI 使用者测试，并在考虑单独审批的节点级手动挂载前检查其事件。

对于 EFS，请检查挂载目标/DNS，并从实际挂载客户端测试 TCP2049。Lustre 需要 TCP988 和1018–1023，以及服务端的客户端/服务器规则；EFA 配置还有额外的 SG 引用要求。还需检查 NACL 返回流量和路由。ICMP ping 失败并不能证明 NFS 不可用，而且 AWS CLI 容器不一定包含 ping/telnet/mount 辅助工具。Pod 网络测试所用的源地址/安全组可能与节点发起的 CSI 挂载不同。

### I/O 缓慢

检查测量的操作大小、排队情况、应用并发、预置卷性能、实例 EBS 限制和初始化状态。以下可移植的 Python 时间计算使用闭合的五分钟区间；VolumeReadOps Sum/300 表示读取 IOPS，不同于直接将 Average 解释为速率：

```bash
set -euo pipefail
: "${AWS_REGION:?Set the volume Region}"
: "${EBS_VOLUME_ID:?Set the verified owned EBS volume ID}"
read -r START_TIME END_TIME < <(python3 - <<'PY'
import datetime, time
end = int(time.time()) // 300 * 300
fmt = lambda value: datetime.datetime.fromtimestamp(value, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
print(fmt(end - 3600), fmt(end))
PY
)
aws cloudwatch get-metric-statistics --region "$AWS_REGION" \
  --namespace AWS/EBS --metric-name VolumeReadOps \
  --dimensions "Name=VolumeId,Value=$EBS_VOLUME_ID" \
  --start-time "$START_TIME" --end-time "$END_TIME" \
  --period 300 --statistics Sum --output json > ebs-read-ops.json
python3 - ebs-read-ops.json <<'PY'
import json, sys
with open(sys.argv[1]) as stream:
    points = json.load(stream)["Datapoints"]
for point in sorted(points, key=lambda p: p["Timestamp"]):
    print(point["Timestamp"], "read IOPS:", point["Sum"] / 300)
if not points:
    print("No datapoints: check dimensions, attachment/activity, Region and publication delay")
PY
```

文件系统写入测试必须使用已核实挂载上的获批临时目录。请将此脚本保存在预期测试环境中；它会创建一个唯一的64MiB 文件，并且只清理它自己创建的文件/目录。读取操作可能命中缓存，因此这些计时结果无法证明冷存储性能。不要在实时数据上执行可预测路径 `/data/test` 的覆盖写入，或对原始设备写入零：

```bash
set -euo pipefail
: "${STORAGE_TEST_DIR:?Set an approved disposable directory on the verified disposable filesystem mount}"
test -d "$STORAGE_TEST_DIR" && test -w "$STORAGE_TEST_DIR"
STORAGE_TEST_PATH=$(mktemp -d "$STORAGE_TEST_DIR/storage-test.XXXXXX")
cleanup() { rm -f -- "$STORAGE_TEST_PATH/payload"; rmdir -- "$STORAGE_TEST_PATH"; }
trap cleanup EXIT
time dd if=/dev/zero of="$STORAGE_TEST_PATH/payload" bs=1M count=64 conv=fsync
time dd if="$STORAGE_TEST_PATH/payload" of=/dev/null bs=1M
```

本次审查未执行存储基准测试。应将碎片化视为需要证据支持的假设；重建/格式化文件系统属于数据迁移，不是常规的首选修复方法。不要更改猜测中的 nvme0n1 I/O 调度器：它可能是另一个卷/根设备，而且现代 blk-mq 调度器的名称/支持情况各不相同。

对于 EFS，需考虑 General Purpose、实际吞吐量模式、客户端限制、元数据需求和并发。使用 Part2 中受支持的挂载助手选项，包括 hard/TLS 和适当的超时/重试行为。对经过测量的工作负载，文件打包或增加顺序访问可能有帮助，但改变应用数据布局并非总是有益。

## 存储成本优化

在满足延迟、持久性、恢复和所有权要求的前提下，优化工作负载总成本。计算折扣、分配的存储、预置性能、请求/传输费用和保留的备份是不同的成本项。

<!-- Diagram repair pending: align each storage service with its actual optimization strategy; do not map S3 to FSx optimization or FSx to EFS optimization.
![Diagram showing four AWS storage types (EBS, EFS, FSx for Lustre, S3), each feeding its matching optimization strategy (volume optimization, lifecycle management, EFS optimization, FSx optimization), with all four strategies rolling up into a single cost-monitoring node built on Cost Explorer, Kubernetes cost allocation, and anomaly detection.](../.gitbook/assets/en-eks-04-eks-storage-part3-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part3-2.html)
-->

### 卷类型、大小与迁移

将 gp3 与实际的 gp2 成本/性能配置进行比较；仅在访问模式适合时考虑 HDD 类型。根据测量结果预留充足余量并设置告警，而不是任意设置最大容量。EBS/PVC 容量通常只能增加，不能缩小；要减少已分配容量，必须通过受支持的迁移流程将数据迁移到较小的新卷，并验证数据。

创建 gp3 StorageClass 或将其标记为默认类，**不会迁移现有 gp2 卷**。更改默认类还会影响其他无关的新 claim。请复用 Part1 中明确命名的类。对于现有卷，应选择已部署驱动支持的修改流程，或经过测试的备份/恢复迁移到新 claim；变更存储前请检查所有权、应用一致性和回滚方案。

### 生命周期与保留

VolumeSnapshotClass 定义驱动/保留行为；它既不会安排快照，也不会按期限删除快照。请使用备份负责人制定的计划和保留策略。Part2 介绍了 Velero 的 CSI 快照生命周期，包括原始类为 Retain 时的删除行为。

标记为 Available 或 Released 的 PV 并不代表可以自动处置，Bound 也不能证明它正在使用。清理前，请盘点 claimRef/UID、工作负载所有者、快照、保留义务以及实际后端资源。Retain 可能会留下仍需付费的资源；Delete 的行为取决于驱动。删除 EFS access point 不等于删除其文件系统/数据。将文件分层到 S3/Archive 还需要与应用兼容的恢复/访问计划。

### EFS 成本优化

AWS 建议对不可预测/突发型工作负载使用 Elastic 吞吐量。根据实际计量 I/O 和当前定价，将其与适用于已知持续需求的 Provisioned，以及基于容量/积分模型的 Bursting 进行比较。General Purpose 是推荐的性能模式。Access point 可以让不同 POSIX 身份共享一个文件系统；它们不会预留每个 PVC 的容量，也不会自动实现按应用计费。

提出变更前，请读取完整的现有生命周期配置：

```bash
set -euo pipefail
: "${AWS_REGION:?Set the filesystem Region}"
: "${EFS_FILE_SYSTEM_ID:?Set the owned filesystem ID}"
aws efs describe-file-systems --region "$AWS_REGION" --file-system-id "$EFS_FILE_SYSTEM_ID" \
  --output json > efs-filesystem-review.json
aws efs describe-lifecycle-configuration --region "$AWS_REGION" \
  --file-system-id "$EFS_FILE_SYSTEM_ID" --output json > efs-lifecycle-before.json
```

put-lifecycle-configuration 请求会更新文件系统配置；请在经过审查的数组中保留所有预期的现有转换。空数组会禁用生命周期管理。每个策略对象包含一个转换。Archive 要求使用受支持的 General Purpose/Elastic 配置，并且转换时间晚于 IA。成本分析应包含 IA/Archive 访问费和最低存储期限费用；不要不加判断地用单个30天示例覆盖现有策略。

### FSx for Lustre 与成本归属

仅对可重新创建的数据选择 scratch，并根据所需生命周期选择持久部署/存储选项。LZ4 可能会减少物理数据大小，但不会自动降低已经预置的 SSD 容量账单；应根据所选存储定价模型、压缩比以及吞吐量/CPU 影响进行评估。S3 存储库集成需要配置导入/导出/释放行为，而不仅仅是指定存储桶名称。

Cost Explorer 和 Kubernetes 成本分摊工具需要配置计费数据，在适用时激活成本分配标签，并测试从 PVC/PV 到云资源 ID 的映射。仅有命名空间标签并不会自动标记每一项 AWS 费用。跟踪保留的卷/快照、请求/传输费用和遥测数据保留。EC2 Reserved Instances/Compute Savings Plans 可以改变符合条件的计算成本；它们不会自动降低单独的 EBS/EFS/FSx 存储费用。

## 存储安全

分别保护后端、节点/挂载路径以及 Kubernetes 控制平面。类名称、命名空间策略或只读容器根文件系统本身都无法保护可写 PVC 的内容。

<!-- Diagram repair pending: TLS, at-rest key management, IAM, network rules, RBAC and admission are distinct controls; neither RBAC nor PSS proves backend encryption.
![Diagram showing EBS/FSx, EFS, and S3 storage security feeding data-at-rest and data-in-transit encryption that converge on AWS KMS key management, security groups and IAM roles leading through Kubernetes RBAC to OPA Gatekeeper/Kyverno policy enforcement, and the pod security context enforced by Pod Security Standards.](../.gitbook/assets/en-eks-04-eks-storage-part3-3.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part3-3.html)
-->

### 数据加密

预置卷时请求 EBS 加密；更改 StorageClass 不会追溯加密现有卷。以下新类示例请求加密的 gp3 存储，并设置延迟拓扑绑定和显式保留策略。如果需要客户管理的密钥，请添加真实且经过审查的 kmsKeyId，并准备好密钥策略/驱动授权；示例 ARN 不是可用密钥。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-encrypted
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: gp3
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
```

使用 Part1 中带有保护措施的基础设施工作流，在创建文件系统时配置 EFS 加密。对于现有未加密数据，需要迁移到加密文件系统，并使用受支持的迁移流程，而不是设置挂载选项。FSx for Lustre 会自动加密静态数据：scratch 文件系统使用服务管理的密钥；可选 AWS 托管/客户管理 KMS 密钥是**持久文件系统**的选项。不要在 SCRATCH_2 示例中传入客户 kms-key-id。

检查实际云资源，将 EBS ID 与已绑定 PV 的 volumeHandles 匹配，并确认账户/区域。没有选择客户密钥的 scratch FSx 响应并不能证明存储未加密：

```bash
set -euo pipefail
: "${AWS_REGION:?Set the resources Region}"
: "${EBS_VOLUME_ID:?Identify the actual volume from its bound PV}"
: "${EFS_FILE_SYSTEM_ID:?Set the owned EFS filesystem ID}"
: "${FSX_FILE_SYSTEM_ID:?Set the owned FSx filesystem ID}"
aws ec2 describe-volumes --region "$AWS_REGION" --volume-ids "$EBS_VOLUME_ID" \
  --query 'Volumes[0].{Id:VolumeId,Encrypted:Encrypted,KmsKeyId:KmsKeyId}' --output json
aws efs describe-file-systems --region "$AWS_REGION" --file-system-id "$EFS_FILE_SYSTEM_ID" \
  --query 'FileSystems[0].{Id:FileSystemId,Encrypted:Encrypted,KmsKeyId:KmsKeyId}' --output json
aws fsx describe-file-systems --region "$AWS_REGION" --file-system-ids "$FSX_FILE_SYSTEM_ID" \
  --query 'FileSystems[0].{Id:FileSystemId,Type:LustreConfiguration.DeploymentType,KmsKeyId:KmsKeyId}' --output json
```

对于传输中数据，请使用受支持的 EFS CSI/挂载助手 `tls` 选项，并验证实际挂载路径。FSx 传输加密取决于其受支持的文件系统/客户端/实例配置；请遵循相应服务指南。**S3 HTTPS/TLS 可保护传输；`aws s3 cp --sse AES256` 可选择静态数据加密 SSE-S3。**该标志不会启用 TLS。使用 HTTPS 端点并验证证书，同时审查要求安全传输的存储桶策略。KMS 密钥策略与传输证书管理是两回事。

### 访问控制

使用 Part1 中准备好的 CSI 身份：控制器受支持的 Pod Identity/IRSA 角色及精确的驱动权限，并在适用时配置 KMS 授权。不要通过无关的 eksctl 命令重新创建现有托管 add-on 的 ServiceAccount，也不要将控制器权限转移到每个节点/应用。Mountpoint 的 Pod 级身份、EFS IAM 挂载和文件系统 POSIX/access-point 身份具有不同的授权路径。

对于网络访问，请允许实际客户端/节点源安全组通过 TCP2049 访问 EFS 挂载目标。Lustre 需要客户端和文件服务器之间符合文档要求的 TCP988 和1018–1023 规则，包括所需的自引用/客户端流量。启用 EFA 的 Lustre 则需要指定的、通过安全组引用的全流量规则；面向整个互联网的 CIDR 不能替代这些规则。除安全组外，还应检查路由、DNS、NACL 以及实际的 CSI 挂载源。Kubernetes Pod NetworkPolicy 不会自动控制每个由节点发起的文件系统连接。

以下命名空间范围的 reader 可以检查 PVC 对象；它不能创建、扩容或删除 PVC。对集群范围的 PV 进行访问需要单独审查 ClusterRole。两个角色都不能直接控制文件字节。能够在命名空间中创建 Pod 的主体可能可以挂载该命名空间的 PVC，因此还必须控制 Pod 创建、工作负载身份、POSIX/access-point 权限和租户隔离：

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: storage-auditor
  namespace: storage-demo
automountServiceAccountToken: false
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pvc-reader
  namespace: storage-demo
rules:
- apiGroups:
  - ''
  resources:
  - persistentvolumeclaims
  verbs:
  - get
  - list
  - watch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: pvc-reader
  namespace: storage-demo
subjects:
- kind: ServiceAccount
  name: storage-auditor
  namespace: storage-demo
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: pvc-reader
```

### Pod 安全上下文

此完整示例将 Pod 级别的 runAsUser/runAsGroup/fsGroup/seccomp 与容器级别的 allowPrivilegeEscalation/capabilities/readOnlyRootFilesystem 分开配置。它使用预先准备的加密类和已声明的 PVC，而不是未定义的数据卷，也不使用未提供可写运行时路径的 nginx 镜像。命名空间策略版本与经过审查的 Kubernetes1.36 示例一致；请使用适用于集群的策略版本。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: secure-ns
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: secure-data
  namespace: secure-ns
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-encrypted
  resources:
    requests:
      storage: 10Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
  namespace: secure-ns
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: busybox:1.38.0
    command:
    - sh
    - -c
    args:
    - test -w /data && sleep 3600
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    resources:
      requests:
        cpu: 10m
        memory: 16Mi
      limits:
        cpu: 100m
        memory: 64Mi
    volumeMounts:
    - name: data
      mountPath: /data
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: secure-data
```

只读根文件系统不会让 `/data` 变成只读：此工作负载会特意检查 PVC 是否可写。fsGroup 的行为取决于 CSI/文件系统；EFS access point 可以强制使用不同的 POSIX 身份。SELinux/AppArmor 配置文件需要实际节点/运行时的支持以及已准备好的策略。不要随意照搬 MCS 标签或配置文件名称。Pod Security Standards 限制的是 Pod 配置；它们不会加密云卷，也不会授予 IAM 权限。具有主机访问权限的监控/CSI 节点代理需要单独审查其命名空间/安全设计。

### 安全策略执行

PVC 名称模式或仅有 StorageClass 允许列表，都无法证明 EBS 已加密。以下 **Kyverno ValidatingPolicy** 使用已提供服务的 `policies.kyverno.io/v1` API，已使用 Kyverno1.19.1 及其 CRD 进行检查。它要求已安装相应控制器/CRD，并且准入控制由适当的负责人管理。该版本中较旧的 ClusterPolicy 示例已弃用；请有计划地迁移，不要假定 API 兼容。

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: require-declared-ebs-encryption
spec:
  validationActions:
  - Deny
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
    - apiGroups:
      - storage.k8s.io
      apiVersions:
      - v1
      resources:
      - storageclasses
      operations:
      - CREATE
      - UPDATE
      scope: Cluster
  validations:
  - expression: '!(object.provisioner in [''ebs.csi.aws.com'', ''ebs.csi.eks.amazonaws.com''])
      || (has(object.parameters) && ''encrypted'' in object.parameters && object.parameters[''encrypted'']
      == ''true'')'
    message: EBS StorageClasses must explicitly request encryption.
```

此策略会检查 EBS StorageClass 创建/更新时**声明的加密参数**，包括 Auto Mode provisioner。它不会检查现有 AWS 卷、静态 PV、快照内容或不属于其匹配范围的绕过路径。除准入控制外，还应限制 StorageClass/PV 管理权限，并使用后端合规性检查。全面强制执行前，应针对代表性资源进行试运行，并监控策略报告/webhook 健康状况。现有数据的加密仍需单独迁移。

## 存储管理最佳实践

![图示将四个存储生命周期阶段（规划、实施、运维、优化）与对应的最佳实践领域（规划与设计、自动化与 IaC、备份与灾难恢复、性能与成本优化）配对，并按顺序列出每个领域的三项实践。](../.gitbook/assets/en-eks-04-eks-storage-part3-4.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part3-4.html)

### 规划与容量

分别记录延迟/IOPS/吞吐量、容量增长、读写模式、并发、可用性、持久性以及 RPO/RTO。根据这些要求选择块存储、共享 NFS、并行 Lustre 或对象访问。根据测量结果预留足够余量并制定有界扩容流程；自动扩缩器或 PVC 扩容并不提供应用复制能力，也不能随意缩减容量。

### 备份与灾难恢复

使用具备唯一备份身份和明确保留负责人的受支持计划。shell cron 行反复创建固定快照名称，会在第一个对象创建后失败；一次性的 Velero 备份 `daily-backup` 并不是计划任务。基于经过审查的 Velero/CSI 安装，以及 Part2 中的数据库一致性要求，以下命令会生成一个供审查的每日计划：

```bash
velero schedule create storage-daily --schedule="0 0 * * *" \
  --include-namespaces=storage-demo --ttl=720h0m0s -o yaml > storage-schedule-review.yaml
```

审查后由负责人部署，然后针对缺失/失败的备份设置告警，并测试隔离恢复。S3 中的备份可能引用原生快照，而不是包含卷的全部字节。跨可用区/区域恢复需要可访问的数据、密钥、驱动/存储映射以及应用验证。在受控切换成功前保留源数据；记录实测恢复时间，不要仅凭计划就声称达到某个 RPO/RTO。

### 基础设施即代码与 GitOps

使用 Part1/Part2 中带保护措施的文件系统创建示例，或使用经过审查的 provider/schema 版本、子网/挂载目标/安全组配置和删除保护机制的自有 Terraform/CloudFormation 模块。仅创建文件系统的 Terraform 资源并不等同于适用于 EKS 的挂载路径。将备份保留策略与 IaC destroy/prune 行为分开。

Helm values 是 chart 专用输入：除非模板将自定义 `storage.encrypted: true` 映射到实际受支持的资源字段，否则它不会起任何作用。部署前应渲染并验证生成的 StorageClass/PVC/工作负载。GitOps prune、chart 卸载和 claim 保留设置对数据可能产生不同影响；应记录每项资源由哪个系统负责，并在临时数据上测试生命周期变更。

例如，此文件系统资源请求加密和 Elastic 吞吐量，保留30天 IA 教学策略，并添加 Terraform destroy 保护。请将创建令牌替换为稳定且项目专用的值，配置 provider/账户/区域，并添加经过审查的网络/挂载目标资源。prevent_destroy 是 Terraform 操作保护措施，并非备份，也不能防止所有外部删除：

```hcl
resource "aws_efs_file_system" "example" {
  creation_token   = "example"
  performance_mode = "generalPurpose"
  throughput_mode  = "elastic"
  encrypted        = true

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Name = "ExampleFileSystem"
  }
}
```

### 持续审查

随着工作负载变化，定期审查瓶颈、配置限制、保留成本和安全控制。在确认资源所有权、备份/恢复以及删除影响之前，清理报告应保持只读。先设置告警并提出范围明确的变更，再将其自动化。本章示例是经过本地检查的参考配置；后端性能、准入部署和恢复仍需在目标环境中验证。

## 结论

本文档介绍了 Amazon EKS 存储的监控、故障排查、成本优化和安全。有效的存储管理对于确保 EKS 集群的性能、可靠性和成本效益至关重要。

存储要求因应用而异，因此了解工作负载的特征并选择合适的存储解决方案非常重要。此外，还应通过定期监控、故障排查、成本优化和安全审查，有效管理存储资源。

## 参考资料

- [Amazon EKS 存储最佳实践](https://docs.aws.amazon.com/eks/latest/best-practices/storage.html)
- [Kubernetes 存储故障排查](https://kubernetes.io/docs/tasks/debug-application-cluster/debug-application/#debugging-pods)
- [Kubernetes 存储安全](https://kubernetes.io/docs/concepts/security/)

- [EBS CloudWatch 指标](https://docs.aws.amazon.com/ebs/latest/userguide/using_cloudwatch_ebs.html)
- [FSx Lustre 指标维度](https://docs.aws.amazon.com/fsx/latest/LustreGuide/fs-metrics.html)
- [EFS 性能模式](https://docs.aws.amazon.com/efs/latest/ug/performance.html)
- [EFS 生命周期 API](https://docs.aws.amazon.com/efs/latest/APIReference/API_PutLifecycleConfiguration.html)
- [FSx 静态数据加密](https://docs.aws.amazon.com/fsx/latest/LustreGuide/encryption-at-rest.html)
- [FSx 网络访问](https://docs.aws.amazon.com/fsx/latest/LustreGuide/limit-access-security-groups.html)
- [S3 静态数据加密](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingServerSideEncryption.html)
- [Kyverno CEL 迁移](https://kyverno.io/docs/guides/migration-to-cel/)

## 测验

为了检验你在本章中的学习成果，请尝试[主题测验](../quizzes/eks/04-eks-storage-part3-quiz.md)。
