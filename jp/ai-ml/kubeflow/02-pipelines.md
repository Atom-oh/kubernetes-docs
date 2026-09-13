# パート 2: Kubeflow Pipelines

> **サポート対象バージョン**: Kubeflow Pipelines 2.16.1, Kubeflow Community Distribution 26.03.1
> **最終更新**: September 12, 2026

## ラボ環境のセットアップ

ローカルでのコンパイルには Python と `kfp==2.16.1` が必要です。この章は Python 3.12 で確認しました。コンパイル時にクラスターへ接続することはありません。リモート実行には、互換性のある KFP backend、認証済みクライアント、および namespace の権限が必要です。S3 ではさらに、実際に実行する ServiceAccount と artifact にアクセスするコンポーネント向けの workload identity が必要です。

## Kubeflow Pipelines とは

KFP は、型付けされた parameter/artifact を使用してコンポーネントを接続し、Run を追跡します。ここで使用するオープンソースの KFP 2.16.1 backend は、IR を Argo Workflows に変換します。Argo は workflow の順序と Pod の作成を管理し、Kubernetes scheduler は Pod を node に配置します。キャッシュされた task、importer、ネストされた DAG があるため、すべての論理 task が個別の user-container 実行に対応するわけではありません。

## KFP v2 アーキテクチャ: IR YAML と Backend 実行

Community Distribution 26.03.1 には KFP 2.16.1 が含まれています。従来の v1 のデフォルトのコンパイルパスは Argo Workflow YAML を生成していましたが、v2 の `Compiler().compile(...)` は PipelineSpec ベースの IR YAML を生成します。pipeline のアップロード/保存と Run の作成は別の操作です。アップロードだけでは実行されません。

IR により Argo object を直接記述する必要はなくなりますが、すべての backend に対する無制限の移植性が保証されるわけではありません。IR/SDK のバージョン、サポートされる機能、Kubernetes platform extension、認証、ストレージは対象環境と一致している必要があります。`kfp` package は client API と Python component 実行サポートも提供します。その役割はコンパイルだけで終わりません。

## コア概念

| 概念 | 役割と範囲 |
| --- | --- |
| Pipeline | `@dsl.pipeline` で作成する graph。アップロードした definition/version と実行は別のもの |
| Component / Task | 再利用可能な component definition と graph invocation。lightweight Python は container/importer/graph と並ぶ一形態 |
| Run / Experiment | input を伴う実行と、関連する Run のグループ。Katib の Experiment CRD とは異なる |
| Parameter | 文字列、数値、小規模な構造化 input/output 値 |
| Artifact | URI、型、metadata を持つ Dataset/Model/Metrics 形式の object。必ずしも単一のファイルではない |
| MLMD | 登録された execution、artifact、関係性。すべての外部 side effect やファイルの整合性を自動記録するものではない |

Metadata の記録と artifact の bytes は別です。再現性やコンテンツの検証が重要な場合は、code/image/data の revision と hash を記録してください。

## Pipeline Run がシステムを流れる仕組み

![Kubeflow Pipelines の Run フロー: Python DSL pipeline は IR YAML にコンパイルされて KFP API server に送信され、component Pod を実行する Argo Workflow に変換されます。Pod は artifact を S3/MinIO に書き込み、metadata を MLMD に記録します。](../../.gitbook/assets/en-ai-ml-kubeflow-02-pipelines-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-02-pipelines-0.html)

コンパイルはローカルで行われます。Run の作成後、API server、Argo、KFP driver/launcher、user container が連携します。launcher/runtime は artifact の path、転送、metadata を処理します。Kubernetes における node 配置は Argo の workflow 順序制御とは別です。

## EKS 固有の Artifact Storage

確認した Distribution のデフォルトインストールには MinIO が含まれますが、すべての KFP インストールまたは artifact URI で使用されるわけではありません。pipeline root、import した URI、provider の設定を確認してください。Metrics のような metadata 指向の artifact は、必ずしも metric file ではありません。

S3 では、[最新の object-store guide](https://www.kubeflow.org/docs/components/pipelines/operator-guides/configure-object-store/) に従い、`pipeline_root`、provider、credential chain を設定してください。S3 には storage、request、transfer の料金が発生します。無料のデフォルト artifact service ではありません。

すべての環境で `pipeline-runner` が実行用 ServiceAccount であると仮定しないでください。Run で選択された account と実際の Pod、および API server/launcher が必要とする access を確認してください。IRSA は最新の guide に記載されています。Pod Identity では、SDK、agent、association、runtime support の確認が必要です。この章では AWS integration を実行していません。[Part 1](01-architecture-installation.md) では、これらの境界と従来の AWS distribution のインストール上の制限について説明しています。

## シンプルな 2 ステップ Pipeline

以下は、KFP v2 SDK の decorator を使用し、最初の component から 2 番目へ型付けされた `Dataset` artifact を渡す、最小限の `data-prep -> train` pipeline を示します。

```python
from kfp import dsl, compiler
from kfp.dsl import Dataset, Model, Output, Input

@dsl.component(base_image="python:3.12-slim", packages_to_install=["pandas==2.3.3"])
def prepare_data(output_dataset: Output[Dataset]):
    import pandas as pd

    # In a real pipeline this would read from S3 or another source
    df = pd.DataFrame({"feature": [1, 2, 3, 4], "label": [0, 1, 0, 1]})
    df.to_csv(output_dataset.path, index=False)

@dsl.component(base_image="python:3.12-slim", packages_to_install=["scikit-learn==1.7.2", "pandas==2.3.3"])
def train_model(input_dataset: Input[Dataset], output_model: Output[Model]):
    import pandas as pd
    from sklearn.linear_model import LogisticRegression
    import pickle

    df = pd.read_csv(input_dataset.path)
    clf = LogisticRegression().fit(df[["feature"]], df["label"])
    with open(output_model.path, "wb") as f:
        pickle.dump(clf, f)

@dsl.pipeline(name="data-prep-train-pipeline")
def data_prep_train_pipeline():
    prep_task = prepare_data()
    train_task = train_model(input_dataset=prep_task.outputs["output_dataset"])

compiler.Compiler().compile(
    pipeline_func=data_prep_train_pipeline,
    package_path="data_prep_train_pipeline.yaml",
)
```

`Output[Dataset]` から `Input[Dataset]` への接続は、graph の依存関係と artifact type を記録します。実際の `.path` の準備と転送は runtime 時に行われます。コンパイルでは storage や training を検証しません。

これらは lightweight Python component です。`@dsl.component` は function code を抽出しますが、image を自動的に build するわけではありません。`packages_to_install` は、base image 内で実行時に dependency をインストールします。以前の例では prepare_data から pandas を省略していましたが、現在は両 component が dependency を宣言し、function body はローカルで確認されています。本番環境では dependency を container に事前 build し、その digest を pin したうえで、その container を個別に test してください。ここでの Python image tag と transitive dependency は完全に lock された build ではありません。

この演習で生成された信頼できる pickle のみを load してください。外部の pickle を load すると任意の code が実行される可能性があります。この小さな model は API を示すものであり、model quality の検証結果ではありません。

## Caching の動作

2.16.1 では、key には input parameter value、input artifact の **name/ID**、output specification、container image string、command/argument、PVC name が含まれます。cache lookup の scope は pipeline name と namespace です。lookup ごとに input artifact file の byte を読み取り、hash 化することはありません。

したがって、同じ artifact ID の背後にある file、image tag、外部 database/API state を変更しても、key は変わらない可能性があります。既存の cache metadata も、削除された output object が downstream で読み取り可能なままであることを保証しません。data version/hash を明示的な parameter として渡し、変更可能な外部 state や side effect については caching の無効化を検討してください。

```python
# Inside the pipeline function, disable caching for this task.
prep_task.set_caching_options(enable_caching=False)
```

認証済み client の `create_run_from_pipeline_package(..., enable_caching=False)` は、Run の task caching を上書きします。`None` はコンパイル済みの task 設定を維持します。CLI のデフォルトと `KFP_DISABLE_EXECUTION_CACHING_BY_DEFAULT` もコンパイルのデフォルトを変更できます。environment variable は KFP を import する前に設定してください。

## 検証とソース

IR は Python 3.12 / KFP 2.16.1 でコンパイルし、dependency、type、caching 設定を確認しました。function body は pandas 2.3.3 / scikit-learn 1.7.2 を使用して CPU 上でローカル実行しました。Docker、Argo、cluster cache reuse、S3、Pod Identity の実行はテストしていません。

- [2.16.1 cache-key implementation](https://github.com/kubeflow/pipelines/blob/2.16.1/backend/src/v2/cacheutils/cache.go)
- [2.16.1 cache lookup and reuse](https://github.com/kubeflow/pipelines/blob/2.16.1/backend/src/v2/driver/cache.go)
- [Official caching guide](https://www.kubeflow.org/docs/components/pipelines/user-guides/core-functions/caching/)
- [Lightweight Python components](https://www.kubeflow.org/docs/components/pipelines/user-guides/components/lightweight-python-components/)

## 次のステップ

pipeline を作成、コンパイル、実行した後、通常次に問われるのは、それらの pipeline component の背後にある対話的な開発作業がそもそもどこで行われるかです。[Part 3: Kubeflow Notebooks](./03-notebooks.md) では、team が pipeline component にまとめられる code を作成・反復するために使用する user ごとの notebook environment について説明します。また、このシリーズの後半では、[Part 6: KServe — Model Serving on Kubernetes](./06-kserve.md) で、その pipeline が最終的に生成する model の serving を扱います。

[メインページに戻る](./README.md)

## クイズ

この章で学んだことを確認するには、[トピッククイズ](../../quizzes/ai-ml/kubeflow/02-pipelines-quiz.md) に挑戦してください。
