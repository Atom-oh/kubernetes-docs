# 从零开始学习 Linux 网络

> **学习环境基线**：Ubuntu Server 24.04 LTS，另提供 Rocky Linux 9 路径
>
> **最后更新**：2026 年 9 月 15 日

本课程从你的第一个终端开始。你将创建文件并安装程序，配置 IP 和 DNS，通过 SSH 连接，设置防火墙规则并观察数据包。最后，你会诊断一个小型 Web 服务，并把所学内容与 Docker、Kubernetes 和云网络联系起来。

你不必记住每条命令。学习目标是能够说明：**你正在修改哪台机器、什么现象可以证明操作成功，以及如何恢复到之前的状态**。

## 课程路线图 {#course-map}

初学者从第 1 课开始。熟悉 Linux 的学习者也需要了解共用实验环境，并在第 2 课识别网络接口。所列时间是包含个人练习的规划估算；实际用时取决于经验。

| 顺序 | 课程 | 学完后可以 | 预计时间 |
|---|---|---|---|
| 1 | [Linux 与命令行](01-linux-cli.md) · [测验](../../quizzes/networking/beginner/01-linux-cli-quiz.md) | 识别发行版，并操作文件、编辑器、软件包和服务 | 2–3 小时 |
| 2 | [地址与网络接口](02-addressing-interfaces.md) · [测验](../../quizzes/networking/beginner/02-addressing-interfaces-quiz.md) | 区分 IP、子网、网关和 DNS 的作用，并识别网卡 | 2–3 小时 |
| 3 | [持久化网络配置](03-persistent-configuration.md) · [测验](../../quizzes/networking/beginner/03-persistent-configuration-quiz.md) | 配置 Netplan 或 NetworkManager，并验证重启和恢复行为 | 3–4 小时 |
| 4 | [DNS 与连通性](04-dns-connectivity.md) · [测验](../../quizzes/networking/beginner/04-dns-connectivity-quiz.md) | 分别排查名称解析、路由、端口和 HTTP | 2–3 小时 |
| 5 | [通过 SSH 远程访问](05-ssh-access.md) · [测验](../../quizzes/networking/beginner/05-ssh-access-quiz.md) | 验证主机密钥、使用用户密钥登录并检查生效的设置 | 2–3 小时 |
| 6 | [防火墙与主机安全](06-firewalls-host-security.md) · [测验](../../quizzes/networking/beginner/06-firewalls-host-security-quiz.md) | 放行必要流量，并说明 SELinux 和 Fail2ban 的作用 | 3–4 小时 |
| 7 | [监控与性能](07-monitoring-performance.md) · [测验](../../quizzes/networking/beginner/07-monitoring-performance-quiz.md) | 观察套接字、数据包和流量，并说明测量的局限 | 2–3 小时 |
| 8 | [综合练习与云网络](08-container-cloud-capstone.md) · [测验](../../quizzes/networking/beginner/08-container-cloud-capstone-quiz.md) | 重现、隔离并恢复小型故障，再选择后续学习方向 | 3–4 小时 |

继续学习前，请完成每课的验收要求，并用自己的话解释测验答案。第 1 课学会软件包操作后，回到[来宾工具准备](#guest-tools)，再学习第 2–4 课。核心练习完成后，再学习内核调优和 CNI 实现方案比较。

## 准备实验虚拟机 {#lab-environment}

### 先准备一台虚拟机

1. 使用 PC 支持的虚拟化应用。操作系统镜像的虚拟 CPU 架构必须与应用支持的架构相符。例如，Arm 机器需要该虚拟化工具支持的 Arm 镜像。
2. 从 [Ubuntu Server 官方下载页](https://ubuntu.com/download/server)选择 **24.04 LTS** 镜像。如果使用其他版本，请重新核对软件包和服务的默认设置。按照[安装指南](https://documentation.ubuntu.com/server/tutorial/basic-installation/)操作，并创建带密码的普通用户。示例使用 `student`；请换成自己的用户名。
3. 每台虚拟机的起始资源可以设为 2 个 vCPU、2 GiB 内存和 20 GiB 磁盘。这只是实验规划建议，不代表性能保证，也不是所有虚拟机监控程序的最低要求。
4. 将第一个 NIC 接入虚拟机监控程序的 **NAT 网络并启用 DHCP**。它提供安装和下载软件包所需的连接，后续练习中保持不变。
5. 通过虚拟机监控程序的**控制台窗口**登录。现在还不需要 SSH。正常关闭来宾系统，并为全新安装创建快照。

第 1 课只需要一台虚拟机。普通容器不能替代拥有完整 systemd 和网络管理器的虚拟机。WSL 可用于练习 Shell，但不要假定它后续的网络和防火墙环境与 Linux 虚拟机相同。

### 从第 2 课起准备两台虚拟机

两台来宾系统都使用 Ubuntu，可以让你专注学习一个发行版。也可以选择 Rocky Linux 9。请使用 [Rocky 官方镜像](https://rockylinux.org/download)和[文档](https://docs.rockylinux.org/)；不必同时学习这两个发行版。

1. 独立安装第二台虚拟机，并分别将来宾系统命名为 `net-client` 和 `net-server`。简单克隆可能会复制机器标识符和 SSH 主机密钥，因此初次设置时请分别安装。
2. 正常关闭两台来宾系统，并为每台添加**第二个 NIC**。
3. 将两个第二 NIC 接入同一个**内部虚拟网络**，例如 `linux-net-lab`。不要将 DHCP 服务器或外部上行链路接入该网络。“桥接”、“NAT”和“仅主机”设置不能互换；请确认所选模式实际连接到哪里。
4. 在虚拟机监控程序设置中记录每个 NIC 的 MAC 地址。启动来宾系统，在第 2 课中用 `ip -br link` 根据 MAC 地址找到对应接口。接口名可能是 `eth1`、`enp0s8` 或 `ens19`；不要照抄接口名。
5. 在第 2 和第 3 课中配置 IP 地址。不要在安装程序中为第二个 NIC 随意添加网关或 DNS 服务器。

| 项目 | 客户端虚拟机 | 服务器虚拟机 |
|---|---|---|
| 作用 | 发送 SSH 和 curl 请求 | 接收 SSH 和 HTTP 请求 |
| 管理 NIC | 保留现有 NAT/DHCP 设置 | 保留现有 NAT/DHCP 设置 |
| 实验 NIC | `192.0.2.10/24` | `192.0.2.20/24` |
| 实验 NIC 网关/DNS | 无 | 无 |
| 恢复访问方式 | 虚拟机监控程序控制台和快照 | 虚拟机监控程序控制台和快照 |

```text
Client lab NIC                       Server lab NIC
192.0.2.10/24 ── internal virtual network ── 192.0.2.20/24
      |                                       |
Separate NAT/DHCP management NIC     Separate NAT/DHCP management NIC
```

`192.0.2.0/24` 是本文仅用于隔离本地网络的文档示例地址段，不是可在公共网络中路由的网络设计。管理 NIC 仍会将来宾系统连接到另一个网络，因此不能据此认为整台虚拟机处于物理隔离状态。

## 在第 1 课后准备来宾工具 {#guest-tools}

先学习[第 1 课的软件包操作流程](01-linux-cli.md)，然后在第 2–4 课开始前，**在每个可随时丢弃的来宾系统中**完成此检查点。使用现有的 NAT/DHCP 管理连接访问软件包仓库；不要让内部实验 NIC 接入上行链路、配置网关或设置 DNS 服务器。精简镜像可能缺少诊断工具，即使网络本身正常。

### 确认缺少的命令及其软件包

**在每台来宾系统上以普通用户身份执行；仅检查：**

```bash
hostname
cat /etc/os-release
command -v ip ss ping getent grep timeout dig tracepath traceroute python3 curl nc ncat
```

命令打印出可执行文件路径，就表示该命令可用。如果结果不明确，可以单独查询某个命令，例如 `command -v dig`。缺少某个可选命令时，没有路径或返回非零状态都属正常。请记录该来宾系统所选练习需要但当前缺少的命令，**不要记录所有缺少的可选命令**。

| 命令 / 用途 | Ubuntu Server 24.04 软件包 | Rocky Linux 9 软件包 | 使用位置 |
|---|---|---|---|
| `ip`、`ss`：接口、路由、套接字 | `iproute2` | `iproute` | 两台来宾系统 |
| `ping`：有次数限制的 ICMP 检查 | `iputils-ping` | `iputils` | 两台来宾系统 |
| `dig`：DNS 协议查询 | `bind9-dnsutils` | `bind-utils` | 第 4 课的客户端 |
| `tracepath`：默认的路由跟踪工具 | `iputils-tracepath` | `iputils` | 客户端；选择此项或下一行 |
| Linux `traceroute`：另一种路由跟踪工具 | `traceroute` | `traceroute` | 客户端；仅在选择此工具时需要 |
| `python3`：临时 HTTP 服务器 | `python3`（会安装解释器软件包） | `python3` | 服务器 |
| `curl`：HTTP 请求 | `curl` | 已有 `curl-minimal` **或** `curl` 提供程序 | 客户端及服务器自检 |
| OpenBSD `nc` / Ncat `ncat`：TCP 探测 | `netcat-openbsd` → 使用 `nc` | `nmap-ncat` → 使用 `ncat` | 客户端 |

本检查点默认选择 **`tracepath`**；如果已经安装 Linux `traceroute`，也可按第 4 课中的对应命令使用它。两者不必都装。在 Rocky 上，`iputils` 同时提供 `ping` 和 `tracepath`。请使用表中指定的 netcat 实现；命令名称相似不代表参数选项也相同。

`getent`、`grep`、`timeout`、sudo 和编辑器属于来宾系统和第 1 课的基线工具。如果这些检查失败，请先解决基线问题。不要为了满足此表而安装第二个网络管理器或解析器。在**已经由 NetworkManager 管理的 Rocky 来宾系统上**，可选的 `nmtui` 由 `NetworkManager-tui` 提供；只有在选择此界面时，才通过相同的指定软件包流程检查或安装它。使用 networkd 的来宾系统不需要安装它。

### 仅预览并安装选定的缺失工具

首次安装前，为来宾系统创建名为 `before-guest-tools` 的快照，并记录当前已安装的软件包和提供程序状态。只执行**与你的发行版相符**的命令分支。以下每个示例都假定缺少 `dig`。如果该命令已经可用，就跳过安装。对于选定的其他缺失命令，将 `TOOL_PACKAGE` 替换为表中对应的一个软件包，并重复检查候选版本和事务；不要把整张对应关系表粘贴到安装命令中。

**Ubuntu 来宾系统，以普通用户身份执行；只在标注的行使用 sudo：**

```bash
TOOL_PACKAGE=bind9-dnsutils
dpkg-query -W "$TOOL_PACKAGE"
sudo apt update
apt-cache policy "$TOOL_PACKAGE"
sudo apt-get --simulate install "$TOOL_PACKAGE"
```

本地查询显示“未找到软件包”时，表示该软件包当前未安装，这是正常结果。成功刷新软件包索引后，检查 `Candidate` 版本以及模拟安装将涉及的依赖、升级和移除操作。如果没有候选版本或仓库报错，请停止并检查已配置的 Ubuntu 仓库和管理连接。如果软件包已安装但找不到命令，请检查软件包中的文件和命令搜索路径，不要再安装一个冲突的提供程序。

只有在**所选命令确实缺少**，且预览中包含预期软件包及其依赖项时，才在 **Ubuntu 来宾系统**上安装：

```bash
sudo apt install "$TOOL_PACKAGE"
```

也要检查实际出现的确认提示；预览之后，仓库元数据可能会变化。不要自动确认意料之外的升级或移除。

**Rocky 来宾系统，以普通用户身份执行**：选择软件包之前，单独检查 curl 提供程序。

```bash
command -v curl
rpm -q curl curl-minimal
```

其中一个软件包查询可能报告“未安装”，这属于正常情况。如果 `curl` 已经可用，**保留当前提供该命令的软件包**，不要再请求安装另一个提供程序。确认命令可用后，可以用 `rpm -qf "$(command -v curl)"` 查看该文件的归属。本文的 HTTP 练习使用现有 `curl-minimal` 已足够。`curl` 与 `curl-minimal` 互相冲突；不要为了遵循课程而使用 `--allowerasing` 或替换软件包。

如果缺少 `curl`，且**两个提供程序都未安装**，请按下面的流程选择 `curl-minimal`。如果其中一个提供程序已安装但找不到命令，请检查其文件和 PATH，而不要替换它。

**Rocky 来宾系统，以普通用户身份执行；以下示例仅针对缺少 `dig` 的情况：**

```bash
TOOL_PACKAGE=bind-utils
rpm -q "$TOOL_PACKAGE"
dnf info "$TOOL_PACKAGE"
sudo dnf --assumeno install "$TOOL_PACKAGE"
```

检查可用的软件包、架构、仓库及计划执行的依赖安装和软件包移除。`--assumeno` 会拒绝事务而不进行安装；因为拒绝事务而产生非零状态，并不表示网络探测失败。如果没有候选版本，请检查已配置的 Rocky 9 仓库。必需工具表不要求启用 EPEL。然后，**只为选定的缺失命令**，在 **Rocky 来宾系统**上安装：

```bash
sudo dnf install "$TOOL_PACKAGE"
```

确认最终事务内容后再继续。保留现有 curl 提供程序和网络管理器。软件包候选版本是来宾系统查询到的结果，本文不保证其固定不变。

### 重新检查命令并保留恢复记录

**两台来宾系统均以普通用户身份执行：**`command -v ip ss ping getent grep timeout` 应能找到这些基线工具。对于本检查点默认选择的工具，请在相应来宾系统上检查以下内容：

```bash
# Client, either distribution; substitute traceroute only if you selected it:
command -v dig tracepath curl
```

```bash
# Ubuntu client only:
command -v nc
```

```bash
# Rocky client only:
command -v ncat
```

```bash
# Server, either distribution:
command -v python3 curl
python3 --version
```

所选工具应显示路径，Python 版本应为 3.9 或更高。记录安装了哪些软件包；这些检查只能确认工具可用，不能证明网络通信正常。如果第 4 课发现缺少必需工具，请回到这里处理。

后续课程仍要使用这些工具。删除指定软件包并不能精确撤销依赖项、配置、缓存或日志；不要移除预先存在的提供程序，也不要用通用的 autoremove 命令清理。如果要完整撤销这项准备工作，请在完成依赖它的练习后恢复 `before-guest-tools` 快照；请记住，恢复快照也会丢弃之后在来宾系统中完成的工作。

软件包对应关系于 2026 年 9 月 15 日依据发行版的主要来源核对：Ubuntu Noble 软件包文件列表包括 [iproute2](https://packages.ubuntu.com/noble/amd64/iproute2/filelist)、[ping](https://packages.ubuntu.com/noble/amd64/iputils-ping/filelist)、[dig](https://packages.ubuntu.com/noble/amd64/bind9-dnsutils/filelist)、[tracepath](https://packages.ubuntu.com/noble/amd64/iputils-tracepath/filelist)、[traceroute](https://packages.ubuntu.com/noble/amd64/traceroute/filelist)、[netcat](https://packages.ubuntu.com/noble/amd64/netcat-openbsd/filelist)、[curl](https://packages.ubuntu.com/noble/amd64/curl/filelist)和 [Python 软件包依赖](https://packages.ubuntu.com/noble/python3)；Rocky 9 软件包规格包括 [iproute](https://git.rockylinux.org/staging/rpms/iproute/-/blob/r9/SPECS/iproute.spec)、[iputils](https://git.rockylinux.org/staging/rpms/iputils/-/blob/r9/SPECS/iputils.spec)、[BIND 工具](https://git.rockylinux.org/staging/rpms/bind/-/blob/r9/SPECS/bind.spec)、[Ncat](https://git.rockylinux.org/staging/rpms/nmap/-/blob/r9/SPECS/nmap.spec)和 [curl 提供程序](https://git.rockylinux.org/staging/rpms/curl/-/blob/r9/SPECS/curl.spec)。来宾系统中的实时查询会选择对应的架构和版本；示例中的 x86_64 文件列表不代表必须使用该架构。

## 如何阅读命令 {#command-conventions}

- **客户端**、**服务器**和**两者**表示应在哪台机器上运行命令。先检查主机名。
- 命令块省略 `$` 和 `#` 提示符。`sudo` 会请求该命令所需的管理员权限。
- `LAB_IF` 这类大写名称表示当前 Shell 中的变量。在新终端中，需要先按说明确认实际 NIC，再重新设置这些变量。
- YAML 和 INI 代码块是配置文件内容，不是要粘贴到 Shell 中的命令。
- “示例输出”不保证与你的运行结果一致。请根据自己的环境对比地址、接口、计数器和时间。
- 修改之前先记录原有状态和配置。一次只改一项；检查失败时，按照课程提供的恢复步骤处理。

这些练习在可随时丢弃的虚拟机上进行，不要求你更改用于阅读本文的设备或远程生产服务器的网络和防火墙。

## 入门术语表 {#starter-glossary}

| 术语 | 初步含义 |
|---|---|
| 内核 / 用户空间 | 管理硬件和资源的核心部分 / 位于其上的 Shell 和程序 |
| NIC / 网络接口 | 通信设备 / 操作该设备时，操作系统使用的名称和设置 |
| MAC / IP | 用于在链路上递送帧的地址 / 用于跨网络递送数据包的地址 |
| 子网 / 前缀 | 共享前导位的地址范围 / 这些前导位的长度 |
| 网关 / 路由 | 转发数据时使用的下一台路由器 / 按目标地址选择的转发规则 |
| DHCP / DNS | 分配网络配置租约 / 查询与名称关联的信息 |
| TCP / UDP / 端口 | 两种传输协议 / 标识主机上通信端点的编号 |
| HTTP / SSH | Web 请求和响应协议 / 经过身份验证且加密的远程访问协议 |
| 套接字 / 监听器 | 程序用于通信的端点 / 等待新连接的套接字 |
| 防火墙 / SELinux | 流量规则 / 控制进程访问资源的策略 |
| NAT / CNI | 地址转换 / 用于设置容器网络的接口和实现生态 |

## 完成标准 {#completion}

完成课程不应只意味着“命令运行了”。

- 说明你使用的发行版和软件包管理器，并编辑一个文件。
- 区分实验 NIC 与管理 NIC，并找出负责 IP、路由和 DNS 设置的组件。
- 验证 SSH 主机身份、密钥登录、生效配置及恢复方法。
- 只允许预期客户端访问实验服务，并撤销自己添加的规则。
- 根据观察结果，区分 DNS 故障、TCP 连接失败和 HTTP 错误。
- 在[综合练习报告](08-container-cloud-capstone.md#capstone-report)中汇总套接字、数据包和应用层证据。

接下来学习[协议详情](../../basics/06-network-fundamentals-part1.md)、[内核数据包路径](../../kernel/02-network-stack.md)、[更深入的 Linux 诊断](../07-linux-network-diagnostics.md)和 [Kubernetes Service 实验](../../labs/core/03-services-networking-lab.md)。你不必一开始就安装 CNI 产品。

## 继续学习专家路径

[网络专家学习路径](../expert/README.md)接续本入门课程，提供六本练习手册，涵盖协议、路由、数据包路径，以及策略或故障发生前、中、后的证据。各章环境不同；请从[入门检查](../expert/README.md#entry-check)开始。

## 利用外部课程继续学习 {#further-study}

外部课程是可选的。[Bootlin Linux 网络课程](https://bootlin.com/training/networking/)可用于后续内核网络学习；[Linux Foundation 网络课程目录](https://training.linuxfoundation.org/networking/)可帮助你选择专业进阶课程。请向课程提供方核实范围、价格和时间安排。

阅读 CentOS 7 资料或基于旧版 `ifconfig` 的课程时，请区分其中的概念与执行环境。本文课程使用 `ip`、`ss` 和上文所列的发行版。

**开始学习：**[第 1 课：Linux 与命令行](01-linux-cli.md)
