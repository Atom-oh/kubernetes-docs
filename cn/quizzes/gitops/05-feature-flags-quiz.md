# Feature Flags 与 OpenFeature 测验

1. OpenFeature 的 Provider 模型主要有什么优势？
   - A) Vendor lock-in 可提供最佳性能
   - B) 与供应商无关的评估 API 可减少切换后端时所需的代码改动
   - C) 必须自行运行 Feature Flag 服务器
   - D) 仅支持 REST API

<details>
<summary>显示答案</summary>

**答案：B) 与供应商无关的评估 API 可减少切换后端时所需的代码改动**

**说明：**
OpenFeature 提供与供应商无关的 SDK API，可减少切换后端时对评估代码的改动。不过，Flag key、变体、定向规则、上下文语义、凭证、缓存和事件行为仍需迁移和测试。

</details>

---

2. 在 Kubernetes 上部署 flagd 时，Sidecar 和 Standalone 模式有什么区别？
   - A) Sidecar 性能更好，Standalone 更易管理
   - B) Sidecar 在应用 Pod 内运行，Standalone 通过共享 Service 提供评估
   - C) Sidecar 仅支持 TCP，Standalone 仅支持 HTTP
   - D) Sidecar 使用 CRD，Standalone 仅使用 ConfigMap

<details>
<summary>显示答案</summary>

**答案：B) Sidecar 在应用 Pod 内运行，Standalone 通过共享 Service 提供评估**

**说明：**
RPC 可以调用本地 sidecar，也可以经由 Service 调用共享 Deployment。应测量实际延迟和资源用量。Sidecar/共享部署描述的是组件放置位置；RPC/进程内评估描述的是在哪里执行评估。进程内 Provider 也可以同步规则，并在应用程序内部完成评估。

</details>

---

3. Feature Flag 的 Evaluation Context 有什么作用？
   - A) 传递构建信息，以便在编译时确定 Flag
   - B) 使用用户 ID、区域和环境等上下文评估定向规则
   - C) 传递数据库连接信息
   - D) 传递 Kubernetes 节点信息

<details>
<summary>显示答案</summary>

**答案：B) 使用用户 ID、区域和环境等上下文评估定向规则**

**说明：**
Evaluation Context 是在评估 Flag 时动态传入的元数据，可包含用户 ID、区域、环境（dev/staging/prod）和用户组等信息。定向规则会使用这些信息，为特定用户或组启用功能。涉及权限或权益的判断应使用经服务器验证的属性；Feature Flag 不能替代身份验证或授权。

</details>

---

4. Dark Launch 模式中的 Feature Flag 有什么作用？
   - A) 完全隐藏服务并阻止访问
   - B) 返回现有结果，同时通过无副作用的影子执行测试新逻辑
   - C) 将服务器切换到深色模式
   - D) 只在夜间执行部署

<details>
<summary>显示答案</summary>

**答案：B) 返回现有结果，同时通过无副作用的影子执行测试新逻辑**

**说明：**
影子验证会继续返回现有结果，并对只读计算或隔离重放的结果进行比较。它不得重复扣费、写入业务记录或发送通知。应限制异步并发，并为后台工作设置独立超时。这不同于逐步发布；后者会把新结果实际提供给选定用户。

</details>

---

5. 以代码管理 Feature Flag（GitOps）有什么优势？
   - A) 只能通过 GUI 管理 Flag
   - B) 通过 Git PR 管理 Flag 变更，便于审查、审计和回滚
   - C) 可以加快 Flag 评估速度
   - D) 可以节省服务器资源

<details>
<summary>显示答案</summary>

**答案：B) 通过 Git PR 管理 Flag 变更，便于审查、审计和回滚**

**说明：**
在 Git 中管理 FeatureFlag CR，可以通过 PR 审查、查看变更历史并使用 Git revert 回滚。消费者仍需 ArgoCD/Flux 协调、源同步和 SDK 状态更新。Self-healing 可能撤销紧急的手动 patch，因此必须一并考虑资源所有权和协调行为。

</details>

---

6. 防止 Feature Flag 形成技术债务的最佳做法是什么？
   - A) 永久保留所有 Flag
   - B) 为 Flag 设置到期日期，并在发布完成后清理 Flag 代码
   - C) 不限制数量，随意创建 Flag
   - D) 不要在 Flag 名称中包含日期

<details>
<summary>显示答案</summary>

**答案：B) 为 Flag 设置到期日期，并在发布完成后清理 Flag 代码**

**说明：**
记录负责人和审查日期；移除代码和配置前，还要检查较旧的应用版本及其他使用者。到期元数据本身不会删除 Flag。永久使用的运维型 Flag 可能需要定期审查，而不是删除。

</details>

---

7. OpenFeature Operator 在 Kubernetes 上提供什么核心功能？
   - A) 自动向 Pod 注入 flagd sidecar，并管理 FeatureFlag CRD
   - B) 审计 Kubernetes 集群安全性
   - C) 自动构建容器镜像
   - D) 自动配置 HPA

<details>
<summary>显示答案</summary>

**答案：A) 自动向 Pod 注入 flagd sidecar，并管理 FeatureFlag CRD**

**说明：**
Operator 管理的资源包括 FeatureFlag 和 FeatureFlagSource。Pod 注入使用 `openfeature.dev/enabled` 和 `openfeature.dev/featureflagsource` 注解。文件源的 ConfigMap 卷、直接访问 Kubernetes 和代理源有不同的同步路径。应用仍需集成 SDK。

</details>

---

8. Flagger 与 Feature Flag 组合使用时，基于指标的自动发布如何运作？
   - A) Feature Flag 直接控制流量
   - B) Flagger 负责 Canary 流量迁移，Feature Flag 在应用层控制功能的逐步开放
   - C) Feature Flag 完全替代 Flagger
   - D) 两种工具使用完全相同的指标

<details>
<summary>显示答案</summary>

**答案：B) Flagger 负责 Canary 流量迁移，Feature Flag 在应用层控制功能的逐步开放**

**说明：**
Flagger 控制工作负载发布和流量；Feature Flag 控制应用行为。两者不会自动组成一个事务。协调 Flag 变更和回滚需要实际的 webhook 或 Git 自动化，以及相应的授权和故障处理。Canary 流量百分比与用户群体百分比也代表不同的人群。

</details>
