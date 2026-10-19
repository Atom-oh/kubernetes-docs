# Cilium Service Mesh トラフィック管理クイズ

Cilium 1.20.3/Gateway API 1.6.3 に照らして確認しました。詳しい例と一次資料は[トラフィック管理ガイド](../../../service-mesh/cilium-service-mesh/02-traffic-management.md)を参照してください。

### 1. CiliumEnvoyConfig で HTTP routing rule を定義するために使う Envoy filter はどれですか?

- **A.** `envoy.filters.network.tcp_proxy`
- **B.** `envoy.filters.network.http_connection_manager`
- **C.** `envoy.filters.http.fault`
- **D.** `envoy.filters.network.redis_proxy`

<details>
<summary>答えを表示</summary>

**答え: B. `envoy.filters.network.http_connection_manager`**

HTTP Connection Manager は HTTP 通信を扱い、inline の `route_config` または RDS から route を取得します。router HTTP filter と参照先の Cluster resource も必要です。バックエンド Service を列挙するだけでは不十分です。

</details>

### 2. CiliumNetworkPolicy で L7 HTTP rule を定義するとき、利用できない field はどれですか?

- **A.** `method`
- **B.** `path`
- **C.** `headers`
- **D.** `body`

<details>
<summary>答えを表示</summary>

**答え: D. `body`**

HTTP policy では、structured `headerMatches` を含め、method、path、headers に一致させられます。任意の request body 内の field を認可することはできません。認証と application-level authorization は別途必要です。

</details>

### 3. Cilium 1.20.3 で Kafka topic 単位の access をどのように制御しますか?

- **A.** Cilium の `rules.kafka` を変更せずに使う
- **B.** HTTP body rule で Kafka message を検査する
- **C.** broker の ACL を使い、到達性は別途 L4 policy で制御する
- **D.** すべての rule を削除し、topic 権限が残ると仮定する

<details>
<summary>答えを表示</summary>

**答え: C. broker の ACL を使い、到達性は別途 L4 policy で制御する**

Cilium 1.20.3 の L7 rule schema が対応するのは HTTP と DNS であり、旧 `rules.kafka` object は拒否されます。broker への到達性には L4 network policy を使い、topic、group、operation の制御には Kafka TLS/SASL と broker ACL を使ってください。旧 Kafka rule を削除しても topic 単位の認可は維持されません。

</details>

### 4. Cilium eBPF load balancing のうち、適用可能な経路で Maglev が提供するものは何ですか?

- **A.** 完全にランダムな振り分け
- **B.** backend 選択の一貫性を保ち、membership 変更時の再割り当てを減らす
- **C.** 削除された backend への接続が必ず維持される
- **D.** 最小のメモリ使用量

<details>
<summary>答えを表示</summary>

**答え: B. backend 選択の一貫性を保ち、membership 変更時の再割り当てを減らす**

該当する外部 load balancing で、Maglev は backend 集合が変わったときの flow 再割り当てを抑えます。これは ClientIP session affinity とは別の機能であり、利用できなくなった backend への接続を維持できるわけではありません。Cilium の socket-level east–west 経路では、この Maglev 選択は行われません。

</details>

### 5. Gateway API HTTPRoute で weight による traffic split を正しく設定する方法はどれですか?

- **A.** `split` field を使う
- **B.** `backendRefs` に `weight` field を指定する
- **C.** `trafficPolicy` を使う
- **D.** `destinationRule` を使う

<details>
<summary>答えを表示</summary>

**答え: B. `backendRefs` に `weight` field を指定する**

`backendRefs` の weight は相対的な選択確率を定義します。90 と 10 は 90:10 の割合を表しますが、10 request ごとに厳密に 9 対 1 になることや、user ごとの session 固定を保証しません。Service、port、parent listener が解決でき、Route の接続が受理される必要があります。

</details>

### 6. CiliumEnvoyConfig の retry policy で `retry_on` に指定できない値はどれですか?

- **A.** `5xx`
- **B.** `reset`
- **C.** `timeout`
- **D.** `connect-failure`

<details>
<summary>答えを表示</summary>

**答え: C. `timeout`**

`timeout` は `retry_on` token ではありません。`per_try_timeout` は最初の試行を含む各 upstream attempt の上限であり、backoff interval ではありません。ガイドでは安全な GET operation だけを再試行し、GET 以外の retry を明示的に無効にしたうえで、routing 前に caller 指定の Envoy retry/timeout override を削除します。

</details>

### 7. Cilium の DNS L7 policy が主に制御するものは何ですか?

- **A.** DNS server の性能向上
- **B.** 選択した DNS resolver に送る、特定 domain の query だけを許可する
- **C.** DNS cache の無効化
- **D.** DNS over HTTPS のサポート

<details>
<summary>答えを表示</summary>

**答え: B. 選択した DNS resolver に送る、特定 domain の query だけを許可する**

DNS rule は、選択した信頼できる resolver に送られる query name を制限します。それだけで応答された IP address への接続を許可するわけではなく、data exfiltration や DoH を確実に防ぐものでもありません。destination/port policy を別途追加し、UDP/TCP と実際の resolver/search-list の動作も確認してください。

</details>

### 8. CiliumEnvoyConfig で local rate limiting を設定する filter はどれですか?

- **A.** `envoy.filters.http.ratelimit`
- **B.** `envoy.filters.http.local_ratelimit`
- **C.** `envoy.filters.http.bandwidth_limit`
- **D.** `envoy.filters.http.throttle`

<details>
<summary>答えを表示</summary>

**答え: B. `envoy.filters.http.local_ratelimit`**

`envoy.filters.http.local_ratelimit` は、明示的な enabled/enforced fraction を備える token bucket を使います。route-level override を含め、fraction の既定値は 0% です。例では Envoy process ごとに 1 つの bucket を使い、その worker thread 間で共有します。cluster 全体や user ごとの quota ではありません。

</details>

### 9. Gateway API で HTTP から HTTPS への redirect に使う filter type はどれですか?

- **A.** `URLRewrite`
- **B.** `RequestMirror`
- **C.** `RequestRedirect`
- **D.** `ResponseHeaderModifier`

<details>
<summary>答えを表示</summary>

**答え: C. `RequestRedirect`**

`RequestRedirect` は `scheme: https` を指定した redirect response を返せます。301 は恒久 redirect ですが、client によっては request method が変わる場合があります。HTTP listener 用の Route を別に設定し、動作する HTTPS listener と certificate を用意してください。method 変更を伴う意味で write request を暗黙に redirect しないでください。

</details>

### 10. Cilium Service Mesh の traffic mirroring (shadowing) は何のために使いますか?

- **A.** 通信の暗号化
- **B.** production traffic を test 環境へ複製する
- **C.** load balancing の最適化
- **D.** cache の無効化

<details>
<summary>答えを表示</summary>

**答え: B. production traffic を test 環境へ複製する**

`request_mirror_policies` は shadow backend に request のコピーを送り、その response を caller の結果には使いません。それでもデータが複製され、resource を消費し、副作用を起こす可能性があります。ガイドでは承認済み GET/HEAD traffic だけを隔離された backend に mirror し、ほかの method は mirror しません。user への影響がゼロになる保証はありません。

</details>

### 11. 現行 Envoy は `weighted_clusters` の weight 合計をどのように扱いますか?

- **A.** request 数の上限を設定する
- **B.** 各 Cluster の weight の合計を使う。`total_weight` は非推奨
- **C.** weight を timeout として扱う
- **D.** すべての request で最小 weight の Cluster を使う

<details>
<summary>答えを表示</summary>

**答え: B. 各 Cluster の weight の合計を使う。`total_weight` は非推奨**

現行 Envoy は各 Cluster の weight の合計を使います。`total_weight` は非推奨で、更新された例からは省かれています。weight 90 と 10 は相対選択比 90:10 を表しますが、自動 promotion/rollback や、一定期間内の厳密な request quota を実装するものではありません。

</details>

### 12. Gateway API HTTPRoute で header-based routing を設定する `matches` field はどれですか?

- **A.** `headerMatchers`
- **B.** `headers`
- **C.** `requestHeaders`
- **D.** `matchHeaders`

<details>
<summary>答えを表示</summary>

**答え: B. `headers`**

HTTPRoute の `matches.headers` で header の match 条件を表します。1 つの match 内に複数の header を指定すると、すべてが AND 条件になります。選択には Gateway API の path/header precedence rule が適用されます。client が送る version/canary header は認証情報ではありません。

</details>
