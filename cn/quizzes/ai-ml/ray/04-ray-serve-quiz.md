# Ray Serve 测验

## 多项选择题

1. Serve Deployment 与 Kubernetes Deployment 有何关系？
   - A) 它们完全相同
   - B) 它是一个逻辑 actor-replica 单元，而非与 Pod 一一对应
   - C) 每个 replica 都需要一个 EC2 节点
   - D) Serve 不使用 actor

<details>
<summary>显示答案</summary>

**答案：B**

一个 Ray Pod 可以托管多个 replica actor。
</details>

2. 2.58.0 的默认 proxy 位置是什么？
   - A) 始终在 head 上设置一个
   - B) 在托管 replicas 的节点上使用 EveryNode
   - C) 无条件地在每个 EC2 节点上
   - D) 始终为 Disabled

<details>
<summary>显示答案</summary>

**答案：B**

HeadOnly 和 Disabled 是显式选项。请区分过时的架构说明与当前 API。
</details>

3. 默认 Deployment 与 num_replicas="auto" 有何不同？
   - A) 两者都会立即启动 100 个 replicas
   - B) 默认值固定为 1；auto 使用最小值 1/最大值 100/目标值 2
   - C) 默认 GPU 为 1；auto GPU 为 100
   - D) 两者都不支持 autoscaling

<details>
<summary>显示答案</summary>

**答案：B**

直接构建的 AutoscalingConfig 的默认最大值为 1，因此请指定预期的边界。
</details>

4. max_queued_requests 的作用域是什么？
   - A) 一个集群全局队列
   - B) 每个调用方，例如 proxy 或 handle
   - C) GPU KV-cache 容量
   - D) RayCluster Pod 数量

<details>
<summary>显示答案</summary>

**答案：B**

默认值 -1 表示无限制；超过配置的边界可能会拒绝 HTTP 请求，或引发 handle BackPressureError。
</details>

5. pending replica actor 是否总会创建新的 Pod 和 EC2 节点？
   - A) 始终一一对应
   - B) 不会；现有容量、group 边界、placement 和 autoscaler 是否启用都会产生影响
   - C) 它会自动变成 CPU 模型
   - D) Serve 直接创建 EC2 节点

<details>
<summary>显示答案</summary>

**答案：B**

请分别检查 actor placement、Pod 大小和节点配置。
</details>

6. 关于 2.58.0 LLM backends，验证了什么？
   - A) 仅存在 vLLM
   - B) 存在 vLLM 和 SGLang backends；请分别检查它们的 dependencies/configuration
   - C) 每个 engine kwarg 在所有 engine 中都完全相同
   - D) ray[serve]includes 所有 LLM weights

<details>
<summary>显示答案</summary>

**答案：B**

Inference dependencies 以及 model access/downloads 是独立的。CPU 检查并未验证 LLM execution。
</details>

7. 哪项关于 RayService 更新的说法是准确的？
   - A) 对于每个 EKS deployment 都是强制性的，并保证零停机时间
   - B) 它是可选的 lifecycle 路径；请验证 strategy、Gateway、capacity、readiness 和 draining
   - C) 始终只会编辑现有 Pod image
   - D) 所有长 streams 始终都会被保留

<details>
<summary>显示答案</summary>

**答案：B**

请区分 application changes、cluster transitions 和 actor reconfiguration。
</details>

8. 本地 Echo 测试验证了什么？
   - A) GPU 性能
   - B) LLM 质量
   - C) HTTP 200 和 DeploymentHandle 调用
   - D) 多节点 autoscaling

<details>
<summary>显示答案</summary>

**答案：C**

这是一个微型的单节点 CPU 测试，不包含 model、LLM、GPU 或 cloud deployment。
</details>

## 简答题

9. 为什么要区分最大 ongoing、autoscaling target 和 caller queue limit？

<details>
<summary>显示答案</summary>

它们控制不同的事物：分配给 replicas 的请求、用于 scaling 的目标负载，以及每个 caller 的等待请求。一个设置并不能确定所有其他边界或 latency guarantees。
</details>

10. 为什么 cluster tokens 或 ClusterIP 不能完成 application security？

<details>
<summary>显示答案</summary>

请分别验证 TLS、每个 entry point 的 authentication/authorization、model-artifact permissions、sensitive request/log handling，以及 resource/queue/timeout policies。
</details>

---

[返回学习材料](../../../ai-ml/ray/04-ray-serve.md)
