# Amazon EKS High Availability and Resiliency Quiz

This quiz tests your understanding of Amazon EKS cluster high availability (HA), resiliency, Multi-AZ deployment, Cell-Based Architecture, Chaos Engineering, PodDisruptionBudget, and Topology Spread Constraints.

## Quiz Overview
- Multi-AZ Architecture and Configuration
- Cell-Based Architecture Patterns
- Chaos Engineering Principles and Tools
- PodDisruptionBudget (PDB) Configuration
- Topology Spread Constraints
- Disaster Recovery and Failover

## Multiple Choice Questions

### 1. What is the primary benefit of Multi-AZ deployment in Amazon EKS?

A. Cost reduction
B. Maintaining application availability even during single AZ failure
C. Increased network latency
D. Reduced management complexity

<details>
<summary>View Answer</summary>

**Answer: B. Maintaining application availability even during single AZ failure**

**Explanation:**
The key benefit of Multi-AZ deployment is that even if a single Availability Zone (AZ) fails, workloads can continue running in other AZs, maintaining application availability.

**Key Benefits of Multi-AZ Deployment:**
- Automatic failover during single AZ failure
- Datacenter-level fault tolerance
- Ability to achieve 99.99%+ availability
- Enhanced regional disaster recovery capability

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

### 2. What is the primary purpose of PodDisruptionBudget (PDB)?

A. Limit Pod CPU usage
B. Ensure minimum available Pods during voluntary disruptions
C. Control network traffic between Pods
D. Monitor Pod memory usage

<details>
<summary>View Answer</summary>

**Answer: B. Ensure minimum available Pods during voluntary disruptions**

**Explanation:**
PodDisruptionBudget (PDB) ensures that a minimum number of Pods remain running during voluntary disruptions such as node draining, cluster upgrades, and autoscaling events.

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

**Key PDB Features:**
- `minAvailable`: Minimum number of Pods that must remain available
- `maxUnavailable`: Maximum number of Pods that can be unavailable simultaneously
- Ensures service continuity during rolling updates and node maintenance

</details>

### 3. What does `whenUnsatisfiable: DoNotSchedule` mean in Topology Spread Constraints?

A. Schedule Pod on any node if constraints cannot be satisfied
B. Reject Pod scheduling if constraints cannot be satisfied
C. Ignore constraints and always schedule
D. Delete existing Pods when constraints are violated

<details>
<summary>View Answer</summary>

**Answer: B. Reject Pod scheduling if constraints cannot be satisfied**

**Explanation:**
`whenUnsatisfiable: DoNotSchedule` rejects Pod scheduling if the topology spread constraints cannot be satisfied. This is used when enforcing strict distribution policies.

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

**whenUnsatisfiable Options:**
- `DoNotSchedule`: Reject scheduling if constraints not met (Hard constraint)
- `ScheduleAnyway`: Best effort to satisfy constraints, schedule anywhere if not possible (Soft constraint)

</details>

### 4. Which is NOT a key characteristic of a "Cell" in Cell-Based Architecture?

A. Can be deployed and scaled independently
B. Failures propagate to the entire system
C. Self-contained functional unit
D. Loosely coupled with other Cells

<details>
<summary>View Answer</summary>

**Answer: B. Failures propagate to the entire system**

**Explanation:**
The core purpose of Cell-Based Architecture is failure isolation. Each Cell operates independently so that a failure in one Cell does not propagate to other Cells.

**Core Principles of Cell-Based Architecture:**
1. **Failure Isolation**: Failure in one Cell doesn't affect others
2. **Independent Deployment**: Each Cell can be updated individually
3. **Horizontal Scaling**: Scale capacity at the Cell level
4. **Self-Containment**: Each Cell contains all necessary components

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

### 5. What does "Steady State Hypothesis" mean in Chaos Engineering?

A. Keeping the system always in a stopped state
B. A measurable baseline to verify normal system behavior before and after experiments
C. Conditions for stopping chaos experiments
D. Maximum load state of the system

<details>
<summary>View Answer</summary>

**Answer: B. A measurable baseline to verify normal system behavior before and after experiments**

**Explanation:**
Steady State Hypothesis defines measurable metrics for the system's "normal" state. Before a chaos experiment, verify that this hypothesis is true, and after the experiment, verify that the system returns to this state.

**Steady State Metrics Examples:**
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

### 6. What Service annotation is used to implement Zone-Aware Routing in EKS?

A. `service.kubernetes.io/topology-aware-hints: auto`
B. `service.kubernetes.io/zone-routing: enabled`
C. `service.kubernetes.io/local-only: true`
D. `service.kubernetes.io/cross-zone: disabled`

<details>
<summary>View Answer</summary>

**Answer: A. `service.kubernetes.io/topology-aware-hints: auto`**

**Explanation:**
Topology Aware Hints, introduced in Kubernetes 1.23+, allows kube-proxy to preferentially route traffic to endpoints in the same Zone, reducing cross-AZ traffic costs and latency.

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

**Benefits of Zone-Aware Routing:**
- Reduced cross-AZ data transfer costs
- Lower network latency
- Improved reliability by keeping traffic within the same Zone

</details>

### 7. With `maxUnavailable: 25%` in a PDB and 8 replicas, what is the maximum number of Pods that can be disrupted simultaneously?

A. 1
B. 2
C. 3
D. 4

<details>
<summary>View Answer</summary>

**Answer: B. 2**

**Explanation:**
`maxUnavailable: 25%` means up to 25% of total replicas can be disrupted simultaneously. 25% of 8 is 2 (8 × 0.25 = 2).

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

**Calculation Method:**
- Percentages are rounded down
- replicas = 8, maxUnavailable = 25%
- 8 × 0.25 = 2 (decimal truncated)
- Therefore, minimum 6 Pods must always remain running

</details>

### 8. Which is NOT an experiment type provided by Litmus Chaos?

A. pod-delete
B. node-drain
C. network-loss
D. cluster-delete

<details>
<summary>View Answer</summary>

**Answer: D. cluster-delete**

**Explanation:**
Litmus Chaos does not provide an experiment to delete an entire cluster. The purpose of Chaos Engineering is to test system resilience in controlled environments, not to destroy entire infrastructure.

**Main Litmus Chaos Experiment Types:**
- **Pod Level**: pod-delete, pod-cpu-hog, pod-memory-hog, pod-network-loss
- **Node Level**: node-drain, node-cpu-hog, node-memory-hog, node-taint
- **Network Level**: network-loss, network-latency, network-corruption
- **AWS Specific**: ec2-terminate, ebs-loss, az-chaos

```bash
# Litmus Chaos Installation
kubectl apply -f https://litmuschaos.github.io/litmus/litmus-operator-v2.14.0.yaml
```

</details>

### 9. How is EKS Control Plane high availability guaranteed?

A. Users must configure Multi-AZ manually
B. AWS automatically manages it across multiple AZs
C. It runs in a single AZ only
D. Manual failover configuration required

<details>
<summary>View Answer</summary>

**Answer: B. AWS automatically manages it across multiple AZs**

**Explanation:**
Amazon EKS Control Plane is fully managed by AWS and automatically deployed with high availability across multiple Availability Zones. etcd data is also replicated across multiple AZs.

**EKS Control Plane HA Features:**
- Automatic Multi-AZ deployment (minimum 2 AZs)
- Automatic API server scaling
- Automatic etcd data replication and backup
- Automatic failure detection and recovery
- 99.95% SLA guarantee

**User Responsibility:**
- Data plane (node) Multi-AZ configuration
- Workload Pod distribution
- PDB and Topology Spread settings

</details>

### 10. What does `maxSkew` mean in Topology Spread Constraints?

A. Maximum number of Pods
B. Maximum allowed difference in Pod count between topology domains
C. Minimum number of nodes
D. Maximum Pods per node

<details>
<summary>View Answer</summary>

**Answer: B. Maximum allowed difference in Pod count between topology domains**

**Explanation:**
`maxSkew` is the maximum allowed difference in Pod count between different topology domains (e.g., AZs, nodes). For example, with `maxSkew: 1`, the Pod count difference between any two domains cannot exceed 1.

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

**maxSkew Examples (replicas=6, 3 AZs):**
- maxSkew=1: Zone-A(2), Zone-B(2), Zone-C(2) - Even distribution
- maxSkew=2: Zone-A(3), Zone-B(2), Zone-C(1) - Allowed
- maxSkew=1 violation: Zone-A(4), Zone-B(1), Zone-C(1) - Scheduling rejected

</details>

## Short Answer Questions

### 1. What Service annotation is used to reduce cross-AZ data transfer costs in EKS?

<details>
<summary>View Answer</summary>

**Answer:** `service.kubernetes.io/topology-aware-hints: auto`

**Explanation:**
Adding this annotation to a Service enables Kubernetes Topology Aware Hints, which preferentially routes traffic to endpoints within the same AZ.

```yaml
apiVersion: v1
kind: Service
metadata:
  annotations:
    service.kubernetes.io/topology-aware-hints: auto
```

</details>

### 2. List 3 examples of "Voluntary Disruption" in PodDisruptionBudget.

<details>
<summary>View Answer</summary>

**Answer:**
1. Node drain (kubectl drain)
2. Cluster upgrade
3. Node scale-down by Cluster Autoscaler

**Additional examples:**
- Rolling updates of Deployment/StatefulSet
- Manual Pod deletion (kubectl delete pod)
- Node cordon/drain for maintenance

**Involuntary Disruption examples:**
- Hardware failure
- Kernel panic
- VM deletion
- OOM Kill

</details>

### 3. List the 4 core principles of Chaos Engineering.

<details>
<summary>View Answer</summary>

**Answer:**
1. **Build a Steady State Hypothesis**: Define measurable metrics for normal state
2. **Vary Real-World Events**: Simulate real-world failure scenarios
3. **Run Experiments in Production**: Test in real environments when possible
4. **Minimize Blast Radius**: Limit experiment impact and set automatic abort conditions

**Additional principles:**
- Automate experiments for continuous verification
- Analyze results and improve the system

</details>

### 4. What is the minimum recommended number of AZs when configuring EKS node groups for Multi-AZ?

<details>
<summary>View Answer</summary>

**Answer:** 3

**Explanation:**
Distributing nodes across 3 or more AZs provides:
- 2/3 capacity maintained during single AZ failure
- Stability for quorum-based systems (e.g., etcd)
- More even workload distribution

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

### 5. How is traffic routed to a specific Cell in Cell-Based Architecture?

<details>
<summary>View Answer</summary>

**Answer:** The routing layer (e.g., API Gateway, Service Mesh, Load Balancer) distributes traffic to specific Cells based on user/tenant ID.

**Implementation Methods:**
1. **Hash-based routing**: Hash user ID to determine Cell
2. **Explicit mapping**: Maintain user-to-Cell mapping table
3. **Region-based**: Assign Cell based on geographic location

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

## Hands-on Exercises

### 1. Write a PodDisruptionBudget YAML that satisfies the following requirements:
- Name: api-server-pdb
- Target: Pods with label `app: api-server`
- Minimum 3 Pods must always remain running

<details>
<summary>View Answer</summary>

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

**Verification Commands:**
```bash
# Create PDB
kubectl apply -f api-server-pdb.yaml

# Check PDB status
kubectl get pdb api-server-pdb

# View detailed information
kubectl describe pdb api-server-pdb
```

**Expected Output:**
```
NAME              MIN AVAILABLE   MAX UNAVAILABLE   ALLOWED DISRUPTIONS   AGE
api-server-pdb    3               N/A               2                     10s
```

</details>

### 2. Write a Deployment with Topology Spread Constraints to evenly distribute Pods across 3 AZs.
- Deployment name: web-frontend
- replicas: 6
- maxSkew: 1
- Distribution key: topology.kubernetes.io/zone

<details>
<summary>View Answer</summary>

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

**Verification Commands:**
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

**Expected Output:**
```
2 us-west-2a
2 us-west-2b
2 us-west-2c
```

</details>

### 3. Define a Chaos experiment using Litmus Chaos to delete specific Pods.
- Target: Pods in namespace `production` with label `app: payment-service`
- Experiment duration: 30 seconds
- Number of Pods to delete: 1

<details>
<summary>View Answer</summary>

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

**Prerequisites:**
```bash
# Install Litmus Chaos Operator
kubectl apply -f https://litmuschaos.github.io/litmus/litmus-operator-v2.14.0.yaml

# Install ChaosExperiment CRD
kubectl apply -f https://hub.litmuschaos.io/api/chaos/2.14.0?file=charts/generic/pod-delete/experiment.yaml

# Create ServiceAccount
kubectl apply -f https://hub.litmuschaos.io/api/chaos/2.14.0?file=charts/generic/pod-delete/rbac.yaml -n production
```

**Verification Commands:**
```bash
# Run Chaos experiment
kubectl apply -f payment-pod-delete.yaml

# Check experiment status
kubectl get chaosengine payment-pod-delete -n production

# Check experiment results
kubectl get chaosresult payment-pod-delete-pod-delete -n production -o yaml
```

</details>

## Advanced Questions

### 1. Design an architecture to achieve 99.99% availability for an EKS cluster at a financial services company. Provide a comprehensive strategy utilizing Multi-AZ, Cell-Based Architecture, PDB, and Chaos Engineering.

<details>
<summary>View Answer</summary>

**Comprehensive Architecture for 99.99% Availability:**

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

**3. Strong PDB Policies:**
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
- 99.99% = approximately 52 minutes downtime per year
- Multi-AZ: Handles single AZ failures
- Multi-Region: Handles region-level failures
- Cell isolation: Limits blast radius
- Auto-recovery: Minimizes MTTR

</details>

### 2. Develop an EKS resiliency strategy for a large e-commerce platform preparing for Black Friday traffic surge (10x). Include pre-scaling, Chaos Engineering validation, and failure scenario response plans.

<details>
<summary>View Answer</summary>

**Black Friday Traffic Surge Preparation Strategy:**

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
