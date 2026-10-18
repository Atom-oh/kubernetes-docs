# Linux 网络诊断：HTTP、TCP 队列、路由与 MTU

> **支持环境**：Linux、Python 3.9+、curl 和 iproute2；路由练习需要本地 Docker Engine
> **最后更新**：2026 年 9 月 15 日

从 Linux 上的一个请求开始，找出套接字和下一跳，然后说明同一个数据包如何经过容器网络命名空间。这些练习帮助你在调查 Kubernetes 或 AWS 网络之前，区分应用层、传输层和路由层的证据。

如果你想先练习 CLI、IP 配置、DNS、SSH 和防火墙，请先完成[八节初学者课程](beginner/README.md)。本指南随后会深入观察套接字、ICMP 和 PMTU。

练习时请同时阅读 [IPv4 与下一跳基础](../basics/06-network-fundamentals-part1.md#ipv4-cidr-subnet)和 [HTTP 消息结构](../basics/06-network-fundamentals-part3.md#http11-message-structure)。

- [HTTP 消息](#http-message-lab)
- [TCP 队列与缓冲区](#tcp-buffer-lab)
- [路由与 ICMP](#routing-icmp-lab)
- [MTU、PMTU 与 MSS](#mtu-mss-lab)
- [Docker 数据包路径](#docker-packet-path)

## 范围与准备 {#lab-scope}

在本仓库的一个检出目录中运行命令。文中指出时，请使用不同的终端。

| 练习 | 要求 | 范围 |
|---|---|---|
| HTTP | Python 3.9+、curl | 在 `127.0.0.1:18080` 上运行一个服务器，并自动停止 |
| TCP 观察 | HTTP 服务器、Python、iproute2 中的 `ss` | 只读观察本地测试端口 |
| 路由与 MTU | Linux Docker Engine、Docker CLI、主机 iproute2、已拉取的镜像 | 三个临时容器和两个专用 bridge |

辅助程序是 [http_lab.py](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/networking/foundations/http_lab.py) 和 [routing_lab.py](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/networking/foundations/routing_lab.py)。运行前先阅读它们的约定和 [examples README](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/networking/foundations/README.md)。

命令说明操作步骤；HTTP 响应摘录是**示例**。明确标注的路由摘录来自记录的参考运行，并非你的机器。请根据所列标准和路由辅助程序的 JSON 记录判断自己的运行结果。

HTTP 辅助程序是用于教学的小型 HTTP/1.1 服务器，并非生产服务器，也不是完整的 RFC 实现。它最多接受 4096 字节请求正文，并且只支持 `Content-Length` 消息定界；它会拒绝传输编码。

路由辅助程序只使用 `unix:///var/run/docker.sock`，并忽略指向远程 Docker 主机/上下文的环境设置。它需要本地 Linux Engine 和该套接字的访问权限；远程上下文或位置不同的 rootless 套接字不能替代它。

其 `IMAGE` 常量固定使用以下参考镜像，该镜像必须已经存在于该 Engine 中：

```text
nicolaka/netshoot:v0.16@sha256:b09d9b21381f47a79b3cbcb30da25266dc17186ea00ae65e99fdc51396f48e70
```

辅助程序不会拉取镜像。创建资源前，它会将固定子网与可见的主机 IPv4 路由和现有 Docker 网络网段进行检查。一次只运行一个路由练习；遇到冲突时应停止，不要更改共享主机路由。

## 练习 1：读取 HTTP 消息 {#http-message-lab}

**目的**：区分请求/状态行、字段、标头终止符和内容字节。

在终端 A 中启动服务器：

```bash
python3 examples/networking/foundations/http_lab.py --port 18080 --duration 120
```

服务器只绑定到 `127.0.0.1`，并在 120 秒后退出；允许的最长运行时间为 600 秒。如果端口已被占用，请换用另一个空闲的本地端口，并在命令和过滤器中始终使用该端口。不要停止无关的侦听进程。

在终端 B 中发送 GET 和 HEAD 请求：

```bash
curl --disable --noproxy '*' --max-time 5 --http1.1 -i http://127.0.0.1:18080/lesson
curl --disable --noproxy '*' --max-time 5 --http1.1 -I http://127.0.0.1:18080/lesson
```

作为第一个选项的 `--disable` 会跳过 curl 的默认配置；`--noproxy '*'` 可避开已配置的代理。`-i` 会包含响应标头；`-I` 发送的是 HEAD，而不是隐藏正文的普通 GET。

下面是一个 GET 响应摘录示例；省略了动态生成的 `Date` 和 `Server` 字段：

```http
HTTP/1.1 200 OK
Content-Type: text/plain; charset=utf-8
Content-Length: 6

hello
```

实际正文为 `b"hello\n"`：十六进制字节是 `68 65 6c 6c 6f 0a`。末尾 LF 是第六个字节。HTTP/1.1 在线路上传输时，标头行和标头/正文分隔符使用 CRLF；本文的 Markdown 展示使用 LF。

现在将相同的六个字节发送到 echo 端点：

```bash
printf 'hello\n' | curl --disable --noproxy '*' --max-time 5 --http1.1 -i \
  -H 'Content-Type: text/plain' --data-binary @- \
  http://127.0.0.1:18080/echo
```

`--data-binary @-` 会从标准输入读取内容且不移除 LF，并选择 POST。辅助程序会原样返回这些字节，并设置 `Content-Type: application/octet-stream`；它不会解析文本、JSON 或表单。

| 观察项 | 预期标准 | 解释 |
|---|---|---|
| GET `/lesson` | HTTP/1.1 200，长度为 6，六个内容字节 | 长度不包括起始行和标头 |
| HEAD `/lesson` | HTTP/1.1 200，长度为 6，没有响应正文 | 此字段描述对应 GET 表示的长度 |
| POST `/echo` | HTTP/1.1 200，长度为 6，`hello` 和 LF 保持不变 | 字节保留与媒体类型解析是两回事 |

一个非 ASCII 字符可能占用多个 UTF-8 字节。请统计实际发送的编码字节，包括真正的换行符，而不要按可见字符计数。

查看客户端调试跟踪中的请求行和发出的字段：

```bash
curl --disable --noproxy '*' --max-time 5 --http1.1 --trace-ascii - \
  --output /dev/null http://127.0.0.1:18080/lesson
```

这是 **curl 客户端侧的调试输出**，不是抓包。它的注释不是线路字节、TCP 分段边界，也不能证明路由器看到的内容。收集跟踪时只使用演示数据。

使用 HTTPS 时，客户端可以显示 HTTP 明文，但被动网络抓包若没有会话密钥就无法读取。HTTP/2 和 HTTP/3 也采用不同的二进制分帧；工具中可读的输出并非它们的原始编码。

**清理**：在终端 A 中按 Ctrl+C 停止服务器，或等待计时器到期。它不会创建持久应用数据。计时器到期后，可为下一项练习重新启动服务器。

## 练习 2：观察 TCP 队列与缓冲区 {#tcp-buffer-lab}

**目的**：将一个持久连接与套接字状态、数据流队列和内存记账关联起来。

在终端 A 中启动同一个 120 秒服务器。在终端 B 中运行这个有界客户端：

```bash
python3 - <<'PY'
import http.client
import time

connection = http.client.HTTPConnection("127.0.0.1", 18080, timeout=2)
try:
    for number in range(30):
        connection.request("GET", "/lesson")
        response = connection.getresponse()
        body = response.read()
        assert response.status == 200
        assert response.getheader("Content-Length") == "6"
        assert body == b"hello\n"
        if number == 0:
            print("Client endpoint:", connection.sock.getsockname(), flush=True)
        time.sleep(1)
finally:
    connection.close()
PY
```

客户端会在复用连接前读取每个响应。它每隔一秒发送 30 个小型 GET 请求，因此相比多个短暂的 curl 进程，更容易观察已建立的套接字。

客户端运行期间，在终端 C 中执行：

```bash
ss -ltn 'sport = :18080'
ss -tinm state established '( sport = :18080 or dport = :18080 )'
```

多次重复第二条命令。这些命令检查当前网络命名空间，并筛选测试端口。这个 loopback 连接的两个本地端都可能出现；请区分服务器端口和客户端临时端口。

**预期标准：**`127.0.0.1:18080` 上存在侦听套接字，而且客户端运行时可以看到一个已建立连接。队列、RTT 和内存的具体数值会变化；这种小负载下队列为零很正常。

| 字段/状态 | 含义 |
|---|---|
| ESTABLISHED `Recv-Q` | 应用尚未读取的、按序接收的字节 |
| ESTABLISHED `Send-Q` | 尚未确认的数据流字节，包括尚未发送的字节 |
| LISTEN `Recv-Q` | 排队等待 `accept()` 的连接数，不是负载字节 |
| LISTEN `Send-Q` | 最大 accept backlog，不是发送缓冲区大小 |
| `skmem` `r` / `rb` | 接收内存记账 / 接收内存预算 |
| `skmem` `w` / `tb` | 排队的发送内存 / 发送内存预算 |
| `rtt`、`mss`、`cwnd` | RTT、TCP 数据大小和拥塞窗口信息；`cwnd` 通常以分段数表示 |

套接字内存包含记账开销，不必等于数据流队列列出的数值。侦听队列也不同于未完成的 SYN 队列。[ss(8) 手册](https://man7.org/linux/man-pages/man8/ss.8.html)介绍了这些字段。

只读取当前缓冲区策略，不要更改它：

```bash
sysctl net.ipv4.tcp_rmem net.ipv4.tcp_wmem net.ipv4.tcp_moderate_rcvbuf
```

`tcp_*mem` 三元组描述最小值/默认值/自动调优上限，而不是每个套接字当前占用量。接收缓冲区自动调优和应用设置的套接字选项会影响结果；缓冲区预算既不是通告的接收窗口，也不是 `cwnd`。

接收队列增长时，应调查应用读取是否及时；发送队列持续增长时，应结合应用、确认和路径证据调查。单次快照或更大的缓冲区都不能证明吞吐量有所提升。

这个六字节工作负载用于观察正常运行；它不会刻意制造背压，也不会测量最大吞吐量。在提出调优更改前，请先阅读[套接字与缓冲区的分析方法](../kernel/02-network-stack.md#tcp-buffer-policy)。

**清理**：客户端会在 30 次迭代后关闭连接，中断时则通过 `finally` 关闭。请在终端 A 中停止服务器或等待计时器到期。不需要撤销任何 sysctl 更改。

## 练习 3：跟踪路由与 ICMP {#routing-icmp-lab}

**目的**：证明所选下一跳，区分名称查询与转发，并将受 TTL 限制的探测与 ICMP 响应对应起来。

路由辅助程序会构建以下临时拓扑：

```text
client namespace          router namespace                 server namespace
192.0.2.2/29 --- left --- 192.0.2.3/29
                          198.51.100.2/29 --- right --- 198.51.100.3/29
left bridge: 192.0.2.0/29             right bridge: 198.51.100.0/29
```

两个专用 bridge 都设置了 `com.docker.network.bridge.enable_ip_masquerade=false`。在添加明确的实验路由前，辅助程序会从三个容器中**移除所有 IPv4 默认路由**，但保留直连路由。

容器会删除所有 capabilities，然后只添加 `NET_ADMIN` 和 `NET_RAW`；路由器命名空间内会启用转发。辅助程序不使用特权容器或 host 网络、不发布端口，也不会创建 AWS 资源。

Docker 会创建主机 bridge 并管理其常规网络规则。辅助程序不会手动更改主机路由、sysctl 或 iptables 规则；但这不代表主机完全未受影响，也不构成网络隔离证明。

它会为客户端添加一条经 `192.0.2.3` 到 `198.51.100.0/29` 的路由，并为服务器添加一条经 `198.51.100.2` 返回 `192.0.2.0/29` 的路由。

选择一个尚不存在的输出路径：

```bash
python3 examples/networking/foundations/routing_lab.py \
  --output ./routing-observation-01.json
```

辅助程序拒绝覆盖现有文件。**这一次调用也会执行下面的 MTU 练习**；不要为该部分再并发启动第二次运行。

下面列出辅助程序在**客户端命名空间**中执行的命令，供理解用途，不是要求你在主机 Shell 中直接执行：

```text
ip -j route get 198.51.100.3
ip -j neigh show to 192.0.2.3
ip -j neigh show to 198.51.100.3
ping -n -c 1 -W 1 -t 1 198.51.100.3
traceroute -n -I -m 4 -q 1 -w 1 198.51.100.3
```

它还会使用 Docker DNS 解析生成的路由器容器名称。目标名称会随本次运行所用前缀变化；DNS 返回结果本身并不是可达性测试。

| JSON 观察项 | 预期标准 | 解释 |
|---|---|---|
| `defaultRoutes` | 客户端、路由器和服务器的列表都为空 | 三个容器都不保留 IPv4 默认路由 |
| `route` | 网关为 `192.0.2.3`，源地址为 `192.0.2.2` | 通过路由器到达目标 |
| `dns` | 路由器名称在左侧网络中解析为 `192.0.2.3` | Docker 名称查询正常 |
| `nextHopNeighbor` | 存在 `192.0.2.3` 的 MAC 地址 | ARP 已解析下一跳 |
| `remoteNeighbor` | 为空 | 远程服务器不是客户端的以太网邻居 |
| `ttlOne` | 探测失败；抓包包含 ICMP Time Exceeded | TTL 按预期在路由器处过期 |
| `traceroute` | 第一跳是 `192.0.2.3`，目标是 `198.51.100.3` | 使用 ICMP 探测的跟踪经过两个 IP 跳点 |

针对 `ttlOne`，辅助程序会在路由器命名空间中启动实际的 `tcpdump`，使用过滤器 `icmp[0] == 11`，等待抓包就绪后再发送 TTL 为 1 的 ping。预期的响应是 IPv4 ICMP Type 11 Code 0，其中会引用原始探测。

如果抓包匹配，这里的 ping 失败就是一次成功的诊断触发。探测发送的是 ICMP Echo；Time Exceeded 则是单独返回的消息。

`traceroute -I` 使用 ICMP Echo 探测。UDP 和 TCP 方法可能遇到不同的过滤行为，也会收到不同的目标端响应。`*` 只表示等待期间没有匹配响应，本身不能证明端到端丢包。RTT 包含响应返回路径的时间。

辅助程序结束后检查你的证据文件：

```bash
python3 - <<'PY'
import json
from pathlib import Path

record = json.loads(Path("routing-observation-01.json").read_text())
print("Status:", record["status"])
print("Checks:", record.get("checks", {}))
print("Cleanup:", record.get("cleanup", "not reported"))
PY
```

**成功标准**：辅助程序成功退出，并记录 `status: passed`；八项命名检查全部为 true，且已报告清理结果。仅有路由和 DNS 成功，不能替代失败的数据包观测项。

**清理**：正常完成、观测失败或处理过的中断发生时，辅助程序都会尝试移除其创建的容器 ID 和网络 ID。清理出错即为运行失败。强制终止可能会阻止清理；应使用已记录的 ID 识别残留资源，绝不要对共享 Docker 资源执行宽泛的 prune。解释下一节前请保留 JSON。

### 记录的参考运行 {#routing-reference-run}

2026 年 9 月 14 日的运行见[示例验证记录](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/networking/foundations/README.md#validation)，在 Linux Docker Engine 25.0.16 上通过：八项检查全部通过，三个默认路由列表均为空，创建的 ID 也已移除。Traceroute 观测到 `192.0.2.3`，随后到达 `198.51.100.3`。

测得的 TTL 错误数据包详情如下，已省略时间戳和接口前缀：

```text
IP 192.0.2.3 > 192.0.2.2: ICMP time exceeded in-transit, length 92
```

这是该环境中的功能证据，不保证其他主机上的时间、接口名称、MAC 地址或兼容性相同。

## 练习 4：区分 MTU、PMTU 与 MSS {#mtu-mss-lab}

**目的**：利用实际 ICMP 错误解释与大小相关的失败，避免将 ICMP 负载大小误认为 TCP MSS。

使用相同的路由调用和 JSON 记录。辅助程序通过路由查询找出路由器上通往服务器的接口，然后将**该容器接口的 MTU 设为 1280**。它不会假设出口接口名为 `eth1`。

针对第一个客户端探测，辅助程序会在路由器处捕获 `icmp[0] == 3 and icmp[1] == 4`，然后发送较小的探测：

```text
ping -n -c 1 -W 1 -M do -s 1372 198.51.100.3
ping -n -c 1 -W 1 -M do -s 1200 198.51.100.3
```

`-M do` 会请求 IPv4 Don't Fragment 行为。这里使用的常见 IPv4 标头为 20 字节、ICMP 标头为 8 字节：

| 探测 | IP 数据包大小 | 预期标准 |
|---|---|---|
| 1372 字节 ICMP 数据 | `1372 + 8 + 20 = 1400` 字节 | 超过 1280 字节的出口 MTU；探测失败并捕获到 ICMP Type 3 Code 4 |
| 1200 字节 ICMP 数据 | `1200 + 8 + 20 = 1228` 字节 | 符合该出口 MTU；Echo Reply 成功 |

检查 `pmtu.probeOutput`、`pmtu.capture`、`smallerPacket` 和 `routeAfterFeedback`。关键证据是**收到 Fragmentation Needed 反馈，且较小数据包探测成功**，而不是某个特定 RTT 或精确的输出文字。

同一次记录运行得到如下测量 ping 行：

```text
From 192.0.2.3 icmp_seq=1 Frag needed and DF set (mtu = 1280)
```

它的 1200 字节数据探测收到了响应，`routeAfterFeedback` 报告 MTU 为 1280。这些是该次运行的观测结果，不是固定的时间或缓存过期保证。

收到反馈后，Linux 可能会缓存目标 PMTU。之后发送过大的数据包时，可能会在本地收到“message too long”错误，而不会再次到达路由器。`routeAfterFeedback` 可能会显示学到的 MTU 信息；字段和过期行为会变化。

辅助程序的抓包对应于它在临时客户端命名空间中刻意触发的首次失败。仅仅没有捕获到后续 ICMP 消息，并不会推翻之前收到的反馈。

**MSS 不同**：它限制 TCP 数据字节数。对于以太网 MTU 1500 和基本 IPv4/TCP 标头，`1500 − 20 − 20 = 1460` 是基本 MSS 计算结果。IP/TCP 选项和路径条件可能减少每个数据包中实际承载的数据。

上面的 1372 和 1200 是 ICMP 数据大小，**并非实测 MSS 值**。loopback TCP 练习也未必会显示 MSS 1460：loopback 有自己的 MTU 和内核行为。

TSO/GSO/GRO 和校验和卸载可能使主机抓包不同于物理链路上的数据包。在把大型捕获单元或表面上的校验和错误视为线路故障前，请先检查接口、命名空间和观测位置。

IPv6 路由器不会分片转发的数据包，而是使用 ICMPv6 Packet Too Big。传统 PMTUD 与分组层探测依赖不同的反馈；请参阅 [ICMP 基础](../basics/06-network-fundamentals-part1.md#icmp-traceroute-interpretation)。

**清理**：路由辅助程序会连同其他创建的 ID 一起移除临时路由器及其 MTU 更改。主机物理接口的 MTU 不会被更改。分析后，只保留或删除你自己的证据文件。

## 解释 Docker 数据包路径 {#docker-packet-path}

**目的**：将观测结果与 Linux 命名空间、虚拟以太网链路和路由查询联系起来。

使用已有的路由记录；不需要额外容器。对照 `route`、邻居观测、ICMP 抓包和记录的命令：

1. 客户端命名空间选择 `198.51.100.0/29 via 192.0.2.3`；显式路由决定下一跳。
2. 客户端通过 ARP 解析路由器左侧 MAC。IP 目标地址仍为 `198.51.100.3`。
3. 一对 veth 和左侧 bridge 将以太网帧传送到路由器。L2 桥接不会消耗一个 IP TTL 跳数。
4. 路由器命名空间执行 IPv4 转发：递减 TTL、查询服务器路由，并检查出口 MTU。
5. 在右侧网络上，路由器解析服务器 MAC 并发送新的以太网帧。预期的路由路径不会转换这些源/目标 IP。
6. 服务器的显式返回路由使用 `198.51.100.2`。请求成功送达，并不意味着响应路径无需正常工作。

**预期标准**：从记录中可以指出每次路由查询所在的命名空间、其 IP 目标地址、本地 ARP 目标和返回路由。不要从其他运行中推断接口名称或 MAC 值。

Docker DNS 名称解析与 Linux 数据包转发是不同的观测。DNS 答案正确时，路由、转发策略或返回路径仍可能有问题。

每个网络命名空间也有自己的 loopback 设备。容器中的 `127.0.0.1` 不会到达主机上的 HTTP 辅助程序；本练习不会通过使用 host 网络模式改变这一点。

这是两个**专用的用户自定义 bridge，并通过显式路由器连接**；已禁用 masquerading，且三个容器中都没有 IPv4 默认路由。这定义了预期的实验路径，但不是一般性的安全隔离保证。本练习不会测量 Docker 默认的 Internet NAT、已发布端口转发或 Internet 吞吐量。

**清理**：复用已完成的记录；路由辅助程序已经尝试清理资源。记录失败或不完整时，应检查失败阶段，而不是禁用共享防火墙控制。

继续阅读[容器技术](../basics/03-container-technology.md)，然后完成[核心服务与网络实验](../labs/core/03-services-networking-lab.md)。Kubernetes CNI、Service 转换和 AWS VPC 路由还有各自的规则；应在适当层面检查它们，而不是照搬 Docker 拓扑。

## 参考资料与审核 {#references}

- [HTTP 语义：RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)和 [HTTP/1.1 分帧：RFC 9112](https://www.rfc-editor.org/rfc/rfc9112.html)
- [curl 手册](https://curl.se/docs/manpage.html)：HTTP 版本、HEAD、二进制请求数据和跟踪
- [ss(8)](https://man7.org/linux/man-pages/man8/ss.8.html)、[socket(7)](https://man7.org/linux/man-pages/man7/socket.7.html)和 [Linux TCP 缓冲区策略](https://docs.kernel.org/networking/ip-sysctl.html)
- [ip-route(8)](https://man7.org/linux/man-pages/man8/ip-route.8.html)、[ip-neighbour(8)](https://man7.org/linux/man-pages/man8/ip-neighbour.8.html)和 [network_namespaces(7)](https://man7.org/linux/man-pages/man7/network_namespaces.7.html)
- [iputils ping 手册](https://github.com/iputils/iputils/blob/master/doc/ping.xml)和 [traceroute(8)](https://man7.org/linux/man-pages/man8/traceroute.8.html)
- [ICMP：RFC 792](https://www.rfc-editor.org/rfc/rfc792.html)、[IPv4 路由器行为：RFC 1812](https://www.rfc-editor.org/rfc/rfc1812.html)和 [MSS：RFC 6691](https://www.rfc-editor.org/rfc/rfc6691.html)
- [Docker bridge 网络和驱动选项](https://docs.docker.com/engine/network/drivers/bridge/)

[检查你的理解](../quizzes/networking/07-linux-network-diagnostics-quiz.md)
