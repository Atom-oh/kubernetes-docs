# Migrating from Managed Node Groups to Auto Mode

> **Supported Versions**: EKS 1.29+, EKS Auto Mode GA
> **Last Updated**: July 3, 2026

This guide covers how to migrate from existing EKS Managed Node Groups to Auto Mode, including step-by-step instructions, coexistence strategies, and important cautions.

---

## Migration Overview

![A seven-step top-to-bottom migration path for moving an Amazon EKS cluster onto Auto Mode: analyze the current state, enable Auto Mode, configure NodePools, migrate workloads, scale down and then delete the existing managed node groups, and finish with validation and optimization.](../../assets/diagrams/rendered/en-eks-auto-mode-09-migration-guide-0.svg)

---

## Step 1: Analyze Current State

Before migration, thoroughly analyze your current cluster configuration.

```bash
# Check current node groups
eksctl get nodegroup --cluster my-cluster

# Analyze node resource usage
kubectl top nodes

# Check workload distribution
kubectl get pods -A -o wide | awk '{print $8}' | sort | uniq -c

# Nodes by current instance type
kubectl get nodes -o custom-columns=\
NAME:.metadata.name,\
TYPE:.metadata.labels.node\\.kubernetes\\.io/instance-type,\
ZONE:.metadata.labels.topology\\.kubernetes\\.io/zone

# Check for node selectors in deployments
kubectl get deployments -A -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name}: {.spec.template.spec.nodeSelector}{"\n"}{end}'

# Check for node affinities
kubectl get deployments -A -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name}: {.spec.template.spec.affinity.nodeAffinity}{"\n"}{end}'
```

### Pre-Migration Checklist

| Item | Check | Notes |
|------|-------|-------|
| EKS version | >= 1.29 | Required for Auto Mode |
| Node group instance types | Document all | Map to NodePool requirements |
| Custom AMIs | Document | May need NodeClass config |
| User data scripts | Review | Ensure compatibility |
| IAM roles | Document | Auto Mode creates new roles |
| Security groups | Document | Configure in NodeClass |
| Tags | Document | Add to NodeClass |
| Node selectors in workloads | Identify | May need updates |

---

## Step 2: Enable Auto Mode

Enable Auto Mode on your existing cluster.

```bash
# 1. Enable Auto Mode
aws eks update-cluster-config \
    --name my-cluster \
    --compute-config enabled=true,nodePools=general-purpose,nodePools=system

# 2. Check activation status
aws eks describe-cluster --name my-cluster \
    --query 'cluster.computeConfig'

# 3. Wait for update to complete
aws eks wait cluster-active --name my-cluster

# 4. Verify NodePools are created
kubectl get nodepools
```

---

## Step 3: Configure Custom NodePools

Create NodePools that match your current node group configurations.

```yaml
# custom-nodepools.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: migrated-workloads
spec:
  template:
    metadata:
      labels:
        migration: auto-mode
    spec:
      requirements:
        # Instance types similar to existing node groups
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r"]
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["large", "xlarge", "2xlarge"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
```

### Mapping Node Groups to NodePools

| Node Group Config | NodePool Equivalent |
|-------------------|---------------------|
| Instance types | `karpenter.k8s.aws/instance-category`, `instance-size` |
| Capacity type | `karpenter.sh/capacity-type` |
| Labels | `template.metadata.labels` |
| Taints | `template.spec.taints` |
| Scaling limits | `spec.limits` |
| Subnet tags | NodeClass `subnetSelectorTerms` |
| Security groups | NodeClass `securityGroupSelectorTerms` |
| AMI type | NodeClass `amiFamily` |

---

## Step 4: Migrate Workloads

Gradually move workloads from existing node groups to Auto Mode nodes.

```bash
# Apply cordon to existing nodes (prevent new Pod scheduling)
kubectl cordon -l eks.amazonaws.com/nodegroup=old-nodegroup

# Gradually drain Pods
for node in $(kubectl get nodes -l eks.amazonaws.com/nodegroup=old-nodegroup -o name); do
    kubectl drain $node --ignore-daemonsets --delete-emptydir-data
    sleep 60  # Wait time between each node
done
```

### Safe Migration Script

```bash
#!/bin/bash
# migrate-workloads.sh

NODE_GROUP="old-nodegroup"
DRAIN_INTERVAL=60

# Get nodes in the old node group
NODES=$(kubectl get nodes -l eks.amazonaws.com/nodegroup=$NODE_GROUP -o name)

echo "Starting migration of node group: $NODE_GROUP"
echo "Found $(echo "$NODES" | wc -l) nodes to migrate"

# Cordon all nodes first
for node in $NODES; do
    echo "Cordoning $node..."
    kubectl cordon $node
done

echo "All nodes cordoned. Starting drain process..."

# Drain nodes one by one
for node in $NODES; do
    echo "Draining $node..."
    kubectl drain $node \
        --ignore-daemonsets \
        --delete-emptydir-data \
        --timeout=300s

    if [ $? -ne 0 ]; then
        echo "WARNING: Failed to drain $node, continuing..."
    fi

    echo "Waiting ${DRAIN_INTERVAL}s before next node..."
    sleep $DRAIN_INTERVAL
done

echo "Migration complete. Verify with: kubectl get pods -A -o wide"
```

---

## Step 5: Scale Down Existing Node Groups

After workloads are migrated, scale down the old node groups.

```bash
# Scale down node group
eksctl scale nodegroup \
    --cluster my-cluster \
    --name old-nodegroup \
    --nodes 0 \
    --nodes-min 0

# Verify nodes are terminating
kubectl get nodes -l eks.amazonaws.com/nodegroup=old-nodegroup -w
```

---

## Step 6: Delete Existing Node Groups

Once confirmed that all workloads are running on Auto Mode nodes, delete the old node groups.

```bash
# Delete node group
eksctl delete nodegroup \
    --cluster my-cluster \
    --name old-nodegroup

# Verify deletion
eksctl get nodegroup --cluster my-cluster
```

---

## Step 7: Validation and Optimization

Validate the migration and optimize configurations.

```bash
# Verify all pods are running
kubectl get pods -A --field-selector=status.phase!=Running

# Check node distribution
kubectl get nodes -o wide -L karpenter.sh/nodepool,karpenter.sh/capacity-type

# Verify resource utilization
kubectl top nodes
kubectl top pods -A

# Check for any pending pods
kubectl get pods -A --field-selector=status.phase=Pending
```

---

## Coexistence Period Operations

During migration, existing node groups and Auto Mode can coexist.

```yaml
# coexistence-config.yaml
# Existing node group workloads
apiVersion: apps/v1
kind: Deployment
metadata:
  name: legacy-app
spec:
  replicas: 3
  template:
    spec:
      # Pin to existing node group
      nodeSelector:
        eks.amazonaws.com/nodegroup: old-nodegroup
      containers:
        - name: app
          image: legacy-app:latest
---
# Auto Mode workloads
apiVersion: apps/v1
kind: Deployment
metadata:
  name: new-app
spec:
  replicas: 3
  template:
    spec:
      # Prefer Auto Mode nodes
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              preference:
                matchExpressions:
                  - key: karpenter.sh/nodepool
                    operator: Exists
      containers:
        - name: app
          image: new-app:latest
```

### Coexistence Best Practices

| Practice | Description |
|----------|-------------|
| Use node selectors | Pin workloads to specific infrastructure |
| Gradual migration | Move workloads in phases |
| Monitor both | Track metrics from both node types |
| Test thoroughly | Validate behavior before full migration |
| Rollback plan | Keep node groups scaled down, not deleted initially |

---

## Migrating from Self-Managed Karpenter (Official kubectl-Based Path)

If you are running **self-managed Karpenter directly** rather than managed node groups, AWS provides an officially supported kubectl-based migration path as an alternative to the node group cutover procedure described above.

### Prerequisites

- Self-managed Karpenter **v1.1 or later** must already be installed on the cluster
- Document your existing Karpenter NodePool/EC2NodeClass configuration

### Migration Steps

1. **Enable Auto Mode**: Enable Auto Mode while leaving the existing Karpenter controller and NodePools in place.

2. **Create a tainted Auto Mode NodePool**: Add a taint so workloads aren't scheduled onto Auto Mode nodes unintentionally.

   ```yaml
   apiVersion: karpenter.sh/v1
   kind: NodePool
   metadata:
     name: auto-mode-migration
   spec:
     template:
       spec:
         taints:
           - key: eks.amazonaws.com/auto-mode
             value: "true"
             effect: NoSchedule
         nodeClassRef:
           group: eks.amazonaws.com
           kind: NodeClass
           name: default
   ```

3. **Add matching tolerations/nodeSelector to workloads**: Add a toleration for the taint above and a `nodeSelector` targeting the Auto Mode NodePool to the workloads you want to migrate.

   ```yaml
   spec:
     template:
       spec:
         tolerations:
           - key: eks.amazonaws.com/auto-mode
             value: "true"
             effect: NoSchedule
         nodeSelector:
           karpenter.sh/nodepool: auto-mode-migration
   ```

4. **Migrate incrementally**: Add the toleration/nodeSelector to one workload group at a time, moving workloads onto Auto Mode nodes while Karpenter-managed nodes and Auto Mode nodes run side by side in the same cluster.

5. **Remove self-managed Karpenter**: Once all workloads are confirmed running on Auto Mode nodes, remove the self-managed Karpenter controller and its associated resources (NodePools, EC2NodeClasses, IAM roles, Helm release, etc.).

This path is intended for clusters already running self-managed Karpenter. If you are migrating directly from managed node groups, follow Steps 1-7 above instead.

---

## Migration Cautions

| Item | Caution | Mitigation |
|------|---------|------------|
| **AMI Compatibility** | Auto Mode supports only AL2023 or Bottlerocket | Test workloads on new AMI |
| **User Data** | Verify existing bootstrap script compatibility | Review and test userData |
| **IAM Role** | Auto Mode IAM role is auto-created | Verify permissions for workloads |
| **Security Groups** | Reconfigure in NodeClass | Document and replicate rules |
| **Tags** | Reflect existing tag policies in NodeClass | Audit and add tags |
| **Monitoring** | New metrics collection setup required | Update dashboards and alerts |
| **Node Selectors** | Workloads with `eks.amazonaws.com/nodegroup` won't schedule | Update selectors |
| **Persistent Volumes** | EBS volumes are AZ-specific | Plan for volume migration |

### Common Migration Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| Pods not scheduling | Pending state | Update node selectors, tolerations |
| Application errors | Runtime failures | Check AMI compatibility |
| Performance degradation | Latency increase | Verify instance types match |
| Cost increase | Higher EC2 bills | Review NodePool limits, Spot config |

---

## Rollback Procedure

If migration issues occur, you can rollback.

```bash
# 1. Scale up old node groups
eksctl scale nodegroup \
    --cluster my-cluster \
    --name old-nodegroup \
    --nodes 3 \
    --nodes-min 1 \
    --nodes-max 10

# 2. Uncordon old nodes (if cordoned)
kubectl uncordon -l eks.amazonaws.com/nodegroup=old-nodegroup

# 3. Cordon Auto Mode nodes
kubectl cordon -l karpenter.sh/nodepool

# 4. Drain Auto Mode nodes
for node in $(kubectl get nodes -l karpenter.sh/nodepool -o name); do
    kubectl drain $node --ignore-daemonsets --delete-emptydir-data
done

# 5. Verify workloads are back on old nodes
kubectl get pods -A -o wide

# 6. Optionally disable Auto Mode
aws eks update-cluster-config \
    --name my-cluster \
    --compute-config enabled=false
```

---

## Post-Migration Optimization

After successful migration:

1. **Review NodePool configurations**: Optimize requirements based on actual workload needs
2. **Enable Spot instances**: For suitable workloads to reduce costs
3. **Configure consolidation**: Enable cost optimization through node consolidation
4. **Set up monitoring**: Create dashboards for Auto Mode metrics
5. **Document changes**: Update runbooks and documentation
6. **Train team**: Ensure operations team understands new management model

---

< [Previous: Workload Optimization](./08-workload-optimization.md) | [Table of Contents](./README.md) | [Back to EKS Topics](../README.md) >
