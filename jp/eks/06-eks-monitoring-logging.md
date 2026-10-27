# Amazon EKS のモニタリングとログ記録

> **最終更新日**: 2026年10月23日

効果的なモニタリングとログ記録は、Amazon EKS クラスターの信頼性、可用性、パフォーマンスを維持するうえで不可欠です。このドキュメントでは、EKS クラスターでモニタリングとログ記録を実装するためのさまざまなツール、手法、ベストプラクティスについて説明します。

## 目次

1. [モニタリングとログ記録の概要](#monitoring-and-logging-overview)
2. [EKS コントロールプレーンのログ記録](#eks-control-plane-logging)
3. [コンテナのログ記録](#container-logging)
4. [クラスターのモニタリング](#cluster-monitoring)
5. [アラートとイベント管理](#alerting-and-event-management)
6. [ログ分析と可視化](#log-analysis-and-visualization)
7. [モニタリングとログ記録のベストプラクティス](#monitoring-and-logging-best-practices)
8. [トラブルシューティングとデバッグ](#troubleshooting-and-debugging)

## モニタリングとログ記録の概要

### モニタリングとログ記録の重要性

Amazon EKS クラスターでのモニタリングとログ記録は、次の理由から重要です。

1. **可視性**: クラスターの状態、パフォーマンス、動作を可視化します
2. **問題の検出**: 問題が重大になる前に早期に検出します
3. **傾向分析**: パフォーマンスとリソース使用量の経時的な傾向を特定します
4. **キャパシティプランニング**: リソース要件を予測し、計画します
5. **セキュリティと監査**: 調査と、該当する統制で必要となる証跡の確保を支援します
6. **トラブルシューティング**: 問題が発生した際に、迅速な診断と解決を可能にします

### モニタリングとログ記録のアーキテクチャ

包括的な EKS クラスターのモニタリングとログ記録のアーキテクチャは、次のコンポーネントで構成されます。

AWS は、マネージドコントロールプレーンのログを CloudWatch Logs に配信します。コンテナランタイムは CRI ログファイルを書き込み、kubelet はローテーションとログへのアクセスを管理し、ノードコレクターがファイルを読み取ります。メトリクスとトレースは、それぞれに設定された収集／エクスポート経路を使用します。

<!-- Audit: parent diagram repair needed for direct control-plane delivery and runtime-versus-kubelet log responsibilities.
![Architecture diagram showing EKS control-plane logs, pod logs, and node metrics flowing through Fluent Bit and Prometheus into CloudWatch Logs/Metrics, Amazon OpenSearch, and Grafana/Alertmanager.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-0.html)
-->

### モニタリングとログ記録の戦略

効果的なモニタリングとログ記録の戦略を策定するには、次の手順に従います。

1. **目標を定める**: モニタリングとログ記録の目標と要件を定義します
2. **メトリクスとログを特定する**: 収集する主要なメトリクスとログを特定します
3. **ツールを選ぶ**: 要件を満たすモニタリングとログ記録のツールを選択します
4. **ベースラインを確立する**: 通常時の動作についてベースラインを確立します
5. **アラートを設定する**: 重要なイベントやしきい値に対するアラートを設定します
6. **自動化する**: モニタリングとログ記録のプロセスを可能な限り自動化します
7. **定期的に見直す**: モニタリングとログ記録の戦略を定期的に見直し、改善します

## EKS コントロールプレーンのログ記録

EKS は、選択したマネージドコントロールプレーンのログタイプを CloudWatch Logs にエクスポートします。ノード側のコレクターがマネージドコントロールプレーンのファイルシステムをスクレイプすることはありません。ログ配信はベストエフォートです。アクセス権と保持期間を設定し、ログ欠落の検出を行ったうえで、実際にログが到着していることを確認してください。

### コントロールプレーンのログタイプ

| タイプ | 目的 |
|---|---|
| `api` | API server コンポーネントの診断情報 |
| `audit` | 監査ポリシーとレベルによって選択された Kubernetes リクエスト |
| `authenticator` | EKS IAM 認証の診断情報 |
| `controllerManager` | コアの controller-manager の操作 |
| `scheduler` | スケジューラーの判断と診断情報 |

監査ログは、すべてのリクエスト本文やアプリケーション操作を無条件に記録するものではありません。Secret 関連の記録はメタデータのみの場合があり、ポリシーによって一部のイベントは除外されます。CloudTrail の AWS API 記録と、アプリケーションのデータアクセスログは別個の証跡ソースです。

### ログ記録の確認と有効化

変更前に、対象クラスターのリージョン、ARN、現在のログ設定、更新状態を確認してください。ログ記録の変更には、文書化されたサブネット IP 容量が必要で、CloudWatch の取り込み／ストレージ料金が発生します。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{ARN:arn,Status:status,Logging:logging}'
```

承認済みの変更では、次のコマンドで5種類のログタイプを有効にし、返された更新情報を確認します。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the reviewed cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
UPDATE_ID=$(aws eks update-cluster-config \
  --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query 'update.id' --output text)
if [[ -z "$UPDATE_ID" || "$UPDATE_ID" == None ]]; then
  printf '%s\n' 'No update ID returned; inspect the request result.' >&2
  exit 1
fi
aws eks describe-update --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --update-id "$UPDATE_ID" \
  --query 'update.{ID:id,Status:status,Errors:errors}'
```

最後のコマンドは状態確認であり、完了を待つコマンドではありません。DescribeUpdate を繰り返し、Successful または終端エラーになるまで確認してから、有効な設定とログの到着を確認してください。更新 ID は処理完了の証拠ではありません。選択したタイプのみを有効にしても、既存の無関係なタイプが無効になるとは限りません。明示的に無効化するかどうかは、保持／可視性についての別個の判断です。

確認済みの eksctl CLI では、--approve を省略すると変更内容がプレビューされます。CLUSTER_NAME と AWS_REGION に同じ検証済みクラスターを設定し、プレビューを確認してください。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
eksctl utils update-cluster-logging \
  --region "$AWS_REGION" --cluster "$CLUSTER_NAME" \
  --enable-types api,audit,authenticator,controllerManager,scheduler
```

計画を確認した後、別の適用コマンドを実行します。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
eksctl utils update-cluster-logging \
  --region "$AWS_REGION" --cluster "$CLUSTER_NAME" \
  --enable-types api,audit,authenticator,controllerManager,scheduler --approve
```

### コントロールプレーンのログをクエリする

実際のロググループ `/aws/eks/CLUSTER_NAME/cluster` を使用してください。最初の2つの例は、選択したコンポーネントのログストリームを対象にしたテキスト検索のヒューリスティックであり、エラー率を完全に測定するものではありません。

**API の診断情報:**

```text
fields @timestamp, @message
| filter @logStream like /kube-apiserver-/ and @logStream not like /audit/
| filter @message like /[Ee]rror/
| sort @timestamp desc
| limit 20
```

**IAM 認証の診断情報:**

```text
fields @timestamp, @message
| filter @logStream like /authenticator/
| filter @message like /[Ff]ailed|[Dd]enied|[Uu]nauthorized/
| sort @timestamp desc
| limit 20
```

**監査ログの拒否:** 生の JSON テキスト内でリテラルの `responseStatus.code` 文字列を検索するのではなく、検出した JSON フィールドを使用してください。サンプルイベントでフィールドの形式を確認します。

```text
fields @timestamp, user.username, verb, objectRef.resource, objectRef.namespace, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code in [401, 403]
| sort @timestamp desc
| limit 20
```

### 保持期間とコストの管理

返されたプレフィックス検索結果から、正確なロググループの項目を確認します。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
aws logs describe-log-groups --region "$AWS_REGION" \
  --log-group-name-prefix "/aws/eks/$CLUSTER_NAME/cluster" \
  --query 'logGroups[].{Name:logGroupName,RetentionDays:retentionInDays,KmsKey:kmsKeyId}'
```

承認済みのポリシーで30日間が必要な場合、変更コマンドは `aws logs put-retention-policy --region "$AWS_REGION" --log-group-name "/aws/eks/$CLUSTER_NAME/cluster" --retention-in-days 30` です。30日はポリシーの例であり、普遍的なコンプライアンス要件ではありません。保持期間を短縮すると古い証跡が期限切れになることがあります。延長しても、削除済みのログは復元されません。保持期間だけでは、アーカイブ配信、完全性、コンプライアンスを証明できません。

### EKS Capabilities のログ記録（GitOps、ACK、kro）

2026年6月4日の機能はサポートされています。ACK、kro、Argo CD の capability controller はクラスター**外部の AWS 管理インフラストラクチャ**で実行され、CloudWatch Vended Logs を通じて構造化されたコントローラーログを配信できます。これは capability ごとの配信設定を使用し、標準の5種類のコントロールプレーンログとは別個です。

| Capability | ログタイプ |
|---|---|
| ACK | `EKS_CAPABILITY_ACK_LOGS` |
| kro | `EKS_CAPABILITY_KRO_LOGS` |
| Argo CD | `EKS_CAPABILITY_ARGOCD_APPLICATION_LOGS`、`EKS_CAPABILITY_ARGOCD_APPLICATIONSET_LOGS`、`EKS_CAPABILITY_ARGOCD_COMMITSERVER_LOGS`、`EKS_CAPABILITY_ARGOCD_REPOSERVER_LOGS`、`EKS_CAPABILITY_ARGOCD_SERVER_LOGS` |

配信ソースを設定する前に、実際の capability ARN を取得します。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
: "${CAPABILITY_NAME:?Set the actual capability name}"
aws eks describe-capability --region "$AWS_REGION" \
  --cluster-name "$CLUSTER_NAME" --capability-name "$CAPABILITY_NAME" \
  --query 'capability.capabilityArn' --output text
```

所有者は、この ARN／ログタイプを指定して PutDeliverySource を設定し、承認済みの送信先で PutDeliveryDestination を設定してから、CreateDelivery で両者を接続します。配信を有効にする前に、送信先ポリシー、暗号化、クロスアカウント権限、保持期間を確認してください。

CloudWatch Logs の送信先では Logs Insights クエリを実行できます。S3 の送信先は、選択した S3／Athena ワークフロー用のオブジェクトであり、Firehose は設定されたターゲットにレコードを送信します。これらは CloudWatch Logs Insights から自動的にクエリされるものではありません。ACK のレコードには、サービスコントローラーのフィルタリングに使用できる controllerGroup が含まれます。実際の配信とクエリフィールドを確認し、Vended Logs の料金を考慮してください。

配信ソースを追加するたびに capability は数秒間 `UPDATING` となり、その間にさらに変更すると `ConflictException` が発生します（2026年10月のテストでは約6.6～7秒）。ソースは一度に1つずつ追加し、`ACTIVE` になるまで待ってください。capability 全般については、[EKS Capabilities](./13-eks-capabilities.md) を参照してください。

参照先: [EKS コントロールプレーンのログ記録](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)、[監査ポリシーとクエリ例](https://docs.aws.amazon.com/eks/latest/best-practices/auditing-and-logging.html)、[capability controller のログ](https://docs.aws.amazon.com/eks/latest/userguide/capabilities-controller-logs.html)。

## コンテナのログ記録

コンテナランタイムは、stdout/stderr をノードの CRI ログファイルに書き込みます。kubelet はローテーションを管理し、Pod のログアクセスを提供します。コレクターはファイルを追跡して、選択したバックエンドにレコードを転送します。JSON 形式のアプリケーションメッセージも CRI ラッパーの中にあるため、コンテナログの行全体を Docker JSON として解析してはいけません。

<!-- Audit: parent diagram repair needed for direct control-plane delivery and runtime-versus-kubelet log responsibilities.
![Architecture diagram showing container stdout/stderr picked up by kubelet, read by a log agent, and fanned out to CloudWatch Logs, Amazon OpenSearch, and Amazon S3.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-1.html)
-->

### コレクターの管理者を選ぶ

CloudWatch Observability アドオンにはコンテナログコレクターが含まれます。これを選択したスタックとして使用する場合は、その管理対象の設定を使ってください。以下の単独 Fluent Bit の例は、ログパイプラインを独立して管理する場合の代替案です。重複とコストについて明示的な計画がない限り、同じファイル／送信先に対してコレクターを重複してインストールしないでください。

### 接続済み Fluent Bit の例

この例では、公開済みのリリースと設定を確認した AWS chart 0.2.0 と image 3.4.14（Fluent Bit 5.0.9）を使用します。対象は所有管理下の Linux/containerd EC2 ノードです。affinity の設定では、この例の対象から Fargate、Auto Mode、Hybrid のラベルを意図的に除外しています。これらのモードでは、個別にサポートされた収集／ID 設計が必要です。このコレクターは選択されたノードの taint を許容するため、配置とプラットフォームエージェントの admission 権限を確認してください。

namespace logging、ServiceAccount logging/eks-log-collector 用の最小権限 IRSA ロール EKSLogWriter、所有管理下の CloudWatch ロググループを準備します。アカウント、ロール、リージョン、クラスター固有のロググループを、一貫して置き換えてください。セキュリティの章で説明するように、IAM OIDC provider／信頼 audience／subject を設定します。コレクターには CloudWatch のストリーム／書き込み権限と、リージョン STS／バックエンドへの接続性が必要です。これらの IAM 前提条件は Kubernetes メタデータ RBAC とは別です。

fluent-bit-values.yaml として保存します。

```yaml
fullnameOverride: eks-log-collector
image:
  tag: 3.4.14
serviceAccount:
  create: true
  name: eks-log-collector
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/EKSLogWriter
nodeSelector:
  kubernetes.io/os: linux
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: eks.amazonaws.com/compute-type
          operator: NotIn
          values:
          - fargate
          - auto
          - hybrid
tolerations:
- operator: Exists
service:
  extraService: 'Flush 5

    Log_Level info

    Daemon Off

    HTTP_Server On

    HTTP_Listen 0.0.0.0

    HTTP_Port 2020

    Health_Check On

    storage.path /var/fluent-bit/state/storage

    storage.sync normal

    storage.checksum On

    storage.backlog.mem_limit 20M

    '
input:
  path: /var/log/containers/*.log
  db: /var/fluent-bit/state/tail.db
  multilineParser: cri
  skipLongLines: 'On'
  extraInputs: 'storage.type filesystem

    Read_from_Head On

    '
filter:
  kubeURL: https://kubernetes.default.svc:443
  mergeLog: 'On'
  mergeLogKey: data
  keepLog: 'On'
  k8sLoggingParser: 'Off'
  k8sLoggingExclude: 'Off'
  extraFilters: 'Use_Kubelet Off

    '
cloudWatch:
  enabled: false
cloudWatchLogs:
  enabled: true
  region: us-west-2
  logGroupName: /aws/eks/my-cluster/application
  logStreamPrefix: unmatched-
  logStreamTemplate: $kubernetes['namespace_name'].$kubernetes['pod_name'].$kubernetes['container_name']
  autoCreateGroup: false
  extraOutputs: 'auto_create_group false

    storage.total_limit_size 512M

    '
volumes:
- name: varlog
  hostPath:
    path: /var/log
    type: Directory
- name: state
  hostPath:
    path: /var/lib/eks-log-collector
    type: DirectoryOrCreate
volumeMounts:
- name: varlog
  mountPath: /var/log
  readOnly: true
- name: state
  mountPath: /var/fluent-bit/state
```

Chart 0.2.0 では、ネイティブの cloudWatchLogs output がデフォルトで有効になり、旧来の cloudWatch output は無効になります。そのため cloudWatch.region だけを設定しても、アクティブなネイティブ output は設定されません。上記の値では、実際の output のリージョン／グループを設定し、レコード全体を保持しています。log_key を使うと選択した値だけが送信され、Kubernetes のコンテキストが失われる可能性があります。

logStreamTemplate は、フォールバック用のプレフィックスを伴う record-accessor 構文を使用します。logStreamPrefix はリテラルのプレフィックスであり、レコードごとに評価される Kubernetes 式ではありません。CRI multiline parser がコンテナのラッパーを処理し、Merge_Log は JSON アプリケーションフィールドを data の下に配置し、log を保持します。ワークロードのアノテーションによって parser を選択したり、この例の収集対象から除外したりすることはできません。

### レンダリング時にメタデータ RBAC を制限する

公開 chart の広範な ClusterRole には、nodes/proxy と旧式の PodSecurityPolicy ルールが含まれています。この API server メタデータモードでは Use_Kubelet Off を明示的に設定しており、選択した Pod／Namespace の読み取り権限が必要ですが、kubelet proxy へのアクセスは必要ありません。次の Python 3 + PyYAML post-renderer を fluent-bit-rbac.py として保存します。別の広範なロールが設定されていても黙ってそのままにせず、想定外の chart ID を拒否します。

```python
#!/usr/bin/env python3
"""Helm post-renderer for this pinned, owned metadata-only Fluent Bit setup."""
import sys
import yaml

objects = [obj for obj in yaml.safe_load_all(sys.stdin) if obj is not None]
roles = [obj for obj in objects if obj.get("kind") == "ClusterRole"]
bindings = [obj for obj in objects if obj.get("kind") == "ClusterRoleBinding"]
if len(roles) != 1 or roles[0].get("metadata", {}).get("name") != "eks-log-collector":
    raise SystemExit("Unexpected chart RBAC; review this renderer before proceeding")
if len(bindings) != 1 or bindings[0].get("roleRef", {}).get("name") != "eks-log-collector":
    raise SystemExit("Unexpected chart role binding")
subjects = bindings[0].get("subjects", [])
if len(subjects) != 1 or any(
    subjects[0].get(key) != value
    for key, value in {
        "kind": "ServiceAccount", "name": "eks-log-collector", "namespace": "logging"
    }.items()
):
    raise SystemExit("Unexpected collector identity")
if any(obj.get("kind") == "PodSecurityPolicy" for obj in objects):
    raise SystemExit("Obsolete PodSecurityPolicy output is not supported by this example")
roles[0]["rules"] = [{
    "apiGroups": [""],
    "resources": ["namespaces", "pods"],
    "verbs": ["get", "list", "watch"],
}]
yaml.safe_dump_all(objects, sys.stdout, sort_keys=False)
```

新しい所有管理下のリリースでは、値と renderer を組み合わせてインストールします。

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
chmod +x fluent-bit-rbac.py
helm install eks-log-collector eks/aws-for-fluent-bit \
  --version 0.2.0 --namespace logging --create-namespace \
  -f fluent-bit-values.yaml --post-renderer ./fluent-bit-rbac.py \
  --wait --timeout 5m
```

アップグレードのたびに、同じ確認済み post-renderer を使用してください。chart バージョン、リリース ID、namespace、メタデータモードを変更する場合は、改めて検証してください。レンダリングされた ConfigMap は実際の DaemonSet にマウントされます。無関係な ConfigMap を適用しても設定は変わりません。アカウント／IRSA ロールとロググループは前提条件であり、この chart の例で作成されるリソースではありません。

### バッファリング、ローテーション、障害時の動作

ホストログは読み取り専用で、チェックポイントとファイルシステムバッファーの状態は別のノードローカルディレクトリを使用します。tail データベースはオフセットを記録するものであり、それ自体が永続的なバックエンドアーカイブではありません。ノードを置き換えると、その状態が失われる場合があります。チェックポイントがないとき、Read_from_Head On は保持されているファイル内容を読み取るため、バックフィルと重複処理を計画してください。

512M の output-queue 上限と backlog メモリ設定は、割り当ての例です。output キューが storage.total_limit_size に達すると、Fluent Bit は最も古いチャンクを破棄することがあります。Skip_Long_Lines On も、大きすぎるレコードを意図的にスキップします。有限のバッファー、再試行、ノードローカルの状態によって、損失のない配信や厳密に1回の配信が保証されるわけではありません。再試行、破棄されたレコード、ディスク容量、送信先の障害を監視し、実際のログレートと停止時間に合わせて上限を検証してください。

### OpenSearch への任意のファンアウト

所有管理下の VPC domain と、コレクターの IAM／FGAC マッピングを準備した後、この overlay を fluent-bit-opensearch-values.yaml として保存し、endpoint のホスト名を置き換えます。同じ確認済み Helm 操作に `-f fluent-bit-opensearch-values.yaml` を追加してください。CloudWatch を有効にしたままにすると、両方の送信先にコピーが送られます。OpenSearch のみを意図的に選択する場合に限り、cloudWatchLogs.enabled=false を設定します。

```yaml
opensearch:
  enabled: true
  host: vpc-eks-logs-EXAMPLE.us-west-2.es.amazonaws.com
  port: '443'
  tls: 'On'
  awsAuth: 'On'
  awsRegion: us-west-2
  index: eks-logs
  generateId: 'On'
  suppressTypeName: 'On'
  extraOutputs: 'tls.verify On

    storage.total_limit_size 512M

    '
```

TLS の証明書／ホスト名検証を有効にし、固定されたガバナンス対象の index／rollover 設計を使用してください。Pod ごとの index パターンは、index／shard 数を過剰に増やす可能性があります。Generate_ID は再試行時の重複インデックス登録を減らしますが、個々の output と障害復旧については依然として検証が必要です。一方の送信先への書き込み成功は、もう一方への配信を証明するものではありません。

### その他のログスタック

所有管理下の deployment で必要な parser／output plugin、ホストマウント、ID、TLS 設定を用意できる場合、Fluentd も選択肢です。汎用 JSON parser は CRI wrapper をデコードしません。また、ssl_verify の無効化は証明書エラーの解決策ではありません。旧 Elastic Helm chart リポジトリはアーカイブ済みです。Elastic deployment には、保守されている製品／Operator のインストール手順を使用してください。

loki-stack chart は非推奨とされ、Promtail agent は2026年3月2日に EOL を迎えました。Loki には、Alloy などのサポート対象クライアントを含む、現行のサポート対象 deployment を使用し、ストレージ、アクセス制御、保持期間を明示的に設定してください。専用の設定手順については、[Loki ガイド](../observability/logging/01-loki.md)と[コレクターガイド](../observability/logging/05-collectors.md)を参照してください。Promtail agent の終了は、別途保守されている lambda-promtail クライアントには適用されません。

### 構造化アプリケーションログ

以下の保持された例は、合成されたアプリケーションデータであり、新たな測定値やこの監査の記録ではありません。タイムスタンプは元の例示値のままです。

```json
{
  "timestamp": "2025-07-11T13:00:00Z",
  "level": "INFO",
  "message": "Request processed successfully",
  "request_id": "12345",
  "user_id": "user-789",
  "duration_ms": 45,
  "status_code": 200
}
```

設定済みのパイプラインでは、CRI レコードが転送時のタイムスタンプを提供し、アプリケーション JSON は data の下に格納されます。アプリケーションフィールドでタイムスタンプを上書きする前に、タイムゾーンとクロックの動作を確認してください。ユーザー／セッション ID は依然として機微情報であったり、個人を関連付ける情報であったりする可能性があります。最小限に抑え、認証情報や生のセッショントークンは決して記録しないでください。

次の例は、このコレクターのレコード形式を前提としています。ほかのコレクターではフィールドパスが異なる場合があります。

```text
fields @timestamp, kubernetes.namespace_name, kubernetes.pod_name, data.level, log
| filter kubernetes.namespace_name = "production"
| filter data.level in ["ERROR", "error"]
| sort @timestamp desc
| limit 100
```

検証では、公開 chart／image のメタデータ、実際の Helm ConfigMap／DaemonSet の配線、ネイティブ Kubernetes schema、post-renderer の失敗ケースを確認しました。image はインストールしておらず、コレクタープロセスも起動していません。AWS ログの送信や本番ファイルシステムへのアクセスもテストしていません。展開前に、実際のノード権限、IRSA 認証情報、エンドツーエンドの配信を検証してください。

参照先: [AWS image release 3.4.14](https://github.com/aws/aws-for-fluent-bit/releases/tag/v3.4.14)、[CloudWatch output](https://docs.fluentbit.io/manual/data-pipeline/outputs/cloudwatch)、[Fluent Bit buffering](https://docs.fluentbit.io/manual/data-pipeline/buffering)、[Promtail lifecycle](https://grafana.com/docs/loki/latest/send-data/promtail/)。

## クラスターのモニタリング

EKS クラスターの状態、パフォーマンス、リソース使用量を追跡するには、効果的なクラスターのモニタリングが不可欠です。このセクションでは、EKS クラスターをモニタリングするためのさまざまなツールと手法について説明します。

![EKS クラスターの監視対象（クラスター、ノード、Pod レベルのテレメトリ）に、監視ソリューション（AMP/AMG を使った CloudWatch Container Insights、kube-state-metrics、Node Exporter、Grafana を使った Prometheus スタック、X-Ray/OpenTelemetry のトレース）を対応付けた図。](../.gitbook/assets/en-eks-06-eks-monitoring-logging-2.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-2.html)

### CloudWatch Container Insights

CloudWatch Observability アドオンは、Container Insights、コンテナログ収集、Application Signals の機能を組み合わせています。所有管理下のインストールを1つだけ使用し、同じファイルを読む別のコレクターと Fluent Bit コレクターを重複させないでください。データを期待する前に、ID、サポート対象ノードへのアクセス、バックエンド接続を設定してください。

#### クラスターと互換性のあるアドオンのビルドを確認する

この標準的な Linux EC2 の例では、適切な EKS Pod Identity agent と専用の CloudWatch ロールを準備し、信頼をこのクラスターと amazon-cloudwatch/cloudwatch-agent に限定します。運用担当者には、必要なアドオン／関連付けの権限と、承認済みロールを渡す権限が必要です。EKS アドオン一覧に加え、既存の Helm release、ServiceAccount アノテーション、関連付けも確認してください。既存コレクターがある場合は、その所有者の移行／アップグレード手順が必要です。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
CLUSTER_VERSION=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.version --output text)
aws eks list-addons --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
aws eks describe-addon-versions --region "$AWS_REGION" \
  --addon-name amazon-cloudwatch-observability --kubernetes-version "$CLUSTER_VERSION"
```

固定の v5.0.0 の例にダウングレードするのではなく、カタログから互換性のある確認済みビルドを選択します。アドオンの設定 schema はバージョンごとに異なります。ここでのローカル参照レンダリングでは Helm chart 6.6.0 を使用し、その Fluent Bit DaemonSet は agent の ID 経路と同じ cloudwatch-agent ServiceAccount を使用します。

#### Auto Monitor の明示的な設定

新規インストールの例では、以下を cloudwatch-config.json として保存します。アプリケーションの rollout を確認するまで、デフォルトのコンテナログ設定は保持し、広範なワークロード自動選択と自動再起動は無効にしています。

```json
{
  "manager": {
    "applicationSignals": {
      "autoMonitor": {
        "monitorAllServices": false,
        "restartPods": false
      }
    }
  }
}
```

これは Auto Monitor の選択／再起動を制御するものであり、考えられるすべてのテレメトリソースを制御するわけではありません。既存のアノテーション、カスタムセレクター、手動計装されたアプリケーションについては別途確認が必要です。Python 3 と jsonschema がローカルで利用できる環境で、選択したビルドの schema を取得し、設定を検証します。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the cluster Region}"
: "${CLOUDWATCH_ADDON_VERSION:?Choose a reviewed compatible add-on build}"
aws eks describe-addon-configuration --region "$AWS_REGION" \
  --addon-name amazon-cloudwatch-observability --addon-version "$CLOUDWATCH_ADDON_VERSION" \
  --output json > cloudwatch-addon-review.json
python3 - "$CLOUDWATCH_ADDON_VERSION" <<'PY'
import json
import sys
import jsonschema
with open("cloudwatch-addon-review.json") as stream:
    review = json.load(stream)
if review["addonName"] != "amazon-cloudwatch-observability" or review["addonVersion"] != sys.argv[1]:
    raise SystemExit("Returned schema does not match the selected add-on build")
schema = json.loads(review["configurationSchema"])
with open("cloudwatch-config.json") as stream:
    config = json.load(stream)
validator = jsonschema.validators.validator_for(schema)
validator.check_schema(schema)
validator(schema).validate(config)
PY
```

#### 新しい所有管理下のインストールを作成する

選択した機能に必要な CloudWatch／trace 権限を、CloudWatch ロールにあらかじめ付与しておく必要があります。以下では、確認済みの schema／ビルドを再確認し、既存のアドオンやコレクターの関連付けがあれば拒否して、競合するリソースを引き継がないようにします。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the reviewed cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
: "${CLOUDWATCH_ADDON_VERSION:?Set the reviewed, schema-checked compatible build}"
: "${CLOUDWATCH_ROLE_ARN:?Set the prepared CloudWatch Pod Identity role ARN}"
python3 - "$CLOUDWATCH_ADDON_VERSION" <<'PY'
import json
import sys
import jsonschema
with open("cloudwatch-addon-review.json") as stream:
    review = json.load(stream)
if review["addonName"] != "amazon-cloudwatch-observability" or review["addonVersion"] != sys.argv[1]:
    raise SystemExit("Selected add-on build changed; review its schema again")
schema = json.loads(review["configurationSchema"])
with open("cloudwatch-config.json") as stream:
    config = json.load(stream)
jsonschema.validators.validator_for(schema)(schema).validate(config)
PY
EXISTING_ADDONS=$(aws eks list-addons --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" --output json)
python3 - "$EXISTING_ADDONS" <<'PY'
import json, sys
if "amazon-cloudwatch-observability" in json.loads(sys.argv[1])["addons"]:
    raise SystemExit("Add-on already exists; use its owner's reviewed upgrade procedure")
PY
EXISTING_ASSOCIATIONS=$(aws eks list-pod-identity-associations \
  --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --namespace amazon-cloudwatch --service-account cloudwatch-agent --output json)
python3 - "$EXISTING_ASSOCIATIONS" <<'PY'
import json, sys
if json.loads(sys.argv[1])["associations"]:
    raise SystemExit("Collector association already exists; inspect its owner before installation")
PY
ASSOCIATIONS=$(python3 - "$CLOUDWATCH_ROLE_ARN" <<'PY'
import json, sys
print(json.dumps([{"serviceAccount": "cloudwatch-agent", "roleArn": sys.argv[1]}]))
PY
)
aws eks create-addon --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --addon-name amazon-cloudwatch-observability --addon-version "$CLOUDWATCH_ADDON_VERSION" \
  --pod-identity-associations "$ASSOCIATIONS" \
  --configuration-values file://cloudwatch-config.json --resolve-conflicts NONE
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --addon-name amazon-cloudwatch-observability \
  --query 'addon.{Status:status,Version:addonVersion,Health:health.issues}'
```

CreateAddon は非同期です。アドオンが ACTIVE になるまで状態／ヘルスを確認し、その後、agent／collector Pod、実際の ContainerInsights datapoint、意図したロググループを検証します。リクエストの成功、ACTIVE 状態、ダッシュボードだけでは、完全な取り込みの証明になりません。上記の最後の DescribeAddon コマンドは確認用であり、完了を待つコマンドではありません。再試行の前に、障害と権限を検証してください。インストールを強制するために、未確認の上書きを使用したり、既存の設定を消去したりしないでください。

#### バージョン 5.0.0 での変更点

2026年2月26日のデフォルト APM の変更は実際のものです。バージョン 5.0.0 以降では、新規インストールとアップグレードで Application Signals Auto Monitor がデフォルトで有効になります。monitorAllServices のデフォルトは true、restartPods のデフォルトは false です。対象は、サポートされているサービスマッピング済みの Deployment、DaemonSet、StatefulSet で、デフォルトでは kube-system と amazon-cloudwatch を除外します。対象範囲内の新規または再起動されたワークロードには、ワークロードごとのアノテーションなしで計装が適用されることがあります。すでに実行中の Pod がすぐに再計装されるとは限りません。

サポート対象の言語／ワークロードを選択し、既存の OpenTelemetry／APM 統合、サンプリング、コストを確認して、再起動 rollout を制御してください。明示的な除外が優先されます。Container Insights は Linux と Windows の設定をサポートしていますが、Application Signals は EKS Windows ノードではサポートされません。Fargate と Hybrid のノード収集／ID には文書化されたプラットフォーム固有の経路が必要です。一般的な DaemonSet の例からサポートを推測しないでください。

#### メトリクス、ダッシュボード、アラーム

Container Insights のコンソールビューでは実際のクラスターを選択し、公開済みのメトリクス名、ディメンション、最近のデータを確認します。ノード CPU／メモリ／ファイルシステムのメトリクスはノード使用量を表します。Pod の CPU／メモリ使用率では、分母にノードの limit が使われ、Pod の request は使われません。文書化されたメトリクスでは namespace／service／cluster の集計値も利用できますが、集計パーセンテージが異種クラスターの容量加重使用率になるとは限りません。

ダッシュボードはデータの確認に役立ちますが、すべてのアラームを作成したり、通知の配信を保証したりするものではありません。後述の CloudWatch Alarms の例では、ノードメトリクスと Maximum、および明示的に選択したディメンションを使用します。メトリクスの利用可能性を確認し、ワークロードに適したアラームと配信経路を設定してください。

検証では、公開済みの既存 chart、そのレンダリング済みデフォルトログ設定、Auto Monitor 引数に加え、schema／所有権／失敗フローについて9つのモックケースを確認しました。合成テスト用 schema は補助ツールの動作確認に使用したものであり、上記のライブ環境におけるビルド固有 schema の代替にはなりません。この監査では、アドオン、ワークロード計装、テレメトリのエクスポート、AWS リソースのいずれも実行していません。

参照先: [CloudWatch アドオンのインストールと Auto Monitor](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Observability-EKS-addon.html)、[デフォルト APM の発表](https://aws.amazon.com/about-aws/whats-new/2026/02/application-performance-monitoring-cloudwatch-eks/)、[Container Insights のメトリクス](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html)。

### EKS Node Monitoring Agent

EKS Node Monitoring Agent は、ノードレベルのシステム、ストレージ、ネットワーク、アクセラレーターのヘルス状態を公開します。2026年2月24日にオープンソース化され、EKS Auto Mode に含まれています。個別に管理するアドオンとしてインストールする場合は、リリースを選ぶ前に、クラスターの実際のバージョン、既存アドオン、互換性のある agent のバージョンを確認してください。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
KUBERNETES_VERSION=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.version --output text)
aws eks list-addons --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
aws eks describe-addon-versions --addon-name eks-node-monitoring-agent \
  --kubernetes-version "$KUBERNETES_VERSION" --region "$AWS_REGION"
```

既存のアドオン所有者を通じ、確認済みバージョンとサポート対象ノード設定でインストールまたは更新します。アドオンの create コマンドは、既存インストールのアップグレード手順ではありません。

Condition 名だけでは、ノードが異常かどうかは判断できません。各 condition の意味を踏まえて、status と reason を読み取ってください。Ready=False と MemoryPressure=False は意味が異なります。

```bash
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{range .status.conditions[*]}{"  "}{.type}{"="}{.status}{" reason="}{.reason}{"\n"}{end}{end}'
```

モニタリングと修復の有効化は別のものです。Auto Mode では自動ノード修復が有効です。マネージドノードグループでは nodeRepairConfig を使用し、Karpenter では NodeRepair feature gate を使用します。修復動作を agent に帰属させる前に、実際のマネージドノードグループを確認してください。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${NODEGROUP_NAME:?Set an actual managed node group name}"
: "${AWS_REGION:?Set the cluster Region}"
aws eks describe-nodegroup --region "$AWS_REGION" \
  --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --query 'nodegroup.{Name:nodegroupName,Repair:nodeRepairConfig,Health:health.issues}'
```

修復の対象となるかは、condition、reason、待機時間、適用される安全対策によって異なります。文書化されたデフォルトでは、MemoryPressure と DiskPressure に自動修復アクションはありません。報告されたすべての condition や agent のインストールを、ノードが置き換えられる証拠として扱わないでください。オープンソース agent をカスタマイズする場合も、選択した修復設定に対して condition の意味をテストする必要があります。

参照先: [オープンソース化の発表](https://aws.amazon.com/about-aws/whats-new/2026/02/amazon-eks-node-monitoring-agent-open-source/)、[自動ノード修復](https://docs.aws.amazon.com/eks/latest/userguide/node-repair.html)。

### Prometheus と Grafana

Prometheus は時系列データベース兼モニタリングシステムであり、Grafana はメトリクスを可視化するダッシュボードツールです。これら2つのツールを組み合わせることで、EKS クラスターを包括的にモニタリングできます。

#### Amazon Managed Service for Prometheus と Grafana

AMP は取り込んだ Prometheus メトリクスを保存してクエリします。AMG は設定済みのデータソースに対してクエリし、ダッシュボードを表示します。どちらかの workspace を作成しても、スクレイパーのデプロイ、AWS ID の付与、データソースの接続は自動的には行われません。この例では、所有管理下の既存 workspace を確認し、以下の kube-prometheus-stack release を拡張することで、Prometheus を二重にインストールしないようにします。

**AMP の取り込み ID と値**

ServiceAccount monitoring/amp-writer 用に IRSA ロールを準備します。その信頼ポリシーでは、このクラスターの OIDC provider と、正確な `sub=system:serviceaccount:monitoring:amp-writer` および `aud=sts.amazonaws.com` の condition を使用します。対象 workspace ARN に対して aps:RemoteWrite を許可します。Prometheus プロセスは投影された token を受け取り、STS と AMP endpoint に到達できる必要があります。Kubernetes RBAC は別の権限経路です。この例に無関係な Pod Identity 関連付けや静的な AWS key を併用しないでください。

以下では workspace を読み取り、確認済み chart 92.9.0 用の overlay を書き出します。/api/v1/ の有無にかかわらず文書化された endpoint 形式を受け入れ、remote_write を正確に1回だけ追加します。Python 3 が必要です。workspace は作成されません。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the AMP workspace Region}"
: "${AMP_WORKSPACE_ID:?Set the owned AMP workspace ID}"
: "${AMP_WRITE_ROLE_ARN:?Set the prepared IRSA writer role ARN}"
: "${CLUSTER_NAME:?Set the source cluster name}"
aws amp describe-workspace --region "$AWS_REGION" \
  --workspace-id "$AMP_WORKSPACE_ID" --output json > amp-workspace.json
python3 - "$AWS_REGION" "$AMP_WORKSPACE_ID" "$AMP_WRITE_ROLE_ARN" "$CLUSTER_NAME" <<'PY'
import json
import sys
from urllib.parse import urlsplit, urlunsplit

region, workspace_id, role_arn, cluster = sys.argv[1:]
with open("amp-workspace.json") as stream:
    workspace = json.load(stream)["workspace"]
if workspace["workspaceId"] != workspace_id or workspace["status"]["statusCode"] != "ACTIVE":
    raise SystemExit("Review the workspace identity and ACTIVE status")
arn = workspace["arn"].split(":", 5)
if len(arn) != 6 or arn[2] != "aps" or arn[3] != region or arn[5] != "workspace/" + workspace_id:
    raise SystemExit("Workspace ARN does not match the selected Region/ID")
endpoint = urlsplit(workspace["prometheusEndpoint"])
path = endpoint.path.rstrip("/")
if path.endswith("/api/v1"):
    path = path[:-7]
if (endpoint.scheme != "https" or not endpoint.hostname or endpoint.username
        or endpoint.password or endpoint.query or endpoint.fragment
        or path != "/workspaces/" + workspace_id):
    raise SystemExit("Inspect the workspace endpoint before configuring remote write")
remote_write = urlunsplit((endpoint.scheme, endpoint.netloc, path + "/api/v1/remote_write", "", ""))
values = {
    "prometheus": {
        "serviceAccount": {
            "create": True, "name": "amp-writer", "createTokenSecret": True,
            "annotations": {"eks.amazonaws.com/role-arn": role_arn},
        },
        "prometheusSpec": {
            "externalLabels": {"cluster": cluster},
            "remoteWrite": [{"url": remote_write, "sigv4": {"region": region}}],
        },
    },
}
with open("amp-values.json", "w") as stream:
    json.dump(values, stream, indent=2)
    stream.write("\n")
print("Wrote amp-values.json; review it with all existing release values")
PY
```

amp-values.json を monitoring-values.yaml と組み合わせ、所有者が確認済みのインストール／アップグレード用の値に含めます。この overlay は remoteWrite のリストを置き換えるため、既存の送信先と external label を意図的に保持してください。新しい release では、以下のインストールコマンドに -f amp-values.json を追加します。既存 release では現在のすべての設定を保持し、所有者のアップグレード手順を適用する前に、レンダリング差分と rollout を確認してください。ServiceAccount を変更すると Prometheus Pod の ID も変わります。Chart 92.9.0 では、デフォルトの API server／kubelet ServiceMonitor 認証に、明示的な ServiceAccount token Secret が使用されます。この Secret を保護し、ローテーション／失効手順に従ってください。この Secret は、有効期間が短く audience が限定された IRSA token とは別のものです。createTokenSecret を無効にし、依存するすべての monitor credential を置き換えないと、レンダリングまたは認証に失敗します。

複数の replica を使用する場合は、重複スクレイプを無償と考えず、AMP の文書化された HA deduplication label と replica topology を設定してください。実際のワークロードを基に、cardinality、保持期間、取り込み予算を設定します。remote-write の失敗／backlog を確認し、対象 workspace で最近のデータをクエリしてください。Helm rollout の成功は、取り込みの証明ではありません。

**AMG の認証とデータソース接続**

```bash
set -euo pipefail
: "${AMG_REGION:?Set the Grafana workspace Region}"
: "${AMG_WORKSPACE_ID:?Set the owned Grafana workspace ID}"
aws grafana describe-workspace --region "$AMG_REGION" \
  --workspace-id "$AMG_WORKSPACE_ID" \
  --query 'workspace.{ID:id,Status:status,Version:grafanaVersion,Endpoint:endpoint,Role:workspaceRoleArn,Authentication:authentication,PermissionType:permissionType}'
```

workspace ユーザー認証（IAM Identity Center／SAML）、Grafana ユーザー権限、workspace の AWS data-source IAM role は、それぞれ異なる統制です。Grafana service account は Grafana HTTP API 用の ID です。ADMIN service account を作成しても、AMP data source は作成されず、aps:QueryMetrics も許可されません。メトリクスを閲覧するだけの目的で、広範な API ID を用意しないでください。

AMG 12 以降では、Amazon Managed Service for Prometheus data-source plugin を選択します。そのバージョンの AMG では、Core Prometheus plugin から SigV4 サポートが削除され、既存の AMP data source は AMP plugin に移行されます。workspace の実際のバージョンに対応するドキュメントを使用してください。承認済みの workspace 設定を通じて、対象のアカウント／リージョン／workspace を選び、クエリ ID を設定して既知の series をテストします。文書化された AWS data-source の設定フローではサービス管理権限を使用します。カスタマー管理の workspace には個別に確認済みの IAM 設定が必要で、自動的に所有権が変更されるわけではありません。

通常、クエリロールには workspace を対象範囲とする aps:QueryMetrics、aps:GetSeries、aps:GetLabels、aps:GetMetricMetadata が必要です。探索やその他の有効機能には追加アクションが必要な場合があります。クエリ endpoint は remote_write 取り込み URL ではありません。workspace を個別にプロビジョニングする場合、CLI では --workspace-name を使用し、--account-access-type、認証、権限設定が必要です。サービス管理 IAM の自動化は、文書化されたコンソールのワークフローに関連付けられています。workspace を利用可能とみなす前に、ID、ユーザー割り当て、ネットワークアクセスを設定してください。

参照先: [AMP remote write](https://docs.aws.amazon.com/prometheus/latest/userguide/AMP-onboard-ingest-metrics-existing-Prometheus.html)、[AMG AMP plugin](https://docs.aws.amazon.com/grafana/latest/userguide/amazon-prometheus-data-source.html)、[AWS data-source configuration](https://docs.aws.amazon.com/grafana/latest/userguide/amazon-AMP-adding-AWS-config.html)。この監査では workspace、認証フロー、テレメトリの取り込みを実行していません。

#### セルフマネージド Prometheus と Grafana

この例では、ServiceMonitor と PrometheusRule の例に必要な Prometheus Operator を含む、所有管理下の kube-prometheus-stack release を1つ使用します。単独の Prometheus chart だけでは、それらの CRD／controller は自動的には提供されません。インストール前に、既存 Operator、release、CRD の所有者を確認してください。既存スタックについては、所有者のアップグレード手順を使用します。

確認済みのベースラインは chart 92.9.0／Operator 0.94.1 で、EKS 1.36 向けにレンダリングされています。標準的な Linux EC2 ノードと、EBS CSI 権限が機能するよう準備された暗号化済みの ebs-gp3 StorageClass を前提としています。Auto Mode や別のストレージ実装の場合は、実際にサポートされる class とノード配置を選択してください。以下の保持期間と PVC サイズは割り当ての例であり、測定済みの容量を保証するものではありません。

承認済みのシークレット管理プロセスを通じて、namespace monitoring と、admin-user／admin-password key を持つ Secret grafana-admin を準備します。この値設定では、共有パスワードを Helm values やコマンド引数に記述せず、Secret を参照します。以下を monitoring-values.yaml として保存してください。

```yaml
grafana:
  admin:
    existingSecret: grafana-admin
    userKey: admin-user
    passwordKey: admin-password
  service:
    type: ClusterIP
  rbac:
    namespaced: true
  sidecar:
    dashboards:
      searchNamespace: monitoring
    datasources:
      searchNamespace: monitoring
  persistence:
    enabled: true
    storageClassName: ebs-gp3
    size: 10Gi
    accessModes:
    - ReadWriteOnce
  deploymentStrategy:
    type: Recreate
prometheus:
  prometheusSpec:
    retention: 14d
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: ebs-gp3
          accessModes:
          - ReadWriteOnce
          resources:
            requests:
              storage: 20Gi
kubeEtcd:
  enabled: false
kubeControllerManager:
  enabled: false
kubeScheduler:
  enabled: false
kubeProxy:
  enabled: false
kubelet:
  serviceMonitor:
    tlsConfig:
      insecureSkipVerify: false
      ca:
        configMap:
          name: kubelet-serving-ca
          key: ca.crt
```

Grafana の dashboard／data-source sidecar は、namespaced role で monitoring のみを監視します。ClusterIP Service には port-forwarding でローカルからアクセスします。単一 replica の PVC の例では、rollout 中に書き込み元が重複しないよう Recreate を使用するため、置き換え時の UI 停止を計画してください。これは高可用な Grafana の設計ではありません。

chart のデフォルトでは、kubelet server certificate の検証がスキップされます。これらの値では代わりに、信頼済み kubelet serving CA chain を含む ca.crt を設定した monitoring/kubelet-serving-ca ConfigMap と、スクレイプ対象 endpoint に一致する SAN を持つ証明書が必要です。ノード所有者の証明書管理プロセスを通じて、その信頼性を確認してください。EKS API server の CA が kubelet serving CA と同じとは限りません。この前提条件を満たせない場合は、収集を有効にする前に証明書設定を解決してください。target を正常に見せるために、insecureSkipVerify を黙って元に戻さないでください。この監査では kubelet TLS handshake をテストしていません。

この例では etcd／controller-manager／scheduler／kube-proxy のスクレイプジョブを無効にしています。設定からは、直接アクセス可能な endpoint が提供されないためです。実際に到達可能で認可された endpoint を設定した後にのみジョブを有効にしてください。API server や CloudWatch のメトリクスは別のソースであり、存在しないコンポーネントの ServiceMonitor target を機能させるものではありません。

新しい所有管理下の release では、次のようにします。

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update prometheus-community
helm install monitoring prometheus-community/kube-prometheus-stack \
  --version 92.9.0 --namespace monitoring --create-namespace \
  -f monitoring-values.yaml --wait --timeout 10m
```

Helm の待機が完了しても、Operator が作成したすべてのリソース、target、通知経路が機能する証拠にはなりません。生成されたリソース、PVC のバインド、Prometheus target のヘルス、メトリクスデータを確認してください。

```bash
kubectl get pods,svc,pvc -n monitoring
kubectl get prometheus,alertmanager -n monitoring
```

このコマンドの実行中に、承認済みシークレットストアの認証情報を使って、`http://127.0.0.1:3000` で Grafana にアクセスします。

```bash
kubectl port-forward --address 127.0.0.1 -n monitoring \
  svc/monitoring-grafana 3000:80
```

Grafana のデータベース／PVC と、エクスポートしたダッシュボード定義を保護してください。Grafana がサポートする認証情報のローテーション手順を使います。bootstrap Secret を変更しただけでは、既存データベースのユーザーのパスワードが変更された証明にはなりません。サンプル用の共有パスワードで UI を公開しないでください。

chart のレンダリングでは、実際の Prometheus Service monitoring-kube-prometheus-prometheus、Grafana Service monitoring-grafana、data-source UID prometheus を確認できます。カスタム ServiceMonitor／PrometheusRule は、この release が使用する release=monitoring の selector に一致させる必要があります。レンダリング済みマニフェストと schema チェックはローカルの証跡です。実際のクラスターでスタック、PVC、ログインを試してはいません。

参照先: [kube-prometheus-stack chart とアップグレードのガイダンス](https://github.com/prometheus-community/helm-charts/tree/kube-prometheus-stack-92.9.0/charts/kube-prometheus-stack)。

#### 主要な Prometheus メトリクス

メトリクスの利用可能性は、ダッシュボード名だけではなく、実際のスクレイプ target と権限に依存します。

- Node exporter は、サポート対象ノードの CPU、メモリ、ファイルシステム、ネットワークの series を提供します。
- Kubelet／cAdvisor はコンテナのリソースメトリクスを提供し、kube-state-metrics は再起動や readiness など Kubernetes object の状態を提供します。
- API server は、認可された API メトリクスを公開します。etcd／controller-manager／scheduler の直接メトリクスには、それぞれ到達可能な endpoint が必要です。上記の設定では、それらの target を有効にしていません。

series が見つからない場合、exporter が存在しない、スクレイプに失敗した、プラットフォームが未対応、メトリクスが変更された、などの可能性があります。使用量ゼロやシステム正常を自動的に意味するものではありません。

#### 便利な Grafana ダッシュボード

確認済みの kube-prometheus-stack release に同梱された Kubernetes、node-exporter、API-server のダッシュボードから始め、prometheus data-source UID を選択します。コミュニティダッシュボード ID だけでは、互換性のあるメトリクス／label の契約は保証されません。インポートした各ダッシュボードのクエリ、単位、必要な recording rule、data-source 参照を確認してください。データのないグラフは、監視対象コンポーネントが正常である証拠ではありません。

以前に掲載されていたコミュニティ ID は現在も存在しますが、タイトルや想定用途に誤りがあるものがあります。カタログで確認した結果は次のとおりです。インポート／実行時の互換性はテストしていません。

| ID | 実際のカタログタイトル | 対象範囲の注記 |
| --- | --- | --- |
| [15661](https://grafana.com/grafana/dashboards/15661-k8s-dashboard-en-20250125/) | K8S Dashboard | K8S リソース全般の概要 |
| [1860](https://grafana.com/grafana/dashboards/1860-node-exporter-full/) | Node Exporter Full | 対応する node-exporter series が必要 |
| [6417](https://grafana.com/grafana/dashboards/6417-kubernetes-cluster-prometheus/) | Kubernetes Cluster (Prometheus) | クラスター／コンテナの概要。最終更新はカタログ上2018年 |
| [12006](https://grafana.com/grafana/dashboards/12006-kubernetes-apiserver/) | Kubernetes apiserver | API server latency／cache ダッシュボード。最終更新はカタログ上2020年 |
| [13770](https://grafana.com/grafana/dashboards/13770-1-kubernetes-all-in-one-cluster-monitoring-kr/) | 1 Kubernetes All-in-one Cluster Monitoring KR | 書籍の VM 環境向けに最適化された韓国語のオールインワンダッシュボード |

#### PromQL クエリ例

これらの例は、確認済みスタックの job および metrics_path label に一致します。特に共有 AMP workspace では、Pod の namespace ID と、存在する場合は cluster label を維持してください。Prometheus の external label はデータを外部に送信するときに付加されますが、ローカルに保存されたすべての series に自動的に表示されるわけではありません。max 集計は、同じ ID を持つ object の重複観測をまとめるものであり、異なるワークロードをまとめるものではありません。このパターンを応用する前に label を確認してください。

CPU ごとの平均値を使用した、ノードの CPU 非 idle パーセンテージ:

```promql
100 * (1 - avg by (cluster, instance) (max by (cluster, instance, cpu) (rate(node_cpu_seconds_total{job="node-exporter",mode="idle"}[5m]))))
```

コンテナの memory working-set byte 数が多い Pod の上位10件:

```promql
topk(10, sum by (cluster, namespace, pod) (max by (cluster, namespace, pod, container) (container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD"})))
```

現在の Pod UID ごとの再起動カウンター。これは CrashLoopBackOff の検出器ではありません。

```promql
sum by (cluster, namespace, pod, uid) (max by (cluster, namespace, pod, uid, container) (kube_pod_container_status_restarts_total{job="kube-state-metrics"}))
```

ゼロサイズのファイルシステムを除いた、ルートファイルシステムの利用不可パーセンテージ:

```promql
(100 * (1 - max by (cluster, instance, device, mountpoint, fstype) (node_filesystem_avail_bytes{job="node-exporter",mountpoint="/"}) / max by (cluster, instance, device, mountpoint, fstype) (node_filesystem_size_bytes{job="node-exporter",mountpoint="/"}))) and on (cluster, instance, device, mountpoint, fstype) (max by (cluster, instance, device, mountpoint, fstype) (node_filesystem_size_bytes{job="node-exporter",mountpoint="/"}) > 0)
```

ここでの CPU パーセンテージは非 idle 時間を表します。メモリは byte 単位で測定され、再起動は現在の Pod／コンテナのライフタイムにおけるカウンターです。カウンターの変化を調べる場合は、選択した期間に対して rate／increase を使用してください。ファイルシステムの計算では利用可能な領域を使うため、一般ユーザーが利用できない予約領域が含まれることがあります。これらは調査用の例であり、普遍的なアラートしきい値ではありません。

### AWS X-Ray による分散トレース

X-Ray は引き続きサポート対象の trace backend です。X-Ray の SDK と daemon は2026年2月25日にセキュリティ修正のみの保守フェーズに入りました。現在の AWS タイムラインでは、そのフェーズの終了日は公表されていません。新たに計装する場合は、サポート対象の OpenTelemetry／ADOT 統合を使用してください。X-Ray daemon や collector が trace を送信するために Kubernetes の cluster-admin 権限を必要とするわけではありません。また、その Kubernetes ロールによって AWS の書き込み権限が付与されるわけでもありません。

#### コレクターの管理者と前提条件

計装／収集の管理者を1つ選びます。上記の CloudWatch アドオンの Application Signals 経路は代替案です。重複 span や競合を確認せずに、すでに計装済みのプロセスに別の SDK agent を追加しないでください。以下の明示的な例では、OpenTelemetry Operator 0.158.0 と ADOT Collector 0.50.0 を使用し、traces のみのパイプラインを構成します。

コレクターを適用する前に、各所有者を通じて次の依存関係を準備してください。

- 一致する CRD／webhook を備えた稼働中の Operator。公開済みの upstream manifest では cert-manager を使用します。文書化されたインストール／アップグレード手順に従ってください。EKS ADOT アドオンも所有権の別経路であり、ビルド固有の schema が必要です。Collector release には Operator のインストール manifest は含まれていません。
- 専用の tracing-demo namespace と ServiceAccount adot-traces。このクラスター用に、`sub=system:serviceaccount:tracing-demo:adot-traces` および `aud=sts.amazonaws.com` で準備された IRSA trust が必要です。このパイプラインに必要な X-Ray 書き込み action（PutTraceSegments）を許可し、STS／X-Ray への接続性を確保してください。この OTLP 専用コレクターは Kubernetes object を検出しないため、クラスター全体の RBAC は不要です。
- `tls.crt`／`tls.key` を持つ Secret tracing-demo/otel-receiver-tls。adot-traces-collector.tracing-demo.svc に対して有効な server certificate が必要です。信頼する CA をアプリケーションにマウントします。証明書の発行、更新、コレクターの reload／再起動は運用上の責任です。
- NetworkPolicy を適用する CNI と、確認済みのアプリケーション egress。この例では、app=my-app ラベルが付いた default Pod からの ingress を許可します。この設定は専用 tracing-demo namespace 内のすべての Pod に適用されます。ラベルはトラフィックを選択しますが、ワークロードを認証したり、Pod 作成者に対する RBAC 統制の代わりになったりするものではありません。

Collector URL を Operator manifest として適用するのではなく、公開済みの [Operator release](https://github.com/open-telemetry/opentelemetry-operator/releases/tag/v0.158.0) と [ADOT release](https://github.com/aws-observability/aws-otel-collector/releases/tag/v0.50.0) を確認してください。v1beta1 CRD では、spec.config は object 型です。例のリージョンは、env／exporter の両フィールドで同時に変更してください。

```yaml
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: adot-traces
  namespace: tracing-demo
spec:
  mode: deployment
  replicas: 1
  image: public.ecr.aws/aws-observability/aws-otel-collector:v0.50.0
  serviceAccount: adot-traces
  env:
  - name: AWS_REGION
    value: us-west-2
  - name: AWS_EC2_METADATA_DISABLED
    value: "true"
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: "1"
      memory: 512Mi
  volumes:
  - name: receiver-tls
    secret:
      secretName: otel-receiver-tls
  volumeMounts:
  - name: receiver-tls
    mountPath: /etc/otel/tls
    readOnly: true
  config:
    receivers:
      otlp:
        protocols:
          http:
            endpoint: 0.0.0.0:4318
            tls:
              cert_file: /etc/otel/tls/tls.crt
              key_file: /etc/otel/tls/tls.key
    processors:
      memory_limiter:
        check_interval: 1s
        limit_percentage: 75
        spike_limit_percentage: 15
      batch: {}
    exporters:
      awsxray:
        region: us-west-2
        local_mode: true
        no_verify_ssl: false
        index_all_attributes: false
        telemetry:
          enabled: false
    extensions:
      health_check:
        endpoint: 0.0.0.0:13133
    service:
      extensions: [health_check]
      pipelines:
        traces:
          receivers: [otlp]
          processors: [memory_limiter, batch]
          exporters: [awsxray]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tracing-ingress
  namespace: tracing-demo
spec:
  podSelector: {}
  policyTypes: [Ingress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: default
      podSelector:
        matchLabels:
          app: my-app
    ports:
    - protocol: TCP
      port: 4318
```

Operator は OTLP/HTTP port から ClusterIP receiver Service を生成します。tracing-demo 内の adot-traces-collector で、TCP 4318 を使用します。receiver は、ユーザー ID や業務上の認可を示す claim を検証しません。この例では server TLS と選択したネットワーク境界を使用します。より強い分離が必要な場合は、mTLS またはサポート対象の receiver authenticator を必須にできます。アクセスを拡張する前に、両端で一貫して設定してください。

Collector が受け付けたことは、保存が確認されたことを意味しません。生成された Deployment／Service、TLS handshake、AWS credential の選択、exporter の失敗、X-Ray の既知の trace を確認してください。replica 1台のインメモリ例は、損失のないパイプラインでも高可用パイプラインでもありません。ワークロードに合わせて、バッファー、バックプレッシャー、再試行動作、障害処理の容量を決め、テストしてください。CRD schema の確認だけでは、すべてのコンポーネント設定を検証できず、collector の起動も証明できません。

#### アプリケーションを計装し、コンテキストを伝播する

Python 3.10 以降のアプリケーションでは、アプリケーションの依存関係 lock 内で opentelemetry-sdk==1.44.0 と opentelemetry-exporter-otlp-proto-http==1.44.0 のバージョンを合わせます。各サービスを個別に設定してください。共有コレクターが、受信するすべての service.name を1つのグローバル値で上書きしてはいけません。HTTP exporter endpoint には /v1/traces が含まれます。4317 の gRPC endpoint は別のプロトコル／設定です。

```bash
export OTEL_SERVICE_NAME=my-app
export CLUSTER_NAME=my-owned-cluster
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://adot-traces-collector.tracing-demo.svc:4318/v1/traces
export OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE=/etc/otel/ca.crt
```

CA ファイルはアプリケーションコンテナにマウントする必要があります。アプリケーション起動時に RequestTracing instance を1つ作成し、正規化した受信 header 名と、指定された送信 header を使う operation を使って実際の server handler から handle_request を呼び出します。正常終了時には close を呼び出してください。framework／client の自動計装で代用することもできます。同じ operation を二重に計装しないでください。

```python
import os
from urllib.parse import urlsplit

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.trace import SpanKind
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


class RequestTracing:
    def __init__(self):
        endpoint = os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"]
        parsed = urlsplit(endpoint)
        if parsed.scheme != "https" or parsed.path != "/v1/traces":
            raise ValueError("Set the HTTPS OTLP/HTTP traces endpoint including /v1/traces")
        self.provider = TracerProvider(
            resource=Resource.create({
                "service.name": os.environ["OTEL_SERVICE_NAME"],
                "k8s.cluster.name": os.environ["CLUSTER_NAME"],
            }),
            sampler=ParentBased(TraceIdRatioBased(0.1)),
        )
        exporter = OTLPSpanExporter(
            endpoint=endpoint,
            certificate_file=os.environ["OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE"],
            timeout=10,
        )
        self.provider.add_span_processor(BatchSpanProcessor(exporter))
        self.tracer = self.provider.get_tracer("example.request-handler")
        self.propagator = TraceContextTextMapPropagator()

    def handle_request(self, incoming_headers, operation):
        parent = self.propagator.extract(incoming_headers)
        with self.tracer.start_as_current_span("request", context=parent, kind=SpanKind.SERVER):
            outgoing_headers = {}
            self.propagator.inject(outgoing_headers)
            return operation(outgoing_headers)

    def close(self):
        self.provider.shutdown()
```

この adapter は W3C tracecontext の伝播と1つの server span を示すものであり、HTTP server やすべての client span を実装するものではありません。X-Amzn-Trace-Id を使用する AWS edge 統合では、W3C 専用の抽出がその header を読み取ると想定せず、サポート対象の propagator／bridge を使用してください。head sampling の10%は新しい root に対する例であり、親の判断を引き継ぎます。後から発生したすべてのエラーや遅いリクエストを保持できる保証はありません。tail sampling には、1つの trace のすべての span が同じ場所にルーティングされるようにし、十分なバッファーを備えた別個の設計が必要です。

#### Trace map と調査

アカウントで利用可能な X-Ray／CloudWatch tracing view で、trace map、latency 分布、error／fault の詳細を確認します。map に反映されるのは、計装され、サンプリングされ、正常に配信された span です。edge がないことは、サービス間通信がない証拠ではありません。trace ID を適切な保持期間で管理されたログやメトリクスと関連付ける一方、認証情報、個人情報、上限のないリクエスト属性は除外してください。

この監査で検証したのは、公開 API／schema と合成されたローカル動作のみです。collector のデプロイ、ライブ計装、trace export、本番容量テストを実施したとは主張しません。参照先: [X-Ray 保守タイムライン](https://aws.amazon.com/blogs/mt/aws-x-ray-sdks-daemon-migration-to-opentelemetry/)、[EKS ADOT の管理](https://docs.aws.amazon.com/eks/latest/userguide/opentelemetry.html)、[AWS X-Ray exporter](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.158.0/exporter/awsxrayexporter)。

### Kubernetes Dashboard

[Kubernetes Dashboard プロジェクト](https://github.com/kubernetes-retired/dashboard)はアーカイブされ、保守されていません。現在の UI のニーズには、Kubernetes SIG UI の Headlamp を使うよう、メンテナーが案内しています。古い Dashboard v2.7 の raw-manifest と cluster-admin token を使う手順は、現在のインストール方法として使用すべきではありません。

保守されている UI を選び、実際の認証、TLS、認可、アップグレード要件を確認してください。セキュリティの章にある access-entry／RBAC の例に従い、意図した IAM／RBAC ID と namespace の範囲を使用してください。UI のデフォルトユーザーに、無制限の cluster-admin ServiceAccount は必要ありません。管理者の bearer token を公開することは、アクセス設計の代わりにはなりません。

### カスタムメトリクスとモニタリング

アプリケーション固有のメトリクスを収集、監視するためのカスタムソリューションを実装できます。

#### Prometheus Client Library の統合

Prometheus Java client 1.8.0 API では、現行の io.prometheus.metrics package と、バージョンを揃えた依存関係を使用します。既存の Gradle Java project では、次のようにします。

```groovy
dependencies {
    implementation(platform("io.prometheus:prometheus-metrics-bom:1.8.0"))
    implementation("io.prometheus:prometheus-metrics-core")
    implementation("io.prometheus:prometheus-metrics-exporter-httpserver")
}
```

この例を App.java として保存します。main method は port 9400 でメトリクスを公開して待機します。アプリケーションの実際の request handler から processRequest を呼び出す必要があります。メトリクス endpoint を起動しただけでは、業務リクエストの件数は計上されません。合成したリクエスト数を実測トラフィックとして示してはいません。

```java
import io.prometheus.metrics.core.metrics.Counter;
import io.prometheus.metrics.core.metrics.Histogram;
import io.prometheus.metrics.exporter.httpserver.HTTPServer;
import java.io.IOException;

public class App {
    private static final Counter requests = Counter.builder()
        .name("app_requests_total").help("Requests processed by this application.")
        .register();
    private static final Histogram latency = Histogram.builder()
        .name("app_request_latency_seconds").help("Request processing time in seconds.")
        .register();

    public static void processRequest(Runnable operation) {
        requests.inc();
        long started = System.nanoTime();
        try {
            operation.run();
        } finally {
            latency.observe((System.nanoTime() - started) / 1_000_000_000.0);
        }
    }

    public static void main(String[] args) throws IOException, InterruptedException {
        HTTPServer server = HTTPServer.builder().port(9400).buildAndStart();
        Runtime.getRuntime().addShutdownHook(new Thread(server::close));
        Thread.currentThread().join();
    }
}
```

ソース API と依存関係の座標は公開済み client に照らして確認しました。この監査環境には Java compiler／runtime がなかったため、例をコンパイルまたは実行していません。デプロイ前に、アプリケーションのビルド、ライフサイクル、リクエスト経路に統合してください。label の値の種類は上限を設けてください。request ID、user ID、生の URL は、デフォルトのメトリクスディメンションとして適切ではありません。

#### カスタムメトリクスの収集

所有管理下のアプリケーション Pod が default にあり、app=my-app を持ち、TCP 9400 で /metrics を実際に提供していることを前提とします。Service は Pod を選択し、ServiceMonitor は Service の label と名前付き port を選択します。release=monitoring label と namespaceSelector によって、この ServiceMonitor は上記のスタックに接続されます。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-app-metrics
  namespace: default
  labels:
    app: my-app
spec:
  type: ClusterIP
  selector:
    app: my-app
  ports:
  - name: metrics
    port: 9400
    targetPort: 9400
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: app-monitor
  namespace: monitoring
  labels:
    release: monitoring
spec:
  namespaceSelector:
    matchNames:
    - default
  selector:
    matchLabels:
      app: my-app
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
```

Service の EndpointSlice と Prometheus target の状態を確認し、適用される network policy／セキュリティ統制で意図したコレクターだけを許可してください。このクラスター内 HTTP metrics の例では、確認済みのネットワーク境界が必要です。メトリクス endpoint で必要な場合は TLS／認証を設定します。ServiceMonitor はアプリケーションを計装したり、存在しない metrics server を作成したりしません。

参照先: [Java client quickstart](https://prometheus.github.io/client_java/getting-started/quickstart/)、[Prometheus configuration](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)。

#### カスタムダッシュボード

Grafana でカスタムダッシュボードを作成し、アプリケーションメトリクスを可視化します。

1. Grafana にログインします
2. 「+」アイコンをクリックし、「Dashboard」を選択します
3. 「Add panel」をクリックします
4. データソースとして「Prometheus」を選択します
5. PromQL クエリ（例: `rate(app_requests_total[5m])`）を記述します
6. パネルのタイトル、説明、可視化の種類を設定します
7. 「Save」をクリックします

## アラートとイベント管理

EKS クラスターの問題を迅速に検出し、対応するには、効果的なアラートとイベント管理が不可欠です。このセクションでは、EKS クラスターのアラートとイベントを管理するためのさまざまなツールと手法について説明します。

![CloudWatch のメトリクスとログ、AWS イベント、Prometheus のメトリクスと Loki のログ、Kubernetes／アプリケーションイベントを、CloudWatch Alarms、EventBridge、Prometheus Alertmanager、イベントルーター経由で SNS（Email と SQS のサブスクリプション）、Lambda、Slack、PagerDuty、OpsGenie にルーティングするアーキテクチャ図。](../.gitbook/assets/en-eks-06-eks-monitoring-logging-3.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-3.html)

### CloudWatch Alarms

アラームを作成する前に、最近の datapoint と、正確なメトリクス namespace、名前、ディメンションセットを確認してください。以下の例では、文書化された ClusterName のみの ContainerInsights ノード集計と Maximum を使用します。これによりノードのホットスポットを検出できますが、クラスター全体の容量加重使用率を測定するものではありません。影響を受けているノードを特定するには、ノード固有のディメンションを使用してください。

80／80／85 パーセントのしきい値と、5分間の評価期間を2回とする設定は、説明用のポリシー選択です。2つの期間で Maximum がしきい値を超えても、10分間の毎秒で飽和が続いたことを意味しません。データがない場合は欠測であり、使用率が健全である証拠ではありません。PutMetricAlarm は既存のアラームを更新するため、アラーム名を再利用する前に既存定義を確認してください。通知権限、サブスクリプション、配信テストは別個の前提条件です。

#### ノード CPU

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set the metric Region}"
: "${ALARM_PREFIX:?Set a reviewed alarm-name prefix owned by this workflow}"
: "${SNS_TOPIC_ARN:?Set the approved notification topic ARN}"
aws cloudwatch put-metric-alarm --region "$AWS_REGION" \
  --alarm-name "${ALARM_PREFIX}-node-cpu" \
  --alarm-description "Example: maximum reported node cpu utilization exceeds 80 percent" \
  --metric-name node_cpu_utilization --namespace ContainerInsights \
  --statistic Maximum --period 300 --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions "Name=ClusterName,Value=$CLUSTER_NAME" \
  --evaluation-periods 2 --datapoints-to-alarm 2 --treat-missing-data missing \
  --alarm-actions "$SNS_TOPIC_ARN"
```

#### ノードメモリ

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set the metric Region}"
: "${ALARM_PREFIX:?Set a reviewed alarm-name prefix owned by this workflow}"
: "${SNS_TOPIC_ARN:?Set the approved notification topic ARN}"
aws cloudwatch put-metric-alarm --region "$AWS_REGION" \
  --alarm-name "${ALARM_PREFIX}-node-memory" \
  --alarm-description "Example: maximum reported node memory utilization exceeds 80 percent" \
  --metric-name node_memory_utilization --namespace ContainerInsights \
  --statistic Maximum --period 300 --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions "Name=ClusterName,Value=$CLUSTER_NAME" \
  --evaluation-periods 2 --datapoints-to-alarm 2 --treat-missing-data missing \
  --alarm-actions "$SNS_TOPIC_ARN"
```

#### ノードファイルシステム

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set the metric Region}"
: "${ALARM_PREFIX:?Set a reviewed alarm-name prefix owned by this workflow}"
: "${SNS_TOPIC_ARN:?Set the approved notification topic ARN}"
aws cloudwatch put-metric-alarm --region "$AWS_REGION" \
  --alarm-name "${ALARM_PREFIX}-node-disk" \
  --alarm-description "Example: maximum reported node disk utilization exceeds 85 percent" \
  --metric-name node_filesystem_utilization --namespace ContainerInsights \
  --statistic Maximum --period 300 --threshold 85 \
  --comparison-operator GreaterThanThreshold \
  --dimensions "Name=ClusterName,Value=$CLUSTER_NAME" \
  --evaluation-periods 2 --datapoints-to-alarm 2 --treat-missing-data missing \
  --alarm-actions "$SNS_TOPIC_ARN"
```

これらのアラームコマンドは AWS に対して実行していません。参照先: [Container Insights のメトリクスとディメンション](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html)。

### Prometheus Alertmanager

Prometheus はアラートルールを評価し、Alertmanager は生成されたアラートをグループ化、重複排除、ルーティングします。任意の名前の ConfigMap が、Operator 管理下の Alertmanager に自動的に読み込まれるわけではありません。確認済みのスタックでは Alertmanager 0.34.0 を使用します。その設定と認証情報ファイルを明示的に接続してください。

#### Alertmanager の設定

Slack の例では、承認済みのシークレット管理プロセスで monitoring/notification-credentials を準備し、実際の webhook URL を含む slack-url key を用意します。認証情報を ConfigMap、リポジトリ内のテキスト、Helm コマンド引数に記載しないでください。以下の機密情報を含まないルーティング定義を alertmanager-config.yaml として保存します。

```yaml
global:
  resolve_timeout: 5m
route:
  group_by: [cluster, namespace, alertname]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: slack-notifications
  routes:
  - matchers:
    - alertname="Watchdog"
    receiver: discard
receivers:
- name: discard
- name: slack-notifications
  slack_configs:
  - api_url_file: /etc/alertmanager/secrets/notification-credentials/slack-url
    channel: "#eks-alerts"
    send_resolved: true
    title: '[{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}'
    text: '{{ range .Alerts }}{{ .Annotations.summary }} — {{ .Annotations.description }}{{ "\n" }}{{ end }}'
```

webhook は、意図した Slack の送信先に対して認可されている必要があります。channel field によって Slack app の権限が上書きされるわけではありません。この例では、常時発火する同梱の Watchdog alert が Slack に定期メッセージを送らないよう、破棄しています。実際の dead-man／heartbeat 監視には、別の receiver と外部の不在検出が必要です。Watchdog を破棄しても、アラート配信のテストにはなりません。

一致する amtool でファイルをローカル検証してから、新規の所有管理下インストールに限り、設定 Secret を作成してください。既存の Secret／release については、所有者が確認済みの更新手順が必要です。

```bash
amtool --no-version-check check-config alertmanager-config.yaml
kubectl create secret generic alertmanager-routing -n monitoring \
  --from-file=alertmanager.yaml=alertmanager-config.yaml
```

以下を alertmanager-values.yaml として保存し、monitoring release の確認済みのすべての値と組み合わせます。configSecret で Secret を指定します。Operator はその中の alertmanager.yaml key を参照します。secrets は notification-credentials を /etc/alertmanager/secrets/notification-credentials にマウントします。デプロイ前に、monitoring 内で release=monitoring によって選択されるその他の AlertmanagerConfig resource を確認してください。

```yaml
alertmanager:
  alertmanagerSpec:
    useExistingSecret: true
    configSecret: alertmanager-routing
    secrets:
    - notification-credentials
    alertmanagerConfigSelector:
      matchLabels:
        release: monitoring
    alertmanagerConfigNamespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: monitoring
```

生成された設定／reload 状態と通知の失敗を確認し、通知に依存する前に、承認済みテスト先へ label 付きテストアラートを送ってください。ローカルの解析と route テストでは、Secret の利用可能性、webhook 権限、SMTP 接続、実際の配信は証明できません。chart の例は replica 1台のため、別途可用性設計も必要です。

#### アラートルールの設定

rule release label は Prometheus selector と一致しています。同等の同梱ルールがないか確認し、アラートの重複を避けてください。CrashLoopBackOff は Kubernetes の waiting reason です。再起動率のしきい値だけでは、その状態を確認できません。これらの例では、指定された kube-state-metrics series が必要で、namespace／Pod UID／container または node ID を使用します。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: kubernetes-alerts
  namespace: monitoring
  labels:
    release: monitoring
spec:
  groups:
  - name: kubernetes-example
    rules:
    - alert: KubernetesPodCrashLooping
      expr: max by (cluster, namespace, pod, uid, container) (max_over_time(kube_pod_container_status_waiting_reason{job="kube-state-metrics",reason="CrashLoopBackOff"}[5m])) >= 1
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "CrashLoopBackOff observed for {{ $labels.namespace }}/{{ $labels.pod }}"
        description: "Inspect container {{ $labels.container }} logs and events; the rule tracks recent waiting reasons, not a restart-count guarantee."
    - alert: KubernetesNodeMemoryPressure
      expr: max by (cluster, node) (kube_node_status_condition{job="kube-state-metrics",condition="MemoryPressure",status="true"}) == 1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Node {{ $labels.node }} reports MemoryPressure"
        description: "Inspect node capacity and workloads; the observed condition has matched for five minutes."
    - alert: KubernetesNodeDiskPressure
      expr: max by (cluster, node) (kube_node_status_condition{job="kube-state-metrics",condition="DiskPressure",status="true"}) == 1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Node {{ $labels.node }} reports DiskPressure"
        description: "Inspect disk space and inodes; the observed condition has matched for five minutes."
```

CrashLoopBackOff ルールは、直近5分間の window で繰り返し観測された状態を調べるものであり、再起動回数ではありません。ノード pressure は kubelet で観測された condition であり、一般的な使用率とは異なります。series の欠落／陳腐化でアラートが抑制される場合があるため、スクレイプの健全性とメトリクスの利用可能性を別途監視してください。しきい値と継続時間は例であり、インシデント対応を保証するものではありません。

### EventBridge イベントルール

イベント名と payload field は、イベントを発行するサービスが公開しているものを使用してください。EKS の直接イベントカタログには、アドオンの作成／更新／削除の結果、アドオンの health degraded／restored イベント、Fargate の予定済み終了が含まれます。以前の例で使われていた汎用の EKS Cluster State Change または EKS Node Group State Change という名前は公開されていません。CloudTrail 経由で配信される EKS API の操作は、別の detail-type と payload を使用します。

#### 直接のアドオンヘルスイベントと CloudTrail API 操作

以下では、選択したアカウントとリージョンを対象とする2つの代替パターンを書き出します。対象はそのアカウント／リージョン内で一致する操作全体であり、単一クラスターではありません。さらにルールの範囲を絞る場合は、その特定イベントタイプのイベントを取得して field を確認し、文書化された field をテストしてください。すべてのイベントに detail.clusterName が含まれると想定しないでください。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the owned Region}"
: "${ACCOUNT_ID:?Set the owned 12-digit AWS account ID}"
python3 - "$AWS_REGION" "$ACCOUNT_ID" <<'PY'
import json
import re
import sys
region, account = sys.argv[1:]
if not re.fullmatch(r"[0-9]{12}", account):
    raise SystemExit("ACCOUNT_ID must contain 12 digits")
base = {"source": ["aws.eks"], "account": [account], "region": [region]}
patterns = {
    "eks-addon-health-pattern.json": dict(base, **{
        "detail-type": ["EKS Addon Health Degraded", "EKS Addon Health Restored"],
    }),
    "eks-update-api-pattern.json": dict(base, **{
        "detail-type": ["AWS API Call via CloudTrail"],
        "detail": {
            "eventSource": ["eks.amazonaws.com"],
            "eventName": ["UpdateClusterVersion", "UpdateNodegroupVersion"],
        },
    }),
}
for filename, pattern in patterns.items():
    with open(filename, "w") as stream:
        json.dump(pattern, stream, indent=2)
        stream.write("\n")
PY
```

CloudTrail のパターンは UpdateClusterVersion と UpdateNodegroupVersion API イベントに一致し、該当するアップグレード／ロールバック要求も含みます。API call event が記録するのは、試行または受理された要求であり、非同期更新の完了ではありません。error field を確認し、成功した要求を update ID および DescribeUpdate の状態と照合してください。該当する CloudTrail management event の配信が設定されていることを確認します。直接配信と CloudTrail 経由の配信はいずれもベストエフォートであるため、サービス状態の確認と障害監視も使用してください。

#### 所有管理下の SNS target を接続する

標準 SNS topic、その確認済み subscription、同じアカウント／リージョン内の EventBridge target 実行ロールを準備します。ロールは EventBridge を信頼し、該当する暗号化 KMS 権限とともに、意図した topic に対する sns:Publish を許可する必要があります。運用担当者には、対応するルール／target の権限と承認済みロールを渡す権限が必要です。現在の EventBridge は SNS target に実行ロールをサポートしています。resource-based policy は代替手段であり、target を追加すると自動的に設定されるものではありません。

生成済みのパターンファイルを1つ選び、新規の所有管理下ルール名を指定します。事前確認ではすでに存在する名前を拒否しますが、PutRule は upsert であるため、所有権と同時変更を調整してください。ルールは無効状態で作成され、PutTargets の一部失敗があれば処理を停止します。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the reviewed Region}"
: "${ACCOUNT_ID:?Set the reviewed account ID}"
: "${RULE_NAME:?Set a new owned rule name}"
: "${PATTERN_FILE:?Select one reviewed pattern JSON file}"
: "${SNS_TOPIC_ARN:?Set the prepared standard SNS topic ARN}"
: "${EVENTBRIDGE_ROLE_ARN:?Set the prepared EventBridge target execution role ARN}"
python3 - "$AWS_REGION" "$ACCOUNT_ID" "$RULE_NAME" "$PATTERN_FILE" \
  "$SNS_TOPIC_ARN" "$EVENTBRIDGE_ROLE_ARN" <<'PY'
import json
import re
import sys
region, account, name, path, topic, role = sys.argv[1:]
if not re.fullmatch(r"[0-9]{12}", account) or not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", name):
    raise SystemExit("Review the account ID and rule name")
with open(path) as stream:
    pattern = json.load(stream)
if pattern.get("account") != [account] or pattern.get("region") != [region] or pattern.get("source") != ["aws.eks"]:
    raise SystemExit("Pattern scope differs from the selected account/Region/service")
t, r = topic.split(":", 5), role.split(":", 5)
if (len(t) != 6 or len(r) != 6 or t[0] != "arn" or r[0] != "arn"
        or t[1] != r[1] or t[2:5] != ["sns", region, account]
        or r[2:5] != ["iam", "", account] or not r[5].startswith("role/")
        or not t[5] or t[5].endswith(".fifo")):
    raise SystemExit("Use the reviewed same-account standard topic and target role")
with open("eks-event-targets.json", "w") as stream:
    json.dump([{"Id": "ops-sns", "Arn": topic, "RoleArn": role}], stream)
PY
EXISTING=$(aws events list-rules --region "$AWS_REGION" --event-bus-name default \
  --name-prefix "$RULE_NAME" --query 'Rules[].Name' --output json)
python3 - "$RULE_NAME" "$EXISTING" <<'PY'
import json
import sys
if sys.argv[1] in json.loads(sys.argv[2]):
    raise SystemExit("Rule already exists; use its owner's reviewed update procedure")
PY
aws events put-rule --region "$AWS_REGION" --event-bus-name default \
  --name "$RULE_NAME" --state DISABLED --event-pattern "file://$PATTERN_FILE"
aws events put-targets --region "$AWS_REGION" --event-bus-name default \
  --rule "$RULE_NAME" --targets file://eks-event-targets.json \
  --output json > eks-event-targets-result.json
python3 - <<'PY'
import json
with open("eks-event-targets-result.json") as stream:
    result = json.load(stream)
if result["FailedEntryCount"] != 0:
    raise SystemExit("Target configuration failed; inspect FailedEntries before retrying")
print("Rule remains DISABLED; review the target and pattern before enabling")
PY
```

target の応答全体、ロール、subscription、配信再試行／dead-letter のポリシー、代表的なイベントを確認してください。pattern の一致は TestEventPattern で確認できますが、target の権限や配信はテストされません。確認後にのみ有効にします。

```bash
aws events enable-rule --region "$AWS_REGION" --event-bus-name default --name "$RULE_NAME"
```

有効化後は、一致／失敗した呼び出しを監視し、承認済みのエンドツーエンドイベントを確認します。ルール、target、API 応答の成功だけでは、アラート配信を保証できません。この監査では EventBridge／SNS リソース、イベント、通知は作成していません。

参照先: [EKS EventBridge イベントカタログ](https://docs.aws.amazon.com/eventbridge/latest/ref/events-ref-eks.html)、[target の権限](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html)。

### Kubernetes Event のモニタリング

Kubernetes Event は、スケジューリング、image pull、再起動、その他の object の動作を調査するのに役立ちます。これらは短期間のみ利用できるベストエフォートの観測情報であり、同じ事象が繰り返された場合に集約されることもあります。完全で永続的な監査証跡ではありません。まず、対象 namespace を確認します。

```bash
kubectl events -n default --types=Warning
kubectl events -n default --types=Warning --watch
```

#### コレクターのバージョンと管理

元の Opsgenie exporter は保守されていません。現在活動している fork は resmoio から mustafaakin/kubernetes-event-exporter に移りました。ここで確認した最新公開 release は2024年2月の v1.7 ですが、リポジトリにはそれ以降の開発が存在します。リポジトリが活動中であることや最新 tag が古いことだけでは、本番用 image が現在も修正されていることは証明できません。

以下の参照設定は、v1.7 の設定／watcher source に照らして確認されています。この設定／CLI の契約を維持し、UID 65532 で動作し、読み取り専用 root filesystem でマウント済み設定を読み取れる、ビルドプロセスで確認およびパッチ適用された所有管理下 image が必要です。レンダリング時に変更不可能な digest を設定します。公開の latest image や、根拠のない digest は示していません。この監査では image のビルド、脆弱性レビュー、実行時互換性テストを行っていません。

#### Namespace の範囲、RBAC、設定

この例では既存の monitoring namespace 内で動作しますが、core/v1 Event のみを default から監視します。omitLookup=true によって、involved object の label／annotation を補完するための別個の GET request を無効にします。そのため Role に付与する権限は default 内の event 読み取りだけであり、Secret やあらゆる API resource のワイルドカード読み取りは許可しません。replica が1つなので leader election を無効にし、lease 書き込み権限は付与しません。範囲を変更する場合は、namespace、Role、RoleBinding の整合性を保ってください。

以下を event-exporter-template.yaml として保存します。image marker が含まれているため、使用前にレンダリングが必要です。match rule は名前付き receiver を指定します。その receiver は JSON を stdout に出力し、既存の所有管理下コンテナログパイプラインで収集できます。この設定では Warning event のみをエクスポートします。

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: event-exporter
  namespace: monitoring
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: event-exporter-read
  namespace: default
rules:
- apiGroups: [""]
  resources: [events]
  verbs: [get, list, watch]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: event-exporter-read
  namespace: default
subjects:
- kind: ServiceAccount
  name: event-exporter
  namespace: monitoring
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: event-exporter-read
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: event-exporter-config
  namespace: monitoring
data:
  config.yaml: |
    logLevel: warn
    logFormat: json
    namespace: default
    omitLookup: true
    maxEventAgeSeconds: 60
    metricsNamePrefix: event_exporter_
    leaderElection:
      enabled: false
    route:
      routes:
      - match:
        - type: Warning
          receiver: event-log
    receivers:
    - name: event-log
      stdout:
        deDot: false
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: event-exporter
  namespace: monitoring
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: event-exporter
  template:
    metadata:
      labels:
        app: event-exporter
    spec:
      serviceAccountName: event-exporter
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: event-exporter
        image: REVIEWED_EVENT_EXPORTER_IMAGE
        args:
        - -conf=/etc/event-exporter/config.yaml
        - -metrics-address=127.0.0.1:2112
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 250m
            memory: 128Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop: [ALL]
        volumeMounts:
        - name: config
          mountPath: /etc/event-exporter
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: event-exporter-config
```

レンダリングには Python 3 と PyYAML が必要です。まず既存の event-exporter resource と所有者を確認してください。既存インストールについては、所有者のアップグレード手順を使用します。

```bash
set -euo pipefail
: "${EVENT_EXPORTER_IMAGE:?Set the reviewed, patched image reference including @sha256 digest}"
python3 - "$EVENT_EXPORTER_IMAGE" <<'PY'
import re
import sys
import yaml
image = sys.argv[1]
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[a-f0-9]{64}", image):
    raise SystemExit("Use a reviewed image pinned by SHA256 digest")
with open("event-exporter-template.yaml") as stream:
    objects = list(yaml.safe_load_all(stream))
deployment = next(obj for obj in objects if obj["kind"] == "Deployment")
container = deployment["spec"]["template"]["spec"]["containers"][0]
if container["image"] != "REVIEWED_EVENT_EXPORTER_IMAGE":
    raise SystemExit("Review the template before replacing its image")
container["image"] = image
with open("event-exporter-rendered.yaml", "w") as stream:
    yaml.safe_dump_all(objects, stream, sort_keys=False)
PY
```

新規の所有管理下インストールでは、レンダリング済み manifest、image pull ID、API 接続を確認してから適用します。Recreate は rollout 中に replica が重複するのを防ぎますが、停止時間が生じます。高可用なコレクターではありません。

```bash
kubectl apply -f event-exporter-rendered.yaml
kubectl rollout status deployment/event-exporter -n monitoring --timeout=120s
kubectl logs -n monitoring deployment/event-exporter --tail=100
```

#### 損失、繰り返し発生するイベント、アラート payload

確認した v1.7 watcher は add 通知を処理し、update／delete callback は無視します。そのため、繰り返し発生する Event count／series の更新は、エクスポートされた発生回数の信頼できるカウンターにはなりません。maxEventAgeSeconds=60 は例示的な取り込み判定のしきい値であり、バックエンドの保持期間ではありません。起動時、スロットリング中、停止中に、それより古い event が破棄されることがあります。再リスト／再起動でも観測が重複する場合があります。イベント件数を運用上の判断に使う前に、必要な update 処理、バッファリング、耐久性のある送信先を選択してテストしてください。

watch／discard カウンターとログの両方を確認します。この例では exporter の metrics listener を loopback にバインドしています。認可された運用担当者は、ローカル port-forward で確認できます。Prometheus に endpoint が自動追加されるわけではありません。

```bash
kubectl port-forward --address 127.0.0.1 -n monitoring \
  deployment/event-exporter 2112:2112
```

forwarding 中に `http://127.0.0.1:2112/metrics` から /metrics を取得します。rollout や stdout の record だけでは CloudWatch／OpenSearch に保存されたことの確認にはなりません。既存のログコレクターと意図した送信先を確認してください。Event message には機微な運用情報が含まれることがあるため、アクセス、フィルタリング、保持期間を確認します。

webhook URL だけを変更して、生の Kubernetes Event object を Alertmanager に送信しないでください。Alertmanager の現行 /api/v2/alerts endpoint は alert-array schema を期待します。旧 /api/v1/alerts path は現行 API ではありません。意図的に構成した adapter で、ID、label、annotation、解除の意味を変換する必要があります。上記の stdout／ログ経路は、そのような adapter を実装しているかのように装っていません。

参照先: [保守されている exporter repository](https://github.com/mustafaakin/kubernetes-event-exporter)、[v1.7 watcher](https://github.com/mustafaakin/kubernetes-event-exporter/blob/v1.7/pkg/kube/watcher.go)、[Alertmanager v2 API](https://github.com/prometheus/alertmanager/blob/v0.34.0/api/v2/openapi.yaml)。

### 通知チャネルの統合

実際の Alertmanager バージョンがサポートする receiver を使用してください。以下の断片は alertmanager-config.yaml の receivers 配下の項目であり、Kubernetes resource ではありません。1つ選ぶには、その receiver を追加し、route.receiver または一致する child route を正確な名前に変更してから、設定全体を検証し、選択した Secret を更新します。未使用の receiver 項目だけでは、アラートはルーティングされません。

#### Slack との統合

上記の接続済み Slack の例では、マウントされた webhook file を使用します。許可されている channel を確認し、機微情報の確認なしにアラートの全 label／annotation を公開しないでください。実際の Slack token や webhook を repository に commit する Provider／ConfigMap の例に記載しないでください。

#### PagerDuty との統合

Events API v2 の統合では、notification-credentials に pagerduty-routing-key key を準備します。routing_key_file が指すのはその統合 key であり、汎用の PagerDuty REST API token ではありません。critical alert のみを通知する場合は、確認済みの child route を通じて critical alert を接続してください。

```yaml
name: pagerduty-notifications
pagerduty_configs:
- routing_key_file: /etc/alertmanager/secrets/notification-credentials/pagerduty-routing-key
  send_resolved: true
  severity: '{{ if eq .CommonLabels.severity "critical" }}critical{{ else }}warning{{ end }}'
  description: '{{ .CommonLabels.alertname }}'
```

#### Email との統合

予約済みの SMTP host／address／user の例を、承認済みメールサービスの設定に置き換え、同じ認証情報 Secret に smtp-password を準備します。TLS を必須にし、server の信頼性、送信者の認可、配信を確認してください。これは Alertmanager の email receiver であり、Flux Provider ではありません。

```yaml
name: email-notifications
email_configs:
- to: oncall@example.com
  from: alerts@example.com
  smarthost: smtp.example.com:587
  auth_username: alerting-user
  auth_password_file: /etc/alertmanager/secrets/notification-credentials/smtp-password
  require_tls: true
  send_resolved: true
```

#### Amazon SNS ネイティブ統合

Alertmanager 0.34.0 にはネイティブの SNS receiver があるため、この経路では未定義の sns-forwarder webhook service は不要です。例のリージョン／アカウント／topic を、所有管理下の標準 topic に置き換えます。実際の Alertmanager ServiceAccount に、その topic に対する sns:Publish を許可するサポート対象 AWS ID を付与します。暗号化された topic では該当する KMS 権限とネットワーク接続も必要です。Prometheus またはアプリケーションの role が Alertmanager の role になるわけではありません。静的な AWS access key は埋め込んでいません。

```yaml
name: sns-notifications
sns_configs:
- sigv4:
    region: us-west-2
  topic_arn: arn:aws:sns:us-west-2:123456789012:eks-alerts
  send_resolved: true
  subject: 'EKS {{ .CommonLabels.alertname }}'
```

topic の subscription と送信先ポリシーを確認し、配信を別途テストしてください。FIFO topic には重複排除／グループ化に関する追加考慮事項があります。この断片が対象とするのは標準 topic です。receiver の解析では IAM や SNS 発行をテストしていません。

Flux notification Provider は、Flux Alert resource および選択されたイベントソースと組み合わせて Flux reconciliation event をルーティングします。Provider が存在するだけでは、任意の Prometheus alert や Kubernetes Event を受信しません。そのワークフローは、ここで示した Alertmanager receiver 設定とは分けてください。

参照先: [Alertmanager の設定と receiver](https://prometheus.io/docs/alerting/latest/configuration/)。

### アラートの管理とエスカレーション

アラートを効果的に管理し、エスカレーションするための方針を実装します。

#### アラートの重大度レベル

アラートを次の重大度レベルに分類します。

- **Critical**: 直ちに対応する必要がある重大な問題
- **Warning**: 注意は必要だが、直ちに対応する必要はない問題
- **Info**: 情報提供を目的としたアラート

#### アラートのエスカレーションポリシー

PagerDuty などのツールを使って、アラートのエスカレーションポリシーを実装します。

1. **最初の対応**: オンコールエンジニアにアラートを通知します
2. **エスカレーション1**: 15分経っても応答がない場合、バックアップエンジニアに通知します
3. **エスカレーション2**: 30分経っても応答がない場合、チームリードに通知します
4. **エスカレーション3**: 45分経っても応答がない場合、マネージャーに通知します

#### アラート疲れの軽減

アラート疲れを軽減するための方針を実装します。

1. **アラートのグループ化**: 関連するアラートをまとめ、重複通知を減らします
2. **アラートのフィルタリング**: 重要なアラートのみを配信するようにフィルタリングします
3. **アラートのスロットリング**: 繰り返し発生するアラートの頻度を制限します
4. **アラートの時間帯**: 業務上重要でないアラートは営業時間内のみ配信します

## ログ分析と可視化

ログ分析と可視化は、EKS クラスターで発生する問題の診断と解決に重要な役割を果たします。このセクションでは、EKS クラスターのログを分析、可視化するさまざまなツールと手法について説明します。

![ログ分析／可視化パイプラインの図。コントロールプレーンおよび AWS service のログは CloudWatch Logs に直接送られ、コンテナ／アプリケーションログはログコレクター（Fluent Bit、Fluentd、Vector、CloudWatch Agent）を通じて4つのストア（CloudWatch Logs、Amazon OpenSearch、Amazon S3、Grafana Loki）に送られる。各ストアは対応する分析／可視化ツール（CloudWatch Logs Insights、OpenSearch Dashboards、Athena と QuickSight、Grafana Explore と dashboard）にデータを渡す。](../.gitbook/assets/en-eks-06-eks-monitoring-logging-4.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-4.html)

### CloudWatch Logs Insights

クエリを実行する前に、実際のロググループと範囲を限定した時間帯を選択します。コンテナ、API／監査、authenticator の各ストリームでは schema が異なります。上記の単独 Fluent Bit の値を使用する場合、解析されたアプリケーション JSON は data の下、Kubernetes メタデータは kubernetes の下にあり、元の log field も保持されます。ほかのコレクター／設定では field path が異なる場合があります。まず保存済みの event を確認してください。

#### コンテナログのクエリ

level field が文字列である構造化アプリケーション record の場合:

```
fields @timestamp, @log, kubernetes.pod_name, data.level, data.message, log
| filter kubernetes.namespace_name = "default"
| filter kubernetes.container_name = "app"
| filter toupper(data.level) = "ERROR"
| sort @timestamp desc
| limit 20
```

プレーンテキストまたは JSON の解析に失敗した record には data.level がありません。結果が空だから「エラーなし」と判断するのではなく、log field を別に確認してください。

#### 監査ログ内の API エラー応答

監査ログが有効で、record に responseStatus が含まれる場合は、API server のすべてのテキストから Error という語を検索するのではなく、数値の応答コードを使用します。

```
fields @timestamp, verb, objectRef.resource, responseStatus.code, user.username
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code >= 400
| sort @timestamp desc
| limit 20
```

このクエリは選択した監査ストリーム／期間内に記録された応答を検索するもので、試行されたすべての API request を検索するわけではありません。4xx 応答は呼び出し元や認可の問題であることがあり、コントロールプレーンの停止を自動的に意味するものではありません。監査ポリシー、stage、取り込み、保持期間は網羅性に影響します。

#### Authenticator イベントの確認

失敗フィルターを追加する前に、現在の authenticator message 形式を確認します。

```
fields @timestamp, @message
| filter @logStream like /authenticator/
| sort @timestamp desc
| limit 50
```

固定の「authentication failed」という部分文字列では、実際の失敗を見落としたり、無関係なテキストに一致したりする場合があります。観測された message／status field を比較し、監査ログの 401／403 応答と関連付けてください。認証と Kubernetes 認可は別個の確認事項です。一方のストリームだけでは両方を完全に証明できません。

#### レベル別のログ件数

同じ構造化アプリケーション schema の場合:

```
fields toupper(data.level) as level, kubernetes.namespace_name
| filter ispresent(data.level)
| stats count(*) as log_records by @log, level, kubernetes.namespace_name
| sort log_records desc
```

これらはログ record の件数であり、一意なリクエスト数やエラー率ではありません。再試行、メッセージの繰り返し、コレクターの重複によって件数は変わることがあります。想定した空白区切り形式を解析しても、任意の JSON／コンテナ／コントロールプレーンログを確実に分類することはできません。

参照先: [JSON field の検出](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_AnalyzeLogData-discoverable-fields.html)、[クエリ関数](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax-operations-functions.html)。

### Amazon OpenSearch Service

Amazon OpenSearch Service（旧 Amazon Elasticsearch Service）を使用して、EKS クラスターのログを保存、分析、可視化します。

#### 所有管理下の OpenSearch domain を準備する

プラットフォーム所有者が確認済みのプロビジョニング手順で準備した domain を使用します。ワークロードに合わせて、サポート対象の engine／version、容量、保持ポリシーを選びます。このログ記録の例では、承認済みのネットワーク経路、HTTPS、保存時暗号化、ノード間暗号化、きめ細かなアクセス制御（FGAC）を備える VPC domain を使用します。コレクターを設定する前に、実際の domain を確認してください。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the owned domain Region}"
: "${OPENSEARCH_DOMAIN:?Set the owned domain name}"
aws opensearch describe-domain --region "$AWS_REGION" \
  --domain-name "$OPENSEARCH_DOMAIN" \
  --query 'DomainStatus.{ARN:ARN,Engine:EngineVersion,Endpoint:Endpoint,EndpointV2:EndpointV2,Endpoints:Endpoints,VPC:VPCOptions,HTTPS:DomainEndpointOptions.EnforceHTTPS,AtRest:EncryptionAtRestOptions.Enabled,NodeToNode:NodeToNodeEncryptionOptions.Enabled,FGAC:AdvancedSecurityOptions.Enabled}'
```

ネットワーク到達性、domain アクセスポリシー、FGAC は別々の層です。SigV4 コレクター ID は、domain／IAM ポリシーによって許可され、限定された OpenSearch 取り込みロールにマッピングされる必要があります。管理者権限は取り込み権限と分けてください。内部ユーザーデータベースの設定でも IAM ID をマッピングできます。同じリクエストで HTTP basic credential と SigV4 credential を併用しないでください。

承認済みの ID／シークレット管理経路を通じて認証情報を提供します。公開された管理者パスワードの共有や、ワイルドカードの公開アクセス ポリシーは、適切なログ設定ではありません。既存の公開 domain を VPC 内に移すには、新しい domain とデータ移行が必要です。endpoint を切り替えるだけでは対応できません。既存の Terraform resource type／address を変更する場合も、所有権／state の移行計画が必要です。

コレクター設定では返された endpoint のホスト名を使用し、CA／ホスト名の検証と認可済みの取り込みを確認します。domain の確認だけでは、取り込みや本番運用への準備ができたことをテストしたことにはなりません。

参照先: [OpenSearch FGAC](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/fgac.html)、[VPC domain と移行](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/vpc.html)。

#### Fluent Bit を使って OpenSearch にログを送信する

「コンテナのログ記録」のセクションにある、接続済み Fluent Bit の値、RBAC post-renderer、OpenSearch overlay を使用します。実際の所有管理下 endpoint、SigV4 権限、FGAC 取り込みマッピングを指定してください。無関係な fluent-bit-config ConfigMap を適用しても、別名の ConfigMap をマウントしている Helm release は変更されません。

#### OpenSearch Dashboards によるログの可視化

OpenSearch Dashboards で次の可視化を作成します。

1. **Log Explorer**: ログの検索とフィルタリング
2. **Dashboards**: ログデータに基づくダッシュボードの作成
3. **Visualizations**: ログデータに基づくチャートとグラフの作成
4. **Alerts**: ログパターンに基づくアラートの設定

### Grafana Loki

Grafana Loki は、Prometheus と同様の label ベースの方式を採用するログ集約システムです。

#### Loki のインストール

所有管理下の deployment と Alloy などのサポート対象クライアントには、[現行の Loki 設定ガイド](../observability/logging/01-loki.md)を使用してください。非推奨の loki-stack／Promtail の組み合わせは、現行のインストール方法ではありません。本番ログを送信する前に、ストレージ、認証、label／保持期間ポリシーを設定します。

#### LogQL クエリ例

以下のクエリは、コレクターが namespace と pod の stream label を作成し、最上位の level field を持つアプリケーション JSON を保存することを前提としています。label や JSON の抽出方法は、CloudWatch／Fluent Bit の data wrapper と自動的に同じになるわけではありません。

```logql
{namespace="default"} |= "ERROR"

{namespace="default", pod=~"app-.*"} | json | __error__=""

sum by (level) (
  count_over_time(
    {namespace="default"} | json | __error__="" | level=~"INFO|WARN|ERROR" [5m]
  )
)
```

JSON parser の error filter は、解析後に指定します。メトリクスクエリではパイプラインエラーを除外してください。フィルタリングで収集上の問題が隠れないよう、拒否／不正形式の record は別途調査します。例の level は大文字の構造化ログ例に合わせたものです。実際のデータに合わせて field／大文字小文字を調整してください。stream label の種類は上限を設けます。request ID や user ID は、デフォルトの高カーディナリティ stream label ではなく、制御されたログ field に含めてください。

#### Grafana dashboard の作成

Loki data source を使って Grafana にログ dashboard を作成します。

1. Grafana にログインします
2. 「+」アイコンをクリックし、「Dashboard」を選択します
3. 「Add panel」をクリックします
4. データソースとして「Loki」を選択します
5. LogQL クエリを記述します
6. パネルのタイトル、説明、可視化の種類を設定します
7. 「Save」をクリックします

### AWS CloudTrail

CloudTrail は、EKS クラスター／アドオン／ノードグループの管理など、サポート対象の AWS API 操作を記録します。Kubernetes API の監査ログやアプリケーションのリクエストログを置き換えるものではありません。未準備の bucket に重複した trail を作成するのではなく、まず既存の組織／アカウント trail を確認してください。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the Region to inspect}"
aws cloudtrail describe-trails --region "$AWS_REGION" --include-shadow-trails \
  --query 'trailList[].{Name:Name,ARN:TrailARN,HomeRegion:HomeRegion,Organization:IsOrganizationTrail,MultiRegion:IsMultiRegionTrail}'
```

所有管理下の trail とそのホームリージョンを選択した後、次のようにします。

```bash
set -euo pipefail
: "${TRAIL_ARN:?Choose the existing owned trail ARN}"
: "${TRAIL_HOME_REGION:?Use the home Region of the selected trail}"
aws cloudtrail get-trail-status --region "$TRAIL_HOME_REGION" --name "$TRAIL_ARN"
aws cloudtrail get-event-selectors --region "$TRAIL_HOME_REGION" --trail-name "$TRAIL_ARN"
```

ログ記録／配信エラーと event selector を確認してください。新しい trail には、独自に確認した bucket／配信ポリシー、暗号化／key の権限、保持期間、所有権設定が必要です。trail resource があるだけでは、ログがストレージに届くとは限りません。trail の作成とログ記録の開始は別個の操作です。

#### 最近の管理イベント

CloudTrail Event history は trail を作成しなくても利用でき、選択したリージョンの過去90日間の管理イベントを対象とします。この読み取り専用の例では、過去1時間を要求し、表示する batch は最大50項目に制限しています。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the Region to query}"
python3 - <<'PY'
import datetime
import json
end = datetime.datetime.now(datetime.timezone.utc)
request = {
    "LookupAttributes": [{"AttributeKey": "EventSource", "AttributeValue": "eks.amazonaws.com"}],
    "StartTime": (end - datetime.timedelta(hours=1)).isoformat(),
    "EndTime": end.isoformat(),
}
with open("cloudtrail-lookup.json", "w") as stream:
    json.dump(request, stream, indent=2)
PY
aws cloudtrail lookup-events --region "$AWS_REGION" \
  --cli-input-json file://cloudtrail-lookup.json --max-items 50 --output json
```

CLI から NextToken が返された場合は、同じリクエスト／期間を指定し、--starting-token を使って残りを確認します。すべての ID／リクエスト／エラー field を取得するには、CloudTrailEvent の JSON 文字列を解析してください。Username だけでは、完全な呼び出し元の特定にはなりません。Event history は長期保持の計画ではなく、あらゆる data event category を含むわけでもありません。

#### 対象となる既存顧客向け CloudTrail Lake

CloudTrail Lake は2026年5月31日に新規顧客の受付を終了し、現在は重大なバグ／セキュリティ更新のみを受けています。既存顧客は文書化された条件の範囲で引き続き利用できます。組織の event data store は新しい member account を対象にできますが、既存の account-level store が、新たに追加されたアカウントにも Lake の取り込みを自動的に拡張するわけではありません。CloudTrail Trails、Insights、Aggregated Events は引き続きサポートされています。新しい分析設計では、新たに Lake にサインアップすることを前提とせず、AWS の最新の CloudWatch 移行／取り込みガイダンスを確認してください。

利用資格のある既存 store では、EVENT_DATA_STORE_ID を Lake query editor で選択した実際の ID に置き換えてください。eks_events のような任意のテーブル別名ではありません。以下は元の例示期間である2025年7月1日～11日を維持しています。この監査中に実行したクエリではなく、store がその期間を実際に保持している必要があります。

```sql
SELECT eventTime, eventName, userIdentity.arn, requestParameters
FROM EVENT_DATA_STORE_ID
WHERE eventSource = 'eks.amazonaws.com'
  AND eventTime >= '2025-07-01 00:00:00'
  AND eventTime < '2025-07-12 00:00:00'
ORDER BY eventTime DESC
```

排他的な上限によって、タイムスタンプが秒単位の精度だけだと想定せず、最終日の全体を含めています。このクエリは利用可能な EKS AWS 管理操作を返します。個々の ID field は呼び出し元の種類によって異なる場合があります。クエリ実行にはサービス利用料が発生することがあります。

参照先: [CloudTrail Event history](https://aws.amazon.com/cloudtrail/features/)、[Lake 利用可能性の変更](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-lake-service-availability-change.html)、[event data store の選択](https://docs.aws.amazon.com/help-panel/awscloudtrail/latest/console/query-editor-eds.html)。

### ログ分析のベストプラクティス

EKS クラスターのログを効果的に分析するためのベストプラクティス:

#### 構造化ログ

アプリケーションでは、JSON などの構造化ログ形式を使用します。

```json
{
  "timestamp": "2025-07-11T13:00:00Z",
  "level": "INFO",
  "message": "Request processed successfully",
  "request_id": "12345",
  "user_id": "user-789",
  "duration_ms": 45,
  "status_code": 200
}
```

#### 相関 ID

上記の2025年の JSON 例は、所要時間や架空の ID を含めて例示したものです。新たな測定値ではありません。仮名化しても、ユーザー／セッション ID は機微情報のままの場合があります。必要な field のみを、適切なアクセス制御と保持期間で含めてください。

SLF4J と MDC 対応の logging backend を使う Java アプリケーションでは、種類が限定された ID を使用し、ネストされた呼び出しに備えて以前の context を復元します。この framework 非依存の helper では、未定義の Request 型をなくし、UUID import を含めています。

```java
import java.util.UUID;
import java.util.regex.Pattern;
import org.slf4j.MDC;

public final class CorrelationContext {
    private static final Pattern SAFE_ID = Pattern.compile("[A-Za-z0-9._-]{1,128}");

    public static void run(String suppliedId, Runnable operation) {
        String correlationId = suppliedId != null && SAFE_ID.matcher(suppliedId).matches()
            ? suppliedId : UUID.randomUUID().toString();
        String previous = MDC.get("correlation_id");
        MDC.put("correlation_id", correlationId);
        try {
            operation.run();
        } finally {
            if (previous == null) {
                MDC.remove("correlation_id");
            } else {
                MDC.put("correlation_id", previous);
            }
        }
    }
}
```

抽出した request header と実際の operation を使って CorrelationContext.run を呼び出します。encoder／pattern に correlation_id を含めるよう設定してください。MDC に値を入れただけでは、ログ形式は自動的に変わりません。呼び出し元が指定した correlation ID は trace metadata であり、認証情報ではありません。MDC context は thread に紐づきます。executor／reactive の境界を越えて伝播させるには、backend／framework がサポートする方法で伝播と復元を行ってください。この helper のソースは確認済みですが、この監査環境には Java compiler／runtime がありませんでした。

参照先: [SLF4J MDC API](https://www.slf4j.org/apidocs/org/slf4j/MDC.html)、[Logback MDC と thread pool](https://logback.qos.ch/manual/mdc.html)。

#### ログレベルの使用

ログの重要度を示すため、適切なログレベルを使用します。

- **ERROR**: アプリケーションエラーと例外
- **WARN**: 潜在的な問題や予期しない状況
- **INFO**: 一般的なアプリケーションイベント
- **DEBUG**: デバッグに役立つ詳細情報
- **TRACE**: 非常に詳細なデバッグ情報

#### ログ保持ポリシー

承認済みの運用、データアクセス、保全要件に基づいて保持期間を選択します。保持期間を短縮すると、すでに保存されたデータが期限切れになることがあります。期間を設定しただけでは、コンプライアンス要件を満たしたことにも、改変不可の保全にもなりません。所有管理下の CloudWatch ロググループでは、以下は単なるログ確認ではなく、保持期間を変更します。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the log group Region}"
: "${LOG_GROUP:?Set the reviewed owned log group}"
: "${RETENTION_DAYS:?Choose a supported approved retention value such as 30}"
aws logs put-retention-policy --region "$AWS_REGION" \
  --log-group-name "$LOG_GROUP" --retention-in-days "$RETENTION_DAYS"
```

S3 general purpose bucket では、PutBucketLifecycleConfiguration によって lifecycle 設定全体が置き換えられます。無関係な既存ルール、versioning／Object Lock 要件、移行の最小サイズ設定を確認し、保持してください。誤った bucket を対象にする間違いを減らすため、期待するアカウント所有者を指定します。

```bash
set -euo pipefail
: "${LOG_BUCKET:?Set the owned general purpose S3 bucket}"
: "${ACCOUNT_ID:?Set its expected AWS account ID}"
aws s3api get-bucket-versioning --bucket "$LOG_BUCKET" --expected-bucket-owner "$ACCOUNT_ID"
aws s3api get-bucket-lifecycle-configuration --bucket "$LOG_BUCKET" \
  --expected-bucket-owner "$ACCOUNT_ID" --output json > current-lifecycle.json
```

サービスから NoSuchLifecycleConfiguration が明示的に返された場合は、設定がないことを確認し、新しいポリシーを作成する場合に限り `{"Rules":[]}` を current-lifecycle.json に初期化します。AccessDenied やその他の取得失敗を、ポリシーが空であると扱わないでください。以下の例を追加する前に、既存ルールを確認してください。

90日間の現行オブジェクトに適用する例示ポリシーを log-lifecycle-example.json として保存します。対象のログを30日後に Standard-IA に移行し、90日後に期限切れにします。以前の「60日目に Glacier、90日目に期限切れ」という組み合わせでは、Glacier Flexible Retrieval の最低保存期間90日に対し、Glacier に保存されるのは名目上30日だけです。その移行は、この90日間の例から除外しています。

```json
{
  "Rules": [
    {
      "ID": "example-logs-expiry-90d",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "logs/"
      },
      "Expiration": {
        "Days": 90
      }
    },
    {
      "ID": "example-logs-standard-ia-30d",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "logs/"
      },
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        }
      ]
    }
  ]
}
```

これらは既存オブジェクトにも適用されるオブジェクト年齢ルールであり、アクションは非同期です。実際の移行タイミング、最低期間より前の手動削除、上書きによって、最低期間分の料金が発生する場合があります。Standard-IA の最低請求期間は30日、Glacier Flexible Retrieval は90日、Deep Archive は180日です。さらに長いアーカイブスケジュールを選ぶ場合は、これらの制約と実際のアクセス／取得コストを考慮してください。この日数はサービスのルールであり、測定済みのコスト削減額ではありません。

確認済みの追加を行うには、以下を merge-log-lifecycle.py として保存して実行します。既存の Rules を保持し、例の ID と衝突する場合は拒否します。重複する filter の解決や、統合した保持ポリシーの承認は行いません。

```python
import json

with open("current-lifecycle.json") as stream:
    current = json.load(stream)
with open("log-lifecycle-example.json") as stream:
    example = json.load(stream)
if not isinstance(current.get("Rules"), list) or not isinstance(example.get("Rules"), list):
    raise SystemExit("Both files must contain an explicitly reviewed Rules array")
existing_ids = {rule.get("ID") for rule in current["Rules"] if rule.get("ID")}
new_ids = [rule.get("ID") for rule in example["Rules"]]
if any(not name for name in new_ids) or len(new_ids) != len(set(new_ids)):
    raise SystemExit("Example rules need distinct nonempty IDs")
if existing_ids.intersection(new_ids):
    raise SystemExit("A rule ID already exists; review its owner and changes instead of replacing it")
merged = {"Rules": current["Rules"] + example["Rules"]}
if len(merged["Rules"]) > 1000:
    raise SystemExit("The merged configuration exceeds the lifecycle rule limit")
with open("reviewed-full-lifecycle.json", "w") as stream:
    json.dump(merged, stream, indent=2)
    stream.write("\n")
print("Wrote a candidate preserving existing Rules; review overlaps, retention impact and minimum-size setting")
```

```bash
python3 merge-log-lifecycle.py
```

候補となる設定全体を確認し、最新の bucket 設定と比較してください。この API には置き換えの意味があるため、ほかの書き込み担当者と調整してください。2024年9月以降、新規作成／変更された設定では、128 KB 未満のオブジェクトを移行しない設定がデフォルトです。変更されていない古い設定では、従来の動作が残る場合があります。size filter でデフォルトを上書きできます。この設定は保持されている無関係なルールにも影響する場合があります。確認済みの all_storage_classes_128K または varies_by_storage_class を明示的に選択してください。GET の応答に TransitionDefaultMinimumObjectSize が含まれていれば、その値を確認できます。

設定全体と既存データへの影響を確認した後にのみ、完全なファイルを送信します。

```bash
set -euo pipefail
: "${LOG_BUCKET:?Set the reviewed owned bucket}"
: "${ACCOUNT_ID:?Set its expected AWS account ID}"
: "${TRANSITION_MINIMUM_OBJECT_SIZE:?Choose the reviewed minimum-size behavior}"
aws s3api put-bucket-lifecycle-configuration --bucket "$LOG_BUCKET" \
  --expected-bucket-owner "$ACCOUNT_ID" \
  --transition-default-minimum-object-size "$TRANSITION_MINIMUM_OBJECT_SIZE" \
  --lifecycle-configuration file://reviewed-full-lifecycle.json
```

versioning が有効な bucket では、current version の期限切れによって通常は delete marker が作成され、noncurrent version は残ります。noncurrent version の期限切れ、delete marker のクリーンアップ、Object Lock／replication の制限には、別途確認が必要です。この例は、すべての version を消去したり bucket を空にしたりするものではありません。移行されない小さなオブジェクトも、期限切れルールには一致する場合があります。

この監査では保持ポリシーもオブジェクト lifecycle action も適用していません。参照先: [lifecycle replacement API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketLifecycleConfiguration.html)、[移行の制約](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html)、[期限切れ／versioning／最低期間](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-expire-general-considerations.html)。

## モニタリングとログ記録のベストプラクティス

EKS クラスターでモニタリングとログ記録を効果的に実装するためのベストプラクティスを見ていきましょう。

### モニタリングのベストプラクティス

#### 多層モニタリング

EKS クラスターのすべての層を監視します。

1. **インフラストラクチャ層**: EC2 instance、VPC、subnet、security group
2. **クラスター層**: コントロールプレーン、ノード、Pod、Service
3. **アプリケーション層**: アプリケーションのパフォーマンス、ユーザー体験

#### ゴールデンシグナルのモニタリング

Google の SRE book が推奨する「4つのゴールデンシグナル」に注目します。

1. **Latency**: リクエスト処理にかかる時間
2. **Traffic**: システムへのリクエスト数
3. **Errors**: 失敗したリクエストの割合
4. **Saturation**: システムがどの程度「いっぱい」か（例: メモリ使用量）

#### プロアクティブなモニタリング

傾向と異常を使って、顕在化しつつあるリスクを特定します。予測は推定であり、インシデントの発生を予測できる保証はありません。

1. **傾向分析**: リソース使用量の経時的な傾向を分析します
2. **異常検知**: 異常なパターンを検知します
3. **予測分析**: 将来必要となるリソースを予測します

#### 自動スケーリング

この説明用の HPA は、所有管理下の default/my-app Deployment、稼働中の resource metrics API、適切な CPU／メモリ request を前提としています。使用率の目標値は request に対するパーセンテージであり、ノード容量やコンテナ limit に対するものではありません。複数のメトリクスがある場合、HPA は最も大きい replica 推奨数を選択します。メトリクスの取得に失敗すると、scale down が妨げられることがあります。HPA の condition を確認し、ワークロードが水平スケーリングの効果を実際に得られるかテストしてください。

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

#### ビジネスメトリクスのモニタリング

技術メトリクスに加え、ビジネスメトリクスも監視します。

1. **ユーザーアクティビティ**: アクティブユーザー数、セッション時間
2. **トランザクション**: トランザクション数、トランザクション額
3. **コンバージョン率**: ユーザーのコンバージョン率、解約率
4. **SLI／SLO の達成状況**: indicator と定義された objective を測定します。SLA は契約であり、結果を伴う場合があります。内部 SLO を満たしただけでは、契約上の遵守を証明できません。

### ログ記録のベストプラクティス

#### ログの一元管理

必要なログを、アクセス制御、保持期間、取り込み障害の監視が明示された承認済み送信先に収集します。

1. **一貫した形式**: すべてのアプリケーションで一貫したログ形式を使用します
2. **一元化されたリポジトリ**: CloudWatch Logs、OpenSearch、Loki などの中央ログリポジトリを使用します
3. **ログ転送**: Fluent Bit や Fluentd などのログ転送 agent を使用します

#### コンテキスト情報を含める

ログには十分なコンテキスト情報を含めます。

1. **タイムスタンプ**: 正確なタイムスタンプ（ISO 8601 形式を推奨）
2. **Request ID**: 分散システムでリクエストを追跡するための一意な ID
3. **承認済み ID**: user／session ID は、機微情報または識別情報となる場合があります。必要な ID のみを、適切なアクセス制御と保持期間で含めてください。
4. **サービス情報**: サービス名、version、instance ID
5. **エラーの詳細**: エラーコード、エラーメッセージ、stack trace

#### ログレベルのフィルタリング

環境に応じて適切なログレベルを設定します。

1. **開発環境**: 調査のため、DEBUG／TRACE を意図的に使用します。テスト環境でもシークレットのフィルタリングを行ってください。
2. **ステージング環境**: INFO レベル
3. **本番環境**: 有用な INFO／WARN の範囲を選択します。一時的に DEBUG を有効にする場合は、量／期間を制限し、機微情報をフィルタリングしてください。

#### 機微情報の保護

ログ内の機微情報を保護します。

1. **PII のマスキング**: 個人を特定できる情報（PII）をマスキングします
2. **認証情報の除外**: パスワード、token、API key などの認証情報を除外します
3. **暗号化**: 保存時と転送中にログを暗号化します

### アラートのベストプラクティス

#### アラートの優先度

アラート疲れを減らすため、アラートに優先度を設定します。

1. **P1（Critical）**: 直ちに対応する必要がある重大な問題
2. **P2（High）**: サービスで合意された応答時間内に対応する重要な問題。緊急度が高いからといって、営業時間まで自動的に待つわけではありません。
3. **P3（Medium）**: 定期メンテナンス中に対応する必要がある問題
4. **P4（Low）**: 情報提供を目的としたアラート

#### アラートのグループ化

以下の route field を上記の Alertmanager 設定全体に統合し、receiver と child route を保持します。instance ごとに自動的に別 group を作成するのではなく、service context ごとにグループ化してください。

```yaml
route:
  group_by: ['cluster', 'namespace', 'alertname']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
```

#### 対応可能なアラート

トラブルシューティングに十分な情報をアラートに含めます。

1. **明確なタイトル**: 問題の内容を明確に説明するタイトル
2. **証拠と影響**: 観測された症状と影響を説明します。確認が取れるまでは、原因の推測を仮説として示してください。
3. **トラブルシューティング手順**: トラブルシューティングの手順やリンク
4. **関連メトリクスとログ**: 診断に役立つメトリクスやログへのリンク

#### アラートのテスト

アラートシステムを定期的にテストします。

1. **アラートのシミュレーション**: テストアラートを生成します
2. **エスカレーションのテスト**: エスカレーション経路をテストします
3. **フォールトインジェクション**: 管理された環境で障害を注入します

### コスト最適化のベストプラクティス

#### ログ量の最適化

コストを削減するため、ログ量を最適化します。

1. **サンプリング**: 必要な網羅性が許す範囲でのみサンプリングし、欠落範囲を記録します。必要な監査／エラー証跡は保持してください。
2. **フィルタリング**: 不要なログをフィルタリングします
3. **圧縮**: ログを圧縮します

#### メトリクスのカーディナリティ管理

コストを削減するため、メトリクスのカーディナリティを管理します。

1. **種類を限定した label 値**: label 名の数だけでなく、異なる値と label の組み合わせを制御します。
2. **集計**: 詳細なメトリクスをより高いレベルに集計します
3. **収集頻度**: 必要なシグナルを維持できる scrape interval と集計を選択します。粗い収集ではピークが見えなくなることがあります。

#### ストレージ階層化

コスト効率の高いストレージ階層化を実装します。

1. **ホットストレージ**: 最近のログと頻繁にアクセスされるログ
2. **ウォームストレージ**: アクセス頻度が低いログ
3. **コールドストレージ**: アーカイブされたログ

## トラブルシューティングとデバッグ

EKS クラスターの問題をトラブルシューティング、デバッグするためのさまざまな手法を見ていきましょう。

![3つの EKS トラブルシューティング領域（クラスターの問題、ワークロードの問題、一般的な問題）を3つのデバッグツール群（Kubernetes の kubectl ツール、AWS ツール、ネットワーク診断ツール）に対応付けた図。kubectl ツールは中央に配置され、3つすべての領域で使用される。](../.gitbook/assets/en-eks-06-eks-monitoring-logging-5.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-5.html)

### クラスターのトラブルシューティング

#### クラスターの状態確認

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
LOG_GROUP="/aws/eks/$CLUSTER_NAME/cluster"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{ARN:arn,Status:status,Endpoint:endpoint,Logging:logging}'
aws logs describe-log-streams --region "$AWS_REGION" \
  --log-group-name "$LOG_GROUP" --order-by LastEventTime --descending \
  --max-items 10 --query 'logStreams[].{Name:logStreamName,LastEvent:lastEventTimestamp}'
```

実際に返された stream を選んで範囲を限定した GetLogEvents の読み取りを行うか、上記のクエリを使用してください。この確認によってログ記録が有効または無効になることはありません。ログ記録が無効な場合は、別途確認済みの設定手順を使用し、更新完了を検証してください。

#### ノードのトラブルシューティング

node condition を解釈する前に、Kubernetes context を確認し、実際の node を選択してください。Node Ready、スケジューリング可否、アプリケーションのヘルスは別々のシグナルです。

```bash
kubectl config current-context
kubectl get nodes
: "${NODE_NAME:?Choose the node to inspect}"
kubectl describe node "$NODE_NAME"
kubectl get node "$NODE_NAME" -o jsonpath='{.spec.providerID}{"\n"}{.status.nodeInfo.kubeletVersion}{"\n"}{.status.nodeInfo.containerRuntimeVersion}{"\n"}'
```

マネージドノードグループでは、実際の名前を選び、その状態／health を確認します。これはすべての Auto Mode、Fargate、self-managed node に適用されるものではありません。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster}"
: "${AWS_REGION:?Set its Region}"
: "${NODEGROUP_NAME:?Choose the actual managed node group}"
aws eks describe-nodegroup --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --nodegroup-name "$NODEGROUP_NAME" \
  --query 'nodegroup.{Status:status,Version:version,Health:health.issues,Resources:resources}'
```

ノード所有者が承認したアクセス／診断経路を使用してください。SSH の利用可否、ログインユーザー、systemd ツールはノード OS と設定によって異なり、EKS 共通の機能ではありません。Auto Mode、Fargate、Bottlerocket では、それぞれ該当するマネージド／プラットフォームの手順が必要です。すでに認可された標準 Linux EC2 node の session があり、systemd を使用している場合は、範囲を限定して kubelet log、容量、inode を確認します。

```bash
sudo journalctl -u kubelet --since "30 minutes ago" --no-pager
df -h
df -i
```

アクセス可能なインスタンスでは、EC2 console output が起動時の問題の診断に役立つことがありますが、kubelet／アプリケーションログ全体を確認できるわけではありません。すべてのノードで Docker が動いていると想定せず、報告された runtime とその文書化された診断方法を使用してください。

#### Pod のトラブルシューティング

```bash
set -euo pipefail
: "${NAMESPACE:?Set the owned namespace}"
: "${POD_NAME:?Choose the actual Pod}"
: "${CONTAINER_NAME:?Choose its application container}"
kubectl get pod "$POD_NAME" -n "$NAMESPACE" -o wide
kubectl describe pod "$POD_NAME" -n "$NAMESPACE"
kubectl events -n "$NAMESPACE" --for="pod/$POD_NAME"
kubectl logs "$POD_NAME" -n "$NAMESPACE" -c "$CONTAINER_NAME" --tail=100
```

そのコンテナの以前の終了済み instance が利用可能な場合は、そのログも確認します。

```bash
kubectl logs "$POD_NAME" -n "$NAMESPACE" -c "$CONTAINER_NAME" --previous --tail=100
```

previous-log コマンドは、以前の終了済みコンテナ instance がある場合にのみ使えます。任意の古い Pod やノードとともに失われたログを復元するものではありません。exit code、最後の終了理由、probe、リソースイベントを合わせて確認します。再起動数だけでは、OOM や特定の根本原因を証明できません。/bin/bash などの shell command がすべてのアプリケーション image で利用できるわけではありません。

### ネットワークのトラブルシューティング

#### Service のトラブルシューティング

```bash
set -euo pipefail
: "${NAMESPACE:?Set the service namespace}"
: "${SERVICE_NAME:?Choose the actual Service}"
kubectl get service "$SERVICE_NAME" -n "$NAMESPACE" -o yaml
kubectl get endpointslices.discovery.k8s.io -n "$NAMESPACE" \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
kubectl get pods -n "$NAMESPACE" --show-labels
kubectl get networkpolicies -n "$NAMESPACE"
```

現在の endpoint 確認には EndpointSlice を使用します。旧 Endpoints API は非推奨ですが、完全に削除されたわけではありません。selector、ready endpoint address、Service の port／targetPort、protocol を確認してください。DNS 解決、endpoint の readiness、ネットワーク到達性はそれぞれ別の確認事項です。

ローカル port-forward で選択した Service port を調べることはできますが、これは診断経路であり、通常の Pod-to-Service 通信や load balancer が機能する証明ではありません。実際の Service port を指定します。

```bash
set -euo pipefail
: "${NAMESPACE:?Set the service namespace}"
: "${SERVICE_NAME:?Choose the Service}"
: "${SERVICE_PORT:?Choose its service port number}"
kubectl port-forward --address 127.0.0.1 -n "$NAMESPACE" \
  "svc/$SERVICE_NAME" "8080:$SERVICE_PORT"
```

#### Network policy と診断コンテキスト

source の egress と宛先の ingress、namespace／Pod selector、DNS access、強制適用中の CNI を確認します。security group、route、network ACL、service mesh policy、TLS も追加の層となり得ます。任意の一時的 Pod からの probe は、問題が起きているワークロードとは異なる label、ServiceAccount、security group、sidecar を持つ場合があります。

認可された調査では、制限付き profile と互換性のある、確認済みの non-root image を使い、選択した Pod に ephemeral diagnostic container を追加します。DEBUG_IMAGE には承認済みの digest を設定してください。古い BusyBox tag や未確認の latest image は使用しないでください。

```bash
set -euo pipefail
: "${NAMESPACE:?Set the owned Pod namespace}"
: "${POD_NAME:?Choose the Pod}"
: "${CONTAINER_NAME:?Choose the target container}"
: "${DEBUG_IMAGE:?Set the reviewed non-root diagnostic image digest}"
kubectl debug "$POD_NAME" -n "$NAMESPACE" -it \
  --image="$DEBUG_IMAGE" --profile=restricted --target="$CONTAINER_NAME" -- sh
```

これは ephemeral container を追加して Pod を変更する操作であり、該当する RBAC／admission 権限が必要です。記録は Pod が削除されるまで残ります。shell を終了しても ephemeral-container entry は削除されません。process namespace の target は runtime のサポートに依存します。image には意図したツールが含まれ、profile で禁止される capability なしで動作する必要があります。診断の拒否を回避するため、privileged profile に黙って切り替えないでください。

diagnostic shell 内で、target の値も設定してください。ホスト shell の変数は自動的には継承されません。選択した image で使用可能なツールを使います。

```bash
: "${SERVICE_DNS:?Set the intended service DNS name inside this shell}"
: "${SERVICE_PORT:?Set its port inside this shell}"
nslookup "$SERVICE_DNS"
nc -zv "$SERVICE_DNS" "$SERVICE_PORT"
```

FQDN が必要な場合は、実際のクラスター DNS suffix を使用してください。TCP 接続に成功しても、HTTP、アプリケーション認証、TLS が検証されたことにはなりません。packet capture と node debugging には、個別に確認された権限／コンテキストと、範囲を限定した capture filter、期間、ストレージが必要です。一般的な非特権 tcpdump command がどこでも使用できるとは限りません。取得データが切り詰められていても、capture には認証情報やユーザーデータが含まれる場合があります。この監査では診断 Pod、ephemeral container、packet capture、node session を開始していません。

### ログ記録／モニタリングのトラブルシューティング

#### Fluent Bit のトラブルシューティング

この章でインストールする単独 collector では、レンダリングされた DaemonSet と ConfigMap はどちらも logging 内の eks-log-collector です。

```bash
kubectl get daemonset eks-log-collector -n logging
kubectl get pods -n logging -l app.kubernetes.io/instance=eks-log-collector
kubectl logs -n logging -l app.kubernetes.io/instance=eks-log-collector \
  -c aws-for-fluent-bit --prefix --tail=100
kubectl get configmap eks-log-collector -n logging -o yaml
```

CloudWatch アドオンが収集を管理している場合は、amazon-cloudwatch と実際のリソースを確認してください。マウント済み設定、ノードファイルへのアクセス、IRSA／Pod Identity の選択、RBAC、output 接続、buffer／backlog／drop の指標を検証します。無関係な kube-system/fluent-bit-config を作成しても、collector がそれを読み込むとは限りません。設定／ログ出力に機微情報が含まれていないか確認してから共有してください。

#### Prometheus のトラブルシューティング

```bash
kubectl get prometheus,alertmanager -n monitoring
kubectl get pods,pvc -n monitoring
kubectl get servicemonitors,prometheusrules -n monitoring
kubectl port-forward --address 127.0.0.1 -n monitoring \
  svc/monitoring-kube-prometheus-prometheus 9090:9090
```

forwarding 中に `http://127.0.0.1:9090/targets` を確認します。実際の Pod log、target error、証明書の信頼性、名前付き Service port、namespace／label selector、rule、最近の sample を確認してください。ServiceMonitor object があるだけでは、Prometheus がそれを選択していることや endpoint に到達可能であることは証明できません。AMP については、remote-write の失敗／backlog と対象 workspace を別々に確認してください。

#### Grafana のトラブルシューティング

```bash
kubectl get deployment monitoring-grafana -n monitoring
kubectl logs deployment/monitoring-grafana -n monitoring -c grafana --tail=100
kubectl port-forward --address 127.0.0.1 -n monitoring \
  svc/monitoring-grafana 3000:80
```

`http://127.0.0.1:3000` を開き、設定済み data source、認証情報、時間範囲、クエリを確認します。ローカルスタックの Prometheus data-source UID は prometheus です。AMG／AMP には別個の plugin と IAM 要件があります。dashboard が空白になるのは、使用量ゼロではなく、data source／label／時間範囲の誤りや取り込み失敗が原因の場合もあります。

### よくある問題と解決策

#### ImagePullBackOff エラー

pull error、image repository／digest、architecture、registry 認証、ノードのネットワーク経路を確認します。適切な private endpoint／route が利用できる場合に、インターネットアクセスが常に必要とは限りません。ECR では、EC2 node または Fargate Pod の実行 ID と repository policy を検証してください。アプリケーションの IRSA／Pod Identity は kubelet の image-pull ID ではありません。

pull Secret を使う private registry では、承認済みの credential プロセスで、必要な情報がすべて含まれる Docker auth JSON file を準備します。credential-helper への参照しか含まない file は、Kubernetes imagePullSecret には不十分です。新しい所有管理下 Secret を作る場合は、パスワードをコマンド引数に含めず、file path を渡します。

```bash
set -euo pipefail
: "${NAMESPACE:?Set the owned workload namespace}"
: "${DOCKER_CONFIG_JSON:?Set the protected self-contained registry auth JSON file}"
kubectl create secret generic regcred -n "$NAMESPACE" \
  --type=kubernetes.io/dockerconfigjson \
  --from-file=".dockerconfigjson=$DOCKER_CONFIG_JSON"
```

対象の所有管理下ワークロードだけに設定します。Deployment では、この strategic patch によって名前付き imagePullSecrets entry が既存の entry に追加されます。これは Pod template を変更し、rollout を開始します。まず所有者の deployment 手順を確認してください。

```bash
set -euo pipefail
: "${NAMESPACE:?Set the owned workload namespace}"
: "${DEPLOYMENT:?Set the owned Deployment name}"
kubectl patch deployment "$DEPLOYMENT" -n "$NAMESPACE" --type=strategic \
  -p '{"spec":{"template":{"spec":{"imagePullSecrets":[{"name":"regcred"}]}}}}'
```

既存 Secret については所有者のローテーション手順を使用し、その他の registry 参照を保持してください。包括的な解決策として namespace の default ServiceAccount を変更しないでください。Secret を作成しただけでは、registry へのログイン、image の存在、pull の成功は検証されません。

#### CrashLoopBackOff エラー

選択したコンテナの現在／以前の log、exit code、termination reason、startup／liveness probe、設定、リソースイベントを照合します。OOMKilled、probe failure、アプリケーションの終了は原因が異なります。依存先が起動していないことや command の誤りによって、コンテナが再起動する場合もあります。通常の image にツールがない場合は、前述の範囲を限定した診断手順を使用してください。証跡を収集する前に再起動／削除しないでください。

#### ノードが NotReady の状態

適切なプラットフォームアクセス経路を使って、Ready status／reason、node／lease の鮮度、pressure condition、実際の runtime／kubelet 診断を確認します。ディスク容量、inode 枯渇、ネットワーク／API 到達性、runtime の障害には、それぞれ異なる対処が必要です。NotReady の表示だけから、自動修復の対象となることや安全に drain できることを推測しないでください。

#### Service 接続の問題

上記の Service → EndpointSlice → Pod の経路を確認し、その後 source／destination のネットワーク統制と、アプリケーションの待ち受け port／protocol を調べます。代表的なワークロードのコンテキストからテストしてください。port-forward、DNS lookup、TCP handshake のいずれかが成功しただけでは、エンドツーエンドでサービスが正常であるとは証明できません。

### デバッグツール

Kubernetes の状態／event には kubectl、対応するマネージドサービスの状態には AWS CLI、接続性の確認には承認済みの実行コンテキスト内ネットワークツールを使います。証跡を保持し、確認だけを行う操作と、Pod 作成、template 変更、ノード drain、ログ設定変更を伴う操作を区別してください。

#### CloudWatch Logs Insights の結果を取得する

StartQuery が返すのは非同期 query ID であり、最終結果ではありません。この Bash／Python の例は、macOS 専用の date -v option を使わずに UTC epoch 秒を使用し、回数に上限を設けてポーリングしてから、Complete の場合にのみ結果を表示します。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the log group Region}"
: "${LOG_GROUP:?Set the owned log group to query}"
python3 - "$LOG_GROUP" <<'PY'
import datetime
import json
import sys
end = datetime.datetime.now(datetime.timezone.utc)
request = {
    "logGroupName": sys.argv[1],
    "startTime": int((end - datetime.timedelta(hours=1)).timestamp()),
    "endTime": int(end.timestamp()),
    "queryString": "fields @timestamp, @message | sort @timestamp desc | limit 50",
}
with open("logs-query-request.json", "w") as stream:
    json.dump(request, stream, indent=2)
PY
STARTED=$(aws logs start-query --region "$AWS_REGION" \
  --cli-input-json file://logs-query-request.json --output json)
QUERY_ID=$(python3 - "$STARTED" <<'PY'
import json
import sys
value = json.loads(sys.argv[1]).get("queryId")
if not isinstance(value, str) or not value:
    raise SystemExit("StartQuery did not return a query ID")
print(value)
PY
)
printf 'Started query %s\n' "$QUERY_ID" >&2
for ((query_attempt = 1; query_attempt <= 20; query_attempt++)); do
  aws logs get-query-results --region "$AWS_REGION" --query-id "$QUERY_ID" \
    --output json > logs-query-result.json
  QUERY_STATE=$(python3 - <<'PY'
import json
with open("logs-query-result.json") as stream:
    print(json.load(stream)["status"])
PY
)
  case "$QUERY_STATE" in
    Complete)
      cat logs-query-result.json
      exit 0
      ;;
    Scheduled|Running)
      if (( query_attempt < 20 )); then sleep 3; fi
      ;;
    *)
      printf 'Query %s ended with status %s; inspect logs-query-result.json\n' "$QUERY_ID" "$QUERY_STATE" >&2
      exit 1
      ;;
  esac
done
printf 'Query %s is still %s; inspect it again or stop it explicitly if no longer needed\n' "$QUERY_ID" "$QUERY_STATE" >&2
exit 2
```

ポーリング回数の上限は、サービスの timeout ではありません。query の実行が続いている場合は、再度確認するか、不要になった場合は StopQuery を明示的に使って停止します。ロググループ／時間範囲と必要な IAM 権限を限定し、クエリ料金も考慮してください。この監査では CloudWatch query もクラスターのデバッグ操作も実行していません。

## まとめ

このドキュメントでは、Amazon EKS クラスターのモニタリングとログ記録に関するさまざまなツール、手法、ベストプラクティスについて説明しました。効果的なモニタリングとログ記録の戦略を実装すると、クラスターの状態を継続的に把握し、問題を早期に検出して、問題発生時に迅速に対応できます。

主なトピック:

1. **モニタリングとログ記録の概要**: モニタリングとログ記録の重要性およびアーキテクチャ
2. **EKS コントロールプレーンのログ記録**: コントロールプレーンのログタイプと有効化方法
3. **コンテナのログ記録**: Fluent Bit と CloudWatch Container Insights を使ったコンテナログの収集
4. **クラスターのモニタリング**: CloudWatch、Prometheus、Grafana を使ったクラスターのモニタリング
5. **アラートとイベント管理**: CloudWatch アラームと Prometheus Alertmanager を使ったアラート設定
6. **ログ分析と可視化**: CloudWatch Logs Insights、OpenSearch、Grafana Loki を使ったログ分析
7. **モニタリングとログ記録のベストプラクティス**: 効果的なモニタリングとログ記録のベストプラクティス
8. **トラブルシューティングとデバッグ**: よくある問題と解決策

EKS クラスターのモニタリングとログ記録は継続的なプロセスです。クラスターとアプリケーションの要件を満たすため、継続的に改善する必要があります。

## 参考資料

- [Amazon EKS のモニタリングに関するベストプラクティス](https://docs.aws.amazon.com/eks/latest/userguide/eks-observe.html)
- [Amazon EKS のログ記録に関するベストプラクティス](https://docs.aws.amazon.com/prescriptive-guidance/latest/amazon-eks-observability-best-practices/logging-best-practices.html)
- [Kubernetes のモニタリングアーキテクチャ](https://kubernetes.io/docs/tasks/debug-application-cluster/resource-usage-monitoring/)
- [Prometheus のドキュメント](https://prometheus.io/docs/introduction/overview/)
- [Grafana のドキュメント](https://grafana.com/docs/grafana/latest/)
- [Fluent Bit のドキュメント](https://docs.fluentbit.io/manual/)
- [Amazon CloudWatch のドキュメント](https://docs.aws.amazon.com/cloudwatch/)
- [Amazon OpenSearch Service のドキュメント](https://docs.aws.amazon.com/opensearch-service/)

## クイズ

この章で学んだ内容を確認するには、[トピッククイズ](../quizzes/eks/06-eks-monitoring-logging-quiz.md)に挑戦してください。
