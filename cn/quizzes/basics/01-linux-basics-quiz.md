# Linux 基础测验

本测验用于检查你对 Linux 基础概念的理解，这些概念构成 Kubernetes 和容器技术的基础。

## 选择题

1. 以下哪一项不是 Linux kernel 的主要职责？
   - A) 进程管理
   - B) 内存管理
   - C) 提供用户界面
   - D) 设备管理
<details>

<summary>显示答案</summary>

**答案：C) 提供用户界面**

**解释：**
Linux kernel 是操作系统的核心，充当硬件和软件之间的中介。kernel 的主要职责包括进程管理、内存管理、设备管理以及提供系统调用接口。用户界面（GUI、CLI）由运行在用户空间的独立程序提供，并不是 kernel 的职责。

</details>

2. 以下哪一项不是 Linux namespace 的类型？
   - A) PID namespace
   - B) Network namespace
   - C) Memory namespace
   - D) User namespace
<details>

<summary>显示答案</summary>

**答案：C) Memory namespace**

**解释：**
Linux namespace 包括 PID（Process ID）、Network、Mount、UTS（hostname）、IPC（Inter-Process Communication）、User、cgroup 和 time namespace。不存在 memory namespace：进程虚拟地址空间提供内存隔离，而 cgroups 用于统计并限制内存使用。

</details>

3. cgroups（Control Groups）的主要功能是什么？
   - A) 限制和隔离进程组的资源使用
   - B) 控制文件系统访问
   - C) 过滤网络数据包
   - D) 管理用户身份认证
   
<details>

<summary>显示答案</summary>

**答案：A) 限制和隔离进程组的资源使用**

**解释：**
cgroups 是一种 Linux kernel 功能，用于限制和隔离进程组的资源使用。它可以限制并监控 CPU 时间、内存和块 I/O 的使用；网络带宽控制则需要集成 tc/eBPF。这是容器中实现资源限制的核心技术。
</details>

4. 在文件权限 "rwxr-xr--" 中，组用户的权限是什么？
   - A) 读取、写入、执行
   - B) 读取、执行
   - C) 只读
   - D) 仅执行
   
<details>

<summary>显示答案</summary>

**答案：B) 读取、执行**

**解释：**
在文件权限 "rwxr-xr--" 中：
  - 前 3 个字符（rwx）：所有者权限 - 读取、写入、执行
  - 中间 3 个字符（r-x）：组权限 - 读取、执行
  - 最后 3 个字符（r--）：其他用户权限 - 只读

因此，组用户拥有读取和执行权限。

</details>

5. 哪种文件系统主要用于实现容器镜像层？
   - A) ext4
   - B) XFS
   - C) OverlayFS
   - D) Btrfs

<details>

<summary>显示答案</summary>

**答案：C) OverlayFS**

**解释：**
OverlayFS 是一种联合挂载文件系统，它将多个目录叠加并呈现为单个目录。Docker 等容器运行时主要使用它来实现镜像层。这允许基础镜像保持只读，同时为每个容器添加一个可写层。
</details>

6. 使用 systemctl 命令管理服务时，哪个命令会将服务设置为在启动时自动启动？
   - A) systemctl start
   - B) systemctl enable
   - C) systemctl restart
   - D) systemctl reload

<details>

<summary>显示答案</summary>

**答案：B) systemctl enable**

**解释：**
`systemctl enable` 会将服务设置为在系统启动时自动启动。`start` 会立即启动服务，`restart` 会重启服务，`reload` 只会重新读取配置文件。在 Kubernetes 节点上，kubelet 和 containerd 等核心服务应使用 `systemctl enable` 配置为自动启动。
</details>

7. 当节点需要在网络接口之间转发 IPv4 数据包时，哪个 kernel 参数可启用该功能？
   - A) net.ipv4.tcp_syncookies
   - B) net.ipv4.ip_forward
   - C) net.core.somaxconn
   - D) fs.file-max

<details>

<summary>显示答案</summary>

**答案：B) net.ipv4.ip_forward**

**解释：**
`net.ipv4.ip_forward` 是在 Linux kernel 中启用 IP 数据包转发的设置。当节点需要在接口之间转发 IPv4 数据包时，将此设置为 1；同一网络命名空间中的 localhost 流量无需转发。配置 Kubernetes 节点时，在需要转发的场景中必须启用此参数，可使用命令 `sysctl -w net.ipv4.ip_forward=1` 设置。
</details>

8. 在 systemd unit 文件中，哪个指令用于定义某个服务应在特定服务之后启动？
   - A) Requires
   - B) Wants
   - C) After
   - D) Before

<details>

<summary>显示答案</summary>

**答案：C) After**

**解释：**
在 systemd unit 文件中，`After` 仅在两个 unit 都被启动时规定当前 unit 的启动顺序晚于指定 unit。若服务启动时需要网络就绪，应将 Wants=network-online.target 与 After=network-online.target 配合使用，并配置发行版提供的 wait-online 实现。它不会持续监控网络可用性。`Requires` 定义强依赖，`Wants` 定义弱依赖，`Before` 表示当前 unit 应在另一个 unit 之前启动。
</details>

9. 当所选 CNI 要求使用 bridge netfilter 时，哪个 kernel 参数会让桥接的 IPv4 流量经过 iptables？
   - A) net.ipv4.ip_forward
   - B) net.bridge.bridge-nf-call-iptables
   - C) net.core.netdev_max_backlog
   - D) net.ipv4.tcp_max_syn_backlog

<details>

<summary>显示答案</summary>

**答案：B) net.bridge.bridge-nf-call-iptables**

**解释：**
`net.bridge.bridge-nf-call-iptables` 会配置桥接的 IPv4 流量经过 iptables 规则。是否需要此设置取决于 CNI/数据平面；对于路由或 eBPF 网络并非通用要求。启用此设置前，必须先加载 `br_netfilter` kernel 模块。
</details>

10. 在包管理中，在 Ubuntu/Debian 上使用哪个命令来防止 Kubernetes 组件自动升级？
    - A) apt lock
    - B) apt-mark hold
    - C) apt freeze
    - D) apt pin

<details>

<summary>显示答案</summary>

**答案：B) apt-mark hold**

**解释：**
`apt-mark hold` 会固定特定软件包以防止自动升级。在 Kubernetes 集群中，kubelet、kubeadm 和 kubectl 的版本兼容性很重要，因此建议使用命令 `sudo apt-mark hold kubelet kubeadm kubectl` 固定版本。在基于 RPM 的系统上，应根据发行版使用已安装的 DNF/YUM versionlock 插件，或采用相应的软件仓库排除规则。
</details>

## 简答题

11. 当一个进程已经终止，但其父进程尚未检查其状态时，这个进程叫什么？

<details>

<summary>显示答案</summary>

**答案：Zombie Process**

**解释：**
Zombie Process 是指已经完成执行但仍保留在进程表中的进程，因为父进程尚未通过 `wait()` 系统调用检查它的退出状态。Zombie Process 几乎不使用资源，但如果大量累积，进程表可能会被填满，从而阻止新进程创建。
</details>

12. 隔离进程网络栈的 Linux namespace 名称是什么？

<details>

<summary>显示答案</summary>

**答案：Network Namespace**

**解释：**
Network namespace 会隔离网络栈（网络接口、路由表、防火墙规则、套接字等）。这使每个容器都可以拥有自己的网络环境，并独立于主机系统或其他容器的网络运行。
</details>

13. 限制进程可使用的系统调用的 Linux 安全功能叫什么？

<details>

<summary>显示答案</summary>

**答案：seccomp (Secure Computing Mode)**

**解释：**
seccomp 是一种 Linux kernel 安全功能，用于限制进程可使用的系统调用。容器运行时使用 seccomp 过滤器来限制容器可执行的系统调用，从而增强安全性。
</details>

14. Linux 中传统 root 权限被拆分为更小的权限单元，这叫什么？

<details>

<summary>显示答案</summary>

**答案：Capabilities**

**解释：**
Linux Capabilities 将传统 root 权限拆分为更小的权限单元。这允许只向进程授予所需的最小权限，从而增强安全性。例如，要更改网络设置，只需要 `CAP_NET_ADMIN` capability，而不需要完整的 root 权限。
</details>

15. 在容器网络中，主机与容器之间的网络接口对叫什么？

<details>

<summary>显示答案</summary>

**答案：veth pair**

**解释：**
veth pair 是一对虚拟以太网接口，其中一端位于容器内，另一端位于主机网络 namespace 中。这使容器和主机之间能够进行网络通信。通常，主机侧的 veth 接口会连接到一个桥接器（例如 docker0），以支持多个容器之间的通信。
</details>

16. 用于检查并限制进程可打开的最大文件描述符数量的命令是什么？

<details>

<summary>显示答案</summary>

**答案：ulimit**

**解释：**
ulimit 用于检查和设置用户与进程的资源限制。`ulimit -n` 会检查可打开的文件描述符数量，`ulimit -n 65536` 会更改该限制。shell 限制会作用于该 shell 及其之后创建的子进程。PAM limits 仅影响新的登录会话；对于 kubelet 等 systemd 系统服务，应通过 service drop-in 设置 LimitNOFILE。
</details>

17. systemd 用于统一管理服务日志的日志系统工具叫什么？

<details>

<summary>显示答案</summary>

**答案：journald (or systemd-journald)**

**解释：**
journald 是 systemd 的统一日志系统，用于收集和存储系统与服务日志。可以使用 `journalctl` 命令查询日志，使用 `-u` 选项查看特定服务日志，使用 `-f` 选项查看实时日志。在 Kubernetes 节点上，可以使用 `journalctl -u kubelet` 检查 kubelet 日志。
</details>

18. 用于与 NTP 服务器同步系统时间的现代守护进程叫什么？

<details>

<summary>显示答案</summary>

**答案：chronyd (or chrony)**

**解释：**
chronyd 是 NTP 客户端/服务器；其收敛速度取决于网络、时间源质量和配置。`chronyc tracking` 命令会检查同步状态，`chronyc sources` 会显示 NTP 服务器列表。在 Kubernetes 集群中，所有节点都需要准确同步时间，身份认证、日志记录等才能正常工作。
</details>

19. Linux 中存储 DNS 名称解析设置的文件路径是什么？

<details>

<summary>显示答案</summary>

**答案：/etc/resolv.conf**

**解释：**
`/etc/resolv.conf` 是存储 DNS 名称解析设置的文件，用于定义 nameserver、搜索域、选项等。在 Kubernetes 环境中，此文件与 CoreDNS 一起发挥重要作用，并且也会影响 Pod DNS 设置。在现代系统中，systemd-resolved 可能会动态管理此文件。
</details>

## 实操题

20. 写出创建新 network namespace 并列出该 namespace 内网络接口的命令。

<details>

<summary>显示答案</summary>

**答案：**
```bash
# Create a new network namespace
sudo ip netns add mynetns

# List network interfaces within that namespace
sudo ip netns exec mynetns ip link list
# After the exercise, when no processes use it:
sudo ip netns delete mynetns
```

**解释：**
第一个命令会创建名为 "mynetns" 的新 network namespace。第二个命令会在该 namespace 内执行 `ip link list` 命令，以列出网络接口。新创建的 network namespace 默认只包含 loopback 接口（lo），并且该接口初始处于 down 状态。
</details>

21. 写出用于检查特定进程（PID：1234）的 cgroup 信息的命令。

<details>

<summary>显示答案</summary>

**答案：**
```bash
cat /proc/1234/cgroup
```

**解释：**
在 Linux 中，可以通过 `/proc/<PID>/cgroup` 文件检查特定进程的 cgroup 信息。此文件显示该进程所属的所有 cgroup 层级和 controller 信息。也可以使用 `systemd-cgls` 命令以树形格式查看 cgroup 层级。
</details>

22. 写出一个 chmod 命令，为文件 "example.sh" 的所有者授予读取、写入、执行权限，为组授予读取和执行权限，为其他用户授予只读权限。

<details>

<summary>显示答案</summary>

**答案：**
```bash
chmod 754 example.sh
```

或

```bash
chmod u=rwx,g=rx,o=r example.sh
```

**解释：**
第一种方法使用数字表示法：
  - 7(rwx)：授予所有者读取(4)、写入(2)、执行(1)权限
  - 5(r-x)：授予组读取(4)和执行(1)权限
  - 4(r--)：仅授予其他用户读取(4)权限

第二种方法使用符号表示法来设置相同的权限。
</details>

23. 写出用于检查系统当前内存使用情况的命令。

<details>

<summary>显示答案</summary>

**答案：**
```bash
free -h
```

**解释：**
`free` 命令会显示系统的内存使用情况。`-h` 选项会以人类可读格式输出（例如 GB、MB）。输出包括总内存、已用内存、可用内存、用于 buffers/cache 的内存、swap 内存信息等。
</details>

24. 写出用于查找在特定端口（例如 8080）上运行的进程的命令。

<details>

<summary>显示答案</summary>

**答案：**
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

**解释：**
  - `lsof -i :8080`：显示使用端口 8080 的进程。
  - `netstat -tulpn | grep :8080`：从 TCP/UDP 连接列表中查找使用端口 8080 的条目。使用选项 `-t`(TCP)、`-u`(UDP)、`-l`(listening)、`-p`(process info)、`-n`(show numerically)。
  - `ss -tulpn | grep :8080`：`netstat` 的现代替代工具，提供相同的信息。
</details>

25. 当所选运行时/CNI 需要 br_netfilter 和 overlay 模块时，写出将这些 kernel 模块配置为启动时自动加载的命令。

<details>

<summary>显示答案</summary>

**答案：**
```bash
cat <<EOF | sudo tee /etc/modules-load.d/kubernetes.conf
overlay
br_netfilter
EOF

# Load immediately in current session
sudo modprobe overlay
sudo modprobe br_netfilter
```

**解释：**
在 `/etc/modules-load.d/` 目录中创建 `.conf` 文件会使 systemd-modules-load 服务在启动时自动加载其中的模块。`overlay` 模块支持容器镜像层所使用的 OverlayFS 文件系统；当所选 CNI 配置需要 bridge netfilter 时，`br_netfilter` 模块可让桥接流量经过 iptables。
</details>

26. 写出一个 journalctl 命令，用于查看 kubelet 服务的实时日志，同时只过滤错误级别及以上的消息。

<details>

<summary>显示答案</summary>

**答案：**
```bash
journalctl -u kubelet -f -p err
```

**解释：**
`-p warning` 还会显示警告，因此不符合题目要求的“仅错误级别及以上”。
  - `-u kubelet`：仅显示 kubelet 服务日志
  - `-f`：实时流式显示新日志（类似 tail -f）
  - `-p err`：仅显示错误级别及以上日志（err、crit、alert、emerg）
  - `-p warning`：显示 warning 级别及以上日志（warning、err、crit、alert、emerg）

journalctl 的优先级级别范围从 0(emerg) 到 7(debug)，会显示指定级别及更高优先级的消息。
</details>

27. 写出用于检查系统当前时区并将其更改为 Asia/Seoul 的命令。

<details>

<summary>显示答案</summary>

**答案：**
```bash
# Check current timezone
timedatectl

# Change timezone
sudo timedatectl set-timezone Asia/Seoul
```

**解释：**
`timedatectl` 命令是 systemd 的时间管理工具，可用于设置和检查系统的时间、日期与时区。`timedatectl list-timezones` 命令会显示可用时区。在 Kubernetes 集群中，如果所有节点使用相同时区或使用 UTC，将有助于日志分析和故障排查。
</details>

28. 写出要添加到 /etc/security/limits.conf 的配置，用于将文件描述符限制永久设置为 65536。

<details>

<summary>显示答案</summary>

**答案：**
```text
*               soft    nofile          65536
*               hard    nofile          65536
```

或针对特定 PAM 登录用户（不适用于 systemd 服务）：
```text
root            soft    nofile          65536
root            hard    nofile          65536
```

**解释：**
`/etc/security/limits.conf` 是 PAM（Pluggable Authentication Modules）使用的配置文件，用于定义每个用户的资源限制。`*` 匹配普通用户（root 需要单独配置），`soft` 是默认限制，`hard` 是最大限制。`nofile` 指定可打开的文件描述符数量，应根据工作负载需求选择限制。PAM 设置不会更改正在运行的进程，也不会作用于普通的 systemd 系统服务；应在服务 drop-in 中配置 LimitNOFILE。
</details>

## 进阶题

29. 解释 Linux kernel 用于容器隔离的三项主要技术，并描述每项技术提供哪种隔离。

<details>

<summary>显示答案</summary>

**答案：**

1. **Namespaces**:
  - Namespaces 会隔离进程组，使每个组都能独立地看到系统资源。
  - 主要 namespace 类型：
  - PID namespace：进程 ID 隔离
  - Network namespace：网络栈隔离（接口、路由表、防火墙等）
  - Mount namespace：文件系统挂载点隔离
  - UTS namespace：主机名和域名隔离
  - IPC namespace：进程间通信资源隔离
  - User namespace：用户和组 ID 隔离
  - cgroup namespace：cgroup 根目录隔离

2. **cgroups (Control Groups)**:
  - cgroups 是一种限制和隔离进程组资源使用的功能。
  - 提供的隔离：
  - CPU 时间限制
  - 内存使用限制
  - 块 I/O 带宽限制
  - 与 tc/eBPF 集成的网络流量分类
  - 设备访问控制

3. **Capabilities**:
  - Linux capabilities 将传统 root 权限拆分为更小的权限单元。
  - 提供的隔离：
  - 权限隔离：仅向容器授予最低必要权限
  - 安全增强：通过移除不必要的权限来降低安全风险
  - 示例：`CAP_NET_ADMIN`（网络配置更改）、`CAP_SYS_ADMIN`（系统管理任务）等。

这三项技术结合起来，使容器能够在与主机系统和其他容器隔离的环境中运行，同时限制资源使用并增强安全性。
</details>

30. 解释 OverlayFS 如何管理容器镜像层，并描述只读层与可写层之间的关系。

<details>

<summary>显示答案</summary>

**答案：**

OverlayFS 是一种联合挂载文件系统，它将多个目录叠加并呈现为单个目录。在容器镜像层管理中，OverlayFS 的工作方式如下：

1. **层结构**：
  - **Lower directory（只读层）**：基础镜像层；可以存在多个。包含基础文件系统和应用程序代码。
  - **Upper directory（可写层）**：容器运行时创建的可写层。容器内发生的所有更改都存储在此层中。
  - **Work directory**：用于 OverlayFS 内部操作的临时目录。
  - **Merged directory**：所有层集成后的最终视图；也就是容器实际看到的文件系统。

2. **只读层与可写层之间的关系**：
  - **文件读取**：读取文件时，OverlayFS 首先在 Upper directory（可写层）中查找该文件。如果找不到，则按顺序搜索 Lower directory（只读层）。
  - **文件写入**：修改文件时，会使用 Copy-on-Write（CoW）。当尝试修改只读层中的文件时，会先将该文件复制到可写层，然后再进行修改。原始文件保持不变。
  - **文件删除**：当尝试删除只读层中的文件时，该文件不会被实际删除；而是在可写层中创建一个 "whiteout" 文件，使其看起来像已被删除。

3. **优势**：
  - **空间效率**：多个容器共享相同的基础镜像层，从而节省磁盘空间。
  - **快速启动时间**：启动新容器时，只需创建可写层，而无需复制整个文件系统。
  - **镜像版本管理**：可以通过向基础镜像添加新层来更新镜像。

通过这种方式，OverlayFS 高效管理容器镜像层，使容器在共享基础镜像的同时拥有独立的文件系统。
</details>

31. 解释 Linux capabilities 如何影响容器安全，以及为什么只向容器授予最低必要 capabilities 很重要。

<details>

<summary>显示答案</summary>

**答案：**

**Linux Capabilities 与容器安全：**

Linux capabilities 将传统 root 权限拆分为更小的权限单元，并通过以下方式影响容器安全：

1. **权限粒度**：
  - 传统上，进程只区分为 root（UID 0）或非 root。
  - Capabilities 允许将 root 权限拆分为多个独立权限，从而只向进程授予特定的必要权限。
  - 示例：要更改网络设置，只需要 `CAP_NET_ADMIN` capability，而不是完整的 root 权限。

2. **增强容器安全性**：
  - 容器运行时默认只向容器授予有限的一组 capabilities。
  - 这会限制容器对主机系统可能产生的影响。
  - 即使在容器内以 root 身份运行的进程也具有受限的 capabilities，从而降低安全风险。

3. **关键容器相关 Capabilities**：
  - `CAP_NET_ADMIN`：网络配置更改
  - `CAP_SYS_ADMIN`：系统管理任务（非常强大）
  - `CAP_CHOWN`：文件所有权更改
  - `CAP_DAC_OVERRIDE`：绕过文件权限
  - `CAP_SETUID`：UID 更改
  - `CAP_SETGID`：GID 更改

**最小权限原则的重要性：**

只向容器授予最低必要 capabilities 很重要，原因如下：

1. **减少攻击面**：
  - 移除不必要的 capabilities 会减少攻击者可利用的向量。
  - 即使容器被攻破，攻击者可执行的操作也会受到限制。

2. **防止容器逃逸**：
  - 强大的 capabilities（尤其是 `CAP_SYS_ADMIN`）可能导致容器逃逸（从容器访问主机）。
  - 限制这些 capabilities 会显著降低容器逃逸风险。

3. **纵深防御策略**：
  - 最小权限原则是纵深防御安全策略的一部分。
  - 与其他安全机制（seccomp、AppArmor、SELinux 等）配合使用可提供更强的安全性。

4. **合规要求**：
  - 许多安全标准和法规要求遵循最小权限原则。
  - 只向容器授予最低必要 capabilities 有助于满足这些要求。

5. **问题隔离**：
  - 向容器授予有限的 capabilities 可防止一个容器中的问题扩散到其他容器或主机系统。

在生产环境中，准确识别容器需要的 capabilities 并移除所有其他 capabilities 是良好的安全实践。可以使用 Docker 的 `--cap-drop`、`--cap-add` 选项，或 Kubernetes 的 `securityContext.capabilities` 字段来实现这一点。
</details>

32. 解释 systemd service unit 文件的结构以及主要部分（[Unit]、[Service]、[Install]）的作用，并为训练服务写出一个基本 unit 文件示例；说明为什么应保留 kubelet 随软件包提供的 unit 和 drop-in。

<details>

<summary>显示答案</summary>

**答案：**

**systemd unit 文件的主要部分：**

1. **[Unit] 部分**：定义 unit 元数据和依赖关系
   - `Description`：服务描述
   - `Documentation`：文档 URL
   - `After/Before`：定义启动顺序
   - `Requires/Wants`：定义依赖关系

2. **[Service] 部分**：定义服务如何运行
   - `Type`：服务类型（simple、forking、oneshot 等）
   - `ExecStart`：要执行的命令
   - `Restart`：重启策略
   - `RestartSec`：重启等待时间

3. **[Install] 部分**：定义启用 unit 时的行为
   - `WantedBy`：需要此 unit 的 target

**训练服务 unit 示例（linux-basics-demo.service）：**

```ini
[Unit]
Description=Linux basics training service
Documentation=man:systemd.service(5)
Wants=network-online.target
After=network-online.target

[Service]
ExecStart=/usr/bin/sleep infinity
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**解释：**
此 unit 会运行一个无害的训练进程。使用 systemctl cat kubelet 检查发行版提供的 unit 和 kubeadm drop-in；不要用此示例替换它们。当两个 unit 都被激活时，它会将启动顺序设为晚于 network-online.target；失败时重启（`Restart=on-failure`），并每 10 秒尝试重启一次（`RestartSec=10`）。`WantedBy=multi-user.target` 表示系统启动到多用户模式时会启动此服务。
</details>

33. 解释如何永久设置 Kubernetes 节点配置所需的 sysctl kernel 参数，并描述每个参数的作用。

<details>

<summary>显示答案</summary>

**答案：**

**Kubernetes 所需的关键 sysctl 设置及其作用：**

```bash
# Create /etc/sysctl.d/99-kubernetes.conf file
cat <<EOF | sudo tee /etc/sysctl.d/99-kubernetes.conf
# Enable IP forwarding - essential for packet routing between containers
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1

# Bridge traffic passes through iptables - only if the CNI uses bridge netfilter
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1

# Size conntrack separately from measured workload/memory requirements.
EOF

# Apply settings
sudo sysctl --system
```

**每个参数的作用：**

1. **net.ipv4.ip_forward = 1**
   - 允许 Linux kernel 在网络接口之间转发数据包
   - 对 Pod 到其他 Pod 或外部网络的通信至关重要
   - 如果禁用，容器网络将无法工作

2. **net.bridge.bridge-nf-call-iptables = 1**
   - 配置经过桥接器的流量受 iptables 规则约束
   - 仅当实现依赖 bridge netfilter 时才需要
   - kube-proxy 可能使用 iptables 或 nftables；其他数据平面也可能替代 kube-proxy

3. **net.ipv6.conf.all.forwarding = 1**
   - 在 IPv6 环境中启用数据包转发
   - 双栈集群需要此设置

**设置应用顺序：**
1. 首先加载 `br_netfilter` 模块：`modprobe br_netfilter`
2. 创建 sysctl 配置文件
3. 使用 `sysctl --system` 应用所有设置

只应用 IP 地址族和 CNI 所需的设置，并在隔离实验环境或经过审查的节点配置流程中操作。
</details>

34. 解释使用 journald 和 logrotate 的 Linux 日志管理策略，并给出在 Kubernetes 节点上高效管理日志的配置方法。

<details>

<summary>显示答案</summary>

**答案：**

**journald 和 logrotate 的作用：**

**journald（基于 systemd 的日志）：**
- 收集 systemd 服务的 stdout/stderr 日志
- 以二进制格式存储，使用 journalctl 查询
- 支持自动日志压缩和轮转

**logrotate（传统日志文件管理）：**
- 管理文本日志文件的轮转、压缩和删除
- 通过 cron job 定期运行

**Kubernetes 节点日志管理配置：**

**1. journald 配置（/etc/systemd/journald.conf）：**
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

**2. Kubelet CRI 日志轮转：**

将这些字段合并到现有 kubelet 配置中；不要通过 kubectl 应用，也不要替换整个配置文件。
```yaml
containerLogMaxSize: 10Mi
containerLogMaxFiles: 5
```

对于不由 kubelet 管理的普通应用文本日志：
```text
# /etc/logrotate.d/myapp
/var/log/myapp/*.log {
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

1. **kubelet 日志**：通常由 journald 管理；持久日志位于 /var/log/journal，临时日志位于 /run/log/journal
2. **容器日志**：CRI 文件通常位于 /var/log/pods，并在 /var/log/containers 中提供符号链接；由 kubelet 管理轮转。不要对这些符号链接运行 logrotate。
3. **集中式日志记录**：建议使用 Fluentd/Fluent Bit 转发到外部系统

copytruncate 在复制/截断的竞态期间可能丢失日志记录；应优先使用应用支持的重新打开日志机制。journal vacuum 命令只会删除归档文件。

合理的日志管理可以在防止磁盘空间耗尽导致节点故障与保留日志用于故障排查之间保持平衡。
</details>

---

[返回学习资料](../../basics/01-linux-basics.md) | [下一测验：Linux 运维](./02-linux-advanced-quiz.md)

## 验证参考资料

- https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html
- https://kubernetes.io/docs/concepts/architecture/cgroups/
- https://man7.org/linux/man-pages/man7/time_namespaces.7.html
- https://man7.org/linux/man-pages/man2/getrlimit.2.html
- https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html
- https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html
- https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html
- https://www.freedesktop.org/software/systemd/man/latest/journalctl.html
- https://kubernetes.io/docs/concepts/cluster-administration/logging/
- https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/
- https://ubuntu.com/about/release-cycle
- https://www.debian.org/releases/
- https://www.centos.org/centos-linux-eol/
- https://documentation.ubuntu.com/server/how-to/networking/timedatectl-and-timesyncd/
- https://aws.amazon.com/amazon-linux-2/faqs/
- https://docs.aws.amazon.com/linux/al2023/ug/ec2.html
- https://github.com/logrotate/logrotate/blob/main/logrotate.8.in
- https://github.com/linux-pam/linux-pam/blob/master/modules/pam_limits/limits.conf.5.xml
