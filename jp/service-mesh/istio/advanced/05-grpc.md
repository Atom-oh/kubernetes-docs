# gRPC のサポート

> **検証基準**: Istio 1.31.0、Kubernetes 1.32～1.37
> **最終レビュー日**: 2026年10月16日

Istio は、プレーンテキストの gRPC HTTP/2 リクエストを RPC パスやメタデータに基づいてルーティングし、新しい RPC を適格なエンドポイント間で負荷分散できます。長時間続くストリームは選択済みのバックエンドにとどまり、レプリカを増やしても既存ストリームは移行されません。

## 概要

- Service のポート名を `grpc` または `http2` として明示します。アプリケーション側で TLS を管理する場合、設定済みの終端境界で TLS を終端しない限り sidecar から中身を確認できません。メッシュの mTLS は別のトランスポート層です。
- メタデータベースのルーティングでは、ヘッダーは入力値として扱い、認証済み ID として扱いません。
- ヘルスプローブ、受動的な異常ホスト検出、クライアント deadline、メッシュのリトライはそれぞれ別の仕組みであり、個別の設定が必要です。

## 基本設定

この sidecar の例は、`app: grpc-service` を持つ既存ワークロード、ポート 9090 で待ち受ける適格な `version: v2` バックエンド、および `mypackage.MyService` の実装があることを前提にしています。サーバーをデプロイするものではありません。`grpc` ポートの宣言によって HTTP/2 が確立されるため、ここでは一律の `h2UpgradePolicy` は不要です。対象環境で生成されたエンドポイント／ルートと実際の RPC を検証してください。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: grpc-service
  namespace: default
spec:
  selector:
    app: grpc-service
  ports:
  - name: grpc
    port: 9090
    targetPort: 9090
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: grpc-service
  namespace: default
spec:
  hosts: ["grpc-service"]
  http:
  - match:
    - uri:
        prefix: /mypackage.MyService/
    route:
    - destination:
        host: grpc-service
        subset: v2
        port:
          number: 9090
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: grpc-service
  namespace: default
spec:
  host: grpc-service
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
    outlierDetection:
      consecutiveGatewayErrors: 5
      interval: 30s
      baseEjectionTime: 30s
  subsets:
  - name: v2
    labels:
      version: v2
```

`LEAST_REQUEST` は、新しいリクエストについて適格なホスト間で動作します。`outlierDetection` は実際のトラフィックで発生した障害を受動的に観測します。`grpc.health.v1.Health` のプローブを送信するものではなく、カウンターの集計は Envoy に設定されたエラー分類に従います。

## gRPC ヘルスチェック

アプリケーションで標準の gRPC Health Checking Protocol を実装してください。Kubernetes はネイティブの gRPC readiness／liveness／startup probe をサポートしています。たとえば、次の readiness 部分を既存のアプリケーションコンテナにマージします。

```yaml
# Existing application container fragment, not a complete Pod
name: app
readinessProbe:
  grpc:
    port: 9090
  initialDelaySeconds: 5
  periodSeconds: 10
  timeoutSeconds: 1
  failureThreshold: 3
```

ネイティブプローブでは数値のポートを使い、独自の認証／TLS パラメーターは指定できません。アプリケーションのヘルスチェック用リスナーと、Istio のプローブ書き換え／mTLS 経路を確認してください。readiness はエンドポイントの適格性に影響します。liveness はコンテナを再起動するため、下流依存先の障害をすべて再起動理由として扱わないでください。

## リトライ設定

次の代替設定は、`GetItem` が**冪等な単項読み取り**であることを前提としています。多くの gRPC メソッドは HTTP POST を使うため、HTTP メソッドだけでは安全な読み取りと書き込みを区別できません。正確な RPC パスに一致させ、ストリームや書き込みを含むその他の RPC ではメッシュのリトライを無効にしてください。

```yaml
# Alternative to the VirtualService above; do not create a second competing route.
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: grpc-service
  namespace: default
spec:
  hosts: ["grpc-service"]
  http:
  - name: idempotent-unary-read
    match:
    - uri:
        exact: /mypackage.MyService/GetItem
    route:
    - destination:
        host: grpc-service
        subset: v2
        port:
          number: 9090
    timeout: 3s
    retries:
      attempts: 2
      perTryTimeout: 1s
      retryOn: unavailable
  - name: other-rpcs
    match:
    - uri:
        prefix: /mypackage.MyService/
    route:
    - destination:
        host: grpc-service
        subset: v2
        port:
          number: 9090
    retries:
      attempts: 0
```

`attempts: 2` は、初回リクエストの後に最大 2 回リトライする設定です。合計 3 秒のメッシュ timeout とクライアント自身の deadline の範囲内で動作します。バックオフや処理時間のため、3 回の試行すべてが完了するとは限りません。キャンセル、deadline の期限切れ、リソース枯渇を自動的にリトライしないでください。現実的なクライアント deadline を設定し、サーバー処理がキャンセルに応答するようにします。メッシュの timeout だけでは、アプリケーション処理のキャンセルは保証されません。

クライアントライブラリも透過的または設定済みのリトライを行う場合があります。各層でリトライを担当する範囲と予算を調整し、試行数の増幅を避けてください。書き込みを再実行するには、アプリケーション側で冪等性／重複排除を保証する必要があります。また、このルート例で応答の送信を始めたストリームを安全に再開することはできません。

## 参考資料

- [Istio のプロトコル選択](https://istio.io/latest/docs/ops/configuration/traffic-management/protocol-selection/)
- [Istio VirtualService リトライ API](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [Istio DestinationRule](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [gRPC deadline](https://grpc.io/docs/guides/deadlines/)
- [gRPC リトライ](https://grpc.io/docs/guides/retry/)
- [gRPC ヘルスチェック](https://grpc.io/docs/guides/health-checking/)
- [Kubernetes probe](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [gRPC 負荷分散の背景](https://grpc.io/blog/grpc-load-balancing/)
