# 网络基础知识第 3 部分测验：应用层协议

> **最后更新**：2026 年 9 月 14 日

测试你对 10 种应用层协议的理解，范围从 DNS 到 MQTT。

## 选择题

1. 启用 HTTP/3 后却没有提速时，哪项传输层检查有帮助？
   - A) 服务器证书的到期日期
   - B) UDP 443 是否可达，以及是否实际协商了 HTTP/3
   - C) DNS TTL 设置
   - D) HTTP/2 标头压缩（HPACK）设置

<details>
<summary>显示答案</summary>

**答案：B) UDP 443 是否可达，以及是否实际协商了 HTTP/3**

**说明：**
HTTP/3 通常通过 UDP 443 使用 QUIC。如果这条路径被阻止，客户端在可用时可能改用基于 TCP 的 HTTP/2 或 HTTP/1.1。比较性能前应先验证协商出的协议。丢包、RTT、工作负载、实现方式以及 CPU/卸载行为都会影响结果；本题并不能确定真实事件的原因。

</details>

2. 权威 DNS 记录变更后，哪些因素可能延迟 DNS 故障转移？
   - A) DNS 只使用 TCP，因此握手成本很高
   - B) 之前缓存的应答、应用程序缓存和现有连接可能在记录变更后继续有效
   - C) 根名称服务器必须批准此次更新
   - D) A 记录不能更改

<details>
<summary>显示答案</summary>

**答案：B) 之前缓存的应答、应用程序缓存和现有连接可能在记录变更后继续有效**

**说明：**
新近调低的 TTL 不会缩短已按旧 TTL 缓存的应答的有效期。故障检测、记录更新、应用程序缓存和连接复用也会影响恢复。根据定义的故障条件，解析器可能会提供过期数据（RFC 8767）。DNS、负载均衡器和 Anycast 设计都需要测量故障和收敛行为。

</details>

3. 浏览器选择未经批准的公共 DoH 解析器时，可能出现什么策略问题？
   - A) 因为 DNS 应答会变大并浪费带宽
   - B) 它可能绕过组织的解析器策略，并且无法解析私有名称
   - C) 因为 UDP 端口 53 会过载
   - D) 因为它与 DNSSEC 不兼容

<details>
<summary>显示答案</summary>

**答案：B) 它可能绕过组织的解析器策略，并且无法解析私有名称**

**说明：**
DoH 使用 HTTPS 保护客户端到解析器这一跳，包括其完整性。独立的公共解析器可能绕过组织解析器上的控制，但受管理的 DoH 本身也可以提供策略和日志记录。应使用端点策略选择获准的解析器，并测试分离式 DNS。加密不会让解析器端点或所有流量元数据都不可见。

</details>

4. 为什么 L4 负载均衡器可能会使 gRPC 流量集中到少数几个后端？
   - A) 因为 Protocol Buffers 序列化是不对称的
   - B) 许多 RPC 可以共用长连接，而 L4 负载均衡器按连接选择后端
   - C) 因为 HTTP/2 标头压缩会在负载均衡器处失效
   - D) 因为 gRPC 基于 UDP，所以 L4 负载均衡无法实现

<details>
<summary>显示答案</summary>

**答案：B) 许多 RPC 可以共用长连接，而 L4 负载均衡器按连接选择后端**

**说明：**
gRPC 通道可以使用零个或多个 HTTP/2 连接。少量长连接可以承载许多 RPC，而 L4 负载均衡器不会对每个 RPC 重新分配后端。合适的客户端策略或能够识别 gRPC 的 L7 代理可以改善请求分布；已建立的流仍会留在其后端。

</details>

5. 以下哪项关于运行 WebSocket 服务的问题与应对方式的配对是错误的？
   - A) 负载均衡器空闲超时导致断开 → 使用 ping/pong 帧保持连接
   - B) 部署期间出现重连风暴 → 使用带抖动的指数退避
   - C) 在不同实例间传递应用事件 → 使用 Redis Pub/Sub 等消息传递方式，同时让每个 socket 仍由本地实例持有
   - D) 代理阻止 Upgrade 标头 → 提高到 QoS 2

<details>
<summary>显示答案</summary>

**答案：D) 代理阻止 Upgrade 标头 → 提高到 QoS 2**

**说明：**
QoS 等级属于 MQTT，无法修复 WebSocket 握手。HTTP/1.1 使用 Upgrade；HTTP/2 和 HTTP/3 在受支持时使用 Extended CONNECT。心跳必须符合空闲超时行为；退避和连接排空可以减少重连峰值。Pub/Sub 可以分发应用事件，但不会迁移 socket，也不会单独提供持久消息传递。

</details>

6. SPF、DKIM 和 DMARC 这三种电子邮件域身份验证机制与其作用的哪种对应关系正确？
   - A) SPF：邮件签名 / DKIM：发布获准的发送方 IP / DMARC：强制加密
   - B) SPF：授权 envelope/HELO 身份使用的主机 / DKIM：使用域密钥对受保护内容签名 / DMARC：将可见的 From 域与通过验证的 SPF 或 DKIM 对齐并发布策略
   - C) SPF：接收服务器身份验证 / DKIM：传输加密 / DMARC：垃圾邮件过滤
   - D) SPF：邮件队列管理 / DKIM：MX 记录验证 / DMARC：强制使用 TLS

<details>
<summary>显示答案</summary>

**答案：B) SPF：授权 envelope/HELO 身份使用的主机 / DKIM：使用域密钥对受保护内容签名 / DMARC：将可见的 From 域与通过验证的 SPF 或 DKIM 对齐并发布策略**

**说明：**
SPF 检查 envelope/HELO 域，DKIM 则验证其签名域对应的受保护内容。DMARC 要求至少一种通过验证的机制与可见的 From 域对齐；它不要求两种机制都通过。这些机制有助于保护域，但不保证邮件送达，也无法阻止通过显示名称或相似域名进行的冒充。

</details>

7. 一条 HTTP/1.1 请求以 `POST /echo HTTP/1.1` 开头，响应以 `HTTP/1.1 200 OK` 开头。哪种解释正确？
   - A) `POST` 是标头字段，`/echo` 是响应状态
   - B) `200` 是消息体长度，`OK` 决定请求是否成功
   - C) 请求行包含方法、目标和版本；状态行包含版本、状态码以及可选的原因短语
   - D) 第一个空行会终止整个消息，包括消息体

<details>
<summary>显示答案</summary>

**答案：C) 请求行包含方法、目标和版本；状态行包含版本、状态码以及可选的原因短语**

**说明：**
POST 会要求目标处理所提供的内容；200 是成功状态。起始行后面是标头字段行，随后空行结束标头部分。只有在消息规则允许的情况下才会有消息体。即使示例展示时使用 LF，HTTP/1.1 线上格式的行尾仍使用 CRLF。

</details>

8. HTTP/1.1 消息体只有 5 个 ASCII 字节 `hello`，没有尾随换行符，也没有内容编码或传输编码。`Content-Length: 5` 计数的是什么？
   - A) 整条消息，包括起始行和标头
   - B) 仅消息体的 5 个字节；`Content-Type` 会单独描述其媒体类型
   - C) 5 个 Unicode 字符，不受字节编码影响
   - D) 承载消息体的 TCP 数据包数量

<details>
<summary>显示答案</summary>

**答案：B) 仅消息体的 5 个字节；`Content-Type` 会单独描述其媒体类型**

**说明：**
Content-Length 统计字节数，不包括起始行、标头和空行分隔符。ASCII 字符串 `hello` 占 5 个字节；如果实际多了一个 LF，则会变为 6 个字节。非 ASCII UTF-8 字符可能占用多个字节。Content-Type 告诉接收方如何解读表示内容，而不是消息在哪里结束。

</details>

9. 有效的 HTTP/1.1 `200` GET 响应使用 `Transfer-Encoding: chunked`，并保持 TCP 连接打开。消息体如何划定边界？
   - A) 根据 TCP 数据包边界
   - B) 仅由 Content-Type 决定
   - C) 由必须与 Transfer-Encoding 一同发送的 Content-Length 决定
   - D) 由分块帧格式决定，并以零长度块、任何尾随标头和最后的空行结束

<details>
<summary>显示答案</summary>

**答案：D) 由分块帧格式决定，并以零长度块、任何尾随标头和最后的空行结束**

**说明：**
分块帧格式可以标识消息体的结束，而不必关闭连接。发送方不得同时发送 Content-Length 和 Transfer-Encoding。TCP 是字节流：一条消息可能跨多个数据包，一个数据包也可能承载多条消息中的字节。

</details>

10. 对 HEAD 请求的有效 HTTP/1.1 响应包含 `Content-Length: 500`。收到标头部分后，客户端应读取 500 个消息体字节吗？
   - A) 不应；HEAD 响应没有消息体，该字段描述对应 GET 响应的长度
   - B) 应；Content-Length 始终优先于方法
   - C) 应，但仅当 Content-Type 是 text/plain 时
   - D) 不应；任何 HEAD 响应都禁止使用 Content-Length

<details>
<summary>显示答案</summary>

**答案：A) 不应；HEAD 响应没有消息体，该字段描述对应 GET 响应的长度**

**说明：**
方法和状态规则优先于通用长度分帧规则。HEAD 响应没有消息体；允许的长度字段只是元数据。状态码为 1xx、204 或 304 的响应也没有消息体，但对允许使用的字段有各自的限制。

</details>

11. 客户端工具显示了某个通过 HTTPS 请求协商出的 HTTP/2 响应的可读标头。在没有会话密钥的被动抓包中，应看到什么？
   - A) 相同的明文 `GET ... HTTP/1.1` 请求行
   - B) 可见的明文标头，只有消息体经过加密
   - C) 受保护的应用数据；HTTP/2 使用二进制帧，而工具显示的是解码后的字段
   - D) 用于分隔每条 HTTP/2 流的 HTTP/1.1 分块大小

<details>
<summary>显示答案</summary>

**答案：C) 受保护的应用数据；HTTP/2 使用二进制帧，而工具显示的是解码后的字段**

**说明：**
在 HTTPS 连接中，TLS 会保护 HTTP/2 标头和内容。HTTP/2 在 TCP 上使用 HEADERS/DATA 帧；HTTP/3 在受保护的 QUIC 流上使用自己的帧格式。两者都保留 HTTP 语义，但都不使用 HTTP/1.1 文本起始行或分块传输编码。应在获准的端点或 TLS 终止点观察已解码的消息。

</details>

---

[返回学习材料](../../basics/06-network-fundamentals-part3.md) | [下一个测验：第 4 部分](./06-network-fundamentals-part4-quiz.md)

请复习[HTTP 消息结构、分帧和可见性](../../basics/06-network-fundamentals-part3.md#http11-message-structure)，包括其中引用的主要参考资料。
