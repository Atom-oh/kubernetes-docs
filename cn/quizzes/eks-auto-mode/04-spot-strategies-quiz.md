# EKS Auto Mode Spot 策略测验

> **相关文档**：[Spot 实例策略](../../eks-auto-mode/04-spot-strategies.md)

## 选择题

### 1. 哪种做法能扩大可选的兼容 Spot 容量范围？

- A) 只在一个可用区使用一种实例类型
- B) 允许使用多种兼容的实例类型、大小、架构和可用区
- C) 要求额外架构使用不兼容的镜像
- D) 始终只选择价格最低的实例类型

<details>
<summary>显示答案</summary>

**答案：B) 允许使用多种兼容的实例类型、大小、架构和可用区**

**说明：**
Spot 容量池按实例类型和可用区组合划分。多样化配置会增加可选项，但不会让中断彼此独立；仅仅列出两种架构也不会使实际容量翻倍。应先验证镜像、依赖项和性能配置是否兼容。

```yaml
requirements:
- key: eks.amazonaws.com/instance-category
  operator: In
  values:
  - m
  - c
  - r
  - i
  - d
- key: eks.amazonaws.com/instance-generation
  operator: Gt
  values:
  - '4'
- key: eks.amazonaws.com/instance-size
  operator: In
  values:
  - large
  - xlarge
  - 2xlarge
- key: kubernetes.io/arch
  operator: In
  values:
  - amd64
  - arm64
- key: karpenter.sh/capacity-type
  operator: In
  values:
  - spot
```

这只是 requirements 片段，并不是完整的 NodePool。

</details>

### 2. 在这些示例中，哪个标签用于区分 Spot 和 On-Demand 容量？

- A) node.kubernetes.io/capacity-type
- B) karpenter.sh/capacity-type
- C) eks.amazonaws.com/instance-type
- D) karpenter.k8s.aws/spot-or-ondemand

<details>
<summary>显示答案</summary>

**答案：B) karpenter.sh/capacity-type**

**说明：**
可在 NodePool requirements 或 Pod 选择条件中使用 `karpenter.sh/capacity-type`。preferred affinity 不会强制使用 Spot、预留备用节点，也不会设定固定的购买选项比例。

```yaml
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      preference:
        matchExpressions:
        - key: karpenter.sh/capacity-type
          operator: In
          values:
          - spot
```

如需强制配置基准容量，应在另一个工作负载中使用兼容的硬性 selector 或 required affinity。Downward API 中的 `spec.nodeName` 是节点名称，不是表示 Spot 的布尔值。

</details>

### 3. 应如何理解 EC2 Spot 停止或终止通知？

- A) 每个 Pod 都保证有 30 秒
- B) 通常为两分钟，但通知尽力而为
- C) 每个 Pod 都保证有五分钟
- D) 可以通过 preStop 请求延长十分钟

<details>
<summary>显示答案</summary>

**答案：B) 通常为两分钟，但通知尽力而为**

**说明：**
EC2 通常会在停止或终止实例前两分钟发出中断通知，但该通知尽力而为；休眠的开始行为则不同。Kubernetes 的检测、驱逐和应用处理都会占用这段时间。Pod 宽限期和 preStop hook 都不能延长 EC2 截止时间；休眠 90 秒也不等于检查点或优雅关闭实现。应使用定期持久化检查点、幂等恢复机制，并测试应用对信号的处理。

</details>

### 4. 依赖可中断容量前，哪种模式最需要重新设计？

- A) 经验证可重试的幂等批处理任务
- B) 已复制且经过故障转移测试的无状态服务
- C) 没有恢复路径、唯一状态存于本地存储的关键单实例数据库
- D) 能容忍延迟并可重试的开发任务

<details>
<summary>显示答案</summary>

**答案：C) 没有恢复路径、唯一状态存于本地存储的关键单实例数据库**

**说明：**
这种单实例模式可能导致服务不可用，并丢失唯一状态。使用 On-Demand 也不会让节点本地存储变得持久，或消除维护和故障风险。数据库、队列和长时间运行的任务都需要结合具体架构评估，不能仅凭工作负载名称一概而论。

</details>

### 5. 在一个混合容量的 NodePool 中，如何让 Spot 优先被选用？

- A) 设置 spotPriority: high
- B) 允许 Spot 和 On-Demand，由 Auto Mode 按符合条件的容量优先级进行选择
- C) 设置 capacityPriority: spot
- D) 使用 weight 精确预留 80% 的 Spot 节点

<details>
<summary>显示答案</summary>

**答案：B) 允许 Spot 和 On-Demand，由 Auto Mode 按符合条件的容量优先级进行选择**

**说明：**
允许这两种容量类型即可。数组顺序和 weight 不会决定该池内的容量百分比。如果允许且存在合适的预留容量，其优先级高于 Spot；Spot 的优先级高于 On-Demand。实际可用性仍受容量和约束影响。

单独配置两个 NodePool，可通过 weight 影响置备优先级：

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot-first
spec:
  weight: 100
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - c
        - m
        - r
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: spot-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        capacity-example: spot-lab
        capacity-strategy: spot-preferred
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ondemand-fallback
spec:
  weight: 10
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - c
        - m
        - r
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: spot-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        capacity-example: spot-lab
        capacity-strategy: spot-preferred
  limits:
    cpu: '100'
    memory: 400Gi
```

两个池使用共同标签和实验用 taint。需要回退能力的工作负载必须容忍该 taint，并匹配这两个池；若将 Pod 固定到仅限 Spot 的池名，就无法回退。weight 不会迁移已调度的 Pod，也不保证立即获得回退容量。

</details>

### 6. AWS 公布的 EC2 Spot 折扣幅度是多少？

- A) 保证节省 30–40%
- B) 保证节省 50–60%
- C) 相比 On-Demand 最高可达 90%，但不保证整个工作负载都能节省这些费用
- D) 保证节省 95% 或更多

<details>
<summary>显示答案</summary>

**答案：C) 相比 On-Demand 最高可达 90%，但不保证整个工作负载都能节省这些费用**

**说明：**
实际价格以及有用工作量的成本取决于实例类型、可用区、时段、恢复方式和其他费用。Auto Mode 管理费是在 EC2 价格之外另计。下面保留原教学示例表，但其中数据未经验证：

| 先前的示例 | 未验证的数值 |
|---|---|
| Spot | 70–90% |
| Graviton/ARM | 约 20% |
| Spot + Graviton | 最高 90% |

对比基线和测量方法均未确定。不要将这些百分比相加，也不要把它们视为保证的节省额。Advisor 数据是可能延迟的过去一个月汇总；请使用可用区级价格历史或实际账单，并避免重复计算恢复所需时长的费用。

</details>
