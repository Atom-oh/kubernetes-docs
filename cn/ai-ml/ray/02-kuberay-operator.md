# 第 2 部分：KubeRay Operator

> **审查基线**：KubeRay 1.7.0 · Ray 2.58.0 · 2026-09-12

## 实验环境设置

准备受支持的 Kubernetes、兼容的 kubectl 和 Helm 3。审查 CPU 配置并不以 GPU 硬件和 Karpenter 为前提。实际 EKS 容量可以来自现有的托管节点组、Karpenter、Cluster Autoscaler，或集群选用的供应配置。

此处的验证涵盖官方 chart 下载和原生 Helm 渲染、CRD schema 检查，以及 Ray 2.58.0 的 autoscaler 配置生成器。**它并不验证 API-server admission/CEL、controller reconciliation、实时 autoscaling 或 GPU 执行。**

## KubeRay 的作用

KubeRay 会将 Ray CR 调谐为 Pods、Services 和相关资源。不要假设普通 RayCluster worker group 必然是 Deployment 或 StatefulSet。一个 Ray 节点通常对应一个 Ray Pod，与承载该 Pod 的 Kubernetes/EC2 节点不同。

安装 operator 不会启动 Ray 工作负载。请分别创建 RayCluster、RayJob 或 RayService 等资源。也不是每项 spec 变更都会自动原地应用到已有 Pod；请检查更新路径。

## CRD 和 Feature Gates

1.7.0 chart 包含 **RayCluster、RayJob、RayService 和 RayCronJob** CRD。全部提供 `ray.io/v1`。前三者还保留已弃用的 `v1alpha1`；新示例使用 `v1`。

| 资源 | 角色和边界 |
|---|---|
| RayCluster | 管理一个 head Pod 和 worker groups；也可以使用仅 head 的配置 |
| RayJob | 批量提交和可选的 RayCluster 生命周期；区分现有集群和清理策略 |
| RayService | 管理 RayCluster 和 Serve 应用程序；检查升级和流量切换条件 |
| RayCronJob | 按计划创建 RayJobs；尽管安装了 CRD，其 controller feature gate 默认仍被禁用 |

Chart 默认启用 beta `RayServiceIncrementalUpgrade` gate。mTLS、RayCluster NetworkPolicy 和自动注入 History collector 的 alpha gates 均被禁用。History Server 的 beta 状态不同于 alpha 自动 collector 注入。可用的 feature gate 不代表资源已配置该功能。

### RayJob 清理

`shutdownAfterJobFinishes` 默认值为 false。默认的 `ttlSecondsAfterFinished: 0` 不会启用它。请显式配置清理、重试以及 pre-running/execution deadlines。1.7 版本还提供 `deletionStrategy`，并带有诸如不能混用旧版 onSuccess/onFailure policies 和 deletionRules 的约束。

区分共享集群选择与 controller 创建的集群的清理，并首先保留结果、checkpoints 和日志。删除 RayCluster 不会自动清理外部 artifacts/PVCs，也不会清理所有 EC2 费用。

### RayService 升级

`NewCluster` 和 `NewClusterWithIncrementalUpgrade` 会创建一个新集群。后者使用 Kubernetes Gateway API 和适合的 GatewayClass 实现逐步切换流量。这不同于仅原地滚动几个 Pods。

尽管 incremental gate 在 1.7 中默认启用，策略、Gateway 配置、空闲容量、就绪状态和 draining 要求仍然很重要。零停机是目标，而非对每个应用程序的保证。[第 4 部分](04-ray-serve.md)会更详细地介绍 Serve 行为。

## Autoscaling 层

使用 `enableInTreeAutoscaling: true` 启用 Ray autoscaling。KubeRay 会配置 head-Pod autoscaler sidecar 和所需权限。该示例显式设置 `autoscalerOptions.version: v2`，而不依赖对版本敏感的默认值。

Ray autoscaler 会检查 tasks、actors、placement/resource requests 和所需的 worker-group 大小；KubeRay 则调整 Pods。使用 `numOfHosts` 时，一个 group replica 可对应多个 Ray Pods，因此 `replicas == Pod count` 并不总是成立。

Kubernetes 放置 Pods，而 Karpenter 等 provisioner 则为不可调度的要求提供 EC2 容量。因 image pulls、PVCs、权限或 quotas 而处于 Pending 状态的 Pod，未必能通过增加节点解决。Karpenter consolidation 和 drift handling 也是独立的控制行为。

Ray 2.58.0 配置生成器默认将全局 idle timeout 设为 60 秒；group-level idle timeouts 可以覆盖该行为。最小/最大 replicas、活动情况、轮询和 draining conditions 意味着这并不承诺恰好在 60 秒后删除一个 Pod。

![KubeRay 将 RayCluster 的期望状态调谐为 Pods，Ray autoscaler 根据工作负载需求请求 worker 容量，而 Kubernetes 放置和 EC2 供应则作为独立层运行。](../../.gitbook/assets/en-ai-ml-ray-02-kuberay-operator-0.png)

[交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-ray-02-kuberay-operator-0.html)

## CPU/GPU 资源声明

**Pod GPU limit 并不总是唯一的配置来源。** 已审查的代码会在结构化 group `resources`、`rayStartParams` 和第一个 Ray container 的 limits/requests 之间应用优先级。显式的 `num-gpus` 不会无条件被 container GPU limit 覆盖。

原生 Ray 2.58.0 配置检查生成的 GPU 值为：limit 1 时为 GPU 1、`rayStartParams.num-gpus=2` 时为 GPU 2、结构化 group `resources.GPU=3` 时为 GPU 3。这**不会创建更多物理 GPU**。请对齐 Kubernetes limits、device plugins、drivers、Ray logical resources 和可见硬件。

最小 replicas 和 CPU/placement requirements 也会影响 GPU-group 大小；GPU Pods 并不一定只在 GPU tasks Pending 时出现。还应区分 Ray logical CPU 设置与 container enforcement。

## 安装和升级 Operator

```bash
helm repo add kuberay https://ray-project.github.io/kuberay-helm/
helm repo update kuberay
helm pull kuberay/kuberay-operator --version 1.7.0 --untar --untardir ./vendor
helm template kuberay-operator ./vendor/kuberay-operator \
  --namespace kuberay-system --include-crds > operator.rendered.yaml
```

检查 CRDs、RBAC、namespace watch scope 和 feature gates。Chart 默认启用 leader election 并在整个集群范围内 watch。若要缩小范围，请一并审查 `singleNamespaceInstall`、`watchNamespace` 和相关 RBAC 设置。

在验证 context 和管理权限后执行实际安装：

```bash
helm upgrade --install kuberay-operator kuberay/kuberay-operator \
  --version 1.7.0 --namespace kuberay-system --create-namespace
kubectl rollout status deployment/kuberay-operator -n kuberay-system
```

Helm 的 `crds/` 机制**不会自动升级或删除已有 CRDs**。不要假设 chart 升级已更新 schema。请检查已存储的 CRs 和 API-version compatibility，然后单独执行与该 release 相应的 CRD 更新。删除 CRD 可能会删除其 custom resources。

## 最小 CPU 配置

此示例假定 `ray-demo` namespace 已存在。已验证 CRD schema；未执行 controller 执行、image 启动和 autoscaling 测试。

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

完整 schema fixture 对 head 和 workers 使用 `rayproject/ray:2.58.0-py312`，并设置 CPU 1/memory 2 GiB requests 和 limits。设置 `rayVersion` 本身不会升级 container images。也请验证 runtime、Python 和 image compatibility。

将 dashboard、Ray Client 和 job-submission entry points 限制为受信任的 actors。Token authentication 是独立配置，并非每个 application endpoint 的 TLS 或 access control。请根据组织策略检查 secret delivery，并将敏感 tokens 排除在公共 manifests 和日志之外。

## 主要来源

- [KubeRay 1.7.0 release](https://github.com/ray-project/kuberay/releases/tag/v1.7.0)
- [1.7.0 chart values](https://github.com/ray-project/kuberay/blob/v1.7.0/helm-chart/kuberay-operator/values.yaml)
- [Pod/resource construction](https://github.com/ray-project/kuberay/blob/v1.7.0/ray-operator/controllers/ray/common/pod.go)
- [Ray 2.58.0 autoscaler configuration](https://github.com/ray-project/ray/blob/ray-2.58.0/python/ray/autoscaler/_private/kuberay/autoscaling_config.py)
- [RayJob API](https://github.com/ray-project/kuberay/blob/v1.7.0/ray-operator/apis/ray/v1/rayjob_types.go)
- [RayService API](https://github.com/ray-project/kuberay/blob/v1.7.0/ray-operator/apis/ray/v1/rayservice_types.go)
- [Helm CRD lifecycle](https://helm.sh/docs/chart_best_practices/custom_resource_definitions/)

[下一步：Train/Tune](03-ray-train-tune.md) · [主页](README.md) · [测验](../../quizzes/ai-ml/ray/02-kuberay-operator-quiz.md)
