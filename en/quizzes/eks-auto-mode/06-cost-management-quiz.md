# EKS Auto Mode Cost Management Quiz

> **Related Document**: [Cost Management](../../eks-auto-mode/06-cost-management.md)

## Multiple Choice Questions

### 1. Approximately what percentage of cost savings can be achieved by including Graviton (ARM) instances for cost optimization?

- A) 5%
- B) 10%
- C) 20%
- D) 50%

<details>
<summary>Show Answer</summary>

**Answer: C) 20%**

**Explanation:**
AWS Graviton processor-based instances (arm64) are approximately 20% cheaper than comparable x86 instances while delivering excellent performance.

```yaml
spec:
  template:
    spec:
      requirements:
        # Include Graviton (ARM) instances
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
```

**Cost Optimization Strategies:**
- Using Graviton (ARM) instances: ~20% savings
- Using Spot instances: Up to 70-90% savings
- Aggressive Consolidation: Consolidate underutilized nodes
- Appropriate resource requests: Prevent overprovisioning

</details>

### 2. What does it mean when CPU limit is set to 500 in NodePool's `limits` setting?

- A) Maximum CPU per node is 500 cores
- B) NodePool can provision up to 500 vCPU total
- C) Maximum 500m CPU per Pod
- D) Cluster-wide CPU limit

<details>
<summary>Show Answer</summary>

**Answer: B) NodePool can provision up to 500 vCPU total**

**Explanation:**
NodePool's `limits` restricts the total amount of resources that NodePool can provision.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: compute-optimized
spec:
  limits:
    cpu: 500      # Maximum 500 vCPU
    memory: 1Ti   # Maximum 1TB memory
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c"]
```

This helps prevent cost overruns and manage budgets.

</details>

### 3. What Consolidation policy automatically cleans up underutilized nodes to optimize costs?

- A) `consolidationPolicy: WhenEmpty`
- B) `consolidationPolicy: WhenEmptyOrUnderutilized`
- C) `consolidationPolicy: Always`
- D) `consolidationPolicy: Aggressive`

<details>
<summary>Show Answer</summary>

**Answer: B) `consolidationPolicy: WhenEmptyOrUnderutilized`**

**Explanation:**
The `WhenEmptyOrUnderutilized` policy targets both empty and underutilized nodes for consolidation.

```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
```

**Policy Comparison:**
- `WhenEmpty`: Only removes empty nodes (conservative, stability-first)
- `WhenEmptyOrUnderutilized`: Aggressive cost optimization

Cost savings effect: Consolidate underutilized nodes to reduce total node count and infrastructure costs

</details>

### 4. What is the recommended approach when using Savings Plans with EKS Auto Mode?

- A) Compute Savings Plans for instance family flexibility
- B) EC2 Instance Savings Plans for specific instance types
- C) Use only Reserved Instances
- D) Don't use Savings Plans

<details>
<summary>Show Answer</summary>

**Answer: A) Compute Savings Plans for instance family flexibility**

**Explanation:**
Auto Mode uses various instance types depending on workloads, making Compute Savings Plans most suitable.

**Savings Plans Comparison:**
| Type | Flexibility | Discount |
|------|-------------|----------|
| Compute Savings Plans | Instance family, size, region, OS flexible | Up to 66% |
| EC2 Instance Savings Plans | Specific instance family fixed | Up to 72% |

```
Recommended Strategy:
1. Analyze baseline workload volume (3-month baseline)
2. Cover 70% of minimum usage with Compute Savings Plans
3. Run remainder flexibly with Spot/On-Demand
```

</details>

### 5. What is required for Pod-level cost allocation in cost analysis using Kubecost?

- A) Automatically supported without configuration
- B) Add cost-center label to Pods
- C) Install Kubecost agent and cluster integration
- D) AWS Cost Explorer is sufficient

<details>
<summary>Show Answer</summary>

**Answer: C) Install Kubecost agent and cluster integration**

**Explanation:**
Kubecost is a Kubernetes-native cost monitoring tool that provides detailed cost analysis.

```bash
# Kubecost installation (Helm)
helm repo add kubecost https://kubecost.github.io/cost-analyzer/
helm install kubecost kubecost/cost-analyzer \
    --namespace kubecost \
    --create-namespace
```

Kubecost features:
- Cost analysis by namespace/workload
- Resource efficiency recommendations
- Budget alert settings
- AWS integration for actual cost accuracy

</details>

### 6. What is the best practice to prevent overprovisioning when setting resource requests?

- A) Always set limits and requests equal
- B) Reference VPA recommendations based on actual usage
- C) Set requests as high as possible
- D) Omit requests setting

<details>
<summary>Show Answer</summary>

**Answer: B) Reference VPA recommendations based on actual usage**

**Explanation:**
Use Vertical Pod Autoscaler (VPA) to analyze actual resource usage and set appropriate request values.

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Off"  # Only provide recommendations, no auto-apply
```

Check recommendations:
```bash
kubectl describe vpa my-app-vpa
```

This enables:
- Prevent overprovisioning (cost savings)
- Prevent underprovisioning (performance guarantee)

</details>

### 7. What is the cost-efficient NodePool separation strategy for multi-tier workloads?

- A) Place all workloads in single NodePool
- B) Separate NodePool by tier (frontend/API/batch/ML)
- C) Separate NodePool by instance size
- D) Separate NodePool by availability zone

<details>
<summary>Show Answer</summary>

**Answer: B) Separate NodePool by tier (frontend/API/batch/ML)**

**Explanation:**
Separating NodePools according to workload characteristics achieves optimal cost/performance balance.

| Tier | Strategy | Expected Savings |
|------|----------|-----------------|
| Frontend | On-Demand + Graviton | ~20% |
| API | Spot mixed + Graviton | ~40% |
| Batch | Spot only + diversification | ~70% |
| ML | Appropriate instance size selection | ~30% |

```yaml
# Batch tier example - Maximum cost savings
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch-tier
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]  # Spot only
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]  # Include Graviton
```

</details>

### 8. What is needed to categorize EKS Auto Mode costs by tag in AWS Cost Explorer?

- A) All tags are automatically applied
- B) Need to set tags field in NodeClass
- C) Configure in AWS Organizations
- D) Tag-based categorization not possible

<details>
<summary>Show Answer</summary>

**Answer: B) Need to set tags field in NodeClass**

**Explanation:**
Apply cost allocation tags to provisioned nodes through the tags field in NodeClass.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: production-nodeclass
spec:
  tags:
    Environment: production
    Team: platform
    CostCenter: engineering-001
    Project: kubernetes-platform
```

AWS Cost Explorer setup:
1. Enable Cost Allocation Tags in Billing Console
2. Select desired tag keys
3. Available in Cost Explorer after 24 hours

</details>
