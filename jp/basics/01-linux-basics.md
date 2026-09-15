# Linux の基礎

> **対応バージョン**: 検証済みの例: Ubuntu 24.04 LTS、Debian 13、Amazon Linux 2023。パッケージ名やサービス名はディストリビューションによって異なります **最終更新**: September 15, 2026

Linux の基礎を理解することは、Kubernetes とコンテナ技術を理解するために不可欠です。このドキュメントでは、Kubernetes 環境で特に重要となる Linux の中核的な概念を扱います。

ターミナルやネットワークに初めて触れる場合は、[はじめての Linux ネットワーク](../networking/beginner/README.md) のレッスン 1 から始めてください。このドキュメントは、その後にコンテナやカーネルの概念をより深く参照するためのリファレンスとしても機能します。

## ラボ環境のセットアップ

このドキュメントの例を実際に試すには、次の環境が必要です。

### 必要な環境

* Linux オペレーティングシステム (Ubuntu 24.04 LTS、Debian 13、または Amazon Linux 2023 を推奨)
* ターミナルへのアクセス
* sudo 権限

### クラウド環境のセットアップ (任意)

隔離されたトレーニング用 VM を使用してください。AWS の場合は、正しいアーキテクチャとリージョンの AL2023 を選択します。古いハードコードされた AMI は移植性がありません。AWS は AL2 の標準サポートが 2026 年 6 月 30 日に終了したと公表しています。以下は AMI を検索するだけの操作です。インスタンスの作成と権限を絞ったアクセスは別途用意し、その後に既存のインスタンスへ接続してください。

```bash
# Read-only AMI discovery; select a kernel-specific parameter when reproducibility is required.
aws ssm get-parameter --region us-east-1 \
  --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
  --query Parameter.Value --output text

# SSH connection
ssh -i your-key.pem ec2-user@your-instance-public-ip
```

### ローカル環境のセットアップ (任意)

ローカルで練習する場合は、次のいずれかを利用できます。

* **VirtualBox + Vagrant**: 仮想マシン環境を構築します
* **WSL2**: Windows 上で Linux 環境を利用します
* **Docker**: 基本的なシェル演習には適していますが、通常のコンテナは完全な systemd ホストや、ホストネットワーク/カーネル演習に必要な権限を提供しません。

## 目次

* [Linux カーネルとユーザー空間](01-linux-basics.md#linux-kernel-and-user-space)
* [プロセス管理](01-linux-basics.md#process-management)
* [Namespace](01-linux-basics.md#namespaces)
* [cgroups (Control Groups)](01-linux-basics.md#cgroups-control-groups)
* [ファイルシステム](01-linux-basics.md#file-system)
* [ネットワークの基礎](01-linux-basics.md#networking-basics)
* [セキュリティコンテキスト](01-linux-basics.md#security-context)
* [systemd とサービス管理](01-linux-basics.md#systemd-and-service-management)
* [カーネルパラメータとモジュール](01-linux-basics.md#kernel-parameters-and-modules)
* [システムリソース制限](01-linux-basics.md#system-resource-limits)
* [ログ管理](01-linux-basics.md#log-management)
* [DNS とネットワーク設定](01-linux-basics.md#dns-and-network-configuration)
* [時刻同期](01-linux-basics.md#time-synchronization)
* [パッケージ管理](01-linux-basics.md#package-management)
* [必須の Linux コマンド](01-linux-basics.md#essential-linux-commands)
* [コンテナ関連の Linux 機能](01-linux-basics.md#container-related-linux-features)

## Linux カーネルとユーザー空間

### カーネルの役割

> **重要な概念**: Linux カーネルはオペレーティングシステムの中核であり、ハードウェアとソフトウェアの仲介役として動作します。

Linux カーネルはオペレーティングシステムの中核であり、ハードウェアとソフトウェアの仲介役として動作します。主な機能は次のとおりです。

* **プロセス管理**: プロセスの生成、スケジューリング、終了
* **メモリ管理**: 仮想メモリと物理メモリの割り当て
* **デバイス管理**: ハードウェアデバイスとの通信
* **システムコールインターフェイス**: ユーザー空間のプログラムがカーネルのサービスにアクセスする手段を提供

### ユーザー空間

ユーザー空間は、通常のアプリケーションが動作するメモリ領域です。ユーザー空間のプログラムは、システムコールを通じてカーネルのサービスにアクセスします。

![Linux のユーザー空間、カーネル空間、ハードウェアの各層: アプリケーションと Shell はシステムライブラリとシステムコールインターフェイスを介してカーネルのサブシステムに到達し、デバイスドライバーが CPU、メモリ、ストレージ、ネットワークカードに到達します。](../.gitbook/assets/en-basics-01-linux-basics-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-01-linux-basics-0.html)

### システムコールの例

| システムコール | 説明 | 関連コマンド |
| ----------- | --------------------- | ------------------- |
| `fork()`    | 新しいプロセスの作成 | `ps`, `top`         |
| `exec()`    | プログラムの実行 | `bash`, `sh`        |
| `open()`    | ファイルのオープン | `cat`, `less`       |
| `read()`    | ファイルからのデータ読み取り | `cat`, `grep`       |
| `write()`   | ファイルへのデータ書き込み | `echo`, `tee`       |
| `socket()`  | ネットワークソケットの作成 | `netstat`, `ss`     |
| `clone()`   | Namespace の作成 | `unshare`, `docker` |

### Linux カーネルアーキテクチャ

![層で表した Linux カーネルアーキテクチャ: アプリケーションと Shell はシステムライブラリとシステムコールインターフェイスを介してカーネルに入り、カーネルのサブシステムはデバイスドライバーを介してハードウェアを駆動します。](../.gitbook/assets/en-basics-01-linux-basics-1.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-01-linux-basics-1.html)

## プロセス管理

### プロセスとスレッド

* **プロセス**: 実行中のプログラムのインスタンスで、独立したメモリ空間を持ちます
* **スレッド**: プロセス内で実行される作業単位。同一プロセスのスレッドはメモリ空間を共有します

### プロセスの状態

* **Running**: 現在 CPU 上で実行中
* **Waiting**: I/O の完了やイベントの発生を待機中
* **Ready**: 実行可能だが CPU の割り当てを待機中
* **Zombie**: 終了したが、親プロセスがその状態を確認していない
* **Stopped**: 一時停止された状態

### 主要なプロセス管理コマンド

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

## Namespace

Namespace (名前空間) は、プロセスグループを分離して、それぞれのグループがシステムリソースを独立して認識できるようにする Linux カーネルの機能です。これはコンテナ技術の中核的な要素です。

### 主な Namespace の種類

* **PID Namespace**: プロセス ID の分離。コンテナが独自の PID 1 (init) を持てるようにします
* **Network Namespace**: ネットワークスタックの分離 (インターフェイス、IP アドレス、ルーティングテーブル、ファイアウォールなど)。コンテナネットワークの基盤です
* **Mount Namespace**: マウントテーブルを分離します。ファイルシステムの内容やコンテナのルート分離には、適切なマウント/ルート設定が必要です
* **UTS Namespace**: ホスト名と NIS ドメイン名の分離 (DNS ドメインではありません)。各コンテナに固有のホスト識別子を与えます
* **IPC Namespace**: プロセス間通信リソースの分離 (共有メモリ、セマフォ、メッセージキューなど)。マイクロサービスアーキテクチャにおけるサービス分離で重要です
* **User Namespace**: ユーザー ID とグループ ID の分離。rootless なコンテナ実行をサポートし、セキュリティを強化します
* **cgroup Namespace**: cgroup ルートディレクトリの分離。コンテナ内部でリソース制限を確認できるようにします
* **Time Namespace**: CLOCK_MONOTONIC/CLOCK_BOOTTIME のオフセットを仮想化します (Linux 5.6 以降)。実時間の壁時計は対象外です

### Namespace 関連コマンド

```bash
# Check process namespaces
ls -la /proc/<PID>/ns/

# Execute command in new namespace
sudo unshare --mount --net --pid --fork --mount-proc bash

# Enter existing process's namespace
sudo nsenter --target <PID> --net --pid bash

# Create and manage network namespaces
ip netns add <name>
ip netns exec <name> <command>

# Using user namespace for rootless container execution
unshare --user --map-root-user --mount --net bash

# Using time namespace (Linux 5.6+)
sudo unshare --time --fork bash
```

## cgroups (Control Groups)

cgroups は、プロセスグループのリソース使用量を制限・分離する Linux カーネルの機能です。コンテナのリソース制限を実装するために使用されます。クラウドネイティブ環境や Kubernetes におけるリソース管理の中核技術です。

### cgroups の主な機能

* **CPU 時間の制限**: プロセスグループが使用できる CPU 時間を制限し、CPU コアを割り当てます
* **メモリの制限**: プロセスグループが使用できるメモリを制限し、OOM (Out of Memory) の挙動を制御します
* **ブロック I/O の制限**: ディスク I/O 帯域幅の制限と優先度の設定
* **ネットワークトラフィック制御**: tc/eBPF と cgroup の分類を組み合わせます。cgroup v2 には単独のネットワーク帯域幅設定はありません
* **デバイスアクセス制御**: 特定デバイスに対するアクセス制御と権限管理
* **PIDs の制御**: プロセス生成数を制限して fork 爆弾を防ぎます
* **Freezer**: プロセスグループの一時停止と再開 (コンテナの一時停止に使用)
* **cpuset**: プロセスを特定の CPU コアや NUMA ノードにバインドします

### cgroups v1 と v2

* **cgroups v1**: リソースの種類ごとに独立した階層を持ちます。レガシーシステムで今も使われています
* **cgroups v2**: 単一の統合された階層でより一貫した管理を行います。最新のディストリビューションではデフォルトです
* **ハイブリッドモード**: v1 と v2 を併用し、互換性を保ちながら新機能を活用します

### cgroups 関連コマンド

```bash
# Check cgroups
ls -la /sys/fs/cgroup/                     # cgroups v2
ls -la /sys/fs/cgroup/cpu /sys/fs/cgroup/memory  # cgroups v1

# cgroups management through systemd (modern approach)
sudo systemctl set-property --runtime <service-name> CPUQuota=20%
sudo systemctl set-property --runtime <service-name> MemoryMax=1G
sudo systemctl set-property --runtime <service-name> IOWeight=500

# Check process cgroup
cat /proc/<PID>/cgroup

# Run only the example command inside a transient cgroup managed by systemd.
sudo systemd-run --scope -p CPUQuota=20% -p MemoryHigh=768M -p MemoryMax=1G sleep 60
# memory.max/high take one byte count or "max"; cpu.max takes quota and period.
# Do not move your shell into systemd-owned user.slice or edit its control files.

# Container runtime and cgroups
podman stats  # Monitor container resource usage
docker run --cpus=0.5 --memory=512m nginx  # Set resource limits
```

## ファイルシステム

### ファイルシステム階層

Linux は、単一のルートディレクトリ (`/`) から始まる階層的なファイルシステム構造を持ちます。

主要なディレクトリ:

* `/bin`: 基本的なコマンド
* `/sbin`: システム管理コマンド
* `/etc`: システム設定ファイル
* `/home`: ユーザーのホームディレクトリ
* `/var`: 可変データ (ログ、キャッシュなど)
* `/tmp`: 一時ファイル
* `/usr`: ユーザープログラムとデータ
* `/proc`: プロセスとカーネルの情報 (仮想ファイルシステム)
* `/sys`: システムとハードウェアの情報 (仮想ファイルシステム)

### ファイルシステムの種類

* **ext4**: 一般的な Linux ファイルシステム。デフォルト設定はディストリビューションによって異なります
* **XFS**: 大規模なファイルシステムに適しています
* **Btrfs**: スナップショットや圧縮などの高度な機能を提供します
* **OverlayFS**: 複数のディレクトリを単一のディレクトリとして表現します (コンテナで広く利用)
* **tmpfs**: メモリを backing store とする一時ファイルシステム。swap を無効にしていない場合、ページが swap される可能性があります

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

### ネットワークインターフェイス

* **lo**: ループバックインターフェイス (127.0.0.1)
* **eth0、ens3 など**: 物理ネットワークインターフェイス
* **docker0、cni0 など**: 仮想ブリッジインターフェイス (コンテナネットワーク)

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

### Network Namespace と仮想インターフェイス

```bash
# Create network namespace
ip netns add <namespace-name>

# Create virtual ethernet pair
ip link add <veth1> type veth peer name <veth2>

# Connect virtual interface to namespace
ip link set <veth2> netns <namespace-name>
```

## セキュリティコンテキスト

### ユーザーとグループ

* **UID (User ID)**: ユーザー識別子
* **GID (Group ID)**: グループ識別子
* **root (UID 0)**: 管理者権限を持つ特別なユーザー

### ファイルパーミッション

Linux のファイルパーミッションは、所有者、グループ、その他のユーザーに対する読み取り (r)、書き込み (w)、実行 (x) の権限で構成されます。

![ls -l の 10 文字のパーミッション文字列が、ファイル種別を表す 1 文字と、所有者・グループ・その他に対する r w x の 3 文字組に分かれる仕組み。drwxr-xr-- はディレクトリで、所有者は全権限、グループは読み取りと実行、その他は読み取りのみのアクセスであることを示します。](../.gitbook/assets/en-basics-01-linux-basics-2.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-01-linux-basics-2.html)

### パーミッション関連コマンド

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

* **SELinux (Security-Enhanced Linux)**: NSA が開発した強制アクセス制御システム
* **AppArmor**: プログラムごとのセキュリティプロファイルを使用するアクセス制御システム

```bash
# Check SELinux status
getenforce

# Only in a reviewed isolated lab: permissive disables enforcement system-wide.
# sudo setenforce 0
# Restore the original mode after investigation; do not use permissive as a generic fix.

# Check AppArmor status
aa-status

# AppArmor profile management
aa-enforce /etc/apparmor.d/<profile>
aa-complain /etc/apparmor.d/<profile>
```

## systemd とサービス管理

systemd は、現代の Linux システムにおける init システムかつサービスマネージャーです。Kubernetes ノード上の kubelet や containerd といった中核サービスの管理に使用されます。

### systemd の主な機能

* **サービス管理**: システムサービスの起動、停止、再起動、有効化/無効化
* **依存関係管理**: サービス依存関係の自動管理と並列起動
* **ロギング**: journald による統合的なログ管理
* **タイマー**: cron を置き換え可能なタイマーユニット
* **リソース管理**: cgroups によるサービス単位のリソース制限

### systemd ユニットの種類

* **service**: システムサービス (例: kubelet.service、containerd.service)
* **socket**: ソケットベースのアクティベーション
* **target**: ユニットのグループ (ランレベルに類似)
* **timer**: スケジュールされたタスク
* **mount**: ファイルシステムのマウント
* **device**: デバイスユニット

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

### systemd ユニットファイルの記述

小さなトレーニング用サービスでユニットの構造を確認します。kubelet は systemctl cat kubelet で確認し、ディストリビューションや kubeadm が管理するユニットとドロップインは置き換えずにそのまま維持してください。

```ini
# /etc/systemd/system/linux-basics-demo.service
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

### systemd のリソース制限

以下のコマンドは、上記のトレーニング用ユニットをラボ VM に保存し、daemon-reload を完了していることを前提としています。この学習用の制限を本番の kubelet/containerd に適用しないでください。

```bash
# CPU limit (20%)
sudo systemctl set-property --runtime linux-basics-demo.service CPUQuota=20%

# Memory limit (1GB)
sudo systemctl set-property --runtime linux-basics-demo.service MemoryMax=1G

# I/O weight setting (1-10000, default 100)
sudo systemctl set-property --runtime linux-basics-demo.service IOWeight=500

# Check settings
systemctl show linux-basics-demo.service | grep -E 'CPUQuota|MemoryMax|IOWeight'
```

## カーネルパラメータとモジュール

### sysctl によるカーネルパラメータ設定

sysctl は、実行中のカーネルパラメータを参照・変更するためのツールです。Kubernetes クラスターを構成する際のネットワークおよびシステムパラメータのチューニングに不可欠です。

#### CNI 固有の sysctl 設定とチューニング例

これらは、すべての Kubernetes ノードに必須のデフォルト値ではありません。選択した IP ファミリー、CNI、Service プロキシの要件を確認してください。bridge-netfilter の設定は br_netfilter を使用する構成にのみ適用されます。パフォーマンス/ARP/conntrack の値は測定なしに本番へ適用しないでください。既存の値を記録し、隔離されたトレーニング用 VM を使用してください。

```bash
# Enable IP forwarding (required for container networking)
sudo sysctl -w net.ipv4.ip_forward=1
sudo sysctl -w net.ipv6.conf.all.forwarding=1

# Enable bridge traffic to pass through iptables (only for CNI configurations requiring bridge netfilter)
sudo sysctl -w net.bridge.bridge-nf-call-iptables=1
sudo sysctl -w net.bridge.bridge-nf-call-ip6tables=1

# Increase maximum file descriptor count
sudo sysctl -w fs.file-max=2097152

# Network performance tuning
sudo sysctl -w net.core.somaxconn=32768
sudo sysctl -w net.ipv4.tcp_max_syn_backlog=8192
sudo sysctl -w net.core.netdev_max_backlog=16384

# ARP cache settings (for large clusters)
sudo sysctl -w net.ipv4.neigh.default.gc_thresh1=80000
sudo sysctl -w net.ipv4.neigh.default.gc_thresh2=90000
sudo sysctl -w net.ipv4.neigh.default.gc_thresh3=100000

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
sudo sysctl --system
```

### カーネルモジュールの管理

必要なモジュールは、ランタイム/CNI/ストレージの選択によって異なります。IPVS モードは Kubernetes 1.35 以降で非推奨です。以下の IPVS コマンドは既存の IPVS クラスター専用です。新しいクラスターで、列挙されたすべてのモジュールを事前ロードしないでください。

```bash
# Load modules
sudo modprobe overlay  # OverlayFS (container storage)
sudo modprobe br_netfilter  # Bridge networking
sudo modprobe ip_vs  # IPVS load balancing (kube-proxy IPVS mode)
sudo modprobe ip_vs_rr  # Round Robin algorithm
sudo modprobe ip_vs_wrr  # Weighted Round Robin
sudo modprobe ip_vs_sh  # Source Hashing

# Check loaded modules
lsmod | grep overlay
lsmod | grep br_netfilter

# Check module information
modinfo overlay

# Set auto-load at boot
cat <<EOF | sudo tee /etc/modules-load.d/kubernetes.conf
overlay
# Add br_netfilter only if required by the chosen CNI.
EOF

# Unload module
sudo modprobe -r <module-name>
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

### ulimit - ユーザー単位のリソース制限

ulimit は、プロセスが使用できるシステムリソースを制限します。Kubernetes ノードで十分なリソースを確保するために調整が必要になる場合があります。

```bash
# Check current limits
ulimit -a

# Key limit items
ulimit -n      # Number of open file descriptors
ulimit -u      # Maximum number of processes
ulimit -m      # RSS limit; not enforced on modern Linux
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

### PAM の制限設定

limits.conf は、pam_limits を使用する新しいログインセッションに適用されます。通常の systemd システムサービスは自動的にこれを継承しないため、LimitNOFILE や TasksMax といったサービスのドロップインを使用してください。既存のセッションやプロセスは変更されません。重複した common-session のエントリを無闇に追記するのではなく、ディストリビューションの PAM チェーンを確認してください。

```bash
# Inspect the active configuration; PAM file names differ by distribution.
grep -R pam_limits.so /etc/pam.d
systemctl show kubelet -p LimitNOFILE -p TasksMax
```

### プロセス単位のリソース確認

```bash
# Check current resource limits for a process
cat /proc/<PID>/limits

# Check file descriptors for a specific process
find /proc/<PID>/fd -mindepth 1 -maxdepth 1 -printf '%f\n' | wc -l
```

## ログ管理

### journald - systemd の統合ロギング

journald は systemd のロギングシステムで、Kubernetes ノード上のシステムサービスのログを管理します。

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
journalctl -p err        # Error and higher severity (0-3)
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
journalctl --vacuum-time=7d   # Remove archived journal files older than 7 days
journalctl --vacuum-size=1G   # Remove oldest archived journals toward 1GiB total
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

一部のシステムでは、今も syslog が使用されています。

```bash
# syslog file locations
# /var/log/syslog         # Debian/Ubuntu
# /var/log/messages       # RHEL/CentOS

# Real-time log viewing
tail -f /var/log/syslog

# Log search
grep "kubelet" /var/log/syslog
grep -i "error" /var/log/syslog
```

### ログローテーション

通常のアプリケーションのファイルには logrotate を使用します。copytruncate にはコピーと切り詰めの競合があり、レコードが失われる可能性があります。アプリケーションが対応している場合は、ログの再オープンを優先してください。kubelet は CRI コンテナログのローテーションを自身で管理します。

```bash
# logrotate configuration
sudo vi /etc/logrotate.d/linux-basics-demo

# File content (only application text logs not managed by kubelet):
```

```text
/var/log/linux-basics-demo/*.log {
    daily
    rotate 7
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
}
```

```bash
# Run rotation manually
sudo logrotate -f /etc/logrotate.d/linux-basics-demo
```

## DNS とネットワーク設定

### DNS の設定

NetworkManager や systemd-resolved がホストの resolv.conf を管理している場合があるため、まずそれを確認してください。8.8.8.8 のようなパブリックリゾルバーでは cluster.local の Service を解決できません。ClusterFirst の Pod は kubelet が構成したクラスター DNS を使用します。ホストのリゾルバーにクラスターの検索サフィックスを追加しても、クラスター DNS への接続性は得られません。

```bash
# On the Linux host
cat /etc/resolv.conf
cat /etc/hosts
# If a cluster is available, inspect its actual DNS Service address.
kubectl -n kube-system get service kube-dns
# Run inside an existing Pod with DNS utilities and ClusterFirst policy:
# nslookup kubernetes.default.svc.cluster.local
```

以下は **Pod のリゾルバーファイル形式**の例です。IP、namespace、クラスタードメインは実際の値に置き換えてください。ホストの設定にコピーしないでください。

```text
nameserver <cluster-dns-service-ip>
search <namespace>.svc.cluster.local svc.cluster.local cluster.local
options ndots:5
```

### systemd-resolved

現代の Linux ディストリビューションは systemd-resolved を使用します。

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

ディストリビューションが NetworkManager と netplan のどちらを使用しているかを確認してください。netplan の YAML は /etc/netplan 配下のファイル内容であり、シェルコマンドではありません。リモートのアドレス設定やルーティングを変更する前に復旧手段を用意し、netplan try で検証してください。

```bash
nmcli connection show
nmcli device status
# On a netplan-based installation:
ls /etc/netplan
```

```yaml
# Example netplan file: replace eth0 with the actual interface name.
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: true
```

```bash
sudo netplan generate
sudo netplan try
```

## 時刻同期

分散システムにおいて時刻同期は非常に重要です。Kubernetes クラスターのすべてのノードは正確な時刻を維持する必要があります。

### chronyd (推奨)

chronyd は、変動するネットワーク条件に適した NTP クライアント/サーバーです。同期性能は、クロック、参照ソース、設定によって左右されます。

```bash
# Install chronyd (RHEL/CentOS)
sudo yum install chrony

# Install chronyd (Ubuntu/Debian)
sudo apt install chrony

# Check the installed unit: chronyd on RHEL/Amazon Linux, chrony on Debian/Ubuntu.
systemctl status chronyd

# Check time synchronization status
chronyc tracking

# NTP server list
chronyc sources

# Detailed information
chronyc sourcestats

# Manual time synchronization
# Only during a reviewed maintenance window; stepping can disrupt time-sensitive workloads.
# sudo chronyc makestep
```

### chronyd の設定

RHEL 系のシステムでは通常 /etc/chrony.conf を、Debian/Ubuntu では /etc/chrony/chrony.conf を使用します。パブリックサーバーに置き換える前に、ディストリビューションやプロバイダーの設定 (EC2 の Amazon Time Sync Service を含む) を確認してください。以下は設定ファイルの内容です。

```text
# Choose an approved reachable time source.
server <approved-ntp-server> iburst
# Permit stepping only during the first three clock updates.
makestep 1.0 3
```

```bash
# Choose the unit actually installed on your distribution:
systemctl status chronyd.service  # RHEL/Amazon Linux
systemctl status chrony.service   # Debian/Ubuntu
chronyc tracking
chronyc sources
```

### timesyncd (ディストリビューション固有の選択)

Ubuntu は 25.10 でデフォルトの時刻サービスを chrony に切り替えました。それ以前のリリースやイメージでは systemd-timesyncd が使われている場合があります。有効な時刻サービスは 1 つだけにしてください。show-timesync は timesyncd 固有のコマンドです。chrony は chronyc で確認してください。

```bash
timedatectl status
# Only for installations using systemd-timesyncd:
timedatectl show-timesync --all
systemctl status systemd-timesyncd
```

```ini
# /etc/systemd/timesyncd.conf: use approved servers for this environment.
[Time]
NTP=<approved-ntp-server>
```

```bash
# After editing a timesyncd installation:
sudo systemctl restart systemd-timesyncd
```

### タイムゾーンの設定

```bash
# Check current time and timezone
timedatectl

# List timezones
timedatectl list-timezones

# Change timezone
sudo timedatectl set-timezone Asia/Seoul

# Manually set time (when NTP is disabled)
: "${LAB_TIME:?Set an intentional time for an isolated VM with NTP disabled}"
# sudo timedatectl set-time "$LAB_TIME"

# Enable/disable NTP
sudo timedatectl set-ntp true
```

## パッケージ管理

Kubernetes と関連ツールをインストール・管理するためのパッケージマネージャーの使い方です。

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
set -o pipefail
: "${KUBERNETES_MINOR:?Choose a supported cluster-compatible minor, for example v1.37}"
sudo apt install -y ca-certificates curl gnupg
sudo mkdir -p -m 755 /etc/apt/keyrings
curl -fsSL "https://pkgs.k8s.io/core:/stable:/${KUBERNETES_MINOR}/deb/Release.key" | \
  sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/${KUBERNETES_MINOR}/deb/ /" | \
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
: "${KUBERNETES_MINOR:?Choose a supported cluster-compatible minor, for example v1.37}"
cat <<EOF | sudo tee /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/${KUBERNETES_MINOR}/rpm/
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/core:/stable:/${KUBERNETES_MINOR}/rpm/repodata/repomd.xml.key
exclude=kubelet kubeadm kubectl cri-tools kubernetes-cni
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

# DNF: install the distribution-supported versionlock plugin first.
# Alternatively, use the Kubernetes repository exclusions shown above.
sudo dnf versionlock add kubelet kubeadm kubectl

# Remove the versionlock entry
sudo dnf versionlock delete kubelet kubeadm kubectl
```

## 必須の Linux コマンド

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
systemctl restart <service> # Or use start/stop as separate subcommands
journalctl -u <service> # View service logs
```

## コンテナ関連の Linux 機能

### OverlayFS

OverlayFS は、複数のディレクトリを単一のディレクトリとして表現する union マウントファイルシステムです。Docker などのコンテナランタイムがイメージレイヤーを実装するために使用します。

### ネットワークブリッジと NAT

Docker のデフォルトのブリッジネットワークは、外部トラフィックに対してブリッジと NAT を使用します。Kubernetes の CNI 実装はルーティング、オーバーレイ、VPC ネイティブネットワークを使用する場合があり、Pod 間のトラフィックが常に NAT されるわけではありません。

![単一ホスト上の Docker ブリッジネットワーク: 2 つのコンテナが veth ペアを介して docker0 ブリッジに接続し、トラフィックは iptables の NAT ルールとホストの eth0 インターフェイスを通過して外部のインターネットに到達します。](../.gitbook/assets/en-basics-01-linux-basics-10.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-01-linux-basics-10.html)

### システムコールのフィルタリング (seccomp)

seccomp (Secure Computing Mode) は、プロセスが利用できるシステムコールを制限する Linux カーネルの機能です。コンテナのセキュリティを強化するために使用されます。

### Capabilities の制限

Linux の capabilities は、従来の root 権限をより細かい権限単位に分割します。コンテナには必要な capabilities のみを付与し、セキュリティを高めます。

主要な capabilities:

* `CAP_NET_ADMIN`: ネットワーク設定の変更
* `CAP_SYS_ADMIN`: システム管理作業
* `CAP_CHOWN`: ファイル所有者の変更
* `CAP_DAC_OVERRIDE`: ファイルパーミッションのバイパス

## まとめ

Linux の基礎と機能は、Kubernetes とコンテナ技術を理解するために不可欠です。このドキュメントで扱った主なトピックをまとめます。

### 中核技術

* **Namespace と cgroups**: コンテナの分離とリソース管理の基盤
* **OverlayFS**: コンテナイメージのレイヤー化の中核
* **systemd**: Kubernetes ノードのサービス管理

### 必須の運用知識

* **カーネルパラメータのチューニング**: sysctl によるネットワークとシステムの最適化
* **モジュール管理**: CNI プラグインとストレージドライバーのサポート
* **ログ管理**: journald によるシステムおよびサービスログの分析
* **時刻同期**: 分散システムにおける一貫性の維持

### トラブルシューティング

* **リソース制限**: ulimit と cgroups によるリソース管理
* **ネットワーク**: DNS、ブリッジ、iptables の設定
* **パッケージ管理**: Kubernetes コンポーネントのバージョン管理

この Linux の基礎があれば、Kubernetes 環境の問題を効果的にトラブルシューティングし、クラスターを最適化して、安定して運用できるようになります。

## クイズ

この章で学んだ内容を確認するには、[Linux 基礎クイズ](../quizzes/basics/01-linux-basics-quiz.md) に取り組んでください。

## 参考資料

* [The Linux Documentation Project](https://tldp.org/)
* [Linux Kernel Documentation](https://www.kernel.org/doc/)
* [Linux Namespaces](https://man7.org/linux/man-pages/man7/namespaces.7.html)
* [Control Groups v2](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)

## 検証用参考資料

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
