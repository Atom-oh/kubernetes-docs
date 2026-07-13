# EKS Auto Mode 工作负载优化测验

> **相关文档**: [工作负载优化](../../eks-auto-mode/08-workload-optimization.md)

## 选择题

### 1. 对于大型电子商务平台上的前端工作负载，推荐的 NodePool 设置是什么？

- A) 仅 Spot，激进的 Consolidation
- B) On-Demand 优先，以可用性为重点的 Disruption Budget
- C) GPU 实例，高性能设置
- D) 仅内存优化型实例

<details>
<summary>显示答案</summary>

**答案：B) On-Demand 优先，以可用性为重点的 Disruption Budget**

**解释：**
前端工作负载面向用户，因此可用性是最高优先级。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: frontend-tier
spec:
  template:
    metadata:
      labels:
        tier: frontend
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]  # Availability first
      taints:
        - key: tier
          value: frontend
          effect: NoSchedule
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
    budgets:
      - nodes: "10%"
      - nodes: "1"
        schedule: "0 9-23 * * *"  # Peak hours
        duration: 14h
```

</details>

### 2. 对于批处理工作负载，最合适的 NodePool 设置是什么？

- A) 仅 On-Demand，保守的 Consolidation
- B) 仅 Spot，多样化的实例系列，快速清理
- C) 仅使用 GPU 实例
- D) 放置在系统 NodePool 中

<details>
<summary>显示答案</summary>

**答案：B) 仅 Spot，多样化的实例系列，快速清理**

**解释：**
批处理作业可容忍中断，因此适合使用 Spot 实例。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch-tier
spec:
  template:
    metadata:
      labels:
        tier: batch
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c", "m", "r", "i", "d"]  # Diverse families
        - key: karpenter.k8s.aws/instance-generation
          operator: In
          values: ["5", "6", "7"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]  # Spot only
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
      taints:
        - key: tier
          value: batch
          effect: NoSchedule
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s  # Quick cleanup
```

</details>

### 3. 对于 GPU ML 推理工作负载，推荐的 Consolidation 设置是什么？

- A) `consolidateAfter: 0s`
- B) `consolidateAfter: 15m`（考虑 GPU 启动时间）
- C) `consolidationPolicy: WhenEmptyOrUnderutilized`
- D) 禁用 Consolidation

<details>
<summary>显示答案</summary>

**答案：B) `consolidateAfter: 15m`（考虑 GPU 启动时间）**

**解释：**
GPU 实例启动需要更长时间，因此需要足够的 consolidateAfter。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ml-inference
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["g"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["g5.xlarge", "g5.2xlarge", "g5.4xlarge"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      taints:
        - key: nvidia.com/gpu
          value: "true"
          effect: NoSchedule
  limits:
    nvidia.com/gpu: 20
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 15m  # Consider GPU startup time
```

</details>

### 4. 哪种策略可以在 API server 工作负载的稳定性和成本之间取得平衡？

- A) 仅 On-Demand
- B) 仅 Spot
- C) Spot/On-Demand 混合 + 包含 Graviton
- D) 仅 Fargate

<details>
<summary>显示答案</summary>

**答案：C) Spot/On-Demand 混合 + 包含 Graviton**

**解释：**
API server 需要适当的可用性，同时实现成本优化。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: api-tier
spec:
  template:
    metadata:
      labels:
        tier: api
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]  # Mixed
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]  # Include Graviton
      taints:
        - key: tier
          value: api
          effect: NoSchedule
  weight: 10
```

**预期成本节省：** ~40%

</details>

### 5. 对于多架构（amd64/arm64）支持，应用程序中应该验证什么？

- A) 不需要特殊验证
- B) 验证容器镜像是否支持多架构
- C) 仅检查 Kubernetes 版本
- D) 仅检查 AWS 区域

<details>
<summary>显示答案</summary>

**答案：B) 验证容器镜像是否支持多架构**

**解释：**
要使用 Graviton（arm64）实例，容器镜像必须支持该架构。

```bash
# Check image supported architectures
docker manifest inspect nginx:latest | grep architecture

# Multi-arch image build example
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t myapp:latest \
    --push .
```

**检查清单：**
- 验证基础镜像的多架构支持
- 为两种架构构建原生二进制文件
- 在 CI/CD pipeline 中配置多架构构建

</details>

### 6. 按工作负载分离 NodePool 时，确保 Pods 调度到正确 NodePool 的方法是什么？

- A) 按 Pod 名称自动匹配
- B) 使用 Taint/Toleration 和 NodeSelector 或 Affinity
- C) 按 namespace 自动分离
- D) 仅按 AWS 标签分离

<details>
<summary>显示答案</summary>

**答案：B) 使用 Taint/Toleration 和 NodeSelector 或 Affinity**

**解释：**
在 NodePool 上设置 taints，并向 Pods 添加 tolerations 和 affinity。

```yaml
# Set taint on NodePool
spec:
  template:
    spec:
      taints:
        - key: tier
          value: batch
          effect: NoSchedule

---
# Set toleration and affinity on Pod
apiVersion: apps/v1
kind: Deployment
metadata:
  name: batch-job
spec:
  template:
    spec:
      tolerations:
        - key: tier
          value: batch
          effect: NoSchedule
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: tier
                    operator: In
                    values: ["batch"]
```

</details>
