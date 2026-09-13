# EKS Auto Mode Cost Management Quiz

> **Related Document**: [Cost Management](../../eks-auto-mode/06-cost-management.md)
> **Last Updated**: September 12, 2026

## Multiple Choice Questions

### 1. How should the prior “20% Graviton saving” be used when allowing ARM nodes?

- A) As a universal AWS guarantee
- B) As a discount on the entire bill
- C) As an unverified example; compare compatible workloads and actual rates
- D) As proof every image runs on ARM

<details>
<summary>Show Answer</summary>

**Answer: C) As an unverified example; compare compatible workloads and actual rates**

**Explanation:**
The old ~20% ARM and 70–90% Spot figures were planning examples, not a verified comparison for this workload. Check multi-architecture images, dependencies, performance per useful work, current regional rates and Auto Mode/other fees. Allowing `amd64` and `arm64` does not validate application compatibility or guarantee either architecture is selected.

</details>

### 2. What does a dynamic NodePool `limits.cpu: 500` constrain?

- A) Each node to 500 cores
- B) Aggregate CPU resources provisioned by that pool
- C) Each Pod to 500m
- D) All AWS spending in the account

<details>
<summary>Show Answer</summary>

**Answer: B) Aggregate CPU resources provisioned by that pool**

**Explanation:**
It is a pool-level resource ceiling, with possible temporary overshoot during rapid eventually consistent provisioning. `1Ti` means 1 TiB (1024 GiB), not one decimal TB. Resource limits help constrain growth but do not price instances, include other services, or enforce a hard monetary budget.
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: compute-optimized
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
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
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
      - key: cost-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        cost-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
  limits:
    cpu: '500'
    memory: 1Ti
```


</details>

### 3. Which policy permits consolidation of empty and underutilized nodes when rescheduling/cost constraints allow it?

- A) `WhenEmpty`
- B) `WhenEmptyOrUnderutilized`
- C) `Always`
- D) `Aggressive`

<details>
<summary>Show Answer</summary>

**Answer: B) `WhenEmptyOrUnderutilized`**

**Explanation:**
This evaluates request-based scheduling feasibility and cost; it does not delete every node below a measured CPU threshold. `consolidateAfter` is a debounce, and PDBs, budgets and placement constraints can block consolidation. `WhenEmpty` is narrower; neither policy guarantees savings or disables every other disruption method.

</details>

### 4. Which option gives billing flexibility when eligible EC2 usage may change family or region?

- A) Compute Savings Plans
- B) An EC2 Instance Savings Plan fixed to one family and region
- C) Only one exact-size Standard RI
- D) Exclude all commitment discounts

<details>
<summary>Show Answer</summary>

**Answer: A) Compute Savings Plans**

**Explanation:**
Compute Savings Plans offer family/size/region/OS/tenancy flexibility; EC2 Instance Savings Plans are family-and-region commitments with size/OS/tenancy flexibility. The advertised maxima remain up to 66% and 72%, not expected rates. Match a USD/hour commitment to sustained eligible uncovered usage, existing commitments and planned changes. The old three-month/70%-coverage strategy is an unverified planning example. Spot and the separate Auto Mode charge do not receive EC2 Savings Plans discounts; there is no special ARM plan or universal GPU exclusion.

</details>

### 5. What is required for useful Kubecost Pod-level allocation?

- A) No setup or data sources
- B) Only a Pod cost-center label
- C) A configured agent/cluster integration and appropriate cost data
- D) Cost Explorer alone without Kubernetes allocation data

<details>
<summary>Show Answer</summary>

**Answer: C) A configured agent/cluster integration and appropriate cost data**

**Explanation:**
The reviewed Kubecost 3.2.4 chart is `kubecost/kubecost` from the new repository. Version 3's FinOps agent/ClickHouse architecture differs from the old cost-analyzer deployment. Configure licensing, private access, storage/retention, workload IAM and billing reconciliation. Render the reviewed values before installation; labels alone do not create actual cost data.

```bash
: "${KUBECOST_VALUES:?Set the reviewed Kubecost 3.2.4 values file}"
test -f "$KUBECOST_VALUES"
helm repo add kubecost https://kubecost.github.io/kubecost/
helm repo update kubecost
helm show chart kubecost/kubecost --version 3.2.4
helm template cost-review kubecost/kubecost --version 3.2.4 \
  --namespace kubecost --values "$KUBECOST_VALUES" \
  > "$WORK_DIR/kubecost-rendered.yaml"
```


</details>

### 6. What evidence should guide resource-request changes?

- A) Always make requests and limits equal
- B) VPA recommendations plus representative workload/SLO evidence
- C) Maximize all requests
- D) Remove requests

<details>
<summary>Show Answer</summary>

**Answer: B) VPA recommendations plus representative workload/SLO evidence**

**Explanation:**
`Off` does not apply recommendations and still needs functioning VPA components/metrics. Check every container, confidence/history, startup peaks, memory limits and CPU throttling. A recommendation does not guarantee performance, prevent every OOM or prove a saving. Do not strip Kubernetes unit suffixes when comparing quantities.
```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: cost-app-vpa
  namespace: cost-lab
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cost-efficient-app
  updatePolicy:
    updateMode: 'Off'
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: '4'
        memory: 8Gi
```


</details>

### 7. When tiers have genuinely different interruption or architecture requirements, which design can express them?

- A) Require identical placement for every tier
- B) Use appropriate tier pools and matching workload constraints
- C) Create a separate pool for every instance size
- D) Assume each AZ is a separate billing discount

<details>
<summary>Show Answer</summary>

**Answer: B) Use appropriate tier pools and matching workload constraints**

**Explanation:**
Separate pools may express real constraints, but fragmentation can increase idle cost. A Spot-only batch pool has no On-Demand fallback; use it only for compatible interruption-tolerant jobs with recovery. A pool name alone does not route workloads: set selectors/tolerations as in the guide.

| Tier | Prior strategy | Original unverified saving |
|------|----------------|----------------------------|
| Frontend | On-Demand + Graviton | ~20% |
| API | Mixed Spot + Graviton | ~40% |
| Batch | Spot + diversity | ~70% |
| ML | Instance sizing | ~30% |

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch-tier
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
      - key: cost-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        cost-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
```


</details>

### 8. What is needed for custom NodeClass tags to support AWS cost allocation?

- A) Every Kubernetes label automatically propagates
- B) Valid NodeClass/tagging permissions, actual resource tags and Billing activation
- C) Only creating an AWS Organization
- D) Tag allocation is impossible

<details>
<summary>Show Answer</summary>

**Answer: B) Valid NodeClass/tagging permissions, actual resource tags and Billing activation**

**Explanation:**
The related guide supplies a complete NodeClass with identity/network selectors. Review node access entries and tag permissions, reference that class from the intended pool, verify actual tags and activate the keys in Billing. User-defined keys can take up to 24 hours to appear and another up to 24 hours to activate; reporting latency is separate. The AWS-generated EC2 cluster key is `aws:eks:cluster-name`; it does not include control-plane charges. Namespace labels alone neither propagate nor allocate all AWS costs.

</details>

## References

- [EKS pricing](https://aws.amazon.com/eks/pricing/)
- [Savings Plans types](https://docs.aws.amazon.com/savingsplans/latest/userguide/plan-types.html)
- [EKS billing tags](https://docs.aws.amazon.com/eks/latest/userguide/eks-using-tags.html)
