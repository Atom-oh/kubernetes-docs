# Pod Network Benchmark クイズ

1. `ping -c 200 -i 0.05` で測定した場合、平均 Pod-to-Pod RTT は同一 node → 同一 AZ 内の別 node → 別 AZ でどのように変化しましたか？
   - A) 0.040 ms → 0.544 ms → 0.339 ms — cross-AZ の方が same-AZ より高速だった
   - B) 3 つの経路はすべて約 0.3 ms のノイズ範囲内だった
   - C) 0.040 ms → 0.339 ms → 0.544 ms — node を離れると +0.30 ms、AZ を離れるとさらに +0.21 ms 増加する、段階的な増加
   - D) 0.040 ms → 0.339 ms → 5.4 ms — AZ 境界により RTT がミリ秒単位まで増加した
<details>
<summary>回答を表示</summary>

**回答: C) 0.040 ms → 0.339 ms → 0.544 ms — node を離れると +0.30 ms、AZ を離れるとさらに +0.21 ms 増加する、段階的な増加**

**解説:**
ping の平均値（50 ms 間隔で 200 プローブ、損失 0/200）は、同一 node で 0.040 ms、same-AZ で 0.339 ms、cross-AZ で 0.544 ms でした。same-AZ − 同一 node = +0.30 ms、cross-AZ − same-AZ = +0.21 ms、cross-AZ − 同一 node = +0.50 ms です。fortio HTTP（100 qps、4 接続、keepalive）の p50 も 0.259 → 0.461 → 0.704 ms（+0.20 / +0.24 ms）と同じ段階的な増加を示しました。また、HTTP p50 − ping 平均は経路ごとに約 0.22 / 0.12 / 0.16 ms であり、これは client+server の user-space stack によるものです。5.4 ms という値は、単一 flow を飽和させた iperf3 実行中の送信側 TCP RTT（shaper での queueing）であり、アイドル時の cross-AZ RTT ではありません（D は誤り）。規模の比較として、この repo の Istio 比較ページでは sidecar hop 1 回が p50 で +1.29 ms とされており、mesh hop は AZ hop よりもコストが大きくなります。

</details>

2. 単一の iperf3 TCP stream（`-P 1`）は same-AZ と cross-AZ の両経路で 4.96 Gbps にとどまり、8 streams（`-P 8`）では両方とも 9.94 Gbps に達しました。この 2 つの数値を最もよく説明するものは何ですか？
   - A) 4.96 Gbps は client CPU core 1 個の飽和であり、8 streams が高速なのはより多くの core を使用するため
   - B) 4.96 Gbps は EC2 が文書化している 5 Gbps の single-flow limit（cluster placement group 外）であり、9.94 Gbps は m5.xlarge の "Up to 10 Gigabit" instance peak — instance の帯域幅を使うには flow を並列化する必要がある
   - C) 4.96 Gbps は m5.xlarge の baseline bandwidth であり、8 streams は burst credits を使って peak に到達した
   - D) 単一 stream では Jumbo frames（MTU 9001）が有効になっていなかった
<details>
<summary>回答を表示</summary>

**回答: B) 4.96 Gbps は EC2 が文書化している 5 Gbps の single-flow limit（cluster placement group 外）であり、9.94 Gbps は m5.xlarge の "Up to 10 Gigabit" instance peak — instance の帯域幅を使うには flow を並列化する必要がある**

**解説:**
異なる node 上の Pod 間の単一 flow は両経路で同一でした。same-AZ（cli→srv-a）が 4.96 Gbps、cross-AZ（cli→srv-b）も 4.96 Gbps であり、これは AWS が文書化する 5 Gbps の single-flow limit です。iperf3 はこれらの実行中、client CPU が 19.5 % / 20.0 %（1 core に対して）にすぎないと報告しており、CPU は制限要因ではありませんでした（A は誤り）。CPU-bound となるのは、client が 99.8 % となった同一 node の単一 stream（29.97 Gbps）です。m5.xlarge の baseline は 1.25 Gbps、peak は 10 Gbps であり（C は誤り）、8-stream の 9.94 Gbps はこの peak です。MSS 8949（MTU 9001）はすべての実行に等しく適用されていました（D は誤り）。単一 flow が上限に固定されると、送信側の TCP RTT はアイドル時の ping RTT である 0.34 ms（same-AZ）/ 0.54 ms（cross-AZ）から、約 4.3 MB の congestion window で 5.6 ms / 5.4 ms まで増加しました。また、instance ceiling に達すると retransmits は 1 stream 時の 4 / 2 から 8 streams 時の 5,874 / 5,979 へ増加しました。これは ENA allowance shaping の間接的な兆候です（counter 自体は収集していません）。実際には、異なる node 上の Pod 間の gRPC stream 1 本または Kafka replica fetch 1 本は、約 5 Gbps を超えることはできません。

</details>

3. 8-stream iperf3 の帯域幅は same-AZ と cross-AZ のどちらも同じ 9.94 Gbps でしたが、fortio の closed-loop maximum（`-qps 0`、16 接続、20 s）は same-AZ の 38,507 qps から cross-AZ の 25,602 qps へ低下しました。なぜですか？
   - A) inter-AZ link は request/response traffic の帯域幅を半減させる
   - B) cross-AZ 経路で errors と retries が増加した
   - C) srv-b をホストする node は srv-a の node より CPU が遅かった
   - D) Little の法則 — 16 接続で固定の場合、throughput = concurrency ÷ latency なので、16 ÷ 0.000624 s ≈ 25,641 qps が上限となる。AZ hop によるおよそ +0.2 ms の latency が throughput を 34 % 削減した。cross-AZ で増えるのは帯域幅ではなく latency
<details>
<summary>回答を表示</summary>

**回答: D) Little の法則 — 16 接続で固定の場合、throughput = concurrency ÷ latency なので、16 ÷ 0.000624 s ≈ 25,641 qps が上限となる。AZ hop によるおよそ +0.2 ms の latency が throughput を 34 % 削減した。cross-AZ で増えるのは帯域幅ではなく latency**

**解説:**
closed-loop の平均 latency は同一 node で 0.355 ms、same-AZ で 0.415 ms、cross-AZ で 0.624 ms であり、Little の法則は 3 経路すべてで成り立ちます。16 ÷ 0.000355 = 45,070（測定値 44,991）、16 ÷ 0.000415 = 38,554（測定値 38,507）、16 ÷ 0.000624 = 25,641（測定値 25,602）です。すべての実行で errors は 0 であり（B は誤り）、response body は約 75 bytes のため帯域幅は無関係です（A は誤り）。実際に同じ 8-stream test は両経路で同一の 9.94 Gbps を示しました。srv-a と srv-b は同じ m5.xlarge type で実行されています（C は誤り）。接続 pool が固定された request/response Service では、AZ hop により throughput は 34 %（38.5k → 25.6k qps）低下し、その原因は latency です。なお、同一 node の p99 1.695 ms / max 13.593 ms は same-AZ（0.728 / 4.502 ms）より悪化しています。これは client と server が 1 node の 4 vCPUs を共有するためであり、network ではなく 45k qps 時の CPU contention によるものです。

</details>

4. 同じ 100 qps / 4 接続で、`-keepalive=false`（request ごとに新規 TCP connection）へ切り替えると、cross-AZ HTTP p50 はどのように変化しましたか？
   - A) 0.704 ms → 1.517 ms（+0.813 ms）、2 倍以上に増加 — 新規 connection には TCP handshake の約 1 RTT に加えて約 0.3 ms の socket setup/teardown が必要であり、経路の RTT が長いほど penalty も大きくなる
   - B) 変化なし — kernel はいずれにせよ connections を再利用する
   - C) 0.704 ms → 0.813 ms、小幅な増加
   - D) p50 は変化せず、悪化したのは p99 のみ
<details>
<summary>回答を表示</summary>

**回答: A) 0.704 ms → 1.517 ms（+0.813 ms）、2 倍以上に増加 — 新規 connection には TCP handshake の約 1 RTT に加えて約 0.3 ms の socket setup/teardown が必要であり、経路の RTT が長いほど penalty も大きくなる**

**解説:**
keepalive=false（30 s、3,000 requests）では、p50 は同一 node で 0.664 ms（+0.405）、same-AZ で 1.079 ms（+0.618）、cross-AZ で 1.517 ms（+0.813）でした。追加コストは経路の RTT とともに増加し、TCP handshake のおよそ 1 RTT に約 0.3 ms の socket setup/teardown を加えたものになります。cross-AZ の ping 平均 0.544 ms に約 0.3 ms を加えると、測定された +0.813 ms とほぼ一致します。0.813 ms は増加分であり、新しい p50 ではありません（C は誤り）。また、p50 自体が 2 倍以上になっています（D は誤り）。AZ をまたぐ Service では、connection pool を維持することで、AZ hop 自体のコスト（+0.24 ms）よりも大きな latency を節約できます。

</details>

5. 180 秒間の sustained run（4 streams）は、AZ 境界を越えて 223.4 GB を転送しました。検証済みの料金（`APN2-DataTransfer-Regional-Bytes`）を使うと、この 1 回の実行のコストはいくらでしたか？
   - A) $0 — Region 内の traffic は無料
   - B) $2.23 — $0.01/GB が 1 回だけ課金される
   - C) 約 $4.47 — $0.01/GB は送信 AZ の "out" と受信 AZ の "in" の両方で課金されるため、方向ごとに $2.23、合計 $4.47（実質 $0.02/GB）
   - D) 1.25 Gbps baseline までの traffic は無料で、それを上回る burst 分だけが課金される
<details>
<summary>回答を表示</summary>

**回答: C) 約 $4.47 — $0.01/GB は送信 AZ の "out" と受信 AZ の "in" の両方で課金されるため、方向ごとに $2.23、合計 $4.47（実質 $0.02/GB）**

**解説:**
`aws pricing get-products` は、usagetype `APN2-DataTransfer-Regional-Bytes`（"Regional Data Transfer - in/out/between AZs …"）を GB あたり $0.0100 として返します。inter-AZ transfer は各 AZ から出る data に対して課金されるため、1 account 内での一方向の bulk transfer であっても、送信 AZ の "out" で $0.01/GB、受信 AZ の "in" で $0.01/GB、実質 $0.02/GB がかかります。この run は 180 s で 223,376,179,200 bytes（9.93 Gbps 時に 223.4 GB）を送信したため、223.4 × $0.01 = 方向ごとに $2.23、合計 $4.47 です。throughput tests における cross-AZ bytes の合計は 12.41 + 24.85 + 223.38 = 260.6 GB、約 $5.21 でした。この run の 18 intervals は 9.92–9.94 Gbps で一定に保たれ、1.25 Gbps baseline に向かって段階的に低下することはありませんでしたが、請求は帯域幅 tier に関係なく byte ごとです（D は誤り）。

</details>

6. デフォルトの `ndots:5` Pod（glibc 2.41）で、`sts.ap-northeast-2.amazonaws.com`（3 dots）を cold resolution すると、tcpdump では DNS queries と NXDOMAIN answers がそれぞれいくつ発生しましたか？
   - A) 2 queries、0 NXDOMAIN — 3 dots の名前は直ちに absolute として query される
   - B) 10 queries、8 NXDOMAIN — 4 つの search-list candidates ごとに A+AAAA が送られ、5 番目の candidate（absolute name）が A answer を返すまでに 8 NXDOMAIN が返る
   - C) 5 queries、4 NXDOMAIN — candidate ごとに A query が 1 回
   - D) 4 queries、2 NXDOMAIN
<details>
<summary>回答を表示</summary>

**回答: B) 10 queries、8 NXDOMAIN — 4 つの search-list candidates ごとに A+AAAA が送られ、5 番目の candidate（absolute name）が A answer を返すまでに 8 NXDOMAIN が返る**

**解説:**
EKS Pod の resolv.conf には、`search bench-net.svc.cluster.local svc.cluster.local cluster.local ap-northeast-2.compute.internal` と `options ndots:5` が設定されています。5 dots 未満の名前は、最初に 4 つの search suffixes のそれぞれと組み合わせて試行され、glibc は candidate ごとに A と AAAA を並列送信します（C は誤り）。capture では、`….bench-net.svc.cluster.local.` → `….svc.cluster.local.` → `….cluster.local.`（この 3 つはいずれも CoreDNS kubernetes plugin から authoritative NXDomain）→ `….ap-northeast-2.compute.internal.`（VPC resolver に forward され NXDomain）→ 最後に `sts.ap-northeast-2.amazonaws.com.` が A 10.0.3.84 / 10.0.2.129 で回答される流れでした。つまり、10 queries、8 NXDOMAIN、5 回の順次 round trips、最初の packet から 4.37 ms であり、有用な answer は最後の 0.38 ms で到着しています。20 回の繰り返しにおける warm median はなお 3.78 ms でしたが、trailing-dot 形式の `sts.ap-northeast-2.amazonaws.com.` は 2 queries、median 0.80 ms でした。CoreDNS の `cache 30` は NXDOMAIN も cache するため、warm 時のコストは upstream lookups ではなく、5 回の順次 Pod↔CoreDNS round trips そのものです。算出例として、application が cluster 全体で毎秒 1,000 回、request ごとに external name 1 つを解決すると、CoreDNS には 2,000 ではなく 10,000 queries/s が送られ、そのうち 8,000 は NXDOMAIN で回答されます。4 queries / 2 NXDOMAIN は、この名前ではなく `kubernetes.default`（1 dot）の結果です（D は誤り）。

</details>

7. 同じ `ndots:5` Pod では、FQDN のように見える `kubernetes.default.svc.cluster.local`（trailing dot なし）も 10 queries と 8 NXDOMAIN を生成しました。なぜ search list 全体をたどったのでしょうか？
   - A) CoreDNS の `kubernetes` plugin は `cluster.local` zone 外の名前に対してのみ即座に回答する
   - B) glibc は `svc.cluster.local` で終わる名前を常に Service 名として扱う
   - C) `.ap-northeast-2.compute.internal` suffix が search list の先頭にあり、最初に試行される
   - D) この名前は 4 dots しかなく ndots 5 より少ないため、glibc には "short" name として扱われる。4 つすべての search suffixes が追加されて試行された後、名前そのものが送信される — trailing dot を付けると 2 queries になる
<details>
<summary>回答を表示</summary>

**回答: D) この名前は 4 dots しかなく ndots 5 より少ないため、glibc には "short" name として扱われる。4 つすべての search suffixes が追加されて試行された後、名前そのものが送信される — trailing dot を付けると 2 queries になる**

**解説:**
`kubernetes.default.svc.cluster.local` には 4 dots があり、ndots 5 未満です。そのため glibc は、最初に `….bench-net.svc.cluster.local`、`….svc.cluster.local`、`….cluster.local`、`….ap-northeast-2.compute.internal` を試行し、8 NXDOMAIN を受け取ります（compute.internal candidate のみ、CoreDNS が upstream に forward したため 2.2 ms かかりました）。5 番目の candidate、すなわち元の名前で初めて A answer が返ります。cold walk は 5.6 ms、warm median は 3.63 ms でした。同じ名前に trailing dot を付けた `kubernetes.default.svc.cluster.local.` は、2 queries、0 NXDOMAIN であり、cold 時 0.4–0.5 ms、warm median 0.46 ms です。`ndots:1` Pod では dot なしの形式も 2 queries（median 0.97 ms）でした。search list は namespace domain → `svc.cluster.local` → `cluster.local` → node domain の順であるため、C は誤りです。また、A と B は glibc または CoreDNS の動作を説明していません。Service FQDN を config file に記述する際は、trailing dot を書くのが安全な選択です。

</details>

8. `dnsConfig.options` で `ndots:1` を設定した Pod では、external names は 10 queries から 2 queries に減りましたが、短い in-cluster name `kubernetes.default` は悪化しました（6 queries、4 NXDOMAIN、median 2.04 ms。ndots:5 では 1.71 ms）。何が起きましたか？
   - A) 1 dot ≥ ndots 1 のため、glibc はまず `kubernetes.default.` を absolute name として送信した。CoreDNS にはこの zone がないため VPC resolver に forward され（NXDomain）、その後に search list をたどって `svc.cluster.local` candidate で answer を得た — cluster-internal names が upstream resolver に漏洩する
   - B) ndots:1 は CoreDNS cache を無効化する
   - C) `kubernetes.default` は ndots:1 ではまったく解決されなかった
   - D) glibc は A と AAAA を順次送信するため、時間が 2 倍になる
<details>
<summary>回答を表示</summary>

**回答: A) 1 dot ≥ ndots 1 のため、glibc はまず `kubernetes.default.` を absolute name として送信した。CoreDNS にはこの zone がないため VPC resolver に forward され（NXDomain）、その後に search list をたどって `svc.cluster.local` candidate で answer を得た — cluster-internal names が upstream resolver に漏洩する**

**解説:**
ndots:1 Pod では、`kubernetes.default`（1 dot）は最初に absolute name `kubernetes.default.` として送信されました。CoreDNS にはこの zone がないため、VPC resolver に forward され、1.6 ms 後に NXDomain が返りました。その後、`kubernetes.default.bench-net.svc.cluster.local`（NXDOMAIN）、最後に `kubernetes.default.svc.cluster.local` が続き、172.20.0.1 で回答されました。結果は 6 queries、4 NXDOMAIN、warm median 2.04 ms であり、ndots:5 時の 4 queries / 2 NXDOMAIN / 1.71 ms より悪化しました（C は誤り）。対照的に external names では大幅な改善があります。`sts.ap-northeast-2.amazonaws.com` と `www.amazon.com` は 10 queries から 2 queries、median 3.5–3.8 ms から 0.5–0.9 ms となり、約 4–7× 高速、queries は 5× 少なくなりました。glibc はデフォルトで A と AAAA を並列送信します（D は誤り）。また、CoreDNS cache は Pod の ndots とは無関係です（B は誤り）。ndots:1 を使用する場合、in-cluster Services は `service.namespace.svc.cluster.local` 形式の FQDN として記述してください。trailing-dot 形式は ndots に関係なく動作し、常に 2 queries、約 0.4–0.8 ms です。

</details>

9. ページ上のすべての fortio latency table は、`-r 0.00001`（10 µs histogram resolution）で rerun した結果です。最初の run が破棄された理由は何ですか？
   - A) 最初の run では error rate が高かった
   - B) fortio のデフォルト `-r 0.001` は 1 ms buckets を意味するため、sub-millisecond response はすべて 1 つの bucket に入り、percentiles はその中で線形補間された（例: 1 ms 未満のすべてで p50 = 0.5 ms）。averages は有効だったが、percentiles は無意味だった
   - C) デフォルトの resolution では fortio は p99.9 を計算しない
   - D) 最初の run は誤って keepalive なしで実行されていた
<details>
<summary>回答を表示</summary>

**回答: B) fortio のデフォルト `-r 0.001` は 1 ms buckets を意味するため、sub-millisecond response はすべて 1 つの bucket に入り、percentiles はその中で線形補間された（例: 1 ms 未満のすべてで p50 = 0.5 ms）。averages は有効だったが、percentiles は無意味だった**

**解説:**
この benchmark における実際の p50 値はすべて 1 ms 未満であり、keepalive HTTP では 0.259–0.704 ms です。fortio のデフォルト `-r 0.001` では histogram bucket は 1 ms のため、これらの samples はすべて最初の bucket に蓄積されます。percentiles は bucket 内で線形補間されるため、経路に関係なく p50 = 0.5 ms のような偽の値が生じます。averages は有効でしたが、percentiles は破棄され、すべての fortio run を `-r 0.00001`（10 µs buckets）で再実行しました。すべての run で errors は 0 であり（A は誤り）、request/response setup は変更されていません（D は誤り）。教訓は、sub-millisecond network を測定する前に、tool の histogram resolution を確認することです。

</details>

10. ページが ClusterIP（kube-proxy iptables）hop または `trafficDistribution: PreferClose` を測定しなかった理由を正しく説明しているのはどれですか？
   - A) fortio は Service DNS name を target にできない
   - B) kube-proxy は IPVS mode だったため、測定対象の iptables hop がなかった
   - C) cluster の aws-load-balancer-controller webhook（`mservice.elbv2.k8s.aws`、`failurePolicy: Fail`）はすべての Service CREATE を intercept するが、controller Pods は Gateway API `ListenerSet` CRD を待って 48 日間 CrashLoopBackOff となっていた。そのため webhook の endpoints は 0 であり、cluster 内のどこでも Service を作成できなかった — webhook は bypass せず、fixture は Pod IPs のみを使用した
   - D) 測定はしたが Pod-IP の数値と一致したため tables から除外した
<details>
<summary>回答を表示</summary>

**回答: C) cluster の aws-load-balancer-controller webhook（`mservice.elbv2.k8s.aws`、`failurePolicy: Fail`）はすべての Service CREATE を intercept するが、controller Pods は Gateway API `ListenerSet` CRD を待って 48 日間 CrashLoopBackOff となっていた。そのため webhook の endpoints は 0 であり、cluster 内のどこでも Service を作成できなかった — webhook は bypass せず、fixture は Pod IPs のみを使用した**

**解説:**
benchmark namespace で Service に対して行ったすべての `kubectl apply` は、`Internal error occurred: failed calling webhook "mservice.elbv2.k8s.aws": … no endpoints available for service "aws-load-balancer-webhook-service"` により拒否されました。read-only diagnosis により、aws-load-balancer-controller v3.2.1（kube-system、2 replicas）が、9,250 restarts を伴い 48 日間 CrashLoopBackOff にあることが分かりました。各 container は `no matches for kind "ListenerSet" in version "gateway.networking.k8s.io/v1"` を繰り返し log に出力し、cache-sync timeout の約 2m18s 後に終了していました。その `MutatingWebhookConfiguration` である `aws-load-balancer-webhook` は、`failurePolicy: Fail` かつ `namespaceSelector: {}` で、cluster 全体のすべての Service に対する CREATE に一致します。このため ready endpoints が 0 の状態では、どの namespace でも Service を作成できません。webhook を bypass したり controller を修復したりする代わりに、fixture は Pod IPs のみを使用しました。これが、ページに ClusterIP hop または `PreferClose`（Kubernetes 1.31 で beta、1.33 で GA）の数値がない理由です（D は誤り）。kube-proxy は `mode: "iptables"` でした（B は誤り）。また、ENA allowance counters（hostNetwork Pod を必要とする `ethtool -S`）も収集していません。さらに、すべての cell は 1 日の単一実行による n = 1 であるため、数値は SLA ではなく桁違いの目安です。

</details>

---

[学習教材に戻る](../../networking/06-pod-network-benchmark.md) | [Networking ホームに戻る](../../networking/README.md)
