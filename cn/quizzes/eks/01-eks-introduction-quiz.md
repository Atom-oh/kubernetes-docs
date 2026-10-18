# EKS 入门测验

> **最后更新**：October 12, 2026

本测验用于检验你对 Amazon Elastic Kubernetes Service (EKS) 基本概念和功能的理解。内容涵盖 EKS 架构、组件、管理方法和定价模式等主题。

对于独立的 API 示例，请将 `EXAMPLE_CLUSTER`、`EXAMPLE_REGION`、`EXAMPLE_CONTEXT` 及其他标记变量设置为经过审核的目标值。IRSA 示例需要一个现有的 `EXAMPLE_NAMESPACE`、一个范围限定到所需存储桶/前缀的 `APP_POLICY_ARN`，以及一个使用兼容 IRSA 的 AWS SDK 的应用程序。两个练习分别使用专为其集群设置的 `EKS_INTRO_*` 变量。

## 选择题

1. Amazon EKS (Elastic Kubernetes Service) 的主要优势是什么？
   * A) 无需管理自己的 Kubernetes 控制平面基础设施
   * B) 成本低于其他托管 Kubernetes 服务
   * C) 只能使用 AWS 服务
   * D) 只能在单个可用区中运行

<details>

<summary>显示答案</summary>

**答案：A) 无需管理自己的 Kubernetes 控制平面基础设施**

**说明：** Amazon EKS (Elastic Kubernetes Service) 的主要优势是你无需管理自己的 Kubernetes 控制平面基础设施。由于 AWS 负责管理 Kubernetes 控制平面的可用性和可扩展性，用户可以专注于运行自己的工作负载。

EKS 的主要优势：

* **托管控制平面**：AWS 管理控制平面节点、etcd 集群、API 服务器等。
* **高可用性**：区域级控制平面跨多个可用区部署。工作负载的可用性仍取决于副本、调度位置、容量和依赖项。
* **托管维护**：AWS 为控制平面打补丁。运维人员需规划次要版本升级；根据版本支持策略，也会进行自动升级。
* **与 AWS 服务集成**：与 IAM、VPC、ELB、ECR 等各种 AWS 服务无缝集成。
* **标准 Kubernetes**：符合规范的 Kubernetes API 有助于实现可移植性；但 AWS 专用身份、存储和集成仍需要迁移工作。

其他选项的问题：

* EKS 不一定比其他托管 Kubernetes 服务便宜。实际上，控制平面需要按小时付费。
* EKS 可以运行任何兼容 Kubernetes 的应用程序和服务，而不仅仅是 AWS 服务。
* 区域级 EKS 控制平面跨多个可用区部署；用户必须另外分散部署工作节点和应用程序副本。

</details>

2. Amazon EKS 集群控制平面部署在哪里？
   * A) 在用户的 VPC 内
   * B) 部署在 AWS 管理的账户中，并跨多个可用区
   * C) 在用户选择的单个可用区中
   * D) 在用户的 EC2 实例上运行

<details>

<summary>显示答案</summary>

**答案：B) 部署在 AWS 管理的账户中，并跨多个可用区**

**说明：** Amazon EKS 集群控制平面部署在 AWS 管理的账户中，并跨多个可用区。这是 EKS 作为托管服务的核心特点之一。

EKS 控制平面部署的主要特点：

* **AWS 管理的基础设施**：控制平面运行在 AWS 拥有和管理的账户中。
* **多可用区部署**：区域级 EKS 控制平面组件分布在多个可用区中。
* **自动恢复**：AWS 监控控制平面组件的运行状况，并自动替换出现故障的组件。
* **端点可访问性**：可配置公共访问、私有访问或两者兼有。私有访问还需要 VPC 或已连接网络具备 DNS 和路由配置。
* **自动扩缩**：标准控制平面容量会自动调整；可选的预置控制平面层级需显式选择。

其他选项的问题：

* 控制平面并非部署在用户的 VPC 内。相反，用户的 VPC 与 AWS 管理的 VPC 之间会通过 ENI (弹性网络接口) 建立连接。
* 控制平面部署在多个可用区，而不是单个可用区，以确保高可用性。
* 控制平面运行在 AWS 管理的基础设施上，而不是用户的 EC2 实例上。

</details>

3. 以下哪项对 EKS 计算管理的描述不正确？
   * A) 自行管理的 EC2 节点
   * B) 托管节点组
   * C) Fargate 配置文件
   * D) Bottlerocket 是一种独立的无服务器计算服务

<details>
<summary>显示答案</summary>

**答案：D) Bottlerocket 是一种独立的无服务器计算服务**

Bottlerocket 是一种面向容器节点的操作系统，而不是独立的无服务器执行选项。

1. **自行管理的节点**：客户管理 EC2/Auto Scaling 组、AMI、更新和节点配置。
2. **托管节点组**：AWS 管理预置和替换流程，而运维人员负责启动 AMI/版本更新。仅设置最小和最大大小不会启用基于需求的扩缩。
3. **Fargate**：配置文件用于选择在隔离计算环境中运行的 Pod。请检查 DaemonSet、GPU 和 EBS 等限制。
4. **EKS Auto Mode**：一项真正的 EKS 功能，可自动执行节点预置、扩缩和替换。
5. **混合节点**：将本地/边缘机器连接到 AWS 管理的控制平面。

传统 EC2 节点可以使用单独配置的 Cluster Autoscaler 或自行管理的 Karpenter 来进行基于需求的扩缩。

</details>

4. 基于传统 EC2 的 EKS 节点默认使用什么 CNI？
   * A) Flannel
   * B) Calico
   * C) AWS VPC CNI
   * D) Weave Net

<details>

<summary>显示答案</summary>

**答案：C) AWS VPC CNI**

**说明：** Amazon EKS 集群中默认用于 Pod 网络的 CNI (容器网络接口) 插件是 AWS VPC CNI。此插件将 Amazon VPC 网络直接集成到 Kubernetes Pod 中。

AWS VPC CNI 的主要功能：

* **VPC 原生 IP 地址分配**：Pod 直接从 VPC 获取 IP 地址，与 VPC 中的其他资源处于相同的网络空间。
* **使用辅助 IP 地址**：将连接到每个节点弹性网络接口 (ENI) 的辅助 IP 地址分配给 Pod。
* **安全组集成**：Pod 安全组需要受支持的实例、VPC 资源控制器权限、CNI 配置和 SecurityGroupPolicy。
* **VPC 流日志可见性**：Pod 流量可在 VPC 流日志中查看。
* **利用 AWS 网络功能**：Pod 可以直接使用 VPC 对等连接、Transit Gateway、PrivateLink 等功能。

AWS VPC CNI 是一个开源项目，你可以在 GitHub 上查看代码：https://github.com/aws/amazon-vpc-cni-k8s

EC2 节点上的其他 CNI 需要单独检查兼容性和支持情况。Fargate 和 Auto Mode 不支持任意替换 CNI；混合节点需要兼容的本地 CNI。`hostNetwork` Pod 与节点共享网络。

</details>

5. 如何授予 IAM 身份访问 EKS Kubernetes API 的权限？
   * A) 仅通过 ServiceAccount 对每个 IAM 用户进行身份验证
   * B) 使用访问条目进行 IAM 身份验证，并通过访问策略和/或 Kubernetes RBAC 授权
   * C) EKS IAM 策略会自动授予所有 Kubernetes 资源权限
   * D) 自动将 Cognito 连接到每个集群

<details>
<summary>显示答案</summary>

**答案：B) 使用访问条目进行 IAM 身份验证，并通过访问策略和/或 Kubernetes RBAC 授权**

IAM 对 Kubernetes API 的访问与 Pod 对 AWS API 的访问是两条独立路径。

1. `aws eks get-token` 使用 IAM 凭证创建签名的身份验证令牌。
2. EKS 对 IAM 身份进行身份验证。对于新的访问配置，请使用 **访问条目**。
3. 关联 EKS 访问策略，或者指定 Kubernetes 组并创建 RoleBinding/ClusterRoleBinding。RBAC 和 EKS 授权器会授予累加权限；如果两者都不允许该请求，则请求会被拒绝。
4. 旧版 `aws-auth` ConfigMap 已弃用。迁移时不会自动迁移所有现有映射，因此请在切换到访问条目时逐一验证每个身份及其权限。

IAM 策略控制对 EKS 服务 API 的调用。EKS 访问策略是 Kubernetes 权限模板，而不是 IAM 策略。IRSA/Pod Identity 则单独为工作负载授予 AWS 权限。Kubernetes ServiceAccount 令牌和已配置的 OIDC 提供商也可以用于 Kubernetes 身份验证；IAM 并非唯一的身份验证机制。

</details>

6. 哪个选项使用 OIDC 联合关系，为 Kubernetes ServiceAccount 授予临时 AWS 凭证？
   * A) 使用 EC2 实例配置文件向节点授予 IAM 角色
   * B) 在 Pod 环境变量中嵌入长期 AWS 访问密钥
   * C) 将 IAM 角色关联到 Kubernetes 服务账户 (IRSA)
   * D) 将 AWS 凭证存储为 Kubernetes Secret 并挂载

<details>

<summary>显示答案</summary>

**答案：C) 将 IAM 角色关联到 Kubernetes 服务账户 (IRSA)**

IRSA 通过集群 OIDC 提供商交换 ServiceAccount 令牌，以获取临时 AWS 凭证。请将信任策略限制到相应的命名空间/ServiceAccount 和 `aud=sts.amazonaws.com`。EKS Pod Identity 也可提供临时凭证，且无需单独的 OIDC 提供商；请检查其计算环境、代理和 SDK 要求。本示例演示 IRSA 方法。

IRSA 的主要优势：

* **最小权限原则**：你可以只授予每个应用程序所需的最低权限。
* **权限隔离**：在同一节点上运行的不同 Pod 可以拥有不同的 IAM 权限。
* **简化凭证管理**：无需直接管理 AWS 凭证。
* **增强安全性**：凭证不会硬编码在代码或配置中。

IRSA 设置方法：

1.  将 OpenID Connect (OIDC) 提供商与 EKS 集群关联：

    ```bash
    eksctl utils associate-iam-oidc-provider --cluster="${EXAMPLE_CLUSTER:?}" --region="${EXAMPLE_REGION:?}" --approve
    ```
2.  为服务账户创建 IAM 角色：

    ```bash
    eksctl create iamserviceaccount \
      --name=app-sa \
      --namespace="${EXAMPLE_NAMESPACE:?}" \
      --cluster="${EXAMPLE_CLUSTER:?}" --region="${EXAMPLE_REGION:?}" \
      --attach-policy-arn="${APP_POLICY_ARN:?Use a reviewed policy scoped to the required bucket/prefix}" \
      --approve
    ```
3.  在同一命名空间中的 Pod 内引用该服务账户。以下为模板：将镜像替换为使用兼容 IRSA 的 SDK 的应用程序，然后使用 `-n "$EXAMPLE_NAMESPACE"` 应用：

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: my-pod
    spec:
      serviceAccountName: app-sa
      containers:
      - name: my-container
        image: registry.example.com/team/app:reviewed
    ```

其他选项的问题：

* 能够访问 IMDS 的 Pod 可能会获取节点角色凭证。请限制 IMDS 访问并使用专用于工作负载的角色；IRSA 本身不会阻止此类访问。
* 在 Pod 环境变量中嵌入长期访问密钥会增加泄露和轮换风险。IRSA/Pod Identity 凭证提供程序环境变量属于不同的机制。
* 将 AWS 凭证存储为 Kubernetes Secret 会增加凭证管理负担，并使凭证轮换更加复杂。

</details>

7. 关于 Amazon EKS 集群的日志记录功能，以下哪项说法正确？
   * A) 默认情况下，所有日志都会发送到 CloudWatch Logs
   * B) 可以选择将控制平面日志发送到 CloudWatch Logs
   * C) 只有工作节点日志可以发送到 CloudWatch Logs
   * D) EKS 不提供日志记录功能

<details>

<summary>显示答案</summary>

**答案：B) 可以选择将控制平面日志发送到 CloudWatch Logs**

**说明：** 在 Amazon EKS 集群中，可以选择将控制平面日志发送到 CloudWatch Logs。此功能默认处于禁用状态，用户可以选择启用所需的日志类型。

EKS 控制平面日志记录的主要功能：

* **可选启用**：可以在创建集群时或对现有集群启用。
* **选择日志类型**：可以仅选择所需的日志类型：
  * API 服务器 (api)
  * 审计 (audit)
  * 身份验证器 (authenticator)
  * 控制器管理器 (controllerManager)
  * 调度器 (scheduler)
* **CloudWatch Logs 集成**：所选日志会发送到 AWS CloudWatch Logs，以便存储、分析和监控。
* **成本注意事项**：可能会产生 CloudWatch Logs 日志摄取、保留和查询费用。

启用日志记录的方法：

```bash
# Enable logging using AWS CLI
aws eks update-cluster-config \
    --region "${EXAMPLE_REGION:?}" \
    --name "${EXAMPLE_CLUSTER:?}" \
    --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# Enable logging using eksctl
eksctl utils update-cluster-logging --enable-types api,audit,authenticator,controllerManager,scheduler --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" --approve
```

工作节点日志记录：

* 工作节点日志不包含在 EKS 控制平面日志记录功能中。
* 如需将工作节点日志发送到 CloudWatch Logs，需要安装 CloudWatch 代理或配置 Fluentd/Fluent Bit 等日志解决方案。

其他选项的问题：

* 默认情况下，并非所有日志都会发送到 CloudWatch Logs。用户必须显式启用所需日志。
* 并非只有工作节点日志可以发送到 CloudWatch Logs；控制平面日志也可以发送。
* EKS 确实提供控制平面日志记录功能。

</details>

8. 以下哪项不是 Amazon EKS 集群的成本组成部分？
   * A) EKS 控制平面小时费用
   * B) 工作节点的 EC2 实例成本
   * C) Fargate Pod 执行成本
   * D) Kubernetes 许可费

<details>

<summary>显示答案</summary>

**答案：D) Kubernetes 许可费**

**说明：** Kubernetes 许可费不是 Amazon EKS 集群的成本组成部分。Kubernetes 是由云原生计算基金会 (CNCF) 管理的开源软件，根据 Apache 2.0 许可证可免费使用。因此，使用 EKS 时无需支付单独的 Kubernetes 许可费。

Amazon EKS 集群的实际成本组成部分包括：

1. **EKS 控制平面小时费用**：
   * 标准支持和延长支持的集群费率不同；选择可选的预置控制平面层级还会产生额外费用。
   * EKS 集群是区域级资源；多区域部署需要单独的集群并产生相应费用。
   * 还需单独核算 Auto Mode、EKS Capabilities、混合节点和 AWS 基础设施费用。
2. **工作节点的 EC2 实例成本**：
   * 自行管理或托管节点组使用的 EC2 实例会产生费用。
   * 费用因实例类型、大小、数量和运行时长而异。
   * 可通过预留实例、Savings Plans 和 Spot 实例优化成本。
3. **Fargate Pod 执行成本**：
   * 使用 Fargate 时，根据分配给 Pod 的 vCPU 和内存资源计费。
   * Linux Fargate 计费从下载镜像时开始，按秒取整，且最低计费时长为一分钟；请求的资源会按受支持的配置取整。
   * 请比较总预置容量、利用率和运维工作量；Fargate 和 EC2 并非始终由其中一方更便宜。
4. **其他 AWS 资源成本**：
   * EBS 卷
   * 负载均衡器 (NLB、ALB)
   * CloudWatch 日志和指标
   * NAT Gateway
   * 数据传输

成本优化策略：

* 选择合适的实例类型
* 配置自动扩缩
* 使用 Spot 实例
* 集群自动化和定时扩缩
* 优化资源请求和限制
* 成本监控和分析

</details>

9. 在不使用 Auto Mode 的传统 EKS 集群中，哪个选项可以提供声明式 ALB/NLB 集成？
   * A) 使用内置的 EKS 负载均衡器
   * B) 将 Kubernetes Service 资源与 AWS Load Balancer Controller 集成
   * C) 手动创建和配置 EC2 负载均衡器
   * D) EKS 不支持负载均衡

<details>

<summary>显示答案</summary>

**答案：B) 将 Kubernetes Service 资源与 AWS Load Balancer Controller 集成**

**说明：** 在 Amazon EKS 集群中实现负载均衡的正确方法是将 Kubernetes Service 资源与 AWS Load Balancer Controller 集成。此方法结合了 Kubernetes 的声明式资源管理与 AWS 的负载均衡功能。

在 EKS 中实现负载均衡的方法：

1.  **默认的 LoadBalancer 类型 Service**：

    * 由所选控制器决定负载均衡器。本示例通过 `service.k8s.aws/nlb` 显式选择已安装且获得授权的 AWS LBC；旧版集成则可能创建 CLB。

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: my-service
    spec:
      type: LoadBalancer
      loadBalancerClass: service.k8s.aws/nlb
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: my-app
    ```
2.  **AWS Load Balancer Controller**：

    * 安装 AWS Load Balancer Controller，以使用更高级的功能来管理应用程序负载均衡器 (ALB) 和网络负载均衡器 (NLB)。
    * 可以通过 Ingress 资源预置和配置 ALB。
    * 可以通过注释配置各种负载均衡器属性。

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: my-ingress
      annotations:
        alb.ingress.kubernetes.io/scheme: internet-facing
        alb.ingress.kubernetes.io/target-type: ip
    spec:
      ingressClassName: alb
      rules:
      - http:
          paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: my-service
                port:
                  number: 80
    ```
3.  **Service 注释**：

    * 可以向 Service 添加注释，以指定负载均衡器类型和配置。

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: my-service
      annotations:
        service.beta.kubernetes.io/aws-load-balancer-scheme: internal
        service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    spec:
      type: LoadBalancer
      loadBalancerClass: service.k8s.aws/nlb
      selector:
        app: my-app
      ports:
      - port: 80
        targetPort: 8080
    ```

其他选项的问题：

* Auto Mode 使用不同的类别提供托管负载均衡，包括 `eks.amazonaws.com/nlb`。它不需要在集群内安装 AWS LBC；不要混用两者的类别或不受支持的注释。
* 虽然可以手动创建和配置 EC2 负载均衡器，但这不符合 Kubernetes 的声明式方法，并会使管理更加复杂。
* EKS 完全支持负载均衡。

</details>

10. 以下哪项不是在 Amazon EKS 集群中管理存储的有效方法？
    * A) 使用 EBS CSI 驱动程序预置 EBS 卷
    * B) 使用 EFS CSI 驱动程序挂载 EFS 文件系统
    * C) 在 Fargate Pod 中挂载 EBS 卷
    * D) 使用 FSx for Lustre CSI 驱动程序连接高性能文件系统

<details>

<summary>显示答案</summary>

**答案：C) 在 Fargate Pod 中挂载 EBS 卷**

Fargate 无法挂载 EBS 卷。传统 EC2 节点使用已安装并配置 IAM 权限的 EBS CSI 驱动程序。Auto Mode 通过 `ebs.csi.eks.amazonaws.com` 提供托管 EBS 预置，与传统的 `ebs.csi.aws.com` 驱动程序不同。

在 Amazon EKS 集群中管理存储的实际方法包括：

1.  **EBS CSI 驱动程序**：

    * 支持将 Amazon EBS (Elastic Block Store) 卷连接到 Kubernetes Pod。
    * 适用于需要块存储的应用程序（例如数据库）。
    * 支持动态预置、通过快照控制器创建快照，以及在 StorageClass 允许时扩展卷。
    * EBS 的作用范围是可用区。ReadWriteOnce 表示可从一个节点进行读写挂载，而不是仅供一个 Pod 使用；该节点上的多个 Pod 可以使用此卷。访问模式不会定义卷所在的可用区。

    ```yaml
    # StorageClass example
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc
    provisioner: ebs.csi.aws.com
    volumeBindingMode: WaitForFirstConsumer
    parameters:
      type: gp3
      encrypted: "true"
    ```
2.  **EFS CSI 驱动程序**：

    * 支持将 Amazon EFS (Elastic File System) 挂载到 Kubernetes Pod。
    * 适用于需要由多个 Pod 同时访问的共享文件系统。
    * 可跨多个可用区访问 (ReadWriteMany 访问模式)。
    * 适用于 Web 服务器、CMS、CI/CD 流水线等。

    ```yaml
    # StorageClass example
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: efs-sc
    provisioner: efs.csi.aws.com
    parameters:
      provisioningMode: efs-ap
      fileSystemId: fs-0123456789abcdef0
      directoryPerms: "700"
    ```
3.  **FSx for Lustre CSI 驱动程序**：

    * 支持将 Amazon FSx for Lustre 连接到 Kubernetes Pod。
    * 适用于高性能计算、机器学习和大数据分析等高性能工作负载。
    * 可提供高吞吐量和低延迟。

    ```yaml
    # StorageClass example
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: fsx-sc
    provisioner: fsx.csi.aws.com
    parameters:
      subnetId: subnet-0123456789abcdef0
      securityGroupIds: sg-0123456789abcdef0
      deploymentType: PERSISTENT_1
      automaticBackupRetentionDays: "1"
      dailyAutomaticBackupStartTime: "00:00"
      perUnitStorageThroughput: "200"
    ```
   在 PVC 的 `spec.resources.requests.storage` 中指定容量（例如 `1200Gi`），而不是使用 `storageCapacity` StorageClass 参数。请检查具体部署所需的容量增量、子网/安全组、Lustre 客户端兼容性和驱动程序 IAM 权限。

4. **其他存储选项**：
   * 通过 CSI 驱动程序或 S3 挂载工具使用 Amazon S3 (Simple Storage Service)
   * Amazon FSx for Windows File Server
   * Amazon FSx for NetApp ONTAP
   * 第三方存储解决方案 (Portworx、Rook 等)

存储管理最佳实践：

* 根据工作负载需求选择合适的存储类型
* 配置 StorageClass 以实现动态预置
* 制定备份和恢复策略
* 监控存储性能
* 选择合适的存储类别和大小以优化成本

</details>

## 动手练习

### 练习 1：创建和配置 EKS 集群

**场景：** 你是公司的 DevOps 工程师，需要为开发团队设置 Amazon EKS 集群。该集群用于开发环境，应在提供所有必要功能的同时保持成本效益。

**要求：**

1. 创建一个经济高效的 EKS 集群
2. 配置合适的节点组
3. 设置基本监控
4. 配置对集群的 kubectl 访问

**解决方案：**

<details>
<summary>显示解决方案</summary>

运行这些部署命令会创建需要付费的 AWS 资源。本次审计期间未执行这些命令。请准备好 Bash、当前版本的 AWS CLI v2、kubectl 1.36 和 Helm，并使用[官方 eksctl 安装流程](https://eksctl.io/installation/)检查操作系统/CPU 架构和校验和。本示例依据 eksctl 0.230.0 架构和 EKS 1.36 进行了审核；它不是经过验证的生产配置。

请在同一个 shell 中运行这些步骤，并在命令失败时停止。将 `EKS_INTRO_ADMIN_CIDR` 设置为经批准的客户端实际外部 IPv4 CIDR，通常为 `/32`。新集群使用私有节点/私有 API 访问，并限制公共 API 访问范围。单个 NAT gateway 适用于开发实验环境，并非生产环境的可用性设计。集群创建者的管理员访问权限仅用于引导此专用实验环境。

**1. 创建专用集群**

```bash
# Use a dedicated nonproduction AWS account/role and an approved region.
eksctl version  # Example tool baseline: 0.230.0
aws --version
kubectl version --client
helm version

EKS_INTRO_DIR=$(mktemp -d /tmp/eks-intro.XXXXXX)
: "${EKS_INTRO_DIR:?}"
EKS_INTRO_CLUSTER=$(basename "$EKS_INTRO_DIR" | tr '[:upper:].' '[:lower:]-')
EKS_INTRO_REGION=us-west-2
: "${EKS_INTRO_ADMIN_CIDR:?Set your approved client egress IPv4 CIDR, normally /32}"
EKS_INTRO_KUBECONFIG="$EKS_INTRO_DIR/kubeconfig"
unset EKS_INTRO_CLUSTER_ARN EKS_INTRO_POLICY_ARN
aws sts get-caller-identity

cat > "$EKS_INTRO_DIR/eks-cluster.yaml" << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ${EKS_INTRO_CLUSTER}
  region: ${EKS_INTRO_REGION}
  version: "1.36"
  tags:
    docs-lab: ${EKS_INTRO_CLUSTER}
iam:
  withOIDC: true
accessConfig:
  authenticationMode: API
  bootstrapClusterCreatorAdminPermissions: true
vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs: ["${EKS_INTRO_ADMIN_CIDR}"]
  nat:
    gateway: Single
managedNodeGroups:
- name: ng-1
  amiFamily: AmazonLinux2023
  instanceType: t3.medium
  privateNetworking: true
  disableIMDSv1: true
  disablePodIMDS: true
  desiredCapacity: 2
  minSize: 1
  maxSize: 3
cloudWatch:
  clusterLogging:
    enableTypes: ["api", "audit", "authenticator", "controllerManager", "scheduler"]
EOF

# Inspect the file, account, allowed CIDR and projected costs before provisioning.
cat "$EKS_INTRO_DIR/eks-cluster.yaml"
eksctl create cluster -f "$EKS_INTRO_DIR/eks-cluster.yaml" \
  --kubeconfig "$EKS_INTRO_KUBECONFIG" &&
  EKS_INTRO_CLUSTER_ARN=$(aws eks describe-cluster --name "$EKS_INTRO_CLUSTER" \
    --region "$EKS_INTRO_REGION" --query cluster.arn --output text)
: "${EKS_INTRO_CLUSTER_ARN:?Cluster creation/verification did not complete}"
```

如果创建失败，请检查此唯一名称对应的 CloudFormation 堆栈/资源并清理，然后再重复使用该名称。`minSize`/`maxSize` 仅设置上下限；它们不会安装基于需求的节点自动扩缩器。t3.medium 仅为示例，需审核其容量、CPU 积分和区域价格。

**2. 专用 kubeconfig 和连接检查**

```bash
aws eks update-kubeconfig --name "${EKS_INTRO_CLUSTER:?}" \
  --region "${EKS_INTRO_REGION:?}" --kubeconfig "${EKS_INTRO_KUBECONFIG:?}"
intro_kubectl() {
  kubectl --kubeconfig "${EKS_INTRO_KUBECONFIG:?}" "$@"
}
intro_kubectl get nodes
intro_kubectl cluster-info
```

**3. 基本资源指标**

Metrics Server 0.9.x 支持 Kubernetes 1.34 及更高版本。此工具提供资源指标，不提供日志记录或长期监控。请检查 kubelet 证书和网络可达性，且不要禁用 TLS 验证。

```bash
intro_kubectl get pods -n kube-system

# Fresh lab cluster only: do not overwrite an existing managed installation.
curl -fL https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.9.0/components.yaml \
  -o "${EKS_INTRO_DIR:?}/metrics-server.yaml" &&
  intro_kubectl apply -f "$EKS_INTRO_DIR/metrics-server.yaml"
intro_kubectl rollout status deployment/metrics-server -n kube-system --timeout=180s
intro_kubectl top nodes
```

**4. 安装 AWS Load Balancer Controller**

策略、控制器和 chart 均固定为 3.5.0。请使用其 IRSA 角色，而不是向每个节点授予无关的附加组件权限。显式设置区域/VPC，避免依赖 IMDS 发现。请单独检查子网标签、安全组和服务配额。

```bash
: "${EKS_INTRO_CLUSTER_ARN:?Use the new lab cluster}"
curl -fL https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v3.5.0/docs/install/iam_policy.json \
  -o "${EKS_INTRO_DIR:?}/lbc-policy.json" || exit 1
# Inspect the pinned policy before creating this lab-owned IAM policy.
EKS_INTRO_POLICY_ARN=$(aws iam create-policy \
  --policy-name "${EKS_INTRO_CLUSTER:?}-lbc" \
  --policy-document "file://$EKS_INTRO_DIR/lbc-policy.json" \
  --query Policy.Arn --output text)
: "${EKS_INTRO_POLICY_ARN:?Policy creation failed}"

# iam.withOIDC created the cluster OIDC provider in step1.
eksctl create iamserviceaccount \
  --cluster="$EKS_INTRO_CLUSTER" --region="${EKS_INTRO_REGION:?}" \
  --namespace=kube-system --name=aws-load-balancer-controller \
  --attach-policy-arn="$EKS_INTRO_POLICY_ARN" --approve

EKS_INTRO_VPC_ID=$(aws eks describe-cluster --name "$EKS_INTRO_CLUSTER" \
  --region "$EKS_INTRO_REGION" --query cluster.resourcesVpcConfig.vpcId --output text)
: "${EKS_INTRO_VPC_ID:?}"
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
helm --kubeconfig "${EKS_INTRO_KUBECONFIG:?}" install aws-load-balancer-controller \
  eks/aws-load-balancer-controller --version 3.5.0 -n kube-system \
  --set clusterName="$EKS_INTRO_CLUSTER" \
  --set region="$EKS_INTRO_REGION" --set vpcId="$EKS_INTRO_VPC_ID" \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller \
  --wait --timeout 5m
```

**5. 检查集群状态**

```bash
intro_kubectl get nodes -o wide
intro_kubectl get pods -n kube-system
intro_kubectl get events --sort-by='.lastTimestamp'
intro_kubectl cluster-info
```

**6. 通过本地端口转发检查基本应用**

```bash
intro_kubectl create namespace intro-smoke
intro_kubectl -n intro-smoke create deployment nginx --image=nginx:1.30.6-alpine
intro_kubectl -n intro-smoke rollout status deployment/nginx --timeout=180s
intro_kubectl -n intro-smoke expose deployment nginx --port=80 --type=ClusterIP
intro_kubectl -n intro-smoke get deployment,service
# Run in a separate terminal using the same dedicated kubeconfig.
kubectl --kubeconfig "${EKS_INTRO_KUBECONFIG:?}" -n intro-smoke \
  port-forward --address 127.0.0.1 service/nginx 8080:80
```

端口转发运行时，打开 `http://127.0.0.1:8080`；按 Ctrl-C 停止转发。下一个练习将配置外部 ALB 访问。完成两个练习后，请按照清理流程操作；预期行为和潜在节省并非审计实测结果。

</details>

### 练习 2：在 EKS 集群中部署应用程序并公开 Service

**场景：** 你的团队开发了一个基于微服务架构的 Web 应用程序。你需要将此应用程序部署到 EKS 集群，并配置外部访问。

**要求：**

1. 部署前端和后端服务
2. 配置服务间通信
3. 通过 Ingress Controller 配置外部访问
4. 设置基本扩缩

**解决方案：**

<details>
<summary>显示解决方案</summary>

使用练习 1 中的专用集群和 shell 变量、AWS LBC/IngressClass `alb`，以及运行正常的 Metrics Server。此 HTTP 演示仅提供公开的虚拟响应，并将 ALB 访问限制为所选客户端 CIDR。它不实现应用程序身份验证、TLS 或生产环境负载验证。

**1. 创建命名空间**

```bash
: "${EKS_INTRO_CLUSTER_ARN:?Complete exercise1 first}"
unset EKS_INTRO_WEB_UID
EKS_INTRO_WEB_UID=$(intro_kubectl create namespace web-app -o jsonpath='{.metadata.uid}')
: "${EKS_INTRO_WEB_UID:?Stop if this namespace already exists}"
```

**2. 配置后端**

配置 NGINX 监听 port80，并为包括 `/api` 在内的路径返回虚拟 JSON。

```bash
cat > "${EKS_INTRO_DIR:?}/backend-deployment.yaml" << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: backend-config
  namespace: web-app
data:
  default.conf: |
    server {
        listen 80;
        location / {
            default_type application/json;
            return 200 '{"service":"backend","example":true}\n';
        }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: web-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      automountServiceAccountToken: false
      containers:
      - name: backend
        image: nginx:1.30.6-alpine
        ports:
        - name: http
          containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
        readinessProbe:
          httpGet:
            path: /
            port: http
        volumeMounts:
        - name: config
          mountPath: /etc/nginx/conf.d
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: backend-config
---
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: web-app
spec:
  selector:
    app: backend
  ports:
  - port: 80
    targetPort: http
EOF
intro_kubectl apply -f "$EKS_INTRO_DIR/backend-deployment.yaml"
```

**3. 配置前端和服务间通信**

标准 NGINX 镜像不会使用 `BACKEND_URL`。此处明确配置 NGINX，将 `/proxy-api/` 代理到 `backend-service`，从而建立实际的服务间通信路径。

```bash
cat > "${EKS_INTRO_DIR:?}/frontend-deployment.yaml" << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: frontend-config
  namespace: web-app
data:
  default.conf: |
    server {
        listen 80;
        location /proxy-api/ {
            proxy_pass http://backend-service/;
        }
        location / {
            default_type text/plain;
            return 200 'frontend demo\n';
        }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: web-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      automountServiceAccountToken: false
      containers:
      - name: frontend
        image: nginx:1.30.6-alpine
        ports:
        - name: http
          containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
        readinessProbe:
          httpGet:
            path: /
            port: http
        volumeMounts:
        - name: config
          mountPath: /etc/nginx/conf.d
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: frontend-config
---
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  namespace: web-app
spec:
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: http
EOF
intro_kubectl apply -f "$EKS_INTRO_DIR/frontend-deployment.yaml"
```

**4. 创建 AWS LBC Ingress**

ALB 不会自动移除 `/api`；此后端会直接处理该路径。`/` 和 `/proxy-api/` 会转发到前端。

```bash
cat > "${EKS_INTRO_DIR:?}/ingress.yaml" << EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-app-ingress
  namespace: web-app
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /
    alb.ingress.kubernetes.io/inbound-cidrs: ${EKS_INTRO_ADMIN_CIDR:?}
spec:
  ingressClassName: alb
  rules:
  - http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
EOF
intro_kubectl apply -f "$EKS_INTRO_DIR/ingress.yaml"
```

**5. 配置 HPA**

CPU 利用率是相对于 requests 计算的。HPA 会调整 Pod 副本数，而不是节点数；它需要 Metrics Server 和充足的空闲节点容量。

```bash
cat > "${EKS_INTRO_DIR:?}/hpa.yaml" << 'EOF'
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: frontend-hpa
  namespace: web-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: web-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
EOF
intro_kubectl apply -f "$EKS_INTRO_DIR/hpa.yaml"
```

**6. 检查路由和状态**

ALB 主机名并不能证明其目标运行正常。如果请求失败，请检查事件、目标运行状况、安全组和客户端 CIDR。

```bash
intro_kubectl -n web-app rollout status deployment/backend --timeout=180s
intro_kubectl -n web-app rollout status deployment/frontend --timeout=180s
intro_kubectl -n web-app get deployments,services,ingress,hpa
intro_kubectl -n web-app describe ingress web-app-ingress
ALB_ADDRESS=$(intro_kubectl -n web-app get ingress web-app-ingress \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
: "${ALB_ADDRESS:?Wait for ALB provisioning and inspect events}"
curl --fail --show-error --connect-timeout 5 --max-time 20 "http://$ALB_ADDRESS/"
curl --fail --show-error --connect-timeout 5 --max-time 20 "http://$ALB_ADDRESS/api"
curl --fail --show-error --connect-timeout 5 --max-time 20 "http://$ALB_ADDRESS/proxy-api/"
```

**7. 观察有限负载下的行为**

此示例负载不保证 CPU 利用率超过目标值或触发 HPA。静态 NGINX 响应可能只使用很少的 CPU，而对前端根路径的请求不会增加后端负载。请观察指标、HPA 状态和 Pending Pod，以判断实际扩缩情况。

```bash
# Only target the lab ALB whose ownership and health you checked above.
: "${ALB_ADDRESS:?}"
ab -n 1000 -c 10 -s 10 "http://$ALB_ADDRESS/"
intro_kubectl -n web-app get hpa
intro_kubectl -n web-app top pods
intro_kubectl -n web-app get events --sort-by='.lastTimestamp'
# Optional observation; Ctrl-C stops watching, not the HPA.
intro_kubectl -n web-app get hpa -w
```

</details>

### 清理练习资源

确认账户、ARN 和标签均指向专用实验集群。请先删除应用程序负载均衡器，再删除控制器，并等待资源最终清理完成。如果超时，请调查控制器错误，不要移除 finalizer。

```bash
: "${EKS_INTRO_CLUSTER_ARN:?Use only the dedicated cluster created in exercise1}"
EKS_INTRO_CLEANUP_READY=false
current_arn=$(aws eks describe-cluster --name "${EKS_INTRO_CLUSTER:?}" \
  --region "${EKS_INTRO_REGION:?}" --query cluster.arn --output text)
current_tag=$(aws eks describe-cluster --name "$EKS_INTRO_CLUSTER" \
  --region "$EKS_INTRO_REGION" --query 'cluster.tags."docs-lab"' --output text)
if [[ "$current_arn" = "$EKS_INTRO_CLUSTER_ARN" && "$current_tag" = "$EKS_INTRO_CLUSTER" ]]; then
  # Keep the controller running until it removes ALB resources/finalizers.
  intro_kubectl -n web-app delete ingress web-app-ingress --ignore-not-found --wait=true --timeout=180s &&
    intro_kubectl delete namespace web-app intro-smoke --ignore-not-found --wait=true --timeout=180s &&
    EKS_INTRO_CLEANUP_READY=true
else
  printf 'Ownership check failed; stop cleanup and inspect the selected account/cluster\n' >&2
fi
```

只有在完成所有权验证并成功删除 Ingress/命名空间后，才能继续操作。删除策略前，请确认 IAM 角色堆栈已删除且策略已解除关联。

```bash
if [[ ${EKS_INTRO_CLEANUP_READY:-false} = true ]]; then
  helm --kubeconfig "${EKS_INTRO_KUBECONFIG:?}" uninstall aws-load-balancer-controller -n kube-system
  eksctl delete iamserviceaccount --cluster="${EKS_INTRO_CLUSTER:?}" \
    --region="${EKS_INTRO_REGION:?}" --namespace=kube-system --name=aws-load-balancer-controller --approve --wait
  # Wait for the related IAM-role stack deletion to finish before deleting its policy.
  aws iam list-entities-for-policy --policy-arn "${EKS_INTRO_POLICY_ARN:?}"
  # Continue only when no attachment remains.
  aws iam delete-policy --policy-arn "$EKS_INTRO_POLICY_ARN" &&
    eksctl delete cluster --config-file="${EKS_INTRO_DIR:?}/eks-cluster.yaml" --wait
else
  printf 'Complete ownership and load balancer cleanup checks first\n' >&2
fi
```

请确认 CloudFormation 删除完成，并检查是否仍有负载均衡器、安全组、NAT、EBS 和日志保留成本。请单独决定是否保留或删除 CloudWatch 日志组。不要假定部分创建的资源或这些步骤之外的资源会自动清理。实验完成后，请删除专用目录中的清单、策略和 kubeconfig。

## 高级主题

以下是有关 Amazon EKS 高级主题的问题。本节用于检验你对 EKS 高级功能和集成的理解。

1. 配置 Amazon EKS Fargate 配置文件时，以下哪项描述正确？
   * A) Fargate 配置文件根据特定命名空间和标签指定应在 Fargate 上运行的 Pod
   * B) Fargate 配置文件会自动在 Fargate 上运行所有 Pod
   * C) Fargate 配置文件将 Pod 执行限制为特定 EC2 实例类型
   * D) Fargate 配置文件为整个集群设置资源配额

<details>

<summary>显示答案</summary>

**答案：A) Fargate 配置文件根据特定命名空间和标签指定应在 Fargate 上运行的 Pod**

**说明：** Amazon EKS Fargate 配置文件是一项配置，它根据特定命名空间和标签指定哪些 Pod 应在 Fargate 上运行。这样可以配置混合架构，同时使用无服务器容器执行环境和基于 EC2 的节点。

Fargate 配置文件的主要功能：

* **选择性执行**：只有符合配置文件定义条件的 Pod 才会在 Fargate 上运行，而不是所有 Pod。
* **命名空间和标签选择器**：根据特定的命名空间和标签组合选择 Pod。
* **子网指定**：可以指定 Pod 运行所在的私有子网。
* **IAM 角色**：Pod 执行角色供 Fargate 基础设施使用，例如用于拉取镜像。应用程序容器需要自己的 IRSA 角色才能访问 AWS API。

创建 Fargate 配置文件的示例：

```bash
eksctl create fargateprofile \
  --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --name my-fargate-profile \
  --namespace my-namespace \
  --labels app=my-app
```

基于 YAML 的 Fargate 配置文件定义：

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
fargateProfiles:
  - name: my-fargate-profile
    selectors:
      - namespace: my-namespace
        labels:
          app: my-app
      - namespace: another-namespace
```

使用 Fargate 时的注意事项：

* Fargate 不支持 DaemonSet。
* 无法运行特权容器。
* 不支持 HostNetwork 和 HostPort。
* 不支持 GPU 工作负载。
* 按 Pod 计费，因此需要进行成本规划。
* 可以通过静态预置的 EFS 卷提供持久化存储。Fargate 不支持 EBS 卷和 EFS 动态预置。

其他选项的问题：

* Fargate 配置文件不会自动在 Fargate 上运行所有 Pod；只有符合选择器条件的 Pod 才会在 Fargate 上运行。
* Fargate 配置文件与 EC2 实例类型无关；Fargate 是一种无服务器容器执行环境。
* Fargate 配置文件不会设置集群范围的资源配额。资源配额通过 Kubernetes ResourceQuota 管理。

</details>

2. 应如何规划 EKS 升级？
   * A) 先将节点升级到目标版本，之后再检查兼容性
   * B) 先准备兼容性和当前版本信息，然后按控制平面 → 节点的顺序操作，并协调每项附加组件的更新
   * C) 将所有附加组件盲目升级到最新版本，作为全部准备工作
   * D) 同时更改所有组件

<details>
<summary>显示答案</summary>

**答案：B) 先准备兼容性和当前版本信息，然后按控制平面 → 节点的顺序操作，并协调每项附加组件的更新**

首先检查当前集群/节点版本、升级洞察、已移除的 API、webhook/CRD/附加组件兼容性、子网剩余 IP 和恢复计划。在升级到下一个次要版本之前，先将落后于当前控制平面版本的节点升级到该版本。

**1. 控制平面**

每次仅升一个次要版本。当前 kubelet 不能高于 API 服务器版本，且最多可以落后三个次要版本；不过，EKS 建议在升级前后使版本保持一致。最大允许版本偏差并非长期运行的目标。

```bash
# Inspect the current version and node versions before choosing the next minor.
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --query 'cluster.{version:version,status:status}' --output table
kubectl --context "${EXAMPLE_CONTEXT:?}" get nodes

# Choose one interface, after prerequisite checks and workload testing.
aws eks update-cluster-version --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?Select the next supported minor}"
# Alternative:
# eksctl upgrade cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" --version "$NEXT_MINOR_VERSION" --approve

# Use the update ID returned above. Proceed only after status is Successful.
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "${CONTROL_PLANE_UPDATE_ID:?}" --query update.status
```

**2. 节点**

控制平面更新成功后，启动托管节点组更新，并检查其更新状态、节点就绪情况和 kubelet 版本。传统节点组不会随控制平面自动更新。运维人员需更新自行管理的节点/混合节点；要使用新版本，需重新创建 Fargate Pod。Auto Mode 节点会由 AWS 逐步更新。

```bash
aws eks update-nodegroup-version --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}"
# Alternative:
# eksctl upgrade nodegroup --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" --name "$EXAMPLE_NODEGROUP" --kubernetes-version "$NEXT_MINOR_VERSION"
```

**3. 附加组件和客户端**

提前检查与当前版本和目标版本的兼容性。有些 CNI、webhook 或控制器组件需要在控制平面之前更新到兼容版本，因此附加组件并非总是在最后一步更新。控制平面更新后，将其余附加组件、Cluster Autoscaler 和 kubectl 更新到受支持的版本，并逐项验证。

```bash
aws eks describe-addon-versions --region "${EXAMPLE_REGION:?}" --addon-name vpc-cni \
  --kubernetes-version "${NEXT_MINOR_VERSION:?}" \
  --query 'addons[].addonVersions[].addonVersion' --output table

# Select a compatible EKS add-on build after reviewing configuration changes.
aws eks update-addon --cluster-name "${EXAMPLE_CLUSTER:?}" --region "$EXAMPLE_REGION" \
  --addon-name vpc-cni --addon-version "${REVIEWED_ADDON_VERSION:?}" \
  --resolve-conflicts PRESERVE
```

`PRESERVE` 会保留用户配置，但不能保证兼容性。请检查 PDB、剩余容量和优雅终止情况；不要使用强制标志掩盖故障。验证每个阶段，并准备可恢复的应用程序/数据备份。AWS 控制平面备份不能替代客户的数据恢复计划。

EKS 现在支持在符合条件的升级完成后七天内回滚到先前的次要版本。此功能受节点、附加组件、API 变更和支持策略等条件限制，且不会自动恢复应用程序数据。请遵循[升级流程](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)和[回滚条件](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)。

</details>

3. 以下哪项不是 Amazon EKS 中 VPC CNI 插件的主要功能？
   * A) 为 Pod 分配 VPC IP 地址
   * B) 在 Pod 级别应用安全组
   * C) 加密 Pod 之间的网络流量
   * D) 通过前缀委派扩展 IP 地址

<details>

<summary>显示答案</summary>

**答案：C) 加密 Pod 之间的网络流量**

Amazon VPC CNI 不会全面加密 Pod 之间的流量。请配置应用程序 TLS/mTLS，或使用明确受支持的网格/CNI 加密功能。NetworkPolicy 只能过滤流量，不能加密流量。

Amazon VPC CNI 插件的实际主要功能包括：

1. **为 Pod 分配 VPC IP 地址**：
   * 普通 Pod 会获得 VPC IP；`hostNetwork` Pod 与节点共享网络。
   * 这样 Pod 可以直接与 VPC 中的其他资源通信。
   * Pod IP 可在 VPC 内路由，因此无需复杂的覆盖网络。
2. **在 Pod 级别应用安全组**：
   * 通过 SecurityGroupsForPods 功能，可以将 AWS 安全组应用到单个 Pod。
   * 这样可以在 Pod 级别实施细粒度网络安全策略。
   *   配置示例：

       ```yaml
       apiVersion: vpcresources.k8s.aws/v1beta1
       kind: SecurityGroupPolicy
       metadata:
         name: my-security-group-policy
         namespace: default
       spec:
         podSelector:
           matchLabels:
             app: my-app
         securityGroups:
           groupIds:
             - sg-0123456789abcdef0
       ```
3. **通过前缀委派扩展 IP 地址**：
   * 默认情况下，每个节点可分配给 Pod 的 IP 地址数量有限，且因实例类型而异。
   * 使用前缀委派功能，可以为每个节点分配 `/28` CIDR 块（16 个 IP），增加可用 IP 地址数量。
   * 该功能会增加每个 ENI 的地址容量，但会消耗现有子网地址。它要求有连续的空闲前缀，且不会增加新的子网容量。
4. **自定义网络**：
   * 可以将 Pod 放置在特定子网中。
   * 可以使用多个网络接口配置 Pod 网络。
5. **Kubernetes 主机网络**：
   * `hostNetwork` 使用节点网络；这是 Kubernetes Pod 设置，不是 CNI 加密或隔离功能。
   * 适用于网络性能至关重要的工作负载。

启用 VPC CNI 功能前，请分别检查其前提条件。

| 设置 | 必要检查 |
| --- | --- |
| `ENABLE_PREFIX_DELEGATION` | 受支持的实例/CNI 版本、连续空闲的 `/28` 块、kubelet max-pods 和新节点过渡计划 |
| `ENABLE_POD_ENI` | 受支持的 trunk/branch ENI 实例、VPC 资源控制器权限、SecurityGroupPolicy 和 DNS/安全组规则 |
| `AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG` | IPv4、同一 VPC/AZ 中的 Pod 子网/安全组、节点 ENIConfig 选择和空闲 IP |

仅启用一个标记就可能导致新旧 Pod 的行为不同，或导致 IP 分配失败。请遵循官方过渡流程，避免与 EKS 托管附加组件的配置冲突。不要将此传统 EC2 DaemonSet 方法直接用于 Auto Mode、Fargate 或混合节点。

```bash
# Inspect current non-secret CNI flags; this does not enable any feature.
kubectl --context "${EXAMPLE_CONTEXT:?}" -n kube-system get daemonset aws-node \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="aws-node")].env}{"\n"}'
```


如需实现 Pod 之间的网络流量加密，可以考虑以下替代方案：

* App Mesh 支持已于 September 30, 2026 结束；现有用户必须迁移。
* 实施 Istio 服务网格
* 使用 Cilium 的透明加密功能
* 在应用程序级别实施 TLS/mTLS

</details>

4. 如何为开发者 IAM 角色授予命名空间范围的 Kubernetes 只读访问权限？
   * A) 将 Kubernetes Role 直接附加到 IAM 用户
   * B) 使用 EKS 访问条目将 IAM 角色映射到 Kubernetes 组，并配置 RBAC 绑定
   * C) 仅将 S3 策略附加到集群 IAM 角色
   * D) 仅通过应用程序 ServiceAccount 的 IRSA 设置向开发者授予 kubectl 访问权限

<details>
<summary>显示答案</summary>

**答案：B) 使用 EKS 访问条目将 IAM 角色映射到 Kubernetes 组，并配置 RBAC 绑定**

对于新的 IAM 访问配置，请使用 **EKS 访问条目**。集群身份验证模式必须为 `API` 或 `API_AND_CONFIG_MAP`。更改现有集群模式前，请准备映射迁移方案和管理员恢复路径。`aws-auth` 已弃用，并不是唯一的映射机制。

此示例将现有开发者 IAM 角色关联到 `dev-readers`。IAM 身份和访问条目不会自动创建 Kubernetes RBAC 对象。

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --query cluster.accessConfig.authenticationMode

aws eks create-access-entry --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --principal-arn "${DEV_ROLE_ARN:?Existing developer IAM role}" \
  --type STANDARD --kubernetes-groups dev-readers
```

管理员在现有的 `dev` 命名空间中应用此 Role 和 RoleBinding。它授予 Pod/Deployment 读取权限，但不授予 Secret 或修改权限。创建工作负载的权限可能会使用户能够使用命名空间中的 Secret，因此需要单独审核。

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: dev
  name: dev-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-readers
  namespace: dev
subjects:
- kind: Group
  name: dev-readers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: dev-reader
  apiGroup: rbac.authorization.k8s.io
```

使用有权代入该角色的身份创建专用 kubeconfig，并验证实际权限。除非其他 RBAC 授权或 EKS 访问策略增加权限，否则第一个检查应允许访问，第二个检查应拒绝访问。

```bash
aws eks update-kubeconfig --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --role-arn "${DEV_ROLE_ARN:?}" --kubeconfig "${DEV_KUBECONFIG:?Use a dedicated file}"
kubectl --kubeconfig "$DEV_KUBECONFIG" auth can-i get pods -n dev
kubectl --kubeconfig "$DEV_KUBECONFIG" auth can-i get secrets -n dev
```

另一种方法是将命名空间范围的 EKS 访问策略关联到此条目。访问策略和 RBAC 授权是累加的；仅附加 IAM 策略不会授予 Kubernetes 权限。IRSA/Pod Identity 为 Pod 调用 AWS API 提供另一条独立路径。不要向普通开发者授予 `system:masters`，也不要覆盖整个 `aws-auth` ConfigMap。

</details>

5. 关于 EKS 版本支持，以下哪项描述正确？
   * A) 所有版本都会无限期获得支持
   * B) 所有版本的支持都会在 12 个月后结束
   * C) 始终只支持最新版本加之前三个版本
   * D) EKS 发布后提供 14 个月标准支持，之后提供 12 个月付费延长支持

<details>
<summary>显示答案</summary>

**答案：D) EKS 发布后提供 14 个月标准支持，之后提供 12 个月付费延长支持**

EKS 次要版本从其 **EKS 发布日期**起获得 **14 个月的标准支持**，之后获得 **12 个月的付费延长支持**。计时不会从上游发布日期开始。

* 截至 October 12, 2026 的官方版本列表：标准支持版本为 **1.34–1.37**，延长支持版本为 **1.31–1.33**。EKS 1.37 于 October 1, 2026 开始提供，晚于其上游版本 August 26 的发布日期。
* 默认启用延长支持。选择 `STANDARD` 升级策略即可选择退出延长支持，并使集群在标准支持结束后受自动升级约束。
* 延长支持结束后，AWS 会自动将控制平面升级到受支持的版本。无法保证具体执行时间，因此运维人员应主动规划升级。
* 托管/自行管理/混合节点不会仅因控制平面自动升级而更新。请单独规划 Fargate Pod 替换和附加组件更新；Auto Mode 节点遵循托管更新机制。
* 受支持的版本会获得安全补丁；不支持无限期保留每个版本。已结束支持的版本无法用于创建新集群。

请在实际区域中检查发布日历和版本信息。对附加组件元数据执行 grep 不能代替集群版本支持列表。

```bash
aws eks describe-cluster-versions --region "${EXAMPLE_REGION:?}" --output table
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" --region "$EXAMPLE_REGION" \
  --query 'cluster.{version:version,upgradePolicy:upgradePolicy}' --output json
```

制定升级计划，检查已移除的 API 和兼容性，在非生产环境中测试，准备应用程序/数据恢复方案，并且每次只升级一个次要版本。EKS 至少提供三个标准支持版本，但没有固定的“仅支持最新版本加之前三个版本”规则。

</details>


## 官方参考资料和验证范围

- [EKS 版本生命周期](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [EKS 访问条目](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [Pod Identity 和 IRSA](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html)
- [Load Balancer Controller](https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html)
- [Auto Mode 负载均衡](https://docs.aws.amazon.com/eks/latest/userguide/auto-configure-nlb.html)
- [EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)
- [FSx CSI 配置和 PVC 容量](https://docs.aws.amazon.com/eks/latest/userguide/fsx-csi-create.html)
- [Fargate 限制](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
- [前缀委派](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses.html)
- [自定义网络](https://docs.aws.amazon.com/eks/latest/userguide/cni-custom-network.html)
- [EKS 定价](https://aws.amazon.com/eks/pricing/)
- [Fargate 定价](https://aws.amazon.com/fargate/pricing/)
- [eksctl 0.230.0 架构](https://github.com/eksctl-io/eksctl/blob/v0.230.0/pkg/apis/eksctl.io/v1alpha5/assets/schema.json)
- [LBC 3.5.0 安装](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/deploy/installation.md)
- [Metrics Server 0.9.0 兼容性](https://github.com/kubernetes-sigs/metrics-server/blob/v0.9.0/README.md)

本内容是根据官方文档和发布架构进行的静态审核。未执行集群/IAM/负载均衡器预置、应用程序部署、升级/回滚、NGINX 运行、负载测试或成本测量。示例的预期行为并非实测结果。
