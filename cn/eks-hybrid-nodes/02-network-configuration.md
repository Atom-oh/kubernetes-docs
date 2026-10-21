# 网络配置

> **支持的版本**：EKS 1.36 示例；AWS 维护的 Cilium 1.18.3-0 参考版本，需要兼容的主机/内核
> **最后更新**：2026年10月18日

分别验证路由、DNS、TLS、凭证和应用流量。这些示例已使用本地 Schema 和测试样例进行检查，其中包括模拟的 Terraform 提供程序；没有更改任何 AWS 资源、路由器、防火墙或运行中的集群。这些图示是基于 AWS 概念绘制的仓库插图，并非 AWS 发布的针对这些配置的验证结果。

![混合节点先决条件和双向路由。](../.gitbook/assets/en-eks-hybrid-nodes-prereq-0.png)

[🔍 查看交互式图示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-prereq-0.html)

**安全团队配套文档：**[混合节点网络隔离审查](11-network-separation-security.md)说明了新增的控制平面到本地网络连接、端点类型、权限和数据边界以及审查证据。仅有私有连接并不能证明符合规范。

## 网络架构概览

控制平面→混合节点流量和私有 Kubernetes API 流量使用集群 VPC 网络路径。Kubelet 到公共 API 端点的流量则使用其配置的公共路由；“所有流量始终经过 VPC ENI”的说法过于笼统。Direct Connect 公共 VIF、私有连接和公共互联网路径是不同的选项。

EKS 控制平面 ENI/IP 可能发生变化。请审查实际的集群归属和已批准的控制平面子网范围，而不要将共享 VPC 中每个 `Amazon EKS*` ENI 都视为属于此集群。

在执行只读诊断前，先绑定账户和 Kubernetes 上下文：

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

## CIDR 范围要求

远程节点/Pod 网络应使用互不重叠的 IPv4 **RFC1918 或 CGNAT** 地址段，并与 VPC 和 Kubernetes Service CIDR 分开。每种远程网络最多支持 15 个 CIDR。目前，EKS 支持通过 API 工作流为现有集群配置远程网络；这并非仅适用于创建集群。

| 网络行为 | 含义 |
|------------------|---------|
| 可路由的 Pod IP | 已批准的路由允许云端/控制平面客户端向 Pod IP 发起连接 |
| 出站伪装 | SNAT 可以为 Pod 发起的连接提供返回路径；但它不会自动允许新的入站连接 |
| 不可路由的 Pod 网络 | 直接的云端→Pod 流量需要其他受支持的路径；常规设计应使用托管在云端的 Webhook/API Service |

不可路由并不意味着 Pod 无法发起任何 AWS API 调用。对于直接的混合节点/云端 Pod 通信和托管在混合节点上的 Webhook，请提供实际的 Pod 路由。网关/代理替代方案有各自的要求。

## 所需防火墙端口

| 流量方向 | 协议/端口 |
|------|-----------------|
| Node/Pod → Kubernetes API | 到实际集群端点的 TCP443 |
| 控制平面 ENI → kubelet | TCP10250，并启用 kubelet 身份验证/授权 |
| 控制平面 → Webhook 或聚合 API Pod | 其配置的 TCP 端口，而不是笼统的“8443+”范围 |
| DNS 客户端 ↔ 实际解析器 | UDP/TCP53 和有状态返回流量 |
| 参与节点之间的 Cilium VXLAN | UDP8472 |
| Cilium Geneve，仅在为设计选择且受支持时 | UDP6081 |
| Cilium 健康检查 | TCP4240 以及所需的 ICMP/健康端点可达性 |
| BGP 节点↔路由器 | 为配置的主/备对等体使用 TCP179 |
| VPN 网关传输 | UDP500/4500 及适用的 IPsec 传输要求 |
| 应用/AWS 凭证和镜像仓库 Service | 仅限其实际目标地址和端口 |

网络管理员应在保留现有规则和连接跟踪的前提下更改防火墙规则。只允许通信所需的 IP 地址、CIDR 和端口。避免使用允许整个 `10.0.0.0/8` 范围的 INPUT 规则，或不限制源地址和目标地址的 DNS/VXLAN 规则。在持久化更改前，应审查要保存哪些规则，不要不加区分地保存整个规则集。

对于 kubelet API，请使用带身份验证和授权的 TCP `10250`。不要开放允许未授权访问的旧版只读 kubelet 端口 TCP `10255`。

## AWS 端点访问

**EKS 管理 API PrivateLink 端点不是 Kubernetes API Server 端点。**

| `com.amazonaws.<region>.*` 的 Service 后缀 | 用途/所需场景 |
|------------------------------------------------|-----------------------|
| `eks` | AWS EKS 管理调用，例如 DescribeCluster |
| `eks-auth` | 使用 EKS Pod Identity 时所需 |
| `ecr.api`、`ecr.dkr` | 私有 ECR API/容器镜像仓库；镜像层还需要 S3 访问 |
| `s3` | 私有 S3 访问；本地网络无法直接使用 VPC 网关端点 |
| `ssm`、适用的 SSM 消息服务 | SSM 凭证/管理功能 |
| `rolesanywhere` | 使用该提供程序时所需的 IAM Roles Anywhere 凭证 |
| `sts` | 实际客户端 STS/IRSA/AssumeRole 调用；在本地签署 EKS 令牌本身并不构成客户端 STS 网络请求 |
| `logs`、`monitoring`、其他选定的服务 | 仅当所选 Agent/工作负载会调用这些服务时需要 |
| `oidc-eks` | 当前的 EKS OIDC 发现/JWKS PrivateLink 服务（如有提供） |
| `eks-proxy` | AWS 控制台资源视图；不是面向公共应用的 SDK/API |

请确认目标区域提供相应服务。私有 ECR 端点不会使**公共 ECR**、CloudFront 或任意软件包仓库变为私有。例如，公共 ECR 中的 AWS Cilium OCI Chart 需要经过批准且可访问/镜像后的分发路径。

OIDC 发现/JWKS 是匿名的公钥材料。`oidc-eks` 仅接受其默认的完全访问端点策略；应使用 SG/路由控制可达性，并使用 IAM 信任中的 `aud`/`sub` 条件进行角色授权。STS 会在 AWS 内部验证 IRSA 令牌，此过程独立于此 VPC 端点。

对于 Roles Anywhere CreateSession 端点策略，由于策略评估先于证书身份验证，主体必须为 `*`；应按文档所述限制已批准的信任锚资源和受支持的证书条件。不要将一个通用端点策略复制到这些不同的服务上。端点策略用于筛选端点流量；它不能取代 IAM/角色信任，也不会在全局范围内禁用公共服务端点。

```bash
check_account
vpc_id=$(jq -er '.cluster.resourcesVpcConfig.vpcId' "$WORK_DIR/cluster.json")
aws ec2 describe-vpc-endpoints --region "$AWS_REGION" \
  --filters "Name=vpc-id,Values=$vpc_id" --output json |
  jq '[.VpcEndpoints[]|{id:.VpcEndpointId,service:.ServiceName,type:.VpcEndpointType,
      state:.State,privateDNS:.PrivateDnsEnabled,dnsOptions:.DnsOptions,
      subnets:.SubnetIds,groups:.Groups,dnsEntries:.DnsEntries}]'
```

### S3 私有 DNS 和制品分发

S3 **接口端点支持私有 DNS**。“仅限入站 Resolver”的选项会通过接口端点引导本地网络查询，同时让 VPC 内流量使用必需的 S3 网关端点。启用此选项期间，请保留该网关端点。或者，清除此选项，让所有相关 S3 流量都使用接口端点。

私有 DNS 并不是 TLS 重写。通过 PHZ/CNAME 将 `hybrid-assets.eks.amazonaws.com` 映射到 S3 端点，并不会让 S3 获得 CloudFront 主机名的证书或对象/Host 路由行为。不要为了让此类镜像正常工作而禁用 TLS 验证。请使用受支持的制品准备/客户端配置路径、带有自有主机名/证书且经批准的镜像，或使用已在经过验证的映像中预装的依赖项。

## VPC 私有端点（受限互联网连接） {#vpc-private-endpoints-air-gap-private-connectivity}

此处的“气隙”是指限制互联网访问但保留所需 AWS 连接，并非断开连接的集群。

下面的完整 Terraform 示例使用现有 VPC、端点子网和 TGW。它不会创建 VPN/DX 线路、TGW 附加、到本地网络的路由或 EKS 私有 DNS 配置。请验证 VPC DNS 支持/主机名设置以及实际可用区的差异；两个不同的子网 ID 本身并不能证明它们分布在不同可用区。

请通过原基础设施所有者管理，并在规划替换前导入/接管现有资源。默认端点集合以 SSM 为例；请根据所选提供程序/工作负载进行调整。端点和 Resolver ENI 会产生费用。提供程序的账户防护和范围受限的入站规则都是有意设置的；响应流量使用有状态 SG 跟踪。

```hcl
terraform {
  required_version = ">= 1.9, < 2.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
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

S3 网关依赖关系已明确声明。请将所需的本地 DNS/Service 地址段纳入 `remote_ipv4_cidrs`，而不只是节点/Pod 网络：示例中的 DNS 服务器 `192.168.1.10/11` 需要已批准的 `192.168.1.0/24` 路由或相应的主机路由。对于 VGW 返回路由，请使用 `gateway_id` 而不是 `transit_gateway_id`；不要将 TGW ID 放入 VGW/网关字段，也不要同时配置两个目标。仅有 VPC 路由并不能建立 TGW/VPN/本地网络路由。

## DNS 配置

本地解析器可以有条件地将选定的 AWS/Service 名称和实际集群端点名称转发到 Route 53 Resolver 入站 IP。请使用实际端点返回的地址。宽泛地转发 `amazonaws.com` 可能会影响无关服务；请谨慎选择域名区域并避免转发环路。

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

此 BIND 片段涵盖了所示的 Service 区域，但不会自动涵盖 Kubernetes API 主机名。请添加实际集群端点的 DNS 名称/后缀，以及经核实的 Service 清单中的其他必需名称。Resolver 出站规则负责处理本地域名；该域名必须由所选 DNS 服务器权威解析或可访问，而不能再被转发回同一环路。

### CoreDNS 自定义域名配置

如果所选设计直接从 CoreDNS 转发，请将经过审查的服务器块合并到现有 Corefile 中；不要覆盖整个托管 ConfigMap：

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

请保留现有 Kubernetes 区域、健康/就绪检查和重新加载行为。检查实际的解析器文件以及 systemd-resolved/存根布局；将 DNS 服务器的查询转发回其自身可能导致环路。对于某个区域，请选择适当的 VPC 转发路径或显式的 CoreDNS 转发，不要叠加相互矛盾的路由。

对于托管的 EKS 插件，请获取**已安装版本**的配置 Schema，并验证完整的拟议值，同时保留其他现有设置：

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

这是本地 Schema 检查，不是发布操作。应用配置前，请协调托管插件/GitOps 的管理权、自动扩缩容和恢复方案。

### CoreDNS 的部署位置和本地性

AWS 建议在混合集群中，云端节点和混合节点上各至少运行一个 CoreDNS 副本。每个位置运行两个副本可以作为一种韧性设计选择；四个副本既不是普遍适用的最低要求，也不是保证。

请验证所有目标 DNS 节点上的实际可用区标签。混合节点需要由所有者定义的 `topology.kubernetes.io/zone` 值，例如 `onprem-dc1`；计算类型标签并不会自动成为此可用区标签或污点。合并部署位置偏好时，不要删除其他无关的亲和性/容忍度设置：

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

软亲和性/分布约束只是偏好，无法保证 2+2 的分布或成功引导。仅靠部署位置也不能确保客户端选择本地 DNS 副本。

AWS 文档中的 Service 流量分布示例使用 `PreferClose`。使用 Cilium 时，应配置受支持的 `loadBalancer.serviceTopology` 设置，并由所有者滚动更新受影响的 Agent，然后再依赖此功能。请检查实际数据平面/版本和健康的本地端点。

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

检查实际的 Service IP、EndpointSlice 可用区/提示信息和 Pod 就绪状态。`10.100.0.10` 是某个特定 Service CIDR 的示例，并非通用的集群 DNS 地址。本地副本不会让断开连接的 EKS 集群变成完全独立的 DNS/控制平面。

## 流量模式

图示使用示意地址和简化的处理阶段。请检查实际的 Service 数据平面是 kube-proxy iptables、nftables/IPVS，还是 Cilium 的 eBPF 替代实现。

### 模式 1：Kubelet → EKS 控制平面

Kubelet 会解析并连接到已配置的 Kubernetes API 端点。私有和公共访问使用不同的路由；两者都不应与 EKS 管理 PrivateLink 端点混淆。

![公共和私有端点配置下的 Kubelet API 访问路径。](../.gitbook/assets/en-eks-hybrid-nodes-02-network-configuration-10.png)

[🔍 查看交互式图示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-02-network-configuration-10.html)

### 模式 2：EKS 控制平面 → Kubelet

控制平面通过 TCP10250 访问上报的、可路由的节点地址。此路径支持日志、exec 和 port-forward，并需要反向路由、防火墙许可及 kubelet 身份验证。

![控制平面通过 TCP10250 连接到可路由的 kubelet 地址。](../.gitbook/assets/en-eks-hybrid-nodes-02-network-configuration-11.png)

[🔍 查看交互式图示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-02-network-configuration-11.html)

### 模式 3：Pod → EKS 控制平面

使用 Kubernetes Service IP 的 Pod 需要进行 Service 转换，以便连接到所选 API 端点。如果应用了出站 SNAT，响应会发往节点地址，并由连接跟踪执行反向转换；如果未使用 SNAT，则 Pod 地址必须具有返回路由。

![Service 逻辑转换和可选 SNAT 的影响；图示顺序并非适用于所有情况的 Hook 顺序。](../.gitbook/assets/en-eks-hybrid-nodes-02-network-configuration-12.png)

[🔍 查看交互式图示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-02-network-configuration-12.html)

图示中 SNAT 先于 DNAT 的编号并非通用 Hook 顺序。在 iptables 路径中，Service DNAT 通常先于路由和适用的 POSTROUTING SNAT。eBPF 路径有所不同。请先捕获实际数据包/连接状态，再得出结论。

### 模式 4：EKS 控制平面 → Pod（Webhook）

API Server 必须能够访问所选 Webhook Pod IP/端口。请使用已配置的端口；旧图例中的“8443+”并非有效的端口范围要求。

![控制平面到 Webhook Pod 的路径；请使用实际配置的 TCP 端口和数据平面。](../.gitbook/assets/en-eks-hybrid-nodes-02-network-configuration-13.png)

[🔍 查看交互式图示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-02-network-configuration-13.html)

### 模式 5：混合节点上的 Pod ↔ Pod

使用受支持的 VXLAN 覆盖网络时，通过**外层节点 IP**访问目标节点。仅为了传送封装后的数据包，底层网络不需要为内层目标 Pod CIDR 配置路由。

![VXLAN Pod 通信。外层转发使用节点 IP；旧图中的 Pod CIDR 转发标签需要更正。](../.gitbook/assets/en-eks-hybrid-nodes-02-network-configuration-14.png)

[🔍 查看交互式图示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-02-network-configuration-14.html)

图示中封装后使用 `10.85.x.0/24` 的转发标签应理解为旧版简化表示：外层数据包会路由到 `10.80.0.x`。同一 L2 网段中的节点可能无需经过路由器即可直接通信。

VXLAN 使用 UDP 封装内层以太网帧。在 IPv4/无额外封装的示例中，50 字节的开销解释了为何需要将 MTU 从 1500 调整为 1450；额外隧道会改变此计算。Cilium VXLAN 使用 UDP8472；标准 VXLAN 通常使用 4789。Geneve 使用 UDP6081。当前 Cilium 隧道配置区分 VXLAN/Geneve；IP-in-IP 并非可互换的默认覆盖网络，不应采用旧版 `--tunnel` 建议来选择它。

VNI 字段为 24 位；Cilium 可以在封装元数据中携带安全身份。这并不是加密的租户隔离。网络策略和实际身份传播应分别处理。

### 模式 6：云端 Pod ↔ 混合节点 Pod

直接 Pod-IP 流量需要通过 VPC、WAN 和本地网络配置相关 Pod 路由。仅当请求实际以 Service VIP 为目标时，才需要进行 Service 转换。

![云端到混合节点 Pod 的直接路由；目标为直接 Pod-IP 时不需要 kube-proxy Service 转换。](../.gitbook/assets/en-eks-hybrid-nodes-02-network-configuration-15.png)

[🔍 查看交互式图示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-02-network-configuration-15.html)

图中的 kube-proxy/iptables 区块取决于数据平面；直接 Pod-IP 数据包本身并不一定需要 kube-proxy DNAT。

### kube-proxy 和 kubelet 详情

在 kube-proxy 的 **iptables 模式**下，常见的链路为：

```text
KUBE-SERVICES → KUBE-SVC-* → KUBE-SEP-* → endpoint DNAT
```

如果有三个符合条件且权重相同的端点，并且没有覆盖此行为的亲和性/本地性策略，则条件概率依次为 1/3、剩余数据包的 1/2、以及其余数据包，最终大致实现均匀选择。这只是示意，并非实际捕获的输出，也不代表所有数据平面的规则结构：

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

| 安全的 kubelet 端点 | 用途 |
|------------------------|---------|
| `/pods` | Pod 信息 |
| `/exec/{namespace}/{pod}/{container}` | 容器 exec 流 |
| `/containerLogs/{namespace}/{pod}/{container}` | 容器日志；不是旧版的 `/logs/...` 路径 |
| `/metrics`、`/healthz` | 需授权的指标/健康端点 |

请使用受支持的、通过 API Server 中介的诊断方式，并进行适当授权。应以节点实际的 `status.addresses` 为准；不要用主机名或无关对象中的第一个地址代替。

## 选择 CNI 设计：仅使用 Cilium，还是与 VPC CNI 混合使用

VPC CNI 与混合节点不兼容。**此比较假设混合节点使用 Cilium，并采用当前 CNI 指南中介绍的 AWS 维护版本**。对于现有的 Calico 安装，请另行确认其当前支持情况和运维责任。因此，“仅使用 Cilium，还是与 VPC CNI 混合使用？”这个问题实际上是在问：**集群中是否有云端节点；如果有，它们运行哪种 CNI？**

| 标准 | ① 仅混合节点的集群（仅 Cilium） | ② 混合模式（云端使用 VPC CNI + 混合节点使用 Cilium） | ③ 云端节点也使用 Cilium |
|---|---|---|---|
| AWS 支持 | 受支持（混合节点上使用 Cilium） | 受支持。AWS 推荐的混合模式设计 | 云端不受支持：AWS 不支持在 AWS Cloud 中的节点上运行 Cilium |
| Webhook 部署位置 | 运行在混合节点上。控制平面连接 Pod IP，因此本地 Pod CIDR 必须通过 BGP 或静态路由实现可路由 | 运行在云端节点上。本地 Pod CIDR 无需可路由 | 取决于云端 Cilium 的 IPAM 和路由；必须自行验证 |
| 云端到本地 Pod 的流量 | 不适用 | 可路由的本地 Pod CIDR，或[混合节点网关](10-hybrid-nodes-gateway.md) | 自行设计隧道或路由。混合节点网关要求云端节点（包括网关节点）使用 VPC CNI（或 Auto Mode 内置网络），因此无法使用 |
| 突发扩容和 Auto Mode | 没有云端容量时无法实现 | Karpenter 可以添加云端节点。Auto Mode 使用内置网络 | Auto Mode 无法替换其 CNI。Karpenter 节点上的 Cilium 也需要自行运维 |
| 策略和可观测性 | 一个 CNI（NetworkPolicy、Cilium 策略、Hubble），并配置策略实施 | 分别为每种 CNI 配置并验证 NetworkPolicy 实施。必须在受支持的 EC2 Linux 节点上启用 VPC CNI 策略实施；仅有 NetworkPolicy 对象并不会启用它。Cilium 专用策略和 Hubble 仅存在于混合节点一侧 | 一个 CNI，并配置策略实施；但云端一侧的事件响应和升级由你或供应商负责 |

选择方式：

- **存在云端节点：②**。此混合设计在 AWS 支持范围内。在云端运行 Webhook，并使用突发扩容和混合节点网关。在混合模式下，两侧都至少运行一个 CoreDNS 副本；控制平面或 VPC 需要访问混合 Pod IP 的功能（ALB/NLB IP 目标、Metrics Server、AMP 收集）需要可路由的本地 Pod CIDR（[混合模式 Webhook 运维](08-operations.md#mixed-mode-webhook-operations)）。
- **仅使用本地环境：①**。使用单一 CNI 更简单，但 Webhook 运行在混合节点上，因此需要[可路由的 Pod CIDR](#routable-pod-cidr-configuration)。
- **谨慎考虑 ③**。云端节点上的 Cilium 不在 AWS 支持范围内，而且无法使用混合节点网关和 Auto Mode。只有在与供应商签订支持协议，且使用单一 CNI 的优势超过这些限制时，才考虑此方案。

参考资料：
- [为混合节点配置 CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [使用 Kubernetes 网络策略限制 Pod 流量](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [为混合节点配置 Webhook：混合模式集群注意事项](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-webhooks.html)
- [开始使用 EKS 混合节点网关](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-gateway-getting-started.html)

## 可路由的 Pod CIDR 配置

![远程 Pod CIDR 和本地路由器示意图。](../.gitbook/assets/en-eks-hybrid-nodes-02-network-configuration-0.png)

[🔍 查看交互式图示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-02-network-configuration-0.html)

### 选项 1：BGP（推荐）

![Pod 前缀 BGP 通告示意图。](../.gitbook/assets/en-eks-hybrid-nodes-02-network-configuration-1.png)

[🔍 查看交互式图示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-02-network-configuration-1.html)

AWS 专用的 CNI 支持页面列出了 AWS 维护的 Cilium 1.17/1.18 版本。此处参考的是与兼容内核/OS 搭配使用的 1.18.3-0；不要不加判断地将它替换成上游 1.19。AWS 其他页面仍会提及 Calico BGP 及保留的示例。这并不能证明 Calico 项目已弃用；请确认现有部署的支持范围。

请通过**现有且已固定版本的 Cilium 发行版**的所有者启用 BGP，合并配置值，并审查 Operator/Agent 的滚动更新：

```yaml
bgpControlPlane:
  enabled: true
operator:
  rollOutPods: true
```

经审查的 1.18.3 CRD 仍提供 AWS 风格的 `v2alpha1` API（同时也提供 `v2`）。仅仅为了使用此示例，无需替换 CRD。在 Cilium 1.19+ 中，请改用 `cilium.io/v2` BGP CRD（`v2alpha1` BGP CRD 已弃用），而旧版 `CiliumBGPPeeringPolicy` 已在 1.19 中移除。

以下配置会选择混合节点，将对等体的通告选择器关联到通告标签，并且只通告这些节点的 Pod CIDR：

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

此示例假定所选节点可以按预期的对等拓扑访问路由器 `10.80.1.1`。不同机架/环回地址可能需要不同且不重叠的选择器，以及经过审查的多跳设置。TCP179、ASN、身份验证、路由筛选、协商计时器和优雅重启时陈旧路由的行为都需要网络所有者审查。

BGP 会话建立本身并不能证明预期前缀已通告、被接受或安装到路由器的转发表中。Cilium BGP 控制平面负责通告可达性；它不能取代所有内核/底层网络路由。

```bash
cilium --context "$KUBE_CONTEXT" bgp peers
cilium --context "$KUBE_CONTEXT" bgp routes
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s \
  get ciliumbgpclusterconfigs,ciliumbgppeerconfigs,ciliumbgpadvertisements -o json |
  jq '[.items[]|{kind,name:.metadata.name,status:.status}]'
```

#### ASN 和路由器配置

RFC6996 私有范围为 **64512–65534** 和 **4200000000–4294967294**。先前笼统规定“仅限 16 位范围”是错误的。不要把 1–64511 中的所有值都描述为可自由使用的公共 ASN；公共/保留/文档用途分配各有自己的规则。

请使用现有且已协调一致的网络 ASN。在这些示例中，`localASN=65001` 代表 Cilium 节点，`peerASN=65000` 代表其本地路由器。TGW 的 ASN 属于另一种上游关系：不会仅仅因为 TGW 存在，Cilium 就自动与它建立对等关系。Site-to-Site VPN BGP 会在配置的 VPN/客户网关路径上终止；TGW Connect 则是另一种独立的传输/设计。

以下厂商配置片段只是示意性起点，并非经过设备测试的配置。请通过路由器所有者，根据平台/版本合并具有平台/版本特性的入站/出站前缀筛选、限制和恢复配置。不要不加区分地更改运行中路由器的全局 ASN。

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

**FRRouting (FRR)，参考版本 10.7.1**

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

RouterOS 7.20+ 会显式定义 BGP 实例。FRR 的传统默认行为要求 eBGP 策略；即使会话已建立，如果没有筛选器，也可能显示 `(Policy)` 并且不交换路由。FRR 示例只接受经审查的 `/25` Pod 区块，并且不会向 Cilium 通告任何路由；请根据实际 IPAM 设计和上游路由调整筛选器。

### 选项 2：静态路由

![Pod 前缀静态路由示意图；应根据观测到的状态确定当前下一跳。](../.gitbook/assets/en-eks-hybrid-nodes-02-network-configuration-2.png)

[🔍 查看交互式图示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-02-network-configuration-2.html)

在 Cilium **cluster-pool IPAM** 中，读取所有已分配的 `CiliumNode.spec.ipam.podCIDRs`。分配顺序不一定遵循节点注册顺序。一个 `/16` 从几何上可划分为 512 个 `/25` 区块，每个 `/25` 有 128 个地址；这并不保证支持 512 个节点，也不保证每个节点有 128 个可供应用 Pod 使用的 IP。保留地址、节点/CNI 使用情况以及 kubelet/资源限制也会产生影响。

这是用于经审查的新地址池的 Cilium Helm values 片段，不是面向整个 kubelet 的 `podCIDR` 设置。不要为了简化迁移而更改现有已分配的 CIDR 或区块大小：

```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.85.0.0/16
    clusterPoolIPv4MaskSize: 25
```

不要将 `.addresses[0]` 用作下一跳：它可能是 Cilium 内部地址。以下代码会交叉核对 IPv4 InternalIP 和 Kubernetes Node，验证所有 Pod 前缀是否属于已批准的远程范围，拒绝重叠/缺失的状态，并生成**JSON 候选项**，而不是可执行的 Shell 命令：

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

这是基于某一时点为 cluster-pool IPAM 生成的计划，并非对节点身份的原子租约或路由控制器。更改前请重新验证。Calico BlockAffinity 属于另一种模式；请检查其状态、借用/地址池行为和实际路由，不要不加判断地复用此生成器。

经所有者审查后，手动路由器配置可以类似如下：

```text
# Illustrative syntax after validating the route plan on the intended router:
# Linux
ip route add 10.85.0.0/25 via 10.80.1.10
# Cisco IOS / IOS-XE
ip route 10.85.0.0 255.255.255.128 10.80.1.10 name hybrid-node-001-pods
# FRR
ip route 10.85.0.0/25 10.80.1.10
```

请通过实际的网络管理器/设备配置持久化更改。`up ip route ...` 行属于 ifupdown 配置段，而不是独立的 Bash 脚本，也不适用于所有现代 Linux 网络管理器。静态路由需要漂移/故障跟踪；原先的“1–5 个节点”阈值是规划经验值，并非技术限制。

### 选项 3：ARP 代理

AWS 将代理 ARP 描述为一种可选的 L2 方案。它需要适当的链路上邻居发现行为，以及经过专门配置的 CNI/主机实现；仅启用通用 Cilium 并不能证明此路径已就绪。

![经验证的 L2/链路上设计中的代理 ARP 概念；仍需要上游路由。](../.gitbook/assets/en-eks-hybrid-nodes-02-network-configuration-3.png)

[🔍 查看交互式图示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-02-network-configuration-3.html)

ARP 广播不会穿过 TGW/VPN/DX 三层路由。此选项并不会消除 VPC/WAN 返回路由要求。在替换 BGP/静态路由设计前，请验证实际的 L2 行为和故障转移。

## 网络策略

策略取决于选择器、方向和实施策略的数据平面。Kubernetes NetworkPolicy 的允许规则是累加的：其他匹配策略也可能放行流量。Cilium 显式拒绝和 L7 行为需要单独评估。以下示例是供受控命名空间测试的替代方案，并非要求叠加所有允许规则并期待行为变得更严格。

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

此策略选择 `reviews` 的入站流量，并允许同一命名空间中匹配的 `productpage` Pod 使用 TCP9080 端口。它不会隔离所有 Pod/方向，也不会覆盖其他所有策略。

### CiliumNetworkPolicy 和 L7

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

HTTP 规则是对不受限制的 L4 允许规则的替代方案，并不会自动叠加在其上以实现限制。请使用实际的应用路径。HTTP 检查需要适当的可见性；加密的网格/TLS 流量不会自动变得可检查。

### 基于 DNS 的出站流量

单独的 `external-api-client` 示例允许通过 **Cilium 识别的 CoreDNS Pod** 进行 DNS 查询，并通过 HTTPS 访问已观测到的 API 地址：

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

请验证实际的解析器/身份布局。NodeLocal DNS、主机 DNS 或非 Cilium 管理的端点可能需要使用其他受支持的规则。FQDN IP 观测不能替代远程 API 身份验证；请考虑 DNS 缓存和共享地址。Cilium 专用的 L7/FQDN 功能也超出了 AWS 列出的默认 Kubernetes NetworkPolicy 支持范围。

## Webhook 配置

常规的直接路由设计要求控制平面能够访问 Webhook Pod IP。如果没有合适的 Pod 返回路径，请使用部署位置适当且托管在云端的组件。请单独验证其他网关/代理设计。

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

这是 Pod 模板亲和性片段，不是完整的 Deployment。`NotIn hybrid` 条件并不能证明存在匹配的健康云端容量，也不能证明其他所有调度约束都满足。

AWS Load Balancer Controller、CloudWatch/ADOT Operator 和 cert-manager 都有 Webhook 部署位置要求。请将它们的 Operator 与节点采集器区分开。**Metrics Server 是聚合 API Service，不是准入 Webhook**，但仍需要控制平面到 Pod 的可达性。请测试实际 API 调用和 Webhook，而不只是检查 Pod 状态。

## 只读连接诊断

### Kubernetes API TLS 和计时

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

必须验证集群 CA 和主机名。HTTP401/403 响应可以证明 TLS 端点可达，但授权缺失；它并不代表应用健康检查成功。Curl 计时字段是累积阶段时间，并非纯 RTT 测量。ICMP ping 没有收到响应，并不能证明 EKS API 已宕机。

### VPN 状态和指标

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

`available` 是 VPN 资源状态，不是隧道健康状态。TunnelState 在 UP/static 或 ESTABLISHED/BGP 时为 1，在其他状态时为 0；聚合值可能是小数。应将缺失数据与 DOWN 状态区分开，并验证两条隧道、路由和实际工作负载行为。此查询不会输出客户网关配置/预共享密钥。

AWS 的一般连接建议为**带宽 100 Mbps，RTT 不超过 200ms**。选择 VPN 或 Direct Connect 时，除线路标称带宽外，还应评估实际往返延迟、数据包丢失、故障转移路径和工作负载响应时间。

## 参考资料

- [混合网络](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
- [EKS PrivateLink：管理、OIDC 和控制台端点](https://docs.aws.amazon.com/eks/latest/userguide/vpc-interface-endpoints.html)
- [S3 接口端点和私有 DNS](https://docs.aws.amazon.com/AmazonS3/latest/userguide/privatelink-interface-endpoints.html)
- [Roles Anywhere 端点策略](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/vpc-interface-endpoints.html)
- [当前混合 CNI 支持情况](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [AWS 混合 BGP 操作步骤](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cilium-bgp.html)
- [混合模式 DNS 和 Webhook](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-webhooks.html)
- [混合路由概念](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-concepts-kubernetes.html)
- [混合流量流参考](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-concepts-traffic-flows.html)
- [Cilium 1.18.3 路由源文件](https://github.com/cilium/cilium/blob/v1.18.3/Documentation/network/concepts/routing.rst)
- [Cilium 1.18.3 DNS 策略源文件](https://github.com/cilium/cilium/blob/v1.18.3/Documentation/security/dns.rst)
- [RFC6996 私有 ASN](https://www.rfc-editor.org/rfc/rfc6996.html)
- [RouterOS BGP 参考](https://help.mikrotik.com/docs/spaces/ROS/pages/328220/BGP)
- [FRR 10.7.1 BGP 参考源文件](https://github.com/FRRouting/frr/blob/frr-10.7.1/doc/user/bgp.rst)
- [VPN 指标](https://docs.aws.amazon.com/vpn/latest/s2svpn/monitoring-cloudwatch-vpn.html)
- [Kubernetes 1.36.5 kubelet Server 源文件](https://github.com/kubernetes/kubernetes/blob/v1.36.5/pkg/kubelet/server/server.go)
- [Kubernetes NetworkPolicy 语义](https://kubernetes.io/docs/concepts/services-networking/network-policies/)


< [上一篇：先决条件](01-prerequisites.md) | [目录](./README.md) | [下一篇：受限互联网设置](03-airgap-setup.md) >
