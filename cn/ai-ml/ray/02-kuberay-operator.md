# 第 2 部分：KubeRay Operator

> **审查基线**：KubeRay 1.7.1 · Ray 2.58.0 · 2026-10-16

## 实验环境设置

准备受支持的 Kubernetes、兼容的 kubectl 和 Helm 3。审查 CPU 配置不需要 GPU 硬件和 Karpenter。实际 EKS 容量可以来自现有的托管节点组、Karpenter、Cluster Autoscaler，或集群选用的配置方式。

此处的验证涵盖官方 chart 下载和原生 Helm 渲染、CRD schema 检查，以及 Ray 2.58.0 的 autoscaler 配置生成器。**这并不代表已验证 API server 准入/CEL、控制器协调、实时自动扩缩容或 GPU 执行。**

## KubeRay 的作用

KubeRay 将 Ray CR 协调为 Pod、Service 和相关资源。不要假设普通 RayCluster worker 组一定是 Deployment 或 StatefulSet。Ray 节点通常对应一个 Ray Pod，与承载该 Pod 的 Kubernetes/EC2 节点不同。

安装 Operator 不会启动 Ray 工作负载。需要单独创建 RayCluster、RayJob 或 RayService 等资源。此外，并非每项 spec 变更都会自动就地应用到现有 Pod；请检查更新路径。

## CRD 和功能门控

1.7.1 chart 包含 **RayCluster、RayJob、RayService 和 RayCronJob** CRD。它们均提供 `ray.io/v1`。前三种还保留了已弃用的 `v1alpha1`；新示例使用 `v1`。

| 资源 | 作用和边界 |
|---|---|
| RayCluster | 管理一个 head Pod 和 worker 组；也可以仅配置 head |
| RayJob | 批处理提交和可选的 RayCluster 生命周期管理；区分现有集群与清理策略 |
| RayService | 管理 RayCluster 和 Serve 应用；检查升级和流量切换条件 |
| RayCronJob | 按计划创建 RayJob；尽管 CRD 已安装，其控制器功能门控默认处于禁用状态 |

chart 默认启用 beta 功能门控 `RayServiceIncrementalUpgrade`。mTLS、RayCluster NetworkPolicy 和自动注入 History collector 的 alpha 功能门控均处于禁用状态。History Server 的 beta 状态与自动注入 alpha collector 不同。功能门控可用，并不表示资源已配置该功能。

### RayJob 清理

`shutdownAfterJobFinishes` 默认值为 false。默认的 `ttlSecondsAfterFinished: 0` 不会启用它。请明确配置清理、重试以及运行前/执行期限。1.7 版本还提供 `deletionStrategy`，并有一些限制，例如不能同时使用旧版 onSuccess/onFailure 策略和 deletionRules。

区分共享集群的选择与清理由控制器创建的集群，并先保留结果、检查点和日志。删除 RayCluster 不会自动清理外部制品/PVC，也不会消除所有 EC2 费用。

### RayService 升级

`NewCluster` 和 `NewClusterWithIncrementalUpgrade` 都会创建新集群。后者使用 Kubernetes Gateway API 和合适的 GatewayClass 实现逐步切换流量。这不同于简单地就地滚动更新几个 Pod。

尽管 1.7 默认启用了增量升级功能门控，策略、Gateway 配置、备用容量、就绪状态和排空要求仍然很重要。零停机是目标，并非对每个应用的保证。[第 4 部分](04-ray-serve.md)将更详细地介绍 Serve 的行为。

## 自动扩缩容层

使用 `enableInTreeAutoscaling: true` 启用 Ray 自动扩缩容。KubeRay 会配置 head Pod autoscaler sidecar 及所需权限。示例明确设置 `autoscalerOptions.version: v2`，而不依赖可能随版本变化的默认值。

Ray autoscaler 会检查任务、actor、placement/资源请求和期望的 worker 组大小；KubeRay 则调整 Pod。使用 `numOfHosts` 时，一个组副本可能对应多个 Ray Pod，因此 `replicas == Pod count` 并非普遍成立。

Kubernetes 负责调度 Pod，而 Karpenter 之类的配置器会为无法调度的需求提供 EC2 容量。由镜像拉取、PVC、权限或配额导致的 Pending Pod，不一定能通过增加节点解决。Karpenter 的整合和漂移处理也属于独立的控制行为。

Ray 2.58.0 配置生成器将全局空闲超时默认设为 60 秒；组级空闲超时可以覆盖该行为。最小/最大副本数、活动状态、轮询和排空条件意味着它并不保证恰好在 60 秒后删除 Pod。

![KubeRay 将 RayCluster 的期望状态协调为 Pod；Ray autoscaler 根据工作负载需求请求 worker 容量；Kubernetes 调度和 EC2 配置则作为独立层运行。](../../.gitbook/assets/en-ai-ml-ray-02-kuberay-operator-0.png)

[交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-ray-02-kuberay-operator-0.html)

## CPU/GPU 资源声明

**Pod 的 GPU limit 并非总是唯一的配置来源。**审查的代码会按优先级处理结构化组 `resources`、`rayStartParams` 和第一个 Ray 容器的 limits/requests。显式指定的 `num-gpus` 不会无条件被容器 GPU limit 覆盖。

Ray 2.58.0 原生配置检查结果显示：limit 为 1 时得到 GPU 1；`rayStartParams.num-gpus=2` 时得到 GPU 2；结构化组 `resources.GPU=3` 时得到 GPU 3。这**不会创造更多物理 GPU**。请确保 Kubernetes limits、device plugin、驱动程序、Ray 逻辑资源和可见硬件相互匹配。

最小副本数和 CPU/placement 要求也会影响 GPU 组大小；GPU Pod 不一定只会在 GPU 任务 Pending 时出现。还要区分 Ray 逻辑 CPU 设置与容器资源约束。

## 安装和升级 Operator

```bash
helm repo add kuberay https://ray-project.github.io/kuberay-helm/
helm repo update kuberay
helm pull kuberay/kuberay-operator --version 1.7.1 --untar --untardir ./vendor
helm template kuberay-operator ./vendor/kuberay-operator \
  --namespace kuberay-system --include-crds > operator.rendered.yaml
```

检查 CRD、RBAC、namespace 监视范围和功能门控。chart 默认启用 leader election 并监视整个集群。若要缩小范围，请一并检查 `singleNamespaceInstall`、`watchNamespace` 和相关 RBAC 设置。

确认 context 和管理员权限后，再执行实际安装：

```bash
helm upgrade --install kuberay-operator kuberay/kuberay-operator \
  --version 1.7.1 --namespace kuberay-system --create-namespace
kubectl rollout status deployment/kuberay-operator -n kuberay-system
```

Helm 的 `crds/` 机制**不会自动升级或删除现有 CRD**。不要假设 chart 升级已更新 schema。请检查已存储的 CR 和 API 版本兼容性，然后根据对应版本的发布要求单独更新 CRD。删除 CRD 可能会删除其自定义资源。

## 最简 CPU 配置

此示例假设 `ray-demo` namespace 已存在。CRD schema 已通过验证；未测试控制器执行、镜像启动和自动扩缩容。

```yaml
apiVersion: ray.io/v1
kind: RayCluster
metadata:
  name: ray-cpu-demo
  namespace: ray-demo
spec:
  rayVersion: '2.58.0'
  enableInTreeAutoscaling: true
  autoscalerOptions:
    version: v2
    idleTimeoutSeconds: 60
  headGroupSpec:
    serviceType: ClusterIP
    rayStartParams:
      num-cpus: '0'
    template:
      spec:
        containers:
          - name: ray-head
            image: rayproject/ray:2.58.0-py312
            resources:
              requests:
                cpu: '1'
                memory: 2Gi
              limits:
                cpu: '1'
                memory: 2Gi
  workerGroupSpecs:
    - groupName: cpu
      replicas: 0
      minReplicas: 0
      maxReplicas: 2
      rayStartParams: {}
      template:
        spec:
          containers:
            - name: ray-worker
              image: rayproject/ray:2.58.0-py312
              resources:
                requests:
                  cpu: '1'
                  memory: 2Gi
                limits:
                  cpu: '1'
                  memory: 2Gi
```

完整的 schema fixture 为 head 和 worker 使用 `rayproject/ray:2.58.0-py312`，并将 CPU 1/内存 2 GiB 设置为 requests 和 limits。设置 `rayVersion` 本身不会升级容器镜像。还要确认运行时、Python 和镜像的兼容性。

仅允许可信参与者访问 dashboard、Ray Client 和作业提交入口。Token 身份验证需要单独配置；它不是 TLS，也不能为每个应用端点提供访问控制。请根据组织策略检查密钥交付方式，并避免在公开的 manifest 和日志中泄露敏感 token。

## 主要来源

- [KubeRay 1.7.1 发布版本](https://github.com/ray-project/kuberay/releases/tag/v1.7.1)
- [1.7.1 chart values](https://github.com/ray-project/kuberay/blob/v1.7.1/helm-chart/kuberay-operator/values.yaml)
- [Pod/资源构建](https://github.com/ray-project/kuberay/blob/v1.7.1/ray-operator/controllers/ray/common/pod.go)
- [Ray 2.58.0 autoscaler 配置](https://github.com/ray-project/ray/blob/ray-2.58.0/python/ray/autoscaler/_private/kuberay/autoscaling_config.py)
- [RayJob API](https://github.com/ray-project/kuberay/blob/v1.7.1/ray-operator/apis/ray/v1/rayjob_types.go)
- [RayService API](https://github.com/ray-project/kuberay/blob/v1.7.1/ray-operator/apis/ray/v1/rayservice_types.go)
- [Helm CRD 生命周期](https://helm.sh/docs/chart_best_practices/custom_resource_definitions/)

[下一篇：Train/Tune](03-ray-train-tune.md) · [主页](README.md) · [测验](../../quizzes/ai-ml/ray/02-kuberay-operator-quiz.md)
