# AWS Load Balancer Controller 测验

基于 self-managed LBC v3.6.0 指南。

## 1. AWS Load Balancer Controller 管理什么？

- A. 所有云提供商职责，包括节点生命周期
- B. 根据 Kubernetes 资源协调的受支持 AWS 负载均衡器资源
- C. kube-proxy 数据包转发
- D. 每个 pod 的 CoreDNS 记录

<details>
<summary>显示答案</summary>

B. LBC 管理受支持的 ALB/NLB、目标组、监听器及相关资源。它不会取代 kube-proxy、CNI、DNS 或所有云控制器职责。旧版 AWS 提供商行为和 EKS Auto Mode 是单独的实现；不要声称 LBC 实现了每种 ELB 产品的所有功能。

</details>

## 2. ALB 的 ip 和 instance 目标类型有何不同？

- A. ip 注册 pod IP；instance 通过节点 NodePort 转发
- B. ip 始终通过 NodePort 转发
- C. 两者相同
- D. instance 仅适用于 IPv6

<details>
<summary>显示答案</summary>

A. IP 目标需要受支持、可通过 VPC 路由的 pod 地址，以及端点/ENI 发现功能。Amazon VPC CNI 是 EKS 中的常见选择，但也可以使用兼容的替代 CNI 配置。Instance 目标需要支持 NodePort 的 Service 和适当的节点网络。直接寻址并不能证明所有工作负载都能获得特定的延迟优势。

</details>

## 3. 为什么控制器需要通过 IRSA 或 EKS Pod Identity 获取 IAM 角色？

- A. 取代 pod 网络
- B. 对其 AWS API 调用进行身份验证和授权
- C. 取代 Kubernetes RBAC
- D. 使每个后端请求都经过身份验证

<details>
<summary>显示答案</summary>

B. 控制器会调用 AWS API 来创建/管理负载均衡器、目标组、监听器和相关安全组。IRSA 和受支持的 Pod Identity 配置是可选方案。角色只会授予附加到该角色的策略所允许的权限；使用角色并不会自动使策略符合最小权限原则。Kubernetes RBAC 和应用身份验证是彼此独立的。

</details>

## 4. 多个 Ingress 如何共享一个 ALB？

- A. 位于同一命名空间就足够了
- B. 使用相同的 alb.ingress.kubernetes.io/group.name
- C. 所有 Ingress 始终共享一个 ALB
- D. 设置相同的 pod 名称

<details>
<summary>显示答案</summary>

B. IngressGroup 会共享 ALB 和规则空间。较小的 group.order 值会先进行评估；值相同时按 namespace/name 排序。仅在有强制执行的信任边界内使用此功能，因为能够加入该组的不可信用户可以影响路由。请检查注解的合并/互斥行为、限制和成本，不要假设每种部署都能节省成本。

</details>

## 5. 哪个注解用于指定 NLB TLS 证书？

- A. service.beta.kubernetes.io/aws-load-balancer-ssl-cert
- B. alb.ingress.kubernetes.io/certificate-arn
- C. service.beta.kubernetes.io/aws-load-balancer-tls-termination
- D. nlb.kubernetes.io/ssl-certificate

<details>
<summary>显示答案</summary>

A. 对于 self-managed LBC，完整的 Service 示例为：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nlb-tls-service
  namespace: default
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: '443'
    service.beta.kubernetes.io/aws-load-balancer-backend-protocol: tcp
spec:
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  selector:
    app: my-app
  ports:
  - name: https
    port: 443
    targetPort: 8080
    protocol: TCP
```

请替换证书 ARN，并提供与之匹配、在 8080 端口监听的后端 pod。面向客户端的 TLS 在 NLB 处终止；这里的 tcp 表示后端连接不使用 TLS。请使用适当的证书/安全策略和网络控制。Auto Mode 使用自己的 loadBalancerClass 和受支持的注解集。

</details>

## 6. 独立创建的 TargetGroupBinding 有什么用途？

- A. 自动创建所有负载均衡器/监听器
- B. 将 Kubernetes Service 的目标注册到现有目标组
- C. 定义 ALB HTTP 监听器路由规则
- D. 取代 IAM 授权

<details>
<summary>显示答案</summary>

B. 负载均衡器、监听器和目标组都已存在，并且必须与 Service/目标协议、地址族和端口相匹配。

```yaml
apiVersion: elbv2.k8s.aws/v1beta1
kind: TargetGroupBinding
metadata:
  name: my-tgb
  namespace: default
spec:
  targetGroupARN: arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/my-tg/1234567890abcdef
  serviceRef:
    name: my-service
    port: 80
  targetType: ip
```

对于由多个集群/TGB 共享的目标组，每个参与方都必须在创建时设置 multiClusterTargetGroup: true。默认情况下，系统会假定拥有完整所有权，并可能注销外部目标。nodeSelector 适用于 instance 目标，不适用于 IP 模式的 pod 筛选。请将 TGB 权限限制为受信任用户。

</details>

## 7. 哪个注解可将区域级 WAF v2 Web ACL 关联到 ALB？

- A. alb.ingress.kubernetes.io/waf-acl-id
- B. alb.ingress.kubernetes.io/wafv2-acl-arn
- C. alb.ingress.kubernetes.io/web-acl
- D. alb.ingress.kubernetes.io/firewall-rules

<details>
<summary>显示答案</summary>

B. 请提供 ALB 所在区域中现有 Web ACL 的 ARN，配置其规则，并授予控制器所需的权限。必须启用 WAF v2 集成；其默认值为 true，因此并非所有情况下都需要显式设置 enableWafv2。禁用该集成时，注解不会生效。WAF 和付费的 Shield Advanced 保护是不同的功能。

</details>

## 8. 常见的子网角色标签有哪些？

- A. 仅 kubernetes.io/cluster/CLUSTER_NAME
- B. 公有子网使用 kubernetes.io/role/elb，私有子网使用 kubernetes.io/role/internal-elb
- C. aws:cloudformation:stack-name
- D. 仅 Name=kubernetes-subnet

<details>
<summary>显示答案</summary>

B. 对于 self-managed LBC，标签值可以是 1 或空。在 v2.12.1 及更高版本中，如果缺少匹配的角色标签，默认的基于可达性的回退机制可以根据路由表对子网进行分类。显式指定子网和 IngressClassParams 标签筛选器是其他选择路径。Auto Mode 仍要求使用其文档中规定的标签。请检查集群标签、可用 IP 数量和 AZ 要求；标签不会修改路由。

</details>

## 9. 如何配置 ALB 粘性会话？

- A. alb.ingress.kubernetes.io/sticky-sessions=true
- B. 在 target-group-attributes 中设置 stickiness.enabled=true
- C. 在 Ingress 上设置 session-affinity=cookie
- D. 始终默认启用

<details>
<summary>显示答案</summary>

B. 设置 alb.ingress.kubernetes.io/target-type: ip，并在同一个 target-group-attributes 注解中将 stickiness.enabled=true 与适当的 cookie 属性组合使用。不要为慢启动或注销延迟重复使用 YAML 键，因为重复键可能导致设置被丢弃。使用加权转发操作时，请按照文档说明一致地配置其目标组粘性。

</details>

## 10. 关于 NLB 客户端身份，哪项说法正确？

- A. Proxy Protocol v2 会将 IP 数据包的源地址更改为客户端地址
- B. externalTrafficPolicy: Local 保证所有目标模式都能保留客户端 IP
- C. Proxy Protocol 会传递元数据；数据包源地址保留是另一项设置，且受网络/协议限制
- D. NLB 始终保留客户端 IP

<details>
<summary>显示答案</summary>

C. 后端必须在应用数据之前解析 Proxy Protocol v2，并支持适用的运行状况检查。preserve_client_ip.enabled 用于在受支持的情况下控制数据包源地址保留。在 instance/NodePort 模式下，externalTrafficPolicy: Local 可以避免后续 kube-proxy SNAT 跳转；但它无法解决所有 NLB 路径或 IP 地址族转换情况。对于加权 NLB 目标，常规权重调整会影响新连接，但将权重设为零会在短时间后关闭现有连接。

</details>

## 11. 哪个注解可配置 ALB 的 HTTP 到 HTTPS 重定向？

- A. alb.ingress.kubernetes.io/force-ssl-redirect
- B. alb.ingress.kubernetes.io/ssl-redirect: "443"
- C. alb.ingress.kubernetes.io/http-to-https
- D. 始终需要 HTTPRoute

<details>
<summary>显示答案</summary>

B. 配置 HTTP 监听器和目标 HTTPS 监听器，并设置适当的证书。启用后，HTTP 监听器会使用重定向默认操作，其其他路由规则将被忽略。此设置会影响整个 IngressGroup，因此请检查组级行为。Cognito/OIDC/JWT 身份验证需要 HTTPS；单靠重定向并不等于应用授权。

</details>

## 12. ALB 未创建时，应该先检查什么？

- A. 仅检查 kube-proxy 日志
- B. 应用的 cookie 内容
- C. 控制器日志/事件、类选择、IAM、子网资格以及 webhook/CRD 健康状况
- D. 仅检查 pod 副本数

<details>
<summary>显示答案</summary>

C. 首先检查协调/控制平面路径。对于节点/Service 流量，kube-proxy 或 eBPF 替代方案之后可能会有影响，但它不是 AWS CreateLoadBalancer 操作失败时首先要检查的内容。kubectl apply 成功并不能证明 AWS 协调成功。请使用真实的资源 ID、命名空间，并限制日志输出范围。

</details>

[返回指南](../../networking/03-aws-lb-controller.md)
