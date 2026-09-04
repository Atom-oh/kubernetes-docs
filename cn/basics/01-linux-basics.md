# Linux 基础

> **支持的版本**：所有主流 Linux 发行版（Ubuntu 20.04+、CentOS/RHEL 8+、Debian 11+） **最后更新**：February 11, 2026

理解 Linux 基础知识对于掌握 Kubernetes 和容器技术至关重要。本文档涵盖了在 Kubernetes 环境中特别重要的核心 Linux 概念。

## 实验环境设置

要跟随本文档中的示例操作，您需要以下环境：

### 必需环境

* Linux 操作系统（推荐 Ubuntu 20.04+、CentOS/RHEL 8+、Debian 11+）
* 终端访问权限
* sudo 权限

### 云环境设置（可选）

如果使用 AWS EC2 实例：

```bash
# Start an Amazon Linux 2 instance
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.micro \
  --key-name your-key-pair \
  --security-group-ids sg-12345678 \
  --subnet-id subnet-12345678

# SSH connection
ssh -i your-key.pem ec2-user@your-instance-public-ip
```

### 本地环境设置（可选）

如需在本地练习，您可以使用以下任一环境：

* **VirtualBox + Vagrant**：搭建虚拟机环境
* **WSL2**：在 Windows 上使用 Linux 环境
* **Docker**：在容器环境中练习

## 目录

* [Linux 内核和用户空间](01-linux-basics.md#linux-kernel-and-user-space)
* [进程管理](01-linux-basics.md#process-management)
* [命名空间](01-linux-basics.md#namespaces)
* [cgroups（控制组）](01-linux-basics.md#cgroups-control-groups)
* [文件系统](01-linux-basics.md#file-system)
* [网络基础](01-linux-basics.md#networking-basics)
* [安全上下文](01-linux-basics.md#security-context)
* [systemd 和服务管理](01-linux-basics.md#systemd-and-service-management)
* [内核参数和模块](01-linux-basics.md#kernel-parameters-and-modules)
* [系统资源限制](01-linux-basics.md#system-resource-limits)
* [日志管理](01-linux-basics.md#log-management)
* [DNS 和网络配置](01-linux-basics.md#dns-and-network-configuration)
* [时间同步](01-linux-basics.md#time-synchronization)
* [软件包管理](01-linux-basics.md#package-management)
* [基本 Linux 命令](01-linux-basics.md#essential-linux-commands)
* [容器相关 Linux 功能](01-linux-basics.md#container-related-linux-features)

## Linux 内核和用户空间

### 内核的作用

> **关键概念**：Linux 内核是操作系统的核心，充当硬件和软件之间的中介。

Linux 内核是操作系统的核心，充当硬件和软件之间的中介。其主要功能包括：

* **进程管理**：进程的创建、调度和终止
* **内存管理**：虚拟内存和物理内存分配
* **设备管理**：与硬件设备通信
* **系统调用接口**：为用户空间程序提供访问内核服务的方式

### 用户空间

用户空间是常规应用程序运行的内存区域。用户空间程序通过系统调用访问内核服务。

![展示 Linux 用户空间、内核空间和硬件层：应用程序和 Shell 通过系统库及系统调用接口调用内核子系统（进程与内存管理、文件系统、网络、安全），内核子系统再通过设备驱动程序访问 CPU、内存、存储和网卡。](../.gitbook/assets/en-basics-01-linux-basics-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-01-linux-basics-0.html)

### 系统调用示例

| 系统调用 | 描述 | 相关命令 |
| ----------- | --------------------- | ------------------- |
| `fork()`    | 创建新进程 | `ps`, `top`         |
| `exec()`    | 执行程序 | `bash`, `sh`        |
| `open()`    | 打开文件 | `cat`, `less`       |
| `read()`    | 从文件读取数据 | `cat`, `grep`       |
| `write()`   | 向文件写入数据 | `echo`, `tee`       |
| `socket()`  | 创建网络套接字 | `netstat`, `ss`     |
| `clone()`   | 创建命名空间 | `unshare`, `docker` |

### Linux 内核架构

![分层的 Linux 内核架构展示了用户空间的应用程序和 Shell 如何通过系统库及系统调用接口访问内核，下方是进程、内存、文件系统、网络和安全子系统，以及通过设备驱动程序与 CPU、内存、存储和网卡硬件通信的结构。](../.gitbook/assets/en-basics-01-linux-basics-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-01-linux-basics-1.html)

## 进程管理

### 进程和线程

* **进程**：正在运行的程序实例，具有独立的内存空间
* **线程**：在进程中执行的工作单元；同一进程的线程共享内存空间

### 进程状态

* **运行中**：当前正在 CPU 上执行
* **等待中**：正在等待 I/O 完成或事件发生
* **就绪**：准备运行但正在等待 CPU 分配
* **僵尸**：已终止，但父进程尚未检查其状态
* **已停止**：暂停状态

### 关键进程管理命令

```bash
# View process list
ps aux

# Real-time process monitoring
top

# Enhanced real-time process monitoring
htop

# Terminate process
kill <PID>
killall <process-name>

# Background execution
command &

# Job management
jobs
fg %<job-number>
bg %<job-number>
```

## 命名空间

命名空间是 Linux 内核的一项功能，可隔离进程组，使每个组能够独立看到系统资源。这是容器技术的核心要素。

### 主要命名空间类型

* **PID Namespace**：进程 ID 隔离，允许容器拥有自己的 PID 1（init）
* **Network Namespace**：网络栈隔离（接口、IP 地址、路由表、防火墙等），是容器网络的基础
* **Mount Namespace**：文件系统挂载点隔离，为每个容器提供独立的文件系统
* **UTS Namespace**：主机名和域名隔离，为每个容器提供唯一的主机标识
* **IPC Namespace**：进程间通信资源隔离（共享内存、信号量、消息队列等），对微服务架构中的服务隔离非常重要
* **User Namespace**：用户和组 ID 隔离，支持以 rootless 方式执行容器以增强安全性
* **cgroup Namespace**：cgroup 根目录隔离，提供容器内部的资源限制可见性
* **Time Namespace**：系统时钟隔离，允许每个容器独立设置时间（Linux 5.6+）

### 命名空间相关命令

```bash
# Check process namespaces
ls -la /proc/<PID>/ns/

# Execute command in new namespace
unshare --net --pid --fork --mount-proc bash

# Enter existing process's namespace
nsenter --target <PID> --net --pid bash

# Create and manage network namespaces
ip netns add <name>
ip netns exec <name> <command>

# Using user namespace for rootless container execution
unshare --user --map-root-user --mount --net bash

# Using time namespace (Linux 5.6+)
unshare --time bash
```

## cgroups（控制组）

cgroups 是 Linux 内核的一项功能，可限制和隔离进程组的资源使用。它用于实现容器资源限制，是云原生环境和 Kubernetes 中资源管理的核心技术。

### cgroups 的主要功能

* **CPU 时间限制**：限制进程组可用的 CPU 时间并分配 CPU 核心
* **内存限制**：限制进程组可用的内存并控制 OOM（内存不足）行为
* **块 I/O 限制**：磁盘 I/O 带宽限制和优先级设置
* **网络带宽限制**：网络流量限制（结合 tc 使用）
* **设备访问控制**：针对特定设备的访问控制和权限管理
* **PIDs 控制**：限制进程创建数量，防止 fork bomb
* **Freezer**：暂停和恢复进程组（用于暂停容器）
* **cpuset**：将进程绑定到特定 CPU 核心和 NUMA 节点

### cgroups v1 和 v2

* **cgroups v1**：每种资源类型具有独立的层级结构，仍用于旧版系统
* **cgroups v2**：统一的单一层级结构，可实现更一致的管理，是现代发行版的默认配置
* **混合模式**：同时使用 v1 和 v2，在利用新功能的同时保持兼容性

### cgroups 相关命令

```bash
# Check cgroups
ls -la /sys/fs/cgroup/                     # cgroups v2
ls -la /sys/fs/cgroup/cpu /sys/fs/cgroup/memory  # cgroups v1

# cgroups management through systemd (modern approach)
systemctl set-property <service-name> CPUQuota=20%
systemctl set-property <service-name> MemoryLimit=1G
systemctl set-property <service-name> IOWeight=500

# Check process cgroup
cat /proc/<PID>/cgroup

# Direct cgroups v2 manipulation (advanced)
echo $$ > /sys/fs/cgroup/user.slice/cgroup.procs
echo "max 100000" > /sys/fs/cgroup/user.slice/memory.max
echo "100000 500000" > /sys/fs/cgroup/user.slice/memory.high

# Container runtime and cgroups
podman stats  # Monitor container resource usage
docker run --cpus=0.5 --memory=512m nginx  # Set resource limits
```

## 文件系统

### 文件系统层级结构

Linux 使用从单个根目录（`/`）开始的层级文件系统结构。

关键目录：

* `/bin`：基本命令
* `/sbin`：系统管理命令
* `/etc`：系统配置文件
* `/home`：用户主目录
* `/var`：可变数据（日志、缓存等）
* `/tmp`：临时文件
* `/usr`：用户程序和数据
* `/proc`：进程和内核信息（虚拟文件系统）
* `/sys`：系统和硬件信息（虚拟文件系统）

### 文件系统类型

* **ext4**：默认 Linux 文件系统
* **XFS**：适用于大型文件系统
* **Btrfs**：提供快照和压缩等高级功能
* **OverlayFS**：将多个目录表示为单个目录（常用于容器）
* **tmpfs**：基于内存的临时文件系统

### 挂载和卷

```bash
# Mount file system
mount -t <filesystem-type> <source> <mount-point>

# Check mounted file systems
mount
df -h

# Unmount file system
umount <mount-point>
```

## 网络基础

### 网络接口

* **lo**：回环接口（127.0.0.1）
* **eth0、ens3 等**：物理网络接口
* **docker0、cni0 等**：虚拟网桥接口（容器网络）

### 网络配置命令

```bash
# Check network interfaces
ip addr show
ifconfig

# Check routing table
ip route
route -n

# Check network connections
netstat -tuln
ss -tuln

# Network packet analysis
tcpdump -i <interface>
```

### 网络命名空间和虚拟接口

```bash
# Create network namespace
ip netns add <namespace-name>

# Create virtual ethernet pair
ip link add <veth1> type veth peer name <veth2>

# Connect virtual interface to namespace
ip link set <veth2> netns <namespace-name>
```

## 安全上下文

### 用户和组

* **UID（用户 ID）**：用户标识符
* **GID（组 ID）**：组标识符
* **root（UID 0）**：具有管理权限的特殊用户

### 文件权限

Linux 文件权限由所有者、组和其他用户的读取（r）、写入（w）和执行（x）权限组成。

![展示 ls -l 输出的 10 个字符权限字符串如何分为 1 个字符的文件类型和三组分别对应所有者、组及其他用户的 r w x 三元组，以及示例 drwxr-xr-- 如何表示一个所有者拥有全部权限、组拥有读/执行权限、其他用户仅有读取权限的目录。](../.gitbook/assets/en-basics-01-linux-basics-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-01-linux-basics-2.html)

### 权限相关命令

```bash
# Change file permissions
chmod 755 <filename>  # rwxr-xr-x
chmod u+x <filename>  # Add execute permission for owner

# Change file owner
chown <user>:<group> <filename>

# Special permissions
chmod 4755 <filename>  # Set setuid
chmod 2755 <filename>  # Set setgid
chmod 1755 <filename>  # Set sticky bit
```

### SELinux 和 AppArmor

* **SELinux（Security-Enhanced Linux）**：由 NSA 开发的强制访问控制系统
* **AppArmor**：使用按程序划分的安全配置文件的访问控制系统

```bash
# Check SELinux status
getenforce

# Change SELinux mode
setenforce 0  # Permissive mode
setenforce 1  # Enforcing mode

# Check AppArmor status
aa-status

# AppArmor profile management
aa-enforce /etc/apparmor.d/<profile>
aa-complain /etc/apparmor.d/<profile>
```

## systemd 和服务管理

systemd 是现代 Linux 系统的 init 系统和服务管理器。它用于管理 Kubernetes 节点上的 kubelet 和 containerd 等核心服务。

### systemd 的主要功能

* **服务管理**：启动、停止、重启、启用/禁用系统服务
* **依赖关系管理**：自动管理服务依赖关系并支持并行启动
* **日志记录**：通过 journald 实现集成的日志管理
* **定时器**：可替代 cron 的定时器单元
* **资源管理**：通过 cgroups 为每项服务设置资源限制

### systemd 单元类型

* **service**：系统服务（例如 kubelet.service、containerd.service）
* **socket**：基于套接字的激活
* **target**：单元组（类似运行级别）
* **timer**：计划任务
* **mount**：文件系统挂载
* **device**：设备单元

### systemd 命令

```bash
# Check service status
systemctl status kubelet
systemctl status containerd

# Service control
systemctl start <service>
systemctl stop <service>
systemctl restart <service>
systemctl reload <service>  # Reload configuration

# Set auto-start at boot
systemctl enable <service>
systemctl disable <service>

# Check service logs
journalctl -u kubelet -f  # Real-time logs
journalctl -u kubelet --since "1 hour ago"
journalctl -u kubelet --no-pager

# List all services
systemctl list-units --type=service
systemctl list-unit-files --type=service

# Check failed services
systemctl --failed

# Reload systemd configuration
systemctl daemon-reload
```

### 编写 systemd 单元文件

Kubernetes 相关服务的 systemd 单元文件示例：

```ini
# /etc/systemd/system/kubelet.service
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

### systemd 资源限制

```bash
# CPU limit (20%)
systemctl set-property kubelet CPUQuota=20%

# Memory limit (1GB)
systemctl set-property kubelet MemoryLimit=1G

# I/O weight setting (100-1000, default 100)
systemctl set-property kubelet IOWeight=500

# Check settings
systemctl show kubelet | grep -E 'CPUQuota|MemoryLimit|IOWeight'
```

## 内核参数和模块

### 通过 sysctl 设置内核参数

sysctl 是用于查询和修改正在运行的内核参数的工具。在配置 Kubernetes 集群时，它对于网络和系统参数调优至关重要。

#### Kubernetes 所需的关键 sysctl 设置

```bash
# Enable IP forwarding (required for container networking)
sysctl -w net.ipv4.ip_forward=1
sysctl -w net.ipv6.conf.all.forwarding=1

# Enable bridge traffic to pass through iptables (required for CNI plugins)
sysctl -w net.bridge.bridge-nf-call-iptables=1
sysctl -w net.bridge.bridge-nf-call-ip6tables=1

# Increase maximum file descriptor count
sysctl -w fs.file-max=2097152

# Network performance tuning
sysctl -w net.core.somaxconn=32768
sysctl -w net.ipv4.tcp_max_syn_backlog=8192
sysctl -w net.core.netdev_max_backlog=16384

# ARP cache settings (for large clusters)
sysctl -w net.ipv4.neigh.default.gc_thresh1=80000
sysctl -w net.ipv4.neigh.default.gc_thresh2=90000
sysctl -w net.ipv4.neigh.default.gc_thresh3=100000

# Check current settings
sysctl net.ipv4.ip_forward
sysctl -a | grep bridge-nf-call

# Persistent settings (/etc/sysctl.conf or /etc/sysctl.d/*.conf)
cat <<EOF | sudo tee /etc/sysctl.d/99-kubernetes.conf
net.ipv4.ip_forward = 1
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
EOF

# Apply settings
sysctl --system
```

### 内核模块管理

许多 CNI 插件和存储驱动程序需要特定的内核模块。

```bash
# Load modules
modprobe overlay  # OverlayFS (container storage)
modprobe br_netfilter  # Bridge networking
modprobe ip_vs  # IPVS load balancing (kube-proxy IPVS mode)
modprobe ip_vs_rr  # Round Robin algorithm
modprobe ip_vs_wrr  # Weighted Round Robin
modprobe ip_vs_sh  # Source Hashing

# Check loaded modules
lsmod | grep overlay
lsmod | grep br_netfilter

# Check module information
modinfo overlay

# Set auto-load at boot
cat <<EOF | sudo tee /etc/modules-load.d/kubernetes.conf
overlay
br_netfilter
ip_vs
ip_vs_rr
ip_vs_wrr
ip_vs_sh
EOF

# Unload module
modprobe -r <module-name>
```

### 内核版本和功能检查

```bash
# Check kernel version
uname -r

# Check kernel compile options
cat /boot/config-$(uname -r) | grep OVERLAY
cat /boot/config-$(uname -r) | grep NETFILTER

# Check available kernel features
cat /proc/filesystems  # Supported file systems
cat /proc/sys/net/ipv4/ip_forward  # IP forwarding status
```

## 系统资源限制

### ulimit - 每用户资源限制

ulimit 限制进程可使用的系统资源。为了确保 Kubernetes 节点具有充足资源，可能需要进行调整。

```bash
# Check current limits
ulimit -a

# Key limit items
ulimit -n      # Number of open file descriptors
ulimit -u      # Maximum number of processes
ulimit -m      # Maximum memory size
ulimit -v      # Virtual memory size

# Change limits (current session)
ulimit -n 65536  # Increase file descriptors to 65536

# Persistent settings (/etc/security/limits.conf)
sudo tee -a /etc/security/limits.conf <<EOF
*               soft    nofile          65536
*               hard    nofile          65536
*               soft    nproc           32768
*               hard    nproc           32768
EOF

# Settings for specific users/groups
sudo tee -a /etc/security/limits.conf <<EOF
root            soft    nofile          65536
root            hard    nofile          65536
@docker         soft    nofile          65536
@docker         hard    nofile          65536
EOF
```

### PAM 限制设置

```bash
# Check PAM settings
cat /etc/pam.d/common-session
cat /etc/pam.d/common-session-noninteractive

# Add to PAM settings to apply limits.conf
echo "session required pam_limits.so" | sudo tee -a /etc/pam.d/common-session
```

### 每进程资源检查

```bash
# Check current resource limits for a process
cat /proc/<PID>/limits

# Check file descriptors for a specific process
ls -l /proc/<PID>/fd | wc -l
```

## 日志管理

### journald - systemd 集成日志记录

journald 是 systemd 的日志系统，用于管理 Kubernetes 节点上的系统服务日志。

```bash
# Full system logs
journalctl

# Specific service logs
journalctl -u kubelet
journalctl -u containerd
journalctl -u docker

# Real-time logs (similar to tail -f)
journalctl -u kubelet -f

# Time range specification
journalctl --since "2025-11-24 10:00:00"
journalctl --since "1 hour ago"
journalctl --since yesterday
journalctl --until "2025-11-24 12:00:00"

# Filter by priority
journalctl -p err        # Errors only
journalctl -p warning    # Warnings and above
journalctl -p debug      # All including debug

# Change output format
journalctl -u kubelet -o json        # JSON format
journalctl -u kubelet -o json-pretty # Pretty JSON
journalctl -u kubelet -o cat         # Messages only

# Boot logs
journalctl -b           # Current boot logs
journalctl -b -1        # Previous boot logs
journalctl --list-boots # Boot list

# Check disk usage
journalctl --disk-usage

# Clean logs
journalctl --vacuum-time=7d   # Delete logs older than 7 days
journalctl --vacuum-size=1G   # Delete logs over 1GB
```

### journald 配置

```bash
# journald configuration file
sudo vi /etc/systemd/journald.conf

# Key configuration options
# Storage=persistent        # Persistent storage to disk
# SystemMaxUse=1G          # Maximum disk usage
# SystemKeepFree=500M      # Minimum free space
# MaxRetentionSec=1month   # Maximum retention period

# Apply configuration
sudo systemctl restart systemd-journald
```

### 传统 syslog

有些系统仍然使用 syslog。

```bash
# syslog file locations
/var/log/syslog         # Debian/Ubuntu
/var/log/messages       # RHEL/CentOS

# Real-time log viewing
tail -f /var/log/syslog

# Log search
grep "kubelet" /var/log/syslog
grep -i "error" /var/log/syslog
```

### 日志轮转

配置日志轮转以防止日志文件无限增长。

```bash
# logrotate configuration
sudo vi /etc/logrotate.d/kubernetes

# Example configuration
/var/log/kubernetes/*.log {
    daily
    rotate 7
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
}

# Run rotation manually
sudo logrotate -f /etc/logrotate.d/kubernetes
```

## DNS 和网络配置

### DNS 配置

DNS 是 Kubernetes 集群内服务发现的核心。

```bash
# DNS configuration file
cat /etc/resolv.conf

# Example configuration
nameserver 8.8.8.8
nameserver 8.8.4.4
search cluster.local svc.cluster.local
options ndots:5

# DNS lookup test
nslookup kubernetes.default.svc.cluster.local
dig kubernetes.default.svc.cluster.local

# hosts file
cat /etc/hosts
```

### systemd-resolved

现代 Linux 发行版使用 systemd-resolved。

```bash
# Check systemd-resolved status
systemctl status systemd-resolved

# Check DNS servers
resolvectl status

# DNS cache statistics
resolvectl statistics

# Clear DNS cache
resolvectl flush-caches
```

### 网络配置文件

```bash
# NetworkManager (RHEL/CentOS 8+, Ubuntu 18.04+)
nmcli connection show
nmcli device status

# netplan (Ubuntu 18.04+)
cat /etc/netplan/*.yaml

# Example netplan configuration
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: true
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]

# Apply configuration
sudo netplan apply
```

## 时间同步

时间同步在分布式系统中非常重要。Kubernetes 集群中的所有节点都必须保持准确的时间。

### chronyd（推荐）

chronyd 是现代 NTP 客户端，其时间同步速度比 ntpd 更快。

```bash
# Install chronyd (RHEL/CentOS)
sudo yum install chrony

# Install chronyd (Ubuntu/Debian)
sudo apt install chrony

# Check service status
systemctl status chronyd

# Check time synchronization status
chronyc tracking

# NTP server list
chronyc sources

# Detailed information
chronyc sourcestats

# Manual time synchronization
sudo chronyc makestep
```

### chronyd 配置

```bash
# Configuration file
sudo vi /etc/chrony.conf

# Key settings
# NTP server configuration
server 0.pool.ntp.org iburst
server 1.pool.ntp.org iburst
server 2.pool.ntp.org iburst
server 3.pool.ntp.org iburst

# Fast synchronization
makestep 1.0 3

# Apply configuration
sudo systemctl restart chronyd
```

### timesyncd（Ubuntu 默认）

Ubuntu 默认使用 systemd-timesyncd。

```bash
# Check status
timedatectl status

# NTP synchronization status
timedatectl show-timesync --all

# Configuration file
sudo vi /etc/systemd/timesyncd.conf

# Example configuration
[Time]
NTP=0.pool.ntp.org 1.pool.ntp.org
FallbackNTP=time.google.com

# Restart service
sudo systemctl restart systemd-timesyncd
```

### 时区设置

```bash
# Check current time and timezone
timedatectl

# List timezones
timedatectl list-timezones

# Change timezone
sudo timedatectl set-timezone Asia/Seoul

# Manually set time (when NTP is disabled)
sudo timedatectl set-time "2025-11-24 12:00:00"

# Enable/disable NTP
sudo timedatectl set-ntp true
```

## 软件包管理

用于安装和管理 Kubernetes 及相关工具的软件包管理器。

### apt（Debian/Ubuntu）

```bash
# Update package list
sudo apt update

# Upgrade packages
sudo apt upgrade

# Install package
sudo apt install <package-name>

# Remove package
sudo apt remove <package-name>
sudo apt purge <package-name>  # Remove configuration files as well

# Search packages
apt search <keyword>

# Package information
apt show <package-name>

# List installed packages
apt list --installed

# Add repository (Kubernetes example)
sudo apt install -y apt-transport-https ca-certificates curl
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.28/deb/Release.key | \
  sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] \
  https://pkgs.k8s.io/core:/stable:/v1.28/deb/ /' | \
  sudo tee /etc/apt/sources.list.d/kubernetes.list

# Clean unnecessary packages
sudo apt autoremove
sudo apt autoclean
```

### yum/dnf（RHEL/CentOS/Fedora）

```bash
# Install package
sudo yum install <package-name>
sudo dnf install <package-name>  # Fedora/RHEL 8+

# Update packages
sudo yum update
sudo dnf update

# Remove package
sudo yum remove <package-name>
sudo dnf remove <package-name>

# Search packages
yum search <keyword>
dnf search <keyword>

# Package information
yum info <package-name>
dnf info <package-name>

# List installed packages
yum list installed
dnf list installed

# Add repository (Kubernetes example)
cat <<EOF | sudo tee /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/v1.28/rpm/
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/core:/stable:/v1.28/rpm/repodata/repomd.xml.key
EOF

# Clean cache
sudo yum clean all
sudo dnf clean all
```

### 软件包版本锁定

Kubernetes 组件存在版本兼容性要求，因此应防止自动更新。

```bash
# apt (Ubuntu/Debian)
sudo apt-mark hold kubelet kubeadm kubectl

# Remove apt hold
sudo apt-mark unhold kubelet kubeadm kubectl

# yum (RHEL/CentOS)
sudo yum install yum-plugin-versionlock
sudo yum versionlock add kubelet kubeadm kubectl

# Remove yum versionlock
sudo yum versionlock delete kubelet kubeadm kubectl
```

## 基本 Linux 命令

### 文件和目录管理

```bash
ls -la           # List files (including hidden)
cd <directory>   # Change directory
pwd              # Print current directory
mkdir -p <path>  # Create directory (create parent directories if needed)
rm -rf <path>    # Remove files/directories
cp -r <source> <destination> # Copy files/directories
mv <source> <destination>    # Move or rename files/directories
find <path> -name "<pattern>" # Search files
```

### 文本处理

```bash
cat <file>        # Output file contents
less <file>       # View file contents page by page
grep "<pattern>" <file> # Search pattern in file
sed 's/<pattern>/<replacement>/' <file> # Text substitution
awk '{print $1}' <file> # Text processing
```

### 系统信息

```bash
uname -a         # Kernel information
lsb_release -a   # Distribution information
free -h          # Memory usage
df -h            # Disk usage
du -sh <path>    # Directory size
```

### 进程和服务管理

```bash
systemctl status <service> # Check service status
systemctl start/stop/restart <service> # Service control
journalctl -u <service> # View service logs
```

## 容器相关 Linux 功能

### OverlayFS

OverlayFS 是一种联合挂载文件系统，可将多个目录表示为单个目录。Docker 等容器运行时使用它来实现镜像层。

### 网络网桥和 NAT

容器网络主要使用网桥接口和 NAT（网络地址转换）实现。

![单台主机上的 Docker 网桥网络](../../assets/diagrams/rendered/docker-bridge-networking.svg)

### 系统调用过滤（seccomp）

seccomp（安全计算模式）是 Linux 内核的一项功能，可限制进程可用的系统调用。它用于增强容器安全性。

### Capabilities 限制

Linux capabilities 将传统 root 权限划分为更小的权限单元。容器仅获得必要的 capabilities，以增强安全性。

关键 capabilities：

* `CAP_NET_ADMIN`：网络配置更改
* `CAP_SYS_ADMIN`：系统管理任务
* `CAP_CHOWN`：更改文件所有权
* `CAP_DAC_OVERRIDE`：绕过文件权限

## 结论

Linux 基础知识和功能对于理解 Kubernetes 和容器技术至关重要。以下是本文档涵盖的关键主题总结：

### 核心技术

* **命名空间和 cgroups**：容器隔离和资源管理的基础
* **OverlayFS**：容器镜像分层的核心
* **systemd**：Kubernetes 节点服务管理

### 基本运维知识

* **内核参数调优**：通过 sysctl 进行网络和系统优化
* **模块管理**：CNI 插件和存储驱动程序支持
* **日志管理**：通过 journald 分析系统和服务日志
* **时间同步**：在分布式系统中保持一致性

### 故障排除

* **资源限制**：通过 ulimit 和 cgroups 进行资源管理
* **网络**：DNS、网桥、iptables 配置
* **软件包管理**：Kubernetes 组件的版本管理

掌握这些 Linux 基础知识后，您可以有效排查 Kubernetes 环境中的问题、优化集群并可靠地运行它们。

## 测验

要测试您在本章中学到的内容，请完成 [Linux 基础测验](../quizzes/basics/01-linux-basics-quiz.md)。

## 参考资料

* [Linux 文档项目](https://tldp.org/)
* [Linux 内核文档](https://www.kernel.org/doc/)
* [Linux 命名空间](https://man7.org/linux/man-pages/man7/namespaces.7.html)
* [控制组 v2](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)
