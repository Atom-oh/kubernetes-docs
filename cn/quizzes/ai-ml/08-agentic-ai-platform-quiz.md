# EKS 上的 Agentic AI 平台测验

关于当前 API、执行边界和验证限制的 20 个问题。

## 1. PagedAttention 主要改善什么？

<details>
<summary>答案与说明</summary>

KV-cache 块管理和内存浪费。它不会压缩模型权重，也不保证固定的 2–4 倍吞吐量。
</details>

## 2. 推理网关与训练执行器有何不同？

<details>
<summary>答案与说明</summary>

受支持的网关/插件处理推理路由、访问和限制。Trainer/Ray 及其他系统执行训练。仅安装网关并不会启用所有安全或 A/B 功能。
</details>

## 3. RAG 向量存储中哪些内容必须匹配？

<details>
<summary>答案与说明</summary>

实际 embedding 维度、模型修订版本、归一化、度量方式以及摄取/查询行为。仅有 tenant 字段并不构成隔离；应通过服务端过滤器强制执行经身份验证的检索范围。
</details>

## 4. LangGraph 提供什么控制模型？

<details>
<summary>答案与说明</summary>

有状态节点、边、条件路由和循环。图本身并不实现工具执行、持久化状态或有界重试。
</details>

## 5. Langfuse 和 DCGM 有何不同？

<details>
<summary>答案与说明</summary>

Langfuse 跟踪已埋点的调用、trace、用量和评估；DCGM 报告设备指标。token 成本估算不是账单，并且不同于 GPU 温度等基础设施测量值。
</details>

## 6. Kagent 0.10.1 使用什么 API 形态？

<details>
<summary>答案与说明</summary>

使用带有 spec.type 和 declarative/BYO 的 kagent.dev/v1alpha2。应使用 declarative.modelConfig 以及 McpServer/Agent 工具引用，而非虚构的顶层 llm、任意 python/eval 工具定义或 permissions 字段。
</details>

## 7. MIG 内部的时间切片提供什么隔离？

<details>
<summary>答案与说明</summary>

应区分 MIG 实例之间的隔离与单个实例内部的共享。同一实例内的时间切片用户不会获得新的内存/故障隔离，也没有按比例计算资源的保证。
</details>

## 8. 连续批处理是否意味着请求永远不会等待？

<details>
<summary>答案与说明</summary>

不是。调度可以在每一步接纳工作，但 token 预算、KV 容量、并发度和队列限制都会导致等待。应测量实际工作负载行为。
</details>

## 9. 何时 chunk size 1000 表示 1000 个 token？

<details>
<summary>答案与说明</summary>

当所选 splitter 使用适当的 tokenizer 测量 token 时。RecursiveCharacterTextSplitter 默认按字符计数。应一并评估模型限制、语义单元和检索质量。
</details>

## 10. vLLM 自动扩缩容必须检查什么？

<details>
<summary>答案与说明</summary>

实际的 vllm: 指标名称、模型/Pod 标签、adapter、队列/延迟信号以及一个扩缩容所有者。分配量不是 GPU 利用率；避免让 HPA/KEDA 竞争控制相同的 replica。
</details>

## 11. KV cache 存储什么？

<details>
<summary>答案与说明</summary>

先前 token 的键/值表示，以减少重复计算。它不同于响应缓存；GQA/MQA、滑动窗口及其他架构会改变内存核算方式。
</details>

## 12. 当前 Langfuse SDK 如何处理 trace 和 span？

<details>
<summary>答案与说明</summary>

使用 start_as_current_observation 在一个 trace 下创建子 span/generation observation，并记录 usage_details。经检查的 SDK 4.15.2 没有旧的 trace()/generation() 方法。还应定义 secret/原始数据的日志记录边界。
</details>

## 13. 为什么混合搜索不仅仅是两次搜索调用？

<details>
<summary>答案与说明</summary>

它需要 RRF 或经过校准的分数融合、等效的授权过滤器、去重和召回率评估。来自不同 retriever 的分数并不会自动具有可比性。
</details>

## 14. 原始 SqliteSaver 示例有什么问题？

<details>
<summary>答案与说明</summary>

应将 from_conn_string 用作上下文管理器。:memory: 不持久，并且 PostgreSQL DSN 不是 SQLite。仅读取历史记录并不能重放/恢复，而 thread_id 不是身份验证。
</details>

## 15. TP 和 PP 分别划分什么？

<details>
<summary>答案与说明</summary>

TP 划分层内的操作；PP 划分层阶段。应根据架构/backend/网络/内存限制选择，而不是采用通用的 2 的幂或按模型大小固定 GPU 数量。
</details>

## 16. 练习：当前 vLLM 部署应验证什么？

<details>
<summary>答案与说明</summary>

使用 [vLLM 指南](../../ai-ml/02-vllm-deployment.md)中的固定 image/model、GPU/cache/startupProbe 和 ClusterIP 示例。准备 namespace/driver/device。没有进行推理的 schema 检查不能证明性能或可用性。
</details>

## 17. 练习：Langfuse 部署和 Python trace 应验证什么？

<details>
<summary>答案与说明</summary>

使用[章节](../../ai-ml/03-agentic-ai-platform.md)中的当前 SDK 示例、文件凭据、span 关联以及 flush/shutdown。Chart 2.1.0 包含 web/worker、Postgres、Valkey、对象存储、ClickHouse 和 operator 前置条件。默认的 secret 环境交付方式不同于仅文件策略。
</details>

## 18. 练习：没有证据时，RAG 重试循环应如何安全终止？

<details>
<summary>答案与说明</summary>

将原始问题与 search_query 分开，设置重试和递归边界，依据证据生成，在预算内重写，然后在未找到证据时拒绝回答。该章节通过本地确定性回调验证了这些路径和 SQLite 重新打开。
</details>

## 19. 高级：金融咨询 agent 需要哪些边界？

<details>
<summary>答案与说明</summary>

设计经过身份验证的 tenant/account 范围、检索权限、provider 出站访问、最小权限/幂等/已批准的工具、最少的敏感日志、审计和人工交接。不要在后续分支中将已有的 requires_human=true 覆盖为 false。compliance_check 函数名称或 LLM 决策并不能证明符合法规要求。
</details>

## 20. 高级：应如何验证多模型路由、A/B 和成本优化？

<details>
<summary>答案与说明</summary>

使用 provider adapter/凭据，并在没有候选项满足允许的 provider、预算和质量限制时拒绝。实现稳定的 A/B 分配、真实的路由消费者和经过测量的 guardrail。缓存键包括 tenant/authorization/model/retrieval 修订版本；成本估算包括路由调用、重试、缓存和 GPU 固定成本。虚构的节省百分比不是结果。
</details>

[返回章节](../../ai-ml/03-agentic-ai-platform.md)
