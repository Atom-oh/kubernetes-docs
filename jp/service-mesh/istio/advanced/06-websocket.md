# WebSocket サポート

> **検証基準**: Istio 1.31.0、Kubernetes 1.32～1.37
> **最終レビュー日**: 2026年10月16日

Istio は、生成する HTTP connection manager で WebSocket upgrade を有効にします。この例では、Ingress Gateway で TLS を終端する HTTP/1.1 Upgrade を扱います。HTTP/2 Extended CONNECT と HTTP/3 では、通信経路全体にわたる別個のサポートと設定が必要です。

## 基本設定

前提条件: 以下に示すラベルを持ち、443 番ポートを公開する既存の Ingress Gateway Deployment／Service、`ws.example.com` の DNS 設定、Gateway のワークロード名前空間にある `ws-tls` 証明書／鍵 Secret、そして 8080 番ポートで `/ws` を提供する既存の `app: websocket-service` Pod が必要です。例のドメインは、証明書に含まれる実際のドメインに置き換えてください。以下のリソースは、アプリケーションのデプロイやロードバランサー／証明書の作成は行いません。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: websocket-service
  namespace: default
spec:
  selector:
    app: websocket-service
  ports:
  - name: http
    port: 8080
    targetPort: 8080
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: websocket-service
  namespace: default
spec:
  hosts: ["ws.example.com"]
  gateways: ["istio-system/websocket-gateway"]
  http:
  - match:
    - uri:
        exact: /ws
    - uri:
        prefix: /ws/
    route:
    - destination:
        host: websocket-service.default.svc.cluster.local
        port:
          number: 8080
    retries:
      attempts: 0
```

このルートは、以下の Gateway に明示的にバインドされています。パスで照合することで、大文字と小文字を区別する `Upgrade` ヘッダー照合を不要にできますが、WebSocket ハンドシェイクはアプリケーション側でも検証してください。メッシュによる再試行は無効です。VirtualService のリクエストタイムアウトは省略しており、Istio のデフォルトではルートタイムアウトは無効です。ただし、これは通信経路上のすべての接続／ストリームタイムアウトが無効になることを意味しません。

## Gateway の設定

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: websocket-gateway
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
      credentialName: ws-tls
    hosts: ["ws.example.com"]
```

クライアントは `wss://ws.example.com/ws` を使用します。Gateway はクライアント側の TLS を終端し、その後は設定済みのメッシュ／バックエンド間トランスポートを使用します。アプリケーションでの認証、Origin の確認、認可は引き続き必要です。手前のプロキシやロードバランサーで TLS を終端する場合は、その構成におけるプロトコル、証明書、ヘッダーの信頼性を別途確認してください。

## 接続とタイムアウトの管理

以下の任意の DestinationRule は、元の例の上限値を**負荷テスト用の例示入力値**として維持します。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: websocket-service
  namespace: default
spec:
  host: websocket-service.default.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 1000
      http:
        http1MaxPendingRequests: 1000
        idleTimeout: 3600s
```

`maxConnections` と保留リクエスト数は、プロキシごとの宛先プール制御値であり、クラスター全体の WebSocket 処理能力を保証するものではありません。`connectionPool.http.idleTimeout` は、HTTP 接続にアクティブなリクエスト／ストリームがない状態を指します。アクティブな WebSocket の接続寿命や、メッセージがない時間を 1 時間に制限する値ではありません。

生成された HCM／ルートのストリームアイドル設定、最大ストリーム／接続継続時間、アプリケーションの heartbeat／close ポリシー、およびすべての中継機器のアイドルタイムアウトを確認してください。Istio の HCM 生成設定と、インストール済みの ConnectionSettings によって Envoy のデフォルトが上書きされる場合があります。バッファリングや本文処理を行うフィルターは Upgrade と互換性がないことがあります。レプリカをスケールしても既存の WebSocket 接続は移行しません。書き込みを安易に再送しないようにしながら、接続ドレインとアプリケーションを考慮した再接続を計画してください。

## 検証

```bash
# Inspect the selected gateway and backend configuration.
istioctl proxy-config routes <gateway-pod> -n istio-system
istioctl proxy-config clusters <gateway-pod> -n istio-system --fqdn websocket-service.default.svc.cluster.local

# Bounded HTTP/1.1 handshake check; certificate validation remains enabled.
curl --http1.1 --include --max-time 5 https://ws.example.com/ws -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ=='
```

この HTTP/1.1 チェックで有効なサーバーは、通常 `101` と一致する `Sec-WebSocket-Accept` を返します。curl コマンドが確認するのはハンドシェイクだけです。5 秒の制限時間に達すると、接続が開いたままでも終了コード 28 になることがあります。フレーム、ping／pong、アプリケーション認証、長時間のアイドル状態、close code、ロールアウト時の再接続をテストするには、実際の WebSocket クライアントを使用してください。このドキュメント監査では、デプロイも実稼働セッションのテストも行っていません。

## 参考資料

- [Envoy HTTP upgrades](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/http/upgrades)
- [Envoy timeout types](https://www.envoyproxy.io/docs/envoy/latest/faq/configuration/timeouts)
- [Istio secure ingress](https://istio.io/latest/docs/tasks/traffic-management/ingress/secure-ingress/)
- [Istio VirtualService](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [Istio DestinationRule](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [Istio 1.31 HCM generation](https://raw.githubusercontent.com/istio/istio/1.31.0/pilot/pkg/networking/core/listener_builder.go)
