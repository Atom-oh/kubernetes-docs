# 使用 cert-manager 管理证书

> **最后更新**：October 16, 2026
> **验证基线**：cert-manager 1.21.2、cmctl 2.6.1、trust-manager 0.25.0、istio-csr 0.18.0、aws-privateca-issuer 1.9.2、ACK ACM 1.8.1。cert-manager 1.21 公布的受支持/已测试 Kubernetes 版本范围为 1.33–1.36；Kubernetes 1.37 不在该范围内，因此本指南不声明与其兼容。

cert-manager 将证书签发和续期作为 Kubernetes 资源进行管理。**CA 信任分发、应用重新加载、吊销以及 CRL/OCSP 操作仍是单独的职责。**示例已使用本地 schema、配置和库进行检查；它们不能证明外部 CA 签发或 AWS/Kubernetes 部署已成功。另有一项独立的临时本地 Vault 2.1.0 测试，使用合成 CA 对十六种签发/CSR 签名接受/拒绝场景进行了验证。

<span id="what-cert-manager-solves"></span>
<span id="project-status"></span>
<span id="why-certificate-lifecycle-automation-matters"></span>
<span id="overview-1"></span>

## 概述

cert-manager 于 2020 年 11 月 10 日加入 CNCF，于 2022 年 9 月 19 日进入孵化阶段，并于 **2024 年 9 月 29 日毕业**。毕业并不保证特定部署的安全性或可用性。

| 生命周期事项 | 职责 |
|---|---|
| 签发 | 签发者身份验证、请求者审批、SAN/用途/有效期策略 |
| 续期 | 实际签发的有效期、ARI/renewBefore、重试和告警 |
| 密钥轮换 | Secret 访问、使用方重新加载、CA 轮换顺序 |
| 信任 | 每个命名空间/进程信任哪些根证书/中间证书 |
| 吊销 | CA 吊销流程以及 CRL/OCSP 发布/使用 |

不要将旧版 1.16.2 安装和兼容性表作为当前支持指南。1.16 版本已于 2025 年 6 月结束生命周期。请根据中间版本的发布说明和 CRD 变更规划升级。

<span id="component-overview"></span>
<span id="component-responsibilities"></span>
<span id="certificate-issuance-flow"></span>

## 架构

![cert-manager 组件以及签发者/Secret 关系](../.gitbook/assets/en-security-10-cert-manager-0.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-security-10-cert-manager-0.html)

控制器协调 Certificates 并创建 CertificateRequests；签发者控制器负责签发。Webhook 用于验证/设置默认值/转换自定义资源，而 cainjector 管理受支持 API/webhook 配置中的 CA bundle。CA/SelfSigned 签发者不一定是外部服务。

<span id="prerequisites"></span>
<span id="installation-with-helm-recommended"></span>
<span id="production-helm-values"></span>
<span id="installation-with-kubectl"></span>
<span id="verify-installation"></span>

## 安装

检查受支持的 Kubernetes 版本、Helm/集群权限、Gateway API CRD 和实际的 Gateway 控制器，以及可选的 Prometheus Operator CRD。如果在控制器启动后才安装 Gateway API CRD，请确认是否需要重启/重新发现。

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update jetstack
helm upgrade --install cert-manager jetstack/cert-manager \
  --version v1.21.2 --namespace cert-manager --create-namespace \
  --values cert-manager-values.yaml
kubectl get pods -n cert-manager
cmctl check api
```

```yaml
crds:
  enabled: true
  keep: true
replicaCount: 2
podDisruptionBudget:
  enabled: true
  minAvailable: 1
config:
  apiVersion: controller.config.cert-manager.io/v1alpha1
  kind: ControllerConfiguration
  gatewayAPI:
    enabled: true
prometheus:
  enabled: true
  servicemonitor:
    enabled: true
webhook:
  replicaCount: 2
  timeoutSeconds: 10
  podDisruptionBudget:
    enabled: true
    minAvailable: 1
cainjector:
  replicaCount: 2
  podDisruptionBudget:
    enabled: true
    minAvailable: 1
```

此配置启用了 ServiceMonitor 和 Gateway API，因此相应的 CRD/控制器必须已存在。若要在不依赖这些组件的情况下进行最小化安装，请禁用这些选项。副本/PDB 不能替代节点/AZ 分布和 API 连通性。当前配置使用 config.gatewayAPI.enabled；旧字段 enableGatewayAPI 在 1.21.2 解码器中仍可接受，但已弃用。

检查 CRD 保留策略以及实际的卸载归属。删除 CRD 可能会删除其自定义资源；这不是常规的升级故障排查步骤。

<span id="custom-resource-definitions-crds"></span>
<span id="certificate-resource"></span>
<span id="issuer-vs-clusterissuer"></span>
<span id="certificaterequest-resource"></span>

## 核心概念

![Certificate 资源以及由控制器创建的请求](../.gitbook/assets/en-security-10-cert-manager-1.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-security-10-cert-manager-1.html)

| 资源 | 作用范围和用途 |
|---|---|
| Certificate | 命名空间内所需的证书和输出 Secret |
| Issuer | 在其命名空间内引用的签发配置 |
| ClusterIssuer | 可跨命名空间引用的签发配置 |
| CertificateRequest | CSR、issuerRef 以及审批/拒绝状态 |
| Order/Challenge | ACME 流程使用的排序/验证资源 |

ClusterIssuer 的凭证/CA Secret 位于控制器的集群资源命名空间，默认为 cert-manager。Issuer Secret 位于 Issuer 所在的命名空间。创建 Certificate 的权限本身不会限制 SAN 或 issuerRef。

### Certificate 和续期

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: app-tls
  namespace: demo-app
spec:
  secretName: app-tls
  dnsNames: [app.example.com]
  duration: 2160h
  renewBeforePercentage: 33
  privateKey:
    algorithm: ECDSA
    size: 256
    encoding: PKCS8
    rotationPolicy: Always
  usages: [server auth]
  issuerRef:
    name: lab-ca
    kind: ClusterIssuer
    group: cert-manager.io
```

请求的有效期可能与 CA 实际签发的有效期不同。默认续期时间为**实际 X.509 有效期的三分之二处**，而不是在到期前固定 15/30 天。renewBeforePercentage 根据实际有效期计算缓冲时间。选择 renewBefore 或 percentage，不要同时使用两者；duration 至少为 1 小时，实际续期缓冲时间必须至少为 5 分钟且短于 duration。

1.21.2 版本的续期策略/窗口和受支持的 ARI 路径可能会影响时间。renewal.policy:Disabled 会禁用自动续期。检查 status.renewalTime、实际 notBefore/notAfter 和失败告警。自 1.18 起，privateKey.rotationPolicy 的默认值为 Always。更新密钥/证书 Secret 并不保证应用会重新加载。

### CertificateRequest 和私钥

直接请求必须使用真实的 PEM CSR；不要应用被截断的 base64 示例。cmctl create certificaterequest **会在集群中创建请求**，并非离线验证命令。应单独限制 cmctl approve/deny 权限。本次审计仅使用 cert-manager PKI 库生成并验证了合成的本地密钥/CSR。

<span id="selfsigned-issuer-development-testing"></span>
<span id="ca-issuer-internal-pki"></span>
<span id="acme-let-s-encrypt"></span>
<span id="acme-challenge-types"></span>
<span id="http-01-solver"></span>
<span id="dns-01-solver-with-route53-and-irsa"></span>
<span id="aws-private-ca-issuer"></span>
<span id="hashicorp-vault-pki"></span>

## 签发者类型

### SelfSigned 和 CA 引导

[完整的引导示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/bootstrap.yaml)会创建专用的实验室根证书和叶证书。根证书明确设置 renewal Disabled 和密钥轮换 Never，以避免**意外替换信任锚**。生产环境根密钥保管、离线 CA、中间 CA 隔离、审计和吊销需要单独设计。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cert-manager
  labels:
    trust-bundle: enabled
---
apiVersion: v1
kind: Namespace
metadata:
  name: demo-app
  labels:
    trust-bundle: enabled
    cert-manager-http01: enabled
---
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: bootstrap
  namespace: cert-manager
spec:
  selfSigned: {}
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: lab-root
  namespace: cert-manager
spec:
  secretName: lab-root
  isCA: true
  commonName: Documentation Lab Root
  subject:
    organizations: [Documentation Lab]
  duration: 8760h
  renewal:
    policy: Disabled
  privateKey:
    algorithm: ECDSA
    size: 256
    encoding: PKCS8
    rotationPolicy: Never
  usages: [cert sign, crl sign]
  issuerRef:
    name: bootstrap
    kind: Issuer
    group: cert-manager.io
---
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: lab-ca
spec:
  ca:
    secretName: lab-root
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: app-tls
  namespace: demo-app
spec:
  secretName: app-tls
  dnsNames: [app.example.com]
  duration: 2160h
  renewBeforePercentage: 33
  privateKey:
    algorithm: ECDSA
    size: 256
    encoding: PKCS8
    rotationPolicy: Always
  usages: [server auth]
  issuerRef:
    name: lab-ca
    kind: ClusterIssuer
    group: cert-manager.io
```

CA 签发者使用包含 CA 证书/私钥的 Secret。替换该 Secret 不会立即重新签发所有叶证书，也不会更新所有客户端的信任存储。CA 签发者可以包含 CRL/OCSP URL，但不会生成或维护 CRL/OCSP 响应。应实施策略，防止叶证书的有效期超过其 CA。

### ACME：HTTP-01 和 DNS-01

![ACME HTTP/DNS 验证和签发](../.gitbook/assets/en-security-10-cert-manager-2.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-security-10-cert-manager-2.html)

HTTP-01 需要通过端口 80 访问主机名，且不支持通配符。DNS-01 使用 DNS TXT 权限进行通配符验证。重复使用授权以及 ACM 的预验证流程意味着并非每个请求都会创建新的 challenge。

不要将社区版 ingress-nginx 推荐为新安装的默认选择；它已于 2026 年 3 月结束维护。[HTTP-01 Gateway 示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/public-staging.yaml)假定已安装 Envoy Gateway 及其 envoy-gateway GatewayClass。请验证实际的 class，并确保 solver 命名空间的 cert-manager-http01:enabled 标签与 allowedRoutes 相匹配。Gateway 证书填充功能不会安装 Gateway 控制器，也不会实现其 TLS 重新加载。

[Route53 签发者](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/route53-issuer.yaml)和 [IAM 策略](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/route53-policy.json)指定了 hostedZoneID，并将更改范围限制为 challenge TXT 名称。指定 zone 可避免要求全局 ListHostedZonesByName 访问权限。请通过 IRSA 或受支持的 Pod Identity，以及任何跨账户角色链来验证控制器凭证。命名空间选择和 dnsZones 不能替代 IAM 授权。

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: public-dns01
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: pki-admin@example.com
    privateKeySecretRef:
      name: public-dns01-account
    solvers:
      - selector:
          dnsZones: [example.com]
        dns01:
          route53:
            region: ap-northeast-2
            hostedZoneID: Z1234567890ABC
```

Let’s Encrypt staging 环境有速率限制，其根证书也不受生产环境浏览器信任。ACME 账户按环境区分。到期通知邮件已于 2025 年停止发送；email 字段不能替代到期监控。对于 429 响应，应遵循 Retry-After 和相应的补充策略，而不是一律在一小时后重试。ARI 续期和新签发适用不同的速率限制规则。

### AWS Private CA

外部 aws-privateca-issuer 控制器需要限定 CA ARN 范围的签发/读取权限，以及 EKS 工作负载身份。文档中列出的操作为 acm-pca:DescribeCertificateAuthority、acm-pca:GetCertificate 和 acm-pca:IssueCertificate；请将其 Resource 限定为目标 CA ARN。替换[示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/pca-issuer.yaml)中的实际 CA ARN，并验证 CA 模式、模板、算法、用途和请求的有效期。请另行检查短期 CA 限制和定价。不要通过 disableApprovedCheck 绕过审批检查。

```bash
helm repo add awspca https://cert-manager.github.io/aws-privateca-issuer
helm upgrade --install aws-pca-issuer awspca/aws-privateca-issuer \
  --version v1.9.2 --namespace cert-manager
```

### Vault PKI

[Issuer/token RBAC 示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/vault-issuer.yaml)将令牌创建权限限制在 demo-app/vault-issuer。请单独提供 Vault 服务器的 TLS CA Secret。[PKI 角色/策略脚本](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/vault-setup.sh)假定 PKI/Kubernetes-auth 挂载已存在、Vault 身份已获批准，且 TokenReview 访问权限已配置。

在 Vault 角色中限制 SAN，并将 audience vault://demo-app/vault-pki 绑定到此 Issuer。审核者 JWT、Kubernetes API audience 和 OIDC 访问取决于 Vault 的运行位置。不要通过 tls-skip-verify 或宽泛的默认 Vault 策略来绕过连通性问题。

<span id="tls-termination-comparison"></span>
<span id="alb-ingress-with-acm-vs-cert-manager"></span>
<span id="nlb-with-tls-termination-at-ingress-controller"></span>
<span id="gateway-api-integration"></span>

DNS 角色明确设置 allow_ip_sans=false 和 allow_localhost=false。allowed_domains 不会限制 IP SAN，而 localhost 有单独的宽松默认值。vault write POST 会将未提供的角色字段重置为默认值；应用后请读取完整角色，并测试允许的 DNS 请求以及被拒绝的 IP/localhost 请求。

## EKS 集成模式

| 路径 | TLS 终止位置和密钥位置 |
|---|---|
| 使用 ACM 的 ALB/NLB TLS 侦听器 | AWS 负载均衡器使用 ACM ARN |
| 使用 Gateway/Pod 的 NLB TCP | 后端使用 Kubernetes Secret 终止 TLS |
| Gateway HTTPS 侦听器 | Gateway 控制器引用同一命名空间中的 TLS Secret |
| ACM 可导出的公有证书 | 显式导出的密钥/证书供客户管理的工作负载使用 |

ALB 不能直接将 cert-manager Kubernetes Secret 作为侦听器证书；导入/导出以及 ACM ARN 关联是单独的步骤。[ALB 示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/alb-acm-ingress.yaml)需要真实的 ACM ARN 和后端 Service。[NLB TCP 示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/nlb-tcp-service.yaml)会将 TLS 流量转发到后端端口 8443，该端口必须实际提供 TLS 服务。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: app-gateway
  namespace: demo-app
  annotations:
    cert-manager.io/cluster-issuer: lab-ca
spec:
  gatewayClassName: envoy-gateway
  listeners:
    - name: https
      hostname: app.example.com
      protocol: HTTPS
      port: 443
      tls:
        mode: Terminate
        certificateRefs:
          - group: ""
            kind: Secret
            name: app-gateway-tls
      allowedRoutes:
        namespaces:
          from: Same
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: app
  namespace: demo-app
spec:
  parentRefs:
    - name: app-gateway
  hostnames: [app.example.com]
  rules:
    - backendRefs:
        - name: app
          port: 8080
```

此 Gateway 使用 lab-ca，普通浏览器不信任该 CA。实际的公有证书签发需要经过批准的签发者/域名验证流程及控制器。请验证 GatewayClass 名称以及 certificateRefs 的作用域/类型；避免由两个控制器管理同一个 Secret。

<span id="july-2026-update-acm-now-supports-the-acme-protocol"></span>
<span id="supported-certificate-types"></span>
<span id="applicable-scenarios"></span>
<span id="example-defining-a-certificate-via-ack"></span>
<span id="comparison-with-cert-manager"></span>

<span id="aws-native-alternative-acm--ack"></span>

## AWS 原生替代方案：ACM + ACK

### ACM RequestCertificate 和 ACK 导出

ACK ACM 本身也是一个已安装并需要运维的开源控制器。1.8.1 [示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/ack-acm.yaml)明确配置 options.export:ENABLED、exportTo 和输出 Secret。仅定义签发请求不会创建 TLS Secret。在 1.8.1 CRD 中（v1.10.0 中也未变化），validationMethod 仅出现在只读的 status domainValidations 字段中，而不在 spec 中；不要将旧示例中的该字段复制到请求中。

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: exported-public-tls
  namespace: demo-app
type: kubernetes.io/tls
data:
  tls.crt: ""
  tls.key: ""
---
apiVersion: acm.services.k8s.aws/v1alpha1
kind: Certificate
metadata:
  name: exportable-public-tls
  namespace: demo-app
spec:
  domainName: app.example.com
  keyAlgorithm: RSA_2048
  options:
    export: ENABLED
  exportTo:
    namespace: demo-app
    name: exported-public-tls
    key: tls.crt
```

域名验证是单独的步骤。Route53 ACK 可以管理 ACM 提供的 CNAME，但安装 ACM 控制器不会自动验证所有 DNS 提供商。请评估可导出证书的定价、控制器 IAM/RBAC/命名空间边界，以及私钥 Secret 的访问权限。私有 CA/SPIFFE mTLS 身份需要单独设计签发者/信任方案。

### ACM ACME：EAB 和预验证域名

ACM 于 2026 年 7 月 6 日宣布推出 ACME，可签发有效期为 45 天的公有证书。PKI 管理员会准备端点/域名验证以及与 IAM 角色关联的 EAB 凭证，然后注册客户端。**仅更改服务器 URL 并不足够。**请安全存储 HMAC 密钥，并在 cert-manager 的集群资源命名空间中提供 acm-eab Secret/hmac 条目。

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: acm-acme
spec:
  acme:
    server: https://acm-acme-enroll.ap-northeast-2.api.aws/REPLACE_ENDPOINT_ID/directory
    email: pki-admin@example.com
    privateKeySecretRef:
      name: acm-acme-account
    externalAccountBinding:
      keyID: REPLACE_EAB_KEY_ID
      keySecretRef:
        name: acm-eab
        key: hmac
```

externalAccountBinding 引用的 Secret 值必须包含经过 base64url 编码的 HMAC 密钥；Kubernetes Secret 数据编码是另一个独立的编码层。若提供方的值已经编码，请保留原值，不要再次编码。请参阅 [ACME EAB 配置](https://cert-manager.io/docs/configuration/acme/)。

Endpoint ID 和 EAB keyID 都是占位符。域名必须已在端点完成预验证。ACME 客户端会生成/持有私钥并管理续期。ACM 资源清单中出现 ARN 并不意味着此证书可以直接用于托管 ALB/CloudFront/API Gateway 集成。ExportCertificate、RenewCertificate 和 RevokeCertificate 不适用于此签发路径；其生命周期由 ACME 客户端管理。请区分面向 AWS 集成服务的 RequestCertificate。

<span id="istio-with-istio-csr"></span>
<span id="installing-istio-csr"></span>
<span id="configuring-istio-to-use-istio-csr"></span>
<span id="linkerd-trust-anchor-management"></span>

## 服务网格集成

![istio-agent、istio-csr、SDS 和对等 mTLS](../.gitbook/assets/en-security-10-cert-manager-3.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-security-10-cert-manager-3.html)

### Istio 和 istio-csr

在 sidecar 流程中，istio-agent 会创建 CSR，istio-csr 会提交 CertificateRequest。Agent 通过 SDS 将密钥/证书材料交付给 Envoy；工作负载代理会建立 mTLS。同一 Pod 内的应用流量不会自动启用 mTLS。

[istio-csr values](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/istio-csr-values.yaml)会为 rootCAFile 配置实际的 ConfigMap 卷/挂载。请先在 cert-manager 中创建应用信任 bundle，并等待签发者就绪。仅有文件路径或 meshConfig 中的空 PEM 并不足够。请使用当前的 Istio Helm/istioctl 外部 CA 设置；不要将 istio-csr 路径与 Kubernetes CSR RA 模式混用。Ambient 支持情况应单独评估。

```bash
helm upgrade --install cert-manager-istio-csr jetstack/cert-manager-istio-csr \
  --version v0.18.0 --namespace cert-manager --values istio-csr-values.yaml
```

### Linkerd 和 trust-manager

[Linkerd identity 示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/linkerd-identity.yaml)会准备签发者 Secret 和根证书 bundle ConfigMap。固定版本的控制平面 chart 2026.9.1 引用了 linkerd-identity-issuer 和 linkerd-identity-trust-roots。

```yaml
identity:
  externalCA: true
  issuer:
    scheme: kubernetes.io/tls
```

这样控制平面会连接到由外部续期的签发者 Secret，而不是在安装时只复制一次密钥。根证书轮换需要新旧根证书重叠、工作负载续期以及信任重新加载。示例中的实验室根证书由人工管理，并已禁用自动续期。

<span id="installing-trust-manager"></span>
<span id="bundle-resource"></span>
<span id="using-trust-bundles-in-applications"></span>

## trust-manager

默认的 trust-manager 0.25.0 chart 会渲染 trust.cert-manager.io/v1alpha1 Bundle。仓库中的额外 CRD 本身不会改变默认安装的 API。源 Secret/ConfigMap 会从配置的 trust 命名空间读取。

```yaml
apiVersion: trust.cert-manager.io/v1alpha1
kind: Bundle
metadata:
  name: application-trust
spec:
  sources:
    - secret:
        name: lab-root
        key: tls.crt
  target:
    configMap:
      key: ca-bundle.pem
    namespaceSelector:
      matchLabels:
        trust-bundle: enabled
```

内联 PEM 字段为 inLine，而非 inlineString。尽量减少公有/私有信任根，并明确选择目标命名空间。Secret 目标需要单独启用/RBAC；此示例使用 ConfigMap。信任 bundle 分发的是信任锚，而非私钥。

[使用方 Deployment](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/trust-consumer.yaml)会挂载一个目录。通过 subPath 文件挂载时，ConfigMap 更改不会传播。即使挂载的是目录投影，也不会自动重新加载进程缓存的 TLS 上下文；请测试应用是否实际使用 SSL_CERT_FILE 或其配置的信任存储。

<span id="prometheus-metrics"></span>
<span id="key-metrics"></span>
<span id="prometheusrule-for-alerting"></span>
<span id="certificate-readiness-check"></span>
<span id="common-errors-and-solutions"></span>
<span id="cmctl-cli-tool"></span>

## 监控和故障排查

检查已安装 chart 的 ServiceMonitor 中的选择器和 port/targetPort 值。1.21.2 配置会针对 controller/cainjector/webhook 选择 http-metrics。不要凭空编造 tcp-prometheus-servicemonitor 端口名称。

```yaml
groups:
  - name: cert-manager
    rules:
      - alert: CertificateNotReady
        expr: certmanager_certificate_ready_status{condition="True"} == 0
        for: 10m
        labels:
          severity: critical
      - alert: CertificateExpiringSoon
        expr: (certmanager_certificate_expiration_timestamp_seconds - time() < 604800) and (certmanager_certificate_expiration_timestamp_seconds - time() > 86400)
        for: 30m
        labels:
          severity: warning
      - alert: CertificateExpiryCritical
        expr: (certmanager_certificate_expiration_timestamp_seconds - time() <= 86400) and (certmanager_certificate_expiration_timestamp_seconds - time() > 0)
        for: 10m
        labels:
          severity: critical
      - alert: CertificateExpired
        expr: (certmanager_certificate_expiration_timestamp_seconds > 0) and (certmanager_certificate_expiration_timestamp_seconds <= time())
        for: 5m
        labels:
          severity: critical
```

就绪指标包含 True/False/Unknown 序列；未筛选的 ==0 可能会对健康证书触发告警。这些规则通过了 5 个案例/20 项断言，涵盖健康、NotReady、即将到期警告、严重到期和已过期证书。抓取/指标缺失需要单独设置告警。

```bash
kubectl get certificates,certificaterequests -A
kubectl get orders,challenges -A
kubectl describe certificate app-tls -n demo-app
cmctl status certificate app-tls -n demo-app
# These change resources; check permissions and impact first.
cmctl renew app-tls -n demo-app
```

选择递归 DNS 解析器并不等于延长传播等待时间。请检查分视 DNS、CAA、TXT 授权、CNAME、HTTP 路径以及 Challenge 原因。调整 chart 的 timeoutSeconds（1–30 秒）前，应先调查 webhook 连通性/身份验证/路由问题；没有可盲目套用的通用 webhook-timeout 标志。

<span id="renewal-buffer-configuration"></span>
<span id="backup-ca-strategy"></span>
<span id="multi-tenant-issuer-strategy"></span>
<span id="rbac-configuration"></span>
<span id="private-key-rotation"></span>

## 最佳实践

- [命名空间 Role](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/certificate-requester-rbac.yaml)可管理 Certificates，但不会授予开发人员集群范围的 Secret 读取权限。SAN/issuerRef/secretName 限制需要单独的准入/审批策略。
- 将 CertificateRequest 审批与 CA 凭证访问分离。检查默认审批控制器行为，并在需要时配置 approver-policy 等签发策略。
- CA 密钥备份需要加密、访问控制和恢复测试；不要将明文 Secret YAML 转储到普通目录中。Base64 不等于加密。
- 私有 CA 不能自动作为公有 CA 的备用方案：请验证客户端信任、名称、用途、密钥访问权限和恢复时间。
- secretTemplate 注解/标签只是元数据；它们本身不会激活外部 Secret 同步。
- 分别测试续期、CA 轮换、使用方重新加载和吊销。Schema/Helm 成功并不能证明签发成功。

<span id="table-of-contents"></span>
<span id="key-concepts-summary"></span>
<span id="issuer-selection-guide"></span>
<span id="official-references"></span>
<span id="version-compatibility-matrix"></span>

## 总结和参考资料

本地检查包括固定版本的 Helm/CRD schema、控制器配置解码、6 个续期案例、真实 CSR 生成/签名检查、5 个 Prometheus 案例/20 项断言、24 个图表浏览器案例，以及临时本地 Vault 中的十六种合成签发/CSR 签名案例。未执行外部 CA/ACME 签发、AWS 资源创建、已部署 Vault 登录、网格安装或运行时 mTLS。

- [cert-manager 发布版本](https://cert-manager.io/docs/releases/)
- [cert-manager 1.21.2 发布版本](https://github.com/cert-manager/cert-manager/releases/tag/v1.21.2)
- [CNCF 项目历史](https://www.cncf.io/projects/cert-manager/)
- [证书续期和轮换](https://cert-manager.io/docs/usage/certificate/)
- [CA 签发者的限制](https://cert-manager.io/docs/configuration/ca/)
- [Vault 签发者](https://cert-manager.io/docs/configuration/vault/)
- [Gateway API 签发者集成](https://cert-manager.io/docs/usage/gateway/)
- [trust-manager](https://cert-manager.io/docs/trust/trust-manager/)
- [istio-csr](https://cert-manager.io/docs/usage/istio-csr/)
- [Linkerd 自动证书轮换](https://linkerd.io/2-edge/tasks/automatically-rotating-control-plane-tls-credentials/)
- [ACM Kubernetes 导出](https://docs.aws.amazon.com/acm/latest/userguide/exportable-certificates-kubernetes.html)
- [ACM ACME](https://docs.aws.amazon.com/acm/latest/userguide/acm-acme.html)
- [ACM ACME 发布公告](https://aws.amazon.com/about-aws/whats-new/2026/07/aws-certificate-manager-acme/)
- [AWS Private CA 签发者](https://github.com/cert-manager/aws-privateca-issuer/tree/v1.9.2)
- [Let’s Encrypt 速率限制](https://letsencrypt.org/docs/rate-limits/)
- [暂存环境](https://letsencrypt.org/docs/staging-environment/)
- [停止发送到期邮件](https://letsencrypt.org/2025/01/22/ending-expiration-emails/)
- [Ingress NGINX 退役](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/)
