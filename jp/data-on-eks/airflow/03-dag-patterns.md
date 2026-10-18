# パート3: DAGパターンと KubernetesPodOperator

> **レビュー基準**: Airflow 3.3.1 / cncf-kubernetes provider 10.21.0
> **確認した最新の上流パッチ**: Airflow 3.3.2。例は3.3.1のまま · 2026年10月12日

## 1. Executor、KPO、実際の Pod 数

KubernetesPodOperator（KPO）を使うと、Airflow タスクから別個のワークロード Pod を作成し、その状態を監視できます。CeleryExecutor、KubernetesExecutor、または互換性のある別の executor を通じて実行できます。Airflow タスクの実行環境には provider が必要ですが、**ワークロード Pod 自体に Airflow がインストールされている必要はありません**。

| 一般的な新規実行 | 新たに作成される Pod と共有リソース |
| --- | --- |
| CeleryExecutor + KPO | 既存の worker プロセスが KPO を実行してワークロード Pod を作成する。複数のタスクが同じ worker Pod を共有できる |
| KubernetesExecutor + KPO | Airflow のタスク実行用 Pod と、別の KPO ワークロード Pod を作成する |

そのため、executor を変更すると実際の Pod 数も変わることがあります。論理上の実行役割が2つあるからといって、Pod 数が変わらないとは限りません。再試行や再アタッチでは既存 Pod を再利用したり、追加の試行用 Pod を作成したりします。deferrable モードでは、triggerer が監視を続けながら worker slot を解放できます。稼働中の Pod が常にちょうど2つになる保証はありません。

## 2. マージ動作を含む優先順位

Provider 10.21.0 は、次のように Pod を構築します。

1. `pod_template_file` が指定されていれば、それを選択します。同じ呼び出しで `pod_template_dict` も追加でマージすることはありません。
2. それ以外の場合は、`pod_template_dict` を選択するか、`full_pod_spec`／空の Pod から開始します。
3. 選択したテンプレートを `full_pod_spec` とマージし、その後 KPO が構築した Pod とマージします。
4. Airflow のラベル、Secret／XCom の処理、`pod_mutation_hook`、サーバー側の admission／defaulting によって、さらに結果が変わる場合があります。

`image` や `namespace` など、空でない値は通常テンプレートを上書きしますが、すべてのフィールドが単純な置き換えになるわけではありません。リリース済みのマージメソッドを実行すると、次の結果を確認できます。

| 入力 | 結果 |
| --- | --- |
| 空でない `image` | テンプレートの image を上書きする |
| 空の `command` または `tolerations` | テンプレートの値が残ることがある |
| テンプレートが `true` のときに `false` で automount を上書き | falsy な上書きでは `true` が残ることがある。最終的な Pod を確認する |
| `env`／`volume_mounts` などのリスト | 連結されることがある。空のリストでも元の値が消えるとは限らない |
| `limits` だけを指定した `container_resources` | 以前の `requests` は保持されない |
| 空でない `node_selector` | 以前の selector 全体を置き換えることがある |
| メタデータのラベル | キーごとにマージされる |
| Init container | 名前が一致するものはマージされ、ほかは追加される |

Kubernetes コンテナのリソースには **`container_resources=V1ResourceRequirements(...)`** を使います。一般的な `resources` 引数と混同しないでください。元のテンプレートだけで判断せず、`dry_run` の出力と実際に admission された Pod を確認してください。

## 3. 小さく実行可能な DAG を用意する

最初にパート2の Airflow と DAG 配布の手順を済ませてください。この例は実行 ID を出力するだけで、S3 にはアクセスしないため、AWS データロールは不要です。実際のワークロードでは、それぞれに必要なイメージ、パッケージ、データ権限を用意してください。

`workload-access.yaml` では、RoleBinding の subject を、実際に KPO を実行する **Airflow worker のサービスアカウント**に設定します。この例では `airflow` namespace の `airflow-worker` を使います。これはワークロード Pod のサービスアカウントとは異なります。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: airflow-workloads
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: workload-smoke
  namespace: airflow-workloads
automountServiceAccountToken: false
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: airflow-kpo
  namespace: airflow-workloads
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - create
  - get
  - list
  - watch
  - patch
  - delete
- apiGroups:
  - ''
  resources:
  - pods/log
  verbs:
  - get
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: airflow-kpo-worker
  namespace: airflow-workloads
subjects:
- kind: ServiceAccount
  name: airflow-worker
  namespace: airflow
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: airflow-kpo
```

Role の適用範囲はワークロード namespace に限定されていますが、その中の一致する Pod リソースすべてに影響する可能性があります。信頼境界と admission control を使い、信頼できない DAG 作成者が特権 ID や危険な Pod 仕様を選べないようにしてください。この同期実行の例では XCom の exec 権限は不要です。XCom sidecar や deferral を追加する場合は、`pods/exec` と triggerer の監視権限を見直してください。

以下のファイルをまとめて DAG bundle に配布します。

```text
dags/
  kpo_smoke.py
  templates/
    base-pod-template.yaml
```

`templates/base-pod-template.yaml` は KPO によって補完されるもので、単独の Pod デプロイ用ではありません。ここで設定するリソース、ファイルシステム、UID は、この例のワークロードに合わせています。

```yaml
apiVersion: v1
kind: Pod
metadata:
  labels:
    app: airflow-kpo-smoke
spec:
  serviceAccountName: workload-smoke
  automountServiceAccountToken: false
  restartPolicy: Never
  securityContext:
    runAsNonRoot: true
    runAsUser: 65532
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: base
    image: python:3.12-slim
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
```

`kpo_smoke.py` は、Airflow が実際に検出できる DAG を定義します。どこでも同じとは限らない `/opt/airflow/dags` パスを前提にせず、worker 上で bundle 内のファイルを基準にテンプレートを解決します。

```python
from datetime import datetime, timedelta, timezone
from pathlib import Path

from airflow.sdk import Asset, DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from kubernetes.client import models as k8s

TEMPLATES = Path(__file__).parent / "templates"
smoke_completed = Asset("demo://kpo-smoke-completed")

with DAG(
    dag_id="kpo_smoke",
    schedule=None,
    start_date=datetime(2026, 9, 1, tzinfo=timezone.utc),
    catchup=False,
) as dag:
    run_smoke = KubernetesPodOperator(
        task_id="run_smoke",
        name="kpo-smoke",
        namespace="airflow-workloads",
        in_cluster=True,
        pod_template_file=str(TEMPLATES / "base-pod-template.yaml"),
        service_account_name="workload-smoke",
        image="python:3.12-slim",
        cmds=["python", "-B", "-c"],
        arguments=["import sys; print('KPO_SMOKE_OK run_id=' + sys.argv[1])", "{{ run_id }}"],
        container_resources=k8s.V1ResourceRequirements(
            requests={"cpu": "250m", "memory": "128Mi"},
            limits={"cpu": "500m", "memory": "256Mi"},
        ),
        random_name_suffix=True,
        reattach_on_restart=True,
        deferrable=False,
        get_logs=True,
        do_xcom_push=False,
        startup_timeout_seconds=120,
        active_deadline_seconds=180,
        execution_timeout=timedelta(minutes=5),
        on_finish_action="delete_pod",
        on_kill_action="delete_pod",
        outlets=[smoke_completed],
    )

if __name__ == "__main__":
    run_smoke.dry_run()
```

Provider をインストールした Airflow 環境で `python kpo_smoke.py` を実行すると、Pod の設定が出力されます。namespace を明示し XCom を無効にすると、この例は10.21.0の `dry_run` 経路で Kubernetes client を実際に初期化せずに済みます。Jinja 引数と task-instance のラベルには、実際の実行コンテキストが必要です。`dry_run` は最終的な admission や実行成功を示すものではありません。

`run_id` は独立したコマンド引数として渡します。Asset によって起動された DAG 実行では `logical_date`／`ds` などの時間コンテキストがない場合があるため、すべてのタスクに `{{ ds }}` が存在すると仮定しないでください。

namespace と RBAC を適用し、DAG の配布と解析を確認してから、UI または CLI で `kpo_smoke` を起動します。タスクの状態、`KPO_SMOKE_OK` のログ、実際の Pod の image、サービスアカウント、リソースを調べます。成功後に Pod を削除する設定になっています。ログを長期保存するには、パート5のリモートログ設定が必要です。

### 削除、停止、再起動

Provider 10.21.0 は `is_delete_operator_pod` を受け取りますが、constructor ではこの引数を使いません。`False` にしても Pod が確実に保持されるわけではありません。それぞれの処理には **`on_finish_action`** と **`on_kill_action`** を設定してください。再アタッチは再起動後に既存 Pod の監視を再開しますが、外部への書き込みが必ず一度だけ行われることは保証しません。

## 4. 専用ノードと AWS アクセス

必要な場合は、準備済みの NodePool に合う selector／required affinity と toleration を追加します。Toleration は taint があっても配置を許可するもので、配置先を強制するものではありません。専用 pool を使っても、Spot の回収、ノード障害、ディスク圧迫、disruption は防げません。また、同じ taint を許容する別のワークロードが存在することもあります。

実際に S3 を使う場合は、ワークロードのサービスアカウントに対する IRSA の OIDC trust または Pod Identity の関連付け／Agent、IAM 権限、互換性のある SDK／provider を用意します。注釈や `service_account_name` の文字列だけでは S3 アクセスは完成しません。環境変数、IMDS、SDK のデフォルト認証情報チェーンなど、ほかの認証情報の供給元も確認してください。また、Pod の存続期間が一時認証情報の有効期限と一致するとは限りません。Kubernetes RBAC と AWS のデータ権限を分け、許可されるアクセスと拒否されるアクセスをテストしてください。

## 5. DAG bundle と再実行時のコードバージョン

Bundle は DAG processor と worker に DAG コードや関連ファイルを提供します。現在、`LocalDagBundle` と `S3DagBundle`／`GCSDagBundle` は bundle のバージョン管理を行いません。そのため、parser 時点の snapshot と worker が後で読み込むコードが一致するとは限りません。`GitDagBundle` はバージョン管理に対応しています。`git-sync` も引き続き利用できます。

バージョン管理された bundle であっても、すべての再実行が元の commit を使うわけではありません。3.3.1での選択順序は次のとおりです。

1. API リクエストの `run_on_latest_version` を明示した値。
2. DAG の `rerun_with_latest_version` の値。
3. グローバル設定 `[core] rerun_with_latest_version`。
4. 未設定の場合は呼び出しごとの fallback。clear／rerun は `False`、backfill は `True`。

`disable_bundle_versioning` は、実行に対するバージョン追跡を別途無効にします。追跡されなかったバージョンは、再実行時の既定値でも保持できません。Git commit を保持しても、イメージ、パッケージ、外部データ、設定が変われば結果を再現できるとは限りません。必要に応じてリポジトリの履歴とアクセスを保持し、実行時の依存関係を固定してください。

Bundle の kwargs は Config API 経由で公開される場合があります。`repo_url` に token を埋め込まず、Airflow Connections や適切な認証情報の仕組みを参照してください。

![KPO を実行する Airflow worker、作成・監視されるワークロード Pod、状態を報告する Airflow。](../../.gitbook/assets/en-data-on-eks-airflow-03-dag-patterns-0.png)

[インタラクティブ図](https://www.atomai.click/kubernetes-docs/archmaps/en-data-on-eks-airflow-03-dag-patterns-0.html)

## 6. Spark、dbt、Asset の連携

KPO は、パッケージ化した dbt やほかの CLI ワークロードを実行できます。Spark には複数の連携方法があります。

| 方法 | 確認すること |
| --- | --- |
| SparkKubernetesOperator | SparkApplication API／CRD と provider の互換性、呼び出し元の RBAC、driver の監視／cleanup |
| SparkSubmitOperator または KPO の submitter image | `spark-submit` のランタイム／認証、driver／executor の権限、完了／失敗処理 |
| CustomObjects client または送信サービス | namespace の明示、一意な実行 ID、状態／再試行／cleanup の契約 |

固定名の SparkApplication に対して apply した後、`COMPLETED` だけを待つ古い方法では、以前の実行状態 `COMPLETED` を今回の成功と誤認することがあります。また、誤った namespace を待ち続けたり、終端の失敗をすぐに処理できなかったりすることもあります。ここでは、その組み合わせを実行可能な基本例として使用していません。

Native operator であっても、あらゆるリリースの組み合わせと自動的に互換性があるわけではありません。確認対象の10.21.0では、`SparkKubernetesOperator` が再アタッチ設定に `spec.labels` を追加しますが、Spark の章で扱う Kubeflow 2.5.2 の CRD にはそのフィールドがありません。サーバー側のフィールド検証／pruning は動作に影響することがあります。**最終的に生成された CR** を検証してください。このバージョンの kill 処理は Spark CR を削除するため、その経路では `delete_on_termination=False` にしても CR は保持されません。入力 YAML だけを検証しても、連携テストにはなりません。

基本 DAG の `demo://kpo-smoke-completed` は、成功時に出力される **デモ用 Asset event** です。S3 オブジェクトを自動検出したり、データを検証したりするものではありません。下流 DAG では `schedule=[smoke_completed]` を使えますが、実際のパイプラインでは、意図したデータが確定した後にだけ outlet event を出してください。

## 検証の範囲

変更していないリリース済みのマージ関数を、実際の Kubernetes Python model で実行してマージ動作を確認しました。constructor の確認はソース／AST の検査です。Airflow タスク、Kubernetes API、IAM／S3、Spark クラスターでの実行や復旧を完了したテストではありません。

- [Kubernetes provider 10.21.0 の operator](https://airflow.apache.org/docs/apache-airflow-providers-cncf-kubernetes/10.21.0/operators.html)
- [KPO の実装](https://github.com/apache/airflow/blob/providers-cncf-kubernetes/10.21.0/providers/cncf/kubernetes/src/airflow/providers/cncf/kubernetes/operators/pod.py)
- [リリース済み PodGenerator のマージ実装](https://github.com/apache/airflow/blob/providers-cncf-kubernetes/10.21.0/providers/cncf/kubernetes/src/airflow/providers/cncf/kubernetes/pod_generator.py)
- [DAG bundle と再実行時のバージョン選択](https://airflow.apache.org/docs/apache-airflow/3.3.1/administration-and-deployment/dag-bundles.html)
- [テンプレートコンテキストと論理日時](https://airflow.apache.org/docs/apache-airflow/3.3.1/templates-ref.html)
- [SparkKubernetesOperator の実装](https://github.com/apache/airflow/blob/providers-cncf-kubernetes/10.21.0/providers/cncf/kubernetes/src/airflow/providers/cncf/kubernetes/operators/spark_kubernetes.py)
- [Kubeflow SparkApplication 2.5.2 CRD](https://github.com/kubeflow/spark-operator/blob/v2.5.2/config/crd/bases/sparkoperator.k8s.io_sparkapplications.yaml)

[パート4: MWAA との連携](04-mwaa-integration.md)

[README](README.md)

[クイズ](../../quizzes/data-on-eks/airflow/03-dag-patterns-quiz.md)
