# 监控与性能测验

[课程](../../../networking/beginner/07-monitoring-performance.md)

共六道题。请用自己的话解释每道题的答案。

1. 一个 LISTEN 套接字显示 Recv-Q 为 3，Send-Q 为 128。这意味着什么？

   - A) 收到 3 个正文数据字节，发送了 128 个正文数据字节
   - B) 有 3 个连接等待 accept；accept backlog 最大为 128
   - C) 有 3 次重传，RTT 为 128ms
   - D) 当前有 128 个连接

<details>
<summary>显示答案</summary>

**答案：B) 有 3 个连接等待 accept；accept backlog 最大为 128**

**说明：**LISTEN 队列统计的是连接。它的单位与 ESTABLISHED 套接字上的流字节不同，因此应先检查状态。

</details>

2. 对 IP 地址执行 curl 请求时，time_namelookup 非常小。可以得出什么结论？

   - A) 组织 DNS 总是很快
   - B) 所有 DNS 缓存都为空
   - C) 此请求不适合用于验证 DNS 性能
   - D) 服务器处理耗时为零

<details>
<summary>显示答案</summary>

**答案：C) 此请求不适合用于验证 DNS 性能**

**说明：**IP 字面值不会测试服务名称的查询。另外，不要把累计计时字段当作彼此独立的时间间隔相加。

</details>

3. curl 成功，但 tcpdump 没有捕获到内容。首先应检查什么？

   - A) 选择的 NIC、过滤器和捕获时间窗口
   - B) 重置每台主机的所有路由表
   - C) 启用 SSH 密码登录
   - D) 增大最大 TCP 缓冲区

<details>
<summary>显示答案</summary>

**答案：A) 选择的 NIC、过滤器和捕获时间窗口**

**说明：**捕获结果取决于观察位置和条件。应使请求时间与捕获时间一致，并验证实验室中选择的 NIC。

</details>

4. 100 Mbit/s 和 100 MB/s 如何比较？

   - A) 两者总是相等
   - B) Mbit/s 的值大八倍
   - C) 仅对 HTTP 来说两者相等
   - D) 100 MB/s 相当于 800 Mbit/s

<details>
<summary>显示答案</summary>

**答案：D) 100 MB/s 相当于 800 Mbit/s**

**说明：**1 字节等于 8 比特。比较实际应用吞吐量时，还需考虑协议开销、观察点和执行条件。

</details>

5. 单次快照中的 Send-Q 大于零。下一步应怎么做？

   - A) 确认发生了网络丢包
   - B) 将每个缓冲区 sysctl 都加倍
   - C) 关联检查状态、时间变化、应用进度和数据包
   - D) 禁用远端防火墙

<details>
<summary>显示答案</summary>

**答案：C) 关联检查状态、时间变化、应用进度和数据包**

**说明：**Send-Q 可能同时包含未确认和未发送的字节。单个快照不足以确定原因。

</details>

6. 块 I/O 调度器与网络 qdisc 有什么区别？

   - A) 它们分别处理存储请求和网络发送队列
   - B) 两者都是 DNS 缓存
   - C) 两者都验证 SSH 密钥
   - D) 两者使用同一个 sysctl

<details>
<summary>显示答案</summary>

**答案：A) 它们分别处理存储请求和网络发送队列**

**说明：**应先定位瓶颈。它们都涉及调度，并不意味着它们控制相同资源或具有相同的调优效果。

</details>
