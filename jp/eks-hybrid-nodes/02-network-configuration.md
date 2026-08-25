# ネットワーク設定

< [前へ: 前提条件](01-prerequisites.md) | [目次](./README.md) | [次へ: エアギャップ設定](03-airgap-setup.md) >

> **サポート対象バージョン**: EKS 1.31+, nodeadm 0.1+ **最終更新**: February 23, 2026

このドキュメントでは、CIDR 要件、ファイアウォールルール、AWS エンドポイントアクセス、Security Group 設定、DNS セットアップなど、EKS Hybrid Nodes に必要なネットワーク設定について説明します。

## ネットワークアーキテクチャの概要

次の図は、VPC 設定、Transit Gateway ルーティング、リモート CIDR、ファイアウォールルールを含む、EKS Hybrid Nodes の完全なネットワークトポロジーを示しています。

![EKS Hybrid Nodes Network Prerequisites](../.gitbook/assets/hybrid-prereq-diagram.png)

### ネットワークハブとしての VPC

EKS Hybrid Nodes 環境では、VPC が hybrid node と control plane の間の**ネットワークハブ**として機能します。

* **ENI の配置**: EKS control plane は VPC subnet 内に ENI (Elastic Network Interface) を配置します。これらの ENI は control plane と hybrid node 間の通信エンドポイントです。
* **トラフィックパス**: control plane と hybrid node 間のすべてのトラフィックは、これらの ENI を通過します。API server リクエスト、kubelet 通信、webhook 呼び出し、およびすべての control plane トラフィックが VPC ENI を通過します。
* **ENI IP の変更**: cluster 更新（例: バージョンアップグレード）中に、ENI が削除および再作成される場合があり、IP アドレスが変更される可能性があります。ファイアウォールルールで個別の IP ではなく subnet CIDR 範囲を使用すると、このような変更に柔軟に対応できます。

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                                │
│  ┌──────────────────┐    ┌──────────────────────────────────┐   │
│  │  EKS Control     │    │              VPC                  │   │
│  │     Plane        │◄──►│  ┌────────┐  ┌────────┐          │   │
│  │                  │    │  │  ENI   │  │  ENI   │          │   │
│  └──────────────────┘    │  │10.0.1.x│  │10.0.2.x│          │   │
│                          │  └────┬───┘  └────┬───┘          │   │
│                          └───────┼───────────┼──────────────┘   │
└──────────────────────────────────┼───────────┼──────────────────┘
                                   │           │
                           VPN / Direct Connect
                                   │           │
┌──────────────────────────────────┼───────────┼──────────────────┐
│                          On-Premises                             │
│                    ┌─────────────┴───────────┴─────────────┐    │
│                    │         Hybrid Nodes                   │    │
│                    │   ┌─────────┐    ┌─────────┐          │    │
│                    │   │  Node   │    │  Node   │          │    │
│                    │   │ kubelet │    │ kubelet │          │    │
│                    │   └─────────┘    └─────────┘          │    │
│                    └───────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## CIDR 範囲の要件

オンプレミスの node および Pod CIDR は、次の要件を満たす必要があります。

* **RFC-1918 範囲**内であること: `10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16`
* 次の CIDR と**重複しない**こと:
  * 相互（node CIDR と Pod CIDR）
  * EKS cluster の VPC CIDR
  * Kubernetes Service IPv4 CIDR

`RemoteNodeNetwork` および `RemotePodNetwork` フィールドは、EKS cluster の作成時に指定します。

### ルーティング可能な Pod ネットワークとルーティング不可能な Pod ネットワーク

| 設定                    | ルーティング可能（推奨）                              | ルーティング不可能                |
| ----------------------- | --------------------------------------------------- | ----------------------------- |
| セットアップ            | BGP（推奨）、静的ルート、またはカスタムルーティング | CNI egress masquerade/NAT     |
| Webhook                 | hybrid node 上で実行可能                            | cloud node 上でのみ実行可能   |
| Pod↔Pod 通信            | cloud↔オンプレミスの直接通信                        | 不可能                        |
| AWS service 統合        | ALB、Prometheus などが hybrid workload に到達可能   | hybrid workload に到達不可    |

> **推奨**: Cilium BGP Control Plane を使用して Pod CIDR をルーティング可能にします。

***

## 必要なファイアウォールポート

### Cluster 通信ポート

オンプレミスと AWS 間の通信のために、次のポートを開放する必要があります。

| ポート        | プロトコル   | 方向          | 目的                                                                     |
| ------------- | ------------ | ------------- | ------------------------------------------------------------------------ |
| 443           | TCP          | On-Prem → AWS | kubelet から Kubernetes API server                                      |
| 443           | TCP          | On-Prem → AWS | Pod から Kubernetes API server                                          |
| 10250         | TCP          | AWS → On-Prem | API server から kubelet                                                 |
| Webhook ポート | TCP          | AWS → On-Prem | API server から webhook（ルーティング可能な Pod ネットワークのみ）    |
| 53            | TCP/UDP      | 双方向        | CoreDNS (pod CIDR ↔ pod CIDR。CoreDNS が cloud で実行される場合は VPC CIDR を含む) |
| App ポート     | ユーザー定義 | 双方向        | Pod 間のアプリケーション通信                                            |

### VPN ポート（Site-to-Site VPN 使用時）

| ポート | プロトコル | 方向     | 目的                        |
| ---- | -------- | ------------- | --------------------------- |
| 500  | UDP      | 双方向        | IKE (Internet Key Exchange) |
| 4500 | UDP      | 双方向        | IPSec NAT-T                 |

### Cilium CNI ポート

Cilium を CNI として使用する場合に必要な追加ポート:

| ポート | プロトコル | 方向     | 目的                                |
| ---- | -------- | ------------- | ----------------------------------- |
| 8472 | UDP      | 双方向        | VXLAN overlay（デフォルトの tunnel mode） |
| 4240 | TCP      | 双方向        | ヘルスチェック                      |

> **注記**: Cilium および Calico の詳細なファイアウォール要件については、各プロジェクトの公式ドキュメントを参照してください。

### iptables ルールの例

```bash
# Allow Kubernetes API server communication
sudo iptables -A INPUT -p tcp --dport 443 -s 10.0.0.0/8 -j ACCEPT
sudo iptables -A OUTPUT -p tcp --dport 443 -d 10.0.0.0/8 -j ACCEPT

# Allow Kubelet API
sudo iptables -A INPUT -p tcp --dport 10250 -s 10.0.0.0/8 -j ACCEPT

# Allow Cilium VXLAN
sudo iptables -A INPUT -p udp --dport 8472 -j ACCEPT
sudo iptables -A OUTPUT -p udp --dport 8472 -j ACCEPT

# Allow Cilium health check
sudo iptables -A INPUT -p tcp --dport 4240 -j ACCEPT
sudo iptables -A OUTPUT -p tcp --dport 4240 -j ACCEPT

# Allow DNS
sudo iptables -A INPUT -p tcp --dport 53 -j ACCEPT
sudo iptables -A INPUT -p udp --dport 53 -j ACCEPT
sudo iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT
sudo iptables -A OUTPUT -p udp --dport 53 -j ACCEPT

# Save rules
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

***

## オンプレミスからのアウトバウンドアクセス要件

### インストールおよびアップグレードに必要なエンドポイント

nodeadm のインストールおよびアップグレード中に、オンプレミス node から HTTPS (443) で次の AWS エンドポイントに到達できる必要があります。

| コンポーネント           | URL                                                     | 注記                                  |
| ----------------------- | ------------------------------------------------------- | ------------------------------------- |
| EKS node artifact (S3)  | `https://hybrid-assets.eks.amazonaws.com`               | nodeadm binary と依存関係             |
| EKS service             | `https://eks.<region>.amazonaws.com`                    | Cluster 情報の検索                    |
| ECR service             | `https://api.ecr.<region>.amazonaws.com`                | container image の pull               |
| SSM binary              | `https://amazon-ssm-<region>.s3.<region>.amazonaws.com` | SSM credential provider 使用時        |
| SSM service             | `https://ssm.<region>.amazonaws.com`                    | SSM credential provider 使用時        |
| IAM Roles Anywhere      | `https://rolesanywhere.<region>.amazonaws.com`          | IAM RA credential provider 使用時     |
| OS package manager      | リージョン固有のエンドポイント                          | system package のインストール         |

### 継続的な運用に必要なエンドポイント

| 目的                      | 送信元    | 宛先                  | 注記                      |
| ------------------------- | --------- | --------------------- | --------------------------- |
| Kubelet → API server      | Node CIDR | EKS cluster IP        | ポート 443                  |
| Pod → API server          | Pod CIDR  | EKS cluster IP        | ポート 443                  |
| SSM credential 更新       | Node CIDR | SSM エンドポイント    | 5 分間の heartbeat 間隔     |
| IAM RA credential 更新    | Node CIDR | IAM Anywhere endpoint | 定期的な更新                |
| EKS Pod Identity          | Node CIDR | EKS Auth endpoint     | Pod Identity 使用時         |

### EKS Cluster Network Interface IP の検出

ファイアウォールルールに EKS cluster IP が必要な場合は、次のコマンドを使用します。

```bash
aws ec2 describe-network-interfaces \
  --filters "Name=vpc-id,Values=<VPC_ID>" "Name=description,Values=Amazon EKS*" \
  --query 'NetworkInterfaces[].PrivateIpAddress' \
  --output text
```

> **注記**: EKS network interface は、cluster 更新（例: バージョンアップグレード）中に削除および再作成される場合があります。制約された subnet サイズを使用すると IP 範囲を予測可能にでき、ファイアウォール設定が簡素化されます。

***

## VPC Private Endpoint（エアギャップ / Private Connectivity）

オンプレミス node が internet access なしで VPN または Direct Connect 経由で AWS に接続する場合、AWS service にプライベートに到達するために **VPC Interface Endpoint** (PrivateLink) を設定する必要があります。

### VPC Endpoint が必要な理由

標準の AWS API 呼び出しは public internet を経由します。エアギャップまたは private-only 環境では internet path がないため、AWS service に到達できません。VPC Interface Endpoint は、VPC 内に private IP address を持つ ENI (Elastic Network Interface) を作成し、オンプレミス node が VPN/Direct Connect 経由で AWS API に直接到達できるようにします。

```
On-premises node
  → VPN / Direct Connect
    → VPC Interface Endpoint ENI (private IP)
      → AWS Service (EKS, ECR, STS, SSM, etc.)
```

> **重要ポイント**: Gateway endpoint（S3 および DynamoDB 用）は VPC route table に route を追加するだけであり、VPN/Direct Connect 経由で**オンプレミスネットワークから到達できません**。オンプレミスから S3 にアクセスするには、**Interface type** S3 endpoint を使用する必要があります。

### 必要な Interface VPC Endpoint

| Service      | Endpoint Service Name                | Private DNS | 目的                                                 |
| ------------ | ------------------------------------ | ----------- | ---------------------------------------------------- |
| EKS          | `com.amazonaws.<region>.eks`         | Yes         | Kubernetes API server 通信                           |
| EKS Auth     | `com.amazonaws.<region>.eks-auth`    | Yes         | Pod Identity 認証                                    |
| ECR API      | `com.amazonaws.<region>.ecr.api`     | Yes         | image metadata クエリ                                |
| ECR DKR      | `com.amazonaws.<region>.ecr.dkr`     | Yes         | image pull (Docker registry)                         |
| S3           | `com.amazonaws.<region>.s3`          | —           | image layer、nodeadm artifact（**Interface type**） |
| STS          | `com.amazonaws.<region>.sts`         | Yes         | IAM credential exchange                              |
| SSM          | `com.amazonaws.<region>.ssm`         | Yes         | SSM credential provider 使用時                       |
| SSM Messages | `com.amazonaws.<region>.ssmmessages` | Yes         | SSM Session Manager 通信                             |

> **注記**: S3 Interface endpoint は `private_dns_enabled` を自動的にはサポートしません。S3 domain の Private DNS resolution が必要な場合は、別の Private Hosted Zone (PHZ) を設定する必要があります。`hybrid-assets.eks.amazonaws.com` の private mirroring パターンについては、[エアギャップ設定 - hybrid-assets Private Mirroring](03-airgap-setup.md#hybrid-assets-private-mirroring-s3--phz-pattern) を参照してください。

### Terraform を使用した VPC Endpoint の作成

#### Security Group

```hcl
resource "aws_security_group" "vpc_endpoints" {
  name_prefix = "vpc-endpoints-"
  vpc_id      = var.vpc_id
  description = "Security group for VPC Interface Endpoints"

  ingress {
    description = "HTTPS from VPC and on-premises"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [
      var.vpc_cidr,           # VPC internal traffic
      var.remote_node_cidr,   # On-premises node CIDR
      var.remote_pod_cidr     # On-premises pod CIDR
    ]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "vpc-endpoints-sg"
  }
}
```

#### Interface VPC Endpoint

```hcl
# List of Interface endpoints to create
locals {
  interface_endpoints = {
    eks          = "com.amazonaws.${var.region}.eks"
    eks-auth     = "com.amazonaws.${var.region}.eks-auth"
    ecr-api      = "com.amazonaws.${var.region}.ecr.api"
    ecr-dkr      = "com.amazonaws.${var.region}.ecr.dkr"
    sts          = "com.amazonaws.${var.region}.sts"
    ssm          = "com.amazonaws.${var.region}.ssm"
    ssmmessages  = "com.amazonaws.${var.region}.ssmmessages"
  }
}

resource "aws_vpc_endpoint" "interface" {
  for_each = local.interface_endpoints

  vpc_id              = var.vpc_id
  service_name        = each.value
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true

  subnet_ids         = var.private_subnet_ids
  security_group_ids = [aws_security_group.vpc_endpoints.id]

  tags = {
    Name = "vpce-${each.key}"
  }
}

# S3 Interface endpoint (Interface type, not Gateway)
resource "aws_vpc_endpoint" "s3_interface" {
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = false  # S3 does not support auto Private DNS for Interface type

  subnet_ids         = var.private_subnet_ids
  security_group_ids = [aws_security_group.vpc_endpoints.id]

  tags = {
    Name = "vpce-s3-interface"
  }
}
```

### AWS CLI を使用した VPC Endpoint の作成

```bash
# 1. Create security group for VPC endpoints
SG_ID=$(aws ec2 create-security-group \
  --group-name vpc-endpoints-sg \
  --description "Security group for VPC Interface Endpoints" \
  --vpc-id <VPC_ID> \
  --query 'GroupId' --output text)

# Allow port 443 inbound
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --ip-permissions '[
    {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443,
     "IpRanges": [
       {"CidrIp": "<VPC_CIDR>", "Description": "VPC internal"},
       {"CidrIp": "<REMOTE_NODE_CIDR>", "Description": "On-prem nodes"},
       {"CidrIp": "<REMOTE_POD_CIDR>", "Description": "On-prem pods"}
     ]}
  ]'

# 2. Create Interface VPC endpoint (EKS example)
aws ec2 create-vpc-endpoint \
  --vpc-id <VPC_ID> \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.<REGION>.eks \
  --subnet-ids <SUBNET_ID_1> <SUBNET_ID_2> \
  --security-group-ids $SG_ID \
  --private-dns-enabled

# 3. Create remaining service endpoints
for SERVICE in eks-auth ecr.api ecr.dkr sts ssm ssmmessages; do
  echo "Creating endpoint for: $SERVICE"
  aws ec2 create-vpc-endpoint \
    --vpc-id <VPC_ID> \
    --vpc-endpoint-type Interface \
    --service-name com.amazonaws.<REGION>.$SERVICE \
    --subnet-ids <SUBNET_ID_1> <SUBNET_ID_2> \
    --security-group-ids $SG_ID \
    --private-dns-enabled
done

# 4. S3 Interface endpoint (without private-dns-enabled)
aws ec2 create-vpc-endpoint \
  --vpc-id <VPC_ID> \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.<REGION>.s3 \
  --subnet-ids <SUBNET_ID_1> <SUBNET_ID_2> \
  --security-group-ids $SG_ID

# 5. Verify created endpoints
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=<VPC_ID>" \
  --query 'VpcEndpoints[].{ID:VpcEndpointId, Service:ServiceName, State:State}' \
  --output table
```

### オンプレミス DNS 解決フロー

VPC endpoint の `private_dns_enabled` オプションは VPC 内でのみ機能します。オンプレミス node が AWS service domain（例: `eks.ap-northeast-2.amazonaws.com`）を VPC endpoint の private IP に解決できるようにするには、DNS クエリを Route 53 Resolver Inbound Endpoint 経由でルーティングする必要があります。

```
On-premises node
  → On-premises DNS server (conditional forwarding)
    → Route 53 Resolver Inbound Endpoint (in VPC)
      → Route 53 resolves via Private Hosted Zone / VPC DNS
        → Returns VPC Endpoint ENI private IP
          → On-premises node reaches ENI directly over VPN/DX
```

#### オンプレミス DNS での条件付きフォワーディングの設定

オンプレミス DNS server（例: BIND、Windows DNS、dnsmasq）を設定して、AWS domain を Route 53 Inbound Endpoint に転送します。

```
# BIND example (/etc/named.conf)
zone "amazonaws.com" {
    type forward;
    forward only;
    forwarders {
        10.0.1.10;    # Route 53 Inbound Endpoint IP #1
        10.0.2.10;    # Route 53 Inbound Endpoint IP #2
    };
};

zone "eks.amazonaws.com" {
    type forward;
    forward only;
    forwarders {
        10.0.1.10;
        10.0.2.10;
    };
};
```

> **注記**: Route 53 Resolver Inbound Endpoint の作成については、このドキュメントの [DNS 設定](02-network-configuration.md#dns-configuration) セクションを参照してください。VPC endpoint の設定後は、必ず `nslookup eks.<region>.amazonaws.com` で private IP が返されることを確認してください。

***

## AWS Security Group 設定

EKS は cluster 作成時に Security Group の inbound rule を自動設定しますが、outbound rule は自動作成されません（Security Group はデフォルトで全 outbound を許可します）。

### 自動作成される Inbound Rule

| プロトコル | ポート | 送信元              | 目的                                  |
| -------- | ---- | ------------------- | ------------------------------------ |
| TCP      | 443  | Remote node CIDR    | kubelet から Kubernetes API          |
| TCP      | 443  | Remote Pod CIDR     | Kubernetes API への Pod（non-NAT CNI） |

### 手動で追加する Outbound Rule

| プロトコル | ポート        | 宛先                | 目的                       |
| -------- | ------------- | ------------------- | ---------------------- |
| TCP      | 10250         | Remote node CIDR    | API server から kubelet |
| TCP      | Webhook ポート | Remote Pod CIDR     | API server から webhook |

```bash
# Example: Create a custom security group
aws ec2 create-security-group \
  --group-name hybrid-nodes-sg \
  --description "Security group for EKS Hybrid Nodes" \
  --vpc-id <VPC_ID>

# Add inbound rules
aws ec2 authorize-security-group-ingress \
  --group-id <SG_ID> \
  --ip-permissions '[
    {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443,
     "IpRanges": [{"CidrIp": "<REMOTE_NODE_CIDR>"}, {"CidrIp": "<REMOTE_POD_CIDR>"}]}
  ]'
```

> **注意**: デフォルトの上限は、Security Group あたり 60 inbound rule です。また、remote network が削除されても EKS は rule を自動的に削除しないため、手動でのクリーンアップが必要です。

***

## Pod CIDR ファイアウォール戦略

Pod 間通信のために、Pod CIDR 範囲全体のファイアウォールルールを登録する必要があります。

```bash
# Pod CIDR range example: 10.244.0.0/16
# Check cluster's Pod CIDR
kubectl cluster-info dump | grep -m 1 cluster-cidr

# Add firewall rules for Pod CIDR
sudo iptables -A INPUT -s 10.244.0.0/16 -j ACCEPT
sudo iptables -A OUTPUT -d 10.244.0.0/16 -j ACCEPT
sudo iptables -A FORWARD -s 10.244.0.0/16 -j ACCEPT
sudo iptables -A FORWARD -d 10.244.0.0/16 -j ACCEPT

# Add Service CIDR as well (e.g., 172.20.0.0/16)
sudo iptables -A INPUT -s 172.20.0.0/16 -j ACCEPT
sudo iptables -A OUTPUT -d 172.20.0.0/16 -j ACCEPT
```

***

## DNS 設定

### Route 53 Resolver Inbound Endpoint

オンプレミスから AWS domain をクエリできるように、Inbound Endpoint を作成します。

```bash
# Create Inbound Endpoint
aws route53resolver create-resolver-endpoint \
  --creator-request-id "hybrid-inbound-$(date +%s)" \
  --name "hybrid-inbound-endpoint" \
  --security-group-ids sg-0123456789abcdef0 \
  --direction INBOUND \
  --ip-addresses SubnetId=subnet-111111111,Ip=10.0.1.10 SubnetId=subnet-222222222,Ip=10.0.2.10

# Check Endpoint IPs
aws route53resolver list-resolver-endpoint-ip-addresses \
  --resolver-endpoint-id rslvr-in-xxxxxxxxxxxxx
```

### Route 53 Resolver Outbound Endpoint

AWS がオンプレミス domain をクエリできるように、Outbound Endpoint と forwarding rule を作成します。

```bash
# Create Outbound Endpoint
aws route53resolver create-resolver-endpoint \
  --creator-request-id "hybrid-outbound-$(date +%s)" \
  --name "hybrid-outbound-endpoint" \
  --security-group-ids sg-0123456789abcdef0 \
  --direction OUTBOUND \
  --ip-addresses SubnetId=subnet-111111111 SubnetId=subnet-222222222

# Create forwarding rule (on-premises domain)
aws route53resolver create-resolver-rule \
  --creator-request-id "forward-onprem-$(date +%s)" \
  --name "forward-to-onprem" \
  --rule-type FORWARD \
  --domain-name "internal.company.io" \
  --resolver-endpoint-id rslvr-out-xxxxxxxxxxxxx \
  --target-ips "Ip=192.168.1.10,Port=53" "Ip=192.168.1.11,Port=53"

# Associate rule with VPC
aws route53resolver associate-resolver-rule \
  --resolver-rule-id rslvr-rr-xxxxxxxxxxxxx \
  --vpc-id vpc-0123456789abcdef0
```

### CoreDNS カスタムドメイン設定

オンプレミス domain の DNS クエリをオンプレミス DNS server に転送します。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health {
            lameduck 5s
        }
        ready
        kubernetes cluster.local in-addr.arpa ip6.arpa {
            pods insecure
            fallthrough in-addr.arpa ip6.arpa
        }
        prometheus :9153
        forward . /etc/resolv.conf {
            max_concurrent 1000
        }
        cache 30
        loop
        reload
        loadbalance
    }
    internal.company.io:53 {
        errors
        cache 30
        forward . 192.168.1.10 192.168.1.11 {
            max_concurrent 1000
        }
    }
```

```bash
# Apply CoreDNS ConfigMap
kubectl apply -f coredns-configmap.yaml

# Restart CoreDNS
kubectl rollout restart deployment coredns -n kube-system

# Test DNS resolution
kubectl run dns-test --rm -it --image=busybox --restart=Never -- nslookup internal.company.io
```

### CoreDNS の二拠点 Deployment（オンプレミス + Cloud）

#### 二拠点 Deployment が必要な理由

EKS Hybrid Nodes 環境で、CoreDNS が cloud node 上でのみ実行されている場合、オンプレミス Pod からの DNS クエリは VPN/Direct Connect link を通って cloud へ往復する必要があります。反対に、CoreDNS がオンプレミス node 上でのみ実行されている場合、cloud Pod からの DNS クエリは逆方向のラウンドトリップを行う必要があります。

DNS latency を最小化し、一方で network outage が発生した場合でも DNS service availability を維持するには、**CoreDNS Pod が両側に存在する必要があります**。

#### 推奨 Replica 数

最小 **4 replica**（cloud 2 + オンプレミス 2）を推奨します。各ロケーションに少なくとも 2 replica を配置することで high availability を確保します。

#### CoreDNS Deployment Patch

`topologySpreadConstraints` と `tolerations` を使用して、CoreDNS Pod を cloud node とオンプレミス node に均等に分散します。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: coredns
  namespace: kube-system
spec:
  replicas: 4
  template:
    spec:
      tolerations:
        - key: "eks.amazonaws.com/compute-type"
          value: "hybrid"
          effect: "NoSchedule"
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: "eks.amazonaws.com/compute-type"
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              k8s-app: kube-dns
```

#### kubectl patch コマンド

```bash
kubectl patch deployment coredns -n kube-system --type=strategic -p '{
  "spec": {
    "replicas": 4,
    "template": {
      "spec": {
        "tolerations": [
          {
            "key": "eks.amazonaws.com/compute-type",
            "value": "hybrid",
            "effect": "NoSchedule"
          }
        ],
        "topologySpreadConstraints": [
          {
            "maxSkew": 1,
            "topologyKey": "eks.amazonaws.com/compute-type",
            "whenUnsatisfiable": "ScheduleAnyway",
            "labelSelector": {
              "matchLabels": {
                "k8s-app": "kube-dns"
              }
            }
          }
        ]
      }
    }
  }
}'
```

#### 配置の確認

```bash
# Verify CoreDNS Pods are distributed across both node types
kubectl get pods -n kube-system -l k8s-app=kube-dns -o wide

# Check compute-type labels on nodes
kubectl get nodes -L eks.amazonaws.com/compute-type
```

> **注記**:
>
> * EKS managed CoreDNS add-on を使用する場合、同じ設定を add-on の `configurationValues` で適用できます。
> * `whenUnsatisfiable: ScheduleAnyway` を使用すると、片側にしか node が存在しない場合でも scheduling がブロックされません。これにより、初期 cluster bootstrap 中に CoreDNS が正常に起動することを保証します。

***

## トラフィックフローパターン

AWS とオンプレミス間のトラフィックフローパターンを理解することは、ファイアウォール設定とトラブルシューティングに不可欠です。以下のセクションでは、公式 AWS アーキテクチャ図を用いて各トラフィックパターンを詳しく説明します。

> **出典**: [AWS EKS Hybrid Nodes Traffic Flows](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-concepts-traffic-flows.html)

### パターン 1: Kubelet → EKS Control Plane

Kubelet は DNS lookup 経由で API server endpoint に HTTPS リクエストを開始します。public access mode では、トラフィックは public internet を経由します。private mode では、トラフィックは VPN/DX 経由で VPC ENI に流れます。

![Kubelet to Control Plane](../.gitbook/assets/hybrid-nodes-kubelet-to-cp.svg)

### パターン 2: EKS Control Plane → Kubelet

API server は node status object から node IP を取得します。トラフィックは VPC を経由し、Direct Connect または VPN を介して cloud boundary を越え、port 10250 の kubelet に到達します。これは `kubectl logs`、`kubectl exec`、`kubectl port-forward` などで使用されます。

![Control Plane to Kubelet](../.gitbook/assets/hybrid-nodes-cp-to-kubelet.svg)

### パターン 3: Pod → EKS Control Plane

Pod は `kubernetes` Service (ClusterIP) 経由で Kubernetes API と通信します。kube-proxy は DNAT を適用して service IP を control plane ENI IP に変換し、その後 packet は VPN/DX 経由で VPC にルーティングされます。

* **CNI NAT なし**: Pod は kubernetes service IP（例: 172.16.0.1）に送信し、kube-proxy は control plane ENI IP に DNAT を適用します。return traffic には pod CIDR 経由の reverse routing が必要です。
* **CNI NAT あり**: CNI は node processing 前に SNAT を適用するため、return routing が簡素化されます（追加の pod CIDR routing は不要です）。

![Pod to Control Plane](../.gitbook/assets/hybrid-nodes-pod-to-cp.svg)

### パターン 4: EKS Control Plane → Pod (Webhook)

API server は、hybrid node 上で実行されている webhook Pod への直接接続を開始します。トラフィックは remote pod CIDR 向けに VPC を経由してルーティングされ、gateway を介して境界を越えます。これには**ルーティング可能な pod CIDR が必要です**。

![Control Plane to Pod](../.gitbook/assets/hybrid-nodes-cp-to-pod.svg)

> **重要**: オンプレミス pod CIDR がルーティング不可能な場合、**すべての webhook を cloud node 上で実行する必要があります**。以下の [Webhook 設定](02-network-configuration.md#webhook-configuration) を参照してください。

### パターン 5: Hybrid Node 上の Pod ↔ Pod

異なる hybrid node 上の Pod は、[VXLAN encapsulation](../networking/cilium/03-networking.md#vxlan-technology-deep-dive)（または Geneve、IP-in-IP などの同様の overlay protocol）を使用して通信します。CNI は、source/destination node IP を使用する outer header で元の pod-to-pod packet を encapsulate します。受信 node の CNI は decapsulate して destination Pod に配信します。

![Pod to Pod on Hybrid Nodes](../.gitbook/assets/hybrid-nodes-pod-to-pod.svg)

#### VXLAN Encapsulation の詳細

VXLAN (Virtual Extensible LAN) は L2 frame を L3 packet に encapsulate して overlay network を作成します。hybrid node 間の Pod 通信で packet structure がどのように変換されるかを以下に示します。

**元の Packet（Encapsulation 前）**

```
┌────────────────────────────────────────────────┐
│  Pod-A IP (src) → Pod-B IP (dst) │   Payload   │
│    10.85.0.10       10.85.1.20   │   (data)    │
└────────────────────────────────────────────────┘
```

**VXLAN Encapsulation 後**

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Outer IP Header │ UDP Header │ VXLAN Header │      Original Packet          │
│ Node-A → Node-B │ Port 8472  │    (VNI)     │ Pod-A IP → Pod-B IP │ Payload │
│ 10.80.1.10      │            │              │ 10.85.0.10  10.85.1.20        │
│   → 10.80.1.11  │            │              │                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Encapsulation Process（Source Node）**

1. Pod-A が Pod-B に packet を送信します
2. source node の CNI (Cilium) が destination Pod IP を検索し、target node を特定します
3. CNI が元の packet を VXLAN header と outer IP header でラップします
4. outer header は source/destination として node IP を使用します
5. encapsulate された packet は UDP port 8472 経由で送信されます

**Decapsulation Process（Destination Node）**

1. destination node は UDP port 8472 で VXLAN packet を受信します
2. CNI が VXLAN header と outer IP header を取り除きます
3. 元の packet が destination Pod に配信されます

**主要コンポーネント**

| コンポーネント                 | 説明                                                                       |
| ------------------------------ | ---------------------------------------------------------------------------- |
| VNI (VXLAN Network Identifier) | pod network traffic を分離する 24-bit identifier（デフォルト: 自動割り当て） |
| UDP Port                       | Cilium default: 8472、Standard VXLAN: 4789                                   |
| MTU                            | VXLAN overhead (50 bytes) を考慮する必要あり。例: 1500 → 1450                |

> **注記**: VXLAN に加えて、Cilium は Geneve や IP-in-IP などの他の tunnel protocol をサポートしています。`--tunnel` オプションを使用して tunnel mode を選択します。

### パターン 6: Cloud Pod ↔ Hybrid Pod (East-West)

VPC Pod（VPC CNI を使用）は hybrid Pod に直接送信し、VPC routing はオンプレミス gateway にトラフィックを転送します。packet は境界を越え、hybrid node に到着します。これには**ルーティング可能な pod CIDR と適切な VPC route table entry が必要です**。

![East-West Traffic](../.gitbook/assets/hybrid-nodes-east-west.svg)

### トラフィックフローの概要

| # | フロー                     | 方向             | ポート      | 要件                                |
| - | ------------------------ | ---------------- | --------- | ---------------------------------- |
| 1 | Kubelet → API Server     | On-Prem → AWS    | TCP 443   | VPN/DX または internet              |
| 2 | API Server → Kubelet     | AWS → On-Prem    | TCP 10250 | SG outbound rule                   |
| 3 | Pod → API Server         | On-Prem → AWS    | TCP 443   | kube-proxy DNAT                    |
| 4 | API Server → Webhook Pod | AWS → On-Prem    | TCP 8443+ | **ルーティング可能な pod CIDR**       |
| 5 | Hybrid Pod ↔ Hybrid Pod  | On-Prem 内部     | UDP 8472  | Cilium VXLAN                       |
| 6 | Cloud Pod ↔ Hybrid Pod   | AWS ↔ On-Prem    | VPC route | **ルーティング可能な pod CIDR** + VPC route |

### kube-proxy iptables Chain 構造

kube-proxy は iptables rule を使用して Kubernetes Service traffic を実際の Pod にルーティングします。同じ 3 層の chain structure が hybrid node にも適用されます。

```
KUBE-SERVICES (entry point)
  └─→ KUBE-SVC-xxxx (per-service chain, load balancing)
        └─→ KUBE-SEP-xxxx (per-endpoint chain, DNAT to pod IP)
```

**Chain の役割**

| Chain             | 役割                                                       | 例                                   |
| ----------------- | ---------------------------------------------------------- | ------------------------------------ |
| **KUBE-SERVICES** | destination IP:Port をすべての ClusterIP service と照合   | `172.20.0.1:443` → `KUBE-SVC-NPX...` |
| **KUBE-SVC-xxxx** | probability-based load balancing を使用して endpoint を選択 | 3 Pod → 各 33% の確率                 |
| **KUBE-SEP-xxxx** | 特定の Pod IP:Port への DNAT を実行                        | `10.85.0.15:8080` への DNAT           |

**実際の iptables Rule の例**

```bash
# KUBE-SERVICES chain (nat table)
-A KUBE-SERVICES -d 172.20.0.10/32 -p tcp -m tcp --dport 80 -j KUBE-SVC-XXXXXX

# KUBE-SVC chain (load balancing)
-A KUBE-SVC-XXXXXX -m statistic --mode random --probability 0.33333 -j KUBE-SEP-AAAAAA
-A KUBE-SVC-XXXXXX -m statistic --mode random --probability 0.50000 -j KUBE-SEP-BBBBBB
-A KUBE-SVC-XXXXXX -j KUBE-SEP-CCCCCC

# KUBE-SEP chain (DNAT)
-A KUBE-SEP-AAAAAA -p tcp -j DNAT --to-destination 10.85.0.15:8080
-A KUBE-SEP-BBBBBB -p tcp -j DNAT --to-destination 10.85.0.16:8080
-A KUBE-SEP-CCCCCC -p tcp -j DNAT --to-destination 10.85.1.20:8080
```

> **Hybrid Environment への影響**: 上記の例で、`10.85.1.20` が別の hybrid node 上の Pod である場合、DNAT 後の packet は VXLAN encapsulate されてその node に送信されます。kube-proxy は Service traffic を Pod IP に変換し、CNI は実際の network routing を処理します。

### kubelet Endpoint

kubelet は各 node で実行され、API server 通信のための REST endpoint を公開します。

**kubelet API Port と Endpoint**

| ポート | Endpoint                              | 目的                                             |
| ----- | ------------------------------------- | ------------------------------------------------ |
| 10250 | `/pods`                               | node 上で実行中の Pod を一覧表示                 |
| 10250 | `/exec/{namespace}/{pod}/{container}` | container 内でコマンドを実行（`kubectl exec`）   |
| 10250 | `/logs/{namespace}/{pod}/{container}` | container log を stream（`kubectl logs`）        |
| 10250 | `/metrics`                            | kubelet metric を公開（Prometheus scrape 用）    |
| 10250 | `/healthz`                            | kubelet ヘルスチェック                           |

**Node Registration と Address Reporting**

kubelet が cluster に node を登録すると、`Node.status.addresses` に address 情報を報告します。

```yaml
status:
  addresses:
  - address: 10.80.1.10        # Actual on-premises IP
    type: InternalIP
  - address: hybrid-node-001   # Node hostname
    type: Hostname
```

* **InternalIP**: node の実際のオンプレミス IP address。API server はこの address を使用して kubelet に接続します。
* **Hostname**: node の hostname。

> **ファイアウォールルールの要件**: API server は `InternalIP` を使用して kubelet に接続するため、**AWS → On-Prem からの TCP port 10250 を開放する必要があります**。この接続がブロックされると、`kubectl exec`、`kubectl logs`、`kubectl port-forward` などのコマンドは失敗します。

***

## ルーティング可能な Pod CIDR の設定

オンプレミス pod CIDR をルーティング可能にすることは、webhook、east-west traffic、および AWS service integration（ALB、Prometheus など）に不可欠です。

![Remote Pod CIDRs](../.gitbook/assets/hybrid-nodes-remote-pod-cidrs.png)

### オプション 1: BGP（推奨）

CNI は virtual router として動作し、node ごとの pod CIDR route をローカルのオンプレミス router に伝播します。これは最も dynamic で maintainable なアプローチです。

![BGP Routing](../.gitbook/assets/hybrid-nodes-bgp.png)

#### Cilium BGP Control Plane 設定

```yaml
apiVersion: cilium.io/v2alpha1
kind: CiliumBGPClusterConfig
metadata:
  name: hybrid-bgp-config
spec:
  bgpInstances:
  - name: hybrid-instance
    localASN: 65001
    peers:
    - name: on-prem-router
      peerASN: 65000
      peerAddress: 10.80.0.1
      peerConfigRef:
        name: on-prem-peer
---
apiVersion: cilium.io/v2alpha1
kind: CiliumBGPPeerConfig
metadata:
  name: on-prem-peer
spec:
  families:
  - afi: ipv4
    safi: unicast
  gracefulRestart:
    enabled: true
---
apiVersion: cilium.io/v2alpha1
kind: CiliumBGPAdvertisement
metadata:
  name: pod-cidr-advert
spec:
  advertisements:
  - advertisementType: PodCIDR
  - advertisementType: Service
    service:
      addresses:
      - ClusterIP
```

#### ASN (Autonomous System Number) について

上記の Cilium BGP 設定における `localASN` と `peerASN` は**Autonomous System Number**です。これは各 BGP participant に割り当てられる一意の identifier です。すべての BGP speaker（router、switch、またはこの場合は各 node 上の Cilium）には ASN が必要であり、接続先の peer にも ASN が必要です。

**Private ASN 範囲と Public ASN 範囲**

| 範囲                        | 種類           | ユースケース                                                                                |
| --------------------------- | -------------- | ------------------------------------------------------------------------------------------- |
| **64512 – 65534**           | 16-bit Private | internal network、data center、lab environment。**EKS Hybrid Nodes にはこの範囲を使用します。** |
| **4200000000 – 4294967294** | 32-bit Private | 多数の一意な ASN を必要とする大規模 internal deployment                                      |
| 1 – 64511                   | 16-bit Public  | RIR (ARIN、RIPE、APNIC) に登録された internet-facing network                                 |

> **EKS Hybrid Nodes 向け**: 常に**private ASN 範囲** (64512–65534) を使用してください。public ASN は不要です。ここでの BGP は Cilium node とオンプレミス router 間の internal network 内でのみ使用されます。

**ASN 値の選択方法**

* **`localASN`**（例: `65001`）: hybrid node 上で実行される Cilium に割り当てる ASN です。同じ cluster 内のすべての Cilium node は通常、1 つの ASN を共有します。
* **`peerASN`**（例: `65000`）: Cilium が peer するオンプレミス router の ASN です。この値は router の BGP 設定で確認してください。

環境で BGP がまだ設定されていない場合は、private 範囲から 2 つの異なる番号を選択します（例: router には `65000`、Cilium には `65001`）。network team がすでに内部で BGP を使用している場合は、ASN conflict を避けるために調整してください。

**オンプレミス Router BGP 設定例**

以下は、上記の Cilium 設定に一致するように BGP peering の**router 側**を設定する例です。各例で router は ASN `65000` を使用し、`10.80.1.10`（ASN `65001`）の Cilium node と peer します。

**Cisco IOS / IOS-XE**

```
router bgp 65000
 neighbor 10.80.1.10 remote-as 65001
 neighbor 10.80.1.10 description "EKS Hybrid Node - Cilium BGP"
 !
 address-family ipv4 unicast
  neighbor 10.80.1.10 activate
  neighbor 10.80.1.10 soft-reconfiguration inbound
 exit-address-family
```

**Cisco NX-OS (Nexus)**

```
router bgp 65000
  address-family ipv4 unicast
  neighbor 10.80.1.10
    remote-as 65001
    description EKS-Hybrid-Cilium
    address-family ipv4 unicast
      soft-reconfiguration inbound
```

**Juniper Junos (MX / QFX / SRX)**

```
set protocols bgp group eks-hybrid type external
set protocols bgp group eks-hybrid peer-as 65001
set protocols bgp group eks-hybrid neighbor 10.80.1.10 description "EKS Hybrid Node"
set protocols bgp group eks-hybrid family inet unicast
set routing-options autonomous-system 65000
```

**Arista EOS**

```
router bgp 65000
   neighbor 10.80.1.10 remote-as 65001
   neighbor 10.80.1.10 description EKS-Hybrid-Cilium
   !
   address-family ipv4
      neighbor 10.80.1.10 activate
```

**MikroTik RouterOS**

```
/routing bgp connection
add name=eks-hybrid remote.address=10.80.1.10 remote.as=65001 \
    local.role=ebgp as=65000 address-families=ip
```

**FRRouting (FRR) — Software Router (Linux)**

FRRouting は、Linux server および VM 上の software BGP router として一般的に使用されます。

```
router bgp 65000
 neighbor 10.80.1.10 remote-as 65001
 neighbor 10.80.1.10 description EKS-Hybrid-Cilium
 !
 address-family ipv4 unicast
  neighbor 10.80.1.10 activate
 exit-address-family
```

**AWS Transit Gateway (TGW)**

Site-to-Site VPN で AWS Transit Gateway を使用する場合、TGW 側の ASN は TGW 作成時に設定されます。

```bash
# TGW creation with custom ASN
aws ec2 create-transit-gateway \
  --options AmazonSideAsn=65000

# The VPN tunnel automatically establishes BGP with the TGW ASN
# On-premises router (or Cilium) uses its own ASN to peer with TGW
```

> **注記**: AWS TGW の default ASN は `64512` です。Cilium node が `65001` を使用する場合、Cilium 設定内の TGW（または VGW）peer ASN は TGW の ASN と一致する必要があります。

**複数の Hybrid Node**

複数の hybrid node がある場合、各 node は**同じ `localASN`**を持つ独自の Cilium BGP speaker を実行します。オンプレミス router は各 node と個別に peer します。

```
# Router config — peer with each hybrid node
router bgp 65000
 neighbor 10.80.1.10 remote-as 65001   ! hybrid-node-001
 neighbor 10.80.1.11 remote-as 65001   ! hybrid-node-002
 neighbor 10.80.1.12 remote-as 65001   ! hybrid-node-003
```

各 node は自身の pod CIDR slice（例: node-001 は `10.85.0.0/25`、node-002 は `10.85.0.128/25`）を advertise するため、router はすべての pod CIDR に対する完全な routing table を構築します。

#### BGP Peering の確認

```bash
cilium bgp peers
cilium bgp routes
```

Hybrid node には Session State `established` が表示されるはずです。

### オプション 2: Static Route

pod CIDR を使用した手動 router 設定です。最も簡単ですが、error-prone であり、node が変更されるたびに手動更新が必要です。

![Static Routes](../.gitbook/assets/hybrid-nodes-static-routes.png)

#### Cluster-Pool IPAM Allocation について

Cilium の `cluster-pool` IPAM mode では、pod CIDR pool 全体が node ごとに固定サイズの block に分割されます。2 つの主要な parameter は [04-node-bootstrap.md](04-node-bootstrap.md) の Cilium values で設定されます。

| Parameter                    | 例の値          | 説明                                           |
| ---------------------------- | -------------- | ---------------------------------------------- |
| `clusterPoolIPv4PodCIDRList` | `10.85.0.0/16` | pod CIDR pool 全体                             |
| `clusterPoolIPv4MaskSize`    | `25`           | node ごとに割り当てられる subnet size (/25 = 128 IP) |

たとえば、pool `10.85.0.0/16` と mask size `/25` では、最大 **512 node** にそれぞれ 128 個の pod IP を割り当てられます。Cilium Operator は node registration 順に block を割り当てます。

| Node            | 割り当てられた PodCIDR | 利用可能な Pod IP             |
| --------------- | ----------------- | ----------------------------- |
| hybrid-node-001 | `10.85.0.0/25`    | `10.85.0.1` – `10.85.0.126`   |
| hybrid-node-002 | `10.85.0.128/25`  | `10.85.0.129` – `10.85.0.254` |
| hybrid-node-003 | `10.85.1.0/25`    | `10.85.1.1` – `10.85.1.126`   |

> **重要**: この allocation 情報は **CiliumNode CR** に記録されます。Kubernetes Node object の `spec.podCIDR` とは異なる場合があるため、static route を設定するときは常に CiliumNode CR を参照してください。

#### Node ごとの PodCIDR のクエリ

static route を設定するには、各 node の割り当て済み PodCIDR と node IP (next hop) を特定する必要があります。query method は CNI によって異なります。

**Cilium** — `CiliumNode` CR の `spec.ipam.podCIDRs` が authoritative source です。

```bash
kubectl get ciliumnodes -o custom-columns='\
NAME:.metadata.name,\
NODE_IP:.spec.addresses[0].ip,\
POD_CIDR:.spec.ipam.podCIDRs[0]'
```

```
NAME                NODE_IP       POD_CIDR
hybrid-node-001     10.80.1.10    10.85.0.0/25
hybrid-node-002     10.80.1.11    10.85.0.128/25
hybrid-node-003     10.80.1.12    10.85.1.0/25
```

> CiliumNode CR structure、scripting usage、および詳細については、[Cilium IPAM — CiliumNode CR を使用した Node ごとの PodCIDR のクエリ](../networking/cilium/04-ipam-policy.md#querying-per-node-podcidrs-via-ciliumnode-cr) を参照してください。

**Calico** — `BlockAffinity` CR は node ごとの CIDR block を追跡します。

```bash
kubectl get blockaffinities -o custom-columns='\
NAME:.metadata.name,\
CIDR:.spec.cidr,\
NODE:.spec.node'
```

> **⚠ 非推奨**: Calico は EKS Hybrid Nodes では公式サポートされなくなりました。新しい deployment には Cilium を使用してください。詳細な BlockAffinity query については、[Calico Advanced Topics — BlockAffinity を使用した Node ごとの PodCIDR のクエリ](../networking/calico/07-advanced-topics.md#querying-per-node-podcidrs-via-blockaffinity) を参照してください。

#### Static Route の設定

CiliumNode（または Calico BlockAffinity）CR の情報に基づき、router に static route を追加します。一般的なパターンは次のとおりです。

```
Destination = Node's PodCIDR
Next Hop    = Node's InternalIP
```

**Linux (ip route)**

```bash
# Add routes for each node's pod CIDR
ip route add 10.85.0.0/25 via 10.80.1.10    # hybrid-node-001
ip route add 10.85.0.128/25 via 10.80.1.11  # hybrid-node-002
ip route add 10.85.1.0/25 via 10.80.1.12    # hybrid-node-003
```

reboot 後も永続化するには:

```bash
# /etc/network/interfaces.d/hybrid-routes (Debian/Ubuntu)
up ip route add 10.85.0.0/25 via 10.80.1.10
up ip route add 10.85.0.128/25 via 10.80.1.11
up ip route add 10.85.1.0/25 via 10.80.1.12

# Or for NetworkManager (RHEL/Rocky)
# /etc/NetworkManager/dispatcher.d/99-hybrid-routes
```

**Cisco IOS / IOS-XE**

```
ip route 10.85.0.0 255.255.255.128 10.80.1.10 name hybrid-node-001-pods
ip route 10.85.0.128 255.255.255.128 10.80.1.11 name hybrid-node-002-pods
ip route 10.85.1.0 255.255.255.128 10.80.1.12 name hybrid-node-003-pods
```

**FRRouting (FRR)**

```
ip route 10.85.0.0/25 10.80.1.10
ip route 10.85.0.128/25 10.80.1.11
ip route 10.85.1.0/25 10.80.1.12
```

**AWS VPC Route Table**

Pod が VPN/Direct Connect 経由で接続された AWS VPC から到達可能である必要がある場合は、aggregate CIDR を使用します。

```bash
# Add VPC route with aggregate CIDR (VPN Gateway or TGW as next hop)
aws ec2 create-route \
  --route-table-id rtb-0123456789abcdef0 \
  --destination-cidr-block 10.85.0.0/16 \
  --gateway-id vgw-0123456789abcdef0
```

```hcl
# Terraform
resource "aws_route" "hybrid_pod_cidr" {
  route_table_id         = aws_route_table.main.id
  destination_cidr_block = "10.85.0.0/16"
  gateway_id             = aws_vpn_gateway.main.id
}
```

#### 自動化と BGP の比較

CiliumNode CR から `ip route` コマンドを自動生成する script の例:

```bash
#!/bin/bash
# generate-static-routes.sh — Generate static route commands from CiliumNode CRs
kubectl get ciliumnodes -o json | jq -r \
  '.items[] | "ip route add \(.spec.ipam.podCIDRs[0]) via \(.spec.addresses[0].ip)"'
```

出力例:

```
ip route add 10.85.0.0/25 via 10.80.1.10
ip route add 10.85.0.128/25 via 10.80.1.11
ip route add 10.85.1.0/25 via 10.80.1.12
```

**Static Route と BGP の比較**

| 観点                     | Static Route                                | BGP（オプション 1）                    |
| ------------------------ | ------------------------------------------ | ----------------------------------- |
| Node の追加              | router に手動で route を追加する必要あり  | route は自動的に伝播される          |
| Node の削除              | router から手動で route を削除する必要あり | route は自動的に撤回される          |
| Node IP の変更           | すべての route を手動で更新する必要あり    | update は自動的に伝播される         |
| 障害検出                 | なし（stale route が残る）                  | BGP keepalive により自動検出        |
| 設定の複雑さ             | 低                                         | 中（BGP peering の設定が必要）      |
| Scalability              | 1～5 node に適している                     | 数十～数百 node に scale            |

> **推奨**:
>
> * **PoC / 小規模環境**（1～5 node）: Static Route はすぐに開始できます
> * **Production / 5+ node**: [BGP（オプション 1）](02-network-configuration.md#option-1-bgp-recommended) を使用してください。node の変更に自動的に対応し、運用 overhead を大幅に削減します
> * **ポリシーにより BGP が許可されていない環境**: 上記の automation script を使用して Static Route を管理します

### オプション 3: ARP Proxying

Node は host する pod IP の ARP request に応答します。local router への Layer 2 network proximity が必要です。Cilium には built-in proxy ARP support があります。router の BGP または static route 設定は不要ですが、pod CIDR が他の network と重複してはなりません。

![ARP Proxying](../.gitbook/assets/hybrid-nodes-arp-proxy.png)

***

## Network Policy

Network policy を使用して、hybrid node 環境の Pod 間 traffic を制御できます。Cilium CNI を使用する場合、標準の Kubernetes NetworkPolicy と拡張された CiliumNetworkPolicy の両方がサポートされます。

### Kubernetes NetworkPolicy

標準の Kubernetes NetworkPolicy は基本的な L3/L4 traffic filtering を提供します。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: bookinfo
spec:
  podSelector:
    matchLabels:
      app: reviews
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: productpage
    ports:
    - protocol: TCP
      port: 9080
```

この policy は、`bookinfo` namespace 内で `app: productpage` label を持つ Pod のみが、`app: reviews` Pod の port 9080 にアクセスすることを許可します。

### CiliumNetworkPolicy

CiliumNetworkPolicy は Kubernetes NetworkPolicy を拡張し、L7 filtering、DNS-aware policy、identity-based matching を提供します。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: bookinfo
spec:
  endpointSelector:
    matchLabels:
      app: reviews
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: productpage
    toPorts:
    - ports:
      - port: "9080"
        protocol: TCP
```

#### CiliumNetworkPolicy の高度な機能

**L7 HTTP Filtering**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: l7-rule
  namespace: bookinfo
spec:
  endpointSelector:
    matchLabels:
      app: reviews
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: productpage
    toPorts:
    - ports:
      - port: "9080"
        protocol: TCP
      rules:
        http:
        - method: "GET"
          path: "/api/v1/.*"
```

**DNS ベースの Egress Policy**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-external-api
  namespace: bookinfo
spec:
  endpointSelector:
    matchLabels:
      app: productpage
  egress:
  - toFQDNs:
    - matchName: "api.example.com"
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP
```

### Hybrid Environment における Network Policy の考慮事項

| 考慮事項                   | 説明                                                                                                                               |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| **デフォルトの動作**       | network policy がない場合、すべての traffic が許可されます。NetworkPolicy を適用すると、明示的に許可された traffic のみが通過します。 |
| **境界をまたぐ traffic**   | policy では cloud node 上の Pod と hybrid node 上の Pod 間の通信を考慮する必要があります。                                        |
| **CNI 要件**               | Cilium が CNI として設定されている場合、両方の policy type が機能します。                                                         |
| **Policy Scope**           | CiliumNetworkPolicy はその namespace にのみ適用されます。cluster-wide policy には CiliumClusterwideNetworkPolicy を使用します。 |

> **推奨**: hybrid environment では、意図しない境界をまたぐ traffic を防止するため、明示的な network policy を定義してください。sensitive workload は厳格な Ingress/Egress policy で保護する必要があります。

***

## Webhook 設定

Webhook は、mutating および validation capability のために Kubernetes application や open source project（AWS Load Balancer Controller、CloudWatch Observability Agent）で使用されます。

### ルーティング可能な Pod Network の場合

オンプレミス pod CIDR が（BGP、static route、または ARP proxy 経由で）ルーティング可能な場合、webhook は hybrid node 上で実行できます。

### ルーティング不可能な Pod Network の場合

オンプレミス pod CIDR がルーティング**不可能**な場合、node affinity を使用して**すべての webhook を cloud node 上で実行します**。

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: eks.amazonaws.com/compute-type
          operator: NotIn
          values:
          - hybrid
```

### Webhook を使用する Add-on

次の add-on では webhook の配置を考慮する必要があります。

| Add-on                         | Webhook の配置（ルーティング不可能な Pod CIDR） |
| ------------------------------ | --------------------------------------- |
| AWS Load Balancer Controller   | cloud node のみ                         |
| CloudWatch Observability Agent | cloud node のみ                         |
| ADOT (OpenTelemetry)           | cloud node のみ                         |
| cert-manager                   | cloud node のみ                         |
| Kubernetes Metrics Server      | ルーティング可能な pod CIDR が必要      |

***

< [前へ: 前提条件](01-prerequisites.md) | [目次](./README.md) | [次へ: エアギャップ設定](03-airgap-setup.md) >
