# EKS Hybrid Nodes Cost Optimization Quiz

> **Related Document**: [Cost Optimization](../../eks-hybrid-nodes/07-cost-optimization.md)

## Multiple Choice Questions

### 1. Which is NOT a suitable cost optimization strategy for Hybrid Nodes environments?

A. Use on-premises GPUs for inference workloads
B. Handle burst traffic on cloud nodes
C. Migrate all workloads to Hybrid Nodes
D. Run data-locality-required workloads on-premises

<details>
<summary>Show Answer</summary>

**Answer: C. Migrate all workloads to Hybrid Nodes**

**Explanation:**
Migrating all workloads to Hybrid Nodes increases complexity and reduces cost efficiency. Choose the appropriate location based on workload characteristics.

**Cost Optimization Strategies:**

| Workload Type | Recommended Location | Reason |
|---------------|---------------------|--------|
| Continuous GPU Inference | On-premises | Utilize existing hardware |
| Burst Traffic | Cloud | Elastic scaling |
| Data-Intensive | Near data | Reduce transfer costs |
| Stateless | Cloud | Easier management |
| Regulated | On-premises | Compliance |

</details>

### 2. Which is NOT a factor to consider in break-even analysis between on-premises and cloud GPUs?

A. Hardware depreciation costs
B. Power and cooling costs
C. Cloud instance hourly costs
D. User interface design

<details>
<summary>Show Answer</summary>

**Answer: D. User interface design**

**Explanation:**
Break-even analysis focuses on infrastructure operational costs. UI design is unrelated to cost analysis.

**Cost Analysis Factors:**

```
On-premises TCO (Monthly):
+-- Hardware depreciation (GPU server / 36 months)
+-- Power costs (kWh x rate)
+-- Cooling costs (PUE factor)
+-- Network costs (Direct Connect)
+-- Labor costs (operations/maintenance)
+-- Facility costs (rental/space)

Cloud TCO (Monthly):
+-- Instance costs (hourly x usage hours)
+-- Data transfer costs
+-- Storage costs
+-- Managed service costs
```

```python
# Break-even calculation example
onprem_monthly = 5000  # On-premises monthly cost (fixed)
cloud_hourly = 32.77   # p4d.24xlarge hourly cost

# Break-even = On-premises monthly cost / Cloud hourly cost
breakeven_hours = onprem_monthly / cloud_hourly
print(f"Break-even point: {breakeven_hours:.0f} hours/month")  # ~153 hours
```

</details>

### 3. How do you configure Karpenter to prefer Spot instances for cost optimization?

A. Set Spot label with nodeSelector
B. Set capacity-type to spot as preferred in Provisioner
C. Manually create Spot instances
D. Use Fargate profile

<details>
<summary>Show Answer</summary>

**Answer: B. Set capacity-type to spot as preferred in Provisioner**

**Explanation:**
Karpenter Provisioner can be configured to preferentially use Spot instances.

```yaml
apiVersion: karpenter.sh/v1alpha5
kind: Provisioner
metadata:
  name: gpu-spot-provisioner
spec:
  requirements:
  - key: karpenter.sh/capacity-type
    operator: In
    values: ["spot", "on-demand"]  # Spot preferred
  - key: node.kubernetes.io/instance-type
    operator: In
    values: ["p4d.24xlarge", "p3.16xlarge"]

  # Spot instance priority (higher weight = higher priority)
  weight: 100

  limits:
    resources:
      nvidia.com/gpu: 32

  # Cost optimization: Scale down quickly when unused
  ttlSecondsAfterEmpty: 300
```

**Spot Instance Benefits:**
- Up to 90% cost savings vs on-demand
- Suitable for fault-tolerant workloads
- Recommended for batch processing, training jobs

</details>

### 4. What NVIDIA tool is used for monitoring GPU utilization to optimize costs?

A. nvidia-smi only
B. DCGM (Data Center GPU Manager) Exporter
C. kubectl top
D. htop

<details>
<summary>Show Answer</summary>

**Answer: B. DCGM (Data Center GPU Manager) Exporter**

**Explanation:**
DCGM Exporter exposes GPU metrics in Prometheus format, enabling detailed GPU utilization monitoring.

```yaml
# DCGM Exporter deployment (included in GPU Operator)
# or manual deployment
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: dcgm-exporter
  namespace: gpu-operator
spec:
  template:
    spec:
      containers:
      - name: dcgm-exporter
        image: nvcr.io/nvidia/k8s/dcgm-exporter:3.2.6-3.1.9-ubuntu22.04
        ports:
        - containerPort: 9400
```

```yaml
# Prometheus alerting rule example
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
spec:
  groups:
  - name: gpu.cost.rules
    rules:
    - alert: GPUUnderutilized
      expr: |
        avg_over_time(DCGM_FI_DEV_GPU_UTIL[1h]) < 20
      for: 2h
      labels:
        severity: info
      annotations:
        summary: "GPU utilization below 20% - cost optimization review needed"
```

**Key Monitoring Metrics:**
- `DCGM_FI_DEV_GPU_UTIL`: GPU utilization (%)
- `DCGM_FI_DEV_MEM_USED`: GPU memory usage
- `DCGM_FI_DEV_POWER_USAGE`: Power usage

</details>

### 5. What is the strategy for reducing data transfer costs in a hybrid environment?

A. Copy all data to cloud
B. Workload placement considering data locality
C. Transfer without data compression
D. Real-time synchronization of all data

<details>
<summary>Show Answer</summary>

**Answer: B. Workload placement considering data locality**

**Explanation:**
Processing data where it resides can significantly reduce network transfer costs.

```yaml
# Workload placement based on data location
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-processor
spec:
  template:
    spec:
      nodeSelector:
        data-location: primary-storage
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: location
                operator: In
                values: ["onprem"]  # Prefer nodes near data
```

**Data Transfer Cost Optimization Strategies:**

| Strategy | Savings |
|----------|---------|
| Data locality placement | 40-60% |
| Data compression | 30-50% |
| Caching layer | 20-40% |
| Batch transfer | 10-20% |

</details>

### 6. What workload type is most suitable for Reserved Instances or Savings Plans?

A. Unpredictable burst workloads
B. One-time batch jobs
C. Stable and predictable always-on workloads
D. Test and development environments

<details>
<summary>Show Answer</summary>

**Answer: C. Stable and predictable always-on workloads**

**Explanation:**
Reserved Instances and Savings Plans offer discounts with 1-3 year commitments, making them suitable for continuously running workloads.

```
Cost Model Comparison:

Workload Type              | Recommended Pricing Model
---------------------------|---------------------------
Always-on (24/7)           | Reserved/Savings Plans (up to 72% discount)
Predictable peaks          | On-Demand + Scheduled Reserved
Burst/Idle                 | Spot Instances (up to 90% discount)
Test/Development           | Spot or On-Demand
```

**Cost Optimization Combination in EKS:**
```yaml
# Base capacity: Reserved Instances
# Peak capacity: Spot Instances
# Burst: On-Demand (Karpenter auto-scaling)

apiVersion: karpenter.sh/v1alpha5
kind: Provisioner
metadata:
  name: mixed-capacity
spec:
  requirements:
  - key: karpenter.sh/capacity-type
    operator: In
    values: ["spot", "on-demand"]
  # Cost optimization priority: spot > on-demand
```

</details>

