# イベント Capacity Planning Playbook クイズ

1. KEDA ScaledObject に複数の trigger（Cron + Prometheus + SQS）が設定されている場合、最終的な replica 数はどのように決定されますか？
   - A) すべての trigger 値の平均
   - B) 最も低い値（MIN）
   - C) 最も高い値（MAX）
   - D) 最初の trigger の値

<details>
<summary>答えを表示</summary>

**回答: C) 最も高い値（MAX）**

**解説:**
複数の trigger が設定されている場合、KEDA はすべての trigger の中から最も高い希望 replica 数を選択します。これにより、「cron が下限を設定し、metrics が上限を決定する」パターンが可能になります。たとえば、cron が 100 を要求し、Prometheus が 150 を要求した場合、結果は 150 になります。

</details>

---

2. Pause Pod パターンでは、実際の workload が到着したときに Pause Pod が evict される原因となる仕組みは何ですか？
   - A) resource request が小さいため、Pod が自動的に置き換えられる
   - B) 低い PriorityClass 値が Preemption をトリガーする
   - C) DaemonSet が Pod を自動的に再分散する
   - D) TTL の期限切れにより自動削除される

<details>
<summary>答えを表示</summary>

**回答: B) 低い PriorityClass 値が Preemption をトリガーする**

**解説:**
Pause Pod には value: -10 の PriorityClass が割り当てられます。実際の workload（default priority 0 以上）を schedule する必要があり、十分な capacity がない場合、Kubernetes Scheduler は低 priority の Pod を preempt して空き領域を確保します。これにより、実際の workload をすでに provision された Node 上に即座に schedule できます。

</details>

---

3. なぜ KEDA cron trigger は flash sale 開始の 30 分前に発火するよう設定されているのですか？
   - A) KEDA の polling interval が 30 分だから
   - B) Cron trigger は正確な時刻に発火しないから
   - C) Node provisioning と Pod scheduling にはリードタイムが必要だから
   - D) AWS API throttling を避けるため

<details>
<summary>答えを表示</summary>

**回答: C) Node provisioning と Pod scheduling にはリードタイムが必要だから**

**解説:**
KEDA が Pod を scale up すると、Karpenter が新しい Node を provision するのに 60〜90 秒かかり、さらに Pod scheduling と container 起動の時間が必要です。30 分早く scale-up を開始することで、最初の traffic surge が到達する前にすべての Pod が Ready state になることを保証します。

</details>

---

4. なぜ EC2 Capacity Reservation で `instance_match_criteria = "targeted"` を設定するのですか？
   - A) コストを削減するため
   - B) reservation を使用できる対象を特定の Karpenter NodePool のみに制限するため
   - C) Spot instance での使用を有効にするため
   - D) multi-AZ deployment のため

<details>
<summary>答えを表示</summary>

**回答: B) reservation を使用できる対象を特定の Karpenter NodePool のみに制限するため**

**解説:**
`targeted` 設定により、Capacity Reservation を明示的に参照する instance のみがそれを使用できます。これにより、event 専用の Karpenter NodePool（capacityReservationSelectorTerms によって matching される）向けに確保された reserved capacity を、一般的な workload が消費することを防ぎます。

</details>

---

5. Karpenter NodePool で高い `weight` 値を設定すると、どのような効果がありますか？
   - A) Node がより速く provision される
   - B) その NodePool が他の NodePool より優先される
   - C) より多くの Node を provision できる
   - D) 低コストの instance が選択される

<details>
<summary>答えを表示</summary>

**回答: B) その NodePool が他の NodePool より優先される**

**解説:**
複数の NodePool が Pending Pod の要件を満たせる場合、Karpenter は最も高い weight を持つ NodePool を選択します。event NodePool に weight: 100 を設定すると、default NodePool（例: weight: 10）より先に使用され、event 専用の設定（instance types、capacity types など）が適用されます。

</details>

---

6. HPA scaleDown behavior において、`type: Percent, value: 10, periodSeconds: 120` は何を意味しますか？
   - A) 120 秒以内に合計の 10% まで scale down する
   - B) 120 秒ごとに現在の Pod の 10% ずつ削減する
   - C) 10 秒ごとに 120 Pod を削除する
   - D) 最小 10 Pod を維持し、120 秒後にすべて削除する

<details>
<summary>答えを表示</summary>

**回答: B) 120 秒ごとに現在の Pod の 10% ずつ削減する**

**解説:**
この policy は、現在の replica 数の最大 10% を 120 秒（2 分）ごとに削減することを許可します。200 Pod の場合、これは 2 分ごとに最大 20 Pod を削除することを意味し、急激な scale-down による service の不安定化を防ぎます。

</details>

---

7. capacity planning worksheet が 30% の safety margin を追加するのはなぜですか？
   - A) AWS instance の価格変動を考慮するため
   - B) 予測誤差、Pod 起動時間、不均等な load distribution をカバーするため
   - C) Kubernetes system Pod の resource usage を考慮するため
   - D) network bandwidth の制限があるため

<details>
<summary>答えを表示</summary>

**回答: B) 予測誤差、Pod 起動時間、不均等な load distribution をカバーするため**

**解説:**
30% の safety margin は複数の不確実性を吸収します: (1) traffic prediction が不正確な可能性がある、(2) Pod がすべて同時に ready になるわけではない、(3) load が Pod 間で完全に均等に分散されるわけではない、(4) 一部の Node/Pod が fail する可能性がある。margin は過去の event の post-mortem data に基づいて調整できます。

</details>

---

8. image pre-caching DaemonSet が initContainers を使用するのはなぜですか？
   - A) resource を節約するために image を実行して終了するため
   - B) Node cache に image を download（pull）して終了し、cache だけを残すため
   - C) image version を検証するため
   - D) Container Registry で認証するため

<details>
<summary>答えを表示</summary>

**回答: B) Node cache に image を download（pull）して終了し、cache だけを残すため**

**解説:**
DaemonSet initContainers はすべての Node 上で実行され、container image を pull します。それらは `echo cached` だけを実行して終了しますが、image は Node の local cache に残ります。後で実際の workload Pod が schedule されると、image pull phase（数十秒から数分かかる場合があります）を skip できるため、Pod startup time が大幅に短縮されます。

</details>

---

9. D-30 timeline で target RPM の 120% で load testing を行うのはなぜですか？
   - A) 高 traffic について AWS から事前承認を得るため
   - B) target traffic を超える system stability を検証し、bottleneck を早期に発見するため
   - C) KEDA trigger threshold を正確に計算するため
   - D) cost estimation の精度を向上させるため

<details>
<summary>答えを表示</summary>

**回答: B) target traffic を超える system stability を検証し、bottleneck を早期に発見するため**

**解説:**
実際の event traffic は予測を上回る可能性があるため、120% で testing することで、(1) target を上回る system stability を確認し、(2) DB connections、network bandwidth、API gateways などの bottleneck を発見し、(3) 実際の scaling chain（KEDA → HPA → Karpenter）の挙動を本番 event 前に検証できます。

</details>

---

10. event で Spot の代わりに On-Demand instance を使用することが最も正当化される状況はどれですか？
    - A) event duration が 4 時間を超える
    - B) Spot savings が 60% を超える
    - C) interruption が許容されない revenue-critical service
    - D) workload に retry logic が実装されている

<details>
<summary>答えを表示</summary>

**回答: C) interruption が許容されない revenue-critical service**

**解説:**
Spot instance は AWS によって 2 分前の通知で reclaimed される可能性があります。flash sale 中の order processing のような revenue-critical service は、availability を保証するために On-Demand を使用するべきです。email notification や log processing のような auxiliary service は、retry logic があれば Spot を使用でき、resilience を維持しながら cost を削減できます。

</details>
