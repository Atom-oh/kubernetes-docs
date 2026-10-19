# EKS Auto Mode 运维测验

> **相关文档**：[运维](../../eks-auto-mode/05-operations.md)
> **最后更新**：2026 年 9 月 12 日

## 选择题

### 1. 哪项定时设置会在首尔工作时间内阻止适用的自愿 NodePool 中断？

- A) `nodes: "100%"`
- B) `nodes: "0"`，并配有时间边界正确的 UTC 定时计划
- C) `consolidateAfter: 0s`
- D) `consolidationPolicy: Never`

<details>
<summary>显示答案</summary>

**答案：B) `nodes: "0"`，并配有时间边界正确的 UTC 定时计划**

**说明：**
在预算生效期间，零预算会阻止 consolidation、drift 等适用的优雅中断方式，但不会阻止 EC2 中断、到期、修复或每一种手动删除。下面的定时计划每天从 UTC 00:00 开始、持续 9 小时，对应首尔工作日 09:00–18:00。若使用每小时执行的 `9-18` 计划并设置 9 小时持续时间，时间窗口会反复重叠。
```yaml
# Fragment of NodePool spec.disruption
budgets:
  - nodes: "10%"
  - nodes: "0"
    schedule: "0 0 * * mon-fri"
    duration: 9h
```


</details>

### 2. 当 PDB 选择一个可扩缩控制器的六个副本时，`minAvailable: "80%"` 表示什么？

- A) 运行的副本不得超过 80%
- B) 执行驱逐决策时，向上取整后必须有五个健康副本
- C) 每个 Pod 有 80% 的概率被保留
- D) 这些 Pod 会受到 80 秒的保护

<details>
<summary>显示答案</summary>

**答案：B) 执行驱逐决策时，向上取整后必须有五个健康副本**

**说明：**
控制器会将六个副本的 80% 向上取整为五个健康/Ready 副本。此限制适用于 Eviction API 的决策，并不涵盖所有故障、直接删除或副本创建。`minAvailable` 和 `maxUnavailable` 是含义不同的替代字段；不要同时配置两者。原示例中的五个副本和 `minAvailable: 3` 允许最多驱逐两个副本，这与 `maxUnavailable: 1` 不同。
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
  namespace: ops-lab
spec:
  minAvailable: "80%"
  selector:
    matchLabels:
      app: web-app
```

当 `disruptionsAllowed` 为零时，也可能是健康且有意设置的阻止状态。在将其判定为违规之前，请检查 `observedGeneration`、`currentHealthy` 和 `desiredHealthy`。

</details>

### 3. 哪项资源有助于诊断 Auto Mode 节点的置备生命周期？

- A) 仅查看应用日志
- B) 查看 NodeClaim conditions，再结合相关的 NodePool/NodeClass 证据
- C) 仅查看 EC2 控制台
- D) 仅查看 CloudWatch 小组件

<details>
<summary>显示答案</summary>

**答案：B) 查看 NodeClaim conditions，再结合相关的 NodePool/NodeClass 证据**

**说明：**
先读取 conditions 和原因，再根据证据调查调度约束、NodeClass 就绪情况、IAM 和网络配置。NodeClaim 没有通用的 `.status.phase` 字段。下面的命令使用相关指南中已审阅并设定的 `KUBE_CONTEXT`，并只选择诊断所需字段，而不是转储完整对象。
```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodeclaims -o json |
  jq '[.items[] | {name: .metadata.name, uid: .metadata.uid, node: .status.nodeName,
      pool: .metadata.labels["karpenter.sh/nodepool"], createdAt: .metadata.creationTimestamp,
      expireAfter: .spec.expireAfter, terminationGracePeriod: .spec.terminationGracePeriod,
      imageID: .status.imageID,
      conditions: [.status.conditions[]? | {type,status,reason,lastTransitionTime,observedGeneration}]}]'
```


</details>

### 4. 哪个 do-not-disrupt 注解是受支持的？

- A) `kubernetes.io/do-not-disrupt: "true"`
- B) `karpenter.sh/do-not-disrupt: "true"`
- C) `eks.amazonaws.com/no-disrupt: "true"`
- D) `node.kubernetes.io/exclude-disruption: "true"`

<details>
<summary>显示答案</summary>

**答案：B) `karpenter.sh/do-not-disrupt: "true"`**

**说明：**
Pod 和 Node 上的注解作用范围不同。Pod 注解会阻止该 Pod 被自愿驱逐，也会阻止对其所在节点进行 consolidation；NodeClaim 的终止宽限期允许包含这类 Pod 的节点发生 drift，并最终限制排空时间。Node 注解会将该节点排除在自愿中断之外。这两者都不能无限期保证节点不会到期、被中断或修复，也不能阻止手动删除。Auto Mode 有自己的默认终止宽限期，不要假定该值未设置。
```yaml
# Metadata fragment for a deliberately selected Pod or Node.
# Review the different Pod/Node semantics before applying.
metadata:
  annotations:
    karpenter.sh/do-not-disrupt: "true"
```

元数据片段不是可直接运行的完整 Pod。将此控制应用到真实工作负载之前，请先制定恢复或移除方案。

</details>

### 5. 哪种监控方式能为 Auto Mode 运维提供有用的证据？

- A) 只使用 `kubectl top`
- B) 结合已配置的数据采集器和日志传送、Kubernetes conditions 及工作负载信号
- C) 只使用 EC2 控制台
- D) 假设 CloudWatch 中无需配置采集就能获得所有指标

<details>
<summary>显示答案</summary>

**答案：B) 结合已配置的数据采集器和日志传送、Kubernetes conditions 及工作负载信号**

**说明：**
Container Insights、EKS control-plane 指标、kube-state-metrics/node-exporter 以及 Auto Mode 托管组件日志各自有不同的前提条件。请验证每个数据发布方和维度。`kubectl top` 需要正常工作的 metrics API；命令报错并不能证明 metrics-server 不存在。托管组件日志需要单独配置 Vended Logs 传送。调度延迟和应用可用性需要合适的埋点；启用 Container Insights 不会自动产生所有设想中的信号。

</details>

### 6. 哪个 NodePool 字段用于设置按节点年龄计算的到期资格？

- A) `autoUpdate: true`
- B) `expireAfter`
- C) `updatePolicy: Rolling`
- D) `refreshInterval: 24h`

<details>
<summary>显示答案</summary>

**答案：B) `expireAfter`**

**说明：**
示例让 NodeClaim 在 168 小时后达到到期资格，并单独设置终止阶段的时限。这并不承诺节点能连续运行七天、在精确时间完成替换，或届时必定使用最新安全补丁。此前仍可能发生 drift、consolidation 或中断；修改模板也不会改写现有 NodeClaim。请检查 Auto Mode 的默认值/最长生命周期以及应用恢复要求。
```yaml
# Fragment of NodePool spec.template.spec
expireAfter: 168h
terminationGracePeriod: 24h
```


</details>

### 7. 多个适用的 NodePool disruption budget 如何组合？

- A) 最新的定时条目会覆盖较早的条目
- B) 采用最小的允许中断数
- C) 将各百分比相加
- D) 保证一定数量的替换节点

<details>
<summary>显示答案</summary>

**答案：B) 采用最小的允许中断数**

**说明：**
始终生效的 10% 上限不会被定时的 30% 预算放宽。相关指南实际从 30% 开始，再加入首尔工作日 10% 上限、工作时间最多一台节点的上限，以及明确的 UTC 每月冻结窗口。对于 20 个其他条件均健康的节点，允许数量分别为 6、2、1 和 0。删除节点或未就绪节点会降低允许数量；这些预算并不限制所有强制中断。
```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
  budgets:
  - nodes: 30%
  - nodes: 10%
    schedule: 0 15 * * sun-thu
    duration: 24h
  - nodes: '1'
    schedule: 0 0 * * mon-fri
    duration: 9h
  - nodes: '0'
    schedule: 0 0 1 * *
    duration: 24h
```


</details>

### 8. 当相关数据采集端已配置时，哪些信号有助于定义节点运维告警？

- A) 仅 EC2 状态
- B) 调度积压、实测置备延迟和工作负载可用性
- C) 仅成本
- D) 仅网络流量

<details>
<summary>显示答案</summary>

**答案：B) 调度积压、实测置备延迟和工作负载可用性**

**说明：**
为每条告警选择数据来源、维度、统计值、时间窗口和应用目标。Pending 不等同于无法调度。下方保留的原数值示例仅用于未经验证的规划阈值，不能视为实测正常范围、Auto Mode 默认值或 Container Insights 保证提供的指标。

| 信号 | 先前的规划示例 | 先前的告警示例 |
|--------|---------------------------|------------------------|
| Pending Pod 数量 | 0–5 | >10 for 5 min |
| 节点置备时间 | <90 sec | >120 sec |
| 工作负载可用性 | >99.9% | <99.5% |
| API 响应时间 | <200 ms | >500 ms |

必须区分指标缺失或采集器数据过期与错误数为零。该指南根据实际指标目录在本地生成 CloudWatch 控制面板定义，而不是编造指标名称。

</details>

## 参考资料

- [Karpenter disruption controls](https://karpenter.sh/v1.14/concepts/disruption/)
- [Kubernetes PDB 语义](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [Auto Mode NodePools](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
