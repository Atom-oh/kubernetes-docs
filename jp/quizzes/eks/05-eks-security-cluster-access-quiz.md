# EKS クラスターアクセス認証クイズ

> **最終更新日**: 2026年11月21日

このクイズでは、[EKS クラスターアクセス認証: IAM とアクセスエントリ](../../eks/05-eks-security-cluster-access.md)の理解度を確認します。

## クイズの概要
- IAM 認証と Kubernetes 認可
- EKS クラスターのロールとプロビジョニングを実行する呼び出し元
- 認証モードとアクセスエントリ
- アクセスポリシーの適用範囲と検証

## 選択式問題

### 1. IAM ユーザーまたはロールについて、ID 認証と Kubernetes 認可を正しく組み合わせる EKS の設定はどれですか？

- A) IAM の管理権限だけを使用する
- B) ID の認証経路を設定せずに RBAC ルールを作成する
- C) IAM クラスターアクセスに加え、適切な RBAC ルールや EKS アクセスポリシーを設定する
- D) API エンドポイントのネットワーク制限だけを使用する

<details>
<summary>回答を表示</summary>

**回答: C) IAM クラスターアクセスに加え、適切な RBAC ルールや EKS アクセスポリシーを設定する**

**解説:**

IAM は、設定済みの EKS アクセス経路を通じて、対象となる人間または自動化の ID を認証します。Kubernetes RBAC と EKS アクセスポリシーは Kubernetes 操作を認可し、両者の許可は加算されます。ネットワーク制限は別の層であり、認可の代わりにはなりません。Pod から Kubernetes への認証には通常、その ServiceAccount トークンが使われます。IRSA/Pod Identity は、代わりにワークロード用の AWS 認証情報を提供します。

EKS クラスターのサービスロールと人間の開発者ロールは、目的が異なります。開発者に AmazonEKSClusterPolicy をアタッチしても Kubernetes アクセスは許可されません。また、DescribeCluster/ListClusters の権限や kubeconfig ファイルがあっても、ワークロードに対する権限は付与されません。

**適用範囲を限定した実装:** 認可されたプラットフォーム運用担当者が、既存の承認済み開発者 IAM ロールに対して、以下の Namespace と RBAC を用意します。クラスターでは、すでにアクセスエントリがサポートされている必要があります。既存の管理者/ノードのマッピングを維持し、認証モードの移行を確認してください。サンプルの ConfigMap で aws-auth を上書きしないでください。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: security-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
```



```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the verified cluster name}"
: "${AWS_REGION:?Set its Region}"
: "${DEVELOPER_ROLE_ARN:?Set a prepared IAM role ARN, not an STS session ARN}"
MODE=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.accessConfig.authenticationMode --output text)
case "$MODE" in
  API|API_AND_CONFIG_MAP) ;;
  *) echo "Access entries are not enabled; review the migration first"; exit 1 ;;
esac
aws eks list-access-entries --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --output json > security-access-entries.json
python3 - "$DEVELOPER_ROLE_ARN" <<'PY'
import json, sys
with open("security-access-entries.json") as stream:
    existing = json.load(stream)["accessEntries"]
if sys.argv[1] in existing:
    raise SystemExit("Entry already exists; inspect its groups/policies instead of overwriting")
PY
aws eks create-access-entry --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --principal-arn "$DEVELOPER_ROLE_ARN" --type STANDARD \
  --kubernetes-groups security-demo-developers
```



```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: developer
  namespace: security-demo
rules:
- apiGroups:
  - ''
  resources:
  - pods
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - apps
  resources:
  - deployments
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
- apiGroups:
  - batch
  resources:
  - jobs
  verbs:
  - get
  - list
  - watch
  - create
  - update
  - patch
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developer
  namespace: security-demo
subjects:
- kind: Group
  name: security-demo-developers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer
  apiGroup: rbac.authorization.k8s.io
```

アクセスエントリのグループ名は、RoleBinding の subject と一致している必要があります。このロールが許可するのは、security-demo 内での列挙された操作だけです。ほかの既存の許可によってアクセス範囲が広がる場合があります。Deployment/Job の作成によって、その Namespace 内の Secrets、PVC、ServiceAccounts が間接的に利用される可能性があります。そのため、Secret を直接読み取るルールがないことは、テナント間のセキュリティ境界にはなりません。テナントを分離し、アドミッションと所有権の制御を通じて、ワークロードの ID とリソースの使用を制限してください。

別途審査した閲覧者には、Namespace の範囲を限定した AmazonEKSViewPolicy の関連付けを代わりに使用できます。追加する前に既存のアクセスポリシーを確認してください。追加しても、より広範な RBAC やその他のアクセスポリシーによる許可は取り消されません。`eks:namespaces` はアクセスポリシーの関連付けリクエストをフィルタリングするものであり、一般的な kubectl リクエストをフィルタリングするものではありません。

**実際のログインを検証する:** 呼び出し元は、クラスターを検出し、承認済みロールを引き受けられる必要があります。次のコマンドは既定のコンテキストを置き換えず、一時的な kubeconfig を作成します。

```bash
set -euo pipefail
umask 077
: "${CLUSTER_NAME:?Set the reviewed cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
: "${DEVELOPER_ROLE_ARN:?Set the intended IAM role ARN}"
review_dir=$(mktemp -d "${TMPDIR:-/tmp}/eks-login-check.XXXXXXXX")
trap 'rm -rf -- "$review_dir"' EXIT
aws eks update-kubeconfig --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --role-arn "$DEVELOPER_ROLE_ARN" --kubeconfig "$review_dir/config"
kubectl --kubeconfig "$review_dir/config" auth can-i list pods -n security-demo
kubectl --kubeconfig "$review_dir/config" auth can-i create jobs -n security-demo
kubectl --kubeconfig "$review_dir/config" auth can-i list pods -n another-team
```

結果を意図した許可と照合し、予期しない Namespace をまたぐ権限があれば調査してください。`--as` は偽装/RBAC をテストするものであり、IAM アクセスポリシー経路が機能することを確認するものではありません。このクイズでは、実際の IAM ログインや Kubernetes 認可テストは実行していません。ローカルでの根拠は、スキーマ/シェルのチェックと、モックを使ったアクセスエントリのフローです。

参考資料: [EKS アクセスエントリ](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)、[EKS アクセスポリシー](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)、[Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)。

</details>

### 2. CONFIG_MAP 認証モードから API_AND_CONFIG_MAP または API に移行する場合、正しい説明はどれですか？

- A) 自由に元に戻せるわけではないため、管理者/ノードのマッピングを維持し、復旧経路を計画する
- B) 後からいつでも元に戻せるため、事前確認なしにモードを切り替える
- C) まずノードロールを省いた短いサンプル ConfigMap で aws-auth を上書きする
- D) API モードでは aws-auth のすべてのマッピングが自動的にアクセスエントリへ移行されるため、確認を省略する

<details>
<summary>回答を表示</summary>

**回答: A) 自由に元に戻せるわけではないため、管理者/ノードのマッピングを維持し、復旧経路を計画する**

**解説:**

`describe-cluster` の `accessConfig` で現在の認証モードを確認し、移行前に既存の管理者/ノードのマッピングを維持してください。CONFIG_MAP から API_AND_CONFIG_MAP/API への移行は、自由に元に戻せる切り替えではありません。ノードロールを省いた短いサンプルで aws-auth を上書きしないでください。API のみのモードを選択する前に、すべての ID、ポリシー、ノードと復旧経路を確認してください。

</details>

### 3. 標準的な EKS クラスター IAM ロールと開発者の権限について、正しい説明はどれですか？

- A) kubectl を使用するには、クラスターのロールが開発者 IAM ユーザーを信頼する必要がある
- B) 開発者ロールに AmazonEKSClusterPolicy を付与すると、すべての Namespace へのアクセスが許可される
- C) CreateCluster はリソース ARN によるスコープ指定をサポートしているため、クラスター ARN だけに限定すれば十分である
- D) クラスターのロールが信頼するのは開発者の ID ではなく、`eks.amazonaws.com` サービスである

<details>
<summary>回答を表示</summary>

**回答: D) クラスターのロールが信頼するのは開発者の ID ではなく、`eks.amazonaws.com` サービスである**

**解説:**

標準的な EKS クラスターのロールの信頼関係では、`eks.amazonaws.com` サービスプリンシパルに対して `sts:AssumeRole` が許可されています。これは開発者の権限ポリシーではありません。プロビジョニングを実行する呼び出し元には、選択した構成に必要なアクションと、対象ロールに対する PassRole が別途必要です。現在の認可リファレンスでは、CreateCluster はリソース ARN によるスコープ指定に対応していないため、サポートされているリクエスト条件を使用してください。開発者ロールに AmazonEKSClusterPolicy をアタッチしても、Kubernetes アプリケーションへのアクセスは許可されません。

</details>

### 4. 開発者のアクセスエントリと RBAC を設定した後、`kubectl auth can-i --as=...` の結果から何がわかりますか？

- A) 実際の IAM ログインとアクセスポリシー経路の両方が機能することの証明
- B) Kubernetes の偽装/RBAC のみであり、IAM アクセスポリシー経路が機能する証明にはならない
- C) kubeconfig 自体が権限を付与するため、それ以外の確認は不要
- D) `--as` は RBAC を完全に迂回するため、IAM ポリシーの評価のみ

<details>
<summary>回答を表示</summary>

**回答: B) Kubernetes の偽装/RBAC のみであり、IAM アクセスポリシー経路が機能する証明にはならない**

**解説:**

`kubectl --as` でテストできるのは Kubernetes の偽装と RBAC であり、IAM アクセスポリシー経路が機能することの証明にはなりません。更新の反映には時間がかかることがあるため、実際に使用する対象の IAM ログインでテストしてください。kubeconfig はクライアントにクラスターと認証情報の仕組みを指定するもので、それ自体が権限を付与することはありません。

</details>

### 5. Namespace の範囲を限定した AmazonEKSViewPolicy の関連付けと、`eks:namespaces` 条件について、正しい説明はどれですか？

- A) View を追加すると、プリンシパルに既に付与されている、より広範な RBAC 権限が取り消される
- B) `eks:namespaces` によって、すべての kubectl API 呼び出しが指定した Namespace に制限される
- C) `eks:AccessKubernetesApi` は kubectl 用の一般的な Namespace RBAC 権限である
- D) View を追加しても何も取り消されず、`eks:namespaces` は関連付けリクエストをフィルタリングする

<details>
<summary>回答を表示</summary>

**回答: D) View を追加しても何も取り消されず、`eks:namespaces` は関連付けリクエストをフィルタリングする**

**解説:**

許可を追加する前に、`list-associated-access-policies` でエントリに設定済みのグループと関連付け済みのポリシーを確認してください。View を追加しても、より広範な RBAC/アクセスポリシーによる許可は取り消されません。`eks:namespaces` 条件はアクセスポリシーの関連付けリクエストをフィルタリングするものであり、kubectl API 呼び出しに対する一般的な Namespace フィルターではありません。`eks:AccessKubernetesApi` はコンソール表示用の権限です。

</details>
