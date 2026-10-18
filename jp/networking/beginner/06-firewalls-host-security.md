# 6. ファイアウォール、SELinux、制限付き SSH 保護

> **対応バージョン**: Ubuntu Server 24.04 LTS (主対象)、Rocky Linux 9 (代替)
> **最終更新日**: 2026年9月15日

[前へ: SSH](05-ssh-access.md) | [コース](README.md) | [クイズ](../../quizzes/networking/beginner/06-firewalls-host-security-quiz.md) | [次へ: 監視](07-monitoring-performance.md)

アプリケーションが待ち受けていてもファイアウォールが接続を拒否する場合があります。接続を受け付けても、ファイルを読む権限がないこともあります。このレッスンでは、ネットワークポリシー、プロセス/ファイルポリシー、認証失敗が繰り返された場合の対応を分けて扱います。

## 前提条件と学習目標

レッスン1～5で使った、コンソールからアクセスできる使い捨てゲスト2台を使用します。クライアントは `192.0.2.10/24`、サーバーは `192.0.2.20/24` です。内部専用ラボ NIC には DHCP/アップリンクがなく、別の NAT/DHCP 管理 NIC は変更しません。TCP 22 がブロックされているためレッスン5からここに進んだ場合は、選択したファイアウォール分岐だけを完了してレッスン5に戻ってください。その分岐を実施する前提として、SSH の完全な強化は必要ありません。

指定した IPv4 クライアントからサーバーの TCP ポート **22 と 8000** への接続を許可し、実際に適用されるポリシーを確認して、保存済みルールと実行時ルールを区別します。自分が加えた変更だけを元に戻し、スクラッチファイル1つに意図的に付けた誤った SELinux ラベルを修復します。必要に応じて、範囲を限定した Fail2ban jail も設定します。変更にはサーバーのコンソールを使い、接続テストにはクライアントを使います。コマンドと出力の例はすべて説明用であり、**実際の VM で検証した結果ではありません**。

サーバーのスナップショット `before-host-security` を作成します。既存のファイアウォール/実行時状態と、管理用 SSH 経路を記録します。既存の管理主体に応じて、**Ubuntu では UFW、Rocky では firewalld のどちらか一方**を選びます。競合する管理ツールをインストール/有効化したり、ルールをフラッシュしたり、テストに通すためにセキュリティサービスを無効化したりしないでください。これは IPv4 のラボ用ポリシーであり、IPv6 リスナーの完全なポリシーでも、本番環境のセキュリティ強化チェックリストでもありません。

## 1. 通信方向と管理主体を確認する

**インバウンド**とは、このサーバー宛てのトラフィックです。たとえば、新しい SSH 接続が該当します。**アウトバウンド**は、パッケージリポジトリへの要求など、サーバーが生成するトラフィックです。**転送**されるトラフィックは、サーバーを経由して別のホストに向かいます。このサーバーはルーターではありません。転送、NAT、デフォルトルートの変更は不要です。

ステートフルファイアウォールは通信を追跡し、確立済み接続への応答を通常は許可します。そのため、既存の SSH セッションが維持されていても、新しいインバウンド接続が許可されている証明にはなりません。ファイアウォールの許可ルールを追加しても、待ち受けるプログラムが起動するわけではありません。

**サーバー、一般ユーザー。状態の確認のみ:**

```bash
hostname
cat /etc/os-release
ip -br link
ip -4 -br address
ip -4 route
systemctl is-active ufw firewalld
```

ユニットが存在しない/非アクティブであっても、障害とは限りません。UFW では、強制適用が有効かどうかを UFW 自身の `status` で確認します。systemd のユニットだけでは判断できません。Docker、Kubernetes、独自の nftables/iptables ルール、または別のポリシー管理ツールがある場合は、簡略化したこのポリシーがマシン全体を管理していると決めつけず、コース用のクリーンな VM を使ってください。

**サーバー、一般ユーザー。ハイパーバイザーの MAC アドレスと照合してから名前を入力:**

```bash
read -r -p 'Server lab NIC verified by MAC: ' LAB_IF
read -r -p 'Server management NIC verified by MAC: ' MGMT_IF
ip -br link show dev "$LAB_IF"
ip -br link show dev "$MGMT_IF"
FW_NOTE=$(mktemp -d "$HOME/network-beginner-firewall.XXXXXX")
printf '%s\n' "$FW_NOTE"
```

ディレクトリが作成されなかった、名前が空/同一、または MAC アドレスが一致しない場合は中止します。値はシェルの外に記録します。`LAB_IF` が `.20/24` を持つことを確認し、管理用のベースラインを保存します。

```bash
ip -4 -br address show dev "$MGMT_IF" > "$FW_NOTE/management.before"
ip -4 route > "$FW_NOTE/routes.before"
```

## 2A. Ubuntu: UFW

この分岐は、UFW が既存の管理主体であるゲストでのみ実行します。UFW がなければ、ゲストのパッケージ準備手順でインストールしておきます。有効か無効かを記録します。

**Ubuntu サーバー、sudo を実行する一般ユーザー:**

```bash
sudo ufw status verbose
sudo ufw status numbered
sudo ufw show added
sudo ufw show raw
sudo cat /etc/default/ufw
sudo ufw show added > "$FW_NOTE/ufw-added.before"
```

ローカルの `/etc/ufw/before.rules`、`after.rules` と対応する IPv6 ファイルを確認します。先に評価される独自の accept ルールが、以下のユーザールールによる制限を迂回する場合があります。理解できる標準ルールがあり、競合する独自ポリシーがない場合にのみ続行します。一般的な `allow 22/tcp` は今回の目的より広い送信元を許可します。制限付き許可を追加するだけでは、その広い許可は取り消されません。

UFW が**無効**の場合、最初に有効化するには、受信のデフォルトが deny、送信のデフォルトが allow、標準の DHCP/応答処理があること、さらに**開いたファイアウォールを必要とする既存のインバウンド管理サービスがないこと**が条件です。コンソールとアウトバウンド NAT/DHCP 管理があれば、この条件に該当します。既存の管理 SSH/インバウンドサービスへの到達性を維持する必要がある場合、有効化する前に既に承認された範囲限定ポリシーを保持してください。広い管理許可を新たに設けたり、コンソールでのテストが SSH を検証すると考えたりしてはいけません。条件が不明なら、ポリシーが確定するまで UFW を無効のままにします。

クライアントからの SSH と HTTP それぞれに許可を加え、その後、同じラボエンドポイントへの deny を追加します。順序は**SSH 許可、HTTP 許可、ラボの deny**で、通常の広いユーザールールより前に配置します。3つとも対象はラボ NIC に限定します。別々の許可にすることで、[総合演習のファイアウォール課題](08-container-cloud-capstone.md#firewall-fault)では、SSH 許可を残したまま HTTP 許可を取り除けます。

**Ubuntu サーバー、sudo を実行する一般ユーザー:**

```bash
sudo ufw insert 1 allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 22 comment 'network-beginner-ssh'
sudo ufw insert 2 allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 8000 comment 'network-beginner-http'
sudo ufw insert 3 deny in on "$LAB_IF" proto tcp \
  from any to 192.0.2.20 port 22,8000 comment 'network-beginner-other'
sudo ufw show added
```

コマンドが失敗した場合は中止し、正常に追加できたルールだけに対して、以下の正確な削除操作を使います。同一のルールが既にある場合、重複して追加してはいけません。この演習より前から存在したかを記録し、元の構成の管理下にあるものはそのままにします。

UFW が無効で、上記の有効化条件を満たした場合は、**サーバーのコンソール上で** `sudo ufw enable` を実行します。`--force` は使わず、警告を読んでください。すでに有効なら、ルール変更は直ちに適用されます。

**Ubuntu サーバー、sudo を実行する一般ユーザー:**

```bash
sudo ufw status numbered
sudo ufw status verbose
sudo ufw reload
sudo ufw status numbered
```

同一インターフェイス/宛先を対象とする deny より前に、2つの送信元限定許可が前述の順番で並び、再読み込み後も保持されることを確認します。この方法で追加した UFW ルールは保存と適用が同時に行われます。この手順では firewalld のようなルール単位の実行時/`--permanent` の分離やタイムアウトはありません。ルール番号はその時点の一覧内での位置に過ぎないため、後でクリーンアップするときは元のルール指定を使います。

以下の共通テストを実施します。**このレッスン全体のクリーンアップ**としてこれらのルールだけを元に戻す場合は、Ubuntu サーバーのコンソールから次を実行します。

```bash
sudo ufw delete allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 22
sudo ufw delete allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 8000
sudo ufw delete deny in on "$LAB_IF" proto tcp \
  from any to 192.0.2.20 port 22,8000
sudo ufw show added
```

これは**レッスン全体をクリーンアップするための**3つの逆操作です。HTTP だけの障害を再現するときに実行する3つのコマンドではありません。自分のルールだけであることを確認します。演習のために無効だった UFW を有効にし、元の状態に戻す場合は、保存済みルールを削除**した後で** `sudo ufw disable` を実行します。もともと有効だったファイアウォールは無効にしないでください。`ufw-added.before` と比較します。レッスン7～8でコースのポリシーを使う場合は、クリーンアップしたままにせず、3つのルールを元の順番で再適用し、もう一度検証します。

## 2B. Rocky: firewalld とラボ専用ゾーン

この分岐は、firewalld が既存かつ有効な管理主体の場合にのみ使います。**ゾーン**は、関連付けられたインターフェイス/送信元のポリシーをまとめます。NetworkManager の接続でゾーンを指定していない場合、firewalld のデフォルトゾーンが使われます。そこでは SSH がすでに広く許可されている可能性があります。そのゾーンに制限付き許可を追加しても、既存の許可は制限されません。

**Rocky サーバー、ファイアウォールを確認するため sudo を実行する一般ユーザー:**

```bash
sudo firewall-cmd --state
sudo firewall-cmd --get-default-zone
sudo firewall-cmd --get-active-zones
sudo firewall-cmd --list-all-zones
sudo firewall-cmd --permanent --list-all-zones
sudo firewall-cmd --list-all-policies
sudo firewall-cmd --permanent --list-all-policies
sudo firewall-cmd --direct --get-all-rules
sudo firewall-cmd --list-all-zones > "$FW_NOTE/firewalld-runtime.before"
sudo firewall-cmd --permanent --list-all-zones > "$FW_NOTE/firewalld-permanent.before"
nmcli -f NAME,UUID,TYPE,DEVICE connection show --active
```

2つの NIC の有効ゾーンとデフォルトゾーンを記録します。送信元バインディング、ポリシー、rich rule、独自の direct rule も確認します (direct の照会は以前からある設定の確認であり、作成を推奨するものではありません)。これらは、インターフェイスのゾーン表示だけではわからない分類や許可動作を変える場合があります。この新規 VM 向け手順では、競合する送信元バインディング/ポリシーがなく、再読み込みで失われる無関係な実行時変更もないことが前提です。不明な変更を保存するために `--runtime-to-permanent` を使わないでください。

レッスン3で作成した、**ラボ専用**の有効な NetworkManager プロファイルの UUID を調べます。管理用プロファイルや共有プロファイルは決して選ばないでください。

**Rocky サーバー、一般ユーザー:**

```bash
read -r -p 'Active lab-only connection UUID: ' LAB_UUID
nmcli connection show uuid "$LAB_UUID"
LAB_OLD_ZONE=$(nmcli -g connection.zone connection show uuid "$LAB_UUID")
printf '%s\n' "$LAB_OLD_ZONE" > "$FW_NOTE/lab-zone.before"
```

プロファイルの NIC/MAC アドレスと `.20/24` を確認します。以前のゾーンが空であることもあり得ます。その場合は空欄の値を正確に記録します。実行時と永続設定の両方で、`network-beginner` が既にゾーン一覧にあるか調べます。既に存在する場合は中止し、他の人のゾーンを再利用したり削除したりしないでください。

**Rocky サーバー、sudo を実行する一般ユーザー:**

```bash
sudo firewall-cmd --permanent --new-zone=network-beginner
sudo firewall-cmd --check-config
sudo firewall-cmd --reload
```

この手順で実行時に使うには、新しいゾーンを永続設定に定義してから読み込む必要があります。再読み込みすると実行時ポリシーが永続設定で置き換わります。そのため、無関係な実行時変更を先に解消する必要があります。この段階では、インターフェイスをまだ移動していません。

送信元、宛先、TCP ポートを指定する2つの正確な rich-rule 文字列を設定します。ゾーンを `LAB_IF` に関連付けることで、インターフェイスの境界が加わります。

**Rocky サーバー、一般ユーザー:**

```bash
RULE22='rule family="ipv4" source address="192.0.2.10/32" destination address="192.0.2.20/32" port port="22" protocol="tcp" accept'
RULE8000='rule family="ipv4" source address="192.0.2.10/32" destination address="192.0.2.20/32" port port="8000" protocol="tcp" accept'
```

**Rocky サーバー、sudo を実行する一般ユーザー。10分間の実行時テスト:**

```bash
sudo firewall-cmd --zone=network-beginner --add-rich-rule="$RULE22" --timeout=600
sudo firewall-cmd --zone=network-beginner --add-rich-rule="$RULE8000" --timeout=600
sudo nmcli connection modify uuid "$LAB_UUID" connection.zone network-beginner
sudo firewall-cmd --get-zone-of-interface="$LAB_IF"
sudo firewall-cmd --get-zone-of-interface="$MGMT_IF"
sudo firewall-cmd --zone=network-beginner --list-all
sudo firewall-cmd --permanent --zone=network-beginner --list-all
```

NetworkManager の `connection.zone` を変更すると、有効な接続には直ちに反映されます。選択したプロファイルのファイアウォールゾーンだけが変わり、IP/DHCP/ゲートウェイは変わりません。空の新しいゾーンに `LAB_IF` が入り、これら2つの rich accept だけがあること、管理用 NIC が元のゾーンにあることを確認します。新しいゾーンには広範な `ssh` サービスや `trusted`/ACCEPT ターゲットはありません。許可されていない新規 TCP 接続はデフォルトで拒否されますが、ICMP など他のプロトコルの扱いは別のポリシーです。

テストルールは実行時設定にだけ存在します。600秒後に期限切れとなり、再読み込みでも失われます。ただし、ゾーン/プロファイルの関連付けは解除されません。コンソールからの復旧が不可欠です。`--timeout` と `--permanent` を併用しないでください。この試用期間中に共通テストを実施します。

ポリシーを保持する場合は、**Rocky サーバー、sudo を実行する一般ユーザー**として次を実行します。

```bash
sudo firewall-cmd --permanent --zone=network-beginner --add-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --add-rich-rule="$RULE8000"
sudo firewall-cmd --check-config
sudo firewall-cmd --reload
sudo firewall-cmd --zone=network-beginner --list-rich-rules
sudo firewall-cmd --permanent --zone=network-beginner --list-rich-rules
```

途中で無関係な実行時変更を加えていない場合にのみ続行します。再読み込み後、保存済みルール文字列と実行時ルール文字列が一致することを確認し、新しい SSH/HTTP 接続をもう一度テストします。

**元に戻す**場合は、Rocky サーバーのコンソールで作業する前に、下記のオプション Fail2ban jail を停止します。jail がこのゾーンにルールを追加することがあるためです。まず、記録しておいたプロファイルのゾーン (空欄の場合も含む) を戻します。

```bash
sudo nmcli connection modify uuid "$LAB_UUID" connection.zone "$LAB_OLD_ZONE"
sudo firewall-cmd --get-zone-of-interface="$LAB_IF"
sudo firewall-cmd --get-zone-of-interface="$MGMT_IF"
```

自分が追加したルールのうち、どれが残っているか調べます。**Rocky サーバーのコンソール、sudo:**

```bash
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE8000"
```

`yes` はルールが存在することを示します。`no` と非ゼロの終了ステータスは、試用期間のタイムアウト後など、ルールが存在しないことを示します。自分が追加したルールのうち存在するものに対応する削除だけを実行してください。

```bash
sudo firewall-cmd --zone=network-beginner --remove-rich-rule="$RULE22"
sudo firewall-cmd --zone=network-beginner --remove-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --remove-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --remove-rich-rule="$RULE8000"
```

最後に、次を実行します。

```bash
sudo firewall-cmd --permanent --delete-zone=network-beginner
sudo firewall-cmd --check-config
sudo firewall-cmd --reload
```

自分が作成した未使用のゾーンだけを削除します。無関係な実行時状態に問題がない場合に限り、再読み込みを行います。プロファイルが元のゾーンにあること、デフォルトゾーン、管理用ゾーン/アドレス、ベースラインポリシーを比較します。レッスン7～8を続ける場合は、検証済みの保存済みラボゾーンを残します。ロールバック後に再試行する場合は、同じ試用/検証手順をやり直します。

## 3. クライアントから確認し、証拠の範囲を限定する

レッスン5と同様に、クライアントから**新しい鍵限定 SSH 接続**を使います。既存セッションは新しいルールのテストになりません。TCP 8000 のテストでは、前の HTTP レッスンで用意した `python3` が使えること、ほかのサービスがそのポートを使用していないことを確認します。

**サーバーコンソール A、一般ユーザー:**

```bash
WEB_DIR=$(mktemp -d "$HOME/network-beginner-fw-web.XXXXXX")
printf '%s\n' "$WEB_DIR"
```

パスを記録します。空、または失敗した場合は中止します。続けて次を実行します。

```bash
printf 'firewall lesson\n' > "$WEB_DIR/index.html"
timeout 120 python3 -m http.server 8000 --bind 192.0.2.20 --directory "$WEB_DIR"
```

これはスクラッチディレクトリだけを対象とし、ラボ用 IPv4 アドレスにバインドして最大2分間提供します。ここにシークレットやシンボリックリンクを置かないでください。**サーバーコンソール B**で `sudo ss -ltnp 'sport = :8000'` を実行し、`.20:8000` が表示されることを確認します。

**クライアント、一般ユーザー:**

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/
```

HTTP 200 と本文中の `firewall lesson` を確認します。テストに失敗しても、広い許可を追加してはいけません。リスナー、ルート、ゾーン/インターフェイス、送信元、ログの順に確認します。想定した送信元制限が設定されていることを構成から確認してください。許可されたクライアントから成功しただけでは、ほかのすべての送信元が拒否されることをテストしたことにはなりません。localhost/サーバー自身からのテストも、外部の拒否対象クライアントによるテストではありません。

サーバーのタイムアウト後 (ステータス 124 は正常)、または Ctrl+C で中断した後に、**サーバーコンソール A、一般ユーザー**として `rm -i -- "$WEB_DIR/index.html"` を実行し、その後 `rmdir -- "$WEB_DIR"` を実行します。管理用アドレス/ルートが `FW_NOTE` と一致すること、および必要な場合は新しい管理用 SSH ログインも確認します。DHCP 更新の時刻は別の要因で変わる場合があります。

## 4. Rocky SELinux: ポリシー全体ではなくラベルを修復する

SELinux は、Unix の所有者/モードやファイアウォールとは別にプロセス/リソースのポリシーを適用します。**Enforcing** はポリシーを適用し、拒否を記録します。**Permissive** は強制適用せず、拒否されるはずのアクセスを記録します。**Disabled** は SELinux による強制適用がありません。このラボではモードを切り替えません。Ubuntu は通常 AppArmor を使います。この代替手順を実行するためだけに SELinux をインストールしたり切り替えたりしないでください。

**Rocky サーバー、一般ユーザー。監査ログに sudo でアクセス:**

```bash
getenforce
sestatus
ls -Z "$HOME"
sudo ausearch -m AVC,USER_AVC -ts recent -i
```

SELinux が有効な状態で準備されたゲストで、この演習を行います。無効なら、稼働中のシステム全体を再ラベルするのではなく、正しく準備されたスナップショットに戻ってください。`ausearch` を使うには `audit` ツールが必要です。一致がないというのは、その期間に保持された監査記録に該当項目がないという意味であり、ポリシーがアクセスを拒否し得ない証拠ではありません。

AVC レコードは、要求された権限、プロセス、オブジェクト、送信元コンテキスト (`scontext`)、対象コンテキスト (`tcontext`) を特定します。実行ファイル/パスと時刻をあわせて確認します。SELinux コンテキストは通常 `user:role:type:level` 形式で、**type** が targeted policy の中心です。すべての拒否を `audit2allow` にそのまま渡さないでください。誤ったラベルやアプリケーションパスが原因の場合もよくあります。

**Rocky サーバー、一般ユーザー。専用スクラッチファイルを1つ作成:**

```bash
SEL_DIR=$(mktemp -d "$HOME/network-beginner-selinux.XXXXXX")
printf '%s\n' "$SEL_DIR"
```

失敗した場合は中止して正確なパスを記録し、続けて次を実行します。

```bash
touch "$SEL_DIR/probe.txt"
ls -Z "$SEL_DIR/probe.txt"
matchpathcon "$SEL_DIR/probe.txt"
sudo restorecon -v "$SEL_DIR/probe.txt"
matchpathcon -V "$SEL_DIR/probe.txt"
```

ポリシー検索により、このパスで期待されるコンテキストがわかります。まずベースラインを確認します。すべてのホームディレクトリで同じ type を使うと決めつけないでください。続いて、ファイルに既存の別 type を意図的に設定し、修復します。

**Rocky サーバー、指定箇所で sudo を実行する一般ユーザー:**

```bash
sudo chcon -t httpd_sys_content_t "$SEL_DIR/probe.txt"
ls -Z "$SEL_DIR/probe.txt"
sudo restorecon -n -v "$SEL_DIR/probe.txt"
sudo restorecon -v "$SEL_DIR/probe.txt"
matchpathcon -V "$SEL_DIR/probe.txt"
```

`chcon` はこのファイルのラベルを変更しますが、永続的なファイルコンテキストルールは作りません。`restorecon -n` は変更せずにプレビューし、`restorecon` はポリシーで定義されたパスのラベルを復元します。最後の検証でポリシーと一致することを確認します。親ディレクトリが専用であるため、これはラベルの演習であり、Web コンテンツのデプロイではありません。閉じ込められたアプリケーションからこのファイルへ意図的にアクセスしていないので、AVC が発生するとは限りません。

永続的な独自パスでは、`restorecon` の前に範囲を限定した `semanage fcontext` マッピングが必要な場合がありますが、この演習では不要です。**Rocky サーバー、一般ユーザー**として、クリーンアップに `rm -i -- "$SEL_DIR/probe.txt"` と `rmdir -- "$SEL_DIR"` を実行します。`chcon` の後に演習が中断している場合は、クリーンアップ前に同じ対象を指定した `restorecon` を実行します。このファイルのために SELinux 全体を無効化したり、ファイルシステム全体を再ラベルしたりしないでください。

## 5. オプションのパッケージと Rocky 9 の EPEL/CRB {#epel-prerequisites}

Fail2ban や `iftop` がなくても、ファイアウォール/SELinux の本編は完了できます。この節では、レッスン7のオプション `iftop` 手順で参照する Rocky の前提条件も扱います。パッケージのインストールは、管理用接続を使って**使い捨てゲスト内だけで**行います。

**Ubuntu サーバー**では、まず `apt-cache policy fail2ban python3-systemd` を確認します。設定済みの Ubuntu リポジトリに候補があれば、`sudo apt update` の後で `sudo apt install fail2ban python3-systemd` を実行すると、Fail2ban とその journal バックエンドが入ります。候補がなければ、無関係なダウンロード元を追加するのではなく、公式リポジトリのコンポーネント設定を調べます。

**Rocky 9** では、EPEL は Enterprise Linux 向けの Fedora 追加リポジトリであり、依存関係を CRB が提供します。EPEL Next や異なるメジャーバージョンの EL を使ったり、パッケージ署名の検証を無効にしたりする理由にはなりません。

**Rocky ゲスト、一般ユーザー。リポジトリ/パッケージの元の状態を記録:**

```bash
dnf repolist --all
rpm -q epel-release dnf-plugins-core fail2ban-server python3-systemd
```

CRB/EPEL が既に有効か、どのパッケージが既に入っていたかを記録し、スナップショット `before-optional-packages` を作成します。その後、**Rocky ゲスト、sudo を実行する一般ユーザー**として次を実行します。

```bash
sudo dnf install dnf-plugins-core
sudo dnf config-manager --set-enabled crb
sudo dnf install epel-release
dnf repolist --enabled
dnf info fail2ban-server python3-systemd iftop
```

EPEL が **9** に対応していること、想定したリポジトリ/署名を使っていること、ゲストのアーキテクチャ向けに候補があることを確認します。Fail2ban を使う場合は `sudo dnf install fail2ban-server python3-systemd` を実行し、オプションのレッスン7ツールを使う場合は `iftop` だけをインストールします。トランザクションを確認し、未解決の依存関係があれば中止します。パッケージバージョンは変わるため、特定のビルドは前提にしません。

演習より前から CRB/EPEL が有効だった場合や、インストール済みソフトウェアが必要としている場合は、無効にしないでください。一時的な試用だけが目的なら、依存するレッスンをすべて終えてから `before-optional-packages` に戻します。これはパッケージ/リポジトリに対する正確なロールバックです。リポジトリだけを無効にしても、インストール済みパッケージは元に戻りません。

## 6. ラボに範囲を限定したアクションを使うオプション Fail2ban jail

Fail2ban は**フィルター**で認証失敗ログを読み取り、`findtime` の期間内にイベント数を数え、`maxretry` に達すると**アクション**を実行します。**jail** はそれらの設定を組み合わせたものです。弱い鍵を修正したり、ファイアウォールのベースラインポリシーを置き換えたり、分散型/低速のあらゆる攻撃を止めたりするものではありません。フィルター/バックエンドが誤っていると、サービスが稼働していても何も検出しないことがあります。

このオプション設定は、独自 jail がない**新規 Fail2ban インストール**を前提とします。既に使われている場合は、既存の所有者/構成を先に確認し、ほかのワークロードの保護を停止しないでください。開始時点のサービス/自動起動状態を記録します。新規インストールでは自動起動することがあります。準備中はコンソールで、このために新しく導入したサービスだけを `sudo systemctl stop fail2ban` で停止します。`/etc/fail2ban/jail.conf`、`jail.d`、インストールされたアクションを確認します。パッケージが提供する `jail.conf` は編集しないでください。

選択した管理ツール用の新しいアクションファイルを**1つだけ**作成し、既存ファイルの上書きを拒否します。

**サーバー、sudo を実行する一般ユーザー:**

```bash
sudo sh -c 'umask 077; set -C; : > /etc/fail2ban/action.d/network-beginner.conf'
sudoedit /etc/fail2ban/action.d/network-beginner.conf
```

**UFW の場合のみ**、新しいファイルに次の INI を入れます。`REPLACE_WITH_LAB_NIC` を MAC アドレスで照合済みのサーバー NIC 名に置き換えます。プレースホルダーを残さないでください。

```ini
[Definition]
actionstart =
actionstop =
actioncheck = LC_ALL=C ufw status | grep -q 'Status: active'
actionban = ufw insert 1 deny in on REPLACE_WITH_LAB_NIC proto tcp from <ip> to 192.0.2.20 port 22 comment 'network-beginner-ban'
actionunban = ufw delete deny in on REPLACE_WITH_LAB_NIC proto tcp from <ip> to 192.0.2.20 port 22
```

**firewalld の場合のみ**は、代わりにこちらを使います。コース用ゾーンは引き続きラボ NIC 専用にしてください。

```ini
[Definition]
actionstart =
actionstop =
actioncheck = firewall-cmd --zone=network-beginner --list-all
actionban = firewall-cmd --zone=network-beginner --add-rich-rule='rule family="ipv4" priority="-10" source address="<ip>" destination address="192.0.2.20/32" port port="22" protocol="tcp" reject'
actionunban = firewall-cmd --zone=network-beginner --remove-rich-rule='rule family="ipv4" priority="-10" source address="<ip>" destination address="192.0.2.20/32" port port="22" protocol="tcp" reject'
```

これらのアクションでは検出された送信元に対し、**ラボのインターフェイス/ゾーン、宛先 `.20`、TCP 22** に限定します。管理用アドレスや TCP 8000 に対するその送信元の接続を禁止しません。UFW では許可の前に挿入し、firewalld では負の優先度を使うことで、一時的な deny をラボの許可より先に評価します。Fail2ban 自身が `bantime` 後にルールを削除します。このオプションの演習中に、下位のファイアウォールを再読み込みしないでください。このタイマーを管理するのは UFW ルールではなく Fail2ban です。デーモンが失敗した場合は、期限切れになったと思い込まず、正確な `actionunban` 指定を使い、残っているコース用 ban だけを調べて削除します。

**サーバー、sudo を実行する一般ユーザー。専用 jail を作成:**

```bash
sudo sh -c 'umask 077; set -C; : > /etc/fail2ban/jail.d/99-network-beginner.local'
sudoedit /etc/fail2ban/jail.d/99-network-beginner.local
```

**Ubuntu** では次の INI を使います。**Rocky** では `journalmatch` の `ssh.service` だけを `sshd.service` に置き換えます。

```ini
[sshd]
enabled = false

[network-beginner-sshd]
enabled = true
filter = sshd
backend = systemd
journalmatch = _SYSTEMD_UNIT=ssh.service
usedns = no
ignoreip = 127.0.0.0/8 ::/0
port = 22
maxretry = 3
findtime = 60
bantime = 60
action = network-beginner
```

`[sshd]` 設定により、この**新規**インストールにパッケージ付属のデフォルト SSH jail が適用され、より広いアクションが二重に実行されるのを防ぎます。有効な jail がほかにないことを確認してください。既存の独自保護を無効にするために使ってはいけません。名前を指定した jail は `sshd` フィルターと新しいアクションを明示的に使用します。`backend=systemd` は journal を読むため、`logpath` は追加しません。`journalmatch` は実際のログユニットのメタデータに一致させる必要があります。`::/0` はこの IPv4 専用デモから IPv6 を意図的に除外しています。本番用の保護ポリシーではありません。

**サーバー、sudo を実行する一般ユーザー。起動前に検証:**

```bash
sudo journalctl -u ssh.service -b -n 10 -o verbose --no-pager
sudo fail2ban-client -t
sudo fail2ban-client -d
```

Rocky では `-u sshd.service` を使います。実際の認証関連レコードの `_SYSTEMD_UNIT` を調べます。一致するレコードがなければ、バックエンドが対象ログを取得できていることは未検証です。`-t` は構成をテストし、`-d` は強制適用を起動せずに解釈済み構成を表示します。jail 名、journal バックエンド/マッチ条件、想定したアクションが1つだけであること、期間が制限されていること、競合する有効化済み jail がないことを確認します。

**サーバー、sudo を実行する一般ユーザー:**

```bash
sudo systemctl start fail2ban
sudo fail2ban-client status
sudo fail2ban-client status network-beginner-sshd
sudo fail2ban-client get network-beginner-sshd journalmatch
sudo fail2ban-client get network-beginner-sshd actions
sudo fail2ban-client get network-beginner-sshd action network-beginner actionban
sudo journalctl -u fail2ban -b -n 30 --no-pager
```

意図した jail と、展開済みの範囲限定アクションコマンドが表示され、起動エラーがないことを確認します。失敗/ban が0件でも正常です。**総当たりループを実行したり、自分自身を意図的に ban したりしないでください。** これらの確認で検証できるのは構成と起動までであり、攻撃の検知や適用が実証されたわけではありません。サービスのメタデータが誤っている、Python の journal サポートがない、フィルターに一致しない、またはアクション実行エラーがある場合は、保護が動作すると判断する前に解決する必要があります。

既知のラボクライアントが誤って ban 一覧に載った場合は、**サーバーコンソール、sudo** で次を実行します。

```bash
sudo fail2ban-client set network-beginner-sshd unbanip 192.0.2.10
sudo fail2ban-client status network-beginner-sshd
```

これは指定した単一 IP の unban を要求します。対応する UFW/rich rule が存在しないことと、新しい SSH 接続が成功することを確認します。既存セッションでは不十分です。ban やファイアウォールルール全体をフラッシュしないでください。

クリーンアップでは、この jail に実際に表示されているアドレスだけを1つずつ unban し、アクションのルールが削除されたことを確認します。その後 `sudo fail2ban-client stop network-beginner-sshd` を実行します。サービスを停止するのは、元々非アクティブだった場合、または今回新たに導入した場合だけです。さらに、ここで作成した2つのファイルだけを `sudo rm -i -- /etc/fail2ban/jail.d/99-network-beginner.local /etc/fail2ban/action.d/network-beginner.conf` で削除します。jail がなくなり、コース用 ban が残っていないことを確認します。**firewalld のゾーンを削除する前に**行ってください。記録したサービス/自動起動の状態に戻します。オプションパッケージ全体を元に戻す場合はスナップショットを使います。

## 完了確認とコースの続き

選択した管理ツール、正しいインターフェイス/ゾーン、`.10` から `.20` への TCP 22/8000 の正確なルール、新しい許可対象 SSH/HTTP 接続、変更されていない管理経路、および逆操作を提示できる状態にします。UFW の保存済みルールと firewalld の実行時/永続ルールの違い、正しいファイルモードと正しい SELinux type の違いを説明してください。追加の検証済み証拠がない限り、オプション Fail2ban は「構成を検証済み」と報告します。

検証済みで送信元を限定した**保存済みファイアウォールポリシー**を[レッスン7](07-monitoring-performance.md)でも使います。削除を試した場合は、先に再適用して検証してください。次のレッスンには HTTP プロセス、意図的に誤ったラベル、一時 Fail2ban jail のいずれも必要ありません。

不要になったら、`FW_NOTE` に自分が作成したベースラインファイル (`management.before`、`routes.before`、選択した分岐で列挙したベースラインファイル) だけを削除し、ディレクトリが空になったことを確認して `rmdir` します。コース全体の最後のクリーンアップでのみ、記録したプロファイル/ファイアウォール状態に戻します。名前が見慣れているというだけで、不明なゾーン/ルールを削除しないでください。

## 主な参考資料

2026年9月15日確認:

- [Ubuntu UFW manual](https://manpages.ubuntu.com/manpages/noble/man8/ufw.8.html): ルールの方向、インターフェイス、順序、永続化、正確な削除。
- [firewalld CLI](https://firewalld.org/documentation/man-pages/firewall-cmd.html)、[rich language](https://firewalld.org/documentation/man-pages/firewalld.richlanguage.html)、[zones](https://firewalld.org/documentation/zone/connections-interfaces-and-sources.html): タイムアウト、再読み込み、送信元/宛先ルール、分類。
- [NetworkManager connection settings](https://networkmanager.dev/docs/api/latest/settings-connection.html): 有効な接続での `zone` の即時変更、空欄/デフォルトの動作。
- [Rocky Linux 9 SELinux guide](https://docs.rockylinux.org/9/guides/security/learning_selinux/) と [SELinux labeling tools](https://github.com/SELinuxProject/selinux/tree/main/policycoreutils/setfiles): AVC の診断と対象を限定したコンテキストの復元。
- [Fedora EPEL getting started](https://docs.fedoraproject.org/en-US/epel/getting-started/)、[Rocky repository documentation](https://wiki.rockylinux.org/rocky/repo/)、[EPEL Fail2ban packages](https://packages.fedoraproject.org/pkgs/fail2ban/fail2ban-server/): オプションパッケージの取得元と前提条件。
- [Fail2ban jail configuration](https://github.com/fail2ban/fail2ban/blob/master/config/jail.conf)、[systemd backend](https://github.com/fail2ban/fail2ban/blob/master/fail2ban/server/filtersystemd.py)、[client manual](https://manpages.ubuntu.com/manpages/noble/man1/fail2ban-client.1.html): フィルター/バックエンド/アクションの分離、構成テスト、状態確認、範囲を限定した unban。

[クイズ](../../quizzes/networking/beginner/06-firewalls-host-security-quiz.md) | [監視に進む](07-monitoring-performance.md)
