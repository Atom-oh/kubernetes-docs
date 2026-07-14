# CloudWatch Alarms クイズ

CloudWatch Alarms の理解度を確認するためのクイズです。

---

1. CloudWatch Alarm の3つの状態は何ですか？
   - A) Active、Inactive、Pending
   - B) OK、ALARM、INSUFFICIENT_DATA
   - C) Normal、Warning、Critical
   - D) Green、Yellow、Red

<details>
<summary>回答を表示</summary>

**回答: B) OK、ALARM、INSUFFICIENT_DATA**

**解説:**
CloudWatch Alarms には3つの状態があります。
- **OK**: Metric が正常範囲内にある
- **ALARM**: Metric が定義されたしきい値に違反している
- **INSUFFICIENT_DATA**: Alarm を評価するためのデータが不足している

これらの状態は、Metric の値と Alarm の設定に基づいて自動的に遷移します。

</details>

---

2. CloudWatch Alarms の `evaluation-periods` 設定と `datapoints-to-alarm` 設定の違いは何ですか？
   - A) 両方の設定は同じ機能を実行する
   - B) evaluation-periods は評価期間の数、datapoints-to-alarm は ALARM 状態をトリガーするために必要なデータポイント数である
   - C) evaluation-periods は秒単位、datapoints-to-alarm は分単位である
   - D) evaluation-periods は Metric の収集間隔、datapoints-to-alarm は通知間隔である

<details>
<summary>回答を表示</summary>

**回答: B) evaluation-periods は評価期間の数、datapoints-to-alarm は ALARM 状態をトリガーするために必要なデータポイント数である**

**解説:**
- `evaluation-periods`: Alarm の評価に使用する期間の数（例: 3）
- `datapoints-to-alarm`: ALARM 状態へ遷移するためにしきい値に違反する必要があるデータポイント数（例: 2）

たとえば、evaluation-periods=3 かつ datapoints-to-alarm=2 の場合、「3つの期間のうち2つ以上でしきい値に違反した場合に ALARM」となります。これは「M of N」Alarm と呼ばれます。

</details>

---

3. CloudWatch Metric Math で ALB のエラー率を計算する正しい式はどれですか？
   - A) `errors + requests`
   - B) `(errors / requests) * 100`
   - C) `errors - requests`
   - D) `RATE(errors)`

<details>
<summary>回答を表示</summary>

**回答: B) `(errors / requests) * 100`**

**解説:**
エラー率は、エラー数をリクエストの総数で割り、100を掛けてパーセンテージを求めることで計算されます。CloudWatch Metric Math では、このような計算のために複数の Metric を組み合わせることができ、結果を Alarm 条件として使用できます。

```
errors = HTTPCode_Target_5XX_Count
requests = RequestCount
error_rate = (errors / requests) * 100
```

</details>

---

4. Composite Alarms に関する記述として正しくないものはどれですか？
   - A) 複数の Metric Alarms を組み合わせて複雑な条件を定義できる
   - B) AND、OR、NOT 論理演算子を使用できる
   - C) Composite Alarm 内に別の Composite Alarms を含めることができる
   - D) Composite Alarms は独自の Metric を定義できる

<details>
<summary>回答を表示</summary>

**回答: D) Composite Alarms は独自の Metric を定義できる**

**解説:**
Composite Alarms は独自の Metric を定義しません。代わりに、既存の Metric Alarms の状態を組み合わせて複雑な Alarm 条件を作成します。Composite Alarm ルールは、`ALARM(alarm-name)`、`OK(alarm-name)`、および AND、OR、NOT 演算子などの関数で構成されます。Composite Alarms は、他の Composite Alarms 内にネストすることもできます。

</details>

---

5. CloudWatch Anomaly Detection の動作を正しく説明しているものはどれですか？
   - A) 固定しきい値に基づいて異常を検出する
   - B) 機械学習を使用して想定される Metric 範囲を学習し、それを超えた場合にアラートする
   - C) 他の Metric との相関関係を分析して異常を検出する
   - D) パターンがユーザー定義のパターンと一致しない場合にアラートする

<details>
<summary>回答を表示</summary>

**回答: B) 機械学習を使用して想定される Metric 範囲を学習し、それを超えた場合にアラートする**

**解説:**
CloudWatch Anomaly Detection は、機械学習アルゴリズムを使用して履歴 Metric データを分析し、時間帯や曜日による変動などのパターンを学習します。これに基づいて想定範囲を生成し、実際の Metric 値がこの範囲外になった場合に異常として検出されます。`ANOMALY_DETECTION_BAND(metric, stddev)` 関数を使用して、標準偏差の乗数を調整できます。

</details>

---

6. CloudWatch Alarms の `treat-missing-data` における `notBreaching` オプションは何を意味しますか？
   - A) データが欠落している場合に Alarm をトリガーする
   - B) データが欠落している場合に以前の状態を維持する
   - C) 欠落データをしきい値に違反していないものとして扱う
   - D) データが欠落している場合に INSUFFICIENT_DATA 状態へ遷移する

<details>
<summary>回答を表示</summary>

**回答: C) 欠落データをしきい値に違反していないものとして扱う**

**解説:**
`treat-missing-data` オプション値の意味:
- `notBreaching`: 欠落データをしきい値に違反していないものとして扱う（OK とみなす）
- `breaching`: 欠落データをしきい値に違反しているものとして扱う（ALARM とみなす）
- `ignore`: 現在の状態を維持する
- `missing`: INSUFFICIENT_DATA 状態へ遷移する

一般的に、データ欠落による不要なアラートを防ぐために `notBreaching` が推奨されます。

</details>

---

7. CloudWatch Alarm Action として直接実行できないアクションはどれですか？
   - A) EC2 インスタンスの停止/開始/再起動
   - B) Auto Scaling ポリシーのトリガー
   - C) SNS トピックへのメッセージ送信
   - D) EKS Pod の再起動

<details>
<summary>回答を表示</summary>

**回答: D) EKS Pod の再起動**

**解説:**
CloudWatch Alarm Actions では、以下の AWS ネイティブ操作を直接実行できます。
- EC2 Actions: 停止、開始、再起動、復旧、終了
- Auto Scaling Actions: スケールアウト/インポリシーのトリガー
- SNS Actions: トピックへのメッセージ送信

EKS Pod の再起動は直接サポートされておらず、SNS -> Lambda -> Kubernetes API チェーンを通じて間接的に実装する必要があります。

</details>

---

8. Container Insights で EKS cluster 内の Pod 再起動回数を監視するための Metric はどれですか？
   - A) pod_restart_count
   - B) pod_number_of_container_restarts
   - C) container_restart_total
   - D) kube_pod_container_status_restarts

<details>
<summary>回答を表示</summary>

**回答: B) pod_number_of_container_restarts**

**解説:**
Container Insights の主要な EKS Metrics:
- `pod_number_of_container_restarts`: Pod 内の Container 再起動回数
- `pod_cpu_utilization`: Pod CPU 使用率
- `pod_memory_utilization`: Pod メモリ使用率
- `node_cpu_utilization`: Node CPU 使用率
- `cluster_node_count`: cluster の Node 数

これらの Metrics は `ContainerInsights` namespace で利用できます。

</details>

---

9. CloudWatch Alarms のコスト最適化に推奨されない方法はどれですか？
   - A) 重要度が低いアラートには Standard Resolution（60秒）を使用する
   - B) 複数の Metric Alarms を Composite Alarms に統合する
   - C) すべてのアラートに High Resolution（10秒）を使用する
   - D) 未使用の Alarm を定期的に削除する

<details>
<summary>回答を表示</summary>

**回答: C) すべてのアラートに High Resolution（10秒）を使用する**

**解説:**
High Resolution Alarm は Standard Resolution より3倍高額です（$0.30 対 $0.10/Alarm/月）。コスト最適化のために:
- High Resolution は Critical アラートにのみ使用する
- Warning/Info アラートには Standard Resolution を使用する
- 関連する Alarm を Composite Alarms に統合する
- 未使用の Alarm を定期的に削除する
- Anomaly Detection は必要な場合にのみ使用する（追加コストは $0.30/Metric/月）

</details>

---

10. 自動対応のために EventBridge を CloudWatch Alarms と統合する場合、Alarm 状態の変更を検出する `detail-type` は何ですか？
    - A) "AWS CloudWatch Alarm"
    - B) "CloudWatch Alarm State Change"
    - C) "CloudWatch Metric Alarm"
    - D) "AWS Alarm Notification"

<details>
<summary>回答を表示</summary>

**回答: B) "CloudWatch Alarm State Change"**

**解説:**
EventBridge で CloudWatch Alarm の状態変更を検出するためのイベントパターン:
```json
{
  "source": ["aws.cloudwatch"],
  "detail-type": ["CloudWatch Alarm State Change"],
  "detail": {
    "state": {
      "value": ["ALARM"]
    }
  }
}
```

このパターンを使用すると、Alarm 状態が ALARM に変わったときに Lambda 関数、Step Functions、SSM Automation などをトリガーして、自動対応を実装できます。

</details>

---

## 追加学習リソース

- [Amazon CloudWatch Alarms Documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- [CloudWatch Metrics Math](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/using-metric-math.html)
- [CloudWatch Anomaly Detection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html)
- [Container Insights Metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html)
