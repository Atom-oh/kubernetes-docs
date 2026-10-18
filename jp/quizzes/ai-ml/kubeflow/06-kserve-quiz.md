# KServe クイズ

ベースライン: KServe 0.18.0 / Community Distribution 26.03.1。

## 多肢選択問題

1. KServe は Kubeflow とどのような関係にありますか？

   - A) KFServing から発展し、依存関係とともに独立して実行できる
   - B) Katib の新しい名称である
   - C) 常に Kubeflow ディストリビューション全体を必要とする
   - D) Kubernetes を置き換える

<details>
<summary>回答を表示</summary>

**回答: A) KFServing から発展し、依存関係とともに独立して実行できる**

すべての KServe インストールで、完全な Kubeflow と Models Web Application が前提条件となるわけではありません。
</details>

2. この章ではどのバージョンを確認していますか？

   - A) 0.16.1 の Web App のみ
   - B) Community 26.03.1 の KServe と Web App 0.18.0。2026-10-12 時点で確認した最新の KServe は 0.21.0
   - C) すべてのコンポーネントで異なるバージョンが必要である
   - D) Web App のラベルが、インストールされるすべての CRD を決定する

<details>
<summary>回答を表示</summary>

**回答: B) Community 26.03.1 の KServe と Web App 0.18.0。2026-10-12 時点で確認した最新の KServe は 0.21.0**

Controller、CRD、Web App はそれぞれ別個の成果物です。実際の互換性とリビジョンを記録する必要があります。
</details>

3. 必須の InferenceService コンポーネントはどれですか？

   - A) Explainer
   - B) Transformer
   - C) Predictor
   - D) 3 つすべて

<details>
<summary>回答を表示</summary>

**回答: C) Predictor**

Transformer と Explainer は任意です。runtime/protocol の互換性に加え、説明リクエストの実際の経路も確認する必要があります。
</details>

4. Knative を選択すると、アイドル状態のすべての Predictor は自動的にゼロまでスケールしますか？

   - A) はい。設定は不要である
   - B) いいえ。KServe の minReplicas のデフォルトは 1 であり、ゼロへのスケーリングには minReplicas 0 など、サポートされる autoscaler/policy 設定が必要である
   - C) はい。EC2 の課金も直ちに停止する
   - D) Knative のインストールは不要である

<details>
<summary>回答を表示</summary>

**回答: B) いいえ。KServe の minReplicas のデフォルトは 1 であり、ゼロへのスケーリングには minReplicas 0 など、サポートされる autoscaler/policy 設定が必要である**

ゼロからのスケールには、容量、イメージ、モデルのロードが含まれます。Pod がゼロになっても、node の終了は保証されません。
</details>

5. Standard モードについて正しい記述はどれですか？

   - A) 常にウォーム状態で正常な replica を保証する
   - B) Deployment/Service を使用する。デフォルトの HPA は少なくとも 1 を維持する一方、設定された KEDA パスではゼロをサポートできる
   - C) 常に Knative を必要とする
   - D) autoscaling オプションをまったくサポートしない

<details>
<summary>回答を表示</summary>

**回答: B) Deployment/Service を使用する。デフォルトの HPA は少なくとも 1 を維持する一方、設定された KEDA パスではゼロをサポートできる**

KEDA には、インストール、有効な metrics/triggers、アクティベーションパスが必要です。いずれのモードでも、再起動、rollout、scale-out の起動レイテンシーは残ります。
</details>

6. 0.18.0 における現在のモード名は何ですか？

   - A) Serverless と RawDeployment だけが有効な名前である
   - B) Knative と Standard。古い名前は非推奨のエイリアスである
   - C) HPA と GPU
   - D) Predictor と Transformer

<details>
<summary>回答を表示</summary>

**回答: B) Knative と Standard。古い名前は非推奨のエイリアスである**

実際の annotation と config を確認してください。コードのフォールバックは Standard ですが、確認した OCI resource chart のデフォルトは Knative です。
</details>

7. 検証済みの canaryTrafficPercent パスを実装するのは何ですか？

   - A) KServe Controller がすべてのリクエストを自らプロキシする
   - B) KServe が Knative revision のトラフィックターゲットを設定し、Knative networking がリクエストをルーティングする
   - C) すべての Standard Deployment が自動的に同じ revision 分割を持つ
   - D) Argo Rollouts が必須である

<details>
<summary>回答を表示</summary>

**回答: B) KServe が Knative revision のトラフィックターゲットを設定し、Knative networking がリクエストをルーティングする**

Standard の rolling update は、同じ revision のパーセンテージメカニズムではありません。昇格/rollback と保持された成果物には、個別の検証が必要です。
</details>

8. nvidia.com/gpu をリクエストすると、GPU inference は保証されますか？

   - A) はい。すべてのモデルで保証される
   - B) いいえ。drivers、image/backend、model/device 設定も一致している必要がある
   - C) 必要なすべての drivers が自動的にインストールされる
   - D) node 容量は不要になる

<details>
<summary>回答を表示</summary>

**回答: B) いいえ。drivers、image/backend、model/device 設定も一致している必要がある**

リソースの割り当てと実際のモデル実行は別物です。Karpenter は policy、quota、可用性に従って、適格な容量を提供します。
</details>

## 短答式問題

9. 常時ウォームとゼロへのスケーリングは、なぜ 2 つのモード間の絶対的な区別ではないのですか？

<details>
<summary>回答を表示</summary>

Knative は最小設定を通じてウォーム状態の replica を維持でき、Standard は適切な外部シグナルとともに KEDA を使用できます。どちらのモードも可用性やレイテンシーを保証しません。readiness、ロード、容量、リカバリをテストしてください。
</details>

10. artifact URI だけではなぜ不十分であり、TorchServe はどのように扱うべきですか？

<details>
<summary>回答を表示</summary>

runtime、モデルの形式/レイアウト、library バージョン、credentials、ports、protocol が一致している必要があります。TorchServe は、セキュリティ修正の予定がなく、もはや積極的に保守されていないと述べています。したがって、古い runtime catalog エントリは、保守されたデフォルトの証拠にはなりません。
</details>

11. Pod autoscaling と EC2 scaling はどのように相互作用しますか？

<details>
<summary>回答を表示</summary>

Knative/HPA/KEDA または別の設定済み scaler が、必要な Pod 数を決定します。Kubernetes scheduling と Karpenter capacity policy は、node のプロビジョニング/回収に影響します。モデル Pod がゼロになった後も、他の workload や disruption rule により EC2 node が課金対象のままになることがあります。
</details>

---

[学習教材に戻る](../../../ai-ml/kubeflow/06-kserve.md)
