# CloudWatch Alarms クイズ

従来の CloudWatch メトリクスアラームとコンポジットアラームに関するクイズです。2026-09-13 時点の公式ドキュメントに照らして確認済みです。

---

1. 従来の CloudWatch メトリクスアラームの 3 つの状態は何ですか？
   - A) Active, Inactive, Pending
   - B) OK, ALARM, INSUFFICIENT_DATA
   - C) Normal, Warning, Critical
   - D) Green, Yellow, Red

<details>
<summary>回答を表示</summary>

**回答: B) OK, ALARM, INSUFFICIENT_DATA**

**解説:**
CloudWatch Alarms には 3 つの状態があります。
- **OK**: メトリクスが正常範囲内にある
- **ALARM**: メトリクスが定義されたしきい値に違反した
- **INSUFFICIENT_DATA**: アラームを評価するのに十分なデータがない

これらの状態は、メトリクス値とアラーム設定に基づいて自動的に遷移します。

</details>

---

2. CloudWatch Alarms の `evaluation-periods` 設定と `datapoints-to-alarm` 設定の違いは何ですか？
   - A) 両方の設定は同じ機能を実行する
   - B) evaluation-periods は評価期間の数、datapoints-to-alarm は ALARM 状態をトリガーするために必要なデータポイント数である
   - C) evaluation-periods は秒単位、datapoints-to-alarm は分単位である
   - D) evaluation-periods はメトリクス収集間隔、datapoints-to-alarm は通知間隔である

<details>
<summary>回答を表示</summary>

**回答: B) evaluation-periods は評価期間の数、datapoints-to-alarm は ALARM 状態をトリガーするために必要なデータポイント数である**

**解説:**
- `evaluation-periods`: アラームの評価に使用する期間数（例: 3）
- `datapoints-to-alarm`: ALARM 状態に遷移するために、しきい値に違反する必要があるデータポイント数（例: 2）

たとえば、evaluation-periods=3 および datapoints-to-alarm=2 の場合、「3 期間のうち 2 期間以上でしきい値に違反したら ALARM」という意味です。これは「M of N」アラームと呼ばれます。

</details>

---

3. CloudWatch Metric Math で、リクエスト数が正の場合の ALB ターゲットエラー率の基本的な比率は何ですか？
   - A) `errors + requests`
   - B) `(errors / requests) * 100`
   - C) `errors - requests`
   - D) `RATE(errors)`

<details>
<summary>回答を表示</summary>

**回答: B) `(errors / requests) * 100`**

**解説:**
エラー率は、エラー数をリクエスト総数で割り、100 を掛けてパーセンテージとして算出します。分母はすべての ALB 生成の失敗ではなく、ターゲットに転送されたリクエストを数えます。リクエスト数がゼロの場合、5xx が欠落している場合、収集データが欠落している場合の扱いは別途定義してください。

```
errors = HTTPCode_Target_5XX_Count
requests = RequestCount
error_rate = (errors / requests) * 100
```

</details>

---

4. コンポジットアラームに関する記述で、正しくないものはどれですか？
   - A) 複数のメトリクスアラームを組み合わせて複雑な条件を定義できる
   - B) AND、OR、NOT の論理演算子を使用できる
   - C) コンポジットアラーム内に別のコンポジットアラームを含めることができる
   - D) コンポジットアラームは独自のメトリクスを定義できる

<details>
<summary>回答を表示</summary>

**回答: D) コンポジットアラームは独自のメトリクスを定義できる**

**解説:**
コンポジットアラームは独自のメトリクスを定義しません。代わりに、既存のメトリクスアラームの状態を組み合わせて、複雑なアラーム条件を作成します。コンポジットアラームのルールは、`ALARM(alarm-name)`、`OK(alarm-name)` のような関数と、AND、OR、NOT 演算子で構成されます。コンポジットアラームは、他のコンポジットアラーム内にネストすることもできます。

</details>

---

5. CloudWatch Anomaly Detection の動作を正しく説明している記述はどれですか？
   - A) 固定しきい値に基づいて異常を検出する
   - B) 機械学習を使用して予想されるメトリクス範囲を学習し、それを超えた場合にアラートを出す
   - C) 他のメトリクスとの相関関係を分析して異常を検出する
   - D) パターンがユーザー定義のパターンと一致しない場合にアラートを出す

<details>
<summary>回答を表示</summary>

**回答: B) 機械学習を使用して予想されるメトリクス範囲を学習し、それを超えた場合にアラートを出す**

**解説:**
CloudWatch Anomaly Detection は、機械学習アルゴリズムを使用して履歴メトリクスデータを分析し、時刻や曜日による変動などのパターンを学習します。これに基づいて予想範囲を生成し、実際のメトリクス値がこの範囲外になった場合に異常として検出します。`ANOMALY_DETECTION_BAND(metric, stddev)` パラメータは範囲の幅を制御しますが、固定の 95% または 99.7% 信頼区間を保証するものではありません。

</details>

---

6. CloudWatch Alarms の `treat-missing-data` における `notBreaching` オプションは何を意味しますか？
   - A) データが欠落している場合にアラームをトリガーする
   - B) データが欠落している場合に以前の状態を維持する
   - C) 欠落データをしきい値に違反していないものとして扱う
   - D) データが欠落している場合に INSUFFICIENT_DATA 状態へ遷移する

<details>
<summary>回答を表示</summary>

**回答: C) 欠落データをしきい値に違反していないものとして扱う**

**解説:**
`treat-missing-data` オプション値の意味:
- `notBreaching`: 欠落データをしきい値に違反していないものとして扱う（OK と見なす）
- `breaching`: 欠落データをしきい値に違反しているものとして扱う（ALARM と見なす）
- `ignore`: 現在の状態を維持する
- `missing`: すべての評価データが欠落している場合は INSUFFICIENT_DATA

メトリクスの意味に応じて選択してください。`notBreaching` は断続的なエラー数に適している場合がありますが、欠落したハートビートを見逃す可能性があります。EC2 の変更アクションを伴うアラームには `missing` を使用し、ALARM の場合にのみトリガーしてください。十分な数の追加の実データポイントは、欠落データの補完より優先されます。

</details>

---

7. CloudWatch Alarm Action として直接実行できないアクションはどれですか？
   - A) EC2 インスタンスの停止/終了/再起動/復旧
   - B) Auto Scaling ポリシーのトリガー
   - C) SNS トピックへのメッセージ送信
   - D) EKS Pod の再起動

<details>
<summary>回答を表示</summary>

**回答: D) EKS Pod の再起動**

**解説:**
CloudWatch Alarm Actions では、次の AWS ネイティブ操作を直接実行できます。
- EC2 アクション: 停止、再起動、復旧、終了（起動は直接アクションではありません）
- Auto Scaling アクション: スケールアウト/スケールインポリシーのトリガー
- SNS アクション: トピックへのメッセージ送信

EKS Pod の再起動は直接サポートされておらず、別途認可された Lambda/ワークフローおよび Kubernetes API パスが必要です。

</details>

---

8. Container Insights において、EKS クラスター内の Pod 再起動回数を監視するメトリクスは何ですか？
   - A) pod_restart_count
   - B) pod_number_of_container_restarts
   - C) container_restart_total
   - D) kube_pod_container_status_restarts

<details>
<summary>回答を表示</summary>

**回答: B) pod_number_of_container_restarts**

**解説:**
Container Insights における主要な EKS メトリクス:
- `pod_number_of_container_restarts`: Pod の累積コンテナ再起動回数。ClusterName、Namespace、PodName が必要
- `pod_cpu_utilization`: Pod CPU 使用率
- `pod_memory_utilization`: Pod メモリ使用率
- `node_cpu_utilization`: Node CPU 使用率
- `cluster_node_count`: クラスターの Node 数

これらのメトリクスは `ContainerInsights` 名前空間で利用できます。

</details>

---

9. CloudWatch Alarms のコスト最適化に推奨されないプラクティスはどれですか？
   - A) 重要度が低いアラートには Standard Resolution（60 秒）を使用する
   - B) 評価対象メトリクスと保持される子アラームの料金を考慮する
   - C) すべてのアラートに High Resolution（10 秒）を使用する
   - D) 未使用のアラームを定期的に削除する

<details>
<summary>回答を表示</summary>

**回答: C) すべてのアラートに High Resolution（10 秒）を使用する**

**解説:**
高解像度は、レイテンシー要件と収集解像度に見合う場合にのみ選択してください。60 秒は標準解像度です。コンポジットアラームはその子アラームを保持し、追加料金が発生します。通知ノイズを減らしても、コストが自動的に下がるわけではありません。異常検知アラームには、評価対象メトリクスと上限/下限バンドメトリクスが含まれます。実際の Region の最新料金を確認してください。

</details>

---

10. 自動応答のために EventBridge と CloudWatch Alarms を統合する場合、アラーム状態の変化を検出する `detail-type` は何ですか？
    - A) "AWS CloudWatch Alarm"
    - B) "CloudWatch Alarm State Change"
    - C) "CloudWatch Metric Alarm"
    - D) "AWS Alarm Notification"

<details>
<summary>回答を表示</summary>

**回答: B) "CloudWatch Alarm State Change"**

**解説:**
EventBridge で CloudWatch Alarm の状態変化を検出するためのイベントパターン:
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

このパターンを使用すると、アラーム状態が ALARM に変化したときに Lambda 関数、Step Functions、SSM Automation などをトリガーして、自動応答を実装できます。

</details>

---

## 追加学習リソース

- [Amazon CloudWatch Alarms Documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- [CloudWatch Metrics Math](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/using-metric-math.html)
- [CloudWatch Anomaly Detection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html)
- [Container Insights Metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html)
