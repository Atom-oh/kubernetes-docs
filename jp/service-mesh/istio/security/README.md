# セキュリティ

> **レビュー済みバージョン**: Istio 1.31.0
> **最終更新日**: 2026年9月11日

Istio は service mesh に堅牢なセキュリティ機能を提供します。Zero Trust セキュリティモデルに基づき、サービス間通信を自動的に暗号化し、きめ細かなアクセス制御を実現します。

## 目次

1. [セキュリティアーキテクチャの概要](#security-architecture-overview)
2. [主要なセキュリティ機能](#core-security-features)
3. [セキュリティコンポーネント](#security-components)
4. [詳細ドキュメント](#next-steps)
5. [セキュリティのベストプラクティス](#security-best-practices)
6. [セキュリティモニタリング](#3-security-monitoring)

## セキュリティアーキテクチャの概要 {#security-architecture-overview}

<p align="center">
  <img src="https://istio.io/latest/docs/concepts/security/arch-sec.svg" alt="Istio Security Architecture" width="900">
</p>

Istio は、メッシュに参加している通信に対して **Zero Trust セキュリティモデル**を実装します。通信の除外設定、平文を使うクライアント、サポート対象外のプロトコルには、別途明示的な制御が必要です。主なセキュリティ上の役割を以下に示します。

### セキュリティアーキテクチャのレイヤー

![Diagram showing the istiod Certificate Authority and Configuration API distributing certificates and policy to the Envoy sidecars in two pods, which encrypt only the sidecar-to-sidecar hop with mTLS, above a five-step security-layer chain from identity to authorization.](../../../.gitbook/assets/en-service-mesh-istio-security-readme-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-security-readme-0.html)

### セキュリティコンポーネント {#security-components}

1. **コントロールプレーン（istiod）**
   - 認証局（CA）: X.509 証明書の発行と管理
   - Configuration API: セキュリティポリシーの配布と管理
   - Service Discovery: ワークロード ID の管理

2. **データプレーン（Envoy サイドカー、または ambient の ztunnel / waypoint）**
   - mTLS の終端点: サービス間の暗号化通信
   - ポリシー適用: 認証・認可ポリシーの適用
   - セキュリティテレメトリ: セキュリティメトリクスの収集

3. **ID 管理**
   - SPIFFE 標準に基づく強力な ID 管理
   - Kubernetes ServiceAccount との連携
   - 証明書のデフォルト有効期間は 24 時間で、有効期限前にローテーションされます

4. **ポリシーエンジン**
   - CRD ベースの宣言型セキュリティポリシー
   - きめ細かなアクセス制御（RBAC）
   - 監査ログのサポート

## 主要なセキュリティ機能 {#core-security-features}

Istio は、次の主要なセキュリティ機能を提供します。

### 1. 通信セキュリティ（mTLS）

参加中のワークロードを PERMISSIVE から STRICT に移行する前に、必要なクライアントがすべて mTLS を使用していることを確認してください。

Auto mTLS は、メッシュに参加しているピア間の通信を暗号化します。PERMISSIVE は平文通信も受け入れます。選択したインバウンドワークロードでメッシュの mTLS を必須にするには STRICT を使用します。

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # Production: STRICT, Migration: PERMISSIVE
```

**モードの説明**:
- **STRICT**: mTLS のみを許可します（本番環境に推奨）。
- **PERMISSIVE**: mTLS と平文の両方を許可します（移行時に使用）。
- **DISABLE**: sidecar モードで Istio のトランスポート mTLS を無効にします。ambient ではサポートされません。

以下のポリシー例は sidecar の selector を使用します。ambient では ztunnel が L4 セキュリティを適用します。JWT などの L7 ポリシーには、適切な waypoint と targetRefs のアタッチメントが必要です。

### 2. 認証

<p align="center">
  <img src="https://istio.io/latest/docs/concepts/security/authn.svg" alt="Authentication Architecture" width="700">
</p>

Istio では、次の 2 層で認証を行います。

- **Peer Authentication**: サービス間認証（mTLS と SPIFFE ID）
- **Request Authentication**: 対応する issuer の JWT を検証します。ログインや OAuth フローは外部で処理します。

**例**:
```yaml
# Request Authentication (JWT)
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-auth
  namespace: default
spec:
  jwtRules:
  - issuer: "https://accounts.google.com"
    jwksUri: "https://www.googleapis.com/oauth2/v3/certs"
    audiences: ["<your-google-client-id>"]
```

### 3. 認可

<p align="center">
  <img src="https://istio.io/latest/docs/concepts/security/authz.svg" alt="Authorization Architecture" width="600">
</p>

きめ細かなアクセス制御ポリシーを適用できます。AuthorizationPolicy は、次の情報に基づいて制御します。
- ServiceAccount / Namespace
- HTTP メソッド / パス
- IP アドレス
- JWT クレーム

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-read
spec:
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/myapp"]
    to:
    - operation:
        methods: ["GET"]
        paths: ["/api/*"]
```

## セキュリティのベストプラクティス {#security-best-practices}

### 1. 多層防御

トランスポート層の ID、検証済みのリクエスト資格情報、明示的な認可ルールを組み合わせます。

複数の層にセキュリティを適用して、多層防御を実現します。

**ネットワーク層**:
```yaml
# 1. Enable mTLS STRICT mode
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT
```

**アプリケーション層**:
```yaml
# 2. Enable JWT authentication
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: require-jwt
  namespace: default
spec:
  jwtRules:
  - issuer: "https://your-auth-provider.com"
    jwksUri: "https://your-auth-provider.com/.well-known/jwks.json"
    audiences: ["<your-api-audience>"]
```

**アクセス制御層**:
```yaml
# 3. Default deny policy
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all
  namespace: default
spec:
  action: ALLOW
  rules: []
---
# 4. Allow only required access
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-specific
  namespace: default
spec:
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/frontend/sa/webapp"]
        requestPrincipals: ["*"]
    to:
    - operation:
        methods: ["GET", "POST"]
```

RequestAuthentication だけではトークンは必須にならず、トークンのないリクエストも受け入れられます。上記の ALLOW 例では、検証済みのピアと検証済みのリクエストプリンシパルの両方を要求します。空の ALLOW ポリシーはデフォルト拒否を設定します。DENY の全拒否ルールは例外より優先され、それらもブロックします。これらの namespace 単位の例は、一致するすべてのワークロードに影響します。selector や targetRefs を使って対象を意図的に絞ってください。AUDIT の利用には監査実装の設定が必要です。また、アクセスログは別途有効にする必要があります。

### 2. 最小権限の原則

- 各サービスには必要最小限の権限だけを付与します。
- ServiceAccount を用途に応じて細かく分離します。
- namespace による分離を活用します。

<span id="3-security-monitoring"></span>

### 3. セキュリティモニタリング

- Istio のアクセスログを有効にします。
- Prometheus でセキュリティメトリクスを収集します。
- Kiali で mTLS の状態を監視します。

## 次のステップ {#next-steps}

1. **[mTLS](01-mtls.md)**: サービス間の暗号化と ID 管理
2. **[認証](02-authentication.md)**: JWT と OAuth/OIDC の連携
3. **[認可](03-authorization.md)**: きめ細かなアクセス制御ポリシー

## 参考資料

### 公式ドキュメント
- [Istio Security Concepts](https://istio.io/latest/docs/concepts/security/)
- [Security Best Practices](https://istio.io/latest/docs/ops/best-practices/security/)
- [Security Reference](https://istio.io/latest/docs/reference/config/security/)

### 関連標準
- [SPIFFE Specification](https://github.com/spiffe/spiffe)
- [OAuth 2.0 / OIDC](https://oauth.net/2/)
- [JWT (RFC 7519)](https://datatracker.ietf.org/doc/html/rfc7519)

## クイズ

この章の理解を確認するには、[Istio Security Quiz](../../../quizzes/service-mesh/istio/security.md)に挑戦してください。
