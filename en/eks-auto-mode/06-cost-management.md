# Cost Management and Optimization

> **Supported Versions**: EKS 1.29+, EKS Auto Mode GA
> **Last Updated**: July 11, 2026

This guide covers cost optimization strategies for EKS Auto Mode, including cost analysis, Spot savings measurement, resource right-sizing, and Savings Plans integration.

### July 2026 Update: GPU Management Fees Reduced by Up to 60%

Effective July 1, 2026, EKS Auto Mode management fees for GPU and accelerated instance types were reduced:

- **G-series**: management fees reduced by 35%
- **P-series and AWS Trainium**: management fees reduced by 60%

The reductions apply automatically to all Auto Mode clusters in every AWS Region where EKS Auto Mode is available — no action required. Auto Mode includes capabilities built for accelerated workloads, such as parallel image pulling and unpacking on GPU instances with local NVMe storage (so large container and model images start faster) and accelerator-aware node repair that detects GPU hardware failures and automatically replaces unhealthy nodes. See [Amazon EKS pricing](https://aws.amazon.com/eks/pricing/) for the updated rate table. ([Announcement](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-eks-auto-mode-gpu-price))

---

## Cost Optimization Best Practices

```yaml
# cost-optimization-best-practices.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-optimized
spec:
  template:
    spec:
      requirements:
        # 1. Allow various instance families
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r", "i", "d"]

        # 2. Include Graviton (ARM) instances (20% cheaper)
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]

        # 3. Prioritize Spot instances
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]

      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default

  # 4. Aggressive Consolidation
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
---
# Pod settings for cost optimization
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cost-efficient-app
spec:
  replicas: 5
  template:
    spec:
      # Prefer Spot
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              preference:
                matchExpressions:
                  - key: karpenter.sh/capacity-type
                    operator: In
                    values: ["spot"]

      # Appropriate resource requests (prevent overprovisioning)
      containers:
        - name: app
          resources:
            requests:
              cpu: 250m      # Based on actual usage
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
```

---

## Cost Analysis Dashboard

### CloudWatch Cost Metrics

Set up a CloudWatch dashboard to track Auto Mode costs:

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "title": "Node Hours by Capacity Type",
        "metrics": [
          ["Karpenter", "karpenter_nodes_total", "capacity_type", "spot"],
          ["Karpenter", "karpenter_nodes_total", "capacity_type", "on-demand"]
        ],
        "period": 3600,
        "stat": "Average"
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Node Provisioning Rate",
        "metrics": [
          ["Karpenter", "karpenter_nodeclaims_created"],
          ["Karpenter", "karpenter_nodeclaims_terminated"]
        ],
        "period": 3600,
        "stat": "Sum"
      }
    }
  ]
}
```

### Kubecost Integration

For detailed cost allocation, integrate Kubecost:

```bash
# Install Kubecost
helm repo add kubecost https://kubecost.github.io/cost-analyzer/
helm install kubecost kubecost/cost-analyzer \
  --namespace kubecost \
  --create-namespace \
  --set kubecostToken="<your-token>"
```

Key Kubecost metrics for Auto Mode:

| Metric | Description | Use Case |
|--------|-------------|----------|
| Cluster cost | Total compute spend | Budget tracking |
| Namespace cost | Cost per namespace | Chargeback |
| Pod cost | Cost per workload | Optimization targets |
| Idle cost | Unused resources | Right-sizing opportunities |
| Spot savings | Spot vs On-Demand delta | Validate Spot strategy |

---

## Measuring Spot Instance Savings

### Calculate Actual Spot Savings

```bash
# Get current node distribution
kubectl get nodes -L karpenter.sh/capacity-type -L node.kubernetes.io/instance-type | \
  awk 'NR>1 {print $6, $7}' | sort | uniq -c
```

### Spot Savings Analysis Script

```bash
#!/bin/bash
# spot-savings-analysis.sh

# Get Spot and On-Demand node counts
SPOT_NODES=$(kubectl get nodes -l karpenter.sh/capacity-type=spot --no-headers | wc -l)
OD_NODES=$(kubectl get nodes -l karpenter.sh/capacity-type=on-demand --no-headers | wc -l)

echo "Current Node Distribution:"
echo "  Spot nodes: $SPOT_NODES"
echo "  On-Demand nodes: $OD_NODES"
echo "  Spot percentage: $(echo "scale=2; $SPOT_NODES * 100 / ($SPOT_NODES + $OD_NODES)" | bc)%"

# Estimate savings (assuming average 70% Spot discount)
echo ""
echo "Estimated Monthly Savings:"
echo "  If all were On-Demand: \$X,XXX"
echo "  With current Spot mix: \$X,XXX"
echo "  Monthly savings: \$X,XXX (XX%)"
```

### AWS Cost Explorer Queries

Use Cost Explorer to analyze Auto Mode costs:

1. **Filter by tag**: `eks:cluster-name` = your-cluster
2. **Group by**: `Instance Type` or `Purchase Option`
3. **Time range**: Last 30 days
4. **Compare**: Spot vs On-Demand spend

---

## Resource Right-Sizing Analysis

### VPA Recommendations

Install Vertical Pod Autoscaler for right-sizing recommendations:

```bash
# Install VPA
kubectl apply -f https://github.com/kubernetes/autoscaler/releases/latest/download/vpa-v1-crd-gen.yaml
kubectl apply -f https://github.com/kubernetes/autoscaler/releases/latest/download/vpa-rbac.yaml
kubectl apply -f https://github.com/kubernetes/autoscaler/releases/latest/download/recommender-deployment.yaml
```

Configure VPA in recommendation mode:

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Off"  # Recommendation only
  resourcePolicy:
    containerPolicies:
      - containerName: '*'
        minAllowed:
          cpu: 100m
          memory: 128Mi
        maxAllowed:
          cpu: 4
          memory: 8Gi
```

### Analyzing Usage Patterns

```bash
# Get VPA recommendations
kubectl get vpa my-app-vpa -o jsonpath='{.status.recommendation.containerRecommendations[0]}' | jq

# Compare with current requests
kubectl get deployment my-app -o jsonpath='{.spec.template.spec.containers[0].resources}'
```

### Right-Sizing Decision Matrix

| Current vs Recommended | Action | Expected Savings |
|------------------------|--------|------------------|
| Request > 2x usage | Reduce request | 20-50% |
| Request within 2x | Optimal | - |
| Request < usage | Increase request | Avoid OOM |
| Limit >> request | Reduce limit | Better bin-packing |

---

## Savings Plans and Reserved Instances Strategy

### How Savings Plans Interact with Auto Mode

EKS Auto Mode with Savings Plans:

| Scenario | Savings Plans Apply | Recommendation |
|----------|---------------------|----------------|
| On-Demand nodes | Yes | Purchase Compute Savings Plans |
| Spot nodes | No (already discounted) | Don't include in coverage |
| Graviton instances | Yes (separate rate) | Consider ARM Savings Plans |
| Mixed workloads | Partial | Calculate On-Demand baseline |

### Savings Plans Sizing

```
Recommended Savings Plans Coverage =
    Baseline On-Demand Hours *
    (1 - Expected Spot Percentage) *
    Average Instance Cost

Where:
- Baseline = Minimum sustained usage
- Expected Spot = Target Spot percentage (e.g., 60%)
- Don't over-commit (leave room for Spot)
```

### Savings Plans Best Practices

| Practice | Rationale |
|----------|-----------|
| Cover 60-70% of On-Demand baseline | Leave room for Spot optimization |
| Use Compute Savings Plans | Flexibility across instance types |
| Review quarterly | Adjust as workload evolves |
| Exclude GPU instances | Separate GPU-specific plans |

### Reserved Instances vs Savings Plans

| Factor | Reserved Instances | Savings Plans |
|--------|-------------------|---------------|
| Flexibility | Instance-specific | Any instance |
| Auto Mode fit | Poor (instances vary) | Good |
| Commitment | 1 or 3 years | 1 or 3 years |
| Recommendation | Not recommended | Recommended |

---

## Cost Optimization Checklist

### Quick Wins

| Action | Estimated Savings | Effort |
|--------|-------------------|--------|
| Enable Spot instances | 60-90% on Spot nodes | Low |
| Add ARM/Graviton support | 20% on ARM instances | Low |
| Right-size requests | 10-30% | Medium |
| Enable consolidation | 10-20% | Low |

### Medium-Term Optimizations

| Action | Estimated Savings | Effort |
|--------|-------------------|--------|
| Implement VPA | 15-30% | Medium |
| Purchase Savings Plans | 20-40% on On-Demand | Low |
| Multi-AZ optimization | 5-10% | Medium |
| Workload scheduling | 10-20% | High |

### Cost Monitoring Alerts

Set up alerts for cost anomalies:

```yaml
# CloudWatch Alarm for unexpected node growth
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  NodeCountAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: EKS-Auto-Mode-Node-Count-High
      MetricName: karpenter_nodes_total
      Namespace: Karpenter
      Statistic: Average
      Period: 300
      EvaluationPeriods: 3
      Threshold: 100  # Adjust based on expected max
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref AlertSNSTopic
```

---

## Cost Attribution

### Tagging Strategy for Cost Allocation

```yaml
# NodeClass with cost allocation tags
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: tagged-nodeclass
spec:
  tags:
    Environment: production
    Team: platform
    CostCenter: "12345"
    Application: my-app
    ManagedBy: eks-auto-mode
```

### Namespace-Level Cost Tracking

```yaml
# Namespace with cost labels
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
  labels:
    cost-center: "team-a"
    environment: production
```

---

< [Previous: Operations](./05-operations.md) | [Table of Contents](./README.md) | [Next: Node Lifecycle](./07-node-lifecycle.md) >
