# Argo Rollouts と Istio の統合

> **検証基準**: Argo Rollouts 1.10.1、Istio 1.31.0、Kubernetes 1.32～1.37
> **最終確認日**: 2026年10月16日
> **難易度**: 上級

Argo Rollouts は段階的デリバリー中にレプリカの選択と Istio のトラフィック重みを調整します。分析を行うには設定と信頼できる観測データが必要です。両方のコントローラーをインストールしただけでは、自動品質ゲートも可用性の保証も得られません。

## 目次

1. [概要](#overview)
2. [アーキテクチャ](#architecture)
3. [基本概念](#core-concepts)
4. [セットアップと設定](#setup-and-configuration)
5. [トラフィックルーティング戦略](#traffic-routing-strategies)
6. [分析とメトリクス](#analysis-and-metrics)
7. [高度なデプロイパターン](#advanced-deployment-patterns)
8. [トラブルシューティング](#troubleshooting)
9. [ベストプラクティス](#best-practices)

## 概要 {#overview}

Canary は対象トラフィックを段階的に移行し、blue/green はアクティブ Service のセレクターを切り替えます。設定した分析により、更新を続行させるか、中止（abort）するか、一時停止させるかを判断できます。トラフィックの伝播、readiness、追加容量、長時間接続、アプリケーションやデータの互換性が、引き続きユーザーに見える結果を左右します。

![手動で重みを変更する場合と、Analysis ステップを明示的に設定した Rollout の概念比較](../../../.gitbook/assets/en-service-mesh-istio-advanced-08-argo-rollouts-0.png)

[インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-advanced-08-argo-rollouts-0.html)

この図では分析が設定済みであることを前提とします。更新中に abort すると、管理対象のトラフィックを安定版へ戻せますが、Git 内のイメージ指定は元に戻りません。Argo Rollouts はほかのトラフィックルーターとも連携できますが、それぞれ実装と保守状況が異なります。

## アーキテクチャ {#architecture}

Argo CD/GitOps の利用は任意です。Rollouts コントローラーは Rollout/Analysis リソースを読み取り、設定された Service または DestinationRule の subset ラベルと VirtualService の重みを更新します。Istiod はこれらのリソースをプロキシ設定に変換します。リクエストは Envoy を通ってアプリケーションのエンドポイントへ進みます。VirtualService と DestinationRule は設定であり、ネットワーク上の中継点ではありません。

Prometheus は対象プロキシをスクレイプし、分析プロバイダーは Prometheus にクエリします。コントローラーは AnalysisRun のフェーズに応じて動作します。設定したメッシュプロキシまたはゲートウェイを通るトラフィックだけが Istio の分割に従います。メッシュ外のクライアントや Pod への直接接続、port-forward はこの経路を迂回することがあります。

## 基本概念 {#core-concepts}

### 1. Rollout リソース

Rollout は Canary または blue/green 戦略で ReplicaSet を管理します。これは Deployment とは別の API であり、`strategy: RollingUpdate` を付けた Deployment の別名ではありません。既存 Deployment の移行には、レビュー済みの移行または workloadRef の計画が必要です。同じ Pod を2つのコントローラーに管理させないでください。

### 2. VirtualService の所有権

Rollouts は指定された名前付きルートの重みを調整し、管理対象の experiment 宛先を追加・削除する場合があります。対応するルーティングフィールドを維持し、宛先配列全体を無条件に上書きするわけではありません。追加の subset 宛先には `additionalSubsetNames` と有効な合計重みが必要です。管理外の宛先が削除される場合があります。各管理ルートは1つの Rollout に割り当て、GitOps の所有権も調整してください。

### 3. ホスト単位と subset 単位のトラフィック分割

| 方式 | ユーザーが作成するリソース | Rollouts が調整するフィールド |
|---|---|---|
| メインラボで使うホスト単位 | Rollout、stable/canary Service、VirtualService | Service の hash セレクターと名前付きルートの重み |
| 代替方式の subset 単位 | Rollout、単一 Service、VirtualService、DestinationRule | stable/canary subset の hash ラベルと名前付きルートの重み |

仮の ReplicaSet hash を手作業で設定しないでください。ホスト単位の分割では、コントローラーが2つの Service セレクターに `rollouts-pod-template-hash` を追加します。subset 単位の分割では、設定した DestinationRule subset のラベルに hash を追加し、単一 Service はワークロード全体を選択したままにします。

以下は**ホスト単位のラボとは別の subset 単位の代替構成**です。この構成では Service と VirtualService の両方で `test` を使います。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: test
  namespace: rollouts-demo
spec:
  selector:
    app: test
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test-subsets
  namespace: rollouts-demo
spec:
  hosts:
  - test
  - test.rollouts-demo.svc.cluster.local
  http:
  - name: primary
    route:
    - destination:
        host: test
        port:
          number: 8080
        subset: stable
      weight: 100
    - destination:
        host: test
        port:
          number: 8080
        subset: canary
      weight: 0
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: test-subsets
  namespace: rollouts-demo
spec:
  host: test
  subsets:
  - name: stable
    labels:
      app: test
  - name: canary
    labels:
      app: test
```

メインの Rollout では Canary 戦略をこの断片に置き換え、実際のワークロードとテンプレートは維持します。この代替構成では、ホスト単位用の `stableService` と `canaryService` フィールドを省きます。

```yaml
spec:
  strategy:
    canary:
      trafficRouting:
        istio:
          virtualService:
            name: test-subsets
            routes:
            - primary
          destinationRule:
            name: test-subsets
            canarySubsetName: canary
            stableSubsetName: stable
      steps:
      - setWeight: 10
      - pause: {}
```

コントローラーが異なる hash を書き込むまでは、同一または空の2つの subset セレクターでリビジョンを分離できません。テストトラフィックを送る前に、調整後のラベルと readiness を確認してください。subset を使っても `destination_service_name` が自動的に分かれるわけではありません。この代替構成の分析では、リビジョンまたはワークロードのテレメトリを検証する必要があります。`destination_workload_label_rollouts_pod_template_hash` は**Istio の既定メトリクスラベルではありません**。

### 4. 分析結果

Prometheus はベクトルを返します。`result[0]` にアクセスする前に、要素数と値が有限であることを確認してください。`successCondition` だけを指定した場合、条件が false なら測定は失敗です。プロバイダーや式のエラーは別扱いです。成功条件と失敗条件の両方を指定し、どちらにも一致しなければ測定結果は判定不能です。

`failureLimit: 2` は2回の測定失敗を許容し、3回目に失敗します（`failed > failureLimit`）。したがって、この上限で `count: 5` を指定しても、5回すべての成功が必須になるわけではありません。メイン例では、データ欠落や非有限値も含めて `failureLimit: 0` とし、観測トラフィックの最小量も要求します。以下のしきい値やサンプル数は例示であり、統計的な信頼度や本番 SLO の保証ではありません。

## セットアップと設定 {#setup-and-configuration}

### 前提条件と対象範囲

対応する Rollouts コントローラー、CRD、CLI プラグイン、互換性のある Istio sidecar データプレーン、そして分析プロバイダーから DNS/RBAC/ネットワーク経由で利用できる Prometheus のスクレイプ設定を用意してください。[可観測性ガイド](../observability/README.md)と[インジェクションガイド](07-sidecar-injection.md)を参照してください。分析を有効にする前に、実際のメトリクスを検証します。

この独立した HTTP デモでは、digest で固定した公式 blue/green デモイメージを使います。検証済みイメージは **Linux amd64 専用**なので、Pod テンプレートでそのアーキテクチャを選択します。Arm64/Graviton では、別途検証した Arm64 またはマルチプラットフォームのアプリケーションイメージを用意してください。この監査ではクラスター、イメージランタイム、本番負荷、実際の Rollout をテストしていません。

この例では、新しい `rollouts-demo` namespace を作成し、既定/legacy の sidecar インジェクションを使います。revisioned インストールでは、リンク先ガイドのインジェクション規則を維持したうえで、インストール済みの revision/tag を選択してください。

### 1. Namespace と Rollout

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: rollouts-demo
  labels:
    istio-injection: enabled
---
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: test
  namespace: rollouts-demo
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: test
  template:
    metadata:
      labels:
        app: test
    spec:
      nodeSelector:
        kubernetes.io/os: linux
        kubernetes.io/arch: amd64
      terminationGracePeriodSeconds: 45
      containers:
      - name: app
        image: argoproj/rollouts-demo@sha256:3225193a6415b14b3fcdd160c40248b2bfd62f8c77326480559b91a41ced6e20
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /
            port: http
          initialDelaySeconds: 3
          periodSeconds: 5
          timeoutSeconds: 1
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
  strategy:
    canary:
      stableService: test-stable
      canaryService: test-canary
      maxSurge: 1
      maxUnavailable: 0
      trafficRouting:
        istio:
          virtualService:
            name: test
            routes:
            - primary
      steps:
      - setWeight: 10
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: success-rate
          args:
          - name: service-name
            value: test-canary
          - name: namespace
            value: rollouts-demo
      - setWeight: 50
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: success-rate
          args:
          - name: service-name
            value: test-canary
          - name: namespace
            value: rollouts-demo
      - setWeight: 80
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: success-rate
          args:
          - name: service-name
            value: test-canary
          - name: namespace
            value: rollouts-demo
```

イメージ、CPU/メモリー設定、レプリカ数はデモ用の入力値です。45秒の終了猶予は、デモで説明されているシャットダウン遅延を考慮したものです。実際の Rollout ではアプリケーション固有のライフサイクルを検証してください。この戦略では、メイン VirtualService ルートのメッシュ再試行を明示的に無効にし、ウォームアップの pause 後にインライン分析を実行します。

### 2. Stable/Canary Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: test-stable
  namespace: rollouts-demo
spec:
  selector:
    app: test
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-canary
  namespace: rollouts-demo
spec:
  selector:
    app: test
  ports:
  - name: http
    port: 8080
    targetPort: http
```

Rollouts は各 Service に追加する hash セレクターを所有します。stable Service が昇格後のリビジョンを選択できなくなるため、固定の `version: v1` セレクターを追加しないでください。

### 3. VirtualService

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test
  namespace: rollouts-demo
spec:
  hosts:
  - test-stable
  - test-stable.rollouts-demo.svc.cluster.local
  http:
  - name: primary
    route:
    - destination:
        host: test-stable
        port:
          number: 8080
      weight: 100
    - destination:
        host: test-canary
        port:
          number: 8080
      weight: 0
    retries:
      attempts: 0
```

これは**メッシュ内 HTTP ルーティング**であり、ingress Gateway は前提としていません。sidecar を注入したクライアントから `http://test-stable.rollouts-demo.svc.cluster.local:8080/color` へ継続的にテストトラフィックを送ります。Canary Service への直接アクセス、Pod の port-forward、非メッシュクライアントでは、重み付きルートを検証できません。

### 4. AnalysisTemplate とデータ契約

この例は `reporter="source"` と宛先 Service の namespace を使って、標準的な Service 単位のメトリクスをクエリします。このデータセットでは source proxy が一度だけスクレイプされ、実際のラベル値がセレクターと一致することを前提とします。

Rollout 全体を通して実際のテストトラフィックを流し続けてください。5分のウォームアップは2分の lookback より長く、最初のゲートに以前のセレクターのデータが混ざらないようにしています。最小量の検査はカウンター増加からの推定であり、統計的有意性の証明ではありません。トラフィック不足やテレメトリ欠落を黙って昇格につなげてはいけません。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
  namespace: rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
  - name: http-availability
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.95
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code!~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
```

可用性の計算は4xxも含め、5xx 以外かつゼロ以外の HTTP 応答を数えます。業務上の成功を証明するものではありません。これは HTTP デモであり、gRPC ステータスの SLO ではありません。スクレイプの重複、遅延、カウンターのリセット、重複する時間窓を考慮して結果を解釈してください。

### デプロイの手順

レビュー済みリソースを個別ファイルに保存し、Rollout より先に依存リソースを作成します。

```bash
kubectl argo rollouts lint -f rollout.yaml
kubectl apply -f namespace.yaml
kubectl apply -f analysis-templates.yaml -f services.yaml -f virtualservice.yaml
kubectl apply -f rollout.yaml

kubectl argo rollouts get rollout test -n rollouts-demo --watch
```

最初の作成で安定版リビジョンを確立します。テストトラフィックを流しながら、次のイメージ変更で Canary 戦略を試してください。GitOps 管理環境では、Git 内の desired image を変更します。以下の CLI コマンドはラボでの代替手順です。

```bash
kubectl argo rollouts set image test app=argoproj/rollouts-demo@sha256:e32df3d15f759d36c323b3dccb7003d38df1a4274d37217715151f085c24c58f -n rollouts-demo
kubectl argo rollouts get rollout test -n rollouts-demo --watch

# Choose the action appropriate to the observed state; do not run these as a sequence.
kubectl argo rollouts promote test -n rollouts-demo
kubectl argo rollouts abort test -n rollouts-demo
kubectl argo rollouts retry rollout test -n rollouts-demo
```

Promote は意図した pause を解除する操作であり、分析失敗の調査に代わるものではありません。Abort 後も desired Pod template は変更されません。特に別の GitOps コントローラーが値を戻す場合は、再試行や undo の前に desired version を調整してください。

## トラフィックルーティング戦略 {#traffic-routing-strategies}

このセクションの断片はすべて、メイン Canary 戦略の**代替案**です。既存の Service、トラフィックルーティング参照、ワークロードテンプレートと組み合わせてください。単独のリソースとして適用してはいけません。

### 1. 重み付き Canary

`setWeight` と `pause` は別々の step object にします。パーセンテージはルーティング目標であり、少数のサンプルで正確な比率になるわけではありません。セッションアフィニティや長時間リクエストも、観測される分布に影響します。

![Canary の重み目標と pause の例。実際の経過時間は readiness と分析結果によって決まります](../../../.gitbook/assets/en-service-mesh-istio-advanced-08-argo-rollouts-4.png)

[インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-advanced-08-argo-rollouts-4.html)

### 2. 管理対象ヘッダールーティング

`managedRoutes`/`setHeaderRoute` を使うと、Rollouts が生成ルートの順序と削除を管理できます。ヘッダーのみの段階に入る前に Canary レプリカを用意し、トラフィック重みによるスケーリングへ戻す前にその状態を確保してください。

```yaml
spec:
  strategy:
    canary:
      trafficRouting:
        managedRoutes:
        - name: beta-header
        istio:
          virtualService:
            name: test
            routes:
            - primary
      steps:
      - setCanaryScale:
          replicas: 1
      - setWeight: 0
      - setHeaderRoute:
          name: beta-header
          match:
          - headerName: x-beta-user
            headerValue:
              exact: 'true'
      - pause:
          duration: 5m
      - setHeaderRoute:
          name: beta-header
      - setCanaryScale:
          matchTrafficWeight: true
      - setWeight: 10
      - pause: {}
```

Release 1.10 はこのヘッダールートに primary route の再試行ポリシーをコピーしません。この断片は冪等なデモリクエストに限って使い、生成されたルートを確認してください。読み取り専用メソッドを強制するものでも、書き込みが再試行されないことを保証するものでもありません。書き込みを受け付けるデプロイでは、再試行と認可を別途制御・検証する設計が必要です。

`x-beta-user` ヘッダーは、認証済みテスターの識別情報ではありません。公開範囲を制限する必要がある場合は、信頼できる認証境界を使ってください。Rollouts の managed-route リスト外で手動作成したヘッダールートは、abort/完了時に自動削除されず、Canary endpoint へ到達し続ける可能性があります。

### 3. 管理対象ミラートラフィック

この例は GET リクエストだけをミラーし、shadow 段階ではユーザーへの応答を stable ルートに維持します。通常の Canary トラフィックへ移る前にミラーを削除します。

```yaml
spec:
  strategy:
    canary:
      trafficRouting:
        managedRoutes:
        - name: shadow-read
        istio:
          virtualService:
            name: test
            routes:
            - primary
      steps:
      - setCanaryScale:
          replicas: 1
      - setWeight: 0
      - setMirrorRoute:
          name: shadow-read
          percentage: 10
          match:
          - method:
              exact: GET
      - pause:
          duration: 5m
      - setMirrorRoute:
          name: shadow-read
      - setCanaryScale:
          matchTrafficWeight: true
      - setWeight: 10
      - pause: {}
```

生成されたミラールートにも primary の再試行ポリシーは引き継がれません。実効メッシュ既定値を確認してください。ミラー応答は破棄されますが、リクエスト処理自体は実行されます。GET でもアプリケーションに副作用を起こす場合があるため、必要に応じてセマンティクスを検証し、データや依存先を分離します。ミラーはリソース/ネットワーク負荷を増やし、ユーザーへの影響がゼロとは限りません。実際の mirror Host の動作とアプリケーションの受け入れを確認してください。

### 4. 複数の名前付きルート

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test
  namespace: rollouts-demo
spec:
  hosts:
  - test-stable
  - test-stable.rollouts-demo.svc.cluster.local
  http:
  - name: api-route
    match:
    - uri:
        exact: /api
    - uri:
        prefix: /api/
    route:
    - destination:
        host: test-stable
        port:
          number: 8080
      weight: 100
    - destination:
        host: test-canary
        port:
          number: 8080
      weight: 0
    retries:
      attempts: 0
  - name: web-route
    match:
    - uri:
        exact: /web
    - uri:
        prefix: /web/
    route:
    - destination:
        host: test-stable
        port:
          number: 8080
      weight: 100
    - destination:
        host: test-canary
        port:
          number: 8080
      weight: 0
    retries:
      attempts: 0
---
spec:
  strategy:
    canary:
      trafficRouting:
        istio:
          virtualService:
            name: test
            routes:
            - api-route
            - web-route
      steps:
      - setWeight: 10
      - pause: {}
```

2つの名前付きルートには同じ Canary 重みが設定されます。境界条件によって `/api` と `/api/…` を無関係な prefix から個別に保護します。これらのパス外のリクエストには、明示的なルート設計が必要です。

## 分析とメトリクス {#analysis-and-metrics}

上流の過去のスクリーンショットは、Service 単位の分離を示すものであり、統合アーキテクチャや現在のベンチマークを示すものではありません。

![stable と Canary の Service メトリクスを示す過去の Istio Service ダッシュボード](https://raw.githubusercontent.com/argoproj/argo-rollouts/v1.10.1/docs/features/traffic-management/istio-service-metrics.png)

### 1. インライン分析

メイン Rollout は `success-rate` をインライン step として実行し、完了を待ちます。呼び出しごとに必須の引数を両方渡します。失敗した run は abort し、判定不能の run は pause できます。分析プロバイダーは、存在しないアプリケーショントラフィックを作り出したり、誤ったメトリクスセレクターを修正したりはできません。

### 2. 継続的なバックグラウンド分析

`count: 5` を設定したバックグラウンドテンプレートは、有限回の測定後に停止します。継続的なバックグラウンドゲートにするには count を省略します。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate-continuous
  namespace: rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
  - name: http-availability
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.95
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code!~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
---
spec:
  strategy:
    canary:
      analysis:
        templates:
        - templateName: success-rate-continuous
        startingStep: 2
        args:
        - name: service-name
          value: test-canary
        - name: namespace
          value: rollouts-demo
      steps:
      - setWeight: 10
      - pause:
          duration: 5m
      - setWeight: 30
      - pause:
          duration: 5m
      - setWeight: 50
      - pause: {}
```

`startingStep: 2` は0始まりで、この断片では3番目の step（`setWeight: 30`）を指します。その前の pause で2分のデータ窓をウォームアップします。Rollout による終了または完了、あるいは失敗条件まで、後続 step と並行して分析を続けます。これはエンドツーエンドの即時ロールバックを保証しません。

### 3. 複合メトリクス

このより厳格な代替案では、リクエスト量、99% 以上の5xx以外かつゼロ以外の可用性、0.5秒以下の p95、1% 以下のエラー率を要求します。ここでは可用性検査とエラー率検査を組み合わせていますが、サンプル値はワークロードに応じた根拠が必要です。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: comprehensive-analysis
  namespace: rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
  - name: http-availability
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.99
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code!~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
  - name: latency-p95
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.5
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          histogram_quantile(0.95,
            sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
          ) / 1000
    count: 5
  - name: http-error-rate
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.01
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
```

Istio の duration histogram はミリ秒単位なので、秒と比較する前にクエリで1000で割ります。instant-vector の結果は、空、複数要素、NaN/Inf の値を検査します。重複する lookback は独立した統計サンプルにはなりません。

### 4. Pre/Post 検査

Canary に指定できる background `analysis` フィールドは1つです。同じ YAML object に `analysis` キーを2つ書いても pre/post 検査にはなりません。適切なトラフィックと事前条件を用意し、意図した地点に inline analysis step を置くか、以下の blue/green 用 `prePromotionAnalysis` および `postPromotionAnalysis` hook を使います。

## 高度なデプロイパターン {#advanced-deployment-patterns}

### 1. Blue/Green

これは**独立した戦略のひな型**です。レビュー済みのワークロードテンプレートを再利用し、Canary 戦略とクライアント向け Service 参照を置き換えます。実行前に active と preview の両 Service を作成してください。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: test-active
  namespace: rollouts-demo
spec:
  selector:
    app: test
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-preview
  namespace: rollouts-demo
spec:
  selector:
    app: test
  ports:
  - name: http
    port: 8080
    targetPort: http
---
spec:
  strategy:
    blueGreen:
      activeService: test-active
      previewService: test-preview
      autoPromotionEnabled: false
      prePromotionAnalysis:
        templates:
        - templateName: smoke-test
        args:
        - name: service-name
          value: test-preview
        - name: namespace
          value: rollouts-demo
      postPromotionAnalysis:
        templates:
        - templateName: post-promotion-analysis
        args:
        - name: service-name
          value: test-active
        - name: namespace
          value: rollouts-demo
      scaleDownDelaySeconds: 600
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test-bluegreen
  namespace: rollouts-demo
spec:
  hosts:
  - test-active
  - test-active.rollouts-demo.svc.cluster.local
  http:
  - name: active
    route:
    - destination:
        host: test-active
        port:
          number: 8080
      weight: 100
    retries:
      attempts: 0
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: post-promotion-analysis
  namespace: rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
  - name: http-availability
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.99
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code!~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
  - name: latency-p95
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.5
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          histogram_quantile(0.95,
            sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
          ) / 1000
    count: 5
    initialDelay: 5m
  - name: http-error-rate
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.01
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
    initialDelay: 5m
```

アプリケーション側で用意する `smoke-test` AnalysisTemplate は、実装と検証が必要な前提条件であり、このガイドには含まれません。`service-name`/`namespace` 引数を宣言し、適切な ID、ネットワークアクセス、機能検査を使って preview リビジョンをテストしてください。promotion 後のテンプレートは5分待ってから2分間の窓をクエリします。伝播や `test-active` への継続的なトラフィックを確認し、既存接続やデータがすぐ消えると決めつけないでください。この断片を、動作確認済みの smoke-test デプロイ全体としてコピーしないでください。

`autoPromotionEnabled` の既定値は true ですが、この例では明示的に無効化しています。`scaleDownDelaySeconds` は古い ReplicaSet のスケールダウンを遅らせます。リビジョン履歴をすべて削除したり、既存接続を移行したりする設定ではありません。Service/endpoint の伝播や上流ロードバランサーの動作によっては、停止が発生することがあります。

![blue/green preview、promotion、post-analysis、旧リビジョンのスケールダウンを条件付きで行うフロー](../../../.gitbook/assets/en-service-mesh-istio-advanced-08-argo-rollouts-6.png)

[インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-advanced-08-argo-rollouts-6.html)

### 2. 重み付き Experiment

Istio はトラフィックルーティングされた experiment をサポートします。ここで有効な `specRef` は `stable` と `canary` です。`experimental` というソースリビジョンはありません。

```yaml
spec:
  strategy:
    canary:
      steps:
      - experiment:
          duration: 10m
          templates:
          - name: baseline
            specRef: stable
            weight: 5
          - name: candidate
            specRef: canary
            weight: 5
      - setWeight: 10
      - pause: {}
```

最初の experiment step では、コントローラーが experiment の ReplicaSet/Service を作成し、stable の宛先を90%に保ちながら、それぞれに5%を振り分けます。Experiment Pod の hash は親 Rollout の hash と異なります。この断片は10分間の公開をスケジュールするものであり、それだけで統計的に妥当な比較を行うわけではありません。実際の比較用 AnalysisTemplate を追加し、experiment が生成する固有の識別子/Service を引数に使ってください。

### 3. 時間をかけた段階的 Rollout

```yaml
spec:
  strategy:
    canary:
      steps:
      - setWeight: 1
      - pause:
          duration: 1h
      - setWeight: 5
      - pause:
          duration: 1h
      - setWeight: 10
      - pause:
          duration: 2h
      - setWeight: 25
      - pause:
          duration: 4h
      - setWeight: 50
      - pause:
          duration: 8h
      - setWeight: 75
      - pause:
          duration: 8h
      analysis:
        templates:
        - templateName: success-rate-continuous
        startingStep: 2
        args:
        - name: service-name
          value: test-canary
        - name: namespace
          value: rollouts-demo
```

指定された pause の合計は24時間で、これに readiness、分析、伝播の時間が加わります。長いスケジュールだけでは、代表的なトラフィック、障害検知、容量、レビュー済みの復旧手順を代替できません。

## トラブルシューティング {#troubleshooting}

namespace 内のリソースと実際のプロキシ経路を確認します。

```bash
kubectl argo rollouts get rollout test -n rollouts-demo
kubectl describe rollout test -n rollouts-demo
kubectl get virtualservice test -n rollouts-demo -o yaml
kubectl get services test-stable test-canary -n rollouts-demo -o yaml
kubectl get pods -n rollouts-demo -l app=test --show-labels
kubectl get endpointslices -n rollouts-demo -l kubernetes.io/service-name=test-canary
istioctl proxy-config routes <client-pod> -n rollouts-demo
istioctl proxy-config clusters <client-pod> -n rollouts-demo
kubectl get analysisruns -n rollouts-demo
kubectl logs -n argo-rollouts deployment/argo-rollouts
```

重みが更新されない場合は、RBAC、参照されるルート名、コントローラーイベント、競合する GitOps 更新を調べてください。Canary にトラフィックが届かない場合は、Service/subset の hash セレクター、ready な EndpointSlice、実際のメッシュクライアント/Gateway 経路、サンプル量を確認します。

分析に失敗した場合は、AnalysisRun の測定値とメッセージを調べ、同じ Prometheus datasource に同じクエリを実行します。source reporter、namespace/Service ラベル、トラフィック量、lookback、プロバイダーの認証/ネットワークアクセスを検証してください。しきい値による失敗、判定不能、プロバイダーエラーを区別します。

Rollout の完了後、abort は履歴全体を戻す一般的なコマンドではありません。履歴を確認し、意図したテンプレート/バージョンを復元します。

```bash
kubectl argo rollouts get rollout test -n rollouts-demo
kubectl argo rollouts undo test --to-revision=<reviewed-revision> -n rollouts-demo
```

GitOps を使っている場合は、Git の desired version も変更・同期してください。保持された ReplicaSet とデータベース/API の互換性によって、安全に undo できる範囲が決まります。

## ベストプラクティス {#best-practices}

### GitOps のフィールド所有権

Argo CD Application では、Rollouts が所有する runtime field だけを sync 時にも尊重される除外設定にできます。

```yaml
spec:
  ignoreDifferences:
  - group: networking.istio.io
    kind: VirtualService
    name: test
    namespace: rollouts-demo
    jqPathExpressions:
    - .spec.http[] | select(.name == "primary") | .route[].weight
  - group: ''
    kind: Service
    name: test-stable
    namespace: rollouts-demo
    jqPathExpressions:
    - .spec.selector["rollouts-pod-template-hash"]
  - group: ''
    kind: Service
    name: test-canary
    namespace: rollouts-demo
    jqPathExpressions:
    - .spec.selector["rollouts-pod-template-hash"]
  syncPolicy:
    syncOptions:
    - RespectIgnoreDifferences=true
```

これは Application の `spec` 断片であり、単独で使える Application リソースではありません。最初のリソース作成では、重み/セレクターを正しく設定する必要があります。subset ルーティングでは、管理対象 DestinationRule subset の hash ラベルも除外範囲にします。managed header/mirror route では、固有名の runtime entry も考慮してください。VirtualService の spec 全体を無視しないでください。hosts、宛先、セキュリティに関わるルーティングはレビュー可能な状態にします。

### Step、測定、容量

割合と pause の長さは、リクエスト量、リスク、復旧時間をもとに決めます。最低30秒、5サンプルで信頼できる、最後の段階は素早く昇格すべき、といった普遍的な規則はありません。CanaryStep では1つの操作に絞り、再試行とスキーマ/データ互換性を調整します。

```yaml
spec:
  revisionHistoryLimit: 2
  progressDeadlineSeconds: 600
  progressDeadlineAbort: false
  template:
    spec:
      containers:
      - name: app
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
```

`revisionHistoryLimit` は履歴の保持設定であり、常に最低2を必要とするわけではありません。`progressDeadlineSeconds` は進行がない状態に関する設定です。pause と分析のライフサイクルは別に理解してください。明示的に false にした `progressDeadlineAbort` は、progress deadline 到達時に自動 abort しません。リクエスト/limit 比率の2倍は、元の例に入っていた値にすぎません。

レプリカが3つあっても、各 AZ に1つずつ配置されるとは限りません。ゾーン分散が必要なら、レビュー済みの topology 制約と容量を使ってください。[Zone-Aware Argo Rollouts](09-zone-aware-argo-rollouts.md)を参照してください。トラフィックルーティングには、単純な surge 見積もりを超える stable/canary 容量が必要になる場合があります。PDB が影響するのは自発的な退避であり、すべての障害やコントローラーによるスケーリングではありません。

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: test-pdb
  namespace: rollouts-demo
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: test
```

更新前に、コントローラー/CRD、インジェクション、DNS、イメージのプラットフォーム、Service/route、プロバイダーアクセス、メトリクスラベル、継続的なテストトラフィックを確認してください。更新中は、実際の endpoint 選択と AnalysisRun の結果を調べます。promotion 後は、desired image、管理対象の重み、endpoint readiness、古い ReplicaSet のスケール/保持動作を確認し、古い ReplicaSet がすべて削除されると期待しないでください。

## 参考資料

- [Argo Rollouts Istio 統合](https://argoproj.github.io/argo-rollouts/features/traffic-management/istio/)
- [分析のライフサイクル](https://argoproj.github.io/argo-rollouts/features/analysis/)
- [Prometheus プロバイダー](https://argoproj.github.io/argo-rollouts/analysis/prometheus/)
- [トラフィックルーティングと managed route](https://argoproj.github.io/argo-rollouts/features/traffic-management/)
- [Blue/green](https://argoproj.github.io/argo-rollouts/features/bluegreen/)
- [Experiment](https://argoproj.github.io/argo-rollouts/features/experiment/)
- [Rollout 仕様](https://argoproj.github.io/argo-rollouts/features/specification/)
- [Rollouts FAQ](https://argoproj.github.io/argo-rollouts/FAQ/)
- [Release 1.10 の Istio reconciler](https://raw.githubusercontent.com/argoproj/argo-rollouts/v1.10.1/rollout/trafficrouting/istio/istio.go)
- [Release 1.10 の分析失敗判定](https://raw.githubusercontent.com/argoproj/argo-rollouts/v1.10.1/analysis/analysis.go)
- [Argo CD sync options のソース](https://raw.githubusercontent.com/argoproj/argo-cd/master/docs/user-guide/sync-options.md)
- [トラフィック分割](../traffic-management/04-traffic-splitting.md)
- [VirtualService](../traffic-management/01-gateway-virtualservice.md)
- [DestinationRule](../traffic-management/03-destination-rule.md)
