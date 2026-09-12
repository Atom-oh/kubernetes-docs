# Ray 架构测验

## 选择题

1. 如何提交远程函数？
   - A) 正常调用 f(...)
   - B) 在 @ray.remote 函数上使用 f.remote(...)
   - C) 仅调用 ray.get(f)
   - D) 为每次调用创建一个 Pod

<details>
<summary>显示答案</summary>

**答案：B**

单返回值示例会产生一个 ObjectRef；ray.get 读取其值。
</details>

2. 所有 Ray 任务都是相互独立且无副作用的吗？
   - A) 是；Ray 从不跟踪依赖关系
   - B) 否；需要考虑 ObjectRef 依赖关系、副作用和重试
   - C) 只有 actor 会返回 ObjectRef
   - D) 每个函数都恰好执行一次

<details>
<summary>显示答案</summary>

**答案：B**

无状态执行单元并不保证纯函数或恰好执行一次。
</details>

3. 关于 actor 状态，哪项说法是准确的？
   - A) 实例内存在调用之间持续存在；故障恢复是独立的
   - B) 所有状态都会自动持久化
   - C) actor 仅在 head 节点上运行
   - D) 启用重启会恢复之前的内存

<details>
<summary>显示答案</summary>

**答案：A**

max_restarts 会重新运行构造函数；它不会替代 checkpoint 恢复。
</details>

4. 已验证的零拷贝范围是什么？
   - A) 所有 Python 对象和 GPU 内存
   - B) 每个节点共享的一块物理 RAM
   - C) 同一节点上只读的 NumPy 共享内存视图
   - D) 所有情况下网络传输成本均为零

<details>
<summary>显示答案</summary>

**答案：C**

修改需要复制。不要将其泛化到其他对象、GPU 或跨节点传输。
</details>

5. GCS 的名称和作用是什么？
   - A) Global Control Service；存储 actor、节点和 placement group 等集群元数据
   - B) 用于存储所有权重的 GPU Copy Store
   - C) Global Control Store；所有 ObjectRef 元数据的唯一所有者
   - D) Kubernetes API server 的替代品

<details>
<summary>显示答案</summary>

**答案：A**

Object ownership 元数据属于创建原始 ObjectRef 的进程，而不是普遍属于 GCS。
</details>

6. 两个节点各有一个空闲 CPU 时，能否执行一个需要两个 CPU 的任务？
   - A) 总是可以，因为它们的总和为两个
   - B) Ray 会自动将任务拆分成两半
   - C) 不可以；该任务必须能放入一个可行的节点
   - D) 如果内存可用，CPU 要求永远无关紧要

<details>
<summary>显示答案</summary>

**答案：C**

集群级别的选择仍取决于节点级别的资源可行性。
</details>

7. num_cpus=1 表示什么？
   - A) OS 将所有线程固定到一个核心
   - B) 逻辑上的 Ray 调度/准入要求，与 OS 限制分离
   - C) 保证独占一个物理核心
   - D) 自动施加 GPU 内存限制

<details>
<summary>显示答案</summary>

**答案：B**

Container 限制和库的线程设置是独立的。
</details>

8. KubeRay 的作用是什么？
   - A) 自动为应用选择 Train、Tune 或 Serve
   - B) 在 Kubernetes 上协调 Ray CR 和 Pod 生命周期
   - C) 替代 kube-scheduler
   - D) 为每个 Ray 任务创建一个新的 EC2 实例

<details>
<summary>显示答案</summary>

**答案：B**

Ray 工作调度、Pod 放置和 EC2 预置是不同的层。
</details>

## 简答题

9. 为什么 actor 适合在请求之间保持模型常驻？

<details>
<summary>显示答案</summary>

显式远程实例拥有该状态。不要依赖偶然的任务 worker 全局缓存复用来保证正确性。actor 故障仍需要 checkpoint 和恢复设计。
</details>

10. 为什么要将 GCS 恢复与对象及 actor 的应用恢复分开？

<details>
<summary>显示答案</summary>

持久化集群元数据、对象所有权/谱系/值恢复以及 actor checkpoint 解决的是不同问题。仅 Redis 或 alpha RocksDB 配置无法恢复所有值和应用状态。
</details>

---

[返回学习材料](../../../ai-ml/ray/01-architecture.md)
