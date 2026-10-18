# 03. ネットワーク設定の永続化

> **対応バージョン**: Ubuntu Server 24.04 LTS（主な手順）、Rocky Linux 9（代替手順）
> **最終更新日**: 2026年9月15日

`ip address add`で追加したaddressは、実行中kernelの設定を変更します。次回起動時の設定を指示するものではありません。この章では、ネットワーク設定の管理者に永続的な指示を登録し、保存した設定とVMが実際に使用している設定を比較します。

## 前提条件と学習目標

[アドレスとインターフェイス](02-addressing-interfaces.md)を終えて、[コースのラボ](README.md)を準備してください。使い捨てVMを2台使い、それぞれのコンソールを開きます。両方Ubuntuでも構いません。Rockyを同時に学ぶかどうかは任意です。

| 項目 | 必要な状態 |
|---|---|
| ClientラボNIC | このレッスン後に`192.0.2.10/24`となる |
| ServerラボNIC | このレッスン後に`192.0.2.20/24`となる |
| ラボnetwork | 同じ内部仮想network。DHCP server、router、uplinkなし |
| 管理NIC | 既存のNAT／DHCP接続を分離して使う。address、route、DNS設定を保持する |
| Identity | ハイパーバイザーで各NICのMACを記録し、ゲスト内で照合する |
| accessとtool | ゲストconsole、sudo権限、editor、`ip`、インストール済みnetwork managerのtool |

コマンドは**指定したVMの中**で実行してください。VMを実行するworkstationでは実行しません。代替手順を使うために、2つ目のnetwork managerをインストールまたは有効化しないでください。必要なtoolがなければ、ラボ準備に戻ります。

設定の管理元を特定し、static addressを永続化し、DHCP／gateway／DNS設定が適切な場合を説明し、再起動後に検証し、自分のラボ変更だけを元に戻せるようになります。まずVMのsnapshotを取り、consoleを開いたままにしてください。各手順を個別に実行し、errorが出たら続ける前に調べます。

## 1. NICと設定の管理元を特定する

**各VM**で、変更を加えずinventoryを確認します。

```bash
cat /etc/os-release
ip -br link
ip -br address
ip -4 route show
ip -6 route show default
systemctl is-active systemd-networkd NetworkManager
```

`ip -br link`はinterface名とMAC addressを対応付けて表示します。一覧の先頭ではなく、ハイパーバイザーに記録した**ラボNICの**MACを照合してください。通常、NAT／DHCP NICは管理用default routeを持ちます。続行前にそのidentityと現在のroute／DNS設定を記録します。2つのserviceのいずれかが存在しない、またはinactiveで、`systemctl is-active`がnonzero statusを返しても、それだけで障害とは限りません。

この章では、`REPLACE_WITH_LAB_NIC`を確認済みの名前に置き換えます。変数は現在のshell内だけで有効です。独立したblockでは再度代入してください。`HOME`や`PATH`などのshell変数にラボ用の値を代入しないでください。

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
ip link show dev "$LAB_IF"
ip -4 address show dev "$LAB_IF"
ip -4 route show dev "$LAB_IF"
```

2つ目のコマンドはkernelの現在のaddressを表示しますが、次回それらを再作成する設定元までは特定しません。この章を始める前に、chapter 02で追加した一時addressを対象を絞って削除してください。新しく追加したラボNICには一時IPv4 addressが残っていないはずです。既存profileが管理するaddressは、予想外だからという理由だけで削除しないでください。

根拠を確認して設定の管理元を選びます。

| 根拠 | 設定の管理元と対応 |
|---|---|
| UbuntuのNetplan YAMLで`networkd`を選択し、`networkctl status`が該当するnetwork fileを示す | 分岐Aへ |
| RockyのNetworkManagerがmanaged deviceとprofileを示す | 分岐Bへ |
| Netplanで`NetworkManager`を選択している | Netplanも上流の設定元である。編集前にYAMLと生成profileを調べる |
| cloud-init、provisioning tool、直接置かれた`.network` file、wildcard match、複数定義が同じNICを管理している | 別定義を追加する前に管理元を特定する。分からなければ新しいコースVMを使う |

NetplanはYAMLをbackend設定へ変換します。`systemd-networkd`とNetworkManagerがdeviceへ設定を適用します。`nmcli`と`nmtui`はどちらもNetworkManagerと通信します。serviceが実行中でも、すべてのNICを管理している証明にはなりません。ここで使うUbuntu Serverの手順は、すべてのUbuntu image、Ubuntu Desktop、Debianに当てはまるものではありません。

### 分岐Aの管理元確認: Ubuntu Netplan／networkd

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
sudo netplan get
sudo ls -l /etc/netplan
networkctl status "$LAB_IF"
sudo ls -l /etc/systemd/network /run/systemd/network
resolvectl status
```

`netplan get`は統合済みの設定を表示します。一覧から実際のYAML file名を選び、`sudo less /etc/netplan/ACTUAL_FILE.yaml`で内容を確認してください。既存の`/lib/netplan`と`/run/netplan`directoryも調べます。`networkctl status`は該当するnetwork fileがあれば表示します。`resolvectl status`では既存DNS serverとlinkを記録します。

Netplanは名前の異なるYAML fileを辞書順に統合します。後のscalar値は前の値を置き換えますが、listは**連結される**ことがあります。後から空のaddress／DNS listを追加しても、それ以前のlistを一般に消去できるとは限りません。別名の定義も同じNICにmatchする場合があります。[Netplanのfile統合](https://netplan.readthedocs.io/en/stable/netplan-generate/)を参照してください。

以下の手順は、直接置かれたnetworkd file内のwildcard matchも含め、ラボNICに**永続定義が存在しないこと**を前提にします。installerがすでに定義していた場合は、そのfileの管理元を確認し、backupを取ったうえで該当するラボ用設定箇所だけを意図的に編集してください。このfileでinstallerのfileを上書きしたり、同じNICの定義を2つ残したりしないでください。cloud-initのcommentを見つけたらprovisioning元を確認します。cloud-init全体を無効にしてはいけません。最初のラボではOSの初期設定後に内部NICを追加すると、このような競合を避けやすくなります。

### 分岐Bの管理元確認: Rocky NetworkManager

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
nmcli --version
nmcli device status
nmcli -f GENERAL,IP4,IP6,CONNECTIONS device show "$LAB_IF"
nmcli -f NAME,UUID,TYPE,DEVICE,AUTOCONNECT connection show
```

`device`はNIC、`connection`は保存済みprofileの情報です。名前が一致するとは限りません。`GENERAL.CON-UUID`はactive profileがあればそのUUIDを示します。`CONNECTIONS`からinactiveなものも含め、互換性のあるprofileを特定できます。以前のラボprofileのUUIDと、それがactiveだったかを記録し、管理profileは保持します。

互換性のあるprofileをそれぞれ`nmcli connection show uuid ACTUAL_UUID`で確認します。`connection.interface-name`、`802-3-ethernet.mac-address`、`connection.autoconnect`、`connection.autoconnect-priority`を記録してください。device／MACの指定が空のEthernet profileは、複数NICにmatchする場合があります。ラボ設定を簡単にするためだけに、そのような共有profileを変更しないでください。

Rocky 9はNetworkManagerのkeyfile設定に対応しており、以前のifcfg profileも残っている場合があります。interface名だけを見て保存形式を推測しないでください。[Rocky 9のversion付きguide](https://docs.rockylinux.org/9/guides/network/basic_network_configuration/)はRocky 9を説明します。[versionなしのguide](https://docs.rockylinux.org/guides/network/basic_network_configuration/)は現在Rocky 10を扱っています。

## 2A. Netplan／networkdでaddressを永続化する

分岐Aの管理元確認を済ませた場合だけ、この手順を使います。clientとserverそれぞれで**自分のMACとaddress**を指定してください。

### backupを取り、1つだけ管理対象fileを作る

各**Ubuntu VM**で新しい復旧用directoryを作ります。すでに存在する場合は、以前の作業を調べて停止してください。既存backupを置き換えないでください。

```bash
sudo mkdir -m 700 /root/network-beginner-03
sudo cp -a /etc/netplan /root/network-beginner-03/netplan-before
sudo sh -c 'umask 077; set -C; : > /etc/netplan/90-beginner-lab.yaml'
sudoedit /etc/netplan/90-beginner-lab.yaml
```

`cp -a`は元fileとpermissionを保持します。短い`sh` commandはrootのみ読み書きできる空fileを作成します。`set -C`は既存fileへの上書きを拒否します。`sudoedit`は設定済みeditorで編集可能なcopyを開きます。

次の**YAML文書全体**を、tabではなくspaceを使って貼り付けてください。例のMACはclientの実際のラボMACに置き換えます。serverではserver側のMACに置き換え、addressを`192.0.2.20/24`に変更してください。

```yaml
network:
  version: 2
  ethernets:
    beginner-lab:
      renderer: networkd
      match:
        macaddress: "02:00:00:00:00:10"
      dhcp4: false
      dhcp6: false
      accept-ra: false
      link-local: []
      addresses:
        - 192.0.2.10/24
      optional: true
```

| 設定 | このラボでの意味 |
|---|---|
| `version: 2` | Netplanの設定schema version |
| `beginner-lab` | 定義ID。MACでNICを選択するため、名前変更は不要 |
| device単位の`renderer` | global rendererを変更せず、この定義でnetworkdを選ぶ |
| `dhcp4: false` | DHCP serverのないnetworkでDHCP requestを送らない |
| IPv6／link-local設定 | この隔離演習ではNICをIPv4専用にする。host全体に推奨するIPv6設定ではない |
| `addresses` | `/24` prefixを持つaddressを1つ設定する。接続subnetにgatewayは不要 |
| `optional: true` | 起動時にnetworkdがラボNICを待たないようにする。NICの設定自体は行う |

意図的に`routes` blockも`nameservers` blockも含めていません。どちらのVMもrouterやDNS serverではありません。gatewayとして`192.0.2.1`を推測しても、routerが作られるわけではありません。管理NICの設定はそのまま維持します。

### 検証し、試行し、状態を確認する

```bash
sudo chmod 600 /etc/netplan/90-beginner-lab.yaml
sudo netplan generate
sudo netplan get
```

`chmod 600`でrootだけがfileを読み書きできるようにします。起動済みのこのsessionでは`generate`が検査とbackend設定の生成を行いますが、適用はしません。成功時は通常何も表示されません。統合後の出力を確認します。意図したラボaddress／MACだけがあり、ラボgateway／DNSは追加されず、管理設定は元のままであることを確かめてください。YAMLが正しくても、MACやaddressが間違っている場合はあります。

**VM console**から試行を始めます。

```bash
sudo netplan try --timeout 120
```

確認promptが待っている間に、2つ目のconsole／loginから状態を確認します。

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
ip -4 address show dev "$LAB_IF"
ip -4 route show dev "$LAB_IF"
ip -4 route show default
ip -6 route show default
networkctl status "$LAB_IF"
resolvectl status
```

`192.0.2.0/24`のlocal route、`.10`または`.20`の正しいaddress、ラボNICから追加されたdefault route／DNSがないこと、元の管理経路を引き続き使えることを確認します。それらを確認した後だけ試行を確定してください。peerへのpingが成功することを求める前に、両VMを設定します。

`try`と`apply`は新しいfileだけでなく、**統合済みの設定全体**を対象にします。複数deviceのnetwork設定を再適用する可能性があります。管理定義を編集していなくてもconsole accessを維持してください。`try`は確定されない試行をrevertする想定ですが、[Netplanはrollbackのbugを文書化しています](https://netplan.readthedocs.io/en/stable/netplan-try/)。timeoutやCtrl+Cは**復旧できた証拠ではありません**。実行状態とdisk上のfileを確認してください。

### Netplanの復旧とrollback

後続レッスンのため、動作するラボ設定は維持します。この変更を破棄するには、**consoleから**復旧します。

1. `/etc/netplan/90-beginner-lab.yaml`を確認し、この手順で作成したfileであることを確かめる。
2. そのfileだけをNetplanの入力directory外へ移動する。
3. 残った、以前から動作していた設定をgenerateしてapplyする。

```bash
sudo mv -i /etc/netplan/90-beginner-lab.yaml /root/network-beginner-03/90-beginner-lab.failed.yaml
sudo netplan generate
sudo netplan apply
```

`mv -i`は以前の失敗copyがある場合に上書き確認します。`generate`が失敗した場合は`apply`する前に停止します。新規NIC向け手順を使わず既存の管理元fileを編集した場合は、`netplan-before`内にある対応fileと比較し、**編集したそのfileだけ**を復元してからgenerate／applyしてください。directory全体を置き換えないでください。

address、route、管理accessを再確認します。管理対象外になったラボNICに、実行状態のaddressだけが残る場合があります。**このレッスンで追加した正確なaddressがまだ存在する場合に限り**削除します。

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
LAB_CIDR='192.0.2.10/24'
sudo ip address del "$LAB_CIDR" dev "$LAB_IF"
```

serverでは`LAB_CIDR='192.0.2.20/24'`を設定します。最初のinventoryでラボNICが管理上downだった場合は、同じshellで`sudo ip link set dev "$LAB_IF" down`を実行して元に戻します。管理routeを削除したりinterfaceをflushしたりしないでください。最終的な復旧操作としてrebootする前に、disk上の設定が復元済みのものであることを確認します。設定の管理元または復旧方法が不明なら、レッスン前のVM snapshotを復元してください。

## 2B. NetworkManagerでaddressを永続化する

各**Rocky VM**で分岐Bのinventoryを使います。この手順は各ゲストに`beginner-lab-static`を作成します。新しい名前である必要があります。すでに存在する場合は、重複を作るのではなく前回の作業を調べてください。

互換性のある古いprofileは復旧用として残します。再起動時にどれが選択されるか予測可能にするため、ラボNICだけにbindされたprofileに限り、元の値を記録したうえでautoconnectを**無効にします。**

```bash
OLD_LAB_UUID='REPLACE_WITH_CONFIRMED_LAB_PROFILE_UUID'
nmcli -f connection connection show uuid "$OLD_LAB_UUID"
sudo nmcli connection modify uuid "$OLD_LAB_UUID" connection.autoconnect no
```

以前のラボprofileがなければ、このblockは省略します。ほかにもラボ専用のcandidateがあれば繰り返します。今のactive設定はまだ変えません。candidateが未bind／共有状態、または管理元が不明な場合は、先へ進む前に曖昧さを解消します。`DEVICE=--`はinactiveという意味にすぎず、安全なprofileを意味するわけではありません。

新しいprofileを作ります。このblockでは、最初に**自動activateせず保存します。**

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
LAB_MAC='REPLACE_WITH_LAB_MAC'
LAB_CIDR='192.0.2.10/24'
sudo nmcli connection add type ethernet con-name beginner-lab-static \
  ifname "$LAB_IF" 802-3-ethernet.mac-address "$LAB_MAC" \
  connection.autoconnect no \
  ipv4.method manual ipv4.addresses "$LAB_CIDR" \
  ipv4.gateway "" ipv4.dns "" ipv4.never-default yes \
  ipv6.method disabled
nmcli -f connection,802-3-ethernet,ipv4,ipv6 connection show id beginner-lab-static
```

serverでは`.20/24`を使ってください。`manual`にはaddress／prefixが必要です。interfaceとMACのbindにより、このprofileを使えるdeviceを制限します。`mac-address`は恒久MACを照合し、MAC自体を変更しません。空のgateway／DNSと`never-default yes`によりローカルだけで使います。IPv6を無効にするのはこのラボprofileだけです。`connection add`は既定で永続保存しますが、**保存済みでもまだactiveとは限りません。**

出力された新しいUUIDを記録します。このprofileだけをactivateし、実行状態を確認します。

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
LAB_UUID='REPLACE_WITH_NEW_LAB_PROFILE_UUID'
sudo nmcli --wait 30 connection up uuid "$LAB_UUID" ifname "$LAB_IF"
nmcli -f GENERAL,IP4,IP6 device show "$LAB_IF"
ip -4 route show
```

activateすると、このNICで以前activeだったprofileが置き換えられる場合があります。意図したaddressと接続subnet routeがあり、ラボgateway／DNSがないことを確認してください。管理routeを最初のinventoryと比較します。activateに失敗したら`journalctl -u NetworkManager -b -n 50 --no-pager`を確認します。timeoutが起きても、保存済みprofileが消えた証拠にはなりません。

確認が成功した後で、次回起動時のactivateを有効にします。

```bash
LAB_UUID='REPLACE_WITH_NEW_LAB_PROFILE_UUID'
sudo nmcli connection modify uuid "$LAB_UUID" connection.autoconnect yes
nmcli -f connection.id,connection.uuid,connection.autoconnect connection show uuid "$LAB_UUID"
```

### nmtuiで同じprofileを設定する

`nmtui`がすでに利用可能であれば、**既存の専用profile**を開きます。

```bash
sudo nmtui edit beginner-lab-static
```

Tabで項目を移動し、矢印keyで選択、Spaceで切り替え、Enterで確定します。profile名とdeviceを確認し、IPv4を**Manual**にして詳細を展開し、`.10/24`または`.20/24`のaddressが1つだけ設定されているか確認してください。Gateway、DNS server、search domainは空のままにします。Routesの項目にあれば、**Never use this network for default route**を選択します。IPv6は**Disabled**のままにし、検証後は自動接続を有効にします。

確認だけなら**Cancel**、意図した変更を保存するなら**OK**を選びます。保存すると`nmcli`と同じNetworkManager profileが変わります。別の設定層ができるわけではありません。保存後に`nmcli connection show`で確認し、前述のblockから記録したUUIDをactivateします。menuはpackage versionにより異なります。propertyが見つからなければ`nmcli`で設定して検証してください。管理接続を一般的なdeactivate／reactivate操作の対象にしないでください。

### NetworkManagerの復旧とrollback

**consoleから**記録した新UUIDを確認し、自分のprofileだけを削除します。作成が成功しなかった場合は、この新profile用blockを省略しますが、以前のautoconnect値を変更していたら必ず復元してください。

```bash
LAB_UUID='REPLACE_WITH_NEW_LAB_PROFILE_UUID'
nmcli -f connection,ipv4 connection show uuid "$LAB_UUID"
sudo nmcli connection modify uuid "$LAB_UUID" connection.autoconnect no
sudo nmcli connection down uuid "$LAB_UUID"
sudo nmcli connection delete uuid "$LAB_UUID"
```

UUIDを確認した後であれば、`down`の結果が「すでにinactive」でも問題ありません。それ以外の無関係なerrorは調査が必要です。接続をdownにすると互換性のある別profileが自動activateされることがあります。deviceを再確認してください。

以前のラボprofileがあれば、記録したautoconnect値をすべて復元します。**レッスン開始前にactiveだった場合だけ**再activateします。

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
OLD_LAB_UUID='REPLACE_WITH_PREVIOUS_LAB_PROFILE_UUID'
OLD_AUTOCONNECT='yes'
sudo nmcli connection modify uuid "$OLD_LAB_UUID" connection.autoconnect "$OLD_AUTOCONNECT"
sudo nmcli --wait 30 connection up uuid "$OLD_LAB_UUID" ifname "$LAB_IF"
```

推測した値ではなく、記録した`yes`または`no`を使ってください。以前のprofileがinactiveだったなら`up`の行は省略します。以前のprofileがなければ復元するprofileはありません。レッスンで追加したaddressが消えていることを確認してください。必要に応じてラボlinkの元のup／down状態も復元し、管理address／route／DNSを最初の記録と比較します。すべてのEthernet profileを削除したり、network全体を再起動したりしないでください。

## 3. DHCP、gateway、DNSが必要な場合

static addressingは管理者が選んだaddressを割り当てます。DHCPは実際に稼働するDHCP serverへleaseを要求し、routeやDNSも提供される場合があります。内部コースnetworkでDHCPを有効にしてもleaseは取得できません。DNS serverはnameに関する問い合わせへ応答し、gatewayはlink外のpacketを転送します。1台のdeviceが両方を提供する場合もありますが、IP末尾が`.1`というだけでどちらかの役割を持つわけではありません。

以下は**任意の応用例であり、2台のVMを使うコースラボには変更を加えません**。ハイパーバイザーのMACで特定し、consoleからアクセスでき、設定の競合元がなく、DHCP対応の仮想networkまたは管理者が指定したrouting networkを持つ、別の使い捨て練習VM／interfaceを使います。コースVMの管理NICを代用してはいけません。

### DHCPを実際に提供するnetworkで設定する

DHCP対応の練習networkにある、空いている**networkd管理NIC**向けの完全なNetplan定義は次のとおりです。

```yaml
network:
  version: 2
  ethernets:
    practice-dhcp:
      renderer: networkd
      match:
        macaddress: "02:00:00:00:00:30"
      dhcp4: true
      dhcp4-overrides:
        use-routes: false
        use-dns: false
        use-domains: false
      dhcp6: false
      accept-ra: false
      link-local: []
      optional: true
```

例のMACを空いているNICのMACに置き換えます。このoverrideはaddressを要求する一方、DHCP route、DNS、search domainを受け取らず、練習VMの既存管理経路を保ちます。接続subnet routeは追加されます。primary uplinkとして意図的に選んだNICであれば、管理者はDHCP routeとDNSも受け取る設定にできます。このコースでは既存uplinkを変更しません。

同じ新規file／backup手順を使い、`90-beginner-dhcp.yaml`のような異なるfileを用意します。mode 600を設定し、`generate`、統合結果の確認、`try`を実行します。leaseは`networkctl status`と`ip address`で確認します。取得できなければcarrier、仮想networkの選択、DHCP service／scopeが利用可能か調べます。この新しいfileだけを削除し、復元した設定をapplyして戻します。分岐Aと同様にラボaddressが残っていないことを確認してください。

まだ設定されていない**NetworkManager管理の空きNIC**では、同じ設定を次のprofileで保存できます。

```bash
PRACTICE_IF='REPLACE_WITH_SPARE_NIC'
PRACTICE_MAC='REPLACE_WITH_SPARE_MAC'
sudo nmcli connection add type ethernet con-name beginner-practice-dhcp \
  ifname "$PRACTICE_IF" 802-3-ethernet.mac-address "$PRACTICE_MAC" \
  connection.autoconnect no ipv4.method auto \
  ipv4.never-default yes ipv4.ignore-auto-routes yes ipv4.ignore-auto-dns yes \
  ipv6.method disabled
sudo nmcli --wait 60 connection up id beginner-practice-dhcp ifname "$PRACTICE_IF"
nmcli -f GENERAL,IP4,DHCP4 device show "$PRACTICE_IF"
```

profile名は未使用のものにします。UUIDを記録し、分岐BのUUID指定rollbackでこの新profileだけを削除してください。この例は`autoconnect no`を使うため、設定は保存されてもreboot後のactivateは手動です。staticからDHCPへ、すでに存在する**専用練習profile**を変更する場合は、同じ`connection modify`操作内で`ipv4.method auto`を設定し、`ipv4.addresses`、`ipv4.gateway`、`ipv4.routes`、`ipv4.dns`、`ipv4.dns-search`を消去します。そうしないと、古いstatic値とDHCP設定が共存することがあります。変更前の値を記録し、その設定を復元して応用例を取り消します。

### routing networkでgatewayとDNSを永続設定する

コースVMとは別の**練習用VM**に、管理者から`10.77.0.10/24`、link上にある実際のrouter `10.77.0.1`、`training.example`を提供する到達可能なresolver `10.77.0.53`が割り当てられている例を考えます。演習用NICは明示的に選んだdefault uplinkであり、**競合する管理用default routeがあってはいけません**。ハイパーバイザーconsoleを使います。使用前に、例の値がその練習networkに合っていることを管理者に確認してください。

Netplan／networkdでは、完全な定義は次のようになります。

```yaml
network:
  version: 2
  ethernets:
    practice-uplink:
      renderer: networkd
      match:
        macaddress: "02:00:00:00:00:40"
      dhcp4: false
      dhcp6: false
      accept-ra: false
      link-local: []
      addresses:
        - 10.77.0.10/24
      routes:
        - to: default
          via: 10.77.0.1
      nameservers:
        addresses:
          - 10.77.0.53
        search:
          - training.example
```

`to: default`は、より具体的なmatchがない宛先へのrouteを追加します。`via`はlink上にあるrouterのaddressです。`nameservers.addresses`はresolverを指定します。`search`は`web`のような短いnameを`web.training.example`として補完できます。DNS recordを作成するものではありません。個別にbackupした管理対象fileを使い、MACを置き換え、分岐Aと同じpermission／validation／trial／復旧手順を繰り返します。

NetworkManagerでは、同じ条件を満たす新規管理NICに次を設定します。

```bash
PRACTICE_IF='REPLACE_WITH_PRACTICE_UPLINK'
PRACTICE_MAC='REPLACE_WITH_PRACTICE_MAC'
sudo nmcli connection add type ethernet con-name beginner-practice-routed \
  ifname "$PRACTICE_IF" 802-3-ethernet.mac-address "$PRACTICE_MAC" \
  connection.autoconnect no \
  ipv4.method manual ipv4.addresses 10.77.0.10/24 \
  ipv4.gateway 10.77.0.1 ipv4.never-default no \
  ipv4.dns 10.77.0.53 ipv4.dns-search training.example \
  ipv6.method disabled
sudo nmcli --wait 30 connection up id beginner-practice-routed ifname "$PRACTICE_IF"
nmcli -f GENERAL,IP4 device show "$PRACTICE_IF"
```

activate前に新profileを確認してUUIDを記録します。起動時にactivateしたい場合は、確認が成功した後にだけautoconnectを有効にします。分岐Bと同様にUUIDを指定して削除すればrollbackできます。どちらのbackendでも、`ip route get 10.77.0.53`、default route、管理者から提供されたDNS recordを検証してください。resolvedがactiveなら`resolvectl status`を確認します。それ以外はNetworkManagerのactive DNSと`/etc/resolv.conf`を確認します。生成された`resolv.conf`を直接編集したり、一時的な`resolvectl dns`コマンドを永続profileの変更と見なしたりしないでください。

## 4. reboot後にコースラボを検証する

2台のコースVMのstatic設定に戻ります。作業を保存し、各**使い捨てguest**のconsoleから`sudo reboot`で再起動してください。login後にNICのMACを再照合します。shell変数はreboot後に残りません。

**client**側:

```bash
LAB_IF='REPLACE_WITH_CLIENT_LAB_NIC'
ip -4 address show dev "$LAB_IF"
ip -4 route get 192.0.2.20
ip -4 route show default
ping -n -c 3 -W 2 192.0.2.20
```

**server**側では`.20/24`を確認し、`ip -4 route get 192.0.2.10`と`ping -n -c 3 -W 2 192.0.2.10`を実行します。route lookupは`via`なしでラボNICとlocal lab source addressを選ぶはずです。管理用default routeは引き続き存在してもよく、元の設定と一致する必要があります。DHCP leaseの詳細が更新されることはあり得ます。

| 観察結果 | 最初に調べること |
|---|---|
| reboot後にaddressがない | MAC違い、未保存file／profile、autoconnect無効、設定の競合元 |
| ラボaddress／DNS／default routeが余分にある | 統合YAMLのlist、別のmatch定義／profile、残った一時設定 |
| `NO-CARRIER` | ハイパーバイザーのcable／adapter状態と内部networkへの接続 |
| routeは正しいがping応答がない | peer address、同一内部network、neighbor discovery、ICMP policy。chapter 04へ |
| 管理accessが変わった | consoleと該当rollbackを使う。routeをflushしない |

## 完了確認

- 両VMでMAC情報からラボNICと管理NICを特定する。
- ラボNICの設定を所有するfile／profileを説明し、保存済みとactiveの状態を区別する。
- `.10/24`と`.20/24`がreboot後も残り、peer向けon-link routeを持つことを確認する。
- ラボNICからgateway／DNSが追加されず、管理設定が保たれていることを示す。
- peer pingの結果を記録し、gatewayを推測せず失敗を調べる。
- 元に戻す正確な新file／profileと復元すべき状態を特定する。
- 任意のDHCP／routing例に、別途準備したnetworkが必要な理由を説明する。

次のレッスンのため、動作するstatic lab addressは残しておきます。コースが終わるまでbackupの記録を保管してください。

## 主要資料と追加の読み物

- [Ubuntu Server: network設定](https://documentation.ubuntu.com/server/explanation/networking/configuring-networks/)
- [Netplanの例](https://netplan.readthedocs.io/en/stable/examples/)、[YAML reference](https://netplan.readthedocs.io/en/stable/netplan-yaml/)、[file permission](https://netplan.readthedocs.io/en/stable/security/)
- [Netplanのgenerateと統合](https://netplan.readthedocs.io/en/stable/netplan-generate/)、[Netplan tryと復旧時の注意点](https://netplan.readthedocs.io/en/stable/netplan-try/)
- [NetworkManager nmcli例](https://www.networkmanager.dev/docs/api/latest/nmcli-examples.html)、[nmcli manual](https://www.networkmanager.dev/docs/api/latest/nmcli.html)、[profile property](https://www.networkmanager.dev/docs/api/latest/nm-settings-nmcli.html)、[nmtui](https://www.networkmanager.dev/docs/api/latest/nmtui.html)
- [Rocky Linux 9のnetwork設定](https://docs.rockylinux.org/9/guides/network/basic_network_configuration/)

[前へ: アドレスとインターフェイス](02-addressing-interfaces.md) · [クイズ](../../quizzes/networking/beginner/03-persistent-configuration-quiz.md) · [次へ: DNSと接続性](04-dns-connectivity.md)
