# EKSの高度なデバッグとインシデント対応

> **レビュー基準**: Kubernetes 1.36スキーマおよびkubectl 1.36.2。現在サポートされているEKSバージョンと互換性のあるコンポーネントリリースを選択してください。
> **最終更新日**: 2026年9月12日

Amazon EKSクラスターを安定して運用するには、体系的なインシデント対応フレームワークと高度なデバッグスキルが欠かせません。このドキュメントでは、本番環境で発生する複雑な問題をすばやく診断し、解決するための実践的な手順を説明します。

## 目次

1. [インシデント対応フレームワーク](#1-incident-response-framework)
2. [コントロールプレーンのデバッグ](#2-control-plane-debugging)
3. [ノードレベルのトラブルシューティング](#3-node-level-troubleshooting)
4. [ワークロードのデバッグ](#4-workload-debugging)
5. [ネットワーク診断](#5-networking-diagnostics)
6. [ストレージのトラブルシューティング](#6-storage-troubleshooting)
7. [可観測性アーキテクチャ](#7-observability-architecture)
8. [障害検出アーキテクチャ](#8-failure-detection-architecture)
9. [クイックリファレンス](#9-quick-reference)
10. [次のステップ](#10-next-steps)

---

<span id="1-incident-response-framework"></span>

## 1. インシデント対応フレームワーク

### 最初の5分間のチェックリスト（初期トリアージ）

最初の30秒で行う手順、2分間の影響範囲確認、合計5分という時間は、計画上の目安として扱い、実測済みの完了時間とみなさないでください。まず顧客への影響と、対象のアカウント、クラスター／コンテキスト、namespace、直近の変更を特定します。APIクライアントが利用できない原因には、認証情報、認可、DNS／ネットワーク、コントロールプレーンの問題があります。それだけで、稼働中のアプリケーションがすべて停止したとは判断できません。

ノードの状態、Pod／コンテナの状態、コントローラーのロールアウト状況、最近のイベント、リソースのサンプルを合わせて確認します。`phase!=Running`では、RunningだがNotReady／CrashLoopingのPodを見落とし、正常に完了したJobを含めてしまいます。PodのphaseがRunningでも、readinessが成立しているとは限りません。Deploymentでは、`1/1`のような表示文字列を検索するのではなく、desired、updated、ready／availableのレプリカ数とobserved generationを比較します。

標準的なVPC CNIの`aws-node` DaemonSetは通常`kube-system`で動作します。`amazon-vpc-cni-system`というnamespaceはEKSの前提条件ではありません。Auto Modeのみを使う環境では、ネットワーキングとノードシステムのDNSを標準とは異なる方法で管理するため、標準アドオンのPodがない場合はノード／コントローラーのモードを踏まえて解釈します。Metrics Serverのデータはサンプリングされたリソース状況であり、顧客向けサービスの可用性を示すものではありません。

### 初期診断スクリプト

このスクリプトはAPI要求を範囲限定して実行し、選択したワークロードnamespaceとクラスターのノード／システムPodの状態について、非公開の証跡を保存します。Secretの内容を収集したり、すべてのPodの環境変数／設定を出力したりはしません。ログ、イベント、エラーメッセージにも機密性の高いアプリケーションデータが含まれる場合があります。証跡を共有する前に内容を確認して秘匿情報をマスキングしてください。実行前にアカウント／コンテキストの入力値と、既存の非公開証跡ディレクトリを確認します。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the intended Region}"
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${EXPECTED_ACCOUNT_ID:?Set the intended account ID}"
: "${KUBE_CONTEXT:?Set the explicit kubectl context}"
: "${NAMESPACE:?Set the owned workload namespace}"
: "${EVIDENCE_PARENT:?Set an existing private evidence directory}"
test -d "$EVIDENCE_PARENT"
ACTUAL_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
test "$ACTUAL_ACCOUNT_ID" = "$EXPECTED_ACCOUNT_ID" || { echo "Account mismatch" >&2; exit 1; }
CLUSTER_ENDPOINT=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.endpoint --output text)
KUBE_ENDPOINT=$(kubectl config view --context "$KUBE_CONTEXT" --minify \
  -o jsonpath='{.clusters[0].cluster.server}')
test "$CLUSTER_ENDPOINT" = "$KUBE_ENDPOINT" || { echo "Context/cluster mismatch" >&2; exit 1; }

umask 077
TRIAGE_DIR=$(mktemp -d "$EVIDENCE_PARENT/eks-triage.XXXXXXXX")
TRIAGE_FAILED=0
k() { kubectl --context "$KUBE_CONTEXT" --request-timeout=15s "$@"; }
collect() {
  local name=$1
  shift
  if "$@" > "$TRIAGE_DIR/$name.txt" 2> "$TRIAGE_DIR/$name.stderr"; then
    printf '%s\tok\n' "$name" >> "$TRIAGE_DIR/status.tsv"
  else
    local rc=$?
    TRIAGE_FAILED=$((TRIAGE_FAILED + 1))
    printf '%s\tfailed:%s\n' "$name" "$rc" >> "$TRIAGE_DIR/status.tsv"
  fi
}
node_health() {
  k get nodes -o json | jq '[.items[] | {
    name:.metadata.name,uid:.metadata.uid,providerID:.spec.providerID,
    unschedulable:.spec.unschedulable,taints:.spec.taints,conditions:.status.conditions
  }]'
}
pod_health() {
  k -n "$NAMESPACE" get pods -o json | jq '[.items[] | {
    name:.metadata.name,uid:.metadata.uid,node:.spec.nodeName,owners:.metadata.ownerReferences,
    deleting:.metadata.deletionTimestamp,phase:.status.phase,conditions:.status.conditions,
    containers:[.status.containerStatuses[]? | {name,ready,restartCount,state,lastState}],
    initContainers:[.status.initContainerStatuses[]? | {name,ready,restartCount,state,lastState}]
  }]'
}
deployment_health() {
  k -n "$NAMESPACE" get deployments -o json | jq '[.items[] | {
    name:.metadata.name,generation:.metadata.generation,observed:.status.observedGeneration,
    desired:(.spec.replicas // 1),updated:(.status.updatedReplicas // 0),
    ready:(.status.readyReplicas // 0),available:(.status.availableReplicas // 0),
    conditions:.status.conditions
  }]'
}
load_balancers() {
  k -n "$NAMESPACE" get services -o json | jq '[.items[] | select(.spec.type=="LoadBalancer") | {
    name:.metadata.name,class:.spec.loadBalancerClass,selector:.spec.selector,
    ports:.spec.ports,status:.status.loadBalancer
  }]'
}
collect nodes node_health
collect pods pod_health
collect deployments deployment_health
collect load-balancers load_balancers
collect events k -n "$NAMESPACE" get events --sort-by='.metadata.creationTimestamp'
collect system-pods k -n kube-system get pods -o wide
collect node-resources k top nodes
collect pod-resources k -n "$NAMESPACE" top pods --sort-by=memory
printf 'Private evidence: %s; failed collections: %s\n' "$TRIAGE_DIR" "$TRIAGE_FAILED"
test "$TRIAGE_FAILED" -eq 0
```

`status.tsv`と各エラー出力を確認します。権限不足、メトリクスの利用不可、APIタイムアウトは収集失敗として扱われます。どれか一つでも収集に失敗するとスクリプトは0以外で終了し、インシデントが解決したとは主張しません。完了済み、Pending、RunningのPod状態は意図的にすべて残し、個別に判断できるようにしています。追加ログを選択して取得するときは、namespace、Pod UID、コンテナを正確に指定し、時間範囲と行数に上限を設けてください。

LoadBalancer一覧はService JSONをローカルで絞り込みます。`spec.type`はサポート対象の組み込みServiceフィールドセレクターではありません。初期収集では、広範な`cluster-info dump`、自動アーカイブのアップロード、リソースの再起動や削除は行いません。

### 重大度マトリクス

| 重大度 | 分類 | 影響範囲 | 対応時間 | 例 |
|----------|---------------|--------------|---------------|----------|
| **P1** | 重大 | サービス全体の停止 | 15分以内 | コントロールプレーン障害、全ノードがNotReady |
| **P2** | 高 | 主要機能の障害 | 1時間以内 | 特定ワークロードの完全停止、ネットワーク接続の問題 |
| **P3** | 中 | 部分的な影響 | 4時間以内 | 一部Podの再起動、性能低下 |
| **P4** | 低 | 軽微な問題 | 24時間以内 | ログ収集の遅延、重要度の低い監視アラート |

この重大度表の対応時間は、組織ごとに設定する目標の例です。実際の顧客影響に基づいて分類してください。コントロールプレーンだけの停止でも、既存ワークロードのトラフィックは継続している場合があります。

### 問題をすばやく特定するための判断フロー

<!-- Content audit: diagram prose needs parent repair; see eks-advanced-debugging/diagram-review.json.
![Decision-tree workflow for the first minutes of EKS incident triage: after an incident is detected it asks whether the service is accessible, then walks kubectl connectivity, node readiness, and pod status toward control-plane, node, scheduling, or app/config causes, or response delay and intermittent errors toward workload, cluster-wide, or network/DNS causes.](../.gitbook/assets/en-eks-11-eks-advanced-debugging-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-11-eks-advanced-debugging-0.html)
-->

---

<span id="2-control-plane-debugging"></span>

## 2. コントロールプレーンのデバッグ

### EKSコントロールプレーンのログ種別

EKSには5種類のコントロールプレーンログがあります。有効にした場合に限り、リージョン単位のCloudWatchロググループへ送信されます。ログを有効にしても、過去に存在しなかったログが復元されるわけではありません。ログへのアクセスと保持期間を適切に制限し、CloudWatchの取り込み、保存、クエリにかかる料金も考慮してください。ロググループ／ストリームが見つからない場合、ログ記録の無効化、データ未配信、リージョンの誤り、アクセス拒否などが考えられ、必ずしもコントロールプレーン障害を意味しません。

| 種類 | 証跡 |
| --- | --- |
| api | APIサーバーの操作とエラーメッセージ |
| audit | API要求の主体、verb、リソース、応答ステータス |
| authenticator | IAMからKubernetesへの認証に関する証跡 |
| controllerManager | コントローラーの調整処理に関するメッセージ |
| scheduler | スケジューリングの判断／エラー |

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"
LOG_GROUP="/aws/eks/$CLUSTER_NAME/cluster"
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query 'cluster.{ARN:arn,Status:status,Logging:logging}'
aws logs describe-log-streams --region "$AWS_REGION" --log-group-name "$LOG_GROUP" \
  --order-by LastEventTime --descending --max-items 10 \
  --query 'logStreams[].{Name:logStreamName,LastEvent:lastEventTimestamp}'
```
```bash
# MUTATION: review cost, retention, access and available subnet IPs first.
set -euo pipefail
UPDATE_ID=$(aws eks update-cluster-config --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query update.id --output text)
test -n "$UPDATE_ID" && test "$UPDATE_ID" != None
aws eks describe-update --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --update-id "$UPDATE_ID" --query update
```
変更は非同期で行われます。返されたupdate IDをSuccessfulになるまで追跡してください。Failed／Cancelledやクライアントのタイムアウトは成功を意味しません。その後、describe-clusterと新しいログの配信を確認します。クラスターがACTIVEであることだけでは、この更新の完了は確認できません。更新には、設定された各クラスターサブネットで最大5個の空きIPアドレスが必要になる場合があります。現在のEKSログ記録の前提条件を確認してください。

### CloudWatch Logs Insightsのクエリ

各ブロックは、BashやSQLではなく、**個別のLogs Insights QLクエリ**として実行します。コンソールまたはStartQuery要求で、対象のロググループと時間範囲を正しく選択してください。以下のクエリは、CloudWatchが認識したEKS JSON監査ログのフィールドを使います。パイプラインが形式を変更している場合は、代表的なログレコードとネストしたログの解析結果を確認してください。クエリがイベントに一致しなくても、サービスが正常だったことやログが配信されたことの証明にはなりません。

#### APIエラーメッセージ

```text
fields @timestamp, @message
| filter @logStream like /kube-apiserver/ and @logStream not like /audit/
| filter @message like /error|Error|ERROR/
| sort @timestamp desc
| limit 100
```

#### 選択した時間範囲内のエラー件数

```text
fields @timestamp, @message
| filter @logStream like /kube-apiserver/ and @logStream not like /audit/
| filter @message like /error|Error|ERROR/
| stats count(*) as error_count by bin(5m)
```

#### 調査が必要なauthenticatorメッセージ

```text
fields @timestamp, @message
| filter @logStream like /authenticator/
| filter @message like /access denied|Unauthorized|unauthorized/
| sort @timestamp desc
| limit 50
```

#### 構造化監査ログの認証／認可拒否

```text
fields @timestamp, user.username, verb, objectRef.resource, objectRef.namespace, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code in [401, 403]
| sort @timestamp desc
| limit 100
```

#### 調査対象の1つのIDに関する構造化監査ログの操作

```text
fields @timestamp, user.username, verb, objectRef.resource, objectRef.namespace, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter user.username = "REPLACE_WITH_OBSERVED_KUBERNETES_USERNAME"
| sort @timestamp desc
| limit 50
```

#### ID／リソース別の監査ログ429イベント

```text
fields user.username, verb, objectRef.resource, responseStatus.code
| filter @logStream like /kube-apiserver-audit/
| filter responseStatus.code = 429
| stats count(*) as request_count by user.username, verb, objectRef.resource
| sort request_count desc
| limit 50
```

#### API要求数（スロットリング数とは限らない）

```text
fields user.username, verb, objectRef.resource
| filter @logStream like /kube-apiserver-audit/
| stats count(*) as request_count by user.username, verb, objectRef.resource
| sort request_count desc
| limit 50
```

監査ログの401／403検索では、authenticatorメッセージ検索とは異なる要求単位の拒否を確認できます。API呼び出し件数はスロットリングされた呼び出し数ではありません。また、時間帯ごとに集計した結果には各イベントの@timestampが残らないため、それを基準に並べ替えることはできません。StartQueryはクエリIDを返します。GetQueryResultsでCompleteになるまでポーリングし、Failed／Cancelled／Timeout／データ欠落の状態も保持してください。[監視の章](06-eks-monitoring-logging.md)では、範囲を限定したクエリとポーリングの手順を説明します。この監査では実際のCloudWatchクエリを実行していません。

[EKSコントロールプレーンログ](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html) · [AWS監査フィールドの例](https://docs.aws.amazon.com/eks/latest/best-practices/auditing-and-logging.html)

### IAM認証のトラブルシューティング

最初のトリアージでアカウント／コンテキストの確認を先に行います。kubectlを使う人間／自動化のIAMアイデンティティ、ノードのブートストラップに使うアイデンティティ、アプリケーションPod内で使うAWSアイデンティティを区別してください。トークンを生成できても、Kubernetesで認証または認可されたことの証明にはなりません。

k8s-aws-v1で始まるEKS IAMトークンは、base64urlでエンコードされた署名付きSTS要求であり、**3つの部分から成るJWTではありません**。JSONとしてデコード／表示したり、ログに貼り付けたりしないでください。Kubernetesが投影するServiceAccountトークンは別のJWT認証情報です。

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"; : "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"
aws sts get-caller-identity
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query 'cluster.{ARN:arn,AuthenticationMode:accessConfig.authenticationMode}'
# Print only the credential expiry, not the bearer token.
aws eks get-token --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --query status.expirationTimestamp --output text
kubectl --context "$KUBE_CONTEXT" auth whoami
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" auth can-i get pods
```

どこを調査するかはAuthenticationModeによって異なります。API／API_AND_CONFIG_MAPモードでは、プリンシパルのaccess entry、関連付けられたポリシーの範囲、RBACバインディングを調べます。CONFIG_MAPモードでは既存のレガシーマッピングを調べます。分類できていない401／403を直すために、認証モードを切り替えたりaws-authを置き換えたりしないでください。アクセスモードの移行には固有の前提条件と、元に戻せない遷移があります。IAMロールのパスやSTSセッションARNを、文字列置換で推測してはいけません。

```bash
# Run for API or API_AND_CONFIG_MAP authentication mode.
aws eks list-access-entries --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME"
: "${PRINCIPAL_ARN:?Use a reviewed IAM role/user ARN, not an STS assumed-role session ARN}"
aws eks describe-access-entry --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --principal-arn "$PRINCIPAL_ARN"
aws eks list-associated-access-policies --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --principal-arn "$PRINCIPAL_ARN"
```
```bash
# Read-only legacy mapping inspection for CONFIG_MAP/API_AND_CONFIG_MAP clusters.
kubectl --context "$KUBE_CONTEXT" -n kube-system get configmap aws-auth -o yaml
```

既存のノードブートストラップ用マッピングは維持してください。関連付けられたバインディングがなければ、グループ名だけでは権限は付与されません。診断目的でsystem:mastersを追加するのではなく、レビュー済みの最小権限アクセスを使ってください。403は認可拒否を示し、401は無効または期限切れの認証情報を示す場合があります。ネットワーク／TLS障害は別の証跡です。

### IRSAのトラブルシューティング

IRSAには、正しいOIDC issuer／provider、namespaceとServiceAccountのsubjectおよびsts.amazonaws.com audienceに一致するロール信頼ポリシー、さらにweb identity認証情報を使いローテーションするワークロードSDKが必要です。以下のannotationは構成の一部にすぎません。namespaceとロールはプレースホルダーで、このYAMLだけでロール、provider、バケット権限は作成されません。

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-access-sa
  namespace: diagnostics-example
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/owned-s3-access-role
```
```bash
set -euo pipefail
: "${SERVICE_ACCOUNT:?Set the actual ServiceAccount on the Pod}"
: "${POD_NAME:?Set an owned Pod}"; : "${CONTAINER_NAME:?Set its application container}"
: "${IRSA_ROLE_NAME:?Set the reviewed IAM role name}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get serviceaccount "$SERVICE_ACCOUNT" \
  -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}{"\n"}'
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.identity.oidc.issuer --output text
aws iam get-role --role-name "$IRSA_ROLE_NAME" --query Role.AssumeRolePolicyDocument
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json | jq '{
  uid:.metadata.uid,serviceAccount:.spec.serviceAccountName,
  envNames:[.spec.containers[] | {name,envNames:[.env[]?.name]}],
  projectedVolumes:[.spec.volumes[]? | select(.projected) | {name,projected}]
}'
```

Secretの値やトークンのバイト列を出力せず、環境変数の**名前**、トークンファイルのパス／マウントのメタデータ、SDKの認証情報チェーンを調べます。静的な認証情報やSDKチェーンで先に選ばれる別のproviderが、意図したアイデンティティを上書きする場合があります。実際のアプリケーションコンテナを調査してください。新規作成したdebug Pod／コンテナは、異なるアイデンティティや設定を持つ場合があります。

```bash
# Optional read-only identity request, only if AWS CLI is already in this container.
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- aws sts get-caller-identity
```

STSのアイデンティティ応答は使用中のロールを示しますが、すべてのバケットを一覧表示したり特定のオブジェクトへアクセスしたりできることの証明にはなりません。アイデンティティの確認だけを目的に、アカウント全体に対してaws s3 lsを実行しないでください。

### Pod Identityのトラブルシューティング

```bash
aws eks list-pod-identity-associations --region "$AWS_REGION" \
  --cluster-name "$CLUSTER_NAME" --namespace "$NAMESPACE" --service-account "$SERVICE_ACCOUNT"
: "${ASSOCIATION_ID:?Use the exact matching association ID}"
aws eks describe-pod-identity-association --region "$AWS_REGION" \
  --cluster-name "$CLUSTER_NAME" --association-id "$ASSOCIATION_ID"
# Standard EC2-node setup only; Auto Mode provides the integration itself.
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods \
  -l app.kubernetes.io/name=eks-pod-identity-agent
```

関連付け、ロール信頼／権限、対応するSDK認証情報provider、agent／ノードへの到達性を確認します。Auto Modeには組み込みのサポートがあり、重複するagentをインストールする必要はありません。FargateはEKS Pod Identityに対応していません。これらの診断と関連付けの作成／変更は分けてください。IRSAとPod Identityでは、トークンのaudienceと認証情報の受け渡し経路が異なります。特に設定しない限り、オペレーターのAWS CLIアイデンティティはどちらにも使われません。

### ServiceAccountトークンの有効期間とローテーション

投影トークンに一律の「最大24時間」という上限はありません。要求した有効期間とAPIサーバーの設定上限は別です。Kubeletは、トークンの有効期間の80%を超えたとき、または24時間を超えたときにローテーションを要求します。アプリケーション側では更新後のファイルを読み直す必要があります。EKSが説明するKubernetes API ServiceAccountトークン移行向けの90日間の互換期間と古いトークンの監査annotationは、キャッシュしてよい期間でも、IRSA／Pod Identity／任意の依存サービスに対する有効期間の保証でもありません。

次の例はSTS audience向けに有効期間1時間のカスタムトークンを要求します。デフォルトのAPIトークンの有効期間を延長するものでも、IRSAを自動構成するものでもありません。既存のnamespace／ServiceAccount、レビュー済みイメージ、ロール信頼、アプリケーションSDK／トークンファイルの設定は別途準備してください。STS audienceのトークンがKubernetes APIに有効だと想定してはいけません。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: audience-token-example
  namespace: diagnostics-example
spec:
  serviceAccountName: owned-app
  automountServiceAccountToken: false
  containers:
  - name: app
    image: registry.example.com/owned/app:replace-with-reviewed-digest
    volumeMounts:
    - name: token
      mountPath: /var/run/secrets/tokens
      readOnly: true
  volumes:
  - name: token
    projected:
      sources:
      - serviceAccountToken:
          path: token
          expirationSeconds: 3600
          audience: sts.amazonaws.com
```

[EKS access entry](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html) · [EKSトークンの移行／ローテーション](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html) · [Kubernetesの投影トークン](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/) · [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html) · [Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)

### EKSアドオンのエラーパターン

アドオンを変更する前に、インストール済みバージョン、管理者、設定／アイデンティティの値、health issuesを確認してください。ACTIVEはアドオンの状態であり、顧客向けトラフィックがすべて正常である証明ではありません。DEGRADEDはhealth issuesを示し、単なる性能低下を意味するものではありません。CREATE_FAILED／UPDATE_FAILED／DELETE_FAILEDの場合は実際のissue詳細を調べます。Auto Modeが管理する機能では、標準アドオンが存在しないことが想定内の場合があります。

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"; : "${ADDON_NAME:?Set the existing owned add-on}"
aws eks describe-addon --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --addon-name "$ADDON_NAME" \
  --query 'addon.{Version:addonVersion,Status:status,Issues:health.issues,Configuration:configurationValues,Role:serviceAccountRoleArn,PodIdentity:podIdentityAssociations}'
CLUSTER_VERSION=$(aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query cluster.version --output text)
aws eks describe-addon-versions --region "$AWS_REGION" --addon-name "$ADDON_NAME" \
  --kubernetes-version "$CLUSTER_VERSION" \
  --query 'addons[].addonVersions[].{Version:addonVersion,Architectures:architecture,ComputeTypes:computeTypes,Compatibility:compatibilities}'
```

応答の先頭にあるバージョンを「最新」とみなしたり、すべてのノード種別と自動的に互換すると考えたりしないでください。アーキテクチャ、コンピュート種別、デフォルトバージョンの表示、設定スキーマ、IAM／Pod Identity、コンポーネントの移行手順を確認します。設定出力は機密情報を含む場合があるため、非公開にしてください。バージョン更新は意図的な変更であり、初期診断ではありません。

```bash
# MUTATION: use a reviewed compatible version and configuration/identity plan.
set -euo pipefail
: "${REVIEWED_ADDON_VERSION:?Choose from the compatible versions after review}"
: "${REVIEWED_ADDON_CONFIG:?Set the path to the reviewed JSON configuration file}"
test -f "$REVIEWED_ADDON_CONFIG"
aws eks describe-addon-configuration --region "$AWS_REGION" --addon-name "$ADDON_NAME" \
  --addon-version "$REVIEWED_ADDON_VERSION" --query configurationSchema --output text
# The configuration file must be checked against this version's schema before this request.
UPDATE_ID=$(aws eks update-addon --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --addon-name "$ADDON_NAME" --addon-version "$REVIEWED_ADDON_VERSION" \
  --configuration-values "file://$REVIEWED_ADDON_CONFIG" \
  --resolve-conflicts PRESERVE --query update.id --output text)
test -n "$UPDATE_ID" && test "$UPDATE_ID" != None
aws eks describe-update --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --addon-name "$ADDON_NAME" --update-id "$UPDATE_ID" --query update
```

PRESERVEは競合を解決する際にEKSへ既存のカスタム設定を維持するよう要求する値であり、バックアップではなく、任意の古い設定が新しいリリースで動作する保証でもありません。OVERWRITEは競合するカスタマイズを初期化する場合があるため、個別にレビューする必要があります。このupdate IDを完了まで追跡し、更新エラーを調べ、アドオンの稼働状態を確認してください。configurationValuesとアイデンティティの変更は、黙って省略／上書きせず明示的に確認します。

[EKSアドオンの更新](https://docs.aws.amazon.com/eks/latest/userguide/updating-an-add-on.html)

---

<span id="3-node-level-troubleshooting"></span>

## 3. ノードレベルのトラブルシューティング

<a id="node-join-diagnosis"></a>

### ノード参加失敗の診断

以下は調査すべき仮説であり、8つの原因が必ず当てはまるという意味ではありません。対象インスタンス／NodeClaim、ブートストラップログ、endpointへの到達性、認証モードと照合して確認してください。

| 領域 | 確認事項 |
| --- | --- |
| ブートストラップとAMI | クラスター名／endpoint／CA、OSごとのブートストラップ、アーキテクチャ、互換性のあるkubelet／AMI。すべてで完全なバージョン一致を求めるわけではありません。 |
| ネットワーク／セキュリティ | Node→API TCP 443、API→kubelet TCP 10250、DNS、ワークロード固有の経路。通信方向、Security Groupの所属、ルーティングを検証します。 |
| VPC DNS | DNS support／hostnames、DHCP resolver／ドメイン設定、実際に使用するendpoint |
| アイデンティティ | Node IAMロールとKubernetesのnode access entry／レガシーマッピング。instance profile ARNではなくロールARNを使用します。 |
| 所有／検出タグ | Provisioner固有のノード所有タグを確認します。ロードバランサー検出用のサブネットタグと混同しないでください。 |
| プライベートアクセス | EKS／ECR／S3／STSなど必要なサービスへの経路を、レビュー済みendpointまたはegressで確保します。プライベートクラスターの設計でNAT gatewayが常に必須とは限りません。 |
| 起動設定 | 実際のprovisionerに合うロール／profileの扱い、launch templateのversion、capacity、subnetの空きIPを確認します。 |
| 初期化 | 選択したAMIに適したnodeadm／cloud-init／bootstrapの証跡を調べます。AL2023、Bottlerocket、Windows、Auto Modeでパスが共通とは限りません。 |

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?Set the exact owned node name}"
NODE_JSON=$(kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o json)
printf '%s\n' "$NODE_JSON" | jq '{
  name:.metadata.name,uid:.metadata.uid,providerID:.spec.providerID,
  os:.status.nodeInfo.osImage,kernel:.status.nodeInfo.kernelVersion,
  kubelet:.status.nodeInfo.kubeletVersion,runtime:.status.nodeInfo.containerRuntimeVersion,
  labels:.metadata.labels,taints:.spec.taints,conditions:.status.conditions
}'
NODE_UID=$(printf '%s\n' "$NODE_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" get events -A \
  --field-selector "involvedObject.uid=$NODE_UID" --sort-by='.metadata.creationTimestamp'
```
```bash
# EC2-backed nodes only: map the Node providerID to an inspected instance ID/Region.
: "${AWS_REGION:?}"; : "${INSTANCE_ID:?Use the verified EC2 ID, not a guessed node-name conversion}"
aws ec2 describe-instances --region "$AWS_REGION" --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[].Instances[].{ID:InstanceId,State:State.Name,AZ:Placement.AvailabilityZone,Subnet:SubnetId,Profile:IamInstanceProfile,Groups:SecurityGroups,Image:ImageId}'
aws ec2 describe-instance-status --region "$AWS_REGION" --instance-ids "$INSTANCE_ID" \
  --include-all-instances
```

まだ登録されていないインスタンスにはNodeオブジェクトがありません。その場合は、管理対象node group／NodeClaim／instanceの証跡を使います。Ready=Falseと、heartbeatがなくReady=Unknownになった状態では、必要な証跡が異なります。NodeがReadyでもpressure状態を併発する場合があります。一つの表示文字列から原因を決めつけないでください。新しいAuto ModeのEC2管理インスタンスは、既定で一般的なEC2一覧から隠れている場合があります。instance IDを直接指定した検索や管理リソースを明示的に含める検索は、アカウント全体の表示設定を変更することとは別です。

### NotReadyノードの判断フロー

<!-- Content audit: diagram prose needs parent repair; see eks-advanced-debugging/diagram-review.json.
![Decision-tree flowchart for diagnosing a NotReady EKS node, walking down through EC2 instance status, kubelet health, network connectivity, and disk/memory pressure to containerd runtime health, with the matching remediation command at each branch.](../.gitbook/assets/en-eks-11-eks-advanced-debugging-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-11-eks-advanced-debugging-1.html)
-->

### ホストと管理ノードの診断

顧客がアクセスできるLinuxノードでSSMを利用するには、ノードエージェント、ロール／ネットワークの前提条件、対象インスタンスへの認可済みアクセスが必要です。SSMはセッションを開きます。EKS Auto Modeの管理インスタンスは、直接SSH接続に対応していません。文書化されたNodeDiagnostic／console-output経路、またはサポート対象のkubectl debug nodeワークフローを使います。現行のAuto Modeガイドでは、ライブログの取得に**sysadmin debug profileを明示的に指定**する方法をサポートしています。これは権限の高いPodを作成する手順であり、SSHセッションでも、デフォルトで付与されるdebug権限でもありません。NodeDiagnosticの収集結果をS3にアップロードすると機密ログやcaptureが保存される場合があるため、対象範囲と保存権限を別途レビューしてください。

```bash
# Interactive host access: an operational session, not an automatic triage step.
: "${AWS_REGION:?}"; : "${INSTANCE_ID:?Use the reviewed self-managed or managed-node-group instance}"
aws ssm start-session --region "$AWS_REGION" --target "$INSTANCE_ID"
```
```bash
# Read-only Linux/systemd host checks after authorized access.
sudo systemctl show kubelet containerd --no-pager \
  -p Id -p LoadState -p ActiveState -p SubState -p ExecMainStatus
sudo journalctl -u kubelet --since "15 minutes ago" -n 200 --no-pager
sudo journalctl -u containerd --since "15 minutes ago" -n 100 --no-pager
sudo crictl info
sudo crictl ps
sudo crictl ps -a
sudo crictl images
df -h
df -i
sudo journalctl --disk-usage
```
```bash
# Exact container ID only; log content may be sensitive.
: "${CONTAINER_ID:?Use an inspected CRI container ID}"
sudo crictl logs --tail=100 "$CONTAINER_ID"
```

これらのsystemd／CRIコマンドは、対象ホストにそのコンポーネントとツールが存在することを前提とします。crictlでは正しいCRI endpointを設定してください。journalの読み取り範囲を限定します。journalctl -fをtailへpipeすると、終了しない場合があります。kubeconfig／client keyを表示したり、ログ、終了済みコンテナ、イメージキャッシュを無差別に削除したりしないでください。必要な証跡が失われたり、kubeletのgarbage collectionが管理する対象に影響したりします。再起動、drain、置換、保持設定の変更は、診断済みの状態に基づく別途レビュー済みの復旧手順として行います。

### リソースプレッシャー

DiskPressureは、利用可能なバイト数／inode数と設定されたeviction thresholdに関係し、dfの容量だけで判断できません。df -hとdf -iの両方、mount identity、kubeletイベントを確認します。保持期間に基づくcleanupが承認されている場合でも、journalctl --vacuum-size=500Mはポリシー例にすぎません。先に必要な証跡を収集し、/var/log配下のglobで一括削除しないでください。MemoryPressureとコンテナのOOMは別々の兆候です。メモリ制限、ノードの空き容量、working set、ログ、pressureメトリクスを照合します。制限値を増やすことやノードを追加することだけでは、根本原因を修正した証明にはなりません。

```bash
# Read-only host evidence, not remediation.
free -h
awk '/MemTotal|MemFree|MemAvailable|Buffers|Cached/ {print}' /proc/meminfo
cat /proc/sys/kernel/pid_max
cat /proc/sys/kernel/threads-max
ps -eLf --no-headers | wc -l
ps -eo pid,comm,nlwp --sort=-nlwp | head -20
if [ -r /proc/pressure/memory ]; then cat /proc/pressure/memory; fi
if [ -r /proc/pressure/cpu ]; then cat /proc/pressure/cpu; fi
```

プロセスディレクトリの数は、すべてのthread／task数を表すものではありません。ps NLWPとカーネル上限は手掛かりですが、kubeletによるPID pressureの計算やcgroup PID制限はそれぞれ個別に解釈する必要があります。単純なメモリ使用率の高さを、KubernetesのMemoryPressure状態と呼ばないでください。メトリクスが得られない場合は、証跡が利用できない状態として扱います。

### Karpenterのprovisioningに関する問題 {#karpenter-provisioning-issues}

```bash
# Self-managed Karpenter; use the actual release namespace and selected objects.
: "${KARPENTER_NAMESPACE:?Set the existing controller namespace}"
: "${NODEPOOL_NAME:?}"; : "${NODECLAIM_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$KARPENTER_NAMESPACE" logs \
  -l app.kubernetes.io/name=karpenter -c controller --since=15m --tail=200 --prefix
kubectl --context "$KUBE_CONTEXT" get nodepool "$NODEPOOL_NAME" -o yaml
kubectl --context "$KUBE_CONTEXT" get nodeclaim "$NODECLAIM_NAME" -o yaml
kubectl --context "$KUBE_CONTEXT" get events -A \
  --field-selector "involvedObject.name=$NODECLAIM_NAME" --sort-by='.metadata.creationTimestamp'
```

NodePool／NodeClassのready状態、NodeClaimのconditions／events、制約、上限、subnetの空きIP、IAM、EC2 capacityを確認します。Auto Modeでは同梱コントローラーのNodeClaim／NodeClass／eventsと監査ログの証跡を使い、セルフマネージドのkarpenter Deployment／namespaceがあると想定しないでください。次のセルフマネージドKarpenter v1スキーマはパターンの例です。互換性のあるリリースと、レビュー済みの既存EC2NodeClassが必要です。これはクラスターのデフォルトNodePoolを置き換えるコマンドではありません。CPU／メモリのlimitは上限値であり、予約済みcapacityではありません。capacity typeの一覧だけでSpotのみの動作やAZ間の均等配置が保証されるわけでもありません。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: reviewed-capacity-example
spec:
  template:
    spec:
      requirements:
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
        - on-demand
      - key: karpenter.k8s.aws/instance-category
        operator: In
        values:
        - c
        - m
        - r
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: reviewed-existing-class
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 30s
```

### 管理Node Groupのエラーコード

| Issue | 意味と証跡 |
| --- | --- |
| AccessDenied | Kubernetes APIの認証／認可失敗。IAMに加えてnode accessとEKS node-manager RBACを調べます。 |
| AsgInstanceLaunchFailures | ASGの起動失敗。実際のactivity message、template、capacity、権限を確認します。 |
| ClusterUnreachable | Kubernetes APIの接続性または要求処理のtimeout。VPC endpointの欠落とは限りません。 |
| InsufficientFreeAddresses | 選択したnode subnetの空きIP不足。既存subnetのIPv4 CIDRはその場で拡張できません。 |
| NodeCreationFailure | 起動したinstanceが登録に失敗。bootstrap、アクセス、必要なネットワーク経路を確認します。 |

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"; : "${NODEGROUP_NAME:?Set the exact managed node group}"
aws eks describe-nodegroup --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --nodegroup-name "$NODEGROUP_NAME" \
  --query 'nodegroup.{Status:status,Issues:health.issues,Version:version,Release:releaseVersion,Subnets:subnets,Role:nodeRole,LaunchTemplate:launchTemplate,Repair:nodeRepairConfig}'
# For a Kubernetes authorization issue, inspect rather than blindly replace EKS-managed RBAC.
kubectl --context "$KUBE_CONTEXT" get clusterrole eks:node-manager -o yaml
kubectl --context "$KUBE_CONTEXT" get clusterrolebinding eks:node-manager -o yaml
```

各issueのmessage／resourceIdsと、現行AWSの修復手順を使ってください。トラブルシューティングガイドでは、管理ノードが15分以内にjoinできない場合のNodeCreationFailureを説明しています。すべての起動がその時間内に完了するという保証ではありません。subnetの空き領域が必要なら、既存CIDRを編集するのではなく、新たなアドレス空間／subnetとprovisioner固有の移行を計画します。EKS管理のRBAC構成は変わる場合があります。AccessDeniedが発生しただけで、古いClusterRoleの置き換え例を貼り付けないでください。ノードの修復／evictionは調査とは別の操作です。ワークロード、budget、データ、現在のノード管理モードを考慮してください。

[EKSのトラブルシューティング](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html) · [Auto Modeの診断経路](https://docs.aws.amazon.com/eks/latest/userguide/auto-troubleshoot.html) · [Security Groupの通信経路](https://docs.aws.amazon.com/eks/latest/userguide/sec-group-reqs.html) · [プライベートクラスター](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html) · [Karpenterの互換性](https://karpenter.sh/docs/upgrading/compatibility/)

### Node Readiness Controller（起動段階ごとの検証）

Kubernetes SIGsのNode Readiness Controllerは、クラスター外部で稼働する実際のコントローラーです。レビュー対象のv0.5.0リリースは、クラスター全体の`readiness.node.x-k8s.io/v1alpha1` `NodeReadinessRule`を使用します。組み込みのEKS ConfigMap処理機能でも、Node APIのGAフィールドでもありません。

このコントローラーはNode conditionsを読み取り、taintを管理します。ConfigMap内の任意の`checks[].probe.exec`を実行するものではありません。元のファイル存在確認／containerdチェックを行うには、対応するconditionsを公開する、別途実装され認可されたreporterまたはNPD custom monitorが必要です。CNI設定ファイルが存在するだけではCNIがreadyだと証明できません。プロジェクトに付属するreporterは`CHECK_ENDPOINT`、`CONDITION_TYPE`、`NODE_NAME`を使ってHTTP endpointをpollします。従来のexec probe形式の設定ではありません。

このルールは明示的なtest-scopeの**taint preview**です。適用するとクラスターリソースが作成され、コントローラーがstatusを更新しますが、`dryRun: true`ではノードのtaintを追加／削除しません。例のcondition名とノードlabelはカスタムの前提条件であり、EKSが自動的に提供するlabel／conditionではありません。

```yaml
apiVersion: readiness.node.x-k8s.io/v1alpha1
kind: NodeReadinessRule
metadata:
  name: reviewed-bootstrap-readiness
spec:
  dryRun: true
  enforcementMode: bootstrap-only
  nodeSelector:
    matchLabels:
      audit.example.com/readiness-demo: 'true'
  conditions:
  - type: audit.example.com/CNIReady
    requiredStatus: 'True'
  - type: audit.example.com/ContainerRuntimeReady
    requiredStatus: 'True'
  taint:
    key: readiness.k8s.io/bootstrap-not-ready
    value: pending
    effect: NoSchedule
```

強制を有効にする前に、`status.dryRunResults`、`status.nodeEvaluations`、失敗したノード、実際に選択されたNode conditionsを確認します。

```bash
# Read-only: the controller and released CRD must already be installed.
: "${KUBE_CONTEXT:?Set the verified context}"
kubectl --context "$KUBE_CONTEXT" get nodereadinessrule reviewed-bootstrap-readiness -o yaml
kubectl --context "$KUBE_CONTEXT" get nodes \
  -l audit.example.com/readiness-demo=true -o json
```

起動時のゲートとして使う場合は、コントローラーとスケジューラーの競合が起きる前に、条件に合うstartup taintを付けて新規ノードを登録します。reporterと必要なsystem DaemonSetはそのtaintを許容し、APIに到達できる必要があります。必要条件をすべて満たすとbootstrap-onlyモードはtaintを削除して完了を記録しますが、その後にconditionが失敗してもゲートを再適用しません。continuousモードは別のポリシー選択です。

`NoSchedule`はtaintを許容しない新しいPodの配置を防ぎますが、既存Podを退避しません。bootstrap-onlyルールに`defaultStatus`を設定しないでください。このリリースでは組み合わせが拒否されます。ネイティブCRD検証に合格しても、reporterの健全性、admission webhookの動作、すべてのEKSノード種別での稼働が証明されたわけではありません。この監査ではnode label、taint、コントローラー、conditionを変更していません。

[リリースv0.5.0](https://github.com/kubernetes-sigs/node-readiness-controller/releases/tag/v0.5.0) · [強制とdry-runの意味](https://github.com/kubernetes-sigs/node-readiness-controller/blob/v0.5.0/docs/book/src/user-guide/concepts.md) · [Reporter設定](https://github.com/kubernetes-sigs/node-readiness-controller/blob/v0.5.0/docs/book/src/reference/reporter-configuration.md)

---

<span id="4-workload-debugging"></span>

## 4. ワークロードのデバッグ

### Podとコンテナの状態

Pod phaseはPending、Running、Succeeded、Failed、Unknownです。コンテナ状態はWaiting、Running、Terminatedです。ContainerCreatingやCrashLoopBackOffはreason／表示情報であり、Pod phaseが増えたものではありません。RunningはReadyと同じ意味ではありません。restart policyによりPod内でコンテナが再起動する場合はありますが、terminalなFailed PodがPendingに戻るわけではありません。コントローラーによる置き換えではUIDの異なる新しいPodが作られます。

<!-- Content audit: diagram prose needs parent repair; see eks-advanced-debugging/diagram-review.json.
![State machine showing a Kubernetes Pod's lifecycle -- Pending to ContainerCreating to Running to Succeeded on the happy path, with ContainerCreating and Running able to fail into Failed, and Failed pods returning to Pending under the restart policy -- annotated with the major failure causes at each state.](../.gitbook/assets/en-eks-11-eks-advanced-debugging-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-11-eks-advanced-debugging-2.html)
-->

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
POD_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json)
printf '%s\n' "$POD_JSON" | jq '{
  name:.metadata.name,uid:.metadata.uid,owners:.metadata.ownerReferences,node:.spec.nodeName,
  phase:.status.phase,reason:.status.reason,conditions:.status.conditions,
  containers:.status.containerStatuses,initContainers:.status.initContainerStatuses,
  ephemeralContainers:.status.ephemeralContainerStatuses
}'
POD_UID=$(printf '%s\n' "$POD_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --field-selector "involvedObject.uid=$POD_UID" --sort-by='.metadata.creationTimestamp'
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" logs "$POD_NAME" -c "$CONTAINER_NAME" \
  --since=15m --tail=200
```
```bash
# Separate read: this can fail when no previous container log exists.
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" logs "$POD_NAME" -c "$CONTAINER_NAME" \
  --previous --tail=200
```

前のログは、選択したコンテナの直近に終了したインスタンスのものであり、再起動履歴全体ではありません。ログローテーションやPod削除によりログが利用できなくなる場合があります。収集時にはPod UIDと時刻を記録し、その間の置き換え有無を確認します。init／sidecar／ephemeral containerでは異なる障害が起きる場合があります。ログと状態メッセージには機密情報が含まれる可能性があるため、収集した証跡は非公開にしてください。診断の近道として、すべての環境変数やアプリケーション設定ファイルを出力しないでください。

### kubectl debug：3種類の異なる操作

Ephemeral containerは既存Podを変更します。--copy-toは別のPodを作成し、node/はノード上に診断用Podを作成します。いずれも変更を伴う操作であり、適切なRBAC／admission権限が必要です。確認対象のkubectl 1.36.2では、デフォルトprofileはgeneralです。自動的にprivilegedになるわけではありません。また、host namespace／filesystemへのアクセスはprivileged=trueとは別の概念です。

#### Ephemeral container

```bash
# MUTATION: adds a permanent-to-this-Pod-spec ephemeral-container entry.
: "${DEBUG_IMAGE:?Use a reviewed non-root diagnostic image with a compatible shell}"
: "${DEBUG_CONTAINER_NAME:?Choose an unused container name}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" debug "$POD_NAME" -it \
  --container="$DEBUG_CONTAINER_NAME" --target="$CONTAINER_NAME" \
  --image="$DEBUG_IMAGE" --profile=restricted -- sh
```

restricted profileはcapabilityを削除し、権限昇格を禁止し、non-root実行／RuntimeDefault seccompを要求します。イメージ／ユーザー／shellが対応している必要があり、root専用の任意のBusyBoxイメージが必ず起動するとは限りません。--targetはランタイムが対応する場合にtargetのprocess namespaceだけを要求します。アプリケーションのfilesystem／環境変数を複製したり、権限を迂回したりはしません。終了するとdebug processは終わりますが、既存Podのspecに追加されたephemeral-containerの記録は削除できません。

#### Podのコピー

```bash
# MUTATION: copy only a reviewed reproduction Pod; inspect all side effects first.
: "${DEBUG_POD_NAME:?Choose a new owned Pod name in the same namespace}"
: "${DEBUG_IMAGE:?Use a reviewed diagnostic image that provides sleep}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" debug "$POD_NAME" \
  --copy-to="$DEBUG_POD_NAME" --container="$CONTAINER_NAME" --image="$DEBUG_IMAGE" \
  --keep-init-containers=false --keep-labels=false --keep-annotations=false \
  --share-processes=true --profile=general -- sleep 3600
```

native CLIの確認では、この操作が選択したコンテナのimage／commandを置き換え、init containerを削除し、ServiceAccountを維持して共有process namespaceを有効にすることを確認しました。そのほかの通常コンテナ、環境変数／Secret参照、volumeは残り、実行されたり同じデータにアクセスしたりする場合があります。コピーは同じnamespaceに残りますが、別のノードにスケジュールされることがあり、隔離されたデータクローンではありません。使用前に、admissionによる変更、副作用、アイデンティティ、永続volume、cleanupをレビューしてください。general profileのcapabilityがnamespaceポリシーで拒否される場合があります。ポリシーを黙って緩和しないでください。

#### ノードの診断

```bash
# MUTATION: privileged host diagnostic Pod, only where this access is authorized.
: "${NODE_NAME:?Use the exact reviewed Node}"
: "${NODE_DEBUG_IMAGE:?Use a reviewed image with nsenter}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" debug "node/$NODE_NAME" -it \
  --image="$NODE_DEBUG_IMAGE" --profile=sysadmin \
  -- nsenter -t 1 -m -- journalctl -u kubelet --since "15 minutes ago" -n 200 --no-pager
```

Node debugはhost rootを/hostにmountし、host namespaceを使います。明示的なsysadmin profileではprivileged実行が追加されます。実行コマンドがログを読むだけでも、ホストへの広範なアクセス権が付与されます。必要な診断ツールがイメージに含まれている必要があります。Auto Modeのユーザーガイドはこの経路を説明していますが、通常のSSHアクセスは利用できません。ほかのOS／ノード種別では対応するアクセス方法を使います。kubelet／ランタイム／ネットワーキングが壊れている場合、新しいdebug Podが起動できるとは限りません。

実際の操作で作成されたdebug Podの名前／UIDを記録します。証跡を確認した後に削除するのは、その別個のPodだけです。ephemeral containerを「片付ける」ためにアプリケーションPodを削除しないでください。

```bash
# MUTATION: remove only the separately created debug Pod after checking its identity.
: "${DEBUG_POD_NAME:?}"; : "${EXPECTED_DEBUG_UID:?Use the UID recorded at creation}"
ACTUAL_DEBUG_UID=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$DEBUG_POD_NAME" \
  -o jsonpath='{.metadata.uid}')
test "$ACTUAL_DEBUG_UID" = "$EXPECTED_DEBUG_UID" || { echo "Debug Pod changed; stop" >&2; exit 1; }
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" delete pod "$DEBUG_POD_NAME" --timeout=2m
```

UID確認は安全性を高める手順ですが、削除の原子的な事前条件ではありません。確認と削除の間に名前が再利用されないよう調整してください。この監査ではdebug container、privileged workload、ノードコマンドを実行していません。native CLIのテストでは合成したloopback API応答だけを使いました。

### Deploymentのロールアウト管理

```bash
# Read-only rollout evidence.
: "${DEPLOYMENT_NAME:?Set the owned Deployment}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout status \
  "deployment/$DEPLOYMENT_NAME" --timeout=2m
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout history "deployment/$DEPLOYMENT_NAME"
```
```bash
# MUTATION: workload revision rollback, not database/PVC/control-plane rollback.
set -euo pipefail
: "${REVIEWED_REVISION:?Set an inspected compatible revision}"
[[ "$REVIEWED_REVISION" =~ ^[1-9][0-9]*$ ]]
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout undo \
  "deployment/$DEPLOYMENT_NAME" --to-revision="$REVIEWED_REVISION"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout status \
  "deployment/$DEPLOYMENT_NAME" --timeout=5m
```

timeout／失敗は調査すべき証跡であり、成功ではありません。GitOpsやほかのreconcilerと調整してください。rollbackでデータベースが復元されたり、schema変更が取り消されたりするわけではありません。Deploymentのpause／resumeはロールアウトの進行を制御するもので、HPAやすべてのPod作成を停止しません。rollout restartは同じimage参照でもPod templateを意図的に変更し、Podを置き換えます。tagで固定されていないイメージは、別の成果物に解決される可能性があります。triageでrestart／undo／scaleコマンドをまとめて実行せず、namespaceとDeploymentを正確に指定し、レビュー済みの更新計画を使ってください。

### HPA／VPAのスケーリングに関する問題

```bash
# Read-only: use the actual scaler names and workload namespace.
: "${HPA_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get hpa "$HPA_NAME" -o yaml
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" describe hpa "$HPA_NAME"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods --containers
```
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
  namespace: diagnostics-example
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app
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
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
```
```bash
# VPA is a separately installed controller/CRD, not built into EKS.
: "${VPA_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get vpa "$VPA_NAME" -o json | jq '{
  target:.spec.targetRef,updatePolicy:.spec.updatePolicy,resourcePolicy:.spec.resourcePolicy,
  recommendation:.status.recommendation,conditions:.status.conditions
}'
```

HPAの例では、既存のDeploymentとresource metrics provider、さらに対象コンテナの適切なCPU／memory requestsが必要です。utilizationの目標値はrequestsに対する割合であり、limitsに対する割合ではありません。複数のメトリクスを使う場合、最大の推奨replica数が選択されます。メトリクス欠落／エラーも判断に影響します。memory utilizationだけであらゆるleak／OOMを解決できるわけではありません。scale-down stabilizationとrate policyは停止スイッチではありません。

VPAは別途インストールします。実際のrecommendation、conditions、update mode、対応リリースを確認してください。旧来のAuto update-mode名は現行ガイダンスでは非推奨です。recommendations-onlyのOffや、レビュー済みのupdate modeなど文書化されたモードを選びます。HPAが使うrequestの分母をVPAが変更する場合は、連携せずに動作させないでください。

### Probeの設定

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-probe-example
  namespace: diagnostics-example
spec:
  containers:
  - name: app
    image: registry.example.com/owned/app:replace-with-reviewed-digest
    ports:
    - name: http
      containerPort: 8080
    startupProbe:
      httpGet:
        path: /healthz
        port: http
      initialDelaySeconds: 10
      periodSeconds: 5
      failureThreshold: 30
    livenessProbe:
      httpGet:
        path: /healthz
        port: http
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
    readinessProbe:
      httpGet:
        path: /ready
        port: http
      periodSeconds: 5
      timeoutSeconds: 3
      successThreshold: 1
      failureThreshold: 3
    resources:
      requests:
        cpu: 250m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 512Mi
```

placeholderイメージを置き換え、実際のhealth endpointを実装します。この単独Podはschema例であり、複製された本番ワークロードではありません。Startup probeが成功するまでliveness／readiness probeは開始されません。初期遅延の後、5秒間隔で30回試す設定は概算上の起動時間であり、150秒で必ず終了する厳密な期限ではありません。Readiness failureはServiceルーティング上のready状態を解除しますが、コンテナは再起動しません。外部依存先が遅いというだけで、正常なプロセスをliveness probeで再起動しないでください。shutdown、resource pressure、実際の応答時間は別々に検証します。

[Podのライフサイクル](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/) · [稼働中Podのデバッグ](https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/) · [HPAの動作](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/) · [VPAモード](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler)

---

<span id="5-networking-diagnostics"></span>

## 5. ネットワーク診断

### VPC CNIとIP割り当て

まずノード／ネットワークの実装を特定してください。以下のaws-node設定は、標準Amazon VPC CNIを使う場合に適用されます。Auto Modeには管理対象の独自ネットワーキング／NodeClass制御があり、aws-node DaemonSetを変更してもAuto Modeノードの設定にはなりません。Windows、Fargate、Hybrid Nodesでは適用範囲と診断方法が異なります。初期確認ではアカウント／コンテキストのguardを使い、対象ノード／namespaceを正確に指定します。

```bash
# Standard Amazon VPC CNI on applicable nodes, not an Auto Mode control interface.
: "${KUBE_CONTEXT:?}"; : "${AWS_REGION:?}"; : "${INSTANCE_ID:?Use the inspected EC2 node ID}"
kubectl --context "$KUBE_CONTEXT" -n kube-system get daemonset aws-node -o json | jq '{
  containers:[.spec.template.spec.containers[] | {name,image,settings:[
    .env[]? | select(.name | IN("ENABLE_PREFIX_DELEGATION","WARM_PREFIX_TARGET","WARM_IP_TARGET",
      "MINIMUM_IP_TARGET","AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG","ENI_CONFIG_LABEL_DEF"))
  ]}]
}'
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods -l k8s-app=aws-node -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=aws-node \
  -c aws-node --since=15m --tail=100 --prefix
aws ec2 describe-network-interfaces --region "$AWS_REGION" \
  --filters "Name=attachment.instance-id,Values=$INSTANCE_ID" \
  --query 'NetworkInterfaces[].{ID:NetworkInterfaceId,Subnet:SubnetId,Description:Description,IPv4:PrivateIpAddresses[].PrivateIpAddress,IPv4Prefixes:Ipv4Prefixes,IPv6Prefixes:Ipv6Prefixes,Groups:Groups}'
```
```bash
# Read-only: use subnets actually selected by the node/provisioner, not all account subnets.
: "${SUBNET_ID:?Set an inspected subnet ID}"
aws ec2 describe-subnets --region "$AWS_REGION" --subnet-ids "$SUBNET_ID" \
  --query 'Subnets[].{ID:SubnetId,VPC:VpcId,AZ:AvailabilityZone,CIDR:CidrBlock,AvailableIPv4:AvailableIpAddressCount}'
```

ENIのdescriptionだけでは所有者を判定できません。確認したinstance／subnet IDを使い、カスタムネットワーキングやPod ENIも含めてください。subnetの空きアドレス数だけでは連続したprefixが利用可能とは証明できません。またVPC CIDRを追加しただけでは、Podネットワーキングが設定されるわけではありません。

### Prefix Delegation

対応するLinux／Nitro／CNI構成でprefix delegationを使うと、IP密度と割り当て動作を改善できます。連続したprefix用のアドレス空間／予約、ENI／prefix上限、ノードのmaxPods／allocatable Pods、移行準備状況を確認します。稼働中ノードで安易に有効化せず、IPv4の空き数だけから利用可能容量を推定しないでください。

以下はレビュー用の**設定断片**です。実際に対応するアドオン／chartの設定とマージしてください。既存設定をすべて置き換える例ではありません。

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```

設定済みのWARM_IP_TARGET／MINIMUM_IP_TARGETはWARM_PREFIX_TARGETより優先されます。warm targetは予備のアドレス／prefixを保持するもので、ノードcapacityを予約したり、空きがない／断片化したsubnetを修復したりはしません。管理者と保存済み設定を確認してから、制御されたrolloutを計画し、その後に新しいPodと実際のIPAM状態を検証します。

### カスタムネットワーキング

CNIモードを変更する前に、重複しないVPCアドレス空間、AZごとに実際に使うPod subnet、ルーティング／egress、Security Group、移行に必要な余裕容量を準備します。元のCIDR／subnet作成と環境変数の切り替えだけの2行は、運用手順全体を示していません。既存subnetのIPv4 CIDRはその場で拡張できません。以下の標準的なENIConfig方式とAuto Modeのネットワーキング制御は別のものです。

```json
{
  "env": {
    "AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG": "true",
    "ENI_CONFIG_LABEL_DEF": "topology.kubernetes.io/zone"
  }
}
```
```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: ap-northeast-2a
spec:
  securityGroups:
  - sg-0123456789abcdef0
  subnet: subnet-0123456789abcdef0
```

ENIConfigの例は1つのAZだけを対象とし、IDはplaceholderです。zone単位で選択する場合は、対象となる各AZに正しい設定を作り、ノードに対応するlabelが付いていることを確認します。AZごとに複数のPod subnetを使う場合は、明示的な選択方式を設計する必要があります。Pod用Security Groupの設定で適用されるgroupが変わる場合があるため、インストール済みCNIの優先順位を調べてください。古いcapacityを廃止する前に、コントローラーの設定、新規ノードへのrollout、Podの配置を検証します。全体の構成は[ネットワーキングガイド](03-eks-networking-part1.md)を参照してください。

### CoreDNSとresolverのコンテキスト

Auto Modeのみのクラスターでは、CoreDNSはノードシステムサービスとして稼働します。Auto Mode以外のノードが混在するクラスターでは、そのノード向けDeploymentを維持します。Auto ModeだけのクラスターにDeploymentがないことは、それ自体ではDNS障害を意味しません。Deployment方式のDNSでは次を確認します。

```bash
# CoreDNS Deployment on standard/mixed clusters; Auto Mode node-system DNS differs.
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods -l k8s-app=kube-dns -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=kube-dns \
  --since=15m --tail=100 --prefix
kubectl --context "$KUBE_CONTEXT" -n kube-system get configmap coredns -o yaml
# Inspect the actual resolver context in an owned application container with these tools.
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- cat /etc/resolv.conf
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- nslookup kubernetes.default.svc.cluster.local.
```

CoreDNSは、該当するlogging設定を有効にしない限り、すべてのDNS問い合わせを記録しません。新規のテストPodは、障害が起きているワークロードと異なるnamespace／node／DNS／identity／policy経路を使う場合があります。障害が起きたワークロード自身のresolverコンテキストで確認し、絶対名を検証するときは末尾にdotを付けたFQDNを使います。

次のndots=2は実験の値であり、レイテンシーに対する万能策ではありません。search動作を変更し、部分修飾名の解決に影響する場合があります。libc、言語のresolver、アプリケーションのcache動作はそれぞれ異なります。single-request-reopenのようなglibc固有オプションを、移植可能な前提として扱わないでください。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: dns-options-example
  namespace: diagnostics-example
spec:
  dnsPolicy: ClusterFirst
  dnsConfig:
    options:
    - name: ndots
      value: '2'
    - name: timeout
      value: '2'
    - name: attempts
      value: '3'
  containers:
  - name: app
    image: registry.example.com/owned/app:replace-with-reviewed-digest
```

以下にCorefileの例を示します。インストール済みversion、必須plugin、カスタムzone／forwarder、管理対象アドオンの設定と比較してください。稼働中のConfigMapを丸ごと上書きしないでください。cache、max_concurrent、lameduckの値は、実際のトラフィック／healthで検証する必要があります。pods insecureはKubernetes pluginのPod recordモードであり、Kubernetes APIのTLS／認証を無効にするスイッチではありません。

```text
.:53 {
    errors
    health {
        lameduck 5s
    }
    ready
    kubernetes cluster.local in-addr.arpa ip6.arpa {
        pods insecure
        fallthrough in-addr.arpa ip6.arpa
        ttl 30
    }
    prometheus :9153
    forward . /etc/resolv.conf {
        max_concurrent 1000
    }
    cache 30
    loop
    reload
    loadbalance
}
```

### ServiceとEndpointSliceの検証

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${SERVICE_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get service "$SERVICE_NAME" -o json | jq '{
  name:.metadata.name,type:.spec.type,clusterIP:.spec.clusterIP,ipFamilies:.spec.ipFamilies,
  externalName:.spec.externalName,selector:.spec.selector,ports:.spec.ports,
  trafficDistribution:.spec.trafficDistribution,externalTrafficPolicy:.spec.externalTrafficPolicy
}'
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o json | jq '[.items[] | {
    name:.metadata.name,addressType,ports,
    endpoints:[.endpoints[]? | {addresses,conditions,nodeName,zone,targetRef}]
  }]'
```

現行endpointの調査には、非推奨になったEndpoints APIではなくEndpointSliceを使います。Serviceのselector／port／targetPort、address family、endpointのready／serving／terminating conditionsを確認します。Headless、ExternalName、selectorのないServiceでは動作が異なります。endpoint addressの存在は、そのアドレスが意図したトラフィックを受け取れる証明ではありません。またServiceのportがアプリケーションのcontainer portと常に同じとは限りません。

### NetworkPolicyのAND／ORロジック

1つのpeer内にあるnamespaceSelectorとpodSelectorはAND条件です。別々のpeer／ruleはOR条件です。podSelectorだけのpeerは、そのポリシーと同じnamespaceのPodを選択します。適用されるすべてのNetworkPolicyの許可ルールは加算され、制限的なポリシー1つが別ポリシーのより広い許可を上書きすることはありません。manifestをfirewallとして扱う前に、実際のCNI／ノード種別における強制機能とモードを確認してください。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: reviewed-api-policy
  namespace: diagnostics-example
spec:
  podSelector:
    matchLabels:
      app: api-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: monitoring
      podSelector:
        matchLabels:
          app.kubernetes.io/name: prometheus
    ports:
    - protocol: TCP
      port: 9090
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```
```bash
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get networkpolicies -o yaml
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods --show-labels
kubectl --context "$KUBE_CONTEXT" get namespaces --show-labels
```

この例では該当するCoreDNS Pod宛てのTCP／UDP DNSを追加します。databaseのみを許可するegressでは、DNSが別途ないと名前解決できません。Node-local／Auto Mode DNSでは経路が異なるため、モードごとの検証が必要です。実際の監視／database labelとportに合わせ、レビュー済みの外部依存先のみ追加してください。このポリシーは例示であり、本番向けの許可リストとして検証済みではありません。

### 範囲を限定したネットワークテスト

```bash
# An intentional, bounded request from the actual workload context with curl installed.
: "${HEALTH_URL:?Set the owned safe health-check URL}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" -c "$CONTAINER_NAME" \
  -- curl --silent --show-error --connect-timeout 5 --max-time 10 \
  --output /dev/null --write-out 'HTTP status: %{http_code}\n' "$HEALTH_URL"
```
```bash
# In an approved diagnostic context with the named tools.
: "${SERVICE_FQDN:?Set the exact owned service DNS name}"
dig +time=2 +tries=1 "$SERVICE_FQDN"
# Packet capture needs the appropriate capabilities/privileges and an owned target.
: "${TARGET_IP:?Set one reviewed peer IP}"
umask 077
timeout 30 tcpdump -i any -nn -c 100 -s 96 "host $TARGET_IP and port 443" -w owned-capture.pcap
# Separate deliberate load test: only against an agreed iperf3 server.
: "${IPERF_SERVER:?Set the owned test server}"
iperf3 -c "$IPERF_SERVER" -p 5201 -t 10 -P 1 -b 10M
```

前述のdebugワークフローに従い、レビュー済みの診断イメージ／ツールを選択してください。netshoot Podの作成は受動的な観測ではなく、変更を伴う操作です。packet captureにはrootユーザーだけでなくcapability／privilegeが必要です。範囲を限定したcaptureにも機密ヘッダー／データが含まれる場合があります。非公開で保管し、共有前に内容を確認してください。dig +traceは、ワークロードに設定されたresolverだけでなく、直接の反復DNS経路を試します。iperf3は意図的にトラフィックを生成します。そのthroughputはnetwork latencyではなく、この監査で測定した結果でもありません。

[Prefix mode](https://docs.aws.amazon.com/eks/latest/best-practices/prefix-mode-linux.html) · [カスタムネットワーキング](https://docs.aws.amazon.com/eks/latest/best-practices/custom-networking.html) · [NetworkPolicyの意味](https://kubernetes.io/docs/concepts/services-networking/network-policies/) · [EndpointSlice](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)

---

<span id="6-storage-troubleshooting"></span>

## 6. ストレージのトラブルシューティング

### Driverと権限の特定

bind済みPVのspec.csi.driverとvolumeHandle、StorageClassのprovisionerを確認します。標準EBS driverはebs.csi.aws.comです。Auto Modeはebs.csi.eks.amazonaws.comと管理対象コントローラーを使うため、標準コントローラーDeploymentがない場合があります。以下の標準driver用ログコマンドを使うには、そのdriverがインストールされている必要があります。EBSはFargate PodやEKS Hybrid Nodesにmountできません。標準コントローラーをFargateに配置しても、このdata plane上の制約は変わりません。

```bash
# Read-only: identify the actual installed driver and workload owner first.
kubectl --context "$KUBE_CONTEXT" get csidrivers
: "${CSI_NAMESPACE:?Set the namespace of the installed standard CSI controller}"
kubectl --context "$KUBE_CONTEXT" -n "$CSI_NAMESPACE" get deployments,daemonsets,pods -o wide
: "${CSI_CONTROLLER_NAME:?Use an observed controller Deployment name}"
: "${CSI_CONTAINER_NAME:?Use the CSI plugin container name}"
kubectl --context "$KUBE_CONTEXT" -n "$CSI_NAMESPACE" logs "deployment/$CSI_CONTROLLER_NAME" \
  -c "$CSI_CONTAINER_NAME" --since=15m --tail=100
```
```bash
# Inspect only the role actually used by the standard EBS CSI controller.
: "${CSI_ROLE_NAME:?Set the reviewed role name}"
aws iam get-role --role-name "$CSI_ROLE_NAME" --query Role.AssumeRolePolicyDocument
aws iam list-attached-role-policies --role-name "$CSI_ROLE_NAME"
aws iam list-role-policies --role-name "$CSI_ROLE_NAME"
```

現在のEKSガイドは、標準driverの権限についてAmazonEBSCSIDriverPolicyV2を確認するよう勧めています。このポリシーは、driver所有権tagとCSI移行済みvolume tagへの対応を使ってvolume／snapshot管理の範囲を制限します。古いポリシーを置き換える前に、移行と既存resourceのtagを確認してください。一般的な修正として、すべての変更権限を含む無制限なResource: *ポリシーを付けないでください。AWSの一部read／list操作でwildcard resourceが必要なことと、広範な変更権限を与えることは別です。

想定上のnode identityではなく、実際のPod IdentityまたはIRSAロール／trust policyを使ってください。顧客管理KMS keyを使うには、該当するkey policy／grant／encrypt／decrypt権限が必要です。文書化されたCreateGrantのconditionにはkms:GrantIsForAWSResourceが含まれます。volumeの作成権限があるだけでは、選択したKMS keyの利用や対象ノードへのattachが許可されている証明にはなりません。これらの診断コマンドはIAMを変更しません。

### EFSのMount TargetとAccess Point

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${FILE_SYSTEM_ID:?Use the owned EFS filesystem}"
aws efs describe-file-systems --region "$AWS_REGION" --file-system-id "$FILE_SYSTEM_ID"
aws efs describe-mount-targets --region "$AWS_REGION" --file-system-id "$FILE_SYSTEM_ID"
: "${MOUNT_TARGET_ID:?Use the relevant mount target}"
aws efs describe-mount-target-security-groups --region "$AWS_REGION" --mount-target-id "$MOUNT_TARGET_ID"
: "${EFS_SECURITY_GROUP_ID:?Use an observed mount-target security group}"
aws ec2 describe-security-groups --region "$AWS_REGION" --group-ids "$EFS_SECURITY_GROUP_ID"
```

filesystem種別／Region、到達可能なmount target、DNS、TCP 2049のrule、両方向のネットワーク経路を確認します。Regional EFSとOne Zoneでは障害ドメインが異なります。IAM認可、access pointのPOSIX identity／ディレクトリ権限、Pod security contextは別々の層です。以下はplaceholder IDを使う既存filesystem用の設定例であり、filesystem／role／network全体を構築する手順ではありません。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: reviewed-efs
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: '700'
  gidRangeStart: '1000'
  gidRangeEnd: '2000'
  basePath: /diagnostics-example
mountOptions:
- tls
reclaimPolicy: Retain
```
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: efs-claim
  namespace: diagnostics-example
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: reviewed-efs
  resources:
    requests:
      storage: 5Gi
```

5GiのPVC要求は、EFSが強制する容量quotaではありません。Access Pointでサーバー側POSIX identityを強制できます。client PodのUIDだけからアクセスを判断したり、無差別なchmodで解決したりしないでください。TLSによるmount暗号化とfilesystem保存時の暗号化は別です。Retainを使う場合は明示的なaccess point／データcleanup計画が必要で、課金対象リソースが残る場合があります。Fargate EFSには別のstatic provisioning経路があります。このdynamic provisioningの例がすべてのノード種別に適用されるとは限りません。

### PVC／PVの状態と削除保護

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${PVC_NAME:?Set the owned claim name}"
PVC_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pvc "$PVC_NAME" -o json)
printf '%s\n' "$PVC_JSON" | jq '{
  name:.metadata.name,namespace:.metadata.namespace,uid:.metadata.uid,
  deleting:.metadata.deletionTimestamp,finalizers:.metadata.finalizers,
  phase:.status.phase,conditions:.status.conditions,volumeName:.spec.volumeName,
  hasStorageClassName:(.spec | has("storageClassName")),
  storageClassName:.spec.storageClassName,accessModes:.spec.accessModes,resources:.spec.resources
}'
PVC_UID=$(printf '%s\n' "$PVC_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --field-selector "involvedObject.uid=$PVC_UID" --sort-by='.metadata.creationTimestamp'
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -o json | jq --arg claim "$PVC_NAME" '[
  .items[] | select(any(.spec.volumes[]?; .persistentVolumeClaim.claimName? == $claim)) |
  {name:.metadata.name,uid:.metadata.uid,owners:.metadata.ownerReferences,
   node:.spec.nodeName,phase:.status.phase,deleting:.metadata.deletionTimestamp}
]'
PV_NAME=$(printf '%s\n' "$PVC_JSON" | jq -r '.spec.volumeName // empty')
if [ -z "$PV_NAME" ]; then
  echo "No bound PV: inspect StorageClass, consumer scheduling and provisioning events."
else
  kubectl --context "$KUBE_CONTEXT" get pv "$PV_NAME" -o json | jq '{
    name:.metadata.name,uid:.metadata.uid,claimRef:.spec.claimRef,
    deleting:.metadata.deletionTimestamp,finalizers:.metadata.finalizers,
    reclaimPolicy:.spec.persistentVolumeReclaimPolicy,csi:.spec.csi,nodeAffinity:.spec.nodeAffinity
  }'
  kubectl --context "$KUBE_CONTEXT" get volumeattachments -o json | jq --arg pv "$PV_NAME" '[
    .items[] | select(.spec.source.persistentVolumeName == $pv) |
    {name:.metadata.name,driver:.spec.attacher,node:.spec.nodeName,status:.status}
  ]'
fi
```

PVC名はnamespace内で一意です。consumer検索ではclaimのnamespaceを使います。claim／PVのUID、controller owner、VolumeAttachment、finalizerを調べます。deletion timestampが付くと表示上はTerminatingになりますが、PVCのstatus.phaseが新しく増えるわけではありません。WaitForFirstConsumerでは、スケジュール可能なconsumerができるまでPendingが想定内の場合があります。storageClassNameを省略する場合と、明示的に空文字列を指定する場合は異なり、後者はclassを使わない指定です。

削除を完了させるためにPVC／PVのfinalizerをすべてnullにしないでください。PVC保護、CSIによるdetach／delete処理、reclaim policyはライフサイクルの異なる部分を保護します。まず、consumer（Podを再作成する可能性のあるcontrollerを含む）、attachment状態、controller error、backup、データの所有者を特定してください。最終手段のorphan修復では、driver固有の復旧手順とデータ／attachment状態の確認が必要です。メタデータを削除しても、安全なdetachやデータ復元は行われません。Deleteで実データが削除される場合があります。Retainもbackupの代わりではありません。

### WaitForFirstConsumer、トポロジー、暗号化

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: reviewed-ebs-wffc
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: 'true'
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
```

これは標準EBS CSI provisioner用です。WaitForFirstConsumerは初回のprovision／bindをschedulerの制約に合わせますが、EBSをAZ間で利用可能にしたり、障害のあるAZに固定されたvolumeを修復したりしません。ap-northeast-2a／2cのようにworkloadの配置先AZを制限する場合は、scheduler制約を実際のCSI topology／利用可能capacityに合わせてください。最初のPV affinity expressionが必ずAZを示すとは限りません。またPodに要求したaffinityは、Podが実際に配置された場所とは限りません。

```bash
# Use the actual consumer node, not the Pod's requested node-affinity text.
: "${NODE_NAME:?Set an observed consumer node}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o json | jq '{
  name:.metadata.name,providerID:.spec.providerID,
  topologyLabels:(.metadata.labels | with_entries(select(.key | contains("topology"))))
}'
kubectl --context "$KUBE_CONTEXT" get csinode "$NODE_NAME" -o json | jq '.spec.drivers'
# For an actual EBS-backed PV, inspect the volume handle and Region before this lookup.
: "${AWS_REGION:?}"; : "${EBS_VOLUME_ID:?Set the inspected EBS volume ID}"
aws ec2 describe-volumes --region "$AWS_REGION" --volume-ids "$EBS_VOLUME_ID" \
  --query 'Volumes[].{ID:VolumeId,AZ:AvailabilityZone,State:State,Encrypted:Encrypted,KMS:KmsKeyId,Attachments:Attachments}'
```

Auto Modeでは別のprovisionerとノード互換性の前提を使います。**encrypted: "true"を明示し、作成後のvolume／KMS keyを確認してください**。現在のAuto Mode StorageClass parameter一覧では、encryptedのデフォルトはfalseです。Auto Modeノードのroot／data diskが暗号化されていても、各workload PVCの暗号化が証明されたわけではありません。StorageClassを変更しても、既存volumeの暗号化は遡って変更されません。

既存EBS volumeは、StorageClassにWaitForFirstConsumerがあるだけでAZをまたいでattachできるわけではありません。移行／復旧では、文書化されたsnapshotまたは制御されたstatic-volume手順、正しい所有tag／IAM、アプリケーション整合性を保つデータ処理が必要です。driver名だけを変更する方法ではありません。Snapshot controller／CRDは別の前提条件です。またsnapshotを作成しただけではrestoreが機能する証明になりません。ReadWriteOnceは1つのノードからのアクセスを許可するもので、必ず「Pod 1つ」ではありません。Auto ModeのSELinux隔離によって、Pod間に追加の制約が加わる場合もあります。変更前にデータを保護し、想定するaccess／整合性モデルを確認してください。

[EBS CSI／IAM](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html) · [管理ポリシーの範囲](https://docs.aws.amazon.com/eks/latest/userguide/security-iam-awsmanpol.html) · [Auto Modeのparameter](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html) · [PVのライフサイクル](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) · [EFS CSI](https://github.com/kubernetes-sigs/aws-efs-csi-driver)

---
<span id="7-observability-architecture"></span>

## 7. 可観測性アーキテクチャ

### 既存の収集設定を確認する

インシデント対応を急ぐあまり、旧バージョン1.0.0のアドオンをインストールしないでください。[監視のセットアップガイド](06-eks-monitoring-logging.md)を参照し、現在互換性のあるアドオン／chartと収集の管理者を選びます。変更前にIAM／Pod Identity、ログ／メトリクスの設定、ノードへの適用範囲、自動計装／再起動の設定を確認してください。新しいOperatorリリースでアプリケーションの計装やrolloutに影響する場合があります。収集を二重に管理すると競合する可能性があります。

```bash
# Read-only: inspect the installed owner/version rather than installing during triage.
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"; : "${KUBE_CONTEXT:?}"
aws eks describe-addon --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --addon-name amazon-cloudwatch-observability \
  --query 'addon.{Version:addonVersion,Status:status,Issues:health.issues,Configuration:configurationValues,Role:serviceAccountRoleArn,PodIdentity:podIdentityAssociations}'
kubectl --context "$KUBE_CONTEXT" -n amazon-cloudwatch get pods,deployments,daemonsets -o wide
# If Helm owns the installation, inspect that existing release instead.
helm list -n amazon-cloudwatch --kube-context "$KUBE_CONTEXT"
```

アドオンが見当たらなくても、Helmが収集を管理している場合や、そのコンポーネントをインストールしていない場合があります。PodのRunningやアドオンのACTIVEだけでは、データ配信、監視範囲、利用者から見たhealthは証明されません。scrape target、IAM／network／TLS、取り込みエラー、保持期間、料金を確認してください。以下の例はこれらの前提条件を置いており、本番プラットフォームで検証済みではありません。

### PromQL：各メトリクスが示す内容を明確にする

クエリは、**単一クラスターで正しいlabelが設定されたデータセット**と、診断例で選んだnamespaceを前提とします。共有バックエンドでは、実際のcluster／job selectorを追加してください。cAdvisorとkube-state-metricsを収集する必要があります。クエリを書いただけでseriesが作られるわけではありません。aggregationでexporter instance labelを削除するのは、ここで示す範囲内だけです。timestamp、Pod／container identity、最終終了理由メトリクスを含むversionごとのメトリクス利用可否を確認してください。

#### コンテナごとのCFS throttled period割合

```promql
sum by (namespace,pod,container) (rate(container_cpu_cfs_throttled_periods_total{namespace="diagnostics-example",container!="",container!="POD"}[5m]))
/ on (namespace,pod,container) (sum by (namespace,pod,container) (rate(container_cpu_cfs_periods_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])) > 0)
```

#### throttled period割合の上位10コンテナ

```promql
topk(10, sum by (namespace,pod,container) (rate(container_cpu_cfs_throttled_periods_total{namespace="diagnostics-example",container!="",container!="POD"}[5m]))
/ on (namespace,pod,container) (sum by (namespace,pod,container) (rate(container_cpu_cfs_periods_total{namespace="diagnostics-example",container!="",container!="POD"}[5m])) > 0))
```

#### 最後に報告された終了理由がOOM（新規イベント数ではない）

```promql
max by (namespace,pod,container) (kube_pod_container_status_last_terminated_reason{namespace="diagnostics-example",reason="OOMKilled"} == 1)
```

#### 最後の終了理由がOOMだったrestartの直近増加分（OOM件数そのものではない）

```promql
(max by (namespace,pod,container) (increase(kube_pod_container_status_restarts_total{namespace="diagnostics-example"}[15m])) > 0)
and on (namespace,pod,container) (max by (namespace,pod,container) (kube_pod_container_status_last_terminated_reason{namespace="diagnostics-example",reason="OOMKilled"} == 1))
```

#### コンテナごとのworking set／正のmemory limit

```promql
max by (namespace,pod,container) (container_memory_working_set_bytes{namespace="diagnostics-example",container!="",container!="POD"})
/ on (namespace,pod,container)
max by (namespace,pod,container) (kube_pod_container_resource_limits{namespace="diagnostics-example",resource="memory",unit="byte"} > 0)
```

#### Podごとの通常コンテナrestart増加数の15分間の推定

```promql
sum by (namespace,pod) (max by (namespace,pod,container) (increase(kube_pod_container_status_restarts_total{namespace="diagnostics-example"}[15m])))
```

#### restart増加数が多い上位10 Pod

```promql
topk(10, sum by (namespace,pod) (max by (namespace,pod,container) (increase(kube_pod_container_status_restarts_total{namespace="diagnostics-example"}[15m]))))
```

#### 現在報告されているCrashLoopBackOff待機理由

```promql
max by (namespace,pod,container) (kube_pod_container_status_waiting_reason{namespace="diagnostics-example",reason="CrashLoopBackOff"} == 1)
```

#### Activeで削除中ではなくReady=falseのPod（Runningを含む）

```promql
((1 - max by (namespace,pod) (kube_pod_status_ready{namespace="diagnostics-example",condition="true"})) > 0)
and on (namespace,pod) (max by (namespace,pod) (kube_pod_status_phase{namespace="diagnostics-example",phase=~"Pending|Running|Unknown"} == 1))
unless on (namespace,pod) kube_pod_deletion_timestamp{namespace="diagnostics-example"}
```

CFS throttled periodはCPU utilizationでも、経過CPU時間に対する比率でもありません。memory比率は正のlimitが設定されたコンテナのみを含みます。limit／データの欠落はutilization 0を意味しません。increase()はcounter resetを考慮して外挿する推定値で、小数になる場合があります。changes(restarts_total)は観測した値の変化を数え、OOMイベントの件数ではありません。最後の終了理由とrestart増加の組み合わせは相関情報であり、OOMイベント数の正確な集計でもmemory leakの証明でもありません。CrashLoopBackOffは、すべてのrestartから推測せずwaiting reasonを直接確認します。

readinessクエリにはRunningでもNotReadyのPodが含まれ、terminal／削除中のPodは除かれます。これらの例は、scrape監視やtarget不存在の監視に代わるものではありません。seriesが返らないことを、ワークロードが正常である証明として扱わないでください。

### CloudWatch Logs Insights

各ブロックを、適切なロググループと時間範囲を指定して個別に実行します。kubernetes.* fieldはcollectorのschemaに依存するため、実際のレコードを確認してください。エラーメッセージの件数とOOMキーワードは診断上の手掛かりであり、request error率や障害履歴の全体を示しません。

#### request error率ではなく、エラーメッセージのサンプル

```text
fields @timestamp, @message, kubernetes.pod_name, kubernetes.namespace_name
| filter kubernetes.namespace_name = "diagnostics-example"
| filter @message like /error|Error|ERROR|exception|Exception|EXCEPTION/
| sort @timestamp desc
| limit 100
```

#### 選択したnamespace内の1つのPod

```text
fields @timestamp, @message
| filter kubernetes.namespace_name = "diagnostics-example" and kubernetes.pod_name = "REPLACE_WITH_OBSERVED_POD"
| sort @timestamp desc
| limit 100
```

#### ログ形式にそのfieldが定義されている場合のみ、アプリケーションの応答時間

```text
fields @timestamp, @message
| filter kubernetes.namespace_name = "diagnostics-example"
| parse @message /response_time=(?<response_time>\d+)ms/
| filter ispresent(response_time)
| stats avg(response_time) as avg_response_ms, max(response_time) as max_response_ms by bin(5m)
```

#### 相関確認が必要なOOM関連のログメッセージ

```text
fields @timestamp, @message
| filter @message like /OOMKilled|Out of memory|oom-kill/
| sort @timestamp desc
| limit 50
```

### PrometheusRuleの選択とアラート

release labelを、意図するPrometheusのruleSelectorで必要な値に置き換え、ruleNamespaceSelectorも確認してください。CRDが受け付けられただけでは、ruleが読み込まれたり通知が機能したりする証明になりません。閾値と継続時間はworkloadのSLOに合わせて調整する例です。アラートは自動削除／再起動を許可するものではありません。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: reviewed-eks-diagnostics
  namespace: monitoring
  labels:
    release: REPLACE_WITH_SELECTED_PROMETHEUS_RELEASE
spec:
  groups:
  - name: reviewed-eks-diagnostics
    rules:
    - alert: NodeNotReady
      expr: kube_node_status_condition{condition="Ready",status="true"} == 0
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: Node {{ $labels.node }} reports Ready=false/unknown; inspect the
          node condition and heartbeat.
    - alert: NodeMemoryPressure
      expr: kube_node_status_condition{condition="MemoryPressure",status="true"} ==
        1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Node {{ $labels.node }} reports MemoryPressure.
    - alert: NodeDiskPressure
      expr: kube_node_status_condition{condition="DiskPressure",status="true"} ==
        1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Node {{ $labels.node }} reports DiskPressure.
    - alert: PodCrashLooping
      expr: max by (namespace,pod,container) (kube_pod_container_status_waiting_reason{namespace="diagnostics-example",reason="CrashLoopBackOff"}
        == 1)
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: '{{ $labels.namespace }}/{{ $labels.pod }}/{{ $labels.container }}
          reports CrashLoopBackOff.'
    - alert: ActivePodNotReady
      expr: '((1 - max by (namespace,pod) (kube_pod_status_ready{namespace="diagnostics-example",condition="true"}))
        > 0)

        and on (namespace,pod) (max by (namespace,pod) (kube_pod_status_phase{namespace="diagnostics-example",phase=~"Pending|Running|Unknown"}
        == 1))

        unless on (namespace,pod) kube_pod_deletion_timestamp{namespace="diagnostics-example"}'
      for: 15m
      labels:
        severity: warning
      annotations:
        summary: Active Pod {{ $labels.namespace }}/{{ $labels.pod }} is not Ready.
    - alert: ContainerRecentOOM
      expr: '(max by (namespace,pod,container) (increase(kube_pod_container_status_restarts_total{namespace="diagnostics-example"}[15m]))
        > 0)

        and on (namespace,pod,container) (max by (namespace,pod,container) (kube_pod_container_status_last_terminated_reason{namespace="diagnostics-example",reason="OOMKilled"}
        == 1))'
      for: 0m
      labels:
        severity: warning
      annotations:
        summary: Recent restart and last reported OOM for {{ $labels.namespace }}/{{
          $labels.pod }}/{{ $labels.container }}; verify events.
    - alert: HighCPUThrottling
      expr: '(sum by (namespace,pod,container) (rate(container_cpu_cfs_throttled_periods_total{namespace="diagnostics-example",container!="",container!="POD"}[5m]))

        / on (namespace,pod,container) (sum by (namespace,pod,container) (rate(container_cpu_cfs_periods_total{namespace="diagnostics-example",container!="",container!="POD"}[5m]))
        > 0)) > 0.5'
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: More than 50% of CFS periods were throttled for {{ $labels.namespace
          }}/{{ $labels.pod }}/{{ $labels.container }}.
```
```bash
# Read-only: this rule must be selected by the intended Prometheus instance.
kubectl --context "$KUBE_CONTEXT" -n monitoring get prometheus -o json | jq '[
  .items[] | {name:.metadata.name,ruleSelector:.spec.ruleSelector,ruleNamespaceSelector:.spec.ruleNamespaceSelector}
]'
kubectl --context "$KUBE_CONTEXT" -n monitoring get prometheusrule reviewed-eks-diagnostics -o yaml
```

### ADOT Collector：明示的なpipelineと前提条件

この例は、レビュー対象のOperator 0.158.0のobject形式v1beta1設定とADOT 0.50.0のコンポーネントを使います。namespace、Operator／CRD、receiver TLS Secret、信頼するclient CA、適切に設定されたServiceAccount AWS identityを準備してください。以下のRoleはKubernetes Podの検出だけを許可し、X-Ray、CloudWatch Logs、AMPへのアクセス権限は付与しません。デプロイする前にexporter IAM権限と実際のRegion／log group／workspaceを確認してください。この例は実行済みでも、本番対応と実証済みでもありません。

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: adot-diagnostics
  namespace: diagnostics-example
```
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: adot-pod-discovery
  namespace: diagnostics-example
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - get
  - list
  - watch
```
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: adot-pod-discovery
  namespace: diagnostics-example
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: adot-pod-discovery
subjects:
- kind: ServiceAccount
  name: adot-diagnostics
  namespace: diagnostics-example
```
```yaml
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: adot-diagnostics
  namespace: diagnostics-example
spec:
  mode: deployment
  replicas: 1
  image: public.ecr.aws/aws-observability/aws-otel-collector:v0.50.0
  serviceAccount: adot-diagnostics
  env:
  - name: AWS_REGION
    value: us-west-2
  - name: AWS_EC2_METADATA_DISABLED
    value: 'true'
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: '1'
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
          grpc:
            endpoint: 0.0.0.0:4317
            tls:
              cert_file: /etc/otel/tls/tls.crt
              key_file: /etc/otel/tls/tls.key
          http:
            endpoint: 0.0.0.0:4318
            tls:
              cert_file: /etc/otel/tls/tls.crt
              key_file: /etc/otel/tls/tls.key
      prometheus:
        config:
          scrape_configs:
          - job_name: owned-pod-metrics
            scrape_interval: 30s
            kubernetes_sd_configs:
            - role: pod
              namespaces:
                names:
                - diagnostics-example
            relabel_configs:
            - source_labels:
              - __meta_kubernetes_pod_annotation_prometheus_io_scrape
              action: keep
              regex: 'true'
            - source_labels:
              - __meta_kubernetes_pod_phase
              action: keep
              regex: Running
            - source_labels:
              - __meta_kubernetes_pod_container_port_name
              action: keep
              regex: metrics
            - source_labels:
              - __meta_kubernetes_pod_container_port_protocol
              action: keep
              regex: TCP
            - source_labels:
              - __meta_kubernetes_pod_annotation_prometheus_io_path
              action: replace
              target_label: __metrics_path__
              regex: (.+)
            - source_labels:
              - __meta_kubernetes_namespace
              target_label: namespace
            - source_labels:
              - __meta_kubernetes_pod_name
              target_label: pod
            - source_labels:
              - __meta_kubernetes_pod_container_name
              target_label: container
    processors:
      memory_limiter:
        check_interval: 1s
        limit_percentage: 75
        spike_limit_percentage: 15
      batch:
        timeout: 30s
        send_batch_size: 8192
    exporters:
      awsxray:
        region: us-west-2
        local_mode: true
        no_verify_ssl: false
        index_all_attributes: false
        telemetry:
          enabled: false
      awsemf:
        region: us-west-2
        namespace: EKS/DiagnosticsExample
        log_group_name: /aws/eks/REPLACE_WITH_CLUSTER/otel-metrics
        log_stream_name: adot-diagnostics
        dimension_rollup_option: NoDimensionRollup
        resource_to_telemetry_conversion:
          enabled: false
      prometheusremotewrite:
        endpoint: https://aps-workspaces.us-west-2.amazonaws.com/workspaces/REPLACE_WITH_WORKSPACE_ID/api/v1/remote_write
        auth:
          authenticator: sigv4auth
        resource_to_telemetry_conversion:
          enabled: false
    extensions:
      sigv4auth:
        region: us-west-2
        service: aps
      health_check:
        endpoint: 0.0.0.0:13133
    service:
      extensions:
      - sigv4auth
      - health_check
      pipelines:
        traces:
          receivers:
          - otlp
          processors:
          - memory_limiter
          - batch
          exporters:
          - awsxray
        metrics:
          receivers:
          - otlp
          - prometheus
          processors:
          - memory_limiter
          - batch
          exporters:
          - awsemf
          - prometheusremotewrite
```
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: adot-otlp-ingress
  namespace: diagnostics-example
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/managed-by: opentelemetry-operator
      app.kubernetes.io/instance: diagnostics-example.adot-diagnostics
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          telemetry-client: 'true'
    ports:
    - protocol: TCP
      port: 4317
    - protocol: TCP
      port: 4318
```

OTLP clientでは証明書を信頼し、実際に生成されたService、protocol、4317／4318 portを使用してください。NetworkPolicyを強制するCNIが必要です。このpolicyはCollector Podだけを選択し、同じnamespace内のlabel付きclientを許可します。必要に応じてmetrics targetのTLS／認証と、workloadのingress policyを設定します。Prometheus discoveryの対象は1つのnamespace内に限られ、TCP port名がmetricsのannotation付きRunning Podだけがopt-inします。設定されていないannotation portを書き換えず、このendpointにあるportを使います。

この例ではscrapeの重複を避けるためreplicaを1つにしています。scaleするにはtargetのsharding／allocator設計が必要です。memory_limiterはbatchより前に置きますが、memory／batchの設定でlosslessな配信が保証されるわけではありません。AWS X-Rayにはtraceを、awsemfはCloudWatch Logs経由でmetricsを書き込み、AMPにはSigV4認証付きremote writeを送ります。独自のEKS／DiagnosticsExample metricsは、Container Insightsのschema／dashboardに自動ではなりません。未解決の{ClusterName}がundefinedになることを避けるためlog名を固定していますが、exporterのresource attributeが振り分けに影響する場合があります。producerのデータを制限し、IAMを確認してください。cardinalityを評価せず、すべてのresource attributeをmetric labelに変換しないでください。

アプリケーションのservice identityとpropagationは維持してください。Collectorを配置しただけでは全requestが計装されたり、samplingによる欠落がなくなったりしません。使わないexporterとpipeline参照はセットで削除します。この監査ではtelemetry、AWSへの要求、アプリケーションの再起動、Collector／Operatorのインストールを行っていません。

[CloudWatchの設定](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Observability-EKS-addon.html) · [Pod metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/pod-metrics.md) · [Operator API](https://github.com/open-telemetry/opentelemetry-operator/releases/tag/v0.158.0) · [ADOTコンポーネントversion](https://github.com/aws-observability/aws-otel-collector/blob/v0.50.0/go.mod) · [Prometheus receiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.158.0/receiver/prometheusreceiver) · [EMF exporter](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.158.0/exporter/awsemfexporter)

---

<span id="8-failure-detection-architecture"></span>

## 8. 障害検出アーキテクチャ

### 4層の検出pipeline

![メトリクス、ログ、トレース、イベントがデータソースからCloudWatch Agent、Fluent Bit、ADOT Collector、Prometheusなどの収集ツールを通り、CloudWatch Logs Insights、メトリクスアラーム、異常検出、複合アラームなどの分析層へ入り、SNS、Slack、PagerDuty、EventBridgeなどの通知先へ流れるEKS障害検出の4段階パイプライン図。](../.gitbook/assets/en-eks-11-eks-advanced-debugging-3.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-11-eks-advanced-debugging-3.html)

この図は概念上の選択肢を示しており、すべてが接続された構成ではありません。収集、保存／query、alarm評価、通知のそれぞれに、設定、identity、ネットワークアクセス、正常な配信の確認が必要です。traceを分析するには、設定済みのtrace backendも必要です。Logs Insightsがすべてのtraceを自動的にalarmへ変換するわけではありません。

### AWSネイティブのログ収集：設定上の契約

以下は、レビュー済みLinuxノード用Fluent Bit設定の例であり、DaemonSetがインストール済みという意味ではありません。既存の管理主体または[監視のセットアップ手順](06-eks-monitoring-logging.md)を使い、競合するcollectorを二重にインストールしないでください。プロセスには、読み取り専用host log mount、Kubernetes metadata用RBAC、適切なAWS identity、そして**別々の**checkpoint／buffer用の書き込み可能なディレクトリが必要です。AWS_REGION、CLUSTER_NAME、NODE_NAMEはdeployment／Downward APIで設定します。auto_create_groupはfalseのため、保存先log groupを事前に作り、アクセス許可を設定してください。

```text
[SERVICE]
    Flush                   5
    Grace                   30
    Log_Level               info
    Daemon                  off
    storage.path            /var/fluent-bit/buffer
    storage.sync            normal
    storage.checksum        on
    storage.max_chunks_up   32

[INPUT]
    Name                    tail
    Tag                     kube.*
    Path                    /var/log/containers/*.log
    Exclude_Path            /var/log/containers/*_amazon-cloudwatch_*.log
    multiline.parser        cri
    DB                      /var/fluent-bit/state/containers.db
    Mem_Buf_Limit           50MB
    Skip_Long_Lines         On
    Refresh_Interval        10
    storage.type            filesystem

[FILTER]
    Name                    kubernetes
    Match                   kube.*
    Kube_URL                https://kubernetes.default.svc:443
    Kube_CA_File            /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    Kube_Token_File         /var/run/secrets/kubernetes.io/serviceaccount/token
    Kube_Tag_Prefix         kube.var.log.containers.
    Merge_Log               On
    Merge_Log_Key           log_processed
    K8S-Logging.Exclude      Off

[OUTPUT]
    Name                    cloudwatch_logs
    Match                   kube.*
    region                  ${AWS_REGION}
    log_group_name          /aws/eks/${CLUSTER_NAME}/containers
    log_stream_name         ${NODE_NAME}
    auto_create_group       false
    storage.total_limit_size 100M
```

組み込みのCRI multiline parserはcontainerdで使うCRI stream／partial record形式を扱います。Docker JSON parserとは形式が異なります。agent自身を除外するnamespaceは、実際に使う値に合わせてください。log_processedは結合済みアプリケーションJSONを含み、下のmetric filterの例で参照されます。Filesystem bufferとDB checkpointは異なる問題を扱う機能であり、losslessまたはexactly-once配信を保証しません。output queueが満杯になると古いchunkが破棄されます。長い行のskipでrecordが失われる場合があり、container／nodeのrotationで未読データが消えることもあります。サイズ上限、保持期間、diskの空き、IAM／KMS失敗を監視してください。Fargate／Auto Mode／Windowsには対応する収集方法があります。このhost mountを使う例をすべての環境へ一律に適用できるわけではありません。

### Alertmanager：読み込み済み設定とSecretファイル

Prometheus Operatorでは、alertmanager.yamlキーを含むSecretを使い、既存のAlertmanagerのspec.configSecretから参照します。alertmanager-configというConfigMapが自動的に読み込まれるわけではありません。以下はレビュー済みのHelm／Operator管理者に組み込む**spec断片**であり、新しいAlertmanager一式のdeploymentではありません。別のSecretからurl／keyを提供し、`/etc/alertmanager/secrets/<secret-name>/`へmountする必要があります。

```yaml
spec:
  configSecret: alertmanager-reviewed
  secrets:
  - alertmanager-slack
  - alertmanager-pagerduty
```
```yaml
global:
  resolve_timeout: 5m
  slack_api_url_file: /etc/alertmanager/secrets/alertmanager-slack/url
route:
  receiver: default
  group_by:
  - alertname
  - cluster
  - namespace
  - pod
  - node
  - severity
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
  - matchers:
    - severity="critical"
    receiver: critical
  - matchers:
    - severity="warning"
    receiver: warnings
receivers:
- name: default
  slack_configs:
  - channel: '#alerts-default'
    send_resolved: true
- name: critical
  slack_configs:
  - channel: '#incidents'
    send_resolved: true
  pagerduty_configs:
  - routing_key_file: /etc/alertmanager/secrets/alertmanager-pagerduty/key
    severity: critical
- name: warnings
  slack_configs:
  - channel: '#alerts-warnings'
    send_resolved: true
    title: '{{ .Status | toUpper }}: {{ .CommonAnnotations.summary }}'
    text: '{{ .CommonAnnotations.description }}'
inhibit_rules:
- source_matchers:
  - severity="critical"
  target_matchers:
  - severity="warning"
  equal:
  - alertname
  - cluster
  - namespace
  - pod
  - container
  - node
```

この設定ではcritical alertを1つのreceiverからSlackとPagerDutyの両方へ送り、warningはSlackへ、それ以外はdefault receiverへ送ります。continue: trueがあっても、childが一致した後にparent／default receiverも呼び出すわけではありません。現行のmatchers／source_matchers／target_matchersを使い、非推奨のmapping構文は避けています。inhibitionで比較するlabelにはリソースidentityを含めます。labelがない場合は空値として比較されるため、異なるPod／nodeのalertを抑制しないよう、実際のlabel仕様を確認してください。読み込まれた設定、route、通信経路は個別に検証します。構文解析や合成routingの成功は、Slack／PagerDutyが通知を受信した証明ではありません。email／SMSには別途明示的な接続設定が必要です。

### CloudWatchの閾値、異常検出、複合アラーム

実際のmetric dimension、unit、statisticを使用してください。list-metricsのfilterは、filterより多くのdimensionを持つseriesを返す場合があります。公開されているdimensionの**完全な組み合わせ**を1つ選びます。Container Insightsの設定が必要です。前のセクションの独自ADOT metric namespaceでは代用できません。node_cpu_utilizationはPodのCPU／request／limit比率とは異なります。以下のalarm名、topic ARN、cluster値は例です。設定を置き換えるコマンドの前に既存名を確認してください。通知topic、access／KMS policy、recipientは別途準備が必要です。

```bash
# Read-only: select an actual published metric and its complete dimension set.
: "${AWS_REGION:?}"; : "${CLUSTER_NAME:?}"
aws cloudwatch list-metrics --region "$AWS_REGION" --namespace ContainerInsights \
  --metric-name node_cpu_utilization --dimensions "Name=ClusterName,Value=$CLUSTER_NAME" \
  --query 'Metrics[].{Name:MetricName,Namespace:Namespace,Dimensions:Dimensions}'
```
```bash
# MUTATION: creates/replaces this named alarm and can trigger configured notifications.
: "${AWS_REGION:?}"; : "${SNS_TOPIC_ARN:?Use the owned topic ARN}"
: "${METRIC_DIMENSIONS_FILE:?JSON array containing one reviewed complete dimension set}"
aws cloudwatch put-metric-alarm --region "$AWS_REGION" \
  --alarm-name owned-eks-high-cpu --alarm-description "Example node CPU utilization threshold" \
  --namespace ContainerInsights --metric-name node_cpu_utilization \
  --dimensions "file://$METRIC_DIMENSIONS_FILE" --statistic Average \
  --period 300 --evaluation-periods 3 --datapoints-to-alarm 3 \
  --threshold 80 --comparison-operator GreaterThanThreshold \
  --treat-missing-data missing --alarm-actions "$SNS_TOPIC_ARN"
```

この例では300秒のperiodを3回使い、3 datapointがbreachする条件です。つまり15分間の評価windowであり、2分以内の検出を保証するものではありません。TreatMissingData=missingは欠損データ状態を保ちます。metricの意味に合う場合に限り、別のポリシーを選択してください。初期のINSUFFICIENT_DATAと状態遷移を調査し、alarmを作成しただけで動作中とみなさないでください。

異常検出の例ではAPI固有のmetric／band構造を使います。m1が計測するseries、ad1がThresholdMetricIdで選択するbandです。model、period、statistic、dimensionsを一致させてください。modelには適切なデータと学習が必要で、停止予測を保証しません。JSONに記載された具体的なdimensionの例は、使用前にレビュー済みのdimensionsファイルの値と置き換えます。

```json
{
  "AlarmName": "owned-eks-anomaly-cpu",
  "AlarmDescription": "Example anomaly model for an observed Container Insights metric",
  "Metrics": [
    {
      "Id": "m1",
      "ReturnData": true,
      "MetricStat": {
        "Metric": {
          "Namespace": "ContainerInsights",
          "MetricName": "node_cpu_utilization",
          "Dimensions": [
            {
              "Name": "ClusterName",
              "Value": "REPLACE_WITH_CLUSTER"
            }
          ]
        },
        "Period": 300,
        "Stat": "Average"
      }
    },
    {
      "Id": "ad1",
      "Expression": "ANOMALY_DETECTION_BAND(m1, 2)"
    }
  ],
  "EvaluationPeriods": 3,
  "ThresholdMetricId": "ad1",
  "ComparisonOperator": "LessThanLowerOrGreaterThanUpperThreshold",
  "TreatMissingData": "missing",
  "AlarmActions": [
    "arn:aws:sns:us-west-2:123456789012:owned-eks-alerts"
  ]
}
```
```bash
# MUTATIONS: same observed metric/statistic/dimensions as the reviewed model.
aws cloudwatch put-anomaly-detector --region "$AWS_REGION" \
  --namespace ContainerInsights --metric-name node_cpu_utilization --stat Average \
  --dimensions "file://$METRIC_DIMENSIONS_FILE"
# Replace the example cluster/topic/metric dimensions in the JSON before this request.
aws cloudwatch put-metric-alarm --region "$AWS_REGION" --cli-input-json file://anomaly-alarm-reviewed.json
```
```bash
# Read-only prerequisites: both named alarms must exist and have understood state.
aws cloudwatch describe-alarms --region "$AWS_REGION" \
  --alarm-names owned-eks-high-cpu owned-eks-high-memory
# MUTATION: the AND policy requires both alarms to be ALARM.
aws cloudwatch put-composite-alarm --region "$AWS_REGION" \
  --alarm-name owned-eks-combined-resource \
  --alarm-rule 'ALARM("owned-eks-high-cpu") AND ALARM("owned-eks-high-memory")' \
  --alarm-actions "$SNS_TOPIC_ARN"
```

複合alarmの例では、参照先alarmが同一account／Region内にすでにあることを前提とし、両方がALARMの場合のみ成立します。ANDとORは異なるインシデントポリシーを表し、互いに置き換え可能なresilience保証ではありません。PutMetricAlarmの説明にあるとおり、異常検出modelを使うalarmにはAuto Scaling actionを設定できません。

### Log-Based Metrics

次の方式は、Fluent Bitが統合したJSONのlog_processed.levelを前提とします。実際のレコードとmetric filter対応のlog group classに合わせてください。複数のellipsisを含む空白区切りpatternをそのまま使わないでください。filterは作成後に一致したログイベントを数えるものであり、過去のrequestや一意なエラーの件数ではありません。defaultValue=0を設定しても、イベントがないときにログが配信されている証明にはなりません。

```bash
# MUTATION: structured JSON must actually contain log_processed.level.
aws logs put-metric-filter --region "$AWS_REGION" \
  --log-group-name "/aws/eks/$CLUSTER_NAME/containers" \
  --filter-name OwnedApplicationErrors \
  --filter-pattern '{ $.log_processed.level = "ERROR" }' \
  --metric-transformations "metricName=ApplicationErrors,metricNamespace=EKS/$CLUSTER_NAME/Application,metricValue=1,defaultValue=0,unit=Count"
```

### 成熟度の目標と自動化の境界

元のMTTD値である30／15／5／2分は、検証されていない計画目標として残しています。ここに示す設定がその結果を実証するわけではありません。インシデントごとに発生／検出／復旧時刻を同じ方法で測定してください。ML／異常検出だけで予測精度が確立するわけでも、修復操作の許可になるわけでもありません。

| レベル | 元の参考MTTD目標 | 検証する機能 |
| --- | --- | --- |
| 基本 | 30分 | 基本メトリクスと手作業によるログ調査 |
| 事後対応 | 15分 | 調整済み閾値、log metric、dashboard |
| 事前対応 | 5分 | 相関付けしたalarmとレビュー済みrunbook |
| 予測の設計目標 | 2分 | 検証済み予測、範囲を制限した自動化、制御された演習 |

### EventBridgeからLambdaへの診断受付

対象account／Region／alarmを正確に指定したruleと、明示的なtarget invocation authorizationを使います。以下の例はeventを分類して少量の診断要求をログに記録するだけで、Kubernetes／AWS変更用clientは含みません。集約alarmだけではPod名／namespace／UIDを確実に特定できないため、推測したPodを削除する方法をCrashLoopBackOffの既定の修復策にしないでください。

```json
{
  "source": [
    "aws.cloudwatch"
  ],
  "detail-type": [
    "CloudWatch Alarm State Change"
  ],
  "account": [
    "123456789012"
  ],
  "region": [
    "us-west-2"
  ],
  "resources": [
    "arn:aws:cloudwatch:us-west-2:123456789012:alarm:owned-eks-pod-crashlooping"
  ],
  "detail": {
    "alarmName": [
      "owned-eks-pod-crashlooping"
    ],
    "state": {
      "value": [
        "ALARM"
      ]
    }
  }
}
```
```python
"""EventBridge alarm intake example: classification/logging only, no AWS or Kubernetes client."""
import datetime
import json
import os

def classify_alarm(event, expected_alarm_arn, now):
    parts=expected_alarm_arn.split(':',5)
    if len(parts)!=6 or parts[2]!='cloudwatch' or not parts[5].startswith('alarm:'):
        raise ValueError('Configure one exact CloudWatch alarm ARN')
    if not isinstance(event,dict):
        return {'status':'ignored','reason':'invalid event'}
    detail=event.get('detail')
    state=detail.get('state') if isinstance(detail,dict) else None
    resources=event.get('resources')
    if (event.get('source')!='aws.cloudwatch'
        or event.get('detail-type')!='CloudWatch Alarm State Change'
        or event.get('account')!=parts[4] or event.get('region')!=parts[3]
        or not isinstance(resources,list) or expected_alarm_arn not in resources
        or not isinstance(state,dict) or state.get('value')!='ALARM'
        or detail.get('alarmName')!=parts[5][len('alarm:'):]):
        return {'status':'ignored','reason':'outside configured alarm/state'}
    event_id=event.get('id')
    if not isinstance(event_id,str) or not 1<=len(event_id)<=128:
        return {'status':'ignored','reason':'missing or invalid event ID'}
    try:
        changed=datetime.datetime.fromisoformat(state['timestamp'].replace('Z','+00:00'))
        if changed.tzinfo is None or now.tzinfo is None:
            raise ValueError('Timezone required')
        age=(now-changed).total_seconds()
    except (KeyError,TypeError,ValueError,AttributeError):
        return {'status':'ignored','reason':'invalid timestamp'}
    if age < -300 or age > 3600:
        return {'status':'ignored','reason':'outside example event-age window'}
    return {'status':'diagnostic_request','event_id':event_id,
            'alarm_arn':expected_alarm_arn,'state_changed_at':changed.isoformat(),
            'action':'inspect evidence and select a reviewed runbook'}

def lambda_handler(event,context):
    result=classify_alarm(event,os.environ['EXPECTED_ALARM_ARN'],
                          datetime.datetime.now(datetime.timezone.utc))
    print(json.dumps(result))
    return result
```

EXPECTED_ALARM_ARNには、所有するalarmの正確なARNを設定します。1時間のage windowと5分の未来時刻許容幅はポリシー例です。実際のLambda invocation主体を制限してください。event fieldの確認は、送信元を暗号学的に検証するものではありません。EventBridgeの非同期invocationは、返されたdictionaryをactionとして転送しません。実際のdiagnostic queue／workflowは明示的に接続する必要があります。この分類結果の記録は「自動修復の実行」ではありません。

変更を行うrunbookを有効にする前に、identity／UIDの再検証、永続化されたevent IDの重複排除、rate limit、最小権限、同時実行制御、workload／data／PDBの確認、rollback、事後検証を実装します。retryや重複eventで削除が繰り返されてはいけません。この分類機能では、それらの本番変更制御を実装済みとは主張しません。

| 重大度の例 | Slack | PagerDuty | そのほかのchannel | 変更ポリシー |
| --- | --- | --- | --- | --- |
| P1 重大 | Incident | 即時対応ポリシー | 接続済みの場合、チームリード／当番のemailまたはSMS | 範囲を限定したレビュー済みrunbookのみ |
| P2 高 | 高優先度alert | 15分後のエスカレーション例 | 接続済みの場合、チームemail | 条件付きでレビュー |
| P3 中 | Alert | 任意 | 接続済みの場合、チームemail | 既定では自動変更しない |
| P4 低 | 低優先度alert | なし | 日次digestの例 | 自動変更しない |

これはrouting policyの例であり、すべてのchannelが設定済みで時間どおりに通知される証拠ではありません。この監査ではalarm、topic、policy、Lambda function、cloud resourceを作成／実行しておらず、通知も行っていません。

[Fluent BitのCRI解析](https://docs.fluentbit.io/manual/administration/configuring-fluent-bit/multiline-parsing) · [Bufferingの上限](https://docs.fluentbit.io/manual/administration/buffering-and-storage) · [CloudWatch output](https://docs.fluentbit.io/manual/pipeline/outputs/cloudwatch) · [Alertmanager 0.34設定](https://github.com/prometheus/alertmanager/blob/v0.34.0/docs/configuration.md) · [PutMetricAlarmの例](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutMetricAlarm.html) · [Metric dimension](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html)

---

<span id="9-quick-reference"></span>

## 9. クイックリファレンス

### 変更を選ぶ前に症状を解釈する

| 症状 | 証跡と解釈 |
| --- | --- |
| CrashLoopBackOff | backoffを伴うコンテナ終了／再起動の繰り返し。exit code、last state、probe、現在／前回のログを確認します。restartAlwaysではexit 0でもloopする場合があります。 |
| ImagePullBackOff | image pull失敗後の再試行待ちです。先行するerror、image／tag／digest、platform、pull identity、registry／network／CA／rate limitを調べます。 |
| ErrImagePull | pullが失敗した状態です。ネットワーク障害だけや、アプリケーションのIRSA問題だけを証明するものではありません。 |
| OOMKilled | runtimeの理由、memory limit／working set、ノードの証跡を照合します。exit 137だけ、または使用量の高さだけではleakを証明できません。 |
| CreateContainerConfigError | 参照するConfigMap／Secret／volume、namespace、keyを確認します。credentialの値を表示しないでください。 |
| Pending：resource | provisioning前にrequest、init／Pod overhead、allocatable resource、Pod limit、実際のscheduling eventを比較します。 |
| Pending：配置 | selector／affinity／taint／topology／storageの制約を調べます。Pendingが意図された状態の場合もあります。 |
| ContainerCreating | コンテナstatusのreason／表示であり、Pod phaseではありません。runtime、image、CNI、volumeの準備を確認します。 |
| RunContainerError | 実際のruntime／security／command errorを確認します。常に適用できる再起動策はありません。 |
| postStart hook failure | handlerとアプリケーション起動を調べます。postStartはENTRYPOINTより前に実行される保証がなく、一般的なtimeoutSecondsフィールドもありません。 |
| preStop hook failure | handlerのerrorとgrace periodの上限を確認します。hookの実行時間もこの上限に含まれます。強制終了はdrain成功を意味しません。 |
| FailedScheduling | CPU不足と決めつけず、PVC／affinity／resource制約を含むmessage全文を確認します。 |
| FailedMount | CSIの管理者、claim、attachment／topology、権限、backend／networkのhealthを調べます。finalizerをすべて削除しないでください。 |
| NetworkNotReady | 実際のノードネットワーク実装とready証跡を確認します。標準aws-node用コマンドはモード依存です。 |
| NodeNotReady | Ready=Falseとheartbeat欠落によるUnknownを区別し、node／EC2／runtime／networkの証跡を確認します。 |
| Evicted | node pressure／ephemeral-storageの証跡とPod reasonを調べます。limitを増やしたりログを削除したりすれば直るとは限りません。 |
| BackOff | 再試行動作を示します。調査対象はその直前の失敗です。 |
| InvalidImageName | image参照の構文を確認します。registryから正常に取得されるより前の段階の問題です。 |

### 範囲を限定した読み取りコマンド

```bash
# Use the account/context guard and the actual namespace/Pod/container from triage.
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
kubectl --context "$KUBE_CONTEXT" get nodes -o wide
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -o wide
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events --field-selector type=Warning
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods --containers
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" logs "$POD_NAME" -c "$CONTAINER_NAME" --since=15m --tail=100
# Run separately: previous-container logs may not exist.
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" logs "$POD_NAME" -c "$CONTAINER_NAME" --previous --tail=100
```
```bash
# Authorized reads; print names/keys only, not configuration or Secret values.
: "${CONFIGMAP_NAME:?Set one relevant ConfigMap}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get configmap "$CONFIGMAP_NAME" -o json | jq '{
  name:.metadata.name,textKeys:(.data // {} | keys),binaryKeys:(.binaryData // {} | keys)
}'
: "${SECRET_NAME:?Set one Secret whose read permission is explicitly authorized}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get secret "$SECRET_NAME" -o json | jq '{
  name:.metadata.name,type:.type,keyNames:(.data // {} | keys)
}'
```

Secret表示を抑えるこのコマンドもAPIからSecretを要求し、Secret読み取り権限が必要です。認可境界の代わりにはなりません。event timestampが複数回発生したeventを集計した時刻の場合があります。topは最近のメトリクスのsampleであり、過去または瞬間値の真実を示すものではありません。endpointは前述のEndpointSlice手順で調べてください。

Pod作成／debug／exec、rollout undo／restart、scale、drain／repair、削除は、それぞれ別途レビュー済みの運用手順に分けてください。Podを強制削除するとAPIオブジェクトは消えますが、古いprocessが停止した証明にはなりません。writerが重複する原因となる場合があります。日常のtriage手順や、データ／eviction保護の迂回にこのコマンドを含めないでください。

### ツールの選択

| ツール | 用途と注意点 |
| --- | --- |
| netshoot | レビュー済み診断イメージ／toolbox。Pod作成とtraffic送信は前述の対象範囲を限定した手順に従います。 |
| eks-node-viewer | スケジュールされたPod requestとnode allocatable capacityを比較します。実際のPod CPU／memory使用量ではありません。releaseとcluster／AWS accessを確認します。 |
| crictl | 認可された互換ホストで、設定済みruntime endpointを使ってCRIの状態／ログを調べます。 |
| kubeconform | Kubernetes schema versionを固定し、CRD schemaを提供します。schema欠落／skipは検証成功ではありません。 |
| stern | context／namespace／selectorを明示し、出力量を制限して複数Podのログを調べます。 |
| k9s | 対話型TUIです。調査を目的とする場合は、readonlyモードと適切なRBACを使用します。 |
| kubectx／kubens | ローカルのデフォルトcontext／namespaceを変更します。共有診断手順では明示的なcontext flagの方が安全です。 |

インシデント前にレビュー済みのreleaseを選び、修復手順としてgo install @latestのようなversion固定のないコマンドを実行しないでください。Kubeconformはローカル／offlineのschema場所を指定できますが、admission webhookの実行やruntime動作の証明にはなりません。server-side dry-runは選択したAPI serverへ接続するため、offline検査とは異なります。K9sは--readonlyに対応しますが、既定でreadonlyではありません。この監査ではツールのbenchmarkも対話セッションも実行していません。

### 自分が所有するSupport Case向けのEKS Log Collector

このレビューでは、公式EKS log collectorへの経路を確認できました。リポジトリが移動したという推測で置き換えるものではありません。collectorはhost／system／runtime／network情報を集め、archiveを書き出します。互換性のある認可済みノードには、現行の公式手順だけを使い、collectorのrevisionを確認してください。Auto ModeではNodeDiagnosticを推奨し、文書化されたdebug-container経路に対応します。通常の直接SSHアクセスは利用できません。

```bash
# Download only; do not automatically execute a newly downloaded host script.
set -euo pipefail
: "${EVIDENCE_PARENT:?Set an existing private evidence directory}"
: "${COLLECTOR_REF:?Set a reviewed full 40-character commit SHA from the official repository}"
[[ "$COLLECTOR_REF" =~ ^[0-9a-fA-F]{40}$ ]]
test -d "$EVIDENCE_PARENT"
umask 077
COLLECTOR_DIR=$(mktemp -d "$EVIDENCE_PARENT/eks-support.XXXXXXXX")
curl --fail --location --silent --show-error --connect-timeout 5 --max-time 30 \
  "https://raw.githubusercontent.com/awslabs/amazon-eks-ami/$COLLECTOR_REF/log-collector-script/linux/eks-log-collector.sh" \
  --output "$COLLECTOR_DIR/eks-log-collector.sh"
sha256sum "$COLLECTOR_DIR/eks-log-collector.sh"
```

digestをレビュー済みの独立したartifact記録と比較してください。sha256sumを表示しただけでは認証になりません。collectorを実行すること自体は、disk／CPU負荷と機密データを伴う別の認可対象操作です。archiveを確認し、秘匿情報を除いてから、所有するAWS Support caseへ手動で添付します。kubeconfig／key material、アプリケーションログ、endpoint address、環境情報を公開して安全だと決めつけないでください。この監査ではSupport archiveを作成／アップロードしていません。

[Kubeconform](https://github.com/yannh/kubeconform) · [K9s](https://github.com/derailed/k9s) · [eks-node-viewer](https://github.com/awslabs/eks-node-viewer) · [EKSのトラブルシューティング](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html)

---

<span id="10-next-steps"></span>

## 10. 次のステップ

### クイズ

このドキュメントの内容を理解できたか確認するには、[EKS高度なデバッグのクイズ](../quizzes/eks/11-eks-advanced-debugging-quiz.md)に取り組んでください。

### 次のドキュメント

この章に続くversion計画のトピックは、[Kubernetes version roadmap](12-kubernetes-version-roadmap.md)を参照してください。

EKSクラスターとオンプレミス環境の統合については、[EKS Hybrid Nodes](../eks-hybrid-nodes/README.md)を参照してください。

### 追加の学習資料

- [AWS EKS公式ドキュメント：トラブルシューティング](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html)
- [Kubernetes公式ドキュメント：デバッグ](https://kubernetes.io/docs/tasks/debug/)
- [Amazon EKS Best Practices Guide](https://docs.aws.amazon.com/eks/latest/best-practices/introduction.html)
