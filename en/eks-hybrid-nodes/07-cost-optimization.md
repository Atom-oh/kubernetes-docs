# Cost Optimization

< [Previous: Workload Placement](./06-workload-placement.md) | [Table of Contents](./README.md) | [Next: Operations](./08-operations.md) >

> **Supported Versions**: EKS 1.31+
> **Last Updated**: February 2025

This document covers cost optimization strategies for EKS Hybrid Nodes environments, including on-premises vs cloud cost comparisons and workload distribution recommendations.

## On-Premises GPU vs Cloud GPU Cost Comparison

### Monthly Cost Comparison (Example)

| Item | On-Premises H100 Server | AWS p5.48xlarge |
|------|------------------------|-----------------|
| GPU | 8x H100 80GB | 8x H100 80GB |
| Hourly Cost | ~$24.96 (TCO-based) | ~$98.32 |
| Monthly Cost (24/7) | ~$17,971 | ~$70,790 |
| 3-Year TCO | ~$647,000 | ~$2,548,440 |

> **Calculation Basis**: On-premises includes hardware, power, cooling, space, management personnel. Cloud is based on On-Demand pricing.

### Cost Calculation Script

```bash
#!/bin/bash
# cost-calculator.sh - Hybrid Environment Cost Calculator

# On-premises H100 server monthly cost (TCO-based)
ONPREM_H100_MONTHLY=17971

# AWS p5.48xlarge hourly cost
AWS_P5_HOURLY=98.32

# Enter usage hours
read -p "Monthly GPU usage hours: " HOURS

# Calculate costs
AWS_COST=$(echo "$AWS_P5_HOURLY * $HOURS" | bc)
ONPREM_COST=$ONPREM_H100_MONTHLY

echo ""
echo "=== Monthly Cost Comparison ==="
echo "On-Premises H100: \$${ONPREM_COST}"
echo "AWS p5.48xlarge: \$${AWS_COST}"
echo ""

# Calculate break-even point
BREAKEVEN=$(echo "$ONPREM_COST / $AWS_P5_HOURLY" | bc)
echo "Break-even point: ${BREAKEVEN} hours/month"
echo "If current usage exceeds ${BREAKEVEN} hours, on-premises is more cost-effective."
```

## Break-Even Analysis

```
Cost comparison by monthly usage hours:

  $80,000 |                                        ___
          |                                   ____/
  $60,000 |                              ____/
          |                         ____/
  $40,000 |                    ____/
          |               ____/
  $20,000 |----------____/------------------------ On-Premises (Fixed Cost)
          |     ____/
        0 |____/
          +----+----+----+----+----+----+----+----+
            100  200  300  400  500  600  700  730
                     Monthly GPU Usage Hours

Break-even point: ~183 hours/month (25% utilization)
- Below 183 hours: AWS is advantageous
- Above 183 hours: On-premises is advantageous
```

## AWS Cost Explorer Integration

```bash
# Hybrid environment cost tag configuration
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-01-31 \
  --granularity MONTHLY \
  --metrics "BlendedCost" \
  --group-by Type=TAG,Key=Environment Type=TAG,Key=NodeType \
  --filter '{
    "Tags": {
      "Key": "kubernetes.io/cluster/my-hybrid-cluster",
      "Values": ["owned"]
    }
  }'

# Cost analysis by EKS cluster
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-01-31 \
  --granularity DAILY \
  --metrics "UnblendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE \
  --filter '{
    "Tags": {
      "Key": "eks:cluster-name",
      "Values": ["my-hybrid-cluster"]
    }
  }'
```

## Selective Workload Distribution Recommendations

| Workload Type | Recommended Location | Reason |
|--------------|---------------------|--------|
| Large-scale model training | On-Premises GPU | Long-running, cost-effective |
| Real-time inference (high load) | On-Premises GPU | Consistent latency |
| Real-time inference (variable) | AWS (Karpenter) | Elastic scaling |
| Data preprocessing | On-Premises CPU | Minimize data movement |
| API serving | AWS | Global distribution, Auto Scaling |
| Batch processing | AWS Spot | Cost optimization |

---

< [Previous: Workload Placement](./06-workload-placement.md) | [Table of Contents](./README.md) | [Next: Operations](./08-operations.md) >
