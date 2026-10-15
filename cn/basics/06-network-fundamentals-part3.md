# 网络基础 第 3 部分 — 十种应用协议

> **最后更新**: September 14, 2026

::: tip 这是一个由四部分组成的系列
[第 1 部分：分层模型、链路层与路由层](./06-network-fundamentals-part1.md) ·
[第 2 部分：传输层与 TLS](./06-network-fundamentals-part2.md) ·
**第 3 部分：应用协议** *(本文档)* ·
[第 4 部分：一个请求的旅程与云](./06-network-fundamentals-part4.md)
:::

传输协议提供流或数据报；应用协议将它们转化为服务。本部分涵盖名称解析（DNS 和 DoH）、引导配置（DHCP）、运维访问（SSH）、邮件（SMTP），以及 HTTP/3、WebSocket、WebRTC、gRPC 和 MQTT。

---

## 5. 应用层 — 实际服务

### DNS

**定义：** 将域名解析为 IP 地址及其他记录的分布式目录系统。

**工作原理：** DNS 使用层级委派。在缓存未命中时，递归解析器会从根域名服务器到 TLD 再到权威名称服务器逐级跟随转介，或将请求转发给另一个解析器。缓存的回答可以避免部分或全部这些工作。A/AAAA 记录包含地址，CNAME 记录包含别名，MX 记录包含邮件服务器，TXT 记录包含多个协议使用的文本。

**实践中：** DNS 是分布式的，但解析器、提供商或配置可能成为共享依赖。进行 DNS 故障切换时，应考虑故障检测、记录更新、已缓存回答的 TTL、应用缓存和现有连接。现在降低 TTL 并不会缩短旧缓存回答的 TTL。某些解析器还会在已定义的故障条件下提供过期回答（RFC 8767）。应测量每个阶段；仅凭较短 TTL 不能保证故障切换时间。负载均衡器和 anycast 可以补充 DNS，但它们自身也有健康检测和收敛限制。

**常见记录类型一览：**

| 类型 | 用途 | 说明 |
|---|---|---|
| A / AAAA | 域名 → IPv4 / IPv6 | 基础记录 |
| CNAME | 别名 → 规范名称 | 不能与根域 SOA/NS 共存；特定提供商的 ALIAS/ANAME 或 Route 53 Alias 可为受支持的目标提供根域映射 |
| MX | 接收邮件的服务器 | 优先级数字越小优先级越高 |
| TXT | 任意字符串 | SPF/DKIM/DMARC、域名所有权验证 |
| NS | 被委派的名称服务器 | 子区域委派 |
| SRV | 服务位置（主机+端口） | 某些协议的发现机制 |
| CAA | 限制已授权的证书颁发者 | 需要 CA 强制执行；其本身无法防止所有错误签发 |

**DNSSEC 和 DoH 解决的是不同问题。** DNSSEC 通过经验证的信任链对已签名的 DNS 数据及其完整性进行认证；它不加密查询。DoH 使用 HTTPS 对所选解析器进行认证，并在客户端到解析器这一跳保护机密性和完整性。它不能证明恶意或出错的解析器返回了权威数据。两者可以结合使用。

![展示递归 DNS 解析：桩解析器的查询经由递归解析器，依次到达根、TLD 和权威名称服务器，回答会按照其 TTL 被缓存。](../.gitbook/assets/en-basics-06-network-fundamentals-part3-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-06-network-fundamentals-part3-0.html)

### DoH

**定义：** 封装在 HTTPS 中并通过 HTTPS 传输的 DNS 查询。

**工作原理：** 传统 DNS 通常使用明文 UDP **和 TCP** 端口 53。DoH 通过 HTTPS 承载 DNS 消息，从而保护其免受该链路上的被动检查和篡改。解析器端点和流量元数据仍可能表明使用了 DoH；所选解析器可以看到查询。

**实践中：** 独立选择的公共 DoH 解析器可以绕过组织解析器上的过滤/日志记录，并且可能无法解析私有名称。DoH 并不会从根本上禁用策略：受管理的 DoH 解析器可以应用日志记录/过滤，浏览器/OS 策略也可以选择经批准的解析器。应测试分割 DNS 和端点策略，而不是假设总是需要禁用加密。

### DHCP

**定义：** 自动为主机分配 IP 地址和网络配置的协议。

**工作原理：** 常见的初始 **DHCPv4** 交换是 DORA：Discover → Offer → Request → Acknowledge。本地广播或 DHCP 中继会定位服务器。租约可包含 IPv4 地址、子网掩码、网关和 DNS 配置。续租可以使用更简短的交换。DHCPv6 使用不同的消息；IPv6 默认路由器信息通常来自 Router Advertisements，而 SLAAC 是另一种地址配置机制。

**实践中：** 在云中，这大多已被抽象化，但在 VPC DHCP 选项集里会再次遇到它，其中配置了 DNS 服务器和域名。当使用本地 DNS 的混合环境发生名称解析故障时，这就是应检查的设置。

### SSH

**定义：** 提供加密远程 shell 访问和隧道功能的协议。

**工作原理：** 服务器使用其主机密钥进行身份验证，密钥交换派生出会话密钥，然后用户进行身份验证（公钥或密码）。所有后续流量均会被加密。除了远程 shell，SSH 还支持端口转发、SFTP 和 agent 转发。

**实践中：** 应根据访问策略限制转发，并验证服务器主机密钥。能够访问已转发 agent socket 的受攻击主机可以向 agent 请求签名/身份验证；转发通常不会将私钥材料复制到该主机。agent 转发不必要时，优先使用跳板主机（`ProxyJump`）。原始密钥没有内在的到期时间，但 OpenSSH 支持证书有效期和 `authorized_keys` 到期限制。移除离职用户的访问权限，并轮换或撤销凭据。

AWS Systems Manager Session Manager 可在不开放入站 SSH 端口或分发 SSH 密钥的情况下提供 shell 访问，前提是已配置受管节点、IAM 权限和服务连接。CloudTrail 会记录 API 活动；将 shell 内容记录到 CloudWatch Logs/S3 需要配置。**Session Manager SSH 和端口转发会话不支持会话内容日志记录。** 仅基于 IAM 的访问并不意味着每条命令都会被记录。

### SMTP

**定义：** 在邮件服务器之间中继消息的协议。

**工作原理：** 客户端将邮件提交给提交服务器，SMTP 服务器中继并接收消息，通常使用 MX 查找进行路由。IMAP 和 POP3 让用户检索或访问已存储在邮箱中的消息；它们不能替代 SMTP 的服务器端接收功能。

**实践中：** SMTP 身份验证和 TLS 可保护提交/传输，但它们本身并不能证明可见发件人域名。以下三种互补的域机制很重要：

- **SPF** — 授权用于信封 MAIL FROM 或 HELO 身份的发送主机；这并不自动等同于可见的 From 标头。
- **DKIM** — 使用签名域的 DNS 密钥验证覆盖的邮件内容签名；签名域可以不同于可见的 From 域。
- **DMARC** — 要求可见 From 域与通过的 SPF **或** DKIM 身份保持对齐，并发布请求的处理/报告策略。

在适当情况下共同配置 SPF、DKIM 和 DMARC，监控报告，并考虑转发/邮件列表行为。只要有一个对齐机制通过，DMARC 就可以通过。这些控制既不保证投递，也不能消除显示名称或形似域名的冒充；接收方还会应用本地策略。

### HTTP/3

**定义：** 运行在 QUIC 上的 HTTP 第三个主要版本。

**工作原理：** HTTP 语义在各版本间共享，但 HTTP/3 使用 QUIC 流以及自己的帧和映射。它移除了 TCP 的跨流顺序依赖；流内丢包、QPACK 依赖和共享拥塞控制仍可能延迟工作。典型的完整握手大约需要 1 RTT，支持的迁移可以在地址变更后保持连接。QPACK 取代 HPACK，以适应独立交付的流。

**实践中：** 客户端可通过 `Alt-Svc`、预先知识或声明支持协议的 HTTPS DNS 记录发现 HTTP/3。`Alt-Svc` 可通过较早的 TCP 连接获知；支持 HTTPS 记录的客户端可以在该交换之前发现 HTTP/3。两种方法都不能保证可达性或特定的延迟节省。

独立交付和集成握手可帮助应对有丢包或高延迟的路径。实际延迟、吞吐量和 CPU 成本取决于实现、卸载、工作负载和网络条件。应测量有代表性的移动和数据中心流量，而不是假设存在普适的收益或损失。

**三代协议并列对比：**

| | HTTP/1.1 | HTTP/2 | HTTP/3 |
|---|---|---|---|
| 传输 | TCP | TCP | QUIC (UDP) |
| 每个连接的请求 | 顺序执行，或使用按序响应的流水线 | 多路复用 | 多路复用 |
| HOL 阻塞 | 按序响应和 TCP 交付 | 跨流的 TCP 顺序 | 没有 TCP 跨流顺序；仍存在其他阻塞 |
| 标头压缩 | 无 | HPACK | QPACK |
| 加密 | 可选（HTTPS） | HTTPS 使用 TLS；也存在明文 HTTP/2 | TLS 1.3 集成在 QUIC 中 |

多路复用改变了顺序依赖出现的位置；HTTP/3 减少了一种阻塞来源，但不会消除所有调度、流量控制或应用依赖。

#### 解读 HTTP/1.1 请求和响应 {#http11-message-structure}

HTTP 版本共享方法、状态码和字段语义。HTTP/1.1 通过 **起始行 → 标头字段行 → 空行 → 可选消息体** 使这些概念可见。消息体可以包含文本或二进制数据；“文本化 HTTP/1.1”描述的是其起始行和标头，而非每个有效载荷。

这些是**示例 HTTP/1.1 消息，并非捕获的输出或命令操作步骤**。为便于阅读，显示中使用 LF 换行符。在网络上传输时，起始行和每个标头行都以 **CRLF (`\r\n`)** 结束，额外的 CRLF 结束标头部分。以下每个消息体均恰好为 **5 个 ASCII 字节**，即 `hello`，且**没有结尾换行符**；关闭围栏前显示的换行不是消息体的一部分。

客户端 → 服务器：

```http
POST /echo HTTP/1.1
Host: example.test
Content-Type: text/plain; charset=utf-8
Content-Length: 5

hello
```

服务器 → 客户端：

```http
HTTP/1.1 200 OK
Date: Mon, 14 Sep 2026 00:00:00 GMT
Content-Type: text/plain; charset=utf-8
Content-Length: 5

hello
```

| 元素 | 解读方式 |
|---|---|
| 请求行 | `POST` 是方法，`/echo` 是请求目标（此处为路径），`HTTP/1.1` 是版本。必需的 `Host` 字段提供目标主机名和可选端口（authority）。 |
| 状态行 | `HTTP/1.1` 是版本，`200` 是状态码，`OK` 是可选原因短语。使用该代码解读结果。 |
| 标头字段 | `Name: value` 行承载元数据；字段名称不区分大小写。`Content-Type` 描述表示形式的媒体类型，在此还描述其字符集。 |
| 空行 | 结束标头部分。它不指定后续消息体的结束位置。 |
| 消息体 | 内容字节。在此，`Content-Length: 5` 界定五个字节，不包括起始行、标头和分隔符。应按字节计数，而不是按 Unicode 字符计数。 |

**语义和分帧回答的是不同问题。** 方法表达所请求的操作：GET 获取表示形式，HEAD 请求相应的响应元数据而不请求响应内容，POST 请求目标处理所提供的内容。状态类别概述结果：1xx 信息性响应、2xx 成功、3xx 重定向、4xx 客户端错误以及 5xx 服务器错误。`Content-Type` 说明如何解释内容；它不界定内容。有关这些共享语义，请参阅 [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)。

HTTP/1.1 分帧确定可复用 TCP 流中有多少字节属于此消息。对于普通的带消息体消息，不含 `Transfer-Encoding` 的有效 `Content-Length` 给出其长度。使用 `Transfer-Encoding: chunked` 时，分块大小和终止的零大小分块，以及其后的任何 trailers 和最终空行，会界定消息体。发送方不得同时发送这两个字段。某些响应以连接关闭作为分隔符；TCP 数据包边界永远不会界定 HTTP 消息。

方法/状态规则优先：对 HEAD 的响应以及状态为 1xx、204 或 304 的响应没有消息体，即使允许的元数据描述了某个表示形式。成功的 CONNECT 响应会启动隧道。没有长度或传输编码的请求没有消息体。这些区别可防止将下一条消息读作内容（[RFC 9112 §§2–6](https://www.rfc-editor.org/rfc/rfc9112.html)）。

**HTTP/2 和 HTTP/3 保留语义，但使用二进制分帧**，包括 HEADERS 和 DATA 帧，而不是这些文本起始行和 CRLF 边界。HTTP/2 使用 TCP；HTTP/3 将消息映射到 QUIC 流。两者均不使用 HTTP/1.1 的 chunked 传输编码。工具可以将已解码字段显示为可读文本，而无需展示其实际的线上编码（[RFC 9113](https://www.rfc-editor.org/rfc/rfc9113.html)、[RFC 9114](https://www.rfc-editor.org/rfc/rfc9114.html)）。

使用 HTTPS 时，TLS 会保护传输中的 HTTP 标头和消息体；没有会话密钥的被动捕获不会暴露此明文（[RFC 8446 §5](https://www.rfc-editor.org/rfc/rfc8446.html#section-5)）。QUIC 同样会保护 HTTP/3 应用数据。应在经授权的端点或 TLS 终止点检查已解码消息，并识别正在观察的连接链路。

> 📎 在将相同区别应用于容器服务、Kubernetes Ingress 或 AWS 负载均衡器之前，请继续进行 [Linux HTTP 消息实验](../networking/07-linux-network-diagnostics.md#http-message-lab)。

### WebSocket

**定义：** 在单个连接上进行双向消息传递的应用协议。

**工作原理：** HTTP/1.1 握手使用 `Upgrade` 和成功的 `101` 响应。HTTP/2 和 HTTP/3 则在受支持时使用 Extended CONNECT（RFC 8441 和 9220）。建立后，任一对等方都可以发送 WebSocket 消息，无需反复进行 HTTP 轮询。

**实践中：** 应为长连接做好规划：在相关空闲超时内发送心跳流量，在 Deployment 期间进行优雅排空，并使用带抖动的重连退避。每个 socket 都保留在其所属实例上。共享应用状态或消息系统（如 Redis Pub/Sub）可以跨实例传递事件，但无法转移存活 socket，也无法单独提供持久化交付。应验证协商 HTTP 版本所使用的握手及代理支持情况。

### WebRTC

**定义：** 用于兼容端点（包括浏览器和媒体服务器）之间实时媒体和数据传输的 API 与协议。

**工作原理：** NAT 可能阻碍直接可达性，但两个位于 NAT 后面的对等方仍可能连接。ICE 会交换并测试主机候选项、服务器反射候选项（通过 STUN 获得）和中继候选项（TURN）。应用信令承载会话描述和候选项。选定路径取决于连通性检查和策略。媒体使用 SRTP，通常使用 DTLS-SRTP 建立密钥；数据通道使用 SCTP over DTLS。

**实践中：** TURN 中继的使用会带来带宽和基础设施成本；即使媒体路径直连，信令、STUN 及其他服务成本仍然存在。NAT 映射/过滤和防火墙行为会影响连通性，因此仅凭“对称 NAT”标签并不能普遍证明中继不可避免。应为 TURN 回退预留预算并测试真实网络。SFU 是一种常见的多方设计，与完整对等网状结构相比，它以服务器带宽/计算为代价降低客户端上传需求。

### gRPC

**定义：** 其标准原生传输使用 HTTP/2 的 RPC 框架，通常配合 Protocol Buffers 服务和消息 schema。

**工作原理：** Protocol Buffers 定义可以生成客户端/服务器代码，并支持一元、服务器流式、客户端流式和双向流式 RPC。二进制编码可以很紧凑，但相对于 JSON 的大小和速度取决于数据、实现和压缩；它们不是协议保证。

**实践中：** 原生 gRPC 很适合许多服务 API。浏览器 API 不会暴露原生 gRPC 所需的全部能力，因此浏览器客户端通常通过兼容服务器或转换代理使用 gRPC-Web；可用的流式模式取决于该实现。应使用 schema 感知工具进行检查和调试。

一个 gRPC channel 可以使用**零个或多个 HTTP/2 连接**，许多 RPC 可以共享一个长连接。L4 均衡按连接选择后端，因此较小的连接池可能集中 RPC 流量；它不能保证按 RPC 分配。应考虑合适的客户端策略或 gRPC 感知的 L7 代理（其可能是 service mesh 的一部分）。已建立的流仍会保留在其选定的后端。对于 schema 演进，请保留已删除的 Protocol Buffers 字段编号/名称，且绝不能复用其编号。

> 📎 有关 Istio 中的 gRPC 处理，请参阅 [Istio gRPC Advanced](../service-mesh/istio/advanced/05-grpc.md)。

### MQTT

**定义：** 轻量级发布-订阅消息协议。

**工作原理：** 客户端连接到 broker 并向主题发布/订阅。固定标头最小可为 2 字节，但真实数据包也可能需要可变标头、属性和有效载荷。QoS 0/1/2 分别提供**相关发送方–接收方链路上的协议级至多一次、至少一次和恰好一次交付**。发布者到 broker 与 broker 到订阅者的交付是分开的。已配置的 Will 可在指定断开条件下发布；MQTT 5 Will Delay 和重连行为会影响其出现时间。

**实践中：** 应根据丢失/重复容忍度和成本选择 QoS。成功的 QoS 2 交付通常会交换 PUBLISH、PUBREC、PUBREL 和 PUBCOMP；它不会使应用数据库副作用或整个业务工作流实现恰好一次。QoS 1 加应用去重是一种可能的权衡。应针对所选产品规划 broker 可用性、持久会话/消息状态和恢复。使用 TLS 和适当的设备身份验证/授权方案；客户端证书是一种选择，但有配置和轮换要求。


**主要参考资料**：[DoH](https://www.rfc-editor.org/rfc/rfc8484.html)、[DNS serve-stale](https://www.rfc-editor.org/rfc/rfc8767.html)、[OpenSSH](https://man.openbsd.org/ssh)、[Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html)、[DMARC](https://www.rfc-editor.org/rfc/rfc7489.html)、[HTTP/3](https://www.rfc-editor.org/rfc/rfc9114.html)、[ICE](https://www.rfc-editor.org/rfc/rfc8445.html)、[gRPC performance](https://grpc.io/docs/guides/performance/)、[MQTT 5.0](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html)。
---

**下一步：** [第 4 部分：一个请求的旅程与云](./06-network-fundamentals-part4.md)
