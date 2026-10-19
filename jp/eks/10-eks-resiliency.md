# EKS のレジリエンスと高可用性

> **API の設定例の基準**: Kubernetes 1.36。現在サポートされている EKS と互換性のあるコントローラーのリリースを選択してください。
> **最終更新**: 2026年9月12日

ここに示すのは設定パターンであり、本番環境で検証済みのプラットフォームではありません。管理下にあるテスト範囲を用意し、アプリケーションイメージ、ヘルスチェックパス、IAM、インフラストラクチャの参照先をレビュー済みの値に置き換えてください。このレビューでは、クラスター、フェイルオーバー、カオス実験を実行していません。

RTO は検知と復旧を含む許容可能な復旧時間の目標、RPO は許容可能な復旧時点、つまりデータ損失の範囲です。マルチ AZ、レプリケーション、コントロールプレーンの SLA があっても、データ損失がゼロになることや、特定のワークロード復旧時間が保証されるわけではありません。

## レジリエンスの概要

レジリエンスとは、**障害時の影響を抑えながら通常状態に復旧する、またはサービスを維持する能力**です。単純な高可用性（HA）を超え、障害を予測して備える設計思想を表します。

### レジリエンスの成熟度モデル

| レベル | 対象範囲 | 制御の例 | 以前の版にある復旧時間の例示（実測値ではありません） |
| --- | --- | --- | --- |
| 1. 基本 | Pod／ワークロード | Probe、リソース、退避予算、シャットダウン | 数秒～数分 |
| 2. マルチ AZ | AZ 障害 | 配置、残存容量、トラフィック／データの復旧 | 数秒～数分 |
| 3. セル | サービスの分割単位 | ルーティング、依存先と容量の制限 | 部分的な影響なら数秒～数分 |
| 4. マルチリージョン | リージョン障害 | リージョン間のトラフィック／データ切り替えと運用 | 設計に応じて、ほぼゼロから数分／数時間 |

以前の各言語版では、異なる復旧時間の例を使っていました。このモデルは設計上の選択肢を整理するもので、認定ではなく、上位レベルほど速く復旧するという保証でもありません。ユーザージャーニーとその依存先ごとに目標を定め、実測してください。

リージョンの EKS コントロールプレーンは 3 つの AZ にまたがって管理されます。現在のエンドポイント SLA は、Standard Control Plane が月間稼働率 99.95%（5 分間隔で測定）、Provisioned Control Plane が 99.99%（1 分間隔で測定）です。これは条件付きのサービスクレジットに関するコミットメントであり、アプリケーションの SLO／RTO／RPO を保証するものではありません。[AWS EKS SLA](https://aws.amazon.com/eks/sla/)


> すべてのサービスにレベル 4 が必要なわけではありません。SLA 要件、規制、予算に応じて適切なレベルを選択してください。

***

## レベル 1: 基本的なレジリエンス（Pod レベル）

### Liveness／Readiness／Startup Probe

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: resilience-demo
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: app
        image: registry.example.com/team/web-app:replace-with-reviewed-digest
        ports:
        - name: http
          containerPort: 8080
        startupProbe:
          httpGet:
            path: /healthz
            port: http
          failureThreshold: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        lifecycle:
          preStop:
            sleep:
              seconds: 5
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

上の画像は、アプリケーション用の明示的なプレースホルダーであり、公開済みの成果物ではありません。デプロイ前に検証済みのダイジェストへ置き換え、ヘルスチェックの契約を実装してください。Startup Probe は Liveness／Readiness Probe の開始を制御します。下流サービスの応答が遅いという理由だけで Liveness Probe が失敗しないようにしてください。リソースと Probe の値は例示です。Job や Init Container に常に同じ Probe が必要とは限りません。

### PodDisruptionBudget（PDB）

PDB は、対象 Pod に対するサポート済みの自発的な退避を制約します。AZ／ハードウェア障害、Pod の直接削除、Deployment 自体のローリング更新／スケールダウンを通じて Pod 数を維持するものではありません。コントローラーの戦略、配置、予備容量はそれぞれ別の制御です。

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
  namespace: resilience-demo
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: web-app
```

```bash
# Check PDB status
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pdb web-app-pdb
# Inspect the actual workload health and ongoing disruptions.
# Illustrative only: three Ready replicas and no ongoing/unhealthy deductions permit one eviction.
```

### グレースフルシャットダウン

```yaml
spec:
  terminationGracePeriodSeconds: 60
  containers:
  - name: app
    lifecycle:
      preStop:
        sleep:
          seconds: 5
```

これは管理対象アプリケーションの Pod 仕様の断片です。組み込みの preStop sleep は Kubernetes 1.34 から GA であり、基準とする 1.36 でも有効です。5 秒の sleep は単なる待ち時間であり、エンドポイント／ロードバランサーへの反映を保証しません。猶予期間には Hook の実行時間も含まれ、EndpointSlice の終了状態への更新はノードのシャットダウンと並行して進みます。終了中のエンドポイントは、排出処理のため ready=false と serving 条件を伴って一覧に残ることがあります。

その後、ランタイムは設定された停止シグナル（通常は SIGTERM。イメージやランタイムの設定によって異なることがあります）を送信します。アプリケーションはそのシグナルを処理し、強制終了される前に処理を完了するか、新しい処理を拒否する必要があります。preStop で PID 1 を手動終了し、エンドポイントが決まった順番で削除されると想定しないでください。長時間接続、登録解除、バッファーのフラッシュを実際にテストしてください。

***

## レベル 2: マルチ AZ 戦略

### Pod Topology Spread Constraints

トポロジー分散は配置に影響しますが、正常な容量を作り出したり、障害後に既存 Pod を自動で移動したりはしません。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 6
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      topologySpreadConstraints:
      # Hard constraint for the documented N-1 example; review eligible domains and capacity.
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-app
        minDomains: 2
      # Soft constraint: Even distribution across nodes
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: web-app
      containers:
      - name: app
        image: web-app:1.0
```

| パラメーター | 説明 |
| --- | --- |
| `maxSkew` | DoNotSchedule の場合、候補となるドメインの Pod 数と全体の最小値との差 |
| `topologyKey` | 分散の基準（ゾーン、ホスト名など） |
| `whenUnsatisfiable` | `DoNotSchedule`（ハード）または `ScheduleAnyway`（ソフト） |
| `minDomains` | 適格なドメインがこれより少ない場合、全体の最小値はゼロになる |

例として、適格なゾーンが 2 つ残り、それぞれに対象 Pod が 2 つある場合を考えます。minDomains=3 では全体の最小値がゼロになり、maxSkew=1 のとき代替 Pod の配置を妨げることがあります。minDomains=2 なら、他の制約や容量が許す場合に、新たな Pod の分散計算が可能です。使用中の AZ を正確に 2 つまたは 3 つにする指定ではありません。最初の 3 AZ 配置と、障害後に残る AZ の余裕容量は別々に確保してください。ScheduleAnyway は優先設定であり、他のスケジューラー制約は引き続き適用されます。

### Karpenter のマルチ AZ NodePool

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
      - key: topology.kubernetes.io/zone
        operator: In
        values: ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["on-demand", "spot"]
      - key: node.kubernetes.io/instance-type
        operator: In
        values: ["m6i.xlarge", "m6i.2xlarge", "m7i.xlarge", "m7i.2xlarge"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: "20%"    # Applicable voluntary budget, rounded up and reduced by deleting/NotReady nodes
    - nodes: "0"
      schedule: "0 0 * * MON-FRI"   # UTC 00:00–09:00 = Korea/Japan 09:00–18:00; not all failure types
      duration: 9h
```

Karpenter の要件指定でゾーンを許可しても、ノードが均等に事前プロビジョニングされたり、障害用の余裕容量が確保されたりはしません。EKS と互換性のあるバージョンを使ってください。スキーマの基準は保守されている 1.14.1 リリースであり、過去の 1.0 以降を一律の最低要件とするものではありません。参照される EC2NodeClass、AMI、ロール、サブネット、容量は、事前にレビュー済みである必要があります。

割合による予算は ceil（合計 × 割合）で計算し、削除中と NotReady のノードを差し引きます。適用される予算のうち最も厳しいものが優先されます。すべての中断、期限切れ、修復、手動削除をレート制限するものではありません。スケジュールは UTC です。例では平日の 09:00～18:00（韓国／日本時間）の 1 ブロックを使います。予算をゼロにしても、すべての障害を防げるわけではありません。

Spot と On-Demand のプールを分け、重みを 100／50 にできます。ただし重みはプロビジョニングの優先度であり、Spot が利用できない場合に限って低い重みのプールを使う保証ではありません。既存容量、制約、バッチ処理も影響します。NodePool の上限はプロビジョニングを制限するもので、事前スケーリングではありません。

### 同一ゾーンのサービス優先設定

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-app
  namespace: resilience-demo
spec:
  selector:
    app: web-app
  ports:
  - name: http
    port: 80
    targetPort: http
  trafficDistribution: PreferSameZone
```

PreferSameZone／PreferSameNode は Kubernetes 1.35 から GA であり、基準とする 1.36 でも有効です。PreferClose は PreferSameZone の古い別名です。これは優先設定であり、厳密な局所性やレイテンシー／コストの保証ではありません。実際の Proxy／EndpointSlice の挙動と Local トラフィックポリシーを確認してください。古い topology-mode=Auto アノテーションは、別のヒント割り当てヒューリスティックを使います。topology-aware-hints は旧式のガイダンスです。

参照: [PDB](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)、[Pod の終了処理](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)、[トポロジー分散](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)、[Service のトラフィック分散](https://kubernetes.io/docs/concepts/services-networking/service/#traffic-distribution)、[Karpenter の中断制御](https://karpenter.sh/docs/concepts/disruption/)。

### ARC Zonal Shift

手動のゾーンシフトと自動のゾーンオートシフトは別の操作です。EKS 連携は影響を受けたゾーンのノードを cordon し、そのエンドポイントを EndpointSlice から削除しますが、Pod を退避したりノードを終了したりはしません。Auto Mode は対象 AZ への新規ノード作成を避け、関連する自発的な中断を一時停止します。マネージドノードグループは AZ リバランスを一時停止し、その AZ への新規起動を避けます。現在の Karpenter 連携には、文書化されたバージョン、設定、IAM の準備が必要です。ロードバランサーのシフトは独立したリソース操作です。

最初に、アカウント、正確なマネージドリソース、有効化済み連携、既存のプラクティス設定、アラームの挙動を確認してください。障害後も残るゾーンのアプリケーション、DNS、データ、ノード容量をテストします。ゾーンシフトはネットワークを完全に隔離するものではありません。サービスの全エンドポイントが影響ゾーンにある場合、EKS にはフェイルセーフがあります。既存のゾーン固定 EBS ボリュームを移動することもできません。Auto Mode のみの構成ではノードシステムの CoreDNS を使います。Auto Mode 以外のノードが混在する場合は、Deployment とその容量も必要です。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the resource region}"
: "${ARC_RESOURCE_ARN:?Set the exact owned EKS cluster or eligible load-balancer ARN}"
aws sts get-caller-identity
aws arc-zonal-shift get-managed-resource \
  --region "$AWS_REGION" --resource-identifier "$ARC_RESOURCE_ARN"
```

次のブロックは個別の運用手順であり、まとめて実行するセットアップスクリプトではありません。プラクティス設定は定期的なトラフィック変更を開始するため、再作成せず既存設定を確認してください。結果アラームの識別子は ARN 文字列であり、alarmName／リージョンのオブジェクトではありません。準備ができたらオートシフトを別途有効化してください。

```bash
# MUTATION: authorizes recurring weekly traffic-shifting practice runs.
: "${OUTCOME_ALARM_ARN:?Set the reviewed CloudWatch alarm ARN in the resource region}"
aws arc-zonal-shift create-practice-run-configuration \
  --region "$AWS_REGION" --resource-identifier "$ARC_RESOURCE_ARN" \
  --outcome-alarms "alarmIdentifier=$OUTCOME_ALARM_ARN,type=CLOUDWATCH"
```
```bash
# MUTATION: enable automatic shifts only after the readiness review.
aws arc-zonal-shift update-zonal-autoshift-configuration \
  --region "$AWS_REGION" --resource-identifier "$ARC_RESOURCE_ARN" \
  --zonal-autoshift-status ENABLED
```
```bash
# MUTATION: a separate, manually initiated one-hour shift.
set -euo pipefail
: "${AWAY_FROM_AZ:?Set an AZ of this resource}"
SHIFT_ID=$(aws arc-zonal-shift start-zonal-shift \
  --region "$AWS_REGION" --resource-identifier "$ARC_RESOURCE_ARN" \
  --away-from "$AWAY_FROM_AZ" --expires-in 1h \
  --comment "Owned resilience exercise" --query zonalShiftId --output text)
test -n "$SHIFT_ID" && test "$SHIFT_ID" != None
printf '%s\n' "$SHIFT_ID" > owned-zonal-shift-id.txt
```
```bash
# MUTATION: cancel only the recorded manual shift after checking its ownership.
: "${SHIFT_ID:?Use the exact ID recorded for this exercise}"
aws arc-zonal-shift cancel-zonal-shift \
  --region "$AWS_REGION" --zonal-shift-id "$SHIFT_ID"
```
[EKS の ARC の挙動と前提条件](https://docs.aws.amazon.com/eks/latest/userguide/zone-shift.html) · [Auto Mode／Karpenter との連携](https://aws.amazon.com/blogs/containers/arc-zonal-shift-support-for-eks-auto-mode-and-karpenter/)

### ストレージに関する考慮事項

WaitForFirstConsumer は、スケジューラーが配置を考慮できるまで初回のプロビジョニング／バインドを遅らせます。**EBS は AZ に固定されます。** AZ 障害後に別の AZ で代替 Pod を起動しても、同じボリュームをアタッチできません。レビュー済みのバックアップ／レプリケーション計画を使ってデータを復元／移行し、RPO／RTO をテストしてください。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: resilience-ebs
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  encrypted: 'true'
allowVolumeExpansion: true
reclaimPolicy: Retain
```

この StorageClass は標準の EBS CSI ドライバーを使います。Auto Mode は ebs.csi.eks.amazonaws.com と、互換性のある独自のノード／IAM／移行要件を使います。いずれの設計でも encrypted: "true" を明示し、作成された EBS ボリュームと KMS キーを確認してください。Auto Mode のノードルート／データディスク暗号化が、すべてのワークロード PVC の暗号化を意味するわけではありません。現在の Auto Mode StorageClass パラメーターのデフォルトは false です。Retain は解放されたボリュームを管理された復旧／クリーンアップ用に保持します。バックアップではなく、課金対象のリソースが残る場合があります。

AZ をまたいで共有ファイルシステムにアクセスするには、既存の **Regional** EFS ファイルシステム、到達可能なマウントターゲット、TCP 2049 のセキュリティルール、レビュー済みのアクセスポイント権限、互換性のある CSI IAM が必要です。EFS One Zone は同じレジリエンス設計ではありません。以下の ID はプレースホルダーであり、ここではファイルシステムを作成しません。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: resilience-efs
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: '700'
  basePath: /resilience-demo
reclaimPolicy: Retain
mountOptions:
- tls
```
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: efs-claim
  namespace: resilience-demo
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: resilience-efs
  resources:
    requests:
      storage: 5Gi
```

5Gi の PVC 要求は、EFS の強制ストレージクォータではありません。TLS マウント暗号化とファイルシステムの保存時暗号化は別の設定です。Retain を使う場合も、アクセスポイントとデータをクリーンアップする手順を文書化してください。

[EKS EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html) · [Auto Mode StorageClass パラメーター](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html) · [EFS CSI](https://github.com/kubernetes-sigs/aws-efs-csi-driver)

### Istio のローカリティ対応ルーティング

Istio のサイドカーモードの例では、文書化されたローカリティ上書きを設定しない限り、Istio は Pod が稼働するノードからローカリティを取得します。通常の Pod ゾーンラベルが自動で使われるわけではありません。Proxy の実際のエンドポイント／ローカリティと、到達可能で正常な容量を確認してください。文書化されたローカリティ・フェイルオーバーの挙動にはアウトライアー検出が必要です。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: web-app-locality
  namespace: resilience-demo
spec:
  host: web-app.resilience-demo.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
    loadBalancer:
      simple: ROUND_ROBIN
      localityLbSetting:
        enabled: true
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

**重み付き分散を構成する別案**として、loadBalancer の localityLbSetting を次の断片に置き換えてください。ソースにある 3 つのゾーンすべてを含みます。80／10／10 は設定する重みであり、実測された局所性やフェイルオーバー容量の保証ではありません。distribute ルールを互換性のない failover ポリシーと併用しないでください。

```yaml
localityLbSetting:
  enabled: true
  distribute:
  - from: ap-northeast-2/ap-northeast-2a/*
    to:
      ap-northeast-2/ap-northeast-2a/*: 80
      ap-northeast-2/ap-northeast-2b/*: 10
      ap-northeast-2/ap-northeast-2c/*: 10
  - from: ap-northeast-2/ap-northeast-2b/*
    to:
      ap-northeast-2/ap-northeast-2a/*: 10
      ap-northeast-2/ap-northeast-2b/*: 80
      ap-northeast-2/ap-northeast-2c/*: 10
  - from: ap-northeast-2/ap-northeast-2c/*
    to:
      ap-northeast-2/ap-northeast-2a/*: 10
      ap-northeast-2/ap-northeast-2b/*: 10
      ap-northeast-2/ap-northeast-2c/*: 80
```

以前の「ローカルのトラフィック 80% 以上」「コストを 60～80% 削減」「同一 AZ レイテンシー 1ms 未満」という値は、未検証の例示としてのみ残しています。測定元は確認できず、ヘルス状態、接続再利用、エンドポイント構成、リクエストのバイト数、料金によって結果は変わります。

[ローカリティ・フェイルオーバー](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/failover/) · [重み付き分散](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/distribute/)

---

## レベル 3: セルベース・アーキテクチャ

### セルの概念

セルとは、**独自のデータストア、キャッシュ、キューを持つ自己完結型のサービス単位**です。ルーティング、容量、依存関係によってセル境界を守り、障害の影響を局所化することを目指します。

### セルの分割戦略

| 戦略 | 説明 | 適用例 |
| --- | --- | --- |
| 顧客単位 | 顧客 ID のハッシュでセルを割り当てる | SaaS のマルチテナント |
| リージョン単位 | 地理的な場所ごとに分割する | グローバルサービス |
| 容量単位 | 容量に達したら新しいセルを作成する | 負荷の均等分散 |
| ティア単位 | サービスティアごとにセルを分ける | Premium／Standard の差別化 |

### Namespace を使ったセルの実装

Namespace、クォータ、NetworkPolicy が作るのは論理境界であり、独立した障害ドメインではありません。共有ノード、コントロールプレーン、CNI、DNS、ルーター、データサービスは引き続き依存先です。ネットワークプラグインがポリシーを実施することを確認してください。許可される通信は、適用されるすべてのポリシーの和集合です。以下のルータ Namespace／ワークロードは、指定されたラベルで存在している必要があります。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cell-1
  labels:
    cell: '1'
    customer-range: a-f
```
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: cell-1-quota
  namespace: cell-1
spec:
  hard:
    requests.cpu: '20'
    requests.memory: 40Gi
    limits.cpu: '40'
    limits.memory: 80Gi
    pods: '100'
    services: '20'
    persistentvolumeclaims: '50'
```
```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: cell-1-limits
  namespace: cell-1
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 128Mi
    type: Container
```
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: cell-1-isolation
  namespace: cell-1
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector: {}
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: cell-router
      podSelector:
        matchLabels:
          app: cell-router
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector: {}
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

DNS ルールは kube-system の該当する CoreDNS Pod に対する TCP と UDP を許可します。Node-local／Auto Mode のシステム DNS は別の経路を使うため、モードごとの検証が必要です。このポリシーは任意の外部通信を意図的に許可しません。必要なサービスについて、レビュー済みのエンドポイントまたは Egress Gateway のルールを追加してください。0.0.0.0/0 から 10.0.0.0/8 だけを除外しても、すべてのプライベートネットワークやセルを隔離できるわけではありません。

[NetworkPolicy の仕様](https://kubernetes.io/docs/concepts/services-networking/network-policies/)

### シャッフル・シャーディング

ルーティング、受付制限、データ可用性によって設計を実現する場合、顧客を一定のセル部分集合へ割り当てることで、顧客間の影響の重なりを減らせます。

```
With 2 Cell combinations from a pool of 8 Cells:
- Customer A → Cell 1, Cell 5
- Customer B → Cell 2, Cell 7
- Customer C → Cell 1, Cell 3

When Cell 1 fails:
- Customer A → Can use Cell 5 if failover routing/data/capacity are ready
- Customer B → Not affected ✅
- Customer C → Can use Cell 3 if failover routing/data/capacity are ready
```

C(8,2)=28 です。独立かつ一様に割り当てる場合、同じペアになる確率は厳密に 1/28（約 3.6%）です。固定された 1 つの障害セルが影響するのは、割り当て全体の期待値で 2/8=25% です。顧客数や負荷の最大 25% という意味ではありません。ConfigMap やハッシュだけでは、フェイルオーバーもデータレプリケーションも実装されません。

***

## レベル 4: マルチクラスター／マルチリージョン

ユーザージャーニーとデータ整合性の要件に応じてパターンを選択してください。クラスターやリージョンを追加するだけで、RTO／RPO がほぼゼロになるわけではありません。以下の時間／コストは、検証されていない設計例であり、実測値や AWS のコミットメントではありません。

| パターン | 以前の RTO 例 | 以前の RPO 例 | 以前のコスト例 | 設計上の条件 |
| --- | --- | --- | --- | --- |
| アクティブ／アクティブ | ほぼ 0 を目標 | ほぼ 0 を目標 | 2 倍以上 | ルーティング、整合性、競合処理、容量 |
| アクティブ／パッシブ | 数分～数時間 | 数分 | 1.5 倍 | 待機系の準備、レプリケーション遅延、昇格 |
| リージョン分離 | 指定なし | 指定なし | リージョンあたり 1 倍 | リージョンごとに独立したサービス。自動フェイルオーバーではない |
| ハブ・スポーク | 数分 | 数分 | 1.3 倍 | 別途保護しない限り、ハブは共有依存先 |

### Argo CD ApplicationSet

次の 3 案には、稼働中の Argo CD／ApplicationSet コントローラー、文書化されたラベルを持つ明示的に登録済みで到達可能なクラスター、リポジトリ認証情報、レビュー済みのリポジトリ／宛先／リソース種別に制限した事前作成済み AppProject が必要です。例のリポジトリとリビジョンは、管理下の値に置き換えてください。生成される Application は手動同期です。自動 sync／prune ポリシーを有効にする前に、レンダリングされた宛先とマニフェストをレビューしてください。Generator が EKS クラスターを作成することはありません。

#### Cluster Generator

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: resilience-clusters
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions:
  - missingkey=error
  generators:
  - clusters:
      selector:
        matchLabels:
          resilience-example: 'true'
  template:
    metadata:
      name: web-app-{{.nameNormalized}}
    spec:
      project: resilience-reviewed
      source:
        repoURL: https://github.com/example/owned-gitops.git
        targetRevision: REPLACE_WITH_REVIEWED_COMMIT
        path: apps/web-app/overlays/{{.metadata.labels.region}}
      destination:
        server: '{{.server}}'
        namespace: resilience-demo
```
#### Git ディレクトリ × 登録済みクラスター

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: resilience-region-directories
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions:
  - missingkey=error
  generators:
  - matrix:
      generators:
      - git:
          repoURL: https://github.com/example/owned-gitops.git
          revision: REPLACE_WITH_REVIEWED_COMMIT
          directories:
          - path: regions/*
      - clusters:
          selector:
            matchLabels:
              resilience-example: 'true'
              region: '{{.path.basename}}'
  template:
    metadata:
      name: '{{.nameNormalized}}-{{.path.basename}}'
    spec:
      project: resilience-reviewed
      source:
        repoURL: https://github.com/example/owned-gitops.git
        targetRevision: REPLACE_WITH_REVIEWED_COMMIT
        path: '{{.path.path}}'
      destination:
        server: '{{.server}}'
        namespace: resilience-demo
```

2 つ目の Matrix 子要素は、ディレクトリのベース名を登録済みクラスターのラベルと照合し、実際の server 値を使います。リージョン名から EKS API URL を組み立てることはできません。ラベルがない、または一致しない場合、Application が 1 つも生成されないことがあります。スキーマの妥当性だけでなく、生成された一覧を確認してください。

#### クラスター × アプリケーションの一覧

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: resilience-cluster-app-matrix
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions:
  - missingkey=error
  generators:
  - matrix:
      generators:
      - clusters:
          selector:
            matchLabels:
              resilience-example: 'true'
      - list:
          elements:
          - app: frontend
            port: '80'
          - app: backend
            port: '8080'
          - app: worker
            port: '9090'
  template:
    metadata:
      name: '{{.nameNormalized}}-{{.app}}'
    spec:
      project: resilience-reviewed
      source:
        repoURL: https://github.com/example/owned-gitops.git
        targetRevision: REPLACE_WITH_REVIEWED_COMMIT
        path: apps/{{.app}}
        helm:
          parameters:
          - name: cluster.name
            value: '{{.name}}'
          - name: service.port
            value: '{{.port}}'
      destination:
        server: '{{.server}}'
        namespace: resilience-demo
```
[ApplicationSet の Matrix パラメーター](https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/Generators-Matrix/)

### Global Accelerator

既存の適格な ALB／NLB エンドポイントを使い、TLS、ヘルスチェック、リージョンごとの十分な容量をテストしてください。次は任意のプロビジョニング例であり、ここでは実行していません。返されたリソース ID と管理下のクリーンアップ計画を保存してください。途中で失敗しても、それまでに作成したリソースは削除されません。Accelerator を無効にしてもリソース料金はなくなりません。

```bash
# MUTATIONS: creates a disabled, billable accelerator and its configuration.
set -euo pipefail
: "${GA_API_REGION:?Set the documented Global Accelerator API region}"
: "${ACCELERATOR_NAME:?Set a unique owned name}"
: "${REGION_ONE:?Set the first endpoint region}"
: "${REGION_TWO:?Set the second endpoint region}"
: "${REGION_ONE_LB_ARN:?Set the reviewed eligible ALB/NLB ARN}"
: "${REGION_TWO_LB_ARN:?Set the reviewed eligible ALB/NLB ARN}"
test "$REGION_ONE" != "$REGION_TWO"
ACCELERATOR_ARN=$(aws globalaccelerator create-accelerator \
  --region "$GA_API_REGION" --name "$ACCELERATOR_NAME" \
  --ip-address-type IPV4 --no-enabled --query Accelerator.AcceleratorArn --output text)
test -n "$ACCELERATOR_ARN" && test "$ACCELERATOR_ARN" != None
LISTENER_ARN=$(aws globalaccelerator create-listener \
  --region "$GA_API_REGION" --accelerator-arn "$ACCELERATOR_ARN" \
  --protocol TCP --port-ranges FromPort=443,ToPort=443 \
  --query Listener.ListenerArn --output text)
test -n "$LISTENER_ARN" && test "$LISTENER_ARN" != None
aws globalaccelerator create-endpoint-group \
  --region "$GA_API_REGION" --listener-arn "$LISTENER_ARN" \
  --endpoint-group-region "$REGION_ONE" --traffic-dial-percentage 100 \
  --endpoint-configurations "EndpointId=$REGION_ONE_LB_ARN,Weight=100"
aws globalaccelerator create-endpoint-group \
  --region "$GA_API_REGION" --listener-arn "$LISTENER_ARN" \
  --endpoint-group-region "$REGION_TWO" --traffic-dial-percentage 100 \
  --endpoint-configurations "EndpointId=$REGION_TWO_LB_ARN,Weight=100"
```
```bash
# MUTATION: run separately after endpoint health, routing, data and rollback checks.
: "${ACCELERATOR_ARN:?Use the accelerator just reviewed}"
aws globalaccelerator update-accelerator \
  --region "$GA_API_REGION" --accelerator-arn "$ACCELERATOR_ARN" --enabled
```

Traffic dial は、新規接続について、そのリージョンの Endpoint Group にすでに向けられているトラフィックの割合です。2 つの dial を 50% にしても、グローバルな 50／50 分散にはなりません。この例では両方を 100% にしています。dial の変更で既存接続が強制的に移動することはなく、フェイルオーバールールは dial がゼロでも無視する場合があります。エンドポイントの重みと Traffic dial は別の制御です。ALB／NLB エンドポイントのヘルス状態は Elastic Load Balancing のヘルスチェックに従います。Global Accelerator の /healthz 上書きを設定しても、ターゲットグループのヘルスチェックは設定されません。

[Traffic dial の仕様](https://docs.aws.amazon.com/global-accelerator/latest/dg/about-endpoint-groups-traffic-dial.html) · [エンドポイントのヘルス状態](https://repost.aws/knowledge-center/global-accelerator-unhealthy-endpoints) · [フェイルオーバールール](https://repost.aws/knowledge-center/global-accelerator-failover-different-region)

### Istio マルチプライマリ・フェデレーション

サイドカーのマルチプライマリ／複数ネットワーク設計には、共有された信頼済み ID モデル、個別のクラスター／ネットワーク名、到達可能なリモート Kubernetes API と East-West Gateway、互換性のあるサービス／Namespace、適切なデータ動作が必要です。ServiceEntry だけではフェデレーションは成立しません。Gateway へのアクセスを意図したネットワークに限定してください。TLS を終端する L7 ロードバランサーは AUTO_PASSTHROUGH と互換性がありません。

次の IstioOperator は **istioctl のインストール入力**であり、kubectl で適用するクラスター内 Operator ではありません。対応する東京側の設定と、公式の Gateway／Discovery のセットアップ全体を準備してください。DNS capture／auto-allocation のフラグは、そのセットアップの代わりにはなりません。

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    global:
      meshID: resilience-mesh
      multiCluster:
        clusterName: cluster-seoul
      network: network-seoul
```
```bash
# MUTATIONS: source-cluster credentials/RBAC and destination Secret may be created.
set -euo pipefail
umask 077
: "${SEOUL_CONTEXT:?Verify the owned Seoul context}"
: "${TOKYO_CONTEXT:?Verify the owned Tokyo context}"
test "$SEOUL_CONTEXT" != "$TOKYO_CONTEXT"
test ! -e tokyo-remote-secret.yaml && test ! -e seoul-remote-secret.yaml
istioctl create-remote-secret --context "$TOKYO_CONTEXT" --name cluster-tokyo > tokyo-remote-secret.yaml
istioctl create-remote-secret --context "$SEOUL_CONTEXT" --name cluster-seoul > seoul-remote-secret.yaml
# Inspect Secret metadata without printing token data; verify destination contexts first.
kubectl --context "$SEOUL_CONTEXT" -n istio-system apply -f tokyo-remote-secret.yaml
kubectl --context "$TOKYO_CONTEXT" -n istio-system apply -f seoul-remote-secret.yaml
```

remote-secret ファイルには認証情報が含まれます。安全に保ち、ソース管理に含めず、インストール後は認証情報の取り扱いポリシーに従ってローカルコピーを削除してください。上記のコマンドは、信頼関係／ネットワークを準備した後に実行する変更操作であり、読み取り専用の診断ではありません。

明示的なルーティングでは、各クラスターで設定するワークロードのリージョン別 **Pod テンプレートラベル**を利用できます。ノードのトポロジーラベルは Pod に自動コピーされません。x-region はルーティング入力として扱い、認可には使わないでください。80／20 の重みはデータのフェイルオーバー手順を実装するものではありません。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: cross-cluster-routing
  namespace: resilience-demo
spec:
  hosts:
  - web-app.resilience-demo.svc.cluster.local
  http:
  - match:
    - headers:
        x-region:
          exact: tokyo
    route:
    - destination:
        host: web-app.resilience-demo.svc.cluster.local
        subset: tokyo
  - route:
    - destination:
        host: web-app.resilience-demo.svc.cluster.local
        subset: seoul
      weight: 80
    - destination:
        host: web-app.resilience-demo.svc.cluster.local
        subset: tokyo
      weight: 20
```
```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: cross-cluster-subsets
  namespace: resilience-demo
spec:
  host: web-app.resilience-demo.svc.cluster.local
  subsets:
  - name: seoul
    labels:
      workload-region: ap-northeast-2
  - name: tokyo
    labels:
      workload-region: ap-northeast-1
```

無関係な外部 DNS サービスについては、別の ServiceEntry でレジストリー項目を記述できます。これは独自の DNS／TLS／アプリケーション要件を持つ外部サービス向けの別パターンであり、2 つ目のクラスターにある Kubernetes サービスを検出するものではありません。

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: reviewed-remote-service
  namespace: resilience-demo
spec:
  hosts:
  - remote-service.example.com
  location: MESH_EXTERNAL
  ports:
  - number: 443
    name: https
    protocol: TLS
  resolution: DNS
```
[Istio マルチプライマリの前提条件と手順](https://istio.io/latest/docs/setup/install/multicluster/multi-primary_multi-network/)

---

## アプリケーションのレジリエンス・パターン

前述の PDB とシャットダウンの例は、それぞれ対応する管理対象ワークロードにのみ適用されます。minAvailable と maxUnavailable はどちらも割合を切り上げます。3 Pod の 75% は Ready Pod が 3 つ必要であることを意味し、25% の maxUnavailable は 1 Pod の停止を許可します。コントローラーのローリング更新と Pod の直接削除は別の制御です。

### Istio によるサーキットブレーカー

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: backend-circuit-breaker
  namespace: resilience-demo
spec:
  host: backend-service.resilience-demo.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 3s
      http:
        http1MaxPendingRequests: 100
        http2MaxRequests: 1000
        maxRequestsPerConnection: 10
        maxRetries: 3
    outlierDetection:
      consecutive5xxErrors: 5
      consecutiveGatewayErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 30
      splitExternalLocalOriginErrors: true
```

これらの上限は設定された Proxy／宛先プールに適用され、クラスター全体の同時実行数を制限するものではありません。http2MaxRequests は同時に処理中の HTTP リクエスト数を制限します。maxRetries は 1 リクエストあたりの試行回数ではなく、**同時に未完了のリトライ数**を制限します。minHealthPercent はアウトライアー検出を有効にする条件を制御するもので、その割合の正常容量を予約するものではありません。エラーによる排除、接続上限、リトライは実測に基づいて調整してください。

### リトライ／タイムアウト

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: backend-retry-timeout
  namespace: resilience-demo
spec:
  hosts:
  - backend-service.resilience-demo.svc.cluster.local
  http:
  - match:
    - method:
        exact: GET
    route:
    - destination:
        host: backend-service.resilience-demo.svc.cluster.local
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 3s
      retryOn: 5xx,reset,connect-failure
      retryRemoteLocalities: true
```

GET 専用の Route は、アプリケーションが対象リクエストを本当に安全にリトライできることを前提とします。3 回のリトライは初回試行に加えて行われますが、合計 10 秒の予算、試行ごとの 3 秒制限、バックオフ、同時実行上限によってすべての試行が実行されないことがあります。リトライは過負荷を悪化させたり、副作用を重複させたりすることがあります。書き込み処理には明示的な冪等性の契約が必要です。retryRemoteLocalities は別のローカリティを許可する設定であり、リモートに正常な容量があることを保証しません。Envoy の retriable-4xx は現在 **409 のみ**であり、408 は含みません。楽観ロックの競合では、要求を再送するのではなく状態を読み直す必要がある場合があります。

[Istio DestinationRule](https://istio.io/latest/docs/reference/config/networking/destination-rule/) · [Envoy のリトライ条件](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/router_filter)

---

## カオスエンジニアリング

カオスエンジニアリングでは、反証可能な定常状態の仮説を、制御された障害を使ってテストします。管理下にある代表的なテスト環境から始めてください。本番実験では、影響範囲、実行権限、テレメトリー、停止条件、復旧を別途レビューする必要があります。CR の適用が障害を引き起こす場合があります。ここにある設定はオフラインで確認したもので、実行しておらず、本番利用の準備が整ったことを示すものではありません。

```bash
# Read-only: verify the exact cluster/namespace and opt-in test workload.
: "${KUBE_CONTEXT:?Set the owned test context}"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pods \
  -l 'app=web-app,experiment-approved=true' -o wide
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pdb
```
### AWS Fault Injection Service（FIS）

IAM 実験ロール／信頼ポリシー、必要な EKS アクセスエントリー（または文書化された旧マッピング）、Namespace を指定した Kubernetes ServiceAccount／Role／RoleBinding、アクション固有の EC2／ネットワーク権限を公式ガイドに従って準備してください。次のロールとアラーム ARN は、1 つの例示リージョン／アカウントのプレースホルダーです。すべて一貫して置き換えてください。アラームが存在し、有効なデータを受信し、テスト済みである必要があります。停止条件は、データの復元でも影響ゼロの保証でもありません。

Pod の対象指定には clusterIdentifier／namespace／selector を使います。**aws:eks:pod の resourceArns にクラスター ARN は指定できません。** アクションには kubernetesServiceAccount が必要です。Pod の削除は直接削除経路を使うため、PDB は削除防止にはなりません。COUNT(1) はオプトインした対象から 1 つ選ぶもので、AZ 障害をシミュレートしません。

#### Pod を 1 つ削除

```json
{
  "description": "Delete one selected test Pod; not an AZ outage",
  "targets": {
    "test-pod": {
      "resourceType": "aws:eks:pod",
      "selectionMode": "COUNT(1)",
      "parameters": {
        "clusterIdentifier": "REPLACE_WITH_OWNED_TEST_CLUSTER",
        "namespace": "resilience-demo",
        "selectorType": "labelSelector",
        "selectorValue": "app=web-app,experiment-approved=true"
      }
    }
  },
  "actions": {
    "delete-one": {
      "actionId": "aws:eks:pod-delete",
      "parameters": {
        "kubernetesServiceAccount": "fis-test",
        "maxErrorsPercent": "0"
      },
      "targets": {
        "Pods": "test-pod"
      }
    }
  },
  "stopConditions": [
    {
      "source": "aws:cloudwatch:alarm",
      "value": "arn:aws:cloudwatch:ap-northeast-2:123456789012:alarm:owned-resilience-stop"
    }
  ],
  "roleArn": "arn:aws:iam::123456789012:role/owned-fis-test"
}
```
#### Pod 1 つにネットワーク遅延を追加

```json
{
  "description": "Add bounded IPv4 latency to one selected test Pod",
  "targets": {
    "test-pod": {
      "resourceType": "aws:eks:pod",
      "selectionMode": "COUNT(1)",
      "parameters": {
        "clusterIdentifier": "REPLACE_WITH_OWNED_TEST_CLUSTER",
        "namespace": "resilience-demo",
        "selectorType": "labelSelector",
        "selectorValue": "app=web-app,experiment-approved=true"
      }
    }
  },
  "actions": {
    "latency": {
      "actionId": "aws:eks:pod-network-latency",
      "parameters": {
        "kubernetesServiceAccount": "fis-test",
        "duration": "PT1M",
        "delayMilliseconds": "200",
        "jitterMilliseconds": "50",
        "sources": "10.20.0.0/24",
        "maxErrorsPercent": "0"
      },
      "targets": {
        "Pods": "test-pod"
      }
    }
  },
  "stopConditions": [
    {
      "source": "aws:cloudwatch:alarm",
      "value": "arn:aws:cloudwatch:ap-northeast-2:123456789012:alarm:owned-resilience-stop"
    }
  ],
  "roleArn": "arn:aws:iam::123456789012:role/owned-fis-test"
}
```

例示の宛先 CIDR はレビュー済みのテスト依存先に置き換えてください。このネットワーク操作には特権／root による Fault Injection が必要で、Fargate または Bridge Networking ではサポートされません。IPv4 に影響します。ALL や IPv4 CIDR では IPv6 に影響しません。読み取り専用 root ファイルシステムやコンテナセキュリティ制限を現在の仕様で確認してください。この例を動かすために本番ワークロードのセキュリティ設定を弱めないでください。FIS は Injector Pod を使い、pod-delete 以外のアクションでは Ephemeral Container も使います。プロセスを終了しても、変更できない Ephemeral Container の記録は Pod 仕様から消えません。

#### サブネット 1 つのネットワークを中断

```json
{
  "description": "One owned test subnet network disruption, not a complete AZ outage",
  "targets": {
    "test-subnet": {
      "resourceType": "aws:ec2:subnet",
      "selectionMode": "COUNT(1)",
      "resourceArns": [
        "arn:aws:ec2:ap-northeast-2:123456789012:subnet/subnet-0123456789abcdef0"
      ]
    }
  },
  "actions": {
    "network": {
      "actionId": "aws:network:disrupt-connectivity",
      "parameters": {
        "duration": "PT1M",
        "scope": "all"
      },
      "targets": {
        "Subnets": "test-subnet"
      }
    }
  },
  "stopConditions": [
    {
      "source": "aws:cloudwatch:alarm",
      "value": "arn:aws:cloudwatch:ap-northeast-2:123456789012:alarm:owned-resilience-stop"
    }
  ],
  "roleArn": "arn:aws:iam::123456789012:role/owned-fis-test"
}
```

このサブネットは、管理下にある専用のテストサブネットであり、無関係なワークロードがないことを確認してください。このアクションは NACL を複製して拒否ルールを追加し、完了時に元の関連付けを復元します。scope=all でもサブネット内通信は機能します。AZ の完全な停電を再現するものではありません。開始前に NACL クォータ、IAM、対象サブネット、管理／テレメトリーへのアクセスを確認してください。停止と復旧は非同期です。実験の最終状態と、実際のネットワーク／ワークロード復旧を確認してください。

```bash
# MUTATION: stop only the recorded experiment ID, not all account experiments.
: "${AWS_REGION:?Set the experiment region}"
: "${EXPERIMENT_ID:?Set the exact running FIS experiment ID}"
aws fis stop-experiment --region "$AWS_REGION" --id "$EXPERIMENT_ID"
```
[FIS の EKS Pod 前提条件／RBAC](https://docs.aws.amazon.com/fis/latest/userguide/eks-pod-actions.html) · [アクションのパラメーターとサブネットの挙動](https://docs.aws.amazon.com/fis/latest/userguide/fis-actions-reference.html)

### Litmus Chaos（CNCF インキュベーティング）

レビュー対象の 3.31.0 Operator が定義するのは ChaosEngine、ChaosExperiment、ChaosResult です。ChaosHub や ChaosSchedule は定義しません。これらの Engine 例を使う前に、レビュー済みリリースと必要な ChaosExperiment を、範囲を限定した RBAC および検証済みの Runner／Helper イメージとともにインストールしてください。カタログにある最新の Fault ファイルは CI／latest イメージを既定で使うため、無条件に適用しないでください。スキーマ検証はクラスター／ランタイムとの互換性を証明しません。

次の例は engineState: stop で開始します。対象を準備した後、インストール済みリリースのワークフローで実験を 1 つずつ評価してください。Active な Engine は期間中に Pod を繰り返し削除する可能性があります。期間 30 秒でも、削除がちょうど 1 回とは限りません。固定値 TARGET_PODS は、現在の名前／UID を使って Pod を選ぶまでは未解決のままにします。空欄のままにしたり、本番の selector 全体に広げたりしてはいけません。

#### Pod の削除

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: pod-delete-review
  namespace: resilience-demo
spec:
  engineState: stop
  appinfo:
    appns: resilience-demo
    applabel: app=web-app,experiment-approved=true
    appkind: deployment
  chaosServiceAccount: pod-delete-sa
  experiments:
  - name: pod-delete
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: '30'
        - name: CHAOS_INTERVAL
          value: '10'
        - name: FORCE
          value: 'false'
        - name: TARGET_PODS
          value: REPLACE_WITH_ONE_REVIEWED_POD_NAME
        - name: PODS_AFFECTED_PERC
          value: '100'
```
#### ノードの Drain（インスタンス終了ではありません）

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: node-drain-review
  namespace: resilience-demo
spec:
  engineState: stop
  appinfo:
    appns: resilience-demo
    applabel: app=web-app,experiment-approved=true
    appkind: deployment
  chaosServiceAccount: node-drain-sa
  experiments:
  - name: node-drain
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: '60'
        - name: TARGET_NODE
          value: REPLACE_WITH_ONE_OWNED_TEST_NODE
```

Drain は、アプリケーションの selector を超えて、そのノード上のワークロードに影響します。専用のテストノード、空でない明示的な名前、PDB を考慮した退避動作、復旧／uncordon 計画を使ってください。所有者を問わない kubernetes.io/os=linux のような一般的 selector に置き換えないでください。この実験は EC2 ノードの終了ではありません。

#### DNS エラー

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: pod-dns-error-review
  namespace: resilience-demo
spec:
  engineState: stop
  appinfo:
    appns: resilience-demo
    applabel: app=web-app,experiment-approved=true
    appkind: deployment
  chaosServiceAccount: pod-dns-error-sa
  experiments:
  - name: pod-dns-error
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: '60'
        - name: TARGET_HOSTNAMES
          value: '["backend-service.resilience-demo.svc.cluster.local"]'
        - name: MATCH_SCHEME
          value: exact
        - name: CONTAINER_RUNTIME
          value: containerd
        - name: SOCKET_PATH
          value: /run/containerd/containerd.sock
        - name: PODS_AFFECTED_PERC
          value: '100'
```

TARGET_HOSTNAMES は JSON 配列を表す文字列です。Runtime／Socket／Privilege の前提条件を選択した Linux テストノードに合わせてください。このサンプルはすべての EKS ノード種別で利用できるわけではありません。選択したワークロードの範囲を限定し、この割合で無関係な Pod が対象にならないようにしてください。ChaosResult とアプリケーションのヘルス状態を監視してください。リソースが存在するだけでは実験の成功を示しません。

```bash
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get chaosengine,chaosresult
```
[Litmus Operator 3.31.0](https://github.com/litmuschaos/chaos-operator/releases/tag/3.31.0) · [公式 Fault カタログ](https://github.com/litmuschaos/chaos-charts/tree/master/faults/kubernetes) · [CNCF プロジェクトの状態](https://www.cncf.io/projects/litmus/)

### Chaos Mesh

この例では、リリース 2.8.4 の CRD 形式を使います。インストール前に Helm Chart の Runtime／Socket、ノード選択、Daemon の権限、Dashboard へのアクセス、クラスター互換性を確認してください。特権を要するホスト Fault Injection には、明示的に承認されたテストノードのクラスを使ってください。スキーマが有効だからといって Auto Mode／Fargate／Hybrid Nodes で使えると想定しないでください。

以下の NetworkChaos／IOChaos／TimeChaos は、このリリースの experiment.chaos-mesh.org/pause アノテーションで一時停止します。一時停止したマニフェストを適用する場合も、クラスターへの書き込みが発生します。対象と状態を確認してから、一時停止を別途解除してください。停止するときは復旧状態を待ちます。一時停止で削除済みデータが元に戻るわけではなく、単発 Fault の一時停止動作は異なります。

#### ネットワーク遅延

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: review-network-delay
  namespace: resilience-demo
  annotations:
    experiment.chaos-mesh.org/pause: 'true'
spec:
  action: delay
  mode: fixed
  value: '1'
  selector:
    namespaces:
    - resilience-demo
    labelSelectors:
      app: web-app
      experiment-approved: 'true'
  delay:
    latency: 100ms
    jitter: 50ms
    correlation: '25'
  duration: 1m
```
#### ネットワーク分断

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: review-network-partition
  namespace: resilience-demo
  annotations:
    experiment.chaos-mesh.org/pause: 'true'
spec:
  action: partition
  mode: fixed
  value: '1'
  selector:
    namespaces:
    - resilience-demo
    labelSelectors:
      app: web-app
      experiment-approved: 'true'
  direction: both
  target:
    mode: fixed
    value: '1'
    selector:
      namespaces:
      - resilience-demo
      labelSelectors:
        app: backend
        experiment-approved: 'true'
  duration: 1m
```
#### I/O 遅延

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: IOChaos
metadata:
  name: review-io-delay
  namespace: resilience-demo
  annotations:
    experiment.chaos-mesh.org/pause: 'true'
spec:
  action: latency
  mode: fixed
  value: '1'
  selector:
    namespaces:
    - resilience-demo
    labelSelectors:
      app: web-app
      experiment-approved: 'true'
  volumePath: /audit-data
  delay: 100ms
  percent: 50
  duration: 1m
```

/audit-data にマウントした使い捨てテストボリュームを使ってください。この例では任意のパスフィルターを指定していません。有効化前に対象ファイルを確認してください。percent は注入操作の割合であり、容量の上限ではありません。この例を本番 PostgreSQL の元のデータディレクトリに向けないでください。既知の基準状態から復旧とデータ整合性を確認してください。

#### 時刻のオフセット

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: TimeChaos
metadata:
  name: review-time-offset
  namespace: resilience-demo
  annotations:
    experiment.chaos-mesh.org/pause: 'true'
spec:
  mode: fixed
  value: '1'
  selector:
    namespaces:
    - resilience-demo
    labelSelectors:
      app: web-app
      experiment-approved: 'true'
  timeOffset: -2h
  clockIds:
  - CLOCK_REALTIME
  duration: 1m
```

-2h のオフセットが適用されるのは、選択された注入対象プログラムの CLOCK_REALTIME の挙動です。ノードやすべての時計が一律に 2 時間変更されるわけではありません。トークン、スケジューラー、Lease の挙動を推測する前に、注入機構とアプリケーションの時計の使い方を確認してください。期間は意図した Fault の時間幅を制限するもので、アプリケーションの復旧時間を保証しません。

```bash
kubectl --context "$KUBE_CONTEXT" -n resilience-demo \
  get networkchaos,iochaos,timechaos -o yaml
```
[Chaos Mesh 2.8.4 Chart](https://github.com/chaos-mesh/chaos-mesh/tree/v2.8.4/helm/chaos-mesh) · [Pause Controller](https://github.com/chaos-mesh/chaos-mesh/blob/v2.8.4/controllers/common/desiredphase/controller.go)

### Game Day の枠組み

注入を始める前に、中止基準、独立した観測者、復旧担当者を正確に定めてください。失敗やデータが得られなかった観測を含め、検知と復旧を分けて記録します。次の実験を始める前に 1 つ目を停止し、Fault の期間が過ぎただけで成功とせず、復元を確認してください。

| フェーズ | 作業 | 成果物 |
| --- | --- | --- |
| 1. 定常状態の記録 | メトリクスの基準値を収集する | ダッシュボードのスナップショット |
| 2. 障害の注入 | FIS／Litmus の実験を実行する | 実験ログ |
| 3. 復旧の観測 | 自動復旧の処理を監視する | 復旧時間の測定値 |
| 4. 影響の分析 | エラー率、レイテンシーの変化を分析する | 影響レポート |
| 5. 事後レビュー | 改善点とアクション項目を特定する | 改善計画 |

***

## 実装チェックリスト

### レベル 1: 基本

* [ ] 長時間稼働する各アプリケーションに適したヘルス Probe を選ぶ
* [ ] Resource の要求値／上限値を設定する
* [ ] PodDisruptionBudget を構成する
* [ ] グレースフルシャットダウン（preStop Hook）を実装する
* [ ] 適切な terminationGracePeriodSeconds を設定する

### レベル 2: マルチ AZ

* [ ] Pod Topology Spread Constraints を適用する
* [ ] 実際の Pod／ノード分布と、障害後に残る AZ の余裕容量を確認する
* [ ] ゾーン固定ストレージの復旧を計画し、新規プロビジョニングには WaitForFirstConsumer を使う
* [ ] ARC の適格性、N-1 の準備状況、アラーム、オートシフトを別途承認する運用を確認する
* [ ] AZ 間トラフィックのコストを監視する

### レベル 3: セルベース

* [ ] セル境界（Namespace または Cluster）を定義する
* [ ] セルルーターを実装する
* [ ] セル境界とネットワークプラグインによるポリシー適用を検証する
* [ ] シャッフル・シャーディングを実装する
* [ ] セルごとに ResourceQuota を設定する

### レベル 4: マルチリージョン

* [ ] マルチリージョンのアーキテクチャパターンを決める
* [ ] Global Accelerator を構成する
* [ ] ArgoCD ApplicationSet を使ったマルチクラスター構成をデプロイする
* [ ] データレプリケーション戦略を確立する
* [ ] GitOps による整合性を維持する

***

## コストに関する考慮事項

以下は、以前からある未検証のコスト例を保持したものであり、現在の見積もりや実測した削減額ではありません。AZ 間料金はサービス、トラフィック経路／方向、リージョンによって異なります。$0.01/GB は EKS のあらゆる料金を含む普遍的な単価ではありません。現在のサービス料金ページを使い、実際のリソースと障害用余裕容量の料金を算出してください。コスト／カオスのベンチマークは再実行していません。

| 項目 | コストへの影響 | コスト削減策 |
| --- | --- | --- |
| マルチリージョン・アクティブ／アクティブ | 1 リージョンの場合の 2 倍以上 | アクティブ／パッシブにしてパッシブ側を 50～70% 削減する |
| AZ 間トラフィック | $0.01/GB（同一リージョン内） | ローカリティ対応ルーティングで 60～80% 削減する |
| Spot Instance | On-Demand と比べて 60～90% の削減 | ステートレスなワークロードに適用する |
| カオスエンジニアリング | 以前の月額 $100～500 の例示。実際の FIS／リソース利用量に応じて課金 | 実験のリソースと期間を制限する |
| セルアーキテクチャ | 以前の 10～20% 増の例示 | 分離による負荷と運用価値を測定する |

***

## 次のステップ

* [EKS の高度なデバッグとインシデント対応](11-eks-advanced-debugging.md)
* [EKS 高可用性クイズ](../quizzes/eks/10-eks-resiliency-quiz.md)
* [Istio Service Mesh](../service-mesh/02-istio.md) - Circuit Breaker、Retry の詳細
