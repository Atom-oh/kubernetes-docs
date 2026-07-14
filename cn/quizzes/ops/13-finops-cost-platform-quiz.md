# FinOps 成本可视化平台测验

1. FinOps 运营周期三个阶段的正确顺序是什么？
   - A) Optimize → Inform → Operate
   - B) Inform → Optimize → Operate
   - C) Operate → Inform → Optimize
   - D) Inform → Operate → Optimize

<details>
<summary>显示答案</summary>

**答案: B) Inform → Optimize → Operate**

**解释:**
FinOps 周期会迭代经过 Inform（建立成本可视性）→ Optimize（降低成本）→ Operate（治理）。首先了解谁花费了什么以及花费多少，然后进行优化，最后通过策略进行管理。

</details>

---

2. 将 AWS CUR (Cost and Usage Report) 与 Kubecost 集成的主要原因是什么？
   - A) 降低 Kubecost 许可证成本
   - B) 跟踪 Kubernetes 之外的 AWS service 成本
   - C) 通过匹配实际 AWS 账单数据来提高 Pod-level 成本准确性
   - D) 启用多集群 federation

<details>
<summary>显示答案</summary>

**答案: C) 通过匹配实际 AWS 账单数据来提高 Pod-level 成本准确性**

**解释:**
Kubecost 基于公开标价估算成本。CUR 集成会将这些估算值与反映 Savings Plans、Reserved Instances 和协商费率的实际账单数据相匹配，从而显著提高成本准确性。

</details>

---

3. 使用 Kyverno 强制执行成本标签时，`validationFailureAction: Enforce` 表示什么？
   - A) 对没有标签的 workloads 显示警告
   - B) 阻止部署缺少必需标签的 workloads
   - C) 自动添加标签
   - D) 修改现有 workloads 上的标签

<details>
<summary>显示答案</summary>

**答案: B) 阻止部署缺少必需标签的 workloads**

**解释:**
`validationFailureAction: Enforce` 会阻止创建/修改违反策略的 resources。缺少 team、service 和 cost-center 标签的 Deployments 将被拒绝。建议先从 `Audit` 模式开始用于警告，然后在团队准备就绪后切换到 `Enforce`。

</details>

---

4. 为什么将 VPA 设置为 `updateMode: "Off"`？
   - A) 完全禁用 VPA
   - B) 仅提供建议，而不自动重启 Pods
   - C) 仅调整 CPU，同时保持 memory 固定
   - D) 防止与 HPA 冲突

<details>
<summary>显示答案</summary>

**答案: B) 仅提供建议，而不自动重启 Pods**

**解释:**
`updateMode: "Off"` 让 VPA 分析 resource 使用情况并提供建议，而不会自动重启 Pods 来应用更改。这支持一种安全的工作流：先审查建议，再通过 PRs 手动应用。Goldilocks dashboard 也利用了此模式。

</details>

---

5. Showback 和 Chargeback 之间有什么区别？
   - A) Showback 显示成本，Chargeback 隐藏成本
   - B) Showback 提供成本可视性，Chargeback 实际向部门/团队收费
   - C) Showback 是实时的，Chargeback 是按月的
   - D) Showback 仅适用于 cloud，Chargeback 仅适用于 on-premises

<details>
<summary>显示答案</summary>

**答案: B) Showback 提供成本可视性，Chargeback 实际向部门/团队收费**

**解释:**
Showback 向每个团队/service 显示其花费，以提高意识，而 Chargeback 则实际从部门预算中扣除成本。大多数组织先从 Showback 开始建立成本意识文化，然后再过渡到 Chargeback。

</details>

---

6. namespace 必须具有哪个标签，Goldilocks 才会显示 resource 建议？
   - A) goldilocks.fairwinds.com/vpa-enabled=true
   - B) goldilocks.fairwinds.com/enabled=true
   - C) vpa.kubernetes.io/enabled=true
   - D) monitoring.goldilocks.com/watch=true

<details>
<summary>显示答案</summary>

**答案: B) goldilocks.fairwinds.com/enabled=true**

**解释:**
Goldilocks 会自动为带有 `goldilocks.fairwinds.com/enabled=true` 标签的 namespaces 中的所有 Deployments 创建 VPAs，并在其 web dashboard 中可视化推荐的 resource 值。

</details>

---

7. Kubecost Allocation API 中的 `aggregate=label:team` 表示什么？
   - A) 仅筛选带有 team 标签的 Pods
   - B) 按 team 标签值对成本进行分组并求和
   - C) 为每个 team 创建单独的 API 调用
   - D) 自动添加 team 标签

<details>
<summary>显示答案</summary>

**答案: B) 按 team 标签值对成本进行分组并求和**

**解释:**
`aggregate=label:team` 指示 Kubecost 按 `team` 标签值（例如 team-commerce、team-platform）对所有 Pod 成本进行分组并求和，在单个查询中提供每个 team 的总成本、CPU 成本和 memory 成本。

</details>

---

8. 为什么成本 anomaly alert 需要持续 30 分钟的高成本才会触发？
   - A) Prometheus scrape interval 是 30 分钟
   - B) 防止临时峰值（deployments、autoscaling）造成误报
   - C) 避免 Slack API rate limits
   - D) Kubecost 数据刷新周期是 30 分钟

<details>
<summary>显示答案</summary>

**答案: B) 防止临时峰值（deployments、autoscaling）造成误报**

**解释:**
Deployments、autoscaling events 和 batch jobs 可能导致临时成本峰值。`for: 30m` 条件确保只有当成本持续升高 30 分钟以上时才触发 alerts，从而减少正常运营活动带来的噪音。

</details>
