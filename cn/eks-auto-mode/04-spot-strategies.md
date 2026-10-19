# Spot 实例利用策略

> **支持的版本**：EKS Auto Mode GA；示例基准版本为 EKS 1.36
> **最后更新**：2026年9月12日

Spot 以中断和容量不确定性为代价，换取可能更低的 EC2 价格。混合容量、多样化选择和副本可以提升弹性，但任何单一措施都不能保证可用性或节省成本。请使用前面章节中经过审核的账户/上下文和 NodeClass。

这些清单是通过本地架构定义（schema）检查的实验室示例，并非生产环境故障转移测试。它们使用 `spot-lab` 污点/容忍度和显式的节点池选择，以减少无关工作负载意外调度到这些节点的情况。污点不是租户安全边界。应用前请检查副本数和资源限制；这些示例可能会创建产生费用的节点。本次审核未预置 Spot 实例，也未查询客户账单或 EC2 Spot Price History API。

## 混合容量与有意设置的基准容量

下面的节点池允许使用 Spot 和 On-Demand。在一个符合条件的节点池内，Auto Mode 会优先选择允许的容量类型；当 Spot 和 On-Demand 都被允许且有可用容量时，会优先选择 Spot。如果同时允许 `reserved` 且存在合适的预留容量，其优先级更高。数组顺序和 NodePool 权重都不会设定 Spot 占比。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: spot-lab
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: mixed-capacity
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
        - r
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '5'
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
        - on-demand
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
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spot-friendly-app
  namespace: spot-lab
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
      containers:
      - name: app
        image: nginx:1.30.6
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        ports:
        - containerPort: 80
        readinessProbe:
          httpGet:
            path: /
            port: 80
          periodSeconds: 5
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: mixed-capacity
      tolerations:
      - key: spot-lab
        operator: Equal
        value: 'true'
        effect: NoSchedule
```

Pod 的首选亲和性只是偏好，不是要求或预留。它不能保证立即回退到 On-Demand、固定比例，或在中断窗口内完成替换。现有容量、约束、配额和实际可用性仍然会产生影响。

如果需要一个必须使用 On-Demand 的独立基准 Deployment，请用如下硬性选择替换 Pod 模板中的 Spot 偏好，并保留实验室容忍度。请保持适当数量的基准副本运行；仅在节点池中允许 On-Demand，并不会自动预留闲置容量。

```yaml
nodeSelector:
  karpenter.sh/nodepool: mixed-capacity
  karpenter.sh/capacity-type: on-demand
tolerations:
- key: spot-lab
  operator: Equal
  value: 'true'
  effect: NoSchedule
```

此选择器有意要求 `on-demand`；它不包括 `reserved` 容量。如果之后使用容量预留，请检查标签和预留配置。On-Demand 并不保证数据持久性或容量可用性。

## 多样化兼容容量

Spot 容量池与实例类型和 AZ 绑定。更多兼容的实例类型/AZ 能给分配器提供更多选择；但这不会使中断彼此独立，也不会仅仅因为列出了两种架构就让容量翻倍。

此示例允许使用第 5 代及更新的代际，而不将上限固定为第 7 代。扩大约束范围前，请确认映像、二进制文件、存储和性能方面的兼容性。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: diversified-spot
spec:
  template:
    spec:
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
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
  limits:
    cpu: '100'
    memory: 400Gi
```

`consolidationPolicy` 和 `consolidateAfter` 控制的是整合，而不是对 EC2 中断作出反应所需的时间。使用多种架构需要匹配的多架构映像和依赖项。只有在更多代际或规格仍适合工作负载且在所选 AZ 中可用时，扩大其范围才有意义。

## 将主动中断预算与 EC2 中断区分开

Auto Mode 提供原生 Spot 中断处理；为此不需要额外部署 Node Termination Handler 或由用户管理的 SQS 队列。不要在 Auto Mode 节点上部署之前有问题的 NTH DaemonSet。如果还有其他类型的节点共存，请针对这些节点单独配置中断处理，并谨慎设置目标范围和权限。

NodePool 中断预算会限制整合和漂移等主动中断。它们无法阻止 EC2 回收 Spot 容量、延长其通知时间，也无法保证替代容量已准备就绪。

所有适用的预算都会一并考虑，并采用其中限制最严格的允许值。下面的 `10%` 和 `3` 并非二选一。百分比会向上取整，正在删除的节点/未就绪节点会占用预算；对于 20 个其他条件均健康的节点，在零预算时段之外，这两项最多允许发起两次新的主动中断。

此示例通过从 **00:00 UTC** 开始的九小时窗口，保护**首尔时间（KST）周一至周五 09:00–18:00** 时段。Karpenter 预算计划使用 UTC。旧的 `0 9-18 * * mon-fri` 每小时都会启动一个新的九小时窗口，将阻止时段延长到第二天，而不是在 18:00 结束。

```yaml
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
        values:
        - spot
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
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
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
    - nodes: '3'
    - nodes: '0'
      schedule: 0 0 * * mon-fri
      duration: 9h
  limits:
    cpu: '100'
    memory: 400Gi
```

请根据运营日历调整窗口；使用其他时区或遇到夏令时变化时，需要谨慎换算。零主动中断预算可能会延迟有益的维护，但仍无法阻止非自愿中断。

## 在实际可用时间内优雅关闭

EC2 通常会在停止/终止中断前发出两分钟警告，但通知属于尽力而为。休眠则会立即开始，行为有所不同。不要将两分钟视为每个 Pod 都能保证获得的时间：检测、驱逐、应用处理和路由变更都会消耗时间，故障也可能导致通知处理失败。

`terminationGracePeriodSeconds` 是 Kubernetes 的关闭时间预算，并不会延长 EC2 的截止时间。`preStop` 会在该预算内、正常停止信号发出之前运行。盲目执行 `sleep 90` 会浪费 120 秒预算中的大部分时间，也没有实现应用关闭或检查点保存。

此示例针对 nginx，立即启动优雅退出，使用实际的 HTTP 就绪探针，并准确记录节点名称。对于其他应用，请实现并测试其自身的停止信号处理、就绪状态转换、在途工作完成和持久化检查点。此处选择的 60 秒是示例预算上限，并不代表保证可用的时间。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spot-aware-app
  namespace: spot-lab
spec:
  replicas: 6
  selector:
    matchLabels:
      app: spot-aware
  template:
    metadata:
      labels:
        app: spot-aware
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: app
        image: nginx:1.30.6
        lifecycle:
          preStop:
            exec:
              command:
              - nginx
              - -s
              - quit
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        ports:
        - containerPort: 80
        readinessProbe:
          httpGet:
            path: /
            port: 80
          periodSeconds: 5
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: spot-aware
        minDomains: 2
        nodeAffinityPolicy: Honor
        nodeTaintsPolicy: Honor
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: spot-with-disruption-budget
      tolerations:
      - key: spot-lab
        operator: Equal
        value: 'true'
        effect: NoSchedule
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: spot-aware-budget
  namespace: spot-lab
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: spot-aware
```

`NODE_NAME` 通过 Downward API 获取节点名称。它不是 Spot 布尔值，Downward API Pod 字段也不会自动公开节点标签。无论使用何种购买选项，应用通常都应处理优雅终止。如果需要容量类型，请使用经过审核的机制提供已验证的元数据，而不要依赖节点 IMDS 凭证。

此示例要求至少有两个符合条件的 AZ 域，并以 `maxSkew: 1` 平衡六个副本。硬性 `DoNotSchedule` 约束可能会在 AZ 或容量不可用时导致 Pod 处于 Pending 状态；它们不会凭空创造容量。要求三个域之前，请评估其利弊；也不要假设 AZ 间的分散调度会同时在同一 AZ 内分散实例类型。

PDB 会限制对应用进行的主动驱逐，但无法保住被 EC2 回收的虚拟机。只有在流量处理、符合条件的容量、拓扑和故障恢复也经过验证时，增加副本才有帮助。

## 工作负载适用性

| 工作负载 | 起点和所需验证 |
|----------|-----------------|
| 无状态 Web/推理 | 使用可容忍中断的 Spot 容量，并设置明确的关键基准容量，同时测试延迟/故障转移 |
| 批处理/CI | Spot 适用于可重试、幂等的工作；对时限敏感的任务可能需要其他容量 |
| 长时间训练或有状态处理 | 定期保存持久化检查点，并验证恢复/重放能力；不要指望最后一刻保存检查点有保证 |
| 单实例数据库或关键仲裁 | 除非有明确的恢复架构，否则应避免暴露于中断风险；单靠 On-Demand 无法保护本地数据 |
| 开发/测试 | 设置成本上限并容忍容量短缺；不要假设仅使用 Spot 的作业总能启动 |

重要状态的唯一副本应保存在易丢弃的节点本地存储之外。无论实例购买选项如何，都应独立验证持久化存储、备份和恢复。

## 历史成本示例，并非当前报价

先前的指南发布了以下月度金额，但未注明区域、实例小时数构成、计费范围或可复现的测量方法。它们作为**未经验证的教学示例**保留，不代表基于当前 EKS 版本测得的节省金额。

| 示例 | 先前的 On-Demand 金额 | 先前的 Spot 金额 | 算术上的降幅 |
|---------|------------------------|-------------------|----------------------|
| 批处理 | $1,000/月 | $300/月 | 70% |
| 开发/测试 | $2,000/月 | $500/月 | 75% |
| CI/CD | $500/月 | $150/月 | 70% |
| 非关键 API | $3,000/月 | $1,200/月 | 60% |

AWS 宣称 EC2 Spot 折扣最高可达 90%；这并不意味着最低折扣，也不保证整个工作负载都能节省相同比例的费用。Spot Instance Advisor 汇总按 AZ 平均的过去一个月中断/节省数据，且数据可能存在延迟。计算价格时，请使用当前按 AZ 划分的 Spot Price History 或实际账单数据；历史中断区间不能预测下一个作业的情况。

请针对相同的有效工作量、区域、时段和可用性目标进行比较：

```text
Baseline total =
  sum(baseline On-Demand node-hours[type] * On-Demand rate[type])
  + other baseline costs

Actual total =
  sum(billed Spot node-hours[type, AZ] * time-weighted Spot rate[type, AZ])
  + sum(billed On-Demand fallback node-hours[type] * On-Demand rate[type])
  + other actual costs

Net savings = Baseline total - Actual total
```

如果费率按小时计价，请统一使用小时，并根据实际计费使用时段对价格变化进行加权。计费的 Spot/回退容量小时数应包括实际产生费用的重试、重叠运行和恢复工作。如果这些工作已经计入计费小时数，就不要再扣除一笔笼统的“中断开销”。

请在其他成本中统一计入相关的 Auto Mode 管理费用、控制平面费用、EBS、网络/NAT、数据传输、日志和许可费用。Auto Mode 费用是在 EC2 购买选项费用之外额外产生的。旧的 `interrupt count × recovery time × instance count` 快捷算法没有明确单位，也未说明中断是否已经按整个集群统计。

## 运营验证

依赖 Spot 之前，请在获批的环境中测试中断和恢复行为，包括未收到/延迟收到通知、替代容量不可用、在途工作、映像拉取、存储恢复和硬性拓扑约束。观察实际丢失的工作量和计费的恢复成本。本次审核仅在本地检查了架构定义（schema）、调度窗口和配置；并未运行这些故障实验。

## 参考资料

- [Spot 中断通知](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-instance-termination-notices.html)
- [Auto Mode 原生中断处理](https://docs.aws.amazon.com/eks/latest/userguide/ml-node-pools.html)
- [容量类型优先级](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Karpenter 中断预算和 UTC 计划](https://karpenter.sh/v1.14/concepts/disruption/)
- [Pod 终止和 preStop](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [拓扑分散调度](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [Downward API 字段](https://kubernetes.io/docs/concepts/workloads/pods/downward-api/)
- [nginx 优雅关闭](https://nginx.org/en/docs/control.html)
- [EC2 Spot 折扣说明](https://aws.amazon.com/ec2/spot/)
- [Spot Instance Advisor](https://aws.amazon.com/ec2/spot/instance-advisor/)
- [Spot 价格历史 API](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeSpotPriceHistory.html)
- [EKS Auto Mode 定价](https://aws.amazon.com/eks/pricing/)

< [上一页：扩展行为](./03-scaling-behavior.md) | [目录](./README.md) | [下一页：运营](./05-operations.md) >
