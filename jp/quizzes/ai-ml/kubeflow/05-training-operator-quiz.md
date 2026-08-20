# Kubeflow Trainer と分散トレーニングのクイズ

このクイズでは、レガシー Training Operator のフレームワーク固有の CRD、Kubeflow Trainer v2 の統一された `TrainJob`/runtime モデルへの移行、および Kubernetes 上の分散トレーニングの仕組みに関する理解を確認します。

## 選択問題

1. 2021 年に統合された、元の（v1）Training Operator の基本的なアーキテクチャのアプローチは何でしたか？
   - A) すべてのフレームワークで共有する単一の CRD を使用し、runtime にフレームワークを検出する
   - B) ML フレームワークごとに個別の CRD（例: `PyTorchJob`、`TFJob`、`MPIJob`）を使用し、それぞれにそのフレームワークの分散トレーニングのセマンティクスを実装する独自の controller がある
   - C) CRD をまったく使用せず、トレーニング引数をイメージに組み込んだ `kubectl run` container で Job を直接送信する
   - D) `framework` フィールドを持つ単一の `TrainingJob` CRD を使用するが、controller は 1 つだけを共有する

<details>
<summary>回答を表示</summary>

**回答: B) ML フレームワークごとに個別の CRD（例: `PyTorchJob`、`TFJob`、`MPIJob`）を使用し、それぞれにそのフレームワークの分散トレーニングのセマンティクスを実装する独自の controller がある**

**解説:**
v1 Training Operator では、`PyTorchJob`、`TFJob`、`MPIJob` など、フレームワークごとに 1 つの CRD が提供され、それぞれは特定のフレームワークの分散トレーニングの慣例（例: PyTorch の rank/env-var モデルと TensorFlow の `TF_CONFIG`）を理解する独自の controller によって支えられていました。

</details>

2. worker が `torch.distributed` process group を形成できるように、`PyTorchJob` controller はどの environment variable を注入しましたか？
   - A) `TF_CONFIG` のみ
   - B) `MASTER_ADDR`、`RANK`、`WORLD_SIZE`
   - C) `KUBEFLOW_HOST` と `KUBEFLOW_PORT`
   - D) `POD_IP` と `POD_NAMESPACE`

<details>
<summary>回答を表示</summary>

**回答: B) `MASTER_ADDR`、`RANK`、`WORLD_SIZE`**

**解説:**
`PyTorchJob` controller は、各 worker Pod に `MASTER_ADDR`、`RANK`、`WORLD_SIZE` を注入し、PyTorch の `torch.distributed` 機構が process group を形成して連携できるようにしました。

</details>

3. v1 Training Operator と比較して、Kubeflow Trainer v2 によって導入された中心的なアーキテクチャ変更は何ですか？
   - A) 既存のフレームワーク固有の CRD に加えて、さらに多くのフレームワーク固有の CRD を追加する
   - B) フレームワークごとの CRD を、統一された `TrainJob` API と再利用可能な `TrainingRuntime`/`ClusterTrainingRuntime` template に置き換える
   - C) controller が不要になり、admission webhook のみを使用する
   - D) `TrainJob` と `ClusterTrainingRuntime` を、フレームワークごとの単一の CRD に再統合する

<details>
<summary>回答を表示</summary>

**回答: B) フレームワークごとの CRD を、統一された `TrainJob` API と再利用可能な `TrainingRuntime`/`ClusterTrainingRuntime` template に置き換える**

**解説:**
Trainer v2 では、フレームワークごとに CRD と controller を 1 つずつ設ける代わりに、`TrainJob`（何を実行するか）と `TrainingRuntime`/`ClusterTrainingRuntime`（どのように実行するか — 再利用可能でフレームワーク固有の実行 template）を導入し、Job の送信を分散起動の仕組みから分離します。

</details>

4. `TrainJob` / `ClusterTrainingRuntime` の分割において、通常は platform team が所有し、多数の個別トレーニング実行で再利用する object はどれですか？
   - A) `TrainJob`
   - B) `ClusterTrainingRuntime`
   - C) どちらも常に実行ごとに新しく作成される
   - D) どちらでもない — 代わりに `PyTorchJob` が作成される

<details>
<summary>回答を表示</summary>

**回答: B) `ClusterTrainingRuntime`**

**解説:**
`ClusterTrainingRuntime`（または namespace-scoped の `TrainingRuntime`）は、container image と分散起動の仕組みを含めて platform team が一度定義する再利用可能な template です。個々の `TrainJob` は名前でこれを参照し、実行固有の script、引数、worker 数のみを指定します。

</details>

5. Kubeflow Trainer v2.2 は、どの 2 つの追加トレーニング runtime に first-class support を追加しましたか？
   - A) TensorFlow と MXNet
   - B) JAX と XGBoost
   - C) Scikit-learn と ONNX
   - D) Spark MLlib と H2O

<details>
<summary>回答を表示</summary>

**回答: B) JAX と XGBoost**

**解説:**
Kubeflow Trainer の [release notes](https://github.com/kubeflow/trainer/releases)によると、v2.2（2026 年 3 月頃にリリース）では、既存の PyTorch support に加えて JAX および XGBoost のトレーニング runtime に first-class support が追加され、observability の強化と HPC スタイルの workload 向け Flux Framework integration も行われました。

</details>

6. Kubeflow Community Distribution 26.03 リリース時点での、v1 から Trainer v2 への移行の現状を最も正確に説明しているものはどれですか？
   - A) 移行は完全に完了しており、レガシー Training Operator はすべての distribution から削除されている
   - B) レガシー Training Operator（1.9.2）は 26.03 distribution で Trainer v2 とともに引き続き同梱されており、既存の Job を `TrainJob` に移行する作業は多くの team にとって現在も進行中の移行である
   - C) Kubeflow Trainer v2 は廃止され、v1 CRD に戻された
   - D) `TrainJob` と `PyTorchJob` は、同一の CRD に対する 2 つの名称にすぎない

<details>
<summary>回答を表示</summary>

**回答: B) レガシー Training Operator（1.9.2）は 26.03 distribution で Trainer v2 とともに引き続き同梱されており、既存の Job を `TrainJob` に移行する作業は多くの team にとって現在も進行中の移行である**

**解説:**
Kubeflow Community Distribution 26.03 では、レガシー Training Operator 1.9.2 が Trainer v2 とともに引き続き提供されています。これは両者が共存しており、多くの team が `TrainJob` への完全な移行を完了しておらず、移行の途中にあることを示しています。

</details>

7. 分散トレーニング Job で通常 gang scheduling が必要なのはなぜですか？
   - A) Kubernetes では、namespace 内のすべての Pod をデフォルトで gang scheduling する必要があるため
   - B) 通常、トレーニングを開始する前にすべての worker をまとめて schedule し、実行する必要があるため。部分的な scheduling は GPU capacity を無駄にし、deadlock を引き起こす可能性がある
   - C) gang scheduling は stateless web workload にのみ必要なため
   - D) cloud provider が課す課金要件であるため

<details>
<summary>回答を表示</summary>

**回答: B) 通常、トレーニングを開始する前にすべての worker をまとめて schedule し、実行する必要があるため。部分的な scheduling は GPU capacity を無駄にし、deadlock を引き起こす可能性がある**

**解説:**
必要な worker の一部しか schedule されない分散トレーニング Job は、残りの worker を無期限に待機する可能性があり、確保済みの GPU capacity を無駄にし、deadlock に陥るおそれがあります。gang-scheduling primitive は、この問題を回避するために Job の Pod を全か無かの scheduling unit としてグループ化します。

</details>

## 短答問題

8. Kubernetes 上の複数 worker による分散トレーニング Job を連携させる際に、headless Service はどのような役割を果たしますか？

<details>
<summary>回答を表示</summary>

**回答:** 各 worker Pod に安定して名前解決できる DNS name を提供することで、再 schedule 時に変わる可能性のある Pod IP に依存せず、他の worker がその Pod を検出できるようにします。

**解説:**
分散トレーニングの worker は相互を確実に検出する必要があります。worker Pod の前に配置された headless Service は、個々の Pod の再 scheduling 後も維持される、安定した DNS ベースの検出機能を提供します。

</details>

9. このドキュメントから参照されている Katib において、Katib Trial 内で `TrainJob` はどのような役割を果たしますか？

<details>
<summary>回答を表示</summary>

**回答:** Katib は通常、各 Trial の基盤となるトレーニング Job として `TrainJob` を template 化し、その Trial で選択された hyperparameter 値を script 引数として注入して、報告された metrics を読み戻し、検索を導きます。

**解説:**
Katib 自体は分散起動の仕組みを認識する必要はありません。platform team がすでに定義した runtime を対象に Trial ごとに `TrainJob` を作成するため、hyperparameter 検索ロジックをトレーニング実行の仕組みから分離した状態に保てます。

</details>

10. 既存の v1 CRD manifest（例: `PyTorchJob`）を Kubeflow Trainer v2 に移行する際の、フィールド単位の正式なリファレンスを、このドキュメントに依存せずに確認するにはどこにアクセスすべきですか？

<details>
<summary>回答を表示</summary>

**回答:** kubeflow.org の「Migrating to Kubeflow Trainer v2」ガイド。

**解説:**
このドキュメントでは、概念的な変更と仕組みを高レベルで説明していますが、すべての移行手順を意図的に繰り返してはいません。具体的なフィールド単位の対応付けについては、公式の kubeflow.org 移行ガイドが正式な情報源です。

</details>

---

[学習教材に戻る](../../../ai-ml/kubeflow/05-training-operator.md)
