# Node Lifecycle Management

> **Supported Versions**: EKS 1.29+, EKS Auto Mode GA
> **Last Updated**: July 3, 2026

This guide covers node lifecycle management in EKS Auto Mode, including expiration policies, AMI management, drift detection, and node freshness monitoring.

---

## Node Expiration Policies (expireAfter)

The `expireAfter` field controls how long a node can run before being automatically replaced.

### How expireAfter Works

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: with-expiration
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      # Set maximum node lifetime
      expireAfter: 168h  # Auto-replace after 7 days
```

### Expiration Process

1. Node reaches `expireAfter` age
2. Controller marks node for replacement
3. New node provisioned with fresh configuration
4. Workloads migrated respecting PDBs
5. Old node drained and terminated

### Auto Mode's 21-Day Maximum Node Lifetime

EKS Auto Mode uses the Karpenter-based `expireAfter` default, and nodes are automatically replaced once they reach a maximum age of **21 days (504h)** after creation. You can set `expireAfter` shorter than 21 days for more frequent replacement, but setting it longer than 21 days has no effect — Auto Mode enforces 21 days as the hard ceiling. Unlike managed node groups or self-managed Karpenter, nodes cannot be kept indefinitely.

If you run workloads that hold state for extended periods (services with long cache warm-up times, stateful workloads relying on local storage, etc.), plan Pod rescheduling and data rebalancing procedures around this 21-day ceiling in advance.

### Recommended expireAfter Values

| Use Case | expireAfter | Rationale |
|----------|-------------|-----------|
| **Security-critical** | 24h - 72h | Frequent patching, compliance requirements |
| **Standard production** | 168h (7 days) | Balance between freshness and stability |
| **Cost-sensitive** | 336h (14 days) | Minimize replacement overhead (within the 21-day ceiling) |
| **Development/Test** | 504h (21 days, maximum) | Maximize node reuse; this is the enforced upper bound |
| **Compliance (PCI/HIPAA)** | 72h - 168h | Meet audit requirements |

### expireAfter Configuration Examples

```yaml
# Security-first configuration
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: security-critical
spec:
  template:
    spec:
      expireAfter: 72h  # 3 days for security compliance
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: secure-nodeclass
---
# Cost-optimized configuration
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-optimized
spec:
  template:
    spec:
      expireAfter: 336h  # 14 days for cost efficiency
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
```

---

## AMI Management Strategy

### How Auto Mode Selects AMIs

EKS Auto Mode automatically selects and manages AMIs based on your NodeClass configuration.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: ami-managed
spec:
  # AMI family selection
  amiFamily: AL2023  # or Bottlerocket
```

### AMI Family Comparison

| Feature | AL2023 | Bottlerocket |
|---------|--------|--------------|
| Base OS | Amazon Linux 2023 | Purpose-built container OS |
| Boot time | ~40-60 seconds | ~20-40 seconds |
| Attack surface | Standard | Minimal (read-only root) |
| Customization | Full (userData) | Limited (settings API) |
| Package manager | dnf | None (immutable) |
| Security updates | Standard patching | Atomic updates |
| Use case | General workloads | Security-focused workloads |

### AMI Family Selection Guidelines

| Workload Type | Recommended AMI | Rationale |
|---------------|-----------------|-----------|
| General web services | AL2023 | Flexibility, familiar tooling |
| Security-critical | Bottlerocket | Minimal attack surface |
| Compliance (PCI/SOC2) | Bottlerocket | Immutable infrastructure |
| GPU workloads | AL2023 | NVIDIA driver support |
| Custom kernel modules | AL2023 | Full OS access |
| Fast scaling | Bottlerocket | Faster boot times |

### Custom AMI Configuration

```yaml
# For specific AMI requirements
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: custom-ami
spec:
  amiFamily: AL2023

  # AMI selection by tags (if using custom AMIs)
  amiSelectorTerms:
    - tags:
        Name: my-custom-eks-ami
        Environment: production
```

---

## AMI Updates and Drift Detection

### How AMI Updates Trigger Drift

When AWS releases new AMIs or you update your NodeClass:

1. **AMI Release**: AWS publishes new EKS-optimized AMI
2. **Drift Detection**: Controller detects AMI version mismatch
3. **Node Marking**: Existing nodes marked as "drifted"
4. **Replacement**: Nodes replaced based on disruption settings

### Drift Detection Triggers

| Change | Triggers Drift | Replacement Speed |
|--------|----------------|-------------------|
| New AMI version | Yes | Based on disruption budget |
| NodeClass AMI family change | Yes | Immediate scheduling |
| Security patch AMI | Yes | Based on disruption budget |
| NodePool requirement change | Yes | Based on consolidation |
| NodeClass block device change | Yes | New nodes only |

### Monitoring Drift Status

```bash
# Check for drifted nodes
kubectl get nodes -o custom-columns=\
NAME:.metadata.name,\
NODEPOOL:.metadata.labels.karpenter\\.sh/nodepool,\
AGE:.metadata.creationTimestamp,\
DRIFT:.metadata.annotations.karpenter\\.sh/drift-hash

# Check NodeClaim drift status
kubectl get nodeclaims -o wide

# Watch for drift events
kubectl get events --sort-by='.lastTimestamp' | grep -i drift
```

### Controlling Drift Replacement

```yaml
# Slow drift replacement for stability
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: controlled-drift
spec:
  template:
    spec:
      expireAfter: 168h
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
    budgets:
      # Slow, controlled replacement
      - nodes: "1"
      # No replacement during business hours
      - nodes: "0"
        schedule: "0 9-17 * * mon-fri"
        duration: 8h
```

---

## Node Freshness Policies and Security Patching

### Why Node Freshness Matters

| Concern | Impact | Mitigation |
|---------|--------|------------|
| **Security patches** | Unpatched vulnerabilities | Short expireAfter |
| **AMI updates** | Missing features/fixes | Enable drift replacement |
| **Configuration drift** | Inconsistent behavior | Regular node rotation |
| **Compliance** | Audit findings | Documented rotation policy |

### Security Patching Strategy

```yaml
# Security-focused NodePool
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: security-patched
spec:
  template:
    spec:
      # Maximum node age for security compliance
      expireAfter: 72h  # 3 days
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: secure-nodeclass
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
      # Allow faster replacement for security patches
      - nodes: "20%"
---
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: secure-nodeclass
spec:
  amiFamily: Bottlerocket  # Security-hardened OS

  metadataOptions:
    httpTokens: required  # IMDSv2 only
    httpPutResponseHopLimit: 1

  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        encrypted: true
        volumeType: gp3
```

---

## Consolidation vs Expiration Trade-offs

### When Each Applies

| Mechanism | Trigger | Purpose | Priority |
|-----------|---------|---------|----------|
| **Consolidation** | Underutilization | Cost optimization | Lower |
| **Expiration** | Age threshold | Security/freshness | Higher |
| **Drift** | Configuration change | Consistency | Highest |

### Interaction Between Mechanisms

```
Node Lifecycle Priority:
1. Drift (immediate) - Configuration mismatch
2. Expiration (scheduled) - Age threshold reached
3. Consolidation (opportunistic) - Underutilization detected
```

### Configuration for Different Priorities

```yaml
# Cost-priority (consolidation aggressive, expiration relaxed)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-priority
spec:
  template:
    spec:
      expireAfter: 336h  # 14 days - relaxed
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m  # Aggressive consolidation
---
# Security-priority (expiration aggressive, consolidation relaxed)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: security-priority
spec:
  template:
    spec:
      expireAfter: 72h  # 3 days - aggressive
  disruption:
    consolidationPolicy: WhenEmpty  # Relaxed consolidation
    consolidateAfter: 10m
```

---

## Monitoring Node Age Distribution

### kubectl-Based Monitoring

```bash
# List nodes with age
kubectl get nodes --sort-by='.metadata.creationTimestamp' \
  -o custom-columns=\
NAME:.metadata.name,\
NODEPOOL:.metadata.labels.karpenter\\.sh/nodepool,\
INSTANCE:.metadata.labels.node\\.kubernetes\\.io/instance-type,\
CREATED:.metadata.creationTimestamp,\
AGE:.metadata.creationTimestamp

# Calculate node ages in days
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.creationTimestamp}{"\n"}{end}' | \
while read name created; do
  age_seconds=$(($(date +%s) - $(date -d "$created" +%s)))
  age_days=$((age_seconds / 86400))
  age_hours=$(((age_seconds % 86400) / 3600))
  echo "$name: ${age_days}d ${age_hours}h"
done
```

### Prometheus/Grafana Monitoring

Key Prometheus queries for node age:

```promql
# Node age in days
(time() - kube_node_created) / 86400

# Nodes older than 7 days
count(((time() - kube_node_created) / 86400) > 7)

# Average node age by NodePool
avg((time() - kube_node_created) / 86400) by (label_karpenter_sh_nodepool)

# Node age distribution histogram
histogram_quantile(0.50,
  sum(rate(kube_node_created_bucket[24h])) by (le)
)
```

### Alerting Rules

```yaml
# Prometheus alerting rules for node age
groups:
  - name: node-lifecycle
    rules:
      - alert: NodeTooOld
        expr: (time() - kube_node_created) / 86400 > 10
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Node {{ $labels.node }} is older than 10 days"

      - alert: NodeAgeDistributionSkewed
        expr: stddev((time() - kube_node_created) / 86400) > 3
        for: 4h
        labels:
          severity: info
        annotations:
          summary: "Node ages are highly variable, check rotation"
```

### Node Age Dashboard

Create a Grafana dashboard with:

| Panel | Query | Visualization |
|-------|-------|---------------|
| Node count by age bucket | Histogram of node ages | Bar chart |
| Average age by NodePool | `avg by (nodepool)` | Stat panel |
| Oldest nodes | Top N by age | Table |
| Nodes expiring soon | Age close to expireAfter | Alert list |
| Replacement rate | NodeClaims created/terminated | Time series |

---

## Node Lifecycle Best Practices

| Practice | Recommendation |
|----------|----------------|
| Set expireAfter | Always configure, default 7 days |
| Use Bottlerocket for security | Minimal attack surface |
| Monitor node ages | Alert on nodes > expected age |
| Respect PDBs | Ensure graceful workload migration |
| Stagger replacements | Use disruption budgets |
| Track AMI versions | Monitor for security patches |

---

< [Previous: Cost Management](./06-cost-management.md) | [Table of Contents](./README.md) | [Next: Workload Optimization](./08-workload-optimization.md) >
