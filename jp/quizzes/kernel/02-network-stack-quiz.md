# カーネルネットワークスタックのクイズ

このクイズでは、socket／VFS の入口、TCP buffer と window、状態に応じて異なる queue の観測方法、hook の位置、Pod 間 routing の理解を確認します。

## 選択問題

1. NIC に送られる前の outgoing packet を queue し、`tc -s qdisc` で drop を確認できるのはどのコンポーネントですか。
   - A) NIC の物理層
   - B) qdisc: node 内での drop は `tc -s qdisc` の `dropped` に表示される
   - C) VPC network
   - D) アプリケーションの socket buffer

<details>

<summary>解答を表示</summary>

**正解: B) qdisc: node 内での drop は `tc -s qdisc` の `dropped` に表示される**

**解説:**
qdisc は outgoing packet を queue／schedule し、queue 上限や active queue management によって drop することがあります。`dropped` counter の増加は、その qdisc での drop を示しますが、経路上のあらゆる loss を示すわけではありません。影響を受けた時間帯と traffic を、interface、driver、stack、remote 側の証拠と照合してください。`overlimits` は drop を伴わない shaping を示すこともあり、`dropped` と同じ意味ではありません。
</details>

2. packet を早期に drop する性能について話すとき、XDP のどの mode の違いが重要ですか。
   - A) kernel module ではなく hardware 上で動作する
   - B) Native／driver XDP は skb allocation の前に動作し、generic XDP はすでに skb を使う
   - C) JIT compile される
   - D) conntrack を参照する必要がない

<details>

<summary>解答を表示</summary>

**正解: B) Native／driver XDP は skb allocation の前に動作し、generic XDP はすでに skb を使う**

**解説:**
早期 drop の利点は mode によって異なります。BPF map は状態を保持できます。性能は kernel、program、driver、hardware に依存するため、あらゆる環境で最速になるという保証はありません。
</details>

3. 受信 traffic が多い状況で、CPU 1つだけが100%になり、ほかの CPU は idle です。考えられる原因と関連する仕組みとして、何を調べるべきですか。
   - A) qdisc queue が不足しているため、queue 長を増やす
   - B) 受信処理が偏っているため、RSS queue／IRQ の分配、RPS による software steering、RFS の cache locality を調べる
   - C) socket buffer が不足しているため、`tcp_rmem` を増やす
   - D) TCP congestion control の不一致なので、bbr に切り替える

<details>

<summary>解答を表示</summary>

**正解: B) 受信処理が偏っているため、RSS queue／IRQ の分配、RPS による software steering、RFS の cache locality を調べる**

**解説:**
RSS は flow を受信 queue に hash します。IRQ affinity はどの CPU が処理するかに影響します。RPS は後続の受信処理を software で振り分け、RFS は処理を application の実行場所に近づけようとします。これらがすべて hardware interrupt を移動させるわけではなく、単一 flow が1つの queue にとどまる場合もあります。原因を決める前に `/proc/interrupts`、`mpstat -P ALL` の CPU ごとの `%soft`、application の CPU 使用率を確認してください。
</details>

4. 通常の interrupt-driven NAPI は、どのように packet ごとの処理 overhead を減らしますか。
   - A) kernel が CPU frequency を自動的に上げる
   - B) driver が対象 queue の interrupt を mask し、上限付き polling を schedule して、batch ごとに処理することで作業をまとめる
   - C) 処理前に packet を圧縮する
   - D) GRO を自動的に有効化する

<details>

<summary>解答を表示</summary>

**正解: B) driver が対象 queue の interrupt を mask し、上限付き polling を schedule して、batch ごとに処理することで作業をまとめる**

**解説:**
Batch 処理で interrupt と処理の overhead を分散できます。Polling が schedule される間、driver は対象 interrupt を mask し、polling が終わったときに解除できます。すべての CPU interrupt を無効にするわけではありません。Polling には work budget があり、過負荷では遅延や drop が増える場合があります。Busy polling と threaded NAPI は別の実行方式です。
</details>

5. CPU がボトルネックなのに、同一 node 内の Pod 間 traffic が単一 flow で29.97 Gbpsに達したのはなぜですか。
   - A) node 内に専用の高速 network がある
   - B) 図示した一般的な veth／routed の同一 node 経路では、物理 NIC を通らず kernel memory 内に packet がとどまる場合がある
   - C) kernel が packet を圧縮する
   - D) 同一 node の traffic では TCP を使わない

<details>

<summary>解答を表示</summary>

**正解: B) 図示した一般的な veth／routed の同一 node 経路では、物理 NIC を通らず kernel memory 内に packet がとどまる場合がある**

**解説:**
Virtual device にも driver 処理はあります。CNI、SR-IOV、overlay、service／policy による迂回経路が異なれば通信経路も変わるため、実際の構成に照らして判断してください。
</details>

6. 小さな handshake packet は通過しますが、DF が設定された大きな IPv4 packet が低 MTU の hop で drop され、戻りの ICMP も遮断されています。どの仕組みで通信が停止しますか。
   - A) conntrack の枯渇
   - B) PMTUD の失敗。path MTU を通知する ICMP が遮断されるため、大きな packet だけが drop される
   - C) TCP congestion control の不一致
   - D) socket receive buffer の不足

<details>

<summary>解答を表示</summary>

**正解: B) PMTUD の失敗。path MTU を通知する ICMP が遮断されるため、大きな packet だけが drop される**

**解説:**
DF が設定されていると、IPv4 router は大きすぎる packet を fragment 化できず、通常は ICMP の「fragmentation needed」を返します。この通知が遮断されると PMTUD が壊れ、black hole が生じることがあります。IPv6 router は fragment 化せず、ICMPv6 の「Packet Too Big」を使います。設問に示された証拠がなければ、handshake の後に通信が停止することは手掛かりに過ぎず、証明ではありません。probe によって回復する場合もあります。
</details>

7. Network 障害を診断するとき、推奨される順序はどれですか。
   - A) 上から下へ、application から NIC まで順に調べる
   - B) drop counter から始める: `conntrack -S` の `insert_failed`、`tc -s qdisc` の `dropped`、`ethtool -S` の NIC drop
   - C) 必ず最初に `tcpdump` で packet capture する
   - D) CPU 使用率から始める

<details>

<summary>解答を表示</summary>

**正解: B) drop counter から始める: `conntrack -S` の `insert_failed`、`tc -s qdisc` の `dropped`、`ethtool -S` の NIC drop**

**解説:**
これらの counter は調査候補を示しますが、診断を完了させるものではありません。変化を対象 flow と時間帯に関連付けてください。conntrack では `insert_failed` が枯渇だけを意味するわけではないため、count／max と kernel log も確認します。集約 counter には無関係な traffic が含まれることがあります。ローカル counter に変化がなくても、remote 側の drop、認証、application の失敗は除外できません。症状に応じて、`ss -tin` の RTT／cwnd、返された error、経路上のほかの証拠も確認してください。
</details>

8. workload の benchmark がなくても正しい、`cubic` と `bbr` の比較はどれですか。
   - A) cubic は UDP 用、bbr は TCP 用
   - B) cubic は loss／ECN などの event に応じて congestion window を調整し、bbr は delivery rate と RTT の推定値を使う。結果は実装と経路に左右される
   - C) bbr は常に cubic より高速
   - D) kernel 6.x で cubic は削除された

<details>

<summary>解答を表示</summary>

**正解: B) cubic は loss／ECN などの event に応じて congestion window を調整し、bbr は delivery rate と RTT の推定値を使う。結果は実装と経路に左右される**

**解説:**
これらの model は制御動作の違いを説明するもので、性能順位を保証しません。BBR にも loss／recovery の挙動があり、どちらの algorithm も receive-window や application の制限をなくすものではありません。比較を解釈する前に、kernel 実装、有効な algorithm、RTT／cwnd、workload、経路を特定してください。
</details>

9. Process が TCP socket に対して `write(fd, ...)` と `send(fd, ...)` の両方を使います。Linux の socket／VFS bridge を正しく説明しているのはどれですか。
   - A) どちらの呼び出しも TCP に入る前に disk filesystem を通る必要がある
   - B) `send()` は常に `vfs_write()` を呼び、socket は disk file である
   - C) FD は socket に関連付けられた `struct file` を参照する。`write()` は VFS の socket file operation を使い、`send()` は socket 専用の入口経路を使う
   - D) Socket に file descriptor table の entry はない

<details>

<summary>解答を表示</summary>

**正解: C) FD は socket に関連付けられた `struct file` を参照する。`write()` は VFS の socket file operation を使い、`send()` は socket 専用の入口経路を使う**

**解説:**
version が固定された Linux の例では、`file->private_data` が `struct socket` に結び付いています。VFS の `write()` は `socket_file_ops.write_iter` から `sock_write_iter` に dispatch します。`send()` は独自の syscall 経路で FD から socket を取得します。どちらも socket／protocol operation に到達します。File abstraction を共有していても disk I/O を意味するわけではなく、送信が成功しても peer application が受信したとは限りません。[VFS bridge](../../kernel/02-network-stack.md#socket-vfs-bridge)を参照してください。
</details>

10. 確立済み TCP 接続に未読 payload があり、`ss -m` の receive memory が `Recv-Q` より大きい場合、正しい説明はどれですか。
   - A) Memory accounting には allocation overhead と、順序が前後した data が含まれる場合がある。`Recv-Q` は未読の in-order stream byte 数を表す
   - B) 各 `sk_buff` が socket receive buffer 全体である
   - C) Receive memory、`Recv-Q`、`rwnd`、`cwnd` は常に同じ値である
   - D) 各 skb が必ず wire 上の packet 1つに対応する

<details>

<summary>解答を表示</summary>

**正解: A) Memory accounting には allocation overhead と、順序が前後した data が含まれる場合がある。`Recv-Q` は未読の in-order stream byte 数を表す**

**解説:**
skb は packet data と metadata を表します。fragment を参照したり、clone されたり、結合／分割された data を表したりすることがあります。Socket memory budget、application payload、receiver が通知する window、sender の congestion window は、それぞれ異なる上限や量を表します。`ss -m` の memory 値を `rwnd` の代わりに使うことはできず、ローカル buffer を増やしても `cwnd` が直接増えるわけではありません。[Queue の観測](../../kernel/02-network-stack.md#ss-tcp-queues)を参照してください。
</details>

11. 確立済みの TCP 接続で `ss` が `LISTEN` に `Recv-Q=3, Send-Q=128`、`ESTABLISHED` に `Recv-Q=4096, Send-Q=8192` と表示します。これらの値は何を意味しますか。
   - A) どちらの行も NIC ring 内の packet 数を数える
   - B) Listener は3 byte 受信し、128 byte 送信した
   - C) Listener には accept 待ちの SYN が3つあり、確立済み接続の8192 byte はすべて wire 上にあると分かる
   - D) Listener には accept 待ちの接続が3つあり、backlog の最大値は128。確立済み socket には未読の in-order byte が4096あり、書き込み済みで cumulative acknowledgement を受けていない byte が8192ある

<details>

<summary>解答を表示</summary>

**正解: D) Listener には accept 待ちの接続が3つあり、backlog の最大値は128。確立済み socket には未読の in-order byte が4096あり、書き込み済みで cumulative acknowledgement を受けていない byte が8192ある**

**解説:**
Listener では列が接続数を示し、SYN queue の使用量は示しません。確立済み TCP では stream byte 数を示します。`Send-Q` には未送信と送信済み／未 ack の byte の両方が含まれる場合があります。これらは socket memory budget ではなく、packet loss の証拠でもありません。[状態によって異なる TCP queue](../../kernel/02-network-stack.md#ss-tcp-queues)を参照してください。
</details>

12. Application が `SO_RCVBUF` と `SO_SNDBUF` を明示的に設定しました。その後、Operator が `tcp_rmem[2]` と `tcp_wmem[2]` だけを増やしました。何が起こると考えるのが正しいですか。
   - A) 既存 socket はすべて新しい最大値をただちに確保する
   - B) 明示された socket 設定は、それぞれの方向の通常の自動調整に対して lock されたままである
   - C) Linux は `tcp_rmem[2]` を2倍にし、その値を `rwnd` として直接広告する
   - D) Send-buffer policy を変更すると peer の receive window が直接広がる

<details>

<summary>解答を表示</summary>

**正解: B) 明示された socket 設定は、それぞれの方向の通常の自動調整に対して lock されたままである**

**解説:**
Socket option は `SOCK_RCVBUF_LOCK` と `SOCK_SNDBUF_LOCK` を設定します。これは policy flag であり、mutex ではありません。通常の option request は `net.core.rmem_max`／`wmem_max` の制約を受けます。Linux は通常、受け入れた request を bookkeeping のために2倍にし、その値を `getsockopt()` で返しますが、その memory がすべて確保済み、または payload として使用可能という意味ではありません。Sysctl による自動調整の上限と、明示的な option 上限は別の制御です。[TCP buffer policy](../../kernel/02-network-stack.md#tcp-buffer-policy)を確認してください。
</details>

13. 仮定上の経路は1 Gbit/s、RTT 40 ms です。どの BDP 計算と結論が妥当ですか。
   - A) 40 MB。すべての socket の send buffer をこの値に設定する
   - B) 5 byte。millisecond と bit/s をそのまま掛ければよい
   - C) 5,000,000 byte（約4.77 MiB）。この規模を byte 単位に換算した window、application の進行状況、memory overhead と比較する
   - D) 5 MB。したがって、すべての host で buffer がボトルネックだと証明される

<details>

<summary>解答を表示</summary>

**正解: C) 5,000,000 byte（約4.77 MiB）。この規模を byte 単位に換算した window、application の進行状況、memory overhead と比較する**

**解説:**
`1,000,000,000 bit/s × 0.040 s ÷ 8 bit/byte = 5,000,000 bytes` です。RTT を使い、理想的な定常状態での in-flight payload を概算しています。`ss` は通常 `cwnd` を segment 数で表示するため、byte 単位の値と比べるには MSS を使ってください。Receive-window の制限、pacing、loss、CPU、application の挙動は引き続き影響します。BDP は一律に適用する tuning 指示ではありません。[BDP の考え方](../../kernel/02-network-stack.md#tcp-bdp-reasoning)と[TCP buffer lab](../../networking/07-linux-network-diagnostics.md#tcp-buffer-lab)を参照してください。
</details>

14. Interface の IP MTU は1500です。Host 上の capture では、1500 byte を超える TCP unit と、不正に見える送信 checksum が記録されています。最初にどう判断すべきですか。
   - A) Capture 位置と offload を調べる。option がなければ IPv4 の TCP payload は1460 byte 以下だが、host の GSO／GRO unit と未計算 checksum は wire 上の packet と異なる場合がある
   - B) TCP MSS は IP header を含むため1500 byte である
   - C) Remote の IPv6 router が packet を fragment 化したに違いない
   - D) Capture により wire 上の破損が証明され、PMTUD が無効だと分かる

<details>

<summary>解答を表示</summary>

**正解: A) Capture 位置と offload を調べる。option がなければ IPv4 の TCP payload は1460 byte 以下だが、host の GSO／GRO unit と未計算 checksum は wire 上の packet と異なる場合がある**

**解説:**
MSS は IP／TCP header を除いた値で、PMTU は経路全体に依存します。option がなければ IPv4 は `1500 - 20 - 20 = 1460`、IPv6 は base header を除いて1440 byte です。Offload によって segmentation／checksum の計算が後回しになったり、受信 packet が結合されたりすることがあります。Host の capture だけでは wire 上の packet size や破損は証明できません。[MTU／MSS lab](../../networking/07-linux-network-diagnostics.md#mtu-mss-lab)へ進んでください。
</details>
