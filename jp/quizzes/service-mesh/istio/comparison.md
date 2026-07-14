# 比較クイズ

> **対応バージョン**: Istio 1.30 / EKS 1.36 **最終更新**: July 7, 2026

このクイズでは、sidecar と ambient モードの選択基準、特に EKS 1.36 のテスト結果についての理解を確認します。

## 多肢選択問題（1～4）

### 問題 1: ambient waypoint 503 の根本原因

ambient モードでのロールアウト中、waypoint 経路で断続的に 503 が発生する根本原因は何ですか？

A. Pod の再起動時に IP が重複して割り当てられる B. waypoint は宛先 IP:Port をキーとして connection を再利用し、ztunnel は Pod の終了時に waypoint へ通知しない C. NetworkPolicy が waypoint トラフィックをブロックする D. waypoint は STRICT mTLS をサポートしていない

<details>

<summary>回答 &#x26; 解説</summary>

**回答: B**

**解説:**

waypoint（Envoy）は、宛先 IP:Port をキーとする connection pool を管理し、再利用します。対象 Pod の終了時に、ztunnel は waypoint へ明示的に通知しません。終了した Pod の IP が新しい Pod に再割り当てされると、waypoint は無効になった connection を再利用して 503 を返す可能性があります。これが懸念の背景にあるメカニズムであり、つまり IP の重複割り当てではなく、**connection lifecycle management** です。また、§4 の測定済み 503 率もこれと整合します。

**参照:**

* [Sidecar vs Ambient Mode Selection Guide](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
* [Ambient Mode: Waypoint Proxy](../../../service-mesh/istio/advanced/01-ambient-mode.md)

</details>

***

### 問題 2: EKS 1.36 のテスト結果の解釈

専用の single-tenant EKS 1.36 cluster で、繰り返しロールアウトしながら 100 qps x 600s（60,000 requests）の負荷をかけたところ、sidecar の 503 率は 0.5%、ambient-L4（waypoint なし）では実際の 503 はゼロ（ただし代わりに TCP errors が 0.3%）、ambient-L7（waypoint あり）では 2.6% でした。正しい解釈はどれですか？

A. ambient は常に sidecar より安定している B. waypoint を経由する routing は sidecar より高い 503 率を生むが、L4 のみを使用する場合（waypoint なし）は実際の 503 を生まない C. ambient-L4 の TCP errors（0.3%）は waypoint の 503 と同じ現象である D. socket 使用量が最も少ないモードが最も安定している

<details>

<summary>回答 &#x26; 解説</summary>

**回答: B**

**解説:**

データは、"ambient" が sidecar より一律に優れているわけでも劣っているわけでもなく、トラフィックが **waypoint** を経由するかどうかが決定要因であることを示しています。ambient-L7（waypoint あり）の 503 率は sidecar の約 5 倍（2.6% 対 0.5%）でしたが、ambient-L4（waypoint なし）では実際の 503 はゼロでした。ただし、ambient-L4 が failure-free という意味ではありません。代わりに別の failure mode、すなわち TCP-level connection drops（0.3%）が発生しました。これは waypoint が切断された connection に request を転送して 503 を返すこととは異なります（したがって C は誤りです）。socket 使用量は安定性の指標ではなく、connection が再確立された頻度の proxy にすぎません（したがって D は誤りです）。実際、ambient-L4 は最も多くの sockets を消費しましたが、503 はゼロでした。

**参照:**

* [Sidecar vs Ambient Mode Selection Guide: Zero-Downtime Rollout Results](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

***

### 問題 3: NetworkPolicy と ambient

port-based NetworkPolicies を使用している cluster で、トラフィックが ambient モードの Pod に到達していません。application は port 8080 を listen しています。最も可能性の高い原因と修正は何ですか？

A. ambient は NetworkPolicy をサポートしていないため、NetworkPolicy を削除する必要がある B. 実際のトラフィックは HBONE tunnel（TCP 15008）を通って到着するため、NetworkPolicy に 15008 の inbound allow rule を追加する必要がある C. PeerAuthentication を PERMISSIVE に変更する必要がある D. istio-cni DaemonSet を再起動する必要がある

<details>

<summary>回答 &#x26; 解説</summary>

**回答: B**

**解説:**

ambient モードでは、ztunnel が Pod トラフィックを HBONE（mTLS）tunnel でラップし、port 15008 で配信します。application port（8080）のみを許可する NetworkPolicy は、実際に到着する 15008 のトラフィックをブロックします。修正方法は、対象 Pod に対する TCP 15008 の inbound allow rule を追加することです。sidecar では、sidecar が application と同じ Pod network namespace を共有するため、この追加 rule は必要ありません。

**参照:**

* [Sidecar vs Ambient Mode Selection Guide: NetworkPolicy](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

***

### 問題 4: non-idempotent API と retry policy

注文作成のような non-idempotent API path で、mesh-level retry（例: waypoint retry、VirtualService retries）をデフォルトで有効にしないことが推奨されるのはなぜですか？

A. retry により CPU overhead が大きくなりすぎる B. waypoint が切断された connection に request を転送して 503 を返した場合、retry によって server-side ですでに完了していた request が再実行され、重複実行（例: 注文の重複）が発生する可能性がある C. retry は STRICT mTLS と互換性がない D. retry は ambient モードでサポートされていない

<details>

<summary>回答 &#x26; 解説</summary>

**回答: B**

**解説:**

503 は client-visible failure ですが、その failure category には、request が実際には server に到達して処理を完了していたケースが含まれます。この場合、connection の切断と application の処理完了の race により、失われたのは _response_ のみです。この場合、mesh retry は別の connection を介して同じ logical request を再送し、server が idempotency を保証していなければ request は 2 回処理されます。このリスクは注文作成のような不可逆的な operation で特に深刻なため、retry をデフォルトで有効にせず、個別に検証する方が安全です。後続のテスト（T2）では、sidecar と ambient-L7 waypoint retry の両方に対して、継続的な rollout churn を 300s 実行したところ、その実行では重複実行がゼロでした。これは race が _common_ である可能性を低下させますが、安全であることを立証するものではありません。非常に狭い timing window が必要であり、より長時間またはより高 throughput のテストで発生する可能性があるためです。

**参照:**

* [Sidecar vs Ambient Mode Selection Guide: The Risk of Retry as a Mitigation](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

***

## スコアリング

* 4 問中何問正解したかを数えてください。
* 4/4: テスト結果の証拠に基づいて sidecar と ambient の判断を説明できます。
* 2-3/4: 核となる概念は理解していますが、NetworkPolicy と retry risk のセクションをもう一度確認してください。
* 0-1/4: 最初から [Sidecar vs Ambient Mode Selection Guide](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md) を読み直してください。

## 学習リソース

* [Sidecar vs Ambient Mode Selection Guide](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
* [Ambient Mode](../../../service-mesh/istio/advanced/01-ambient-mode.md)
* [mTLS](../../../service-mesh/istio/security/01-mtls.md)
