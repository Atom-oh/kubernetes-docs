# 5. SSHによるリモートアクセス

> **対応バージョン**: Ubuntu Server 24.04 LTS（主環境）、Rocky Linux 9（代替環境）
> **最終更新日**: 2026年9月15日

[前へ: DNSと接続](04-dns-connectivity.md) | [コース](README.md) | [クイズ](../../quizzes/networking/beginner/05-ssh-access-quiz.md) | [次へ: ホストセキュリティ](06-firewalls-host-security.md)

SSHを使うと、別のコンピューター上で暗号化された端末を利用できます。しかし、暗号化だけでは不十分です。クライアントはサーバーを識別し、サーバーは利用者のアカウントを認証する必要があります。ログイン設定を変更する前に、この2つのアイデンティティを別々に確立します。

## 前提条件、到達目標、復旧の境界

レッスン1～4を完了してください。クライアント`192.0.2.10/24`とサーバー`192.0.2.20/24`では、MACアドレスを照合済みの内部専用NICを使います。ラボ用のDHCP、ゲートウェイ、上り回線は使いません。NAT／DHCP管理用の別NICは変更しません。通常アカウントを使い、**作業中はサーバーのハイパーバイザーコンソールを開いたままにしてください**。サーバーでsudoを使えること、通常アカウントのパスワードまたは公開鍵をインストールするためのコンソールアクセスがあること、パッケージをダウンロードするための既存の管理接続が必要です。

SSHツールをインストール／確認し、ホストフィンガープリントを検証し、パスフレーズで保護したユーザー鍵を作成して公開鍵だけをインストールします。その後、独立した2回目の鍵のみログインを実証し、サーバーの実効設定を確認して、変更を元に戻します。以下の例は説明用であり、**VM上で実行して検証した記録ではありません**。各コマンドは指定されたゲストで実行し、物理ホストや文書作成ホストでは実行しないでください。予期しないエラーが出たら停止してください。

両方のゲストで`before-ssh-lesson`という名前のスナップショットを取得します。インストール前に、既存のSSHリスナーとサービス／ソケットの状態を記録してください。パッケージや依存関係の変更を完全に戻すにはスナップショットが必要です。パッケージ削除は厳密な逆操作ではありません。サンプルに合わせるために既存の鍵や設定ファイルを置き換えないでください。

## 1. クライアントとサーバーを確認する

接続を開始する`ssh`コマンドを実行する側が**SSHクライアント**です。接続を待ち受ける側が`sshd`で、通常はTCP 22を使う**SSHサーバー**です。**ホスト鍵**はサーバーに属し、サーバーのアイデンティティを証明します。**ユーザー鍵**は利用者に属し、アカウントを使う権限を証明します。フィンガープリントは公開鍵の短い表現で、信頼できる経路を通じた照合に使えます。

**両方のゲスト、通常ユーザー; まず状態を確認:**

```bash
hostname
cat /etc/os-release
ip -br link
ip -4 -br address
command -v ssh
```

NICのMACアドレスをハイパーバイザー側の記録と照合し、役割ごとのアドレスを確認します。クライアントで`ip -4 route get 192.0.2.20`を実行すると、ラボ用NICと送信元`.10`が選択されるはずです。読み取り方はレッスン2を参照してください。

**Ubuntuサーバー、通常ユーザー; 状態を記録し、不足している場合に限りインストール:**

```bash
dpkg-query -W openssh-server
systemctl status ssh.service ssh.socket --no-pager
```

なければ、`sudo apt update`の後に`sudo apt install openssh-server`を実行します。Ubuntu 24.04では`ssh.socket`によるソケットアクティベーションが使われることがあります。サービス名は引き続き`ssh.service`です。ソケットを無効化せず、サービスとソケットの両方を調べてください。このレッスンでは既存の待受アドレス／ポートを維持するため、ソケットのバインド設定を変更する必要はありません。

**Rockyサーバー、通常ユーザー; 状態を記録し、不足している場合に限りインストール:**

```bash
rpm -q openssh-server
systemctl status sshd.service --no-pager
```

なければ、`sudo dnf install openssh-server`を実行します。Ubuntuクライアントでは`openssh-client`、Rockyクライアントでは`openssh-clients`がツールを提供します。不足していれば、レッスン1のディストリビューション別パッケージ管理手順に従って該当パッケージをインストールしてください。トランザクションを確認し、OpenSSHのためにリポジトリを追加しないでください。

**サーバーで**、ディストリビューションを確認してからサービス変数を1つ設定します。

```bash
# Ubuntu server only:
SSH_UNIT=ssh.service
```

```bash
# Rocky server only:
SSH_UNIT=sshd.service
```

**サーバー、通常ユーザー; 表示にsudoを付ける箇所ではsudoを使う:**

```bash
sudo /usr/sbin/sshd -t
sudo systemctl start "$SSH_UNIT"
systemctl cat "$SSH_UNIT"
systemctl status "$SSH_UNIT" --no-pager
sudo ss -ltnp 'sport = :22'
```

`sshd -t`は設定と鍵の整合性を検査します。成功時は通常、何も表示されません。検証エラーがあれば、起動／再読み込みをしないでください。`start`は現在の実行状態に作用し、起動時の有効化とは別です。`systemctl cat`でユニットと上書き設定を確認できます。この手順は標準の設定パスを前提とします。独自の`ExecStart`／環境オプションで`-f`や`-o`を指定している場合は、以降の検証と実効設定の確認でも同じオプションを指定し、別の設定を検査しないでください。`0.0.0.0:22`／`[::]:22`での待受はラボ用アドレスより広い範囲をカバーしますが、接続元を制限するものではありません。管理アクセスを失うおそれがあるため、ここではネットワークのバインド設定を変更しません。レッスン6で接続元とインターフェイスを制限します。

現在ファイアウォールがラボ接続を遮断している場合は、レッスン6の該当するファイアウォール手順だけを完了し、`.10`から`.20`へのTCP 22を許可してから戻ってください。コンソールアクセスを維持し、ファイアウォールを無効にしないでください。「Connection refused」はリスナー不在または拒否を示すことが多く、タイムアウトはフィルタリングや経路障害を示す場合があります。レッスン4の証拠確認手順に従ってください。

## 2. コンソール経由でサーバーのホスト鍵を検証する

**サーバーのハイパーバイザーコンソール、通常ユーザー; sudoを使う:**

```bash
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

完全な`SHA256:...`フィンガープリントと、これが**ED25519ホスト鍵**であることを記録します。これは公開ホスト鍵であり、後で作るユーザー鍵ではありません。`/etc/ssh/ssh_host_ed25519_key`などの秘密鍵を表示したりコピーしたりしないでください。この方法は一般的な非FIPSゲストを前提とします。暗号ポリシーでEd25519が禁止されている場合は、承認されたアルゴリズムを使う手順が必要です。セキュリティポリシーを無効にしてはいけません。

**クライアント、通常ユーザー:**

```bash
SSH_LAB_DIR=$(mktemp -d "$HOME/network-beginner-ssh.XXXXXX")
printf '%s\n' "$SSH_LAB_DIR"
read -r -p 'Normal account name on the server: ' SERVER_USER
```

ディレクトリとアカウントを記録します。作成に失敗した、出力パスが空、またはアカウントがrootの場合は停止してください。この専用ディレクトリにはコース用の鍵とホスト記録を保存し、既存のクライアント側`~/.ssh`ファイルには触れません。

**クライアント、通常ユーザー:**

```bash
ssh -o HostKeyAlgorithms=ssh-ed25519 \
  -o UserKnownHostsFile="$SSH_LAB_DIR/known_hosts" \
  -o StrictHostKeyChecking=ask \
  "$SERVER_USER@192.0.2.20"
```

初回のホスト鍵確認では、**フィンガープリント全体**をサーバーコンソールの値と照合します。完全一致した場合に限り`yes`と入力してください。一致しなければ停止してVM／アドレスを確認し、ホスト鍵の検査を無効にしたり、保存済み記録を安易に削除したりしないでください。`ssh-keyscan`は鍵を取得できますが、誰が提示した鍵かを単独で証明するものではありません。

パスワードログインが許可されている場合は、**サーバーアカウントのパスワード**を入力します。リモート側で`hostname`、`whoami`、`printf '%s\n' "$SSH_CONNECTION"`を確認し、その後`exit`してクライアントに戻ります。`SSH_CONNECTION`にはクライアントのIP／ポートとサーバーのIP／ポートが入ります。ラボでは`.10`と`.20`が含まれることを確認してください。独立したハイパーバイザーコンソールを使える状態に保ちます。すでにパスワードログインが無効でも、認証が失敗する前にホスト鍵の検証は完了できます。その場合は、パスワードを有効にせず、下記のコンソール経由のインストール方法を使ってください。

## 3. ユーザー鍵を作成し、サーバーの権限を準備する

**クライアント、通常ユーザー、同じシェル:**

```bash
ssh-keygen -t ed25519 -a 64 -f "$SSH_LAB_DIR/id_ed25519" \
  -C "network-beginner-$(basename "$SSH_LAB_DIR")"
ssh-keygen -lf "$SSH_LAB_DIR/id_ed25519.pub"
ls -l "$SSH_LAB_DIR"
```

空でないパスフレーズを2回入力します。これは秘密鍵をディスク上で暗号化するもので、サーバーアカウントのパスワードではありません。`-a 64`は鍵導出処理の反復コストを指定します。`id_ed25519`はクライアントに保管し、サーバーに送るのは`id_ed25519.pub`だけです。専用ディレクトリを使うことで、既存の鍵を誤って置き換えるのを防ぎます。予期しない上書き確認が出たら、yesと答えず停止してください。

インストール前に、`SERVER_USER`で使う**同じ通常サーバーアカウント**の復旧記録を準備します。

**サーバーコンソール、その通常アカウントでログイン:**

```bash
SERVER_NOTE=$(mktemp -d "$HOME/network-beginner-ssh-state.XXXXXX")
printf '%s\n' "$SERVER_NOTE"
stat -c '%a %U %n' "$HOME"
ls -ld "$HOME/.ssh" "$HOME/.ssh/authorized_keys"
```

ディレクトリ作成に失敗した、または出力パスが空の場合は停止します。新しいパスと変更前のホームディレクトリのモードを記録してください。新規アカウントで`.ssh`または`authorized_keys`が「存在しない」のは正常です。どれがなかったか記録します。存在する場合は`stat -c '%a %U %n'`で数値モードを記録し、所有者を確認してください。どちらかがシンボリックリンク、別所有者、想定外のACLを持つ、または別システムが管理している場合は停止します。再帰的に権限を変更せず、所有権の扱いを確認してください。

`authorized_keys`がすでにある場合、**サーバーの通常ユーザー**で`cp -p -- "$HOME/.ssh/authorized_keys" "$SERVER_NOTE/authorized_keys.before"`を実行し、新しいディレクトリにバックアップを作ります。変更前の`.ssh`モードも記録してください。`.ssh`がないときだけ`mkdir -m 700 -- "$HOME/.ssh"`で作成します。このアカウントでは`chmod go-w "$HOME"`と`chmod 700 "$HOME/.ssh"`を使い、元のモードを復元用に記録します。安全でない所有権やグループ／全ユーザー書き込み可能なパスは、OpenSSHの厳格な検査で拒否されます。再帰的な`chmod`を使ったり、他人の鍵を移動したりしないでください。

## 4. 公開鍵をインストールし、鍵だけでのアクセスを実証する

**クライアント、通常ユーザー:**

```bash
ssh-copy-id -i "$SSH_LAB_DIR/id_ed25519.pub" \
  -o UserKnownHostsFile="$SSH_LAB_DIR/known_hosts" \
  -o StrictHostKeyChecking=yes \
  "$SERVER_USER@192.0.2.20"
```

`ssh-copy-id`は既存の認証方法を使い、選択した公開鍵をサーバーアカウントの`~/.ssh/authorized_keys`に追記します。秘密鍵はコピーしません。追加された鍵の数を確認します。1つ追加された、またはすでにインストール済みと表示されるはずです。強制モードで重複追加しないでください。

**パスワード／初期SSHが利用できない場合のコンソール代替手順:** クライアントでは`cat "$SSH_LAB_DIR/id_ed25519.pub"`で公開鍵だけを表示します。サーバーコンソールでは対象ユーザーで`nano "$HOME/.ssh/authorized_keys"`を開き、**公開鍵の1行全体を末尾に追加**して、既存の行は残します。保存後、`ssh-keygen -lf "$HOME/.ssh/authorized_keys"`の結果をクライアントのユーザー鍵フィンガープリントと照合してください。これはステップ2のホスト鍵フィンガープリントとは別です。

**サーバーコンソール、通常の対象ユーザー:**

```bash
chmod 600 "$HOME/.ssh/authorized_keys"
ls -ld "$HOME" "$HOME/.ssh"
ls -l "$HOME/.ssh/authorized_keys"
ssh-keygen -lf "$HOME/.ssh/authorized_keys"
```

対象アカウントが所有者であり、`.ssh`の権限がプライベートで、既存エントリーの中に新しい公開鍵フィンガープリントがあることを確認します。SELinuxがEnforcingのRockyでは、標準ホームパスのラベルが誤っている場合、`sudo restorecon -v "$HOME/.ssh" "$HOME/.ssh/authorized_keys"`も実行します。Unix権限だけではポリシー全体を説明できない理由はレッスン6で扱います。

**クライアント端末A、通常ユーザー; このセッションを開いたままにする:**

```bash
ssh -i "$SSH_LAB_DIR/id_ed25519" -o IdentitiesOnly=yes \
  -o PreferredAuthentications=publickey \
  -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no \
  -o ControlMaster=no -o ControlPath=none \
  -o UserKnownHostsFile="$SSH_LAB_DIR/known_hosts" \
  -o StrictHostKeyChecking=yes "$SERVER_USER@192.0.2.20"
```

秘密鍵のパスフレーズが求められるのは想定どおりです。鍵のみのテストでリモートアカウントのパスワードが求められてはいけません。`IdentitiesOnly`は提示する鍵を制限し、接続共有を無効にすることで、既存の多重化セッションを再利用せず、新しい認証をテストします。

この**リモートサーバーセッション**で`whoami`と`printf '%s\n' "$SSH_CONNECTION"`を実行し、セッションを開いたままにします。次に**クライアント端末B**を開き、記録した正確なクライアントディレクトリを`SSH_LAB_DIR`に、同じアカウントを`SERVER_USER`に設定して、上記の鍵のみログインコマンド全体をもう一度実行します。アカウントと`.10`→`.20`の接続を再確認します。2回目の独立したログインに成功して、初めてこの確認条件を満たします。

すでに**管理用NIC**経由でSSHを使っている場合は、サーバー全体のパスワード認証を無効にする前に、維持が必要なすべての管理アカウント／経路について鍵のみログインを再テストします。既存セッションが残っているだけでは不十分です。必要な経路を検証できなければ、現在の認証ポリシーを維持して準備までで終えてください。NICのIPが変わらなくても、ログインアクセスが維持されるとは限りません。

## 5. 強化する前に設定の優先順位を調べる

**サーバーコンソール、通常ユーザー; sudoを使う:**

```bash
sudo cat /etc/ssh/sshd_config
sudo ls -la /etc/ssh/sshd_config.d
sudo grep -RnsE '^[[:space:]]*(Include|Match|PasswordAuthentication|KbdInteractiveAuthentication|PermitRootLogin|PubkeyAuthentication|AuthenticationMethods|AuthorizedKeysFile)' \
  /etc/ssh/sshd_config /etc/ssh/sshd_config.d
```

`Include`で指定された別のパスも含め、実際に読み込まれるファイルを確認してください。`grep`は補助にはなりますが、完全なパーサーではありません。OpenSSHは通常、キーワードについて**最初に取得した値**を使います。Includeは記述位置で処理され、globに一致したファイル名は辞書順で読み込まれます。該当する`Match`ブロックは、その接続に対してグローバル値を上書きする場合があります。適用されるMatch設定同士では、順序が再び重要になります。後から読み込まれる`99-...conf`が確実な上書き方法とは限りません。

この演習では**新規のグローバル設定専用drop-in**を使います。そのためには、メインファイルのグローバル部分で`/etc/ssh/sshd_config.d/*.conf`のIncludeが有効になっていなければなりません。先行する設定が新しい値を無効にしないか確認してください。このコース用drop-inに`Match`ブロックを入れたり、優先順位を無理に変えるために無関係なIncludeファイルを編集したりしないでください。インストール済みの構成では意図した新規ファイルを使えない場合、アクセスを維持したまま強化手順を止め、設定の所有者／構成を調べてください。

**サーバーコンソール; このシェルで対象アカウントを再設定:**

```bash
read -r -p 'Normal SSH account on this server: ' SERVER_USER
SSH_CASE="user=$SERVER_USER,addr=192.0.2.10,host=net-client,laddr=192.0.2.20,lport=22"
sudo /usr/sbin/sshd -T -C "$SSH_CASE"
```

`-T`は実効設定を表示し、`-C`は仮想接続の条件を渡してMatchルールを評価します。`host`はホスト名一致判定に使う接続元ホストを表し、サーバー自身のホスト名ではありません。このコースではホスト名によるMatchルールを前提にしません。設定で使っている場合は、`sshd`が実際に評価する名前を指定します。`pubkeyauthentication`、`passwordauthentication`、`kbdinteractiveauthentication`、`permitrootlogin`、`authenticationmethods`、`authorizedkeysfile`を確認してください。設定自体が有効でも、`AllowUsers`、`DenyUsers`、グループ制限、PAM、アカウント状態によってログインを拒否される場合があります。

追加変更をする前に実効設定のベースラインを保存します。

```bash
sudo /usr/sbin/sshd -T -C "$SSH_CASE" > "$SERVER_NOTE/effective.before"
sudo /usr/sbin/sshd -T -C \
  'user=root,addr=192.0.2.10,host=net-client,laddr=192.0.2.20,lport=22' \
  > "$SERVER_NOTE/root-effective.before"
```

既存の管理用SSH経路についても、実際の接続元／ローカルアドレスとアカウントを使って同等のベースラインを記録してください。例のアドレスで実際の管理エンドポイントを置き換えないでください。

## 6. 所有するポリシーファイルを1つ追加し、検証・再読み込み・再テストする

2回目の鍵のみログインと必要な管理経路のテストが成功してから進みます。これらの設定は実効Matchルールに従って**サーバー全体の認証**を変更します。NIC設定は変更しません。

**サーバーコンソール、通常ユーザー; sudoを使って排他的に作成:**

```bash
sudo sh -c 'umask 077; set -C; : > /etc/ssh/sshd_config.d/00-network-beginner.conf'
sudoedit /etc/ssh/sshd_config.d/00-network-beginner.conf
```

`set -C`は既存ファイルへの上書きを拒否します。失敗したら停止してください。復旧記録がない以前の試行を編集／削除してはいけません。新しく作ったファイルには、この**設定テキストだけ**を入れます。

```text
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
```

`PasswordAuthentication no`だけでは、パスワードに似たkeyboard-interactive／PAM認証は無効になりません。通常ユーザーの鍵ログインとsudoを維持することで、rootでの直接SSHログインを避けます。PAMをグローバルに無効にしないでください。

**サーバーコンソール、通常ユーザー; sudoを使う:**

```bash
sudo /usr/sbin/sshd -t
sudo /usr/sbin/sshd -T -C "$SSH_CASE"
sudo /usr/sbin/sshd -T -C \
  'user=root,addr=192.0.2.10,host=net-client,laddr=192.0.2.20,lport=22'
```

構文検証に成功し、対象の接続で`pubkeyauthentication yes`、パスワードとkeyboard-interactiveの両方が`no`、`permitrootlogin no`となる場合に限り続行します。必要な管理経路についても実効設定を再確認してください。先行設定やMatchが優先される場合は、**再読み込みしないでください**。新しいファイルだけを削除し、復元後の設定を検証してから優先順位を調べます。ファイル名を無作為に変更しても解決にはなりません。

**サーバーコンソール、通常ユーザー; sudoを使う:**

```bash
sudo systemctl reload "$SSH_UNIT"
systemctl status "$SSH_UNIT" --no-pager
sudo journalctl -u "$SSH_UNIT" -b -n 30 --no-pager
```

再読み込みすると、実行中のデーモンが設定を読み直します。ファイアウォールの再読み込みでも、ソケットバインドの変更でもありません。コンソールと元のセッションを開いたままにし、ステップ4を使って**別の新規クライアント鍵のみログイン**を行い、管理用SSH経路も再確認してください。古い認証済みセッションが残っていても、新しいログインができる証明にはなりません。

## 完了条件と正確な復旧

成功の条件は、ホストフィンガープリントの検証、専用のパスフレーズ保護ユーザー鍵、正しい所有権／権限、強化前の2回目の新規ログイン、該当するアカウント／経路に対する想定どおりの`-T -C`結果、再読み込み**後**の新規ログイン成功です。認証失敗とTCP接続拒否の違いを説明してください。

**サーバーコンソール**からポリシーのロールバックを練習します。

```bash
sudo rm -i -- /etc/ssh/sshd_config.d/00-network-beginner.conf
sudo /usr/sbin/sshd -t
sudo /usr/sbin/sshd -T -C "$SSH_CASE" > "$SERVER_NOTE/effective.restored"
diff -u "$SERVER_NOTE/effective.before" "$SERVER_NOTE/effective.restored"
sudo /usr/sbin/sshd -T -C \
  'user=root,addr=192.0.2.10,host=net-client,laddr=192.0.2.20,lport=22' \
  > "$SERVER_NOTE/root-effective.restored"
diff -u "$SERVER_NOTE/root-effective.before" "$SERVER_NOTE/root-effective.restored"
```

自分で作成したファイルだけが削除対象であることを確認します。差分がなければ、通常アカウントの実効設定はベースラインと一致しています。rootと記録済みの管理経路も確認してください。その間に別の管理者／設定管理ツールが状態を変更した場合は、古いディレクトリ全体を復元せず、差分を調査します。構文と意図した復元値が通った**後に限り**`$SSH_UNIT`を再読み込みし、新規ログインを確認してください。強化後に新しいログインが失敗した場合も、同じコンソール手順が復旧経路です。

強化したコース設定を維持する場合は、同じ検証条件を通したうえで、自分が作成したdrop-inを再適用できます。それ以外の場合は、次の順序で片付けます。

1. **サーバーの対象アカウント:** `~/.ssh/authorized_keys`をnanoで開き、コース用コメントと記録済みユーザー鍵フィンガープリントで特定した鍵の1行だけを削除します。無関係な鍵はすべて残します。存在していた場合は`"$SERVER_NOTE/authorized_keys.before"`と比較します。記録した数値モードを戻してください。元々ファイルがなく、現在空なら、その空ファイルだけを削除します。`.ssh`を削除できるのは、自分で作成し、空である場合だけです。元々存在したホーム／`.ssh`の記録済みモードを戻します。共有アカウントでは、バックアップで上書きせず、並行した変更を確認してください。
2. **クライアント:** コースセッションを閉じ、公開鍵を失効させてから、記録した`SSH_LAB_DIR`内の`id_ed25519`、`id_ed25519.pub`、`known_hosts`だけを`rm -i`で削除し、その後`rmdir "$SSH_LAB_DIR"`を実行します。余分なファイルがあれば名前を確認し、再帰削除はしないでください。既存のクライアントSSHファイルは置き換えていません。
3. **サーバー:** 検証後、`SERVER_NOTE`内でこのレッスン用に作成したベースライン／バックアップファイルだけを削除し、空になったディレクトリを削除します。作成した管理用ベースラインのファイル名も記録し、明示的に片付けられるようにします。
4. 変更しており、後続レッスンでSSHが不要な場合に限り、**記録した**サービス／ソケットの実行時状態を戻します。Ubuntuで元々ソケットアクティベーションが有効だった場合は、そのソケットを維持してください。サービスが当初停止していたという理由だけでソケットを無効化してはいけません。新規インストールしたパッケージは後続レッスン用に残しても構いません。パッケージ変更まで完全に戻すにはスナップショットを使いますが、それ以降のゲスト作業も破棄されます。

## 主な参考資料

2026年9月15日確認:

- [Ubuntu Server OpenSSH](https://documentation.ubuntu.com/server/how-to/security/openssh-server/): インストール、`ssh.service`、Includeの優先順位。
- [Ubuntu 24.04リリースノート](https://discourse.ubuntu.com/t/noble-numbat-release-notes/39890): OpenSSHのソケットアクティベーションとソケット設定ジェネレーター。
- [Rocky LinuxのOpenSSH鍵設定](https://docs.rockylinux.org/9/guides/security/ssh_public_private_keys/): RockyでのOpenSSH手順。
- [OpenSSH `ssh`](https://man.openbsd.org/ssh)、[`ssh-keygen`](https://man.openbsd.org/ssh-keygen)、[`sshd`](https://man.openbsd.org/sshd)、[`sshd_config`](https://man.openbsd.org/sshd_config): アイデンティティ、鍵、検証、Include／Match、実効設定。
- [Ubuntu 24.04 `ssh-copy-id`](https://manpages.ubuntu.com/manpages/noble/man1/ssh-copy-id.1.html): 選択した鍵のインストールと既存鍵の扱い。

[クイズ](../../quizzes/networking/beginner/05-ssh-access-quiz.md) | [ホストセキュリティへ進む](06-firewalls-host-security.md)
