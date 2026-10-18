# Linuxネットワーク診断: HTTP、TCP queue、ルーティング、MTU

> **対応環境**: Linux、Python 3.9以降、curl、iproute2。ルーティング演習にはローカルDocker Engineを使う。
> **最終更新日**: 2026年9月15日

Linuxでリクエストを発行し、socketと次ホップを特定してから、コンテナnamespaceをまたぐ同じパケット経路を説明します。この演習を通して、KubernetesやAWSネットワークを調べる前に、アプリケーション、トランスポート、ルーティングの各証拠を区別します。

CLI、IP設定、DNS、SSH、ファイアウォールから練習するには、まず[初心者向け8レッスン](beginner/README.md)を完了してください。その後、このガイドでsocket、ICMP、PMTUの観察を深めます。

演習と併せて、[IPv4と次ホップの基礎](../basics/06-network-fundamentals-part1.md#ipv4-cidr-subnet)と[HTTPメッセージ構造](../basics/06-network-fundamentals-part3.md#http11-message-structure)を読みます。

- [HTTPメッセージ](#http-message-lab)
- [TCP queueとbuffer](#tcp-buffer-lab)
- [ルーティングとICMP](#routing-icmp-lab)
- [MTU、PMTU、MSS](#mtu-mss-lab)
- [Dockerのパケット経路](#docker-packet-path)

## スコープと準備 {#lab-scope}

このリポジトリをcheckoutした場所からコマンドを実行します。指示があれば端末を分けてください。

| 演習 | 要件 | 範囲 |
|---|---|---|
| HTTP | Python 3.9以降、curl | `127.0.0.1:18080`でサーバーを1つ起動し、自動停止 |
| TCP観察 | HTTPサーバー、Python、iproute2の`ss` | ローカルテストポートの読み取り専用観察 |
| ルーティングとMTU | Linux Docker Engine、Docker CLI、ホストのiproute2、pull済みイメージ | 一時コンテナ3つと専用bridge 2つ |

補助スクリプトは[http_lab.py](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/networking/foundations/http_lab.py)と[routing_lab.py](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/networking/foundations/routing_lab.py)です。実行前に、それぞれの契約と[examples README](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/networking/foundations/README.md)を読んでください。

コマンドは手順を示します。HTTP応答の抜粋は**説明用**です。ルーティングの抜粋で明示されたものは、記録済み参照実行からのものであり、あなたのマシンの実行結果ではありません。自分の実行は、記載された基準とrouting helperのJSON記録に照らして評価してください。

HTTP helperは教材用の小さなHTTP/1.1サーバーであり、本番サーバーでもRFCの完全実装でもありません。リクエストbodyは最大4096 byte、対応する`Content-Length` framingだけを受け付け、transfer codingは拒否します。

Routing helperは`unix:///var/run/docker.sock`だけを使い、リモートDocker host／context環境変数の選択は無視します。ローカルLinux Engineとそのsocketへのアクセスが必要です。リモートcontextや場所の異なるrootless socketでは代用できません。

`IMAGE`定数で次の参照イメージを固定しています。実行対象のEngineにあらかじめ存在している必要があります。

```text
nicolaka/netshoot:v0.16@sha256:b09d9b21381f47a79b3cbcb30da25266dc17186ea00ae65e99fdc51396f48e70
```

helperはイメージをpullしません。リソース作成前に、固定サブネットが見えるホストIPv4経路や既存Docker networkの範囲と衝突しないか確認します。ルーティング演習は一度に1つだけ実行します。衝突したら停止し、共有ホストの経路を変更しないでください。

## ラボ1: HTTPメッセージを読む {#http-message-lab}

**目的:** request／status line、fields、header終端、content byteを区別します。

端末Aでサーバーを起動します。

```bash
python3 examples/networking/foundations/http_lab.py --port 18080 --duration 120
```

`127.0.0.1`だけにbindし、120秒後に終了します。許可される最大時間は600秒です。ポートが使用中なら、別の空きローカルポートを選び、コマンドとfilterで一貫して使います。無関係なlistenerを停止しないでください。

端末BでGETとHEADを送ります。

```bash
curl --disable --noproxy '*' --max-time 5 --http1.1 -i http://127.0.0.1:18080/lesson
curl --disable --noproxy '*' --max-time 5 --http1.1 -I http://127.0.0.1:18080/lesson
```

先頭の`--disable`はcurlの既定設定を読み込まないための指定です。`--noproxy '*'`は設定済みproxyを回避します。`-i`は応答headerを含めます。`-I`はHEADを送るもので、bodyを隠した通常のGETではありません。

説明用のGET応答抜粋を示します。生成された`Date`と`Server` fieldは省略しています。

```http
HTTP/1.1 200 OK
Content-Type: text/plain; charset=utf-8
Content-Length: 6

hello
```

実際のbodyは`b"hello\n"`、16進数では`68 65 6c 6c 6f 0a`です。最後のLFも含めて6 byteです。HTTP/1.1のwire上ではheader行とheader／bodyの区切りにCRLFを使います。このMarkdown表示ではLFを使います。

同じ6 byteをecho endpointに送ります。

```bash
printf 'hello\n' | curl --disable --noproxy '*' --max-time 5 --http1.1 -i \
  -H 'Content-Type: text/plain' --data-binary @- \
  http://127.0.0.1:18080/echo
```

`--data-binary @-`はstdinからLFを取り除かず読み込み、POSTを選択します。helperは受け取ったbyteをそのまま`Content-Type: application/octet-stream`で返します。テキスト、JSON、formは解析しません。

| 観察 | 期待する基準 | 解釈 |
|---|---|---|
| GET `/lesson` | HTTP/1.1 200、length 6、contentは6 byte | lengthはstart lineとheaderを含まない |
| HEAD `/lesson` | HTTP/1.1 200、length 6、応答bodyなし | fieldは対応するGETのrepresentationを表す |
| POST `/echo` | HTTP/1.1 200、length 6、LF付き`hello`を変更せず返す | byte保存とmedia typeの解釈は別 |

非ASCII文字はUTF-8で複数byteになることがあります。見える文字数ではなく、実際の改行を含めて送信されたencoding後のbyte数を数えてください。

クライアントのdebug traceからrequest lineと送信fieldを確認します。

```bash
curl --disable --noproxy '*' --max-time 5 --http1.1 --trace-ascii - \
  --output /dev/null http://127.0.0.1:18080/lesson
```

これは**curlのクライアント側debug出力**であり、パケットキャプチャではありません。注釈はwire byte、TCP segment境界、ルーターが見た内容の証拠ではありません。trace収集にはデモデータだけを使います。

HTTPSでは、クライアントがHTTPの平文を表示できても、受動的なネットワークキャプチャからはsession secretなしに読み取れません。HTTP/2とHTTP/3は別のbinary framingを使います。ツールが読みやすく表示しても、raw encodingとは異なります。

**クリーンアップ:** 端末AでCtrl+Cを押すか、timerが切れるまで待ってサーバーを停止します。永続的なアプリケーションデータは作りません。timer切れ後に次の演習でも使う場合は、再起動してください。

## ラボ2: TCP queueとbufferを観察する {#tcp-buffer-lab}

**目的:** 1つの持続接続をsocket状態、stream queue、メモリ計上に関連付けます。

端末Aで同じ120秒サーバーを起動します。端末Bで、実行時間を限定した次のクライアントを動かします。

```bash
python3 - <<'PY'
import http.client
import time

connection = http.client.HTTPConnection("127.0.0.1", 18080, timeout=2)
try:
    for number in range(30):
        connection.request("GET", "/lesson")
        response = connection.getresponse()
        body = response.read()
        assert response.status == 200
        assert response.getheader("Content-Length") == "6"
        assert body == b"hello\n"
        if number == 0:
            print("Client endpoint:", connection.sock.getsockname(), flush=True)
        time.sleep(1)
finally:
    connection.close()
PY
```

クライアントは各応答を読み切ってから接続を再利用します。1秒間隔で小さなGETを30回送り、個別に短命なcurlプロセスを使うより、確立済みsocketを観察しやすくします。

動作中に端末Cで実行します。

```bash
ss -ltn 'sport = :18080'
ss -tinm state established '( sport = :18080 or dport = :18080 )'
```

2つ目のコマンドを何度か繰り返します。現在のnetwork namespaceを調べ、テストポートに絞ります。loopback接続のローカル側両端が表示される場合があるため、サーバーポートとクライアントのephemeral portを区別してください。

**期待する基準:** `127.0.0.1:18080`でlistenerが存在し、クライアントの実行中に確立済み接続が見えること。queue、RTT、memoryの具体値は異なります。この小さな負荷でqueueが0でも正常です。

| field／状態 | 意味 |
|---|---|
| ESTABLISHED `Recv-Q` | 順序どおり受信済みだが、アプリケーションがまだ読み取っていないbyte |
| ESTABLISHED `Send-Q` | 未送信分も含む、まだacknowledgeされていないstream byte |
| LISTEN `Recv-Q` | `accept()`待ちの接続数。payload byteではない |
| LISTEN `Send-Q` | accept backlogの最大値。送信bufferサイズではない |
| `skmem` `r`／`rb` | 受信memory計上／受信memory予算 |
| `skmem` `w`／`tb` | queue内の送信memory／送信memory予算 |
| `rtt`、`mss`、`cwnd` | RTT、TCP dataサイズ、輻輳window情報。`cwnd`の単位は通常segment |

socket memoryには管理情報も含まれるため、stream queueの列と一致するとは限りません。listener backlogは未完了のSYN queueとも別です。各fieldは[`ss(8)`マニュアル](https://man7.org/linux/man-pages/man8/ss.8.html)を参照してください。

値を変更せず、現在のbufferポリシーを読み取ります。

```bash
sysctl net.ipv4.tcp_rmem net.ipv4.tcp_wmem net.ipv4.tcp_moderate_rcvbuf
```

`tcp_*mem`の3値は最小／既定／自動調整上限を表し、各socketの現在使用量ではありません。受信autotuningやアプリケーションが指定するsocket optionも結果に影響します。予算値は広告するreceive windowや`cwnd`ではありません。

受信queueが増え続ける場合はreaderの処理進捗を調べます。送信queueが継続するなら、アプリケーション、acknowledgement、経路の証拠を調べてください。1回の観察やbuffer拡大だけではスループット改善を証明できません。

この6 byte負荷は通常動作を観察するものであり、backpressureを意図的に起こしたり最大スループットを測定したりはしません。調整を提案する前に、[socketとbufferの考え方](../kernel/02-network-stack.md#tcp-buffer-policy)を読んでください。

**クリーンアップ:** クライアントは30回の反復後、または中断時の`finally`で接続を閉じます。端末Aのサーバーを停止するか、timer切れを待ちます。sysctl変更を戻す必要はありません。

## ラボ3: ルーティングとICMPを追う {#routing-icmp-lab}

**目的:** 選択された次ホップを証明し、名前解決と転送を区別し、TTL制限プローブとICMP応答を照合します。

Routing helperは次の一時トポロジーを作成します。

```text
client namespace          router namespace                 server namespace
192.0.2.2/29 --- left --- 192.0.2.3/29
                          198.51.100.2/29 --- right --- 198.51.100.3/29
left bridge: 192.0.2.0/29             right bridge: 198.51.100.0/29
```

専用bridgeはどちらも`com.docker.network.bridge.enable_ip_masquerade=false`を設定します。helperは明示的なラボ経路を追加する前に、3つのコンテナ内にある**すべてのIPv4 default routeを削除**し、connected routeは残します。

コンテナから全capabilityを取り除いた後、`NET_ADMIN`と`NET_RAW`だけを追加します。router namespace内ではforwardingを有効にします。helperはprivileged containerもhost networkingも使わず、portを公開せず、AWSリソースも作成しません。

Dockerはホストbridgeを作り、通常のnetwork ruleを管理します。helperはホストroute、sysctl、iptables ruleを手動変更しません。ただし、ホストに影響がない、またはair gapができるという意味ではありません。

クライアントには`192.0.2.3`経由で`198.51.100.0/29`への経路を追加し、サーバーには`198.51.100.2`経由で`192.0.2.0/29`への戻り経路を追加します。

存在しない出力パスを選びます。

```bash
python3 examples/networking/foundations/routing_lab.py \
  --output ./routing-observation-01.json
```

helperは既存ファイルの上書きを拒否します。この**1回の実行で、後述のMTU演習も実行します**。その節のために2回目の並行実行を開始しないでください。

以下はhelperが**client namespace内で実行する**コマンドです。ホストシェルの手順ではなく、意味を理解するための表示です。

```text
ip -j route get 198.51.100.3
ip -j neigh show to 192.0.2.3
ip -j neigh show to 198.51.100.3
ping -n -c 1 -W 1 -t 1 198.51.100.3
traceroute -n -I -m 4 -q 1 -w 1 198.51.100.3
```

また、生成したrouterコンテナ名をDocker DNSで解決します。target名は実行prefixで変わります。DNS応答だけでは到達性を証明できません。

| JSONの観察値 | 期待する基準 | 解釈 |
|---|---|---|
| `defaultRoutes` | client、router、serverのリストがすべて空 | 3コンテナにIPv4 default routeが残っていない |
| `route` | gateway `192.0.2.3`、source `192.0.2.2` | 宛先にはrouter経由で到達する |
| `dns` | 左ネットワーク上でrouter名が`192.0.2.3`に解決される | Dockerの名前解決が動作している |
| `nextHopNeighbor` | `192.0.2.3`のMACアドレス | ARPで次ホップが解決された |
| `remoteNeighbor` | 空 | リモートserverはclientと同一Ethernet上のneighborではない |
| `ttlOne` | probeは失敗し、captureにICMP Time Exceededがある | 意図どおりrouterでTTLが尽きた |
| `traceroute` | 第1 hopが`192.0.2.3`、宛先が`198.51.100.3` | ICMP probeによるtraceがIP hopを2つ通る |

`ttlOne`では、helperがrouter namespace内で`icmp[0] == 11`のfilterを使って実際の`tcpdump`を起動し、capture開始を待ってからTTL-1 pingを送ります。想定される応答は、元のprobeを引用するIPv4 ICMP Type 11 Code 0です。

ここでpingが失敗することは、captureで一致する応答が確認されれば診断刺激の成功です。Probe自体はICMP Echoで、Time Exceededは別の戻りメッセージです。

Tracerouteの`-I`はICMP Echo probeを使います。UDP／TCP方式では異なるfilterに遭遇し、宛先から異なる応答が返る場合があります。`*`は待機中に対応する応答がなかったことを記録するだけで、end-to-end lossを単独で証明しません。RTTには応答の戻り経路も含まれます。

helper終了後に証拠ファイルを調べます。

```bash
python3 - <<'PY'
import json
from pathlib import Path

record = json.loads(Path("routing-observation-01.json").read_text())
print("Status:", record["status"])
print("Checks:", record.get("checks", {}))
print("Cleanup:", record.get("cleanup", "not reported"))
PY
```

**成功基準:** helperが正常終了して`status: passed`を記録し、名前付きの8項目がすべてtrueで、cleanupも報告されていること。経路とDNSの成功で、パケット観察の失敗を補うことはできません。

**クリーンアップ:** 正常終了、観察失敗、処理可能な中断では、helperは作成したcontainerとnetworkのIDを削除しようとします。cleanupエラーは実行失敗です。突然終了するとcleanupできないことがあるため、記録済みIDで残存物を特定してください。共有Dockerリソースに対する広範なpruneはしないでください。次節の解釈にも使うのでJSONを保持します。

### 記録済み参照実行 {#routing-reference-run}

[examples検証記録](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/networking/foundations/README.md#validation)にリンクされた2026年9月14日の実行はLinux Docker Engine 25.0.16上でPASSし、8項目すべてを確認しました。3コンテナのdefault routeリストはすべて空で、作成IDは削除されました。tracerouteでは`192.0.2.3`の次に`198.51.100.3`が観測されました。

時刻とinterface prefixを省略した、実測TTL-error packetの詳細:

```text
IP 192.0.2.3 > 192.0.2.2: ICMP time exceeded in-transit, length 92
```

これはその環境における機能的な証拠です。別ホストで同一のタイミング、interface名、MACアドレス、互換性になる保証はありません。

## ラボ4: MTU、PMTU、MSSを区別する {#mtu-mss-lab}

**目的:** ICMPエラーの実測を使ってサイズ依存の失敗を説明し、ICMP payloadサイズをTCP MSSと取り違えないようにします。

同じrouting invocationとJSON記録を使います。helperはroute lookupでserver方向のrouter interfaceを見つけ、**そのコンテナinterfaceのMTUを1280に設定**します。egress interface名が`eth1`だとは仮定しません。

最初のclient probeではrouterで`icmp[0] == 3 and icmp[1] == 4`をcaptureしてから、小さい方のprobeを送信します。

```text
ping -n -c 1 -W 1 -M do -s 1372 198.51.100.3
ping -n -c 1 -W 1 -M do -s 1200 198.51.100.3
```

`-M do`はIPv4のDon't Fragment動作を要求します。ここで使う標準20-byte IPv4 headerと8-byte ICMP headerの場合:

| Probe | IP packetサイズ | 期待する基準 |
|---|---|---|
| ICMPデータ1372 byte | `1372 + 8 + 20 = 1400` byte | MTU 1280のegressには大きすぎる。captureされたICMP Type 3 Code 4を伴って失敗する |
| ICMPデータ1200 byte | `1200 + 8 + 20 = 1228` byte | そのegressに収まる。Echo Replyが成功する |

`pmtu.probeOutput`、`pmtu.capture`、`smallerPacket`、`routeAfterFeedback`を確認します。重要な証拠は、特定のRTTや出力文言ではなく、**Fragmentation Needed応答と小さいpacketの成功**です。

同じ記録済み実行で観測されたping行:

```text
From 192.0.2.3 icmp_seq=1 Frag needed and DF set (mtu = 1280)
```

1200-byte data probeは応答を受信し、`routeAfterFeedback`はMTU 1280を報告しました。これらはその実行の観察結果であり、固定された時間やcache有効期限の保証ではありません。

応答後、Linuxは宛先のPMTUをcacheする場合があります。その後に大きすぎるpacketを送ると、再びrouterに到達する前にローカルで「message too long」として失敗する場合があります。`routeAfterFeedback`に学習したMTU情報が表示されることがありますが、fieldと期限切れ動作は異なります。

helperのcaptureは、一時client namespaceで意図的に起こした最初の失敗に対応します。後からICMPメッセージが見えないことだけでは、先行する応答の証拠は否定されません。

**MSSは別の値です**。TCP data byteの上限です。Ethernet MTU 1500、基本IPv4／TCP headerの場合、基本MSSは`1500 − 20 − 20 = 1460`です。IP／TCP optionと経路条件で、1 packetあたりの実際のdataは小さくなることがあります。

上記の1372と1200はICMP dataサイズであり、**実測MSSではありません**。loopbackは独自のMTUとkernel動作を持つため、loopback TCP演習でMSS 1460が必ず表示されるわけでもありません。

TSO／GSO／GROやchecksum offloadによって、ホストcaptureが物理リンク上のpacketと異なる場合があります。大きなcapture単位や見かけ上のchecksum errorをwire障害と判断する前に、interface、namespace、観察地点を確認してください。

IPv6 routerは転送packetをfragmentせず、ICMPv6 Packet Too Bigを使います。古典的PMTUDとpacketization-layer probingでは応答への依存が異なります。[ICMPの基礎](../basics/06-network-fundamentals-part1.md#icmp-traceroute-interpretation)を参照してください。

**クリーンアップ:** routing helperは、作成した他のIDと一緒に一時routerを削除し、MTU変更も取り除きます。ホストの物理interface MTUは変更しません。解析後は、自分の証拠ファイルだけを保持または削除してください。

## Dockerのパケット経路を説明する {#docker-packet-path}

**目的:** 観察結果をLinux namespace、仮想Ethernet link、route lookupに結び付けます。

既存のrouting記録を使います。追加containerは不要です。`route`、neighborの観察結果、ICMP capture、記録されたコマンドを比較します。

1. Client namespaceは`192.0.2.3`経由で`198.51.100.0/29`を選択します。明示的経路が次ホップを決めます。
2. ClientはARPでrouter左側のMACを解決します。IP宛先は`198.51.100.3`のままです。
3. veth pairと左bridgeがEthernet frameをrouterへ運びます。L2 bridgingではIP TTL hopを消費しません。
4. Router namespaceがIPv4 forwardingを行い、TTLを減らし、server経路をlookupしてegress MTUを確認します。
5. 右側networkではrouterがserverのMACを解決し、新しいEthernet frameを送ります。意図したrouting経路では送信元／宛先IPは変換されません。
6. Serverの明示的な戻り経路は`198.51.100.2`を使います。要求が届いても、返信経路が動作する必要があります。

**期待する基準:** 記録を見て、それぞれのlookupのnamespace、IP宛先、ローカルARP対象、返信経路を特定できること。別の実行におけるinterface名やMAC値を推測してはいけません。

Docker DNSによる名前解決とLinux packet forwardingは別の観察結果です。DNS応答が正しくても、経路、forwarding policy、戻り経路が壊れている場合があります。

各network namespaceに独自のloopback deviceがあります。コンテナ内の`127.0.0.1`はホストのHTTP helperに届きません。この演習ではhost-network modeを使って挙動を変えません。

ここではmasqueradingを無効にし、3コンテナにIPv4 default routeを設けず、routerを明示した**専用user-defined bridgeを2つ**使います。これは意図したラボ経路を定義するもので、一般的なセキュリティ分離の保証ではありません。既定のDocker Internet NAT、公開port転送、Internet throughputは測定しません。

**クリーンアップ:** 完了済みの記録を再利用します。routing helperはリソースcleanupをすでに試みています。失敗／不完全な記録は該当段階を調べる理由であり、共有firewall制御を無効にする理由ではありません。

[コンテナ技術](../basics/03-container-technology.md)、次に[Core Services and Networking Lab](../labs/core/03-services-networking-lab.md)へ進みます。Kubernetes CNI、Service変換、AWS VPC routingにはそれぞれ独自のルールがあります。Dockerトポロジーをそのままコピーせず、適切な層で調べてください。

## 参考資料とレビュー {#references}

- [HTTP semantics: RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)、[HTTP/1.1 framing: RFC 9112](https://www.rfc-editor.org/rfc/rfc9112.html)
- [curlマニュアル](https://curl.se/docs/manpage.html): HTTP version、HEAD、binary request data、trace
- [`ss(8)`](https://man7.org/linux/man-pages/man8/ss.8.html)、[`socket(7)`](https://man7.org/linux/man-pages/man7/socket.7.html)、[Linux TCP buffer policy](https://docs.kernel.org/networking/ip-sysctl.html)
- [ip-route(8)](https://man7.org/linux/man-pages/man8/ip-route.8.html)、[ip-neighbour(8)](https://man7.org/linux/man-pages/man8/ip-neighbour.8.html)、[network_namespaces(7)](https://man7.org/linux/man-pages/man7/network_namespaces.7.html)
- [iputils pingマニュアル](https://github.com/iputils/iputils/blob/master/doc/ping.xml)、[traceroute(8)](https://man7.org/linux/man-pages/man8/traceroute.8.html)
- [ICMP: RFC 792](https://www.rfc-editor.org/rfc/rfc792.html)、[IPv4 routerの動作: RFC 1812](https://www.rfc-editor.org/rfc/rfc1812.html)、[MSS: RFC 6691](https://www.rfc-editor.org/rfc/rfc6691.html)
- [Docker bridge networkingとdriver option](https://docs.docker.com/engine/network/drivers/bridge/)

[理解度クイズ](../quizzes/networking/07-linux-network-diagnostics-quiz.md)
