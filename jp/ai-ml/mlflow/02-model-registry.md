# Part 2: MLflow Model Registry

> **確認基準**: MLflow 3.16.0 · 2026-09-12

## ラボ環境の準備 {#lab-environment-setup}

Python 3.10 以降と `mlflow==3.16.0` を使用します。Registry API はローカル SQLite でも動作します。個別の HTTP サーバーは必須ではありません。チームでの Deployment については [Part 3](03-eks-deployment.md)、Tracking のセットアップについては [Part 1](01-tracking.md) を参照してください。この章では OSS MLflow について説明します。Databricks Unity Catalog などのマネージド Registry では、権限、コピー、および保持の動作が異なる場合があります。

## Model Registry とは {#what-the-model-registry-is}

Registry は、論理的なモデル名、番号付きバージョン、エイリアス、メタデータを管理します。候補の記録、昇格の承認、エンドポイントの Deployment はそれぞれ別の操作です。Registry を持つだけでは、承認や serving の動作は自動的に実装されません。

## 基本概念 {#core-concepts}

| Entity | Meaning and mutation boundary |
|---|---|
| Registered Model | `fraud-detector` のような論理名の配下にあるバージョンのコレクション |
| Model Version | ソース情報を持つ番号付きレコード。説明、タグ、stage/alias の関係は変更可能 |
| Alias | 1 つのバージョンを指す変更可能な名前。複数の Alias が同じバージョンを指すことも可能 |
| LoggedModel | 独立した Tracking のモデルエンティティ。Registered Models および Model Versions とは別物 |

### Model Version

通常、新しいモデルの結果は新しいバージョンにする必要があります。ただし、**すべてのバージョンフィールドと artifact のバイト列が不変というわけではありません**。`update_model_version` は説明を変更し、バージョンタグも変更可能です。書き込み権限を持つ人は、外部の `source` URI にあるファイルを変更できます。Registry のバージョン番号は、オブジェクトの不変性やコンテンツハッシュを強制しません。

`run_id` と `model_id` は、`create_model_version` ではオプションです。直接のソース URI から登録すると、トレーニング Run へのリンクがない場合があります。登録がポインターであるか、artifact をコピーするか、別の保存先を使用するかは、Registry バックエンドと操作に依存します。実際の動作を検証してください。

### Aliases

`models:/fraud-detector@champion` は、**解決/ロード時に** Alias のバージョンを見つけます。`models:/fraud-detector/7` は明示的なバージョン参照です。Alias を移動しても、すでにメモリまたはキャッシュにロードされているモデルは自動的に置き換えられません。serving-controller の Deployment、リロード、キャッシュのポリシーを別途実装し、実際にリクエストを処理しているバージョンを記録してください。

`champion` と `challenger` はチームが定義する名前です。これらはライブ/シャドウトラフィックの割合を設定したり、自ら評価を実行したりしません。Alias の更新は、品質またはセキュリティ承認の証拠ではありません。

### The Legacy Stage Model

レガシー stage は `None`、`Staging`、`Production`、`Archived` です。`transition_model_version_stage` は **2.9.0 以降非推奨** であり、3.16.0 API には引き続き存在します。すべての現行バージョンから削除されたものとして説明しないでください。新しいワークフローでは、Alias とタグを環境固有の Registered Models および明示的な権限と組み合わせることができます。stage 名またはタグはアクセス制御ではありません。

## モデルの登録 {#registering-a-model}

実際の flavor model をログに記録した後、`mlflow.register_model(model_uri, name)` を呼び出すか、flavor の `log_model` 呼び出しに `registered_model_name` を渡します。より低レベルの `MlflowClient.create_model_version` API では、ソースを直接指定できます。登録と Alias の再割り当ては別の操作です。

この **Registry メタデータ演習** では、推論可能なモデルは作成されません。Python 3.12、MLflow 3.16.0、SQLite で確認済みです。

```python
from pathlib import Path
import mlflow
from mlflow import MlflowClient

root = Path(".registry-demo").resolve()
root.mkdir(exist_ok=True)
mlflow.set_tracking_uri(f"sqlite:///{root / 'registry.db'}")
client = MlflowClient()
name = "registry-contract-demo"
# Run once in a fresh demo DB. Inspect the existing name before repeating.
client.create_registered_model(name)
versions = []
for number in (1, 2):
    source = root / f"candidate-{number}"
    source.mkdir(exist_ok=True)
    (source / "metadata.json").write_text('{"fixture": true}')
    versions.append(client.create_model_version(name, source=source.as_uri()))

first, second = versions
assert first.run_id is None
client.update_model_version(name, first.version, description="metadata fixture")
client.set_model_version_tag(name, first.version, "review_state", "demo-only")
client.set_registered_model_alias(name, "champion", first.version)
snapshot = client.get_model_version_by_alias(name, "champion")
client.set_registered_model_alias(name, "champion", second.version)
assert snapshot.version == first.version
assert client.get_model_version_by_alias(name, "champion").version == second.version
```

`READY` は登録ステータスです。上記のように、model flavor や weights を持たないメタデータ fixture でも登録できます。推論互換性と評価基準は別途テストしてください。この演習では、ローカル DB と fixture が `.registry-demo` に残ります。

## ガバナンスと引き継ぎワークフロー {#governance-and-the-handoff-workflow}

1. 実際のソース artifact、model/code/data hash、依存関係、Run/model 参照を記録します。
2. 品質、安全性、ビジネス基準を評価し、承認の証拠を保存します。
3. 権限を持つ担当者が `set_registered_model_alias` を呼び出します。トレーニングの完了は自動承認ではありません。
4. serving システムが新しい参照を解決し、リロードまたは Deployment を実行します。再現性とロールバックのために必要に応じてバージョン番号と artifact hash を固定します。

候補の作成と昇格を分離するには、認証、認可、運用パイプラインが必要です。`review_state=approved` のようなタグだけでは、書き込みアクセスを制限したり、承認の証拠を改ざん不能にしたりすることはできません。複数の Deployment job からの同時 Alias 更新を調整してください。

![コンシューマーは champion および challenger Alias を Model Version 参照へ解決します。Alias の解決はトラフィックをルーティングせず、すでにロードされているモデルを自動的に置き換えることもありません。](../../.gitbook/assets/en-ai-ml-mlflow-02-model-registry-0.png)

[インタラクティブ図](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-02-model-registry-0.html)

## Lineage と再現性 {#lineage-and-reproducibility}

Lineage の完全性は、記録および保持された情報と同程度に限られます。Registry は、欠落した `run_id`、`model_id`、コードリビジョン、データセットハッシュを後から復元できません。ソースファイルの変更、Run/Model Version の削除、artifact のクリーンアップによっても、リンクが不完全になる可能性があります。

監査には、実際に serving しているバージョン/model ID、artifact hash と場所、ソース commit、データセット snapshot、依存関係、評価/承認記録が必要です。メタデータ DB と artifact-store のバックアップおよび保持を一緒に運用してください。Alias はすべての変更に対する恒久的な監査ログではありません。

## 次のステップ {#next-steps}

[Part 3: EKS Deployment](03-eks-deployment.md) では、サーバー、データベース、artifact の権限境界について扱います。

## 一次資料 {#primary-sources}

- [Model Registry](https://mlflow.org/docs/3.16.0/ml/model-registry/)
- [3.16.0 Registry client API](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/tracking/client.py)
- [ModelVersion fields](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/entities/model_registry/model_version.py)
- [OSS SQL registry implementation](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/store/model_registry/sqlalchemy_store.py)

[メインページ](README.md) · [クイズ](../../quizzes/ai-ml/mlflow/02-model-registry-quiz.md)
