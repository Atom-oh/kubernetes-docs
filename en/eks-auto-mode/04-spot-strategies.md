# Spot Instance Utilization Strategies

> **Supported Versions**: EKS Auto Mode GA; example baseline EKS 1.36
> **Last Updated**: September 12, 2026

Spot trades interruption and capacity uncertainty for potentially lower EC2 prices. Mixed capacity, diversification and replicas can improve resilience, but none alone guarantees availability or savings. Use the reviewed account/context and NodeClass from the preceding chapters.

The manifests are lab examples checked locally against schemas, not a production failover test. They use a `spot-lab` taint/toleration and explicit pool selection to reduce accidental placement of unrelated workloads. Taints are not a tenant-security boundary. Review the replica counts and resource limits before applying; these examples can create billed nodes. No Spot instances were provisioned, and no customer billing or EC2 Spot Price History API query was executed during this audit.

## Mixed Capacity and a Deliberate Baseline

The pool below permits both Spot and On-Demand. Within one eligible pool Auto Mode prioritizes allowed capacity types; Spot is preferred over On-Demand when both are allowed and available. If `reserved` is also allowed and a suitable reservation exists, it has higher priority. Array order and NodePool weight do not set a Spot percentage.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: spot-lab
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: mixed-capacity
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
        - r
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '5'
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: spot-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        capacity-example: spot-lab
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spot-friendly-app
  namespace: spot-lab
spec:
  replicas: 10
  selector:
    matchLabels:
      app: spot-friendly
  template:
    metadata:
      labels:
        app: spot-friendly
    spec:
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: karpenter.sh/capacity-type
                operator: In
                values:
                - spot
      containers:
      - name: app
        image: nginx:1.30.4
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        ports:
        - containerPort: 80
        readinessProbe:
          httpGet:
            path: /
            port: 80
          periodSeconds: 5
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: mixed-capacity
      tolerations:
      - key: spot-lab
        operator: Equal
        value: 'true'
        effect: NoSchedule
```

The Pod's preferred affinity is a preference, not a requirement or a reservation. It does not promise instantaneous On-Demand fallback, a fixed ratio, or replacement within an interruption window. Existing capacity, constraints, quotas and actual availability still matter.

For a separate baseline Deployment that must use On-Demand, replace the Pod template's Spot preference with a hard selection such as the following, retaining the lab toleration. Keep an appropriate number of baseline replicas running; allowing On-Demand in a pool does not itself keep spare capacity warm.

```yaml
nodeSelector:
  karpenter.sh/nodepool: mixed-capacity
  karpenter.sh/capacity-type: on-demand
tolerations:
- key: spot-lab
  operator: Equal
  value: 'true'
  effect: NoSchedule
```

This selector intentionally requires `on-demand`; it does not include `reserved` capacity. Review labels and reservation configuration if you later use capacity reservations. On-Demand is not a data-durability or capacity-availability guarantee.

## Diversify Compatible Capacity

A Spot capacity pool is tied to an instance type and AZ. More compatible types/AZs give the allocator more choices; they do not make interruptions independent or double capacity merely because two architectures are listed.

The example permits generation 5 and newer instead of freezing the upper bound at 7. Confirm image, binary, storage and performance compatibility before broadening constraints.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: diversified-spot
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
        - r
        - i
        - d
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '4'
      - key: eks.amazonaws.com/instance-size
        operator: In
        values:
        - large
        - xlarge
        - 2xlarge
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: spot-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        capacity-example: spot-lab
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
  limits:
    cpu: '100'
    memory: 400Gi
```

`consolidationPolicy` and `consolidateAfter` control consolidation, not the time taken to react to an EC2 interruption. Multiple architectures require matching multi-architecture images and dependencies. More generations or sizes are useful only if they remain suitable for the workload and are available in the selected AZs.

## Separate Voluntary Budgets from EC2 Interruptions

Auto Mode provides native Spot interruption handling; it does not require an extra Node Termination Handler or a user-managed SQS queue for this purpose. Do not deploy the previous broken NTH DaemonSet onto Auto Mode nodes. If other node types coexist, configure their interruption handling separately with deliberate targeting and permissions.

NodePool disruption budgets constrain voluntary disruption such as consolidation and drift. They cannot stop EC2 from reclaiming Spot capacity, extend its notice, or guarantee that replacement capacity is ready.

All applicable budgets are considered together, taking the most restrictive allowance. The `10%` and `3` entries below are not alternatives. Percentages round up, and deleting/not-ready nodes consume the allowance; for 20 otherwise healthy nodes, these two entries allow at most two new voluntary disruptions outside the zero-budget window.

This example protects **Monday–Friday 09:00–18:00 in Seoul (KST)** by starting a nine-hour window at **00:00 UTC**. Karpenter budget schedules use UTC. The old `0 9-18 * * mon-fri` started another nine-hour window every hour, extending the blocked interval into the following day rather than ending at 18:00.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot-with-disruption-budget
spec:
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
        - r
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: spot-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        capacity-example: spot-lab
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
    - nodes: '3'
    - nodes: '0'
      schedule: 0 0 * * mon-fri
      duration: 9h
  limits:
    cpu: '100'
    memory: 400Gi
```

Adapt the window to your operational calendar; other timezones and daylight-saving changes need deliberate conversion. A zero voluntary budget can delay useful maintenance and still does not stop involuntary interruptions.

## Graceful Shutdown Within the Time Actually Available

EC2 normally issues a two-minute warning before stop/terminate interruption, but notices are best effort. Hibernation has a different immediate-start behavior. Do not treat two minutes as time guaranteed to every Pod: detection, eviction, application work and routing changes consume time, and failures can prevent notice handling.

`terminationGracePeriodSeconds` is a Kubernetes shutdown budget, not an extension of the EC2 deadline. `preStop` runs inside that budget before the normal stop signal. A blind `sleep 90` wastes most of a 120-second budget and does not implement application shutdown or checkpointing.

This nginx-specific example initiates graceful quit immediately, has a real HTTP readiness probe and records the node name accurately. For another application, implement and test its own stop-signal handler, readiness transition, in-flight work completion and durable checkpoints. The chosen 60 seconds is an example upper budget, not guaranteed available time.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spot-aware-app
  namespace: spot-lab
spec:
  replicas: 6
  selector:
    matchLabels:
      app: spot-aware
  template:
    metadata:
      labels:
        app: spot-aware
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: app
        image: nginx:1.30.4
        lifecycle:
          preStop:
            exec:
              command:
              - nginx
              - -s
              - quit
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        ports:
        - containerPort: 80
        readinessProbe:
          httpGet:
            path: /
            port: 80
          periodSeconds: 5
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: spot-aware
        minDomains: 2
        nodeAffinityPolicy: Honor
        nodeTaintsPolicy: Honor
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: spot-with-disruption-budget
      tolerations:
      - key: spot-lab
        operator: Equal
        value: 'true'
        effect: NoSchedule
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: spot-aware-budget
  namespace: spot-lab
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: spot-aware
```

`NODE_NAME` receives the node name through the Downward API. It is not a Spot boolean, and Downward API Pod fields do not automatically expose node labels. Applications should normally handle graceful termination regardless of purchase option. If capacity type is required, provide verified metadata through a reviewed mechanism rather than relying on node IMDS credentials.

The example requires two eligible AZ domains and balances six replicas with `maxSkew: 1`. Hard `DoNotSchedule` constraints may leave Pods Pending when an AZ or capacity is unavailable; they do not manufacture capacity. Review the tradeoff before requiring three domains, and do not assume an AZ spread also distributes instance types within an AZ.

The PDB limits voluntary application eviction; it cannot preserve a VM reclaimed by EC2. More replicas help only when traffic handling, eligible capacity, topology and failure recovery are also validated.

## Workload Suitability

| Workload | Starting point and required validation |
|----------|----------------------------------------|
| Stateless web/inference | Interrupt-tolerant Spot capacity with a deliberate critical baseline and tested latency/failover |
| Batch/CI | Spot can fit retryable, idempotent work; deadline-sensitive jobs may need other capacity |
| Long training or stateful processing | Periodic durable checkpoints and proven resume/replay, not a last-minute checkpoint guarantee |
| Single-instance database or critical quorum | Avoid interruption exposure without an explicit recovery architecture; On-Demand alone does not protect local data |
| Development/test | Use cost limits and tolerate capacity shortages; do not assume Spot-only jobs always start |

Keep the only copy of important state off disposable node-local storage. Validate durable storage, backups and restoration independently of instance purchase option.

## Historical Cost Illustration, Not a Current Quote

The previous guide published these monthly amounts without a region, instance-hour mix, billing scope or reproducible measurement. They are retained as **unverified teaching examples**, not measured savings with the current EKS version.

| Example | Prior On-Demand amount | Prior Spot amount | Arithmetic reduction |
|---------|------------------------|-------------------|----------------------|
| Batch | $1,000/month | $300/month | 70% |
| Development/test | $2,000/month | $500/month | 75% |
| CI/CD | $500/month | $150/month | 70% |
| Non-critical API | $3,000/month | $1,200/month | 60% |

AWS advertises EC2 Spot discounts of up to 90%; this is not a minimum discount or a whole-workload savings guarantee. Spot Instance Advisor summarizes trailing-month interruption/savings data averaged across AZs and may be delayed. Use current AZ-specific Spot Price History or actual billing data for a price calculation; historical interruption bands are not a prediction for your next job.

Compare the same useful work, region, period and availability objective:

```text
Baseline total =
  sum(baseline On-Demand node-hours[type] * On-Demand rate[type])
  + other baseline costs

Actual total =
  sum(billed Spot node-hours[type, AZ] * time-weighted Spot rate[type, AZ])
  + sum(billed On-Demand fallback node-hours[type] * On-Demand rate[type])
  + other actual costs

Net savings = Baseline total - Actual total
```

Use hours consistently with hourly rates, and weight changing prices by the actual billed usage intervals. Billed Spot/fallback hours should include retries, overlap and recovery work actually paid for. Do not subtract a second generic “interrupt overhead” charge if that work is already included in billed hours.

Include relevant Auto Mode management fees, control-plane charges, EBS, networking/NAT, data transfer, logging and licensing consistently in other costs. Auto Mode fees are additional to the EC2 purchase option. The old `interrupt count × recovery time × instance count` shortcut was ambiguous about units and whether interruptions were already cluster-wide.

## Operational Validation

Before relying on Spot, test interruption and recovery behavior in an approved environment, including no/late notice, unavailable replacement capacity, in-flight work, image pulls, storage recovery and hard topology constraints. Observe actual lost work and billed recovery cost. This audit performed only local schema, scheduling-window and configuration checks; it did not run these failure experiments.

## References

- [Spot interruption notices](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-instance-termination-notices.html)
- [Auto Mode native interruption handling](https://docs.aws.amazon.com/eks/latest/userguide/ml-node-pools.html)
- [Capacity type priority](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Karpenter disruption budgets and UTC schedules](https://karpenter.sh/v1.14/concepts/disruption/)
- [Pod termination and preStop](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Topology spread](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [Downward API fields](https://kubernetes.io/docs/concepts/workloads/pods/downward-api/)
- [nginx graceful shutdown](https://nginx.org/en/docs/control.html)
- [EC2 Spot published discount guidance](https://aws.amazon.com/ec2/spot/)
- [Spot Instance Advisor](https://aws.amazon.com/ec2/spot/instance-advisor/)
- [Spot price history API](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeSpotPriceHistory.html)
- [EKS Auto Mode pricing](https://aws.amazon.com/eks/pricing/)

< [Previous: Scaling Behavior](./03-scaling-behavior.md) | [Table of Contents](./README.md) | [Next: Operations](./05-operations.md) >
