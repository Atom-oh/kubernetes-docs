# EKS 网络测验 - 第 2 部分

> **最后更新**: October 12, 2026

这些答案使用[第 2 部分](../../eks/03-eks-networking-part2.md)中的控制器所有权和前提条件：LBC 3.5.0 和 Gateway API 1.6.0。命令是运行时会更改资源的示例；本地 schema/mock 测试不构成 EKS 部署。请替换账户/Region/资源占位符，使用预期的 kubeconfig，并保留平台对 IAM/Helm/IaC 的所有权。

### 1. 对于 Kubernetes Ingress 资源，AWS Load Balancer Controller 默认预置哪种类型的 AWS 负载均衡器？

A. Classic Load Balancer (CLB) B. Network Load Balancer (NLB) C. Application Load Balancer (ALB) D. Gateway Load Balancer (GWLB)

<details>

<summary>显示答案</summary>

**答案：C. Application Load Balancer (ALB)**

**说明：** 对于 Kubernetes Ingress 资源，AWS Load Balancer Controller 默认预置 Application Load Balancer (ALB)。ALB 是第 7 层负载均衡器，处理 HTTP/HTTPS 流量，并提供基于路径的路由、基于主机的路由和 TLS 终止等功能，以满足 Ingress 资源的要求。

LBC 必须选择 Ingress class；其他控制器可以采用不同方式实现 Ingress。以下 public scheme 要求有经过明确配置的公有子网、客户端 SG 访问权限和就绪的后端 Service。

**主要功能：**

1. **基于路径的路由：** ALB 可以根据 URL 路径将流量路由到不同的服务，因此适合在 Ingress 中实现基于路径的路由规则。
2. **基于主机的路由：** 单个 ALB 可以处理多个域名，支持具有多个主机规则的 Ingress。
3. **TLS 终止：** ALB 可以管理 SSL/TLS 证书并终止 HTTPS 流量。
4. **WebSockets 支持：** ALB 支持 WebSockets 协议，适用于实时应用程序。
5. **身份验证集成：** 可以与 Amazon Cognito 或 OIDC 集成，提供应用程序级身份验证。

**配置示例：**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
spec:
  ingressClassName: alb
  rules:
  - host: example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
```

**关键注释：**

* `spec.ingressClassName: alb`：选择控制器为 `ingress.k8s.aws/alb` 的 IngressClass
* `alb.ingress.kubernetes.io/scheme: internet-facing`：创建面向互联网的 ALB
* `alb.ingress.kubernetes.io/target-type: ip`：使用 Pod IP 作为目标（而非 instance）
* `alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'`：配置监听器端口
* `alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account-id:certificate/certificate-id`：指定 SSL 证书

其他选项的问题：

* **A. Classic Load Balancer (CLB)：** AWS Load Balancer Controller 不会将 CLB 用于 Ingress 资源。CLB 被视为旧版负载均衡器。
* **B. Network Load Balancer (NLB)：** NLB 主要用于 Service 类型 LoadBalancer，默认不用于 Ingress 资源。
* **D. Gateway Load Balancer (GWLB)：** GWLB 用于网络虚拟设备，不与 Kubernetes Ingress 资源配合使用。

</details>

### 2. 哪个 Ingress 注释用于选择内部 ALB？

- A. Service 注释 `aws-load-balancer-internal`
- B. Ingress 注释 `alb.ingress.kubernetes.io/scheme: internal`
- C. 任意名为 `internal-alb` 的 class
- D. `aws-load-balancer-type: internal`

<details>
<summary>显示答案</summary>

**答案：B. `alb.ingress.kubernetes.io/scheme: internal`**

内部 ALB 使用私有地址。当路由、DNS 和安全控制允许时，连接的 VPC 或本地网络中的已路由客户端也可访问它；按定义，它并不限于 Pod 或其自身 VPC。
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: internal-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
spec:
  ingressClassName: alb
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: internal-service
            port:
              number: 80
```
子网发现或显式子网 ID 会选择放置位置；SG 控制访问。`inbound-cidrs` 配置由控制器创建的前端 SG，但在提供自定义 SG 时会被忽略。必须单独创建 Route 53 私有 alias/CNAME；ALB 日志属性不会创建 DNS 记录。当存在实际匹配的 IngressClass/控制器配置时，可以使用如 `internal-alb` 的自定义 IngressClass 名称，但仅凭名称不会选择 scheme。

</details>

### 3. 哪个 Ingress 注释用于选择 Pod IP 目标？

- A. `target-type: pod`
- B. `alb.ingress.kubernetes.io/target-type: ip`
- C. `service.beta.kubernetes.io/aws-load-balancer-target-type: ip`
- D. `aws-load-balancer-target-node-labels: ip-mode=true`

<details>
<summary>显示答案</summary>

**答案：B. `alb.ingress.kubernetes.io/target-type: ip`**

`ip` 会注册可路由的 Pod IP 和已解析的 Service 目标端口。`instance` 通常注册节点和 NodePort（受控制器/IngressClass 默认值约束）。EKS Fargate 要求使用 IP 目标。选择 IP 目标本身不会创建 Pod security group、消除节点故障或保证更高性能。
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ip-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
spec:
  ingressClassName: alb
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: example-service
            port:
              number: 80
```
| 属性 | IP 目标 | Instance 目标 |
|---|---|---|
| 路径 | LB → Pod 目标 | LB → NodePort → 选定的 endpoint |
| 节点故障 | 故障节点上的 Pod 会丢失；健康检查/协调将收敛 | 故障节点目标会被移除；其他健康节点可以保留 |
| Service 类型 | ClusterIP 已足够 | 使用已分配 NodePort 的 NodePort 或 LoadBalancer |
| Fargate | 支持的路径 | 无 EC2 NodePort 目标 |

使用 VPC 可路由的 Pod 网络，并允许应用程序和健康检查流量。原生 VPC CNI 是常规的 EC2 路径；受支持的混合/网络设计需要自行验证其可达性。`service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip` 是对应的 NLB Service 注释；省略 `nlb` 的选项不是正确注释。

</details>

### 4. NLB-IP 注释会创建 PrivateLink endpoint service 吗？

- A. 任何 `LoadBalancer` Service 都会创建 PrivateLink
- B. `nlb-ip` 会自动创建并授权它
- C. 单独配置 NLB、endpoint service 和消费者
- D. 只有 instance 目标可以使用 PrivateLink

<details>
<summary>显示答案</summary>

**答案：C. 不会；请分别创建 NLB、endpoint-service 配置和消费者访问权限。**

原先的 `nlb-ip` 答案混淆了目标选择和 PrivateLink 预置。endpoint service 使用 NLB（或用于设备的 GWLB）；它不要求 IP 目标或内部 NLB。此示例刻意选择内部 IP-target NLB 来私有访问 Pod。
```yaml
apiVersion: v1
kind: Service
metadata:
  name: privatelink-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
spec:
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  allocateLoadBalancerNodePorts: false
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
```
在预期的 namespace 中创建此 Service，并确保匹配的 Pod 已就绪后等待 NLB。请按精确 DNSName 识别它，而非按连字符拆分其 hostname：
```bash
set -euo pipefail
: "${AWS_REGION:?Set the provider Region}"
: "${SERVICE_NAMESPACE:?Set the Service namespace}"
NLB_DNS=$(kubectl -n "$SERVICE_NAMESPACE" get service privatelink-service \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
test -n "$NLB_DNS"
aws elbv2 describe-load-balancers --region "$AWS_REGION" --output json > privatelink-load-balancers.json
NLB_ARN=$(python3 - "$NLB_DNS" <<'PY'
import json, sys
with open("privatelink-load-balancers.json") as stream:
    matches = [lb for lb in json.load(stream)["LoadBalancers"]
               if lb["DNSName"] == sys.argv[1] and lb["Type"] == "network"]
if len(matches) != 1:
    raise SystemExit("Expected exactly one matching NLB; check Region, account and readiness")
print(matches[0]["LoadBalancerArn"])
PY
)
printf '%s\n' "$NLB_ARN"
```
以下提供方命令会创建需付费资源，并向一个消费者账户授予 endpoint-service 访问权限。请在经过审查的基础设施所有者身份下运行，记录返回的 ID，并避免把创建操作当作幂等操作反复运行。本示例适用于商业 AWS 分区；对于其他分区，请调整 ARN。
```bash
set -euo pipefail
: "${AWS_REGION:?Set the provider Region}"
: "${NLB_ARN:?Use the NLB ARN verified above}"
: "${CONSUMER_ACCOUNT_ID:?Set the allowed consumer account}"
aws ec2 create-vpc-endpoint-service-configuration \
  --region "$AWS_REGION" --network-load-balancer-arns "$NLB_ARN" \
  --acceptance-required --output json > endpoint-service-created.json
SERVICE_ID=$(python3 -c 'import json; print(json.load(open("endpoint-service-created.json"))["ServiceConfiguration"]["ServiceId"])')
SERVICE_NAME=$(python3 -c 'import json; print(json.load(open("endpoint-service-created.json"))["ServiceConfiguration"]["ServiceName"])')
aws ec2 modify-vpc-endpoint-service-permissions \
  --region "$AWS_REGION" --service-id "$SERVICE_ID" \
  --add-allowed-principals "arn:aws:iam::$CONSUMER_ACCOUNT_ID:root"
printf 'Service name: %s\n' "$SERVICE_NAME"
```
在消费者账户中，选择受支持的 AZ（跨账户比较 AZ ID）、允许预期客户端的 endpoint SG，以及精确的返回 service name。这个同 Region 示例不配置跨 Region PrivateLink。
```bash
set -euo pipefail
: "${CONSUMER_REGION:?Set the consumer Region}"
: "${CONSUMER_VPC_ID:?Set the consumer VPC}"
: "${CONSUMER_SUBNET_A:?Set a subnet in an available service AZ}"
: "${CONSUMER_SUBNET_B:?Set another supported AZ subnet}"
: "${CONSUMER_SG_ID:?Set the endpoint security group}"
: "${SERVICE_NAME:?Copy the exact name returned by the provider}"
aws ec2 create-vpc-endpoint \
  --region "$CONSUMER_REGION" --vpc-id "$CONSUMER_VPC_ID" \
  --service-name "$SERVICE_NAME" --vpc-endpoint-type Interface \
  --subnet-ids "$CONSUMER_SUBNET_A" "$CONSUMER_SUBNET_B" \
  --security-group-ids "$CONSUMER_SG_ID"
```
由于要求接受，提供方必须接受特定的待处理 endpoint 请求。可选的 private DNS 要求在消费者启用它之前验证域名所有权。验证健康目标、endpoint 状态和应用程序身份验证。目标处的 PrivateLink 源 IP 是 NLB 地址；如果后端理解，Proxy Protocol v2 可以携带消费者元数据。它不会自动满足合规要求，也不会授权应用程序请求。通过各自的所有者停用消费者 endpoint、endpoint-service 关联和 Kubernetes 负载均衡器资源。

</details>

### 5. 哪个额外的 policy engine 可以与 Amazon VPC CNI 配合使用？

- A. AWS Network Firewall
- B. Calico
- C. Security Groups for Pods
- D. VPC Flow Logs

<details>
<summary>显示答案</summary>

**答案：B. Calico**

在 VPC CNI 保留 IPAM/网络功能时，Calico 可以实施策略。它是原生 VPC CNI policy engine 的替代方案，而非必需附加组件。请遵循[官方仅策略 EKS 流程](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks)，包括受支持版本、`cni.type: AmazonVPC`、`ANNOTATE_POD_IP` 和所需的 Pod patch 权限。不要同时启用两个 engine，也不要对正在运行的集群应用 VXLAN 替换 manifest。

Calico API 还提供有序/分层规则、GlobalNetworkPolicy、NetworkSet、service-account selector 和 host-endpoint policy。它们的语义与可叠加的 Kubernetes NetworkPolicy 不同；在 Calico policy 引用 NetworkSet 之前，NetworkSet 不会限制流量。全局 allow-all policy 不是最小权限基线。不要假定每种 VPC CNI 模式都兼容：当前 Calico EKS 指南明确排除了在 `ENABLE_V4_EGRESS=true` 的情况下对 IPv6 Pod 的实施。

对于 namespace 自有的 Kubernetes policy 示例，请创建 `policy-lab` 和一个由控制器管理、标签为 `role=frontend` 的 Pod。此 egress policy 只允许常规 CoreDNS 和已批准的 HTTPS 目标，仍受所有其他可叠加策略约束。请将文档 CIDR 替换为真实目标；针对 NodeLocal DNS 调整 DNS。
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-egress
  namespace: policy-lab
spec:
  podSelector:
    matchLabels:
      role: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
  - to:
    - ipBlock:
        cidr: 203.0.113.0/24
    ports:
    - protocol: TCP
      port: 443
```
在依赖实施之前，验证基线连通性以及允许/拒绝的 TCP 路径。NetworkPolicy 没有可移植的仅审计模式。请在可用时使用所选 engine 已记录的日志/暂存功能。SGs for Pods 和 VPC firewall 是独立的控制措施；Flow Logs 观测流量，而不实施此 API。

</details>

### 6. 自定义 ALB 前端 security group 与后端规则有何不同？

<details>
<summary>显示答案</summary>

**答案：`alb.ingress.kubernetes.io/security-groups`**

将此注释片段合并到预期的 Ingress 中。SG ID 没有歧义；名称查找匹配 AWS `Name` tag，而非 EC2 `groupName` 属性。
```yaml
metadata:
  annotations:
    alb.ingress.kubernetes.io/security-groups: sg-0123456789abcdef0
    alb.ingress.kubernetes.io/manage-backend-security-group-rules: "true"
    alb.ingress.kubernetes.io/tags: Environment=training,Team=platform
```
请自行配置自定义前端 inbound/outbound 规则。对于提供的前端 SG，`inbound-cidrs` 和 prefix-list 注释将被忽略。`manage-backend-security-group-rules: "true"` 授权控制器通过其后端 SG 机制管理目标访问；它不会在自定义前端 SG 中创建限制客户端访问的规则。若没有它，请自行安排节点/Pod SG 访问。允许应用程序和健康检查端口，并在目标 ENI 有多个 SG 时审核 SG-selection tag。

发布版 IAM policy 包含整个控制器所需的 EC2/ELB 权限；简短的 SG action 列表不是完整的 role policy。跨信任域复用 SG 会扩大暴露面并增加变更耦合。审核实际规则和 VPC Flow Log 拒绝记录。`tags` 会添加受支持的资源 tag；`load_balancing.cross_zone.enabled` 是均衡属性，而非 tag。应根据客户端兼容性和要求选择受支持的 TLS security policy，而不要将旧 policy name 作为当前指南照搬。

</details>

### 7. 如何配置 NLB 客户端 IP 保留，其限制是什么？

<details>
<summary>显示答案</summary>

**答案：`service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true`**

对于 TCP/TLS target group，该属性可配置：instance 目标默认启用，IP 目标默认禁用。UDP/TCP_UDP/QUIC/TCP_QUIC target group 始终保留客户端 IP，且无法禁用。此 IPv4 IP-target TCP 示例会更改可配置的情况：
```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
spec:
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  allocateLoadBalancerNodePorts: false
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
```
应用程序看到的地址仍取决于完整路径。除非本地流量 policy/拓扑保留它，否则 NodePort 转发可能会 SNAT；ALB 使用 HTTP forwarded header；IPv6 到 IPv4 的转换和 PrivateLink 不会保留原始数据包源地址。保留要求支持的直接同 VPC 或同 Region peering 路径，并且无法通过 transit gateway 工作。回到同一已注册目标的内部 NLB hairpin 连接可能失败。

Proxy Protocol v2 可以传递原始地址元数据，但需要兼容的 listener/parser；不要盲目启用它。框架 `remote_addr` 或 TCP `RemoteAddr()` 报告的是直接对等方，而非自动报告原始互联网客户端。只信任来自显式可信 proxy 的 forwarded header。更改保留设置会影响新的 TCP 连接。`deregistration_delay.timeout_seconds` 控制排空，而非 TCP keep-alive。通过测量性能，而不是指定没有支持依据的开销值。

</details>

### 8. AWS WAF 如何附加到由 LBC 管理的 ALB？

<details>
<summary>显示答案</summary>

**答案：对于同 Region 的 REGIONAL Web ACL，使用 `alb.ingress.kubernetes.io/wafv2-acl-arn`。**

使用真实的 `regional/webacl/...` ARN。CloudFront `global/webacl/...` ARN 无法附加到区域 ALB。关联会保护经过该 ALB 的流量；它不会将 WAF 附加到 Pod、NLB 或 Kubernetes API server。
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: waf-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:us-west-2:123456789012:regional/webacl/eks-ingress-protection/00000000-0000-4000-8000-000000000000
spec:
  ingressClassName: alb
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: example-service
            port:
              number: 80
```
默认 Allow 的空 Web ACL 不会阻止任何内容。对于隔离的规则开发示例，请将以下数组保存为 `waf-rules.json`。此规则对 `/admin` 前缀进行**计数**而非阻止；它不是身份验证控制，也不是完整的 managed-rule 基线。
```json
[
  {
    "Name": "count-admin-path",
    "Priority": 1,
    "Action": {
      "Count": {}
    },
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "count-admin-path"
    },
    "Statement": {
      "ByteMatchStatement": {
        "SearchString": "/admin",
        "FieldToMatch": {
          "UriPath": {}
        },
        "TextTransformations": [
          {
            "Priority": 0,
            "Type": "NONE"
          }
        ],
        "PositionalConstraint": "STARTS_WITH"
      }
    }
  }
]
```
安全所有者可以使用以下命令创建该训练 ACL；关联时使用其返回的 ARN。binary-format flag 使 JSON SearchString 在 AWS CLI v2 中成为字面字节。
```bash
set -euo pipefail
: "${AWS_REGION:?Set the ALB Region}"
aws wafv2 create-web-acl --region "$AWS_REGION" \
  --name eks-ingress-training --scope REGIONAL \
  --default-action '{"Allow":{}}' --rules file://waf-rules.json \
  --cli-binary-format raw-in-base64-out \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=eks-ingress-training
```
Managed SQLi/XSS、bot、reputation、rate-based 和 custom rule 只有在配置和调优后才提供各自的保护；费用/功能各不相同。在启用实施前，于 Count 模式中审查误报。规则计数时，默认 Allow 仍然宽松。

ALB `access_logs.s3.*` 属性配置的是 S3 中的 ALB access log，而非 WAF log 或 CloudWatch Logs。请单独使用已批准的 CloudWatch Logs/S3/Firehose 目标和所需权限配置 WAF logging；sampled request 和 CloudWatch metric 与完整请求日志分开。关联请使用经过审查的发布版 controller IAM policy，ACL 创建/规则/logging 请使用单独的 security-administration role。在受支持的位置限定资源权限；不要粘贴不受约束的独立 wildcard policy 作为完整 controller role。

</details>

### 9. 为三个可区分的后端构建并验证路径路由。

<details>
<summary>显示答案</summary>

**答案：Ingress + ClusterIP Service + 就绪的 HTTP workload。**

前提条件：具有经过审查的 IAM/子网的 LBC、可路由的私有测试客户端、受你控制的 hostname 的 ACM 证书，以及创建专用 namespace 的权限。此示例创建内部 ALB；`/admin` 只是路由标签，没有身份验证。它是有限的培训练习，不是生产就绪性证据。请在一个 shell 中以 `set -euo pipefail` 运行各代码块；在清理前保留 LAB_NS/LAB_UID。
```bash
set -euo pipefail
LAB_NS="alb-paths-$(date -u +%Y%m%d%H%M%S)-$RANDOM"
kubectl create namespace "$LAB_NS"
LAB_UID=$(kubectl get namespace "$LAB_NS" -o jsonpath='{.metadata.uid}')
test -n "$LAB_UID"
kubectl label namespace "$LAB_NS" \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/enforce-version=v1.36
printf 'Namespace: %s UID: %s\n' "$LAB_NS" "$LAB_UID"
```
HTTP server 确实在 8080 上监听，并通过其后端名称响应 `/health` 及所有请求路径。仅声明 `containerPort: 8080` 不会重新配置默认 nginx server。可变的 Python tag 是示例运行时；为可重复使用，请固定已批准的 image digest。
```bash
for APP in api admin frontend; do
  kubectl -n "$LAB_NS" apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $APP
spec:
  replicas: 2
  selector:
    matchLabels:
      app: $APP
  template:
    metadata:
      labels:
        app: $APP
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: http
        image: python:3.13-alpine
        command: ["python", "-u", "-c"]
        args:
        - |
          import os
          from http.server import BaseHTTPRequestHandler, HTTPServer
          class Handler(BaseHTTPRequestHandler):
              def do_GET(self):
                  self.send_response(200)
                  self.end_headers()
                  self.wfile.write((os.environ["APP_NAME"] + "\\n").encode())
          HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
        env:
        - name: APP_NAME
          value: $APP
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: http
        resources:
          requests:
            cpu: 50m
            memory: 32Mi
          limits:
            cpu: 200m
            memory: 64Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop: ["ALL"]
---
apiVersion: v1
kind: Service
metadata:
  name: $APP-service
spec:
  type: ClusterIP
  selector:
    app: $APP
  ports:
  - port: 80
    targetPort: http
EOF
  kubectl -n "$LAB_NS" rollout status "deployment/$APP" --timeout=180s
done
```

```bash
set -euo pipefail
: "${LAB_NS:?Run the namespace setup first}"
: "${LAB_HOST:?Set a DNS hostname you control, for example app.example.com}"
: "${ACM_CERT_ARN:?Set a matching certificate ARN in the ALB Region}"
: "${CLIENT_CIDR:?Set the permitted private client CIDR}"
kubectl -n "$LAB_NS" apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: multi-path-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/inbound-cidrs: "$CLIENT_CIDR"
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP":80},{"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: "$ACM_CERT_ARN"
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/healthcheck-path: /health
spec:
  ingressClassName: alb
  rules:
  - host: "$LAB_HOST"
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
      - path: /admin
        pathType: Prefix
        backend:
          service:
            name: admin-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
EOF
kubectl -n "$LAB_NS" get ingress multi-path-ingress
kubectl -n "$LAB_NS" get endpointslices
```
等待 ALB hostname、健康目标和控制器协调完成。若失败，请检查 Ingress event、controller log、EndpointSlice 和 SG/health-check 路径。从获准的私有客户端发起时，此测试会在直接连接 ALB hostname 的同时保留 Host header 和 TLS SNI；它不要求 DNS 记录，也不会禁用证书验证。
```bash
ALB_DNS=$(kubectl -n "$LAB_NS" get ingress multi-path-ingress \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
test -n "$ALB_DNS"
for ROUTE in api admin frontend; do
  URL_PATH="/$ROUTE"
  test "$ROUTE" != frontend || URL_PATH=/
  RESPONSE=$(curl --fail --show-error --silent --max-time 15 \
    --connect-to "$LAB_HOST:443:$ALB_DNS:443" "https://$LAB_HOST$URL_PATH")
  test "$RESPONSE" = "$ROUTE" || { printf 'Unexpected backend: %s\n' "$RESPONSE"; exit 1; }
done
```
对于持久 DNS，请创建适当的 Route 53 alias；CNAME 可用于子域，但不能用于 zone apex。不要使用 public CA 占位 ARN 或 `curl -k` 来隐藏证书不匹配。

可选的 weighted routing 是一个针对现有 `service-v1`/`service-v2` 后端的独立示例。该 action 必须由 `use-annotation` 后端引用；仅添加 action 注释没有任何效果。请在预期的 namespace 中运行，并避免路由冲突。
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: weighted-ingress
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/actions.weighted-routing: >-
      {"type":"forward","forwardConfig":{"targetGroups":[{"serviceName":"service-v1","servicePort":"80","weight":80},{"serviceName":"service-v2","servicePort":"80","weight":20}]}}
spec:
  ingressClassName: alb
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: weighted-routing
            port:
              name: use-annotation
```
检查已保存的 UID 后，仅清理本练习的 namespace。在删除 namespace 前，让 LBC 移除 Ingress 负载均衡器。如果终结失败，请诊断 controller/IAM/deletion-protection 状态；不要强制移除 finalizer。此代码块不会删除共享的 certificate、controller role 和 DNS record。
```bash
set -euo pipefail
: "${LAB_NS:?Use the namespace from this exercise}"
: "${LAB_UID:?Use the UID saved when that namespace was created}"
case "$LAB_NS" in alb-paths-*) ;; *) echo "Unexpected namespace"; exit 1 ;; esac
CURRENT_UID=$(kubectl get namespace "$LAB_NS" -o jsonpath='{.metadata.uid}')
test "$CURRENT_UID" = "$LAB_UID" || { echo "Namespace identity changed"; exit 1; }
kubectl -n "$LAB_NS" delete ingress multi-path-ingress --ignore-not-found --wait=true --timeout=300s
kubectl delete namespace "$LAB_NS" --wait=true --timeout=300s
```

</details>

### 10. service mesh 如何改变 EKS 网络，必须验证什么？

<details>
<summary>显示答案</summary>

**答案：它会在兼容的 Pod 网络之上增加流量/安全/遥测处理。**

control plane 分发配置和 workload identity；data-plane proxy 处理已加入的流量。在 sidecar 设计中，应用程序和 proxy 共享**相同的 Pod network namespace/IP**。sidecar 本身不会消耗另一个 VPC IP 或 ENI。额外的 mesh gateway/control-plane Pod 会消耗资源/IP。Ambient 设计改用节点 proxy 和可选的 waypoint，因此“每个 Pod 都有一个 sidecar”并非普遍情况。
```text
Client application → client proxy → Pod network → destination proxy → destination application
```
这是一条逻辑 sidecar 路径，并不保证每个数据包都经过 Service virtual IP 或都被拦截。排除的端口、UDP、host-network 流量、namespace 加入和模式都会产生影响。VPC route、SG 和 NetworkPolicy 仍然适用。L3/L4 policy 必须允许所需的 data-plane、DNS、control-plane 和 health path；mTLS 对 mesh peer 进行身份验证/加密，但不能替代应用程序授权。

对于 Istio，请为计算类型选择一种有文档记录的 sidecar/ambient 安装。Fargate 无法运行某些模式所需的节点 DaemonSet/特权组件；请验证支持情况，不要声称通用兼容。不要在一个 namespace 上启用两个 mesh injector。应通过受支持的 Helm/安装/workload 设置配置 proxy 资源，而不是用无关的 `pilot.resources` 覆盖 injector ConfigMap。请将 Prometheus/tracing 部署和 mesh export 配置分开；已移除的 `IstioOperator.addonComponents.prometheus` 和虚构的 App Mesh `Mesh.spec.tracing` 不是可用的安装方案。

**历史比较：** AWS 已于 **September 30, 2026** 结束 App Mesh 支持；其 console 和资源不再可用。现有 App Mesh 部署必须迁移；不要将它作为新的 EKS 默认方案引入。其历史 Fargate 集成并不保证未来支持。ECS Service Connect 是 ECS 选项，而非直接的 EKS 替代方案。请使用受支持的 EKS mesh/data-plane 设计，并验证路由、重试、证书、授权、tracing 和故障处理方面的功能对等性。

原先“通常 <10 ms”延迟和“10–15%”CPU/内存开销数字在本文档中没有经过验证的测量来源。它们在此仅保留为**未经验证的历史估计**，而非基准或容量保证。请在加入前后使用相同的请求组合、TLS、遥测采样和负载，测量 p50/p95/p99 延迟、吞吐量、错误和 CPU/内存。包括 proxy rollout、节点丢失、control-plane 丢失、证书轮换和重试放大测试。

在专用 namespace 中逐步采用，验证一个 injector、就绪 workload、mTLS 和正向/负向 policy 测试，然后再扩展。对于 mesh ingress gateway 前的 LBC，请公开 gateway Service 并验证目标端口/probe；Ingress API object 是配置，而不是另一个 proxy hop。按需使用范围受限的 controller IAM；`cloudmap:*` 不是 `servicediscovery` IAM service prefix 的有效替代。prefix delegation 是 IP 容量设计选择，而非 sidecar 前提条件。有关实现，请参阅持续维护的 [Istio 安装](../../service-mesh/istio/01-installation.md) 和 [AWS 集成](../../service-mesh/istio/04-aws-integration.md)章节。

</details>

### 11. Kubernetes Gateway API 中用于 L7 负载均衡 (ALB) 的路由资源是什么？

A. IngressRoute B. HTTPRoute C. VirtualService D. ServiceRoute

<details>

<summary>显示答案</summary>

**答案：B. HTTPRoute**

**说明：** 在 Kubernetes Gateway API 中，HTTPRoute 资源用于 L7 负载均衡。HTTPRoute 定义将 HTTP/HTTPS 流量路由到服务的规则，并且在与 AWS Load Balancer Controller 配合使用时，它会通过 ALB 分配流量。

**Gateway API 资源层次结构：**

1. **GatewayClass**：定义负载均衡器类型（例如 `amazon-alb`、`amazon-nlb`）
2. **Gateway**：实际的负载均衡器实例（监听器端口、TLS 设置等）
3. **HTTPRoute**：L7 路由规则（主机、路径、基于 header 的路由）
4. **TCPRoute**：L4 路由规则（TCP 流量）

LBC 使用独立的 ALB 和 NLB Gateway；controllerName 选择实现，而非任意 GatewayClass object 名称。请在发布版 conformance table 中确认受支持的 filter。

**HTTPRoute 主要功能：**

* 基于路径和主机的路由
* 原生基于权重的流量拆分
* header 和 query parameter 匹配
* 路由到多个后端 Service

其他选项的问题：

* **A. IngressRoute：** 这不是标准 Gateway API 资源。
* **C. VirtualService：** 这是 Istio service mesh 的资源。
* **D. ServiceRoute：** 此资源不存在。

</details>

### 12. 如何启用 LBC 3.5.0 Gateway controller？

- A. 始终传递 `--enable-gateway-api`
- B. 使用真正默认启用的 gate 检测兼容的 CRD
- C. 使用 `--feature-gates=EnableGatewayAPI=true`
- D. 仅从 1.2.1 安装 experimental CRD

<details>
<summary>显示答案</summary>

**答案：B. 检测所需 CRD；ALBGatewayAPI/NLBGatewayAPI 默认启用。**

安装与发布版兼容的 Gateway API 1.6.0 standard CRD 和 LBC 专用 Gateway CRD。默认 gate 是 `ALBGatewayAPI` 和 `NLBGatewayAPI`；`EnableGatewayAPI` 是未知 feature name。TCPRoute/UDPRoute 现在在 standard channel 中以 v1 提供服务。早期控制器发布版有不同的兼容性/gating 要求：L4 支持从 2.13.3 开始，L7 从 2.14.0 开始。在安装 CRD 后检查 controller startup/log；仅有 CRD 不提供 IAM、子网或应用程序后端。

</details>

### 13. Gateway API 中用于通过 NLB 路由 L4 级 TCP 流量的资源是什么？

A. HTTPRoute B. TLSRoute C. TCPRoute D. GRPCRoute

<details>
<summary>显示答案</summary>

**答案：C. TCPRoute**

**说明：** 在 Gateway API 中，TCPRoute 资源用于路由 L4 级 TCP 流量。与 AWS Load Balancer Controller 配合使用时，TCPRoute 通过 NLB (Network Load Balancer) 将 TCP 流量转发到后端服务。

**TCPRoute 配置示例：**

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: TCPRoute
metadata:
  name: db-route
  namespace: gateway-demo
spec:
  parentRefs:
  - name: my-nlb-gateway
    sectionName: tcp
  rules:
  - backendRefs:
    - name: postgres-service
      port: 5432
```

**Gateway API 路由资源用法：**

| 资源 | 协议 | AWS LB 类型 |
| --------- | ---------- | ----------- |
| HTTPRoute | HTTP/HTTPS | ALB         |
| TCPRoute  | TCP        | NLB         |
| TLSRoute  | TLS        | NLB         |
| GRPCRoute | gRPC       | ALB         |

其他选项的问题：

* **A. HTTPRoute：** 与 ALB 配合用于 HTTP/HTTPS L7 流量。
* **B. TLSRoute：** 用于 TLS 流量路由，但 TCPRoute 适用于 TCP 级路由。
* **D. GRPCRoute：** 专门用于 gRPC 协议的路由资源。

</details>
`my-nlb-gateway` listener 和后端 Service 必须存在于 `gateway-demo` 中。此实现中的 TLSRoute 不提供基于 SNI 的 NLB 路由；请使用发布版特定的 TLS 行为，而不要假定所有 Gateway API 实现的行为都相同。

### 14. LBC 3.5.0 如何为 ALB Gateway 配置静态证书？

- A. 创建任意名为 tls-cert 的 Secret
- B. 在 LoadBalancerConfiguration 中使用 ACM ARN
- C. 仅添加一个 Route hostname
- D. 设置后端 Service 端口 443

<details>
<summary>显示答案</summary>

**答案：B. `LoadBalancerConfiguration.spec.listenerConfigurations[].defaultCertificate`**

为 HTTPS listener 使用有效的同 Region ACM 证书 ARN。此实现不支持 Kubernetes Secret `certificateRefs`。hostname 发现还需要现有的匹配 ACM 证书和安全 listener。仅使用后端端口为 443 的 HTTPRoute 不会配置客户端 HTTPS。

</details>

### 15. 仅前端 ingress policy 会缩小现有的同 namespace allow-all policy 吗？

- A. 会，最新的 policy 获胜
- B. 会，最具体的 selector 获胜
- C. 不会，匹配的 allow 会形成并集
- D. 仅当 policy name 排序最前时

<details>
<summary>显示答案</summary>

**答案：C. 不会；匹配的 NetworkPolicy allow 是可叠加的。**

两个 policy 都选择后端，因此更宽泛的同 namespace allow 仍允许其他同 namespace 调用方。通过其所有者移除或缩小更宽泛的 policy，然后测试允许和拒绝的连接。Ingress 和 egress 隔离相互独立；DNS egress 和目标 ingress 都可能影响测试结果。

</details>

官方参考资料：[LBC Gateway API](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/gateway/gateway/)、[PrivateLink](https://docs.aws.amazon.com/vpc/latest/privatelink/create-endpoint-service.html)、[NLB 客户端 IP](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/edit-target-group-attributes.html)、[WAF 关联](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-associating-aws-resource.html)、[App Mesh 停用](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html)。
