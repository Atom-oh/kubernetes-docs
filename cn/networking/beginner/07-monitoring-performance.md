# 7. 网络监控与性能入门

> **学习基线**：Ubuntu Server 24.04 LTS，另提供 Rocky Linux 9 路径
>
> **最后更新**：2026 年 9 月 15 日

**前置要求**：完成[第 1–6 课](README.md#course-map)。两台虚拟机通过各自的实验网卡通信；服务器上的 TCP 8000 端口只允许实验客户端访问。如果其他实验服务器占用了 8000 端口，请先确认其归属，再按照对应实验的流程将其停止。

**学习成果**：区分监听器、连接、队列、数据包和流量大小，并将“运行很慢”转化为可以验证的问题。包含练习约需 2–3 小时。

## 工具与观测点 {#observation-tools}

| 问题 | 工具 | 无法据此确认的内容 |
|---|---|---|
| 程序正在监听哪个地址和端口？ | `ss -ltnp` | 外部客户端是否能够访问 |
| 连接处于什么状态，队列情况如何？ | `ss -tinm` | 仅凭一次快照确定丢包原因 |
| 哪些数据包经过了这块网卡？ | `tcpdump` | 其他未抓包的网卡或网络命名空间上的活动 |
| 哪些主机对占用了带宽？ | `iftop` | 应用程序处理时间或准确的计费流量 |
| HTTP 请求耗时在哪里？ | `curl -w` | 服务器各个函数内部的时间 |

较早的资料可能使用 `netstat`。本课程使用 `ss` 观察套接字。`netstat -lnt` 和 `ss -ltn` 可以回答类似的问题，但输出格式和字段并不完全相同。缺少 `netstat` 不代表应该删除较新的工具或重新配置系统。

请检查服务器上是否安装了所需软件包。在 Ubuntu 上：

```bash
sudo apt update
sudo apt install iproute2 tcpdump python3
```

在 Rocky 上：

```bash
sudo dnf install iproute tcpdump python3
```

客户端需要 `curl`；请按照[第 1 课](01-linux-cli.md)中的软件包管理器说明安装。

## 生成少量 HTTP 流量 {#small-http-workload}

**服务器控制台 A**：在一个空的临时目录中创建一个实验文件。

```bash
LAB_WEB=$(mktemp -d /tmp/net-web.XXXXXX)
printf 'network lesson\n' > "$LAB_WEB/index.html"
timeout 300 python3 -m http.server 8000 \
  --bind 192.0.2.20 --directory "$LAB_WEB"
```

服务器只公开指定目录，并在五分钟后停止。退出状态 124 表示 `timeout` 达到了时限。这不是带 TLS 和用户身份验证的生产 Web 服务器。不要在实验目录中放入其他文件或符号链接。

**客户端**：发送一个请求，然后以一秒为间隔再发送十个请求。

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/
for n in $(seq 1 10); do
  curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
    -sS -o /dev/null http://192.0.2.20:8000/
  sleep 1
done
```

**通过标准**：第一个响应是 HTTP 200，响应正文包含 `network lesson`。后续请求应无错误完成，并出现在服务器日志中。如果请求失败，请返回[第 4 课的诊断流程](04-dns-connectivity.md)，不要通过增加负载来排查。

## 查看套接字状态和队列 {#socket-observation}

**服务器控制台 B**：打开另一个终端。

```bash
sudo ss -ltnp 'sport = :8000'
ss -tinm '( sport = :8000 or dport = :8000 )'
```

在第一条命令的结果中找到 `192.0.2.20:8000` 监听器。客户端发送请求时，重复观察第二条命令。短连接可能在两次快照之间就已结束；没有 ESTABLISHED 行并不能证明请求失败。请结合服务器日志和数据包捕获结果进行分析。

| 状态或字段 | 含义 |
|---|---|
| LISTEN `Recv-Q` / `Send-Q` | 等待被接受的连接 / accept backlog 上限 |
| ESTABLISHED `Recv-Q` | 应用程序尚未读取的有序字节 |
| ESTABLISHED `Send-Q` | 尚未确认的流字节，包括尚未发送的数据 |
| `rtt` | TCP 往返时间估计值，并非 HTTP 总耗时 |
| `cwnd` | 发送端拥塞窗口；`ss` 通常以报文段显示 |
| `skmem` | 套接字内存记账，其中包含开销，并不只是排队中的负载字节数 |

这些小请求下队列为零是正常现象。形成大型队列并不是成功标准。[Linux TCP 队列练习](../07-linux-network-diagnostics.md#tcp-buffer-lab)使用持续时间更长的连接，并提供进一步说明。

## 在选定网卡上捕获数据包 {#packet-capture}

**服务器控制台 B**：根据虚拟机管理程序中记录的 MAC 地址，找到实验网卡。

```bash
ip -br link
```

将下面的示例名称替换为已确认的网卡名称。`enp0s8` 只是示例，不代表应该选择管理网卡。

```bash
LAB_IF=enp0s8
ip -br address show dev "$LAB_IF"
sudo timeout 15 tcpdump -ni "$LAB_IF" -c 20 \
  'host 192.0.2.10 and tcp port 8000'
```

开始抓包后，**从客户端再次执行 curl 请求**。`-n` 可避免名称查询，`-i` 用于指定接口，`-c 20` 将捕获的数据包数限制为 20。15 秒的时限可能会先到。

TCP 标志示例包括 `[S]`（SYN）、`[S.]`（SYN+ACK）、`[.]`（ACK）和 `[F.]`（FIN+ACK）。数据和确认信息可能以不同方式组合。不要死记“一个 HTTP 请求恰好对应三个数据包”这类固定规则。

保存证据时，只需在短时间内捕获本次实验的流量。

```bash
LAB_CAPTURE=$(mktemp -d /tmp/net-capture.XXXXXX)
sudo timeout 15 tcpdump -Z "$(id -un)" -ni "$LAB_IF" -c 20 \
  -w "$LAB_CAPTURE/http.pcap" 'host 192.0.2.10 and tcp port 8000'
sudo tcpdump -nn -r "$LAB_CAPTURE/http.pcap"
```

运行写入抓包文件的命令时，再次从客户端发送请求。`-Z "$(id -un)"` 会在打开抓包设备后切换到当前普通用户，使抓包文件能够写入该用户的临时目录。PCAP 可能包含地址和真实负载。请只使用本实验中的字符串，不要捕获 SSH 凭证或真实用户流量。读取命令使用 `sudo`，以应对文件权限差异。

**解读结果**：识别请求和响应的地址、端口。如果没有捕获到内容，先检查网卡、过滤条件和时间窗口。网卡卸载功能可能导致主机观测到的数据包大小和校验和与线路上的值不同。一次抓包中的校验和警告不能证明网络存在故障。

## 带宽与请求计时 {#bandwidth-and-time}

`iftop` 是可选工具。在 Ubuntu 上可通过 `sudo apt install iftop` 安装。如果 Rocky 已配置的软件源不提供此工具，可以跳过练习，或先检查[第 6 课中的 EPEL 前置要求](06-firewalls-host-security.md)。`sudo dnf install iftop` 失败并不意味着应该运行任意外部安装脚本。

**服务器**：在已设置并验证 `LAB_IF` 的终端中运行：

```bash
sudo iftop -nNP -i "$LAB_IF" -f 'host 192.0.2.10'
```

重复发送客户端请求，查看各方向的速率，然后按 `q` 退出。小而短的请求可能显示为接近零。这不是链路容量或互联网吞吐量测试。

**客户端**：单独观察 HTTP 请求耗时。

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -sS -o /dev/null \
  -w 'dns=%{time_namelookup} connect=%{time_connect} first_byte=%{time_starttransfer} total=%{time_total}\n' \
  http://192.0.2.20:8000/
```

这些值表示从开始时刻起经过的秒数。此请求使用 IP 字面量，不会测量 DNS 性能。首字节时间包含此前的步骤和服务器准备时间；不要将所有字段相加，仿佛它们是相互独立的时间段。

| 测量项 | 含义 | 需要控制的条件 |
|---|---|---|
| 延迟 | 操作或往返所需时间 | 请求大小、路由、服务器负载 |
| 吞吐量 | 单位时间内传输的数据量 | 并发数、方向、按字节还是按比特计量、持续时间 |
| 丢包 / 重传 | 观测到的数据包丢失或 TCP 恢复 | 抓包位置 / 丢包、路由变化、时间窗口 |
| 资源使用量 | CPU、内存和 I/O 活动或等待 | 进程、虚拟机分配、其他负载 |

`1 byte = 8 bits`。不要把 `100 Mbit/s` 等同于 `100 MB/s`。重复测量时，应记录测试条件和最小值 / 中位数 / 最大值，或选择其他合适的分布指标。

## 接下来学习内核与 I/O {#kernel-next}

以下命令**只观察状态**：

```bash
uname -r
sysctl net.ipv4.tcp_congestion_control
sysctl net.ipv4.tcp_rmem net.ipv4.tcp_wmem
lsblk -o NAME,TYPE,SIZE
```

`sysctl` 返回的缓冲区策略值并非每个套接字当前的用量。在增加这些值之前，请先区分[套接字缓冲区、窗口和 BDP](../../kernel/02-network-stack.md#tcp-buffer-policy)。使用 `lsblk` 找到磁盘后，读取 `/sys/block/DEVICE/queue/scheduler` 可查看其支持 / 选定的块 I/O 调度器；并非所有虚拟设备都提供相同选项。

块 I/O 调度器处理存储请求，网络 qdisc 则处理网络发送队列。两者名称都包含“调度器”，不代表它们是可互换的调优控制项。本课不会更改 sysctl、MTU、qdisc 或 I/O 调度器。高级实验需要单独控制变量，并进行测量和回滚。

## 清理与完成要求 {#completion}

在控制台 A 中按 Ctrl+C 停止服务器，或等待其达到时限。在**同一个终端**中，只删除自己的实验文件和目录。

```bash
rm -- "${LAB_WEB:?}/index.html"
rmdir -- "${LAB_WEB:?}"
```

在抓包终端中也删除抓包文件。

```bash
sudo rm -- "${LAB_CAPTURE:?}/http.pcap"
rmdir -- "${LAB_CAPTURE:?}"
```

如果变量未设置或为空，`${VARIABLE:?}` 会阻止命令执行。如果目录非空，应先调查原因，而不要使用范围过大的递归删除。

- 说明监听器、TCP 连接和 HTTP 成功为何是不同形式的证据。
- 在 PCAP 中识别两个方向的地址 / 端口，并记录抓包点。
- 说明队列 / 带宽单位，以及使用 IP 字面量的请求无法测量 DNS 的限制。
- 区分仅观察状态与需要单独受控实验的调优操作。

## 参考资料与下一课

- [iproute2 ss 手册](https://man7.org/linux/man-pages/man8/ss.8.html)
- [tcpdump 手册](https://www.tcpdump.org/manpages/tcpdump.1.html)
- [iftop 作者提供的手册](https://www.ex-parrot.com/pdw/iftop/iftop.8.html)
- [curl 手册](https://curl.se/docs/manpage.html)
- [Python 3.12 http.server](https://docs.python.org/3.12/library/http.server.html)
- [Linux 块多队列](https://docs.kernel.org/block/blk-mq.html)

[上一课：防火墙与主机安全](06-firewalls-host-security.md) · [测验](../../quizzes/networking/beginner/07-monitoring-performance-quiz.md) · [下一课：综合实践](08-container-cloud-capstone.md)
