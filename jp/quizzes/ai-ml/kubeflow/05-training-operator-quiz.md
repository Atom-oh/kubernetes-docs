# Kubeflow Trainer と分散トレーニングのクイズ

このクイズでは、レガシー Training Operator のフレームワーク固有 CRD、Kubeflow Trainer v2 の統合された `TrainJob`/runtime モデルへの移行、および Kubernetes 上の分散トレーニングの仕組みに関する理解を確認します。

## 選択問題

1. 2021 年に統合された、元の（v1）Training Operator の基本的なアーキテクチャ上のアプローチは何でしたか？
   - A) すべてのフレームワークで共有され、runtime 時にフレームワークを検出する単一の CRD
   - B) ML フレームワークごとに個別の CRD（例: `PyTorchJob`、`TFJob`、`MPIJob`）を用意し、それぞれにそのフレームワークの分散トレーニングのセマンティクスを実装する独自の controller を持たせる
   - C) CRD をまったく使用せず、トレーニング引数を image に組み込んだ `kubectl run` container を介して job を直接送信する
   - D) `framework` field を持つ単一の `TrainingJob` CRD と、共有の controller

<details>
<summary>回答を表示</summary>

**回答: B) ML フレームワークごとに個別の CRD（例: `PyTorchJob`、`TFJob`、`MPIJob`）を用意し、それぞれにそのフレームワークの分散トレーニングのセマンティクスを実装する独自の controller を持たせる**

**解説:**
v1 Training Operator は、`PyTorchJob`、`TFJob`、`MPIJob` など、フレームワークごとに 1 つの CRD を提供していました。それぞれは、そのフレームワーク固有の分散トレーニングの慣例（例: PyTorch の rank/env-var モデルと TensorFlow の `TF_CONFIG`）を理解する独自の controller によって支えられていました。

</details>

2. worker が `torch.distributed` process group を形成できるように、`PyTorchJob` controller はどの環境変数を inject しましたか？
   - A) `TF_CONFIG` のみ
   - B) `MASTER_ADDR`、`RANK`、`WORLD_SIZE`
   - C) `KUBEFLOW_HOST` と `KUBEFLOW_PORT`
   - D) `POD_IP` と `POD_NAMESPACE`

<details>
<summary>回答を表示</summary>

**回答: B) `MASTER_ADDR`、`RANK`、`WORLD_SIZE`**

**解説:**
`PyTorchJob` controller は各 worker Pod に `MASTER_ADDR`、`RANK`、`WORLD_SIZE` を inject し、PyTorch の `torch.distributed` 機構が process group を形成して連携できるようにしました。

</details>

3. Kubeflow Trainer v2 が v1 Training Operator と比較して導入した中心的なアーキテクチャ上の変更は何ですか？
   - A) 既存のフレームワーク固有 CRD の上に、さらに多くのフレームワーク固有 CRD を追加する
   - B) フレームワークごとの CRD を、統合された `TrainJob` API と再利用可能な `TrainingRuntime`/`ClusterTrainingRuntime` template に置き換える
   - C) controller の必要性を完全になくし、admission webhook のみに依存する
   - D) `TrainJob` と `ClusterTrainingRuntime` を、再びフレームワークごとの単一 CRD に統合する

<details>
<summary>回答を表示</summary>

**回答: B) フレームワークごとの CRD を、統合された `TrainJob` API と再利用可能な `TrainingRuntime`/`ClusterTrainingRuntime` template に置き換える**

**解説:**
Trainer v2 は、フレームワークごとに CRD と controller を 1 つずつ用意する代わりに、`TrainJob`（何を実行するか）と `TrainingRuntime`/`ClusterTrainingRuntime`（どのように実行するか — 再利用可能でフレームワーク固有の実行 template）を導入し、job の送信を分散起動の仕組みから分離します。

</details>

4. `TrainJob` / `ClusterTrainingRuntime` の分割において、通常は platform team が所有し、多くの個別トレーニング実行で再利用する object はどれですか？
   - A) `TrainJob`
   - B) `ClusterTrainingRuntime`
   - C) どちらも常に実行ごとに新規作成される
   - D) どちらでもない — 代わりに `PyTorchJob` が作成される

<details>
<summary>回答を表示</summary>

**回答: B) `ClusterTrainingRuntime`**

**解説:**
`ClusterTrainingRuntime`（または namespace-scoped の `TrainingRuntime`）は、container image と分散起動の仕組みを定義する、platform team が一度定義する再利用可能な template です。個々の TrainJob は kind/name を参照し、許可された実行固有の設定を指定します。numNodes はトレーニング Pod 数であり、必ずしも EC2 instance 数ではありません。

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
Kubeflow Trainer の [release notes](https://github.com/kubeflow/trainer/releases) によると、v2.2（2026 年 3 月 20 日リリース）では、既存の PyTorch support に加え、Flux policy/integration とともに JAX および XGBoost training runtime の first-class support が追加されました。trainerStatus は alpha の TrainJobStatus-gated feature で、default では無効になっており、明示的な application reporting が必要です。

</details>

6. Kubeflow Community Distribution 26.03.1 release 時点での、v1 から Trainer v2 への migration の現状を最も正確に表す記述はどれですか？
   - A) migration は完全に完了しており、レガシー Training Operator はすべての distribution から削除されている
   - B) レガシー Training Operator（1.9.2）は 26.03.1 distribution で Trainer v2 とともに引き続き bundled されており、レガシー job と TrainJob には個別に検証された migration が必要である
   - C) Kubeflow Trainer v2 は非推奨となり、v1 CRD に戻された
   - D) `TrainJob` と `PyTorchJob` は同一の CRD に対する単なる 2 つの名称である

<details>
<summary>回答を表示</summary>

**回答: B) レガシー Training Operator（1.9.2）は 26.03.1 distribution で Trainer v2 とともに引き続き bundled されており、レガシー job と TrainJob には個別に検証された migration が必要である**

**解説:**
Kubeflow Community Distribution 26.03.1 は、Trainer v2 と並行してレガシー Training Operator 1.9.2 を引き続き提供しています。これは両方の API が提供されていることを示しており、特定の team の migration の進捗を示すものではありません。

</details>

7. 任意の gang scheduling が同期分散トレーニングに役立つことがあるのはなぜですか？
   - A) Kubernetes では、default で namespace 内のすべての Pod を gang-scheduled にする必要があるため
   - B) job が通信に必要なすべての worker を取得できない間の、部分的な resource allocation を減らせるため
   - C) gang scheduling は stateless web workload にのみ必要であるため
   - D) cloud provider によって課される課金要件であるため

<details>
<summary>回答を表示</summary>

**回答: B) job が通信に必要なすべての worker を取得できない間の、部分的な resource allocation を減らせるため**

**解説:**
固定サイズの同期 job では、rendezvous 時に必要な process がそろっている必要があります。Trainer は gang scheduling を自動では有効にしません。default Torch runtime には podGroupPolicy がありません。scheduler/CRD/policy は別途設定してください。順次 node provisioning は timeout 範囲内で成功する可能性があります。

</details>

## 記述問題

8. Kubernetes 上で multi-worker 分散トレーニング job を連携させる際に、headless Service はどのような役割を果たしますか？

<details>
<summary>回答を表示</summary>

**回答:** 各 worker Pod に安定して名前解決可能な DNS 名を与え、再 schedule 時に変わる可能性がある Pod IP に依存せず、他の worker がその Pod を検出できるようにします。

**解説:**
分散トレーニングの worker は互いを確実に検出する必要があります。worker Pod の前に配置する headless Service は、適切な Pod naming/hostname/subdomain と networking による DNS ベースの検出をサポートします。process state や IP を保持するものではありません。

</details>

9. このドキュメントの Katib cross-reference において、Katib Trial 内で `TrainJob` はどのような役割を果たしますか？

<details>
<summary>回答を表示</summary>

**回答:** 互換性のある template、runtime、status conditions、metric collection があれば、Katib は各 Trial に対して TrainJob を作成し、その Trial で選択された hyperparameter 値を script arguments として inject して、報告された metrics を読み取り search を導きます。

**解説:**
Katib 自体は分散起動の仕組みを知る必要はありません。platform team がすでに定義した runtime に対して Trial ごとに `TrainJob` を生成するため、hyperparameter-search logic はトレーニング実行の仕組みから分離された状態に保たれます。

</details>

10. このドキュメントに頼るのではなく、既存の v1 CRD manifest（例: `PyTorchJob`）を Kubeflow Trainer v2 に migration する際の、field ごとの authoritative reference はどこで確認すべきですか？

<details>
<summary>回答を表示</summary>

**回答:** kubeflow.org の「Migrating to Kubeflow Trainer v2」guide。

**解説:**
このドキュメントでは概念上の移行と仕組みを高レベルで扱っていますが、すべての migration step を意図的に再記載してはいません。[pinned official guide](https://github.com/kubeflow/trainer/blob/v2.3.0/docs/operator-guides/migration.md) は PyTorchJob の例を提供しており、すべての framework/field に対する網羅的な mapping ではありません。実際の launch roles、retries、storage、networking を比較してください。

</details>

---

[学習教材に戻る](../../../ai-ml/kubeflow/05-training-operator.md)
