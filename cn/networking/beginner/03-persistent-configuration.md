# 03. 持久化网络配置

> **支持的版本**：Ubuntu Server 24.04 LTS（主要版本）、Rocky Linux 9（替代版本）
> **最后更新**：2026 年 9 月 15 日

使用 `ip address add` 添加地址，只会更改正在运行的内核配置；它不会为下次启动保存指令。本章将为网络配置的所有者写入持久配置，然后比较保存的配置与虚拟机实际使用的配置。

## 前置条件与学习目标

完成[地址与接口](02-addressing-interfaces.md)，并准备好[课程实验环境](README.md)。使用两台一次性虚拟机及其虚拟机管理程序控制台。两台虚拟机都可以运行 Ubuntu；同时学习 Rocky 是可选项。

| 项目 | 所需状态 |
|---|---|
| 客户端实验网卡 | 完成本课后为 `192.0.2.10/24` |
| 服务器实验网卡 | 完成本课后为 `192.0.2.20/24` |
| 实验网络 | 同一个内部虚拟网络，不带 DHCP 服务器、路由器或上行链路 |
| 管理网卡 | 单独的现有 NAT/DHCP 连接；保留其地址、路由和 DNS 配置 |
| 身份识别 | 在虚拟机管理程序中记录每个网卡的 MAC 地址，并在来宾系统内匹配 |
| 访问与工具 | 来宾控制台、sudo 权限、编辑器、`ip` 以及已安装网络管理器的工具 |

命令必须在**指定的虚拟机内部**运行，绝不能在承载虚拟机的工作站上运行。不要为了采用另一种分支而安装或启用第二个网络管理器。如果缺少必需工具，请返回实验环境准备步骤。

完成后，你将能够判断配置由谁管理、持久保存静态地址、说明何时适合配置 DHCP/网关/DNS、重启后验证配置，并且只撤销本实验所做的更改。首先创建虚拟机快照并保持控制台打开。每次只执行一个步骤；发生错误时先检查再继续。

## 1. 确认网卡及其配置所有者

在**每台虚拟机**上只读取清单，不做任何更改：

```bash
cat /etc/os-release
ip -br link
ip -br address
ip -4 route show
ip -6 route show default
systemctl is-active systemd-networkd NetworkManager
```

`ip -br link` 会列出接口名称及其 MAC 地址。请匹配虚拟机管理程序中**实验网卡**的 MAC 地址，不要直接选列表中的第一个接口。NAT/DHCP 网卡通常承载管理默认路由。继续之前，记录该网卡的身份以及当前路由/DNS 设置。由于两个服务中的一个可能未安装或处于非活动状态，`systemctl is-active` 可能返回非零状态；这本身不代表故障。

本章中，将 `REPLACE_WITH_LAB_NIC` 替换为刚刚确认的名称。变量仅属于当前 shell；独立代码块会重复定义变量。不要将实验值赋给 `HOME` 或 `PATH` 等 shell 变量。

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
ip link show dev "$LAB_IF"
ip -4 address show dev "$LAB_IF"
ip -4 route show dev "$LAB_IF"
```

第二条命令显示内核当前使用的地址，但无法说明是谁负责在以后重新创建这些地址。开始本章前，先完成第 02 章中对临时地址的定向清理。新添加的实验网卡不应残留临时 IPv4 地址。不要仅仅因为某个地址出乎意料，就删除现有配置文件所管理的地址。

根据证据选择配置所有者：

| 证据 | 配置所有者及操作 |
|---|---|
| Ubuntu Netplan YAML 选择了 `networkd`；`networkctl status` 指出对应的 network 文件 | 按分支 A 操作 |
| Rocky NetworkManager 报告设备受其管理，并列出其配置文件 | 按分支 B 操作 |
| Netplan 选择了 `NetworkManager` | Netplan 也是上游配置来源；编辑前检查 YAML 和生成的配置文件 |
| cloud-init、配置工具、直接的 `.network` 文件、通配符匹配项或多个定义共同管理同一网卡 | 添加另一个定义之前先厘清所有权；如果来源不明确，请使用干净的课程虚拟机 |

Netplan 会将 YAML 转换为后端配置。`systemd-networkd` 和 NetworkManager 会将配置应用到设备；`nmcli` 和 `nmtui` 都通过 NetworkManager 操作。服务正在运行，并不能证明它管理每个网卡。本章采用的 Ubuntu Server 路径不代表所有 Ubuntu 映像、Ubuntu Desktop 或 Debian 安装都采用相同方式。

### 分支 A 所有权检查：Ubuntu Netplan/networkd

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
sudo netplan get
sudo ls -l /etc/netplan
networkctl status "$LAB_IF"
sudo ls -l /etc/systemd/network /run/systemd/network
resolvectl status
```

`netplan get` 会显示合并后的配置；请根据文件列表选择文件名，并使用 `sudo less /etc/netplan/ACTUAL_FILE.yaml` 检查实际 YAML 文件。同时检查现有的 `/lib/netplan` 和 `/run/netplan` 目录（如果存在）。`networkctl status` 会显示匹配的 network 文件（如果有）。`resolvectl status` 用于记录现有 DNS 服务器和链接。

Netplan 会按词典顺序合并名称不同的 YAML 文件：后面的标量值会替换前面的值，但列表可能会**串接**。在后续文件中添加空的地址/DNS 列表，通常并不能清除前面的列表。名称不同的定义也可能匹配同一个网卡。请参见 [Netplan 文件合并](https://netplan.readthedocs.io/en/stable/netplan-generate/)。

以下步骤要求实验网卡**不存在任何持久定义**，包括直接 networkd 文件中的通配符匹配项。如果安装程序已经定义了该网卡，请检查该文件的所有者并备份，然后有意地编辑其中准确对应实验网卡的配置段；不要把本文件覆盖到安装程序文件上，也不要保留两个定义。看到 cloud-init 注释时，应检查配置来源，而不是全局禁用 cloud-init。首次搭建实验环境时，在操作系统初始设置后再添加内部网卡，可以避免许多此类冲突。

### 分支 B 所有权检查：Rocky NetworkManager

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
nmcli --version
nmcli device status
nmcli -f GENERAL,IP4,IP6,CONNECTIONS device show "$LAB_IF"
nmcli -f NAME,UUID,TYPE,DEVICE,AUTOCONNECT connection show
```

`device` 描述网卡；`connection` 描述已保存的配置文件。两者的名称不一定相同。`GENERAL.CON-UUID` 用于识别当前活动的配置文件（如果有）。`CONNECTIONS` 有助于识别兼容的配置文件，包括非活动配置文件。记录之前实验配置文件的 UUID 及其是否处于活动状态；保留管理配置文件。

使用 `nmcli connection show uuid ACTUAL_UUID` 检查每个兼容配置文件。记录其 `connection.interface-name`、`802-3-ethernet.mac-address`、`connection.autoconnect` 和 `connection.autoconnect-priority`。设备/MAC 绑定为空时，一个以太网配置文件可能匹配多个网卡。不要为了简化实验而更改这种共享配置文件。

Rocky 9 支持 NetworkManager 的 keyfile 配置，也可能仍有较旧的 ifcfg 配置文件。不要只凭接口名称推断存储格式。[Rocky Linux 9 版本指南](https://docs.rockylinux.org/9/guides/network/basic_network_configuration/)介绍该版本；[未指定版本的指南](https://docs.rockylinux.org/guides/network/basic_network_configuration/)目前介绍的是 Rocky 10。

## 2A. 使用 Netplan/networkd 持久保存地址

只有完成分支 A 的所有权检查后，才能采用此分支。在客户端和服务器上分别操作，并使用**各自的 MAC 地址和 IP 地址**。

### 备份并创建一个由本实验管理的文件

在每台 **Ubuntu 虚拟机**上创建一个新的恢复目录。如果目录已存在，请停止并检查先前的尝试；不要替换之前的备份。

```bash
sudo mkdir -m 700 /root/network-beginner-03
sudo cp -a /etc/netplan /root/network-beginner-03/netplan-before
sudo sh -c 'umask 077; set -C; : > /etc/netplan/90-beginner-lab.yaml'
sudoedit /etc/netplan/90-beginner-lab.yaml
```

`cp -a` 会保留原文件及其权限。简短的 `sh` 命令会创建一个仅 root 可访问的空文件；`set -C` 会拒绝覆盖已有文件。`sudoedit` 会使用你配置的编辑器打开可编辑副本。

粘贴这份**完整的 YAML 文档**，使用空格而不是制表符。将示例 MAC 替换为客户端实验网卡的实际 MAC。在服务器上，将 MAC 替换为服务器实验网卡的 MAC，并将地址改为 `192.0.2.20/24`。

```yaml
network:
  version: 2
  ethernets:
    beginner-lab:
      renderer: networkd
      match:
        macaddress: "02:00:00:00:00:10"
      dhcp4: false
      dhcp6: false
      accept-ra: false
      link-local: []
      addresses:
        - 192.0.2.10/24
      optional: true
```

| 设置 | 在本实验中的含义 |
|---|---|
| `version: 2` | Netplan 配置架构版本 |
| `beginner-lab` | 定义 ID；通过 MAC 匹配选择网卡，不更改其名称 |
| 设备级 `renderer` | 为此定义选择 networkd，但不更改全局 renderer |
| `dhcp4: false` | 在没有 DHCP 服务器的网络上不发送 DHCP 请求 |
| IPv6 和链路本地设置 | 让此隔离练习仅在该网卡上使用 IPv4；这不代表建议主机全局禁用 IPv6 |
| `addresses` | 配置一个带 `/24` 前缀的地址；直连子网不需要网关 |
| `optional: true` | networkd 启动时无需等待此实验网卡；但仍会为其配置网络 |

这里有意不包含 `routes` 或 `nameservers` 配置块。这两台虚拟机都不是路由器或 DNS 服务器。猜测网关为 `192.0.2.1` 并不会凭空创建网关。管理网卡会保留原配置。

### 验证、试用并观察

```bash
sudo chmod 600 /etc/netplan/90-beginner-lab.yaml
sudo netplan generate
sudo netplan get
```

`chmod 600` 可确保只有 root 能读写文件。在正常且已启动的会话中，`generate` 会检查并生成后端配置，但不会应用配置；成功时通常不会输出任何信息。检查合并后的输出：仅包含预期的实验地址/MAC、不包含新增的实验网关/DNS，并且保留原有管理定义。YAML 文档格式有效，并不代表 MAC 或地址一定正确。

从**虚拟机控制台**启动试用：

```bash
sudo netplan try --timeout 120
```

在确认提示等待输入时，使用第二个控制台/登录会话进行检查：

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
ip -4 address show dev "$LAB_IF"
ip -4 route show dev "$LAB_IF"
ip -4 route show default
ip -6 route show default
networkctl status "$LAB_IF"
resolvectl status
```

预期会看到本地 `192.0.2.0/24` 路由、正确的 `.10` 或 `.20` 地址、实验网卡未引入默认路由/DNS，并且原管理路径仍可用。完成这些检查后再确认试用。只有两台虚拟机都完成配置后，才能要求对端 ping 成功。

`try` 和 `apply` 作用于**合并后的配置**，而不只是新文件，并且可能在多个设备上重新应用网络配置。即使没有编辑管理配置，仍然需要控制台访问。`try` 原本用于撤销未确认的试用配置，但 [Netplan 文档记录了回滚缺陷](https://netplan.readthedocs.io/en/stable/netplan-try/)。超时或按 Ctrl+C **并不能证明恢复已经完成**；请检查运行状态和磁盘上的文件。

### Netplan 恢复与回滚

请保留可供后续课程使用的实验配置。要撤销此次更改，请从**控制台**恢复：

1. 检查 `/etc/netplan/90-beginner-lab.yaml`，确认它是本课创建的文件。
2. 只将该文件移出 Netplan 输入目录。
3. 生成并应用剩余的、此前可正常工作的配置。

```bash
sudo mv -i /etc/netplan/90-beginner-lab.yaml /root/network-beginner-03/90-beginner-lab.failed.yaml
sudo netplan generate
sudo netplan apply
```

`mv -i` 会在覆盖先前失败留下的副本前询问。如果 `generate` 失败，请停止，不要运行 `apply`。如果你选择编辑现有所有者文件，而不是采用全新网卡路径，请将其与 `netplan-before` 中对应文件比较，并恢复**确切的被编辑文件**，然后生成/应用；不要替换整个目录。

重新检查地址、路由和管理访问。已不受管理的实验网卡可能仍保留运行时状态。**仅当本课配置的确切地址仍然存在时**，才删除该地址：

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
LAB_CIDR='192.0.2.10/24'
sudo ip address del "$LAB_CIDR" dev "$LAB_IF"
```

在服务器上设置 `LAB_CIDR='192.0.2.20/24'`。如果初始清单记录实验网卡在管理上处于关闭状态，请在同一个 shell 中运行 `sudo ip link set dev "$LAB_IF" down` 恢复该状态。不要删除管理路由，也不要清空接口配置。作为最后恢复步骤重启之前，请确认磁盘配置已恢复。如果所有权或恢复步骤不明确，请还原课前的虚拟机快照。

## 2B. 使用 NetworkManager 持久保存地址

在每台 **Rocky 虚拟机**上使用分支 B 的清单。本路径会在每台来宾系统上创建 `beginner-lab-static`。该名称必须是新名称；如果已存在，请检查先前的尝试，不要添加重复项。

保留兼容的旧配置文件作为恢复选项。为使重启后的选择可预测，只对**专门绑定到实验网卡**的配置文件禁用 autoconnect，并先记录每个原有值：

```bash
OLD_LAB_UUID='REPLACE_WITH_CONFIRMED_LAB_PROFILE_UUID'
nmcli -f connection connection show uuid "$OLD_LAB_UUID"
sudo nmcli connection modify uuid "$OLD_LAB_UUID" connection.autoconnect no
```

如果没有旧实验配置文件，则跳过此代码块。对其他仅供实验网卡使用的候选项重复此操作；暂时不要更改当前活动状态。如果候选项未绑定/由多设备共享，或其所有权不明确，请先厘清情况。`DEVICE=--` 只表示非活动状态，并不代表可以忽略。

创建新配置文件；此代码块会先**保存但不自动启用**：

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
LAB_MAC='REPLACE_WITH_LAB_MAC'
LAB_CIDR='192.0.2.10/24'
sudo nmcli connection add type ethernet con-name beginner-lab-static \
  ifname "$LAB_IF" 802-3-ethernet.mac-address "$LAB_MAC" \
  connection.autoconnect no \
  ipv4.method manual ipv4.addresses "$LAB_CIDR" \
  ipv4.gateway "" ipv4.dns "" ipv4.never-default yes \
  ipv6.method disabled
nmcli -f connection,802-3-ethernet,ipv4,ipv6 connection show id beginner-lab-static
```

服务器上使用 `.20/24`。`manual` 要求指定地址/前缀。接口和 MAC 绑定会限制此配置文件可用于哪个设备；`mac-address` 用于匹配永久 MAC，而不是更改它。网关/DNS 为空且设置了 `never-default yes`，因此连接仅限本地。`connection add` 默认会持久保存；**已保存不等于已激活**。

从输出中记录新 UUID。激活这个确切配置文件，然后检查运行时状态：

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
LAB_UUID='REPLACE_WITH_NEW_LAB_PROFILE_UUID'
sudo nmcli --wait 30 connection up uuid "$LAB_UUID" ifname "$LAB_IF"
nmcli -f GENERAL,IP4,IP6 device show "$LAB_IF"
ip -4 route show
```

激活可能会替换此网卡上先前活动的配置文件。预期地址应正确、存在直连子网路由，并且没有实验网关/DNS。将管理路由与初始清单比较。如果激活失败，请检查 `journalctl -u NetworkManager -b -n 50 --no-pager`。发生超时并不代表已保存的配置文件消失。

观察结果符合预期后，启用后续启动时自动激活：

```bash
LAB_UUID='REPLACE_WITH_NEW_LAB_PROFILE_UUID'
sudo nmcli connection modify uuid "$LAB_UUID" connection.autoconnect yes
nmcli -f connection.id,connection.uuid,connection.autoconnect connection show uuid "$LAB_UUID"
```

### 在 nmtui 中配置同一配置文件

如果系统已经提供 `nmtui`，请打开**现有的专用配置文件**：

```bash
sudo nmtui edit beginner-lab-static
```

使用 Tab 移动，方向键选择，空格键切换，Enter 确认。检查配置文件名称/设备，将 IPv4 设为 **Manual** 并展开，然后确认只有一个 `.10/24` 或 `.20/24` 地址。Gateway、DNS 服务器和搜索域应留空；如果 Routes 中提供相应选项，请选择 **Never use this network for default route**。IPv6 保持 **Disabled**，验证后启用自动连接。

选择 **Cancel** 仅检查，或选择 **OK** 保存预期修改。保存操作修改的是同一个 NetworkManager 配置文件，与 `nmcli` 相同；它不是单独的配置层。保存后使用 `nmcli connection show` 检查，再通过前一代码块激活所记录的 UUID。菜单因软件包版本而异；如果缺少某项属性，请使用 `nmcli` 设置并验证。不要对管理连接执行通用停用/重新启用操作。

### NetworkManager 恢复与回滚

从**控制台**检查已记录的新 UUID，然后只删除自己的配置文件。如果创建未成功，请跳过此新配置文件代码块，但仍要恢复之前更改过的旧 autoconnect 值：

```bash
LAB_UUID='REPLACE_WITH_NEW_LAB_PROFILE_UUID'
nmcli -f connection,ipv4 connection show uuid "$LAB_UUID"
sudo nmcli connection modify uuid "$LAB_UUID" connection.autoconnect no
sudo nmcli connection down uuid "$LAB_UUID"
sudo nmcli connection delete uuid "$LAB_UUID"
```

确认 UUID 无误后，如果 `down` 返回“已处于非活动状态”可以接受；其他无关错误都需要调查。连接关闭时，其他兼容配置文件可能会自动激活，因此要再次检查设备。

如果此前存在旧实验配置文件，请恢复所有已记录的 autoconnect 值。**只有先前处于活动状态时**才重新激活它：

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
OLD_LAB_UUID='REPLACE_WITH_PREVIOUS_LAB_PROFILE_UUID'
OLD_AUTOCONNECT='yes'
sudo nmcli connection modify uuid "$OLD_LAB_UUID" connection.autoconnect "$OLD_AUTOCONNECT"
sudo nmcli --wait 30 connection up uuid "$OLD_LAB_UUID" ifname "$LAB_IF"
```

请使用记录的 `yes` 或 `no`，不要猜测。如果旧配置文件之前处于非活动状态，请省略 `up` 这一行。如果此前没有旧配置文件，则无需恢复旧配置文件：只需确认本课配置的地址已消失。如有必要，恢复实验链路原来的启用/关闭状态，并将管理地址/路由/DNS 与初始记录比较。不要删除所有以太网配置文件，也不要全局重启网络服务。

## 3. DHCP、网关与 DNS：何时需要这些设置

静态寻址使用管理员选择的地址。DHCP 会向实际存在的 DHCP 服务器请求租约；服务器也可能提供路由和 DNS。在内部课程网络上启用 DHCP 并不会获得租约。DNS 服务器负责回答名称查询；网关负责将数据包转发到链路外的网络。同一设备可以同时提供这两种服务，但不能仅凭 IP 地址以 `.1` 结尾就认定它具备其中任何一种功能。

下面是**可选的配置示例，不属于两虚拟机课程实验的操作**。应使用另一台一次性练习虚拟机/接口，以虚拟机管理程序中的 MAC 地址识别，并保证有控制台访问、没有冲突的配置所有者，且所在虚拟网络已启用 DHCP 或路由网络由管理员明确指定。绝不要改用课程虚拟机的管理网卡。

### 在确实提供 DHCP 的网络上配置 DHCP

对于接入 DHCP 练习网络的备用 **networkd 管理网卡**，完整的 Netplan 定义如下：

```yaml
network:
  version: 2
  ethernets:
    practice-dhcp:
      renderer: networkd
      match:
        macaddress: "02:00:00:00:00:30"
      dhcp4: true
      dhcp4-overrides:
        use-routes: false
        use-dns: false
        use-domains: false
      dhcp6: false
      accept-ra: false
      link-local: []
      optional: true
```

将示例 MAC 替换为备用网卡的 MAC。此处的覆盖设置会请求地址，同时拒绝 DHCP 路由、DNS 和搜索域，以保留练习虚拟机现有的管理路径。它仍会获得直连子网路由。如果管理员有意将该接口选作主要上行链路，也可以接受 DHCP 路由和 DNS；本课程不会更改现有上行链路。

使用相同的新文件/备份流程，采用不同的文件名（例如 `90-beginner-dhcp.yaml`）和 600 权限模式，并执行 `generate`、检查合并后的输出以及 `try`。使用 `networkctl status` 和 `ip address` 检查是否获得租约。如果没有租约，请检查链路载波状态、虚拟网络选择以及 DHCP 服务/作用域是否可用。撤销时只移除此新文件并应用恢复后的配置；按照分支 A 检查是否残留实验地址。

对于尚未配置的 **NetworkManager 管理备用网卡**，等效的已保存配置文件如下：

```bash
PRACTICE_IF='REPLACE_WITH_SPARE_NIC'
PRACTICE_MAC='REPLACE_WITH_SPARE_MAC'
sudo nmcli connection add type ethernet con-name beginner-practice-dhcp \
  ifname "$PRACTICE_IF" 802-3-ethernet.mac-address "$PRACTICE_MAC" \
  connection.autoconnect no ipv4.method auto \
  ipv4.never-default yes ipv4.ignore-auto-routes yes ipv4.ignore-auto-dns yes \
  ipv6.method disabled
sudo nmcli --wait 60 connection up id beginner-practice-dhcp ifname "$PRACTICE_IF"
nmcli -f GENERAL,IP4,DHCP4 device show "$PRACTICE_IF"
```

配置名称必须尚未使用。记录其 UUID，并使用分支 B 中基于 UUID 的回滚方法只删除这个新配置文件。由于此示例采用 `autoconnect no`，重启后配置仍会保存，但须手动激活。如果要将现有的**专用练习配置文件**从静态配置改为 DHCP，请在同一条 `connection modify` 操作中设置 `ipv4.method auto`，并清除 `ipv4.addresses`、`ipv4.gateway`、`ipv4.routes`、`ipv4.dns` 和 `ipv4.dns-search`；否则旧的静态值可能与 DHCP 设置并存。先记录旧值，以便撤销修改时恢复。

### 在带路由的练习网络上持久配置网关和 DNS

假设**另一台练习虚拟机**（不是两台课程虚拟机）具有管理员分配的 `10.77.0.10/24`、真实且处于同一链路上的路由器 `10.77.0.1`，以及可访问的解析器 `10.77.0.53`，后者负责 `training.example`。其实验网卡必须是明确选定的默认上行链路，且**不存在会竞争的管理默认路由**；请使用虚拟机管理程序控制台。在使用前，管理员必须确认这些示例值适用于该练习网络。

对于 Netplan/networkd，完整定义如下：

```yaml
network:
  version: 2
  ethernets:
    practice-uplink:
      renderer: networkd
      match:
        macaddress: "02:00:00:00:00:40"
      dhcp4: false
      dhcp6: false
      accept-ra: false
      link-local: []
      addresses:
        - 10.77.0.10/24
      routes:
        - to: default
          via: 10.77.0.1
      nameservers:
        addresses:
          - 10.77.0.53
        search:
          - training.example
```

`to: default` 会为没有更具体匹配项的目标提供路由。`via` 指定链路上的路由器地址。`nameservers.addresses` 用来指定解析器；`search` 可以将 `web` 这样的短名称扩展为 `web.training.example`。它不会创建 DNS 记录。应使用单独备份且由本实验管理的文件，替换 MAC，然后重复分支 A 中的权限/验证/试用/恢复流程。

在等效的全新且由本实验管理的练习网卡上，NetworkManager 配置如下：

```bash
PRACTICE_IF='REPLACE_WITH_PRACTICE_UPLINK'
PRACTICE_MAC='REPLACE_WITH_PRACTICE_MAC'
sudo nmcli connection add type ethernet con-name beginner-practice-routed \
  ifname "$PRACTICE_IF" 802-3-ethernet.mac-address "$PRACTICE_MAC" \
  connection.autoconnect no \
  ipv4.method manual ipv4.addresses 10.77.0.10/24 \
  ipv4.gateway 10.77.0.1 ipv4.never-default no \
  ipv4.dns 10.77.0.53 ipv4.dns-search training.example \
  ipv6.method disabled
sudo nmcli --wait 30 connection up id beginner-practice-routed ifname "$PRACTICE_IF"
nmcli -f GENERAL,IP4 device show "$PRACTICE_IF"
```

激活之前先检查新配置文件并记录其 UUID；如果希望启动时自动激活，请只在成功检查之后启用 autoconnect。按照分支 B 的方式通过 UUID 移除它进行回滚。无论使用哪个后端，都应验证 `ip route get 10.77.0.53`、默认路由及管理员提供的 DNS 记录。如果 resolved 正在运行，请检查 `resolvectl status`；否则检查 NetworkManager 的活动 DNS 和 `/etc/resolv.conf`。不要手动编辑生成的 `resolv.conf`，也不要把临时 `resolvectl dns` 命令当作持久配置更改。

## 4. 重启后验证课程实验环境

返回两台课程虚拟机的静态配置。保存工作，然后从控制台运行 `sudo reboot`，重启每台**一次性来宾虚拟机**。登录后重新通过 MAC 地址匹配网卡；shell 变量不会在重启后保留。

在**客户端**上：

```bash
LAB_IF='REPLACE_WITH_CLIENT_LAB_NIC'
ip -4 address show dev "$LAB_IF"
ip -4 route get 192.0.2.20
ip -4 route show default
ping -n -c 3 -W 2 192.0.2.20
```

在**服务器**上检查 `.20/24`，然后运行 `ip -4 route get 192.0.2.10` 和 `ping -n -c 3 -W 2 192.0.2.10`。路由查找应选择实验网卡和本地实验源地址，不应显示 `via`。管理默认路由仍可能存在，并应与原始配置相符。DHCP 租约详情可能会正常续租。

| 观察结果 | 首要调查方向 |
|---|---|
| 重启后地址缺失 | MAC 错误、文件/配置未保存、autoconnect 已禁用或存在冲突的配置所有者 |
| 出现额外实验地址/DNS/默认路由 | YAML 列表已合并、存在其他匹配定义/配置文件或残留的临时状态 |
| `NO-CARRIER` | 检查虚拟机管理程序中的网线/适配器状态，以及是否连接到内部网络 |
| 路由正确但收不到 ping 回复 | 检查对端地址、是否位于同一内部网络、邻居发现和 ICMP 策略；继续学习第 04 章 |
| 管理访问发生变化 | 使用控制台和对应的回滚步骤；不要清空路由 |

## 完成检查

- 根据两台虚拟机上的 MAC 地址证据识别实验网卡和管理网卡。
- 说明哪个文件/配置文件管理实验网卡，并区分已保存状态与活动状态。
- 验证 `.10/24` 和 `.20/24` 在重启后仍然存在，且对端路由位于本地链路上。
- 证明实验网卡未添加网关/DNS，并且管理配置得到保留。
- 记录对端 ping 结果；遇到失败时调查原因，而不是臆造网关。
- 指出要撤销的确切新文件/配置文件，以及需要恢复的原始状态。
- 说明为什么可选的 DHCP/路由示例需要使用另行准备的网络。

保留有效的静态实验地址，为下一课继续使用。课程结束前请保留备份记录。

## 主要资料与延伸阅读

- [Ubuntu Server：配置网络](https://documentation.ubuntu.com/server/explanation/networking/configuring-networks/)
- [Netplan 示例](https://netplan.readthedocs.io/en/stable/examples/)、[YAML 参考](https://netplan.readthedocs.io/en/stable/netplan-yaml/)、[文件权限](https://netplan.readthedocs.io/en/stable/security/)
- [Netplan 生成与合并](https://netplan.readthedocs.io/en/stable/netplan-generate/)、[Netplan try 与恢复注意事项](https://netplan.readthedocs.io/en/stable/netplan-try/)
- [NetworkManager nmcli 示例](https://www.networkmanager.dev/docs/api/latest/nmcli-examples.html)、[nmcli 手册](https://www.networkmanager.dev/docs/api/latest/nmcli.html)、[配置文件属性](https://www.networkmanager.dev/docs/api/latest/nm-settings-nmcli.html)、[nmtui](https://www.networkmanager.dev/docs/api/latest/nmtui.html)
- [Rocky Linux 9 网络配置](https://docs.rockylinux.org/9/guides/network/basic_network_configuration/)

[上一章：地址与接口](02-addressing-interfaces.md) · [测验](../../quizzes/networking/beginner/03-persistent-configuration-quiz.md) · [下一章：DNS 与连通性](04-dns-connectivity.md)
