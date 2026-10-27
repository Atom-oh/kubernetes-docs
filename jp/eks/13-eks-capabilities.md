# Amazon EKS Capabilities: Managed Argo CD、kro、ACK

> **サポート対象バージョン**: EKS 1.36–1.37、Argo CD `3.4.6-eks-2` および `3.4.7-eks-1`、kro `0.9.4-eks-1`、ACK `46.186.1-eks-1`、AWS CLI 2.38.3
> **最終更新日**: 2026年10月23日

EKS Capabilities は、Argo CD、kro（Kube Resource Orchestrator）、ACK（AWS Controllers for Kubernetes）を、クラスターの外部で AWS が運用するコントローラーとして実行します。この機能は2025年11月30日に一般提供が開始されました。コントローラーログの配信（Vended Logs）は2026年6月に、Argo CD のカスタム `argocd-cm` 設定は2026年8月に、それぞれ提供が開始されました。

この章の数値は、2026年10月に ap-northeast-2 のテストクラスターで測定したものです。メインクラスターはプライベートサブネットを使用し、authenticationMode は `API`、ノードは m7g.large を2台使用しました（アップグレードとマルチクラスターのテストに使ったハブとスポークは、それぞれノード1台でした）。同じシナリオを、同じクラスターにインストールしたセルフマネージド（OSS）コントローラーでも繰り返しました。各シナリオの実行回数は1～5回に限られるため、数値は範囲として捉え、運用上の判断を下す前にご自身の環境で再確認してください。測定せず、ドキュメントだけで確認した項目には「ドキュメントによる」と記載しています。測定内容と生データは、[EKS Capabilities のブログシリーズ](https://blog.atomai.click/eks-capabilities-argocd/)（韓国語）に掲載されています。

## 目次

1. [共通モデル](#common)
2. [作成と日常的な運用](#create)
3. [Argo CD Capability](#argocd)
4. [kro Capability](#kro)
5. [ACK Capability](#ack)
6. [3つを組み合わせて使う](#together)
7. [クラスターのアップグレードと Capability のバージョン](#upgrade)
8. [マルチクラスターと Blue/Green による置き換え](#multicluster)
9. [セルフマネージドとの比較と選択基準](#compare)
10. [料金](#pricing)
11. [検証範囲と参考資料](#refs)

---

<span id="common"></span>

## 1. 共通モデル

| 項目 | 動作 |
|---|---|
| コントローラーの配置場所 | AWS が所有するインフラストラクチャ。ワーカーノード上に Pod は存在しない（3つとも測定値はゼロ） |
| クラスターへのアクセス | Capability のロール（信頼されたプリンシパル `capabilities.eks.amazonaws.com`）が、EKS access entry 経由で API サーバーを呼び出す。プライベートのみの API エンドポイントでも動作する |
| 数 | クラスターごとに Capability タイプあたり1つ |
| バージョン | AWS が選択し、ロールアウトする。作成／更新 API にバージョン引数がないため、バージョンを固定したり選択したりすることはできない |
| 削除 | `--delete-propagation-policy RETAIN` のみ。CRD、CR、デプロイ済みリソース、access entry は残る |
| ログ | `kubectl logs` では取得できない。CloudWatch Vended Logs を使って CloudWatch Logs、S3、または Amazon Data Firehose に配信する（[EKS のモニタリングとログ記録](./06-eks-monitoring-logging.md)を参照） |
| 料金 | Capability の時間単位の料金と、管理対象オブジェクトごとの料金（Argo CD は Application、kro はインスタンス、ACK はリソース） |

3つに共通する特徴は、デフォルトの権限が狭いことです。自動作成された access entry のポリシーだけでは、Argo CD はデプロイできず、kro は RGD コントローラーを起動できず、ACK はサービスごとの IAM 権限なしでは AWS リソースを作成できません。一方、Argo CD と kro の OSS Helm Chart のデフォルトでは、コントローラーに `apiGroups: ["*"], resources: ["*"], verbs: ["*"]` が付与されます。

<span id="create"></span>

## 2. 作成と日常的な運用

### Capability のロールと作成コマンド

Capability のロールでは `capabilities.eks.amazonaws.com` を信頼し、`sts:AssumeRole` と `sts:TagSession` を許可します。kro は AWS API を呼び出さないため、権限ポリシーは不要です。パブリック Git リポジトリを使う Argo CD も、権限ポリシーなしで動作しました。

```bash
aws eks create-capability --cluster-name "$CLUSTER_NAME" \
  --capability-name kro --type KRO \
  --role-arn "arn:aws:iam::${ACCOUNT_ID}:role/${CLUSTER_NAME}-kro" \
  --delete-propagation-policy RETAIN

aws eks describe-capability --cluster-name "$CLUSTER_NAME" --capability-name kro \
  --query 'capability.{status:status,version:version}'
```

| Capability | `CREATING` → `ACTIVE` | 削除 | 自動作成される access entry のポリシー | インストールされる CRD |
|---|---|---|---|---|
| Argo CD | 349秒（別のクラスターで `endpointPrefix` を指定して新規作成した場合は385秒、同じプレフィックスで再作成した場合は338秒） | 100.5秒 | `AmazonEKSArgoCDClusterPolicy`（クラスター）、`AmazonEKSArgoCDPolicy`（`argocd` namespace） | `applications`、`applicationsets`、`appprojects` |
| kro | 70.1～70.4秒 | 46.9秒 | `AmazonEKSKROPolicy` | `resourcegraphdefinitions.kro.run`、`graphrevisions.internal.kro.run` |
| ACK | 385.7秒（CRD がすでに存在する場合は77秒） | 67.3秒 | `AmazonEKSACKPolicy` | 267個（66個のサービス API グループと、`services.k8s.aws` 内の `IAMRoleSelector`） |

### 運用上の注意

- **AWS CLI は最新の状態に保つ。** CLI 2.35.11 は `argoCd` 配下で `namespace`、`awsIdc`、`rbacRoleMappings`、`networkAccess` しか認識せず（`endpointPrefix` は未対応）、ACK の設定も `Unknown parameter in configuration: "ack", must be one of: argoCd` として拒否しました。2.38.3 では両方を受け付けました。何かがサポートされていないと判断する前に、CLI のバージョンを確認してください。
- **Capability の変更は一度に1つずつ適用する。** ログ配信ソースを追加するたびに Capability は約6.6～7秒間 `UPDATING` になり、その間に次の変更を行うと `ConflictException: ... currently in UPDATING state` で失敗しました。変更と変更の間は `ACTIVE` になるまで待ってください。
- **最初からログ配信を有効にする。** コントローラーがクラスター外にあるため、後から内部動作を確認する手段はログしかありません（CloudTrail では引き続き AWS API 呼び出し時刻を確認できます）。ログは構造化 JSON 形式です。Argo CD は各 reconcile のフェーズごとの所要時間（`compare_app_state_ms`、`patch_ms` など）を記録します。
- **RETAIN では「コントローラー以外のすべて」が残る。** Capability の削除中は CR の変更が reconcile されません（kro インスタンスのレプリカ数を変更して確認）。同じ CRD を使用する OSS コントローラーをインストールすると、保留されていた変更が反映されます。

<span id="argocd"></span>

## 3. Argo CD Capability

### ローカルクラスターの登録とデプロイ権限

マネージド Argo CD は、自身のクラスターすらデプロイ先として追加しません。API URL ではなく EKS ARN を使ってクラスター Secret を作成してください。

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

Argo CD はデプロイ対象のリソースだけでなく、キャッシュを構築するためにクラスター内のすべてのリソースタイプを一覧表示するので、自動作成された access entry だけでは同期できません。

| Capability ロールのクラスター権限 | 結果 |
|---|---|
| 自動作成された access entry のみ | `ComparisonError: ... podtemplates is forbidden ... at the cluster scope` |
| + `AmazonEKSEditPolicy` | 141秒後も失敗。`securitygrouppolicies.vpcresources.k8s.aws` の一覧取得が拒否された |
| + `AmazonEKSAdminViewPolicy` | 11.6秒で同期され、Healthy になった |
| kro／ACK API の CR をデプロイ（NginxApp インスタンス、ACK Queue） | `nginxapps.platform.example.com is forbidden`。access entry に Kubernetes グループを追加し、その API グループ用の ClusterRole をバインドすると、16秒で解決した |

AWS のドキュメントでは、使い始める際に `AmazonEKSClusterAdminPolicy`（`system:masters` と同等）を使用し、本番環境ではクラスター全体への読み取りアクセスと namespace スコープの `AmazonEKSEditPolicy` を組み合わせた最小権限の構成が説明されています。テストでは、クラスター範囲の Edit と AdminView に加えて、プラットフォーム CRD ごとの ClusterRole を使う構成で動作しましたが、これはドキュメント記載の本番構成より広い権限です。さらに範囲を絞るには、マネージド Capability がサポートする `resource.respectRBAC` を使用して、許可されたリソースだけを監視する方法があります（未テスト）。

### Git ポーリングと Webhook

| 方法 | コミットから Synced まで（3回実行） |
|---|---|
| マネージド、デフォルトのポーリング（ドキュメントによると6分） | 341.8秒、619.3秒、697.1秒 |
| マネージド、GitHub webhook | 7.0～7.3秒 |
| セルフマネージド 3.4.6、デフォルトのポーリング（120秒 + 60秒のジッター） | 115.7～171.4秒 |

マネージドのポーリング間隔（`timeout.reconciliation`）は設定可能なキーではなく、ジッターも公開されていません。デプロイの遅延が数分単位で変動しては困る場合、実質的に webhook が必須です。Capability が作成した `argocd-webhook-creds-secret` の `webhook.github.secret` にランダムな文字列を設定し、同じシークレットを使って Git リポジトリに `<server URL>/api/webhook` を登録します。サーバー URL は AWS がホストするパブリックアドレスなので、webhook 用のエンドポイントを別途公開する必要はありません。VPC endpoint によってパブリックアクセスを制限すると、GitHub webhook もブロックされる可能性があります（未テスト）。

ドリフトの自動修復時間は同程度でした。マネージドは2.08～2.32秒、セルフマネージドは1.05～3.06秒でした。ただし、同じアプリで新しいコミットなしに自動修復を繰り返すと、上流のバックオフ（2秒、実行ごとに×3、上限300秒）が適用され、復旧までに約5分かかるようになりました（251～254秒を測定）。セルフマネージドでは `--self-heal-backoff-*` フラグで調整できます。マネージドで公開されている `argocd-cmd-params-cm` のキーは3つ（`hydrator.enabled`、`application.namespaces`、`applicationsetcontroller.namespaces`）のみで、AWS のドキュメントでは自動修復のタイミングに関する要望は AWS Support に問い合わせるよう案内しています。緊急の場合は手動同期を実行してください。

### 設定、ヘルスチェック、CLI

Capability の namespace に、ラベル `app.kubernetes.io/part-of: argocd` を付けて `argocd-cm` ConfigMap を作成します。サポートされていないキーは警告なく無視されます。

| 項目 | 結果 |
|---|---|
| `ui.bannercontent` | UI に表示された |
| kro インスタンスの Lua ヘルスチェック | 適用された。スクリプトの編集は約12秒で反映された |
| Lua の `string.upper()`、`os.time()` | `attempt to index a non-table object(nil)`、health は `Unknown`。上流のデフォルト（`useOpenLibs` がオフ）と同じだが、マネージドでは有効にできない |
| `argocd login --username admin` または `--sso` | どちらも失敗 |
| UI のトークン + `ARGOCD_SERVER`、`ARGOCD_AUTH_TOKEN`、`ARGOCD_OPTS=--grpc-web` | `app list/get/sync`、`cluster list`、`proj list` は動作 |
| 150秒スリープする PreSync hook | ドキュメント記載の同期タイムアウト120秒を超えたにもかかわらず、161秒で `Succeeded`。制限がどのフェーズに適用されるかは不明 |

Argo CD 3.x はデフォルトでは Application のステータスにリソースのヘルスを保存しないため、`kubectl get application -o json` で `.status.resources[].health` が空でも正常です。ヘルスは `argocd app get` または UI で確認してください。

ドキュメントによると、Config Management Plugin（CMP）、Notifications コントローラー、カスタム SSO、UI 拡張、`argocd admin` などはサポートされていません。Notifications でデプロイ通知を送信している場合や、CMP でマニフェストを生成している場合は、そのままではマネージド Capability に移行できません。

### サインイン：IAM Identity Center のみ

認証方式は IAM Identity Center のみで、ローカルユーザーはありません。Capability の設定にある `rbacRoleMappings` で、Identity Center ユーザー（`SSO_USER`）またはグループ（`SSO_GROUP`）を ADMIN、EDITOR、VIEWER に割り当てます。Okta や Microsoft Entra ID は Argo CD に直接接続しません。ドキュメントによると、サインインには SAML、ユーザーとグループの同期には SCIM を使用して、外部 IdP を Identity Center のアイデンティティソースとして設定します。

- Identity Center インスタンスで設定できるアイデンティティソースは1つです。組織インスタンスがすでに別の IdP を使用している場合、Argo CD だけに別の IdP を使うにはアカウントインスタンスが必要です（未テスト）。
- リンク済みの Identity Center インスタンスは、作成後に変更できません（EKS コンソールのヘルプによる）。マッピングはユーザー ID とグループ ID で保存されます。アイデンティティソースを Active Directory に切り替えるとユーザーとグループが削除されるため、マッピングを作り直す必要があります。
- Capability ごとにマッピングできるアイデンティティは最大1,000件なので、ユーザーではなくグループを割り当ててください。グローバルロールは3つしかないため、細かな `argocd-rbac-cm` ポリシーは AppProject のロールに移す必要があります。

<span id="kro"></span>

## 4. kro Capability

AWS のドキュメントによると、マネージド kro は上流と同じコントローラーを使い、完全な互換性があります。テストでは、報告されたバージョン `0.9.4-eks-1` は最新の OSS リリースと一致し、同じ RGD と CEL 式が同じように動作しました。違いは権限と運用にあります。kro の概念と例については、[kro の章](../platform-engineering/03-kro.md)を参照してください。

### デフォルトの権限ではコントローラーを起動できない

`AmazonEKSKROPolicy` が対象とするのは `kro.run` グループと CRD のみです。RGD のスキーマグループから生成された API（例：`platform.example.com`）の watch 権限も、子 Deployment や Service の作成権限も付与しません。この失敗は forbidden ではなく、キャッシュ同期のタイムアウトとして現れます。

```text
ControllerReady=False FailedToStart
  ...
  cache sync timeout for platform.example.com/v1alpha1, Resource=nginxapps
```

eksctl のガイドでは、使い始める際に `AmazonEKSClusterAdminPolicy` をアタッチします。最小権限の代替案は、access entry に Kubernetes グループを追加し、RGD ごとに ClusterRole をバインドすることです。

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

RGD の作成後に権限を付与した場合、`Active` になるまでさらに228秒かかりました（おそらくコントローラーの再試行間隔ですが、ログでは確認できていません）。ClusterRole を先に適用した2つ目の RGD は、すぐに `Active` になりました。RGD とその ClusterRole を同じ Git パスに置き、sync waves を使って RBAC を先に適用してください（sync waves は未テスト）。OSS の `rbac.mode: aggregation` も、ラベル付けされた ClusterRole だけをコントローラー権限にマージするため、同様の作業が必要です（Chart による。未テスト）。

### ライフサイクルのパフォーマンスと移行

| フェーズ（各5回実行） | マネージド | OSS 0.9.4 |
|---|---|---|
| 作成 → `ACTIVE` | 2.49～3.73秒 | 2.43～3.44秒 |
| Spec の変更 → Deployment の更新 | 0.50～0.52秒（原因不明の外れ値が1回あり、51.6秒） | 0.49～0.56秒 |
| 削除 → Deployment と Service の削除完了 | 1.02～3.02秒 | 1.01～4.38秒 |

マネージド → OSS → マネージドと切り替えても、2つの RGD と4つのインスタンスはそのまま維持されました（片方のコントローラーを削除してから、もう片方をインストール）。ダウンタイムなしで移行するには、リーダー選出リースを移動する AWS の手順に従ってください（未テスト）。ただし、Chart のパスと値のキーは古くなっています。現在の Chart は `oci://registry.k8s.io/kro/charts/kro` で、0.9.4 のキーは `config.leaderElectionNamespace` です。

### 注意点：kro は同じ名前の既存 CR を引き継ぐ

子リソースと同じ名前の CR が namespace にすでに存在していても、kro は拒否せず、server-side apply で上書きします。テストでは、既存の ACK Table CR に `kro.run/owned=true` が付与され、`spec.tableName` が変更されました。ACK は新しいテーブルを作成し、元のテーブルは管理対象外になりました。インスタンスを削除すると、引き継がれた CR も削除されました。OSS 0.9.4 でも同じ動作が再現されたため、これは上流の挙動です。

- 子リソース名に RGD 固有のサフィックスを追加する（`${schema.metadata.name + "-os"}`）。
- kro が管理する namespace と、ユーザーが CR を直接作成する namespace を分ける。
- データを保持する ACK リソースには `services.k8s.aws/deletion-policy: retain` を設定する。これを設定しても、名前変更によって新しいリソースに移ることは防げないため、実際の解決策は名前を分けることです（このケースで retain を併用する方法は未テスト）。
- マルチテナントクラスターでは、インスタンスから `ingressClassName` やホスト名を自由に指定できないようにする。RGD で固定するか、インスタンス名から生成してください。

<span id="ack"></span>

## 5. ACK Capability

マネージド ACK は、上流で GA になっているすべてのサービスコントローラーを1つの Capability にまとめます。プレビュー中のコントローラーは GA になると自動的に追加されます（ドキュメントによる）。ACK のリソースモデル、引き継ぎ、保持については、[ACK の章](../platform-engineering/02-ack.md)を参照してください。

### IAMRoleSelector を使ったチームごとの IAM

Capability のロールにはチームロールを引き受ける権限だけを付与し、クラスター範囲の `IAMRoleSelector` で namespace とロールを対応付けます。各チームロールは Capability ロールを信頼し、`sts:AssumeRole` と `sts:TagSession` を許可します。

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

team-b に作成した S3 Bucket で、そのロールに SQS しか許可していなかったところ、`AccessDenied` になり、実際に使用されたロール（`assumed-role/ack-team-b/...`）がメッセージに示されました。CR の条件 `ACK.IAMRoleSelected=True` からも、セレクターが一致したことを確認できます。詳細は次のとおりです。

- S3 Bucket コントローラーは、最初に `s3:ListAllMyBuckets` を呼び出します。バケットリソースを名前パターンで絞っても、この権限は別途必要と見られます（この権限なしの状態では未テスト）。対象リソースは `*` です。
- 一致するセレクターがない namespace では、Capability のロールが使われます（ドキュメントによる）。Capability のロールにサービス権限がなければ、デフォルトでは拒否されます。
- OSS コントローラーで同じ分離を実現するには、`featureGates.IAMRoleSelector=true` と `enableCARM=false` の両方を設定します。Chart のデフォルト `enableCARM: true` のままだと、コントローラーは `cannot enable feature gate 'IAMRoleSelector' when flag 'enable-carm' is set to true` というエラーでクラッシュを繰り返します。

### リソースの作成、タグ、ドリフト

| リソース | マネージド（3回実行） | OSS（2回実行） |
|---|---|---|
| SQS Queue | 1.04～1.06秒 | 1.10～1.16秒 |
| S3 Bucket | 3.10～3.14秒 | 3.20～3.32秒 |
| DynamoDB Table | 11.28～11.53秒 | 10.15～11.54秒 |

Capability の初回作成直後に行った最初の作成だけ、時間が長くなりました。Queue は7.3秒、Bucket は10.9秒、Table は16.5秒でした。

マネージド ACK は AWS リソースに5つのタグを追加します。`eks:controller-version`、`eks:kubernetes-namespace`、`eks:kubernetes-resource-name`、`eks:kubernetes-api-group`、`eks:eks-capability-arn` です。すべての AWS API 呼び出しには、セッションタグ `eks:eks-capability-arn`、`eks:kubernetes-namespace`、`eks:kubernetes-api-group` が付与されます。OSS は `services.k8s.aws/controller-version` と `services.k8s.aws/namespace` の2つのタグを追加します。OSS から移行するとタグのプレフィックスが変わるため、コスト配分タグとタグベースの IAM 条件も同時に更新してください。

ACK は AWS 側の変更をリアルタイムで監視しません。ACK の外部で CLI を使って SQS の `VisibilityTimeout` を変更したところ、マネージド（2回実行）でも OSS（1回実行）でも、25分以内に定期的な変更取り消しは起きませんでした。マネージドで確認された2回の取り消しは、ログ設定変更のために Capability が `UPDATING` になってから86秒後と、Capability 再作成の直後に発生しました（呼び出し時刻は CloudTrail で確認）。コントローラーの再起動がきっかけと思われますが、ログでは確認できていません。OSS のデフォルトの再同期間隔は10時間（`reconcile.defaultResyncPeriod: 36000`）で、調整可能です。マネージドの間隔は公開されておらず、変更できません。速やかな復旧が重要な場合は、SCP または IAM 条件で帯域外の変更を防いでください。たとえば、`aws:ResourceTag/eks:eks-capability-arn` タグが付いたリソースへの変更を、`aws:PrincipalTag/eks:eks-capability-arn` が一致する呼び出しに限って許可する方法があります（未テスト）。

### マネージド版の違いと移行

- `FieldExport` CRD はありません。ステータス値を ConfigMap または Secret にエクスポートするには、kro でステータスを ConfigMap に書き込むなど、別の方法を使ってください。
- `--configuration '{"ack":{"disabledServices":["sagemaker"]}}'` を使ったサービスの無効化は、CLI 2.38.3 では12.5秒で反映されましたが、そのサービス用にインストール済みの CRD は350秒後も残っていました。代わりに、作成時に未使用のサービスを指定してください（作成時の設定は未テスト）。
- コントローラーのバージョンは、最新の OSS リリースより1段階前でした（s3 は 1.12.2 対 1.13.1、sqs は 1.7.1 対 1.8.2）。
- マネージド Capability では、引き継ぎ（`services.k8s.aws/adoption-policy: adopt-or-create`）と retain アノテーションが動作します。引き継ぎには4.7秒かかり、retain を指定して削除した Queue は AWS に残りました（マネージドで測定）。Capability を削除した後、OSS コントローラーは残っていた12個の CR をそのまま引き継ぎました。

<span id="together"></span>

## 6. 3つを組み合わせて使う

自然な役割分担は、Argo CD が Git からマニフェストを同期し、kro が複数のリソースを1つの API にまとめ、その中の AWS リソースを ACK が作成する形です。テストした `OrderService` RGD は ACK Queue と Table を作成し、それらのステータス値（Queue URL、Table ARN）を ConfigMap にコピーして、Deployment を起動しました。

| 組み合わせ | 結果 | 必要な追加設定 |
|---|---|---|
| Argo CD → ACK Queue | Git の Queue CR が6.5秒で Synced になった | Argo CD Capability ロールに `queues.sqs.services.k8s.aws` の RBAC |
| kro → ACK Queue と Table + ConfigMap + Deployment | インスタンスが13.2～34.3秒で `ACTIVE` になった（大半は DynamoDB Table の作成時間） | kro Capability ロールに ACK リソースの RBAC、ACK 側に IAMRoleSelector |

ACK CRD は `AmazonEKSEditPolicy` などのデフォルト EKS access policy の対象外です。そのため、Argo CD と kro のどちらが ACK リソースを作成する場合でも、その API グループへの権限が必要です。この2つの測定は別々に実施しており、3段階すべてをつないだエンドツーエンドの実行は行っていません。

<span id="upgrade"></span>

## 7. クラスターのアップグレードと Capability のバージョン

### インプレースアップグレード中の動作

3つすべての Capability を持つクラスターを、1.36 から1.37へインプレースアップグレードしました。コントロールプレーンのアップグレードには約7分かかり、3つの Capability はバージョン、ヘルス、`modifiedAt` を変えることなく `ACTIVE` のままでした。

| フェーズ | Argo CD の自動修復 | kro の反映 | ACK Queue の同期 |
|---|---|---|---|
| 前（3回実行） | 2.1～14.6秒 | 1.02～1.04秒 | 1.49～3.53秒 |
| 中（4回実行） | 2.1秒、6.1秒、112.9秒、254.5秒 | 1.02～1.07秒 | 1.52～1.58秒 |
| 後（5回実行） | 2.3秒、その後251～252秒 | 1.01～1.15秒 | 1.47～1.57秒 |

kro と ACK の「中」の4回のうち1回は、アップグレード完了直後に実行しました。アップグレード中の自動修復遅延はアップグレード後にも同じように再現したため、原因は上記の自動修復バックオフであり、アップグレードではありません。API サーバーのバージョンが1.36.4と1.37.0の間で切り替わっていた約3分間は、kro と ACK を測定していません。ノードグループのアップグレードも行っていません。

インプレースアップグレードに、Capability 固有の手順は必要ありませんでした。セルフマネージドのコントローラーでは、新しい Kubernetes バージョンのサポート状況を確認し、必要に応じて先にアップグレードする必要があります。マネージドモデルでは、その互換性確認を AWS に任せます。ただし、EKS のアップグレードインサイトでは、Capability はいずれのチェック対象にもなっていませんでした。

### バージョンは選択できない

`create-capability` と `update-capability` にはバージョン引数がなく、AWS のドキュメントには「自動更新とセキュリティパッチ」としか記載されていません。Capability のバージョンについて、更新スケジュール、事前通知、メンテナンスウィンドウ、バージョンごとのリリースノート、ロールバック手順は、ドキュメントで確認できませんでした。2026年7月に追加された[クラスターのバージョンロールバック](./08-eks-upgrades.md)は Kubernetes のマイナーバージョンを戻すもので、ロールバックのドキュメントは Capability を対象としていません。Capability にバージョン引数がないため、これを Capability のバージョンロールバック手段として扱わないでください（推論）。テストでは、10月21日に作成した Argo CD Capability は `3.4.6-eks-2`、その翌日に別のクラスターで作成したものは `3.4.7-eks-1` を報告しました。コントローラーのバージョンはクラスターのアップグレードとは独立して変更される可能性があります。

不具合のあるリリースに備えるには、次のようにしてください。

| 準備 | 方法 | 根拠 |
|---|---|---|
| バージョン変更の記録 | `describe-capability` から `capability.version` を定期的に取得し、インシデントと関連付ける | 測定済み（フィールドを確認） |
| 検証用クラスター | 本番と同じ Capability を持つクラスターで、本番用 RGD、Application、ACK CR を先に実行する。ロールアウトの順序は制御できないため、本番より先に更新される保証はない | 推論 |
| Git で動作を固定 | ヘルスチェック（`resource.customizations`）、同期オプション、RBAC を Git で管理し、再作成や移行後も同じ動作を再現できるようにする | 測定済み（設定を適用） |
| AWS Support | ユーザー側でロールバックする方法はないため、問い合わせを行う。AWS のドキュメントでは、自動修復のタイミング調整について Support に問い合わせるよう案内している | 推論（自動修復のタイミングについてはドキュメントによる） |
| セルフマネージドへの一時的なフォールバック | RETAIN を指定して Capability を削除すると CRD とリソースが残り、同じ CRD を使う OSS コントローラーが引き継ぐ（kro、ACK、Argo CD で測定済み）。Argo CD では、クラスター Secret の `server` を EKS ARN から API URL（ローカルでは `https://kubernetes.default.svc`）に変更する必要があった。ARN で登録したリモートまたはプライベートのスポークには、OSS で独自のネットワーク経路と認証が必要。マネージドに戻すには再作成が必要（Argo CD は約6分） | 測定済み |
| サービス単位での ACK ロールバック | 影響を受けたサービスだけを `disabledServices` に追加し、セルフマネージドのコントローラーをインストールするかスケールアップする。OSS コントローラーには独自の IAM 設定が必要で、IAMRoleSelector を使う場合は `featureGates.IAMRoleSelector=true` と `enableCARM=false` も必要。Capability がインストールした CRD 上で OSS Chart を実行することは未テスト。インストール済み CRD は残る（測定済み） | ドキュメントによる |

バージョンを確実に固定する必要があるなら、AWS のドキュメント自体もセルフマネージドを推奨しています（「特定の Kubernetes リソース API バージョン、カスタムコントローラービルドが必要」な場合）。

<span id="multicluster"></span>

## 8. マルチクラスターと Blue/Green による置き換え

### Argo CD ハブとプライベートスポーク

ハブクラスターの Argo CD Capability は、同じアカウントと VPC 内にある、API エンドポイントがプライベートのみのスポークを、ネットワーク設定（endpoint、セキュリティグループ、ルート）なしで登録できました。別の VPC にあるワークステーションからスポークには接続できなかったため、接続には AWS が提供する経路が使われているようです。スポークには、手動で作成したハブの Capability ロール用の access entry が必要です。

| スポーク access entry の権限 | 結果 |
|---|---|
| `AmazonEKSEditPolicy` + `AmazonEKSAdminViewPolicy` | 接続と認証には成功したが、`CreateNamespace=true` は `namespaces is forbidden` で失敗。自動再試行5回（約303秒）を使い切った |
| + `AmazonEKSArgoCDClusterPolicy`、その後に手動同期 | 11.1秒で同期され、Healthy になった |

- クラスター Secret に指定できるのは EKS ARN のみなので、EKS 以外のクラスターはデプロイ先にできません（ドキュメントによる）。
- Application の料金はデプロイ先クラスターごとに数えるため、ハブ配置でもクラスターごとの配置でも同じ料金です。増えるのは Argo CD インスタンス数に応じた Capability 料金だけです。ただし、ハブの Capability ロールはすべてのスポークへの書き込みアクセスを持つため、AppProject のデプロイ先を制限するか、チームごとに Capability を分けることを検討してください。
- ドキュメントによると、別アカウントのクラスターで必要なのはハブの Capability ロール用の access entry だけです（未テスト）。マネージドの上限は、リモートクラスター100個、Application 3,000個です。

### kro と ACK の配置場所

kro と ACK の Capability が管理するのは、それぞれ自身のクラスターだけです。ハブの Argo CD からスポークに RGD インスタンスや ACK CR をデプロイするには、スポークにも kro または ACK（マネージドまたは OSS）が必要です。

| 構成 | 適するケース | 懸念事項 |
|---|---|---|
| すべてのクラスターに kro を配置し、ApplicationSet で RGD をロールアウト | アプリチームが各クラスターで同じ API を使う | Capability 料金と RBAC 作業がクラスター数に応じて増える。ドキュメントでは、クラスター間で kro のバージョンが同一である保証はない（未テスト） |
| kro はハブだけに配置し、RGD でスポーク用 ACK リソースと Argo CD Application を作成 | プラットフォームの抽象化を1か所で定義 | 権限と影響範囲がハブに集中する。スポークのアプリチームは kro API を直接使えない（未テスト） |
| ACK 集中型（ハブ） | データベース、IAM、VPC などプラットフォームが所有するリソース | ハブ Capability ロールがすべてのアカウントとリソースの権限を持つ |
| ACK 分散型（クラスターごと） | ワークロードの隣に Queue や Bucket を宣言する | IAMRoleSelector の設定がクラスター数に応じて増える |
| ACK ハイブリッド型 | 管理者スコープのリソースはハブに、ワークロードスコープのリソースはスポークに配置 | 1つのリソースを2か所で宣言しないよう、スコープのルールが必要 |

どの構成でも、同じ AWS リソースを2つのクラスターが同時に宣言しないよう、スコープのルールを設定してください。

### Blue/Green による置き換え

- **Argo CD**: Capability はクラスターに属するため、Argo CD をホストするクラスターを置き換える際は Capability を再作成する必要があります。デフォルトのアドレス `argocd-<ID>-<account ID>.eks-capabilities.<region>.amazonaws.com` はクラスターごとに異なるため、UI と webhook の URL が変わります。作成時に `endpointPrefix` を設定すると、削除後に同じプレフィックスで再作成した際もアドレスは維持されました（同じクラスター上でのみテスト）。アドレスにはクラスター固有の情報が含まれていないため、別のクラスターに移動した後も使えるはずです。アカウントとリージョン内でプレフィックスが一意である場合（未テスト）、古いクラスターと新しいクラスターで同時に使うことはできません。その場合、置き換えは削除してから再作成する形になり、その間は UI、webhook、同期が停止します（削除に100秒、再作成に338秒を測定）。この停止を許容できない場合は、先に新しいプレフィックスで新しい Capability を起動して Git の webhook URL を変更します。新しい方を有効にする前に、古い方の自動同期を無効にするか、その Application を cascade なしで削除してください。また、対象クラスターに新しい Capability ロールの access entry をあらかじめ作成してください（未テスト）。作成後にプレフィックスを変更することはできません。頻繁に置き換えるワークロードクラスターではなく、専用ハブに Argo CD を配置してください。
- **kro**: ClusterRole とバインディングは Git 経由で移せますが、access entry への Kubernetes グループ追加は EKS API の呼び出しです。クラスターを作成する IaC（eksctl、Terraform など）に含めてください。
- **ACK**: 1つの方法は、古いクラスターの CR を `deletion-policy: retain` で削除し、新しいクラスターで `adoption-policy: adopt-or-create` を使って同じリソースを引き継ぐことです（各手順は測定済み。クラスターをまたぐ一連の手順は未テスト）。SCP が `eks:eks-capability-arn` タグに基づいて変更をブロックしている場合、新しい Capability では ARN が変わるため、引き継ぎがブロックされる可能性があります。切り替え中は条件を緩和するか、代わりに環境またはチームのタグを条件にしてください。

<span id="compare"></span>

## 9. セルフマネージドとの比較と選択基準

| 項目 | マネージド Capability | セルフマネージド（OSS） |
|---|---|---|
| インストール時間 | Argo CD 349秒、kro 70秒、ACK 386秒 | Argo CD 43.4秒、kro 15.6秒、ACK コントローラー3つで46秒 |
| ノードリソース | なし | Argo CD は7 Pod（メモリ339～624Mi）、kro は1 Pod（requests 256m、128Mi）、ACK は3 Pod（各 requests 50m、64Mi） |
| バージョン | AWS が選択し、固定できない | 自分で選択（テスト時点の最新は Argo CD v3.5.5、ACK s3 1.13.1） |
| デフォルトの権限 | 範囲が狭い。デプロイ、子リソース、IAM の権限を自分で付与する | Argo CD と kro の Chart のデフォルトは `*/*/*` |
| パフォーマンス | kro、ACK、Argo CD の自動修復は OSS と同程度。Argo CD のデフォルトポーリングは遅い | 基準値（同じバージョンで Argo CD 3.4.6 と kro 0.9.4 を測定。ACK OSS は1つ新しいバージョンで実行） |
| SSO | Identity Center のみ。設定項目は2つ | Dex、OIDC などを自分で設定 |
| リモートクラスター | EKS ARN + access entry。ネットワーク設定なしでプライベートクラスターを利用可能 | クラスターごとに API URL、認証、ネットワーク経路が必要 |
| 未対応機能 | Argo CD Notifications、CMP、`argocd admin`、Lua 標準ライブラリ、ACK FieldExport | なし |
| 直接調整できない項目 | Argo CD のポーリング、ACK の再同期間隔、コントローラーフラグとリソース制限。Argo CD の自動修復バックオフは AWS Support 経由でのみ調整可能 | すべて調整可能 |
| ログ | Vended Logs | `kubectl logs`、独自のログ収集 |

マネージドが適しているケース：

- 複数の EKS クラスター、特にプライベートクラスターや別アカウントのクラスターにデプロイするハブを構築する
- AWS へのサインインがすでに Identity Center に集約されており、Argo CD の SSO を自分で運用したくない
- Kubernetes から複数の AWS サービスを管理しており、サービスごとに ACK コントローラーを実行する負担を減らし、チームごとに IAM を分離したい
- プラットフォームコントローラーの権限をデフォルトで狭くし、access entry と RBAC で明示的に管理したい

セルフマネージドを継続すべきケース：

- Notifications、CMP、FieldExport、または Lua 標準ライブラリに依存している
- デプロイ先に EKS 以外のクラスターが含まれる
- Argo CD だけに組織の Identity Center とは異なる IdP を使う必要があり、アカウントインスタンスも選択できない
- コントローラーのバージョン、アップグレード時期、ポーリングまたは再同期の間隔を自分で制御する必要がある

クラスターが1つを超える前に評価するのがよいタイミングです。ハブの配置場所、Identity Center インスタンス、`endpointPrefix` は、作成後に固定されたり変更が難しくなったりするためです。また、セルフマネージドの Argo CD で HA 構成の再構築やメジャーアップグレードが必要なときも、評価に適しています。AWS の移行手順では、既存のコントローラーをゼロにスケールし、Application と Secret を移動して、`destination.server` を ARN に変更します。その間は同期が停止します（未テスト）。

<span id="pricing"></span>

## 10. 料金

料金はソウル（ap-northeast-2）のもので、2026年10月21日に AWS Pricing API で照会し、月730時間として計算しました。

| Capability | Capability の料金 | オブジェクト単位の料金 | 例（月額） |
|---|---|---|---|
| Argo CD | 1時間あたり $0.034799（月あたり約$25.4） | Application-hour あたり $0.001726（デプロイ先クラスターごとに計上） | 9アプリで約$36.7、100アプリで約$151 |
| kro | 1時間あたり $0.006038（月あたり約$4.4） | インスタンス時間あたり $0.000061 | 100インスタンスで約$8.9 |
| ACK | 1時間あたり $0.006038（月あたり約$4.4） | リソース時間あたり $0.000061 | 200リソースで約$13.3 |

比較のため、デフォルトのセルフマネージド構成で m7g.large の料金（ソウルでは1時間あたり $0.1003）を按分すると、Argo CD（メモリ624Mi）は約$5.6、kro（CPU requests 256m）は約$9.4、ACK コントローラー3つ（CPU requests 合計150m）は約$5.5になります。HA 構成やアプリ、サービスの増加に応じて、OSS 側の費用も上がります。マネージド Argo CD はアプリ数の増加とともに割高になります。kro と ACK では差が小さいため、運用負荷と機能の不足を基準に判断してください。

<span id="refs"></span>

## 11. 検証範囲と参考資料

測定では、ap-northeast-2 の単一アカウントを使用しました。クラスターは EKS 1.36.4 を1つ、アップグレードとマルチクラスターのテスト用に2つ追加で使用しました（ハブは1.36から1.37へアップグレード、プライベートスポークは1.37）。シナリオの実行回数は1～5回で、Argo CD Application は最大9個、kro インスタンスは6個、ACK リソースは約20個でした。ACK では S3、SQS、DynamoDB のみをテストしました。以下はテストしておらず、ドキュメントの記載に依存しています。Okta または Entra ID との連携と Identity Center のアカウントインスタンス、VPC endpoint 経由のプライベートアクセス、別アカウントまたは別 VPC のクラスター登録、Notifications と CMP、クロスアカウント ACK、マネージドと OSS を同時に実行するダウンタイムなしの移行、クラスターをまたぐ ACK の retain 後の adopt の一連の手順です。測定後、テストクラスターと AWS リソースは削除しました。

- [EKS Capabilities](https://docs.aws.amazon.com/eks/latest/userguide/capabilities.html)
- [EKS Capabilities に関する考慮事項](https://docs.aws.amazon.com/eks/latest/userguide/capabilities-considerations.html)
- [Capability の Kubernetes リソース](https://docs.aws.amazon.com/eks/latest/userguide/capability-kubernetes-resources.html)
- [Argo CD に関する考慮事項](https://docs.aws.amazon.com/eks/latest/userguide/argocd-considerations.html)
- [Argo CD の EKS Capability とセルフマネージド Argo CD の比較](https://docs.aws.amazon.com/eks/latest/userguide/argocd-comparison.html)
- [ターゲットクラスターの登録](https://docs.aws.amazon.com/eks/latest/userguide/argocd-register-clusters.html)
- [Argo CD 設定の構成](https://docs.aws.amazon.com/eks/latest/userguide/argocd-configure-settings.html)
- [kro の権限の設定](https://docs.aws.amazon.com/eks/latest/userguide/kro-permissions.html)
- [kro の EKS Capability とセルフマネージド kro の比較](https://docs.aws.amazon.com/eks/latest/userguide/kro-comparison.html)
- [ACK の権限の設定](https://docs.aws.amazon.com/eks/latest/userguide/ack-permissions.html)
- [ACK の EKS Capability とセルフマネージド ACK の比較](https://docs.aws.amazon.com/eks/latest/userguide/ack-comparison.html)
- [EKS Capabilities コントローラーのログへのアクセス](https://docs.aws.amazon.com/eks/latest/userguide/capabilities-controller-logs.html)
- [クラスターを以前の Kubernetes バージョンにロールバックする](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [Amazon EKS の料金](https://aws.amazon.com/eks/pricing/)
- 測定ブログ（韓国語）：[マネージド Argo CD](https://blog.atomai.click/eks-capabilities-argocd/)、[マネージド kro](https://blog.atomai.click/eks-capabilities-kro/)、[マネージド ACK](https://blog.atomai.click/eks-capabilities-ack/)
- テストマニフェスト：[Atom-oh/eks-capabilities-demo](https://github.com/Atom-oh/eks-capabilities-demo)

[EKS Capabilities のクイズ](../quizzes/eks/13-eks-capabilities-quiz.md)
