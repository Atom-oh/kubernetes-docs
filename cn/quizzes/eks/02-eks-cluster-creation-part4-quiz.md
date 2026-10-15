# EKS 集群创建测验 - 第 4 部分

> **最后更新**: October 12, 2026

本测验将 Terraform 集群指南与扩缩容、身份和生命周期操作联系起来。最后一节检查 Terraform 专属概念。示例要求已审核的账户/Region/kubeconfig、IAM 和网络前提条件；它们在本次审计期间未被部署。

## 基础概念问题

1. Cluster Autoscaler 和 Karpenter 在预置方面的主要区别是什么？
   * A) CA 是一项 AWS 托管服务
   * B) CA 扩缩现有组；Karpenter 预置选定的单个容量
   * C) CA 仅衡量 CPU，Karpenter 仅衡量 Pod 数量
   * D) Karpenter 替代 Kubernetes scheduler

<details>
<summary>显示答案</summary>

**答案：B) CA 扩缩现有组；Karpenter 预置选定的单个容量**

Cluster Autoscaler 调整已发现的预定义节点组/ASG 的大小。Karpenter 通过 NodePools 和 EC2NodeClasses 创建 NodeClaims 和选定的 EC2 容量。Kubernetes 调度 Pod；Karpenter 不会替代 Kubernetes scheduler。

两者都会考虑无法调度的工作负载请求和放置约束。两者都不只是“CPU 百分比与 Pod 数量”的区别，且两者均不会就地调整正在运行的 EC2 实例大小。Karpenter 可以用不同大小的实例替换容量；VPA 则单独管理 Pod 资源请求。

**Cluster Autoscaler 示例：**对于 EKS 1.36，使用匹配的次要版本以及具有已审核 IAM 和发现标签的专用 ServiceAccount。Chart 9.59.0 需要显式覆盖为 v1.36.1 镜像。安装前渲染 RBAC、镜像和参数：

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
除非经审核的工作负载/数据策略另有要求，否则请保留本地存储和系统 Pod 防护措施。由 CA 管理的同一组内的混合实例类型应具有相近的 CPU/内存/GPU 规格。

**Karpenter 示例：**安装兼容的 controller/CRD，并单独配置其 IAM、节点授权、发现标签、中断处理和容量限制。将两个 AMI 占位符替换为与集群版本和各架构匹配、且已审核的 AL2023 镜像。如果允许两种架构，工作负载镜像必须同时支持这两种架构：

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
| 配置 | 组、发现、IAM 和 controller | NodePools、EC2NodeClasses、IAM 和 controller |
| 移除 | 需要调度和中断检查 | 受整合、预算和中断控制约束 |
| 原指南中的历史耗时声明 | 2–10 分钟，未经验证 | 少于 1 分钟，未经验证 |

原始耗时数据保留为**未经验证的历史声明**，而非本次审计中复现的基准数据或当前性能保证。节点启动、镜像、配额和工作负载约束都会影响这两种工具。请勿根据该表推断通用的成本、简易性或延迟排名。

</details>

2. 当前 EKS CreateNodegroup API 中有哪些容量类型？
   * A) Reserved、On-Demand、Spot
   * B) On-Demand、Spot、Dedicated
   * C) ON_DEMAND、SPOT、CAPACITY_BLOCK
   * D) Standard、Burstable、Compute-Optimized

<details>
<summary>显示答案</summary>

**答案：C) ON_DEMAND、SPOT、CAPACITY_BLOCK**

当前 EKS CreateNodegroup API 包含 **ON_DEMAND、SPOT 和 CAPACITY_BLOCK**。托管节点组使用一种容量类型；对于不同容量池，请使用不同的组。

On-Demand 可避免 Spot 回收，但并不保证不中断或可用性。Spot 使用闲置容量，要求工作负载能够容忍中断；宣传的折扣并不保证一定节省成本。Reserved Instances/Savings Plans 是计费安排，并非额外的 CreateNodegroup 枚举值。

Capacity Blocks 是面向受支持实例/Regions 的另一种有时限预留工作流。它们需要针对预留的自定义启动模板、匹配的 AZ/subnet 以及了解预留的扩缩容。EKS 会在预留结束前 40 分钟创建计划的缩容操作；请勿修改/删除该操作。以下示例是传统的 On-Demand/Spot 替代方案，并非 Capacity Block 预置。

**AWS CLI：**使用未使用的节点组名称、现有私有 subnet 和经批准的 EC2 节点角色（包括所需的 CNI 身份路径）。等待组激活，然后验证实际的 Node/工作负载就绪状态：

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
**eksctl 替代方案：**为现有集群和未使用的组名称保存配置，然后使用 `eksctl create nodegroup -f nodegroups.yaml`。请使用 `managedNodeGroups` 和 `spot`，而非原始示例中不受支持的 `capacityType` 字段：

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
使用亲和性/selectors 和 tolerations 放置合适的工作负载。托管节点组具有内置的 Spot 再平衡/驱逐处理；Node Termination Handler 并非通用的额外要求。PDB 无法阻止 EC2 回收 Spot 实例，而且并非每个 Pod 都能获得完整的中断窗口。请规划检查点、备用容量和中断恢复。

</details>

3. 每个 Fargate profile selector 中哪个字段是必填项？
   * A) 实例类型
   * B) Namespace；labels 为可选项
   * C) Security group ID
   * D) 最大 Pod 数量

<details>
<summary>显示答案</summary>

**答案：B) Namespace；labels 为可选项**

每个 profile selector 都需要一个 **namespace**；labels 为可选项。profile 还需要名称和 Pod execution role，并使用符合条件的私有 subnets。它没有 security-group 参数。Pod security groups 是一种单独受支持的策略机制，而非 Fargate-profile 字段。

使用未使用的 profile 名称和已审核的私有 subnet ID。此 selector 有意只针对应用程序 Pod，保持现有 CoreDNS 放置不变：

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
启动匹配的 Pod 前请等待 `ACTIVE`。下方是替代的 eksctl profile 定义；创建之前，请验证集群的私有 subnet 发现和 execution-role 设置：

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
仍需单独创建 namespace 和带标签的工作负载。如果多个 profile 匹配，除非 Pod 使用 `eks.amazonaws.com/fargate-profile` 选择匹配的 profile，否则 EKS 使用按字母数字排序的 profile 名称。Profiles 不可变；替换/删除它们会影响其 Pod。

Pod execution role 服务于 Fargate 基础设施，而非应用程序 AWS 访问。请使用兼容的工作负载身份，例如 IRSA；EKS Pod Identity 不支持 Fargate。将 CoreDNS 移至 Fargate 需要其 compute configuration 和匹配的 profile，而不只是向 selector 添加 `kube-system`。

Fargate 按**预置容量**收费，由请求的资源加上开销/取整决定；它并非仅按采样的 CPU/内存使用量计费。检查 `CapacityProvisioned`。EKS Fargate 不支持 Spot、DaemonSets、特权容器、主机网络或挂载 EBS 的工作负载卷。持久 EFS 使用静态预置；仅 profile 匹配不会创建文件系统/PV/PVC。请考虑 DNS、镜像拉取、STS 和其他必需的网络路径。

</details>

4. 以下哪项不是 NodegroupUpdateConfig 字段？
   * A) maxUnavailable
   * B) maxUnavailablePercentage
   * C) updateStrategy
   * D) Node-group operation timeout

<details>
<summary>显示答案</summary>

**答案：D) Node-group operation timeout**

`NodegroupUpdateConfig` 支持整数 `maxUnavailable`、整数 `maxUnavailablePercentage` 和 `updateStrategy`（`DEFAULT` 或 `MINIMAL`）。设置数量或百分比，不可同时设置两者。百分比本身不是 `maxUnavailable` 的有效值。

操作超时不是 NodegroupUpdateConfig 字段。`--force` 属于版本更新请求，可以绕过 Pod 驱逐保护；它不是存储的 update-config 设置。CLI/IaC 等待超时也不同于服务操作。

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
对于替代的百分比设置，请使用 `{"maxUnavailablePercentage":20,"updateStrategy":"DEFAULT"}`。启动版本更新前，请跟踪返回的更新 ID 直至 `Successful`。`DEFAULT` 先启动替换容量；`MINIMAL` 先终止选定的旧节点以减少临时额外容量。

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
PDB 并非一般可用性保证。直接删除、故障和工作负载 controller 自身的 rollout 与驱逐不同。检查备用容量、就绪状态和卷。不要承诺已经运行的 EKS 更新可以简单暂停或回滚；停止后续计划的变更，并遵循适用的恢复流程。

</details>

5. 正常 EKS 版本工作流支持哪一个 control-plane 升级步骤？
   * A) 直接跨越两个次要版本
   * B) 跳转至任意上游版本
   * C) 在就绪检查后移至下一个 EKS 支持的次要版本
   * D) 先将节点升级到高于 control-plane 的版本

<details>
<summary>显示答案</summary>

**答案：C) 在就绪检查后移至下一个 EKS 支持的次要版本**

EKS control-plane 升级按**每次一个次要版本**进行，例如 1.34 → 1.35 → 1.36。确认每个目标版本均由 EKS 提供；上游 Kubernetes 版本发布并不证明 EKS 可用。不要从当前 Kubernetes 1.x 工作流推断未来主版本升级策略。

在升级 control plane 之前，按照 EKS 流程要求将托管和 Fargate 节点升级到其当前次要版本；按建议更新 self-managed/hybrid 节点。Kubelet 的版本绝不可高于 API server。Kubernetes 1.28+ 的通用版本偏差上限允许 kubelet 最多落后三个次要版本，但这并不建议忽略 EKS 升级先决条件。

先审查 insights、已删除的 API、add-on 兼容性、容量和应用程序/数据备份。EKS 不提供对其托管 etcd 的常规管理员 shell 访问来运行自行制作的快照命令；请使用受支持的集群/资源及持久数据备份/恢复流程。此命令仅强制执行一个次要版本的升级步骤；它不能替代这些检查：

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
等待该更新 ID 成功，然后按其文档顺序更新节点和兼容的集群组件。将 Cluster Autoscaler 的次要版本与集群相匹配，并让 kubectl 保持在其支持的版本偏差范围内。

当前 EKS 在已完成的原地升级后七天内提供有条件地回滚至上一次要版本的功能。该功能不适用于在该版本创建的集群，也不适用于扩展支持结束时的自动升级。先准备兼容的节点/add-ons；Auto Mode 管理其节点回滚。回滚不会还原 etcd、工作负载或持久数据。请参阅官方回滚就绪要求，而不要将其当作无条件的撤销。

</details>

## 简答题

6. 如何更改 EKS 托管节点组的实例类型？

<details>
<summary>答案和说明</summary>

这取决于实例类型配置的位置：

* 在托管节点组的 `instanceTypes` 中设置的类型不是 `UpdateNodegroupConfig` 字段。请创建替换组，验证容量，并在淘汰旧组之前迁移工作负载。
* 如果该组最初是通过**您的自定义启动模板**创建，且实例类型位于该模板中而非 EKS 组字段，您可以更新为**同一模板**的新版本。EKS 会循环替换节点。不要修改 EKS 生成的模板，也不要假定可以切换任意模板 ID。
* 对于 self-managed ASG，启动模板更新/实例刷新还需要具备 Kubernetes 感知的 drain 和生命周期设计；仅 EC2 替换并不是 PDB 感知的迁移。

审查 AMI 架构、驱动程序、Pod IP 限制、labels/taints、存储拓扑、配额和 PDB。对于 Terraform 拥有的资源，请通过所属 state 进行变更并检查替换操作；不要进行带外 CLI 变更后假定 state 仍然正确。

</details>

7. 如何仅允许私有访问 Kubernetes API endpoint？

<details>
<summary>答案和说明</summary>

将私有访问设置为 true，将公共访问设置为 false。在 module v21 中，它们是 `endpoint_private_access` 和 `endpoint_public_access`；适用时，请通过所属 Terraform state 进行更改。

禁用公共访问前，从管理员已连接网络验证到私有 endpoint 的 DNS、路由和安全规则。系统可以从 VPC **或其他正确连接的网络**访问它；不必实际位于 VPC 内。这会更改 Kubernetes API endpoint，而非对独立 AWS EKS service API 的访问。

对于 API 拥有的集群，等效的 CLI 操作为：

```bash
set -euo pipefail
ENDPOINT_UPDATE_ID=$(aws eks update-cluster-config \
  --region "${EXAMPLE_REGION:?}" --name "${EXAMPLE_CLUSTER:?}" \
  --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true \
  --query update.id --output text)
aws eks describe-update --region "$EXAMPLE_REGION" --name "$EXAMPLE_CLUSTER" \
  --update-id "$ENDPOINT_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```
跟踪该更新 ID 至 `Successful`，并从预期的管理路径测试已认证的 kubectl 访问。单个 `InProgress` 响应并不代表完成。

</details>

8. EKS Kubernetes 版本支持生命周期是什么？

<details>
<summary>答案和说明</summary>

一个 EKS 次要版本获得**14 个月的标准支持**，随后获得**12 个月的扩展支持**，并产生额外的集群小时成本。时钟从其 EKS 发布日期开始，而非上游发布日期。

截至 October 12, 2026，EKS 将 1.34–1.37 列为标准支持，将 1.31–1.33 列为扩展支持。EKS 1.37 在 October 1, 2026 可用，晚于其 August 26 的上游发布。选择部署/升级目标前，请查看当前 EKS 发布日历。

扩展支持默认启用。集群升级策略决定标准支持结束时的行为。扩展支持结束后，EKS 会自动将 control plane 升级到最早受支持的扩展版本；旧版本不会无限期在没有更新的情况下运行。托管/self-managed/hybrid 节点和 add-ons 需要各自的生命周期操作，而 Auto Mode 管理其功能和节点。

请勿依赖旧测验中固定的“四个版本”、“60 天通知”或“2–3 个月发布滞后”规则。请使用实际集群的已发布日期和策略。上游 Kubernetes 有自己的支持计划；旧的九个月对比不再是当前指南。

</details>

## 动手实践题

9. 设计 Pod 自动扩缩容：CPU 75% / 内存 80% 利用率目标，以及一个限制在 2–10 个节点、初始为 3 个节点的节点组。

<details>
<summary>答案和说明</summary>

将**Pod 需求扩缩容**与**节点容量扩缩容**分开。使用 CPU 75% 和内存 80% 的 HPA 资源利用率目标，并配合 Metrics Server 和有效的容器 requests。HPA 从指标中选择最大的副本建议值，并受容差、限制和稳定化约束；它不是即时的“超过阈值”告警。

然后对托管节点组使用 Cluster Autoscaler，设置 min=2、max=10 和初始 desired=3。等效的 Terraform module 节点组字段为 `min_size`、`max_size` 和 `desired_size`；请审查所属配置。这个完整 eksctl 替代方案适用于已审核的现有集群上的新组：

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
使用问题 1 中专用且已授权的 Cluster Autoscaler 设置。仅设置边界不会运行 autoscaler。CA 对无法调度的 Pod 请求和移除约束作出反应；它自身不会实现所要求的 CPU/内存百分比。

在新的 `autoscaling-lab` namespace 中，以下 Deployment/HPA 演示了 requests 和两个指标。Pod 副本范围 2–20 与节点范围 2–10 是分开的：

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
        image: nginx:1.30.4
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
在经批准的负载测试下检查 HPA conditions、指标可用性、Pending 原因和 autoscaler 决策。增加副本时内存使用量可能不会按比例下降，因此请针对应用程序验证该指标。这些 requests/limits 值只是示例，而非经过测量的规格。

不要将独立的 ASG CPU/内存 target-tracking policy 添加到同一个 desired-capacity 循环中。它们可能会与 CA 竞争，并有不同的 drain 行为。默认情况下，EC2 不提供普通内存利用率；任何单独的非 CA 设计都需要正确发布的自定义指标和自定义 namespace，而非假定存在 `AWS/EC2` 内存指标。此 HPA+CA 方案不需要此类 ASG policy。

</details>

## 高级问题

10. 说明蓝绿节点组升级、其风险以及受保护的迁移工作流。

<details>
<summary>答案和说明</summary>

创建替换容量，对其进行测试，逐步迁移，并且仅在应用程序/数据验证后淘汰旧组。在仍有回滚必要时保留旧容量和兼容状态；共享一个集群并不是完整隔离或零停机保证。

审查配额、subnet IP、镜像/架构、labels、taints、daemon 开销、PDB、本地数据以及卷 AZ/挂载约束。StatefulSet 成员资格本身并不会使卷可移植。在更改 TTL 或添加 service mesh 之前调查 DNS 故障。确认监控/日志收集器确实覆盖新节点。

以下 CLI 示例适用于**API 拥有的组**，并使用未使用的绿色组名称。对于 Terraform 或 eksctl/CloudFormation 拥有的组，请通过该所有者执行等效变更，以避免漂移和孤立 stacks。

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
节点组标签并不能证明底层 ASG 具有 Cluster Autoscaler 发现标签。如果 CA 将管理它，请验证实际 ASG 标签/IAM。迁移主要工作负载前，请检查新 Node 就绪状态和单独限定范围的 canary 工作负载。

每次 drain 一个已确认的旧节点。此处特意省略自动 emptyDir 删除和强制驱逐：

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
每一步之后均验证就绪状态、应用程序健康和持久数据。drain 失败时停止并解决原因。在所有工作负载均已验证且不再需要保留旧组后，请在此单独的最终删除前比较其原始 ARN：

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

11. terraform_remote_state 读取器可以访问什么？
   * A) 仅存储层中的已声明 outputs
   * B) 完整 state 快照，即使 HCL 仅暴露 outputs
   * C) 在任何情况下都无法访问敏感值
   * D) 仅其自身 module 中的 resources

<details>
<summary>显示答案</summary>

**答案：B) 完整 state 快照，即使 HCL 仅暴露 outputs**

State 访问是一条授权边界。当消费者不应读取完整快照时，请单独发布选定的值。

</details>

12. 哪些输入名称与 EKS module v21 示例匹配？
   * A) cluster_name 和 cluster_version
   * B) name 和 kubernetes_version
   * C) clusterId 和 versionNumber
   * D) cluster_addons 和 cluster_compute_config

<details>
<summary>显示答案</summary>

**答案：B) name 和 kubernetes_version**

Module v21 重命名了这些输入。AWS resource 字段（例如 aws_eks_addon.cluster_name）和 module outputs（例如 cluster_name）仍使用各自文档规定的名称；不要全局替换每一处出现的名称。

</details>

13. 关于 S3 backend 示例的哪项陈述是正确的？
   * A) encrypt=true 也会启用 state locking
   * B) DynamoDB 是唯一的 locking 选项
   * C) use_lockfile=true 启用 S3 locking；必须准备客户端和 lock-file IAM 权限
   * D) 一个锁协调所有 state keys

<details>
<summary>显示答案</summary>

**答案：C) use_lockfile=true 启用 S3 locking；必须准备客户端和 lock-file IAM 权限**

对 S3 lock files 使用 Terraform 1.10+。DynamoDB locking 已弃用；请迁移协同客户端，而非在旧客户端仍依赖它时删除表。

</details>

14. aws_eks_pod_identity_association 会创建 Kubernetes ServiceAccount 吗？
   * A) 是，会附带 cluster-admin
   * B) 否；namespace/ServiceAccount 和受支持的 agent/SDK 路径是单独的先决条件
   * C) 是，并会安装 Metrics Server
   * D) 仅在 Fargate 上

<details>
<summary>显示答案</summary>

**答案：B) 否；namespace/ServiceAccount 和受支持的 agent/SDK 路径是单独的先决条件**

该 association 将 AWS identity 绑定到现有 Kubernetes identity。限定信任和权限范围，保持所需 session tags 启用，处理传播，并验证实际假定的角色。

</details>

15. module constraint ~> 21.0 允许什么？
   * A) 仅 21.0.0
   * B) 仅 21.0.x 中的补丁版本
   * C) 兼容范围内、低于 22.0 的 21.x 次要和补丁版本，但不保证行为
   * D) 每个未来主版本

<details>
<summary>显示答案</summary>

**答案：C) 兼容范围内、低于 22.0 的 21.x 次要和补丁版本，但不保证行为**

~> 21.0.0 将范围限制为 21.0.x。该指南显式固定 module 版本；.terraform.lock.hcl 记录 provider 选择，而非远程 module 版本。应用前审查保存的 plans。

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
