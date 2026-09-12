# Amazon EKS High Availability and Resiliency Quiz

> **Example API baseline**: Kubernetes 1.36; official source/quiz assumptions match the [source chapter](../../eks/10-eks-resiliency.md).
> **Last Updated**: September 12, 2026

Configuration and numerical examples are illustrative. No cloud resources, chaos experiments, workloads or benchmarks were run in this audit. Use an owned test scope and replace placeholders before deployment.

This quiz tests your understanding of Amazon EKS cluster high availability (HA), resiliency, Multi-AZ deployment, Cell-Based Architecture, Chaos Engineering, PodDisruptionBudget, and Topology Spread Constraints.

## Quiz Overview
- Multi-AZ Architecture and Configuration
- Cell-Based Architecture Patterns
- Chaos Engineering Principles and Tools
- PodDisruptionBudget (PDB) Configuration
- Topology Spread Constraints
- Disaster Recovery and Failover

## Multiple Choice Questions

### 1. What is the primary resilience benefit of Multi-AZ EKS workloads?

A. Automatic cost reduction
B. A design that can continue service after one AZ fails, if capacity/data/routing are prepared
C. Higher latency as a goal
D. Removal of operational complexity

<details>
<summary>View Answer</summary>

**Answer: B. A design that can continue service after one AZ fails, if capacity/data/routing are prepared**

Multi-AZ improves the failure-domain design but does not promise automatic workload/data failover or 99.99% availability. It does not address loss of the whole region. Six evenly distributed equal-capacity nodes across three AZs leave four after one AZ is lost; actual Pod placement and capacity must be inspected. The following is a provisioning input example, not an executed command. Version 1.36 is the chapter baseline: verify current regional EKS/AMI support before creation.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: owned-ha-example
  region: us-west-2
  version: '1.36'
managedNodeGroups:
- name: ng-multi-az
  instanceType: m5.large
  desiredCapacity: 6
  availabilityZones:
  - us-west-2a
  - us-west-2b
  - us-west-2c
```

</details>

### 2. What does a PodDisruptionBudget constrain?

A. Pod CPU usage
B. Supported voluntary evictions according to workload availability
C. All Pod-to-Pod traffic
D. Every cause of Pod termination

<details>
<summary>View Answer</summary>

**Answer: B. Supported voluntary evictions according to workload availability**

PDB admission constrains the Eviction API, as used by cooperating drain/maintenance/autoscaling operations. It does not protect direct Pod deletion, Deployment rolling updates/scale-down, or involuntary failures. Choose one of minAvailable or maxUnavailable; labels must match the intended controller workload. This example is an alternative to the percentage PDB below, not an overlapping policy to apply alongside it.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
  namespace: resilience-demo
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web-app
```

</details>

### 3. What does whenUnsatisfiable: DoNotSchedule do?

A. Schedules anywhere despite this constraint
B. Keeps a new Pod unscheduled when no eligible node satisfies the spread constraint
C. Ignores all scheduling constraints
D. Deletes existing Pods to restore balance

<details>
<summary>View Answer</summary>

**Answer: B. Keeps a new Pod unscheduled when no eligible node satisfies the spread constraint**

This is a scheduling filter, not rejection of the Pod object by the API server. ScheduleAnyway makes only this spread rule a preference; resources, affinity, taints and storage constraints still apply. The complete Deployment below uses a placeholder image and application-specific health paths; replace them before applying. minDomains=2 permits an N-1 calculation when two eligible zones remain, but does not force initial occupation of three AZs or create capacity.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: resilience-demo
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
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-app
```

</details>

### 4. Which is not a goal of a cell-based architecture?

A. Independent deployment/scaling
B. Propagating a cell failure across the whole system
C. A self-contained functional unit
D. Bounded coupling with other cells

<details>
<summary>View Answer</summary>

**Answer: B. Propagating a cell failure across the whole system**

Isolation is a design property to implement and test, not a guarantee created by Namespace labels. Separate routing/admission limits, capacity and data dependencies; account for shared nodes, control plane, DNS and routers. The two namespaces below express grouping only. Quota and NetworkPolicy require additional enforcement and do not create physical failure domains.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cell-a
  labels:
    cell: a
```
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cell-b
  labels:
    cell: b
```

</details>

### 5. What is a steady-state hypothesis in chaos engineering?

A. Keeping the service stopped
B. A measurable hypothesis about acceptable behavior before, during and after a fault
C. Only the command that stops an experiment
D. The maximum possible load

<details>
<summary>View Answer</summary>

**Answer: B. A measurable hypothesis about acceptable behavior before, during and after a fault**

Define user-visible metrics, windows, missing-data behavior and abort thresholds before the experiment. The original p99<200ms, errors<0.1%, throughput>1000req/s and Ready Pods>99% are illustrative thresholds, not observations. Ready Pod percentage is not request availability. Litmus ChaosExperiment.spec.definition.steadyState is not a field in the reviewed operator CRD. The following JSON is a human review plan, not a Kubernetes resource.

```json
{
  "scenario": "one bounded test fault",
  "hypothesis": {
    "p99_latency_seconds": "<0.2",
    "error_percentage": "<0.1",
    "request_rate_per_second": ">1000",
    "ready_pod_percentage": ">99"
  },
  "required_observations": [
    "baseline",
    "during fault",
    "recovery",
    "missing data"
  ],
  "abort": "Set an independent measured threshold and recovery owner before execution"
}
```

</details>

### 6. Which Service field expresses same-zone preference in the Kubernetes 1.36 baseline?

A. spec.trafficDistribution: PreferSameZone
B. spec.zoneRouting: enabled
C. spec.localOnly: true
D. spec.crossZone: disabled

<details>
<summary>View Answer</summary>

**Answer: A. spec.trafficDistribution: PreferSameZone**

PreferSameZone/PreferSameNode are GA from 1.35. They express preferences, not strict isolation or guaranteed savings. PreferClose is the older alias. The older topology-mode=Auto annotation follows a separate hint heuristic; topology-aware-hints is legacy guidance. Review proxy implementation, EndpointSlices and Local traffic-policy precedence.

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

</details>

### 7. With eight healthy replicas, no ongoing disruption and maxUnavailable: 25%, what is the nominal eviction allowance?

A. 1
B. 2
C. 3
D. 4

<details>
<summary>View Answer</summary>

**Answer: B. 2**

ceil(8×0.25)=2. Both PDB percentage forms round UP, not down: three replicas with 25% maxUnavailable give ceil(0.75)=1, while 75% minAvailable requires ceil(2.25)=3 healthy Pods. Unhealthy Pods and ongoing disruptions consume the budget; this is not a guarantee that six Pods always run through every failure.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb-percentage
  namespace: resilience-demo
spec:
  selector:
    matchLabels:
      app: web-app
  maxUnavailable: 25%
```

</details>

### 8. Which claim is incorrect for the reviewed Litmus operator/catalog?

A. pod-delete is a catalog fault
B. node-drain is distinct from instance termination
C. pod-network-loss is a catalog fault
D. cluster-delete is a standard fault that removes an entire EKS cluster

<details>
<summary>View Answer</summary>

**Answer: D. cluster-delete is a standard fault that removes an entire EKS cluster**

The reviewed catalog contains these exact pod/node fault names, not the claimed cluster-delete fault. Generic names such as network-loss or ec2-terminate must not be assumed valid IDs. The current AWS catalog includes aws-az-chaos, ebs-loss-by-id/by-tag and ec2-stop-by-id/by-tag. Review the actual fault definition, required RBAC and runner image. Installing an operator alone does not install every experiment; the 3.31.0 operator does not define ChaosHub or ChaosSchedule.


</details>

### 9. Who manages regional EKS control-plane availability?

A. Users manually place the API servers
B. AWS manages the regional control plane across three AZs
C. It is always a single-AZ control plane
D. Users must implement etcd failover for managed EKS

<details>
<summary>View Answer</summary>

**Answer: B. AWS manages the regional control plane across three AZs**

Regional EKS spreads its managed control plane across three AZs; the customer subnet requirement of at least two AZs is different. Standard Control Plane has a 99.95% monthly endpoint SLA and Provisioned Control Plane 99.99%, with service-credit conditions and different measurement intervals. These do not guarantee application availability or provide a customer-managed workload/PV backup. Customers still own workload/data-plane placement, data recovery and SLO measurement.


</details>

### 10. With DoNotSchedule, what does maxSkew constrain when placing a Pod?

A. Maximum total Pods
B. The candidate domain count compared with the global minimum
C. Minimum node count
D. Maximum Pods per node

<details>
<summary>View Answer</summary>

**Answer: B. The candidate domain count compared with the global minimum**

Eligible domains and minDomains determine the global minimum; when fewer eligible domains than minDomains remain, the minimum is zero. Counts 2/2 across two eligible zones can block replacements with minDomains=3 and maxSkew=1. A 2/2/2 distribution is one healthy example, not a permanent invariant; 3/2/1 fits a skew-2 illustration, while placing further Pods into a 4/1/1 imbalance can fail. Existing Pods are not automatically rebalanced or deleted.


</details>

## Short Answer Questions

### 1. Which field should a Kubernetes 1.36 Service use for same-zone preference?

<details>
<summary>View Answer</summary>

spec.trafficDistribution: PreferSameZone. This is a preference; measure routing and cost. The legacy topology-aware-hints annotation is not the current answer. Review Local traffic policies and the implementation actually serving this Service.

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

</details>

### 2. Give three operations that can use PDB-aware voluntary eviction, and distinguish bypasses.

<details>
<summary>View Answer</summary>

Examples: kubectl drain using Eviction, an upgrade workflow that drains through Eviction, and a cooperating node autoscaler scale-down. Verify the specific implementation and force options. Deployment/StatefulSet rollouts, direct kubectl delete pod and some cloud desired-capacity changes do not use PDB admission in the same way. Cordon alone prevents new scheduling and does not evict existing Pods. Hardware failure, kernel panic and OOM cannot be prevented by PDB.


</details>

### 3. Describe four controls for a useful chaos experiment.

<details>
<summary>View Answer</summary>

Define a measurable steady-state hypothesis; choose a realistic bounded fault; use a representative environment with explicit production authorization if production is necessary; minimize blast radius with independent observation, stop thresholds and a recovery owner. Automation and post-experiment analysis improve repeatability, but neither makes production testing mandatory or restores data automatically.


</details>

### 4. Why use three AZs for this workload example, and is that an EKS node-group minimum?

<details>
<summary>View Answer</summary>

Three equally provisioned zones leave two-thirds of pre-existing capacity after losing one zone, if workloads and dependencies are also distributed. This is a design choice, not a universal node-group API minimum. EKS cluster subnets require at least two AZs; its regional managed control plane spans three. Customer node-group AZs do not determine placement of EKS-managed etcd. Choose zones available for the region, instance types, storage and workload constraints.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: owned-ha-example
  region: us-west-2
  version: '1.36'
managedNodeGroups:
- name: ng-multi-az
  instanceType: m5.large
  desiredCapacity: 6
  availabilityZones:
  - us-west-2a
  - us-west-2b
  - us-west-2c
```

</details>

### 5. How should a routing layer assign traffic to a cell?

<details>
<summary>View Answer</summary>

Use a trusted tenant identity and stable hash, explicit mapping or regional assignment. The router must validate authorization, capacity and data placement; do not trust an arbitrary client x-cell-id as tenant authorization. The mesh example assumes registered destination Services and compatible policies. Unknown/untrusted cell IDs need an explicit rejection/default policy. Two namespaces or a routing ConfigMap alone do not implement isolation or failover.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: cell-routing-example
  namespace: resilience-demo
spec:
  hosts:
  - cell-router.resilience-demo.svc.cluster.local
  http:
  - match:
    - headers:
        x-cell-id:
          exact: cell-a
    route:
    - destination:
        host: app.cell-a.svc.cluster.local
  - match:
    - headers:
        x-cell-id:
          exact: cell-b
    route:
    - destination:
        host: app.cell-b.svc.cluster.local
```

</details>

## Hands-on Exercises

### 1. Write api-server-pdb for app=api-server so PDB-aware evictions require three available replicas.

<details>
<summary>View Answer</summary>

This is your application label, not the AWS-managed Kubernetes API server. The namespace and matching controller workload must already exist. Five Ready replicas with no ongoing disruption would illustrate an allowance of two; three replicas give no healthy-eviction allowance. Inspect actual status rather than assuming the earlier sample output was observed.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-server-pdb
  namespace: resilience-demo
spec:
  minAvailable: 3
  selector:
    matchLabels:
      app: api-server
```
```bash
# Prerequisite: the owned test namespace and matching application already exist.
: "${KUBE_CONTEXT:?Set the owned test context}"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pods -l app=api-server
# MUTATION: apply only this reviewed PDB file.
kubectl --context "$KUBE_CONTEXT" -n resilience-demo apply -f api-server-pdb.yaml
kubectl --context "$KUBE_CONTEXT" -n resilience-demo describe pdb api-server-pdb
```

</details>

### 2. Write web-frontend with six replicas and a zone spread rule; explain the AZ-loss trade-off.

<details>
<summary>View Answer</summary>

The full example uses maxSkew=1 and minDomains=2 for the N-1 scenario. Initial three-zone placement and surviving-zone capacity must be verified separately. It does not automatically rebalance or move zonal PVCs. Replace the application placeholder image/health paths; resources are examples. After a controlled apply, use the Python report below instead of assuming every Pod has a node name/zone label.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
  namespace: resilience-demo
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
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-frontend
```
```bash
# MUTATION: replace the image/health contract and review this exact file first.
: "${KUBE_CONTEXT:?Set the owned test context}"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo apply -f web-frontend.yaml
kubectl --context "$KUBE_CONTEXT" -n resilience-demo rollout status deployment/web-frontend --timeout=5m
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pods -l app=web-frontend -o json > frontend-pods.json
kubectl --context "$KUBE_CONTEXT" get nodes -o json > frontend-nodes.json
```
```python
import collections, json
from pathlib import Path
pods = json.loads(Path("frontend-pods.json").read_text())["items"]
nodes = json.loads(Path("frontend-nodes.json").read_text())["items"]
zones = {n["metadata"]["name"]: n["metadata"].get("labels", {}).get("topology.kubernetes.io/zone", "<unlabeled>") for n in nodes}
counts, ready = collections.Counter(), collections.Counter()
for pod in pods:
    if pod["metadata"].get("deletionTimestamp"):
        continue
    node = pod.get("spec", {}).get("nodeName")
    zone = zones.get(node, "<unknown-node>") if node else "<unscheduled>"
    counts[zone] += 1
    if any(c.get("type") == "Ready" and c.get("status") == "True" for c in pod.get("status", {}).get("conditions", [])):
        ready[zone] += 1
print(json.dumps({"activePodsByZone": dict(counts), "readyPodsByZone": dict(ready)}, indent=2))
```

</details>

### 3. Prepare a stopped 30-second Litmus Pod-deletion experiment scoped to one reviewed test Pod.

<details>
<summary>View Answer</summary>

Use an owned payment-service test workload in resilience-demo, not a broad production selector. Replace TARGET_PODS with an exact current name after checking its UID/owner. The operator, pod-delete ChaosExperiment, verified runner/helper images and scoped RBAC must already be reviewed. Duration/interval can lead to repeated deletion attempts; this is not a proof of exactly one delete over 30 seconds. If the requirement is one selected deletion action, use the chapter’s FIS COUNT(1) example with its separate IAM/RBAC prerequisites. No fault is executed here.

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: payment-pod-delete-review
  namespace: resilience-demo
spec:
  engineState: stop
  appinfo:
    appns: resilience-demo
    applabel: app=payment-service,experiment-approved=true
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
```bash
# Read-only: resolve an exact current Pod name/UID before filling TARGET_PODS.
: "${KUBE_CONTEXT:?Set the owned test context}"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pods \
  -l 'app=payment-service,experiment-approved=true' -o wide
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get chaosexperiment pod-delete
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get serviceaccount pod-delete-sa
# MUTATION: this reviewed file must still have engineState: stop.
kubectl --context "$KUBE_CONTEXT" -n resilience-demo apply -f payment-pod-delete-review.yaml
```
```bash
# Read-only observation; no experiment is started by these commands.
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get chaosengine payment-pod-delete-review -o yaml
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get chaosresult
```

</details>

## Advanced Questions

### 1. Design a financial-service workload for a 99.99% availability SLO; identify what must be proved.

<details>
<summary>View Answer</summary>

A 99.99% target is a workload SLO, not a guarantee produced by the following resources. For a 365-day time-based window, the arithmetic budget is 52.56 minutes/year (the earlier “about 52 minutes” approximation); EKS SLA is a separate monthly service-credit commitment. Request-based availability uses a different denominator. Define each critical user journey, partial failures, measurement window, RTO/RPO and alerting.

Prepare primary/secondary regions with independently usable data, identity, DNS, routing, observability and capacity. Test replication lag, write promotion/conflicts and recovery ownership; neither Multi-AZ nor Active-Active alone guarantees zero data loss. The following original-scale resource values remain design illustrations, not measured capacity or an executed deployment.

#### Multi-AZ node input and cell resources

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: finance-primary-example
  region: us-west-2
  version: '1.36'
managedNodeGroups:
- name: ng-critical
  instanceType: m5.xlarge
  desiredCapacity: 9
  availabilityZones:
  - us-west-2a
  - us-west-2b
  - us-west-2c
  labels:
    criticality: high
```
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: finance-cell
  labels:
    cell: finance
```
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: cell-quota
  namespace: finance-cell
spec:
  hard:
    requests.cpu: '100'
    requests.memory: 200Gi
    limits.cpu: '200'
    limits.memory: 400Gi
```
The quota does not reserve nodes or isolate shared dependencies. Add the chapter’s reviewed router/network-policy/data boundaries. For the strict hostname anti-affinity below, nine replicas require nine eligible nodes with criticality=high; scaling to 30 needs corresponding node capacity. Strict placement can intentionally leave Pods Pending. Replace the placeholder image/health contract and confirm the chosen region/version/instance availability first.

#### Placement and eviction budget

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-api
  namespace: finance-cell
spec:
  replicas: 9
  selector:
    matchLabels:
      app: payment-api
  template:
    metadata:
      labels:
        app: payment-api
        tier: critical
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
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: payment-api
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: payment-api
      nodeSelector:
        criticality: high
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: payment-api
            topologyKey: kubernetes.io/hostname
```
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: critical-service-pdb
  namespace: finance-cell
spec:
  minAvailable: 80%
  selector:
    matchLabels:
      app: payment-api
```
With nine healthy replicas, minAvailable: 80% rounds up to eight; one healthy eviction is the nominal allowance before other deductions. It does not constrain every rollout, cloud scale-down or AZ failure. minDomains=2 supports the described N-1 placement calculation, not automatic evacuation or data migration.

#### HPA with an actual target and metric contract

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: critical-service-hpa
  namespace: finance-cell
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: payment-api
  minReplicas: 9
  maxReplicas: 30
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
```
The CPU resource metric needs working Metrics Server and CPU requests on the relevant containers. Raising replicas cannot repair a leak, exhausted database or zonal volume constraint. Keep the replica field/GitOps/HPA ownership consistent.

For regular game days, use an owned scheduler or approved workflow that invokes reviewed individual experiments, records its exact target/ID, watches abort signals and verifies restoration before the next fault. The old 2024 ChaosSchedule snippet was both expired and not a CRD in Litmus 3.31.0; merely changing its dates would not fix it. A 99.99% claim requires actual SLI evidence and exercises, not just a weekly schedule.

</details>

### 2. Plan for a 10× Black Friday traffic scenario, including pre-scaling and bounded failure recovery.

<details>
<summary>View Answer</summary>

10× is a test target, not a measured result. Model request mix, CPU/memory, warm-up, connections, queues, database and external-service quotas. Budget for the loss of an AZ while carrying the target traffic. NodePool limits are provisioning ceilings, **not pre-created or reserved capacity**. The existing EC2NodeClass, AMIs/IAM, subnets/IPs and selected instance types must support this design. A zero voluntary disruption budget does not block interruptions, repairs or every forced termination.

#### Capacity settings to validate

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: blackfriday-example
spec:
  template:
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: reviewed-test-class
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - m5.2xlarge
        - m5.4xlarge
        - c5.2xlarge
        - c5.4xlarge
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - us-west-2a
        - us-west-2b
        - us-west-2c
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
  limits:
    cpu: 2000
    memory: 4000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
    budgets:
    - nodes: '0'
```
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: product-catalog-hpa
  namespace: resilience-demo
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: product-catalog
  minReplicas: 50
  maxReplicas: 500
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
  behavior:
    scaleDown:
      selectPolicy: Disabled
```
The original normal 10→minimum 50/max 500 values are illustrative: five times the replica floor does not prove ten times the throughput. This HPA assumes an existing product-catalog Deployment with CPU requests and working metrics. Disabling scaleDown prevents HPA scale-in while scaling up remains allowed; it is not a total HPA pause. Verify Ready Pods, healthy endpoints and already available node/headroom before the event, then restore the reviewed normal policy afterwards.

Before the event, run the chapter’s separately reviewed experiments under representative test load: one bounded Pod fault, a controlled zonal shift/network scenario, and dependency latency. Do not label node-drain as an entire AZ outage, pass a label selector as TARGET_PODS, or combine unreviewed faults in one active production engine. Capture results including failure/no-data and actual restoration.

#### Scenario response plan

| Scenario | Evidence | Reviewed response |
| --- | --- | --- |
| AZ impairment | Endpoint/customer health, node state, data availability | Eligible ARC/manual shift and proven surviving capacity; topology spread alone does not evacuate Pods |
| Database latency | Query/connection/replication metrics | Bound retries/concurrency; follow writer promotion/runbook if necessary, not a blind switch to any read replica |
| OOM/memory growth | Limit, working set, restart and application evidence | Diagnose/correct resource or application behavior; CPU HPA is not an automatic OOM repair |
| Traffic surge | Request mix, backlog, saturation, customer errors | Admission/rate limits and tested scaling; cache only data with safe public/personalization semantics |

#### Circuit breaker and metrics

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: product-catalog-circuit-breaker
  namespace: resilience-demo
spec:
  host: product-catalog.resilience-demo.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 3s
      http:
        http1MaxPendingRequests: 1000
        http2MaxRequests: 2000
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
Proxy pool limits and outlier detection do not reserve backend capacity. Tune with the source chapter’s timeout/idempotency rules. The queries below require **your application instrumentation** exposing the named counter/classic-histogram metrics and the job/namespace/status labels, plus kube-state-metrics. Initialize relevant status series and verify scrape coverage; these metrics are not supplied automatically by EKS. A zero request denominator/no samples is unavailable evidence, not 100% success. The Pod indicator deliberately excludes completed/deleting Pods and is not the application SLI.

Request rate

```promql
sum(rate(http_requests_total{job="product-catalog",namespace="resilience-demo"}[5m]))
```

5xx percentage

```promql
100 * sum(rate(http_requests_total{job="product-catalog",namespace="resilience-demo",status=~"5.."}[5m]))
/ sum(rate(http_requests_total{job="product-catalog",namespace="resilience-demo"}[5m]))
and on() (sum(rate(http_requests_total{job="product-catalog",namespace="resilience-demo"}[5m])) > 0)
```

Classic-histogram p99 seconds

```promql
histogram_quantile(0.99,
  sum by (le) (rate(http_request_duration_seconds_bucket{job="product-catalog",namespace="resilience-demo"}[5m]))
)
```

Active test-namespace Ready Pod percentage, not request availability

```promql
100 *
sum(
  kube_pod_status_ready{namespace="resilience-demo",condition="true"}
  and on (namespace,pod)
  (kube_pod_status_phase{namespace="resilience-demo",phase=~"Pending|Running|Unknown"} == 1)
  unless on (namespace,pod) kube_pod_deletion_timestamp{namespace="resilience-demo"}
)
/
count(
  (kube_pod_status_phase{namespace="resilience-demo",phase=~"Pending|Running|Unknown"} == 1)
  unless on (namespace,pod) kube_pod_deletion_timestamp{namespace="resilience-demo"}
)
```

#### Workload rollback and separately reviewed controls

```bash
# MUTATION: workload revision rollback only, after data/schema and GitOps review.
set -euo pipefail
: "${KUBE_CONTEXT:?Set the verified owned context}"
: "${REVIEWED_REVISION:?Set an inspected compatible Deployment revision}"
[[ "$REVIEWED_REVISION" =~ ^[1-9][0-9]*$ ]]
kubectl --context "$KUBE_CONTEXT" -n resilience-demo rollout history deployment/product-catalog
kubectl --context "$KUBE_CONTEXT" -n resilience-demo rollout undo deployment/product-catalog \
  --to-revision="$REVIEWED_REVISION"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo rollout status deployment/product-catalog --timeout=5m
```
Coordinate GitOps and HPA ownership before rollback; rollout undo is not a database/PVC rollback or an EKS control-plane downgrade. Raising minReplicas to 100 does not pause HPA. Use the HPA behavior policy and a recorded restore plan when needed. Feature flags require your real authenticated management API/SDK and an audited target flag; no generic unauthenticated disable URL is assumed.

For CloudFront, first retrieve the existing full configuration and ETag into a private file:

```bash
# Read-only preparation; output can include sensitive origin configuration.
set -euo pipefail
umask 077
: "${CF_DIST_ID:?Set the exact owned CloudFront distribution ID}"
test ! -e cloudfront-current-private.json
aws cloudfront get-distribution-config --id "$CF_DIST_ID" > cloudfront-current-private.json
```
Review cache policy, cookies, authorization and personalized content. A change requires the complete valid DistributionConfig and matching IfMatch ETag; update-distribution has no --default-cache-behavior shortcut. Prepare and review the full configuration separately, wait for deployment and keep a restoration plan. Do not apply a blanket 24-hour TTL to transactional/user-specific responses.

The original D-14 basic tests, D-7 game day, D-3 final verification/pre-scaling and D-Day monitoring schedule remains a planning illustration; all runtime results are unverified here.

[CloudFront update API](https://docs.aws.amazon.com/cli/latest/reference/cloudfront/update-distribution.html) · [HPA behavior](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/) · [kube-state-metrics Pod metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/pod-metrics.md)

</details>
