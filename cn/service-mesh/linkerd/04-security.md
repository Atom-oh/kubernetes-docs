# Linkerd 安全

> **最后更新**：2026 年 9 月 11 日 · Linkerd edge-26.9.1 · cert-manager 示例对照 1.21.1 检查

Linkerd 为代理处理的流量提供工作负载身份验证、传输加密和入站授权。纳管、策略、证书生命周期及应用安全仍需明确设计。使用[安装指南](01-installation.md)中的受支持 Kubernetes/Gateway API 组合；此处假定已完成该安装并存在应用工作负载。

## 安全架构

![逻辑签名链和控制平面角色。根签署签发者；Identity 服务使用该签发者签署工作负载证书。图中不意味着根私钥必须存于集群。](../../.gitbook/assets/en-service-mesh-linkerd-04-security-0.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-linkerd-04-security-0.html)

## 自动 mTLS

Linkerd 自动为网格 Pod 间合格 TCP 流量使用 mTLS。两端代理必须参与、信任证书链并接收流量。Skip 端口绕过代理；UDP 不属于此 TCP 机制。与非网格端点之间的流量不会仅因一端有代理就获得 Linkerd mTLS。

应用使用明文 HTTP 时，出站代理验证目标代理并加密网络跳点；接收代理验证调用方，再向本地应用转发 HTTP。应用发起的 TLS 可在网格中保持加密：Linkerd 不会自动解密每条外部或不透明 TLS 流。

| 属性 | 含义和边界 |
|---|---|
| 透明加密 | 合格代理间跳点不要求应用实现 TLS |
| 双向身份验证 | 代理验证工作负载身份，不是终端用户 |
| TLS 1.3 | 所选版本的网格 TLS 协议 |
| 自动叶证书续订 | 代理通常续订短期工作负载证书 |
| 根/签发者生命周期 | 独立凭证，仍需轮换和监控 |

默认 Linkerd 接受非网格来源明文。授权策略可拒绝。因此“启用 mTLS”不同于“所有入站访问都要求经验证的网格身份”。网络策略和准入控制还必须覆盖绕过或缺少代理的路径。

### 观察加密和身份

```bash
linkerd check --proxy
linkerd viz edges deploy -n production
linkerd viz tap deploy/api -n production --method GET
linkerd identity -n production -l app=api
kubectl -n production get pods -l app=api \
  -o custom-columns=NAME:.metadata.name,SERVICEACCOUNT:.spec.serviceAccountName
```

`viz edges` 报告观察到的资源连接及安全状态；不是所有可能或空闲连接的清单。`tap` 展示受支持的观测流量，不是完整数据包/安全审计。其显示接口不同于 Prometheus TLS 标签值。应从目标客户端身份测试接受和有意拒绝的流量。

`linkerd identity` 通过端口转发从选定 Pod 获取公有证书。检查 SAN、签发者和有效期。这样避免假定签发叶证书位于代理镜像固定文件路径。

## 工作负载身份

标准 Kubernetes 身份路径中，Linkerd 使用以下 DNS 形式身份：

```text
<service-account>.<namespace>.serviceaccount.identity.<control-plane-namespace>.<trust-domain>

web.production.serviceaccount.identity.linkerd.cluster.local
api.production.serviceaccount.identity.linkerd.cluster.local
```

示例使用控制平面命名空间 `linkerd` 和信任域 `cluster.local`。根证书 common name 本身不是工作负载信任域设置。这不是此前展示的 Istio 风格 `spiffe://.../ns/.../sa/...` URI。相同 ServiceAccount 的多个 Pod 共享授权身份，但私钥/证书独立。

代理生成密钥和 CSR，将 CSR 与投影 ServiceAccount 令牌发送到 Identity。Identity 使用 Kubernetes TokenReview 验证令牌、检查请求身份，并用**签发者的**密钥签名。根签署签发者，不签署每个代理请求。私钥不从 ServiceAccount 令牌派生。

默认工作负载证书约 24 小时有效，并在到期前刷新。证书请求不生成新 Kubernetes ServiceAccount，续订也不证明每次刷新都轮换全部密钥。生命周期参阅[架构指南](02-architecture.md)。

## 授权策略

这些资源属于 Linkerd `policy.linkerd.io` API。`AuthorizationPolicy` 不是 Gateway API 资源；在 Linkerd 2.12 引入。它可针对使用 Gateway API 定义的路由。

| 资源 | 作用 |
|---|---|
| Server | 选择本命名空间匹配 Pod 上声明的入站端口 |
| 附加到 Server 的 HTTPRoute/GRPCRoute | 选择入站请求子集 |
| MeshTLSAuthentication | 描述允许的网格身份 |
| NetworkAuthentication | 描述允许的客户端 IP 网络；不提供 mTLS |
| AuthorizationPolicy | 身份验证要求匹配时授予目标访问 |
| ServerAuthorization | 较旧的仅 Server 授权；所选 CRD 以 `v1beta1` 支持 |

`ServerAuthorization` 和 `AuthorizationPolicy` 是备选授权机制，不是顺序管道。多个授权可扩大访问；同一 AuthorizationPolicy 中多个 `requiredAuthenticationRefs` 必须**全部**匹配。以命名空间为目标的 AuthorizationPolicy 覆盖其中定义的策略目标，不是每个未声明端口的自动策略。

Server 不得选择重叠 Pod/端口对。在 Pod 规范声明应用端口。即使命名空间默认策略宽松，Server 默认拒绝未匹配流量。`accessPolicy: audit` 可在准备期间帮助观察未匹配流量，但允许该流量，不是强制执行。

### 默认策略

此注解配置已纳管命名空间中新建代理：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  annotations:
    linkerd.io/inject: enabled
    config.linkerd.io/default-inbound-policy: deny
```

更改命名空间注解不会更新现有代理已初始化默认值。协调工作负载专属发布并验证就绪。动态策略 CRD 是独立机制，可不替换每个 Pod 就更新策略。

集群范围 Helm 值为 `proxy.defaultInboundPolicy`，不是 `policyController.defaultPolicy`。将其合并到完整安装 values，保留 CA 配置和发布所有权：

```yaml
proxy:
  defaultInboundPolicy: deny
```

| 默认值 | 含义 |
|---|---|
| all-unauthenticated | 允许流量而不要求网格身份验证；安装默认值 |
| all-authenticated | 要求经过验证的网格客户端，包括适当受信任的多集群客户端 |
| cluster-authenticated | 要求来自同集群的经过验证客户端 |
| cluster-unauthenticated | 允许配置集群网络范围内的客户端，不要求网格身份验证 |
| deny | 拒绝未匹配流量，受显式策略和文档规定探针处理约束 |
| audit | 允许未匹配流量，同时记录审计证据 |

集群范围不是终端用户身份或应用授权边界。验证配置网络及代理可见的源地址。

### 微服务示例

对于这些独立示例资源，在 `production` 准备网格内 frontend/API/PostgreSQL 工作负载，带 `app: frontend/api/postgres`、下方声明端口及对应 ServiceAccount。在 `ingress` 命名空间准备使用 ServiceAccount `edge-gateway` 的网格入口工作负载；仅名称不安装或验证网关。

```yaml
apiVersion: policy.linkerd.io/v1beta3
kind: Server
metadata:
  name: frontend-http
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: frontend
  port: 8080
  proxyProtocol: HTTP/1
  accessPolicy: deny
---
apiVersion: policy.linkerd.io/v1alpha1
kind: AuthorizationPolicy
metadata:
  name: frontend-from-gateway
  namespace: production
spec:
  targetRef:
    group: policy.linkerd.io
    kind: Server
    name: frontend-http
  requiredAuthenticationRefs:
  - kind: ServiceAccount
    name: edge-gateway
    namespace: ingress
---
apiVersion: policy.linkerd.io/v1beta3
kind: Server
metadata:
  name: api-http
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  port: 8080
  proxyProtocol: HTTP/1
  accessPolicy: deny
---
apiVersion: policy.linkerd.io/v1alpha1
kind: AuthorizationPolicy
metadata:
  name: api-from-frontend
  namespace: production
spec:
  targetRef:
    group: policy.linkerd.io
    kind: Server
    name: api-http
  requiredAuthenticationRefs:
  - kind: ServiceAccount
    name: frontend
    namespace: production
---
apiVersion: policy.linkerd.io/v1beta3
kind: Server
metadata:
  name: database-tcp
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: postgres
  port: 5432
  proxyProtocol: opaque
  accessPolicy: deny
---
apiVersion: policy.linkerd.io/v1alpha1
kind: AuthorizationPolicy
metadata:
  name: database-from-api
  namespace: production
spec:
  targetRef:
    group: policy.linkerd.io
    kind: Server
    name: database-tcp
  requiredAuthenticationRefs:
  - kind: ServiceAccount
    name: api
    namespace: production
```

预期调用链为 gateway → frontend → API → database。YAML 中 ServiceAccount 名不够：调用方必须出示该账户经过验证的身份。验证没有更宽泛命名空间/Server 授权同时允许非预期调用方。

没有显式路由附加到 Server 时，Linkerd 通常为声明的 HTTP 健康/就绪探针添加授权。一旦附加 HTTPRoute/GRPCRoute，就不创建默认探针授权；应显式建模必需探针路由及有限访问。不要仅为一个探针成功就给整个业务端口授予未经身份验证访问。

供参考，这个**替代旧版授权**等同于 API 的 frontend 客户端授权，无需与上方 AuthorizationPolicy 组合：

```yaml
apiVersion: policy.linkerd.io/v1beta1
kind: ServerAuthorization
metadata:
  name: api-from-frontend-legacy
  namespace: production
spec:
  server:
    name: api-http
  client:
    meshTLS:
      serviceAccounts:
      - name: frontend
        namespace: production
```

所选版本不提供 `ServerAuthorization/v1beta2`；不要从 Server 版本推断其他资源 API 版本。`client.unauthenticated:true` 允许无网格身份验证客户端，而 `meshTLS.identities:["*"]` 仍要求网格身份，但授权非常宽泛。

### 指标端口和验证

对于 API Pod 上显式声明的**应用指标端口 9091**，授权示例如下：

```yaml
apiVersion: policy.linkerd.io/v1beta3
kind: Server
metadata:
  name: api-app-metrics
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  port: 9091
  proxyProtocol: HTTP/1
  accessPolicy: deny
---
apiVersion: policy.linkerd.io/v1alpha1
kind: AuthorizationPolicy
metadata:
  name: metrics-from-prometheus
  namespace: production
spec:
  targetRef:
    group: policy.linkerd.io
    kind: Server
    name: api-app-metrics
  requiredAuthenticationRefs:
  - kind: ServiceAccount
    name: prometheus
    namespace: monitoring
```

它不同于代理自身管理端口，通常为 **4191**。proxy-init 配置将管理/控制端口排除在普通入站拦截之外。因此 4191 上的 Server 不会将该端点变为 mTLS 保护的应用端口。管理端点使用实际集群/网络控制和受限访问路径。

```bash
kubectl -n production get servers,authorizationpolicies,serverauthorizations
kubectl -n production get server api-http -o yaml
# Set this to an actual selected API Pod.
api_pod=api-example-pod
linkerd diagnostics policy -n production "pod/$api_pod" 8080 -o json
linkerd viz authz deploy/api -n production
```

已知 HTTP 策略拒绝通常产生 HTTP 403；不透明/TCP 流量可在连接层拒绝。策略更改可能中断现有连接。Kubernetes `Forbidden` 事件不是代理授权拒绝的自动逐请求记录。使用策略诊断及适当 HTTP/TCP 授权指标。


## 证书管理

| 凭证 | 用途 | 默认/手动所有权注意事项 |
|---|---|---|
| 信任锚证书包 | 网格接受的公有根 | 通常为 ConfigMap `linkerd-identity-trust-roots`，键 `ca-bundle.crt` |
| Identity 签发者证书/密钥 | Identity 签署工作负载证书所用中间 CA | Secret `linkerd-identity-issuer`；键名取决于签发者方案 |
| 工作负载证书/密钥 | 每代理 TLS 凭证 | 短期叶证书，由代理自动刷新 |

CLI 默认生成根和签发者一年后到期；工作负载叶证书通常 24 小时。可以手动选择十年根，但不是通用建议或安装默认值。根据 CA 策略和恢复流程选择寿命及提前续订时间，跟踪链中每张证书。

Linkerd 提供的根/签发者凭证要求 **ECDSA P-256**。[安装指南](01-installation.md)包含明确生成参数和本地私钥处理。将根签名密钥与公有信任包分离；公有 ConfigMap 绝不能包含该密钥。

### 读取生效公有凭证

```bash
set -euo pipefail
umask 077
# Public trust bundle: ConfigMap data is not base64-encoded.
kubectl -n linkerd get configmap linkerd-identity-trust-roots -o json \
  | jq -er '.data["ca-bundle.crt"] | select(length > 0)' > current-trust.pem
# Select only public certificate data from the issuer Secret, never its key.
kubectl -n linkerd get secret linkerd-identity-issuer -o json \
  | jq -er '(.data["tls.crt"] // .data["crt.pem"]) | select(length > 0)' \
  | base64 -d > current-issuer.pem

# Show every certificate in a multi-root bundle, not only its first entry.
openssl crl2pkcs7 -nocrl -certfile current-trust.pem \
  | openssl pkcs7 -print_certs -text -noout
openssl x509 -in current-issuer.pem -noout -subject -issuer -dates
# Nonzero exit means expiration is within this window or parsing failed.
openssl x509 -in current-issuer.pem -noout -checkend 86400
```

默认 `linkerd.io/tls` 方案中，签发者 Secret 使用 `crt.pem`/`key.pem`；`kubernetes.io/tls` 使用 `tls.crt`/`tls.key`。命令仅选择公有证书数据。更改前检查配置方案和资源所有者。

检查证书包内每个根。单独 `openssl x509` 只检查第一张证书；不是完整多根到期审计。除日期外，还要针对目标信任锚验证签发者链，链需要时提供中间证书。解析或 API 读取失败必须报告为失败，不能报告“证书健康”。

### 信任锚不变时续订签发者

通过所有者更新签发者：Linkerd 管理的 Secret 使用完整 Helm/CLI 证书 values，托管 Secret 使用证书控制器。Identity 监视挂载的签发者文件，验证替换并重新加载有效签发者；每次续订并不都要求全面重启 Identity Deployment。

```bash
kubectl -n linkerd get events --field-selector reason=IssuerUpdated
kubectl -n linkerd get events --field-selector reason=IssuerUpdateSkipped
kubectl -n linkerd logs deployment/linkerd-identity -c identity --tail=100
linkerd check --proxy
linkerd identity -n production -l app=api
```

`IssuerUpdated` 确认 Identity 接受更新。调查 `IssuerUpdateSkipped` 或验证错误。现有代理叶证书可在正常刷新前仍由旧签发者签署；两条证书链有效时这是预期行为。立即替换每张叶证书是独立协调的工作负载操作。

### 信任锚轮换

替换根需要分阶段转换。健康根流程不保证能恢复已过期根。

1. 清点活动根包、签发者链、托管资源及所有使用方，包括控制平面代理、工作负载、外部工作负载和关联集群。确认计划发布的容量/就绪。
2. 生成新根并保留**公有旧根+新根证书包**。通过实际所有者更新证书包。
3. 切换签发者前，将重叠包分发到所有使用方。代理通过安装/注入配置接收信任；仅 ConfigMap 写入不证明现有进程已重载。
4. 用 `linkerd check --proxy` 及工作负载/跨集群检查验证分发。再签发并加载新根签署的签发者。
5. 允许或有意协调叶证书续订，验证全部相关客户端/服务器使用新证书链。固定休眠或仅控制器滚动发布成功不够。
6. 通过证书包所有者移除旧根，将最终包传播到全部使用方，再验证连接和信任。

保留回滚材料并监控每阶段。仅重启已审核的网格工作负载控制器，采用适合工作负载的就绪/中断处理；遍历所有命名空间 Deployment 会遗漏其他工作负载类型，并可能中断无关工作负载。本文不声称未经测试的轮换零停机。

## 外部证书管理

### cert-manager 签发者续订

示例假定 `linkerd` 命名空间的 `linkerd-trust-anchor` Secret 中已有经验证 CA 证书和 ECDSA P-256 签名密钥。cert-manager CA Issuer 将签名密钥保留在集群；若不符合信任模型，应选择不同 CA 集成。所选 cert-manager 版本必须支持集群 Kubernetes 版本。

```yaml
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: linkerd-trust-anchor
  namespace: linkerd
spec:
  ca:
    secretName: linkerd-trust-anchor
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: linkerd-identity-issuer
  namespace: linkerd
spec:
  secretName: linkerd-identity-issuer
  duration: 8760h
  renewBefore: 720h
  issuerRef:
    name: linkerd-trust-anchor
    kind: Issuer
    group: cert-manager.io
  commonName: identity.linkerd.cluster.local
  isCA: true
  privateKey:
    algorithm: ECDSA
    size: 256
    rotationPolicy: Always
  usages:
  - cert sign
  - crl sign
  - server auth
  - client auth
```

签发者是 CA，因为它签署工作负载叶证书。`rotationPolicy: Always` 显式要求密钥轮换。此处 8760h 是 365 天，`renewBefore:720h` 表示**到期前 30 天续订**，不是每 30 天。确保父 CA 剩余有效期足够：CA Issuer 不自动执行全部证书链寿命/路径长度约束，更新其 CA Secret 也不会自动重签所有依赖证书。

```bash
kubectl -n linkerd get issuer linkerd-trust-anchor
kubectl -n linkerd get certificate linkerd-identity-issuer
kubectl -n linkerd describe certificate linkerd-identity-issuer
# Inspect public certificate contents and effective issuer loading as above.
```

Certificate 必须 Ready，Secret 必须有预期键/链，Identity 必须接受，才是正常集成。

### 明确信任包所有权

**选项 A：cert-manager 管理签发者；Helm 管理公有信任包。** 保存为 `managed-issuer-values.yaml`，通过完整已审核 chart values 提供根包：

```yaml
identity:
  externalCA: false
  issuer:
    scheme: kubernetes.io/tls
```

```bash
# Merge into the complete reviewed values from the installation guide.
# In this option, Helm owns the public trust bundle; cert-manager owns the issuer.
helm template linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version 2026.9.1 -n linkerd \
  -f reviewed-values.yaml -f managed-issuer-values.yaml \
  --set-file identityTrustAnchorsPEM=ca.crt > reviewed-control-plane.yaml
```

使用 `kubernetes.io/tls` 时，chart 要求签发者 Secret 已存在，不创建 Linkerd 格式 Secret。`externalCA:false` 时，Helm 仍创建公有信任 ConfigMap。通过安装流程部署前，审核渲染对象和现有所有权。

**选项 B：外部控制器也管理信任 ConfigMap。** 在该不同所有权模型中：

```yaml
identity:
  externalCA: true
  issuer:
    scheme: kubernetes.io/tls
```

`identity.externalCA:true` 表示 chart **不**创建 `linkerd-identity-trust-roots`。trust-manager 等外部控制器必须在控制平面命名空间提供带 `ca-bundle.crt` 的 ConfigMap。仅传入 `identityTrustAnchorsPEM` 而省略外部 ConfigMap，不能完成设置。

托管根轮换时，在重叠包中保留旧**公有证书**，协调签发者续订和使用方发布，再将其退役。不要仅为保留公有证书复制整个 CA Secret。cert-manager/trust-manager 不会自动完成所有工作负载重启和信任转换。

### Vault 集成边界

Vault 可参与 CA 设计，但普通 PKI `sign/<role>` 叶证书签名方案不是完整 Linkerd 签发者流程。Linkerd 要求实际中间 CA 证书；仅在 Certificate 设置 `isCA:true` 不能证明 Vault 端点授予此能力。

验证所选集成的签名端点和请求/响应映射。Vault 文档规定特权 `root/sign-intermediate` 和签发者专属中间证书签名端点；使用权限授予 CA 签发能力，需要有意限制的角色/策略。还要验证 ECDSA P-256、返回证书链、签发者寿命、Vault 服务器信任和续订行为。

对于 cert-manager 身份验证，适当时优先使用文档规定的短期 ServiceAccount 令牌流程，配备必需 TokenRequest RBAC、Vault Kubernetes/JWT 身份验证配置及受众。仅名为 `vault-token` 的 Secret 不够。旧 YAML 遗漏这些前提和经过验证的中间 CA 签发路径，因此不作为已测试部署方案提供。

## 应用安全和监控

| 职责 | Linkerd 提供的能力 | 额外控制 |
|---|---|---|
| 网络跳点 | 合格代理间 mTLS | 其他跳点 TLS、网络限制和端点暴露 |
| 工作负载身份验证 | ServiceAccount 派生网格身份 | 终端用户/API 客户端身份验证及令牌验证 |
| 服务访问 | 入站授权策略 | 应用角色、租户和对象授权 |
| 数据处理 | 不验证业务输入 | 输入验证、输出处理和数据保护 |

允许 frontend 身份不证明其调用者是管理员。应用必须验证用户凭证、业务权限及输入。

### 有意义的安全警报

以下规则要求 Prometheus Operator、选择此 PrometheusRule 的 Prometheus，以及保留所示 namespace/deployment 和代理 TLS 身份标签的抓取。共享后端审核目标和集群范围。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: linkerd-security-alerts
  namespace: monitoring
spec:
  groups:
  - name: linkerd-security
    rules:
    - alert: LinkerdWorkloadCertificateExpiring
      expr: identity_cert_expiration_timestamp_seconds{namespace="production"} - time() < 3600
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Proxy workload certificate has less than one hour remaining
    - alert: LinkerdIssuerCertificateExpiring
      expr: issuer_cert_ttl_seconds{job="linkerd-controller",component="identity"} < 86400
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Identity issuer has less than one day remaining
    - alert: LinkerdInboundHTTPWithoutMeshIdentity
      expr: |-
        ((sum(rate(response_total{namespace="production",deployment="api",direction="inbound"}[5m])) - (sum(rate(response_total{namespace="production",deployment="api",direction="inbound",tls="true",client_id!=""}[5m])) or vector(0))) / sum(rate(response_total{namespace="production",deployment="api",direction="inbound"}[5m])) > 0.10)
        and on() (sum(rate(response_total{namespace="production",deployment="api",direction="inbound"}[5m])) > 0)
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: More than 10% of observed API HTTP responses lack authenticated mesh client identity
    - alert: LinkerdInboundHTTPAuthorizationDenied
      expr: sum(rate(inbound_http_authz_deny_total{namespace="production",deployment="api"}[5m])) > 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: API inbound HTTP authorization denials observed
```

`identity_cert_expiration_timestamp_seconds` 测量**代理叶证书的绝对到期时间**。七天警告总会匹配健康的默认 24 小时叶证书。控制器 `issuer_cert_ttl_seconds` 已是剩余时长；不要再减 `time()`。选择器使用默认 Viz 控制器 job/component 标签；该抓取不添加 namespace 标签。自定义 Collector 改变标签时调整选择器。按配置凭证寿命和预期刷新间隔调整阈值，单独监控公有根和抓取可用性。

所选代理 TLS 标签包括 `true`、`no_identity`、`disabled` 和 `opaque`；原 `tls="false"` 查询未匹配预期序列。仅 `tls="true"` 也可能缺失客户端身份。示例用速率和正流量保护，将已完成入站 API HTTP 响应与同时具有 TLS 及非空已验证 `client_id` 的响应比较。

此比率**不是全部网络字节或全部明文流量的百分比**。不覆盖绕过路径或不透明 TCP，且依赖保留身份标签。预期探针或有意未经认证路由需要自身范围/基线。全部流量均认证且无未认证序列时，底层比例为零，此警报不触发。无流量或缺失数据不证明安全。

HTTP 授权拒绝计数器不同于应用登录失败。不透明连接使用 TCP 授权计数器，不要从缺失抓取推断“无拒绝”。审计模式日志/指标记录被允许的未匹配流量，而非实际拒绝。

## 后续步骤和参考资料

- [可观测性](05-observability.md)、[多集群](06-multi-cluster.md)、[最佳实践](07-best-practices.md)、[安全测验](../../quizzes/service-mesh/linkerd/security.md)
- [自动 mTLS](https://linkerd.io/docs/features/automatic-mtls/)
- [授权行为](https://linkerd.io/docs/features/server-policy/)和 [API 参考](https://linkerd.io/docs/reference/authorization-policy/)
- [Identity CLI](https://linkerd.io/docs/reference/cli/identity/)
- [手动凭证轮换](https://linkerd.io/docs/tasks/manually-rotating-control-plane-tls-credentials/)
- [托管凭证轮换](https://linkerd.io/docs/tasks/automatically-rotating-control-plane-tls-credentials/)
- [代理指标](https://linkerd.io/docs/reference/proxy-metrics/)
- [发布的 Identity 重载/签发者指标实现](https://github.com/linkerd/linkerd2/blob/edge-26.9.1/pkg/identity/service.go)
- [发布 chart 凭证所有权](https://github.com/linkerd/linkerd2/blob/edge-26.9.1/charts/linkerd-control-plane/templates/identity.yaml)
- [cert-manager CA Issuer](https://cert-manager.io/docs/configuration/ca/)和 [Vault 身份验证](https://cert-manager.io/docs/configuration/vault/)
- [Vault 中间证书签名](https://developer.hashicorp.com/vault/api-docs/secret/pki#sign-intermediate)
