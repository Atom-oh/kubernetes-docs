# Linux の基礎クイズ

このクイズでは、Kubernetes とコンテナ技術の基盤となる Linux の基本概念についての理解を確認します。

## 選択問題

1. 次のうち、Linux カーネルの主要な役割ではないものはどれですか？
   - A) プロセス管理
   - B) メモリ管理
   - C) ユーザーインターフェースの提供
   - D) デバイス管理
<details>

<summary>答えを表示</summary>

**回答: C) ユーザーインターフェースの提供**

**解説:**
Linux カーネルはオペレーティングシステムの中核であり、ハードウェアとソフトウェアの仲介役として機能します。カーネルの主要な役割には、プロセス管理、メモリ管理、デバイス管理、システムコールインターフェースの提供が含まれます。ユーザーインターフェース（GUI、CLI）はユーザー空間で動作する別のプログラムによって提供されるものであり、カーネルの責務ではありません。

</details>

2. 次のうち、Linux namespace の種類ではないものはどれですか？
   - A) PID namespace
   - B) Network namespace
   - C) Memory namespace
   - D) User namespace
<details>

<summary>答えを表示</summary>

**回答: C) Memory namespace**

**解説:**
Linux には、PID（Process ID）、Network、Mount、UTS（hostname）、IPC（Inter-Process Communication）、User、cgroup namespace があります。Memory namespace は存在しません。メモリの分離は主に cgroups によって管理されます。

</details>

3. cgroups（Control Groups）の主な機能は何ですか？
   - A) プロセスグループのリソース使用量を制限し分離する
   - B) ファイルシステムアクセスを制御する
   - C) ネットワークパケットをフィルタリングする
   - D) ユーザー認証を管理する
   
<details>

<summary>答えを表示</summary>

**回答: A) プロセスグループのリソース使用量を制限し分離する**

**解説:**
cgroups は、プロセスグループのリソース使用量を制限し分離する Linux カーネル機能です。CPU 時間、メモリ、ブロック I/O、ネットワーク帯域幅などのリソース使用量を制限・監視できます。これはコンテナでリソース制限を実装するための中核技術です。
</details>

4. ファイル権限 "rwxr-xr--" において、グループユーザーの権限はどれですか？
   - A) 読み取り、書き込み、実行
   - B) 読み取り、実行
   - C) 読み取りのみ
   - D) 実行のみ
   
<details>

<summary>答えを表示</summary>

**回答: B) 読み取り、実行**

**解説:**
ファイル権限 "rwxr-xr--" では:
  - 最初の 3 文字 (rwx): 所有者の権限 - 読み取り、書き込み、実行
  - 中央の 3 文字 (r-x): グループの権限 - 読み取り、実行
  - 最後の 3 文字 (r--): その他のユーザーの権限 - 読み取りのみ

したがって、グループユーザーには読み取りと実行の権限があります。

</details>

5. コンテナイメージレイヤーを実装するために主に使用されるファイルシステムはどれですか？
   - A) ext4
   - B) XFS
   - C) OverlayFS
   - D) Btrfs

<details>

<summary>答えを表示</summary>

**回答: C) OverlayFS**

**解説:**
OverlayFS は、複数のディレクトリを重ね合わせて 1 つのディレクトリとして見せる union mount ファイルシステムです。Docker のようなコンテナランタイムで、イメージレイヤーを実装するために主に使用されます。これにより、ベースイメージを読み取り専用のまま維持しつつ、各コンテナに書き込み可能なレイヤーを追加できます。
</details>

6. systemctl コマンドでサービスを管理する場合、起動時にサービスを自動起動するよう設定するコマンドはどれですか？
   - A) systemctl start
   - B) systemctl enable
   - C) systemctl restart
   - D) systemctl reload

<details>

<summary>答えを表示</summary>

**回答: B) systemctl enable**

**解説:**
`systemctl enable` は、システム起動時にサービスが自動的に開始されるよう設定します。`start` はサービスを即時開始し、`restart` はサービスを再起動し、`reload` は設定ファイルを再読み込みするだけです。Kubernetes ノードでは、kubelet や containerd のような中核サービスに対して `systemctl enable` で自動起動を設定しておく必要があります。
</details>

7. Kubernetes クラスターのセットアップで、コンテナネットワーキングのために IP パケット転送を有効化する必須のカーネルパラメータはどれですか？
   - A) net.ipv4.tcp_syncookies
   - B) net.ipv4.ip_forward
   - C) net.core.somaxconn
   - D) fs.file-max

<details>

<summary>答えを表示</summary>

**回答: B) net.ipv4.ip_forward**

**解説:**
`net.ipv4.ip_forward` は、Linux カーネルで IP パケット転送を有効化する設定です。コンテナ間、およびコンテナと外部ネットワーク間の通信を可能にするには、この設定を 1 にする必要があります。このパラメータは Kubernetes ノードをセットアップするときに有効化する必要があり、`sysctl -w net.ipv4.ip_forward=1` コマンドで設定できます。
</details>

8. systemd unit ファイルで、特定のサービスの後にサービスを開始すべきことを定義するために使用するディレクティブはどれですか？
   - A) Requires
   - B) Wants
   - C) After
   - D) Before

<details>

<summary>答えを表示</summary>

**回答: C) After**

**解説:**
systemd unit ファイルでは、`After` は現在の unit が指定された unit の後に開始されるべきことを定義します。たとえば、`After=network-online.target` は、ネットワークの準備が整った後にサービスが開始されることを保証します。`Requires` は強い依存関係を定義し、`Wants` は弱い依存関係を定義し、`Before` は現在の unit が別の unit より前に開始されるべきことを示します。
</details>

9. CNI プラグインが適切に動作するために必要で、ブリッジトラフィックが iptables を通過できるようにするカーネルパラメータはどれですか？
   - A) net.ipv4.ip_forward
   - B) net.bridge.bridge-nf-call-iptables
   - C) net.core.netdev_max_backlog
   - D) net.ipv4.tcp_max_syn_backlog

<details>

<summary>答えを表示</summary>

**回答: B) net.bridge.bridge-nf-call-iptables**

**解説:**
`net.bridge.bridge-nf-call-iptables` は、ブリッジされたネットワークトラフィックが iptables ルールを通過するよう設定します。この設定は、Kubernetes CNI プラグイン（Calico、Flannel など）がネットワークポリシーと Service ルーティングを正しく適用するために不可欠です。この設定を有効にするには、まず `br_netfilter` カーネルモジュールをロードする必要があります。
</details>

10. パッケージ管理において、Ubuntu/Debian で Kubernetes コンポーネントの自動アップグレードを防ぐために使用するコマンドはどれですか？
    - A) apt lock
    - B) apt-mark hold
    - C) apt freeze
    - D) apt pin

<details>

<summary>答えを表示</summary>

**回答: B) apt-mark hold**

**解説:**
`apt-mark hold` は、特定のパッケージを固定して自動アップグレードを防ぎます。Kubernetes クラスターでは kubelet、kubeadm、kubectl のバージョン互換性が重要であるため、`sudo apt-mark hold kubelet kubeadm kubectl` コマンドでバージョンを固定することが推奨されます。RHEL/CentOS では `yum versionlock` コマンドを使用します。
</details>

## 短答問題

11. 終了したものの、親プロセスがその状態を確認していないプロセスは何と呼ばれますか？

<details>

<summary>答えを表示</summary>

**回答: ゾンビプロセス**

**解説:**
ゾンビプロセスとは、実行を完了したものの、親プロセスが `wait()` システムコールを通じて終了ステータスを確認していないため、プロセステーブルに残っているプロセスです。ゾンビプロセスはほとんどリソースを使用しませんが、多数蓄積するとプロセステーブルが満杯になり、新しいプロセスの作成を妨げる可能性があります。
</details>

12. プロセスのネットワークスタックを分離する Linux namespace の名前は何ですか？

<details>

<summary>答えを表示</summary>

**回答: Network Namespace**

**解説:**
network namespace は、ネットワークスタック（ネットワークインターフェース、ルーティングテーブル、ファイアウォールルール、ソケットなど）を分離します。これにより、各コンテナが独自のネットワーク環境を持ち、ホストシステムや他のコンテナのネットワークから独立して動作できます。
</details>

13. プロセスが使用できるシステムコールを制限する Linux のセキュリティ機能の名前は何ですか？

<details>

<summary>答えを表示</summary>

**回答: seccomp (Secure Computing Mode)**

**解説:**
seccomp は、プロセスが使用できるシステムコールを制限する Linux カーネルのセキュリティ機能です。コンテナランタイムは seccomp フィルターを使用してコンテナが実行できるシステムコールを制限し、それによってセキュリティを強化します。
</details>

14. Linux における従来の root 権限を、より小さな権限単位に分割したものは何と呼ばれますか？

<details>

<summary>答えを表示</summary>

**回答: Capabilities**

**解説:**
Linux Capabilities は、従来の root 権限をより小さな権限単位に分割します。これにより、プロセスに必要最小限の権限だけを付与でき、セキュリティが向上します。たとえばネットワーク設定を変更するには、完全な root 権限ではなく `CAP_NET_ADMIN` capability だけが必要です。
</details>

15. コンテナネットワーキングにおいて、ホストとコンテナ間のネットワークインターフェースペアは何と呼ばれますか？

<details>

<summary>答えを表示</summary>

**回答: veth pair**

**解説:**
veth pair は仮想イーサネットインターフェースのペアで、一方の端はコンテナ内にあり、もう一方の端はホストの network namespace 内にあります。これにより、コンテナとホスト間のネットワーク通信が可能になります。通常、ホスト側の veth インターフェースはブリッジ（例: docker0）に接続され、複数のコンテナ間の通信を可能にします。
</details>

16. プロセスが開けるファイルディスクリプターの最大数を確認し、制限するために使用するコマンドは何ですか？

<details>

<summary>答えを表示</summary>

**回答: ulimit**

**解説:**
ulimit は、ユーザーとプロセスのリソース制限を確認・設定するコマンドです。`ulimit -n` は開けるファイルディスクリプター数を確認し、`ulimit -n 65536` はその制限を変更します。Kubernetes ノードでは多数のファイルハンドルが必要になるため、`/etc/security/limits.conf` に高い値を恒久的に設定するのが一般的です。
</details>

17. サービスログを一元管理するために使用される systemd のログシステムツールの名前は何ですか？

<details>

<summary>答えを表示</summary>

**回答: journald（または systemd-journald）**

**解説:**
journald は、システムログとサービスログを収集・保存する systemd の統合ログシステムです。ログは `journalctl` コマンドで照会でき、`-u` オプションで特定のサービスログを表示し、`-f` オプションでリアルタイムログを表示できます。Kubernetes ノードでは、kubelet ログを `journalctl -u kubelet` で確認できます。
</details>

18. NTP サーバーとシステム時刻を同期するために使用される現代的なデーモンの名前は何ですか？

<details>

<summary>答えを表示</summary>

**回答: chronyd（または chrony）**

**解説:**
chronyd は、従来の ntpd より高速に時刻を同期する現代的な NTP クライアント/サーバーです。`chronyc tracking` コマンドで同期状態を確認し、`chronyc sources` で NTP サーバー一覧を表示します。Kubernetes クラスターでは、認証やログなどを正しく機能させるため、すべてのノードで時刻が正確に同期されている必要があります。
</details>

19. Linux で DNS 名前解決設定が保存されるファイルのパスは何ですか？

<details>

<summary>答えを表示</summary>

**回答: /etc/resolv.conf**

**解説:**
`/etc/resolv.conf` は、DNS 名前解決設定を保存するファイルで、ネームサーバー、検索ドメイン、オプションなどを定義します。Kubernetes 環境では、このファイルは CoreDNS とともに重要な役割を果たし、Pod DNS 設定にも影響します。現代的なシステムでは、systemd-resolved がこのファイルを動的に管理する場合があります。
</details>

## ハンズオン問題

20. 新しい network namespace を作成し、その namespace 内のネットワークインターフェースを一覧表示するコマンドを書いてください。

<details>

<summary>答えを表示</summary>

**回答:**
```bash
# Create a new network namespace
ip netns add mynetns

# List network interfaces within that namespace
ip netns exec mynetns ip link list
```

**解説:**
最初のコマンドは "mynetns" という名前の新しい network namespace を作成します。2 番目のコマンドは、その namespace 内で `ip link list` コマンドを実行し、ネットワークインターフェースを一覧表示します。新しく作成された network namespace には、デフォルトでは loopback インターフェース（lo）のみが含まれ、このインターフェースは初期状態では down 状態です。
</details>

21. 特定のプロセス（PID: 1234）の cgroup 情報を確認するコマンドを書いてください。

<details>

<summary>答えを表示</summary>

**回答:**
```bash
cat /proc/1234/cgroup
```

**解説:**
Linux では、`/proc/<PID>/cgroup` ファイルを通じて特定のプロセスの cgroup 情報を確認できます。このファイルには、そのプロセスが属するすべての cgroup 階層とコントローラー情報が表示されます。代わりに、`systemd-cgls` コマンドを使用して cgroup 階層をツリー形式で表示することもできます。
</details>

22. ファイル "example.sh" に対して、所有者には読み取り・書き込み・実行権限、グループには読み取り・実行権限、その他のユーザーには読み取り専用権限を付与する chmod コマンドを書いてください。

<details>

<summary>答えを表示</summary>

**回答:**
```bash
chmod 754 example.sh
```

または

```bash
chmod u=rwx,g=rx,o=r example.sh
```

**解説:**
最初の方法は数値表記を使用します:
  - 7(rwx): 所有者に読み取り(4)、書き込み(2)、実行(1) 権限を付与
  - 5(r-x): グループに読み取り(4) と実行(1) 権限を付与
  - 4(r--): その他のユーザーに読み取り(4) 権限のみを付与

2 番目の方法はシンボリック表記を使用して同じ権限を設定します。
</details>

23. システムの現在のメモリ使用量を確認するコマンドを書いてください。

<details>

<summary>答えを表示</summary>

**回答:**
```bash
free -h
```

**解説:**
`free` コマンドはシステムのメモリ使用量を表示します。`-h` オプションは、人間が読みやすい形式（例: GB、MB）で出力します。出力には、総メモリ、使用中メモリ、空きメモリ、バッファ/キャッシュに使用されているメモリ、スワップメモリ情報などが含まれます。
</details>

24. 特定のポート（例: 8080）で実行中のプロセスを見つけるコマンドを書いてください。

<details>

<summary>答えを表示</summary>

**回答:**
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
  - `lsof -i :8080`: ポート 8080 を使用しているプロセスを表示します。
  - `netstat -tulpn | grep :8080`: TCP/UDP 接続一覧からポート 8080 を使用しているエントリを見つけます。オプション `-t`(TCP)、`-u`(UDP)、`-l`(リスニング)、`-p`(プロセス情報)、`-n`(数値で表示) を使用します。
  - `ss -tulpn | grep :8080`: `netstat` の現代的な代替で、同じ情報を提供します。
</details>

25. Kubernetes ノードに必要なカーネルモジュール br_netfilter と overlay を、起動時に自動的にロードするよう設定するコマンドを書いてください。

<details>

<summary>答えを表示</summary>

**回答:**
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
`/etc/modules-load.d/` ディレクトリに `.conf` ファイルを作成すると、systemd-modules-load サービスが起動時にそれらのモジュールを自動的にロードします。`overlay` モジュールはコンテナイメージレイヤーで使用される OverlayFS ファイルシステムをサポートし、`br_netfilter` モジュールはブリッジトラフィックが iptables を通過できるようにします。これは Kubernetes ネットワーキングに不可欠です。
</details>

26. エラーレベル以上のメッセージだけをフィルタリングしながら、kubelet サービスのリアルタイムログを表示する journalctl コマンドを書いてください。

<details>

<summary>答えを表示</summary>

**回答:**
```bash
journalctl -u kubelet -f -p err
```

または

```bash
journalctl -u kubelet -f -p warning
```

**解説:**
  - `-u kubelet`: kubelet サービスのログのみを表示
  - `-f`: 新しいログをリアルタイムでストリーミング（tail -f と同様）
  - `-p err`: エラーレベル以上のログのみを表示（err、crit、alert、emerg）
  - `-p warning`: 警告レベル以上のログを表示（warning、err、crit、alert、emerg）

journalctl の優先度レベルは 0(emerg) から 7(debug) まであり、指定されたレベル以上の優先度のメッセージが表示されます。
</details>

27. システムの現在のタイムゾーンを確認し、Asia/Seoul に変更するコマンドを書いてください。

<details>

<summary>答えを表示</summary>

**回答:**
```bash
# Check current timezone
timedatectl

# Change timezone
sudo timedatectl set-timezone Asia/Seoul
```

**解説:**
`timedatectl` コマンドは、システムの時刻、日付、タイムゾーンを設定・確認できる systemd の時刻管理ユーティリティです。`timedatectl list-timezones` コマンドは利用可能なタイムゾーンを表示します。Kubernetes クラスターでは、すべてのノードが同じタイムゾーンを使用するか UTC を使用していると、ログ分析やトラブルシューティングに役立ちます。
</details>

28. ファイルディスクリプター制限を 65536 に恒久的に設定するために、/etc/security/limits.conf に追加する設定を書いてください。

<details>

<summary>答えを表示</summary>

**回答:**
```bash
*               soft    nofile          65536
*               hard    nofile          65536
```

または特定のユーザー/サービス向け:
```bash
root            soft    nofile          65536
root            hard    nofile          65536
```

**解説:**
`/etc/security/limits.conf` は、PAM（Pluggable Authentication Modules）がユーザーごとのリソース制限を定義するために使用する設定ファイルです。`*` はすべてのユーザーを意味し、`soft` はデフォルトの制限、`hard` は最大制限です。`nofile` は開けるファイルディスクリプター数を指定します。Kubernetes ノードでは多くのネットワーク接続とファイルハンドルが必要になるため、この値は高く設定すべきです。
</details>

## 応用問題

29. コンテナ分離のために Linux カーネルで使用される 3 つの主要技術を説明し、それぞれがどのような分離を提供するかを述べてください。

<details>

<summary>答えを表示</summary>

**回答:**

1. **Namespaces**:
  - Namespaces は、各グループがシステムリソースを独立して見られるように、プロセスグループを分離します。
  - 主な namespace の種類:
  - PID namespace: Process ID の分離
  - Network namespace: ネットワークスタックの分離（インターフェース、ルーティングテーブル、ファイアウォールなど）
  - Mount namespace: ファイルシステムマウントポイントの分離
  - UTS namespace: ホスト名とドメイン名の分離
  - IPC namespace: プロセス間通信リソースの分離
  - User namespace: ユーザー ID とグループ ID の分離
  - cgroup namespace: cgroup ルートディレクトリの分離

2. **cgroups (Control Groups)**:
  - cgroups は、プロセスグループのリソース使用量を制限し分離する機能です。
  - 提供される分離:
  - CPU 時間の制限
  - メモリ使用量の制限
  - ブロック I/O 帯域幅の制限
  - ネットワーク帯域幅の制限
  - デバイスアクセス制御

3. **Capabilities**:
  - Linux capabilities は、従来の root 権限をより小さな権限単位に分割します。
  - 提供される分離:
  - 権限の分離: コンテナに必要最小限の権限のみを付与
  - セキュリティ強化: 不要な権限を削除することでセキュリティリスクを低減
  - 例: `CAP_NET_ADMIN`（ネットワーク設定変更）、`CAP_SYS_ADMIN`（システム管理タスク）など

これら 3 つの技術を組み合わせることで、コンテナはホストシステムや他のコンテナから分離された環境で、リソース使用量を制限し、セキュリティを強化して実行できます。
</details>

30. OverlayFS がコンテナイメージレイヤーをどのように管理するかを説明し、読み取り専用レイヤーと書き込み可能レイヤーの関係を述べてください。

<details>

<summary>答えを表示</summary>

**回答:**

OverlayFS は、複数のディレクトリを重ね合わせて 1 つのディレクトリとして見せる union mount ファイルシステムです。コンテナイメージレイヤー管理では、OverlayFS は次のように動作します:

1. **レイヤー構造**:
  - **Lower directory (read-only layers)**: ベースイメージレイヤー。複数存在できます。ベースファイルシステムとアプリケーションコードを含みます。
  - **Upper directory (writable layer)**: コンテナ実行時に作成される書き込み可能レイヤー。コンテナ内で行われたすべての変更はこのレイヤーに保存されます。
  - **Work directory**: OverlayFS の内部操作のための一時ディレクトリ。
  - **Merged directory**: すべてのレイヤーが統合された最終的なビュー。コンテナが実際に見るファイルシステムです。

2. **読み取り専用レイヤーと書き込み可能レイヤーの関係**:
  - **ファイル読み取り**: ファイルを読み取るとき、OverlayFS はまず Upper directory（書き込み可能レイヤー）内でファイルを探します。見つからない場合は、Lower directory（読み取り専用レイヤー）を順番に検索します。
  - **ファイル書き込み**: ファイルを変更するときは、Copy-on-Write（CoW）が使用されます。読み取り専用レイヤー内のファイルを変更しようとすると、まずそのファイルが書き込み可能レイヤーにコピーされ、その後変更されます。元のファイルは変更されません。
  - **ファイル削除**: 読み取り専用レイヤー内のファイルを削除しようとしても、そのファイルは実際には削除されません。代わりに、削除されたように見せるための "whiteout" ファイルが書き込み可能レイヤーに作成されます。

3. **利点**:
  - **容量効率**: 複数のコンテナが同じベースイメージレイヤーを共有するため、ディスク容量を節約できます。
  - **高速な起動時間**: 新しいコンテナを開始するとき、ファイルシステム全体をコピーするのではなく、書き込み可能レイヤーだけを作成すればよいです。
  - **イメージバージョン管理**: ベースイメージに新しいレイヤーを追加することで、イメージを更新できます。

このように、OverlayFS はコンテナイメージレイヤーを効率的に管理し、ベースイメージを共有しながら各コンテナが独立したファイルシステムを持てるようにします。
</details>

31. Linux capabilities がコンテナセキュリティにどのように影響するか、またコンテナに必要最小限の capabilities のみを付与することがなぜ重要なのかを説明してください。

<details>

<summary>答えを表示</summary>

**回答:**

**Linux Capabilities とコンテナセキュリティ:**

Linux capabilities は、従来の root 権限をより小さな権限単位に分割し、次のようにコンテナセキュリティに影響します:

1. **権限の粒度**:
  - 従来、プロセスは root（UID 0）か非 root かだけで区別されていました。
  - Capabilities により、root 権限を複数の個別権限に分割でき、プロセスには必要な特定の権限だけを付与できます。
  - 例: ネットワーク設定を変更するには、完全な root 権限ではなく `CAP_NET_ADMIN` capability だけが必要です。

2. **コンテナセキュリティの強化**:
  - コンテナランタイムは、デフォルトで限られた capabilities セットのみをコンテナに付与します。
  - これにより、コンテナがホストシステムに及ぼせる影響が制限されます。
  - コンテナ内で root として実行されるプロセスであっても capabilities は制限されるため、セキュリティリスクが低減されます。

3. **主なコンテナ関連 Capabilities**:
  - `CAP_NET_ADMIN`: ネットワーク設定変更
  - `CAP_SYS_ADMIN`: システム管理タスク（非常に強力）
  - `CAP_CHOWN`: ファイル所有権の変更
  - `CAP_DAC_OVERRIDE`: ファイル権限の回避
  - `CAP_SETUID`: UID 変更
  - `CAP_SETGID`: GID 変更

**最小権限の原則の重要性:**

次の理由により、コンテナには必要最小限の capabilities のみを付与することが重要です:

1. **攻撃対象領域の削減**:
  - 不要な capabilities を削除すると、攻撃者が悪用できる経路が減ります。
  - コンテナが侵害された場合でも、攻撃者が実行できる操作は制限されます。

2. **コンテナエスケープの防止**:
  - 強力な capabilities（特に `CAP_SYS_ADMIN`）は、コンテナエスケープ（コンテナからホストへアクセスすること）を可能にする場合があります。
  - これらの capabilities を制限すると、コンテナエスケープのリスクを大幅に低減できます。

3. **多層防御戦略**:
  - 最小権限の原則は、多層防御セキュリティ戦略の一部です。
  - 他のセキュリティ機構（seccomp、AppArmor、SELinux など）と併用することで、より強固なセキュリティを提供します。

4. **規制遵守**:
  - 多くのセキュリティ標準や規制は、最小権限の原則を要求しています。
  - コンテナに必要最小限の capabilities だけを付与することは、これらの要件を満たすのに役立ちます。

5. **問題の分離**:
  - コンテナに限定的な capabilities を付与すると、1 つのコンテナで発生した問題が他のコンテナやホストシステムへ広がるのを防げます。

本番環境では、コンテナが必要とする capabilities を正確に特定し、それ以外の capabilities をすべて削除することが良いセキュリティプラクティスです。これには Docker の `--cap-drop`、`--cap-add` オプション、または Kubernetes の `securityContext.capabilities` フィールドを使用できます。
</details>

32. systemd service unit ファイルの構造と主要セクション（[Unit]、[Service]、[Install]）の役割を説明し、Kubernetes kubelet サービスの基本的な unit ファイル例を書いてください。

<details>

<summary>答えを表示</summary>

**回答:**

**systemd unit ファイルの主要セクション:**

1. **[Unit] セクション**: unit のメタデータと依存関係を定義します
   - `Description`: サービスの説明
   - `Documentation`: ドキュメント URL
   - `After/Before`: 起動順序を定義
   - `Requires/Wants`: 依存関係を定義

2. **[Service] セクション**: サービスの実行方法を定義します
   - `Type`: サービス種別（simple、forking、oneshot など）
   - `ExecStart`: 実行するコマンド
   - `Restart`: 再起動ポリシー
   - `RestartSec`: 再起動待機時間

3. **[Install] セクション**: unit が有効化されたときの動作を定義します
   - `WantedBy`: この unit を必要とする target

**kubelet サービス unit ファイル例:**

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
この unit ファイルは kubelet サービスを定義します。ネットワークの準備が整った後に開始し（`After=network-online.target`）、失敗時には常に再起動し（`Restart=always`）、10 秒ごとに再起動を試みます（`RestartSec=10`）。`WantedBy=multi-user.target` は、このサービスがシステムの multi-user モード起動時に開始されることを意味します。
</details>

33. Kubernetes ノード構成に必要な sysctl カーネルパラメータを恒久的に設定する方法を説明し、各パラメータの役割を述べてください。

<details>

<summary>答えを表示</summary>

**回答:**

**Kubernetes に必要な主要 sysctl 設定とその役割:**

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

**各パラメータの役割:**

1. **net.ipv4.ip_forward = 1**
   - Linux カーネルがネットワークインターフェース間でパケットを転送できるようにします
   - Pods から他の Pods または外部ネットワークへの通信に不可欠です
   - 無効になっていると、コンテナネットワーキングは動作しません

2. **net.bridge.bridge-nf-call-iptables = 1**
   - ブリッジを通過するトラフィックが iptables ルールの対象になるよう設定します
   - Kubernetes Service（ClusterIP、NodePort）と NetworkPolicy が正しく動作するために不可欠です
   - kube-proxy が Service ルーティングに iptables を使用するため必要です

3. **net.ipv6.conf.all.forwarding = 1**
   - IPv6 環境でパケット転送を有効にします
   - dual-stack クラスターに必要です

**設定適用の順序:**
1. まず `br_netfilter` モジュールをロードします: `modprobe br_netfilter`
2. sysctl 設定ファイルを作成します
3. `sysctl --system` ですべての設定を適用します

これらの設定がないと、Kubernetes クラスターネットワーキングは適切に機能せず、特に Pod-to-Pod 通信や Service discovery で問題が発生します。
</details>

34. journald と logrotate を使用した Linux ログ管理戦略を説明し、Kubernetes ノードで効率的にログを管理するための設定方法を提示してください。

<details>

<summary>答えを表示</summary>

**回答:**

**journald と logrotate の役割:**

**journald (systemd ベースのロギング):**
- systemd サービスから stdout/stderr ログを収集します
- バイナリ形式で保存され、journalctl で照会します
- 自動ログ圧縮とローテーションをサポートします

**logrotate (従来型のログファイル管理):**
- テキストログファイルのローテーション、圧縮、削除を管理します
- cron ジョブにより定期的に実行されます

**Kubernetes ノードログ管理設定:**

**1. journald 設定 (/etc/systemd/journald.conf):**
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

**2. コンテナログ用 logrotate 設定:**
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

**3. ログクリーンアップコマンド:**
```bash
# journald log cleanup
journalctl --vacuum-time=7d   # Delete logs older than 7 days
journalctl --vacuum-size=1G   # Delete old logs when exceeding 1GB

# Check disk usage
journalctl --disk-usage
```

**Kubernetes ログ管理のベストプラクティス:**

1. **kubelet ログ**: journald によって管理され、`/var/log/journal/` に保存されます
2. **コンテナログ**: `/var/log/containers/` に保存され、logrotate によって管理されます
3. **集中ログ管理**: Fluentd/Fluent Bit を使用して外部システムへ転送することが推奨されます

適切なログ管理は、ディスク容量枯渇によるノード障害を防ぐことと、トラブルシューティング用にログを保持することのバランスを維持します。
</details>

---

[学習資料に戻る](../../basics/01-linux-basics.md) | [次のクイズ: Linux 運用](./02-linux-advanced-quiz.md)
