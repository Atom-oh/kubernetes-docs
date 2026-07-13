# EKS Cluster 创建测验 - 第 2 部分

本测验测试你对 Amazon EKS cluster 创建相关的高级概念、安全设置和网络配置的理解。内容涵盖 cluster 安全、network policies 和 service accounts 等主题。

## 基础概念问题

1. 在 Amazon EKS cluster 中，IRSA (IAM Roles for Service Accounts) 的主要用途是什么？
   * A) 向 cluster 管理员授予 IAM 权限
   * B) 将 IAM roles 分配给 worker nodes
   * C) 向 Kubernetes service accounts 授予 AWS service 访问权限
   * D) 向 EKS control plane 授予 IAM 权限

<details>

<summary>显示答案</summary>

**答案：C) 向 Kubernetes service accounts 授予 AWS service 访问权限**

**解释：** IRSA (IAM Roles for Service Accounts) 的主要用途是向 Kubernetes service accounts 授予 AWS service 访问权限。此功能允许你在 pod 级别提供细粒度权限，并且不用共享 node 级别的 IAM roles，而是只向每个应用授予所需的最低权限。

**IRSA 的工作方式：**

1.  **OpenID Connect (OIDC) Provider 设置**:

    * EKS cluster 被配置为 OIDC provider。
    * 这使 Kubernetes service account tokens 能够成为 AWS IAM 中受信任的身份验证机制。

    ```bash
    # Associate OIDC provider
    eksctl utils associate-iam-oidc-provider --cluster my-cluster --approve
    ```
2.  **创建 IAM Role 并配置 Trust Policy**:

    * 创建 Kubernetes service account 可以 assume 的 IAM role。
    * trust policy 限制只有特定 namespaces 中的特定 service accounts 可以 assume 该 role。

    ```json
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.region.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE"
          },
          "Action": "sts:AssumeRoleWithWebIdentity",
          "Condition": {
            "StringEquals": {
              "oidc.eks.region.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:sub": "system:serviceaccount:default:my-service-account"
            }
          }
        }
      ]
    }
    ```
3.  **创建 Service Account 并关联 IAM Role**:

    * 将 IAM role ARN 作为 annotation 添加到 service account。

    ```yaml
    apiVersion: v1
    kind: ServiceAccount
    metadata:
      name: my-service-account
      namespace: default
      annotations:
        eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/my-role
    ```
4.  **在 Pod 中使用 Service Account**:

    * 在 pod manifest 中指定 service account。

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: my-pod
    spec:
      serviceAccountName: my-service-account
      containers:
      - name: my-container
        image: my-image
    ```

**IRSA 的优势：**

1. **最小权限原则**:
   * 你可以只向每个应用授予所需的最低权限。
   * 按 pod 设置不同权限，而不是共享 node 级别的 IAM roles
2. **增强安全性**:
   * 无需在代码或环境变量中存储 AWS credentials。
   * 降低 credentials 泄露风险
3. **权限隔离**:
   * 运行在同一 node 上的不同 pods 可以拥有不同的 IAM 权限。
   * 在多租户环境中很重要
4. **简化 Credential 管理**:
   * 无需直接管理 AWS credentials。
   * Credential rotation 会自动处理。

**使用 eksctl 设置 IRSA 的示例：**

```bash
# Create service account and IAM role
eksctl create iamserviceaccount \
  --name my-service-account \
  --namespace default \
  --cluster my-cluster \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
  --approve

# Verify created service account
kubectl get serviceaccount my-service-account -o yaml
```

**其他选项的问题：**

* **向 cluster 管理员授予 IAM 权限**: 这不是 IRSA 的用途。Cluster 管理员权限通常通过 aws-auth ConfigMap 管理。
* **将 IAM roles 分配给 worker nodes**: 这是通过 node IAM roles 完成的，与 IRSA 分开。Node IAM roles 会被所有 pods 共享，这可能违反最小权限原则。
* **向 EKS control plane 授予 IAM 权限**: EKS control plane 权限通过 cluster IAM role 管理，与 IRSA 无关。

IRSA 是一项重要功能，它允许 Kubernetes workloads 安全地访问 AWS services，也是在 EKS clusters 上运行应用时推荐的方法。

</details>

2\. Amazon EKS cluster 中 security groups 的主要作用是什么？ - A) 控制 pods 之间的 network traffic - B) 控制 cluster API server 与 nodes 之间的 traffic - C) 应用 Kubernetes RBAC policies - D) 管理用户身份验证

<details>

<summary>显示答案</summary>

**答案：B) 控制 cluster API server 与 nodes 之间的 traffic**

**解释：** Amazon EKS cluster 中 security groups 的主要作用是控制 cluster API server 与 nodes 之间的 traffic。Security groups 是 AWS 虚拟防火墙，用于在 EC2 instance 级别控制入站和出站 traffic。在 EKS 中，有 cluster security groups 和 node security groups，它们保护 cluster components 之间的通信。

**EKS Clusters 中 Security Groups 的类型：**

1. **Cluster Security Group**:
   * 应用于 EKS control plane。
   * 允许 worker nodes 与 control plane 之间通信。
   * 创建 EKS cluster 时默认自动创建。
   * 关键规则：
     * 允许来自 node security group 的 443 端口入站 traffic
     * 允许出站 traffic 到 node security group
2. **Node Security Group**:
   * 应用于 worker nodes。
   * 允许 nodes 之间以及 nodes 与 control plane 之间通信。
   * 关键规则：
     * 允许 nodes 之间的所有 traffic
     * 允许 443 端口出站 traffic 到 cluster security group
     * 允许来自 cluster security group 的入站 traffic
     * 为 kubelet 允许 10250 端口

**Security Group 配置示例：**

**Cluster Security Group Rules**:

```
Inbound:
- Protocol: TCP
- Port Range: 443
- Source: Node Security Group

Outbound:
- Protocol: All Traffic
- Port Range: All Ports
- Destination: 0.0.0.0/0
```

**Node Security Group Rules**:

```
Inbound:
- Protocol: All Traffic
- Source: Node Security Group itself (node-to-node communication)

- Protocol: TCP
- Port Range: 10250
- Source: Cluster Security Group (kubelet communication)

Outbound:
- Protocol: All Traffic
- Port Range: All Ports
- Destination: 0.0.0.0/0
```

**自定义 Security Groups：**

创建 EKS cluster 时可以指定自定义 security groups：

```bash
# Specifying custom security groups using AWS CLI
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
  --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345

# Specifying custom security groups using eksctl
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
vpc:
  id: vpc-12345
  securityGroup: sg-12345
  subnets:
    private:
      us-west-2a: subnet-12345
      us-west-2b: subnet-67890
```

**Pods 的 Security Groups：**

最近，EKS 还支持 pod 级别的 security groups（SecurityGroupsForPods 功能）。这允许你将 security groups 应用于单个 pods：

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

**其他选项的问题：**

* **控制 pods 之间的 network traffic**: 默认情况下，pods 之间的 network traffic 通过 Kubernetes Network Policies (NetworkPolicy) 控制，而不是 AWS security groups。虽然 SecurityGroupsForPods 功能允许在 pod 级别应用 security groups，但这不是 security groups 的主要作用。
* **应用 Kubernetes RBAC policies**: RBAC (Role-Based Access Control) 是控制 Kubernetes API resources 访问的机制，与 AWS security groups 分开。
* **管理用户身份验证**: EKS clusters 中的用户身份验证通过 AWS IAM 与 Kubernetes RBAC 的集成管理，与 security groups 无关。

Security groups 在 EKS clusters 的网络安全中发挥重要作用，保护 cluster components 之间的通信并阻止不必要的 traffic。正确的 security group 配置对于强化 EKS clusters 的安全态势至关重要。

</details>

3. 在 Amazon EKS cluster 中实现 Kubernetes Network Policies 需要什么？
   * A) AWS security group 配置
   * B) 支持 network policies 的 CNI plugin，例如 Calico 或 Cilium
   * C) AWS Network Firewall 设置
   * D) 启用 VPC Flow Logs

<details>

<summary>显示答案</summary>

**答案：B) 支持 network policies 的 CNI plugin，例如 Calico 或 Cilium**

**解释：** 要在 Amazon EKS cluster 中实现 Kubernetes Network Policies，你需要一个支持 network policies 的 CNI (Container Network Interface) plugin，例如 Calico 或 Cilium。默认的 Amazon VPC CNI plugin 不支持 network policies，因此必须安装额外组件。

**支持 Network Policy 的 CNI 选项：**

1. **Calico**:
   * 广泛使用的开源 networking 和 network security 解决方案
   * 可在 EKS 中与 Amazon VPC CNI 一起使用
   *   安装方法：

       ```bash
       # Install Calico using Helm
       helm repo add projectcalico https://docs.projectcalico.org/charts
       helm install calico projectcalico/tigera-operator --namespace tigera-operator --create-namespace

       # Or install using manifest files
       kubectl apply -f https://docs.projectcalico.org/manifests/calico-vxlan.yaml
       ```
2. **Cilium**:
   * 基于 eBPF 的 networking、安全和可观测性解决方案
   * 提供高性能和高级功能
   *   安装方法：

       ```bash
       # Install Cilium using Helm
       helm repo add cilium https://helm.cilium.io/
       helm install cilium cilium/cilium --namespace kube-system
       ```
3. **AWS CNI with Cilium**:
   * 同时使用 Amazon VPC CNI 和 Cilium 的混合方法
   * VPC CNI 处理 pod networking，Cilium 处理 network policies
   *   安装方法：

       ```bash
       # Install Cilium in network policy only mode
       helm install cilium cilium/cilium --namespace kube-system \
         --set enableIPv4Masquerade=false \
         --set tunnel=disabled \
         --set installIptablesRules=false \
         --set autoDirectNodeRoutes=false \
         --set policyEnforcementMode=default
       ```

**Network Policy 示例：**

```yaml
# Default deny policy
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

# Allow communication between specific applications
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

**验证 Network Policy 实现：**

```bash
# Verify network policy support
kubectl get pods -n kube-system | grep -E 'calico|cilium'

# Apply test network policy
kubectl apply -f test-network-policy.yaml

# Test connectivity
kubectl run -it --rm --restart=Never busybox --image=busybox -- wget -O- --timeout=2 http://service-name
```

**其他选项的问题：**

* **AWS security group 配置**: AWS security groups 在 EC2 instance 级别工作，不能用于在 Kubernetes pods 之间实现细粒度 network policies。虽然 SecurityGroupsForPods 功能允许将 security groups 应用于 pods，但这是不同于 Kubernetes NetworkPolicy 的机制。
* **AWS Network Firewall 设置**: AWS Network Firewall 在 VPC 级别工作，不能用于在 Kubernetes pods 之间实现细粒度 network policies。
* **启用 VPC Flow Logs**: VPC Flow Logs 用于监控和记录 network traffic，但不能用于实现 network policies。

Network policies 是控制 microservices 之间通信并增强 Kubernetes clusters 内部安全性的重要工具。要在 EKS 中实现 network policies，必须安装 Calico 或 Cilium 等额外 CNI plugins。

</details>

4. 在 Amazon EKS cluster 中配置 Secrets 加密的正确方式是什么？
   * A) 创建 EKS cluster 时使用 AWS KMS key 启用加密
   * B) 将 Kubernetes Secrets 迁移到 AWS Secrets Manager
   * C) 将所有 Secrets 编码为 Base64
   * D) 将加密 sidecar container 部署到 EKS cluster

<details>

<summary>显示答案</summary>

**答案：A) 创建 EKS cluster 时使用 AWS KMS key 启用加密**

**解释：** 在 Amazon EKS cluster 中配置 Secrets 加密的正确方式，是在创建 EKS cluster 时或在现有 cluster 上使用 AWS KMS (Key Management Service) key 启用加密。此方法可确保 Kubernetes Secrets 存储在 etcd 中时被加密。

**配置 EKS Secrets 加密的步骤：**

1.  **创建 KMS Key 或使用现有 Key**:

    ```bash
    # Create KMS key
    aws kms create-key --description "EKS Secrets Encryption Key"

    # Store the created key ID
    KEY_ID=$(aws kms create-key --query KeyMetadata.KeyId --output text)
    ```
2.  **创建新 Cluster 时启用加密**:

    ```bash
    # Enable encryption using AWS CLI
    aws eks create-cluster \
      --name my-cluster \
      --role-arn arn:aws:iam::123456789012:role/EksClusterRole \
      --resources-vpc-config subnetIds=subnet-12345,subnet-67890 \
      --encryption-config '[{"resources":["secrets"],"provider":{"keyArn":"arn:aws:kms:region:123456789012:key/'$KEY_ID'"}}]'

    # Enable encryption using eksctl
    cat > cluster.yaml << EOF
    apiVersion: eksctl.io/v1alpha5
    kind: ClusterConfig
    metadata:
      name: my-cluster
      region: us-west-2
    secretsEncryption:
      keyARN: arn:aws:kms:us-west-2:123456789012:key/$KEY_ID
    EOF

    eksctl create cluster -f cluster.yaml
    ```
3.  **在现有 Cluster 上启用加密**:

    ```bash
    # For existing clusters, you cannot update the encryption configuration, so you need to create a new cluster and migrate workloads.
    ```
4.  **验证加密配置**:

    ```bash
    # Check cluster information
    aws eks describe-cluster --name my-cluster --query cluster.encryptionConfig
    ```

**使用加密的 Secrets：**

启用加密后，创建和使用 Secrets 的方法不会改变。所有加密和解密都由 EKS control plane 自动处理。

```yaml
# Create Secret
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
type: Opaque
data:
  username: YWRtaW4=  # base64 encoded "admin"
  password: cGFzc3dvcmQ=  # base64 encoded "password"
```

```bash
# Create Secret
kubectl create secret generic my-secret --from-literal=username=admin --from-literal=password=password

# Verify Secret
kubectl get secret my-secret -o yaml
```

**配置 KMS Key 权限：**

你需要配置适当的权限，使 EKS cluster 能够使用 KMS key：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowEKSToUseKMSKey",
      "Effect": "Allow",
      "Principal": {
        "Service": "eks.amazonaws.com"
      },
      "Action": [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:ReEncrypt*",
        "kms:GenerateDataKey*",
        "kms:DescribeKey"
      ],
      "Resource": "*"
    }
  ]
}
```

**其他选项的问题：**

* **将 Kubernetes Secrets 迁移到 AWS Secrets Manager**: 这是一种可行方法，但它与标准 Kubernetes Secrets API 的兼容性较低，并且需要额外配置和集成。此外，所有应用都需要修改为从 AWS Secrets Manager 获取 secrets。
* **将所有 Secrets 编码为 Base64**: Kubernetes Secrets 默认已经使用 Base64 编码。但是，Base64 是一种编码方式，不是加密，不能提供安全性。
* **将加密 sidecar container 部署到 EKS cluster**: 这不是标准方法，并且向所有 pods 添加 sidecars 会引入复杂性。它还需要与 Kubernetes API server 集成。

使用 AWS KMS 的 EKS Secrets 加密是保护存储在 etcd 中的 Secrets 的最有效且集成度最高的方式。这让你可以保护静态敏感数据，并利用 AWS 强大的 key management 能力。

</details>
5\. 自定义 Amazon EKS cluster 中 worker nodes 的 kubelet 配置的正确方式是什么？ - A) 在 EKS console 中修改 cluster 配置 - B) 创建 node group 时使用 --kubelet-extra-args 参数 - C) 使用 kubectl edit node 命令 - D) 使用 AWS Systems Manager 更改 node 配置

<details>

<summary>显示答案</summary>

**答案：B) 创建 node group 时使用 --kubelet-extra-args 参数**

**解释：** 自定义 Amazon EKS cluster 中 worker nodes 的 kubelet 配置的正确方式，是在创建 node group 时使用 `--kubelet-extra-args` 参数。此方法允许你在 node bootstrap 时向 kubelet 传递额外参数。

**自定义 kubelet 配置的方法：**

1.  **将 Launch Templates 与 Managed Node Groups 一起使用**:

    * 在 launch template 的 user data 部分自定义 bootstrap script。

    ```bash
    #!/bin/bash
    set -o xtrace
    /etc/eks/bootstrap.sh my-cluster \
      --kubelet-extra-args '--max-pods=110 --kube-reserved memory=0.3Gi,cpu=100m --system-reserved memory=0.5Gi,cpu=200m --eviction-hard memory.available<500Mi'
    ```
2. **使用 eksctl 创建 Node Groups**:

```bash
# Create node group with kubelet arguments
eksctl create nodegroup \
  --cluster my-cluster \
  --name my-nodegroup \
  --node-type m5.large \
  --nodes 3 \
  --kubelet-extra-args "--max-pods=110 --kube-reserved memory=0.3Gi,cpu=100m"
```

3.  **使用 eksctl 配置文件**:

    ```yaml
    apiVersion: eksctl.io/v1alpha5
    kind: ClusterConfig
    metadata:
      name: my-cluster
      region: us-west-2
    managedNodeGroups:
      - name: my-nodegroup
        instanceType: m5.large
        minSize: 2
        maxSize: 5
        kubeletExtraArgs:
          max-pods: "110"
          kube-reserved: "memory=0.3Gi,cpu=100m"
          system-reserved: "memory=0.5Gi,cpu=200m"
          eviction-hard: "memory.available<500Mi"
    ```
4.  **为 self-managed node groups 使用 user data script**:

    ```bash
    #!/bin/bash
    set -o xtrace
    /etc/eks/bootstrap.sh my-cluster \
      --kubelet-extra-args '--max-pods=110 --node-labels=node.kubernetes.io/role=worker,environment=prod'
    ```

**常见自定义 kubelet 参数：**

1. **max-pods**:
   * 设置每个 node 的最大 pods 数量
   * 示例：`--max-pods=110`
2. **node-labels**:
   * 向 node 添加 labels
   * 示例：`--node-labels=environment=prod,node-type=worker`
3. **kube-reserved**:
   * 为 Kubernetes system components 预留 resources
   * 示例：`--kube-reserved=cpu=100m,memory=0.3Gi,ephemeral-storage=1Gi`
4. **system-reserved**:
   * 为 OS system daemons 预留 resources
   * 示例：`--system-reserved=cpu=100m,memory=0.5Gi,ephemeral-storage=1Gi`
5. **eviction-hard**:
   * 设置 hard eviction 阈值
   * 示例：`--eviction-hard=memory.available<500Mi,nodefs.available<10%`
6. **cgroup-driver**:
   * 设置 cgroup driver
   * 示例：`--cgroup-driver=systemd`

**如何验证配置：**

```bash
# SSH into the node
ssh -i ~/.ssh/id_rsa ec2-user@<node-ip>

# Check kubelet service configuration
sudo systemctl status kubelet
sudo cat /etc/systemd/system/kubelet.service.d/10-kubelet-args.conf

# Check running kubelet process arguments
ps aux | grep kubelet
```

**其他选项的问题：**

* **在 EKS console 中修改 cluster 配置**: 虽然 EKS console 允许你修改 cluster 级别配置，但它不提供直接修改单个 nodes 的 kubelet 配置的选项。
* **使用 kubectl edit node 命令**: `kubectl edit node` 命令可以修改 node object metadata，但不能更改 kubelet 配置。kubelet 配置作为 node OS 上的 service 运行，不能通过 Kubernetes API 直接修改。
* **使用 AWS Systems Manager 更改 node 配置**: AWS Systems Manager 可用于在 nodes 上运行命令或更改配置，但此方法是在 nodes 已创建后应用的。此外，更改 kubelet 配置后必须重启 service，这可能影响正在运行的 pods。因此，在 node group 创建时配置更安全，也是推荐方法。

自定义 kubelet 配置允许你优化 node resource 管理、pod 密度、eviction policies 等，以满足 workload 需求。但是，这些更改可能影响 cluster 稳定性，因此应仔细测试。

</details>

6. Amazon EKS clusters 中替代 Pod Security Policy 的推荐机制是什么？
   * A) AWS Security Hub
   * B) Pod Security Admission 或 Kyverno 等 policy engines
   * C) AWS Config Rules
   * D) EKS Security Groups

<details>

<summary>显示答案</summary>

**答案：B) Pod Security Admission 或 Kyverno 等 policy engines**

**解释：** 在 Amazon EKS clusters 中替代 Pod Security Policy (PSP) 的推荐机制是 Pod Security Admission 或 Kyverno 等 policy engines。从 Kubernetes 1.21 开始，PSP 被弃用，并在 Kubernetes 1.25 中被完全移除。Pod Security Admission 作为替代方案引入，也可以使用 Kyverno 或 OPA Gatekeeper 等 policy engines 作为替代。

**Pod Security Admission：**

Pod Security Admission 从 Kubernetes 1.23 开始作为 beta 功能引入，并在 1.25 版本中成为稳定功能。它是内置 Kubernetes 功能，提供三个安全级别（Privileged、Baseline、Restricted）。

1.  **配置方法**:

    ```yaml
    # Apply Pod Security standards to namespace
    apiVersion: v1
    kind: Namespace
    metadata:
      name: my-namespace
      labels:
        pod-security.kubernetes.io/enforce: restricted
        pod-security.kubernetes.io/audit: restricted
        pod-security.kubernetes.io/warn: restricted
    ```
2. **安全级别**:
   * **Privileged**: 无限制，允许所有功能
   * **Baseline**: 防止已知的 privilege escalations
   * **Restricted**: 强安全加固，应用最小权限原则
3. **模式**:
   * **enforce**: 发生违规时拒绝创建 pod
   * **audit**: 在 audit logs 中记录违规
   * **warn**: 发生违规时显示 warning messages

**Kyverno：**

Kyverno 是 Kubernetes-native policy engine，使用基于 YAML 的 policies 来验证、变更和生成 cluster resources。

1.  **安装方法**:

    ```bash
    # Install Kyverno using Helm
    helm repo add kyverno https://kyverno.github.io/kyverno/
    helm install kyverno kyverno/kyverno --namespace kyverno --create-namespace
    ```
2.  **Policy 示例**:

    ```yaml
    # Policy to prevent privileged containers
    apiVersion: kyverno.io/v1
    kind: ClusterPolicy
    metadata:
      name: disallow-privileged-containers
    spec:
      validationFailureAction: enforce
      rules:
      - name: privileged-containers
        match:
          resources:
            kinds:
            - Pod
        validate:
          message: "Privileged containers are not allowed"
          pattern:
            spec:
              containers:
              - name: "*"
                securityContext:
                  privileged: false
    ```

**OPA Gatekeeper：**

OPA (Open Policy Agent) Gatekeeper 是 Kubernetes 中另一个流行的 policy management 解决方案。

1.  **安装方法**:

    ```bash
    # Install Gatekeeper
    kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/master/deploy/gatekeeper.yaml
    ```
2.  **Policy 示例**:

    ```yaml
    # ConstraintTemplate definition
    apiVersion: templates.gatekeeper.sh/v1beta1
    kind: ConstraintTemplate
    metadata:
      name: k8spsprivilegedcontainer
    spec:
      crd:
        spec:
          names:
            kind: K8sPSPPrivilegedContainer
      targets:
      - target: admission.k8s.gatekeeper.sh
        rego: |
          package k8spsprivilegedcontainer
          violation[{"msg": msg}] {
            c := input.review.object.spec.containers[_]
            c.securityContext.privileged
            msg := sprintf("Privileged container is not allowed: %v", [c.name])
          }

    # Apply Constraint
    apiVersion: constraints.gatekeeper.sh/v1beta1
    kind: K8sPSPPrivilegedContainer
    metadata:
      name: psp-privileged-container
    spec:
      match:
        kinds:
        - apiGroups: [""]
          kinds: ["Pod"]
    ```

**EKS 的实施建议：**

1. **启用 Pod Security Admission**:
   * 在 EKS 1.23 及以上版本中默认可用
   * 向 namespaces 应用适当的 labels
2. **安装 Kyverno 或 Gatekeeper**:
   * 当需要更复杂 policies 时
   * 当需要对多种 resource types 应用 policies 时
3. **逐步迁移**:
   * 从 PSP 逐步迁移到新解决方案
   * 从 audit 模式开始识别问题，然后切换到 enforce 模式

**其他选项的问题：**

* **AWS Security Hub**: AWS Security Hub 是用于监控 AWS resources 安全态势的 service，但不能用于在 Kubernetes 中应用 pod 级别的 security policies。
* **AWS Config Rules**: AWS Config 是用于评估 AWS resource configurations 的 service，但不能用于在 Kubernetes 中应用 pod 级别的 security policies。
* **EKS Security Groups**: EKS Security Groups 用于控制 network traffic，不能用于限制 pod security contexts 或 privileges。

随着 Pod Security Policy (PSP) 被移除，EKS clusters 应使用 Pod Security Admission、Kyverno 或 OPA Gatekeeper 等替代机制来强化 pod 安全。这些工具可以限制 privileged containers、host namespace access、host path mounts 等。

</details>

7\. 配置 IRSA (IAM Roles for Service Accounts) 以在 Amazon EKS cluster 中将 pod identity 与 AWS IAM 集成的第一步是什么？ - A) 创建 IAM role - B) 创建 service account - C) 关联 OIDC provider - D) 修改 pod manifest

<details>

<summary>显示答案</summary>

**答案：C) 关联 OIDC provider**

**解释：** 在 Amazon EKS cluster 中配置 IRSA (IAM Roles for Service Accounts) 的第一步是关联 OIDC (OpenID Connect) provider。OIDC provider 是在 AWS IAM 与 Kubernetes service accounts 之间建立信任关系所必需的。这允许 Kubernetes service account tokens 成为 AWS IAM 中受信任的身份验证机制。

**IRSA 配置步骤顺序：**

1.  **关联 OIDC provider**:

    * 检查 EKS cluster 的 OIDC issuer URL
    * 在 AWS IAM 中创建 OIDC provider

    ```bash
    # Check OIDC issuer URL
    aws eks describe-cluster --name my-cluster --query "cluster.identity.oidc.issuer" --output text
    # Example output: https://oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE

    # Associate OIDC provider
    eksctl utils associate-iam-oidc-provider --cluster my-cluster --approve

    # Or use AWS CLI
    aws iam create-open-id-connect-provider \
      --url https://oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE \
      --thumbprint-list 9e99a48a9960b14926bb7f3b02e22da2b0ab7280 \
      --client-id-list sts.amazonaws.com
    ```
2.  **创建 IAM role**:

    * 创建 service account 将要 assume 的 IAM role
    * 在 trust policy 中包含 OIDC provider 和 service account 条件

    ```json
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE"
          },
          "Action": "sts:AssumeRoleWithWebIdentity",
          "Condition": {
            "StringEquals": {
              "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:sub": "system:serviceaccount:default:my-service-account"
            }
          }
        }
      ]
    }
    ```
3.  **创建 service account**:

    * 创建带有 IAM role ARN annotation 的 service account

    ```yaml
    apiVersion: v1
    kind: ServiceAccount
    metadata:
      name: my-service-account
      namespace: default
      annotations:
        eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/my-role
    ```
4.  **修改 pod manifest**:

    * 在 pod manifest 中指定 service account

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: my-pod
    spec:
      serviceAccountName: my-service-account
      containers:
      - name: my-container
        image: my-image
    ```

**使用 eksctl 简化 IRSA 设置：**

eksctl 提供可自动完成上述所有步骤的命令：

```bash
# Associate OIDC provider
eksctl utils associate-iam-oidc-provider --cluster my-cluster --approve

# Create service account and IAM role
eksctl create iamserviceaccount \
  --name my-service-account \
  --namespace default \
  --cluster my-cluster \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
  --approve
```

**验证 IRSA 是否正常工作：**

```bash
# Check service account
kubectl get serviceaccount my-service-account -o yaml

# Run test pod
kubectl run -it --rm \
  --image amazon/aws-cli \
  --serviceaccount my-service-account \
  aws-cli -- s3 ls
```

**其他选项的问题：**

* **创建 IAM role**: 创建 IAM role 是 IRSA 配置的第二步。必须先关联 OIDC provider，这样 IAM role 的 trust policy 才能引用 OIDC provider。
* **创建 service account**: 创建 service account 是 IRSA 配置的第三步。必须先创建 IAM role，这样才能将 IAM role ARN 作为 annotation 添加到 service account。
* **修改 pod manifest**: 修改 pod manifest 是 IRSA 配置的最后一步。必须先创建 service account，这样 pod 才能引用该 service account。

IRSA 是一种安全且高效的方式，用于向 Kubernetes workloads 授予对 AWS services 的细粒度权限。这让你可以向每个应用只授予所需的最低权限，而不是共享 node 级别的 IAM roles。IRSA 配置的第一步是关联 OIDC provider，这对于建立 AWS IAM 与 Kubernetes service accounts 之间的信任关系至关重要。

</details>

8. 在 Amazon EKS cluster 中启用 control plane logs 的正确方式是什么？
   * A) 在 EKS control plane 上安装 CloudWatch agent
   * B) 通过 AWS CLI 或 console 启用 cluster logging 配置
   * C) 使用 Fluentd 配置 log forwarding
   * D) SSH 到 EKS control plane nodes 修改 log 配置

<details>

<summary>显示答案</summary>

**答案：B) 通过 AWS CLI 或 console 启用 cluster logging 配置**

**解释：** 在 Amazon EKS cluster 中启用 control plane logs 的正确方式，是通过 AWS CLI 或 AWS Management Console 启用 cluster logging 配置。由于 EKS 是 managed service，control plane 由 AWS 管理，因此你无法直接访问它或安装 agents。相反，必须通过 AWS 提供的 APIs 配置 logging。

**使用 AWS CLI 启用 control plane logs：**

```bash
# Enable all log types
aws eks update-cluster-config \
  --name my-cluster \
  --region us-west-2 \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# Enable only specific log types
aws eks update-cluster-config \
  --name my-cluster \
  --region us-west-2 \
  --logging '{"clusterLogging":[{"types":["api","audit"],"enabled":true},{"types":["authenticator","controllerManager","scheduler"],"enabled":false}]}'
```

**使用 eksctl 启用 control plane logs：**

```bash
# Enable all log types
eksctl utils update-cluster-logging \
  --enable-types api,audit,authenticator,controllerManager,scheduler \
  --cluster my-cluster \
  --region us-west-2

# Enable only specific log types
eksctl utils update-cluster-logging \
  --enable-types api,audit \
  --disable-types authenticator,controllerManager,scheduler \
  --cluster my-cluster \
  --region us-west-2
```

**使用 AWS Management Console 启用 control plane logs：**

1. 登录 AWS Management Console。
2. 导航到 EKS service。
3. 从 cluster 列表中选择目标 cluster。
4. 选择 "Logging" tab。
5. 点击 "Manage"。
6. 选择要启用的 log types：
   * API server (api)
   * Audit (audit)
   * Authenticator (authenticator)
   * Controller manager (controllerManager)
   * Scheduler (scheduler)
7. 点击 "Save changes"。

**可用的 log types：**

1. **API server (api)**:
   * 来自 Kubernetes API server 的 logs
   * 包含 API request 和 response 信息
2. **Audit (audit)**:
   * cluster 中所有活动的 audit logs
   * 对安全和合规目的很重要
3. **Authenticator (authenticator)**:
   * 来自 AWS IAM Authenticator 的 logs
   * 有助于排查身份验证问题
4. **Controller manager (controllerManager)**:
   * 来自 Kubernetes controller manager 的 logs
   * 包含 resource state management 信息
5. **Scheduler (scheduler)**:
   * 来自 Kubernetes scheduler 的 logs
   * 包含 pod scheduling 决策信息

**如何查看 logs：**

启用的 logs 存储在 CloudWatch Logs 中，可以在以下 log group 中查看：

```
/aws/eks/my-cluster/cluster
```

每种 log type 都作为单独的 log stream 存储：

```
kube-apiserver-xxxxx
audit-xxxxx
authenticator-xxxxx
kube-controller-manager-xxxxx
kube-scheduler-xxxxx
```

**成本注意事项：**

* Control plane logs 受 CloudWatch Logs pricing 约束。
* 启用所有 log types 可能会生成大量 logs。
* 为优化成本，建议只选择性启用所需的 log types。
* 可以通过设置适当的 log retention periods 来管理成本。

**其他选项的问题：**

* **在 EKS control plane 上安装 CloudWatch agent**: EKS control plane 由 AWS 管理，因此你无法直接访问它或安装 agents。
* **使用 Fluentd 配置 log forwarding**: Fluentd 可用于收集 worker nodes 的 logs，但不能访问 EKS control plane logs。
* **SSH 到 EKS control plane nodes 修改 log 配置**: EKS control plane nodes 由 AWS 管理，因此你不能直接 SSH 进入它们。

EKS control plane logs 为 cluster troubleshooting、security audits 和 compliance 提供重要信息。你可以通过 AWS CLI 或 AWS Management Console 选择性启用所需的 log types 来有效监控。

</details>

9. 更改 Amazon EKS cluster 中 node group instance type 的正确方式是什么？
   * A) 在 AWS Management Console 中直接修改 node group instance type
   * B) 使用新的 instance type 创建新 node group 并迁移 workloads
   * C) 使用 kubectl edit 命令修改 node specifications
   * D) 使用 AWS CLI update-nodegroup-config 命令

<details>

<summary>显示答案</summary>

**答案：B) 使用新的 instance type 创建新 node group 并迁移 workloads**

**解释：** 更改 Amazon EKS cluster 中 node group instance type 的正确方式，是使用新的 instance type 创建新的 node group，然后迁移 workloads。在 EKS managed node groups 中，创建后无法直接更改 instance type，因此必须创建新的 node group、迁移 workloads，然后删除现有 node group。

**更改 node group instance type 的步骤：**

1.  **创建新 node group**:

    ```bash
    # Create new node group using eksctl
    eksctl create nodegroup \
      --cluster my-cluster \
      --name my-new-nodegroup \
      --node-type m5.large \
      --nodes 3 \
      --nodes-min 1 \
     --nodes-max 5 \
     --node-labels "migration-target=true"
    ```

## Create new node group using AWS CLI

aws eks create-nodegroup\
\--cluster-name my-cluster\
\--nodegroup-name my-new-nodegroup\
\--subnets subnet-12345 subnet-67890\
\--instance-types m5.large\
\--scaling-config minSize=1,maxSize=5,desiredSize=3\
\--node-role arn:aws:iam::123456789012:role/EksNodeRole\
\--labels migration-target=true

````

2. **验证新 node group 状态**:
 ```bash
 # Check node group status
 aws eks describe-nodegroup \
   --cluster-name my-cluster \
   --nodegroup-name my-new-nodegroup \
   --query "nodegroup.status"

 # Check nodes
 kubectl get nodes --label-columns migration-target
````

3.  **迁移 workloads**:

    **方法 1：使用 Cordoning 和 Draining**

    ```bash
    # Identify nodes in the existing node group
    OLD_NODES=$(kubectl get nodes -l alpha.eksctl.io/nodegroup-name=my-old-nodegroup -o jsonpath='{.items[*].metadata.name}')

    # Cordon nodes (prevent new pod scheduling)
    for node in $OLD_NODES; do
      kubectl cordon $node
    done

    # Drain nodes (remove existing pods)
    for node in $OLD_NODES; do
      kubectl drain $node --ignore-daemonsets --delete-emptydir-data
    done
    ```

    **方法 2：使用 Pod Selector**

    ```yaml
    # Deploy to new nodes using node selector
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: my-app
    spec:
      template:
        spec:
          nodeSelector:
            migration-target: "true"
    ```

    **方法 3：Blue/Green Deployment**

    * 将新的 deployment version 部署到新 node group
    * 逐步将 traffic 切换到新 version
    * 移除现有 deployment version
4.  **删除现有 node group**:

    ```bash
    # Delete node group using eksctl
    eksctl delete nodegroup \
      --cluster my-cluster \
      --name my-old-nodegroup

    # Delete node group using AWS CLI
    aws eks delete-nodegroup \
      --cluster-name my-cluster \
      --nodegroup-name my-old-nodegroup
    ```

**迁移期间的注意事项：**

1.  **最小化 workload 中断**:

    * 配置 PodDisruptionBudget

    ```yaml
    apiVersion: policy/v1
    kind: PodDisruptionBudget
    metadata:
      name: my-app-pdb
    spec:
      minAvailable: 2  # or maxUnavailable: 1
      selector:
        matchLabels:
          app: my-app
    ```

    * 使用 rolling update strategy
2. **Resource 需求**:
   * 验证新 instance type 是否满足 workload 需求
   * 考虑 CPU、memory、storage 和 networking 需求
3. **Stateful workloads**:
   * 验证使用 persistent volumes 的 workloads 的数据持久性
   * 必要时执行 backups
4. **成本影响**:
   * 评估新 instance type 的成本影响
   * 迁移期间两个 node groups 同时运行，成本会暂时增加

**其他选项的问题：**

* **在 AWS Management Console 中直接修改 node group instance type**: 在 EKS managed node groups 中，创建后不能直接修改 instance type。
* **使用 kubectl edit 命令修改 node specifications**: kubectl 用于修改 Kubernetes API objects，但 node 的底层 instance type 在 AWS infrastructure 级别确定，不能通过 kubectl 更改。
* **使用 AWS CLI update-nodegroup-config 命令**: `update-nodegroup-config` 命令可以修改 node group 的 scaling configuration、labels、taints 等，但不能更改 instance type。

为了优化 cluster 性能、降低成本或满足新的 workload 需求，可能需要更改 node group 的 instance type。创建新 node group 并迁移 workloads 是在尽量减少中断的同时安全更改 instance types 的推荐方法。

</details>

10\. 在 Amazon EKS cluster 中将 Kubernetes taints 应用于 node group 的正确方式是什么？ - A) 使用 kubectl taint 命令 - B) 创建 node group 时使用 --taints 参数 - C) 在 AWS Management Console 中配置 node group taints - D) 在 node bootstrap script 中修改 kubelet 配置

<details>

<summary>显示答案</summary>

**答案：B) 创建 node group 时使用 --taints 参数**

**解释：** 在 Amazon EKS cluster 中将 Kubernetes taints 应用于 node group 的正确方式，是在创建 node group 时使用 `--taints` 参数。EKS managed node groups 提供在创建时或更新期间配置 taints 的能力。使用此方法可确保 taints 一致地应用到 node group 中的所有 nodes，并在 nodes 被替换时保持。

**使用 eksctl 配置 taints：**

```bash
# Create node group with taints
eksctl create nodegroup \
  --cluster my-cluster \
  --name tainted-ng \
  --node-type m5.large \
  --nodes 3 \
  --taints "dedicated=gpu:NoSchedule,special=true:PreferNoSchedule"

# Configure taints using configuration file
cat > nodegroup.yaml << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: tainted-ng
    instanceType: m5.large
    minSize: 2
    maxSize: 5
    taints:
      - key: dedicated
        value: gpu
        effect: NoSchedule
      - key: special
        value: "true"
        effect: PreferNoSchedule
EOF

eksctl create nodegroup -f nodegroup.yaml
```

**使用 AWS CLI 配置 taints：**

```bash
# Create node group with taints
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name tainted-ng \
  --subnets subnet-12345 subnet-67890 \
  --instance-types m5.large \
  --scaling-config minSize=2,maxSize=5,desiredSize=3 \
  --node-role arn:aws:iam::123456789012:role/EksNodeRole \
  --taints "key=dedicated,value=gpu,effect=NoSchedule" "key=special,value=true,effect=PreferNoSchedule"

# Update taints on existing node group
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name tainted-ng \
  --taints "addOrUpdateTaints=[{key=dedicated,value=gpu,effect=NoSchedule}],removeTaints=[{key=special}]"
```

**使用 AWS Management Console 配置 taints：**

1. 登录 AWS Management Console。
2. 导航到 EKS service。
3. 选择 cluster。
4. 选择 "Compute" tab。
5. 点击 "Add node group"。
6. 输入 node group details。
7. 在 "Kubernetes taints" 部分，点击 "Add taint"。
8. 输入 key、value 和 effect。
9. 点击 "Create"。

**Taint effect 类型：**

1. **NoSchedule**:
   * 没有匹配 toleration 的 Pods 不会被调度到该 node。
   * 现有 pods 不受影响。
2. **PreferNoSchedule**:
   * 没有匹配 toleration 的 Pods 最好不要被调度到该 node，但不保证。
   * 如果它们无法调度到其他 nodes，则可能会被调度到此 node。
3. **NoExecute**:
   * 没有匹配 toleration 的 Pods 不会被调度到该 node。
   * 已经运行但没有匹配该 taint 的 toleration 的 Pods 将被 evicted。

**taints 的常见使用场景：**

1.  **隔离特殊硬件 nodes**:

    ```bash
    # Apply taint to GPU nodes
    eksctl create nodegroup \
      --cluster my-cluster \
      --name gpu-nodes \
      --node-type p3.2xlarge \
      --taints "dedicated=gpu:NoSchedule"

    # Add toleration to GPU workload
    apiVersion: v1
    kind: Pod
    metadata:
      name: gpu-pod
    spec:
      tolerations:
      - key: "dedicated"
        operator: "Equal"
        value: "gpu"
        effect: "NoSchedule"
      containers:
      - name: gpu-container
        image: gpu-image
    ```
2.  **准备 node maintenance**:

    ```bash
    # Apply taint to node
    kubectl taint nodes node1 maintenance=planned:NoSchedule

    # Remove taint after maintenance
    kubectl taint nodes node1 maintenance=planned:NoSchedule-
    ```
3.  **为特定 workloads 配置 dedicated nodes**:

    ```bash
    # Node group dedicated to production workloads
    eksctl create nodegroup \
      --cluster my-cluster \
      --name prod-nodes \
      --node-type m5.large \
      --taints "environment=production:NoSchedule"

    # Add toleration to production deployment
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: prod-app
    spec:
      template:
        spec:
          tolerations:
          - key: "environment"
            operator: "Equal"
            value: "production"
            effect: "NoSchedule"
    ```

**其他选项的问题：**

* **使用 kubectl taint 命令**: 你可以使用 `kubectl taint` 命令向单个 nodes 应用 taints，但这是临时更改，nodes 被替换时 taints 不会保持。它也难以一致地应用到 node group 中的所有 nodes。
* **在 AWS Management Console 中配置 node group taints**: 你也可以在 AWS Management Console 中创建 node group 时配置 taints，但这与“创建 node group 时使用 --taints 参数”是同一种方法。因此，该选项也可能是正确答案，但从技术上讲，它与创建 node group 时配置 taints 相同。
* **在 node bootstrap script 中修改 kubelet 配置**: 你可以在 bootstrap script 中使用 `--register-with-taints` flag 修改 kubelet 配置，但这种方法复杂且容易出错。对于 EKS managed node groups 也不推荐使用。

Taints 是一个有用的 Kubernetes 功能，可用于只将特定 workloads 部署到特定 nodes，或将某些 workloads 从特定 nodes 排除。对于 EKS managed node groups，在创建或更新 node group 时配置 taints 是最有效且最易管理的方法。

</details>
## 动手练习

### 练习 1：配置 IRSA (IAM Roles for Service Accounts)

**场景：** 你有一个运行在 EKS cluster 中的应用，需要访问 S3 bucket。遵循安全最佳实践，你希望使用 IRSA 只向特定 pods 授予必要权限，而不是共享 node IAM role。

**要求：**

1. 关联 OIDC provider
2. 创建具有 S3 访问权限的 IAM role
3. 创建 service account 并关联 IAM role
4. 部署使用该 service account 的 pod
5. 测试 S3 访问

**解答：**

<details>

<summary>显示解答</summary>

**1. 关联 OIDC Provider**

```bash
# Get the cluster's OIDC issuer URL
OIDC_PROVIDER=$(aws eks describe-cluster --name my-cluster --query "cluster.identity.oidc.issuer" --output text | sed -e "s/^https:\/\///")

# Check if OIDC provider already exists
aws iam list-open-id-connect-providers | grep $OIDC_PROVIDER

# Create OIDC provider if it doesn't exist
eksctl utils associate-iam-oidc-provider --cluster my-cluster --approve
```

**2. 创建具有 S3 访问权限的 IAM Role**

```bash
# Create trust policy
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):oidc-provider/${OIDC_PROVIDER}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${OIDC_PROVIDER}:sub": "system:serviceaccount:default:s3-access-sa"
        }
      }
    }
  ]
}
EOF

# Create IAM role
aws iam create-role --role-name s3-access-role --assume-role-policy-document file://trust-policy.json

# Attach S3 access policy
aws iam attach-role-policy --role-name s3-access-role --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
```

**3. 创建 Service Account 并关联 IAM Role**

```bash
# Get IAM role ARN
ROLE_ARN=$(aws iam get-role --role-name s3-access-role --query Role.Arn --output text)

# Create service account
cat > service-account.yaml << EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-access-sa
  namespace: default
  annotations:
    eks.amazonaws.com/role-arn: ${ROLE_ARN}
EOF

kubectl apply -f service-account.yaml
```

**4. 部署使用该 Service Account 的 Pod**

```bash
# Deploy test pod
cat > pod.yaml << EOF
apiVersion: v1
kind: Pod
metadata:
  name: s3-access-pod
  namespace: default
spec:
  serviceAccountName: s3-access-sa
  containers:
  - name: aws-cli
    image: amazon/aws-cli:latest
    command:
    - sleep
    - "3600"
  restartPolicy: Never
EOF

kubectl apply -f pod.yaml
```

**5. 测试 S3 访问**

```bash
# Verify the pod is running
kubectl get pod s3-access-pod

# Test listing S3 buckets
kubectl exec -it s3-access-pod -- aws s3 ls

# Test listing objects in a specific S3 bucket
kubectl exec -it s3-access-pod -- aws s3 ls s3://my-bucket

# Verify AWS credentials
kubectl exec -it s3-access-pod -- aws sts get-caller-identity
```

**6. 清理**

```bash
# Delete pod
kubectl delete pod s3-access-pod

# Delete service account
kubectl delete serviceaccount s3-access-sa

# Clean up IAM role
aws iam detach-role-policy --role-name s3-access-role --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
aws iam delete-role --role-name s3-access-role
```

**补充说明：**

1. **OIDC Provider 关联**:
   * OIDC provider 在 AWS IAM 与 Kubernetes service accounts 之间建立信任关系。
   * 每个 cluster 只需要设置一次。
2. **IAM Role Trust Policy**:
   * trust policy 限制只有特定 namespaces 中的特定 service accounts 可以 assume 该 role。
   * 使用 condition statements 增强安全性。
3. **Service Account Annotation**:
   * `eks.amazonaws.com/role-arn` annotation 指定 service account 将 assume 的 IAM role。
   * 此 annotation 由 EKS Pod Identity Webhook 处理。
4. **Environment Variables**:
   * EKS Pod Identity Webhook 会自动将以下 environment variables 注入 pod：
     * `AWS_ROLE_ARN`
     * `AWS_WEB_IDENTITY_TOKEN_FILE`
     * `AWS_REGION`
   * AWS SDKs 使用这些 environment variables 获取 credentials。
5. **最小权限原则**:
   * 只授予应用所需的最低权限。
   * 在此示例中，只授予了 S3 read-only access 权限。

通过本练习，你学习了如何配置 IRSA，将对 AWS services 的细粒度权限只授予运行在 EKS cluster 中的特定 pods。这种方法比共享 node IAM role 更安全，并遵循最小权限原则。

</details>

\### 练习 2：强化 EKS Cluster 安全

**场景：** 你是公司的安全工程师，需要强化新创建的 EKS cluster 的安全。该 cluster 已使用默认设置创建并配置。你希望根据安全最佳实践加固 cluster。

**要求：**

1. 限制 cluster endpoint access
2. 启用 Secrets encryption
3. 实现 network policies
4. 应用 Pod Security Standards
5. 启用 control plane logging

**解答：**

<details>

<summary>显示解答</summary>

**1. 限制 Cluster Endpoint Access**

```bash
# Check current cluster endpoint configuration
aws eks describe-cluster --name my-cluster --query "cluster.resourcesVpcConfig.endpointPublicAccess"
aws eks describe-cluster --name my-cluster --query "cluster.resourcesVpcConfig.endpointPrivateAccess"

# Restrict public access (allow only specific CIDR blocks)
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs=["203.0.113.0/24","198.51.100.0/24"]

# Or disable public access (private cluster)
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true
```

**2. 启用 Secrets Encryption**

```bash
# Create KMS key
aws kms create-key --description "EKS Secrets Encryption Key"
KEY_ID=$(aws kms create-key --query KeyMetadata.KeyId --output text)

# Add alias to KMS key
aws kms create-alias \
  --alias-name alias/eks-secrets \
  --target-key-id $KEY_ID

# Cannot enable encryption on current cluster, so a new cluster must be created
# Get existing cluster configuration
aws eks describe-cluster --name my-cluster > cluster-config.json

# Create new cluster (more parameters are needed in practice)
aws eks create-cluster \
  --name my-cluster-encrypted \
  --role-arn $(aws eks describe-cluster --name my-cluster --query cluster.roleArn --output text) \
  --resources-vpc-config subnetIds=$(aws eks describe-cluster --name my-cluster --query cluster.resourcesVpcConfig.subnetIds --output text | tr -d '[]" ' | tr ',' ' '),securityGroupIds=$(aws eks describe-cluster --name my-cluster --query cluster.resourcesVpcConfig.securityGroupIds --output text | tr -d '[]" ') \
  --encryption-config '[{"resources":["secrets"],"provider":{"keyArn":"arn:aws:kms:'$(aws configure get region)':'$(aws sts get-caller-identity --query Account --output text)':key/'$KEY_ID'"}}]'
```

**3. 实现 Network Policies**

```bash
# Install Calico
kubectl create namespace tigera-operator
helm repo add projectcalico https://docs.projectcalico.org/charts
helm install calico projectcalico/tigera-operator --namespace tigera-operator

# Create default deny network policy
cat > default-deny.yaml << EOF
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
EOF

kubectl apply -f default-deny.yaml

# Policy to allow communication between specific applications
cat > allow-app-communication.yaml << EOF
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
EOF

kubectl apply -f allow-app-communication.yaml
```

**4. 应用 Pod Security Standards**

```bash
# Apply Pod Security Standards to namespace
cat > pod-security.yaml << EOF
apiVersion: v1
kind: Namespace
metadata:
  name: restricted-ns
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
EOF

kubectl apply -f pod-security.yaml

# Add labels to existing namespace
kubectl label namespace default \
  pod-security.kubernetes.io/enforce=baseline \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted

# Install Kyverno (for additional policy enforcement)
kubectl create namespace kyverno
helm repo add kyverno https://kyverno.github.io/kyverno/
helm install kyverno kyverno/kyverno --namespace kyverno

# Policy to prevent privileged containers
cat > restrict-privileged.yaml << EOF
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-privileged-containers
spec:
  validationFailureAction: enforce
  rules:
  - name: privileged-containers
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Privileged containers are not allowed"
      pattern:
        spec:
          containers:
          - name: "*"
            securityContext:
              privileged: false
EOF

kubectl apply -f restrict-privileged.yaml
```

**5. 启用 Control Plane Logging**

```bash
# Enable all control plane log types
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# Verify logging status
aws eks describe-cluster --name my-cluster --query "cluster.logging"

# Check logs in CloudWatch Logs
aws logs describe-log-groups --log-group-name-prefix /aws/eks/my-cluster
```

**6. 其他安全加固措施**

```bash
# Restrict IAM policy for AWS Load Balancer Controller
cat > alb-controller-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:DescribeListeners"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name EksAlbControllerRestrictedPolicy \
  --policy-document file://alb-controller-policy.json

# Configure node group update for periodic node replacement
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --update-config '{"maxUnavailable": 1}'

# Start node group update
aws eks update-nodegroup-version \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup
```

**安全加固说明：**

1. **限制 Cluster Endpoint Access**:
   * 将 public endpoint access 限制为特定 IP ranges，或完全禁用。
   * 启用 private endpoint 以允许从 VPC 内部访问 cluster。
   * 这可以防止未经授权访问 cluster API server。
2. **启用 Secrets Encryption**:
   * 使用 AWS KMS keys 加密存储在 etcd 中的 Kubernetes Secrets。
   * 保护静态敏感数据。
   * 注意：无法在现有 clusters 上启用加密，因此需要创建新 cluster。
3. **实现 Network Policies**:
   * 安装 Calico 以支持 Kubernetes network policies。
   * 应用 default deny policies 以阻止所有未明确允许的 traffic。
   * 实现只允许必要通信的细粒度 policies。
4. **应用 Pod Security Standards**:
   * 应用 Kubernetes 1.23 及更高版本中可用的 Pod Security Standards。
   * 在 namespace 级别设置 security constraints。
   * 使用 Kyverno 等 policy engines 应用额外 security policies。
5. **启用 Control Plane Logging**:
   * 将所有 control plane log types 发送到 CloudWatch Logs。
   * 通过 audit logs 监控 cluster 活动。
   * 保留 logs 以用于 security events 和 troubleshooting。

通过本动手练习，你学习了多种强化 EKS cluster 安全的方法。这些安全措施有助于提升 cluster 的安全态势，并保护它免受未经授权访问和恶意活动影响。

</details>
## 高级主题

以下是关于 Amazon EKS cluster 创建高级主题的问题。本节测试你对 EKS cluster 创建中的高级概念和最佳实践的理解。

1. 以下哪一项不是在 Amazon EKS cluster 中配置 IPv6 支持的要求？
   * A) 分配了 IPv6 CIDR block 的 VPC
   * B) 支持 IPv6 的 CNI plugin 版本
   * C) Dual-stack subnets
   * D) IPv6-only instance types

<details>

<summary>显示答案</summary>

**答案：D) IPv6-only instance types**

**解释：** “IPv6-only instance types”不是在 Amazon EKS cluster 中配置 IPv6 支持的要求。IPv6 支持不需要特殊 instance types，因为大多数 EC2 instance types 都支持 IPv6。实际要求是分配了 IPv6 CIDR block 的 VPC、支持 IPv6 的 CNI plugin 版本，以及 dual-stack subnets。

**EKS 中 IPv6 支持的实际要求：**

1.  **分配了 IPv6 CIDR block 的 VPC**:

    * 必须向你的 VPC 分配 IPv6 CIDR block。
    * 可以通过 AWS Management Console 或 AWS CLI 配置。

    ```bash
    # Assign IPv6 CIDR block to existing VPC
    aws ec2 associate-vpc-cidr-block \
      --vpc-id vpc-12345 \
      --amazon-provided-ipv6-cidr-block
    ```
2.  **支持 IPv6 的 CNI plugin 版本**:

    * 需要 Amazon VPC CNI plugin 版本 1.10.0 或更高版本。
    * 需要进行 IPv6 支持配置。

    ```bash
    # Check CNI version
    kubectl describe daemonset aws-node --namespace kube-system | grep Image

    # Update CNI
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.10.0/config/master/aws-k8s-cni.yaml

    # Enable IPv6
    kubectl set env daemonset aws-node -n kube-system ENABLE_IPV6=true
    ```
3.  **Dual-stack subnets**:

    * Subnets 必须同时分配 IPv4 和 IPv6 CIDR blocks。
    * 必须在 route table 中配置 IPv6 routing。

    ```bash
    # Assign IPv6 CIDR block to subnet
    aws ec2 associate-subnet-cidr-block \
      --subnet-id subnet-12345 \
      --ipv6-cidr-block 2600:1f16:d93:e900::/64

    # Create IPv6 internet gateway
    aws ec2 create-egress-only-internet-gateway --vpc-id vpc-12345
    ```

**创建 EKS IPv6 Cluster：**

```bash
# Create IPv6 cluster using eksctl
cat > ipv6-cluster.yaml << EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ipv6-cluster
  region: us-west-2
  version: '1.23'
vpc:
  id: vpc-12345
  subnets:
    private:
      us-west-2a:
        id: subnet-12345
      us-west-2b:
        id: subnet-67890
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
kubernetesNetworkConfig:
  ipFamily: IPv6
managedNodeGroups:
  - name: ng-1
    instanceType: m5.large
    desiredCapacity: 2
EOF

eksctl create cluster -f ipv6-cluster.yaml
```

**验证 IPv6 Cluster 配置：**

```bash
# Check cluster information
aws eks describe-cluster --name ipv6-cluster --query "cluster.kubernetesNetworkConfig"

# Verify Pod IP assignment
kubectl get pods -o wide

# Verify Service IP assignment
kubectl get services -o wide
```

**IPv6 Clusters 的特征：**

1. **Pod IP 分配**:
   * Pods 仅分配 IPv6 addresses。
   * cluster 内部通信通过 IPv6 进行。
2. **Service IP 分配**:
   * ClusterIP services 使用 IPv6 addresses。
   * 默认 service CIDR 是 fd00::/108。
3. **DNS 配置**:
   * CoreDNS 配置为使用 IPv6 addresses。
   * 可通过 AAAA records 进行 service name resolution。
4. **外部通信**:
   * Internet 通信需要 Egress-Only Internet Gateway。
   * 入站通信需要启用 IPv6 的 load balancer。

**使用 IPv6 的优势：**

1. **解决 IP Address Exhaustion**:
   * 克服 IPv4 address space 的限制。
   * 解决大规模 clusters 中的 IP address shortage 问题。
2. **简化 Networking**:
   * 无需 NAT，简化 network 配置。
   * Direct routing 可以提升 network performance。
3. **未来兼容性**:
   * 为向 IPv6-only environments 过渡做准备。
   * 支持利用新的 networking features 和 optimizations。

“IPv6-only instance types”是一个不存在的概念，大多数 EC2 instance types 都支持 IPv6。在 EKS 中配置 IPv6 不需要选择特殊 instance types。

</details>

2\. 配置 Amazon EKS cluster 中 custom networking 的主要好处是什么？ - A) 将 Pod IP address range 与 VPC CIDR 分离以防止 IP address conflicts - B) 缩短 cluster 创建时间 - C) 提高 control plane 性能 - D) 加密 node-to-node 通信

<details>

<summary>显示答案</summary>

**答案：A) 将 Pod IP address range 与 VPC CIDR 分离以防止 IP address conflicts**

**解释：** 在 Amazon EKS cluster 中配置 custom networking 的主要好处，是将 Pod IP address range 与 VPC CIDR 分离，以防止 IP address conflicts。此功能便于与现有 network infrastructure 集成，并在大规模 clusters 中实现更高效的 IP address management。

**Custom Networking 的工作方式：**

默认情况下，Amazon VPC CNI plugin 从 node 的主 network interface 分配 secondary IP addresses，为 Pods 提供 IP addresses。在这种方法中，Pod IP addresses 从 VPC CIDR range 内分配。相比之下，custom networking 允许你从与 VPC CIDR 分离的 CIDR block 中分配 Pod IP addresses。

**配置 Custom Networking 的步骤：**

1.  **启用 Custom Networking**:

    ```bash
    # Modify CNI plugin configuration
    kubectl set env daemonset aws-node -n kube-system AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true
    ```
2.  **创建 ENIConfig Resources**:

    ```yaml
    # Create ENIConfig for each availability zone
    apiVersion: crd.k8s.amazonaws.com/v1alpha1
    kind: ENIConfig
    metadata:
      name: us-west-2a
    spec:
      subnet: subnet-12345
      securityGroups:
      - sg-12345
    ---
    apiVersion: crd.k8s.amazonaws.com/v1alpha1
    kind: ENIConfig
    metadata:
      name: us-west-2b
    spec:
      subnet: subnet-67890
      securityGroups:
      - sg-12345
    ```
3.  **启用基于 Availability Zone 的 ENIConfig 使用方式**:

    ```bash
    kubectl set env daemonset aws-node -n kube-system ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone
    ```
4.  **验证 Node Labels**:

    ```bash
    kubectl get nodes --show-labels | grep topology.kubernetes.io/zone
    ```

**Custom Networking 的优势：**

1. **防止 IP Address Conflicts**:
   * 将 Pod IP address range 与 VPC CIDR 分离，以防止 IP address conflicts。
   * 便于与现有 network infrastructure 集成。
   * 对 on-premises networks 与 VPCs 之间的 peering 或 VPN connections 很有用。
2. **IP Address Management 的灵活性**:
   * 允许单独规划和管理 Pod IP address ranges。
   * 在大规模 clusters 中实现更高效的 IP address management。
3. **Network Segmentation**:
   * 通过将 Pods 放置在特定 subnets 中实现 network segmentation。
   * 可通过 security groups 进行 network access control。
4. **Multi-CIDR Support**:
   * 可使用多个 CIDR blocks 扩展 IP address space。
   * 即使现有 VPC CIDR 有限，也可以构建大规模 clusters。

**Custom Networking 的使用场景：**

1. **Hybrid Network Environments**:
   * 当 on-premises networks 与 AWS VPC 之间存在连接时
   * 当必须防止 IP address space 重叠时
2. **大规模 Clusters**:
   * 当运行大量 Pods 时
   * 当 VPC CIDR range 有限时
3. **多租户环境**:
   * 当每个 tenant 都需要单独 subnets 时
   * 当需要 network isolation 时
4. **监管要求**:
   * 当法规要求将特定 workloads 放置在特定 subnets 中时

**其他选项的问题：**

* **缩短 cluster 创建时间**: Custom networking 不会影响 cluster 创建时间，并且由于额外配置，实际上可能增加设置时间。
* **提高 control plane 性能**: Custom networking 只影响 data plane（worker nodes 和 Pods）networking，不会直接影响 control plane 性能。
* **加密 node-to-node 通信**: Custom networking 只改变 IP addresses 的分配方式，与 node-to-node 通信加密无关。Node-to-node 通信加密必须通过单独的安全机制实现（例如 Calico、Cilium encryption features）。

Custom networking 是一项强大功能，可以更灵活地配置 EKS cluster networking，但其配置复杂，并可能带来额外的管理开销，因此只有在确实需要时才应使用。

</details>

3\. 以下哪一项不是在 Amazon EKS cluster 中支持 Windows worker nodes 的要求？ - A) 需要至少 2 个基于 Amazon Linux 的 managed node groups - B) 安装 VPC-CNI、kube-proxy、CoreDNS add-ons - C) Windows Server 2019 或更高版本 AMI - D) Cluster 版本 1.14 或更高

<details>

<summary>显示答案</summary>

**答案：A) 需要至少 2 个基于 Amazon Linux 的 managed node groups**

**解释：** 要在 Amazon EKS cluster 中支持 Windows worker nodes，需要至少 1 个（不是 2 个或更多）基于 Amazon Linux 的 managed node group。这是因为 CoreDNS 等关键 system Pods 必须运行在 Linux nodes 上。但是，要求至少 2 个 Linux node groups 是不正确的。

**EKS 中 Windows Worker Node 支持的实际要求：**

1.  **需要 Linux Node Group**:

    * cluster 中至少需要 1 个 Linux node。
    * CoreDNS、VPC CNI plugin 和 kube-proxy 等 System Pods 只在 Linux nodes 上运行。

    ```bash
    # Create Linux node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name linux-ng \
      --node-type m5.large \
      --nodes 2
    ```
2.  **安装 VPC-CNI、kube-proxy、CoreDNS Add-ons**:

    * 这些 add-ons 是 EKS cluster 的关键组件。
    * Windows node 支持可能需要特定版本或更高版本。

    ```bash
    # Check add-on versions
    aws eks describe-addon-versions \
      --addon-name vpc-cni \
      --kubernetes-version 1.23

    # Update add-on
    aws eks update-addon \
      --cluster-name my-cluster \
      --addon-name vpc-cni \
      --addon-version v1.10.4-eksbuild.1
    ```
3.  **Windows Server 2019 或更高版本 AMI**:

    * Windows worker nodes 必须使用 Windows Server 2019 或更高版本 AMI。
    * 建议使用 EKS-optimized Windows AMI。

    ```bash
    # Create Windows node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name windows-ng \
      --node-type m5.large \
      --nodes 2 \
      --node-ami-family WindowsServer2019FullContainer
    ```
4.  **Cluster 版本 1.14 或更高**:

    * Windows node 支持从 Kubernetes 1.14 开始正式支持。
    * 建议使用更高版本以获得最新功能。

    ```bash
    # Check cluster version
    aws eks describe-cluster --name my-cluster --query "cluster.version"
    ```

**启用 Windows 支持的步骤：**

1.  **启用 Windows 支持**:

    ```bash
    # Enable Windows support
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/vpc-resource-controller.yaml

    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/vpc-admission-webhook.yaml
    ```
2.  **创建 Windows Node Group**:

    ```bash
    # Create Windows node group using eksctl
    eksctl create nodegroup \
      --cluster my-cluster \
      --name windows-ng \
      --node-type m5.large \
      --nodes 2 \
      --node-ami-family WindowsServer2019FullContainer
    ```
3.  **验证 Windows Nodes**:

    ```bash
    # Verify nodes
    kubectl get nodes -o wide

    # Verify Windows node labels
    kubectl get nodes -l kubernetes.io/os=windows
    ```

**Windows Container Deployment 示例：**

```yaml
# Windows Pod deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: windows-server-iis
spec:
  selector:
    matchLabels:
      app: windows-server-iis
      tier: backend
      track: stable
  replicas: 2
  template:
    metadata:
      labels:
        app: windows-server-iis
        tier: backend
        track: stable
    spec:
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: windows-server-iis
        image: mcr.microsoft.com/windows/servercore:ltsc2019
        ports:
        - containerPort: 80
        command:
        - powershell.exe
        - -command
        - "Add-WindowsFeature Web-Server; Invoke-WebRequest -UseBasicParsing -Uri 'https://dotnetbinaries.blob.core.windows.net/servicemonitor/2.0.1.6/ServiceMonitor.exe' -OutFile 'C:\\ServiceMonitor.exe'; echo '<html><body><br/><br/><center><h1>Hello from Windows Container</h1></center></body></html>' > C:\\inetpub\\wwwroot\\default.html; C:\\ServiceMonitor.exe 'w3svc';"
```

**Windows Node 限制：**

1. **Networking 限制**:
   * Windows nodes 不支持 HostPort 和 HostNetwork 模式。
   * Windows nodes 不支持 NodeLocal DNSCache。
2. **Storage 限制**:
   * Windows nodes 仅支持某些 storage drivers。
   * host path volume mounts 存在限制。
3. **Container Runtime**:
   * Windows nodes 仅支持 containerd runtime。
   * Linux containers 不能在 Windows nodes 上运行。
4. **功能限制**:
   * 某些 Kubernetes features 在 Windows nodes 上不受支持。
   * privileged containers、process namespace sharing 等存在限制。

要在 EKS 中支持 Windows worker nodes，至少需要一个 Linux node group，但不强制要求两个或更多 Linux node groups。因此，“需要至少 2 个基于 Amazon Linux 的 managed node groups”不是准确的要求。

</details>

3\. 以下哪一项不是在 Amazon EKS cluster 中支持 Windows worker nodes 的要求？ - A) 需要至少 2 个基于 Amazon Linux 的 managed node groups - B) 安装 VPC-CNI、kube-proxy、CoreDNS add-ons - C) 使用 Windows Server 2019 或更高版本 AMI - D) Cluster 版本 1.14 或更高

<details>

<summary>显示答案</summary>

**答案：A) 需要至少 2 个基于 Amazon Linux 的 managed node groups**

**解释：** 要在 Amazon EKS cluster 中支持 Windows worker nodes，需要至少一个（不是两个或更多）基于 Amazon Linux 的 managed node group。这是因为 CoreDNS 等关键 system pods 必须运行在 Linux nodes 上。但是，要求至少两个 Linux node groups 并不准确。

**EKS 中 Windows Worker Node 支持的实际要求：**

1.  **需要 Linux Node Group**:

    * cluster 至少需要一个 Linux node。
    * CoreDNS、VPC CNI plugin 和 kube-proxy 等 system pods 只在 Linux nodes 上运行。

    ```bash
    # Create Linux node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name linux-ng \
      --node-type m5.large \
      --nodes 2
    ```
2.  **安装 VPC-CNI、kube-proxy、CoreDNS Add-ons**:

    * 这些 add-ons 是 EKS cluster 的基础组件。
    * Windows node 支持可能需要特定版本或更高版本。

    ```bash
    # Check add-on versions
    aws eks describe-addon-versions \
      --addon-name vpc-cni \
      --kubernetes-version 1.23

    # Update add-on
    aws eks update-addon \
      --cluster-name my-cluster \
      --addon-name vpc-cni \
      --addon-version v1.10.4-eksbuild.1
    ```
3.  **使用 Windows Server 2019 或更高版本 AMI**:

    * Windows worker nodes 必须使用 Windows Server 2019 或更高版本 AMI。
    * 建议使用 EKS-optimized Windows AMI。

    ```bash
    # Create Windows node group
    eksctl create nodegroup \
      --cluster my-cluster \
      --name windows-ng \
      --node-type m5.large \
      --nodes 2 \
      --node-ami-family WindowsServer2019FullContainer
    ```
4.  **Cluster 版本 1.14 或更高**:

    * Windows node 支持从 Kubernetes 1.14 开始 generally available。
    * 建议使用更高版本以获得最新功能。

    ```bash
    # Check cluster version
    aws eks describe-cluster --name my-cluster --query "cluster.version"
    ```

**启用 Windows 支持的步骤：**

1.  **启用 Windows 支持**:

    ```bash
    # Enable Windows support
    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/vpc-resource-controller.yaml

    kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/master/vpc-admission-webhook.yaml
    ```
2.  **创建 Windows Node Group**:

    ```bash
    # Create Windows node group using eksctl
    eksctl create nodegroup \
      --cluster my-cluster \
      --name windows-ng \
      --node-type m5.large \
      --nodes 2 \
      --node-ami-family WindowsServer2019FullContainer
    ```
3.  **验证 Windows Nodes**:

    ```bash
    # Verify nodes
    kubectl get nodes -o wide

    # Verify Windows node labels
    kubectl get nodes -l kubernetes.io/os=windows
    ```

**Windows Container Deployment 示例：**

```yaml
# Windows Pod deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: windows-server-iis
spec:
  selector:
    matchLabels:
      app: windows-server-iis
      tier: backend
      track: stable
  replicas: 2
  template:
    metadata:
      labels:
        app: windows-server-iis
        tier: backend
        track: stable
    spec:
      nodeSelector:
        kubernetes.io/os: windows
      containers:
      - name: windows-server-iis
        image: mcr.microsoft.com/windows/servercore:ltsc2019
        ports:
        - containerPort: 80
        command:
        - powershell.exe
        - -command
        - "Add-WindowsFeature Web-Server; Invoke-WebRequest -UseBasicParsing -Uri 'https://dotnetbinaries.blob.core.windows.net/servicemonitor/2.0.1.6/ServiceMonitor.exe' -OutFile 'C:\\ServiceMonitor.exe'; echo '<html><body><br/><br/><center><h1>Hello from Windows Container</h1></center></body></html>' > C:\\inetpub\\wwwroot\\default.html; C:\\ServiceMonitor.exe 'w3svc';"
```

**Windows Node 限制：**

1. **Networking 限制**:
   * Windows nodes 不支持 HostPort 和 HostNetwork 模式。
   * Windows nodes 不支持 NodeLocal DNSCache。
2. **Storage 限制**:
   * Windows nodes 仅支持某些 storage drivers。
   * host path volume mounts 存在限制。
3. **Container Runtime**:
   * Windows nodes 仅支持 containerd runtime。
   * Linux containers 不能在 Windows nodes 上运行。
4. **功能限制**:
   * 某些 Kubernetes features 在 Windows nodes 上不受支持。
   * privileged containers、process namespace sharing 等存在限制。

要在 EKS 中支持 Windows worker nodes，至少需要一个 Linux node group，但不强制要求两个或更多 Linux node groups。因此，“需要至少 2 个基于 Amazon Linux 的 managed node groups”不是准确的要求。

</details>

4. 保护 Amazon EKS cluster 中 node groups 的 Instance Metadata Service (IMDS) 的最有效方式是什么？
   * A) 禁用 IMDSv1 并要求使用 IMDSv2
   * B) 使用 security group rules 限制对 169.254.169.254 的访问
   * C) 对 node IAM role 设置限制性权限
   * D) 将 IAM roles 附加到 pod service accounts

<details>

<summary>显示答案</summary>

**答案：A) 禁用 IMDSv1 并要求使用 IMDSv2**

**解释：** 保护 Amazon EKS cluster 中 node groups 的 Instance Metadata Service (IMDS) 的最有效方式，是禁用 IMDSv1 并要求使用 IMDSv2。IMDSv2 使用基于 session 的 requests 提供增强安全功能，可防御 Server-Side Request Forgery (SSRF) 和类似漏洞。

**IMDS 安全的重要性：**

Instance Metadata Service 提供有关 EC2 instances 的重要信息，包括 IAM role credentials。未经授权访问此 service 可能导致 privilege escalation 和 security breaches。在 Kubernetes environments 中，由于 pods 可以访问 node 的 IMDS，安全风险会增加。

**如何配置 IMDSv2：**

1.  **使用 Launch Template 配置 IMDSv2**:

    ```bash
    # Create launch template
    aws ec2 create-launch-template \
      --launch-template-name eks-imdsv2-template \
      --version-description "IMDSv2 required" \
      --launch-template-data '{
        "MetadataOptions": {
          "HttpTokens": "required",
          "HttpPutResponseHopLimit": 1,
          "HttpEndpoint": "enabled"
        }
      }'

    # Create node group using launch template
    eksctl create nodegroup \
      --cluster my-cluster \
      --name ng-imdsv2 \
      --node-type m5.large \
      --nodes 3 \
      --launch-template-name eks-imdsv2-template \
      --launch-template-version 1
    ```
2.  **使用 eksctl 配置文件配置 IMDSv2**:

    ```yaml
    apiVersion: eksctl.io/v1alpha5
    kind: ClusterConfig
    metadata:
      name: my-cluster
      region: us-west-2
    managedNodeGroups:
      - name: ng-imdsv2
        instanceType: m5.large
        minSize: 2
        maxSize: 5
        disableIMDSv1: true
        metadataOptions:
          httpTokens: required
          httpPutResponseHopLimit: 1
    ```
3.  **修改现有 Node Groups**: 要更改现有 node groups 的 IMDS 设置，需要创建新的 node group 并迁移 workloads。现有 EC2 instances 的 IMDS 设置可以按如下方式修改：

    ```bash
    aws ec2 modify-instance-metadata-options \
      --instance-id i-1234567890abcdef0 \
      --http-tokens required \
      --http-put-response-hop-limit 1 \
      --http-endpoint enabled
    ```

**IMDSv2 的安全优势：**

1. **基于 Session 的身份验证**:
   * IMDSv2 使用通过 PUT requests 生成的 tokens 来验证后续 requests。
   * 这些 tokens 仅在有限时间内有效。
2. **SSRF 攻击防护**:
   * 防止通过 Server-Side Request Forgery (SSRF) 漏洞访问 metadata。
   * 没有 token 就无法访问 metadata。
3. **Hop Limit 设置**:
   * 设置 HTTP PUT response hop limit 可防止 metadata requests 被重定向到 instance 外部。
   * 默认值为 1，确保 requests 只在 instance 内部处理。

**其他 IMDS 安全措施：**

1.  **完全禁用 IMDS**: 如果某些 workloads 不需要 IMDS，可以完全禁用它：

    ```yaml
    metadataOptions:
      httpEndpoint: disabled
    ```
2.  **阻止 Pod 访问 IMDS**: 如果 pods 未使用 host networking，可以添加 iptables rules 阻止 IMDS 访问：

    ```bash
    iptables -t nat -A PREROUTING -d 169.254.169.254/32 -i eth0 -p tcp -m tcp --dport 80 -j DNAT --to-destination 127.0.0.1:1
    ```
3. **使用 IRSA**: 使用 IAM Roles for Service Accounts (IRSA) 为 pods 提供所需 AWS 权限，并消除对 node IMDS 的依赖。

**其他选项的问题：**

* **使用 security group rules 限制对 169.254.169.254 的访问**: Security groups 控制来自 instance 外部的 traffic，但 IMDS 从 instance 内部访问，因此无法使用 security groups 限制。
* **对 node IAM role 设置限制性权限**: 这是良好的安全实践，但不会强化 IMDS 本身的安全。如果攻击者可以访问 IMDS，即使权限有限也可能被利用。
* **将 IAM roles 附加到 pod service accounts**: IRSA 是确保 pods 不依赖 node IMDS 的好方法，但它不会直接强化 node IMDS 本身的安全。

禁用 IMDSv1 并要求使用 IMDSv2 是保护 EKS nodes metadata service 的最有效方式。这是 AWS 安全最佳实践，在多租户 Kubernetes environments 中尤其重要。

</details>

5. 以下哪一项不是在 Amazon EKS cluster 中创建 node groups 时自定义 bootstrap scripts 的主要目的？
   * A) 修改 cluster control plane components
   * B) 安装额外软件
   * C) 调整 kernel parameters
   * D) 设置 node labels 和 taints

<details>

<summary>显示答案</summary>

**答案：A) 修改 cluster control plane components**

**解释：** 在 Amazon EKS cluster 中创建 node groups 时，自定义 bootstrap scripts 的主要目的不是修改 cluster control plane components。EKS 是 managed service，control plane 由 AWS 管理，用户无法直接修改。Bootstrap scripts 只能修改 worker node configurations。

**Bootstrap Scripts 的实际使用场景：**

1.  **安装额外软件**:

    * Monitoring agents (CloudWatch Agent, Prometheus Node Exporter 等)
    * Logging tools (Fluentd, Fluent Bit 等)
    * Security tools (Falco, Sysdig 等)
    * Performance optimization tools

    ```bash
    #!/bin/bash
    # Install CloudWatch agent
    wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
    rpm -U amazon-cloudwatch-agent.rpm

    # Create configuration file
    cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
    {
      "metrics": {
        "metrics_collected": {
          "mem": {
            "measurement": ["mem_used_percent"]
          },
          "swap": {
            "measurement": ["swap_used_percent"]
          }
        }
      }
    }
    EOF

    # Start agent
    /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s
    ```
2.  **调整 Kernel Parameters**:

    * Network setting optimization
    * Memory management settings
    * File system 和 I/O settings

    ```bash
    #!/bin/bash
    # Adjust kernel parameters
    cat > /etc/sysctl.d/99-kubernetes.conf << EOF
    net.ipv4.ip_forward = 1
    net.bridge.bridge-nf-call-iptables = 1
    net.ipv4.tcp_keepalive_time = 600
    net.ipv4.tcp_max_syn_backlog = 40000
    net.core.somaxconn = 40000
    net.core.netdev_max_backlog = 40000
    vm.max_map_count = 262144
    EOF

    # Apply changes
    sysctl --system
    ```
3.  **设置 Node Labels 和 Taints**:

    * 设置 node role labels
    * 设置 hardware characteristic labels
    * 为特定 workloads 设置 taints

    ```bash
    #!/bin/bash
    # Execute EKS bootstrap script
    /etc/eks/bootstrap.sh my-cluster \
      --kubelet-extra-args '--node-labels=node.kubernetes.io/role=worker,environment=prod,node-type=compute --register-with-taints=dedicated=compute:NoSchedule'
    ```
4.  **Disk 和 File System 配置**:

    * 挂载额外 volumes
    * File system optimization
    * Temporary storage configuration

    ```bash
    #!/bin/bash
    # Format and mount additional EBS volume
    mkfs -t xfs /dev/nvme1n1
    mkdir -p /data
    mount /dev/nvme1n1 /data
    echo "/dev/nvme1n1 /data xfs defaults 0 0" >> /etc/fstab
    ```
5.  **安全配置**:

    * 设置 firewall rules
    * Security hardening settings
    * Log audit configuration

    ```bash
    #!/bin/bash
    # Set firewall rules
    iptables -A INPUT -p tcp --dport 22 -s 10.0.0.0/8 -j ACCEPT
    iptables -A INPUT -p tcp --dport 22 -j DROP

    # Security hardening settings
    sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
    systemctl restart sshd
    ```

**如何实现 Bootstrap Scripts：**

1.  **使用 Launch Template 的 User Data Script**:

    ```bash
    # Create launch template
    aws ec2 create-launch-template \
      --launch-template-name eks-custom-bootstrap \
      --version-description "Custom bootstrap script" \
      --launch-template-data '{
        "UserData": "BASE64_ENCODED_USER_DATA_SCRIPT"
      }'

    # Create node group using launch template
    eksctl create nodegroup \
      --cluster my-cluster \
      --name custom-ng \
      --node-type m5.large \
      --nodes 3 \
      --launch-template-name eks-custom-bootstrap \
      --launch-template-version 1
    ```
2.  **使用 eksctl 配置文件的 User Data Script**:

    ```yaml
    apiVersion: eksctl.io/v1alpha5
    kind: ClusterConfig
    metadata:
      name: my-cluster
      region: us-west-2
    managedNodeGroups:
      - name: custom-ng
        instanceType: m5.large
        minSize: 2
        maxSize: 5
        preBootstrapCommands:
          - "echo 'net.ipv4.ip_forward = 1' >> /etc/sysctl.d/99-kubernetes.conf"
          - "sysctl --system"
        kubeletExtraArgs:
          node-labels: "environment=prod,node-type=compute"
    ```

**Cluster Control Plane Components：**

EKS cluster 的 control plane components 由 AWS 管理，不能通过 bootstrap scripts 修改：

* API Server
* Controller Manager
* Scheduler
* etcd
* CoreDNS

要修改这些 components，必须通过 AWS 提供的 APIs 在 cluster 级别进行配置。例如，control plane logging 可以按如下方式配置：

```bash
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

Bootstrap script 只能修改 worker node configurations，不能修改 cluster control plane components。因此，“修改 cluster control plane components”不是 bootstrap script 的主要目的。

</details>
