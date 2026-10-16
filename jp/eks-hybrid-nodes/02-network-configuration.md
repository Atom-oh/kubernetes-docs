# ネットワーク設定

> **サポート対象バージョン**: EKS 1.36 の例。AWS が管理する Cilium 1.18.3-0 を参照バージョンとし、互換性のあるホスト/カーネルが必要です
> **最終更新**: September 16, 2026

ルーティング、DNS、TLS、認証情報、アプリケーショントラフィックはそれぞれ個別に検証してください。これらの例は、モック化した Terraform provider を含むローカルのスキーマとフィクスチャで確認したものであり、AWS リソース、ルーター、ファイアウォール、稼働中の cluster は一切変更していません。図は AWS の概念に基づくこのリポジトリ独自の説明図であり、この構成に対する AWS 公式の検証結果ではありません。

![Hybrid prerequisites and bidirectional routing.](../.gitbook/assets/en-eks-hybrid-nodes-prereq-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-prereq-0.html)

**セキュリティチーム向けの補足資料:** [Hybrid Nodes のネットワーク分離レビュー](11-network-separation-security.md)では、control plane からオンプレミスへの新たな接続、endpoint の種類、権限とデータの境界、レビュー用の証跡について説明しています。プライベート接続だけではコンプライアンスは満たされません。

## ネットワークアーキテクチャの概要

control plane から hybrid node へのトラフィックと、プライベートな Kubernetes API トラフィックは cluster VPC のネットワーク経路を使用します。パブリック API endpoint に対する kubelet のトラフィックは、代わりに設定されたパブリック経路を使用します。「すべてのトラフィックは常に VPC の ENI を通過する」という説明は的が広すぎました。Direct Connect の public VIF、プライベート接続、パブリックインターネット経路はそれぞれ別個の選択肢です。

EKS control plane の ENI/IP は変わる可能性があります。共有 VPC 内のすべての `Amazon EKS*` ENI をこの cluster のものとみなすのではなく、実際の cluster の所有関係と承認済みの control plane subnet 範囲を確認してください。

読み取り専用の診断を行う前に、アカウントと Kubernetes context を固定します。

```bash
set -euo pipefail
: "${EXPECTED_ACCOUNT_ID:?Set the intended account}"
: "${AWS_REGION:?Set the cluster Region}"
: "${CLUSTER_NAME:?Set the reviewed cluster name}"
: "${KUBECONFIG:?Set the reviewed kubeconfig}"
export KUBECONFIG KUBE_CONTEXT="${KUBE_CONTEXT:-$CLUSTER_NAME}"
check_account() {
  local account
  account=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text) || return
  test "$account" = "$EXPECTED_ACCOUNT_ID" || { printf 'Account mismatch.\n' >&2; return 1; }
}
check_account
umask 077
export WORK_DIR
WORK_DIR=$(mktemp -d "$PWD/hybrid-network.XXXXXXXX")
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" --output json \
  > "$WORK_DIR/cluster.json"
endpoint=$(kubectl --context "$KUBE_CONTEXT" config view --minify \
  -o jsonpath='{.clusters[0].cluster.server}')
jq -e --arg endpoint "$endpoint" '
  .cluster.status=="ACTIVE" and .cluster.endpoint==$endpoint and
  (.cluster.remoteNetworkConfig.remoteNodeNetworks|length)>0
' "$WORK_DIR/cluster.json" >/dev/null
printf 'Private diagnostics: %s\n' "$WORK_DIR"
```

## CIDR 範囲の要件

リモートの node/Pod ネットワークには、VPC および Kubernetes Service CIDR とは別の、重複しない IPv4 の **RFC1918 または CGNAT** アドレスを使用します。各リモート種別ごとに最大 15 個の CIDR がサポートされます。現行の EKS では、API ワークフローを通じて既存 cluster に対するリモートネットワーク設定が可能です。作成時のみの設定ではありません。

| ネットワークの挙動 | 意味 |
|------------------|---------|
| ルーティング可能な Pod IP | 承認済みのルートにより、クラウド/control plane 側のクライアントが Pod IP への接続を開始できます |
| マスカレードされた egress | SNAT は Pod 側から開始した接続の戻り経路を提供できますが、新しい inbound 接続を自動的に許可するものではありません |
| ルーティング不可能な Pod ネットワーク | クラウドから Pod への直接トラフィックには別のサポート経路が必要です。一般的な設計ではクラウドホスト型の webhook/API service を使用してください |

ルーティング不可能であることは、Pod が AWS API 呼び出しを一切開始できないという意味ではありません。hybrid/クラウド間の Pod 直接通信や hybrid でホストする webhook を使う場合は、実際の Pod ルートを用意してください。Gateway/proxy を使う代替案には別の要件があります。

## 必要なファイアウォールポート

| フロー | プロトコル / ポート |
|------|-----------------|
| Node/Pod → Kubernetes API | 実際の cluster endpoint への TCP443 |
| control plane の ENI → kubelet | kubelet の認証/認可を伴う TCP10250 |
| control plane → webhook または集約 API の Pod | 汎用的な「8443+」の範囲ではなく、設定された TCP ポート |
| DNS クライアント ↔ 実際のリゾルバー | UDP/TCP53 とステートフルな戻りトラフィック |
| 参加ノード間の Cilium VXLAN | UDP8472 |
| Cilium Geneve（設計上選択され、かつサポートされる場合のみ） | UDP6081 |
| Cilium のヘルスチェック | TCP4240 と、必要な ICMP/health endpoint への到達性 |
| BGP node ↔ ルーター | 設定された active/passive ピアに対する TCP179 |
| VPN gateway のトランスポート | UDP500/4500 と該当する IPsec トランスポート要件 |
| アプリケーション / AWS 認証情報およびレジストリサービス | 実際の宛先とポートのみ |

ファイアウォールの変更は、コネクショントラッキングと既存ルールを保持したまま、ネットワーク所有者を通じて適用してください。従来の広範な `10.0.0.0/8` INPUT ルール、範囲を絞らない DNS/VXLAN の許可、ルールセット全体の保存は、安全に再利用できるファイアウォールポリシーではありませんでした。認証なしの kubelet 10255 を、最近の任意要件として開放してはいけません。

## AWS endpoint へのアクセス

**EKS 管理 API の PrivateLink endpoint は、Kubernetes API server の endpoint ではありません。**

| `com.amazonaws.<region>.*` のサービスサフィックス | 用途 / 必要になる場面 |
|------------------------------------------------|-----------------------|
| `eks` | DescribeCluster などの AWS EKS 管理 API 呼び出し |
| `eks-auth` | EKS Pod Identity を使用する場合 |
| `ecr.api`, `ecr.dkr` | プライベートな ECR API/レジストリ。イメージレイヤーには S3 へのアクセスも必要です |
| `s3` | プライベートな S3 アクセス。オンプレミスからは VPC gateway endpoint を直接利用できません |
| `ssm`, 該当する SSM メッセージング系サービス | SSM の認証情報/管理機能 |
| `rolesanywhere` | IAM Roles Anywhere をプロバイダーとして使用する場合の認証情報 |
| `sts` | 実際のクライアントによる STS/IRSA/AssumeRole 呼び出し。ローカルでの EKS トークン署名自体はクライアントの STS ネットワークリクエストではありません |
| `logs`, `monitoring`, その他選択したサービス | 選択したエージェント/ワークロードがそれらを呼び出す場合のみ |
| `oidc-eks` | 現行の EKS OIDC discovery/JWKS 用 PrivateLink サービス（利用可能なリージョンで） |
| `eks-proxy` | AWS コンソールのリソース表示用。公開されたアプリケーション向け SDK/API ではありません |

対象リージョンでサービスが利用可能かを確認してください。プライベートな ECR endpoint によって、**public ECR**、CloudFront、任意のパッケージリポジトリがプライベートになるわけではありません。たとえば public ECR にある AWS の Cilium OCI チャートには、承認済みで到達可能な配布経路またはミラーが必要です。

OIDC discovery/JWKS は匿名で公開される公開鍵情報です。`oidc-eks` はデフォルトのフルアクセス endpoint policy のみを受け付けます。到達性は SG/ルーティングで制御し、role の認可は IAM 信頼ポリシーの `aud`/`sub` 条件で制御してください。STS は IRSA トークンを AWS 内部で検証するため、この VPC endpoint とは無関係です。

Roles Anywhere の CreateSession 向け endpoint policy では、評価が証明書認証より先に行われるため、principal は `*` にする必要があります。ドキュメントに従い、承認済みの trust anchor リソースとサポートされる証明書の条件で制限してください。これら異なるサービス間で、汎用的な endpoint policy を1つ流用してはいけません。endpoint policy は endpoint のトラフィックをフィルタリングするものであり、IAM/role の信頼関係を置き換えるものでも、パブリックなサービス endpoint を全体的に無効化するものでもありません。

```bash
check_account
vpc_id=$(jq -er '.cluster.resourcesVpcConfig.vpcId' "$WORK_DIR/cluster.json")
aws ec2 describe-vpc-endpoints --region "$AWS_REGION" \
  --filters "Name=vpc-id,Values=$vpc_id" --output json |
  jq '[.VpcEndpoints[]|{id:.VpcEndpointId,service:.ServiceName,type:.VpcEndpointType,
      state:.State,privateDNS:.PrivateDnsEnabled,dnsOptions:.DnsOptions,
      subnets:.SubnetIds,groups:.Groups,dnsEntries:.DnsEntries}]'
```

### S3 のプライベート DNS とアーティファクト配布

S3 の **interface endpoint はプライベート DNS をサポートします**。inbound Resolver 限定のオプションを使うと、オンプレミスからのクエリは interface endpoint 経由になり、VPC 内のトラフィックは必須の S3 gateway endpoint を使用します。このオプションを有効にしている間は gateway endpoint を維持してください。あるいはオプションを解除して、対象となるすべての S3 トラフィックに interface endpoint を使用することもできます。

プライベート DNS は TLS の書き換えではありません。`hybrid-assets.eks.amazonaws.com` を S3 endpoint にマッピングする PHZ/CNAME を作っても、S3 が CloudFront ホスト名の証明書やオブジェクト/Host のルーティング動作を得るわけではありません。そのようなミラーを動かすために TLS 検証を無効化してはいけません。サポートされているアーティファクト準備/クライアント設定の経路、独自のホスト名と証明書を持つ承認済みミラー、または検証済みイメージへの依存関係のプリインストールを使用してください。

## VPC プライベート endpoint（インターネット制限環境での接続） {#vpc-private-endpoints-air-gap-private-connectivity}

ここでの「エアギャップ」とは、インターネットアクセスを制限しつつ必要な AWS 接続は確保した状態を意味し、完全に切り離された cluster ではありません。

以下の完全な Terraform の例は、既存の VPC、endpoint 用 subnet、TGW を使用します。VPN/DX の回線、TGW アタッチメント、オンプレミス側のルート、EKS のプライベート DNS 設定は作成しません。VPC の DNS サポート/ホスト名の有効化と、実際に異なる AZ であることを確認してください。subnet ID が2つ異なるだけでは AZ 分散の証明にはなりません。

置き換えを計画する前に、元のインフラストラクチャ所有者を通じて既存リソースを import/引き継いでください。デフォルトの endpoint セットは SSM を例示したものです。選択したプロバイダー/ワークロードに合わせて変更してください。endpoint と Resolver の ENI には課金が発生します。provider のアカウントガードと範囲を絞った ingress は意図的なものです。応答トラフィックは SG のステートフルな追跡を利用します。

```hcl
terraform {
  required_version = ">= 1.9, < 2.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.64.0"
    }
  }
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.expected_account_id]
}

variable "expected_account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.expected_account_id))
    error_message = "Set the reviewed 12-digit account ID."
  }
}

variable "region" {
  type = string
}

variable "name_prefix" {
  type    = string
  default = "hybrid-network"
}

variable "vpc_id" {
  type = string
}

variable "endpoint_subnet_ids" {
  type = set(string)
  validation {
    condition     = length(var.endpoint_subnet_ids) >= 2
    error_message = "Provide subnets in at least two verified Availability Zones."
  }
}

variable "s3_gateway_route_table_ids" {
  type = set(string)
  validation {
    condition     = length(var.s3_gateway_route_table_ids) > 0
    error_message = "Provide the reviewed VPC route tables for the S3 gateway endpoint."
  }
}

variable "client_ipv4_cidrs" {
  type = set(string)
  validation {
    condition = length(var.client_ipv4_cidrs) > 0 && alltrue([
      for c in var.client_ipv4_cidrs : can(cidrnetmask(c)) && c != "0.0.0.0/0"
    ])
    error_message = "Provide scoped IPv4 CIDRs for the actual VPC/on-premises clients."
  }
}

variable "onprem_dns_client_cidrs" {
  type = set(string)
  validation {
    condition = length(var.onprem_dns_client_cidrs) > 0 && alltrue([
      for c in var.onprem_dns_client_cidrs : can(cidrnetmask(c)) && c != "0.0.0.0/0"
    ])
    error_message = "Scope inbound DNS to the actual on-premises resolvers."
  }
}

variable "onprem_dns_servers" {
  type = set(string)
  validation {
    condition = length(var.onprem_dns_servers) > 0 && alltrue([
      for ip in var.onprem_dns_servers : can(cidrnetmask("${ip}/32"))
    ])
    error_message = "Provide actual IPv4 addresses of the on-premises DNS servers."
  }
}

variable "onprem_domain" {
  type    = string
  default = "corp.example.internal"
  validation {
    condition = length(var.onprem_domain) <= 253 && length(split(".", trimsuffix(var.onprem_domain, "."))) >= 2 && alltrue([
      for label in split(".", trimsuffix(var.onprem_domain, ".")) :
      length(label) <= 63 && can(regex("^[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?$", label))
    ]) && !can(regex("(^|\\.)(amazonaws\\.com|api\\.aws|cluster\\.local)\\.?$", lower(var.onprem_domain)))
    error_message = "Use a specific owned DNS suffix; do not forward root, AWS or Kubernetes service zones back to on-premises."
  }
}

variable "interface_services" {
  type    = set(string)
  default = ["eks", "ecr.api", "ecr.dkr", "ssm", "ssmmessages"]
  validation {
    condition     = !contains(var.interface_services, "s3")
    error_message = "S3 has its own gateway/interface configuration below."
  }
}

variable "endpoint_policy_json" {
  type    = map(string)
  default = {}
  validation {
    condition = !contains(keys(var.endpoint_policy_json), "oidc-eks") && alltrue([
      for policy in values(var.endpoint_policy_json) : can(jsondecode(policy))
    ])
    error_message = "Use valid service-specific JSON policies; oidc-eks supports only its default full-access policy."
  }
}

variable "controlplane_route_table_ids" {
  type = set(string)
}

variable "remote_ipv4_cidrs" {
  type = set(string)
  validation {
    condition = alltrue([
      for c in var.remote_ipv4_cidrs : can(cidrnetmask(c)) && c != "0.0.0.0/0"
    ])
    error_message = "Use reviewed remote node, Pod and required DNS/service IPv4 CIDRs."
  }
}

variable "existing_transit_gateway_id" {
  type = string
}
```
```hcl
# Import/adopt existing resources through their owner before using this example.
# The existing VPC must have DNS support/hostnames and working hybrid routes.
resource "aws_security_group" "endpoints" {
  name_prefix = "${var.name_prefix}-vpce-"
  description = "HTTPS clients for interface endpoints"
  vpc_id      = var.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "endpoint_https" {
  for_each          = var.client_ipv4_cidrs
  security_group_id = aws_security_group.endpoints.id
  cidr_ipv4         = each.value
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_vpc_endpoint" "service" {
  for_each            = var.interface_services
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.region}.${each.value}"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = var.endpoint_subnet_ids
  security_group_ids  = [aws_security_group.endpoints.id]
  policy              = lookup(var.endpoint_policy_json, each.key, null)
  tags                = { Name = "${var.name_prefix}-${each.key}" }
}

# S3 inbound-Resolver-only private DNS requires this gateway endpoint.
resource "aws_vpc_endpoint" "s3_gateway" {
  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = var.s3_gateway_route_table_ids
  tags             = { Name = "${var.name_prefix}-s3-gateway" }
}

resource "aws_vpc_endpoint" "s3_interface" {
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = var.endpoint_subnet_ids
  security_group_ids  = [aws_security_group.endpoints.id]
  dns_options {
    private_dns_only_for_inbound_resolver_endpoint = true
  }
  depends_on = [aws_vpc_endpoint.s3_gateway]
  tags       = { Name = "${var.name_prefix}-s3-interface" }
}

resource "aws_security_group" "dns_inbound" {
  name_prefix = "${var.name_prefix}-dns-in-"
  description = "DNS from on-premises resolvers"
  vpc_id      = var.vpc_id
}

resource "aws_security_group" "dns_outbound" {
  name_prefix = "${var.name_prefix}-dns-out-"
  description = "DNS to reviewed on-premises resolvers"
  vpc_id      = var.vpc_id
}

locals {
  inbound_dns_rules = {
    for pair in setproduct(var.onprem_dns_client_cidrs, toset(["tcp", "udp"])) :
    "${pair[0]}-${pair[1]}" => { cidr = pair[0], protocol = pair[1] }
  }
  outbound_dns_rules = {
    for pair in setproduct(var.onprem_dns_servers, toset(["tcp", "udp"])) :
    "${pair[0]}-${pair[1]}" => { ip = pair[0], protocol = pair[1] }
  }
}

resource "aws_vpc_security_group_ingress_rule" "dns" {
  for_each          = local.inbound_dns_rules
  security_group_id = aws_security_group.dns_inbound.id
  cidr_ipv4         = each.value.cidr
  ip_protocol       = each.value.protocol
  from_port         = 53
  to_port           = 53
}

resource "aws_vpc_security_group_egress_rule" "dns" {
  for_each          = local.outbound_dns_rules
  security_group_id = aws_security_group.dns_outbound.id
  cidr_ipv4         = "${each.value.ip}/32"
  ip_protocol       = each.value.protocol
  from_port         = 53
  to_port           = 53
}

resource "aws_route53_resolver_endpoint" "inbound" {
  name                   = "${var.name_prefix}-inbound"
  direction              = "INBOUND"
  resolver_endpoint_type = "IPV4"
  security_group_ids     = [aws_security_group.dns_inbound.id]
  dynamic "ip_address" {
    for_each = var.endpoint_subnet_ids
    content {
      subnet_id = ip_address.value
    }
  }
}

resource "aws_route53_resolver_endpoint" "outbound" {
  name                   = "${var.name_prefix}-outbound"
  direction              = "OUTBOUND"
  resolver_endpoint_type = "IPV4"
  security_group_ids     = [aws_security_group.dns_outbound.id]
  dynamic "ip_address" {
    for_each = var.endpoint_subnet_ids
    content {
      subnet_id = ip_address.value
    }
  }
}

resource "aws_route53_resolver_rule" "onprem" {
  domain_name          = var.onprem_domain
  name                 = "${var.name_prefix}-onprem"
  rule_type            = "FORWARD"
  resolver_endpoint_id = aws_route53_resolver_endpoint.outbound.id
  dynamic "target_ip" {
    for_each = var.onprem_dns_servers
    content {
      ip   = target_ip.value
      port = 53
    }
  }
}

resource "aws_route53_resolver_rule_association" "onprem" {
  resolver_rule_id = aws_route53_resolver_rule.onprem.id
  vpc_id           = var.vpc_id
}

output "inbound_resolver_ips" {
  value = [for address in aws_route53_resolver_endpoint.inbound.ip_address : address.ip]
}

# VPC return routes only. Existing TGW attachment routes/propagation and
# on-premises routing must be managed separately by their infrastructure owner.
locals {
  remote_routes = {
    for pair in setproduct(var.controlplane_route_table_ids, var.remote_ipv4_cidrs) :
    "${pair[0]}-${pair[1]}" => { table = pair[0], cidr = pair[1] }
  }
}

resource "aws_route" "hybrid" {
  for_each               = local.remote_routes
  route_table_id         = each.value.table
  destination_cidr_block = each.value.cidr
  transit_gateway_id     = var.existing_transit_gateway_id
  # A VGW topology uses gateway_id instead; do not set both target fields.
}
```

S3 gateway への依存関係は明示的に指定しています。`remote_ipv4_cidrs` には node/Pod ネットワークだけでなく、必要なオンプレミスの DNS/service 範囲も含めてください。例に挙げた DNS サーバー `192.168.1.10/11` には、承認済みの `192.168.1.0/24` ルートまたは対応するホストルートが必要です。VGW の戻りルートには `transit_gateway_id` ではなく `gateway_id` を使用してください。TGW の ID を VGW/gateway のフィールドに設定したり、両方のターゲットを同時に設定してはいけません。VPC のルートだけでは TGW/VPN/オンプレミスのルーティングは成立しません。

## DNS 設定

オンプレミスのリゾルバーは、選択した AWS/サービス名や実際の cluster endpoint 名を Route 53 Resolver の inbound IP に条件付きで転送できます。実際の endpoint に対して返されたアドレスを使用してください。`amazonaws.com` を広く転送すると無関係なサービスにも影響し得るため、ゾーンは意図的に選択し、転送ループを避けてください。

```text
// Example service zones only. Replace these Resolver IPs with actual outputs.
zone "eks.ap-northeast-2.amazonaws.com" {
    type forward;
    forward only;
    forwarders { 10.0.1.10; 10.0.2.10; };
};
zone "s3.ap-northeast-2.amazonaws.com" {
    type forward;
    forward only;
    forwarders { 10.0.1.10; 10.0.2.10; };
};
```

この BIND のフラグメントが対象とするのは記載したサービスゾーンのみで、Kubernetes API のホスト名を自動的に含むわけではありません。検証済みのサービス一覧から、実際の cluster endpoint の DNS 名/サフィックスとその他の必要な名前を追加してください。オンプレミスのゾーンは Resolver の outbound ルールで処理します。そのゾーンは選択した DNS サーバー上で権威があり到達可能である必要があり、同じループへ転送し返してはいけません。

### CoreDNS のカスタムドメイン設定

選択した設計で CoreDNS から直接転送する場合は、レビュー済みの server ブロックを既存の Corefile にマージしてください。管理対象の ConfigMap 全体を上書きしてはいけません。

```text
# Fragment to merge through the CoreDNS configuration owner.
corp.example.internal:53 {
    errors
    cache 30
    forward . 192.168.1.10 192.168.1.11 {
        max_concurrent 1000
    }
}
```

既存の Kubernetes ゾーン、health/readiness、reload の動作は維持してください。実際の resolver ファイルと systemd-resolved/stub の構成を確認してください。DNS サーバーを自分自身へ転送するとループする可能性があります。あるゾーンについては、適切な VPC 転送経路か明示的な CoreDNS 転送のいずれかを選び、矛盾する経路を重ねないようにしてください。

EKS のマネージド add-on では、**インストール済みバージョンの**設定スキーマを取得し、無関係な既存設定を保持したまま、提案する値の全体を検証してください。

```bash
check_account
aws eks describe-addon --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --addon-name coredns --output json > "$WORK_DIR/coredns-addon.json"
addon_version=$(jq -er '.addon.addonVersion' "$WORK_DIR/coredns-addon.json")
aws eks describe-addon-configuration --region "$AWS_REGION" --addon-name coredns \
  --addon-version "$addon_version" --output json > "$WORK_DIR/coredns-schema-response.json"
jq -r '.configurationSchema' "$WORK_DIR/coredns-schema-response.json" \
  > "$WORK_DIR/coredns-schema.json"
# Prepare the full intended values, preserving unrelated existing configuration.
: "${COREDNS_CANDIDATE_JSON:?Set the reviewed full configurationValues JSON file}"
export COREDNS_CANDIDATE_JSON
python3 - <<'PY'
import json, os
from pathlib import Path
import jsonschema
folder = Path(os.environ["WORK_DIR"])
schema = json.loads((folder / "coredns-schema.json").read_text())
candidate = json.loads(Path(os.environ["COREDNS_CANDIDATE_JSON"]).read_text())
validator = jsonschema.validators.validator_for(schema)
validator.check_schema(schema)
validator(schema).validate(candidate)
print("Configuration matches the fetched schema; rollout and DNS behavior are not yet verified")
PY
```

これはローカルでのスキーマ検証であり、ロールアウトではありません。設定を適用する前に、マネージド add-on/GitOps の管理主体、オートスケーリング、復旧手順について調整してください。

### CoreDNS の配置とローカリティ

AWS は、混在 cluster においてクラウドノードに少なくとも1つ、hybrid node に少なくとも1つの CoreDNS replica を配置することを推奨しています。ロケーションごとに2つという構成は可用性のための選択肢になり得ますが、replica 4つは普遍的な最小値でも保証でもありません。

DNS を担わせるすべてのノードで、実際のゾーンラベルを確認してください。hybrid node には `onprem-dc1` のような、所有者が定義した `topology.kubernetes.io/zone` の値が必要です。compute-type のラベルは自動的にそのゾーンや taint になるわけではありません。無関係な affinity/tolerations を削除せずに、配置の設定をマージしてください。

```json
{
  "affinity": {
    "podAntiAffinity": {
      "preferredDuringSchedulingIgnoredDuringExecution": [
        {
          "weight": 100,
          "podAffinityTerm": {
            "labelSelector": {
              "matchLabels": {
                "k8s-app": "kube-dns"
              }
            },
            "topologyKey": "kubernetes.io/hostname"
          }
        },
        {
          "weight": 50,
          "podAffinityTerm": {
            "labelSelector": {
              "matchLabels": {
                "k8s-app": "kube-dns"
              }
            },
            "topologyKey": "topology.kubernetes.io/zone"
          }
        }
      ]
    }
  }
}
```

ソフトな affinity/spread は優先設定にすぎず、2+2 の分散や bootstrap の成功を保証するものではありません。また、配置だけではクライアントがローカルの DNS replica を選ぶとも限りません。

AWS がドキュメント化している Service Traffic Distribution の例では `PreferClose` を使用します。Cilium では、サポートされている `loadBalancer.serviceTopology` の設定を行い、所有者を通じて対象エージェントをロールアウトしてから、この機能に依存してください。実際のデータプレーン/バージョンと、正常なローカル endpoint を確認してください。

```json
{
  "spec": {
    "trafficDistribution": "PreferClose"
  }
}
```
```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n kube-system \
  get service kube-dns -o json |
  jq '{name:.metadata.name,uid:.metadata.uid,clusterIP:.spec.clusterIP,
       clusterIPs:.spec.clusterIPs,ports:.spec.ports,trafficDistribution:.spec.trafficDistribution}'
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n kube-system \
  get endpointslices -l kubernetes.io/service-name=kube-dns -o json |
  jq '[.items[]|{name:.metadata.name,addressType,ports,
       endpoints:[.endpoints[]?|{addresses,nodeName,zone,conditions,hints}]}]'
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n kube-system \
  get pods -l k8s-app=kube-dns -o json |
  jq '[.items[]|{name:.metadata.name,node:.spec.nodeName,phase:.status.phase,
       ready:([.status.conditions[]?|select(.type=="Ready")|.status]|first // "NotReported")}]'
```

実際の Service IP、EndpointSlice のゾーン/hints、Pod の readiness を確認してください。`10.100.0.10` は特定の Service CIDR における例であり、普遍的な cluster DNS アドレスではありません。ローカルの replica があっても、切断された EKS cluster が完全に独立した DNS/control plane になるわけではありません。

## トラフィックフローのパターン

図では説明用のアドレスと簡略化した処理段階を使用しています。実際の Service データプレーンが kube-proxy の iptables なのか、nftables/IPVS なのか、Cilium の eBPF 置き換えなのかを確認してください。

### パターン 1: Kubelet → EKS control plane

kubelet は設定された Kubernetes API endpoint を解決して接続します。プライベートアクセスとパブリックアクセスでは経路が異なり、いずれも EKS 管理用の PrivateLink endpoint と混同してはいけません。

![Kubelet API access paths for public and private endpoint configurations.](../.gitbook/assets/en-eks-hybrid-nodes-02-network-configuration-10.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-02-network-configuration-10.html)

### パターン 2: EKS control plane → Kubelet

control plane は、報告されたルーティング可能なノードアドレスへ TCP10250 で接続します。この経路は logs、exec、port-forward を支えるもので、逆方向のルーティング、ファイアウォールの許可、kubelet の認証が必要です。

![Control-plane connection to the routable kubelet address over TCP10250.](../.gitbook/assets/en-eks-hybrid-nodes-02-network-configuration-11.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-02-network-configuration-11.html)

### パターン 3: Pod → EKS control plane

Kubernetes Service IP を使用する Pod では、選択した API endpoint への Service 変換が必要です。egress の SNAT が適用される場合、応答はノードのアドレス宛てになり、コネクショントラッキングが変換を戻します。SNAT がない場合は、Pod のアドレスに対する戻りルートが必要です。

![Logical Service translation and optional SNAT effects; the pictured order is not a universal hook sequence.](../.gitbook/assets/en-eks-hybrid-nodes-02-network-configuration-12.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-02-network-configuration-12.html)

図にある SNAT が DNAT より先という番号付けは、普遍的な hook の順序ではありません。iptables の経路では通常、Service の DNAT がルーティングと該当する POSTROUTING の SNAT より先に行われます。eBPF の経路では異なります。結論を出す前に、実際のパケット/接続の状態をキャプチャしてください。

### パターン 4: EKS control plane → Pod（webhook）

API server が、選択した webhook Pod の IP/ポートに到達できる必要があります。設定されたポートを使用してください。従来の「8443+」という凡例は有効なポート範囲要件ではありません。

![Control-plane path to a webhook Pod; use its actual configured TCP port and dataplane.](../.gitbook/assets/en-eks-hybrid-nodes-02-network-configuration-13.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-02-network-configuration-13.html)

### パターン 5: hybrid node 上の Pod ↔ Pod

サポートされている VXLAN overlay では、宛先ノードへの到達に**外側のノード IP** を使用します。カプセル化されたパケットを運ぶだけであれば、underlay に内側の宛先 Pod CIDR へのルートは不要です。

![VXLAN Pod communication. Outer forwarding uses node IPs; the older Pod-CIDR forwarding labels need correction.](../.gitbook/assets/en-eks-hybrid-nodes-02-network-configuration-14.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-02-network-configuration-14.html)

図中、カプセル化後に `10.85.x.0/24` を使う転送のラベルは、古い簡略表現として読む必要があります。外側のパケットは `10.80.0.x` へルーティングされます。同一の L2 セグメント上のノードは、ルーターを経由せずに直接通信できる場合があります。

VXLAN は内側の Ethernet フレームを UDP でカプセル化します。IPv4 で追加のカプセル化がない例では、50 バイトのオーバーヘッドにより MTU を 1500→1450 に調整する説明が成り立ちます。追加のトンネリングがあるとこの計算は変わります。Cilium の VXLAN は UDP8472 を使用し、標準的な VXLAN では一般に 4789 が使われます。Geneve は UDP6081 を使用します。現行の Cilium のトンネル設定は VXLAN/Geneve を区別します。IP-in-IP は、古い `--tunnel` の助言で選択されるような相互に置き換え可能なデフォルト overlay ではありません。

VNI フィールドは 24 ビットで、Cilium はカプセル化のメタデータにセキュリティ identity を載せることができます。これは暗号によるテナント分離ではありません。ネットワークポリシーと実際の identity 伝搬は別のものとして扱ってください。

### パターン 6: クラウドの Pod ↔ hybrid の Pod

Pod IP 間の直接トラフィックには、VPC、WAN、オンプレミスにわたる該当 Pod のルートが必要です。Service 変換が必要になるのは、リクエストが実際に Service の VIP を宛先としている場合だけです。

![Direct cloud-to-hybrid Pod routing; kube-proxy Service translation is not required for a direct Pod-IP destination.](../.gitbook/assets/en-eks-hybrid-nodes-02-network-configuration-15.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-02-network-configuration-15.html)

図中の kube-proxy/iptables のブロックはデータプレーンに依存します。Pod IP 宛ての直接パケットが本質的に kube-proxy の DNAT を必要とするわけではありません。

### kube-proxy と kubelet の詳細

kube-proxy の **iptables モード**では、一般的なチェーンの経路は次のようになります。

```text
KUBE-SERVICES → KUBE-SVC-* → KUBE-SEP-* → endpoint DNAT
```

同じ重みの適格な endpoint が3つあり、affinity/ローカリティのポリシーによる上書きがない場合、条件付き確率は 1/3、次に残りのパケットの 1/2、そして残り、というかたちでほぼ均等な選択になります。これは説明用の例であり、キャプチャした出力でも、すべてのデータプレーンのルール構造でもありません。

```text
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

| セキュアな kubelet endpoint | 用途 |
|------------------------|---------|
| `/pods` | Pod の情報 |
| `/exec/{namespace}/{pod}/{container}` | container の exec ストリーム |
| `/containerLogs/{namespace}/{pod}/{container}` | container のログ。以前の `/logs/...` パスではありません |
| `/metrics`, `/healthz` | 認可済みのメトリクス/ヘルス endpoint |

サポートされている API server 経由の診断手段と適切な認可を使用してください。ノードの実際の `status.addresses` が重要です。ホスト名や無関係なオブジェクトの先頭アドレスで代用してはいけません。

## ルーティング可能な Pod CIDR の設定

![Illustrative remote Pod CIDRs and the on-premises router.](../.gitbook/assets/en-eks-hybrid-nodes-02-network-configuration-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-02-network-configuration-0.html)

### オプション 1: BGP（推奨）

![Illustrative BGP Pod-prefix advertisements.](../.gitbook/assets/en-eks-hybrid-nodes-02-network-configuration-1.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-02-network-configuration-1.html)

AWS の CNI サポート専用ページには、AWS が管理する Cilium 1.17/1.18 のビルドが記載されています。ここでの参照バージョンは互換性のあるカーネル/OS 上の 1.18.3-0 です。upstream の 1.19 に無検証で置き換えないでください。AWS の他のページには Calico BGP とその例が引き続き記載されています。それは Calico プロジェクトが非推奨であることの根拠にはなりません。既存のデプロイについてはサポート範囲を確認してください。

**既存の固定された Cilium リリース**の所有者を通じて BGP を有効化し、values をマージして operator/agent のロールアウトを確認してください。

```yaml
bgpControlPlane:
  enabled: true
operator:
  rollOutPods: true
```

AWS 形式の `v2alpha1` API は、レビュー対象の 1.18.3 の CRD でも引き続き提供されています（同 CRD は `v2` も提供します）。この例を使うためだけに CRD を置き換える必要はありません。

以下では hybrid node を選択し、ピアの advertisement セレクターを advertisement のラベルに紐づけ、それらの Pod CIDR のみをアドバタイズします。

```yaml
apiVersion: cilium.io/v2alpha1
kind: CiliumBGPClusterConfig
metadata:
  name: hybrid-bgp-config
spec:
  nodeSelector:
    matchLabels:
      eks.amazonaws.com/compute-type: hybrid
  bgpInstances:
  - name: hybrid-instance
    localASN: 65001
    peers:
    - name: on-prem-router
      peerASN: 65000
      peerAddress: 10.80.1.1
      peerConfigRef:
        name: on-prem-peer
```
```yaml
apiVersion: cilium.io/v2alpha1
kind: CiliumBGPPeerConfig
metadata:
  name: on-prem-peer
spec:
  timers:
    holdTimeSeconds: 90
    keepAliveTimeSeconds: 30
  gracefulRestart:
    enabled: true
    restartTimeSeconds: 120
  families:
  - afi: ipv4
    safi: unicast
    advertisements:
      matchLabels:
        advertise: hybrid-pods
```
```yaml
apiVersion: cilium.io/v2alpha1
kind: CiliumBGPAdvertisement
metadata:
  name: hybrid-pod-cidrs
  labels:
    advertise: hybrid-pods
spec:
  advertisements:
  - advertisementType: PodCIDR
```

この例は、選択したノードが意図したピアリングトポロジーでルーター `10.80.1.1` に到達できることを前提としています。ラック/ループバックが異なる場合は、重複しない個別のセレクターとレビュー済みの multihop 設定が必要になることがあります。TCP179、ASN、認証、ルートフィルター、ネゴシエートされたタイマー、graceful restart 時の stale route の挙動については、ネットワーク所有者のレビューが必要です。

BGP セッションが確立しただけでは、意図した prefix がアドバタイズされ、受け入れられ、ルーターの転送テーブルにインストールされたことの証明にはなりません。Cilium の BGP control plane は到達性をアドバタイズするものであり、カーネル/underlay のルーティングすべてを置き換えるものではありません。

```bash
cilium --context "$KUBE_CONTEXT" bgp peers
cilium --context "$KUBE_CONTEXT" bgp routes
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s \
  get ciliumbgpclusterconfigs,ciliumbgppeerconfigs,ciliumbgpadvertisements -o json |
  jq '[.items[]|{kind,name:.metadata.name,status:.status}]'
```

#### ASN とルーターの設定

RFC6996 のプライベート範囲は **64512〜65534** と **4200000000〜4294967294** です。従来の「16 ビットの範囲のみ」という一律のルールは誤りでした。1〜64511 のすべての値を自由に使えるパブリック ASN として説明してはいけません。パブリック/予約済み/ドキュメント用の割り当てにはそれぞれ独自のルールがあります。

既存の、調整済みのネットワーク ASN を使用してください。これらの例では `localASN=65001` が Cilium ノードを、`peerASN=65000` がそのオンプレミスルーターを表します。TGW の ASN は上流の別の関係です。TGW が存在するだけで Cilium が自動的に TGW とピアリングすることはありません。Site-to-Site VPN の BGP は、設定された VPN/customer gateway の経路上で終端します。TGW Connect はさらに別のトランスポート/設計です。

以下のベンダー別フラグメントは説明用の出発点であり、実機で検証した設定ではありません。プラットフォーム/バージョン固有の import/export prefix フィルター、上限、復旧手順とともに、ルーターの所有者を通じてマージしてください。稼働中のルーターのグローバル ASN を無闇に変更しないでください。

**Cisco IOS / IOS-XE**

```text
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

```text
router bgp 65000
  address-family ipv4 unicast
  neighbor 10.80.1.10
    remote-as 65001
    description EKS-Hybrid-Cilium
    address-family ipv4 unicast
      soft-reconfiguration inbound
```

**Juniper Junos (MX / QFX / SRX)**

```text
set protocols bgp group eks-hybrid type external
set protocols bgp group eks-hybrid peer-as 65001
set protocols bgp group eks-hybrid neighbor 10.80.1.10 description "EKS Hybrid Node"
set protocols bgp group eks-hybrid family inet unicast
set routing-options autonomous-system 65000
```

**Arista EOS**

```text
router bgp 65000
   neighbor 10.80.1.10 remote-as 65001
   neighbor 10.80.1.10 description EKS-Hybrid-Cilium
   !
   address-family ipv4
      neighbor 10.80.1.10 activate
```

**MikroTik RouterOS 7.20+**

```text
/routing/bgp/instance
add name=hybrid as=65000
/routing/bgp/connection
add name=hybrid-node-001 instance=hybrid remote.address=10.80.1.10 remote.as=65001 local.role=ebgp address-families=ip disabled=yes
# Review input/output filters and routing before enabling the connection.
```

**FRRouting (FRR), 参照バージョン 10.7.1**

```text
ip prefix-list HYBRID_PODS seq 10 permit 10.85.0.0/16 ge 25 le 25
route-map FROM_HYBRID permit 10
 match ip address prefix-list HYBRID_PODS
route-map TO_HYBRID deny 10
router bgp 65000
 bgp router-id 10.80.1.1
 bgp ebgp-requires-policy
 neighbor 10.80.1.10 remote-as 65001
 address-family ipv4 unicast
  neighbor 10.80.1.10 activate
  neighbor 10.80.1.10 route-map FROM_HYBRID in
  neighbor 10.80.1.10 route-map TO_HYBRID out
 exit-address-family
```

RouterOS 7.20 以降では BGP インスタンスを明示的に定義します。FRR の従来のデフォルトでは eBGP のポリシーが必須で、フィルターがないまま確立したセッションは `(Policy)` と表示され、ルートを交換しないことがあります。FRR の例では、レビュー済みの `/25` の Pod ブロックのみを受け入れ、Cilium へはルートをエクスポートしません。実際の IPAM 設計と上流のルーティングに合わせてフィルターを調整してください。

### オプション 2: 静的ルート

![Illustrative static Pod-prefix routes; derive current next hops from observed state.](../.gitbook/assets/en-eks-hybrid-nodes-02-network-configuration-2.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-02-network-configuration-2.html)

Cilium の **cluster-pool IPAM** では、割り当て済みの `CiliumNode.spec.ipam.podCIDRs` をすべて読み取ってください。割り当てがノードの登録順に従うとは限りません。`/16` は幾何学的には 512 個の `/25` ブロックを含み、各 `/25` は 128 アドレスを持ちますが、これは 512 ノードのサポートや、ノードあたり 128 個の利用可能なアプリケーション Pod IP を保証するものではありません。予約アドレス、ノード/CNI による使用、kubelet やリソースの上限も影響します。

これはレビュー済みの新規プールに対する Cilium の Helm values のフラグメントであり、kubelet 全体の `podCIDR` 設定ではありません。移行の近道として、既存の割り当て済み CIDR やブロックサイズを変更してはいけません。

```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.85.0.0/16
    clusterPoolIPv4MaskSize: 25
```

`.addresses[0]` を next hop として使わないでください。Cilium 内部のアドレスである可能性があります。以下は IPv4 の InternalIP を Kubernetes の Node と相互チェックし、すべての Pod prefix を承認済みのリモート範囲に対して検証し、重複や状態の欠落を拒否して、実行可能なシェルではなく **JSON の候補**を生成します。

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/compute-type=hybrid -o json |
  jq '{items:[.items[]|{metadata:{name:.metadata.name,uid:.metadata.uid},
       status:{addresses:.status.addresses}}]}' > "$WORK_DIR/hybrid-nodes.json"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get ciliumnodes.cilium.io -o json |
  jq '{items:[.items[]|{metadata:{name:.metadata.name,uid:.metadata.uid},
       spec:{addresses:.spec.addresses,ipam:{podCIDRs:.spec.ipam.podCIDRs}}}]}' \
  > "$WORK_DIR/cilium-nodes.json"
```
```bash
python3 - <<'PY'
import ipaddress, json, os
from pathlib import Path
folder = Path(os.environ["WORK_DIR"])
network = json.loads((folder / "cluster.json").read_text())["cluster"]["remoteNetworkConfig"]
node_ranges = [ipaddress.ip_network(c, strict=True) for n in network["remoteNodeNetworks"] for c in n["cidrs"]]
pod_ranges = [ipaddress.ip_network(c, strict=True) for n in network.get("remotePodNetworks", []) for c in n["cidrs"]]
if not pod_ranges:
    raise SystemExit("A reviewed routable remote Pod range is required for this route plan")
nodes = {n["metadata"]["name"]: n for n in json.loads((folder / "hybrid-nodes.json").read_text())["items"]}
claims = json.loads((folder / "cilium-nodes.json").read_text())["items"]
rows, seen = [], []
for item in claims:
    name = item["metadata"]["name"]
    if name not in nodes:
        continue
    node = nodes[name]
    ips = [ipaddress.ip_address(a["address"]) for a in node["status"]["addresses"]
           if a["type"] == "InternalIP" and ":" not in a["address"]]
    if len(ips) != 1 or not any(ips[0] in n for n in node_ranges):
        raise SystemExit(f"Review the unique IPv4 InternalIP and remote-node range for {name}")
    cilium_ips = [ipaddress.ip_address(a["ip"]) for a in item["spec"].get("addresses", [])
                  if a["type"] == "InternalIP" and ":" not in a["ip"]]
    if cilium_ips != ips:
        raise SystemExit(f"Kubernetes/Cilium InternalIP mismatch for {name}")
    cidrs = item["spec"]["ipam"].get("podCIDRs") or []
    if not cidrs:
        raise SystemExit(f"No allocated cluster-pool Pod CIDRs for {name}; do not invent a route")
    for raw in cidrs:
        cidr = ipaddress.ip_network(raw, strict=True)
        if cidr.version != 4 or not any(cidr.subnet_of(p) for p in pod_ranges):
            raise SystemExit(f"Unapproved Pod CIDR for {name}: {cidr}")
        if any(cidr.overlaps(previous) for previous in seen):
            raise SystemExit("Overlapping or duplicate Pod routes require investigation")
        seen.append(cidr)
        rows.append({"node": name, "nodeUID": node["metadata"]["uid"],
                     "ciliumNodeUID": item["metadata"]["uid"], "destination": str(cidr), "nextHop": str(ips[0])})
if set(nodes) != {row["node"] for row in rows}:
    raise SystemExit("Some hybrid nodes have no matching Cilium allocation")
(folder / "reviewed-route-candidates.json").write_text(json.dumps(rows, indent=2) + "\n")
print(json.dumps(rows, indent=2))
PY
```

これは cluster-pool IPAM に対するある時点の計画であり、ノード identity のアトミックなリースでも、ルーティングコントローラーでもありません。変更前に再検証してください。Calico の BlockAffinity は別のモデルです。このジェネレーターを無検証で再利用せず、その状態、borrowing/pool の挙動、実際のルートを確認してください。

所有者のレビュー後、手動でのルーター設定の記述は次のようになります。

```text
# Illustrative syntax after validating the route plan on the intended router:
# Linux
ip route add 10.85.0.0/25 via 10.80.1.10
# Cisco IOS / IOS-XE
ip route 10.85.0.0 255.255.255.128 10.80.1.10 name hybrid-node-001-pods
# FRR
ip route 10.85.0.0/25 10.80.1.10
```

変更は実際のネットワークマネージャー/デバイス設定を通じて永続化してください。`up ip route ...` の行は ifupdown のスタンザに属するもので、単独の Bash スクリプトに置くものではなく、最近のすべての Linux ネットワークマネージャーで通用するものでもありません。静的ルートにはドリフト/障害の追跡が必要です。元の「1〜5 ノード」というしきい値は計画上の目安であり、技術的な上限ではありませんでした。

### オプション 3: ARP プロキシ

AWS は proxy ARP を L2 における選択肢の一つとして説明しています。これには適切な on-link の近隣探索の挙動と、専用に設定された CNI/ホスト側の実装が必要です。汎用的な Cilium を有効化するだけでは、この経路が使える状態であることの証明にはなりません。

![Proxy ARP concept for a verified L2/on-link design; upstream routes are still required.](../.gitbook/assets/en-eks-hybrid-nodes-02-network-configuration-3.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-02-network-configuration-3.html)

ARP のブロードキャストは TGW/VPN/DX の Layer 3 ルーティングを越えません。このオプションによって VPC/WAN の戻りルート要件がなくなるわけではありません。BGP/静的ルートの設計を置き換える前に、実際の L2 の挙動とフェイルオーバーを検証してください。

## ネットワークポリシー

ポリシーの効果は、セレクション、方向、適用するデータプレーンに依存します。Kubernetes NetworkPolicy の allow は加算的で、別の一致するポリシーがトラフィックを許可し得ます。Cilium の明示的な deny と L7 の挙動は個別に評価する必要があります。以下の例は管理された namespace で試すべき代替案であり、あらゆる allow ルールを重ねればより厳格になると期待するための指示ではありません。

### Kubernetes NetworkPolicy

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

これは `reviews` への ingress を選択し、同じ namespace 内で一致する `productpage` の Pod からの TCP9080 を許可します。すべての Pod/方向を分離したり、他のすべてのポリシーを上書きするものではありません。

### CiliumNetworkPolicy と L7

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
        k8s:io.kubernetes.pod.namespace: bookinfo
    toPorts:
    - ports:
      - port: '9080'
        protocol: TCP
```
```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: frontend-http-contract
  namespace: bookinfo
spec:
  endpointSelector:
    matchLabels:
      app: reviews
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: productpage
        k8s:io.kubernetes.pod.namespace: bookinfo
    toPorts:
    - ports:
      - port: '9080'
        protocol: TCP
      rules:
        http:
        - method: GET
          path: /api/v1/.*
```

この HTTP ルールは、制限のない L4 の allow に対する代替案であり、その上に自動的に重なる制限ではありません。実際のアプリケーションのパスを使用してください。HTTP の検査には適切な可視性が必要で、暗号化された mesh/TLS のトラフィックが自動的に検査可能になるわけではありません。

### DNS ベースの egress

別途用意した `external-api-client` の例では、**Cilium が identity を認識する CoreDNS Pod** への DNS と、観測された API アドレスへの HTTPS を許可します。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-external-api
  namespace: bookinfo
spec:
  endpointSelector:
    matchLabels:
      app: external-api-client
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: ANY
      rules:
        dns:
        - matchPattern: '*'
  - toFQDNs:
    - matchName: api.example.com
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

実際のリゾルバー/identity の構成を確認してください。NodeLocal DNS、ホストの DNS、Cilium 管理外の endpoint では、サポートされる別のルールが必要になることがあります。FQDN の IP 観測はリモート API の認証ではありません。DNS のキャッシュと共有アドレスを考慮してください。また、Cilium 固有の L7/FQDN 機能は、AWS が挙げているデフォルトの Kubernetes NetworkPolicy のサポート範囲を超えています。

## webhook の設定

一般的な直接ルーティングの設計では、control plane が webhook Pod の IP に到達できる必要があります。適切な Pod の戻り経路がない場合は、適切な場所に配置したクラウドホスト型のコンポーネントを使用してください。gateway/proxy を使う代替設計は個別に検証してください。

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

これは Pod テンプレートの affinity のフラグメントであり、完全な Deployment ではありません。`NotIn hybrid` の条件は、一致する正常なクラウド側のキャパシティや、その他すべてのスケジューリング制約が満たされることの証明にはなりません。

AWS Load Balancer Controller、CloudWatch/ADOT の operator、cert-manager には webhook の配置要件があります。これらの operator とノード側のコレクターを区別してください。**Metrics Server は集約 API service であり、admission webhook ではありません**が、それでも control plane から Pod への到達性が必要です。Pod の phase だけでなく、実際の API 呼び出しと webhook をテストしてください。

## 読み取り専用の接続診断

### Kubernetes API の TLS とタイミング

```bash
set -euo pipefail
endpoint=$(jq -er '.cluster.endpoint' "$WORK_DIR/cluster.json")
case "$endpoint" in https://*) ;; *) printf 'HTTPS endpoint required.\n' >&2; exit 1;; esac
jq -er '.cluster.certificateAuthority.data' "$WORK_DIR/cluster.json" |
  base64 --decode > "$WORK_DIR/cluster-ca.pem"
openssl x509 -in "$WORK_DIR/cluster-ca.pem" -noout >/dev/null
curl --silent --show-error --connect-timeout 5 --max-time 15 \
  --cacert "$WORK_DIR/cluster-ca.pem" --output "$WORK_DIR/api-response.txt" \
  --write-out '{"httpCode":%{http_code},"remoteIP":"%{remote_ip}","dnsTotalSeconds":%{time_namelookup},"connectTotalSeconds":%{time_connect},"tlsTotalSeconds":%{time_appconnect},"totalSeconds":%{time_total}}\n' \
  "$endpoint/readyz" > "$WORK_DIR/api-timing.json"
cat "$WORK_DIR/api-timing.json"
```

cluster の CA とホスト名が検証を通る必要があります。HTTP401/403 の応答は、認可が不足している一方で TLS endpoint には到達できていることを示し得ますが、アプリケーションのヘルスチェックの成功ではありません。curl のタイミングフィールドは累積の各フェーズであり、純粋な RTT の測定値ではありません。ICMP ping に応答がないことは、EKS API が停止している証明にはなりません。

### VPN の状態とメトリクス

```bash
: "${VPN_ID:?Select the reviewed VPN connection}"
: "${TUNNEL_IP:?Select its actual AWS tunnel outside IP}"
check_account
# Select telemetry only: do not dump customer gateway configuration or pre-shared keys.
aws ec2 describe-vpn-connections --region "$AWS_REGION" --vpn-connection-ids "$VPN_ID" \
  --query 'VpnConnections[].{id:VpnConnectionId,state:State,telemetry:VgwTelemetry}' \
  --output json > "$WORK_DIR/vpn-state.json"
jq -e --arg ip "$TUNNEL_IP" 'length==1 and any(.[0].telemetry[]?; .OutsideIpAddress==$ip)' \
  "$WORK_DIR/vpn-state.json" >/dev/null
export VPN_ID TUNNEL_IP
python3 - <<'PY'
import ipaddress, json, os
from datetime import datetime, timedelta, timezone
from pathlib import Path
ipaddress.ip_address(os.environ["TUNNEL_IP"])
now = datetime.now(timezone.utc)
end = now.replace(minute=now.minute - now.minute % 5, second=0, microsecond=0)
body = {"Namespace": "AWS/VPN", "MetricName": "TunnelState",
        "Dimensions": [{"Name": "VpnId", "Value": os.environ["VPN_ID"]},
                       {"Name": "TunnelIpAddress", "Value": os.environ["TUNNEL_IP"]}],
        "StartTime": (end - timedelta(minutes=15)).isoformat(), "EndTime": end.isoformat(),
        "Period": 300, "Statistics": ["Minimum", "Maximum"]}
(Path(os.environ["WORK_DIR"]) / "vpn-metric-request.json").write_text(json.dumps(body, indent=2) + "\n")
PY
aws cloudwatch get-metric-statistics --region "$AWS_REGION" \
  --cli-input-json "file://$WORK_DIR/vpn-metric-request.json" --output json \
  > "$WORK_DIR/vpn-metric-result.json"
jq '{label:.Label,datapoints:(.Datapoints|sort_by(.Timestamp))}' "$WORK_DIR/vpn-metric-result.json"
```

`available` は VPN リソースの状態であり、トンネルの健全性ではありません。TunnelState は UP/静的または ESTABLISHED/BGP のとき 1、それ以外の状態では 0 になります。集計値は小数になり得ます。データがないことと DOWN は区別し、両方のトンネル、ルート、実際のワークロードの挙動を確認してください。このクエリは customer gateway の設定や pre-shared key を出力しないようにしています。

AWS の RTT 200ms 以下 / 100Mbps という指針は一般的なガイダンスです。従来の 50/100ms の区分や「Direct Connect は常に 10ms 未満」という記述は、検証されていない目安であり、保証ではありませんでした。

## 参考資料

- [Hybrid networking](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
- [EKS PrivateLink: management, OIDC and console endpoints](https://docs.aws.amazon.com/eks/latest/userguide/vpc-interface-endpoints.html)
- [S3 interface endpoints and private DNS](https://docs.aws.amazon.com/AmazonS3/latest/userguide/privatelink-interface-endpoints.html)
- [Roles Anywhere endpoint policies](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/vpc-interface-endpoints.html)
- [Current hybrid CNI support](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [AWS hybrid BGP procedure](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cilium-bgp.html)
- [Mixed-mode DNS and webhooks](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-webhooks.html)
- [Hybrid routing concepts](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-concepts-kubernetes.html)
- [Hybrid traffic-flow reference](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-concepts-traffic-flows.html)
- [Cilium 1.18.3 routing source](https://github.com/cilium/cilium/blob/v1.18.3/Documentation/network/concepts/routing.rst)
- [Cilium 1.18.3 DNS-policy source](https://github.com/cilium/cilium/blob/v1.18.3/Documentation/security/dns.rst)
- [RFC6996 private ASNs](https://www.rfc-editor.org/rfc/rfc6996.html)
- [RouterOS BGP reference](https://help.mikrotik.com/docs/spaces/ROS/pages/328220/BGP)
- [FRR 10.7.1 BGP reference source](https://github.com/FRRouting/frr/blob/frr-10.7.1/doc/user/bgp.rst)
- [VPN metrics](https://docs.aws.amazon.com/vpn/latest/s2svpn/monitoring-cloudwatch-vpn.html)
- [Kubernetes 1.36.2 kubelet server source](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/kubelet/server/server.go)
- [Kubernetes NetworkPolicy semantics](https://kubernetes.io/docs/concepts/services-networking/network-policies/)


< [前へ: 前提条件](01-prerequisites.md) | [目次](./README.md) | [次へ: インターネット制限環境のセットアップ](03-airgap-setup.md) >
