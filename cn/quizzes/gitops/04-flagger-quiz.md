# Flagger 渐进式交付测验

1. 在 Flagger 的 Canary 部署中，`stepWeight: 10`、`maxWeight: 50` 表示什么？
   - A) 从 10% 流量开始，逐步增加至 50%，然后晋级到 100%
   - B) 创建 10 个 Pod，并最多扩展到 50 个
   - C) 每隔 10 秒将流量切换至 50%
   - D) 允许最高 10% 的错误率，并在达到 50% 时回滚

<details>
<summary>显示答案</summary>

**答案：A) 从 10% 流量开始，逐步增加至 50%，然后晋级到 100%**

**说明：**
`stepWeight` 是每个分析步骤中增加的流量百分比，`maxWeight` 是 Canary 可接收的最大流量百分比。流量按 10% → 20% → 30% → 40% → 50% 递增；如果所有指标都通过，则晋级到 100%。

</details>

---

2. Flagger 会在什么条件下自动回滚 Canary 部署？
   - A) 当 CPU 使用率超过 80% 时
   - B) 当指标阈值连续超过配置的失败次数时
   - C) 当 Pod 数量超过 maxReplicas 时
   - D) 当部署时间超过 30 分钟时

<details>
<summary>显示答案</summary>

**答案：B) 当指标阈值连续超过配置的失败次数时**

**说明：**
Flagger 会在每个分析步骤评估已定义的指标（request-success-rate、request-duration 等）。当连续失败次数达到 `threshold` 时，它会自动执行回滚，将 Canary 流量恢复为 0%，并保持原始版本。

</details>

---

3. Flagger 与 Argo Rollouts 的关键区别是什么？
   - A) Flagger 仅支持 Canary，而 Argo Rollouts 仅支持 Blue-Green
   - B) Flagger 集成 Flux 生态系统，而 Argo Rollouts 集成 Argo 生态系统
   - C) Flagger 仅支持 Istio，而 Argo Rollouts 支持所有 mesh
   - D) Flagger 不支持指标分析

<details>
<summary>显示答案</summary>

**答案：B) Flagger 集成 Flux 生态系统，而 Argo Rollouts 集成 Argo 生态系统**

**说明：**
Flagger 是 Flux/Flagger 生态系统的一部分，可通过 FluxCD 自然集成到 GitOps 工作流中。Argo Rollouts 是 Argo 生态系统的一部分，与 ArgoCD 并列。两者都支持 Canary、Blue-Green 和 A/B Testing 策略，并且都可与各种 service mesh 和 ingress controller 配合使用。

</details>

---

4. `spec.analysis.mirror: true` 在 Flagger 的 Blue-Green 部署中起什么作用？
   - A) 在 Blue 和 Green 环境之间镜像日志
   - B) 将生产流量复制到 Canary（Green），以使用真实流量进行测试
   - C) 镜像数据库以进行同步
   - D) 保持两个环境之间的配置一致

<details>
<summary>显示答案</summary>

**答案：B) 将生产流量复制到 Canary（Green），以使用真实流量进行测试**

**说明：**
`mirror: true` 会将生产流量的副本发送到新版本（Green），以使用真实流量模式进行测试。镜像响应不会返回给客户端，因此可在不影响用户的情况下验证新版本的行为。

</details>

---

5. 在 Flagger 中使用 Custom Metrics 分析时，`templateRef` 的作用是什么？
   - A) 引用 Helm chart 模板
   - B) 引用 MetricTemplate CR 以执行 Prometheus/Datadog 查询
   - C) 引用 Deployment 模板以创建 Pod
   - D) 引用 ConfigMap 模板

<details>
<summary>显示答案</summary>

**答案：B) 引用 MetricTemplate CR 以执行 Prometheus/Datadog 查询**

**说明：**
`templateRef` 引用一个包含 Prometheus PromQL 或 Datadog 查询的 MetricTemplate Custom Resource。在分析阶段，Flagger 会执行这些查询并将结果与阈值比较。这使得可以基于标准 HTTP 指标之外的业务指标做出部署决策。

</details>

---

6. 使用 Flagger Webhook 进行 pre-rollout 测试的目的是什么？
   - A) 在部署前执行数据库迁移
   - B) 在流量切换前运行负载测试或一致性测试，以验证新版本
   - C) 在 Git 仓库中创建标签
   - D) 发送 Slack 通知

<details>
<summary>显示答案</summary>

**答案：B) 在流量切换前运行负载测试或一致性测试，以验证新版本**

**说明：**
pre-rollout webhook 会在开始流量切换前调用。通常，它们会通过 Flagger loadtester 运行负载测试（hey、wrk）或 Helm 测试，以验证新版本在向真实用户开放之前能否正确执行基本操作。

</details>

---

7. 将 FluxCD Image Automation 与 Flagger 配合使用时，正确的顺序是什么？
   - A) 检测到新镜像标签 → Git 提交 → Flux 同步 → Flagger Canary 分析
   - B) Flagger Canary 分析 → 检测到新镜像标签 → Git 提交
   - C) Git 提交 → 检测到新镜像标签 → Flux 同步
   - D) Flux 同步 → Flagger Canary 分析 → 检测到新镜像标签

<details>
<summary>显示答案</summary>

**答案：A) 检测到新镜像标签 → Git 提交 → Flux 同步 → Flagger Canary 分析**

**说明：**
Flux Image Automation 会检测 registry 中的新镜像标签，并创建一个提交以更新 Git 仓库中的 manifest。当 Flux 同步此变更时，Deployment 会更新，Flagger 会检测到此变更并自动开始 Canary 分析过程。

</details>

---

8. Flagger A/B Testing 中基于 header 的路由与常规 Canary 部署有何不同？
   - A) A/B Testing 会将新版本开放给所有用户
   - B) 只有匹配特定 HTTP header/cookie 条件的请求才会路由到新版本
   - C) A/B Testing 不支持回滚
   - D) 基于 header 的路由仅适用于 TCP 流量

<details>
<summary>显示答案</summary>

**答案：B) 只有匹配特定 HTTP header/cookie 条件的请求才会路由到新版本**

**说明：**
在 A/B Testing 中，流量会根据 `spec.analysis.match` 中定义的 HTTP header 或 cookie 条件进行分类。只有符合这些条件的请求才会路由到新版本，从而可将新功能开放给特定用户群体（beta 测试人员、内部员工等），同时其他用户继续使用稳定版本。

</details>
