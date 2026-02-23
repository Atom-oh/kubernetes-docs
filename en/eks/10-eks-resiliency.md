# EKS High Availability and Resiliency Architecture

> **Supported Versions**: EKS 1.28+, Istio 1.20+, Karpenter 1.0+
> **Last Updated**: February 23, 2026

## Resiliency Overview

Resiliency is **the ability to minimize impact during failures while recovering to a normal state or maintaining service**. It goes beyond simple high availability (HA) and represents a design philosophy that anticipates and prepares for failures.

### Resiliency Maturity Model

| Level | Name | Scope | Key Technologies | RTO Target |
|-------|------|-------|-----------------|------------|
| 1 | Basic | Pod | Probes, Resource Limits, PDB | Minutes |
| 2 | Multi-AZ | Availability Zone | Topology Spread, ARC Zonal Shift | Seconds |
| 3 | Cell-Based | Service Unit | Shuffle Sharding, Cell Router | Seconds (partial) |
| 4 | Multi-Region | Region | Global Accelerator, Data Replication | Near Zero |

> Not all services require Level 4. Choose the appropriate level based on SLA requirements, regulations, and budget.

---

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

PDB ensures minimum availability during voluntary disruptions.

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

> The reason for waiting 5 seconds in `preStop`: If the Pod terminates before endpoint removal propagates, traffic loss occurs. The sleep ensures propagation time.

---

## Level 2: Multi-AZ Strategy

### Pod Topology Spread Constraints

Distribute Pods evenly across availability zones.

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

| Parameter | Description |
|-----------|-------------|
| `maxSkew` | Maximum difference in Pod count between topology domains |
| `topologyKey` | Distribution basis (zone, hostname, etc.) |
| `whenUnsatisfiable` | `DoNotSchedule` (Hard) or `ScheduleAnyway` (Soft) |
| `minDomains` | Minimum number of domains (3 for 3 AZs) |

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

AWS Application Recovery Controller (ARC) Zonal Shift automatically redirects traffic away from a failing AZ.

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

**Preventing EBS AZ Lock-in Issues:**

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

**Cross-AZ Access with EFS:**

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

Prioritizing traffic within the same AZ reduces cross-AZ transfer costs by 60-80%.

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

---

## Level 3: Cell-Based Architecture

### Cell Concept

A Cell is **a self-contained service unit with its own data store, cache, and queue**. It isolates the blast radius of failures to a specific Cell.

### Cell Partitioning Strategies

| Strategy | Description | Suitable For |
|----------|-------------|--------------|
| Customer-based | Assign Cell by customer ID hash | SaaS multi-tenant |
| Region-based | Partition by geographic location | Global services |
| Capacity-based | New Cell when capacity is reached | Even load distribution |
| Tier-based | Cell by service tier | Premium/Standard differentiation |

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

Assigning each customer to a randomly selected combination of Cells minimizes the customers affected by a single Cell failure.

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

Number of combinations: C(8,2) = 28, making the probability of two customers sharing the same combination very low.

---

## Level 4: Multi-Cluster / Multi-Region

### Architecture Pattern Comparison

| Pattern | RTO | RPO | Cost | Complexity |
|---------|-----|-----|------|------------|
| Active-Active | ~0 | ~0 | 2x+ | Very High |
| Active-Passive | Min~Hours | Minutes | 1.5x | High |
| Regional Isolation | N/A | N/A | 1x per region | Medium |
| Hub-Spoke | Minutes | Minutes | 1.3x | Medium |

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

---

## Chaos Engineering

Chaos Engineering is **a methodology for intentionally injecting failures in production environments to discover system weaknesses proactively**.

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

| Phase | Activity | Deliverable |
|-------|----------|-------------|
| 1. Record Steady State | Collect metric baselines | Dashboard snapshot |
| 2. Inject Failure | Run FIS/Litmus experiments | Experiment logs |
| 3. Observe Recovery | Monitor automatic recovery process | Recovery time measurement |
| 4. Analyze Impact | Analyze error rate, latency changes | Impact report |
| 5. Post-mortem Review | Identify improvements, Action Items | Improvement plan |

---

## Implementation Checklist

### Level 1 Basic
- [ ] Set Liveness/Readiness Probe for all containers
- [ ] Set Resource requests/limits
- [ ] Configure PodDisruptionBudget
- [ ] Implement Graceful shutdown (preStop hook)
- [ ] Set appropriate terminationGracePeriodSeconds

### Level 2 Multi-AZ
- [ ] Apply Pod Topology Spread Constraints
- [ ] Configure 3 AZ distribution in Karpenter NodePool
- [ ] Set `WaitForFirstConsumer` in StorageClass
- [ ] Enable ARC Zonal Shift
- [ ] Monitor Cross-AZ traffic costs

### Level 3 Cell-Based
- [ ] Define Cell boundaries (Namespace or Cluster)
- [ ] Implement Cell Router
- [ ] Isolate Cells with NetworkPolicy
- [ ] Implement Shuffle Sharding
- [ ] Set ResourceQuota per Cell

### Level 4 Multi-Region
- [ ] Decide on Multi-Region architecture pattern
- [ ] Configure Global Accelerator
- [ ] Deploy multi-cluster with ArgoCD ApplicationSet
- [ ] Establish data replication strategy
- [ ] Maintain consistency with GitOps

---

## Cost Considerations

| Item | Cost Impact | Cost Reduction Strategy |
|------|-------------|------------------------|
| Multi-Region Active-Active | 2x+ compared to single region | Reduce Passive by 50-70% with Active-Passive |
| Cross-AZ Traffic | $0.01/GB (within same region) | Reduce 60-80% with Locality-aware routing |
| Spot Instance | 60-90% savings compared to On-Demand | Apply to stateless workloads |
| Chaos Engineering | FIS experiment costs | ROI through failure prevention |

---

## Next Steps

- [EKS Advanced Debugging and Incident Response](./11-eks-advanced-debugging.md)
- [EKS High Availability Quiz](../quizzes/eks/10-eks-resiliency-quiz.md)
- [Istio Service Mesh](../service-mesh/02-istio.md) - Circuit Breaker, Retry Deep Dive
