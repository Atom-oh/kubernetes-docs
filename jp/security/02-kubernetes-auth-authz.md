# Kubernetes 認証および認可システム

> **対象範囲**: Kubernetes stable API および Amazon EKS ユーザーアクセス管理
> **最終更新**: October 12, 2026

## 概要

認証はリクエストの識別情報を確立し、認可はその識別情報が実行できる API 操作を決定し、admission は認可された変更に追加のポリシーを適用します。以下のマニフェストは互いに独立した学習用の例です。最初に namespace、管理者権限、証明書、および webhook サーバーを準備してください。実行中の cluster/API 呼び出しまたは EKS アクセス変更はテストしていません。

`kube-apiserver` フラグの例は、**セルフマネージド control plane** に適用されます。EKS ではマネージドアクセス設定を使用してください。これらの例は、API server フラグの設定や CA private key の取得を指示するものではありません。

## 認証

認証は、ユーザーまたはサービスが主張するとおりの存在であることを検証するプロセスです。Kubernetes は複数の認証方式をサポートしており、これらは同時に有効化できます。

複数の authenticator がある場合、最初に成功した結果が使用されますが、評価順序は保証されません。無効な認証情報は認証に失敗する可能性があります。認証情報のないリクエストの処理は匿名認証の設定に依存し、匿名の識別情報にも認可が必要です。

### 認証戦略

#### 1. X.509 証明書

API server の `--client-ca-file` で信頼される **client CA** によって署名された証明書を使用します。subject の CN はユーザー名を、O は group を提供します。証明書には client authentication (`clientAuth`) usage が必要です。server の TLS 証明書を検証する CA は、client を認証する CA とは異なる目的を果たします。

**ローカル private key および CSR の例:**

```bash
umask 077
auth_lab_dir=$(mktemp -d)
openssl genrsa -out "$auth_lab_dir/john.key" 2048
openssl req -new -key "$auth_lab_dir/john.key" \
  -out "$auth_lab_dir/john.csr" -subj '/CN=john/O=engineering'
openssl req -in "$auth_lab_dir/john.csr" -noout -verify
```

これらのコマンドは証明書を発行しません。**CSR のみ**を、識別情報、group、usage、有効期間をレビューする必要がある承認済みの発行者に送信してください。CA private key をユーザーにコピーしたり、レビューなしで組織名を承認したりしないでください。EKS の `beta.eks.amazonaws.com/app-serving` signer は serving certificate 用であり、ユーザー client-certificate signing をサポートしません。EKS ユーザーアクセスには、以下の IAM/OIDC 経路を使用してください。

**発行後の kubeconfig:**

```yaml
apiVersion: v1
kind: Config
clusters:
- name: my-cluster
  cluster:
    certificate-authority: /secure/path/server-ca.crt
    server: https://kubernetes.example.com
users:
- name: john
  user:
    client-certificate: /secure/path/john.crt
    client-key: /secure/path/john.key
contexts:
- name: john@my-cluster
  context:
    cluster: my-cluster
    user: john
    namespace: default
current-context: john@my-cluster
```

パスを発行済みのファイルに置き換え、private key と kubeconfig へのアクセスを制限してください。`*-data` フィールド内の Base64 は暗号化ではありません。信頼できない kubeconfig ファイルは使用前に検査してください。credential plugin を通じてコマンドを実行される可能性があります。

#### 2. Service Account Token

ServiceAccount は namespace スコープの workload identity です。すべての namespace には `default` account があり、Pod の `serviceAccountName` は同じ namespace 内の account を参照します。account を選択するだけでは、application resource へのアクセスは付与されません。

この例は API を呼び出さず、token の自動マウントを無効にしています。例の image は network service を提供しません。

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: default
automountServiceAccountToken: false
---
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
  namespace: default
spec:
  serviceAccountName: my-service-account
  automountServiceAccountToken: false
  containers:
  - name: my-container
    image: registry.k8s.io/pause:3.10
```

`automountServiceAccountToken` はトップレベルの ServiceAccount フィールドおよび Pod の `spec` フィールドです。Pod の設定が優先されます。これはデフォルトの mount を制御するものであり、明示的に宣言された `serviceAccountToken` projected volume を防ぐものではありません。

API アクセスを必要とする Pod では、kubelet が TokenRequest を介してデフォルトの projected token を取得およびローテーションします。デフォルトの token ファイルは `/var/run/secrets/kubernetes.io/serviceaccount/token` です。application はローテーションされたファイルを再読み込みする必要があります。有効期限と audience binding は露出を減らしますが、bearer token を安全に開示できるようにするものではありません。account を作成すると長期間有効な Secret token が自動的に作成されると想定しないでください。[quiz の projected-volume の例](../quizzes/security/02-kubernetes-auth-authz-quiz.md)では、カスタム audience と要求される有効期間を扱っています。

#### 3. OpenID Connect (OIDC)

OIDC により、API server は外部 identity provider からの **ID token** を検証できます。issuer、audience、signature/expiry validation、および identity mapping を設定します。API server は対話型ログインを提供せず、refresh token も発行しません。client は、identity provider 用にレビュー済みのツールまたは `exec` credential plugin を使用します。

これらは**セルフマネージド API server の追加フラグ**であり、完全な起動コマンドや kubeconfig ではありません。例の HTTPS issuer および client ID を置き換えてください。

```text
--oidc-issuer-url=https://idp.example.com
--oidc-client-id=kubernetes
--oidc-username-claim=sub
--oidc-username-prefix=oidc:
--oidc-groups-claim=groups
--oidc-groups-prefix=oidc:
```

既存の `system:` group などの identity との衝突を避けるため、ユーザー名と group に prefix を付けてください。構造化された `AuthenticationConfiguration` は代替手段です。`--authentication-config` と `--oidc-*` フラグを組み合わせないでください。EKS 用の外部 OIDC provider は、以下の別のマネージド手順で設定してください。

#### 4. Webhook Token 認証

セルフマネージド API server は、`authentication.k8s.io/v1` **TokenReview** を外部サービスに送信します。以下は、**API server がそのサービスに到達するために使用する別個の kubeconfig** です。ユーザーの kubeconfig における `authentication.webhook` フィールドではありません。

```yaml
apiVersion: v1
kind: Config
clusters:
- name: authentication-service
  cluster:
    server: https://authn.example.com/authenticate
    certificate-authority: /etc/kubernetes/authn-webhook/ca.crt
users:
- name: kube-apiserver-webhook-client
  user:
    client-certificate: /etc/kubernetes/authn-webhook/client.crt
    client-key: /etc/kubernetes/authn-webhook/client.key
contexts:
- name: webhook
  context:
    cluster: authentication-service
    user: kube-apiserver-webhook-client
current-context: webhook
```

`/etc/kubernetes/authn-webhook.kubeconfig` にインストールする場合は、API server に `--authentication-token-webhook-config-file=/etc/kubernetes/authn-webhook.kubeconfig` および `--authentication-token-webhook-version=v1` を設定してください。参照される証明書とサービスは別途プロビジョニングしてください。サービスは token と想定する audience を検証し、TokenReview response を返す必要があります。mutual TLS、credential protection、cache TTL、および failure behavior を設計してください。この例には webhook 実装も可用性の検証も含まれません。

#### 5. Authentication Proxy

認証 proxy は呼び出し元を検証し、結果のユーザー名と group を転送します。信頼する header に名前を付けるだけでは信頼を確立できません。まず、専用の front-proxy CA と許可された client-certificate CN を使用して、proxy の TLS identity を認証してください。

**セルフマネージド API server フラグの抜粋:**

```text
--requestheader-client-ca-file=/etc/kubernetes/front-proxy-ca.crt
--requestheader-allowed-names=front-proxy-client
--requestheader-username-headers=X-Remote-User
--requestheader-group-headers=X-Remote-Group
```

proxy は呼び出し元が指定した identity header を取り除き、検証済みの値に置き換える必要があります。通常の user-client CA を proxy CA として再利用したり、許可する CN を空のままにしてすべての client certificate を信頼したりしないでください。この抜粋は proxy 自体を実装するものではありません。

### ユーザーと Group

Kubernetes では、ユーザーは次のように分類されます。

1. **通常ユーザー**: cluster の外部で管理され、Kubernetes が直接管理することはありません。
2. **Service Account**: Kubernetes API により管理される account です。

ユーザーは 1 つ以上の group に所属でき、group は認可ポリシーで使用されます。

## 認可

認可は、認証済みユーザーが要求されたアクションを実行する権限を持つかどうかを検証するプロセスです。Kubernetes は複数の認可 module をサポートしています。

### 認可モード

#### 1. RBAC (Role-Based Access Control)

RBAC は role-based access control を提供し、現在 Kubernetes で最も広く使用されている認可メカニズムです。

**主要な概念:**

1. **Role**: namespace 内の権限を定義します。
2. **ClusterRole**: cluster resource、non-resource URL、または namespace スコープ resource に対して再利用可能な権限のための cluster スコープ定義です。
3. **RoleBinding**: 同じ namespace 内の Role または ClusterRole を参照し、**binding namespace 内でのみ**権限を付与します。ServiceAccount subject は別の namespace に明示的に所属できます。
4. **ClusterRoleBinding**: ClusterRole の権限を cluster 全体に付与します。Role を参照することはできません。

role 定義は binding がなければ何も付与しません。RBAC は許可された権限を追加し、明示的な deny ルールはありません。Secret の `get/list/watch` は secret data の読み取りを許可するため、これらの例では Pod の読み取りを使用します。

**Role の例:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
```

**RoleBinding の例:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default
subjects:
- kind: User
  name: john
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

**ClusterRole の例:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: pod-reader-reusable
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
```

**ClusterRoleBinding の例:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-pods-global
subjects:
- kind: Group
  name: cluster-inventory-readers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: pod-reader-reusable
  apiGroup: rbac.authorization.k8s.io
```

この ClusterRoleBinding は、**すべての namespace にまたがる Pod 情報**を明示的に必要とする operations group を示すものであり、デフォルトの推奨事項ではありません。単一の namespace の場合は、代わりに `roleRef.kind: ClusterRole` および `roleRef.name: pod-reader-reusable` を使用する RoleBinding をその namespace 内で使用してください。

#### 2. ABAC (Attribute-Based Access Control)

ABAC は attribute-based access control を提供します。ポリシーは JSON ファイルで定義されます。

**ポリシーの例:**

```json
{
  "apiVersion": "abac.authorization.kubernetes.io/v1beta1",
  "kind": "Policy",
  "spec": {
    "user": "john",
    "namespace": "default",
    "apiGroup": "",
    "resource": "pods",
    "readonly": true
  }
}
```

ABAC は既存のセルフマネージド cluster を理解するために含まれています。`--authorization-policy-file` が読み込むポリシーは、Kubernetes API resource ではなく、**1 行に 1 つの JSON object** を含むファイルです。上記のインデントは説明のためのものです。実際のファイルでは各ポリシーを 1 行にシリアライズしてください。変更には API server の再起動が必要です。新しい構成には RBAC を推奨します。このフラグは EKS 構成メカニズムではありません。

#### 3. Node 認可

Node 認可は kubelet 固有です。その identity は `system:nodes` に所属し、実際の node 名と一致するユーザー名 `system:node:<nodeName>` を使用する必要があります。これは workload のアクセスメカニズムではありません。セルフマネージド cluster では、kubelet による Node および Pod object への変更を制限するために、NodeRestriction admission と組み合わせてください。

#### 4. Webhook 認可

セルフマネージド API server は、`authorization.k8s.io/v1` **SubjectAccessReview** を外部サービスに送信します。認証 webhook と同じ connection-file format を、別個の authorization endpoint、CA、および client certificate とともに使用してください。`--authorization-webhook-config-file` および `--authorization-webhook-version=v1` を設定するか、構造化された `AuthorizationConfiguration` を使用して chain と failure policy を設定してください。ユーザーの kubeconfig に `authorization.webhook` フィールドはありません。

authorizer は設定された順序で実行され、最初の **Allow または Deny** が決定します。`NoOpinion` は次の authorizer に進み、すべてが NoOpinion の結果はアクセスを拒否します。後続の webhook は、RBAC がすでに許可したリクエストを拒否できません。`system:masters` は RBAC と webhook 認可をバイパスする特別な group です。通常の管理者に割り当てたり、role binding を削除すればアクセスが取り消されると考えたりしないでください。

### 認可のベストプラクティス

1. **最小権限の原則**: 必要最小限の権限のみを付与します。
2. **Role の分離**: 管理者、開発者、operator などの role に基づき、適切な権限を付与します。
3. **Namespace の分離**: team または project ごとに namespace を分離し、適切な権限を付与します。
4. **Service Account の分離**: application ごとに個別の service account を使用します。
5. **定期的な監査**: 認可ポリシーを定期的にレビューおよび更新します。

## Admission Control

admission control は、認証および認可の後、リクエストを処理する前に追加の検証と変更を実行します。

admission は作成、変更、削除、および一部の接続リクエストを処理します。**get/list/watch の読み取りは admission をバイパスします**。mutation は validation より先に行われ、どちらのフェーズでもリクエストを拒否できます。

### Admission Controller の種類

1. **Mutating Admission Controller**: リクエストを変更できます。
2. **Validating Admission Controller**: 変更せずにリクエストを検証するだけです。

### 主要な Admission Controller

1. **LimitRanger**: LimitRange で定義されたデフォルト値と最小/最大制約を適用します。
2. **ResourceQuota**: object 数、resource request、および類似の量に対して設定された namespace quota を確認します。測定された CPU/memory 消費量や支出の上限ではありません。
3. **PodSecurity**: namespace label に従って Pod Security Standards を適用します。以前の PodSecurityPolicy は Kubernetes 1.25 で削除されました。
4. **ServiceAccount**: Pod に service account を自動的に割り当てます。
5. **DefaultStorageClass**: class が指定されていない PVC にデフォルトの StorageClass を選択します。StorageClass を作成するものではありません。

### Dynamic Admission Control

動的 admission control は webhook により実装されます。

1. **MutatingAdmissionWebhook**: リクエストを変更できます。
2. **ValidatingAdmissionWebhook**: 変更せずにリクエストを検証するだけです。

**Webhook 構成の例:**

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: pod-policy-webhook
webhooks:
- name: pod-policy.example.com
  clientConfig:
    url: https://pod-policy.example.com/validate
    caBundle: <BASE64_ENCODED_CA_CERT>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    resources: ["pods"]
    operations: ["CREATE", "UPDATE"]
    scope: "Namespaced"
  namespaceSelector:
    matchLabels:
      training.example.com/pod-policy: "enabled"
  failurePolicy: Fail
  matchPolicy: Equivalent
  admissionReviewVersions: ["v1"]
  sideEffects: None
  timeoutSeconds: 5
```

この webhook は、明示的に label 付けされた namespace のみを対象にします。実際の HTTPS service、CA、およびリクエスト UID を保持する AdmissionReview 実装なしでインストールしないでください。`failurePolicy: Fail` は、呼び出しエラー/timeout 時に一致するリクエストをブロックします。`Ignore` は呼び出し失敗を無視します。正常に返された拒否を許可に変えるものではありません。専用の namespace で可用性と復旧をテストしてください。CEL ValidatingAdmissionPolicy は validation のもう 1 つの選択肢です。

## 実践的な実装例

### EKS における認証および認可の構成

#### IAM と RBAC の統合

現在の EKS IAM ユーザーアクセスには **access entry** を使用してください。IAM role は認証された identity を提供し、関連付けられた EKS access policy または Kubernetes RBAC は Kubernetes 権限を付与します。両方の経路からの許可された権限は累積されます。EKS access policy は IAM policy ではありません。

以下は、既存の cluster と IAM role に対する管理者の変更例です。最初に account、Region、cluster、`API` または `API_AND_CONFIG_MAP` mode、既存の `development` namespace、重複する access entry がないこと、および `eks:CreateAccessEntry` と RBAC 変更の権限を確認してください。これは infrastructure 作成 script や完全な migration 手順ではありません。

```bash
# Example inputs: replace with the approved cluster and existing IAM role.
region=ap-northeast-2
cluster_name=my-cluster
principal_arn=arn:aws:iam::123456789012:role/EKSDeveloperRole
aws eks describe-cluster --region "$region" --name "$cluster_name" \
  --query 'cluster.accessConfig.authenticationMode' --output text

# Mutates access configuration; run only after the prerequisites above.
aws eks create-access-entry --region "$region" --cluster-name "$cluster_name" \
  --principal-arn "$principal_arn" --type STANDARD \
  --kubernetes-groups eks:developers
```

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: developer-pod-reader
  namespace: development
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: eks-developer-pod-reader
  namespace: development
subjects:
- kind: Group
  name: eks:developers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer-pod-reader
  apiGroup: rbac.authorization.k8s.io
```

RBAC object を適用した後、role の実際の認証情報でアクセスを検証してください。この例では access policy を関連付けておらず、access entry を作成しても RBAC object は作成されません。既存の binding または policy により、有効な権限がこれらの Pod 読み取りより広くなる可能性があります。伝播遅延を考慮してください。

`aws-auth` ConfigMap はレガシーなメカニズムです。ConfigMap 全体を置き換えると、node/Fargate mapping が削除される可能性があります。`CONFIG_MAP` から `API_AND_CONFIG_MAP` への migration を計画し、mapping を移行して検証した後、`API` を使用してください。一度有効にすると、mode を戻しても API access は削除できません。`API` は ConfigMap mode に戻せません。両方を使用している間、同じ IAM principal に対しては access entry が優先されます。既存のすべての mapping が自動的に移行されるわけではありません。

`kubectl auth can-i --list` は EKS access policy からの権限を表示しません。`--as`/`--as-group` による impersonation は Kubernetes RBAC 評価を強制するため、IAM role の access-policy 権限をテストしません。namespace 外部での期待される拒否と Secret 読み取りを含め、実際の role として個別のアクションを検証してください。

#### OIDC Provider の構成

これら 3 つの経路は、方向と目的が異なります。

| 経路 | 認証対象と構成 |
|---|---|
| 外部 OIDC ユーザー → Kubernetes API | EKS `AssociateIdentityProviderConfig` を通じて外部 IdP を関連付け、そのユーザー/group を RBAC に bind します。EKS は public HTTPS 経由で issuer に到達する必要があります。customer-routed control-plane egress (`controlPlaneEgressMode=CUSTOMER_ROUTED`) では、issuer も VPC で構成する egress path を介して到達可能である必要があります。自己署名 issuer 証明書はサポートされません。これは IAM 認証を無効化しません。 |
| Pod → IRSA を通じた AWS API | cluster の ServiceAccount OIDC issuer に IAM trust を確立し、role trust を対象の namespace/ServiceAccount に制限し、必要な AWS resource のみを付与します。`eksctl utils associate-iam-oidc-provider` は外部ユーザーログインではなく、この経路に使用します。 |
| Pod → EKS Pod Identity を通じた AWS API | サポートされている execution environment で Pod Identity Agent と role association を使用します。これは IRSA の IAM OIDC provider 設定とは異なります。 |

どちらの workload メカニズムも、それだけでは Kubernetes API RBAC を付与しません。account 全体の S3 読み取り managed policy をデフォルト例として使用せず、実際の bucket/object ARN に権限をスコープしてください。構成の詳細は、[EKS 外部 OIDC](https://docs.aws.amazon.com/eks/latest/userguide/authenticate-oidc-identity-provider.html) および [workload IAM role](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html) に従ってください。

### マルチテナント Cluster のセキュリティ

マルチテナント環境では、tenant 間の分離が重要です。

**Namespace の分離:**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-a
  labels:
    tenant: a
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-from-other-namespaces
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes: [Ingress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          tenant: a
```

この policy は `tenant: a` の label を持つ**すべての** namespace からの ingress を許可します。他の ingress policy は許可を追加でき、egress は制限されません。CNI による NetworkPolicy の enforcement が必要です。信頼できる管理者のみが namespace label と policy を制御する必要があります。namespace だけでは、敵対的な tenant 間の強力な分離を保証できません。quiz には両方向の default deny が含まれています。DNS と必要な traffic に対する個別の許可をレビューしてください。

**Resource Quota:**

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-a-quota
  namespace: tenant-a
spec:
  hard:
    pods: "10"
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
```

## セキュリティのベストプラクティス

1. **定期的な証明書ローテーション**: 証明書を定期的に更新します。
2. **Service Account Token の自動マウントを無効化**: 必要でない場合は、service account token の自動マウントを無効にします。
3. **RBAC ポリシーの最小化**: 必要最小限の権限のみを付与します。
4. **Network Policy の実装**: Pod 間の通信を制限します。
5. **Audit Logging の有効化**: audit-policy coverage、sensitive-data exclusion、retention、および log access を検証してください。EKS では `audit` control-plane log type を有効にし、CloudWatch への配信を検証します。すべてのリクエスト本文が記録されると想定しないでください。
6. **Security Context の構成**: Pod と container の security context を適切に構成します。
7. **Image Scanning**: container image の脆弱性を定期的にスキャンします。

## 結論

Kubernetes の認証および認可システムは、cluster セキュリティの中核要素です。適切な認証方式を選択し、RBAC によるきめ細かなアクセス制御を実装し、admission controller を使用して追加のセキュリティポリシーを適用することで、安全な Kubernetes 環境を構築できます。

認証、認可、および admission control は相互に補完し合うため、Defense in Depth 戦略を実装するにはこれらを組み合わせて使用することが重要です。

## 公式リファレンス

- [Kubernetes 認証](https://kubernetes.io/docs/reference/access-authn-authz/authentication/)
- [Kubernetes 認可](https://kubernetes.io/docs/reference/access-authn-authz/authorization/)
- [RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [ServiceAccount 構成](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/)
- [ABAC](https://kubernetes.io/docs/reference/access-authn-authz/abac/)
- [Node 認可](https://kubernetes.io/docs/reference/access-authn-authz/node/)
- [Admission controller](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/)
- [Admission webhook](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)
- [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [EKS 証明書署名](https://docs.aws.amazon.com/eks/latest/userguide/cert-signing.html)
- [EKS access entry](https://docs.aws.amazon.com/eks/latest/userguide/creating-access-entries.html)
- [EKS 認証モード](https://docs.aws.amazon.com/eks/latest/userguide/setting-up-access-entries.html)
- [EKS access policy 評価](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)
- [EKS audit log](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
- [信頼できる kubeconfig](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/)
