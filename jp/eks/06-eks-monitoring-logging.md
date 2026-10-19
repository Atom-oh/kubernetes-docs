# Amazon EKS のモニタリングとロギング

> **最終更新日**: 2026年10月16日

効果的なモニタリングとロギングは、Amazon EKS クラスターの信頼性、可用性、パフォーマンスを維持するうえで不可欠です。このドキュメントでは、EKS クラスターにモニタリングとロギングを実装するためのさまざまなツール、手法、ベストプラクティスについて説明します。

## 目次

1. [モニタリングとロギングの概要](#monitoring-and-logging-overview)
2. [EKS コントロールプレーンのロギング](#eks-control-plane-logging)
3. [コンテナのロギング](#container-logging)
4. [クラスターのモニタリング](#cluster-monitoring)
5. [アラートとイベント管理](#alerting-and-event-management)
6. [ログの分析と可視化](#log-analysis-and-visualization)
7. [モニタリングとロギングのベストプラクティス](#monitoring-and-logging-best-practices)
8. [トラブルシューティングとデバッグ](#troubleshooting-and-debugging)

## モニタリングとロギングの概要

### モニタリングとロギングの重要性

Amazon EKS クラスターでモニタリングとロギングが重要な理由は次のとおりです。

1. **可視性**: クラスターの状態、パフォーマンス、動作を把握できます
2. **問題の検出**: 問題が重大になる前に早期に検出します
3. **傾向分析**: パフォーマンスとリソース使用量の傾向を時系列で特定します
4. **キャパシティプランニング**: リソース要件を予測し、計画を立てます
5. **セキュリティと監査**: 該当する統制に必要な調査と証拠の収集を支援します
6. **トラブルシューティング**: 問題発生時の迅速な診断と解決を可能にします

### モニタリングとロギングのアーキテクチャ

EKS クラスターの包括的なモニタリングおよびロギングアーキテクチャは、次のコンポーネントで構成されます。

AWS は、管理対象コントロールプレーンのログを CloudWatch Logs に配信します。コンテナランタイムは CRI ログファイルを書き込み、kubelet はローテーションとログへのアクセスを管理し、ノードコレクターがファイルを読み取ります。メトリクスとトレースには、設定済みの収集／エクスポート経路が使用されます。

<!-- Audit: parent diagram repair needed for direct control-plane delivery and runtime-versus-kubelet log responsibilities.
![Architecture diagram showing EKS control-plane logs, pod logs, and node metrics flowing through Fluent Bit and Prometheus into CloudWatch Logs/Metrics, Amazon OpenSearch, and Grafana/Alertmanager.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-0.html)
-->

### モニタリングとロギングの戦略

効果的なモニタリングとロギングの戦略を策定するには、次の手順に従います。

1. **目標を定義する**: モニタリングとロギングの目標および要件を定義します
2. **メトリクスとログを特定する**: 収集する主要なメトリクスとログを特定します
3. **ツールを選択する**: 要件を満たすモニタリングツールとロギングツールを選択します
4. **ベースラインを確立する**: 通常の動作に関するベースラインを確立します
5. **アラートを設定する**: 重要なイベントやしきい値に対するアラートを設定します
6. **自動化する**: モニタリングとロギングのプロセスを可能な限り自動化します
7. **定期的に見直す**: モニタリングとロギングの戦略を定期的に見直し、改善します

## EKS コントロールプレーンのロギング

EKS は、選択した管理対象コントロールプレーンのログタイプを CloudWatch Logs にエクスポートします。ノード側のコレクターが管理対象コントロールプレーンのファイルシステムをスクレイプすることはありません。ログ配信はベストエフォートです。アクセス権限と保持期間を設定し、ログ欠落の検出も構成したうえで、実際にログが届くことを確認してください。

### コントロールプレーンのログタイプ

| タイプ | 目的 |
|---|---|
| `api` | API サーバーコンポーネントの診断 |
| `audit` | 監査ポリシーとレベルで選択された Kubernetes リクエスト |
| `authenticator` | EKS IAM 認証の診断 |
| `controllerManager` | コアコントローラーマネージャーの操作 |
| `scheduler` | スケジューラーの判断と診断 |

監査ログは、すべてのリクエスト本文やすべてのアプリケーションアクションを無条件に記録するものではありません。Secret に関する記録がメタデータのみの場合もあり、ポリシーによって一部のイベントは除外されます。CloudTrail の AWS API レコードとアプリケーションのデータアクセスログは、別個の証拠ソースです。

### ロギングの確認と有効化

変更を行う前に、対象クラスターの所有者を確認し、そのクラスターの Region、ARN、現在のロギング設定、更新状態を調べてください。ロギングの変更には、文書化されたサブネットの IP 容量が必要で、CloudWatch の取り込み／ストレージ料金が発生します。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{ARN:arn,Status:status,Logging:logging}'
```

承認済みの変更を行う場合、次のコマンドは5種類すべてのログタイプを有効にし、返された更新情報を確認します。

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

最後のコマンドはステータス確認であり、完了を待つコマンドではありません。Successful または最終的な失敗状態になるまで DescribeUpdate を繰り返し、実際に有効な設定とログの到着を確認してください。更新 ID は処理完了の証明ではありません。選択したタイプだけを有効にしても、無関係な既存タイプが無効になるとは限りません。明示的に無効化する場合は、保持期間と可視性に関する別個の判断が必要です。

確認済みの eksctl CLI では、--approve を省略すると変更内容をプレビューします。CLUSTER_NAME と AWS_REGION に同じ確認済みクラスターの値を設定し、プレビューを確認してください。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
eksctl utils update-cluster-logging \
  --region "$AWS_REGION" --cluster "$CLUSTER_NAME" \
  --enable-types api,audit,authenticator,controllerManager,scheduler
```

計画を確認した後、別の適用コマンドを使用します。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
eksctl utils update-cluster-logging \
  --region "$AWS_REGION" --cluster "$CLUSTER_NAME" \
  --enable-types api,audit,authenticator,controllerManager,scheduler --approve
```

### コントロールプレーンログのクエリ

実際の `/aws/eks/CLUSTER_NAME/cluster` グループを使用します。最初の2つの例は、選択したコンポーネントのストリームを対象としたテキスト検索のヒューリスティックであり、エラー率を完全に測定するものではありません。

**API の診断:**

```text
fields @timestamp, @message
| filter @logStream like /kube-apiserver-/ and @logStream not like /audit/
| filter @message like /[Ee]rror/
| sort @timestamp desc
| limit 20
```

**IAM 認証の診断:**

```text
fields @timestamp, @message
| filter @logStream like /authenticator/
| filter @message like /[Ff]ailed|[Dd]enied|[Uu]nauthorized/
| sort @timestamp desc
| limit 20
```

**監査拒否:** 生の JSON テキスト内に `responseStatus.code` という文字列を検索するのではなく、検出済みの JSON フィールドを使用してください。サンプルイベントでフィールドの形式を確認します。

```text
fields @timestamp, user.username, verb, objectRef.resource, objectRef.namespace, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code in [401, 403]
| sort @timestamp desc
| limit 20
```

### 保持期間とコスト管理

返された prefix 検索結果から、正確なグループエントリを確認します。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
aws logs describe-log-groups --region "$AWS_REGION" \
  --log-group-name-prefix "/aws/eks/$CLUSTER_NAME/cluster" \
  --query 'logGroups[].{Name:logGroupName,RetentionDays:retentionInDays,KmsKey:kmsKeyId}'
```

承認済みのポリシーで30日間の保持が必要な場合、変更コマンドは `aws logs put-retention-policy --region "$AWS_REGION" --log-group-name "/aws/eks/$CLUSTER_NAME/cluster" --retention-in-days 30` です。30日はポリシーの例であり、普遍的なコンプライアンス要件ではありません。保持期間を短縮すると古い証拠が期限切れになる可能性があります。延長しても削除済みログは復元されません。保持期間だけでは、アーカイブへの配信、完全性、コンプライアンスは証明されません。

### EKS Capabilities のロギング（GitOps、ACK、kro）

2026年6月4日に発表された機能はサポートされています。ACK、kro、Argo CD の capability controller は、クラスター**外部の** AWS 管理インフラストラクチャで実行され、CloudWatch Vended Logs を通じて構造化されたコントローラーログを配信できます。これは capability ごとの配信設定を使い、標準のコントロールプレーンログタイプ5種類とは別に構成します。

| Capability | ログタイプ |
|---|---|
| ACK | `EKS_CAPABILITY_ACK_LOGS` |
| kro | `EKS_CAPABILITY_KRO_LOGS` |
| Argo CD | `EKS_CAPABILITY_ARGOCD_APPLICATION_LOGS`, `EKS_CAPABILITY_ARGOCD_APPLICATIONSET_LOGS`, `EKS_CAPABILITY_ARGOCD_COMMITSERVER_LOGS`, `EKS_CAPABILITY_ARGOCD_REPOSERVER_LOGS`, `EKS_CAPABILITY_ARGOCD_SERVER_LOGS` |

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

所有者は、この ARN とログタイプを使って PutDeliverySource を設定し、承認済みの宛先を使って PutDeliveryDestination を設定してから、CreateDelivery で両者を接続します。配信を有効にする前に、宛先ポリシー、暗号化、クロスアカウント権限、保持期間を確認してください。

CloudWatch Logs の宛先では Logs Insights のクエリを実行できます。S3 の宛先は、選択した S3/Athena ワークフローで使うオブジェクトです。Firehose は設定済みのターゲットにレコードを送信します。いずれも CloudWatch Logs Insights で自動的にクエリできるわけではありません。ACK レコードには、サービスコントローラーでフィルタリングするための controllerGroup が含まれます。実際にログが配信されることとクエリフィールドを確認し、Vended Logs の料金も考慮してください。

参考資料: [EKS コントロールプレーンのロギング](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)、[監査ポリシーとクエリの例](https://docs.aws.amazon.com/eks/latest/best-practices/auditing-and-logging.html)、[capability controller のログ](https://docs.aws.amazon.com/eks/latest/userguide/capabilities-controller-logs.html)。

## コンテナのロギング

コンテナランタイムは stdout/stderr をノードの CRI ログファイルに書き込みます。kubelet はローテーションと Pod のログアクセスを管理します。コレクターはファイルを tail して、選択したバックエンドにレコードを転送します。JSON 形式のアプリケーションメッセージも CRI ラッパーの内部にあります。コンテナログ行全体を Docker JSON のように解析してはいけません。

<!-- Audit: parent diagram repair needed for direct control-plane delivery and runtime-versus-kubelet log responsibilities.
![Architecture diagram showing container stdout/stderr picked up by kubelet, read by a log agent, and fanned out to CloudWatch Logs, Amazon OpenSearch, and Amazon S3.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-1.html)
-->

### コレクターの管理主体を選ぶ

CloudWatch Observability add-on にはコンテナログコレクターが含まれます。これを選択したスタックで使用する場合は、add-on が管理する設定を使用してください。以下のスタンドアロン Fluent Bit の例は、独立して管理するログパイプライン用の代替手段です。重複やコストに関する明確な計画なしに、同じファイル／宛先を扱うコレクターを重複してインストールしないでください。

### 配線済み Fluent Bit の例

この例では AWS chart 0.2.0 と image 3.4.14（Fluent Bit 5.0.9）を使用します。公開リリースと設定を確認済みです。管理下にある Linux/containerd の EC2 ノードを対象とし、affinity によって Fargate、Auto Mode、Hybrid のラベルを意図的に除外しています。それらのモードでは、個別にサポートされた収集／ID 設計が必要です。コレクターは対象ノードの taint を許容するため、配置と platform-agent の admission 権限を確認してください。

logging 名前空間を用意し、サービスアカウント logging/eks-log-collector 用の最小権限 IRSA ロール EKSLogWriter と、管理対象の CloudWatch log group を作成します。アカウント、ロール、Region、クラスター固有のグループを一貫して置き換えてください。セキュリティの章に記載されているとおり、IAM OIDC provider／trust audience／subject を設定します。コレクターには CloudWatch のストリーム／書き込み権限と、リージョン別 STS／バックエンドへの接続性が必要です。これらの IAM 前提条件は、Kubernetes メタデータの RBAC とは別です。

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

Chart 0.2.0 では、ネイティブの cloudWatchLogs output がデフォルトで有効になり、以前の cloudWatch output は無効になります。そのため、cloudWatch.region だけでは、有効なネイティブ output は設定されません。上記の値では、実際の output の Region／group を設定し、完全なレコードを保持しています。log_key を使うと選択した値だけが送信され、Kubernetes コンテキストが失われる可能性があります。

logStreamTemplate は fallback prefix を備えた record-accessor 構文を使います。logStreamPrefix は文字列の prefix であり、レコードごとの Kubernetes 式ではありません。CRI multiline parser がコンテナラッパーを処理し、Merge_Log が JSON アプリケーションフィールドを data の下に配置して log を保持します。ワークロードの annotation では、パーサーを選択したり、この例の収集対象から除外したりできません。

### レンダリング時のメタデータ RBAC の制限

公開されている chart の広範な ClusterRole には nodes/proxy と、旧式の PodSecurityPolicy ルールが含まれています。この API-server メタデータモードでは Use_Kubelet Off を明示しており、選択した Pod／Namespace の読み取り権限が必要です。kubelet proxy へのアクセスは必要ありません。Python 3 と PyYAML を使う次の post-renderer を fluent-bit-rbac.py として保存します。別の広範な role が黙って残るのではなく、予期しない chart の ID を検出して処理を中断します。

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

新しく管理下のリリースを作成する場合は、values と renderer を一緒に指定してインストールします。

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
chmod +x fluent-bit-rbac.py
helm install eks-log-collector eks/aws-for-fluent-bit \
  --version 0.2.0 --namespace logging --create-namespace \
  -f fluent-bit-values.yaml --post-renderer ./fluent-bit-rbac.py \
  --wait --timeout 5m
```

アップグレードのたびに、同じレビュー済み post-renderer を使用してください。chart バージョン、リリース ID、namespace、メタデータモードを変更するときは再検証します。レンダリングされた ConfigMap は実際の DaemonSet にマウントされます。無関係な ConfigMap だけを適用しても、その設定は変更されません。アカウント／IRSA ロールと log group は前提条件であり、この chart の例が作成するリソースではありません。

### バッファリング、ローテーション、障害時の動作

ホストログは読み取り専用で、チェックポイントとファイルシステムバッファの状態には別のノードローカルディレクトリを使用します。tail database はオフセットを記録するものであり、それ自体は耐久性のあるバックエンドアーカイブではありません。ノードの置き換えによって、その状態が失われる可能性があります。チェックポイントがない場合、Read_from_Head On は保持されているファイル内容を読み取るため、バックフィルと重複への対策を計画してください。

512M の output queue 上限と backlog memory 設定は、配分の例です。output queue が storage.total_limit_size に達すると、Fluent Bit は古い chunk を破棄することがあります。Skip_Long_Lines On も、大きすぎるレコードを意図的にスキップします。有限のバッファ、再試行、ノードローカルの状態があっても、欠損のない配信や exactly-once 配信が保証されるわけではありません。再試行、破棄されたレコード、ディスク容量、宛先の障害を監視し、実際のログ量と停止時間に応じて上限を検証してください。

### 任意の OpenSearch へのファンアウト

管理対象の VPC domain と、コレクターの IAM／FGAC マッピングを準備してから、この overlay を fluent-bit-opensearch-values.yaml として保存し、endpoint の hostname を置き換えます。同じレビュー済み Helm 操作に `-f fluent-bit-opensearch-values.yaml` を追加します。CloudWatch を有効のままにすると両方の宛先にコピーが送信されます。OpenSearch のみを意図的に選ぶ場合に限り、cloudWatchLogs.enabled=false を設定してください。

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

TLS の証明書／hostname 検証を有効にし、固定され、管理された index／rollover 設計を使用してください。Pod ごとの index パターンを使うと、index／shard 数が過剰になることがあります。Generate_ID によって再試行時の重複 index 登録は抑えられますが、独立した output と障害復旧についても検証が必要です。一方の宛先への書き込み成功は、もう一方への配信を証明しません。

### その他のロギングスタック

管理対象のデプロイで必要な parser/output plugin、ホストマウント、ID、TLS 設定が提供される場合は、Fluentd も選択肢になります。汎用 JSON parser は CRI ラッパーをデコードしません。また、ssl_verify を無効化しても証明書エラーの解決にはなりません。旧 Elastic Helm chart repository はアーカイブされています。Elastic をデプロイする場合は、保守されている製品／Operator のインストール手順を使用してください。

loki-stack chart は非推奨とされ、Promtail agent は2026年3月2日に EOL に達しました。Loki には、Alloy のようなサポート対象のクライアントを使い、現在サポートされているデプロイ方法を使用してください。ストレージ、アクセス制御、保持期間も明示的に設定します。専用のセットアップ手順は、[Loki ガイド](../observability/logging/01-loki.md)と[コレクターガイド](../observability/logging/05-collectors.md)を参照してください。Promtail agent の廃止には、別個に保守されている lambda-promtail client は含まれません。

### 構造化アプリケーションログ

次の保持された例は合成したアプリケーションデータであり、新たな測定値でも、この監査の記録でもありません。timestamp は元の例示値のままです。

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

設定済みのパイプラインでは、CRI レコードが転送用 timestamp を提供し、アプリケーション JSON は data の下に格納されます。アプリケーションフィールドで timestamp を上書きする前に、タイムゾーンとクロックの動作を確認してください。ユーザー／セッション ID は依然として機微情報になり得るほか、個人にひも付けられる可能性もあります。必要最小限にし、認証情報や生のセッショントークンをログに記録しないでください。

以下の例は、このコレクターのレコード形式を前提としています。他のコレクターではフィールドパスが異なる場合があります。

```text
fields @timestamp, kubernetes.namespace_name, kubernetes.pod_name, data.level, log
| filter kubernetes.namespace_name = "production"
| filter data.level in ["ERROR", "error"]
| sort @timestamp desc
| limit 100
```

検証では、公開 chart/image のメタデータ、実際の Helm ConfigMap／DaemonSet の配線、ネイティブ Kubernetes schema、post-renderer の失敗ケースを確認しました。イメージのインストール、コレクタープロセスの起動、AWS へのログ送信、本番ファイルシステムへのアクセスはテストしていません。展開前に、実際のノード権限、IRSA 認証情報、エンドツーエンドの配信を検証してください。

参考資料: [AWS image release 3.4.14](https://github.com/aws/aws-for-fluent-bit/releases/tag/v3.4.14)、[CloudWatch output](https://docs.fluentbit.io/manual/data-pipeline/outputs/cloudwatch)、[Fluent Bit のバッファリング](https://docs.fluentbit.io/manual/data-pipeline/buffering)、[Promtail のライフサイクル](https://grafana.com/docs/loki/latest/send-data/promtail/)。

## クラスターのモニタリング

EKS クラスターの状態、パフォーマンス、リソース使用量を追跡するには、効果的なクラスター監視が不可欠です。このセクションでは、EKS クラスターをモニタリングするためのさまざまなツールと手法を紹介します。

![Diagram mapping monitoring solutions (CloudWatch Container Insights with AMP/AMG, the Prometheus stack with kube-state-metrics, Node Exporter and Grafana, and X-Ray/OpenTelemetry tracing) to the cluster-, node-, and pod-level telemetry they cover in an EKS cluster.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-2.html)

### CloudWatch Container Insights

CloudWatch Observability add-on は、Container Insights、コンテナログ収集、Application Signals の機能を組み合わせます。管理主体を1つにし、別のコレクターが同じファイルを読むような Fluent Bit コレクターの重複を避けてください。データを期待する前に、ID、サポートされているノードアクセス、バックエンド接続を設定します。

#### クラスターと互換性のある add-on build の確認

標準の Linux EC2 の例では、適切な EKS Pod Identity agent と専用の CloudWatch role を準備します。trust の対象を、このクラスターと amazon-cloudwatch/cloudwatch-agent に限定してください。add-on／association に必要な権限と、承認済み role を渡す権限も用意します。既存の Helm release、ServiceAccount annotation、association も EKS add-on の一覧とともに確認してください。既存コレクターがある場合は、管理者の移行／アップグレード手順に従います。

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

固定された v5.0.0 の例にダウングレードせず、catalog から互換性のあるレビュー済み build を選択してください。add-on の設定 schema はバージョンごとに異なります。ここで行ったローカルの参照レンダリングでは Helm chart 6.6.0 を使用しました。この chart の Fluent Bit DaemonSet は、agent の ID 経路と同じ cloudwatch-agent ServiceAccount を使います。

#### Auto Monitor の明示的な設定

新規インストールの例として、次の内容を cloudwatch-config.json として保存します。アプリケーションの展開を確認するまで、広範な自動ワークロード選択と自動再起動を無効にしつつ、デフォルトのコンテナログ設定を保持します。

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

この設定が制御するのは Auto Monitor の選択／再起動であり、あらゆるテレメトリソースではありません。既存の annotation、カスタム selector、手動で計装したアプリケーションは別途確認してください。ローカル環境で Python 3 と jsonschema を使用できる場合は、選択した build の schema を取得し、設定を検証します。

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

#### 新しい管理下インストールの作成

CloudWatch role には、選択した機能に必要な CloudWatch／trace の権限が事前に必要です。次のコマンドでは、レビュー済みの schema/build を再確認し、既存の add-on または collector association がある場合は処理を中断して、競合するリソースを引き継がないようにします。

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

CreateAddon は非同期です。add-on が ACTIVE になるまで status／health を確認し、その後 agent／collector の Pod、実際の ContainerInsights datapoint、意図した log group を確認してください。リクエストの成功、ACTIVE status、ダッシュボードの表示だけでは、取り込みが完全に行われたことは証明されません。上記の最後の DescribeAddon コマンドは確認用であり、完了を待つコマンドではありません。再試行の前に障害と権限を検証してください。インストールを強制するために、未確認の上書きや既存設定の消去を行わないでください。

#### バージョン 5.0.0 での変更点

2026年2月26日のデフォルト APM の変更は実際のもので、バージョン 5.0.0 以降では新規インストールとアップグレード時に Application Signals Auto Monitor がデフォルトで有効になります。monitorAllServices のデフォルト値は true、restartPods のデフォルト値は false です。対象はサービスにマッピングされたサポート対象の Deployment、DaemonSet、StatefulSet で、デフォルトでは kube-system と amazon-cloudwatch を除外します。対象範囲内の新規ワークロードや再起動されたワークロードは、個々のワークロードに annotation を付けなくても計装されることがあります。すでに実行中の Pod が直ちに再計装されるとは限りません。

サポート対象の言語／ワークロードを選び、既存の OpenTelemetry／APM 統合、sampling、コストを確認し、再起動を伴う展開を制御してください。明示的な除外が優先されます。Container Insights は Linux と Windows の設定をサポートしますが、Application Signals は EKS Windows node をサポートしません。Fargate と Hybrid のノード収集／ID には、文書化されたプラットフォーム固有の経路が必要です。汎用 DaemonSet の例だけからサポートを推定しないでください。

#### メトリクス、ダッシュボード、アラーム

Container Insights のコンソールビューで実際のクラスターを選択し、公開されたメトリクス名、dimension、直近のデータを確認してください。Node の CPU／memory／filesystem メトリクスは、ノードの使用状況を示します。Pod の CPU／memory utilization は、Pod の request ではなくノードの limit を分母にします。文書化されたメトリクスには namespace／service／cluster 単位の集計値がありますが、集約された percentage が、異種クラスター全体の容量加重 utilization になるとは限りません。

ダッシュボードはデータの確認に役立ちますが、すべてのアラームを作成したり、通知の配信を保証したりするものではありません。後述の CloudWatch Alarms の例では、ノードメトリクスと、明示的に選択した dimension に対する Maximum を使用します。メトリクスが利用できることを確認し、ワークロードに適切なアラームと通知経路を設定してください。

検証では、既存の公開 chart、そのデフォルトのログ設定のレンダリング、Auto Monitor の引数に加え、9件の schema／所有権／失敗フローのモックケースを確認しました。合成したテスト schema は helper の動作を確認するものであり、上記の実際の build 固有 schema の代わりにはなりません。この監査では add-on、ワークロードの計装、テレメトリのエクスポート、AWS リソースはいずれも実行していません。

参考資料: [CloudWatch add-on のインストールと Auto Monitor](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Observability-EKS-addon.html)、[デフォルト APM の発表](https://aws.amazon.com/about-aws/whats-new/2026/02/application-performance-monitoring-cloudwatch-eks/)、[Container Insights のメトリクス](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html)。

### EKS Node Monitoring Agent

EKS Node Monitoring Agent は、ノードレベルのシステム、ストレージ、ネットワーク、アクセラレーターの健全性条件を公開します。2026年2月24日にオープンソース化され、EKS Auto Mode に含まれています。別途管理する add-on としてインストールする場合は、リリースを選択する前に、クラスターの実際のバージョン、既存の add-on、互換性のある agent バージョンを確認してください。

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

レビュー済みのバージョンとサポート対象のノード設定を使い、既存の add-on 管理者を通じてインストールまたは更新してください。add-on の create コマンドは、既存インストールのアップグレード手順ではありません。

condition 名だけでは、ノードが異常かどうかは分かりません。status と reason を読み、それぞれの condition の意味を解釈してください。Ready=False と MemoryPressure=False は異なる状態です。

```bash
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{range .status.conditions[*]}{"  "}{.type}{"="}{.status}{" reason="}{.reason}{"\n"}{end}{end}'
```

モニタリングと修復の有効化は別です。Auto Mode では自動ノード修復が有効です。managed node group では nodeRepairConfig、Karpenter では NodeRepair feature gate を使用します。agent による修復動作について判断する前に、実際の managed node group を確認してください。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${NODEGROUP_NAME:?Set an actual managed node group name}"
: "${AWS_REGION:?Set the cluster Region}"
aws eks describe-nodegroup --region "$AWS_REGION" \
  --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --query 'nodegroup.{Name:nodegroupName,Repair:nodeRepairConfig,Health:health.issues}'
```

修復の対象になるかどうかは、condition、reason、待ち時間、適用される安全措置によって異なります。文書化されているデフォルトでは、MemoryPressure と DiskPressure に自動修復アクションはありません。報告された condition や agent のインストールだけで、ノードが置き換えられると判断しないでください。オープンソース agent をカスタマイズする場合も、選択した修復設定に対する condition の意味をテストする必要があります。

参考資料: [オープンソース化の発表](https://aws.amazon.com/about-aws/whats-new/2026/02/amazon-eks-node-monitoring-agent-open-source/)、[自動ノード修復](https://docs.aws.amazon.com/eks/latest/userguide/node-repair.html)。

### Prometheus と Grafana

Prometheus は時系列データベース兼モニタリングシステムであり、Grafana はメトリクスを可視化するダッシュボードツールです。この2つのツールを組み合わせて、EKS クラスターを包括的にモニタリングできます。

#### Amazon Managed Service for Prometheus と Grafana

AMP は取り込まれた Prometheus メトリクスを保存してクエリします。AMG は設定済みのデータソースにクエリを実行し、ダッシュボードを表示します。どちらかの workspace を作成しても、scraper が自動的にデプロイされたり、AWS ID が付与されたり、データソースが接続されたりするわけではありません。この例では、管理下の既存 workspace を確認したうえで、以下の kube-prometheus-stack release を拡張します。Prometheus をもう1つインストールすることはありません。

**AMP 取り込み ID と values**

ServiceAccount monitoring/amp-writer 用の IRSA role を準備します。trust policy には、このクラスターの OIDC provider と、正確な `sub=system:serviceaccount:monitoring:amp-writer` および `aud=sts.amazonaws.com` の条件を使用してください。対象 workspace ARN に対する aps:RemoteWrite を許可します。Prometheus プロセスには投影された token が必要で、STS と AMP endpoint に到達できなければなりません。Kubernetes RBAC は別の権限経路です。この例に、無関係な Pod Identity association や静的 AWS key も設定しないでください。

次のコマンドは workspace を読み取り、レビュー済み chart 92.9.0 用の overlay を書き出します。`/api/v1/` の有無を含む文書化された endpoint 形式を受け入れ、remote_write をちょうど1回だけ追加します。Python 3 が必要です。workspace は作成しません。

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

amp-values.json を monitoring-values.yaml と組み合わせて、管理者がレビューしたインストール／アップグレード用の values に含めます。この overlay は remoteWrite のリストを置き換えます。既存の宛先や external label は、意図を確認したうえで維持してください。新規リリースの場合は、以下のインストールコマンドに -f amp-values.json を追加します。既存リリースの場合はすべての現在の設定を保持し、レンダリングされた差分と展開を確認してから、管理者のアップグレード手順に従って適用します。ServiceAccount を変更すると Prometheus Pod の ID が変わります。chart 92.9.0 は、デフォルトの API-server／kubelet ServiceMonitor の認証に、明示的な ServiceAccount token Secret を使用します。その Secret を保護し、ローテーション／失効の手順に従ってください。この Secret は、有効期間の短い audience-bound IRSA token とは別のものです。依存するすべての monitor 認証情報を置き換えずに createTokenSecret を無効にすると、レンダリングまたは認証が失敗します。

複数の replica を使用する場合、重複 scrape が無償であると仮定せず、AMP の文書化された HA deduplication label と replica topology を設定してください。cardinality、保持期間、取り込み予算は実際のワークロードに基づいて設定します。remote-write の失敗／backlog を確認し、対象 workspace で直近のデータをクエリしてください。Helm rollout の成功は、取り込みが行われた証拠ではありません。

**AMG の認証とデータソース接続**

```bash
set -euo pipefail
: "${AMG_REGION:?Set the Grafana workspace Region}"
: "${AMG_WORKSPACE_ID:?Set the owned Grafana workspace ID}"
aws grafana describe-workspace --region "$AMG_REGION" \
  --workspace-id "$AMG_WORKSPACE_ID" \
  --query 'workspace.{ID:id,Status:status,Version:grafanaVersion,Endpoint:endpoint,Role:workspaceRoleArn,Authentication:authentication,PermissionType:permissionType}'
```

workspace のユーザー認証（IAM Identity Center/SAML）、Grafana のユーザー権限、workspace の AWS データソース IAM role は、それぞれ異なる制御です。Grafana service account は Grafana HTTP API の ID です。ADMIN service account を作成しても、AMP データソースが作成されたり、aps:QueryMetrics の権限が付与されたりすることはありません。メトリクスを表示するだけの目的で、広範な API ID を用意しないでください。

AMG 12 以降では、Amazon Managed Service for Prometheus データソース plugin を選択します。この AMG バージョンでは、Core Prometheus plugin から SigV4 サポートが削除され、既存の AMP データソースは AMP plugin に移行します。workspace の実際のバージョンに対応したドキュメントを使用してください。承認済みの workspace 設定で、対象のアカウント／Region／workspace を選び、クエリ用の ID を設定して既知の series をテストします。文書化された AWS データソースの設定フローでは、service-managed permission を使用します。customer-managed workspace には、独自にレビューした IAM 設定が必要であり、所有権が自動的に変更されるわけではありません。

クエリ role には通常、workspace にスコープされた aps:QueryMetrics、aps:GetSeries、aps:GetLabels、aps:GetMetricMetadata が必要です。discovery やその他の有効化した機能には、追加の action が必要な場合があります。クエリ endpoint は remote_write の取り込み URL ではありません。別途 workspace をプロビジョニングする場合、CLI では --workspace-name を使い、--account-access-type、認証、permission の設定も必要です。service-managed IAM の自動化は、文書化されたコンソールのワークフローに結び付いています。workspace を利用可能とみなす前に、ID、ユーザー割り当て、ネットワークアクセスを設定してください。

参考資料: [AMP remote write](https://docs.aws.amazon.com/prometheus/latest/userguide/AMP-onboard-ingest-metrics-existing-Prometheus.html)、[AMG AMP plugin](https://docs.aws.amazon.com/grafana/latest/userguide/amazon-prometheus-data-source.html)、[AWS データソースの設定](https://docs.aws.amazon.com/grafana/latest/userguide/amazon-AMP-adding-AWS-config.html)。この監査では workspace、認証フロー、テレメトリの取り込みを実行していません。

#### セルフマネージド Prometheus と Grafana

この例では、ServiceMonitor と PrometheusRule の例に必要な Prometheus Operator を含む、管理下の kube-prometheus-stack release を1つ使用します。スタンドアロンの Prometheus chart では、これらの CRD／controller は自動的に提供されません。インストール前に既存の Operator、release、CRD の所有権を確認してください。既存の stack がある場合は、管理者のアップグレード手順に従います。

レビュー済みのベースラインは chart 92.9.0 / Operator 0.94.1 で、EKS 1.36 向けにレンダリングされています。標準の Linux EC2 node と、EBS CSI の権限が適切に設定された暗号化済み ebs-gp3 StorageClass を前提とします。Auto Mode や別のストレージ実装では、実際にサポートされている class とノード配置を選択してください。以下の保持期間と PVC サイズは配分例であり、測定された容量保証ではありません。

monitoring namespace と、承認済みの Secret 管理プロセスで用意した `admin-user`／`admin-password` key を含む Secret grafana-admin を準備します。values では Secret を参照し、共有パスワードを Helm values やコマンド引数に記述しません。次の内容を monitoring-values.yaml として保存します。

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

Grafana の dashboard／data-source sidecar が監視するのは、namespaced role を使う monitoring namespace のみです。Grafana の ClusterIP Service には port-forwarding でローカルからアクセスします。単一 replica の PVC の例では、rollout 時の書き込みの重なりを避けるために Recreate を使用します。置き換え時に UI が停止するため、停止時間を計画してください。これは高可用性 Grafana の設計ではありません。

chart のデフォルトでは kubelet server certificate の検証が省略されます。この values では、ca.crt に信頼できる kubelet serving CA chain を含む、事前作成済みの monitoring/kubelet-serving-ca ConfigMap と、scrape 対象 endpoint に一致する SAN を持つ証明書が必要です。ノード管理者の証明書管理プロセスを通じて、その信頼性を確認してください。EKS API-server CA が kubelet serving CA になるとは限りません。この前提条件を満たせない場合は、収集を有効にする前に証明書設定を解決してください。target を健全に見せるために insecureSkipVerify を黙って元に戻さないでください。この監査では kubelet TLS handshake をテストしていません。

この例では、etcd／controller-manager／scheduler／kube-proxy の scrape job は無効です。セットアップで、これらの直接 endpoint を提供していないためです。実際に到達可能で、アクセスを許可された endpoint を設定した後にのみ job を有効にしてください。API-server や CloudWatch のメトリクスは別個のソースであり、component の ServiceMonitor target がない状態を解決するものではありません。

新しく管理下の release を作成する場合:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update prometheus-community
helm install monitoring prometheus-community/kube-prometheus-stack \
  --version 92.9.0 --namespace monitoring --create-namespace \
  -f monitoring-values.yaml --wait --timeout 10m
```

Helm の wait は、Operator が作成したすべてのリソース、target、通知 route が動作する証拠ではありません。生成されたリソース、PVC の bind 状態、Prometheus の target health、メトリクスデータを確認してください。

```bash
kubectl get pods,svc,pvc -n monitoring
kubectl get prometheus,alertmanager -n monitoring
```

次のコマンドを実行している間に、承認済み Secret ストアの認証情報を使い、Grafana に `http://127.0.0.1:3000` でアクセスします。

```bash
kubectl port-forward --address 127.0.0.1 -n monitoring \
  svc/monitoring-grafana 3000:80
```

Grafana の database／PVC とエクスポートした dashboard definition を保護してください。Grafana のサポート対象の認証情報ローテーション手順を使用します。初期設定用 Secret を変更しただけでは、既存の database user のパスワードが変わったことは証明されません。共有サンプルパスワードを使って UI を公開しないでください。

chart のレンダリング結果では、実際の Prometheus service が monitoring-kube-prometheus-prometheus、Grafana service が monitoring-grafana、data-source UID が prometheus であることを確認しています。カスタム ServiceMonitor／PrometheusRule は、この release が使用する release=monitoring selector に一致させる必要があります。レンダリングされた manifest と schema の確認はローカルでの証拠です。実際のクラスターで stack、PVC、ログインを試してはいません。

参考資料: [kube-prometheus-stack chart とアップグレードのガイダンス](https://github.com/prometheus-community/helm-charts/tree/kube-prometheus-stack-92.9.0/charts/kube-prometheus-stack)。

#### 主な Prometheus メトリクス

メトリクスが利用できるかどうかは、dashboard 名だけでなく、実際の scrape target と権限によって決まります。

- Node exporter は、サポート対象のノードで CPU、memory、filesystem、network の series を提供します。
- Kubelet/cAdvisor はコンテナのリソースメトリクスを提供し、kube-state-metrics は再起動や readiness などの Kubernetes object の状態を提供します。
- API server は認可された API メトリクスを公開します。etcd/controller-manager/scheduler の直接メトリクスには、それぞれ到達可能な endpoint が必要です。上記のセットアップでは、これらの target を有効にしていません。

series が見つからない場合、exporter の未導入、scrape の失敗、未サポートのプラットフォーム、メトリクスの変更などが考えられます。使用量がゼロである、またはシステムが健全であるとは限りません。

#### Grafana の便利な dashboard

レビュー済みの kube-prometheus-stack release にバンドルされた Kubernetes、node-exporter、API-server の dashboard から始め、prometheus data-source UID を選択してください。community dashboard の ID があるだけでは、メトリクス／label の互換性は保証されません。インポートした各 dashboard の query、単位、必要な recording rule、data-source 参照を確認してください。データのない graph は、監視対象の component が健全である証拠ではありません。

以前に記載されていた community ID は現在も存在しますが、いくつかはタイトルや想定されている用途が正確ではありませんでした。catalog で確認した参照先は次のとおりです。インポート時／実行時の互換性はテストしていません。

| ID | catalog 上の正式タイトル | 対象範囲の注記 |
| --- | --- | --- |
| [15661](https://grafana.com/grafana/dashboards/15661-k8s-dashboard-en-20250125/) | K8S Dashboard | K8S リソースの全般的な概要 |
| [1860](https://grafana.com/grafana/dashboards/1860-node-exporter-full/) | Node Exporter Full | 対応する node-exporter series が必要 |
| [6417](https://grafana.com/grafana/dashboards/6417-kubernetes-cluster-prometheus/) | Kubernetes Cluster (Prometheus) | クラスター／コンテナの概要。catalog の最終更新は2018年 |
| [12006](https://grafana.com/grafana/dashboards/12006-kubernetes-apiserver/) | Kubernetes apiserver | API-server latency/cache dashboard。catalog の最終更新は2020年 |
| [13770](https://grafana.com/grafana/dashboards/13770-1-kubernetes-all-in-one-cluster-monitoring-kr/) | 1 Kubernetes All-in-one Cluster Monitoring KR | 韓国語のオールインワン dashboard。書籍の VM 環境に最適化 |

#### PromQL クエリの例

これらの例は、レビュー済み stack の job と metrics_path label に対応しています。特に AMP workspace を共有する場合は、Pod の namespace ID と、存在する場合の cluster label を保持してください。Prometheus external label は外部へのデータ送信時に付与されますが、ローカルに保存されたすべての series に自動的に付くわけではありません。max 集約は同じ識別対象に対する重複観測をまとめるものであり、異なるワークロードをまとめるものではありません。このパターンを応用する前に、label を確認してください。

node CPU の non-idle percentage（CPU 全体の平均）:

```promql
100 * (1 - avg by (cluster, instance) (max by (cluster, instance, cpu) (rate(node_cpu_seconds_total{job="node-exporter",mode="idle"}[5m]))))
```

container の memory working-set byte が多い上位10 Pod:

```promql
topk(10, sum by (cluster, namespace, pod) (max by (cluster, namespace, pod, container) (container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD"})))
```

Pod UID ごとの現在の再起動カウンター。これは CrashLoopBackOff の検出器ではありません。

```promql
sum by (cluster, namespace, pod, uid) (max by (cluster, namespace, pod, uid, container) (kube_pod_container_status_restarts_total{job="kube-state-metrics"}))
```

root filesystem の空き容量不足率。サイズがゼロの filesystem は除外されます。

```promql
(100 * (1 - max by (cluster, instance, device, mountpoint, fstype) (node_filesystem_avail_bytes{job="node-exporter",mountpoint="/"}) / max by (cluster, instance, device, mountpoint, fstype) (node_filesystem_size_bytes{job="node-exporter",mountpoint="/"}))) and on (cluster, instance, device, mountpoint, fstype) (max by (cluster, instance, device, mountpoint, fstype) (node_filesystem_size_bytes{job="node-exporter",mountpoint="/"}) > 0)
```

ここでの CPU percentage は non-idle 時間を表し、memory は byte 単位で測定され、restart は現在の Pod/container のライフタイムに対するカウンターです。カウンターの変化を確認する場合は、選択した期間に対して rate/increase を使用します。filesystem の計算には使用可能な空き容量を使うため、一般ユーザーが利用できない予約領域が含まれることがあります。これらは調査用の例であり、普遍的なアラートしきい値ではありません。

### AWS X-Ray による分散トレーシング

X-Ray は引き続きサポート対象の trace backend です。SDK と daemon は2026年2月25日にセキュリティ修正のみの保守段階に入りました。現行の AWS の予定では、この段階の終了日は公表されていません。新しい計装には、サポートされている OpenTelemetry／ADOT 統合を使用してください。X-Ray daemon や collector が trace を送信するために Kubernetes の cluster-admin 権限を必要とするわけではなく、その Kubernetes role に AWS の書き込み権限が付与されるわけでもありません。

#### コレクターの管理主体と前提条件

計装／収集を管理する主体を1つ選択してください。上記の CloudWatch add-on の Application Signals 経路も代替手段です。重複 span や競合を確認せずに、すでに計装されたプロセスへ別の SDK agent を追加しないでください。以下の明示的な例では OpenTelemetry Operator 0.158.0 と ADOT Collector 0.50.0 を使い、trace のみの pipeline を構成します。

コレクターを適用する前に、各管理者を通じて次の依存関係を準備します。

- 一致する CRD／webhook を備えた、動作中の Operator。upstream の公開 manifest では cert-manager を使用します。文書化されたインストール／アップグレード手順に従ってください。EKS ADOT add-on も別の管理経路であり、build 固有の schema を使用します。Collector release には Operator のインストール manifest は含まれません。
- 専用の tracing-demo namespace と、準備済み IRSA trust を持つ ServiceAccount adot-traces。このクラスター用に、`sub=system:serviceaccount:tracing-demo:adot-traces` と `aud=sts.amazonaws.com` を設定します。この pipeline で必要な X-Ray 書き込み action（PutTraceSegments）を許可し、STS/X-Ray への接続を用意してください。この OTLP 専用 collector は Kubernetes object を検出せず、クラスター全体の RBAC も必要としません。
- `tls.crt`／`tls.key` を含み、`adot-traces-collector.tracing-demo.svc` に有効な server certificate を備えた Secret tracing-demo/otel-receiver-tls。信頼できる CA をアプリケーションに mount してください。証明書の発行、更新、collector の reload/restart は運用上の責任範囲です。
- NetworkPolicy を適用する CNI と、レビュー済みのアプリケーション egress。この例では app=my-app という label が付いた default Pod からの ingress を許可します。適用対象は、専用の tracing-demo namespace 内のすべての Pod です。label は通信を選択するものであり、ワークロードを認証したり、Pod を作成する権限に対する RBAC 制御の代わりになったりするものではありません。

Collector の URL を Operator manifest として適用せず、公開されている [Operator release](https://github.com/open-telemetry/opentelemetry-operator/releases/tag/v0.158.0) と [ADOT release](https://github.com/aws-observability/aws-otel-collector/releases/tag/v0.50.0) を確認してください。v1beta1 CRD では spec.config は object 型です。例の Region は env/exporter の両方で同時に変更します。

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

Operator は OTLP/HTTP port から ClusterIP receiver Service を導出します。Service 名は tracing-demo 内の adot-traces-collector、protocol は TCP 4318 です。この receiver はユーザー ID も業務上の認可情報も検証しません。この例では server TLS と選択したネットワーク境界を使用します。より強力な分離には mTLS またはサポート対象の receiver authenticator が必要です。アクセス範囲を広げる前に、両端で一貫するように設定してください。

Collector の受信は、保存の確認ではありません。生成された Deployment／Service、TLS handshake、AWS 認証情報の選択、exporter の失敗、X-Ray 内の既知の trace を確認してください。replica 1台のインメモリの例は、欠損のない配信や高可用性を実現する pipeline ではありません。ワークロードに合わせて buffer、backpressure、再試行動作、障害処理を規模設定してテストしてください。CRD schema の検証だけでは、すべての component 設定や collector の起動は検証できません。

#### アプリケーションの計装とコンテキスト伝播

Python 3.10 以降のアプリケーションでは、アプリケーションの依存関係 lock 内で opentelemetry-sdk==1.44.0 と opentelemetry-exporter-otlp-proto-http==1.44.0 のバージョンをそろえます。各 service を個別に設定してください。共有 collector が、受信するすべての service.name を単一のグローバル値で上書きしてはいけません。HTTP exporter の endpoint には /v1/traces を含めます。4317 の gRPC endpoint は別の protocol／設定です。

```bash
export OTEL_SERVICE_NAME=my-app
export CLUSTER_NAME=my-owned-cluster
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://adot-traces-collector.tracing-demo.svc:4318/v1/traces
export OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE=/etc/otel/ca.crt
```

CA ファイルはアプリケーションコンテナに mount する必要があります。アプリケーション起動時に RequestTracing instance を1つ作成し、実際のサーバーハンドラーから正規化した受信 header 名とともに handle_request を呼び出してください。渡された送信 header を使用する operation を実行し、graceful shutdown 時に close を呼び出します。framework／client の自動計装でこれらの境界を処理することもできます。同じ operation を二重に計装しないでください。

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

この adapter は W3C tracecontext の伝播と1つの server span を示すものであり、HTTP server やすべての client span を実装するものではありません。X-Amzn-Trace-Id を使う AWS edge 統合では、W3C 専用の抽出でこの header を読み取れると仮定せず、サポートされている propagator／bridge を使用してください。head sampling の10%は、新しい root に対する例であり、parent の判断は保持されます。後で発生するすべての error や遅いリクエストの保持を保証するものではありません。tail sampling には、trace のすべての span を同じ場所へ振り分け、十分なバッファを備えた別の設計が必要です。

#### Trace map と調査

アカウントで利用できる X-Ray／CloudWatch の tracing view で、trace map、latency distribution、error／fault の詳細を確認してください。map に表示されるのは、計装され、sampling され、配信に成功した span です。edge が表示されないからといって、service 間の通信がないとは限りません。適切な保持期間を設定したログやメトリクスと trace ID を関連付けてください。認証情報、個人情報、上限のない request attribute は除外します。

この監査で検証したのは、公開 API／schema と合成したローカル動作のみです。デプロイ済み collector、稼働中の計装、trace のエクスポート、本番容量のテストは確認していません。参考資料: [X-Ray の保守期間](https://aws.amazon.com/blogs/mt/aws-x-ray-sdks-daemon-migration-to-opentelemetry/)、[EKS ADOT の管理](https://docs.aws.amazon.com/eks/latest/userguide/opentelemetry.html)、[AWS X-Ray exporter](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.158.0/exporter/awsxrayexporter)。

### Kubernetes Dashboard

[Kubernetes Dashboard プロジェクト](https://github.com/kubernetes-retired/dashboard)はアーカイブされ、保守も終了しています。保守担当者は、現在の UI のニーズには Kubernetes SIG UI の Headlamp を推奨しています。古い Dashboard v2.7 の raw-manifest と cluster-admin-token の手順を、現在のインストール方法として使用しないでください。

保守されている UI を選び、実際の認証、TLS、認可、アップグレードの要件を確認してください。セキュリティの章の access-entry／RBAC の例に従い、意図した IAM/RBAC ID と namespace scope を使用します。UI にデフォルトユーザーとして無制限の cluster-admin ServiceAccount を使う必要はありません。管理者 bearer token の公開は、アクセス設計の代わりにはなりません。

### カスタムメトリクスとモニタリング

アプリケーション固有のメトリクスを収集してモニタリングするために、カスタムソリューションを実装できます。

#### Prometheus Client Library の統合

Prometheus Java client 1.8.0 API では、現行の io.prometheus.metrics package とバージョンをそろえた依存関係を使用します。既存の Gradle Java project では、次のように設定します。

```groovy
dependencies {
    implementation(platform("io.prometheus:prometheus-metrics-bom:1.8.0"))
    implementation("io.prometheus:prometheus-metrics-core")
    implementation("io.prometheus:prometheus-metrics-exporter-httpserver")
}
```

次の例を App.java として保存します。main method は port 9400 でメトリクスを公開して待機します。実際のアプリケーションの request handler から、operation とともに processRequest を呼び出す必要があります。メトリクス endpoint を起動しただけでは、業務上のリクエスト件数はカウントされません。測定値としての合成リクエスト数は提示していません。

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

source API と依存関係の座標は、公開 client に照らして確認しました。この監査環境では Java compiler/runtime を利用できなかったため、例をコンパイル／実行していません。デプロイ前にアプリケーションの build、ライフサイクル、request path に統合してください。label の値は限定してください。request ID、user ID、生の URL は、デフォルトのメトリクス dimension には適しません。

#### カスタムメトリクスの収集

管理対象のアプリケーション Pod が default namespace にあり、app=my-app の label を持ち、TCP 9400 で実際に /metrics を提供しているものとします。Service は Pod を選択します。ServiceMonitor は Service の label と名前付き port を選択します。release=monitoring label と namespaceSelector により、上記の stack に接続します。

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

Service の EndpointSlice と Prometheus の target status を確認し、適用されるネットワークポリシー／セキュリティ制御で、意図した collector だけがアクセスできるようにしてください。このクラスター内 HTTP metrics の例には、レビュー済みのネットワーク境界が必要です。メトリクス endpoint が必要とする場合は、TLS／認証を設定してください。ServiceMonitor はアプリケーションを計装せず、存在しないメトリクスサーバーを作成することもありません。

参考資料: [Java client クイックスタート](https://prometheus.github.io/client_java/getting-started/quickstart/)、[Prometheus の設定](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)。

#### カスタム dashboard

Grafana でカスタム dashboard を作成して、アプリケーションのメトリクスを可視化します。

1. Grafana にログインします
2. 「+」アイコンをクリックし、「Dashboard」を選択します
3. 「Add panel」をクリックします
4. データソースとして「Prometheus」を選択します
5. PromQL クエリを記述します（例: `rate(app_requests_total[5m])`）
6. panel のタイトル、説明、可視化の種類を設定します
7. 「Save」をクリックします

## アラートとイベント管理

EKS クラスターの問題を迅速に検出し対応するには、効果的なアラートとイベント管理が不可欠です。このセクションでは、EKS クラスターのアラートやイベントを管理するためのさまざまなツールと手法を紹介します。

![Architecture diagram showing CloudWatch metrics and logs, AWS events, Prometheus metrics and Loki logs, and Kubernetes and application events routed through CloudWatch Alarms, EventBridge, Prometheus Alertmanager, and an event router to SNS (Email and SQS subscriptions), Lambda, Slack and PagerDuty, and OpsGenie.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-3.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-3.html)

### CloudWatch Alarms

アラームを作成する前に、直近の datapoint と正確なメトリクス namespace、name、dimension 一式を確認してください。この例では、文書化された ClusterName のみを使う ContainerInsights node aggregate と Maximum を使用しています。ノードの hotspot を検出できますが、クラスター全体の容量加重 utilization を測定するものではありません。影響を受けているノードを特定するには、ノード固有の dimension を使います。

80/80/85% というしきい値と、2回の5分間の評価期間は、ポリシーの例です。2つの期間で Maximum がしきい値を超えても、10分間の全秒数で飽和が続いたことを意味するわけではありません。データが欠落している場合は、健全な utilization の証拠ではなく、欠落したままです。PutMetricAlarm は既存アラームを更新するため、名前を再利用する前にアラーム定義を確認してください。通知の権限、subscription、配信テストは別途必要です。

#### Node CPU

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

#### Node Memory

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

#### Node Filesystem

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

これらのアラームコマンドは AWS に対して実行していません。参考資料: [Container Insights のメトリクスと dimension](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html)。

### Prometheus Alertmanager

Prometheus はアラートルールを評価し、Alertmanager は結果のアラートをグループ化、重複排除、ルーティングします。任意の名前の ConfigMap を作成しても、Operator が管理する Alertmanager に自動的に読み込まれるわけではありません。レビュー済み stack では Alertmanager 0.34.0 を使用しています。設定と認証情報ファイルを明示的に接続してください。

#### Alertmanager の設定

Slack の例では、承認済み Secret 管理プロセスを通じて monitoring/notification-credentials を準備し、実際の webhook URL を含む slack-url key を用意します。認証情報を ConfigMap、repository のテキスト、Helm のコマンド引数に保存しないでください。認証情報を含まない次の routing 定義を alertmanager-config.yaml として保存します。

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

webhook は意図した Slack の宛先への送信を許可されている必要があります。channel field を設定しても、Slack app の権限が上書きされるわけではありません。この例では、Slack に定期的なメッセージが送られないよう、常に発火するバンドル済みの Watchdog alert を破棄します。実際の dead-man／heartbeat 監視には、別の receiver と外部からの不在検出が必要です。Watchdog を破棄しても、アラート配信はテストされません。

一致するバージョンの amtool でファイルをローカルに検証し、新規に管理下のインストールを行う場合のみ設定 Secret を作成してください。既存の Secret／release がある場合は、管理者のレビュー済み更新手順が必要です。

```bash
amtool --no-version-check check-config alertmanager-config.yaml
kubectl create secret generic alertmanager-routing -n monitoring \
  --from-file=alertmanager.yaml=alertmanager-config.yaml
```

次の内容を alertmanager-values.yaml として保存し、monitoring release のレビュー済み values 一式と組み合わせます。configSecret で Secret を選択し、Operator は `alertmanager.yaml` key を使用します。secrets は notification-credentials を `/etc/alertmanager/secrets/notification-credentials` に mount します。デプロイ前に、monitoring 内で release=monitoring に選択される追加の AlertmanagerConfig resource を確認してください。

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

生成された設定／reload status と通知失敗を確認し、paging を信頼する前に、承認済みのテスト宛先を通じて label 付きのテスト alert を送信してください。ローカルの parse と route のテストだけでは、Secret の利用可能性、webhook の権限、SMTP の接続性、実際の配信は証明されません。chart の replica 1台の例には、別途可用性設計も必要です。

#### アラートルールの設定

rule の release label は Prometheus selector に一致します。アラートの重複を避けるため、同等のバンドル済み rule がないか確認してください。CrashLoopBackOff は Kubernetes の waiting reason です。restart rate のしきい値だけでは、その condition が発生したとは判断できません。以下の例では、指定した kube-state-metrics series と namespace／Pod UID／container または node ID が必要です。

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

CrashLoopBackOff rule は、直近5分間の複数回の窓を調べます。restart 数を数えるものではありません。ノードの pressure は観測された kubelet condition であり、一般的な utilization percentage とは異なります。series の欠落／stale 化によってアラートが抑制されることがあるため、scrape health とメトリクスの利用可能性も別途監視してください。しきい値と保留時間は例であり、インシデント対応を保証するものではありません。

### EventBridge Event rule

イベントを発行する service が公開している event 名と payload field を使用します。EKS の直接イベント catalog には、add-on の作成／更新／削除の結果、add-on の health degraded/restored event、Fargate の終了予定イベントが含まれます。古い例で使用されていた汎用の EKS Cluster State Change や EKS Node Group State Change という名前は公開されていません。CloudTrail 経由で配信される EKS API activity は、異なる detail-type と payload を使用します。

#### 直接発行される add-on health event と CloudTrail API activity

次のコマンドは、選択したアカウントと Region にスコープした2つの代替パターンを作成します。対象は、そのアカウント／Region 内で一致する activity であり、単一クラスターではありません。rule をさらに絞り込む場合は、該当する event type のイベントを記録し、その文書化された field をテストしてください。すべてのイベントに `detail.clusterName` が含まれるとは限りません。

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

CloudTrail pattern は、該当する upgrade／rollback リクエストを含め、UpdateClusterVersion と UpdateNodegroupVersion の API event に一致します。API call event が記録するのは、リクエストの試行または受け付けであり、非同期 update の完了ではありません。error field を確認し、成功したリクエストを update ID および DescribeUpdate status と照合してください。関連する CloudTrail management event の配信が設定されていることも確認します。直接配信と CloudTrail 経由の配信はいずれもベストエフォートです。service の状態確認と障害監視も行ってください。

#### 管理下の SNS target を接続する

標準 SNS topic、その確認済み subscription、同じアカウント／Region 内の EventBridge target 実行 role を準備します。role は EventBridge を trust し、対象 topic に対する sns:Publish と、暗号化に必要な該当 KMS 権限を持つ必要があります。運用担当者には対応する rule／target 権限と、承認済み role を渡す権限が必要です。現在の EventBridge は SNS target に実行 role を使用できます。resource-based policy は代替手段であり、target を追加すると自動で設定されるものではありません。

生成済みの pattern file を1つ選び、新たに管理する rule 名を指定します。事前確認では既存名を拒否しますが、PutRule は upsert のため、所有権と並行変更を調整してください。rule は無効状態で作成され、PutTargets が一部失敗した場合はワークフローを中断します。

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

target の完全な response、role、subscription、配信の再試行／dead-letter policy、代表的な event を確認してください。TestEventPattern で pattern の一致を検証できますが、target の権限や配信をテストするものではありません。レビュー後にのみ有効化してください。

```bash
aws events enable-rule --region "$AWS_REGION" --event-bus-name default --name "$RULE_NAME"
```

有効化後は、一致／失敗した invocation を監視し、承認済みのエンドツーエンド event を確認してください。rule、target、API response の成功だけでは、アラート配信は保証されません。この監査では EventBridge／SNS の resource、event、notification を作成していません。

参考資料: [EKS EventBridge event catalog](https://docs.aws.amazon.com/eventbridge/latest/ref/events-ref-eks.html)、[target の権限](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-resource-based.html)。

### Kubernetes Event のモニタリング

Kubernetes Event は、スケジューリング、イメージの pull、再起動、その他の object activity を調査する際に役立ちます。保持期間の短いベストエフォートの記録であり、繰り返された発生を集約することもあります。完全で永続的な監査証跡ではありません。まず対象の namespace を確認してください。

```bash
kubectl events -n default --types=Warning
kubectl events -n default --types=Warning --watch
```

#### Collector のバージョンと管理主体

元の Opsgenie exporter は保守されていません。稼働中の fork は resmoio から mustafaakin/kubernetes-event-exporter に移転しました。ここで確認した最新の公開 release は2024年2月の v1.7 ですが、repository ではその後も開発が続いています。repository が稼働中であることや、latest tag が古いことだけでは、本番用 image に現在の security patch が適用されている証拠にはなりません。

次の参照例は v1.7 の設定／watcher source に照らして確認しました。この設定／CLI の契約を維持する、管理下でビルドし、レビューして patch を適用した image が必要です。UID 65532 で実行し、read-only root filesystem で mount した設定を読み取れる必要があります。rendering 時に不変の digest を設定します。public latest image や、根拠のない digest は提示していません。この監査では image build、脆弱性レビュー、実行時の互換性テストは実施していません。

#### Namespace scope、RBAC、設定

この例では既存の monitoring namespace で実行し、default 内の core/v1 Event のみを監視します。omitLookup=true は、関連 object の label／annotation を補完するための別個の GET request を無効にします。そのため Role に付与するのは default 内の event の読み取り権限のみです。Secret やすべての API resource に対するワイルドカードの読み取り権限は与えません。単一 replica では leader election を無効にするため、lease の書き込み権限は付与されません。scope を変更するときは、namespace、Role、RoleBinding の範囲を一致させてください。

次の内容を event-exporter-template.yaml として保存します。image marker を含んでいるため、使用前に rendering が必要です。match rule は名前付き receiver を指定します。その receiver は JSON を stdout に出力し、既存の管理下のコンテナログ pipeline で収集できます。この設定は Warning event のみをエクスポートします。

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

rendering には Python 3 と PyYAML が必要です。既存の event-exporter resource とその所有者を最初に確認してください。既存インストールがある場合は、管理者のアップグレード手順に従います。

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

新しく管理下のインストールを行う場合は、レンダリング済みの manifest、image-pull ID、API 接続性を確認してから適用してください。Recreate は rollout 時に replica が重複するのを防ぎますが、停止時間が発生します。高可用性 collector ではありません。

```bash
kubectl apply -f event-exporter-rendered.yaml
kubectl rollout status deployment/event-exporter -n monitoring --timeout=120s
kubectl logs -n monitoring deployment/event-exporter --tail=100
```

#### 欠損、繰り返しイベント、アラートの payload

確認した v1.7 watcher は add notification を処理し、update/delete callback を無視します。そのため、Event の繰り返し count／series update は、エクスポートされた発生件数の信頼できるカウンターにはなりません。maxEventAgeSeconds=60 は受け付ける event の期限の例であり、バックエンドの保持期間ではありません。起動、throttling、停止中に古い event が破棄される可能性があります。再度の list／restart で記録が重複することもあります。運用上の判断に event 件数を使用する前に、必要な update 処理、buffer、永続的な宛先を選択してテストしてください。

watch／discard counter とログも確認してください。この例では exporter の metrics listener を loopback に bind します。認可された運用者はローカル port-forward 経由で確認できます。endpoint が Prometheus に自動追加されるわけではありません。

```bash
kubectl port-forward --address 127.0.0.1 -n monitoring \
  deployment/event-exporter 2112:2112
```

forwarding 中に `http://127.0.0.1:2112/metrics` で /metrics を読み取ります。rollout や stdout のレコードだけでは、CloudWatch／OpenSearch に保存されたことは確認できません。既存のログ collector と意図した宛先を検証してください。Event message には機微な運用情報が含まれることがあるため、アクセス、filtering、保持期間を確認してください。

raw Kubernetes Event object を送信するには、webhook URL だけを変更して Alertmanager に送信してはいけません。現行の Alertmanager `/api/v2/alerts` endpoint は、その alert-array schema を期待します。古い `/api/v1/alerts` path は現行 API ではありません。意図的な adapter で、ID、label、annotation、解除の意味を変換する必要があります。上記の stdout／log 経路は、そのような adapter を実装しているかのようには扱いません。

参考資料: [保守されている exporter repository](https://github.com/mustafaakin/kubernetes-event-exporter)、[v1.7 watcher](https://github.com/mustafaakin/kubernetes-event-exporter/blob/v1.7/pkg/kube/watcher.go)、[Alertmanager v2 API](https://github.com/prometheus/alertmanager/blob/v0.34.0/api/v2/openapi.yaml)。

### 通知チャネルの統合

実際の Alertmanager バージョンでサポートされている receiver を使用してください。以下の断片は alertmanager-config.yaml 内の receivers エントリであり、Kubernetes resource ではありません。使用する場合は receiver を追加し、route.receiver または一致する child route をその正確な名前に変更してから、完全な設定を検証し、選択した Secret を更新してください。未使用の receiver entry を追加しただけではアラートはルーティングされません。

#### Slack の統合

上記の配線済み Slack の例では、mount した webhook file を使用します。許可された channel を確認し、アラートの label／annotation 全体を送る前に、機微情報が含まれないか確認してください。repository に commit する Provider／ConfigMap の例へ、実際の Slack token や webhook を決して記述しないでください。

#### PagerDuty の統合

Events API v2 integration を使用する場合は、notification-credentials に pagerduty-routing-key key を準備します。routing_key_file が参照するのは integration key であり、一般的な PagerDuty REST API token ではありません。critical alert のみを pager に送る場合は、レビュー済みの child route を通じて critical alert を接続します。

```yaml
name: pagerduty-notifications
pagerduty_configs:
- routing_key_file: /etc/alertmanager/secrets/notification-credentials/pagerduty-routing-key
  send_resolved: true
  severity: '{{ if eq .CommonLabels.severity "critical" }}critical{{ else }}warning{{ end }}'
  description: '{{ .CommonLabels.alertname }}'
```

#### メールの統合

予約済みの SMTP host／address／user の例を、承認済みのメールサービス設定に置き換え、同じ認証情報 Secret に smtp-password を用意します。TLS を必須にし、サーバーの信頼性、送信元の認可、配信を確認してください。これは Alertmanager の email receiver であり、Flux Provider ではありません。

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

#### Amazon SNS native 統合

Alertmanager 0.34.0 には native SNS receiver があり、未定義の sns-forwarder webhook service は必要ありません。例の Region／account／topic を管理下の標準 topic に置き換えます。実際の Alertmanager ServiceAccount に対し、その topic への sns:Publish を許可するサポート対象の AWS ID と、暗号化 topic に該当する KMS 権限、ネットワーク接続を用意します。Prometheus またはアプリケーションの role が Alertmanager の role になるわけではありません。静的な AWS access key はここに埋め込みません。

```yaml
name: sns-notifications
sns_configs:
- sigv4:
    region: us-west-2
  topic_arn: arn:aws:sns:us-west-2:123456789012:eks-alerts
  send_resolved: true
  subject: 'EKS {{ .CommonLabels.alertname }}'
```

topic subscription と宛先の policy を確認し、別途配信をテストしてください。FIFO topic には deduplication/grouping に関する追加の考慮事項があります。この設定断片の対象は標準 topic です。receiver を parse しても、IAM や SNS publishing は実行されません。

Flux notification Provider は Flux Alert resource および選択された event source とともに、Flux reconciliation event をルーティングします。存在するだけで、任意の Prometheus alert や Kubernetes Event を受信するものではありません。このワークフローは、ここに示した Alertmanager receiver 設定とは分けてください。

参考資料: [Alertmanager の設定と receiver](https://prometheus.io/docs/alerting/latest/configuration/)。

### アラートの管理とエスカレーション

アラートを効果的に管理し、エスカレーションするための戦略を実装します。

#### アラートの深刻度レベル

アラートを次の深刻度レベルに分類します。

- **Critical**: 直ちに対応が必要な重大な問題
- **Warning**: 注意が必要だが、直ちに対応する必要はない問題
- **Info**: 情報を伝えるアラート

#### アラートエスカレーションポリシー

PagerDuty などのツールを使用して、アラートエスカレーションポリシーを実装します。

1. **最初の応答**: オンコールエンジニアにアラートを送信します
2. **エスカレーション 1**: 15分後も応答がなければ、バックアップエンジニアにアラートを送信します
3. **エスカレーション 2**: 30分後も応答がなければ、チームリードにアラートを送信します
4. **エスカレーション 3**: 45分後も応答がなければ、マネージャーにアラートを送信します

#### アラート疲れの軽減

アラート疲れを軽減するための戦略を実装します。

1. **アラートのグループ化**: 関連するアラートをまとめて、重複した通知を減らします
2. **アラートのフィルタリング**: 重要なアラートだけが配信されるように絞り込みます
3. **アラートの抑制**: 繰り返されるアラートの頻度を制限します
4. **アラートの時間帯**: 業務に重大な影響のないアラートは、営業時間内のみ配信します

## ログの分析と可視化

ログの分析と可視化は、EKS クラスターで発生する問題の診断と解決に重要な役割を果たします。このセクションでは、EKS クラスターのログを分析し可視化するためのさまざまなツールと手法を紹介します。

![Architecture diagram of the log analysis and visualization pipeline: control plane and AWS service logs go directly to CloudWatch Logs, container and application logs pass through log collectors (Fluent Bit, Fluentd, Vector, CloudWatch Agent) into four stores (CloudWatch Logs, Amazon OpenSearch, Amazon S3, Grafana Loki), and each store feeds its paired analysis and visualization tool: CloudWatch Logs Insights, OpenSearch Dashboards, Athena with QuickSight, and Grafana Explore with dashboards.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-4.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-4.html)

### CloudWatch Logs Insights

クエリを実行する前に、実際の log group と期間の上限を決めてください。コンテナ、API／audit、authenticator の stream では schema が異なります。上記のスタンドアロン Fluent Bit の values では、解析されたアプリケーション JSON は data の下に、Kubernetes metadata は kubernetes の下に格納され、元の log field は保持されます。他の collector／設定では field path が異なることがあります。まず保存済み event を確認してください。

#### コンテナログのクエリ

文字列の level field を持つ構造化アプリケーションレコードの場合:

```
fields @timestamp, @log, kubernetes.pod_name, data.level, data.message, log
| filter kubernetes.namespace_name = "default"
| filter kubernetes.container_name = "app"
| filter toupper(data.level) = "ERROR"
| sort @timestamp desc
| limit 20
```

通常のテキストログや JSON parse に失敗したログには、data.level はありません。空の結果を「エラーなし」と解釈せず、別途 log field を確認してください。

#### 監査ログ内の API error response

監査ログが有効で、レコードに responseStatus が含まれる場合は、API-server のすべてのテキストから Error という単語を検索するのではなく、数値の response code を使用します。

```
fields @timestamp, verb, objectRef.resource, responseStatus.code, user.username
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code >= 400
| sort @timestamp desc
| limit 20
```

これは選択した監査 stream／期間内で記録された response を見つけるものであり、試行されたすべての API request を見つけるものではありません。4xx response は呼び出し側／認可の問題である可能性があり、コントロールプレーンの障害とは限りません。監査ポリシー、stage、取り込み、保持期間がカバレッジに影響します。

#### Authenticator event の確認

失敗 filter を追加する前に、現行の authenticator message 形式を確認してください。

```
fields @timestamp, @message
| filter @logStream like /authenticator/
| sort @timestamp desc
| limit 50
```

「authentication failed」という固定文字列では、実際の失敗を見逃したり、無関係なテキストに一致したりすることがあります。観測された message／status field を比較し、監査ログの 401/403 response と関連付けてください。認証と Kubernetes 認可は別のチェックです。どちらも、1つの stream だけでは完全な証拠になりません。

#### level ごとのログ件数

同じ構造化アプリケーション schema の場合:

```
fields toupper(data.level) as level, kubernetes.namespace_name
| filter ispresent(data.level)
| stats count(*) as log_records by @log, level, kubernetes.namespace_name
| sort log_records desc
```

これはログレコードの件数であり、固有のリクエスト数やエラー率ではありません。再試行、繰り返しメッセージ、collector による重複によって件数が変わることがあります。想定されるスペース区切り形式を前提にした parse では、任意の JSON／コンテナ／コントロールプレーンのログを確実に分類できません。

参考資料: [JSON field の検出](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_AnalyzeLogData-discoverable-fields.html)、[クエリ関数](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax-operations-functions.html)。

### Amazon OpenSearch Service

Amazon OpenSearch Service（旧 Amazon Elasticsearch Service）を使用すると、EKS クラスターのログを保存、分析、可視化できます。

#### 管理下の OpenSearch domain の準備

プラットフォーム管理者のレビュー済みプロビジョニング手順で準備した domain を使用します。ワークロードに適したサポート対象の engine／version、容量、保持ポリシーを選択してください。このロギングの例では、承認済みのネットワーク経路、HTTPS、保管時の暗号化、ノード間暗号化、きめ細かなアクセス制御（FGAC）を備えた VPC domain を使用します。collector を設定する前に、実際の domain を確認してください。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the owned domain Region}"
: "${OPENSEARCH_DOMAIN:?Set the owned domain name}"
aws opensearch describe-domain --region "$AWS_REGION" \
  --domain-name "$OPENSEARCH_DOMAIN" \
  --query 'DomainStatus.{ARN:ARN,Engine:EngineVersion,Endpoint:Endpoint,EndpointV2:EndpointV2,Endpoints:Endpoints,VPC:VPCOptions,HTTPS:DomainEndpointOptions.EnforceHTTPS,AtRest:EncryptionAtRestOptions.Enabled,NodeToNode:NodeToNodeEncryptionOptions.Enabled,FGAC:AdvancedSecurityOptions.Enabled}'
```

ネットワーク到達性、domain access policy、FGAC はそれぞれ別の層です。SigV4 collector ID は domain／IAM policy で許可され、権限を制限した OpenSearch ingestion role にマッピングされる必要があります。管理者権限と ingestion 権限を分けてください。internal user database 設定でも IAM ID をマッピングできます。同じ request で HTTP basic credential と SigV4 credential を組み合わせないでください。

承認済みの ID／Secret 管理経路で認証情報を提供します。共有の公開管理者パスワードやワイルドカードの public access policy は、適切なログ設定ではありません。既存の public domain を VPC に移行するには、新しい domain とデータ移行が必要です。これは既存 endpoint の設定を切り替えるだけではできません。既存の Terraform resource の type/address を変更する場合も、所有権／state の移行計画が必要です。

collector 設定では返された endpoint の hostname を使い、CA／hostname と認可された ingestion を検証してください。domain を調査しただけでは、ログの取り込みや本番運用への準備は確認できません。

参考資料: [OpenSearch FGAC](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/fgac.html)、[VPC domain と移行](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/vpc.html)。

#### Fluent Bit で OpenSearch にログを送信する

コンテナのロギングのセクションにある、配線済みの Fluent Bit values、RBAC post-renderer、OpenSearch overlay を使用します。実際に管理している endpoint、SigV4 権限、FGAC ingestion mapping を指定してください。無関係な fluent-bit-config ConfigMap を適用しても、別名の ConfigMap を mount している Helm release の設定は変わりません。

#### OpenSearch Dashboards でのログ可視化

OpenSearch Dashboards で次の可視化を作成します。

1. **Log Explorer**: ログ検索とフィルタリング
2. **Dashboards**: ログデータに基づく dashboard の作成
3. **Visualizations**: ログデータに基づく chart と graph の作成
4. **Alerts**: ログパターンに基づくアラートの設定

### Grafana Loki

Grafana Loki は Prometheus に似た label ベースの手法を使うログ集約システムです。

#### Loki のインストール

管理下のデプロイと Alloy などのサポート対象 client については、[現行の Loki セットアップガイド](../observability/logging/01-loki.md)を使用してください。非推奨の loki-stack/Promtail の組み合わせは、現在のインストール方法ではありません。本番ログを送信する前に、ストレージ、認証、label／保持ポリシーを設定してください。

#### LogQL クエリの例

これらの query は、collector が namespace／pod の stream label を作成し、application JSON をトップレベルの level field として保存することを前提としています。label と JSON の抽出形式が CloudWatch／Fluent Bit の data wrapper と自動的に同じになるわけではありません。

```logql
{namespace="default"} |= "ERROR"

{namespace="default", pod=~"app-.*"} | json | __error__=""

sum by (level) (
  count_over_time(
    {namespace="default"} | json | __error__="" | level=~"INFO|WARN|ERROR" [5m]
  )
)
```

JSON parser error の filter は、parse の後に置きます。メトリクスクエリでは pipeline error を除外します。filtering によって収集の問題が隠れないよう、拒否された／形式の不正なレコードも別途調査してください。例の level は大文字の構造化ログサンプルに対応しています。実際のデータに合わせて field／大小文字を調整してください。stream label の値は限定してください。request ID や user ID は、デフォルトの高 cardinality stream label ではなく、アクセスを制御したログフィールドに格納します。

#### Grafana dashboard の作成

Grafana で Loki data source を使用してログ dashboard を作成します。

1. Grafana にログインします
2. 「+」アイコンをクリックし、「Dashboard」を選択します
3. 「Add panel」をクリックします
4. データソースとして「Loki」を選択します
5. LogQL クエリを記述します
6. panel のタイトル、説明、可視化の種類を設定します
7. 「Save」をクリックします

### AWS CloudTrail

CloudTrail は、EKS クラスター／add-on／node group の管理など、サポート対象の AWS API activity を記録します。Kubernetes API の監査ログやアプリケーションの request log の代わりにはなりません。未準備の bucket に重複した trail を作成する前に、アカウントに既存の organization/account trail がないか確認してください。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the Region to inspect}"
aws cloudtrail describe-trails --region "$AWS_REGION" --include-shadow-trails \
  --query 'trailList[].{Name:Name,ARN:TrailARN,HomeRegion:HomeRegion,Organization:IsOrganizationTrail,MultiRegion:IsMultiRegionTrail}'
```

管理下の trail とその home Region を選択した後、次のコマンドを実行します。

```bash
set -euo pipefail
: "${TRAIL_ARN:?Choose the existing owned trail ARN}"
: "${TRAIL_HOME_REGION:?Use the home Region of the selected trail}"
aws cloudtrail get-trail-status --region "$TRAIL_HOME_REGION" --name "$TRAIL_ARN"
aws cloudtrail get-event-selectors --region "$TRAIL_HOME_REGION" --trail-name "$TRAIL_ARN"
```

ロギング／配信の error と event selector を確認してください。新しい trail には、個別にレビューした bucket／配信ポリシー、暗号化／key の権限、保持期間、所有権の設定が必要です。trail resource が存在するだけでは、ログが storage に届いたことは証明されません。trail の作成とロギングの開始は別の操作です。

#### 最近の management event

CloudTrail Event history は trail を作成しなくても利用でき、選択した Region の過去90日間の management event を対象とします。この読み取り専用の例では、直近1時間を照会し、表示する batch を50件までに制限します。

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

CLI が NextToken を返した場合は、同じ request／期間を使って --starting-token を指定し、残りを確認します。完全な ID／request／error field を確認するには、CloudTrailEvent の JSON 文字列を parse してください。Username だけでは呼び出し元を完全に特定できません。Event history は長期保持の計画ではなく、すべての data-event category を含むわけでもありません。

#### 対象となる既存顧客向け CloudTrail Lake

CloudTrail Lake は2026年5月31日に新規顧客の受付を終了し、現在は重大な bug／security 更新を受け取っています。既存顧客は文書化された条件のもとで引き続き利用できます。organization event data store は新しい member account を対象にできますが、既存の account-level store が新たに追加されたアカウントまで自動的に Lake への取り込み対象にするわけではありません。CloudTrail Trails、Insights、Aggregated Events は引き続きサポートされています。新しい分析設計では、新規 Lake 申し込みを前提とせず、AWS の現行 CloudWatch 移行／取り込みガイダンスを確認してください。

対象となる既存 store には、Lake query editor で選択した実際の ID に EVENT_DATA_STORE_ID を置き換えてください。eks_events のような任意の table alias ではありません。次のクエリは、元の例示値である2025年7月1日から11日までの期間を維持しています。この監査で実行した query ではなく、store が実際にその期間を保持している必要があります。

```sql
SELECT eventTime, eventName, userIdentity.arn, requestParameters
FROM EVENT_DATA_STORE_ID
WHERE eventSource = 'eks.amazonaws.com'
  AND eventTime >= '2025-07-01 00:00:00'
  AND eventTime < '2025-07-12 00:00:00'
ORDER BY eventTime DESC
```

上限を排他的にすることで、timestamp の精度が秒単位だけだと仮定せずに最終日全体を含められます。この query は、利用可能な EKS の AWS management activity を返します。個々の ID field は呼び出し元の種類によって異なる場合があります。query の実行には service 料金が発生することがあります。

参考資料: [CloudTrail Event history](https://aws.amazon.com/cloudtrail/features/)、[Lake の利用可能性の変更](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-lake-service-availability-change.html)、[event data store の選択](https://docs.aws.amazon.com/help-panel/awscloudtrail/latest/console/query-editor-eds.html)。

### ログ分析のベストプラクティス

EKS クラスターのログを効果的に分析するためのベストプラクティス:

#### 構造化ロギング

アプリケーションで構造化ログ形式（JSON など）を使用します。

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

上記の2025年の JSON 例は、duration や架空の ID を含めて例示用です。新たに測定した値ではありません。仮名化されていても、ユーザー／セッション ID は機微情報になり得ます。適切なアクセス権と保持期間を設定し、必要な field のみを含めてください。

SLF4J と MDC 対応の logging backend を使用する Java アプリケーションでは、値の範囲を制限した ID を使い、ネストした呼び出しでは以前のコンテキストを復元します。この framework 非依存の helper は未定義の Request 型をなくし、UUID import を含みます。

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

抽出した request header と実際の operation を指定して CorrelationContext.run を呼び出します。encoder／pattern を設定して correlation_id を含めてください。MDC に値を設定しただけでは、ログ形式は自動的に変わりません。呼び出し元が指定する correlation ID は tracing metadata であり、認証ではありません。MDC のコンテキストは thread に結び付いています。executor/reactive の境界を越えて伝播し、復元するには、backend／framework のサポート対象の仕組みを使ってください。helper の source review は行いましたが、この環境では Java compiler/runtime を利用できませんでした。

参考資料: [SLF4J MDC API](https://www.slf4j.org/apidocs/org/slf4j/MDC.html)、[Logback MDC と thread pool](https://logback.qos.ch/manual/mdc.html)。

#### ログレベルの使用

ログの重要度を示す適切なログレベルを使用します。

- **ERROR**: アプリケーションの error と例外
- **WARN**: 潜在的な問題や予期しない状況
- **INFO**: 一般的なアプリケーションイベント
- **DEBUG**: デバッグに役立つ詳細情報
- **TRACE**: 非常に詳細なデバッグ情報

#### ログの保持ポリシー

承認済みの運用要件、データアクセス要件、保存要件に基づいて保持期間を選択してください。保持期間を短縮すると、保存済みデータが期限切れになる可能性があります。保持期間の長さは、コンプライアンスの保証や不変の保存ではありません。管理下の CloudWatch log group では、次のコマンドはログを調べるだけではなく、保持期間を変更します。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the log group Region}"
: "${LOG_GROUP:?Set the reviewed owned log group}"
: "${RETENTION_DAYS:?Choose a supported approved retention value such as 30}"
aws logs put-retention-policy --region "$AWS_REGION" \
  --log-group-name "$LOG_GROUP" --retention-in-days "$RETENTION_DAYS"
```

S3 general purpose bucket では、PutBucketLifecycleConfiguration により lifecycle 設定全体が置き換えられます。関係のないすべての rule、versioning／Object Lock の要件、移行の最小サイズ設定を確認し、維持してください。誤った bucket を変更するリスクを減らすため、想定するアカウント所有者も指定します。

```bash
set -euo pipefail
: "${LOG_BUCKET:?Set the owned general purpose S3 bucket}"
: "${ACCOUNT_ID:?Set its expected AWS account ID}"
aws s3api get-bucket-versioning --bucket "$LOG_BUCKET" --expected-bucket-owner "$ACCOUNT_ID"
aws s3api get-bucket-lifecycle-configuration --bucket "$LOG_BUCKET" \
  --expected-bucket-owner "$ACCOUNT_ID" --output json > current-lifecycle.json
```

service から NoSuchLifecycleConfiguration が明示的に返された場合は、設定が存在しないことを確認してから、新しいポリシーを設定するケースに限り、`{"Rules":[]}` で current-lifecycle.json を初期化します。AccessDenied やその他の lookup 失敗を、ポリシーが空であると見なさないでください。以下の例を追加する前に、既存 rule を確認します。

次の例示用の「現在の object を90日後に期限切れにする」ポリシーを log-lifecycle-example.json として保存します。対象となるログを30日後に Standard-IA に移行し、現在の object を90日後に期限切れにします。以前の「60日後に Glacier、90日後に期限切れ」という組み合わせでは、Glacier Flexible Retrieval の90日間の最小ストレージ料金があるのに、Glacier で保持される期間が名目上30日だけです。その移行は、この90日間の例から省略しています。

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

これらは object の経過日数を基準とする rule であり、すでに存在する object にも適用されます。action は非同期です。実際の移行タイミング、早期の手動削除、上書きによっても、最小期間の料金が発生することがあります。Standard-IA の最小課金期間は30日、Glacier Flexible Retrieval は90日、Deep Archive は180日です。より長期のアーカイブスケジュールを選ぶ場合は、これらの制約と実際のアクセス／取得コストを考慮してください。これらの数値は service rule であり、測定された節約額ではありません。

レビュー済みの追加には、次のスクリプトを merge-log-lifecycle.py として保存して実行してください。既存の Rules を保持し、例の ID と衝突する場合は処理を中断します。重複する filter を解決したり、結合された保持ポリシーを承認したりするものではありません。

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

candidate 全体を確認し、bucket の最新設定と比較してください。この API は置換動作をするため、他の書き込み元との調整も必要です。2024年9月以降、新しく作成／変更された設定では、128 KB より小さい object の移行をデフォルトで防止します。変更されていない古い設定では、以前の動作が保持されていることがあります。size filter でデフォルトを上書きできます。また、この設定は維持した無関係な rule にも影響する可能性があります。レビュー済みの all_storage_classes_128K または varies_by_storage_class を明示的に選択してください。GET response に、利用可能な場合は TransitionDefaultMinimumObjectSize が表示されます。

完全な設定と既存データへの影響を確認した後にのみ、ファイル全体を送信してください。

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

versioning を有効にした bucket では、現在の version を期限切れにしても、通常は delete marker が作られ、以前の version は残ります。noncurrent version の期限切れ、delete marker のクリーンアップ、Object Lock／replication の制限は別途確認が必要です。この例は、すべての version を消去したり bucket を空にしたりするものではありません。移行されない小さな object でも、expiration rule の対象にはなります。

この監査では、保持ポリシーや object lifecycle action を適用していません。参考資料: [lifecycle の置換 API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketLifecycleConfiguration.html)、[移行の制約](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html)、[期限切れ／versioning／最小期間](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-expire-general-considerations.html)。

## モニタリングとロギングのベストプラクティス

EKS クラスターにモニタリングとロギングを効果的に実装するためのベストプラクティスを紹介します。

### モニタリングのベストプラクティス

#### 多層モニタリング

EKS クラスターのすべての層をモニタリングします。

1. **インフラストラクチャ層**: EC2 instance、VPC、subnet、security group
2. **クラスター層**: コントロールプレーン、node、Pod、Service
3. **アプリケーション層**: アプリケーションのパフォーマンス、ユーザーエクスペリエンス

#### ゴールデンシグナルのモニタリング

Google の SRE book が提案する「4つのゴールデンシグナル」に注目します。

1. **Latency**: リクエストの処理にかかる時間
2. **Traffic**: システムに対するリクエスト数
3. **Error**: 失敗したリクエストの割合
4. **Saturation**: システムがどれだけ「満杯」か（例: memory 使用量）

#### プロアクティブなモニタリング

傾向や異常を使って、進行しつつあるリスクを特定します。予測は推定値であり、インシデントを事前に予測できる保証はありません。

1. **傾向分析**: リソース使用量の推移を分析します
2. **異常検出**: 異常なパターンを検出します
3. **予測分析**: 将来のリソース要件を予測します

#### 自動スケーリング

この例示用 HPA は、管理下の default/my-app Deployment、動作しているリソースメトリクス API、適切な CPU／memory request を前提としています。utilization の目標値は request に対する percentage であり、ノード容量やコンテナの limit に対する値ではありません。複数のメトリクスを指定した場合、HPA は最も大きい replica 推奨値を選びます。メトリクス取得の失敗で scale down できなくなることがあります。HPA condition を確認し、ワークロードで水平スケーリングが実際に効果を発揮するかテストしてください。

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

技術メトリクスに加えて、ビジネスメトリクスもモニタリングします。

1. **ユーザーアクティビティ**: アクティブユーザー数、セッション時間
2. **トランザクション**: トランザクション件数、トランザクション金額
3. **コンバージョン率**: ユーザーのコンバージョン率、離脱率
4. **SLI/SLO の達成度**: 指標と、定義された目標を測定します。SLA は影響を伴う場合がある契約です。社内 SLO の達成だけでは、契約上の義務を遵守している証明になりません。

### ロギングのベストプラクティス

#### 集中ロギング

必要なログを承認済みの宛先に収集し、明示的なアクセス権と保持期間を設定して、取り込みの失敗も監視します。

1. **一貫した形式**: すべてのアプリケーションでログ形式を統一します
2. **中央リポジトリ**: CloudWatch Logs、OpenSearch、Loki などの中央ログリポジトリを使用します
3. **ログ転送**: Fluent Bit や Fluentd などのログ転送 agent を使用します

#### コンテキスト情報を含める

ログに十分なコンテキスト情報を含めます。

1. **Timestamp**: 正確な timestamp（ISO 8601 形式を推奨）
2. **Request ID**: 分散システムでリクエストを追跡するための一意の ID
3. **承認済みの ID**: user／session ID は、機微情報または個人識別情報となる可能性があります。適切なアクセス権と保持期間を設定し、必要な ID のみを含めてください。
4. **Service 情報**: service 名、バージョン、instance ID
5. **Error の詳細**: error code、error message、stack trace

#### ログレベルのフィルタリング

環境に応じて適切なログレベルを設定します。

1. **開発環境**: 調査に必要な範囲で DEBUG/TRACE を使用し、テスト時も Secret のフィルタリングを行います。
2. **ステージング環境**: INFO レベル
3. **本番環境**: 有用な INFO/WARN のカバレッジを選択します。一時的に DEBUG を使う場合は、量／期間に上限を設け、機微情報をフィルタリングします。

#### 機微情報の保護

ログ内の機微情報を保護します。

1. **PII のマスキング**: 個人識別情報（PII）をマスキングします
2. **認証情報の除外**: パスワード、token、API key などの認証情報を除外します
3. **暗号化**: 保存中と転送中のログを暗号化します

### アラートのベストプラクティス

#### アラートの優先度

アラート疲れを軽減するため、アラートに優先度を付けます。

1. **P1（Critical）**: 直ちに対応が必要な重大な問題
2. **P2（High）**: service で合意された応答時間内に対応すべき重要な問題。緊急度が高くても、営業時間まで自動的に待つわけではありません。
3. **P3（Medium）**: 定期保守中に対応が必要な問題
4. **P4（Low）**: 情報を伝えるアラート

#### アラートのグループ化

次の route field を上記の Alertmanager 設定全体に統合し、receiver と child route は維持します。instance ごとに自動で別々の group を作成するのではなく、service のコンテキストでグループ化してください。

```yaml
route:
  group_by: ['cluster', 'namespace', 'alertname']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
```

#### 対応可能なアラート

トラブルシューティングに十分な情報をアラートに含めます。

1. **明確なタイトル**: 問題を明確に説明するタイトル
2. **証拠と影響**: 観測された症状と影響を説明します。検証するまでは、原因の推測を仮説として明示してください。
3. **トラブルシューティング手順**: トラブルシューティングの手順または link
4. **関連メトリクスとログ**: 診断に役立つメトリクスやログへの link

#### アラートのテスト

アラートシステムを定期的にテストします。

1. **アラートのシミュレーション**: テストアラートを生成します
2. **エスカレーションのテスト**: エスカレーション経路をテストします
3. **障害注入**: 制御された環境で障害を注入します

### コスト最適化のベストプラクティス

#### ログ量の最適化

ログ量を最適化してコストを削減します。

1. **サンプリング**: 必要なカバレッジを確保できる場合に限りサンプリングを行い、欠落する範囲を文書化します。必要な監査／エラー証拠は保持してください。
2. **フィルタリング**: 不要なログをフィルタリングします
3. **圧縮**: ログを圧縮します

#### メトリクス cardinality の管理

メトリクスの cardinality を管理してコストを削減します。

1. **制限された label 値**: label 名の数だけでなく、異なる値と label の組み合わせを制御します。
2. **集約**: 詳細なメトリクスを、より上位のレベルに集約します
3. **収集分解能**: 必要な信号を保持できる scrape interval と集約を選択します。粗い収集ではピークが見えなくなることがあります。

#### ストレージ階層化

コスト効率の高いストレージ階層化を実装します。

1. **ホットストレージ**: 最近のログと頻繁にアクセスされるログ
2. **ウォームストレージ**: アクセス頻度が低いログ
3. **コールドストレージ**: アーカイブ済みログ

## トラブルシューティングとデバッグ

EKS クラスターの問題をトラブルシューティングし、デバッグするためのさまざまな手法を紹介します。

![Diagram mapping three EKS troubleshooting areas (cluster issues, workload issues, common problems) to three debugging tool families: Kubernetes kubectl tools, AWS tools, and network diagnostic tools, with the kubectl tools at the center used by all three areas.](../.gitbook/assets/en-eks-06-eks-monitoring-logging-5.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-06-eks-monitoring-logging-5.html)

### クラスターのトラブルシューティング

#### クラスターの状態を確認する

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

返された実際の stream を選んで範囲を限定した GetLogEvents を実行するか、上記の query を使用してください。この確認ではロギングを有効化／無効化しません。ログがない場合は、別途レビュー済みの設定手順を使い、更新が完了したことを確認してください。

#### ノードのトラブルシューティング

node condition を解釈する前に、Kubernetes context を確認し、実際の node を選択します。Node Ready、スケジューリングの可否、アプリケーションの健全性は、それぞれ異なる信号です。

```bash
kubectl config current-context
kubectl get nodes
: "${NODE_NAME:?Choose the node to inspect}"
kubectl describe node "$NODE_NAME"
kubectl get node "$NODE_NAME" -o jsonpath='{.spec.providerID}{"\n"}{.status.nodeInfo.kubeletVersion}{"\n"}{.status.nodeInfo.containerRuntimeVersion}{"\n"}'
```

managed node group の場合は、実際の名前を選び、status／health を確認してください。これは、すべての Auto Mode、Fargate、self-managed node に当てはまるものではありません。

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster}"
: "${AWS_REGION:?Set its Region}"
: "${NODEGROUP_NAME:?Choose the actual managed node group}"
aws eks describe-nodegroup --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --nodegroup-name "$NODEGROUP_NAME" \
  --query 'nodegroup.{Status:status,Version:version,Health:health.issues,Resources:resources}'
```

ノード管理者が承認したアクセス／診断経路を使用してください。SSH の利用可否、ログインユーザー、systemd tool は、ノード OS と設定によって異なり、EKS の普遍的な機能ではありません。Auto Mode、Fargate、Bottlerocket では、それぞれに該当する管理対象／プラットフォームの手順が必要です。systemd を搭載した標準 Linux EC2 node に、すでに認可された session で接続している場合は、範囲を限定して kubelet log、容量、inode を確認します。

```bash
sudo journalctl -u kubelet --since "30 minutes ago" --no-pager
df -h
df -i
```

アクセス可能な EC2 instance の起動時の問題には EC2 console output が役立つ場合がありますが、kubelet／アプリケーションログ全体を示すものではありません。すべての node が Docker を実行していると仮定せず、報告された runtime とその文書化された診断手段を使用してください。

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

そのコンテナの終了済みの直前 instance が利用できる場合は、そのログも確認します。

```bash
kubectl logs "$POD_NAME" -n "$NAMESPACE" -c "$CONTAINER_NAME" --previous --tail=100
```

以前の instance のログを取得するコマンドは、以前に終了したコンテナ instance が利用可能な場合にのみ使えます。任意の古い Pod や、node とともに失われたログを復元するものではありません。exit code、最後の termination reason、probe、リソース event を合わせて確認してください。restart 数だけでは、OOM や特定の根本原因は証明されません。すべてのアプリケーション image に /bin/bash があるわけではありません。

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

現在の endpoint を確認するには EndpointSlice を使用します。旧式の Endpoints API は非推奨ですが、一律に廃止されたわけではありません。selector、ready な endpoint address、Service port／targetPort、protocol を確認してください。DNS 解決、endpoint の readiness、ネットワーク到達性は、それぞれ別の確認事項です。

ローカル port-forward で選択した Service port を調査できますが、これは診断経路を通じた確認であり、通常の Pod-to-Service 通信や load balancer が動作する証拠ではありません。実際の Service port を指定します。

```bash
set -euo pipefail
: "${NAMESPACE:?Set the service namespace}"
: "${SERVICE_NAME:?Choose the Service}"
: "${SERVICE_PORT:?Choose its service port number}"
kubectl port-forward --address 127.0.0.1 -n "$NAMESPACE" \
  "svc/$SERVICE_NAME" "8080:$SERVICE_PORT"
```

#### NetworkPolicy と診断コンテキスト

送信元の egress と宛先の ingress、namespace／Pod selector、DNS access、policy を適用する CNI を確認してください。security group、route、network ACL、service-mesh policy、TLS も追加の層となる場合があります。任意の一時 Pod から行う probe は、失敗しているワークロードとは異なる label、ServiceAccount、security group、sidecar を持つことがあります。

認可された調査では、制限された profile に対応するレビュー済みの non-root image を使い、選択した Pod に ephemeral diagnostic container を追加します。古い BusyBox tag や未確認の latest image ではなく、承認済み digest を DEBUG_IMAGE に設定してください。

```bash
set -euo pipefail
: "${NAMESPACE:?Set the owned Pod namespace}"
: "${POD_NAME:?Choose the Pod}"
: "${CONTAINER_NAME:?Choose the target container}"
: "${DEBUG_IMAGE:?Set the reviewed non-root diagnostic image digest}"
kubectl debug "$POD_NAME" -n "$NAMESPACE" -it \
  --image="$DEBUG_IMAGE" --profile=restricted --target="$CONTAINER_NAME" -- sh
```

これは ephemeral container を追加して Pod を変更する操作であり、対応する RBAC／admission 権限が必要です。entry は Pod が削除されるまで残ります。shell を終了しただけでは ephemeral-container entry は削除されません。process namespace を対象にできるかどうかは runtime のサポートによります。使用する image には必要な tool が含まれ、profile が禁止する capability なしで実行できる必要があります。診断を拒否されたからといって、privileged profile に黙って切り替えてはいけません。

診断用 shell 内では、対象値もそこで設定してください。ホスト shell の変数は自動的には継承されません。選択した image に必要な tool がある場合、次のようにします。

```bash
: "${SERVICE_DNS:?Set the intended service DNS name inside this shell}"
: "${SERVICE_PORT:?Set its port inside this shell}"
nslookup "$SERVICE_DNS"
nc -zv "$SERVICE_DNS" "$SERVICE_PORT"
```

FQDN が必要な場合は、実際のクラスター DNS suffix を使用してください。TCP 接続に成功しても、HTTP、アプリケーション認証、TLS の有効性は検証されません。packet capture と node debugging には、権限／コンテキストの別途レビューと、範囲を限定した capture filter、時間、保存容量が必要です。一般的な権限のない tcpdump command が常に使えるわけではありません。truncated でも capture に認証情報やユーザーデータが含まれることがあります。この監査では diagnostic Pod、ephemeral container、packet capture、node session を開始していません。

### ロギングとモニタリングのトラブルシューティング

#### Fluent Bit のトラブルシューティング

この章でインストールしたスタンドアロン collector では、レンダリングされた DaemonSet と ConfigMap はどちらも logging 内の eks-log-collector です。

```bash
kubectl get daemonset eks-log-collector -n logging
kubectl get pods -n logging -l app.kubernetes.io/instance=eks-log-collector
kubectl logs -n logging -l app.kubernetes.io/instance=eks-log-collector \
  -c aws-for-fluent-bit --prefix --tail=100
kubectl get configmap eks-log-collector -n logging -o yaml
```

CloudWatch add-on が収集を管理している場合は、amazon-cloudwatch と実際の resource を確認してください。mount 済み設定、ノードファイルへのアクセス、IRSA／Pod Identity の選択、RBAC、output 接続、buffer／backlog／drop の指標を確認します。無関係な kube-system/fluent-bit-config を作成し、collector がそれを読み込むと決めつけないでください。設定／ログ出力を共有する前に、機微情報がないか確認してください。

#### Prometheus のトラブルシューティング

```bash
kubectl get prometheus,alertmanager -n monitoring
kubectl get pods,pvc -n monitoring
kubectl get servicemonitors,prometheusrules -n monitoring
kubectl port-forward --address 127.0.0.1 -n monitoring \
  svc/monitoring-kube-prometheus-prometheus 9090:9090
```

forwarding 中に `http://127.0.0.1:9090/targets` を確認します。実際の Pod log、target error、証明書の信頼性、名前付き Service port、namespace／label selector、rule、直近の sample を確認してください。ServiceMonitor object が存在するだけでは、Prometheus がそれを選択することも endpoint に到達できることも証明されません。AMP の場合は、remote-write の失敗／backlog と対象 workspace を別途確認してください。

#### Grafana のトラブルシューティング

```bash
kubectl get deployment monitoring-grafana -n monitoring
kubectl logs deployment/monitoring-grafana -n monitoring -c grafana --tail=100
kubectl port-forward --address 127.0.0.1 -n monitoring \
  svc/monitoring-grafana 3000:80
```

`http://127.0.0.1:3000` を開き、設定済みの data source、認証情報、time range、query を確認してください。ローカル stack の Prometheus data-source UID は prometheus です。AMG/AMP には別個の plugin と IAM 要件があります。dashboard が空白になるのは、データがゼロだからではなく、誤った data source／label／time range、取り込み失敗が原因の場合があります。

### よくある問題と解決策

#### ImagePullBackOff error

pull error、image repository／digest、architecture、registry 認証、node のネットワーク経路を確認してください。適切な private endpoint／route が使える場合、常にインターネットアクセスが必要なわけではありません。ECR では EC2 node または Fargate Pod の実行 ID と repository policy を検証します。アプリケーションの IRSA／Pod Identity は kubelet の image-pull ID ではありません。

pull Secret を使用する private registry では、承認済みの認証情報プロセスで、完全な Docker auth JSON file を用意してください。credential-helper 参照だけの file では Kubernetes imagePullSecret として不十分です。新しい管理下の Secret を作成する場合は、パスワードをコマンド引数に記述せず file path を渡します。

```bash
set -euo pipefail
: "${NAMESPACE:?Set the owned workload namespace}"
: "${DOCKER_CONFIG_JSON:?Set the protected self-contained registry auth JSON file}"
kubectl create secret generic regcred -n "$NAMESPACE" \
  --type=kubernetes.io/dockerconfigjson \
  --from-file=".dockerconfigjson=$DOCKER_CONFIG_JSON"
```

対象となる管理下のワークロードだけに Secret を関連付けます。Deployment に対するこの strategic patch は、名前付き imagePullSecrets entry を既存 entry に統合します。Pod template を変更し rollout を引き起こすため、最初に管理者の deployment 手順を確認してください。

```bash
set -euo pipefail
: "${NAMESPACE:?Set the owned workload namespace}"
: "${DEPLOYMENT:?Set the owned Deployment name}"
kubectl patch deployment "$DEPLOYMENT" -n "$NAMESPACE" --type=strategic \
  -p '{"spec":{"template":{"spec":{"imagePullSecrets":[{"name":"regcred"}]}}}}'
```

既存 Secret のローテーションでは、管理者の手順に従い、他の registry 参照を保持してください。一律の対処として namespace の default ServiceAccount を patch しないでください。Secret の作成だけでは、registry のログイン、image の存在、pull の成功は確認できません。

#### CrashLoopBackOff error

選択したコンテナの現在／直前の log、exit code、termination reason、startup／liveness probe、設定、リソース event を照合します。OOMKilled、probe の失敗、アプリケーション終了は、それぞれ異なる原因です。依存先の未起動や誤った command でもコンテナは再起動することがあります。通常の image に tool がない場合は、上記の範囲を限定した診断手順を使ってください。証拠を集める前に再起動／削除しないでください。

#### Node NotReady 状態

適切なプラットフォームアクセス経路を通じて、Ready status／reason、node／lease の更新状況、pressure condition、実際の runtime／kubelet 診断情報を確認してください。ディスク容量、inode の枯渇、ネットワーク／API 到達性、runtime failure では、必要な対応が異なります。NotReady の表示だけから、自動修復の対象になった、または安全に drain できると判断しないでください。

#### Service 接続の問題

上記の Service-to-EndpointSlice-to-Pod の経路をたどり、送信元／宛先のネットワーク制御とアプリケーションの listen port／protocol を調べてください。代表的なワークロードのコンテキストからテストします。port-forward、DNS lookup、TCP handshake が成功しても、エンドツーエンドで service が健全とは限りません。

### デバッグツール

Kubernetes の状態／event には kubectl、対応する管理対象 service の状態には AWS CLI、接続性には承認済みの実行コンテキスト内ネットワーク tool を使用します。証拠を保持し、確認だけの操作と Pod の作成、template の変更、ノードの drain、ロギング設定の変更を分けてください。

#### CloudWatch Logs Insights の結果を取得する

StartQuery が返すのは非同期 query ID であり、最終結果ではありません。この Bash／Python の例では、macOS 専用の date -v option を使わず UTC の epoch 秒を使用し、上限回数を設けて polling して、Complete になった場合にのみ結果を表示します。

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

polling の上限は service の timeout ではありません。query が引き続き実行中の場合は、再度確認するか、不要になった場合は StopQuery を明示的に使用してください。log group／期間と必要な IAM 権限の範囲を限定し、query の料金も考慮してください。この監査では CloudWatch query やクラスターのデバッグ操作を実行していません。

## 結論

このドキュメントでは、Amazon EKS クラスターのモニタリングとロギングに関するさまざまなツール、手法、ベストプラクティスを紹介しました。効果的なモニタリングとロギングの戦略を実装することで、クラスターの状態を継続的に把握し、問題を早期に検出し、問題発生時に迅速に対応できます。

主なトピック:

1. **モニタリングとロギングの概要**: モニタリングとロギングの重要性およびアーキテクチャ
2. **EKS コントロールプレーンのロギング**: コントロールプレーンのログタイプと有効化方法
3. **コンテナのロギング**: Fluent Bit と CloudWatch Container Insights を使ったコンテナログの収集
4. **クラスターのモニタリング**: CloudWatch、Prometheus、Grafana を使ったクラスターのモニタリング
5. **アラートとイベント管理**: CloudWatch alarm と Prometheus Alertmanager を使ったアラートの設定
6. **ログの分析と可視化**: CloudWatch Logs Insights、OpenSearch、Grafana Loki を使ったログ分析
7. **モニタリングとロギングのベストプラクティス**: 効果的なモニタリングとロギングのベストプラクティス
8. **トラブルシューティングとデバッグ**: よくある問題と解決策

EKS クラスターのモニタリングとロギングは継続的なプロセスです。クラスターとアプリケーションの要件を満たせるよう、常に改善してください。

## 参考資料

- [Amazon EKS のモニタリングに関するベストプラクティス](https://docs.aws.amazon.com/eks/latest/userguide/eks-observe.html)
- [Amazon EKS のロギングに関するベストプラクティス](https://docs.aws.amazon.com/prescriptive-guidance/latest/amazon-eks-observability-best-practices/logging-best-practices.html)
- [Kubernetes モニタリングアーキテクチャ](https://kubernetes.io/docs/tasks/debug-application-cluster/resource-usage-monitoring/)
- [Prometheus ドキュメント](https://prometheus.io/docs/introduction/overview/)
- [Grafana ドキュメント](https://grafana.com/docs/grafana/latest/)
- [Fluent Bit ドキュメント](https://docs.fluentbit.io/manual/)
- [Amazon CloudWatch ドキュメント](https://docs.aws.amazon.com/cloudwatch/)
- [Amazon OpenSearch Service ドキュメント](https://docs.aws.amazon.com/opensearch-service/)

## クイズ

この章で学んだ内容を確認するには、[トピッククイズ](../quizzes/eks/06-eks-monitoring-logging-quiz.md)に挑戦してください。
