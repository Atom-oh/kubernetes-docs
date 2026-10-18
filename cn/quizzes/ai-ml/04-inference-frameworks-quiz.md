# 推理框架测验

关于当前 API 和执行边界的 15 道问题。

## 1. NIM 提供什么，必须验证什么？

<details>
<summary>答案和说明</summary>

面向模型/设备的容器和配置方案（profiles）。NIM 并不总是 TensorRT-LLM；请验证容器/模型修订版本、支持的设备、支持协议、身份验证、缓存和指标。
</details>

## 2. 什么是 Dynamo 解耦式服务？

<details>
<summary>答案和说明</summary>

通过兼容的 KV 传输连接起来的独立预填充（prefill）和解码（decode）工作进程。模型、KV 格式、后端、设备和网络必须一致；速度或成本改进取决于工作负载。
</details>

## 3. 如何在 AIBrix 0.7.0 中声明 LoRA 适配器？

<details>
<summary>答案和说明</summary>

使用包含 baseModel、podSelector 和 artifactURL 的 ModelAdapter。省略 replicas 表示所有匹配的 Pod；1 表示一个 Pod；不支持其他值。适配器名称不会对租户进行身份验证。
</details>

## 4. 哪些控制器和扩缩容层在 Kubernetes 上运行 Ray Serve？

<details>
<summary>答案和说明</summary>

KubeRay 协调 Ray 资源；Ray 自动扩缩容调整工作节点，Serve 自动扩缩容调整服务副本。不要将 RayCluster 视为普通 Deployment HPA 的目标。
</details>

## 5. 应如何评估 Inf2 成本和硬件？

<details>
<summary>答案和说明</summary>

测量相同的模型、SLO、成功吞吐量和标注日期的价格。每个芯片具有 2 个核心/32GiB HBM。inf2.24xlarge 有 6 个芯片/12 个核心/192GiB HBM；48xlarge 有 12/24/384GiB。主机 RAM 独立计算。
</details>

## 6. TTFT、ITL 和端到端延迟有何不同？

<details>
<summary>答案和说明</summary>

TTFT 衡量到首个 token 的时间；ITL 衡量后续 token 的间隔。均匀间隔近似值为 TTFT+(输出 token-1)×ITL，另加独立开销。请使用特定于工作负载的 SLO 和实际单位。
</details>

## 7. Dynamo 的 KV 感知路由会考虑什么？

<details>
<summary>答案和说明</summary>

缓存本地性和工作进程负载。固定的 0.7/0.3 公式或仅解码缓存的假设并不通用；请检查实际后端和路由策略。
</details>

## 8. 安装 Neuron device plugin 前应检查什么？

<details>
<summary>答案和说明</summary>

渲染固定版本的官方 chart，并检查驱动程序、RBAC/hostPaths、启用的组件和实际 DaemonSet。neuron 分配整个设备；neuroncore 分配核心。
</details>

## 9. AIBrix 自动扩缩容控制器的配置结构是什么？

<details>
<summary>答案和说明</summary>

PodAutoscaler 使用 scaleTargetRef、metricsSources 和 HPA/KPA/APA 策略。需要控制器和实际指标来源；仅有 ConfigMap 或 GPU 请求不会扩缩容工作负载。
</details>

## 10. NGC/profile 的角色和凭证边界是什么？

<details>
<summary>答案和说明</summary>

识别受支持的模型、镜像和 profile。NIM_MODEL_PROFILE 必须使用实际的 profile ID/名称。区分镜像拉取和运行时下载凭证；通过环境变量交付密钥不符合仅通过文件交付的策略。
</details>

## 11. 多后端支持是否意味着可以任意混用？

<details>
<summary>答案和说明</summary>

否。请验证所选的 vLLM/SGLang/TensorRT-LLM、设备、连接器、模型和 KV 格式。仅模型名称匹配并不能建立预填充/解码的互操作性。
</details>

## 12. 应如何选择模型缓存？

<details>
<summary>答案和说明</summary>

使用大小、修订版本、重启/下载并发性、授权和成本来比较本地存储/EBS/EFS/FSx。不要在节点之间共享一个 RWO EBS PVC；在特定约束下，将模型嵌入镜像可能是合适的。
</details>

## 13. GenAI-Perf 命令和结果中哪些方面很重要？

<details>
<summary>答案和说明</summary>

0.0.16 版本使用 profile 和 synthetic-input-tokens-mean/output-tokens-mean。analyze 可以运行额外的负载扫描。保留原始结果、失败记录、预热记录和分词器；GPU 利用率需要配置采集。
</details>

## 14. StatefulSet 本身能实现分布式 vLLM 吗？

<details>
<summary>答案和说明</summary>

否。稳定名称可能有帮助，但 rank、rendezvous、TP/PP、模型和通信需要显式配置。检查有序就绪的死锁；其他控制器也可能适用。
</details>

## 15. NEURON_RT_VISIBLE_CORES 与 Kubernetes 分配有何关系？

<details>
<summary>答案和说明</summary>

它选择运行时核心，但不会创建未分配的设备。inf2.xlarge 有一个设备，因此 neuron:2 无法调度。请区分用于 Inf2 的 SDK 2.32 NxD 与新的 Trn2/3 beta 路径。
</details>

[返回指南](../../ai-ml/04-inference-frameworks.md)
