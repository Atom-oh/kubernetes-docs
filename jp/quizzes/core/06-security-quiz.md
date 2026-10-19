# Kubernetes セキュリティクイズ

このクイズでは、認証、認可、NetworkPolicy、Security Context、Secret 管理など、Kubernetes のセキュリティ概念に関する理解を確認します。

## 選択問題

1. Kubernetes のユーザー認証でサポートされていない方式はどれですか？
   - A) X.509 証明書
   - B) ServiceAccount トークン
   - C) OpenID Connect ID トークン
   - D) 組み込みユーザーデータベース

<details>
<summary>回答を表示</summary>

**回答: D) 組み込みユーザーデータベース**

**解説:**
Kubernetes は組み込みのユーザーデータベースを提供していません。X.509 証明書、ServiceAccount トークン、OIDC ID トークン、webhook によるトークン認証などをサポートしています。任意の OAuth アクセストークンを使うには、対応する認証機能を適切に構成する必要があります。ユーザー管理には通常、LDAP や Active Directory などの外部システムを使用します。
</details>

2. Kubernetes における RBAC (Role-Based Access Control) の主要コンポーネントではないものはどれですか？
   - A) Role
   - B) ClusterRole
   - C) RoleBinding
   - D) SecurityPolicy

<details>
<summary>回答を表示</summary>

**回答: D) SecurityPolicy**

**解説:**
Kubernetes RBAC の主要コンポーネントは Role、ClusterRole、RoleBinding、ClusterRoleBinding です。Role と ClusterRole は権限を定義し、各 Binding はその権限をユーザー、グループ、ServiceAccount に付与します。SecurityPolicy は RBAC のコンポーネントではありません。PodSecurityPolicy は Kubernetes 1.25 で削除されました。Pod Security Standards は Pod Security Admission が適用するポリシー定義であり、PodSecurityStandard という API リソースはありません。
</details>

3. Kubernetes の Pod の Security Context で設定できないものはどれですか？
   - A) コンテナのユーザー ID (UID)
   - B) コンテナのグループ ID (GID)
   - C) コンテナのネットワークポリシー
   - D) コンテナの権限昇格機能

<details>
<summary>回答を表示</summary>

**回答: C) コンテナのネットワークポリシー**

**解説:**
Security Context では、Pod またはコンテナ単位で権限やアクセス制御を設定します。設定項目にはユーザー ID (`runAsUser`)、グループ ID (`runAsGroup`)、権限昇格の許可 (`allowPrivilegeEscalation`)、特権モード (`privileged`)、Linux capabilities があります。ネットワークポリシーは Security Context ではなく、別の NetworkPolicy リソースで定義します。
</details>

4. Kubernetes における ServiceAccount の主な目的は何ですか？
   - A) クラスター外のユーザー認証
   - B) Pod が API server と通信するための ID を提供する
   - C) ノード間通信を暗号化する
   - D) cluster-admin 権限を付与する

<details>
<summary>回答を表示</summary>

**回答: B) Pod が API server と通信するための ID を提供する**

**解説:**
ServiceAccount は、Pod 内のプロセスが Kubernetes API server と通信するための ID を提供します。各 namespace にはデフォルトの ServiceAccount があり、明示しない場合は Pod がこれを使用します。RBAC と組み合わせることで、Pod が実行できる操作を制限できます。
</details>

5. Kubernetes の NetworkPolicy の主な目的は何ですか？
   - A) クラスター外から内部へのトラフィックをルーティングする
   - B) Pod 間の通信を制御・制限する
   - C) ノード間通信を暗号化する
   - D) サービスディスカバリーを提供する

<details>
<summary>回答を表示</summary>

**回答: B) Pod 間の通信を制御・制限する**

**解説:**
NetworkPolicy を使うと、Pod のグループ間で許可する通信相手、ポート、プロトコルを指定できます。サービス間通信を細かく制御できるため、マイクロサービス構成のセキュリティ強化に役立ちます。
</details>

6. Pod Security Standards の 3 つのポリシーレベルのうち、最も制限が厳しいものはどれですか？
   - A) Privileged
   - B) Baseline
   - C) Restricted
   - D) Enforced

<details>
<summary>回答を表示</summary>

**回答: C) Restricted**

**解説:**
Pod Security Standards は、次の 3 つのポリシーレベルを定義しています。
  - Privileged: 制限なし、すべての権限を許可
  - Baseline: 既知の権限昇格経路を防止
  - Restricted: セキュリティ設定を強化した、最も制限の厳しいポリシー

Restricted ポリシーは最も制限が厳しく、最小権限の原則に沿ったセキュリティのベストプラクティスを適用します。特権コンテナ、ホスト namespace の共有、hostPath マウントなどを禁止します。
</details>

7. Kubernetes Secret のデータを保護するうえで最も効果的な方法は何ですか？
   - A) Base64 エンコード
   - B) etcd の保存時暗号化設定
   - C) Namespace による分離
   - D) label の追加

<details>
<summary>回答を表示</summary>

**回答: B) etcd の保存時暗号化設定**

**解説:**
Kubernetes Secret のデータは、既定では Base64 でエンコードされますが、これは暗号化ではありません。etcd の暗号化を設定すると、Secret のデータは etcd への保存前に暗号化され、etcd データベースへの不正アクセスから保護されます。namespace の分離やラベルはアクセス制御には役立ちますが、データそのものを暗号化するものではありません。
</details>

8. Kubernetes でコンテナイメージの安全性を高める方法ではないものはどれですか？
   - A) イメージの脆弱性スキャン
   - B) 信頼できるレジストリの使用
   - C) イメージの署名と検証
   - D) コンテナに root 権限を付与する

<details>
<summary>回答を表示</summary>

**回答: D) コンテナに root 権限を付与する**

**解説:**
コンテナに root 権限を与えるとセキュリティが弱まります。コンテナイメージの安全性を高めるには、脆弱性スキャン、信頼できるレジストリの使用、イメージの署名と検証、最小権限の適用、不要なパッケージの削除、root 以外のユーザーでの実行などが有効です。
</details>

9. Kubernetes の監査ログの主な目的は何ですか？
   - A) Pod ログの収集
   - B) API server へのリクエストの記録
   - C) ノード状態の監視
   - D) ネットワーク通信の分析

<details>
<summary>回答を表示</summary>

**回答: B) API server へのリクエストの記録**

**解説:**
監査ログは Kubernetes API server へのリクエストを記録します。これにより、クラスター内で誰が何をしたかを追跡でき、セキュリティインシデントの調査、コンプライアンス要件への対応、トラブルシューティングに役立ちます。監査ログには、リクエスト時刻、ユーザー、リクエスト内容、応答などを記録できます。
</details>

10. Kubernetes の特権コンテナの特徴ではないものはどれですか？
    - A) すべてのホストデバイスへのアクセス
    - B) すべての Linux capability の付与
    - C) ホストカーネルモジュールを読み込める
    - D) 他の namespace のリソースへの自動アクセス

<details>
<summary>回答を表示</summary>

**回答: D) 他の namespace のリソースへの自動アクセス**

**解説:**
特権コンテナはホストのほぼすべての Linux capability にアクセスできますが、他の namespace の Kubernetes リソースに自動でアクセスするわけではありません。namespace をまたぐアクセスは RBAC 権限で制御されます。`privileged: true` を設定しても `hostNetwork: true` にはなりません。ただし、ホストとの隔離が大きく損なわれるため、侵害されたワークロードから認証情報が漏えいしたり、想定した分離を回避されたりするおそれがあります。RBAC は侵害された特権ワークロードを防御しません。
</details>

## 短答問題

1. Kubernetes RBAC における Role と ClusterRole の主な違いは何ですか？

<details>
<summary>回答を表示</summary>

**回答:**
Role は namespace 内の権限を定義します。ClusterRole はクラスター全体を対象とする権限定義ですが、namespace 付きリソースにもクラスター全体のリソースにも使えます。RoleBinding は ClusterRole の権限を特定の namespace に付与し、ClusterRoleBinding はクラスター全体に付与します。Role や ClusterRole を作成しただけでは、主体に権限は付与されません。
</details>

2. Kubernetes で「最小権限の原則」を実践する方法を 3 つ説明してください。

<details>
<summary>回答を表示</summary>

**回答:**
1. RBAC で必要最小限の権限だけを付与する
2. Pod の Security Context でコンテナを root 以外のユーザーとして実行する
3. NetworkPolicy で必要な通信だけを許可する
4. 特権コンテナの使用を制限する
5. コンテナの Linux capabilities を制限する
6. Pod Security Standards の Restricted プロファイルを適用する

（上記のうち 3 つだけ説明すればよい）
</details>

3. Kubernetes のセキュリティ上、Secret と ConfigMap はどのように異なりますか？

<details>
<summary>回答を表示</summary>

**回答:**
Secret にはパスワード、トークン、鍵などの機密情報を保存し、ConfigMap には一般的な設定データを保存します。Secret の `data` は API 上で Base64 エンコードされますが、暗号化ではありません。Linux では Secret ボリューム全体がメモリ上のストレージを使い、Pod 作成後の更新も反映されます。アプリケーションはファイルを再読み込みする必要があります。保存時暗号化の有無はクラスター構成によります（EKS 1.28 以降は API データが既定で暗号化されます）。引き続き RBAC と Pod からの最小権限アクセスが必要です。
</details>

4. Kubernetes の ServiceAccount トークンのボリューム投影には、どのような目的と利点がありますか？

<details>
<summary>回答を表示</summary>

**回答:**
ServiceAccount トークンのボリューム投影では、Pod にマウントするトークンの有効期間と audience を制限し、漏えい時のリスクを抑えます。kubelet は投影トークンをローテーションしますが、アプリケーションはファイルを再読み込みし、受信側は audience と有効期限を検証する必要があります。トークンをキャッシュしたままのアプリケーションは、ローテーション後も古い値を使い続けるため、ファイルを再読み込みする実装が必要です。
</details>

5. Kubernetes における「コンテナのサンドボックス化」とは何ですか。実装にはどのような技術を使用できますか？

<details>
<summary>回答を表示</summary>

**回答:**
コンテナのサンドボックス化は、コンテナをホストシステムや他のコンテナから分離してセキュリティを強化する技術です。実装には次の技術を使用できます。
1. Linux namespaces と cgroups: 基本的なコンテナ分離を提供します
2. seccomp: システムコールを制限します
3. AppArmor/SELinux: 強制アクセス制御を適用します
4. gVisor: ユーザー空間カーネルの実装により、追加の分離境界を設けます
5. Kata Containers: 軽量 VM を使用してハードウェア支援の分離を実現します
6. Firecracker: MicroVM による分離を実現します

これらの技術は、コンテナがホストシステムに及ぼす影響を抑え、コンテナ脱出攻撃のリスクを低減します。
</details>

## 実践問題

1. 次の要件を満たす RBAC リソースを作成してください。
   - `monitoring` namespace 内の Pod を読み取る Role を作成する
   - Role を `monitoring-team` ServiceAccount に紐付ける RoleBinding を作成する

<details>
<summary>回答を表示</summary>

**回答:**

```yaml
# monitoring-role.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: monitoring
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
---
# monitoring-rolebinding.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: monitoring
subjects:
- kind: ServiceAccount
  name: monitoring-team
  namespace: monitoring
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

適用方法:
```bash
kubectl apply -f monitoring-role.yaml
kubectl apply -f monitoring-rolebinding.yaml
```
</details>

2. 次の要件を満たす NetworkPolicy を作成してください:
   - `backend` namespace 内のすべての Pod に適用する
   - `frontend` namespace 内の Pod からポート 8080 への受信トラフィックだけを許可する
   - すべての送信トラフィックを許可する

<details>
<summary>回答を表示</summary>

**回答:**

```yaml
# backend-network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-allow-frontend
  namespace: backend
spec:
  podSelector: {}  # Apply to all pods
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - {}  # Allow all outgoing traffic
```

適用方法:
```bash
kubectl apply -f backend-network-policy.yaml
```

組み込みラベル `kubernetes.io/metadata.name` を使えば `frontend` namespace を選択できるため、独自ラベルは不要です。ほかの NetworkPolicy は許可ルールを追加する場合があり、送信元 Pod 側の egress policy も通信可否に影響します。
</details>

3. 次のセキュリティコンテキスト要件を満たす Pod を作成してください。
   - コンテナを UID 1000 で実行する
   - 権限昇格を許可しない
   - ルートファイルシステムを読み取り専用にする

<details>
<summary>回答を表示</summary>

**回答:**

```yaml
# secure-pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  containers:
  - name: secure-container
    image: busybox:1.36
    command: ["sh", "-c", "sleep 3600"]
    securityContext:
      runAsUser: 1000
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
```

適用方法:
```bash
kubectl apply -f secure-pod.yaml
```
</details>

4. 次の要件を満たす Secret を作成し、Pod にボリュームとしてマウントしてください。
   - `db-credentials` という名前にする
   - `username=admin` と `password=s3cr3t` を含める
   - Pod 内の `/etc/db-credentials` パスにマウントする

<details>
<summary>回答を表示</summary>

**回答:**

Secret を作成します。
```bash
kubectl create secret generic db-credentials \
  --from-literal=username=admin \
  --from-literal=password=s3cr3t
```

または、次の YAML を使います。
```yaml
# db-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
data:
  username: YWRtaW4=  # base64 encoding of 'admin'
  password: czNjcjN0  # base64 encoding of 's3cr3t'
```

Pod にマウントします。
```yaml
# pod-with-secret.yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-with-secret
spec:
  containers:
  - name: app
    image: nginx
    volumeMounts:
    - name: secret-volume
      mountPath: "/etc/db-credentials"
      readOnly: true
  volumes:
  - name: secret-volume
    secret:
      secretName: db-credentials
```

適用方法:
```bash
kubectl apply -f db-secret.yaml
kubectl apply -f pod-with-secret.yaml
```
</details>

## 応用トピック

1. Kubernetes で OPA (Open Policy Agent) Gatekeeper を使って実装できるポリシーを 3 つ挙げ、説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

OPA Gatekeeper は Kubernetes クラスターにポリシーを適用するツールです。以下の Constraint を作成する前に、公式ポリシーライブラリから対応する ConstraintTemplate を導入してください。Constraint の kind は Kubernetes に組み込まれた API ではありません。また、レジストリの許可リストだけではイメージ署名を検証できません。ポリシーの例を示します。

1. **イメージレジストリの制限**: 承認済みレジストリからのみイメージを pull するよう強制し、信頼できない提供元のイメージを防ぎます。
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sAllowedRepos
   metadata:
     name: allowed-repos
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       repos:
         - "docker.io/company/"
         - "gcr.io/company/"
   ```

2. **特権コンテナの禁止**: セキュリティリスクを抑えるため、特権コンテナの使用を禁止します。
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sPSPPrivilegedContainer
   metadata:
     name: prevent-privileged-containers
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
   ```

3. **リソース制限の強制**: リソース枯渇攻撃を防ぐため、すべてのコンテナに CPU とメモリの上限を設定させます。
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sRequiredResources
   metadata:
     name: container-must-have-limits
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       limits:
         - cpu
         - memory
   ```

OPA Gatekeeper では、namespace に特定のラベルを要求する、Ingress のホスト名やボリューム種別を制限する、hostPath のマウントを禁止するといったポリシーも適用できます。
</details>

2. Kubernetes で mTLS (mutual TLS) を実装する方法とその利点を説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

mTLS (mutual TLS) では、クライアントとサーバーが証明書を使って互いを認証します。Kubernetes では、次の方法で実装できます。

**実装方法:**

1. **サービスメッシュの使用**: Istio や Linkerd などのサービスメッシュは、サイドカープロキシを通じて mTLS を自動的に適用します。
   ```yaml
   # Istio example
   apiVersion: security.istio.io/v1
   kind: PeerAuthentication
   metadata:
     name: default
     namespace: istio-system
   spec:
     mtls:
       mode: STRICT
   ```

2. **NetworkPolicy との併用**: NetworkPolicy で L3/L4 の到達性を制限し、サービスメッシュで証明書を検証します。ワークロードをメッシュに登録して mTLS を強制し、メッシュの認可ポリシーで認証済み ID へのアクセスを制御します。

3. **証明書管理**: cert-manager などのツールで証明書のライフサイクルを管理します。
   ```yaml
   apiVersion: cert-manager.io/v1
   kind: Certificate
   metadata:
     name: service-cert
     namespace: default
   spec:
     secretName: service-tls
     issuerRef:
       name: ca-issuer
       kind: ClusterIssuer
     commonName: service.default.svc.cluster.local
     dnsNames:
     - service.default.svc.cluster.local
   ```

**利点:**

1. **相互認証**: クライアントとサーバーが互いを認証し、中間者攻撃を防ぎます。
2. **通信の暗号化**: サービス間の通信を暗号化し、盗聴を防ぎます。
3. **きめ細かなアクセス制御**: 証明書に基づく ID により、細かなアクセス制御が可能になります。
4. **ゼロトラストアーキテクチャ**: ネットワーク上の位置にかかわらず、すべての通信で認証を要求します。
5. **コンプライアンス対応**: PCI DSS や HIPAA などのコンプライアンス要件への対応に役立ちます。

mTLS は、マイクロサービス間の通信の安全性を高める重要な手段です。
</details>

3. Kubernetes のソフトウェアサプライチェーンを保護する方法を説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

Kubernetes のソフトウェアサプライチェーンを保護する方法には、次のものがあります。

1. **イメージの署名と検証**:
   - Cosign や Notary などのツールでコンテナイメージに署名する
   - 署名済みイメージだけがデプロイされるようにポリシーを適用する（例: OPA Gatekeeper、Kyverno）
   ```bash
   cosign sign --key cosign.key "${IMAGE_REF:?Set repository@sha256:digest}"
   ```

2. **ソフトウェア部品表 (SBOM) の生成と検証**:
   - Syft や Anchore などのツールで SBOM を生成する
   - イメージに含まれるすべてのソフトウェア構成要素を追跡する
   ```bash
   syft "${IMAGE_REF:?Set repository@sha256:digest}" -o spdx-json > sbom.json
   ```

3. **脆弱性スキャン**:
   - Trivy や Clair などのツールでイメージの脆弱性をスキャンする
   - スキャンを CI/CD パイプラインに組み込む
   ```bash
   trivy image "${IMAGE_REF:?Set repository@sha256:digest}"
   ```

4. **最小限のベースイメージを使用する**:
   - 攻撃対象領域を減らすため、distroless や scratch のような最小構成のイメージを使う
   ```dockerfile
   FROM gcr.io/distroless/java21-debian13:nonroot
   COPY app.jar /app.jar
   CMD ["app.jar"]
   ```

5. **イメージポリシーの適用**:
   - イメージの経過時間、脆弱性の深刻度、レジストリの提供元などを基準にポリシーを適用する
   ```yaml
   apiVersion: constraints.gatekeeper.sh/v1beta1
   kind: K8sAllowedRepos
   metadata:
     name: trusted-images
   spec:
     match:
       kinds:
         - apiGroups: [""]
           kinds: ["Pod"]
     parameters:
       repos:
         - "docker.io/company/"
         - "gcr.io/verified/"
   ```

6. **ソフトウェア成果物のサプライチェーンレベル (SLSA)**:
   - ビルドの来歴を追跡する
   - 再現可能なビルドを確保する
   - ビルドの完全性を検証する

7. **継続的な監視と監査**:
   - 実行時セキュリティツールで異常な挙動を検出する
   - セキュリティ監査を定期的に実施する

これらの方法を組み合わせることで、Kubernetes 環境をソフトウェアサプライチェーン攻撃から保護できます。
</details>

4. Kubernetes でゼロトラストセキュリティモデルを実装する方法を説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

ゼロトラストセキュリティモデルは、「決して信頼せず、常に検証する」という原則に基づきます。Kubernetes では次のように実装できます。

1. **きめ細かな ID とアクセス管理**:
   - 強固な RBAC ポリシーを設定する
   - ServiceAccount に必要最小限の権限だけを付与する
   - 外部 ID プロバイダー（OIDC、LDAP など）と統合する
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     namespace: default
     name: minimal-access
   rules:
   - apiGroups: [""]
     resources: ["pods"]
     verbs: ["get"]
     resourceNames: ["app-pod"]
   ```

2. **ネットワークの分割**:
   - デフォルトですべての通信を拒否する
   - 明示的に必要な通信のみを許可する NetworkPolicy を適用する
   - マイクロセグメンテーションを実装する
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: default-deny
   spec:
     podSelector: {}
     policyTypes:
     - Ingress
     - Egress
   ```

3. **相互 TLS (mTLS) の適用**:
   - Istio や Linkerd などのサービスメッシュを使い、すべてのサービス間通信に mTLS を適用する
   - 証明書に基づいてサービス ID を検証する
   ```yaml
   apiVersion: security.istio.io/v1
   kind: PeerAuthentication
   metadata:
     name: default
     namespace: istio-system
   spec:
     mtls:
       mode: STRICT
   ```

4. **継続的な検証と認証**:
   - すべてのリクエストを継続的に認証・認可する
   - 時刻、場所、デバイスの状態などのコンテキストに基づいてアクセスを制御する
   - OPA Gatekeeper または Kyverno でポリシーを動的に適用する

5. **暗号化**:
   - 保存データを暗号化する（etcd の暗号化、暗号化済み PV など）
   - 通信中のデータを暗号化する（TLS、mTLS）
   - Secret 管理ツールとの連携（Vault、Sealed Secrets など）

6. **脅威の検出と対応**:
   - 実行時セキュリティ監視ツールを導入する
   - 異常な挙動を検出してアラートを出す
   - 自動応答の仕組みを実装する

7. **ワークロードの最小権限構成**:
   - コンテナを root 以外のユーザーで実行する
   - 読み取り専用ファイルシステムを使う
   - セキュリティコンテキストで制限を設定する
   ```yaml
   spec:
     securityContext:
       runAsUser: 1000
       runAsGroup: 3000
       fsGroup: 2000
       runAsNonRoot: true
       seccompProfile:
         type: RuntimeDefault
     containers:
     - name: app
       image: busybox:1.36
       command: ["sh", "-c", "sleep 3600"]
       securityContext:
         readOnlyRootFilesystem: true
         allowPrivilegeEscalation: false
         capabilities:
           drop: ["ALL"]
   ```

8. **セキュリティ態勢の継続的な評価**:
   - 脆弱性スキャンを定期的に行う
   - ペネトレーションテストとセキュリティ監査を実施する
   - コンプライアンス状況を継続的に監視する

ゼロトラストは単一の製品で実現するものではありません。継続的な検証と最小権限の原則に基づき、複数の防御層を組み合わせるアプローチです。
</details>

5. Kubernetes の実行時セキュリティに使うツールと技術を比較し、説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

Kubernetes の実行時セキュリティには、主に次のツールや技術が使われます。

1. **Falco**:
   - **仕組み**: システムコールを監視し、異常な挙動を検出します
   - **特徴**:
     - カーネルレベルで動作し、コンテナ内部の活動を監視します
     - さまざまなセキュリティ上の脅威を検出するルールを作成できます
     - リアルタイムのアラートと対応をサポートします
   - **ルール例**:
     ```yaml
     - rule: Terminal shell in container
       desc: A shell was spawned by a container
       condition: spawned_process and container and proc.name = bash and proc.tty != 0
       output: Shell opened in container (user=%user.name container=%container.name)
       priority: WARNING
     ```

2. **Seccomp (Secure Computing Mode)**:
   - **仕組み**: コンテナが使用できるシステムコールを制限します
   - **特徴**:
     - Linux カーネルに組み込まれた機能を使います
     - 許可したシステムコールだけを実行できます
     - 攻撃対象領域を減らします
   - **実装例**:
     ```yaml
     apiVersion: v1
     kind: Pod
     metadata:
       name: seccomp-pod
     spec:
       securityContext:
         seccompProfile:
           type: Localhost
           localhostProfile: profiles/audit.json
       containers:
       - name: app
         image: busybox:1.36
         command: ["sh", "-c", "sleep 3600"]
     ```

3. **AppArmor**:
   - **仕組み**: プログラムごとにアクセス制御プロファイルを適用します
   - **特徴**:
     - ファイル、ネットワーク、ケーパビリティなどへのアクセスを細かく制御できます
     - AppArmor が有効な Linux ノードと、事前に読み込んだプロファイルが必要です
     - コンテナごとにプロファイルを適用できます
   - **実装例**:
     ```yaml
     apiVersion: v1
     kind: Pod
     metadata:
       name: apparmor-pod
     spec:
       containers:
       - name: container1
         image: busybox:1.36
         command: ["sh", "-c", "sleep 3600"]
         securityContext:
           appArmorProfile:
             type: Localhost
             localhostProfile: restricted
     ```

4. **SELinux**:
   - **仕組み**: Mandatory Access Control (MAC、強制アクセス制御) ポリシーを適用します
   - **特徴**:
     - ラベルに基づく細かなセキュリティポリシーを適用します
     - ホストに設定済みの SELinux ポリシーを適用します
     - 複雑な設定が必要です
   - **実装例**:
     ```yaml
     apiVersion: v1
     kind: Pod
     metadata:
       name: selinux-pod
     spec:
       securityContext:
         seLinuxOptions:
           level: "s0:c123,c456"
       containers:
       - name: app
         image: busybox:1.36
         command: ["sh", "-c", "sleep 3600"]
     ```

5. **OPA Gatekeeper**:
   - **仕組み**: Admission 時にポリシーを強制し、API オブジェクトを定期監査します。システムコールは監視しません
   - **特徴**:
     - 宣言的なポリシー定義
     - 幅広い種類のリソースにポリシーを適用できます
     - 監査モードと強制モードのサポート

6. **商用ツール (Aqua、Sysdig、StackRox など)**:
   - **仕組み**: 包括的なコンテナセキュリティプラットフォームを提供します
   - **特徴**:
     - 脆弱性スキャン、実行時保護、コンプライアンス監視を統合します
     - 機械学習による異常検知
     - ダッシュボードとレポート機能

7. **gVisor**:
   - **仕組み**: アプリケーションとホストカーネルの間にユーザー空間カーネルを設けます
   - **特徴**:
     - コンテナとホストの間に追加の分離層を設けます
     - システムコールの仲介とエミュレーション
     - 性能へのオーバーヘッドがあります
   - **実装例**:
     ```yaml
     apiVersion: node.k8s.io/v1
     kind: RuntimeClass
     metadata:
       name: gvisor
     handler: runsc
     ```

8. **Kata Containers**:
   - **仕組み**: 軽量 VM 内でコンテナを実行します
   - **特徴**:
     - ハードウェア支援による分離を提供します
     - OCI 互換性を維持します
     - 通常のコンテナよりオーバーヘッドが大きくなります

**比較と選定基準**:
  - **セキュリティレベル**: Kata Containers と gVisor は隔離境界を追加します。脅威モデルに照らして選択してください。
  - **性能への影響**: 実際のワークロードで起動時間、I/O、メモリ、システムコールのオーバーヘッドを測定してください。
  - **導入の複雑さ**: Seccomp と AppArmor は比較的簡単ですが、SELinux の設定は複雑です。
  - **監視と防御**: Falco は主に検知と通知に使います。Seccomp、AppArmor、SELinux、OPA Gatekeeper などは構成に応じて実行やリソース操作を制限します。商用製品の機能は製品ごとに異なります。
  - **統合のしやすさ**: OPA Gatekeeper は Kubernetes と緊密に連携します。

Seccomp の Localhost プロファイルは、対象ノードの kubelet が参照する seccomp プロファイル用ディレクトリに事前に配置します。監査専用プロファイルはシステムコールを記録しますが、実行を遮断しません。AppArmor と SELinux には、ホスト側の対応と設定済みプロファイルやラベルが必要です。RuntimeClass handler (`runsc`、`kata`) は CRI ランタイムに事前導入して設定し、Pod の `runtimeClassName` で指定します。RuntimeClass を作成しただけではランタイムは導入されません。Java の Dockerfile 例では、ビルドコンテキストに互換性のある `app.jar` があらかじめ必要です。

組織の脅威モデル、実際のワークロードで測定した性能、運用上の複雑さを踏まえて、適切なツールの組み合わせを選んでください。
</details>
