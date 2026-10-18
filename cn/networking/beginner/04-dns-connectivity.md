# 04. DNS 与连通性诊断

> **支持的版本**：Ubuntu Server 24.04 LTS（主要版本）、Rocky Linux 9（替代版本）
> **最后更新**：2026 年 9 月 15 日

“服务器无法访问”可能意味着名称解析失败、数据包选择了错误路由、防火墙拒绝了连接，或应用返回了错误。下面每项测试只回答一个较小的问题。选择下一项测试前，记录结果及其局限。

## 前置条件与学习目标

完成[持久化配置](03-persistent-configuration.md)。[课程实验环境](README.md)在同一内部虚拟网络上配置了客户端 `192.0.2.10/24` 和服务器 `192.0.2.20/24`。该网络**没有 DHCP、网关、DNS 服务器或上行链路**。每台来宾系统单独的 NAT/DHCP 管理网卡保持原样。

使用来宾控制台，并将虚拟机管理程序中的 MAC 与 `ip -br link` 输出相匹配，以识别实验网卡。主要课程不依赖公共 DNS 或互联网访问。单独标注的公共查询练习为可选内容。

| 来宾系统中已准备的工具 | 用途 |
|---|---|
| `ip`、`ping`、`getent`、`grep`、`timeout`、编辑器和 sudo | 本地配置、名称查询和有时限的探测 |
| `dig` | 检查 DNS 协议响应；由 BIND 工具包提供 |
| `tracepath` 和/或 Linux `traceroute` | 观察对跳数受限探测的响应 |
| `python3`（3.9+）、`curl`、`ss` | 提供临时网页并观察 HTTP/监听套接字 |
| Ubuntu OpenBSD `nc` 或 Rocky `ncat` | 测试一次 TCP 连接 |
| 在 systemd-resolved 运行时提供的 `resolvectl` | 检查该解析器；Rocky 不要求安装此工具 |

使用 `command -v ip ping getent timeout dig tracepath traceroute python3 curl ss nc ncat` 检查工具。没有可选的替代工具是正常情况；如果所选练习需要的工具缺失，请返回[来宾工具准备](README.md#guest-tools)，查阅软件包对应表并安装所需工具。本章不包含安装软件包的命令。

完成后，你将能够区分 NSS 查询与 DNS，说明权威响应和缓存，检查所选路由，解释 ICMP 和路由跟踪结果，区分 TCP 与 HTTP，并撰写包含合理后续步骤的故障报告。

## 1. 名称、DNS 与操作系统

DNS 是一种分布式数据库。**A** 记录包含 IPv4 地址；**AAAA** 包含 IPv6 地址；**CNAME** 将别名指向另一个名称；**PTR** 用于反向查询。这些记录都不能证明目标应用正在运行。

**递归解析器**会为客户端查找答案，使用缓存信息或查询其他 DNS 服务器。**权威服务器**保存某个区域发布的数据。缓存可以在允许的时限内重用肯定和否定答案。DNS **TTL** 以秒计；IP TTL 是跳数限制，两者无关。现在降低 DNS TTL 不会立即移除先前已按较高 TTL 缓存的副本。请参见 [DNS 概念](https://www.rfc-editor.org/rfc/rfc1034.html)和[否定缓存](https://www.rfc-editor.org/rfc/rfc2308.html)。

Linux 应用可能通过 **NSS**（Name Service Switch，名称服务切换）向 C 库查询名称。NSS 使用 `/etc/nsswitch.conf` 选择来源：`files` 读取 `/etc/hosts`；`dns` 使用 DNS；如果已安装/配置 `resolve`，则会与 systemd-resolved 通信。其他模块和方括号中的返回规则可能改变查询顺序。自行实现解析器的应用（例如使用 DNS over HTTPS 的浏览器）行为可能有所不同。

| 工具 | 回答的问题 |
|---|---|
| `getent ahostsv4 NAME` | 系统的 NSS/getaddrinfo 路径会返回哪些 IPv4 地址？ |
| `getent hosts NAME` | NSS hosts 查询会返回什么？其地址族行为与 `ahostsv4` 不同 |
| `getent -s files hosts NAME` | 仅 files 来源中是否包含此名称？ |
| `dig @SERVER NAME A` | 该服务器返回什么 DNS 响应？它不会通过 NSS 查询所给名称 |
| `resolvectl query NAME` | systemd-resolved 通过其解析器接口返回什么？ |

在**客户端**上检查但不要编辑：

```bash
grep '^hosts:' /etc/nsswitch.conf
cat /etc/hosts
ls -l /etc/resolv.conf
cat /etc/resolv.conf
systemctl is-active systemd-resolved
```

例如，`hosts: files dns` 会先尝试 hosts 文件，再使用 DNS。不要用此示例替换实际配置行。`/etc/resolv.conf` 可能是指向生成的 stub 文件、生成的上游服务器列表或由其他方式管理的文件的符号链接。`nameserver 127.0.0.53` 表示本地 loopback stub，而不是路由器。

在启用了 systemd-resolved 的 **Ubuntu 客户端**上：

```bash
resolvectl status
resolvectl statistics
```

检查每个链路的 DNS 服务器、搜索域和缓存统计。课程实验网卡不应提供 DNS；管理 DNS 仍可能显示出来。对于由 NetworkManager 管理的 **Rocky 客户端**，使用 `nmcli -f GENERAL,IP4,IP6 device show` 和上文的解析器文件检查步骤。不要为了匹配 Ubuntu 布局而安装 resolved 或重写符号链接。任何持久修正都应写入第 03 章已确认的所有者所管理的配置中。

## 2. 为两台虚拟机配置本地名称

在**客户端**上使用 `/etc/hosts`，这样本地实验不需要外部解析器。这些名称只是本地别名，不会重命名来宾系统、创建 DNS 记录或远程配置服务器。`.test` 保留用于测试；避免使用 `.local`，它具有特殊的组播 DNS 行为。

首先检查冲突：

```bash
grep -nE 'netlab\.test|BEGIN network-beginner-04|END network-beginner-04' /etc/hosts
```

首次运行时，预期不会有输出，并且退出状态为 1。如果有任何条目，请先检查，不要追加重复映射。创建新的恢复目录并备份：

```bash
sudo mkdir -m 700 /root/network-beginner-04
sudo cp -a /etc/hosts /root/network-beginner-04/hosts-before
sudoedit /etc/hosts
```

如果目录已经存在，请停止并检查之前的尝试。只将以下代码块添加到文件末尾；保留所有现有 localhost 和来宾主机名条目：

```text
# BEGIN network-beginner-04
192.0.2.10 client.netlab.test
192.0.2.20 server.netlab.test
# END network-beginner-04
```

现在比较仅查询文件和正常应用程序查询：

```bash
getent -s files hosts server.netlab.test
timeout 5s getent ahostsv4 server.netlab.test
timeout 5s getent hosts server.netlab.test
```

前两条结果都应包含 `192.0.2.20`。`ahostsv4` 可能会为 `STREAM`、`DGRAM` 和 `RAW` 重复该地址；它们表示套接字类型，不是三台服务器。`hosts` 可能会先查询 IPv6 再查询 IPv4，因此路径不同或耗时更久。超时（状态码 124）只是有时限的观测，不能证明 DNS 表示该名称不存在。

如果仅查询文件成功而正常查询失败，请检查 NSS 顺序/模块，并比较准确的拼写和地址族。不要通过修改路由来修复名称查询。只有服务器本身也要使用这些名称时，才需要为服务器配置 hosts 条目；在服务器上重复本节时也需要单独备份。

### 不依赖外部服务，使用 dig 进行比较

在 hosts 条目正常工作且 resolved 正在运行的 **Ubuntu 客户端**上：

```bash
resolvectl --network=no -4 query server.netlab.test
dig -r @127.0.0.53 server.netlab.test. A +time=2 +tries=1
```

`--network=no` 可阻止 resolved 访问网络，使本地来源/缓存足以回答查询，否则就会返回本地错误。`dig -r` 会跳过个人 `.digrc` 设置，`@127.0.0.53` 选择 stub，末尾的点号使 DNS 名称成为绝对名称，而这些选项会限制等待时间/重试次数。正常的 resolved 设置会读取 `/etc/hosts`，因此**两个**命令都可能返回 `.20`。Dig 仍发送了 DNS 查询；stub 是根据本地数据合成答案。因此，声称“dig 绝不会返回 hosts 文件中的条目”会产生误导。

如果 stub 被禁用，或 resolved 不读取 hosts 文件，则此分支可能不会成功。检查当前解析器设置，不要为了实验启用某项服务。在**任一发行版**上，将 hosts 查询与发送到实验服务器的 DNS 查询进行比较：

```bash
dig -r @192.0.2.20 server.netlab.test. A +time=2 +tries=1
```

这是一个**预期失败的探测**：课程服务器没有运行 DNS 服务，因此预期得到拒绝响应或超时，而不是答案。客户端有 hosts 条目并不会让服务器变成 DNS 服务器。如果出现意外答案，需要检查服务器的 53 端口上运行着什么服务。让普通应用继续使用 hosts 映射；不要将系统 DNS 指向 `.20`。

如果不指定 `@SERVER`，dig 会读取 `/etc/resolv.conf`，因此看似本地的测试可能会查询管理网络的上游解析器。上面的命令显式指定了查询目标。

### 解读 DNS 响应

以下内容是来自假设权威实验 DNS 服务的**示例响应**，并非本课捕获的输出，也并非本课创建的服务：

```text
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 1234
;; flags: qr aa; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0
;; ANSWER SECTION:
server.netlab.test. 300 IN A 192.0.2.20
;; SERVER: 192.0.2.53#53(192.0.2.53) (UDP)
```

| 字段/状态 | 解释 |
|---|---|
| `SERVER` | 返回此查询的服务器，不一定是权威数据源 |
| `300 IN A 192.0.2.20` | TTL 秒数、Internet 类、IPv4 类型和地址 |
| `aa` | 表示对相关查询名称的答案具有权威性；这并不保证连通性或身份 |
| 出现 `rd` / `ra` | 请求递归 / 支持递归；两者都不证明刚刚向上游进行了查询 |
| `NOERROR` 且有预期答案 | DNS 查询成功；还需检查数据本身 |
| `NOERROR` 但没有所请求的数据 | 可能是 NODATA；下结论前检查 Authority/CNAME/转介上下文 |
| `NXDOMAIN` | DNS 响应表示查询名称不存在；也可能是缓存/策略返回的结果 |
| `SERVFAIL` | 解析器失败，例如上游或验证出现问题 |
| `REFUSED` | 服务器策略拒绝了查询 |
| 超时 | 等待期间没有收到可用响应；不等于 NXDOMAIN |

`dig +short` 会隐藏有用的状态和服务器信息，因此诊断时应查看完整输出。收到 `NXDOMAIN` 响应后，dig 仍可能以 0 退出；仅凭退出状态不能证明找到了地址。

缓存可能位于应用、本地服务和上游递归解析器中。第二次查询更快，并不能单独证明命中了缓存。对于 resolved，可比较 `resolvectl statistics`；源自 hosts 文件的答案不一定像 DNS 记录那样缓存。`sudo resolvectl flush-caches` 会清除 resolved 的本地 DNS 缓存，但不会清除 `/etc/hosts`、应用缓存或上游缓存。查询后缓存状态会重新生成，且没有有意义的“恢复缓存”操作。本实验不需要清缓存；在单独调查缓存时，应先记录证据再考虑执行此操作。

## 3. 先检查所选路由，再探测 IP

在**客户端**上再次匹配实验 MAC，并替换名称：

```bash
LAB_IF='REPLACE_WITH_CLIENT_LAB_NIC'
ip -br link
ip -4 address show dev "$LAB_IF"
ip -4 route get 192.0.2.20
ip -4 route show default
```

路由结果示例如下：

```text
192.0.2.20 dev LAB_NIC src 192.0.2.10 uid 1000
```

`dev` 选择输出接口，`src` 选择源地址，`via` 则会指出下一跳路由器。本例中对端位于同一链路上，因此不需要 `via`。`LAB_NIC` 是说明性标签，不是实际设备名称。`ip route get` 只在本地执行路由查询；它不会发送 ping，也不能证明对端可用或返回路径正常。

如果查询选择了管理网卡，请停止对端探测，并检查实验地址/前缀及已保存的配置。不要删除管理默认路由。在**服务器**上运行 `ip -4 route get 192.0.2.10`，结果应选择实验网卡且源地址为 `.20`；回复数据包也需要有效的返回路径。

在**客户端**上比较 loopback、本机地址和对端：

```bash
ping -n -c 3 -W 2 127.0.0.1
ping -n -c 3 -W 2 192.0.2.10
ping -n -c 3 -W 2 192.0.2.20
```

`-n` 会禁止反向名称查询，`-c 3` 会发送三条 Echo Request，`-W 2` 会在没有收到响应时限制等待时间。使用数字地址可以从此次测试中排除正向名称查询。`time` 表示往返时间，不是带宽。回复中打印的 `ttl` 是收到数据包时剩余的 TTL；不知道初始值时，不能据此准确计算跳数。

Loopback 成功表示本地协议栈正常。ping 自己的实验地址通常由本地处理，并不会测试虚拟网线。收到对端回复表示当时 ICMP Echo 双向通信正常，但不能证明 TCP 端口可用。三次都没有回复，只能说明这三次探测的结果；还需要调查过滤、响应速率限制、地址错误或返回路径故障。

完成对端探测后，检查**客户端**的邻居项：

```bash
LAB_IF='REPLACE_WITH_CLIENT_LAB_NIC'
ip neigh show to 192.0.2.20 dev "$LAB_IF"
```

显示 `REACHABLE` 或 `STALE` 的 MAC 地址表示已知邻居映射；`STALE` 并非故障。`INCOMPLETE`/`FAILED` 表示 ARP 解析可能未成功。检查两个适配器连接的内部网络、对端地址、载波状态以及重复 IP 的可能性。DNS 不会提供以太网目标 MAC。

## 4. 谨慎解读 traceroute 和 tracepath

在**客户端**上运行已准备好的工具：

```bash
traceroute -4 -n -m 4 -q 1 -w 1 192.0.2.20
timeout 15s tracepath -4 -n -m 4 192.0.2.20
```

Linux traceroute 通常使用 UDP 探测。`-m 4` 限制最大 TTL，`-q 1` 表示每个 TTL 只发送一次探测，`-w 1` 限制每次探测的等待时间。Tracepath 也使用 UDP，并报告路径 MTU 信息；外层的 `timeout` 会限制其总运行时间。如果对端直接相连且允许回复，预期目标会在 TTL 1 时出现。虚拟以太网交换机不是 IP 路由器，不会在 traceroute 中增加一跳。

探测的 TTL 到期时，路由器可能返回 ICMP Time Exceeded。探测关闭 UDP 端口时，目标可能返回 ICMP Port Unreachable。这些控制响应能揭示路径的部分信息，但不是每个数据包经过路径的完整记录。

traceroute 中的 `*` 或 tracepath 中的 `no reply` 表示在超时前没有收到匹配的响应。这**不**能证明该跳丢弃了普通应用流量。过滤、速率限制、探测协议不同以及非对称返回路径都可能造成响应缺失。后续跳或应用仍可能成功响应。

如果已安装的 Linux traceroute 支持，可选用 **ICMP 比较探测**访问同一对端：

```bash
sudo traceroute -4 -I -n -m 4 -q 1 -w 1 192.0.2.20
```

`-I` 使用 ICMP Echo 探测；在需要时 sudo 允许发送原始探测包。结果不同可能反映协议相关的策略。这些命令不会更改持久配置。不要为了让路由跟踪输出更好看而禁用防火墙。

## 5. 使用一个本地服务区分 TCP 与 HTTP

不假定系统已经安装 SSH 或 Web 服务器。我们会使用现有 Python 创建一个临时 HTTP 服务，并且只绑定到**服务器实验地址**。

### 在服务器上启动有时限的服务

在**服务器终端 A**中，确认 `.20` 属于实验网卡，并且没有其他 TCP 监听器占用 18080 端口：

```bash
ip -br address
ss -ltn 'sport = :18080'
```

如果已有监听器，请识别其所属服务；不要终止其他服务。选择一个空闲端口并相应调整本节，或者先完成之前的实验。

仍在同一个**服务器终端 A**中，以普通用户身份创建新目录并提供其中的内容：

```bash
LAB_HTTP_DIR=$(mktemp -d /tmp/network-beginner-04.XXXXXX)
printf '%s\n' "$LAB_HTTP_DIR"
printf 'network lab ok\n' > "${LAB_HTTP_DIR:?missing lab directory}/index.html"
timeout 300s python3 -m http.server 18080 --bind 192.0.2.20 --directory "${LAB_HTTP_DIR:?missing lab directory}"
```

如果 `mktemp` 失败，请停止。`${variable:?message}` 可防止使用空路径变量。记录打印出的目录路径。只有这个新目录包含要提供的文件；不要提供 home 目录，也不要添加指向该目录的符号链接。`--bind` 可以避免监听所有接口，`--directory` 选择内容根目录，`timeout` 会在五分钟后终止服务器。也可以提前按 Ctrl+C 停止。时间限制结束时，预期超时退出状态为 124。

如果计时器在练习过程中到期，请在同一个服务器终端 A 中使用 `timeout 300s python3 -m http.server 18080 --bind 192.0.2.20 --directory "${LAB_HTTP_DIR:?missing lab directory}"` 重新启动；复用已记录的目录，不要再次运行 `mktemp`。

Python 内置 HTTP 服务器仅用于练习。这里没有身份验证/TLS，也不是生产部署方式。不会创建系统服务或启用开机启动。

在服务运行期间，于**服务器终端 B**中：

```bash
ss -ltn 'sport = :18080'
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:18080/
```

预期会看到监听地址 `192.0.2.20:18080`、HTTP 200 和 `network lab ok`。此 Python 服务器响应中的 HTTP/1.0 是正常现象，包括 Rocky 上使用 Python 3.9 的情况。向自身发起请求只能验证本地应用行为，不能验证来自客户端的路径。如果绑定时报错“Cannot assign requested address”，请检查第 03 章中服务器的地址。如果报告权限拒绝，应调查该故障，而不是禁用 SELinux。

### 从客户端测试 TCP

在安装 OpenBSD netcat 的 **Ubuntu 客户端**上：

```bash
nc -n -z -v -w 3 192.0.2.20 18080
```

在使用 Ncat 的 **Rocky 客户端**上，等价命令为：

```bash
ncat -n -z -v -w 3 192.0.2.20 18080
```

`-n` 可避免 DNS 查询，`-z` 在不发送应用负载的情况下测试连接建立，`-v` 显示结果，`-w 3` 限制连接等待时间。成功只证明当时能与该端点建立 TCP 连接，并不代表 HTTP 正常。拒绝连接通常表示端口关闭或被主动拒绝；超时可能意味着过滤、邻居未解析、对端关闭或返回路径有问题。

来宾防火墙可能会阻止这个新端口，尤其是已配置 Rocky firewalld 策略时。结合服务器监听器/自测结果与客户端路由/邻居/TCP 证据，记录一个**可能的策略边界**。本章不更改防火墙规则；[第 06 章](06-firewalls-host-security.md)会介绍范围受控的策略更改。如果远程测试受阻，请在服务器终端 B 完成 HTTP 观测，并保留客户端失败信息供后续课程使用。不要把服务器对自身的请求报告为远程 HTTP 成功。

### 测试 HTTP 并比较名称解析

服务运行期间，在**客户端**上：

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:18080/
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://server.netlab.test:18080/
```

第一个选项 `--disable` 会跳过 curl 默认配置；`--noproxy '*'` 会避免使用继承的 HTTP 代理。`--connect-timeout` 限制连接建立时间，`--max-time` 限制整个操作时间，`-i` 会显示响应标头。第二条命令会使用客户端的名称查询结果。如果数字 URL 成功而名称 URL 失败，请在更改路由前比较 `getent ahostsv4` 的结果和 curl 错误。

要仅针对**本次 curl 调用**隔离名称查询，请保留主机名但提供已知实验地址：

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  --resolve server.netlab.test:18080:192.0.2.20 \
  -i http://server.netlab.test:18080/
```

`--resolve` 只更改 curl 针对此主机名/端口的映射；不会更改 hosts 文件或 DNS 记录，也无需回滚。HTTP Host 标头仍使用原名称。真实 HTTPS 还涉及基于名称的证书验证和 TLS SNI；将主机名替换为 IP 并不总等于测试原应用。不要绕过证书验证并声称 TLS 问题“已修复”。

请求一个从未创建过的文件，构造无害的应用层失败：

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:18080/missing-page
```

如果服务器可访问，预期得到 HTTP **404**。名称/IP 路径和 TCP 传输已足以返回 HTTP 错误；只是请求的页面不存在。没有 `--fail` 时，curl 遇到 HTTP 404 仍可能以 0 退出，因此应查看状态行。`curl -I` 会发送 **HEAD**，并非只隐藏响应体的 GET。

## 6. 根据证据选择下一项测试

按此表的顺序操作；如果新证据推翻某项假设，则返回较早的行。示例只是可能原因，不是自动诊断结果。

| 观察结果 | 已确认的事实 | 用于区分原因的下一项检查 |
|---|---|---|
| 仅查询文件时没有 `.20` | 本地映射缺失/错误 | 准确拼写、`/etc/hosts` 配置段及重复条目 |
| 文件查询正常；普通 getent 失败 | 名称来源行为不同 | NSS 顺序/返回规则、模块和地址族 |
| getent 正常；查询 `.20` 的 dig 失败 | 本地名称解析正常；`.20` 上没有预期 DNS 服务 | 使用 hosts 条目；只有需要 DNS 时才检查真正的解析器 |
| DNS 返回 `NXDOMAIN` | 收到了 DNS 否定响应 | 查询拼写、解析器/视图、权威数据及否定缓存 |
| DNS 超时 | 限定时间内没有可用 DNS 答案 | 到解析器的 `ip route get`、53 端口可达性、解析器服务/策略 |
| 路由选择了管理网卡或错误源地址 | 本实验的本地转发选择有误 | 实验地址/前缀、持久配置所有者、路由/规则清单 |
| 路由正确；邻居状态为 `FAILED` | 下一跳 MAC 解析失败 | 虚拟机管理程序网络/网线、对端地址、链路状态和冲突 |
| 存在邻居项；ping 失败 | 已知 MAC，但没有 ICMP 回复 | 服务器返回路由、ICMP 策略，然后检查预期 TCP 端口 |
| ping 成功；TCP 被拒绝 | ICMP 正常；TCP 被主动拒绝 | 服务器 `ss`、服务运行时间/绑定地址、拒绝策略 |
| 服务器自测 HTTP 正常；客户端 TCP 超时 | 本地服务正常；远程路径尚未验证 | 两端路由、邻居及主机策略；记录证据供第 06 章使用 |
| TCP 建连；HTTP 挂起或无效 | 连接建立正常 | 协议/端口是否正确、应用日志和响应行为 |
| HTTP 404/403/500 | HTTP 端点返回了应用结果 | 请求路径、应用权限或服务错误；这不是 DNS 修复方法 |
| 数字 HTTP 正常；名称 HTTP 失败 | 不依赖普通查询时已知端点可用 | getent 结果、curl 解析错误、单次请求 `--resolve` 比较 |
| Traceroute 出现 `*`；HTTP 正常 | 路由跟踪探测未收到响应；应用请求成功 | 探测协议/速率限制；没有依据断言数据包全部丢失 |

常用 curl 退出码包括 **6**（无法解析主机）、**7**（无法连接）和 **28**（操作超时）。它们指出失败阶段，但不一定指出根因。记录命令、执行命令的虚拟机、时间戳（`date -Is`）、目标、输出、退出状态（随后立即运行 `echo $?`）、预期结果和下一步测试。区分“观察到的事实”和“推测”。

## 7. 可选：观察公共 DNS

**外部依赖**：只有在客户端现有且未经更改的管理网络已提供获准的互联网访问，并允许查询所选解析器时，才运行此项。这不是完成课程的要求，失败本身也不能说明隔离的 `.10` ↔ `.20` 实验有问题。不要为实验网卡添加上行链路或公共 DNS 服务器。

```bash
ip -4 route get 1.1.1.1
dig -r @1.1.1.1 example.com. A +time=2 +tries=1
dig -r @1.1.1.1 example.com. AAAA +time=2 +tries=1
dig -r @1.1.1.1 example.com. NS +time=2 +tries=1
```

发送查询前检查路由；路由应使用预先存在的管理路径。如果策略要求使用另一个经批准的解析器，请始终一致地替换为其已知地址。观察 DNS 状态、服务器、记录类型和 TTL，不要期待固定的公共 IP。再执行一次 A 查询并比较 TTL，但不要仅根据时序推断缓存位置。`+tcp` 可用于将 DNS over TCP 与常见的 UDP A 查询进行比较。不要通过公共解析器查询私有/内部名称。

NS 答案指出权威信息；递归解析器 `1.1.1.1` 返回的答案并不会因此成为该区域的权威响应。`dig +trace` 跟随 DNS 委派，而不像 traceroute 那样跟踪 IP 路由器跳数；它会增加外部依赖，因此不属于本地练习范围。

## 8. 清理与完成检查

在**服务器终端 A**中，按 Ctrl+C 停止 Python 进程，或等待计时器到期。在终端 B 中使用 `ss -ltn 'sport = :18080'` 确认本课监听器已停止。

在**创建目录的同一个终端 A shell**中，检查并只移除该文件及空目录：

```bash
printf '%s\n' "$LAB_HTTP_DIR"
ls -la -- "${LAB_HTTP_DIR:?missing lab directory}"
rm -i -- "${LAB_HTTP_DIR:?missing lab directory}/index.html"
rmdir -- "${LAB_HTTP_DIR:?missing lab directory}"
unset LAB_HTTP_DIR
```

如果已关闭该 shell，请将 `LAB_HTTP_DIR` 设置为记录的准确路径，并在执行此代码块前验证目录内容。不要使用范围过大的通配符猜测路径。`rmdir` 会拒绝删除非空目录，有助于暴露意外文件。

在每台编辑过 `/etc/hosts` 的来宾系统上，使用 `sudoedit /etc/hosts` 只删除 `# BEGIN network-beginner-04` 和 `# END network-beginner-04` 之间的内容，并一并删除这两条标记行。与 `sudo diff -u /root/network-beginner-04/hosts-before /etc/hosts` 比较；如果没有其他无关编辑且无输出，表示原始内容已恢复。保留合法的中间修改，不要用备份覆盖它们。

验证 `getent -s files hosts server.netlab.test` 不再返回本课的映射。不要要求所有解析器立即忘掉此名称。第 03 章中的静态地址和管理设置仍保留，以供 SSH 使用。

继续学习之前，你应能够：

- 根据来宾系统上的实际来源说明 getent/NSS、dig 和 resolved 的行为。
- 不使用公共 DNS 在本地解析 `.20`，并解释预期失败的 dig 查询。
- 解读 DNS 响应，包括 TTL、权威状态和否定结果。
- 显示所选实验路由/源地址，并区分 loopback、邻居和对端证据。
- 解释为何 trace 中的星号不能证明应用流量丢包。
- 比较 TCP 测试、HTTP 200 和 HTTP 404，并指出每个结果由哪台虚拟机产生。
- 根据证据和下一项检查描述远程测试受阻的情况；不要用本地成功代替远程结果。
- 移除临时服务器、相关文件和 hosts 条目，且不更改网络/防火墙设置。

## 主要资料与延伸阅读

- [Ubuntu Server：名称与 NSS](https://documentation.ubuntu.com/server/explanation/networking/configuring-networks/)、[getent 手册](https://manpages.ubuntu.com/manpages/noble/en/man1/getent.1.html)
- [BIND dig 手册](https://bind9.readthedocs.io/en/latest/manpages.html#dig-dns-lookup-utility)、[Ubuntu 24.04 中的 resolvectl](https://manpages.ubuntu.com/manpages/noble/en/man1/resolvectl.1.html)
- [DNS 概念：RFC 1034](https://www.rfc-editor.org/rfc/rfc1034.html)、[否定缓存：RFC 2308](https://www.rfc-editor.org/rfc/rfc2308.html)、[测试域名：RFC 2606](https://www.rfc-editor.org/rfc/rfc2606.html)
- [ping](https://manpages.ubuntu.com/manpages/noble/en/man8/ping.8.html)、[tracepath](https://manpages.ubuntu.com/manpages/noble/en/man8/tracepath.8.html)、[Ubuntu 附带的 Linux traceroute 手册](https://manpages.ubuntu.com/manpages/noble/en/man1/traceroute.db.1.html)
- [OpenBSD nc](https://man.openbsd.org/nc)、[Ncat](https://nmap.org/book/ncat-man.html)、[curl 手册](https://curl.se/docs/manpage.html)、[Python HTTP 服务器](https://docs.python.org/3.12/library/http.server.html)
- 后续可学习[Linux 网络诊断](../07-linux-network-diagnostics.md)，了解数据包、TCP 队列和 MTU 的解读方法。

[上一章：持久化配置](03-persistent-configuration.md) · [测验](../../quizzes/networking/beginner/04-dns-connectivity-quiz.md) · [下一章：SSH 访问](05-ssh-access.md)
