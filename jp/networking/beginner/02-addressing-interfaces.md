# 2. アドレス、サブネット、ネットワークインターフェイス

> **対応バージョン**: Ubuntu Server 24.04 LTS（主な手順）、Rocky Linux 9（代替手順）
> **最終更新日**: 2026年9月15日

[前へ: Linux端末](01-linux-cli.md) | [コースの準備](README.md) | [クイズ](../../quizzes/networking/beginner/02-addressing-interfaces-quiz.md) | [次へ: 永続的な設定](03-persistent-configuration.md)

ネットワークインターフェイスにケーブルとアドレスがあっても、serviceに到達できないことがあります。これらは問題の異なる層です。このレッスンでは、まずメッセージが各層を通る様子を追い、その後、小さなIPv4ネットワークをローカルに構築して違いを確かめます。

## 前提条件と学習目標

[レッスン1](01-linux-cli.md)を終えてください。通常アカウント、`sudo`、変数、一意な練習用ディレクトリを使い、VMコンソールを問題なく操作できる必要があります。使い捨てのローカルVMを2台用意します。どちらもUbuntu Server 24.04 LTSを使うか、管理手順の代替としてRocky Linux 9を使ってください。コマンドには`iproute2`（Rockyでは`iproute`パッケージ）とiputilsの`ping`を使います。演習前に利用可能にしてください。このレッスンではパッケージをインストールしません。

[コースの準備](README.md)の説明に従い、ハイパーバイザーで以下を用意します。「内部専用」とは、2台の仮想NICを**同じ隔離された仮想ネットワーク**に接続し、DHCP server、router、外部uplinkを置かないことです。host-only networkが自動的にこれと同等とは限りません。ハイパーバイザーの設定によっては、ホストへの接続やDHCPが含まれる場合があります。

| ゲストの役割 | 既存の管理NIC | 分離された内部ラボNIC |
| --- | --- | --- |
| Client | 既存のNAT/DHCP接続。変更しない | `192.0.2.10/24`、gatewayとDNSなし |
| Server | 既存のNAT/DHCP接続。変更しない | `192.0.2.20/24`、gatewayとDNSなし |

ハイパーバイザー設定で、各ゲストの**両方のNICのMAC address**と、それぞれが接続する仮想ネットワークを記録してください。2台のゲストで異なるMAC addressを使います。両方のコンソールを開いたままにしてください。`192.0.2.0/24`は文書用に予約された範囲（RFC 5737）です。この隔離ラボだけで使い、実際のインターネット宛先には使わないでください。ラボNICを自宅、会社、cloud networkにbridgeしないでください。

レッスンを終えると、次のことができるようになります。

- Ethernet frame、IP packet、transport port、application serviceを区別する。
- サブネット境界を計算し、宛先がローカルかrouter経由かを判断する。
- gateway、DHCP、DNS、ARP、IPv6 Neighbor Discoveryがそれぞれ何をするか説明する。
- 名前を推測せず、ゲストのinterfaceと正しいハイパーバイザーNICを対応付ける。
- link、address、route、neighborを調べ、各ラボNICに一時IPv4 addressを1つ追加し、正確に元へ戻す。

**実行時の約束:** コマンドは**指定した練習用VM内だけ**で実行します。行に`sudo`がなければ通常ユーザーとして実行してください。物理ホストやドキュメント用ホストは設定しません。「各VM」と書かれたコマンドは、別々に各VMのコンソールで繰り返します。変数はそのshell内だけのものです。例は説明用で、VMでの実行結果ではありません。予期しないエラーが出たら続行せず停止してください。

## applicationからケーブルまで、1つのメッセージを追う

次の演習で、clientがTCP port `8080`のserverにWebページを要求すると想像してください。Web serverが実際にそこでlistenしている必要があります。IP addressを割り当ててもserviceは作成されません。

| 層 | 運ぶもの、または識別するもの | このラボでの例 |
| --- | --- | --- |
| application | requestとresponseの意味 | ページを要求するHTTP request |
| transport | port番号で識別するTCPまたはUDP通信のendpoint | clientの一時TCP source portからserverのTCP port `8080`へ |
| Internet | routing用のsource／destination addressを持つIP packet | `192.0.2.10`から`192.0.2.20` |
| local link | source／destination MAC addressを持つEthernet frame | clientラボNICのMACからserverラボNICのMACへ |

送信側はapplication dataをtransport情報で包み、さらにIP packet、現在のlink用のframeへと包みます。受信側はそれらの包みを順に外します。frameはlink上でtrafficを運び、routerはネットワーク間でIP packetを転送します。routerを通ると、次のlink用にlink層のframeが置き換わります。この小さなラボでは2台のゲスト間にrouterは不要です。

**MAC address**はlink上のEthernet interfaceを識別します。仮想NICにもMAC addressがあります。**prefix付きIP address**は、IP network内でinterfaceをどう特定するかをhostに伝えます。1つのNICが複数のaddressを持つ場合もあります。どちらのaddressも、人のidentityを証明するものではありません。

**port**はTCPまたはUDP内の16-bit番号であり、VMの物理的な差し込み口ではありません。TCP port `8080`とUDP port `8080`は異なるendpointです。protocol、source IP／port、destination IP／portによって通信が識別されます。IPに到達できても、選んだportでlistenしている、またはfirewallが許可しているとは限りません。`ping`が使うICMPにTCP／UDP port番号はありません。application serviceのテストは後のレッスンで行います。

## IPv4とCIDRを暗記せずに計算する

IPv4 addressは32-bitで、通常は`0`～`255`の10進数octetを4つ並べて表します。`/`の後ろに書く**prefix長**は、先頭から何bitがnetworkを表すかを示します。残りのbitでその中のaddressを区別します。このslash表記をCIDR表記と呼びます。

`192.0.2.10/24`では、先頭24-bitがnetworkで、8-bitが残ります。

| 計算 | 結果 |
| --- | --- |
| prefix mask: 1が24個、続いて0が8個 | `255.255.255.0` |
| host bitをすべて0にしたaddress | network address `192.0.2.0` |
| host bitをすべて1にしたaddress | broadcast address `192.0.2.255` |
| address数 | `2^(32-24) = 256` |
| このsubnetの通常host範囲 | `192.0.2.1`～`192.0.2.254` |

両端の2つのaddressは通常hostに割り当てないため、host用は254個です。point-to-point向けの特殊な`/31`と`/32`は異なる規則に従い、この最初のラボでは扱いません。`.10/24`と`.20/24`はどちらも`192.0.2.0/24`に属します。先頭2つのoctetが一致していても、`192.0.3.20`はその範囲外です。

もう少し分かりにくい例として、**`192.0.2.70/26`を考えます**。

1. `/26`ではhost bitが6個残り、各blockのaddress数は`2^6 = 64`です。
2. maskは`255.255.255.192`です。最後のoctetは2進数で`11000000`です。
3. `.70`の最後のoctetは`01000110`です。先頭2 bitを残し、ほかを0にすると`01000000`、つまり`.64`です。
4. したがってblockは`.0`、`.64`、`.128`、`.192`から始まります。`.70`は`.64`のblock内です。
5. networkは`192.0.2.64/26`、broadcastは`.127`、通常host範囲は`.65`～`.126`（host address 62個）です。

したがって、`.100/26`は`.70/26`と同じsubnetですが、`.130/26`は異なります。prefixが`/24`でない限り、先頭3つのoctetだけで一致すると判断できません。prefix値が大きいほどaddress blockは小さくなります。実際のラボでは`/24`を使い、計算例の`/26`は使わないでください。

## Gateway、DHCP、DNS、neighborは別々の問いに答える

**route**は、packetをどこへ送るかkernelに伝えます。直接接続routeは「この宛先はそのinterfaceのlink上にある」という意味です。`via`を含むrouteは、次のhopとなるrouter、一般に**gateway**と呼ばれるものを指定します。複数routeが一致する場合は、最長一致prefixが優先されます。より具体的なrouteが一致しないときに使うfallbackが、**default route**（`0.0.0.0/0`、表示は`default`）です。

この`/24`で`.10`から`.20`へ送るときは、直接接続routeの方が管理用default routeより具体的です。clientはラボlink上に直接送ります。**入力すべきラボgatewayはありません**。また、`.1`が自動的にrouterになるわけでもありません。既存の管理用default routeはそのままにしてください。

| 仕組み | 答える問い | 証明しないこと |
| --- | --- | --- |
| DHCP | 「設定serverからaddressをleaseし、routeやDNSなどのoptionを取得できるか」 | Web serviceが実行中かどうか |
| DNS | 「このnameにどのaddressやほかのrecordが対応するか」 | routeやlisten中のserviceがあるかどうか |
| IPv4 ARP | 「link上にいるIPv4 neighborに、現在どのMAC addressが対応するか」 | neighborがTCP接続を受け付けるかどうか |

DHCPは設定情報の交換であり、すべてのpacketを転送する動作ではありません。DNSはnameをaddressなどへ解決する仕組みであり、client自身のIP addressを割り当てるものではありません。IPv4でsubnet外へ送るとき、ARPで通常確認するのは**次hop gatewayのMAC**であり、インターネット上のremote serverのMACではありません。

このラボ用NICにはDHCP serverがないため、文字列で指定したIP addressによる通信にgatewayもDNSも必要ありません。別の管理NICは、既存のDHCP設定を引き続き使えます。そのaddressやresolver設定は変更しません。

IPv6 addressは**128-bit**で、colonで区切った16進数groupとして表します。group内の先頭の0は省略でき、`::`は連続する0のgroupをまとめて表せます。`::1`はloopbackです。`fe80:`で始まるaddressは一般にlink-localで、そのlink上だけで使えます。interfaceごとにlink-local addressを持つ場合があるため、宛先のlinkを指定する`%interface-name`のようなzoneが必要なことがあります。interface名はこの例ではなく、実際のゲストOSから取得してください。

`2001:db8::/32`はIPv6の文書用範囲（RFC 3849）で、ここでは設定しません。一般的なIPv6 LAN prefixは`/64`です。IPv6はARPの代わりにICMPv6 Neighbor Discoveryを使い、IPv4形式のbroadcastはありません。Router Advertisement、SLAAC、DHCPv6は別の設定項目です。link-local IPv6 addressがあるだけでは、インターネットへ到達できる証拠になりません。IPv4演習中も、既存のIPv6設定は有効のまま変更しないでください。

## interfaceを選ぶ前に調べる

現代的な`ip`コマンドは、関連するobjectをグループ化します。`link`はdevice、`address`（`addr`または`a`とも表記）はaddress、`route`はrouting、`neigh`はneighbor tableを扱います。通常、これらの確認に`sudo`は必要ありません。

**各VM、通常ユーザー、確認のみ:**

```bash
hostname
ip -br link
ip -br address
ip a
ip -4 route
ip neigh
```

`-br`は簡潔な出力を指定します。`-4`はIPv4に限定します。付けずに`ip a`を実行するとIPv6も表示されます。`ip a`は`ip address`の省略形で、addressを追加するコマンドではありません。

実際のinterface名を置き換えた、説明用の簡潔な出力:

```text
lo            UNKNOWN  00:00:00:00:00:00 <LOOPBACK,UP,LOWER_UP>
<management>  UP       02:00:00:00:01:10 <BROADCAST,MULTICAST,UP,LOWER_UP>
<lab>         DOWN     02:00:00:00:02:10 <BROADCAST,MULTICAST>
```

行は順にinterface名、動作状態、MAC address、flagを表します。**完全なMAC address**を各ゲストについてハイパーバイザーの記録と照合してください。NICの順序、PCI接続、image設定、OSの命名規則によって名前は変わります。「2行目」や、推測した`eth1`／`ens19`を頼りにしてはいけません。`lo`はゲスト内のloopbackで、仮想Ethernet NICではありません。

flagの`UP`は管理上有効であること、`LOWER_UP`は下位層でcarrierが検出されたことを表します。管理上は有効でもcarrierがないdeviceがあります。その場合は仮想ケーブルと内部ネットワークへの接続を調べます。特にloopbackの動作状態が`UNKNOWN`でも、自動的に失敗を意味するわけではありません。変更する前に、元の管理上の状態を記録してください。

## 各VMで境界と変更前の状態を記録する

**各VM、通常ユーザー。promptが求めたら実際の名前を入力:**

```bash
read -r -p 'Lab NIC name matched by MAC: ' LAB_IF
read -r -p 'Management NIC name matched by MAC: ' MGMT_IF
ip -br link show dev "$LAB_IF"
ip -br link show dev "$MGMT_IF"
ip -4 address show dev "$LAB_IF"
ip -4 route show table main
```

`read`はshell変数に入力値を保存するだけで、interfaceは変更しません。名前が空、deviceが存在しない、2つの名前が同一、いずれかのMACが記録と異なる場合は停止して、識別をやり直してください。コマンドが名前を受け付けたというだけで続行してはいけません。

**変更前の確認条件:** ラボNICにはIPv4 addressが**割り当てられていないこと**。また、管理用default（想定どおりの`default`）を除き、`192.0.2.0/24`と重なるIPv4 routeがゲストに存在しないことを確認してください。既存のIPv6 link-local addressは問題ありません。ラボNICにIPv4 addressがすでにある、または予期しないrouteがある場合は停止し、コース準備を見直してください。不明な状態を削除したり、network managerが所有するaddressを使い回したりしないでください。後でゲストのnetwork managerが手動設定を置き換えることがあります。そのため、この演習の設定は一時的にします。

変更前の情報を保管する場所を作ります。2台のゲストそれぞれで個別に実行してください。

**各VM、通常ユーザー:**

```bash
NET_NOTE_DIR=$(mktemp -d "$HOME/network-beginner-ip.XXXXXX")
printf '%s\n' "$NET_NOTE_DIR"
```

この正確なpathを記録してください。作成に失敗したか値が空なら停止します。次に変更前の状態を保存します。

```bash
ip -details link show dev "$LAB_IF" > "$NET_NOTE_DIR/lab-link.before"
ip -4 -br address show dev "$MGMT_IF" > "$NET_NOTE_DIR/management-addresses.before"
ip -4 route show table main > "$NET_NOTE_DIR/routes.before"
cat "$NET_NOTE_DIR/lab-link.before"
```

`>`は指定したfileへ出力を書き込み、同名fileがあれば置き換えます。ここでは新規directoryを使います。link flagでは、**単独の`UP` flag**があるか判断してください。`LOWER_UP`だけでは該当しません。各VMのshellで、次のどちらか**一方**の代入を行い、元の状態を記録します。

```bash
# Use this only if the standalone UP flag was present:
LAB_LINK_WAS=up
```

```bash
# Otherwise use this:
LAB_LINK_WAS=down
```

元の状態、MAC、interface名、baseline directoryもshellの外に記録してください。sessionが失われたときに後片付けで必要になります。

## 2つの一時addressを追加する

VMごとに該当するroleのblockを**1つだけ選びます**。この代入は文字列を保存するだけです。clientとserverのaddressを取り違えたり、両方のゲストに同じaddressを割り当てたりしないでください。

**Client VMのみ、通常ユーザー:**

```bash
LAB_IP=192.0.2.10
LAB_CIDR=192.0.2.10/24
LAB_PEER=192.0.2.20
```

**Server VMのみ、通常ユーザー:**

```bash
LAB_IP=192.0.2.20
LAB_CIDR=192.0.2.20/24
LAB_PEER=192.0.2.10
```

権限を上げる前に、対象をもう一度確認します。

**各VM、通常ユーザー:**

```bash
printf 'guest=%s lab=%s management=%s address=%s original-link=%s\n' \
  "$(hostname)" "$LAB_IF" "$MGMT_IF" "$LAB_CIDR" "$LAB_LINK_WAS"
ip -br link show dev "$LAB_IF"
```

roleと記録済みMACを照合します。その後、**各VMで通常ユーザーからsudoを実行し**、そのVMのラボaddressだけを追加します。

```bash
sudo ip link set dev "$LAB_IF" up
sudo ip address add "$LAB_CIDR" dev "$LAB_IF"
```

`link set ... up`は特定したラボNICを管理上有効にします。管理NICは変更しません。`address add`は**2つ目のNIC上**に、そのゲスト用のaddressを追加します。「管理NICに2つ目のIPv4 addressを追加する」操作ではなく、Linuxの表示に`secondary` flagを必ず出す必要もありません。

追加が成功すれば、通常は何も表示されません。`File exists`が出た場合はaddressを確認して停止してください。`replace`に切り替えたりinterface全体をflushしたりしません。元はdownだったラボNICをupにした後でaddress追加に失敗した場合でも、後述のlink状態の復旧は必要です。addressを削除するのは、自分の追加が成功した場合に限ります。

この`ip`による変更はkernelの現在の状態に適用され、NetplanやNetworkManagerの設定は変更しません。rebootすると手動で追加した設定は失われます。それより前にnetwork managerがaddressを削除または再作成することもあります。addressのlifetimeが`forever`なら、**この実行中のaddressに有効期限timerがない**という意味であり、rebootを越えて保持される意味ではありません。次のレッスンで永続設定を扱います。

## 各層で結果を読み取る

**各VM、通常ユーザー、確認のみ:**

```bash
ip -br link show dev "$LAB_IF"
ip -4 address show dev "$LAB_IF"
ip -4 route show dev "$LAB_IF"
ip -4 route get "$LAB_PEER"
```

client側では、関連する行が次のように表示されます。

```text
inet 192.0.2.10/24 scope global <lab-name>
    valid_lft forever preferred_lft forever
192.0.2.0/24 dev <lab-name> proto kernel scope link src 192.0.2.10
192.0.2.20 dev <lab-name> src 192.0.2.10 uid 1000
```

addressの表示は「このNICが`.10/24`を所有する」という意味です。`scope global`はLinuxのaddress scopeラベルです。文書用addressを、インターネットから到達可能なaddressに変えるものではありません。addressを追加すると、通常は接続prefix向けのrouteも作成されます。`proto kernel`は自動作成されたroute、`scope link`はnext-hop routerが不要なこと、`src`は優先されるsource addressを示します。serverも同様に`.20/24`を持ち、sourceとして`.20`を選ぶはずです。

`ip route get`は特定の宛先にどうrouteするかkernelに問い合わせます。**probe packetは送信しません**。peer宛てにはラボNICと正しいlocal sourceを選び、`via` gatewayを表示しないはずです。ほかの通信ができていても、管理NIC経由のrouteが選ばれたら設定エラーです。接続routeがない、またはaddressが消えた場合は、link状態と設定を管理するソフトウェアを調べてください。競合するdefault routeを追加してはいけません。

**両方のゲスト**の設定後、ARPがpeerを解決する必要が生じる程度の少量のtrafficを送ります。

**各VM、通常ユーザー:**

```bash
ping -4 -c 3 -W 2 -I "$LAB_IF" "$LAB_PEER"
ip -4 neigh show dev "$LAB_IF"
```

`ping -4`はIPv4 ICMP echoを使い、`-c 3`はrequestを3回に制限し、`-W 2`は応答timeoutを秒数で指定します。`-I`はラボinterfaceを選びます。一般的なiputilsパッケージでは通常ユーザーがこのecho testを実行できます。権限エラーはtoolまたはcapabilityの設定に関するもので、networkがdownである証拠ではありません。

ICMPを許可する正しい設定の経路では、応答と送受信packet数のsummaryが表示されるはずです。所要時間は変わるため、例にあるlatencyを自分の結果としてコピーしないでください。neighbor entryの例:

```text
192.0.2.20 dev <lab-name> lladdr 02:00:00:00:02:20 REACHABLE
```

`lladdr`を、ハイパーバイザーで記録した**相手側ラボNICのMAC**と比べます。`REACHABLE`は最近確認済み、`STALE`はcacheされた対応付けがあり、次に使うとき再確認が必要という意味です。直ちに失敗を示すわけではありません。trafficを送る前のtableが空でも正常です。`INCOMPLETE`は解決中、`FAILED`は解決に失敗した状態です。entryは動的なため、読んでいる間に状態が変わることがあります。

| 観察結果 | このレッスン内で次に調べること |
| --- | --- |
| carrierがない／`LOWER_UP`がない | ハイパーバイザーの仮想ケーブルと正しい内部networkへの接続 |
| IPv4 addressが間違っている／ない | role変数、追加結果、network managerがNICを変更したか |
| peerへのrouteが管理NICを使う | prefix、ラボaddress、route lookup |
| neighborが`INCOMPLETE`／`FAILED`のまま | 両VMの起動、同じ内部network、peer address、一意なMACとIP |
| neighborのMACは解決したがpingの応答がない | peer状態とICMP filtering。ARP成功はICMP／serviceの成功を意味しない |

この最初のtestを通すためにfirewallやIPv6を無効にしないでください。証拠を保存し、必要に応じてレッスン4の診断方法、レッスン6のfirewall policyへ進みます。

## 成功確認と正確な後片付け

設定を元に戻す前に、**両方のゲスト**で次を確認します。

1. MAC照合により、管理用とラボ用のinterfaceを別々に特定できる。
2. ラボNICにroleで指定した正確な`/24` addressと、接続済みの`192.0.2.0/24` routeがある。
3. peer宛てrouteがgatewayなしでラボNICと正しいsourceを使う。
4. neighborの結果を理解している。ICMP応答の成功が示すのは限定されたIP testであり、TCP serviceがlistenしていることではない。
5. 管理address、default route、元の管理アクセスが記録したbaselineと変わらない。

**各VM、通常ユーザー。保存した管理情報と現在の状態を比較:**

```bash
cat "$NET_NOTE_DIR/management-addresses.before"
ip -4 -br address show dev "$MGMT_IF"
cat "$NET_NOTE_DIR/routes.before"
ip -4 route show table main
```

新しいラボ接続routeがあるのは想定どおりですが、新しいラボdefault routeは不要です。DHCPが管理leaseを独自に更新する場合があります。動的な値をすべてラボの変更とみなすのではなく、interface、address、gateway、routeの目的を比べてください。

ここでVMごとに個別にrollbackを練習します。shellを失った場合は、記録したMACからNICを再特定し、そのゲスト自身の記録から`LAB_IF`、`MGMT_IF`、`LAB_IP`、`LAB_CIDR`、`LAB_LINK_WAS`、`NET_NOTE_DIR`を復元してください。現在の状態を確認します。変数は自動では残りません。削除するaddressを推測してはいけません。

**各VM、通常ユーザー。自分が追加に成功したaddressがまだあるか確認:**

```bash
ip -4 address show dev "$LAB_IF"
```

**各VM、通常ユーザーからsudoを実行。このVMで追加したaddressだけを削除:**

```bash
sudo ip address del "$LAB_CIDR" dev "$LAB_IF"
```

追加が成功し、addressもまだある場合にだけ削除を実行してください。すでにrebootした場合や、network managerが削除した場合は、不在を確認した上で削除を省略します。これは対象を絞った逆操作で、正確なIP、prefix、interfaceを指定します。addressもrouteも一括flushしません。IPv4が元々空だったことを前提に、唯一のラボIPv4 addressを削除すると、自動作成された接続routeも削除されます。

**各VM、同じshell。必要なときだけ通常ユーザーがsudoを実行:**

```bash
if [ "$LAB_LINK_WAS" = down ]; then
  sudo ip link set dev "$LAB_IF" down
fi
```

この条件分岐は、**自分がdownからupにした**linkだけを元に戻します。元からupだった場合はそのままにします。`[`は記録した値を検査し、特権コマンドを実行するのは`down`の場合だけです。値が見つからなければ、元の状態を推測せず記録を確認してください。

**各VM、通常ユーザー。復旧を確認:**

```bash
ip -br link show dev "$LAB_IF"
ip -4 address show dev "$LAB_IF"
ip -4 route show dev "$LAB_IF"
ip -4 -br address show dev "$MGMT_IF"
ip -4 route show default
```

ラボIPv4 addressと接続routeがなく、元の管理上のlink状態、管理設定、アクセスが復元されていることを確認します。動的に学習したneighbor entryは時間とともに消えることがあります。tableを空に見せるためflushしないでください。addressが再び現れた場合は、network managerが管理している可能性があります。繰り返し削除せず、停止して永続設定を調べてください。

baselineが不要になったら、その3つのfileと空のdirectoryだけを削除します。

**各VM、通常ユーザー:**

```bash
rm -i -- "$NET_NOTE_DIR/lab-link.before" \
  "$NET_NOTE_DIR/management-addresses.before" "$NET_NOTE_DIR/routes.before"
rmdir -- "$NET_NOTE_DIR"
test ! -e "$NET_NOTE_DIR"
echo $?
unset LAB_IF MGMT_IF LAB_IP LAB_CIDR LAB_PEER LAB_LINK_WAS NET_NOTE_DIR
```

自分が作ったsnapshot用のテキストfile3つだけを確認してください。存在確認の終了statusが`0`なら後片付けは成功です。`rmdir`が失敗したら、残っている正確なfile名を調べてください。永続network設定は編集していません。[レッスン3](03-persistent-configuration.md)では実際のnetwork managerを使って同じaddressを再設定します。このshellの変数や一時状態に依存することはありません。

## 参考資料と追加の読み物

一次資料は2026年9月14～15日に確認しました。

- [Ubuntu 24.04 `ip-address`マニュアル](https://manpages.ubuntu.com/manpages/noble/man8/ip-address.8.html)、[`ip-link`](https://manpages.ubuntu.com/manpages/noble/man8/ip-link.8.html)、[`ip-route`](https://manpages.ubuntu.com/manpages/noble/man8/ip-route.8.html)、[`ip-neighbour`](https://manpages.ubuntu.com/manpages/noble/man8/ip-neighbour.8.html): command構文、接続route、addressの有効期間、neighborの状態。
- [Ubuntu 24.04 `ping`マニュアル](https://manpages.ubuntu.com/manpages/noble/man8/ping.8.html): 範囲を限定したecho testとinterfaceの選択。
- [IETF RFC 1122](https://www.rfc-editor.org/rfc/rfc1122.html)、[RFC 4632](https://www.rfc-editor.org/rfc/rfc4632.html)、[RFC 826](https://www.rfc-editor.org/rfc/rfc826.html): Internet層、CIDR、IPv4 address解決。
- [IETF RFC 2131](https://www.rfc-editor.org/rfc/rfc2131.html)と[RFC 1034](https://www.rfc-editor.org/rfc/rfc1034.html): DHCPとDNSが異なる役割を持つこと。
- [IETF RFC 5737](https://www.rfc-editor.org/rfc/rfc5737.html)と[RFC 3849](https://www.rfc-editor.org/rfc/rfc3849.html): 文書用に予約されたaddress範囲。
- [IETF RFC 4291](https://www.rfc-editor.org/rfc/rfc4291.html)と[RFC 4861](https://www.rfc-editor.org/rfc/rfc4861.html): IPv6 addressingとNeighbor Discovery。

[クイズ](../../quizzes/networking/beginner/02-addressing-interfaces-quiz.md)で理解度を確認し、次に[永続的な設定](03-persistent-configuration.md)へ進んでください。
