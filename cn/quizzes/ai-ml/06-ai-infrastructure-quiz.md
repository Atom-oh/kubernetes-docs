# EKS 上的 AI 基础设施测验

关于当前 API 和运维边界的 15 道问题。

## 1. 什么是 JARK？它是否会自动形成完整方案？

<details>
<summary>答案与说明</summary>

JupyterHub/Argo Workflows/Ray/Karpenter 的一种集成模式。需要显式连接身份、提交、执行、Pod 放置、节点供给、存储和授权。
</details>

## 2. 将 JupyterHub 与 Cognito 配合使用时，必须配置什么？

<details>
<summary>答案与说明</summary>

回调/token/userInfo URL、作用域、稳定的用户名声明和访问允许策略。从准备好的文件中读取客户端密钥；在身份提供商中单独配置 MFA/联合身份。身份验证成功并不意味着可以访问所有资源。
</details>

## 3. Ray head 和 Karpenter 分别承担什么角色？

<details>
<summary>答案与说明</summary>

GCS 是 Global Control Service（全局控制服务）；调度会与 raylet 交互。声明可用 CPU 的 head 节点可能会运行工作负载。Karpenter 根据工作节点 Pod 的需求和 Kubernetes 调度状态提供节点容量。
</details>

## 4. 应如何比较 DRA 与设备插件？

<details>
<summary>答案与说明</summary>

DRA 通过 DeviceClass/ResourceSlice/ResourceClaim 提供结构化请求、属性和分配。设备插件也支持 MIG/时间切片，并非一律只能以设备独占方式分配。功能取决于驱动程序、硬件和特性开关。
</details>

## 5. 关于 MIG 配置方案（profile）和隔离，有哪些要点？

<details>
<summary>答案与说明</summary>

3g.20gb 描述的是一种配置方案，而不是三个 20GB 设备。MIG 会划分硬件，但不能替代主机/驱动程序/授权隔离。MPS/时间切片不是安全边界。
</details>

## 6. 仅凭一个 GPU Operator 版本，能否确认所有 DRA 功能都受支持？

<details>
<summary>答案与说明</summary>

不能。检查 Kubernetes API、驱动程序/硬件/CDI 和各项特性开关。Operator 26.7 的 GPUCluster 与 ClusterPolicy 互斥；独立版本 0.5 提供了需主动启用的保护机制，以防止与设备插件发生冲突。
</details>

## 7. 集成 Langfuse 时应检查什么？

<details>
<summary>答案与说明</summary>

验证当前 SDK/后端依赖项、数据库/ClickHouse/对象存储、文件凭证、追踪以及敏感数据保留策略。旧的 2.x Deployment 或 trace() 调用不是当前的 4.x API。
</details>

## 8. 应如何选择 EFS、FSx 和 Mountpoint？

<details>
<summary>答案与说明</summary>

比较 I/O、授权、命名空间/PVC 范围、容量和文件系统语义。EFS 请求不是配额；Mountpoint CSI 2.8 对现有存储桶使用静态 PV，且并非完全 POSIX 兼容。
</details>

## 9. 应如何理解 EFA 带宽和网络接口数量？

<details>
<summary>答案与说明</summary>

区分实例的汇总带宽与每个接口的带宽；不要将已汇总的数值再次相乘。验证同一可用区内的放置、接口、驱动程序/libfabric/NCCL、安全组和 Pod 资源。RAID0 不会启用 EFA。
</details>

## 10. 应如何理解 GPU 显存和 XID 指标？

<details>
<summary>答案与说明</summary>

FB_USED/FREE 是以 MiB 为单位的 Gauge 指标；较高比例不一定表示 OOM。XID_ERRORS 是记录最后一个错误码的 Gauge 指标，而不是可用于 increase() 的 Counter。应调查实际错误、缓存、分配失败以及具体设备的限制。
</details>

## 11. Karpenter 节点整合会直接使用 GPU 利用率指标吗？

<details>
<summary>答案与说明</summary>

它依据工作负载资源请求、调度可行性、价格和中断约束，而不是 DCGM 20% 阈值。资源限制/预算并非绝对的成本或故障保障；应验证终止和恢复。
</details>

## 12. 谁发布 ResourceSlice，它们表示什么？

<details>
<summary>答案与说明</summary>

驱动程序发布真实的设备清单，其中包含有类型的属性/容量。任意创建一个 ResourceSlice 并不会创建 GPU。CEL 和 matchAttribute 必须遵循实际发布的数据模式。
</details>

## 13. 为 Milvus 请求 GPU 就能完成 RAG 吗？

<details>
<summary>答案与说明</summary>

不能。匹配受支持的镜像/索引、嵌入维度/修订版本、度量/参数、租户筛选以及更新/删除生命周期。验证结果访问授权，并处理缺少证据的情况。
</details>

## 14. 应如何调查待处理的 GPU Pod 和节点故障？

<details>
<summary>答案与说明</summary>

仅统计处于 Pending 状态且请求 GPU 的 Pod 无法诊断原因。检查事件、PVC、亲和性、污点、配额、资源申领和镜像，并测试检查点/恢复。即使一个 Pod 内有多个请求 GPU 的容器，该 Pod 也只计数一次。
</details>

## 15. MCP 是否提供标准的 Kubernetes 自动发现网关？

<details>
<summary>答案与说明</summary>

不是。它定义了工具列举/调用等操作。应选择实际的服务器/网关版本、传输方式和授权设计。虚构的镜像/标签/配置或 URL 环境变量并不能实现发现/执行功能。
</details>

[返回指南](../../ai-ml/06-ai-infrastructure.md)
