# 2. 地址、子网与网络接口

> **支持版本**：Ubuntu Server 24.04 LTS（主要路径）、Rocky Linux 9（备选路径）
> **最后更新**：2026 年 9 月 15 日

[上一课：Linux 终端](01-linux-cli.md) | [课程准备](README.md) | [测验](../../quizzes/networking/beginner/02-addressing-interfaces-quiz.md) | [下一课：持久配置](03-persistent-configuration.md)

网络接口即使有线缆、有地址，也仍可能无法访问某个服务。这是不同层面的问题。本课会先沿着各层跟踪一条消息，然后搭建一个小型本地 IPv4 网络，让你亲自观察这些区别。

## 先决条件与学习成果

完成[第 1 课](01-linux-cli.md)：熟练使用普通账户、`sudo`、变量、唯一的临时目录和虚拟机控制台。先准备两台可丢弃的本地虚拟机。两台都可以运行 Ubuntu Server 24.04 LTS，也可以使用 Rocky Linux 9 作为备选管理路径。这些命令使用 `iproute2`（Rocky 上为 `iproute` 软件包）和 iputils 中的 `ping`；练习前请确保它们已安装。本课不会安装软件包。

按照[课程准备](README.md)中的说明，在虚拟机管理程序中准备以下配置。“仅内部”指两个虚拟网卡都连接到**同一个隔离虚拟网络**，且该网络没有 DHCP 服务器、路由器或外部上行链路。仅主机网络不一定等价：虚拟机管理程序可能允许它访问主机或提供 DHCP。

| 客户机角色 | 现有管理网卡 | 独立的内部实验网卡 |
| --- | --- | --- |
| 客户端 | 保持现有 NAT/DHCP 连接不变 | `192.0.2.10/24`，不设网关或 DNS |
| 服务器 | 保持现有 NAT/DHCP 连接不变 | `192.0.2.20/24`，不设网关或 DNS |

从虚拟机管理程序设置中记录每台客户机**两个网卡的 MAC 地址**，以及每个网卡连接的虚拟网络。两台客户机的 MAC 地址必须各不相同。保持控制台窗口打开。`192.0.2.0/24` 网段保留用于文档示例（RFC 5737）；只在此隔离实验中使用，不要将其当作真实 Internet 目的地址。不要把实验网卡桥接到家庭、公司或云网络。

完成后，你应该能够：

- 区分以太网帧、IP 数据包、传输层端口和应用服务。
- 计算子网边界，并判断目标地址是本地地址还是需要经过路由器。
- 说明网关、DHCP、DNS、ARP 和 IPv6 邻居发现各自的作用。
- 不靠猜测名称，将客户机接口匹配到正确的虚拟机管理程序网卡。
- 检查链路、地址、路由和邻居，给每台实验网卡添加一个临时 IPv4 地址，并精确撤销这些更改。

**执行约定**：命令只能在**指定的练习虚拟机内部**运行，除非某行包含 `sudo`，否则以普通用户身份运行。绝不要配置物理主机或文档主机。标注“每台虚拟机”的命令，需要分别在两台虚拟机的控制台中运行；变量仅在当前 Shell 中有效。示例仅供说明，**并非虚拟机上的实测结果**。遇到意外错误，请先停止再继续。

## 沿着网络各层跟踪一条消息

假设在之后的练习中，客户端要通过 TCP 8080 端口向服务器请求一个网页。服务器必须确实在该端口侦听；仅分配 IP 地址并不会创建服务器。

| 层 | 承载或标识的内容 | 本地实验示例 |
| --- | --- | --- |
| 应用层 | 请求和响应的含义 | 请求网页的 HTTP 请求 |
| 传输层 | 使用端口号标识的 TCP 或 UDP 通信端点 | 客户端临时 TCP 源端口到服务器 TCP 8080 端口 |
| 网际层 | 用于路由的源/目标地址 IP 数据包 | `192.0.2.10` 到 `192.0.2.20` |
| 本地链路层 | 带有源/目标 MAC 地址的以太网帧 | 客户端实验网卡 MAC 到服务器实验网卡 MAC |

发送方会先将应用数据封装进传输层信息，再封装进 IP 数据包，最后封装成当前链路上的帧。接收方会移除这些封装。帧在链路上承载流量；路由器在不同网络之间转发 IP 数据包。数据包经过路由器时，链路层帧会被替换为下一段链路上的新帧。这个简单实验不需要在两台客户机之间设置路由器。

**MAC 地址**用于标识链路上的以太网接口；虚拟网卡也有 MAC 地址。**IP 地址加前缀**可告知主机如何在 IP 网络中定位接口。一个网卡可以有多个地址。地址本身都不能证明某个人的身份。

**端口**是 TCP 或 UDP 中的 16 位数字，不是虚拟机上的物理插口。TCP 8080 端口和 UDP 8080 端口是不同的端点。协议、源 IP/端口和目标 IP/端口共同区分一次通信。IP 可达并不意味着某个端口正在侦听或未被防火墙阻止。`ping` 使用的 ICMP 不使用 TCP/UDP 端口号。我们会在后续课程中测试应用服务。

## 计算 IPv4 与 CIDR，而不是死记

IPv4 地址有 32 位，通常写成四个十进制八位组，每组为 `0`–`255`。斜杠后的**前缀长度**表示网络部分占多少个前导位，其余位用于区分网络中的地址。这种斜杠表示法称为 CIDR 表示法。

对于 `192.0.2.10/24`，前 24 位属于网络，剩余 8 位属于主机：

| 计算 | 结果 |
| --- | --- |
| 前缀掩码：24 个 1 位，后接 8 个 0 位 | `255.255.255.0` |
| 主机位全部为 0 的地址 | 网络地址 `192.0.2.0` |
| 主机位全部为 1 的地址 | 广播地址 `192.0.2.255` |
| 地址数 | `2^(32-24) = 256` |
| 此子网中的普通主机范围 | `192.0.2.1`–`192.0.2.254` |

这里两个端点地址不会分配给普通主机，因此有 254 个主机地址。特殊的 `/31` 点到点和 `/32` 情况遵循不同规则，不属于本课的入门练习。`.10/24` 和 `.20/24` 都属于 `192.0.2.0/24`。`192.0.3.20` 不属于该网段，尽管它的前两个八位组相同。

再看一个不太直观的例子：**`192.0.2.70/26`**：

1. `/26` 留下 6 个主机位，因此每个地址块有 `2^6 = 64` 个地址。
2. 掩码是 `255.255.255.192`，最后一个八位组的二进制形式是 `11000000`。
3. `.70` 的最后一个八位组为二进制 `01000110`。保留前两位、将其余位清零后得到 `01000000`，即 `.64`。
4. 因此地址块从 `.0`、`.64`、`.128` 和 `.192` 开始。`.70` 位于 `.64` 地址块中。
5. 网络为 `192.0.2.64/26`，广播地址为 `.127`，普通主机范围是 `.65`–`.126`（62 个主机地址）。

因此，`.100/26` 与 `.70/26` 属于同一个子网，而 `.130/26` 不属于。除非前缀是 `/24`，否则只匹配前三个八位组并不足够。前缀数字越大，地址块越小。实际实验使用 `/24`，而不是 `/26` 计算示例。

## 网关、DHCP、DNS 和邻居各自回答不同问题

**路由**告诉内核应把数据包发送到哪里。直连路由表示“这个目标位于该接口所在的链路上”。包含 `via` 的路由会选择下一跳路由器，通常称为**网关**。如果有多条路由匹配，会先选前缀最长的路由。**默认路由**（`0.0.0.0/0`，显示为 `default`）是在没有更具体匹配项时采用的备用路径。

对于我们 `/24` 网段中的 `.10` 到 `.20` 流量，直连路由比管理默认路由更具体。客户端会直接通过实验链路发送。**实验网卡不需要填写网关**，而 `.1` 也不会自动成为路由器。请保留现有管理默认路由。

| 机制 | 它回答的问题 | 它无法证明什么 |
| --- | --- | --- |
| DHCP | “配置服务器能否分配地址并提供路由/DNS 等选项？” | Web 服务是否正在运行 |
| DNS | “某个名称对应哪个地址或其他记录？” | 是否存在路由或侦听服务 |
| IPv4 ARP | “在我的链路上，哪个 MAC 地址当前对应此 IPv4 邻居？” | 邻居是否接受 TCP 连接 |

DHCP 是配置交换机制，而不是转发每个数据包的过程。DNS 用于解析名称；它不会分配客户端自己的 IP 地址。在 IPv4 跨子网通信时，ARP 通常查找的是**下一跳网关的 MAC 地址**，而不是 Internet 另一端远程服务器的 MAC 地址。

我们的实验网卡没有 DHCP 服务器，使用字面 IP 地址通信时既不需要网关也不需要 DNS。独立的管理网卡可以继续使用现有 DHCP 配置。我们不会更改它的地址或解析器设置。

IPv6 使用**128 位**地址，以冒号分隔的十六进制组表示。一个组中的前导零可以省略，`::` 可压缩一段全零组。`::1` 是 loopback；以 `fe80:` 开头的地址通常是链路本地地址，只能在其所在链路上使用。多个接口可能各自拥有链路本地地址，因此目标地址可能需要 `%interface-name` 这样的区域标识来指明链路。接口名称应从客户机中确认，不要照抄示例。

`2001:db8::/32` 是 IPv6 文档示例地址空间（RFC 3849），不应在此配置。普通 IPv6 LAN 前缀通常为 `/64`。IPv6 使用 ICMPv6 邻居发现，不使用 ARP，也没有 IPv4 式广播。路由器通告、SLAAC 和 DHCPv6 是不同的配置主题。仅有链路本地 IPv6 地址不能证明可以访问 Internet。进行 IPv4 练习时，请保留现有 IPv6 设置，不要更改。

## 选择接口前先检查

新版 `ip` 命令按对象类型分组：`link` 查看设备，`address`（也可写 `addr` 或 `a`）查看地址，`route` 查看路由，`neigh` 查看邻居表。通常只读这些信息无需 `sudo`。

**每台虚拟机，普通用户；仅检查：**

```bash
hostname
ip -br link
ip -br address
ip a
ip -4 route
ip neigh
```

`-br` 要求显示简要输出。`-4` 将命令限制为 IPv4；不加它时，`ip a` 也会显示 IPv6。`ip a` 是 `ip address` 的简写，并不是添加地址的命令。

下面是带有示例标签的简要输出，**接口名称已替换为占位说明**：

```text
lo            UNKNOWN  00:00:00:00:00:00 <LOOPBACK,UP,LOWER_UP>
<management>  UP       02:00:00:00:01:10 <BROADCAST,MULTICAST,UP,LOWER_UP>
<lab>         DOWN     02:00:00:00:02:10 <BROADCAST,MULTICAST>
```

每一行依次显示接口名称、运行状态、MAC 地址和标志。对两台客户机分别将**完整 MAC 地址**与虚拟机管理程序记录核对。网卡顺序、PCI 挂载方式、镜像设置和操作系统命名规则都可能改变接口名。“第二行”以及猜测的 `eth1`/`ens19` 都不可靠。`lo` 是客户机内的 loopback，并非虚拟以太网卡。

`UP` 标志表示管理员已启用该设备。`LOWER_UP` 表示下层载波存在。设备可能已在管理上启用但没有载波；这种情况下应检查虚拟网线以及内部网络连接。运行状态显示 `UNKNOWN`（尤其是 loopback）不一定代表故障。更改前先保存接口原有的管理状态。

## 在每台虚拟机上记录边界和基线

**每台虚拟机，普通用户；按提示输入实际名称：**

```bash
read -r -p 'Lab NIC name matched by MAC: ' LAB_IF
read -r -p 'Management NIC name matched by MAC: ' MGMT_IF
ip -br link show dev "$LAB_IF"
ip -br link show dev "$MGMT_IF"
ip -4 address show dev "$LAB_IF"
ip -4 route show table main
```

`read` 会将输入保存为 Shell 变量，不会更改接口。如果名称为空、设备不存在、两个名称相同，或任一 MAC 与记录不符，请停止并重新识别接口。不要只因为命令接受某个名称就继续。

**更改前的检查关卡**：实验网卡上必须**尚未分配 IPv4 地址**；客户机也不得存在与 `192.0.2.0/24` 重叠的现有 IPv4 路由，唯一例外是预期存在的管理默认路由（`default`）。已有 IPv6 链路本地地址没有问题。如果实验网卡已有 IPv4 地址或出现意外路由，请停止并检查课程准备；不要删除未知状态，也不要重复使用网络管理器占用的地址。网络管理器之后可能覆盖手动状态，因此本练习只设置临时配置。

创建目录以保存基线。两台客户机分别执行。

**每台虚拟机，普通用户：**

```bash
NET_NOTE_DIR=$(mktemp -d "$HOME/network-beginner-ip.XXXXXX")
printf '%s\n' "$NET_NOTE_DIR"
```

记录此准确路径。如果创建失败或值为空，请停止。然后保存基线：

```bash
ip -details link show dev "$LAB_IF" > "$NET_NOTE_DIR/lab-link.before"
ip -4 -br address show dev "$MGMT_IF" > "$NET_NOTE_DIR/management-addresses.before"
ip -4 route show table main > "$NET_NOTE_DIR/routes.before"
cat "$NET_NOTE_DIR/lab-link.before"
```

`>` 会将输出写入指定文件，并覆盖同名文件；这里使用的是新目录。在链路标志中，确认是否包含**单独的 `UP` 标志**。单独的 `LOWER_UP` 不算。请在该虚拟机的 Shell 中只执行以下两个赋值之一，并记录结果：

```bash
# Use this only if the standalone UP flag was present:
LAB_LINK_WAS=up
```

```bash
# Otherwise use this:
LAB_LINK_WAS=down
```

还要在 Shell 之外记录原始状态、MAC 地址、接口名称和基线目录。如果会话丢失，清理操作仍需要这些记录。

## 添加两个临时地址

每台虚拟机选择**一个角色代码块**。这些赋值只保存文本。不要意外交换客户端/服务器地址，也不要把两个地址都分配给同一台客户机。

**仅限客户端虚拟机，普通用户：**

```bash
LAB_IP=192.0.2.10
LAB_CIDR=192.0.2.10/24
LAB_PEER=192.0.2.20
```

**仅限服务器虚拟机，普通用户：**

```bash
LAB_IP=192.0.2.20
LAB_CIDR=192.0.2.20/24
LAB_PEER=192.0.2.10
```

提权前再次检查目标。

**每台虚拟机，普通用户：**

```bash
printf 'guest=%s lab=%s management=%s address=%s original-link=%s\n' \
  "$(hostname)" "$LAB_IF" "$MGMT_IF" "$LAB_CIDR" "$LAB_LINK_WAS"
ip -br link show dev "$LAB_IF"
```

确认角色和记录的 MAC 均匹配。然后，**每台虚拟机都由普通用户调用 sudo**，只添加该虚拟机的实验地址：

```bash
sudo ip link set dev "$LAB_IF" up
sudo ip address add "$LAB_CIDR" dev "$LAB_IF"
```

`link set ... up` 会在管理上启用已识别的实验网卡，不会修改管理网卡。`address add` 会在客户机的**第二块网卡**上附加地址。这并非“给管理网卡添加第二个 IPv4 地址”，也不要求 Linux 显示 `secondary` 标志。

成功添加时通常不会打印内容。如果看到 `File exists`，请检查地址并停止；不要改用 `replace` 或清空接口。如果实验网卡原先处于 down 状态，你已将它启用但添加地址失败，后续清理仍要恢复链路状态；只有在你成功添加地址时才删除该地址。

此 `ip` 更改只更新内核当前状态，不会修改 Netplan 或 NetworkManager 配置。重启会清除手动添加状态；网络管理器也可能更早删除或重新创建地址。地址生命周期显示 `forever`，仅表示此运行时地址没有过期计时器，**不**表示它能跨重启保留。下一课会学习持久配置。

## 在各层解释结果

**每台虚拟机，普通用户；仅检查：**

```bash
ip -br link show dev "$LAB_IF"
ip -4 address show dev "$LAB_IF"
ip -4 route show dev "$LAB_IF"
ip -4 route get "$LAB_PEER"
```

客户端相关输出可能类似：

```text
inet 192.0.2.10/24 scope global <lab-name>
    valid_lft forever preferred_lft forever
192.0.2.0/24 dev <lab-name> proto kernel scope link src 192.0.2.10
192.0.2.20 dev <lab-name> src 192.0.2.10 uid 1000
```

地址表示“这个网卡拥有 `.10/24`”。`scope global` 是 Linux 的地址范围标签；它不会使文档示例地址变成 Internet 可达地址。添加地址后，系统默认还会自动创建一条连接前缀路由。`proto kernel` 表示该路由由内核自动创建，`scope link` 表示无需下一跳路由器，`src` 指定优先使用的源地址。服务器也应拥有 `.20/24`，并选择 `.20` 作为源地址。

`ip route get` 用于询问内核会如何路由到某个目标；**它不会发送探测数据包**。访问对端时，结果应选择实验网卡和正确的本地源地址，且不应包含 `via` 网关。即使其他连接正常，如果路由经过管理网卡，也说明配置有误。如果缺少直连路由或地址消失，请检查链路状态和配置所有者；不要添加冲突的默认路由。

配置好**两台**客户机后，发送少量流量，让 ARP 有理由解析对端。

**每台虚拟机，普通用户：**

```bash
ping -4 -c 3 -W 2 -I "$LAB_IF" "$LAB_PEER"
ip -4 neigh show dev "$LAB_IF"
```

`ping -4` 使用 IPv4 ICMP echo，`-c 3` 将请求数限制为 3，`-W 2` 将响应超时设为 2 秒，`-I` 选择实验接口。通常 iputils 允许普通用户进行此 echo 测试。权限错误说明工具/能力配置有问题，并不能证明网络已断开。

如果路径配置正确且允许 ICMP，预期会收到回复和发送/接收数据包统计。时间会变化，不要照抄示例中的延迟。邻居表示例：

```text
192.0.2.20 dev <lab-name> lladdr 02:00:00:00:02:20 REACHABLE
```

将 `lladdr` 与虚拟机管理程序记录的**对端实验网卡 MAC**核对。`REACHABLE` 表示最近已确认；`STALE` 表示存在缓存映射，但下次使用时需要重新确认，并非立即故障。发送任何流量之前表格为空很正常。`INCOMPLETE` 表示正在解析；`FAILED` 表示解析失败。表项是动态的，查看时状态可能变化。

| 观察结果 | 本课中下一步检查 |
| --- | --- |
| 无载波 / 没有 `LOWER_UP` | 虚拟机管理程序中的虚拟网线和正确内部网络连接 |
| IPv4 地址错误或缺失 | 角色变量、添加结果，以及网络管理器是否更改了网卡 |
| 对端路由使用管理网卡 | 前缀、实验地址和路由查询结果 |
| 邻居持续处于 `INCOMPLETE`/`FAILED` | 两台 VM 均在运行、位于同一内部网络、对端地址、唯一的 MAC 和 IP |
| 邻居 MAC 已解析，但 ping 无回复 | 对端状态和 ICMP 过滤；ARP 成功不等于 ICMP/服务成功 |

不要为了让首次测试通过而关闭防火墙或 IPv6。保存证据；必要时继续采用第 4 课的诊断方法以及第 6 课的防火墙策略。

## 成功检查与精确清理

撤销更改前，先在**两台客户机**上确认：

1. 通过 MAC 匹配，分别识别了管理接口和实验接口。
2. 实验网卡拥有角色对应的准确 `/24` 地址以及 `192.0.2.0/24` 连接路由。
3. 对端路由使用实验网卡和正确的源地址，且没有网关。
4. 你理解邻居证据；ICMP 回复只能证明有限的 IP 测试成功，不能证明 TCP 服务开放。
5. 管理地址、默认路由和原有管理连接仍符合记录的基线。

**每台虚拟机，普通用户；比较保存的/当前管理数据：**

```bash
cat "$NET_NOTE_DIR/management-addresses.before"
ip -4 -br address show dev "$MGMT_IF"
cat "$NET_NOTE_DIR/routes.before"
ip -4 route show table main
```

预期会新增实验网段连接路由，但不应新增实验默认路由。DHCP 可能独立续租管理地址，因此应比较接口、地址、网关和路由用途，而不要把每项动态细节都当作本练习所做的更改。

现在在每台虚拟机上分别练习回滚。如果 Shell 会话丢失，先根据已记录的 MAC 重新识别网卡，并从**该客户机**的记录恢复 `LAB_IF`、`MGMT_IF`、`LAB_IP`、`LAB_CIDR`、`LAB_LINK_WAS` 和 `NET_NOTE_DIR`。检查当前状态；变量不会自动保留。不要猜测要删除的地址。

**每台虚拟机，普通用户；确认自己成功添加的地址仍存在：**

```bash
ip -4 address show dev "$LAB_IF"
```

**每台虚拟机，普通用户调用 sudo；只删除本机添加的地址：**

```bash
sudo ip address del "$LAB_CIDR" dev "$LAB_IF"
```

只有在添加操作成功且该地址仍然存在时才执行删除。如果已经重启或网络管理器移除了地址，确认其不存在后跳过删除。这是定向逆操作：明确指定精确 IP、前缀和接口。不清空任何地址或路由。由于已设定“此前无 IPv4 地址”的先决条件，删除唯一的实验 IPv4 地址也会移除系统自动创建的连接路由。

**每台虚拟机，同一 Shell；只有必要时由普通用户调用 sudo：**

```bash
if [ "$LAB_LINK_WAS" = down ]; then
  sudo ip link set dev "$LAB_IF" down
fi
```

如果实验链路原先处于 down 状态，此条件分支会恢复你更改过的链路。如果原先已经是 up，就保持 up。`[` 会检查记录的值；只有 `down` 分支才执行提权命令。如果没有该值，请找回记录，不要臆造原始状态。

**每台虚拟机，普通用户；检查恢复情况：**

```bash
ip -br link show dev "$LAB_IF"
ip -4 address show dev "$LAB_IF"
ip -4 route show dev "$LAB_IF"
ip -4 -br address show dev "$MGMT_IF"
ip -4 route show default
```

预期结果是没有实验 IPv4 地址或连接路由，管理链路状态恢复原状，管理配置/访问与原始基线一致。动态学习的邻居表项可能会超时消失；不要为了让表看上去为空而清空邻居表。如果地址重新出现，可能由网络管理器接管：先暂停并调查持久配置，不要反复删除地址。

不再需要基线时，只删除其中三个文件和空目录。

**每台虚拟机，普通用户：**

```bash
rm -i -- "$NET_NOTE_DIR/lab-link.before" \
  "$NET_NOTE_DIR/management-addresses.before" "$NET_NOTE_DIR/routes.before"
rmdir -- "$NET_NOTE_DIR"
test ! -e "$NET_NOTE_DIR"
echo $?
unset LAB_IF MGMT_IF LAB_IP LAB_CIDR LAB_PEER LAB_LINK_WAS NET_NOTE_DIR
```

只确认删除自己的三个快照文本文件。存在性检查退出状态为 `0` 表示清理成功；如果 `rmdir` 失败，请检查具体剩余文件名。本练习没有修改持久网络配置。[第 3 课](03-persistent-configuration.md)会通过实际网络管理器重新配置相同地址，不应依赖此 Shell 留下的变量或临时状态。

## 参考资料与延伸阅读

主要文档于 2026 年 9 月 14–15 日核对：

- [Ubuntu 24.04 `ip-address` 手册](https://manpages.ubuntu.com/manpages/noble/man8/ip-address.8.html)、[`ip-link`](https://manpages.ubuntu.com/manpages/noble/man8/ip-link.8.html)、[`ip-route`](https://manpages.ubuntu.com/manpages/noble/man8/ip-route.8.html)和 [`ip-neighbour`](https://manpages.ubuntu.com/manpages/noble/man8/ip-neighbour.8.html)：命令语法、直连路由、地址生命周期和邻居状态。
- [Ubuntu 24.04 `ping` 手册](https://manpages.ubuntu.com/manpages/noble/man8/ping.8.html)：有界 echo 测试和接口选择。
- [IETF RFC 1122](https://www.rfc-editor.org/rfc/rfc1122.html)、[RFC 4632](https://www.rfc-editor.org/rfc/rfc4632.html)和 [RFC 826](https://www.rfc-editor.org/rfc/rfc826.html)：Internet 分层、CIDR 和 IPv4 地址解析。
- [IETF RFC 2131](https://www.rfc-editor.org/rfc/rfc2131.html)和 [RFC 1034](https://www.rfc-editor.org/rfc/rfc1034.html)：DHCP 和 DNS 的职责不同。
- [IETF RFC 5737](https://www.rfc-editor.org/rfc/rfc5737.html)和 [RFC 3849](https://www.rfc-editor.org/rfc/rfc3849.html)：保留用于文档示例的地址块。
- [IETF RFC 4291](https://www.rfc-editor.org/rfc/rfc4291.html)和 [RFC 4861](https://www.rfc-editor.org/rfc/rfc4861.html)：IPv6 编址和邻居发现。

完成[测验](../../quizzes/networking/beginner/02-addressing-interfaces-quiz.md)，然后继续学习[持久配置](03-persistent-configuration.md)。
