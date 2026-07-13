# EKS Hybrid Nodes Node Bootstrapping Quiz

> **関連ドキュメント**: [Node Bootstrapping](../../eks-hybrid-nodes/04-node-bootstrap.md)

## Multiple Choice Questions

### 1. What is the primary role of nodeadm?

A. EKS cluster を作成する
B. kubelet や containerd などの node component をインストールし、bootstrap する
C. Pod の scheduling decision を行う
D. cluster network policy を管理する

<details>
<summary>解答を表示</summary>

**解答: B. kubelet や containerd などの node component をインストールし、bootstrap する**

**説明:**
nodeadm は EKS node bootstrapping の公式ツールです。kubelet、containerd、aws-iam-authenticator など、必要な component をインストールして設定します。

```bash
# Install nodeadm
curl -L -o nodeadm https://github.com/awslabs/amazon-eks-ami/releases/download/nodeadm-v0.1.0/nodeadm-linux-amd64
chmod +x nodeadm
sudo mv nodeadm /usr/local/bin/

# Initialize node with nodeadm
sudo nodeadm init --config-source file://nodeadm-config.yaml
```

**nodeadm の機能:**
- Kubernetes component のインストール (kubelet, containerd)
- AWS IAM Authenticator の設定
- kubelet certificate bootstrapping
- Node label と taint の設定

</details>

### 2. What are the 3 required cluster information pieces when initializing a Hybrid Node with nodeadm?

A. Cluster name、VPC ID、Subnet ID
B. Cluster name、API server endpoint、CA certificate
C. Cluster name、IAM role、Security group
D. Cluster name、Region、Availability zone

<details>
<summary>解答を表示</summary>

**解答: B. Cluster name、API server endpoint、CA certificate**

**説明:**
nodeadm configuration file で必要な項目:

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

### 3. What authentication method is used for IAM in EKS Hybrid Nodes?

A. Static token
B. x509 certificate のみ
C. IAM Roles Anywhere または IAM user credentials
D. LDAP authentication

<details>
<summary>解答を表示</summary>

**解答: C. IAM Roles Anywhere または IAM user credentials**

**説明:**
EKS Hybrid Nodes では、on-premises からの AWS IAM authentication が必要です。IAM Roles Anywhere により、on-premises server から IAM role を使用できます。

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

### 4. Which is NOT a valid kubelet configuration option in NodeConfig?

A. maxPods
B. clusterDNS
C. clusterCIDR
D. podScheduler

<details>
<summary>解答を表示</summary>

**解答: D. podScheduler**

**説明:**
`podScheduler` は NodeConfig の kubelet configuration option ではありません。Scheduling は control plane の kube-scheduler によって処理されます。

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

### 5. What components are required when registering a Hybrid Node using SSM (Systems Manager)?

A. SSM Agent と activation code
B. CloudWatch Agent のみ
C. AWS CLI のみ
D. EC2 instance profile

<details>
<summary>解答を表示</summary>

**解答: A. SSM Agent と activation code**

**説明:**
SSM で on-premises server を管理するには、SSM Agent をインストールし、hybrid activation を通じて登録する必要があります。

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

### 6. What is the purpose of providing the CA certificate in nodeadm configuration?

A. node 間の traffic を暗号化する
B. kubelet が API server の信頼性を検証する
C. Pod 間の mTLS を設定する
D. Harbor registry authentication

<details>
<summary>解答を表示</summary>

**解答: B. kubelet が API server の信頼性を検証する**

**説明:**
CA (Certificate Authority) certificate は、接続時に kubelet が EKS API server の信頼性を検証するために使用されます。

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

**Certificate flow:**
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

### 7. When a node fails to join the cluster after running nodeadm init, what should be checked first?

A. Pod deployment status
B. kubelet log と network connectivity
C. Deployment configuration
D. ConfigMap contents

<details>
<summary>解答を表示</summary>

**解答: B. kubelet log と network connectivity**

**説明:**
node の参加に失敗した場合は、まず kubelet log と network connectivity を確認します。

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

**一般的な失敗原因:**
- API server endpoint にアクセスできない (firewall)
- CA certificate の不一致
- IAM authentication failure
- DNS resolution failure
- Time synchronization issues (NTP)

</details>
