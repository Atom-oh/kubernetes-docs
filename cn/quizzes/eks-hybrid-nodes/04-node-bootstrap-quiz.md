# EKS Hybrid Nodes Node Bootstrapping 测验

> **相关文档**: [Node Bootstrapping](../../eks-hybrid-nodes/04-node-bootstrap.md)

## 选择题

### 1. nodeadm 的主要作用是什么？

A. 创建 EKS clusters
B. 安装并引导 kubelet 和 containerd 等 Node components
C. 做出 Pod 调度决策
D. 管理 cluster network policies

<details>
<summary>显示答案</summary>

**答案：B. 安装并引导 kubelet 和 containerd 等 Node components**

**解释：**
nodeadm 是用于 EKS Node Bootstrapping 的官方工具。它会安装并配置必要组件，包括 kubelet、containerd 和 aws-iam-authenticator。

```bash
# Install nodeadm
curl -L -o nodeadm https://github.com/awslabs/amazon-eks-ami/releases/download/nodeadm-v0.1.0/nodeadm-linux-amd64
chmod +x nodeadm
sudo mv nodeadm /usr/local/bin/

# Initialize node with nodeadm
sudo nodeadm init --config-source file://nodeadm-config.yaml
```

**nodeadm 功能：**
- Kubernetes component 安装（kubelet、containerd）
- AWS IAM Authenticator 配置
- kubelet certificate bootstrapping
- Node label 和 taint 设置

</details>

### 2. 使用 nodeadm 初始化 Hybrid Node 时，需要哪 3 项 cluster 信息？

A. Cluster name、VPC ID、Subnet ID
B. Cluster name、API server endpoint、CA certificate
C. Cluster name、IAM role、Security group
D. Cluster name、Region、Availability zone

<details>
<summary>显示答案</summary>

**答案：B. Cluster name、API server endpoint、CA certificate**

**解释：**
nodeadm 配置文件中的必需项：

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster                    # Required 1
    region: us-west-2
    apiServerEndpoint: https://xxxxx.eks.amazonaws.com  # Required 2
    certificateAuthority: LS0tLS1CRUdJTi...             # Required 3
```

```bash
# Get required information from EKS
aws eks describe-cluster --name my-cluster \
  --query "cluster.{name:name,endpoint:endpoint,ca:certificateAuthority.data}" \
  --output json
```

</details>

### 3. EKS Hybrid Nodes 中的 IAM 使用哪种身份验证方法？

A. Static tokens
B. 仅 x509 certificates
C. IAM Roles Anywhere 或 IAM user credentials
D. LDAP authentication

<details>
<summary>显示答案</summary>

**答案：C. IAM Roles Anywhere 或 IAM user credentials**

**解释：**
EKS Hybrid Nodes 需要来自 on-premises 的 AWS IAM 身份验证。IAM Roles Anywhere 允许从 on-premises servers 使用 IAM roles。

```bash
# Create IAM Roles Anywhere Trust Anchor
aws rolesanywhere create-trust-anchor \
  --name hybrid-nodes-anchor \
  --source "sourceType=CERTIFICATE_BUNDLE,sourceData={x509CertificateData=$CERT_DATA}"

# Create IAM Roles Anywhere Profile
aws rolesanywhere create-profile \
  --name hybrid-node-profile \
  --role-arns arn:aws:iam::123456789012:role/HybridNodeRole \
  --duration-seconds 3600
```

```yaml
# Using IAM Roles Anywhere in nodeadm Configuration
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  iam:
    mode: rolesAnywhere
    rolesAnywhere:
      trustAnchorArn: arn:aws:rolesanywhere:us-west-2:123456789012:trust-anchor/xxxxx
      profileArn: arn:aws:rolesanywhere:us-west-2:123456789012:profile/xxxxx
      roleArn: arn:aws:iam::123456789012:role/HybridNodeRole
```

</details>

### 4. 以下哪一项不是 NodeConfig 中有效的 kubelet 配置选项？

A. maxPods
B. clusterDNS
C. clusterCIDR
D. podScheduler

<details>
<summary>显示答案</summary>

**答案：D. podScheduler**

**解释：**
`podScheduler` 不是 NodeConfig 中的 kubelet 配置选项。调度由 control plane 中的 kube-scheduler 处理。

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  kubelet:
    config:
      maxPods: 110              # Maximum Pods per node
      clusterDNS:               # Cluster DNS servers
        - 10.100.0.10
      clusterDomain: cluster.local
      evictionHard:             # Pod eviction thresholds
        memory.available: "100Mi"
        nodefs.available: "10%"
    flags:
      - "--node-labels=location=onprem"
      - "--register-with-taints=dedicated=hybrid:NoSchedule"
```

</details>

### 5. 使用 SSM (Systems Manager) 注册 Hybrid Node 时需要哪些组件？

A. SSM Agent 和 activation code
B. 仅 CloudWatch Agent
C. 仅 AWS CLI
D. EC2 instance profile

<details>
<summary>显示答案</summary>

**答案：A. SSM Agent 和 activation code**

**解释：**
要使用 SSM 管理 on-premises servers，必须安装 SSM Agent 并通过 hybrid activation 注册。

```bash
# 1. Create SSM hybrid activation (AWS Console or CLI)
aws ssm create-activation \
  --default-instance-name "hybrid-node" \
  --iam-role service-role/AmazonEC2RunCommandRoleForManagedInstances \
  --registration-limit 10

# Output: ActivationId, ActivationCode

# 2. Install and register SSM Agent on on-premises server
sudo amazon-ssm-agent -register \
  -code "activation-code" \
  -id "activation-id" \
  -region "us-west-2"

# 3. Start SSM Agent
sudo systemctl start amazon-ssm-agent
sudo systemctl enable amazon-ssm-agent
```

```yaml
# Use SSM mode in nodeadm
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  hybrid:
    ssm: true
    ssmActivationId: "activation-id"
    ssmActivationCode: "activation-code"
```

</details>

### 6. 在 nodeadm 配置中提供 CA certificate 的目的是什么？

A. 加密 nodes 之间的流量
B. kubelet 验证 API server 的可信性
C. 配置 Pods 之间的 mTLS
D. Harbor registry authentication

<details>
<summary>显示答案</summary>

**答案：B. kubelet 验证 API server 的可信性**

**解释：**
kubelet 在连接时使用 CA (Certificate Authority) certificate 来验证 EKS API server 的可信性。

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    apiServerEndpoint: https://xxxxx.eks.amazonaws.com
    certificateAuthority: |
      LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUM...
      # Base64 encoded CA certificate
```

**证书流程：**
```
kubelet ----TLS connection----> EKS API Server
   |                              |
   |-- Verify server cert with CA |
   |                              |
   |<-- Issue client certificate --|
```

```bash
# Get CA certificate from EKS cluster
aws eks describe-cluster --name my-cluster \
  --query "cluster.certificateAuthority.data" \
  --output text | base64 -d > ca.crt

# View CA certificate contents
openssl x509 -in ca.crt -text -noout
```

</details>

### 7. 运行 nodeadm init 后，如果 Node 无法加入 cluster，应首先检查什么？

A. Pod deployment status
B. kubelet logs 和 network connectivity
C. Deployment configuration
D. ConfigMap contents

<details>
<summary>显示答案</summary>

**答案：B. kubelet logs 和 network connectivity**

**解释：**
当 Node 加入失败时，首先检查 kubelet logs 和 network connectivity。

```bash
# 1. Check kubelet service status
sudo systemctl status kubelet

# 2. Check kubelet logs
sudo journalctl -u kubelet -f

# 3. Check for common error patterns
sudo journalctl -u kubelet | grep -E "error|failed|unable"

# 4. Check resource status (memory, disk)
free -h
df -h

# 5. Test network connectivity
curl -vk https://<eks-api-endpoint>:443

# 6. Check DNS resolution
nslookup <eks-api-endpoint>

# 7. Check firewall rules
sudo iptables -L -n | grep 443

# 8. Check nodeadm status
sudo nodeadm status
```

**常见失败原因：**
- API server endpoint 无法访问（firewall）
- CA certificate 不匹配
- IAM authentication 失败
- DNS resolution 失败
- Time synchronization 问题（NTP）

</details>
