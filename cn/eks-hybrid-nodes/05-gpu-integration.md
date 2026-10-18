# GPU 服务器集成

< [上一节：节点引导](./04-node-bootstrap.md) | [目录](./README.md) | [下一节：工作负载放置](./06-workload-placement.md) >

> **支持的版本**：DRA GPU 示例要求在受支持的 EKS 版本上运行 Kubernetes 1.34.2+。已审查的接口：GPU Operator 26.7.0、DRA driver 0.5.0、device plugin 0.20.0。
> **最后更新**：October 12, 2026

本章将准备就绪的 NVIDIA GPU 主机集成到 EKS Hybrid Nodes。内容涵盖分配、GPU Operator 所有权、MIG 和时间切片。**本次审计未执行 GPU、驱动程序安装、模型下载或推理基准测试**。这些示例要求使用已获批准的 OS/kernel/driver/toolkit/runtime/image 组合，并在实际硬件上进行测试。

## 为每个 GPU 选择一个分配所有者

| 路径 | 前提条件和分配 |
|---|---|
| 独立 NVIDIA device plugin | 已准备好的主机 driver、NVIDIA Container Toolkit 和 runtime；发布如 `nvidia.com/gpu` 等扩展资源 |
| 独立 DRA driver | 已准备好的 driver 和 CDI runtime；发布 ResourceSlices 并通过 DeviceClass/ResourceClaim 进行分配 |
| 使用 `ClusterPolicy` 的 GPU Operator | Operator 管理的 device-plugin 工作流；driver/toolkit/MIG 组件的所有权必须与已安装的组件一致 |
| 使用 `GPUCluster` 的 GPU Operator 26.7 | 面向新安装的 Operator 管理 DRA 工作流；在集群中与 `ClusterPolicy` 互斥 |

AWS 建议在使用受支持静态容量预置的新 EKS 1.34+ 部署中采用 DRA。**NVIDIA DRA driver 不支持 EKS Auto Mode**，后者已管理自己的 GPU device plugin；AWS 指导 Auto Mode 和 Karpenter 动态容量使用 NVIDIA device plugin（[EKS 标准支持发行说明](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions-standard.html)的 Kubernetes 1.37 部分，检查日期为 October 12, 2026）。以下独立示例仅面向标识出的 Hybrid GPU 节点；请勿在 Auto Mode 或其他 GPU 节点上安装重复的分配管理器。

使用不重叠的、由所有者管理的标签，例如 `workload.example.com/gpu-allocation=device-plugin` 或 `dra`。这些标签是调度输入，而非安全边界或 GPU 硬件健康的证明。在启用任一路径之前，确认没有其他 plugin/Operator 正在发布同一物理设备。

## 准备并验证主机群组

- 完成[节点引导](./04-node-bootstrap.md)，包括 Hybrid 身份、CNI 和时间同步。
- 根据 NVIDIA 的矩阵和 AWS Hybrid OS 支持，检查 GPU 型号/形态、固件、driver 分支、OS/kernel 和 runtime。较新的 NVIDIA 矩阵并不意味着 EKS 提供其中列出的每个 Kubernetes 版本。
- 验证实际已安装 NVIDIA driver 和 toolkit。位于本地并不意味着 driver 一定存在。
- 对于旧版示例，准备一个名为 `nvidia` 的现有 `RuntimeClass`，其由已配置的 containerd NVIDIA runtime handler 支持。仅有类名不会配置该 handler。
- 对于 DRA 0.5.0 GPU 分配，发布的前提指南要求 Kubernetes **1.34.2+**、独立 driver **565+**、Toolkit **1.18+** 和启用 CDI 的 runtime。GPU Operator DRA 工作流要求 driver **580+**。这些是兼容性下限，而不是当前补丁/分支建议。
- 通过已获批准的 NFD/GFD 安装或主机清单流程准备发现标签。不要仅因示例启用了某个发现控制器就部署第二个。

以下由 operator 运行的检查会读取主机 GPU 元数据；它不是 CUDA 或 LLM 基准测试：

```bash
nvidia-smi --query-gpu=name,driver_version,uuid,memory.total --format=csv,noheader
```

早期示例中显示 `cpu: 128`、`memory: 1024Gi`、`nvidia.com/gpu: 8` 的输出是**未经验证的示意**，并非本次审计的测量结果。Kubernetes GPU 容量可能表示物理 GPU、MIG 实例或时间切片副本，具体取决于配置。

## 在选定的 Hybrid 节点上使用独立 device plugin

以下值要求预安装的 driver/runtime 和现有的兼容发现设置。两个 node-selector 标签会与 chart 的 GPU-discovery affinity 组合。如果没有节点匹配，请修正清单/标签；不要仅为让 Pods 运行而移除 affinity。

```yaml
nodeSelector:
  eks.amazonaws.com/compute-type: hybrid
  workload.example.com/gpu-allocation: device-plugin
runtimeClassName: nvidia
migStrategy: none
failOnInitError: true
deviceListStrategy: envvar
gfd:
  enabled: false
nfd:
  enabled: false
resources:
  requests:
    cpu: 50m
    memory: 64Mi
  limits:
    cpu: 500m
    memory: 256Mi
```

保存为 `device-plugin-values.yaml`。已审查的 chart 是 **0.20.0**；部署前请验证所需的升级路径和 image 兼容性：

```bash
# Cluster write; installs a privileged infrastructure component.
set -euo pipefail
umask 077
: "${KUBECONFIG:?}" "${CONTEXT:?}"
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" get nodes \
  -l 'eks.amazonaws.com/compute-type=hybrid,workload.example.com/gpu-allocation=device-plugin' \
  -o json > plugin-nodes.json
jq -e '.items | length > 0 and
  all(.[]; .metadata.labels["nvidia.com/mps.capable"] != "true")' plugin-nodes.json
helm repo add nvdp https://nvidia.github.io/k8s-device-plugin
helm repo update nvdp
helm install hybrid-gpu-plugin nvdp/nvidia-device-plugin \
  --version 0.20.0 --namespace gpu-system --create-namespace \
  --kubeconfig "$KUBECONFIG" --kube-context "$CONTEXT" \
  --values device-plugin-values.yaml --wait --timeout 10m
```

使用由 GPU 基础设施 operator 所有的 namespace 和 release。审查渲染出的 RBAC、主机路径、特权、registry 访问和 tolerations。Helm `--wait` 成功并不证明 CUDA 兼容性或工作负载性能。

发布的 0.20.0 chart 还会渲染一个 MPS control DaemonSet，并通过 `nvidia.com/mps.capable=true` 加上所选 Hybrid 群组进行限制。此独占 GPU 示例会在该标签已设置时停止。请调查现有 MPS 所有权，而不是盲目清除标签；不要假定 chart 只包含一个 DaemonSet。

## 在单独的 Hybrid GPU 群组上使用独立 DRA

当前 driver 项目是 **`kubernetes-sigs/dra-driver-nvidia-gpu`**。DRA API 稳定性、EKS 支持和各个供应商功能成熟度是彼此独立的检查项。当前 NVIDIA 26.7 文档指出，完整 GPU 和现有 MIG 分配已达到 GA；动态 MIG、MPS、部分共享和 NVML 分配健康功能具有单独的 Alpha gate。不要为了让演示启动而启用所有 feature gate。

带标签的 repository README 中较早的文字将 GPU 分配描述为不受支持。发布的前提/安装文档和当前 NVIDIA 功能表提供了更新的、特定功能的指导。为生产部署记录确切版本和支持契约。

该示例禁用 ComputeDomains，因为普通 H100/H200 分配不需要 Multi-Node NVLink 编排。ComputeDomains 具有额外的 Grace Blackwell/MNNVL、IMEX 和发现要求。

```yaml
gpuResourcesEnabledOverride: true
nvidiaDriverRoot: /
resources:
  gpus:
    enabled: true
  computeDomains:
    enabled: false
featureGates: {}
kubeletPlugin:
  nodeSelector:
    eks.amazonaws.com/compute-type: hybrid
    workload.example.com/gpu-allocation: dra
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
  containers:
    gpus:
      resources:
        requests:
          cpu: 50m
          memory: 128Mi
        limits:
          cpu: "1"
          memory: 512Mi
webhook:
  enabled: false
```

保存为 `dra-values.yaml`。此路径假定主机 driver root 为 `/` 且已配置 CDI。由 Operator 安装的 driver 通常使用不同的 root；不要将此值复制到该部署中。

```bash
# Alternative cluster write, only for the separately selected DRA cohort.
set -euo pipefail
: "${KUBECONFIG:?}" "${CONTEXT:?}"
helm install hybrid-gpu-dra \
  oci://registry.k8s.io/dra-driver-nvidia/charts/dra-driver-nvidia-gpu \
  --version 0.5.0 --namespace gpu-dra-system --create-namespace \
  --kubeconfig "$KUBECONFIG" --kube-context "$CONTEXT" \
  --values dra-values.yaml --wait --timeout 10m
```

此 chart 仍要求使用 `gpuResourcesEnabledOverride=true` 来启用 GPU 资源。它的存在并不表示每项 GPU 功能都是 Alpha。此最小示例禁用了可选 admission webhook；启用它需要可访问的 webhook endpoint 和已验证的 TLS/cert-manager 或 existing-secret 配置。

### GPU Operator 替代方案和所有权

当 Operator 管理的组件生命周期与预期安装一致时，请使用 Operator。`driver.enabled=false` **仅在主机 driver 已验证时**才适用。同样，仅在准备好所需 runtime 配置后才禁用 toolkit 管理。Operator 升级可能更改 driver、validator、资源发布和节点可用性。

对于**新的 Operator 管理 DRA**，文档化的值包括：

```yaml
clusterPolicy:
  deployCR: false
gpuCluster:
  deployCR: true
driver:
  enabled: false
nfd:
  enabled: false
draDriver:
  computeDomains:
    enabled: false
```

此片段假定已获批准的预安装 driver、CDI runtime 和发现安装。GPUCluster 不会自动提供 ClusterPolicy 的 toolkit/MIG-management 行为。审查 **26.7.0** 的完整 chart 值，然后通过集群的 GPU 所有者进行部署。

`GPUCluster` 是一个名为 `gpu-cluster` 的 cluster-scoped singleton。它不能与 `ClusterPolicy` 共存。本工作流不支持从 ClusterPolicy 或独立 DRA Helm release 原地迁移至 GPUCluster；请使用文档化的新安装路径。不要为 Operator 管理的部署安装额外的独立 DRA release。

Operator controller 的 `nodeSelector` **不会**限制每个 operand。Operand 放置使用 GPU 发现和 `nvidia.com/gpu.deploy.*` 标签；还要审查被排除的 cloud/Auto Mode GPU 以及未来节点。如果无法维持该边界，请使用隔离的集群或适当限定范围的独立路径。

GPUCluster 协调可运行 GPU validator 并分配 claim。它的就绪状态和 DCGM telemetry 不等同于 DRA 设备分配健康：`NVMLDeviceHealthCheck` 在此版本中为 Alpha，且默认禁用。

## 当前 DRA manifests

这些示例使用 **`resource.k8s.io/v1`**。Kubernetes 1.31 先前的 alpha 形式不能直接用于当前集群。DRA 需要可工作的供应商 driver、ResourceSlices、兼容的 kubelets/runtime 和启用的 API；仅有 DeviceClass 不会发现 GPU。

```yaml
apiVersion: resource.k8s.io/v1
kind: DeviceClass
metadata:
  name: hybrid-full-gpu
spec:
  selectors:
    - cel:
        expression: >-
          device.driver == "gpu.nvidia.com" &&
          device.attributes["gpu.nvidia.com"].type == "gpu"
---
apiVersion: resource.k8s.io/v1
kind: DeviceClass
metadata:
  name: hybrid-large-gpu
spec:
  selectors:
    - cel:
        expression: >-
          device.driver == "gpu.nvidia.com" &&
          device.attributes["gpu.nvidia.com"].type == "gpu" &&
          device.capacity["gpu.nvidia.com"].memory.isGreaterThan(quantity("40Gi"))
---
apiVersion: resource.k8s.io/v1
kind: ResourceClaimTemplate
metadata:
  name: single-large-gpu
  namespace: ai-workloads
spec:
  spec:
    devices:
      requests:
        - name: gpu
          exactly:
            deviceClassName: hybrid-large-gpu
            allocationMode: ExactCount
            count: 1
```

`type == "gpu"` selector 排除了在同一 `gpu.nvidia.com` driver 下发布的 MIG 和 VFIO 设备。第二个 class 选择发布内存**大于 40 GiB**的设备；它不是仅适用于 H100/H200 的 selector。检查实际容量和 NVML `productName` 的 ResourceSlice。诸如 `NVIDIA-H200` 的 GFD 节点标签不必等于 DRA product-name attribute。

在此 API 中，DeviceClass 没有 `suitableNodes` 字段。使用工作负载的 node selector/affinity 约束工作负载，并让 DRA 匹配设备和节点可用性。请求使用 `requests[].exactly`；Pod claim 直接引用 `resourceClaimTemplateName`，不使用旧的 `source` wrapper。

## 有界 GPU smoke Jobs

使用已获批准的 namespace（例如 `ai-workloads`）和经过测试、**按 digest 固定**的 image，该 image 应可与选定的 driver/runtime、非 root UID 和只读 root filesystem 一同工作。下方占位 image 故意不可用。两个 Job 均**默认暂停**，因此应用它们不会启动 GPU 工作。

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: hybrid-gpu-plugin-smoke
  namespace: ai-workloads
spec:
  suspend: true
  completions: 1
  parallelism: 1
  backoffLimit: 0
  activeDeadlineSeconds: 120
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      runtimeClassName: nvidia
      nodeSelector:
        eks.amazonaws.com/compute-type: hybrid
        workload.example.com/gpu-allocation: device-plugin
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: gpu-check
          image: registry.example.invalid/approved/gpu-smoke:replace-with-approved-digest
          command: ["nvidia-smi", "-L"]
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
              nvidia.com/gpu: 1
            limits:
              cpu: 500m
              memory: 256Mi
              nvidia.com/gpu: 1
---
apiVersion: batch/v1
kind: Job
metadata:
  name: hybrid-gpu-dra-smoke
  namespace: ai-workloads
spec:
  suspend: true
  completions: 1
  parallelism: 1
  backoffLimit: 0
  activeDeadlineSeconds: 120
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      nodeSelector:
        eks.amazonaws.com/compute-type: hybrid
        workload.example.com/gpu-allocation: dra
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: gpu-check
          image: registry.example.invalid/approved/gpu-smoke:replace-with-approved-digest
          command: ["nvidia-smi", "-L"]
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
            claims:
              - name: gpu-resource
      resourceClaims:
        - name: gpu-resource
          resourceClaimTemplateName: single-large-gpu
```

第一个 Job 用于独占的旧版 device-plugin 示例；第二个用于单独的 DRA 群组。不要通过两种机制请求同一个 GPU。即使多个 container 引用它，单个 DRA claim 也是一次分配。

在所有者替换 image、验证放置/runtime/security 并批准 GPU 测试后，仅通过正常部署流程恢复预期 Job。请在 TTL 清理前捕获其结果。120 秒截止时间限制的是 Job 启动后的时长，而不是 image 准备或外部维护操作的时长。

不要为单设备 claim 设置 `CUDA_VISIBLE_DEVICES=0,1,2,3`。device manager/runtime 会提供已分配的设备；CUDA 的进程可见索引可能不同于物理 GPU 索引。手动覆盖可能隐藏或错误识别该分配，且不会授予额外 GPU。

`nvidia-smi -L` 仅确认设备可见性。请在获批准的硬件上分别验证有界 CUDA 操作和实际应用；本文不声称已执行此类操作或获得性能结果。

## MIG 和时间切片

MIG 将受支持的 GPU 划分为具有硬件支持的计算/内存实例。它提供比时间切片更强的资源和内存/故障隔离，但不会将共享主机/driver 变成完整的安全边界，也不保证应用的延迟 SLO。受支持的 profile 和实例限制取决于 GPU SKU 和 driver。

常见的 **A100 40 GB** profile 包括：

| Profile | 标称 profile 内存 | 该 profile 的最大实例数 |
|---|---|---|
| `1g.5gb` | 5 GB | 7 |
| `2g.10gb` | 10 GB | 3 |
| `3g.20gb` | 20 GB | 2 |
| `4g.20gb` | 20 GB | 1 |
| `7g.40gb` | 40 GB | 1 |

`4g.40gb` 属于 **A100 80 GB** profile 集；旧测验混合了这些 SKU 表。`1g` 指的是 profile 的 GPU 计算切片数量，而不是物理 GPU 数量。标称内存标签并不保证精确的可用内存。混合 profile 放置还有额外的几何约束。

启用/重新配置 MIG 是由所有者控制的维护操作，可能中断 GPU 工作负载。上面的基线独立 plugin 值使用 `migStrategy: none`；将 Pod 请求更改为 `nvidia.com/mig-1g.5gb` 不会创建 MIG 实例。请先准备实际 MIG 几何和 plugin 的适当策略。

时间切片发布多个**逻辑访问槽位**，而不是物理隔离的 GPU 或内存分区。例如，经过单独审查的 device-plugin 配置可以使用：

```yaml
# Fragment of device-plugin configuration, not a Kubernetes resource.
version: v1
sharing:
  timeSlicing:
    renameByDefault: true
    failRequestsGreaterThanOne: true
    resources:
      - name: nvidia.com/gpu
        replicas: 4
```

通过其命名 ConfigMap/config 选择和预期节点将此配置连接到 plugin；未附加的 ConfigMap 不会产生任何变化。使用 `renameByDefault: true` 时，发布的资源为 `nvidia.com/gpu.shared`。不要针对该共享资源原样使用独占 GPU smoke 请求。

四个副本不会预留四个独立的内存区域，且请求更多票证不保证成比例的计算能力。争用、上下文切换和工作负载行为可能影响延迟/吞吐量；应测量而非假定固定原因。时间切片在副本之间没有内存/故障隔离。推理并非自动适合超额订阅，训练也并非在所有情况下都与共享不兼容。

## H100/H200 规格背景

| NVIDIA 规格 | H100 **SXM** | H200 **SXM** |
|---|---|---|
| GPU 内存 | 80 GB HBM3 | 141 GB HBM3e |
| 发布的内存带宽 | 3.35 TB/s | 4.8 TB/s |
| MIG | 最多 7 个，具体 profile 因型号而异 | 最多 7 个，具体 profile 因型号而异 |

这些是供应商硬件规格，并非此 Kubernetes 环境的测量值。H100 NVL/PCIe 变体具有不同的容量/带宽；不要将 SXM 行泛化到每个 H100。更大的内存可能有助于工作负载适配，但实际推理/训练性能还取决于模型、精度、批处理、软件、互连和争用。

## 检查分配并安全清理

使用显式管理员 kubeconfig/context，并确保硬件/Pod 诊断信息保持私密：

```bash
set -euo pipefail
umask 077
: "${KUBECONFIG:?}" "${CONTEXT:?}"
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  get resourceslices -o json > gpu-slices.json
jq '[.items[] | select(.spec.driver == "gpu.nvidia.com") |
  {name: .metadata.name, node: .spec.nodeName,
   devices: [.spec.devices[] | {name, attributes, capacity}]}]' gpu-slices.json
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  get resourceclaims -n ai-workloads -o json > gpu-claims.json
jq '[.items[] | {name: .metadata.name,
  allocation: .status.allocation.devices.results,
  reservedFor: .status.reservedFor}]' gpu-claims.json
```

当前 ResourceClaims 没有通用的持久化 `Pending → Allocated → Bound` phase enum。请检查分配结果、预留、Pod 调度/events 和 driver 准备状态。预留并不证明 container 已成功使用 GPU。旧的 `resourceHandles` 示例不是当前的结构化分配形式。

检查日志时，请使用所选 driver release 实际渲染的工作负载名称/标签。Operator 管理的 DRA 和独立 DRA release 不一定共享旧的 `app=nvidia-dra-driver` selector。

捕获结果后，仅删除所拥有的测试 Jobs/Pods；确认生成的 claims 已释放且设备已取消准备。保留的 claims 或 finalizers 可能在 container 停止后仍然存在。当工作负载仍需要 DRA kubelet plugin 来取消准备 claims 时，不要移除它。

对于 Operator 管理的 DRA，请遵循其有序的 Helm hook/finalizer 拆除流程。不要使用 `helm uninstall --no-hooks`，也不要盲目移除 finalizers/强制删除共享 claims。在复用硬件之前，请与资源所有者协调处理失败的清理。

## 主要参考资料

- [AWS NVIDIA 设备管理](https://docs.aws.amazon.com/eks/latest/userguide/device-management-nvidia.html)
- [AWS Hybrid 推理：限定范围的 device plugin](https://aws.amazon.com/blogs/containers/run-genai-inference-across-environments-with-amazon-eks-hybrid-nodes/)
- [GPU Operator 平台/组件矩阵](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/platform-support.html)
- [GPU Operator DRA/GPUCluster 工作流](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/dra-intro-install.html)
- [DRA driver 0.5.0 前提条件](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/blob/v0.5.0/site/content/docs/prerequisites.md)
- [DRA ResourceSlice 属性](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/blob/v0.5.0/site/content/docs/reference/resourceslice-attributes.md)
- [Kubernetes DRA](https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/)
- [NVIDIA device plugin 0.20.0](https://github.com/NVIDIA/k8s-device-plugin/tree/v0.20.0)
- [MIG profile](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/supported-mig-profiles.html)和[时间切片](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-sharing.html)
- [H100 规格](https://www.nvidia.com/en-us/data-center/h100/)和[H200 规格](https://www.nvidia.com/en-us/data-center/h200/)

< [上一节：节点引导](./04-node-bootstrap.md) | [目录](./README.md) | [下一节：工作负载放置](./06-workload-placement.md) >
