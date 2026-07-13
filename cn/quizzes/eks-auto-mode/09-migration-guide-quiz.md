# EKS Auto Mode 迁移指南测验

> **相关文档**: [迁移指南](../../eks-auto-mode/09-migration-guide.md)

## 选择题

### 1. 从 managed node groups 迁移到 Auto Mode 时，第一步是什么？

- A) 立即删除现有 node groups
- B) 分析当前状态（检查节点资源使用情况、工作负载分布）
- C) 创建 Auto Mode NodePool
- D) Drain 所有 Pods

<details>
<summary>显示答案</summary>

**答案：B) 分析当前状态（检查节点资源使用情况、工作负载分布）**

**解释：**
迁移的第一步是全面分析当前环境。

**迁移步骤：**
1. **分析当前状态** - 检查 node groups、资源使用情况、工作负载分布
2. 启用 Auto Mode
3. 配置 NodePool
4. 迁移工作负载
5. 缩容现有 node groups
6. 删除现有 node groups
7. 验证并优化

```bash
# Check current node groups
eksctl get nodegroup --cluster my-cluster

# Analyze node resource usage
kubectl top nodes

# Check workload distribution
kubectl get pods -A -o wide | awk '{print $8}' | sort | uniq -c
```

</details>

### 2. 迁移期间如何允许现有 node groups 与 Auto Mode 共存？

- A) 不可能，必须只能按顺序进行
- B) 使用 nodeSelector 分离工作负载
- C) 需要单独的 cluster
- D) 需要 AWS Support 工单

<details>
<summary>显示答案</summary>

**答案：B) 使用 nodeSelector 分离工作负载**

**解释：**
在共存期间，使用 nodeSelector 和 affinity 来分离工作负载。

```yaml
# Workloads pinned to existing node groups
apiVersion: apps/v1
kind: Deployment
metadata:
  name: legacy-critical-app
spec:
  template:
    spec:
      nodeSelector:
        eks.amazonaws.com/nodegroup: old-nodegroup

---
# Workloads that can be migrated to Auto Mode
apiVersion: apps/v1
kind: Deployment
metadata:
  name: migrated-app
spec:
  template:
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: karpenter.sh/nodepool
                    operator: Exists
```

</details>

### 3. 渐进式迁移工作负载的推荐顺序是什么？

- A) Production -> Staging -> Development
- B) Development -> Staging -> Production（先迁移非关键工作负载）
- C) 同时迁移所有工作负载
- D) 随机顺序

<details>
<summary>显示答案</summary>

**答案：B) Development -> Staging -> Production（先迁移非关键工作负载）**

**解释：**
渐进式迁移可以最大限度降低风险。

```yaml
# Step 1: Migrate non-critical workloads
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dev-app
spec:
  template:
    spec:
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              preference:
                matchExpressions:
                  - key: node-type
                    operator: In
                    values: ["auto-mode"]
```

**迁移顺序：**
1. Development 环境工作负载
2. Staging 工作负载
3. Production 非关键工作负载
4. Production 关键工作负载

</details>

### 4. 需要回滚时，步骤顺序是什么？

- A) 删除并重新创建 cluster
- B) 删除 NodePool -> 扩容现有 node groups -> 迁移工作负载
- C) 联系 AWS Support
- D) 仅禁用 Auto Mode

<details>
<summary>显示答案</summary>

**答案：B) 删除 NodePool -> 扩容现有 node groups -> 迁移工作负载**

**解释：**
回滚按相反顺序进行。

```bash
#!/bin/bash
# rollback.sh

# 1. Disable Auto Mode NodePool
kubectl delete nodepool migration-pool

# 2. Scale up existing node groups
eksctl scale nodegroup \
    --cluster my-cluster \
    --name old-nodegroup \
    --nodes 10 \
    --nodes-min 3

# 3. Migrate workloads back to existing nodes
kubectl patch deployment migrated-app -p '
{
  "spec": {
    "template": {
      "spec": {
        "nodeSelector": {
          "eks.amazonaws.com/nodegroup": "old-nodegroup"
        },
        "affinity": null
      }
    }
  }
}'

# 4. Drain Auto Mode Pods
for node in $(kubectl get nodes -l karpenter.sh/nodepool=migration-pool -o name); do
    kubectl drain $node --ignore-daemonsets --delete-emptydir-data
done
```

</details>

### 5. 渐进式缩容现有 node groups 的推荐方法是什么？

- A) 立即缩容到 0
- B) 每次缩容 50%，并进行稳定性检查
- C) 每次仅缩容 1 个
- D) 同时 Drain 所有节点

<details>
<summary>显示答案</summary>

**答案：B) 每次缩容 50%，并进行稳定性检查**

**解释：**
渐进式缩容可以最大限度降低对服务的影响。

```bash
#!/bin/bash
CLUSTER="my-cluster"
NODEGROUP="old-nodegroup"
CURRENT_SIZE=$(eksctl get nodegroup --cluster $CLUSTER --name $NODEGROUP -o json | jq -r '.[0].DesiredCapacity')

# Scale down by 50%
while [ $CURRENT_SIZE -gt 0 ]; do
    NEW_SIZE=$((CURRENT_SIZE / 2))
    if [ $NEW_SIZE -lt 1 ]; then
        NEW_SIZE=0
    fi

    echo "Scaling from $CURRENT_SIZE to $NEW_SIZE"
    eksctl scale nodegroup --cluster $CLUSTER --name $NODEGROUP \
        --nodes $NEW_SIZE --nodes-min 0

    # Wait for stabilization
    sleep 300

    # Check workload status
    kubectl get pods -A --field-selector=status.phase=Pending

    CURRENT_SIZE=$NEW_SIZE
done
```

</details>

### 6. 迁移期间哪一项不是需要监控的关键指标？

- A) Pending Pod 数量
- B) Node provisioning time
- C) EC2 instance cost
- D) Workload availability

<details>
<summary>显示答案</summary>

**答案：C) EC2 instance cost**

**解释：**
迁移期间，服务稳定性是最高优先级，因此需要监控以下指标。

| 指标 | 正常范围 | 告警条件 |
|--------|--------------|-----------------|
| Pending Pod 数量 | 0-5 | > 10 for 5 min |
| 节点预置时间 | < 90 sec | > 120 sec |
| 工作负载可用性 | > 99.9% | < 99.5% |
| API 响应时间 | < 200ms | > 500ms |

成本会在迁移完成后的优化阶段进行检查。

```bash
# Real-time monitoring
watch -n 5 'echo "=== Pending Pods ===" && \
kubectl get pods -A --field-selector=status.phase=Pending && \
echo "=== Node Status ===" && kubectl get nodes -o wide'
```

</details>

### 7. 迁移完成后，不属于验证项的是哪一项？

- A) 验证所有工作负载正常运行
- B) 验证 Auto Mode 节点上的 Pod 分布
- C) 完全删除现有 node groups
- D) 验证 NodePool 状态

<details>
<summary>显示答案</summary>

**答案：C) 完全删除现有 node groups**

**解释：**
在验证阶段，应保留现有 node groups，以保留回滚选项。确认稳定性后再进行删除。

**验证清单：**
1. 验证所有 Pods 处于 Running 状态
2. 验证 Auto Mode 节点上的工作负载分布
3. NodePool 和 NodeClaim 状态正常
4. 应用程序性能测试
5. 日志和指标收集正常
6. **确认稳定运行一段时间（1-2 周）后删除现有 node groups**

</details>

### 8. 从直接使用 Karpenter 的 cluster 迁移到 Auto Mode 时，需要注意什么？

- A) 可以直接迁移
- B) 可能与现有 Karpenter 资源冲突，移除 Karpenter 后再迁移
- C) 推荐同时运行
- D) 会产生额外成本

<details>
<summary>显示答案</summary>

**答案：B) 可能与现有 Karpenter 资源冲突，移除 Karpenter 后再迁移**

**解释：**
Auto Mode 在内部使用 Karpenter，因此可能与现有自管理 Karpenter 冲突。

**迁移流程：**
1. 备份现有 Karpenter NodePool 配置
2. 将 Karpenter 管理的工作负载临时迁移到 managed node groups
3. 移除自管理 Karpenter
4. 启用 Auto Mode
5. 配置 Auto Mode NodePool（参考备份）
6. 迁移工作负载

```bash
# Verify before removing Karpenter
kubectl get nodepools
kubectl get nodeclaims
kubectl get nodes -l karpenter.sh/nodepool

# Remove Karpenter
helm uninstall karpenter -n karpenter
kubectl delete namespace karpenter
```

</details>
