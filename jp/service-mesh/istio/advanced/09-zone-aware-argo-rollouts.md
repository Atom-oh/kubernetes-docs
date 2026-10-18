# ゾーン単位の Argo Rollouts

> **検証対象の基準**: Istio 1.31.0、Argo Rollouts 1.10.1、Kubernetes 1.32–1.37
> **最終レビュー**: 2026年10月16日
> **難易度**: 上級

このガイドでは、各ゾーンで独立した Canary を運用する方法と、AZ をまたぐフェイルオーバーを分けて説明します。主な例は**ゾーン単位のルーティング／分離を行う設計図**です。クライアント群に応じて、1つのゾーンにある stable／canary Service を選択します。対象 endpoint がなくなったときに、別のゾーンへ自動フェイルオーバーする構成ではありません。

## 目次

1. [問題の定義](#problem-definition)
2. [アーキテクチャの概要](#architecture-overview)
3. [主な設計判断](#key-design-decisions)
4. [実装ガイド](#implementation-guide)
5. [トラフィックフロー](#traffic-flow)
6. [トラブルシューティング](#troubleshooting)
7. [ベストプラクティス](#best-practices)

## 問題の定義 {#problem-definition}

### Spot 中断と PDB

Spot capacity は回収される場合があり、複数 AZ で連動してキャパシティが失われる事態も想定する必要があります。中断通知はベストエフォートです。停止／終了通知では通常2分前に通知されますが、休止は直ちに始まります。EKS managed node group は代替 node の起動や rebalance を試みますが、中断された node の drain 前に代替 node が Ready になるとは限りません。

PodDisruptionBudget（PDB）が制限するのは、voluntary Eviction API 操作です。EC2 interruption、node failure、Pod の直接削除、controller が行うすべての更新を防ぐものではありません。Argo Rollouts は以下の PDB を作成・管理しません。PDB はアプリケーションチームが定義し、Kubernetes が status を計算します。

条件に一致する正常な Pod が9個あり、**整数の `minAvailable: 6`** を設定すると、自発的な退避を3 Pod 分許容します。正常な Pod が6個だけなら、許容数は0です。ここで6 Podを要求しているのは整数値の `minAvailable` であり、33%が6 Podに相当するという意味ではありません。expected Pod が9個のとき `minAvailable: "33%"` は3へ切り上げられます。percentage の `maxUnavailable` は意味が異なり、controller の replica 数にも依存します。

全体共通の disruption budget を、ゾーンごとの `minAvailable: 1` に分割すると保護内容が変わります。1つのゾーンを失うと、残る2つの budget は、それぞれのゾーンで正常な Pod が1つ残るまで自発的な退避を許す可能性があります。つまり、全体で6 Podを維持する構成ではありません。独立運用に役立つ場合はありますが、可用性と必要キャパシティに関する別の policy です。stable と canary の両方を選択する PDB でも、weight で選ばれる各 destination の capacity は保証されません。

### 目標と制約

| 設計 | ゾーンごとの独立した version | AZ 間 failover | 主な制約 |
|---|---|---|---|
| AZ をまたぐ endpoint を持つ共有 revision／subset | ゾーンごとの revision を独立制御できない | 選択された endpoint pool 内では可能 | 他 AZ における healthy capacity と互換性のある release／data state |
| ゾーンごとの Rollout と zone-filtered Service（本例） | 可能 | locality 設定だけでは提供されない | 選択ゾーンの pool が空なら空のまま |
| zonal gateway／pipeline より手前で health-aware な入口ルーティング | 設計可能 | 独自の policy／controller と test が必要 | routing、capacity、identity、復旧の調整が追加される |

DestinationRule を追加しただけで「厳密な zonal filtering」「ゾーンごとの独立 hash」「透過的な failover」の3つを同時に実現できると主張しないでください。別途入口 routing を設計する方法は、この blueprint の範囲外であり、本番 test も行っていません。

## アーキテクチャの概要 {#architecture-overview}

共通の `test` Service が DNS 名を提供します。sidecar を注入した client では、VirtualService が**明示的な client Pod label**に基づきゾーン別 route を選びます。各 route はそのゾーンの stable／canary Service を参照します。個別の Rollout が、その Service pair の hash と、自分が所有する名前付き route の weight を管理します。

Istiod は設定を Envoy 用にコンパイルします。VirtualService／DestinationRule object 自体は network hop ではありません。mesh 外の client は共通 Service の通常の Kubernetes endpoint 選択を使い、これらの route rule を迂回することがあります。routing 用 label は security boundary ではありません。

各ゾーンの Pod は、設定した AZ 内だけに配置されます。そのため zone A の Service に zone B／C の fallback endpoint は含まれません。deployment state を分離しても、共有 control plane、API server、network、database への依存はなくなりません。

## 主な設計判断 {#key-design-decisions}

### 1. Route の所有権

Argo Rollouts 1.10 は設定された route weight と、サポート対象で管理下にある destination を reconcile します。destination array を常に丸ごと置き換える動作ではありません。route 名を分ければ、desired weight の競合を避けられます。ただし、3つの controller が1つの VirtualService を更新すると、Kubernetes `resourceVersion` の競合や reconcile の遅延は起こり得ます。control plane をさらに分離する必要があれば、別 object／入口 routing も選択肢です。

この blueprint は別々の route（`zone-a-route`、`zone-b-route`、`zone-c-route`）と**host-level splitting**を使います。Service hash と DestinationRule subset の所有権を混在させません。両方の方式については[統合ガイド](08-argo-rollouts.md)を参照してください。

### 2. Client label と実際の AZ

`sourceLabels` は Istiod が mesh configuration を作る際に source workload を選択するもので、実行時の request-header match ではありません。`topology.kubernetes.io/zone` などの Node label が Pod に自動コピーされることもありません。独自の Pod label `routing.example.com/zone: a` は、対象 AZ に実際に配置されていることの確認と組み合わせる必要があります。

これらの selector が対象にするのは mesh client であり、ingress gateway に到着する一般的な外部 request ではありません。gateway scope の `mesh` を維持してください。この例では未知の client cohort に別 zone を黙って選ばせず、明示的に503を返します。

### 3. Locality で選択済み pool の外へは移動できない

`zone: a` の subset と Rollout A の hash は、隣の zone B の subset へ failover できません。zone で絞り込んだ Service も同様です。outlier detection が変えるのは選択済み upstream pool 内の endpoint eligibility だけで、別の VirtualService route へ移ることはありません。

また、`localityLbSetting.distribute`、`failover`、`failoverPriority` は代替となる設定で、自由に組み合わせる field ではありません。`failover.from/to` の値は**region**であり、`region/zone` 文字列ではありません。これらの項目だけで A→B→C→A の AZ cycle が成立するわけではありません。

## 実装ガイド {#implementation-guide}

### 前提条件

[Argo Rollouts 統合ガイド](08-argo-rollouts.md)にある controller、CLI、sidecar injection、Prometheus、workload の前提条件を使います。ここでは default／legacy injection を使う独立した sidecar HTTP demo を扱います。revisioned mesh では、インストール済み revision／tag を使ってください。この lab には互換性のある EC2-backed Linux worker node、quota、network、image access、observability が必要です。Fargate は対象外です。Istio の互換性範囲内にある、現在サポートされている EKS version を選んでください。

例にある AZ 名 `us-east-1a/b/c` は、実際の node label に置き換えます。account ごとに AZ 名の対応は異なる場合があります。複数 account 間で物理 zone を合わせる場合は AZ ID を確認してください。固定された demo image は Linux amd64 専用なので、選択する各 AZ に互換性のある node を用意するか、置き換える image を別途検証してください。

```bash
kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone,kubernetes.io/arch
```

### 1. Namespace と共通／ゾーン別 Service

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: zone-rollouts-demo
  labels:
    istio-injection: enabled
---
apiVersion: v1
kind: Service
metadata:
  name: test
  namespace: zone-rollouts-demo
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
  name: test-stable-a
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: a
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-canary-a
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: a
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-stable-b
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: b
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-canary-b
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: b
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-stable-c
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: c
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-canary-c
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: c
  ports:
  - name: http
    port: 8080
    targetPort: http
```

共通 Service は mesh caller 向けの DNS entry であり、authorization mechanism ではありません。6つの zone Service には実際の Pod `zone` selector があり、Argo Rollouts がそれぞれに stable／canary hash を追加します。

### 2. Client template の契約

既存の **`zone-client-a` という名前の Deployment** にこの設定を merge してください。selector、container、検証済み image、resource、その他の配置制約は維持します。`a` route label は Deployment metadata だけでなく、実際の Pod template に追加してください。

```yaml
metadata:
  name: zone-client-a
  namespace: zone-rollouts-demo
spec:
  template:
    metadata:
      labels:
        routing.example.com/zone: a
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1a
```

B／C client を test する場合は、対応する label と実際の AZ 制約を使って用意します。既存の rule と affinity を組み合わせるときは、意図した AND／OR 制約を保ち、node の選択範囲を誤って広げないでください。`.spec.nodeName` と、選択した Node の zone を照合します。この設定断片は client を deploy したり、Node metadata を自動コピーしたりしません。

### 3. 独立した route を持つ共有 VirtualService

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test
  namespace: zone-rollouts-demo
spec:
  hosts:
  - test
  - test.zone-rollouts-demo.svc.cluster.local
  gateways:
  - mesh
  http:
  - name: zone-a-route
    match:
    - sourceLabels:
        routing.example.com/zone: a
    route:
    - destination:
        host: test-stable-a
        port:
          number: 8080
      weight: 100
    - destination:
        host: test-canary-a
        port:
          number: 8080
      weight: 0
    retries:
      attempts: 0
  - name: zone-b-route
    match:
    - sourceLabels:
        routing.example.com/zone: b
    route:
    - destination:
        host: test-stable-b
        port:
          number: 8080
      weight: 100
    - destination:
        host: test-canary-b
        port:
          number: 8080
      weight: 0
    retries:
      attempts: 0
  - name: zone-c-route
    match:
    - sourceLabels:
        routing.example.com/zone: c
    route:
    - destination:
        host: test-stable-c
        port:
          number: 8080
      weight: 100
    - destination:
        host: test-canary-c
        port:
          number: 8080
      weight: 0
    retries:
      attempts: 0
  - name: unclassified-client
    directResponse:
      status: 503
      body:
        string: No reviewed client-zone route
```

test traffic を流す前に、各 controller が意図した hash と healthy endpoint を選択したことを確認します。初期 weight は100/0です。根拠のない稼働中の90/10 split ではありません。各名前付き route では mesh retry を明示的に無効化します。application 側の retry 動作は別の設定です。

### 4. ゾーンごとの Rollout

workload、replica 数、requests／limits、pause は demo 用の入力です。replica が3つでも、3 node に自動的に分散されるとは限りません。本番構成では node-level spread／anti-affinity、capacity、PDB、stable／canary の余力を確認します。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: test-a
  namespace: zone-rollouts-demo
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: test
      zone: a
  template:
    metadata:
      labels:
        app: test
        zone: a
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
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1a
  strategy:
    canary:
      stableService: test-stable-a
      canaryService: test-canary-a
      maxSurge: 1
      maxUnavailable: 0
      trafficRouting:
        istio:
          virtualService:
            name: test
            routes:
            - zone-a-route
      steps:
      - setWeight: 5
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-a
          - name: namespace
            value: zone-rollouts-demo
      - pause: {}
      - setWeight: 25
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-a
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 50
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-a
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 75
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-a
          - name: namespace
            value: zone-rollouts-demo
---
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: test-b
  namespace: zone-rollouts-demo
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: test
      zone: b
  template:
    metadata:
      labels:
        app: test
        zone: b
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
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1b
  strategy:
    canary:
      stableService: test-stable-b
      canaryService: test-canary-b
      maxSurge: 1
      maxUnavailable: 0
      trafficRouting:
        istio:
          virtualService:
            name: test
            routes:
            - zone-b-route
      steps:
      - setWeight: 5
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-b
          - name: namespace
            value: zone-rollouts-demo
      - pause: {}
      - setWeight: 25
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-b
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 50
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-b
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 75
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-b
          - name: namespace
            value: zone-rollouts-demo
---
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: test-c
  namespace: zone-rollouts-demo
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: test
      zone: c
  template:
    metadata:
      labels:
        app: test
        zone: c
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
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1c
  strategy:
    canary:
      stableService: test-stable-c
      canaryService: test-canary-c
      maxSurge: 1
      maxUnavailable: 0
      trafficRouting:
        istio:
          virtualService:
            name: test
            routes:
            - zone-c-route
      steps:
      - setWeight: 5
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-c
          - name: namespace
            value: zone-rollouts-demo
      - pause: {}
      - setWeight: 25
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-c
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 50
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-c
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 75
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-c
          - name: namespace
            value: zone-rollouts-demo
```

各 Rollout はそれぞれの selector、image／revision state、Service、analysis argument を持ちます。最初の5% gate の後にある無期限 pause は、意図して promotion する必要があります。hard zone affinity の場合、その AZ に capacity がなければ対象 Pod は Pending のままです。healthy な AZ へ移動することはありません。

### 5. 明示的な PDB

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: test-a-pdb
  namespace: zone-rollouts-demo
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: test
      zone: a
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: test-b-pdb
  namespace: zone-rollouts-demo
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: test
      zone: b
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: test-c-pdb
  namespace: zone-rollouts-demo
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: test
      zone: c
```

これらは、前述したゾーンごとに Pod を1つ確保する例を表す PDB です。先に示した全体の minimum 6と同等ではなく、traffic weight ごとに選択される各 revision の Pod 数も保護しません。voluntary maintenance の前に `currentHealthy`、`desiredHealthy`、`disruptionsAllowed` を確認してください。

### 6. ゾーン別 Analysis

Rollout より先に、この template を作成します。実際の zonal canary Service 名と、架空の Pod-zone label ではなく標準の source-reporter metric を使います。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: zone-canary-check
  namespace: zone-rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 1m
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
  - name: http-2xx-rate
    interval: 1m
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.95
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"2.."}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
```

分子は、このガイドで成功と定義する**HTTP 2xx**です。5xx だけの window は分子0となり、empty numerator にはなりません。traffic がない場合や data がない場合は、finite-value／volume gate を通過できません。source proxy と provider から設定した Prometheus に到達でき、実際の label が selector と一致する必要があります。

`http://test.zone-rollouts-demo.svc.cluster.local:8080/color` に対して、mesh 内の代表的な traffic を継続して流してください。caller label がゾーンを選び、controller がそのゾーンの stable／canary weight を選びます。5分間の warm-up は2分の metric lookback より長くしています。20 request の推定値と測定回数は例示であり、統計的な信頼度を示すものではありません。

## トラフィックフロー {#traffic-flow}

### 通常時のゾーン内経路

正しい label が付いた client A を確認済みの AZ に配置すると、`zone-a-route` が選択され、A の stable／canary Service に接続します。観測される比率は sample 数、session、readiness によって変わり、10 request ごとの正確な比率を保証するものではありません。

### Zone loss

eligible な A endpoint がすべてなくなると、A route に healthy upstream はありません。outlier threshold を下げたり PDB を変更したりしても、B endpoint が A Service に作られるわけではありません。この例では capacity が戻るか、明示的に設計された上位の routing policy が変わるまで failure が返ります。

AZ 間で継続性を確保するには、同じ選択済み release pool に healthy な remote endpoint がある構成を選ぶか、別途入口レイヤーの failover policy を実装して test します。remote capacity、data consistency、authentication、処理中 request、failback を考慮してください。上記の zonal code は透過的または循環する failover を提供しません。

### 共有 endpoint を使う locality の別案

次は**別の構成**で使う設定です。すでに存在する `shared-app` Service または AZ をまたいで endpoint を持ち、release state に互換性がある subset を前提とします。上述の zonal Service に failover を加えるものではありません。既存の DestinationRule がその shared host／subset を管理している場合は、競合する rule を新設せず、ここでの `trafficPolicy` を既存 object に merge してください。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: shared-endpoint-locality
  namespace: zone-rollouts-demo
spec:
  host: shared-app.zone-rollouts-demo.svc.cluster.local
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
      localityLbSetting:
        enabled: true
        failoverPriority:
        - topology.kubernetes.io/region
        - topology.kubernetes.io/zone
    outlierDetection:
      consecutive5xxErrors: 3
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
```

locality priority は region／zone の一致を優先し、以降の traffic を eligible で healthy な endpoint に移せます。固定された AZ の循環順序を指定するものではありません。現在の field は `consecutive5xxErrors` です。連続 error の検知は traffic 駆動であり、`interval` は周期的な検知処理に適用されます。すべての endpoint を eject すると error になり、すでに失敗した request が自動 replay されることもありません。[ゾーン認識 routing](../resilience/03-zone-aware-routing.md)を参照してください。

## トラブルシューティング {#troubleshooting}

```bash
kubectl argo rollouts get rollout test-a -n zone-rollouts-demo
kubectl get virtualservice test -n zone-rollouts-demo -o yaml
kubectl get services test-stable-a test-canary-a -n zone-rollouts-demo -o yaml
kubectl get pods -n zone-rollouts-demo -l app=test -o wide --show-labels
kubectl get endpointslices -n zone-rollouts-demo -l kubernetes.io/service-name=test-canary-a
kubectl get pdb -n zone-rollouts-demo -o wide

istioctl proxy-config routes <client-a-pod> -n zone-rollouts-demo
istioctl proxy-config endpoints <client-a-pod> -n zone-rollouts-demo --cluster 'outbound|8080||test-canary-a.zone-rollouts-demo.svc.cluster.local'
kubectl get analysisruns -n zone-rollouts-demo
kubectl logs -n argo-rollouts deployment/argo-rollouts
```

- **更新の競合**: 同じ route の所有権を奪い合っているのか、共有 VirtualService の object version が一時的に競合しているのかを区別します。subset 名を分けるだけでは、どちらの原因も解消しません。
- **誤ったゾーンが選択される**: client Pod の実際の label、Node placement、compile 済み route を比較します。Node zone label が Pod にコピーされたとは仮定しないでください。
- **fallback がない**: まず選択した Service／subset の eligible endpoint を調べます。A の外に endpoint がなければ、outlier detection を速めても AZ 間 failover はできません。
- **canary traffic がない**: mesh を通過しているか、EndpointSlice が Ready か、hash selector、実際の weight、sample 数を確認します。
- **analysis が停止／失敗する**: aggregate rollout phase だけでなく、raw result と provider error を確認します。独自の zone label がないことは、組み込み telemetry の欠落を意味するものではありません。

## ベストプラクティス {#best-practices}

### 1. Version 変更を明示的に調整する

`Promote` は既存 pause から再開する操作であり、新しい image を deploy したり、別 AZ の健全性を証明したりするものではありません。Git（または隔離した lab）で1ゾーンの desired image を更新し、analysis と workload state を観測してから、次のゾーンに進むか判断します。5分待つだけでは十分な根拠になりません。

```bash
# Isolated lab alternative to changing Git; affects zone A only.
kubectl argo rollouts set image test-a app=argoproj/rollouts-demo@sha256:e32df3d15f759d36c323b3dccb7003d38df1a4274d37217715151f085c24c58f -n zone-rollouts-demo
kubectl argo rollouts get rollout test-a -n zone-rollouts-demo --watch
# After the intended manual pause and review:
kubectl argo rollouts promote test-a -n zone-rollouts-demo
```

`Abort` は Git の desired image を戻しません。GitOps が各ゾーンの管理下にある weight や Service hash selector を上書きしないよう調整してください。前述の統合ガイドも参照してください。

### 2. Continuous Analysis の別案

continuous monitoring が必要なら、inline-step の schedule を意図的に置き換えます。background template では `count` を省略し、`startingStep: 2` は3番目の step を指します。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: zone-canary-continuous
  namespace: zone-rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 1m
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
  - name: http-2xx-rate
    interval: 1m
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.95
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"2.."}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
---
spec:
  strategy:
    canary:
      analysis:
        templates:
        - templateName: zone-canary-continuous
        startingStep: 2
        args:
        - name: service-name
          value: test-canary-a
        - name: namespace
          value: zone-rollouts-demo
      steps:
      - setWeight: 5
      - pause:
          duration: 5m
      - setWeight: 25
      - pause:
          duration: 5m
      - setWeight: 50
      - pause: {}
```

この A 用 fragment を B／C に適用する場合は、正しいゾーンの route、Service、argument を残してください。独立した analysis も、共有 Prometheus／network／control plane に依存する場合があります。

### 3. Monitoring rule

この PrometheusRule には Prometheus Operator と、rule namespace／label selector の一致が必要です。Istio addon の単独 Prometheus は、この CRD を自動では読み込みません。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: zone-rollout-alerts
  namespace: zone-rollouts-demo
spec:
  groups:
  - name: zone-rollout
    rules:
    - alert: HighErrorRateZoneACanary
      expr: |-
        ((sum(rate(istio_requests_total{reporter="source",destination_service_namespace="zone-rollouts-demo",destination_service_name="test-canary-a",response_code=~"5..|0"}[2m])) or vector(0)) / sum(rate(istio_requests_total{reporter="source",destination_service_namespace="zone-rollouts-demo",destination_service_name="test-canary-a"}[2m]))) > 0.05
        and
        (sum(increase(istio_requests_total{reporter="source",destination_service_namespace="zone-rollouts-demo",destination_service_name="test-canary-a"}[2m]))) >= 20
      for: 2m
      annotations:
        summary: Zone A canary has elevated 5xx/zero-status rate with observed traffic
    - alert: UnexpectedDemoZoneRoute
      expr: |-
        sum(rate(istio_requests_total{
          reporter="source",source_workload="zone-client-a",source_workload_namespace="zone-rollouts-demo",
          destination_service_namespace="zone-rollouts-demo",destination_service_name=~"test-(stable|canary)-(b|c)"
        }[5m])) > 0
      for: 5m
      annotations:
        summary: Demo client A is using a B/C destination Service; inspect route/placement assumptions
```

1つ目の rule は5xx／zero-status failure を検知します。4xx は Analysis の2xx rate を下げますが、この error rule の対象ではありません。traffic が少ない場合や欠損している場合は、期待 traffic／telemetry health を示す signal を別途設計します。data がないことは canary が健全である証拠ではありません。

2つ目は**demo 用の routing invariant alert**であり、あらゆる物理 AZ の状態を検知する一般的な alert ではありません。実際の source Deployment が `zone-client-a` で、配置先が A、B／C Service に各 zone selector が残っていることを前提にしています。物理 zone を測定するには、routing／observability guide に記載された、検証済みの node／endpoint locality または明示的に追加した telemetry を使ってください。

### 4. 復旧と capacity

実際の EKS／node provisioning model に応じて Spot capacity を分散し、fault-tolerant capacity を十分に確保します。zonal affinity、中断処理、PDB policy は代替 capacity を保証しません。node group の lifecycle 動作と、アプリケーションの termination／restore 処理を確認してください。

この blueprint には resource や latency の測定結果はありません。実 workload における reconcile 負荷、endpoint 数、resource 使用量、正常時／障害時の latency を測ってから、Istiod、proxy、Rollouts controller を sizing してください。

## 参考資料と次のステップ

- [Argo Rollouts 統合](08-argo-rollouts.md)
- [ゾーン認識 routing](../resilience/03-zone-aware-routing.md)
- [Outlier Detection](../resilience/01-outlier-detection.md)
- [DestinationRule](../traffic-management/03-destination-rule.md)
- [Istio VirtualService の source selector](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [Istio locality failover](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/failover/)
- [Istio DestinationRule API](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [Argo Rollouts Istio integration](https://argoproj.github.io/argo-rollouts/features/traffic-management/istio/)
- [Kubernetes disruption](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [PDB の設定と percentage の切り上げ](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [Node affinity](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
- [EC2 interruption notice](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-instance-termination-notices.html)
- [EKS managed node group の Spot 動作](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html)
- [AWS の AZ ID と account mapping](https://docs.aws.amazon.com/global-infrastructure/latest/regions/az-ids.html)
- [AWS Region と Availability Zone](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html)

上記の保守対象 integration／routing guide を、lab validation の出発点にしてください。[Multi-cluster](02-multi-cluster.md) では trust、connectivity、failure domain の追加設計を扱います。単一設定を追加するだけの blueprint ではありません。
