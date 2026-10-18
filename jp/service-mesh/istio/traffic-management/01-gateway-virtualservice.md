# Gateway と VirtualService

Gateway と VirtualService は、Istio でトラフィックを管理するための中核リソースです。

## 目次

1. [Gateway の概要](#gateway-overview)
2. [VirtualService の概要](#virtualservice-overview)
3. [基本設定](#basic-configuration)
4. [実践例](#practical-examples)
5. [高度なパターン](#advanced-patterns)
6. [トラブルシューティング](#troubleshooting)

この章では、Kubernetes Gateway API とは異なる `networking.istio.io/v1` の Gateway を使用します。各例は、`istio-system` namespace に `istio=ingressgateway` ラベルが付いた既存の Gateway workload/Service、`default` namespace のアプリケーション Service、および一致する Service port があることを前提とします。Istio Gateway は既存の proxy を設定するものであり、proxy 自体を作成するものではありません。TLS Secret は Gateway workload の namespace に作成し、検証する Gateway に VirtualService をバインドしてください。host が重複する例は、相互に置き換えて使う構成です。

<span id="gateway-overview"></span>

## Gateway の概要

Gateway は、mesh への外部トラフィックのエントリーポイントを定義します。

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: my-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway  # Select Ingress Gateway pods
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "myapp.example.com"
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: myapp-tls
    hosts:
    - "myapp.example.com"
```

<span id="virtualservice-overview"></span>

## VirtualService の概要

VirtualService は、mesh の sidecar、明示的に参照された Gateway、またはその両方に適用するルーティングを定義します。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp
  namespace: default
spec:
  hosts:
  - "myapp.example.com"
  gateways:
  - istio-system/my-gateway
  http:
  - match:
    - uri:
        prefix: "/api"
    route:
    - destination:
        host: api-service
        port:
          number: 8080
  - route:
    - destination:
        host: frontend-service
        port:
          number: 3000
```

<span id="basic-configuration"></span>

## 基本設定

### HTTP トラフィック

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: http-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "*"  # Allow all hosts
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: app-routes
spec:
  hosts:
  - "*"
  gateways:
  - istio-system/http-gateway
  http:
  - route:
    - destination:
        host: myapp
        port:
          number: 8080
```

### HTTPS トラフィック

```bash
# Create TLS certificate Secret
kubectl create secret tls myapp-tls \
  --cert=myapp.crt \
  --key=myapp.key \
  -n istio-system
```

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: https-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: myapp-tls
    hosts:
    - "myapp.example.com"
```

<span id="practical-examples"></span>

## 実践例

### パスベースのルーティング

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: path-routing
spec:
  hosts:
  - "myapp.example.com"
  gateways:
  - istio-system/my-gateway
  http:
  # API traffic
  - match:
    - uri:
        prefix: "/api/v1"
    route:
    - destination:
        host: api-v1
        port:
          number: 8080
  # Admin traffic
  - match:
    - uri:
        prefix: "/admin"
    route:
    - destination:
        host: admin-service
        port:
          number: 9000
  # Default traffic
  - route:
    - destination:
        host: frontend
        port:
          number: 3000
```

### ヘッダーベースのルーティング

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: header-routing
spec:
  hosts:
  - reviews
  http:
  # Mobile traffic
  - match:
    - headers:
        user-agent:
          regex: ".*Mobile.*"
    route:
    - destination:
        host: reviews
        subset: mobile-v2
  # Developer traffic
  - match:
    - headers:
        x-dev-user:
          exact: "true"
    route:
    - destination:
        host: reviews
        subset: v3
  # Default traffic
  - route:
    - destination:
        host: reviews
        subset: v1
```

このヘッダーベースの例を使う前に、対応する Pod ラベルを持つ `mobile-v2`、`v3`、`v1` の DestinationRule subset を作成してください。クライアントから指定できるルーティングヘッダーは認可の代わりにはなりません。以下の静的な応答ヘッダーは例示であり、測定したレイテンシーではありません。

### 複数ドメインの設定

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: multi-domain-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https-api
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: api-tls
    hosts:
    - "api.example.com"
  - port:
      number: 443
      name: https-admin
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: admin-tls
    hosts:
    - "admin.example.com"
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-routes
spec:
  hosts:
  - "api.example.com"
  gateways:
  - istio-system/multi-domain-gateway
  http:
  - route:
    - destination:
        host: api-service
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: admin-routes
spec:
  hosts:
  - "admin.example.com"
  gateways:
  - istio-system/multi-domain-gateway
  http:
  - route:
    - destination:
        host: admin-service
```

<span id="advanced-patterns"></span>

## 高度なパターン

### HTTP から HTTPS へのリダイレクト

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: secure-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  # HTTP (for redirect)
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "myapp.example.com"
    tls:
      httpsRedirect: true  # Redirect to HTTPS
  # HTTPS
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: myapp-tls
    hosts:
    - "myapp.example.com"
```

### URL の書き換え

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: url-rewrite
spec:
  hosts:
  - "myapp.example.com"
  gateways:
  - istio-system/my-gateway
  http:
  - match:
    - uri:
        prefix: "/old-api"
    rewrite:
      uri: "/api/v2"  # URL rewrite
    route:
    - destination:
        host: api-service
```

### ヘッダーの追加・変更

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: header-manipulation
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
    headers:
      request:
        add:
          x-custom-header: "custom-value"
          x-demo-stage: "gateway"
        set:
          x-api-version: "v2"
        remove:
          - x-internal-header
      response:
        add:
          x-demo-response: "configured-value"
```

### リダイレクト

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: redirect-example
spec:
  hosts:
  - "myapp.example.com"
  gateways:
  - istio-system/my-gateway
  http:
  - match:
    - uri:
        prefix: "/old-page"
    redirect:
      uri: "/new-page"
      authority: "newapp.example.com"
```

<span id="troubleshooting"></span>

## トラブルシューティング

### Gateway が動作しない

```bash
# 1. Check Gateway status
kubectl get gateways.networking.istio.io -n istio-system

# 2. Check Ingress Gateway pods
kubectl get pods -n istio-system -l istio=ingressgateway

# 3. Check Gateway configuration
kubectl describe gateways.networking.istio.io my-gateway -n istio-system

# 4. Check Envoy configuration
istioctl proxy-config listeners -n istio-system istio-ingressgateway-xxx
```

### VirtualService のルーティング失敗

```bash
# 1. Check VirtualService
kubectl get virtualservice

# 2. Analyze configuration
istioctl analyze

# 3. Check routing rules
istioctl proxy-config routes -n istio-system istio-ingressgateway-xxx

# 4. Check logs
kubectl logs -n istio-system -l istio=ingressgateway --tail=100
```

### TLS 証明書の問題

```bash
# Check Secret
kubectl get secret -n istio-system myapp-tls

# Check Secret contents
kubectl describe secret -n istio-system myapp-tls

# Check Gateway TLS configuration
istioctl proxy-config secret -n istio-system istio-ingressgateway-xxx
```

## ベストプラクティス

1. **Namespace の分離**: Gateway は `istio-system`、VirtualService はアプリケーション Namespace に配置します
2. **TLS が必須**: 本番環境では常に HTTPS を使用します
3. **明示的な Host 指定**: ワイルドカード（`*`）ではなく明示的なドメインを使用します
4. **Match 条件の順序**: 特定の条件を先に、一般的な条件を最後に配置します
5. **リソースの命名**: 一貫した命名規則を使用します

## 参照

- [Istio Gateway](https://istio.io/latest/docs/reference/config/networking/gateway/)
- [Istio VirtualService](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [Ingress Traffic](https://istio.io/latest/docs/tasks/traffic-management/ingress/)
