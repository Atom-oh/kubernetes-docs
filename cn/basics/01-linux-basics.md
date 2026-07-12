# Linux Basics

> **支持的版本**: All major Linux distributions (Ubuntu 20.04+, CentOS/RHEL 8+, Debian 11+) **最后更新**: February 11, 2026

理解 Linux 基础知识对于掌握 Kubernetes 和 container（容器）技术至关重要。本文档介绍在 Kubernetes 环境中特别重要的核心 Linux 概念。

## Lab Environment Setup

若要跟随本文档中的示例进行练习，你需要准备以下环境：

### Required Environment

* Linux 操作系统（推荐 Ubuntu 20.04+、CentOS/RHEL 8+、Debian 11+）
* Terminal 访问权限
* sudo 权限

### Cloud Environment Setup (Optional)

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

### Local Environment Setup (Optional)

进行本地练习时，可以使用以下任一方式：

* **VirtualBox + Vagrant**: 设置虚拟机环境
* **WSL2**: 在 Windows 上使用 Linux 环境
* **Docker**: 在 container 环境中练习

## Table of Contents

* [Linux Kernel and User Space](01-linux-basics.md#linux-kernel-and-user-space)
* [Process Management](01-linux-basics.md#process-management)
* [Namespaces](01-linux-basics.md#namespaces)
* [cgroups (Control Groups)](01-linux-basics.md#cgroups-control-groups)
* [File System](01-linux-basics.md#file-system)
* [Networking Basics](01-linux-basics.md#networking-basics)
* [Security Context](01-linux-basics.md#security-context)
* [systemd and Service Management](01-linux-basics.md#systemd-and-service-management)
* [Kernel Parameters and Modules](01-linux-basics.md#kernel-parameters-and-modules)
* [System Resource Limits](01-linux-basics.md#system-resource-limits)
* [Log Management](01-linux-basics.md#log-management)
* [DNS and Network Configuration](01-linux-basics.md#dns-and-network-configuration)
* [Time Synchronization](01-linux-basics.md#time-synchronization)
* [Package Management](01-linux-basics.md#package-management)
* [Essential Linux Commands](01-linux-basics.md#essential-linux-commands)
* [Container-Related Linux Features](01-linux-basics.md#container-related-linux-features)

## Linux Kernel and User Space

### Role of the Kernel

> **关键概念**: Linux kernel 是操作系统的核心，在硬件和软件之间充当中介。

Linux kernel 是操作系统的核心，在硬件和软件之间充当中介。它的主要功能包括：

* **进程管理**: 进程创建、调度和终止
* **内存管理**: 虚拟内存和物理内存分配
* **设备管理**: 与硬件设备通信
* **系统调用接口**: 为用户空间程序访问 kernel 服务提供方式

### User Space

用户空间是普通应用程序运行的内存区域。用户空间程序通过系统调用访问 kernel 服务。

### System Call Examples

| System Call | Description           | Related Commands    |
| ----------- | --------------------- | ------------------- |
| `fork()`    | Create new process    | `ps`, `top`         |
| `exec()`    | Execute program       | `bash`, `sh`        |
| `open()`    | Open file             | `cat`, `less`       |
| `read()`    | Read data from file   | `cat`, `grep`       |
| `write()`   | Write data to file    | `echo`, `tee`       |
| `socket()`  | Create network socket | `netstat`, `ss`     |
| `clone()`   | Create namespace      | `unshare`, `docker` |

### Linux Kernel Architecture

## Process Management

### Processes and Threads

* **进程**: 正在运行的程序实例，拥有独立的内存空间
* **线程**: 在进程内执行的工作单元；同一进程的线程共享内存空间

### Process States

* **运行中**: 当前正在 CPU 上执行
* **等待中**: 等待 I/O 完成或事件发生
* **就绪**: 已准备运行，但正在等待 CPU 分配
* **僵尸**: 已终止，但父进程尚未检查其状态
* **已停止**: 挂起状态

### Key Process Management Commands

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

## Namespaces

Namespaces（命名空间）是 Linux kernel 的一项功能，它隔离进程组，使每个组都能独立地看到系统资源。这是 container 技术的核心元素。

### Main Namespace Types

* **PID Namespace**: 进程 ID 隔离，允许 container 拥有自己的 PID 1（init）
* **Network Namespace**: 网络栈隔离（接口、IP 地址、路由表、防火墙等），是 container networking 的基础
* **Mount Namespace**: 文件系统挂载点隔离，为每个 container 提供独立文件系统
* **UTS Namespace**: 主机名和域名隔离，为每个 container 提供唯一的主机标识符
* **IPC Namespace**: 进程间通信资源隔离（共享内存、信号量、消息队列等），对 microservices architecture 中的服务隔离很重要
* **User Namespace**: 用户和组 ID 隔离，支持 rootless container 执行以增强安全性
* **cgroup Namespace**: cgroup 根目录隔离，在 container 内提供资源限制可见性
* **Time Namespace**: 系统时钟隔离，允许每个 container 拥有独立时间设置（Linux 5.6+）

### Namespace-Related Commands

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

## cgroups (Control Groups)

cgroups 是 Linux kernel 的一项功能，用于限制和隔离进程组的资源使用。它用于实现 container 资源限制。它是 cloud-native 环境和 Kubernetes 中资源管理的核心技术。

### Main cgroups Features

* **CPU 时间限制**: 限制进程组可用的 CPU 时间并分配 CPU core
* **内存限制**: 限制进程组可用的内存并控制 OOM (Out of Memory) 行为
* **Block I/O 限制**: 磁盘 I/O 带宽限制和优先级设置
* **网络带宽限制**: 网络流量限制（与 tc 结合使用）
* **设备访问控制**: 对特定设备进行访问控制和权限管理
* **PIDs 控制**: 限制进程创建数量以防止 fork bomb
* **Freezer**: 暂停和恢复进程组（用于 container 暂停）
* **cpuset**: 将进程绑定到特定 CPU core 和 NUMA 节点

### cgroups v1 and v2

* **cgroups v1**: 每种资源类型使用独立层级，仍在 legacy system 中使用
* **cgroups v2**: 统一的单一层级，管理更加一致，是现代发行版中的默认选择
* **Hybrid Mode**: 同时使用 v1 和 v2，在利用新功能的同时保持兼容性

### cgroups-Related Commands

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

## File System

### File System Hierarchy

Linux 采用从单一根目录（`/`）开始的层级式文件系统结构。

关键目录：

* `/bin`: 基本命令
* `/sbin`: 系统管理命令
* `/etc`: 系统配置文件
* `/home`: 用户主目录
* `/var`: 可变数据（日志、缓存等）
* `/tmp`: 临时文件
* `/usr`: 用户程序和数据
* `/proc`: 进程和 kernel 信息（虚拟文件系统）
* `/sys`: 系统和硬件信息（虚拟文件系统）

### File System Types

* **ext4**: 默认 Linux 文件系统
* **XFS**: 适合大型文件系统
* **Btrfs**: 提供 snapshot 和压缩等高级功能
* **OverlayFS**: 将多个目录表示为单个目录（常用于 container）
* **tmpfs**: 基于内存的临时文件系统

### Mount and Volumes

```bash
# Mount file system
mount -t <filesystem-type> <source> <mount-point>

# Check mounted file systems
mount
df -h

# Unmount file system
umount <mount-point>
```

## Networking Basics

### Network Interfaces

* **lo**: Loopback 接口（127.0.0.1）
* **eth0, ens3, etc.**: 物理网络接口
* **docker0, cni0, etc.**: 虚拟 bridge 接口（container networking）

### Network Configuration Commands

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

### Network Namespaces and Virtual Interfaces

```bash
# Create network namespace
ip netns add <namespace-name>

# Create virtual ethernet pair
ip link add <veth1> type veth peer name <veth2>

# Connect virtual interface to namespace
ip link set <veth2> netns <namespace-name>
```

## Security Context

### Users and Groups

* **UID (User ID)**: 用户标识符
* **GID (Group ID)**: 组标识符
* **root (UID 0)**: 拥有管理权限的特殊用户

### File Permissions

Linux 文件权限由 owner、group 和 other users 的 read (r)、write (w) 和 execute (x) 权限组成。

### Permission-Related Commands

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

### SELinux and AppArmor

* **SELinux (Security-Enhanced Linux)**: 由 NSA 开发的强制访问控制系统
* **AppArmor**: 使用按程序定义的安全配置文件的访问控制系统

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

## systemd and Service Management

systemd 是现代 Linux 系统的 init system 和 service manager。它用于管理 Kubernetes 节点上的 kubelet 和 containerd 等核心服务。

### Main systemd Features

* **服务管理**: 启动、停止、重启、启用/禁用系统服务
* **依赖管理**: 自动服务依赖管理和并行启动
* **日志记录**: 通过 journald 进行集成日志管理
* **Timers**: 可替代 cron 的 timer unit
* **资源管理**: 通过 cgroups 实现按服务的资源限制

### systemd Unit Types

* **service**: 系统服务（例如 kubelet.service、containerd.service）
* **socket**: 基于 socket 的激活
* **target**: Unit 组（类似 runlevel）
* **timer**: 定时任务
* **mount**: 文件系统挂载
* **device**: 设备 unit

### systemd Commands

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

### Writing systemd Unit Files

Kubernetes 相关服务的 systemd unit file 示例：

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

### systemd Resource Limits

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

## Kernel Parameters and Modules

### Kernel Parameter Settings via sysctl

sysctl 是用于查询和修改正在运行的 kernel parameter 的工具。在配置 Kubernetes 集群时，它对于网络和系统参数调优至关重要。

#### Key sysctl Settings Required for Kubernetes

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

### Kernel Module Management

许多 CNI plugin 和 storage driver 需要特定的 kernel module。

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

### Kernel Version and Feature Check

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

## System Resource Limits

### ulimit - Per-User Resource Limits

ulimit 用于限制进程可使用的系统资源。在 Kubernetes 节点上可能需要进行调整，以确保资源充足。

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

### PAM Limit Settings

```bash
# Check PAM settings
cat /etc/pam.d/common-session
cat /etc/pam.d/common-session-noninteractive

# Add to PAM settings to apply limits.conf
echo "session required pam_limits.so" | sudo tee -a /etc/pam.d/common-session
```

### Per-Process Resource Checking

```bash
# Check current resource limits for a process
cat /proc/<PID>/limits

# Check file descriptors for a specific process
ls -l /proc/<PID>/fd | wc -l
```

## Log Management

### journald - systemd Integrated Logging

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

### journald Configuration

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

### Traditional syslog

有些系统仍在使用 syslog。

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

### Log Rotation

配置日志轮转可以防止日志文件无限增长。

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

## DNS and Network Configuration

### DNS Configuration

DNS 是 Kubernetes 集群内部 service discovery 的核心。

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

### Network Configuration Files

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

## Time Synchronization

时间同步在分布式系统中非常重要。Kubernetes 集群中的所有节点都必须保持准确的时间。

### chronyd (Recommended)

chronyd 是现代 NTP client，与 ntpd 相比同步时间更快。

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

### chronyd Configuration

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

### timesyncd (Ubuntu Default)

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

### Timezone Settings

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

## Package Management

用于安装和管理 Kubernetes 及相关工具的 package manager 用法。

### apt (Debian/Ubuntu)

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

### yum/dnf (RHEL/CentOS/Fedora)

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

### Package Version Locking

Kubernetes 组件有版本兼容性要求，因此应防止自动更新。

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

## Essential Linux Commands

### File and Directory Management

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

### Text Processing

```bash
cat <file>        # Output file contents
less <file>       # View file contents page by page
grep "<pattern>" <file> # Search pattern in file
sed 's/<pattern>/<replacement>/' <file> # Text substitution
awk '{print $1}' <file> # Text processing
```

### System Information

```bash
uname -a         # Kernel information
lsb_release -a   # Distribution information
free -h          # Memory usage
df -h            # Disk usage
du -sh <path>    # Directory size
```

### Process and Service Management

```bash
systemctl status <service> # Check service status
systemctl start/stop/restart <service> # Service control
journalctl -u <service> # View service logs
```

## Container-Related Linux Features

### OverlayFS

OverlayFS 是一个 union mount 文件系统，可将多个目录表示为单个目录。Docker 等 container runtime 使用它来实现 image layer。

### Network Bridge and NAT

Container networking 主要通过 bridge 接口和 NAT (Network Address Translation) 实现。

```mermaid
flowchart TB
    subgraph "Host"
        subgraph "Container A"
            CA["eth0
172.17.0.2"]
        end

        subgraph "Container B"
            CB["eth0
172.17.0.3"]
        end

        BR["Bridge (docker0)
172.17.0.1/16"]

        ETH["eth0
192.168.1.10"]

        IPTABLES["iptables
NAT Rules"]

        CA -- "veth pair" --> BR
        CB -- "veth pair" --> BR
        BR --> IPTABLES
        IPTABLES --> ETH
    end

    INTERNET["External Network
    Internet"]

    ETH <--> INTERNET

    %% Style definitions
    classDef container fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef bridge fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef host fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    classDef network fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef iptables fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class CA,CB container
    class BR bridge
    class ETH host
    class INTERNET network
    class IPTABLES iptables
```

### System Call Filtering (seccomp)

seccomp (Secure Computing Mode) 是 Linux kernel 的一项功能，用于限制进程可用的系统调用。它用于增强 container 安全性。

### Capabilities Restriction

Linux capabilities 将传统 root 权限划分为更小的权限单元。Container 只获得必要的 capabilities，以增强安全性。

关键 capabilities：

* `CAP_NET_ADMIN`: 网络配置更改
* `CAP_SYS_ADMIN`: 系统管理任务
* `CAP_CHOWN`: 更改文件所有权
* `CAP_DAC_OVERRIDE`: 绕过文件权限

## Conclusion

Linux 基础知识和功能对于理解 Kubernetes 与 container 技术至关重要。以下是本文档涵盖的关键主题摘要：

### Core Technologies

* **Namespaces and cgroups**: container 隔离和资源管理的基础
* **OverlayFS**: container image layering 的核心
* **systemd**: Kubernetes 节点服务管理

### Essential Operations Knowledge

* **Kernel Parameter Tuning**: 通过 sysctl 进行网络和系统优化
* **Module Management**: 支持 CNI plugin 和 storage driver
* **Log Management**: 通过 journald 进行系统和服务日志分析
* **Time Synchronization**: 在分布式系统中保持一致性

### Troubleshooting

* **Resource Limits**: 通过 ulimit 和 cgroups 进行资源管理
* **Networking**: DNS、bridge、iptables 配置
* **Package Management**: Kubernetes 组件的版本管理

有了这些 Linux 基础，你就可以在 Kubernetes 环境中有效排查问题、优化集群并可靠地运行它们。

## Quiz

若要测试你在本章学到的内容，请完成 [Linux Basics Quiz](../quizzes/basics/01-linux-basics-quiz.md)。

## References

* [The Linux Documentation Project](https://tldp.org/)
* [Linux Kernel Documentation](https://www.kernel.org/doc/)
* [Linux Namespaces](https://man7.org/linux/man-pages/man7/namespaces.7.html)
* [Control Groups v2](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)
