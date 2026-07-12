# Linux 基础测验

本测验用于测试你对 Linux 基本概念的理解，这些概念构成 Kubernetes 和容器技术的基础。

## 选择题

1. 以下哪一项不是 Linux kernel 的主要职责？
   - A) Process 管理
   - B) Memory 管理
   - C) 提供用户界面
   - D) Device 管理
<details>

<summary>显示答案</summary>

**答案: C) 提供用户界面**

**解释:**
Linux kernel 是操作系统的核心，充当硬件与软件之间的中介。kernel 的主要职责包括 process 管理、memory 管理、device 管理，以及提供 system call 接口。用户界面（GUI、CLI）由运行在 user space 中的独立程序提供，并不是 kernel 的职责。

</details>

2. 以下哪一项不是 Linux namespace 的类型？
   - A) PID namespace
   - B) Network namespace
   - C) Memory namespace
   - D) User namespace
<details>

<summary>显示答案</summary>

**答案: C) Memory namespace**

**解释:**
Linux 有以下 namespace：PID (Process ID)、Network、Mount、UTS (hostname)、IPC (Inter-Process Communication)、User 和 cgroup namespace。Memory namespace 不存在。Memory 隔离主要通过 cgroups 管理。

</details>

3. cgroups (Control Groups) 的主要功能是什么？
   - A) 限制和隔离 process group 的资源使用
   - B) 控制文件系统访问
   - C) 过滤网络数据包
   - D) 管理用户认证
   
<details>

<summary>显示答案</summary>

**答案: A) 限制和隔离 process group 的资源使用**

**解释:**
cgroups 是 Linux kernel 的一项功能，用于限制和隔离 process group 的资源使用。它可以限制并监控 CPU 时间、memory、block I/O 和网络带宽等资源的使用。这是实现容器中资源限制的核心技术。
</details>

4. 在文件权限 "rwxr-xr--" 中，group 用户的权限是什么？
   - A) 读取、写入、执行
   - B) 读取、执行
   - C) 只读
   - D) 仅执行
   
<details>

<summary>显示答案</summary>

**答案: B) 读取、执行**

**解释:**
在文件权限 "rwxr-xr--" 中：
  - 前 3 个字符 (rwx)：Owner 权限 - 读取、写入、执行
  - 中间 3 个字符 (r-x)：Group 权限 - 读取、执行
  - 后 3 个字符 (r--)：Other users 权限 - 只读

因此，group 用户具有读取和执行权限。

</details>

5. 哪种文件系统主要用于实现容器镜像层？
   - A) ext4
   - B) XFS
   - C) OverlayFS
   - D) Btrfs

<details>

<summary>显示答案</summary>

**答案: C) OverlayFS**

**解释:**
OverlayFS 是一种 union mount 文件系统，它将多个目录叠加起来并呈现为单个目录。它主要被 Docker 等 container runtime 用于实现镜像层。这允许 base image 保持只读，同时为每个容器添加一个可写层。
</details>

6. 使用 systemctl 命令管理服务时，哪个命令会设置服务在启动时自动启动？
   - A) systemctl start
   - B) systemctl enable
   - C) systemctl restart
   - D) systemctl reload

<details>

<summary>显示答案</summary>

**答案: B) systemctl enable**

**解释:**
`systemctl enable` 会设置服务在系统启动时自动启动。`start` 会立即启动服务，`restart` 会重启服务，而 `reload` 只会重新读取配置文件。在 Kubernetes node 上，kubelet 和 containerd 等核心服务应使用 `systemctl enable` 配置自动启动。
</details>

7. 哪个 kernel 参数对 Kubernetes cluster 设置至关重要，用于为容器网络启用 IP 数据包转发？
   - A) net.ipv4.tcp_syncookies
   - B) net.ipv4.ip_forward
   - C) net.core.somaxconn
   - D) fs.file-max

<details>

<summary>显示答案</summary>

**答案: B) net.ipv4.ip_forward**

**解释:**
`net.ipv4.ip_forward` 是在 Linux kernel 中启用 IP 数据包转发的设置。必须将此设置设为 1，才能启用容器之间以及容器与外部网络之间的通信。设置 Kubernetes node 时必须启用此参数，并且可以使用命令 `sysctl -w net.ipv4.ip_forward=1` 进行设置。
</details>

8. 在 systemd unit 文件中，哪个指令用于定义某个服务应在特定服务之后启动？
   - A) Requires
   - B) Wants
   - C) After
   - D) Before

<details>

<summary>显示答案</summary>

**答案: C) After**

**解释:**
在 systemd unit 文件中，`After` 定义当前 unit 应在指定 unit 之后启动。例如，`After=network-online.target` 确保服务在网络就绪后启动。`Requires` 定义强依赖，`Wants` 定义弱依赖，而 `Before` 表示当前 unit 应在另一个 unit 之前启动。
</details>

9. CNI plugin 正常工作需要哪个 kernel 参数，以允许 bridge traffic 通过 iptables？
   - A) net.ipv4.ip_forward
   - B) net.bridge.bridge-nf-call-iptables
   - C) net.core.netdev_max_backlog
   - D) net.ipv4.tcp_max_syn_backlog

<details>

<summary>显示答案</summary>

**答案: B) net.bridge.bridge-nf-call-iptables**

**解释:**
`net.bridge.bridge-nf-call-iptables` 配置 bridged network traffic 通过 iptables 规则。此设置对于 Kubernetes CNI plugin（Calico、Flannel 等）正确应用网络策略和 service 路由至关重要。要启用此设置，必须先加载 `br_netfilter` kernel module。
</details>

10. 在包管理中，Ubuntu/Debian 上使用哪个命令来防止 Kubernetes 组件自动升级？
    - A) apt lock
    - B) apt-mark hold
    - C) apt freeze
    - D) apt pin

<details>

<summary>显示答案</summary>

**答案: B) apt-mark hold**

**解释:**
`apt-mark hold` 会固定特定包以防止自动升级。在 Kubernetes cluster 中，kubelet、kubeadm 和 kubectl 的版本兼容性很重要，因此建议使用命令 `sudo apt-mark hold kubelet kubeadm kubectl` 固定版本。在 RHEL/CentOS 上，使用 `yum versionlock` 命令。
</details>

## 简答题

11. 一个 process 已经终止，但其 parent process 尚未检查其状态，这个 process 被称为什么？

<details>

<summary>显示答案</summary>

**答案: Zombie Process（僵尸进程）**

**解释:**
Zombie Process（僵尸进程）是指已经完成执行，但由于 parent process 尚未通过 `wait()` system call 检查其退出状态而仍保留在 process table 中的 process。Zombie process 几乎不使用资源，但如果大量累积，process table 可能会被占满，从而阻止创建新的 process。
</details>

12. 隔离 process 的 network stack 的 Linux namespace 名称是什么？

<details>

<summary>显示答案</summary>

**答案: Network Namespace**

**解释:**
network namespace 隔离 network stack（network interfaces、routing tables、firewall rules、sockets 等）。这允许每个容器拥有自己的网络环境，并独立于 host system 或其他容器的网络运行。
</details>

13. 限制 process 可以使用哪些 system call 的 Linux 安全功能名称是什么？

<details>

<summary>显示答案</summary>

**答案: seccomp (Secure Computing Mode)**

**解释:**
seccomp 是一项 Linux kernel 安全功能，用于限制 process 可以使用的 system call。Container runtime 使用 seccomp filter 限制容器可以执行的 system call，从而增强安全性。
</details>

14. 将 Linux 中传统 root 权限划分为更小权限单元的机制叫什么？

<details>

<summary>显示答案</summary>

**答案: Capabilities（能力）**

**解释:**
Linux Capabilities 将传统 root 权限划分为更小的权限单元。这允许只向 process 授予最低限度的必要权限，从而增强安全性。例如，要更改网络设置，只需要 `CAP_NET_ADMIN` capability，而不需要完整的 root 权限。
</details>

15. 在容器网络中，host 与容器之间的网络接口对叫什么？

<details>

<summary>显示答案</summary>

**答案: veth pair**

**解释:**
veth pair 是一个 virtual ethernet interface pair，其中一端位于容器内部，另一端位于 host network namespace 中。这使容器与 host 之间能够进行网络通信。通常，host 侧 veth interface 会连接到一个 bridge（例如 docker0），以实现多个容器之间的通信。
</details>

16. 用于检查并限制 process 可打开的最大 file descriptor 数量的命令是什么？

<details>

<summary>显示答案</summary>

**答案: ulimit**

**解释:**
ulimit 是用于检查和设置用户及 process 资源限制的命令。`ulimit -n` 检查可以打开的 file descriptor 数量，`ulimit -n 65536` 更改该限制。在 Kubernetes node 上，需要大量 file handle，因此通常会在 `/etc/security/limits.conf` 中永久设置较高的值。
</details>

17. systemd 用于统一管理服务日志的 logging system tool 名称是什么？

<details>

<summary>显示答案</summary>

**答案: journald（或 systemd-journald）**

**解释:**
journald 是 systemd 的统一 logging system，用于收集并存储系统和服务日志。可以使用 `journalctl` 命令查询日志，使用 `-u` 选项查看特定服务日志，使用 `-f` 选项查看实时日志。在 Kubernetes node 上，可以使用 `journalctl -u kubelet` 检查 kubelet 日志。
</details>

18. 用于与 NTP server 同步系统时间的现代 daemon 名称是什么？

<details>

<summary>显示答案</summary>

**答案: chronyd（或 chrony）**

**解释:**
chronyd 是一种现代 NTP client/server，与传统 ntpd 相比能更快同步时间。`chronyc tracking` 命令检查同步状态，`chronyc sources` 显示 NTP server 列表。在 Kubernetes cluster 中，所有 node 都必须准确同步时间，以确保认证、日志记录等正常工作。
</details>

19. Linux 中存储 DNS name resolution 设置的文件路径是什么？

<details>

<summary>显示答案</summary>

**答案: /etc/resolv.conf**

**解释:**
`/etc/resolv.conf` 是存储 DNS name resolution 设置的文件，用于定义 nameserver、search domain、options 等。在 Kubernetes 环境中，此文件与 CoreDNS 一起发挥重要作用，并且也会影响 Pod DNS 设置。在现代系统中，systemd-resolved 可能会动态管理此文件。
</details>

## 实操题

20. 写出创建新的 network namespace 并列出该 namespace 内 network interface 的命令。

<details>

<summary>显示答案</summary>

**答案:**
```bash
# Create a new network namespace
ip netns add mynetns

# List network interfaces within that namespace
ip netns exec mynetns ip link list
```

**解释:**
第一个命令创建一个名为 "mynetns" 的新 network namespace。第二个命令在该 namespace 内执行 `ip link list` 命令以列出 network interface。默认情况下，新创建的 network namespace 仅包含 loopback interface (lo)，并且该 interface 初始处于 down 状态。
</details>

21. 写出检查特定 process（PID: 1234）的 cgroup 信息的命令。

<details>

<summary>显示答案</summary>

**答案:**
```bash
cat /proc/1234/cgroup
```

**解释:**
在 Linux 中，可以通过 `/proc/<PID>/cgroup` 文件检查特定 process 的 cgroup 信息。该文件显示 process 所属的所有 cgroup hierarchy 和 controller 信息。也可以使用 `systemd-cgls` 命令以树形格式查看 cgroup hierarchy。
</details>

22. 写出一个 chmod 命令，为文件 "example.sh" 的 owner 授予读取、写入、执行权限，为 group 授予读取和执行权限，并为 other users 授予只读权限。

<details>

<summary>显示答案</summary>

**答案:**
```bash
chmod 754 example.sh
```

或

```bash
chmod u=rwx,g=rx,o=r example.sh
```

**解释:**
第一种方法使用数字表示法：
  - 7(rwx)：向 owner 授予 read(4)、write(2)、execute(1) 权限
  - 5(r-x)：向 group 授予 read(4) 和 execute(1) 权限
  - 4(r--)：仅向 other users 授予 read(4) 权限

第二种方法使用符号表示法设置相同权限。
</details>

23. 写出检查系统当前 memory 使用情况的命令。

<details>

<summary>显示答案</summary>

**答案:**
```bash
free -h
```

**解释:**
`free` 命令显示系统的 memory 使用情况。`-h` 选项以人类可读格式输出（例如 GB、MB）。输出包括总 memory、已用 memory、可用 memory、用于 buffers/cache 的 memory、swap memory 信息等。
</details>

24. 写出查找在特定端口（例如 8080）上运行的 process 的命令。

<details>

<summary>显示答案</summary>

**答案:**
```bash
lsof -i :8080
```

或

```bash
netstat -tulpn | grep :8080
```

或

```bash
ss -tulpn | grep :8080
```

**解释:**
  - `lsof -i :8080`：显示使用端口 8080 的 process。
  - `netstat -tulpn | grep :8080`：从 TCP/UDP 连接列表中查找使用端口 8080 的条目。使用选项 `-t`(TCP)、`-u`(UDP)、`-l`(listening)、`-p`(process info)、`-n`(show numerically)。
  - `ss -tulpn | grep :8080`：`netstat` 的现代替代工具，提供相同信息。
</details>

25. 写出配置 kernel module br_netfilter 和 overlay 在启动时自动加载的命令，这些模块是 Kubernetes node 所必需的。

<details>

<summary>显示答案</summary>

**答案:**
```bash
cat <<EOF | sudo tee /etc/modules-load.d/kubernetes.conf
overlay
br_netfilter
EOF

# Load immediately in current session
sudo modprobe overlay
sudo modprobe br_netfilter
```

**解释:**
在 `/etc/modules-load.d/` 目录中创建 `.conf` 文件，会使 systemd-modules-load 服务在启动时自动加载这些模块。`overlay` module 支持用于容器镜像层的 OverlayFS 文件系统，而 `br_netfilter` module 允许 bridge traffic 通过 iptables，这对 Kubernetes 网络至关重要。
</details>

26. 写出一个 journalctl 命令，用于查看 kubelet 服务的实时日志，同时仅过滤 error 级别及以上的消息。

<details>

<summary>显示答案</summary>

**答案:**
```bash
journalctl -u kubelet -f -p err
```

或

```bash
journalctl -u kubelet -f -p warning
```

**解释:**
  - `-u kubelet`：仅显示 kubelet 服务日志
  - `-f`：实时流式输出新日志（类似 tail -f）
  - `-p err`：仅显示 error 级别及以上日志（err、crit、alert、emerg）
  - `-p warning`：显示 warning 级别及以上日志（warning、err、crit、alert、emerg）

journalctl priority level 范围从 0(emerg) 到 7(debug)，会显示指定级别及更高优先级的消息。
</details>

27. 写出检查系统当前 timezone 并将其更改为 Asia/Seoul 的命令。

<details>

<summary>显示答案</summary>

**答案:**
```bash
# Check current timezone
timedatectl

# Change timezone
sudo timedatectl set-timezone Asia/Seoul
```

**解释:**
`timedatectl` 命令是 systemd 的时间管理工具，可用于设置和检查系统的时间、日期和 timezone。`timedatectl list-timezones` 命令显示可用 timezone。在 Kubernetes cluster 中，如果所有 node 使用相同 timezone 或使用 UTC，将有助于日志分析和故障排查。
</details>

28. 写出要添加到 /etc/security/limits.conf 的配置，用于将 file descriptor 限制永久设置为 65536。

<details>

<summary>显示答案</summary>

**答案:**
```bash
*               soft    nofile          65536
*               hard    nofile          65536
```

或针对特定用户/服务：
```bash
root            soft    nofile          65536
root            hard    nofile          65536
```

**解释:**
`/etc/security/limits.conf` 是 PAM (Pluggable Authentication Modules) 使用的配置文件，用于定义每个用户的资源限制。`*` 表示所有用户，`soft` 是默认限制，`hard` 是最大限制。`nofile` 指定可以打开的 file descriptor 数量。在 Kubernetes node 上，需要大量网络连接和 file handle，因此应将此值设置得较高。
</details>

## 高级题

29. 解释 Linux kernel 用于容器隔离的三项主要技术，并描述每项技术提供哪种隔离。

<details>

<summary>显示答案</summary>

**答案:**

1. **Namespaces**:
  - Namespaces 会隔离 process group，使每个 group 能够独立查看系统资源。
  - 主要 namespace 类型：
  - PID namespace：Process ID 隔离
  - Network namespace：Network stack 隔离（interfaces、routing tables、firewall 等）
  - Mount namespace：文件系统 mount point 隔离
  - UTS namespace：Hostname 和 domain name 隔离
  - IPC namespace：Inter-process communication resource 隔离
  - User namespace：User 和 group ID 隔离
  - cgroup namespace：cgroup root directory 隔离

2. **cgroups (Control Groups)**:
  - cgroups 是一项限制和隔离 process group 资源使用的功能。
  - 提供的隔离：
  - CPU 时间限制
  - Memory 使用限制
  - Block I/O 带宽限制
  - Network 带宽限制
  - Device 访问控制

3. **Capabilities**:
  - Linux capabilities 将传统 root 权限划分为更小的权限单元。
  - 提供的隔离：
  - 权限隔离：仅向容器授予最低限度的必要权限
  - 安全增强：通过移除不必要的权限降低安全风险
  - 示例：`CAP_NET_ADMIN`（网络配置更改）、`CAP_SYS_ADMIN`（系统管理任务）等。

这三项技术结合起来，使容器能够在与 host system 和其他容器隔离的环境中运行，同时限制资源使用并增强安全性。
</details>

30. 解释 OverlayFS 如何管理容器镜像层，并描述只读层与可写层之间的关系。

<details>

<summary>显示答案</summary>

**答案:**

OverlayFS 是一种 union mount 文件系统，它将多个目录叠加起来并呈现为单个目录。在容器镜像层管理中，OverlayFS 的工作方式如下：

1. **层结构**:
  - **Lower directory（只读层）**：base image 层；可以有多个。包含 base file system 和 application code。
  - **Upper directory（可写层）**：容器运行时创建的可写层。容器内发生的所有更改都存储在这一层。
  - **Work directory**：OverlayFS 内部操作使用的临时目录。
  - **Merged directory**：所有层整合后的最终视图；也就是容器实际看到的文件系统。

2. **只读层与可写层之间的关系**:
  - **文件读取**：读取文件时，OverlayFS 首先在 Upper directory（可写层）中查找该文件。如果未找到，则按顺序搜索 Lower directory（只读层）。
  - **文件写入**：修改文件时，会使用 Copy-on-Write (CoW)。当尝试修改只读层中的文件时，文件会先被复制到可写层，然后再修改。原始文件保持不变。
  - **文件删除**：当尝试删除只读层中的文件时，该文件不会被实际删除；而是在可写层中创建一个 "whiteout" 文件，使其看起来像已被删除。

3. **优势**:
  - **空间效率**：多个容器共享相同的 base image 层，从而节省磁盘空间。
  - **启动速度快**：启动新容器时，只需创建可写层，而无需复制整个文件系统。
  - **镜像版本管理**：可以通过向 base image 添加新层来更新镜像。

通过这种方式，OverlayFS 高效管理容器镜像层，使容器在共享 base image 的同时拥有独立的文件系统。
</details>

31. 解释 Linux capabilities 如何影响容器安全，以及为什么只向容器授予最低限度的必要 capabilities 很重要。

<details>

<summary>显示答案</summary>

**答案:**

**Linux Capabilities 与容器安全：**

Linux capabilities 将传统 root 权限划分为更小的权限单元，并通过以下方式影响容器安全：

1. **权限粒度**:
  - 传统上，process 只区分为 root (UID 0) 或非 root。
  - Capabilities 允许将 root 权限划分为多个独立权限，从而只向 process 授予特定的必要权限。
  - 示例：要更改网络设置，只需要 `CAP_NET_ADMIN` capability，而不是完整的 root 权限。

2. **容器安全增强**:
  - Container runtime 默认只向容器授予有限的一组 capabilities。
  - 这会限制容器对 host system 可能造成的影响。
  - 即使在容器内以 root 运行的 process，也只拥有有限的 capabilities，从而降低安全风险。

3. **关键的容器相关 Capabilities**:
  - `CAP_NET_ADMIN`：网络配置更改
  - `CAP_SYS_ADMIN`：系统管理任务（非常强大）
  - `CAP_CHOWN`：文件所有权更改
  - `CAP_DAC_OVERRIDE`：绕过文件权限
  - `CAP_SETUID`：UID 更改
  - `CAP_SETGID`：GID 更改

**最小权限原则的重要性：**

只向容器授予最低限度的必要 capabilities 非常重要，原因如下：

1. **减少攻击面**:
  - 移除不必要的 capabilities 会减少攻击者可利用的途径。
  - 即使容器被攻破，攻击者可以执行的操作也会受到限制。

2. **防止容器逃逸**:
  - 强大的 capabilities（尤其是 `CAP_SYS_ADMIN`）可能导致容器逃逸（从容器访问 host）。
  - 限制这些 capabilities 可显著降低容器逃逸风险。

3. **纵深防御策略**:
  - 最小权限原则是纵深防御安全策略的一部分。
  - 与其他安全机制（seccomp、AppArmor、SELinux 等）配合使用时，可提供更强的安全性。

4. **合规要求**:
  - 许多安全标准和法规要求遵循最小权限原则。
  - 仅向容器授予最低限度的必要 capabilities 有助于满足这些要求。

5. **问题隔离**:
  - 向容器授予有限 capabilities，可防止一个容器中的问题扩散到其他容器或 host system。

在生产环境中，准确识别容器需要的 capabilities 并移除所有其他 capabilities 是良好的安全实践。可以使用 Docker 的 `--cap-drop`、`--cap-add` 选项，或 Kubernetes 的 `securityContext.capabilities` 字段来实现。
</details>

32. 解释 systemd service unit 文件的结构以及主要 section（[Unit]、[Service]、[Install]）的作用，并为 Kubernetes kubelet 服务写出一个基本 unit file 示例。

<details>

<summary>显示答案</summary>

**答案:**

**systemd unit 文件的主要 section：**

1. **[Unit] Section**：定义 unit 元数据和依赖关系
   - `Description`：服务描述
   - `Documentation`：文档 URL
   - `After/Before`：定义启动顺序
   - `Requires/Wants`：定义依赖关系

2. **[Service] Section**：定义如何运行服务
   - `Type`：服务类型（simple、forking、oneshot 等）
   - `ExecStart`：要执行的命令
   - `Restart`：重启策略
   - `RestartSec`：重启等待时间

3. **[Install] Section**：定义 unit 启用时的行为
   - `WantedBy`：需要此 unit 的 target

**kubelet service unit file 示例：**

```ini
[Unit]
Description=kubelet: The Kubernetes Node Agent
Documentation=https://kubernetes.io/docs/
Wants=network-online.target
After=network-online.target

[Service]
ExecStart=/usr/bin/kubelet
Restart=always
StartLimitInterval=0
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**解释:**
此 unit file 定义了 kubelet 服务。它在网络就绪后启动（`After=network-online.target`），失败时始终重启（`Restart=always`），并且每 10 秒尝试重启一次（`RestartSec=10`）。`WantedBy=multi-user.target` 表示该服务会在系统启动进入 multi-user mode 时启动。
</details>

33. 解释如何永久设置 Kubernetes node 配置所需的 sysctl kernel 参数，并描述每个参数的作用。

<details>

<summary>显示答案</summary>

**答案:**

**Kubernetes 所需的关键 sysctl 设置及其作用：**

```bash
# Create /etc/sysctl.d/99-kubernetes.conf file
cat <<EOF | sudo tee /etc/sysctl.d/99-kubernetes.conf
# Enable IP forwarding - essential for packet routing between containers
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1

# Bridge traffic passes through iptables - essential for CNI network policies
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1

# Connection tracking table size (for large clusters)
net.netfilter.nf_conntrack_max = 1000000
EOF

# Apply settings
sudo sysctl --system
```

**每个参数的作用：**

1. **net.ipv4.ip_forward = 1**
   - 允许 Linux kernel 在 network interface 之间转发数据包
   - 对从 Pod 到其他 Pod 或外部网络的通信至关重要
   - 如果禁用，容器网络将无法工作

2. **net.bridge.bridge-nf-call-iptables = 1**
   - 配置通过 bridge 的流量受 iptables 规则处理
   - 对 Kubernetes service（ClusterIP、NodePort）和 NetworkPolicy 正常工作至关重要
   - 这是必需的，因为 kube-proxy 使用 iptables 进行 service 路由

3. **net.ipv6.conf.all.forwarding = 1**
   - 在 IPv6 环境中启用数据包转发
   - dual-stack cluster 需要此设置

**设置应用顺序：**
1. 首先加载 `br_netfilter` module：`modprobe br_netfilter`
2. 创建 sysctl 配置文件
3. 使用 `sysctl --system` 应用所有设置

如果没有这些设置，Kubernetes cluster 网络将无法正常运行，尤其会出现 Pod-to-Pod 通信和 service discovery 方面的问题。
</details>

34. 解释使用 journald 和 logrotate 的 Linux 日志管理策略，并给出 Kubernetes node 上高效日志管理的配置方法。

<details>

<summary>显示答案</summary>

**答案:**

**journald 和 logrotate 的作用：**

**journald（基于 systemd 的日志记录）：**
- 收集 systemd 服务的 stdout/stderr 日志
- 以二进制格式存储，并使用 journalctl 查询
- 支持自动日志压缩和轮转

**logrotate（传统日志文件管理）：**
- 管理文本日志文件的轮转、压缩和删除
- 通过 cron job 定期运行

**Kubernetes Node 日志管理配置：**

**1. journald 配置 (/etc/systemd/journald.conf):**
```ini
[Journal]
# Store persistently on disk
Storage=persistent

# Maximum disk usage (total /var/log/journal)
SystemMaxUse=2G

# Maximum file size
SystemMaxFileSize=100M

# Minimum free space to maintain
SystemKeepFree=1G

# Maximum retention period
MaxRetentionSec=1month
```

**2. 容器日志的 logrotate 配置：**
```bash
# /etc/logrotate.d/containers
/var/log/containers/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    maxsize 100M
}
```

**3. 日志清理命令：**
```bash
# journald log cleanup
journalctl --vacuum-time=7d   # Delete logs older than 7 days
journalctl --vacuum-size=1G   # Delete old logs when exceeding 1GB

# Check disk usage
journalctl --disk-usage
```

**Kubernetes 日志管理最佳实践：**

1. **kubelet logs**：由 journald 管理，存储在 `/var/log/journal/`
2. **Container logs**：存储在 `/var/log/containers/`，由 logrotate 管理
3. **Centralized logging**：建议使用 Fluentd/Fluent Bit 转发到外部系统

适当的日志管理可以在防止节点因磁盘空间耗尽而失败与保留用于故障排查的日志之间保持平衡。
</details>

---

[返回学习资料](../../basics/01-linux-basics.md) | [下一测验：Linux 运维](./02-linux-advanced-quiz.md)
