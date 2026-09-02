# Linux の基礎

> **対応バージョン**: すべての主要な Linux ディストリビューション（Ubuntu 20.04+、CentOS/RHEL 8+、Debian 11+） **最終更新**: February 11, 2026

Linux の基礎を理解することは、Kubernetes とコンテナ技術を理解するために不可欠です。このドキュメントでは、Kubernetes 環境で特に重要な Linux の主要概念を取り上げます。

## ラボ環境のセットアップ

このドキュメント内の例に沿って進めるには、以下の環境が必要です。

### 必要な環境

* Linux オペレーティングシステム（Ubuntu 20.04+、CentOS/RHEL 8+、Debian 11+ を推奨）
* ターミナルへのアクセス
* sudo 権限

### クラウド環境のセットアップ（任意）

AWS EC2 インスタンスを使用する場合:

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

### ローカル環境のセットアップ（任意）

ローカルで練習するには、以下のいずれかを使用できます。

* **VirtualBox + Vagrant**: 仮想マシン環境をセットアップ
* **WSL2**: Windows 上で Linux 環境を使用
* **Docker**: コンテナ環境で練習

## 目次

* [Linux カーネルとユーザー空間](01-linux-basics.md#linux-kernel-and-user-space)
* [プロセス管理](01-linux-basics.md#process-management)
* [Namespace](01-linux-basics.md#namespaces)
* [cgroups（Control Groups）](01-linux-basics.md#cgroups-control-groups)
* [ファイルシステム](01-linux-basics.md#file-system)
* [ネットワークの基礎](01-linux-basics.md#networking-basics)
* [Security Context](01-linux-basics.md#security-context)
* [systemd とサービス管理](01-linux-basics.md#systemd-and-service-management)
* [カーネルパラメータとモジュール](01-linux-basics.md#kernel-parameters-and-modules)
* [システムリソース制限](01-linux-basics.md#system-resource-limits)
* [ログ管理](01-linux-basics.md#log-management)
* [DNS とネットワーク設定](01-linux-basics.md#dns-and-network-configuration)
* [時刻同期](01-linux-basics.md#time-synchronization)
* [パッケージ管理](01-linux-basics.md#package-management)
* [重要な Linux コマンド](01-linux-basics.md#essential-linux-commands)
* [コンテナ関連の Linux 機能](01-linux-basics.md#container-related-linux-features)

## Linux カーネルとユーザー空間

### カーネルの役割

> **重要な概念**: Linux カーネルはオペレーティングシステムの中核であり、ハードウェアとソフトウェアの仲介役を担います。

Linux カーネルはオペレーティングシステムの中核であり、ハードウェアとソフトウェアの仲介役を担います。主な機能は次のとおりです。

* **プロセス管理**: プロセスの作成、スケジューリング、終了
* **メモリ管理**: 仮想メモリと物理メモリの割り当て
* **デバイス管理**: ハードウェアデバイスとの通信
* **システムコールインターフェース**: ユーザー空間プログラムがカーネルサービスにアクセスする手段を提供

### ユーザー空間

ユーザー空間は、通常のアプリケーションが実行されるメモリ領域です。ユーザー空間のプログラムは、システムコールを通じてカーネルサービスにアクセスします。

![Linux のユーザー空間、カーネル空間、ハードウェア層を示します。アプリケーションとシェルは、システムライブラリおよびシステムコールインターフェースを通じてカーネルサブシステム（プロセス・メモリ管理、ファイルシステム、ネットワーク、セキュリティ）を呼び出し、デバイスドライバーを介して CPU、メモリ、ストレージ、ネットワークカードに到達します。](../.gitbook/assets/en-basics-01-linux-basics-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-01-linux-basics-0.html)

### システムコールの例

| システムコール | 説明           | 関連コマンド    |
| ----------- | --------------------- | ------------------- |
| `fork()`    | 新しいプロセスを作成    | `ps`, `top`         |
| `exec()`    | プログラムを実行       | `bash`, `sh`        |
| `open()`    | ファイルを開く             | `cat`, `less`       |
| `read()`    | ファイルからデータを読み取る   | `cat`, `grep`       |
| `write()`   | ファイルにデータを書き込む    | `echo`, `tee`       |
| `socket()`  | ネットワークソケットを作成 | `netstat`, `ss`     |
| `clone()`   | Namespace を作成      | `unshare`, `docker` |

### Linux カーネルアーキテクチャ

![階層化された Linux カーネルアーキテクチャを示します。ユーザー空間のアプリケーションとシェルは、システムライブラリおよびシステムコールインターフェースを通じてカーネルに到達し、その下にプロセス、メモリ、ファイルシステム、ネットワーク、セキュリティのサブシステムがあり、デバイスドライバーが CPU、メモリ、ストレージ、ネットワークカードのハードウェアと通信します。](../.gitbook/assets/en-basics-01-linux-basics-1.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-01-linux-basics-1.html)

## プロセス管理

### プロセスとスレッド

* **プロセス**: 独自の独立したメモリ空間を持つ、実行中のプログラムのインスタンス
* **スレッド**: プロセス内で実行される作業単位。同じプロセスのスレッドはメモリ空間を共有します

### プロセスの状態

* **実行中**: 現在 CPU 上で実行中
* **待機中**: I/O の完了またはイベントの発生を待機中
* **実行可能**: 実行の準備はできているが、CPU の割り当てを待機中
* **ゾンビ**: 終了したが、親プロセスがその状態を確認していない
* **停止中**: 一時停止状態

### 主なプロセス管理コマンド

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

Namespaces は、プロセスグループを分離し、各グループがシステムリソースを独立して認識できるようにする Linux カーネルの機能です。これはコンテナ技術の中核要素です。

### 主な Namespace の種類

* **PID Namespace**: プロセス ID を分離し、コンテナが独自の PID 1（init）を持つことを可能にします
* **Network Namespace**: ネットワークスタック（インターフェース、IP アドレス、ルーティングテーブル、ファイアウォールなど）を分離し、コンテナネットワーキングの基盤となります
* **Mount Namespace**: ファイルシステムのマウントポイントを分離し、コンテナごとに独立したファイルシステムを提供します
* **UTS Namespace**: ホスト名とドメイン名を分離し、各コンテナに一意のホスト識別子を与えます
* **IPC Namespace**: プロセス間通信リソース（共有メモリ、セマフォ、メッセージキューなど）を分離し、マイクロサービスアーキテクチャにおけるサービス分離で重要です
* **User Namespace**: ユーザーおよびグループ ID を分離し、セキュリティを高める rootless コンテナ実行をサポートします
* **cgroup Namespace**: cgroup のルートディレクトリを分離し、コンテナ内でリソース制限を可視化します
* **Time Namespace**: システムクロックを分離し、コンテナごとに独立した時刻設定を可能にします（Linux 5.6+）

### Namespace 関連コマンド

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

## cgroups（Control Groups）

cgroups は、プロセスグループのリソース使用量を制限・分離する Linux カーネルの機能です。コンテナのリソース制限を実装するために使用されます。クラウドネイティブ環境と Kubernetes におけるリソース管理の中核技術です。

### cgroups の主な機能

* **CPU 時間の制限**: プロセスグループが使用できる CPU 時間を制限し、CPU コアを割り当てます
* **メモリ制限**: プロセスグループが使用できるメモリを制限し、OOM（Out of Memory）動作を制御します
* **ブロック I/O 制限**: ディスク I/O 帯域幅の制限と優先度設定
* **ネットワーク帯域幅制限**: ネットワークトラフィックの制限（tc と組み合わせて使用）
* **デバイスアクセス制御**: 特定デバイスへのアクセス制御と権限管理
* **PIDs 制御**: fork bomb を防ぐためにプロセス作成数を制限
* **Freezer**: プロセスグループを一時停止・再開（コンテナの一時停止に使用）
* **cpuset**: プロセスを特定の CPU コアおよび NUMA ノードにバインド

### cgroups v1 と v2

* **cgroups v1**: リソースタイプごとに個別の階層を持ち、レガシーシステムで現在も使用されています
* **cgroups v2**: より一貫した管理のための統合された単一階層で、最新のディストリビューションではデフォルトです
* **ハイブリッドモード**: v1 と v2 を併用し、互換性を維持しながら新機能を活用します

### cgroups 関連コマンド

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

## ファイルシステム

### ファイルシステム階層

Linux には、単一のルートディレクトリ（`/`）から始まる階層的なファイルシステム構造があります。

主要なディレクトリ:

* `/bin`: 基本コマンド
* `/sbin`: システム管理コマンド
* `/etc`: システム設定ファイル
* `/home`: ユーザーのホームディレクトリ
* `/var`: 可変データ（ログ、キャッシュなど）
* `/tmp`: 一時ファイル
* `/usr`: ユーザープログラムとデータ
* `/proc`: プロセスおよびカーネル情報（仮想ファイルシステム）
* `/sys`: システムおよびハードウェア情報（仮想ファイルシステム）

### ファイルシステムの種類

* **ext4**: デフォルトの Linux ファイルシステム
* **XFS**: 大規模なファイルシステムに適しています
* **Btrfs**: スナップショットや圧縮などの高度な機能を提供します
* **OverlayFS**: 複数のディレクトリを単一のディレクトリとして表現します（コンテナで一般的に使用）
* **tmpfs**: メモリベースの一時ファイルシステム

### マウントとボリューム

```bash
# Mount file system
mount -t <filesystem-type> <source> <mount-point>

# Check mounted file systems
mount
df -h

# Unmount file system
umount <mount-point>
```

## ネットワークの基礎

### ネットワークインターフェース

* **lo**: ループバックインターフェース（127.0.0.1）
* **eth0, ens3, etc.**: 物理ネットワークインターフェース
* **docker0, cni0, etc.**: 仮想ブリッジインターフェース（コンテナネットワーキング）

### ネットワーク設定コマンド

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

### Network Namespace と仮想インターフェース

```bash
# Create network namespace
ip netns add <namespace-name>

# Create virtual ethernet pair
ip link add <veth1> type veth peer name <veth2>

# Connect virtual interface to namespace
ip link set <veth2> netns <namespace-name>
```

## Security Context

### ユーザーとグループ

* **UID（User ID）**: ユーザー識別子
* **GID（Group ID）**: グループ識別子
* **root（UID 0）**: 管理者権限を持つ特別なユーザー

### ファイル権限

Linux のファイル権限は、所有者、グループ、その他のユーザーに対する読み取り（r）、書き込み（w）、実行（x）権限で構成されます。

![ls -l の 10 文字の権限文字列が、1 文字のファイルタイプと、所有者・グループ・その他のユーザー向けの 3 組の r w x に分かれることを示します。また、例の drwxr-xr-- は、所有者にはすべての権限、グループには読み取り・実行権限、その他には読み取り専用権限を持つディレクトリであることを表します。](../.gitbook/assets/en-basics-01-linux-basics-2.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-01-linux-basics-2.html)

### 権限関連コマンド

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

### SELinux と AppArmor

* **SELinux（Security-Enhanced Linux）**: NSA が開発した強制アクセス制御システム
* **AppArmor**: プログラムごとのセキュリティプロファイルを使用するアクセス制御システム

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

## systemd とサービス管理

systemd は、最新の Linux システムの init システムおよびサービスマネージャーです。Kubernetes ノード上の kubelet や containerd などの中核サービスの管理に使用されます。

### systemd の主な機能

* **サービス管理**: システムサービスの開始、停止、再起動、有効化・無効化
* **依存関係管理**: サービス依存関係の自動管理と並列起動
* **ロギング**: journald による統合ログ管理
* **Timers**: cron の代替となるタイマーユニット
* **リソース管理**: cgroups によるサービスごとのリソース制限

### systemd Unit の種類

* **service**: システムサービス（例: kubelet.service、containerd.service）
* **socket**: ソケットベースのアクティベーション
* **target**: Unit グループ（runlevel に類似）
* **timer**: スケジュールされたタスク
* **mount**: ファイルシステムのマウント
* **device**: デバイス Unit

### systemd コマンド

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

### systemd Unit ファイルの作成

Kubernetes 関連サービス用の systemd Unit ファイルの例:

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

### systemd リソース制限

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

## カーネルパラメータとモジュール

### sysctl によるカーネルパラメータ設定

sysctl は、実行中のカーネルパラメータを照会および変更するツールです。Kubernetes クラスターを設定する際のネットワークおよびシステムパラメータのチューニングに不可欠です。

#### Kubernetes に必要な主要 sysctl 設定

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

### カーネルモジュール管理

多くの CNI プラグインとストレージドライバーには、特定のカーネルモジュールが必要です。

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

### カーネルバージョンと機能の確認

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

## システムリソース制限

### ulimit - ユーザーごとのリソース制限

ulimit はプロセスが使用できるシステムリソースを制限します。十分なリソースを確保するため、Kubernetes ノードでは調整が必要になる場合があります。

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

### PAM 制限設定

```bash
# Check PAM settings
cat /etc/pam.d/common-session
cat /etc/pam.d/common-session-noninteractive

# Add to PAM settings to apply limits.conf
echo "session required pam_limits.so" | sudo tee -a /etc/pam.d/common-session
```

### プロセスごとのリソース確認

```bash
# Check current resource limits for a process
cat /proc/<PID>/limits

# Check file descriptors for a specific process
ls -l /proc/<PID>/fd | wc -l
```

## ログ管理

### journald - systemd 統合ロギング

journald は、Kubernetes ノード上のシステムサービスログを管理する systemd のロギングシステムです。

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

### journald の設定

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

### 従来の syslog

一部のシステムでは、現在も syslog を使用しています。

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

### ログローテーション

ログファイルが無制限に大きくなることを防ぐため、ログローテーションを設定します。

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

## DNS とネットワーク設定

### DNS 設定

DNS は Kubernetes クラスター内のサービスディスカバリーの中核です。

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

最新の Linux ディストリビューションでは systemd-resolved を使用します。

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

### ネットワーク設定ファイル

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

## 時刻同期

分散システムでは時刻同期が非常に重要です。Kubernetes クラスター内のすべてのノードは、正確な時刻を維持する必要があります。

### chronyd（推奨）

chronyd は、ntpd より速く時刻を同期する最新の NTP クライアントです。

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

### chronyd の設定

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

### timesyncd（Ubuntu のデフォルト）

Ubuntu ではデフォルトで systemd-timesyncd を使用します。

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

### タイムゾーン設定

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

## パッケージ管理

Kubernetes および関連ツールのインストールと管理に使用するパッケージマネージャー。

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

### パッケージバージョンの固定

Kubernetes コンポーネントにはバージョン互換性の要件があるため、自動更新を防ぐ必要があります。

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

## 重要な Linux コマンド

### ファイルとディレクトリの管理

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

### テキスト処理

```bash
cat <file>        # Output file contents
less <file>       # View file contents page by page
grep "<pattern>" <file> # Search pattern in file
sed 's/<pattern>/<replacement>/' <file> # Text substitution
awk '{print $1}' <file> # Text processing
```

### システム情報

```bash
uname -a         # Kernel information
lsb_release -a   # Distribution information
free -h          # Memory usage
df -h            # Disk usage
du -sh <path>    # Directory size
```

### プロセスとサービスの管理

```bash
systemctl status <service> # Check service status
systemctl start/stop/restart <service> # Service control
journalctl -u <service> # View service logs
```

## コンテナ関連の Linux 機能

### OverlayFS

OverlayFS は、複数のディレクトリを単一のディレクトリとして表現する union mount ファイルシステムです。Docker などのコンテナランタイムがイメージレイヤーを実装するために使用します。

### ネットワークブリッジと NAT

コンテナネットワーキングは、主にブリッジインターフェースと NAT（Network Address Translation）を使用して実装されます。

![Docker bridge networking on a single host](../../assets/diagrams/rendered/docker-bridge-networking.svg)

### システムコールフィルタリング（seccomp）

seccomp（Secure Computing Mode）は、プロセスが利用できるシステムコールを制限する Linux カーネルの機能です。コンテナのセキュリティを強化するために使用されます。

### Capabilities の制限

Linux capabilities は、従来の root 権限をより小さな権限単位に分割します。コンテナには、セキュリティを向上させるために必要な capabilities のみが付与されます。

主な capabilities:

* `CAP_NET_ADMIN`: ネットワーク設定の変更
* `CAP_SYS_ADMIN`: システム管理タスク
* `CAP_CHOWN`: ファイル所有者の変更
* `CAP_DAC_OVERRIDE`: ファイル権限をバイパス

## まとめ

Linux の基礎と機能は、Kubernetes とコンテナ技術を理解するために不可欠です。このドキュメントで扱った主なトピックを以下にまとめます。

### コア技術

* **Namespaces と cgroups**: コンテナの分離とリソース管理の基盤
* **OverlayFS**: コンテナイメージのレイヤリングの中核
* **systemd**: Kubernetes ノードのサービス管理

### 必須の運用知識

* **カーネルパラメータのチューニング**: sysctl によるネットワークとシステムの最適化
* **モジュール管理**: CNI プラグインとストレージドライバーのサポート
* **ログ管理**: journald によるシステムおよびサービスログの分析
* **時刻同期**: 分散システムにおける一貫性の維持

### トラブルシューティング

* **リソース制限**: ulimit と cgroups によるリソース管理
* **ネットワーキング**: DNS、bridge、iptables の設定
* **パッケージ管理**: Kubernetes コンポーネントのバージョン管理

この Linux の基盤知識があれば、Kubernetes 環境で問題を効果的にトラブルシューティングし、クラスターを最適化して、信頼性高く運用できます。

## クイズ

この章で学んだ内容を確認するには、[Linux の基礎クイズ](../quizzes/basics/01-linux-basics-quiz.md)に挑戦してください。

## 参考資料

* [The Linux Documentation Project](https://tldp.org/)
* [Linux Kernel Documentation](https://www.kernel.org/doc/)
* [Linux Namespaces](https://man7.org/linux/man-pages/man7/namespaces.7.html)
* [Control Groups v2](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)
