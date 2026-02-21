# Cost Optimization

< [Previous: Workload Placement](./06-workload-placement.md) | [Table of Contents](./README.md) | [Next: Operations](./08-operations.md) >

> **Supported Versions**: EKS 1.31+, nodeadm 0.1+
> **Last Updated**: February 2025

This document covers cost optimization strategies for EKS Hybrid Nodes environments, including on-premises vs cloud cost comparisons and workload distribution recommendations.

## On-Premises GPU vs Cloud GPU Cost Comparison

### Comparison Target

Comparing on-premises servers and AWS cloud instances based on identical specs (8x NVIDIA H200 141GB HBM3e). The H200 offers 76% more HBM memory (80GB → 141GB) and 43% higher memory bandwidth (3.35TB/s → 4.8TB/s) compared to the H100, delivering up to 2x faster LLM inference performance.

| Item | On-Premises (e.g., DGX H200) | AWS p5en.48xlarge |
|------|------------------------------|-------------------|
| GPU | 8x H200 141GB HBM3e | 8x H200 141GB HBM3e |
| GPU Memory Total | 1,128 GB | 1,128 GB |
| vCPU / RAM | 112 cores / 2TB | 192 vCPUs / 2,048 GB |
| Network | NVLink + InfiniBand 400Gb/s | EFA 3200 Gbps (Gen5 PCIe) |

### Server Component Cost Breakdown (8x H200 SXM Server)

| Component | Details | Estimated Cost |
|-----------|---------|---------------|
| **GPU** | 8x NVIDIA H200 141GB SXM (~$27K-$30K each, HBM3e premium over H100) | ~$220,000 |
| **System memory** | 2TB DDR5 RDIMM (32x 64GB, reflecting DDR5 price surge) | ~$20,000 |
| **CPU** | 2x Intel Xeon Platinum 8480C (56C) | ~$10,000 |
| **NVSwitch + interconnect** | 4x NVSwitch + NVLink fabric (7.2TB/s bidirectional) | ~$35,000 |
| **Storage** | NVMe SSD (OS 2x 1.9TB + data 8x 3.84TB) | ~$15,000 |
| **Chassis + PSU + cooling** | Server chassis, power supplies, fans/heatsinks (TDP 700W/GPU) | ~$15,000 |
| **Networking** | ConnectX-7 400Gb/s NIC × 10 | ~$10,000 |
| **OEM margin + assembly** | Manufacturer margin and integration testing | ~$75,000 |
| **Total** | | **~$400,000** |

> **Price Sources**:
> - GPU: H200 SXM with HBM3e 141GB commands a premium over H100 ($20-$23K). 2025-2026 market price estimated at $27K-$30K (industry estimates)
> - DDR5 memory: DRAMeXchange (Feb 2026) reports sustained DDR5 RDIMM price increases. 64GB RDIMM modules ~$400-$600 (up ~60-100% from $200-$300 in 2024)
> - Full server reference: NVIDIA DGX H200 sell price ~$350K-$450K (up from DGX H100 $270K), OEM server market range $380K-$500K
> - H200 TDP is the same as H100 at 700W/GPU (SXM form factor)

### Monthly TCO Calculation

Monthly Total Cost of Ownership (TCO) based on 3-year amortization.

| Cost Component | Calculation Basis | Monthly Cost |
|---------------|-------------------|-------------|
| **Hardware amortization** | ~$400,000 server price ÷ 36 months | $11,111 |
| **Power** | ~10kW consumption × 730h × $0.10/kWh | $730 |
| **Cooling (PUE 1.3)** | Power cost × 0.3 (PUE overhead) | $219 |
| **Data center space** | Rack space allocation (pro-rated from 42U rack) | $1,500 |
| **Network circuit** | Dedicated/internet line allocation | $500 |
| **Operations staff** | Infra engineer partial FTE allocation | $3,000 |
| **Maintenance/warranty** | ~15% of hardware price/year ÷ 12 | $5,000 |
| **Total** | | **~$22,060** |

> **Key Assumptions**:
> - Server price ~$400,000 is the 2025-2026 estimated market price for 8x H200 SXM servers, reflecting HBM3e and DDR5 memory price increases
> - Power rate $0.10/kWh is the US commercial electricity average (EIA 2024 range: $0.08-$0.13)
> - PUE 1.3 assumes a modern data center, better than the Uptime Institute 2024 global average of 1.55
> - Operations staff assumes 1 dedicated infra engineer ($150K/year) shared across 10 servers
> - **These figures are illustrative examples; actual costs vary significantly by region, power rates, and data center contract terms**

### AWS Cost Breakdown

| Item | Source | Cost |
|------|--------|------|
| **p5en.48xlarge On-Demand** | AWS EC2 Pricing API (us-east-1, Feb 2026 query) | $63.30/hour |
| **Monthly (730 hours)** | $63.30 × 730h | **~$46,209** |
| **1-Year RI (No Upfront)** | ~30% discount (GPU instance estimate) | ~$32,346/month |
| **3-Year RI (All Upfront)** | ~50% discount (GPU instance estimate) | ~$23,105/month |

> **Note**:
> - AWS prices are for the us-east-1 region, queried directly from the AWS Pricing API (p5en.48xlarge: $63.2960/hr)
> - For reference, p5.48xlarge (H100) is currently $55.04/hr, significantly reduced from the earlier $98.32
> - RI discount rates are estimates for GPU instances. Check [AWS Pricing Calculator](https://calculator.aws/) for exact RI pricing

### Monthly Cost Summary

| Scenario | On-Premises | AWS On-Demand | AWS 1Y RI | AWS 3Y RI |
|---------|------------|---------------|-----------|-----------|
| Monthly (24/7) | ~$22,060 | ~$46,209 | ~$32,346 | ~$23,105 |
| Hourly equivalent | ~$30.22 | $63.30 | ~$44.31 | ~$31.65 |
| 3-Year total | ~$794,160 | ~$1,663,524 | ~$1,164,456 | ~$831,780 |

### Cost Calculation Script

```bash
#!/bin/bash
# cost-calculator.sh - Hybrid Environment Cost Calculator

# On-premises H200 server monthly cost (TCO-based)
ONPREM_H200_MONTHLY=22060

# AWS p5en.48xlarge pricing scenarios
AWS_P5EN_ON_DEMAND=63.30
AWS_P5EN_1Y_RI=44.31
AWS_P5EN_3Y_RI=31.65

# Enter usage hours
read -p "Monthly GPU usage hours: " HOURS

# Calculate costs
AWS_OD=$(echo "$AWS_P5EN_ON_DEMAND * $HOURS" | bc)
AWS_1Y=$(echo "$AWS_P5EN_1Y_RI * $HOURS" | bc)
AWS_3Y=$(echo "$AWS_P5EN_3Y_RI * $HOURS" | bc)

echo ""
echo "=== Monthly Cost Comparison (${HOURS}h usage) ==="
echo "On-Premises H200 (TCO):        \$${ONPREM_H200_MONTHLY}"
echo "AWS p5en.48xlarge On-Demand:    \$${AWS_OD}"
echo "AWS p5en.48xlarge 1Y RI:        \$${AWS_1Y}"
echo "AWS p5en.48xlarge 3Y RI:        \$${AWS_3Y}"
echo ""

# Calculate break-even points
BE_OD=$(echo "$ONPREM_H200_MONTHLY / $AWS_P5EN_ON_DEMAND" | bc)
BE_1Y=$(echo "$ONPREM_H200_MONTHLY / $AWS_P5EN_1Y_RI" | bc)
BE_3Y=$(echo "$ONPREM_H200_MONTHLY / $AWS_P5EN_3Y_RI" | bc)
echo "=== Break-Even Points ==="
echo "vs On-Demand: ${BE_OD} hours/month ($(echo "scale=0; $BE_OD * 100 / 730" | bc)% utilization)"
echo "vs 1Y RI:     ${BE_1Y} hours/month ($(echo "scale=0; $BE_1Y * 100 / 730" | bc)% utilization)"
echo "vs 3Y RI:     ${BE_3Y} hours/month ($(echo "scale=0; $BE_3Y * 100 / 730" | bc)% utilization)"
```

## Break-Even Analysis

Break-even points against on-premises by AWS pricing scenario:

| AWS Scenario | Hourly Cost | Break-Even | Min. Utilization |
|-------------|------------|------------|-----------------|
| On-Demand | $63.30 | ~349 hours/month | ~48% |
| 1-Year RI | ~$44.31 | ~498 hours/month | ~68% |
| 3-Year RI | ~$31.65 | ~697 hours/month | ~95% |

> **Interpretation**: With H200 pricing, on-premises becomes cheaper than On-Demand at 48% utilization, but requires 95%+ utilization to beat 3-Year RI pricing. Compared to H100, AWS cloud pricing has dropped significantly, making **cloud cost-competitiveness much stronger when RI/Savings Plans are applied**.

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
