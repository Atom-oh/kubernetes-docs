# EKS 韧性与高可用性

> **支持版本**: EKS 1.28+, Istio 1.20+, Karpenter 1.0+ **最后更新**: February 23, 2026

## 韧性概述

韧性是指**在故障期间尽量降低影响，同时恢复到正常状态或维持服务的能力**。它超越了简单的高可用性 (HA)，代表了一种预见故障并为故障做好准备的设计理念。

### 韧性成熟度模型

| 级别 | 名称         | 范围             | 关键技术                             | RTO 目标          |
| ----- | ------------ | ----------------- | ------------------------------------ | ----------------- |
| 1     | 基础         | Pod               | Probes, Resource Limits, PDB         | 分钟              |
| 2     | Multi-AZ     | Availability Zone | Topology Spread, ARC Zonal Shift     | 秒                |
| 3     | Cell-Based   | Service Unit      | Shuffle Sharding, Cell Router        | 秒（部分）        |
| 4     | Multi-Region | Region            | Global Accelerator, Data Replication | 接近零            |

> 并非所有服务都需要 Level 4。请根据 SLA 要求、法规和预算选择合适的级别。

***

## Level 1: 基础韧性（Pod 级别）

### Liveness/Readiness/Startup Probes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
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
      containers:
      - name: app
        image: web-app:1.0
        ports:
        - containerPort: 8080
        startupProbe:
          httpGet:
            path: /healthz
            port: 8080
          failureThreshold: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 0
          periodSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          periodSeconds: 5
          failureThreshold: 3
        resources:
          requests:
            cpu: "250m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
```

### PodDisruptionBudget (PDB)

PDB 可确保在自愿中断期间保持最低可用性。

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
spec:
  # Method 1: Minimum available Pods
  minAvailable: 2
  # Method 2: Maximum unavailable Pods (use only one)
  # maxUnavailable: 1
  selector:
    matchLabels:
      app: web-app
```

```bash
# Check PDB status
kubectl get pdb web-app-pdb
# NAME          MIN AVAILABLE   MAX UNAVAILABLE   ALLOWED DISRUPTIONS   AGE
# web-app-pdb   2               N/A               1                     5m
```

### 优雅关闭

```yaml
spec:
  terminationGracePeriodSeconds: 60
  containers:
  - name: app
    lifecycle:
      preStop:
        exec:
          command: ["/bin/sh", "-c", "sleep 5"]
```

> 在 `preStop` 中等待 5 秒的原因：如果 Pod 在 endpoint 移除传播完成之前终止，就会发生流量丢失。sleep 可确保有足够的传播时间。

***

## Level 2: Multi-AZ 策略

### Pod Topology Spread Constraints

将 Pods 均匀分布到各个可用区。

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
      # Hard constraint: Maximum 1 difference between AZs
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-app
        minDomains: 3
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

| 参数                | 说明                                                     |
| ------------------- | -------------------------------------------------------- |
| `maxSkew`           | 拓扑域之间 Pod 数量的最大差异                            |
| `topologyKey`       | 分布依据（zone、hostname 等）                            |
| `whenUnsatisfiable` | `DoNotSchedule`（硬约束）或 `ScheduleAnyway`（软约束）   |
| `minDomains`        | 域的最小数量（3 个 AZ 时为 3）                           |

### Karpenter Multi-AZ NodePool

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
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    budgets:
    - nodes: "20%"    # Maximum 20% disrupted simultaneously
    - nodes: "0"
      schedule: "0 9 * * 1-5"   # No disruption during business hours
      duration: 8h
```

### ARC Zonal Shift

AWS Application Recovery Controller (ARC) Zonal Shift 会自动将流量从发生故障的 AZ 重定向出去。

```bash
# Start Zonal Shift (manual)
aws arc-zonal-shift start-zonal-shift \
  --resource-identifier arn:aws:elasticloadbalancing:ap-northeast-2:123456789012:loadbalancer/app/my-alb/abc123 \
  --away-from ap-northeast-2a \
  --expires-in 1h \
  --comment "AZ-a experiencing issues"

# Enable Zonal Autoshift (automatic)
aws arc-zonal-shift create-practice-run-configuration \
  --resource-identifier $ALB_ARN \
  --outcome-alarms '[{"alarmIdentifier": {"alarmName": "my-alarm", "region": "ap-northeast-2"}, "type": "CLOUDWATCH"}]'
```

### 存储注意事项

**防止 EBS AZ 锁定问题：**

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-sc
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer  # Create volume after Pod scheduling
parameters:
  type: gp3
```

**使用 EFS 实现 Cross-AZ 访问：**

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-12345
  directoryPerms: "700"
```

### Istio Locality-Aware Routing

优先处理同一 AZ 内的流量可将 Cross-AZ 传输成本降低 60-80%。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: web-app-dr
spec:
  host: web-app.default.svc.cluster.local
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
    connectionPool:
      tcp:
        maxConnections: 100
  # Locality-aware routing is handled automatically by Istio
  # Based on Pod's topology.kubernetes.io/zone label
```

***

## Level 3: Cell-Based 架构

### Cell 概念

Cell 是**一个自包含的 Service Unit，拥有自己的 data store、cache 和 queue**。它将故障的爆炸半径隔离到特定 Cell。

### Cell 分区策略

| 策略           | 说明                              | 适用场景                         |
| -------------- | --------------------------------- | -------------------------------- |
| Customer-based | 按客户 ID hash 分配 Cell          | SaaS multi-tenant                |
| Region-based   | 按地理位置分区                    | Global services                  |
| Capacity-based | 达到容量时创建新 Cell             | 均匀负载分布                     |
| Tier-based     | 按服务层级分配 Cell               | Premium/Standard 差异化          |

### 基于 Namespace 的 Cell 实现

```yaml
# Cell A Namespace
apiVersion: v1
kind: Namespace
metadata:
  name: cell-a
  labels:
    cell: a
    tier: standard
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: cell-a-quota
  namespace: cell-a
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: cell-isolation
  namespace: cell-a
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          cell: a
    - namespaceSelector:
        matchLabels:
          role: cell-router
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          cell: a
    - namespaceSelector:
        matchLabels:
          role: shared-services
```

### Shuffle Sharding

将每个客户分配到随机选择的 Cells 组合，可以最大限度减少单个 Cell 故障所影响的客户数量。

```
With 2 Cell combinations from a pool of 8 Cells:
- Customer A → Cell 1, Cell 5
- Customer B → Cell 2, Cell 7
- Customer C → Cell 1, Cell 3

When Cell 1 fails:
- Customer A → Automatically switches to Cell 5 ✅
- Customer B → Not affected ✅
- Customer C → Automatically switches to Cell 3 ✅
```

组合数量：C(8,2) = 28，因此两个客户共享同一组合的概率非常低。

***

## Level 4: Multi-Cluster / Multi-Region

### 架构模式比较

| 模式               | RTO        | RPO     | 成本          | 复杂度     |
| ------------------ | ---------- | ------- | ------------- | ---------- |
| Active-Active      | \~0        | \~0     | 2x+           | 非常高     |
| Active-Passive     | 分钟\~小时 | 分钟    | 1.5x          | 高         |
| Regional Isolation | N/A        | N/A     | 每 region 1x  | 中         |
| Hub-Spoke          | 分钟       | 分钟    | 1.3x          | 中         |

### 使用 ArgoCD ApplicationSet 进行 Multi-Cluster 部署

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: web-app-set
  namespace: argocd
spec:
  generators:
  # Cluster Generator: Based on cluster labels
  - clusters:
      selector:
        matchLabels:
          environment: production
  template:
    metadata:
      name: 'web-app-{{name}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/org/k8s-manifests.git
        targetRevision: main
        path: 'apps/web-app/overlays/{{metadata.labels.region}}'
      destination:
        server: '{{server}}'
        namespace: web-app
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

### Global Accelerator 集成

```bash
# Create Global Accelerator
aws globalaccelerator create-accelerator \
  --name prod-accelerator \
  --ip-address-type IPV4

# Add endpoint groups (each region)
aws globalaccelerator create-endpoint-group \
  --listener-arn $LISTENER_ARN \
  --endpoint-group-region ap-northeast-2 \
  --endpoint-configurations "EndpointId=$NLB_ARN_APNE2,Weight=50" \
  --health-check-path /healthz
```

### Istio Multi-Primary Federation

```yaml
# Cross-cluster service discovery
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: web-app-remote
spec:
  hosts:
  - web-app.default.svc.cluster.local
  location: MESH_INTERNAL
  ports:
  - number: 80
    name: http
    protocol: HTTP
  resolution: DNS
  endpoints:
  - address: web-app.remote-cluster.example.com
    locality: us-west-2/us-west-2a
    ports:
      http: 80
```

***

## Chaos Engineering

Chaos Engineering 是**通过在生产环境中有意注入故障，主动发现系统弱点的方法论**。

### AWS Fault Injection Service (FIS)

```json
{
  "description": "AZ Failure Simulation",
  "targets": {
    "eks-pods": {
      "resourceType": "aws:eks:pod",
      "selectionMode": "ALL",
      "parameters": {
        "clusterIdentifier": "production-cluster",
        "namespace": "default",
        "selectorType": "labelSelector",
        "selectorValue": "app=web-app"
      }
    }
  },
  "actions": {
    "delete-pods": {
      "actionId": "aws:eks:pod-delete",
      "parameters": {},
      "targets": { "Pods": "eks-pods" }
    }
  },
  "stopConditions": [
    {
      "source": "aws:cloudwatch:alarm",
      "value": "arn:aws:cloudwatch:ap-northeast-2:123456789012:alarm:error-rate-high"
    }
  ]
}
```

### Litmus Chaos (CNCF Incubating)

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: pod-delete-chaos
  namespace: default
spec:
  appinfo:
    appns: default
    applabel: app=web-app
    appkind: deployment
  chaosServiceAccount: litmus-admin
  experiments:
  - name: pod-delete
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: "30"
        - name: CHAOS_INTERVAL
          value: "10"
        - name: FORCE
          value: "false"
```

### Chaos Mesh

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: network-delay
spec:
  action: delay
  mode: all
  selector:
    namespaces:
    - default
    labelSelectors:
      app: web-app
  delay:
    latency: "100ms"
    jitter: "50ms"
    correlation: "25"
  duration: "5m"
```

### Game Day Framework

| 阶段                   | 活动                                | 交付物                    |
| ---------------------- | ----------------------------------- | ------------------------- |
| 1. 记录稳定状态        | 收集指标基线                        | Dashboard 快照            |
| 2. 注入故障            | 运行 FIS/Litmus 实验                | 实验日志                  |
| 3. 观察恢复            | 监控自动恢复过程                    | 恢复时间测量              |
| 4. 分析影响            | 分析错误率和延迟变化                | 影响报告                  |
| 5. 事后复盘            | 识别改进项和 Action Items           | 改进计划                  |

***

## 实施检查清单

### Level 1 基础

* [ ] 为所有 containers 设置 Liveness/Readiness Probe
* [ ] 设置 Resource requests/limits
* [ ] 配置 PodDisruptionBudget
* [ ] 实现优雅关闭（preStop hook）
* [ ] 设置合适的 terminationGracePeriodSeconds

### Level 2 Multi-AZ

* [ ] 应用 Pod Topology Spread Constraints
* [ ] 在 Karpenter NodePool 中配置 3 AZ 分布
* [ ] 在 StorageClass 中设置 `WaitForFirstConsumer`
* [ ] 启用 ARC Zonal Shift
* [ ] 监控 Cross-AZ 流量成本

### Level 3 Cell-Based

* [ ] 定义 Cell 边界（Namespace 或 Cluster）
* [ ] 实现 Cell Router
* [ ] 使用 NetworkPolicy 隔离 Cells
* [ ] 实现 Shuffle Sharding
* [ ] 为每个 Cell 设置 ResourceQuota

### Level 4 Multi-Region

* [ ] 决定 Multi-Region 架构模式
* [ ] 配置 Global Accelerator
* [ ] 使用 ArgoCD ApplicationSet 部署 multi-cluster
* [ ] 建立数据复制策略
* [ ] 通过 GitOps 保持一致性

***

## 成本注意事项

| 项目                       | 成本影响                             | 成本降低策略                                 |
| -------------------------- | ------------------------------------ | -------------------------------------------- |
| Multi-Region Active-Active | 相比单 region 为 2x+                 | 使用 Active-Passive 将 Passive 降低 50-70%   |
| Cross-AZ Traffic           | $0.01/GB（同一 region 内）           | 使用 Locality-aware routing 降低 60-80%      |
| Spot Instance              | 相比 On-Demand 节省 60-90%           | 应用于无状态 workloads                       |
| Chaos Engineering          | FIS 实验成本                         | 通过故障预防获得 ROI                         |

***

## 后续步骤

* [EKS 高级调试与事件响应](11-eks-advanced-debugging.md)
* [EKS 高可用性测验](../quizzes/eks/10-eks-resiliency-quiz.md)
* [Istio Service Mesh](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/02-istio.md) - Circuit Breaker、Retry 深入解析
