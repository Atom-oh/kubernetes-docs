# 02. 路由策略与收敛测量

> **最后更新**：2026 年 9 月 15 日
> **实验范围**：一台单独准备、由自己负责且可丢弃的 Linux 路由虚拟机；仅使用本地 FRRouting 容器。
> **验证状态**：已检查上游文档、拓扑和 CLI 源码；编写本章时**未实际执行**路由实验。

完成本工作手册后，你应能够解释为什么选中了某个前缀，证明其下一跳可用，并测量受控故障期间流量经历了什么。
首先完成全部[八节初级课程](../beginner/README.md)，包括[容器/云综合实训](../beginner/08-container-cloud-capstone.md)。
当协议路由表中的路由无法解释数据包路径时，请重新阅读[Linux 转发](../../kernel/02-network-stack.md)。

## 1. 带着要回答的问题阅读

| 阅读材料 | 用自己的话回答的问题 |
|---|---|
| [BGP 实验概览](https://bgplabs.net/)和[FRRouting 简介](https://bgplabs.net/basic/0-frrouting/) | 哪些操作应在 Linux shell 中执行，哪些操作应在 `vtysh` 中执行？ |
| [Local-preference 实验](https://bgplabs.net/policy/5-local-preference/) | 为什么在一端边缘设置的优先级会影响另一端边缘？ |
| [FRR BGP 手册](https://docs.frrouting.org/en/latest/bgp.html) | 收到的路径何时具备资格、被选中、通告和安装？ |
| [FRR OSPF 手册](https://docs.frrouting.org/en/latest/ospfd.html) | 邻接关系证明了什么？IGP 会携带哪些前缀？ |
| [RFC 4271](https://www.rfc-editor.org/rfc/rfc4271.html)和[RFC 4456](https://www.rfc-editor.org/rfc/rfc4456.html) | 常规 iBGP 通告规则与路由反射有何不同？ |

配置之前先阅读选定章节。绘制一张拓扑图，分别标出路由会话和转发链路。
BGP 会话是 BGP 对等体之间的 TCP 连接；这并不代表每个已通告的目的地都能经该连接到达。

## 2. 建立控制平面模型

**IGP 和 BGP 解决的是不同问题。** OSPF 在一个管理域内分发链路状态信息，并按开销计算路径。
在本实验中，它提供内部可达性，包括 iBGP 使用的 loopback 地址。
BGP 通过属性交换目的地可达信息并应用策略；它不只是 OSPF 的“最短跳数”替代品。
在两个协议之间盲目重分发所有路由会引入额外路由、策略歧义和潜在反馈。

**eBGP** 通常在不同自治系统之间交换路由；**iBGP** 在同一自治系统内分发 BGP 信息。
AS_PATH 有助于检测 AS 级环路，而常规 iBGP 通告限制可以防止简单的内部重通告环路。
iBGP 学到的路由通常不会再通告给另一个 iBGP 对等体；需要全互联、路由反射器或其他有意设计的方案。
不要根据这些会话连接关系推断数据转发拓扑。

**下一跳解析是有效转发的前提。** BGP 路由可能可见，但由于其下一跳没有可达路由而无法使用。
iBGP 下一跳可能仍然是外部地址，除非通过 `next-hop-self` 等设计改变它。
应检查实际收到的 NEXT_HOP，再通过路由表递归解析到接口和邻居。
OSPF 邻接关系本身不能证明所需的下一跳前缀已被通告。

| 层级 | 证据 | 该证据无法证明的内容 |
|---|---|---|
| BGP 会话 | 状态和已协商的地址族 | 预期前缀已被接受 |
| BGP RIB | 候选路径、属性、有效性和最佳路径标记 | 所选路由已进入转发平面 |
| Zebra 路由表 | 所选路由及其安装状态 | 数据包确实从预期接口发出 |
| Linux FIB 查询 | 某目的地对应的路由、出接口和下一跳 | 返回路径可达，或不存在分组过滤 |
| 分组观测 | 指定源地址的探测和接口抓包 | 每种应用、分组大小或 ECMP 路径都能正常工作 |

报告中应明确区分“BGP 表”和“内核转发表”，不要把两者都笼统称为“路由表”。
FRR 通过 Zebra 传递路由决策；本实验的转发由所选软件数据平面中的 Linux 执行。

## 3. 在测试策略前先解释它

| 机制 | 运维目的 | 常见错误推断 |
|---|---|---|
| 前缀过滤器 | 只接受或通告预期前缀及前缀长度 | 允许 `/24` 就会自动允许所有更具体的路由 |
| LOCAL_PREF | 表达 AS 内部出口优先级；数值越大优先级越高 | 它会告诉外部 AS 应从哪个入口进入 |
| Weight | 单台路由器上的本地实现专属优先级 | 它会作为 BGP 属性传播给其他路由器 |
| AS_PATH / 路径预置 | 描述 AS 路径；在接收方策略允许时影响路径选择 | 路径较短总会胜过更高的 local preference |
| MED | 根据接收方比较规则提示入口优先级 | 所有相邻 AS 都会无条件进行比较 |
| Community | 携带供接收方策略解读的标签 | 没有匹配策略，标签本身也会强制执行某种行为 |
| 路由反射器 | 通过反射减少 iBGP 会话需求 | 它会补上缺失的下一跳路由，或必然承载中转流量 |

反射器的 ORIGINATOR_ID 和 CLUSTER_LIST 支持环路防护；它的路径选择也可能导致客户端看不到其他路径。
对于被反射的路径，应分别检查客户端、反射器和下一跳可达性。
可将[路由反射器实验](https://bgplabs.net/ibgp/3-rr/)作为之后单独准备的练习；不要将反射器加入本工作手册的拓扑。

先在纸面上写出以下过滤器设计，不要部署：向上游仅导出 `192.168.42.0/24`。
精确匹配 `/24` 后应接受该路由、拒绝 `192.168.42.0/25`，并拒绝学到的提供商前缀 `192.168.100.0/24`。
除非另有明确合同允许，否则还应拒绝 `0.0.0.0/0`。
解释隐式拒绝、评估顺序以及过滤器的应用方向。
接下来可使用[过滤通告前缀](https://bgplabs.net/policy/3-prefix/)进行实际过滤器练习；不要假设本实验现有策略已经实现了你提出的过滤器。

## 4. 准备此实验

所选上游实验为 **`bgplab/bgplab`、`policy/5-local-preference/topology.yml`**，修订版 **`5a9fab68658ce69317b147396481714ee3478482`**。
四台路由器分别是 AS65000 中的 c1/c2，以及 AS65100 中的 x1/x2。
拓扑配置了 OSPF、eBGP、iBGP 和路由通告；学习者修改客户侧策略。
[拓扑源码](https://github.com/bgplab/bgplab/blob/5a9fab68658ce69317b147396481714ee3478482/policy/5-local-preference/topology.yml)要求使用 **netlab 2.0.0 或更高版本**。

检查日期时，`https://bgplabs.net/install/` 返回 404；请改用官方[安装与设置](https://bgplabs.net/1-setup/)页面。
启动本工作手册前，应按照其[Ubuntu 安装前提条件](https://netlab.tools/install/ubuntu/)在这台单独的虚拟机中完成准备。
不要复用初级课程的虚拟机、共享 Docker 主机或 Kubernetes 节点。

- 准备一台由自己负责的 x86-64 Ubuntu 24.04 虚拟机。四个 FRR 容器和工具的资源**规划余量**为 4 vCPU、8 GiB 内存和 20 GiB 可用磁盘；这不是上游规定的最低要求或基准测试结果。
- 按照上游说明准备 netlab、其 Ansible 依赖、Docker 和 containerlab（`clab` provider）、Git、iproute2、iputils `ping`、GNU `timeout` 和 tcpdump。
- 记录已安装的 netlab 发行版和 provider 版本。使用该 netlab 发行版所选的 FRR 镜像；记录标签、镜像 ID/摘要和实际的 `show version` 输出。
- CLI 示例依据 FRR **10.6.1** 源码检查。使用其他运行时发行版前，必须在变更之前检查其命令帮助；笼统的“FRR 镜像”并不能保证兼容性。
- 此处选择的 FRR 是开源软件；无需商业路由器许可证。下载镜像和准备工具仍需要网络访问。
- Provider 管理需要在这台可丢弃虚拟机上使用特权；FRR 容器中的 Linux shell/`vtysh` 使用 root。保持虚拟机控制台可用，并不要修改管理接口。
- 明确由你独占负责虚拟机、克隆目录和实验名称。客户/提供商链路是模拟的本地链路，不会连接 ISP 或互联网。

在**实验虚拟机的 shell**中创建一个新克隆；目标目录必须尚不存在：

```bash
test ! -e "$HOME/expert-routing-bgplab"
git clone --no-checkout https://github.com/bgplab/bgplab.git "$HOME/expert-routing-bgplab"
git -C "$HOME/expert-routing-bgplab" checkout --detach 5a9fab68658ce69317b147396481714ee3478482
cd "$HOME/expert-routing-bgplab/policy/5-local-preference"
git rev-parse HEAD
git status --short
sha256sum topology.yml
python3 -c 'from importlib.metadata import version; print(version("networklab"))'
containerlab version
docker version
ansible --version
uname -r
```

如果确认目录不存在的检查失败，应停止操作；不要在已有目录上继续执行克隆命令。
将这些命令的输出记录在克隆目录以外的证据记录中。
只有在负责人根据上游流程、在此目录中使用 `provider=clab`、客户设备 `frr` 和外部设备 `frr` 启动后，准备阶段才算完成。
上游启动操作会创建/配置实验环境；它是前提步骤，并非只读命令。
应由虚拟机所有者记录生成的节点/容器身份，并保存一份属于自己的实验前虚拟机检查点。
本章作者没有执行启动、安装、主机配置或拆除操作。

## 5. 就绪状态与终端边界

在**同一个实验目录的虚拟机 shell**中运行：

```bash
netlab defaults --project
netlab status
netlab connect --dry-run c1
netlab connect c1 --show version
netlab connect c1 --show running-config
netlab connect c2 --show bgp ipv4 unicast summary
netlab connect c1 --show ip ospf neighbor
netlab connect c2 --show ip ospf neighbor
```

`netlab defaults --project` 要求 netlab 2.0.1 或更高版本；使用 2.0.0 时应检查克隆出的 `defaults.yml`。
[connect 参考文档](https://netlab.tools/netlab/connect/)介绍了单节点访问和 `--show`。
对于此 FRR/clab 选择，`netlab connect c1` 会打开 **c1 的 Linux shell**；输入 `vtysh` 会打开 **c1 的 FRR CLI**。
下方提示符是说明标签，不要把它们作为命令粘贴：

```text
lab-vm$ netlab connect c1
c1-linux# vtysh
c1# show version
c1# show running-config
c1# exit
c1-linux# exit
```

应在 Linux shell 中运行 `ip`、`ping` 和 shell 命令，而不是在 `c1#` 提示符下。
`configure terminal` 会进入 FRR 配置模式；`end` 会返回 FRR 运维提示符。
在虚拟机中运行 `netlab connect c1 --show ip route` 会调用正确的 FRR 封装命令；不要将原始 `show` 命令发送到 Linux shell。

就绪标准包括：iBGP/eBGP 会话确实已建立、预期 OSPF 邻居已建立、c2 上存在两条符合条件的提供商路径，以及有界探测成功。
应使用 `docker inspect --format '{{.Config.Image}} {{.Image}}' CONTAINER` 分别检查**已记录的 c1、c2、x1 和 x2 容器身份**所使用的镜像。
不要以全主机容器列表代替这些节点版本的证据。

## 6. 基线：预测、观测、解释

在固定修订版中，c1 的外部对等体为 `10.1.0.2`；c2 的为 `10.1.0.6`。
iBGP loopback 地址为 `10.0.0.1` 和 `10.0.0.2`；客户网段为 `192.168.42.0/24`。
使用这些值前，应根据实际运行配置进行验证。
探测目标 `192.168.100.10` 是 x1 在模拟提供商网段上的地址。

```bash
netlab connect c2 --show bgp ipv4 unicast 192.168.100.0/24
netlab connect c2 --show ip route 10.0.0.1/32
netlab connect c2 --show ip route 192.168.100.0/24
netlab connect c2 ip route get 192.168.100.10
netlab connect c2 ping -I 192.168.42.2 -c 5 -W 1 192.168.100.10
netlab connect c1 --show bgp ipv4 unicast neighbors 10.1.0.2 advertised-routes
```

记录两条候选路径、下一跳、AS_PATH、LOCAL_PREF、最佳路径原因和内核路由查询结果。
解释 c2 选择的是直接连接的上游，还是经由 c1 的出口。
在通告输出中，按你提出的导出允许列表对每个实际前缀进行分类；发现意外通告属于调查结果，并不证明你提出的过滤器已经运行。
在因缺少响应而归咎于出站策略前，先检查 x1 返回 `192.168.42.0/24` 的路由。

## 7. 更改一侧客户路由器的出口优先级

初始状态：c1 的 AS65000 实例中**没有显式配置** `bgp default local-preference`，有效默认值为 100，并且没有入站策略覆盖正在检查的提供商路由。
c2 的基线有效值也为 100。保留两台路由器的原始配置。
如果不符合这些条件，应停止实验并建立适当的基线，而不是删除已有策略。

由你负责的对象是**c1 的 AS65000 BGP 实例**；逆操作只需移除此处新增的设置。
在 c1 的 **FRR CLI** 中：

```text
configure terminal
router bgp 65000
 bgp default local-preference 200
end
show bgp ipv4 unicast 192.168.100.0/24
```

该 FRR 命令已通过[10.6.1 CLI 实现](https://github.com/FRRouting/frr/blob/frr-10.6.1/bgpd/bgp_vty.c)核实；该实现也会重新处理此实例中的入站路由。
不要在共享环境中复制上游的通配清除示例。
在 c2 上重新执行第 6 节：预期经 c1 的合格路径携带 200，并胜过值为 100 的路径；随后应能看到相应的 FIB 路由和分组路径。
如果属性没有变化，应检查入站策略、下一跳有效性和实际运行时版本；仅看到一行配置并不算 PASS。
本工作手册有意只修改 c1，因此上游验证器单独预期 c2=50，**并不是**本工作手册的验收标准。

## 8. 测量一次对等体故障

保持优先级实验设置不变。初始状态：**c1 的邻居 `10.1.0.2`** 已建立且没有 `shutdown` 设置。
逆操作：在同一个 BGP 实例中执行 `no neighbor 10.1.0.2 shutdown`。
这是管理性关闭对等体，不是断线、静默丢包或 BFD 实验。

时间戳探测应使用虚拟机 iputils，并在**c2 已记录的容器网络命名空间**内运行。
从本实验的 inventory/provider 映射中获取命名空间名称，并用 `ip netns list` 确认它存在；不要使用宽泛的通配符来选择。
在第二个虚拟机终端中运行前，先替换占位符：

```bash
routing_c2_ns='REPLACE_WITH_THIS_LABS_C2_NAMESPACE'
sudo ip netns exec "$routing_c2_ns" ip -br address
sudo ip netns exec "$routing_c2_ns" ping -D -O -n -I 192.168.42.2 -i 0.2 -c 150 -w 40 -W 1 192.168.100.10
```

确认显示地址与 c2 匹配。注入故障前，应先成功收到多个响应。
[iputils `-O` 选项](https://github.com/iputils/iputils/blob/master/doc/ping.xml)会报告尚未收到响应的请求；应将序列号与稍后到达的响应对应起来，不要把每个等待中的报告都当作永久丢包。
在 c1 的 FRR CLI 中记录干预时间，然后执行：

```text
configure terminal
router bgp 65000
 neighbor 10.1.0.2 shutdown
end
```

在虚拟机中，在有界探测窗口期间按照第 6 节的方式采样 c2 的 BGP 前缀和内核路由。
在另一终端中，使用[抓包命令](https://netlab.tools/netlab/capture/)检查 **c2 已确认的备用数据接口**；固定 FRR 拓扑将其映射到 `eth2`：

```bash
timeout 20s netlab capture c2 eth2 -nn -l -c 40 icmp
```

超时只会限制采集时长；没有匹配分组或遇到访问错误并不代表抓包成功。
预期 c2 会选择 x2，然后通过提供商内部网段到达 x1。
应区分 `t_action`、首次观测到路由撤销/变更的时间、FIB 变更时间、最后一次失败探测以及首次持续恢复的时间。
事先定义持续恢复，例如连续收到五个响应；报告采样间隔和不确定性。
探测与干预记录使用同一虚拟机时钟；应在 CLI 操作之前立即记录虚拟机 shell 的 `date -u +%FT%T.%NZ`，并将人工终端延迟计入不确定性。
如果采样率下观察到的丢包数为零，这只表示没有测到持续时间的故障，不表示收敛时间为零。
Hold timer、BFD、graceful restart、故障检测、路由处理和 FIB 编程都可能影响结果；不要断言存在通用的固定收敛时间。

## 9. 恢复、重复并提交

先恢复**对等体**，在 c1 的 FRR CLI 中执行：

```text
configure terminal
router bgp 65000
 no neighbor 10.1.0.2 shutdown
end
```

确认对等体重新建立、首选路由恢复且探测正常。
然后恢复**策略对象**：

```text
configure terminal
router bgp 65000
 no bgp default local-preference
end
```

重新检查运行配置、两条候选路由、有效优先级、FIB 查询结果和原始源地址指定的探测。
不要将实验设置保存到启动配置，不要重启 FRR，也不要运行宽泛清理命令。
如果恢复失败，应停止后续实验并报告发生变化的对象；负责人可以在导出证据后，恢复这台可丢弃虚拟机已记录的检查点。
新克隆应保留为证据；之后仅可由负责人按照其生命周期流程销毁这台由其负责的虚拟机。

| 阶段 | 必须提供的正向证据 | 需保留的反向/失败证据 |
|---|---|---|
| 基线 | 两条符合条件的路径、可用下一跳、探测成功 | 缺少返回路由、下一跳未解析或设置错误 |
| 优先级 | c1 导出的 LOCAL_PREF 为 200、已选出口和对应转发 | 属性未改变或 RIB/FIB 不一致 |
| 对等体故障 | 观测到备用路径且探测持续恢复 | 丢包区间、备用路由缺失、抓包错误 |
| 恢复 | 原始配置和转发行为恢复 | 仍处于 shutdown、策略漂移或持续丢包 |

只有每次恢复检查均通过后，才重复测量故障三次；报告每次样本和观测范围。
保留原始时间戳和输出，不要只保留平均值。所有结果都应标记为实测、计划或受阻。
路由缺失、探测记录缺失或抓包为空，都不能满足正向断言。
当你能够解释策略、下一跳递归解析、“会话已建立就代表服务正常”的反例、测量限制和已验证的恢复过程时，本章才算完成。
接下来阅读 [EVPN](03-datacenter-evpn.md)，然后将 [Calico BGP](../calico/04-bgp-deep-dive.md) 作为 Kubernetes 专项延伸。
将你的矩阵提交到[自动化综合实训](06-automation-capstone.md)，并完成[测验](../../quizzes/networking/expert/02-routing-policy-convergence-quiz.md)。
