# EKS 集群创建测验 - 第 4 部分

> **最后更新**：2026年10月12日

本测验将 Terraform 集群指南与扩缩容、身份和生命周期操作联系起来。最后一部分检查 Terraform 特定概念。示例需要经过审核的账户/Region/kubeconfig、IAM 和网络前提条件；本次审计期间并未部署这些示例。

## 基础概念问题

1. Cluster Autoscaler 和 Karpenter 在预置资源方面的主要区别是什么？
   * A) CA 是 AWS 托管服务
   * B) CA 扩缩现有组；Karpenter 预置选定的独立容量
   * C) CA 只测量 CPU，而 Karpenter 只测量 Pod 数量
   * D) Karpenter 取代 Kubernetes 调度器

<details>
<summary>显示答案</summary>

**答案：B) CA 扩缩现有组；Karpenter 预置选定的独立容量**

Cluster Autoscaler 会调整已发现的预定义节点组/ASG 的大小。Karpenter 会创建 NodeClaims 和由 NodePools 与 EC2NodeClasses 选择的 EC2 容量。Kubernetes 负责调度 Pod；Karpenter 不会取代 Kubernetes 调度器。

两者都会考虑无法调度的工作负载请求和放置约束。它们都不是简单的“CPU 百分比与 Pod 数量”之分，也都不会就地调整正在运行的 EC2 实例大小。Karpenter 可以用不同规格的实例替换现有容量；VPA 则单独管理 Pod 资源请求。

**Cluster Autoscaler 示例：** 对于 EKS 1.36，请使用匹配的小版本，并使用经过审核的 IAM 和发现标签配置专用 ServiceAccount。Chart 9.59.0 需要显式指定 v1.36.1 镜像覆盖值。安装前先渲染 RBAC、镜像和参数：

```bash
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update autoscaler
helm template cluster-autoscaler autoscaler/cluster-autoscaler \
  --version 9.59.0 --namespace kube-system \
  --set-string autoDiscovery.clusterName="${EXAMPLE_CLUSTER:?}" \
  --set-string awsRegion="${EXAMPLE_REGION:?}" \
  --set-string image.tag=v1.36.1 \
  --set rbac.serviceAccount.create=false \
  --set-string rbac.serviceAccount.name=cluster-autoscaler \
  > cluster-autoscaler-reviewed.yaml
```
除非经过审核的工作负载/数据策略另有要求，否则请保留本地存储和系统 Pod 保护措施。由 CA 管理的同一组中，混合实例类型应具有相近的 CPU/内存/GPU 规格。

**Karpenter 示例：** 单独安装兼容的控制器/CRD，并配置其 IAM、节点授权、发现标签、中断处理和容量限制。将两个 AMI 占位值替换为经过审核且与集群版本和各架构匹配的 AL2023 镜像。如果允许两种架构，工作负载镜像必须支持这两种架构：

```yaml
# Karpenter NodePool (karpenter.sh/v1) + EC2NodeClass (karpenter.k8s.aws/v1)
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
          values: ["spot", "on-demand"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["m5.large", "m5a.large", "m5d.large", "m5ad.large", "m6g.large"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  role: KarpenterNodeRole-my-cluster
  amiFamily: AL2023
  amiSelectorTerms:
    - id: ami-REPLACE_WITH_REVIEWED_AMD64_IMAGE
    - id: ami-REPLACE_WITH_REVIEWED_ARM64_IMAGE
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
```
| 对比项 | Cluster Autoscaler | Karpenter |
| --- | --- | --- |
| 扩缩单位 | 现有节点组/ASG 容量 | NodeClaims 和选定的 EC2 容量 |
| 配置 | 组、发现、IAM 和控制器 | NodePools、EC2NodeClasses、IAM 和控制器 |
| 移除 | 需要调度和中断检查 | 受整合、预算和中断控制措施约束 |
| 原指南中的历史时间说法 | 2–10 分钟，未经验证 | 少于 1 分钟，未经验证 |

原有的时间数字保留为**未经验证的历史说法**，并非本次审计复现的基准测试，也不保证反映当前性能。节点启动、镜像、配额和工作负载约束都会影响这两种工具。不要根据该表推断普遍适用的成本、简易性或延迟排名。

</details>

2. 当前 EKS CreateNodegroup API 中有哪些容量类型？
   * A) Reserved、On-Demand、Spot
   * B) On-Demand、Spot、Dedicated
   * C) ON_DEMAND、SPOT、CAPACITY_BLOCK
   * D) Standard、Burstable、Compute-Optimized

<details>
<summary>显示答案</summary>

**答案：C) ON_DEMAND、SPOT、CAPACITY_BLOCK**

当前 EKS CreateNodegroup API 包含 **ON_DEMAND、SPOT 和 CAPACITY_BLOCK**。托管节点组使用一种容量类型；不同容量池应使用不同的节点组。

On-Demand 可避免 Spot 回收，但不保证不会中断，也不保证可用性。Spot 使用闲置容量，适用于可容忍中断的工作负载；宣传的折扣不保证一定能节省成本。Reserved Instances/Savings Plans 是计费安排，并非额外的 CreateNodegroup 枚举值。

Capacity Blocks 是针对受支持实例/Region 的独立限时预留工作流。它们需要指向预留容量的自定义启动模板、匹配的 AZ/子网以及了解预留情况的扩缩策略。EKS 会在预留结束前 40 分钟创建一个计划缩容操作；请勿修改/删除该操作。以下示例是常规的 On-Demand/Spot 替代方案，不是 Capacity Block 预置方式。

**AWS CLI：** 使用尚未使用的节点组名称、现有私有子网和获批的 EC2 节点角色（包括所需的 CNI 身份路径）。等待节点组激活，然后验证实际的 Node/工作负载就绪情况：

```bash
set -euo pipefail
aws eks create-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --scaling-config minSize=3,maxSize=10,desiredSize=5 \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --instance-types t3.medium t3a.medium --capacity-type SPOT \
  --ami-type AL2023_x86_64_STANDARD --node-role "${NODE_ROLE_ARN:?}"
aws eks wait nodegroup-active --cluster-name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --nodegroup-name "$NEW_NODEGROUP_NAME"
```
**eksctl 替代方案：** 为现有集群和未使用的组名称保存配置，然后运行 `eksctl create nodegroup -f nodegroups.yaml`。使用 `managedNodeGroups` 和 `spot`，而不是原示例中不受支持的 `capacityType` 字段：

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: ng-on-demand
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  desiredCapacity: 3
  minSize: 2
  maxSize: 5
  spot: false
- name: ng-spot
  amiFamily: AmazonLinux2023
  instanceTypes: [m5.large, m5a.large]
  privateNetworking: true
  desiredCapacity: 2
  minSize: 0
  maxSize: 5
  spot: true
```
使用 affinity/selector 和 toleration 来放置适当的工作负载。托管节点组内置 Spot 再平衡/排空处理；Node Termination Handler 并非普遍必须额外配置的组件。PDB 无法阻止 EC2 回收 Spot 实例，也不是每个 Pod 都能获得完整的中断窗口。请规划检查点、备用容量和中断恢复。

</details>

3. 每个 Fargate profile selector 中哪个字段是必填项？
   * A) 实例类型
   * B) Namespace；labels 可选
   * C) 安全组 ID
   * D) Pod 数量上限

<details>
<summary>显示答案</summary>

**答案：B) Namespace；labels 可选**

每个 profile selector 都必须指定 **namespace**；labels 是可选项。profile 还需要名称和 Pod 执行角色，并使用符合条件的私有子网。它没有安全组参数。Pod 安全组是单独支持的策略机制，并非 Fargate profile 字段。

使用未占用的 profile 名称和经过审核的私有子网 ID。此 selector 仅针对应用 Pod，不会改变现有 CoreDNS 的放置方式：

```bash
set -euo pipefail
aws eks create-fargate-profile --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --fargate-profile-name "${NEW_FARGATE_PROFILE:?}" \
  --pod-execution-role-arn "${FARGATE_EXECUTION_ROLE_ARN:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --selectors '[{"namespace":"fargate-lab","labels":{"app":"nginx"}}]'
aws eks describe-fargate-profile --cluster-name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --fargate-profile-name "$NEW_FARGATE_PROFILE" \
  --query 'fargateProfile.{status:status,subnets:subnets,selectors:selectors}'
```
启动匹配的 Pod 前，先等待状态变为 `ACTIVE`。以下是另一种 eksctl profile 定义；创建前请验证集群的私有子网发现和执行角色配置：

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
fargateProfiles:
- name: fp-application
  selectors:
  - namespace: fargate-lab
    labels:
      app: nginx
```
namespace 和带标签的工作负载仍需单独创建。如果有多个 profile 匹配，EKS 会按 profile 名称的字母数字顺序选择，除非 Pod 使用 `eks.amazonaws.com/fargate-profile` 选择一个匹配的 profile。Profiles 不可变；替换/删除它们会影响其 Pod。

Pod 执行角色服务于 Fargate 基础设施，不用于应用访问 AWS。请使用兼容的工作负载身份机制，例如 IRSA；EKS Pod Identity 不支持 Fargate。将 CoreDNS 移至 Fargate 需要配置其计算方式并添加匹配的 profile，而不仅仅是在 selector 中添加 `kube-system`。

Fargate 按**预置容量**计费，该容量根据请求的资源加上开销/取整确定；它不会只按采样到的 CPU/内存使用量计费。请检查 `CapacityProvisioned`。EKS Fargate 不支持 Spot、DaemonSet、特权容器、host networking 或挂载 EBS 卷的工作负载。持久化 EFS 使用静态预置；仅匹配 profile 并不会创建文件系统/PV/PVC。请考虑 DNS、镜像拉取、STS 及其他必需的网络路径。

</details>

4. 哪一项不是 NodegroupUpdateConfig 字段？
   * A) maxUnavailable
   * B) maxUnavailablePercentage
   * C) updateStrategy
   * D) 节点组操作超时

<details>
<summary>显示答案</summary>

**答案：D) 节点组操作超时**

`NodegroupUpdateConfig` 支持整数 `maxUnavailable`、整数 `maxUnavailablePercentage` 和 `updateStrategy`（`DEFAULT` 或 `MINIMAL`）。设置数量或百分比，不能两者兼设。百分比不能作为 `maxUnavailable` 本身的有效值。

操作超时不是 NodegroupUpdateConfig 字段。`--force` 属于版本更新请求，可能绕过 Pod 驱逐保护；它不是存储的更新配置设置。CLI/IaC 等待超时也不同于服务操作。

```bash
set -euo pipefail
UPDATE_ID=$(aws eks update-nodegroup-config \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --update-config '{"maxUnavailable":2,"updateStrategy":"DEFAULT"}' \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$EXAMPLE_NODEGROUP" --update-id "$UPDATE_ID" \
  --query 'update.{status:status,errors:errors}'
```
若要使用百分比设置，请使用 `{"maxUnavailablePercentage":20,"updateStrategy":"DEFAULT"}`。跟踪返回的更新 ID，直到状态为 `Successful`，然后再启动版本更新。`DEFAULT` 会先启动替换容量；`MINIMAL` 会先终止选定的旧节点，以减少临时额外容量。

对于 `update-lab` 中经审核的三副本 Deployment，此 PDB 会约束自愿驱逐：

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: update-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
```
PDB 并不普遍保证可用性。直接删除、故障和工作负载控制器自身的滚动更新与驱逐各不相同。请检查备用容量、就绪状态和卷。不要承诺已经运行的 EKS 更新可以简单暂停或回滚；应停止后续计划变更，并按照适用的恢复流程操作。

</details>

5. 常规 EKS 版本工作流支持哪种控制平面升级步骤？
   * A) 跨过两个小版本直接升级
   * B) 跳转到任意上游版本
   * C) 完成就绪检查后升级到下一个受 EKS 支持的小版本
   * D) 先将节点升级到高于控制平面的版本

<details>
<summary>显示答案</summary>

**答案：C) 完成就绪检查后升级到下一个受 EKS 支持的小版本**

EKS 控制平面升级一次只能升级**一个小版本**，例如 1.34 → 1.35 → 1.36。请确认 EKS 提供每个目标版本；上游 Kubernetes 已发布某个版本，并不能证明 EKS 已提供该版本。不要根据当前 Kubernetes 1.x 工作流推断未来的大版本升级策略。

升级控制平面之前，请按 EKS 流程要求，先将托管节点和 Fargate 节点升级到其当前小版本；并按建议更新自管理/混合节点。Kubelet 版本绝不能高于 API server。Kubernetes 1.28+ 的常规版本偏差上限允许 Kubelet 最多落后三个小版本，但这并不意味着可以忽略 EKS 升级前提条件。

请先检查 insights、已移除的 API、附加组件兼容性、容量以及应用/数据备份。EKS 不提供对其托管 etcd 的常规管理员 Shell 访问，无法供用户自行运行快照命令；请使用受支持的集群/资源和持久化数据备份/恢复流程。此命令仅强制执行一次升级一个小版本的要求，并不能替代这些检查：

```bash
set -euo pipefail
: "${EXAMPLE_CLUSTER:?}" "${EXAMPLE_REGION:?}" "${NEXT_KUBERNETES_VERSION:?Confirm the next supported EKS minor}"
CURRENT_KUBERNETES_VERSION=$(aws eks describe-cluster \
  --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" --query cluster.version --output text)
if [[ "$CURRENT_KUBERNETES_VERSION" =~ ^1\.([0-9]+)$ ]]; then
  CURRENT_MINOR="${BASH_REMATCH[1]}"
else
  printf '%s\n' 'Unexpected cluster version; stop and inspect.' >&2
  exit 1
fi
EXPECTED_NEXT_VERSION="1.$((CURRENT_MINOR + 1))"
[ "$NEXT_KUBERNETES_VERSION" = "$EXPECTED_NEXT_VERSION" ] || {
  printf '%s\n' 'Only the next minor version is allowed in this upgrade example.' >&2
  exit 1
}
CLUSTER_UPDATE_ID=$(aws eks update-cluster-version --name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --kubernetes-version "$NEXT_KUBERNETES_VERSION" \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$CLUSTER_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```
等待该更新 ID 成功，然后按文档规定的顺序更新节点和兼容的集群组件。Cluster Autoscaler 的小版本应与集群匹配；kubectl 版本应处于其支持的偏差范围内。

当前 EKS 支持在就地升级完成后的七天内，有条件地回滚到前一个小版本。对创建时即使用该版本的集群，或因扩展支持期结束而自动升级的集群，不提供此功能。请先准备兼容的节点/附加组件；Auto Mode 会管理其节点回滚。回滚不会还原 etcd、工作负载或持久化数据。请参阅官方回滚就绪要求，不要将其视为无条件撤销操作。

</details>

## 简答题

6. 如何更改 EKS 托管节点组的实例类型？

<details>
<summary>答案与说明</summary>

这取决于实例类型的配置位置：

* 在托管节点组的 `instanceTypes` 中设置的类型，不是 `UpdateNodegroupConfig` 字段。请创建替代节点组，验证容量并迁移工作负载，然后再停用旧组。
* 如果节点组最初使用**你自己的自定义启动模板**创建，且实例类型配置在该模板中而非 EKS 组字段中，则可以更新到**同一模板**的新版本。EKS 会回收节点。不要修改 EKS 生成的模板，也不要假设可以随意切换模板 ID。
* 对于自管理 ASG，更新启动模板/刷新实例也需要 Kubernetes 感知型排空和生命周期设计；仅靠 EC2 替换并不能实现遵循 PDB 的迁移。

请检查 AMI 架构、驱动程序、Pod IP 限制、labels/taints、存储拓扑、配额和 PDB。对于由 Terraform 管理的资源，应通过所属 state 进行更改并检查替换操作；不要在 CLI 中进行状态外更改，然后假设 state 仍然正确。

</details>

7. 如何仅允许通过私有方式访问 Kubernetes API endpoint？

<details>
<summary>答案与说明</summary>

将私有访问设为 true，将公共访问设为 false。在 module v21 中，这些参数是 `endpoint_private_access` 和 `endpoint_public_access`；如适用，请通过所属 Terraform state 进行更改。

禁用公共访问前，请验证管理员所连接的网络到私有 endpoint 之间的 DNS、路由和安全规则。系统可以从 VPC **或其他正确连接的网络**访问它；不必实际位于 VPC 中。此操作更改的是 Kubernetes API endpoint，而不是单独的 AWS EKS 服务 API 访问权限。

对于由 API 管理的集群，对应的 CLI 操作为：

```bash
set -euo pipefail
ENDPOINT_UPDATE_ID=$(aws eks update-cluster-config \
  --region "${EXAMPLE_REGION:?}" --name "${EXAMPLE_CLUSTER:?}" \
  --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true \
  --query update.id --output text)
aws eks describe-update --region "$EXAMPLE_REGION" --name "$EXAMPLE_CLUSTER" \
  --update-id "$ENDPOINT_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```
跟踪该更新 ID，直到状态为 `Successful`，并从预期的管理路径测试经过身份验证的 kubectl 访问。单次返回 `InProgress` 并不表示操作已完成。

</details>

8. EKS Kubernetes 版本的支持生命周期是什么？

<details>
<summary>答案与说明</summary>

EKS 的每个小版本提供 **14 个月标准支持**，随后提供 **12 个月扩展支持**，并额外收取集群小时费用。计时从该版本的 EKS 发布日期开始，而非上游发布日期。

截至 2026 年 10 月 12 日，EKS 将 1.34–1.37 列为标准支持版本，将 1.31–1.33 列为扩展支持版本。EKS 1.37 于 2026 年 10 月 1 日开始提供，晚于其上游版本 8 月 26 日的发布时间。选择部署/升级目标前，请查看当前 EKS 版本日历。

默认启用扩展支持。集群升级策略决定标准支持结束时的行为。扩展支持结束后，EKS 会自动将控制平面升级到最旧的受支持扩展版本；旧版本不会在没有更新的情况下无限期运行。托管/自管理/混合节点和附加组件需要各自进行生命周期操作，而 Auto Mode 会管理其功能和节点。

不要依赖旧测验中“固定四个版本”、“提前 60 天通知”或“版本发布滞后 2–3 个月”等规则。请根据实际集群使用已公布的日期和策略。上游 Kubernetes 有自己的支持计划；旧的九个月对比已不是当前指导。

</details>

## 实践题

9. 设计 Pod 自动扩缩容方案，CPU 利用率目标为 75% / 内存利用率目标为 80%，节点组范围为 2–10 个节点，初始为 3 个节点。

<details>
<summary>答案与说明</summary>

将**Pod 需求扩缩容**与**节点容量扩缩容**分开。使用 CPU 75% 和内存 80% 的 HPA 资源利用率目标，并配置 Metrics Server 和有效的容器 requests。HPA 会根据指标选择副本数最高的建议值，同时受容差、限制和稳定窗口影响；它不是一旦“超过阈值”就立即触发的警报。

然后，对 min=2、max=10、初始 desired=3 的托管节点组使用 Cluster Autoscaler。对应的 Terraform module 节点组字段是 `min_size`、`max_size` 和 `desired_size`；请检查所属配置。以下完整的 eksctl 替代方案适用于在经审核的现有集群上创建新节点组：

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: autoscaling-workers
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  minSize: 2
  maxSize: 10
  desiredCapacity: 3
```
使用问题 1 中的专用且经过授权的 Cluster Autoscaler 配置。仅有上下限并不会运行 autoscaler。CA 会根据无法调度的 Pod requests 和移除约束作出响应；它本身不实现所要求的 CPU/内存百分比目标。

在新建的 `autoscaling-lab` namespace 中，以下 Deployment/HPA 展示了 requests 和两种指标。Pod 副本范围 2–20 与节点范围 2–10 是分开的：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: autoscaling-lab
spec:
  replicas: 2
  selector:
    matchLabels: {app: my-app}
  template:
    metadata:
      labels: {app: my-app}
    spec:
      automountServiceAccountToken: false
      containers:
      - name: web
        image: nginx:1.30.6
        ports:
        - containerPort: 80
        resources:
          requests: {cpu: 100m, memory: 128Mi}
          limits: {cpu: 500m, memory: 256Mi}
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
  namespace: autoscaling-lab
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 75
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```
在经过批准的负载测试中检查 HPA conditions、指标可用性、Pending 原因和 autoscaler 决策。随着副本增加，内存使用量可能不会按比例下降，因此请验证该指标是否适用于应用程序。此处的 requests/limits 数值仅为示例，并非经过测量得出的规格。

不要对同一 desired-capacity 循环添加独立的 ASG CPU/内存目标跟踪策略。它们可能与 CA 相互竞争，且排空行为不同。EC2 默认不提供常规的内存利用率指标；任何单独的非 CA 方案都需要正确发布自定义指标并使用自定义 namespace，不能假设存在 `AWS/EC2` 内存指标。此 HPA+CA 方案不需要此类 ASG 策略。

</details>

## 高级问题

10. 说明蓝绿节点组升级、风险以及受控迁移工作流。

<details>
<summary>答案与说明</summary>

创建替代容量，对其进行测试，逐步迁移，并且只有在验证应用程序/数据后才停用旧组。在仍需要回滚时保留旧容量和兼容状态；在同一集群中共享资源并不意味着完全隔离或保证零停机。

请检查配额、子网 IP、镜像/架构、labels、taints、Daemon 开销、PDB、本地数据以及卷的 AZ/挂载约束。StatefulSet 成员身份本身并不能让卷可移植。更改 TTL 或添加 service mesh 之前，请先调查 DNS 故障。确认监控/日志收集器确实覆盖新节点。

以下 CLI 示例适用于**由 API 管理的节点组**，并使用尚未占用的绿组名称。对于由 Terraform 或 eksctl/CloudFormation 管理的节点组，应通过相应管理工具执行等效变更，以避免配置漂移和孤立堆栈。

```bash
set -euo pipefail
: "${EXAMPLE_CLUSTER:?}" "${EXAMPLE_REGION:?}" "${OLD_NODEGROUP_NAME:?}" "${GREEN_NODEGROUP_NAME:?}"
[ "$OLD_NODEGROUP_NAME" != "$GREEN_NODEGROUP_NAME" ]
OLD_NODEGROUP_ARN=$(aws eks describe-nodegroup --cluster-name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --nodegroup-name "$OLD_NODEGROUP_NAME" \
  --query nodegroup.nodegroupArn --output text)
aws eks create-nodegroup --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$GREEN_NODEGROUP_NAME" --scaling-config minSize=3,maxSize=10,desiredSize=5 \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" --instance-types t3.large \
  --ami-type AL2023_x86_64_STANDARD --node-role "${NODE_ROLE_ARN:?}" \
  --labels audit.example.com/pool=green
aws eks wait nodegroup-active --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$GREEN_NODEGROUP_NAME"
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -l "eks.amazonaws.com/nodegroup=$GREEN_NODEGROUP_NAME" -o wide
```
节点组标签不能证明底层 ASG 已配置 Cluster Autoscaler 发现标签。如果 CA 将管理该组，请验证实际的 ASG 标签/IAM。在迁移主工作负载之前，请检查新 Node 是否就绪，并检查作用域单独限定的 canary 工作负载。

每次只排空一个已确认的旧节点。此操作有意不使用自动删除 emptyDir 和强制驱逐：

```bash
# One reviewed node at a time, after validating replacement capacity.
OLD_NODE_JSON=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  get node "${OLD_NODE_NAME:?}" -o json) || exit 1
OLD_NODE_GROUP=$(printf '%s' "$OLD_NODE_JSON" |
  jq -er '.metadata.labels["eks.amazonaws.com/nodegroup"]') || exit 1
if [ "$OLD_NODE_GROUP" != "${OLD_NODEGROUP_NAME:?}" ]; then
  printf '%s\n' 'Node is not in the intended old managed node group.' >&2
  exit 1
fi
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" cordon "$OLD_NODE_NAME" &&
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" drain "$OLD_NODE_NAME" \
  --ignore-daemonsets --timeout=15m
```
每一步之后都要验证就绪状态、应用健康情况和持久化数据。如果排空失败，请停止操作并解决原因。在验证所有工作负载且不再需要保留旧组后，请在单独执行最终删除操作之前，比较旧组的原始 ARN：

```bash
# A separate final step for API-owned groups only.
: "${OLD_NODEGROUP_ARN:?Use the ARN captured before migration}"
if [ "${MIGRATION_VERIFIED:?Set yes only after application/data checks}" = yes ]; then
  CURRENT_OLD_GROUP_ARN=$(aws eks describe-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
    --region "${EXAMPLE_REGION:?}" --nodegroup-name "${OLD_NODEGROUP_NAME:?}" \
    --query nodegroup.nodegroupArn --output text) || exit 1
  [ "$CURRENT_OLD_GROUP_ARN" = "$OLD_NODEGROUP_ARN" ] || {
    printf '%s\n' 'Node-group identity changed; no deletion attempted.' >&2
    exit 1
  }
  aws eks delete-nodegroup --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --nodegroup-name "$OLD_NODEGROUP_NAME" || exit 1
  aws eks wait nodegroup-deleted --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --nodegroup-name "$OLD_NODEGROUP_NAME"
fi
```

</details>


## Terraform 检查

11. terraform_remote_state 读取者可以访问什么？
   * A) 在存储层只能访问已声明的输出
   * B) 完整的 state 快照，尽管 HCL 暴露的是输出
   * C) 在任何情况下都不能访问敏感值
   * D) 只能访问其自身 module 中的资源

<details>
<summary>显示答案</summary>

**答案：B) 完整的 state 快照，尽管 HCL 暴露的是输出**

State 访问权限是授权边界。如果消费者不应读取完整快照，请单独发布选定的值。

</details>

12. 哪些输入名称与 EKS module v21 示例相匹配？
   * A) cluster_name 和 cluster_version
   * B) name 和 kubernetes_version
   * C) clusterId 和 versionNumber
   * D) cluster_addons 和 cluster_compute_config

<details>
<summary>显示答案</summary>

**答案：B) name 和 kubernetes_version**

Module v21 重命名了这些输入。AWS 资源字段（例如 aws_eks_addon.cluster_name）和 module 输出（例如 cluster_name）仍使用各自文档中规定的名称；不要全局替换每个匹配项。

</details>

13. 关于 S3 backend 示例，哪项说法正确？
   * A) encrypt=true 也会启用 state 锁定
   * B) DynamoDB 是唯一的锁定选项
   * C) use_lockfile=true 会启用 S3 锁定；必须准备好客户端和锁文件 IAM 权限
   * D) 一个锁可以协调所有 state 键

<details>
<summary>显示答案</summary>

**答案：C) use_lockfile=true 会启用 S3 锁定；必须准备好客户端和锁文件 IAM 权限**

S3 锁文件需要 Terraform 1.10+。DynamoDB 锁定已弃用；应迁移所有协同使用的客户端，而不是在旧客户端仍依赖该表时将其删除。

</details>

14. aws_eks_pod_identity_association 会创建 Kubernetes ServiceAccount 吗？
   * A) 会，并授予 cluster-admin
   * B) 不会；namespace/ServiceAccount 以及受支持的 agent/SDK 路径是独立的前提条件
   * C) 会，并安装 Metrics Server
   * D) 仅适用于 Fargate

<details>
<summary>显示答案</summary>

**答案：B) 不会；namespace/ServiceAccount 以及受支持的 agent/SDK 路径是独立的前提条件**

此关联将 AWS 身份绑定到现有 Kubernetes 身份。请限制信任和权限，保持启用所需的会话标签，处理传播，并验证实际采用的角色。

</details>

15. module 约束 ~> 21.0 允许什么？
   * A) 仅允许 21.0.0
   * B) 仅允许 21.0.x 的补丁版本
   * C) 允许兼容范围内 21.x 的小版本和补丁版本（低于 22.0），但不保证行为
   * D) 允许所有未来的大版本

<details>
<summary>显示答案</summary>

**答案：C) 允许兼容范围内 21.x 的小版本和补丁版本（低于 22.0），但不保证行为**

~> 21.0.0 会将范围限制在 21.0.x。指南会显式固定 module 版本；.terraform.lock.hcl 记录 provider 选择，而非远程 module 版本。应用前请检查已保存的计划。

</details>

## 参考资料

- [API_CreateNodegroup.html](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateNodegroup.html)
- [ml-node-groups.html](https://docs.aws.amazon.com/eks/latest/userguide/ml-node-groups.html)
- [fargate-profile.html](https://docs.aws.amazon.com/eks/latest/userguide/fargate-profile.html)
- [fargate-pod-configuration.html](https://docs.aws.amazon.com/eks/latest/userguide/fargate-pod-configuration.html)
- [API_NodegroupUpdateConfig.html](https://docs.aws.amazon.com/eks/latest/APIReference/API_NodegroupUpdateConfig.html)
- [launch-templates.html](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html)
- [kubernetes-versions.html](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [update-cluster.html](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [rollback-cluster.html](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [cas.html](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)
- [horizontal-pod-autoscale](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [s3](https://developer.hashicorp.com/terraform/language/backend/s3)
- [remote-state-data](https://developer.hashicorp.com/terraform/language/state/remote-state-data)
