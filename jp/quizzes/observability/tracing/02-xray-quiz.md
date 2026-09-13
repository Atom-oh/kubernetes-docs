# AWS X-Ray クイズ

> **最終更新**: September 13, 2026

[AWS X-Ray](../../../observability/tracing/02-xray.md)

---

1. X-Ray trace pipeline で自動的に提供されない動作はどれですか？
   - A) 収集した trace に基づく Service 依存関係の可視化
   - B) 分散リクエストトレーシング
   - C) すべてのアプリケーションの通常ログファイルの収集
   - D) 収集した span タイミングの分析

<details>
<summary>回答を表示</summary>

**回答: C) すべてのアプリケーションの通常ログファイルの収集**

**解説:**

Tracing は、汎用的なアプリケーションログコレクターを設定しません。CloudWatch Transaction Search は構造化 span を aws/spans に保存できますが、これは通常のアプリケーションログをすべて収集することとは異なります。Metrics/logs には、それぞれ独自に設定した pipeline とアクセス制御が必要です。

</details>

---

2. レガシー daemon パスでは、各適格な EC2 worker 上で daemon を実行できる Kubernetes workload はどれですか？
   - A) Deployment
   - B) StatefulSet
   - C) DaemonSet
   - D) Job

<details>
<summary>回答を表示</summary>

**回答: C) DaemonSet**

**解説:**

DaemonSet は適格な node を選択します。EKS Fargate ではサポートされません。ClusterIP Service は別の node 上の daemon を選択する可能性があるため、DaemonSet の配置だけでは node-local または損失のない UDP 配信を保証しません。X-Ray SDK/daemon はメンテナンスモードです。このガイドでは、新しい instrumentation に対して別の OpenTelemetry collector Deployment を使用します。

</details>

---

3. X-Ray の集中型 sampling rule のフィールドではないものはどれですか？
   - A) FixedRate
   - B) ReservoirSize
   - C) Priority
   - D) RetentionDays

<details>
<summary>回答を表示</summary>

**回答: D) RetentionDays**

**解説:**

FixedRate、ReservoirSize、Priority は sampling フィールドです。RetentionDays は sampling-rule parameter ではありません。トラフィックがない場合、reservoir は trace の最小数を保証するものではありません。rule には互換性のある remote sampler が必要です。head sampling は、まだ発生していない response error を選択できません。

</details>

---

4. X-Ray annotations と metadata を正しく区別している記述はどれですか？
   - A) すべての segment はそれぞれ 100 個のインデックス付き annotation を受け取る
   - B) annotations は X-Ray のフィルタリング用にインデックス化され、インデックス化されない metadata は保存されアクセス可能なままである
   - C) annotations が受け付けるのは文字列のみである
   - D) metadata は自動的にマスキングされる

<details>
<summary>回答を表示</summary>

**回答: B) annotations は X-Ray のフィルタリング用にインデックス化され、インデックス化されない metadata は保存されアクセス可能なままである**

**解説:**

X-Ray は trace ごとに最大50個の annotation をインデックス化します。Metadata は annotation としてインデックス化されませんが、インデックス化されないことは秘密であることやアクセス不能であることを意味しません。収集前に、意図的に制限したフィールドを使用し、機密 payload、identifier、token、SQL parameter を削除してください。index_all_attributes=false は redaction processor ではありません。

</details>

---

5. ADOT Collector について誤っている記述はどれですか？
   - A) サポートされている OpenTelemetry protocol を受け入れる
   - B) サポートされている pipeline を複数の backend に接続できる
   - C) 使用されていない CloudWatch Logs exporter を宣言すると、trace は自動的に logs に変換される
   - D) リリースされた component inventory を確認する必要がある

<details>
<summary>回答を表示</summary>

**回答: C) 使用されていない CloudWatch Logs exporter を宣言すると、trace は自動的に logs に変換される**

**解説:**

receiver、processor、exporter は、適切な logs/metrics/traces pipeline に接続する必要があります。ADOT には awsxray などの AWS integration が含まれるため、AWS 固有の動作はレガシー daemon 専用ではありません。選択した ADOT リリースに、upstream Contrib のすべての exporter が存在すると想定しないでください。

</details>

---

6. X-Ray/CloudWatch trace map の赤いトラフィックカテゴリは何を表しますか？
   - A) すべての低速なリクエスト
   - B) 高トラフィック量
   - C) HTTP5xx などの server fault
   - D) 新たに検出された Service

<details>
<summary>回答を表示</summary>

**回答: C) HTTP5xx などの server fault**

**解説:**

赤は server fault、黄は client error、紫は HTTP429 などの throttling、緑は正常なトラフィックを表します。これらのカテゴリは任意の latency threshold ではなく、また、すべての赤い Service がユーザー定義の高エラー率アラームのしきい値を超えたことを示すものでもありません。

</details>

---

7. ガイドの X-Ray collection パスを通じて OpenTelemetry span を送信するために必要なものは何ですか？
   - A) すべての producer がレガシー X-Ray SDK を使用すること
   - B) 正しい AWS identity を持つ、互換性があり認証された OTLP collector/export pipeline
   - C) すべてのアプリケーションが CloudWatch Agent をインストールすること
   - D) すべての EKS Pod が Lambda Layer をインストールすること

<details>
<summary>回答を表示</summary>

**回答: B) 正しい AWS identity を持つ、互換性があり認証された OTLP collector/export pipeline**

**解説:**

このガイドでは、mTLS を使用して OTLP を ADOT に送信し、その awsxray exporter が署名付きの classic X-Ray API を呼び出します。X-Ray は W3C128-bit ID をサポートします。特別な X-Ray ID generator/propagator が常に必須というわけではありません。代替のネイティブ OTLP HTTPS endpoint には SigV4 と Transaction Search が必要です。実際の integration に合わせて propagation を設定してください。

</details>

---

8. 2 秒より厳密に大きい値を選択する X-Ray response-time filter はどれですか？
   - A) `responsetime > 2000`
   - B) `responsetime > 2`
   - C) `responsetime >= 2`
   - D) `time > 2s`

<details>
<summary>回答を表示</summary>

**回答: B) `responsetime > 2`**

**解説:**

Response-time の値は秒単位です。>2 はちょうど2秒を除外し、>=2 はそれを含みます。これらは X-Ray filter expression であり、shell command や Logs Insights QL ではありません。duration も文書化された X-Ray keyword であり、架空の無効な keyword として提示してはなりません。

</details>

---

9. CloudWatch trace map を開くだけでは、何を確立できませんか？
   - A) すでに収集された trace 依存関係のビュー
   - B) 設定済み metrics/alarms との相関
   - C) すべてのアプリケーションの自動 instrumentation と収集の成功
   - D) 適切に相関付けられた logs へのリンク

<details>
<summary>回答を表示</summary>

**回答: C) すべてのアプリケーションの自動 instrumentation と収集の成功**

**解説:**

Instrumentation、collection、identity、correlation は個別に設定する必要があります。以前の ServiceLens と X-Ray map は CloudWatch trace map に統合されています。既存の telemetry はそこで相関付けられますが、mount されていない ConfigMap や空のビューは、agent とアプリケーションが設定されている証拠にはなりません。

</details>

---

10. X-Ray Groups の目的は何ですか？
   - A) IAM authorization を置き換えること
   - B) 分析および関連する metrics/alarms のために一致する trace をグループ化すること
   - C) AWS billing の所有者を自動的に割り当てること
   - D) sampling rule を通じて retention を設定すること

<details>
<summary>回答を表示</summary>

**回答: B) 分析および関連する metrics/alarms のために一致する trace をグループ化すること**

**解説:**

Groups は filter expression を使用して trace を選択します。結果の metrics を確認し、CloudWatch alarms を別途設定してください。group を作成しても、producer を instrument したり、sampling を上書きしたり、IAM isolation を定義したり、end-to-end alert が発生したことを証明したりはしません。

</details>

---
