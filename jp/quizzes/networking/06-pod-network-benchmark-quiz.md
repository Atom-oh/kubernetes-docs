# Pod Network Benchmark クイズ

この問題は、2026年9月2日のレポートに基づきます。普遍的な性能値や課金保証を示すものではありません。

1. `ping -c 200 -i 0.05` で測定した場合、平均 Pod-to-Pod RTT は同一 node → 同一 AZ 内の別 node → 別 AZ でどのように変化しましたか？
   - A) 0.040 ms → 0.544 ms → 0.339 ms — cross-AZ の方が same-AZ より高速だった
   - B) 3 つの経路はすべて約 0.3 ms のノイズ範囲内だった
   - C) 0.040 ms → 0.339 ms → 0.544 ms — node を離れると +0.30 ms、AZ を離れるとさらに +0.21 ms 増加する、段階的な増加
   - D) 0.040 ms → 0.339 ms → 5.4 ms — AZ 境界により RTT がミリ秒単位まで増加した
<details>
<summary>回答を表示</summary>

**回答: C) 0.040 ms → 0.339 ms → 0.544 ms — node を離れると +0.30 ms、AZ を離れるとさらに +0.21 ms 増加する、段階的な増加**

**解説:**
報告された ping の平均値は、経路ごとに 200 回測定し、損失は 0/200 でした。別 AZ と同一 AZ の差は 0.205 ms（約 0.21 ms）、別 AZ と同一ノードの差は 0.504 ms です。HTTP の p50 は 0.259 → 0.461 → 0.704 ms でした。HTTP の中央値から ping の平均値を引いても、ユーザー空間の処理時間だけを分離して測定したことにはなりません。5.4 ms は負荷をかけた TCP RTT の値で、キューがどこにあるかは測定されていません。別の Istio レポートにある +1.29 ms は、異なるハードウェアとワークロードによるシナリオ全体の p50 差です。単一のプロキシ処理時間ではなく、この測定値に加算できません。

</details>

2. 単一の iperf3 TCP stream（`-P 1`）は same-AZ と cross-AZ の両経路で 4.96 Gbps にとどまり、8 streams（`-P 8`）では両方とも 9.94 Gbps に達しました。この 2 つの数値を最もよく説明するものは何ですか？
   - A) 4.96 Gbps は client CPU core 1 個の飽和であり、8 streams が高速なのはより多くの core を使用するため
   - B) 4.96 Gbps は一般的な 5 Gbps の単一フロー上限と整合し、8 本の並列フローは m5.xlarge の 10 Gbps バースト上限に近づいた
   - C) 4.96 Gbps は m5.xlarge の baseline bandwidth であり、8 streams は burst credits を使って peak に到達した
   - D) 単一 stream では Jumbo frames（MTU 9001）が有効になっていなかった
<details>
<summary>回答を表示</summary>

**回答: B) 4.96 Gbps は一般的な 5 Gbps の単一フロー上限と整合し、8 本の並列フローは m5.xlarge の 10 Gbps バースト上限に近づいた**

**解説:**
異なるノード上の Pod 間では、同一 AZ と別 AZ の単一フローがどちらも 4.96 Gbps でした。これは一般的な 5 Gbps の単一フロー上限と整合しますが、普遍的な上限を証明するものではありません。測定中のクライアント CPU 使用率はノード間経路で 19.5 %／20.0 %（1 コア比）で、同一ノードの単一フロー測定時の 99.8 % とは異なります。帯域幅制限という解釈を支持しますが、あらゆるホスト側のボトルネックを否定するものではありません。m5.xlarge のベースライン帯域幅は 1.25 Gbps、ベストエフォートのバースト上限は 10 Gbps です。20 秒の測定だけでは、上限を持続できることは証明されません。再送は 4／2 から 5,874／5,979 に増えましたが、ENA カウンターを採取していないため、シェーピングが原因とは確認できません。MSS 8949（MTU 9001）は全測定で同じでした。AWS はクラスター配置グループ内で最大 10 Gbps、条件を満たす同一 AZ の ENA Express フローで最大 25 Gbps も案内しています。したがって 5 Gbps は一律の上限ではありません。

</details>

3. 8-stream iperf3 の帯域幅は same-AZ と cross-AZ のどちらも同じ 9.94 Gbps でしたが、fortio の closed-loop maximum（`-qps 0`、16 接続、20 s）は same-AZ の 38,507 qps から cross-AZ の 25,602 qps へ低下しました。なぜですか？
   - A) inter-AZ link は request/response traffic の帯域幅を半減させる
   - B) cross-AZ 経路で errors と retries が増加した
   - C) srv-b をホストする node は srv-a の node より CPU が遅かった
   - D) 約 16 件の同時リクエストを保つ場合、スループット ≈ 16 ÷ 平均レイテンシーと整合する。測定された速度差は 33.5 % だが、AZ による普遍的なペナルティを証明するものではない
<details>
<summary>回答を表示</summary>

**回答: D) 約 16 件の同時リクエストを保つ場合、スループット ≈ 16 ÷ 平均レイテンシーと整合する。測定された速度差は 33.5 % だが、AZ による普遍的なペナルティを証明するものではない**

**解説:**
報告された平均レイテンシーは 0.355／0.415／0.624 ms でした。16 をこれらの値で割ると 45,070／38,554／25,641 qps となり、実測値の 44,991／38,507／25,602 qps に近づきます。測定条件下では、Little の法則が同時実行数、スループット、平均応答時間の関係を説明しますが、遅延の唯一の原因までは特定しません。エラーは 0 件で、両サーバーのインスタンスタイプも同じでしたが、それだけで選択肢 B や C の根拠にはなりません。同一ノード経路のテール悪化には CPU 競合が影響した可能性がありますが、プロファイリングでは確認されていません。報告上の差は 33.5 % です。

</details>

4. 同じ 100 qps / 4 接続で、`-keepalive=false`（request ごとに新規 TCP connection）へ切り替えると、cross-AZ HTTP p50 はどのように変化しましたか？
   - A) 0.704 ms → 1.517 ms（+0.813 ms）で 2 倍以上に増加した。接続確立の処理が加わるが、この実験では各要因を個別に測定していない
   - B) 変化なし — kernel はいずれにせよ connections を再利用する
   - C) 0.704 ms → 0.813 ms、小幅な増加
   - D) p50 は変化せず、悪化したのは p99 のみ
<details>
<summary>回答を表示</summary>

**回答: A) 0.704 ms → 1.517 ms（+0.813 ms）で 2 倍以上に増加した。接続確立の処理が加わるが、この実験では各要因を個別に測定していない**

**解説:**
keepalive を無効にしたときの p50 は、同一ノードで 0.664 ms（+0.405）、同一 AZ で 1.079 ms（+0.618）、別 AZ で 1.517 ms（+0.813）でした。0.813 ms は新しい p50 ではなく増加分です（C は誤り）。接続確立は処理を追加しますが、ping RTT を差し引いても固定のソケット処理時間を個別に測定したことにはなりません。接続再利用をアプリケーションで検証してください。TIME_WAIT は測定されておらず、接続を閉じる側と終了動作にも依存します。

</details>

5. 180 秒間の測定（4 フロー）では 223,376,179,200 ペイロードバイトを転送しました。レポートの明示的な 10 進 GB 換算と、各 EC2 端点に対する $0.01/GB の料金モデルでは、推定額はいくらですか？
   - A) $0 — Region 内の traffic は無料
   - B) $2.23 — $0.01/GB が 1 回だけ課金される
   - C) レポートの 10 進 GB 換算では約 $4.47。送信側と受信側の両方に $0.01/GB を適用した額で、実際の請求額は確認していない
   - D) 1.25 Gbps baseline までの traffic は無料で、それを上回る burst 分だけが課金される
<details>
<summary>回答を表示</summary>

**回答: C) レポートの 10 進 GB 換算では約 $4.47。送信側と受信側の両方に $0.01/GB を適用した額で、実際の請求額は確認していない**

**解説:**
正確なペイロードは 223,376,179,200 バイトです。レポートの過去の試算では 10 億で割って 10 進 GB に換算し、$0.01/GB を 2 端点分適用して約 $4.47 としました。同じモデルで 3 回の cross-AZ iperf3 実行は合計 260,633,264,128 バイト、約 $5.21 です。一方向のペイロードでも両端で課金される場合があります。ただし、公開されている get-products の料金は実際のアカウント請求額ではなく、課金単位が 10 進ペイロード GB と一致することもこの監査では確認していません。CUR の計量単位、プロトコルのオーバーヘッド、両端、適用される割引を照合してください。18 区間の測定値が 9.92～9.94 Gbps だったことは、1.25 Gbps までの転送が無料になることを意味しません。

</details>

6. デフォルトの `ndots:5` Pod（glibc 2.41）で、`sts.ap-northeast-2.amazonaws.com`（3 dots）を cold resolution すると、tcpdump では DNS queries と NXDOMAIN answers がそれぞれいくつ発生しましたか？
   - A) 2 queries、0 NXDOMAIN — 3 dots の名前は直ちに absolute として query される
   - B) この測定では 10 queries、8 NXDOMAIN。4 つの search candidate がそれぞれ A と AAAA で失敗し、その後 absolute name が成功した
   - C) 5 queries、4 NXDOMAIN — candidate ごとに A query が 1 回
   - D) 4 queries、2 NXDOMAIN
<details>
<summary>回答を表示</summary>

**回答: B) この測定では 10 queries、8 NXDOMAIN。4 つの search candidate がそれぞれ A と AAAA で失敗し、その後 absolute name が成功した**

**解説:**
この Pod には記録された 4 項目の search list があり、glibc は AF_UNSPEC で名前を解決しました。4 つの search 候補はそれぞれ A と AAAA の両方で失敗し、最後に absolute name が成功したため、合計 10 query と 8 NXDOMAIN です。最初のパケットから有効な A 応答まで 4.37 ms かかりましたが、これは最初のプロセス呼び出し全体の所要時間ではなく、表では AAAA 応答の完了時間も計測されていません。最後の 0.38 ms で有効な A 応答が届きました。温まった状態の中央値は 3.78 ms、末尾にドットを付けた場合は 0.80 ms でした。`cache 30` は TTL の上限であり、上流への問い合わせがないことを証明しません。同じ応答パターンで毎秒 1,000 回解決すると 10,000 query/s と 8,000 NXDOMAIN になりますが、CoreDNS の CPU 使用率が 80 % になるという意味ではありません。名前によっては、`kubernetes.default` のように 4 query で成功する場合もあります。

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
リゾルバーはドットの数を数えますが、Kubernetes Service のサフィックスを見て search list を省略するわけではありません。この測定では、4 つの search suffix を付けた候補がすべて失敗し、その後に名前自体が問い合わせられました。末尾のドットなしでは warm median が 3.63 ms、付けた場合は 0.46 ms でした。候補への forward は 2.2 ms、wire walk は 5.6 ms、別途記録された初回プロセス全体の所要時間は 7.40 ms です。末尾のドットで DNS 名は absolute になりますが、アプリケーション URL に使う場合は Host／SNI、証明書、署名との互換性が必要です。あらゆる HTTPS や AWS SDK のエンドポイントで安全に使えるとは限りません。

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
ndots:1 Pod では、`kubernetes.default`（1 dot）は最初に absolute name `kubernetes.default.` として送信されました。CoreDNS にはこの zone がないため、VPC resolver に forward され、1.6 ms 後に NXDOMAIN が返りました。その後、`kubernetes.default.bench-net.svc.cluster.local`（NXDOMAIN）、最後に `kubernetes.default.svc.cluster.local` が続き、172.20.0.1 で回答されました。結果は 6 queries、4 NXDOMAIN、warm median 2.04 ms であり、ndots:5 時の 4 queries / 2 NXDOMAIN / 1.71 ms より悪化しました（C は誤り）。対照的に external names では改善しました。`sts.ap-northeast-2.amazonaws.com` と `www.amazon.com` は 10 queries から 2 queries、median 3.5～3.8 ms から 0.5～0.9 ms となり、約 4～7 倍高速、queries は 5 分の 1 になりました。glibc はデフォルトで A と AAAA を並列送信します（D は誤り）。また、CoreDNS cache は Pod の ndots とは無関係です（B は誤り）。ndots:1 を使う場合は、in-cluster Service を `service.namespace.svc.cluster.local` 形式の FQDN で指定してください。末尾のドットは search list を回避しますが、query 数や latency が常に一定になるわけではありません。

</details>

9. `-r 0.00001` で再実行した Fortio の結果をどう解釈すべきですか？
   - A) 最初の run では error rate が高かった
   - B) デフォルトの最小 bucket は 1 ms で、比較には粗すぎたため 10 µs の分解能で再実行した。ただし、単一 bucket に入る値が常に p50 = 0.5 ms を意味するわけではない
   - C) デフォルトの resolution では fortio は p99.9 を計算しない
   - D) 最初の run は誤って keepalive なしで実行されていた
<details>
<summary>回答を表示</summary>

**回答: B) デフォルトの最小 bucket は 1 ms で、比較には粗すぎたため 10 µs の分解能で再実行した。ただし、単一 bucket に入る値が常に p50 = 0.5 ms を意味するわけではない**

**解説:**
Fortio 1.69.5 の `-r` は秒単位です。`0.001` は最小 bucket が 1 ms、`0.00001` は 10 µs です。より大きい bucket は幅が広がる場合があります。パーセンタイルは bucket の範囲内で補間され、最初と最後の bucket には実測の最小値と最大値が影響します。そのため、「1 ms 未満の応答が同じ bucket に入れば、必ず p50 は 0.5 ms」という主張は誤りです。keepalive 時の中央値は 0.259～0.704 ms でしたが、テールの一部と新規接続時の中央値は 1 ms を超えます。再実行の経緯、平均値、全ヒストグラム、エラー数を保ち、補間自体を無意味と決めつけないでください。

</details>

10. レポートが Service 経由のトラフィック分散を比較しなかった理由を正しく説明しているのはどれですか？
   - A) fortio は Service DNS name を target にできない
   - B) kube-proxy は IPVS mode だったため、測定対象の iptables hop がなかった
   - C) レポートによれば、LBC の admission webhook がベンチマークでの Service 作成要求を拒否したため、アプリケーションテストでは webhook を回避せず Pod IP を使った
   - D) 測定はしたが Pod-IP の数値と一致したため tables から除外した
<details>
<summary>回答を表示</summary>

**回答: C) レポートによれば、LBC の admission webhook がベンチマークでの Service 作成要求を拒否したため、アプリケーションテストでは webhook を回避せず Pod IP を使った**

**解説:**
レポートに記載された過去の診断は、LBC v3.2.1、2 replicas、48 日間の CrashLoopBackOff、9,250 restarts、`no matches for kind "ListenerSet" in version "gateway.networking.k8s.io/v1"` を挙げ、その後約 2 分 18 秒で cache-sync timeout になったとしています。これはレポートに基づく記述であり、この監査では元ログの回収や稼働中クラスターの確認をしていません。`failurePolicy: Fail` の webhook は、ルール、selector、条件に一致する要求を拒否します。`namespaceSelector: {}` だけでは、すべての Service CREATE が対象だったとは証明できません。アプリケーションテストでは Service を使わず、DNS テストでは既存の kube-dns を使いました。`PreferClose` は現在 `PreferSameZone` の非推奨エイリアスで、どちらもこのレポートでは測定されていません。ENA カウンターは採取されず、独立した反復測定もありません。

</details>

---

[学習教材に戻る](../../networking/06-pod-network-benchmark.md) | [Networking ホームに戻る](../../networking/README.md)
