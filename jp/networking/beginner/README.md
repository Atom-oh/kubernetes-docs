# Linuxネットワーキング入門

> **学習環境の基準**: Ubuntu Server 24.04 LTS。Rocky Linux 9を使う代替手順もあります
>
> **最終更新日**: 2026年9月15日

このコースは、最初のターミナル操作から始めます。ファイルを作成してプログラムをインストールし、IPとDNSを設定し、SSHで接続してファイアウォールルールを適用し、パケットを観察します。最後に、小さなWebサービスの問題を診断し、学んだことをDocker、Kubernetes、クラウドネットワーキングに結び付けます。

すべてのコマンドを暗記する必要はありません。目標は、**どのマシンを変更しているのか、何をもって成功と判断するのか、以前の状態にどう戻すのか**を説明できることです。

## コースの構成 {#course-map}

初めての方はレッスン1から始めてください。Linuxの使用経験がある方も、共通のラボ環境とレッスン2でのインターフェースの特定が必要です。所要時間は個人練習を含む計画上の目安です。実際の時間は経験によって異なります。

| 順序 | レッスン | できるようになること | 推定時間 |
|---|---|---|---|
| 1 | [LinuxとCLI](01-linux-cli.md) · [クイズ](../../quizzes/networking/beginner/01-linux-cli-quiz.md) | ディストリビューションを特定し、ファイル、エディター、パッケージ、サービスを扱う | 2～3時間 |
| 2 | [アドレスとインターフェース](02-addressing-interfaces.md) · [クイズ](../../quizzes/networking/beginner/02-addressing-interfaces-quiz.md) | IP、サブネット、ゲートウェイ、DNSそれぞれの役割を区別し、NICを特定する | 2～3時間 |
| 3 | [永続的なネットワーク設定](03-persistent-configuration.md) · [クイズ](../../quizzes/networking/beginner/03-persistent-configuration-quiz.md) | NetplanまたはNetworkManagerを設定し、再起動時や復旧時の動作を確認する | 3～4時間 |
| 4 | [DNSと接続性](04-dns-connectivity.md) · [クイズ](../../quizzes/networking/beginner/04-dns-connectivity-quiz.md) | 名前解決、ルート、ポート、HTTPをそれぞれ別に調査する | 2～3時間 |
| 5 | [SSHによるリモートアクセス](05-ssh-access.md) · [クイズ](../../quizzes/networking/beginner/05-ssh-access-quiz.md) | ホストキーを検証し、ユーザーキーでログインして、有効な設定を確認する | 2～3時間 |
| 6 | [ファイアウォールとホストセキュリティ](06-firewalls-host-security.md) · [クイズ](../../quizzes/networking/beginner/06-firewalls-host-security-quiz.md) | 必要なトラフィックを許可し、SELinuxとFail2banについて説明する | 3～4時間 |
| 7 | [監視とパフォーマンス](07-monitoring-performance.md) · [クイズ](../../quizzes/networking/beginner/07-monitoring-performance-quiz.md) | ソケット、パケット、トラフィックを観察し、測定の限界を説明する | 2～3時間 |
| 8 | [総合演習とクラウドとのつながり](08-container-cloud-capstone.md) · [クイズ](../../quizzes/networking/beginner/08-container-cloud-capstone-quiz.md) | 小規模な障害を再現、切り分け、復旧し、次に進む内容を選ぶ | 3～4時間 |

次に進む前に、各レッスンの完了基準を満たし、クイズの回答を自分の言葉で説明してください。レッスン1でパッケージ操作を学んだら、レッスン2～4の前に[ゲストツールの準備](#guest-tools)に戻ってください。カーネルチューニングとCNIの実装比較は、基本演習の後に扱います。

## ラボ用VMの準備 {#lab-environment}

### まずはVMを1台用意する

1. お使いのPCでサポートされている仮想化アプリケーションを使用します。OSイメージは、サポート対象の仮想CPUアーキテクチャに合わせてください。たとえばArmマシンでは、その仮想化ツールがサポートするArmイメージが必要です。
2. [Ubuntu Server公式ダウンロード](https://ubuntu.com/download/server)から**24.04 LTS**イメージを選びます。別のバージョンを使用する場合は、パッケージとサービスのデフォルト設定を再確認してください。[インストールガイド](https://documentation.ubuntu.com/server/tutorial/basic-installation/)に従い、パスワード付きの一般ユーザーを作成します。例では`student`を使用します。ご自身のユーザー名に置き換えてください。
3. 最初の割り当て量は、VMごとにvCPU 2個、メモリ2 GiB、ディスク20 GiBです。これはラボ計画上の提案であり、パフォーマンスの保証でも、すべてのハイパーバイザーに共通する最小要件でもありません。
4. 最初のNICは、ハイパーバイザーの**DHCP付きNATネットワーク**に接続します。これにより、インストールやパッケージのダウンロードが可能になり、その後の演習でも設定を変更せずに使えます。
5. ハイパーバイザーの**コンソールウィンドウ**からログインします。まだSSHは必要ありません。ゲストを通常の方法でシャットダウンし、クリーンインストールのスナップショットを作成します。

レッスン1ではVMは1台だけで十分です。通常のコンテナは、完全なVMのsystemdやネットワークマネージャーの代わりにはなりません。WSLはシェルの練習に使えますが、後半のネットワークやファイアウォール環境が同一だと想定してはいけません。

### レッスン2以降に向けてVMを2台準備する

両方のゲストでUbuntuを使うと、1つのディストリビューションに集中できます。Rocky Linux 9を使う代替手順もあります。[Rocky公式イメージ](https://rockylinux.org/download)と[ドキュメント](https://docs.rockylinux.org/)を使用してください。両方のディストリビューションを同時に学ぶ必要はありません。

1. 2台目のVMを別途インストールし、ゲストを`net-client`と`net-server`として識別できるようにします。単純なクローンではマシン識別子やSSHホストキーが重複する可能性があるため、最初は個別にインストールしてください。
2. 両方のゲストを通常の方法でシャットダウンし、それぞれに**2つ目のNIC**を追加します。
3. 2つ目のNICを、`linux-net-lab`など、同じ**内部仮想ネットワーク**に接続します。そのネットワークにはDHCPサーバーや外部アップリンクを接続しないでください。「ブリッジ」「NAT」「ホストオンリー」の設定は互換ではありません。選択したモードが実際に何に接続するのかを確認してください。
4. ハイパーバイザーの設定で、各NICのMACアドレスを記録します。ゲストを起動し、レッスン2でそのアドレスと`ip -br link`の表示を照合します。`eth1`、`enp0s8`、`ens19`などの名前は環境によって異なります。インターフェース名を確認せずにそのままコピーしないでください。
5. レッスン2と3でIPアドレスを設定します。インストーラーで2つ目のNICに任意のゲートウェイやDNSサーバーを追加しないでください。

| 項目 | クライアントVM | サーバーVM |
|---|---|---|
| 役割 | SSHとcurlのリクエストを送信する | SSHとHTTPのリクエストを受信する |
| 管理NIC | 既存のNAT/DHCP設定を維持する | 既存のNAT/DHCP設定を維持する |
| ラボNIC | `192.0.2.10/24` | `192.0.2.20/24` |
| ラボNICのゲートウェイ/DNS | なし | なし |
| 復旧アクセス | ハイパーバイザーのコンソールとスナップショット | ハイパーバイザーのコンソールとスナップショット |

```text
Client lab NIC                       Server lab NIC
192.0.2.10/24 ── internal virtual network ── 192.0.2.20/24
      |                                       |
Separate NAT/DHCP management NIC     Separate NAT/DHCP management NIC
```

`192.0.2.0/24`は、ここでは隔離されたローカルネットワーク上でのみ使う文書用アドレス範囲であり、インターネット上でルーティングされるネットワーク設計には使いません。管理NICは引き続きゲストを別のネットワークに接続するため、VM全体がエアギャップ環境になるわけではありません。

## レッスン1の後にゲストツールを準備する {#guest-tools}

まず[レッスン1のパッケージ操作手順](01-linux-cli.md)を学び、その後、レッスン2～4の前に、使い捨ての各ゲスト**内で**この確認項目を完了してください。リポジトリには、既存のNAT/DHCP管理接続を使います。内部ラボNICにはアップリンク、ゲートウェイ、DNSサーバーを設定しないでください。最小構成のイメージでは、ネットワークが動作していても診断ツールが省かれていることがあります。

### 不足しているコマンドとパッケージを特定する

**各ゲストで、一般ユーザーとして実行。確認のみ:**

```bash
hostname
cat /etc/os-release
command -v ip ss ping getent grep timeout dig tracepath traceroute python3 curl nc ncat
```

実行ファイルのパスが表示されれば、そのコマンドは利用できます。結果がわかりにくい場合は、たとえば`command -v dig`のように、名前を1つだけ指定して確認してください。不足している代替コマンドでパスが表示されない、または終了ステータスがゼロ以外になるのは正常です。不在のコマンドすべてではなく、**そのゲストで選んだ演習に必要な**不足コマンドを記録します。

| コマンド / 用途 | Ubuntu Server 24.04のパッケージ | Rocky Linux 9のパッケージ | 必要な場所 |
|---|---|---|---|
| `ip`、`ss`: インターフェース、ルート、ソケット | `iproute2` | `iproute` | 両方のゲスト |
| `ping`: 回数を制限したICMP確認 | `iputils-ping` | `iputils` | 両方のゲスト |
| `dig`: DNSプロトコルの問い合わせ | `bind9-dnsutils` | `bind-utils` | レッスン4のクライアント |
| `tracepath`: デフォルトの経路追跡ツール | `iputils-tracepath` | `iputils` | クライアント。これか次の行のどちらかを選択 |
| Linux版`traceroute`: 代替の経路追跡ツール | `traceroute` | `traceroute` | クライアント。この代替を選ぶ場合のみ |
| `python3`: 一時的なHTTPサーバー | `python3`（インタープリタのパッケージもインストールされる） | `python3` | サーバー |
| `curl`: HTTPリクエスト | `curl` | 既存の`curl-minimal` **または** `curl`プロバイダー | クライアントとサーバーの自己確認 |
| OpenBSD版`nc` / Ncat版`ncat`: TCPプローブ | `netcat-openbsd` → `nc`を使用 | `nmap-ncat` → `ncat`を使用 | クライアント |

この確認項目では、**デフォルトで`tracepath`を選択**します。Linux版`traceroute`がすでにインストールされている場合は、レッスン4にある対応するコマンドを使って代用できます。両方を揃える必要はありません。Rockyでは、`iputils`が`ping`と`tracepath`の両方を提供します。指定されたnetcat実装を使ってください。コマンド名が似ていても、同じオプションが使えるとは限りません。

`getent`、`grep`、`timeout`、sudo、エディターは、ゲストまたはレッスン1の基本環境に含まれます。これらの確認に失敗した場合は、まずその基本環境の問題を解決してください。この表にあるツールを揃えるために、別のネットワークマネージャーや名前解決ツールをインストールしないでください。**すでにNetworkManagerで管理されているRockyゲスト**では、`nmtui`はオプションであり、`NetworkManager-tui`から提供されます。このインターフェースを選ぶ場合に限り、同じ選択パッケージの手順で確認・インストールしてください。networkdを使うゲストには不要です。

### 選んだツールだけを確認してインストールする

最初にインストールする前に、ゲストのスナップショット`before-guest-tools`を作成し、インストール済みパッケージやプロバイダーの状態を記録してください。以下では**使用するディストリビューションの手順だけ**を使います。各例では`dig`が不足しているものとします。すでに利用できる場合は、そのインストールを省略してください。選択した別のコマンドが不足している場合は、表から対応する1つのパッケージを`TOOL_PACKAGE`に設定し、候補とトランザクションの確認を繰り返してください。表全体をインストールコマンドに貼り付けないでください。

**Ubuntuゲストで、一般ユーザーとして実行。sudoは明記した行でのみ使用:**

```bash
TOOL_PACKAGE=bind9-dnsutils
dpkg-query -W "$TOOL_PACKAGE"
sudo apt update
apt-cache policy "$TOOL_PACKAGE"
sudo apt-get --simulate install "$TOOL_PACKAGE"
```

パッケージがない場合、ローカル照会に「No packages found」と表示されるのは想定どおりです。リポジトリのインデックスを正常に更新した後、`Candidate`のバージョンと、シミュレーションで示される依存関係、アップグレード、削除を確認します。候補がない場合やリポジトリエラーがある場合は、停止して、設定済みのUbuntuリポジトリや管理経路を確認してください。パッケージがすでにインストールされているのにコマンドが見つからない場合は、競合するプロバイダーをインストールするのではなく、そのパッケージのファイルとコマンド検索パスを調べてください。

**選択したコマンドが不足しており**、プレビューに目的のパッケージと依存関係が含まれている場合に限り、**Ubuntuゲスト**でインストールします。

```bash
sudo apt install "$TOOL_PACKAGE"
```

実際の確認プロンプトも確認してください。プレビュー後、インストール前にメタデータが変わる可能性があります。想定外のアップグレードや削除を自動で承認しないでください。

**Rockyゲストで、一般ユーザーとして実行:** パッケージを選択する前に、curlプロバイダーを別途確認してください。

```bash
command -v curl
rpm -q curl curl-minimal
```

いずれかのパッケージ確認で「not installed」と表示されても正常です。`curl`がすでに動作する場合は、**どちらのプロバイダーが提供しているかにかかわらず、そのまま維持し**、もう一方のパッケージを要求しないでください。利用可能であることを確認できた後、`rpm -qf "$(command -v curl)"`を実行すれば、どのパッケージがそのコマンドを提供しているか確認できます。これらのHTTP演習には、既存の`curl-minimal`で十分です。`curl`と`curl-minimal`は競合します。このコースに従うために、`--allowerasing`やパッケージの入れ替えを使用しないでください。

`curl`がなく、**どちらのプロバイダーもインストールされていない**場合は、以下の手順で`curl-minimal`を選択します。プロバイダーがインストール済みなのにコマンドが見つからない場合は、置き換えるのではなく、そのパッケージのファイルやPATHを調べてください。

**Rockyゲストで、一般ユーザーとして実行。不足している`dig`の例のみ:**

```bash
TOOL_PACKAGE=bind-utils
rpm -q "$TOOL_PACKAGE"
dnf info "$TOOL_PACKAGE"
sudo dnf --assumeno install "$TOOL_PACKAGE"
```

利用可能なパッケージ、アーキテクチャ、リポジトリ、提案されている依存関係や削除対象を確認してください。`--assumeno`はインストールせずにトランザクションを拒否します。拒否されたトランザクションで終了ステータスがゼロ以外になっても、ネットワーク確認の失敗ではありません。候補がない場合は、設定済みのRocky 9リポジトリを調査してください。必須表のパッケージにEPELは必要ありません。その後、**選択した不足コマンドに限り**、**Rockyゲスト**にインストールします。

```bash
sudo dnf install "$TOOL_PACKAGE"
```

確定する前に、最終的なトランザクションの内容を確認してください。インストール済みのcurlプロバイダーと既存のネットワークマネージャーは維持してください。パッケージ候補やバージョンはゲスト上での確認結果であり、この文書が保証する値ではありません。

### コマンドを再確認し、復旧記録を残す

**両方のゲストで、一般ユーザーとして実行:** `command -v ip ss ping getent grep timeout`で基本ツールが見つかる必要があります。この確認項目でデフォルトの選択をした場合は、指定されたゲストで以下を確認してください。

```bash
# Client, either distribution; substitute traceroute only if you selected it:
command -v dig tracepath curl
```

```bash
# Ubuntu client only:
command -v nc
```

```bash
# Rocky client only:
command -v ncat
```

```bash
# Server, either distribution:
command -v python3 curl
python3 --version
```

選択したツールとPython 3.9以降のパスが表示されることを確認してください。追加したパッケージを記録します。これらの確認で分かるのはツールが利用可能かどうかであり、ネットワーク通信が成功するかどうかではありません。レッスン4で必要なツールが見つからなかった場合は、ここに戻ってください。

後のレッスンでも使うため、ツールはそのまま残してください。指定したパッケージを削除しても、依存関係、設定、キャッシュ、ログが正確に元に戻るわけではありません。もともと存在していたプロバイダーは絶対に削除せず、クリーンアップのために広範なautoremoveを実行しないでください。この準備を完全にロールバックするには、関連する演習を終えてから`before-guest-tools`を復元します。ただし、そのスナップショットによって後から行ったゲスト作業も破棄されることを理解してください。

パッケージ対応表は、2026年9月15日にディストリビューションの一次資料で確認しました。Ubuntu Nobleのファイル一覧: [iproute2](https://packages.ubuntu.com/noble/amd64/iproute2/filelist)、[ping](https://packages.ubuntu.com/noble/amd64/iputils-ping/filelist)、[dig](https://packages.ubuntu.com/noble/amd64/bind9-dnsutils/filelist)、[tracepath](https://packages.ubuntu.com/noble/amd64/iputils-tracepath/filelist)、[traceroute](https://packages.ubuntu.com/noble/amd64/traceroute/filelist)、[netcat](https://packages.ubuntu.com/noble/amd64/netcat-openbsd/filelist)、[curl](https://packages.ubuntu.com/noble/amd64/curl/filelist)、[Pythonパッケージの依存関係](https://packages.ubuntu.com/noble/python3)。Rocky 9のパッケージ仕様: [iproute](https://git.rockylinux.org/staging/rpms/iproute/-/blob/r9/SPECS/iproute.spec)、[iputils](https://git.rockylinux.org/staging/rpms/iputils/-/blob/r9/SPECS/iputils.spec)、[BIND utilities](https://git.rockylinux.org/staging/rpms/bind/-/blob/r9/SPECS/bind.spec)、[Ncat](https://git.rockylinux.org/staging/rpms/nmap/-/blob/r9/SPECS/nmap.spec)、[curlプロバイダー](https://git.rockylinux.org/staging/rpms/curl/-/blob/r9/SPECS/curl.spec)。稼働中のゲストでの確認では、適切なアーキテクチャとバージョンが選択されます。x86_64のファイル一覧は一例であり、そのアーキテクチャの使用を求めるものではありません。

## コマンドの読み方 {#command-conventions}

- **クライアント**、**サーバー**、**両方**は、コマンドを実行する場所を示します。まずホスト名を確認してください。
- コマンドブロックでは`$`や`#`のプロンプトを省略しています。`sudo`は、そのコマンドに管理者権限を要求します。
- `LAB_IF`のような大文字の名前は、現在のシェルで使う変数です。新しいターミナルを開いたときは、実際のNICを手順どおりに特定してから、変数を再設定してください。
- YAMLとINIのブロックは設定ファイルの内容であり、シェルに貼り付けて実行するコマンドではありません。
- 「出力例」は、実行結果を保証するものではありません。アドレス、インターフェース、カウンター、時刻を自分の環境と比較してください。
- 変更前の状態と設定を記録してください。一度に変更するのは1つだけにし、確認に失敗した場合はレッスンの復旧手順に従ってください。

これらの演習は、使い捨てのVM上で行います。読書に使っている端末やリモートの本番サーバーのネットワークやファイアウォールを変更するよう求めるものではありません。

## 用語の入門 {#starter-glossary}

| 用語 | 最初に覚える意味 |
|---|---|
| カーネル / ユーザー空間 | ハードウェアやリソースを管理する中核 / その上で動作するシェルやプログラム |
| NIC / インターフェース | 通信デバイス / OS上でそのデバイスを操作するために使う名前と設定 |
| MAC / IP | リンク上でフレームを配送するためのアドレス / ネットワーク間でパケットを配送するためのアドレス |
| サブネット / プレフィックス | 先頭ビットを共有するアドレス範囲 / そのビット数 |
| ゲートウェイ / ルート | 転送先となる次のルーター / 宛先に応じて選択される転送ルール |
| DHCP / DNS | ネットワーク設定をリースする / 名前に関連付けられた情報を検索する |
| TCP / UDP / ポート | 2つのトランスポートプロトコル / ホスト上の通信エンドポイントを識別する番号 |
| HTTP / SSH | Webのリクエストとレスポンスのプロトコル / 認証と暗号化に対応したリモートアクセス用プロトコル |
| ソケット / リスナー | プログラムの通信エンドポイント / 新しい接続を待ち受けるソケット |
| ファイアウォール / SELinux | トラフィックのルール / プロセスによるリソースへのアクセスを制御するポリシー |
| NAT / CNI | アドレス変換 / コンテナネットワークの設定に使うインターフェースと実装のエコシステム |

## 完了基準 {#completion}

「コマンドが実行できた」だけでは、完了とは言えません。

- 使用しているディストリビューションとパッケージマネージャーを説明し、ファイルを編集する。
- ラボNICと管理NICを区別し、IP、ルート、DNSの設定を管理しているものを特定する。
- SSHのホスト識別、鍵ログイン、有効な設定、復旧方法を確認する。
- ラボサービスへのアクセスを、意図したクライアントだけに許可し、追加したルールを取り消す。
- 観察結果を使って、DNSの失敗、TCP接続の失敗、HTTPエラーを区別する。
- ソケット、パケット、アプリケーションの情報を組み合わせて、[総合演習レポート](08-container-cloud-capstone.md#capstone-report)にまとめる。

続けて、[プロトコルの詳細](../../basics/06-network-fundamentals-part1.md)、[カーネルのパケット経路](../../kernel/02-network-stack.md)、[Linuxの詳しい診断方法](../07-linux-network-diagnostics.md)、[Kubernetes Serviceラボ](../../labs/core/03-services-networking-lab.md)に進んでください。CNI製品のインストールを最初に行う必要はありません。

## エキスパート向けの学習経路に進む

[エキスパート向けネットワーキング学習経路](../expert/README.md)では、この初心者向けコースに続いて、プロトコル、ルーティング、パケット経路、ポリシーや障害の前・最中・後に確認する証拠を扱う9つのワークブックに取り組みます。章によって環境が異なります。まず[開始前の確認](../expert/README.md#entry-check)を行ってください。

## 外部コースの活用 {#further-study}

外部コースは任意です。[BootlinのLinuxネットワーキングコース](https://bootlin.com/training/networking/)は、後のカーネルネットワーキング学習に役立ちます。[Linux Foundationのネットワーキングコース一覧](https://training.linuxfoundation.org/networking/)では、専門分野の次のコースを探せます。対象範囲、価格、日程は提供元に確認してください。

CentOS 7の教材や、古い`ifconfig`ベースのレッスンを読む際は、概念と実行環境を分けて考えてください。このコースでは、上記のディストリビューションと`ip`、`ss`を使用します。

**開始:** [レッスン1: LinuxとCLI](01-linux-cli.md)
