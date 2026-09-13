# Kubeflow Pipelines クイズ

このクイズでは、Kubeflow Pipelines のアーキテクチャ、KFP v2 IR YAML コンパイルモデル、コア概念（Pipeline、Component、Run、Experiment、Artifact、MLMD）、EKS における Artifact ストレージの考慮事項、およびキャッシュの動作に関する理解を確認します。

## 多肢選択問題

1. ここで使用するオープンソース KFP 2.16.1 バックエンドで、ワークフローの順序付けと Pod 作成を管理するエンジンはどれですか？
   - A) Apache Airflow
   - B) Argo Workflows
   - C) Tekton Pipelines
   - D) 基盤となるワークフローエンジンを使用せず、Kubernetes CronJobs が直接管理する

<details>

<summary>回答を表示</summary>

**回答: B) Argo Workflows**

**解説:**
このバックエンドは、Run 用の IR を Argo Workflow リソースに変換します。Argo が順序と Pod 作成を管理し、Kubernetes scheduler が Pod をノードに配置します。Pipeline をアップロードするだけでは Run は作成されません。
</details>

2. KFP v1 SDK compiler と KFP v2 SDK compiler の主なアーキテクチャ上の違いは何ですか？
   - A) v1 は IR YAML にコンパイルし、v2 は Argo Workflow YAML に直接コンパイルする
   - B) v1 は Argo Workflow YAML に直接コンパイルし、v2 はバックエンドに依存しない Intermediate Representation (IR) YAML にコンパイルする
   - C) 違いはない — 両方とも同一の出力を生成する
   - D) v2 ではコンパイルが完全に不要になった

<details>

<summary>回答を表示</summary>

**回答: B) v1 は Argo Workflow YAML に直接コンパイルし、v2 はバックエンドに依存しない Intermediate Representation (IR) YAML にコンパイルする**

**解説:**
v1 SDK の `dsl-compile` は、Argo 固有の `Workflow` YAML manifest を直接生成しました。v2 SDK は、DAG、Component、型付けされた Artifact を記述するバックエンドに依存しない IR YAML（`PipelineSpec`）にコンパイルします。このバックエンドは、バックエンドのバージョンおよびプラットフォーム拡張との互換性を前提に、Run 作成時に IR を変換します。
</details>

3. 登録済みの実行とその入力／出力 Artifact の関係を記録し、KFP UI でのリネージ追跡を可能にする Kubeflow Pipelines Component はどれですか？
   - A) Argo Workflow Controller
   - B) ML Metadata (MLMD) store
   - C) MinIO Artifact store
   - D) KFP SDK Compiler

<details>

<summary>回答を表示</summary>

**回答: B) ML Metadata (MLMD) store**

**解説:**
MLMD は、すべての外部副作用やファイルのバイト列の完全性ではなく、登録済みの実行／Artifact 関係を保存します。再現性のために、コード／データのリビジョンとハッシュを記録してください。
</details>

4. KFP v2 SDK では、Component が下流の Component で使用するために `Dataset` 種別の型付き Artifact を生成することを、どのように宣言しますか？
   - A) 通常の Python dictionary を返す
   - B) `Output[Dataset]` 型の parameter を宣言する
   - C) 型宣言なしで、ハードコードされた `/tmp/dataset.csv` パスに書き込む
   - D) `DATASET` という名前の environment variable を設定する

<details>

<summary>回答を表示</summary>

**回答: B) `Output[Dataset]` 型の parameter を宣言する**

**解説:**
KFP v2 では、Artifact は第一級の型（`Dataset`、`Model`、`Metrics` など）として扱われます。`Output[Dataset]` 型の Component parameter は型と接続を宣言します。runtime はパスを準備し、一致する `Input[Dataset]` parameter を宣言した任意の下流 Component にその Artifact を渡します。
</details>

5. 確認したデフォルトのインストールで、MinIO ではなく S3 を使用するために必要なものは何ですか？
   - A) デフォルトは S3 であり、このパターンでは MinIO に切り替える
   - B) バンドルされた MinIO ではなく S3 用に pipeline root、provider、credential chain を設定する
   - C) デフォルトの Artifact store はないため、常に手動で設定する必要がある
   - D) デフォルトは EFS であり、このパターンでは EBS に切り替える

<details>

<summary>回答を表示</summary>

**回答: B) バンドルされた MinIO ではなく S3 用に pipeline root、provider、credential chain を設定する**

**解説:**
デフォルトの bundle には MinIO が含まれていますが、ほかのインストールやインポートされた Artifact URI は異なる場合があります。最新の KFP object-store guide を使用してください。S3 には storage/request/transfer の料金がかかります。レガシーな AWS distribution guide は、検証済みの現行バージョン用インストール手順ではありません。
</details>

6. KFP の Artifact store をクラスター内の MinIO ではなく S3 に向けた場合、実際の Run 実行 ServiceAccount および Artifact にアクセスする Component に対して、どの identity mechanism が直接関係しますか？
   - A) なし — AWS identity の設定なしで S3 アクセスは機能する
   - B) SDK、trust、runtime support、およびスコープを限定した S3 permissions を検証した IRSA または Pod Identity
   - C) すべての Component の container image にハードコードした AWS access key
   - D) S3 アクセスには Kubernetes RBAC だけで十分である

<details>

<summary>回答を表示</summary>

**回答: B) SDK、trust、runtime support、およびスコープを限定した S3 permissions を検証した IRSA または Pod Identity**

**解説:**
Artifact の読み取り／書き込みがクラスター内の MinIO endpoint ではなく AWS に直接行われるようになると、KFP pipeline Pod が使用する ServiceAccount には、その S3 bucket に対する permissions を持つ IRSA role または EKS Pod Identity association が必要です。
</details>

7. 2 ステップの Pipeline 例（`prepare_data` -> `train_model`）では、`Dataset` Artifact は最初の Component から 2 番目の Component にどのように渡されますか？
   - A) 両方の Component で共有される global variable に書き込む
   - B) `train_model(input_dataset=prep_task.outputs["output_dataset"])` により、最初の Component が宣言した出力を 2 番目の Component の型付き入力に接続する
   - C) environment variable に格納する
   - D) 2 つの Component でデータを共有することはできないため、1 つの Component に統合する必要がある

<details>

<summary>回答を表示</summary>

**回答: B) `train_model(input_dataset=prep_task.outputs["output_dataset"])` により、最初の Component が宣言した出力を 2 番目の Component の型付き入力に接続する**

**解説:**
`@dsl.pipeline` でデコレートされた関数内では、`prep_task.outputs["output_dataset"]` は `prepare_data` が宣言した `Output[Dataset]` parameter を参照します。これを `train_model` の `input_dataset: Input[Dataset]` parameter に渡すことで、独立して実行される 2 つの Pod 間の Artifact dependency を SDK が接続します。
</details>

8. KFP は、Component を再実行する代わりにキャッシュ済みの結果を再利用するかどうかを、どのように判断しますか？
   - A) 入力に関係なく、常にすべての Component を再実行する
   - B) Component の入力（parameter 値、入力 Artifact 名／ID、container image／command、出力仕様および関連設定）をハッシュ化し、過去に成功した実行の一致するハッシュからキャッシュ済み出力を再利用する
   - C) Pipeline 名が変更された場合にのみ Component を再実行する
   - D) キャッシュは、前回の Run からの経過時間のみに基づく

<details>

<summary>回答を表示</summary>

**回答: B) Component の入力（parameter 値、入力 Artifact 名／ID、container image／command、出力仕様および関連設定）をハッシュ化し、過去に成功した実行の一致するハッシュからキャッシュ済み出力を再利用する**

**解説:**
2.16.1 の key は、ファイルのバイト列に対する新しいハッシュではなく、parameter 値、Artifact ID、container／出力設定を使用します。バイト列や image tag を変更しても、key が変わらない可能性があります。lookup は Pipeline 名および namespace の範囲に限定されます。

ファイルの内容、変更可能な image tag、外部 state によって key が自動的に無効化されることはありません。データバージョン／ハッシュを明示的な入力として記録するか、キャッシュを無効にしてください。
</details>

## 短答式問題

9. この章で説明した、KFP のキャッシュ動作を無効にする 2 つの方法を挙げてください。

<details>

<summary>回答を表示</summary>

**回答: Component ごとに、task 上で `set_caching_options(enable_caching=False)` を使用する方法。Run ごとに、`enable_caching=False` を指定した認証済み client submission を使用する方法。**

**解説:**
`prep_task.set_caching_options(enable_caching=False)` は、Pipeline 関数内の特定の Component task 1 つに対してキャッシュを無効にします。代わりに、Component ごとではなく Run-submission 時に Pipeline 全体の submission のキャッシュを無効にすることもできます。
</details>

10. KFP SDK のコンパイルステップは実際には何を生成し、その出力が KFP API server に到達すると何が起こりますか？

<details>

<summary>回答を表示</summary>

**回答: Intermediate Representation (IR) YAML、すなわちバックエンドに依存しない `PipelineSpec` を生成します。アップロードと Run 作成の後、このバックエンドは IR YAML を Argo `Workflow` に変換し、その Pod 作成は Argo が、ノード配置は Kubernetes が管理します。**

**解説:**
コンパイルにより IR が生成されます。package は client API と Python runtime support も提供します。Run 作成によりバックエンドのワークフロー処理が開始されます。バックエンド IR バージョンとプラットフォーム拡張には互換性が必要です。
</details>

## ハンズオン問題

11. `prepare_data` という名前の `@dsl.component` 関数を作成してください。この関数では 1 つの `Output[Dataset]` parameter を宣言し、pandas DataFrame を CSV としてそこに書き込みます。

<details>

<summary>回答を表示</summary>

**回答:**
```python
from kfp import dsl
from kfp.dsl import Dataset, Output

@dsl.component(base_image="python:3.12-slim", packages_to_install=["pandas==2.3.3"])
def prepare_data(output_dataset: Output[Dataset]):
    import pandas as pd

    df = pd.DataFrame({"feature": [1, 2, 3, 4], "label": [0, 1, 0, 1]})
    df.to_csv(output_dataset.path, index=False)
```

**解説:**
`output_dataset: Output[Dataset]` は型付き Artifact 出力を宣言します。runtime は Component が書き込む storage location として `output_dataset.path` を準備し、下流の Component はそれを `Input[Dataset]` として宣言できます。
</details>

12. `prepare_data` の出力を `train_model` Component の `input_dataset` parameter に接続する `@dsl.pipeline` 関数を作成してください。

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
`prep_task.outputs["output_dataset"]` は、`prepare_data` の `Output[Dataset]` parameter（`output_dataset` という名前）が生成する Artifact を参照します。これを `train_model` の `input_dataset` argument として渡すと、2 つの Component 間に DAG edge が作成されます。
</details>

13. `prep_task` という名前の単一 Pipeline task でキャッシュを無効にするコードを記述してください。

<details>

<summary>回答を表示</summary>

**回答:**
```python
prep_task.set_caching_options(enable_caching=False)
```

**解説:**
Pipeline 関数内で task object に対して `set_caching_options(enable_caching=False)` を呼び出すと、そのコンパイル済み task のキャッシュが無効になります。Run submission 時の明示的な enable_caching 値はこれを上書きできます。コンパイル済みの設定を保持するには、その option を None のままにしてください。
</details>

---

[学習教材に戻る](../../../ai-ml/kubeflow/02-pipelines.md) | [次のクイズ: Notebooks](./03-notebooks-quiz.md)
