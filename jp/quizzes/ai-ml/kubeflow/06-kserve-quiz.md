# パート 6: KServe — Kubernetes 上の Model Serving クイズ

このクイズでは、KServe と Kubeflow の関係、`InferenceService` コンポーネント、Serverless と Raw Deployment のトレードオフ、autoscaling の仕組み、canary rollout、EKS での GPU inference についての理解を確認します。

## 多肢選択問題

1. KServe と Kubeflow の歴史的な関係は何ですか？
   - A) KServe は常に Kubeflow との関係がない完全に独立したプロジェクトだった
   - B) KServe は Kubeflow 内で KFServing として始まり、その後独自の top-level standalone project として独立した
   - C) Kubeflow は KServe の subcomponent である
   - D) KServe は Katib の rebranding である

<details>
<summary>解答を表示</summary>

**解答: B) KServe は Kubeflow 内で KFServing として始まり、その後独自の top-level standalone project として独立した**

**解説:**
KServe は、trained model を inference endpoint に変換する役割を担う Kubeflow 内のコンポーネントである KFServing として始まりました。その後、Kubeflow なしで任意の Kubernetes cluster にインストールできる独立した standalone project になりましたが、Kubeflow は引き続きこれをデフォルトの model-serving layer としてバンドルしています。
</details>

2. Kubeflow dashboard の KServe web app に表示される version が、KServe controller/CRD の version と一致すると想定できないのはなぜですか？
   - A) Kubeflow dashboard は KServe version 情報を一切表示しない
   - B) KServe には Kubeflow Community Distribution の calendar-versioned release train とは別の独自の release cadence があるため、platform team は web app とは独立して controller を upgrade できる
   - C) KServe は deprecated であり、もはや version update を受け取らない
   - D) Kubeflow web app と KServe controller は常に完全に同じ binary である

<details>
<summary>解答を表示</summary>

**解答: B) KServe には Kubeflow Community Distribution の calendar-versioned release train とは別の独自の release cadence があるため、platform team は web app とは独立して controller を upgrade できる**

**解説:**
Kubeflow Community Distribution 26.03 は KServe web app の v0.16.1 をバンドルしていますが、この番号は dashboard integration を表すものであり、cluster 上で実行されている基盤となる KServe controller/CRD の version を必ずしも表していません。controller は独自のスケジュールで upgrade できるためです。
</details>

3. 他は optional である一方、必須の `InferenceService` コンポーネントはどれですか？
   - A) Explainer
   - B) Transformer
   - C) Predictor
   - D) 3 つすべてが必須である

<details>
<summary>解答を表示</summary>

**解答: C) Predictor**

**解説:**
predictor は model server 自体であり、`InferenceService` の唯一の必須コンポーネントです。transformer（pre/post-processing）と explainer（model explanations）は、use case で必要となる場合にのみ使用する optional add-on です。
</details>

4. KServe の Serverless deployment mode を定義づける機能と、そのコストは何ですか？
   - A) plain Deployment と HPA を使用し、トレードオフはまったくない
   - B) idle 時に Knative を介して pod を zero まで scale するが、scale-up 時に cold-start latency が発生する
   - C) Kubernetes cluster をまったく必要としない
   - D) predictor が不要になる

<details>
<summary>解答を表示</summary>

**解答: B) idle 時に Knative を介して pod を zero まで scale するが、scale-up 時に cold-start latency が発生する**

**解説:**
Serverless mode は pod lifecycle を Knative Serving に委任します。これにより、traffic がない場合は predictor（および transformer/explainer）pod を完全に zero まで scale でき、idle 時の GPU cost を削減できます。トレードオフは cold-start latency です。新しい pod の scheduling、container の起動、model artifact の loading には時間がかかるため、zero から scale した後の最初の request に応答できるまで待機が発生します。
</details>

5. Raw Deployment mode と Serverless mode の主な違いは何ですか？
   - A) Raw Deployment mode は Knative dependency や scale-to-zero なしで plain Deployment/Service（および optional HPA）を管理する
   - B) Raw Deployment mode は Knative Serving を必要とするが、transformer を自動的に追加する
   - C) Raw Deployment mode は SKLearn model でのみ利用できる
   - D) Raw Deployment mode は常に Serverless mode より多くの replica を実行する

<details>
<summary>解答を表示</summary>

**解答: A) Raw Deployment mode は Knative dependency や scale-to-zero なしで plain Deployment/Service（および optional HPA）を管理する**

**解説:**
Raw Deployment mode は運用上よりシンプルであり（install/upgrade する Knative が不要）、cold start を完全に回避できます。しかし、Deployment の設定済み minimum replica count を下回る scale は行わないため、traffic に関係なく少なくともその数の predictor pod（GPU を使用する場合はその GPU も）が常に実行されます。
</details>

6. 2 つの deployment mode では autoscaling はどのように異なりますか？
   - A) 両方の mode で、まったく同じ HPA ベースの CPU scaling を使用する
   - B) Serverless mode は Knative の concurrency/RPS ベースの signal で scale し、Raw Deployment mode は CPU/memory または custom metrics を使用する標準 HPA で scale する
   - C) Serverless mode は一切 scale しない
   - D) Raw Deployment mode は Knative concurrency に基づいて scale し、Serverless mode は HPA を使用する

<details>
<summary>解答を表示</summary>

**解答: B) Serverless mode は Knative の concurrency/RPS ベースの signal で scale し、Raw Deployment mode は CPU/memory または custom metrics を使用する標準 HPA で scale する**

**解説:**
Serverless mode の Knative autoscaler は、concurrency や requests-per-second などの request-level signal に反応します。これは resource-utilization signal よりも bursty な inference traffic に素早く反応する傾向があります。一方、Raw Deployment mode は、cluster 上の他の Deployment と同じ autoscaling model である標準 Kubernetes HorizontalPodAutoscaler に依存します。
</details>

7. KServe の built-in canary rollout mechanism は、このドキュメントの他の箇所で扱う Istio/Argo Rollouts の traffic-splitting pattern とどのような関係にありますか？
   - A) 名前が異なるだけで、まったく同じ mechanism である
   - B) KServe の canary rollout は KServe control plane に組み込まれた、model-serving 固有の独立した mechanism であり、service-mesh または progressive-delivery-controller の traffic-splitting とは異なる
   - C) KServe には canary rollout capability がなく、代わりに Argo Rollouts を使用する必要がある
   - D) Istio traffic-splitting は InferenceService 自体の必要性を置き換える

<details>
<summary>解答を表示</summary>

**解答: B) KServe の canary rollout は KServe control plane に組み込まれた、model-serving 固有の独立した mechanism であり、service-mesh または progressive-delivery-controller の traffic-splitting とは異なる**

**解説:**
KServe は stable と canary の `InferenceService` revision 間で独自に traffic を分割し、confidence の向上に応じて traffic を徐々に移行できます。これは特に `InferenceService` revision の level で動作し、platform 上の他の workload に使用される Istio または Argo Rollouts ベースの traffic-splitting pattern とは別の tool です。置き換えの要件ではなく、独自の model-serving 固有の path です。
</details>

8. `InferenceService` predictor が EKS で GPU を request するとき、Karpenter はどのような役割を果たしますか？
   - A) Karpenter は KServe predictor の inference protocol を構成する
   - B) Karpenter は pod の GPU request を既存 node が満たせない場合に対応する GPU-backed EC2 instance を provision し、その capacity が不要になったら consolidate/reclaim できる
   - C) Karpenter は GPU device plugin の必要性を置き換える
   - D) Karpenter は Raw Deployment mode でのみ動作し、Serverless mode では決して動作しない

<details>
<summary>解答を表示</summary>

**解答: B) Karpenter は pod の GPU request を既存 node が満たせない場合に対応する GPU-backed EC2 instance を provision し、その capacity が不要になったら consolidate/reclaim できる**

**解説:**
EKS での GPU inference は、GPU device plugin が公開する resource に対する標準 Kubernetes resource request model に従います。Karpenter の GPU node pool は unschedulable な GPU request に反応して対応する capacity を provision し、その consolidation behavior は predictor（特に Serverless mode で zero まで scale する predictor）が不要になった capacity を reclaim できます。これは、このドキュメントの他の箇所の EKS でも使用される two-tier autoscaling pattern です。
</details>

## 短答問題

9. 1 文または 2 文で、spiky で intermittent な inference traffic を持つ model には Serverless mode が適している一方、すべての request で一貫して低い latency を必要とする model には不向きである理由を説明してください。

<details>
<summary>解答を表示</summary>

**解答: Serverless mode の scale-to-zero は idle period 中の GPU cost を削減するため、model が多くの時間 idle 状態にある spiky/intermittent traffic に適しています。しかし、zero からの scale-up には cold-start latency（pod scheduling、container start、model load）が発生するため、個々の request すべてに一貫して低い latency が必要な workload には受け入れられません。**

**解説:**
このトレードオフの本質は、cost（idle GPU savings）と latency predictability（cold start がないこと）の比較です。Raw Deployment mode は、このトレードオフを反転させ、idle 時にもその capacity の cost を支払う代わりに、minimum replica count を常に warm に保ちます。
</details>

10. KServe における predictor の built-in framework support と custom container predictor の違いは何ですか？

<details>
<summary>解答を表示</summary>

**解答: Built-in predictor server（例: SKLearn、XGBoost、TorchServe 経由の PyTorch、NVIDIA Triton 用）では、predictor spec が model artifact location を指定するだけで、serving code を書くことなく動作する server を利用できます。custom container predictor はこれらの built-in framework の対象外に使用され、それ自体が KServe の inference protocol を実装する必要があります。**

**解説:**
この違いにより、必要な serving-side implementation work の量が決まります。built-in server は一般的な framework をすぐに利用できる形でカバーしますが、それ以外には KServe の protocol を話す手書きの container が必要です。
</details>

11. KServe 自身の scaling decision と、それに対する Karpenter の response の間にある two-tier autoscaling relationship を説明してください。

<details>
<summary>解答を表示</summary>

**解答: KServe（Serverless mode では Knative、Raw Deployment mode では HPA 経由）は、request-level または resource-utilization signal に基づいて必要な predictor pod 数を決定します。これは node を認識しない pod-level decision です。Karpenter はこれとは別に、結果として生じる pod scheduling state（unschedulable な GPU request、または空の GPU node）に反応して、provision または reclaim する EC2 GPU capacity の量を決定します。これは pod が存在する理由を認識しない node-level decision です。**

**解説:**
これらは独立した 2 つの control loop であり、pod count/scheduling state を通じてのみ結び付いています。これは、このドキュメントの他の箇所の EKS における他の autoscaled workload でも使用される、同じ一般的な two-tier autoscaling pattern（まず job/pod-level decision が行われ、それに node-level decision が反応する）です。
</details>

---

[学習教材に戻る](../../../ai-ml/kubeflow/06-kserve.md)
