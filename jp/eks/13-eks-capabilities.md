# Amazon EKS Capabilities: Managed Argo CD、kro、ACK

> **サポート対象バージョン**: EKS 1.36–1.37、Argo CD `3.4.6-eks-2` および `3.4.7-eks-1`、kro `0.9.4-eks-1`、ACK `46.186.1-eks-1`、AWS CLI 2.38.3
> **最終更新日**: 2026年11月19日

EKS Capabilities は、Argo CD、kro (Kube Resource Orchestrator)、ACK (AWS Controllers for Kubernetes) を、クラスターの外部にある AWS 運用のコントローラーとして実行します。この機能は2025年11月30日に一般提供が開始されました。コントローラーログの配信 (Vended Logs) は2026年6月に、Argo CD のカスタム `argocd-cm` 設定は2026年8月に追加されました。

この章の数値は、2026年10月に ap-northeast-2 のテストクラスターで測定したものです。メインのクラスターはプライベートサブネットと authenticationMode `API` を使用し、m7g.large ノードを2台備えていました（アップグレードおよびマルチクラスターのテストに使った hub と spoke は、それぞれ1台のノードを使用）。同じシナリオを、同じクラスターにインストールしたセルフマネージド (OSS) コントローラーでも繰り返しました。各シナリオの実行回数は1～5回に限られているため、数値は範囲として捉え、運用上の判断を下す前に自分の環境で再確認してください。測定せず、ドキュメントのみで確認した内容には「ドキュメントによる」と記しています。測定の詳細と生データは[ EKS Capabilities ブログシリーズ](https://blog.atomai.click/eks-capabilities-argocd/)（韓国語）にあります。

## 目次

1. [共通モデル](#common)
2. [作成と日常運用](#create)
3. [Argo CD Capability](#argocd)
4. [kro Capability](#kro)
5. [ACK Capability](#ack)
6. [3つを組み合わせて使う](#together)
7. [クラスターのアップグレードと Capability のバージョン](#upgrade)
8. [マルチクラスターと Blue/Green 置き換え](#multicluster)
9. [セルフマネージドとの比較と選択基準](#compare)
10. [料金](#pricing)
11. [検証範囲と参考資料](#refs)

---

<span id="common"></span>

## 1. 共通モデル

| 項目 | 動作 |
|---|---|
| コントローラーの配置場所 | AWS 所有のインフラストラクチャ。ワーカーノード上に Pod は存在しない（3つすべてでゼロを測定） |
| クラスターへのアクセス | Capability ロール（信頼されたプリンシパル `capabilities.eks.amazonaws.com`）は、EKS access entry を通じて API サーバーを呼び出す。API エンドポイントがプライベート専用でも動作する |
| 数 | クラスターごとに、Capability の種類ごとに1つ |
| バージョン | AWS が選択し、ロールアウトする。作成/更新 API にバージョン引数がないため、固定も選択もできない |
| 削除 | `--delete-propagation-policy RETAIN` のみ。CRD、CR、デプロイ済みリソース、access entry は残る |
| ログ | `kubectl logs` では参照できない。CloudWatch Vended Logs を使い、CloudWatch Logs、S3、または Amazon Data Firehose に配信する（[EKS のモニタリングとログ記録](./06-eks-monitoring-logging.md)を参照） |
| 料金 | Capability の時間料金に加え、管理対象オブジェクトごとの料金（Argo CD は Application、kro はインスタンス、ACK はリソース） |

3つすべてに共通する特徴は、デフォルトの権限が限定的なことです。自動作成される access entry のポリシーだけでは、Argo CD はデプロイできず、kro は RGD コントローラーを起動できず、ACK はサービスごとの IAM 権限なしでは AWS リソースを作成できません。これに対し、Argo CD と kro の OSS Helm chart のデフォルトでは、コントローラーに `apiGroups: ["*"], resources: ["*"], verbs: ["*"]` が付与されます。

<span id="create"></span>

## 2. 作成と日常運用

### Capability ロールと作成コマンド

Capability ロールで `capabilities.eks.amazonaws.com` を信頼し、`sts:AssumeRole` と `sts:TagSession` を許可します。kro は AWS API を呼び出さないため、権限ポリシーは必要ありません。パブリック Git リポジトリを使う Argo CD も、権限ポリシーなしで動作しました。

```bash
aws eks create-capability --cluster-name "$CLUSTER_NAME" \
  --capability-name kro --type KRO \
  --role-arn "arn:aws:iam::${ACCOUNT_ID}:role/${CLUSTER_NAME}-kro" \
  --delete-propagation-policy RETAIN

aws eks describe-capability --cluster-name "$CLUSTER_NAME" --capability-name kro \
  --query 'capability.{status:status,version:version}'
```

| Capability | `CREATING` → `ACTIVE` | 削除 | 自動作成される access entry ポリシー | インストールされる CRD |
|---|---|---|---|---|
| Argo CD | 349 s（別のクラスターで `endpointPrefix` を指定して新規作成した場合は385 s、同じ prefix で再作成した場合は338 s） | 100.5 s | `AmazonEKSArgoCDClusterPolicy`（クラスター）、`AmazonEKSArgoCDPolicy`（`argocd` namespace） | `applications`、`applicationsets`、`appprojects` |
| kro | 70.1–70.4 s | 46.9 s | `AmazonEKSKROPolicy` | `resourcegraphdefinitions.kro.run`、`graphrevisions.internal.kro.run` |
| ACK | 385.7 s（CRD がすでに存在する場合は77 s） | 67.3 s | `AmazonEKSACKPolicy` | 267個（66個のサービス API group と `services.k8s.aws` の `IAMRoleSelector`） |

### 運用上の注意事項

- **AWS CLI を最新の状態に保つ。** CLI 2.35.11 は `argoCd` 配下で認識する設定が `namespace`、`awsIdc`、`rbacRoleMappings`、`networkAccess` のみで（`endpointPrefix` はなし）、ACK の設定には `Unknown parameter in configuration: "ack", must be one of: argoCd` というエラーを返しました。2.38.3 では両方が受け付けられました。未サポートと判断する前に、CLI のバージョンを確認してください。
- **Capability の変更は1つずつ適用する。** ログ配信ソースを追加するたびに Capability は約6.6～7秒間 `UPDATING` になり、その間に次の変更を行うと `ConflictException: ... currently in UPDATING state` で失敗しました。変更の間には `ACTIVE` になるまで待ってください。
- **最初からログ配信を有効にする。** コントローラーがクラスターの外部にあるため、後から内部の動作を確認する手段はログだけです（CloudTrail では引き続き AWS API 呼び出しの時刻を確認できます）。ログは構造化 JSON で、Argo CD は各 reconcile のフェーズごとの時間（`compare_app_state_ms`、`patch_ms` など）を記録します。
- **RETAIN では「コントローラー以外はすべて」残る。** Capability の削除中は、CR の変更は reconcile されません（kro インスタンスのレプリカ数を変更して確認）。同じ CRD を使用する OSS コントローラーをインストールすると、保留中の変更を適用します。

<span id="argocd"></span>

## 3. Argo CD Capability

### ローカルクラスターの登録とデプロイ権限

マネージド Argo CD では、自身のクラスターでさえデプロイ先として自動追加されません。API URL ではなく EKS ARN を使ってクラスター Secret を作成してください。

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: in-cluster
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: cluster
stringData:
  name: in-cluster
  server: arn:aws:eks:ap-northeast-2:111122223333:cluster/example-cluster
  project: default
```

自動作成される access entry だけでは同期できません。Argo CD はデプロイするリソースだけでなく、キャッシュを構築するためにクラスター内のすべてのリソースタイプを一覧表示するためです。

| Capability ロールのクラスター権限 | 結果 |
|---|---|
| 自動作成された access entry のみ | `ComparisonError: ... podtemplates is forbidden ... at the cluster scope` |
| `AmazonEKSEditPolicy` を追加 | 141 s 経過後も失敗。`securitygrouppolicies.vpcresources.k8s.aws` の一覧表示が拒否された |
| `AmazonEKSAdminViewPolicy` を追加 | 11.6 s で同期され、Healthy になった |
| kro/ACK API の CR をデプロイ（NginxApp インスタンス、ACK Queue） | `nginxapps.platform.example.com is forbidden`。access entry に Kubernetes group を追加し、その API group 用の ClusterRole をバインドすると16 s で解決した |

AWS ドキュメントでは、開始時に `AmazonEKSClusterAdminPolicy`（`system:masters` と同等）を使い、本番環境向けの最小権限構成として、クラスター全体の読み取りアクセスと namespace スコープの `AmazonEKSEditPolicy` を説明しています。テストでは、クラスター範囲の Edit と AdminView に加え、プラットフォーム CRD ごとに ClusterRole を設定する方法で動作しましたが、これはドキュメント記載の本番構成より広い権限です。さらに範囲を狭めるには、マネージド Capability がサポートする `resource.respectRBAC` を使うと、監視対象が許可されたリソースに限定されます（未テスト）。

### Git のポーリングと Webhook

| 方法 | Commit → Synced（3回実行） |
|---|---|
| マネージド、デフォルトのポーリング（ドキュメントによると6分） | 341.8 s、619.3 s、697.1 s |
| マネージド、GitHub Webhook | 7.0–7.3 s |
| セルフマネージド 3.4.6、デフォルトのポーリング（120 s + 60 s のジッター） | 115.7–171.4 s |

マネージドのポーリング間隔（`timeout.reconciliation`）は設定可能なキーではなく、ジッターも公開されていません。デプロイの遅延が数分単位で変動しては困る場合、実質的に Webhook が必要です。Capability が作成した `argocd-webhook-creds-secret` の `webhook.github.secret` にランダムな文字列を設定し、同じシークレットを使って Git リポジトリに `<server URL>/api/webhook` を登録します。サーバー URL は AWS がホストするパブリックアドレスなので、Webhook 専用エンドポイントを別途公開する必要はありません。VPC endpoint でパブリックアクセスを制限すると、GitHub Webhook もブロックされる可能性があります（未テスト）。

ドリフトの self-heal は同等でした。マネージドは2.08–2.32 s、セルフマネージドは1.05–3.06 s でした。ただし、新しい commit がない同じアプリに対して self-heal を繰り返すと、上流のバックオフ（2 s、毎回×3、上限300 s）が発生し、復旧にほぼ5分かかりました（251–254 s を測定）。セルフマネージドでは `--self-heal-backoff-*` フラグで調整できます。マネージドで公開されている `argocd-cmd-params-cm` のキーは3つ（`hydrator.enabled`、`application.namespaces`、`applicationsetcontroller.namespaces`）のみで、self-heal のタイミング調整は AWS Support に依頼するよう AWS ドキュメントに記載されています。急を要する場合は手動で sync を実行してください。

### 設定、ヘルスチェック、CLI

Capability の namespace に、ラベル `app.kubernetes.io/part-of: argocd` を付けて `argocd-cm` ConfigMap を作成します。サポートされていないキーは警告なしに無視されます。

| 項目 | 結果 |
|---|---|
| `ui.bannercontent` | UI に表示される |
| kro インスタンスの Lua ヘルスチェック | 適用された。スクリプトの変更は約12 s で反映された |
| Lua の `string.upper()`、`os.time()` | `attempt to index a non-table object(nil)`、health は `Unknown`。上流のデフォルト（`useOpenLibs` がオフ）と同じだが、マネージドでは有効化できない |
| `argocd login --username admin` または `--sso` | どちらも失敗する |
| UI の Token + `ARGOCD_SERVER`、`ARGOCD_AUTH_TOKEN`、`ARGOCD_OPTS=--grpc-web` | `app list/get/sync`、`cluster list`、`proj list` は動作する |
| 150 s スリープする PreSync hook | ドキュメント記載の sync timeout は120 s だが、161 s で `Succeeded`。制限がどのフェーズに適用されるかは不明 |

Argo CD 3.x では、デフォルトでリソースの health は Application の status に保存されません。そのため、`kubectl get application -o json` で `.status.resources[].health` が空でも正常です。`argocd app get` または UI で health を確認してください。

ドキュメントによると、Config Management Plugins (CMP)、カスタム SSO、UI 拡張、`argocd admin` などはサポートされていません。CMP を使ってマニフェストを生成している場合、そのままではマネージド Capability に移行できません。2026年10月の上記測定時点では未サポートだった Notifications controller は、2026年11月に追加されました（下記参照）。

### 2026年11月の更新: Argo CD Notifications をサポート

[2026年11月3日の発表](https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-eks-argo-cd-notifications/)によると、EKS Capability for Argo CD は現在 Argo CD Notifications をサポートしています。上流の Argo CD と同じように、クラスター内でトリガーとメッセージテンプレートを定義し、アノテーションで個々の Application をサブスクライブできます。Slack、PagerDuty、Opsgenie、Amazon SQS、Amazon EventBridge など、16の通知サービスに対応しています。SQS と EventBridge は IAM Capability Role を通じて認証されるため、認証情報をクラスターに保存せずにデプロイイベントをイベント駆動型ワークフローに渡せます。Slack token などのサードパーティー認証情報が必要なサービスでは、シークレットの代わりに AWS Secrets Manager ARN を参照できます。この Capability が提供されるすべてのリージョンで追加料金なしで利用できます。このドキュメントの測定は提供開始前のため、通知の動作はここではテストしていません。

### サインイン: IAM Identity Center のみ

認証は IAM Identity Center のみで、ローカルユーザーはありません。Capability 設定の `rbacRoleMappings` で Identity Center のユーザー (`SSO_USER`) またはグループ (`SSO_GROUP`) を ADMIN、EDITOR、VIEWER にマッピングします。Okta や Microsoft Entra ID を Argo CD に直接接続することはできません。外部 IdP を Identity Center の ID ソースとして設定し、サインインには SAML、ユーザーとグループの同期には SCIM を使います（ドキュメントによる）。

- Identity Center インスタンスの ID ソースは1つです。組織インスタンスがすでに別の IdP を使っている場合、Argo CD だけに別の IdP を割り当てるにはアカウントインスタンスが必要です（未テスト）。
- リンクした Identity Center インスタンスは作成後に変更できません（EKS コンソールのヘルプによる）。マッピングはユーザー ID とグループ ID で保存されます。ID ソースを Active Directory に切り替えるとユーザーとグループが削除されるため、マッピングを書き直す必要があります。
- Capability では最大1,000個の ID をマッピングできるため、ユーザーではなくグループをマッピングしてください。グローバルロールは3つだけなので、細かな `argocd-rbac-cm` ポリシーは AppProject のロールに移行する必要があります。

<span id="kro"></span>

## 4. kro Capability

AWS ドキュメントによると、マネージド kro は同じ上流コントローラーを使用し、完全な互換性があります。テストでは報告されたバージョン `0.9.4-eks-1` が最新の OSS リリースと一致し、同じ RGD と CEL 式が同じように動作しました。違いは権限と運用にあります。kro の概念と例については、[kro の章](../platform-engineering/03-kro.md)を参照してください。

### デフォルトの権限ではコントローラーを起動できない

`AmazonEKSKROPolicy` の対象は `kro.run` group と CRD のみです。RGD スキーマの group から生成される API（たとえば `platform.example.com`）を watch する権限も、子の Deployment と Service を作成する権限もありません。エラーは forbidden ではなく、キャッシュ同期のタイムアウトとして現れます。

```text
ControllerReady=False FailedToStart
  ...
  cache sync timeout for platform.example.com/v1alpha1, Resource=nginxapps
```

eksctl ガイドでは、開始時に `AmazonEKSClusterAdminPolicy` をアタッチしています。最小権限の代替策として、access entry に Kubernetes group を追加し、RGD ごとに ClusterRole をバインドできます。

```bash
aws eks update-access-entry --cluster-name "$CLUSTER_NAME" \
  --principal-arn "arn:aws:iam::${ACCOUNT_ID}:role/${CLUSTER_NAME}-kro" \
  --kubernetes-groups kro-workloads
```

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: kro-workloads-reviewed-nginxapps
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: kro:controller:reviewed-nginxapps
subjects:
  - kind: Group
    name: kro-workloads
    apiGroup: rbac.authorization.k8s.io
```

RGD の適用後に権限を付与した場合、`Active` になるまでさらに228 s かかりました（おそらくコントローラーの再試行間隔ですが、ログでは確認できていません）。2つ目の RGD では、ClusterRole を先に適用するとすぐに `Active` になりました。RGD とその ClusterRole は同じ Git path に置き、sync waves を使って RBAC を先に適用してください（sync waves は未テスト）。OSS の `rbac.mode: aggregation` も、ラベル付き ClusterRole のみをコントローラー権限にマージするため、同様の作業が必要です（chart による。未テスト）。

### ライフサイクルのパフォーマンスと移行

| フェーズ（各5回実行） | マネージド | OSS 0.9.4 |
|---|---|---|
| 作成 → `ACTIVE` | 2.49–3.73 s | 2.43–3.44 s |
| Spec の変更 → Deployment の更新 | 0.50–0.52 s（1回だけ51.6 s の外れ値。原因不明） | 0.49–0.56 s |
| 削除 → Deployment と Service の消失 | 1.02–3.02 s | 1.01–4.38 s |

マネージド → OSS → マネージドと切り替えても、2つの RGD と4つのインスタンスはそのまま残りました（一方のコントローラーを削除してから、もう一方をインストール）。ダウンタイムなしで移行するには、リーダー選出 lease を移動する AWS の手順に従ってください（未テスト）。ただし、chart の path と value key は古くなっています。現在の chart は `oci://registry.k8s.io/kro/charts/kro`、0.9.4 のキーは `config.leaderElectionNamespace` です。

### 落とし穴: kro は同じ名前の既存 CR を引き継ぐ

namespace 内に子リソースと同じ名前の CR がすでにある場合、kro は処理を拒否せず、server-side apply で上書きします。テストでは既存の ACK Table CR に `kro.run/owned=true` が設定され、`spec.tableName` が変更されました。ACK は新しい table を作成し、元の table は管理対象から外れました。インスタンスを削除すると、引き継いだ CR も削除されました。OSS 0.9.4 でも同じ動作が再現されたため、これは上流の挙動です。

- 子リソース名に RGD 固有の suffix を追加します（`${schema.metadata.name + "-os"}`）。
- kro が管理する namespace と、人が CR を直接作成する namespace を分離します。
- データを保持する ACK リソースには `services.k8s.aws/deletion-policy: retain` を設定します。名前の変更によって新しいリソースに移行することは防げないため、名前の分離が本質的な対策です（このケースと retain の併用は未テスト）。
- マルチテナントクラスターでは、インスタンスが `ingressClassName` やホスト名を自由に選べないようにします。RGD で固定するか、インスタンス名から生成してください。

<span id="ack"></span>

## 5. ACK Capability

マネージド ACK は、上流で GA となっているすべてのサービスコントローラーを1つの Capability にまとめます。プレビュー段階のコントローラーは GA に達すると自動的に追加されます（ドキュメントによる）。ACK のリソースモデル、引き継ぎ、保持については、[ACK の章](../platform-engineering/02-ack.md)を参照してください。

### IAMRoleSelector によるチームごとの IAM

Capability ロールにはチームロールを引き受ける権限だけを付与し、クラスター範囲の `IAMRoleSelector` で namespace をロールにマッピングします。各チームロールは Capability ロールを信頼し、`sts:AssumeRole` と `sts:TagSession` を許可します。

```json
{"Effect": "Allow", "Action": ["sts:AssumeRole", "sts:TagSession"],
 "Resource": ["arn:aws:iam::111122223333:role/ack-team-a",
              "arn:aws:iam::111122223333:role/ack-team-b"]}
```

```yaml
apiVersion: services.k8s.aws/v1alpha1
kind: IAMRoleSelector
metadata:
  name: team-b
spec:
  arn: arn:aws:iam::111122223333:role/ack-team-b
  namespaceSelector:
    names: [team-b]
```

SQS だけを許可するロールを使って team-b に S3 Bucket を作成すると `AccessDenied` で失敗し、エラーメッセージには実際に使われたロール（`assumed-role/ack-team-b/...`）が示されました。CR の条件 `ACK.IAMRoleSelected=True` も、selector が一致したことを示します。詳細を確認したところ、次のことが分かりました。

- S3 Bucket コントローラーは最初に `s3:ListAllMyBuckets` を呼び出します。Bucket リソースを名前パターンで絞り込んでも、この権限は別途必要と思われます（これなしでは未テスト）。
- 一致する selector がない namespace では、Capability ロールが使われます（ドキュメントによる）。Capability ロールにサービス権限がなければ、デフォルトでは拒否されます。
- OSS コントローラーで同じ分離を実現するには、`featureGates.IAMRoleSelector=true` と `enableCARM=false` の両方を設定します。chart のデフォルト `enableCARM: true` のままでは、`cannot enable feature gate 'IAMRoleSelector' when flag 'enable-carm' is set to true` でコントローラーがクラッシュループします。

### リソースの作成、タグ、ドリフト

| リソース | マネージド（3回実行） | OSS（2回実行） |
|---|---|---|
| SQS Queue | 1.04–1.06 s | 1.10–1.16 s |
| S3 Bucket | 3.10–3.14 s | 3.20–3.32 s |
| DynamoDB Table | 11.28–11.53 s | 10.15–11.54 s |

Capability を最初に作成した直後の初回作成だけは遅く、Queue は7.3 s、Bucket は10.9 s、Table は16.5 s でした。

マネージド ACK は AWS リソースに5つのタグを追加します。`eks:controller-version`、`eks:kubernetes-namespace`、`eks:kubernetes-resource-name`、`eks:kubernetes-api-group`、`eks:eks-capability-arn` です。すべての AWS API 呼び出しには、セッションタグ `eks:eks-capability-arn`、`eks:kubernetes-namespace`、`eks:kubernetes-api-group` が付与されます。OSS では `services.k8s.aws/controller-version` と `services.k8s.aws/namespace` の2つのタグが追加されます。OSS から移行するとタグの prefix が変わるため、コスト配分タグとタグベースの IAM 条件も同時に更新してください。

ACK は AWS 側の変更をリアルタイムでは監視しません。ACK の外部で CLI を使って SQS の `VisibilityTimeout` を変更しても、マネージド（2回実行）と OSS（1回実行）のどちらも25分以内に定期的な巻き戻しは起きませんでした。マネージドで確認できた2回の巻き戻しは、Capability がログ設定変更で `UPDATING` になってから86 s 後と、Capability の再作成直後に発生しました（呼び出し時刻は CloudTrail で確認）。コントローラーの再起動がきっかけと思われますが、ログでは確認できていません。OSS のデフォルトの再同期間隔は10時間（`reconcile.defaultResyncPeriod: 36000`）で、調整可能です。マネージドの間隔は公開されておらず、変更もできません。迅速な復旧が重要な場合は、SCP または IAM 条件を使って帯域外の変更を防いでください。たとえば `aws:ResourceTag/eks:eks-capability-arn` のタグが一致するリソースへの変更を、`aws:PrincipalTag/eks:eks-capability-arn` が一致する呼び出しに限って許可します（未テスト）。

### マネージド版の違いと移行

- `FieldExport` CRD はありません。status の値を ConfigMap または Secret にエクスポートするには、kro で status を ConfigMap に書き込むなど、別の方法を使ってください。
- `--configuration '{"ack":{"disabledServices":["sagemaker"]}}'` によるサービスの無効化は、CLI 2.38.3 で12.5 s 後に反映されましたが、そのサービスのインストール済み CRD は350 s 経過後も残っていました。代わりに、未使用のサービスは作成時に指定してください（作成時の設定は未テスト）。
- コントローラーバージョンは最新 OSS リリースより1つ古いものでした（s3 1.12.2 対 1.13.1、sqs 1.7.1 対 1.8.2）。
- マネージド Capability では adopt（`services.k8s.aws/adoption-policy: adopt-or-create`）と retain アノテーションが動作します。adopt は4.7 s で完了し、retain を指定して削除した Queue は AWS に残りました（マネージドで測定）。Capability の削除後、OSS コントローラーは残っていた12個の CR をそのまま引き継ぎました。

<span id="together"></span>

## 6. 3つを組み合わせて使う

自然な役割分担は、Argo CD が Git からマニフェストを同期し、kro が複数のリソースを1つの API にまとめ、その中の AWS リソースを ACK が作成する形です。テストした `OrderService` RGD は、ACK Queue と Table を作成し、その status の値（queue URL、table ARN）を ConfigMap にコピーして Deployment を起動しました。

| 組み合わせ | 結果 | 必要な追加設定 |
|---|---|---|
| Argo CD → ACK Queue | Git からの Queue CR が6.5 s で Synced になった | Argo CD Capability ロールに `queues.sqs.services.k8s.aws` の RBAC |
| kro → ACK Queue と Table + ConfigMap + Deployment | インスタンスは13.2–34.3 s で `ACTIVE`（大半は DynamoDB table の作成時間） | kro Capability ロールに ACK リソースの RBAC、ACK 側に IAMRoleSelector |

ACK CRD は、`AmazonEKSEditPolicy` などのデフォルトの EKS access policy の対象ではありません。そのため、ACK リソースを作成する Argo CD または kro のいずれにも、それらの API group に対する権限が必要です。2つの測定は別々に行い、3段階すべての連携はエンドツーエンドでは実行していません。

<span id="upgrade"></span>

## 7. クラスターのアップグレードと Capability のバージョン

### インプレースアップグレード中の動作

3つすべての Capability があるクラスターを、1.36 から1.37にインプレースアップグレードしました。コントロールプレーンのアップグレードには約7分かかり、3つの Capability はすべて `ACTIVE` のままで、バージョン、health、`modifiedAt` に変化はありませんでした。

| フェーズ | Argo CD self-heal | kro の伝播 | ACK Queue の同期 |
|---|---|---|---|
| 前（3回実行） | 2.1–14.6 s | 1.02–1.04 s | 1.49–3.53 s |
| 中（4回実行） | 2.1 s、6.1 s、112.9 s、254.5 s | 1.02–1.07 s | 1.52–1.58 s |
| 後（5回実行） | 2.3 s、その後251–252 s | 1.01–1.15 s | 1.47–1.57 s |

kro と ACK の「中」の4回の測定のうち1回は、アップグレード完了直後に実施しました。アップグレード中の self-heal の遅延は、アップグレード後にも同じように再現したため、アップグレードではなく、前述の self-heal のバックオフによるものです。API サーバーのバージョンが 1.36.4 と1.37.0の間で切り替わっていた約3分間は、kro と ACK を測定していません。ノードグループはアップグレードしていません。

インプレースアップグレードでは、Capability 固有の手順は不要でした。セルフマネージドコントローラーでは、新しい Kubernetes バージョンへの対応を確認し、場合によっては先にアップグレードする必要があります。マネージドモデルでは、その互換性確認を AWS に任せられます。ただし、EKS upgrade insights のチェック項目には Capability を対象としたものはありませんでした。

### バージョンは選択できない

`create-capability` と `update-capability` にバージョン引数はなく、AWS ドキュメントに記載されているのは「自動更新とセキュリティパッチ」のみです。Capability のバージョンについて、更新スケジュール、事前通知、メンテナンスウィンドウ、バージョンごとのリリースノート、ロールバック方法をドキュメントで確認できませんでした。2026年7月に追加された[クラスターのバージョンロールバック](./08-eks-upgrades.md)は Kubernetes のマイナーバージョンをロールバックするもので、ロールバックのドキュメントは Capability を扱っていません。Capability にはバージョン引数がないため、Capability のバージョンをロールバックする手段として扱わないでください（推論）。テストでは、10月21日に作成した Argo CD Capability のバージョンは `3.4.6-eks-2`、翌日に別のクラスターで作成したものは `3.4.7-eks-1` でした。コントローラーのバージョンは、クラスターのアップグレードとは独立して変更されることがあります。

不具合のあるリリースに備えるため、次のように準備してください。

| 準備 | 方法 | 根拠 |
|---|---|---|
| バージョン変更の記録 | `describe-capability` から `capability.version` をポーリングし、インシデントと照合する | 測定済み（フィールドを確認） |
| 検証クラスター | 本番用の RGD、Application、ACK CR を、同じ Capability があるクラスターで先に実行する。ロールアウト順序は制御できないため、本番より先に更新される保証はない | 推論 |
| Git で動作を固定 | health check（`resource.customizations`）、sync options、RBAC を Git に保持し、再作成や移行で同じ動作を再現できるようにする | 測定済み（設定を適用） |
| AWS Support | ユーザー側でロールバックする手段はないため、ケースを起票する。self-heal のタイミング調整は AWS Support に依頼するよう AWS ドキュメントに記載されている | 推論（self-heal のタイミングはドキュメントによる） |
| セルフマネージドへの一時的な切り替え | RETAIN を指定して Capability を削除すると、CRD とリソースは残り、同じ CRD を使用する OSS コントローラーが引き継ぐ（kro、ACK、Argo CD で測定）。Argo CD ではクラスター Secret の `server` を EKS ARN から API URL（ローカルの場合は `https://kubernetes.default.svc`）に変更する必要があり、ARN で登録したリモートまたはプライベートの spoke では、OSS 側のネットワーク経路と認証が必要。マネージドに戻すには再作成が必要（Argo CD は約6分） | 測定済み |
| サービスごとの ACK ロールバック | 影響を受けるサービスだけを `disabledServices` に追加し、セルフマネージドコントローラーをインストールするかスケールアップする。OSS コントローラーには独自の IAM 設定が必要。また、IAMRoleSelector を使う場合は `featureGates.IAMRoleSelector=true` と `enableCARM=false` が必要。Capability がインストールした CRD 上で OSS chart を実行することは未テスト。インストール済みの CRD は残る（測定済み） | ドキュメントによる |

バージョンを明示的に固定する必要がある場合、AWS ドキュメント自体がセルフマネージドを勧めています（「特定の Kubernetes リソース API バージョンやカスタムコントローラービルドが必要な場合」）。

<span id="multicluster"></span>

## 8. マルチクラスターと Blue/Green 置き換え

### Argo CD hub とプライベート spoke

hub クラスターの Argo CD Capability から、同じアカウントと VPC にあり、API エンドポイントがプライベート専用の spoke を登録しました。エンドポイント、セキュリティグループ、ルートなどのネットワーク設定は不要でした。別の VPC にあるワークステーションから spoke には接続できなかったため、接続には AWS が提供する経路が使われているようです。spoke には hub の Capability ロール用の access entry が必要で、手動で作成します。

| Spoke の access entry 権限 | 結果 |
|---|---|
| `AmazonEKSEditPolicy` + `AmazonEKSAdminViewPolicy` | 接続と認証は成功したが、`CreateNamespace=true` は `namespaces is forbidden` で失敗。自動再試行5回（約303 s）が尽きた |
| `AmazonEKSArgoCDClusterPolicy` を追加後、手動で sync | 11.1 s で同期され、Healthy になった |

- Cluster Secret が受け付けるのは EKS ARN のみのため、EKS 以外のクラスターはデプロイ先にできません（ドキュメントによる）。
- Application の料金はデプロイ先クラスターごとにカウントされるため、hub 配置でもクラスターごとの配置でも費用は同じです。増えるのは Argo CD インスタンス数に応じた Capability 料金だけです。ただし、hub の Capability ロールはすべての spoke に書き込みアクセスを持つため、AppProject のデプロイ先を制限するか、チームごとに Capability を分けることを検討してください。
- 別アカウントのクラスターには hub Capability ロールの access entry だけが必要です（ドキュメントによる。未テスト）。マネージド版の上限はリモートクラスター100個、Application 3,000個です。

### kro と ACK の配置場所

kro と ACK の Capability が管理するのは、それぞれ自身のクラスターだけです。hub の Argo CD から spoke に RGD インスタンスや ACK CR をデプロイするには、spoke にも kro または ACK が必要です（マネージド版または OSS）。

| 構成 | 適するケース | 懸念事項 |
|---|---|---|
| すべてのクラスターに kro を配置し、ApplicationSet で RGD をロールアウト | アプリチームが各クラスターで同じ API を使用する | Capability 料金と RBAC の作業はクラスター数に応じて増える。クラスター間で kro のバージョンが同一である保証はドキュメントにない（未テスト） |
| hub のみ kro を配置し、RGD から spoke 用の ACK リソースと Argo CD Application を作成 | プラットフォームの抽象化を1か所で定義する | 権限と影響範囲が hub に集中する。spoke のアプリチームは kro API を直接利用できない（未テスト） |
| 中央 ACK（hub） | データベース、IAM、VPC など、プラットフォームが所有するリソース | hub の Capability ロールがすべてのアカウントとリソースに対する権限を持つ |
| 分散 ACK（クラスターごと） | Queue や Bucket をワークロードの近くで宣言する | IAMRoleSelector の設定がクラスター数に応じて増える |
| ハイブリッド ACK | hub に管理者スコープのリソース、spoke にワークロードスコープのリソース | 同じリソースを2か所で宣言しないよう、スコープのルールが必要 |

どの構成でも、同じ AWS リソースを2つのクラスターが同時に宣言しないよう、スコープのルールを設定してください。

### Blue/Green 置き換え

- **Argo CD**: Capability はクラスターに属するため、Argo CD をホストするクラスターを置き換える場合、Capability を再作成する必要があります。デフォルトのアドレス `argocd-<ID>-<account ID>.eks-capabilities.<region>.amazonaws.com` はクラスターごとに異なるため、UI と Webhook の URL も変わります。作成時に `endpointPrefix` を設定しておけば、削除して同じ prefix で再作成してもアドレスは維持されました（同じクラスターでのみテスト）。アドレスにはクラスター固有の情報が含まれないため、別のクラスターに移行した後も動作するはずです。prefix がアカウントとリージョン内で一意の場合（未テスト）、旧クラスターと新クラスターで同時に使用できません。その場合は削除して再作成する必要があり、その間（実測で100 s + 338 s）は UI、Webhook、同期が停止します。この停止が許容できない場合は、まず新しい prefix で Capability を起動して Git の Webhook URL を変更してください。新しい Capability を有効にする前に、古い方の auto-sync を無効にするか、その Application を非カスケードで削除し、ターゲットクラスターに新しい Capability ロールの access entry をあらかじめ作成します（未テスト）。prefix は作成後に変更できません。頻繁に置き換えるワークロードクラスターではなく、専用の hub に Argo CD を配置してください。
- **kro**: ClusterRole と binding は Git 経由で移行できますが、access entry への Kubernetes group の追加には EKS API 呼び出しが必要です。クラスターを作成する IaC（eksctl、Terraform など）に含めてください。
- **ACK**: 1つの方法は、旧クラスターの CR を `deletion-policy: retain` で削除し、新クラスターで同じリソースを `adoption-policy: adopt-or-create` によって引き継ぐ順序です（各手順は測定済み。クラスター間の一連の手順は未テスト）。`eks:eks-capability-arn` タグに基づく変更を SCP がブロックする場合、新しい Capability の ARN は異なるため、引き継ぎが拒否される可能性があります。切り替え中は条件を緩和するか、代わりに環境タグやチームタグを条件にしてください。

<span id="compare"></span>

## 9. セルフマネージドとの比較と選択基準

| 項目 | マネージド Capability | セルフマネージド (OSS) |
|---|---|---|
| インストール時間 | Argo CD 349 s、kro 70 s、ACK 386 s | Argo CD 43.4 s、kro 15.6 s、ACK コントローラー3つで46 s |
| ノードリソース | なし | Argo CD は7 Pod（メモリ339–624Mi）、kro は1 Pod（requests 256m、128Mi）、ACK は3 Pod（各 requests 50m、64Mi） |
| バージョン | AWS が選択し、固定できない | 自分で選択（テスト時点で Argo CD v3.5.5 と ACK s3 1.13.1 が最新） |
| デフォルトの権限 | 限定的。デプロイ、子リソース、IAM の権限は自分で付与する | Argo CD と kro の chart のデフォルトは `*/*/*` |
| パフォーマンス | kro、ACK、Argo CD self-heal は OSS と同等。Argo CD のデフォルトのポーリングは遅い | 基準値（Argo CD 3.4.6 と kro 0.9.4 は同じバージョンで測定。ACK OSS は1つ新しいバージョンで実行） |
| SSO | Identity Center のみ。設定項目は2つ | Dex、OIDC などを自分で設定 |
| リモートクラスター | EKS ARN + access entry。ネットワーク設定なしでプライベートクラスターに対応 | クラスターごとに API URL、認証、ネットワーク経路が必要 |
| 未対応機能 | CMP、`argocd admin`、Lua 標準ライブラリ、ACK FieldExport（Argo CD Notifications は2026年11月に追加） | なし |
| 直接調整できない項目 | Argo CD のポーリング、ACK の再同期間隔、コントローラーフラグ、リソース制限。Argo CD self-heal のバックオフ調整は AWS Support 経由のみ | すべて調整可能 |
| ログ | Vended Logs | `kubectl logs` と独自の収集機能 |

マネージドが適するケース:

- 複数の EKS クラスター、特にプライベートクラスターや別アカウントのクラスターにデプロイする hub を構築している
- AWS のサインインがすでに Identity Center に集約されており、Argo CD の SSO を自分で運用したくない
- Kubernetes から複数の AWS サービスを管理しており、サービスごとに ACK コントローラーを1つずつ実行する負担が大きく、チームごとの IAM 分離が必要
- プラットフォームコントローラーの権限をデフォルトで限定し、access entry と RBAC で明示したい

セルフマネージドを続けるべきケース:

- CMP、FieldExport、Lua 標準ライブラリに依存している
- EKS 以外のクラスターもデプロイ先に含まれる
- 組織の Identity Center とは別の IdP を Argo CD のみで使用する必要があり、アカウントインスタンスが選択肢にならない
- コントローラーのバージョン、アップグレード時期、ポーリング間隔、再同期間隔を自分で制御しなければならない

評価に適したタイミングの1つは、クラスターが1つを超える規模に拡大する前です。hub の配置場所、Identity Center インスタンス、`endpointPrefix` は、作成後に変更できないか、変更が困難です。もう1つは、セルフマネージド Argo CD の HA 再構築やメジャーアップグレードを行うときです。AWS の移行手順では、既存コントローラーをゼロにスケールし、Application と Secret を移動してから、`destination.server` を ARN に変更します。その間、同期は停止します（未テスト）。

<span id="pricing"></span>

## 10. 料金

料金はソウル (ap-northeast-2) のもので、2026年10月21日に AWS Pricing API を使って照会し、月730時間で計算しました。

| Capability | Capability 料金 | オブジェクトごとの料金 | 例（月額） |
|---|---|---|---|
| Argo CD | 1時間あたり $0.034799（約 $25.4/月） | 1 Application-hour あたり $0.001726（デプロイ先クラスターごとにカウント） | アプリ9個で約 $36.7、100個で約 $151 |
| kro | 1時間あたり $0.006038（約 $4.4/月） | 1 instance-hour あたり $0.000061 | インスタンス100個で約 $8.9 |
| ACK | 1時間あたり $0.006038（約 $4.4/月） | 1 resource-hour あたり $0.000061 | リソース200個で約 $13.3 |

比較として、m7g.large の料金（ソウルでは1時間あたり $0.1003）をデフォルトのセルフマネージド構成に按分すると、Argo CD（メモリ624Mi）は約 $5.6、kro（CPU request 256m）は約 $9.4、ACK コントローラー3つ（CPU request 合計150m）は約 $5.5 になります。HA 構成やアプリ、サービスの増加によって OSS 側のコストも上がります。マネージド Argo CD はアプリ数が増えるほど割高になります。kro と ACK は差が小さいため、運用負荷と機能差で判断してください。

<span id="refs"></span>

## 11. 検証範囲と参考資料

測定には ap-northeast-2 の単一アカウントを使用しました。EKS 1.36.4 のクラスターが1つと、アップグレードおよびマルチクラスターのテスト用に2つのクラスター（hub は1.36 → 1.37、プライベート spoke は1.37）を使用しました。各シナリオの実行回数は1～5回で、Argo CD app は最大9個、kro インスタンスは6個、ACK リソースは約20個でした。ACK は S3、SQS、DynamoDB のみをテストしました。以下は未テストで、ドキュメントに依拠しています。Okta または Entra ID との統合と Identity Center アカウントインスタンス、VPC endpoint 経由のプライベートアクセス、別アカウントまたは別 VPC のクラスター登録、Notifications と CMP、クロスアカウント ACK、マネージドと OSS を同時に動作させるダウンタイムなしの移行、クラスターをまたぐ ACK の retain から adopt までの一連の手順。測定後、テストクラスターと AWS リソースは削除しました。

- [EKS Capabilities](https://docs.aws.amazon.com/eks/latest/userguide/capabilities.html)
- [EKS Capabilities に関する考慮事項](https://docs.aws.amazon.com/eks/latest/userguide/capabilities-considerations.html)
- [Capability の Kubernetes リソース](https://docs.aws.amazon.com/eks/latest/userguide/capability-kubernetes-resources.html)
- [Argo CD に関する考慮事項](https://docs.aws.amazon.com/eks/latest/userguide/argocd-considerations.html)
- [EKS Capability for Argo CD とセルフマネージド Argo CD の比較](https://docs.aws.amazon.com/eks/latest/userguide/argocd-comparison.html)
- [ターゲットクラスターの登録](https://docs.aws.amazon.com/eks/latest/userguide/argocd-register-clusters.html)
- [Argo CD 設定の構成](https://docs.aws.amazon.com/eks/latest/userguide/argocd-configure-settings.html)
- [kro 権限の構成](https://docs.aws.amazon.com/eks/latest/userguide/kro-permissions.html)
- [EKS Capability for kro とセルフマネージド kro の比較](https://docs.aws.amazon.com/eks/latest/userguide/kro-comparison.html)
- [ACK 権限の構成](https://docs.aws.amazon.com/eks/latest/userguide/ack-permissions.html)
- [EKS Capability for ACK とセルフマネージド ACK の比較](https://docs.aws.amazon.com/eks/latest/userguide/ack-comparison.html)
- [EKS Capabilities コントローラーログへのアクセス](https://docs.aws.amazon.com/eks/latest/userguide/capabilities-controller-logs.html)
- [クラスターを以前の Kubernetes バージョンにロールバックする](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [Amazon EKS の料金](https://aws.amazon.com/eks/pricing/)
- 測定ブログ（韓国語）: [マネージド Argo CD](https://blog.atomai.click/eks-capabilities-argocd/)、[マネージド kro](https://blog.atomai.click/eks-capabilities-kro/)、[マネージド ACK](https://blog.atomai.click/eks-capabilities-ack/)
- テスト用マニフェスト: [Atom-oh/eks-capabilities-demo](https://github.com/Atom-oh/eks-capabilities-demo)

[EKS Capabilities クイズ](../quizzes/eks/13-eks-capabilities-quiz.md)
