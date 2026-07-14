# CloudWatch Metrics クイズ

CloudWatch Metrics の理解度を確認するクイズです。

---

1. Amazon CloudWatch Container Insights の主な機能は何ですか？
   - A) Container image のビルド
   - B) EKS cluster の Container/Pod レベルのモニタリング
   - C) Container orchestration
   - D) CI/CD pipeline の管理

<details>
<summary>回答を表示</summary>

**回答: B) EKS cluster の Container/Pod レベルのモニタリング**

**解説:**
Container Insights は、EKS、ECS、Kubernetes 環境の containerized workload をモニタリングする CloudWatch の機能です。cluster、node、Pod、Container レベルの CPU、memory、network、filesystem metrics を自動的に収集し、可視化します。

</details>

---

2. CloudWatch Agent を EKS にデプロイする推奨方法は何ですか？
   - A) 単一の Pod としてデプロイする
   - B) DaemonSet としてすべての node にデプロイする
   - C) Deployment で 3 replicas としてデプロイする
   - D) StatefulSet としてデプロイする

<details>
<summary>回答を表示</summary>

**回答: B) DaemonSet としてすべての node にデプロイする**

**解説:**
CloudWatch Agent は、各 node から metrics と logs を収集するために DaemonSet としてデプロイされます。これにより、すべての node から system metrics、Container metrics、logs を一貫して収集できます。

</details>

---

3. CloudWatch Metric Math における `SEARCH()` 関数の目的は何ですか？
   - A) Log の検索
   - B) pattern に一致する metrics を動的に検索する
   - C) Alert の検索
   - D) Dashboard の検索

<details>
<summary>回答を表示</summary>

**回答: B) pattern に一致する metrics を動的に検索する**

**解説:**
`SEARCH()` 関数は、namespace、dimension、metric name の pattern を使用して metrics を動的に検索します。たとえば、`SEARCH('{AWS/EC2,InstanceId} MetricName="CPUUtilization"', 'Average')` は、すべての EC2 instance の CPU utilization を検索します。

</details>

---

4. CloudWatch Anomaly Detection はどのように機能しますか？
   - A) 手動で設定した threshold に基づく検出
   - B) ML に基づく異常 pattern の自動検出
   - C) Log pattern の分析
   - D) Network traffic の分析

<details>
<summary>回答を表示</summary>

**回答: B) ML に基づく異常 pattern の自動検出**

**解説:**
CloudWatch Anomaly Detection は machine learning を使用して metrics の通常の pattern を学習し、異常値を自動的に検出します。seasonality、trend、曜日の pattern を考慮した動的な expected range（band）を生成し、値がこの range の外に出た場合に anomaly を特定します。

</details>

---

5. AWS Distro for OpenTelemetry (ADOT) を使用して Prometheus metrics を CloudWatch に送信する場合、どの exporter を使用しますか？
   - A) prometheus-exporter
   - B) awsemf (AWS EMF Exporter)
   - C) cloudwatch-exporter
   - D) metric-exporter

<details>
<summary>回答を表示</summary>

**回答: B) awsemf (AWS EMF Exporter)**

**解説:**
ADOT で Prometheus metrics を CloudWatch に送信するには、AWS EMF (Embedded Metric Format) Exporter を使用します。この exporter は metrics を CloudWatch Logs 内の EMF format に変換して送信し、CloudWatch がそれを metrics として抽出します。

</details>

---

6. CloudWatch の cost optimization に有効ではない方法はどれですか？
   - A) Log retention period を設定する
   - B) 不要な high-resolution metrics を削除する
   - C) すべての metrics を 1-second interval で収集する
   - D) Infrequent Access log class を使用する

<details>
<summary>回答を表示</summary>

**回答: C) すべての metrics を 1-second interval で収集する**

**解説:**
High-resolution metrics（1-second interval）は高価です。cost optimization のため、必要な metrics のみを high resolution で収集し、大半の metrics は 60-second interval（default）で収集します。log retention period の設定、不要な metrics の filtering、Infrequent Access log class の使用も cost の削減に役立ちます。

</details>

---

7. CloudWatch で custom metrics を作成するために使用する API はどれですか？
   - A) CreateMetric
   - B) PutMetricData
   - C) PublishMetric
   - D) SendMetric

<details>
<summary>回答を表示</summary>

**回答: B) PutMetricData**

**解説:**
`PutMetricData` API は、custom metrics を CloudWatch に送信するために使用します。namespace、metric name、dimensions、value、unit、timestamp などを指定できます。AWS SDK または CLI から呼び出せます。

</details>

---

8. CloudWatch における Dimensions の役割は何ですか？
   - A) Metric unit を指定する
   - B) Metrics を区分する key-value pair
   - C) Alert severity を指定する
   - D) Log group を指定する

<details>
<summary>回答を表示</summary>

**回答: B) Metrics を区分する key-value pair**

**解説:**
Dimensions は、metrics を区分し識別する key-value pair です。たとえば、EC2 instance metrics では、`InstanceId` dimension が特定の instance を識別します。単一の metric には最大 30 dimensions を指定できます。

</details>

---

9. Enhanced Container Insights は basic Container Insights とどのように異なりますか？
   - A) 無料で提供される
   - B) 追加の metrics と、より詳細なモニタリングを提供する
   - C) Log collection 機能を削除する
   - D) Alerting 機能のみを提供する

<details>
<summary>回答を表示</summary>

**回答: B) 追加の metrics と、より詳細なモニタリングを提供する**

**解説:**
Enhanced Container Insights は basic Container Insights より多くの metrics を収集します。reserved CPU/memory capacity、GPU metrics（該当する場合）、Kubernetes control plane metrics などの追加情報を提供します。cost は高くなりますが、より詳細なモニタリングが可能になります。

</details>

---

10. CloudWatch alerts における `ANOMALY_DETECTION_BAND()` 関数の役割は何ですか？
    - A) 固定 threshold を設定する
    - B) anomaly detection model から expected range を返す
    - C) Log filtering
    - D) Dashboard の作成

<details>
<summary>回答を表示</summary>

**回答: B) anomaly detection model から expected range を返す**

**解説:**
`ANOMALY_DETECTION_BAND()` 関数は、anomaly detection model が学習した expected value range（upper/lower bounds）を返します。この range は alerts で使用でき、metrics が expected range の外に出たときに notification をトリガーします。2 番目の argument は standard deviation multiplier を指定し、band width を調整します。

</details>
