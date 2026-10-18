# パート 2: MLflow Model Registry

> **レビュー基準**: MLflow 3.16.0; 最新リリース 3.17.1 を確認済み · 2026-10-16

## ラボ環境のセットアップ

Python 3.10 以降と `mlflow==3.16.0` を使用してください。Registry API はローカル SQLite でも動作します。個別の HTTP サーバーは必須ではありません。パッチ 3.16.1 と、それ以降の 3.17.x 系列 (最新 3.17.1) が利用可能ですが、この章の例では 3.16.0 を使用しており、それ以降のバージョンでは再実行していません。

チームでのデプロイについては[パート 3](03-eks-deployment.md)、Tracking のセットアップについては[パート 1](01-tracking.md)を参照してください。この章では OSS MLflow を説明します。Databricks Unity Catalog などのマネージド Registry では、権限、コピー、保持の挙動が異なる場合があります。

## Model Registry とは

Registry は論理的なモデル名、番号付きバージョン、Alias、およびメタデータを管理します。候補の記録、昇格の承認、エンドポイントのデプロイはそれぞれ別の操作です。Registry があるだけでは、承認またはサービングの動作が自動的に実装されるわけではありません。

## 基本概念

| エンティティ | 意味と変更境界 |
|---|---|
| Registered Model | `fraud-detector` などの論理名の下にあるバージョンのコレクション |
| Model Version | ソース情報を持つ番号付きレコード。説明、タグ、Stage/Alias の関係は変更できます |
| Alias | 1 つのバージョンを指す変更可能な名前。複数の Alias が同じバージョンを指すことができます |
| LoggedModel | 独立した Tracking モデルエンティティ。Registered Model および Model Version とは別のものです |

### Model Version

通常、新しいモデルの結果は新しいバージョンにする必要があります。ただし、**すべてのバージョンフィールドと artifact バイト列が不変というわけではありません**。`update_model_version` は説明を変更し、バージョンタグも変更可能です。書き込みアクセス権を持つ人は、外部の `source` URI にあるファイルを変更できます。Registry のバージョン番号は、オブジェクトの不変性やコンテンツハッシュを保証しません。

`create_model_version` では `run_id` と `model_id` は任意です。直接のソース URI から登録した場合、トレーニング Run へのリンクがないことがあります。登録がポインターなのか、artifact をコピーするのか、別のストレージロケーションを使用するのかは、Registry バックエンドと操作に依存します。実際の挙動を検証してください。

### Alias

`models:/fraud-detector@champion` は、**解決またはロードが行われる時点で** Alias が指すバージョンを見つけます。`models:/fraud-detector/7` は明示的なバージョン参照です。Alias を移動しても、すでにメモリまたはキャッシュにロードされているモデルが自動的に置き換えられることはありません。サービングコントローラーのデプロイ、リロード、キャッシュポリシーは個別に実装し、実際にリクエストを処理しているバージョンを記録してください。

`champion` と `challenger` はチームで定義する名前です。これら自体がライブ/シャドウトラフィックの割合を設定したり、評価を実行したりすることはありません。Alias の更新は、品質またはセキュリティの承認を示す証拠ではありません。

### レガシー Stage モデル

レガシー Stage は `None`、`Staging`、`Production`、`Archived` です。`transition_model_version_stage` は **2.9.0 以降非推奨**であり、3.16.0 API には引き続き存在します。現在のすべてのバージョンから削除されたものとして説明しないでください。新しいワークフローでは、Alias とタグを環境固有の Registered Model および明示的な権限と組み合わせることができます。Stage 名またはタグはアクセス制御ではありません。

## モデルの登録

実際の flavor モデルをログに記録した後、`mlflow.register_model(model_uri, name)` を呼び出すか、flavor の `log_model` 呼び出しに `registered_model_name` を渡します。低レベルの `MlflowClient.create_model_version` API では、ソースを直接指定できます。登録と Alias の再割り当ては別の操作です。

この **Registry メタデータ演習**では、推論可能なモデルは作成しません。Python 3.12、MLflow 3.16.0、SQLite で確認済みです。

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

`READY` は登録ステータスです。上記のように、model flavor や重みを含まないメタデータ fixture も登録できます。推論の互換性と評価基準は個別にテストしてください。この演習では、ローカル DB と fixture を `.registry-demo` に残します。

## ガバナンスと引き継ぎワークフロー

1. 実際のソース artifact、モデル/コード/データのハッシュ、依存関係、Run/モデル参照を記録します。
2. 品質、安全性、ビジネス基準を評価し、承認の証拠を保持します。
3. 権限を持つアクターが `set_registered_model_alias` を呼び出します。トレーニングの完了は自動承認を意味しません。
4. サービングシステムが新しい参照を解決し、リロードまたはデプロイを実行します。再現性とロールバックのために必要に応じてバージョン番号と artifact ハッシュを固定します。

候補の作成と昇格を分離するには、認証、認可、運用パイプラインが必要です。`review_state=approved` のようなタグだけでは、書き込みアクセスを制限したり、承認の証拠を改ざん防止にしたりすることはできません。複数のデプロイジョブからの Alias 更新の同時実行を調整してください。

![コンシューマーは champion および challenger Alias を Model Version 参照に解決します。Alias 解決ではトラフィックはルーティングされず、すでにロード済みのモデルが自動的に置き換えられることもありません。](../../.gitbook/assets/en-ai-ml-mlflow-02-model-registry-0.png)

[インタラクティブ図](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-02-model-registry-0.html)

## Lineage と再現性

Lineage は、記録および保持される情報と同程度にしか完全ではありません。Registry は、欠落している `run_id`、`model_id`、コードリビジョン、データセットハッシュを後から再構築できません。変更されたソースファイル、削除された Run/Model Version、artifact のクリーンアップによっても、リンクが不完全になることがあります。

監査には、実際にサービングしているバージョン/モデル ID、artifact のハッシュと場所、ソースコミット、データセットスナップショット、依存関係、評価/承認記録が必要です。メタデータ DB と artifact ストアのバックアップおよび保持を連携して運用してください。Alias はすべての変更に対する永続的な監査ログではありません。

## 次のステップ

[パート 3: EKS デプロイ](03-eks-deployment.md)では、サーバー、データベース、artifact の権限境界を扱います。

## 主な情報源

- [Model Registry](https://mlflow.org/docs/3.16.0/ml/model-registry/)
- [3.16.0 Registry client API](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/tracking/client.py)
- [ModelVersion fields](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/entities/model_registry/model_version.py)
- [OSS SQL registry implementation](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/store/model_registry/sqlalchemy_store.py)

[メインページ](README.md) · [クイズ](../../quizzes/ai-ml/mlflow/02-model-registry-quiz.md)
