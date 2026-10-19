# Kubeflow Trainer と分散トレーニングのクイズ

このクイズでは、レガシーな Training Operator のフレームワーク固有 CRD、Kubeflow Trainer v2 で導入された統一的な `TrainJob`/ランタイムモデルへの移行、および Kubernetes 上の分散トレーニングの仕組みに関する理解を確認します。

## 選択問題

1. 2021 年に統合された、元の（v1）Training Operator の基本的なアーキテクチャ上のアプローチは何でしたか？
   - A) すべてのフレームワークで共有され、実行時にフレームワークを検出する単一の CRD
   - B) ML フレームワークごとに個別の CRD（例: `PyTorchJob`、`TFJob`、`MPIJob`）を用意し、それぞれにフレームワーク固有の分散トレーニングの動作を実装する独自のコントローラーを持たせる
   - C) CRD をまったく使用せず、トレーニング引数をイメージに組み込んだ `kubectl run` コンテナを使ってジョブを直接送信する
   - D) `framework` フィールドを持つ単一の `TrainingJob` CRD と、共有のコントローラー

<details>
<summary>回答を表示</summary>

**回答: B) ML フレームワークごとに個別の CRD（例: `PyTorchJob`、`TFJob`、`MPIJob`）を用意し、それぞれにフレームワーク固有の分散トレーニングの動作を実装する独自のコントローラーを持たせる**

**解説:**
v1 Training Operator は、`PyTorchJob`、`TFJob`、`MPIJob` など、フレームワークごとに 1 つの CRD を提供していました。それぞれに専用のコントローラーがあり、各フレームワーク固有の分散トレーニングの慣例（例: PyTorch の rank と環境変数のモデル、TensorFlow の `TF_CONFIG`）を処理していました。

</details>

2. ワーカーが `torch.distributed` のプロセスグループを形成できるように、`PyTorchJob` コントローラーはどの環境変数を注入しましたか？
   - A) `TF_CONFIG` のみ
   - B) `MASTER_ADDR`、`RANK`、`WORLD_SIZE`
   - C) `KUBEFLOW_HOST` と `KUBEFLOW_PORT`
   - D) `POD_IP` と `POD_NAMESPACE`

<details>
<summary>回答を表示</summary>

**回答: B) `MASTER_ADDR`、`RANK`、`WORLD_SIZE`**

**解説:**
`PyTorchJob` コントローラーは各ワーカー Pod に `MASTER_ADDR`、`RANK`、`WORLD_SIZE` を注入し、PyTorch の `torch.distributed` 機構がプロセスグループを形成して連携できるようにしました。

</details>

3. Kubeflow Trainer v2 が v1 Training Operator と比較して導入した中心的なアーキテクチャ上の変更は何ですか？
   - A) 既存のフレームワーク固有 CRD に加えて、さらに別のフレームワーク固有 CRD を追加する
   - B) フレームワークごとの CRD を、統合された `TrainJob` API と再利用可能な `TrainingRuntime`/`ClusterTrainingRuntime` テンプレートに置き換える
   - C) コントローラーを不要にし、アドミッション Webhook のみに依存する
   - D) `TrainJob` と `ClusterTrainingRuntime` を、再びフレームワークごとの単一 CRD に統合する

<details>
<summary>回答を表示</summary>

**回答: B) フレームワークごとの CRD を、統合された `TrainJob` API と再利用可能な `TrainingRuntime`/`ClusterTrainingRuntime` テンプレートに置き換える**

**解説:**
Trainer v2 は、フレームワークごとに CRD とコントローラーを用意する方式に代えて、`TrainJob`（何を実行するか）と `TrainingRuntime`/`ClusterTrainingRuntime`（どのように実行するか — 再利用可能なフレームワーク固有の実行テンプレート）を導入し、ジョブの投入を分散起動の仕組みから分離します。

</details>

4. `TrainJob` / `ClusterTrainingRuntime` の分割において、通常はプラットフォームチームが所有し、多くの個別トレーニング実行で再利用するオブジェクトはどれですか？
   - A) `TrainJob`
   - B) `ClusterTrainingRuntime`
   - C) どちらも常に実行ごとに新規作成される
   - D) どちらでもない — 代わりに `PyTorchJob` を作成する

<details>
<summary>回答を表示</summary>

**回答: B) `ClusterTrainingRuntime`**

**解説:**
`ClusterTrainingRuntime`（または namespace 単位の `TrainingRuntime`）は、コンテナイメージと分散起動の仕組みを定義する、プラットフォームチームが一度作成して再利用するテンプレートです。個々の TrainJob はリソース種別と名前を参照し、許可された実行固有の設定を指定します。`numNodes` はトレーニング Pod 数であり、必ずしも EC2 インスタンス数ではありません。

</details>

5. Kubeflow Trainer v2.2 で正式にサポートされた追加のトレーニングランタイム 2 つはどれですか？
   - A) TensorFlow と MXNet
   - B) JAX と XGBoost
   - C) Scikit-learn と ONNX
   - D) Spark MLlib と H2O

<details>
<summary>回答を表示</summary>

**回答: B) JAX と XGBoost**

**解説:**
Kubeflow Trainer の[リリースノート](https://github.com/kubeflow/trainer/releases) によると、v2.2（2026 年 3 月 20 日リリース）では、既存の PyTorch サポートに加え、Flux ポリシーとの統合とともに JAX および XGBoost のトレーニングランタイムが正式にサポートされました。`trainerStatus` は `TrainJobStatus` によって有効化される alpha 機能で、デフォルトでは無効です。使用するにはアプリケーションから明示的に状態を報告する必要があります。

</details>

6. Kubeflow Community Distribution 26.03.1 のリリース時点で、v1 から Trainer v2 への移行状況を最も正確に表す記述はどれですか？
   - A) 移行は完全に完了しており、レガシー Training Operator はすべてのディストリビューションから削除されている
   - B) レガシー Training Operator（1.9.2）は 26.03.1 ディストリビューションにも Trainer v2 とともに引き続き同梱されており、レガシーなジョブから TrainJob への移行は別途検証が必要である
   - C) Kubeflow Trainer v2 は非推奨となり、v1 CRD に戻された
   - D) `TrainJob` と `PyTorchJob` は同一の CRD に対する単なる 2 つの名称である

<details>
<summary>回答を表示</summary>

**回答: B) レガシー Training Operator（1.9.2）は 26.03.1 ディストリビューションにも Trainer v2 とともに引き続き同梱されており、レガシーなジョブから TrainJob への移行は別途検証が必要である**

**解説:**
Kubeflow Community Distribution 26.03.1 には、Trainer v2 とともにレガシー Training Operator 1.9.2 も引き続き含まれています。これは両方の API が提供されていることを示すもので、特定のチームにおける移行の進捗を示すものではありません。

</details>

7. 任意のギャングスケジューリングが同期分散トレーニングに役立つことがあるのはなぜですか？
   - A) Kubernetes では、デフォルトで名前空間内のすべての Pod にギャングスケジューリングを適用する必要があるため
   - B) ジョブが通信に必要なすべてのワーカーを確保できない間、リソースが一部だけ割り当てられる状況を減らせるため
   - C) ギャングスケジューリングはステートレスな Web ワークロードにのみ必要であるため
   - D) クラウドプロバイダーが課す課金要件であるため

<details>
<summary>回答を表示</summary>

**回答: B) ジョブが通信に必要なすべてのワーカーを確保できない間、リソースが一部だけ割り当てられる状況を減らせるため**

**解説:**
固定サイズの同期ジョブでは、ランデブー時に必要なプロセスがすべてそろっている必要があります。Trainer はギャングスケジューリングを自動では有効にしません。デフォルトの Torch ランタイムには `podGroupPolicy` がありません。スケジューラー、CRD、ポリシーは別途設定してください。ノードを順次プロビジョニングする方法でも、タイムアウトの範囲内で成功する場合があります。

</details>

## 記述問題

8. Kubernetes 上で複数ワーカーによる分散トレーニングジョブを連携させる際に、headless Service はどのような役割を果たしますか？

<details>
<summary>回答を表示</summary>

**回答:** 各ワーカー Pod に安定して名前解決できる DNS 名を与えます。これにより、再スケジュール時に変わる可能性がある Pod IP に依存せず、他のワーカーがその Pod を検出できます。

**解説:**
分散トレーニングのワーカーは、互いを確実に検出する必要があります。ワーカー Pod の前に headless Service を配置すると、Pod の名前、hostname/subdomain、ネットワークが適切に設定されている場合に DNS で検出できます。プロセスの状態や IP アドレスを保持するものではありません。

</details>

9. このドキュメントの Katib との関連記述では、Katib Trial 内で `TrainJob` はどのような役割を果たしますか？

<details>
<summary>回答を表示</summary>

**回答:** 互換性のあるテンプレート、ランタイム、ステータス条件、メトリクス収集機能があれば、Katib は Trial ごとに TrainJob を作成し、その Trial で選択されたハイパーパラメータ値をスクリプト引数として渡します。Katib は報告されたメトリクスを読み取り、探索を進めます。

**解説:**
Katib 自体が分散起動の仕組みを知る必要はありません。プラットフォームチームが定義したランタイムを使って Trial ごとに `TrainJob` を作成するため、ハイパーパラメータ探索のロジックをトレーニング実行の仕組みから分離できます。

</details>

10. このドキュメントに頼るのではなく、既存の v1 CRD マニフェスト（例: `PyTorchJob`）を Kubeflow Trainer v2 に移行するときに参照すべき、フィールドごとの公式資料はどこで確認すべきですか？

<details>
<summary>回答を表示</summary>

**回答:** kubeflow.org の「Migrating to Kubeflow Trainer v2」ガイドです。

**解説:**
このドキュメントは概念と仕組みを概要レベルで扱い、すべての移行手順を再掲するものではありません。[バージョンを固定した公式ガイド](https://github.com/kubeflow/trainer/blob/v2.3.0/docs/operator-guides/migration.md) には PyTorchJob の例がありますが、すべてのフレームワークやフィールドを網羅した対応表ではありません。実際の起動時の役割、再試行、ストレージ、ネットワークを比較してください。

</details>

---

[学習教材に戻る](../../../ai-ml/kubeflow/05-training-operator.md)
