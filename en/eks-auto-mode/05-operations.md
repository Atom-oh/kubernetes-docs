# Operations and Management

> **Supported Versions**: EKS 1.29+, EKS Auto Mode GA
> **Last Updated**: February 2025

This guide covers operational aspects of EKS Auto Mode including disruption budgets, rolling replacement, monitoring, troubleshooting, and security best practices.

---

## Disruption Budget Settings

Configure budgets for safe node replacement.

```yaml
# disruption-budget.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: production-pool
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
      # Default: only 10% of total nodes disrupted simultaneously
      - nodes: "10%"

      # Business hours: minimize disruptions
      - nodes: "1"
        schedule: "0 9-18 * * mon-fri"  # Mon-Fri 9-18
        duration: 9h

      # Weekends: allow more aggressive consolidation
      - nodes: "30%"
        schedule: "0 0 * * sat-sun"
        duration: 48h

      # Emergency maintenance window: no disruptions
      - nodes: "0"
        schedule: "0 0 1 * *"  # 1st of each month
        duration: 24h
```

---

## Rolling Replacement Strategy

```yaml
# rolling-replacement-strategy.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: rolling-replacement
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      # Node expiration time
      expireAfter: 168h  # 7 days
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 2m
    budgets:
      # Limit concurrent disrupted nodes for sequential replacement
      - nodes: "1"
```

### Node Replacement Strategy Comparison

| Strategy | Use Case | Configuration | Trade-offs |
|----------|----------|---------------|------------|
| **Rolling (Conservative)** | Production critical | `nodes: "1"` | Slower but safer |
| **Rolling (Moderate)** | Standard production | `nodes: "10%"` | Balanced approach |
| **Aggressive** | Dev/Test, batch | `nodes: "30%"` | Faster but riskier |
| **Scheduled** | Maintenance windows | Time-based budgets | Predictable disruption |

### When to Use Each Strategy

- **Rolling (Conservative)**: Stateful workloads, databases, critical APIs
- **Rolling (Moderate)**: Standard web services, microservices
- **Aggressive**: CI/CD runners, batch processing, dev environments
- **Scheduled**: Compliance requirements, planned maintenance

---

## Integration with PodDisruptionBudget

```yaml
# pdb-example.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
spec:
  # Minimum available Pods
  minAvailable: 3
  # Or maximum unavailable Pods
  # maxUnavailable: 1
  selector:
    matchLabels:
      app: web-app
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 5
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
        - name: web
          image: nginx:latest
          resources:
            requests:
              cpu: 500m
              memory: 256Mi
      # Graceful shutdown during node replacement
      terminationGracePeriodSeconds: 60
```

### PDB Best Practices

| Workload Type | Replicas | PDB Configuration |
|---------------|----------|-------------------|
| Stateless (3+ replicas) | 3-10 | `minAvailable: N-1` or `maxUnavailable: 1` |
| Stateless (10+ replicas) | 10+ | `maxUnavailable: 10%` |
| Stateful | 3+ | `minAvailable: 2` (maintain quorum) |
| Singleton | 1 | No PDB (or accept disruption) |

---

## Zone Failure Response

### Multi-AZ Deployment Configuration

```yaml
# multi-az-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: high-availability-app
spec:
  replicas: 6
  selector:
    matchLabels:
      app: ha-app
  template:
    metadata:
      labels:
        app: ha-app
    spec:
      # Availability zone distribution
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: ha-app
        # Node distribution
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: ha-app
      containers:
        - name: app
          image: my-app:latest
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
---
# NodePool for guaranteed minimum nodes per zone
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: multi-az-pool
spec:
  template:
    spec:
      requirements:
        - key: topology.kubernetes.io/zone
          operator: In
          values: ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  # Guarantee minimum capacity per zone
  limits:
    cpu: 1000
```

### Availability Zone Failure Response Patterns

| Pattern | Description | Implementation |
|---------|-------------|----------------|
| **Active-Active** | All AZs serve traffic | `topologySpreadConstraints` with `DoNotSchedule` |
| **Active-Standby** | Failover to secondary AZ | Pod anti-affinity + health checks |
| **Capacity Reservation** | Pre-provisioned capacity | On-Demand Capacity Reservations |
| **Overflow** | Burst to other AZs | `ScheduleAnyway` constraints |

---

## CloudWatch Monitoring

EKS Auto Mode automatically sends metrics to CloudWatch.

```bash
# CloudWatch metric namespaces
# - AWS/EKS
# - Karpenter

# Key metrics
# - karpenter_nodes_total: Total node count
# - karpenter_pods_pending: Pending Pod count
# - karpenter_nodeclaims_created: Created NodeClaim count
# - karpenter_nodeclaims_terminated: Terminated NodeClaim count
```

### CloudWatch Dashboard Setup

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "title": "Auto Mode Node Count",
        "metrics": [
          ["Karpenter", "karpenter_nodes_total", "cluster", "my-cluster"]
        ],
        "period": 60
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Pending Pods",
        "metrics": [
          ["Karpenter", "karpenter_pods_pending", "cluster", "my-cluster"]
        ],
        "period": 60
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Node Provisioning Time",
        "metrics": [
          ["Karpenter", "karpenter_nodeclaims_startup_duration_seconds", "cluster", "my-cluster"]
        ],
        "stat": "p99",
        "period": 300
      }
    }
  ]
}
```

---

## kubectl-Based Diagnostics

```bash
# Check NodePool status
kubectl get nodepools
kubectl describe nodepool general-purpose

# Check NodeClaim status (nodes being provisioned)
kubectl get nodeclaims
kubectl describe nodeclaim <name>

# Check node status and labels
kubectl get nodes -o wide -L karpenter.sh/nodepool,karpenter.sh/capacity-type

# Check Pending Pods
kubectl get pods -A --field-selector=status.phase=Pending

# Check events
kubectl get events --sort-by='.lastTimestamp' | grep -E "karpenter|nodepool|nodeclaim"

# Node resource usage
kubectl top nodes

# Pod distribution by node
kubectl get pods -A -o wide | awk '{print $8}' | sort | uniq -c | sort -rn
```

---

## Common Issues and Solutions

### Issue 1: Pod Remains in Pending State

```bash
# Analyze cause
kubectl describe pod <pending-pod>

# Common causes:
# 1. Resource requests too large
# 2. NodePool limits exceeded
# 3. nodeSelector/affinity condition mismatch
# 4. taint/toleration mismatch

# Solution: Check NodePool limits
kubectl get nodepool -o yaml | grep -A5 limits

# Solution: Check nodeSelector conditions
kubectl get pod <pending-pod> -o yaml | grep -A10 nodeSelector
```

### Issue 2: Node Provisioning Failure

```bash
# Check NodeClaim status
kubectl describe nodeclaim <name>

# Check error messages in events
kubectl get events --field-selector reason=FailedProvisioning

# Common causes:
# 1. Instance capacity shortage
# 2. Subnet IP exhaustion
# 3. IAM permission issues
# 4. Security group configuration errors

# Solution: Allow more diverse instance types
# Expand NodePool requirements
```

### Issue 3: Node Consolidation Not Working

```bash
# Check Consolidation status
kubectl get nodeclaims -o custom-columns=\
NAME:.metadata.name,\
NODEPOOL:.metadata.labels.karpenter\\.sh/nodepool,\
PHASE:.status.phase,\
AGE:.metadata.creationTimestamp

# Check PodDisruptionBudget
kubectl get pdb -A

# Solution: Adjust PDB or check budgets settings
```

### Issue 4: Pod Rescheduling Delay After Spot Interrupt

```bash
# Check Spot interrupt events
kubectl get events --sort-by='.lastTimestamp' | grep -i "spot\|interrupt"

# Solutions for fast re-provisioning:
# 1. Allow diverse instance types
# 2. Reduce consolidateAfter time
# 3. Use mixed Spot and On-Demand
```

---

## Security Best Practices

```yaml
# security-best-practices.yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: secure-nodeclass
spec:
  amiFamily: Bottlerocket  # Security-hardened OS

  # IMDSv2 required
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 1  # Block Pod IMDS access
    httpTokens: required

  # EBS encryption
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 100Gi
        volumeType: gp3
        encrypted: true
        kmsKeyId: arn:aws:kms:ap-northeast-2:123456789:key/xxx

  # Use only private subnets
  subnetSelectorTerms:
    - tags:
        kubernetes.io/role/internal-elb: "1"

  # Restrictive security groups
  securityGroupSelectorTerms:
    - tags:
        Type: worker-restricted
---
# Apply Pod Security Standards
apiVersion: v1
kind: Namespace
metadata:
  name: secure-namespace
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/warn: restricted
```

---

## Day-2 Operations Checklist

### Daily Tasks

| Task | Command/Action | Purpose |
|------|----------------|---------|
| Check pending pods | `kubectl get pods -A --field-selector=status.phase=Pending` | Identify scheduling issues |
| Review node health | `kubectl get nodes` | Detect NotReady nodes |
| Check node capacity | `kubectl top nodes` | Monitor resource pressure |
| Review events | `kubectl get events --sort-by='.lastTimestamp'` | Catch warnings/errors |

### Weekly Tasks

| Task | Command/Action | Purpose |
|------|----------------|---------|
| Review node age | `kubectl get nodes --sort-by='.metadata.creationTimestamp'` | Track node freshness |
| Audit NodePool limits | `kubectl get nodepools -o yaml` | Ensure appropriate limits |
| Check consolidation | Review CloudWatch metrics | Verify cost optimization |
| Review Spot usage | Check capacity type distribution | Optimize cost/availability |

### Monthly Tasks

| Task | Command/Action | Purpose |
|------|----------------|---------|
| Review AMI versions | Check node AMI IDs | Security patching |
| Audit security groups | Review NodeClass config | Security compliance |
| Cost analysis | AWS Cost Explorer | Budget tracking |
| Capacity planning | Review usage trends | Scale appropriately |

---

## Operations Automation

### Automated Rotation Alerts

```yaml
# CloudWatch Alarm for old nodes
# Create alarm when nodes exceed age threshold
```

```bash
# Script to check node ages
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.creationTimestamp}{"\n"}{end}' | \
while read name created; do
  age_days=$(( ($(date +%s) - $(date -d "$created" +%s)) / 86400 ))
  if [ $age_days -gt 7 ]; then
    echo "WARNING: Node $name is $age_days days old"
  fi
done
```

### PDB Compliance Monitoring

```bash
# Check PDB status across all namespaces
kubectl get pdb -A -o custom-columns=\
NAMESPACE:.metadata.namespace,\
NAME:.metadata.name,\
MIN-AVAILABLE:.spec.minAvailable,\
MAX-UNAVAILABLE:.spec.maxUnavailable,\
CURRENT:.status.currentHealthy,\
DESIRED:.status.desiredHealthy,\
DISRUPTIONS-ALLOWED:.status.disruptionsAllowed
```

### Capacity Dashboard Queries

Key Prometheus queries for capacity monitoring:

```promql
# Total nodes by NodePool
count(kube_node_labels) by (label_karpenter_sh_nodepool)

# Node CPU utilization by pool
avg(1 - rate(node_cpu_seconds_total{mode="idle"}[5m])) by (node) * on(node) group_left(label_karpenter_sh_nodepool) kube_node_labels

# Pending pods over time
sum(kube_pod_status_phase{phase="Pending"})

# Node age distribution
(time() - kube_node_created) / 86400
```

---

## Operations Summary Checklist

| Area | Checklist Item | Status |
|------|----------------|--------|
| **Configuration** | NodePool limits configured | |
| | Disruption Budget configured | |
| | NodeClass security settings reviewed | |
| **Monitoring** | CloudWatch dashboard created | |
| | Alarms set (Pending Pod, provisioning failures) | |
| | Cost monitoring configured | |
| **Availability** | PodDisruptionBudget configured | |
| | Multi-AZ distribution verified | |
| | Spot/On-Demand mix ratio reviewed | |
| **Cost** | Spot instance ratio optimized | |
| | Consolidation policy reviewed | |
| | Resource requests/limits appropriateness reviewed | |

---

< [Previous: Spot Strategies](./04-spot-strategies.md) | [Table of Contents](./README.md) | [Next: Cost Management](./06-cost-management.md) >
