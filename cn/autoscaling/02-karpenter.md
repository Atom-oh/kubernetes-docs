# Karpenter

> **支持的版本**: Karpenter 1.14 LTS（示例：1.14.1）；请使用兼容性和提供商支持表选择 Kubernetes/EKS 版本。
> **最后更新**: October 12, 2026

## 目录
- [介绍](#introduction)
- [架构](#architecture)
- [安装和配置](#installation-and-configuration)
- [NodePool](#nodepool)
- [节点类](#node-classes)
- [中断处理](#interruption-handling)
- [集成](#integration)
- [与 Amazon EKS 集成](#integration-with-amazon-eks)
- [最佳实践](#best-practices)
- [故障排除](#troubleshooting)
- [结论](#conclusion)

## 介绍

Karpenter 是一个开源节点自动扩缩器。本章使用其 AWS 提供商，它会为兼容的 Kubernetes 工作负载预置 EC2 容量。可用性和效率取决于约束、云容量、节点初始化以及应用程序设计。

### Karpenter 的主要优势

1. **响应式扩缩**：响应不可调度工作负载需求而开始预置；节点和应用程序就绪没有固定的延迟保证。
2. **成本优化**：为工作负载选择最合适的实例类型
3. **简化配置**：通过声明式 API 轻松配置
4. **以工作负载为中心的设计**：根据 Pod 要求预置节点
5. **云集成**：利用云提供商能力
6. **高效装箱**：优化资源利用率
7. **灵活的节点管理**：节点生命周期管理和集成的中断处理

### 与现有自动扩缩器的比较

| 功能 | Karpenter | Cluster Autoscaler | 云提供商托管节点组 |
|---------|-----------|-------------------|---------------------------|
| 扩缩速度 | 取决于调度、EC2 容量和初始化 | 取决于节点组扩缩和初始化 | 取决于扩缩策略、容量和初始化 |
| 实例类型选择 | 动态 | 基于节点组 | 基于节点组 |
| 装箱效率 | 取决于工作负载/约束 | 取决于工作负载/节点组 | 取决于调度器和扩缩控制器 |
| 配置复杂度 | 低 | 中 | 低 |
| 云集成 | 提供商特定的实现 | 多种云提供商集成 | 提供商原生 |
| 节点组管理 | 不需要 | 需要 | 需要 |
| 中断处理 | 已配置的事件处理和节点生命周期 | 取决于平台/集成 | 平台特定的处理 |

> **注意**：EKS 于 2026 年 4 月 8 日新增了 Managed Node Group 预热池支持。预初始化实例可以减少重复初始化工作；Stopped 和 Running 模式具有不同的转换时间和成本，且缩容时复用是可选的。据 AWS 称，Cluster Autoscaler 集成不需要额外配置。恢复、节点就绪和应用程序启动仍需时间。这是 EKS Managed Node Group/Auto Scaling 功能，不是 Karpenter 管理的池。

## 架构

Karpenter 作为 Kubernetes 控制器运行，检测不可调度的 Pod 并预置适当的节点。

![展示 Karpenter 控制器在 Kubernetes 集群中监视不可调度 Pod、使用经 CEL 验证的 NodePool 和 EC2NodeClass CRD，并调用 Kubernetes API 与云提供商 Instance API 来预置计算实例的架构图。](../.gitbook/assets/en-autoscaling-02-karpenter-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-02-karpenter-0.html)

### Karpenter 工作流

下图展示 Karpenter 如何在 EKS 集群中工作：

![展示不可调度 Pod 经 Kubernetes API 到达 Karpenter 控制器、Karpenter 查询 AWS EC2 API 并请求节点，以及新节点注册后 Pod 最终被调度的时序图。](../.gitbook/assets/en-autoscaling-02-karpenter-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-02-karpenter-1.html)

### 关键组件

1. **Karpenter Controller**：模拟调度需求，创建 NodeClaim 并管理节点生命周期；Kubernetes 的调度器执行实际的 Pod 绑定。
2. **CRD CEL 验证**：NodePool 和 EC2NodeClass 由 CRD 中的 CEL 规则验证（admission/conversion webhook 已在 Karpenter 1.1 中移除）
3. **NodePool 和 NodeClaim CRD**：NodePool 定义策略；NodeClaim 记录单个已预置节点的要求和生命周期。
4. **EC2NodeClass CRD**：定义要预置的节点配置
5. **云提供商集成**：与云提供商 API 集成以管理计算资源

### 工作原理

1. Karpenter Controller 检测不可调度的 Pod
2. 分析 Pod 要求（资源、节点选择器、容忍度等）
3. 根据 NodePool 和 EC2NodeClass 配置确定合适的节点类型
4. 调用云提供商 API 预置节点
5. 节点注册并变为就绪；随后 Kubernetes 调度器可以绑定符合条件的 Pod。Karpenter 不替代 kube-scheduler。
6. 整合、漂移、过期、手动删除和云中断具有不同的触发条件和防护措施；它们并非都是 SQS 中断事件。

## 安装和配置

不含 apiVersion/kind 的 YAML 块是所讨论的 NodePool 或 EC2NodeClass spec 的配置片段；它们不是独立的 kubectl apply 文档。

这些是针对现有集群的独立学习示例，而不是生产就绪部署包。重复的对象名称代表备选方案。安装前请准备并验证 IAM/OIDC、节点访问权限、获批准的子网/安全组、引导容量和中断队列。所有 YAML 都使用诸如 `my-cluster` 的字面示例名称；kubectl 不会在已保存的 YAML 文件中展开 `${CLUSTER_NAME}`。本次审计没有预置 AWS 资源、安装 Karpenter 或测量扩缩。若该版本已存在，全新安装命令会失败；现有安装必须遵循版本化的升级/CRD 迁移指南。

### 前提条件

- 使用平台和 Karpenter 矩阵支持的 Kubernetes 版本。已发布的矩阵将 Kubernetes1.34 的最低 Karpenter 版本列为 1.6、1.35 为1.9、1.36 为1.13；这些最低版本并不表示每个旧 Karpenter 次版本仍受维护。该矩阵目前未确认1.37 兼容性。必须单独检查 EKS 版本可用性/支持情况。
- 已配置 kubectl
- 云提供商凭证和权限
- Helm（可选）

### 在 AWS EKS 上安装

#### 1. IAM 角色和策略设置

这些命令假定已有 controller 角色、节点角色和基于 API 的 EKS 身份验证（API 或 API_AND_CONFIG_MAP）。仅使用 CONFIG_MAP 的集群需要检查其现有 aws-auth 节点映射，而不是 list-access-entries；请勿将更改身份验证模式作为附带设置步骤。节点角色信任 EC2，并需要 worker-node/ECR 拉取权限（例如 AmazonEKSWorkerNodePolicy 和 AmazonEC2ContainerRegistryPullOnly）。在支持的情况下，为 VPC CNI 提供自己的身份；SSM 权限是可选的，并且需要已配置的代理。AmazonEKSClusterPolicy 不能替代 Karpenter controller 策略。

```bash
# Set the existing cluster and Region; these commands only inspect AWS/Kubernetes.
export CLUSTER_NAME="my-cluster"
export AWS_REGION="us-west-2"
export KARPENTER_VERSION="1.14.1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
CLUSTER_ENDPOINT=$(aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" --query cluster.endpoint --output text)
export ACCOUNT_ID CLUSTER_ENDPOINT
kubectl config current-context
aws iam get-role --role-name "KarpenterControllerRole-${CLUSTER_NAME}" --query Role.AssumeRolePolicyDocument
aws iam get-role --role-name "KarpenterNodeRole-${CLUSTER_NAME}" --query Role.AssumeRolePolicyDocument
aws eks list-access-entries --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME"
```

#### 2. 使用 Helm 安装

在准备好所引用的队列和引导容量后，仅运行一次全新安装示例。升级时，请查看版本化迁移指南并更新匹配的 CRD（例如通过单独管理的 karpenter-crd chart）；仅升级 controller chart 通常不会升级 CRD。迁移现有 CRD 安装前请验证所有权。

```bash
# Run only after the prerequisites and the current kubectl context are verified.
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${ACCOUNT_ID:?Set the AWS account ID}"
: "${CLUSTER_ENDPOINT:?Set the matching EKS endpoint}"
KARPENTER_VERSION="1.14.1"
helm install karpenter oci://public.ecr.aws/karpenter/karpenter \
  --version "$KARPENTER_VERSION" \
  --namespace karpenter --create-namespace \
  --set-string 'serviceAccount.annotations.eks\.amazonaws\.com/role-arn'="arn:aws:iam::${ACCOUNT_ID}:role/KarpenterControllerRole-${CLUSTER_NAME}" \
  --set-string settings.clusterName="$CLUSTER_NAME" \
  --set-string settings.clusterEndpoint="$CLUSTER_ENDPOINT" \
  --set-string settings.interruptionQueue="$CLUSTER_NAME" \
  --wait --timeout 5m
```

#### 3. 验证安装

```bash
kubectl get deployments,pods -n karpenter
kubectl rollout status deployment/karpenter -n karpenter --timeout=180s
kubectl get nodepools,ec2nodeclasses,nodeclaims
```

默认两个 controller 副本的示例输出（不是在本次审计中捕获的执行结果）：
```
NAME                         READY   STATUS    RESTARTS   AGE
karpenter-<hash>-<id-1>      1/1     Running   0          1m
karpenter-<hash>-<id-2>      1/1     Running   0          1m
```

### 基础 NodePool 和 EC2NodeClass 配置

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
  limits:
    cpu: '1000'
    memory: 1000Gi
  template:
    spec:
      requirements:
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
        - m5.large
        - m5.xlarge
        - m5.2xlarge
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  role: KarpenterNodeRole-my-cluster
  amiSelectorTerms:
  - alias: al2023@latest
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  tags:
    karpenter.sh/discovery: my-cluster
  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 100Gi
      volumeType: gp3
      deleteOnTermination: true
      encrypted: true
```

## NodePool

NodePool 是一种 Kubernetes 自定义资源，用于定义 Karpenter 如何预置节点。它替代了以前的 Provisioner。

### 基础 NodePool 配置

下面的特殊污点有意要求匹配的工作负载容忍度。在拥有已验证、会移除所配置污点的初始化程序之前，请保持 startupTaints 为空；在没有其所有者的情况下凭空创建启动污点，可能会使节点无法使用。限制、初始化和中断示例都是备选方案，而非对运行中生产 NodePool 的累加变更。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    metadata:
      labels:
        environment: training
        app: web
    spec:
      requirements:
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
        - m5.large
        - m5.xlarge
        - m5.2xlarge
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
      expireAfter: 720h
      taints:
      - key: example.com/special-taint
        value: 'true'
        effect: NoSchedule
      startupTaints: []
  limits:
    cpu: '1000'
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### 要求配置

要求彼此之间、与 EC2NodeClass 以及与 Pod 约束取交集。仅当符合条件的实例类型、AMI 和容器镜像都支持两种架构时，允许 amd64 和 arm64 才有帮助。符合条件的可用区/容量类型列表不保证均匀分布；为此请使用工作负载拓扑约束。

要求定义 Karpenter 将预置的节点特征：

```yaml
template:
  spec:
    requirements:
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
    - key: node.kubernetes.io/instance-type
      operator: In
      values:
      - m5.large
      - m5.xlarge
      - c5.large
      - m6g.large
      - c6g.large
    - key: topology.kubernetes.io/zone
      operator: In
      values:
      - us-west-2a
      - us-west-2b
      - us-west-2c
    - key: kubernetes.io/os
      operator: In
      values:
      - linux
```

### 限制配置

`spec.limits` 限制聚合的已预置资源，但并行预置使用最终一致性检查，可能暂时超过限制。它不是严格的计费上限。字符串数量可避免 API/GitOps 类型差异。

```yaml
limits:
  cpu: '1000'
  memory: 1000Gi
  nvidia.com/gpu: '10'
```

### 实验性 DRA 分配跟踪（v1.13）

Core Karpenter v1.13 新增了 DRA 设备分配跟踪。这不是生产 DRA 预置的一揽子保证：AWS1.14.1 chart 默认 `settings.ignoreDRARequests: true`，且上游将正式 DRA 支持标记为尚未 GA。Kubernetes1.29 最低版本不足以证明兼容性。请验证确切的 Kubernetes 资源 API、DRA 驱动程序、ResourceClaims/ResourceSlices 和 Karpenter 配置；不要将 DRA claim 视为可与下方 device-plugin 扩展资源示例互换。

### 节点过期配置

`expireAfter` 定义由过期驱动的驱逐何时开始，而不是保证替换完成的时间。下方可选的 `terminationGracePeriod` 限制驱逐时间，但可能强制删除剩余 Pod，包括被 PDB 阻止的 Pod。只有在验证应用程序关闭和恢复要求后才选择该截止时间。

```yaml
spec:
  template:
    spec:
      expireAfter: 720h
      terminationGracePeriod: 30m
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### 识别 NodeReadinessController 污点（v1.13）

Core Karpenter v1.13 在对未初始化托管节点进行调度模拟时，将独立 NodeReadinessController 的 `readiness.k8s.io/` 污点识别为临时污点。它仍等待这些污点消失后才将初始化标记为完成；它不会删除它们，也不会让 Kubernetes 调度器绕过它们。其他初始化程序污点仍需要准确的 `startupTaints` 配置和负责移除它们的控制器。

### 2026 年 7 月更新：发布 v1.14

Karpenter v1.14 于 2026 年 7 月 11 日发布，带来了：

- **CapacityBuffers API 支持**：alpha 容量缓冲区集成；`CapacityBuffer` 默认禁用，且需要匹配的 CRD/controller 配置。预留余量不是免费容量或延迟保证。
- **预览实例类型支持**：识别符合条件的预览产品；实际预置仍需要账户/Region 访问权限和可用性。
- **Nitro Enclaves 支持**：当 NodeClaim 资源请求包含 `eks.amazonaws.com/nip-slots` 时，提供商会在生成的 launch-template 中设置 `EnclaveOptions.Enabled`。兼容实例、AMI 和 device-plugin 设置仍是前提条件；在1.14.1 中没有 `EC2NodeClass.spec.enclaveOptions` 字段。
- 错误修复：核算辅助 ENI 上的主 IP、确保 Zonal Shift 缓存已水合、将 AWS SDK client 超时接入 operator 配置等

详见 [v1.14.0 release notes](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.14.0)。

在 2026 年 7 月17日，较旧分支收到了包括1.3.8 和1.11.3 在内的补丁。这个历史回移并不表示所有中间次版本都持续受支持。当前支持策略将 LTS1.9 列至 2027 年 2 月、LTS1.14 列至 2027 年 7 月；常规次版本仅支持到下一个次版本。请选择受支持的分支并遵循其迁移指南，而不是假定旧分支仍受维护。

AWS 在 2026 年 7 月22日的公告中为 Karpenter/EKS Auto Mode 添加了 EFA network-interface 和 placement-group 配置。在 AWS Karpenter1.14.1 中，具体字段是 `EC2NodeClass.spec.networkInterfaces` 和 `spec.placementGroupSelector`（而非 NodePool 字段）。仅 EFA 接口不消耗 VPC IP 地址，但 device/card index0 仍需要主 `interface`。请按名称或 ID 选择现有 placement group；其 cluster/spread/partition 策略和支持的实例会限制放置。本示例未配置或验证 HPC 工作负载。

### 2026 年 8 月更新：v1.14.1 补丁版本

[v1.14.1](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.14.1) 是 v1.14 分支的第一个补丁，于 2026 年 8 月 21 日发布。这是一个维护版本，升级了上游 `sigs.k8s.io/karpenter` 版本，并挑选了自 v1.14.0 以来的修复。

### 2026 年 10 月更新：发布 v1.15.0

[v1.15.0](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.15.0) 于 2026 年 10 月 10 日发布。主要变化：

- **节点修复成为自愿中断**：节点修复被纳入中断机制；当容量受限的 NodePool 无法先暂存替换节点时，采用先终止的修复。通过 `ec2:RebootInstances` 重启被加入为修复操作（由 `RebootForRepair` AWS feature gate 控制），此前的修复 controller 可通过 `--legacy-node-repair` 标志继续使用。
- **KubeletConfiguration 中的 CEL 支持**：`maxPodsExpression`、`kubeReserved` 和 `systemReserved` 接受 CEL 表达式，并扩展了 EC2NodeClass KubeletConfiguration 字段。
- **更广泛的 DRA 支持**：支持优先替代项，以及 NVIDIA 和 EFA driver DRA 支持。
- 此外：`--aws-feature-gates` 标志、默认 Pod topology spread 感知、在预置期间核算实例类型卷限制、诸如 `karpenter_pods_disrupted_total` 的新中断指标，以及受 feature gate 控制的 Pod 删除成本管理 controller。

根据支持策略，常规次版本仅支持到下一个次版本，因此随着 v1.15.0 发布，v1.14 仅作为 LTS 分支继续支持（至 2027 年 7 月）。详见 [v1.15.0 release notes](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.15.0)。

## 节点类

节点类定义 Karpenter 预置的节点配置。在 AWS 上，它使用 EC2NodeClass CRD。

### AWS EC2NodeClass 配置

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  tags:
    karpenter.sh/discovery: my-cluster
    environment: training
  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 100Gi
      volumeType: gp3
      deleteOnTermination: true
      encrypted: true
  role: KarpenterNodeRole-my-cluster
  amiSelectorTerms:
  - alias: al2023@latest
  userData: '#!/bin/bash

    echo "Hello from Karpenter node!"

    '
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 1
    httpTokens: required
```

### 子网和安全组选择

使用 selector term 选择子网和安全组（多个 term 之间是 OR；一个 term 内的 tags 之间是 AND）：

```yaml
subnetSelectorTerms:
- tags:
    karpenter.sh/discovery: my-cluster
    Name: private-*
securityGroupSelectorTerms:
- tags:
    karpenter.sh/discovery: my-cluster
```

### AMI 配置

Karpenter 通过 `amiSelectorTerms` 选择 AMI。别名选择 family/version；**`@latest` 不是版本固定项**，可能改变解析出的 AMI 并触发漂移。`@latest` 示例仅供学习。对于生产环境，请在发布前解析并测试明确受支持的 AMI release（具有真实发布日期的 `al2023@vYYYYMMDD`）或已批准的 AMI ID。Kubernetes1.33+ 不发布 AL2 EKS AMI。下列变体是备选方案，Custom AMI 需要可正常工作的 bootstrap、注册污点、kubelet、CNI/runtime 和 identity 设置。

```yaml
# Amazon Linux 2023
amiSelectorTerms:
  - alias: al2023@latest
---
# Bottlerocket
amiSelectorTerms:
  - alias: bottlerocket@latest
---
# Custom AMI (by ID) — amiFamily is required when no alias term is used
amiFamily: Custom
amiSelectorTerms:
  - id: "ami-0123456789abcdef0"
# Ubuntu: no v1 alias — use amiFamily: Custom with an id/tags/name term
```

### 块设备配置

设备映射特定于 AMI family。这些 AL2023 示例将 /dev/xvda 用作根设备；请检查其他 AMI 的实际布局。额外卷需要明确的文件系统/挂载或应用程序存储计划。客户管理的 KMS key 还需要适当的 key/IAM 权限。

您可以为节点定义存储配置：

```yaml
blockDeviceMappings:
- deviceName: /dev/xvda
  ebs:
    volumeSize: 100Gi
    volumeType: gp3
    iops: 3000
    throughput: 125
    deleteOnTermination: true
    encrypted: true
    kmsKeyID: arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab
- deviceName: /dev/xvdb
  ebs:
    volumeSize: 500Gi
    volumeType: gp3
    deleteOnTermination: true
    encrypted: true
```

### 用户数据配置

这些 shell user-data 片段假定使用 AL2023，其生成的 bootstrap/nodeadm 配置会由 Karpenter 与自定义数据合并。它们并非通用的有效 Bottlerocket/Windows bootstrap。请将软件包构建并测试到 AMI 中，不要在每次启动时运行不受限制的软件包更新。未配置 CloudWatch Agent 的配置、IAM 和网络路径就进行安装/启动，并不能建立遥测数据收集。

```yaml
userData: |
  #!/bin/bash
  set -euo pipefail
  # Only for a workload that requires this setting; keep node packages in a tested AMI.
  cat > /etc/sysctl.d/99-workload-map-count.conf <<'EOF'
  vm.max_map_count=262144
  EOF
  sysctl -p /etc/sysctl.d/99-workload-map-count.conf
```

### 节点整合过程

下图展示 Karpenter 的节点整合过程。该功能对于优化集群效率和降低成本很重要：

![概念性整合：模拟工作负载是否适合现有或替换容量，使所需替换节点就绪，然后驱逐并重建 Pod，最后终止符合条件的旧节点。这不是实时 Pod 迁移，也不保证三比一的结果。](../.gitbook/assets/en-autoscaling-02-karpenter-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-02-karpenter-2.html)

## 中断处理

已配置的中断处理会尝试在容量丢失前作出反应。通知、替换容量、关机截止时间和应用程序恢复决定结果；不保证持续可用性。

### 集成中断处理

云中断处理独立于整合/过期。它涵盖如下信号：

1. **Spot 中断警告**：开始驱逐，并在可能时请求替换容量；通知窗口不是保证恢复的 SLA。
2. **计划的健康/维护事件**：响应受影响的实例。
3. **实例停止/终止事件**：协调正在离开服务的容量。
4. **EC2 实例状态失败**：使用所需的 EC2 API 权限检查健康状态。仅 Rebalance 建议作为事件发布，不会自动执行 taint/drain/terminate 操作。

### 中断处理配置

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default

      # Node expiration settings
      expireAfter: 720h  # 30 days
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### 驱逐配置

Karpenter 通常在优雅驱逐期间使用 eviction。Helm settings 配置 controller；NodePool disruption budget 限制自愿整合/漂移的启动，而不是所有同时发生的节点损失。A30% budget 向上取整，然后减去 deleting/not-ready 节点；它不是严格的30% 上限。过期、中断和修复可能具有不同的强制行为。启用 `interruptionQueue` 前，请配置指定的 SQS 队列、EventBridge rules/targets、队列策略和 controller 权限；Helm 字段本身不会创建它们。

```yaml
settings:
  clusterName: my-cluster
  interruptionQueue: my-cluster
  batchMaxDuration: 10s
  batchIdleDuration: 1s
  featureGates:
    spotToSpotConsolidation: false
controller:
  resources:
    requests:
      cpu: 1
      memory: 1Gi
    limits:
      cpu: '1'
      memory: 1Gi
logLevel: info
```

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
      expireAfter: 720h
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
    budgets:
      - nodes: "30%"   # Voluntary budget: round up, then subtract deleting/not-ready nodes
```

### PDB (PodDisruptionBudget) 集成

PDB 根据健康副本约束自愿 eviction；它们不会创建副本或保证应用程序可用性。下方的 `minAvailable: 2` 需要有足够匹配的健康 Pod 后才允许 eviction。实例丢失和强制终止截止时间仍可能中断它们。

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: default
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
```

## 集成

Karpenter 可与各种 Kubernetes 和云服务集成。

### Kubernetes 集成

#### 1. Pod 拓扑分布约束

Karpenter 在预置节点时会考虑 Pod Topology Spread Constraints：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-server
  namespace: default
spec:
  replicas: 10
  template:
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-server
      containers:
      - name: web-server
        image: nginx:1.30.4
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            memory: 256Mi
    metadata:
      labels:
        app: web-server
  selector:
    matchLabels:
      app: web-server
```

#### 2. Pod 亲和性/反亲和性

Karpenter 会考虑 Pod Affinity 和 Anti-Affinity 规则：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-server
  namespace: default
spec:
  replicas: 10
  template:
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - web-server
            topologyKey: kubernetes.io/hostname
      containers:
      - name: web-server
        image: nginx:1.30.4
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            memory: 256Mi
    metadata:
      labels:
        app: web-server
  selector:
    matchLabels:
      app: web-server
```

#### 3. 污点和容忍度

GPU 示例需要兼容的加速 AMI、NVIDIA driver 以及能容忍 GPU 污点并公布 nvidia.com/gpu 的 device-plugin DaemonSet。BusyBox Pod 仅演示预留 GPU；它不运行或基准测试 CUDA。请单独使用真实的 GPU 应用程序镜像进行验证。

Karpenter 在预置节点时会考虑污点和容忍度：

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu
spec:
  template:
    spec:
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - g4dn.xlarge
        - g4dn.2xlarge
      taints:
      - key: nvidia.com/gpu
        value: 'true'
        effect: NoSchedule
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gpu-app
  namespace: default
spec:
  replicas: 3
  template:
    spec:
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
      nodeSelector:
        karpenter.sh/nodepool: gpu
      containers:
      - name: gpu-allocation-demo
        image: busybox:1.37.0
        command:
        - sh
        - -c
        - sleep 3600
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            memory: 128Mi
            nvidia.com/gpu: 1
    metadata:
      labels:
        app: gpu-app
  selector:
    matchLabels:
      app: gpu-app
```

### AWS 集成

#### 1. EC2 Spot 实例

Karpenter 支持 EC2 Spot 实例以优化成本：

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot
spec:
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: spot
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: spot
spec:
  role: KarpenterNodeRole-my-cluster
  amiSelectorTerms:
  - alias: al2023@latest
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
```

#### 2. EC2 实例配置文件

role 和 instanceProfile 互斥。使用 role 时，Karpenter 管理 instance profile，并需要相应的 IAM API 权限/连接性。如果集群没有通向 IAM endpoint 的路径，请使用预置的 instanceProfile；IAM 没有 PrivateLink endpoint。controller 仍需要其 node role 的 PassRole，且 EKS 节点访问权限独立于拥有 EC2 凭证。

Karpenter 使用 EC2 instance profile 向节点授予 IAM 权限：

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  instanceProfile: KarpenterNodeInstanceProfile-my-cluster
  amiSelectorTerms:
  - alias: al2023@latest
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
```

#### 3. 替换 Launch Templates (EC2NodeClass)

Karpenter v1 不接受用户提供的 EC2 launch template（旧版 `launchTemplate` 字段已移除）。Karpenter 从 EC2NodeClass 自行生成和管理 launch template，因此原本会放入 launch template 的设置直接在 EC2NodeClass 中表达：

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: node-config
spec:
  role: KarpenterNodeRole-my-cluster
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  amiSelectorTerms:
  - alias: al2023@latest
  userData: '#!/bin/bash

    echo "Hello from Karpenter node!"

    '
  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 100Gi
      volumeType: gp3
      deleteOnTermination: true
      encrypted: true
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 1
    httpTokens: required
```
## 与 Amazon EKS 集成

当 identity、network、node access 和 bootstrap 已配置时，Karpenter 的 AWS provider 可与 EKS 管理的计算资源并行预置 EC2 容量。

![展示 Amazon EKS 集群中的 Karpenter controller 假设 IAM role 以直接调用 EC2 API、绕过 Auto Scaling Groups 和 Managed Node Groups 来创建 EC2 实例的架构图。](../.gitbook/assets/en-autoscaling-02-karpenter-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-02-karpenter-3.html)

### EKS 集群准备

请一致地替换所有示例名称。仅选择适用于 worker 的子网/安全组；为每个 control-plane 子网打标签不是安全的发现策略。允许节点启动前，请验证子网路由、安全规则、CNI IP 容量以及任何需要的私有 endpoint。

#### 1. 集群标签设置

让基础设施配置仅为已批准的 worker 子网和安全组打标签。VPC 标签不是选择这些资源的依据。发现值必须与示例匹配（此处为 `my-cluster`）；仅有标签并不能证明私有路由、合适的安全规则或足够的可用地址。应用 NodePool 前检查实际资源和路由。

```bash
# Inspect resources that your infrastructure configuration has tagged for this cluster.
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
aws ec2 describe-subnets --region "$AWS_REGION" \
  --filters "Name=tag:karpenter.sh/discovery,Values=${CLUSTER_NAME}" \
  --query 'Subnets[].{ID:SubnetId,AZ:AvailabilityZone,FreeIPs:AvailableIpAddressCount,PublicIPOnLaunch:MapPublicIpOnLaunch,VPC:VpcId}'
aws ec2 describe-security-groups --region "$AWS_REGION" \
  --filters "Name=tag:karpenter.sh/discovery,Values=${CLUSTER_NAME}" \
  --query 'SecurityGroups[].{ID:GroupId,VPC:VpcId,Name:GroupName}'
# Inspect explicit and main route-table associations for the intended subnets.
aws ec2 describe-route-tables --region "$AWS_REGION" \
  --filters "Name=vpc-id,Values=$(aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" --query cluster.resourcesVpcConfig.vpcId --output text)"
```

#### 2. IAM 角色设置

请使用下方特定版本的 controller policy 和 infrastructure reference，而不是之前不完整的手写 allow-all policy。Controller 凭证（此处为 IRSA）独立于节点凭证和 VPC CNI/workload identities。controller trust 必须与集群 OIDC provider、`system:serviceaccount:karpenter:karpenter` 和 `aud: sts.amazonaws.com` 匹配；仅授予此版本和所选 feature 所需的 actions/resources/conditions。节点角色必须获准加入 EKS，在启用基于 API 的身份验证时，通常通过 `EC2_LINUX` access entry。检查命令不会创建 IAM role 或 access entry。

```bash
# Download a versioned reference for review; this does not create a CloudFormation stack.
KARPENTER_VERSION="1.14.1"
curl --fail --show-error --location \
  "https://raw.githubusercontent.com/aws/karpenter-provider-aws/v${KARPENTER_VERSION}/website/content/en/preview/getting-started/getting-started-with-karpenter/cloudformation.yaml" \
  --output karpenter-cloudformation-reference.yaml
# Inspect the existing role's attached and inline policies.
: "${CLUSTER_NAME:?Set the existing cluster name}"
aws iam list-attached-role-policies --role-name "KarpenterControllerRole-${CLUSTER_NAME}"
aws iam list-role-policies --role-name "KarpenterControllerRole-${CLUSTER_NAME}"
```

### 在 EKS 集群上安装 Karpenter

```bash
# Run only after the prerequisites and the current kubectl context are verified.
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${ACCOUNT_ID:?Set the AWS account ID}"
: "${CLUSTER_ENDPOINT:?Set the matching EKS endpoint}"
KARPENTER_VERSION="1.14.1"
helm install karpenter oci://public.ecr.aws/karpenter/karpenter \
  --version "$KARPENTER_VERSION" \
  --namespace karpenter --create-namespace \
  --set-string 'serviceAccount.annotations.eks\.amazonaws\.com/role-arn'="arn:aws:iam::${ACCOUNT_ID}:role/KarpenterControllerRole-${CLUSTER_NAME}" \
  --set-string settings.clusterName="$CLUSTER_NAME" \
  --set-string settings.clusterEndpoint="$CLUSTER_ENDPOINT" \
  --set-string settings.interruptionQueue="$CLUSTER_NAME" \
  --wait --timeout 5m
```

### 与 EKS Managed Node Groups 一起使用

Karpenter 可以与 EKS Managed Node Groups 共存。下列 NodePool 预置单独的 EC2 节点；它不管理 Managed Node Group。将 controller 保留在可靠的 bootstrap capacity 上（默认 chart 排除 Karpenter 节点，并在不同 host 上请求两个副本）。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: managed-ng
spec:
  template:
    metadata:
      labels:
        managed-by: karpenter
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - m5.large
        - m5.xlarge
      taints:
      - key: managed-by
        value: karpenter
        effect: NoSchedule
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: managed-ng
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: managed-ng
spec:
  role: KarpenterNodeRole-my-cluster
  amiSelectorTerms:
  - alias: al2023@latest
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  tags:
    karpenter.sh/discovery: my-cluster
```

### 与 EKS Fargate 一起使用

Fargate 不实现 Kubernetes topologySpreadConstraints，且 Kubernetes affinity/anti-affinity 规则不适用于其中。请不要假定默认 chart 的 EC2 放置约束保证 Fargate AZ 隔离；请单独设计和验证 profile/subnet 放置。

选择范围很窄的 Fargate profile 可以承载 controller Pod，而 Karpenter 预置 EC2 worker。Karpenter 不创建 Fargate 容量或管理其 profile。准备一个选择 namespace `karpenter` 和 controller labels 的 profile，而不是选择全部 `default`/`kube-system`；JSON selector 形式是 `[{"namespace":"karpenter","labels":{"app.kubernetes.io/name":"karpenter"}}]`。该 profile 需要自己的 Pod execution role/private subnets，controller AWS 权限仍需要 IRSA（Fargate 不支持 EKS Pod Identity）。下列命令仅检查现有 profile。

```bash
# Inspect an existing, narrowly selected controller Fargate profile.
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
aws eks describe-fargate-profile --region "$AWS_REGION" \
  --cluster-name "$CLUSTER_NAME" --fargate-profile-name karpenter-controller
```

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ec2
spec:
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: ec2
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: ec2
spec:
  role: KarpenterNodeRole-my-cluster
  amiSelectorTerms:
  - alias: al2023@latest
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
```

### AZ 故障响应：Amazon ARC Zonal Shift 集成（2026 年 5 月）

Karpenter 可与已启用的 EKS ARC zonal-shift resource 集成。一旦手动 zonal shift 或已配置的 autoshift 处于活动状态，Karpenter 会避免在已转移的 AZ 中创建新容量。这并不是对每个 AZ 故障的独立检测，也不会覆盖将工作固定在该 AZ 的 Pod/PV 要求。

在活动 shift 期间，已转移 AZ 中的自愿中断将暂停；依赖将 Pod 移入该 AZ 的健康区中断也会被阻止。这并不是无条件暂停所有健康 AZ 中的每一种自愿中断。配置 EKS/ARC 前提条件、`eks:DescribeCluster`/ARC 权限和 `settings.enableZonalShift: true`（环境选项 `ENABLE_ZONAL_SHIFT`）；autoshift 还需要自己的 opt-in/practice 配置。不需要自定义 ARC CRD，且 shift 结束后操作会恢复。

### EKS 成本优化

您可以使用 Karpenter 为 EKS 集群优化成本：

![节点组扩缩与 Karpenter 动态容量选择、整合和 Spot 选项的概念性比较。未确定对扩缩速度或成本节省的测量结果或普遍排名。](../.gitbook/assets/en-autoscaling-02-karpenter-4.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-02-karpenter-4.html)

#### 1. 使用 Spot 实例

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot
spec:
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: spot
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: spot
spec:
  role: KarpenterNodeRole-my-cluster
  amiSelectorTerms:
  - alias: al2023@latest
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
```

#### 2. 使用多样化实例类型

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: flexible
spec:
  template:
    spec:
      requirements:
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
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - m5.large
        - m5.xlarge
        - m5.2xlarge
        - m6g.large
        - m6g.xlarge
        - m6g.2xlarge
        - c5.large
        - c5.xlarge
        - c5.2xlarge
        - c6g.large
        - c6g.xlarge
        - c6g.2xlarge
        - r5.large
        - r5.xlarge
        - r5.2xlarge
        - r6g.large
        - r6g.xlarge
        - r6g.2xlarge
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

#### 3. 启用节点整合

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
```

## 最佳实践

![按类别分组的 Karpenter 最佳实践：性能优化、成本优化、可用性改进和安全加固，这四个并列列表。](../.gitbook/assets/en-autoscaling-02-karpenter-5.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-02-karpenter-5.html)

### 性能优化

1. **选择适当的实例类型**：选择适合工作负载的实例类型
2. **允许多样化实例类型**：允许多种实例类型以提高可用性并优化成本
3. **设置适当的 TTL**：设置与工作负载模式匹配的 TTL
4. **启用节点整合**：启用节点整合以优化资源利用率

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: optimized
spec:
  template:
    spec:
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - m5.large
        - m5.xlarge
        - m5.2xlarge
        - c5.large
        - c5.xlarge
        - c5.2xlarge
        - r5.large
        - r5.xlarge
        - r5.2xlarge
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
      expireAfter: 720h
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### 成本优化

1. **利用 Spot 实例**：使用 Spot 实例节省成本
2. **选择适当的实例大小**：选择适合工作负载的实例大小
3. **评估空节点移除**：符合条件的 worker NodePool 可以缩至零；controller/bootstrap 计算资源和不相关的集群成本仍然存在。
4. **规划节点刷新**：过期会根据当前约束轮换符合条件的容量；它不会自动选择较新的实例类型或修补固定的 AMI。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-optimized
spec:
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
      expireAfter: 168h
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### 可用性改进

1. **使用多个 Availability Zone**：跨多个可用区部署节点
2. **混合 On-demand 和 Spot 实例**：平衡可用性和成本
3. **设置适当的 PDB**：结合冗余和恢复设计，在实际健康副本限制内保护自愿 eviction。
4. **配置并测试中断处理**：验证通知路径、关机截止时间和替换容量，不要假定服务不中断。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: high-availability
spec:
  template:
    spec:
      requirements:
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - us-west-2a
        - us-west-2b
        - us-west-2c
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
        - spot
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
      expireAfter: 720h
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 60s
```

## 故障排除

### 常见问题

#### 1. 节点预置失败

**症状**：Pod 保持在 Pending 状态且未预置节点

**解决方案**：
- 检查 Karpenter 日志
- 验证 IAM 权限
- 检查 NodePool 配置

```bash
# Check Karpenter logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller

# Check NodePool status
kubectl describe nodepool <name>

# Check pod events
kubectl describe pod <name>
```

#### 2. 节点移除问题

**症状**：节点未按预期移除

**解决方案**：
- 检查 TTL 设置
- 验证节点整合设置
- 检查 Pod 驱逐状态

```bash
# Check node status
kubectl describe node <name>

# Check node labels
kubectl get node <name> --show-labels

# Check Karpenter logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller --since=30m
```

#### 3. 实例类型选择问题

**症状**：预置了意外的实例类型

**解决方案**：
- 检查 NodePool 要求
- 验证 Pod 资源请求
- 检查可用区约束

```bash
# Check NodePool requirements
kubectl get nodepool <name> -o yaml

# Check pod resource requests
kubectl describe pod <name>

# Check node information
kubectl describe node <name>
```

### 调试工具

```bash
# Check Karpenter version
kubectl get deployment -n karpenter karpenter -o jsonpath="{.spec.template.spec.containers[0].image}"

# Check Karpenter logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller

# Check NodePool list
kubectl get nodepools

# Check EC2NodeClass list
kubectl get ec2nodeclasses

# Check events
kubectl get events --sort-by='.lastTimestamp'

# Inspect the installed chart version and values before any optional log-level change.
helm list --namespace karpenter --filter '^karpenter$'
helm get values karpenter --namespace karpenter
kubectl get nodeclaims -o wide
```

## 结论

Karpenter 根据工作负载和基础设施约束自动执行节点预置和生命周期管理。它可以改善容量管理，但可用性、性能和成本结果需要针对工作负载进行验证。

本文档介绍了 Karpenter 的基本概念、安装方法、NodePool 和 EC2NodeClass 配置、中断处理、各种集成、与 Amazon EKS 的集成、最佳实践和故障排除。

使用 Karpenter，您可以简化集群管理、优化资源利用率并降低成本。特别是在 Amazon EKS 等云托管 Kubernetes 环境中，您可以最大化 Karpenter 的优势。

### 后续步骤

- 使用 Karpenter 实施成本优化策略
- 为各种工作负载类型配置 NodePool
- 设计混合集群架构
- 将 Karpenter 与其他 Kubernetes 工具集成
- 开发高级节点生命周期管理策略

## 参考资料

- [Karpenter 官方文档](https://karpenter.sh/)
- [Karpenter AWS Provider Repository](https://github.com/aws/karpenter-provider-aws)
- [Amazon EKS Workshop - Karpenter](https://www.eksworkshop.com/docs/autoscaling/compute/karpenter/)
- [AWS Blog - Karpenter](https://aws.amazon.com/blogs/aws/introducing-karpenter-an-open-source-high-performance-kubernetes-cluster-autoscaler/)
- [Karpenter Best Practices](https://aws.github.io/aws-eks-best-practices/karpenter/)
- [Karpenter GitHub Releases](https://github.com/aws/karpenter-provider-aws/releases)
- [AWS What's New - Karpenter ARC Zonal Shift Support](https://aws.amazon.com/about-aws/whats-new/2026/05/karpenter-arc-zonal-shift/)
- [AWS What's New - Amazon EKS Managed Node Group Warm Pool Support](https://aws.amazon.com/about-aws/whats-new/2026/04/amazon-eks-managed-node-groups-ec2-warm-pools/)

## 测验

要测试您在本章中学到的内容，请尝试[主题测验](../quizzes/autoscaling/06-karpenter-quiz.md)。

本次修订已验证的主要参考资料：[Compatibility](https://karpenter.sh/v1.14/upgrading/compatibility/)、[NodePool](https://karpenter.sh/v1.14/concepts/nodepools/)、[EC2NodeClass](https://karpenter.sh/v1.14/concepts/nodeclasses/)、[Disruption](https://karpenter.sh/v1.14/concepts/disruption/)、[Support policy](https://github.com/aws/karpenter-provider-aws/blob/main/SUPPORT.md)、[Pinned Helm values](https://github.com/aws/karpenter-provider-aws/blob/v1.14.1/charts/karpenter/values.yaml)、[Readiness taints](https://github.com/kubernetes-sigs/karpenter/commit/05431485c90c76a3a662b678a46c1a8da330038d)、[Pinned DRA option](https://github.com/kubernetes-sigs/karpenter/blob/6e7eab7a0f48/pkg/operator/options/options.go)、[EKS node IAM](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html)、[Fargate profiles](https://docs.aws.amazon.com/eks/latest/userguide/fargate-profile.html)。
