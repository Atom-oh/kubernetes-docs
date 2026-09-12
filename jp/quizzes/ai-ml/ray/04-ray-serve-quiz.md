# Ray Serve クイズ

## 多肢選択問題

1. Serve Deployment は Kubernetes Deployment とどのような関係にありますか？
   - A) 両者は同一です
   - B) Pod と一対一に対応するものではなく、論理的な actor-replica ユニットです
   - C) 各 replica には 1 つの EC2 node が必要です
   - D) Serve は actor を使用しません

<details>
<summary>回答を表示</summary>

**回答: B**

1 つの Ray Pod が複数の replica actor をホストできます。
</details>

2. 2.58.0 のデフォルトの proxy location は何ですか？
   - A) 常に head に 1 つです
   - B) replica をホストする node 上の EveryNode です
   - C) 無条件にすべての EC2 node です
   - D) 常に Disabled です

<details>
<summary>回答を表示</summary>

**回答: B**

HeadOnly と Disabled は明示的な選択肢です。古いアーキテクチャの説明と現在の API を区別してください。
</details>

3. デフォルトの deployment は num_replicas="auto" とどのように異なりますか？
   - A) どちらも直ちに 100 個の replica を開始します
   - B) デフォルトは固定の 1、auto は min 1/max 100/target 2 を適用します
   - C) デフォルトは GPU 1、auto は GPU 100 です
   - D) どちらも autoscaling をサポートしません

<details>
<summary>回答を表示</summary>

**回答: B**

直接作成した AutoscalingConfig の max のデフォルト値は 1 であるため、意図した上限を指定してください。
</details>

4. max_queued_requests のスコープは何ですか？
   - A) cluster 全体で 1 つの queue
   - B) proxy や handle など、各 caller
   - C) GPU KV-cache の容量
   - D) RayCluster Pod 数

<details>
<summary>回答を表示</summary>

**回答: B**

デフォルトの -1 は無制限です。設定された上限を超えると、HTTP request が拒否されたり、handle BackPressureError が発生したりする可能性があります。
</details>

5. 保留中の replica actor は常に新しい Pod と EC2 node を作成しますか？
   - A) 常に一対一です
   - B) いいえ。既存の capacity、group の上限、placement、および autoscaler の有効化が影響します
   - C) 自動的に CPU model になります
   - D) Serve が直接 EC2 node を作成します

<details>
<summary>回答を表示</summary>

**回答: B**

actor placement、Pod size、および node provisioning をそれぞれ個別に確認してください。
</details>

6. 2.58.0 の LLM backend について何が検証されましたか？
   - A) vLLM のみが存在します
   - B) vLLM と SGLang backend が存在します。依存関係と設定はそれぞれ個別に確認してください
   - C) すべての engine kwarg は engine 間で同一です
   - D) ray[serve] にはすべての LLM weight が含まれます

<details>
<summary>回答を表示</summary>

**回答: B**

inference の依存関係と model へのアクセス／download は別のものです。CPU check では LLM execution は検証されていません。
</details>

7. RayService の update に関する正確な記述はどれですか？
   - A) ダウンタイムなしが保証される、すべての EKS deployment で必須のものです
   - B) 任意の lifecycle path です。strategy、Gateway、capacity、readiness、draining を検証してください
   - C) 常に既存の Pod image のみを編集します
   - D) すべての長時間 stream は常に保持されます

<details>
<summary>回答を表示</summary>

**回答: B**

application の変更、cluster transition、および actor reconfiguration を区別してください。
</details>

8. ローカルの Echo test では何が検証されましたか？
   - A) GPU performance
   - B) LLM quality
   - C) HTTP 200 と DeploymentHandle call
   - D) multi-node autoscaling

<details>
<summary>回答を表示</summary>

**回答: C**

これは model、LLM、GPU、または cloud deployment を含まない、小規模な single-node CPU test でした。
</details>

## 短答式問題

9. max ongoing、autoscaling target、および caller queue limit を区別する理由は何ですか？

<details>
<summary>回答を表示</summary>

これらは異なるものを制御します。すなわち、replica に割り当てられる request、scaling のための target load、および caller ごとの待機中 request です。1 つの設定だけで、ほかのすべての上限や latency の保証が成立するわけではありません。
</details>

10. cluster token や ClusterIP だけでは application security が完結しない理由は何ですか？

<details>
<summary>回答を表示</summary>

TLS、各 entry point の authentication/authorization、model artifact の permission、機微な request/log の処理、および resource/queue/timeout policy をそれぞれ個別に検証してください。
</details>

---

[学習教材に戻る](../../../ai-ml/ray/04-ray-serve.md)
