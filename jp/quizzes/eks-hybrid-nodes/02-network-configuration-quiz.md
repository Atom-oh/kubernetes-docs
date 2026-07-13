# EKS Hybrid Nodes ネットワーク設定クイズ

> **関連ドキュメント**: [ネットワーク設定](../../eks-hybrid-nodes/02-network-configuration.md)

## 多肢選択問題

### 1. EKS Hybrid Nodes のオンプレミスとクラウド間のネットワーク接続に推奨される方法は何ですか？

A. パブリックインターネット接続
B. AWS Direct Connect または Site-to-Site VPN
C. SSH tunneling
D. HTTP proxy

<details>
<summary>回答を表示</summary>

**回答: B. AWS Direct Connect または Site-to-Site VPN**

**解説:**
EKS Hybrid Nodes には、EKS control plane（制御プレーン）への安定した安全なネットワーク接続が必要です。AWS Direct Connect（専用線）または Site-to-Site VPN が推奨されます。

**ネットワーク要件:**
- EKS API server endpoint へのアクセス (443/TCP)
- AWS service endpoint へのアクセス (ECR, S3, STS, etc.)
- 安定した低レイテンシ接続

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

### 2. Hybrid Nodes が EKS control plane と通信するために開く必要がある firewall port はどれですか？

A. 22/TCP (SSH)
B. 443/TCP (HTTPS)
C. 8080/TCP (HTTP Proxy)
D. 3306/TCP (MySQL)

<details>
<summary>回答を表示</summary>

**回答: B. 443/TCP (HTTPS)**

**解説:**
Hybrid Nodes は HTTPS (443/TCP) 経由で EKS API server と通信します。必要な firewall rules は次のとおりです:

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

### 3. EKS Hybrid Nodes で AWS service access に必要な 3 つの VPC endpoints はどれですか？

A. ec2, ecr.api, sts
B. lambda, dynamodb, sns
C. rds, elasticache, sqs
D. cloudfront, route53, waf

<details>
<summary>回答を表示</summary>

**回答: A. ec2, ecr.api, sts**

**解説:**
Hybrid Nodes が AWS services にアクセスするために必要な主な VPC endpoints は次のとおりです:

1. **ec2.region.amazonaws.com** (EC2 API)
2. **ecr.api.region.amazonaws.com** (ECR API)
3. **sts.region.amazonaws.com** (STS - IAM authentication)

**追加の推奨 Endpoints:**
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

### 4. Hybrid Nodes 環境で Pod network (CIDR) を設定する際の考慮事項ではないものはどれですか？

A. オンプレミスネットワークとの CIDR conflicts を防ぐ
B. VPC CIDR と Pod CIDR を分離する
C. Pod CIDR は /8 range でなければならない
D. clusters 間で Pod CIDR overlap を防ぐ

<details>
<summary>回答を表示</summary>

**回答: C. Pod CIDR は /8 range でなければならない**

**解説:**
Pod CIDR は /8 range である必要はありません。通常は /16 から /24 の range が使用されます。主な考慮事項は次のとおりです:

- **CIDR conflict prevention**: オンプレミス、VPC、Pod networks 間で overlap がないこと
- **Appropriate size**: 想定される Pod 数に基づいて CIDR size を決定する
- **Routability**: Pod CIDR はオンプレミスから routable である必要がある

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

### 5. Hybrid Nodes の DNS を設定する際に、cluster DNS server address として一般的に使用される IP address は何ですか？

A. 8.8.8.8
B. 10.100.0.10
C. 192.168.1.1
D. 169.254.169.254

<details>
<summary>回答を表示</summary>

**回答: B. 10.100.0.10**

**解説:**
EKS clusters では、CoreDNS service は通常、Service CIDR range 内の固定 IP を使用します。デフォルトは `10.100.0.10` です。

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

### 6. Hybrid Nodes と cloud nodes 間の通信に推奨される network latency はどれくらいですか？

A. 500ms 以下
B. 200ms 以下
C. 100ms 以下
D. 50ms 以下

<details>
<summary>回答を表示</summary>

**回答: C. 100ms 以下**

**解説:**
Kubernetes API server との安定した通信には、100ms 以下の network latency が推奨されます。

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

Direct Connect を使用すると、10ms 未満の一貫した latency を実現できます。

</details>
