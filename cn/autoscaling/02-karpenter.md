# Karpenter

> **支持的版本**：Karpenter 1.14 LTS（示例：1.14.1）；请根据兼容性表和提供商支持表选择 Kubernetes/EKS 版本。
> **最后更新**：2026年10月26日

## 目录
- [简介](#introduction)
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

## 简介

Karpenter 是一个开源节点自动伸缩器。本章使用其 AWS 提供商，为兼容的 Kubernetes 工作负载预置 EC2 容量。可用性和效率取决于约束条件、云容量、节点初始化以及应用设计。

### Karpenter 的主要优势

1. **响应迅速的扩缩容**：在工作负载因无法调度而提出需求时开始预置；节点和应用就绪时间没有固定的延迟保证。
2. **成本优化**：为工作负载选择最合适的实例类型
3. **配置简单**：通过声明式 API 轻松配置
4. **以工作负载为中心的设计**：根据 Pod 要求预置节点
5. **云集成**：利用云提供商的能力
6. **高效装箱**：优化资源利用率
7. **灵活的节点管理**：管理节点生命周期并集成中断处理

### 与现有自动伸缩器的比较

| 功能 | Karpenter | Cluster Autoscaler | 云提供商托管节点组 |
|---------|-----------|-------------------|---------------------------|
| 扩缩容速度 | 取决于调度、EC2 容量和初始化 | 取决于节点组扩缩容和初始化 | 取决于扩缩容策略、容量和初始化 |
| 实例类型选择 | 动态 | 基于节点组 | 基于节点组 |
| 装箱效率 | 取决于工作负载/约束条件 | 取决于工作负载/节点组 | 取决于调度器和扩缩容控制器 |
| 配置复杂度 | 低 | 中 | 低 |
| 云集成 | 提供商特定实现 | 多种云提供商集成 | 云提供商原生 |
| 节点组管理 | 不需要 | 需要 | 需要 |
| 中断处理 | 已配置的事件处理和节点生命周期管理 | 取决于平台/集成方式 | 平台特定处理 |

> **注意**：EKS 于2026年4月8日为托管节点组添加了暖池支持。预初始化实例可以减少重复的初始化工作；Stopped 和 Running 模式的转换时间和成本不同，缩容时是否复用实例为可选项。根据 AWS 的说明，Cluster Autoscaler 集成无需额外配置。恢复实例、节点就绪和应用启动仍需要时间。这是 EKS 托管节点组/Auto Scaling 功能，并非由 Karpenter 管理的池。

## 架构

Karpenter 作为 Kubernetes 控制器运行，检测无法调度的 Pod 并预置合适的节点。

![架构图：Kubernetes 集群中的 Karpenter 控制器监视无法调度的 Pod，使用经 CEL 验证的 NodePool 和 EC2NodeClass CRD，并调用 Kubernetes API 和云提供商的 Instance API 来预置计算实例。](../.gitbook/assets/en-autoscaling-02-karpenter-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-02-karpenter-0.html)

### Karpenter 工作流

下图展示了 Karpenter 在 EKS 集群中的工作方式：

![时序图：无法调度的 Pod 经由 Kubernetes API 到达 Karpenter 控制器；Karpenter 查询 AWS EC2 API 并请求创建节点；新节点注册后，Pod 最终被调度。](../.gitbook/assets/en-autoscaling-02-karpenter-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-02-karpenter-1.html)

### 主要组件

1. **Karpenter 控制器**：模拟调度需求、创建 NodeClaims 并管理节点生命周期；实际的 Pod 绑定由 Kubernetes 的调度器执行。
2. **CRD CEL 验证**：NodePool 和 EC2NodeClass 由 CRD 中的 CEL 规则验证（在 Karpenter 1.1 中，准入/转换 Webhook 已移除）
3. **NodePool 和 NodeClaim CRD**：NodePool 定义策略；NodeClaim 记录单个预置节点的要求和生命周期。
4. **EC2NodeClass CRD**：定义待预置节点的配置
5. **云提供商集成**：与云提供商 API 集成，以管理计算资源

### 工作原理

1. Karpenter 控制器检测无法调度的 Pod
2. 分析 Pod 的要求（资源、节点选择器、容忍度等）
3. 根据 NodePool 和 EC2NodeClass 配置确定合适的节点类型
4. 调用云提供商 API 预置节点
5. 节点注册并就绪后，Kubernetes 调度器即可绑定符合条件的 Pod。Karpenter 不会取代 kube-scheduler。
6. 整合、漂移、过期、手动删除和云中断各有不同的触发条件和保护措施；它们并非全部都是 SQS 中断事件。

## 安装和配置

未包含 apiVersion/kind 的 YAML 代码块是针对所讨论的 NodePool 或 EC2NodeClass spec 的配置片段；它们不是可以独立通过 kubectl apply 应用的文档。

以下是针对现有集群的独立学习示例，并非可直接用于生产的部署套件。重复出现的对象名称表示不同的备选方案。安装前，请准备并验证 IAM/OIDC、节点访问权限、经批准的子网/安全组、引导容量和中断队列。所有 YAML 都使用 `my-cluster` 等字面示例名称；kubectl 不会在已保存的 YAML 文件中展开 `${CLUSTER_NAME}`。本次审查未预置 AWS 资源、安装 Karpenter 或测量扩缩容情况。如果对应版本已存在，首次安装命令会失败；现有安装必须遵循带版本的升级/CRD 迁移指南。

### 先决条件

- 使用平台和 Karpenter 兼容矩阵支持的 Kubernetes 版本。已发布的兼容矩阵列出：Kubernetes 1.34 至少需要 Karpenter 1.6，1.35 至少需要 1.9，1.36 至少需要 1.13；这些最低版本并不意味着所有更早的 Karpenter 次要版本仍受维护。v1.14 兼容矩阵未包含 1.37，而 v1.15 兼容矩阵要求 Kubernetes 1.37 使用 Karpenter 1.15.x。EKS 版本的可用性/支持情况需另行确认。
- 已配置 kubectl
- 云提供商凭证和权限
- Helm（可选）

### 在 AWS EKS 上安装

#### 1. IAM 角色和策略设置

这些命令假定控制器角色和节点角色已经存在，并且 EKS 使用基于 API 的身份验证（API 或 API_AND_CONFIG_MAP）。仅使用 CONFIG_MAP 的集群应检查现有 aws-auth 节点映射，而不是使用 list-access-entries；不要把更改身份验证模式作为顺带的设置步骤。节点角色信任 EC2，并需要工作节点/ECR 拉取权限（例如 AmazonEKSWorkerNodePolicy 和 AmazonEC2ContainerRegistryPullOnly）。在支持的情况下，为 VPC CNI 配置独立身份；SSM 权限为可选项，且需要已配置的代理。AmazonEKSClusterPolicy 不能替代 Karpenter 控制器策略。

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

在准备好所引用的队列和引导容量后，仅执行一次首次安装示例。若要升级，请先查看带版本的迁移指南，并更新相应的 CRD（例如通过单独管理的 karpenter-crd chart）；单独升级控制器 chart 通常不会升级 CRD。迁移现有 CRD 安装前，请先验证资源所有权。

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

默认两个控制器副本的示例输出（并非本次审查期间捕获的实际执行结果）：
```
NAME                         READY   STATUS    RESTARTS   AGE
karpenter-<hash>-<id-1>      1/1     Running   0          1m
karpenter-<hash>-<id-2>      1/1     Running   0          1m
```

### 基本 NodePool 和 EC2NodeClass 配置

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

NodePool 是一种 Kubernetes 自定义资源，用于定义 Karpenter 如何预置节点。它取代了旧版 Provisioner。

### 基本 NodePool 配置

下面的特殊污点有意要求工作负载配置匹配的容忍度。只有在已有经过验证的初始化器会移除所配置的污点后，才应配置 startupTaints；如果没有对应的控制器却随意添加启动污点，节点可能无法使用。此处的限制、初始化和中断示例是不同的备选方案，并非要叠加应用到正在运行的生产 NodePool 中的变更。

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

各项要求之间、与 EC2NodeClass 之间以及与 Pod 约束之间都会取交集。只有在符合条件的实例类型、AMI 和容器镜像都支持 amd64 与 arm64 时，允许这两种架构才有帮助。列出符合条件的可用区/容量类型，并不能保证均匀分配；如需实现这一点，请使用工作负载拓扑约束。

要求定义了 Karpenter 将要预置的节点特征：

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

`spec.limits` 限制预置资源的总量，但并行预置使用最终一致性检查，因此可能暂时超出限制。它不是严格的账单上限。使用字符串形式的数量可避免 API/GitOps 类型差异。

```yaml
limits:
  cpu: '1000'
  memory: 1000Gi
  nvidia.com/gpu: '10'
```

### 实验性的 DRA 分配跟踪（v1.13）

Karpenter 核心 v1.13 添加了 DRA 设备分配跟踪。这并不代表生产环境中的 DRA 预置已得到全面保证：AWS 1.14.1 chart 默认设置 `settings.ignoreDRARequests: true`，且上游将正式 DRA 支持标记为尚未达到 GA。Kubernetes 最低版本为 1.29，并不足以证明兼容性。请验证确切的 Kubernetes 资源 API、DRA 驱动程序、ResourceClaims/ResourceSlices 和 Karpenter 配置；不要将 DRA 声明视为可与下方设备插件扩展资源示例互换。

### 节点过期配置

`expireAfter` 定义了因过期而开始清空节点的时间，并不保证替换节点何时完成就绪。下方可选的 `terminationGracePeriod` 会限制清空时长，但可能强制删除剩余 Pod，包括被 PDB 阻止驱逐的 Pod。只有在验证应用关闭和恢复要求后，才选择该期限。

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

Karpenter 核心 v1.13 在对尚未初始化的受管节点进行调度模拟时，会将独立的 NodeReadinessController 的 `readiness.k8s.io/` 污点视为临时污点。它仍会等待这些污点消失后才将初始化标记为完成；它不会删除这些污点，也不会让 Kubernetes 调度器绕过它们。其他初始化器的污点仍需要正确配置 `startupTaints`，并由相应控制器移除。

### 2026年7月更新：v1.14 发布

Karpenter v1.14 于2026年7月11日发布，新增内容包括：

- **支持 CapacityBuffers API**：提供 alpha 版容量缓冲区集成；`CapacityBuffer` 默认禁用，需要匹配的 CRD/控制器配置。预留余量并非免费容量，也不构成延迟保证。
- **支持预览版实例类型**：能够识别符合条件的预览版实例；实际预置仍需要账户/区域访问权限，并且取决于实际可用情况。
- **支持 Nitro Enclaves**：当 NodeClaim 资源请求包含 `eks.amazonaws.com/nip-slots` 时，提供商会在生成的启动模板中设置 `EnclaveOptions.Enabled`。仍需使用兼容的实例、AMI 和设备插件配置；1.14.1 中没有 `EC2NodeClass.spec.enclaveOptions` 字段。
- Bug 修复：核算辅助 ENI 上的主 IP、确保 Zonal Shift 缓存已填充、将 AWS SDK 客户端超时接入 Operator 配置等

详情请参阅 [v1.14.0 发布说明](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.14.0)。

2026年7月17日，较旧分支收到了补丁，包括 1.3.8 和 1.11.3。这些历史回移补丁并不能证明所有介于其间的次要版本仍受支持。当前支持策略列出：LTS 1.9 支持至2027年2月，LTS 1.14 支持至2027年7月；常规次要版本仅支持到下一个次要版本发布。请选择受支持的版本线并遵循其迁移指南，不要假定旧版本线仍在维护。

AWS 于2026年7月22日宣布，Karpenter/EKS Auto Mode 新增了 EFA 网络接口和置放群组配置。在 AWS Karpenter 1.14.1 中，具体字段为 `EC2NodeClass.spec.networkInterfaces` 和 `spec.placementGroupSelector`（不是 NodePool 字段）。仅使用 EFA 的接口不占用 VPC IP 地址，但仍必须在设备/卡索引 0 处配置主 `interface`。按名称或 ID 选择现有置放群组；其集群/分散/分区策略和支持的实例会限制置放。此处的示例并未配置或验证 HPC 工作负载。

### 2026年8月更新：v1.14.1 补丁版本发布

[v1.14.1](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.14.1) 是 v1.14 版本线上的首个补丁，于2026年8月21日发布。这是一个维护版本，升级了上游 `sigs.k8s.io/karpenter` 版本，并回移了自 v1.14.0 以来的修复。

### 2026年10月更新：v1.15.0 常规版本发布

[v1.15.0](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.15.0) 是一个常规（非 LTS）次要版本，于2026年10月10日发布。主要变更：

- **节点修复改为自愿中断**：节点修复被纳入中断机制；当受容量约束的 NodePool 无法先安排替换节点时，会先终止节点再进行修复。新增通过 `ec2:RebootInstances` 重启的修复操作（受 `RebootForRepair` AWS 功能门控控制），旧版修复控制器仍可通过 `--legacy-node-repair` 标志使用。
- **KubeletConfiguration 支持 CEL**：`maxPodsExpression`、`kubeReserved` 和 `systemReserved` 可接受 CEL 表达式，并扩展了 EC2NodeClass 的 KubeletConfiguration 字段。
- **扩大 DRA 支持范围**：支持优先级备选项，以及 NVIDIA 和 EFA 驱动程序的 DRA 支持。
- 其他变更：新增 `--aws-feature-gates` 标志、默认 Pod 拓扑分布感知、在预置期间核算实例类型的卷限制、新增 `karpenter_pods_disrupted_total` 等中断指标，以及受功能门控控制的 Pod 删除成本管理控制器。

根据支持策略，常规次要版本仅支持到下一个次要版本发布，因此 v1.15.0 发布后，v1.14 仅作为 LTS 版本线继续维护（至2027年7月）；因此本章示例继续使用 1.14 LTS（1.14.1）。Kubernetes 1.37 需要 Karpenter 1.15.x；如果需要 Kubernetes 1.37 或计划迁移到 1.15，请先查看 [v1.15 兼容矩阵](https://karpenter.sh/v1.15/upgrading/compatibility/) 和升级指南。详情请参阅 [v1.15.0 发布说明](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.15.0)。

### 2026年10月更新：v1.15.1 和 LTS 补丁版本发布

2026年10月20日至23日，受支持的版本线均发布了补丁：[v1.15.1](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.15.1)（1.15 版本线的首个补丁——修复内容包括：当所有兼容的容量预留都已满时，放宽偏好而不是延后处理；以及创建后标签同步时将节点修复加入队列）、1.14 LTS 版本线上的 [v1.14.2](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.14.2) 和 [v1.14.3](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.14.3)（包括将 `SpotMaxPriceTooLow` 归类为 ICE 错误，以及将正在回收的可中断容量预留视为不可用容量），还有 1.9 LTS 版本线上的 [v1.9.3](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.9.3)。这三条版本线均将 Go 工具链升级到 1.26.10；该 Go 补丁版本停止信任已遭入侵的 eMudhra 中间 CA 证书（CVE-2026-111943）。

## 节点类

节点类定义 Karpenter 预置节点时使用的配置。在 AWS 上，它使用 EC2NodeClass CRD。

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

子网和安全组通过选择器项选择（多个项之间为 OR 关系；单个项内的标签之间为 AND 关系）：

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

Karpenter 通过 `amiSelectorTerms` 选择 AMI。别名用于选择系列/版本；**`@latest` 不是固定版本**，可能会更改解析出的 AMI 并触发漂移。带有 `@latest` 的示例仅用于学习。生产环境中，请在发布前解析并测试明确指定的受支持 AMI 版本（使用实际发布日期，例如 `al2023@vYYYYMMDD`），或使用经过批准的 AMI ID。Kubernetes 1.33 及更高版本不再发布 AL2 EKS AMI。以下变体互为备选；Custom AMI 需要正确配置引导、注册污点、kubelet、CNI/运行时和身份。

```yaml
# Amazon Linux 2023
amiSelectorTerms:
  - alias: al2023@latest
---
# Bottlerocket
amiSelectorTerms:
  - alias: bottlerocket@latest
---
# Custom AMI (by ID): amiFamily is required when no alias term is used
amiFamily: Custom
amiSelectorTerms:
  - id: "ami-0123456789abcdef0"
# Ubuntu: no v1 alias; use amiFamily: Custom with an id/tags/name term
```

### 块设备配置

设备映射因 AMI 系列而异。以下 AL2023 示例将 /dev/xvda 用作根设备；其他 AMI 请检查实际布局。额外卷需要明确的文件系统/挂载或应用存储规划。使用客户自主管理的 KMS 密钥时，还需要相应的密钥/IAM 权限。

可以为节点定义存储配置：

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

这些 shell 用户数据片段假设使用 AL2023；Karpenter 会将生成的 bootstrap/nodeadm 配置与自定义数据合并。它们不适用于通用的 Bottlerocket/Windows 引导。与其在每次启动时不受限制地更新软件包，不如在 AMI 中预装并测试软件包。若未配置 CloudWatch Agent 所需的配置、IAM 权限和网络路径，仅安装/启动 Agent 并不能证明遥测数据已成功收集。

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

### 节点整合流程

下图展示 Karpenter 的节点整合流程。此功能对于提升集群效率和降低成本非常重要：

![整合概念示意：模拟工作负载是否能放到现有或替换容量上；让所需的替换容量就绪；然后驱逐并重新创建 Pod，再终止符合条件的旧节点。这不是实时 Pod 迁移，也不保证实现三换一的结果。](../.gitbook/assets/en-autoscaling-02-karpenter-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-02-karpenter-2.html)

## 中断处理

已配置的中断处理会尝试在容量丢失前作出响应。最终结果取决于通知、替换容量、关机期限和应用恢复情况；不能保证服务始终不中断。

### 集成的中断处理

云中断处理不同于整合/过期处理。它涵盖以下信号：

1. **Spot 中断警告**：尽可能开始清空节点并请求替换容量；通知时间窗口不等于有保证的恢复 SLA。
2. **计划的运行状况/维护事件**：对受影响的实例作出响应。
3. **实例停止/终止事件**：协调正在退出服务的容量。
4. **EC2 实例状态故障**：使用所需的 EC2 API 权限检查运行状况。Rebalance 建议本身仅作为事件发布，不会自动触发污点设置/清空/终止操作。

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

### 清空配置

Karpenter 通常在优雅清空期间使用驱逐。Helm 设置用于配置控制器；NodePool 中断预算限制自愿整合/漂移的开始次数，但不限制所有同时发生的节点丢失。30% 的预算会向上取整，然后减去正在删除/未就绪的节点；它不是严格的 30% 上限。过期、中断和修复可能采用不同的强制处理方式。启用 `interruptionQueue` 前，请先配置指定的 SQS 队列、EventBridge 规则/目标、队列策略和控制器权限；单独设置 Helm 字段并不会创建这些资源。

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

### PDB（PodDisruptionBudget）集成

PDB 会根据健康副本限制自愿驱逐；它不会创建副本，也不保证应用可用性。下面的 `minAvailable: 2` 表示驱逐前需要有足够数量的匹配 Pod 处于健康状态。实例丢失和强制终止期限仍可能中断这些 Pod。

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

Karpenter 在预置节点时会考虑 Pod 拓扑分布约束：

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
        image: nginx:1.30.6
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

Karpenter 会考虑 Pod 亲和性和反亲和性规则：

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
        image: nginx:1.30.6
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

GPU 示例需要兼容的加速型 AMI、NVIDIA 驱动程序和能容忍 GPU 污点并公布 nvidia.com/gpu 的设备插件 DaemonSet。BusyBox Pod 仅用于演示 GPU 预留；它不会运行或测试 CUDA。请使用真实的 GPU 应用镜像另行验证。

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
        image: busybox:1.38.0
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

Karpenter 支持使用 EC2 Spot 实例来优化成本：

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

role 和 instanceProfile 不能同时使用。使用 role 时，Karpenter 会管理实例配置文件，因此需要相应的 IAM API 权限/网络连通性。如果集群无法连接 IAM 端点，请使用预先配置好的 instanceProfile；IAM 没有 PrivateLink 端点。控制器仍需要针对其节点角色的 PassRole 权限，而且拥有 EC2 凭证并不等同于拥有 EKS 节点访问权限。

Karpenter 使用 EC2 实例配置文件向节点授予 IAM 权限：

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

#### 3. 替代启动模板（EC2NodeClass）

Karpenter v1 不接受用户提供的 EC2 启动模板（旧版 `launchTemplate` 字段已移除）。Karpenter 会根据 EC2NodeClass 自行生成并管理启动模板，因此，原本需要在启动模板中设置的内容应直接在 EC2NodeClass 中配置：

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

在配置好身份、网络、节点访问和引导后，Karpenter 的 AWS 提供商可以与 EKS 管理的计算资源并行预置 EC2 容量。

![架构图：Amazon EKS 集群中的 Karpenter 控制器承担 IAM 角色，直接调用 EC2 API，绕过 Auto Scaling Groups 和 Managed Node Groups 来创建 EC2 实例。](../.gitbook/assets/en-autoscaling-02-karpenter-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-02-karpenter-3.html)

### 准备 EKS 集群

请一致地替换所有示例名称。仅选择适合工作节点的子网/安全组；为所有控制平面子网打标签并非安全的资源发现策略。允许节点启动前，请验证子网路由、安全规则、CNI IP 容量以及所需的私有端点。

#### 1. 集群标签设置

让基础设施配置只为经过批准的工作节点子网和安全组添加标签。VPC 上的标签不会决定选择哪些资源。发现标签的值必须与示例相符（此处为 `my-cluster`）；仅凭标签并不能证明私有路由、安全规则合适或可用地址充足。在应用 NodePool 前，请检查实际资源和路由。

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

请使用下方带版本的控制器策略和基础设施参考，而不是前面不完整的手写全放行策略。控制器凭证（此处为 IRSA）与节点凭证以及 VPC CNI/工作负载身份相互独立。控制器信任策略必须匹配集群 OIDC 提供商、`system:serviceaccount:karpenter:karpenter` 和 `aud: sts.amazonaws.com`；仅授予此版本和所选功能所需的操作/资源/条件。节点角色必须获准加入 EKS；启用基于 API 的身份验证时，通常通过 `EC2_LINUX` 访问条目实现。检查命令不会创建 IAM 角色或访问条目。

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

### 与 EKS 托管节点组配合使用

Karpenter 可以与 EKS 托管节点组共存。以下 NodePool 会预置独立的 EC2 节点；它不会管理托管节点组。请让控制器运行在可靠的引导容量上（默认 chart 会排除 Karpenter 节点，并要求两个副本位于不同主机上）。

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

### 与 EKS Fargate 配合使用

Fargate 不实现 Kubernetes topologySpreadConstraints，Kubernetes 亲和性/反亲和性规则也不适用于 Fargate。不要假设默认 chart 的 EC2 置放约束可以确保 Fargate 跨可用区分布；应单独设计并验证配置文件/子网置放。

经过严格筛选的 Fargate 配置文件可以运行控制器 Pod，而 Karpenter 负责预置 EC2 工作节点。Karpenter 不会创建 Fargate 容量，也不会管理其配置文件。请准备只选择 `karpenter` 命名空间和控制器标签的配置文件，而不是选择整个 `default`/`kube-system`；JSON 选择器结构为 `[{"namespace":"karpenter","labels":{"app.kubernetes.io/name":"karpenter"}}]`。配置文件需要自己的 Pod 执行角色/私有子网，控制器 AWS 权限仍需通过 IRSA 配置（EKS Pod Identity 不支持在 Fargate 上使用）。以下命令仅检查现有配置文件。

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

### 可用区故障响应：与 Amazon ARC Zonal Shift 集成（2026年5月）

Karpenter 可以与已启用的 EKS ARC 可用区转移资源集成。手动可用区转移或已配置的自动转移生效后，Karpenter 会避免在被转移的可用区中增加新容量。这并不代表它能独立检测所有可用区故障，也不会覆盖将工作负载固定在该可用区的 Pod/PV 要求。

转移生效期间，被转移可用区中的自愿中断会暂停；如果健康可用区中的中断需要将 Pod 移动到该可用区，也会被阻止。这并不意味着健康可用区中的所有自愿中断都会无条件暂停。请配置 EKS/ARC 先决条件、`eks:DescribeCluster`/ARC 权限以及 `settings.enableZonalShift: true`（环境变量选项 `ENABLE_ZONAL_SHIFT`）；自动转移还需要单独启用并配置相应演练。无需自定义 ARC CRD，转移结束后操作会恢复。

### 优化 EKS 成本

你可以使用 Karpenter 优化 EKS 集群的成本：

![概念性对比：节点组扩缩容与 Karpenter 的动态容量选择、整合和 Spot 选项。此图不代表已测量或普遍适用的扩缩容速度或节省成本排名。](../.gitbook/assets/en-autoscaling-02-karpenter-4.png)

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

#### 2. 使用多种实例类型

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

![四组并列的 Karpenter 最佳实践清单，分类为性能优化、成本优化、可用性提升和安全加固。](../.gitbook/assets/en-autoscaling-02-karpenter-5.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-02-karpenter-5.html)

### 性能优化

1. **选择合适的实例类型**：选择适合工作负载的实例类型
2. **允许多种实例类型**：允许使用多种实例类型，以提高可用性并优化成本
3. **设置合适的 TTL**：设置与工作负载模式相符的 TTL
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

1. **利用 Spot 实例**：使用 Spot 实例以节省成本
2. **选择合适的实例规格**：选择适合工作负载的实例规格
3. **评估空节点移除**：符合条件的工作节点 NodePool 可以缩减至零；控制器/引导计算容量及集群其他无关成本仍会保留。
4. **规划节点刷新**：过期机制会根据当前约束轮换符合条件的容量；它不会自动选择更新的实例类型，也不会修补固定版本的 AMI。

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

### 提升可用性

1. **使用多个可用区**：在多个可用区中部署节点
2. **混用按需实例和 Spot 实例**：平衡可用性与成本
3. **设置合适的 PDB**：在实际健康副本数限制范围内保护 Pod 免遭自愿驱逐，同时做好冗余和恢复设计。
4. **配置并测试中断处理**：验证通知路径、关机期限和替换容量，不要假设服务可以始终不中断。

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

**症状**：Pod 一直处于 Pending 状态，且没有预置节点

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

**症状**：节点没有按预期移除

**解决方案**：
- 检查 TTL 设置
- 验证节点整合设置
- 检查 Pod 清空状态

```bash
# Check node status
kubectl describe node <name>

# Check node labels
kubectl get node <name> --show-labels

# Check Karpenter logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller --since=30m
```

#### 3. 实例类型选择问题

**症状**：预置了意料之外的实例类型

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

Karpenter 会根据工作负载和基础设施约束自动完成节点预置和生命周期管理。它可以改善容量管理，但可用性、性能和成本方面的结果仍需针对具体工作负载进行验证。

本文介绍了 Karpenter 的基本概念、安装方法、NodePool 和 EC2NodeClass 配置、中断处理、各种集成、与 Amazon EKS 的集成、最佳实践以及故障排除。

使用 Karpenter 可以简化集群管理、优化资源利用率并降低成本。尤其是在 Amazon EKS 等云托管 Kubernetes 环境中，你可以充分发挥 Karpenter 的优势。

### 后续步骤

- 使用 Karpenter 实施成本优化策略
- 为各种工作负载类型配置 NodePool
- 设计混合集群架构
- 将 Karpenter 与其他 Kubernetes 工具集成
- 制定高级节点生命周期管理策略

## 参考资料

- [Karpenter 官方文档](https://karpenter.sh/)
- [Karpenter AWS 提供商代码库](https://github.com/aws/karpenter-provider-aws)
- [Amazon EKS Workshop - Karpenter](https://www.eksworkshop.com/docs/autoscaling/compute/karpenter/)
- [AWS 博客 - Karpenter](https://aws.amazon.com/blogs/aws/introducing-karpenter-an-open-source-high-performance-kubernetes-cluster-autoscaler/)
- [Karpenter 最佳实践](https://aws.github.io/aws-eks-best-practices/karpenter/)
- [Karpenter GitHub 发布版本](https://github.com/aws/karpenter-provider-aws/releases)
- [AWS 最新消息 - Karpenter 支持 ARC Zonal Shift](https://aws.amazon.com/about-aws/whats-new/2026/05/karpenter-arc-zonal-shift/)
- [AWS 最新消息 - Amazon EKS 托管节点组支持暖池](https://aws.amazon.com/about-aws/whats-new/2026/04/amazon-eks-managed-node-groups-ec2-warm-pools/)

## 测验

要检验你对本章内容的掌握情况，请尝试[主题测验](../quizzes/autoscaling/06-karpenter-quiz.md)。

本次修订已核实的主要参考资料：[兼容性](https://karpenter.sh/v1.14/upgrading/compatibility/)、[NodePool](https://karpenter.sh/v1.14/concepts/nodepools/)、[EC2NodeClass](https://karpenter.sh/v1.14/concepts/nodeclasses/)、[中断处理](https://karpenter.sh/v1.14/concepts/disruption/)、[支持策略](https://github.com/aws/karpenter-provider-aws/blob/main/SUPPORT.md)、[固定版本的 Helm values](https://github.com/aws/karpenter-provider-aws/blob/v1.14.1/charts/karpenter/values.yaml)、[就绪污点](https://github.com/kubernetes-sigs/karpenter/commit/05431485c90c76a3a662b678a46c1a8da330038d)、[固定版本的 DRA 选项](https://github.com/kubernetes-sigs/karpenter/blob/6e7eab7a0f48/pkg/operator/options/options.go)、[EKS 节点 IAM](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html)、[Fargate 配置文件](https://docs.aws.amazon.com/eks/latest/userguide/fargate-profile.html)。
