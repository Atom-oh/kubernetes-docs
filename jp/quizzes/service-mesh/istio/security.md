# セキュリティクイズ

> **最終更新**: September 11, 2026 · Istio 1.31 · Kubernetes 1.32–1.36（EKS標準サポート: 1.34–1.36）。[インストール対応表](../../../service-mesh/istio/01-installation.md)を参照してください。

サイドカー例でIstioセキュリティを確認するクイズです。各問は独立シナリオであり、同じワークロードに全ALLOWポリシーを組み合わせないでください。AmbientのHTTP/JWTポリシーにはwaypointの`targetRefs`が必要で、PeerAuthentication `DISABLE`は非対応です。指定ワークロード、ServiceAccount、ポート、IDは実デプロイと一致する必要があります。

## 選択問題（1-5）

### 問1: PeerAuthenticationモード

PeerAuthenticationの**PERMISSIVE** mTLSモードを正しく説明するものはどれですか？

A. mTLSと平文の両方を許可する\
B. mTLSのみ許可し平文を拒否する\
C. 全通信を拒否する\
D. mTLSを無効にする

<details>

<summary>解答を表示</summary>

**正解: A**

PERMISSIVEは段階的移行のため**mTLSと平文の両方を許可**します。

**解説:**

**PeerAuthenticationのmTLSモード:**

| モード | 説明 | 使用シナリオ |
| -------------- | ------------------------------ | ------------------------------------- |
| **PERMISSIVE** | mTLS + 平文の両方を許可 | 段階的移行、混在環境 |
| **STRICT** | mTLSだけ許可 | 本番のセキュリティ強化 |
| **DISABLE** | 選択した受信側でメッシュmTLSを無効化 | 明示的なレガシー例外 |

**PERMISSIVEモード例:**

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: PERMISSIVE  # Allows both mTLS + plaintext
```

**動作:**

```
Client A (Istio Sidecar) -> [mTLS] -> Server (PERMISSIVE)  Allowed
Client B (No Sidecar)    -> [Plaintext] -> Server (PERMISSIVE)  Allowed
```

**STRICTとの比較:**

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: strict-mtls
  namespace: production
spec:
  mtls:
    mode: STRICT  # Only allows mTLS
```

```
Client A (Istio Sidecar) -> [mTLS] -> Server (STRICT)  Allowed
Client B (No Sidecar)    -> [Plaintext] -> Server (STRICT)  Rejected
```

**移行戦略:**

```
Step 1: PERMISSIVE (Allow mixed traffic)
  |
Step 2: Inject Sidecars to all services
  |
Step 3: STRICT (Enforce mTLS)
```

**参考資料:**

* [PeerAuthentication](../../../service-mesh/istio/security/01-mtls.md)
* [mTLS](../../../service-mesh/istio/security/01-mtls.md)

</details>

***

### 問2: AuthorizationPolicyアクション

これが名前空間内のワークロードを選ぶ唯一のAuthorizationPolicyなら、何を意味しますか？

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all
spec:
  {}
```

A. 全要求を許可する\
B. 全要求を拒否する\
C. ポリシーを適用しない\
D. mTLSだけ許可する

<details>

<summary>解答を表示</summary>

**正解: B**

空specは一致ルールなしのALLOWがデフォルトとなり、このポリシー単体は**全要求を拒否**します。他の一致ALLOWは例外を提供できますが、明示DENY-allはALLOWで上書きできません。

**解説:**

**AuthorizationPolicyのデフォルト動作:**

1. **ポリシーなし**: 全要求を許可
2. **空spec（例のような場合）**: 全要求を拒否
3. **ルールあり**: ルールに基づいて許可/拒否

**デフォルト拒否パターン:**

```yaml
# Step 1: Deny all requests
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all
  namespace: default
spec: {}  # Empty spec = deny all requests

---
# Step 2: Selectively allow only what's needed
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-frontend
  namespace: default
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/frontend"]
    to:
    - operation:
        methods: ["GET", "POST"]
```

**評価:** CUSTOM → DENY → ALLOW。一致するCUSTOM providerが許可し、次に一致DENYがあれば拒否します。該当ALLOWがあれば最低1ルールに一致する必要があります。該当ALLOWがなければこの段階は許可します。ルールとALLOWポリシーは和集合で、追加制約の順序付きリストではありません。AUDITは設定した監査プラグイン用に一致要求をマークします。第4の適用段階ではなく、単体でログ記録もしません。

**実用例:**

```yaml
# Scenario: Restrict HTTP methods
---
# DENY: Prohibit DELETE
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-delete
spec:
  selector:
    matchLabels:
      app: backend
  action: DENY
  rules:
  - to:
    - operation:
        methods: ["DELETE"]

---
# ALLOW: Only allow GET, POST
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-read-write
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/frontend"]
    to:
    - operation:
        methods: ["GET", "POST"]
```

**テスト:** ServiceAccount `frontend`を使うメッシュ参加済みフロントエンドから実行し、バックエンドのHTTPプロトコル/ポート検出を設定します。

```bash
# GET request -> Matches ALLOW policy -> Allowed
curl http://backend/api

# POST request -> Matches ALLOW policy -> Allowed
curl -X POST http://backend/api

# DELETE request -> Matches DENY policy -> Rejected
curl -X DELETE http://backend/api

# PUT request -> No ALLOW policy match -> Rejected
curl -X PUT http://backend/api
```

**参考資料:**

* [認可ポリシー](../../../service-mesh/istio/security/03-authorization.md)

</details>

***

### 問3: JWT認証

RequestAuthenticationでJWTを検証するフィールドはどれですか？

A. issuerとaudiences\
B. principalsとnamespaces\
C. methodsとpaths\
D. hostsとports

<details>

<summary>解答を表示</summary>

**正解: A**

RequestAuthenticationは**issuer**と**audiences**でJWTを検証します。

**解説:**

トークンがある場合、署名、issuer、audience、時刻の検査を通過する必要があります。RequestAuthentication単体はトークン欠損を許すため、AuthorizationPolicyで`requestPrincipals`を必須にします。以下の時刻値は期限切れの過去例で、使用可能トークンではありません。

**JWT構造:**

```
Header.Payload.Signature

Payload example:
{
  "iss": "https://auth.example.com",        # issuer
  "sub": "user@example.com",                # subject
  "aud": ["api.example.com"],               # audiences
  "exp": 1735689600,                        # expiration
  "iat": 1735686000                         # issued at
}
```

**RequestAuthentication設定:**

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-auth
  namespace: default
spec:
  selector:
    matchLabels:
      app: backend
  jwtRules:
  - issuer: "https://auth.example.com"      # Validate iss field
    jwksUri: "https://auth.example.com/.well-known/jwks.json"
    audiences:
    - "api.example.com"                     # Validate aud field
    forwardOriginalToken: true
```

**JWT検証処理:**

![サイドカーが受信JWTのissuer、audiences、JWKS署名、有効期限を順に確認し、失敗なら401 Unauthorizedで拒否、全4確認の通過後のみ通すフローチャート。](../../../.gitbook/assets/en-quizzes-service-mesh-istio-security-0.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-quizzes-service-mesh-istio-security-0.html)

図は存在するトークンの検証を説明し、認可や欠損トークン処理ではありません。以下のprovider例は選択肢です。アプリが期待するトークンタイプとaudienceを設定します。

**OIDCプロバイダーとの統合:**

```yaml
# Google OAuth2 example
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: google-jwt
spec:
  jwtRules:
  - issuer: "https://accounts.google.com"
    jwksUri: "https://www.googleapis.com/oauth2/v3/certs"
    audiences:
    - "123456789-abcdefg.apps.googleusercontent.com"

---
# Keycloak example
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: keycloak-jwt
spec:
  jwtRules:
  - issuer: "https://keycloak.example.com/realms/myrealm"
    jwksUri: "https://keycloak.example.com/realms/myrealm/protocol/openid-connect/certs"
    audiences:
    - "myapp"
```

**AuthorizationPolicyとの併用:**

```yaml
# 1. RequestAuthentication: Validate JWT
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-auth
spec:
  selector:
    matchLabels:
      app: backend
  jwtRules:
  - issuer: "https://auth.example.com"
    jwksUri: "https://auth.example.com/.well-known/jwks.json"
    audiences: ["api.example.com"]

---
# 2. AuthorizationPolicy: Only allow authenticated requests
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: require-jwt
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        requestPrincipals: ["https://auth.example.com/*"]  # Verified issuer + method in the same rule
    to:
    - operation:
        methods: ["GET", "POST"]

```

**テスト:**

```bash
# Request without JWT -> Passes RequestAuthentication, denied by AuthorizationPolicy
curl http://backend/api
# 403 Forbidden

# Request with valid JWT
read -rsp "Test access token: " TOKEN; echo
curl -H "Authorization: Bearer $TOKEN" http://backend/api
unset TOKEN
# 200 OK
```

**参考資料:**

* [リクエスト認証](../../../service-mesh/istio/security/02-authentication.md)

</details>

***

### 問4: mTLS証明書管理

IstioのmTLS証明書のデフォルト有効期間は何ですか？

A. 1時間\
B. 24時間\
C. 7日\
D. 90日

<details>

<summary>解答を表示</summary>

**正解: B**

IstioのmTLS証明書のデフォルト有効期間は**24時間**で、自動更新されます。

**解説:**

エージェントはデフォルトで24時間のリーフ証明書を要求し、ジッターを伴って寿命の約半分で更新します（`SECRET_GRACE_PERIOD_RATIO=0.5`）。Istiodまたは選択した外部CAが要求に署名し、エージェントがSDSでEnvoyへ渡します。ルート/中間の寿命は別です。デフォルト自己署名ルートはワークロードのリーフへ直接署名し、中間階層は管理者の選択です。

ディスク上の`/etc/certs`ファイルや固定SDS配列順序を想定せず、公開証明書を確認します。

```bash
istioctl proxy-config secret <pod-name> -n <namespace> -o json | \
  jq -r '.dynamicActiveSecrets[] | select(.secret.name == "default") | .secret.tlsCertificate.certificateChain.inlineBytes' | \
  base64 -d | openssl x509 -noout -dates -issuer -ext subjectAltName
```

**有効期間のカスタマイズ:**

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    # Change certificate validity period
    defaultConfig:
      proxyMetadata:
        SECRET_TTL: "48h"  # Extend to 48 hours
```

これは`istioctl install -f`の入力断片で、クラスター内Operatorリソースではありません。発行者が要求48時間TTLを制限する場合があります。発行証明書を確認し、ブートストラップ設定変更時に選択プロキシをローテーションします。

更新失敗時は再起動前にエージェント/istiodログ、CA接続、トークン認証、時刻同期、信頼バンドルを調べます。再起動だけでは期限切れCAは直りません。cert-manager統合には**istio-csr**とそのインストール前提条件が必要です。`EXTERNAL_CA=ISTIOD_RA_KUBERNETES_API`だけではcert-manager設定になりません。[証明書ライフサイクルガイド](../../../service-mesh/istio/security/01-mtls.md)を参照します。

</details>

***

### 問5: Service Accountベースの認証

Istioのサービス間認証に使うIDはどれですか？

A. Pod名\
B. Service名\
C. Service Account\
D. 名前空間名

<details>

<summary>解答を表示</summary>

**正解: C**

Istioは**Service Account**に基づいてサービス間IDを管理します。

**解説:**

**Service AccountベースのID:**

```yaml
# 1. Create Service Account
apiVersion: v1
kind: ServiceAccount
metadata:
  name: frontend
  namespace: default

---
# 2. Use Service Account in Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: default
spec:
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      serviceAccountName: frontend  # Used as identity
      containers:
      - name: frontend
        image: registry.example.com/team/frontend:REPLACE_WITH_TESTED_TAG
```

**SPIFFE ID形式:**

```
spiffe://<trust-domain>/ns/<namespace>/sa/<service-account>

Examples:
spiffe://cluster.local/ns/default/sa/frontend
spiffe://cluster.local/ns/production/sa/backend
```

**AuthorizationPolicyでService Accountを使用:**

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-policy
  namespace: default
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  # Only allow frontend Service Account
  - from:
    - source:
        principals:
        - "cluster.local/ns/default/sa/frontend"
    to:
    - operation:
        methods: ["GET", "POST"]
        paths: ["/api/*"]

  # admin Service Account allowed for all operations
  - from:
    - source:
        principals:
        - "cluster.local/ns/default/sa/admin"
```

上のイメージはアプリのプレースホルダーです。Kubernetes RBACはKubernetes APIアクセスを管理し、メッシュ通信権限を自動付与しません。Istio認可は認証済みServiceAccount IDを別に使います。principalには名前空間と信頼ドメインも含まれます。

**Service AccountとPod/Service名の比較:**

| 項目 | Service Account | Pod名 | Service名 |
| -------------------- | ----------------------- | ------------------- | --------------- |
| **安定性** | 安定 | 動的に変化 | 安定 |
| **セキュリティ** | 証明書ベース | 信頼できない | 信頼できない |
| **RBAC統合** | Kubernetes RBAC | 不可 | 不可 |
| **mTLS** | 証明書に含まれる | 含まれない | 含まれない |

**実用例: 3層アプリケーション:**

```yaml
# Frontend -> Backend only allowed
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: frontend
  namespace: app

---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: backend
  namespace: app

---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: database
  namespace: app

---
# Backend policy: Only allow Frontend access
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-policy
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/app/sa/frontend"]

---
# Database policy: Only allow Backend access
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: database-policy
  namespace: app
spec:
  selector:
    matchLabels:
      app: database
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/app/sa/backend"]
```

**Service Accountの確認:**

```bash
# Check pod's Service Account
kubectl get pod <pod-name> -o jsonpath='{.spec.serviceAccountName}'

# Check SPIFFE ID in mTLS certificate
istioctl proxy-config secret <pod-name> -o json | \
  jq -r '.dynamicActiveSecrets[] | select(.secret.name == "default") | .secret.tlsCertificate.certificateChain.inlineBytes' | \
  base64 -d | openssl x509 -text -noout | grep URI

# Output:
# URI:spiffe://cluster.local/ns/default/sa/frontend
```

**名前空間をまたぐ通信:**

```yaml
# Allow production namespace's frontend -> staging namespace's backend access
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-policy
  namespace: staging
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - "cluster.local/ns/production/sa/frontend"
        namespaces:
        - "production"
```

**参考資料:**

* [mTLS](../../../service-mesh/istio/security/01-mtls.md)
* [認可ポリシー](../../../service-mesh/istio/security/03-authorization.md)

</details>

***

## 短答問題（6-10）

### 問6: デフォルト拒否のセキュリティポリシー実装

KubernetesクラスターでIstioによる**デフォルト拒否**ポリシーを実装する手順を説明してください。**必要リソース**（PeerAuthentication、AuthorizationPolicy）と**例外処理**を含めてください。

<details>

<summary>解答を表示</summary>

1. 実呼び出し元、ServiceAccount、ワークロードポート、アプリプロトコルを把握します。メッシュへ参加させ、互換性確認後に名前空間の`STRICT`を適用します。PeerAuthentication単体は呼び出し元を認可しません。
2. 名前空間の基準として空ALLOWを適用し、必要な呼び出し関係に明示ルールを追加します。例外を設ける場合、`rules: [{}]`の`DENY`を使わないでください。
3. 例は名前空間`app`、一致する`app`ラベルとServiceAccountを持つメッシュ参加済みfrontend/backend/database、HTTP 8080、PostgreSQL 5432、`istio-system`のゲートウェイServiceAccount `istio-ingressgateway`を前提とします。実Gateway PodからIDを確認してください。ゲートウェイServiceはHTTPS 443を**ワークロードポート8443**へ対応付け、AuthorizationPolicyはそのポートを使います。`myapp.example.com/api/*`のTLS終端とVirtualServiceは別途設定します。

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: app
spec:
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: default-deny
  namespace: app
spec: {}
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: ingress-public-api
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: ingressgateway
  action: ALLOW
  rules:
  - to:
    - operation:
        ports:
        - '8443'
        hosts:
        - myapp.example.com
        paths:
        - /api/*
        methods:
        - GET
        - POST
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: frontend-policy
  namespace: app
spec:
  selector:
    matchLabels:
      app: frontend
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/istio-system/sa/istio-ingressgateway
    to:
    - operation:
        ports:
        - '8080'
        paths:
        - /api/*
        methods:
        - GET
        - POST
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-policy
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/app/sa/frontend
    to:
    - operation:
        ports:
        - '8080'
        paths:
        - /api/*
        methods:
        - GET
        - POST
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: database-policy
  namespace: app
spec:
  selector:
    matchLabels:
      app: database
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/app/sa/backend
    to:
    - operation:
        ports:
        - '5432'
```

4. サイドカーのデフォルトプローブ書き換えを保持します。kubeletのHTTP/TCP/gRPCプローブはエージェント（通常15020）経由です。HTTP ALLOWパスは平文をSTRICTに通しません。従来のヘルスエンドポイントに平文例外が必要なら、`portLevelMtls`にはワークロードセレクターとワークロードポートが必要で、認可/ネットワーク制限も必要です。汎用ヘルス修正としてアプリポートのmTLSを無効にしないでください。
5. エージェント/Envoyメトリクスポート（15020/15090）は、捕捉されるアプリメトリクスのエンドポイントとは別です。保護されたアプリメトリクスには、ワークロード、実ポート/パス、mTLS認証済みPrometheus principalに限定したALLOWを設定します。エージェントメトリクスではスクレイプとネットワークアクセスを設定します。アプリ受信通信のAuthorizationPolicyだけでは不十分です。
6. 実効設定と許可/拒否両方の通信を検証します。

```bash
istioctl analyze -n app
istioctl proxy-config secret <backend-pod> -n app
istioctl proxy-config clusters <frontend-pod> -n app -o json
istioctl x authz check <backend-pod>.app
# Run from the indicated application containers with the test clients installed.
kubectl exec <frontend-pod> -n app -c frontend -- curl -i http://backend:8080/api/users
kubectl exec <frontend-pod> -n app -c frontend -- pg_isready -h database -p 5432
kubectl exec <backend-pod> -n app -c backend -- pg_isready -h database -p 5432
```

Frontend → backendはアプリへ届き、frontend → databaseはHTTP 403でなくTCP層で失敗するべきです。Backend → databaseはPostgreSQLに到達するべきで、DB認証情報は別チェックです。経路不足では認可テストが意図したバックエンドに達する前に404になる場合があります。名前空間を指定したPod、アプリコンテナ、実テストクライアントを使います。[認可](../../../service-mesh/istio/security/03-authorization.md)と[ヘルスチェック](https://istio.io/latest/docs/ops/configuration/mesh/app-health-check/)を参照してください。

</details>

***

### 問7: JWT + mTLSの二重認証

Istioで **エンドユーザー認証（JWT）** と **サービス間認証（mTLS）** を併用するシナリオを実装してください。KeycloakなどOAuth2/OIDCプロバイダーとの統合方法も含めてください。

<details>

<summary>解答を表示</summary>

Keycloak realm `myrealm`、OIDCクライアント、明示API audience `myapp`を設定します。PKCE付き認可コードフローと正確なHTTPSリダイレクトURIを使います。クライアントタイプ/認証はアプリがシークレットを保管できるかによります。Keycloakロールは通常`realm_access.roles`に現れます。audience mapper/client scopeでAPIトークンに期待する`aud`を持たせます。

`requestPrincipals`や`request.auth.claims`を評価する全プロキシに独自RequestAuthenticationが必要です。ゲートウェイでJWTを検証してもfrontend/backendでの要求IDは成立しません。`forwardOriginalToken`はその転送要求のトークンを保持し、**frontendアプリが新たなbackend要求へAuthorizationを伝播する必要があります**。

以下は問6の関連ポリシーを置き換えます。ロール限定backendルールの隣に広いALLOWを残さないでください。ALLOWは和集合です。デプロイとHTTPSゲートウェイの前提条件は問6と同じです。

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: app
spec:
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: default-deny
  namespace: app
spec: {}
---
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-ingress
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: ingressgateway
  jwtRules:
  - issuer: https://keycloak.example.com/realms/myrealm
    jwksUri: https://keycloak.example.com/realms/myrealm/protocol/openid-connect/certs
    audiences:
    - myapp
    forwardOriginalToken: true
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: ingress-public-api
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: ingressgateway
  action: ALLOW
  rules:
  - to:
    - operation:
        ports:
        - '8443'
        hosts:
        - myapp.example.com
        paths:
        - /api/*
        methods:
        - GET
        - POST
        - DELETE
    from:
    - source:
        requestPrincipals:
        - https://keycloak.example.com/realms/myrealm/*
---
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-frontend
  namespace: app
spec:
  selector:
    matchLabels:
      app: frontend
  jwtRules:
  - issuer: https://keycloak.example.com/realms/myrealm
    jwksUri: https://keycloak.example.com/realms/myrealm/protocol/openid-connect/certs
    audiences:
    - myapp
    forwardOriginalToken: true
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: frontend-policy
  namespace: app
spec:
  selector:
    matchLabels:
      app: frontend
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/istio-system/sa/istio-ingressgateway
        requestPrincipals:
        - https://keycloak.example.com/realms/myrealm/*
    to:
    - operation:
        ports:
        - '8080'
        paths:
        - /api/*
        methods:
        - GET
        - POST
        - DELETE
---
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-backend
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
  jwtRules:
  - issuer: https://keycloak.example.com/realms/myrealm
    jwksUri: https://keycloak.example.com/realms/myrealm/protocol/openid-connect/certs
    audiences:
    - myapp
    forwardOriginalToken: true
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-policy
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/app/sa/frontend
        requestPrincipals:
        - https://keycloak.example.com/realms/myrealm/*
    to:
    - operation:
        ports:
        - '8080'
        paths:
        - /api/users/*
        methods:
        - GET
        - POST
    when:
    - key: request.auth.claims[realm_access][roles]
      values:
      - user
      - admin
  - from:
    - source:
        principals:
        - cluster.local/ns/app/sa/frontend
        requestPrincipals:
        - https://keycloak.example.com/realms/myrealm/*
    to:
    - operation:
        ports:
        - '8080'
        methods:
        - DELETE
        paths:
        - /api/admin/*
    when:
    - key: request.auth.claims[realm_access][roles]
      values:
      - admin
```

スカラーclaimをヘッダーとして必要とするアプリには、RequestAuthenticationの実験的`outputClaimToHeaders`があります。例えば`header: x-user-id`と`claim: sub`です。認可には検証済みJWT claimを使い、呼び出し元提供のIDヘッダーを信頼しないでください。`outputPayloadToHeader`はエンコードされたペイロードを含み、Envoy Luaランタイムには任意の`require("json")`モジュールはありません。ロール配列は無条件でヘッダーへ連結せず、claimとして照合します。

設定したログインフローでテストトークンを取得し、HTTPSをテストします。クイズコマンドにパスワード/クライアントシークレットを埋め込まないでください。

```bash
read -rsp "Test access token: " TOKEN; echo
curl -i -H "Authorization: Bearer $TOKEN" https://myapp.example.com/api/users/test
unset TOKEN
curl -i https://myapp.example.com/api/users/test
# No JWT: 403 from AuthorizationPolicy.
curl -i -H "Authorization: Bearer invalid-token" https://myapp.example.com/api/users/test
# Invalid JWT: 401 from RequestAuthentication.
```

誤ったServiceAccount、有効だが違うaudience、権限不足ロールのトークンもテストします。JWTロール変更は発行済みトークンの即時失効ではありません。トークン寿命と発行者/アプリの失効機構が重要です。[認証](../../../service-mesh/istio/security/02-authentication.md)と[Keycloak grant types](https://www.keycloak.org/securing-apps/oidc-layers)を参照します。

</details>

***

### 問8: 外部サービスのアクセス制御

Istioで**Egress通信**を制御し、特定の外部サービスだけにアクセスを許す方法を説明してください。**ServiceEntry**、**VirtualService**、**AuthorizationPolicy**を使う完全な例を含めてください。

<details>

<summary>解答を表示</summary>

`ALLOW_ANY`は未知の宛先へ転送し、`REGISTRY_ONLY`はプロキシのレジストリにない宛先を拒否します。レジストリにはServiceEntryに加えてKubernetesサービスも含まれます。どちらもファイアウォールではなく、独立したネットワーク制限がなければアプリはプロキシを迂回できます。メッシュ設定は既存インストールvaluesを通じて適用し、1フィールドの断片で`istio` ConfigMap全体を置き換えないでください。

AuthorizationPolicyは選択プロキシが受信する通信を評価します。クライアントサイドカーの名前空間ポリシーは送信ACLではありません。ID/メソッド/パス制御には、メッシュmTLSを終端するEgress Gateway経由にし、そこで認可してから外部サーバーへのTLSを開始します。アプリはサイドカーへHTTPを送り、HTTPSパススルーではHTTPパス/メソッドが見えません。

前提条件は`app`のメッシュ参加クライアント、`istio: egressgateway`ラベル付き専用Egress Gateway、443をワークロード8443へ対応付けるService `istio-egressgateway.istio-system.svc.cluster.local`、他の広いGateway ALLOWがないことです。インストール済みプロキシの公開CA信頼でGitHub証明書を検証する必要があります。

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: github-api
  namespace: app
spec:
  hosts:
  - api.github.com
  location: MESH_EXTERNAL
  resolution: DNS
  ports:
  - number: 80
    targetPort: 443
    name: http
    protocol: HTTP
---
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: github-egress
  namespace: istio-system
spec:
  selector:
    istio: egressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    hosts:
    - api.github.com
    tls:
      mode: ISTIO_MUTUAL
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: to-egress
  namespace: app
spec:
  host: istio-egressgateway.istio-system.svc.cluster.local
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
      sni: api.github.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: github-through-egress
  namespace: app
spec:
  hosts:
  - api.github.com
  gateways:
  - mesh
  - istio-system/github-egress
  http:
  - match:
    - gateways:
      - mesh
      port: 80
    route:
    - destination:
        host: istio-egressgateway.istio-system.svc.cluster.local
        port:
          number: 443
  - match:
    - gateways:
      - istio-system/github-egress
      port: 443
    timeout: 10s
    retries:
      attempts: 2
      perTryTimeout: 3s
      retryOn: connect-failure,reset
    route:
    - destination:
        host: api.github.com
        port:
          number: 80
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: github-origin-tls
  namespace: istio-system
spec:
  host: api.github.com
  workloadSelector:
    matchLabels:
      istio: egressgateway
  trafficPolicy:
    tls:
      mode: SIMPLE
      sni: api.github.com
      subjectAltNames:
      - api.github.com
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: github-egress-allow
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: egressgateway
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/app/sa/backend
    to:
    - operation:
        hosts:
        - api.github.com
        methods:
        - GET
        paths:
        - /users/*
        ports:
        - '8443'
```

メッシュクライアントは`http://api.github.com/users/octocat`を呼びます。サイドカーはISTIO_MUTUALでゲートウェイへ接続します。ゲートウェイHTTPリスナーはbackend ServiceAccountとGET `/users/*`を強制し、port 80 → targetPort 443でGitHubへHTTPSを送れます。例の再試行はこの冪等GET用途向けで、任意の副作用API向けではありません。

```bash
kubectl exec <backend-pod> -n app -c backend -- curl -i http://api.github.com/users/octocat
kubectl exec <frontend-pod> -n app -c frontend -- curl -i http://api.github.com/users/octocat
# Gateway should reject the second caller with HTTP 403.
istioctl proxy-config clusters <egress-pod> -n istio-system --fqdn api.github.com -o json
istioctl x authz check <egress-pod>.istio-system
```

プライベート外部DBは、明示エンドポイント/アドレスとTCP 5432のSTATIC ServiceEntryを使います。TLS/DB認証はそのプロトコル向けに設計します。HTTP専用サービスはHTTP ServiceEntryを使えますが、機密データには暗号化が必要です。API認証情報はアプリか、Secretに基づく対応署名/認証コンポーネントに保存します。VirtualServiceのヘッダーリテラルは読み取り可能な設定で、シークレットストレージではありません。

最後にCNI NetworkPolicy/ファイアウォールで経路を強制します。クライアントは必要メッシュサービス、DNS、istiod、Egress Gatewayへは届きますが、任意のインターネットIPへは届かないようにし、ゲートウェイに必要な外部アクセスを与えます。IPv4/IPv6、迂回/除外ポート、特権ワークロードを考慮します。標準NetworkPolicyはDNS名をフィルターしません。必要なら対応FQDN制御を使います。承認経路だけでなく直接IP/HTTPS迂回もテストします。[Egress制御](../../../service-mesh/istio/traffic-management/11-egress-control.md)と[TLS開始](https://istio.io/latest/docs/tasks/traffic-management/egress/egress-gateway-tls-origination/)を参照してください。

</details>

***

### 問9: セキュリティ監査とログ

Istioのセキュリティ関連イベントを**監査**・記録する方法を説明してください。**AuthorizationPolicyのAUDITアクション**と**アクセスログ**設定を含めてください。

<details>

<summary>解答を表示</summary>

`AUDIT`は**インストール済み監査プラグイン**用に一致要求をマークします。プラグインなしではログ効果はなく、通信の許可/拒否もしません。例は順序付き2条件でなく、DELETEとadminパスの論理積を監査します。

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: audit-sensitive
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
  action: AUDIT
  rules:
  - to:
    - operation:
        methods:
        - DELETE
        paths:
        - /api/admin/*
```

アクセスログは別です。`istioctl install -f`でこのカスタムproviderを既存Istio設定にマージし（他provider/設定を保持）、選択backendだけで有効にします。形式からクエリ文字列、bearer token、完全JWTペイロードを意図的に除外します。

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    extensionProviders:
    - name: security-json
      envoyFileAccessLog:
        path: /dev/stdout
        logFormat:
          labels:
            start_time: '%START_TIME%'
            method: '%REQ(:METHOD)%'
            path: '%REQ_WITHOUT_QUERY(:PATH)%'
            response_code: '%RESPONSE_CODE%'
            response_code_details: '%RESPONSE_CODE_DETAILS%'
            response_flags: '%RESPONSE_FLAGS%'
            peer: '%DOWNSTREAM_PEER_URI_SAN%'
            request_id: '%REQ(X-REQUEST-ID)%'
```

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: backend-security
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
  accessLogging:
  - providers:
    - name: security-json
    filter:
      expression: response.code >= 400 || request.method == "DELETE" || request.url_path.startsWith("/api/admin/")
  metrics:
  - providers:
    - name: prometheus
    overrides:
    - match:
        metric: REQUEST_COUNT
        mode: SERVER
      tagOverrides:
        security_operation:
          value: 'request.url_path.startsWith("/api/admin/") ? "admin" : "other"'
```

Telemetryは要求数に値の限定された`security_operation`ディメンション（`admin`/`other`）も追加します。`request_method`と生URLパスは標準Istioメトリクスラベルではありません。カーディナリティと機密情報のため完全URLラベルは避けます。AUDITプラグインなしでもエラー、DELETE、adminアクセスは記録します。全要求を有効にするにはフィルターを省略し、名前空間全体にはセレクターを省略します。ルート名前空間のセレクターなしポリシーはメッシュ全体です。

CloudWatchには、ノードログマウント、CRI/containerd解析、`log`フィールドのJSON解析、IAM認証情報、CloudWatch出力を持つ対応EKSログエージェントまたはFluent Bit DaemonSetをデプロイ・設定します。ConfigMap単体はエージェントを起動しません。Elasticsearch/OpenSearchにはその宛先用collector出力を使います。provider `envoy`のTelemetryは標準出力へ書き、Elasticsearchを設定しません。FargateはノードDaemonSetでなく対応ログ機構が必要です。

構造化JSONフィールド取り込み後、CloudWatch Logs Insightsクエリを個別に実行します。

```sql
fields @timestamp, method, path, response_code, peer
| filter method = "DELETE"
| sort @timestamp desc
| limit 100
```

```sql
fields @timestamp, path, response_code, response_code_details
| filter path like /^\/api\/admin\//
| filter response_code = "403"
| stats count() by bin(5m), response_code_details
```

403はアプリ、JWT認可、外部providerが返す場合があります。Istioが原因とする前に`response_code_details`、プロキシRBACログ、実効ポリシーを調べます。`envoy_http_rbac_logged_total`を組み込みAUDITカウンターと想定しないでください。実RBAC/実験的dry-run統計はプロキシ設定と命名に依存するため、公開系列を確認します。

Grafanaでは標準destination報告の403レートとカスタムadminディメンションを描画できます。インストール済みPrometheus Operatorが選択するPrometheusRuleで後者にアラートを設定できます。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: istio-security-alerts
  namespace: monitoring
spec:
  groups:
  - name: istio-security
    rules:
    - alert: AdminHTTP403Responses
      expr: sum(rate(istio_requests_total{reporter="destination",security_operation="admin",response_code="403"}[5m]))
        > 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Admin API returned HTTP 403; inspect response_code_details to identify
          the cause
```

新ポリシーを強制する前に、ALLOW/DENYの実験的`istio.io/dry-run: "true"`アノテーションでシャドー判断を報告できます。AUDITとは異なり、診断出力は安定APIではありません。保持、アクセス制御、機密情報のマスキングは実組織/法的要件に合わせます。普遍的な90日/1年の保持義務はありません。[アクセスログ](https://istio.io/latest/docs/tasks/observability/logs/access-log/)と[認可dry-run](https://istio.io/latest/docs/tasks/security/authorization/authz-dry-run/)を参照してください。

</details>

***

### 問10: ゼロトラストネットワークの実装

Istioで**ゼロトラストネットワーク**原則を実装する方法を説明してください。**mTLS STRICT**、**デフォルト拒否**、**最小権限**を適用する完全な例を含めてください。

<details>

<summary>解答を表示</summary>

ゼロトラストは認証済みID、明示的最小権限認可、ワークロード侵害時にも有効な制御を組み合わせます。Istioはデータプレーンが捕捉する通信を保護し、Kubernetes RBAC、アドミッションポリシー、ネットワーク分離、アプリ認可を代替しません。

1. frontend/backend/databaseに別ServiceAccountを与え、互いのアカウントを自由に使用できないようにします。メッシュ参加、信頼ドメイン、証明書発行/更新を確認します。
2. 対象名前空間にSTRICTと空ALLOW基準を適用します。`default`のポリシーは`app`を自動カバーしません。ルート名前空間基準は影響が広く、明示的なゲートウェイ/運用例外が必要です。
3. gateway → frontend → backend → databaseだけを許可します。問6と同じデプロイ前提で、完全な通信ポリシー群は以下です。

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: app
spec:
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: default-deny
  namespace: app
spec: {}
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: ingress-public-api
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: ingressgateway
  action: ALLOW
  rules:
  - to:
    - operation:
        ports:
        - '8443'
        hosts:
        - myapp.example.com
        paths:
        - /api/*
        methods:
        - GET
        - POST
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: frontend-policy
  namespace: app
spec:
  selector:
    matchLabels:
      app: frontend
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/istio-system/sa/istio-ingressgateway
    to:
    - operation:
        ports:
        - '8080'
        paths:
        - /api/*
        methods:
        - GET
        - POST
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-policy
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/app/sa/frontend
    to:
    - operation:
        ports:
        - '8080'
        paths:
        - /api/*
        methods:
        - GET
        - POST
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: database-policy
  namespace: app
spec:
  selector:
    matchLabels:
      app: database
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/app/sa/backend
    to:
    - operation:
        ports:
        - '5432'
```

4. 名前空間分離が必要なら認証済み名前空間/principalで一致させます。`production`を選択し`notNamespaces: [production, istio-system]`を持つDENYは、production → stagingでなく**他の呼び出し元からproductionへの通信**を遮断します。Gatewayと運用者を考慮します。DENYはALLOWより優先されます。
5. 営業時間に依存するアクセスには、明示タイムゾーン、時刻源、失敗方針を持つアプリ認可か設定済みCUSTOM外部認可providerを使います。挿入位置/タイムゾーン不明のLua `os.date()`確認では完全な認可設計ではありません。CUSTOMで許可されてもDENY/ALLOWを通る必要があります。
6. 問8のGatewayパターンとネットワーク制御でEgressを強制します。REGISTRY_ONLYも`deny-all-egress`という名のサイドカーポリシーもファイアウォールではありません。全ホストに一致する受信DENYはアプリ通信を遮断し、ALLOWで戻せません。
7. プローブ書き換えを保持し、正しいポートへのスクレイプを設計して問6の必要例外だけを追加します。エンドユーザー認可には問7のJWT検証とホップごとのトークン伝播を使います。問9のログ/アラートとmTLS章の証明書期限監視を行います。
8. 変更ごとに実ポリシーを確認し、意図した許可/拒否表、TCP DBアクセス、Egress迂回をテストします。

```bash
istioctl analyze -n app
istioctl proxy-config secret <backend-pod> -n app
istioctl proxy-config clusters <frontend-pod> -n app -o json
istioctl x authz check <backend-pod>.app
# Run from the indicated application containers with the test clients installed.
kubectl exec <frontend-pod> -n app -c frontend -- curl -i http://backend:8080/api/users
kubectl exec <frontend-pod> -n app -c frontend -- pg_isready -h database -p 5432
kubectl exec <backend-pod> -n app -c backend -- pg_isready -h database -p 5432
```

クイズ得点は本番準備の証拠ではありません。実環境のワークロードID割り当て、ネットワーク迂回経路、発行者信頼、最小権限ルール、可観測性、ロールバック、アプリ自身の権限を確認します。[セキュリティ概念](https://istio.io/latest/docs/concepts/security/)と[認可](../../../service-mesh/istio/security/03-authorization.md)を参照してください。

</details>

***

## 得点計算

* 選択問題1-5: 各10点（合計50点）
* 短答問題6-10: 各10点（合計50点）
* **合計: 100点**

**評価基準:**

* 90-100点: このクイズのトピックを非常によく理解
* 80-89点: よく理解。実デプロイは別途検証
* 70-79点: 平均的（追加学習を推奨）
* 60-69点: 平均未満（基本概念の復習が必要）
* 0-59点: 再学習が必要

## 学習資料

* [mTLS](../../../service-mesh/istio/security/01-mtls.md)
* [認可ポリシー](../../../service-mesh/istio/security/03-authorization.md)
* [リクエスト認証](../../../service-mesh/istio/security/02-authentication.md)
* [ピア認証](../../../service-mesh/istio/security/01-mtls.md)
