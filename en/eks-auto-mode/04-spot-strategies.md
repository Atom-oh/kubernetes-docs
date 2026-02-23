# Spot Instance Utilization Strategies

> **Supported Versions**: EKS 1.29+, EKS Auto Mode GA
> **Last Updated**: February 19, 2026

This guide covers strategies for using Spot instances effectively with EKS Auto Mode, including mixed capacity configurations, diversification, and interrupt handling.

---

## Mixed Spot and On-Demand Strategy

A mixed strategy achieves both stability and cost efficiency.

```yaml
# spot-ondemand-mixed.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: mixed-capacity
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r"]
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["5"]
        # Allow both Spot and On-Demand
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
---
# Configure Spot preference in Pod
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spot-friendly-app
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
      # Prefer Spot instances
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              preference:
                matchExpressions:
                  - key: karpenter.sh/capacity-type
                    operator: In
                    values: ["spot"]
      # For critical workloads, require On-Demand
      # requiredDuringSchedulingIgnoredDuringExecution:
      #   nodeSelectorTerms:
      #     - matchExpressions:
      #         - key: karpenter.sh/capacity-type
      #           operator: In
      #           values: ["on-demand"]
      containers:
        - name: app
          image: my-app:latest
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
```

### Capacity Type Selection Guidelines

| Workload Type | Recommended Capacity | Rationale |
|---------------|---------------------|-----------|
| Stateless web services | Spot preferred | Can handle interrupts |
| Batch processing | Spot only | Cost savings, retryable |
| Databases | On-Demand only | Data integrity |
| CI/CD runners | Spot preferred | Cost savings, retryable |
| Machine learning inference | Mixed | Balance cost and availability |
| Machine learning training | Mixed with checkpointing | Long-running, can checkpoint |

---

## Spot Instance Diversification

Use diverse instance types to spread interrupt risk.

```yaml
# diversified-spot.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: diversified-spot
spec:
  template:
    spec:
      requirements:
        # Various instance families
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r", "i", "d"]
        # Various generations
        - key: karpenter.k8s.aws/instance-generation
          operator: In
          values: ["5", "6", "7"]
        # Various sizes
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["large", "xlarge", "2xlarge"]
        # Various architectures
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
        # Use only Spot
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  # Fast re-provisioning on Spot interrupt
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### Diversification Best Practices

| Strategy | Benefit | Configuration |
|----------|---------|---------------|
| Multiple instance families | Reduces correlated interrupts | `["m", "c", "r", "i", "d"]` |
| Multiple generations | Access larger capacity pool | `["5", "6", "7"]` |
| Multiple sizes | Flexibility in provisioning | `["large", "xlarge", "2xlarge"]` |
| Multiple architectures | 2x capacity pool | `["amd64", "arm64"]` |

---

## Spot Interrupt Handling

### Disruption Budget Configuration

```yaml
# spot-disruption-budget.yaml
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
          values: ["spot"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    # Limit concurrent node disruptions
    budgets:
      - nodes: "10%"    # Only 10% of total nodes simultaneously
      - nodes: "3"      # Or maximum 3 nodes
      # Minimize disruptions during business hours
      - nodes: "0"
        schedule: "0 9-18 * * mon-fri"  # Weekdays 9-18
        duration: 9h
```

### Pod Configuration for Spot Awareness

```yaml
# Configure Spot interrupt handling in Pod
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spot-aware-app
spec:
  replicas: 5
  selector:
    matchLabels:
      app: spot-aware
  template:
    metadata:
      labels:
        app: spot-aware
    spec:
      # Allow time for graceful shutdown
      terminationGracePeriodSeconds: 120
      containers:
        - name: app
          image: my-app:latest
          lifecycle:
            preStop:
              exec:
                command: ["/bin/sh", "-c", "sleep 90"]
      # Spread across multiple AZs
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: spot-aware
```

### Interrupt Handling Checklist

| Item | Description | Implementation |
|------|-------------|----------------|
| Graceful shutdown | Handle SIGTERM properly | `terminationGracePeriodSeconds` |
| PreStop hook | Delay termination | `lifecycle.preStop` |
| Multi-AZ spread | Survive AZ-wide interrupts | `topologySpreadConstraints` |
| Multiple replicas | No single point of failure | `replicas > 1` |
| State externalization | Don't store state locally | Use external databases/caches |

---

## Cost Savings Examples

```
+-----------------------------------------------------------------------------+
|                       Spot Instance Cost Savings Examples                    |
+-----------------------------------------------------------------------------+
|                                                                              |
|  Workload Type          On-Demand Cost   Spot Cost      Savings             |
|  ---------------------------------------------------------------------------  |
|  Batch Processing        $1,000/month    $300/month     70%                 |
|  Dev/Test Environment    $2,000/month    $500/month     75%                 |
|  CI/CD Pipeline          $500/month      $150/month     70%                 |
|  Non-critical API Server $3,000/month    $1,200/month   60%                 |
|                                                                              |
|  * Spot instance prices vary based on supply and demand                      |
|                                                                              |
+-----------------------------------------------------------------------------+
```

### Calculating Spot Savings

To estimate your potential Spot savings:

1. **Identify Spot-eligible workloads**: Stateless, fault-tolerant, flexible
2. **Check Spot pricing history**: Use AWS Spot Instance Advisor
3. **Calculate baseline On-Demand cost**: Current or projected spend
4. **Apply average Spot discount**: Typically 60-90% off On-Demand
5. **Factor in interrupt overhead**: Additional compute for re-provisioning

### Spot Savings Formula

```
Estimated Monthly Savings =
    (On-Demand Hours * On-Demand Price) -
    (Spot Hours * Spot Price) -
    (Interrupt Overhead * On-Demand Price)

Where:
- Interrupt Overhead = Estimated interrupts * Recovery time * Instance count
```

---

## Spot Best Practices Summary

| Practice | Description |
|----------|-------------|
| Diversify instance types | Use 10+ instance types to reduce interrupt risk |
| Use multiple AZs | Spread across 3+ AZs for availability |
| Set appropriate grace periods | Allow 120+ seconds for graceful shutdown |
| Implement health checks | Detect and replace unhealthy pods quickly |
| Use topology spread | Prevent all replicas on same Spot pool |
| Externalize state | Don't store critical data on Spot nodes |
| Set disruption budgets | Limit concurrent disruptions |
| Monitor Spot metrics | Track interrupts and savings |

---

< [Previous: Scaling Behavior](./03-scaling-behavior.md) | [Table of Contents](./README.md) | [Next: Operations](./05-operations.md) >
