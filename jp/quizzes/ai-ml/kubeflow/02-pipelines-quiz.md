# Kubeflow Pipelines クイズ

このクイズでは、Kubeflow Pipelines のアーキテクチャ、KFP v2 IR YAML コンパイルモデル、主要概念（Pipeline、Component、Run、Experiment、Artifact、MLMD）、EKS での Artifact ストレージに関する考慮事項、およびキャッシュ動作についての理解を確認します。

## 選択式問題

1. Kubeflow Pipelines backend は、pipeline のステップに対する Pods のスケジューリングと実行を実際に行うために、内部でどの workflow engine を使用しますか？
   - A) Apache Airflow
   - B) Argo Workflows
   - C) Tekton Pipelines
   - D) 基盤となる workflow engine を使わず、直接 Kubernetes CronJobs を使用する

<details>

<summary>回答を表示</summary>

**回答: B) Argo Workflows**

**解説:**
KFP の backend は Argo Workflows 上に構築されています。コンパイル済み pipeline が KFP API server に到達すると、Argo `Workflow` resource に変換され、Argo の controller が Pods を作成して順序付けます。KFP はその上に Python SDK、UI、Experiment/Run の追跡、MLMD store を重ねています。
</details>

2. KFP v1 SDK compiler と KFP v2 SDK compiler の主要なアーキテクチャ上の違いは何ですか？
   - A) v1 は IR YAML にコンパイルし、v2 は直接 Argo Workflow YAML にコンパイルする
   - B) v1 は直接 Argo Workflow YAML にコンパイルし、v2 は backend 非依存の Intermediate Representation (IR) YAML にコンパイルする
   - C) 違いはない — 両方とも同一の出力を生成する
   - D) v2 ではコンパイルが完全に不要になった

<details>

<summary>回答を表示</summary>

**回答: B) v1 は直接 Argo Workflow YAML にコンパイルし、v2 は backend 非依存の Intermediate Representation (IR) YAML にコンパイルする**

**解説:**
v1 SDK の `dsl-compile` は、Argo 固有の `Workflow` YAML manifest を直接生成しました。v2 SDK は、DAG、components、型付き artifacts を記述する backend 非依存の IR YAML（`PipelineSpec`）にコンパイルします。KFP backend は submission 時にその IR を Argo `Workflow` に変換します。
</details>

3. 各 Component の実行、その inputs/outputs、および使用した artifacts をすべて記録し、KFP UI での lineage tracing を可能にする Kubeflow Pipelines の component はどれですか？
   - A) Argo Workflow Controller
   - B) ML Metadata (MLMD) store
   - C) MinIO artifact store
   - D) KFP SDK Compiler

<details>

<summary>回答を表示</summary>

**回答: B) ML Metadata (MLMD) store**

**解説:**
MLMD（通常は MySQL-backed）は、各 Component の実行を、その inputs、outputs、使用した artifacts とともに記録します。これにより、KFP UI は、学習済み model を、実行をまたいでそれを生成した正確な dataset と code までさかのぼって追跡できます。
</details>

4. KFP v2 SDK では、downstream components が利用する `Dataset` 種別の型付き artifact を生成することを Component が宣言するには、どのようにしますか？
   - A) 単純な Python dictionary を返す
   - B) `Output[Dataset]` 型の parameter を宣言する
   - C) 型を宣言せずにハードコードされた `/tmp/dataset.csv` path に書き込む
   - D) `DATASET` という名前の environment variable を設定する

<details>

<summary>回答を表示</summary>

**回答: B) `Output[Dataset]` 型の parameter を宣言する**

**解説:**
KFP v2 では artifacts にファーストクラスの型（`Dataset`、`Model`、`Metrics` など）が与えられます。`Output[Dataset]` 型の Component parameter は、storage path を用意し、その artifact を一致する `Input[Dataset]` parameter を宣言する任意の downstream Component に接続するよう SDK に指示します。
</details>

5. 何も再設定しなかった場合の KFP のデフォルト artifact storage backend は何ですか？また、`awslabs/kubeflow-manifests` project の S3 パターンはそれをどのように変更しますか？
   - A) デフォルトは S3 であり、パターンは MinIO に切り替える
   - B) デフォルトは in-cluster MinIO deployment であり、パターンは代わりに S3 を使用するよう pipeline root と artifact store credentials を再設定する
   - C) デフォルトの artifact store は存在しない — 常に手動で設定する必要がある
   - D) デフォルトは EFS であり、パターンは EBS に切り替える

<details>

<summary>回答を表示</summary>

**回答: B) デフォルトは in-cluster MinIO deployment であり、パターンは代わりに S3 を使用するよう pipeline root と artifact store credentials を再設定する**

**解説:**
KFP には、デフォルト artifact store として in-cluster MinIO deployment が含まれています。EKS では、これは S3 がすでに提供している機能を重複して提供する、追加の stateful service を実行することを意味します。`awslabs/kubeflow-manifests` は、Components が S3 に直接 read/write できるように pipeline root と artifact credentials を再設定する方法を説明しています。
</details>

6. KFP の artifact store が in-cluster MinIO ではなく S3 を指すようになると、KFP pipeline pods（たとえば `pipeline-runner` ServiceAccount）にとって直接関係する identity mechanism は何ですか？
   - A) なし — AWS identity configuration がなくても S3 access は機能する
   - B) IRSA または EKS Pod Identity。これにより ServiceAccount に S3 bucket に対する permissions を付与する
   - C) 各 Component の container image にハードコードされた AWS access key
   - D) S3 access には Kubernetes RBAC だけで十分である

<details>

<summary>回答を表示</summary>

**回答: B) IRSA または EKS Pod Identity。これにより ServiceAccount に S3 bucket に対する permissions を付与する**

**解説:**
artifact の read/write が in-cluster MinIO endpoint ではなく直接 AWS に対して行われるようになると、KFP pipeline pods が使用する ServiceAccount には、その S3 bucket に対する permissions を持つ IRSA role または EKS Pod Identity association が必要です。
</details>

7. 2 ステップ pipeline の例（`prepare_data` -> `train_model`）では、`Dataset` artifact は最初の Component から 2 番目の Component にどのように渡されますか？
   - A) 両方の Components で共有される global variable に書き込む
   - B) `train_model(input_dataset=prep_task.outputs["output_dataset"])` を介して、最初の Component の宣言済み output を 2 番目の型付き input に接続する
   - C) environment variable に保存する
   - D) 2 つの Components は data を共有できないため、1 つの Component に統合する必要がある

<details>

<summary>回答を表示</summary>

**回答: B) `train_model(input_dataset=prep_task.outputs["output_dataset"])` を介して、最初の Component の宣言済み output を 2 番目の型付き input に接続する**

**解説:**
`@dsl.pipeline` decorator を付与した function 内で、`prep_task.outputs["output_dataset"]` は `prepare_data` の宣言済み `Output[Dataset]` parameter を参照します。これを `train_model` の `input_dataset: Input[Dataset]` parameter に渡すことで、SDK は独立して実行される 2 つの Pods 間の artifact dependency を接続します。
</details>

8. KFP は、Component を再実行するのではなくキャッシュされた result を再利用するかどうかをどのように決定しますか？
   - A) inputs に関係なく常にすべての Components を再実行する
   - B) Component の inputs（parameter values、input artifact content、および Component 自身の定義）を hash 化し、過去に成功した実行で一致する hash があれば cached outputs を再利用する
   - C) pipeline name が変更された場合にのみ Components を再実行する
   - D) caching は前回の実行からの wall-clock time のみに基づく

<details>

<summary>回答を表示</summary>

**回答: B) Component の inputs（parameter values、input artifact content、および Component 自身の定義）を hash 化し、過去に成功した実行で一致する hash があれば cached outputs を再利用する**

**解説:**
KFP は Component の実行を、その inputs を hash 化することでキャッシュします。一致する input hash を持つ Component を後続の Run で submission すると、再実行をスキップして以前にキャッシュされた outputs を再利用します。
</details>

## 短答問題

9. この章で説明した KFP の caching behavior を無効化する 2 つの方法を挙げてください。

<details>

<summary>回答を表示</summary>

**回答: Component ごとに、task に対する `set_caching_options(enable_caching=False)` を使用する。Run ごとに、KFP UI の Run submission dialog にある caching toggle を使用する。**

**解説:**
`prep_task.set_caching_options(enable_caching=False)` は、pipeline function 内の 1 つの特定の Component task の caching を無効化します。あるいは、Component ごとではなく Run submission 時に、pipeline submission 全体の caching を無効化できます。
</details>

10. KFP SDK の compilation step は実際には何を生成し、その output が KFP API server に到達した後はどうなりますか？

<details>

<summary>回答を表示</summary>

**回答: Intermediate Representation (IR) YAML、すなわち backend 非依存の `PipelineSpec` を生成します。API server に到達すると、backend はその IR YAML を Argo `Workflow` に変換し、Argo の controller がそれを Pods としてスケジュールします。**

**解説:**
KFP SDK の役割は IR YAML の生成で終わります。API server 以降のすべて、すなわち Argo Workflow への変換と Pod のスケジューリングは backend の責任です。これにより、IR YAML は原則として backend 非依存になります。
</details>

## ハンズオン問題

11. `Output[Dataset]` parameter を 1 つ宣言し、pandas DataFrame を CSV としてそこに書き込む、`prepare_data` という名前の `@dsl.component` function を作成してください。

<details>

<summary>回答を表示</summary>

**回答:**
```python
from kfp import dsl
from kfp.dsl import Dataset, Output

@dsl.component(base_image="python:3.11-slim")
def prepare_data(output_dataset: Output[Dataset]):
    import pandas as pd

    df = pd.DataFrame({"feature": [1, 2, 3, 4], "label": [0, 1, 0, 1]})
    df.to_csv(output_dataset.path, index=False)
```

**解説:**
`output_dataset: Output[Dataset]` は型付き artifact output を宣言します。SDK は Component が書き込む storage location として `output_dataset.path` を用意し、downstream components はそれを `Input[Dataset]` として宣言できます。
</details>

12. `prepare_data` の output を `train_model` Component の `input_dataset` parameter に接続する `@dsl.pipeline` function を作成してください。

<details>

<summary>回答を表示</summary>

**回答:**
```python
from kfp import dsl

@dsl.pipeline(name="data-prep-train-pipeline")
def data_prep_train_pipeline():
    prep_task = prepare_data()
    train_task = train_model(input_dataset=prep_task.outputs["output_dataset"])
```

**解説:**
`prep_task.outputs["output_dataset"]` は、`prepare_data` の `Output[Dataset]` parameter（`output_dataset` という名前）が生成する artifact を参照します。これを `train_model` の `input_dataset` argument として渡すと、2 つの Components 間に DAG edge が作成されます。
</details>

13. `prep_task` という名前の単一 pipeline task の caching を無効化する code を記述してください。

<details>

<summary>回答を表示</summary>

**回答:**
```python
prep_task.set_caching_options(enable_caching=False)
```

**解説:**
pipeline function 内で task object に対して `set_caching_options(enable_caching=False)` を呼び出すと、その特定の Component の実行に対する caching が無効化され、以前の Run に一致する cached result が存在しても強制的に再実行されます。
</details>

---

[学習教材に戻る](../../../ai-ml/kubeflow/02-pipelines.md) | [次のクイズ: Notebooks](./03-notebooks-quiz.md)
