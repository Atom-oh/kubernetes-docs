# Kubernetes 認証と認可クイズ

> **関連ドキュメント**: [Kubernetes 認証と認可システム](../../security/02-kubernetes-auth-authz.md)

## 選択式問題

### 1. Kubernetes の X.509 証明書認証では、ユーザー名はどのフィールドから抽出されますか？

- A) Subject Alternative Name (SAN)
- B) Common Name (CN)
- C) Organization Unit (OU)
- D) Issuer

<details>
<summary>回答を表示</summary>

**回答: B) Common Name (CN)**

**解説:**
X.509 証明書では、Common Name (CN) がユーザー名に、Organization (O) がグループにマッピングされます。

</details>

### 2. RBAC における ClusterRole と Role の主な違いは何ですか？

- A) ClusterRole は読み取り専用、Role は読み取り/書き込み
- B) ClusterRole はクラスター全体のスコープ、Role は namespace スコープ
- C) ClusterRole は管理者専用、Role は一般ユーザー向け
- D) ClusterRole は node のみに適用され、Role は pod のみに適用される

<details>
<summary>回答を表示</summary>

**回答: B) ClusterRole はクラスター全体のスコープ、Role は namespace スコープ**

**解説:**
Role は特定の namespace 内のリソースに対する権限を定義し、ClusterRole はクラスター全体のリソースまたは namespace に属さないリソースに対する権限を定義します。

</details>

### 3. ServiceAccount token が pod に自動的にマウントされるデフォルトのパスはどれですか？

- A) /var/run/secrets/kubernetes.io/token
- B) /etc/kubernetes/serviceaccount
- C) /var/run/secrets/kubernetes.io/serviceaccount
- D) /opt/kubernetes/secrets

<details>
<summary>回答を表示</summary>

**回答: C) /var/run/secrets/kubernetes.io/serviceaccount**

**解説:**
ServiceAccount token はデフォルトで `/var/run/secrets/kubernetes.io/serviceaccount` にマウントされます。

</details>

### 4. MutatingAdmissionWebhook と ValidatingAdmissionWebhook の実行順序はどれですか？

- A) 先に Validating、その後 Mutating
- B) 先に Mutating、その後 Validating
- C) 同時に並列実行される
- D) 順序なしでランダムに実行される

<details>
<summary>回答を表示</summary>

**回答: B) 先に Mutating、その後 Validating**

**解説:**
Admission controller の実行順序は、1) MutatingAdmissionWebhook (リクエストを変更)、2) ValidatingAdmissionWebhook (リクエストを検証) です。

</details>

### 5. EKS で IAM user/role を Kubernetes RBAC にマッピングする ConfigMap はどれですか？

- A) kube-config
- B) aws-auth
- C) eks-iam-mapping
- D) cluster-auth

<details>
<summary>回答を表示</summary>

**回答: B) aws-auth**

**解説:**
Amazon EKS では、`aws-auth` ConfigMap (kube-system namespace 内) が AWS IAM user と role を Kubernetes user と group にマッピングします。

</details>

### 6. 本番環境の Kubernetes cluster で推奨される認証方法はどれですか？

- A) 静的 token ファイル
- B) Basic authentication
- C) OIDC (OpenID Connect)
- D) 匿名認証

<details>
<summary>回答を表示</summary>

**回答: C) OIDC (OpenID Connect)**

**解説:**
OIDC は、token の有効期限、refresh token、Okta、Azure AD、Google などの identity provider との統合といった機能により、エンタープライズグレードの認証を提供します。

</details>

### 7. Kubernetes における `system:masters` group の目的は何ですか？

- A) master node を管理するため
- B) cluster-admin 権限を提供するため
- C) master node 上に pod をスケジュールするため
- D) system namespace を管理するため

<details>
<summary>回答を表示</summary>

**回答: B) cluster-admin 権限を提供するため**

**解説:**
`system:masters` group は `cluster-admin` ClusterRole にバインドされ、cluster への完全な管理アクセスを付与します。

</details>

### 8. 特定の namespace で ServiceAccount が pod を読み取るだけに制限するにはどうしますか？

- A) ClusterRole + ClusterRoleBinding
- B) Role + ClusterRoleBinding
- C) ClusterRole + RoleBinding
- D) Role + RoleBinding

<details>
<summary>回答を表示</summary>

**回答: D) Role + RoleBinding**

**解説:**
namespace スコープの権限には、Role (namespace 内の権限を定義) と RoleBinding (同じ namespace 内の subject に role をバインド) を使用します。

</details>

### 9. RBAC における `impersonate` verb の目的は何ですか？

- A) 偽のリソースを作成するため
- B) ユーザーが別のユーザーまたは group として動作できるようにするため
- C) リソースを複製するため
- D) リソース名を隠すため

<details>
<summary>回答を表示</summary>

**回答: B) ユーザーが別のユーザーまたは group として動作できるようにするため**

**解説:**
`impersonate` verb により、ユーザーは別のユーザー、group、または ServiceAccount であるかのように操作を実行できます。これはデバッグや管理目的に役立ちます。

</details>

### 10. マウントされた volume 内で ServiceAccount token を含むファイルはどれですか？

- A) ca.crt
- B) namespace
- C) token
- D) serviceaccount.json

<details>
<summary>回答を表示</summary>

**回答: C) token**

**解説:**
ServiceAccount volume mount には 3 つのファイルが含まれます: `ca.crt` (CA 証明書)、`namespace` (現在の namespace)、`token` (認証用の JWT token)。

</details>

## 短答問題

### 1. Kubernetes における user account と service account の主な違いは何ですか？

<details>
<summary>回答を表示</summary>

**回答: User account は外部で管理され、Kubernetes によって直接管理されません。一方、service account は Kubernetes API を通じて管理される namespace スコープのリソースです。**

</details>

### 2. ServiceAccount token の自動マウントを無効にするにはどうしますか？

<details>
<summary>回答を表示</summary>

**回答: ServiceAccount または Pod spec のいずれかで `automountServiceAccountToken: false` を設定します。**

</details>

### 3. ClusterRole における `rules` と `aggregationRule` の違いは何ですか？

<details>
<summary>回答を表示</summary>

**回答: `rules` は権限を直接定義し、`aggregationRule` は特定の label に一致する他の ClusterRole から権限を自動的に組み合わせます。**

**解説:**
Aggregated ClusterRole は、組み込み role を直接変更せずに拡張する場合に便利です。

</details>

### 4. TokenRequest API とは何ですか。また、静的 token より推奨される理由は何ですか？

<details>
<summary>回答を表示</summary>

**回答: TokenRequest API は、有効期限付きで audience にバインドされた token を作成し、長期間有効な静的 token より安全です。**

**解説:**
TokenRequest API からの token は自動的に期限切れになり、特定の audience にバインドされるため、token の盗難や誤用のリスクを低減します。

</details>

### 5. 複数の認証方法が設定されている場合、Kubernetes は使用する認証方法をどのように決定しますか？

<details>
<summary>回答を表示</summary>

**回答: Kubernetes は、成功するものが見つかるまで各認証方法を順番に試します。最初に成功した認証が使用されます。**

**解説:**
認証方法はチェーンとして試行されます。すべての方法が失敗した場合、リクエストは 401 Unauthorized エラーで拒否されます。

</details>

## ハンズオン問題

### 1. 次の要件を満たす Role と RoleBinding を作成してください:

- Namespace: development
- Permissions: Pod read (get, list, watch), ConfigMap full access
- User: developer@example.com

<details>
<summary>回答を表示</summary>

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: development
  name: developer-role
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developer-binding
  namespace: development
subjects:
- kind: User
  name: developer@example.com
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer-role
  apiGroup: rbac.authorization.k8s.io
```

</details>

### 2. カスタム token 有効期限を持つ ServiceAccount を作成してください。

<details>
<summary>回答を表示</summary>

```yaml
# ServiceAccount definition
apiVersion: v1
kind: ServiceAccount
metadata:
  name: custom-sa
  namespace: default
---
# Pod using projected token with custom expiration
apiVersion: v1
kind: Pod
metadata:
  name: app-with-custom-token
spec:
  serviceAccountName: custom-sa
  containers:
  - name: app
    image: nginx
    volumeMounts:
    - name: token
      mountPath: /var/run/secrets/tokens
  volumes:
  - name: token
    projected:
      sources:
      - serviceAccountToken:
          path: token
          expirationSeconds: 3600  # 1 hour
          audience: api
```

**解説:**
`serviceAccountToken` を使用した projected volume により、token のカスタム `expirationSeconds` (最小 600 秒) と `audience` を指定できます。

</details>

### 3. 特定のユーザーが持つ権限を確認するコマンドを書いてください。

<details>
<summary>回答を表示</summary>

```bash
# Check if a user can perform a specific action
kubectl auth can-i create deployments --as=developer@example.com -n development

# List all permissions for a user in a namespace
kubectl auth can-i --list --as=developer@example.com -n development

# Check permissions for a ServiceAccount
kubectl auth can-i --list --as=system:serviceaccount:default:my-sa

# Impersonate a group
kubectl auth can-i create pods --as=developer@example.com --as-group=developers -n development
```

**解説:**
`kubectl auth can-i` コマンドにより、現在のユーザーの権限を確認したり、他のユーザー/group になりすましてアクセスレベルを検証したりできます。

</details>

## 発展問題

### 1. マルチテナント Kubernetes cluster におけるテナント分離のためのセキュリティ戦略を設計してください。

<details>
<summary>回答を表示</summary>

**Namespace と RBAC の設計:**
- テナントごとに別々の namespace を作成する
- Pod Security Standards を適用する
- NetworkPolicy を実装してネットワークを分離する
- ResourceQuota を設定してリソース制限を行う

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-alpha
  labels:
    tenant: alpha
    pod-security.kubernetes.io/enforce: restricted
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: tenant-alpha
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: tenant-alpha
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tenant-admin
  namespace: tenant-alpha
rules:
- apiGroups: ["", "apps", "batch"]
  resources: ["*"]
  verbs: ["*"]
- apiGroups: ["networking.k8s.io"]
  resources: ["networkpolicies"]
  verbs: ["get", "list"]  # Read-only for network policies
```

**追加のセキュリティ対策:**
- アプリケーションごとに別々の ServiceAccount を使用する
- audit logging を実装する
- policy enforcement に admission webhook を使用する
- サブテナント管理には Hierarchical Namespaces の使用を検討する

</details>

### 2. kubectl コマンドが実行されたときの完全な認証と認可のフローを説明してください。

<details>
<summary>回答を表示</summary>

**完全なフロー:**

1. **Client Authentication (kubeconfig)**
   - kubectl が `~/.kube/config` を読み取る
   - credentials (証明書、token、または exec plugin) を抽出する
   - EKS の場合: `aws eks get-token` が一時 token を生成する

2. **API Server Authentication**
   - API server が credentials 付きのリクエストを受け取る
   - 認証方法を順番に試す:
     - X.509 client certificates
     - Bearer tokens (ServiceAccount, OIDC)
     - Authentication proxy
     - Webhook token authentication
   - 最初に成功した方法が identity を決定する

3. **Authorization**
   - API server が認可を確認する (通常は RBAC)
   - 適用可能なすべての Role/ClusterRole を評価する
   - 判定: Allow または Deny
   - 複数の authorizer がある場合: 最初の non-deny が採用される

4. **Admission Control**
   - **Mutating Admission**: リクエストを変更する
     - デフォルト値を追加し、sidecar を注入する
   - **Validating Admission**: リクエストを検証する
     - policy や quota を強制する
   - どちらもリクエストを拒否できる

5. **Persistence**
   - すべてのチェックに合格すると、リソースは etcd に保存される
   - レスポンスが client に返される

```
kubectl -> kubeconfig -> API Server
                            |
                     Authentication
                            |
                     Authorization (RBAC)
                            |
                   Mutating Admission
                            |
                  Validating Admission
                            |
                         etcd
```

**要点:**
- Authentication は「あなたが誰か」を決定する
- Authorization は「何ができるか」を決定する
- Admission control はリソースが「どのように変更/検証されるか」を制御する

</details>
