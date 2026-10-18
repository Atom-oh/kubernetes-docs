# EKS Auto Mode 工作负载优化测验

> **相关文档**：[工作负载优化](../../eks-auto-mode/08-workload-optimization.md)
> **最后更新**：2026 年 9 月 12 日

## 单项选择题

### 1. 对于对可用性敏感的前端，哪项是合理的起点？

- A) 假定只使用 Spot 总是合适
- B) 使用 On-Demand，并配合应用可用性和中断控制措施
- C) 始终要求使用 GPU
- D) 只使用内存优化型节点

<details>
<summary>显示答案</summary>

**答案：B) 使用 On-Demand，并配合应用可用性和中断控制措施**

**解释：**
On-Demand 可以避免 Spot 回收事件，但不能保证可用性。必须测试副本数、拓扑、就绪状态、PDB 和恢复机制。下面的替代预算每天从 UTC 00:00 开始一个 14 小时窗口，即首尔时间 09:00–23:00。它没有使用旧的每小时 `9-23` 模式；那种模式会反复延长窗口。生效中的预算按最小值合并，而且无法控制所有强制中断。
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: web-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: web-tier
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: web-tier
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: 10%
    - nodes: '1'
      schedule: 0 0 * * *
      duration: 14h
  limits:
    cpu: '32'
    memory: 128Gi
```


</details>

### 2. 对于已证明能够容忍中断并可持久恢复的批处理工作负载，哪种资源池可能合适？

- A) 只能使用 On-Demand
- B) 使用兼容的多样化实例，并清理空节点的 Spot 资源池
- C) 只能使用 GPU
- D) 默认使用系统资源池

<details>
<summary>显示答案</summary>

**答案：B) 使用兼容的多样化实例，并清理空节点的 Spot 资源池**

**解释：**
并非每个批处理作业都能容忍中断。只使用 Spot 的资源池没有 On-Demand 回退。容器重启或设置 `SPOT_AWARE=true` 并不等同于检查点/恢复逻辑；应使用幂等输出并持久保存进度。`WhenEmpty` 配合 30 秒防抖等待时间，不会在 30 秒后终止正在运行的作业。相关指南提供的是有界的 Indexed 冒烟测试 Job，而不是生产数据处理器。
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - c
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '4'
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: batch-tier
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: batch-tier
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
    budgets:
    - nodes: 10%
  limits:
    cpu: '16'
    memory: 64Gi
```


</details>

### 3. 应如何理解推理资源池中 15 分钟的 `consolidateAfter`？

- A) GPU 启动时间的保证上限
- B) 用于权衡整合防抖与资源变动的示例设置
- C) 调度器放置任何 Pod 前必须等待的时间
- D) 节点永远不会过期的保证

<details>
<summary>显示答案</summary>

**答案：B) 用于权衡整合防抖与资源变动的示例设置**

**解释：**
这个设置不会让 GPU 进入 Ready 状态，也不保证有预热容量。`WhenEmpty` 会缩小整合范围；漂移、过期和中断是不同机制。应根据实测情况，平衡模型预热、期望容量和成本。指南中的推理模板在提供经过审查的镜像、运行时和探针之前，副本数保持为 0。考虑系统资源预留后，4 CPU/16Gi 的 Pod 也无法放入 g5.xlarge。
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - g
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - g5.2xlarge
        - g5.4xlarge
      - key: eks.amazonaws.com/instance-gpu-manufacturer
        operator: In
        values:
        - nvidia
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: gpu-nodeclass
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: gpu-tier
        effect: NoSchedule
      - key: nvidia.com/gpu
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: gpu-tier
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 15m
    budgets:
    - nodes: 10%
  limits:
    cpu: '64'
    memory: 256Gi
    nvidia.com/gpu: '4'
```


</details>

### 4. 对于兼容中断且可容忍中断的应用 API 后端，什么做法可能兼顾成本和可用性？

- A) On-Demand 总是错误的选择
- B) 只使用 Spot 总能保证可用性
- C) 评估混合使用 Spot/On-Demand，并测试 ARM 支持情况
- D) 假设 Auto Mode 会预置 Fargate 节点

<details>
<summary>显示答案</summary>

**答案：C) 评估混合使用 Spot/On-Demand，并测试 ARM 支持情况**

**解释：**
这里讨论的是应用的 API 后端，不是 AWS 管理的 Kubernetes API server。混合容量不代表固定比例，也不代表会立即回退；ARM 则要求镜像和依赖兼容，并且应用通过测试。`weight: 10` 是相对的预置优先级，不是百分比或支出上限。原先约 40% 的节省说法未经验证。
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: api-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
        - spot
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: api-tier
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: api-tier
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
  weight: 10
```


</details>

### 5. 在允许同时使用 amd64 和 arm64 之前，应验证什么？

- A) 无需验证
- B) 已固定版本的镜像平台、原生依赖和应用行为
- C) 只检查 Kubernetes 版本
- D) 只检查区域

<details>
<summary>显示答案</summary>

**答案：B) 已固定版本的镜像平台、原生依赖和应用行为**

**解释：**
下面的镜像索引检查可以确认 Linux 平台条目，但不能证明运行时正确。它会忽略无关的 attestation 条目，并在缺少所需平台时失败。相关指南展示的是本地 OCI 构建产物；并不要求发布一个未指定版本的 `myapp:latest` 镜像来测试架构。

```bash
: "${IMAGE_REF:?Set a reviewed image reference pinned by digest}"
if ! [[ "$IMAGE_REF" =~ @sha256:[0-9a-f]{64}$ ]]; then
  printf 'Use an immutable sha256 digest reference.\n' >&2
  exit 1
fi
docker buildx imagetools inspect --raw "$IMAGE_REF" > "$WORK_DIR/image-index.json"
jq -e '[.manifests[]?.platform |
         select(.os=="linux" and (.architecture=="amd64" or .architecture=="arm64")) |
         .architecture] | unique | sort == ["amd64","arm64"]' \
  "$WORK_DIR/image-index.json"
```


</details>

### 6. 工作负载如何在容忍放置限制的同时选择预期资源池？

- A) 按 Pod 名称匹配
- B) 匹配的 toleration，以及 nodeSelector 或必需的 node affinity
- C) 自动按命名空间匹配
- D) 只使用 AWS 标签

<details>
<summary>显示答案</summary>

**答案：B) 匹配的 toleration，以及 nodeSelector 或必需的 node affinity**

**解释：**
toleration 允许 Pod 放置到带污点的节点上，但不会要求它必须放到该节点。selector 或必需的 affinity 会缩小符合条件的节点范围。下面的片段应放在 Pod 模板的 `spec` 中；源指南包含完整 Job。标签和污点不是租户授权边界；匹配的容量不足时，Pod 仍可能处于 Pending 状态。
```yaml
nodeSelector:
  karpenter.sh/nodepool: batch-tier
tolerations:
- key: workload-lab
  operator: Equal
  value: batch-tier
  effect: NoSchedule
```


</details>

## 参考资料

- [Auto Mode 机器学习计算资源](https://docs.aws.amazon.com/eks/latest/userguide/ml-node-pools.html)
- [Karpenter 中断处理](https://karpenter.sh/v1.14/concepts/disruption/)
- [Docker 多平台构建](https://docs.docker.com/build/building/multi-platform/)
