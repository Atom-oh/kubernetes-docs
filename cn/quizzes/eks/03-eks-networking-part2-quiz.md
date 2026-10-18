# EKS 网络测验 - 第 2 部分

> **最后更新**：October 16, 2026

这些答案采用[第 2 部分](../../eks/03-eks-networking-part2.md)中的控制器所有权和前置条件：LBC 3.6.0 和 Gateway API 1.6.0。命令均为示例，运行时会更改资源；本地 schema/mock 测试不等同于 EKS 部署。请替换账户/Region/资源占位符，使用预期的 kubeconfig，并保留平台对 IAM/Helm/IaC 的所有权。

### 1. 对于 Kubernetes Ingress 资源，AWS Load Balancer Controller 默认会预置哪种类型的 AWS 负载均衡器？

A. Classic Load Balancer (CLB) B. Network Load Balancer (NLB) C. Application Load Balancer (ALB) D. Gateway Load Balancer (GWLB)

<details>

<summary>显示答案</summary>

**答案：C. Application Load Balancer (ALB)**

**说明：**对于 Kubernetes Ingress 资源，AWS Load Balancer Controller 默认会预置 Application Load Balancer (ALB)。ALB 是一个第 7 层负载均衡器，可处理 HTTP/HTTPS 流量，并提供基于路径的路由、基于主机的路由和 TLS 终止等功能，以满足 Ingress 资源的需求。

LBC 必须选择 Ingress 类；其他控制器可以用不同方式实现 Ingress。下面的公开方案要求有意配置公共子网、客户端 SG 访问权限以及就绪的后端 Services。

**主要功能：**

1. **基于路径的路由**：ALB 可以根据 URL 路径将流量路由到不同的服务，因此适用于在 Ingress 中实现基于路径的路由规则。
2. **基于主机的路由**：单个 ALB 可以处理多个域名，支持包含多个主机规则的 Ingress。
3. **TLS 终止**：ALB 可以管理 SSL/TLS 证书并终止 HTTPS 流量。
4. **WebSockets 支持**：ALB 支持 WebSockets 协议，适用于实时应用程序。
5. **身份验证集成**：可以与 Amazon Cognito 或 OIDC 集成，以提供应用程序级身份验证。

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

**主要注解：**

* `spec.ingressClassName: alb`：选择一个 controller 为 `ingress.k8s.aws/alb` 的 IngressClass
* `alb.ingress.kubernetes.io/scheme: internet-facing`：创建面向互联网的 ALB
* `alb.ingress.kubernetes.io/target-type: ip`：使用 Pod IP 作为目标（而不是实例）
* `alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'`：配置侦听器端口
* `alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account-id:certificate/certificate-id`：指定 SSL 证书

其他选项的问题：

* **A. Classic Load Balancer (CLB)**：AWS Load Balancer Controller 不会将 CLB 用于 Ingress 资源。CLB 被视为旧版负载均衡器。
* **B. Network Load Balancer (NLB)**：NLB 主要用于类型为 LoadBalancer 的 Service，默认不用于 Ingress 资源。
* **D. Gateway Load Balancer (GWLB)**：GWLB 用于网络虚拟设备，不用于 Kubernetes Ingress 资源。

</details>

### 2. 哪个 Ingress 注解可以选择内部 ALB？

- A. Service 注解 `aws-load-balancer-internal`
- B. Ingress 注解 `alb.ingress.kubernetes.io/scheme: internal`
- C. 任意名为 `internal-alb` 的类
- D. `aws-load-balancer-type: internal`

<details>
<summary>显示答案</summary>

**答案：B. `alb.ingress.kubernetes.io/scheme: internal`**

内部 ALB 使用私有地址。如果路由、DNS 和安全控制允许，已连接 VPC 或本地网络中的路由客户端也可以访问它；根据定义，它并不只允许 Pod 或自身 VPC 访问。
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
子网发现或显式子网 ID 用于选择部署位置；SG 控制访问。`inbound-cidrs` 用于配置由控制器创建的前端 SG，但在提供自定义 SG 时会被忽略。必须单独创建 Route 53 私有别名/CNAME；ALB 日志属性不会创建 DNS 记录。如果存在实际匹配的 IngressClass/控制器配置，可以使用 `internal-alb` 等自定义 IngressClass 名称，但仅有这个名称并不能选择方案。

</details>

### 3. 哪个 Ingress 注解可以选择 Pod IP 作为目标？

- A. `target-type: pod`
- B. `alb.ingress.kubernetes.io/target-type: ip`
- C. `service.beta.kubernetes.io/aws-load-balancer-target-type: ip`
- D. `aws-load-balancer-target-node-labels: ip-mode=true`

<details>
<summary>显示答案</summary>

**答案：B. `alb.ingress.kubernetes.io/target-type: ip`**

`ip` 会注册可路由的 Pod IP 和解析后的 Service 目标端口。`instance` 通常会注册节点和 NodePort（具体取决于控制器/IngressClass 默认值）。EKS Fargate 必须使用 IP 目标。选择 IP 目标本身不会创建 Pod 安全组、消除节点故障或保证性能更高。
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
| 路径 | LB → Pod 目标 | LB → NodePort → 选定的端点 |
| 节点故障 | 故障节点上的 Pod 会不可用；健康检查/协调过程会逐步收敛 | 故障节点目标会被移除；其他健康节点可以继续使用 |
| Service 类型 | ClusterIP 即可 | NodePort，或分配了 NodePort 的 LoadBalancer |
| Fargate | 支持的方式 | 不支持 EC2 NodePort 目标 |

使用 VPC 可路由的 Pod 网络，并允许应用程序流量和健康检查流量。原生 VPC CNI 是常规的 EC2 方案；受支持的混合/网络设计需要单独验证可达性。`service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip` 是 NLB Service 对应的注解；省略 `nlb` 的选项不是正确注解。

</details>

### 4. NLB-IP 注解会创建 PrivateLink 端点服务吗？

- A. 任何 `LoadBalancer` Service 都会创建 PrivateLink
- B. `nlb-ip` 会自动创建并授权
- C. 分别配置 NLB、端点服务和使用方
- D. 只有 instance 目标可以使用 PrivateLink

<details>
<summary>显示答案</summary>

**答案：C. 不会；需要分别创建 NLB、配置端点服务并设置使用方访问权限。**

原来的 `nlb-ip` 答案混淆了目标选择与 PrivateLink 预置。端点服务使用 NLB（或用于设备的 GWLB）；它不要求使用 IP 目标或内部 NLB。此示例有意选择内部 IP 目标 NLB，以便私有访问 Pod。
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
在预期的命名空间中创建此 Service，并确保匹配的 Pod 已就绪，然后等待 NLB。通过精确的 DNSName 来识别它，不要通过按连字符拆分主机名来识别：
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
以下提供方侧命令会创建计费资源，并向一个使用方账户授予端点服务访问权限。请由经过审核的基础设施所有者执行，记录返回的 ID，并避免将创建操作当作幂等操作而重复运行。此示例适用于 AWS 商业分区；其他分区请相应调整 ARN。
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
在使用方账户中，选择受支持的 AZ（跨账户比较 AZ ID）、允许预期客户端访问的端点 SG，以及返回的精确服务名称。此同 Region 示例未配置跨 Region PrivateLink。
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
由于启用了需要接受请求的设置，提供方必须接受特定的待处理端点请求。可选的私有 DNS 要求先验证域名所有权，之后使用方才能启用它。请验证目标健康状态、端点状态和应用程序身份验证。目标端看到的 PrivateLink 源 IP 是 NLB 地址；如果后端能够处理，Proxy Protocol v2 可以传递使用方元数据。它不会自动满足合规要求，也不会自动授权应用程序请求。请通过各自的所有者来退役使用方端点、端点服务关联和 Kubernetes 负载均衡器资源。

</details>

### 5. 哪个额外的策略引擎可以与 Amazon VPC CNI 配合使用？

- A. AWS Network Firewall
- B. Calico
- C. Security Groups for Pods
- D. VPC Flow Logs

<details>
<summary>显示答案</summary>

**答案：B. Calico**

Calico 可以在 VPC CNI 保留 IPAM/网络功能的同时实施策略。它是 VPC CNI 原生策略引擎的替代方案，不是必需的附加组件。请遵循[官方的仅策略 EKS 操作步骤](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks)，包括受支持的版本、`cni.type: AmazonVPC`、`ANNOTATE_POD_IP` 以及所需的 Pod 修补权限。不要同时启用两个引擎，也不要将 VXLAN 替换清单应用到正在运行的集群。

Calico API 还提供有序/分层规则、GlobalNetworkPolicy、NetworkSet、服务账户选择器和主机端点策略。它们的语义与可叠加的 Kubernetes NetworkPolicy 不同；除非 Calico 策略引用 NetworkSet，否则 NetworkSet 不会限制流量。全局全允许策略不是最小权限基线。不要假设 VPC CNI 的所有模式都兼容：当前 Calico EKS 指南明确排除对启用了 `ENABLE_V4_EGRESS=true` 的 IPv6 Pod 实施策略。

以下是一个由命名空间所有者管理的 Kubernetes 策略示例。请创建 `policy-lab` 和一个标签为 `role=frontend` 的控制器管理 Pod。此出口策略仅允许常规 CoreDNS 和获准的 HTTPS 目标，同时仍受其他所有可叠加策略的约束。请将文档中的 CIDR 替换为真实目标；如使用 NodeLocal DNS，请相应调整 DNS 配置。
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
在依赖策略实施之前，请验证基线连通性以及允许/拒绝的 TCP 路径。NetworkPolicy 没有可移植的仅审计模式。若所选引擎提供相应功能，请使用其文档所述的日志/暂存功能。Pod 的 SG 和 VPC 防火墙是独立控制措施；Flow Logs 用于观察流量，而不是实施此 API。

</details>

### 6. 自定义 ALB 前端安全组与后端规则有何不同？

<details>
<summary>显示答案</summary>

**答案：`alb.ingress.kubernetes.io/security-groups`**

将此注解片段合并到预期的 Ingress 中。SG ID 没有歧义；按名称查找匹配的是 AWS `Name` 标签，而不是 EC2 的 `groupName` 属性。
```yaml
metadata:
  annotations:
    alb.ingress.kubernetes.io/security-groups: sg-0123456789abcdef0
    alb.ingress.kubernetes.io/manage-backend-security-group-rules: "true"
    alb.ingress.kubernetes.io/tags: Environment=training,Team=platform
```
请自行配置自定义前端的入站/出站规则。提供了前端 SG 时，`inbound-cidrs` 和前缀列表注解会被忽略。`manage-backend-security-group-rules: "true"` 授权控制器通过其后端 SG 机制管理目标访问；它不会在自定义前端 SG 中创建用于限制客户端访问的规则。如果不启用此项，请自行安排节点/Pod SG 访问权限。请允许应用程序端口和健康检查端口，并在目标 ENI 有多个 SG 时检查 SG 选择标签。

发布版本的 IAM 策略包含控制器所需的完整 EC2/ELB 权限；仅列出少量 SG 操作并不构成完整的角色策略。在不同信任域之间复用 SG 会扩大暴露面并增加变更耦合。请检查实际规则和 VPC Flow Log 拒绝记录。`tags` 会添加受支持的资源标签；`load_balancing.cross_zone.enabled` 是负载均衡属性，不是标签。请选择符合客户端兼容性和要求的受支持 TLS 安全策略，而不要照搬旧版策略名称并将其当作当前建议。

</details>

### 7. 如何配置 NLB 客户端 IP 保留？它有哪些限制？

<details>
<summary>显示答案</summary>

**答案：`service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true`**

对于 TCP/TLS 目标组，此属性可配置：instance 目标默认启用，IP 目标默认禁用。UDP/TCP_UDP/QUIC/TCP_QUIC 目标组始终保留客户端 IP，且无法禁用。以下 IPv4 IP 目标 TCP 示例更改了可配置的情形：
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
应用程序看到的地址仍取决于完整路径。NodePort 转发可能会执行 SNAT，除非本地流量策略/拓扑能保留客户端 IP；ALB 使用 HTTP 转发标头；IPv6 到 IPv4 的转换和 PrivateLink 都不会保留原始数据包源地址。要保留客户端 IP，必须使用受支持的直接同 VPC 或同 Region 对等连接路径，且不能经过 transit gateway。内部 NLB 的回环连接若返回同一个已注册目标，可能会失败。

Proxy Protocol v2 可以传递原始地址元数据，但需要兼容的侦听器/解析器；不要盲目启用。框架的 `remote_addr` 或 TCP `RemoteAddr()` 报告的是直接对端，不会自动报告原始互联网客户端。只信任来自明确受信任代理的转发标头。更改 IP 保留设置会影响新建的 TCP 连接。`deregistration_delay.timeout_seconds` 控制连接排空，不控制 TCP keep-alive。请通过测量评估性能，不要使用没有依据的开销数值。

</details>

### 8. 如何将 AWS WAF 附加到由 LBC 管理的 ALB？

<details>
<summary>显示答案</summary>

**答案：使用 `alb.ingress.kubernetes.io/wafv2-acl-arn`，并指定同 Region 的 REGIONAL Web ACL。**

使用真实的 `regional/webacl/...` ARN。CloudFront 的 `global/webacl/...` ARN 不能附加到区域 ALB。关联会保护经过该 ALB 的流量；它不会将 WAF 附加到 Pod、NLB 或 Kubernetes API 服务器。
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
默认操作为 Allow 的空 Web ACL 不会阻止任何流量。以下是一个用于独立规则开发示例的规则数组，请保存为 `waf-rules.json`。此规则对 `/admin` 前缀执行**计数**，而不是阻止流量；它不是身份验证控制，也不是完整的托管规则基线。
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
安全负责人可以使用以下命令创建此培训 ACL；关联时请使用命令返回的 ARN。二进制格式标志会将 JSON 中的 SearchString 作为字面字节传递给 AWS CLI v2。
```bash
set -euo pipefail
: "${AWS_REGION:?Set the ALB Region}"
aws wafv2 create-web-acl --region "$AWS_REGION" \
  --name eks-ingress-training --scope REGIONAL \
  --default-action '{"Allow":{}}' --rules file://waf-rules.json \
  --cli-binary-format raw-in-base64-out \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=eks-ingress-training
```
只有经过配置和调优后，托管 SQLi/XSS、机器人、信誉、基于速率和自定义规则才会提供各自的保护；费用/功能各不相同。启用强制执行之前，请在 Count 模式下检查误报。规则处于计数模式时，默认 Allow 仍会放行流量。

ALB 的 `access_logs.s3.*` 属性用于配置 ALB S3 访问日志，不用于 WAF 日志或 CloudWatch Logs。请单独配置 WAF 日志记录，并使用经过批准的 CloudWatch Logs/S3/Firehose 目标及所需权限；采样请求和 CloudWatch 指标不同于完整请求日志。关联操作请使用经过审核的控制器发布版 IAM 策略，ACL 创建/规则/日志记录则使用单独的安全管理角色。在受支持的情况下限定资源权限；不要将不受限制的独立通配符策略直接贴上来，作为完整的控制器角色策略。

</details>

### 9. 如何为三个可区分的后端构建并验证路径路由？

<details>
<summary>显示答案</summary>

**答案：Ingress + ClusterIP Services + 就绪的 HTTP 工作负载。**

前置条件：已配置并审核 IAM/子网的 LBC、可路由的私有测试客户端、用于你控制的主机名的 ACM 证书，以及创建专用命名空间的权限。此示例会创建内部 ALB；`/admin` 仅是路由标签，不提供身份验证。这是范围有限的培训练习，不能作为生产就绪的证明。请在同一个 shell 中运行各代码块，并启用 `set -euo pipefail`；在清理前保留 LAB_NS/LAB_UID。
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
HTTP 服务器确实会侦听 8080，并对 `/health` 以及所有请求路径返回其后端名称。仅声明 `containerPort: 8080` 不会重新配置默认 nginx 服务器。可变的 Python 标签仅用于说明运行时；为了保证可重复使用，请固定经批准的镜像摘要。
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
等待 ALB 主机名、健康目标和控制器协调完成。如果失败，请检查 Ingress 事件、控制器日志、EndpointSlices 以及 SG/健康检查路径。从获准的私有客户端执行此测试时，会保留 Host 标头和 TLS SNI，同时直接连接到 ALB 主机名；不需要 DNS 记录，也不必禁用证书验证。
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
如需持久 DNS，请创建适当的 Route 53 别名；子域名可以使用 CNAME，zone apex 则不可以。不要使用公共 CA 占位符 ARN，也不要用 `curl -k` 掩盖证书不匹配。

加权路由是另一个独立示例，要求已存在 `service-v1`/`service-v2` 后端。必须通过 `use-annotation` 后端引用此操作；仅添加操作注解不会产生效果。请在预期命名空间中运行，并避免路由冲突。
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
确认已保存的 UID 后，仅清理此练习的命名空间。删除命名空间前，请先让 LBC 移除 Ingress 负载均衡器。如果终结过程失败，请诊断控制器/IAM/删除保护状态；不要强制移除 finalizer。此代码块不会删除共享证书、控制器角色或 DNS 记录。
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

### 10. 服务网格如何改变 EKS 网络？需要验证哪些内容？

<details>
<summary>显示答案</summary>

**答案：它会在兼容的 Pod 网络之上增加流量/安全/遥测处理。**

控制平面分发配置和工作负载身份；数据平面代理处理已加入网格的流量。在 sidecar 设计中，应用程序和代理共享**同一个 Pod 网络命名空间/IP**。sidecar 本身不会必然额外占用一个 VPC IP 或 ENI。额外的网格网关/控制平面 Pod 会消耗资源/IP。Ambient 设计改用节点代理和可选 waypoint，因此“每个 Pod 都有一个 sidecar”并非普遍情况。
```text
Client application → client proxy → Pod network → destination proxy → destination application
```
这是一条逻辑上的 sidecar 路径，并不意味着每个数据包都会经过 Service 虚拟 IP 或被拦截。排除的端口、UDP、host-network 流量、命名空间加入网格的方式和运行模式都会影响结果。VPC 路由、SG 和 NetworkPolicy 仍然适用。L3/L4 策略必须允许所需的数据平面、DNS、控制平面和健康检查路径；mTLS 会对网格对等方进行身份验证/加密，但不能取代应用程序授权。

对于 Istio，应根据计算类型选择一种有文档说明的 sidecar/ambient 安装方式。Fargate 无法运行某些模式所需的节点 DaemonSet/特权组件；请验证支持情况，不要宣称其普遍兼容。不要在同一命名空间中启用两个网格注入器。应通过受支持的 Helm/安装/工作负载设置配置代理资源，而不是用无关的 `pilot.resources` 覆盖注入器 ConfigMap。Prometheus/Tracing 部署和网格导出配置应分开处理；已移除的 `IstioOperator.addonComponents.prometheus` 和虚构的 App Mesh `Mesh.spec.tracing` 都不是可用的安装方案。

**历史比较：**AWS 已于 **September 30, 2026** 结束 App Mesh 支持；其控制台和资源现已不可用。现有 App Mesh 部署必须迁移；不要将其作为新的 EKS 默认方案引入。其历史上的 Fargate 集成不代表未来仍会受支持。ECS Service Connect 是 ECS 的选项，并非 EKS 的直接替代品。请使用受支持的 EKS 网格/数据平面设计，并验证路由、重试、证书、授权、Tracing 和故障处理方面的功能对等性。

本文档没有提供经过验证的测量来源来支持“通常小于 10 ms”的延迟和“10–15%”的 CPU/内存开销数据。此处将其保留为**未经验证的历史估算**，不是基准测试结果或容量保证。加入网格前后，应使用相同的请求组合、TLS、遥测采样和负载，测量 p50/p95/p99 延迟、吞吐量、错误率及 CPU/内存。测试中应包括代理滚动更新、节点丢失、控制平面丢失、证书轮换和重试放大。

请在专用命名空间中逐步采用，验证一个注入器、工作负载就绪状态、mTLS 以及正向/负向策略测试，再逐步扩大范围。对于位于网格 Ingress gateway 前方的 LBC，请公开 gateway Service 并验证目标端口/探针；Ingress API 对象是配置，不是另一个代理跳点。必要时使用范围受限的控制器 IAM；`cloudmap:*` 不是 `servicediscovery` IAM 服务前缀的有效替代品。前缀委派是一种 IP 容量设计选择，并非 sidecar 的前置条件。实现细节请参阅维护中的 [Istio 安装](../../service-mesh/istio/01-installation.md)和 [AWS 集成](../../service-mesh/istio/04-aws-integration.md)章节。

</details>

### 11. Kubernetes Gateway API 中用于 L7 负载均衡 (ALB) 的路由资源是什么？

A. IngressRoute B. HTTPRoute C. VirtualService D. ServiceRoute

<details>

<summary>显示答案</summary>

**答案：B. HTTPRoute**

**说明：**在 Kubernetes Gateway API 中，HTTPRoute 资源用于 L7 负载均衡。HTTPRoute 定义将 HTTP/HTTPS 流量路由到服务的规则；与 AWS Load Balancer Controller 配合使用时，它会通过 ALB 分发流量。

**Gateway API 资源层级：**

1. **GatewayClass**：定义负载均衡器类型（例如，`amazon-alb`、`amazon-nlb`）
2. **Gateway**：实际的负载均衡器实例（侦听器端口、TLS 设置等）
3. **HTTPRoute**：L7 路由规则（主机、路径、基于标头的路由）
4. **TCPRoute**：L4 路由规则（TCP 流量）

LBC 使用单独的 ALB 和 NLB Gateway；controllerName 用于选择实现，而不是任意的 GatewayClass 对象名称。请确认发布版一致性表中支持的过滤器。

**HTTPRoute 的主要功能：**

* 基于路径和主机的路由
* 原生的基于权重的流量拆分
* 标头和查询参数匹配
* 路由到多个后端服务

其他选项的问题：

* **A. IngressRoute**：这不是标准的 Gateway API 资源。
* **C. VirtualService**：这是 Istio 服务网格中的资源。
* **D. ServiceRoute**：此资源不存在。

</details>

### 12. 如何启用 LBC 3.6.0 Gateway 控制器？

- A. 始终传入 `--enable-gateway-api`
- B. 检测兼容的 CRD，并使用真正默认启用的 gate
- C. 使用 `--feature-gates=EnableGatewayAPI=true`
- D. 仅安装 1.2.1 的 experimental CRD

<details>
<summary>显示答案</summary>

**答案：B. 检测所需的 CRD；ALBGatewayAPI/NLBGatewayAPI 默认启用。**

安装与此发布版本兼容的 Gateway API 1.6.0 标准 CRD 和 LBC 特定 Gateway CRD。默认 gate 为 `ALBGatewayAPI` 和 `NLBGatewayAPI`；`EnableGatewayAPI` 是未知的功能名称。TCPRoute/UDPRoute 现在通过标准 channel 以 v1 提供。较早的控制器发布版本有不同的兼容性/gate 要求：L4 支持始于 2.13.3，L7 支持始于 2.14.0。安装 CRD 后请检查控制器启动状态/日志；CRD 本身不能提供 IAM、子网或应用程序后端。

</details>

### 13. 在 Gateway API 中，通过 NLB 路由 L4 级 TCP 流量时使用什么资源？

A. HTTPRoute B. TLSRoute C. TCPRoute D. GRPCRoute

<details>

<summary>显示答案</summary>

**答案：C. TCPRoute**

**说明：**在 Gateway API 中，TCPRoute 资源用于路由 L4 级 TCP 流量。与 AWS Load Balancer Controller 配合使用时，TCPRoute 会通过 NLB (Network Load Balancer) 将 TCP 流量转发到后端服务。

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

| 资源  | 协议   | AWS LB 类型 |
| --------- | ---------- | ----------- |
| HTTPRoute | HTTP/HTTPS | ALB         |
| TCPRoute  | TCP        | NLB         |
| TLSRoute  | TLS        | NLB         |
| GRPCRoute | gRPC       | ALB         |

其他选项的问题：

* **A. HTTPRoute**：用于通过 ALB 处理 HTTP/HTTPS L7 流量。
* **B. TLSRoute**：用于 TLS 流量路由，但 TCPRoute 更适合 TCP 级路由。
* **D. GRPCRoute**：专用于 gRPC 协议的路由资源。

</details>
`my-nlb-gateway` 侦听器和后端 Service 必须存在于 `gateway-demo` 中。此实现中的 TLSRoute 不提供基于 SNI 的 NLB 路由；请使用特定发布版本的 TLS 行为，不要假设所有 Gateway API 实现都以相同方式工作。

### 14. LBC 3.6.0 如何为 ALB Gateway 配置静态证书？

- A. 创建任意名为 tls-cert 的 Secret
- B. 在 LoadBalancerConfiguration 中使用 ACM ARN
- C. 仅添加 Route 主机名
- D. 将后端 Service 端口设置为 443

<details>
<summary>显示答案</summary>

**答案：B. `LoadBalancerConfiguration.spec.listenerConfigurations[].defaultCertificate`**

HTTPS 侦听器应使用有效的同 Region ACM 证书 ARN。此实现不支持 Kubernetes Secret `certificateRefs`。主机名发现也需要现有的匹配 ACM 证书和安全侦听器。仅将 HTTPRoute 的后端端口设为 443 并不会配置客户端侧 HTTPS。

</details>

### 15. 仅包含前端规则的 ingress policy 会收窄现有的同命名空间全允许策略吗？

- A. 会，最新的策略优先
- B. 会，选择器最具体的策略优先
- C. 不会，匹配的允许规则会合并
- D. 只有策略名称按字母排序排在最前时才会

<details>
<summary>显示答案</summary>

**答案：C. 不会；匹配的 NetworkPolicy 允许规则会叠加。**

两个策略都会选择后端，因此更宽泛的同命名空间允许规则仍会放行其他同命名空间调用方。请由策略所有者移除或收窄更宽泛的策略，然后测试允许和拒绝的连接。Ingress 和 egress 隔离相互独立；DNS egress 和目标 ingress 都可能影响测试结果。

</details>

官方参考资料：[LBC Gateway API](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/gateway/gateway/)、[PrivateLink](https://docs.aws.amazon.com/vpc/latest/privatelink/create-endpoint-service.html)、[NLB 客户端 IP](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/edit-target-group-attributes.html)、[WAF 关联](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-associating-aws-resource.html)、[App Mesh 退役](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html)。
