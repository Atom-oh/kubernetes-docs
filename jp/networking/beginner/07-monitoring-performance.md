# 7. ネットワーク監視と性能の第一歩

> **学習ベースライン**: Ubuntu Server 24.04 LTS。Rocky Linux 9 の代替手順あり
>
> **最終更新日**: 2026 年 9 月 15 日

**前提条件:** [レッスン 1～6](README.md#course-map)を完了してください。2 台の VM はラボ NIC 経由で通信し、サーバーの TCP 8000 はラボクライアントからの接続だけを許可します。別のラボサーバーがポート 8000 を使用している場合は、所有者を特定し、その演習の手順に従って停止してください。

**学習目標:** リスナー、接続、キュー、パケット、トラフィック量を区別し、「遅い」という状態を検証可能な問いに変えます。練習を含めて約 2～3 時間を見込んでください。

## ツールと観測点 {#observation-tools}

| 確認したいこと | ツール | これだけでは確認できないこと |
|---|---|---|
| プログラムがどのアドレス／ポートでリッスンしているか | `ss -ltnp` | 外部クライアントから到達できるか |
| 接続の状態とキュー | `ss -tinm` | 1 回のスナップショットから損失の原因を特定すること |
| この NIC を通過したパケット | `tcpdump` | キャプチャ対象外の他の NIC や namespace の動作 |
| 帯域幅を使うホストの組み合わせ | `iftop` | アプリケーション処理時間や正確な課金対象トラフィック |
| HTTP リクエストにかかる時間 | `curl -w` | サーバー内の個々の関数の処理時間 |

古い資料では `netstat` が使われていることがあります。このコースではソケットの観測に `ss` を使います。`netstat -lnt` と `ss -ltn` は似た問いに答えますが、形式やフィールドは同一ではありません。`netstat` がない場合も、新しいツールを削除したりシステムを再構成したりする必要はありません。

サーバーで必要なパッケージを確認してください。Ubuntu の場合:

```bash
sudo apt update
sudo apt install iproute2 tcpdump python3
```

Rocky の場合:

```bash
sudo dnf install iproute tcpdump python3
```

クライアントには `curl` が必要です。[レッスン 1](01-linux-cli.md)のパッケージマネージャーの手順に従ってインストールしてください。

## 小規模な HTTP ワークロードを生成する {#small-http-workload}

**サーバーのコンソール A:** 空の一時ディレクトリに演習用ファイルを 1 つ作成します。

```bash
LAB_WEB=$(mktemp -d /tmp/net-web.XXXXXX)
printf 'network lesson\n' > "$LAB_WEB/index.html"
timeout 300 python3 -m http.server 8000 \
  --bind 192.0.2.20 --directory "$LAB_WEB"
```

このサーバーは選択したディレクトリを公開し、5 分後に停止します。終了ステータス 124 は `timeout` が制限時間に達したことを示します。これは TLS とユーザー認証を備えた本番用 Web サーバーではありません。演習ディレクトリに他のファイルやシンボリックリンクを置かないでください。

**クライアント:** リクエストを 1 回送信し、続けて 1 秒間隔でさらに 10 回送信します。

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/
for n in $(seq 1 10); do
  curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
    -sS -o /dev/null http://192.0.2.20:8000/
  sleep 1
done
```

**合格条件:** 最初の応答は HTTP 200 で、本文に `network lesson` が含まれます。後続のリクエストはエラーなく完了し、サーバーログに表示されます。失敗した場合は負荷を上げず、[レッスン 4 の診断手順](04-dns-connectivity.md)に戻ってください。

## ソケットの状態とキューを読む {#socket-observation}

**サーバーのコンソール B:** 別のターミナルを使います。

```bash
sudo ss -ltnp 'sport = :8000'
ss -tinm '( sport = :8000 or dport = :8000 )'
```

最初のコマンドで `192.0.2.20:8000` のリスナーを探してください。リクエストの実行中に 2 つ目の観測を繰り返します。短時間の接続はスナップショットの間に完了することがあります。`ESTABLISHED` の行がないことだけでは、リクエストの失敗は証明されません。サーバーログやパケットキャプチャと照合してください。

| 状態またはフィールド | 解釈 |
|---|---|
| LISTEN `Recv-Q` / `Send-Q` | accept を待っている接続数／accept backlog の最大数 |
| ESTABLISHED `Recv-Q` | アプリケーションがまだ読み取っていない順序どおりのバイト数 |
| ESTABLISHED `Send-Q` | まだ送信されていないデータを含む、未確認のストリームバイト数 |
| `rtt` | TCP の往復時間の推定値。HTTP 全体の所要時間ではない |
| `cwnd` | 送信側の輻輳ウィンドウ。`ss` では通常セグメント単位で表示 |
| `skmem` | オーバーヘッドを含むソケットメモリの計上値。キューにあるペイロードのバイト数だけではない |

これほど小さなリクエストでは、キューが 0 でも正常です。大きなキューを作ることは成功条件ではありません。[Linux TCP キュー演習](../07-linux-network-diagnostics.md#tcp-buffer-lab)では、より長く維持される接続を使って詳しく考察します。

## 選択した NIC でパケットをキャプチャする {#packet-capture}

**サーバーのコンソール B:** ハイパーバイザーに記録した MAC アドレスを使って、ラボ NIC を特定します。

```bash
ip -br link
```

以下のコマンドでは、確認済みのインターフェイス名に置き換えてください。`enp0s8` は例であり、管理用 NIC を選ぶ指示ではありません。

```bash
LAB_IF=enp0s8
ip -br address show dev "$LAB_IF"
sudo timeout 15 tcpdump -ni "$LAB_IF" -c 20 \
  'host 192.0.2.10 and tcp port 8000'
```

キャプチャを開始し、**クライアントから curl リクエストを再実行**します。`-n` は名前解決を避け、`-i` はインターフェイスを指定し、`-c 20` はキャプチャするパケット数を制限します。15 秒の時間制限が先に到達する場合があります。

TCP フラグの例には、SYN の `[S]`、SYN+ACK の `[S.]`、ACK の `[.]`、FIN+ACK の `[F.]` があります。データと確認応答はさまざまな組み合わせで送信されます。「HTTP リクエスト 1 回は必ず 3 パケット」のような固定ルールを暗記しないでください。

証拠を保存する場合は、自分の演習トラフィックだけを短時間キャプチャします。

```bash
LAB_CAPTURE=$(mktemp -d /tmp/net-capture.XXXXXX)
sudo timeout 15 tcpdump -Z "$(id -un)" -ni "$LAB_IF" -c 20 \
  -w "$LAB_CAPTURE/http.pcap" 'host 192.0.2.10 and tcp port 8000'
sudo tcpdump -nn -r "$LAB_CAPTURE/http.pcap"
```

書き込みコマンドの実行中に、クライアントからリクエストを再送します。`-Z "$(id -un)"` はキャプチャデバイスを開いた後で現在の一般ユーザーに権限を下げ、ユーザー自身の一時ディレクトリにファイルを書き込めるようにします。PCAP にはアドレスや実データが含まれる可能性があります。SSH 認証情報や実ユーザーのトラフィックではなく、演習用の文字列だけを使ってください。読み込みコマンドでは、ファイル権限の違いに対応するため `sudo` を使います。

**解釈:** リクエストと応答のアドレス／ポートを特定します。キャプチャが空なら、まず NIC、フィルター、時間範囲を確認してください。NIC オフロードによって、ホストで観測されるパケットサイズやチェックサムは回線上のものと異なる場合があります。1 つのキャプチャにチェックサム警告があるだけでは、ネットワーク障害は証明されません。

## 帯域幅とリクエストの時間 {#bandwidth-and-time}

`iftop` は任意です。Ubuntu では `sudo apt install iftop` でインストールできます。Rocky の設定済みリポジトリにない場合は、この演習を省略するか、先に[レッスン 6 の EPEL 前提条件](06-firewalls-host-security.md)を確認してください。`sudo dnf install iftop` が失敗しても、出所不明のインストールスクリプトを実行しないでください。

**サーバー:** 確認済みの `LAB_IF` を設定したターミナルで実行します。

```bash
sudo iftop -nNP -i "$LAB_IF" -f 'host 192.0.2.10'
```

クライアントのリクエストを繰り返し、方向ごとのレートを読み取ってから `q` を押して終了します。短く小さいリクエストでは、値がほぼゼロに見える場合があります。これはリンク容量やインターネットのスループットのテストではありません。

**クライアント:** HTTP の所要時間を別に観測します。

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -sS -o /dev/null \
  -w 'dns=%{time_namelookup} connect=%{time_connect} first_byte=%{time_starttransfer} total=%{time_total}\n' \
  http://192.0.2.20:8000/
```

値は開始時点からの経過秒数です。このリクエストは IP アドレスを直接指定しているため、DNS の性能は測定しません。最初のバイトまでの時間にはそれ以前の処理とサーバーの準備時間が含まれます。各フィールドが互いに独立した区間であるかのように足し合わせないでください。

| 測定項目 | 意味 | 制御すべき条件 |
|---|---|---|
| レイテンシー | 操作または往復にかかる時間 | リクエストサイズ、経路、サーバー負荷 |
| スループット | 単位時間あたりに転送された量 | 並行性、方向、バイトとビットの別、継続時間 |
| 損失／再送 | 観測されたパケット欠落または TCP の回復 | キャプチャ位置／ドロップ、経路変更、時間範囲 |
| リソース使用量 | CPU、メモリ、I/O の活動または待機 | プロセス、VM の割り当て、他のワークロード |

`1 byte = 8 bits` です。`100 Mbit/s` を `100 MB/s` と同一視しないでください。測定を繰り返す場合は、条件と最小値／中央値／最大値、または別の適切な分布を記録します。

## 次に学ぶカーネルと I/O {#kernel-next}

以下のコマンドは**観測のみ**を行います。

```bash
uname -r
sysctl net.ipv4.tcp_congestion_control
sysctl net.ipv4.tcp_rmem net.ipv4.tcp_wmem
lsblk -o NAME,TYPE,SIZE
```

`sysctl` が返すバッファーポリシーの値は、各ソケットの現在の使用量ではありません。値を増やす前に、[ソケットバッファー、ウィンドウ、BDP](../../kernel/02-network-stack.md#tcp-buffer-policy)を区別してください。`lsblk` でディスクを特定した後、`/sys/block/DEVICE/queue/scheduler` を読むと、サポート対象／選択中のブロック I/O スケジューラーを確認できます。仮想デバイスによって選択肢が同じとは限りません。

ブロック I/O スケジューラーはストレージリクエストを処理し、ネットワーク qdisc はネットワーク送信キューを扱います。どちらも「scheduler」と呼ばれますが、置き換えて調整できるものではありません。このレッスンでは sysctl、MTU、qdisc、I/O スケジューラーを変更しません。高度な作業を行う場合は、変更変数を 1 つに絞った別の実験を設計し、測定とロールバックを用意してください。

## クリーンアップと完了条件 {#completion}

コンソール A で Ctrl+C を押してサーバーを停止するか、時間制限に達するまで待ちます。**同じターミナルで**、自分の演習用ファイルとディレクトリだけを削除します。

```bash
rm -- "${LAB_WEB:?}/index.html"
rmdir -- "${LAB_WEB:?}"
```

キャプチャ用ターミナルで、キャプチャファイルも削除します。

```bash
sudo rm -- "${LAB_CAPTURE:?}/http.pcap"
rmdir -- "${LAB_CAPTURE:?}"
```

`${VARIABLE:?}` は変数が未設定または空の場合、コマンドを停止します。ディレクトリが空でなければ、範囲の広い再帰削除を使わず、中身を調べてください。

- リスナー、TCP 接続、HTTP の成功が、それぞれ異なる証拠である理由を説明する。
- PCAP から双方向のアドレス／ポートを特定し、キャプチャ位置を記録する。
- キュー／帯域幅の単位と、IP アドレスを直接指定したリクエストでは DNS を測定できないことを説明する。
- 観測と、別の管理された実験が必要なチューニングを区別する。

## 参考資料と次のレッスン

- [iproute2 ss マニュアル](https://man7.org/linux/man-pages/man8/ss.8.html)
- [tcpdump マニュアル](https://www.tcpdump.org/manpages/tcpdump.1.html)
- [iftop 作者のマニュアル](https://www.ex-parrot.com/pdw/iftop/iftop.8.html)
- [curl マニュアル](https://curl.se/docs/manpage.html)
- [Python 3.12 http.server](https://docs.python.org/3.12/library/http.server.html)
- [Linux block multi-queue](https://docs.kernel.org/block/blk-mq.html)

[前へ: ファイアウォールとホストセキュリティ](06-firewalls-host-security.md) · [クイズ](../../quizzes/networking/beginner/07-monitoring-performance-quiz.md) · [次へ: 総合演習](08-container-cloud-capstone.md)
