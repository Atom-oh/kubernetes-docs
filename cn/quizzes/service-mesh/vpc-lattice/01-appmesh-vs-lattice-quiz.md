# App Mesh 与 VPC Lattice 架构测验

本测验检查你对 sidecar 与托管数据平面模型、资源映射和功能差距等结构性差异的理解。

## 单选题

1. 应如何评估迁移过程中的功能缺口？
   - A) AWS 只是还没有实现这些功能，很快就会添加
   - B) 比较实际的 App Mesh 和 Lattice API；仅凭代理部署位置无法证明某项功能不可能实现
   - C) 这些功能无法通过 HTTP/2 工作
   - D) IAM 策略可以替代这些功能，因此不需要考虑

<details>

<summary>显示答案</summary>

**答案：B) 比较实际的 App Mesh 和 Lattice API；仅凭代理部署位置无法证明某项功能不可能实现**

**解释：**
通用 Envoy/Istio 功能并不会自动成为 App Mesh 功能。应盘点已配置的控制项，并针对当前产品 API 的缺口，选择应用或代理层面的替代方案。
</details>

2. 为什么说 App Mesh 的 VirtualNode 不能与 VPC Lattice Target Group 一一对应？
   - A) 可以创建很多 VirtualNode，但只能创建一个 Target Group
   - B) VirtualNode 包含的身份、后端、连接池和异常检测属性，要么分散到多个位置，要么会消失
   - C) Target Group 不支持 Lambda
   - D) VirtualNode 依赖 Cloud Map，因此无法转换

<details>

<summary>显示答案</summary>

**答案：B) VirtualNode 包含的身份、后端、连接池和异常检测属性，要么分散到多个位置，要么会消失**

**解释：**
VirtualNode 将“工作负载是谁（身份）、请求发往何处（后端），以及如何接收流量（listener、健康检查、连接池、异常检测）”集中在一个资源中。在 Lattice 中，只有目标集合和健康检查会映射到 Target Group；“请求发往何处”由身份验证策略和 IAM 权限决定；“工作负载是谁”由 IAM Role 表示；连接池和异常检测则没有对应资源。映射表对照的是资源名称，而不是功能能力。
</details>

3. 哪项是合适的可观测性迁移任务？
   - A) Circuit breaking：这是最难实现的功能
   - B) 保留应用追踪，并替换旧代理实际提供的遥测数据
   - C) 流量镜像：完全没有替代方案
   - D) 故障注入：对生产事故响应至关重要

<details>

<summary>显示答案</summary>

**答案：B) 保留应用追踪，并替换旧代理实际提供的遥测数据**

**解释：**
Lattice 没有原生 trace span，但仍可使用应用 span。应将它们与 Lattice 请求 ID、访问日志时间信息以及客户端/服务器观测结果关联起来。
</details>

4. 如果 AWS Gateway API Controller 停止运行，会发生什么？
   - A) 所有流量立即被阻止
   - B) 流量仍会继续转发，但新启动的 Pod 不会注册为 Target，已终止的 Pod 也不会注销
   - C) Lattice Service 会被自动删除
   - D) IAM 身份验证会被禁用

<details>

<summary>显示答案</summary>

**答案：B) 流量仍会继续转发，但新启动的 Pod 不会注册为 Target，已终止的 Pod 也不会注销**

**解释：**
Controller 的核心职责是让 Kubernetes 声明状态与 Lattice 实际目标列表保持同步：它会监视 `backendRefs` 所引用 Service 的 endpoint 变化，并注册/注销 Target。如果 Controller 停止运行，Lattice 会继续使用最后已知的目标列表转发流量，但列表会逐渐过时。因此，Controller Deployment 的可用性和 IAM 权限会直接影响数据路径的可靠性。
</details>

5. 同时运行 ingress-nginx 的环境中，关于迁移范围，哪项说法正确？
   - A) ingress-nginx 也必须迁移到 Lattice
   - B) AWS Gateway API Controller 目前只通过 Lattice 处理 East-West 流量，因此 ingress-nginx 处理的 North-South 流量不在范围内；两条路径共存是正常结果
   - C) ingress-nginx 与 Lattice 不能同时使用
   - D) Gateway API Controller 也会处理 North-South 流量，因此应立即移除 ingress-nginx

<details>

<summary>显示答案</summary>

**答案：B) AWS Gateway API Controller 目前只通过 Lattice 处理 East-West 流量，因此 ingress-nginx 处理的 North-South 流量不在范围内；两条路径共存是正常结果**

**解释：**
Kubernetes Gateway API 的设计范围包括 North-South（Ingress）和 East-West（Mesh）流量，但 AWS Gateway API Controller 目前只侧重 East-West。类似 ALB/NLB 的 North-South 功能由 AWS Load Balancer Controller 提供。因此，ingress-nginx 处理的入口流量不属于此次迁移范围；迁移到 Lattice 的只有 East-West 流量，两条路径预期会共存。
</details>

6. 在 Lattice 环境中，为什么要使用 Pod readiness gate？
   - A) 限制 Pod 的 CPU 使用量
   - B) 只有 Lattice Target Group 健康状态为 Healthy 后，Pod 才会标记为 Ready，避免新 Pod 健康前滚动更新就终止旧 Pod
   - C) 等待 IAM 凭证就绪后才允许流量
   - D) 等待 Envoy sidecar 注入

<details>

<summary>显示答案</summary>

**答案：B) 只有 Lattice Target Group 健康状态为 Healthy 后，Pod 才会标记为 Ready，避免新 Pod 健康前滚动更新就终止旧 Pod**

**解释：**
Kubernetes 可能已将 Pod 标记为 Ready，但 Lattice Target Group 还没有将其视为 Healthy。如果此时滚动更新终止旧 Pod，就会出现没有健康 Target 的时间窗口。Pod readiness gate 会将 Lattice 的健康状态与 Pod 的 Ready 条件关联起来，避免这种情况；这是迁移过程中实现零停机的重要机制。
</details>
