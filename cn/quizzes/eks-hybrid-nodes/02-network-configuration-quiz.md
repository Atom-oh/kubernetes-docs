# EKS Hybrid Nodes 网络配置测验

> **相关文档**: [网络配置](../../eks-hybrid-nodes/02-network-configuration.md)

## 选择题

### 1. 对于 EKS Hybrid Nodes，本地环境与云之间网络连接的推荐方法是什么？

A. 公共互联网连接
B. AWS Direct Connect 或 Site-to-Site VPN
C. SSH 隧道
D. HTTP 代理

<details>
<summary>显示答案</summary>

**答案: B. AWS Direct Connect 或 Site-to-Site VPN**

**说明:**
EKS Hybrid Nodes 需要与 EKS control plane 建立稳定且安全的网络连接。推荐使用 AWS Direct Connect（专线）或 Site-to-Site VPN。

**网络要求:**
- EKS API server endpoint 访问 (443/TCP)
- AWS service endpoint 访问 (ECR, S3, STS, etc.)
- 稳定的低延迟连接

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

### 2. Hybrid Nodes 与 EKS control plane 通信时，必须打开哪个 firewall 端口？

A. 22/TCP (SSH)
B. 443/TCP (HTTPS)
C. 8080/TCP (HTTP Proxy)
D. 3306/TCP (MySQL)

<details>
<summary>显示答案</summary>

**答案: B. 443/TCP (HTTPS)**

**说明:**
Hybrid Nodes 通过 HTTPS (443/TCP) 与 EKS API server 通信。所需的 firewall 规则：

| 端口 | 协议 | 用途 | 方向 |
|------|----------|---------|-----------|
| 443 | TCP | EKS API server, AWS services | 出站 |
| 10250 | TCP | kubelet API | 入站 |
| 10255 | TCP | kubelet read-only | 入站（可选） |

```bash
# Check firewall rules (iptables)
sudo iptables -L -n

# Test connectivity
curl -v https://<eks-api-endpoint>:443/healthz
```

</details>

### 3. EKS Hybrid Nodes 中访问 AWS services 所需的 3 个 VPC endpoints 是什么？

A. ec2, ecr.api, sts
B. lambda, dynamodb, sns
C. rds, elasticache, sqs
D. cloudfront, route53, waf

<details>
<summary>显示答案</summary>

**答案: A. ec2, ecr.api, sts**

**说明:**
Hybrid Nodes 访问 AWS services 所需的关键 VPC endpoints：

1. **ec2.region.amazonaws.com** (EC2 API)
2. **ecr.api.region.amazonaws.com** (ECR API)
3. **sts.region.amazonaws.com** (STS - IAM 身份验证)

**其他推荐的 endpoints:**
- `ecr.dkr.region.amazonaws.com` (ECR Docker Registry)
- `s3.region.amazonaws.com` (S3 - ECR image 存储)
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

### 4. 在 Hybrid Nodes 环境中配置 Pod（容器组）网络 (CIDR) 时，哪一项不是需要考虑的事项？

A. 防止 CIDR 与本地网络冲突
B. 分离 VPC CIDR 和 Pod CIDR
C. Pod CIDR 必须是 /8 范围
D. 防止集群之间 Pod CIDR 重叠

<details>
<summary>显示答案</summary>

**答案: C. Pod CIDR 必须是 /8 范围**

**说明:**
Pod CIDR 不需要是 /8 范围。通常使用 /16 到 /24 范围。关键考虑事项：

- **防止 CIDR 冲突**: 本地环境、VPC 和 Pod 网络之间不能重叠
- **适当的大小**: 根据预期的 Pod 数量确定 CIDR 大小
- **可路由性**: Pod CIDR 必须可从本地环境路由

```yaml
# Configure Pod CIDR in nodeadm settings
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  kubelet:
    config:
      podCIDR: "10.244.0.0/16"
```

| 网络类型 | 推荐 CIDR 示例 |
|--------------|-------------------------|
| VPC | 10.0.0.0/16 |
| Pod | 10.244.0.0/16 |
| Service | 10.100.0.0/16 |
| 本地环境 | 192.168.0.0/16 |

</details>

### 5. 为 Hybrid Nodes 配置 DNS 时，通常使用哪个 IP 地址作为集群 DNS server 地址？

A. 8.8.8.8
B. 10.100.0.10
C. 192.168.1.1
D. 169.254.169.254

<details>
<summary>显示答案</summary>

**答案: B. 10.100.0.10**

**说明:**
在 EKS clusters 中，CoreDNS service 通常使用 Service CIDR 范围内的固定 IP。默认值是 `10.100.0.10`。

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

### 6. Hybrid Nodes 与云节点之间通信的推荐网络延迟是多少？

A. 500ms 或更低
B. 200ms 或更低
C. 100ms 或更低
D. 50ms 或更低

<details>
<summary>显示答案</summary>

**答案: C. 100ms 或更低**

**说明:**
建议网络延迟为 100ms 或更低，以便与 Kubernetes API server 稳定通信。

| 延迟 | 影响 |
|---------|--------|
| < 50ms | 最佳（推荐 Direct Connect） |
| 50-100ms | 良好（可使用 VPN） |
| 100-200ms | 警告（可能出现一些超时） |
| > 200ms | 不适合（频繁断开连接） |

```bash
# Measure latency
ping -c 10 <eks-api-endpoint>

# Measure TCP connection time
curl -w "Connect: %{time_connect}s\n" -o /dev/null -s https://<eks-api-endpoint>
```

使用 Direct Connect 可以实现低于 10ms 的稳定延迟。

</details>
