# 第 6 部分：KServe — Kubernetes 上的模型服务

> **审查基线**：KServe 0.18.0 / Models Web Application 0.18.0 / Community Distribution 26.03.1
> **最后更新**：October 12, 2026

## 实验环境设置

使用兼容的 Kubernetes、KServe controller/CRD、ServingRuntime、存储访问以及经过身份验证的网络路径。无需完整的 Kubeflow；web app 为可选组件。Knative 模式需要 Knative Serving/networking；Standard 的 KEDA 路径需要 KEDA 和指标提供程序。GPU 取决于工作负载。

## KServe 和 Kubeflow

KServe 由 KFServing 演变而来，成为一个独立的服务项目。本章审查 **KServe 和 Models Web Application 0.18.0**，它们捆绑在 Community Distribution 26.03.1 中。

截至 2026 年 10 月 12 日，已核查的最新公开 KServe release 是 **0.21.0（September 25, 2026）**。更早的版本为 0.20.0（August 6, 2026）。这两个 release 都不是该 distribution 的 0.18.0 基线。

Controller、CRD 和 web app 是需要进行兼容性检查的独立构件。它们的版本号不一定始终相同，也不一定始终不同。记录实际的 image、CRD schema 和 web-app revision。

`InferenceService` 是此处涉及的服务 API，而非整个 KServe 架构。ServingRuntime/ClusterServingRuntime、ModelMesh 以及独立的 LLMInferenceService API 具有不同的依赖关系和运行模型。

## InferenceService：Predictor、Transformer、Explainer

InferenceService 具有必需的 predictor 和可选的 transformer/explainer。Predictor 配置模型 server，transformer 提供前/后处理，explainer 处理解释请求。解释不会自动附加到每一次 prediction；runtime/protocol 支持至关重要。

匹配 modelFormat、ServingRuntime、文件布局/library version、URI/credentials、ports/probes 和请求 protocol。仅有 URI 无法使每个模型都可被服务。自定义 container 还必须满足 client contract 以及 KServe routing/health-check 要求。

官方 runtime-config chart 默认不生成任何 resource。使用 `kserve.servingruntime.enabled=true` 渲染会生成 12 个 ClusterServingRuntime。catalog 的存在并不能证明 image 的时效性、安全支持或模型兼容性。

TorchServe 的[项目公告](https://github.com/pytorch/serve)指出，不再计划提供新功能、bug 修复或安全补丁。它出现在较旧的 runtime catalog 中，并不意味着它是新生产用途的受维护默认选项。针对模型格式和 GPU 要求，验证受维护的 runtime。

## Deployment 模式：Knative 和 Standard

0.18.0 中的名称是 **Knative** 和 **Standard**。Serverless 和 RawDeployment annotation 值是已弃用的别名，会被规范化为这些名称。检查 serving.kserve.io/deploymentMode 和已安装的 inferenceservice-config。代码回退值为 Standard，而下载的 OCI resource chart 默认值为 Knative。不要仅凭术语推断安装默认值。

| 项目 | Knative | Standard |
| --- | --- | --- |
| 工作负载资源 | Knative Service/Revision 路径 | Deployment/Service 和选定的 autoscaler |
| 缩容 | 当具备 KPA/policy 支持且 minReplicas=0 时，可以缩至零 | 默认 HPA 路径至少保留一个；KEDA 在具有合适的外部激活信号时可以支持缩至零 |
| 默认 minReplicas | KServe 默认值为一；仅选择 Knative 不会启用缩至零 | HPA 将请求的零限制为至少一 |
| 依赖项 | Knative Serving/networking 和选定的 autoscaler | 所选 ingress/gateway、HPA metrics 或 KEDA 等 |
| 启动延迟 | 从零开始时的调度/image/模型加载 | 尽管存在 warm replicas，重启、rollout 和扩容仍会产生启动延迟 |

两种模式都不保证有可用 replicas 或 latency SLA。验证模型加载、readiness、容量、timeout 和恢复。KEDA 从零扩缩需要无需运行 Pod 即可观测到的信号和重新激活路径；仅有 CPU/memory metrics 并不意味着可由请求驱动激活。

![InferenceService 调谐独立于对正在运行的模型 server 的请求；Knative 和 Standard 路径展示了条件化的 autoscaling 行为。](../../.gitbook/assets/en-ai-ml-kubeflow-06-kserve-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-06-kserve-0.html)

## Autoscaling 和 Metrics

Knative KPA 支持 concurrency/RPS，而 Knative 的 HPA class 是另一条路径。Standard 通过 serving.kserve.io/autoscalerClass 选择 hpa、keda 或 external/none。并非每个 Standard Deployment 都会创建 HPA。

CPU、external 或受支持的 Pod metrics 需要实际的 metrics-server/adapter/provider 依赖。GPU request 不会自动创建 GPU metrics。响应速度取决于观测间隔、stabilization 和模型行为；concurrency metrics 并非普遍更快。

## 渐进式更新和 Canary Traffic

已在 **Knative Revision traffic-splitting 路径**中验证此版本的 canaryTrafficPercent。KServe 将先前 rollout 的 revision 和新 revision 设置为 Knative Service traffic target；Knative networking 分发请求。KServe controller 并非每一次 inference call 的 proxy。

不要将 Standard Deployment rolling update 等同于这种按 revision 百分比分配的路由。Standard 中的 weighted routing 需要另行设计的 services/gateway/mesh 或 rollout tooling，以及明确的所有权。使用 [Istio traffic management](../../service-mesh/istio/traffic-management/04-traffic-splitting.md) 或 [Argo Rollouts](../../service-mesh/istio/advanced/08-argo-rollouts.md) 时，避免对 KServe 管理的 object 产生冲突的所有权。

仅有百分比并不能验证质量或自动执行 promotion/rollback。检查对比 metrics、errors/latency、保留的 revisions/model artifacts 和 route readiness。

## EKS 上的 GPU Inference

Pod 的 nvidia.com/gpu request 会启用调度/device allocation。实际的 GPU inference 需要兼容的 CUDA/drivers、server image、model backend 和 device configuration。审查 Triton model configuration 或 framework device selection；GPU request 不会自动将 CPU model 移至 GPU。

Karpenter 会针对符合条件的 Pending Pod、NodePool、quota 和可用 capacity 进行 provision。KServe/Knative/HPA/KEDA Pod scaling 与 EC2 provisioning/reclamation 是独立的循环。即使模型 Pod 缩至零，其他 workload 或 disruption policy 仍可能使 node 和成本持续运行。

## 验证与来源

已在本地拉取并渲染官方 0.18.0 OCI CRD/resource/runtime-config chart，以检查 schema/config。已审查 mode aliasing、HPA minimum、KEDA ScaledObject 和 Knative traffic code。未执行模型下载/服务、GPU、cluster autoscaling 或 live canary request。

- [0.18.0 mode 名称和默认值](https://github.com/kserve/kserve/blob/v0.18.0/pkg/constants/constants.go)
- [HPA 最小 replica 处理](https://github.com/kserve/kserve/blob/v0.18.0/pkg/controller/v1beta1/inferenceservice/reconcilers/hpa/hpa_reconciler.go)
- [KEDA ScaledObject 处理](https://github.com/kserve/kserve/blob/v0.18.0/pkg/controller/v1beta1/inferenceservice/reconcilers/keda/keda_reconciler.go)
- [Knative traffic 处理](https://github.com/kserve/kserve/blob/v0.18.0/pkg/controller/v1beta1/inferenceservice/reconcilers/knative/ksvc_reconciler.go)
- [0.20.0 release](https://github.com/kserve/kserve/releases/tag/v0.20.0)
- [0.21.0 release（已核查的最新版本）](https://github.com/kserve/kserve/releases/tag/v0.21.0)

## 后续步骤

将此服务路径与 [Kubeflow 系列](README.md)中的架构、Pipelines、Notebooks、Katib 和 Trainer 章节连接起来，同时将模型 artifact deployment 和 validation 视为独立步骤。

---

[返回主页](./README.md)

## 测验

要测试你在本章所学的内容，请尝试[主题测验](../../quizzes/ai-ml/kubeflow/06-kserve-quiz.md)。