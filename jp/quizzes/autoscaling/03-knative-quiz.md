# Knativeクイズ

> **最終更新**: 2026年9月11日

1. Knative ServingのScale-to-Zeroはどのように機能しますか？
   - A) Podを削除し、新しいrequestを受けたらDeploymentを再作成する
   - B) autoscaling経路がreadyなreplicaを起動する間、Activatorが対象requestをbufferする
   - C) Nodeを停止し、requestのたびにKarpenterで新しいNodeをprovisionする
   - D) containerを一時停止し、requestを受けたら再開する

<details>
<summary>解答を表示</summary>

**正解: B) autoscaling経路がreadyなreplicaを起動する間、Activatorが対象requestをbufferする**

**解説:**
replicaが0のときはActivatorを経由するrouting経路が使われます。Activatorは自身の容量とtimeoutの範囲でrequestをbufferし、activationによってreadyな処理容量が確保されます。failureやbuffer容量の超過、client/request timeoutによってerrorになる場合があります。min-scaleを1以上にすると通常のidle時にScale-to-Zeroしませんが、新しいRevisionの初期化、restart、追加replicaの起動は引き続き発生します。

</details>

---

2. Knative ServingのKPAとHPA integrationの違いは何ですか？
   - A) KPAはCPUのみ、HPAはmemoryのみを基準にscaleする
   - B) KPAはconcurrencyを基準にScale-to-Zeroに対応し、HPAはCPU/memoryを基準にscaleする
   - C) KPAはNodeをscaleし、HPAはPodをscaleする
   - D) KPAは手動scale、HPAは自動scaleである

<details>
<summary>解答を表示</summary>

**正解: B) KPAはconcurrencyを基準にScale-to-Zeroに対応し、HPAはCPU/memoryを基準にscaleする**

**解説:**
Knative KPAはconcurrency/RPSに対応し、Activatorを使ったScale-to-Zero経路を提供します。任意で導入するKnative HPA extensionは、CPU、memory、対応するcustom Pod metricを使いますが、このzero経路は実装しません。これはKubernetes HPA全体についての一般論ではありません。upstream Kubernetes 1.37ではobject/external metricを対象としたScale-to-Zeroがbetaです。1.23のHPA実装では、CPU targetはCPU requestに対する利用率の割合、memory targetはMiB、custom metricはPodごとの平均値を使います。

</details>

---

3. Knative EventingのBroker/Trigger patternにおけるTriggerの役割は何ですか？
   - A) eventを生成するsource
   - B) Brokerのeventをfilterし、特定のserviceにrouteする
   - C) eventの永続storage
   - D) eventを外部systemに送るgateway

<details>
<summary>解答を表示</summary>

**正解: B) Brokerのeventをfilterし、特定のserviceにrouteする**

**解説:**
Triggerは一つのBrokerに対するfilter条件とsubscriberを定義し、controllerとBrokerのdataplaneがdeliveryを実行します。条件に一致するTriggerが複数あると、同じeventが複数回deliveryされる場合があります。retryとbacking storeの動作は実装とpolicyによって異なります。Triggerは永続event storeでも、汎用consumer autoscalerでもありません。

</details>

---

4. Knative Serviceで`containerConcurrency: 1`を設定すると、どうなりますか？
   - A) containerごとにPodが一つだけ作成される
   - B) Queue ProxyはPodごとに同時に一件までrequestを転送し、待ち行列の範囲内で待機させながら非同期にscaleする
   - C) 1秒あたり一件のrequestだけが許可される
   - D) Revisionが一つだけ維持される

<details>
<summary>解答を表示</summary>

**正解: B) Queue ProxyはPodごとに同時に一件までrequestを転送し、待ち行列の範囲内で待機させながら非同期にscaleする**

**解説:**
Queue Proxyは各Podで、受信containerへ転送する同時request数を制限します。追加requestは上限付きqueueで待つか、処理可能な容量へ送られるか、失敗する場合があります。autoscalingは非同期で、各種上限とNode容量にも制約されます。1秒あたり一件の制限でも、全replicaを通じた一件の制限でもなく、追加requestごとにPodが作成される保証もありません。

</details>

---

5. KEDAとKnativeを組み合わせる適切な方法はどれですか？
   - A) 互換性がないため、どちらか一方だけを使う
   - B) HTTP workloadにはKnative Serving、queue/stream型の非同期workloadにはKEDAを使う
   - C) KEDAとKPAの両方で、同じKnative生成Deploymentを個別にscaleする
   - D) Knative Serviceを作成すると、KEDAが自動でinstallされdefault autoscalerになる

<details>
<summary>解答を表示</summary>

**正解: B) HTTP workloadにはKnative Serving、queue/stream型の非同期workloadにはKEDAを使う**

**解説:**
適したHTTP serviceにはKnative Servingを、個別に管理するbackground workerにはKEDAを使います。queue retention/acknowledgement、activation metric、workerのidempotencyを設定してください。KEDAとKPAの両方で、同じ生成Deploymentを制御してはいけません。SinkBindingはevent producerを設定するもので、Scale-to-Zero中の任意のHTTP consumerを起動するものではありません。

</details>

---

6. Knativeのtraffic splittingを使ってCanary deploymentを実装するには、どうしますか？
   - A) Deploymentのreplica数を調整する
   - B) Knative Serviceのspec.trafficでRevisionごとのtraffic割合を指定する
   - C) Istio VirtualServiceを手動で作成する
   - D) HPAのminReplicasを調整する

<details>
<summary>解答を表示</summary>

**正解: B) Knative Serviceのspec.trafficでRevisionごとのtraffic割合を指定する**

**解説:**
spec.trafficには、revisionNameを指定したtargetか、latestRevision: trueとtraffic割合を設定します。`@latest`はkn CLIの省略表記であり、revisionNameの値や「最新」を意味するAPI tagではありません。参照するRevisionは存在し、readyである必要があります。routeのreconcileは全体へ即時反映されるわけではなく、既存requestが古いRevisionで処理され続ける場合もあります。

</details>

---

7. KnativeのDead Letter Sinkの目的は何ですか？
   - A) 削除されたKnative Serviceをarchiveする
   - B) subscriberへのdeliveryに失敗したとき、設定済みの別destinationへのdeliveryを試みる
   - C) 期限切れのRevisionを削除する
   - D) debug logを保存する

<details>
<summary>解答を表示</summary>

**正解: B) subscriberへのdeliveryに失敗したとき、設定済みの別destinationへのdeliveryを試みる**

**解説:**
delivery policyに従ってsubscriberへeventを届けられない場合、設定済みのDLSが代替destinationとして使われます。DLSへのdeliveryも失敗する場合があります。eventの保持と永続化が成功するかはtransportとhandler次第です。意図したstorageまたは処理が成功した後にacknowledgeし、必要に応じてCloudEventのsourceとidを使って重複を排除してください。

</details>

---

8. 明示的なwarm capacityの方針を保ちながらcold-start latencyを下げる組み合わせはどれですか？
   - A) container imageのsizeを際限なく小さくする
   - B) `minScale` annotationでminimum instance数を保ち、高速起動するframeworkと軽量imageを使う
   - C) Scale-to-Zeroを完全に無効にする
   - D) Node数を常に最大にする

<details>
<summary>解答を表示</summary>

**正解: B) `minScale` annotationでminimum instance数を保ち、高速起動するframeworkと軽量imageを使う**

**解説:**
autoscaling.knative.dev/min-scaleを正の値にすると、通常のidle期間でもbaseline capacityを維持できます。一方、initial-scaleはRevision作成時の初期replica数に適用されます。image size、Nodeの利用可否、image cache、startup、readinessの挙動はいずれもlatencyに影響します。新しいRevision、restart、warm baselineを超えるscale-outではcold startが起こり得るため、発生しないと約束せず、実際のtrafficで測定してください。

</details>
