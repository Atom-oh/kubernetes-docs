# Flagger 渐进式交付测验

1. 在 Flagger 的 Canary 部署中，`stepWeight: 10` 和 `maxWeight: 50` 分别表示什么？
   - A) 每个分析步骤将流量权重增加 10%，最高增加到 50%，随后执行晋级
   - B) 创建 10 个 Pod，并最多扩展到 50 个
   - C) 每隔 10 秒将流量切换至 50%
   - D) 允许最高 10% 的错误率，并在达到 50% 时回滚

<details>
<summary>显示答案</summary>

**答案：A) 每个分析步骤将流量权重增加 10%，最高增加到 50%，随后执行晋级**

**说明：**
stepWeight 是每个分析步骤增加的流量权重，maxWeight 是分析阶段的目标权重。各步骤依次将权重从 10% 提高到 20%、30%、40% 和 50%；随后更新主版本并晋级流量。晋级期间 Canary 可能暂时接收全部流量，因此 50% 不是 Canary 生命周期内的流量上限。

</details>

---

2. 在什么情况下 Flagger 会自动回滚 Canary 部署？
   - A) CPU 使用率超过 80% 时
   - B) 某个 revision 的失败检查次数达到阈值时
   - C) Pod 数量超过 maxReplicas 时
   - D) 部署时间超过 30 分钟时

<details>
<summary>显示答案</summary>

**答案：B) 某个 revision 的失败检查次数达到阈值时**

**说明：**
Flagger 会在每个分析步骤评估已定义的指标，例如 request-success-rate 和 request-duration。失败检查会按 revision 累积，不会因一次成功检查就清零。达到阈值后，Flagger 会在后续协调过程中触发回滚。主版本晋级失败时可能采用不同的恢复方式，例如保留健康的 Canary。

</details>

---

3. Flagger 与 Argo Rollouts 的主要区别是什么？
   - A) Flagger 仅支持 Canary，而 Argo Rollouts 仅支持 Blue-Green
   - B) Flagger 与 Flux 生态系统集成，而 Argo Rollouts 与 Argo 生态系统集成
   - C) Flagger 仅支持 Istio，而 Argo Rollouts 支持所有 service mesh
   - D) Flagger 不支持指标分析

<details>
<summary>显示答案</summary>

**答案：B) Flagger 与 Flux 生态系统集成，而 Argo Rollouts 与 Argo 生态系统集成**

**说明：**
Flagger 属于 Flux/Flagger 生态系统，并可自然融入 FluxCD GitOps 工作流；Argo Rollouts 属于 Argo 生态系统，与 ArgoCD 并列。这些生态系统关联并非排他性要求。Flagger 通过 Canary 控制现有工作负载，而 Argo Rollouts 使用 Rollout 和 workloadRef。具体的流量路由和实验能力取决于所用 provider。

</details>

---

4. Flagger Blue-Green 部署中的 `spec.analysis.mirror: true` 有什么作用？
   - A) 在 Blue 和 Green 环境之间镜像日志
   - B) 将生产流量复制到 Canary（Green），用真实流量进行测试
   - C) 镜像数据库以进行同步
   - D) 保持两个环境的配置一致

<details>
<summary>显示答案</summary>

**答案：B) 将生产流量复制到 Canary（Green），用真实流量进行测试**

**说明：**
`mirror: true` 会把生产请求的副本发送到新版本（Green），以真实流量模式测试新版本。响应会被丢弃，但数据库写入、消息、付款操作和额外负载仍可能发生。应使用已经验证为只读的请求，或通过隔离和幂等控制避免副作用。

</details>

---

5. 在 Flagger 中使用自定义指标分析时，`templateRef` 有什么作用？
   - A) 引用 Helm chart 模板
   - B) 引用 MetricTemplate CR，以执行 Prometheus/Datadog 查询
   - C) 引用 Deployment 模板以创建 Pod
   - D) 引用 ConfigMap 模板

<details>
<summary>显示答案</summary>

**答案：B) 引用 MetricTemplate CR，以执行 Prometheus/Datadog 查询**

**说明：**
`templateRef` 指向一个 MetricTemplate 自定义资源，其中包含 Prometheus PromQL 或 Datadog 查询。分析期间，Flagger 会执行这些查询，并将结果与阈值比较。这样便可依据标准 HTTP 指标以外的业务指标作出部署决策。

</details>

---

6. 使用 Flagger Webhook 进行 rollout 前测试的目的是什么？
   - A) 在部署前执行数据库迁移
   - B) 在切换流量前运行负载测试或一致性测试，验证新版本
   - C) 在 Git 仓库中创建标签
   - D) 发送 Slack 通知

<details>
<summary>显示答案</summary>

**答案：B) 在切换流量前运行负载测试或一致性测试，验证新版本**

**说明：**
rollout 前的 webhook 会在开始切换流量之前调用。测试可以使用准备好的工具和权限来执行冒烟测试或一致性测试。异步 cmd 负载测试被接受，只表示任务已接收，并不代表质量检查通过；bash 等阻塞测试则必须在其超时时间内完成。

</details>

---

7. 将 FluxCD Image Automation 与 Flagger 配合使用时，正确的顺序是什么？
   - A) 选定镜像 → 审核并合并 Git 变更 → Flux 应用变更 → Flagger 分析
   - B) Flagger Canary 分析 → 检测到新镜像标签 → Git 提交
   - C) Git 提交 → 检测到新镜像标签 → Flux 同步
   - D) Flux 同步 → Flagger Canary 分析 → 检测到新镜像标签

<details>
<summary>显示答案</summary>

**答案：A) 选定镜像 → 审核并合并 Git 变更 → Flux 应用变更 → Flagger 分析**

**说明：**
image-reflector 会评估镜像标签和策略，image-automation 会修改带有标记的 YAML。若变更推送到单独的分支，必须先通过 PR 审核并合并；之后 Flux 才会应用源分支中的变更，Flagger 随后观察到工作负载变化。Flagger 不会直接协调 HelmRelease 对象。

</details>

---

8. Flagger A/B Testing 中，基于 header 的路由与常规 Canary 部署有何不同？
   - A) A/B Testing 会将新版本开放给所有用户
   - B) 只有匹配特定 HTTP header/cookie 条件的请求才会路由到新版本
   - C) A/B Testing 不支持回滚
   - D) 基于 header 的路由仅适用于 TCP 流量

<details>
<summary>显示答案</summary>

**答案：B) 只有匹配特定 HTTP header/cookie 条件的请求才会路由到新版本**

**说明：**
在 A/B Testing 中，流量会根据 `spec.analysis.match` 中定义的 HTTP header 或 cookie 条件进行分类。只有符合条件的请求才会路由到新版本，其余请求继续使用稳定版本。客户端可以自行设置 header 或 cookie，因此不能把它们当作员工身份认证或敏感功能的访问保护机制。

</details>
