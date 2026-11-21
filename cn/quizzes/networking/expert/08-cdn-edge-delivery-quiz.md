# 08. CDN 与边缘交付设计测验

> **最后更新**：2026年11月19日

返回[工作簿](../../../networking/expert/08-cdn-edge-delivery.md)。
每题选择一个答案，并说明工作簿中的哪条规则支持你的选择。
这些是设计推理练习，并非声称已经构建了某个分配。

1. POP 缓存未命中时，在什么情况下 POP 会将请求**直接发送到源站**，而不是请求区域边缘缓存？
   - A) 对一张此前从未请求过的图片发起 `GET` 请求。
   - B) 对一个 API 路径发起 `POST` 请求。
   - C) 对一份已缓存但 TTL 已过期的样式表发起 `HEAD` 请求。

<details>
<summary>显示答案</summary>

**答案：B) 对一个 API 路径发起 `POST` 请求。**

**解释**：代理 HTTP 方法（`PUT`、`POST`、`PATCH`、`OPTIONS`、`DELETE`）会从 POP 直接发送到源站，不经过区域边缘缓存。动态请求，以及源站与最优区域边缘缓存位于同一区域的 S3 请求，也会跳过区域边缘缓存。首次发起的 `GET` 请求正是区域边缘缓存的用途。

</details>

2. 某个分配使用默认缓存键。两个查看者使用不同的查询字符串、`User-Agent` 值和 `session_id` Cookie 请求 `/content/stories/example-story.html`。第二个请求会发生什么？
   - A) 命中缓存，因为默认情况下，缓存键只包含分配域名和 URL 路径。
   - B) 未命中缓存，因为查询字符串不同。
   - C) 未命中缓存，因为 Cookie 总是缓存键的一部分。

<details>
<summary>显示答案</summary>

**答案：A) 命中缓存，因为默认情况下，缓存键只包含分配域名和 URL 路径。**

**解释**：查询字符串、标头和 Cookie 不包含在默认缓存键中。只有当它们会改变响应时，缓存策略才会将它们加入缓存键；源站请求策略则会将这些值转发到源站，但不会因此拆分缓存。

</details>

3. 源站发送 `Cache-Control: max-age=600, s-maxage=86400`。缓存策略的最小 TTL 为 0，最大 TTL 为 3600。CloudFront 会缓存对象多久？浏览器又会缓存多久？
   - A) CloudFront 缓存 600 秒，浏览器缓存 86,400 秒。
   - B) CloudFront 缓存 86,400 秒，浏览器缓存 600 秒。
   - C) CloudFront 缓存 3,600 秒，浏览器缓存 600 秒。

<details>
<summary>显示答案</summary>

**答案：C) CloudFront 缓存 3,600 秒，浏览器缓存 600 秒。**

**解释**：当两个指令同时存在且最小 TTL 为 0 时，CloudFront 的缓存时长取 `s-maxage` 与最大 TTL 中较短的那个值，而浏览器使用 `max-age`。RFC 9111 规定，共享缓存优先使用 `s-maxage`；但分配的最大 TTL 仍会限制缓存时长。

</details>

4. 缓存策略的最小 TTL 为 300 秒，而源站针对账户页面发送 `Cache-Control: no-cache`。CloudFront 会怎么做？如果源站无法访问，如何阻止它提供旧副本？
   - A) CloudFront 从不缓存 `no-cache` 响应，因此无需更改任何设置。
   - B) 尽管有 `no-cache`，CloudFront 仍会将对象缓存至最小 TTL 到期；如果源站无法访问，它也可能提供较早的副本。添加 `Cache-Control: stale-if-error=0` 可以阻止这种情况。
   - C) CloudFront 会按默认 TTL 缓存 24 小时。

<details>
<summary>显示答案</summary>

**答案：B) 尽管有 `no-cache`，CloudFront 仍会将对象缓存至最小 TTL 到期；如果源站无法访问，它也可能提供较早的副本。添加 `Cache-Control: stale-if-error=0` 可以阻止这种情况。**

**解释**：开发人员指南警告说，最小 TTL 大于 0 时会优先于 `no-cache`、`no-store` 和 `private`；并且当源站无法访问且最小 TTL 或最大 TTL 大于 0 时，CloudFront 会提供先前获取的对象。因此，仅降低最小 TTL 并不能阻止提供旧副本；`stale-if-error=0` 会让 CloudFront 返回错误。

</details>

5. 源站发送 `Cache-Control: max-age=3600, stale-while-revalidate=600`。对象缓存 65 分钟后收到请求时会发生什么？
   - A) CloudFront 立即提供旧副本，并在后台从源站获取新副本。
   - B) CloudFront 会阻止查看者继续等待，直到源站返回新副本。
   - C) CloudFront 返回 `504`，因为对象已过期。

<details>
<summary>显示答案</summary>

**答案：A) CloudFront 立即提供旧副本，并在后台从源站获取新副本。**

**解释**：一小时的有效期过后，`stale-while-revalidate=600` 允许 CloudFront 在异步重新验证期间最多提供旧副本 10 分钟（RFC 5861）。提供旧内容的时长不会超过该指令指定的时长与最大 TTL 中较短的那个值。

</details>

6. 一次不良发布之后，你使 `/app.js` 失效。一些使用企业代理的用户仍然获取旧文件。下次如何避免这种情况？
   - A) 使 `/*` 失效，而不是只使 `/app.js` 失效。
   - B) 将最小 TTL 降至 0。
   - C) 使用带版本号的文件名（例如 `app.3f9c.js`），并更新引用它们的页面。

<details>
<summary>显示答案</summary>

**答案：C) 使用带版本号的文件名（例如 `app.3f9c.js`），并更新引用它们的页面。**

**解释**：失效操作只会从 POP 和区域边缘缓存中移除对象；浏览器和企业代理缓存会一直保留旧副本，直到它们各自的缓存过期。新文件名会为每一层缓存生成新的缓存键。版本化也更省钱：无需支付失效费用，而 `/*` 路径仍只算一条失效路径。

</details>

7. 你使用 `curl -sI` 对同一资源连续请求两次。两次响应都显示 `x-cache: Miss from cloudfront`，而且 `x-amz-cf-pop` 的值不同。最可能的解释是什么？
   - A) 两个请求到达了不同的 POP，每个边缘位置只缓存自己接收过的对象。
   - B) 分配的缓存功能已损坏。
   - C) `HEAD` 请求从不缓存。

<details>
<summary>显示答案</summary>

**答案：A) 两个请求到达了不同的 POP，每个边缘位置只缓存自己接收过的对象。**

**解释**：DNS 和任播流量调度都不能保证连续请求到达同一个 POP。下结论前应先比较 `x-amz-cf-pop`；知识中心列出的其他原因还包括缓存淘汰、缓存键内容以及源站的 `Cache-Control`。

</details>

8. 某个响应显示 `x-cache: Hit from cloudfront`、`date: Thu, 19 Nov 2026 09:00:00 GMT` 和 `age: 7200`。你能得出什么结论？
   - A) 源站在两小时前生成了该响应，边缘节点提供了存储的副本；`date` 加上 `age` 大约就是当前时间，即 GMT 11:00。
   - B) 此请求联系了源站，源站用了 7,200 毫秒才作出响应。
   - C) 对象将在 7,200 秒后过期。

<details>
<summary>显示答案</summary>

**答案：A) 源站在两小时前生成了该响应，边缘节点提供了存储的副本；`date` 加上 `age` 大约就是当前时间，即 GMT 11:00。**

**解释**：RFC 9111 将 `Age` 定义为自源站生成或验证响应以来经过的秒数；该标头的存在意味着源站并未为此次请求生成响应。剩余的新鲜时间是有效期（取自 `s-maxage` 或 `max-age`，并受 TTL 设置限制）减去 `Age`，而不是 `Age` 本身。

</details>

9. 某个内部 ALB 是 CloudFront VPC 源站。开发人员指南提供的入站安全组来源中，哪一个**限制最严格**？
   - A) CloudFront 托管前缀列表 `com.amazonaws.global.cloudfront.origin-facing`。
   - B) 服务管理的安全组 `CloudFront-VPCOrigins-Service-SG`。
   - C) VPC CIDR。

<details>
<summary>显示答案</summary>

**答案：B) 服务管理的安全组 `CloudFront-VPCOrigins-Service-SG`。**

**解释**：托管前缀列表包含所有面向源站的 CloudFront 服务器，因此允许任意分配访问；VPC 源站服务安全组会将流量限制为发往你的分配，并且只有在创建 VPC 源站后才会存在。不要编辑该安全组，也不要创建名称前缀相同的安全组。VPC CIDR 根本不是 CloudFront 的来源。

</details>

10. 一个互联网客户端解析内部 ALB 的 DNS 名称并尝试连接。为什么即使还没评估任何安全组规则，连接也会失败？
   - A) 内部负载均衡器的 DNS 名称无法在 VPC 外部解析。
   - B) 内部负载均衡器的节点只有私有 IP 地址，因此互联网上没有路由能到达它们；该名称可以公开解析，但解析得到的是这些私有地址。
   - C) CloudFront 阻止了客户端。

<details>
<summary>显示答案</summary>

**答案：B) 内部负载均衡器的节点只有私有 IP 地址，因此互联网上没有路由能到达它们；该名称可以公开解析，但解析得到的是这些私有地址。**

**解释**：ELB 指南指出，内部负载均衡器的 DNS 名称可以公开解析为其节点的私有 IP，因此只有能够访问 VPC 的客户端才能连接到它。这是路由属性，所以即使之后放宽安全组规则，情况也不会改变。此客户端的请求路径中根本没有 CloudFront。

</details>

11. 审核人员反对 VPC 源站背后的 VPC 附加了互联网网关。下面哪项说法正确？
   - A) 互联网网关是必需的；它表示 VPC 可以接收互联网流量，但不会用于向源站路由，也无需更改路由表。
   - B) 互联网网关意味着源站子网必须改为公有子网。
   - C) 必须移除互联网网关，VPC 源站才能工作。

<details>
<summary>显示答案</summary>

**答案：A) 互联网网关是必需的；它表示 VPC 可以接收互联网流量，但不会用于向源站路由，也无需更改路由表。**

**解释**：CloudFront 通过私有子网中由服务管理的 ENI 访问源站。源站仍位于私有子网中，且没有公有地址；互联网网关只是 VPC 级别的前提条件。

</details>

12. 已启用 Origin Shield。在标准日志中，哪个字段和值可以表明请求由 Origin Shield 而非 POP 或区域缓存提供？
   - A) `x-edge-result-type` = `RefreshHit`。
   - B) `x-edge-detailed-result-type` = `OriginShieldHit`。
   - C) `x-edge-result-type` = `Miss`。

<details>
<summary>显示答案</summary>

**答案：B) `x-edge-detailed-result-type` = `OriginShieldHit`。**

**解释**：除 Origin Shield 命中等情况外，`x-edge-detailed-result-type` 与 `x-edge-result-type` 的值相同。若请求被路由到同时充当 Origin Shield 的区域边缘缓存，日志会记录为 `Hit`，而不是 `OriginShieldHit`。

</details>

完成要求：使用工作簿中的规则解释每个答案，并附上你的响应头观察结果，或将作业标注为**设计评审**。
