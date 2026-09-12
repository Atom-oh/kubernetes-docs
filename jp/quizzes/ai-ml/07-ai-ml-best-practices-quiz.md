# AI/ML ベストプラクティスクイズ

測定、リカバリ、現行 API に関する15問。

## 1. TTFT は何を測定し、いつ利用できませんか？

<details>
<summary>回答と解説</summary>

リクエストから最初の空でない出力までの時間です。最初の HTTP フレームとトークンは異なる場合があります。非ストリーミング応答では実際の TTFT/ITL を測定できません。tokenizer、失敗、および warmup の境界を明示してください。
</details>

## 2. startup optimization を組み合わせると、常に 80～95% 改善しますか？

<details>
<summary>回答と解説</summary>

いいえ。image fetch/unpack、model download/loading、readiness、および node preparation を個別に測定してください。固定の削減率ではなく、prefetch/lazy-loading のコスト、cache、および full-weight read を評価してください。
</details>

## 3. 大規模な分散 training 用の GPU はどのように選択すべきですか？

<details>
<summary>回答と解説</summary>

正確な instance-size の device/memory、CPU/RAM/network、model state/activation、communication、価格、および quota を確認してください。family 名だけでは GPU 数は決まらず、普遍的に最適な選択を証明するものでもありません。
</details>

## 4. EFA と placement group は常に必要ですか？

<details>
<summary>回答と解説</summary>

EFA は適した workload 向けの high-performance path であり、すべての DDP の前提条件ではありません。EFA communication には同じ AZ が必要です。cluster placement group はパフォーマンスのために推奨されます。driver/plugin/security group/interface を確認してください。
</details>

## 5. 10TB を超える dataset には常に FSx が必要ですか？

<details>
<summary>回答と解説</summary>

単一のサイズ閾値では決まりません。I/O、concurrency、metadata、latency、durability、mount semantics、および cost を比較してください。EFS/FSx/S3/instance store と現行の gp3 制限を区別してください。
</details>

## 6. temperature だけで throttling または hardware failure を判断できますか？

<details>
<summary>回答と解説</summary>

いいえ。device 固有の制限、clock、power、throttle reason、および workload を確認してください。DCGMFB_USED は MiB であり、XID_ERRORS は最後の code を示す gauge です。すべての XID が hardware failure を意味するわけではありません。
</details>

## 7. Spot inference には 120 秒の grace と a/drain call で十分ですか？

<details>
<summary>回答と解説</summary>

EC2 は常に 120 秒を保証するわけではなく、任意の vLLM/drain API を想定することもできません。gateway readiness、SIGTERM、stream、retry、duplicate、および cache reload をテストしてください。
</details>

## 8. 平均 ITL はどのように計算しますか？

<details>
<summary>回答と解説</summary>

実際の token timestamp と少なくとも2つの token を使用して、(last-first)/(tokens-1) と計算します。multi-token chunk と空または single-token の出力を考慮し、tool 固有の TPOT 定義を区別してください。
</details>

## 9. saturation test は何を示しますか？

<details>
<summary>回答と解説</summary>

load に応じて throughput、latency、error、および goodput がどのように変化するかを示します。それだけでは CPU/GPU/memory の bottleneck を証明できません。arrival rate と concurrency を区別し、client、profiling、および queue を調査してください。
</details>

## 10. SOCI 0.15 standalone はどの input を使用しますか？

<details>
<summary>回答と解説</summary>

汎用の docker-save tar ではなく、ローカルの OCI image-layout directory/archive を使用します。convert --standalone には containerd は不要です。実際の lazy-start の利点には runtime/registry/workload の検証が必要です。
</details>

## 11. 09～17 UTC の business-hour budget はどのように設定しますか？

<details>
<summary>回答と解説</summary>

8h の duration で 0 9 * * 1-5 を使用します。0 9-17 * * 1-5 は毎時開始され、翌日の01:00まで延長されます。budget は自発的な disruption を制限しますが、Spot reclamation、failure、または強制的な expiration は制限しません。
</details>

## 12. ESO refresh は自動的に credential を発行し、app を reload し、すべての read を audit しますか？

<details>
<summary>回答と解説</summary>

いいえ。provider rotation、Secret synchronization、および app reread を区別してください。subPath/env の値は自動で refresh されず、CloudTrail はすべての local read を記録しません。ESO 2.10 は v1 を提供し、v1beta1 ではありません。
</details>

## 13. 30B FP16 model の GPU memory はどのように見積もるべきですか？

<details>
<summary>回答と解説</summary>

weight だけで約60GBです。KV、activation、workspace、および communication を加算してください。4基の 24GB GPU は合計96GBですが、sharding/peak-memory/throughput の確認が必要です。13B FP16 は 24GB を超え、70B FP16 は 96GB を超えます。
</details>

## 14. 現在の vLLM KV-cache occupancy が高い場合、常に request を reject しますか？

<details>
<summary>回答と解説</summary>

vllm:kv_cache_usage_perc を使用します。occupancy を queue、preemption、および memory state と併せて解釈してください。即時の rejection は保証されません。古い gpu_cache_usage_perc や未検証の hit-rate 名は避けてください。
</details>

## 15. Karpenter の placement group は tag を通じて設定しますか？

<details>
<summary>回答と解説</summary>

Version 1.14.1 は EC2NodeClass.spec.placementGroupSelector name/id を使用します。aws:ec2:placement-group tag は placement API ではありません。AZ、capacity、および networking を確認し、single-AZ recovery のリスクを評価してください。
</details>

[ガイドに戻る](../../ai-ml/07-ai-ml-best-practices.md)
