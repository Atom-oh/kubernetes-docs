# CloudWatch Logs クイズ

Amazon CloudWatch Logs の理解度を確認しましょう。

---

1. EKS control plane logging でサポートされていないログタイプはどれですか？

   - A) api
   - B) audit
   - C) worker
   - D) scheduler

<details>
<summary>回答を表示</summary>

**回答: C) worker**

**解説:**
EKS control plane は api、audit、authenticator、controllerManager、scheduler の 5 種類のログタイプをサポートしています。Worker node のログは control plane ログではないため、Container Insights または FluentBit を通じて個別に収集する必要があります。

</details>

---

2. CloudWatch Logs の料金体系で最も高額な項目はどれですか？

   - A) ストレージ
   - B) 取り込み
   - C) クエリ (Logs Insights)
   - D) S3 Export

<details>
<summary>回答を表示</summary>

**回答: B) 取り込み**

**解説:**
CloudWatch Logs の取り込み料金は $0.50/GB で、ストレージ ($0.03/GB/月) やクエリ ($0.005/GB スキャン) よりも大幅に高額です。そのため、コスト最適化のためには不要なログをフィルタリングすることが重要です。

</details>

---

3. CloudWatch Logs Insights で特定のフィールドを抽出するコマンドは何ですか？

   - A) extract
   - B) parse
   - C) select
   - D) filter

<details>
<summary>回答を表示</summary>

**回答: B) parse**

**解説:**
CloudWatch Logs Insights では、`parse` コマンドでログメッセージから特定のパターンに一致するフィールドを抽出します。例: `parse @message '"level":"*"' as level`

</details>

---

4. Container Insights を通じて収集されるログの Log Group パス形式は何ですか？

   - A) `/aws/eks/cluster-name/logs`
   - B) `/aws/containerinsights/cluster-name/application`
   - C) `/var/log/containers/cluster-name`
   - D) `/kubernetes/cluster-name/logs`

<details>
<summary>回答を表示</summary>

**回答: B) `/aws/containerinsights/cluster-name/application`**

**解説:**
Container Insights は、application、host、dataplane、performance の Log Group を含む `/aws/containerinsights/{cluster-name}/` パスの下に Log Group を作成します。

</details>

---

5. リアルタイムログ処理のために Lambda 関数へログを配信する CloudWatch Logs の機能は何ですか？

   - A) Log Stream
   - B) Metric Filter
   - C) Subscription Filter
   - D) Log Insight

<details>
<summary>回答を表示</summary>

**回答: C) Subscription Filter**

**解説:**
Subscription Filter は、Log Group から他のサービス (Lambda、Kinesis Data Firehose、Kinesis Data Streams) にログをリアルタイムで配信します。フィルタパターンを指定して、特定のログだけを配信できます。

</details>

---

6. CloudWatch Logs にログを送信する FluentBit OUTPUT plugin の名前は何ですか？

   - A) cloudwatch
   - B) cloudwatch_logs
   - C) aws_cloudwatch
   - D) cw_logs

<details>
<summary>回答を表示</summary>

**回答: B) cloudwatch_logs**

**解説:**
FluentBit の CloudWatch Logs output plugin は `cloudwatch_logs` という名前です。AWS が提供する `aws-for-fluent-bit` イメージにデフォルトで含まれています。

</details>

---

7. CloudWatch Logs Insights で期間ごとにログ数を集計する正しいクエリはどれですか？

   - A) `stats count(*) group by hour`
   - B) `stats count(*) as log_count by bin(1h)`
   - C) `select count(*) from logs group by hour`
   - D) `aggregate count by time(1h)`

<details>
<summary>回答を表示</summary>

**回答: B) `stats count(*) as log_count by bin(1h)`**

**解説:**
CloudWatch Logs Insights では、時間ベースの集計に `stats` コマンドと `bin()` 関数を使用します。`bin(1h)` はデータを 1 時間間隔にグループ化します。

</details>

---

8. CloudWatch Logs のコスト最適化で推奨されない戦略はどれですか？

   - A) 不要なログのフィルタリング (healthcheck など)
   - B) 環境ごとに異なる保持期間を設定する
   - C) すべてのログを DEBUG レベルで収集する
   - D) 長期保持ログを S3 にアーカイブする

<details>
<summary>回答を表示</summary>

**回答: C) すべてのログを DEBUG レベルで収集する**

**解説:**
DEBUG レベルのログは非常に詳細であり、ログ量を大幅に増加させます。本番環境では、INFO レベル以上のみを収集するとコスト最適化に役立ちます。

</details>

---

9. CloudWatch Logs で Metric Filter を使用する主な目的は何ですか？

   - A) ログを S3 にエクスポートする
   - B) ログパターンから CloudWatch metrics を作成する
   - C) ログの保持期間を設定する
   - D) ログの暗号化を設定する

<details>
<summary>回答を表示</summary>

**回答: B) ログパターンから CloudWatch metrics を作成する**

**解説:**
Metric Filter は、ログ内の特定のパターン (例: ERROR) を検出し、CloudWatch metrics を作成します。これらの metrics に基づいて、通知を受け取るための CloudWatch Alarms を設定できます。

</details>

---

10. EKS cluster で Container Insights を設定する際、IRSA (IAM Roles for Service Accounts) に必要ではない権限はどれですか？

    - A) logs:CreateLogGroup
    - B) logs:PutLogEvents
    - C) s3:PutObject
    - D) cloudwatch:PutMetricData

<details>
<summary>回答を表示</summary>

**回答: C) s3:PutObject**

**解説:**
基本的な Container Insights の設定には S3 権限は必要ありません。必要なのは CloudWatch Logs (logs:*) と CloudWatch Metrics (cloudwatch:PutMetricData) の権限のみです。S3 権限が必要になるのは、S3 への個別のログエクスポートを設定する場合のみです。

</details>
