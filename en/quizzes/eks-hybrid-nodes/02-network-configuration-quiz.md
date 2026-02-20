# EKS Hybrid Nodes Network Configuration Quiz

> **Related Document**: [Network Configuration](../../eks-hybrid-nodes/02-network-configuration.md)

## Multiple Choice Questions

### 1. What is the recommended method for network connectivity between on-premises and cloud for EKS Hybrid Nodes?

A. Public internet connection
B. AWS Direct Connect or Site-to-Site VPN
C. SSH tunneling
D. HTTP proxy

<details>
<summary>Show Answer</summary>

**Answer: B. AWS Direct Connect or Site-to-Site VPN**

**Explanation:**
EKS Hybrid Nodes require stable and secure network connectivity to the EKS control plane. AWS Direct Connect (dedicated line) or Site-to-Site VPN is recommended.

**Network Requirements:**
- EKS API server endpoint access (443/TCP)
- AWS service endpoint access (ECR, S3, STS, etc.)
- Stable low-latency connection

```bash
# Check Site-to-Site VPN configuration
aws ec2 describe-vpn-connections \
  --filters Name=state,Values=available

# Monitor VPN connection status
aws cloudwatch get-metric-statistics \
  --namespace AWS/VPN \
  --metric-name TunnelState \
  --dimensions Name=VpnId,Value=vpn-xxxxxx
```

</details>

### 2. Which firewall port must be opened for Hybrid Nodes to communicate with the EKS control plane?

A. 22/TCP (SSH)
B. 443/TCP (HTTPS)
C. 8080/TCP (HTTP Proxy)
D. 3306/TCP (MySQL)

<details>
<summary>Show Answer</summary>

**Answer: B. 443/TCP (HTTPS)**

**Explanation:**
Hybrid Nodes communicate with the EKS API server over HTTPS (443/TCP). Required firewall rules:

| Port | Protocol | Purpose | Direction |
|------|----------|---------|-----------|
| 443 | TCP | EKS API server, AWS services | Outbound |
| 10250 | TCP | kubelet API | Inbound |
| 10255 | TCP | kubelet read-only | Inbound (optional) |

```bash
# Check firewall rules (iptables)
sudo iptables -L -n

# Test connectivity
curl -v https://<eks-api-endpoint>:443/healthz
```

</details>

### 3. What are 3 VPC endpoints needed for AWS service access in EKS Hybrid Nodes?

A. ec2, ecr.api, sts
B. lambda, dynamodb, sns
C. rds, elasticache, sqs
D. cloudfront, route53, waf

<details>
<summary>Show Answer</summary>

**Answer: A. ec2, ecr.api, sts**

**Explanation:**
Key VPC endpoints needed for Hybrid Nodes to access AWS services:

1. **ec2.region.amazonaws.com** (EC2 API)
2. **ecr.api.region.amazonaws.com** (ECR API)
3. **sts.region.amazonaws.com** (STS - IAM authentication)

**Additional Recommended Endpoints:**
- `ecr.dkr.region.amazonaws.com` (ECR Docker Registry)
- `s3.region.amazonaws.com` (S3 - ECR image storage)
- `logs.region.amazonaws.com` (CloudWatch Logs)
- `ssm.region.amazonaws.com` (Systems Manager)

```bash
# Create VPC Endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxx \
  --service-name com.amazonaws.us-west-2.sts \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-xxx \
  --security-group-ids sg-xxx
```

</details>

### 4. Which is NOT a consideration when configuring Pod network (CIDR) in a Hybrid Nodes environment?

A. Prevent CIDR conflicts with on-premises network
B. Separate VPC CIDR and Pod CIDR
C. Pod CIDR must be a /8 range
D. Prevent Pod CIDR overlap between clusters

<details>
<summary>Show Answer</summary>

**Answer: C. Pod CIDR must be a /8 range**

**Explanation:**
Pod CIDR does not need to be a /8 range. Typically /16 to /24 ranges are used. Key considerations:

- **CIDR conflict prevention**: No overlap between on-premises, VPC, and Pod networks
- **Appropriate size**: Determine CIDR size based on expected Pod count
- **Routability**: Pod CIDR must be routable from on-premises

```yaml
# Configure Pod CIDR in nodeadm settings
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  kubelet:
    config:
      podCIDR: "10.244.0.0/16"
```

| Network Type | Recommended CIDR Example |
|--------------|-------------------------|
| VPC | 10.0.0.0/16 |
| Pod | 10.244.0.0/16 |
| Service | 10.100.0.0/16 |
| On-premises | 192.168.0.0/16 |

</details>

### 5. What IP address is commonly used as the cluster DNS server address when configuring DNS for Hybrid Nodes?

A. 8.8.8.8
B. 10.100.0.10
C. 192.168.1.1
D. 169.254.169.254

<details>
<summary>Show Answer</summary>

**Answer: B. 10.100.0.10**

**Explanation:**
In EKS clusters, the CoreDNS service typically uses a fixed IP within the Service CIDR range. The default is `10.100.0.10`.

```yaml
# Configure cluster DNS in nodeadm settings
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  kubelet:
    config:
      clusterDNS:
        - 10.100.0.10
      clusterDomain: cluster.local
```

```bash
# Check CoreDNS service IP
kubectl get svc -n kube-system kube-dns

# Test DNS resolution
kubectl run test --image=busybox --rm -it -- nslookup kubernetes.default
```

</details>

### 6. What is the recommended network latency for communication between Hybrid Nodes and cloud nodes?

A. 500ms or less
B. 200ms or less
C. 100ms or less
D. 50ms or less

<details>
<summary>Show Answer</summary>

**Answer: C. 100ms or less**

**Explanation:**
Network latency of 100ms or less is recommended for stable communication with the Kubernetes API server.

| Latency | Impact |
|---------|--------|
| < 50ms | Optimal (Direct Connect recommended) |
| 50-100ms | Good (VPN usable) |
| 100-200ms | Warning (some timeouts possible) |
| > 200ms | Unsuitable (frequent disconnections) |

```bash
# Measure latency
ping -c 10 <eks-api-endpoint>

# Measure TCP connection time
curl -w "Connect: %{time_connect}s\n" -o /dev/null -s https://<eks-api-endpoint>
```

Using Direct Connect can achieve consistent latency under 10ms.

</details>

