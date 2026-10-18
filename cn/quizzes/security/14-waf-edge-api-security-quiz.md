# WAF 与源站防护测验

> **最后更新**：2026 年 10 月 15 日

[阅读本章和一手资料](../../security/14-waf-edge-api-security.md)

### 1. 哪种 API Gateway 资源支持文档所述的直接 WAF 关联？

- A) REST API
- B) 所有 HTTP API
- C) 所有 WebSocket API
- D) 任意 NLB listener

<details>
<summary>显示答案</summary>

**答案：A) REST API**

**解释**：应使用受支持资源列表。在某个资源前部署 CloudFront 进行防护，与直接关联 WAF 是两种不同方式。

</details>

### 2. 较早执行的宽泛 Allow 规则匹配后会发生什么？

- A) 一定会继续评估后续规则
- B) 评估会终止，可能跳过后续防护规则
- C) 只有 Count 规则会终止评估
- D) 默认 Block 一定会覆盖它

<details>
<summary>显示答案</summary>

**答案：B) 评估会终止，可能跳过后续防护规则**

**解释**：Allow 和 Block 都会终止评估；Count 会继续。应检查规则优先级并将例外范围控制得足够窄。

</details>

### 3. 以下哪项正确比较了请求体检查上限？

- A) ALB 总是检查 64 KB
- B) 所有资源的限制都相同
- C) ALB 固定为 8 KB；CloudFront 默认为 16 KB，并可在受支持时提高到 64 KB
- D) 请求体检查上限等于应用上传上限

<details>
<summary>显示答案</summary>

**答案：C) ALB 固定为 8 KB；CloudFront 默认为 16 KB，并可在受支持时提高到 64 KB**

**解释**：检查大小与应用上传限制不同；AWS 文档也排除了对 gRPC 请求体的检查。

</details>

### 4. Oversize MATCH 是否总会阻止请求？

- A) 是，不受 action 影响
- B) 是，即使它位于 NOT 中也会阻止
- C) 是，即使之前已有 Allow 规则也会阻止
- D) 不会；它匹配的是语句，最终行为取决于 action 和组合逻辑

<details>
<summary>显示答案</summary>

**答案：D) 不会；它匹配的是语句，最终行为取决于 action 和组合逻辑**

**解释**：应检查 action、逻辑组合和更早终止评估的规则。MATCH 本身不是独立的 Block action。

</details>

### 5. 为什么仅凭 CloudFront 地址范围无法识别自己的 distribution？

- A) 其他 CloudFront 路径也可能使用相同基础设施
- B) CloudFront 不能使用 HTTPS
- C) ALB 没有 listener 规则
- D) 所有源站请求头都是密码学签名

<details>
<summary>显示答案</summary>

**答案：A) 其他 CloudFront 路径也可能使用相同基础设施**

**解释**：应将网络限制与受保护的源站请求头/listener 条件或受支持的 VPC origin 设计结合，并测试是否能绕过这些控制。

</details>

### 6. 如果请求头不存在，且外层没有 NOT，直接的 forwarded-IP 语句会怎样处理？

- A) 回退行为总会阻止请求
- B) 该语句不匹配；请求头缺失与格式错误时的回退行为不同
- C) 请求头会自动通过身份验证
- D) 总是使用最后一个地址

<details>
<summary>显示答案</summary>

**答案：B) 该语句不匹配；请求头缺失与格式错误时的回退行为不同**

**解释**：请求头缺失不会触发格式错误时的回退行为。外层的 NOT 可能会将不匹配结果反转为匹配。Geo/ASN/rate 使用第一个地址；IP set 则使用已配置的 FIRST/LAST/ANY 选择方式。

</details>

### 7. 关于 rate 规则，哪项说法正确？

- A) 它是精确的每秒配额
- B) 更改时间窗口会保留所有计数器
- C) 跟踪结果是近似值，相关设置变更会重置计数器
- D) 使用客户端可控的聚合键可以防止规避

<details>
<summary>显示答案</summary>

**答案：C) 跟踪结果是近似值，相关设置变更会重置计数器**

**解释**：应测试时间窗口、聚合方式、计数器重置、共享 NAT 和攻击者控制的键变化；业务配额应在应用中强制执行。

</details>

### 8. WAF 日志脱敏能自动保证什么？

- A) 所有采样请求都已脱敏
- B) 任何位置都不会出现敏感数据
- C) 不可能发生日志丢失
- D) 只保证已配置的日志字段处理；采样和数据保护仍需单独审查

<details>
<summary>显示答案</summary>

**答案：D) 只保证已配置的日志字段处理；采样和数据保护仍需单独审查**

**解释**：应检查实际采集的数据。日志脱敏不会自动保护请求采样或 Security Lake 数据采集。

</details>
