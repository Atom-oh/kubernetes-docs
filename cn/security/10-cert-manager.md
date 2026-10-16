# 使用 cert-manager 管理证书

> **最后更新**：October 12, 2026
> **验证基准**：cert-manager 1.21.2、cmctl 2.5.0、trust-manager 0.25.0、istio-csr 0.17.0、aws-privateca-issuer 1.9.2、ACK ACM 1.8.1。cert-manager 1.21 已发布的受支持/已测试 Kubernetes 版本范围为 1.33–1.36；Kubernetes 1.37 不在该范围内，因此本指南不声明与其兼容。

cert-manager 将证书签发和续订作为 Kubernetes 资源进行管理。**CA 信任分发、应用程序重载、吊销以及 CRL/OCSP 操作仍是独立职责。**示例已使用本地 schema、配置和库进行检查；它们并非外部 CA 签发或 AWS/Kubernetes 部署的证据。一项单独的临时本地 Vault 2.1.0 测试使用合成 CA，对十六个签发/CSR 签名接受/拒绝案例进行了测试。

<span id="what-cert-manager-solves"></span>
<span id="project-status"></span>
<span id="why-certificate-lifecycle-automation-matters"></span>
<span id="overview-1"></span>

## 概述

cert-manager 于 2020 年 11 月 10 日加入 CNCF，于 2022 年 9 月 19 日成为孵化项目，并于 **2024 年 9 月 29 日毕业**。毕业并不保证特定部署的安全性或可用性。

| 生命周期关注点 | 职责 |
|---|---|
| 签发 | Issuer 身份验证、请求者批准、SAN/用途/有效期策略 |
| 续订 | 实际签发的有效期、ARI/renewBefore、重试和告警 |
| 密钥轮换 | Secret 访问、使用方重载、CA 轮换顺序 |
| 信任 | 每个 namespace/进程信任哪些根/中间证书 |
| 吊销 | CA 吊销流程以及 CRL/OCSP 的发布/使用 |

不要将旧的 1.16.2 安装和兼容性表格作为当前支持指南。1.16 版本已于 2025 年 6 月结束生命周期（EOL）。请使用中间版本的发行说明和 CRD 变更规划升级。

<span id="component-overview"></span>
<span id="component-responsibilities"></span>
<span id="certificate-issuance-flow"></span>

## 架构

![cert-manager 组件及 Issuer/Secret 关系](../.gitbook/assets/en-security-10-cert-manager-0.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-security-10-cert-manager-0.html)

controller 协调 Certificates 并创建 CertificateRequests；issuer controller 负责处理签发。webhook 对自定义资源进行验证/默认值设置/转换，cainjector 则在受支持的 API/webhook 配置中管理 CA bundle。CA/SelfSigned issuer 不一定是外部服务。

<span id="prerequisites"></span>
<span id="installation-with-helm-recommended"></span>
<span id="production-helm-values"></span>
<span id="installation-with-kubectl"></span>
<span id="verify-installation"></span>

## 安装

检查受支持的 Kubernetes 版本、Helm/cluster 权限、Gateway API CRD 和真实的 Gateway controller，以及可选的 Prometheus Operator CRD。如果在 controller 启动后才安装 Gateway API CRD，请验证重启/发现要求。

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

此配置启用了 ServiceMonitor 和 Gateway API，因此其 CRD/controller 必须已经存在。对于不含这些依赖项的最小安装，请禁用这些选项。副本数/PDB 不能替代节点/AZ 分布和 API 连通性。当前配置使用 config.gatewayAPI.enabled；较旧的 enableGatewayAPI 字段仍会被 1.21.2 解码器接受，但已弃用。

检查 CRD 保留和实际卸载所有权。删除 CRD 可能会删除其自定义资源；这不是常规升级故障排除步骤。

<span id="custom-resource-definitions-crds"></span>
<span id="certificate-resource"></span>
<span id="issuer-vs-clusterissuer"></span>
<span id="certificaterequest-resource"></span>

## 核心概念

![Certificate 资源和 controller 创建的请求](../.gitbook/assets/en-security-10-cert-manager-1.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-security-10-cert-manager-1.html)

| 资源 | 范围和用途 |
|---|---|
| Certificate | namespace 内所需的证书和输出 Secret |
| Issuer | 在其 namespace 内引用的签发配置 |
| ClusterIssuer | 跨 namespace 引用的签发配置 |
| CertificateRequest | CSR、issuerRef 和批准/拒绝状态 |
| Order/Challenge | ACME 路径使用的订购/验证资源 |

ClusterIssuer 的凭据/CA Secret 位于 controller 的 cluster-resource namespace，默认值为 cert-manager。Issuer Secret 位于 Issuer namespace。创建 Certificate 的权限本身并不会限制 SAN 或 issuerRef。

### Certificate 和续订

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

请求的有效期可能与 CA 实际签发的有效期不同。默认续订发生在**实际 X.509 有效期的三分之二处**，而非到期前固定的 15/30 天。renewBeforePercentage 根据实际有效期推导缓冲期。选择 renewBefore 或百分比，不要同时选择两者；duration 至少为 1 小时，有效续订缓冲期必须至少为 5 分钟且短于 duration。

版本 1.21.2 的续订策略/窗口和受支持的 ARI 路径会影响时机。renewal.policy:Disabled 会禁用自动续订。检查 status.renewalTime、实际 notBefore/notAfter 和失败告警。自 1.18 起，privateKey.rotationPolicy 默认为 Always。更新密钥/证书 Secret 并不能保证应用程序重载。

### CertificateRequest 和私钥

直接请求需要真实的 PEM CSR；不要应用截断的 base64 示例。cmctl create certificaterequest **会在 cluster 中创建请求**，并非离线验证命令。单独限制 cmctl approve/deny 权限。本次审计仅使用 cert-manager PKI 库生成并验证合成的本地密钥/CSR。

<span id="selfsigned-issuer-development-testing"></span>
<span id="ca-issuer-internal-pki"></span>
<span id="acme-let-s-encrypt"></span>
<span id="acme-challenge-types"></span>
<span id="http-01-solver"></span>
<span id="dns-01-solver-with-route53-and-irsa"></span>
<span id="aws-private-ca-issuer"></span>
<span id="hashicorp-vault-pki"></span>

## Issuer 类型

### SelfSigned 和 CA 引导

[完整引导示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/bootstrap.yaml)创建专用的实验室根证书和叶证书。根证书明确使用 renewal Disabled 和密钥轮换 Never，以避免**计划外的信任锚替换**。生产根证书托管、离线 CA、中间证书隔离、审计和吊销需要单独设计。

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

CA issuer 使用包含 CA 证书/私钥的 Secret。替换该 Secret 不会立即重新签发每个叶证书或更新每个客户端信任库。CA issuer 可包含 CRL/OCSP URL，但不会生成或维护 CRL/OCSP 响应。实施策略以防止叶证书的存活时间超过其 CA。

### ACME：HTTP-01 和 DNS-01

![ACME HTTP/DNS 验证和签发](../.gitbook/assets/en-security-10-cert-manager-2.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-security-10-cert-manager-2.html)

HTTP-01 需要通过端口 80 访问 hostname，且不支持通配符。DNS-01 使用 DNS TXT 权限进行通配符验证。重复使用的授权和 ACM 的预验证流程意味着不一定会为每个请求都创建新的 Challenge。

不要推荐维护已于 2026 年 3 月结束的社区 ingress-nginx 作为新安装的默认选项。[HTTP-01 Gateway 示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/public-staging.yaml)假设已安装 Envoy Gateway 及其 envoy-gateway GatewayClass。验证实际 class，并使 solver namespace 的 cert-manager-http01:enabled 标签与 allowedRoutes 对齐。Gateway 证书 shimming 不会安装 Gateway controller 或实现其 TLS 重载。

[Route53 issuer](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/route53-issuer.yaml)和[IAM 策略](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/route53-policy.json)指定 hostedZoneID，并将变更限制为 Challenge TXT 名称。指定 zone 可避免要求全局 ListHostedZonesByName 访问权限。通过 IRSA 或受支持的 Pod Identity 以及任何跨账户角色链验证 controller 凭据。namespace 选择和 dnsZones 不能替代 IAM 授权。

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

Let’s Encrypt staging 具有生产浏览器不信任的速率限制和根证书。ACME 账户按环境区分。到期通知电子邮件已于 2025 年停止；email 字段不能替代到期监控。对于 429 响应，应遵循 Retry-After 和相关的补充策略，而不是总在一小时后重试。ARI 续订与新签发有不同的速率限制处理方式。

### AWS Private CA

外部 aws-privateca-issuer controller 需要 CA-ARN 范围内的签发/读取权限和 EKS workload identity。文档规定的操作为 acm-pca:DescribeCertificateAuthority、acm-pca:GetCertificate 和 acm-pca:IssueCertificate；将其 Resource 限制为目标 CA ARN。替换[示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/pca-issuer.yaml)中的实际 CA ARN，并验证 CA 模式、template、算法、用途和请求的有效期。分别检查短期 CA 限制和定价。不要使用 disableApprovedCheck 绕过批准检查。

```bash
helm repo add awspca https://cert-manager.github.io/aws-privateca-issuer
helm upgrade --install aws-pca-issuer awspca/aws-privateca-issuer \
  --version v1.9.2 --namespace cert-manager
```

### Vault PKI

[Issuer/token RBAC 示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/vault-issuer.yaml)将 token 创建限制为 demo-app/vault-issuer。单独提供 Vault server 的 TLS CA Secret。[PKI role/policy 脚本](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/vault-setup.sh)假定现有 PKI/Kubernetes-auth mount、已批准的 Vault identity 以及已配置的 TokenReview 访问。

在 Vault role 中限制 SAN，并将 audience vault://demo-app/vault-pki 绑定到此 Issuer。reviewer JWT、Kubernetes API audience 和 OIDC 访问取决于 Vault 的运行位置。不要以 tls-skip-verify 或宽泛的默认 Vault policy 绕过连通性问题。

<span id="tls-termination-comparison"></span>
<span id="alb-ingress-with-acm-vs-cert-manager"></span>
<span id="nlb-with-tls-termination-at-ingress-controller"></span>
<span id="gateway-api-integration"></span>

DNS role 明确设置 allow_ip_sans=false 和 allow_localhost=false。allowed_domains 不会限制 IP SAN，而 localhost 有单独的宽松默认值。vault write POST 会将省略的 role 字段重置为默认值；应用后读取完整 role，并测试允许的 DNS 请求以及被拒绝的 IP/localhost 请求。

## EKS 集成模式

| 路径 | TLS 终止和密钥位置 |
|---|---|
| 使用 ACM 的 ALB/NLB TLS listener | AWS 负载均衡器使用 ACM ARN |
| 使用 Gateway/Pod 的 NLB TCP | Backend 使用 Kubernetes Secret 终止 TLS |
| Gateway HTTPS listener | Gateway controller 引用同一 namespace 的 TLS Secret |
| 可导出的 ACM 公共证书 | 客户管理的 workload 使用显式导出的密钥/证书 |

ALB 不会直接读取 cert-manager Kubernetes Secret 作为 listener 证书；导入/导出和 ACM ARN 关系是独立步骤。[ALB 示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/alb-acm-ingress.yaml)需要真实的 ACM ARN 和 backend Service。[NLB TCP 示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/nlb-tcp-service.yaml)将 TLS 传递到 backend 端口 8443，该端口必须实际提供 TLS。

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

此 Gateway 使用 lab-ca，普通浏览器并不信任它。真正的公共签发需要经批准的 issuer/domain 验证路径和 controller。验证 GatewayClass 名称和 certificateRefs 范围/类型；避免让两个 controller 拥有同一个 Secret。

<span id="july-2026-update-acm-now-supports-the-acme-protocol"></span>
<span id="supported-certificate-types"></span>
<span id="applicable-scenarios"></span>
<span id="example-defining-a-certificate-via-ack"></span>
<span id="comparison-with-cert-manager"></span>

<span id="aws-native-alternative-acm--ack"></span>

## AWS 原生替代方案：ACM + ACK

### ACM RequestCertificate 和 ACK 导出

ACK ACM 本身是需要安装和运维的开源 controller。1.8.1 [示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/ack-acm.yaml)明确配置 options.export:ENABLED、exportTo 和输出 Secret。仅定义签发请求不会创建 TLS Secret。在 1.8.1 CRD（v1.10.0 中未变）中，validationMethod 仅出现在只读 status domainValidations 字段中，而非 spec 中；不要从旧示例复制到请求中。

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

域验证是独立的。Route53 ACK 可以管理 ACM 提供的 CNAME，但安装 ACM controller 不会自动验证每个 DNS 提供商。评估可导出证书的定价、controller IAM/RBAC/namespace 边界，以及私钥 Secret 访问。Private-CA/SPIFFE mTLS identity 需要自身的 issuer/trust 设计。

### ACM ACME：EAB 和预验证域

ACM ACME 于 2026 年 7 月 6 日发布，可签发 45 天有效期的公共证书。PKI 管理员准备与 IAM role 关联的 endpoint/domain 验证和 EAB 凭据，然后注册客户端。**仅更改 server URL 不够。**安全地存储 HMAC 密钥，并在 cert-manager 的 cluster-resource namespace 中提供 acm-eab Secret/hmac 条目。

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

externalAccountBinding 引用的 Secret 值必须包含 base64url 编码的 HMAC 密钥；Kubernetes Secret 数据编码是单独一层。保留已编码的 provider 值，不要重复编码。请参阅 [ACME EAB 配置](https://cert-manager.io/docs/configuration/acme/)。

Endpoint ID 和 EAB keyID 是占位符。域必须在 endpoint 上预验证。ACME client 生成/持有私钥并管理续订。ACM inventory 中出现 ARN 并不使该证书可直接与托管的 ALB/CloudFront/API Gateway 集成使用。ExportCertificate、RenewCertificate 和 RevokeCertificate 不适用于此签发路径；ACME client 拥有其生命周期。请区分 AWS 集成服务的 RequestCertificate。

<span id="istio-with-istio-csr"></span>
<span id="installing-istio-csr"></span>
<span id="configuring-istio-to-use-istio-csr"></span>
<span id="linkerd-trust-anchor-management"></span>

## Service Mesh 集成

![istio-agent、istio-csr、SDS 和对等 mTLS](../.gitbook/assets/en-security-10-cert-manager-3.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-security-10-cert-manager-3.html)

### Istio 和 istio-csr

在 sidecar 流程中，istio-agent 创建 CSR，istio-csr 提交 CertificateRequest。agent 通过 SDS 将密钥/证书材料传递给 Envoy；workload proxy 建立 mTLS。同一 Pod 内的应用程序 hop 不会自动使用 mTLS。

[istio-csr values](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/istio-csr-values.yaml)为 rootCAFile 配置真实的 ConfigMap volume/mount。先在 cert-manager 中创建应用程序信任 bundle，并等待 issuer 就绪。仅文件路径或 meshConfig 中的空 PEM 均不足够。使用当前的 Istio Helm/istioctl external-CA 设置；不要将 istio-csr 路径与 Kubernetes CSR RA 模式混用。单独评估 Ambient 支持。

```bash
helm upgrade --install cert-manager-istio-csr jetstack/cert-manager-istio-csr \
  --version v0.17.0 --namespace cert-manager --values istio-csr-values.yaml
```

### Linkerd 和 trust-manager

[Linkerd identity 示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/linkerd-identity.yaml)准备 issuer Secret 和 root-bundle ConfigMap。固定版本的 control-plane chart 2026.9.1 引用 linkerd-identity-issuer 和 linkerd-identity-trust-roots。

```yaml
identity:
  externalCA: true
  issuer:
    scheme: kubernetes.io/tls
```

这会将 control plane 连接到由外部续订的 issuer Secret，而不是在安装期间只复制一次密钥。根证书轮换需要旧/新根证书重叠、workload 续订和信任重载。示例实验室根证书为手动管理，且已禁用自动续订。

<span id="installing-trust-manager"></span>
<span id="bundle-resource"></span>
<span id="using-trust-bundles-in-applications"></span>

## trust-manager

默认 trust-manager 0.25.0 chart 渲染 trust.cert-manager.io/v1alpha1 Bundle。仓库中的额外 CRD 本身不会更改默认安装的 API。源 Secret/ConfigMap 从已配置的 trust namespace 读取。

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

内联 PEM 字段是 inLine，而不是 inlineString。最小化公共/私有信任根，并明确选择目标 namespace。Secret target 需要单独启用/RBAC；该示例使用 ConfigMap。信任 bundle 分发信任锚，而非私钥。

[consumer Deployment](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/trust-consumer.yaml)挂载一个目录。ConfigMap 变更不会通过 subPath 文件挂载传播。即使目录投影也不会重载进程缓存的 TLS context；测试应用程序是否实际使用 SSL_CERT_FILE 或其配置的 trust store。

<span id="prometheus-metrics"></span>
<span id="key-metrics"></span>
<span id="prometheusrule-for-alerting"></span>
<span id="certificate-readiness-check"></span>
<span id="common-errors-and-solutions"></span>
<span id="cmctl-cli-tool"></span>

## 监控和故障排除

检查已安装 chart 的 ServiceMonitor 中的 selector 和 port/targetPort 值。1.21.2 配置面向 controller/cainjector/webhook 的 http-metrics。不要杜撰 tcp-prometheus-servicemonitor port 名称。

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

就绪指标包含 True/False/Unknown 序列；未过滤的 ==0 可能会对健康证书触发。这些规则通过了 5 个案例/20 个断言，覆盖健康、NotReady、警告到期、严重到期和已过期的证书。抓取/指标缺失需要单独的告警。

```bash
kubectl get certificates,certificaterequests -A
kubectl get orders,challenges -A
kubectl describe certificate app-tls -n demo-app
cmctl status certificate app-tls -n demo-app
# These change resources; check permissions and impact first.
cmctl renew app-tls -n demo-app
```

选择递归 DNS resolver 不是增加传播等待时间。检查 split-horizon DNS、CAA、TXT 授权、CNAME、HTTP 路径和 Challenge 原因。调整 chart timeoutSeconds（1–30 秒）之前，先调查 webhook 连通性/身份验证/路由；不存在可盲目套用的通用 webhook-timeout 标志。

<span id="renewal-buffer-configuration"></span>
<span id="backup-ca-strategy"></span>
<span id="multi-tenant-issuer-strategy"></span>
<span id="rbac-configuration"></span>
<span id="private-key-rotation"></span>

## 最佳实践

- [namespace Role](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/cert-manager/certificate-requester-rbac.yaml)管理 Certificates，而不向开发人员授予 cluster 范围的 Secret 读取权限。SAN/issuerRef/secretName 限制需要独立的准入/批准策略。
- 将 CertificateRequest 批准与 CA 凭据访问分离。检查默认 approval-controller 行为，并在需要时配置 approver-policy 等签发策略。
- CA 密钥备份需要加密、访问控制和恢复测试；不要将明文 Secret YAML 转储到普通目录中。Base64 不是加密。
- 私有 CA 不是公共 CA 的自动后备方案：请验证客户端信任、名称、用途、密钥访问和恢复时间。
- secretTemplate annotations/labels 是元数据；它们本身不会激活 external-secret 同步。
- 分别测试续订、CA 轮换、使用方重载和吊销。Schema/Helm 成功并不能证明签发成功。

<span id="table-of-contents"></span>
<span id="key-concepts-summary"></span>
<span id="issuer-selection-guide"></span>
<span id="official-references"></span>
<span id="version-compatibility-matrix"></span>

## 总结和参考资料

本地检查包括固定版本的 Helm/CRD schema、controller-config 解码、6 个续订案例、真实 CSR 生成/签名检查、5 个 Prometheus 案例/20 个断言、24 个图表浏览器案例，以及临时本地 Vault 中十六个合成签发/CSR 签名案例。未执行外部 CA/ACME 签发、AWS 资源创建、已部署 Vault 登录、mesh 安装或运行时 mTLS。

- [cert-manager 发行版本](https://cert-manager.io/docs/releases/)
- [cert-manager 1.21.2 发行版本](https://github.com/cert-manager/cert-manager/releases/tag/v1.21.2)
- [CNCF 项目历史](https://www.cncf.io/projects/cert-manager/)
- [证书续订和轮换](https://cert-manager.io/docs/usage/certificate/)
- [CA issuer 限制](https://cert-manager.io/docs/configuration/ca/)
- [Vault issuer](https://cert-manager.io/docs/configuration/vault/)
- [Gateway API issuer 集成](https://cert-manager.io/docs/usage/gateway/)
- [trust-manager](https://cert-manager.io/docs/trust/trust-manager/)
- [istio-csr](https://cert-manager.io/docs/usage/istio-csr/)
- [Linkerd 自动证书轮换](https://linkerd.io/2-edge/tasks/automatically-rotating-control-plane-tls-credentials/)
- [ACM Kubernetes 导出](https://docs.aws.amazon.com/acm/latest/userguide/exportable-certificates-kubernetes.html)
- [ACM ACME](https://docs.aws.amazon.com/acm/latest/userguide/acm-acme.html)
- [ACM ACME 发布](https://aws.amazon.com/about-aws/whats-new/2026/07/aws-certificate-manager-acme/)
- [AWS Private CA issuer](https://github.com/cert-manager/aws-privateca-issuer/tree/v1.9.2)
- [Let’s Encrypt 速率限制](https://letsencrypt.org/docs/rate-limits/)
- [Staging 环境](https://letsencrypt.org/docs/staging-environment/)
- [到期电子邮件已停止](https://letsencrypt.org/2025/01/22/ending-expiration-emails/)
- [Ingress NGINX 退役](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/)