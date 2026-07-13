# EKS Cluster 创建测验 - 第 4 部分

本测验用于测试你对 Amazon EKS cluster 创建相关的高级配置、可扩展性和运维主题的理解。它涵盖 cluster 扩缩容、自动化、成本优化以及运维最佳实践等主题。

## 基本概念问题

1. 在 Amazon EKS cluster 中，Cluster Autoscaler 和 Karpenter 的主要区别是什么？
   * A) Cluster Autoscaler 是 AWS 服务，而 Karpenter 是开源工具
   * B) Cluster Autoscaler 在 node group 级别进行扩缩容，而 Karpenter 会配置符合工作负载需求的单个 node
   * C) Cluster Autoscaler 基于 CPU/memory 使用率进行扩缩容，而 Karpenter 基于 pod 数量进行扩缩容
   * D) Cluster Autoscaler 仅支持水平扩缩容，而 Karpenter 也支持垂直扩缩容

<details>

<summary>显示答案</summary>

**答案：B) Cluster Autoscaler 在 node group 级别进行扩缩容，而 Karpenter 会配置符合工作负载需求的单个 node**

**解释：** Amazon EKS cluster 中 Cluster Autoscaler 和 Karpenter 的主要区别在于它们的扩缩容方式。Cluster Autoscaler 基于现有 Auto Scaling Groups (ASGs) 在 node group 级别进行扩缩容，而 Karpenter 会直接配置符合工作负载需求的单个 node。

**Cluster Autoscaler 特点：**

1. **基于 Node Group 的扩缩容**：
   * 使用预定义的 Auto Scaling Groups 进行扩缩容
   * 在一个 node group 内使用相同实例类型或混合实例类型
   *   示例：

       ```yaml
       # Cluster Autoscaler Deployment
       apiVersion: apps/v1
       kind: Deployment
       metadata:
         name: cluster-autoscaler
         namespace: kube-system
       spec:
         replicas: 1
         selector:
           matchLabels:
             app: cluster-autoscaler
         template:
           metadata:
             labels:
               app: cluster-autoscaler
           spec:
             containers:
             - image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.23.0
               name: cluster-autoscaler
               command:
               - ./cluster-autoscaler
               - --v=4
               - --stderrthreshold=info
               - --cloud-provider=aws
               - --skip-nodes-with-local-storage=false
               - --expander=least-waste
               - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/my-cluster
       ```
2. **工作方式**：
   * 当存在无法调度的 pods 时扩容 node groups
   * 当 node 利用率较低时缩容 node groups
   * 在 ASG 的最小/最大大小限制内运行
3. **限制**：
   * 扩缩容速度相对较慢（2-10 分钟）
   * 受限于预定义的实例类型
   * 只能在 node group 级别进行扩缩容

**Karpenter 特点：**

1. **基于工作负载的配置**：
   * 选择符合工作负载需求的最佳实例类型
   * 不使用 ASGs，直接配置 EC2 实例
   *   示例：

       ```yaml
       # Karpenter Provisioner
       apiVersion: karpenter.sh/v1alpha5
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
         limits:
           resources:
             cpu: 1000
             memory: 1000Gi
         provider:
           subnetSelector:
             karpenter.sh/discovery: "true"
           securityGroupSelector:
             karpenter.sh/discovery: "true"
         ttlSecondsAfterEmpty: 30
       ```
2. **工作方式**：
   * 分析无法调度的 pods 的需求
   * 选择符合需求的最佳实例类型
   * 直接配置实例并调度 pods
   * 当 node 为空时自动终止 node
3. **优势**：
   * 扩缩容速度快（低于 1 分钟）
   * 选择针对工作负载优化的实例类型
   * 成本优化（Spot 实例利用、合适规格）
   * 配置简化（无需 ASG 管理）

**两种工具对比：**

| 特性                     | Cluster Autoscaler                  | Karpenter                                    |
| ------------------------ | ----------------------------------- | -------------------------------------------- |
| 扩缩容单位               | Node Group (ASG)                    | 单个 Node                                    |
| 实例选择                 | 预定义实例类型                      | 符合工作负载需求的最佳实例                   |
| 扩缩容速度               | 慢（2-10 分钟）                     | 快（低于 1 分钟）                            |
| 配置复杂度               | 中等（需要 ASG 配置）               | 低（只需 Provisioner 定义）                  |
| 成本优化                 | 有限                                | 高（针对工作负载优化的实例选择）             |
| 成熟度                   | 高（较早的项目）                    | 中等（相对较新的项目）                       |

**其他选项的问题：**

* **Cluster Autoscaler 是 AWS 服务，而 Karpenter 是开源工具**：两者都是开源工具。Cluster Autoscaler 由 Kubernetes SIG Autoscaling 管理；虽然 Karpenter 由 AWS 发起，但它也是开源项目。
* **Cluster Autoscaler 基于 CPU/memory 使用率进行扩缩容，而 Karpenter 基于 pod 数量进行扩缩容**：两者本质上都基于无法调度的 pods（Pending 状态）进行扩缩容。基于 CPU/memory 使用率的扩缩容是 Horizontal Pod Autoscaler (HPA) 的职责。
* **Cluster Autoscaler 仅支持水平扩缩容，而 Karpenter 也支持垂直扩缩容**：两者都只支持水平扩缩容（增加 node 数量）。不支持垂直扩缩容（增加 node 资源）。Pod 级别的垂直扩缩容是 Vertical Pod Autoscaler (VPA) 的职责。

Cluster Autoscaler 和 Karpenter 都是用于 EKS clusters 自动扩缩容的工具，但 Karpenter 提供更快、更灵活的扩缩容，并且可以选择符合工作负载需求的最佳实例。

</details>

2. 创建 Amazon EKS cluster 的 node group 时，可以使用哪些有效的容量类型？
   * A) Reserved, On-Demand, Spot
   * B) On-Demand, Spot, Dedicated
   * C) On-Demand, Spot
   * D) Standard, Burstable, Compute-Optimized

<details>

<summary>显示答案</summary>

**答案：C) On-Demand, Spot**

**解释：** 创建 Amazon EKS node group 时，可用的容量类型是 On-Demand 和 Spot。

**On-Demand 容量类型：**

* **特点**：实例可靠可用，不会被中断
* **定价**：按固定小时费率付费
* **适用工作负载**：
  * 对中断敏感的生产应用程序
  * 有状态工作负载
  * 数据库
  * 关键业务应用程序

**Spot 容量类型：**

* **特点**：利用 AWS 闲置容量，当 AWS 回收容量时可能会被中断
* **定价**：与 On-Demand 相比最高可享 90% 折扣
* **适用工作负载**：
  * 容错型应用程序
  * 无状态工作负载
  * 批处理作业
  * 开发/测试环境

**创建 EKS Node Group 时指定容量类型的示例：**

AWS CLI 示例：

```bash
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-spot-nodegroup \
  --scaling-config minSize=3,maxSize=10,desiredSize=5 \
  --subnets subnet-0a1b2c3d4e5f6g7h8 subnet-0a1b2c3d4e5f6g7h9 \
  --instance-types t3.medium t3a.medium \
  --capacity-type SPOT \
  --node-role arn:aws:iam::123456789012:role/EKS-NodeInstanceRole
```

eksctl 示例：

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
nodeGroups:
  - name: ng-on-demand
    instanceType: m5.large
    desiredCapacity: 3
    capacityType: ON_DEMAND
  - name: ng-spot
    instanceType: m5.large
    desiredCapacity: 2
    capacityType: SPOT
    spotInstancePools: 3
```

**其他选项的问题：**

* **Reserved, On-Demand, Spot**："Reserved" 指的是 EC2 Reserved Instances，但创建 EKS node groups 时不能直接将其指定为容量类型。Reserved Instances 是一种计费折扣模型，不能直接选择为 node group 容量类型。
* **On-Demand, Spot, Dedicated**："Dedicated" 指的是 EC2 Dedicated Instances，但不能直接指定为 EKS node group 容量类型。Dedicated Instances 可以通过单独的 tenancy 设置进行配置。
* **Standard, Burstable, Compute-Optimized**：这些表示 EC2 实例族类型，而不是容量类型。它们是选择实例类型（例如 t3.medium、m5.large、c5.xlarge）时考虑的特性。

**最佳实践：**

1. **使用混合容量策略**：
   * 将关键工作负载放在 On-Demand node groups 上
   * 将容错型工作负载放在 Spot node groups 上
   * 使用 node affinity 和 tolerations 控制工作负载放置
2. **使用 Spot Instances 时的注意事项**：
   * 指定多种实例类型（分散中断风险）
   * 实现适当的中断处理机制（Pod Disruption Budgets、优雅关闭 hooks）
   * 部署 AWS Node Termination Handler
3. **成本优化**：
   * 将 Savings Plans 或 Reserved Instances 应用于 On-Demand nodes
   * 考虑 Graviton (ARM) 实例
   * 选择适当的实例大小

</details>

3. 在 Amazon EKS cluster 中配置 Fargate profile 时，必须指定什么？
   * A) 实例类型和容量类型
   * B) Namespace 和 label selector
   * C) Subnet ID 和 security group
   * D) Autoscaling 设置和最大 pod 数

<details>

<summary>显示答案</summary>

**答案：B) Namespace 和 label selector**

**解释：** 配置 Amazon EKS Fargate profile 时，必须指定的是 namespace，并可选择指定 label selector。EKS 使用这些信息来判断哪些 pods 应该在 Fargate 上运行。

**Fargate Profile 组成部分：**

1. **必需组成部分**：
   * **Profile Name**：Fargate profile 的唯一标识符
   * **Pod Execution Role**：在 Fargate 基础设施上运行 pods 所需的 IAM role
   * **Subnets**：Fargate pods 将运行所在的私有 subnets（默认使用 cluster subnets）
   * **Selectors**：由 namespaces 和可选 labels 组成的数组
2. **Selector 配置**：
   * **Namespace**：pod 所属的 Kubernetes namespace（必需）
   * **Labels**：键值对形式的 Kubernetes labels（可选）

**Fargate Profile 创建示例：**

AWS CLI 示例：

```bash
aws eks create-fargate-profile \
  --cluster-name my-cluster \
  --fargate-profile-name my-fargate-profile \
  --pod-execution-role-arn arn:aws:iam::123456789012:role/AmazonEKSFargatePodExecutionRole \
  --subnets subnet-0a1b2c3d4e5f6g7h8 subnet-0a1b2c3d4e5f6g7h9 \
  --selectors namespace=default,labels={app=nginx} namespace=kube-system,labels={k8s-app=kube-dns}
```

eksctl 示例：

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
fargateProfiles:
  - name: fp-default
    selectors:
      - namespace: default
        labels:
          app: nginx
      - namespace: kube-system
        labels:
          k8s-app: kube-dns
```

**Fargate Profiles 的工作方式：**

1. 创建 pod 时，EKS 会检查 pod 的 namespace 和 labels。
2. 如果 pod 的 namespace 和 labels 与某个 Fargate profile 的 selectors 匹配，该 pod 将在 Fargate 基础设施上运行。
3. 如果不存在匹配的 Fargate profile，则 pod 会被调度到 EC2 nodes（如果可用），或保持 Pending 状态。

**其他选项的问题：**

* **实例类型和容量类型**：Fargate 是 serverless compute 服务，因此无需指定实例类型或容量类型。AWS 会自动配置所需的计算资源。
* **Subnet ID 和 security group**：虽然需要 subnet ID，但可以默认使用 cluster subnets。Security groups 是可选的；如果未指定，则使用 cluster 的 security groups。
* **Autoscaling 设置和最大 pod 数**：Fargate 会按 pod 自动扩缩容，因此不需要单独的 autoscaling 设置。Pod 数量通过 Kubernetes Deployments 或 HPA (Horizontal Pod Autoscaler) 管理。

**使用 Fargate 时的注意事项：**

1. **成本**：使用 Fargate 时，你只需为实际使用的 vCPU 和 memory 资源付费。空闲 nodes 没有成本。
2. **限制**：
   * DaemonSet pods 不受 Fargate 支持。
   * 不支持特权 containers。
   * 不支持 HostNetwork、HostPort 等 host network 模式。
   * 对于 persistent volumes，仅支持 Amazon EFS。
3. **使用场景**：
   * 批处理作业
   * Web 应用程序
   * API servers
   * Microservices
   * 开发/测试环境

</details>

4. 在 Amazon EKS cluster 中更新 node group 时，以下哪项不是“update configuration”中的可配置项？
   * A) 最大不可用 node 数
   * B) 最大不可用 node 百分比
   * C) Node 替换策略
   * D) Node group 更新超时

<details>

<summary>显示答案</summary>

**答案：C) Node 替换策略**

**解释：** “Node 替换策略”不是 Amazon EKS node group update configuration 中的官方配置项。EKS managed node groups 默认使用滚动更新方式，并且没有可直接更改此策略的选项。

**EKS Node Group Update Configuration 中可配置的项：**

1. **maxUnavailable**：
   * 更新期间可同时不可用的最大 nodes 数量
   * 可以指定为绝对数量（例如 1、2、3）或百分比（例如 20%）
   * 默认值：1
2. **maxUnavailablePercentage**：
   * 更新期间可同时不可用的最大 nodes 百分比
   * 指定为 1 到 100 之间的值
   * 不能与 `maxUnavailable` 一起使用
3. **force**：
   * 是否强制执行 node group 更新
   * 默认值：false
4. **Timeout**：
   * node group 更新操作的最大等待时间
   * 默认值：60 分钟

**Node Group Update Configuration 示例：**

AWS CLI 示例：

```bash
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --update-config maxUnavailable=2
```

或指定百分比：

```bash
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --update-config maxUnavailablePercentage=20
```

eksctl 示例：

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: my-nodegroup
    updateConfig:
      maxUnavailable: 2
```

**Node Group 更新过程：**

1. **更新开始**：AWS 启动 node group 更新。
2. **Node Draining**：根据 `maxUnavailable` 设置，cordon 并 drain 指定数量的 nodes。
3. **Node 终止**：终止已 drain 的 nodes。
4. **新 Node 创建**：使用新配置创建 nodes。
5. **重复**：重复步骤 2-4，直到所有 nodes 都更新完成。

**其他选项说明：**

* **最大不可用 (maxUnavailable) node 数**：用于指定更新期间可同时不可用的最大 nodes 数量的有效设置。
* **最大不可用 (maxUnavailable) node 百分比**：用于指定更新期间可同时不可用的最大 nodes 百分比的有效设置。
* **Node group 更新超时**：用于指定 node group 更新操作最大等待时间的有效设置。

**Node Group 更新最佳实践：**

1. **设置适当的 maxUnavailable 值**：
   * 过小会延长更新时间。
   * 过大可能影响应用程序可用性。
   * 根据工作负载特性和 node group 大小进行设置。
2. **配置 Pod Disruption Budgets (PDB)**：
   * 为关键工作负载设置 PDBs，以确保最低可用性。
   *   示例：

       ```yaml
       apiVersion: policy/v1
       kind: PodDisruptionBudget
       metadata:
         name: app-pdb
       spec:
         minAvailable: 2  # or maxUnavailable: 1
         selector:
           matchLabels:
             app: my-app
       ```
3. **更新前测试**：
   * 在关键更新前先在测试环境中验证。
   * 准备回滚计划。
4. **监控**：
   * 更新期间监控应用程序状态。
   * 如果出现问题，暂停或回滚更新。

</details>

5. 关于在 EKS cluster 中升级 Kubernetes 版本时“跳过”版本，以下哪项陈述是正确的？
   * A) 可以跳过 minor versions，但不能跳过 major versions
   * B) 可以跳过 major versions，但不能跳过 minor versions
   * C) major versions 和 minor versions 都不能跳过
   * D) major versions 和 minor versions 都可以跳过

<details>

<summary>显示答案</summary>

**答案：C) major versions 和 minor versions 都不能跳过**

**解释：** 升级 Amazon EKS cluster 时，major versions 和 minor versions 都必须按顺序升级。不支持跳过版本。

**EKS 版本升级规则：**

1. **需要顺序升级**：
   * 每个 Kubernetes 版本都必须从前一个版本按顺序升级。
   * 示例：1.22 -> 1.23 -> 1.24（不能从 1.22 直接升级到 1.24）
2. **支持的升级路径**：
   * 只能从当前版本升级到下一个 minor version
   * Major versions 也必须按顺序升级
3. **Control Plane 和 Node 版本差异**：
   * Control plane 最多可以比 nodes 超前 2 个 minor versions
   * Nodes 最多可以比 control plane 超前 1 个 minor version

**EKS 版本升级过程：**

1. **制定升级计划**：
   * 查看当前版本和目标版本之间的变更
   * 验证应用程序兼容性
   * 制定升级时间表和回滚计划
2. **推荐升级顺序**：
   * Control plane 升级
   * Add-on 升级（CoreDNS、kube-proxy、VPC CNI 等）
   * Node group 升级
3.  **升级命令示例**：

    使用 AWS CLI 升级 control plane：

    ```bash
    aws eks update-cluster-version \
      --name my-cluster \
      --kubernetes-version 1.24
    ```

    使用 eksctl 升级 control plane：

    ```bash
    eksctl upgrade cluster \
      --name=my-cluster \
      --version=1.24 \
      --approve
    ```

    Node group 升级：

    ```bash
    aws eks update-nodegroup-version \
      --cluster-name my-cluster \
      --nodegroup-name my-nodegroup
    ```

**EKS 版本支持政策：**

1. **支持周期**：
   * 每个 Kubernetes 版本在 EKS 发布后大约支持 14 个月。
   * AWS 始终维护至少 4 个生产 Kubernetes 版本的支持。
2. **支持终止通知**：
   * AWS 会在版本支持终止前约 60 天发布公告。
   * 支持终止后，clusters 会继续运行，但不会收到安全补丁或 bug 修复。
3. **版本发布周期**：
   * AWS 通常会在上游 Kubernetes 发布后 2-3 个月内在 EKS 支持新版本。

**升级最佳实践：**

1. **先在测试环境中升级**：
   * 在生产环境升级前先在测试 cluster 中验证
2. **升级前备份**：
   * etcd 备份以及重要资源的 YAML 备份
3. **渐进式升级**：
   * 逐步进行，而不是一次性升级所有 node groups
4. **升级后验证**：
   * 确认工作负载正常运行
   * 检查监控系统
   * 查看日志
5. **保持最新版本**：
   * 制定定期升级计划
   * 跟踪支持终止日期

**其他选项的问题：**

* **可以跳过 minor versions，但不能跳过 major versions**：minor versions 也不能跳过。必须按顺序升级。
* **可以跳过 major versions，但不能跳过 minor versions**：major versions 也不能跳过。必须按顺序升级。
* **major versions 和 minor versions 都可以跳过**：EKS 不支持跳过版本。

</details>

## 简答题

6. 要更改 EKS cluster 中 node group 的实例类型，需要做什么？

<details>

<summary>答案和解释</summary>

要更改 EKS managed node group 的实例类型，需要创建一个新的 node group 并迁移工作负载，然后删除现有 node group。Managed node groups 的实例类型在创建后不能直接更改。

一般步骤如下：

1. 使用所需实例类型创建新的 node group
2. 如有需要，设置 Pod Disruption Budgets (PDB)
3. Cordon 并 drain 现有 nodes，将工作负载迁移到新 nodes
4. 验证所有工作负载都已移动到新的 node group
5. 删除现有 node group

如果使用 self-managed node groups，可以更新 Auto Scaling Group 的 launch template 并执行 instance refresh。

</details>

7. 要在 EKS cluster 中禁用 Kubernetes API server 的公网访问并仅允许私有访问，需要更改哪些设置？

<details>

<summary>答案和解释</summary>

要禁用 EKS cluster 的 API server 公网访问并仅允许私有访问，需要更改 cluster 的 endpoint access 设置：

1. 通过 AWS Management Console：
   * 导航到 EKS console
   * 选择 cluster
   * 选择 "Networking" tab
   * 在 "Cluster endpoint access" section 中点击 "Edit"
   * 设置为 "Private"（禁用公网访问，启用私有访问）
2. 使用 AWS CLI：

```bash
aws eks update-cluster-config \
    --region region-code \
    --name cluster-name \
    --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true
```

更改此设置后，Kubernetes API server 只能从 VPC 内部访问。因此，只有 VPC 内的系统或连接到 VPC 的网络才能管理 cluster。

</details>

8. EKS cluster 中可用的 Kubernetes 版本通常支持多长时间？

<details>

<summary>答案和解释</summary>

Amazon EKS 中的每个 Kubernetes 版本通常在发布后支持约 14 个月。AWS 力求始终支持至少 4 个生产 Kubernetes 版本。

EKS 版本支持周期如下：

1. 初始发布：AWS 在 EKS 上提供新的 Kubernetes 版本
2. 标准支持：约 14 个月内提供安全补丁和 bug 修复
3. 支持终止公告：AWS 会在版本支持终止前约 60 天发布公告
4. 支持终止：运行已弃用版本的 clusters 不会自动升级，但必须手动升级

AWS 开始支持新版本的时间略晚于 Kubernetes 社区发布，但支持周期通常更长。上游 Kubernetes 项目对每个版本的支持约为 9 个月，而 EKS 支持约 14 个月。

</details>

## 实操问题

9. 说明如何为 EKS cluster 中的 node group 配置 Auto Scaling 设置，并编写满足以下要求的配置：

* 最小 node 数：2
* 最大 node 数：10
* 期望 node 数：3
* 基于 CPU 利用率扩容（当 CPU 利用率超过 75% 时）
* 基于 memory 利用率扩容（当 memory 利用率超过 80% 时）

<details>

<summary>答案和解释</summary>

要为 EKS node group 配置 Auto Scaling 设置，请按以下步骤操作：

1. 首先，在创建 node group 时或在现有 node group 的 Auto Scaling Group 设置中配置基本大小：

```bash
aws eks create-nodegroup \
    --cluster-name my-cluster \
    --nodegroup-name my-nodegroup \
    --scaling-config minSize=2,maxSize=10,desiredSize=3 \
    # Other required parameters...
```

2. 对于基于 CPU 和 memory 利用率的扩缩容，可以设置 Cluster Autoscaler 或 Karpenter，也可以直接向 Auto Scaling Group 添加基于 CloudWatch alarm 的 policies。

**Cluster Autoscaler 方法：**

Cluster Autoscaler Deployment YAML：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
  labels:
    app: cluster-autoscaler
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cluster-autoscaler
  template:
    metadata:
      labels:
        app: cluster-autoscaler
    spec:
      serviceAccountName: cluster-autoscaler
      containers:
      - image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.23.0
        name: cluster-autoscaler
        resources:
          limits:
            cpu: 100m
            memory: 300Mi
          requests:
            cpu: 100m
            memory: 300Mi
        command:
        - ./cluster-autoscaler
        - --v=4
        - --stderrthreshold=info
        - --cloud-provider=aws
        - --skip-nodes-with-local-storage=false
        - --expander=least-waste
        - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/my-cluster
        - --balance-similar-node-groups
        - --skip-nodes-with-system-pods=false
```

**基于 CloudWatch Alarm 的 Auto Scaling Policies：**

基于 CPU 利用率的扩容 policy：

```bash
aws autoscaling put-scaling-policy \
    --auto-scaling-group-name my-nodegroup-xxx \
    --policy-name cpu-scale-out \
    --policy-type TargetTrackingScaling \
    --target-tracking-configuration file://cpu-policy.json
```

cpu-policy.json：

```json
{
  "TargetValue": 75.0,
  "PredefinedMetricSpecification": {
    "PredefinedMetricType": "ASGAverageCPUUtilization"
  }
}
```

基于 memory 利用率的扩容 policy（需要 CloudWatch custom metric）：

```bash
# First need to set up agent to publish memory utilization as CloudWatch custom metric
aws autoscaling put-scaling-policy \
    --auto-scaling-group-name my-nodegroup-xxx \
    --policy-name memory-scale-out \
    --policy-type TargetTrackingScaling \
    --target-tracking-configuration file://memory-policy.json
```

memory-policy.json：

```json
{
  "TargetValue": 80.0,
  "CustomizedMetricSpecification": {
    "MetricName": "MemoryUtilization",
    "Namespace": "AWS/EC2",
    "Dimensions": [
      {
        "Name": "AutoScalingGroupName",
        "Value": "my-nodegroup-xxx"
      }
    ],
    "Statistic": "Average",
    "Unit": "Percent"
  }
}
```

在真实环境中，对 Kubernetes 工作负载而言，使用 Cluster Autoscaler 更合适。Cluster Autoscaler 基于 pod resource requests 扩缩容 nodes，从而实现更高效的扩缩容。

</details>

## 高级问题

10. 说明在 EKS cluster 中使用 blue/green 方法升级 node groups 的策略，并列出此过程中可能出现的问题及解决方案。

<details>

<summary>答案和解释</summary>

#### EKS Node Group Blue/Green 升级策略

Blue/green deployment 是一种在现有环境（blue）旁边构建新环境（green），然后将流量切换到新环境的方法。应用于 EKS node groups 时，流程如下：

**Blue/Green 升级步骤：**

1. **准备阶段**：
   * 记录当前 node group 配置（labels、taints、tags 等）
   * 识别当前工作负载状态和资源需求
2. **创建 Green 环境**：
   * 创建新的 node group（升级后的 AMI、Kubernetes 版本、实例类型等）
   * 应用与现有 node group 相同的 labels 和 taints
   * 应用必要的附加配置（tags、IAM roles 等）
3. **测试**：
   * 将测试工作负载部署到新的 node group
   * 验证功能和性能
4. **流量迁移**：
   * 验证 Pod Disruption Budget (PDB) 设置
   * Cordon 现有 nodes（阻止新的 pod 调度）
   * 逐步 drain 现有 nodes（将工作负载迁移到新 nodes）
   * 监控工作负载状态
5. **完成和清理**：
   * 验证所有工作负载都已移动到新 nodes
   * 删除现有 node group
   * 如有需要，更新监控和告警

**潜在问题和解决方案：**

1. **资源不足问题**：
   * **问题**：创建新 node group 时需要双倍资源，可能超过 service quotas
   * **解决方案**：提前检查 service quotas，并在需要时请求提升；或按小批次逐步升级
2. **有状态工作负载迁移**：
   * **问题**：使用 persistent volumes 的有状态工作负载在 nodes 之间移动时可能出现问题
   * **解决方案**：验证 PVC/PV 设置，使用 StatefulSets，使用合适的 storage classes，并执行备份
3. **Node Affinity 和 Pod Disruption**：
   * **问题**：由于 node affinity 或 pod anti-affinity，某些工作负载可能无法移动到新 nodes
   * **解决方案**：审查 pod specs 中的 node affinity 和 anti-affinity 规则，并在需要时调整
4. **Network Policies 和 Security Groups**：
   * **问题**：必要的 network policies 或 security groups 可能未应用到新的 node group
   * **解决方案**：审查并复制 network 配置，包括 security groups、network policies、CIDR ranges
5. **DNS 和 Service Discovery 延迟**：
   * **问题**：node 迁移期间可能出现临时 DNS 解析延迟或 service discovery 问题
   * **解决方案**：优化 CoreDNS 设置，调整 TTL 值，考虑 service mesh
6. **监控和告警缺口**：
   * **问题**：monitoring agents 或 log collectors 可能不会自动安装到新的 node group
   * **解决方案**：使用基于 DaemonSet 的监控工具，在 node group launch template 中包含 agent 安装脚本
7. **缺少回滚计划**：
   * **问题**：如果升级失败，没有回滚方法
   * **解决方案**：不要立即删除现有 node group，保留一段时间，创建状态快照，并记录回滚步骤

**实现示例 (AWS CLI)：**

```bash
# 1. Check current node group information
aws eks describe-nodegroup --cluster-name my-cluster --nodegroup-name blue-nodegroup

# 2. Create new node group (green)
aws eks create-nodegroup \
    --cluster-name my-cluster \
    --nodegroup-name green-nodegroup \
    --scaling-config minSize=3,maxSize=10,desiredSize=5 \
    --subnets subnet-xxxx subnet-yyyy \
    --instance-types t3.large \
    --ami-type AL2_x86_64 \
    --node-role arn:aws:iam::123456789012:role/EKS-NodeInstanceRole \
    --labels environment=prod,app=myapp \
    --tags "k8s.io/cluster-autoscaler/enabled=true,k8s.io/cluster-autoscaler/my-cluster=owned"

# 3. Check node group status
aws eks describe-nodegroup --cluster-name my-cluster --nodegroup-name green-nodegroup

# 4. Cordon existing nodes (using kubectl)
# Get node list
kubectl get nodes -l eks.amazonaws.com/nodegroup=blue-nodegroup

# Cordon each node
kubectl cordon <node-name>

# 5. Drain existing nodes
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# 6. Verify all pods have moved to new nodes
kubectl get pods -o wide

# 7. Delete existing node group
aws eks delete-nodegroup --cluster-name my-cluster --nodegroup-name blue-nodegroup
```

Blue/green 升级可以最大限度减少停机时间并提供回滚能力，但需要额外资源且会增加复杂性。需要充分规划和测试，尤其对于大规模生产环境，建议采用渐进式方法。

</details>
