# Kubernetes Authentication and Authorization System

> **対象範囲**: Kubernetes の安定版 API および Amazon EKS のユーザーアクセス管理
> **最終更新**: September 13, 2026

## Overview

Authentication (認証) はリクエストの ID を確立し、Authorization (認可) はその ID がどの API 操作を実行できるかを決定し、Admission (アドミッション) は認可された変更に対して追加のポリシーを適用します。以下の manifest は独立した学習用の例です。あらかじめ namespace、管理者権限、証明書、webhook サーバーを準備してください。稼働中のクラスター/API 呼び出しや EKS アクセスの変更はテストしていません。

`kube-apiserver` の flag の例は **セルフマネージドな control plane** に適用されるものです。EKS ではマネージドなアクセス設定を使用してください。これらの例は、EKS の API server の flag を設定したり、その CA 秘密鍵を取得するための手順ではありません。

## Authentication

Authentication は、ユーザーまたはサービスが本人であると主張するとおりの存在であることを検証するプロセスです。Kubernetes は複数の認証方式をサポートしており、それらを同時に有効化できます。

複数の authenticator がある場合、最初に成功した結果が使用されますが、その評価順序は保証されません。無効な資格情報は認証に失敗する可能性があります。資格情報のないリクエストの扱いは anonymous authentication の設定に依存し、匿名の ID であっても認可は必要です。

### Authentication Strategies

#### 1. X.509 Certificates

API server の `--client-ca-file` を通じて信頼された **client CA** が署名した証明書を使用します。subject の CN がユーザー名を、O が group を提供し、証明書には client authentication (`clientAuth`) の usage が必要です。server の TLS 証明書を検証する CA は、client を認証する CA とは目的が異なります。

**ローカルでの秘密鍵と CSR の例:**

```bash
umask 077
auth_lab_dir=$(mktemp -d)
openssl genrsa -out "$auth_lab_dir/john.key" 2048
openssl req -new -key "$auth_lab_dir/john.key" \
  -out "$auth_lab_dir/john.csr" -subj '/CN=john/O=engineering'
openssl req -in "$auth_lab_dir/john.csr" -noout -verify
```

これらのコマンドは証明書を発行しません。**CSR のみ** を承認された発行者に送信し、発行者は ID、group、usage、有効期間を審査する必要があります。CA の秘密鍵をユーザーにコピーしたり、審査なしに organization 名を承認したりしないでください。EKS の `beta.eks.amazonaws.com/app-serving` signer は serving 証明書向けであり、ユーザーの client 証明書への署名はサポートしていません。EKS のユーザーアクセスには、以下の IAM/OIDC の経路を使用してください。

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

パスは発行されたファイルに置き換え、秘密鍵と kubeconfig へのアクセスを制限してください。`*-data` フィールドの Base64 は暗号化ではありません。信頼できない kubeconfig ファイルは使用前に検査してください。credential plugin を通じてコマンドが実行される可能性があります。

#### 2. Service Account Tokens

ServiceAccount は namespace スコープのワークロード ID です。すべての namespace には `default` アカウントが存在し、Pod の `serviceAccountName` は同じ namespace 内のアカウントを参照します。アカウントを選択すること自体が、アプリケーションリソースへのアクセスを付与するわけではありません。

この例は API を呼び出さず、token の自動マウントを無効化しています。この例のイメージはネットワークサービスを提供しません。

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

`automountServiceAccountToken` は ServiceAccount のトップレベルフィールドであり、かつ Pod の `spec` フィールドでもあります。Pod 側の設定が優先されます。これはデフォルトのマウントを制御するものであり、明示的に宣言された `serviceAccountToken` の projected volume を防ぐものではありません。

API アクセスが必要な Pod では、kubelet が TokenRequest を通じてデフォルトの projected token を取得し、ローテーションします。デフォルトの token ファイルは `/var/run/secrets/kubernetes.io/serviceaccount/token` です。アプリケーションはローテーションされたファイルを再読み込みする必要があります。有効期限と audience のバインディングは露出を軽減しますが、bearer token を開示しても安全になるわけではありません。アカウントを作成すれば長期間有効な Secret token が自動的に作られる、と想定しないでください。[quiz の projected volume の例](../quizzes/security/02-kubernetes-auth-authz-quiz.md) では、カスタム audience と要求する有効期間を扱っています。

#### 3. OpenID Connect (OIDC)

OIDC により、API server は外部 identity provider が発行した **ID token** を検証できます。issuer、audience、署名/有効期限の検証、ID のマッピングを設定します。API server は対話的なログインを提供せず、refresh token も発行しません。クライアントは、自身の identity provider 向けに審査済みのツールまたは `exec` credential plugin を使用します。

以下は **セルフマネージドな API server 向けの追加 flag** であり、完全な起動コマンドや kubeconfig ではありません。例に示した HTTPS の issuer と client ID は置き換えてください。

```text
--oidc-issuer-url=https://idp.example.com
--oidc-client-id=kubernetes
--oidc-username-claim=sub
--oidc-username-prefix=oidc:
--oidc-groups-claim=groups
--oidc-groups-prefix=oidc:
```

`system:` group などの既存の ID との衝突を避けるため、ユーザー名と group に prefix を付けてください。構造化された `AuthenticationConfiguration` も代替手段です。`--authentication-config` と `--oidc-*` flag を併用しないでください。EKS で外部 OIDC provider を設定する場合は、後述の個別のマネージド手順に従ってください。

#### 4. Webhook Token Authentication

セルフマネージドな API server は、`authentication.k8s.io/v1` の **TokenReview** を外部サービスに送信します。以下は **API server がそのサービスに到達するために使用する別個の kubeconfig** です。ユーザーの kubeconfig 内の `authentication.webhook` フィールドではありません。

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

`/etc/kubernetes/authn-webhook.kubeconfig` に配置する場合は、API server に `--authentication-token-webhook-config-file=/etc/kubernetes/authn-webhook.kubeconfig` と `--authentication-token-webhook-version=v1` を設定します。参照されている証明書とサービスは別途プロビジョニングしてください。サービスは token と意図された audience を検証し、TokenReview のレスポンスを返す必要があります。相互 TLS、資格情報の保護、キャッシュの TTL、障害時の挙動を設計してください。この例は webhook の実装も可用性の検証も提供しません。

#### 5. Authentication Proxy

authenticating proxy は呼び出し元を検証し、その結果として得られたユーザー名と group を転送します。信頼する header を指定するだけでは信頼は確立されません。まず、専用の front-proxy CA と許可された client 証明書の CN を使用して、proxy の TLS ID を認証します。

**セルフマネージドな API server の flag 抜粋:**

```text
--requestheader-client-ca-file=/etc/kubernetes/front-proxy-ca.crt
--requestheader-allowed-names=front-proxy-client
--requestheader-username-headers=X-Remote-User
--requestheader-group-headers=X-Remote-Group
```

proxy は、呼び出し元が指定した ID header を除去し、検証済みの値に置き換える必要があります。通常のユーザー client 用 CA を proxy CA として再利用したり、許可 CN を空にしてすべての client 証明書を信頼したりしないでください。この抜粋は proxy 自体を実装するものではありません。

### Users and Groups

Kubernetes では、ユーザーは次のように分類されます。

1. **Regular Users**: クラスター外部で管理され、Kubernetes が直接管理することはありません。
2. **Service Accounts**: Kubernetes API によって管理されるアカウントです。

ユーザーは 1 つ以上の group に所属でき、group は認可ポリシーで使用されます。

## Authorization

Authorization は、認証済みのユーザーが要求されたアクションを実行する権限を持つかどうかを検証するプロセスです。Kubernetes は複数の認可モジュールをサポートしています。

### Authorization Modes

#### 1. RBAC (Role-Based Access Control)

RBAC はロールベースのアクセス制御を提供し、現在 Kubernetes で最も広く使われている認可メカニズムです。

**主要な概念:**

1. **Role**: namespace 内の権限を定義します。
2. **ClusterRole**: クラスターリソース、非リソース URL、または namespace スコープのリソースに対する再利用可能な権限を、クラスタースコープで定義します。
3. **RoleBinding**: 同じ namespace の Role または ClusterRole を参照し、**binding の namespace 内でのみ** 権限を付与します。ServiceAccount の subject は、明示的に別の namespace に属することができます。
4. **ClusterRoleBinding**: ClusterRole の権限をクラスター全体に付与します。Role を参照することはできません。

role の定義は binding がなければ何も付与しません。RBAC は許可される権限を加算するのみで、明示的な拒否ルールはありません。Secret の `get/list/watch` は secret のデータの読み取りを許可するため、これらの例では代わりに Pod の読み取りを使用しています。

**Role Example:**

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

**RoleBinding Example:**

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

**ClusterRole Example:**

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

**ClusterRoleBinding Example:**

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

この ClusterRoleBinding は、**すべての namespace にまたがる Pod 情報** を明示的に必要とする運用 group を示したものであり、デフォルトの推奨ではありません。単一の namespace が対象であれば、代わりにその namespace で `roleRef.kind: ClusterRole` と `roleRef.name: pod-reader-reusable` を指定した RoleBinding を使用してください。

#### 2. ABAC (Attribute-Based Access Control)

ABAC は属性ベースのアクセス制御を提供します。ポリシーは JSON ファイルで定義します。

**Policy Example:**

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

ABAC は既存のセルフマネージドクラスターを理解するために取り上げています。`--authorization-policy-file` が読み込むポリシーは、Kubernetes の API リソースではなく **1 行に 1 つの JSON オブジェクト** を記述したファイルです。上記のインデントは説明のためのものであり、実際のファイルでは各ポリシーを 1 行にシリアライズしてください。変更には API server の再起動が必要です。新規の構成では RBAC を優先してください。この flag は EKS の設定メカニズムではありません。

#### 3. Node Authorization

Node authorization は kubelet に固有のものです。その ID は `system:nodes` に属し、実際のノード名と一致する `system:node:<nodeName>` というユーザー名を使用する必要があります。これはワークロードのアクセスメカニズムではありません。セルフマネージドクラスターでは、NodeRestriction admission と組み合わせて、kubelet による変更を Node および Pod オブジェクトに制限してください。

#### 4. Webhook Authorization

セルフマネージドな API server は、`authorization.k8s.io/v1` の **SubjectAccessReview** を外部サービスに送信します。上記の authentication webhook と同じ接続ファイル形式を使用し、認可用のエンドポイント、CA、client 証明書は別に用意します。`--authorization-webhook-config-file` と `--authorization-webhook-version=v1` を設定するか、構造化された `AuthorizationConfiguration` でチェーンと失敗時のポリシーを設定します。ユーザーの kubeconfig に `authorization.webhook` フィールドは存在しません。

authorizer は設定された順序で実行され、最初の **Allow または Deny** が決定となります。`NoOpinion` は次の authorizer に処理を継続し、すべてが NoOpinion の場合はアクセスが拒否されます。後続の webhook が、RBAC が既に許可したリクエストを拒否 (veto) することはできません。`system:masters` は RBAC と webhook 認可をバイパスする特別な group です。通常の管理者に割り当てたり、role binding を削除すればそのアクセスを取り消せると想定したりしないでください。

### Authorization Best Practices

1. **Principle of Least Privilege**: 必要最小限の権限のみを付与します。
2. **Role Separation**: 管理者、開発者、運用者などのロールに応じて適切な権限を付与します。
3. **Namespace Separation**: チームやプロジェクトごとに namespace を分離し、適切な権限を付与します。
4. **Service Account Separation**: アプリケーションごとに個別の service account を使用します。
5. **Regular Auditing**: 認可ポリシーを定期的にレビューし、更新します。

## Admission Control

Admission control は、認証と認可の後、リクエストを処理する前に追加の検証と変更を行います。

Admission は作成、変更、削除、および一部の接続リクエストを扱います。**get/list/watch の読み取りは admission をバイパスします**。Mutation が validation より先に実行され、どちらのフェーズでもリクエストを拒否できます。

### Admission Controller Types

1. **Mutating Admission Controllers**: リクエストを変更できます。
2. **Validating Admission Controllers**: 変更せずにリクエストを検証するだけです。

### Key Admission Controllers

1. **LimitRanger**: LimitRange で定義されたデフォルト値と最小/最大の制約を適用します。
2. **ResourceQuota**: 設定された namespace の quota を、オブジェクト数、リソース request などの数量についてチェックします。実測の CPU/メモリ消費量や支出の上限ではありません。
3. **PodSecurity**: namespace の label に従って Pod Security Standards を適用します。旧来の PodSecurityPolicy は Kubernetes 1.25 で削除されました。
4. **ServiceAccount**: Pod に service account を自動的に割り当てます。
5. **DefaultStorageClass**: class が指定されていない PVC に対してデフォルトの StorageClass を選択します。StorageClass を作成するわけではありません。

### Dynamic Admission Control

Dynamic admission control は webhook を通じて実装されます。

1. **MutatingAdmissionWebhook**: リクエストを変更できます。
2. **ValidatingAdmissionWebhook**: 変更せずにリクエストを検証するだけです。

**Webhook Configuration Example:**

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

この webhook は、明示的に label が付いた namespace のみを対象とします。実際の HTTPS サービス、CA、およびリクエストの UID を保持する AdmissionReview の実装なしにインストールしないでください。`failurePolicy: Fail` は、呼び出しのエラー/タイムアウト時に一致するリクエストをブロックします。`Ignore` は呼び出しの失敗を無視するもので、正常に返された拒否を許可に変えるものではありません。可用性と復旧は専用の namespace でテストしてください。検証には CEL の ValidatingAdmissionPolicy も選択肢になります。

## Practical Implementation Examples

### Authentication and Authorization Configuration in EKS

#### IAM and RBAC Integration

現在の EKS の IAM ユーザーアクセスには **access entry** を使用します。IAM role が認証済みの ID を提供し、関連付けられた EKS access policy または Kubernetes RBAC が Kubernetes の権限を付与します。両方の経路で許可された権限は加算されます。EKS access policy は IAM policy ではありません。

以下は、既存のクラスターと IAM role に対する管理者による変更の例です。まず、アカウント、Region、クラスター、`API` または `API_AND_CONFIG_MAP` モード、既存の `development` namespace、重複する access entry がないこと、そして `eks:CreateAccessEntry` と RBAC 変更に対する権限を確認してください。これはインフラ作成スクリプトでも、完全な移行手順でもありません。

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

RBAC オブジェクトを適用した後は、その role の実際の資格情報でアクセスを検証してください。この例では access policy を関連付けておらず、access entry を作成しても RBAC オブジェクトは作成されません。既存の binding や policy によって、実効権限がこれらの Pod 読み取りより広くなることがあります。伝播の遅延も考慮してください。

`aws-auth` ConfigMap は従来のメカニズムです。ConfigMap 全体を置き換えると、node/Fargate のマッピングが削除される可能性があります。`CONFIG_MAP` から `API_AND_CONFIG_MAP` への移行を計画し、マッピングを移行して検証した後に `API` を使用してください。いったん有効化すると、モードを元に戻しても API アクセスは削除できません。`API` から ConfigMap モードに戻すことはできません。両方を使用している間は、同じ IAM principal に対して access entry が優先されます。既存のマッピングがすべて自動的に移行されるわけではありません。

`kubectl auth can-i --list` は EKS access policy による権限を表示しません。`--as`/`--as-group` による impersonation は Kubernetes RBAC の評価を強制するため、IAM role の access policy の権限をテストすることにはなりません。namespace 外や Secret の読み取りで拒否されることの確認を含め、実際の role として個々のアクションを検証してください。

#### OIDC Provider Configuration

以下の 3 つの経路は、方向と目的が異なります。

| Path | Authentication target and configuration |
|---|---|
| External OIDC user → Kubernetes API | EKS の `AssociateIdentityProviderConfig` で外部 IdP を関連付け、そのユーザー/group を RBAC にバインドします。EKS は public HTTPS 経由で issuer に到達できる必要があり、自己署名の issuer 証明書はサポートされません。これによって IAM 認証が無効になるわけではありません。 |
| Pod → AWS API through IRSA | クラスターの ServiceAccount OIDC issuer に対して IAM の信頼関係を確立し、role の信頼関係を意図した namespace/ServiceAccount に限定し、必要な AWS リソースのみを許可します。`eksctl utils associate-iam-oidc-provider` はこの経路のためのもので、外部ユーザーのログイン用ではありません。 |
| Pod → AWS API through EKS Pod Identity | サポートされる実行環境で Pod Identity Agent と role の関連付けを使用します。これは IRSA の IAM OIDC provider の設定とは異なります。 |

いずれのワークロード向けメカニズムも、それ自体で Kubernetes API の RBAC を付与するわけではありません。アカウント全体を対象とする S3 読み取りのマネージドポリシーをデフォルトの例として使うのは避け、実際の bucket/object の ARN に権限を絞り込んでください。設定の詳細は [EKS external OIDC](https://docs.aws.amazon.com/eks/latest/userguide/authenticate-oidc-identity-provider.html) と [workload IAM roles](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html) を参照してください。

### Multi-tenant Cluster Security

マルチテナント環境では、テナント間の分離が重要です。

**Namespace Isolation:**

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

このポリシーは、`tenant: a` の label が付いた **すべての** namespace からの ingress を許可します。他の ingress ポリシーが許可を追加することがあり、egress は制限されていません。CNI による NetworkPolicy の適用が必要であり、namespace の label とポリシーは信頼できる管理者のみが制御すべきです。namespace だけでは、敵対的なテナント間の強い分離は保証されません。quiz では双方向のデフォルト拒否を扱っています。DNS と必要なトラフィックについては、個別の許可を検討してください。

**Resource Quotas:**

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

## Security Best Practices

1. **Regular Certificate Rotation**: 証明書を定期的に更新します。
2. **Disable Service Account Token Auto-mount**: 不要な場合は service account token の自動マウントを無効化します。
3. **Minimize RBAC Policies**: 必要最小限の権限のみを付与します。
4. **Implement Network Policies**: Pod 間の通信を制限します。
5. **Enable Audit Logging**: audit policy の対象範囲、機密データの除外、保持期間、ログへのアクセスを検証します。EKS では `audit` control plane ログタイプを有効化し、CloudWatch への配信を確認してください。すべてのリクエストボディが記録されると想定しないでください。
6. **Configure Security Contexts**: Pod と container の security context を適切に設定します。
7. **Image Scanning**: container イメージの脆弱性を定期的にスキャンします。

## Conclusion

Kubernetes の認証・認可システムは、クラスターセキュリティの中核要素です。適切な認証方式を選択し、RBAC によるきめ細かなアクセス制御を実装し、admission controller で追加のセキュリティポリシーを適用することで、安全な Kubernetes 環境を構築できます。

Authentication、Authorization、Admission control は互いを補完するものであり、これらを組み合わせて Defense in Depth (多層防御) 戦略を実装することが重要です。

## Official References

- [Kubernetes authentication](https://kubernetes.io/docs/reference/access-authn-authz/authentication/)
- [Kubernetes authorization](https://kubernetes.io/docs/reference/access-authn-authz/authorization/)
- [RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [ServiceAccount configuration](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/)
- [ABAC](https://kubernetes.io/docs/reference/access-authn-authz/abac/)
- [Node authorization](https://kubernetes.io/docs/reference/access-authn-authz/node/)
- [Admission controllers](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/)
- [Admission webhooks](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)
- [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [EKS certificate signing](https://docs.aws.amazon.com/eks/latest/userguide/cert-signing.html)
- [EKS access entries](https://docs.aws.amazon.com/eks/latest/userguide/creating-access-entries.html)
- [EKS authentication modes](https://docs.aws.amazon.com/eks/latest/userguide/setting-up-access-entries.html)
- [EKS access policy evaluation](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)
- [EKS audit logs](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
- [Trusted kubeconfig](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/)
