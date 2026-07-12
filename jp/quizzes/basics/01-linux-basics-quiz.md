# Linux Basics Quiz

このクイズでは、Kubernetes とコンテナ技術の基盤となる Linux の基本概念についての理解を確認します。

## Multiple Choice Questions

1. 次のうち、Linux kernel の主な役割ではないものはどれですか？
   - A) Process management
   - B) Memory management
   - C) ユーザーインターフェースの提供
   - D) Device management
<details>

<summary>答えを表示</summary>

**答え: C) ユーザーインターフェースの提供**

**解説:**
Linux kernel はオペレーティングシステムの中核であり、ハードウェアとソフトウェアの仲介役として機能します。kernel の主な役割には、process management、memory management、device management、および system call インターフェースの提供が含まれます。ユーザーインターフェース（GUI、CLI）は、user space で実行される別のプログラムによって提供されるものであり、kernel の責任ではありません。

</details>

2. 次のうち、Linux namespace の種類ではないものはどれですか？
   - A) PID namespace
   - B) Network namespace
   - C) Memory namespace
   - D) User namespace
<details>

<summary>答えを表示</summary>

**答え: C) Memory namespace**

**解説:**
Linux には次の namespace があります: PID (Process ID)、Network、Mount、UTS (hostname)、IPC (Inter-Process Communication)、User、cgroup namespace。Memory namespace は存在しません。メモリ分離は主に cgroups によって管理されます。

</details>

3. cgroups (Control Groups) の主な機能は何ですか？
   - A) プロセスグループのリソース使用量を制限し分離する
   - B) ファイルシステムアクセスを制御する
   - C) ネットワークパケットをフィルタリングする
   - D) ユーザー認証を管理する
   
<details>

<summary>答えを表示</summary>

**答え: A) プロセスグループのリソース使用量を制限し分離する**

**解説:**
cgroups は、プロセスグループのリソース使用量を制限し分離する Linux kernel の機能です。CPU time、memory、block I/O、network bandwidth などのリソース使用量を制限および監視できます。これは、コンテナでリソース制限を実装するための中核技術です。
</details>

4. ファイル権限 "rwxr-xr--" において、group user の権限は何ですか？
   - A) 読み取り、書き込み、実行
   - B) 読み取り、実行
   - C) 読み取りのみ
   - D) 実行のみ
   
<details>

<summary>答えを表示</summary>

**答え: B) 読み取り、実行**

**解説:**
ファイル権限 "rwxr-xr--" では次のようになります:
  - 最初の 3 文字 (rwx): owner の権限 - 読み取り、書き込み、実行
  - 中央の 3 文字 (r-x): group の権限 - 読み取り、実行
  - 最後の 3 文字 (r--): other users の権限 - 読み取りのみ

したがって、group users には読み取りと実行の権限があります。

</details>

5. コンテナイメージレイヤーの実装に主に使用されるファイルシステムはどれですか？
   - A) ext4
   - B) XFS
   - C) OverlayFS
   - D) Btrfs

<details>

<summary>答えを表示</summary>

**答え: C) OverlayFS**

**解説:**
OverlayFS は、複数のディレクトリを重ね合わせて単一のディレクトリとして提示する union mount file system です。Docker のような container runtime で、image layer を実装するために主に使用されます。これにより、base image を read-only のまま保持しつつ、各コンテナに writable layer を追加できます。
</details>

6. systemctl コマンドで Service を管理する場合、起動時に Service が自動的に開始されるように設定するコマンドはどれですか？
   - A) systemctl start
   - B) systemctl enable
   - C) systemctl restart
   - D) systemctl reload

<details>

<summary>答えを表示</summary>

**答え: B) systemctl enable**

**解説:**
`systemctl enable` は、システム起動時に Service が自動的に開始されるように設定します。`start` は Service を即座に開始し、`restart` は Service を再起動し、`reload` は設定ファイルのみを再読み込みします。Kubernetes nodes では、kubelet や containerd などの中核 Service に対して `systemctl enable` で自動起動を設定しておく必要があります。
</details>

7. Kubernetes cluster のセットアップに不可欠で、コンテナネットワーキングのために IP packet forwarding を有効にする kernel parameter はどれですか？
   - A) net.ipv4.tcp_syncookies
   - B) net.ipv4.ip_forward
   - C) net.core.somaxconn
   - D) fs.file-max

<details>

<summary>答えを表示</summary>

**答え: B) net.ipv4.ip_forward**

**解説:**
`net.ipv4.ip_forward` は、Linux kernel で IP packet forwarding を有効にする設定です。この設定を 1 にすることで、コンテナ間、およびコンテナと外部ネットワーク間の通信が可能になります。このパラメータは Kubernetes nodes を設定するときに有効にする必要があり、`sysctl -w net.ipv4.ip_forward=1` コマンドで設定できます。
</details>

8. systemd unit file で、ある Service が特定の Service の後に開始されるべきことを定義する directive はどれですか？
   - A) Requires
   - B) Wants
   - C) After
   - D) Before

<details>

<summary>答えを表示</summary>

**答え: C) After**

**解説:**
systemd unit files では、`After` は現在の unit が指定された unit の後に開始されるべきことを定義します。たとえば、`After=network-online.target` は、ネットワークの準備ができた後に Service が開始されることを保証します。`Requires` は強い依存関係を定義し、`Wants` は弱い依存関係を定義し、`Before` は現在の unit が別の unit より前に開始されるべきことを示します。
</details>

9. CNI plugins が正しく動作し、bridge traffic が iptables を通過できるようにするために必要な kernel parameter はどれですか？
   - A) net.ipv4.ip_forward
   - B) net.bridge.bridge-nf-call-iptables
   - C) net.core.netdev_max_backlog
   - D) net.ipv4.tcp_max_syn_backlog

<details>

<summary>答えを表示</summary>

**答え: B) net.bridge.bridge-nf-call-iptables**

**解説:**
`net.bridge.bridge-nf-call-iptables` は、ブリッジされたネットワークトラフィックが iptables rules を通過するように設定します。この設定は、Kubernetes CNI plugins (Calico, Flannel, etc.) が NetworkPolicy と Service routing を正しく適用するために不可欠です。この設定を有効にするには、まず `br_netfilter` kernel module をロードする必要があります。
</details>

10. package management において、Ubuntu/Debian で Kubernetes components の自動アップグレードを防ぐために使用するコマンドはどれですか？
    - A) apt lock
    - B) apt-mark hold
    - C) apt freeze
    - D) apt pin

<details>

<summary>答えを表示</summary>

**答え: B) apt-mark hold**

**解説:**
`apt-mark hold` は、特定の package を固定して自動アップグレードを防ぎます。Kubernetes clusters では、kubelet、kubeadm、kubectl のバージョン互換性が重要であるため、`sudo apt-mark hold kubelet kubeadm kubectl` コマンドでバージョンを固定することが推奨されます。RHEL/CentOS では、`yum versionlock` コマンドを使用します。
</details>

## Short Answer Questions

11. 終了したものの、親プロセスがその状態を確認していないプロセスは何と呼ばれますか？

<details>

<summary>答えを表示</summary>

**答え: Zombie Process**

**解説:**
Zombie process は、実行を完了したものの、親プロセスが `wait()` system call によって終了状態を確認していないために process table に残っているプロセスです。Zombie process はほとんどリソースを使用しませんが、多数蓄積すると process table がいっぱいになり、新しいプロセスを作成できなくなる可能性があります。
</details>

12. プロセスの network stack を分離する Linux namespace の名前は何ですか？

<details>

<summary>答えを表示</summary>

**答え: Network Namespace**

**解説:**
network namespace は、network stack（network interfaces、routing tables、firewall rules、sockets など）を分離します。これにより、各コンテナは独自のネットワーク環境を持ち、ホストシステムや他のコンテナのネットワークから独立して動作できます。
</details>

13. プロセスが使用できる system call を制限する Linux security feature の名前は何ですか？

<details>

<summary>答えを表示</summary>

**答え: seccomp (Secure Computing Mode)**

**解説:**
seccomp は、プロセスが使用できる system call を制限する Linux kernel security feature です。Container runtime は seccomp filters を使用して、コンテナが実行できる system call を制限し、それによってセキュリティを強化します。
</details>

14. Linux における従来の root 権限を、より小さな権限単位に分割することを何と呼びますか？

<details>

<summary>答えを表示</summary>

**答え: Capabilities**

**解説:**
Linux Capabilities は、従来の root 権限をより小さな権限単位に分割します。これにより、プロセスに必要最小限の権限だけを付与でき、セキュリティが向上します。たとえば、ネットワーク設定を変更するには、完全な root 権限ではなく `CAP_NET_ADMIN` capability だけが必要です。
</details>

15. コンテナネットワーキングにおいて、ホストとコンテナの間にある network interface pair は何と呼ばれますか？

<details>

<summary>答えを表示</summary>

**答え: veth pair**

**解説:**
veth pair は virtual ethernet interface pair で、一方の端はコンテナ内にあり、もう一方の端は host network namespace 内にあります。これにより、コンテナとホスト間のネットワーク通信が可能になります。通常、ホスト側の veth interface は bridge（例: docker0）に接続され、複数のコンテナ間通信を可能にします。
</details>

16. プロセスが開くことのできる file descriptors の最大数を確認および制限するために使用するコマンドは何ですか？

<details>

<summary>答えを表示</summary>

**答え: ulimit**

**解説:**
ulimit は、ユーザーとプロセスのリソース制限を確認および設定するためのコマンドです。`ulimit -n` は開くことができる file descriptors の数を確認し、`ulimit -n 65536` は制限を変更します。Kubernetes nodes では多くの file handles が必要になるため、`/etc/security/limits.conf` に高い値を永続的に設定するのが一般的です。
</details>

17. Service logs を統合管理するために使用される systemd の logging system tool の名前は何ですか？

<details>

<summary>答えを表示</summary>

**答え: journald (または systemd-journald)**

**解説:**
journald は、system と Service logs を収集して保存する systemd の unified logging system です。Logs は `journalctl` コマンドで照会でき、`-u` オプションで特定の Service logs を表示し、`-f` オプションで real-time logs を表示できます。Kubernetes nodes では、kubelet logs を `journalctl -u kubelet` で確認できます。
</details>

18. system time を NTP servers と同期するために使用される modern daemon の名前は何ですか？

<details>

<summary>答えを表示</summary>

**答え: chronyd (または chrony)**

**解説:**
chronyd は、従来の ntpd よりも高速に時刻を同期する modern NTP client/server です。`chronyc tracking` コマンドで同期状態を確認し、`chronyc sources` で NTP server list を表示します。Kubernetes clusters では、認証や logging などが正しく動作するよう、すべての nodes の時刻が正確に同期されている必要があります。
</details>

19. Linux で DNS name resolution settings が保存されているファイルのパスは何ですか？

<details>

<summary>答えを表示</summary>

**答え: /etc/resolv.conf**

**解説:**
`/etc/resolv.conf` は DNS name resolution settings を保存するファイルで、nameservers、search domains、options などを定義します。Kubernetes environments では、このファイルは CoreDNS とともに重要な役割を果たし、Pod DNS settings にも影響します。Modern systems では、systemd-resolved がこのファイルを動的に管理する場合があります。
</details>

## Hands-on Questions

20. 新しい network namespace を作成し、その namespace 内の network interfaces を一覧表示するコマンドを書いてください。

<details>

<summary>答えを表示</summary>

**答え:**
```bash
# Create a new network namespace
ip netns add mynetns

# List network interfaces within that namespace
ip netns exec mynetns ip link list
```

**解説:**
最初のコマンドは "mynetns" という名前の新しい network namespace を作成します。2 番目のコマンドは、その namespace 内で `ip link list` コマンドを実行して network interfaces を一覧表示します。新しく作成された network namespace には、デフォルトでは loopback interface (lo) のみが含まれ、この interface は初期状態では down state です。
</details>

21. 特定のプロセス (PID: 1234) の cgroup 情報を確認するコマンドを書いてください。

<details>

<summary>答えを表示</summary>

**答え:**
```bash
cat /proc/1234/cgroup
```

**解説:**
Linux では、`/proc/<PID>/cgroup` ファイルを通じて特定のプロセスの cgroup 情報を確認できます。このファイルには、プロセスが属するすべての cgroup hierarchies と controller 情報が表示されます。代わりに、`systemd-cgls` コマンドを使用して cgroup hierarchy を tree format で表示することもできます。
</details>

22. ファイル "example.sh" に対して、owner には読み取り、書き込み、実行権限を、group には読み取りと実行権限を、other users には読み取り専用権限を付与する chmod コマンドを書いてください。

<details>

<summary>答えを表示</summary>

**答え:**
```bash
chmod 754 example.sh
```

または

```bash
chmod u=rwx,g=rx,o=r example.sh
```

**解説:**
最初の方法は numeric notation を使用します:
  - 7(rwx): owner に読み取り(4)、書き込み(2)、実行(1) 権限を付与
  - 5(r-x): group に読み取り(4) と実行(1) 権限を付与
  - 4(r--): other users に読み取り(4) 権限のみを付与

2 番目の方法は symbolic notation を使用して同じ権限を設定します。
</details>

23. システムの現在の memory usage を確認するコマンドを書いてください。

<details>

<summary>答えを表示</summary>

**答え:**
```bash
free -h
```

**解説:**
`free` コマンドはシステムの memory usage を表示します。`-h` オプションは人間が読みやすい形式（例: GB、MB）で出力します。出力には、total memory、used memory、free memory、buffers/cache に使用される memory、swap memory 情報などが含まれます。
</details>

24. 特定の port（例: 8080）で実行されているプロセスを見つけるコマンドを書いてください。

<details>

<summary>答えを表示</summary>

**答え:**
```bash
lsof -i :8080
```

または

```bash
netstat -tulpn | grep :8080
```

または

```bash
ss -tulpn | grep :8080
```

**解説:**
  - `lsof -i :8080`: port 8080 を使用しているプロセスを表示します。
  - `netstat -tulpn | grep :8080`: TCP/UDP connection list から port 8080 を使用している entries を見つけます。オプション `-t`(TCP)、`-u`(UDP)、`-l`(listening)、`-p`(process info)、`-n`(show numerically) を使用します。
  - `ss -tulpn | grep :8080`: `netstat` の現代的な代替コマンドで、同じ情報を提供します。
</details>

25. Kubernetes nodes に必要な kernel modules br_netfilter と overlay を、起動時に自動的にロードするよう設定するコマンドを書いてください。

<details>

<summary>答えを表示</summary>

**答え:**
```bash
cat <<EOF | sudo tee /etc/modules-load.d/kubernetes.conf
overlay
br_netfilter
EOF

# Load immediately in current session
sudo modprobe overlay
sudo modprobe br_netfilter
```

**解説:**
`/etc/modules-load.d/` ディレクトリに `.conf` ファイルを作成すると、systemd-modules-load Service が起動時にそれらの modules を自動的にロードします。`overlay` module は container image layers に使用される OverlayFS file system をサポートし、`br_netfilter` module は bridge traffic が iptables を通過できるようにします。これは Kubernetes networking に不可欠です。
</details>

26. kubelet Service の real-time logs を表示しながら、error level 以上のメッセージのみにフィルタリングする journalctl コマンドを書いてください。

<details>

<summary>答えを表示</summary>

**答え:**
```bash
journalctl -u kubelet -f -p err
```

または

```bash
journalctl -u kubelet -f -p warning
```

**解説:**
  - `-u kubelet`: kubelet Service logs のみを表示
  - `-f`: 新しい logs を real-time でストリーム表示（tail -f に類似）
  - `-p err`: error level 以上の logs のみを表示（err、crit、alert、emerg）
  - `-p warning`: warning level 以上の logs を表示（warning、err、crit、alert、emerg）

journalctl priority levels は 0(emerg) から 7(debug) まであり、指定された level およびそれより高い priority の messages が表示されます。
</details>

27. システムの現在の timezone を確認し、Asia/Seoul に変更するコマンドを書いてください。

<details>

<summary>答えを表示</summary>

**答え:**
```bash
# Check current timezone
timedatectl

# Change timezone
sudo timedatectl set-timezone Asia/Seoul
```

**解説:**
`timedatectl` コマンドは、システムの time、date、timezone を設定および確認できる systemd の time management utility です。`timedatectl list-timezones` コマンドは利用可能な timezones を表示します。Kubernetes clusters では、すべての nodes が同じ timezone を使用するか UTC を使用していると、log analysis と troubleshooting に役立ちます。
</details>

28. file descriptor limit を 65536 に永続的に設定するために /etc/security/limits.conf に追加する configuration を書いてください。

<details>

<summary>答えを表示</summary>

**答え:**
```bash
*               soft    nofile          65536
*               hard    nofile          65536
```

または特定のユーザー/Service の場合:
```bash
root            soft    nofile          65536
root            hard    nofile          65536
```

**解説:**
`/etc/security/limits.conf` は、PAM (Pluggable Authentication Modules) が user ごとの resource limits を定義するために使用する configuration file です。`*` はすべての users、`soft` はデフォルト制限、`hard` は最大制限を意味します。`nofile` は開くことができる file descriptors の数を指定します。Kubernetes nodes では、多くの network connections と file handles が必要になるため、この値は高く設定する必要があります。
</details>

## Advanced Questions

29. コンテナ分離のために Linux kernel が使用する 3 つの主要技術を説明し、それぞれがどのような分離を提供するかを述べてください。

<details>

<summary>答えを表示</summary>

**答え:**

1. **Namespaces**:
  - Namespaces は、各グループが system resources を独立して見られるように process groups を分離します。
  - 主な namespace types:
  - PID namespace: Process ID isolation
  - Network namespace: Network stack isolation (interfaces, routing tables, firewall, etc.)
  - Mount namespace: File system mount point isolation
  - UTS namespace: Hostname and domain name isolation
  - IPC namespace: Inter-process communication resource isolation
  - User namespace: User and group ID isolation
  - cgroup namespace: cgroup root directory isolation

2. **cgroups (Control Groups)**:
  - cgroups は、process groups の resource usage を制限し分離する機能です。
  - 提供される分離:
  - CPU time limiting
  - Memory usage limiting
  - Block I/O bandwidth limiting
  - Network bandwidth limiting
  - Device access control

3. **Capabilities**:
  - Linux capabilities は、従来の root 権限をより小さな権限単位に分割します。
  - 提供される分離:
  - 権限の分離: コンテナに必要最小限の権限のみを付与
  - セキュリティ強化: 不要な権限を削除してセキュリティリスクを低減
  - 例: `CAP_NET_ADMIN` (ネットワーク設定の変更), `CAP_SYS_ADMIN` (システム管理タスク), etc.

これら 3 つの技術が組み合わさることで、コンテナはホストシステムや他のコンテナから分離された環境で実行でき、リソース使用量が制限され、セキュリティが強化されます。
</details>

30. OverlayFS が container image layers をどのように管理するかを説明し、read-only layers と writable layers の関係を述べてください。

<details>

<summary>答えを表示</summary>

**答え:**

OverlayFS は、複数のディレクトリを重ね合わせて単一のディレクトリとして提示する union mount file system です。container image layer management では、OverlayFS は次のように動作します:

1. **レイヤー構造**:
  - **Lower directory (read-only layers)**: base image layers。複数存在できます。base file system と application code を含みます。
  - **Upper directory (writable layer)**: コンテナ実行時に作成される writable layer。コンテナ内で行われたすべての変更はこの layer に保存されます。
  - **Work directory**: OverlayFS の internal operations 用の temporary directory。
  - **Merged directory**: すべての layers が統合された最終ビュー。コンテナが実際に見る file system。

2. **read-only layers と writable layers の関係**:
  - **ファイル読み取り**: ファイルを読み取るとき、OverlayFS はまず Upper directory (writable layer) 内でファイルを探します。見つからない場合、Lower directory (read-only layers) を順番に検索します。
  - **ファイル書き込み**: ファイルを変更するときは、Copy-on-Write (CoW) が使用されます。read-only layer 内のファイルを変更しようとすると、まずファイルが writable layer にコピーされ、その後変更されます。元のファイルは変更されません。
  - **ファイル削除**: read-only layer 内のファイルを削除しようとすると、ファイルは実際には削除されません。代わりに、削除されたように見せるために writable layer に "whiteout" file が作成されます。

3. **利点**:
  - **容量効率**: 複数のコンテナが同じ base image layers を共有するため、disk space を節約できます。
  - **高速な起動時間**: 新しいコンテナを起動するとき、file system 全体をコピーする必要はなく、writable layer だけを作成すればよいです。
  - **Image version management（イメージバージョン管理）**: base image に新しい layers を追加することで image を更新できます。

このように、OverlayFS は container image layers を効率的に管理し、base images を共有しながら、コンテナが独立した file systems を持てるようにします。
</details>

31. Linux capabilities が container security にどのように影響するか、またコンテナに必要最小限の capabilities のみを付与することがなぜ重要かを説明してください。

<details>

<summary>答えを表示</summary>

**答え:**

**Linux Capabilities と Container Security:**

Linux capabilities は、従来の root 権限をより小さな権限単位に分割し、container security に次のように影響します:

1. **権限の粒度**:
  - 従来、プロセスは root (UID 0) か non-root かだけで区別されていました。
  - Capabilities により root 権限を複数の個別権限に分割でき、プロセスに特定の必要な権限だけを付与できます。
  - 例: ネットワーク設定を変更するには、完全な root 権限ではなく `CAP_NET_ADMIN` capability だけが必要です。

2. **Container Security の強化**:
  - Container runtimes はデフォルトで、制限された capabilities のセットだけをコンテナに付与します。
  - これにより、コンテナがホストシステムに与えられる影響が制限されます。
  - コンテナ内で root として実行されているプロセスであっても capabilities は制限されるため、セキュリティリスクが低減されます。

3. **コンテナ関連の主要な Capabilities**:
  - `CAP_NET_ADMIN`: ネットワーク設定の変更
  - `CAP_SYS_ADMIN`: システム管理タスク（非常に強力）
  - `CAP_CHOWN`: ファイル所有者の変更
  - `CAP_DAC_OVERRIDE`: ファイル権限のバイパス
  - `CAP_SETUID`: UID の変更
  - `CAP_SETGID`: GID の変更

**最小権限の原則の重要性:**

次の理由から、コンテナには必要最小限の capabilities のみを付与することが重要です:

1. **Attack Surface の削減**:
  - 不要な capabilities を削除すると、攻撃者が悪用できる vectors が減少します。
  - コンテナが侵害された場合でも、攻撃者が実行できる actions は制限されます。

2. **Container Escape Prevention（コンテナエスケープ防止）**:
  - 強力な capabilities（特に `CAP_SYS_ADMIN`）は container escape（コンテナからホストへアクセスすること）を可能にする場合があります。
  - これらの capabilities を制限すると、container escape risk が大幅に低減されます。

3. **Defense in Depth Strategy（多層防御戦略）**:
  - least privilege principle は defense in depth security strategy の一部です。
  - 他の security mechanisms（seccomp、AppArmor、SELinux など）と併用することで、より強固なセキュリティを提供します。

4. **Regulatory Compliance（規制遵守）**:
  - 多くの security standards と regulations は least privilege principle を要求します。
  - コンテナに必要最小限の capabilities のみを付与することは、これらの要件を満たすのに役立ちます。

5. **Problem Isolation（問題の分離）**:
  - コンテナに制限された capabilities を付与することで、あるコンテナの問題が他のコンテナやホストシステムへ広がるのを防げます。

本番環境では、コンテナが必要とする capabilities を正確に特定し、その他すべての capabilities を削除することが優れたセキュリティプラクティスです。これには Docker の `--cap-drop`、`--cap-add` options、または Kubernetes の `securityContext.capabilities` field を使用できます。
</details>

32. systemd service unit file の構造と主な sections ([Unit], [Service], [Install]) の役割を説明し、Kubernetes kubelet Service の基本的な unit file 例を書いてください。

<details>

<summary>答えを表示</summary>

**答え:**

**systemd unit file の主な sections:**

1. **[Unit] Section**: unit のメタデータと依存関係を定義します
   - `Description`: Service の説明
   - `Documentation`: ドキュメント URL
   - `After/Before`: 起動順序を定義
   - `Requires/Wants`: 依存関係を定義

2. **[Service] Section**: Service の実行方法を定義します
   - `Type`: Service type (simple, forking, oneshot, etc.)
   - `ExecStart`: 実行するコマンド
   - `Restart`: 再起動ポリシー
   - `RestartSec`: 再起動までの待機時間

3. **[Install] Section**: unit が enabled になったときの動作を定義します
   - `WantedBy`: この unit を要求する target

**kubelet service unit file の例:**

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

**解説:**
この unit file は kubelet Service を定義します。ネットワークの準備ができた後に開始され（`After=network-online.target`）、失敗時には常に再起動し（`Restart=always`）、10 秒ごとに再起動を試みます（`RestartSec=10`）。`WantedBy=multi-user.target` は、この Service がシステムの multi-user mode 起動時に開始されることを意味します。
</details>

33. Kubernetes node configuration に必要な sysctl kernel parameters を永続的に設定する方法を説明し、各 parameter の役割を述べてください。

<details>

<summary>答えを表示</summary>

**答え:**

**Kubernetes に必要な主要 sysctl settings とその役割:**

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

**各 parameter の役割:**

1. **net.ipv4.ip_forward = 1**
   - Linux kernel が network interfaces 間で packets を forward できるようにします
   - Pods から他の Pods または外部ネットワークへの通信に不可欠です
   - 無効になっていると container networking は動作しません

2. **net.bridge.bridge-nf-call-iptables = 1**
   - bridges を通過する traffic が iptables rules の対象になるように設定します
   - Kubernetes Services (ClusterIP, NodePort) と NetworkPolicy が正しく動作するために不可欠です
   - kube-proxy が Service routing に iptables を使用するため必要です

3. **net.ipv6.conf.all.forwarding = 1**
   - IPv6 environments で packet forwarding を有効にします
   - dual-stack clusters に必要です

**設定適用の順序:**
1. まず `br_netfilter` module をロードします: `modprobe br_netfilter`
2. sysctl configuration file を作成します
3. `sysctl --system` ですべての settings を適用します

これらの settings がないと、Kubernetes cluster networking は適切に機能せず、特に Pod-to-Pod communication や Service discovery で問題が発生します。
</details>

34. journald と logrotate を使用した Linux log management strategy を説明し、Kubernetes nodes で効率的に log management を行うための configuration methods を提示してください。

<details>

<summary>答えを表示</summary>

**答え:**

**journald と logrotate の役割:**

**journald (systemd-based logging):**
- systemd services から stdout/stderr logs を収集します
- binary format で保存され、journalctl で照会します
- automatic log compression と rotation をサポートします

**logrotate (traditional log file management):**
- text log files の rotation、compression、deletion を管理します
- cron job 経由で定期的に実行されます

**Kubernetes Node Log Management Configuration（ログ管理設定）:**

**1. journald configuration (/etc/systemd/journald.conf):**
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

**2. logrotate configuration for container logs:**
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

**3. Log cleanup commands（ログクリーンアップコマンド）:**
```bash
# journald log cleanup
journalctl --vacuum-time=7d   # Delete logs older than 7 days
journalctl --vacuum-size=1G   # Delete old logs when exceeding 1GB

# Check disk usage
journalctl --disk-usage
```

**Kubernetes Log Management Best Practices（ベストプラクティス）:**

1. **kubelet logs**: journald によって管理され、`/var/log/journal/` に保存されます
2. **Container logs**: `/var/log/containers/` に保存され、logrotate によって管理されます
3. **Centralized logging**: Fluentd/Fluent Bit を使用して外部システムへ転送することが推奨されます

適切な log management により、disk space 不足による node failures を防ぎつつ、troubleshooting のための logs を保持するバランスを維持できます。
</details>

---

[学習資料に戻る](../../basics/01-linux-basics.md) | [次のクイズ: Linux Operations](./02-linux-advanced-quiz.md)
