# Amazon EKS 高可用性和弹性测验

本测验用于测试你对 Amazon EKS cluster 高可用性（HA）、弹性、Multi-AZ 部署、Cell-Based Architecture（基于 Cell 的架构）、Chaos Engineering（混沌工程）、PodDisruptionBudget 和 Topology Spread Constraints 的理解。

## 测验概览
- Multi-AZ Architecture 和配置
- Cell-Based Architecture 模式
- Chaos Engineering 原则和工具
- PodDisruptionBudget (PDB) 配置
- Topology Spread Constraints
- 灾难恢复和故障转移

## 选择题

### 1. 在 Amazon EKS 中，Multi-AZ 部署的主要优势是什么？

A. 降低成本
B. 即使单个 AZ 发生故障，也能维持应用程序可用性
C. 增加网络延迟
D. 降低管理复杂性

<details>
<summary>查看答案</summary>

**答案：B. 即使单个 AZ 发生故障，也能维持应用程序可用性**

**解释：**
Multi-AZ 部署的关键优势是，即使单个 Availability Zone（AZ）发生故障，workloads 仍可在其他 AZ 中继续运行，从而维持应用程序可用性。

**Multi-AZ 部署的主要优势：**
- 单个 AZ 故障期间自动故障转移
- 数据中心级别的容错能力
- 能够实现 99.99%+ 可用性
- 增强的区域灾难恢复能力

```yaml
# Multi-AZ Node Group Configuration Example
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ha-cluster
  region: us-west-2
nodeGroups:
  - name: ng-multi-az
    instanceType: m5.large
    desiredCapacity: 6
    availabilityZones: ["us-west-2a", "us-west-2b", "us-west-2c"]
```

</details>

### 2. PodDisruptionBudget (PDB) 的主要用途是什么？

A. 限制 Pod CPU 使用量
B. 在自愿中断期间确保最少可用 Pods
C. 控制 Pods 之间的网络流量
D. 监控 Pod 内存使用量

<details>
<summary>查看答案</summary>

**答案：B. 在自愿中断期间确保最少可用 Pods**

**解释：**
PodDisruptionBudget (PDB) 确保在 node drain、cluster 升级和 autoscaling 事件等自愿中断期间，最少数量的 Pods 保持运行。

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
spec:
  minAvailable: 2  # or maxUnavailable: 1
  selector:
    matchLabels:
      app: web-app
```

**PDB 的主要特性：**
- `minAvailable`：必须保持可用的 Pods 最小数量
- `maxUnavailable`：可同时不可用的 Pods 最大数量
- 在 rolling updates 和 node 维护期间确保服务连续性

</details>

### 3. Topology Spread Constraints 中的 `whenUnsatisfiable: DoNotSchedule` 表示什么？

A. 如果无法满足约束，则将 Pod 调度到任意 node
B. 如果无法满足约束，则拒绝 Pod 调度
C. 忽略约束并始终调度
D. 当违反约束时删除现有 Pods

<details>
<summary>查看答案</summary>

**答案：B. 如果无法满足约束，则拒绝 Pod 调度**

**解释：**
如果无法满足 topology spread constraints，`whenUnsatisfiable: DoNotSchedule` 会拒绝 Pod 调度。这用于强制执行严格的分布策略。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 6
  template:
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-app
```

**whenUnsatisfiable 选项：**
- `DoNotSchedule`：如果不满足约束，则拒绝调度（Hard constraint）
- `ScheduleAnyway`：尽力满足约束，如果无法满足则调度到任意位置（Soft constraint）

</details>

### 4. 以下哪一项不是 Cell-Based Architecture 中 “Cell” 的关键特征？

A. 可以独立部署和扩展
B. 故障会传播到整个系统
C. 自包含的功能单元
D. 与其他 Cells 松耦合

<details>
<summary>查看答案</summary>

**答案：B. 故障会传播到整个系统**

**解释：**
Cell-Based Architecture 的核心目的是故障隔离。每个 Cell 独立运行，因此一个 Cell 中的故障不会传播到其他 Cells。

**Cell-Based Architecture 的核心原则：**
1. **故障隔离**：一个 Cell 中的故障不会影响其他 Cell
2. **独立部署**：每个 Cell 都可以单独更新
3. **水平扩展**：在 Cell 级别扩展容量
4. **自包含**：每个 Cell 包含所有必要组件

```yaml
# Cell-based Namespace Configuration Example
apiVersion: v1
kind: Namespace
metadata:
  name: cell-a
  labels:
    cell: a
    region: us-west-2
---
apiVersion: v1
kind: Namespace
metadata:
  name: cell-b
  labels:
    cell: b
    region: us-west-2
```

</details>

### 5. Chaos Engineering 中的 “Steady State Hypothesis” 是什么意思？

A. 让系统始终保持停止状态
B. 用于在实验前后验证正常系统行为的可测量基线
C. 停止 chaos experiments 的条件
D. 系统的最大负载状态

<details>
<summary>查看答案</summary>

**答案：B. 用于在实验前后验证正常系统行为的可测量基线**

**解释：**
Steady State Hypothesis 为系统的“正常”状态定义可测量指标。在 chaos experiment 之前，验证该假设为真；实验之后，验证系统是否恢复到此状态。

**Steady State Metrics 示例：**
- 响应时间 < 200ms (p99)
- 错误率 < 0.1%
- 吞吐量 > 1000 req/s
- Pod 可用性 > 99%

```yaml
# Litmus Chaos Experiment Definition Example
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosExperiment
metadata:
  name: pod-delete
spec:
  definition:
    steadyState:
      metrics:
        - name: response_time_p99
          threshold: 200
          comparison: lessThan
        - name: error_rate
          threshold: 0.1
          comparison: lessThan
```

</details>

### 6. 在 EKS 中，用于实现 Zone-Aware Routing 的 Service annotation 是什么？

A. `service.kubernetes.io/topology-aware-hints: auto`
B. `service.kubernetes.io/zone-routing: enabled`
C. `service.kubernetes.io/local-only: true`
D. `service.kubernetes.io/cross-zone: disabled`

<details>
<summary>查看答案</summary>

**答案：A. `service.kubernetes.io/topology-aware-hints: auto`**

**解释：**
Topology Aware Hints 在 Kubernetes 1.23+ 中引入，允许 kube-proxy 优先将流量路由到同一 Zone 中的 endpoints，从而降低跨 AZ 流量成本和延迟。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-service
  annotations:
    service.kubernetes.io/topology-aware-hints: auto
spec:
  selector:
    app: web-app
  ports:
  - port: 80
    targetPort: 8080
```

**Zone-Aware Routing 的优势：**
- 降低跨 AZ 数据传输成本
- 更低的网络延迟
- 通过将流量保持在同一 Zone 内来提高可靠性

</details>

### 7. 在 PDB 中设置 `maxUnavailable: 25%` 且有 8 个 replicas 时，最多可以同时中断多少个 Pods？

A. 1
B. 2
C. 3
D. 4

<details>
<summary>查看答案</summary>

**答案：B. 2**

**解释：**
`maxUnavailable: 25%` 表示总 replicas 的最多 25% 可以同时中断。8 的 25% 是 2（8 × 0.25 = 2）。

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
spec:
  maxUnavailable: 25%  # 2 out of 8 can be disrupted
  selector:
    matchLabels:
      app: web-app
```

**计算方法：**
- 百分比向下取整
- replicas = 8, maxUnavailable = 25%
- 8 × 0.25 = 2（截断小数）
- 因此，必须始终至少保留 6 个 Pods 运行

</details>

### 8. 以下哪一项不是 Litmus Chaos 提供的 experiment 类型？

A. pod-delete
B. node-drain
C. network-loss
D. cluster-delete

<details>
<summary>查看答案</summary>

**答案：D. cluster-delete**

**解释：**
Litmus Chaos 不提供删除整个 cluster 的 experiment。Chaos Engineering 的目的是在受控环境中测试系统弹性，而不是销毁整个基础设施。

**主要 Litmus Chaos Experiment 类型：**
- **Pod 级别**：pod-delete, pod-cpu-hog, pod-memory-hog, pod-network-loss
- **Node 级别**：node-drain, node-cpu-hog, node-memory-hog, node-taint
- **Network 级别**：network-loss, network-latency, network-corruption
- **AWS 特定**：ec2-terminate, ebs-loss, az-chaos

```bash
# Litmus Chaos Installation
kubectl apply -f https://litmuschaos.github.io/litmus/litmus-operator-v2.14.0.yaml
```

</details>

### 9. EKS Control Plane 的高可用性如何得到保证？

A. 用户必须手动配置 Multi-AZ
B. AWS 会自动跨多个 AZ 管理它
C. 它仅在单个 AZ 中运行
D. 需要手动故障转移配置

<details>
<summary>查看答案</summary>

**答案：B. AWS 会自动跨多个 AZ 管理它**

**解释：**
Amazon EKS Control Plane 由 AWS 完全托管，并自动以高可用方式部署在多个 Availability Zones 中。etcd 数据也会复制到多个 AZ。

**EKS Control Plane HA 特性：**
- 自动 Multi-AZ 部署（至少 2 个 AZ）
- 自动 API server 扩展
- 自动 etcd 数据复制和备份
- 自动故障检测和恢复
- 99.95% SLA 保证

**用户责任：**
- Data plane (node) Multi-AZ 配置
- Workload Pod 分布
- PDB 和 Topology Spread 设置

</details>

### 10. Topology Spread Constraints 中的 `maxSkew` 表示什么？

A. Pods 的最大数量
B. topology domains 之间 Pod 数量的最大允许差异
C. nodes 的最小数量
D. 每个 node 的最大 Pods 数

<details>
<summary>查看答案</summary>

**答案：B. topology domains 之间 Pod 数量的最大允许差异**

**解释：**
`maxSkew` 是不同 topology domains（例如 AZs、nodes）之间 Pod 数量的最大允许差异。例如，使用 `maxSkew: 1` 时，任意两个 domains 之间的 Pod 数量差异不能超过 1。

```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      topologySpreadConstraints:
      - maxSkew: 1  # Maximum 1 Pod difference between domains
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-app
```

**maxSkew 示例（replicas=6, 3 AZs）：**
- maxSkew=1：Zone-A(2), Zone-B(2), Zone-C(2) - 均匀分布
- maxSkew=2：Zone-A(3), Zone-B(2), Zone-C(1) - 允许
- maxSkew=1 违规：Zone-A(4), Zone-B(1), Zone-C(1) - 调度被拒绝

</details>

## 简答题

### 1. 在 EKS 中，用于降低跨 AZ 数据传输成本的 Service annotation 是什么？

<details>
<summary>查看答案</summary>

**答案：** `service.kubernetes.io/topology-aware-hints: auto`

**解释：**
将此 annotation 添加到 Service 会启用 Kubernetes Topology Aware Hints，它会优先将流量路由到同一 AZ 内的 endpoints。

```yaml
apiVersion: v1
kind: Service
metadata:
  annotations:
    service.kubernetes.io/topology-aware-hints: auto
```

</details>

### 2. 列出 PodDisruptionBudget 中 “Voluntary Disruption” 的 3 个示例。

<details>
<summary>查看答案</summary>

**答案：**
1. Node drain (kubectl drain)
2. Cluster upgrade
3. Cluster Autoscaler 执行的 node scale-down

**其他示例：**
- Deployment/StatefulSet 的 rolling updates
- 手动 Pod 删除 (kubectl delete pod)
- 用于维护的 node cordon/drain

**Involuntary Disruption 示例：**
- 硬件故障
- Kernel panic
- VM 删除
- OOM Kill

</details>

### 3. 列出 Chaos Engineering 的 4 个核心原则。

<details>
<summary>查看答案</summary>

**答案：**
1. **Build a Steady State Hypothesis**：为正常状态定义可测量指标
2. **Vary Real-World Events**：模拟真实世界的故障场景
3. **Run Experiments in Production**：在可能的情况下在真实环境中测试
4. **Minimize Blast Radius**：限制实验影响并设置自动中止条件

**其他原则：**
- 自动化实验以进行持续验证
- 分析结果并改进系统

</details>

### 4. 配置 EKS node groups 以实现 Multi-AZ 时，建议的最小 AZ 数量是多少？

<details>
<summary>查看答案</summary>

**答案：** 3

**解释：**
将 nodes 分布在 3 个或更多 AZ 中可提供：
- 单个 AZ 故障期间维持 2/3 容量
- 为基于 quorum 的系统（例如 etcd）提供稳定性
- 更均匀的 workload 分布

```yaml
# eksctl Multi-AZ Node Group Configuration
nodeGroups:
  - name: ng-multi-az
    availabilityZones:
      - us-west-2a
      - us-west-2b
      - us-west-2c
    desiredCapacity: 6
```

</details>

### 5. 在 Cell-Based Architecture 中，流量如何路由到特定 Cell？

<details>
<summary>查看答案</summary>

**答案：** routing layer（例如 API Gateway、Service Mesh、Load Balancer）基于用户/tenant ID 将流量分发到特定 Cells。

**实现方法：**
1. **基于哈希的路由**：对 user ID 进行哈希以确定 Cell
2. **显式映射**：维护 user-to-Cell 映射表
3. **基于 Region**：基于地理位置分配 Cell

```yaml
# Cell Routing Example with Istio VirtualService
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: cell-router
spec:
  http:
  - match:
    - headers:
        x-cell-id:
          exact: "cell-a"
    route:
    - destination:
        host: app.cell-a.svc.cluster.local
  - match:
    - headers:
        x-cell-id:
          exact: "cell-b"
    route:
    - destination:
        host: app.cell-b.svc.cluster.local
```

</details>

## 动手练习

### 1. 编写一个满足以下要求的 PodDisruptionBudget YAML：
- Name: api-server-pdb
- Target: 带有 label `app: api-server` 的 Pods
- 必须始终至少有 3 个 Pods 保持运行

<details>
<summary>查看答案</summary>

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-server-pdb
spec:
  minAvailable: 3
  selector:
    matchLabels:
      app: api-server
```

**验证命令：**
```bash
# Create PDB
kubectl apply -f api-server-pdb.yaml

# Check PDB status
kubectl get pdb api-server-pdb

# View detailed information
kubectl describe pdb api-server-pdb
```

**预期输出：**
```
NAME              MIN AVAILABLE   MAX UNAVAILABLE   ALLOWED DISRUPTIONS   AGE
api-server-pdb    3               N/A               2                     10s
```

</details>

### 2. 编写一个带有 Topology Spread Constraints 的 Deployment，将 Pods 均匀分布到 3 个 AZ。
- Deployment name: web-frontend
- replicas: 6
- maxSkew: 1
- Distribution key: topology.kubernetes.io/zone

<details>
<summary>查看答案</summary>

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
spec:
  replicas: 6
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-frontend
      containers:
      - name: web
        image: nginx:latest
        ports:
        - containerPort: 80
```

**验证命令：**
```bash
# Create Deployment
kubectl apply -f web-frontend.yaml

# Check Pod distribution
kubectl get pods -l app=web-frontend -o wide

# Check Pod count per Zone
kubectl get pods -l app=web-frontend -o jsonpath='{range .items[*]}{.spec.nodeName}{"\n"}{end}' | \
  xargs -I {} kubectl get node {} -o jsonpath='{.metadata.labels.topology\.kubernetes\.io/zone}{"\n"}' | \
  sort | uniq -c
```

**预期输出：**
```
2 us-west-2a
2 us-west-2b
2 us-west-2c
```

</details>

### 3. 使用 Litmus Chaos 定义一个 chaos experiment 来删除特定 Pods。
- Target: namespace `production` 中带有 label `app: payment-service` 的 Pods
- Experiment duration: 30 seconds
- Number of Pods to delete: 1

<details>
<summary>查看答案</summary>

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: payment-pod-delete
  namespace: production
spec:
  appinfo:
    appns: production
    applabel: app=payment-service
    appkind: deployment
  engineState: active
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
        - name: PODS_AFFECTED_PERC
          value: "100"
        - name: TARGET_PODS
          value: ""
        - name: FORCE
          value: "false"
```

**先决条件：**
```bash
# Install Litmus Chaos Operator
kubectl apply -f https://litmuschaos.github.io/litmus/litmus-operator-v2.14.0.yaml

# Install ChaosExperiment CRD
kubectl apply -f https://hub.litmuschaos.io/api/chaos/2.14.0?file=charts/generic/pod-delete/experiment.yaml

# Create ServiceAccount
kubectl apply -f https://hub.litmuschaos.io/api/chaos/2.14.0?file=charts/generic/pod-delete/rbac.yaml -n production
```

**验证命令：**
```bash
# Run Chaos experiment
kubectl apply -f payment-pod-delete.yaml

# Check experiment status
kubectl get chaosengine payment-pod-delete -n production

# Check experiment results
kubectl get chaosresult payment-pod-delete-pod-delete -n production -o yaml
```

</details>

## 高级问题

### 1. 为一家金融服务公司设计一个架构，以实现 EKS cluster 99.99% 可用性。提供一项综合策略，使用 Multi-AZ、Cell-Based Architecture、PDB 和 Chaos Engineering。

<details>
<summary>查看答案</summary>

**实现 99.99% 可用性的综合架构：**

**1. Multi-Region + Multi-AZ 配置：**
```yaml
# Primary Region (us-west-2)
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: finance-primary
  region: us-west-2
nodeGroups:
  - name: ng-critical
    instanceType: m5.xlarge
    desiredCapacity: 9
    availabilityZones: ["us-west-2a", "us-west-2b", "us-west-2c"]
    labels:
      criticality: high
```

**2. Cell-Based Architecture 实现：**
```yaml
# Cell-level isolation
apiVersion: v1
kind: Namespace
metadata:
  name: cell-us-1
  labels:
    cell: us-1
    region: us-west-2
---
# Cell-specific resource quotas
apiVersion: v1
kind: ResourceQuota
metadata:
  name: cell-quota
  namespace: cell-us-1
spec:
  hard:
    requests.cpu: "100"
    requests.memory: 200Gi
    limits.cpu: "200"
    limits.memory: 400Gi
```

**3. 强 PDB 策略：**
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: critical-service-pdb
spec:
  minAvailable: 80%  # Always 80%+ available
  selector:
    matchLabels:
      tier: critical
```

**4. Topology Spread + Anti-Affinity：**
```yaml
spec:
  topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
  - maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: ScheduleAnyway
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app: payment-api
        topologyKey: kubernetes.io/hostname
```

**5. Chaos Engineering 计划：**
```yaml
# Periodic Chaos experiments (GameDay)
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosSchedule
metadata:
  name: weekly-resilience-test
spec:
  schedule:
    type: repeat
    repeat:
      timeRange:
        startTime: "2024-01-01T02:00:00Z"
        endTime: "2024-12-31T04:00:00Z"
      workDays:
        includedDays: "Sun"
  engineSpec:
    experiments:
    - name: pod-delete
    - name: node-drain
    - name: network-loss
```

**6. 监控和自动恢复：**
```yaml
# HPA + Auto-recovery
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: critical-service-hpa
spec:
  minReplicas: 6
  maxReplicas: 30
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
```

**SLA 计算：**
- 99.99% = 每年约 52 分钟停机时间
- Multi-AZ：处理单个 AZ 故障
- Multi-Region：处理 Region 级故障
- Cell 隔离：限制 blast radius
- 自动恢复：最小化 MTTR

</details>

### 2. 为一个准备迎接 Black Friday 流量激增（10x）的大型电商平台制定 EKS 弹性策略。包括预扩容、Chaos Engineering 验证和故障场景响应计划。

<details>
<summary>查看答案</summary>

**Black Friday 流量激增准备策略：**

**1. 预扩容容量规划：**
```yaml
# Karpenter Provisioner - Surge Configuration
apiVersion: karpenter.sh/v1alpha5
kind: Provisioner
metadata:
  name: blackfriday
spec:
  requirements:
  - key: node.kubernetes.io/instance-type
    operator: In
    values: ["m5.2xlarge", "m5.4xlarge", "c5.2xlarge", "c5.4xlarge"]
  - key: topology.kubernetes.io/zone
    operator: In
    values: ["us-west-2a", "us-west-2b", "us-west-2c"]
  limits:
    resources:
      cpu: 2000
      memory: 4000Gi
  ttlSecondsAfterEmpty: 30
---
# HPA Pre-scaling
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: product-catalog-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: product-catalog
  minReplicas: 50  # Normal 10 -> Black Friday 50
  maxReplicas: 500
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60  # Conservative 60%
```

**2. 流量前 Chaos Engineering 验证：**
```yaml
# Load Test + Chaos Combination
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: blackfriday-prep-test
spec:
  experiments:
  # Scenario 1: 10x traffic + 30% Pod failure
  - name: pod-delete
    spec:
      components:
        env:
        - name: PODS_AFFECTED_PERC
          value: "30"
        - name: TOTAL_CHAOS_DURATION
          value: "300"
  # Scenario 2: 10x traffic + AZ failure
  - name: node-drain
    spec:
      components:
        env:
        - name: TARGET_NODE_LABEL
          value: "topology.kubernetes.io/zone=us-west-2a"
  # Scenario 3: 10x traffic + DB latency
  - name: pod-network-latency
    spec:
      components:
        env:
        - name: TARGET_PODS
          value: "app=mysql"
        - name: NETWORK_LATENCY
          value: "500"
```

**3. 故障场景响应计划：**

| Scenario | Detection | Auto Response | Manual Response |
|---------|------|----------|----------|
| AZ Failure | CloudWatch Alarm | 通过 Topology Spread 自动分布 | Route53 Failover |
| DB Latency | 延迟告警 | Circuit Breaker 激活 | 切换到 Read Replica |
| Memory Exhaustion | OOM 告警 | HPA Scale-out | 添加 Nodes |
| Traffic Spike | TPS 告警 | Rate Limiting | 扩展 CDN Cache |

**4. Circuit Breaker 模式：**
```yaml
# Istio DestinationRule - Circuit Breaker
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: product-catalog-cb
spec:
  host: product-catalog
  trafficPolicy:
    connectionPool:
      http:
        h2UpgradePolicy: UPGRADE
        http1MaxPendingRequests: 1000
        http2MaxRequests: 2000
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

**5. 实时监控 Dashboard：**
```promql
# Grafana Dashboard Queries
# 1. Total TPS
sum(rate(http_requests_total[1m]))

# 2. Error Rate
sum(rate(http_requests_total{status=~"5.."}[1m])) / sum(rate(http_requests_total[1m])) * 100

# 3. P99 Response Time
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[1m])) by (le))

# 4. Pod Availability Rate
sum(kube_pod_status_ready{condition="true"}) / sum(kube_pod_status_ready) * 100
```

**6. Rollback 计划：**
```bash
#!/bin/bash
# Emergency Rollback Script
NAMESPACE="production"
DEPLOYMENT="product-catalog"

# 1. Rollback to previous version
kubectl rollout undo deployment/$DEPLOYMENT -n $NAMESPACE

# 2. Pause HPA
kubectl patch hpa $DEPLOYMENT-hpa -n $NAMESPACE -p '{"spec":{"minReplicas":100}}'

# 3. Disable Feature Flags
curl -X POST "https://feature-flags.internal/api/v1/flags/blackfriday-features/disable"

# 4. Extend CDN Cache
aws cloudfront update-distribution --id $CF_DIST_ID --default-cache-behavior "DefaultTTL=86400"
```

**测试日程：**
- D-14：基础 Chaos 测试
- D-7：完整场景 GameDay
- D-3：最终验证和预扩容
- D-Day：实时监控和响应

</details>
