# EKS Hybrid Nodes 网络配置测验

> **相关文档**: [网络配置](../../eks-hybrid-nodes/02-network-configuration.md)
> **最后更新**: 2026 年 9 月 12 日

## 选择题

### 1. 哪种方案可提供混合环境所需的双向网络路径？

- A) 仅依赖公共互联网访问
- B) 经审核的 Direct Connect/VPN 设计，并配置实际路由和防火墙访问
- C) 仅使用 SSH 隧道
- D) 仅使用 HTTP 代理

<details>
<summary>显示答案</summary>

**答案：B) 经审核的 Direct Connect/VPN 设计，并配置实际路由和防火墙访问**

**说明：**
控制平面必须能够访问 kubelet 和适用的 Pod 端点，节点也必须能够访问 AWS。即使 Kubernetes API 使用公共端点，也仍然需要这条私有反向路径。Direct Connect 本身既不会加密所有连接，也不保证延迟。应确认 VPN 隧道的实际状态，而不能只看资源状态是否为 `available`。相关指南还规定了这些只读诊断所用的账户/上下文和私有 WORK_DIR。
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


</details>

### 2. 节点连接 Kubernetes API 时使用哪个端口？

- A) TCP 22
- B) TCP 443
- C) 默认 TCP 8080
- D) TCP 3306

<details>
<summary>显示答案</summary>

**答案：B) TCP 443**

**说明：**
控制平面到 kubelet 的反向连接使用安全端口 TCP 10250。Webhook 和聚合 API 使用各自配置的端口。不要把未经身份验证的 10255 当作现代环境的必需端口开放。应验证集群 CA 和主机名；HTTP 401/403 可能表示 TLS 可达、但缺少授权，并不代表应用健康。
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


</details>

### 3. 在无互联网设计中，私有 ECR 镜像拉取需要哪些服务？

- A) ecr.api、ecr.dkr，以及合适的私有 S3 镜像层访问路径
- B) 仅需 Lambda、DynamoDB 和 SNS
- C) 仅需 EC2 元数据
- D) 仅需 EKS 管理端点

<details>
<summary>显示答案</summary>

**答案：A) ecr.api、ecr.dkr，以及合适的私有 S3 镜像层访问路径**

**说明：**
凭证提供程序、EKS 管理端点、Kubernetes API 和工作负载服务各有独立要求。私有 ECR 端点不会使公共 ECR/CloudFront 变为私有。S3 接口端点支持私有 DNS；若只通过入站 Resolver 解析，则 VPC 内流量还需要 S3 网关端点。EKS 管理接口端点不是 Kubernetes API 端点；DNS 别名也无法修复与其无关的 TLS 主机名问题。

</details>

### 4. 混合 Pod 地址规划中，哪项不是必需条件？

- A) 地址范围不得与远程节点/VPC/Service 网段重叠
- B) 按实际节点和 Pod 需求规划容量
- C) 每个 Pod 地址池都必须是 /8
- D) 正确隔离不同集群的地址范围并配置返回路由

<details>
<summary>显示答案</summary>

**答案：C) 每个 Pod 地址池都必须是 /8**

**说明：**
在文档规定的远程 CIDR 限制内，支持 IPv4 RFC1918 或 CGNAT 网段。使用 cluster-pool 的 Cilium 部署应在 Cilium 中配置地址池，而不是通过 kubelet 设置一个覆盖整个集群的 Pod CIDR。这里的新地址池示例并非要求修改已分配的现有地址池。应检查实际的 CiliumNode 分配；block 的顺序和可用 Pod 容量都没有保证。
```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.85.0.0/16
    clusterPoolIPv4MaskSize: 25
```


</details>

### 5. 应如何确定集群 DNS 地址？

- A) 始终使用 8.8.8.8
- B) 检查实际的 kube-dns Service，或检查有意配置的本地 DNS 方案
- C) 始终假定地址为 10.100.0.10
- D) 使用 EC2 元数据地址

<details>
<summary>显示答案</summary>

**答案：B) 检查实际的 kube-dns Service，或检查有意配置的本地 DNS 方案**

**说明：**
`10.100.0.10` 只是某个特定 Service CIDR 下的示例。应检查实际的 Service IP、EndpointSlice 和节点解析器配置。仅靠 DNS 部署位置不能保证本地路由；还必须配置 Service Traffic Distribution 和受支持的数据平面。软性的分散调度偏好也不能证明 CoreDNS 已按 2+2 布局。
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


</details>

### 6. 应如何理解 AWS 对混合网络延迟的指导？

- A) 500ms 是保证的上限
- B) RTT 约 200ms 或更低属于一般性指导，仍需根据工作负载验证
- C) 100ms 是普遍适用的严格要求
- D) Direct Connect 始终保证低于 10ms

<details>
<summary>显示答案</summary>

**答案：B) RTT 约 200ms 或更低属于一般性指导，仍需根据工作负载验证**

**说明：**
AWS 也将 100Mbps 作为一般性指导，而不是与工作负载无关的验收门槛。此前采用的 <50/50–100/100–200/>200ms 分级和 Direct Connect <10ms 说法都未经验证。Curl 报告的 DNS、连接和 TLS 时间是逐阶段累计时间，不是纯 RTT；ICMP 无响应也不能证明 API 故障。应实际测量应用、API、镜像和遥测链路的表现。

</details>

## 参考资料

- [混合网络](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
- [EKS PrivateLink](https://docs.aws.amazon.com/eks/latest/userguide/vpc-interface-endpoints.html)
- [S3 私有 DNS](https://docs.aws.amazon.com/AmazonS3/latest/userguide/privatelink-interface-endpoints.html)
- [VPN 指标](https://docs.aws.amazon.com/vpn/latest/s2svpn/monitoring-cloudwatch-vpn.html)
