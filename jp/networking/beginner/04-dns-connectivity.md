# 04. DNSと接続性の診断

> **対応バージョン**: Ubuntu Server 24.04 LTS（主な手順）、Rocky Linux 9（代替手順）
> **最終更新日**: 2026年9月15日

「serverに接続できない」という状況は、nameが解決されなかった、packetが誤ったrouteを通った、firewallが接続を拒否した、applicationがerrorを返した、など複数の意味を持ちます。以下の各testは、より小さな問いに答えます。次のtestを選ぶ前に結果と、その結果から分かる範囲を記録してください。

## 前提条件と学習目標

[永続的な設定](03-persistent-configuration.md)を終えてください。[コースのラボ](README.md)には、同じ内部仮想network上に`192.0.2.10/24`のclientと`192.0.2.20/24`のserverがあります。ラボには**DHCP、gateway、DNS server、uplinkがありません**。各guestの別のNAT／DHCP管理NICは変更しません。

guest consoleを使い、ハイパーバイザーに記録したMACと`ip -br link`を照合してラボNICを特定します。主なレッスンはpublic DNSやインターネット接続なしで進められます。public DNS queryを試す節は任意です。

| guestに準備済みのtool | 用途 |
|---|---|
| `ip`、`ping`、`getent`、`grep`、`timeout`、editor、sudo | ローカル設定、name解決、時間を制限したprobe |
| `dig` | DNS protocolのresponse確認。BIND utilitiesに含まれる |
| `tracepath`またはLinux `traceroute` | hop制限付きprobeへの応答観察 |
| `python3`（3.9以降）、`curl`、`ss` | 使い捨てpageの提供、HTTP／listen中socketの確認 |
| UbuntuのOpenBSD `nc`またはRockyの`ncat` | TCP接続testを1回実行 |
| systemd-resolvedがactiveな環境の`resolvectl` | 対象resolverの確認。Rockyでは必須でない |

`command -v ip ping getent timeout dig tracepath traceroute python3 curl ss nc ncat`で利用可能か確認します。任意alternativeが見つからなくても問題ありません。選んだ演習に必要なtoolがなければ、[guest toolの準備](README.md#guest-tools)に戻り、使用するpackage名と選択したtoolのインストール手順を確認してください。この章にはpackageのinstall commandはありません。

NSS lookupとDNSを区別し、authoritativeな応答とcacheを説明し、選択されたrouteを調べ、ICMP／trace結果を解釈し、TCPとHTTPを分けて考え、次の手順に根拠を付けた障害報告を書けるようになります。

## 1. name、DNS、OSの関係

DNSは分散databaseです。**A** recordはIPv4 address、**AAAA**はIPv6、**CNAME**はaliasから別nameへの参照、**PTR**は逆引きに使います。どのrecordも、宛先applicationが実行中だとは証明しません。

**recursive resolver**は、cacheされた情報を使うか、ほかのDNS serverへqueryしてclientのためにanswerを探します。**authoritative server**はzoneの公開dataを保持します。cacheは、許可された有効期間中、正のanswerも負のanswerも再利用できます。DNSの**TTL**は秒単位です。IPのTTLはhop上限であり、別の意味です。今DNS TTLを短くしても、以前のTTLでcache済みのcopyが即時に消えるわけではありません。[DNSの概念](https://www.rfc-editor.org/rfc/rfc1034.html)と[negative caching](https://www.rfc-editor.org/rfc/rfc2308.html)を参照してください。

Linux applicationはC libraryを介し、**NSS**（Name Service Switch）でnameを問い合わせる場合があります。NSSは`/etc/nsswitch.conf`でsourceを選択します。`files`は`/etc/hosts`、`dns`はDNS、`resolve`はインストール／設定済みの場合にsystemd-resolvedを使います。ほかのmoduleや角括弧付きの応答規則で検索順が変わることもあります。DNS over HTTPSを使うbrowserなど、独自resolverを持つapplicationは異なる動作をする場合があります。

| tool | 答える問い |
|---|---|
| `getent ahostsv4 NAME` | このsystemのNSS／getaddrinfo経路はどのIPv4 addressを返すか |
| `getent hosts NAME` | NSSのhosts検索は何を返すか。address familyの動作は`ahostsv4`と異なる |
| `getent -s files hosts NAME` | `files` sourceだけにこのnameがあるか |
| `dig @SERVER NAME A` | 指定したserverはどんなDNS responseを返すか。query nameのNSS lookupは使わない |
| `resolvectl query NAME` | systemd-resolvedのresolver interface経由で何が返るか |

**client**で編集せずに確認します。

```bash
grep '^hosts:' /etc/nsswitch.conf
cat /etc/hosts
ls -l /etc/resolv.conf
cat /etc/resolv.conf
systemctl is-active systemd-resolved
```

例えば`hosts: files dns`なら、DNSより先にhosts fileを検索します。この例で自分の実際の行を置き換えないでください。`/etc/resolv.conf`は生成済みstub file、生成済みupstream一覧、または別の方法で管理されるfileへのsymlinkの場合があります。`nameserver 127.0.0.53`はlocal loopback stubを示すもので、routerではありません。

systemd-resolvedがactiveな**Ubuntu client**では:

```bash
resolvectl status
resolvectl statistics
```

linkごとのDNS server、search domain、cache統計を確認します。コースラボNICからDNSは提供されません。管理用DNSは引き続き表示されることがあります。NetworkManagerが管理する**Rocky client**では、`nmcli -f GENERAL,IP4,IP6 device show`と前述のresolver fileの確認を使います。Ubuntuと同じ配置にするためだけにresolvedをインストールしたり、symlinkを書き換えたりしないでください。永続的な修正は、chapter 03で確認した設定元が管理する場所に行います。

## 2. 2台のVMにローカルnameを付ける

**client**で`/etc/hosts`を使うと、ローカルラボに外部resolverは不要です。以下のnameはローカルaliasです。guest名の変更、DNS recordの作成、remote serverの設定は行いません。`.test`はtest用に予約されたsuffixです。multicast DNSで特別な意味を持つ`.local`は避けてください。

まず競合がないか確認します。

```bash
grep -nE 'netlab\.test|BEGIN network-beginner-04|END network-beginner-04' /etc/hosts
```

初回実行時は、終了statusが1で出力なしとなるのが想定結果です。entryがある場合は続行する前に確認し、重複mappingを追加しないでください。新しい復旧用directoryを作り、backupを保存します。

```bash
sudo mkdir -m 700 /root/network-beginner-04
sudo cp -a /etc/hosts /root/network-beginner-04/hosts-before
sudoedit /etc/hosts
```

すでにdirectoryがある場合は、以前の作業を確認して停止してください。次のblockだけをfile末尾に追加し、既存のlocalhostとguest hostnameのentryは残します。

```text
# BEGIN network-beginner-04
192.0.2.10 client.netlab.test
192.0.2.20 server.netlab.test
# END network-beginner-04
```

filesだけのlookupと、通常のapplication lookupを比較します。

```bash
getent -s files hosts server.netlab.test
timeout 5s getent ahostsv4 server.netlab.test
timeout 5s getent hosts server.netlab.test
```

最初の2つの結果には`192.0.2.20`が含まれるはずです。`ahostsv4`は`STREAM`、`DGRAM`、`RAW`に対応して同じaddressを繰り返す場合があります。これはsocket typeを示しており、serverが3台ある意味ではありません。`hosts`はIPv4より先にIPv6 lookupを行い、別の経路や長い時間を使う場合があります。timeout（status 124）は時間を区切った観察結果であり、DNSがnameの不存在を返した証拠ではありません。

files-onlyのlookupが成功して通常lookupが失敗する場合は、NSSの順序／moduleと、綴り／address familyが一致しているか確認します。name lookupを直すためにrouteを変更しないでください。server自身がこのnameを使う場合にのみ、serverにもhosts entryが必要です。serverで繰り返す場合は別途backupが必要です。

### 外部依存なしでdigと比較する

hosts entryが動作し、resolvedがactiveな**Ubuntu client**で実行します。

```bash
resolvectl --network=no -4 query server.netlab.test
dig -r @127.0.0.53 server.netlab.test. A +time=2 +tries=1
```

`--network=no`はresolvedがnetworkへqueryするのを防ぎます。local source／cacheでanswerが得られるか、local failureが返ります。`dig -r`は個人の`.digrc`設定を読み飛ばします。`@127.0.0.53`でstubを選択し、末尾のdotでDNS nameをabsoluteにします。optionは待機とretryに上限を設けます。一般的なresolved設定は`/etc/hosts`を読み、両方のcommandへ`.20`を返すことがあります。digもDNS queryは送信していますが、stubがlocal dataからanswerを合成しています。したがって「digはhosts fileのentryを決して返さない」と言うのは正確ではありません。

stubが無効、またはresolvedによるhosts file読込が無効なら、この分岐は成功しない場合があります。serviceを有効化せず、現在のresolver設定を確認してください。**どちらのdistributionでも**、hosts lookupとラボserverへのDNS queryを比較します。

```bash
dig -r @192.0.2.20 server.netlab.test. A +time=2 +tries=1
```

これは**意図した失敗probe**です。コースserverにはDNS serviceを実行していないため、answerではなくrefusalまたはtimeoutが想定結果です。clientのhosts entryを追加してもserverはDNS serverにはなりません。想定外のanswerが返ったら、serverのport 53で何がlistenしているか調べてください。通常のapplicationはhosts mappingを使い続けます。system DNSを`.20`に向けないでください。

`@SERVER`を指定しないとdigは`/etc/resolv.conf`を読みます。一見localなtestでも、管理networkのupstream resolverへqueryする可能性があります。上記commandでは対象を明示しています。

### DNS responseの読み方

以下は**仮想的なauthoritative lab DNS serviceのresponse例**であり、実際に取得した出力でも、このレッスンで作成するserviceでもありません。

```text
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 1234
;; flags: qr aa; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0
;; ANSWER SECTION:
server.netlab.test. 300 IN A 192.0.2.20
;; SERVER: 192.0.2.53#53(192.0.2.53) (UDP)
```

| field／status | 解釈 |
|---|---|
| `SERVER` | queryに回答したserver。authoritative originとは限らない |
| `300 IN A 192.0.2.20` | TTL秒数、Internet class、IPv4 typeとaddress |
| `aa` | query対象nameについてanswerがauthoritativeと示されている。接続性やidentityを保証しない |
| `rd`／`ra`がある場合 | recursionを要求／recursionが利用可能。どちらもupstreamへ新規queryした証拠ではない |
| `NOERROR`と想定answer | DNS queryは成功。data自体を確認する |
| 要求したdataなしの`NOERROR` | NODATAの可能性がある。結論を出す前にAuthority／CNAME／referralの文脈を調べる |
| `NXDOMAIN` | queryされたnameが存在しないとDNS responseが返した。cacheやpolicyによる場合もある |
| `SERVFAIL` | upstreamやvalidation問題などでresolverが失敗した |
| `REFUSED` | server policyがqueryを拒否した |
| timeout | 待機時間内に利用できるresponseがない。NXDOMAINではない |

`dig +short`は有用なstatusとserver情報を隠すため、診断中はfull outputを使います。digは`NXDOMAIN` responseを受信しても終了status 0を返す場合があります。終了statusだけでaddressが見つかったとは判断できません。

application、local service、upstream recursive resolverでcacheされることがあります。2回目が速いというだけではcache hitの証明になりません。resolvedでは`resolvectl statistics`を比較します。hostsから得たanswerはDNS recordのcacheとは動作が異なる場合があります。`sudo resolvectl flush-caches`はresolvedのlocal DNS cacheを消しますが、`/etc/hosts`、application cache、upstream cacheは消しません。消したcacheはqueryにより再度構築される一時状態で、意味のある「cache復元」操作はありません。このラボに不要です。別のcache調査で使う前に証拠を記録してください。

## 3. 選択されたrouteを調べ、次にIPをprobeする

**client**でラボMACをもう一度照合し、NIC名を指定します。

```bash
LAB_IF='REPLACE_WITH_CLIENT_LAB_NIC'
ip -br link
ip -4 address show dev "$LAB_IF"
ip -4 route get 192.0.2.20
ip -4 route show default
```

route結果の例:

```text
192.0.2.20 dev LAB_NIC src 192.0.2.10 uid 1000
```

`dev`は出力interface、`src`は選択されたsource address、`via`はnext-hop routerを示します。ここではpeerがon-linkなので`via`は不要です。`LAB_NIC`は説明用のlabelであり、実際のdevice名ではありません。`ip route get`はlocal route lookupで、pingを送らず、peerが利用可能か、reply routeが正しいかも証明しません。

lookupが管理NICを選んだ場合はpeerへのprobeを停止し、ラボaddress／prefixと保存済み設定を調べます。管理用default routeを削除しないでください。**server**側では`ip -4 route get 192.0.2.10`がsource `.20`を使い、ラボNICを選ぶはずです。responseにも有効な戻りrouteが必要です。

**client**でloopback、自分のaddress、peerを比較します。

```bash
ping -n -c 3 -W 2 127.0.0.1
ping -n -c 3 -W 2 192.0.2.10
ping -n -c 3 -W 2 192.0.2.20
```

`-n`はreverse name lookupを抑制し、`-c 3`はEcho Requestを3回送信し、`-W 2`はreplyがない場合の待機を制限します。数値の宛先を指定すると、このtestからforward name lookupを除外できます。`time`はround-trip timeであり、bandwidthではありません。reply内の`ttl`は受信packetに残ったTTLです。初期値が分からないと正確なhop数にはなりません。

loopback成功はlocal stackをtestします。自分のラボaddressへのpingは通常localで処理され、仮想cableはtestしません。peerからのreplyは、その時点の双方向ICMP Echo交換を示すだけで、TCP portへのaccessを示すものではありません。replyが3つない場合、分かるのは3つのprobeの観察結果です。filtering、response rate limit、address誤り、戻り経路を調べる必要があります。

peerへのprobe後、**client**のneighbor entryを確認します。

```bash
LAB_IF='REPLACE_WITH_CLIENT_LAB_NIC'
ip neigh show to 192.0.2.20 dev "$LAB_IF"
```

`REACHABLE`または`STALE`のMACはneighbor mappingがあることを示します。`STALE`は失敗ではありません。`INCOMPLETE`／`FAILED`ならARP解決に失敗した可能性があります。両adapterの内部network接続、peer address、carrier、duplicate IPの可能性を調べてください。DNSはEthernet宛先MACを提供しません。

## 4. tracerouteとtracepathを慎重に読む

**client**で、準備したtoolを実行します。

```bash
traceroute -4 -n -m 4 -q 1 -w 1 192.0.2.20
timeout 15s tracepath -4 -n -m 4 192.0.2.20
```

Linuxのtracerouteは通常UDP probeを使います。`-m 4`は最大TTL、`-q 1`は各TTLあたりのprobe数を1つ、`-w 1`はprobeごとの待機時間を設定します。tracepathもUDPを使い、path MTUの情報も表示します。外側の`timeout`は実行全体の時間を制限します。peerへ直結し、replyが許可されていれば、TTL 1で宛先が表示されるはずです。仮想Ethernet switchはIP routerではないため、tracerouteのhopを増やしません。

probeのTTLが切れると、routerはICMP Time Exceededを返す場合があります。閉じたUDP port宛てのprobeには、宛先からICMP Port Unreachableが返ることがあります。これらのcontrol responseは経路の一部を示すもので、全packetの経路を記録したものではありません。

tracerouteの`*`やtracepathの`no reply`はtimeout前に対応する応答がなかったという意味です。そのhopが通常のapplication trafficをdropした証明には**なりません**。filtering、rate limiting、probe protocolの違い、非対称な戻り経路が応答欠落の原因となることがあります。後続hopやapplicationが応答する場合もあります。

インストール済みLinux tracerouteが対応する場合は、同じpeerに対し任意の**ICMP比較**を行います。

```bash
sudo traceroute -4 -I -n -m 4 -q 1 -w 1 192.0.2.20
```

`-I`はICMP Echo probeを使います。必要な場合、sudoでraw probeを許可します。結果の違いはprotocol別policyによる場合があります。これらのcommandは永続設定を変更しません。trace表示をきれいにするためfirewallを無効にしないでください。

## 5. 一時serviceを使ってTCPとHTTPを区別する

SSHやWeb serverがすでにインストールされているとは限りません。Pythonがあれば一時HTTP serviceを作れます。listenerは**server側のラボaddressだけ**にbindします。

### serverで実行時間を限ったserviceを起動する

**server terminal A**で、`.20`がラボNICにあり、port 18080に既存TCP listenerがないことを確認します。

```bash
ip -br address
ss -ltn 'sport = :18080'
```

listenerがある場合は何か特定してください。別serviceをkillしてはいけません。空きportを選び、この節全体で統一して置き換えるか、先行ラボを完了してください。

同じ**server terminal A**で新規directoryを作り、通常ユーザーとして配信します。

```bash
LAB_HTTP_DIR=$(mktemp -d /tmp/network-beginner-04.XXXXXX)
printf '%s\n' "$LAB_HTTP_DIR"
printf 'network lab ok\n' > "${LAB_HTTP_DIR:?missing lab directory}/index.html"
timeout 300s python3 -m http.server 18080 --bind 192.0.2.20 --directory "${LAB_HTTP_DIR:?missing lab directory}"
```

`mktemp`が失敗したら停止します。`${variable:?message}`はpath変数が空の場合の使用を防ぎます。表示されたdirectory pathを記録してください。配信対象fileは新しいdirectoryの中だけにします。home directoryを配信したりsymlinkを追加したりしないでください。`--bind`はwildcard listenerを避け、`--directory`はcontent rootを選びます。`timeout`は5分後にserverを終了します。Ctrl+Cで早く停止できます。時間切れの終了status 124は想定どおりです。

演習の途中でtimerが切れた場合、同じserver terminal Aで次を再実行します。記録したdirectoryを再利用し、`mktemp`はやり直しません。

`timeout 300s python3 -m http.server 18080 --bind 192.0.2.20 --directory "${LAB_HTTP_DIR:?missing lab directory}"`

Python組み込みHTTP serverは演習用です。ここでは認証もTLSもなく、本番deploy向けではありません。system serviceや起動時自動実行は作成しません。

**server terminal B**で、Aが実行中の間に確認します。

```bash
ss -ltn 'sport = :18080'
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:18080/
```

`192.0.2.20:18080`のlistener、HTTP 200、`network lab ok`を確認するはずです。RockyのPython 3.9経路を含め、このPython serverではresponseがHTTP/1.0でも正常です。この自己requestはlocal application動作を検証しますが、clientからの経路は検証しません。bind時に「Cannot assign requested address」が出たらchapter 03でserverのaddressを確認します。permission拒否が出てもSELinuxを無効化せず、その失敗を調べます。

### clientからTCPをtestする

OpenBSD netcatを使う**Ubuntu client**:

```bash
nc -n -z -v -w 3 192.0.2.20 18080
```

Ncatを使う**Rocky client**で同じtestを実行:

```bash
ncat -n -z -v -w 3 192.0.2.20 18080
```

`-n`はDNSを使わず、`-z`はapplication payloadなしで接続確立をtestし、`-v`は結果を表示し、`-w 3`は接続待機を制限します。成功はそのendpointへのTCP接続が可能だった証拠ですが、HTTPが動く証明ではありません。拒否ならportが閉じているか、明示的にrejectされた可能性があります。timeoutならfiltering、neighbor未解決、peer停止、戻り経路などが考えられます。

特に設定済みのRocky firewalld policyなど、guest firewallが新しいportを遮断する場合があります。serverのlistener／自己requestと、clientのroute／neighbor／TCP証拠を比較し、**policy境界の候補**を記録します。この章ではfirewall ruleを変更しません。[chapter 06](06-firewalls-host-security.md)で範囲を絞ったpolicy変更を扱います。remote testが遮断されてもserver terminal BでHTTP観察を完了し、client側の失敗は後のレッスン用に記録してください。server自身へのrequestをremote HTTP成功として報告しないでください。

### HTTPをtestし、nameを比較する

serviceが動作中の**client**で実行します。

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:18080/
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://server.netlab.test:18080/
```

最初のoption `--disable`はcurlの既定設定を読み飛ばします。`--noproxy '*'`は引き継いだHTTP proxyを使わない指定です。`--connect-timeout`は接続確立、`--max-time`は処理全体の時間を制限し、`-i`はresponse headerを含めます。2つ目のcommandはclientのname lookupを使います。数値URLが動きname付きURLが失敗したら、routeを触る前に`getent ahostsv4`とcurl errorを比較します。

この**curl呼び出し1回だけ**でlookupを切り分けるには、hostnameを維持しつつ既知のラボaddressを指定します。

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  --resolve server.netlab.test:18080:192.0.2.20 \
  -i http://server.netlab.test:18080/
```

`--resolve`はそのhostname／portに対するcurl内のmappingだけを変更します。hosts fileやDNS recordは変わらず、rollbackも不要です。HTTP Host headerでは引き続きnameを使います。HTTPSではnameに基づくcertificate確認とTLS SNIも関係します。hostnameをIPに置き換えても、application testが常に同等になるわけではありません。certificate検証を迂回してTLSが「修正済み」と扱わないでください。

存在しないfileを要求し、害のないapplication-level failureを作ります。

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:18080/missing-page
```

serverに到達可能ならHTTP **404**を想定します。name／IP経路とTCP transportがHTTP errorを返せるところまで動きましたが、要求したpageはありません。`--fail`を付けないとcurlはHTTP 404でも終了status 0を返すため、status lineを読んでください。`curl -I`はbodyを隠したGETではなく**HEAD**を送信します。

## 6. 証拠に基づいて次のtestを選ぶ

この判断表を順に使います。ただし新しい証拠が前提と矛盾したら前の行に戻ってください。例は候補を示しており、自動的な診断ではありません。

| 観察結果 | 確認できたこと | 次に区別する確認 |
|---|---|---|
| files-only lookupに`.20`がない | local mappingがない／誤っている | 正確な綴り、`/etc/hosts`の箇所、重複entry |
| files-only成功、通常のgetent失敗 | sourceごとに動作が異なる | NSS順序／応答規則、module、address family |
| getent成功、`.20`へのdig失敗 | local name解決は動作するが、`.20`に想定したDNS serviceはない | hosts entryを使う。DNSが必要な場合だけ本来のresolverを調べる |
| DNS `NXDOMAIN` | 否定的DNS responseが返った | queryの綴り、resolver view、authoritative data、negative cache |
| DNS timeout | 制限時間内に使用可能なDNS answerなし | resolverへの`ip route get`、port 53の到達性、resolver service／policy |
| routeが管理NICまたは誤ったsourceを選ぶ | このラボで使うlocal転送経路が誤り | ラボaddress／prefix、永続設定元、route／rule一覧 |
| routeは正しいがneighborが`FAILED` | next-hop MAC解決失敗 | ハイパーバイザーnetwork／cable、peer address、link状態、競合 |
| neighborあり、ping失敗 | MAC既知、ICMP replyなし | serverの戻りroute、ICMP policy、その後に対象TCP port |
| ping成功、TCP拒否 | ICMP動作、TCPは明示的に拒否 | serverの`ss`、serviceの稼働時間／bind address、拒否policy |
| server自己HTTP成功、client TCP timeout | local serviceは動くがremote経路は未確認 | 両方のroute、neighbor、host policy。chapter 06用に証拠を記録 |
| TCP接続成功、HTTP停止または不正 | 接続確立は成功 | 正しいprotocol／port、application log、response動作 |
| HTTP 404／403／500 | HTTP endpointがapplication resultを返した | 要求path、application permission、service error。DNSの問題ではない |
| 数値HTTP成功、name付きHTTP失敗 | 通常lookupなしで既知endpointへ到達できた | getent、curlの解決error、request単位の`--resolve`比較 |
| tracerouteが`*`、HTTP成功 | trace probeはreplyなしだがapplicationは成功 | probe protocol／rate limit。packet全体の損失とは言えない |

curlの終了codeには**6**（host名を解決できない）、**7**（接続できない）、**28**（処理がtimeout）がよくあります。これは失敗した段階を絞るもので、必ずしも根本原因ではありません。command、実行VM、時刻（`date -Is`）、宛先、output、終了status（直後に`echo $?`）、期待結果、次のtestを記録します。「観測」と「推測」を分けてください。

## 7. 任意のpublic DNS観察

**外部依存あり:** 既存の変更していない管理networkに、許可済みのインターネット接続と選択resolverへのquery許可がある場合だけ実行してください。完了条件ではありません。失敗しても、隔離された`.10` ↔ `.20`ラボについて直接分かることはありません。ラボNICにuplinkやpublic DNS serverを追加しないでください。

```bash
ip -4 route get 1.1.1.1
dig -r @1.1.1.1 example.com. A +time=2 +tries=1
dig -r @1.1.1.1 example.com. AAAA +time=2 +tries=1
dig -r @1.1.1.1 example.com. NS +time=2 +tries=1
```

query送信前にrouteを確認します。既存の管理経路を使うはずです。policy上、別の承認済みresolverが必要なら、その既知addressに一貫して置き換えてください。DNS status、server、record type、TTLを確認します。public IP addressが固定だとは想定しません。A queryをもう一度実行してTTLを比較しますが、時間だけからcache場所を推測しないでください。`+tcp`は通常のUDP A queryとDNS over TCPを任意に比較するoptionです。private／internal nameをpublic resolverへqueryしてはいけません。

NS answerはauthorityに関する情報を示します。`1.1.1.1`からのrecursive answerが、zoneのauthoritative responseになるわけではありません。`dig +trace`はDNS delegationをたどります。tracerouteのようにIP routerのhopを調べるものではなく、外部依存も追加するため、このlocal演習の範囲外です。

## 8. 後片付けと完了確認

**server terminal A**でPython processをCtrl+Cで停止するか、timer終了まで待ちます。terminal Bで`ss -ltn 'sport = :18080'`を実行し、このレッスンのlistenerがなくなったことを確認します。

directoryを作った**同じterminal Aのshell**で、中身を確認して自分のfileと空directoryだけを削除します。

```bash
printf '%s\n' "$LAB_HTTP_DIR"
ls -la -- "${LAB_HTTP_DIR:?missing lab directory}"
rm -i -- "${LAB_HTTP_DIR:?missing lab directory}/index.html"
rmdir -- "${LAB_HTTP_DIR:?missing lab directory}"
unset LAB_HTTP_DIR
```

そのshellを閉じた場合は、記録した正確なpathを`LAB_HTTP_DIR`に設定し、このblockを実行する前に中身を確認してください。広いwildcardで推測しないでください。`rmdir`は空でないdirectoryを削除しないため、想定外のfileがあれば分かります。

`/etc/hosts`を編集したguestでは、`sudoedit /etc/hosts`を開き、`# BEGIN network-beginner-04`から`# END network-beginner-04`までの行だけを、marker 2行も含めて削除します。`sudo diff -u /root/network-beginner-04/hosts-before /etc/hosts`で比較します。無関係な編集がなければ出力なしとなり、元の内容に戻ったことを示します。間に正当な編集が加わっていたらbackupで上書きせず、それらを保持します。

`getent -s files hosts server.netlab.test`がレッスンのmappingを返さないことを確認します。すべてのresolverが瞬時にnameを忘れると期待しないでください。chapter 03のstatic addressと管理設定はSSHのために保持します。

次に進む前に、次のことができるはずです。

- guest上で実際に使われているsourceを元にgetent／NSS、dig、resolvedを説明する。
- public DNSなしで`.20`をlocal解決し、意図したdig失敗の理由を説明する。
- TTL、authoritative status、否定responseを含むDNS responseを解釈する。
- 選択されたラボroute／sourceを示し、loopback、neighbor、peerの証拠を区別する。
- tracerouteの無応答がapplication packet lossを示すとは限らない理由を説明する。
- TCP test、HTTP 200、HTTP 404を比較し、各結果をどちらのVMが生成したか特定する。
- remote testが遮断された場合、local成功で代用せず、証拠と次の確認を示す。
- network／firewall設定を変更せず、一時server、file、hosts entryを削除する。

## 主要資料と追加の読み物

- [Ubuntu Server: nameとNSS](https://documentation.ubuntu.com/server/explanation/networking/configuring-networks/)、[getent manual](https://manpages.ubuntu.com/manpages/noble/en/man1/getent.1.html)
- [BIND dig manual](https://bind9.readthedocs.io/en/latest/manpages.html#dig-dns-lookup-utility)、[Ubuntu 24.04のresolvectl](https://manpages.ubuntu.com/manpages/noble/en/man1/resolvectl.1.html)
- [DNSの概念: RFC 1034](https://www.rfc-editor.org/rfc/rfc1034.html)、[negative caching: RFC 2308](https://www.rfc-editor.org/rfc/rfc2308.html)、[test name: RFC 2606](https://www.rfc-editor.org/rfc/rfc2606.html)
- [ping](https://manpages.ubuntu.com/manpages/noble/en/man8/ping.8.html)、[tracepath](https://manpages.ubuntu.com/manpages/noble/en/man8/tracepath.8.html)、[Ubuntu付属Linux traceroute manual](https://manpages.ubuntu.com/manpages/noble/en/man1/traceroute.db.1.html)
- [OpenBSD nc](https://man.openbsd.org/nc)、[Ncat](https://nmap.org/book/ncat-man.html)、[curl manual](https://curl.se/docs/manpage.html)、[Python HTTP server](https://docs.python.org/3.12/library/http.server.html)
- 後の[Linux network診断](../07-linux-network-diagnostics.md)ではpacket、TCP queue、MTUの解釈を扱います。

[前へ: 永続的な設定](03-persistent-configuration.md) · [クイズ](../../quizzes/networking/beginner/04-dns-connectivity-quiz.md) · [次へ: SSH access](05-ssh-access.md)
