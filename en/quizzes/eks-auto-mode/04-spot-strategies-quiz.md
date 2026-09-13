# EKS Auto Mode Spot Strategies Quiz

> **Related Document**: [Spot Instance Strategies](../../eks-auto-mode/04-spot-strategies.md)

## Multiple Choice Questions

### 1. Which approach broadens compatible Spot capacity choices?

- A) Use a single instance type in one AZ
- B) Allow diverse compatible types, sizes, architectures and AZs
- C) Require incompatible images on extra architectures
- D) Always select only the cheapest type

<details>
<summary>Show Answer</summary>

**Answer: B) Allow diverse compatible types, sizes, architectures and AZs**

**Explanation:**
Spot pools are tied to instance type/AZ combinations. Diversification provides more options, but does not make interruptions independent or double actual capacity just by listing two architectures. Validate the image, dependencies and performance profile first.

```yaml
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
```

This is a requirements fragment, not a complete NodePool.

</details>

### 2. Which label distinguishes Spot and On-Demand capacity in these examples?

- A) node.kubernetes.io/capacity-type
- B) karpenter.sh/capacity-type
- C) eks.amazonaws.com/instance-type
- D) karpenter.k8s.aws/spot-or-ondemand

<details>
<summary>Show Answer</summary>

**Answer: B) karpenter.sh/capacity-type**

**Explanation:**
Use `karpenter.sh/capacity-type` in NodePool requirements or Pod selection. Preferred affinity does not require Spot, reserve spare nodes or establish a fixed purchase-option ratio.

```yaml
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
```

For a mandatory baseline, use a compatible hard selector/required affinity in a separate workload. `spec.nodeName` from the Downward API is a node name, not a Spot boolean.

</details>

### 3. How should you interpret the EC2 Spot stop/terminate warning?

- A) Every Pod is guaranteed thirty seconds
- B) Normally two minutes, delivered on a best-effort basis
- C) Every Pod is guaranteed five minutes
- D) A ten-minute extension can be requested by preStop

<details>
<summary>Show Answer</summary>

**Answer: B) Normally two minutes, delivered on a best-effort basis**

**Explanation:**
EC2 normally provides a two-minute stop/terminate interruption notice, but delivery is best effort and hibernation has different immediate-start behavior. Kubernetes detection, eviction and application work consume time. Pod grace periods and preStop hooks do not extend EC2's deadline; a 90-second sleep is not a checkpoint or graceful-shutdown implementation. Use periodic durable checkpoints, idempotent recovery and tested application signal handling.

</details>

### 4. Which pattern most needs redesign before relying on interruptible capacity?

- A) Idempotent batch work with validated retry
- B) Replicated stateless service with tested failover
- C) Critical single-instance database with no recovery path and its only state on local storage
- D) Development jobs that tolerate delay and retry

<details>
<summary>Show Answer</summary>

**Answer: C) Critical single-instance database with no recovery path and its only state on local storage**

**Explanation:**
The single-instance pattern can lose availability and its only state. On-Demand also does not make node-local storage durable or eliminate maintenance/failure risk. Databases, queues and long-running jobs require architecture-specific evaluation rather than a blanket rule based on workload name.

</details>

### 5. Within one mixed-capacity NodePool, how do you allow Spot-first selection?

- A) Set spotPriority: high
- B) Allow spot and on-demand; Auto Mode applies its eligible-capacity priority
- C) Set capacityPriority: spot
- D) Use weight to reserve exactly 80% Spot nodes

<details>
<summary>Show Answer</summary>

**Answer: B) Allow spot and on-demand; Auto Mode applies its eligible-capacity priority**

**Explanation:**
Allow both capacity types. Array order and weight do not choose a percentage within that pool. If reserved capacity is also allowed and suitable, it has higher priority than Spot; Spot has priority over On-Demand. Availability and constraints still apply.

A separate two-pool strategy can use weights to influence provisioning preference:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot-first
spec:
  weight: 100
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
        - c
        - m
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
        capacity-strategy: spot-preferred
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ondemand-fallback
spec:
  weight: 10
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - c
        - m
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
        capacity-strategy: spot-preferred
  limits:
    cpu: '100'
    memory: 400Gi
```

Both pools have a common label and lab taint. Workloads needing fallback must tolerate the taint and match both pools; pinning a Pod to the Spot-only pool name prevents that fallback. Weight does not move already scheduled Pods or guarantee immediate fallback capacity.

</details>

### 6. What potential EC2 Spot discount does AWS advertise?

- A) A guaranteed 30–40% saving
- B) A guaranteed 50–60% saving
- C) Up to 90% versus On-Demand, not guaranteed whole-workload savings
- D) A guaranteed 95% or more

<details>
<summary>Show Answer</summary>

**Answer: C) Up to 90% versus On-Demand, not guaranteed whole-workload savings**

**Explanation:**
Actual rates and useful-work cost depend on type, AZ, period, recovery and other charges. Auto Mode management fees are additional to EC2 pricing. The previous teaching table is retained below without claiming verified results:

| Prior illustration | Unverified figure |
|---|---|
| Spot | 70–90% |
| Graviton/ARM | About 20% |
| Spot + Graviton | Up to 90% |

The comparison baselines and measurements were not established. Do not add these percentages or treat them as guaranteed savings. Advisor data is a trailing-month summary that can be delayed; use AZ-specific price history or actual bills and avoid double-counting recovery hours.

</details>
