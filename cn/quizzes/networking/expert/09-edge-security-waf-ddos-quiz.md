# 09. 边缘安全：WAF 和 DDoS 防御测验

> **最后更新**：2026年11月19日

返回[练习册](../../../networking/expert/09-edge-security-waf-ddos.md)。
每题选择一个答案，并说明练习册中的哪条规则支持该答案。
这些是设计推理练习，并不表示已部署 Web ACL。

1. 一个僵尸网络向一个 CloudFront 分配发送 SYN 洪水攻击，该分配的源站是位于 VPC origin 后方的内部 ALB。为什么 ALB 不会收到 SYN 洪水？
   - A) 在边缘，Shield TCP SYN 代理会在连接到达服务之前验证握手（无状态 SYN cookie），而 CloudFront 会与源站保持自己的持久连接。
   - B) WAF Web ACL 使用基于速率的规则阻止 SYN 数据包。
   - C) ALB 安全组会丢弃到达速度过快的 SYN 数据包。

<details>
<summary>显示答案</summary>

**答案：A) 在边缘，Shield TCP SYN 代理会在连接到达服务之前验证握手（无状态 SYN cookie），而 CloudFront 会与源站保持自己的持久连接。**

**说明**：SYN 洪水会耗尽监听器的半开连接队列。这里的监听器是 CloudFront，Shield 的 SYN 代理只会放行完成握手的连接；查看者建立的新连接并不意味着要新建源站连接。AWS WAF 检查的是 HTTP 请求，而不是 TCP 段；安全组也不是速率限制器。

</details>

2. UDP 反射攻击需要攻击者具备什么能力？哪种网络实践可以消除这一条件？
   - A) 与反射器完成 TCP 握手；在所有地方使用 TLS 可以消除这一条件。
   - B) 将受害者地址伪造为源地址的能力；源地址验证（BCP 38）可以消除这一条件。
   - C) 发送有效 HTTP 请求的能力；基于速率的 WAF 规则可以消除这一条件。

<details>
<summary>显示答案</summary>

**答案：B) 将受害者地址伪造为源地址的能力；源地址验证（BCP 38）可以消除这一条件。**

**说明**：攻击者发送较小的 UDP 请求（DNS、NTP、SSDP、CLDAP、Memcached 等），并将受害者地址设为源地址；反射器随后会向受害者发送大得多的响应。对于 DNS，AWS 白皮书给出的放大倍数为 28 到 54 倍。验证源地址的网络能够杜绝地址伪造。

</details>

3. 某个请求匹配了一条操作为 CAPTCHA 的规则，并携带有效且未过期的 CAPTCHA 令牌。AWS WAF 会怎么处理？
   - A) 阻止请求并发送新的谜题。
   - B) 立即允许请求并停止评估。
   - C) 按 Count 处理请求，并继续评估剩余规则。

<details>
<summary>显示答案</summary>

**答案：C) 按 Count 处理请求，并继续评估剩余规则。**

**说明**：如果令牌有效且未过期，CAPTCHA 和 Challenge 都是非终止操作；如果令牌缺失、无效或已过期，它们则会终止评估（阻止请求，并显示谜题或静默挑战）。Allow 和 Block 始终会终止评估；Count 则永远不会终止。默认情况下，被阻止的请求会收到 `403 (Forbidden)`。

</details>

4. 以下哪项基于速率的规则配置**无效**？
   - A) 评估窗口 300 秒，限制 100，操作 Block。
   - B) 评估窗口 600 秒，限制 10，操作 Count。
   - C) 评估窗口 300 秒，限制 100，操作 Allow。

<details>
<summary>显示答案</summary>

**答案：C) 评估窗口 300 秒，限制 100，操作 Allow。**

**说明**：基于速率的规则可以使用除 Allow 以外的任何规则操作。评估窗口可以是 60、120、300 或 600 秒（默认值为 300 秒），最低限制值为 10，因此 A 和 B 均有效。

</details>

5. 在 HTTP 洪水攻击期间，一名工程师调低了一条已在阻止流量的基于速率的规则的限制值。团队应预期更改后会立即发生什么？
   - A) 新限制会立即生效，同时保留旧计数。
   - B) 更改会重置规则计数，并可能导致速率限制暂停最多一分钟。
   - C) 在下一个完整评估窗口结束之前，规则会保持不活动状态。

<details>
<summary>显示答案</summary>

**答案：B) 更改会重置规则计数，并可能导致速率限制暂停最多一分钟。**

**说明**：更改限制值、评估窗口、聚合方式、转发 IP 配置或作用范围都会重置计数。速率限制也是近似值：超过速率后，可能要过几分钟才开始限流；速率下降后，限流也可能短暂持续。应在事件发生前规划速率限制变更，而不是在事件期间变更。

</details>

6. 你想在强制执行之前，查看 `AWSManagedRulesCommonRuleSet` 中每条规则会阻止哪些请求。哪项设置可以实现这一目的？
   - A) 将规则组的返回操作覆盖为 Count。
   - B) 将 Web ACL 的默认操作设为 Count。
   - C) 使用 `RuleActionOverrides` 将每条规则的操作覆盖为 Count。

<details>
<summary>显示答案</summary>

**答案：C) 使用 `RuleActionOverrides` 将每条规则的操作覆盖为 Count。**

**说明**：使用逐条规则覆盖时，匹配的请求会按该规则的操作为 Count 来处理，而规则组会继续评估其他规则。将规则组的返回操作覆盖为 Count，并不会改变规则组的评估方式：评估会在首次匹配到终止性规则时停止，因此该请求不会再经过组内的后续规则。默认操作只能是 Allow 或 Block。

</details>

7. 优先级为 50 的规则 `block-bad-ua` 是一条标签匹配语句，用于匹配 `awswaf:managed:aws:core-rule-set:NoUserAgent_Header`。核心规则集的优先级为 100，且该规则已覆盖为 Count。为什么 `block-bad-ua` 永远不会匹配？
   - A) 托管规则组不会添加标签。
   - B) 标签只有在添加该标签的规则之后评估的规则才能使用，而优先级 50 的规则先于优先级 100 的规则运行。
   - C) Count 规则添加的标签会被丢弃。

<details>
<summary>显示答案</summary>

**答案：B) 标签只有在添加该标签的规则之后评估的规则才能使用，而优先级 50 的规则先于优先级 100 的规则运行。**

**说明**：AWS WAF 从数值最低的优先级开始向上评估。标签会在此次评估的剩余过程中保留，供之后的规则使用标签匹配语句读取。所有 AWS 托管规则组都会添加标签；将规则设为 Count，使其只添加标签，是主要的标签使用模式。应将标签匹配规则移到该规则组之后。

</details>

8. 你使用 CLI 创建 Web ACL 来保护 CloudFront 分配。以下哪项说法正确？
   - A) 使用 `--scope=CLOUDFRONT --region=us-east-1`；此全局 Web ACL 不能同时与 ALB 关联。
   - B) 在源站 ALB 所在的区域使用 `--scope=REGIONAL`，并将同一个 Web ACL 也与 ALB 关联。
   - C) 在任意区域使用 `--scope=CLOUDFRONT`，因为 CloudFront 是全局服务。

<details>
<summary>显示答案</summary>

**答案：A) 使用 `--scope=CLOUDFRONT --region=us-east-1`；此全局 Web ACL 不能同时与 ALB 关联。**

**说明**：用于 CloudFront 的 Web ACL 是全局的，其区域固定为美国东部（弗吉尼亚北部）；API 和 SDK 使用 `us-east-1` 端点。与 CloudFront 分配关联的 Web ACL 不能与其他类型的资源关联，因此，如果你还想对 ALB 进行一次检查，就需要为 ALB 单独创建一个 `REGIONAL` Web ACL。

</details>

9. 某个 Web ACL 使用了 `AWSManagedRulesCommonRuleSet`（700 WCU）、`AWSManagedRulesSQLiRuleSet`（200 WCU）、`AWSManagedRulesKnownBadInputsRuleSet`（200 WCU），以及一个创建时容量为 500 WCU、当前包含价值 120 WCU 规则的自定义规则组。结果是什么？
   - A) 1,220 WCU，未超过基础价格包含的额度。
   - B) 1,600 WCU：允许，因为上限为 5,000；但超过了基础价格包含的 1,500 WCU，因此会产生额外费用。
   - C) 拒绝，因为 Web ACL 不能超过 1,500 WCU。

<details>
<summary>显示答案</summary>

**答案：B) 1,600 WCU：允许，因为上限为 5,000；但超过了基础价格包含的 1,500 WCU，因此会产生额外费用。**

**说明**：在 Web ACL 中使用规则组时，计入的是创建时设定且不可更改的规则组容量，而不是该规则组当前包含的内容，因此自定义规则组按 500 WCU 计。700 + 200 + 200 + 500 = 1,600。基础价格包含 1,500 WCU；超出部分会按阶梯计收额外费用，最高上限为 5,000 WCU。

</details>

10. 某团队订阅了 Shield Advanced，并希望 Shield 响应团队在攻击期间主动联系他们。必须具备哪些条件？
   - A) 无需其他条件；订阅已包含此功能。
   - B) 每个 ALB 上都要有一个区域性 Web ACL。
   - C) 必须拥有 Business Support 或 Enterprise Support 计划才能使用 SRT，并且要为受保护资源配置基于运行状况的检测和 Route 53 运行状况检查。

<details>
<summary>显示答案</summary>

**答案：C) 必须拥有 Business Support 或 Enterprise Support 计划才能使用 SRT，并且要为受保护资源配置基于运行状况的检测和 Route 53 运行状况检查。**

**说明**：使用 SRT 需要上述其中一种支持计划。只有配置了基于运行状况的检测的资源才能获得主动联系，该检测使用 Route 53 运行状况检查。Shield Advanced 也只保护你明确添加的资源；Shield Standard 则是自动提供且无需付费的防护层。

</details>

11. 某团队提议使用公有 ALB 作为源站，并在其安全组中放行面向 CloudFront 源站的托管前缀列表。为什么本课程认为这比使用 VPC origin 指向内部 ALB 更弱？
   - A) 该前缀列表会放行任何 CloudFront 分配，包括攻击者创建的分配；而内部 ALB 完全没有通往互联网的路径。
   - B) 该前缀列表不包含 CloudFront 的 IPv4 地址。
   - C) 公有 ALB 不能使用 TLS。

<details>
<summary>显示答案</summary>

**答案：A) 该前缀列表会放行任何 CloudFront 分配，包括攻击者创建的分配；而内部 ALB 完全没有通往互联网的路径。**

**说明**：边缘控制只适用于经过你自己的分配的请求。来自其他分配的请求会绕过你的 Web ACL 和基于速率的规则。只有在机密标头仍然保密时，添加机密标头才有帮助。使用内部 ALB 实现的隐蔽性是一种路由属性，因此即使之后安全组配置得较宽松，源站仍然无法从互联网访问。

</details>

12. 在 Count 模式试运行期间，哪些证据能可靠表明托管规则组中的某条规则本来会匹配？
   - A) WAF 日志中的 `nonTerminatingMatchingRules` 字段和标签，以及标签指标。
   - B) Web ACL 视图中的采样请求表。
   - C) CloudFront 标准日志中的状态码。

<details>
<summary>显示答案</summary>

**答案：A) WAF 日志中的 `nonTerminatingMatchingRules` 字段和标签，以及标签指标。**

**说明**：WAF 日志会在 `nonTerminatingMatchingRules` 下列出 Count 匹配，并记录添加到每个请求的标签。Web ACL 视图不会显示规则组内 Count 规则的采样请求；规则组内执行 Count 操作的规则也不会产生 Web ACL 维度指标。Count 匹配绝不会改变状态码。

</details>

13. 在参考设计中，Pod 的 NetworkPolicy 使用包含 ALB 子网的 `ipBlock` 允许入站流量，而不是使用客户端地址。为什么？
   - A) ALB 是代理，因此 Pod IP 目标看到的是 ALB 节点的私有地址；客户端地址则通过 `X-Forwarded-For` 传递。
   - B) NetworkPolicy 无法表示 IPv4 CIDR 块。
   - C) CloudFront 只有在使用 HTTP/3 时才会将客户端地址改写为 VPC origin ENI 的地址。

<details>
<summary>显示答案</summary>

**答案：A) ALB 是代理，因此 Pod IP 目标看到的是 ALB 节点的私有地址；客户端地址则通过 `X-Forwarded-For` 传递。**

**说明**：ELB 指南指出，服务器访问日志中只包含负载均衡器的地址。Kubernetes 文档提醒，改写是在 NetworkPolicy 处理之前还是之后发生，取决于插件、云提供商和 Service 实现，因此请在自己的 CNI 上确认实际观测到的源地址。

</details>

14. 在练习册的练习中，`rate-login`（窗口 300 s、限制 100、按 IP 聚合、操作 Count）在安静了一小时后，看到 `198.51.100.20` 在 5 分钟内发送了一次孤立突发，共 640 个 `POST /login` 请求。该规则会统计来自此地址的大约多少个请求？为什么实际数量并不精确？
   - A) 640，因为 Count 会统计所有符合范围缩小语句条件的请求。
   - B) 大约 540，即超过限制的请求；数量是近似值，因为 AWS WAF 会估算速率，并且检测到超限需要一定时间。
   - C) 100，因为限制值会封顶计数。

<details>
<summary>显示答案</summary>

**答案：B) 大约 540，即超过限制的请求；数量是近似值，因为 AWS WAF 会估算速率，并且检测到超限需要一定时间。**

**说明**：对于超过限制的某个实例，基于速率的规则会对后续匹配请求执行其操作：640 - 100 = 540。以上计算适用于孤立的突发流量；如果该地址持续超过限制，之后几乎所有请求都会被计数，因为规则会持续生效，直到估算速率降到限制以下。AWS WAF 会对近期请求加权，因此限流值接近但不一定恰好等于配置值。试运行发现了一个误报（共享办公场所的 NAT），计划通过在范围缩小语句中的 `NotStatement` 内使用 IP 集来排除该地址。

</details>

完成要求：用练习册中的规则解释每个答案，并将你的规则计划标注为**已演练的场景，未经测量**。
