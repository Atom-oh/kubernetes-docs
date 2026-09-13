# Cilium 服务网格安全

> **最后更新**：2026 年 9 月 11 日 · Cilium/chart 1.20.1 · 捆绑 SPIRE 1.15.2。已测试 Kubernetes/EKS 版本及平台要求参阅[概述](./README.md)。

## 概述

评估三个独立控制：工作负载授权、对等身份验证和应用数据加密。Cilium 带外双向身份验证、WireGuard/IPsec 传输加密及独立 ztunnel mTLS beta 有不同要求和限制。

下方策略示例描述普通 Cilium 策略/带外身份验证路径。**不要假定启用 ztunnel 加密后，它们仍保持相同 L4 执行效果**；下文解释 beta 限制。

## 安全架构

![身份/策略、带外身份验证及可选加密方案的逻辑分离。](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-03-security-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-03-security-0.html)

方框按职责分组，不证明每种组合都保留所有策略。尤其 ztunnel beta 使用不同身份/数据路径，其默认 CA 不需要图中带外身份验证所用 SPIRE 集成。

## 双向身份验证和数据加密

### 既有 Cilium 双向身份验证

Cilium 1.20.1 文档仍将带外机制标为 **beta/未完成**。Cilium 代理使用 SPIRE 提供的 SVID 验证 Cilium 安全身份；网络策略规则要求身份验证，不会使应用连接本身变成 TLS。

![策略保护的流量继续传输前，代理之间执行带外身份验证交换的示意。](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-03-security-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-03-security-1.html)

身份验证记录按身份关系缓存。图中不是每次 HTTP 请求都新建证书/握手，也不一定每个应用连接都如此。除身份验证要求外，还应应用明确授权规则。

### 通过 ztunnel 提供原生 mTLS（2026 更新）

Cilium 1.20.1 包含 **Ztunnel 透明加密（Beta）**。准备所需引导/CA 材料后，用此模式片段选择它：

```yaml
encryption:
  enabled: true
  type: ztunnel
  ztunnel:
    ca:
      type: internal
```

发布默认值使用 Cilium 内部 CA 选项。`cilium-ztunnel-secrets` Secret 提供 `bootstrap-private.key`、`bootstrap-root.crt`、`ca-private.key` 和 `ca-root.crt`；官方生成脚本是示例，不是完整生产 PKI/轮换设计。Chart 的 `bootstrapRootCert` 选项仅提供公有证书，不生成内部 CA 所需私钥。

Cilium 代理在已纳管 Pod 网络命名空间中配置 iptables 重定向，将工作负载状态发送到节点 ztunnel，并提供控制/证书接口。Chart 创建 `ztunnel-cilium` DaemonSet。命名空间纳管使用 `io.cilium/mtls-enabled=true`；仅安装模式不会纳管所有命名空间。

发布指南规定以下边界：

- 源和目标工作负载都必须纳管；不支持已纳管与未纳管工作负载间通信。
- 纳管基于命名空间；不支持按 Pod 纳管。主机网络 Pod 无法纳管。
- 仅 TCP 被重定向以使用 mTLS；UDP 和其他协议不属于此加密路径。
- 不支持 ClusterMesh，内核必须支持所需 iptables 操作。
- 加密发生在数据包离开 Pod 之前。因此普通 L4 策略在此路径上不工作，除非直接针对 HBONE 端口 15008。

此集成使用命名空间/服务账户工作负载身份模型。它不同于带外身份验证采用的数值 `/identity/<id>` SPIFFE 路径。

准备好的测试安装可进行以下只读检查：

```bash
kubectl -n kube-system get daemonset ztunnel-cilium
kubectl get namespaces -l io.cilium/mtls-enabled=true
kubectl -n kube-system get configmap cilium-config -o yaml
```

仅命名空间标签、健康代理或观察到端口 15008 数据包，不能证明所有预期流量都已加密和授权。检查成功纳管、所选路径两端、证书身份/信任及不受支持流量情况。

### 何时选择 Cilium 或 Istio 实现 mTLS

根据所需身份、授权和流量覆盖选择。现有 Cilium 部署可使用身份策略加 WireGuard/IPsec，或在限制内评估独立 ztunnel beta。考虑实际启用的额外代理、CA 和运维依赖。

Istio 在 Sidecar 和 Ambient 模式提供工作负载代理 mTLS，各有功能/平台边界。`PeerAuthentication` `STRICT` 是入站 mTLS 要求；本身不签发身份、安装代理或授权所有调用方。不要将比较简化为单个加密开关。[Sidecar/Ambient 章节](../istio/comparison/03-sidecar-vs-ambient.md)保留实际测量的版本和场景。

### 基于 SPIRE 的双向身份验证配置

对于**带外**身份验证，将此覆盖配置合并到安装已审核 values：

```yaml
authentication:
  enabled: true
  mutual:
    spire:
      enabled: true
      trustDomain: spiffe.cilium
      agentSocketPath: /run/spire/sockets/agent/agent.sock
      install:
        enabled: true
        server:
          dataStorage:
            enabled: true
            size: 1Gi
```

为 SPIRE StatefulSet 准备合适 StorageClass/PV。名为 `gp3` 的类不会自动存在于每个 EKS 集群。`authentication.enabled` 必需；信任域和代理套接字设置位于 `authentication.mutual.spire` 下，不在 `install.server` 或 `install.agent` 下。捆绑 chart 不实现此前 `server.replicas`、`server.nodeAttestor`、`agent.workloadAttestor` 或 `server.ca.ttl` 示例。

SPIRE Server 验证代理并签发 SVID。代理执行工作负载证明；Cilium 集成还委托获取并为 Cilium 安全身份注册条目。仅启用 SPIRE 既不强制所有流量身份验证，也不启用 WireGuard/IPsec。

### 双向身份验证策略执行

`authentication` 是**入站/出站允许规则内部的对象**。不是数组，也不是顶层 `spec.authentication` 开关。此集群作用域策略有意只选择一个应用/命名空间：

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: production-backend-auth
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: production
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
```

### 按命名空间双向身份验证

此命名空间示例选择 `production` 中工作负载，并允许该命名空间经过身份验证的对等体访问 TCP 8080：

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: namespace-auth
  namespace: production
spec:
  endpointSelector: {}
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
```

这是同命名空间允许示例，不是每个应用的最小权限。其他端口、客户端、探针和现有策略授权必须单独评估。它影响入站；不会默默配置完整出站依赖策略。

### 按服务双向身份验证

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: service-auth
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: default
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
```

此处源和目标标签描述工作负载，不是终端用户登录。Kubernetes 权限必须控制谁能创建工作负载、更改标签或使用其服务账户。

## CiliumNetworkPolicy L7 规则

### HTTP L7 安全策略

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: http-security-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: default
      k8s:app: api-server
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:role: reader
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/api/.*$
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:role: admin
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^(GET|POST|PUT|PATCH|DELETE)$
          path: ^/api/.*$
          headers:
          - Authorization
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:app: monitoring
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/health$
        - method: ^GET$
          path: ^/metrics$
```

一个规则内的 HTTP 规则是备选条件。`headers: [Authorization]` 仅要求存在：不验证 Bearer 令牌、签名、到期或权限。之前 `Authorization: Bearer .*` 字符串不是 JWT 验证器，也不是通用正则值匹配。独立执行应用身份验证和授权。

HTTP 路径策略需要受支持且可检查的 L7 路径。应用 TLS、探针和其他依赖流量需要相关配置；仅端口号不会启用 TLS。

### Kafka L7 安全策略

旧 `rules.kafka` 对象被 Cilium 1.20.1 L7 模式拒绝。下方替代配置**仅限制网络可达性**：

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: kafka-network-boundary
  namespace: kafka
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: kafka
      k8s:app: kafka
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kafka
        k8s:role: producer
    toPorts:
    - ports:
      - port: '9092'
        protocol: TCP
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kafka
        k8s:role: consumer
    toPorts:
    - ports:
      - port: '9092'
        protocol: TCP
```

为 produce/fetch、主题和消费者组配置实际 Kafka 监听器 TLS/SASL 和代理 ACL。移除过时 L7 规则留下的是 L4 访问；不会保留主题级授权。

### DNS L7 安全策略

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: dns-security
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: default
      k8s:app: web-application
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
      rules:
        dns:
        - matchPattern: '*.*.svc.cluster.local'
        - matchName: api.stripe.com
        - matchName: sts.us-east-1.amazonaws.com
  - toFQDNs:
    - matchName: api.stripe.com
    - matchName: sts.us-east-1.amazonaws.com
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

示例假定 `kube-system` 中 CoreDNS 端点带 `k8s-app=kube-dns` 标签，并使用普通 `cluster.local` DNS 后缀。它允许 UDP 和 TCP DNS。Service FQDN 包含服务和命名空间两部分，因此 `*.*.svc.cluster.local` 不同于旧 `*.svc.cluster.local`。

外部 HTTPS 权限独立于 DNS 查询权限。`sts.us-east-1.amazonaws.com` 是具体区域 AWS 端点；AWS 不使用旧 `api.aws.amazon.com` 作为通用 API 端点。选择实际 SDK 区域/服务端点，包括相关 IPv6/双栈或私有端点变体。内部 DNS 应答不会自动授予连接每个内部 Service 的权限。

审核解析器搜索列表行为，启用 NodeLocal DNS 时也要审核。宽泛 S3 通配符可能允许访问超出目标桶的目的地，DNS/IP 策略不保证阻止通过获准目的地外传数据。

## 双向身份验证

### 身份验证模式

| 模式 | 带外策略 API 中的含义 |
|---|---|
| `required` | 对匹配且允许的流量要求成功身份验证 |
| `disabled` | 对匹配规则显式豁免身份验证 |
| `test-always-fail` | 有意使身份验证失败的测试模式 |

发布模式中没有 `optional` 模式。其他规则重叠时，缺少显式要求与精细限定豁免不同；检查最终策略，不要假定身份验证规则像普通独立允许授权一样工作。

### 双向身份验证策略示例

豁免应明确、范围狭窄且有依据：

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: authentication-exception
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: production
      k8s:app: secure-service
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
        k8s:app: trusted-client
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
    authentication:
      mode: required
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: monitoring
        k8s:app: prometheus
    toPorts:
    - ports:
      - port: '9090'
        protocol: TCP
    authentication:
      mode: disabled
```

Prometheus 规则是**禁用身份验证**，不是“尽可能验证”。它仅允许所述监控工作负载和端口。任一应用监听端口上的 TLS 都是独立应用配置。

### 基于 SPIFFE ID 的身份验证

对于默认**带外** SPIRE 信任域，Cilium 安全身份形式如下：

```text
spiffe://spiffe.cilium/identity/<numeric-security-identity>
```

通过端点/身份策略选择获准对等体；`authentication` 对象没有任意 SPIFFE ID 允许列表字段。将注释改成 Istio 式 `/ns/.../sa/...` URI 不会限制访问。上方 ztunnel beta 使用独立工作负载身份模型。

## 加密

### WireGuard 透明加密

```yaml
encryption:
  enabled: true
  type: wireguard
```

Cilium 创建节点密钥对，并通过 CiliumNode 信息分发公钥。**不同节点**上 Cilium 管理 Pod 之间受支持流量被加密；同节点流量不加密。内核必须提供 WireGuard 支持。Chart 没有 `encryption.wireguard.userspaceFallback` 选项。

允许所需节点间 UDP 51871 路径，并考虑 MTU/封装。AWS VPC CNI 链式模式有额外 MTU 要求，包括文档中的 `cni.enableRouteMTUForCNIChaining` 设置；遵循所选安装模式，不要盲目应用。

#### WireGuard 架构

![Cilium 代理逻辑管理节点间 WireGuard，由内核 WireGuard 接口执行加密。](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-03-security-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-03-security-2.html)

Agent 方框代表管理/密钥分发，不是每个数据包的用户态中转跳点。在 WireGuard 接口抓包可看到明文内部数据包；评估加密时验证正确外层网络路径。

节点间覆盖是独立 beta 选项：

```yaml
encryption:
  enabled: true
  type: wireguard
  nodeEncryption: true
```

默认将控制平面节点排除在节点加密之外，避免密钥更新引导失败。发布流量矩阵还指出涉及 XDP 加速、非 Geneve DSR 和出口网关回复的排除项。外部请求从客户端到集群的一段不由节点 WireGuard 加密。

### IPsec 加密

```yaml
encryption:
  enabled: true
  type: ipsec
  ipsec:
    secretName: cilium-ipsec-keys
    keyFile: keys
    keyWatcher: true
    keyRotationDuration: 5m
```

Secret 必须存在于 Cilium 命名空间。文档中的 AES-GCM 示例，其 `keys` 条目形式为：

```text
3+ rfc4106(gcm(aes)) <fresh-20-byte-random-value-in-hex> 128
```

`+` 选择每隧道派生密钥。无 `+` 的旧全局密钥形式因安全原因弃用；不要将其作为当前指导复制。通过文档规定的 CLI/Secret 流程生成并保护新密钥材料，不复用示例密钥。

`keyRotationDuration: 5m` 是密钥更改后的转换/旧密钥清理宽限期，**不是每五分钟生成新密钥的调度器**。通过受支持轮换流程更新密钥 ID 和材料，使用 ClusterMesh 时协调所有集群，升级期间节点版本混合时不要轮换。

检查 ESP/防火墙支持、实际加密接口和原生路由 CIDR。当前 IPsec 配合 L7 时要求文档规定的透明 DNS 代理行为，不支持 CNI 链式模式或主机策略，也不加密同节点流量。

### 加密比较

| 主题 | WireGuard | IPsec | ztunnel beta |
|---|---|---|---|
| 密钥/身份 | 节点生成密钥对 | 分发密钥材料并按隧道派生 | 工作负载 mTLS 证书及引导/CA 材料 |
| 数据路径 | 内核 WireGuard 接口 | 内核 IPsec/XFRM | 每节点 TLS 代理及 Pod 命名空间重定向 |
| 同节点/覆盖 | 同节点流量不加密；使用发布流量矩阵 | 同节点流量不加密；受模式限制 | 两端均纳管；仅 TCP；受策略限制 |
| 密码套件配置 | WireGuard 协议的 ChaCha20-Poly1305 套件 | 内核支持的已配置算法，如 AES-GCM | 受支持代理协商的 TLS |
| 性能 | 测量实际 CPU、MTU 和流量组合 | 测量算法/硬件、隧道和单隧道解密约束 | 测量代理、TLS 和工作负载开销；未包含在旧比较基准中 |

透明加密也可能存在端点发现窗口，此时允许的未知目的地被视为外部。Cilium 文档将受限出站和加密严格模式作为缓解措施，但有具体限制：严格出站依赖 IPv4/CIDR；严格入站要求 WireGuard 和托管接口，不支持 CNI 链式模式。不要将“已启用加密”解释为每条路径都具备失败时拒绝访问保护的证明。

## 基于身份的安全

### Cilium 身份

Cilium 为一组与身份相关的标签分配数值身份；多个 Pod 可共享它。它不是用户计算的哈希或永久 Pod 标识符。

### 身份组成

```bash
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
CILIUM_POD='<agent-on-the-workload-node>'
kubectl -n default get ciliumendpoints
kubectl get ciliumidentities
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg identity list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg encrypt status
```

命名空间、服务账户和选定工作负载标签可参与其中。ID 1–6 对应 host、world、unmanaged、health、init 和 remote-node；分配的工作负载 ID 取决于安装。检查相关节点代理，保留完整命令失败/状态。

### 基于身份的策略

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: identity-based-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: default
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:app: frontend
        k8s:environment: production
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: monitoring
        k8s:app: prometheus
    toPorts:
    - ports:
      - port: '9090'
        protocol: TCP
```

### IP 与身份比较

![身份选择器避免每次 Pod 变化都手动重写地址列表，但 Cilium 仍维护地址到身份的状态。](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-03-security-4.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-03-security-4.html)

IP 变化时策略选择器可保持稳定。Cilium 仍需更新端点/IP 缓存状态，身份也可能被垃圾回收并重新分配；图表不承诺每次重启后数值 ID 不变。

## 外部 PKI 集成

### cert-manager 集成

这些对象演示生成上游 CA Secret。**它们本身不会将该 Secret 连接到 SPIRE**：

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: cilium-ca-issuer
spec:
  ca:
    secretName: cilium-ca-secret
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: cilium-spire-ca
  namespace: cilium-spire
spec:
  secretName: spire-ca-secret
  duration: 8760h
  renewBefore: 720h
  isCA: true
  privateKey:
    algorithm: ECDSA
    size: 256
    rotationPolicy: Always
  usages:
  - cert sign
  - crl sign
  subject:
    organizations:
    - Cilium
  commonName: SPIRE upstream CA
  issuerRef:
    name: cilium-ca-issuer
    kind: ClusterIssuer
    group: cert-manager.io
```

在 cert-manager 配置的集群资源命名空间内，于 `cilium-ca-secret` 准备有效签名 CA/密钥，并保证足够剩余寿命。验证 CA 约束、签名用途和信任链。一年时长是下级 CA 寿命示例，不是通用建议。

外部管理的 SPIRE 服务器必须使用受支持 UpstreamAuthority，并访问所需挂载材料或签发者 API。对于加入现有 PKI 的磁盘授权机构，SPIRE 需要 `cert_file_path`、`key_file_path` 和可信根 `bundle_file_path`；规划重新加载/轮换和信任重叠。仅 Kubernetes Secret 更新不能证明每个证书使用方都采用新 CA。

不要用不完整无关文件替换捆绑 SPIRE ConfigMap。外部运维 SPIRE 时，单独审核 Cilium 外部服务器地址、信任域、委托身份注册和身份验证前提条件。

### Vault 集成

下方仅为独立配置的 SPIRE 1.15.2 服务器的**插件片段**，不是完整服务器配置或 Kubernetes Deployment：

```hcl
plugins {
  UpstreamAuthority "vault" {
    plugin_data {
      vault_addr = "https://vault.vault.svc:8200"
      pki_mount_point = "pki"
      ca_cert_path = "/vault/ca/ca.crt"
      k8s_auth {
        k8s_auth_mount_point = "kubernetes"
        k8s_auth_role_name = "spire-upstream"
        token_path = "/var/run/secrets/vault/token"
      }
    }
  }
}
```

插件位于顶层 `plugins`，不在 `server` 内。字段为 `pki_mount_point`；此处 `token_path` 位于 `k8s_auth` 内。令牌是用于配置 Vault 认证角色的投影 Kubernetes 服务账户令牌，不是通用 Vault 令牌文件。

准备令牌投影/受众和 Vault Kubernetes 身份验证配置，将角色绑定到目标 SPIRE 工作负载，挂载验证 Vault 所用 TLS CA，并授予所需 PKI sign-intermediate 操作。协调 SPIRE `ca_ttl`、Vault PKI TTL、工作负载信任和轮换。本指南不声称已部署或测试这些外部依赖。

## 零信任网络

### 默认拒绝策略

此集群作用域资源有意针对隔离的 `policy-lab` 命名空间：

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: policy-lab-default-deny
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: policy-lab
  enableDefaultDeny:
    ingress: true
    egress: true
  ingress: []
  egress: []
```

`enableDefaultDeny` 标志为显式设置：仅空 Cilium ingress/egress 数组本身不提供启用默认拒绝的规则。不要照搬 Kubernetes NetworkPolicy 示例中的假设。

将 DNS 等具体依赖添加为独立允许规则：

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: policy-lab-dns
  namespace: policy-lab
spec:
  endpointSelector: {}
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
```

不存在必须允许所有主机网络流量的通用要求。评估实际 kubelet/探针、解析器和主机策略行为。这些示例不更改 Cilium 主机处理，也不防御被攻陷的特权节点。

### 最小权限访问

此示例假定 `edge` 中存在 Cilium 管理、带 `app=ingress-gateway` 标签的网关工作负载，`production` 中存在 frontend/database 工作负载，并有正常 SPIRE 集成：

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: production-security
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: production
      k8s:app: api
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: edge
        k8s:app: ingress-gateway
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
        k8s:app: database
    toPorts:
    - ports:
      - port: '5432'
        protocol: TCP
    authentication:
      mode: required
```

使用在所选网关实现中实际观察的标签和身份。Cilium 自身节点 Envoy 入口/Gateway 路径及外部负载均衡器可能暴露不同身份；任意 Pod 标签不能与 `reserved:ingress` 或外部客户端地址互换。此前已退役的 ingress-nginx 示例不是必需依赖。

### 微分段

这些应用层策略为发起 Service 查找的层保留显式 DNS 访问。它们假定相同网关模型和所述监听端口：

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: frontend-policy
  namespace: app
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: app
      k8s:tier: frontend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: edge
        k8s:app: ingress-gateway
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: app
        k8s:tier: backend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-policy
  namespace: app
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: app
      k8s:tier: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: app
        k8s:tier: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: app
        k8s:tier: database
    toPorts:
    - ports:
      - port: '5432'
        protocol: TCP
    authentication:
      mode: required
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: database-policy
  namespace: app
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: app
      k8s:tier: database
  enableDefaultDeny:
    egress: true
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: app
        k8s:tier: backend
    toPorts:
    - ports:
      - port: '5432'
        protocol: TCP
    authentication:
      mode: required
  egress: []
```

数据库显式启用出站默认拒绝且无出站允许规则；对获准连接的有状态回复仍允许。有计划地添加真实备份、复制、身份验证或其他依赖。限制网络路径不能完全防止通过本来获授权的数据库/应用请求提取数据。

## 安全审计和监控

### 策略审计模式

`cilium.io/audit-mode: "true"` 不是受支持的每策略审计开关。带此任意注解的策略仍可能正常强制执行。

对于**隔离端点测试**，实际可变端点选项是 `PolicyAuditMode`。检查本地端点，临时启用，并在受控观察后恢复执行：

```bash
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint list
ENDPOINT_ID='<local-endpoint-id-in-the-isolated-test>'
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint config "$ENDPOINT_ID"
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint config "$ENDPOINT_ID" PolicyAuditMode=true
# Observe the controlled test, then restore enforcement.
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint config "$ENDPOINT_ID" PolicyAuditMode=false
```

这更改该端点的执行，而不是给一个策略对象附加审计行为。不要推断每次 L7 拒绝或安全失败都变成获准审计事件；验证具体数据路径/代理行为。`enableDefaultDeny: false` 也不等于 L7 审计模式。

### 策略违规监控

```bash
# Terminal 1
cilium hubble port-forward --port-forward 4245
# Terminal 2
hubble observe --server localhost:4245 --namespace production --verdict DROPPED --last 100
hubble observe --server localhost:4245 --namespace production --verdict DROPPED --drop-reason-desc POLICY_DENIED --last 100
hubble observe --server localhost:4245 --namespace policy-lab --verdict AUDIT --last 100
```

`DROPPED` 包含策略拒绝之外的原因。按原因过滤的查询聚焦报告的策略拒绝丢弃；L7/应用授权失败需要独立观察。`AUDIT` 不同于 `DROPPED`。`--last 100` 是有界历史，Relay 可按每个连接的 Hubble 实例返回该数量；不是完整集群流量计数器。仅在有意流式观察时添加 `--follow`。

### Prometheus 指标

```yaml
prometheus:
  enabled: true
hubble:
  enabled: true
  metrics:
    enabled:
    - dns
    - drop
    - flow
    - httpV2
    - icmp
    - port-distribution
    - tcp
```

除这些启用标志外，代理和 Hubble 导出器还需要 Prometheus 发现/抓取。`httpV2` 替代已弃用的 `http`；不要同时启用。HTTP 指标需要对应 L7 可见性。

- `cilium_drop_count_total` 按原因/方向统计丢弃数据包，不仅是策略违规。
- `cilium_forward_count_total` 统计转发数据包，不是成功应用请求。
- Hubble `drop` 导出器以 `hubble_drop_total` 暴露流丢弃信息；计量单位不同于代理数据包计数器。
- 之前 `cilium_policy_verdict` 不是文档规定的指标名。使用实际策略裁决事件，或所选导出器暴露的指标。

## 后续步骤

- [可观测性](./04-observability.md)
- [Ingress 和 Gateway](./05-ingress-gateway.md)
- [最佳实践](./06-best-practices.md)
- [安全测验](../../quizzes/service-mesh/cilium-service-mesh/security.md)

## 参考资料

- [Cilium1.20.1 双向身份验证](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
- [身份验证示例/API 结构](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/mutual-authentication/mutual-authentication-example.rst)
- [Cilium1.20.1 CNP 模式](https://github.com/cilium/cilium/blob/v1.20.1/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnetworkpolicies.yaml)
- [Cilium1.20.1 ztunnel beta](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst)
- [Ztunnel CA 实现](https://github.com/cilium/cilium/blob/v1.20.1/pkg/ztunnel/ca/ca_server.go)
- [Ztunnel 引导示例](https://github.com/cilium/cilium/blob/v1.20.1/examples/kubernetes-ztunnel/generate-secrets.sh)
- [加密范围/严格模式](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption.rst)
- [WireGuard](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-wireguard.rst)
- [IPsec 和密钥轮换](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ipsec.rst)
- [Helm values](https://github.com/cilium/cilium/blob/v1.20.1/install/kubernetes/cilium/values.yaml)
- [HTTP/DNS 策略](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/policy/layer7.rst)
- [默认拒绝行为](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/policy/intro.rst)
- [显式默认拒绝 API](https://github.com/cilium/cilium/blob/v1.20.1/pkg/policy/api/rule.go)
- [可变端点审计选项](https://github.com/cilium/cilium/blob/v1.20.1/pkg/option/endpoint.go)
- [端点配置 CLI](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/cmdref/cilium-dbg_endpoint_config.md)
- [指标](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/observability/metrics.rst)
- [SPIRE1.15.2 服务器配置](https://github.com/spiffe/spire/blob/v1.15.2/doc/spire_server.md)
- [SPIRE Vault 授权机构](https://github.com/spiffe/spire/blob/v1.15.2/doc/plugin_server_upstreamauthority_vault.md)
- [SPIRE 磁盘授权机构](https://github.com/spiffe/spire/blob/v1.15.2/doc/plugin_server_upstreamauthority_disk.md)
- [Kafka ACL](https://kafka.apache.org/41/security/authorization-and-acls/)
- [AWS STS 端点](https://docs.aws.amazon.com/general/latest/gr/sts.html)
- [WireGuard 协议](https://www.wireguard.com/protocol/)
- [NIST 零信任架构——扩展阅读](https://www.nist.gov/publications/zero-trust-architecture)
