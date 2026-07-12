# Knative 测验

1. Knative Serving 中的 Scale-to-Zero 是如何工作的？
   - A) 删除 Pods，并在有新请求时重新创建 Deployment
   - B) 在 Autoscaler 将 replicas 从 0 扩展到 1 时，Activator 缓冲流量
   - C) 关闭 Nodes，并让 Karpenter 在请求到来时预置新的 Nodes
   - D) 暂停 containers，并在请求到来时恢复它们

<details>
<summary>显示答案</summary>

**答案：B) 在 Autoscaler 将 replicas 从 0 扩展到 1 时，Activator 缓冲流量**

**说明：**
当 replicas 为 0 时，传入请求会由 Activator 缓冲。Activator 会向 Autoscaler 请求扩容，一旦 Pods 准备就绪，已缓冲的请求就会被转发。这个过程就是 “cold start”，可以通过设置 `minScale` 来维持最小实例数，从而避免该过程。

</details>

---

2. KPA (Knative Pod Autoscaler) 和 HPA 的关键区别是什么？
   - A) KPA 仅基于 CPU，HPA 仅基于内存
   - B) KPA 基于 concurrency 进行扩缩容并支持 Scale-to-Zero，而 HPA 基于 CPU/内存进行扩缩容
   - C) KPA 扩缩 Nodes，HPA 扩缩 Pods
   - D) KPA 是手动扩缩容，HPA 是自动扩缩容

<details>
<summary>显示答案</summary>

**答案：B) KPA 基于 concurrency 进行扩缩容并支持 Scale-to-Zero，而 HPA 基于 CPU/内存进行扩缩容**

**说明：**
KPA 基于 Queue Proxy 测量的并发请求数或 RPS 进行扩缩容，并原生支持 Scale-to-Zero。HPA 基于 CPU/内存指标进行扩缩容，但始终要求至少有 1 个 replica。

</details>

---

3. 在 Knative Eventing 的 Broker/Trigger 模式中，Trigger 的作用是什么？
   - A) 生成 events 的 source
   - B) 从 Broker 过滤 events，并将其路由到特定 services
   - C) 用于 events 的持久化存储
   - D) 将 events 发送到外部系统的 gateway

<details>
<summary>显示答案</summary>

**答案：B) 从 Broker 过滤 events，并将其路由到特定 services**

**说明：**
Triggers 会注册到 Broker，并基于属性（type、source 等）过滤 CloudEvents。只有匹配的 events 会被传递给指定的 Subscriber（Knative Service、Kubernetes Service 等）。可以在单个 Broker 上注册多个 Triggers，以便将 events 路由到不同 services。

</details>

---

4. 在 Knative Service 上设置 `containerConcurrency: 1` 时会发生什么？
   - A) 每个 container 只创建 1 个 Pod
   - B) 每个 container 一次处理一个请求；额外请求会被路由到新的 Pods
   - C) 每秒只允许一个请求
   - D) 只维护一个 Revision

<details>
<summary>显示答案</summary>

**答案：B) 每个 container 一次处理一个请求；额外请求会被路由到新的 Pods**

**说明：**
`containerConcurrency: 1` 会配置每个 Pod 中的 Queue Proxy，使其一次只向 container 转发一个并发请求。当额外请求到达时，Autoscaler 会创建新的 Pods。这对 CPU 密集型任务或非线程安全的应用程序很有用。

</details>

---

5. 同时使用 KEDA 和 Knative 的适当场景是什么？
   - A) 这两个工具不兼容；只能使用其中一个
   - B) 对 HTTP workloads 使用 Knative Serving，对基于 queue/stream 的 async workloads 使用 KEDA
   - C) 使用 KEDA 实现 Scale-to-Zero，使用 Knative 进行 event routing
   - D) Knative 在内部使用 KEDA

<details>
<summary>显示答案</summary>

**答案：B) 对 HTTP workloads 使用 Knative Serving，对基于 queue/stream 的 async workloads 使用 KEDA**

**说明：**
Knative Serving 针对基于 HTTP 请求的 serverless workloads 进行了优化，支持 Scale-to-Zero 和基于 concurrency 的扩缩容。KEDA 擅长基于来自 SQS、Kafka、Redis 等的 queue metrics 进行扩缩容。同时使用两者，可以分别以最佳方式扩缩同步和异步 workloads。

</details>

---

6. 如何在 Knative 中使用 traffic splitting 实现 Canary deployments？
   - A) 调整 Deployment replicas
   - B) 在 Knative Service 的 spec.traffic 中按 Revision 指定流量百分比
   - C) 手动创建 Istio VirtualService
   - D) 调整 HPA minReplicas

<details>
<summary>显示答案</summary>

**答案：B) 在 Knative Service 的 spec.traffic 中按 Revision 指定流量百分比**

**说明：**
Knative Service 中的 `spec.traffic` 字段允许按 Revision 指定流量百分比。例如，对于 canary deployment，可以将 90% 分配给现有 Revision，将 10% 分配给新 Revision。使用 `@latest` 引用最新 Revision，或直接指定 Revision 名称。

</details>

---

7. Knative 中 Dead Letter Sink 的目的是什么？
   - A) 归档已删除的 Knative Services
   - B) 将失败的 events 发送到单独的目标，以防止 event loss
   - C) 清理过期的 Revisions
   - D) 存储 debug logs

<details>
<summary>显示答案</summary>

**答案：B) 将失败的 events 发送到单独的目标，以防止 event loss**

**说明：**
当重试后仍投递失败时，Dead Letter Sink 会将 events 转发到指定目标（另一个 Knative Service、Kubernetes Service 等）。这可以防止 event loss，并支持对失败的 events 进行分析或重新处理。

</details>

---

8. 在 Knative Serving 中最有效地减少 cold starts 的方法是什么？
   - A) 无限减小 container image 大小
   - B) 使用 `minScale` annotation 维持最小实例数，并使用轻量级 images 和启动快速的 frameworks
   - C) 完全禁用 Scale-to-Zero
   - D) 始终将 Nodes 保持在最大数量

<details>
<summary>显示答案</summary>

**答案：B) 使用 `minScale` annotation 维持最小实例数，并使用轻量级 images 和启动快速的 frameworks**

**说明：**
将 `autoscaling.knative.dev/min-scale` 设置为 1 或更高可以防止 cold starts。将其与轻量级 base images（distroless、alpine）、GraalVM Native Image 等启动快速的 frameworks，以及 `initialScale` 设置结合使用，可以最大限度地降低 cold start 延迟。

</details>
