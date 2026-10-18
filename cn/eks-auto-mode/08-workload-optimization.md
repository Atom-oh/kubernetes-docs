# 工作负载专属优化

> **支持的版本**：EKS Auto Mode GA；示例已针对 EKS 1.36 进行审查
> **最后更新**：September 12, 2026

根据工作负载匹配调度和恢复策略，然后验证实际容量、性能和成本。Web 和批处理示例是有界的实验室配置。GPU 示例是**未启用的配置模板**，并非经过验证的训练/推理应用：推理的副本数为零，旧版训练任务已暂停。未执行 GPU/模型运行、实际集群部署或基准测试。

使用 [运维](./05-operations.md) 中的账户/上下文保护措施。所有池都是动态的；它们不会预留物理容量。只选择所需的示例，检查 `default`/自定义 NodeClass 身份和子网访问，并将持续产生的节点/存储成本纳入考虑。Taint 和选择器用于控制调度位置，不构成租户安全边界。

## Web 服务：可用性与恢复

On-Demand 可避免 Spot 回收事件，但不能保证容量或可用性。仍需要副本、拓扑、就绪状态、中断策略、持久化状态以及经过测试的故障恢复机制。

此示例使用三个副本，并配置一个 PDB：当三个副本都健康时，允许主动驱逐一个副本；它没有假设 `N-1` 是 PDB 的字面取值。旧版十副本示例只是一个容量规划选择，并非通用要求。nginx 镜像/摘要和非 root 配置与经过审查的运维示例一致。探针通过 8080 端口访问 `/`；任意应用镜像不一定实现 `/health`。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: workload-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
---
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
  limits:
    cpu: '32'
    memory: 128Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
  namespace: workload-lab
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
    spec:
      containers:
      - name: web
        image: nginxinc/nginx-unprivileged:1.30.6@sha256:455cebcadcac0b597cdeaab077d93fb8ad59a98f7ed001dcf8f8693154b5d3d3
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        ports:
        - containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        readinessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 5
        startupProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 2
          failureThreshold: 30
        livenessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 20
          failureThreshold: 3
      terminationGracePeriodSeconds: 60
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: web-tier
      tolerations:
      - key: workload-lab
        operator: Equal
        value: web-tier
        effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 128Mi
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        nodeAffinityPolicy: Honor
        nodeTaintsPolicy: Honor
        labelSelector:
          matchLabels:
            app: web-frontend
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: web-frontend
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-frontend
  namespace: workload-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web-frontend
```

硬性可用区分布要求至少有两个符合条件的域；容量不足时，Pod 可能会保持 Pending。软性主机名分布只是一个偏好，并不意味着每个节点放置一个副本，也不保证覆盖三个 AZ。请检查匹配的标签、子网覆盖范围和故障策略。

启动探针可避免缓慢初始化期间被过早执行存活检查。就绪状态决定端点是否符合服务条件；存活探针会重启容器。请根据具体应用选择阈值，并避免因共享依赖不可用而导致每个副本都被存活检查重启。此处示例中的探针时间并非经过测量的启动 SLA。

## 批处理：重试不等于检查点恢复

仅对能够容忍中断、错过截止时间和 Spot 容量不可用的任务使用 Spot。此池没有 On-Demand 回退。`restartPolicy: OnFailure` 可以在仍存活的 Pod 上重启失败的容器；它无法从已终止节点中恢复丢失的进程内存。除非应用实现相应逻辑，否则 `SPOT_AWARE=true` 只是一个环境变量。

以下 Indexed Job 会打印逻辑分片编号，作为一个**冒烟测试示例**。它采用双路并行、五次完成、截止时间和有限重试，而不是旧版 20 路并行/100 次完成的容量规划示例。它不是数据处理实现。经过审查的 BusyBox 镜像索引包含 Linux amd64/arm64；本次审计未运行该镜像。

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
---
apiVersion: batch/v1
kind: Job
metadata:
  name: indexed-smoke
  namespace: workload-lab
spec:
  completionMode: Indexed
  parallelism: 2
  completions: 5
  backoffLimit: 2
  activeDeadlineSeconds: 300
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels:
        app: indexed-smoke
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      terminationGracePeriodSeconds: 30
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: processor
        image: busybox:1.38.0@sha256:fd7dc98638c8e305f4dc34e979f1c0fdfdcaeb0fbf8fcff77ae834b6da3d7e6e
        command:
        - /bin/sh
        - -ec
        args:
        - printf 'logical shard=%s; smoke only\n' "$JOB_COMPLETION_INDEX"
        env:
        - name: JOB_COMPLETION_INDEX
          valueFrom:
            fieldRef:
              fieldPath: metadata.annotations['batch.kubernetes.io/job-completion-index']
        resources:
          requests:
            cpu: 100m
            memory: 32Mi
          limits:
            cpu: 500m
            memory: 64Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
      nodeSelector:
        karpenter.sh/nodepool: batch-tier
      tolerations:
      - key: workload-lab
        operator: Equal
        value: batch-tier
        effect: NoSchedule
```

实际任务需要幂等的输出提交、持久化检查点和恢复逻辑。即使是 Indexed Job，在某些故障情况下，同一个索引也可能执行多次；不要假设副作用只会发生一次。请在 TTL 清理前导出所需日志/工件。节点本地缓存和 emptyDir 都不是持久化检查点。

当符合条件的应用工作负载结束后，`WhenEmpty` 可以清理节点；30 秒的 `consolidateAfter` 是防抖时间，并不保证运行中的任务会完成，也不保证节点会在 30 秒后消失。漂移、到期和中断仍是相互独立的生命周期路径。

## GPU 推理：检查完整的节点规格

Auto Mode 管理 NVIDIA 驱动程序/设备支持和 Bottlerocket 镜像。它不支持旧版 `amiFamily: AL2023` 或 `blockDeviceMappings` NodeClass 字段。

| 实例 | GPU 数量 | GPU 内存 | 主机 vCPU / RAM |
|----------|------|------------|-----------------|
| g5.xlarge | 1 A10G | 24 GB | 4 / 16 GiB |
| g5.2xlarge | 1 A10G | 24 GB | 8 / 32 GiB |
| g5.4xlarge | 1 A10G | 24 GB | 16 / 64 GiB |
| g5.12xlarge | 4 A10G | 总计 96 GB，每个 24 GB | 48 / 192 GiB |
| p5.48xlarge | 8 H100 | 总计 640 GB，每个 80 GB | 192 / 2 TiB |

这些只是示例，并非最新 GPU 实例或普遍可用 GPU 实例的列表。GPU 显存总量不等于单个连续设备的显存。尤其是，旧 Pod 的 4 CPU/16Gi 请求在扣除节点/系统预留和 DaemonSet 开销后，无法适配 g5.xlarge。此推理池允许使用更大的 G5 规格，并避免为未经审查的单 GPU 服务选择八 GPU 训练节点。

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: gpu-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      Name: private-subnet
  securityGroupSelectorTerms:
  - tags:
      Name: worker-restricted
  advancedNetworking:
    associatePublicIPAddress: false
  ephemeralStorage:
    size: 200Gi
    iops: 6000
    throughput: 250
---
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
    consolidateAfter: 10m
    budgets:
    - nodes: 10%
  limits:
    cpu: '64'
    memory: 256Gi
    nvidia.com/gpu: '4'
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-inference
  namespace: workload-lab
spec:
  replicas: 0
  selector:
    matchLabels:
      app: ml-inference
  template:
    metadata:
      labels:
        app: ml-inference
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: inference
        image: registry.example.invalid/reviewed-inference:replace-me
        resources:
          requests:
            cpu: '4'
            memory: 16Gi
            nvidia.com/gpu: 1
          limits:
            cpu: '4'
            memory: 16Gi
            nvidia.com/gpu: 1
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
      nodeSelector:
        karpenter.sh/nodepool: gpu-tier
      tolerations:
      - key: workload-lab
        operator: Equal
        value: gpu-tier
        effect: NoSchedule
      - key: nvidia.com/gpu
        operator: Equal
        value: 'true'
        effect: NoSchedule
```

在将刻意无效的示例 registry/image 替换为经过审查的不可变镜像，并提供其实际入口点、模型/输入路径、探针、存储和范围受限的工作负载身份之前，请保持 `replicas: 0`。使用该镜像验证驱动程序/CUDA/库兼容性，以及非 root UID 1000/安全策略；本次审计未验证推理运行时。

`ephemeralStorage` 是节点存储配置，并非持久化模型/检查点存储，也不保证吞吐量。请检查实际可分配存储和底层设备。节点根卷/数据 EBS 加密不代表任意 PVC 都已加密。GPU 数量限制约束的是池资源，而非总费用；快速调配期间还可能暂时超出限制。原有的 16/20 GPU 示例只是容量规划选择；本实验室配置采用较小的四 GPU 上限。

`WhenEmpty` 配合十分钟防抖时间，可以减少工作负载结束后的资源波动。它不会延迟调度，直到 GPU 初始化完成，也不保证节点会保持预热状态。如果适合使用预先调配的所需容量，可以采用 Static NodePool，但其限制/整合语义不同，并会持续产生费用。

## 分布式训练与 EFA

Auto Mode 对 EFA 的支持是当前有效的功能。**在磁盘设置旁添加注释并不会启用它。**受支持的 NodeClass 字段是 `advancedNetworking.networkInterfaces`；device-plugin 路径会公开 `vpc.amazonaws.com/efa`。

在启用训练工作负载之前，请检查以下各项：

- Auto Mode 当前**不**支持 EFA DRA 路径。请使用 EFA device plugin，而不要照搬为其他计算模式编写的 DRANET ResourceClaim 示例。
- NVIDIA/Neuron 主机驱动程序由 Auto Mode 管理；仅有 EFA 主机依赖项，并不能证明已安装独立的 EFA device plugin 且其状态为 Ready。
- 仅使用 EFA 的接口承载 RDMA，不承载 Pod IP。主接口是 card 0/device 0，类型为 `interface`。此示例添加四个 `efa-only` 设备和一个用于 Pod IP 的 `/28` 前缀。
- 静态接口配置仅支持 IPv4；启动后不会添加额外 IP/前缀/ENI。请勿将多接口配置与 `associatePublicIPAddress` 组合使用。请为工作负载和系统 Pod 规划 IP 容量。
- 使用现有的兼容 placement group、匹配的私有 AZ/子网，以及经过审查并允许所需自引用流量的 EFA 安全组。示例中的 AZ/group 名称是占位符，并不能证明那里有可用的 P5 容量。
- 检查 EFA/libfabric/NCCL、进程启动/会合、GPU/EFA 局部性，以及任何所需的大页/内存锁定设置。四设备接口示例并不意味着 P5 网络带宽已达到上限，也不表示在 Auto Mode 的 Bottlerocket 主机上会自动实现 GPU/EFA 对齐。

以下同构 P5 池避免假设混合 P4d/P5 工作节点可以互换。P4d 仍是一个备选方案，但需要单独验证兼容池/运行时。旧版 500Gi/16,000 IOPS/1,000 throughput 和额外 2,000Gi 数据磁盘值仅供说明；受支持的 NodeClass 不会创建此类任意额外块设备。

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: ml-training-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      Name: private-subnet
  securityGroupSelectorTerms:
  - tags:
      Name: reviewed-efa-security-group
  advancedNetworking:
    networkInterfaces:
    - networkCardIndex: 0
      deviceIndex: 0
      interfaceType: interface
      secondaryIPv4PrefixCount: 1
    - networkCardIndex: 0
      deviceIndex: 1
      interfaceType: efa-only
    - networkCardIndex: 1
      deviceIndex: 0
      interfaceType: efa-only
    - networkCardIndex: 2
      deviceIndex: 0
      interfaceType: efa-only
    - networkCardIndex: 3
      deviceIndex: 0
      interfaceType: efa-only
  ephemeralStorage:
    size: 500Gi
    iops: 16000
    throughput: 1000
  placementGroupSelector:
    name: reviewed-ml-training-pg
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ml-training
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - p
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
        - p5.48xlarge
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - ap-northeast-2a
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: ml-training-nodeclass
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: ml-training
        effect: NoSchedule
      - key: nvidia.com/gpu
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: ml-training
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30m
    budgets:
    - nodes: 10%
  limits:
    cpu: '960'
    memory: 10Ti
    nvidia.com/gpu: '40'
```

### 保留的旧版 PyTorchJob 结构

`kubeflow.org/v1 PyTorchJob` 需要 **Kubeflow Training Operator V1**；结构验证使用了其发布的 v1.9.3 CRD。当前 Kubeflow Trainer 的 TrainJob/Runtime API 有所不同。仅创建 NodePool 并不会让 Auto Mode 安装任一 operator。

此模板已暂停，并使用一个刻意无效的占位镜像。它展示了一个 master 加三个 worker、每个节点八个本地 GPU 进程，以及每个 Pod 四个 EFA 设备：启用后为**32 个 GPU / 四个八 GPU 节点**。该池的 40 GPU 上限最多允许五个此类节点规格，可作为包含替换余量的规划上限；它不是预留，也不是严格的账单上限。

```yaml
apiVersion: kubeflow.org/v1
kind: PyTorchJob
metadata:
  name: distributed-training
  namespace: workload-lab
spec:
  nprocPerNode: '8'
  runPolicy:
    suspend: true
    activeDeadlineSeconds: 3600
    backoffLimit: 1
    cleanPodPolicy: None
  pytorchReplicaSpecs:
    Master:
      replicas: 1
      restartPolicy: Never
      template:
        metadata:
          labels:
            app: distributed-training
        spec:
          automountServiceAccountToken: false
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            runAsGroup: 1000
            seccompProfile:
              type: RuntimeDefault
          containers:
          - name: pytorch
            image: registry.example.invalid/reviewed-training:replace-me
            resources:
              requests:
                cpu: '32'
                memory: 128Gi
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
              limits:
                cpu: '32'
                memory: 128Gi
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
            securityContext:
              allowPrivilegeEscalation: false
              capabilities:
                drop:
                - ALL
          nodeSelector:
            karpenter.sh/nodepool: ml-training
          tolerations:
          - key: workload-lab
            operator: Equal
            value: ml-training
            effect: NoSchedule
          - key: nvidia.com/gpu
            operator: Equal
            value: 'true'
            effect: NoSchedule
    Worker:
      replicas: 3
      restartPolicy: Never
      template:
        metadata:
          labels:
            app: distributed-training
        spec:
          automountServiceAccountToken: false
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            runAsGroup: 1000
            seccompProfile:
              type: RuntimeDefault
          containers:
          - name: pytorch
            image: registry.example.invalid/reviewed-training:replace-me
            resources:
              requests:
                cpu: '32'
                memory: 128Gi
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
              limits:
                cpu: '32'
                memory: 128Gi
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
            securityContext:
              allowPrivilegeEscalation: false
              capabilities:
                drop:
                - ALL
          nodeSelector:
            karpenter.sh/nodepool: ml-training
          tolerations:
          - key: workload-lab
            operator: Equal
            value: ml-training
            effect: NoSchedule
          - key: nvidia.com/gpu
            operator: Equal
            value: 'true'
            effect: NoSchedule
```

取消暂停之前，请提供经过审查的镜像/入口点，以实现 operator 的分布式启动约定，并提供实际数据集路径以及持久化检查点/工件导出机制。请验证 operator、队列/组调度行为、四节点容量、DNS/会合、网络规则、运行时权限和截止时间。这不是完整的生产训练配方。如果经过审查的加速器运行时需要受限命名空间模板无法满足的权限，可能需要单独审查工作负载策略；请勿简单地禁用集群级准入安全。

暂停已在运行的旧版 PyTorchJob 会删除其活动 Pod/PodGroup；这不是检查点操作。`cleanPodPolicy: None` 会保留已完成的 Pod 供检查，但不会导出工件。请在持久化导出后审查清理工作，包括 PVC、节点和单独管理的预留资源。

### 观察实际设备容量

此只读快照会报告实际可分配值和 Ready 状态。缺少 GPU/EFA 值或 API 调用失败，不能被视为设备已成功配置：

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/compute-type=auto -o json |
jq '[.items[]|{name:.metadata.name,
  instanceType:.metadata.labels["node.kubernetes.io/instance-type"],
  pool:.metadata.labels["karpenter.sh/nodepool"],
  allocatable:{cpu:.status.allocatable.cpu,memory:.status.allocatable.memory,
    gpu:.status.allocatable["nvidia.com/gpu"],efa:.status.allocatable["vpc.amazonaws.com/efa"]},
  conditions:[.status.conditions[]?|select(.type=="Ready")|{type,status,reason}]}]'
```

## 资源与架构决策

| 工作负载 | 候选策略 | 仍需验证的事项 |
|----------|------------------|-------------------------|
| Web / API | On-Demand 或谨慎混合容量；适度整合 | 可用性预算、副本数、运行时架构和实测延迟 |
| 批处理 / CI | 在重启和截止时间行为允许时使用 Spot | 幂等性、持久化进度、重试和容量不可用情况 |
| 数据库 / 流处理 | 考虑状态的调度位置和中断策略 | 仲裁、卷拓扑、恢复和分区行为 |
| GPU 推理 | 根据模型选择 GPU/CPU/RAM，并考虑预热容量 | 镜像/驱动程序兼容性、探针、冷启动和成本 |
| 分布式训练 | 同构加速器池和经过验证的网络/运行时 | 组调度容量、检查点/导出、EFA 设备和调度位置 |

原有的 24h/72h/168h/336h 到期时间和 30s/1m/5m/10m/15m/30m 整合时间只是策略示例，并非按工作负载类型设定的默认值。Auto Mode 的最长生命周期和单独的终止宽限期仍然适用。

对于 CPU 密集型工作负载，旧版 2 CPU/2Gi 请求和 4 CPU/4Gi 限制只是可能的突发策略示例，并非通用规格。对于内存密集型工作负载，8Gi 请求/限制本身并不能在 CPU 请求和限制不同时提供 Guaranteed QoS。Guaranteed QoS 还取决于所有相关容器/资源，而且内存限制仍可能导致 OOM。此前的 1.2–1.5× 使用量和 2× 请求公式没有经过验证的通用性能依据。

使用 device-plugin API 时，GPU 资源是整数型扩展资源：请指定限制，并可选择设置匹配的请求；仅指定请求并不是 GPU 的使用方式。CPU/内存请求必须为所需系统工作预留足够的节点可分配容量。仅降低限制通常不会改善基于请求的装箱。

### 多架构验证

请检查固定版本镜像索引，而不要使用 grep 检查 `nginx:latest`。索引中包含两个平台只是必要的打包检查，并不能证明原生依赖项和应用行为在两个平台上都有效：

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

对于你自己的、经过审查的 Dockerfile，以下命令会写入本地 OCI 归档，而不是发布一个未指定的镜像：

```bash
: "${BUILD_CONTEXT:?Set the reviewed Dockerfile directory}"
test -f "$BUILD_CONTEXT/Dockerfile"
docker buildx build --platform linux/amd64,linux/arm64 \
  --output "type=oci,dest=$WORK_DIR/app-multiarch.tar" "$BUILD_CONTEXT"
```

构建需要合适的 Buildx builder、原生 worker，或正确配置的模拟/交叉编译。请在通过常规 registry 工作流发布前运行特定架构的应用测试。此前关于混合 Spot/Graviton 可节省约 40% 的说法仍是未经验证的估算；请按照 [成本管理](./06-cost-management.md) 中的说明比较实际有效工作成本。

## 参考资料

- [Auto Mode AI/ML 计算](https://docs.aws.amazon.com/eks/latest/userguide/ml-node-pools.html)
- [NodeClass 存储和静态网络接口](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [EFA 设备管理（包括 Auto Mode）](https://docs.aws.amazon.com/eks/latest/userguide/device-management-efa.html)
- [G5 实例规格](https://aws.amazon.com/ec2/instance-types/g5/)
- [P5 实例规格](https://aws.amazon.com/ec2/instance-types/p5/)
- [Kubernetes Jobs 和 Indexed Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/)
- [Kubernetes GPU 调度](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/)
- [资源请求、限制和数量](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [拓扑分布约束](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [启动、就绪和存活探针](https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/)
- [Training Operator v1.9.3 PyTorchJob CRD](https://github.com/kubeflow/training-operator/blob/v1.9.3/manifests/base/crds/kubeflow.org_pytorchjobs.yaml)
- [Kubeflow Trainer 和旧版 v1 迁移](https://github.com/kubeflow/trainer)
- [Docker 多平台构建](https://docs.docker.com/build/building/multi-platform/)

< [上一页：节点生命周期](./07-node-lifecycle.md) | [目录](./README.md) | [下一页：迁移指南](./09-migration-guide.md) >
