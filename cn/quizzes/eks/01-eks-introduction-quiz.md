# EKS 简介测验

本测验用于测试你对 Amazon Elastic Kubernetes Service (EKS) 基本概念和功能的理解。内容涵盖 EKS 架构、组件、管理方法和定价模型等主题。

## 选择题

1. Amazon EKS (Elastic Kubernetes Service) 的主要优势是什么？
   * A) 无需管理自己的 Kubernetes control plane 基础设施
   * B) 成本低于其他托管 Kubernetes 服务
   * C) 只能使用 AWS 服务
   * D) 只能在单个 availability zone 中运行

<details>

<summary>显示答案</summary>

**答案：A) 无需管理自己的 Kubernetes control plane 基础设施**

**解释：** Amazon EKS (Elastic Kubernetes Service) 的主要优势是你无需管理自己的 Kubernetes control plane 基础设施。由于 AWS 负责管理 Kubernetes control plane 的可用性和可扩展性，用户可以专注于运行自己的工作负载。

EKS 的主要优势：

* **托管 Control Plane**：AWS 管理 control plane nodes、etcd cluster、API server 等。
* **高可用性**：control plane 部署在多个 availability zones 中，消除单点故障。
* **自动升级和补丁**：AWS 管理 Kubernetes 版本升级和安全补丁。
* **与 AWS 服务集成**：与 IAM、VPC、ELB、ECR 等多种 AWS 服务无缝集成。
* **标准 Kubernetes**：提供完全兼容的 Kubernetes，防止厂商锁定。

其他选项的问题：

* EKS 不一定比其他托管 Kubernetes 服务更便宜。实际上，control plane 会按小时收费。
* EKS 可以运行任何兼容 Kubernetes 的应用程序和服务，而不仅仅是 AWS 服务。
* 为实现高可用性，EKS clusters 默认部署在多个 availability zones 中。

</details>

2. Amazon EKS cluster control plane 部署在哪里？
   * A) 在用户的 VPC 内
   * B) 部署在 AWS 托管账户的多个 availability zones 中
   * C) 在用户选择的单个 availability zone 中
   * D) 运行在用户的 EC2 instances 上

<details>

<summary>显示答案</summary>

**答案：B) 部署在 AWS 托管账户的多个 availability zones 中**

**解释：** Amazon EKS cluster control plane 部署在 AWS 托管账户的多个 availability zones 中。这是 EKS 作为托管服务的核心方面之一。

EKS control plane 部署的主要特征：

* **AWS 托管基础设施**：control plane 运行在 AWS 拥有并管理的账户中。
* **Multi-AZ 部署**：部署在至少 3 个 availability zones 中以实现高可用性。
* **自动恢复**：AWS 监控 control plane 组件的运行状况，并自动替换故障组件。
* **Endpoint 可访问性**：control plane endpoints 可以配置为公开访问，或仅在 VPC 内访问。
* **自动扩展**：control plane 容量会根据 cluster 负载自动调整。

其他选项的问题：

* control plane 不部署在用户的 VPC 内。相反，会通过 ENI (Elastic Network Interface) 在用户的 VPC 与 AWS 托管 VPC 之间建立连接。
* control plane 部署在多个 availability zones 中，而不是单个 availability zone，以确保高可用性。
* control plane 运行在 AWS 托管基础设施上，而不是用户的 EC2 instances 上。

</details>

3. 以下哪一项不是 Amazon EKS 中管理 worker nodes 的有效方法？
   * A) Self-managed node groups
   * B) Managed node groups
   * C) Fargate profiles
   * D) EKS automatic node provisioning

<details>

<summary>显示答案</summary>

**答案：D) EKS automatic node provisioning**

**解释：** “EKS automatic node provisioning” 不是 Amazon EKS 官方提供的 worker node 管理方法。此功能并不存在。

Amazon EKS 中实际用于管理 worker nodes 的方法包括：

1. **Self-managed node groups**：
   * 用户直接创建和管理 EC2 instances。
   * 可以通过 Auto Scaling groups 进行管理。
   * 提供对 node 配置的完全控制。
   * 运维开销最高。
2. **Managed node groups**：
   * AWS 管理 node 预置和生命周期。
   * node 升级、补丁和调整会自动化执行。
   * 基于 EC2 Auto Scaling groups。
   * 使用标准 Amazon Linux 或 Bottlerocket AMI。
3. **Fargate profiles**：
   * 一种 serverless 计算选项，无需管理单独的 EC2 instances。
   * 按 Pod 预置计算资源。
   * 基础设施管理开销最低。
   * 存在某些限制（例如不支持 DaemonSet、某些资源限制）。

对于 node 自动扩展，EKS 支持 Kubernetes Cluster Autoscaler 或 Karpenter 等工具，但没有名为 “EKS automatic node provisioning” 的官方功能。

</details>

4. Amazon EKS clusters 默认使用哪个 CNI plugin 进行 Pod 网络？
   * A) Flannel
   * B) Calico
   * C) AWS VPC CNI
   * D) Weave Net

<details>

<summary>显示答案</summary>

**答案：C) AWS VPC CNI**

**解释：** Amazon EKS clusters 中默认用于 Pod 网络的 CNI (Container Network Interface) plugin 是 AWS VPC CNI。该 plugin 将 Amazon VPC 网络与 Kubernetes Pods 直接集成。

AWS VPC CNI 的主要功能：

* **VPC-native IP 地址分配**：Pods 直接从 VPC 获取 IP 地址，与 VPC 中的其他资源处于同一网络空间。
* **Secondary IP 地址使用**：将连接到每个 node 的 Elastic Network Interface (ENI) 的 secondary IP 地址分配给 Pods。
* **Security group 集成**：security groups 可以应用到 Pod 级别（SecurityGroupsForPods 功能）。
* **VPC flow log 可见性**：Pod 流量在 VPC flow logs 中可见。
* **利用 AWS 网络功能**：Pods 可以直接使用 VPC peering、Transit Gateway、PrivateLink 等功能。

AWS VPC CNI 是一个开源项目，你可以在 GitHub 上查看代码：https://github.com/aws/amazon-vpc-cni-k8s

其他 CNI plugins（Flannel、Calico、Weave Net 等）可以安装在 EKS 上，但 AWS VPC CNI 是默认提供的。

</details>

5. 在 Amazon EKS 中管理 Kubernetes 资源认证和授权的方法是什么？
   * A) 仅使用 Kubernetes service accounts
   * B) 集成 AWS IAM 和 Kubernetes RBAC
   * C) EKS 专用权限管理系统
   * D) 通过 AWS Cognito 进行用户认证

<details>

<summary>显示答案</summary>

**答案：B) 集成 AWS IAM 和 Kubernetes RBAC**

**解释：** Amazon EKS 通过集成 AWS IAM (Identity and Access Management) 和 Kubernetes RBAC (Role-Based Access Control) 来管理 Kubernetes 资源的认证和授权。这种集成方式结合了 AWS 强大的身份管理能力和 Kubernetes 的细粒度权限控制。

主要功能：

* **IAM 认证**：使用 AWS IAM 凭证向 Kubernetes API server 进行认证。
* **aws-auth ConfigMap**：将 IAM roles 或 users 映射到 Kubernetes users 和 groups。
* **RBAC 授权**：使用 Kubernetes RBAC 系统控制 cluster 内的权限。
* **IRSA (IAM Roles for Service Accounts)**：将 IAM roles 关联到 Kubernetes service accounts，使 Pods 能够安全访问 AWS 服务。

工作方式：

1. 用户使用 `aws eks get-token` 命令（通过 AWS CLI 或 AWS SDK）获取 Kubernetes API server 的认证 token。
2. 该 token 使用 IAM 凭证签名。
3. Kubernetes API server 使用 AWS IAM authenticator 验证 token。
4. 根据 aws-auth ConfigMap 中的映射，用户被分配为 Kubernetes users 和 groups。
5. Kubernetes RBAC 系统根据授予这些 users 或 groups 的权限允许或拒绝请求。

其他选项的问题：

* 仅使用 Kubernetes service accounts 会限制与 AWS 服务的集成。
* EKS 没有单独的专用权限管理系统；它将标准 Kubernetes RBAC 与 AWS IAM 集成。
* AWS Cognito 不直接用于 EKS 认证，尽管它可以配置为 OIDC provider。

</details>

6. 在 Amazon EKS cluster 中，Pods 访问 AWS 服务（例如 S3、DynamoDB）的推荐方法是什么？
   * A) 使用 EC2 instance profiles 向 nodes 授予 IAM roles
   * B) 将 AWS 凭证作为环境变量直接注入 Pods
   * C) 将 IAM roles 关联到 Kubernetes service accounts (IRSA)
   * D) 将 AWS 凭证存储为 Kubernetes Secrets 并挂载它们

<details>

<summary>显示答案</summary>

**答案：C) 将 IAM roles 关联到 Kubernetes service accounts (IRSA)**

**解释：** 在 Amazon EKS cluster 中，Pods 访问 AWS 服务的推荐方法是将 IAM roles 关联到 Kubernetes service accounts。此功能称为 IRSA (IAM Roles for Service Accounts)，并在 Pod 级别提供细粒度权限。

IRSA 的主要优势：

* **最小权限原则**：你可以只授予每个应用程序所需的最小权限。
* **权限隔离**：运行在同一 node 上的不同 Pods 可以拥有不同的 IAM 权限。
* **简化凭证管理**：无需直接管理 AWS 凭证。
* **增强安全性**：凭证不会硬编码在代码或配置中。

如何设置 IRSA：

1.  将 OpenID Connect (OIDC) provider 与 EKS cluster 关联：

    ```bash
    eksctl utils associate-iam-oidc-provider --cluster=<cluster-name> --approve
    ```
2.  为 service account 创建 IAM role：

    ```bash
    eksctl create iamserviceaccount \
      --name=<service-account-name> \
      --namespace=<namespace> \
      --cluster=<cluster-name> \
      --attach-policy-arn=arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
      --approve
    ```
3.  在 Pod manifest 中引用 service account：

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: my-pod
    spec:
      serviceAccountName: <service-account-name>
      containers:
      - name: my-container
        image: my-image
    ```

其他选项的问题：

* 使用 EC2 instance profiles 会让同一 node 上的所有 Pods 拥有相同权限，违反最小权限原则。
* 将 AWS 凭证作为环境变量注入会带来凭证暴露风险，并使凭证轮换变得困难。
* 将 AWS 凭证存储为 Kubernetes Secrets 会增加凭证管理负担，并使凭证轮换复杂化。

</details>

7. 关于 Amazon EKS clusters 的日志功能，哪项陈述是正确的？
   * A) 默认情况下所有日志都会发送到 CloudWatch Logs
   * B) control plane logs 可以选择性地发送到 CloudWatch Logs
   * C) 只有 worker node logs 可以发送到 CloudWatch Logs
   * D) EKS 不提供日志功能

<details>

<summary>显示答案</summary>

**答案：B) control plane logs 可以选择性地发送到 CloudWatch Logs**

**解释：** 在 Amazon EKS clusters 中，control plane logs 可以选择性地发送到 CloudWatch Logs。此功能默认禁用，用户可以选择启用所需的日志类型。

EKS control plane logging 的主要功能：

* **可选启用**：可以在创建 cluster 时启用，也可以在现有 clusters 上启用。
* **日志类型选择**：你可以只选择需要的日志类型：
  * API server (api)
  * Audit (audit)
  * Authenticator (authenticator)
  * Controller manager (controllerManager)
  * Scheduler (scheduler)
* **CloudWatch Logs 集成**：选定的日志会发送到 AWS CloudWatch Logs，用于存储、分析和监控。
* **成本考虑**：日志存储适用 CloudWatch Logs 定价。

如何启用日志：

```bash
# Enable logging using AWS CLI
aws eks update-cluster-config \
    --region <region> \
    --name <cluster-name> \
    --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# Enable logging using eksctl
eksctl utils update-cluster-logging --enable-types api,audit,authenticator,controllerManager,scheduler --cluster <cluster-name> --region <region>
```

Worker node logging：

* Worker node logs 不包含在 EKS control plane logging 功能中。
* 要将 worker node logs 发送到 CloudWatch Logs，需要安装 CloudWatch agent 或配置 Fluentd/Fluent Bit 等日志解决方案。

其他选项的问题：

* 并非所有日志默认都会发送到 CloudWatch Logs。用户必须显式启用它们。
* 并不是只有 worker node logs 可以发送到 CloudWatch Logs；control plane logs 也可以发送。
* EKS 确实提供 control plane logging 功能。

</details>

8. 以下哪一项不是 Amazon EKS cluster 的成本组成部分？
   * A) EKS control plane 小时费用
   * B) worker nodes 的 EC2 instance 成本
   * C) Fargate Pod 执行成本
   * D) Kubernetes 许可证费用

<details>

<summary>显示答案</summary>

**答案：D) Kubernetes 许可证费用**

**解释：** Kubernetes 许可证费用不是 Amazon EKS clusters 的成本组成部分。Kubernetes 是由 Cloud Native Computing Foundation (CNCF) 管理的开源软件，并可根据 Apache 2.0 license 免费使用。因此，使用 EKS 时没有单独的 Kubernetes 许可证费用。

Amazon EKS clusters 的实际成本组成部分包括：

1. **EKS control plane 小时费用**：
   * 每个 EKS cluster 会收取固定小时费用（例如每小时 $0.10）。
   * 无论 cluster 规模或工作负载如何，此成本都是固定的。
   * 如果跨多个 regions，则按 region 收费。
2. **worker nodes 的 EC2 instance 成本**：
   * 在 self-managed 或 managed node groups 中使用的 EC2 instances 会产生成本。
   * 成本会根据 instance type、大小、数量和运行时间而变化。
   * 可以通过 Reserved Instances、Savings Plans 和 Spot Instances 优化成本。
3. **Fargate Pod 执行成本**：
   * 使用 Fargate 时，会根据分配给 Pods 的 vCPU 和内存资源收费。
   * 成本根据 Pod 运行时间按秒计算。
   * 没有 node 管理开销，但通常比基于 EC2 的 nodes 更昂贵。
4. **其他 AWS 资源成本**：
   * EBS volumes
   * Load balancers (NLB, ALB)
   * CloudWatch logs and metrics
   * NAT Gateway
   * Data transfer

成本优化策略：

* 选择合适的 instance types
* 配置 auto-scaling
* 使用 Spot Instances
* Cluster 自动化和计划扩展
* 优化 resource requests 和 limits
* 成本监控和分析

</details>

9. 在 Amazon EKS cluster 中实现 load balancing 的正确方法是什么？
   * A) 使用内置的 EKS load balancer
   * B) 将 Kubernetes Service 资源与 AWS Load Balancer Controller 集成
   * C) 手动创建和配置 EC2 load balancers
   * D) EKS 不支持 load balancing

<details>

<summary>显示答案</summary>

**答案：B) 将 Kubernetes Service 资源与 AWS Load Balancer Controller 集成**

**解释：** 在 Amazon EKS cluster 中实现 load balancing 的正确方法是将 Kubernetes Service 资源与 AWS Load Balancer Controller 集成。这种方法结合了 Kubernetes 的声明式资源管理和 AWS 的 load balancing 能力。

在 EKS 中实现 load balancing 的方法：

1.  **默认 LoadBalancer 类型 Service**：

    * 在 Kubernetes 中创建 `LoadBalancer` 类型的 Service，默认会预置 Classic Load Balancer (CLB) 或 Network Load Balancer (NLB)。

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: my-service
    spec:
      type: LoadBalancer
      ports:
      - port: 80
        targetPort: 8080
      selector:
        app: my-app
    ```
2.  **AWS Load Balancer Controller**：

    * 安装 AWS Load Balancer Controller，以使用更高级的功能来管理 Application Load Balancer (ALB) 和 Network Load Balancer (NLB)。
    * 可以通过 Ingress 资源预置和配置 ALB。
    * 可以通过 annotations 配置各种 load balancer 属性。

    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      name: my-ingress
      annotations:
        kubernetes.io/ingress.class: alb
        alb.ingress.kubernetes.io/scheme: internet-facing
        alb.ingress.kubernetes.io/target-type: ip
    spec:
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
3.  **Service annotations**：

    * 可以向 services 添加 annotations，以指定 load balancer 类型和配置。

    ```yaml
    apiVersion: v1
    kind: Service
    metadata:
      name: my-service
      annotations:
        service.beta.kubernetes.io/aws-load-balancer-type: nlb
        service.beta.kubernetes.io/aws-load-balancer-internal: "true"
    spec:
      type: LoadBalancer
      # ...
    ```

其他选项的问题：

* EKS 中没有单独的“内置 EKS load balancer”组件。Load balancing 通过 Kubernetes Service 资源与 AWS load balancers 的集成来提供。
* 虽然可以手动创建和配置 EC2 load balancers，但这不符合 Kubernetes 的声明式方法，并会使管理复杂化。
* EKS 完全支持 load balancing。

</details>

10. 以下哪一项不是 Amazon EKS cluster 中管理存储的有效方法？
    * A) 使用 EBS CSI driver 预置 EBS volumes
    * B) 使用 EFS CSI driver 挂载 EFS file systems
    * C) 通过 EKS built-in storage manager 自动预置 volumes
    * D) 使用 FSx for Lustre CSI driver 连接高性能 file systems

<details>

<summary>显示答案</summary>

**答案：C) 通过 EKS built-in storage manager 自动预置 volumes**

**解释：** “EKS built-in storage manager” 是不存在的功能。Amazon EKS 没有用于自动 volume 预置的内置 storage manager；存储通过 CSI (Container Storage Interface) drivers 管理。

Amazon EKS clusters 中实际的存储管理方法包括：

1.  **EBS CSI driver**：

    * 允许将 Amazon EBS (Elastic Block Store) volumes 连接到 Kubernetes Pods。
    * 适用于需要 block storage 的应用程序（数据库等）。
    * 支持 dynamic provisioning、snapshots 和 volume resizing。
    * 仅可在单个 availability zone 内访问（ReadWriteOnce access mode）。

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
2.  **EFS CSI driver**：

    * 允许将 Amazon EFS (Elastic File System) 挂载到 Kubernetes Pods。
    * 适用于需要多个 Pods 同时访问的共享 file systems。
    * 可跨多个 availability zones 访问（ReadWriteMany access mode）。
    * 适用于 web servers、CMS、CI/CD pipelines 等。

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
3.  **FSx for Lustre CSI driver**：

    * 允许将 Amazon FSx for Lustre 连接到 Kubernetes Pods。
    * 适用于 high-performance computing、machine learning 和 big data analytics 等高性能工作负载。
    * 提供高吞吐量和低延迟。

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
      storageCapacity: "1200"
    ```
4. **其他存储选项**：
   * 通过 CSI drivers 或 S3 mounters 使用 Amazon S3 (Simple Storage Service)
   * Amazon FSx for Windows File Server
   * Amazon FSx for NetApp ONTAP
   * 第三方存储解决方案（Portworx、Rook 等）

存储管理最佳实践：

* 根据工作负载需求选择合适的存储类型
* 为 dynamic provisioning 配置 StorageClass
* 建立备份和恢复策略
* 监控存储性能
* 选择合适的 storage classes 和大小以优化成本

</details>

## 动手练习

### 练习 1：创建和配置 EKS Cluster

**场景：** 你是公司的一名 DevOps engineer，需要为开发团队设置 Amazon EKS cluster。该 cluster 用于开发环境，应具备成本效益，同时提供所有必要功能。

**需求：**

1. 创建一个具备成本效益的 EKS cluster
2. 配置合适的 node groups
3. 设置基本监控
4. 配置对 cluster 的 kubectl 访问

**解决方案：**

<details>

<summary>显示解决方案</summary>

**1. 使用 eksctl 创建 EKS Cluster**

```bash
# Install eksctl (if not already installed)
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
eksctl version

# Create cluster
cat << EOF > eks-cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: dev-cluster
  region: us-west-2
  version: "1.28"

managedNodeGroups:
  - name: ng-1
    instanceType: t3.medium
    desiredCapacity: 2
    minSize: 1
    maxSize: 3
    iam:
      withAddonPolicies:
        imageBuilder: true
        autoScaler: true
        externalDNS: true
        certManager: true
        appMesh: false
        ebs: true
        fsx: false
        efs: false
        albIngress: true
        xRay: false
        cloudWatch: true

cloudWatch:
  clusterLogging:
    enableTypes: ["api", "audit", "authenticator", "controllerManager", "scheduler"]
EOF

eksctl create cluster -f eks-cluster.yaml
```

**2. 配置并验证 kubectl**

```bash
# Update kubectl configuration
aws eks update-kubeconfig --name dev-cluster --region us-west-2

# Verify cluster connection
kubectl get nodes
kubectl cluster-info
```

**3. 验证基本监控组件**

```bash
# Check basic system pods
kubectl get pods -n kube-system

# Install metrics server (if not provided by default)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Verify metrics server operation
kubectl get deployment metrics-server -n kube-system
kubectl top nodes
```

**4. 安装 AWS Load Balancer Controller**

```bash
# Create IAM policy
curl -o iam-policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json
aws iam create-policy \
    --policy-name AWSLoadBalancerControllerIAMPolicy \
    --policy-document file://iam-policy.json

# Set up IRSA
eksctl create iamserviceaccount \
  --cluster=dev-cluster \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn=arn:aws:iam::<AWS_ACCOUNT_ID>:policy/AWSLoadBalancerControllerIAMPolicy \
  --override-existing-serviceaccounts \
  --approve

# Install controller with Helm
helm repo add eks https://aws.github.io/eks-charts
helm repo update
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=dev-cluster \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

**5. 检查 Cluster 状态**

```bash
# Check node status
kubectl get nodes -o wide

# Check system pod status
kubectl get pods -n kube-system

# Check cluster events
kubectl get events --sort-by='.lastTimestamp'

# Check cluster info
kubectl cluster-info
```

**6. 部署测试应用程序**

```bash
# Deploy simple nginx
kubectl create deployment nginx --image=nginx
kubectl expose deployment nginx --port=80 --type=LoadBalancer

# Verify deployment
kubectl get deployment nginx
kubectl get service nginx
```

通过本练习，你学习了如何创建具备成本效益的 EKS cluster、设置基本监控，并配置 load balancer controller 以将应用程序暴露到外部。t3.medium instance type 是适合开发环境的具备成本效益的选择，auto-scaling 设置允许 nodes 按需扩展。

</details>

### 练习 2：在 EKS Cluster 中部署应用程序并暴露 Services

**场景：** 你的团队已经开发了一个基于 microservices 架构的 web 应用程序。你需要将该应用程序部署到 EKS cluster，并配置它以便从外部访问。

**需求：**

1. 部署 frontend 和 backend services
2. 配置 services 之间的通信
3. 通过 ingress controller 配置外部访问
4. 设置基本扩展

**解决方案：**

<details>

<summary>显示解决方案</summary>

**1. 创建 Namespace**

```bash
kubectl create namespace web-app
kubectl config set-context --current --namespace=web-app
```

**2. 部署 Backend Service**

```yaml
# backend-deployment.yaml
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
      containers:
      - name: backend
        image: nginx:alpine  # Replace with actual backend image
        ports:
        - containerPort: 8080
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
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
    targetPort: 8080
```

```bash
kubectl apply -f backend-deployment.yaml
```

**3. 部署 Frontend Service**

```yaml
# frontend-deployment.yaml
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
      containers:
      - name: frontend
        image: nginx:alpine  # Replace with actual frontend image
        ports:
        - containerPort: 80
        env:
        - name: BACKEND_URL
          value: "http://backend-service"
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
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
    targetPort: 80
```

```bash
kubectl apply -f frontend-deployment.yaml
```

**4. 创建 Ingress 资源（使用 AWS ALB Ingress Controller）**

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-app-ingress
  namespace: web-app
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /
spec:
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
```

```bash
kubectl apply -f ingress.yaml
```

**5. 配置 Horizontal Pod Autoscaling (HPA)**

```yaml
# hpa.yaml
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
```

```bash
kubectl apply -f hpa.yaml
```

**6. 检查 Deployment 状态**

```bash
# Check deployment status
kubectl get deployments -n web-app

# Check service status
kubectl get services -n web-app

# Check ingress status
kubectl get ingress -n web-app

# Check HPA status
kubectl get hpa -n web-app

# Get ALB address
kubectl get ingress web-app-ingress -n web-app -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

**7. 负载测试并验证扩展**

```bash
# Get ALB address
ALB_ADDRESS=$(kubectl get ingress web-app-ingress -n web-app -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Load test (requires separate tool)
# Example: Using Apache Bench
ab -n 10000 -c 100 http://$ALB_ADDRESS/

# Verify scaling
kubectl get hpa -n web-app -w
```

通过本练习，你学习了如何将 microservices 架构应用程序部署到 EKS cluster、使用 AWS ALB Ingress Controller 将其暴露到外部，并通过 HPA 配置 auto-scaling。resource requests 和 limits 已适当设置以确保高效的资源使用，并通过 ingress rules 实现了基于路径的路由。

</details>

## 高级主题

以下是关于高级 Amazon EKS 主题的问题。本节测试你对高级 EKS 功能和集成的理解。

1. 在 Amazon EKS 中配置 Fargate profile 时，哪项描述是正确的？
   * A) Fargate profiles 根据特定 namespaces 和 labels 指定 Pods 应在 Fargate 上运行
   * B) Fargate profiles 会自动在 Fargate 上运行所有 Pods
   * C) Fargate profiles 将 Pod 执行限制到特定 EC2 instance types
   * D) Fargate profiles 为整个 cluster 设置 resource quotas

<details>

<summary>显示答案</summary>

**答案：A) Fargate profiles 根据特定 namespaces 和 labels 指定 Pods 应在 Fargate 上运行**

**解释：** Amazon EKS Fargate profile 是一种配置，用于根据特定 namespaces 和 labels 指定哪些 Pods 应在 Fargate 上运行。这允许配置同时使用 serverless container 执行环境和基于 EC2 的 nodes 的混合架构。

Fargate profiles 的主要功能：

* **选择性执行**：只有匹配 profile 中定义条件的 Pods 会在 Fargate 上运行，并非所有 Pods。
* **Namespace 和 label selectors**：基于特定 namespace 和 label 组合选择 Pods。
* **Subnet 指定**：你可以指定 Pods 将运行的 private subnets。
* **IAM role**：指定 Fargate Pods 的 IAM execution role。

Fargate profile 创建示例：

```bash
eksctl create fargateprofile \
  --cluster my-cluster \
  --name my-fargate-profile \
  --namespace my-namespace \
  --labels app=my-app
```

基于 YAML 的 Fargate profile 定义：

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

* Fargate 不支持 DaemonSets。
* Privileged containers 无法运行。
* 不支持 HostNetwork 和 HostPort。
* 不支持 GPU workloads。
* 按 Pod 产生成本，因此需要进行成本规划。
* 存储仅限于 ephemeral storage（可通过 EFS 使用 persistent volumes）。

其他选项的问题：

* Fargate profiles 不会自动在 Fargate 上运行所有 Pods；只有匹配 selectors 的 Pods 才会在 Fargate 上运行。
* Fargate profiles 与 EC2 instance types 无关；Fargate 是 serverless container 执行环境。
* Fargate profiles 不设置 cluster 范围的 resource quotas。Resource quotas 通过 Kubernetes ResourceQuota 管理。

</details>

2. 在 Amazon EKS 中执行 cluster 升级时，正确顺序是什么？
   * A) Worker node upgrade -> Control plane upgrade -> Add-on upgrade
   * B) Control plane upgrade -> Worker node upgrade -> Add-on upgrade
   * C) Add-on upgrade -> Control plane upgrade -> Worker node upgrade
   * D) 同时升级所有组件

<details>

<summary>显示答案</summary>

**答案：B) Control plane upgrade -> Worker node upgrade -> Add-on upgrade**

**解释：** Amazon EKS cluster 升级的正确顺序是先升级 control plane，然后升级 worker nodes，最后升级 add-ons。此顺序遵循 Kubernetes 的版本兼容模型，并最大限度减少升级过程中潜在问题。

**1. Control Plane Upgrade**

* control plane 充当 cluster 的大脑，应首先升级。
* Kubernetes 的设计允许 control plane 最多比 nodes 领先 2 个 minor versions。
* control plane 升级可以通过 AWS Management Console、AWS CLI 或 eksctl 执行。

```bash
# Control plane upgrade using AWS CLI
aws eks update-cluster-version --name my-cluster --kubernetes-version 1.28

# Control plane upgrade using eksctl
eksctl upgrade cluster --name=my-cluster --version=1.28 --approve
```

**2. Worker Node Upgrade**

* control plane 升级完成后，升级 worker nodes。
* 对于 managed node groups，可以通过 AWS Management Console、AWS CLI 或 eksctl 完成升级。
* 对于 self-managed nodes，必须使用新的 AMIs 替换 nodes。

```bash
# Managed node group upgrade
aws eks update-nodegroup-version --cluster-name my-cluster --nodegroup-name my-nodegroup

# Managed node group upgrade using eksctl
eksctl upgrade nodegroup --cluster=my-cluster --name=my-nodegroup
```

**3. Add-on Upgrade**

* 最后，升级 cluster add-ons（kube-proxy、CoreDNS、Amazon VPC CNI 等）。
* Add-ons 被设计为与特定 Kubernetes 版本兼容，因此应在 control plane 和 node 升级之后升级。

```bash
# Add-on upgrade using AWS CLI
aws eks update-addon --cluster-name my-cluster --addon-name vpc-cni --addon-version v1.12.0-eksbuild.1

# Add-on upgrade using eksctl
eksctl update addon --name vpc-cni --version v1.12.0-eksbuild.1 --cluster my-cluster
```

**升级最佳实践：**

* 升级前检查 cluster 状态并备份
* 先在测试环境中测试升级
* 考虑 blue/green deployment 策略
* 配置 PodDisruptionBudget，以在升级期间最大限度减少工作负载中断
* 每次升级一个 minor version
* 升级后验证工作负载和系统组件

其他选项的问题：

* 在 control plane 之前升级 worker nodes 可能导致版本兼容性问题。
* 先升级 add-ons 可能导致新的 add-on versions 与旧 Kubernetes version 不兼容。
* 同时升级所有组件风险很高，并且如果出现问题，很难识别原因。

</details>

3. 以下哪一项不是 Amazon EKS 中 VPC CNI plugin 的关键功能？
   * A) 向 Pods 分配 VPC IP 地址
   * B) 在 Pod 级别应用 security groups
   * C) 加密 Pods 之间的网络流量
   * D) 通过 prefix delegation 扩展 IP 地址

<details>

<summary>显示答案</summary>

**答案：C) 加密 Pods 之间的网络流量**

**解释：** Amazon VPC CNI (Container Network Interface) plugin 不会自动加密 Pods 之间的网络流量。Pod-to-pod 流量加密不是 VPC CNI 的基本功能，需要 service meshes（例如 AWS App Mesh、Istio）或 network policy solutions（例如 Calico、Cilium）等额外工具。

Amazon VPC CNI plugin 的实际关键功能包括：

1. **向 Pods 分配 VPC IP 地址**：
   * 每个 Pod 都会在 VPC 内获得唯一 IP 地址。
   * 这允许 Pods 与 VPC 中的其他资源直接通信。
   * Pod IPs 在 VPC 内可路由，消除了复杂 overlay networks 的需求。
2. **在 Pod 级别应用 security groups**：
   * AWS security groups 可以通过 SecurityGroupsForPods 功能应用到单个 Pods。
   * 这允许在 Pod 级别实施细粒度网络安全策略。
   *   示例配置：

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
3. **通过 prefix delegation 扩展 IP 地址**：
   * 默认情况下，每个 node 可分配给 Pods 的 IP 地址数量有限（因 instance type 而异）。
   * 使用 prefix delegation 功能，可以为每个 node 分配 /28 CIDR blocks（16 个 IPs），增加可用 IP 地址数量。
   * 这解决了高密度部署场景中的 IP 地址短缺问题。
4. **Custom networking**：
   * Pods 可以放置在特定 subnets 中。
   * Pod 网络可以使用多个 network interfaces 配置。
5. **Host networking 集成**：
   * Pods 可以直接使用 host network stack。
   * 适用于网络性能至关重要的工作负载。

VPC CNI 配置示例：

```bash
# Enable prefix delegation
kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true

# Enable security group pods feature
kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true

# Enable custom networking
kubectl set env daemonset aws-node -n kube-system AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true
```

要实现 Pods 之间的网络流量加密，请考虑以下替代方案：

* 使用带 TLS 的 AWS App Mesh
* 实施 Istio service mesh
* 使用 Cilium 的透明加密功能
* 在应用程序级别实施 TLS/mTLS

</details>

4. 在 Amazon EKS 中为 cluster authentication 配置基于 IAM role 的 access control (RBAC) 的正确方法是什么？
   * A) 直接将 Kubernetes RBAC roles 分配给 IAM users
   * B) 在 aws-auth ConfigMap 中配置 IAM role 和 Kubernetes group 映射
   * C) 直接将 IAM policies 附加到 EKS cluster
   * D) 将 IAM roles 关联到 Kubernetes service accounts

<details>

<summary>显示答案</summary>

**答案：B) 在 aws-auth ConfigMap 中配置 IAM role 和 Kubernetes group 映射**

**解释：** 在 Amazon EKS 中，为 cluster authentication 配置基于 IAM role 的 access control (RBAC) 的正确方法是使用 `aws-auth` ConfigMap 配置 IAM roles 与 Kubernetes groups 之间的映射。此方法允许将 AWS IAM 凭证与 Kubernetes RBAC 系统集成。

**aws-auth ConfigMap 的工作方式：**

1. EKS 使用 AWS IAM Authenticator 对 API 请求进行认证。
2. `aws-auth` ConfigMap 将 IAM entities（users 或 roles）映射到 Kubernetes users 和 groups。
3. Kubernetes RBAC 系统向这些 users 和 groups 授予权限。

**aws-auth ConfigMap 配置示例：**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: arn:aws:iam::123456789012:role/EksAdminRole
      username: eks-admin
      groups:
        - system:masters
    - rolearn: arn:aws:iam::123456789012:role/DevTeamRole
      username: dev-team
      groups:
        - dev-group
  mapUsers: |
    - userarn: arn:aws:iam::123456789012:user/admin-user
      username: admin
      groups:
        - system:masters
    - userarn: arn:aws:iam::123456789012:user/read-only-user
      username: read-only
      groups:
        - read-only-group
```

**Kubernetes RBAC role 和 binding 配置：**

```yaml
# Create developer role
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: dev
  name: developer
rules:
- apiGroups: ["", "apps", "batch"]
  resources: ["pods", "deployments", "jobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]

---
# Bind role to developer group
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-binding
  namespace: dev
subjects:
- kind: Group
  name: dev-group
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer
  apiGroup: rbac.authorization.k8s.io
```

**使用 eksctl 进行 IAM 和 RBAC 配置：**

```bash
# Add IAM role mapping
eksctl create iamidentitymapping \
  --cluster my-cluster \
  --arn arn:aws:iam::123456789012:role/EksAdminRole \
  --username eks-admin \
  --group system:masters

# Add IAM user mapping
eksctl create iamidentitymapping \
  --cluster my-cluster \
  --arn arn:aws:iam::123456789012:user/admin-user \
  --username admin \
  --group system:masters
```

**最佳实践：**

* 应用最小权限原则
* 优先使用 IAM roles，而不是单个 IAM users
* 按 namespace 分离权限
* 定期审查访问权限
* 谨慎授予 cluster administrator 权限（system:masters）

其他选项的问题：

* Kubernetes RBAC roles 不能直接分配给 IAM users。由于 IAM 和 Kubernetes 是不同系统，必须通过 aws-auth ConfigMap 进行映射。
* 直接将 IAM policies 附加到 EKS cluster 与 cluster 内的 RBAC 权限无关。IAM policies 控制对 cluster 本身的 API call 权限。
* 将 IAM roles 关联到 Kubernetes service accounts (IRSA) 是为了让 Pods 访问 AWS 服务，与 cluster authentication 和 authorization 目的不同。

</details>

5. 关于 Amazon EKS 的 Kubernetes 版本支持策略，哪项描述是正确的？
   * A) 所有 Kubernetes versions 都会无限期支持
   * B) 每个 Kubernetes version 发布后支持 12 个月
   * C) 仅支持最新版本和前 3 个版本
   * D) 每个 Kubernetes version 发布后支持 14 个月

<details>

<summary>显示答案</summary>

**答案：D) 每个 Kubernetes version 发布后支持 14 个月**

**解释：** 根据 Amazon EKS 的 Kubernetes 版本支持策略，每个 Kubernetes version 在 EKS 上发布后支持 14 个月。此期限过后，该版本不再受支持，你必须将 cluster 升级到受支持版本。

**EKS 版本支持策略的主要特征：**

1. **14 个月支持期**：
   * 每个 Kubernetes version 从其在 EKS 上发布之日起支持 14 个月。
   * AWS 会提前公布支持结束日期。
2. **标准支持计划**：
   * Kubernetes community 大约每 4 个月发布一个新版本。
   * EKS 通常在 community release 后 2-3 个月内支持新的 Kubernetes versions。
   * 因此，EKS 上通常会同时支持 3-4 个 Kubernetes versions。
3. **无自动升级**：
   * 即使支持结束，AWS 也不会自动升级 clusters。
   * Cluster administrators 必须显式执行升级。
4. **支持结束后的影响**：
   * 运行不受支持版本的 clusters 会继续运行，但 AWS 不再提供安全补丁或 bug 修复。
   * 不能在不受支持版本上创建新的 clusters。
   * AWS support 不可用。

**版本升级最佳实践：**

* 建立定期升级计划
* 监控支持结束日期
* 先在测试环境中测试升级
* 升级前备份 cluster
* 每次升级一个 minor version
* 考虑 blue/green deployment 策略

**检查版本支持状态：**

```bash
# Check available EKS versions
aws eks describe-addon-versions | grep kubernetesVersion

# Check specific cluster version
aws eks describe-cluster --name my-cluster --query "cluster.version"
```

其他选项的问题：

* 并非所有 Kubernetes versions 都会无限期支持。每个版本仅在定义的期限内受支持。
* 每个版本支持 14 个月，而不是 12 个月。
* 没有“仅支持最新版本和前 3 个版本”的固定规则；受支持版本数量会根据 Kubernetes community release 计划和 EKS 支持策略而变化。

</details>
