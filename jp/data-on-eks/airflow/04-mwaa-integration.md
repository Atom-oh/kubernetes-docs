# パート4: Amazon MWAA との統合

> **最終更新日**: 2026年10月12日。MWAA Airflow 3.3.1／Python 3.12、Kubernetes provider 10.21.0。
> **最新の上流パッチ確認済み**: Airflow 3.3.2（2026年10月12日時点で MWAA は掲載していない）。

この章の対象は、顧客所有の EKS クラスターに処理を送信する**プロビジョニング済み Amazon MWAA 環境**です。YAML 形式のワークフロー定義を使う **MWAA Serverless** は別のデプロイ方法です。この環境／DAG ファイル／コストのモデルを、そのまま適用しないでください。

## 1. 管理境界と現在のバージョン

MWAA のスケジューラー／ワーカーは AWS 管理の Fargate インフラストラクチャを使い、選択した顧客 VPC 内のプライベートサブネットに接続します。メタデータデータベースも AWS が管理します。したがって、このサービスは VPC と無関係ではありません。ただし、**MWAA スケジューラー Pod が kubectl 管理用に EKS クラスター内へデプロイされるわけではありません。** Airflow 3 では MWAA Web サーバーが Execution API もホストします。

基盤サービスは AWS が運用します。DAG、依存関係、IAM、VPC 接続、キャパシティ設定、アラーム、復旧手順、サポート対象バージョンへのアップグレードは、引き続き利用者が管理します。インフラストラクチャがマネージドでも、環境障害やキャパシティ計画が不要になるわけではありません。

公式のサポート表では、Airflow **3.3.1 は2026年9月1日から利用可能**、3.2.1 は2026年5月19日から利用可能とされています。上流の3.3.1は2026年8月12日にリリースされました。上流の3.3.2は2026年9月17日にリリースされましたが、2026年10月12日時点で、MWAA の表に掲載されている最新バージョンは3.3.1です。上流のパッチが自動的に MWAA で利用可能になるわけではありません。最新のバージョンとリージョンでの提供状況は、[AWS MWAA のサポート対象バージョン一覧](https://docs.aws.amazon.com/mwaa/latest/userguide/airflow-versions.html)で確認してください。
一律に3か月遅れると想定せず、必要なパッチ、プロバイダー、リージョン、実環境のバージョンを確認します。既存の環境が、新たにサポートされた Airflow リリースへ自動で切り替わることはありません。

| 項目 | EKS 上のセルフマネージド Airflow | プロビジョニング済み MWAA |
| --- | --- | --- |
| 運用 | Kubernetes リソース、データベース、アップグレード、復旧を設計する | AWS がサービスインフラストラクチャを管理する。利用者は DAG、権限、接続、キャパシティの選択、アップグレードを引き続き管理する |
| バージョン／executor | 選択した組み合わせを検証する | サポート対象のランタイム／設定から選ぶ |
| Python パッケージ | 独自のイメージまたは他の配信方法を構築する | 一致するバージョン制約を指定した S3 の requirements.txt |
| システム依存関係 | イメージ／ノードのポリシー内で構成する | 起動スクリプトで Linux ランタイムをインストールできる。サポート、起動時間、ネットワークを検証する |
| DAG の配信 | GitDagBundle、git-sync、その他の経路を構成する | 文書化されたベースラインは S3 の DAG フォルダーと補助ファイルの同期 |
| 外部ワークロード | 別イメージ向けに KPO などの統合を使う | KPO／EKS 統合でも、別のワークロードイメージを実行できる |

起動スクリプトは requirements のインストールと Airflow の起動より前に実行されます。公式の例には sudo を使ったランタイムのインストールが含まれます。そのため、システムパッケージを一律に禁止する説明は正しくありません。この機能は、マネージドベースイメージや executor を自由に置き換えられることとは異なります。

この例では Git → CI → S3 → MWAA を使います。S3 で配信するだけで、Airflow 3 のすべての bundle 機能が使えないと証明されるわけではありません。別の bundle 設定を採用する前に、MWAA の特定リリースで許可される設定とサポート状況を検証してください。Git のポーリングと S3 の同期にはどちらも解析遅延があり、push や merge の直後に実行される保証はありません。

## 2. EKS アクセスに必要な3要件

1. **ネットワーク:** ワーカーサブネットから EKS API エンドポイントへ、DNS と HTTPS 443 でアクセスできる必要があります。プライベートエンドポイントでは、ルート、セキュリティグループ、DNS を確認してください。認証を追加しても接続タイムアウトは解決しません。
2. **認証:** MWAA の実行ロールが、EKS access entry または既存の aws-auth 設定を通じて認識される必要があります。kubeconfig の exec plugin は、実行時に利用できる IAM 認証情報を使います。
3. **認可:** 対応付けられた Kubernetes グループを namespace の Role にバインドします。EKS 認証、Kubernetes RBAC、子 Pod の AWS データ権限は別々の層です。

既存の MWAA 3.3.1 環境、既存の EKS クラスター、AWS CLI v2、kubectl を使用してください。現在の EKS サポート状況とプロバイダー／クライアントの互換性を確認します。この章では、新規クラスターや広範な管理者 ID を必要としません。

### Access entry と namespace RBAC

以下の設定はクラスター管理者が実行します。ロール ARN、クラスター、リージョンを置き換え、先に既存の access entry を確認してください。

```bash
aws eks describe-cluster \
  --name data-eks-cluster --region us-east-1 \
  --query 'cluster.accessConfig.authenticationMode'

# Administrator action; API or API_AND_CONFIG_MAP mode is required.
aws eks create-access-entry \
  --cluster-name data-eks-cluster --region us-east-1 \
  --principal-arn arn:aws:iam::123456789012:role/mwaa-execution-role-my-environment \
  --type STANDARD \
  --kubernetes-groups mwaa-pod-launcher
```

access entry は API_AND_CONFIG_MAP モードでも使えます。aws-auth を編集しても、API-only モードではアクセス権が付与されません。従来の CONFIG_MAP クラスターでは、既存のマッピングを使うか、移行を計画してください。認証モードの切り替えには元に戻せない変更が含まれるため、この例ではモードを暗黙に変更しません。

以下の workload-access.yaml を保存して適用します。RoleBinding は、この許可を data-processing に限定します。ClusterRoleBinding では、この namespace の境界を表現できません。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: data-processing
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: workload-smoke
  namespace: data-processing
automountServiceAccountToken: false
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: mwaa-pod-launcher
  namespace: data-processing
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
  name: mwaa-pod-launcher
  namespace: data-processing
subjects:
- kind: Group
  name: mwaa-pod-launcher
  apiGroup: rbac.authorization.k8s.io
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: mwaa-pod-launcher
```

この Role は namespace 全体の Pod に影響を与える可能性があります。他の access-policy／RBAC 許可は加算されるため、権限全体を確認してください。他のサービスアカウントを選択したり、危険な Pod spec を指定したりできる信頼されていない作成者には、admission 制御を使います。この同期実行の例では、XCom／exec 権限は必要ありません。

## 3. kubeconfig と依存関係の配信

個人用 kubeconfig コンテキストを成果物にマージせず、新しいファイルを生成します。生成する管理者には、対象に対する eks:DescribeCluster が必要です。

```bash
set -eu
mkdir -p ./mwaa-staging
test ! -e ./mwaa-staging/kube_config.yaml
aws eks update-kubeconfig \
  --name data-eks-cluster --region us-east-1 \
  --alias data-eks-cluster \
  --kubeconfig ./mwaa-staging/kube_config.yaml
```

生成された cluster、context、CA、exec.command を確認します。開発者のローカル AWS_PROFILE を参照する exec.env エントリは削除し、MWAA 実行ロールのデフォルト認証情報チェーンを使えるようにします。別のロール引き受けを意図していない限り、exec --role 引数は追加しないでください。長期キーや静的トークンを保存しないでください。MWAA ランタイム内の aws 実行ファイルと get-token の経路も確認します。

以下の requirements.txt は、**この章の Airflow 3.3.1／Python 3.12 環境**を対象とします。まず、イメージにすでに含まれるプロバイダーを確認し、追加や変更後に実際のインストール済みバージョンを検証してください。意図せず Airflow コアを変更することがないよう、バージョンを指定しない apache-airflow extra は使わないでください。

```text
--constraint https://raw.githubusercontent.com/apache/airflow/constraints-3.3.1/constraints-3.12.txt
apache-airflow-providers-cncf-kubernetes==10.21.0
```

MWAA の要件に従って、バケットのバージョニングと Block Public Access を有効にします。requirements.txt のアップロード後、環境が参照するオブジェクトバージョンを更新し、インストールログを確認してください。オブジェクトを上書きしただけでは、依存関係の更新手順は完了しません。

設定済みの S3 DAG プレフィックスの下に、この構造を維持します。生成した kube_config.yaml を DAG の隣に配置する前にレビューしてください。

```text
dags/
  mwaa_eks_smoke.py
  kube_config.yaml
  templates/
    base-pod-template.yaml
```

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

```python
from datetime import datetime, timedelta, timezone
from pathlib import Path

from airflow.sdk import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

BUNDLE_DIR = Path(__file__).resolve().parent

with DAG(
    dag_id="mwaa_eks_smoke",
    start_date=datetime(2026, 9, 1, tzinfo=timezone.utc),
    schedule=None,
    catchup=False,
) as dag:
    run_smoke = KubernetesPodOperator(
        task_id="run_smoke",
        name="mwaa-eks-smoke",
        namespace="data-processing",
        image="python:3.12-slim",
        cmds=["python", "-B", "-c"],
        arguments=["import sys; print('MWAA_EKS_OK run_id=' + sys.argv[1])", "{{ run_id }}"],
        pod_template_file=str(BUNDLE_DIR / "templates/base-pod-template.yaml"),
        in_cluster=False,
        config_file=str(BUNDLE_DIR / "kube_config.yaml"),
        service_account_name="workload-smoke",
        random_name_suffix=True,
        reattach_on_restart=True,
        deferrable=False,
        do_xcom_push=False,
        get_logs=True,
        log_events_on_failure=False,
        startup_timeout_seconds=120,
        active_deadline_seconds=180,
        execution_timeout=timedelta(minutes=5),
        on_finish_action="delete_pod",
        on_kill_action="delete_pod",
    )
```

![MWAA ワーカーがネットワーク接続、IAM 認証、namespace RBAC を通じて EKS に到達し、別のワークロード Pod を実行する。](../../.gitbook/assets/en-data-on-eks-airflow-04-mwaa-integration-0.png)

[インタラクティブ図](https://www.atomai.click/kubernetes-docs/archmaps/en-data-on-eks-airflow-04-mwaa-integration-0.html)

## 4. 実行を確認し、運用モデルを選ぶ

DAG の解析が成功した後、mwaa_eks_smoke を手動でトリガーし、タスクの状態と MWAA_EKS_OK ログを確認します。実行中に、Pod の実際のサービスアカウント、イメージ、リソースを調べます。成功後の削除は設定済みのクリーンアップ動作です。保持されたログは MWAA CloudWatch タスクログで確認してください。

| 症状 | 調査する境界 |
| --- | --- |
| DNS／接続タイムアウト | ワーカーサブネットから EKS API までのルート、DNS、セキュリティグループ |
| Unauthorized | exec 認証情報、実際の IAM ロール、access entry |
| Forbidden | namespace、グループ、RoleBinding、必要な verb |
| ImagePullBackOff | EKS ノード／Fargate のイメージ取得 ID とレジストリ接続 |
| DAG import／exec-binary エラー | インストール済み MWAA パッケージ、同期ファイル、aws 実行ファイル |

ワークロード Pod が MWAA 実行ロールを自動的に引き継ぐわけではありません。実際に S3 を使う処理には、サービスアカウントに対する IRSA や Pod Identity など、別途データ権限が必要です。KPO では他のイメージも実行できます。MWAA が PyPI のみ、または重要度の低いパイプラインに限られるわけではありません。

executor／ランタイムの柔軟性、サポート対象バージョン、運用キャパシティ、ネットワーク境界、復旧要件を比較します。コストを比較する際は、スループット／レイテンシの目標を一定に保ち、環境クラス／ワーカー範囲、EKS、データベース、ストレージ、NAT、ログ、エンジニアリング工数を含めてください。セルフホストによって30～60%節約できるという根拠のない主張に基づいて選択しないでください。

## 検証範囲と参考資料

バージョン表、公式の制約、プロバイダーのソース、Python／YAML／シェルの例の構造をレビューしました。MWAA の更新、EKS access entry の作成、RBAC の適用、エンドツーエンド実行は行っていません。前述のチェックを使って、アカウント固有の接続性と実行を検証してください。


- [MWAA のサポート対象バージョンと提供開始日](https://docs.aws.amazon.com/mwaa/latest/userguide/airflow-versions.html)
- [MWAA のアーキテクチャ](https://docs.aws.amazon.com/mwaa/latest/userguide/what-is-mwaa.html)
- [起動スクリプトと Linux ランタイム](https://docs.aws.amazon.com/mwaa/latest/userguide/using-startup-script.html)
- [Python 依存関係と制約](https://docs.aws.amazon.com/mwaa/latest/userguide/working-dags-dependencies.html)
- [MWAA と EKS](https://docs.aws.amazon.com/mwaa/latest/userguide/mwaa-eks-example.html)
- [EKS のアクセス管理](https://aws.amazon.com/blogs/containers/a-deep-dive-into-simplified-amazon-eks-access-management-controls/)
- [MWAA Serverless](https://docs.aws.amazon.com/mwaa/latest/mwaa-serverless-userguide/what-is-mwaa-serverless.html)

[パート5: 運用](05-operations.md)

[README](README.md)

[クイズ](../../quizzes/data-on-eks/airflow/04-mwaa-integration-quiz.md)
