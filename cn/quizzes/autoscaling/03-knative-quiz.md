# Knative 测验

> **最后更新**：2026 年 9 月 11 日

1. Knative Serving 如何实现缩容到零（Scale-to-Zero）？
   - A) 删除 Pod，并在收到新请求时重新创建 Deployment
   - B) Activator 在自动扩缩容路径启动就绪副本期间缓冲符合条件的请求
   - C) 关闭节点，并在收到请求时让 Karpenter 配置新节点
   - D) 暂停容器，并在收到请求时恢复

<details>
<summary>显示答案</summary>

**答案：B) Activator 在自动扩缩容路径启动就绪副本期间缓冲符合条件的请求**

**解释：**
副本数为零时，请求路由路径会经过 Activator。Activator 会在自身容量和超时限制内缓冲请求，同时激活流程创建就绪容量。缓冲区耗尽、激活失败或客户端/请求超时仍可能导致错误。设置大于零的 `min-scale` 可避免正常空闲期间缩至零，但无法消除新 Revision、重启或额外副本的初始化过程。

</details>

---

2. Knative Serving 中的 KPA 和 HPA 集成有何区别？
   - A) KPA 只基于 CPU 扩缩容，HPA 只基于内存扩缩容
   - B) KPA 根据并发量扩缩容并支持缩容到零，HPA 根据 CPU/内存扩缩容
   - C) KPA 扩缩节点，HPA 扩缩 Pod
   - D) KPA 手动扩缩容，HPA 自动扩缩容

<details>
<summary>显示答案</summary>

**答案：B) KPA 根据并发量扩缩容并支持缩容到零，HPA 根据 CPU/内存扩缩容**

**解释：**
Knative KPA 支持根据并发量/RPS 扩缩容，并支持基于 Activator 的缩容到零路径。可选的 Knative HPA 扩展支持 CPU、内存和受支持的自定义 Pod 指标，但不实现该缩容到零路径。这不是对 Kubernetes HPA 的普遍断言：上游 Kubernetes 1.37 为对象/外部指标提供了 beta 版缩容到零能力。在 1.23 版 HPA 实现中，CPU 目标是相对于 CPU requests 的利用率百分比，内存目标以 MiB 表示，自定义指标则使用每个 Pod 的平均值。

</details>

---

3. 在 Knative Eventing 的 Broker/Trigger 模式中，Trigger 起什么作用？
   - A) 生成事件的 source
   - B) 从 Broker 过滤事件，并将其路由到指定服务
   - C) 事件的持久化存储
   - D) 向外部系统发送事件的网关

<details>
<summary>显示答案</summary>

**答案：B) 从 Broker 过滤事件，并将其路由到指定服务**

**解释：**
Trigger 为一个 Broker 描述过滤规则和 subscriber；实际投递由 controller 与 Broker 数据面实现。多个匹配的 Trigger 可能分别投递同一事件的副本，重试和后备存储行为取决于具体实现与策略。Trigger 不是持久化事件存储，也不是通用的 consumer 自动扩缩器。

</details>

---

4. 在 Knative Service 中设置 `containerConcurrency: 1` 会怎样？
   - A) 每个容器只创建一个 Pod
   - B) Queue Proxy 每个 Pod 至多向容器转发一个并发请求，等待时间有限，并异步扩缩容
   - C) 每秒只允许一个请求
   - D) 只保留一个 Revision

<details>
<summary>显示答案</summary>

**答案：B) Queue Proxy 每个 Pod 至多向容器转发一个并发请求，等待时间有限，并异步扩缩容**

**解释：**
Queue Proxy 限制每个 Pod 转发给接收容器的并发请求数。额外请求可能在有界队列中等待、发送到可用容量，或失败。自动扩缩容是异步的，并受限额和节点容量约束。这既不代表每秒只能处理一个请求，也不代表所有副本总共只能处理一个请求，更不保证每个额外请求都会创建一个 Pod。

</details>

---

5. 什么场景适合同时使用 KEDA 和 Knative？
   - A) 两种工具不兼容；只能选一个
   - B) 使用 Knative Serving 运行 HTTP 工作负载，使用 KEDA 运行基于队列/流的异步工作负载
   - C) 让 KEDA 和 KPA 分别扩缩同一个 Knative 生成的 Deployment
   - D) 每个 Knative Service 都会自动安装 KEDA，并将其设为默认扩缩器

<details>
<summary>显示答案</summary>

**答案：B) 使用 Knative Serving 运行 HTTP 工作负载，使用 KEDA 运行基于队列/流的异步工作负载**

**解释：**
对合适的 HTTP 服务使用 Knative Serving，对独立管理的后台 worker 使用 KEDA。配置队列保留和确认机制、激活指标以及 worker 幂等性。不要让 KEDA 与 KPA 分别控制同一个生成的 Deployment。SinkBinding 用于配置事件生产者；它不会唤醒已缩容到零的任意 HTTP consumer。

</details>

---

6. 如何使用 Knative 的流量拆分来实现 Canary 部署？
   - A) 调整 Deployment 的副本数
   - B) 在 Knative Service 的 `spec.traffic` 中为每个 Revision 指定流量百分比
   - C) 手动创建 Istio VirtualService
   - D) 调整 HPA 的 minReplicas

<details>
<summary>显示答案</summary>

**答案：B) 在 Knative Service 的 `spec.traffic` 中为每个 Revision 指定流量百分比**

**解释：**
`spec.traffic` 包含显式的 `revisionName` 目标，或带有流量百分比的 `latestRevision: true`。`@latest` 是 `kn` CLI 的简写，不是 `revisionName` 的取值，也不是表示 latest 的 API tag。所引用的 Revision 必须存在且已就绪；路由协调不是瞬间的全局切换，已有请求也可能继续由旧 Revision 处理。

</details>

---

7. Knative 中 Dead Letter Sink 的用途是什么？
   - A) 归档已删除的 Knative Service
   - B) subscriber 投递失败时，尝试投递到配置的备用目标
   - C) 清理过期 Revision
   - D) 存储调试日志

<details>
<summary>显示答案</summary>

**答案：B) subscriber 投递失败时，尝试投递到配置的备用目标**

**解释：**
配置的 DLS 会在投递策略无法将事件交付给 subscriber 后，尝试将事件发送到备用目标。DLS 自身也可能失败；事件能否保留成功取决于传输方式和处理程序。只有在预期的存储/处理成功后才确认事件；必要时使用 CloudEvent 的 source 和 id 去重。

</details>

---

8. 哪种组合可以降低冷启动延迟，同时保留明确的预热容量策略？
   - A) 无限缩小容器镜像
   - B) 使用 `minScale` annotation 维持最小实例数，并采用轻量镜像和启动快的框架
   - C) 完全禁用缩容到零
   - D) 始终将节点数保持在最大值

<details>
<summary>显示答案</summary>

**答案：B) 使用 `minScale` annotation 维持最小实例数，并采用轻量镜像和启动快的框架**

**解释：**
设置大于零的 `autoscaling.knative.dev/min-scale` 可在普通空闲时段维持基准容量；`initial-scale` 则适用于新 Revision 首次创建时。镜像大小、节点是否可用、镜像缓存、启动过程和就绪行为都会影响延迟。新 Revision、重启以及超出预热基准的扩容仍可能发生冷启动；应使用有代表性的流量进行测量，不要承诺完全消除冷启动。

</details>
