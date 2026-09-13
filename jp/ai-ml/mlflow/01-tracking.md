# Part 1: MLflow Tracking

> **レビュー基準**: MLflow 3.16.0 · 2026-09-12

## ラボ環境のセットアップ

Python 3.10 以降で `mlflow==3.16.0` をインストールします。以下の例は Python 3.12、SQLite、およびローカル artifact store で確認しています。GPU、学習済みモデル、リモートサーバーは不要です。[Part 3](03-eks-deployment.md) ではチーム向け HTTP サーバーと EKS 運用を扱います。

## MLflow Tracking とは？

Tracking は、experiments、runs、parameters、metrics、artifacts、logged models、traces 向けの API と UI を提供します。SDK は HTTP tracking server に接続することも、ローカルの file/SQL backend に直接接続することもできます。すべての用途で個別のサーバープロセスが必要になるわけではありません。

リモートサーバーを使用する場合でも、metadata と artifact の転送は異なる経路を取る場合があります。metadata は tracking API を経由し、artifacts はサーバーが proxy するか、client と S3 などの store 間で直接転送されます。これらの構成については以下で区別します。

## コア概念: Experiments と Runs

**Experiment** は runs と関連する結果をグループ化します。**Run** は training だけでなく、evaluation、preprocessing、比較を表すこともできます。1 つの run 内では、parameter key を別の値に変更できません。Metrics は steps を伴う複数の timestamp 付き observations を持つことができるため、現在の summary と完全な履歴を区別してください。

以下の値は、**測定されたモデル精度ではなく Tracking API fixtures** です。この例は、未定義の image file に依存せず、独自の JSON artifact を作成します。

```python
from pathlib import Path
import mlflow
from mlflow import MlflowClient

root = Path(".mlflow-demo").resolve()
root.mkdir(exist_ok=True)
mlflow.set_tracking_uri(f"sqlite:///{root / 'mlflow.db'}")
client = MlflowClient()
experiment = client.get_experiment_by_name("tracking-demo")
experiment_id = (
    experiment.experiment_id if experiment else
    client.create_experiment(
        "tracking-demo", artifact_location=(root / "artifacts").as_uri()
    )
)
mlflow.set_experiment(experiment_id=experiment_id)

with mlflow.start_run(run_name="demo") as run:
    mlflow.log_param("learning_rate", 0.01)
    mlflow.log_metric("demo_score", 0.92, step=0)
    mlflow.log_metric("demo_score", 0.95, step=1)
    mlflow.log_dict({"synthetic_example": True}, "summary.json")
    run_id = run.info.run_id

assert client.get_run(run_id).info.status == "FINISHED"
assert len(client.get_metric_history(run_id, "demo_score")) == 2
```

通常、context の終了時に run は `FINISHED` として終了します。block 内で例外が発生した場合は `FAILED` として終了します。Run の終了は artifacts の backup を行わず、training process 全体の成功を検証するものでもありません。この例を繰り返すと、同じ experiment に run が追加されます。条件分岐によって既存の experiment の artifact location が変更されることはありません。

### Autologging

`mlflow.autolog()` はサポートされる integrations を構成します。取得される値、サポート対象の framework versions、model logging、input-example collection は integration によって異なります。通常の PyTorch loop と Lightning workflow が同一の自動 instrumentation を受けると想定しないでください。framework 固有の API と version support を確認し、追加の metrics は手動で記録してください。

Autologging を有効にする前に、inputs、outputs、models、data samples の保存先を確認してください。この機能を有効にしても PII が除去されるわけではなく、すべての custom code path が instrumentation されるわけでもありません。

## MLflow 3 の変化: First-Class Entities としての Models

`LoggedModel` には独自の `model_id`、status、artifact location、metadata があります。`source_run_id` を通じて training run を参照でき、他の evaluation runs、metrics、traces と関係を持つことができます。これは Registered Models および Model Versions とは別物です。

**明示的な `start_run()` block なしで `log_model()` を呼び出すこと自体は、3.x の新機能ではありません。** 2.22.0 の `Model.log()` は必要に応じてすでに `_get_or_start_run()` を使用しており、3.16.0 の model-logging path でもこの動作は継続しています。重要な変更点は、独立した model identity と relationship tracking です。

上記の tracking setup の後、これは active run なしで model metadata を作成します:

```python
model = mlflow.initialize_logged_model(
    name="metadata-only", model_type="demo"
)
assert mlflow.active_run() is None
assert model.source_run_id is None
print(model.model_id, model.status)  # PENDING
```

これはまだ使用可能な model weights や model flavor を含んでいません。使用前に、実際の model logging、artifact retention、finalization を完了してください。`READY` は deployment approval、quality、security review の証拠ではありません。

## GenAI と LLM Observability: Tracing

MLflow Tracing は **2024-06-17 の 2.14.0** で導入されました。Version 3.x では model、evaluation、GenAI UI の integration が拡張され、3.16.0 では span links と再設計された trace UI が追加されました。Tracing が初めて可能になったのは version 3 ではありません。

trace は、retrieval、tool execution、LLM calls などの request steps を spans で表します。parent/child structure と span links を区別してください。Token collection は integration と provider response に依存します。retrieval または tool spans に LLM token や cost fields が必ず含まれるとは限りません。Cost estimation には model identity、usage、price information が必要であり、照合済みの billing total ではありません。

適切な場合は automatic instrumentation と manual spans を組み合わせてください。Inputs、outputs、exceptions、tool arguments、reasoning には機密情報が含まれることがあります。collection scope、access、redaction、retention を定義してください。integration をインストールしても、完全な path coverage や cost accounting が保証されるわけではありません。

## Backend Store と Artifact Store

| Store または default | 意味 |
|---|---|
| Backend | experiment/run/parameter/metric/model metadata。SQLite、PostgreSQL、MySQL、その他のサポート対象 SQL stores |
| Artifact | model files、plots、JSON、その他の files。ローカル paths、S3、その他の stores |
| Default | 新しい 3.16.0 environment では `sqlite:///mlflow.db` を使用します。`./mlruns` がすでに存在する場合は compatibility behavior を確認してください |
| Legacy file backend | maintenance mode。新規運用では明示的な SQL backend と migration plan を選択してください |

SQLite も relational database です。小規模なローカル演習には適していますが、concurrent writers、複数の server replicas、backups、high availability には個別の評価が必要です。metadata database の backup には artifact files が自動的に含まれません。

### リモートサーバーでの 2 つの Artifact Path

- **Proxy mode:** client は `mlflow-artifacts:` location を使用して server 経由で files を送信し、server が artifact-store permissions を保持します。clients に独自の S3 access が不要な場合があるため、tracking-server authentication と authorization が重要になります。
- **Direct mode:** `--no-serve-artifacts` と直接の `s3://...` artifact root を使用する場合、clients は storage に直接アクセスします。関連する AWS permissions、network access、libraries が必要です。

server flags を変更しても、既存の experiment artifact URIs が遡って書き換えられることはありません。実際の experiment/run URI を確認してください。browser UI は server HTTP APIs を query します。PostgreSQL に直接接続するわけではありません。

![Clients と web UI は Tracking server API に接続し、これが SQL metadata と artifact storage にアクセスします。direct artifact mode では、認可された client が別の file-transfer path を使用して storage にアクセスします。](../../.gitbook/assets/en-ai-ml-mlflow-01-tracking-0.png)

[インタラクティブ図](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-01-tracking-0.html)

## 次のステップ

[Part 2](02-model-registry.md) では registration、versions、aliases を扱います。[Part 3](03-eks-deployment.md) では EKS storage と access control を扱います。alias の変更だけで、すべての serving process が自動的に redeploy されるわけではありません。

## 主な情報源

- [MLflow 3.16.0 リリース](https://github.com/mlflow/mlflow/releases/tag/v3.16.0)
- [Backend store](https://mlflow.org/docs/3.16.0/self-hosting/architecture/backend-store/)
- [Artifact store](https://mlflow.org/docs/3.16.0/self-hosting/architecture/artifact-store/)
- [2.22.0 model logging 実装](https://github.com/mlflow/mlflow/blob/v2.22.0/mlflow/models/model.py)
- [3.16.0 Tracking API 実装](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/tracking/fluent.py)
- [2.14.0 で導入された Tracing](https://github.com/mlflow/mlflow/releases/tag/v2.14.0)

[メインページに戻る](README.md) · [クイズ](../../quizzes/ai-ml/mlflow/01-tracking-quiz.md)
