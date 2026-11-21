# 08. CDN 与边缘交付设计

> **上次更新**：2026年11月19日
> **实验边界**：只读观察。本练习会向一个由公共 CloudFront 提供服务的资产发送少量 `curl` 请求；本工作簿不会创建分配、源站、VPC 或负载均衡器。
> **验证状态**：已查阅 Amazon CloudFront 开发人员指南、AWS Knowledge Center 页面以及 RFC 9111/5861。撰写本文时，观察了一个由公共 CloudFront 提供服务的资产的响应标头，**只观察到 Hit 响应**（未捕获到 Miss）；没有对任何分配进行**配置或测量**。

完成本工作簿后，你应能预测**请求在哪一层得到响应**（边缘 POP、区域边缘缓存、Origin Shield 或源站），根据响应标头解释为何请求在该层得到响应，并绘制从边缘到源站的路径，使源站只能通过 CloudFront 访问。

本章假定你已掌握基础知识。[网络基础知识第 3 部分](../../basics/06-network-fundamentals-part3.md)介绍 DNS 缓存和 TTL 行为，包括[HTTP/1.1 消息的结构](../../basics/06-network-fundamentals-part3.md#http11-message-structure)；[第 2 部分](../../basics/06-network-fundamentals-part2.md)介绍 TLS 握手、SNI 和终止点；[第 4 部分](../../basics/06-network-fundamentals-part4.md)梳理了 CloudFront、ALB 和 ACM 的作用。第 3 部分介绍 DNS 缓存，但不涉及 HTTP 缓存，因此第 6 节会定义本章需要的 HTTP 缓存术语。基于 [工作簿 02](02-routing-policy-convergence.md) 中的内容，本章进一步介绍使用 BGP 的 Anycast 路由；基于[工作簿 07](07-wan-hybrid-connectivity.md)中的内容，本章进一步介绍源站背后的私有连接。

**准备情况**：需要一个装有 `curl` 且可连接互联网的 Shell。无需 AWS 账户。自行构建参考设计会产生 CloudFront 请求和数据传输费用、超出免费额度的失效路径费用、Origin Shield 请求费用、负载均衡器使用时长费用和实例使用时长费用；**这些费用以及清理工作均由学习者自行承担**。不要在现有且已获批准的实验账户之外创建资源。

## 1. 带着问题阅读

考试范围只用于决定阅读内容。具体数值和行为来自第一列列出的官方文档。

| 阅读材料 | 对应的考试范围 | 用自己的话回答这个问题 |
|---|---|---|
| [CloudFront 如何交付内容](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/HowCloudFrontWorks.html)、[Origin Shield](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/origin-shield.html) | ANS-C01 领域 1 网络设计，任务 1.1（边缘网络服务） | 哪些请求会跳过区域边缘缓存，哪些请求会跳过 Origin Shield？ |
| [了解缓存键](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-the-cache-key.html)、[使用策略控制源站请求](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/controlling-origin-requests.html) | ANS-C01 领域 1 和 2（网络实施） | 源站需要接收哪些内容，但这些内容**不应**放入缓存键？ |
| [管理内容在缓存中的保留时间](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Expiration.html)、[RFC 9111](https://www.rfc-editor.org/rfc/rfc9111.html)、[RFC 5861](https://www.rfc-editor.org/rfc/rfc5861.html) | ANS-C01 领域 2；协议原理 | 源站的 `s-maxage` 与缓存策略的最大 TTL 不一致时，以哪个为准？ |
| [使用 VPC 源站限制访问](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html)、[限制对 Amazon S3 源站的访问](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html) | ANS-C01 领域 4 网络安全、合规与治理 | 如何才能确保源站只能通过 CloudFront 访问？ |
| [查看 CloudFront 指标](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/viewing-cloudfront-metrics.html)、[标准日志字段](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/standard-logs-reference.html) | ANS-C01 领域 3 网络管理与运维 | 哪个字段能区分 POP 命中和 Origin Shield 命中？ |

阅读后，绘制 viewer、POP、区域边缘缓存、Origin Shield（如使用）和源站，并用**不同线型**表示**缓存层级**和**连接链路**。每条链路都有自己的 TCP 或 QUIC 连接和自己的 TLS 会话，因此“端到端 HTTPS”是对每条链路的描述，而不是只描述一条链路。

## 2. 为什么使用 CDN

CDN 会改变三件事，设计方案应说明你希望获得其中哪种收益。

| 目标 | 机制 | 设计中要说明的限制 |
|---|---|---|
| **降低延迟（RTT）** | viewer 的 TCP/QUIC 和 TLS 握手在附近的 POP 结束，而不是在远处的源站结束；缓存命中时，完全不需要往返源站 | 缓存未命中时，仍需经过 POP 到源站的链路。第 2 部分指出，完整的 TLS 1.3 握手约需 1 RTT；现在这次 RTT 是较短的 viewer 到 POP 的往返 |
| **减轻源站负载** | 缓存命中时请求不会到达源站；区域边缘缓存、Origin Shield 和请求合并会减少未命中请求 | 命中率取决于你选择的缓存键和 TTL（第 5 节和第 6 节），而非仅由 CDN 决定 |
| **吸收流量** | 流量会到达大型分布式边缘，而不是单个源站 | 只有当源站无法绕过 CDN 直接访问时，吸收流量才会保护源站（第 9 节）。流量型和 L7 攻击防御将在下一本工作簿[边缘安全](./09-edge-security-waf-ddos.md)中介绍 |

CloudFront 会将每个请求路由到最适合为其提供服务的边缘站点，通常是延迟最低的站点，并通过 AWS 网络传输源站流量。

## 3. 请求引导：基于 DNS 和 Anycast

必须有某种机制来决定 viewer 与**哪个 POP**通信。常见方法有两种。

| 方法 | 如何选择 POP | 故障转移和粒度 | 应用场景 |
|---|---|---|---|
| **基于 DNS** | CDN 的权威 DNS 向 viewer 的解析器返回适当 POP 的地址 | 更改会在解析器重新查询时生效，但受缓存答案影响（第 3 部分：现在降低 TTL 不会缩短已缓存的答案）。除非解析器传递客户端子网信息（[RFC 7871](https://www.rfc-editor.org/rfc/rfc7871.html)），否则权威服务器看到的是**解析器**的地址，而非 viewer 的地址 | CloudFront 默认行为：“DNS 会将请求路由到最适合为请求提供服务的 CloudFront POP（边缘站点）” |
| **Anycast** | 多个站点通过 BGP 通告**同一**前缀；常规路由会将每个数据包交付给拓扑距离最近的通告站点（[RFC 4786](https://www.rfc-editor.org/rfc/rfc4786.html)） | 故障转移遵循 BGP 撤销和收敛过程（工作簿 02）。RFC 4786 警告，节点选择必须在长于一次事务的时间内保持稳定，因为路由变化可能会将会话的其余部分发送到另一个节点 | CloudFront **Anycast 静态 IP**：可选择启用的专用静态 IPv4（或 IPv4 和 IPv6）地址列表，可用于加入允许列表，也可用于为带有 A 记录的顶点域名指定地址；支持 SNI |

**实际情况**：使用 DNS 引导时，位于较远解析器之后的 viewer 可能会被引导到离自己较远的 POP。使用 Anycast 时，“最近”指 BGP 跳数最少或优先级最高，而非延迟最低。这两种方法都不能保证连续两个请求抵达同一个 POP 或同一台服务器，这对第 11 节的练习很重要。

## 4. 缓存层级：POP、区域边缘缓存、Origin Shield、源站

**GET 请求的处理方式：**

1. DNS 将 viewer 路由到一个 POP。如果该对象已缓存在此处且仍有效，POP 就会返回该对象。
2. POP 缓存未命中时，通常会向最近的**区域边缘缓存**请求对象。区域边缘缓存的容量大于单个 POP，因此，在 POP 上不再热门的对象仍可在此处缓存更长时间。
3. 区域边缘缓存未命中时，CloudFront 会将请求转发到源站（如果启用了 Origin Shield，则经由 Origin Shield）。响应会经过区域边缘缓存返回 POP，并由**两者**分别存储副本。CloudFront 一收到第一个字节就会开始转发。

![CDN 缓存 MISS 后 HIT 的动画。① 客户端 A 解析分配的域名；DNS 返回延迟最低的边缘 POP，A 发送 GET /img/logo.png。② 边缘 POP 没有对应此缓存键的对象，因此发生 MISS；它向区域边缘缓存请求，但区域边缘缓存也未命中。③ 源站——一个通过 CloudFront VPC 源站访问的内部 ALB——返回 200，且带有 Cache-Control: max-age=3600。④ 响应返回时，区域边缘缓存和 POP 各自存储一份副本，客户端 A 收到 x-cache: Miss from cloudfront。⑤ 客户端 B 向同一个 POP 请求同一对象：请求命中，POP 从缓存中返回对象，带有 Age: 42 和 x-cache: Hit from cloudfront，且不会有请求到达源站。](../../.gitbook/assets/en-networking-expert-08-cdn-edge-delivery-anim-0.svg)

**会跳过区域边缘缓存的请求**（开发人员指南）：

- 代理 HTTP 方法 `PUT`、`POST`、`PATCH`、`OPTIONS` 和 `DELETE` 会从 POP 直接发送到源站。
- 在请求处理时被判定为动态的请求会直接发送到源站。
- 如果源站是 S3 存储桶，且请求对应的最优区域边缘缓存与存储桶位于同一区域，POP 会直接访问存储桶。

区域边缘缓存的功能与 POP 相同：失效操作会从两者中移除对象。

**Origin Shield** 是位于区域边缘缓存和源站之间的可选附加层。来自所有 CloudFront 缓存层、发往源站的请求都会经过此层，因此每个对象只需一个源站请求即可完成获取；在与源站相同的区域中发出的请求会绕过此层。选择与源站延迟最低的 Origin Shield 区域（仅在 CloudFront 设有区域边缘缓存的区域提供）。Origin Shield 是按请求收费的**增量**层：动态请求（`PUT`、`POST`、`PATCH`、`DELETE`，以及 TTL 小于 3600 秒或已禁用缓存的 `GET`/`HEAD`）始终计费；可缓存请求仅在其从位于不同区域的区域边缘缓存到达时计费。AWS 列出的不适用场景包括动态代理内容、可缓存性低的内容和请求频率低的内容。

**请求合并**：如果首个未命中请求仍在等待源站响应时，同一缓存键有更多请求到达，CloudFront 会暂停这些请求，并用首个请求的响应回答所有请求。只有缓存键相同的请求才会合并。在日志中，首个请求显示为 `Miss`，合并的请求显示为 `Hit`。

## 5. 缓存键设计与命中率

**缓存键**是缓存中对象的唯一标识符。当请求生成的缓存键与之前某个请求相同，且对应对象仍在缓存中且有效时，就会命中。RFC 9111 将请求方法和目标 URI 定义为最小缓存键，`Vary` 可添加请求标头。

**CloudFront 默认行为**：分配的域名和 URL 路径。默认情况下，查询字符串、标头和 Cookie **不会**放入缓存键。开发人员指南展示了两个针对 `/content/stories/example-story.html` 的请求，它们的查询字符串、`User-Agent`、`Referer` 和 `session_id` Cookie 各不相同，但第二个请求仍然命中。`OPTIONS` 的响应与 `GET` 和 `HEAD` 的响应分别缓存。

**两种策略，各有用途：**

| 策略 | 控制内容 | 规则 |
|---|---|---|
| **缓存策略** | 哪些内容纳入缓存键，以及最小/默认/最大 TTL | 只有在某个值会改变响应时才将其纳入 |
| **源站请求策略** | 缓存未命中时源站会收到哪些内容，**但不**将这些内容加入缓存键 | 缓存键中的所有内容都会自动转发；对于源站需要、但缓存不应因此拆分的值（分析、遥测），使用此策略 |

源站请求始终包含 URL 路径、任何请求正文，以及 CloudFront 自动添加的标头，例如 `Host`、`User-Agent` 和 `X-Amz-Cf-Id`。

**哪些内容会拆分缓存键，以及替代做法：**

| 候选值 | 问题 | 替代做法 |
|---|---|---|
| `Accept-Language` | `en-US,en`、`en,en-US`、`en-US, en` 和 `en-US` 都表示英语，但会生成不同的对象 | 将语言放入 URL（`/en-US/...`） |
| `User-Agent` | 变体数以千计 | 不将其纳入缓存键 |
| 会话 Cookie | 每个用户都不同，因此每个用户都会获得自己的私有副本 | 不将其纳入缓存键，或将响应标记为不可缓存 |
| 源站会忽略的查询字符串 | 生成重复对象 | 排除这些查询字符串，或仅纳入指定参数 |

**命中率**是 viewer 请求中命中请求所占的比例。只在缓存键中纳入必要的最少值、在新鲜度允许时设置较长的 TTL，以及在 viewer 分布于多个区域时使用 Origin Shield，都有助于提高命中率。

## 6. TTL、Cache-Control 和失效

**本文使用的 HTTP 缓存术语**（RFC 9111）：已存储响应在其新鲜度生命周期结束前为**新鲜**，之后则为**陈旧**。共享缓存（如 CDN）会按 `s-maxage`、`max-age`、`Expires` 减去 `Date` 的顺序，使用第一个可用值计算新鲜度生命周期。使用陈旧响应通常需要与源站进行**验证**（条件请求可能会返回 `304 Not Modified`）。`Age` 标头表示发送方估算的响应自源站生成或验证以来经过的秒数；如果存在此标头，则意味着该响应不是源站为本次请求生成的。只要新鲜度生命周期大于当前 Age，响应就仍然新鲜，因此剩余时间等于生命周期减去 `Age`。`no-cache` 表示存储的响应未经成功验证不得重复使用；`no-store` 表示不得存储该响应。

**CloudFront 如何将源站标头与缓存策略 TTL 组合起来：**

| 源站发送的内容 | 最小 TTL = 0 | 最小 TTL > 0 |
|---|---|---|
| `Cache-Control: max-age` | CloudFront 缓存时间取 `max-age` 和最大 TTL 中较小者 | 限制在范围内：低于最小 TTL 时使用最小值；高于最大 TTL 时使用最大值 |
| `max-age` **和** `s-maxage` | CloudFront 使用 `s-maxage`（不超过最大 TTL）；浏览器使用 `max-age` | `s-maxage` 限制在最小和最大 TTL 之间 |
| 无 `max-age` | 使用默认 TTL | 使用最小 TTL 和默认 TTL 中较大的值 |
| `Expires` | 缓存到指定日期或最大 TTL，以先到者为准 | 限制在最小和最大 TTL 之间 |
| `no-cache`、`no-store` 和/或 `private` | CloudFront 和浏览器遵循这些标头 | CloudFront 仍会按**最小 TTL**缓存 |

其他规则：

- 如果同时存在 `max-age` 和 `Expires`，CloudFront 只使用 `max-age`。
- viewer 在 GET 请求中发送的 `Cache-Control` 或 `Pragma` 无法强制 CloudFront 回源；CloudFront 会忽略这些标头。
- 如果未使用缓存策略（旧版设置），默认 TTL 为 24 小时。
- **陷阱**：当最小 TTL 大于 0 时，即使源站发送了 `no-cache`，响应仍会按最小 TTL 缓存。如果源站之后无法访问，且最小 **或** 最大 TTL 大于 0，CloudFront 会提供先前获取的对象，因此仅降低最小 TTL 并不能阻止这种情况。将 `Cache-Control: stale-if-error=0` 添加到源站响应中，可让 CloudFront 改为返回错误。

**有意提供陈旧内容**：CloudFront 支持 [RFC 5861](https://www.rfc-editor.org/rfc/rfc5861.html) 扩展。

- `max-age=3600, stale-while-revalidate=600`：一小时后，CloudFront 最多再提供 10 分钟的陈旧副本，同时在后台获取新副本。
- `max-age=3600, stale-if-error=86400`：一小时后，如果源站无法访问或返回 5xx 错误，CloudFront 会继续提供陈旧副本，最长 24 小时。
- 无论哪种情况，提供陈旧内容的时间都不会超过指令值和**最大 TTL**中的较小者。

**失效与版本化文件名：**

| | 失效 | 版本化名称（`app.3f9c.js`） |
|---|---|---|
| 效果 | 从 POP 和区域边缘缓存中移除对象；下一个请求会访问源站 | 新 URL 会生成新的缓存键；新旧对象可以共存 |
| 浏览器和企业代理缓存 | 不受影响：用户可能会继续使用旧副本，直到其在这些缓存中到期 | 页面会引用新名称，因此每个缓存都会获取它 |
| 费用 | 每个账户每月前 1,000 条失效路径免费，之后按路径收费；无论 `*` 通配符路径移除多少文件，均只计为一条路径 | 不收取失效费用；但仍需支付向边缘传输新版本的费用 |
| 速率配额 | 每秒 150 条路径或标签，每秒 1 条通配符失效（参见开发人员指南的配额页面） | 无 |
| 回滚 | 再次执行失效 | 将页面指回旧名称 |

AWS 建议对经常更新的文件使用版本化文件名。CloudFront 常见问题解答和一篇 Knowledge Center 文章仍描述较旧的“同时进行中的失效”限制（每个分配最多 3,000 个单独文件和 15 条通配符路径）；目前应以开发人员指南的配额页面为准，因此请在设计当天进行核查。

## 7. 边缘侧以及到源站的 TLS

viewer 链路和源站链路是两个独立的 TLS 会话（第 2 部分：TLS 终止不会加密下一跳）。

**viewer 到 CloudFront：**

- viewer 协议策略可以允许 HTTP 和 HTTPS、将 HTTP 重定向到 HTTPS，或仅要求使用 HTTPS。
- CloudFront 分配的 ACM 证书必须在**美国东部**（弗吉尼亚北部）申请或导入；CloudFront 会将其分发到各个站点。
- HTTP/2 要求 viewer 支持 TLS 1.2 或更高版本以及 SNI；HTTP/3 要求 TLS 1.3 和 SNI。

**CloudFront 到源站：**

- 源站协议策略可以是仅 HTTP、仅 HTTPS 或与 viewer 匹配（仅当 viewer 策略为重定向到 HTTPS 或仅 HTTPS 时，才选择与 viewer 匹配）。
- 源站证书必须与分配中配置的源站域名相匹配；如果转发 `Host` 标头，则必须与其中的主机名相匹配。CloudFront 也会将此名称作为 SNI 发送。如果证书不匹配、不受信任的 CA 签发、证书链损坏或已过期，CloudFront 就会断开连接并向 viewer 返回 `502`。
- 如果源站是 ALB，ALB 上的证书位于**ALB 所在的区域**，与 viewer 证书所在的 us-east-1 区域不同。
- 使用 **VPC 源站**时，CloudFront 会通过 ARN 而非公共 DNS 查询访问内部 ALB；你配置的主机名仅用于 SNI 和证书匹配，因此无需设置公共 DNS 记录指向内部 ALB（AWS Networking 博客，2026）。

**实际情况**：针对每条链路，记录所用协议、证书及其所在区域、最低 TLS 版本，以及证书续订的负责人。在设计评审中，“HTTPS”意味着两行都填写完整。

## 8. 动态加速、HTTP/2 和 HTTP/3

并非所有内容都可缓存，CDN 仍然能帮助传输不可缓存的流量：

- **缩短 viewer 握手时间**：TCP/QUIC 和 TLS 握手在附近的 POP 进行。
- **持久的源站连接**：响应发送后，CloudFront 会继续保持源站连接数秒（自定义源站和 VPC 源站的可配置保持活动超时），使下一个请求无需重新执行 TCP 和 TLS 握手。
- **AWS 网络**：边缘与 AWS 区域内源站之间的流量会留在 AWS 网络中。
- **动态请求会跳过区域边缘缓存**（第 4 节），因此不会因为额外的缓存查询而变慢。

**各链路上的协议版本：**

| 链路 | 版本 | 备注 |
|---|---|---|
| Viewer ↔ CloudFront | 默认启用 HTTP/1.0 和 1.1；可启用 HTTP/2 和 HTTP/3 | HTTP/3 通过 UDP 使用 QUIC；CloudFront 支持连接迁移，因此 viewer 可以切换网络而不中断连接 |
| CloudFront → 自定义源站 | HTTP/1.1 | viewer 侧的 HTTP/2 多路复用不会延伸到源站；请据此规划源站连接容量 |

HTTP/2 和 HTTP/3 保留 HTTP 语义，只改变帧格式（第 3 部分），因此所有版本的缓存键和 TTL 行为都相同。

## 9. CloudFront 映射与边缘到源站的路径

| 概念 | CloudFront 功能 | 设计说明 |
|---|---|---|
| 缓存键和 TTL | 缓存策略 | 缓存键中仅包含最少必要值；按行为设置 TTL |
| 转发但不拆分缓存 | 源站请求策略 | 源站需要、但缓存不应据此区分的值 |
| 按路径设置行为 | 缓存行为（路径模式） | 例如 `/assets/*` 使用较长 TTL 和版本化名称，`/api/*` 禁用缓存 |
| 私有 S3 源站 | 源站访问控制（OAC） | AWS 建议使用 OAC，而非旧版 OAI |
| 私有 ALB、NLB 或 EC2 源站 | VPC 源站 | 下方展示的本文参考设计 |

**适用于 S3 的 OAC**：CloudFront 会为源站请求签名，存储桶策略只允许该分配访问。AWS 建议使用 OAC 而非 OAI，因为它支持所有区域中的 S3 存储桶（包括 2022 年 12 月之后推出的选择加入区域）、SSE-KMS 和动态请求（`PUT`、`DELETE`）。使用 OAC 时，S3 对象所有权必须设为 **Bucket owner enforced**（新存储桶的默认设置）。S3 **网站端点**属于自定义源站，不能使用 OAC。

<a id="edge-origin-path"></a>

### 边缘到源站的路径：VPC 源站到内部 ALB

**参考设计**：CloudFront → **VPC 源站** → 私有子网中的**内部** ALB → 目标组。源站没有公共地址，且只有 CloudFront 能向其发送入站流量。不要在 CloudFront 后面放置面向互联网的负载均衡器，也不要添加允许公共 CIDR 访问源站的入站规则。

![边缘到源站路径动画。① viewer 通过 HTTPS 发送可缓存的 GET /menu.json；TLS 在边缘 POP 终止，且 POP 和区域边缘缓存都未命中。② CloudFront 通过 VPC 源站连接到源站：服务管理的 ENI 位于私有子网（例如 10.0.11.25），并向内部 ALB（10.0.12.40）发起连接。③ ALB 安全组仅允许来自 CloudFront-VPCOrigins-Service-SG（或 CloudFront 源站访问托管前缀列表）的流量。④ ALB 侦听器将请求转发到目标组，目标组中的目标仅接受来自 ALB 安全组的流量。⑤ 互联网客户端尝试直接访问 ALB，但失败：内部 ALB 只有私有地址，因此互联网上没有任何路由可以到达它，请求无法进入 VPC。VPC 连接了互联网网关，但此路径不会使用它。](../../.gitbook/assets/en-networking-expert-08-cdn-edge-delivery-anim-1.svg)

**VPC 源站要求**（开发人员指南）：

- **源站类型**：已完全部署且处于 Active 状态的私有子网中的 ALB、NLB 或 EC2 实例。Gateway Load Balancer 和带 TLS 侦听器的 NLB 不能用作源站；NLB 必须附加安全组。
- **VPC**：VPC 必须**连接互联网网关**；这表示 VPC 可以接收来自互联网的流量，但互联网网关**不会用于路由**到源站，也无需更改路由表。
- **子网**：CloudFront 会在私有子网中创建服务管理的 ENI；该子网至少需要一个可用的 IPv4 地址（双栈还需要一个 IPv6 地址）。
- **安全组**：源站必须关联安全组。入站流量可允许来自**CloudFront 托管前缀列表**（`com.amazonaws.global.cloudfront.origin-facing`，双栈还需 IPv6 列表）的流量，该列表可以预先添加；也可以允许来自服务管理的 **`CloudFront-VPCOrigins-Service-SG`** 的流量，该安全组在创建 VPC 源站后可用，限制更严格，因为它只允许你的分配访问。不要编辑此安全组，也不要使用此前缀创建自己的安全组。
- **不支持**：gRPC、Lambda@Edge 源站请求和源站响应触发器。针对 CloudFront 到源站流量，不会评估入站 NACL 规则；但返回路径会评估**出站** NACL 规则，必须允许流向 CloudFront 源站访问范围的临时 TCP 端口 1024–65535。
- **配额**：每个账户有 25 个 VPC 源站（可调整），每个 VPC 源站可用于 50 个分配。

**为什么无法绕过 CloudFront 访问内部 ALB**：内部负载均衡器的节点只有私有 IP 地址。其 DNS 名称可以通过公共 DNS 解析，但解析结果是这些私有地址，因此只有能够访问 VPC 的客户端才能连接。这是路由属性，而非过滤规则；即使之后放宽安全组规则，这一属性依然成立。如果 ALB 来自 Kubernetes Ingress，[AWS Load Balancer Controller](../03-aws-lb-controller.md) 会通过 `alb.ingress.kubernetes.io/scheme: internal` 将其设为内部 ALB。

**前缀列表还是服务安全组**：托管前缀列表包含所有 CloudFront 源站访问服务器，因此允许**任何**分配访问；VPC 源站服务安全组只允许你自己的分配访问。作为入站规则，前缀列表按 55 条规则的权重计入安全组规则配额。[WAF、边缘与 API 安全](../../security/14-waf-edge-api-security.md)介绍 WAF 的部署位置，并将此设计与安全性较弱的公共 ALB 源站设计（前缀列表加密钥标头）进行比较；本文参考设计不使用后者。下一本工作簿[边缘安全](./09-edge-security-waf-ddos.md)将在此路径基础上介绍攻击侧视角。

## 10. 可观测性：每种信号能证明什么

| 信号 | 位置 | 说明 |
|---|---|---|
| `x-cache` 响应标头 | Viewer 响应 | `Hit from cloudfront`、`RefreshHit from cloudfront`（过期副本已通过源站重新验证）或 `Miss from cloudfront` |
| `Age` | Viewer 响应 | 副本自源站生成或验证以来经过的秒数；命中时，`Date` 加上 `Age` 大致等于当前时间 |
| `x-amz-cf-pop` | Viewer 响应 | 提供响应的 POP；在对第二次 Miss 作出判断前，先比较各请求中的此值 |
| `Via` | Viewer 响应 | 处理此消息的中间节点（[RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)）；两次发往同一 POP 的请求可能会显示不同的服务器标识符 |
| `x-edge-result-type` | 标准日志 | `Hit`、`RefreshHit`、`Miss`、`LimitExceeded`、`CapacityExceeded`、`Error`、`Redirect`；WebSocket 和 gRPC 始终为 `Miss` |
| `x-edge-detailed-result-type` | 标准日志 | 除列出的情况外，与 `x-edge-result-type` 相同；由 Origin Shield 提供服务时为 `OriginShieldHit`（路由到充当 Origin Shield 的区域边缘缓存的请求会记录为 `Hit`） |
| `time-to-first-byte` | 标准日志 | 从收到请求到写入第一个字节的秒数，在服务器端测量 |
| 缓存命中率、源站延迟 | CloudWatch 附加指标（收费；每个分配最多 8 个，在 us-east-1 发布） | 命中率只统计可缓存请求（不包括 `POST`、`PUT` 和错误）；源站延迟表示由源站提供服务的请求的首字节延迟 |

**为什么第二个请求仍可能是 Miss**（AWS Knowledge Center）：每个边缘站点只缓存自己收到的内容，因此请求若抵达另一个 POP，就会未命中；请求频率低的对象可能会在过期前被逐出；缓存键中的标头、Cookie 或查询字符串会拆分请求；源站的 `Cache-Control` 或 `Expires` 也可能缩短缓存时长。

## 11. 练习：从响应标头中识别未命中和命中

本练习只观察，不做修改。将结果标记为**对第三方分配的观察**：你看不到它的缓存策略，因此所有结论都只能根据标头推断。

**选择目标**：任选一个响应带有 `x-cache: ... from cloudfront` 和 `x-amz-cf-pop` 的公共静态资产（图像、CSS 或 JavaScript 文件）。不要假定任何特定网站的行为，先检查标头。如果你有自己获准使用的分配，请使用它，这样便能与其已知策略进行对比。

```bash
URL='https://<cloudfront-served-host>/<path-to-static-asset>'
curl -sI "$URL" | grep -iE '^(HTTP|date|age|cache-control|x-cache|via|x-amz-cf-pop)'
sleep 5
curl -sI "$URL" | grep -iE '^(HTTP|date|age|cache-control|x-cache|via|x-amz-cf-pop)'
```

`curl -I` 会发送 `HEAD`。开发人员指南指出，只有 `OPTIONS` 响应会与 `GET` 和 `HEAD` 分开缓存，因此这些标头描述的是 `GET` 会使用的同一个缓存对象。如要使用真正的 `GET` 重试并丢弃正文，可运行 `curl -s -o /dev/null -D - "$URL"`。

**示例输出**（仅展示格式，并非从某个特定网站捕获；实际值会有所不同）：

```text
HTTP/2 200
date: Thu, 19 Nov 2026 09:00:00 GMT
cache-control: max-age=86400
x-cache: Miss from cloudfront
via: 1.1 <edge-server-id-1>.cloudfront.net (CloudFront)
x-amz-cf-pop: <POP-code>

HTTP/2 200
date: Thu, 19 Nov 2026 09:00:00 GMT
cache-control: max-age=86400
x-cache: Hit from cloudfront
via: 1.1 <edge-server-id-2>.cloudfront.net (CloudFront)
x-amz-cf-pop: <POP-code>
age: 5
```

**解读规则：**

| 观察结果 | 结论 | 后续检查 |
|---|---|---|
| 先 Miss 后 Hit，且 `x-amz-cf-pop` 相同 | 第一个请求填充了此 POP 的缓存（或填充了它随后读取的区域缓存）；第二个请求无需访问源站即可得到响应 | `age` 大致等于请求间隔；`date` 保持不变 |
| 第一个请求就是 Hit | 其他 viewer 已经填充该缓存 | `date` + `age` ≈ 当前时间；`age` 接近 `max-age` 表示即将过期 |
| 先 Miss 后 Miss | 请求到达不同 POP、对象被逐出、缓存键包含不同值，或响应不可缓存 | 比较 `x-amz-cf-pop`；检查 `cache-control` 中是否有 `no-store`、`private` 或 `max-age=0` |
| `RefreshHit` | 副本已过期，并通过源站重新验证 | 预期 `age` 会重新从接近 0 开始 |
| `via` 中的服务器标识符变化，但 POP 相同 | 同一 POP 中的另一台服务器提供了响应；仍然找到了缓存对象 | 无需修复 |

**任务：**

1. 发送两次请求，并分别记录每次的 `x-amz-cf-pop`、`x-cache`、`age`、`date` 和 `cache-control`。
2. 计算 `date` + `age`，并与本地时钟比较。解释两者的差异。
3. 根据 `cache-control`，说明共享缓存可以将副本视为新鲜内容多长时间，以及 CDN 会使用哪个值（`s-maxage` 或 `max-age`）。说明分配的最小和最大 TTL 可能造成哪些影响，并引用第 6 节的表格。
4. 如果第一个请求已经命中，解释原因。缓存破坏查询字符串无法可靠地强制产生 Miss：当缓存策略未将查询字符串纳入缓存键时（CloudFront 默认如此），`?x=1` 仍会命中同一个对象。如果要尝试，只能向他人的网站发送至多一个此类请求，并使用缓存键解释结果。
5. **设计部分（桌面检查**）：对于包含 `/assets/*`（版本化文件名）、`/index.html` 和 `/api/*` 的网站，编写缓存行为表：缓存键内容、TTL、源站请求策略、失效计划，以及 Origin Shield 是否值得其每请求费用。然后按照第 9 节绘制源站路径并列出其安全组规则。

**评审标准：**

- 每个结论都引用一个标头和第 4–6 节或第 10 节中的一条规则。
- 比较 POP 代码之前，不得将第二个 Miss 报告为“缓存失效”。
- 设计部分不得使用面向互联网的负载均衡器，也不得在任何入站规则中使用公共 CIDR；`/api/*` 必须完全不缓存，或使用包含所有会改变响应的值的缓存键。

## 12. 观察故障与恢复

使用此表判断**需要哪些证据才能确定每个结论**。如果之后在获批准的现有环境中复现某种情形，请收集相应证据。

| 故障 | 预期行为 | 证据 | 仅凭这些证据无法确定的内容 |
|---|---|---|---|
| 源站宕机，但对象仍新鲜 | 命中继续成功；未命中失败 | `x-cache: Hit` 且 `age` 持续增加；日志中未命中请求的结果为 `Error` | 并非每个对象都已缓存 |
| 源站宕机，对象已陈旧，且设置了 `stale-if-error` | 提供陈旧副本，最长不超过指令值和最大 TTL 中的较小者 | `age` 超过 `max-age`；日志中有源站错误 | 故障持续了多久 |
| 源站宕机，最小或最大 TTL > 0，使用 `no-cache` 但未设置 `stale-if-error=0` | 可以提供先前获取的副本（第 6 节的陷阱） | 返回的响应与预期错误不同 | 这是否适用于该内容 |
| 缓存键增大（添加了标头或 Cookie） | 命中率降低，源站延迟和源站负载升高 | CloudWatch 缓存命中率、源站请求数 | 是哪个值拆分了缓存键（需比较策略） |
| 源站证书不匹配或已过期 | 未命中时向 viewer 返回 `502` | Viewer 收到 `502`；源站 TLS 错误 | 命中是否受到影响（不会） |
| 安全组更改移除了 CloudFront 源 | 未命中请求无法建立连接；命中继续成功 | 未命中时出现 `504`（源站防火墙或安全规则阻止 CloudFront 流量时会返回 504）；安全组规则历史记录 | 内部 ALB 是否因此能从互联网访问（不能：它没有公共地址） |
| 通过失效修复错误部署 | 边缘会重新获取内容；浏览器和代理可能仍保留旧副本 | 失效状态；先 `x-cache: Miss`，再 `Hit` | 用户的浏览器是否已更新（只有版本化名称才能做到这一点） |

**恢复过程会造成流量负载**。失效或源站中断后，许多 POP 会同时发生缓存未命中。区域边缘缓存、Origin Shield 和请求合并会减少源站请求数，但仍需为缓存重新填充规划源站容量。观察到的错误数为零，只表示抽样过程中没有捕获到任何错误。

## 13. 交付物与完成标准

| 交付物 | 完成标准 |
|---|---|
| 路径图 | 图中包含 viewer、POP、区域边缘缓存、Origin Shield（如使用）和源站；缓存层级与连接链路有所区分，并标明跳过区域边缘缓存的请求 |
| 标头观察记录 | 记录两次请求的 POP、`x-cache`、`age`、`date` 和 `cache-control`，并将每个结论与一条规则对应起来 |
| 缓存行为表 | 按路径列出缓存键、TTL、源站请求策略、失效或版本化方案，并说明 Origin Shield 决策的依据 |
| 源站路径和规则 | VPC 源站到内部 ALB 的路径、安全组规则来源（服务安全组或前缀列表）以及逐链路 TLS 表格 |
| 故障表 | 每一行都列出预期行为、证据及其局限 |

当你能够结合来源说明请求如何被引导到 POP、哪个层级为何响应、缓存键和 TTL 规则如何决定命中率、失效与版本化名称有何区别，以及为什么源站只能通过 CloudFront 访问时，就算完成本工作簿。接下来学习[边缘安全](./09-edge-security-waf-ddos.md)，了解同一路径上的攻击侧内容；查看[WAF、边缘与 API 安全](../../security/14-waf-edge-api-security.md)中的 WAF 部署位置；然后完成[测验](../../quizzes/networking/expert/08-cdn-edge-delivery-quiz.md)。

## 参考资料

Amazon CloudFront 开发人员指南

- [什么是 Amazon CloudFront？](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html)（最低延迟路由、AWS 网络）
- [CloudFront 如何交付内容](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/HowCloudFrontWorks.html)（通过 DNS 将请求路由到 POP、区域边缘缓存以及会跳过这些缓存的请求）
- [使用 Amazon CloudFront Origin Shield](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/origin-shield.html)（绕过、区域、计费依据、`OriginShieldHit`）
- [了解缓存键](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-the-cache-key.html)、[使用策略控制源站请求](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/controlling-origin-requests.html)
- [管理内容在缓存中的保留时间（过期）](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Expiration.html)（TTL 表、`stale-while-revalidate`、`stale-if-error`、最小 TTL 警告）
- [使文件失效以移除内容](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html)、[支付文件失效费用](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/PayingForInvalidation.html)
- [配额](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cloudfront-limits.html)（失效率、VPC 源站、源站访问控制）
- [自定义源站的请求和响应行为](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/RequestAndResponseBehaviorCustomOrigin.html)（到源站的 HTTP/1.1、持久连接、请求合并、`Via`、源站协议）
- [分配设置参考](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/DownloadDistValuesGeneral.html)（支持的 HTTP 版本、HTTP/2 和 HTTP/3 要求）
- [要求 CloudFront 与自定义源站之间使用 HTTPS](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-https-cloudfront-to-custom-origin.html)（源站协议策略、源站证书名称）
- [限制对 Amazon S3 源站的访问](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)（OAC）
- [使用 VPC 源站限制访问](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html)（要求、安全组、限制）
- [CloudFront 边缘服务器的位置和 IP 地址范围](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/LocationsOfEdgeServers.html)（托管前缀列表）
- [请求 Anycast 静态 IP](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/request-static-ips.html)
- [查看 CloudFront 和边缘函数指标](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/viewing-cloudfront-metrics.html)（缓存命中率、源站延迟）、[标准日志文件字段](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/standard-logs-reference.html)
- [限制对 Application Load Balancer 的访问](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/restrict-access-to-load-balancer.html)（ALB 证书区域与 us-east-1 viewer 证书的区别）
- [HTTP 504 状态代码（网关超时）](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/http-504-gateway-timeout.html)（源站防火墙阻止 CloudFront）

其他 AWS 资料

- [Elastic Load Balancing 的工作原理](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/how-elastic-load-balancing-works.html)（内部负载均衡器方案）
- [AWS 白皮书：源站 HTTPS 配置](https://docs.aws.amazon.com/whitepapers/latest/secure-content-delivery-amazon-cloudfront/origin-https-configuration.html)（源站证书条件、SNI、`502`）
- [AWS Knowledge Center：CloudFront 支持哪些协议？](https://repost.aws/knowledge-center/cloudfront-supported-protocols)（默认启用 HTTP/1.0 和 1.1；到自定义源站使用 HTTP/1.1）
- [AWS Knowledge Center：X-Cache: Miss from CloudFront](https://repost.aws/knowledge-center/cloudfront-x-cachemiss-error)、[自定义对象缓存和源站标头](https://repost.aws/knowledge-center/cloudfront-custom-object-caching)（`x-cache` 值、`x-amz-cf-pop`）
- [AWS Knowledge Center：在美国东部（弗吉尼亚北部）关联证书](https://repost.aws/knowledge-center/migrate-ssl-cert-us-east)
- [Amazon CloudFront 常见问题解答](https://aws.amazon.com/cloudfront/faqs/)（较旧的并发失效限制）、[Amazon CloudFront 定价](https://aws.amazon.com/cloudfront/pricing/)
- [AWS Networking 博客：通过 CloudFront VPC 源站连接私有 AI 代理](https://aws.amazon.com/blogs/networking-and-content-delivery/private-ai-agent-with-websocket-streaming-over-cloudfront-vpc-origins-and-the-next-generation-of-opensearch-serverless-for-knowledge-retrieval/)（通过 ARN 路由 VPC 源站、源站证书）
- [AWS Networking 博客：CloudFront 托管前缀列表](https://aws.amazon.com/blogs/networking-and-content-delivery/limit-access-to-your-origins-using-the-aws-managed-prefix-list-for-amazon-cloudfront/)（规则权重 55）

标准

- [RFC 9111：HTTP 缓存](https://www.rfc-editor.org/rfc/rfc9111.html)（缓存键、新鲜度、`Age`、`no-cache`、`s-maxage`）
- [RFC 5861：陈旧内容的 HTTP Cache-Control 扩展](https://www.rfc-editor.org/rfc/rfc5861.html)
- [RFC 9110：HTTP 语义](https://www.rfc-editor.org/rfc/rfc9110.html)（`Via`）
- [RFC 4786：Anycast 服务的运行](https://www.rfc-editor.org/rfc/rfc4786.html)、[RFC 7871：DNS 查询中的客户端子网](https://www.rfc-editor.org/rfc/rfc7871.html)
- [RFC 1918](https://www.rfc-editor.org/rfc/rfc1918.html)（示例地址）

考试范围（仅用于选择主题）

- [AWS Certified Advanced Networking - Specialty (ANS-C01) 考试指南](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01.html)
