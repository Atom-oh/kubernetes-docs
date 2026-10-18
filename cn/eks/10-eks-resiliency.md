# EKS 韧性与高可用性

> **示例 API 基线**：Kubernetes 1.36；请选择当前受支持的 EKS 版本和兼容的控制器版本
> **最后更新**：2026 年 9 月 12 日

以下是配置模式，并非经过测试的生产平台。请在自己负责的测试范围内操作，并将应用镜像、健康检查路径、IAM 和基础设施引用替换为经过审查的输入。本次审查没有执行集群、故障转移或混沌实验。

RTO 是可接受的恢复时间目标，包括故障检测和恢复；RPO 是可接受的恢复点/数据丢失时间窗口。多可用区、复制和控制平面 SLA 不会自动保证零数据丢失或特定的工作负载恢复时间。

## 韧性概述

韧性是指**在故障期间尽量降低影响，并在故障后恢复正常状态或维持服务的能力**。它超越了简单的高可用性（HA），是一种预先考虑并为故障做好准备的设计理念。

### 韧性成熟度模型

| 级别 | 范围 | 示例控制措施 | 早期示意性恢复时间，并非测量结果 |
| --- | --- | --- | --- |
| 1. 基础 | Pod/工作负载 | 探针、资源、驱逐预算、关闭流程 | 数秒至数分钟 |
| 2. 多可用区 | 可用区故障 | 放置、存活容量、流量/数据恢复 | 数秒至数分钟 |
| 3. Cell | 服务分区 | 路由以及受限的依赖和容量 | 部分影响时为数秒，或数分钟 |
| 4. 多区域 | 区域故障 | 区域流量/数据故障转移和运维 | 取决于设计，从接近零到数分钟/数小时 |

早期其他语言版本使用了不同的示意性时间范围。此模型用于组织设计选择，不是认证，也不保证级别越高恢复越快。请针对每条用户旅程及其依赖定义并测量目标。

区域级 EKS 会在三个可用区中管理其控制平面。当前端点 SLA 为：标准控制平面每月可用率 99.95%（按五分钟间隔测量），预置控制平面为 99.99%（按一分钟间隔测量）。这些是附带条件的服务抵扣承诺，并非应用 SLO/RTO/RPO 保证。[AWS EKS SLA](https://aws.amazon.com/eks/sla/)

> 并非所有服务都需要第 4 级。请根据 SLA 要求、法规和预算选择合适级别。

***

## 第 1 级：基础韧性（Pod 级）

### 存活、就绪和启动探针

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: resilience-demo
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: app
        image: registry.example.com/team/web-app:replace-with-reviewed-digest
        ports:
        - name: http
          containerPort: 8080
        startupProbe:
          httpGet:
            path: /healthz
            port: http
          failureThreshold: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        lifecycle:
          preStop:
            sleep:
              seconds: 5
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

上图中的镜像是明确标记的应用占位内容，并非已发布产物。部署前请将其替换为经过验证的摘要，并实现相应健康检查契约。启动探针会控制何时开始存活/就绪探针；下游服务变慢本身不应导致存活探针失败。资源和探针数值仅为示例。Job 和 init 容器不一定都需要相同的探针。

### Pod 中断预算（PDB）

对于匹配的 Pod，PDB 会约束受支持的自愿驱逐。它无法在可用区/硬件故障、直接删除 Pod 或 Deployment 自身滚动更新/缩容时保持 Pod 数量。控制器策略、放置和备用容量是另外的控制措施。

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
  namespace: resilience-demo
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: web-app
```

```bash
# Check PDB status
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pdb web-app-pdb
# Inspect the actual workload health and ongoing disruptions.
# Illustrative only: three Ready replicas and no ongoing/unhealthy deductions permit one eviction.
```

### 优雅关闭

```yaml
spec:
  terminationGracePeriodSeconds: 60
  containers:
  - name: app
    lifecycle:
      preStop:
        sleep:
          seconds: 5
```

这是供所属应用使用的 Pod 规格片段。原生 preStop sleep 从 Kubernetes 1.34 起为 GA，在基线版本 1.36 中有效。等待五秒只是延迟，并不能保证端点/负载均衡器状态已传播。终止宽限期包括钩子执行时间；EndpointSlice 的终止状态更新与节点关闭并发发生。终止中的端点可能仍列在列表中，同时 ready=false 并带有 serving 条件，以便排空流量。

随后，运行时会发送配置的停止信号（通常为 SIGTERM；镜像/运行时设置可能不同）。应用必须处理该信号，并在强制终止前完成或拒绝工作。不要在 preStop 中手动终止 PID 1，并假设端点会按严格顺序移除。请实际测试长连接、注销和缓冲数据刷写。

***

## 第 2 级：多可用区策略

### Pod 拓扑分布约束

拓扑分布会影响调度放置，但不会创造健康容量，也不会在故障后自动迁移已有 Pod。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 6
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      topologySpreadConstraints:
      # Hard constraint for the documented N-1 example; review eligible domains and capacity.
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-app
        minDomains: 2
      # Soft constraint: Even distribution across nodes
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: web-app
      containers:
      - name: app
        image: web-app:1.0
```

| 参数 | 说明 |
| --- | --- |
| `maxSkew` | 使用 DoNotSchedule 时，候选域中的 Pod 数与全局最小值之间的差 |
| `topologyKey` | 分布依据（例如 zone、hostname） |
| `whenUnsatisfiable` | `DoNotSchedule`（硬约束）或 `ScheduleAnyway`（软约束） |
| `minDomains` | 剩余符合条件的域更少时，全局最小值设为零 |

例如，若仅剩两个符合条件的可用区，且每区各有两个匹配的 Pod，minDomains=3 会使全局最小值为零；当 maxSkew=1 时，这可能阻止替代 Pod 调度。minDomains=2 则允许在其他约束和容量允许时，为另一个 Pod 进行分布计算。它不会要求恰好占用两个或三个可用区。请分别为初始的三可用区放置和故障后存活区的余量设置门禁。ScheduleAnyway 只是偏好；其他调度器约束仍然适用。

### Karpenter 多可用区 NodePool

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
      - key: topology.kubernetes.io/zone
        operator: In
        values: ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["on-demand", "spot"]
      - key: node.kubernetes.io/instance-type
        operator: In
        values: ["m6i.xlarge", "m6i.2xlarge", "m7i.xlarge", "m7i.2xlarge"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: "20%"    # Applicable voluntary budget, rounded up and reduced by deleting/NotReady nodes
    - nodes: "0"
      schedule: "0 0 * * MON-FRI"   # UTC 00:00–09:00 = Korea/Japan 09:00–18:00; not all failure types
      duration: 9h
```

Karpenter 的 requirements 允许在指定可用区调度；它们不会均匀预置节点，也不会预留故障余量。请使用与 EKS 兼容的版本；当前维护的 1.14.1 版本是此处的架构基线，而不是无条件沿用历史上的 1.0+ 下限。被引用的 EC2NodeClass、AMI、角色、子网和容量都必须预先审查。

百分比预算使用 ceil（总数 × 百分比），并扣除正在删除和 NotReady 的节点；适用预算中最严格者生效。它们不会对每次中断、过期、修复或手动删除都限速。计划按 UTC 执行；示例表示韩国/日本时间工作日 09:00–18:00 的一个时段。零预算并不能阻止所有故障。

Spot/On-Demand 分离的节点池可以分别设权重 100/50，但权重只是供应偏好，并不保证只有 Spot 不可用时才使用低权重池。现有容量、约束和批处理也会影响选择。NodePool limits 限制的是节点供应上限，而非预先扩容。

### 同可用区 Service 优先

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-app
  namespace: resilience-demo
spec:
  selector:
    app: web-app
  ports:
  - name: http
    port: 80
    targetPort: http
  trafficDistribution: PreferSameZone
```

PreferSameZone/PreferSameNode 从 Kubernetes 1.35 起为 GA，适用于此处的 1.36 基线；PreferClose 是 PreferSameZone 的旧别名。这是偏好，并非严格的本地性保证，也不保证延迟或成本。请检查实际代理/EndpointSlice 行为以及 Local 流量策略。较旧的 topology-mode=Auto 注解使用另一种提示分配启发式；topology-aware-hints 已属于旧版指引。

来源：[PDB](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)、[Pod 终止](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)、[拓扑分布](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)、[Service 流量分布](https://kubernetes.io/docs/concepts/services-networking/service/#traffic-distribution)、[Karpenter 中断处理](https://karpenter.sh/docs/concepts/disruption/)。

### ARC 可用区转移

手动可用区转移和自动可用区转移是不同操作。EKS 集成会封锁受影响可用区中的节点，并从 EndpointSlice 移除其端点；它不会驱逐 Pod，也不会终止这些节点。Auto Mode 会避免在受影响可用区创建新节点，并暂停相关的自愿中断；托管节点组会暂停可用区再均衡，并避免在那里启动新节点。当前 Karpenter 集成需要按文档配置相应版本、设置和 IAM。负载均衡器流量转移是另一个资源操作。

首先验证账户、准确的托管资源、已启用的集成、现有 practice configuration 和告警行为。测试存活可用区中的应用、DNS、数据和节点容量。可用区转移不是绝对的网络隔离：如果所有 Service 端点都在受损可用区，EKS 会采用故障保护行为。它无法迁移现有的可用区绑定 EBS 卷。纯 Auto Mode 使用节点系统 CoreDNS；混合或非 Auto 节点仍需要 CoreDNS Deployment 及其容量。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the resource region}"
: "${ARC_RESOURCE_ARN:?Set the exact owned EKS cluster or eligible load-balancer ARN}"
aws sts get-caller-identity
aws arc-zonal-shift get-managed-resource \
  --region "$AWS_REGION" --resource-identifier "$ARC_RESOURCE_ARN"
```

以下代码块是彼此独立的运维步骤，不是一个一体化设置脚本。Practice configuration 会启动周期性流量变更；请检查已有配置，而不是重新创建。结果告警标识符是 ARN 字符串，而不是包含 alarmName/region 的对象。准备就绪后，需另行启用 autoshift。

```bash
# MUTATION: authorizes recurring weekly traffic-shifting practice runs.
: "${OUTCOME_ALARM_ARN:?Set the reviewed CloudWatch alarm ARN in the resource region}"
aws arc-zonal-shift create-practice-run-configuration \
  --region "$AWS_REGION" --resource-identifier "$ARC_RESOURCE_ARN" \
  --outcome-alarms "alarmIdentifier=$OUTCOME_ALARM_ARN,type=CLOUDWATCH"
```
```bash
# MUTATION: enable automatic shifts only after the readiness review.
aws arc-zonal-shift update-zonal-autoshift-configuration \
  --region "$AWS_REGION" --resource-identifier "$ARC_RESOURCE_ARN" \
  --zonal-autoshift-status ENABLED
```
```bash
# MUTATION: a separate, manually initiated one-hour shift.
set -euo pipefail
: "${AWAY_FROM_AZ:?Set an AZ of this resource}"
SHIFT_ID=$(aws arc-zonal-shift start-zonal-shift \
  --region "$AWS_REGION" --resource-identifier "$ARC_RESOURCE_ARN" \
  --away-from "$AWAY_FROM_AZ" --expires-in 1h \
  --comment "Owned resilience exercise" --query zonalShiftId --output text)
test -n "$SHIFT_ID" && test "$SHIFT_ID" != None
printf '%s\n' "$SHIFT_ID" > owned-zonal-shift-id.txt
```
```bash
# MUTATION: cancel only the recorded manual shift after checking its ownership.
: "${SHIFT_ID:?Use the exact ID recorded for this exercise}"
aws arc-zonal-shift cancel-zonal-shift \
  --region "$AWS_REGION" --zonal-shift-id "$SHIFT_ID"
```

[EKS ARC 行为与前置条件](https://docs.aws.amazon.com/eks/latest/userguide/zone-shift.html) · [Auto Mode/Karpenter 集成](https://aws.amazon.com/blogs/containers/arc-zonal-shift-support-for-eks-auto-mode-and-karpenter/)

### 存储注意事项

WaitForFirstConsumer 会延迟初始置备/绑定，直到调度器能够考虑 Pod 放置。**EBS 仍绑定于可用区**。可用区故障后，在另一可用区运行的替代 Pod 无法挂载同一个卷。请通过经过审查的备份/复制方案恢复或迁移数据，并测试 RPO/RTO。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: resilience-ebs
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  encrypted: 'true'
allowVolumeExpansion: true
reclaimPolicy: Retain
```

此 StorageClass 使用标准 EBS CSI 驱动。Auto Mode 使用 ebs.csi.eks.amazonaws.com，并有自己的兼容节点/IAM/迁移要求。无论哪种设计，都要明确设置 encrypted: "true"，并检查创建出的 EBS 卷/KMS 密钥。Auto Mode 节点根盘/数据盘加密不能证明每个工作负载 PVC 都已加密；当前 Auto Mode StorageClass 参数默认值为 false。Retain 会保留已释放的卷供受控恢复/清理；它不是备份，并可能留下仍计费的资源。

若要跨可用区访问共享文件系统，请使用已有的**区域型** EFS 文件系统、可达的挂载目标、TCP 2049 安全规则、经过审查的访问点权限和兼容的 CSI IAM。EFS One Zone 不是相同的韧性设计。以下 ID 均为占位符；这里不会创建文件系统。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: resilience-efs
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: '700'
  basePath: /resilience-demo
reclaimPolicy: Retain
mountOptions:
- tls
```
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: efs-claim
  namespace: resilience-demo
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: resilience-efs
  resources:
    requests:
      storage: 5Gi
```

5Gi PVC 请求并不是 EFS 强制执行的存储配额。TLS 挂载加密和文件系统静态加密是独立设置。Retain 还需要有文档记录的访问点/数据清理流程。

[EKS EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html) · [Auto Mode StorageClass 参数](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html) · [EFS CSI](https://github.com/kubernetes-sigs/aws-efs-csi-driver)

### Istio 本地性路由

在 Istio sidecar 模式的示例中，Istio 会读取运行 Pod 的节点本地性，除非设置了文档说明的本地性覆盖项；普通 Pod 可用区标签不会自动定义这一信息。请验证实际代理端点/本地性和可到达的健康容量。文档所述的本地性故障转移行为需要配置异常检测。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: web-app-locality
  namespace: resilience-demo
spec:
  host: web-app.resilience-demo.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
    loadBalancer:
      simple: ROUND_ROBIN
      localityLbSetting:
        enabled: true
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

作为**加权分布的替代配置**，请用以下片段替换 loadBalancer localityLbSetting。它包含全部三个来源可用区；80/10/10 是配置权重，不是测得的本地流量比例，也不保证有足够的故障转移容量。不要将 distribute 规则与不兼容的 failover 策略组合使用。

```yaml
localityLbSetting:
  enabled: true
  distribute:
  - from: ap-northeast-2/ap-northeast-2a/*
    to:
      ap-northeast-2/ap-northeast-2a/*: 80
      ap-northeast-2/ap-northeast-2b/*: 10
      ap-northeast-2/ap-northeast-2c/*: 10
  - from: ap-northeast-2/ap-northeast-2b/*
    to:
      ap-northeast-2/ap-northeast-2a/*: 10
      ap-northeast-2/ap-northeast-2b/*: 80
      ap-northeast-2/ap-northeast-2c/*: 10
  - from: ap-northeast-2/ap-northeast-2c/*
    to:
      ap-northeast-2/ap-northeast-2a/*: 10
      ap-northeast-2/ap-northeast-2b/*: 10
      ap-northeast-2/ap-northeast-2c/*: 80
```

原先“80% 以上本地流量”“成本降低 60–80%”和“同可用区延迟低于 1ms”的数字仅作为未核验的示意数据保留。其测量来源不可用；健康状况、连接复用、端点组合、请求字节数和价格都会改变结果。

[本地性故障转移](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/failover/) · [加权分布](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/distribute/)

---

## 第 3 级：Cell 架构

### Cell 概念

Cell 是**拥有自己数据存储、缓存和队列的自包含服务单元**。只有当路由、容量和依赖都落实了 Cell 边界时，它才能限制故障影响。

### Cell 分区策略

| 策略 | 说明 | 适用场景 |
| --- | --- | --- |
| 按客户划分 | 根据客户 ID 哈希分配 Cell | SaaS 多租户 |
| 按区域划分 | 根据地理位置分区 | 全球服务 |
| 按容量划分 | 达到容量时创建新 Cell | 均衡负载 |
| 按层级划分 | 按服务层级划分 Cell | Premium/Standard 差异化 |

### 基于 Namespace 的 Cell 实现

Namespace、配额和 NetworkPolicy 提供逻辑边界，而非独立故障域。共享节点、控制平面、CNI、DNS、路由器和数据服务仍是共同依赖。请验证网络插件确实强制执行策略；允许的流量是所有适用策略的并集。下方的路由器 namespace/工作负载必须存在，并带有完全匹配的标签。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cell-1
  labels:
    cell: '1'
    customer-range: a-f
```
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: cell-1-quota
  namespace: cell-1
spec:
  hard:
    requests.cpu: '20'
    requests.memory: 40Gi
    limits.cpu: '40'
    limits.memory: 80Gi
    pods: '100'
    services: '20'
    persistentvolumeclaims: '50'
```
```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: cell-1-limits
  namespace: cell-1
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 128Mi
    type: Container
```
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: cell-1-isolation
  namespace: cell-1
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector: {}
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: cell-router
      podSelector:
        matchLabels:
          app: cell-router
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector: {}
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

DNS 规则允许 TCP 和 UDP 流量访问 kube-system 中匹配的 CoreDNS Pod。本地节点/Auto Mode 系统 DNS 使用不同路径，需要按模式验证。此策略有意不允许任意外部流量：请为必需服务添加经过审查的端点或出口网关规则。仅从 0.0.0.0/0 排除 10.0.0.0/8 并不能隔离所有私有网络或 Cell。

[NetworkPolicy 语义](https://kubernetes.io/docs/concepts/services-networking/network-policies/)

### Shuffle Sharding

若路由、准入限制和数据可用性共同落实该设计，将每个客户稳定分配到一组 Cell，可减少客户之间的故障影响重叠。

```
With 2 Cell combinations from a pool of 8 Cells:
- Customer A → Cell 1, Cell 5
- Customer B → Cell 2, Cell 7
- Customer C → Cell 1, Cell 3

When Cell 1 fails:
- Customer A → Can use Cell 5 if failover routing/data/capacity are ready
- Customer B → Not affected ✅
- Customer C → Can use Cell 3 if failover routing/data/capacity are ready
```

C(8,2)=28。均匀独立分配时，两个客户选中完全相同组合的概率为 1/28（约 3.6%）。一个固定故障 Cell 预计会影响 2/8=25% 的分配，而不是最多影响 25% 的客户或负载。单独使用 ConfigMap 或哈希既不能实现故障转移，也不能实现数据复制。

***

## 第 4 级：多集群/多区域

请按用户旅程及其数据一致性要求选择模式。仅增加第二个集群或区域并不能保证接近零的 RTO/RPO。下表中的早期时间/成本数值只是未经核验的设计示例，并非测量结果或 AWS 承诺。

| 模式 | 早期 RTO 示例 | 早期 RPO 示例 | 早期成本示例 | 设计条件 |
| --- | --- | --- | --- | --- |
| 主动-主动 | 目标约为 0 | 目标约为 0 | 2 倍以上 | 路由、一致性、冲突处理和容量 |
| 主动-被动 | 数分钟至数小时 | 数分钟 | 1.5 倍 | 待机就绪度、复制延迟和提升流程 |
| 区域隔离 | 未指定 | 未指定 | 每个区域 1 倍 | 区域服务独立；不会自动进行区域故障转移 |
| Hub-Spoke | 数分钟 | 数分钟 | 1.3 倍 | Hub 是共享依赖，除非另有保护 |

### Argo CD ApplicationSet

以下三个替代方案都要求已有 Argo CD/ApplicationSet 控制器、已明确注册且可达并带有文档所述标签的集群、仓库凭证，以及预先创建且限制为经审查仓库/目标/资源类型的 AppProject。请将示例仓库和修订版本替换为自己负责的输入。生成的 Application 使用手动同步：启用任何自动同步/修剪策略前，先审查渲染后的目标和清单。任何生成器都不会置备 EKS 集群。

#### 集群生成器

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: resilience-clusters
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions:
  - missingkey=error
  generators:
  - clusters:
      selector:
        matchLabels:
          resilience-example: 'true'
  template:
    metadata:
      name: web-app-{{.nameNormalized}}
    spec:
      project: resilience-reviewed
      source:
        repoURL: https://github.com/example/owned-gitops.git
        targetRevision: REPLACE_WITH_REVIEWED_COMMIT
        path: apps/web-app/overlays/{{.metadata.labels.region}}
      destination:
        server: '{{.server}}'
        namespace: resilience-demo
```

#### Git 目录 × 已注册集群

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: resilience-region-directories
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions:
  - missingkey=error
  generators:
  - matrix:
      generators:
      - git:
          repoURL: https://github.com/example/owned-gitops.git
          revision: REPLACE_WITH_REVIEWED_COMMIT
          directories:
          - path: regions/*
      - clusters:
          selector:
            matchLabels:
              resilience-example: 'true'
              region: '{{.path.basename}}'
  template:
    metadata:
      name: '{{.nameNormalized}}-{{.path.basename}}'
    spec:
      project: resilience-reviewed
      source:
        repoURL: https://github.com/example/owned-gitops.git
        targetRevision: REPLACE_WITH_REVIEWED_COMMIT
        path: '{{.path.path}}'
      destination:
        server: '{{.server}}'
        namespace: resilience-demo
```

第二个矩阵子生成器会将目录基名与已注册集群标签匹配，并使用真实 server 值。不能把区域名称转换为 EKS API URL。缺少标签或无法匹配可能导致不生成 Application；请检查生成的集合，而不只是检查模式有效性。

#### 集群 × 应用列表

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: resilience-cluster-app-matrix
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions:
  - missingkey=error
  generators:
  - matrix:
      generators:
      - clusters:
          selector:
            matchLabels:
              resilience-example: 'true'
      - list:
          elements:
          - app: frontend
            port: '80'
          - app: backend
            port: '8080'
          - app: worker
            port: '9090'
  template:
    metadata:
      name: '{{.nameNormalized}}-{{.app}}'
    spec:
      project: resilience-reviewed
      source:
        repoURL: https://github.com/example/owned-gitops.git
        targetRevision: REPLACE_WITH_REVIEWED_COMMIT
        path: apps/{{.app}}
        helm:
          parameters:
          - name: cluster.name
            value: '{{.name}}'
          - name: service.port
            value: '{{.port}}'
      destination:
        server: '{{.server}}'
        namespace: resilience-demo
```

[ApplicationSet 矩阵参数](https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/Generators-Matrix/)

### Global Accelerator

请使用现有且符合条件的 ALB/NLB 端点，并验证 TLS、健康检查和区域容量足够。以下是可选置备示例，此处未执行。请保存返回的资源 ID 和自己负责的清理计划；执行中途失败不会删除此前已创建的资源。禁用 accelerator 不会免除其资源费用。

```bash
# MUTATIONS: creates a disabled, billable accelerator and its configuration.
set -euo pipefail
: "${GA_API_REGION:?Set the documented Global Accelerator API region}"
: "${ACCELERATOR_NAME:?Set a unique owned name}"
: "${REGION_ONE:?Set the first endpoint region}"
: "${REGION_TWO:?Set the second endpoint region}"
: "${REGION_ONE_LB_ARN:?Set the reviewed eligible ALB/NLB ARN}"
: "${REGION_TWO_LB_ARN:?Set the reviewed eligible ALB/NLB ARN}"
test "$REGION_ONE" != "$REGION_TWO"
ACCELERATOR_ARN=$(aws globalaccelerator create-accelerator \
  --region "$GA_API_REGION" --name "$ACCELERATOR_NAME" \
  --ip-address-type IPV4 --no-enabled --query Accelerator.AcceleratorArn --output text)
test -n "$ACCELERATOR_ARN" && test "$ACCELERATOR_ARN" != None
LISTENER_ARN=$(aws globalaccelerator create-listener \
  --region "$GA_API_REGION" --accelerator-arn "$ACCELERATOR_ARN" \
  --protocol TCP --port-ranges FromPort=443,ToPort=443 \
  --query Listener.ListenerArn --output text)
test -n "$LISTENER_ARN" && test "$LISTENER_ARN" != None
aws globalaccelerator create-endpoint-group \
  --region "$GA_API_REGION" --listener-arn "$LISTENER_ARN" \
  --endpoint-group-region "$REGION_ONE" --traffic-dial-percentage 100 \
  --endpoint-configurations "EndpointId=$REGION_ONE_LB_ARN,Weight=100"
aws globalaccelerator create-endpoint-group \
  --region "$GA_API_REGION" --listener-arn "$LISTENER_ARN" \
  --endpoint-group-region "$REGION_TWO" --traffic-dial-percentage 100 \
  --endpoint-configurations "EndpointId=$REGION_TWO_LB_ARN,Weight=100"
```
```bash
# MUTATION: run separately after endpoint health, routing, data and rollback checks.
: "${ACCELERATOR_ARN:?Use the accelerator just reviewed}"
aws globalaccelerator update-accelerator \
  --region "$GA_API_REGION" --accelerator-arn "$ACCELERATOR_ARN" --enabled
```

流量拨盘表示对新连接而言，已分配到该区域端点组流量的百分比；两个 50% 拨盘并不能构成全球 50/50 分流。此示例将二者都保留为 100%。更改拨盘不会强制迁移现有连接；故障转移规则也可能忽略零拨盘。端点权重和流量拨盘是不同控制项。ALB/NLB 端点健康状态依据 Elastic Load Balancing 健康检查；设置 Global Accelerator /healthz 覆盖项不会配置这些目标组检查。

[流量拨盘语义](https://docs.aws.amazon.com/global-accelerator/latest/dg/about-endpoint-groups-traffic-dial.html) · [端点健康状态](https://repost.aws/knowledge-center/global-accelerator-unhealthy-endpoints) · [故障转移规则](https://repost.aws/knowledge-center/global-accelerator-failover-different-region)

### Istio Multi-Primary 联邦

Sidecar 多主集群/多网络设计需要共享的可信身份模型、不同的集群/网络名称、可达的远程 Kubernetes API 和东西向网关、兼容的 Service/namespace 以及适配的数据行为。单独创建 ServiceEntry 并不能建立联邦。请将网关访问限制在预期网络内；终止 L7 TLS 的负载均衡器与 AUTO_PASSTHROUGH 不兼容。

以下 IstioOperator 是 **istioctl 安装输入**，不是供 kubectl 在集群中应用的 operator。请准备相应的 Tokyo 配置以及完整的官方网关/服务发现设置。DNS 捕获/自动分配标志不能代替这些设置。

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    global:
      meshID: resilience-mesh
      multiCluster:
        clusterName: cluster-seoul
      network: network-seoul
```
```bash
# MUTATIONS: source-cluster credentials/RBAC and destination Secret may be created.
set -euo pipefail
umask 077
: "${SEOUL_CONTEXT:?Verify the owned Seoul context}"
: "${TOKYO_CONTEXT:?Verify the owned Tokyo context}"
test "$SEOUL_CONTEXT" != "$TOKYO_CONTEXT"
test ! -e tokyo-remote-secret.yaml && test ! -e seoul-remote-secret.yaml
istioctl create-remote-secret --context "$TOKYO_CONTEXT" --name cluster-tokyo > tokyo-remote-secret.yaml
istioctl create-remote-secret --context "$SEOUL_CONTEXT" --name cluster-seoul > seoul-remote-secret.yaml
# Inspect Secret metadata without printing token data; verify destination contexts first.
kubectl --context "$SEOUL_CONTEXT" -n istio-system apply -f tokyo-remote-secret.yaml
kubectl --context "$TOKYO_CONTEXT" -n istio-system apply -f seoul-remote-secret.yaml
```

远程 secret 文件包含凭证：请妥善保密，排除在源代码管理之外，并在安装后依照凭证处理策略删除本地副本。上面的命令是在信任/网络设置后执行的变更步骤，不是只读诊断。

显式路由可以使用你在每个集群中设置的工作负载区域 **Pod 模板标签**。节点拓扑标签不会自动复制到 Pod。将 x-region 视为路由输入，而不是授权条件。这些 80/20 权重并未实现数据故障转移协议。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: cross-cluster-routing
  namespace: resilience-demo
spec:
  hosts:
  - web-app.resilience-demo.svc.cluster.local
  http:
  - match:
    - headers:
        x-region:
          exact: tokyo
    route:
    - destination:
        host: web-app.resilience-demo.svc.cluster.local
        subset: tokyo
  - route:
    - destination:
        host: web-app.resilience-demo.svc.cluster.local
        subset: seoul
      weight: 80
    - destination:
        host: web-app.resilience-demo.svc.cluster.local
        subset: tokyo
      weight: 20
```
```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: cross-cluster-subsets
  namespace: resilience-demo
spec:
  host: web-app.resilience-demo.svc.cluster.local
  subsets:
  - name: seoul
    labels:
      workload-region: ap-northeast-2
  - name: tokyo
    labels:
      workload-region: ap-northeast-1
```

对于无关的外部 DNS 服务，可以像下方那样用单独的 ServiceEntry 描述其注册项。这是一种独立的外部服务模式，有自己的 DNS/TLS/应用前置条件；它不会发现第二个集群中的 Kubernetes Service。

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: reviewed-remote-service
  namespace: resilience-demo
spec:
  hosts:
  - remote-service.example.com
  location: MESH_EXTERNAL
  ports:
  - number: 443
    name: https
    protocol: TLS
  resolution: DNS
```

[Istio 多主集群的完整前置条件和步骤](https://istio.io/latest/docs/setup/install/multicluster/multi-primary_multi-network/)

---

## 应用韧性模式

前面的 PDB 和关闭示例只适用于对应的自有工作负载。按百分比设置时，minAvailable 和 maxUnavailable 都向上取整：三个 Pod 的 75% 表示必须有三个 Ready Pod，而 25% 的 maxUnavailable 允许一个 Pod 不可用。控制器滚动更新和直接删除是另外的控制措施。

### 使用 Istio 的断路器

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: backend-circuit-breaker
  namespace: resilience-demo
spec:
  host: backend-service.resilience-demo.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 3s
      http:
        http1MaxPendingRequests: 100
        http2MaxRequests: 1000
        maxRequestsPerConnection: 10
        maxRetries: 3
    outlierDetection:
      consecutive5xxErrors: 5
      consecutiveGatewayErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 30
      splitExternalLocalOriginErrors: true
```

这些限制适用于配置的代理/目标连接池，并非整个集群的并发上限。http2MaxRequests 限制活动 HTTP 请求；maxRetries 限制**同时在途的重试**，不是每个请求的尝试次数。minHealthPercent 控制何时启用异常检测，不会预留该比例的健康容量。异常弹出、连接限制和重试都需要通过测量调优。

### 重试/超时

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: backend-retry-timeout
  namespace: resilience-demo
spec:
  hosts:
  - backend-service.resilience-demo.svc.cluster.local
  http:
  - match:
    - method:
        exact: GET
    route:
    - destination:
        host: backend-service.resilience-demo.svc.cluster.local
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 3s
      retryOn: 5xx,reset,connect-failure
      retryRemoteLocalities: true
```

仅 GET 路由的前提是应用确实允许安全重试这些请求。三次重试是在最初尝试之外的次数，但 10s 总预算、3s 单次尝试上限、退避和并发限制可能导致并非所有尝试都运行。重试会加剧过载或重复副作用；写入操作需要明确的幂等性契约。retryRemoteLocalities 允许尝试其他本地性，但不保证远端有健康容量。Envoy 当前将可重试的 4xx 定义为**仅 409**，不包括 408；乐观锁冲突可能需要重新读取状态，而非重放请求。

[Istio DestinationRule](https://istio.io/latest/docs/reference/config/networking/destination-rule/) · [Envoy 重试条件](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/router_filter)

---

## 混沌工程

混沌工程通过受控故障检验一个可证伪的稳态假设。请从自己负责且具有代表性的测试环境开始；生产实验需要另行审查影响范围、授权、遥测、停止条件和恢复流程。应用 CR 可能触发故障。这里的配置只经过离线检查，没有实际执行，不能证明其已适用于生产。

```bash
# Read-only: verify the exact cluster/namespace and opt-in test workload.
: "${KUBE_CONTEXT:?Set the owned test context}"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pods \
  -l 'app=web-app,experiment-approved=true' -o wide
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pdb
```

### AWS Fault Injection Service（FIS）

请根据官方指南准备 IAM 实验角色/信任策略、所需的 EKS access entry（或文档说明的旧映射方式）、带命名空间范围的 Kubernetes ServiceAccount/Role/RoleBinding，以及按操作配置的 EC2/网络权限。下方示例中的角色和告警 ARN 是同一区域/账户下的占位符：请一致地替换所有值。告警必须已存在、能接收有意义的数据且经过测试；停止条件不是数据恢复，也不能保证零影响。

Pod 目标使用 clusterIdentifier/namespace/selector；**不能将集群 ARN 作为 aws:eks:pod 的 resourceArns**。该操作必须设置 kubernetesServiceAccount。删除 Pod 使用直接删除路径，因此 PDB 不能阻止删除。COUNT(1) 会从选择加入的目标集合中选一个，并不模拟可用区故障。

#### 删除一个 Pod

```json
{
  "description": "Delete one selected test Pod; not an AZ outage",
  "targets": {
    "test-pod": {
      "resourceType": "aws:eks:pod",
      "selectionMode": "COUNT(1)",
      "parameters": {
        "clusterIdentifier": "REPLACE_WITH_OWNED_TEST_CLUSTER",
        "namespace": "resilience-demo",
        "selectorType": "labelSelector",
        "selectorValue": "app=web-app,experiment-approved=true"
      }
    }
  },
  "actions": {
    "delete-one": {
      "actionId": "aws:eks:pod-delete",
      "parameters": {
        "kubernetesServiceAccount": "fis-test",
        "maxErrorsPercent": "0"
      },
      "targets": {
        "Pods": "test-pod"
      }
    }
  },
  "stopConditions": [
    {
      "source": "aws:cloudwatch:alarm",
      "value": "arn:aws:cloudwatch:ap-northeast-2:123456789012:alarm:owned-resilience-stop"
    }
  ],
  "roleArn": "arn:aws:iam::123456789012:role/owned-fis-test"
}
```

#### 为一个 Pod 注入网络延迟

```json
{
  "description": "Add bounded IPv4 latency to one selected test Pod",
  "targets": {
    "test-pod": {
      "resourceType": "aws:eks:pod",
      "selectionMode": "COUNT(1)",
      "parameters": {
        "clusterIdentifier": "REPLACE_WITH_OWNED_TEST_CLUSTER",
        "namespace": "resilience-demo",
        "selectorType": "labelSelector",
        "selectorValue": "app=web-app,experiment-approved=true"
      }
    }
  },
  "actions": {
    "latency": {
      "actionId": "aws:eks:pod-network-latency",
      "parameters": {
        "kubernetesServiceAccount": "fis-test",
        "duration": "PT1M",
        "delayMilliseconds": "200",
        "jitterMilliseconds": "50",
        "sources": "10.20.0.0/24",
        "maxErrorsPercent": "0"
      },
      "targets": {
        "Pods": "test-pod"
      }
    }
  },
  "stopConditions": [
    {
      "source": "aws:cloudwatch:alarm",
      "value": "arn:aws:cloudwatch:ap-northeast-2:123456789012:alarm:owned-resilience-stop"
    }
  ],
  "roleArn": "arn:aws:iam::123456789012:role/owned-fis-test"
}
```

请将示意目的 CIDR 替换为经过审查的测试依赖项。此网络操作需要特权/root 故障注入，不支持 Fargate 或 bridge 网络。它只影响 IPv4；ALL 或 IPv4 CIDR 不会影响 IPv6。请审查当前只读根文件系统和容器安全限制。不要只为运行此示例而放宽生产工作负载的安全配置。FIS 使用注入器 Pod；除 pod-delete 外的操作还使用临时容器。结束进程不会从 Pod 规格中移除不可变的临时容器记录。

#### 中断一个子网的网络

```json
{
  "description": "One owned test subnet network disruption, not a complete AZ outage",
  "targets": {
    "test-subnet": {
      "resourceType": "aws:ec2:subnet",
      "selectionMode": "COUNT(1)",
      "resourceArns": [
        "arn:aws:ec2:ap-northeast-2:123456789012:subnet/subnet-0123456789abcdef0"
      ]
    }
  },
  "actions": {
    "network": {
      "actionId": "aws:network:disrupt-connectivity",
      "parameters": {
        "duration": "PT1M",
        "scope": "all"
      },
      "targets": {
        "Subnets": "test-subnet"
      }
    }
  },
  "stopConditions": [
    {
      "source": "aws:cloudwatch:alarm",
      "value": "arn:aws:cloudwatch:ap-northeast-2:123456789012:alarm:owned-resilience-stop"
    }
  ],
  "roleArn": "arn:aws:iam::123456789012:role/owned-fis-test"
}
```

该子网必须是专用且由你负责的测试子网，不得有无关工作负载。此操作会克隆其 NACL、添加拒绝规则，并在完成后恢复原关联；即便 scope=all，子网内流量仍可工作。它并不等同于整个可用区断电。启动前请验证 NACL 配额、IAM、准确的子网以及管理/遥测访问。停止和恢复都是异步的；请确认实验最终状态以及实际网络/工作负载恢复情况。

```bash
# MUTATION: stop only the recorded experiment ID, not all account experiments.
: "${AWS_REGION:?Set the experiment region}"
: "${EXPERIMENT_ID:?Set the exact running FIS experiment ID}"
aws fis stop-experiment --region "$AWS_REGION" --id "$EXPERIMENT_ID"
```

[FIS EKS Pod 前置条件/RBAC](https://docs.aws.amazon.com/fis/latest/userguide/eks-pod-actions.html) · [操作参数和子网行为](https://docs.aws.amazon.com/fis/latest/userguide/fis-actions-reference.html)

### Litmus Chaos（CNCF 孵化项目）

审查过的 3.31.0 operator 定义了 ChaosEngine、ChaosExperiment 和 ChaosResult，但没有定义 ChaosHub 或 ChaosSchedule。使用这些 engine 示例前，请安装经过审查的版本及各所需 ChaosExperiment，并配置受限 RBAC、验证 runner/helper 镜像。当前目录中的故障文件包含 CI/latest 镜像默认值；不要盲目应用。模式校验并不能证明它与集群/运行时兼容。

这些示例均以 engineState: stop 开始。准备好指定目标后，请按已安装版本的工作流逐次运行实验。活跃的 engine 可能在持续时间内反复删除 Pod；持续 30 秒不代表恰好删除一次。固定的 TARGET_PODS 有意留待你按当前 Pod 名称/UID 选择；不可将其留空，也不可扩展为整个生产选择器。

#### 删除 Pod

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: pod-delete-review
  namespace: resilience-demo
spec:
  engineState: stop
  appinfo:
    appns: resilience-demo
    applabel: app=web-app,experiment-approved=true
    appkind: deployment
  chaosServiceAccount: pod-delete-sa
  experiments:
  - name: pod-delete
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: '30'
        - name: CHAOS_INTERVAL
          value: '10'
        - name: FORCE
          value: 'false'
        - name: TARGET_PODS
          value: REPLACE_WITH_ONE_REVIEWED_POD_NAME
        - name: PODS_AFFECTED_PERC
          value: '100'
```

#### 排空节点，而非终止实例

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: node-drain-review
  namespace: resilience-demo
spec:
  engineState: stop
  appinfo:
    appns: resilience-demo
    applabel: app=web-app,experiment-approved=true
    appkind: deployment
  chaosServiceAccount: node-drain-sa
  experiments:
  - name: node-drain
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: '60'
        - name: TARGET_NODE
          value: REPLACE_WITH_ONE_OWNED_TEST_NODE
```

排空会影响节点上超出应用选择器范围的工作负载。请使用专用测试节点、明确且非空的名称、遵循 PDB 的驱逐行为以及恢复/解除封锁计划。切勿将通用 kubernetes.io/os=linux 选择器替代资源所有权界定。此实验并不终止 EC2 节点。

#### DNS 错误

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: pod-dns-error-review
  namespace: resilience-demo
spec:
  engineState: stop
  appinfo:
    appns: resilience-demo
    applabel: app=web-app,experiment-approved=true
    appkind: deployment
  chaosServiceAccount: pod-dns-error-sa
  experiments:
  - name: pod-dns-error
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: '60'
        - name: TARGET_HOSTNAMES
          value: '["backend-service.resilience-demo.svc.cluster.local"]'
        - name: MATCH_SCHEME
          value: exact
        - name: CONTAINER_RUNTIME
          value: containerd
        - name: SOCKET_PATH
          value: /run/containerd/containerd.sock
        - name: PODS_AFFECTED_PERC
          value: '100'
```

TARGET_HOSTNAMES 是 JSON 数组字符串。运行时/socket/权限假设必须与所选 Linux 测试节点匹配；此示例并不适用于每一种 EKS 节点类型。请限制所选工作负载，避免该百分比选中无关 Pod。观察 ChaosResult 和应用健康状态；仅仅存在资源并不能证明实验成功。

```bash
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get chaosengine,chaosresult
```

[Litmus operator 3.31.0](https://github.com/litmuschaos/chaos-operator/releases/tag/3.31.0) · [官方故障目录](https://github.com/litmuschaos/chaos-charts/tree/master/faults/kubernetes) · [CNCF 项目状态](https://www.cncf.io/projects/litmus/)

### Chaos Mesh

这些示例使用已发布的 2.8.4 CRD 结构。安装前请审查 Helm Chart 的运行时/socket、节点选择、daemon 特权、Dashboard 访问和集群兼容性。特权主机故障注入必须使用明确批准的测试节点类别；不能仅凭模式有效就假设 Auto Mode/Fargate/Hybrid Nodes 都受支持。

下方的 NetworkChaos/IOChaos/TimeChaos 使用该版本的 experiment.chaos-mesh.org/pause 注解暂停。应用暂停状态的清单仍会写入集群。请审查目标和状态，再另行移除暂停；停止时要等待恢复状态。暂停无法撤销已删除的数据，一次性故障也有不同的暂停语义。

#### 网络延迟

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: review-network-delay
  namespace: resilience-demo
  annotations:
    experiment.chaos-mesh.org/pause: 'true'
spec:
  action: delay
  mode: fixed
  value: '1'
  selector:
    namespaces:
    - resilience-demo
    labelSelectors:
      app: web-app
      experiment-approved: 'true'
  delay:
    latency: 100ms
    jitter: 50ms
    correlation: '25'
  duration: 1m
```

#### 网络分区

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: review-network-partition
  namespace: resilience-demo
  annotations:
    experiment.chaos-mesh.org/pause: 'true'
spec:
  action: partition
  mode: fixed
  value: '1'
  selector:
    namespaces:
    - resilience-demo
    labelSelectors:
      app: web-app
      experiment-approved: 'true'
  direction: both
  target:
    mode: fixed
    value: '1'
    selector:
      namespaces:
      - resilience-demo
      labelSelectors:
        app: backend
        experiment-approved: 'true'
  duration: 1m
```

#### I/O 延迟

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: IOChaos
metadata:
  name: review-io-delay
  namespace: resilience-demo
  annotations:
    experiment.chaos-mesh.org/pause: 'true'
spec:
  action: latency
  mode: fixed
  value: '1'
  selector:
    namespaces:
    - resilience-demo
    labelSelectors:
      app: web-app
      experiment-approved: 'true'
  volumePath: /audit-data
  delay: 100ms
  percent: 50
  duration: 1m
```

请使用挂载在 /audit-data 的一次性测试卷。此示例未设置可选路径过滤器；启用前请确认所选文件。percent 表示注入操作的百分比，不是容量上限。不要将此示例指向生产 PostgreSQL 的原始数据目录。请基于已知基线验证恢复和数据完整性。

#### 时间偏移

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: TimeChaos
metadata:
  name: review-time-offset
  namespace: resilience-demo
  annotations:
    experiment.chaos-mesh.org/pause: 'true'
spec:
  mode: fixed
  value: '1'
  selector:
    namespaces:
    - resilience-demo
    labelSelectors:
      app: web-app
      experiment-approved: 'true'
  timeOffset: -2h
  clockIds:
  - CLOCK_REALTIME
  duration: 1m
```

-2h 偏移会影响所选注入程序的 CLOCK_REALTIME 行为，并非将节点及其所有时钟统一修改两小时。推断令牌、调度器或租约行为之前，请检查注入机制和应用使用时钟的方式。持续时间限定预期故障时段，不保证应用在该时间内恢复。

```bash
kubectl --context "$KUBE_CONTEXT" -n resilience-demo \
  get networkchaos,iochaos,timechaos -o yaml
```

[Chaos Mesh 2.8.4 Chart](https://github.com/chaos-mesh/chaos-mesh/tree/v2.8.4/helm/chaos-mesh) · [暂停控制器](https://github.com/chaos-mesh/chaos-mesh/blob/v2.8.4/controllers/common/desiredphase/controller.go)

### Game Day 演练框架

注入故障前，请定义中止阈值、独立观察方和明确的恢复负责人。分别记录故障检测和恢复时间，包括失败/无数据的观测。完成一个实验后再开始下一个；请验证已恢复，而不是仅因故障持续时间结束就宣布成功。

| 阶段 | 活动 | 交付物 |
| --- | --- | --- |
| 1. 记录稳态 | 收集指标基线 | Dashboard 快照 |
| 2. 注入故障 | 运行 FIS/Litmus 实验 | 实验日志 |
| 3. 观察恢复 | 监控自动恢复过程 | 恢复时间测量 |
| 4. 分析影响 | 分析错误率和延迟变化 | 影响报告 |
| 5. 复盘 | 识别改进项和行动事项 | 改进计划 |

***

## 实施检查清单

### 第 1 级：基础

* [ ] 为每个长期运行的应用选择合适的健康探针
* [ ] 设置资源 requests/limits
* [ ] 配置 PodDisruptionBudget
* [ ] 实现优雅关闭（preStop hook）
* [ ] 设置合适的 terminationGracePeriodSeconds

### 第 2 级：多可用区

* [ ] 应用 Pod 拓扑分布约束
* [ ] 验证实际 Pod/节点分布及故障后存活区的余量
* [ ] 规划可用区存储恢复；新置备时使用 WaitForFirstConsumer
* [ ] 审查 ARC 资格、N-1 就绪度、告警和独立的 autoshift 授权
* [ ] 监控跨可用区流量成本

### 第 3 级：Cell 架构

* [ ] 定义 Cell 边界（Namespace 或 Cluster）
* [ ] 实现 Cell Router
* [ ] 验证 Cell 边界和网络插件的策略强制执行
* [ ] 实现 Shuffle Sharding
* [ ] 为每个 Cell 设置 ResourceQuota

### 第 4 级：多区域

* [ ] 选择多区域架构模式
* [ ] 配置 Global Accelerator
* [ ] 使用 Argo CD ApplicationSet 部署多集群
* [ ] 建立数据复制策略
* [ ] 通过 GitOps 保持一致性

***

## 成本注意事项

以下保留了原先未经核验的成本示意，而非当前报价或测得的节省。跨可用区费用取决于服务、流量路径/方向和区域；$0.01/GB 并非适用于所有 EKS 的全包费率。请根据当前服务定价页面，对实际资源和故障余量计价。本次没有重跑成本/混沌基准测试。

| 项目 | 成本影响 | 降低成本的策略 |
| --- | --- | --- |
| 多区域主动-主动 | 比单一区域高 2 倍以上 | 使用主动-被动，将被动侧成本降低 50–70% |
| 跨可用区流量 | $0.01/GB（同一区域内） | 使用本地性路由降低 60–80% |
| Spot 实例 | 比 On-Demand 节省 60–90% | 用于无状态工作负载 |
| 混沌工程 | 早期估计为每月 $100–500；实际按 FIS/资源用量计费 | 限制实验资源和持续时间 |
| Cell 架构 | 早期估计成本增加 10–20% | 测量隔离开销和运维价值 |

***

## 后续步骤

* [EKS 高级调试与事件响应](11-eks-advanced-debugging.md)
* [EKS 高可用性测验](../quizzes/eks/10-eks-resiliency-quiz.md)
* [Istio Service Mesh](../service-mesh/02-istio.md) - 深入了解断路器和重试
