# Pod 网络基准测试测验

1. 使用 `ping -c 200 -i 0.05` 测量时，Pod 到 Pod 的平均 RTT 从同一节点 → 同一 AZ 中的不同节点 → 不同 AZ 是如何变化的？
   - A) 0.040 ms → 0.544 ms → 0.339 ms — 跨 AZ 比同一 AZ 更快
   - B) 三条路径都在约 0.3 ms 的噪声范围内
   - C) 0.040 ms → 0.339 ms → 0.544 ms — 离开节点增加 +0.30 ms，离开 AZ 再增加 +0.21 ms，形成阶梯
   - D) 0.040 ms → 0.339 ms → 5.4 ms — AZ 边界将 RTT 推高到整毫秒级别
<details>
<summary>显示答案</summary>

**答案：C) 0.040 ms → 0.339 ms → 0.544 ms — 离开节点增加 +0.30 ms，离开 AZ 再增加 +0.21 ms，形成阶梯**

**说明：**
ping 平均值（以 50 ms 间隔进行 200 次探测，0/200 丢包）分别为：同节点 0.040 ms、同一 AZ 0.339 ms、跨 AZ 0.544 ms。同一 AZ − 同节点 = +0.30 ms，跨 AZ − 同一 AZ = +0.21 ms，跨 AZ − 同节点 = +0.50 ms。fortio HTTP（100 qps、4 个连接、keepalive）p50 也呈现相同阶梯：0.259 → 0.461 → 0.704 ms（+0.20 / +0.24 ms），而 HTTP p50 − ping 平均值在每条路径上约为 0.22 / 0.12 / 0.16 ms — 即客户端+服务器用户空间协议栈。5.4 ms 的数值是 iperf3 运行中使单个流饱和时发送方的 TCP RTT（整形器中的排队），而非空闲状态的跨 AZ RTT（因此 D 错误）。作为尺度参考，本仓库的 Istio 对比页面显示一次 sidecar 跳转增加 +1.29 ms p50 — 一次 mesh 跳转的代价高于一次 AZ 跳转。

</details>

2. 单个 iperf3 TCP 流（`-P 1`）在同一 AZ 和跨 AZ 路径上均止步于 4.96 Gbps，而 8 个流（`-P 8`）在两条路径上均达到 9.94 Gbps。最能解释这两个数值的是？
   - A) 4.96 Gbps 是单个客户端 CPU 核心饱和；8 个流更快是因为它们使用了更多核心
   - B) 4.96 Gbps 是 EC2 文档说明的 5 Gbps 单流限制（在 cluster placement group 之外），9.94 Gbps 是 m5.xlarge “Up to 10 Gigabit” 实例峰值 — 要使用实例带宽，必须并行化流
   - C) 4.96 Gbps 是 m5.xlarge 的基线带宽，8 个流消耗 burst credits 才达到峰值
   - D) 单个流未启用巨型帧（MTU 9001）
<details>
<summary>显示答案</summary>

**答案：B) 4.96 Gbps 是 EC2 文档说明的 5 Gbps 单流限制（在 cluster placement group 之外），9.94 Gbps 是 m5.xlarge “Up to 10 Gigabit” 实例峰值 — 要使用实例带宽，必须并行化流**

**说明：**
不同节点上 Pod 之间的单个流在两条路径中完全相同 — 同一 AZ（cli→srv-a）为 4.96 Gbps，跨 AZ（cli→srv-b）也为 4.96 Gbps — 这正是 AWS 所述的 5 Gbps 单流限制。iperf3 报告这些运行期间客户端 CPU 仅为 19.5 % / 20.0 %（占一个核心），所以 CPU 并非限制因素（A 错误）；受 CPU 限制的情况是同节点单流达到 29.97 Gbps，客户端为 99.8 %。m5.xlarge 的基线带宽为 1.25 Gbps，峰值为 10 Gbps（C 错误）— 8 流的 9.94 Gbps 就是这一峰值。MSS 8949（MTU 9001）同样适用于每次运行（D 错误）。单个流被限制在上限时，发送方 TCP RTT 从空闲 ping RTT 的 0.34 ms（同一 AZ）/ 0.54 ms（跨 AZ）增至 5.6 ms / 5.4 ms，拥塞窗口约为 4.3 MB；一条流时重传数为 4 / 2，达到实例上限后 8 条流时则为 5,874 / 5,979 — 这是 ENA allowance shaping 的间接特征（未收集计数器本身）。在实践中，不同节点间 Pod 的一个 gRPC 流或一个 Kafka replica fetch 永远无法超过约 5 Gbps。

</details>

3. 8 流 iperf3 带宽在同一 AZ 和跨 AZ 中均为相同的 9.94 Gbps，但 fortio 的闭环最大值（`-qps 0`、16 个连接、20 s）从同一 AZ 的 38,507 qps 降至跨 AZ 的 25,602 qps。为什么？
   - A) 对于请求/响应流量，跨 AZ 链路将带宽减半
   - B) 跨 AZ 路径上的错误和重试增加了
   - C) 承载 srv-b 的节点 CPU 比 srv-a 节点的更慢
   - D) Little 定律 — 固定 16 个连接时，吞吐量 = 并发量 ÷ 延迟，因此 16 ÷ 0.000624 s ≈ 25,641 qps 是上限；AZ 跳转增加的大约 +0.2 ms 延迟使吞吐量降低 34 %。跨 AZ 的代价是延迟，而非带宽
<details>
<summary>显示答案</summary>

**答案：D) Little 定律 — 固定 16 个连接时，吞吐量 = 并发量 ÷ 延迟，因此 16 ÷ 0.000624 s ≈ 25,641 qps 是上限；AZ 跳转增加的大约 +0.2 ms 延迟使吞吐量降低 34 %。跨 AZ 的代价是延迟，而非带宽**

**说明：**
闭环平均延迟为同节点 0.355 ms、同一 AZ 0.415 ms、跨 AZ 0.624 ms，且 Little 定律适用于全部三条路径：16 ÷ 0.000355 = 45,070（实测 44,991），16 ÷ 0.000415 = 38,554（实测 38,507），16 ÷ 0.000624 = 25,641（实测 25,602）。每次运行均有 0 个错误（B 错误），响应体约为 75 字节，因此带宽无关紧要（A 错误）— 相同的 8 流测试显示两条路径均为 9.94 Gbps。srv-a 和 srv-b 运行在相同的 m5.xlarge 类型上（C 错误）。对于具有固定连接池的请求/响应 Service，AZ 跳转使吞吐量减少 34 %（38.5k → 25.6k qps），原因是延迟。注意，同节点 p99 1.695 ms / 最大值 13.593 ms 比同一 AZ（0.728 / 4.502 ms）更差，因为客户端和服务器共享一个节点的 4 个 vCPU — 这是 45k qps 下的 CPU 争用，而非网络问题。

</details>

4. 在相同的 100 qps / 4 个连接下，切换到 `-keepalive=false`（每个请求新建一个 TCP 连接）后，跨 AZ HTTP p50 如何变化？
   - A) 0.704 ms → 1.517 ms（+0.813 ms），超过翻倍 — 一个新连接大致需要一个 RTT 的 TCP 握手加上约 0.3 ms 的 socket 设置/拆除，因此路径 RTT 越长，惩罚越大
   - B) 没有变化 — 内核仍会复用连接
   - C) 0.704 ms → 0.813 ms，小幅增加
   - D) p50 未变；只有 p99 变差
<details>
<summary>显示答案</summary>

**答案：A) 0.704 ms → 1.517 ms（+0.813 ms），超过翻倍 — 一个新连接大致需要一个 RTT 的 TCP 握手加上约 0.3 ms 的 socket 设置/拆除，因此路径 RTT 越长，惩罚越大**

**说明：**
在 keepalive=false 时（30 s、3,000 个请求），p50 为同节点 0.664 ms（+0.405）、同一 AZ 1.079 ms（+0.618）、跨 AZ 1.517 ms（+0.813）：额外成本随路径 RTT 增长，约等于一个 RTT（TCP 握手）加上约 0.3 ms 的 socket 设置/拆除。将约 0.3 ms 加到跨 AZ ping 平均值 0.544 ms 上，大致接近实测的 +0.813 ms。0.813 ms 是增幅，不是新的 p50（C 错误），且 p50 本身增加了超过一倍（D 错误）。对于跨越 AZ 的 Service，保持连接池存活节省的延迟比 AZ 跳转本身的成本（+0.24 ms）还要多。

</details>

5. 持续 180 秒的运行（4 个流）跨越 AZ 边界传输了 223.4 GB。使用已验证的价格（`APN2-DataTransfer-Regional-Bytes`），这一次运行的成本是多少？
   - A) $0 — Region 内的流量免费
   - B) $2.23 — 每 GB $0.01，仅收费一次
   - C) 约 $4.47 — 每 GB $0.01 会同时在发送 AZ 的“out”和接收 AZ 的“in”收费，因此每个方向 $2.23，共 $4.47（实际为 $0.02/GB）
   - D) 最高至 1.25 Gbps 基线的流量免费；仅对超过它的 burst 收费
<details>
<summary>显示答案</summary>

**答案：C) 约 $4.47 — 每 GB $0.01 会同时在发送 AZ 的“out”和接收 AZ 的“in”收费，因此每个方向 $2.23，共 $4.47（实际为 $0.02/GB）**

**说明：**
`aws pricing get-products` 返回 usagetype `APN2-DataTransfer-Regional-Bytes`（“Regional Data Transfer - in/out/between AZs …”），价格为每 GB $0.0100。跨 AZ 传输会对离开每个 AZ 的数据收费，因此即使是同一账户内的单向大批量传输，也要对发送 AZ 的“out”支付 $0.01/GB，并对接收 AZ 的“in”支付 $0.01/GB — 实际为 $0.02/GB。该运行在 180 s 内以 9.93 Gbps 发送了 223,376,179,200 字节（223.4 GB），因此 223.4 × $0.01 = 每个方向 $2.23，共 $4.47。吞吐量测试中的全部跨 AZ 字节总计为 12.41 + 24.85 + 223.38 = 260.6 GB，约为 $5.21。该运行的 18 个时间区间稳定在 9.92–9.94 Gbps，没有向 1.25 Gbps 基线逐步下降，但无论带宽层级如何，账单都按字节计算（D 错误）。

</details>

6. 在默认 `ndots:5` Pod（glibc 2.41）中，对 `sts.ap-northeast-2.amazonaws.com`（3 个点）进行一次冷解析时，tcpdump 中产生了多少 DNS 查询和 NXDOMAIN 响应？
   - A) 2 次查询，0 个 NXDOMAIN — 有 3 个点时，该名称会立即作为绝对名称查询
   - B) 10 次查询，8 个 NXDOMAIN — 4 个搜索列表候选项各自的 A+AAAA 返回 8 个 NXDOMAIN，之后第 5 个候选项（绝对名称）获得 A 响应
   - C) 5 次查询，4 个 NXDOMAIN — 每个候选项一个 A 查询
   - D) 4 次查询，2 个 NXDOMAIN
<details>
<summary>显示答案</summary>

**答案：B) 10 次查询，8 个 NXDOMAIN — 4 个搜索列表候选项各自的 A+AAAA 返回 8 个 NXDOMAIN，之后第 5 个候选项（绝对名称）获得 A 响应**

**说明：**
一个 EKS Pod 的 resolv.conf 包含 `search bench-net.svc.cluster.local svc.cluster.local cluster.local ap-northeast-2.compute.internal` 和 `options ndots:5`。点数少于 5 的名称会先依次尝试 4 个搜索后缀，glibc 会为每个候选项并行发送 A 和 AAAA（C 错误）。抓包显示 `….bench-net.svc.cluster.local.` → `….svc.cluster.local.` → `….cluster.local.`（这三个均是来自 CoreDNS kubernetes plugin 的权威 NXDomain）→ `….ap-northeast-2.compute.internal.`（转发至 VPC resolver，NXDomain）→ 最后 `sts.ap-northeast-2.amazonaws.com.` 获得 A 响应 10.0.3.84 / 10.0.2.129：10 次查询、8 个 NXDOMAIN、5 次顺序往返，从第一个数据包起计 4.37 ms，有效响应在最后 0.38 ms 到达。20 次重复的热缓存中位数仍为 3.78 ms，而带尾点的形式 `sts.ap-northeast-2.amazonaws.com.` 仅需 2 次查询，中位数为 0.80 ms。CoreDNS `cache 30` 也会缓存 NXDOMAIN，因此热缓存成本是 5 次顺序的 Pod↔CoreDNS 往返本身，而非上游查询。推导计算：一个应用程序若在集群范围内以每秒 1,000 次解析为每个请求解析一个外部名称，则会向 CoreDNS 发送每秒 10,000 次查询，而非 2,000 次，其中 8,000 次得到 NXDOMAIN。4 次查询 / 2 个 NXDOMAIN 是 `kubernetes.default`（1 个点）的结果，不是此名称的结果（D 错误）。

</details>

7. 在同一个 `ndots:5` Pod 中，看似 FQDN 的 `kubernetes.default.svc.cluster.local`（无尾点）也产生了 10 次查询和 8 个 NXDOMAIN。它为什么遍历了整个搜索列表？
   - A) CoreDNS 的 `kubernetes` plugin 仅会立即响应 `cluster.local` 区域之外的名称
   - B) glibc 始终将以 `svc.cluster.local` 结尾的名称视为 Service 名称
   - C) `.ap-northeast-2.compute.internal` 后缀在搜索列表中排第一位，因此先被尝试
   - D) 该名称仅有 4 个点，少于 ndots 5，因此 glibc 将其视为“短”名称：会附加并尝试全部 4 个搜索后缀，之后才按原样发送该名称 — 加上尾点后只需 2 次查询
<details>
<summary>显示答案</summary>

**答案：D) 该名称仅有 4 个点，少于 ndots 5，因此 glibc 将其视为“短”名称：会附加并尝试全部 4 个搜索后缀，之后才按原样发送该名称 — 加上尾点后只需 2 次查询**

**说明：**
`kubernetes.default.svc.cluster.local` 包含 4 个点，低于 ndots 5。因此 glibc 会先尝试 `….bench-net.svc.cluster.local`、`….svc.cluster.local`、`….cluster.local` 和 `….ap-northeast-2.compute.internal`，收集 8 个 NXDOMAIN（仅 compute.internal 候选项便因 CoreDNS 将其转发至上游而耗时 2.2 ms），之后第 5 个候选项 — 原始名称 — 获得 A 响应：冷遍历耗时 5.6 ms，热缓存中位数为 3.63 ms。带一个尾点的相同名称 `kubernetes.default.svc.cluster.local.` 会产生 2 次查询和 0 个 NXDOMAIN — 冷缓存为 0.4–0.5 ms，热缓存中位数为 0.46 ms。在 `ndots:1` Pod 中，无尾点形式也是 2 次查询（中位数 0.97 ms）。搜索列表依次为 namespace domain → `svc.cluster.local` → `cluster.local` → node domain，因此 C 错误，A 和 B 也未正确描述 glibc 或 CoreDNS 的行为。当将 Service FQDN 写入配置文件时，写入尾点是安全的选择。

</details>

8. 在通过 `dnsConfig.options` 配置 `ndots:1` 的 Pod 中，外部名称的查询次数从 10 次降为 2 次，但短的集群内名称 `kubernetes.default` 变得更差（6 次查询、4 个 NXDOMAIN，中位数 2.04 ms，而在 ndots:5 下为 1.71 ms）。发生了什么？
   - A) 由于 1 个点 ≥ ndots 1，glibc 首先将 `kubernetes.default.` 作为绝对名称发送；CoreDNS 没有其对应区域，因此将其转发至 VPC resolver（NXDomain），之后才遍历搜索列表，以 `svc.cluster.local` 候选项获得响应 — 集群内部名称泄漏至上游 resolver
   - B) ndots:1 禁用了 CoreDNS 缓存
   - C) `kubernetes.default` 在 ndots:1 下根本无法解析
   - D) glibc 会顺序发送 A 和 AAAA，使时间翻倍
<details>
<summary>显示答案</summary>

**答案：A) 由于 1 个点 ≥ ndots 1，glibc 首先将 `kubernetes.default.` 作为绝对名称发送；CoreDNS 没有其对应区域，因此将其转发至 VPC resolver（NXDomain），之后才遍历搜索列表，以 `svc.cluster.local` 候选项获得响应 — 集群内部名称泄漏至上游 resolver**

**说明：**
在 ndots:1 Pod 中，`kubernetes.default`（1 个点）首先以绝对名称 `kubernetes.default.` 发出；CoreDNS 没有其对应区域，将其转发至 VPC resolver，并在 1.6 ms 后收到 NXDomain。之后是 `kubernetes.default.bench-net.svc.cluster.local`（NXDOMAIN），最后 `kubernetes.default.svc.cluster.local` 获得响应 172.20.0.1 — 6 次查询、4 个 NXDOMAIN、热缓存中位数 2.04 ms，差于 ndots:5 下的 4 次查询 / 2 个 NXDOMAIN / 1.71 ms（C 错误）。相对而言，外部名称收益很大：`sts.ap-northeast-2.amazonaws.com` 和 `www.amazon.com` 的查询次数从 10 次降至 2 次，中位数从 3.5–3.8 ms 降至 0.5–0.9 ms（约快 4–7 倍，查询数少 5 倍）。glibc 默认并行发送 A 和 AAAA（D 错误），CoreDNS 缓存与 Pod 的 ndots 无关（B 错误）。若使用 ndots:1，请将集群内 Service 写为 `service.namespace.svc.cluster.local` 形式的 FQDN；无论 ndots 如何，带尾点的形式均有效 — 始终为 2 次查询和约 0.4–0.8 ms。

</details>

9. 页面上的每个 fortio 延迟表都来自使用 `-r 0.00001`（10 µs 直方图分辨率）重新运行的结果。为什么舍弃了第一次运行？
   - A) 第一次运行的错误率很高
   - B) fortio 默认的 `-r 0.001` 表示 1 ms 桶，因此每个亚毫秒响应都会落入单个桶中，百分位数是在桶内进行线性插值得到的（例如，对所有低于 1 ms 的值 p50 = 0.5 ms）— 平均值有效，百分位数则毫无意义
   - C) 在默认分辨率下 fortio 不计算 p99.9
   - D) 第一次运行意外地未使用 keepalive
<details>
<summary>显示答案</summary>

**答案：B) fortio 默认的 `-r 0.001` 表示 1 ms 桶，因此每个亚毫秒响应都会落入单个桶中，百分位数是在桶内进行线性插值得到的（例如，对所有低于 1 ms 的值 p50 = 0.5 ms）— 平均值有效，百分位数则毫无意义**

**说明：**
此基准测试中的真实 p50 值均低于 1 ms — keepalive HTTP 为 0.259–0.704 ms。使用 fortio 默认的 `-r 0.001` 时，直方图桶为 1 ms，因此所有这些样本都堆积在第一个桶内，百分位数在桶内线性插值，从而产生不真实的数值，例如无论路径如何 p50 = 0.5 ms。平均值有效，但百分位数被舍弃，所有 fortio 运行均使用 `-r 0.00001`（10 µs 桶）重做。每次运行均有 0 个错误（A 错误），请求/响应设置未变（D 错误）。教训是：在测量亚毫秒网络之前，先检查工具的直方图分辨率。

</details>

10. 哪项陈述正确描述了为什么该页面没有测量 ClusterIP（kube-proxy iptables）跳转或 `trafficDistribution: PreferClose`？
   - A) fortio 无法以 Service DNS 名称为目标
   - B) kube-proxy 处于 IPVS 模式，因此没有可测量的 iptables 跳转
   - C) 集群的 aws-load-balancer-controller webhook（`mservice.elbv2.k8s.aws`，`failurePolicy: Fail`）拦截每个 Service CREATE，但 controller Pod 因等待 Gateway API `ListenerSet` CRD 已处于 CrashLoopBackOff 48 天，因此 webhook 的 endpoints 为零，集群中任何位置都无法创建 Service — 未绕过该 webhook，fixture 仅使用 Pod IP
   - D) 已测量，但因为它与 Pod-IP 数值相同而未放入表格
<details>
<summary>显示答案</summary>

**答案：C) 集群的 aws-load-balancer-controller webhook（`mservice.elbv2.k8s.aws`，`failurePolicy: Fail`）拦截每个 Service CREATE，但 controller Pod 因等待 Gateway API `ListenerSet` CRD 已处于 CrashLoopBackOff 48 天，因此 webhook 的 endpoints 为零，集群中任何位置都无法创建 Service — 未绕过该 webhook，fixture 仅使用 Pod IP**

**说明：**
基准测试 namespace 中每次对 Service 的 `kubectl apply` 都被拒绝，并显示 `Internal error occurred: failed calling webhook "mservice.elbv2.k8s.aws": … no endpoints available for service "aws-load-balancer-webhook-service"`。只读诊断发现 aws-load-balancer-controller v3.2.1（kube-system、2 个副本）已处于 CrashLoopBackOff 48 天，重启 9,250 次：每个容器重复记录 `no matches for kind "ListenerSet" in version "gateway.networking.k8s.io/v1"`，并在约 2m18s 的 cache-sync 超时后退出。其 `MutatingWebhookConfiguration` `aws-load-balancer-webhook` 以 `failurePolicy: Fail` 匹配集群范围内每一个 Service 的 CREATE（`namespaceSelector: {}`），因此在没有就绪 endpoints 时，任何 namespace 都无法创建 Service。与其绕过 webhook 或修复 controller，fixture 仅使用 Pod IP，这就是页面没有 ClusterIP 跳转或 `PreferClose`（Kubernetes 1.31 中 beta，1.33 中 GA）数值的原因（D 错误）。kube-proxy 处于 `mode: "iptables"`（B 错误）。同样未收集：ENA allowance 计数器（`ethtool -S`，需要 hostNetwork Pod）；并且每个单元格均是单日的 n = 1，因此这些数值是数量级参考，而非 SLA。

</details>

---

[返回学习材料](../../networking/06-pod-network-benchmark.md) | [返回网络首页](../../networking/README.md)
