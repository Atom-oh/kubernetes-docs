# EKS Hybrid Nodes GPU 集成测验

> **相关文档**: [GPU 集成](../../eks-hybrid-nodes/05-gpu-integration.md)

## 多项选择题

### 1. NVIDIA GPU Multi-Instance GPU (MIG) 技术的关键特征是什么？

A. 将多个 GPU 合并为一个
B. 将单个 GPU 拆分为多个物理隔离的实例
C. 只共享 GPU 内存
D. 软件级时间切片

<details>
<summary>显示答案</summary>

**答案：B. 将单个 GPU 拆分为多个物理隔离的实例**

**解释：**
MIG (Multi-Instance GPU) 可将 NVIDIA A100 和 H100 等 GPU 分区为最多 7 个物理隔离的实例。每个实例都有独立的内存、缓存和计算资源。

**MIG 与 Time-Slicing 对比：**

| 功能 | MIG | Time-Slicing |
|---------|-----|--------------|
| 隔离级别 | 物理（完全隔离） | 基于时间（软件） |
| 内存隔离 | 完全隔离 | 共享 |
| 支持的 GPU | A100, H100 | 所有 NVIDIA GPU |
| QoS 保证 | 是 | 否 |

```yaml
# MIG Resource Request
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  containers:
  - name: cuda-app
    image: nvidia/cuda:12.0-runtime
    resources:
      limits:
        nvidia.com/mig-1g.5gb: 1
```

</details>

### 2. NVIDIA GPU MIG 配置中的 "1g.5gb" 表示什么？

A. 1GB 内存，5 个 GPU 核心
B. 1 个 GPU Instance（1 个计算切片），5GB GPU 内存
C. 1 个 GPU，5GB 系统内存
D. 每 5GB 吞吐量 1 秒

<details>
<summary>显示答案</summary>

**答案：B. 1 个 GPU Instance（1 个计算切片），5GB GPU 内存**

**解释：**
MIG 实例名称格式：`<compute-slices>g.<memory-size>gb`

- **1g**: 1 个计算切片
- **5gb**: 5GB GPU 内存

**A100 MIG Profile 示例：**
- `1g.5gb`: 1 个计算切片，5GB 内存（最多 7 个）
- `2g.10gb`: 2 个计算切片，10GB 内存（最多 3 个）
- `3g.20gb`: 3 个计算切片，20GB 内存（最多 2 个）
- `4g.40gb`: 4 个计算切片，40GB 内存（最多 1 个）
- `7g.40gb`: 7 个计算切片，40GB 内存（完整 GPU）

```bash
# Check MIG instances
nvidia-smi mig -lgi
```

</details>

### 3. GPU Time-Slicing 中发生超额订阅时的预期行为是什么？

A. GPU 任务完全失败
B. 由于上下文切换导致性能下降
C. 自动添加 GPU
D. 自动扩展内存

<details>
<summary>显示答案</summary>

**答案：B. 由于上下文切换导致性能下降**

**解释：**
Time-Slicing 允许多个工作负载以时间分片方式共享单个 GPU。当发生超额订阅时，频繁的上下文切换会导致性能下降。

```yaml
# GPU Time-Slicing Configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: device-plugin-config
  namespace: nvidia-device-plugin
data:
  config.yaml: |
    version: v1
    sharing:
      timeSlicing:
        resources:
        - name: nvidia.com/gpu
          replicas: 4  # Split 1 GPU into 4
```

**Time-Slicing 注意事项：**
- 内存是共享的，因此可能发生 OOM
- 适用于推理工作负载
- 训练建议使用 MIG 或专用 GPU
- 正确设置 replicas 数量很重要

</details>

### 4. Dynamic Resource Allocation (DRA) 的主要优势是什么？

A. 仅支持静态资源分配
B. 无需供应商特定插件即可支持所有设备
C. 为自定义资源提供灵活的请求/分配机制
D. 仅管理 CPU 和内存

<details>
<summary>显示答案</summary>

**答案：C. 为自定义资源提供灵活的请求/分配机制**

**解释：**
DRA (Dynamic Resource Allocation) 在 Kubernetes 1.26 中引入，为 GPU、FPGA 和网络设备等自定义资源提供更灵活的请求和分配机制。

**DRA 核心组件：**
- **ResourceClass**: 定义由驱动程序提供的资源类型
- **ResourceClaim**: 资源请求
- **ResourceClaimTemplate**: 可复用的 claim 模板

```yaml
# Using DRA in Pod
apiVersion: v1
kind: Pod
metadata:
  name: gpu-workload
spec:
  containers:
  - name: cuda-app
    resources:
      claims:
      - name: gpu
  resourceClaims:
  - name: gpu
    source:
      resourceClaimTemplateName: gpu-claim-template
```

</details>

### 5. 在 DRA (Dynamic Resource Allocation) 中，ResourceClaim 状态变为 "Bound" 必须满足什么条件？

A. 仅创建 claim
B. 驱动程序分配资源且 Pod 已调度
C. Pod 终止
D. claim 被删除

<details>
<summary>显示答案</summary>

**答案：B. 驱动程序分配资源且 Pod 已调度**

**解释：**
ResourceClaim 状态流：

1. **Pending**: claim 已创建，尚未分配
2. **Allocated**: 驱动程序已完成资源分配
3. **Bound**: 已绑定到 Pod 并正在使用

```yaml
# Check ResourceClaim Status
kubectl get resourceclaim gpu-claim -o yaml

# Expected output
status:
  allocation:
    resourceHandles:
    - driverName: gpu.nvidia.com
      data: '{"gpu":"GPU-abc123"}'
  reservedFor:
  - name: gpu-workload
    uid: xxx-xxx-xxx
```

</details>

### 6. NVIDIA GPU Operator 的主要作用是什么？

A. GPU 硬件制造
B. 在 Kubernetes 中自动管理 GPU 驱动程序、运行时和插件
C. 仅进行 GPU 性能测试
D. GPU 采购和交付管理

<details>
<summary>显示答案</summary>

**答案：B. 在 Kubernetes 中自动管理 GPU 驱动程序、运行时和插件**

**解释：**
NVIDIA GPU Operator 会在 Kubernetes 中自动管理 GPU 基础设施：

- NVIDIA driver 安装/更新
- NVIDIA Container Toolkit 安装
- NVIDIA Device Plugin 部署
- GPU 监控（DCGM Exporter）
- MIG 管理

```bash
# Install GPU Operator (Helm)
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator \
  --create-namespace
```

```yaml
# GPU Operator Custom Configuration
apiVersion: nvidia.com/v1
kind: ClusterPolicy
metadata:
  name: cluster-policy
spec:
  driver:
    enabled: true
    version: "535.104.12"
  toolkit:
    enabled: true
  devicePlugin:
    enabled: true
  mig:
    strategy: mixed
```

</details>

### 7. H100 和 H200 GPU 之间的主要区别是什么？

A. H200 的内存容量比 H100 小
B. H200 提供 HBM3e 内存，带宽高于 H100
C. H200 不支持 MIG
D. H200 不用于数据中心

<details>
<summary>显示答案</summary>

**答案：B. H200 提供 HBM3e 内存，带宽高于 H100**

**解释：**
H200 是 H100 的后继产品，提供改进的内存系统：

| 功能 | H100 | H200 |
|---------|------|------|
| 内存类型 | HBM3 | HBM3e |
| 内存容量 | 80GB | 141GB |
| 内存带宽 | 3.35TB/s | 4.8TB/s |
| MIG 支持 | 是（最多 7 个） | 是（最多 7 个） |
| LLM 推理 | 出色 | 已优化 |

```yaml
# H200 Node Selection
apiVersion: v1
kind: Pod
spec:
  nodeSelector:
    nvidia.com/gpu.product: "NVIDIA-H200"
  containers:
  - name: llm
    resources:
      limits:
        nvidia.com/gpu: 1
```

H200 凭借其内存容量和带宽，尤其在大语言模型 (LLM) 推理方面表现出色。

</details>
