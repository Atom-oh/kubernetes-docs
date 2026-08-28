# Istio 比較クイズ

> **対応バージョン**: Istio 1.30 / EKS 1.36
> **最終更新**: August 21, 2026

このクイズでは、sidecar と ambient mode の選択基準、特に EKS 1.36 のテスト結果に関する理解を確認します。

## 選択問題（1～6）

### 問題 1: ambient waypoint の 503 の根本原因

ambient mode で rollout 中に waypoint パスで断続的な 503 が発生する根本原因は何ですか？

A. Pod の再起動時に IP が重複して割り当てられる
B. waypoint は宛先 IP:Port をキーにした接続を再利用し、Pod の終了時に ztunnel が waypoint へ通知しない
C. NetworkPolicy が waypoint トラフィックをブロックしている
D. waypoint は STRICT mTLS をサポートしていない

<details>
<summary>回答と解説</summary>

**回答: B**

**解説:**

waypoint（Envoy）は、宛先 IP:Port をキーとする connection pool を管理・再利用します。対象 Pod が終了しても、ztunnel は waypoint に明示的に通知しません。終了した Pod の IP が新しい Pod に再割り当てされると、waypoint は無効になった接続を再利用し、503 を返す可能性があります。これが懸念の背後にある仕組み、すなわち重複 IP 割り当てではなく **connection lifecycle management** であり、§4 で測定された 503 の発生率もこれと整合します。

**参考資料:**
- [Sidecar vs Ambient Mode 選択ガイド](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Ambient Mode: Waypoint Proxy](../../../service-mesh/istio/advanced/01-ambient-mode.md)

</details>

---

### 問題 2: EKS 1.36 のテスト結果の解釈

専用の single-tenant EKS 1.36 cluster 上で、繰り返し rollout を行いながら 100 qps x 600s（60,000 request）の負荷をかけた場合、sidecar の 503 発生率は 0.5%、ambient-L4（waypoint なし）は実際の 503 がゼロ（ただし TCP error は 0.3%）、ambient-L7（waypoint あり）は 2.6% でした。正しい解釈はどれですか？

A. ambient は常に sidecar より安定している
B. waypoint 経由の routing では sidecar より高い 503 発生率になるが、L4 のみ（waypoint なし）では実際の 503 は発生しない
C. ambient-L4 の TCP error（0.3%）は waypoint の 503 と同じ現象である
D. socket 使用量が最も少ない mode が最も安定している

<details>
<summary>回答と解説</summary>

**回答: B**

**解説:**

データが示すのは、ambient が sidecar より一律に優れている、あるいは劣っているということではありません。トラフィックが **waypoint** を通るかどうかが決定変数です。ambient-L7（waypoint あり）の 503 発生率は sidecar のおよそ 5 倍（2.6% 対 0.5%）でしたが、ambient-L4（waypoint なし）では実際の 503 はゼロでした。ただし、ambient-L4 が failure-free であることを意味するわけではなく、代わりに TCP-level connection drop（0.3%）という異なる failure mode が現れました。これは、waypoint が dead connection に request を転送して 503 を返すこととは異なります（したがって C は不正解です）。socket 使用量は安定性の指標ではなく、接続が再確立された頻度の proxy にすぎません（したがって D は不正解です）。実際、ambient-L4 は *最も多くの* socket を消費しながら、503 はゼロでした。

**参考資料:**
- [Sidecar vs Ambient Mode 選択ガイド: Zero-Downtime Rollout の結果](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### 問題 3: NetworkPolicy と ambient

port-based NetworkPolicy を使用している cluster で、トラフィックが ambient-mode Pod に到達しません。application は port 8080 で listen しています。最も可能性の高い原因と修正は何ですか？

A. ambient は NetworkPolicy をサポートしていないため、NetworkPolicy を削除する必要がある
B. 実際のトラフィックは HBONE tunnel（TCP 15008）を介して到着するため、NetworkPolicy に 15008 の inbound allow rule が必要である
C. PeerAuthentication を PERMISSIVE に変更する必要がある
D. istio-cni DaemonSet を再起動する必要がある

<details>
<summary>回答と解説</summary>

**回答: B**

**解説:**

ambient mode では、ztunnel が Pod traffic を HBONE（mTLS）tunnel でラップし、port 15008 で配信します。application port（8080）のみを許可する NetworkPolicy は、実際に到着する 15008 のトラフィックをブロックします。修正するには、対象 Pod に対して TCP 15008 の inbound allow rule を追加します。sidecar では、sidecar が application と同じ Pod network namespace を共有するため、この追加 rule は必要ありません。

**参考資料:**
- [Sidecar vs Ambient Mode 選択ガイド: NetworkPolicy](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### 問題 4: non-idempotent API と retry policy

注文作成のような non-idempotent API path で、mesh-level retry（例: waypoint retry、VirtualService retries）をデフォルトで有効にしないことが推奨されるのはなぜですか？

A. retry により CPU overhead が大きくなりすぎる
B. waypoint が dead connection に request を転送して 503 を返す場合、retry によって server-side ですでに完了していた request が再実行され、重複実行（例: 重複した注文）が発生する可能性がある
C. retry は STRICT mTLS と互換性がない
D. retry は ambient mode ではサポートされていない

<details>
<summary>回答と解説</summary>

**回答: B**

**解説:**

503 は client-visible failure ですが、その failure category には、request が実際には server に到達し、処理を完了していたケースが隠れています。connection の切断と application の処理完了の競合により、失われたのは *response* だけである場合です。このとき、mesh retry は別の connection を介して同じ logical request を再送します。server が idempotency を保証しない場合、request は二度処理されます。このリスクは注文作成のような不可逆な operation で特に深刻なため、retry をデフォルトで有効にせず、個別に検証する方が安全です。follow-up test（T2）では、sidecar と ambient-L7 waypoint retry の両方に対し、継続的な rollout churn を 300s 実行しましたが、その実行では重複実行はゼロでした。これはこの race が *一般的* であるという確信を下げますが、*安全* であることを示すものではありません。非常に狭い timing window が必要であり、より長時間または高 throughput のテストなら、依然として検出できる可能性があるためです。

**参考資料:**
- [Sidecar vs Ambient Mode 選択ガイド: 緩和策としての Retry のリスク](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### 問題 5: sidecar と ambient の rollout を公平に比較する

rollout test において、sidecar は ambient より client-visible 503 が少なくなりました。これが本質的により安定した data plane を反映しているかを最も適切に判断する experiment はどれですか？

A. GET request のみを送信し、最終的な 200 の件数を比較する
B. sidecar ではデフォルトの retry を維持し、ambient では retry を無効にする
C. 両方の mode で write-route retry を `attempts: 0` に設定し、生の HTTP/TCP failure、retry count、最終 outcome を個別に記録する
D. 平均 CPU 使用量が低い mode をより安定していると見なす

<details>
<summary>回答と解説</summary>

**回答: C**

**解説:**

sidecar Envoy と waypoint Envoy は L7 retry によって client から raw failure を隠せますが、ztunnel は HTTP 503 を解釈したり HTTP request を再送したりできない L4 proxy です。write retry を同等に無効化し、HTTP 503、TCP reset/EOF、`upstream_rq_retry`、実際の upstream delivery、最終 client outcome を個別に記録してください。そうしないと、この test では「failure の発生が少なかった」と「retry によってより多くの failure が隠された」を区別できません。

**参考資料:**
- [Sidecar vs Ambient Mode 選択ガイド: raw failure の測定](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Retry and Timeout](../../../service-mesh/istio/traffic-management/05-retry-timeout.md)

</details>

---

### 問題 6: Cilium authentication と encryption

mutual authentication を `required` に設定した、確立済みの Cilium data plane について正しい記述はどれですか？

A. すべての application payload は workload TLS により自動的に暗号化される
B. endpoint identity authentication と payload encryption は別である。confidentiality には WireGuard/IPsec またはサポート対象の native ztunnel mTLS が必要である
C. 実装、成熟度、運用 semantics において、Istio `PeerAuthentication STRICT` と同一である
D. mutual authentication を有効にすると CiliumNetworkPolicy は不要になる

<details>
<summary>回答と解説</summary>

**回答: B**

**解説:**

確立済みの Cilium mutual authentication は、application data path とは別の out-of-band handshake によって peer identity を検証します。authentication policy だけでは payload は自動的に暗号化されないため、WireGuard/IPsec を別途選択するか、サポート対象 platform で native ztunnel mTLS preview を検証してください。結果を Istio `STRICT` workload mTLS と同一と見なすのではなく、identity authorization、peer authentication、encryption in transit をそれぞれ個別に評価してください。

**参考資料:**
- [Cilium Service Mesh Security](../../../service-mesh/cilium-service-mesh/03-security.md)

</details>

---

## 採点

- 6 問中何問正解したかを数えてください。
- 6/6: 測定された evidence を用いて、sidecar、ambient、Cilium の選択と retry risk を説明できます。
- 4-5/6: raw-failure measurement または authentication と encryption の違いを復習してください。
- 0-3/6: 最初から [Sidecar vs Ambient Mode 選択ガイド](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md) を読み直してください。

## 学習リソース

- [Sidecar vs Ambient Mode 選択ガイド](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Ambient Mode](../../../service-mesh/istio/advanced/01-ambient-mode.md)
- [mTLS](../../../service-mesh/istio/security/01-mtls.md)
- [Cilium Service Mesh Security](../../../service-mesh/cilium-service-mesh/03-security.md)
