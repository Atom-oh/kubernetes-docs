# EKS Resiliency and High Availability

> **サポート対象バージョン**: EKS 1.28+, Istio 1.20+, Karpenter 1.0+ **最終更新**: February 23, 2026

## Resiliency Overview

Resiliency（レジリエンシー）とは、障害発生時の影響を最小化しながら通常状態へ復旧する、または service を維持する能力です。これは単純な high availability (HA) を超えるものであり、障害を予測して備える design philosophy を表します。

### Resiliency Maturity Model

| Level | Name         | Scope             | Key Technologies                     | RTO Target        |
| ----- | ------------ | ----------------- | ------------------------------------ | ----------------- |
| 1     | Basic        | Pod               | Probes, Resource Limits, PDB         | Minutes           |
| 2     | Multi-AZ     | Availability Zone | Topology Spread, ARC Zonal Shift     | Seconds           |
| 3     | Cell-Based   | Service Unit      | Shuffle Sharding, Cell Router        | Seconds (partial) |
| 4     | Multi-Region | Region            | Global Accelerator, Data Replication | Near Zero         |

> すべての services に Level 4 が必要なわけではありません。SLA requirements、regulations、budget に基づいて適切な Level を選択してください。

***

## Level 1: Basic Resiliency (Pod Level)

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

PDB は voluntary disruptions 中の最小 availability を保証します。

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

### Graceful Shutdown

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

> `preStop` で5秒待機する理由: endpoint removal の伝播前に Pod が終了すると、traffic loss が発生します。この sleep により伝播時間を確保します。

***

## Level 2: Multi-AZ Strategy

### Pod Topology Spread Constraints

Pods を availability zones 全体に均等に分散します。

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

| Parameter           | Description                                           |
| ------------------- | ----------------------------------------------------- |
| `maxSkew`           | topology domains 間の Pod 数の最大差                 |
| `topologyKey`       | 分散の基準 (zone, hostname など)                     |
| `whenUnsatisfiable` | `DoNotSchedule` (Hard) または `ScheduleAnyway` (Soft) |
| `minDomains`        | domains の最小数 (3 AZs の場合は 3)                  |

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

AWS Application Recovery Controller (ARC) Zonal Shift は、障害が発生している AZ から traffic を自動的にリダイレクトします。

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

### Storage Considerations

**EBS AZ Lock-in Issues の防止:**

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

**EFS による Cross-AZ Access:**

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

同じ AZ 内の traffic を優先すると、cross-AZ transfer costs を 60-80% 削減できます。

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

## Level 3: Cell-Based Architecture

### Cell Concept

Cell は **独自の data store、cache、queue を持つ self-contained service unit** です。障害の blast radius を特定の Cell に分離します。

### Cell Partitioning Strategies

| Strategy       | Description                          | Suitable For                        |
| -------------- | ------------------------------------ | ----------------------------------- |
| Customer-based | customer ID hash によって Cell を割り当て | SaaS multi-tenant                   |
| Region-based   | geographic location によって partition | Global services                     |
| Capacity-based | capacity に達したら新しい Cell を作成 | 均等な load distribution            |
| Tier-based     | service tier による Cell             | Premium/Standard differentiation    |

### Namespace-based Cell Implementation

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

各 customer をランダムに選択された Cells の組み合わせに割り当てることで、単一 Cell 障害の影響を受ける customers を最小化します。

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

組み合わせの数: C(8,2) = 28 となり、2人の customers が同じ組み合わせを共有する確率は非常に低くなります。

***

## Level 4: Multi-Cluster / Multi-Region

### Architecture Pattern Comparison

| Pattern            | RTO        | RPO     | Cost                   | Complexity |
| ------------------ | ---------- | ------- | ---------------------- | ---------- |
| Active-Active      | \~0        | \~0     | 2x+                    | 非常に高い |
| Active-Passive     | Min\~Hours | Minutes | 1.5x                   | 高い       |
| Regional Isolation | N/A        | N/A     | region ごとに 1x       | 中         |
| Hub-Spoke          | Minutes    | Minutes | 1.3x                   | 中         |

### Multi-Cluster Deployment with ArgoCD ApplicationSet

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

### Global Accelerator Integration

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

Chaos Engineering は **system weaknesses を proactive に発見するため、production environments で意図的に障害を注入する methodology** です。

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

| Phase                  | Activity                         | Deliverable            |
| ---------------------- | -------------------------------- | ---------------------- |
| 1. Record Steady State | metric baselines を収集          | Dashboard snapshot     |
| 2. Inject Failure      | FIS/Litmus experiments を実行    | Experiment logs        |
| 3. Observe Recovery    | automatic recovery process を監視 | recovery time measurement |
| 4. Analyze Impact      | error rate、latency changes を分析 | Impact report          |
| 5. Post-mortem Review  | improvements、Action Items を特定 | Improvement plan       |

***

## Implementation Checklist

### Level 1 Basic

* [ ] すべての containers に Liveness/Readiness Probe を設定する
* [ ] Resource requests/limits を設定する
* [ ] PodDisruptionBudget を構成する
* [ ] Graceful shutdown (preStop hook) を実装する
* [ ] 適切な terminationGracePeriodSeconds を設定する

### Level 2 Multi-AZ

* [ ] Pod Topology Spread Constraints を適用する
* [ ] Karpenter NodePool で 3 AZ distribution を構成する
* [ ] StorageClass で `WaitForFirstConsumer` を設定する
* [ ] ARC Zonal Shift を有効化する
* [ ] Cross-AZ traffic costs を監視する

### Level 3 Cell-Based

* [ ] Cell boundaries (Namespace または Cluster) を定義する
* [ ] Cell Router を実装する
* [ ] NetworkPolicy で Cells を分離する
* [ ] Shuffle Sharding を実装する
* [ ] Cell ごとに ResourceQuota を設定する

### Level 4 Multi-Region

* [ ] Multi-Region architecture pattern を決定する
* [ ] Global Accelerator を構成する
* [ ] ArgoCD ApplicationSet で multi-cluster を deploy する
* [ ] data replication strategy を確立する
* [ ] GitOps との consistency を維持する

***

## Cost Considerations

| Item                       | Cost Impact                       | Cost Reduction Strategy                      |
| -------------------------- | --------------------------------- | -------------------------------------------- |
| Multi-Region Active-Active | single region と比較して 2x+      | Active-Passive で Passive を 50-70% 削減     |
| Cross-AZ Traffic           | $0.01/GB (同一 region 内)         | Locality-aware routing で 60-80% 削減        |
| Spot Instance              | On-Demand と比較して 60-90% savings | stateless workloads に適用                   |
| Chaos Engineering          | FIS experiment costs              | failure prevention による ROI                |

***

## Next Steps

* [EKS Advanced Debugging and Incident Response](11-eks-advanced-debugging.md)
* [EKS High Availability Quiz](../quizzes/eks/10-eks-resiliency-quiz.md)
* [Istio Service Mesh](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/service-mesh/02-istio.md) - Circuit Breaker, Retry Deep Dive
