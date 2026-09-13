# EKS 上的 AI 基础设施测验

关于当前 API 和运维边界的 15 道问题。

## 1. 什么是 JARK，它是否会自动完整配置？

<details>
<summary>答案与说明</summary>

JupyterHub/Argo Workflows/Ray/Karpenter 的一种集成模式。需要显式连接身份、提交、执行、Pod 放置、节点供给、存储和授权。
</details>

## 2. 将 JupyterHub 与 Cognito 配合使用时，必须配置什么？

<details>
<summary>答案与说明</summary>

Callback/token/userInfo URL、scope、稳定的用户名 claim 和允许策略。从准备好的文件中读取客户端密钥；在 provider 中单独配置 MFA/federation。认证成功并不意味着可以通用访问。
</details>

## 3. Ray head 和 Karpenter 分别承担什么角色？

<details>
<summary>答案与说明</summary>

GCS 是 Global Control Service；调度会与 raylet 交互。声明 CPU 的 head 可能会运行工作负载。Karpenter 根据 worker-Pod 需求和 Kubernetes 调度状态来配置节点。
</details>

## 4. 应如何比较 DRA 与 device plugin？

<details>
<summary>答案与说明</summary>

DRA 通过 DeviceClass/ResourceSlice/ResourceClaim 提供结构化请求、属性和分配。device plugin 也支持 MIG/time-slicing；它们并非在所有情况下都只能互斥使用。功能取决于 driver、硬件和 gate。
</details>

## 5. 关于 MIG profile 和隔离，有哪些要点？

<details>
<summary>答案与说明</summary>

3g.20gb 描述的是一个 profile，而不是三个 20GB device。MIG 会划分硬件，但不能替代 host/driver/authorization 隔离。MPS/time-slicing 不是安全边界。
</details>

## 6. 一个 GPU Operator 版本能否建立所有 DRA 支持？

<details>
<summary>答案与说明</summary>

不能。检查 Kubernetes API、driver/hardware/CDI 和各项 gate。Operator 26.7 的 GPUCluster 与 ClusterPolicy 互斥；standalone 0.5 提供了防止 device-plugin 冲突的 opt-in guard。
</details>

## 7. 集成 Langfuse 时应检查什么？

<details>
<summary>答案与说明</summary>

验证当前 SDK/backend 依赖项、DB/ClickHouse/object storage、文件凭证、tracing 以及敏感数据保留策略。旧的 2.x Deployment 或 trace() 调用不是当前的 4.x API。
</details>

## 8. 应如何选择 EFS、FSx 和 Mountpoint？

<details>
<summary>答案与说明</summary>

比较 I/O、authorization、namespace/PVC 范围、容量和 filesystem 语义。EFS 请求不是 quota；Mountpoint CSI 2.8 对现有 bucket 使用静态 PV，且并非完全 POSIX 兼容。
</details>

## 9. 应如何理解 EFA bandwidth 和 interface 数量？

<details>
<summary>答案与说明</summary>

区分实例 aggregate bandwidth 与每个 interface 的值；不要将已是 aggregate 的数值再次相乘。验证同一 AZ 放置、interface、driver/libfabric/NCCL、security group 和 Pod 资源。RAID0 不会启用 EFA。
</details>

## 10. 应如何理解 GPU memory 和 XID metric？

<details>
<summary>答案与说明</summary>

FB_USED/FREE 是以 MiB 为单位的 gauge；较高比例不一定表示 OOM。XID_ERRORS 是最后一个 code gauge，而不是可用于 increase() 的 counter。调查实际错误、cache、allocation failure 和特定 device 的限制。
</details>

## 11. Karpenter consolidation 会直接使用 GPU utilization metric 吗？

<details>
<summary>答案与说明</summary>

它使用 workload request、调度可行性、价格和 disruption constraint，而不是 DCGM 20% 阈值。limit/budget 并非绝对的成本或故障保障；应验证终止和恢复。
</details>

## 12. 谁发布 ResourceSlice，它们表示什么？

<details>
<summary>答案与说明</summary>

driver 使用带类型的 attribute/capacity 发布真实的 device inventory。创建任意 slice 并不会创建 GPU。CEL 和 matchAttribute 必须遵循实际发布的 schema。
</details>

## 13. 为 Milvus 请求 GPU 就能完成 RAG 吗？

<details>
<summary>答案与说明</summary>

不能。匹配受支持的 image/index、embedding dimension/revision、metric/parameter、tenant filtering 以及更新/删除生命周期。验证结果 authorization，并处理缺少 evidence 的情况。
</details>

## 14. 应如何调查 pending GPU Pod 和 node failure？

<details>
<summary>答案与说明</summary>

仅统计请求 GPU 的 pending Pod 无法诊断原因。检查 event、PVC、affinity、taint、quota、claim 和 image，并测试 checkpoint/resume。多个请求 GPU 的 container 在每个 Pod 中只计数一次。
</details>

## 15. MCP 是否提供标准的 Kubernetes auto-discovery gateway？

<details>
<summary>答案与说明</summary>

不是。它定义了诸如 tool listing/calling 的操作。选择实际的 server/gateway 版本、transport 和 authorization 设计。虚构的 image/label/config 或 URL environment variable 并不能实现 discovery/execution。
</details>

[返回指南](../../ai-ml/06-ai-infrastructure.md)
