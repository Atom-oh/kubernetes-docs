# EKS Hybrid Nodes Node Bootstrapping Quiz

> **Related Document**: [Node Bootstrapping](../../eks-hybrid-nodes/04-node-bootstrap.md)

## Multiple Choice Questions

### 1. What is the primary role of nodeadm?

A. Creating EKS clusters
B. Installing and bootstrapping node components like kubelet and containerd
C. Making Pod scheduling decisions
D. Managing cluster network policies

<details>
<summary>Show Answer</summary>

**Answer: B. Installing and bootstrapping node components like kubelet and containerd**

**Explanation:**
nodeadm is the official tool for EKS node bootstrapping. It installs and configures necessary components including kubelet, containerd, and aws-iam-authenticator.

```bash
# Install nodeadm
curl -L -o nodeadm https://github.com/awslabs/amazon-eks-ami/releases/download/nodeadm-v0.1.0/nodeadm-linux-amd64
chmod +x nodeadm
sudo mv nodeadm /usr/local/bin/

# Initialize node with nodeadm
sudo nodeadm init --config-source file://nodeadm-config.yaml
```

**nodeadm Features:**
- Kubernetes component installation (kubelet, containerd)
- AWS IAM Authenticator configuration
- kubelet certificate bootstrapping
- Node label and taint settings

</details>

### 2. What are the 3 required cluster information pieces when initializing a Hybrid Node with nodeadm?

A. Cluster name, VPC ID, Subnet ID
B. Cluster name, API server endpoint, CA certificate
C. Cluster name, IAM role, Security group
D. Cluster name, Region, Availability zone

<details>
<summary>Show Answer</summary>

**Answer: B. Cluster name, API server endpoint, CA certificate**

**Explanation:**
Required items in nodeadm configuration file:

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

A. Static tokens
B. x509 certificates only
C. IAM Roles Anywhere or IAM user credentials
D. LDAP authentication

<details>
<summary>Show Answer</summary>

**Answer: C. IAM Roles Anywhere or IAM user credentials**

**Explanation:**
EKS Hybrid Nodes require AWS IAM authentication from on-premises. IAM Roles Anywhere allows using IAM roles from on-premises servers.

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
<summary>Show Answer</summary>

**Answer: D. podScheduler**

**Explanation:**
`podScheduler` is not a kubelet configuration option in NodeConfig. Scheduling is handled by kube-scheduler in the control plane.

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

A. SSM Agent and activation code
B. CloudWatch Agent only
C. AWS CLI only
D. EC2 instance profile

<details>
<summary>Show Answer</summary>

**Answer: A. SSM Agent and activation code**

**Explanation:**
To manage on-premises servers with SSM, you must install the SSM Agent and register through hybrid activation.

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

A. Encrypting traffic between nodes
B. kubelet verifying the API server's trustworthiness
C. Configuring mTLS between Pods
D. Harbor registry authentication

<details>
<summary>Show Answer</summary>

**Answer: B. kubelet verifying the API server's trustworthiness**

**Explanation:**
The CA (Certificate Authority) certificate is used by kubelet to verify the trustworthiness of the EKS API server when connecting.

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
B. kubelet logs and network connectivity
C. Deployment configuration
D. ConfigMap contents

<details>
<summary>Show Answer</summary>

**Answer: B. kubelet logs and network connectivity**

**Explanation:**
When node join fails, first check kubelet logs and network connectivity.

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

**Common failure causes:**
- API server endpoint inaccessible (firewall)
- CA certificate mismatch
- IAM authentication failure
- DNS resolution failure
- Time synchronization issues (NTP)

</details>

