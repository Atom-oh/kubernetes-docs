# 基础概念：链路本地地址与 SNI

> **范围**：VPC Lattice 服务/资源 API 和 AWS Gateway API Controller；请核对所选版本及已安装的 CRD。
> **最后更新**：2026 年 9 月 13 日

## 本文涵盖内容

- 链路本地地址是什么、Lattice 为什么选择这种地址，以及由此产生的两个运维问题
- 为什么必须以明文发送 SNI：选择证书时会遇到先有鸡还是先有蛋的问题
- 区分服务监听器可见的信息与 TCP 资源连通性，以及后者独立的访问模型

## 链路本地地址

### 定义

链路本地地址来自一个**仅在单条链路（即同一个广播域）内有效**的地址范围。不会跨越路由器，这是它的定义。

| 范围 | 协议 | 作用域 | 标准 |
|---|---|---|---|
| `169.254.0.0/16` | IPv4 | 链路本地 | RFC 3927 |
| `fe80::/10` | IPv6 | 链路本地 | RFC 4291 |

这些范围用于满足一项要求：“**即使没有 DHCP 服务器、也没有路由配置，设备仍必须能够与直接相连的邻居通信**。”因此，这些地址不必在全球唯一，并且可以在每条链路上重复使用。

### AWS 已有的应用

使用过 EC2 的人对这种模式并不陌生。

| 地址 | 用途 |
|---|---|
| `169.254.169.254` | **EC2 实例元数据服务（IMDS）**：实例自身的元数据和 IAM 角色凭证 |
| `169.254.170.2` | ECS 任务凭证端点 |
| `169.254.170.23` | **EKS Pod Identity Agent**（IPv4） |
| `fd00:ec2::23` | EKS Pod Identity Agent（IPv6） |
| `169.254.171.0/24` | **VPC Lattice**（IPv4） |

AWS 为这些地址赋予了特殊行为，但它们的作用域和实现并不相同。必须区分 IPv4 链路本地地址、IPv6 ULA 和节点代理端点。地址标准本身并不能说明流量会被虚拟机监控程序截获。

讨论 Lattice 时，应描述**文档明确说明的 VPC 专属寻址行为**，而不要把它说成链路本地寻址的一般定义，也不要据此推断 AWS 内部实现。

### Lattice 地址范围：IPv4 与 IPv6 的性质不同

VPC Lattice 服务的 DNS 名称会解析为两类地址。

| 范围 | 类型 | 性质 |
|---|---|---|
| `169.254.171.0/24` | IPv4 | **链路本地**（属于 `169.254.0.0/16`） |
| `fd00:ec2:80::/64` | IPv6 | **唯一本地地址（ULA）**（属于 `fc00::/7`，RFC 4193），**不是**链路本地地址 |

> IPv6 ULA **不是链路本地地址，也不是已弃用的站点本地地址类别**。ULA 地址可以在私有网络中路由，且地址具有全局作用域；计划的路由可达范围与地址作用域是不同概念。对于 Lattice，请遵循 AWS DNS 和连通性文档，不要仅凭地址前缀推断其实现方式。

尽管名称不同，两个地址范围在运维上有相同的关键属性：**它们并非全球唯一、会在每个 VPC 内重复使用，并且会被基础设施截获**。

### Lattice 为什么采用这种方式

如[文档 01](./01-appmesh-vs-lattice.md)所述，Lattice 必须在**没有 Sidecar 的情况下**处理流量。没有 Sidecar 时，由谁截获流量？答案是链路本地地址。

工作机制如下：

1. 客户端解析 Lattice 服务的 DNS 名称
2. DNS 返回 `169.254.171.x` 范围内的地址（或 `fd00:ec2:80::` 范围内的地址）
3. 客户端照常连接到该地址；**应用程序并不知道 Lattice 的存在**
4. 发往该地址范围的数据包会被导向 VPC 内的 Lattice 入口端点
5. Lattice 评估监听器规则，选择一个目标，并转发到实际的 Pod IP

流量经过基础设施处理，不需要修改应用代码、Pod 规格或 iptables 规则。**正是这个地址范围，让 Lattice 在移除 Sidecar 后仍能保留流量截获点**。

## 选择链路本地地址带来的两个问题

这个设计很简洁，但也有代价。迁移计划必须考虑以下两个问题。

### 问题 1：与 Envoy 的 iptables 流量截获冲突

Sidecar 网格（App Mesh、Istio）**会通过 init 容器安装 iptables 规则**，将 Pod 流量导向代理。通常的做法是“把该 Pod 的所有出站流量重定向到 Envoy 端口”。

宽泛的出站 REDIRECT 规则可能会截获 Lattice 流量。是否会造成问题，取决于网格策略、已配置的路由和签名设计。在显式添加 CIDR 绕过规则前，请先验证这些设置。

解决办法是**注册例外 CIDR**：将 Lattice 地址范围排除在截获规则之外，让流量绕过 Envoy。

| 网格 | 如何注册例外 |
|---|---|
| App Mesh | 在 App Mesh CNI/init 容器配置的出站忽略 CIDR 列表中加入 Lattice 地址范围 |
| Istio | 将 Lattice 地址范围加入 `traffic.sidecar.istio.io/excludeOutboundIPRanges` 注解 |

共存期间，请验证网格出站策略、已注册的外部目标、签名路径以及两种地址族。部分 Envoy 配置会转发未知目标，受限配置则可能拒绝这些目标。CIDR 排除是一种经过明确设计的绕过方式，并不意味着所有共存网格不采用该做法就一定会失败。

反过来也可以使用同一种机制。[文档 03](./03-auth-flow.md)中的出站代理模式使用 iptables **仅选择 Lattice 地址范围**并将其发送到签名代理：也就是用同一工具实现相反的流量处理方式。

### 问题 2：基于目标 IP 的可观测性和控制失去意义

链路本地地址**并非全球唯一，也无法标识某个服务**。这会破坏现有运维工具所依赖的假设。

| 失效的能力 | 原因 |
|---|---|
| **根据流日志中的目标 IP 识别对端** | 目标始终只显示为 `169.254.171.x`，无法判断它对应哪个 Lattice 服务 |
| **基于目标 CIDR 配置安全组出站规则** | 所有 Lattice 服务都在同一个范围内，无法按服务单独允许或拒绝流量 |
| **基于目标 IP 配置 NetworkPolicy** | 原因相同。Kubernetes NetworkPolicy 的 `ipBlock` 无法区分各个 Lattice 服务 |
| **基于 IP 的监控仪表板和告警** | 仅凭 IP 无法可靠地归属到稳定的服务身份；应补充 DNS、请求 ID 和具备服务信息的日志 |
| **基于 IP 范围的资产清单** | Lattice 服务不会以 IP 地址的形式出现在清单中 |

**替代方案是将控制层迁移到其他位置。**

- **用授权策略表达授权条件，而不是依赖 IP**：主体、路径、方法和标头条件（参见[文档 03](./03-auth-flow.md)）
- **用 Lattice 访问日志观测，而不是依赖流日志**：访问日志会记录调用的是哪个服务
- **使用 AWS 托管前缀列表开放安全组，而不是配置 CIDR**（见下文）

这不是简单更换工具，而是**控制模型发生转变**：从“按 IP 和端口控制”转向“按身份和策略控制”。网络团队现有的大量运维资产在此地址范围内会失效。在金融行业环境中，这可能进一步演变为组织职责边界问题，因此应尽早与网络团队达成一致。

### 使用前缀列表开放安全组

为了接收来自 Lattice 的流量，节点安全组必须允许这些流量。正确做法是使用 **AWS 托管前缀列表**，而不是直接填写 CIDR。

| 前缀列表名称 | 用途 |
|---|---|
| `com.amazonaws.<region>.vpc-lattice` | IPv4 |
| `com.amazonaws.<region>.ipv6.vpc-lattice` | IPv6 |

```bash
# Read-only lookup; apply the reviewed ingress rule through CDK/Terraform.
: "${AWS_REGION:?Set the reviewed AWS Region}"
aws ec2 describe-managed-prefix-lists --region "$AWS_REGION" \
  --query "PrefixLists[?PrefixListName=='com.amazonaws.$AWS_REGION.vpc-lattice'].{Id:PrefixListId,Name:PrefixListName}" \
  --output json
```

在经过审查的 IaC 中，只在实际目标安全组（按配置可能是节点安全组或 Pod 安全组）上，为必需的目标端口、健康检查端口及协议开放适用的 Lattice 前缀列表。避免放行所有协议。还应单独检查客户端/服务网络关联的安全组；上述查询不会更改任何安全组。

## SNI（服务器名称指示）

### 为什么域名必须以明文发送

SNI 是 TLS 扩展，会在 `ClientHello` 中以**明文携带你要连接的服务器域名**。在加密协议的第一条消息中明文放入目标域名似乎很奇怪，但这是无法避免的循环依赖。

**先有鸡还是先有蛋的问题：**

1. 要开始 TLS 连接，服务器必须选择**要出示哪张证书**
2. 证书与域名绑定（`api.example.com` 的证书不同于 `www.example.com`）
3. 如果一个 IP:port 提供多个域名的服务，服务器**必须知道客户端要访问哪个域名**，才能选择证书
4. 但客户端想访问的域名位于 HTTP `Host` 标头中，而 **`Host` 标头在 TLS 内部加密后才会到达**
5. 因此，**开始加密需要先知道域名，而获知域名又要求加密已经开始**

普通 TLS 会在 ClientHello 中发送 SNI，让服务器在读取 HTTP 之前选择证书。这并非唯一可能的设计：ECH 会使用预先获取的密钥加密内部 ClientHello。目前，Lattice TLS Passthrough 要求 SNI 可见，并且不支持 ECH/ESNI。

简而言之，**SNI 明文暴露并非设计错误，而是打破循环依赖的一种有意取舍**。也正因为这种取舍，**不终止 TLS 的中间设备仍能获知目标域名**；TLS Passthrough 路由就建立在这一点上。

### Lattice 如何使用 SNI

在 TLS Passthrough 监听器上，Lattice 不会终止 TLS。那么，**它根据什么选择目标**？依据 SNI。它读取 `ClientHello` 中的明文 SNI 字段，并仅根据该字段进行路由。

## HTTPS 监听器与 TLS Passthrough：Lattice 可以看到什么

| 信息 | HTTPS 监听器（TLS Terminate） | TLS Passthrough |
|---|---|---|
| **SNI（域名）** | ✅ | ✅ |
| **HTTP 路径** | ✅ | ❌ |
| **HTTP 方法** | ✅ | ❌ |
| **HTTP 标头** | ✅ | ❌ |
| **查询字符串** | ✅ | ❌ |
| **`Authorization` 标头（SigV4）** | 可读取；支持经过身份验证的 IAM 请求 | 已加密；无法获得经过身份验证的 SigV4 身份 |
| **请求正文** | ✅（会转发） | ❌ |
| **基于路径/标头的路由** | ✅ | ❌（仅 SNI） |
| **路径/方法/标头条件键** | ✅ | ❌ |
| **访问日志中的 HTTP 详情** | ✅ | 有限 |
| **保留端到端加密** | ❌（在 Lattice 处终止一次） | ✅ |
| **端点自身的 mTLS** | ❌（Lattice 不会请求客户端证书） | ✅（由端点自行执行） |
| **目标组协议** | HTTP / HTTPS | **TCP** |
| **Gateway API 资源** | `HTTPRoute` / `GRPCRoute`（`tls.mode: Terminate`） | `TLSRoute`（`tls.mode: Passthrough`） |

本表概括了这一节最重要的权衡。

> **TLS Passthrough 可保留端点 TLS 并承载端点 mTLS，但 Lattice 无法检查 HTTP 字段，也无法验证其中的 SigV4 标头**。基于匿名网络上下文的授权策略与已验证的调用方身份是两回事。

应**针对每个监听器/路径**选择信任边界，而不要声称一个服务绝不可能配置不同类型的监听器。TLS Passthrough 可以使用基于匿名网络上下文的策略，但不能提供已签名的调用方身份。后端协议应单独配置：HTTPS 监听器可以转发 HTTP 或 HTTPS；当目标连接使用 HTTPS 时，Lattice 不会验证目标证书。

## Lattice 支持的协议

| 监听器协议 | 应用协议 | 目标组协议 |
|---|---|---|
| **HTTP** | HTTP/1.1 | HTTP |
| **HTTPS** | HTTP/1.1、HTTP/2、gRPC（通过 **ALPN 协商**；缺少 ALPN 时使用 HTTP/1.1） | HTTP / HTTPS |
| **TLS_PASSTHROUGH** | （Lattice 不解析） | **TCP** |

**Lattice 没有独立的原始 TCP 监听器**。TCP 仅作为 TLS_PASSTHROUGH 的目标组协议存在。

### 服务监听器与 TCP 资源连通性

VPC Lattice 的**服务监听器**支持 HTTP、HTTPS 和 TLS_PASSTHROUGH。除此之外，**资源配置和资源网关支持 TCP 资源**。服务网络授权策略**不**适用于这些资源配置；应分别评估资源共享、端点/网络控制和资源身份验证。

当你需要受支持的 HTTP 路由和身份验证时，应选择服务模型；如需不具备这些服务功能的 TCP 访问，则应评估资源连通性。没有原始 TCP **服务监听器**属于 API 能力边界，并不意味着网络层面在数学上不可能实现。

- HTTP/HTTPS 服务路由使用受支持的应用层字段。
- TLS Passthrough 要求 SNI 与配置的自定义域名相匹配。
- TCP 资源连通性使用资源配置/资源网关及其独立的关联和访问模型。

对于 HTTP/2 和 gRPC **服务目标协议版本，AWS 要求使用 HTTPS 监听器**；目标组传输协议可按支持情况使用 HTTP 或 HTTPS。不要把后端的明文 HTTP/2 与客户端通过明文 h2c 连接服务监听器混为一谈。如果数据库要先交换初始明文消息、之后才协商 TLS，那么它也不同于要求首先收到 ClientHello 的监听器。

> 已发布的服务监听器限制并未排除 TCP 资源访问。请根据所需的路由和授权模型，评估资源网关、现有私有连接或 NLB。

请参阅最新的[资源配置](https://docs.aws.amazon.com/vpc-lattice/latest/ug/resource-configuration.html)和 [TLS 监听器](https://docs.aws.amazon.com/vpc-lattice/latest/ug/tls-listeners.html)文档。对于这些 AWS API 的 Controller 支持情况，必须与服务本身是否可用分开核实。

## 安全提示：SNI 明文的影响

### 暴露的信息

TLS 会保护通信内容，但**链路上的观察者可以看到你连接的是哪个域名**。这是 TLS 和 SNI 的一般属性，并非 Lattice 特有。

由于这里讨论的是 VPC 内部通信，外部观察者不是主要考虑因素，但仍需了解以下两点。

- **内部观察者可以看到服务调用关系**。任何能够观察 VPC 内流量的人，都可以通过 SNI 还原调用关系图。
- **流日志中的目标 IP 没有意义，但 SNI 有意义**。这也意味着，可借助基于 SNI 的观测，部分弥补上述“基于目标 IP 的可观测性失效”问题。

### ECH：避免 SNI 明文暴露的方案

**加密客户端问候**（Encrypted Client Hello，ECH）是一项用于加密整个 `ClientHello`、以避免暴露 SNI 的标准。它会预先通过 DNS 分发服务器公钥，并用该密钥加密 `ClientHello` 中的敏感部分，**通过 DNS 绕开**前文所述的先有鸡还是先有蛋问题。

::: note TLS Passthrough 要求
AWS 明确指出，TLS 监听器不支持 ECH 或 ESNI，要求使用自定义域名，并通过 SNI 选择服务。在迁移长连接协议之前，请检查空闲时间/连接生命周期限制和目标 TCP 健康检查。
:::

### 对使用基于 SNI 的控制设备的环境的影响

许多组织（包括金融行业的组织）都部署了**基于 SNI 控制流量的设备**，用于允许域名白名单、基于 SNI 记录日志或按域名执行策略。采用 Lattice 会从两个方面影响这些环境。

| 配置 | 从 SNI 控制设备角度看产生的影响 |
|---|---|
| **HTTPS 监听器** | 客户端发送的 SNI 是 Lattice 服务的域名。必须将 **Lattice 域名（`*.vpc-lattice-svcs.<region>.on.aws` 或自定义域名）加入现有白名单**。除此之外，设备无法观察 Lattice → 目标这一段流量 |
| **TLS Passthrough** | SNI 会端到端保留，因此适合与基于 SNI 的控制配合。但你将放弃 IAM Auth |
| **链路本地范围** | 基于目标 IP 的控制设备会失去作用（见上文“问题 2”） |

**如果使用自定义域名，这里就会遇到[文档 03](./03-auth-flow.md)中的 Host 标头陷阱。如果你为了** SNI 控制关联了自定义域名，但签名逻辑仍使用 Lattice 生成的域名，就会收到 403。引入自定义域名时，必须同时确定 SNI 控制、签名中的 Host 值和证书管理方式。

## 总结

- 链路本地地址是一个**标记，表示“由基础设施处理此数据包”**。它与 IMDS 和 Pod Identity Agent 属于同一类地址，也是 Lattice 不使用 Sidecar 截获流量的方式。
- IPv4 使用 `169.254.171.0/24`（链路本地），但 **IPv6 使用 `fd00:ec2:80::/64`，这是 ULA 而非链路本地地址**。Lattice 流量必须能够在 VPC 内路由；链路作用域本身并不足够。
- 验证共存环境中的路由和具备服务信息的归属能力；使用经过审查的前缀列表 IaC，并关联网络日志与应用日志。
- SNI 因为**选择证书时存在先有鸡还是先有蛋的问题**而以明文传输；这是有意的权衡，也使 TLS Passthrough 路由成为可能。
- 如果不终止 TLS，Lattice 无法验证加密的 HTTP SigV4 标头；基于匿名网络上下文的策略与端点身份验证仍是独立的控制措施。
- 原始 TCP 不是服务监听器协议；TCP 资源配置则属于另一个受支持的连通性模型。

下一篇：[工作负载身份迁移](./05-spiffe-to-iam.md)将探讨 IAM 在多大程度上可以接替 SPIRE 的职责。

## 参考资料

- [使用 Amazon VPC Lattice 和 VPC 资源管理 DNS 解析](https://aws.amazon.com/blogs/networking-and-content-delivery/managing-dns-resolution-with-amazon-vpc-lattice-and-vpc-resources/)
- [Amazon VPC Lattice DNS 迁移策略与最佳实践](https://aws.amazon.com/blogs/networking-and-content-delivery/amazon-vpc-lattice-dns-migration-strategies-and-best-practices/)
- [AWS Gateway API Controller：部署 Controller（前缀列表设置）](https://www.gateway-api-controller.eks.aws.dev/latest/guides/deploy/)
- [AWS Gateway API Controller：TLS Passthrough](https://www.gateway-api-controller.eks.aws.dev/latest/guides/tls-passthrough/)
- [使用 Amazon VPC Lattice TLS Passthrough 启用端到端加密](https://aws.amazon.com/blogs/networking-and-content-delivery/enabling-end-to-end-encryption-with-amazon-vpc-lattice-tls-passthrough/)
- [VPC Lattice 服务的 HTTPS 监听器](https://docs.aws.amazon.com/vpc-lattice/latest/ug/https-listeners.html)
- [RFC 3927：IPv4 链路本地地址](https://datatracker.ietf.org/doc/html/rfc3927) / [RFC 4193：唯一本地 IPv6 单播地址](https://datatracker.ietf.org/doc/html/rfc4193)
- [RFC 6066：TLS 扩展：服务器名称指示](https://datatracker.ietf.org/doc/html/rfc6066)
- [网络基础第 2 部分：传输层与 TLS](../../basics/06-network-fundamentals-part2.md)


- [目标组和协议版本](https://docs.aws.amazon.com/vpc-lattice/latest/ug/target-groups.html)：HTTPS 目标证书行为，以及 HTTP/2/gRPC 监听器要求

TLS 监听器还有其他运行限制：只支持默认转发规则，不支持 Lambda 目标，连接时长最长为 10 分钟，服务空闲超时可配置为 60–600 秒。默认情况下，TCP 目标组健康检查**处于禁用状态**；启用时必须使用受支持的探测协议/版本。采用长连接前，请核实当前 API 和区域设置。
