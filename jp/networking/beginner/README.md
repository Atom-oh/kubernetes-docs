# ゼロから学ぶLinuxネットワーキング

> **学習環境の前提**: Ubuntu Server 24.04 LTS。別の方法としてRocky Linux 9も利用できます。
>
> **最終更新日**: September 15, 2026

このコースでは、最初のターミナル操作から始めます。ファイルの作成やプログラムのインストール、IPとDNSの設定、SSH接続、ファイアウォールルールの適用、パケットの観測を行います。最後に、小さなWebサービスの問題を診断し、学んだ内容をDocker、Kubernetes、クラウドのネットワーキングと結び付けます。
すべてのコマンドを暗記する必要はありません。目標は、**どのマシンを変更しているか、何をもって成功と判断するか、以前の状態へどう戻すか**を説明できるようになることです。

## コース一覧 {#course-map}

初めて学ぶ人はレッスン1から始めてください。Linuxの経験者も、共有ラボ環境の準備とレッスン2でのインターフェース特定が必要です。所要時間は個人演習を含む計画上の目安で、実際の時間は経験によって異なります。

| 順番 | レッスン | できるようになること | 目安時間 |
|---|---|---|---|
| 1 | [LinuxとCLI](01-linux-cli.md) · [クイズ](../../quizzes/networking/beginner/01-linux-cli-quiz.md) | ディストリビューションを特定し、ファイル、エディター、パッケージ、サービスを扱う | 2～3時間 |
| 2 | [アドレスとインターフェース](02-addressing-interfaces.md) · [クイズ](../../quizzes/networking/beginner/02-addressing-interfaces-quiz.md) | IP、サブネット、ゲートウェイ、DNSの役割を区別し、NICを特定する | 2～3時間 |
| 3 | [ネットワーク設定の永続化](03-persistent-configuration.md) · [クイズ](../../quizzes/networking/beginner/03-persistent-configuration-quiz.md) | NetplanまたはNetworkManagerを設定し、再起動後の動作と復旧を確認する | 3～4時間 |
| 4 | [DNSと接続性](04-dns-connectivity.md) · [クイズ](../../quizzes/networking/beginner/04-dns-connectivity-quiz.md) | 名前解決、経路、ポート、HTTPを分けて調査する | 2～3時間 |
| 5 | [SSHによるリモートアクセス](05-ssh-access.md) · [クイズ](../../quizzes/networking/beginner/05-ssh-access-quiz.md) | ホスト鍵を確認し、ユーザー鍵でログインして有効な設定を調べる | 2～3時間 |
| 6 | [ファイアウォールとホストセキュリティ](06-firewalls-host-security.md) · [クイズ](../../quizzes/networking/beginner/06-firewalls-host-security-quiz.md) | 必要なトラフィックを許可し、SELinuxとFail2banを説明する | 3～4時間 |
| 7 | [モニタリングとパフォーマンス](07-monitoring-performance.md) · [クイズ](../../quizzes/networking/beginner/07-monitoring-performance-quiz.md) | ソケット、パケット、トラフィックを観測し、測定の限界を説明する | 2～3時間 |
| 8 | [総合演習とクラウド接続](08-container-cloud-capstone.md) · [クイズ](../../quizzes/networking/beginner/08-container-cloud-capstone-quiz.md) | 小さな障害を再現、切り分け、復旧し、次の学習内容を選ぶ | 3～4時間 |

各レッスンの完了条件を満たし、クイズの答えを自分の言葉で説明してから次に進んでください。レッスン1でパッケージ操作を学んだら、レッスン2～4に進む前に[ゲストツールの準備](#guest-tools)に戻ります。カーネルのチューニングやCNI実装の比較は、基本演習を終えてから取り組みます。

## ラボVMを準備する {#lab-environment}

### まずVMを1台用意する

1. PCでサポートされている仮想化アプリケーションを使います。OSイメージは仮想CPUのアーキテクチャに合わせてください。たとえばArmマシンでは、その仮想化ツールが対応するArmイメージが必要です。
2. [Ubuntu Serverの公式ダウンロード](https://ubuntu.com/download/server)から**24.04 LTS**イメージを選びます。別のバージョンを使う場合は、パッケージとサービスの既定値を再確認してください。[インストールガイド](https://documentation.ubuntu.com/server/tutorial/basic-installation/)に従い、パスワードを持つ一般ユーザーを作成します。例では`student`を使います。自分のユーザー名に置き換えてください。
3. VMごとに2 vCPU、メモリ2 GiB、ディスク20 GiBを初期割り当ての目安にします。これはラボ準備の提案であり、性能を保証する値でも、あらゆるハイパーバイザーに共通する最小仕様でもありません。
4. 最初のNICを、DHCPを使うハイパーバイザーの**NATネットワーク**に接続します。インストールやパッケージのダウンロードに使い、以降の演習では変更しません。
5. ハイパーバイザーの**コンソールウィンドウ**からログインします。まだSSHは不要です。ゲストを通常の手順でシャットダウンし、初期状態のスナップショットを取得します。

レッスン1で使うVMは1台だけです。通常のコンテナは、完全なVMが持つsystemdやネットワーク管理機能の代わりにはなりません。WSLでシェルの練習はできますが、後半のネットワーク／ファイアウォール環境が同じだとは想定しないでください。

### レッスン2以降はVMを2台用意する

両方のゲストにUbuntuを使うと、1つのディストリビューションに集中できます。Rocky Linux 9を使う方法もあります。[Rockyの公式イメージ](https://rockylinux.org/download)と[ドキュメント](https://docs.rockylinux.org/)を参照してください。2つのディストリビューションを同時に学ぶ必要はありません。

1. 2台目のVMを別途インストールし、ゲスト名を`net-client`と`net-server`にします。単純にクローンするとマシン識別子やSSHホスト鍵が重複する場合があるため、最初は個別にインストールしてください。
2. 両方のゲストを通常の手順でシャットダウンし、それぞれに**2つ目のNIC**を追加します。
3. 2つ目のNICを両ゲストで同じ**内部仮想ネットワーク**（たとえば`linux-net-lab`）に接続します。このネットワークにDHCPサーバーや外部アップリンクを接続しないでください。「ブリッジ」「NAT」「ホストオンリー」は相互に置き換えられません。選択したモードが何に接続するかを確認してください。
4. ハイパーバイザーの設定で各NICのMACアドレスを記録します。ゲストを起動したら、レッスン2でそのアドレスと`ip -br link`の表示を照合します。`eth1`、`enp0s8`、`ens19`などの名前は異なるため、インターフェース名をそのままコピーしないでください。
5. レッスン2と3でIPアドレスを設定します。インストーラーで2つ目のNICに任意のゲートウェイやDNSサーバーを設定しないでください。

| 項目 | クライアントVM | サーバーVM |
|---|---|---|
| 役割 | SSHとcurlの要求を送信する | SSHとHTTPの要求を受信する |
| 管理用NIC | 既存のNAT／DHCP設定を維持する | 既存のNAT／DHCP設定を維持する |
| ラボ用NIC | `192.0.2.10/24` | `192.0.2.20/24` |
| ラボ用NICのゲートウェイ／DNS | なし | なし |
| 復旧アクセス | ハイパーバイザーのコンソールとスナップショット | ハイパーバイザーのコンソールとスナップショット |

```text
Client lab NIC                       Server lab NIC
192.0.2.10/24 ── internal virtual network ── 192.0.2.20/24
      |                                       |
Separate NAT/DHCP management NIC     Separate NAT/DHCP management NIC
```

`192.0.2.0/24`はここでは、分離されたローカルネットワークだけで使う文書用アドレス範囲です。インターネット上で経路制御されるネットワークの設計例ではありません。ただし、管理用NICは引き続きゲストを別のネットワークに接続するため、VM全体がエアギャップになるわけではありません。

## レッスン1の後にゲストツールを準備する {#guest-tools}

まず[レッスン1のパッケージ操作](01-linux-cli.md)を学び、その後、レッスン2～4を始める前に、**使い捨てゲストごとに**この確認を完了します。リポジトリには既存のNAT／DHCP管理接続を使ってください。内部ラボ用NICにアップリンク、ゲートウェイ、DNSサーバーを設定してはいけません。最小構成のイメージでは、ネットワークが使えても診断ツールが入っていないことがあります。

### 不足しているコマンドとパッケージを確認する

**各ゲストの一般ユーザーで、次を確認するだけにします。**

```bash
hostname
cat /etc/os-release
command -v ip ss ping getent grep timeout dig tracepath traceroute python3 curl nc ncat
```

実行ファイルのパスが表示されれば、そのコマンドは使用可能です。結果が分かりにくい場合は、たとえば`command -v dig`のように1つずつ確認します。別の選択肢のパスが出ないことや終了ステータスが0以外であることは、未導入なら通常の結果です。存在しないものをすべて列挙するのではなく、**そのゲストで選んだ演習に必要な**コマンドだけを記録します。

| コマンド／用途 | Ubuntu Server 24.04のパッケージ | Rocky Linux 9のパッケージ | 必要な場所 |
|---|---|---|---|
| `ip`、`ss`: インターフェース、経路、ソケット | `iproute2` | `iproute` | 両ゲスト |
| `ping`: 上限時間付きICMP確認 | `iputils-ping` | `iputils` | 両ゲスト |
| `dig`: DNSプロトコルの問い合わせ | `bind9-dnsutils` | `bind-utils` | レッスン4のクライアント |
| `tracepath`: 既定の経路追跡方法 | `iputils-tracepath` | `iputils` | クライアント。次の行の方法とのいずれか |
| Linux版`traceroute`: 経路追跡の代替方法 | `traceroute` | `traceroute` | この方法を選ぶ場合に限りクライアント |
| `python3`: 一時的なHTTPサーバー | `python3`（インタープリターパッケージも導入） | `python3` | サーバー |
| `curl`: HTTP要求 | `curl` | 既存の`curl-minimal`**または**`curl`プロバイダー | クライアントとサーバーの自己確認 |
| OpenBSD版`nc`／Ncat版`ncat`: TCPプローブ | `netcat-openbsd` → `nc`を使用 | `nmap-ncat` → `ncat`を使用 | クライアント |

この確認では、**既定で`tracepath`を選びます**。Linux版`traceroute`がすでにインストールされていれば、レッスン4の対応するコマンドを使えます。両方を必須にする必要はありません。Rockyでは`iputils`が`ping`と`tracepath`の両方を提供します。指定したnetcat実装を使ってください。似たコマンド名でも、オプションが同じとは限りません。

`getent`、`grep`、`timeout`、sudo、エディターは、ゲスト／レッスン1の基本要件です。これらの確認に失敗した場合は、まず基本環境を整えてください。この表を満たすために、2つ目のネットワーク管理ツールやリゾルバーをインストールしないでください。**すでにNetworkManagerで管理されているRockyゲスト**では、必要なら`NetworkManager-tui`が任意の`nmtui`を提供します。`nmtui`を選ぶ場合に限り、同じ選択式パッケージ手順で確認／インストールしてください。networkdを使うゲストでは不要です。

### 選択した不足ツールだけを事前確認してインストールする

初回インストール前に、ゲストのスナップショット`before-guest-tools`を取得し、インストール済みのパッケージ／プロバイダーの状態を記録します。以下では**使用中のディストリビューションに該当する手順だけ**を使います。**各例では`dig`が不足している**ものとします。すでに使える場合は、そのインストールを飛ばしてください。ほかに選んだコマンドが不足している場合は、表にある該当コマンドのパッケージ1つを`TOOL_PACKAGE`に指定し、候補とトランザクションの確認を繰り返します。表の全パッケージをまとめてインストールコマンドに貼り付けないでください。

**Ubuntuゲストの一般ユーザーで実行します。sudoを使うのは明示した行だけです。**

```bash
TOOL_PACKAGE=bind9-dnsutils
dpkg-query -W "$TOOL_PACKAGE"
sudo apt update
apt-cache policy "$TOOL_PACKAGE"
sudo apt-get --simulate install "$TOOL_PACKAGE"
```

ローカルパッケージ検索で「パッケージが見つからない」と表示されるのは、未導入なら想定内です。リポジトリーのインデックス更新に成功した後、`Candidate`のバージョンとシミュレーションされた依存関係、更新、削除を確認してください。候補がない場合やリポジトリーエラーがある場合は中止し、設定済みのUbuntuリポジトリー／管理経路を調べます。パッケージがインストール済みなのにコマンドが見つからない場合は、競合するプロバイダーをインストールせず、ファイルとコマンド検索パスを調べてください。

**選択したコマンドが不足しており**、プレビューに目的のパッケージ／依存関係が表示された場合に限り、**Ubuntuゲスト**にインストールします。

```bash
sudo apt install "$TOOL_PACKAGE"
```

実際の確認プロンプトも見てください。プレビューとインストールの間にメタデータが変わる場合があります。想定外の更新や削除を自動で承認しないでください。

**Rockyゲストの一般ユーザーで作業します**。パッケージを選ぶ前に、curlのプロバイダーを個別に確認してください。

```bash
command -v curl
rpm -q curl curl-minimal
```

パッケージ検索のどちらかで「未インストール」と表示されることがありますが、これは正常です。`curl`がすでに動作している場合は、所有しているプロバイダーを**そのまま使い**、もう一方のパッケージを要求しないでください。利用可能であることを確認した後、`rpm -qf "$(command -v curl)"`で所有者を調べられます。これらのHTTP演習では、既存の`curl-minimal`で十分です。`curl`と`curl-minimal`は競合するため、このコースに従う目的で`--allowerasing`やパッケージの入れ替えを使わないでください。

`curl`がなく、**どちらのプロバイダーもインストールされていない**場合は、以下の手順で`curl-minimal`を選びます。プロバイダーがインストール済みなのにコマンドが見つからない場合は、置き換えるのではなく、そのファイルとPATHを調べてください。

**Rockyゲストの一般ユーザーで実行します。以下は`dig`が不足している場合だけの例です。**

```bash
TOOL_PACKAGE=bind-utils
rpm -q "$TOOL_PACKAGE"
dnf info "$TOOL_PACKAGE"
sudo dnf --assumeno install "$TOOL_PACKAGE"
```

利用可能なパッケージ、アーキテクチャ、リポジトリー、提案された依存関係／削除を確認します。`--assumeno`はインストールせずにトランザクションを拒否します。拒否された処理の終了ステータスが0以外でも、ネットワークプローブの失敗ではありません。候補がない場合は設定済みのRocky 9リポジトリーを調べてください。必須パッケージ表はEPELを要求していません。その後、**選んだ不足コマンドだけ**を**Rockyゲスト**にインストールします。

```bash
sudo dnf install "$TOOL_PACKAGE"
```

確定する前に最終トランザクションを確認してください。インストール済みのcurlプロバイダーと既存のネットワーク管理ツールは維持します。パッケージ候補やバージョンはゲスト上で観測した値であり、このドキュメントが保証する値ではありません。

### コマンドを再確認し、復旧用の記録を残す

**両ゲストの一般ユーザーで**、`command -v ip ss ping getent grep timeout`により基本ツールが見つかることを確認します。この確認で既定のツールを選ぶ場合は、該当するゲストで次も確認してください。

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

選択したツールのパスとPython 3.9以降が表示されることを確認します。追加したパッケージを記録してください。これらの確認で分かるのは利用可能かどうかであり、ネットワーク通信が成功するかではありません。レッスン4で必要なツールがないと分かった場合は、ここに戻ります。

ツールは以降のレッスンでも使います。パッケージを指定して削除しても、依存関係、設定、キャッシュ、ログが正確に元へ戻るとは限りません。既存のプロバイダーを削除したり、後片付けに広範囲なautoremoveを実行したりしないでください。この準備を完全に取り消すには、関連する演習の終了後に`before-guest-tools`を復元します。その場合、スナップショット以降のゲスト作業も失われることを理解してください。

パッケージの対応関係は、2026年9月15日にディストリビューションの一次資料で確認しました。Ubuntu Nobleでは、[iproute2](https://packages.ubuntu.com/noble/amd64/iproute2/filelist)、[ping](https://packages.ubuntu.com/noble/amd64/iputils-ping/filelist)、[dig](https://packages.ubuntu.com/noble/amd64/bind9-dnsutils/filelist)、[tracepath](https://packages.ubuntu.com/noble/amd64/iputils-tracepath/filelist)、[traceroute](https://packages.ubuntu.com/noble/amd64/traceroute/filelist)、[netcat](https://packages.ubuntu.com/noble/amd64/netcat-openbsd/filelist)、[curl](https://packages.ubuntu.com/noble/amd64/curl/filelist)、[Pythonパッケージ依存関係](https://packages.ubuntu.com/noble/python3)を確認しました。Rocky 9では、[iproute](https://git.rockylinux.org/staging/rpms/iproute/-/blob/r9/SPECS/iproute.spec)、[iputils](https://git.rockylinux.org/staging/rpms/iputils/-/blob/r9/SPECS/iputils.spec)、[BINDユーティリティ](https://git.rockylinux.org/staging/rpms/bind/-/blob/r9/SPECS/bind.spec)、[Ncat](https://git.rockylinux.org/staging/rpms/nmap/-/blob/r9/SPECS/nmap.spec)、[curlのプロバイダー](https://git.rockylinux.org/staging/rpms/curl/-/blob/r9/SPECS/curl.spec)を確認しました。実行中のゲストでは、適切なアーキテクチャとバージョンの候補が選択されます。x86_64のファイル一覧例は、そのアーキテクチャの使用を求めるものではありません。

## コマンドの読み方 {#command-conventions}

- **クライアント**、**サーバー**、**両方**は、コマンドを実行する場所を示します。先にホスト名を確認してください。
- コマンドブロックでは`$`や`#`のプロンプトを省略しています。`sudo`はそのコマンドに管理者権限を要求します。
- `LAB_IF`のような大文字の名前は、現在のシェルで使う変数です。新しいターミナルを開いたときは、実際のNICを指示に従って特定した上で設定し直してください。
- YAMLとINIのブロックは設定ファイルの内容であり、シェルに貼り付けるコマンドではありません。
- 「出力例」は、自分の実行結果を保証するものではありません。アドレス、インターフェース、カウンター、時刻を自分の環境で確認してください。
- 変更前の状態と設定を記録してください。一度に1つだけ変更し、確認に失敗した場合はレッスンに記載された復旧手順に従います。

演習では使い捨てVMを使います。読み物を表示している端末や、リモートの本番サーバーのネットワーク／ファイアウォールを変更するよう求めるものではありません。

## 用語集（入門） {#starter-glossary}

| 用語 | 最初に覚える意味 |
|---|---|
| カーネル／ユーザー空間 | ハードウェアとリソースを管理する中核部分／その上で動くシェルやプログラム |
| NIC／インターフェース | 通信デバイス／OS上で操作する際の名称と設定 |
| MAC／IP | リンク上でフレームを届けるアドレス／ネットワーク間でパケットを届けるアドレス |
| サブネット／プレフィックス | 先頭のビットを共有するアドレス範囲／そのビット数 |
| ゲートウェイ／経路 | 次に転送するルーター／宛先に応じて選択する転送ルール |
| DHCP／DNS | ネットワーク設定を割り当てる仕組み／名前に関連付けられた情報を検索する仕組み |
| TCP／UDP／ポート | 2つのトランスポートプロトコル／ホスト上の通信エンドポイントを示す番号 |
| HTTP／SSH | Webの要求／応答プロトコル／認証と暗号化を備えたリモートアクセスプロトコル |
| ソケット／リスナー | プログラムの通信エンドポイント／新しい接続を待ち受けるソケット |
| ファイアウォール／SELinux | トラフィックのルール／プロセスによるリソースアクセスを制御するポリシー |
| NAT／CNI | アドレス変換／コンテナネットワークのセットアップに使うインターフェースと実装の仕組み |

## 完了条件 {#completion}

「コマンドを実行できた」だけで完了とはしません。

- 使用するディストリビューションとパッケージ管理ツールを説明し、ファイルを編集できる。
- ラボ用NICと管理用NICを区別し、IP、経路、DNSの設定を管理する主体を特定できる。
- SSHのホスト識別情報、鍵ログイン、有効な設定、復旧方法を確認できる。
- ラボのサービスへのアクセスを意図したクライアントに限定し、追加したルールを元に戻せる。
- DNSの失敗、TCP接続の失敗、HTTPエラーを観測結果で区別できる。
- ソケット、パケット、アプリケーションの証拠をまとめて[総合演習のレポート](08-container-cloud-capstone.md#capstone-report)を作成できる。

続けて[プロトコルの詳細](../../basics/06-network-fundamentals-part1.md)、[カーネルのパケット経路](../../kernel/02-network-stack.md)、[Linuxの詳細な診断](../07-linux-network-diagnostics.md)、[Kubernetes Serviceのラボ](../../labs/core/03-services-networking-lab.md)に進みます。最初にCNI製品をインストールする必要はありません。

## エキスパート編へ進む

[ネットワーキングのエキスパート編](../expert/README.md)では、この初級コースに続いて、プロトコル、ルーティング、パケット経路、ポリシー／障害の前後と実行中の証拠を扱う6つのワークブックに取り組みます。章ごとに環境が異なります。[参加前の確認](../expert/README.md#entry-check)から始めてください。

## 外部コースの利用 {#further-study}

外部コースは任意です。[BootlinのLinuxネットワーキングコース](https://bootlin.com/training/networking/)は後半のカーネルネットワーキング学習に役立ちます。[Linux Foundationのネットワーキング講座一覧](https://training.linuxfoundation.org/networking/)から専門分野の次のコースを探すこともできます。対象範囲、価格、日程は提供元に確認してください。

CentOS 7の教材や古い`ifconfig`中心のレッスンを読む場合は、概念と実行環境を分けて考えてください。このコースでは上記のディストリビューションと`ip`、`ss`を使います。

**開始:** [レッスン1: LinuxとCLI](01-linux-cli.md)
