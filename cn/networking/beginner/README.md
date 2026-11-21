# 从零开始学习 Linux 网络

> **学习基线**：Ubuntu Server 24.04 LTS，另提供 Rocky Linux 9 路径
>
> **最后更新**：2026年9月15日

本课程从打开第一个终端开始。创建文件并安装程序，然后配置 IP 和 DNS，通过 SSH 连接，应用防火墙规则并观察数据包。最后，诊断一个小型 Web 服务，并将所学内容与 Docker、Kubernetes 和云网络联系起来。

你不需要记住每条命令。目标是能够解释**你正在更改哪台机器、什么能证明操作成功，以及如何恢复到之前的状态**。

## 课程地图 {#course-map}

如果你是初学者，请从第 1 课开始。有经验的 Linux 用户也需要熟悉第 2 课中的共用实验环境和接口识别。课时为个人练习在内的规划估算；实际用时取决于经验。

| 顺序 | 课程 | 学完后你将能够 | 预计用时 |
|---|---|---|---|
| 1 | [Linux 和命令行界面](01-linux-cli.md) · [测验](../../quizzes/networking/beginner/01-linux-cli-quiz.md) | 识别发行版，并使用文件、编辑器、软件包和服务 | 2–3 小时 |
| 2 | [地址和接口](02-addressing-interfaces.md) · [测验](../../quizzes/networking/beginner/02-addressing-interfaces-quiz.md) | 区分 IP、子网、网关和 DNS 的作用，并识别 NIC | 2–3 小时 |
| 3 | [持久化网络配置](03-persistent-configuration.md) · [测验](../../quizzes/networking/beginner/03-persistent-configuration-quiz.md) | 配置 Netplan 或 NetworkManager，并验证重启和恢复行为 | 3–4 小时 |
| 4 | [DNS 和连接](04-dns-connectivity.md) · [测验](../../quizzes/networking/beginner/04-dns-connectivity-quiz.md) | 分别排查名称、路由、端口和 HTTP | 2–3 小时 |
| 5 | [使用 SSH 进行远程访问](05-ssh-access.md) · [测验](../../quizzes/networking/beginner/05-ssh-access-quiz.md) | 验证主机密钥，使用用户密钥登录，并检查生效的设置 | 2–3 小时 |
| 6 | [防火墙和主机安全](06-firewalls-host-security.md) · [测验](../../quizzes/networking/beginner/06-firewalls-host-security-quiz.md) | 放行所需流量，并解释 SELinux 和 Fail2ban | 3–4 小时 |
| 7 | [监控和性能](07-monitoring-performance.md) · [测验](../../quizzes/networking/beginner/07-monitoring-performance-quiz.md) | 观察套接字、数据包和流量，并说明测量的局限性 | 2–3 小时 |
| 8 | [综合项目和云网络衔接](08-container-cloud-capstone.md) · [测验](../../quizzes/networking/beginner/08-container-cloud-capstone-quiz.md) | 复现、隔离并恢复小型故障，然后选择下一步学习内容 | 3–4 小时 |

继续学习之前，请满足每课的完成标准，并用自己的话解释测验答案。学完第 1 课的软件包操作后，请在学习第 2–4 课之前，返回完成[来宾工具准备](#guest-tools)。内核调优和 CNI 实现比较将在核心练习之后进行。

## 准备实验用 VM {#lab-environment}

### 从一台 VM 开始

1. 使用 PC 支持的虚拟化应用程序。操作系统映像的虚拟 CPU 架构必须与之支持的架构相符。例如，Arm 机器需要使用该虚拟化工具支持的 Arm 映像。
2. 从[官方 Ubuntu Server 下载页面](https://ubuntu.com/download/server)选择 **24.04 LTS** 映像。如果使用其他版本，请重新检查软件包和服务的默认设置。按照[安装指南](https://documentation.ubuntu.com/server/tutorial/basic-installation/)操作，并创建一个带密码的普通用户。示例使用 `student`；请替换为你自己的用户名。
3. 建议每台 VM 起始配置为 2 个 vCPU、2 GiB 内存和 20 GiB 磁盘。这是实验环境的规划建议，并非性能保证，也不是所有虚拟机监控程序的最低规格。
4. 将第一个 NIC 接入虚拟机监控程序的**带 DHCP 的 NAT 网络**。它用于安装和下载软件包，并在后续练习中保持不变。
5. 通过虚拟机监控程序的**控制台窗口**登录。此时还不需要 SSH。正常关闭来宾系统，并为干净安装创建快照。

第 1 课只需要一台 VM。普通容器不能替代具备完整 systemd 和网络管理器的 VM。WSL 可用于命令行练习，但不能假定其后续网络和防火墙环境完全相同。

### 为第 2 课及后续课程准备两台 VM

两台来宾系统都使用 Ubuntu，可以让你专注于一个发行版。也可选择 Rocky Linux 9。使用[官方 Rocky 映像](https://rockylinux.org/download)和[文档](https://docs.rockylinux.org/)；你不需要同时学习两个发行版。

1. 分别安装第二台 VM，并将来宾系统标识为 `net-client` 和 `net-server`。简单克隆可能会复制机器标识符和 SSH 主机密钥，因此一开始请分别安装。
2. 正常关闭两台来宾系统，并为每台添加**第二个 NIC**。
3. 将两个第二 NIC 都接入同一个**内部虚拟网络**，例如 `linux-net-lab`。不要将 DHCP 服务器或外部上行链路接入该网络。“桥接”、“NAT”和“仅主机”设置不可互换：请确认所选模式实际连接的是什么。
4. 在虚拟机监控程序设置中记录每个 NIC 的 MAC 地址。启动来宾系统后，在第 2 课中将这些地址与 `ip -br link` 的输出对应起来。接口名称可能是 `eth1`、`enp0s8` 或 `ens19` 等；不要盲目照抄接口名称。
5. 在第 2、3 课中配置 IP 地址。不要在安装程序中为第二个 NIC 添加随意指定的网关或 DNS 服务器。

| 项目 | 客户端 VM | 服务器 VM |
|---|---|---|
| 角色 | 发送 SSH 和 curl 请求 | 接收 SSH 和 HTTP 请求 |
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

`192.0.2.0/24` 是此处仅用于隔离本地网络的文档专用地址范围，并非可在公共网络中路由的网络设计。管理 NIC 仍将来宾系统接入另一个网络，因此这并不意味着整台 VM 都处于物理隔离状态。

## 在第 1 课后准备来宾工具 {#guest-tools}

先学习[第 1 课的软件包操作流程](01-linux-cli.md)，然后在第 2–4 课之前，**在每台可随时丢弃的来宾系统中**完成此检查点。使用现有的 NAT/DHCP 管理连接访问软件仓库；不要让内部实验 NIC 接入上行链路，也不要为其设置网关或 DNS 服务器。即使网络正常，精简映像也可能没有诊断工具。

### 确认缺失的命令及其所属软件包

**每台来宾系统，普通用户；仅检查：**

```bash
hostname
cat /etc/os-release
command -v ip ss ping getent grep timeout dig tracepath traceroute python3 curl nc ncat
```

输出可执行文件路径表示该命令可用。如果结果不明确，请查询单个名称，例如 `command -v dig`。缺少某个可选命令时没有路径或返回非零状态是正常的。记录该来宾系统所选练习需要的**缺失命令**，而不是记录所有不存在的命令。

| 命令/用途 | Ubuntu Server 24.04 软件包 | Rocky Linux 9 软件包 | 需要安装的位置 |
|---|---|---|---|
| `ip`、`ss`：接口、路由、套接字 | `iproute2` | `iproute` | 两台来宾系统 |
| `ping`：有次数限制的 ICMP 检查 | `iputils-ping` | `iputils` | 两台来宾系统 |
| `dig`：DNS 协议查询 | `bind9-dnsutils` | `bind-utils` | 第 4 课中的客户端 |
| `tracepath`：默认的路径跟踪工具 | `iputils-tracepath` | `iputils` | 客户端；选择本行或下一行 |
| Linux `traceroute`：可选的路径跟踪工具 | `traceroute` | `traceroute` | 客户端，仅在选择此替代工具时安装 |
| `python3`：临时 HTTP 服务器 | `python3`（会拉取解释器软件包） | `python3` | 服务器 |
| `curl`：HTTP 请求 | `curl` | 已有的 `curl-minimal` **或** `curl` 提供者 | 客户端及服务器自检 |
| OpenBSD `nc` / Ncat `ncat`：TCP 探测 | `netcat-openbsd` → 使用 `nc` | `nmap-ncat` → 使用 `ncat` | 客户端 |

此检查点**默认选择 `tracepath`**；如果系统已安装 Linux `traceroute`，也可以使用它，并采用第 4 课中对应的命令。无需两者都安装。在 Rocky 上，`iputils` 同时提供 `ping` 和 `tracepath`。请使用表中指定的 netcat 实现：命令名称相似并不意味着选项也相同。

`getent`、`grep`、`timeout`、sudo 和编辑器属于来宾系统/第 1 课的基线。如果这些检查失败，请先解决基线问题。不要为了满足此表而安装第二个网络管理器或解析器。在**已由 NetworkManager 管理的 Rocky 来宾系统**上，可选的 `nmtui` 由 `NetworkManager-tui` 提供；仅当你选择使用该界面时，才通过同一套选定软件包流程检查/安装它。使用 networkd 的来宾系统不需要它。

### 预览并仅安装选定的缺失工具

首次安装之前，请为来宾系统创建快照 `before-guest-tools`，并记录已安装的软件包/提供者状态。下面的示例中，**只能使用与你的发行版相对应的分支**。每个示例都假定**缺少 `dig`**。如果该命令已经可用，请跳过对应安装。如果缺少的是其他选定命令，请将 `TOOL_PACKAGE` 替换为表中的一个对应软件包，并重复检查候选版本和事务；不要把整个矩阵粘贴到安装命令中。

**Ubuntu 来宾系统，普通用户；仅在标记的行使用 sudo：**

```bash
TOOL_PACKAGE=bind9-dnsutils
dpkg-query -W "$TOOL_PACKAGE"
sudo apt update
apt-cache policy "$TOOL_PACKAGE"
sudo apt-get --simulate install "$TOOL_PACKAGE"
```

本地查询显示“No packages found”表示该软件包不存在，这是预期结果。成功刷新软件仓库索引后，请检查 `Candidate` 版本以及模拟的依赖项、升级项和移除项。如果没有候选版本或出现软件仓库错误，请停止操作并检查已配置的 Ubuntu 软件仓库/管理路径。如果软件包已安装但找不到对应命令，请调查其文件和命令搜索路径，而不是安装会与之冲突的提供者。

仅当**所选命令确实缺失**且预览包含预期的软件包/依赖项时，才在 **Ubuntu 来宾系统**上安装：

```bash
sudo apt install "$TOOL_PACKAGE"
```

还要检查实际安装提示；预览和安装之间的软件包元数据可能发生变化。不要自动确认意外的升级/移除操作。

**Rocky 来宾系统，普通用户**：选择任何软件包之前，请单独检查 curl 提供者。

```bash
command -v curl
rpm -q curl curl-minimal
```

其中一个软件包查询可能会显示“未安装”，这是正常的。如果 `curl` 已经可用，**保留当前拥有它的提供者**，不要再请求另一个软件包。可在命令检查成功后通过 `rpm -qf "$(command -v curl)"` 确认其归属。对于这些 HTTP 练习，已有的 `curl-minimal` 已经够用。`curl` 和 `curl-minimal` 互相冲突；不要使用 `--allowerasing`，也不要为了学习本课程而替换软件包。

如果 `curl` 不存在且**两个提供者都未安装**，请通过以下流程选择 `curl-minimal`。如果某个提供者已安装但找不到该命令，请检查其文件/PATH，而不是替换它。

**Rocky 来宾系统，普通用户；仅以缺少 `dig` 为例：**

```bash
TOOL_PACKAGE=bind-utils
rpm -q "$TOOL_PACKAGE"
dnf info "$TOOL_PACKAGE"
sudo dnf --assumeno install "$TOOL_PACKAGE"
```

检查可用的软件包、架构、软件仓库以及计划中的依赖项/移除项。`--assumeno` 会拒绝事务而不进行安装；拒绝事务导致的非零状态不表示网络探测失败。如果没有候选版本，请调查已配置的 Rocky 9 软件仓库。必需工具表不要求启用 EPEL。然后，**仅针对所选的缺失命令**，在 **Rocky 来宾系统**上安装：

```bash
sudo dnf install "$TOOL_PACKAGE"
```

确认前请检查最终事务。保留已安装的 curl 提供者和现有网络管理器。软件包候选版本是来宾系统的实际观察结果，并非本文档保证的值。

### 重新检查命令并保存恢复记录

**两台来宾系统，普通用户：**`command -v ip ss ping getent grep timeout` 必须能找到基线工具。对于此检查点的默认选择，请在指定的来宾系统上检查以下命令：

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

所选工具应当显示路径，Python 版本应为 3.9 或更高。记录你添加了哪些软件包；这些检查只确认工具可用，并不能证明网络通信成功。如果第 4 课发现缺少必需工具，请回到这里。

保留这些工具供后续课程使用。移除指定软件包并不能精确还原依赖项、配置、缓存或日志；绝不要移除预先存在的提供者，也不要通过大范围 autoremove 进行清理。若要彻底回滚此次准备工作，请在依赖这些工具的练习完成后还原 `before-guest-tools`，但请注意，快照还会丢弃来宾系统此后所做的其他更改。

软件包对应关系于 2026年9月15日根据发行版的主要来源核对：Ubuntu Noble 软件包文件列表包括 [iproute2](https://packages.ubuntu.com/noble/amd64/iproute2/filelist)、[ping](https://packages.ubuntu.com/noble/amd64/iputils-ping/filelist)、[dig](https://packages.ubuntu.com/noble/amd64/bind9-dnsutils/filelist)、[tracepath](https://packages.ubuntu.com/noble/amd64/iputils-tracepath/filelist)、[traceroute](https://packages.ubuntu.com/noble/amd64/traceroute/filelist)、[netcat](https://packages.ubuntu.com/noble/amd64/netcat-openbsd/filelist)、[curl](https://packages.ubuntu.com/noble/amd64/curl/filelist) 和 [Python 软件包依赖项](https://packages.ubuntu.com/noble/python3)；Rocky 9 软件包规格包括 [iproute](https://git.rockylinux.org/staging/rpms/iproute/-/blob/r9/SPECS/iproute.spec)、[iputils](https://git.rockylinux.org/staging/rpms/iputils/-/blob/r9/SPECS/iputils.spec)、[BIND 工具](https://git.rockylinux.org/staging/rpms/bind/-/blob/r9/SPECS/bind.spec)、[Ncat](https://git.rockylinux.org/staging/rpms/nmap/-/blob/r9/SPECS/nmap.spec) 和 [curl 提供者](https://git.rockylinux.org/staging/rpms/curl/-/blob/r9/SPECS/curl.spec)。来宾系统上的实时查询会选择合适的架构/版本；x86_64 文件列表示例并不意味着必须使用该架构。

## 命令阅读说明 {#command-conventions}

- **客户端**、**服务器**和**两台来宾系统**用于标明命令的运行位置。请先检查主机名。
- 命令代码块省略 `$` 和 `#` 提示符。`sudo` 会为该命令请求管理员权限。
- `LAB_IF` 这样的全大写名称是在当前 shell 中使用的变量。在新终端中，或按说明确认实际 NIC 后，需要重新设置这些变量。
- YAML 和 INI 代码块是配置文件内容，不是要粘贴到 shell 中执行的命令。
- “示例输出”不保证与你的运行结果相同。请将地址、接口、计数器和时间与自己的环境进行比较。
- 更改之前，请记录原有状态和配置。一次只改一项；检查失败时，请使用课程中的恢复步骤。

这些练习在可随时丢弃的 VM 上进行。它们不会要求你更改阅读所用设备或远程生产服务器的网络或防火墙。

## 入门词汇表 {#starter-glossary}

| 术语 | 初步含义 |
|---|---|
| 内核 / 用户空间 | 管理硬件和资源的核心 / 位于其上的 shell 和程序 |
| NIC / 接口 | 通信设备 / 操作系统用于操作该设备的名称和设置 |
| MAC / IP | 用于在链路上递送帧的地址 / 用于跨网络递送数据包的地址 |
| 子网 / 前缀 | 共享前导位的地址范围 / 这些前导位的长度 |
| 网关 / 路由 | 要转发到的下一台路由器 / 按目标选择的转发规则 |
| DHCP / DNS | 分配网络配置租约 / 查询与某个名称关联的信息 |
| TCP / UDP / 端口 | 两种传输协议 / 用于标识主机上通信端点的数字 |
| HTTP / SSH | Web 请求/响应协议 / 经身份验证并加密的远程访问协议 |
| 套接字 / 监听器 | 程序的通信端点 / 等待新连接的套接字 |
| 防火墙 / SELinux | 流量规则 / 控制进程访问资源的策略 |
| NAT / CNI | 地址转换 / 用于设置容器网络的接口和实现生态系统 |

## 完成标准 {#completion}

完成课程不应仅仅意味着“命令运行了”。

- 解释你的发行版和软件包管理器，并编辑一个文件。
- 区分实验 NIC 和管理 NIC，并找出 IP、路由和 DNS 设置的归属位置。
- 验证 SSH 主机身份、密钥登录、生效的配置和恢复方式。
- 仅允许预期的客户端访问实验服务，并撤销你添加的规则。
- 通过观察结果区分 DNS 故障、TCP 连接故障和 HTTP 错误。
- 在[综合项目报告](08-container-cloud-capstone.md#capstone-report)中结合套接字、数据包和应用程序证据。

接下来学习[协议细节](../../basics/06-network-fundamentals-part1.md)、[内核数据包路径](../../kernel/02-network-stack.md)、[更深入的 Linux 诊断](../07-linux-network-diagnostics.md)和 [Kubernetes Service 实验](../../labs/core/03-services-networking-lab.md)。安装 CNI 产品不必是你的第一步。

## 继续学习专家路线

[网络专家路线](../expert/README.md)将在本入门课程之后提供九本练习手册，内容涉及协议、路由、数据包路径，以及策略/故障发生前、期间和之后的证据。各章节的环境不尽相同；请从[入门检查](../expert/README.md#entry-check)开始。

## 使用外部课程 {#further-study}

外部课程为可选内容。[Bootlin 的 Linux 网络课程](https://bootlin.com/training/networking/)可辅助后续的内核网络学习；[Linux Foundation 网络课程目录](https://training.linuxfoundation.org/networking/)可帮助你寻找专业方向的后续课程。请向课程提供方确认课程范围、价格和日程安排。

阅读 CentOS 7 资料或基于旧版 `ifconfig` 的课程时，请区分概念和执行环境。本课程使用 `ip`、`ss` 以及上文列出的发行版。

**开始学习：**[第 1 课：Linux 和命令行界面](01-linux-cli.md)
