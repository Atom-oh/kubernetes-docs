# 在 EKS 上构建 Agentic AI 平台

> **审查基线**：Kagent 0.10.1 / Gateway Inference Extension 1.6.1 / LangGraph 1.2.11 / Langfuse SDK 4.15.2
> **最后更新**：September 12, 2026

Agentic AI 超越了简单的问答，能够自主制定计划、使用工具并迭代实现目标。本章介绍如何在 EKS 上设计 Agentic AI 平台及其运行边界。

## 1. Agentic AI 平台概述

### 什么是 Agentic AI？

Agentic AI 是一种具有以下特征的自主 AI 系统：

![带有授权、证据和重试预算的目标、规划、执行和评估，最终得到结果或选择弃答。](../.gitbook/assets/en-ai-ml-03-agentic-ai-platform-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-03-agentic-ai-platform-0.html)

1. **自主规划**：将复杂任务分解为子任务，并确定执行顺序。
2. **基于工具的执行**：使用包括外部 API、数据库和代码执行器在内的多种工具。
3. **迭代改进**：评估执行结果，并按需修改计划。
4. **状态管理**：为长时间运行的任务维护状态和记忆。

### 何时选择 Kubernetes

Kubernetes 为 Agentic AI 平台提供以下核心能力：

| 需求 | Kubernetes 解决方案 |
|-------------|---------------------|
| GPU 编排 | Device Plugin, GPU Operator, MIG |
| 自动扩缩容 | HPA, VPA, Karpenter |
| 多租户隔离 | RBAC, Namespace, 强制执行的 NetworkPolicy, workload identity |
| 高可用性 | replicas, probes, 放置和恢复测试 |
| Service Mesh | 已配置的 gateway/mesh 实现 |
| 成本优化 | Spot 实例, Node 整合 |

### 四项关键技术挑战

构建 Agentic AI 平台时需要解决的关键挑战：

![GPU 放置、provider 集成、独立的 LangGraph 和 Kagent ADK runtime，以及具有强制预算的成本测量。](../.gitbook/assets/en-ai-ml-03-agentic-ai-platform-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-03-agentic-ai-platform-1.html)

---

## 2. GPU 和成本基线

使用外部模型 API 的 Agent 不一定需要 GPU。自托管推理需要根据权重/精度、KV cache、并发量、CPU 架构和 driver 兼容性选择设备。请使用经审查的 [GPU 指南](01-ai-ml-workloads.md)，并避免在 AL2023 NVIDIA AMI 上重复安装 driver/toolkit。

MIG 对支持的 GPU 进行分区。在单个 MIG 实例内进行 time-slicing，不会在其共享 workload 之间增加内存/故障隔离；它不是软件安全边界。同样，80 GB 通常无法容纳 70B FP16 权重。

GPU Operator Helm values 与 ConfigMap/HelmRelease 资源不同。将 Flux HelmRelease 作为 helm --values 传递不会应用预期设置。MIG manager ConfigMap 引用、profile Node label 和 plugin strategy 必须保持一致。device-plugin.config label 选择的是配置键，而不是 ConfigMap 名称。MIG 重新配置可能中断 workload，本次审计未执行该操作。

价格需要包含 region/OS/购买模式/日期及 quota 上下文。此前没有来源支撑的小时价格表和固定节省百分比并非当前定价证据。应将自托管的 GPU 总空闲时间、存储/传输、运维和恢复成本，与测得的成功吞吐量进行比较。

## 3. 模型服务（vLLM）

### vLLM 架构

vLLM 通过以下核心技术提供高性能 LLM 推理：

![PagedAttention、continuous batching、prefix caching 和 chunked prefill，以及依赖 workload 的内存、吞吐量和延迟测量。](../.gitbook/assets/en-ai-ml-03-agentic-ai-platform-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-03-agentic-ai-platform-2.html)

### 经审查的服务路径

请使用[当前 vLLM 指南](02-vllm-deployment.md)了解 0.29.0 image/model revision、startup probe、私有 Service 和实际 CLI 选项。单 GPU NodePool 无法放置原先的四 GPU/200Gi Pod。应区分 TP/PP group 与独立 replica，并计算内存需求。

Prefix cache 会重用受支持的 KV prefix，而不是完整响应。GPU memory utilization 并非仅是 KV-cache 占比，且当前 CLI 中没有 swap-space。llm-d 解耦并不是带有 role 参数的两个虚构 prefill/decode image；应验证其实际 release 的 model server、KV connector、scheduler、gateway 以及硬件/网络组合。

## 4. 推理网关

### 基于 Gateway API 的 AI Workload 路由

扩展 Kubernetes Gateway API，以高效路由 AI 推理 workload。

### Kgateway + InferencePool 架构

![HTTPRoute 引用 InferencePool；gateway 使用 EPP selection 代理至模型 Pod。配置资源与代理 hop 是不同的概念。](../.gitbook/assets/en-ai-ml-03-agentic-ai-platform-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-03-agentic-ai-platform-3.html)

#### InferencePool v1

Gateway API 和 Gateway API Inference Extension 是不同的 API。Extension 1.6.1 使用带有 targetPorts 和 endpointPickerRef 的 inference.networking.k8s.io/v1。先前虚构的 EndpointPicker CRD/endpointPickerConfig 并非此 schema。

这个通过 schema 检查的示例需要位于 9002 的 EPP Service、模型 Pod 和支持的 gateway controller。InferencePool 本身不会配置 authentication、rate limit 或 prefix-aware 选择算法。

```yaml
apiVersion: inference.networking.k8s.io/v1
kind: InferencePool
metadata:
  name: model-pool
  namespace: ai-inference
spec:
  selector:
    matchLabels:
      app: vllm-demo
  targetPorts:
    - number: 8000
  endpointPickerRef:
    name: model-epp
    kind: Service
    group: ""
    port:
      number: 9002
    failureMode: FailClose
```

selector 仅匹配同一 Namespace 中的 Pod。EndpointPickerRef 默认是 Service 引用和 FailClose。应一并验证 HTTPRoute、EPP 配置/version 支持、TLS 和 gateway status。API 定义或 Kgateway 安装并不会启用每项 plugin capability。

### LiteLLM 1.100.1 Provider Gateway

LiteLLM provider adaptation 和 InferencePool endpoint selection 属于不同层。Provider API 在 path、authentication、payload、response 和 streaming 方面各不相同；将 OpenAI JSON 原样转发至 Anthropic endpoint 并不是有效的 adapter。

下面是当前 Router fallback 形式。将 proxy command/args 连接到实际 config file，并在需要时单独提供 Redis/database、credentials 和 callback。

```yaml
model_list:
  - model_name: local-primary
    litellm_params:
      model: openai/qwen3-demo
      api_base: http://vllm-demo.ml-inference:8000/v1
  - model_name: local-fallback
    litellm_params:
      model: openai/qwen3-demo
      api_base: http://vllm-secondary.ml-inference:8000/v1
router_settings:
  fallbacks:
    - local-primary: [local-fallback]
  num_retries: 0
```

这说明了配置方式，前提是 endpoint 和 authentication 已准备就绪。应向应用 client 提供 scoped credentials，而不是 master key。外部 fallback 是数据外流路径：在路由前应强制执行租户的 provider/data policy。由模型选择的名称或 client header 不得绕过此政策。


## 5. RAG 数据和检索边界

最新检查的 Milvus release 是 3.0.1；另行审查的 Operator 1.3.9 默认使用 Milvus 2.6.11。它们不是同一个版本，宽泛的 compatibility table 不能证明已测试的 3.x upgrade。Operator repository 为 https://zilliztech.github.io/milvus-operator/，与普通 Milvus chart repository 分开。

Vector dimension 必须与实际 embedding output 匹配。应为 ingestion 和 query 记录 revision、dimension options、tokenizer、normalization 和 distance metric。Index parameter 各不相同；不能简单将 HNSW M/efConstruction 用于 GPU_IVF_FLAT。GPU indexing 需要兼容的 image、version、device 和 component role；在 indexNode 上请求 GPU 并不等同于自动加速。

仅有 tenant_id field 不会强制隔离。应从经过 authentication 的 identity 派生 scope，应用服务端 retrieval filter，并验证返回的 document。还要管理 document deletion/change 和 embedding-version lifecycle。

### 分块和混合搜索

当前 splitter import 使用 langchain_text_splitters。RecursiveCharacterTextSplitter 的 chunk_size 默认单位是字符，而不是 token。Token splitting 必须与 embedding model 的 tokenizer 和实际 input limit 匹配。Semantic chunking 会增加 embedding call/成本，且不保证质量更好。

Hybrid search 需要 RRF 或校准后的 score 等 fusion，而不只是两次搜索，并且应使用相同的 authorization filter。评估 recall、precision 和 latency。应限制重试次数，并在没有证据时弃答，而不是在重试耗尽后始终生成结果。


## 6. AI Agent 部署（Kagent）

### Kagent 概述

Kagent 是 Kubernetes-native 的 AI agent lifecycle management 工具。

![Kagent controller 协调 v1alpha2 Agent 资源，并管理一个使用已批准 ModelConfig、MCP tool 和已配置 session storage 的 ADK runtime。](../.gitbook/assets/en-ai-ml-03-agentic-ai-platform-4.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-03-agentic-ai-platform-4.html)

### Kagent 0.10.1 Agent API

Kagent 不限于自动执行 kubectl。Declarative agent 使用 Go/Python ADK runtime；BYO 托管用户提供的 A2A agent。LangGraph 是一个独立集成的 workflow framework，并非与 Kagent 相同的 runtime。

此 Agent 引用单独批准/配置的同 Namespace ModelConfig 和 RemoteMCPServer 资源。应提供实际的 MCP service/search_documents tool、authentication、TLS 和数据权限。它既不会创建该 tool，也不会授予 Kubernetes write access。

```yaml
apiVersion: kagent.dev/v1alpha2
kind: Agent
metadata:
  name: research-agent
  namespace: ai-agents
spec:
  type: Declarative
  description: Retrieves authorized documents and cites their sources
  declarative:
    runtime: go
    modelConfig: approved-internal-model
    systemMessage: 'Use approved document tools. Cite retrieved sources.

      If evidence is missing, say so. Do not execute arbitrary code.

      '
    tools:
    - type: McpServer
      mcpServer:
        apiGroup: kagent.dev
        kind: RemoteMCPServer
        name: document-tools
        toolNames:
        - search_documents
    deployment:
      replicas: 1
      resources:
        requests:
          cpu: 250m
          memory: 256Mi
        limits:
          cpu: '1'
          memory: 1Gi
```

ModelConfig.apiKeySecret 不意味着 file delivery。检查的 OpenAI translator 会创建一个 OPENAI_API_KEY SecretKeyRef environment variable。在禁止 secret environment 的 policy 下，应使用经过验证的 file-credential BYO/runtime 或 authentication gateway path。未进行 token-delegation/audience 设计而启用 apiKeyPassthrough 并非替代方案。

使用 eval() 的 calculator 和虚构的 permissions field 不是安全边界。应在实际 tool server 中实施 least privilege、input validation、resource limit、approval 和 idempotency。Agent replica 不会自动使共享 memory/session store 高可用。

### 可执行的 LangGraph 控制流

此本地示例使用实际 SDK 和明确的 retrieve/rewrite/generate callback。其 demo 不调用 LLM 或 vector DB。它保留原始问题，将 rewrite 限制为两次，并在没有 document 时弃答。SQLite context manager 使用正确，并且在重新打开后检查了持久化 state。

```python
from typing import Callable, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver


class QAState(TypedDict):
    question: str
    search_query: str
    documents: list[str]
    answer: str
    retries: int


def build_graph(retrieve: Callable[[str], list[str]],
                rewrite: Callable[[str], str],
                generate: Callable[[str, list[str]], str]):
    def search(state: QAState):
        return {"documents": retrieve(state["search_query"])}

    def route(state: QAState):
        if state["documents"]:
            return "answer"
        return "rewrite" if state["retries"] < 2 else "abstain"

    def rewrite_query(state: QAState):
        return {"search_query": rewrite(state["search_query"]),
                "retries": state["retries"] + 1}

    def answer(state: QAState):
        return {"answer": generate(state["question"], state["documents"])}

    def abstain(state: QAState):
        return {"answer": "No supporting documents were found."}

    graph = StateGraph(QAState)
    graph.add_node("retrieve", search)
    graph.add_node("rewrite", rewrite_query)
    graph.add_node("answer", answer)
    graph.add_node("abstain", abstain)
    graph.add_edge(START, "retrieve")
    graph.add_conditional_edges("retrieve", route,
                               {"answer": "answer", "rewrite": "rewrite", "abstain": "abstain"})
    graph.add_edge("rewrite", "retrieve")
    graph.add_edge("answer", END)
    graph.add_edge("abstain", END)
    return graph


if __name__ == "__main__":
    # Deterministic local fixtures, not a vector database or LLM quality test.
    graph = build_graph(
        retrieve=lambda query: ["A Pod groups containers."] if query == "pod" else [],
        rewrite=lambda query: "pod",
        generate=lambda question, documents: documents[0],
    )
    initial = {"question": "What is a Pod?", "search_query": "unknown",
               "documents": [], "answer": "", "retries": 0}
    # Server-derived authorized tenant/session identity is required in a real app.
    config = {"configurable": {"thread_id": "tenant-a/session-1"}, "recursion_limit": 12}
    with SqliteSaver.from_conn_string("agent-state.sqlite") as saver:
        app = graph.compile(checkpointer=saver)
        print(app.invoke(initial, config)["answer"])
        print(app.get_state(config).values["retries"])
```

生产环境的 thread_id 必须绑定到经 authentication 的 tenant/session identity，并具备 DB authorization、encryption、concurrency 和 retention control。:memory: 无法在进程退出后保留。SqliteSaver 不能使用 PostgreSQL DSN；请使用相应的 Postgres saver。仅读取 get_state_history() 不会恢复执行——应使用 checkpoint configuration 和实际的 resume/replay semantics。

应针对 allowed enum 验证 supervisor output，并处理未知值/budget exhaustion。子字符串 COMPLETE 不得将 INCOMPLETE 视为成功。要求模型使用 tool 本身并不会执行或验证该 tool。

## 7. Langfuse 和运营可观测性

Langfuse SDK 4.15.2 使用 start_as_current_observation()、create_score() 及相关方法替代旧的 trace()/generation() API。本次审计使用 in-memory exporter 在一个 trace 中验证了三个 retrieval/generation/parent span，而非真实 server ingestion/storage/authentication。

```python
from pathlib import Path
from langfuse import Langfuse

# Read existing Secret-volume files; do not put credentials in source.
client = Langfuse(
    public_key=Path("/run/secrets/langfuse/public-key").read_text().strip(),
    secret_key=Path("/run/secrets/langfuse/secret-key").read_text().strip(),
    base_url="https://langfuse.example.internal",
)
with client.start_as_current_observation(name="rag", as_type="span"):
    with client.start_as_current_observation(name="retrieve", as_type="span") as span:
        span.update(metadata={"document_count": 2})
    with client.start_as_current_observation(name="generate", as_type="generation",
                                           model="prepared-model-alias") as generation:
        # Supply actual provider usage; these values only illustrate the shape.
        generation.update(usage_details={"input": 10, "output": 5})
client.flush()
client.shutdown()
```

Langfuse chart 2.1.0 引用 app 4.24.0，与最新检查的 server 4.35.0 不同。需要 Web/worker、PostgreSQL、Redis/Valkey、object storage 和 ClickHouse。该 chart 会检查 ClickHouse Operator/cert-manager prerequisite。离线渲染提供的是模拟的 API capability 信息，而不是已部署的 operator。默认 chart 包含 secret environment delivery，尚未获批用于仅文件凭据部署。

DCGM FB_USED 是一个数量而非百分比；请验证单位和总内存。GPU utilization80% 或 temperature85C 不是通用 health threshold。应一并观测 latency/queue/error/throttling 和实际 device limit。

### 响应缓存和成本

Cache key 必须包含 tenant/authorization scope、model/prompt/retrieved-data revision、generation setting 和相关 tool state。共享的 model+prompt key 可能重用其他用户的结果。对于私有或会变化的外部 state，应禁用 caching 或定义明确的 expiry/invalidation。

Token-price estimate 不是 invoice。应包含 cache read/write、batch、retry、routing call 和 self-hosted fixed cost。拒绝违反 budget、quality 或 provider policy 的 cheapest-model fallback。KEDA cron trigger 不会对其他 trigger 施加更低的 nighttime cap。应定义 CronJob timezone、concurrency/deadline/retry 和持久化结果。


## 8. 评估和质量管理

Ragas 0.4.3 无法针对解析出的 langchain-community 0.4.2 导入，因为它导入了已移除的 vertexai module。在一个单独环境中固定 langchain 0.3.27、core 0.3.79、community 0.3.31 和 openai integration 0.3.35 后，import 以及 SingleTurnSample/EvaluationDataset 构建均通过。不要假设这与当前 LangGraph 共享同一 dependency stack。

Faithfulness/AnswerRelevancy 等当前 collection API 需要显式 LLM/embedding adapter；旧的 ragas.metrics singleton import 会发出 deprecation warning。评估需要处理 model-call cost/failure、dataset/judge/prompt revision 和 missing/NaN。此处仅测试了 metric import/schema；未测量 0.92 等 quality score。

仅有 A/B ConfigMap 不会路由流量。应实现其真实 consumer/controller、稳定 assignment、等效 authorization/data context、足够的 sample 和 guardrail metric。任意 model quality/pricing table 都无法证明可节省 30–50%。

金融示例中的 compliance_check function 并不能证明满足 regulatory compliance。应设计经过 authentication 的 account scope、单调的 sensitive/approval condition（不要随后用 false 覆盖 true）、side-effect idempotency、audit 和 human handoff criteria。


## 9. 审查基线和验证范围

| 组件 | 基线 | 已验证范围 |
| --- | --- | --- |
| Kagent |0.10.1 / v1alpha2 | 官方 Helm/CRD 以及 Agent/ModelConfig/RemoteMCPServer schema |
| Inference Extension |1.6.1 / v1 | InferencePool schema；没有 live EPP/gateway |
| LiteLLM |1.100.1 | Router fallback 配置；没有 provider call |
| Milvus | server/SDK3.0.1; Operator 1.3.9 | Operator Helm/合成 vector schema；没有 database |
| LangGraph |1.2.11 + sqlite saver 3.1.1 | 有界 retrieval、弃答和 state recovery |
| Langfuse | SDK 4.15.2 / chart 2.1.0 | 本地 trace/span 和离线 chart 检查 |
| Ragas |0.4.3 | 兼容的隔离 import/schema；没有 evaluator model call |

Schema、Helm 和本地 SDK 检查不能证明完整平台部署、authentication、HA 或 GPU performance。未使用 cloud resource 或付费 model call。

## 10. 后续步骤

### 练习测验

为验证您对 Agentic AI 平台的理解，请完成以下测验：
- [Agentic AI 平台测验](../quizzes/ai-ml/08-agentic-ai-platform-quiz.md)

### 相关文档

- [vLLM 部署详细指南](./02-vllm-deployment.md) - vLLM 安装与优化详情
- [AI/ML Workload](./01-ai-ml-workloads.md) - Kubernetes 中的 AI/ML workload 管理

### 参考资料

- [Kagent 0.10.1](https://github.com/kagent-dev/kagent/tree/v0.10.1)
- [InferencePool v1 API](https://github.com/kubernetes-sigs/gateway-api-inference-extension/blob/v1.6.1/api/v1/inferencepool_types.go)
- [Milvus Operator 1.3.9](https://github.com/zilliztech/milvus-operator/tree/milvus-operator-1.3.9)
- [Langfuse SDK 4.15.2](https://github.com/langfuse/langfuse-python/tree/v4.15.2)
- [Langfuse Helm2.1.0](https://github.com/langfuse/langfuse-k8s/releases/tag/langfuse-2.1.0)
- [LangGraph 持久化](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LiteLLM Router](https://docs.litellm.ai/docs/routing)
- [Ragas 0.4.3](https://pypi.org/project/ragas/0.4.3/)
