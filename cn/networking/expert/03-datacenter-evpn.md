# 03. 数据中心 EVPN：隔离与数据平面证据

> **最后更新**：2026 年 9 月 15 日
> **实验边界**：单独准备、由你拥有且可随时丢弃的 Linux Fabric 虚拟机；不使用生产 Fabric 或云资源。
> **验证状态**：已核对官方文档、上游拓扑以及 FRR CLI/模板源码；编写本章时**没有实际运行这些实验**。

已建立的 EVPN BGP 会话只是初步观测，不能证明 Fabric 正常工作。
本练习手册要求你跟踪帧或数据包穿过 VLAN、VNI、VRF 和 Underlay 的路径，然后证明隔离效果并恢复原状。
请先完成[八节入门课程](../beginner/README.md)和[路由策略](02-routing-policy-convergence.md)。
使用[Linux 网络栈基础知识](../../kernel/02-network-stack.md)来解释 bridge、邻居和内核路由证据。

## 1. 分层阅读架构

| 主要阅读材料 | 操作实验前要完成的产物 |
|---|---|
| [netlab EVPN 模块](https://netlab.tools/module/evpn/) | 针对所选设备的功能/提供程序检查表 |
| [netlab 平台支持](https://netlab.tools/platforms/)和 [FRR 注意事项](https://netlab.tools/caveats/#frrouting) | 说明为何容器中的 FRR 仍依赖虚拟机内核 |
| [FRR EVPN](https://docs.frrouting.org/en/latest/evpn.html) | 将 Linux bridge、VXLAN 接口、SVI 和 VRF 对应到 EVPN 概念 |
| [RFC 7348](https://www.rfc-editor.org/rfc/rfc7348.html)、[RFC 7432](https://www.rfc-editor.org/rfc/rfc7432.html) | 绘制封装过程，并区分路由标识与导入策略 |
| [RFC 9135](https://www.rfc-editor.org/rfc/rfc9135.html)、[RFC 9136](https://www.rfc-editor.org/rfc/rfc9136.html) | 解释 IRB 及前缀通告和主机通告的差异 |

**VLAN** 定义本地二层成员关系；接入端口 VLAN 和允许通过的 Trunk VLAN 不是可以互换的设置。
**LACP** 会协商链路聚合组：成员状态和哈希决定可用容量；单条流量未必使用每个成员。
**STP** 用于保护桥接拓扑免受环路影响；如果端口意外阻塞，问题可能发生在 EVPN 之前。
阅读 [netlab VLAN](https://netlab.tools/module/vlan/)、[LAG](https://netlab.tools/module/lag/)和 [STP](https://netlab.tools/module/stp/)资料，并结合此检查表。
所选的小型实验**不会**构建 LACP 或冗余 STP 拓扑。应标记为“未实例化”，而不是“测试成功”。
将练习迁移到其他 Fabric 前，应确认接入/Trunk 成员关系正确、LAG 成员符合预期、STP 转发拓扑符合预期。

**Underlay** 提供 VTEP 之间的 IP 可达性。无论租户使用什么地址，Underlay 的路由、返回路径和可用 MTU 都必须独立正常。
**Overlay** 在这些 VTEP 之间承载租户流量；VXLAN 会额外封装外层 Ethernet/IP/UDP/VXLAN 标头。
外层目标地址是远端 VTEP，而不是租户主机；VNI 在 VXLAN 标头中标识一个虚拟网段。
VLAN ID 只在本地有意义；必须核实其到 VNI 的映射；不能假设 VLAN ID 和 VNI 数值相同。

## 2. 区分标识符、路由和转发

| 概念 | 含义 | 应查找的证据 |
|---|---|---|
| VTEP | 封装/解封装端点 | 本地地址、远程可达性、VXLAN 接口 |
| L2VNI / MAC-VRF | 桥接的租户网段 | VLAN/bridge 映射、学习到的远端 MAC 和 VTEP |
| L3VNI / IP-VRF | 路由租户上下文 | VRF 路由表、传输 VNI 和远端前缀 |
| RD | 区分原本可能重叠的 VPN 路由身份 | 起源路由的 RD |
| RT | 用于导入/导出策略的扩展团体属性成员标识 | 通告的导出 RT 和接收方生效的导入 RT 集合 |
| SVI / IRB | 在桥接域边界执行路由 | 网关地址/MAC、SVI 到 VRF 的绑定及路由探测 |

不同 RD 可以属于同一个 VPN；RD 相同并不授予成员资格。
RT 不是数据包防火墙。意外导入路由可能创建可达性，但仅有路由仍不能证明转发成功。
在非对称 IRB 中，入口侧执行路由，远端侧桥接到目标网段；参与网关需要有相关目标 L2 状态。
在对称 IRB 中，两端都会执行租户路由，并在它们之间使用 L3VNI。
不要仅因 BGP 有 EVPN 地址族，就推断使用了对称 IRB。

| EVPN 路由 | 本练习中的作用 | 其存在不能证明什么 |
|---|---|---|
| Type 2：MAC/IP 通告 | 通告 MAC，可选地附带对应 IP；支持远端主机信息 | 每个已通告 MAC 都安装在正确 bridge 中 |
| Type 3：IMET | 通告参与信息，用于构建 BUM 传递（例如入口复制） | 单播主机转发或租户路由正常 |
| Type 5：IP 前缀 | 独立于特定主机 MAC 通告，承载租户 IP 可达性 | 接收方导入了该前缀或能到达其 VTEP |

BUM 表示广播、未知单播和组播；VTEP 的复制状态与其 Type-3 路由同样重要。
报告中应区分全局 EVPN 路由、每个 VNI/VRF 的导入状态和实际转发证据。

## 3. 选择可复现的上游实验

使用 [netlab 主页](https://netlab.tools/)链接的示例仓库，修订版本为 **`7c4fa0dac160d3cc2eac41e11f20b74d083bb896`**：

| 阶段 | 上游准确路径 | 预期基线 |
|---|---|---|
| A：L2 | [EVPN/vxlan-bridging](https://github.com/ipspace/netlab-examples/tree/7c4fa0dac160d3cc2eac41e11f20b74d083bb896/EVPN/vxlan-bridging) | 红色网段中的 h1↔h2 可通；蓝色网段中的 h3↔h4 可通；VLAN 之间无路由 |
| B：L3 | [EVPN/l3vpn](https://github.com/ipspace/netlab-examples/tree/7c4fa0dac160d3cc2eac41e11f20b74d083bb896/EVPN/l3vpn) | 红 VRF 中路由转发的 h1↔h2 可通；蓝 VRF 中的 h3↔h4 可通；不跨 VRF 导入 |

两阶段都使用 `clab`、两台交换机 s1/s2、四台 Linux 主机以及运行 AS65000 EVPN 的 OSPF Underlay。
阶段 A 的上游配置明确选择 EOS 和 Cumulus；阶段 B 默认使用 EOS。
**本文明确选择：分别将 s1 和 s2 覆盖为 `frr`**，使用文档中的 `-s nodes.s1.device=frr -s nodes.s2.device=frr` [启动选项](https://netlab.tools/netlab/up/)。
[EVPN 支持矩阵](https://netlab.tools/module/evpn/#platform-support)列出了 FRR 对基于 VLAN 的 EVPN、对称 IRB 和 iBGP/IGP 的支持。
该矩阵并不保证所有旧镜像或提供程序组合均可用。

每个阶段使用**一台专用虚拟机**；或者在导出证据后，在阶段之间恢复到由你管理的空虚拟机检查点。
不要在共享主机上同时启动两个身份/实验标识会冲突的副本。
阶段 B 使用路由主机链路和传输 VNI；这是 L3VPN 练习，**不是**接入 VLAN 任播网关或主机移动性练习。
通过阅读材料理解 IRB 的区别；如果所选的纯 L3 模型并不要求 Type-2/3 或任播测试，不要报告这些测试通过。

## 4. 实验专属先决条件和记录

- 使用由你拥有、能通过控制台访问的 x86-64 Ubuntu 24.04 Linux 虚拟机。每个活动的六容器阶段可按 4 vCPU、8 GiB 内存和 20 GiB 空闲磁盘规划；请测量实际用量。
- 按照 [netlab Ubuntu 设置](https://netlab.tools/install/ubuntu/)和 [containerlab 提供程序设置](https://netlab.tools/labs/clab/)完成实验前准备，包括 Docker、Ansible 依赖项和节点镜像。
- 使用声明支持所选 FRR EVPN/VXLAN/VRF 功能的 netlab 版本。记录准确版本、示例修订版本以及两个节点覆盖设置。
- 检查过的 netlab [FRR 设备定义](https://github.com/ipspace/netlab/blob/4d85d13365caf3962a72ba59ec57a2e4450f365f/netsim/devices/frr.yml)选择 `quay.io/frrouting/frr:10.6.1`；本文中的 CLI 示例已按 FRR 10.6.1 核对。请记录实际安装版本使用的镜像和摘要，不要假定版本一致。
- FRR/clab 需要虚拟机内核支持 bridge、VXLAN，以及阶段 B 所需的 VRF。上游设置可能会在**这台由你拥有的虚拟机**上加载模块。无法加载所需模块的受限 Codespace 不能替代此环境。
- 在虚拟机上准备 iproute2、iputils、tcpdump 和 GNU `timeout`。对于 DF/大小探测，在记录过的节点命名空间中使用虚拟机的 iputils；不能假定 Alpine 主机镜像中的 BusyBox `ping` 支持这些选项。
- FRR 和所选 Linux 主机镜像均不要求商业路由器许可证。若保留 EOS/Cumulus，就属于不同的平台选择，需要另行满足镜像访问、许可和 CLI 要求。
- 虚拟机所有者负责提供 Docker/提供程序权限；`vtysh` 和命名空间操作需要相应实验权限。不要更改管理接口、工作站路由或云设置。

在**阶段 A 虚拟机 Shell**中，确认目标目录不存在后执行：

```bash
test ! -e "$HOME/expert-fabric-examples"
git clone --no-checkout https://github.com/ipspace/netlab-examples.git "$HOME/expert-fabric-examples"
git -C "$HOME/expert-fabric-examples" checkout --detach 7c4fa0dac160d3cc2eac41e11f20b74d083bb896
cd "$HOME/expert-fabric-examples/EVPN/vxlan-bridging"
git rev-parse HEAD
git status --short
sha256sum topology.yml
python3 -c 'from importlib.metadata import version; print(version("networklab"))'
containerlab version
docker version
ansible --version
uname -r
```

如果检查发现目标已存在，应停止，不要继续。此克隆是新的自有对象；在释放该虚拟机之前，应与证据一起保留。
在单独的阶段 B 虚拟机上重复克隆/修订版本流程，然后将 `EVPN/l3vpn` 作为其工作目录。
在两个阶段收集观测前，所有者都必须使用提供程序 `clab` 和两个 FRR 节点覆盖设置，完成官方启动流程。
记录空虚拟机检查点、生成的实验身份、准确启动选项和健康的实验前检查点。
此设置负责创建 bridge/VTEP/VRF：[FRR 本身不会创建 Linux 接口](https://docs.frrouting.org/en/latest/evpn.html#the-linux-vxlan-dataplane)。
不要把独立的 BGP 设置粘贴进空容器，就称其为已运行的 Overlay。

## 5. 验证身份和数据平面就绪情况

在当前阶段的**虚拟机 Shell**中：

```bash
netlab status
netlab inspect nodes.s1.interfaces
netlab inspect nodes.s2.interfaces
netlab connect --dry-run s1
netlab connect s1 --show version
netlab connect s1 --show running-config
netlab connect s1 --show ip ospf neighbor
netlab connect s1 --show bgp l2vpn evpn summary
netlab connect s1 --show evpn vni
netlab connect s1 --show bgp l2vpn evpn vni
netlab connect s1 ip -d link show
netlab connect s1 bridge link show
netlab connect s1 bridge fdb show
netlab connect s1 ip route show
```

在 s2 上重复只读状态检查。使用 [inspect](https://netlab.tools/netlab/inspect/)和 [connect](https://netlab.tools/netlab/connect/)参考文档理解节点/接口映射。
`netlab connect s1` 会进入 **FRR 容器的 Linux Shell**；输入 `vtysh` 才会进入 FRR CLI。
`s1#` 表示 FRR 操作模式；`configure terminal` 进入配置模式，`end` 退出配置模式，`exit` 从操作模式返回 Linux。
在 Linux 中使用 `ip`/`bridge`，在 FRR 中使用 `show`，也可使用前文所示虚拟机侧的 `--show` 包装器。

使用 `docker inspect --format '{{.Config.Image}} {{.Image}}' CONTAINER` 记录每个准确容器的镜像；逐一检查具名的实验对象。
确认存在真实 VXLAN 接口及其本地 VTEP 地址、bridge 成员关系、运行中的 VNI，以及到远端 VTEP 的可达性。
阶段 B 还应检查 `show vrf vni`、Linux VRF 设备/路由表和主机链路属于红色还是蓝色。
当前 [FRR 注意事项](https://netlab.tools/caveats/#frrouting)指出，VLAN/VRF 初始化不是幂等的，而且配置收集不会包括 Linux 接口状态。
先决条件不满足时，不要反复重放初始化进行修复；应保留失败证据并回到自有实验设置检查点。

依据实际输出填写此映射表；不要凭记忆填写：

| 主机 | 数据 IP/前缀 | 接入 VLAN 或路由链路 | VRF | L2VNI / L3VNI | 本地/远端 VTEP | 抓包接口 |
|---|---|---|---|---|---|---|
| h1 | 记录 | 阶段 A 红色 / 阶段 B 路由链路 | 记录 | 记录或说明不适用 | 记录 | 记录 |
| h2 | 记录 | 阶段 A 红色 / 阶段 B 路由链路 | 记录 | 记录或说明不适用 | 记录 | 记录 |
| h3/h4 | 分别记录 | 蓝色 | 记录 | 记录或说明不适用 | 记录 | 记录 |

## 6. 阶段 A：证明 L2 转发与隔离

通过 `netlab connect h1 ip address show` 查看 h1/h2/h3/h4 的数据地址；每次只替换为一台准确主机。
该命令在主机容器中执行；在虚拟机上安装 iproute2 不会改变容器内 BusyBox 的实现。使用数据地址，不要使用管理地址或可能解析到管理地址的未解析主机名。
在虚拟机 Shell 中，根据映射表替换以下占位符：

```bash
fabric_h2='REPLACE_WITH_H2_DATA_IPV4'
fabric_h3='REPLACE_WITH_H3_DATA_IPV4'
fabric_h4='REPLACE_WITH_H4_DATA_IPV4'
netlab connect h1 ping -c 5 -W 1 "$fabric_h2"
netlab connect h3 ping -c 5 -W 1 "$fabric_h4"
netlab connect h1 ping -c 5 -W 1 "$fabric_h3"
netlab connect s1 --show bgp l2vpn evpn route type 2
netlab connect s1 --show bgp l2vpn evpn route type 3
netlab connect s1 bridge fdb show
```

应先从预期的主机生成流量，再查看远端 Type-2/MAC 学习结果。
将每个远端 MAC 与正确的 VNI 和 VTEP 关联；Type-3/复制状态必须对应预期网段。
前两项探测应成功。在此无路由设计中，跨 VLAN 探测应失败。
仅有失败结果还不够：还必须确认两个正向控制均成功、主机接入正确，且不存在意外路由路径。
记录负向探测是因为本地缺少路由而失败，还是已到达数据平面边界；这是两种不同的观测。

从清单中确认 s1 的交换机间接口；在本文固定的阶段 A FRR 映射中，该接口为 `eth3`。
在另一个终端中重复一个允许的探测，同时只抓取这条由你管理的接口：

```bash
timeout 20s netlab capture s1 eth3 -nn -e -vv -l -c 30 udp port 4789
```

保存外层 VTEP 对、VNI 以及内层 MAC/IP 对。没有输出、抓包错误或管理流量都不构成证明。
解释观测到的封装如何与路由和 FDB 证据相符。
不要为了满足检查表而期待这个纯桥接练习中出现 Type-5 租户前缀。

## 7. 阶段 B：证明路由 VRF 服务

切换到单独准备的阶段 B 虚拟机，并重新建立身份/地址映射。
将 `fabric_h2`、`fabric_h3`、`fabric_h4` 变量重新赋值为**阶段 B**地址；阶段 A 的值不能复用作为证据。
重复第 6 节中的三个探测：红色和蓝色主机对应该互通，跨 VRF 流量不应互通。
还要检查：

```bash
netlab connect s1 --show vrf vni
netlab connect s1 --show bgp l2vpn evpn route type 5
netlab connect s1 --show bgp vrf red ipv4 unicast
netlab connect s1 --show ip route vrf red
netlab connect s1 ip -d link show type vrf
netlab connect s1 ip route show vrf red
```

在 Type-5 表中找到 h2 实际的远端子网、其 RD/导出 RT、导入红色 VRF 的情况，以及对应的 Linux 路由。
单独检查蓝色 VRF。确认红色 VRF 未导入蓝色路由，并检查 s2 上的返回路由。
按照第 6 节抓取 Underlay，但应使用**阶段 B 的实际接口**；该接口不一定是 `eth3`。
将传输 VNI 与 VRF 对应起来；管理网络 ping 成功不代表租户路由服务正常。

## 8. 阶段 B：移除一个导入成员关系，然后恢复

自有对象：**s1 的红色 VRF EVPN 导入 RT 列表**。保留其准确运行配置和生效 RT 列表。
使用 `netlab connect s1 --show bgp l2vpn evpn vni RED_L3VNI` 检查导入/导出 RT 详情；将 `RED_L3VNI` 替换为记录的红色传输 VNI 数字。
先决状态必须是一个明确的导入 RT（下文名为 `RED_RT`），并且没有会导入相同路由的通配符或额外自动导入设置。
只有确认实验路由没有通告 `BAD_RT` 且现有列表没有使用它后，才能选择 `65000:424242` 作为 `BAD_RT`。
如果先决状态不同，不要自行删除其他条目。
在 s1 的 **FRR CLI** 中使用实际的 `RED_RT`，不要照抄占位符：

```text
configure terminal
router bgp 65000 vrf red
 address-family l2vpn evpn
  route-target import 65000:424242
  no route-target import RED_RT
 exit-address-family
end
```

先添加未使用的 RT，再删除原 RT，可以使显式列表在整个操作中保留。
如果不做此保护就删除唯一的手动 RT，可能会恢复自动 RT，从而使实验无效。
不同 FRR 版本控制自动 RT 的方式不同；请使用 VNI 详情和[与运行时匹配的 RT 文档](https://docs.frrouting.org/en/latest/bgp.html)核实**生效的**导入集合。
如果原 RT 仍然生效，应将注入判定为未实现并恢复原状；不要声称已测试隔离。

预期结果是全局 Type-5 通告和 BGP 会话仍然存在，但 h2 的远端前缀会从 s1 的红色 VRF/FIB 消失，红色探测会失败。
要求蓝色主机对仍然互通，且 h2 仍能到达本地红色网关；主机宕机或 Underlay 故障不能证明 RT 隔离有效。
在全局表和导入表中查看准确前缀，并保留负向探测的退出码/输出。
恢复同一个对象；先添加原成员关系，再删除临时成员：

```text
configure terminal
router bgp 65000 vrf red
 address-family l2vpn evpn
  route-target import RED_RT
  no route-target import 65000:424242
 exit-address-family
end
```

确认原有生效 RT 集合、远端路由、红色探测和蓝色控制均已恢复；不要更改 RD、邻居或导出 RT。

## 9. 阶段 B：测量 Underlay MTU 行为

自有对象：**s1 的交换机间数据接口 MTU**。上游阶段 B 链路请求 MTU 为 1600；继续前先确认所选接口的实际值为 1600。
记录该接口不是管理/接入/bridge/VXLAN 接口，并确认其对端为 s2。
在第二台虚拟机终端中准备恢复命令。根据本阶段映射替换接口、h1 命名空间和 h2 数据地址：

```bash
fabric_underlay='REPLACE_WITH_S1_TO_S2_INTERFACE'
fabric_h1_ns='REPLACE_WITH_THIS_LABS_H1_NAMESPACE'
fabric_h2='REPLACE_WITH_H2_DATA_IPV4'
netlab connect s1 ip -d link show dev "$fabric_underlay"
sudo ip netns exec "$fabric_h1_ns" ip -br address
sudo ip netns exec "$fabric_h1_ns" ping -n -M do -s 1200 -c 5 -W 1 "$fabric_h2"
sudo ip netns exec "$fabric_h1_ns" ping -n -M do -s 1400 -c 5 -W 1 "$fabric_h2"
```

确认两种基线探测大小都成功。虚拟机的 [iputils ping](https://github.com/iputils/iputils/blob/master/doc/ping.xml) 提供 `-M do`；不假设会在主机容器内部安装软件包。
对于没有 VLAN 标记、外层使用 IPv4 的 Ethernet，1400 字节 ICMP 载荷会形成 1428 字节的内层 IP 数据包，封装后外层 IP 数据包约为 1478 字节。
记录实际 VLAN 标记/标头；使用 IPv6 传输或额外封装会改变预算。

仅更改记录的 MTU，然后重复两种探测，并同时抓取 Underlay：

```bash
netlab connect s1 ip link set dev "$fabric_underlay" mtu 1400
timeout 20s netlab capture s1 "$fabric_underlay" -nn -vv -l -c 30 'ip proto 17 or icmp'
```

小型探测可能成功，而较大的探测可能被丢弃或外层数据包可能发生分片；内层 DF 标志本身不能保证外层也会设置 DF。
IPv4 协议过滤器会包含后续 UDP 分片；仅按端口过滤可能会漏掉它们。使用记录的 VTEP 对和首个分片识别 VXLAN。
OSPF 也可能会对 MTU 不匹配作出反应。记录邻居状态、错误、分片和 ICMP 反馈，不要坚持认为 BGP 必须始终保持建立状态。
如果没有观察到对数据包大小敏感的影响，就如实报告并调查封装/分片/卸载情况；不要虚构黑洞。
在有界采集结束后立即恢复：

```bash
netlab connect s1 ip link set dev "$fabric_underlay" mtu 1600
netlab connect s1 ip -d link show dev "$fabric_underlay"
```

重新检查 OSPF/BGP、两种探测大小、两个 VRF 正向控制和跨 VRF 负向断言。
不要为了得到看起来干净的结果而清空路由、邻居表或所有 bridge。

## 10. 证据与完成标准

| 测试 | 正向控制 | 预期的负向证据 | 恢复证明 |
|---|---|---|---|
| L2 分段 | 同 VLAN 的两对主机均可通信，VXLAN/FDB 正确 | 不提供路由服务时跨 VLAN 被阻止 | 恢复原映射并重做探测 |
| L3 VPN | Type-5 导入到正确 VRF，租户探测成功 | 其他 VRF 不在导入/FIB 中，探测受阻 | 恢复原路由/探测矩阵 |
| RT 不匹配 | 蓝色仍可通信，目标主机/本地网关正常 | 全局路由存在，但缺少红色导入且红色探测失败 | RT 列表、路由和红色探测准确恢复 |
| 降低 MTU | 基线大小和 Underlay 正常 | 观测到数据包大小/分片/邻接影响，或明确记录未复现 | MTU 恢复为 1600 并重新验证完整基线 |

每一行都应保留阶段、时间戳、虚拟机/实验身份、上游修订版本、工具/镜像版本、节点/接口、预期结果、实际输出和结论。
使用 **PASS**、**FAIL**、**BLOCKED** 或有理由的 **N/A**；空路由表、没有探测结果或缺少抓包本身都不能单独判为 PASS。
根据所选模型标注 Type/功能不适用，不要把它作为必需测试故障时的替代方案。
所有活动更改都必须在明确命名的对象上撤销；如果撤销失败，请保留证据，并且只恢复记录过的自有虚拟机检查点。
不要保存实验更改；不要重放非幂等初始化，也不要执行整个实验的清理/全局剪枝。
完成时，你应能够跟踪 L2 和 L3 服务、解释 RD/RT 和路由类型、用正常工作的控制证明隔离，并展示恢复结果。
继续学习 [Linux 性能](04-linux-performance.md)、[云/CNI 设计](05-cloud-cni-design.md)、[自动化综合练习](06-automation-capstone.md)和[测验](../../quizzes/networking/expert/03-datacenter-evpn-quiz.md)。
