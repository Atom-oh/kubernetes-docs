# Kubernetes 認証と認可 クイズ

> **関連ドキュメント**: [Kubernetes 認証・認可システム](../../security/02-kubernetes-auth-authz.md)

> **最終更新**: September 13, 2026

## 選択問題

### 1. Kubernetes の X.509 証明書認証では、ユーザー名はどのフィールドから抽出されますか？

- A) Subject Alternative Name (SAN)
- B) Common Name (CN)
- C) Organization Unit (OU)
- D) Issuer

<details>
<summary>答えを表示</summary>

**答え: B) Common Name (CN)**

**解説:**
X.509 証明書では、Common Name (CN) がユーザー名にマッピングされ、Organization (O) がグループにマッピングされます。

</details>

### 2. RBAC における ClusterRole と Role の主な違いは何ですか？

- A) ClusterRole は読み取り専用で、Role は読み書き可能
- B) ClusterRole はクラスタースコープの定義で、Role は namespace スコープの定義
- C) ClusterRole は管理者専用で、Role は一般ユーザー向け
- D) ClusterRole は node にのみ適用され、Role は pod にのみ適用される

<details>
<summary>答えを表示</summary>

**答え: B) ClusterRole はクラスタースコープの定義で、Role は namespace スコープの定義**

**解説:**
ClusterRole は namespace スコープのリソースに対する再利用可能な権限を定義することもできます。それを参照する RoleBinding は、付与範囲をその binding の namespace に限定し、ClusterRoleBinding はその権限をクラスター全体に付与します。定義だけでは何の権限も付与されません。

</details>

### 3. ServiceAccount のトークンが pod に自動マウントされるデフォルトのパスはどこですか？

- A) /var/run/secrets/kubernetes.io/token
- B) /etc/kubernetes/serviceaccount
- C) /var/run/secrets/kubernetes.io/serviceaccount
- D) /opt/kubernetes/secrets

<details>
<summary>答えを表示</summary>

**答え: C) /var/run/secrets/kubernetes.io/serviceaccount**

**解説:**
これは自動マウントが有効な Linux Pod におけるデフォルトのディレクトリです。トークンはその中の `token` ファイルです。`automountServiceAccountToken: false` を指定した Pod やカスタムの projected volume を使う Pod では、パスが異なる場合やトークンが存在しない場合があります。

</details>

### 4. MutatingAdmissionWebhook と ValidatingAdmissionWebhook の実行順序はどうなりますか？

- A) 最初に Validating、次に Mutating
- B) 最初に Mutating、次に Validating
- C) 同時に並列で実行される
- D) 順序なくランダムに実行される

<details>
<summary>答えを表示</summary>

**答え: B) 最初に Mutating、次に Validating**

**解説:**
Admission controller の実行順序: 1) MutatingAdmissionWebhook (リクエストを変更する)、2) ValidatingAdmissionWebhook (リクエストを検証する)。

</details>

<span id="_5-what-configmap-maps-iam-users-roles-to-kubernetes-rbac-in-eks"></span>

### 5. レガシーな EKS の CONFIG_MAP 認証モードで IAM マッピングを保存する ConfigMap はどれですか？

- A) kube-config
- B) aws-auth
- C) eks-iam-mapping
- D) cluster-auth

<details>
<summary>答えを表示</summary>

**答え: B) aws-auth**

**解説:**
`kube-system/aws-auth` はレガシーな IAM マッピングです。現在のアクセス管理には、適切な RBAC または EKS access policy を伴う EKS access entry を使用してください。デュアルモードでの移行中は、同一のプリンシパルに対して access entry が優先されます。ConfigMap 全体を置き換えると、node のマッピングが削除される可能性があります。

</details>

<span id="_6-which-authentication-method-is-recommended-for-production-kubernetes-clusters"></span>

### 6. 外部の identity provider が発行する ID トークンを通じてユーザーログインを統合する方式はどれですか？

- A) 静的トークンファイル
- B) Basic 認証
- C) OIDC (OpenID Connect)
- D) 匿名認証

<details>
<summary>答えを表示</summary>

**答え: C) OIDC (OpenID Connect)**

**解説:**
OIDC は外部で発行された ID トークンの issuer、audience、署名、有効期限を検証します。ログインとリフレッシュは IdP / クライアントが処理し、API server はリフレッシュトークンを発行しません。EKS の IAM 認証は別のユーザーアクセス経路であり、IRSA / Pod Identity は異なる目的、すなわち Pod から AWS API へのアクセスのために使われます。

</details>

### 7. Kubernetes における `system:masters` グループの目的は何ですか？

- A) master node を管理するため
- B) RBAC / webhook 認可をバイパスする無制限の API アクセスを提供するため
- C) master node に pod をスケジューリングするため
- D) system namespace を管理するため

<details>
<summary>答えを表示</summary>

**答え: B) RBAC / webhook 認可をバイパスする無制限の API アクセスを提供するため**

**解説:**
`system:masters` は認可をバイパスする特別なグループです。通常の管理者ロールの binding と同等ではなく、ClusterRoleBinding を削除してもそのバイパスは無効になりません。一般の管理者にこのグループを割り当てるのは避けてください。

</details>

### 8. 特定の namespace 内で pod の読み取りのみを行えるように ServiceAccount を制限するにはどうしますか？

- A) ClusterRole + ClusterRoleBinding
- B) Role + ClusterRoleBinding
- C) Role のみ
- D) Role + RoleBinding

<details>
<summary>答えを表示</summary>

**答え: D) Role + RoleBinding**

**解説:**
他の権限付与がないという前提で、Pod の get/list/watch のみを許可する Role と、その namespace 内の RoleBinding を使用します。**ClusterRole + RoleBinding も有効**であり、そのため誤答の選択肢にはなっていません。ServiceAccount の subject は明示的に別の namespace に属することもできますが、権限の適用範囲は binding の namespace のままです。

</details>

### 9. RBAC における `impersonate` verb の目的は何ですか？

- A) 偽のリソースを作成するため
- B) ユーザーが別のユーザーやグループとして振る舞えるようにするため
- C) リソースを複製するため
- D) リソース名をマスクするため

<details>
<summary>答えを表示</summary>

**答え: B) ユーザーが別のユーザーやグループとして振る舞えるようにするため**

**解説:**
`impersonate` verb は、ユーザーが別のユーザー、グループ、または ServiceAccount であるかのように操作を実行することを可能にします。これはデバッグや管理目的に役立ちます。

</details>

### 10. マウントされた volume 内で ServiceAccount のトークンが含まれるファイルはどれですか？

- A) ca.crt
- B) namespace
- C) token
- D) serviceaccount.json

<details>
<summary>答えを表示</summary>

**答え: C) token**

**解説:**
デフォルトで自動マウントされる ServiceAccount の volume は次のファイルを提供します (カスタムの projection では異なる場合があります): `ca.crt` (CA 証明書)、`namespace` (現在の namespace)、`token` (認証用の JWT トークン)。

</details>

## 記述問題

### 1. Kubernetes における user account と service account の主な違いは何ですか？

<details>
<summary>答えを表示</summary>

**答え: user account は外部で管理され、Kubernetes が直接管理するものではありません。一方、service account は Kubernetes API を通じて管理される namespace スコープのリソースです。**

</details>

### 2. ServiceAccount トークンの自動マウントを無効にするにはどうしますか？

<details>
<summary>答えを表示</summary>

**答え: ServiceAccount のトップレベル、または Pod spec で `automountServiceAccountToken: false` を設定します。Pod の設定が優先され、明示的に宣言された projected token volume は引き続き機能します。**

</details>

### 3. ClusterRole における `rules` と `aggregationRule` の違いは何ですか？

<details>
<summary>答えを表示</summary>

**答え: `rules` は権限を直接定義しますが、`aggregationRule` は特定のラベルに一致する他の ClusterRole の権限を自動的に統合します。**

**解説:**
aggregation controller は対象の ClusterRole の rules を管理し、手動での rule 変更を上書きすることがあります。ラベルで選択されるロールを追加・編集する権限も、結果として得られるアクセス権に影響します。

</details>

### 4. TokenRequest API とは何であり、なぜ静的トークンより推奨されるのですか？

<details>
<summary>答えを表示</summary>

**答え: TokenRequest API は有効期限が限定され audience にバインドされたトークンを作成するため、長期間有効な静的トークンより安全です。**

**解説:**
サーバーが返す実際の有効期限を確認してください。要求した有効期間は調整されることがあります。kubelet は Pod に projected されたトークンをローテーションしますが、アプリケーション側でファイルを再読み込みする必要があります。単独の TokenRequest 自体はファイルの自動ローテーションを提供しません。これらのトークンは依然として秘密の bearer 資格情報です。

</details>

### 5. 複数の認証方式が設定されている場合、Kubernetes はどの認証方式を使用するかをどのように決定しますか？

<details>
<summary>答えを表示</summary>

**答え: 最初に成功した認証結果が使用されますが、authenticator の評価順序は保証されません。**

**解説:**
X.509 → OIDC → proxy という固定順序を前提にしないでください。無効な資格情報は 401 になることがあります。資格情報のないリクエストに対する匿名扱いはサーバー設定に依存し、匿名の identity であっても認可によって拒否されることがあります。

</details>

## 実践問題

### 1. 次の要件を満たす Role と RoleBinding を記述してください:

- Namespace: development
- 権限: Pod の読み取り (get, list, watch)、ConfigMap の読み取りと個別オブジェクトの create/update/patch/delete (deletecollection は除く)
- User: developer@example.com

<details>
<summary>答えを表示</summary>

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

<span id="_2-create-a-serviceaccount-with-a-custom-token-expiration-time"></span>

### 2. ServiceAccount と、カスタムの有効期間を要求する projected token を持つ Pod を作成してください。

<details>
<summary>答えを表示</summary>

```yaml
# ServiceAccount definition
apiVersion: v1
kind: ServiceAccount
metadata:
  name: custom-sa
  namespace: default
automountServiceAccountToken: false
---
# Pod using projected token with custom expiration
apiVersion: v1
kind: Pod
metadata:
  name: app-with-custom-token
  namespace: default
spec:
  serviceAccountName: custom-sa
  automountServiceAccountToken: false
  containers:
  - name: app
    image: registry.k8s.io/pause:3.10
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
          expirationSeconds: 3600  # requested, not guaranteed
          audience: https://service.example.com
```

**解説:**
要求可能な `expirationSeconds` の最小値は 600 で、実際の有効期限はサーバーが決定します。この例の audience は受信側のサービスで設定・検証される必要があり、Kubernetes API が自動的に受け入れるわけではありません。Kubernetes API を呼び出す場合は、API server が受け入れる audience を使用してください。自動マウントは無効化され、明示的なトークンのみが読み取り専用でマウントされます。この pause Pod は volume の例示のためのもので、トークンを使用することも HTTP を提供することもありません。実際のアプリケーションでは、kubelet がローテーションした後にファイルを再読み込みする必要があります。

</details>

### 3. 特定のユーザーが持つ権限を確認するコマンドを記述してください。

<details>
<summary>答えを表示</summary>

```bash
# Check if a user can perform a specific action
kubectl auth can-i create deployments --as=developer@example.com -n development

# Request the namespace rule list (see authorizer limitations below)
kubectl auth can-i --list --as=developer@example.com -n development

# Check permissions for a ServiceAccount
kubectl auth can-i get pods -n development \
  --as=system:serviceaccount:default:my-sa \
  --as-group=system:serviceaccounts \
  --as-group=system:serviceaccounts:default \
  --as-group=system:authenticated

# Impersonate a group
kubectl auth can-i create pods --as=developer@example.com --as-group=developers -n development
```

**解説:**
呼び出し元には、対象のユーザー / ServiceAccount と使用する各グループに対する `impersonate` 権限が必要です。グループのメンバーシップが自動的に再構築されると想定しないでください。`--list` は必ずしも実効権限の完全な一覧ではなく、EKS access policy による権限は含まれません。EKS の impersonation は RBAC の評価を強制するため、実際の IAM role は別途テストしてください。`can-i` が肯定的な結果を返しても、admission の通過、ネットワークアクセス、quota による受け入れが保証されるわけではありません。

</details>

## 応用問題

### 1. マルチテナントの Kubernetes クラスターにおけるテナント分離のセキュリティ戦略を設計してください。

<details>
<summary>答えを表示</summary>

**Namespace と RBAC の設計:**

- テナントごとに個別の namespace を作成する
- Pod Security Standards を適用する
- ネットワーク分離のために NetworkPolicy を実装する
- リソース制限のために ResourceQuota を設定する

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-alpha
  labels:
    tenant: alpha
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.35
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
  name: tenant-workload-editor
  namespace: tenant-alpha
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["networking.k8s.io"]
  resources: ["networkpolicies"]
  verbs: ["get", "list"]  # Read-only for network policies
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-workload-editors
  namespace: tenant-alpha
subjects:
- kind: Group
  name: tenant-alpha:developers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: tenant-workload-editor
  apiGroup: rbac.authorization.k8s.io
```

固定した PSS のバージョン `v1.35` は学習用のベースラインです。対象クラスターがサポートする policy バージョンを選択して検証してください。デフォルト拒否は DNS や外部依存もブロックするため、明示的な許可を検討してください。policy を強制するには CNI が対応している必要があります。テナントが namespace のラベル、NetworkPolicy、ResourceQuota、RBAC を変更できないようにする必要があり、既存の他の binding も見直しが必要です。

**Deployment の作成・編集を許可すると、Pod が namespace 内の他の ServiceAccount や Secret を使用できるようになる可能性があります。** Secret の get 権限を取り除くだけでは、この経路は閉じられません。信頼レベルの異なる identity / secret は別々の namespace に分離し、必要に応じて admission で許可する identity を制約するか、別々のクラスターを使用してください。この例は強力なテナント分離の根拠にはなりません。

**追加のセキュリティ対策:**

- アプリケーションごとに個別の ServiceAccount を使用する
- 監査ログを実装する
- policy の強制に admission webhook を使用する
- サブテナントの所有権と policy の伝播を明示的に定義する。通常の Kubernetes の namespace はフラットな構造です

</details>

### 2. kubectl コマンドが実行されたときの、認証と認可の全体的なフローを説明してください。

<details>
<summary>答えを表示</summary>

1. **クライアント**: kubectl は選択された kubeconfig / context を読み取り、サーバーの TLS 証明書を検証します。デフォルトのファイルは `~/.kube/config` ですが、`--kubeconfig` や `KUBECONFIG` で変更できます。証明書、トークン、または exec plugin から資格情報を取得し、EKS の IAM アクセスでは一般に `aws eks get-token` が使われます。
2. **認証**: API server は資格情報を検証してユーザー / グループの identity を確立します。最初に成功した authenticator の結果を使用し、固定の評価順序は保証されません。OIDC、proxy、webhook はそれぞれ検証方法と信頼の要件が異なります。
3. **認可**: 設定された authorizer が順に実行され、最初の Allow または Deny で終了します。NoOpinion の場合は継続し、すべてが NoOpinion の場合は 403 で拒否されます。RBAC は該当する binding の権限を加算し、明示的な拒否ルールはありません。`system:masters` によるバイパスは別のリスクです。
4. **リクエスト処理**: 通常のリソースの CREATE / UPDATE リクエストは mutation の後に validation の admission を通過し、どちらでも拒否されることがあります。成功した変更は、オブジェクトの検証、競合チェック、その他の関連チェックを経て保存されます。`get/list/watch` は admission をバイパスします。dry-run、DELETE、CONNECT、集約 API のすべてを同じ etcd 書き込みシーケンスで表すことはできません。
5. **レスポンス**: API server は結果またはエラーを返します。API の成功は、controller の処理完了やアプリケーションの準備完了を意味しません。

| リクエスト例 | 認証・認可の後の違い |
|---|---|
| `kubectl get pods` | 読み取り結果を返す。admission は実行されず、新しい Pod も保存されない |
| Pod CREATE | 保存前に mutation / validation の admission とオブジェクトチェックを通過し、その後スケジューリングされる |
| サーバー dry-run CREATE | 永続的な保存を行わずに、admission を含むサーバー側の検証を実施する |

認証は identity を確立し、認可は API 操作を許可し、admission は変更に対して追加の policy を適用します。

</details>

## 公式リファレンス

- [Authentication](https://kubernetes.io/docs/reference/access-authn-authz/authentication/)
- [Authorization](https://kubernetes.io/docs/reference/access-authn-authz/authorization/)
- [RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [ServiceAccount](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/)
- [Admission](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/)
- [EKS access policies](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)
