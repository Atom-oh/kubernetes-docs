# Amazon EKS 高可用性とレジリエンシークイズ

このクイズでは、Amazon EKS cluster の高可用性 (HA)、レジリエンシー、Multi-AZ deployment、Cell-Based Architecture、Chaos Engineering、PodDisruptionBudget、Topology Spread Constraints に関する理解を確認します。

## クイズ概要
- Multi-AZ Architecture と Configuration
- Cell-Based Architecture Patterns
- Chaos Engineering の原則とツール
- PodDisruptionBudget (PDB) Configuration
- Topology Spread Constraints
- Disaster Recovery と Failover

## 選択問題

### 1. Amazon EKS における Multi-AZ deployment の主な利点は何ですか？

A. コスト削減
B. 単一 AZ 障害時でもアプリケーションの可用性を維持する
C. ネットワークレイテンシーの増加
D. 管理の複雑さの軽減

<details>
<summary>回答を見る</summary>

**回答: B. 単一 AZ 障害時でもアプリケーションの可用性を維持する**

**解説:**
Multi-AZ deployment の主な利点は、単一の Availability Zone (AZ) に障害が発生しても、workloads が他の AZ で実行を継続でき、アプリケーションの可用性を維持できることです。

**Multi-AZ Deployment の主な利点:**
- 単一 AZ 障害時の自動 failover
- Datacenter レベルの fault tolerance
- 99.99% 以上の可用性を達成できる能力
- 強化されたリージョンの disaster recovery 機能

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

### 2. PodDisruptionBudget (PDB) の主な目的は何ですか？

A. Pod の CPU 使用量を制限する
B. 自発的な disruption 中に利用可能な Pods の最小数を確保する
C. Pods 間のネットワークトラフィックを制御する
D. Pod のメモリ使用量を監視する

<details>
<summary>回答を見る</summary>

**回答: B. 自発的な disruption 中に利用可能な Pods の最小数を確保する**

**解説:**
PodDisruptionBudget (PDB) は、node draining、cluster upgrades、autoscaling events などの自発的な disruption 中に、最小数の Pods が稼働し続けることを保証します。

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

**PDB の主な機能:**
- `minAvailable`: 利用可能な状態を維持する必要がある Pods の最小数
- `maxUnavailable`: 同時に利用不可にできる Pods の最大数
- rolling updates と node maintenance 中の service continuity を確保する

</details>

### 3. Topology Spread Constraints における `whenUnsatisfiable: DoNotSchedule` は何を意味しますか？

A. constraints を満たせない場合、任意の node に Pod を schedule する
B. constraints を満たせない場合、Pod scheduling を拒否する
C. constraints を無視して常に schedule する
D. constraints に違反した場合、既存の Pods を削除する

<details>
<summary>回答を見る</summary>

**回答: B. constraints を満たせない場合、Pod scheduling を拒否する**

**解説:**
`whenUnsatisfiable: DoNotSchedule` は、topology spread constraints を満たせない場合に Pod scheduling を拒否します。これは厳格な分散ポリシーを強制する場合に使用されます。

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

**whenUnsatisfiable のオプション:**
- `DoNotSchedule`: constraints が満たされない場合、scheduling を拒否する (Hard constraint)
- `ScheduleAnyway`: constraints を満たすよう best effort で試み、不可能な場合は任意の場所に schedule する (Soft constraint)

</details>

### 4. Cell-Based Architecture における「Cell」の主な特徴ではないものはどれですか？

A. 独立して deploy および scale できる
B. 障害がシステム全体に伝播する
C. 自己完結型の機能単位
D. 他の Cells と loosely coupled である

<details>
<summary>回答を見る</summary>

**回答: B. 障害がシステム全体に伝播する**

**解説:**
Cell-Based Architecture の中核的な目的は failure isolation です。各 Cell は独立して動作するため、1 つの Cell の障害が他の Cells に伝播しません。

**Cell-Based Architecture の中核原則:**
1. **Failure Isolation**: 1 つの Cell の障害が他に影響しない
2. **Independent Deployment**: 各 Cell を個別に更新できる
3. **Horizontal Scaling**: Cell レベルで capacity を scale する
4. **Self-Containment**: 各 Cell が必要なすべての components を含む

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

### 5. Chaos Engineering における「Steady State Hypothesis」は何を意味しますか？

A. システムを常に停止状態に保つこと
B. 実験の前後に通常のシステム動作を検証するための測定可能な baseline
C. chaos experiments を停止するための条件
D. システムの最大 load state

<details>
<summary>回答を見る</summary>

**回答: B. 実験の前後に通常のシステム動作を検証するための測定可能な baseline**

**解説:**
Steady State Hypothesis は、システムの「通常」状態に対する測定可能な metrics を定義します。chaos experiment の前にこの仮説が真であることを確認し、実験後にシステムがこの状態に戻ることを確認します。

**Steady State Metrics の例:**
- Response time < 200ms (p99)
- Error rate < 0.1%
- Throughput > 1000 req/s
- Pod availability > 99%

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

### 6. EKS で Zone-Aware Routing を実装するために使用される Service annotation はどれですか？

A. `service.kubernetes.io/topology-aware-hints: auto`
B. `service.kubernetes.io/zone-routing: enabled`
C. `service.kubernetes.io/local-only: true`
D. `service.kubernetes.io/cross-zone: disabled`

<details>
<summary>回答を見る</summary>

**回答: A. `service.kubernetes.io/topology-aware-hints: auto`**

**解説:**
Kubernetes 1.23+ で導入された Topology Aware Hints により、kube-proxy は同じ Zone 内の endpoints へ優先的に traffic を route でき、cross-AZ traffic costs と latency を削減できます。

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

**Zone-Aware Routing の利点:**
- cross-AZ data transfer costs の削減
- ネットワーク latency の低減
- traffic を同じ Zone 内に保つことによる reliability の向上

</details>

### 7. PDB で `maxUnavailable: 25%`、replicas が 8 の場合、同時に disruption 可能な Pods の最大数はいくつですか？

A. 1
B. 2
C. 3
D. 4

<details>
<summary>回答を見る</summary>

**回答: B. 2**

**解説:**
`maxUnavailable: 25%` は、総 replicas の最大 25% までを同時に disruption できることを意味します。8 の 25% は 2 です (8 × 0.25 = 2)。

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

**計算方法:**
- percentages は切り捨てられる
- replicas = 8, maxUnavailable = 25%
- 8 × 0.25 = 2 (小数は切り捨て)
- したがって、最小 6 Pods は常に running のままである必要がある

</details>

### 8. Litmus Chaos が提供していない experiment type はどれですか？

A. pod-delete
B. node-drain
C. network-loss
D. cluster-delete

<details>
<summary>回答を見る</summary>

**回答: D. cluster-delete**

**解説:**
Litmus Chaos は cluster 全体を削除する experiment を提供していません。Chaos Engineering の目的は、制御された環境でシステムの resilience をテストすることであり、infrastructure 全体を破壊することではありません。

**主な Litmus Chaos Experiment Types:**
- **Pod Level**: pod-delete, pod-cpu-hog, pod-memory-hog, pod-network-loss
- **Node Level**: node-drain, node-cpu-hog, node-memory-hog, node-taint
- **Network Level**: network-loss, network-latency, network-corruption
- **AWS Specific**: ec2-terminate, ebs-loss, az-chaos

```bash
# Litmus Chaos Installation
kubectl apply -f https://litmuschaos.github.io/litmus/litmus-operator-v2.14.0.yaml
```

</details>

### 9. EKS Control Plane の高可用性はどのように保証されますか？

A. Users が Multi-AZ を手動で configure する必要がある
B. AWS が複数 AZ にわたって自動的に管理する
C. 単一 AZ のみで実行される
D. 手動の failover configuration が必要

<details>
<summary>回答を見る</summary>

**回答: B. AWS が複数 AZ にわたって自動的に管理する**

**解説:**
Amazon EKS Control Plane は AWS によって完全に managed され、複数の Availability Zones にわたり高可用性を備えて自動的に deploy されます。etcd data も複数 AZ に replicated されます。

**EKS Control Plane HA の機能:**
- 自動 Multi-AZ deployment (最小 2 AZs)
- 自動 API server scaling
- 自動 etcd data replication と backup
- 自動 failure detection と recovery
- 99.95% SLA guarantee

**User Responsibility:**
- Data plane (node) Multi-AZ configuration
- Workload Pod distribution
- PDB と Topology Spread settings

</details>

### 10. Topology Spread Constraints における `maxSkew` は何を意味しますか？

A. Pods の最大数
B. topology domains 間の Pod 数の最大許容差
C. nodes の最小数
D. node あたりの最大 Pods 数

<details>
<summary>回答を見る</summary>

**回答: B. topology domains 間の Pod 数の最大許容差**

**解説:**
`maxSkew` は、異なる topology domains (例: AZs、nodes) 間の Pod 数の最大許容差です。たとえば `maxSkew: 1` の場合、任意の 2 つの domains 間の Pod 数の差は 1 を超えることができません。

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

**maxSkew の例 (replicas=6, 3 AZs):**
- maxSkew=1: Zone-A(2), Zone-B(2), Zone-C(2) - 均等分散
- maxSkew=2: Zone-A(3), Zone-B(2), Zone-C(1) - 許可
- maxSkew=1 violation: Zone-A(4), Zone-B(1), Zone-C(1) - Scheduling rejected

</details>

## 短答問題

### 1. EKS で cross-AZ data transfer costs を削減するために使用される Service annotation は何ですか？

<details>
<summary>回答を見る</summary>

**回答:** `service.kubernetes.io/topology-aware-hints: auto`

**解説:**
この annotation を Service に追加すると、Kubernetes Topology Aware Hints が有効になり、traffic が同じ AZ 内の endpoints に優先的に route されます。

```yaml
apiVersion: v1
kind: Service
metadata:
  annotations:
    service.kubernetes.io/topology-aware-hints: auto
```

</details>

### 2. PodDisruptionBudget における「Voluntary Disruption」の例を 3 つ挙げてください。

<details>
<summary>回答を見る</summary>

**回答:**
1. Node drain (kubectl drain)
2. Cluster upgrade
3. Cluster Autoscaler による Node scale-down

**追加の例:**
- Deployment/StatefulSet の rolling updates
- 手動の Pod deletion (kubectl delete pod)
- maintenance のための Node cordon/drain

**Involuntary Disruption の例:**
- Hardware failure
- Kernel panic
- VM deletion
- OOM Kill

</details>

### 3. Chaos Engineering の 4 つの中核原則を挙げてください。

<details>
<summary>回答を見る</summary>

**回答:**
1. **Build a Steady State Hypothesis**: 通常状態の測定可能な metrics を定義する
2. **Vary Real-World Events**: 実世界の failure scenarios を simulate する
3. **Run Experiments in Production**: 可能な場合は実環境で test する
4. **Minimize Blast Radius**: experiment impact を制限し、自動 abort conditions を設定する

**追加の原則:**
- continuous verification のために experiments を自動化する
- results を分析し、system を改善する

</details>

### 4. Multi-AZ 用に EKS node groups を configure する際に推奨される AZs の最小数はいくつですか？

<details>
<summary>回答を見る</summary>

**回答:** 3

**解説:**
nodes を 3 つ以上の AZs に分散すると、次の利点があります:
- 単一 AZ 障害時に 2/3 の capacity が維持される
- quorum-based systems (例: etcd) の stability
- より均等な workload distribution

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

### 5. Cell-Based Architecture では、traffic は特定の Cell にどのように route されますか？

<details>
<summary>回答を見る</summary>

**回答:** routing layer (例: API Gateway, Service Mesh, Load Balancer) が user/tenant ID に基づいて traffic を特定の Cells に分散します。

**実装方法:**
1. **Hash-based routing**: user ID を hash して Cell を決定する
2. **Explicit mapping**: user-to-Cell mapping table を維持する
3. **Region-based**: geographic location に基づいて Cell を割り当てる

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

## ハンズオン演習

### 1. 次の要件を満たす PodDisruptionBudget YAML を書いてください:
- Name: api-server-pdb
- Target: label `app: api-server` を持つ Pods
- 最小 3 Pods は常に running のままである必要がある

<details>
<summary>回答を見る</summary>

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

**検証コマンド:**
```bash
# Create PDB
kubectl apply -f api-server-pdb.yaml

# Check PDB status
kubectl get pdb api-server-pdb

# View detailed information
kubectl describe pdb api-server-pdb
```

**期待される出力:**
```
NAME              MIN AVAILABLE   MAX UNAVAILABLE   ALLOWED DISRUPTIONS   AGE
api-server-pdb    3               N/A               2                     10s
```

</details>

### 2. 3 AZs にわたって Pods を均等に分散する Topology Spread Constraints を持つ Deployment を書いてください。
- Deployment name: web-frontend
- replicas: 6
- maxSkew: 1
- Distribution key: topology.kubernetes.io/zone

<details>
<summary>回答を見る</summary>

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

**検証コマンド:**
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

**期待される出力:**
```
2 us-west-2a
2 us-west-2b
2 us-west-2c
```

</details>

### 3. Litmus Chaos を使用して特定の Pods を削除する Chaos experiment を定義してください。
- Target: namespace `production` 内の label `app: payment-service` を持つ Pods
- Experiment duration: 30 seconds
- Number of Pods to delete: 1

<details>
<summary>回答を見る</summary>

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

**前提条件:**
```bash
# Install Litmus Chaos Operator
kubectl apply -f https://litmuschaos.github.io/litmus/litmus-operator-v2.14.0.yaml

# Install ChaosExperiment CRD
kubectl apply -f https://hub.litmuschaos.io/api/chaos/2.14.0?file=charts/generic/pod-delete/experiment.yaml

# Create ServiceAccount
kubectl apply -f https://hub.litmuschaos.io/api/chaos/2.14.0?file=charts/generic/pod-delete/rbac.yaml -n production
```

**検証コマンド:**
```bash
# Run Chaos experiment
kubectl apply -f payment-pod-delete.yaml

# Check experiment status
kubectl get chaosengine payment-pod-delete -n production

# Check experiment results
kubectl get chaosresult payment-pod-delete-pod-delete -n production -o yaml
```

</details>

## 応用問題

### 1. 金融サービス企業の EKS cluster で 99.99% availability を実現する architecture を設計してください。Multi-AZ、Cell-Based Architecture、PDB、Chaos Engineering を活用した包括的な strategy を提示してください。

<details>
<summary>回答を見る</summary>

**99.99% Availability のための包括的 Architecture:**

**1. Multi-Region + Multi-AZ Configuration:**
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

**2. Cell-Based Architecture Implementation:**
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

**3. 強力な PDB Policies:**
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

**4. Topology Spread + Anti-Affinity:**
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

**5. Chaos Engineering Program:**
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

**6. Monitoring and Auto-Recovery:**
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

**SLA Calculation:**
- 99.99% = 年間約 52 分の downtime
- Multi-AZ: 単一 AZ 障害に対応
- Multi-Region: region-level failures に対応
- Cell isolation: blast radius を制限
- Auto-recovery: MTTR を最小化

</details>

### 2. Black Friday の traffic surge (10x) に備える大規模 e-commerce platform 向けの EKS resiliency strategy を策定してください。pre-scaling、Chaos Engineering validation、failure scenario response plans を含めてください。

<details>
<summary>回答を見る</summary>

**Black Friday Traffic Surge 準備 Strategy:**

**1. Pre-scaling Capacity Planning:**
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

**2. Pre-Traffic Chaos Engineering Validation:**
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

**3. Failure Scenario Response Plans:**

| Scenario | Detection | Auto Response | Manual Response |
|---------|------|----------|----------|
| AZ Failure | CloudWatch Alarm | Auto-distribution via Topology Spread | Route53 Failover |
| DB Latency | Latency Alert | Circuit Breaker activation | Switch to Read Replica |
| Memory Exhaustion | OOM Alert | HPA Scale-out | Add Nodes |
| Traffic Spike | TPS Alert | Rate Limiting | Expand CDN Cache |

**4. Circuit Breaker Pattern:**
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

**5. Real-time Monitoring Dashboard:**
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

**6. Rollback Plan:**
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

**Test Schedule:**
- D-14: Basic Chaos tests
- D-7: Full scenario GameDay
- D-3: Final verification and Pre-scaling
- D-Day: Real-time monitoring and response

</details>
