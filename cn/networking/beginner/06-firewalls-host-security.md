# 6. 防火墙、SELinux 与有时限的 SSH 防护

> **支持的版本**：Ubuntu Server 24.04 LTS（主要版本）、Rocky Linux 9（替代版本）
> **最后更新**：2026 年 9 月 15 日

[上一课：SSH](05-ssh-access.md) | [课程](README.md) | [测验](../../quizzes/networking/beginner/06-firewalls-host-security-quiz.md) | [下一课：监控](07-monitoring-performance.md)

应用可能正在监听端口，但防火墙拒绝了连接；也可能已经接受连接，却没有权限读取文件。本课会区分网络策略、进程/文件策略以及对重复身份验证失败的应对措施。

## 前置条件与学习目标

使用第 1–5 课中两台可通过控制台访问的一次性来宾系统：客户端 `192.0.2.10/24`、服务器 `192.0.2.20/24`，内部实验网卡不带 DHCP/上行链路，另有互不更改的 NAT/DHCP 管理网卡。如果第 5 课因 TCP 22 被阻止而让你来到这里，只需完成所选防火墙分支，再返回原处；该分支不要求先完成所有 SSH 加固。

你将允许指定 IPv4 客户端通过 TCP 端口 **22 和 8000** 连接服务器，检查实际生效的策略、区分已保存规则与运行时规则、仅恢复自己所做的更改、修复一个故意设置了错误 SELinux 标签的临时文件，并可选择配置受限的 Fail2ban jail。使用服务器控制台进行更改，并在客户端测试连接。所有命令/输出示例都仅供说明，**并非在实时虚拟机上测试所得的结果**。

为服务器创建快照 `before-host-security`。记录现有防火墙/运行时状态以及任何管理 SSH 路径。根据现有配置所有者，选择 **Ubuntu 上的 UFW 或 Rocky 上的 firewalld**。不要安装/启用互相竞争的管理器，不要清空规则，也不要为通过测试而禁用安全服务。这只是 IPv4 实验策略，并非完整的 IPv6 监听器策略或生产环境加固清单。

## 1. 理解流量方向并确认配置所有者

**入站**表示发往此服务器的流量，例如新建 SSH 连接。**出站**表示由服务器发起的流量，包括向软件包仓库发起请求。**转发**表示流量经过服务器发往其他主机。本实验服务器不是路由器：无需更改转发、NAT 或默认路由。

有状态防火墙会跟踪会话，并通常允许已建立连接的回复。因此，仍然存在的旧 SSH 会话不能证明允许新的入站会话。防火墙允许规则也不会创建监听程序。

**服务器，以普通用户身份只检查：**

```bash
hostname
cat /etc/os-release
ip -br link
ip -4 -br address
ip -4 route
systemctl is-active ufw firewalld
```

某个单元未安装/未激活时可能以非零状态退出，但这本身并非故障。对于 UFW，其自身 `status` 命令才会报告是否启用了规则强制；仅检查 systemd 单元不够。如果存在 Docker、Kubernetes、自定义 nftables/iptables 规则或其他策略管理器，请改用干净的课程虚拟机，不要假设本简化策略拥有整台主机。

**服务器，以普通用户身份输入名称，并先匹配虚拟机管理程序中的 MAC：**

```bash
read -r -p 'Server lab NIC verified by MAC: ' LAB_IF
read -r -p 'Server management NIC verified by MAC: ' MGMT_IF
ip -br link show dev "$LAB_IF"
ip -br link show dev "$MGMT_IF"
FW_NOTE=$(mktemp -d "$HOME/network-beginner-firewall.XXXXXX")
printf '%s\n' "$FW_NOTE"
```

如果目录创建失败、名称为空/相同，或 MAC 不匹配，请停止。将这些值记录在当前 shell 以外的位置。确认 `.20/24` 属于 `LAB_IF`，然后保存管理基线：

```bash
ip -4 -br address show dev "$MGMT_IF" > "$FW_NOTE/management.before"
ip -4 route > "$FW_NOTE/routes.before"
```

## 2A. Ubuntu：UFW

仅当 UFW 是来宾系统的现有所有者时，才使用此分支。如果缺少 `ufw`，请通过来宾工具准备步骤安装。记录 UFW 原先处于启用还是禁用状态。

**Ubuntu 服务器，以普通用户身份调用 sudo：**

```bash
sudo ufw status verbose
sudo ufw status numbered
sudo ufw show added
sudo ufw show raw
sudo cat /etc/default/ufw
sudo ufw show added > "$FW_NOTE/ufw-added.before"
```

检查本地 `/etc/ufw/before.rules`、`after.rules` 以及对应的 IPv6 文件。此前自定义的 accept 规则可能绕过下文对用户规则施加的限制。只有确认使用已了解的 stock 规则且没有冲突的自定义策略时才能继续。通用的 `allow 22/tcp` 会允许更多来源；仅插入狭窄的 allow 规则并不会撤销更宽泛的允许权限。

如果 UFW 当前**处于禁用状态**，首次启用时必须满足：预期的默认入站 deny/出站 allow 策略、标准 DHCP/回复处理正常，且**没有依赖开放防火墙的现有入站管理服务**。使用控制台和出站 NAT/DHCP 管理连接时，满足此路径要求。如果现有管理 SSH/入站服务必须保持可达，请在启用前保留已批准且范围明确的策略；不要臆造宽泛的管理允许规则，也不要以为控制台测试验证了 SSH。如果这些条件不明确，请在厘清策略前保持 UFW 禁用。

分别添加允许客户端连接 SSH 和 HTTP 的规则，然后对相同实验端点添加拒绝规则。规则顺序为 **SSH allow、HTTP allow、实验 deny**，并置于普通的宽泛用户规则之前。三条规则都只针对实验网卡。分别添加 allow 可让[综合防火墙练习](08-container-cloud-capstone.md#firewall-fault)在不删除 SSH 权限的情况下移除 HTTP 权限。

**Ubuntu 服务器，以普通用户身份调用 sudo：**

```bash
sudo ufw insert 1 allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 22 comment 'network-beginner-ssh'
sudo ufw insert 2 allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 8000 comment 'network-beginner-http'
sudo ufw insert 3 deny in on "$LAB_IF" proto tcp \
  from any to 192.0.2.20 port 22,8000 comment 'network-beginner-other'
sudo ufw show added
```

如果任何命令失败，请停止，并对成功添加的规则按下文精确移除。不要重复添加已有的相同规则：记录它是否在本练习开始前已存在，并保留其原有配置所有者。

如果 UFW 之前处于禁用状态且通过了上述启用条件，请在**服务器控制台**上运行 `sudo ufw enable`；先阅读提示，不要使用 `--force`。如果 UFW 已处于启用状态，规则修改会立即生效。

**Ubuntu 服务器，以普通用户身份调用 sudo：**

```bash
sudo ufw status numbered
sudo ufw status verbose
sudo ufw reload
sudo ufw status numbered
```

预期看到两个按来源限定的 allow 在同一接口/目标的 deny 之前，并且顺序如上；重新加载后也应保留。以此方式添加的 UFW 规则会同时保存并应用；此流程没有 firewalld 那种逐规则的运行时/`--permanent` 分离或超时设置。规则编号只是当前列表中的位置，因此后续清理要按原规则规格进行。

执行下面的通用测试。如需**仅撤销这些规则**，请从 Ubuntu 服务器控制台运行：

```bash
sudo ufw delete allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 22
sudo ufw delete allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 8000
sudo ufw delete deny in on "$LAB_IF" proto tcp \
  from any to 192.0.2.20 port 22,8000
sudo ufw show added
```

这三条分别对应**彻底清理本课**的逆向操作，并非发生仅 HTTP 故障时要全部运行的命令。只确认并处理你自己的规则。如果 UFW 起初处于禁用状态，仅因本练习启用了它，且现在要恢复基线，则在移除已保存规则**之后**运行 `sudo ufw disable`。不要禁用原本已启用的防火墙。与 `ufw-added.before` 比较。若要将课程策略保留用于第 7–8 课，请按原顺序重新应用三条规则并重新验证，不要保持清理后的状态。

## 2B. Rocky：firewalld 与专用实验 zone

仅当 firewalld 是现有且活动的所有者时，才使用此分支。**Zone** 会为相关接口/来源组合策略。NetworkManager 连接未指定 zone 时，会回退到 firewalld 默认 zone，而默认 zone 可能已经广泛允许 SSH。在此 zone 中添加狭窄 allow 规则不会限制已有权限。

**Rocky 服务器，以普通用户身份调用 sudo 检查防火墙：**

```bash
sudo firewall-cmd --state
sudo firewall-cmd --get-default-zone
sudo firewall-cmd --get-active-zones
sudo firewall-cmd --list-all-zones
sudo firewall-cmd --permanent --list-all-zones
sudo firewall-cmd --list-all-policies
sudo firewall-cmd --permanent --list-all-policies
sudo firewall-cmd --direct --get-all-rules
sudo firewall-cmd --list-all-zones > "$FW_NOTE/firewalld-runtime.before"
sudo firewall-cmd --permanent --list-all-zones > "$FW_NOTE/firewalld-permanent.before"
nmcli -f NAME,UUID,TYPE,DEVICE connection show --active
```

记录两张网卡的有效 zone 和默认 zone。检查来源绑定、策略、rich rule 和自定义 direct rule（查询 direct 规则是检查旧状态，不是建议创建此类规则）。这些设置可能改变分类或接受行为，超出接口所属 zone 所显示的内容。此全新虚拟机流程要求没有互相竞争的来源绑定/策略，并且没有 reload 会丢弃的无关运行时更改。不要使用 `--runtime-to-permanent` 保存未知更改。

从第 3 课找到活动的、**仅供实验网卡使用**的 NetworkManager 配置文件 UUID。绝不要选择管理配置文件或共享配置文件。

**Rocky 服务器，以普通用户身份：**

```bash
read -r -p 'Active lab-only connection UUID: ' LAB_UUID
nmcli connection show uuid "$LAB_UUID"
LAB_OLD_ZONE=$(nmcli -g connection.zone connection show uuid "$LAB_UUID")
printf '%s\n' "$LAB_OLD_ZONE" > "$FW_NOTE/lab-zone.before"
```

验证配置文件对应的网卡/MAC 及 `.20/24`。旧 zone 为空也可能完全正常；请记录确切值。在运行时和持久 zone 清单中都检查 `network-beginner`。如果它已存在，请停止，不要复用或删除他人的 zone。

**Rocky 服务器，以普通用户身份调用 sudo：**

```bash
sudo firewall-cmd --permanent --new-zone=network-beginner
sudo firewall-cmd --check-config
sudo firewall-cmd --reload
```

在运行时使用此工作流之前，必须先持久定义新 zone 并加载它。Reload 会用持久策略替换运行时策略，因此必须先处理好无关运行时更改。此时尚未移动任何接口。

设置两条确切的 rich-rule 字符串。它们用于选择 IPv4、来源、目标和 TCP 端口；zone 与 `LAB_IF` 的关联则提供接口边界。

**Rocky 服务器，以普通用户身份：**

```bash
RULE22='rule family="ipv4" source address="192.0.2.10/32" destination address="192.0.2.20/32" port port="22" protocol="tcp" accept'
RULE8000='rule family="ipv4" source address="192.0.2.10/32" destination address="192.0.2.20/32" port port="8000" protocol="tcp" accept'
```

**Rocky 服务器，以普通用户身份调用 sudo；进行十分钟运行时试用：**

```bash
sudo firewall-cmd --zone=network-beginner --add-rich-rule="$RULE22" --timeout=600
sudo firewall-cmd --zone=network-beginner --add-rich-rule="$RULE8000" --timeout=600
sudo nmcli connection modify uuid "$LAB_UUID" connection.zone network-beginner
sudo firewall-cmd --get-zone-of-interface="$LAB_IF"
sudo firewall-cmd --get-zone-of-interface="$MGMT_IF"
sudo firewall-cmd --zone=network-beginner --list-all
sudo firewall-cmd --permanent --zone=network-beginner --list-all
```

NetworkManager 的 `connection.zone` 更改会立即对活动连接生效。它只更改所选配置文件的防火墙 zone，不会更改 IP/DHCP/网关设置。预期看到 `LAB_IF` 位于新建的空 zone 中，且只有上述两条 rich accept；管理网卡仍位于原 zone。新 zone 没有宽泛的 `ssh` service 或 trusted/ACCEPT target。其默认行为会拒绝未允许的新 TCP 连接；对 ICMP 等其他协议的处理属于单独的策略问题。

试用规则只应出现在运行时。600 秒后规则到期，reload 时也会丢失。但 zone/profile 绑定不会随规则到期而移除：因此仍必须能从控制台恢复。不要将 `--timeout` 与 `--permanent` 同时使用。试用期间执行通用测试。

要保留策略，请在**Rocky 服务器上以普通用户身份调用 sudo**：

```bash
sudo firewall-cmd --permanent --zone=network-beginner --add-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --add-rich-rule="$RULE8000"
sudo firewall-cmd --check-config
sudo firewall-cmd --reload
sudo firewall-cmd --zone=network-beginner --list-rich-rules
sudo firewall-cmd --permanent --zone=network-beginner --list-rich-rules
```

只有在期间没有引入无关运行时更改时才继续。Reload 后预期持久规则和运行时规则字符串相同；再次测试一个**新建**的 SSH/HTTP 连接。

如需**恢复原状**，先完成/停止下文的可选 Fail2ban jail，因为它可能会向此 zone 添加规则。然后在 Rocky 服务器控制台上恢复记录的配置文件 zone（包括空值）：

```bash
sudo nmcli connection modify uuid "$LAB_UUID" connection.zone "$LAB_OLD_ZONE"
sudo firewall-cmd --get-zone-of-interface="$LAB_IF"
sudo firewall-cmd --get-zone-of-interface="$MGMT_IF"
```

检查哪些成功添加的规则仍然存在。**Rocky 服务器控制台，sudo：**

```bash
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE8000"
```

`yes` 表示规则存在；`no` 或非零退出状态表示规则不存在，例如试用超时后的状态。对你添加且仍存在的每条规则，**只运行对应的移除操作**：

```bash
sudo firewall-cmd --zone=network-beginner --remove-rich-rule="$RULE22"
sudo firewall-cmd --zone=network-beginner --remove-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --remove-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --remove-rich-rule="$RULE8000"
```

最后：

```bash
sudo firewall-cmd --permanent --delete-zone=network-beginner
sudo firewall-cmd --check-config
sudo firewall-cmd --reload
```

只删除现已不再使用的自有 zone；只有确认无关运行时状态安全后，才进行 reload。比较配置文件的原 zone、默认 zone、管理 zone/地址和基线策略。如果要继续第 7–8 课，应保留已验证并保存的实验 zone；回滚后按相同的试用/验证步骤重新应用。

## 3. 从客户端验证，并保留有限范围的证据

按照第 5 课的方法，从客户端建立一个**全新的、仅使用密钥的 SSH 连接**。保留的已建立连接不能测试新规则。对于 TCP 8000，请确保此前 HTTP 课程已准备 `python3`，并确认没有其他服务占用此端口。

**服务器控制台 A，普通用户：**

```bash
WEB_DIR=$(mktemp -d "$HOME/network-beginner-fw-web.XXXXXX")
printf '%s\n' "$WEB_DIR"
```

记录路径；如果为空/创建失败，请停止。然后：

```bash
printf 'firewall lesson\n' > "$WEB_DIR/index.html"
timeout 120 python3 -m http.server 8000 --bind 192.0.2.20 --directory "$WEB_DIR"
```

此命令只会在实验 IPv4 地址上提供临时目录内容，最长两分钟。不要在目录中放入秘密或符号链接。在**服务器控制台 B**中，`sudo ss -ltnp 'sport = :8000'` 应显示 `.20:8000`。

**客户端，普通用户：**

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/
```

预期 HTTP 200，且正文包含 `firewall lesson`。测试失败时，不应因此添加宽泛 allow：依次检查监听器、路由、zone/interface、来源和日志。检查配置以确认预期的来源限制；允许的客户端测试成功，**并未测试其他所有来源都遭到拒绝**。在 localhost/服务器自身上测试不等于从外部被拒绝的客户端发起测试。

服务器超时（状态码 124 属正常情况）或你按 Ctrl+C 停止后，在**服务器控制台 A，以普通用户身份**运行：`rm -i -- "$WEB_DIR/index.html"`，然后运行 `rmdir -- "$WEB_DIR"`。将管理地址/路由与 `FW_NOTE` 比较，并检查是否需要新建管理 SSH 登录。DHCP 续租也可能独立改变租约时间。

## 4. Rocky SELinux：修复标签，而不是整个策略

SELinux 是额外的进程/资源策略，与 Unix 所有者/权限模式和防火墙分离。**Enforcing** 会执行策略并记录拒绝；**permissive** 只记录本应拒绝的操作，但不强制执行；**disabled** 表示 SELinux 强制执行功能不存在。本实验不会切换模式。Ubuntu 通常使用 AppArmor；不要为了采用此替代分支而安装或切换到 SELinux。

**Rocky 服务器，以普通用户身份操作；使用 sudo 读取审核日志：**

```bash
getenforce
sestatus
ls -Z "$HOME"
sudo ausearch -m AVC,USER_AVC -ts recent -i
```

在已准备并启用 SELinux 的来宾系统上进行此练习。如果 SELinux 已禁用，请恢复正确准备的快照，不要尝试在线全局重新标记。使用 `ausearch` 需要安装 `audit` 工具。没有匹配项只表示该时间段内没有匹配的留存审核记录，并不能证明策略永远不会拒绝访问。

AVC 记录会指出尝试的权限、进程、对象、来源上下文（`scontext`）和目标上下文（`tcontext`）。请结合可执行文件/路径和时间一起阅读。SELinux 上下文通常采用 `user:role:type:level` 格式；**type** 是定向策略中的核心。不要盲目将每条拒绝记录都交给 `audit2allow`：标签错误或应用路径不正确往往才是原因。

**Rocky 服务器，以普通用户身份创建一个私有临时文件：**

```bash
SEL_DIR=$(mktemp -d "$HOME/network-beginner-selinux.XXXXXX")
printf '%s\n' "$SEL_DIR"
```

失败时停止并记录准确路径，然后：

```bash
touch "$SEL_DIR/probe.txt"
ls -Z "$SEL_DIR/probe.txt"
matchpathcon "$SEL_DIR/probe.txt"
sudo restorecon -v "$SEL_DIR/probe.txt"
matchpathcon -V "$SEL_DIR/probe.txt"
```

策略查询会提供此路径预期的上下文。首先确认基线；不要以为每一种 home 目录布局都使用同一 type。现在故意将文件设置为另一个已有 type，然后修复。

**Rocky 服务器，以普通用户身份操作；需要的地方调用 sudo：**

```bash
sudo chcon -t httpd_sys_content_t "$SEL_DIR/probe.txt"
ls -Z "$SEL_DIR/probe.txt"
sudo restorecon -n -v "$SEL_DIR/probe.txt"
sudo restorecon -v "$SEL_DIR/probe.txt"
matchpathcon -V "$SEL_DIR/probe.txt"
```

`chcon` 会更改此文件的标签，但不会创建持久文件上下文规则。`restorecon -n` 只预览不更改；`restorecon` 会恢复策略为该路径定义的标签。预期最终验证结果与策略一致。私有父目录表明本练习只用于熟悉标签，并非部署网页内容；没有故意让受限应用访问此文件，因此不能保证会产生 AVC。

持久化自定义路径时，可能需要先用 `semanage fcontext` 创建范围明确的映射，再运行 `restorecon`；本实验不需要这样做。清理时，**Rocky 服务器普通用户**运行 `rm -i -- "$SEL_DIR/probe.txt"` 和 `rmdir -- "$SEL_DIR"`。如果在 `chcon` 后中断，请先对文件运行相同的定向 `restorecon`，再清理。绝不要全局禁用 SELinux，也不要为了这个文件而重标记整个文件系统。

## 5. 可选软件包与 Rocky 9 EPEL/CRB {#epel-prerequisites}

不安装 Fail2ban 或 `iftop` 也能完成核心防火墙/SELinux 课程。本节还提供第 7 课中可选 `iftop` 路径所需的 Rocky 前置条件。软件包**只应通过管理连接安装到一次性来宾系统中**。

对于 **Ubuntu 服务器**，先检查 `apt-cache policy fail2ban python3-systemd`。如果已配置的 Ubuntu 仓库中存在候选版本，可运行 `sudo apt update`，然后运行 `sudo apt install fail2ban python3-systemd` 安装 Fail2ban 及其 journal 后端。如果没有候选版本，请检查官方仓库组件配置，不要添加随机下载源。

对于 **Rocky 9**，EPEL 是 Fedora 为 Enterprise Linux 提供的额外仓库；CRB 提供依赖项。不要因此使用 EPEL Next、不同的 EL 主版本或禁用软件包签名检查。

**Rocky 来宾系统，普通用户；记录原仓库/软件包状态：**

```bash
dnf repolist --all
rpm -q epel-release dnf-plugins-core fail2ban-server python3-systemd
```

记录 CRB/EPEL 是否已启用以及已安装哪些软件包；创建 `before-optional-packages` 快照。然后，**Rocky 来宾系统，普通用户调用 sudo**：

```bash
sudo dnf install dnf-plugins-core
sudo dnf config-manager --set-enabled crb
sudo dnf install epel-release
dnf repolist --enabled
dnf info fail2ban-server python3-systemd iftop
```

检查 EPEL 与 **9** 版本匹配、使用预期仓库/签名，且来宾系统架构存在候选版本。Fail2ban 使用 `sudo dnf install fail2ban-server python3-systemd`；第 7 课可选工具则只在此处安装 `iftop`。检查事务；如果依赖无法解决，请停止。软件包版本会变化，因此不假定具体构建版本。

如果 CRB/EPEL 在练习之前就已启用，或其他已安装软件需要它们，就不要禁用。如果这只是临时尝试，请在所有依赖课程完成后恢复 `before-optional-packages`。这是恢复软件包/仓库的准确回滚步骤；仅禁用仓库并不会卸载已安装软件包。

## 6. 可选 Fail2ban jail 与范围限定的操作

Fail2ban 通过**过滤器**读取身份验证失败日志，在 `findtime` 时间内统计事件，并在达到 `maxretry` 后调用**操作**。**Jail** 用于组合这些设置。Fail2ban 不能修复弱密钥、替代防火墙基线策略，也无法阻止所有分布式/低速攻击。过滤器/后端错误时，服务可能在运行却什么也检测不到。

此可选设置假设这是一个**全新的 Fail2ban 安装，且没有现有自定义 jail**。如果系统已在使用 Fail2ban，请先检查配置所有者；不要停止其他工作负载的防护。记录初始服务/启用状态。新安装可能会自动启动：准备期间应使用控制台，只停止此新服务 `sudo systemctl stop fail2ban`。检查 `/etc/fail2ban/jail.conf`、`jail.d` 和已安装的操作。不要编辑随软件包安装的 `jail.conf`。

为选定的管理器新建**一个**操作文件，并拒绝覆盖已有文件。

**服务器，普通用户调用 sudo：**

```bash
sudo sh -c 'umask 077; set -C; : > /etc/fail2ban/action.d/network-beginner.conf'
sudoedit /etc/fail2ban/action.d/network-beginner.conf
```

**仅用于 UFW**，将以下 INI 内容放入新文件，并将 `REPLACE_WITH_LAB_NIC` 替换为通过 MAC 验证过的服务器网卡名称。不要留下占位符。

```ini
[Definition]
actionstart =
actionstop =
actioncheck = LC_ALL=C ufw status | grep -q 'Status: active'
actionban = ufw insert 1 deny in on REPLACE_WITH_LAB_NIC proto tcp from <ip> to 192.0.2.20 port 22 comment 'network-beginner-ban'
actionunban = ufw delete deny in on REPLACE_WITH_LAB_NIC proto tcp from <ip> to 192.0.2.20 port 22
```

**仅用于 firewalld**，改用以下内容；课程 zone 仍必须只属于实验网卡：

```ini
[Definition]
actionstart =
actionstop =
actioncheck = firewall-cmd --zone=network-beginner --list-all
actionban = firewall-cmd --zone=network-beginner --add-rich-rule='rule family="ipv4" priority="-10" source address="<ip>" destination address="192.0.2.20/32" port port="22" protocol="tcp" reject'
actionunban = firewall-cmd --zone=network-beginner --remove-rich-rule='rule family="ipv4" priority="-10" source address="<ip>" destination address="192.0.2.20/32" port port="22" protocol="tcp" reject'
```

这些操作会将检测到的来源限制为**实验接口/zone、目标 `.20`、TCP 22**；不会封禁该来源访问管理地址或 TCP 8000。UFW 将规则插入 allow 之前，firewalld 使用负 priority，使临时拒绝优先于实验 allow。Fail2ban 会在 `bantime` 后移除规则；此可选实验期间不要 reload 底层防火墙。此计时器由 Fail2ban 管理，并非 UFW 规则自身的计时器：如果守护进程失败，请根据准确的 `actionunban` 规格检查并仅移除遗留的课程封禁，不要假定封禁已自动到期。

**服务器，普通用户调用 sudo；独占创建 jail：**

```bash
sudo sh -c 'umask 077; set -C; : > /etc/fail2ban/jail.d/99-network-beginner.local'
sudoedit /etc/fail2ban/jail.d/99-network-beginner.local
```

**Ubuntu** 使用此 INI。在 **Rocky** 上，只将 `journalmatch` 中的 `ssh.service` 替换为 `sshd.service`。

```ini
[sshd]
enabled = false

[network-beginner-sshd]
enabled = true
filter = sshd
backend = systemd
journalmatch = _SYSTEMD_UNIT=ssh.service
usedns = no
ignoreip = 127.0.0.0/8 ::/0
port = 22
maxretry = 3
findtime = 60
bantime = 60
action = network-beginner
```

`[sshd]` 设置会阻止软件包提供的默认 SSH jail 在此**全新**安装上再应用一个范围更宽的操作。确认没有启用其他 jail；不要借此禁用现有自定义防护。命名 jail 显式使用 `sshd` 过滤器和新操作。`backend=systemd` 会读取 journal，因此**不要**添加 `logpath`。`journalmatch` 必须匹配实际日志单元元数据。`::/0` 有意将 IPv6 排除在这个仅 IPv4 演示之外；它不是生产防护策略。

**服务器，普通用户调用 sudo；启动前验证：**

```bash
sudo journalctl -u ssh.service -b -n 10 -o verbose --no-pager
sudo fail2ban-client -t
sudo fail2ban-client -d
```

在 Rocky 上使用 `-u sshd.service`。检查实际身份验证相关记录中的 `_SYSTEMD_UNIT`；没有匹配记录表示后端覆盖范围仍未得到验证。`-t` 测试配置，`-d` 显示解析后的配置而不启动强制执行。验证 jail 名称、journal 后端/匹配条件、仅一个预期操作、有限时长，以及没有互相竞争的已启用 jail。

**服务器，普通用户调用 sudo：**

```bash
sudo systemctl start fail2ban
sudo fail2ban-client status
sudo fail2ban-client status network-beginner-sshd
sudo fail2ban-client get network-beginner-sshd journalmatch
sudo fail2ban-client get network-beginner-sshd actions
sudo fail2ban-client get network-beginner-sshd action network-beginner actionban
sudo journalctl -u fail2ban -b -n 30 --no-pager
```

预期会显示指定 jail 和展开后的范围化操作命令，并且没有启动错误。零失败/封禁属正常情况。**不要运行暴力破解循环，也不要故意封禁自己**。这些检查只能证明配置/启动情况，不能证明已验证攻击检测或强制执行。服务元数据错误、缺少 Python journal 支持、过滤器不匹配或操作执行错误，都必须在声称防护有效之前解决。

如果意外封禁列表中出现已知实验客户端，**服务器控制台，sudo：**

```bash
sudo fail2ban-client set network-beginner-sshd unbanip 192.0.2.10
sudo fail2ban-client status network-beginner-sshd
```

这会请求精确解除单个 IP 的封禁。验证相应 UFW/rich 规则已不存在，并成功建立新的 SSH 连接；已有会话不够。不要清空所有封禁或防火墙规则。

清理时，对**此 jail** 中实际列出的 IP 地址逐一解除封禁，并确认相应操作规则已移除。随后运行 `sudo fail2ban-client stop network-beginner-sshd`；只有服务最初处于禁用状态/属于新服务时才停止它；并通过 `sudo rm -i -- /etc/fail2ban/jail.d/99-network-beginner.local /etc/fail2ban/action.d/network-beginner.conf` 只移除本课创建的两个文件。确认 jail 已消失且没有课程封禁残留。必须在**删除 firewalld zone 之前**完成此操作。恢复记录的服务/启用状态；完整回滚可选安装时使用快照。

## 完成检查与课程衔接

你应该能够展示所选的管理器、正确接口/zone、针对 `.10`→`.20` 的确切 TCP 22/8000 规则、新建的允许 SSH/HTTP 连接、未更改的管理路径以及反向操作。说明 UFW 已保存规则与 firewalld 运行时/持久规则的差别，以及正确文件模式与正确 SELinux type 的差别。除非有额外的有效证据，否则可选 Fail2ban 应报告为“配置已验证”。

[第 7 课](07-monitoring-performance.md)继续使用已验证的**持久防火墙策略**。如果你练习了移除规则，请先重新应用并验证。下一课不要求保留 HTTP 进程、故意设置错误的标签或临时 Fail2ban jail。

不再需要基线文件时，从 `FW_NOTE` 中仅移除确切创建的文件（`management.before`、`routes.before` 及所选分支列出的基线文件），然后 `rmdir` 空目录。只有在课程全部结束时才恢复记录的配置文件/防火墙状态。不要只因 zone/规则名称看起来熟悉就删除未知对象。

## 主要参考资料

截至 2026 年 9 月 15 日检查：

- [Ubuntu UFW 手册](https://manpages.ubuntu.com/manpages/noble/man8/ufw.8.html)：规则方向、接口、顺序、持久化和精确删除。
- [firewalld CLI](https://firewalld.org/documentation/man-pages/firewall-cmd.html)、[rich language](https://firewalld.org/documentation/man-pages/firewalld.richlanguage.html) 和 [zone](https://firewalld.org/documentation/zone/connections-interfaces-and-sources.html)：超时、reload、来源/目标规则及分类。
- [NetworkManager 连接设置](https://networkmanager.dev/docs/api/latest/settings-connection.html)：活动连接的 `zone` 即时更改以及空值/默认行为。
- [Rocky Linux 9 SELinux 指南](https://docs.rockylinux.org/9/guides/security/learning_selinux/) 和 [SELinux 标记工具](https://github.com/SELinuxProject/selinux/tree/main/policycoreutils/setfiles)：AVC 诊断及定向上下文恢复。
- [Fedora EPEL 入门](https://docs.fedoraproject.org/en-US/epel/getting-started/)、[Rocky 仓库文档](https://wiki.rockylinux.org/rocky/repo/) 和 [EPEL Fail2ban 软件包](https://packages.fedoraproject.org/pkgs/fail2ban/fail2ban-server/)：可选软件包来源和前置条件。
- [Fail2ban jail 配置](https://github.com/fail2ban/fail2ban/blob/master/config/jail.conf)、[systemd 后端](https://github.com/fail2ban/fail2ban/blob/master/fail2ban/server/filtersystemd.py) 和 [client 手册](https://manpages.ubuntu.com/manpages/noble/man1/fail2ban-client.1.html)：过滤器/后端/操作的分工、配置测试、状态和范围化解除封禁。

[测验](../../quizzes/networking/beginner/06-firewalls-host-security-quiz.md) | [继续学习监控](07-monitoring-performance.md)
