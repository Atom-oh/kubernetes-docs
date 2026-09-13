# KServe クイズ

ベースライン: KServe 0.18.0 / Community Distribution 26.03.1。

## 多肢選択問題

1. KServe は Kubeflow とどのような関係にありますか？

   - A) KFServing から進化し、依存関係とともに独立して実行できる
   - B) Katib の新しい名称である
   - C) 常に Kubeflow ディストリビューション全体を必要とする
   - D) Kubernetes を置き換える

<details>
<summary>回答を表示</summary>

**回答: A) KFServing から進化し、依存関係とともに独立して実行できる**

すべての KServe インストールで、Kubeflow 全体と Models Web Application が前提条件になるわけではありません。
</details>

2. この章ではどのバージョンを確認していますか？

   - A) 0.16.1 の web app のみ
   - B) Community 26.03.1 の KServe と web app 0.18.0。確認した最新の KServe は 0.20.0
   - C) すべてのコンポーネントは異なるバージョンでなければならない
   - D) web-app ラベルが、インストールされたすべての CRD を決定する

<details>
<summary>回答を表示</summary>

**回答: B) Community 26.03.1 の KServe と web app 0.18.0。確認した最新の KServe は 0.20.0**

Controller、CRD、web app は別々のアーティファクトです。実際の互換性とリビジョンを記録する必要があります。
</details>

3. 必須の InferenceService コンポーネントはどれですか？

   - A) Explainer
   - B) Transformer
   - C) Predictor
   - D) 3 つすべて

<details>
<summary>回答を表示</summary>

**回答: C) Predictor**

Transformer と explainer はオプションです。runtime/protocol の互換性と、実際の explanation route は依然として重要です。
</details>

4. Knative を選択すると、アイドル状態のすべての predictor は自動的にゼロまでスケールしますか？

   - A) はい。設定は不要
   - B) いいえ。KServe のデフォルトでは minReplicas は 1 であり、ゼロへのスケールには minReplicas 0 など、サポートされる autoscaler/policy 設定が必要
   - C) はい。EC2 の課金も直ちに停止する
   - D) Knative のインストールは不要

<details>
<summary>回答を表示</summary>

**回答: B) いいえ。KServe のデフォルトでは minReplicas は 1 であり、ゼロへのスケールには minReplicas 0 など、サポートされる autoscaler/policy 設定が必要**

ゼロからのスケールには、capacity、image、model のロードが含まれます。Pod がゼロでも node の終了は保証されません。
</details>

5. Standard mode に関する正しい記述はどれですか？

   - A) 常にウォームで正常な replica を保証する
   - B) Deployment/Service を使用する。デフォルトの HPA は少なくとも 1 を維持する一方、設定済みの KEDA path はゼロをサポートできる
   - C) 常に Knative を必要とする
   - D) autoscaling の選択肢を一切サポートしない

<details>
<summary>回答を表示</summary>

**回答: B) Deployment/Service を使用する。デフォルトの HPA は少なくとも 1 を維持する一方、設定済みの KEDA path はゼロをサポートできる**

KEDA には、インストール、有効な metrics/triggers、activation path が必要です。restart/rollout/scale-out の起動レイテンシーはいずれの mode にも残ります。
</details>

6. 0.18.0 における最新の mode 名は何ですか？

   - A) Serverless と RawDeployment だけが有効な名前である
   - B) Knative と Standard。古い名前は非推奨のエイリアスである
   - C) HPA と GPU
   - D) Predictor と Transformer

<details>
<summary>回答を表示</summary>

**回答: B) Knative と Standard。古い名前は非推奨のエイリアスである**

実際の annotation と config を確認してください。code の fallback は Standard です。確認した OCI resource chart のデフォルトは Knative です。
</details>

7. 検証済みの canaryTrafficPercent path を実装するのは何ですか？

   - A) KServe Controller がすべてのリクエストを自身で proxy する
   - B) KServe が Knative revision の traffic target を設定し、Knative networking がリクエストをルーティングする
   - C) すべての Standard Deployment が自動的に同じ revision splitting を持つ
   - D) Argo Rollouts が必須である

<details>
<summary>回答を表示</summary>

**回答: B) KServe が Knative revision の traffic target を設定し、Knative networking がリクエストをルーティングする**

Standard の rolling update は、同じ revision-percentage mechanism ではありません。promotion/rollback と保持される artifact は別途検証する必要があります。
</details>

8. nvidia.com/gpu をリクエストすると、GPU inference は保証されますか？

   - A) はい。すべての model で保証される
   - B) いいえ。driver、image/backend、model/device 設定も一致している必要がある
   - C) 必要なすべての driver を自動的にインストールする
   - D) node capacity は不要になる

<details>
<summary>回答を表示</summary>

**回答: B) いいえ。driver、image/backend、model/device 設定も一致している必要がある**

resource allocation と実際の model execution は別物です。Karpenter は、policy、quota、可用性に従って適格な capacity を供給します。
</details>

## 短答問題

9. 常にウォームな状態とゼロへのスケールが、2 つの mode 間の絶対的な区別ではないのはなぜですか？

<details>
<summary>回答を表示</summary>

Knative は minimum setting を通じてウォームな replica を保持でき、Standard は適切な external signal とともに KEDA を使用できます。どちらの mode も可用性やレイテンシーを保証しません。readiness、ロード、capacity、recovery をテストしてください。
</details>

10. artifact URI だけでは不十分な理由と、TorchServe をどのように扱うべきですか？

<details>
<summary>回答を表示</summary>

runtime、model format/layout、library version、credentials、ports、protocol が一致している必要があります。TorchServe は、今後の security fix の予定がなく、もはや積極的にはメンテナンスされていないと述べています。そのため、古い runtime catalog entry は、メンテナンスされているデフォルトの証拠にはなりません。
</details>

11. Pod autoscaling と EC2 scaling はどのように相互作用しますか？

<details>
<summary>回答を表示</summary>

Knative/HPA/KEDA または別途設定された scaler が、必要な Pod 数を決定します。Kubernetes scheduling と Karpenter capacity policy は node provisioning/reclamation に影響します。model Pod がゼロになった後も、他の workload や disruption rule により EC2 node の課金が継続する可能性があります。
</details>

---

[学習教材に戻る](../../../ai-ml/kubeflow/06-kserve.md)
