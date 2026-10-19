# EKS 存储第 3 部分测验

> **最后更新**：2026 年 9 月 11 日

请结合本章配置的采集器和存储示例，复习监控、诊断、成本与安全。以下示例经过本地检查；它们不表示已执行 AWS 操作、已完成生产环境恢复或已验证实时仪表板。部署前请替换占位值并确认资源所有权。

## 选择题

### 1. 如何根据 VolumeReadOps 计算读取 IOPS？

- A. 直接将 Average 作为 IOPS
- B. 将 Sum 除以统计周期的秒数
- C. 将字节数乘以 Pod 数量
- D. 将 VolumeQueueLength 作为已完成的 IOPS

<details>
<summary>显示答案</summary>

**答案：B**

用 Sum 除以统计周期的秒数。VolumeReadBytes/VolumeWriteBytes 也需要同样换算，才能得到字节/秒。VolumeTotalReadTime/VolumeTotalWriteTime 是累计操作秒数：将 Sum 除以相应操作次数的 Sum，计算平均每次操作的秒数；还要处理操作次数为零的情况。不要把所有原始计数器都称作速率或延迟。

当前 Nitro 指标还包括 VolumeAvgIOPS、VolumeAvgThroughput 和具有特定单位/限制的平均延迟指标。BurstBalance 适用于 gp2/st1/sc1，不适用于 gp3。EFS 字节数/计量字节指标和 FSx 按 OSS/OST 划分的指标具有不同的维度和统计方式。在受支持的情况下，kubelet_volume_stats_* 可提供文件系统用量；container_fs_usage_bytes 并非通用 PVC 用量指标。

</details>

### 2. Pending 的 PVC/消费者应先检查什么？

- A. 立即删除 PVC
- B. 向每个节点授予完整 EC2 权限
- C. 检查事件、绑定模式和调度约束
- D. 假定未绑定的 PVC 已确定了可用区

<details>
<summary>显示答案</summary>

**答案：C**

检查实际的命名空间、PVC、消费者事件、StorageClass 和拓扑。WaitForFirstConsumer 可以有意让新 PVC 保持 Pending，直到开始调度；这不一定表示驱动程序故障。绑定后，还要考虑 EBS PV 的节点亲和性/可用区以及卷挂载限制。避免使用会绕过调度器的 spec.nodeName，因为绑定流程需要调度器参与。

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

检查驱动程序实际使用的 Pod Identity/IRSA 角色和 KMS 授权，而不只是 EC2 节点实例配置文件。多容器 controller 需要选择相关的驱动程序/sidecar 日志。ContainerCreating 也可能由挂载、客户端软件、镜像拉取或应用权限引起。不要通过删除数据来重置症状。

</details>

### 3. 数据库存储调优应采用哪种方法？

- A. 测量并匹配卷、文件系统和实例的约束
- B. 始终启用 multiAttach:true
- C. 假定任意 hostPath 都是高速 NVMe
- D. 不识别设备就更改根磁盘调度器

<details>
<summary>显示答案</summary>

**答案：A**

测量 I/O 模式、队列、延迟和实例限制，然后选择存储及性能设置。这个 10,000 IOPS 的 io2 StorageClass 只是示例分配，并不能证明它满足数据库 SLO：

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: io2
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
  iops: '10000'
```

Multi-Attach 并不是通用的只读性能开关。本章审阅过的 EBS CSI 路径使用 io2、RWX 和原始块设备，并要求应用协调写入，详见第 2 部分。hostPath 名称为 /mnt/instance-store 并不能证明后端是物理实例存储；应采用准备妥当的节点本地存储设计，并将数据视为临时数据。EC2 实例存储 CSI 是受支持的真实集成，但有自己的先决条件。

不要将 noop 写入猜测的 nvme0n1 调度器：该设备可能是根磁盘或其他磁盘，现代 blk-mq 的名称也有所不同。应先识别设备和受支持的调度器，再单独审查变更。文件系统选择和挂载选项也需要工作负载证据；XFS 或 ext4 都不能保证性能结果。

</details>

### 4. 创建默认 gp3 StorageClass 会迁移现有 gp2 卷吗？

- A. 会，所有已挂载卷都会立即更改
- B. 会，但要先重命名 StorageClass
- C. 会，默认 StorageClass 会加密/迁移旧数据
- D. 不会；现有卷需要单独采用受支持的流程

<details>
<summary>显示答案</summary>

**答案：D**

不会。StorageClass 控制适用的卷创建流程，不会重写所有已绑定的 PV/后端。更改默认 StorageClass 可能会影响无关的新 PVC。应选择有所有权且受支持的修改或数据迁移流程，保留恢复点并验证应用数据。扩容和缩容是不同的操作；通常不能直接缩小 PVC/EBS 卷容量。

请比较已分配容量、预置 IOPS/吞吐量、保留策略、请求量和传输成本。计算折扣不会自动降低单独计费的存储费用。VolumeSnapshotClass 本身不是计划任务；以下示例仅为有意创建的临时快照定义删除行为：

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: temporary-ebs-snapshots
driver: ebs.csi.aws.com
deletionPolicy: Delete
```

不要把本章保留快照使用的 StorageClass 全面替换为这个临时类来优化成本。备份负责人必须安排快照并管理保留策略；Velero 有自己的 CSI 快照生命周期。

</details>

### 5. 哪项陈述正确区分了存储安全控制？

- A. PVC 名称可保证加密
- B. 每种控制都需要正确的作用范围，并映射到实际资源
- C. Role 可以授予所有集群级 PV 权限
- D. PSS 可以取代 IAM 和 KMS

<details>
<summary>显示答案</summary>

**答案：B**

IAM/KMS、网络访问、Kubernetes API 授权、准入控制和文件系统身份分别保护不同的操作。仅按区域限制 EC2 操作列表，并不自动构成完整的最小权限 CSI 策略。应使用驱动程序实际角色策略以及所需的密钥授权。虚构的 kmsKeyId 不会创建 KMS 密钥。

命名空间级 Role 可以授权访问 PVC，但不能授予集群级 PV 权限。Pod 创建者即使不能通过这个特定 Role 读取 PVC 对象，也可能挂载该命名空间的 PVC；还要保护工作负载创建权限和租户边界。本章的命名空间读取者是检查对象的示例：

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

EFS 安全组适用于真实的挂载目标/客户端，而不是虚构的 securityGroupSelector 片段。应使用实际 TCP 2049 路径；Lustre/EFA 规则不同。Pod Security Standards 不能提供云端加密或 IAM 权限。

</details>

### 6. 哪项关于监控集成的陈述正确？

- A. Grafana ConfigMap 会自动采集 PVC 指标
- B. Prometheus 会永久保留数据
- C. 必须配置采集器、服务发现、授权和存储
- D. CloudWatch 永远不能接收自定义指标

<details>
<summary>显示答案</summary>

**答案：C**

CloudWatch 可提供原生服务指标；Prometheus 可采集已配置的 Kubernetes/应用目标；Grafana 可展示已配置的数据源。仍需配置采集器、服务发现、IAM/身份验证、保留期、标签和告警路由。单独的仪表板 ConfigMap 不会自动创建缺失的指标。

通过已配置的 agent 或集成，CloudWatch 可以接收自定义/Kubernetes 指标；Prometheus 也不会自动成为长期持久存储。请根据工作负载选择合适的数据保留和存储/远程写入架构。自动化管理应从观测和有边界的变更提案开始，而不是无条件修改。

</details>

### 7. 哪项观察本身足以授权删除卷？

- A. PV 状态为 Available
- B. 当前列出的 Pod 中没有使用该 PVC
- C. lastUsed 注解日期较早
- D. 以上都不足以单独授权删除

<details>
<summary>显示答案</summary>

**答案：D**

保留的数据、缩容到零的控制器、未来的 Job、备份义务和外部所有者都可能影响决策。lastUsed 不是标准且可信的 PVC 用量字段。清理前请保留命名空间/UID，并核实后端资源身份。

</details>

### 8. kubectl top pods 能测量 PVC 磁盘用量吗？

- A. 不能；它主要报告 CPU/内存
- B. 能；内存用量等于磁盘用量
- C. 能；它会列出所有 EBS 空闲块
- D. 只有 StorageClass 名称为 gp3 时才可以

<details>
<summary>显示答案</summary>

**答案：A**

请使用受支持的文件系统统计信息，从正确的挂载路径/驱动程序读取，并确认对应的 PVC。容器中的 df 可能显示的是其他挂载或共享 EFS 文件系统；EFS PVC 请求量也不是目录配额。

</details>

### 9. 如何配置 EFS IA/Archive 生命周期？

- A. 在访问点 StorageClass 上随意设置 performanceMode 参数
- B. 通过文件系统生命周期配置，并保留预期的转换顺序
- C. 减小 PVC 请求容量
- D. 将 Pod 标签改成 IA

<details>
<summary>显示答案</summary>

**答案：B**

EFS CSI 访问点参数不能配置文件系统的所有吞吐量或生命周期属性。更新配置数组前应先读取现有策略；空数组会禁用生命周期管理。对于需求不可预测的工作负载，Elastic 是推荐的起点；Archive 的可用性和转换顺序则有特定要求。

</details>

### 10. aws s3 cp --sse AES256 选择什么？

- A. TLS 协议版本
- B. NetworkPolicy 加密
- C. SSE-S3 静态加密
- D. EFS 挂载加密

<details>
<summary>显示答案</summary>

**答案：C**

HTTPS/TLS 保护传输过程；--sse 不会启用 TLS。请使用正确的端点并验证证书。FSx scratch 数据使用服务管理的密钥加密；可选择客户密钥的则是持久性文件系统。

</details>

## 简答题

### 11. 如何验证速率计算和容量预测？

<details>
<summary>显示答案</summary>

**答案：核对单位、统计周期、缺失数据和代表性场景**

在 300 秒的统计周期内，30,000 次已完成读取操作相当于 100 IOPS。1,500 累计读取秒除以 30,000 次操作，等于每次操作 0.05 秒，即 50 毫秒。并发操作可能使累计操作时间超过墙钟时间。请对齐统计周期，并分别处理零样本和无样本情况。

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

这些是算术示例，不是实测工作负载结果。对 gauge 使用 predict_linear 预测，而不是对 counter；去除重复抓取的时间序列并排除无效容量。近期趋势不能保证未来何时耗尽。源规则使用合成数据，针对持续高用量、重复目标、零容量、缺失时间序列和用量增加进行了测试。

</details>

### 12. CSI 身份、Multi-Attach 和节点本地存储分别解决什么问题？

<details>
<summary>显示答案</summary>

**答案：它们分别解决授权、卷挂载和数据放置问题**

CSI controller 身份用于授权后端生命周期 API；它并不是每个应用的身份。EBS Multi-Attach 会在服务/驱动程序/可用区限制下提供共享原始设备挂载，并要求应用协调写入/进行 fencing。随意增加 multiAttach StorageClass 字段并不是受支持的开关。

节点本地实例存储在物理上依赖节点生命周期，并要求正确配置设备和调度。hostPath 字符串不能证明其后端设备或持久性。请复用本章审阅过的 CSI 路径，不要为了运行性能示例而授予额外权限或格式化猜测的磁盘。

</details>

### 13. 准入控制和 EKS 审计日志能证明什么？

<details>
<summary>显示答案</summary>

**答案：只能证明其已配置的请求范围和记录到的事件**

本章的 Kyverno policies.kyverno.io/v1 ValidatingPolicy 会检查匹配的 EBS StorageClass 是否声明了加密参数。它不会检查现有 AWS 卷、静态 PV 内容或所有绕过路径。除准入策略外，还应限制管理权限并核实后端实际加密情况。

EKS 管理控制平面的审计策略；应由集群所有者启用受支持的审计日志类型，并检查已交付的记录。粘贴的 audit.k8s.io 策略片段并不是可替换托管策略的 EKS API。Kubernetes 审计事件和 CloudTrail 后端 API 事件可以互补，但各自有独立的保留期、访问控制和覆盖范围。审计日志本身不能防止数据丢失。

</details>

## 实操题

### 14. 创建可供审阅的监控/仪表板配置。

<details>
<summary>显示答案</summary>

**答案：明确配置每项依赖**

使用本章审阅过的监控堆栈和采集器；不要假定 ConfigMap 会单独安装 agent。对于传统的 CloudWatch agent 安装，请检查实际命名空间/工作负载及其身份。根据所选集成方式调整这些名称，并确认计算平台支持：

```bash
set -euo pipefail
kubectl -n amazon-cloudwatch get daemonsets,pods
kubectl -n amazon-cloudwatch get serviceaccount cloudwatch-agent -o yaml
```

[集群监控示例](../../eks/02-eks-cluster-creation-part3.md)介绍了自有 agent/add-on 的先决条件。StatsD 接收器不会自动生成 EBS/PVC 指标。不要为了填补仪表板缺口而添加静态 AWS 密钥或启用重复 agent。

对于 EBS CSI，应通过现有资源所有者启用受支持的指标配置。当现有 Service 存在时，可使用本章生成的监控对象**或**下面的独立监控对象；不要重复抓取。Prometheus 必须选择监控对象所在的命名空间/标签，并能访问其命名的 Service 端口：

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

通过监控系统的资源所有者安装本章的 recording/alert 规则，然后验证目标 Up 状态、预期时间序列和告警投递。EBS 驱动程序端点报告 CSI 操作指标，并不包含每个 sidecar 指标或原始文件系统用量。

这个 ConfigMap 包含适用于支持该导入/配置路径的部署的 **Classic 仪表板模型**。当前 Grafana 还支持 V1 Resource 和默认的 V2 Resource 模型；不要将这个原始 Classic 对象发给需要资源封装对象的其他 API。替换 Prometheus 数据源 UID，确保源端 recording 规则存在，并匹配 Grafana sidecar 的标签/命名空间配置。采用前应针对目标 Grafana 版本导出/导入验证：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: storage-dashboard-reviewed
  namespace: monitoring
  labels:
    grafana_dashboard: '1'
data:
  storage-dashboard.json: |
    {
      "id": null,
      "uid": "eks-storage-reviewed",
      "title": "EKS Storage: PVC Filesystem Usage",
      "tags": [
        "storage"
      ],
      "timezone": "browser",
      "schemaVersion": 42,
      "version": 1,
      "refresh": "30s",
      "time": {
        "from": "now-6h",
        "to": "now"
      },
      "panels": [
        {
          "id": 1,
          "type": "timeseries",
          "title": "PVC filesystem utilization",
          "gridPos": {
            "x": 0,
            "y": 0,
            "w": 24,
            "h": 8
          },
          "datasource": {
            "type": "prometheus",
            "uid": "REPLACE_WITH_PROMETHEUS_DATASOURCE_UID"
          },
          "targets": [
            {
              "refId": "A",
              "expr": "(pvc:storage_used_bytes:max / pvc:storage_capacity_bytes:max) and (pvc:storage_capacity_bytes:max > 0)",
              "legendFormat": "{{cluster}} {{namespace}}/{{persistentvolumeclaim}}"
            }
          ],
          "fieldConfig": {
            "defaults": {
              "unit": "percentunit",
              "min": 0,
              "max": 1
            },
            "overrides": []
          }
        }
      ]
    }
```

如需增加原生 EBS IOPS/EFS 吞吐量面板，应在审核 IAM 访问后配置 CloudWatch 数据源，并使用指标源对应的维度和按周期归一化的计算。除非已配置的 exporter 确实发布了相应名称和语义，否则不要虚构 aws_ebs_* Prometheus 时间序列。这里的 JSON 和表达式仅经过本地检查；未通过已认证的 Grafana 导入或实时 AWS 查询验证。

</details>

### 15. 在不作出不安全清理假设的前提下生成存储清单。

<details>
<summary>显示答案</summary>

**答案：报告证据，不要推断资源是否有资格删除**

请将旧占位 CronJob 替换为只读报告。以下脚本保留命名空间和 UID，列出 Pod 的直接引用，并明确拒绝授权删除。它不会根据 lastUsed 推断资源使用时间，不会把 Bound 视为未使用，也不会在全命名空间查询中丢弃命名空间信息。

```python
"""Report direct Pod/PVC references; never infer deletion eligibility."""
import json,sys
def inventory(namespace,claims,pods):
    refs={}
    for pod in pods['items']:
        meta=pod['metadata']
        if meta['namespace']!=namespace:raise ValueError('Pod list contains another namespace')
        seen=set()
        for volume in pod.get('spec',{}).get('volumes',[]):
            claim=volume.get('persistentVolumeClaim',{}).get('claimName')
            if claim and claim not in seen:
                seen.add(claim)
                refs.setdefault(claim,[]).append({'pod':meta['name'],'podUID':meta['uid'],'phase':pod.get('status',{}).get('phase','Unknown')})
    rows=[]
    for pvc in claims['items']:
        meta,spec=pvc['metadata'],pvc.get('spec',{})
        if meta['namespace']!=namespace:raise ValueError('PVC list contains another namespace')
        rows.append({'namespace':namespace,'name':meta['name'],'uid':meta['uid'],
          'phase':pvc.get('status',{}).get('phase','Unknown'),'volumeName':spec.get('volumeName'),
          'storageClassName':spec.get('storageClassName'),'requestedStorage':spec.get('resources',{}).get('requests',{}).get('storage'),
          'directPodReferences':refs.get(meta['name'],[]),'ownerReferences':meta.get('ownerReferences',[]),
          'deletionAuthorized':False,'nextAction':'Review owner, controller templates, retention, backups and actual backend before any change'})
    return {'reviewOnly':True,'namespace':namespace,'rows':sorted(rows,key=lambda x:x['name']),
      'limitations':['The two API reads are not an atomic snapshot.','No Pod reference does not mean unused: scale-to-zero controllers, future Jobs, retained data and indirect/ephemeral references need separate review.','lastUsed is not a standard trustworthy Kubernetes PVC field. This report never authorizes snapshot creation or deletion.']}
if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('Usage: storage-inventory.py namespace pvcs.json pods.json')
    with open(sys.argv[2]) as f:claims=json.load(f)
    with open(sys.argv[3]) as f:pods=json.load(f)
    print(json.dumps(inventory(sys.argv[1],claims,pods),indent=2))
```



```bash
set -euo pipefail
: "${STORAGE_NAMESPACE:?Set the namespace being reviewed}"
kubectl -n "$STORAGE_NAMESPACE" get pvc -o json > inventory-pvcs.json
kubectl -n "$STORAGE_NAMESPACE" get pods -o json > inventory-pods.json
python3 storage-inventory.py "$STORAGE_NAMESPACE" inventory-pvcs.json inventory-pods.json
```

查询身份只需要此命名空间的读取权限。这个 Role 仅用于说明权限范围；如有需要，应将其绑定到经过审阅的 operator/automation 身份。它不授予创建快照、调整大小或删除资源的权限：

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: storage-inventory-reader
  namespace: storage-demo
rules:
- apiGroups:
  - ''
  resources:
  - pods
  - persistentvolumeclaims
  verbs:
  - get
  - list
```

请分别审查缩容到零的控制器模板、Job/CronJob、保留的 PVC、间接/临时引用、备份策略和实际后端 ID。当前没有 Pod 引用并不代表可以删除。如果以后要定时运行该报告，应使用包含脚本/客户端的真实且经过审阅的镜像，限制执行范围和时长，使用受限凭证，并指定报告目的地；storage-tools:latest 和省略号命令都不是可用实现。

先自动化观测，再提出有边界的变更，并独立验证恢复能力。EBS/PVC 扩容并不等于可以任意缩容。应依据部署需求保留审计证据、生命周期所有权和明确的审批/运维控制，不要使用会静默销毁资源的脚本。

</details>

## 检查答案

本测验共 15 题，其中包括 10 道选择题。请利用错题确定需要复习的主题；测验分数本身不能证明具备生产环境专业能力。对于实操题，除语法外，还应评估假设、资源范围和验证证据。

## 参考资料

- [源章节](../../eks/04-eks-storage-part3.md)
- [EBS 指标](https://docs.aws.amazon.com/ebs/latest/userguide/using_cloudwatch_ebs.html)
- [FSx 指标](https://docs.aws.amazon.com/fsx/latest/LustreGuide/fs-metrics.html)
- [EFS 生命周期 API](https://docs.aws.amazon.com/efs/latest/APIReference/API_PutLifecycleConfiguration.html)
- [EKS 审计](https://docs.aws.amazon.com/eks/latest/best-practices/auditing-and-logging.html)
- [Grafana 仪表板模型](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/view-dashboard-json-model/)
