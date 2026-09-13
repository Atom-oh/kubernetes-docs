# CloudWatch Logs クイズ

> **最終更新**: September 13, 2026

[ガイド](../../../observability/logging/03-cloudwatch-logs.md)

---

1. EKS control-plane のログタイプではないものはどれですか？

   - A) api
   - B) audit
   - C) worker
   - D) scheduler

<details>
<summary>回答を表示</summary>

**回答: C**

5つのタイプは、api、audit、authenticator、controllerManager、scheduler です。Worker/application logs と Auto Mode managed-component delivery は別の経路です。

</details>

---

2. CloudWatch Logs のコスト要因はどのように比較すべきですか？

   - A) 取り込みは常に月額料金の中で最大である
   - B) ストレージは常に無料である
   - C) すべての S3 配信経路は無料である
   - D) 実際のボリューム、保持期間、スキャン、クラス、Region、下流の料金を比較する

<details>
<summary>回答を表示</summary>

**回答: D**

取り込み GB あたりの料金だけでは、GB-month ストレージや繰り返し発生するスキャンボリュームと比較して順位付けできません。ガイド内の $1,575 の例は仮定に基づく計算であり、現在の Seoul 料金や完全な請求額ではありません。

</details>

---

3. glob または正規表現を使用してフィールドを抽出する Logs Insights QL コマンドはどれですか？

   - A) extract
   - B) parse
   - C) select
   - D) filter

<details>
<summary>回答を表示</summary>

**回答: B**

parse はフィールドを抽出します。jsonParse は JSON メッセージを解析できます。collector envelope は application fields を log_processed 配下に配置します。glob では任意の JSON key の順序を想定しないでください。

</details>

---

4. このガイドの手動 application collector で使用されるグループはどれですか？

   - A) /aws/containerinsights/example-eks/application
   - B) /aws/eks/example-eks/logs
   - C) /var/log/containers/example-eks
   - D) すべての cluster は不変の共通グループ名を1つ使用する

<details>
<summary>回答を表示</summary>

**回答: A**

設定された application group は、control-plane logs 用の /aws/eks/example-eks/cluster とは異なります。グループは先に準備されます。collector はグループを作成せず、保持期間も変更しません。

</details>

---

5. subscription delivery について正しい記述はどれですか？

   - A) S3 bucket ARN は直接の subscription-filter destination である
   - B) CloudWatch subscription batches は Firehose の OpenSearch destination を通じて機能する
   - C) subscription は Lambda、Kinesis、または Firehose に送信できる。Firehose を経由した S3 archiving は別個の下流ステップである
   - D) subscription は exactly-once delivery を保証し、すべての履歴を backfill する

<details>
<summary>回答を表示</summary>

**回答: C**

destination API と input format は重要です。CloudWatch Logs→Firehose→OpenSearch は明確にサポートされていません。subscription は非同期かつ at least once です。export tasks と vended-log delivery は別の API です。

</details>

---

6. CloudWatch Logs 用のネイティブ C Fluent Bit output plugin はどれですか？

   - A) cloudwatch
   - B) cloudwatch_logs
   - C) aws_cloudwatch
   - D) cw_logs

<details>
<summary>回答を表示</summary>

**回答: B**

cloudwatch_logs はネイティブ plugin です。cloudwatch は旧式の Go plugin を指します。Credentials、実際の ServiceAccount、output group、IAM policy も一致している必要があります。

</details>

---

7. events を1時間ごとにカウントし、生成された time buckets をソートする QL query はどれですか？

   - A) stats count(*) group by hour
   - B) stats count(*) as log_count by bin(1h) as bucket | sort bucket asc
   - C) select count(*) from logs group by hour
   - D) stats count(*) by bin(1h) | sort @message

<details>
<summary>回答を表示</summary>

**回答: B**

stats は利用可能な output fields を変更するため、その bucket alias をソートします。latency percentile function は percentile ではなく pct であり、大文字・小文字を区別しない regex はスラッシュ内で (?i) を使用します。

</details>

---

8. デフォルトの cost-control approach として安全ではない logging policy はどれですか？

   - A) 保持が必要な records に対して filters を確認する
   - B) log group の単一の owner を通じて retention を設定する
   - C) すべての DEBUG output を無期限に保持し、その代償として security-relevant records を無差別に破棄する
   - D) 設計を変更する前に ingestion と scans を測定する

<details>
<summary>回答を表示</summary>

**回答: C**

volume controls は必要な diagnostics と security records を保持しなければなりません。ConfigMap の LOG_LEVEL は application がそれを使用する場合にのみ効果があります。retention の変更によりデータが削除されることがあります。

</details>

---

9. metric filter の機能、および zero default の意味は何ですか？

   - A) すべての履歴 records を S3 にエクスポートする
   - B) 新たに一致した logs から metrics を導出する。default zero は logs が到着したものの一致する records がない場合に適用される
   - C) logs が到着しない場合でも常に zero を出力する
   - D) すべての log class のすべての機能をサポートする

<details>
<summary>回答を表示</summary>

**回答: B**

この章では、$.log_processed.level に対する Standard-class JSON filter を使用します。incoming logs がない場合、データが欠損することがあります。alarm は error rate や Service health の証明ではなく、2つの5分間の期間における error count を確認します。

</details>

---

10. 手動 logs-only collector に適した IAM/ownership arrangement はどれですか？

   - A) すべての Pods に administrator role を付与する
   - B) 無関係な ServiceAccount をデプロイしながら cloudwatch-agent に policy をアタッチする
   - C) s3:PutObject のみを使用する
   - D) group を事前作成し、その ARN に対して logs:CreateLogStream/logs:PutLogEvents を許可し、実際の collector ServiceAccount をマッピングする

<details>
<summary>回答を表示</summary>

**回答: D**

手動 profile では logging/fluent-bit-cloudwatch と承認済みの IRSA trust を使用します。この経路では PutMetricData や広範な logs:* は不要です。full observability chart は別の profile であり、その Fluent Bit Pods は cloudwatch-agent を使用します。

</details>
