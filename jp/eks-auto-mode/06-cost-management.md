# コスト管理と最適化

> **対応バージョン**: EKS Auto Mode GA。例は EKS 1.36 向けにレビュー済み
> **最終更新日**: 2026 年 9 月 12 日

コスト最適化には、同等の有用な作業量を対象にした請求データが必要です。ノード数のスナップショット、低い CPU 使用率、広告上の割引だけでは、節約額を測定したことにはなりません。以下の例はソース、スキーマ、CLI の仕様に照らしてローカルで確認しました。購入、クラウドへのデプロイ、実際の請求データ照会は行っていません。

## 請求に含まれる費用

EKS クラスター料金、EC2 使用料、**Auto Mode の追加料金**、EBS、ロードバランサー、NAT／データ転送、可観測性、その他のワークロードサービスを計上します。Auto Mode のコンピューティング料金は秒単位で、最低 1 分間の料金が発生し、EC2 の購入オプションとは別です。EC2 Savings Plans／RI の割引は、別建ての Auto Mode 料金には適用されません。

### 2026 年 7 月の GPU 料金引き下げ

AWS の 7 月の発表によると、7 月 1 日から対応リージョンで G シリーズの **Auto Mode 管理料金**が 35%、P シリーズ／Trainium の料金が 60% 引き下げられ、自動適用されます。これは該当料金項目の引き下げであり、GPU 請求総額が同じ割合で下がるという意味ではありません。また、GPU インスタンス上のローカル NVMe を使ったイメージの並列取得／展開と、アクセラレーターを考慮した修復についても説明されていますが、この例の起動時間やアプリケーション復旧時間を実測したものではありません。

## コストを考慮した配置

[運用](./05-operations.md)で説明した、アカウント／API エンドポイントのガードとプライベートな `WORK_DIR` を先に使ってください。以下の例ではレビュー済みの `default` NodeClass と、互換性のあるキャパシティが利用可能であることを前提とします。デプロイ前に費用を確認してください。

以下の完全なラボ用ワークロードでは、以前の英語例に不足していた selector と image を補っています。運用の章で検証した非 root の nginx image、Restricted 名前空間、pool selector／toleration を使用します。例示する requests は**実測使用量ではありません**。ARM を許可する前に、マルチアーキテクチャ image、ライブラリ、アプリケーションの動作を確認してください。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cost-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-optimized
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
        - r
        - i
        - d
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: cost-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        cost-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cost-efficient-app
  namespace: cost-lab
spec:
  replicas: 5
  selector:
    matchLabels:
      app: cost-efficient
  template:
    metadata:
      labels:
        app: cost-efficient
    spec:
      containers:
      - name: web
        image: nginxinc/nginx-unprivileged:1.30.6@sha256:455cebcadcac0b597cdeaab077d93fb8ad59a98f7ed001dcf8f8693154b5d3d3
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        ports:
        - containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        readinessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 5
      terminationGracePeriodSeconds: 60
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: cost-optimized
      tolerations:
      - key: cost-lab
        operator: Equal
        value: 'true'
        effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 128Mi
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: karpenter.sh/capacity-type
                operator: In
                values:
                - spot
```

Spot と On-Demand の両方を許可するとキャパシティを選択できますが、Pod のソフトな優先設定は特定の割合や即時のフォールバックを保証しません。カテゴリを多様化しても、そのリージョン、NodeClass、ワークロード、実際の在庫状況が許す範囲に限られます。割り込み、GPU、アーキテクチャの制約を別の tier pool で表現できますが、pool を不必要に細分化するとパッキング効率が下がる場合があります。

`WhenEmptyOrUnderutilized` は requests と制約を基に、Pod をより低コストで再スケジュールできるかを評価します。CPU 使用率のしきい値ではありません。`consolidateAfter` は削除までの期限ではなく、処理をまとめるための待ち時間です。PDB、affinity、budget によって統合が妨げられることがあります。pool の CPU／memory limits は要求されるインフラの増加を制限しますが、急速なプロビジョニング中は結果整合性により一時的に超過する場合があります。通貨建ての予算でも、アカウント全体に対する厳密な支出上限でもありません。

## 請求と運用メトリクスを分ける

瞬時のノード gauge は node-hours ではなく、node-hours もインスタンス、単価、時間の情報がなければ金額には換算できません。Auto Mode が、以前の例にあった架空の `Karpenter` CloudWatch コストメトリクスを自動公開することはありません。金額には実際の請求エクスポート／Cost Explorer を使い、キャパシティと性能の把握には設定済みの collector を使ってください。

### CloudWatch の請求概要

請求アラート／メトリクスを有効にすると、世界全体のアカウント請求に対する `AWS/Billing` の推定料金が **us-east-1** で公開されます。これらは当月の累積推定料金であり、日別 EC2 支出、EKS クラスター合計、予測値ではありません。請求を支払う payer account では、リンクされた各アカウントの範囲も考慮してください。このローカルダッシュボード定義では、必要な通貨ディメンションとリージョンを指定しています。

```json
{
  "widgets": [
    {
      "type": "metric",
      "x": 0,
      "y": 0,
      "width": 12,
      "height": 6,
      "properties": {
        "title": "Account estimated charges, month to date (USD)",
        "region": "us-east-1",
        "view": "timeSeries",
        "metrics": [
          [
            "AWS/Billing",
            "EstimatedCharges",
            "Currency",
            "USD"
          ]
        ],
        "period": 21600,
        "stat": "Maximum"
      }
    }
  ]
}
```

サービス／クラスターへの配賦や日ごとの変化には、Cost Explorer／CUR または Data Exports を使ってください。AWS Budgets と Cost Anomaly Detection は、レビュー済みの金額しきい値に対して通知できますが、厳密な支出上限ではありません。ノード数アラームは別のキャパシティ保護策であり、実際に設定された publisher、dimensions、通知先が必要です。古いアラームは架空のメトリクスと未定義の SNS リソースを参照していました。

### Kubecost

レビュー済みの安定版 chart／アプリは **3.2.4** で、新しい repository の chart 名は `kubecost` です。より新しい release candidate を、検証せずにアップグレード先として使わないでください。バージョン 3 は FinOps agent と ClickHouse ベースのアーキテクチャを使います。古い `cost-analyzer` repository、`kubecostToken` のコマンドライン例、バージョン 2 の Prometheus デプロイメントを前提とする設定は流用しないでください。

ライセンス、クラスター識別子、請求連携、範囲を限定したワークロード IAM、認証、保持期間、ストレージに対応したバージョン別の values file を準備します。Auto Mode の EBS StorageClass には `ebs.csi.eks.amazonaws.com` を使います。必要に応じて明示的に選び、暗号化も確認してください。この chart には永続データ保持／keep annotation があるため、uninstall しただけでは課金対象のストレージがすべて削除されたとは限りません。アクセスはプライベートに保ち、collector と telemetry の動作を確認してください。インストール前にローカルで render します。

```bash
: "${KUBECOST_VALUES:?Set the reviewed Kubecost 3.2.4 values file}"
test -f "$KUBECOST_VALUES"
helm repo add kubecost https://kubecost.github.io/kubecost/
helm repo update kubecost
helm show chart kubecost/kubecost --version 3.2.4
helm template cost-review kubecost/kubecost --version 3.2.4 \
  --namespace kubecost --values "$KUBECOST_VALUES" \
  > "$WORK_DIR/kubecost-rendered.yaml"
```

render コマンドは何もインストールしません。Pod／名前空間／アイドルコストへの配賦には agent と対応するデータソースが必要です。実際の請求との照合には AWS integration が必要です。名前空間 label だけでは請求データは生成されません。互換性のない推定値を合算せず、idle／共有コスト、割引、未配賦コストを照合してください。

## Spot の節約額を測定する

この構造化スナップショットは、ノードが 0 台の場合、label 欠損、インスタンスタイプ混在を扱います。数えるのは **Auto Mode の Node object** であり、課金時間や支出ではありません。

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/compute-type=auto -o json |
jq '[.items[] | {
  capacity: (.metadata.labels["karpenter.sh/capacity-type"] // "unknown"),
  instanceType: (.metadata.labels["node.kubernetes.io/instance-type"] // "unknown")
}] as $nodes |
{
  totalNodeObjects: ($nodes | length),
  byCapacityAndType: ($nodes | group_by([.capacity,.instanceType]) |
    map({capacity: .[0].capacity, instanceType: .[0].instanceType, count:length})),
  spotNodePercent: (if ($nodes|length) == 0 then null
    else 100 * ([$nodes[]|select(.capacity=="spot")]|length) / ($nodes|length) end)
}'
```

費用を比較する際は、期間、リージョン／AZ、インスタンス／OS／tenancy、通貨、有用な作業の要件を揃えてください。過去の Spot 料金は AZ と時刻によって変わります。インスタンスタイプだけで選んだ Pricing API の結果は、リージョン／OS／tenancy／product が異なる場合があります。以前の script は API エラーも抑制していました。現在の価格サンプルから、先月の実請求額を復元することはできません。

```text
reference_total = cost of the reviewed On-Demand counterfactual for the same useful work
actual_total = actual compute + Auto Mode fees + other allocated costs
               + recovery costs not already included in those billed components
savings_amount = reference_total - actual_total
savings_percent = 100 * savings_amount / reference_total  (reference_total > 0)
```

中断／再試行された作業と、アイドル状態または未使用の commitment をそれぞれ一度だけ計上し、復旧時のコンピューティングを二重計上しないでください。比較対象には Auto Mode などの別料金も含めます。Spot 割引を 70% と仮定した値や、現在の Spot node 割合を、実際の月間節約額として表示してはいけません。中断イベントは別途記録してください。推測した termination counter の reason では、すべての中断を測定できません。

### 読み取り専用の Cost Explorer

まず AWS が生成する **`aws:eks:cluster-name`** tag を有効にしてください。`eks:cluster-name` は文書化された billing key ではありません。この tag で配賦できるのは対象の EC2 instance の費用であり、**control plane 料金やクラスター関連サービスすべてではありません**。アカウント／payer の範囲と tag の適用状況を確認してください。Cost Explorer API のリクエスト自体にも料金が発生する場合があります。

開始日は範囲に含め、終了日は含めない日付範囲を明示します。このリクエストは金額を表す `AmortizedCost` を使います。単位の異なる `UsageQuantity` を混ぜたり、ノード割合を金額として扱ったりしません。

```bash
: "${COST_START:?Set YYYY-MM-DD inclusive start}"
: "${COST_END:?Set YYYY-MM-DD exclusive end, no later than today UTC}"
export COST_START COST_END CLUSTER_NAME
python3 - <<'PY'
import json, os
from datetime import date, datetime, timezone
from pathlib import Path
start, end = (date.fromisoformat(os.environ[key]) for key in ("COST_START", "COST_END"))
if not start < end <= datetime.now(timezone.utc).date():
    raise SystemExit("Require start < end <= today UTC")
request = {
    "TimePeriod": {"Start": start.isoformat(), "End": end.isoformat()},
    "Granularity": "DAILY",
    "Metrics": ["AmortizedCost"],
    "Filter": {"Tags": {"Key": "aws:eks:cluster-name", "Values": [os.environ["CLUSTER_NAME"]]}},
    "GroupBy": [{"Type": "DIMENSION", "Key": "INSTANCE_TYPE"},
                {"Type": "DIMENSION", "Key": "PURCHASE_TYPE"}]
}
(Path(os.environ["WORK_DIR"]) / "ce-request.json").write_text(json.dumps(request, indent=2) + "\n")
PY
```

```bash
check_account
aws ce get-cost-and-usage --region us-east-1 \
  --cli-input-json "file://$WORK_DIR/ce-request.json" \
  --output json > "$WORK_DIR/ce-result.json"
jq '[.ResultsByTime[] | {period:.TimePeriod,estimated:.Estimated,groups:.Groups}]' \
  "$WORK_DIR/ce-result.json"
```

`Estimated` flag を保持し、返金、credit、割引配賦、未確定データを考慮してください。tag で絞った結果には、未配賦料金や未使用 commitment が含まれない場合があります。合計や節約額を主張する前に、完全な請求データと照合してください。

## リソースの適正化

固定した [VPA 1.8.0 のインストールガイド](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.8.0/vertical-pod-autoscaler/docs/installation.md)を使ってください。VPA 1.8.x の文書化された互換性は Kubernetes 1.36～1.38 で、特定の in-place 機能には追加要件があります。古い `releases/latest/download/...` URL は有効な VPA インストール手順ではありません。クラスター全体にインストール用 script を適用する前に、CRD、RBAC、metrics-server、各 component／certificate の設定を確認してください。`Off` モードでも recommender は動作している必要があります。

このリソースは同じ名前空間にある実際のラボ Deployment を対象にします。

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: cost-app-vpa
  namespace: cost-lab
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cost-efficient-app
  updatePolicy:
    updateMode: 'Off'
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: '4'
        memory: 8Gi
```

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n cost-lab \
  get vpa cost-app-vpa -o json |
  jq '{conditions:.status.conditions,recommendations:.status.recommendation.containerRecommendations}'
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n cost-lab \
  get deployment cost-efficient-app -o json |
  jq '[.spec.template.spec.containers[] | {name,resources}]'
```

`Off` は推奨値を提示しますが、自動適用はしません。すべての container、推奨値の condition／履歴、ワークロードの季節性、起動時のピーク、latency、CPU throttling、memory／OOM の挙動を確認してください。`resourcePolicy` の上限は、推奨値が既存の limit に適合する証拠ではありません。VPA は性能を保証しません。また、レビュー済みのこのリリースには Pod レベルの resource stanza に関する制限も記載されています。

### Kubernetes の quantity 単位を維持する

CPU の `1` は 1 core、`1m` は 1 millicore です。`1Gi` は 1024Mi です。suffix を削除しても、どちらの単位も変換されません。古い `sed`／`awk` の合計処理を使わず、各 container の raw request／limit と使用量を snapshot に記録してください。

```bash
: "${WORKLOAD_NAMESPACE:?Select a namespace}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$WORKLOAD_NAMESPACE" \
  get pods -o json |
  jq '[.items[] | {pod:.metadata.name,uid:.metadata.uid,
    podResources:.spec.resources,overhead:.spec.overhead,
    containers:[.spec.containers[]|{name,resources}],
    initContainers:[.spec.initContainers[]?|{name,restartPolicy,resources}]}]' \
  > "$WORK_DIR/pod-requests.json"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$WORKLOAD_NAMESPACE" \
  top pods --containers > "$WORK_DIR/container-usage.txt"
```

メトリクスクエリが成功する必要があります。データ欠損は使用率 0 を意味しません。この 2 つの snapshot は同時点のものではなく、container の使用量だけでは scheduler が計算する Pod の完全な request を表しません。init／restartable-init container、Pod レベルの resource、overhead も関係します。

| 観測内容 | 確認・対応 |
|-------------|---------------|
| request が代表的な使用量の 2 倍を超える | 削減前にピークと SLO の余裕を調査する。20～50% の節約が自動的に得られるわけではない |
| request が使用量の 2 倍以内 | 最適である証拠にはならない |
| 使用量が request を超える | スケジューリングと余裕を評価する。OOM の強制に関係するのは単なる request ではなく memory **limit** |
| limit が request を大きく上回る | burst／throttling／OOM の方針を評価する。limit だけ下げても通常 request ベースの packing は改善しない |

### 任意の Prometheus レビュー候補

以下の情報提供用ルールは、**単一クラスター**で、CPU core／memory byte に正規化された kube-state-metrics と、namespace／Pod／container label を持つ container レベルの cAdvisor 使用量があることを前提とします。CPU query には集約済みの `cpu="total"` series が必要です。利用中の collector の label を確認してください。これらのルールは collector replica を重複排除し、インフラ cgroup を除外し、request の分母が正の場合だけを対象にします。複数クラスターでは、各 grouping／join に実際の cluster label を指定してください。series 欠損を 0 として扱いません。stale series／container 再作成の影響と代表期間の履歴を確認してください。

使用率 30% が 1 時間続くというしきい値は、レビュー開始のための例示であり、request の削減を自動推奨したり節約額を実測したりするものではありません。この resource を使う前に Prometheus Operator をインストールし、namespace／rule selector を一致させてください。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: cost-review-candidates
  namespace: monitoring
spec:
  groups:
  - name: cost-review-candidates
    rules:
    - alert: LowCpuRequestUtilization
      expr: "((\n  sum by (namespace,pod) (max by (namespace,pod,container) (rate(container_cpu_usage_seconds_total{cpu=\"\
        total\",container!=\"\",container!=\"POD\",image!=\"\"}[5m])) and on (namespace,pod,container)\
        \ max by (namespace,pod,container) (kube_pod_container_resource_requests{resource=\"\
        cpu\",unit=\"core\"}))\n  / sum by (namespace,pod) (max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"cpu\",unit=\"core\"}))\n\
        ) and on (namespace,pod) (sum by (namespace,pod) (max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"cpu\",unit=\"core\"}))\
        \ > 0)\nunless on (namespace,pod) count by (namespace,pod) (\n  max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"cpu\",unit=\"core\"}) unless\
        \ on (namespace,pod,container) max by (namespace,pod,container) (rate(container_cpu_usage_seconds_total{cpu=\"\
        total\",container!=\"\",container!=\"POD\",image!=\"\"}[5m]))\n)) < 0.3"
      for: 1h
      labels:
        severity: info
      annotations:
        summary: Review request sizing; do not automatically reduce it
    - alert: LowMemoryRequestUtilization
      expr: "((\n  sum by (namespace,pod) (max by (namespace,pod,container) (container_memory_working_set_bytes{container!=\"\
        \",container!=\"POD\",image!=\"\"}) and on (namespace,pod,container) max by\
        \ (namespace,pod,container) (kube_pod_container_resource_requests{resource=\"\
        memory\",unit=\"byte\"}))\n  / sum by (namespace,pod) (max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"memory\",unit=\"byte\"\
        }))\n) and on (namespace,pod) (sum by (namespace,pod) (max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"memory\",unit=\"byte\"\
        })) > 0)\nunless on (namespace,pod) count by (namespace,pod) (\n  max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"memory\",unit=\"byte\"\
        }) unless on (namespace,pod,container) max by (namespace,pod,container) (container_memory_working_set_bytes{container!=\"\
        \",container!=\"POD\",image!=\"\"})\n)) < 0.3"
      for: 1h
      labels:
        severity: info
      annotations:
        summary: Review request sizing; do not automatically reduce it
```

## Savings Plans と Reserved Instances

| オプション | 対象となる使用量／範囲 | 主な制約 |
|--------|------------------------|----------------------|
| Compute Savings Plans | family、size、region、OS、tenancy をまたぐ対象 EC2 使用量。Fargate／Lambda も対象 | 最大 66% は広告上の上限であり、想定割引ではない |
| EC2 Instance Savings Plans | 1 つの region 内で選んだ instance family。範囲内で size／OS／tenancy に柔軟性がある | 最大 72%。特定の instance size 1 種への commitment ではない |
| EC2 RI | 対象使用量。region 内の size 柔軟性／交換条件は offering によって異なる | 既存の対象 commitment も Auto Mode で利用できる場合がある |
| Spot | Spot 固有の料金 | Savings Plans との重ね掛けはできない |

対象となる Graviton と GPU の EC2 使用量に、特別な「ARM Savings Plan」は不要で、GPU を一律除外する必要もありません。SageMaker AI Savings Plans の対象は SageMaker の使用量です。ML を実行するという理由だけで EC2 GPU node が対象になるわけではありません。Savings Plans は物理キャパシティを予約しないため、キャパシティ予約は別に評価してください。別建ての Auto Mode 料金は、これらの EC2 割引の対象外です。

commitment の規模は、未カバーで継続的に発生している対象使用量から、該当 Savings Plans rate による **USD／時間**で見積もってください。基準値がすでに Spot を除外しているなら、さらに `(1 - Spot%)` を掛けないでください。既存の RI／SP coverage、今後の適正化／アーキテクチャ変更、sharing 設定、季節性、未使用 commitment を考慮してください。EC2 単価やノード数が下がるだけでは、安全に購入できる根拠になりません。

```bash
check_account
aws ce get-savings-plans-purchase-recommendation --region us-east-1 \
  --savings-plans-type COMPUTE_SP --term-in-years ONE_YEAR \
  --payment-option NO_UPFRONT --lookback-period-in-days THIRTY_DAYS \
  --output json > "$WORK_DIR/savings-plan-recommendation.json"
```

これは推奨値を取得するものであり、購入ではありません。30 日の lookback は API で選択できるオプションです。購入判断の前に、より長い代表期間の履歴とも比較してください。

以前の図にあった Compute coverage 60～70%／70%、EC2 Instance coverage 30～40%、On-Demand coverage 50%、Spot 40～60%／covered 30～40%／uncovered 10～20% は、**検証されていない計画例**であり、普遍的な加算可能目標ではありません。ワークロードは Spot または On-Demand のキャパシティ上で実行されます。Savings Plans は対象使用量に対する請求上の coverage であり、第三のノード種別ではありません。

## コスト配賦

有効な NodeClass の identity／network selector と、承認済みの tag 付与権限を使用してください。custom NodeClass には、その node-role の access entry が必要です。tag はリソースを説明するものであり、ネットワーク分離を作ったり、依存するサービスすべてに自動適用したりはしません。

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: tagged-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      Name: private-subnet
  securityGroupSelectorTerms:
  - tags:
      Name: worker-restricted
  advancedNetworking:
    associatePublicIPAddress: false
  ephemeralStorage:
    size: 100Gi
    iops: 3000
    throughput: 125
  tags:
    Environment: lab
    Team: platform
    Project: web-services
    CostCenter: CC-12345
    Application: cost-lab
    ManagedBy: eks-auto-mode
```

この例を使うには、意図した pool から `tagged-nodeclass` を明示的に参照してください。`amiFamily: AL2023` は Auto Mode の NodeClass field ではありません。実際のリソースに tag が付いていることを確認し、Billing で該当 key を有効化してください。ユーザー定義 key は、有効化対象として表示されるまで最大 24 時間、その後有効になるまでさらに最大 24 時間かかる場合があります。レポートの反映速度は別の要素です。データがちょうど 24 時間後に揃うとは保証できません。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
  labels:
    cost-center: team-a
    environment: production
```

名前空間 label は Kubernetes の配賦ツールに利用できますが、AWS の cost-allocation tag に自動伝播するわけではありません。EC2 の tag による配賦も、共有費用／control plane／storage／network の費用配賦の代わりにはなりません。

## 最適化チェックリストと過去の数値例

互換性のあるインスタンスの多様性、ワークロードに応じた Spot 利用、実測に基づく request の調整、実現可能な統合、請求連携、commitment のレビューを別々の作業項目として扱ってください。変更の前後で、有用な作業あたりの総費用と可用性を測定します。

以下の以前の推定値には、検証済みのベンチマーク／請求データの出典がありません。参考情報として残しますが、保証値ではなく、合計して節約額を主張したり、乗算したりしてはいけません。

| 過去の項目 | 元の例示範囲 |
|-------------|-------------------------|
| Spot | 60～70%、60～90%、70～90% |
| ARM／Graviton | 20% |
| request 調整／VPA | 10～30%、15～30%、20～40%、20～50% |
| 統合 | 10～20%、10～30% |
| Savings Plans | 20～30%、20～40% |
| Multi-AZ／スケジューリング | 5～10%／10～20% |

AZ の耐障害性を下げることは、一般的なコスト最適化ではありません。配置／スケジューリングの実験では、データ転送、障害復旧、ストレージ保持、ワークロードの目標を含めてください。

## 参考資料

- [EKS の料金と Auto Mode 料金](https://aws.amazon.com/eks/pricing/)
- [2026 年 7 月の GPU 管理料金引き下げ](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-eks-auto-mode-gpu-price/)
- [Auto Mode のコスト制御](https://docs.aws.amazon.com/eks/latest/userguide/auto-cost-control.html)
- [NodePool のリソース上限と disruption](https://karpenter.sh/v1.14/concepts/nodepools/)
- [Savings Plans の種類](https://docs.aws.amazon.com/savingsplans/latest/userguide/plan-types.html)
- [Savings Plans と RI の比較](https://docs.aws.amazon.com/savingsplans/latest/userguide/sp-ris.html)
- [EKS の請求 tag](https://docs.aws.amazon.com/eks/latest/userguide/eks-using-tags.html)
- [Cost allocation tag の有効化](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/activating-tags.html)
- [CloudWatch の請求額推定](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/monitor_estimated_charges_with_cloudwatch.html)
- [Kubecost 3.2.4 chart](https://kubecost.github.io/kubecost/kubecost-3.2.4.tgz)
- [VPA 1.8.0 のインストール](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.8.0/vertical-pod-autoscaler/docs/installation.md)
- [VPA の既知の制限](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.8.0/vertical-pod-autoscaler/docs/known-limitations.md)
- [Kubernetes の resource 単位とスケジューリング](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Auto Mode の NodeClass と tag](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)

< [前へ: 運用](./05-operations.md) | [目次](./README.md) | [次へ: Node Lifecycle](./07-node-lifecycle.md) >
