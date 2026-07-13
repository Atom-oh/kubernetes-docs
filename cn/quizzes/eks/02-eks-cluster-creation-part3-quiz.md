# EKS Cluster 创建测验 - 第 3 部分

本测验测试你对 Amazon EKS cluster 创建相关的高级网络、存储配置和多租户的理解。内容涵盖 cluster networking、存储选项以及多租户环境配置等主题。

## 基础概念问题

1. 在 Amazon EKS cluster 中，限制每个 pod 可用 IP 地址数量的主要因素是什么？
   * A) VPC CIDR block 大小
   * B) Node instance type
   * C) Cluster 的 Kubernetes version
   * D) Subnet 中可用 IP 地址数量

<details>

<summary>显示答案</summary>

**答案：B) Node instance type**

**解释：** 在 Amazon EKS cluster 中，限制每个 pod 可用 IP 地址数量的主要因素是 node 的 instance type。Amazon VPC CNI plugin 使用每个 node 的 Elastic Network Interfaces (ENIs) 和 secondary IP addresses 为 pods 分配 IP 地址。每种 EC2 instance type 支持的最大 ENI 数量和每个 ENI 的最大 IP 地址数量不同，这决定了一个 node 上可运行的最大 pods 数量。

**按 Instance Type 计算最大 Pod 数量：**

最大 pods 数量使用以下公式计算：

```
(Number of ENIs × IP addresses per ENI - 1) + 2
```

其中：

* 减去 1 是因为 primary ENI 的 primary IP address 由 node 本身使用。
* 加上 2 是因为 kube-proxy 和 aws-node pods 使用 host networking。

**常见 Instance Types 的最大 Pod 数量：**

| Instance Type | Max ENIs | IPs per ENI | Max Pods |
| ------------- | -------- | ----------- | -------- |
| t3.small      | 3        | 4           | 11       |
| t3.medium     | 3        | 6           | 17       |
| m5.large      | 3        | 10          | 29       |
| m5.xlarge     | 4        | 15          | 58       |
| m5.2xlarge    | 4        | 15          | 58       |
| m5.4xlarge    | 8        | 30          | 234      |
| c5.large      | 3        | 10          | 29       |
| c5.xlarge     | 4        | 15          | 58       |
| r5.large      | 3        | 10          | 29       |
| r5.xlarge     | 4        | 15          | 58       |

**如何检查最大 Pod 数量：**

```bash
# Check maximum pod count for a node
kubectl get nodes -o jsonpath='{.items[*].status.capacity.pods}'

# Or use the max-pods script
curl -s https://raw.githubusercontent.com/awslabs/amazon-eks-ami/master/scripts/max-pods-calculator.sh | bash -s -- --instance-type m5.large
```

**限制最大 Pod 数量的因素：**

1. **Instance Type**:
   * 每种 instance type 支持的最大 ENI 数量和每个 ENI 的 IP 地址数量不同。
   * 更大的 instance types 通常支持更多 ENIs 和 IP 地址。
2. **CNI Configuration**:
   * 默认 VPC CNI configuration 使用 secondary IP addresses，而不是为每个 pod 分配完整 ENI。
   * 可以通过 custom networking 改变此行为。
3.  **Prefix Delegation**:

    * VPC CNI 1.9.0 及更高版本支持 prefix delegation，会为每个 ENI 分配一个 /28 CIDR block (16 IPs)。
    * 这可以显著增加每个 node 的最大 pods 数量。

    ```bash
    kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true
    ```
4.  **自定义 max-pods 值**:

    * 你可以使用 kubelet 的 `--max-pods` flag 限制每个 node 的最大 pods 数量。
    * 可以将其设置为低于 instance type 支持值的数量。

    ```bash
    eksctl create nodegroup \
      --cluster my-cluster \
      --name my-nodegroup \
      --node-type m5.large \
      --nodes 3 \
      --kubelet-extra-args "--max-pods=110"
    ```

**其他选项的问题：**

* **VPC CIDR block size**: VPC CIDR block size 限制 VPC 中可用 IP 地址总数，但不会直接限制单个 node 上的最大 pods 数量。
* **Cluster's Kubernetes version**: Kubernetes version 会影响受支持的功能，但不会直接限制每个 node 的最大 pods 数量。
* **Number of available IP addresses in the subnet**: Subnet 中可用 IP 地址数量会影响该 subnet 中可部署的 pods 总数，但不会直接限制单个 node 上的最大 pods 数量。

Node 的 instance type 是通过其支持的 ENI 数量和每个 ENI 的 IP 地址数量来决定一个 node 上可运行最大 pods 数量的主要因素。因此，选择满足 workload 要求的合适 instance type 非常重要。

</details>

2\. Amazon EKS cluster 中 pod-to-pod communication 的默认 network policy 是什么？ - A) 允许所有 pod-to-pod communication - B) 仅允许同一 namespace 中的 pods 之间通信 - C) 仅允许明确许可的 pod-to-pod communication - D) 阻止所有 pod-to-pod communication

<details>

<summary>显示答案</summary>

**答案：A) 允许所有 pod-to-pod communication**

**解释：** Amazon EKS cluster 中 pod-to-pod communication 的默认 network policy 是允许所有 pod-to-pod communication。默认情况下，EKS 不实现 network policies，所有 pods 都可以与 cluster 中的所有其他 pods 自由通信。这是 Kubernetes 的默认行为，你必须显式配置 network policies 才能限制 pod-to-pod communication。

**EKS 中的默认 Networking 行为：**

1. **Default Allow Policy**:
   * 默认情况下，所有 pods 都可以与 cluster 中的所有其他 pods 通信。
   * Namespaces 之间的通信也不受限制。
   * 这遵循 Kubernetes 的 “flat network” 模型。
2. **Amazon VPC CNI**:
   * EKS 的默认 CNI plugin 是 Amazon VPC CNI。
   * 此 plugin 为 pods 分配 VPC IP 地址，使其可在 VPC 内直接路由。
   * 默认情况下它不实现 network policies。

**如何实现 Network Policies：**

要在 EKS 中限制 pod-to-pod communication，你需要实现以下 network policy 方案之一：

1.  **Calico**:

    ```bash
    # Install Calico
    kubectl create namespace tigera-operator
    helm repo add projectcalico https://docs.projectcalico.org/charts
    helm install calico projectcalico/tigera-operator --namespace tigera-operator
    ```
2.  **Cilium**:

    ```bash
    # Install Cilium
    helm repo add cilium https://helm.cilium.io/
    helm install cilium cilium/cilium --namespace kube-system
    ```
3. **AWS Network Firewall** (VPC level):
   * 你可以使用 AWS Network Firewall 在 VPC level 过滤流量。
   * 这提供的是 subnet-level 控制，而不是细粒度的 pod-level 控制。

**Network Policy 示例：**

1.  **Default Deny Policy**:

    ```yaml
    # Block all ingress traffic
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: default-deny-ingress
      namespace: default
    spec:
      podSelector: {}
      policyTypes:
      - Ingress
    ```
2.  **允许特定 Pods 之间通信**:

    ```yaml
    # Allow communication only from frontend to backend
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: allow-frontend-to-backend
      namespace: default
    spec:
      podSelector:
        matchLabels:
          app: backend
      ingress:
      - from:
        - podSelector:
            matchLabels:
              app: frontend
        ports:
        - protocol: TCP
          port: 8080
    ```
3.  **限制跨 Namespace 通信**:

    ```yaml
    # Allow access only from prod namespace
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: allow-from-prod-namespace
      namespace: default
    spec:
      podSelector:
        matchLabels:
          app: database
      ingress:
      - from:
        - namespaceSelector:
            matchLabels:
              name: prod
        ports:
        - protocol: TCP
          port: 5432
    ```

**Network Policy 最佳实践：**

1. **应用 Default Deny Policy**:
   * 对所有 namespaces 应用 default deny policy，以阻止未明确允许的所有流量。
   * 只显式允许必要的通信。
2. **应用最小权限原则**:
   * 只允许 pods 所需的最小 network access。
   * 只允许特定 ports 和 protocols。
3. **Namespace Isolation**:
   * 使用 namespaces 对 workloads 进行逻辑隔离。
   * 显式控制 namespaces 之间的通信。
4. **基于 Label 的 Policies**:
   * 使用 pod labels 定义细粒度 network policies。
   * 维护一致的 labeling scheme。

**其他选项的问题：**

* **Allow communication only between pods in the same namespace**: 默认情况下，EKS 允许所有 pod-to-pod communication，包括跨 namespace 通信。
* **Allow only explicitly permitted pod-to-pod communication**: 这是实现 network policies 之后的行为，但不是默认行为。
* **Block all pod-to-pod communication**: 默认情况下，EKS 不会阻止 pod-to-pod communication。

EKS 中的默认 network policy 是允许所有 pod-to-pod communication。虽然这在开发和测试环境中可能很方便，但在生产环境中实现适当的 network policies 来增强安全性非常重要。

</details>

3. Amazon EKS cluster 中的 pods 要访问 VPC 外部的 internet，需要什么？
   * A) 将 internet gateway 附加到 pod 所在的 subnet
   * B) 将 NAT gateway 或 NAT instance 附加到 pod 所在的 subnet
   * C) 为 pod 分配 public IP address
   * D) 将 Elastic IP address 关联到 pod

<details>

<summary>显示答案</summary>

**答案：B) 将 NAT gateway 或 NAT instance 附加到 pod 所在的 subnet**

**解释：** Amazon EKS cluster 中的 pods 要访问 VPC 外部的 internet，pod 所在的 subnet 必须附加 NAT gateway 或 NAT instance。这是允许 private subnets 中的 pods 访问 internet 的标准方法。

**EKS Networking 架构：**

1. **Private Subnets 中的 Pods**:
   * 出于安全考虑，EKS worker nodes 通常放置在 private subnets 中。
   * Private subnets 中的 pods 不能直接访问 internet。
   * 它们必须通过 NAT gateway 或 NAT instance 访问 internet。
2. **Public Subnets 中的 Pods**:
   * 即使 worker nodes 位于 public subnets 中，pods 默认也不会获得 public IP addresses。
   * Pods 通过 node 的 network interface 经由 NAT 访问 internet。

**NAT Gateway 配置：**

```bash
# Create NAT gateway
aws ec2 create-nat-gateway \
  --subnet-id subnet-public1 \
  --allocation-id eipalloc-12345

# Update private subnet routing table
aws ec2 create-route \
  --route-table-id rtb-private \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id nat-12345
```

**使用 CloudFormation 的 VPC 配置示例：**

```yaml
Resources:
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsSupport: true
      EnableDnsHostnames: true
      Tags:
        - Key: Name
          Value: EKS-VPC

  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !GetAZs ""]
      CidrBlock: 10.0.0.0/24
      MapPublicIpOnLaunch: true
      Tags:
        - Key: Name
          Value: Public-Subnet-1

  PrivateSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !GetAZs ""]
      CidrBlock: 10.0.2.0/24
      Tags:
        - Key: Name
          Value: Private-Subnet-1

  InternetGateway:
    Type: AWS::EC2::InternetGateway
    Properties:
      Tags:
        - Key: Name
          Value: EKS-IGW

  VPCGatewayAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  NatGatewayEIP:
    Type: AWS::EC2::EIP
    DependsOn: VPCGatewayAttachment
    Properties:
      Domain: vpc

  NatGateway:
    Type: AWS::EC2::NatGateway
    Properties:
      AllocationId: !GetAtt NatGatewayEIP.AllocationId
      SubnetId: !Ref PublicSubnet1
      Tags:
        - Key: Name
          Value: EKS-NAT-GW

  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: Public-RT

  PublicRoute:
    Type: AWS::EC2::Route
    DependsOn: VPCGatewayAttachment
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  PrivateRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: Private-RT

  PrivateRoute:
    Type: AWS::EC2::Route
    Properties:
      RouteTableId: !Ref PrivateRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      NatGatewayId: !Ref NatGateway
```

**使用 eksctl 的 VPC 配置：**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
vpc:
  cidr: 192.168.0.0/16
  nat:
    gateway: Single  # NAT gateway configuration
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
```

**其他选项的问题：**

* **Attach an internet gateway to the subnet where the pod is located**: Internet gateway 附加到 public subnets，private subnets 中的资源需要 NAT gateway 才能访问 internet。此外，仅有 internet gateway 并不能让 pods 访问 internet。
* **Assign a public IP address to the pod**: Amazon VPC CNI plugin 不支持为 pods 分配 public IP addresses。Pods 始终获得 private IP addresses。
* **Associate an Elastic IP address with the pod**: 你不能直接将 Elastic IP address 关联到 pod。Elastic IP addresses 只能关联到 EC2 instances 或 network interfaces。

NAT gateway 或 NAT instance 是允许 private subnets 中的 pods 访问 internet 的标准方法。它会将 pod 的 private IP address 转换为 NAT gateway 的 public IP address，从而启用 internet 通信。对于生产环境，建议在每个 availability zone 中部署 NAT gateway 以实现高可用性。

</details>

4. 在 Amazon EKS cluster 中使用 SecurityGroupPolicy 为 pods 应用 security groups 时，以下哪项不是要求？
   * A) Amazon VPC CNI plugin version 1.7.7 或更高版本
   * B) ENIConfig resource configuration
   * C) 在 pod 上设置 hostNetwork: true
   * D) 为要应用 security groups 的 pods 指定 service account

<details>

<summary>显示答案</summary>

**答案：C) 在 pod 上设置 hostNetwork: true**

**解释：** “在 pod 上设置 hostNetwork: true” 不是在 Amazon EKS cluster 中使用 SecurityGroupPolicy 为 pods 应用 security groups 的要求。事实上，security groups 不能应用于 hostNetwork: true 的 pods。要为 pods 应用 security groups，pods 必须使用自己的 network namespace。

**Pod Security Group 功能要求：**

1.  **Amazon VPC CNI Plugin Version 1.7.7 or Later**:

    * Pod security group 功能在 Amazon VPC CNI plugin version 1.7.7 及更高版本中受支持。
    * 建议使用最新版本。

    ```bash
    # Check CNI version
    kubectl describe daemonset aws-node -n kube-system | grep Image

    # Update CNI
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.10.0/config/master/aws-k8s-cni.yaml
    ```
2.  **启用 Pod Security Group 功能**:

    ```bash
    # Enable pod security group feature
    kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true

    # Or use eksctl
    eksctl utils update-cluster-config \
      --name my-cluster \
      --region us-west-2 \
      --enable-pod-security-groups
    ```
3.  **为要应用 Security Groups 的 Pods 指定 Service Account**:

    * 在 SecurityGroupPolicy 中，必须使用 pod selector 或 service account selector 指定要应用 security groups 的 pods。

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
          - sg-12345
    ```

**Pod Security Group 配置示例：**

1.  **创建 SecurityGroupPolicy**:

    ```yaml
    apiVersion: vpcresources.k8s.aws/v1beta1
    kind: SecurityGroupPolicy
    metadata:
      name: db-client-policy
      namespace: default
    spec:
      serviceAccountSelector:
        matchLabels:
          role: db-client
      securityGroups:
        groupIds:
          - sg-db-client
    ```
2.  **创建 Service Account**:

    ```yaml
    apiVersion: v1
    kind: ServiceAccount
    metadata:
      name: db-client
      namespace: default
      labels:
        role: db-client
    ```
3.  **部署 Pod**:

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: db-client-pod
    spec:
      serviceAccountName: db-client
      containers:
      - name: db-client
        image: mysql:5.7
        command: ['sleep', '3600']
    ```

**hostNetwork: true 的问题：**

带有 `hostNetwork: true` 的 Pods 使用 node 的 network namespace，因此无法为 pod 应用单独的 security groups。这类 pods 会继承 node 的 security groups。

```yaml
# Security groups cannot be applied to this pod
apiVersion: v1
kind: Pod
metadata:
  name: host-network-pod
spec:
  hostNetwork: true  # Uses the node's network namespace
  containers:
  - name: nginx
    image: nginx
```

**ENIConfig Resource Configuration：**

配置 custom networking 时需要 ENIConfig resources，但仅使用 pod security groups 功能时它们不是强制要求。不过，如果你将 pod security groups 与 custom networking 一起使用，则必须配置 ENIConfig resources。

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2a
spec:
  subnet: subnet-12345
  securityGroups:
  - sg-12345
```

**Pod Security Group 限制：**

1. **Resource Limitations**:
   * 每个 node 需要额外的 ENIs 用于 pod security groups。
   * 支持的最大 ENI 数量受 instance type 限制。
2. **Compatibility Limitations**:
   * 不能应用于 hostNetwork: true 的 pods。
   * 不能应用于使用 hostPort 的 pods。
   * 可能与某些 CNI plugins 不兼容。
3. **Performance Impact**:
   * 由于每个 pod 都需要额外 ENIs，pod 启动时间可能更长。
   * 每个 node 的最大 pods 数量可能会受到限制。

Pod security groups 功能是一项强大的能力，可在 pod level 提供细粒度 network security。然而，由于此功能不能应用于 hostNetwork: true 的 pods，pods 必须使用自己的 network namespace 才能使用 pod security groups。

</details>

4\. 在 Amazon EKS cluster 中使用 SecurityGroupPolicy 为 pods 应用 security groups 时，什么不是要求？ - A) Amazon VPC CNI plugin version 1.7.7 或更高版本 - B) ENIConfig resource configuration - C) 在 pod 上设置 hostNetwork: true - D) 为将应用 security groups 的 pods 指定 service account

<details>

<summary>显示答案</summary>

**答案：C) 在 pod 上设置 hostNetwork: true**

**解释：** 在 Amazon EKS cluster 中使用 SecurityGroupPolicy 为 pods 应用 security groups 时，不属于要求的选项是“在 pod 上设置 hostNetwork: true”。事实上，security groups 不能应用于 hostNetwork: true 的 pods。要为 pods 应用 security groups，pods 必须使用自己的 network namespace。

**Pod Security Groups 功能要求：**

1.  **Amazon VPC CNI plugin version 1.7.7 or higher**:

    * Pod security groups 功能在 Amazon VPC CNI plugin version 1.7.7 及更高版本中受支持。
    * 建议使用最新版本。

    ```bash
    # Check CNI version
    kubectl describe daemonset aws-node -n kube-system | grep Image

    # Update CNI
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.10.0/config/master/aws-k8s-cni.yaml
    ```
2.  **启用 pod security groups 功能**:

    ```bash
    # Enable pod security groups feature
    kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true

    # Or use eksctl
    eksctl utils update-cluster-config \
      --name my-cluster \
      --region us-west-2 \
      --enable-pod-security-groups
    ```
3.  **指定将应用 security groups 的 pods 的 service account**:

    * 在 SecurityGroupPolicy 中，必须使用 pod selector 或 service account selector 指定将应用 security groups 的 pods。

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
          - sg-12345
    ```

**Pod Security Group 配置示例：**

1.  **创建 SecurityGroupPolicy**:

    ```yaml
    apiVersion: vpcresources.k8s.aws/v1beta1
    kind: SecurityGroupPolicy
    metadata:
      name: db-client-policy
      namespace: default
    spec:
      serviceAccountSelector:
        matchLabels:
          role: db-client
      securityGroups:
        groupIds:
          - sg-db-client
    ```
2.  **创建 Service Account**:

    ```yaml
    apiVersion: v1
    kind: ServiceAccount
    metadata:
      name: db-client
      namespace: default
      labels:
        role: db-client
    ```
3.  **部署 Pod**:

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: db-client-pod
    spec:
      serviceAccountName: db-client
      containers:
      - name: db-client
        image: mysql:5.7
        command: ['sleep', '3600']
    ```

**hostNetwork: true 的问题：**

带有 `hostNetwork: true` 的 Pods 使用 node 的 network namespace，因此无法为 pod 应用单独的 security groups。这类 pods 会继承 node 的 security groups。

```yaml
# Security groups cannot be applied to this pod
apiVersion: v1
kind: Pod
metadata:
  name: host-network-pod
spec:
  hostNetwork: true  # Uses the node's network namespace
  containers:
  - name: nginx
    image: nginx
```

**ENIConfig Resource Configuration：**

配置 custom networking 时需要 ENIConfig resources，但仅使用 pod security groups 功能时它们不是强制要求。不过，如果你将 pod security groups 与 custom networking 一起使用，则必须配置 ENIConfig resources。

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2a
spec:
  subnet: subnet-12345
  securityGroups:
  - sg-12345
```

**Pod Security Group 限制：**

1. **Resource Limitations**:
   * 每个 node 需要额外的 ENIs 用于 pod security groups。
   * 支持的最大 ENI 数量受 instance type 限制。
2. **Compatibility Limitations**:
   * 不能应用于 hostNetwork: true 的 pods。
   * 不能应用于使用 hostPort 的 pods。
   * 可能与某些 CNI plugins 不兼容。
3. **Performance Impact**:
   * 由于每个 pod 都需要额外 ENIs，pod 启动时间可能更长。
   * 每个 node 的最大 pods 数量可能会受到限制。

Pod security groups 功能是一项强大的能力，可在 pod level 提供细粒度 network security。然而，由于此功能不能应用于 hostNetwork: true 的 pods，pods 必须使用自己的 network namespace 才能使用 pod security groups。

</details>

5. Amazon EKS cluster 中 Prefix Delegation 功能的主要优势是什么？
   * A) 提升 pods 之间的通信速度
   * B) 增加每个 node 的最大 pods 数量
   * C) 能够为 pods 分配 public IP addresses
   * D) 增强 pod network isolation

<details>

<summary>显示答案</summary>

**答案：B) 增加每个 node 的最大 pods 数量**

**解释：** Amazon EKS cluster 中 Prefix Delegation 功能的主要优势是增加每个 node 的最大 pods 数量。此功能会向每个 Elastic Network Interface (ENI) 分配 /28 CIDR blocks (16 IP addresses)，而不是单独的 IP addresses，从而显著增加一个 node 可支持的最大 pods 数量。

**Prefix Delegation 的工作方式：**

1. **默认 VPC CNI 行为**:
   * 默认情况下，VPC CNI 会从 ENI 为每个 pod 分配 secondary IP addresses。
   * 每种 EC2 instance type 对最大 ENI 数量和每个 ENI 的 IP 地址数量有限制。
   * 这会限制每个 node 的最大 pods 数量。
2. **Prefix Delegation 行为**:
   * 启用 prefix delegation 后，会为每个 ENI 分配 /28 CIDR blocks (16 IPs)，而不是单独的 IP addresses。
   * 这会显著增加每个 ENI 可支持的 IP 地址数量。
   * 因此，每个 node 的最大 pods 数量会增加。

**启用 Prefix Delegation：**

```bash
# Enable prefix delegation
kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true

# Check prefix delegation status
kubectl describe daemonset aws-node -n kube-system | grep ENABLE_PREFIX_DELEGATION
```

**Prefix Delegation 的优势：**

1. **增加每个 Node 的最大 Pods 数量**:
   * 使用 prefix delegation 会显著增加每个 node 的最大 pods 数量。
   * 例如，对于 m5.large instance：
     * 默认配置：最多 29 个 pods
     * 启用 prefix delegation 后：最多超过 110 个 pods
2. **IP 地址效率**:
   * 优化大型 clusters 中的 IP 地址使用。
   * 适用于 VPC CIDR ranges 有限的环境。
3. **改进 Node 资源利用率**:
   * 运行更多 pods 可以提高 node 资源利用率。
   * 有助于 cluster 成本优化。

**Prefix Delegation 限制：**

1. **EC2 Instance 支持**:
   * 只有基于 Nitro 的 instances 支持 prefix delegation。
   * 不能与旧一代 instances 一起使用。
2. **VPC CNI Version 要求**:
   * 需要 VPC CNI version 1.9.0 或更高版本。
   * 此功能不能与早期版本一起使用。
3. **Subnet Size 要求**:
   * 需要具有足够 IP 地址空间的 subnets。
   * 在小型 subnets 中，IP 地址可能很快耗尽。
4. **迁移注意事项**:
   * 在现有 clusters 上启用时，只有新的 pods 使用 prefix delegation。
   * 现有 pods 必须重启才能应用到所有 pods。

**Prefix Delegation 配置示例：**

```yaml
# eksctl configuration file
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
managedNodeGroups:
  - name: ng-1
    instanceType: m5.large
    minSize: 2
    maxSize: 5
    disableIMDSv1: true
iam:
  withOIDC: true
addons:
  - name: vpc-cni
    version: latest
    configurationValues: |
      {
        "env": {
          "ENABLE_PREFIX_DELEGATION": "true"
        }
      }
```

**其他选项的问题：**

* **Improved communication speed between pods**: Prefix delegation 不会直接影响 pod-to-pod communication speed。Pod 通信性能主要由 network infrastructure 和 CNI implementation 决定。
* **Ability to assign public IP addresses to pods**: Prefix delegation 不提供为 pods 分配 public IP addresses 的能力。VPC CNI 始终为 pods 分配 private IP addresses。
* **Enhanced pod network isolation**: Prefix delegation 与 pod network isolation 无关。Network isolation 通过 network policies 或 security groups 实现。

Prefix delegation 是一项强大功能，可增加每个 node 的最大 pods 数量，提高 cluster density 和效率。它特别适用于大型 clusters 或运行高密度 workloads 的环境。

</details>

6. 在 Amazon EKS cluster 中自定义 CoreDNS 的正确方法是什么？
   * A) 在 AWS Management Console 中修改 CoreDNS settings
   * B) 修改 CoreDNS ConfigMap
   * C) 在 EKS cluster 创建期间指定 CoreDNS configuration
   * D) 使用 AWS CLI 更新 CoreDNS add-on parameters

<details>

<summary>显示答案</summary>

**答案：B) 修改 CoreDNS ConfigMap**

**解释：** 在 Amazon EKS cluster 中自定义 CoreDNS 的正确方法是修改 CoreDNS ConfigMap。CoreDNS 是 Kubernetes 的 cluster DNS server，通过 ConfigMap 进行配置。在 EKS 中，你可以通过修改 `coredns` ConfigMap 来自定义 CoreDNS 行为。

**如何修改 CoreDNS ConfigMap：**

1.  **检查当前 ConfigMap**:

    ```bash
    kubectl get configmap coredns -n kube-system -o yaml
    ```
2.  **编辑 ConfigMap**:

    ```bash
    kubectl edit configmap coredns -n kube-system
    ```
3.  **或应用 Patch**:

    ```bash
    kubectl patch configmap coredns -n kube-system --type=merge -p '{"data":{"Corefile":".:53 {\n    errors\n    health {\n        lameduck 5s\n    }\n    ready\n    kubernetes cluster.local in-addr.arpa ip6.arpa {\n        pods insecure\n        fallthrough in-addr.arpa ip6.arpa\n        ttl 30\n    }\n    prometheus :9153\n    forward . /etc/resolv.conf\n    cache 30\n    loop\n    reload\n    loadbalance\n    # Add custom settings\n    hosts {\n        10.0.0.1 example.com\n        fallthrough\n    }\n}"}}'
    ```

**常见 CoreDNS 自定义场景：**

1.  **添加自定义 DNS Records**:

    ```
    hosts {
        10.0.0.1 example.com
        10.0.0.2 api.example.com
        fallthrough
    }
    ```
2.  **为特定 Domains 配置 Forwarding**:

    ```
    forward example.org 10.0.0.1:53
    ```
3.  **调整 DNS Caching**:

    ```
    cache {
        success 10000
        denial 5000
        prefetch 10 10 10%
    }
    ```
4.  **配置 Logging**:

    ```
    log {
        class error
    }
    ```
5.  **禁用 Autopath**:

    ```
    kubernetes cluster.local in-addr.arpa ip6.arpa {
        pods insecure
        fallthrough in-addr.arpa ip6.arpa
        ttl 30
        autopath off
    }
    ```

**CoreDNS 修改后应用更改：**

修改 ConfigMap 后，需要重启 CoreDNS pods 以应用更改：

```bash
# Check CoreDNS pods
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Restart CoreDNS pods
kubectl rollout restart deployment coredns -n kube-system

# Verify changes are applied
kubectl logs -n kube-system -l k8s-app=kube-dns
```

**CoreDNS 性能优化：**

1.  **配置 Auto-scaling**:

    ```yaml
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    metadata:
      name: coredns-autoscaler
      namespace: kube-system
    spec:
      scaleTargetRef:
        apiVersion: apps/v1
        kind: Deployment
        name: coredns
      minReplicas: 2
      maxReplicas: 10
      metrics:
      - type: Resource
        resource:
          name: cpu
          target:
            type: Utilization
            averageUtilization: 60
    ```
2.  **调整 Resource Requests 和 Limits**:

    ```bash
    kubectl patch deployment coredns -n kube-system --type=json -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources", "value": {"requests": {"cpu": "100m", "memory": "70Mi"}, "limits": {"cpu": "200m", "memory": "170Mi"}}}]'
    ```

**其他选项的问题：**

* **Modify CoreDNS settings in the AWS Management Console**: AWS Management Console 不提供直接修改 CoreDNS settings 的界面。
* **Specify CoreDNS configuration during EKS cluster creation**: 不能在 EKS cluster 创建期间指定详细的 CoreDNS configuration。必须在 cluster 创建后修改 ConfigMap。
* **Update CoreDNS add-on parameters using the AWS CLI**: 虽然你可以使用 AWS CLI 更新 CoreDNS add-on version，但不能修改详细 configuration。Configuration changes 必须通过 ConfigMap 完成。

```bash
# Update CoreDNS add-on version (not configuration change)
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name coredns \
  --addon-version v1.8.7-eksbuild.2 \
  --resolve-conflicts PRESERVE
```

修改 CoreDNS ConfigMap 是在 EKS cluster 中自定义 DNS settings 的标准方法。这支持多种自定义，例如添加自定义 DNS records、为特定 domains 配置 forwarding，以及调整 caching behavior。

</details>

7\. 在 Amazon EKS cluster 中实现 multi-tenancy 的最有效方法是什么？ - A) 为每个 tenant 创建单独的 EKS clusters - B) 为每个 tenant 使用单独的 namespaces，并应用 RBAC、network policies 和 resource quotas - C) 为每个 tenant 创建单独的 node groups 并使用 node selectors - D) 为每个 tenant 使用单独的 VPCs

<details>

<summary>显示答案</summary>

**答案：B) 为每个 tenant 使用单独的 namespaces，并应用 RBAC、network policies 和 resource quotas**

**解释：** 在 Amazon EKS cluster 中实现 multi-tenancy 的最有效方法是为每个 tenant 使用单独的 namespaces，并应用 RBAC (Role-Based Access Control)、network policies 和 resource quotas。这种方法可以在单个 cluster 内高效隔离多个 tenants，同时允许资源共享。

**实现基于 Namespace 的 Multi-Tenancy：**

1.  **为每个 Tenant 创建 Namespaces**:

    ```bash
    # Create namespaces for each tenant
    kubectl create namespace tenant-a
    kubectl create namespace tenant-b
    ```
2.  **配置 RBAC**:

    ```yaml
    # Create tenant role
    apiVersion: rbac.authorization.k8s.io/v1
    kind: Role
    metadata:
      name: tenant-full-access
      namespace: tenant-a
    rules:
    - apiGroups: ["", "apps", "batch"]
      resources: ["*"]
      verbs: ["*"]
    ---
    # Bind role to tenant users
    apiVersion: rbac.authorization.k8s.io/v1
    kind: RoleBinding
    metadata:
      name: tenant-a-access
      namespace: tenant-a
    subjects:
    - kind: Group
      name: tenant-a-users
      apiGroup: rbac.authorization.k8s.io
    roleRef:
      kind: Role
      name: tenant-full-access
      apiGroup: rbac.authorization.k8s.io
    ```
3.  **应用 Network Policies**:

    ```yaml
    # Restrict communication between tenants
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    ```

metadata: name: deny-cross-tenant-traffic namespace: tenant-a spec: podSelector: {} policyTypes: - Ingress - Egress ingress: - from: - namespaceSelector: matchLabels: name: tenant-a egress: - to: - namespaceSelector: matchLabels: name: tenant-a - to: - namespaceSelector: matchLabels: name: kube-system

````

4. **Resource Quota 配置**:
 ```yaml
 # Tenant Resource Quota
 apiVersion: v1
 kind: ResourceQuota
 metadata:
   name: tenant-quota
   namespace: tenant-a
 spec:
   hard:
     requests.cpu: "10"
     requests.memory: 20Gi
     limits.cpu: "20"
     limits.memory: 40Gi
     pods: "50"
     services: "20"
     persistentvolumeclaims: "30"
     secrets: "100"
     configmaps: "100"
````

5.  **LimitRange 配置**:

    ```yaml
    # Default resource limit settings
    apiVersion: v1
    kind: LimitRange
    metadata:
      name: tenant-limits
      namespace: tenant-a
    spec:
      limits:
      - default:
          cpu: 500m
          memory: 512Mi
        defaultRequest:
          cpu: 100m
          memory: 256Mi
        type: Container
    ```

**基于 Namespace 的 Multi-Tenancy 的优势：**

1. **Resource Efficiency**:
   * 多个 tenants 共享单个 cluster 时，资源利用率会提高。
   * Control plane 成本会降低。
2. **Ease of Management**:
   * 管理单个 cluster 可减少运营开销。
   * 可以进行集中式 monitoring 和 logging。
3. **Flexibility**:
   * 添加和移除 tenants 很直接。
   * 可以轻松应用 tenant-specific policies。
4. **Cost Efficiency**:
   * Cluster 开销在多个 tenants 之间共享。
   * 提高资源利用率会带来成本节省。

**基于 Namespace 的 Multi-Tenancy 的缺点：**

1. **有限的隔离级别**:
   * Namespaces 只提供逻辑隔离，而不是完整的物理隔离。
   * 可能暴露于 kernel-level vulnerabilities。
2. **Resource Contention**:
   * Tenants 之间可能出现 resource contention。
   * 可能出现 Noisy Neighbor 问题。
3. **Security Risks**:
   * 存在 cluster-level privilege escalation 风险。
   * 可能暴露于 container escape vulnerabilities。

**其他 Multi-Tenancy 方法：**

1. **Cluster-Based Multi-Tenancy (每个 Tenant 一个单独 EKS Cluster)**:
   * 提供最强隔离
   * 增加管理开销
   * 增加成本
   * 适合大型企业环境或高度监管行业
2. **Node-Based Multi-Tenancy (每个 Tenant 一个单独 Node Group)**:
   * 提供中等级别隔离
   * 可按 tenant 进行 node-level customization
   * 降低资源利用率
   * 适合安全要求较高但也需要考虑成本的场景
3. **Hybrid Approach**:
   * 为关键 tenants 提供 dedicated clusters
   * 在共享 cluster 中按 namespace 分隔不太关键的 tenants
   * 平衡灵活性和成本效率

**其他选项的问题：**

* **Creating a Separate EKS Cluster per Tenant**: 提供最强隔离，但会显著增加管理开销和成本。当 tenants 很多时，可能出现可扩展性问题。
* **Creating Separate Node Groups per Tenant and Using Node Selectors**: 提供 node-level isolation，但资源利用率会下降，管理也可能变得复杂。此外，仅靠 node groups 并不能提供完整隔离。
* **Using Separate VPCs per Tenant**: 由于 EKS clusters 在单个 VPC 内创建，为每个 tenant 使用单独 VPCs 需要为每个 tenant 创建单独 clusters。这会显著增加管理开销和成本。

对于大多数用例，基于 namespace 的 multi-tenancy 在隔离、易管理性和成本效率之间提供最佳平衡。然而，当安全要求非常高时，应考虑基于 cluster 的 multi-tenancy。

</details>

8. 在 Amazon EKS cluster 中为 node group 选择 instance type 时，以下哪项不是需要考虑的因素？
   * A) Workload 的 CPU 和 memory 要求
   * B) Cost optimization
   * C) Cluster 的 Kubernetes version
   * D) Required pod density

<details>

<summary>显示答案</summary>

**答案：C) Cluster 的 Kubernetes version**

**解释：** 在 Amazon EKS cluster 中为 node group 选择 instance type 时，不需要考虑的因素是“cluster 的 Kubernetes version”。虽然 Kubernetes version 会影响受支持功能，但它不会直接影响 node group 的 instance type 选择。Instance type 主要由 workload 要求、成本、pod density 和其他因素决定。

**选择 Node Group Instance Types 时需要考虑的实际因素：**

1. **Workload 的 CPU 和 Memory 要求**:
   * 选择符合 workload 资源要求的 instance types
   * CPU-intensive workloads：compute-optimized instances，例如 c5、c6g
   * Memory-intensive workloads：memory-optimized instances，例如 r5、r6g
   * Balanced workloads：general-purpose instances，例如 m5、m6g
   * GPU workloads：accelerated computing instances，例如 p3、g4dn
2. **Cost Optimization**:
   * On-Demand vs Spot instances
   * Reserved Instances 或 Savings Plans
   * 通过基于 ARM 的 Graviton instances 节省成本（例如 m6g、c6g）
   * 选择大小合适的 instances（避免过度配置）
3. **Required Pod Density**:
   * 最大支持 pods 数量因 instance type 而异
   * 考虑每种 instance type 的 ENI 数量和每个 ENI 的 IP 地址数量
   * 对于高密度 workloads，选择支持更多 ENIs 和 IP 地址的 instance types
4. **Networking Requirements**:
   * Network bandwidth 要求
   * Enhanced networking 支持（ENA、EFA 等）
   * Network performance 因 instance type 而异
5. **Storage Requirements**:
   * 是否需要 local instance storage（例如 i3、d3 instances）
   * EBS optimization 支持
   * Storage throughput 和 IOPS 要求
6. **Availability Requirements**:
   * Instance types 的 regional availability
   * 使用 Spot instances 时的中断可能性
   * Availability Zone 中的 instance type availability

**Instance Type 选择示例：**

1.  **Web Application Servers**:

    ```yaml
    apiVersion: eksctl.io/v1alpha5
    kind: ClusterConfig
    metadata:
      name: my-cluster
      region: us-west-2
    managedNodeGroups:
      - name: web-servers
        instanceType: m5.large
        minSize: 2
        maxSize: 10
        labels:
          role: web
    ```
2.  **Database Workloads**:

    ```yaml
    apiVersion: eksctl.io/v1alpha5
    kind: ClusterConfig
    metadata:
      name: my-cluster
      region: us-west-2
    managedNodeGroups:
      - name: database-nodes
        instanceType: r5.xlarge
        minSize: 3
        maxSize: 5
        labels:
          role: database
    ```
3.  **Batch Processing Workloads**:

    ```yaml
    apiVersion: eksctl.io/v1alpha5
    kind: ClusterConfig
    metadata:
      name: my-cluster
      region: us-west-2
    managedNodeGroups:
      - name: batch-processors
        instanceType: c5.2xlarge
        minSize: 0
        maxSize: 20
        labels:
          role: batch
    ```
4.  **Cost-Optimized Workloads**:

    ```yaml
    apiVersion: eksctl.io/v1alpha5
    kind: ClusterConfig
    metadata:
      name: my-cluster
      region: us-west-2
    managedNodeGroups:
      - name: spot-workers
        instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5ad.large"]
        minSize: 2
        maxSize: 10
        spot: true
        labels:
          lifecycle: spot
    ```

**Kubernetes Version 与 Instance Types 的关系：**

Kubernetes version 会以下列方式影响 cluster，但不会直接影响 instance type 选择：

1. **Supported Features**:
   * 新 Kubernetes versions 提供新功能。
   * 某些功能只在特定 versions 中可用。
2. **API Compatibility**:
   * 某些 APIs 可能会在新 versions 中更改或移除。
   * 如果你的应用依赖特定 APIs，version 选择很重要。
3. **Security Patches**:
   * 最新 versions 包含最新 security patches。
   * 旧 versions 可能暴露于 security vulnerabilities。
4. **Support Period**:
   * 每个 Kubernetes version 只在有限期间内受支持。
   * EKS 对每个 version 的支持约为 14 个月。

Instance type 选择主要由 workload resource requirements、cost optimization、pod density 和其他因素决定，与 Kubernetes version 没有直接关系。因此，“cluster 的 Kubernetes version”不是选择 node group instance type 时需要考虑的主要因素。

</details>

9\. 在 Amazon EKS cluster 中进行 node group updates 时，最大限度减少 pod disruption 的最有效方法是什么？ - A) 使用 rolling update strategy - B) 配置 PodDisruptionBudget - C) 在 node group update 前手动迁移所有 pods - D) 使用 blue/green deployment strategy

<details>

<summary>显示答案</summary>

**答案：B) 配置 PodDisruptionBudget**

**解释：** 在 Amazon EKS cluster 中进行 node group updates 时，最大限度减少 pod disruption 的最有效方法是配置 PodDisruptionBudget (PDB)。PDB 限制在 voluntary disruptions 期间可同时中断的 pods 数量，以确保 application availability。由于 node group updates 被视为 voluntary disruptions，你可以通过 PDB 在 updates 期间维持 application availability。

**PodDisruptionBudget 的工作方式：**

1. **PDB Definition**:
   * `minAvailable`: 指定必须始终可用的 pods 最小数量或百分比
   * `maxUnavailable`: 指定可同时不可用的 pods 最大数量或百分比
   * 这两个选项只能指定一个
2. **PDB Application**:
   * Kubernetes 在 node draining 期间遵守 PDB
   * 如果违反 PDB，draining 过程会暂停
   * 当新的 pods 在其他 nodes 上开始运行时，draining 继续

**PodDisruptionBudget 示例：**

```yaml
# Ensure at least 2 pods are always available
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

```yaml
# Limit only up to 50% of pods to be unavailable simultaneously
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: default
spec:
  maxUnavailable: 50%
  selector:
    matchLabels:
      app: my-app
```

**EKS Node Group Update 流程：**

1. **Update Start**:
   * 创建新 nodes
   * 新 nodes 加入 cluster
2. **Node Draining**:
   * 对现有 nodes 应用 cordoning（防止新的 pod scheduling）
   * 从现有 nodes drain pods（迁移 pods）
   * 在遵守 PDB 的同时迁移 pods
3. **Node Termination**:
   * 所有 pods 迁移后终止 nodes
   * 对下一个 node 重复该过程

**PDB 配置最佳实践：**

1. **设置适当的 Replica Count**:
   * 需要足够 replicas 才能让 PDB 有效工作
   * 建议至少 3 个 replicas
2. **选择适当的 PDB 值**:
   * 选择适合 application characteristics 的值
   * 过于严格的值可能延迟 updates
   * 过于宽松的值可能影响 availability
3. **将 PDB 应用于所有关键 Workloads**:
   * Stateful applications
   * User-facing services
   * System components
4. **测试 PDB**:
   * 在 updates 前测试 PDB 行为
   * 通过 draining simulation 验证 availability

**Node Group Update 配置：**

```bash
# Modify managed node group update configuration
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --update-config '{"maxUnavailable": 1}'

# Or using eksctl
eksctl update nodegroup \
  --cluster my-cluster \
  --name my-nodegroup \
  --max-unavailable 1
```

**其他选项的问题：**

* **Using a Rolling Update Strategy**: EKS managed node groups 默认已经使用 rolling update strategy。然而，仅靠 rolling updates 不能控制 pod disruption，必须与 PDB 一起使用才有效。
* **Manually Migrating All Pods Before Node Group Update**: 这是耗时且容易出错的手动过程。对于大型 clusters 也不实际。
* **Using a Blue/Green Deployment Strategy**: Blue/green deployment 涉及创建新 node group、迁移 workloads，然后删除现有 node group。这是有效策略，但存在因资源重复导致成本增加和实现复杂的缺点。它也最好与 PDB 一起使用。

PodDisruptionBudget 是 Kubernetes-native 的方式，用于在 node group updates 期间控制 pod disruption，使你可以在确保 application availability 的同时安全更新 node groups。因此，最大限度减少 node group updates 期间 pod disruption 的最有效方法是配置 PodDisruptionBudget。

</details>

10. 以下哪项不用于控制 Amazon EKS cluster 中 node groups 的 Auto Scaling 行为？
    * A) Cluster Autoscaler
    * B) Karpenter
    * C) Horizontal Pod Autoscaler
    * D) Vertical Pod Autoscaler

<details>

<summary>显示答案</summary>

**答案：D) Vertical Pod Autoscaler**

**解释：** 不用于控制 Amazon EKS cluster 中 node groups 的 Auto Scaling 行为的是 Vertical Pod Autoscaler (VPA)。VPA 用于自动调整 pods 的 CPU 和 memory requests，但不用于调整 node groups 的大小。Node group Auto Scaling 主要由 Cluster Autoscaler、Karpenter 以及间接由 Horizontal Pod Autoscaler (HPA) 控制。

**Node Group Auto Scaling 工具：**

1.  **Cluster Autoscaler**:

    * 一个 Kubernetes component，会自动调整 node groups 的大小
    * 当 pods 无法调度时添加 nodes
    * 当 nodes 利用率不足时移除 nodes
    * 与 AWS Auto Scaling Groups 集成

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
          serviceAccountName: cluster-autoscaler
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
2.  **Karpenter**:

    * AWS 的 open-source node provisioning project
    * 为 workload requirements 选择最佳 instance types
    * 快速 node provisioning（以秒计）
    * Cost optimization 和统一 lifecycle management

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
          nodeClassRef:
            name: default-class
      limits:
        cpu: 1000
          memory: 1000Gi
      provider:
        subnetSelector:
          karpenter.sh/discovery: "true"
        securityGroupSelector:
          karpenter.sh/discovery: "true"
      ttlSecondsAfterEmpty: 30
    ```
3.  **Horizontal Pod Autoscaler (HPA)**:

    * 自动调整 pod replicas 的数量
    * 基于 CPU、memory 或 custom metrics
    * 可以间接触发 node group Auto Scaling
    * 与 Cluster Autoscaler 或 Karpenter 协同工作

    ```yaml
    # Horizontal Pod Autoscaler
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    metadata:
      name: my-app-hpa
    spec:
      scaleTargetRef:
        apiVersion: apps/v1
        kind: Deployment
        name: my-app
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

**Vertical Pod Autoscaler (VPA)：**

VPA 用于自动调整 pods 的 CPU 和 memory requests，但不会直接调整 node groups 的大小：

```yaml
# Vertical Pod Autoscaler
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 100m
        memory: 50Mi
      maxAllowed:
        cpu: 1
        memory: 500Mi
      controlledResources: ["cpu", "memory"]
```

VPA 提供以下功能：

* 自动调整 pod resource requests
* 基于 resource usage 的建议
* 通过 pod restarts 更新 resource requests

然而，VPA 不会直接调整 node groups 的大小，只影响 pod level 的资源分配。

**Node Group Auto Scaling 策略：**

1. **Reactive Scaling**:
   * 使用 Cluster Autoscaler
   * 当 pods 无法调度时添加 nodes
   * 当 resource utilization 低时移除 nodes
   * 适合可预测 workloads
2. **Predictive Scaling**:
   * 使用 AWS Auto Scaling predictive scaling
   * 根据历史模式预测未来需求
   * 在需求增加前确保容量
   * 适合具有周期性模式的 workloads
3. **Event-driven Scaling**:
   * 使用 KEDA (Kubernetes Event-driven Autoscaling)
   * 基于 external events 或 metrics 进行 scaling
   * 基于 queue length、event count 等进行 scaling
   * 适合 batch processing、event processing workloads

**其他选项说明：**

* **Cluster Autoscaler**: 一个 Kubernetes component，直接控制 node group Auto Scaling，根据 pod scheduling requirements 添加或移除 nodes。
* **Karpenter**: AWS open-source node provisioning project，可快速 provision 满足 workload requirements 的最佳 instances。它可以作为 Cluster Autoscaler 的替代方案使用。
* **Horizontal Pod Autoscaler**: 自动调整 pod replicas 的数量，当创建更多 pods 时，可间接触发 Cluster Autoscaler 或 Karpenter 调整 node group size。

Vertical Pod Autoscaler 用于调整 pod resource requests，但不直接调整 node group size。因此，Vertical Pod Autoscaler 是不用于控制 node group Auto Scaling 行为的选项。

</details>

## 实践练习

### 练习 1：在 EKS Cluster 中实现 Network Policies

**场景：** 你是公司的一名 security engineer，需要在 EKS cluster 中限制 microservices 之间的 network traffic。具体来说，只有 frontend service 应该能够访问 backend API，而 database 应该只能由 backend API 访问。

**要求：**

1. 安装 Calico network policy engine
2. 实现 default deny policy
3. 允许从 frontend 到 backend 的流量
4. 允许从 backend 到 database 的流量
5. 测试 policies

**解决方案：**

<details>

<summary>显示解决方案</summary>

**1. 安装 Calico Network Policy Engine**

```bash
# Install Tigera Operator
kubectl create namespace tigera-operator
helm repo add projectcalico https://docs.projectcalico.org/charts
helm install calico projectcalico/tigera-operator --namespace tigera-operator

# Verify installation
kubectl get pods -n calico-system
```

**2. 创建 Namespace 和示例 Applications**

```bash
# Create namespace
kubectl create namespace microservices

# Deploy frontend
cat > frontend.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: microservices
  labels:
    app: frontend
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
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: microservices
spec:
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 80
EOF

kubectl apply -f frontend.yaml

# Deploy backend
cat > backend.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: microservices
  labels:
    app: backend
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
      - name: httpd
        image: httpd:alpine
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: microservices
spec:
  selector:
    app: backend
  ports:
  - port: 80
    targetPort: 80
EOF

kubectl apply -f backend.yaml

# Deploy database
cat > database.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: database
  namespace: microservices
  labels:
    app: database
spec:
  replicas: 1
  selector:
    matchLabels:
      app: database
  template:
    metadata:
      labels:
        app: database
    spec:
      containers:
      - name: postgres
        image: postgres:13-alpine
        env:
        - name: POSTGRES_PASSWORD
          value: "password"
        ports:
        - containerPort: 5432
---
apiVersion: v1
kind: Service
metadata:
  name: database
  namespace: microservices
spec:
  selector:
    app: database
  ports:
  - port: 5432
    targetPort: 5432
EOF

kubectl apply -f database.yaml

# Verify deployment
kubectl get pods -n microservices
kubectl get services -n microservices
```

**3. 实现 Default Deny Policy**

```bash
# Create default deny policy
cat > default-deny.yaml << EOF
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: microservices
spec:
  selector: all()
  types:
  - Ingress
  - Egress
EOF

kubectl apply -f default-deny.yaml
```

**4. 允许从 Frontend 到 Backend 的流量**

```bash
# Policy to allow traffic from frontend to backend
cat > frontend-to-backend.yaml << EOF
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: frontend-to-backend
  namespace: microservices
spec:
  selector: app == 'backend'
  types:
  - Ingress
  ingress:
  - action: Allow
    source:
      selector: app == 'frontend'
    destination:
      ports:
      - 80
EOF

kubectl apply -f frontend-to-backend.yaml

# Allow frontend egress to external DNS and API
cat > frontend-egress.yaml << EOF
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: frontend-egress
  namespace: microservices
spec:
  selector: app == 'frontend'
  types:
  - Egress
  egress:
  - action: Allow
    destination:
      selector: app == 'backend'
      ports:
      - 80
  # Allow DNS access
  - action: Allow
    destination:
      selector: k8s-app == 'kube-dns'
      ports:
      - 53
EOF

kubectl apply -f frontend-egress.yaml
```

**5. 允许从 Backend 到 Database 的流量**

```bash
# Policy to allow traffic from backend to database
cat > backend-to-database.yaml << EOF
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: backend-to-database
  namespace: microservices
spec:
  selector: app == 'database'
  types:
  - Ingress
  ingress:
  - action: Allow
    source:
      selector: app == 'backend'
    destination:
      ports:
      - 5432
EOF

kubectl apply -f backend-to-database.yaml

# Allow backend egress to external DNS and database
cat > backend-egress.yaml << EOF
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: backend-egress
  namespace: microservices
spec:
  selector: app == 'backend'
  types:
  - Egress
  egress:
  - action: Allow
    destination:
      selector: app == 'database'
      ports:
      - 5432
  # Allow DNS access
  - action: Allow
    destination:
      selector: k8s-app == 'kube-dns'
      ports:
      - 53
EOF

kubectl apply -f backend-egress.yaml
```

**6. 测试 Policies**

```bash
# Get frontend pod name
FRONTEND_POD=$(kubectl get pods -n microservices -l app=frontend -o jsonpath='{.items[0].metadata.name}')

# Get backend pod name
BACKEND_POD=$(kubectl get pods -n microservices -l app=backend -o jsonpath='{.items[0].metadata.name}')

# Get database pod name
DATABASE_POD=$(kubectl get pods -n microservices -l app=database -o jsonpath='{.items[0].metadata.name}')

# Test connection from frontend to backend (should succeed)
kubectl exec -it $FRONTEND_POD -n microservices -- wget -O- --timeout=2 http://backend

# Test connection from frontend to database (should fail)
kubectl exec -it $FRONTEND_POD -n microservices -- nc -zv database 5432

# Test connection from backend to database (should succeed)
kubectl exec -it $BACKEND_POD -n microservices -- nc -zv database 5432

# Test connection from backend to external site (should fail)
kubectl exec -it $BACKEND_POD -n microservices -- wget -O- --timeout=2 https://www.example.com
```

**7. Network Policy 可视化（可选）**

```bash
# Install Calico network policy visualization tool
kubectl apply -f https://raw.githubusercontent.com/tigera/ccol/master/manifests/tigera-policies-viewer/tigera-policies-viewer.yaml

# Set up port forwarding
kubectl port-forward -n tigera-policies-viewer svc/tigera-policies-viewer 8080:8080

# Access http://localhost:8080 in browser to visualize policies
```

通过本练习，你学习了如何使用 Calico 限制 EKS cluster 中 microservices 之间的 network traffic。通过实现 default deny policies 并仅显式允许必要流量，你应用了最小权限原则。这些 network policies 通过限制 cluster 内 services 之间的通信并减少潜在攻击面，帮助增强安全性。

</details>

\### 练习 2：在 EKS Cluster 中配置 IRSA 和 S3 Access

**场景：** 你是公司的一名 DevOps engineer，在 EKS cluster 中运行的 applications 需要安全访问 S3 bucket。按照安全最佳实践，你不想共享 node IAM role，而是希望使用 IRSA (IAM Roles for Service Accounts) 仅向特定 pods 授予必要权限。

**要求：**

1. 将 OIDC provider 与 EKS cluster 关联
2. 创建具有 S3 access permissions 的 IAM role
3. 创建 Kubernetes service account 并关联 IAM role
4. 部署使用该 service account 的 pod
5. 测试 S3 access

**解决方案：**

<details>

<summary>显示解决方案</summary>

**1. 将 OIDC Provider 与 EKS Cluster 关联**

```bash
# Set cluster name
CLUSTER_NAME=my-cluster
REGION=us-west-2

# Get OIDC provider URL
OIDC_PROVIDER=$(aws eks describe-cluster --name $CLUSTER_NAME --region $REGION --query "cluster.identity.oidc.issuer" --output text | sed -e "s/^https:\/\///")

# Check if OIDC provider already exists
aws iam list-open-id-connect-providers | grep $OIDC_PROVIDER

# Create OIDC provider if it doesn't exist
if [ $? -ne 0 ]; then
  echo "Creating OIDC provider..."
  eksctl utils associate-iam-oidc-provider --cluster $CLUSTER_NAME --region $REGION --approve
else
  echo "OIDC provider already exists."
fi
```

**2. 创建具有 S3 Access Permissions 的 IAM Role**

```bash
# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Set namespace and service account name
NAMESPACE=default
SERVICE_ACCOUNT_NAME=s3-access-sa

# Create trust policy
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_PROVIDER}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${OIDC_PROVIDER}:sub": "system:serviceaccount:${NAMESPACE}:${SERVICE_ACCOUNT_NAME}"
        }
      }
    }
  ]
}
EOF

# Create IAM role
ROLE_NAME=eks-s3-access-role
aws iam create-role --role-name $ROLE_NAME --assume-role-policy-document file://trust-policy.json

# Attach S3 read-only policy
aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# Get role ARN
ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query Role.Arn --output text)
echo "Role ARN: $ROLE_ARN"
```

**3. 创建 Kubernetes Service Account 并关联 IAM Role**

```bash
# Create service account
cat > service-account.yaml << EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ${SERVICE_ACCOUNT_NAME}
  namespace: ${NAMESPACE}
  annotations:
    eks.amazonaws.com/role-arn: ${ROLE_ARN}
EOF

kubectl apply -f service-account.yaml

# Verify service account
kubectl get serviceaccount $SERVICE_ACCOUNT_NAME -o yaml
```

**4. 部署使用该 Service Account 的 Pod**

```bash
# Deploy test pod
cat > s3-test-pod.yaml << EOF
apiVersion: v1
kind: Pod
metadata:
  name: s3-test-pod
  namespace: ${NAMESPACE}
spec:
  serviceAccountName: ${SERVICE_ACCOUNT_NAME}
  containers:
  - name: aws-cli
    image: amazon/aws-cli:latest
    command:
    - sleep
    - "3600"
  restartPolicy: Never
EOF

kubectl apply -f s3-test-pod.yaml

# Check pod status
kubectl get pod s3-test-pod
kubectl describe pod s3-test-pod
```

**5. 测试 S3 Access**

```bash
# Test listing S3 buckets
kubectl exec -it s3-test-pod -- aws s3 ls

# Test listing objects in a specific S3 bucket (change bucket name as needed)
kubectl exec -it s3-test-pod -- aws s3 ls s3://my-bucket/

# Verify AWS credentials
kubectl exec -it s3-test-pod -- aws sts get-caller-identity

# Check environment variables
kubectl exec -it s3-test-pod -- env | grep AWS
```

**6. 部署普通 Pod 进行对比**

```bash
# Deploy a pod using a regular service account
cat > regular-pod.yaml << EOF
apiVersion: v1
kind: Pod
metadata:
  name: regular-pod
  namespace: ${NAMESPACE}
spec:
  containers:
  - name: aws-cli
    image: amazon/aws-cli:latest
    command:
    - sleep
    - "3600"
  restartPolicy: Never
EOF

kubectl apply -f regular-pod.yaml

# Test S3 access from regular pod (should fail if node IAM role doesn't have S3 access permissions)
kubectl exec -it regular-pod -- aws s3 ls
```

**7. Cleanup**

```bash
# Delete pods
kubectl delete pod s3-test-pod regular-pod

# Delete service account
kubectl delete serviceaccount $SERVICE_ACCOUNT_NAME

# Clean up IAM role (optional)
aws iam detach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
aws iam delete-role --role-name $ROLE_NAME
```

**IRSA 的工作方式：**

1. **OIDC Provider Connection**:
   * EKS cluster 被配置为 OIDC provider。
   * 这允许 Kubernetes service account tokens 成为 AWS IAM 中受信任的身份验证机制。
2. **IAM Role Trust Policy**:
   * IAM role 的 trust policy 限制哪些 Kubernetes service accounts 可以 assume role。
   * 使用 conditions 将其限制到特定 namespaces 中的特定 service accounts。
3. **Service Account Annotation**:
   * `eks.amazonaws.com/role-arn` annotation 指定 service account 应该 assume 哪个 IAM role。
   * 此 annotation 由 EKS Pod Identity Webhook 处理。
4. **Environment Variable Injection**:
   * EKS Pod Identity Webhook 会自动将以下 environment variables 注入 pods：
     * `AWS_ROLE_ARN`
     * `AWS_WEB_IDENTITY_TOKEN_FILE`
     * `AWS_REGION`
   * AWS SDKs 使用这些 environment variables 获取 credentials。
5. **最小权限原则**:
   * 只授予 application 所需的最低权限。
   * 在本示例中，我们只授予了 S3 read-only access permissions。

通过本 lab，你学习了如何配置 IRSA，以便仅向 EKS cluster 中运行的特定 pods 授予对 AWS services 的细粒度权限。与共享 node IAM roles 相比，此方法更安全，并遵循最小权限原则。

</details>

## 高级主题

以下问题与 Amazon EKS cluster 创建相关的高级主题有关。本节测试你对 EKS cluster 创建的高级概念和最佳实践的理解。

1. 在 Amazon EKS cluster 中启用 Prefix Delegation 时，以下哪项不是会发生的变化？
   * A) 每个 ENI 被分配一个 /28 CIDR block (16 IPs)
   * B) 增加每个 node 的最大 pods 数量
   * C) 缩短 pod 启动时间
   * D) 提高 IP 地址使用效率

<details>

<summary>显示答案</summary>

**答案：C) 缩短 pod 启动时间**

**解释：** 在 Amazon EKS cluster 中启用 Prefix Delegation 时不会发生的变化是“缩短 pod 启动时间”。实际上，启用 prefix delegation 不会缩短 pod 启动时间；它甚至可能略微增加启动时间。Prefix delegation 的主要优势是增加每个 node 的最大 pods 数量并提高 IP 地址使用效率。

**启用 Prefix Delegation 时的实际变化：**

1. **每个 ENI 被分配一个 /28 CIDR block (16 IPs)**:
   * 默认情况下，VPC CNI 会从 ENI 为每个 pod 分配 secondary IP addresses。
   * 启用 prefix delegation 后，每个 ENI 会被分配 /28 CIDR blocks (16 IPs)，而不是单独的 IP addresses。
   * 这会显著增加每个 ENI 可支持的 IP 地址数量。
2. **增加每个 node 的最大 pods 数量**:
   * 使用 prefix delegation 会显著增加每个 node 的最大 pods 数量。
   * 例如，对于 m5.large instance：
     * 默认配置：最多 29 个 pods
     * 启用 prefix delegation 后：最多 110+ 个 pods
3. **提高 IP 地址使用效率**:
   * 优化大型 clusters 中的 IP 地址使用。
   * 适用于 VPC CIDR ranges 有限的环境。
   * 允许在相同 IP address space 内运行更多 pods。

**Prefix Delegation 对 Pod 启动时间的影响：**

Prefix delegation 不会缩短 pod 启动时间；它可能由于以下原因略微增加启动时间：

1. **额外的 setup overhead**:
   * CIDR block allocation 和 management 可能产生额外开销。
   * 可能需要时间进行 routing table updates。
2. **IP address allocation complexity**:
   * CIDR block allocation 和 management 可能比单独 IP address allocation 更复杂。
   * 这可能导致 pod 启动期间出现轻微延迟。
3. **Initial setup time**:
   * 为新 ENIs 分配 CIDR blocks 的初始设置时间可能更长。
   * 但是，一旦设置完成，该 ENI 上可以快速启动多个 pods。

**如何启用 Prefix Delegation：**

```bash
# Enable prefix delegation
kubectl set env daemonset aws-node -n kube-system ENABLE_PREFIX_DELEGATION=true

# Check prefix delegation status
kubectl describe daemonset aws-node -n kube-system | grep ENABLE_PREFIX_DELEGATION
```

**Prefix Delegation 限制：**

1. **EC2 Instance 支持**:
   * 只有基于 Nitro 的 instances 支持 prefix delegation。
   * 不能用于上一代 instances。
2. **VPC CNI Version 要求**:
   * 需要 VPC CNI version 1.9.0 或更高版本。
   * 此功能在早期版本中不可用。
3. **Subnet Size 要求**:
   * 需要具有足够 IP 地址空间的 subnets。
   * 在小型 subnets 中，IP 地址可能很快耗尽。
4. **过渡注意事项**:
   * 在现有 clusters 上启用时，只有新的 pods 使用 prefix delegation。
   * 现有 pods 必须重启才能应用到所有 pods。

Prefix delegation 是一项强大功能，可增加每个 node 的最大 pods 数量并提高 IP 地址使用效率，但它不会缩短 pod 启动时间。因此，“缩短 pod 启动时间”不是启用 prefix delegation 时会发生的变化。

</details>

2\. 在 Amazon EKS cluster node group 中混合 instance types 的主要优势中，以下哪项不是？ - A) Cost optimization - B) 提高 availability - C) 选择适合 workload characteristics 的 instance types - D) 简化 cluster management

<details>

<summary>显示答案</summary>

**答案：D) 简化 cluster management**

**解释：** 在 Amazon EKS cluster node group 中混合 instance types 的主要优势中，不属于主要优势的选项是“简化 cluster management”。实际上，混合多种 instance types 会使 cluster management 更复杂。混合 instance types 的主要优势是 cost optimization、提高 availability，以及选择适合 workload characteristics 的 instance types。

**混合 Instance Types 的实际优势：**

1. **Cost optimization**:
   * 混合 spot instances 和 on-demand instances
   * 利用不同 instance families 的价格差异
   * 为 workload requirements 选择最佳 price-to-performance ratio
   *   示例：

       ```yaml
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: mixed-spot-instances
           instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5ad.large", "m5n.large"]
           spot: true
           minSize: 2
           maxSize: 10
       ```
2. **提高 availability**:
   * 当特定 instance types 容量不足时使用替代 instance types
   * Spot instances 中断时可以替换为其他 types
   * 通过跨多个 instance families 多样化来分散风险
   *   示例：

       ```yaml
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: mixed-instance-types
           instanceTypes: ["c5.large", "c5a.large", "c5d.large", "c5n.large"]
           minSize: 3
           maxSize: 10
           spotAllocationStrategy: capacity-optimized
       ```
3. **选择适合 workload characteristics 的 instance types**:
   * 为不同 workload requirements 提供 instance types
   * C series 用于 compute-intensive workloads
   * R series 用于 memory-intensive workloads
   * M series 用于 balanced workloads
   * G 或 P series 用于 GPU workloads
   *   示例：

       ```yaml
       # Compute optimized node group
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: compute-optimized
           instanceTypes: ["c5.2xlarge"]
           minSize: 2
           maxSize: 10
           labels:
             workload-type: compute
           taints:
             - key: workload-type
               value: compute
               effect: NoSchedule

         # Memory optimized node group
         - name: memory-optimized
           instanceTypes: ["r5.2xlarge"]
           minSize: 2
           maxSize: 10
           labels:
             workload-type: memory
           taints:
             - key: workload-type
               value: memory
               effect: NoSchedule
       ```

**混合 Instance Types 的缺点：**

1. **增加 cluster management complexity**:
   * 需要监控和管理多种 instance types
   * 由于 performance characteristics 不同，troubleshooting 更复杂
   * 需要为不同 instance types 调整 resource requests 和 limits
2. **降低 workload predictability**:
   * Performance characteristics 可能因 instance type 而异
   * 可能出现 workload performance variations，尤其在使用 spot instances 时
3. **Resource allocation complexity**:
   * 很难为不同 instance types 设置 pod resource requests 和 limits
   * 需要使用 node selectors 和 taints 的复杂 scheduling rules
4. **Testing and validation burden**:
   * 需要在多种 instance types 上测试 applications
   * 发现 performance 和 compatibility issues 的可能性增加

**混合 Instance Types 的策略：**

1.  **按 workload 分离 node groups**:

    ```yaml
    # Node group for web servers
    - name: web-servers
      instanceTypes: ["c5.large", "c5a.large"]
      labels:
        role: web

    # Node group for databases
    - name: databases
      instanceTypes: ["r5.xlarge", "r5a.xlarge"]
      labels:
        role: database
    ```
2.  **Cost optimization strategy**:

    ```yaml
    # Base on-demand node group
    - name: on-demand-base
      instanceTypes: ["m5.large"]
      minSize: 2
      maxSize: 5
      spot: false

    # Spot node group for scaling
    - name: spot-scaling
      instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5n.large"]
      minSize: 0
      maxSize: 20
      spot: true
    ```
3.  **Availability optimization strategy**:

    ```yaml
    # Diversification across multiple instance families
    - name: high-availability
      instanceTypes: ["m5.large", "m5a.large", "c5.large", "c5a.large", "r5.large", "r5a.large"]
      minSize: 3
      maxSize: 10
      spotAllocationStrategy: capacity-optimized
    ```

混合 instance types 提供 cost optimization、提高 availability 和选择适合 workload characteristics 的 instance types 等优势，但并不会简化 cluster management，反而可能让管理更复杂。因此，“简化 cluster management”不是混合 instance types 的主要优势。

</details>

3. Amazon EKS cluster 中最安全的 node group update strategy 是什么？
   * A) In-place update
   * B) Blue/Green deployment
   * C) Canary deployment
   * D) Rolling update

<details>

<summary>显示答案</summary>

**答案：B) Blue/Green deployment**

**解释：** Amazon EKS cluster 中最安全的 node group update strategy 是 Blue/Green deployment。Blue/Green deployment 会创建新的 node group (green)，迁移 workloads，然后移除现有 node group (blue)。这种方法最安全，因为如果 update 期间出现问题，你可以立即回滚到之前的环境。

**Node Group Update Strategies 对比：**

1. **Blue/Green Deployment**:
   * **工作方式**: 创建新 node group → 迁移 workloads → 移除现有 node group
   * **优势**:
     * 可以立即 rollback
     * Updates 期间 workload disruption 最小
     * 可以比较 update 前后的环境
     * 可以在测试后切换
   * **缺点**:
     * 临时需要双倍资源
     * 实现复杂
     * 成本增加
   *   **实现示例**:

       ```bash
       # 1. Create new node group
       eksctl create nodegroup \
         --cluster my-cluster \
         --name my-nodegroup-v2 \
         --node-type m5.large \
         --nodes 3 \
         --node-ami-family AmazonLinux2 \
         --node-labels "version=v2,color=green"

       # 2. Migrate workloads (update node selector)
       kubectl patch deployment my-app -p '{"spec":{"template":{"spec":{"nodeSelector":{"color":"green"}}}}}'

       # 3. Verify all workloads have moved to new nodes
       kubectl get pods -o wide

       # 4. Remove existing node group
       eksctl delete nodegroup --cluster my-cluster --name my-nodegroup-v1
       ```
2. **Rolling Update**:
   * **工作方式**: 一次替换一个 node（cordon → drain → terminate → add new node）
   * **优势**:
     * 不需要额外资源
     * EKS managed node groups 的默认策略
     * 实现简单
   * **缺点**:
     * rollback 困难
     * Update 期间的问题可能影响整个 cluster
     * Update 时间可能较长
   *   **实现示例**:

       ```bash
       # Update managed node group
       aws eks update-nodegroup-version \
         --cluster-name my-cluster \
         --nodegroup-name my-nodegroup

       # Modify update configuration
       aws eks update-nodegroup-config \
         --cluster-name my-cluster \
         --nodegroup-name my-nodegroup \
         --update-config '{"maxUnavailable": 1}'
       ```
3. **Canary Deployment**:
   * **工作方式**: 创建小规模新 node group → 迁移部分 workloads → 验证 → 完成迁移
   * **优势**:
     * 最小化风险
     * 允许逐步验证
     * 出现问题时限制影响范围
   * **缺点**:
     * 实现复杂
     * 需要额外资源
     * 到完成完整迁移为止耗时较长
   *   **实现示例**:

       ```bash
       # 1. Create small canary node group
       eksctl create nodegroup \
         --cluster my-cluster \
         --name canary-nodegroup \
         --node-type m5.large \
         --nodes 1 \
         --node-labels "deployment=canary"

       # 2. Migrate some workloads
       kubectl patch deployment my-app -p '{"spec":{"template":{"spec":{"nodeSelector":{"deployment":"canary"}}}}}'

       # 3. Proceed with complete migration after validation
       ```
4. **In-place Update**:
   * **工作方式**: 直接在现有 nodes 上执行 updates
   * **优势**:
     * 不需要额外资源
     * 适合简单更改
   * **缺点**:
     * 风险高
     * rollback 困难
     * update 失败时可能损坏 node
     * EKS 中不推荐
   *   **实现示例**:

       ```bash
       # SSH into node for direct update (not recommended)
       ssh ec2-user@node-ip
       sudo yum update -y
       ```

**为什么 Blue/Green Deployment 最安全：**

1. **Complete isolation**:
   * 新环境与现有环境完全分离，最大限度减少影响
   * 即使 update 期间出现问题，现有环境也不受影响
2. **Immediate rollback**:
   * 出现问题时可以立即将 traffic 重定向到现有环境
   * 可以无 downtime rollback
3. **Validation opportunity**:
   * 可以在切换到 production traffic 前彻底测试新环境
   * 可以在与实际环境相同的条件下进行验证
4. **Gradual transition**:
   * 可以逐步将 traffic 迁移到新环境
   * 出现问题时限制影响范围

**Blue/Green Deployment 最佳实践：**

1. **Automation**:
   * 通过自动化 deployment process 最大限度减少人为错误
   * 与 CI/CD pipeline 集成
2. **Enhanced monitoring**:
   * 监控新环境的 performance 和 error metrics
   * 与现有环境进行比较和分析
3. **Gradual transition**:
   * 逐步将 traffic 迁移到新环境
   * 出现问题时立即 rollback
4. **Resource optimization**:
   * 迁移完成后及时清理不必要资源
   * Cost optimization

Blue/Green deployment 存在需要额外资源和实现复杂的缺点，但从安全性角度看是最优秀的方法。尤其推荐用于重要生产环境，或 update 失败会造成重大业务影响的场景。

</details>

4\. 以下哪项不是优化 Amazon EKS cluster 中 node groups Auto Scaling 的方法？ - A) 调整 Cluster Autoscaler scan interval - B) 配置 pod priority 和 preemption - C) 按 node group 标记 Auto Scaling groups - D) 所有 nodes 使用相同 instance type

<details>

<summary>显示答案</summary>

**答案：D) 所有 nodes 使用相同 instance type**

**解释：** 不属于优化 Amazon EKS cluster 中 node groups Auto Scaling 方法的选项是“所有 nodes 使用相同 instance type”。实践中，混合多种 instance types 在 cost optimization 和 availability 方面是更有效的 Auto Scaling 策略。尤其在使用 Spot Instances 时，建议指定多个 instance types 以提高 capacity availability 并降低 interruption risk。

**优化 Node Group Auto Scaling 的实际方法：**

1. **调整 Cluster Autoscaler Scan Interval**:
   * Cluster Autoscaler 定期扫描 cluster，以判断是否需要 scale up 或 scale down。
   * 你可以通过调整 scan interval 在响应时间和 resource usage 之间取得平衡。
   *   示例：

       ```yaml
       # Cluster Autoscaler deployment configuration
       apiVersion: apps/v1
       kind: Deployment
       metadata:
         name: cluster-autoscaler
         namespace: kube-system
       spec:
         template:
           spec:
             containers:
             - name: cluster-autoscaler
               image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.23.0
               command:
               - ./cluster-autoscaler
               - --v=4
               - --stderrthreshold=info
               - --cloud-provider=aws
               - --scan-interval=30s  # Adjust scan interval (default: 10 seconds)
               - --max-node-provision-time=15m
               - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/my-cluster
       ```
2. **配置 Pod Priority 和 Preemption**:
   * 使用 pod priority 和 preemption (PriorityClass) 确保重要 workloads 优先调度。
   * 当资源不足时，较低优先级 pods 会被 preempted，为较高优先级 pods 腾出空间。
   *   示例：

       ```yaml
       # Priority class definition
       apiVersion: scheduling.k8s.io/v1
       kind: PriorityClass
       metadata:
         name: high-priority
       value: 1000000
       globalDefault: false
       description: "High priority pods"
       ---
       # High priority pod
       apiVersion: v1
       kind: Pod
       metadata:
         name: high-priority-pod
       spec:
         priorityClassName: high-priority
         containers:
         - name: nginx
           image: nginx
       ```
3. **按 Node Group 标记 Auto Scaling Groups**:
   * 为 Auto Scaling groups 添加 tags，使 Cluster Autoscaler 能识别并管理特定 node groups。
   * 可以为每个 node group 配置不同的 Auto Scaling 行为。
   *   示例：

       ```bash
       # Tag Auto Scaling group
       aws autoscaling create-or-update-tags \
         --tags ResourceId=my-asg,ResourceType=auto-scaling-group,Key=k8s.io/cluster-autoscaler/enabled,Value=true,PropagateAtLaunch=true \
                ResourceId=my-asg,ResourceType=auto-scaling-group,Key=k8s.io/cluster-autoscaler/my-cluster,Value=owned,PropagateAtLaunch=true

       # Configure Auto Scaling settings per node group
       aws autoscaling update-auto-scaling-group \
         --auto-scaling-group-name my-asg \
         --min-size 2 \
         --max-size 10 \
         --desired-capacity 2
       ```

**混合多种 Instance Types 的优势：**

1. **Cost Optimization**:
   * 利用各种 instance types 之间的价格差异
   * 使用 Spot Instances 时提高 availability
   *   示例：

       ```yaml
       # Node group using various instance types
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: mixed-instances
           instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5n.large"]
           minSize: 2
           maxSize: 10
           spot: true
       ```
2. **Improved Availability**:
   * 当特定 instance types 容量不足时使用替代 instance types
   * Spot Instances 中断时可以切换到其他 types
   *   示例：

       ```yaml
       # Capacity-optimized Spot allocation strategy
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: spot-nodes
           instanceTypes: ["c5.large", "c5a.large", "c5d.large", "c5n.large"]
           minSize: 2
           maxSize: 10
           spot: true
           spotAllocationStrategy: capacity-optimized
       ```
3. **基于 Workload Characteristics 选择 Instance Types**:
   * 提供适合各种 workload requirements 的 instance types
   * 使用 node selectors 和 taints 控制 workload placement
   *   示例：

       ```yaml
       # Node groups by workload characteristics
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: general-purpose
           instanceTypes: ["m5.large"]
           minSize: 2
           maxSize: 10

         - name: compute-intensive
           instanceTypes: ["c5.large"]
           minSize: 0
           maxSize: 10
           labels:
             workload-type: compute
       ```

**Auto Scaling 优化的其他策略：**

1. **Overprovisioning**:
   * 保留一定数量的 spare resources，以应对突然的 scaling requests
   *   示例：

       ```yaml
       # Overprovisioning pod
       apiVersion: apps/v1
       kind: Deployment
       metadata:
         name: overprovisioning
         namespace: kube-system
       spec:
         replicas: 1
         selector:
           matchLabels:
             app: overprovisioning
         template:
           metadata:
             labels:
               app: overprovisioning
           spec:
             priorityClassName: overprovisioning
             containers:
             - name: reserve-resources
               image: k8s.gcr.io/pause:3.2
               resources:
                 requests:
                   cpu: 1000m
                   memory: 1000Mi
       ```
2. **优化 Scaling Policies**:
   * 使用 target tracking scaling policies
   * 使用 step scaling policies
   * 启用 predictive scaling
   *   示例：

       ```bash
       # Configure target tracking scaling policy
       aws autoscaling put-scaling-policy \
         --auto-scaling-group-name my-asg \
         --policy-name cpu70-target-tracking-scaling-policy \
         --policy-type TargetTrackingScaling \
         --target-tracking-configuration '{"PredefinedMetricSpecification":{"PredefinedMetricType":"ASGAverageCPUUtilization"},"TargetValue":70.0,"DisableScaleIn":false}'
       ```
3. **使用 Karpenter**:
   * 考虑使用 Karpenter 代替 Cluster Autoscaler
   * 更快的 node provisioning 和更灵活的 instance type selection
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
               - key: node.kubernetes.io/instance-type
                 operator: In
                 values: ["m5.large", "m5a.large", "m5d.large", "m5n.large"]
         limits:
           resources:
             cpu: 1000
             memory: 1000Gi
       ```

所有 nodes 使用相同 instance type 不是 Auto Scaling optimization strategy；相反，混合多种 instance types 在 cost optimization 和 availability 方面更有效。因此，“所有 nodes 使用相同 instance type”不是优化 node groups Auto Scaling 的方法。

</details>

5. 创建 Amazon EKS cluster 的 node groups 时，以下哪项不是应考虑的 security best practice？
   * A) 要求 IMDSv2
   * B) 应用 least privilege IAM policies
   * C) 为所有 nodes 分配 public IP addresses
   * D) 限制 security group rules

<details>

<summary>显示答案</summary>

**答案：C) 为所有 nodes 分配 public IP addresses**

**解释：** 创建 Amazon EKS cluster 的 node groups 时，不属于应考虑的 security best practice 的选项是“为所有 nodes 分配 public IP addresses”。实际的 security best practice 正好相反：将 nodes 放在 private subnets 中，并且不分配 public IP addresses。这会通过防止 nodes 从 internet 直接访问来减少攻击面。

**EKS Node Group 创建的实际 Security Best Practices：**

1. **要求 IMDSv2**:
   * 要求 Instance Metadata Service version 2 (IMDSv2) 以防御 SSRF (Server-Side Request Forgery) attacks
   * IMDSv2 使用 session-based requests 来增强安全性
   *   示例：

       ```yaml
       # eksctl configuration file
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: secure-nodes
           instanceType: m5.large
           minSize: 2
           maxSize: 5
           disableIMDSv1: true  # Disable IMDSv1
           metadataOptions:
             httpTokens: required  # Require IMDSv2
             httpPutResponseHopLimit: 1
       ```
2. **应用 Least Privilege IAM Policies**:
   * 仅向 node IAM roles 授予最低必要权限
   * 当需要超出默认 managed policies 的额外权限时，创建细粒度 policies
   *   示例：

       ```yaml
       # Least privilege policy for node IAM role
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       managedNodeGroups:
         - name: secure-nodes
           instanceType: m5.large
           minSize: 2
           maxSize: 5
           iam:
             attachPolicyARNs:
               - arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy
               - arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
               - arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy
             withAddonPolicies:
               imageBuilder: false
               autoScaler: false
               externalDNS: false
               certManager: false
               appMesh: false
               ebs: true
               fsx: false
               efs: false
               albIngress: false
               xRay: false
               cloudWatch: true
       ```
3. **限制 Security Group Rules**:
   * 限制 node security groups 的 inbound 和 outbound rules
   * 只打开最低必要 ports
   *   示例：

       ```bash
       # Create security group
       aws ec2 create-security-group \
         --group-name eks-node-sg \
         --description "Security group for EKS nodes" \
         --vpc-id vpc-12345

       # Add only rules necessary for cluster communication
       aws ec2 authorize-security-group-ingress \
         --group-id sg-12345 \
         --protocol tcp \
         --port 443 \
         --source-group sg-cluster

       aws ec2 authorize-security-group-ingress \
         --group-id sg-12345 \
         --protocol tcp \
         --port 10250 \
         --source-group sg-cluster
       ```

**不为 Nodes 分配 Public IP Addresses 的原因：**

1. **减少 Attack Surface**:
   * 没有 public IPs，nodes 无法从 internet 直接访问
   * SSH access 等管理任务通过 bastion hosts 或 AWS Systems Manager 执行
2. **改进 Security Architecture**:
   * 将 nodes 放置在 private subnets
   * 仅允许通过 NAT Gateway 进行 outbound communication
   * 仅允许通过 load balancers 进入 inbound traffic
3. **Regulatory Compliance**:
   * 许多 security standards 和 regulations 要求最大限度减少直接 internet exposure
   * 有助于满足 PCI DSS、HIPAA 和其他 regulations 的 compliance

**将 Nodes 放置在 Private Subnets 的示例：**

```yaml
# eksctl configuration file
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
vpc:
  subnets:
    private:
      us-west-2a: { id: subnet-private-a }
      us-west-2b: { id: subnet-private-b }
    public:
      us-west-2a: { id: subnet-public-a }
      us-west-2b: { id: subnet-public-b }
managedNodeGroups:
  - name: secure-nodes
    instanceType: m5.large
    minSize: 2
    maxSize: 5
    privateNetworking: true  # Place nodes in private subnets
```

**其他 EKS Security Best Practices：**

1. **启用 Encryption**:
   * EBS volume encryption
   * Secrets encryption
   *   示例：

       ```yaml
       apiVersion: eksctl.io/v1alpha5
       kind: ClusterConfig
       metadata:
         name: my-cluster
         region: us-west-2
       secretsEncryption:
         keyARN: arn:aws:kms:us-west-2:123456789012:key/key-id
       nodeGroups:
         - name: secure-nodes
           volumeEncrypted: true
           volumeKmsKeyID: arn:aws:kms:us-west-2:123456789012:key/key-id
       ```
2. **Container Security**:
   * 禁用 privileged containers
   * 使用 read-only root filesystem
   *   示例：

       ```yaml
       apiVersion: v1
       kind: Pod
       metadata:
         name: secure-pod
       spec:
         containers:
         - name: secure-container
           image: nginx
           securityContext:
             privileged: false
             readOnlyRootFilesystem: true
             allowPrivilegeEscalation: false
       ```
3. **实现 Network Policies**:
   * 限制 pod-to-pod communication
   * 应用 default deny policies
   *   示例：

       ```yaml
       apiVersion: networking.k8s.io/v1
       kind: NetworkPolicy
       metadata:
         name: default-deny
         namespace: default
       spec:
         podSelector: {}
         policyTypes:
         - Ingress
         - Egress
       ```
4. **Logging 和 Monitoring**:
   * 启用 CloudWatch Logs
   * 启用 GuardDuty EKS Protection
   *   示例：

       ```bash
       # Enable CloudWatch Logs
       aws eks update-cluster-config \
         --name my-cluster \
         --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
       ```

为所有 nodes 分配 public IP addresses 不是 security best practice；相反，它会增加安全风险。因此，“为所有 nodes 分配 public IP addresses”不是创建 Amazon EKS cluster node groups 时应考虑的 security best practice。

</details>
