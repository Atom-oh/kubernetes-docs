# Linkerd のトラフィック管理

> **最終更新日**: 2026年10月16日 · Linkerd edge-26.10.1 · Gateway API 1.5.1 · Flagger 1.45.0

現在の Linkerd ルーティングでは、Gateway API リソースとサポート対象のアノテーションを使用します。ServiceProfile は互換性のためのインターフェイスとして引き続き利用できますが、TrafficSplit/linkerd-smi は非推奨です。これらの方式は相互に置き換え可能ではありません。同じ Service に ServiceProfile が存在すると、送信側 HTTPRoute より優先され、新しい再試行、タイムアウト、障害蓄積の設定が適用されません。

以下の例は、既存のテスト済みアプリケーションワークロードを使う個別の演習です。[インストールの前提条件](01-installation.md)、適切な namespace 登録、宣言済みの Service/コンテナーポート、Ready なエンドポイントを前提とします。このレビューでは、クラスターのインストール、トラフィック切り替え、本番負荷テストを実施していません。

## トラフィック管理の構成

| ポリシー経路 | 用途 | 重要な境界 |
|---|---|---|
| Service を親とする HTTPRoute | メッシュ内クライアントからの送信ルーティングと信頼性制御 | クライアントがメッシュに参加し、HTTP を検査できる必要があります |
| Server を親とする HTTPRoute | 受信認可のマッチング | アタッチ先とポリシー上の役割が異なります |
| ServiceProfile | 従来のルートメトリクス、再試行、タイムアウト | 同じ Service では新しいポリシー経路より優先されます |
| TrafficSplit | SMI による従来の重み付きルーティング | 非推奨の拡張機能と CRD が必要です |

Service ベースのポリシーは Service ディスカバリーに依存します。Pod IP への直接アクセスや headless Service、メッシュ外のクライアント、アプリケーションが開始する不透明な TLS 通信では、同じ L7 動作が自動的に得られるわけではありません。ID、認可、ルーティングは別々の制御として扱ってください。

## 現行 HTTPRoute によるルーティング

### Service と重み付きルーティング

この演習では、app:web と version:stable/canary のラベルを持ち、8080 で待ち受ける stable/canary Deployment を準備し、ワークロードに適した readiness を設定します。以下の namespace 設定は、新しく作成された対象 Pod をメッシュに登録します。アプリケーション自体をデプロイするものではありません。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: route-demo
  annotations:
    linkerd.io/inject: enabled
---
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: route-demo
spec:
  selector:
    app: web
    version: stable
  ports:
  - name: http
    port: 80
    targetPort: 8080
    appProtocol: http
---
apiVersion: v1
kind: Service
metadata:
  name: web-stable
  namespace: route-demo
spec:
  selector:
    app: web
    version: stable
  ports:
  - name: http
    port: 80
    targetPort: 8080
    appProtocol: http
---
apiVersion: v1
kind: Service
metadata:
  name: web-canary
  namespace: route-demo
spec:
  selector:
    app: web
    version: canary
  ports:
  - name: http
    port: 80
    targetPort: 8080
    appProtocol: http
```

頂点 Service は Kubernetes の通常のルーティング先として **stable** Pod を選択します。この selector は未使用ではありません。メッシュ外の通信やポリシー対象外の通信にも、意図したバックエンドが必要です。HTTPRoute は、対象となるメッシュ内クライアントの通信をバックエンド Service に振り分けます。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: web-route
  namespace: route-demo
spec:
  parentRefs:
  - group: ''
    kind: Service
    name: web
    port: 80
  rules:
  - backendRefs:
    - name: web-stable
      port: 80
      weight: 90
    - name: web-canary
      port: 80
      weight: 10
```

group:"" は Service 参照で使う正規のコア API グループです。Linkerd の一部の経路には古いコアグループ別名も残っていますが、移植性のある Gateway API リソースでは空の group を使ってください。参照先の 80 は Service のポートであり、コンテナーの 8080 ではありません。

重みは相対値で、0 以上とし、合計が正である必要があります。90/10 と 9/1 は同じ比率を表し、合計を 100 にする必要はありません。これはルーティング設定であり、短時間での正確な要求数、接続数の均等化、レプリカ数との対応を保証するものではありません。

```bash
kubectl -n route-demo get httproute web-route -o yaml
kubectl -n route-demo get endpointslices.discovery.k8s.io \
  -l kubernetes.io/service-name=web-stable -o yaml
linkerd diagnostics policy -n route-demo svc/web 80 -o json
linkerd viz stat deploy/client -n route-demo --to svc/web
linkerd viz stat pods -n route-demo
```

Route の Accepted/ResolvedRefs 条件、実際のコントローラーポリシー、クライアントからの実トラフィックを確認してください。コントローラーのポリシー表示だけでは、すべてのプロキシに設定が反映済みである証明にはなりません。

### ヘッダーとパス

次は web-route を**置き換える別の例**です。重み付きの既定ルールの前に、canary グループ用のヘッダー条件を追加します。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: web-route
  namespace: route-demo
spec:
  parentRefs:
  - group: ''
    kind: Service
    name: web
    port: 80
  rules:
  - matches:
    - headers:
      - name: x-release-track
        type: Exact
        value: canary
    backendRefs:
    - name: web-canary
      port: 80
  - backendRefs:
    - name: web-stable
      port: 80
      weight: 90
    - name: web-canary
      port: 80
      weight: 10
```

ヘッダー値は認証済み ID ではありません。信頼できないクライアントも x-release-track や x-debug を設定できるため、特権バックエンドやデバッグ用バックエンドには別の認可を使ってください。Cookie:beta=true の完全一致は、ヘッダー全体がその値の場合にだけ一致し、複数の Cookie の中にその値が含まれるかどうかは判定しません。完全一致から一般的な Cookie の意味を推測せず、認可済みのグループ信号を正規化するか、意図した Cookie 解析を実装してください。

別途準備した Service 向けのパスルーティング例です。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: frontend-paths
  namespace: route-demo
spec:
  parentRefs:
  - group: ''
    kind: Service
    name: frontend
    port: 80
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    backendRefs:
    - name: api-service
      port: 80
  - matches:
    - path:
        type: PathPrefix
        value: /static
    backendRefs:
    - name: static-service
      port: 80
  - backendRefs:
    - name: web-stable
      port: 80
```

1 つのエントリ内の条件は AND で評価されます。複数のエントリやルール、および競合する Route は Gateway API の優先順位に従います。異なる HTTPRoute オブジェクト間の競合が、ファイル内の記述順だけで解決すると想定しないでください。


## 再試行とタイムアウト

再試行は送信側で任意に有効化する動作であり、失敗した要求が自動的に回復する保証ではありません。実際の操作を安全に再実行できる場合に限って使ってください。reset、error、timeout が起きると、サーバー側で書き込みが完了したか不明になることがあります。アプリケーションの冪等性とクライアント側の再試行は、別途制御する必要があります。

retry-demo にある既存の Service api に対し、この設定では GET /api/read とその配下のパスだけを再試行し、それ以外の要求は転送する fallback を設定します。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api-read
  namespace: retry-demo
  annotations:
    retry.linkerd.io/http: gateway-error
    retry.linkerd.io/limit: '2'
    retry.linkerd.io/timeout: 400ms
    timeout.linkerd.io/request: 2s
spec:
  parentRefs:
  - group: ''
    kind: Service
    name: api
    port: 80
  rules:
  - matches:
    - method: GET
      path:
        type: PathPrefix
        value: /api/read
    backendRefs:
    - name: api
      port: 80
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api-default
  namespace: retry-demo
spec:
  parentRefs:
  - group: ''
    kind: Service
    name: api
    port: 80
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /
    backendRefs:
    - name: api
      port: 80
```

この例を使うには、**親 Service に再試行アノテーションがないこと**、競合する ServiceProfile がないこと、信頼できない要求単位のポリシー上書きが有効になっていないことが必要です。そうでなければ、fallback の要求にも再試行ポリシーが適用される可能性があります。実効ポリシーを確認し、書き込み要求の挙動を別に測定してください。書き込みを転送する設定だけでは、すべてのレイヤーで再試行が無効だとは言えません。

アノテーションは最大 2 回の再試行（最大 3 回の試行）、400ms の再試行タイムアウト、2s の要求全体タイムアウトを設定します。要求の期限には試行に使う時間も含まれるため、再試行をすべて実行する前に処理が終了することがあります。現行のリファレンスでは、本文が 64KiB を超える要求は再試行されません。

**edge-26.10.1 で retry.linkerd.io/limit:"0" を無効化スイッチとして使わないでください。** [リリース版パーサー](https://github.com/linkerd/linkerd2/blob/edge-26.10.1/policy-controller/k8s/index/src/outbound/index/http.rs)では、0 は未指定値として除外されます。再試行条件がある場合、結果として 1 回の再試行にフォールバックします。空の HTTP retry-condition 文字列も、サポート対象の「再試行しない」ポリシーではありません。メソッドが混在する Service の既定設定には再試行を置かず、対象の読み取り Route だけに任意のポリシーを設定してください。

Route の再試行アノテーションは Service の再試行設定を一括して上書きし、Route の timeout アノテーションも同様に Service の timeout アノテーションを上書きします。ServiceProfile はこれらのアノテーションより優先されます。明示的に有効化すると、Linkerd は要求単位の l5d-* ヘッダーを任意で尊重できます。信頼できないクライアントからのポリシー上書きを受け入れず、それらのヘッダーを認証として扱わないでください。

### 期限が適用される範囲

| 設定 | 適用範囲 |
|---|---|
| timeout.linkerd.io/request | 要求と応答のストリーム全体 |
| timeout.linkerd.io/response | バックエンド応答が進行中の時間 |
| timeout.linkerd.io/idle | ストリームの無通信時間 |
| retry.linkerd.io/timeout | 再試行可能な試行に対する timeout。再試行ポリシーと上限に従います |
| ServiceProfile の Route timeout | 再試行を含む、従来の Route 全体の待機時間 |

通常の request/response/idle timeout は再試行の timeout とは異なります。timeout が発生したからといって、業務処理がキャンセルされた証拠にはなりません。応答ヘッダーや本文の送信が始まった後に失敗した場合、新しい HTTP エラー応答を返すのではなく、ストリームを終了または reset することがあります。

![応答ヘッダーが確定する前に HTTP の期限が到来した場合の例。期限内の応答は成功し、timeout では 504 が返ることがあります。クライアントの timeout はバックエンド処理が停止した証拠ではありません。](../../.gitbook/assets/en-service-mesh-linkerd-03-traffic-management-2.png)

[インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-linkerd-03-traffic-management-2.html)

「同期」「非同期」「ファイルアップロード」といったラベルだけを根拠に、5/60/600 秒の値を決めないでください。アプリケーション全体の期限、想定される処理やストリーミングの動作、クライアントとサーバーのキャンセル動作から設計を始めます。あるポリシーの timeout を省略しても、アプリケーション、転送経路、プロキシ、ロードバランサーにある他の制限はなくなりません。

## ServiceProfile: 互換性のための設定

ServiceProfile は引き続きサポートされていますが、新機能の開発では Gateway API の設定に置き換えられています。この**別個の profile-demo 演習**は、従来の Route マッチングと、書き込みを明示的に再試行しない設定の有効な例です。

```yaml
apiVersion: linkerd.io/v1alpha2
kind: ServiceProfile
metadata:
  name: api.profile-demo.svc.cluster.local
  namespace: profile-demo
spec:
  routes:
  - name: read-users
    condition:
      all:
      - method: GET
      - pathRegex: ^/api/users(/.*)?$
    isRetryable: true
    timeout: 5s
  - name: write-api
    condition:
      all:
      - any:
        - method: POST
        - method: PUT
        - method: PATCH
        - method: DELETE
      - pathRegex: ^/api/.*$
    isRetryable: false
    timeout: 10s
  - name: health
    condition:
      all:
      - method: GET
      - pathRegex: ^/(health|ready|live)$
    isRetryable: false
    timeout: 1s
  - name: stream
    condition:
      all:
      - method: GET
      - pathRegex: ^/stream$
    isRetryable: false
  retryBudget:
    retryRatio: 0.2
    minRetriesPerSecond: 10
    ttl: 10s
```

method は正規表現ではなく、HTTP メソッドとの完全一致です。POST|PUT|DELETE は複数メソッドの和集合を表しません。明示的な any/all 条件または別々の Route を使い、必要に応じて PATCH も含めてください。Route の選択と応答分類はアプリケーションに合わせる必要があります。retryable フラグは運用者による安全性の宣言であり、冪等性を自動的に証明するものではありません。

isRetryable:false は一致した Route に対する、この ServiceProfile の再試行方式を無効にします。SDK、クライアント、その他の中継による再試行は止めません。stream Route では profile timeout を省略しています。これはそのフィールドによる timeout がないという意味で、エンドツーエンドの処理が無期限になる意味ではありません。

### 再試行予算

retryRatio:0.2 は比率に応じた再試行枠を加えます。minRetriesPerSecond:10 はそれとは独立した枠を加えるため、低トラフィック時にも**厳密な 20% 上限となるわけではありません**。ttl は予算計算に使う参照・保持期間であり、定期的にリセットするタイマーではありません。実際に再試行されるかどうかは、Route の適格性、応答分類、バッファリング、期限、利用可能なエンドポイントにも左右されます。

![ServiceProfile による再試行の例。対象となる要求の初回試行が失敗し、許可された再試行が成功します。再試行が成功する保証でも、最終結果だけを測ればよいという意味でもありません。](../../.gitbook/assets/en-service-mesh-linkerd-03-traffic-management-1.png)

[インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-linkerd-03-traffic-management-1.html)

失敗した試行、追加された上流への送信、最終結果を分けて観測してください。この図は再試行が成功する一例であり、すべての失敗が隠れるという約束ではありません。

### Profile の生成と観測

```bash
# SERVICE is the short Service name; the CLI adds the namespace/domain.
linkerd profile -n profile-demo --open-api swagger.yaml api > api-openapi-profile.yaml
linkerd profile -n profile-demo --proto service.proto api > api-proto-profile.yaml
# Requires actual Viz tap traffic; the final Service argument is mandatory.
linkerd viz profile -n profile-demo api --tap deploy/api --tap-duration 60s \
  > api-observed-profile.yaml
# For offline generation with default assumptions, use --ignore-cluster.
```

native CLI では短い Service 名が必要で、元の完全修飾名を引数に渡すと拒否されます。tap コマンドにも最後の Service 引数が必要です。OpenAPI/protobuf/tap の出力はレビューしてください。観測できた通信は Route の完全な一覧ではなく、生成されるパスが高カーディナリティのメトリクスを生むことがあります。生成したからといって、すべての操作を安全に再試行できるとは限りません。

```bash
linkerd viz routes service/api -n profile-demo -o wide
linkerd viz routes deploy/client -n profile-demo --to svc/api -o wide
linkerd viz stat deploy/client -n profile-demo --to svc/api
```

viz routes は ServiceProfile 向けの Route 表示です。実際に使用しているバージョンの wide/JSON 出力と、文書化されたメトリクスを使ってください。以前の架空の [RETRIES] 行や、推測で置いたトップレベルの .success_rate フィールドは、信頼できる自動化インターフェイスではありません。


## 負荷分散と障害蓄積

Linkerd は HTTP 要求の負荷分散に遅延を考慮する EWMA を使用し、TCP は接続単位で負荷分散します。正常で応答の速い候補が優先されますが、すべての要求が表示されたスコアの中で最小のエンドポイントを必ず選ぶという意味ではありません。Pod 単位の統計と、送信元から Service への統計は、異なる集計を表します。

### 明示的に有効化するサーキットブレーカー

現行の HTTP 障害蓄積は、Service に設定しない限り**無効です**。その Service に ServiceProfile がある場合は併用できません。別の circuit-demo namespace に準備した api ワークロードを使う例です。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: circuit-demo
  annotations:
    balancer.linkerd.io/failure-accrual: consecutive
    balancer.linkerd.io/failure-accrual-consecutive-max-failures: '7'
    balancer.linkerd.io/failure-accrual-consecutive-min-penalty: 1s
    balancer.linkerd.io/failure-accrual-consecutive-max-penalty: 1m
spec:
  selector:
    app: api
  ports:
  - name: http
    port: 80
    targetPort: 8080
    appProtocol: http
```

連続失敗ポリシーの既定のしきい値は 7 です。接続失敗が自動的に 5 回続くことを条件とするものではありません。対象となる HTTP/gRPC 応答の失敗を追跡するもので、あらゆる TCP 接続エラーに適用される一般的な仕組みではありません。選択したリリースでは、成功率やレート制限を扱う統合ポリシーも説明されています。使う前に別々のパラメーターを確認してください。

| 状態 | 意味 |
|---|---|
| Available | ロードバランサーがエンドポイントを選択できます |
| Unavailable | 可能であれば通常の要求は他のエンドポイントに送られます |
| Probation | バックオフ後、実際のアプリケーション要求を通じて復旧を試します |

Probation は Kubernetes のヘルスプローブを定期的に自動生成しません。対象となるアプリケーション通信がなければ、/ready の確認に成功しただけではエンドポイントは復旧しません。バックオフには設定した時間と jitter が含まれます。利用可能なエンドポイントがすべて失敗すると、要求も失敗するか、別途設定されたバックエンドが選ばれる場合があります。

```bash
linkerd diagnostics policy -n circuit-demo svc/api 80 -o json
linkerd viz stat pods -n circuit-demo
linkerd viz stat deploy/client -n circuit-demo --to svc/api
```

Pod の readiness や成功率の集計だけで判断せず、実際のポリシーと結果を確認してください。outbound_http_balancer_endpoints メトリクスは Ready と pending のエンドポイント数を区別します。pending は障害蓄積だけに起因する状態ではありません。

## 従来の TrafficSplit と SMI

TrafficSplit と linkerd-smi は非推奨であり、別の拡張機能と CRD が必要です。通常の現行 Linkerd インストールで TrafficSplit の YAML を適用しただけでは、このワークフローは利用できません。新しい構成にはサポート対象の Gateway API ルーティングを使い、既存の SMI インストールは移行を計画してください。

![重みを90/10にした従来の SMI TrafficSplit の図。ルーティングを行うのはメッシュ内のクライアントプロキシであり、頂点の Kubernetes Service 自体ではありません。新しい例では Gateway API を使用します。](../../.gitbook/assets/en-service-mesh-linkerd-03-traffic-management-4.png)

[インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-linkerd-03-traffic-management-4.html)

従来のリソースでは service フィールドに頂点 Service を指定し、バックエンドには相対的な重みを設定します。既存設定の読み解きには役立ちますが、上の現行例では HTTPRoute を使います。メッシュ外や fallback 通信では Service selector が引き続き重要です。頂点 Service の selector によって、トラフィックポリシーの対象外のクライアントに canary Pod を誤って公開しないようにしてください。

手動で段階的に変更する場合は、実トラフィック、エラー、レイテンシの状況を確認しながら、設定済みの段階を 1 つずつ検証してください（例: 99/1、90/10、50/50）。同じ名前のリソースを複数、1 つのファイルに適用しても、時間をかけたロールアウトにはなりません。最後に適用された状態が有効になります。

### 明示的な手動ロールバック

**手動管理の route-demo の例だけ**を対象に、web-stable-only.yaml として以下を保存し、stable のみを使う状態を定義します。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: web-route
  namespace: route-demo
spec:
  parentRefs:
  - group: ''
    kind: Service
    name: web
    port: 80
  rules:
  - backendRefs:
    - name: web-stable
      port: 80
      weight: 100
    - name: web-canary
      port: 80
      weight: 0
```

```bash
# Review the target context and this manually owned route before applying.
kubectl apply -f web-stable-only.yaml
kubectl -n route-demo get httproute web-route -o yaml
```

変更後はコントローラーによる受理、Ready な stable エンドポイント、クライアントからの実際の結果を確認してください。以前のシェルループは「Rolling back」と表示した後、ループから抜けるだけで重みを戻していませんでした。データがない場合やエラーの場合の扱いも確実ではありませんでした。自動化には実際のデリバリーコントローラーを使い、Flagger が所有する Route を手動で上書きしないでください。

## Flagger による段階的デリバリー

### バージョン指定とリソース所有権

この構成例は Flagger/chart 1.45.0、選択した Linkerd/Gateway API のインストール、既存の Linkerd Viz Prometheus を使用します。リリース済みの factory では、meshProvider:linkerd は引き続き SMI router に対応付けられています。現行の HTTPRoute router には **gatewayapi:v1** を使ってください。provider の文字列を省略したり、関係のない値を使ったりしても同じ意味にはなりません。

flagger-values.yaml として保存します。

```yaml
image:
  tag: 1.45.0
meshProvider: gatewayapi:v1
metricsServer: http://prometheus.linkerd-viz.svc.cluster.local:9090
crd:
  create: true
prometheus:
  install: false
podAnnotations:
  linkerd.io/inject: enabled
linkerdAuthPolicy:
  create: true
  namespace: linkerd-viz
```

```bash
helm repo add flagger https://flagger.app
helm repo update flagger
helm template flagger flagger/flagger --version 1.45.0 \
  -n flagger-system -f flagger-values.yaml > flagger-rendered.yaml
# Review existing CRD ownership, RBAC, injection and Prometheus access first.
helm upgrade --install flagger flagger/flagger --version 1.45.0 \
  -n flagger-system --create-namespace -f flagger-values.yaml \
  --wait --timeout 10m
```

chart は crd.create を指定した場合に限って Flagger CRD を作成します。有効化する前に既存リソースの所有者を確認してください。コントローラー Pod はメッシュに参加し、Linkerd の認可設定では既存の Viz prometheus-admin Server とコントローラーの ServiceAccount を対象にします。外部の Prometheus を使う場合は、スクレイプ、ID、認証、認可を個別に設計してください。

### アプリケーションと分析の構成例

progressive-demo namespace に既存の Deployment web を準備します。宣言済みの 8080 HTTP ポート、動作確認済み readiness、テスト済みのイメージ、十分な容量が必要です。Canary を適用すると、デプロイと Service のライフサイクル管理を Flagger に委ねます。Flagger は primary Deployment と apex/primary/canary Service を作成し、分析の合間に元の対象 Deployment のレプリカ数を 0 にする場合があります。これは、前述の手動管理による stable/canary Deployment とは異なる構成です。

Service を親とする HTTPRoute を試すには、呼び出し元がメッシュに参加している必要があります。ルーティングの確認には、制御されたトラフィックを apex に送ってください。canary Service に直接負荷を送ると、そのバージョンの試験には使えますが、重み付き apex の判定を迂回します。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: progressive-demo
  annotations:
    linkerd.io/inject: enabled
---
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: web
  namespace: progressive-demo
spec:
  provider: gatewayapi:v1
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  progressDeadlineSeconds: 600
  service:
    port: 80
    targetPort: 8080
    gatewayRefs:
    - group: ''
      kind: Service
      name: web
      namespace: progressive-demo
      port: 80
  analysis:
    interval: 30s
    threshold: 5
    maxWeight: 50
    stepWeight: 10
    metrics:
    - name: linkerd-completed-responses
      templateRef:
        name: completed-responses
        namespace: progressive-demo
      thresholdRange:
        min: 20
      interval: 1m
    - name: linkerd-http-availability
      templateRef:
        name: http-availability
        namespace: progressive-demo
      thresholdRange:
        min: 99
        max: 100
      interval: 1m
    - name: linkerd-ttfb-p99-ms
      templateRef:
        name: ttfb-p99-ms
        namespace: progressive-demo
      thresholdRange:
        min: 0
        max: 500
      interval: 1m
```

gatewayRefs は意図的に Service を参照し、controller の v1 router はその親参照を保持します。生成された Route より優先される ServiceProfile を設定しないでください。同じ HTTPRoute を別のコントローラーや手動ループにも管理させないでください。

threshold:5 は確認失敗の打ち切り値、maxWeight:50 は分析中の canary トラフィックの上限、stepWeight:10 はパーセントポイント単位の増分です。5 回の成功が必要という意味でも、失敗を 50 回まで許す意味でもありません。記録された失敗がしきい値に達するか、別の失敗条件が成立すると、調整を通じてロールバックします。即時に戻る保証ではありません。


### Linkerd 用の明示的なメトリクステンプレート

Canary の分析を有効にする前に、これらの MetricTemplate を作成します。カスタムメトリクス名を使うことで、Gateway API router のこの設定とは別物である、プロバイダー組み込みの request-success-rate/request-duration observer との混同を避けます。

```yaml
apiVersion: flagger.app/v1beta1
kind: MetricTemplate
metadata:
  name: completed-responses
  namespace: progressive-demo
spec:
  provider:
    type: prometheus
    address: http://prometheus.linkerd-viz.svc.cluster.local:9090
  query: sum(increase(response_total{namespace="{{ namespace }}",deployment="{{ target }}",direction="inbound"}[{{
    interval }}]))
---
apiVersion: flagger.app/v1beta1
kind: MetricTemplate
metadata:
  name: http-availability
  namespace: progressive-demo
spec:
  provider:
    type: prometheus
    address: http://prometheus.linkerd-viz.svc.cluster.local:9090
  query: |-
    (100 * (sum(rate(response_total{namespace="{{ namespace }}",deployment="{{ target }}",direction="inbound",classification="success"}[{{ interval }}])) or vector(0)) / sum(rate(response_total{namespace="{{ namespace }}",deployment="{{ target }}",direction="inbound"}[{{ interval }}])))
    and on() (sum(rate(response_total{namespace="{{ namespace }}",deployment="{{ target }}",direction="inbound"}[{{ interval }}])) > 0)
---
apiVersion: flagger.app/v1beta1
kind: MetricTemplate
metadata:
  name: ttfb-p99-ms
  namespace: progressive-demo
spec:
  provider:
    type: prometheus
    address: http://prometheus.linkerd-viz.svc.cluster.local:9090
  query: |-
    histogram_quantile(0.99,
      sum by (le) (rate(response_latency_ms_bucket{namespace="{{ namespace }}",deployment="{{ target }}",direction="inbound"}[{{ interval }}]))
    )
```

このクエリは、Viz の scrape 設定が namespace/deployment ラベルを付与し、対象 Deployment に入って完了した応答を選択できることを前提としています。実際の Prometheus でラベルと系列を確認してください。複数クラスターで共有または federation されたバックエンドでは、適切なクラスター範囲の指定と重複排除が必要です。そうしないと、同名のワークロードが合算されます。

それぞれの確認項目は役割が異なります。

- completed-responses は、ルックバック期間内に完了した応答が少なくとも20件あることを求めます。increase はカウンターから推定した値で、監査ログの正確な件数ではありません。確定時の観測やエラーも含むカウンターであり、成功した業務操作数や一意のユーザー要求数ではありません。
- http-availability は、成功系列がなく全件失敗した期間には0を返します。合計が正であることも求めるため、トラフィックがない、または途切れている状態が正常率100%として通過することはありません。
- ttfb-p99-ms は response_latency_ms、すなわち Linkerd の Time to First Byte ヒストグラムを**ミリ秒**で使います。応答全体の所要時間ではありません。リリース済みのプロキシは最初に利用可能な応答本文フレームでレイテンシを記録し、本文が破棄された場合には fallback を使います。通常、ストリーム全体が完了するまで待ちません。最終応答の分類と件数計上は別処理であるため、ヒストグラムと応答カウンターのサンプルが同時に現れるとは限りません。

各クエリは 1 つの結果に集約されます。リリース済み Prometheus provider は空や NaN の結果を拒否します。availability と latency に明示的な下限・上限を設けることで、無限大の値もチェックを通過できません。1 つのクエリですべての種類の欠落・古い telemetry を検出できるわけではありません。鮮度、scrape の健全性、対象ラベル、サンプル期間も別途確認してください。

### トラフィック、フック、観測

分析を意味のあるものにするには、継続的で代表性のあるトラフィックが必要です。この例では負荷生成器やアプリケーションをインストールしません。ロールアウト前の任意の受け入れテストや、ロールアウト負荷テスト用 webhook を使うには、互換性のあるプライベートエンドポイントを別途デプロイし、認証とネットワークポリシー、実行上限、テストの意味を定義する必要があります。まだ作成していない Service の webhook URL を貼り付けないでください。

```bash
kubectl -n progressive-demo get canary web
kubectl -n progressive-demo describe canary web
kubectl -n progressive-demo get httproute web -o yaml
kubectl -n progressive-demo get deployments,services
kubectl -n flagger-system logs deployment/flagger --tail=200
kubectl -n progressive-demo get events \
  --field-selector involvedObject.kind=Canary
```

生成された web-primary/web-canary Service、apex HTTPRoute、稼働中のエンドポイント、コントローラーのイベント、実際のメトリクス値を確認してください。canary に直接送ったテストが成功しても、apex 経由の通信が意図した比率になる証明ではありません。

ロールバックによって以後のルーティングとデプロイ状態は変わりますが、すでに確定した書き込みを取り消したり、処理中の要求が停止したことを証明したりはできません。アプリケーションのデータや副作用を戻す手順は別途定義してください。

## 運用チェックリスト

- HTTPRoute を手動管理するのか、Flagger に任せるのか、従来の SMI コントローラーを使うのか、ルーティングの所有者を明確にします。
- HTTPRoute のアノテーションが無視されたように見える場合は、ServiceProfile の優先を確認します。
- 実際に安全な操作に限って再試行を有効にし、期限と追加試行の証拠を確認します。
- コントローラーが受理したポリシーと、メッシュ内クライアントから観測した結果の両方を検証します。
- エンドポイントの readiness、レイテンシ、生の失敗、最終結果、telemetry の可用性をまとめて監視します。
- 容量、負荷生成、アプリケーションイメージ、ロールバックの挙動は環境ごとの前提条件として扱います。この文書は、本番環境で試験済みであることを保証しません。

## 参考資料

- [Linkerd HTTPRoute リファレンス](https://linkerd.io/docs/reference/httproute/)
- [再試行](https://linkerd.io/docs/reference/retries/) と [タイムアウト](https://linkerd.io/docs/reference/timeouts/)
- [ServiceProfile](https://linkerd.io/docs/reference/service-profiles/)
- [サーキットブレーカー](https://linkerd.io/docs/reference/circuit-breaking/)
- [負荷分散](https://linkerd.io/docs/features/load-balancing/)
- [トラフィック分割と SMI の非推奨化](https://linkerd.io/docs/features/traffic-split/)
- [プロキシメトリクス](https://linkerd.io/docs/reference/proxy-metrics/)
- [リリース版における応答メトリクス計測の実装](https://github.com/linkerd/linkerd2-proxy/blob/a66af8117769df060adda6233302a2d1c4142229/linkerd/http/metrics/src/requests/service.rs)
- [Flagger 1.45.0 Gateway API router](https://github.com/fluxcd/flagger/blob/v1.45.0/pkg/router/gateway_api.go)
- [Flagger 1.45.0 provider の選択](https://github.com/fluxcd/flagger/blob/v1.45.0/pkg/router/factory.go)
- [Flagger 1.45.0 メトリクス評価](https://github.com/fluxcd/flagger/blob/v1.45.0/pkg/controller/scheduler_metrics.go)
- [トラフィック管理クイズ](../../quizzes/service-mesh/linkerd/traffic-management.md)
