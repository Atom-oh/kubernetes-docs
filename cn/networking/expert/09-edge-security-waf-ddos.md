# 09. 边缘安全：WAF 与 DDoS 防御

> **最后更新**：2026年11月19日
> **实验边界**：仅限桌面演练。你将在纸上编写一份计数模式规则计划；本工作簿不会创建 Web ACL、分配、Shield 订阅、负载均衡器或 Kubernetes 对象，也不会向任何系统发送攻击流量或负载流量。
> **验证状态**：已查阅 AWS WAF、AWS Shield 和 Amazon CloudFront 开发人员指南、AWS WAF API 参考、AWS 关于 DDoS 弹性的白皮书、RFC 4987 以及 OWASP Top 10 2021 页面。没有部署任何规则，也没有测量任何流量；练习中的数字是一个演算示例，并非观测结果。

完成本工作簿后，你应该能够说出攻击针对的层，指出攻击在路径的**哪个位置**以及由哪个控制措施拦截；制定一份从计数模式开始、包含测量预期和回滚触发条件的 AWS WAF 规则计划；并解释为什么如果攻击者可以直接从互联网访问源站，那么所有边缘控制措施对攻击者来说都形同虚设。

本章基于[工作簿 08](./08-cdn-edge-delivery.md#edge-origin-path)中介绍的边缘到源站路径（CloudFront → VPC 源站 → 内部 ALB），不再重复讲解。服务器自身的主机防火墙见[入门 06](../beginner/06-firewalls-host-security.md)。WAF 部署位置、规则排序陷阱、请求正文检查限制、转发的客户端 IP 和完整日志字段列表，见 [WAF、边缘与 API 安全](../../security/14-waf-edge-api-security.md)；本工作簿会链接到这些章节，而不是重复内容。Pod 级规则见[网络策略](../../security/04-network-policies.md)，Ingress 侧内容见 [AWS Load Balancer Controller](../03-aws-lb-controller.md)。Controller 文档中的示例使用 `alb.ingress.kubernetes.io/scheme: internet-facing`；**本课程的边缘设计中，ALB 是内部的**（`alb.ingress.kubernetes.io/scheme: internal`），并位于 CloudFront VPC 源站之后，因此阅读这些示例时，请将这一项替换为相应的值。使用 BGP 的 Anycast 路由见[工作簿 02](./02-routing-policy-convergence.md)，TCP 握手见[网络基础知识第 2 部分](../../basics/06-network-fundamentals-part2.md)。

**准备情况**：需要文本编辑器和 AWS 文档。无需 AWS 账户。自行构建此设计会产生 AWS WAF 费用（按 Web ACL、规则和每百万个请求收费，此外 Bot Control、账户接管防护、Anti-DDoS 规则组〔Shield Advanced 涵盖的情况除外〕、CAPTCHA 和 Challenge、超过 1,500 WCU 的容量以及日志记录都可能产生额外费用）、CloudFront 和负载均衡器费用；如果订阅，还会产生 AWS Shield Advanced 费用（定价页面列出的月费起价为 3,000 美元，合约期限为一年）。**这些费用和清理工作均由学习者自行承担**。除非有书面且获批的测试计划，否则切勿使用攻击流量进行测试，包括针对你自己的资源进行测试。

## 1. 带着问题阅读

考试范围仅用于决定阅读哪些内容。数字和行为以第一列的官方页面为准。

| 阅读内容 | 对应的考试范围 | 用自己的话回答 |
|---|---|---|
| [AWS Shield Standard 概述](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-standard-summary.html)，[Shield 针对 CloudFront 和 Route 53 的缓解逻辑](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-event-mitigation-logic-continuous-inspection.html) | ANS-C01 考试领域 4：网络安全、合规与治理，任务 4.1（使用 AWS WAF 和 AWS Shield 保护入站流量） | 针对 CloudFront 分配的 SYN flood 为什么不会变成源站的 SYN flood？ |
| [使用规则操作](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-action.html)，[基于速率的规则设置](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based-high-level-settings.html)，[Web 请求标记](https://docs.aws.amazon.com/waf/latest/developerguide/waf-labels.html) | 考试领域 4，任务 4.1（威胁模型、缓解策略） | 哪些操作会结束请求评估，哪些操作会让后续规则继续检查请求？ |
| [AWS Shield Advanced 功能](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-advanced-summary-capabilities.html)，[Anti-DDoS 托管规则组](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-anti-ddos.html) | 考试领域 4，任务 4.1 | Shield Advanced 增加了哪些 Shield Standard 不具备的功能？它首先需要什么？ |
| [测试和调整防护措施](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing.html)，[记录 Web ACL 流量](https://docs.aws.amazon.com/waf/latest/developerguide/logging.html)，[查看采样请求](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing-view-sample.html) | 考试领域 4，任务 4.2（使用监控和日志验证并审计安全性） | 哪个日志字段可以显示计数模式下的规则原本会匹配请求？ |
| [OWASP Top 10 2021](https://owasp.org/Top10/2021/) | 考试领域 4，任务 4.1（常见安全威胁） | 边缘 WAF 能降低十类风险中的哪些？哪些只能由应用程序修复？ |

阅读后，画出从客户端到 Pod 的路径，并在图上标出第 2 节中每种攻击被拦截的位置。如果设计评审无法指出某种攻击被拦截的位置，就说明该攻击尚未纳入评审。

## 2. 威胁层：每种攻击会耗尽什么资源

判断攻击针对哪个位置时，可以先问它试图耗尽哪种资源：链路带宽、连接状态、TLS 处理所需的 CPU，还是应用程序处理能力。

| 层 | 攻击 | 机制 | 耗尽的资源 |
|---|---|---|---|
| L3 | **UDP 反射攻击** | 攻击者将受害者地址伪造成发往第三方服务器（DNS、NTP、SSDP、CLDAP、Memcached、CharGen、QOTD）的较小 UDP 请求的源地址，第三方服务器随后向受害者发送大得多的响应。AWS 白皮书给出的 DNS 放大倍数为 28 到 54 倍 | 链路和网络容量 |
| L4 | **SYN flood** | 大量 SYN 请求无法完成三次握手（[第 2 部分](../../basics/06-network-fundamentals-part2.md)） | 监听端的半开连接队列（[RFC 4987](https://www.rfc-editor.org/rfc/rfc4987.html) §2.2）；攻击无须填满链路 |
| L6 | **TLS 滥用** | 将不可读取的数据伪装成握手、无休止地重新协商，或者快速建立并关闭会话 | 终止 TLS 的一侧的 CPU |
| L7 | **HTTP flood** | 发送看起来像合法用户请求的请求，有时会模仿人类浏览行为 | 应用程序容量；低流量也可能足以造成影响 |
| L7 | **缓存规避攻击** | HTTP flood 不断改变查询字符串，迫使 CDN 转发每个请求（[工作簿 08](./08-cdn-edge-delivery.md)第 5 节） | 缓存之后的源站容量 |
| L7 | **漏洞利用尝试** | 针对已知漏洞类别的有效载荷（第 4 节） | 机密性和完整性，而非容量 |
| L7 | **机器人、抓取程序、凭证填充攻击** | 自动窃取内容，并使用泄露的用户名和密码组合尝试登录 | 业务逻辑和账户；白皮书指出，这些严格来说并非 DDoS，但表现看起来类似 |

由此可得出两个结论。第一，反射攻击需要能够伪造源地址，而实施源地址验证的网络（[BCP 38](https://www.rfc-editor.org/info/bcp38)）可以消除这种能力。第二，L7 攻击使用格式正确的流量，因此只检查数据包是否有效的机制无法阻止它；需要能够读取请求内容的控制措施。

## 3. 每种攻击会在哪里被拦截

| 攻击 | 拦截位置 | 机制 | 责任方 |
|---|---|---|---|
| UDP 反射攻击 | CloudFront 边缘 | Shield 缓解措施只放行对 Web 应用有效的流量；CloudFront 只接受格式正确的连接 | AWS（自动） |
| SYN flood | CloudFront 边缘 | Shield TCP SYN 代理会在连接到达服务之前验证握手（无状态 SYN cookie） | AWS（自动） |
| TLS 滥用 | CloudFront 边缘 | TLS 在边缘终止，因此源站只会看到格式正确的请求（[工作簿 08](./08-cdn-edge-delivery.md)第 7 节） | AWS（自动） |
| HTTP flood、缓存规避攻击 | 边缘的 WAF Web ACL | 基于速率的规则、Anti-DDoS 托管规则组、Challenge | 你 |
| 漏洞利用尝试 | WAF Web ACL，然后是应用程序 | 托管规则组作为第一道过滤；应用程序负责输入验证和授权 | 你 |
| 凭证填充攻击 | WAF（账户接管防护），然后是应用程序 | 检查被盗凭证并限制登录量；应用程序负责 MFA 和锁定策略 | 你 |
| 任何直接针对源站的攻击 | **无处拦截**，除非源站没有公共网络路径 | 隐藏源站（第 8 节） | 你 |

**SYN cookie** 让监听端在 SYN-RECEIVED 状态下无需为连接保留状态：服务器将所需信息编码在 SYN-ACK 的序列号中，并在收到有效 ACK 时重建状态（[RFC 4987](https://www.rfc-editor.org/rfc/rfc4987.html) §3.6）。AWS 白皮书将边缘服务的无状态 SYN flood 缓解机制描述为：在转发连接之前，使用 SYN cookie 验证入站连接；白皮书还指出，现代操作系统默认启用 SYN cookie。CloudFront 也会与源站保持持久连接，因此查看者的新连接并不意味着源站建立了新连接。AWS WAF 和安全组都不能取代这些机制：AWS WAF 检查 HTTP 请求，因此只有在连接建立后才会发挥作用；安全组则根据源、协议和端口放行或拒绝流量，但不会限制速率。

**吸收攻击流量**需要拥有大于攻击流量的容量。AWS 关于 CloudFront Shield 缓解措施的页面指出，CloudFront 结合使用 DNS 流量导向和 Anycast 路由，在靠近攻击源的位置缓解攻击并隔离故障。这与工作簿 08 中的说明一致：DNS 将每个查看者引导至某个 POP，攻击流量会落到许多 POP 上，而不是集中到一个源站。Shield 缓解措施与边缘服务集成；白皮书指出，这能将缓解时间从几分钟缩短到不到一秒。

**被拒绝流量的费用**：白皮书指出，对于 CloudFront 或 AWS WAF 拒绝的请求，不会收取 HTTP 请求费用或数据传出费用。WAF 阻止的请求会产生 WAF 请求检查费用，但不会消耗源站容量。

**实践要点**：边缘会拦截流量规模，但不会决定谁可以执行什么操作。AWS WAF 可以缩小漏洞利用和滥用的攻击面，但[授权仍由应用程序负责](../../security/14-waf-edge-api-security.md)（该章第 1 节）。如果设计中 WAF 是业务操作唯一的检查点，就存在单点故障。

## 4. OWASP Top 10 2021 与边缘 WAF 能做什么

[OWASP Top 10 2021](https://owasp.org/Top10/2021/) 列出了十类 Web 应用程序风险，即 A01 至 A10。OWASP 后来发布了 2025 版；本工作簿使用 2021 版列表。AWS 将其核心规则集描述为能够防御 OWASP 出版物（例如 Top 10）中所述的“某些高风险且常见的漏洞”。应将托管规则视为用于过滤已知请求模式的措施，而不是对某个风险类别的全面防护。

| 2021 类别 | 边缘 WAF 的作用（AWS 托管规则组示例） | 只有应用程序或平台才能采取的措施 |
|---|---|---|
| A01 失效的访问控制 | 作用有限：请求看起来合法 | 对每个请求执行对象级授权 |
| A02 加密失效 | WAF 无法处理 | 在每一段链路上使用 TLS（[工作簿 08](./08-cdn-edge-delivery.md)第 7 节），并妥善处理密钥和数据 |
| A03 注入 | SQL 注入规则（`AWSManagedRulesSQLiRuleSet`，200 WCU），以及核心规则集中的跨站脚本规则 | 使用参数化查询、对输出进行编码 |
| A04 不安全的设计 | 无 | 威胁建模、业务限制 |
| A05 安全配置错误 | 间接作用 | 配置审查；源站可以从公网访问，是边缘设计中的配置错误（第 8 节） |
| A06 易受攻击和过时的组件 | 拦截已知恶意输入（`AWSManagedRulesKnownBadInputsRuleSet`，200 WCU），例如 Log4j 和 Java 反序列化模式 | 打补丁；WAF 规则只能争取时间 |
| A07 身份识别和身份验证失效 | 账户接管防护（`AWSManagedRulesATPRuleSet`，50 WCU，收费） | MFA、账户锁定、会话处理 |
| A08 软件和数据完整性失效 | 无 | 已签名的制品、供应链控制 |
| A09 安全日志记录和监控失效 | WAF 日志和指标是一个数据来源（第 9 节） | 跨层关联和告警 |
| A10 服务器端请求伪造（SSRF） | 核心规则集中的规则会查找试图窃取 EC2 元数据的请求（`EC2MetaDataSSRF_*`） | 应用程序中的出站流量控制和 URL 验证 |

核心规则集（`AWSManagedRulesCommonRuleSet`）需要 700 WCU。它还会强制执行大小限制，例如 `SizeRestrictions_BODY` 会阻止超过 8 KB 的请求正文；这通常会导致上传路径产生误报（第 10 节）。

## 5. AWS WAF 模型

**Web ACL。** AWS WAF 控制台现在将 Web ACL 称为**保护包（Web ACL）**；本工作簿使用“Web ACL”。Web ACL 包含规则和规则组，以及一个**默认操作**（Allow 或 Block），用于处理未被任何规则终止评估的请求。每个资源最多关联一个 Web ACL，一个 Web ACL 则可以保护多个资源。

**作用范围。** CloudFront 的 Web ACL 是**全局**的：其固定区域为美国东部（弗吉尼亚北部）。通过 CLI 时，需传入 `--scope=CLOUDFRONT --region=us-east-1`；通过 API 和 SDK 时，需使用 `us-east-1` 端点。与 CloudFront 分配关联的 Web ACL 不能再关联其他资源类型；像 ALB 这样的区域性资源需要在其所在区域使用单独的 `REGIONAL` Web ACL。

**规则、规则组与顺序。** 规则由语句和操作组成。规则组是一组可重复使用的规则，可以由你自行创建，也可以使用**托管规则组**（AWS Managed Rules、AWS Marketplace 卖家提供的规则组）。AWS WAF 按数字优先级从低到高评估规则，直到某条规则终止评估或规则全部用尽；在规则组内部，则使用该组自身的优先级。关于排序陷阱（过早使用宽泛的 Allow、豁免整个组），见 [security/14 第 3 节](../../security/14-waf-edge-api-security.md)。

**操作：**

| 操作 | 是否结束评估？ | 行为 |
|---|---|---|
| Allow | 是 | 将请求转发到受保护资源；你自己的规则可以插入自定义请求标头 |
| Block | 是 | 默认由受保护资源返回 `403 (Forbidden)`；你自己的规则可以定义自定义响应 |
| Count | 否 | 统计匹配结果并继续评估下一条规则；可以添加标签和自定义请求标头 |
| CAPTCHA | 取决于令牌 | 令牌有效且未过期：行为与 Count 相同。令牌缺失、无效或已过期：阻止请求，并在客户端能够显示时发送 CAPTCHA 谜题 |
| Challenge | 取决于令牌 | 令牌逻辑相同，但采用静默浏览器质询，而不是谜题 |

CAPTCHA 和 Challenge 只会在浏览器通过安全上下文访问 HTTPS 端点时运行，并且两者都会产生额外费用。非浏览器 API 客户端无法响应这些质询，因此应单独测试机器 API；AWS WAF 还提供应用程序集成 SDK，可向应用程序发出的请求添加令牌。AWS 还新增了 **Monetize** 操作（HTTP `402 Payment Required`，仅限 CloudFront Web ACL，属于终止操作，不能用于基于速率的规则）；本工作簿不涉及此操作。

**基于速率的规则。** 基于速率的规则会在 **评估窗口**（60、120、300 或 600 秒，默认 300 秒）内统计每个**聚合实例**（例如每个源 IP）的请求，并对超过**限制**（最小值为 10）的实例后续符合条件的请求应用相应操作。操作可以是除 Allow 以外的任何操作。**范围缩小语句**用于限制统计和采取操作的请求，例如只处理发往 `/login` 的 `POST` 请求。设计时需要考虑以下行为：

- AWS WAF 使用一种更重视近期请求的算法估算速率，因此其限制效果接近配置值，而不会精确卡在该值。
- 指南指出，速率会频繁检查，且检查频率独立于时间窗口；API 参考指出检查间隔约为每 10 秒一次。开始限制之前，请求可能会有数分钟的时间以过快的速度到达；速率降下来后，限制也可能继续，通常持续不到 30 秒。
- 更改限制、时间窗口、聚合方式、转发的 IP 配置或范围，会**重置计数**，并可能导致速率限制暂停最多一分钟。
- 基于速率的语句不能嵌套在另一条语句中（例如 `NotStatement`），但其范围缩小语句可以包含其他语句。
- 如果只按 IP 聚合，`GetRateBasedStatementManagedKeys` 会列出当前受到限制的地址。

CloudFront → ALB → Ingress 路径上应聚合哪个客户端地址，见 [security/14 第 5 节](../../security/14-waf-edge-api-security.md)。

**标签。** 标签是匹配规则添加到请求上的元数据；在该 Web ACL 的后续评估中，标签会一直保留，后续规则可通过**标签匹配语句**读取标签。你自己的标签格式为 `awswaf:<account id>:<rulegroup or webacl>:<name>:<namespace>:...:<label name>`；托管规则组标签的格式为 `awswaf:managed:<vendor>:<rule group name>:...`，例如 `awswaf:managed:aws:core-rule-set:NoUserAgent_Header`。所有 AWS Managed Rules 规则组都会添加标签。主要模式是：将一条规则设为 Count，使其只负责添加标签，然后添加一条后续规则，根据标签组合做出决定。标签也会生成 CloudWatch 标签指标。

**覆盖托管规则。** 有两种不同的开关：

| 覆盖方式 | 会发生什么 | 是否用于测试？ |
|---|---|---|
| **规则操作覆盖**（`RuleActionOverrides`，适用于组内的每条规则） | 对匹配请求的处理方式与该规则的操作被覆盖时完全相同，例如改为 Count；规则组会继续评估其中其他规则 | 是，这是文档说明的测试规则组的方式 |
| **将规则组返回操作覆盖为 Count** | 规则组按正常方式评估，并在首次遇到终止匹配时停止；只有返回 Web ACL 的结果会变为 Count | 否：指南指出，这不会改变规则组的评估方式，因此对于该请求，组内后续规则不会运行 |

`RuleActionOverrides` 于 2022 年 10 月取代了较旧的 `ExcludedRules` 设置。

**容量（WCU）。** Web ACL 容量单位用于衡量规则所需的运算资源；它们不会改变流量的检查方式。简单语句的成本低于正则表达式模式集或 JSON 正文检查等操作。规则组的**容量在创建时确定且不可更改**（最高 5,000 WCU）；在 Web ACL 中使用规则组时，按该容量计费，而不是按其当前内容计费。一个 Web ACL 最多可使用 5,000 WCU；基础价格包含 1,500 WCU，超过部分按阶梯额外收费。部署前可以使用 `CheckCapacity` API 获取规则列表的容量。

**传播。** 更改需要几秒到几分钟才能传播到所有位置，因此短时间内，有些位置可能已应用新操作，而其他位置仍在应用旧操作。

## 6. AWS Shield Standard 和 Shield Advanced

| | Shield Standard | Shield Advanced |
|---|---|---|
| 费用和启用方式 | 自动为每位 AWS 客户启用，不收取额外费用 | 需要订阅；定价页面列出的月费起价为 3,000 美元，合约期限为一年，并会自动续订。仅保护你明确添加的资源（也可以通过 AWS Firewall Manager Shield Advanced 策略添加） |
| 覆盖范围 | 最常见、频繁发生的网络层和传输层攻击；CloudFront 分配、Route 53 托管区和 Global Accelerator 标准加速器均可防御所有已知的网络层和传输层攻击 | CloudFront、Route 53 托管区、Global Accelerator 标准加速器、Elastic IP 地址（以及其背后的 EC2 实例和 NLB）、ALB 和 Classic Load Balancer |
| 应用层（L7） | 本身不提供；L7 防护由 WAF 负责 | 使用 AWS WAF Web ACL；受保护资源的标准 WAF 费用最多覆盖 1,500 WCU 和默认正文大小。不覆盖 Bot Control、CAPTCHA、超过 1,500 WCU 的容量和更大的正文检查。订阅还包含 Anti-DDoS 规则组，无需额外付费；每个付款方每月最多 500 亿个请求的 AWS WAF 请求费用也包含在内（超出部分每百万个请求收费 0.15 美元） |
| 自动 L7 缓解 | 无 | 见下一段 |
| 响应团队 | 无 | **Shield 响应团队**（SRT）可在攻击期间提供帮助并制定自定义缓解措施；需要 Business Support 或 Enterprise Support 计划（DDoS 弹性白皮书将其称为 Business Support+ 或 Enterprise Support） |
| 检测 | 自动 | 基于 Route 53 运行状况检查进行运行状况检测；**主动参与**（SRT 联系你）需要运行状况检查 |
| 成本保护 | 无 | 针对攻击导致的部分扩展费用提供 Shield Advanced 服务抵扣 |
| 可见性 | 除服务指标外无其他可见性 | 可通过控制台、API 和 CloudWatch 指标查看事件详情；提供保护组 |

**2026 年的自动 L7 缓解。** 自 2026 年 3 月 26 日起，**Anti-DDoS 托管规则组**（`AWSManagedRulesAntiDDoSRuleSet`，50 WCU；单独使用普通 AWS WAF 时会产生额外费用，订阅 Shield Advanced 时则无需额外付费）成为 AWS 针对 HTTP 请求 flood 的默认解决方案，取代了 Shield Advanced 的第 7 层自动缓解功能；已有客户仍可继续使用原功能。该规则组会将流量与资源基线进行比较，在事件期间为每个请求添加标签（`awswaf:managed:aws:anti-ddos:event-detected`），并根据置信度为疑似来源添加标签（`low-`、`medium-`、`high-suspicion-ddos-request`）；它会发送静默 Challenge 作为软性缓解措施（只有 `GET` 请求可以被标记为可进行 Challenge 的请求），并通过阻止请求实施强制缓解。旧版 Shield Advanced 功能会增加一个 150 WCU 的规则组，需要 24 小时到 30 天学习基线，可以执行计数或阻止操作；在 CDN 后方的 ALB 上效果较差，因为 CDN 可能不会转发原始客户端属性。AWS 建议在 CloudFront 分配上启用该功能。

## 7. 参考路径上的纵深防御

![边缘安全动画。① 僵尸网络向 CloudFront 边缘发起 L3/L4 flood（UDP 反射攻击和 SYN flood）；Shield 在边缘吸收攻击流量，不会有流量到达源站。② 机器人向 /login 发送格式正确的 HTTPS flood；它通过了 L3/L4 检查，但 WAF Web ACL 中名为 rate-login 的示例基于速率的规则会阻止该请求，客户端收到 403 Forbidden。③ 合法的 GET 请求通过 Shield；由于没有任何 WAF 规则终止其评估，Web ACL 的默认操作 Allow 会将其转发。④ CloudFront 通过 VPC 源站进行连接：私有子网中的服务管理 ENI（10.0.11.25）连接到内部 ALB（10.0.12.40）；ALB 的安全组只放行 CloudFront-VPCOrigins-Service-SG 或面向源站的前缀列表。⑤ ALB 由 scheme 为 internal 的 Ingress 创建，并将请求转发到 Pod IP 10.0.13.31；该 Pod 的 NetworkPolicy 只放行来自 ALB 子网的流量，随后 Pod 返回 200。这里没有面向互联网的负载均衡器，也没有放行公共 CIDR 的入站规则。](../../.gitbook/assets/en-networking-expert-09-edge-security-waf-ddos-anim-0.svg)

| 层 | 控制措施 | 放行内容 | 有效的证据 |
|---|---|---|---|
| 边缘网络 | Shield Standard、CloudFront（DNS 导向、Anycast、SYN 代理、边缘 TLS） | 格式正确的 HTTP(S) 连接 | 网络层事件期间源站负载未发生变化；如果订阅了 Shield Advanced，则查看其事件数据 |
| 边缘应用 | 全局 Web ACL（`CLOUDFRONT` 作用范围，us-east-1） | 未被任何规则终止处理的请求，随后由默认操作决定 | WAF 日志中的 `terminatingRuleId`、`action`、标签 |
| 源站路径 | VPC 源站到内部 ALB（[工作簿 08](./08-cdn-edge-delivery.md#edge-origin-path)） | 仅允许 CloudFront；ALB 只有私有地址 | 不存在可用于测试的互联网路由 |
| ALB 安全组 | 仅允许来自 `CloudFront-VPCOrigins-Service-SG`（你的分配）或托管前缀列表 `com.amazonaws.global.cloudfront.origin-facing`（任何分配）的入站流量 | CloudFront 的 VPC 源站 ENI | 安全组规则；预期 ALB 访问日志中只显示来自 VPC 源站子网的地址 |
| Ingress | AWS Load Balancer Controller，使用 `alb.ingress.kubernetes.io/scheme: internal` 和 `target-type: ip`（[AWS Load Balancer Controller](../03-aws-lb-controller.md)） | 你定义的侦听器规则 | Ingress 事件、目标运行状况 |
| Pod | NetworkPolicy 通过包含 ALB 子网的 `ipBlock` 放行 Ingress 流量（[网络策略](../../security/04-network-policies.md#kubernetes-networkpolicy-spec)） | 来自 ALB 节点的连接 | 如果启用，则查看 CNI 策略日志中被拒绝的连接 |
| 主机 | 主机防火墙（[入门 06](../beginner/06-firewalls-host-security.md)） | 节点必须提供服务的端口 | 防火墙计数器 |
| 应用程序 | 身份验证和授权 | 用户获准执行的操作 | 应用程序审计日志 |

**Pod 会看到哪个源地址。** ALB 是代理：ELB 指南指出，服务器访问日志中只包含负载均衡器的 IP 地址；客户端地址则位于 `X-Forwarded-For` 中，只有在由安全可靠的系统正确添加时，该地址才可信。因此，Pod IP 目标看到的是 ALB 节点的私有地址，这也是上面的 NetworkPolicy 指定 ALB 子网的原因。Kubernetes 文档警告，地址改写是在 NetworkPolicy 处理之前还是之后发生，取决于网络插件、云提供商和 Service 实现。因此，在依赖规则之前，请先在自己的 CNI 上确认观测到的源地址；同时请记住，如果没有会强制执行策略的插件，NetworkPolicy 不会生效。

**使用一个还是两个 Web ACL。** CloudFront Web ACL 不能同时关联到 ALB。如果你在 ALB 上添加区域性 Web ACL，那就是一次独立的第二层检查，拥有各自的日志和费用；何时值得这样做，见 [security/14 第 2 节](../../security/14-waf-edge-api-security.md)。

## 8. 隐藏源站：可访问的源站为何会绕过边缘

上表中边缘部分的每项控制措施都**只适用于经过分配的请求**。如果攻击者发现一个可以从互联网访问且会响应请求的源站地址或 DNS 名称，就可以直接向该地址发送请求，一次性绕过 Shield 的边缘流量吸收、全局 Web ACL、基于速率的规则和 CloudFront 的 TLS 终止。这样一来，源站只能依靠自身容量应对原始 SYN flood 和 HTTP flood，而 WAF 日志中不会有任何记录。

**隐藏源站**是指源站完全没有互联网路径。在参考设计中，这是路由层面的属性，而不是过滤措施：内部 ALB 只有私有地址，因此即使之后放宽安全组，也仍然无法从互联网访问它（[工作簿 08](./08-cdn-edge-delivery.md#edge-origin-path)）。比较一下 [security/14 选项 A](../../security/14-waf-edge-api-security.md)中描述的较弱设计：使用公共 ALB，只放行 CloudFront 前缀列表并检查机密标头。前缀列表会放行**任何** CloudFront 分配，包括攻击者创建的分配；而标头是共享机密，一旦泄露就会失去防护作用。本课程不采用这种设计。

**评审时的绕过路径清单**：仍指向旧公共源站的过期 DNS 记录、同一集群中的其他负载均衡器或 `LoadBalancer` 类型的 Service、NodePort、管理端点，以及提供相同应用程序的测试环境。某条路径上的私有源站标记并不能证明不存在其他路径。

## 9. 日志和指标：每种信号能证明什么

| 信号 | 位置 | 能告诉你什么 | 局限 |
|---|---|---|---|
| WAF 日志 | CloudWatch Logs 日志组、S3 存储桶或 Amazon Data Firehose 流，名称以 `aws-waf-logs-` 开头 | 每个请求的信息：`terminatingRuleId` 和 `action`、`nonTerminatingMatchingRules` 中的 Count 匹配结果、`ruleGroupId`、`labels` | 需单独付费；你可以筛选要保留的请求，也可以隐藏字段（显示为 `xxx`） |
| CloudWatch 指标 | AWS WAF 指标 | 按操作分组的匹配结果（Count 规则的匹配结果显示为 Count 指标）；每个标签的标签指标 | 规则组内部的 Count 操作规则不会生成 Web ACL 维度指标，只会生成 Rule、RuleGroup 和 Region 维度指标 |
| 采样请求 | Web ACL 控制台标签页或 `GetSampledRequests` | 从前 3 小时内选取的最多 100 个匹配规则的请求和最多 100 个采用默认操作的请求，以及对应的规则、操作和 URI | 需要启用采样；Web ACL 视图不会显示规则组内部 Count 规则的采样请求；日志记录中的字段隐藏不适用于采样 |
| 流量概览仪表板 | WAF 控制台 | CloudWatch 指标的近实时摘要 | 只提供摘要，不是请求证据 |
| Shield Advanced 事件 | Shield 控制台、API、CloudWatch | 受保护资源上检测到的事件和缓解措施 | 仅限订阅用户 |
| CloudFront 日志 | [工作簿 08 第 10 节](./08-cdn-edge-delivery.md) | 边缘上每个请求的状态码和结果类型 | 匹配的规则记录在 WAF 日志中，因此需要关联两者 |

WAF 日志字段的完整列表见 [security/14 第 6 节](../../security/14-waf-edge-api-security.md)。对于 Count 规则，**日志和标签指标**是可靠的证据，因为采样请求和 Web ACL 指标可能会隐藏托管规则组内部 Count 规则的匹配结果。

## 10. 练习：编写计数模式规则计划并设定回滚触发条件

桌面演练。你要编写一份他人日后可以在获批账户中执行的计划，但不实际部署。请将结果标记为**演算示例，未经测量**。

**场景。** 某商店通过第 7 节的参考路径提供 `/assets/*`、`/login`（`POST`，浏览器表单）、`/api/*`（移动应用，非浏览器）和 `/api/upload`（最大 5 MB 的图片）。连续七天的 CloudFront 日志给出了以下基线：

| 路径 | 流量量 | 任意 5 分钟内的单 IP 峰值 | 备注 |
|---|---|---|---|
| `POST /login` | 每天 120 万次，成功率 96% | 请求数 p99 为 18；地址 `198.51.100.20` 峰值为 640 | `198.51.100.20` 是合作伙伴的办公室 NAT 地址，由许多员工共用 |
| `/api/upload` | 每天 40,000 次 | 请求数 p99 为 6 | 每个请求正文都大于 8 KB |
| `/api/*`（其他） | 每天 900 万次 | 请求数 p99 为 120 | 移动应用，无法运行 Challenge 或 CAPTCHA |

Web ACL 的默认操作为 Allow。

**计划（填写或检查每一行）：**

| 优先级 | 规则 | 试运行操作 | 试运行期间的预期匹配数 | 设为 Block 前的决定 |
|---|---|---|---|---|
| 10 | `AWSManagedRulesCommonRuleSet`，使用 `RuleActionOverrides` 将每条规则都覆盖为 Count | Count（每条规则） | `SizeRestrictions_BODY` 几乎会匹配每天全部 40,000 个 `/api/upload` 请求（正文超过 8 KB）；真实用户触发其他规则的次数接近零 | 使用范围缩小语句，将 `/api/upload` 排除在规则组之外；或者让 `SizeRestrictions_BODY` 保持 Count，并添加用于其他路径的标签匹配规则 |
| 20 | `AWSManagedRulesSQLiRuleSet`，将规则覆盖为 Count | Count（每条规则） | 来自真实用户的匹配数接近零 | 将来自已知客户端的每次匹配都调查清楚后，再启用阻止 |
| 30 | `rate-login`：基于速率的规则，按 IP 聚合，时间窗口为 300 秒，限制为 100，范围缩小到 `POST` 且路径以 `/login` 开头 | Count | 普通用户不会匹配（请求数 p99 为 18，远低于 100）；`198.51.100.20` 一旦超过 100 就会匹配：在安静时段之后出现一次持续 5 分钟、峰值为 640 的突发流量时，约有 540 个请求会被计数（即超过限制的请求）；如果其流量持续高于 100，则之后几乎所有请求都会被计数，因为规则会持续生效，直到估算速率降到限制以下 | 误报：在范围缩小语句中添加 `NOT`（IP 集合包含 `198.51.100.20`），或为该地址单独设置更高的限制 |

下面是第 30 行的片段。它展示的是已作出误报决定后的规则，并添加了 `PartnerNat` 排除项；在表格所述的试运行期间，不包含 `NotStatement`。这只是 **Web ACL 中的一条规则**，并非完整的 Web ACL 或部署命令；`PartnerNat` 是你需要创建的 IP 集。

```json
{
  "Name": "rate-login",
  "Priority": 30,
  "Statement": {
    "RateBasedStatement": {
      "Limit": 100,
      "EvaluationWindowSec": 300,
      "AggregateKeyType": "IP",
      "ScopeDownStatement": {
        "AndStatement": {
          "Statements": [
            { "ByteMatchStatement": { "SearchString": "POST", "FieldToMatch": { "Method": {} },
                "TextTransformations": [{ "Priority": 0, "Type": "NONE" }], "PositionalConstraint": "EXACTLY" } },
            { "ByteMatchStatement": { "SearchString": "/login", "FieldToMatch": { "UriPath": {} },
                "TextTransformations": [{ "Priority": 0, "Type": "NONE" }], "PositionalConstraint": "STARTS_WITH" } },
            { "NotStatement": { "Statement": { "IPSetReferenceStatement": {
                "ARN": "arn:aws:wafv2:us-east-1:111122223333:global/ipset/PartnerNat/<id>" } } } }
          ]
        }
      }
    }
  },
  "Action": { "Count": {} },
  "VisibilityConfig": { "SampledRequestsEnabled": true, "CloudWatchMetricsEnabled": true, "MetricName": "rate-login" }
}
```

**任务：**

1. 完成计划：为每一行写出要查看的证据（日志字段、指标或标签）、试运行时长，以及决策负责人。
2. 解释第 10 行为什么使用逐条规则的 `RuleActionOverrides`，而不使用规则组返回操作覆盖（第 5 节）。
3. 分别计算 `rate-login` 在有无 `PartnerNat` 排除项时，单次突发流量和持续峰值的预期 Count 匹配数，并说明实际数字为什么会不同（计数为近似值、检测有延迟，以及速率下降后限制仍会短暂持续）。
4. 对每条要切换为 Block 的规则编写**回滚触发条件**。触发条件必须包含可测量的阈值、时间窗口、责任人和确切操作。示例：“`rate-login` 切换为 Block 后，如果 `/login` 成功率连续 10 分钟低于 96% 基线超过 2 个百分点，或任何来自合成登录检查的请求被阻止，则当班工程师应将 `rate-login` 改回 Count 并记录此次更改。”请注意，回滚本身需要几秒到几分钟才能传播；对于基于速率的规则，回滚还会重置计数。
5. 决定移动端 `/api/*` 流量应使用什么措施来替代 Challenge 或 CAPTCHA，并说明原因。
6. 决定计划中是否应包含 Anti-DDoS 托管规则组；如果包含，它应位于第 30 行之前还是之后？

**评审标准：**

- 每个预期数字都来自基线表，并列出计算过程。
- 每次将规则升级为 Block 时，证据来源都能看到托管规则组内部的 Count 匹配（日志或标签，而非仅查看采样请求）。
- 计划每次只更改一条规则，并留出传播时间后再评估结果。
- 计划中不得暴露源站、添加面向互联网的负载均衡器或放行公共 CIDR。

## 11. 观察故障和恢复

本表旨在练习**使用哪些证据来确认每项诊断**。如果之后在获批环境中重现某种场景，请准确收集这些证据。

| 故障 | 预期行为 | 证据 | 这些证据不能证明什么 |
|---|---|---|---|
| 托管规则阻止合法上传 | 规则升级后，`/api/upload` 返回 `403` | WAF 日志中的 `terminatingRuleId` = 规则组、规则 `SizeRestrictions_BODY`；CloudFront `403` 比率上升 | 规则组中的其他规则是安全的 |
| 攻击期间更改了速率限制 | 限制暂停最多一分钟 | 更改记录；Count 或 Block 指标先下降，然后恢复 | 新限制是正确的 |
| 从 Block 回滚到 Count | 有些位置仍会在短时间内阻止请求 | Block 指标在几秒到几分钟内下降 | 在某一时刻，所有位置都已应用新设置 |
| 直接请求暴露的源站 | 源站过载，但 WAF 指标保持平稳 | 源站访问日志显示的来源不是 CloudFront ENI | 攻击者发现了哪条路径（参见第 8 节的清单） |
| 分配遭受 L3/L4 flood | 源站不受影响 | 源站指标保持平稳；如果订阅了 Shield Advanced，则查看其事件 | 应用层是安全的 |
| Anti-DDoS 事件 | 每个请求，无论是否合法，都会添加 `event-detected` 标签 | 标签指标 | 添加标签的请求就是恶意请求（只有疑似请求标签才表示这一点） |
| 对移动 API 应用了 Challenge | 应用请求失败 | WAF 日志显示 app 流量由 Challenge 规则终止；应用程序错误率上升 | 客户端是机器人 |

**恢复本身也是一项变更**。每次回滚都是一次 Web ACL 更新，传播行为与导致事件的变更相同。应在将规则改为 Block 之前，将回滚命令及其责任人写入计划，而不是等到事件发生时再写。

## 12. 交付成果和完成标准

| 交付成果 | 完成标准 |
|---|---|
| 威胁图 | 将第 2 节中的每种攻击都标在路径上，并注明其拦截控制措施和责任方 |
| Shield 决策 | 仅使用 Standard，或使用 Advanced 并列出将采用的功能、前提条件（支持计划、运行状况检查）和费用 |
| 规则计划 | 优先级、试运行操作、带有计算过程的预期匹配数、误报处理决定和逐条规则的回滚触发条件 |
| 源站路径评审 | 确认参考路径上的源站已隐藏，检查绕过路径清单，并确认没有面向互联网的负载均衡器或放行公共 CIDR 的 Ingress |
| 证据计划 | 对每条规则，列明证明其匹配的日志字段或指标，以及已知盲点 |

当你能够结合资料解释每种攻击针对哪个层、会在哪里被拦截、AWS WAF 如何评估规则和操作、计数模式测试为何使用逐条规则覆盖、Shield Advanced 相较 Standard 增加了什么功能，以及源站为何不能有公共路径时，本章就完成了。复习 [WAF、边缘与 API 安全](../../security/14-waf-edge-api-security.md)中的 WAF 部署位置，重新查看[工作簿 08](./08-cdn-edge-delivery.md#edge-origin-path)中的源站路径，然后完成[测验](../../quizzes/networking/expert/09-edge-security-waf-ddos-quiz.md)。

## 参考资料

AWS WAF 开发人员指南

- [在 AWS WAF 中使用规则操作](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-action.html)（Allow、Block 及其默认 `403`、Count、CAPTCHA、Challenge、Monetize）
- [设置规则优先级](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-processing-order.html)
- [基于速率的规则高级设置](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based-high-level-settings.html)、[基于速率的规则注意事项](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-type-rate-based-caveats.html)
- [Web 请求标记](https://docs.aws.amazon.com/waf/latest/developerguide/waf-labels.html)、[标签语法和命名要求](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-label-requirements.html)
- [覆盖规则组操作](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-rule-group-override-options.html)
- [Web ACL 容量单位（WCU）](https://docs.aws.amazon.com/waf/latest/developerguide/aws-waf-capacity-units.html)
- [将保护关联到 AWS 资源或取消关联](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-associating-aws-resource.html)（美国东部〔弗吉尼亚北部〕区域中的全局 Web ACL、每个资源一个 Web ACL）
- [基线规则组](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-baseline.html)（核心规则集、已知恶意输入）、[特定使用场景的规则组](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-use-case.html)（SQL 数据库）、[账户接管防护规则组](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-atp.html)、[Anti-DDoS 规则组](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-anti-ddos.html)
- [测试和调整 AWS WAF 防护措施](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing.html)、[监控和调整](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing-activities.html)（计数模式、误报缓解、传播）
- [记录 Web ACL 流量](https://docs.aws.amazon.com/waf/latest/developerguide/logging.html)、[日志目标](https://docs.aws.amazon.com/waf/latest/developerguide/logging-destinations.html)、[配置日志记录](https://docs.aws.amazon.com/waf/latest/developerguide/logging-management-configure.html)（`aws-waf-logs-` 前缀、字段隐藏、筛选条件）
- [查看 Web 请求样本](https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-testing-view-sample.html)

AWS Shield（同一指南中的内容）

- [AWS Shield](https://docs.aws.amazon.com/waf/latest/developerguide/shield-chapter.html)、[Shield Standard 概述](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-standard-summary.html)
- [Shield 针对 CloudFront 和 Route 53 的缓解逻辑](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-event-mitigation-logic-continuous-inspection.html)（仅允许有效的 Web 流量、TCP SYN 代理、边缘 TLS、DNS 和 Anycast）
- [Shield Advanced 概述](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-advanced-summary.html)、[功能和选项](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-advanced-summary-capabilities.html)、[受保护资源](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-advanced-summary-protected-resources.html)
- [使用 Shield Advanced 自动缓解应用层 DDoS 攻击](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-automatic-app-layer-response.html)（自 2026 年 3 月 26 日起，默认使用 Anti-DDoS 规则组；150 WCU；基线学习时间为 24 小时到 30 天；CDN 后方的 ALB）
- [AWS Shield 定价](https://aws.amazon.com/shield/pricing/)

其他 AWS 资料

- [AWS WAF API 参考：CreateWebACL](https://docs.aws.amazon.com/waf/latest/APIReference/API_CreateWebACL.html)（`CLOUDFRONT` 作用范围和 `us-east-1`、默认操作）、[RateBasedStatement](https://docs.aws.amazon.com/waf/latest/APIReference/API_RateBasedStatement.html)（限制范围、时间窗口、约每 10 秒进行一次速率检查、嵌套）
- [AWS DDoS 弹性最佳实践：基础设施层攻击](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/infrastructure-layer-attacks.html)、[UDP 反射攻击](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/udp-reflection-attacks.html)、[SYN flood 攻击](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/syn-flood-attacks.html)、[应用层攻击](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/application-layer-attacks.html)、[缓解技术](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/mitigation-techniques.html)、[边缘上的 Web 应用交付（BP1）](https://docs.aws.amazon.com/whitepapers/latest/aws-best-practices-ddos-resiliency/web-application-delivery-at-the-edge-bp1.html)
- [Amazon CloudFront 开发人员指南：使用 AWS WAF 防护](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/distribution-web-awswaf.html)、[使用 VPC 源站限制访问](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html)
- [Elastic Load Balancing：HTTP 标头和 Application Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/x-forwarded-headers.html)（服务器日志中的负载均衡器地址、`X-Forwarded-For`）

标准和其他一手资料

- [RFC 4987：TCP SYN Flood 攻击及常见缓解措施](https://www.rfc-editor.org/rfc/rfc4987.html)（§2.2、§3.6）
- [BCP 38](https://www.rfc-editor.org/info/bcp38)（源地址验证）
- [OWASP Top 10 2021](https://owasp.org/Top10/2021/)
- [Kubernetes：网络策略](https://kubernetes.io/docs/concepts/services-networking/network-policies/)（`ipBlock`、源地址改写、插件要求）
- [RFC 1918](https://www.rfc-editor.org/rfc/rfc1918.html)、[RFC 5737](https://www.rfc-editor.org/rfc/rfc5737.html)（示例地址）

考试范围（仅用于选择主题）

- [AWS Certified Advanced Networking - Specialty (ANS-C01)：考试领域 4](https://docs.aws.amazon.com/aws-certification/latest/advanced-networking-specialty-01/advanced-networking-specialty-01-domain4.html)
