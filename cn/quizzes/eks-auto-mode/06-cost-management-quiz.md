# EKS Auto Mode 成本管理测验

> **相关文档**：[成本管理](../../eks-auto-mode/06-cost-management.md)
> **最后更新**：2026 年 9 月 12 日

## 单项选择题

### 1. 允许使用 ARM 节点时，应如何看待先前所说的“Graviton 可节省 20%”？

- A) 将其视为 AWS 对所有情况的保证
- B) 将其视为整张账单的折扣
- C) 将其视为未经验证的示例；比较兼容的工作负载和实际费率
- D) 将其视为所有镜像都能在 ARM 上运行的证明

<details>
<summary>显示答案</summary>

**答案：C) 将其视为未经验证的示例；比较兼容的工作负载和实际费率**

**解释：**
先前约 20% 的 ARM 节省和 70–90% 的 Spot 节省都只是规划示例，并非针对当前工作负载经过验证的比较。请检查多架构镜像、依赖项、每单位有效工作量的性能、当前区域费率以及 Auto Mode 和其他费用。允许 `amd64` 和 `arm64` 并不能验证应用兼容性，也不能保证会选中其中任一架构。

</details>

### 2. 动态 NodePool 中的 `limits.cpu: 500` 限制什么？

- A) 每个节点最多 500 个核心
- B) 该资源池所预置资源的 CPU 总量
- C) 每个 Pod 最多使用 500m CPU
- D) AWS 账户的全部支出

<details>
<summary>显示答案</summary>

**答案：B) 该资源池所预置资源的 CPU 总量**

**解释：**
这是资源池级别的资源上限；在快速且最终一致的预置过程中，实际用量可能暂时超出上限。`1Ti` 表示 1 TiB（1024 GiB），而不是十进制的 1 TB。资源限制有助于约束资源增长，但不会给实例定价、涵盖其他服务，也不会强制执行硬性的货币预算。
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: compute-optimized
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
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
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
      - key: cost-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        cost-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
  limits:
    cpu: '500'
    memory: 1Ti
```


</details>

### 3. 在重新调度和成本约束允许时，哪种策略允许整合空闲及利用率偏低的节点？

- A) `WhenEmpty`
- B) `WhenEmptyOrUnderutilized`
- C) `Always`
- D) `Aggressive`

<details>
<summary>显示答案</summary>

**答案：B) `WhenEmptyOrUnderutilized`**

**解释：**
此策略会评估基于资源请求的调度可行性和成本；它不会删除所有 CPU 使用率低于某个测量阈值的节点。`consolidateAfter` 是用于防抖的等待时间，PDB、预算和放置约束都可能阻止整合。`WhenEmpty` 的适用范围更窄；这两种策略都不保证节省成本，也不会禁用所有其他中断方式。

</details>

### 4. 符合条件的 EC2 用量可能转为其他实例系列或区域时，哪种方案能提供更大的计费灵活性？

- A) Compute Savings Plans
- B) 固定到一个实例系列和区域的 EC2 Instance Savings Plan
- C) 仅使用一种确切规格的 Standard RI
- D) 不使用任何承诺折扣

<details>
<summary>显示答案</summary>

**答案：A) Compute Savings Plans**

**解释：**
Compute Savings Plans 可灵活适用于实例系列、规格、区域、操作系统和租赁方式；EC2 Instance Savings Plans 则承诺使用特定实例系列和区域，但在规格、操作系统和租赁方式上仍有灵活性。宣传的最高折扣仍为 66% 和 72%，并非预期费率。应根据持续存在且符合条件的未覆盖用量、现有承诺和计划中的变化，匹配每小时美元承诺额。先前提出的“三个月基线、覆盖 70% 用量”策略只是未经验证的规划示例。Spot 和单独收取的 Auto Mode 费用不享受 EC2 Savings Plans 折扣；不存在专门针对 ARM 的计划，也没有普遍适用的 GPU 排除规则。

</details>

### 5. 要进行有用的 Kubecost Pod 级成本分摊，需要什么？

- A) 无需设置或数据源
- B) 仅为 Pod 添加成本中心标签
- C) 配置代理/集群集成并提供适当的成本数据
- D) 只使用 Cost Explorer，无需 Kubernetes 分摊数据

<details>
<summary>显示答案</summary>

**答案：C) 配置代理/集群集成并提供适当的成本数据**

**解释：**
本次审查的 Kubecost 3.2.4 Helm chart 来自新仓库，名称为 `kubecost/kubecost`。版本 3 的 FinOps 代理/ClickHouse 架构与旧版 cost-analyzer 部署不同。请配置许可、私有访问、存储/保留策略、工作负载 IAM 和账单核对。安装前先渲染并检查本次审查的 values；仅添加标签不会产生实际成本数据。

```bash
: "${KUBECOST_VALUES:?Set the reviewed Kubecost 3.2.4 values file}"
test -f "$KUBECOST_VALUES"
helm repo add kubecost https://kubecost.github.io/kubecost/
helm repo update kubecost
helm show chart kubecost/kubecost --version 3.2.4
helm template cost-review kubecost/kubecost --version 3.2.4 \
  --namespace kubecost --values "$KUBECOST_VALUES" \
  > "$WORK_DIR/kubecost-rendered.yaml"
```


</details>

### 6. 哪些证据应当用于指导资源请求的调整？

- A) 始终让 requests 和 limits 相等
- B) VPA 建议以及有代表性的工作负载/SLO 证据
- C) 将所有请求都设为最大值
- D) 删除所有请求

<details>
<summary>显示答案</summary>

**答案：B) VPA 建议以及有代表性的工作负载/SLO 证据**

**解释：**
`Off` 不会应用建议，同时仍需要正常工作的 VPA 组件和指标。请检查每个容器、建议的置信度和历史记录、启动峰值、内存限制以及 CPU 节流情况。建议并不能保证性能、防止所有 OOM，或证明能够节省成本。比较 Kubernetes 资源数量时，不要去掉单位后缀。
```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: cost-app-vpa
  namespace: cost-lab
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cost-efficient-app
  updatePolicy:
    updateMode: 'Off'
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: '4'
        memory: 8Gi
```


</details>

### 7. 当不同层确实有不同的中断容忍度或架构要求时，哪种设计能够表达这些差异？

- A) 要求所有层采用相同的放置方式
- B) 使用适合各层的资源池，并配置匹配的工作负载约束
- C) 为每种实例规格单独创建一个资源池
- D) 假定每个可用区都对应一项独立的计费折扣

<details>
<summary>显示答案</summary>

**答案：B) 使用适合各层的资源池，并配置匹配的工作负载约束**

**解释：**
不同资源池可以表达实际约束，但过度拆分可能增加闲置成本。仅使用 Spot 的批处理资源池没有按需实例回退；只有在作业兼容中断且具备恢复能力时才使用它。仅有资源池名称并不能路由工作负载：应像指南中那样设置选择器和容忍度。

| 层级 | 先前的策略 | 原先未经验证的节省比例 |
|------|----------------|----------------------------|
| 前端 | On-Demand + Graviton | ~20% |
| API | 混合使用 Spot + Graviton | ~40% |
| 批处理 | Spot + 多样化实例 | ~70% |
| ML | 选择实例规格 | ~30% |

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch-tier
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
      - key: cost-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        cost-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
```


</details>

### 8. 要让自定义 NodeClass 标签支持 AWS 成本分配，需要满足什么条件？

- A) 所有 Kubernetes 标签都会自动传播
- B) 有效的 NodeClass/标签权限、实际资源标签以及 Billing 激活
- C) 只需创建 AWS Organization
- D) 无法按标签分配成本

<details>
<summary>显示答案</summary>

**答案：B) 有效的 NodeClass/标签权限、实际资源标签以及 Billing 激活**

**解释：**
相关指南提供了包含身份和网络选择器的完整 NodeClass。请检查节点访问条目和标签权限，在预期的资源池中引用该 NodeClass，验证资源上实际存在的标签，并在 Billing 中激活相应键。用户定义的键最长可能需要 24 小时才会显示，之后还可能需要另外最多 24 小时才能激活；报告延迟另行计算。AWS 生成的 EC2 集群键是 `aws:eks:cluster-name`；它不包含控制平面费用。仅有命名空间标签既不会自动传播，也无法分配所有 AWS 成本。

</details>

## 参考资料

- [EKS 定价](https://aws.amazon.com/eks/pricing/)
- [Savings Plans 类型](https://docs.aws.amazon.com/savingsplans/latest/userguide/plan-types.html)
- [EKS 账单标签](https://docs.aws.amazon.com/eks/latest/userguide/eks-using-tags.html)
