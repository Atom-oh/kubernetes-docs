# 第 6 部分：KServe — Kubernetes 上的模型服务

> **审阅基线**：KServe 0.18.0 / Models Web Application 0.18.0 / Community Distribution 26.03.1
> **最后更新**：September 12, 2026

## 实验环境设置

使用兼容的 Kubernetes、KServe controller/CRDs、ServingRuntime、存储访问以及已认证的网络路径。不需要完整的 Kubeflow；Web 应用为可选项。Knative 模式需要 Knative Serving/networking；Standard 的 KEDA 路径需要 KEDA 和指标提供程序。GPU 是否需要取决于工作负载。

## KServe 和 Kubeflow

KServe 从 KFServing 演变为独立的服务项目。本章审阅了 Community Distribution 26.03.1 中捆绑的 **KServe 和 Models Web Application 0.18.0**。所审阅的最新公开 KServe 版本是 **0.20.0（2026 年 8 月 6 日）**；它与该发行版的 0.18.0 基线并不相同。

Controller、CRDs 和 Web 应用是需要进行兼容性检查的独立产物。它们的版本号不一定始终相同，也不一定始终不同。记录实际镜像、CRD schema 和 Web 应用修订版本。

`InferenceService` 是此处涵盖的服务 API，并非完整的 KServe 架构。ServingRuntime/ClusterServingRuntime、ModelMesh 以及独立的 LLMInferenceService API 具有不同的依赖关系和运行模型。

## InferenceService：Predictor、Transformer、Explainer

InferenceService 包含必需的 predictor 和可选的 transformer/explainer。Predictor 配置模型服务器，transformer 提供前/后处理，explainer 处理解释请求。解释不会自动附加到每个预测；运行时/协议支持很重要。

匹配 modelFormat、ServingRuntime、文件布局/库版本、URI/凭证、端口/probes 和请求协议。仅有一个 URI 并不能让每个模型都可服务。自定义容器也必须满足客户端契约以及 KServe 路由/健康检查要求。

官方 runtime-config chart 默认不生成资源。使用 `kserve.servingruntime.enabled=true` 渲染会生成 12 个 ClusterServingRuntimes。目录中存在并不能证明镜像时效性、安全支持或模型兼容性。

TorchServe 的[项目公告](https://github.com/pytorch/serve)指出，不计划提供新功能、bug 修复或安全补丁。它出现在较旧的运行时目录中，并不意味着它是新生产用途的受维护默认选项。请根据模型格式和 GPU 要求验证受维护的运行时。

## 部署模式：Knative 和 Standard

0.18.0 中的名称是 **Knative** 和 **Standard**。Serverless 和 RawDeployment annotation 值是已弃用的别名，会被规范化为这些名称。检查 serving.kserve.io/deploymentMode 和已安装的 inferenceservice-config。代码回退值为 Standard，而下载的 OCI resource chart 默认值为 Knative。不要仅从术语推断安装默认值。

| 项目 | Knative | Standard |
| --- | --- | --- |
| 工作负载资源 | Knative Service/Revision 路径 | Deployment/Service 和选定的 autoscaler |
| 缩容 | 在支持 KPA/策略且 minReplicas=0 时，可以缩容至零 | 默认 HPA 路径至少保留一个；KEDA 可通过合适的外部激活信号支持缩容至零 |
| 默认 minReplicas | KServe 默认值为一；仅选择 Knative 不会启用缩容至零 | HPA 将请求的零限制为至少一 |
| 依赖项 | Knative Serving/networking 和选定的 autoscaler | 所选 ingress/gateway、HPA 指标或 KEDA 等 |
| 启动延迟 | 从零开始时的调度/镜像/模型加载 | 尽管存在热副本，重启、rollout 和扩容仍会产生启动延迟 |

两种模式都不保证可用副本或延迟 SLA。请验证模型加载、readiness、容量、超时和恢复。KEDA 从零扩容需要无需运行 Pods 即可观测的信号以及重新激活路径；仅有 CPU/内存指标并不代表请求驱动的激活。

![InferenceService 协调与对正在运行的模型服务器的请求相互独立；Knative 和 Standard 路径展示了条件式 autoscaling 行为。](../../.gitbook/assets/en-ai-ml-kubeflow-06-kserve-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-06-kserve-0.html)

## Autoscaling 和指标

Knative KPA 支持 concurrency/RPS，而 Knative 的 HPA class 是另一条路径。Standard 通过 serving.kserve.io/autoscalerClass 选择 hpa、keda 或 external/none。并非每个 Standard Deployment 都会创建 HPA。

CPU、external 或受支持的 Pod 指标需要实际的 metrics-server/adapter/provider 依赖项。GPU 请求不会自动创建 GPU 指标。响应速度取决于观测间隔、stabilization 和模型行为；concurrency 指标并非总是更快。

## 渐进式更新和 Canary 流量

此版本的 canaryTrafficPercent 已在 **Knative Revision 流量拆分路径**中验证。KServe 将先前已 rollout 的 revision 和新 revision 设置为 Knative Service 流量目标；Knative networking 分配请求。KServe controller 并不是每个推理调用的 proxy。

不要将 Standard Deployment rolling update 等同于这种按 revision 百分比进行的路由。Standard 中的加权路由需要单独设计的 services/gateway/mesh 或 rollout 工具，并明确所有权。使用 [Istio 流量管理](../../service-mesh/istio/traffic-management/04-traffic-splitting.md)或 [Argo Rollouts](../../service-mesh/istio/advanced/08-argo-rollouts.md)时，避免与 KServe 管理对象的所有权发生冲突。

仅有百分比并不能验证质量，也不能自动执行推广/回滚。检查比较指标、错误/延迟、保留的 revisions/模型产物和路由 readiness。

## EKS 上的 GPU 推理

Pod 的 nvidia.com/gpu 请求会启用调度/设备分配。实际 GPU 推理需要兼容的 CUDA/drivers、服务器镜像、模型 backend 和设备配置。审阅 Triton 模型配置或框架设备选择；GPU 请求不会自动将 CPU 模型移至 GPU。

Karpenter 为符合条件的 Pending Pods、NodePools、quotas 和可用容量进行供应。KServe/Knative/HPA/KEDA Pod 扩缩容和 EC2 供应/回收是独立的循环。即使模型 Pods 缩容至零，其他工作负载或 disruption policies 仍可能使节点和成本持续运行。

## 验证和来源

已在本地拉取并渲染官方 0.18.0 OCI CRD/resource/runtime-config charts，以检查 schema/config。已审阅模式别名、HPA 最小值、KEDA ScaledObject 和 Knative 流量代码。未执行模型下载/服务、GPU、集群 autoscaling 或实时 canary 请求。

- [0.18.0 模式名称和默认值](https://github.com/kserve/kserve/blob/v0.18.0/pkg/constants/constants.go)
- [HPA 最小副本处理](https://github.com/kserve/kserve/blob/v0.18.0/pkg/controller/v1beta1/inferenceservice/reconcilers/hpa/hpa_reconciler.go)
- [KEDA ScaledObject 处理](https://github.com/kserve/kserve/blob/v0.18.0/pkg/controller/v1beta1/inferenceservice/reconcilers/keda/keda_reconciler.go)
- [Knative 流量处理](https://github.com/kserve/kserve/blob/v0.18.0/pkg/controller/v1beta1/inferenceservice/reconcilers/knative/ksvc_reconciler.go)
- [0.20.0 发行版](https://github.com/kserve/kserve/releases/tag/v0.20.0)

## 后续步骤

将此服务路径连接到 [Kubeflow 系列](README.md)中的架构、Pipelines、Notebooks、Katib 和 Trainer 章节，同时将模型产物部署和验证视为独立步骤。

---

[返回主页](./README.md)

## 测验

要测试你在本章中学到的内容，请尝试[主题测验](../../quizzes/ai-ml/kubeflow/06-kserve-quiz.md)。
