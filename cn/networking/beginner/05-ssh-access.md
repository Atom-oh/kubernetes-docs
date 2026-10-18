# 5. 使用 SSH 远程访问

> **支持版本**：Ubuntu Server 24.04 LTS（主要路径）、Rocky Linux 9（备用路径）
> **最后更新**：2026 年 9 月 15 日

[上一课：DNS 与连通性](04-dns-connectivity.md) | [课程目录](README.md) | [测验](../../quizzes/networking/beginner/05-ssh-access-quiz.md) | [下一课：主机安全](06-firewalls-host-security.md)

SSH 可以让你在另一台计算机上使用加密终端。仅有加密还不够：客户端必须识别服务器，服务器也必须验证你的账户。修改登录策略前，我们会分别确认这两种身份。

## 先决条件、学习成果与恢复边界

请先完成第 1–4 课。客户端 `192.0.2.10/24` 和服务器 `192.0.2.20/24` 使用经过 MAC 验证、仅供内部使用的 NIC；实验网络上没有 DHCP、网关或上行链路。独立的 NAT/DHCP 管理 NIC 保持不变。使用普通账户，**并在整个过程中保持服务器的虚拟机监控程序控制台打开**。你需要服务器上的 sudo 权限、服务器普通账户密码或用于安装公钥的控制台访问权限，以及用于下载软件包的现有管理连接。

你将安装/检查 SSH 工具、验证主机指纹、创建带口令的用户密钥、仅安装其公钥、通过第二次独立的仅密钥登录进行验证、检查服务器的生效配置，并撤销自己的更改。所有示例均为说明用途，**不是在真实虚拟机中运行的记录**。每条命令都应在指定的来宾系统上运行，绝不要在物理主机或用于阅读本文的主机上运行。出现任何意外错误时都应停止。

为两台来宾系统创建名为 `before-ssh-lesson` 的快照。安装前记录现有 SSH 监听器以及服务/套接字状态。恢复快照是完整撤销软件包及其依赖项更改的方式；卸载软件包不能精确还原原状。不要为了让实际配置符合示例而替换现有密钥或配置文件。

## 1. 找出客户端和服务器

**SSH 客户端**是你用来发起连接的 `ssh` 命令。**SSH 服务器**是等待连接的 `sshd`，通常监听 TCP 22 端口。**主机密钥**属于服务器，用来证明服务器身份。**用户密钥**属于你，用来证明你有权使用某个账户。指纹是公钥的简短表示，可以通过可信渠道进行比对。

**在两台来宾系统上以普通用户身份执行；先检查：**

```bash
hostname
cat /etc/os-release
ip -br link
ip -4 -br address
command -v ssh
```

将 NIC 的 MAC 地址与虚拟机监控程序中的记录对应起来，并确认各自的角色地址。在客户端执行 `ip -4 route get 192.0.2.20`，应显示使用实验 NIC 和源地址 `.10`；具体解释见第 2 课。

**Ubuntu 服务器，以普通用户身份记录状态；只有在缺少时才安装：**

```bash
dpkg-query -W openssh-server
systemctl status ssh.service ssh.socket --no-pager
```

如果缺少，请依次执行 `sudo apt update` 和 `sudo apt install openssh-server`。Ubuntu 24.04 安装可能会通过 `ssh.socket` 激活套接字；服务名称仍是 `ssh.service`。请检查两者，不要禁用套接字。本课保留已有的监听地址/端口，因此不需要更改套接字绑定。

**Rocky 服务器，以普通用户身份记录状态；只有在缺少时才安装：**

```bash
rpm -q openssh-server
systemctl status sshd.service --no-pager
```

如果缺少，请执行 `sudo dnf install openssh-server`。Ubuntu 客户端的工具由 `openssh-client` 提供，Rocky 客户端的工具由 `openssh-clients` 提供。如有缺失，请按照第 1 课的发行版软件包操作流程安装对应的软件包。检查事务内容；不要为了安装 OpenSSH 添加软件仓库。

在**服务器**上检查发行版后，设置一个服务变量：

```bash
# Ubuntu server only:
SSH_UNIT=ssh.service
```

```bash
# Rocky server only:
SSH_UNIT=sshd.service
```

**在服务器上以普通用户身份执行，并在标注处调用 sudo：**

```bash
sudo /usr/sbin/sshd -t
sudo systemctl start "$SSH_UNIT"
systemctl cat "$SSH_UNIT"
systemctl status "$SSH_UNIT" --no-pager
sudo ss -ltnp 'sport = :22'
```

`sshd -t` 用于检查配置和密钥是否有效；成功时通常不输出内容。验证报错时不要启动/重新加载服务。`start` 只影响当前运行状态，不会启用开机启动。`systemctl cat` 会显示单元文件和覆盖配置：本流程假定使用默认配置路径。如果自定义 `ExecStart`/环境选项设置了 `-f` 或 `-o`，后续验证和生效配置检查时也要使用相同选项，否则检查的就不是同一份配置。`0.0.0.0:22`/`[::]:22` 监听范围大于实验地址；它不是按来源限制的设置。不要在此处更改网络绑定，以免失去管理访问。第 6 课会按来源和接口限制实验流量。

如果当前防火墙阻止实验连接，请只执行第 6 课中**与你的防火墙相符的分支**，允许 `.10` 到 `.20` 的 TCP 22 流量，然后返回本课。保持控制台可用，不要关闭防火墙。“Connection refused”通常表示没有监听器或连接被拒绝；超时可能表示流量被过滤或路径故障。请按照第 4 课中的证据收集顺序排查。

## 2. 通过服务器控制台验证主机密钥

**在服务器虚拟机监控程序控制台上以普通用户身份执行，并在标注处调用 sudo：**

```bash
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

记录完整的 `SHA256:...` 指纹，并确认它是 **ED25519 主机密钥**。此处是公开的主机公钥路径，不是之后创建的用户密钥。绝不要打印或复制 `/etc/ssh/ssh_host_ed25519_key` 及其私钥。此路径假设来宾系统采用常规的非 FIPS 基线；如果加密策略不允许使用 Ed25519，应改走获批的算法流程，而不是禁用安全策略。

**客户端，以普通用户身份执行：**

```bash
SSH_LAB_DIR=$(mktemp -d "$HOME/network-beginner-ssh.XXXXXX")
printf '%s\n' "$SSH_LAB_DIR"
read -r -p 'Normal account name on the server: ' SERVER_USER
```

记录目录和账户；如果创建失败、路径为空或账户是 root，请停止。这个私有目录用于存放本课程专用密钥和主机记录，不会改动现有的 `~/.ssh` 客户端文件。

**客户端，以普通用户身份执行：**

```bash
ssh -o HostKeyAlgorithms=ssh-ed25519 \
  -o UserKnownHostsFile="$SSH_LAB_DIR/known_hosts" \
  -o StrictHostKeyChecking=ask \
  "$SERVER_USER@192.0.2.20"
```

首次出现主机密钥提示时，将**完整指纹**与服务器控制台显示的值进行比较。只有完全匹配时才输入 `yes`。如果不同，请停止并检查虚拟机/地址；不要禁用主机密钥检查，也不要盲目删除已保存的记录。`ssh-keyscan` 可以收集密钥，但仅靠它无法证明密钥来自谁。

如果允许密码登录，请输入**服务器账户密码**，然后远程检查 `hostname`、`whoami` 和 `printf '%s\n' "$SSH_CONNECTION"`；之后执行 `exit` 回到客户端。`SSH_CONNECTION` 包含客户端 IP/端口和服务器 IP/端口；应看到实验地址 `.10` 和 `.20`。保留独立的虚拟机监控程序控制台。如果密码登录已禁用，仍可先完成主机密钥验证，然后在身份验证阶段失败；此时使用下方的控制台安装方式，不要为了本课启用密码登录。

## 3. 创建用户密钥并准备服务器权限

**客户端，以普通用户身份在同一个 Shell 中执行：**

```bash
ssh-keygen -t ed25519 -a 64 -f "$SSH_LAB_DIR/id_ed25519" \
  -C "network-beginner-$(basename "$SSH_LAB_DIR")"
ssh-keygen -lf "$SSH_LAB_DIR/id_ed25519.pub"
ls -l "$SSH_LAB_DIR"
```

输入两次非空口令。它用于加密磁盘上的私钥，不是服务器账户密码。`-a 64` 用于指定密钥派生的工作因子。`id_ed25519` 留在客户端；只有 `id_ed25519.pub` 会发送到服务器。单独的目录可以避免意外替换现有密钥。如果提示覆盖的对象出乎意料，请停止，不要回答 yes。

安装前，请为 `SERVER_USER` 中指定的**同一个服务器普通账户**准备一份恢复记录。

**在服务器控制台上使用该普通账户登录：**

```bash
SERVER_NOTE=$(mktemp -d "$HOME/network-beginner-ssh-state.XXXXXX")
printf '%s\n' "$SERVER_NOTE"
stat -c '%a %U %n' "$HOME"
ls -ld "$HOME/.ssh" "$HOME/.ssh/authorized_keys"
```

如果目录创建失败或打印的路径为空，请停止。记录新目录路径以及 home 目录原有的权限模式。对于新账户，`.ssh` 或 `authorized_keys` 显示“No such file”属于正常情况；请记录哪些路径原本不存在。如果它们存在，请用 `stat -c '%a %U %n'` 记录数字权限模式并检查所有权。如果其中任一路径是符号链接、所有者不同、ACL 出乎预期，或由其他系统管理，请停止并协调所有权问题，不要递归更改。

如果 `authorized_keys` 已存在，**服务器普通用户**可执行：`cp -p -- "$HOME/.ssh/authorized_keys" "$SERVER_NOTE/authorized_keys.before"`，在新目录中创建备份。更改前也要记录 `.ssh` 的权限模式。仅当 `.ssh` 不存在时才执行 `mkdir -m 700 -- "$HOME/.ssh"` 创建。对于此账户，执行 `chmod go-w "$HOME"` 和 `chmod 700 "$HOME/.ssh"`；记录原始模式，以便之后恢复。OpenSSH 的严格检查会拒绝所有权不安全或组/其他用户可写的路径。不要递归运行 `chmod`，也不要移动他人的密钥。

## 4. 安装公钥并验证仅密钥访问

**客户端，以普通用户身份执行：**

```bash
ssh-copy-id -i "$SSH_LAB_DIR/id_ed25519.pub" \
  -o UserKnownHostsFile="$SSH_LAB_DIR/known_hosts" \
  -o StrictHostKeyChecking=yes \
  "$SERVER_USER@192.0.2.20"
```

`ssh-copy-id` 使用现有身份验证方式，将所选公钥追加到服务器账户的 `~/.ssh/authorized_keys`；它不会复制私钥。查看添加的密钥数量。应当添加你的一个密钥，或报告该密钥已安装。不要使用强制模式添加重复密钥。

**无法使用密码/引导阶段 SSH 时的控制台替代方式**：在客户端仅显示 `cat "$SSH_LAB_DIR/id_ed25519.pub"` 的结果。在服务器控制台上以目标用户身份打开 `nano "$HOME/.ssh/authorized_keys"`，并将整条公钥行**追加到文件中**，保留原有行。保存后，用 `ssh-keygen -lf "$HOME/.ssh/authorized_keys"` 与客户端的用户密钥指纹进行比较。这不是第 2 步中的主机密钥指纹。

**在服务器控制台上，以目标普通用户身份执行：**

```bash
chmod 600 "$HOME/.ssh/authorized_keys"
ls -ld "$HOME" "$HOME/.ssh"
ls -l "$HOME/.ssh/authorized_keys"
ssh-keygen -lf "$HOME/.ssh/authorized_keys"
```

确认目标账户是所有者、`.ssh` 权限为私有，并且新公钥指纹出现在已有条目中。在启用 SELinux 的 Rocky 系统上，如果标准 home 路径标签错误，还要执行 `sudo restorecon -v "$HOME/.ssh" "$HOME/.ssh/authorized_keys"`；第 6 课会说明为什么 Unix 权限并非全部安全策略。

**客户端控制台 A，以普通用户身份打开并保持此会话：**

```bash
ssh -i "$SSH_LAB_DIR/id_ed25519" -o IdentitiesOnly=yes \
  -o PreferredAuthentications=publickey \
  -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no \
  -o ControlMaster=no -o ControlPath=none \
  -o UserKnownHostsFile="$SSH_LAB_DIR/known_hosts" \
  -o StrictHostKeyChecking=yes "$SERVER_USER@192.0.2.20"
```

出现私钥口令提示是预期行为。仅密钥测试中不应提示输入远程账户密码。`IdentitiesOnly` 限制所提供的密钥；禁用连接共享可确保你测试的是一次新的身份验证，而不是复用多路复用会话。

在这个**远程服务器会话**中，运行 `whoami` 和 `printf '%s\n' "$SSH_CONNECTION"`，并保持会话打开。现在打开**客户端控制台 B**，将 `SSH_LAB_DIR` 设置为所记录的客户端准确目录，并将 `SERVER_USER` 设置为相同账户，然后重复执行上面的**完整仅密钥命令**。再次确认账户和 `.10`→`.20` 连接。只有第二次独立登录成功，才能完成这项检查。

如果你已经通过**管理 NIC**使用 SSH，在禁用服务器范围的密码身份验证前，要对每一条必须保留的管理账户/路径重复进行仅密钥测试。仅有现存会话并不足够。如果无法验证某条必要路径，请保留当前身份验证策略并完成准备工作；NIC 的 IP 地址没有变化，不代表登录访问一定不受影响。

## 5. 强化前检查配置优先级

**服务器控制台，以普通用户身份执行，并在标注处调用 sudo：**

```bash
sudo cat /etc/ssh/sshd_config
sudo ls -la /etc/ssh/sshd_config.d
sudo grep -RnsE '^[[:space:]]*(Include|Match|PasswordAuthentication|KbdInteractiveAuthentication|PermitRootLogin|PubkeyAuthentication|AuthenticationMethods|AuthorizedKeysFile)' \
  /etc/ssh/sshd_config /etc/ssh/sshd_config.d
```

读取实际包含的配置文件，包括 `Include` 指令引用的其他路径；`grep` 只是辅助工具，并非完整解析器。OpenSSH 通常使用某个关键字**首次取得的值**。Include 会在其出现位置处理，通配符匹配的文件名按字典顺序排列。适用于该连接的 `Match` 块可以覆盖全局值；多个适用的 Match 赋值之间也存在顺序影响。较晚处理的 `99-...conf` 文件不一定能可靠覆盖前面的设置。

本练习会创建一个**新的、仅含全局设置的 drop-in 文件**，因此主文件的全局部分必须有生效的 `/etc/ssh/sshd_config.d/*.conf` Include。确认较早的赋值不会使其失效。不要在本课程创建的 drop-in 文件中加入 `Match` 块，也不要为改变优先级而编辑无关的 Include 文件。如果现有配置布局无法按预期支持新文件，请停止加固步骤并调查所有者/布局，同时保留可用的访问方式。

**在服务器控制台中重新设置目标账户：**

```bash
read -r -p 'Normal SSH account on this server: ' SERVER_USER
SSH_CASE="user=$SERVER_USER,addr=192.0.2.10,host=net-client,laddr=192.0.2.20,lport=22"
sudo /usr/sbin/sshd -T -C "$SSH_CASE"
```

`-T` 会输出生效配置；`-C` 会提供假设的连接参数，以便评估 Match 规则。`host` 描述的是用于匹配主机名的连接端主机，而不是服务器主机名。本课程不依赖基于主机名的 Match 规则；如果你的配置使用了这类规则，请使用 sshd 实际评估的名称。检查 `pubkeyauthentication`、`passwordauthentication`、`kbdinteractiveauthentication`、`permitrootlogin`、`authenticationmethods` 和 `authorizedkeysfile`。即使配置有效，`AllowUsers`、`DenyUsers`、组限制、PAM 或账户状态仍可能导致账户被拒绝。

添加任何内容之前，先保存生效配置基线：

```bash
sudo /usr/sbin/sshd -T -C "$SSH_CASE" > "$SERVER_NOTE/effective.before"
sudo /usr/sbin/sshd -T -C \
  'user=root,addr=192.0.2.10,host=net-client,laddr=192.0.2.20,lport=22' \
  > "$SERVER_NOTE/root-effective.before"
```

对任何需要保留的管理 SSH 路径，也使用其真实来源/本地地址和账户记录对应基线。不要用示例地址替代实际管理端点。

## 6. 添加一个自有策略文件，验证、重新加载并复测

只有在第二次仅密钥登录和必要的管理路径测试均成功后，才能继续。这些设置会更改**服务器范围的身份验证**，并受到生效 Match 规则影响；它们不会更改 NIC 配置。

**服务器控制台，以普通用户身份执行并调用 sudo；采用独占创建方式：**

```bash
sudo sh -c 'umask 077; set -C; : > /etc/ssh/sshd_config.d/00-network-beginner.conf'
sudoedit /etc/ssh/sshd_config.d/00-network-beginner.conf
```

`set -C` 会拒绝覆盖现有文件。如果失败，请停止：没有恢复记录时，不要编辑或删除之前的尝试。将以下**配置文本**写入刚创建的文件：

```text
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
```

单独设置 `PasswordAuthentication no` 并不会禁用类似密码的 keyboard-interactive/PAM 身份验证。保留普通用户密钥登录并通过 sudo 执行管理操作，可以避免直接通过 SSH 登录 root。不要全局禁用 PAM。

**服务器控制台，以普通用户身份执行并调用 sudo：**

```bash
sudo /usr/sbin/sshd -t
sudo /usr/sbin/sshd -T -C "$SSH_CASE"
sudo /usr/sbin/sshd -T -C \
  'user=root,addr=192.0.2.10,host=net-client,laddr=192.0.2.20,lport=22'
```

只有在语法检查通过，且预期连接的配置显示 `pubkeyauthentication yes`、密码/keyboard-interactive 均为 `no`、`permitrootlogin no` 时，才可继续。对必需的管理路径重复有效配置检查。如果更早的设置或 Match 规则优先生效，**不要重新加载**：只移除你新建的文件，验证恢复后的配置，然后调查优先级。随意重命名文件并不能解决问题。

**服务器控制台，以普通用户身份执行并调用 sudo：**

```bash
sudo systemctl reload "$SSH_UNIT"
systemctl status "$SSH_UNIT" --no-pager
sudo journalctl -u "$SSH_UNIT" -b -n 30 --no-pager
```

重新加载会要求运行中的守护进程重新读取配置。这不是防火墙重新加载，也不会改变套接字绑定。保持控制台和原有会话打开，然后按照第 4 步**再建立一次新的客户端仅密钥登录**，并重新检查管理 SSH 路径。旧的已验证会话仍在，并不能证明新的登录可用。

## 完成与精确恢复

成功标准包括：主机指纹已验证、使用带口令的专用用户密钥、所有权/权限正确、加固前完成第二次新的登录、相关账户/路径的 `-T -C` 结果符合预期，以及重新加载后再次成功建立新登录。请说明身份验证失败与 TCP 连接被拒绝的区别。

从**服务器控制台**练习回滚策略：

```bash
sudo rm -i -- /etc/ssh/sshd_config.d/00-network-beginner.conf
sudo /usr/sbin/sshd -t
sudo /usr/sbin/sshd -T -C "$SSH_CASE" > "$SERVER_NOTE/effective.restored"
diff -u "$SERVER_NOTE/effective.before" "$SERVER_NOTE/effective.restored"
sudo /usr/sbin/sshd -T -C \
  'user=root,addr=192.0.2.10,host=net-client,laddr=192.0.2.20,lport=22' \
  > "$SERVER_NOTE/root-effective.restored"
diff -u "$SERVER_NOTE/root-effective.before" "$SERVER_NOTE/root-effective.restored"
```

确认只删除你创建的文件。没有 diff 输出表示普通账户的生效基线一致；也要检查 root 和记录过的管理场景。如果其他管理员/配置管理系统在此期间更改了状态，请调查差异，而不要恢复整个旧目录。只有在语法和预期恢复后的值均通过检查后，才重新加载 `$SSH_UNIT`；然后验证新登录。如果加固后新的登录失败，也使用这一控制台流程恢复。

如果要保留本课程的加固设置，可以在相同的验证门控下重新应用自有 drop-in 文件。否则，按以下顺序完成清理：

1. **服务器目标账户**：用 nano 打开 `~/.ssh/authorized_keys`，只删除带有本课程注释、且用户密钥指纹与记录相符的那一行。保留所有无关密钥。与 `"$SERVER_NOTE/authorized_keys.before"`（如果该文件原先存在）进行对照。恢复记录中的数字权限模式。如果文件原先不存在且现在为空，只删除这个空文件；仅当 `.ssh` 是你创建且已经清空时，才用 `rmdir` 删除。若 home/`.ssh` 原先存在，则恢复记录的权限模式。对于共享账户，应协调并处理并发更改，不要用备份覆盖。
2. **客户端**：结束课程会话并撤销公钥后，在记录的 `SSH_LAB_DIR` 中用 `rm -i` 仅删除 `id_ed25519`、`id_ed25519.pub` 和 `known_hosts`，然后执行 `rmdir "$SSH_LAB_DIR"`。如果目录中还有其他文件，请检查其准确名称；不要递归删除。现有客户端 SSH 文件没有被替换。
3. **服务器**：确认后删除 `SERVER_NOTE` 中本课准确创建的基线/备份文件，然后移除空目录。记录你创建过的管理基线文件名，确保清理范围明确。
4. 仅当你更改了**记录的**服务/套接字运行状态且后续课程不再需要 SSH 时，才将其恢复。如果 Ubuntu 原先启用了套接字激活，请保留该套接字；不要因为服务一开始处于非活动状态就禁用它。如果你新装了软件包，为后续课程保留它们是合理的；完整回滚软件包需要恢复快照，这也会丢弃之后的来宾系统工作。

## 主要参考资料

核对日期：2026 年 9 月 15 日

- [Ubuntu Server OpenSSH](https://documentation.ubuntu.com/server/how-to/security/openssh-server/)：安装、`ssh.service` 和 Include 优先级。
- [Ubuntu 24.04 发行说明](https://discourse.ubuntu.com/t/noble-numbat-release-notes/39890)：OpenSSH 套接字激活和套接字配置生成器。
- [Rocky Linux OpenSSH 密钥设置](https://docs.rockylinux.org/9/guides/security/ssh_public_private_keys/)：Rocky 的 OpenSSH 工作流程。
- [OpenSSH `ssh`](https://man.openbsd.org/ssh)、[`ssh-keygen`](https://man.openbsd.org/ssh-keygen)、[`sshd`](https://man.openbsd.org/sshd)和 [`sshd_config`](https://man.openbsd.org/sshd_config)：身份、密钥、验证、Include/Match 和生效设置。
- [Ubuntu 24.04 `ssh-copy-id`](https://manpages.ubuntu.com/manpages/noble/man1/ssh-copy-id.1.html)：安装所选密钥并处理已有密钥。

[测验](../../quizzes/networking/beginner/05-ssh-access-quiz.md) | [继续学习主机安全](06-firewalls-host-security.md)
