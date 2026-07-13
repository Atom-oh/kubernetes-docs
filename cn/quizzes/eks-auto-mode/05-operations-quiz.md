# EKS Auto Mode 运维测验

> **相关文档**: [运维](../../eks-auto-mode/05-operations.md)

## 选择题

### 1. 在业务时间内最大限度减少节点中断的 NodePool Disruption Budget 设置是什么？

- A) `nodes: "100%"`
- B) 带有 schedule 的 `nodes: "0"`
- C) `consolidateAfter: 0s`
- D) `consolidationPolicy: Never`

<details>
<summary>显示答案</summary>

**答案：B) 带有 schedule 的 `nodes: "0"`**

**解释：**
将 `nodes: "0"` 与 Disruption Budget 中的 schedule 一起设置，可以在特定时间窗口内完全防止节点中断。

```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
  budgets:
    # Default: Only 10% of total nodes can be disrupted simultaneously
    - nodes: "10%"

    # Business hours: No disruptions
    - nodes: "0"
      schedule: "0 9-18 * * mon-fri"  # Mon-Fri 9-18
      duration: 9h
```

</details>

### 2. PodDisruptionBudget (PDB) 中的 `minAvailable: 80%` 表示什么？

- A) 最多 80% 的 Pod 可以运行
- B) 至少 80% 的 Pod 必须始终处于运行状态
- C) Pod 保留的概率为 80%
- D) 保护 Pod 80 秒

<details>
<summary>显示答案</summary>

**答案：B) 至少 80% 的 Pod 必须始终处于运行状态**

**解释：**
PDB 的 `minAvailable` 指定必须始终处于运行状态的 Pod 最小数量或百分比。

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  minAvailable: 80%
  selector:
    matchLabels:
      app: web
```

或者，你可以使用 `maxUnavailable`：
```yaml
spec:
  maxUnavailable: 1  # Only 1 Pod can be disrupted simultaneously
```

</details>

### 3. 诊断 Auto Mode 节点问题时，首先应该检查哪个资源？

- A) Pod 日志
- B) NodeClaim 状态
- C) EC2 控制台
- D) CloudWatch 指标

<details>
<summary>显示答案</summary>

**答案：B) NodeClaim 状态**

**解释：**
NodeClaim 是跟踪节点预置过程和状态的关键资源。

```bash
# Check NodeClaim status
kubectl get nodeclaims

# Check details and events
kubectl describe nodeclaim <name>

# Check provisioning failure causes
kubectl get nodeclaims -o yaml | grep -A 10 status
```

典型的故障排查顺序：
1. 检查 NodeClaim 状态
2. 查看 NodePool 配置
3. 验证 IAM 角色/策略
4. 验证子网/安全组

</details>

### 4. do-not-disrupt annotation 的正确用法是什么？

- A) `kubernetes.io/do-not-disrupt: "true"`
- B) `karpenter.sh/do-not-disrupt: "true"`
- C) `eks.amazonaws.com/no-disrupt: "true"`
- D) `node.kubernetes.io/exclude-disruption: "true"`

<details>
<summary>显示答案</summary>

**答案：B) `karpenter.sh/do-not-disrupt: "true"`**

**解释：**
将此 annotation 添加到 Pod 或 Node，可以将其从 Karpenter 的 consolidation 或 drift replacement 中排除。

```yaml
# Apply to Pod
apiVersion: v1
kind: Pod
metadata:
  name: critical-pod
  annotations:
    karpenter.sh/do-not-disrupt: "true"
spec:
  containers:
    - name: app
      image: myapp:latest

# Apply to Node
kubectl annotate node <node-name> karpenter.sh/do-not-disrupt=true
```

</details>

### 5. 在 Auto Mode 集群中监控节点状态的推荐工具是什么？

- A) 仅使用 kubectl top nodes
- B) Container Insights + kubectl 组合
- C) 直接在 EC2 控制台中检查
- D) 仅使用 AWS CLI

<details>
<summary>显示答案</summary>

**答案：B) Container Insights + kubectl 组合**

**解释：**
使用多种工具组合可以实现有效监控。

```bash
# Real-time monitoring
watch -n 5 'echo "=== Pending Pods ===" && \
kubectl get pods -A --field-selector=status.phase=Pending && \
echo "=== Node Status ===" && kubectl get nodes -o wide'

# Check resource usage
kubectl top nodes
kubectl top pods -A

# Check NodePool status
kubectl get nodepools
kubectl describe nodepool <name>
```

Container Insights 指标：
- Node CPU/内存利用率
- Pod 调度延迟
- Container 重启次数

</details>

### 6. 在 Day-2 operations 中，应设置哪个 NodePool 字段来自动化节点更新？

- A) `autoUpdate: true`
- B) `expireAfter` 设置
- C) `updatePolicy: Rolling`
- D) `refreshInterval: 24h`

<details>
<summary>显示答案</summary>

**答案：B) `expireAfter` 设置**

**解释：**
设置 `expireAfter` 可确保节点在指定时间后自动替换，从而应用最新的 AMI 和安全补丁。

```yaml
spec:
  template:
    spec:
      expireAfter: 168h  # Auto-replace after 7 days
```

Day-2 operations 自动化设置：
- `expireAfter`：定期节点替换
- `consolidationPolicy`：成本优化
- Disruption Budget：最大限度减少服务影响

</details>

### 7. 在生产环境中进行滚动更新时，推荐的 Disruption Budget 设置是什么？

- A) 使用 `nodes: "100%"` 进行快速更新
- B) 使用 `nodes: "10%"` 或绝对值进行渐进式更新
- C) 禁用 Disruption Budget
- D) 使用 `nodes: "50%"` 实现中等速度

<details>
<summary>显示答案</summary>

**答案：B) 使用 `nodes: "10%"` 或绝对值进行渐进式更新**

**解释：**
在生产环境中，应在最大限度减少服务影响的同时逐步更新。

```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
  budgets:
    # Default: Gradual replacement at 10%
    - nodes: "10%"

    # Peak hours: More conservative
    - nodes: "1"
      schedule: "0 9-18 * * mon-fri"
      duration: 9h

    # Maintenance window: More aggressive
    - nodes: "30%"
      schedule: "0 2-4 * * sun"
      duration: 2h
```

</details>

### 8. Auto Mode 节点相关 CloudWatch 告警的关键指标是什么？

- A) 仅 EC2 实例状态
- B) Pending Pod 数量、节点预置时间、工作负载可用性
- C) 仅成本指标
- D) 仅网络流量

<details>
<summary>显示答案</summary>

**答案：B) Pending Pod 数量、节点预置时间、工作负载可用性**

**解释：**
Auto Mode 运维中需要监控的关键指标：

| 指标 | 正常范围 | 告警条件 |
|--------|--------------|-----------------|
| Pending Pod 数量 | 0-5 | > 10 for 5 min |
| 节点预置时间 | < 90 sec | > 120 sec |
| 工作负载可用性 | > 99.9% | < 99.5% |
| API 响应时间 | < 200ms | > 500ms |

启用 CloudWatch Container Insights 可自动收集这些指标。

</details>
