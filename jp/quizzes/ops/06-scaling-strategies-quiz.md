# スケーリング戦略クイズ

> **関連ドキュメント**: [スケーリング戦略](../../ops/06-scaling-strategies.md)

## 選択式問題

### 1. HPA で custom metrics を使用するには何が必要ですか？

- A) Kubernetes 1.30 以上
- B) Prometheus Adapter または同様の custom metrics server
- C) AWS Auto Scaling integration
- D) 手動での Pod scaling

<details>
<summary>回答を表示</summary>

**回答: B) Prometheus Adapter または同様の custom metrics server**

**解説:**
custom metrics を使用する HPA には、custom.metrics.k8s.io API を実装する metrics server が必要です。Prometheus Adapter は Prometheus に query し、HPA が期待する形式で metrics を公開することで、1 秒あたりの requests など application-specific metrics に基づく scaling を可能にします。

</details>

### 2. KEDA は HPA では scaling できないどのような種類の event に基づいて scaling できますか？

- A) CPU utilization
- B) Memory usage
- C) SQS queue depth や Kafka lag などの external events
- D) Pod restart counts

<details>
<summary>回答を表示</summary>

**回答: C) SQS queue depth や Kafka lag などの external events**

**解説:**
KEDA (Kubernetes Event-Driven Autoscaling) には、AWS SQS、Kafka、RabbitMQ、databases などの external systems 向けの scaler が含まれています。KEDA はゼロまで scale でき、Kubernetes metrics system の外部にある event に反応できます。

</details>

### 3. VPA mode の「Auto」と「Off」の違いは何ですか？

- A) Auto は HPA を有効にし、Off は無効にする
- B) Auto は Pod を in-place で更新し、Off は recommendation のみを提供する
- C) Auto は restart が必要で、Off は即時に反映される
- D) Auto は Spot instances を使用し、Off は On-Demand を使用する

<details>
<summary>回答を表示</summary>

**回答: B) Auto は Pod を in-place で更新し、Off は recommendation のみを提供する**

**解説:**
VPA の「Auto」mode は、更新された resource requests で Pod を自動的に evict して再作成します。「Off」mode は変更を行わず recommendation のみを生成するため、手動で実装する前に提案内容を review するのに役立ちます。

</details>

### 4. Pod Deletion Cost とは何で、scaling にどのように影響しますか？

- A) Pod を削除する financial cost
- B) scale-down 時にどの Pod を先に削除するかに影響する annotation
- C) Pod の削除に必要な時間
- D) Pod termination に関連する storage costs

<details>
<summary>回答を表示</summary>

**回答: B) scale-down 時にどの Pod を先に削除するかに影響する annotation**

**解説:**
`controller.kubernetes.io/pod-deletion-cost` annotation は Pod に cost value を割り当てます。scale-down 時には、deletion cost が低い Pod が先に終了されます。これにより、重要な workload を実行している Pod や cached data を持つ Pod を維持しやすくなります。

</details>

### 5. custom metrics で HPA を使用する場合、desired replicas を計算する式は何ですか？

- A) currentReplicas + 1
- B) desiredReplicas = ceil(currentReplicas * (currentMetricValue / desiredMetricValue))
- C) maxReplicas / 2
- D) currentMetricValue * targetUtilization

<details>
<summary>回答を表示</summary>

**回答: B) desiredReplicas = ceil(currentReplicas * (currentMetricValue / desiredMetricValue))**

**解説:**
HPA は current metric values を target values と比較し、その後比例的に scaling して desired replicas を計算します。ceiling function により、scale up 時には少なくとも 1 つの追加 replica が追加されます。

</details>

### 6. Spot node interruption handling の推奨戦略は何ですか？

- A) interruption を無視する
- B) Pod Disruption Budgets と interruption handlers による graceful termination を使用する
- C) stateless workloads のみを実行する
- D) Spot instances を完全に無効にする

<details>
<summary>回答を表示</summary>

**回答: B) Pod Disruption Budgets と interruption handlers による graceful termination を使用する**

**解説:**
Spot interruption handling は、AWS Node Termination Handler (または Karpenter の native handling)、可用性を確保するための Pod Disruption Budgets、十分な termination grace periods、そして preemption を graceful に処理する workload design を組み合わせます。

</details>

### 7. KEDA において `pollingInterval` は何を設定しますか？

- A) Pod が restart される頻度
- B) KEDA が external metric source を確認する頻度
- C) scale operations の間の delay
- D) Health check frequency

<details>
<summary>回答を表示</summary>

**回答: B) KEDA が external metric source を確認する頻度**

**解説:**
`pollingInterval` は、KEDA が metric values を取得するために external scaler (例: SQS、Prometheus) に query する頻度を定義します。interval を短くすると反応時間は速くなりますが、metric source への load が増加します。

</details>

### 8. 新しい version の Kubernetes で、VPA が restart なしに Pod を resize できるようにする Kubernetes feature は何ですか？

- A) Rolling updates
- B) In-place Pod Vertical Scaling
- C) Blue/green deployment
- D) Canary releases

<details>
<summary>回答を表示</summary>

**回答: B) In-place Pod Vertical Scaling**

**解説:**
Kubernetes 1.27+ は `resizePolicy` field を通じて in-place vertical scaling をサポートしており、Pod restart なしで CPU と memory を変更できます。VPA はこれを活用して、より disruption の少ない resource adjustment を行えます。

</details>

### 9. HPA に metrics-server ではなく Prometheus Adapter を使用する利点は何ですか？

- A) より低い resource usage
- B) CPU/memory を超える custom metrics と external metrics のサポート
- C) より速い metric collection
- D) built-in alerting

<details>
<summary>回答を表示</summary>

**回答: B) CPU/memory を超える custom metrics と external metrics のサポート**

**解説:**
metrics-server は CPU と memory metrics のみを提供します。Prometheus Adapter は custom.metrics.k8s.io API を通じて任意の Prometheus metric を公開し、HPA が 1 秒あたりの requests、queue depth、latency などの application metrics に基づいて scaling できるようにします。

</details>

### 10. HPA と VPA を組み合わせる場合、何を考慮すべきですか？

- A) 一緒に使用することはできない
- B) 異なる resource dimensions に設定する (CPU には HPA、memory には VPA)
- C) VPA が有効な場合は常に HPA を無効にする
- D) 設定なしで自動的に連携する

<details>
<summary>回答を表示</summary>

**回答: B) 異なる resource dimensions に設定する (CPU には HPA、memory には VPA)**

**解説:**
HPA と VPA の両方が同じ resource dimension を管理しようとすると競合する可能性があります。一般的な pattern は、CPU に基づく horizontal scaling に HPA を使用し、memory には recommendation mode の VPA を使用する、または Pod 作成時にのみ resources を設定する VPA の「Initial」mode を使用することです。

</details>
