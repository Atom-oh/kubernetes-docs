# 運用と管理

> **サポート対象バージョン**: EKS Auto Mode GA。例の基準は EKS 1.36 です。
> **最終更新**: 2026年9月12日

Day 2 の運用では、必要なキャパシティ、Node のライフサイクル、アプリケーションの可用性、実際に収集されるシグナルを区別する必要があります。以下の例は管理されたラボ構成であり、本番環境で検証した運用手順ではありません。この監査ではクラウドリソースを変更せず、稼働中の Node/Pod も実行していません。

NodePool manifest は、リリース済み Karpenter 1.14.1 の構造 schema で検査しました。ワークロードの例は Kubernetes 1.36.2 の構造および Restricted Pod Security policy の検査に合格し、nginx の image tag/index digest と文書化された non-root 構成を確認しました。実行時のイメージ取得、IAM、ネットワーク、アプリケーション動作は、使用環境で別途検証してください。

## 運用コンテキストの確認

一時認証情報と意図した kubeconfig を使用してください。この読み取り専用ガードはアカウントと API endpoint を直接比較します。意図的に proxy を経由する kubeconfig は、不一致を回避するのではなく別途確認してください。

```bash
set -euo pipefail
: "${EXPECTED_ACCOUNT_ID:?Set the intended AWS account}"
: "${AWS_REGION:?Set the cluster region}"
: "${CLUSTER_NAME:?Set the intended cluster name}"
: "${KUBECONFIG:?Set the reviewed kubeconfig path}"
export KUBE_CONTEXT="${KUBE_CONTEXT:-$CLUSTER_NAME}"
check_account() {
  local account
  account=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text) || return
  test "$account" = "$EXPECTED_ACCOUNT_ID" || { printf 'Account mismatch; stop.\n' >&2; return 1; }
}
check_account
umask 077
export WORK_DIR
WORK_DIR=$(mktemp -d "$PWD/auto-ops.XXXXXXXX")
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query 'cluster.{arn:arn,endpoint:endpoint}' --output json > "$WORK_DIR/cluster.json"
endpoint=$(kubectl --context "$KUBE_CONTEXT" config view --minify \
  -o jsonpath='{.clusters[0].cluster.server}')
jq -e --arg endpoint "$endpoint" '.endpoint == $endpoint' "$WORK_DIR/cluster.json" >/dev/null
printf 'Private diagnostic directory: %s\n' "$WORK_DIR"
```

manifest はレビュー済みの `default` NodeClass を前提とします。必要な例だけを選び、リソース名/ネットワーク識別子を意図どおりに置き換え、容量とコストを確認してください。ラボ用 pool には `ops-lab` taint を設定し、ワークロードは対応する toleration/pool selector を使います。これは配置制御であり、tenant 間のセキュリティ境界ではありません。

## Budget は上書きではなく組み合わせて評価される

適用される各 NodePool budget は許容 disruption 数に反映され、その最小値が使われます。常時有効な `10%` budget より、スケジュール済み `30%` budget を追加しても緩和されません。割合は切り上げられ、削除済みまたは NotReady の Node は残りの許容数を減らします。

次の明示的なカレンダーでは、上限を 30%、平日の上限を 10%、営業時間中の上限を 1 Node とします。Karpenter の schedule は UTC です。

| 設定 | UTC の schedule | 意図する時間帯 |
|---|---|---|
| 30% | 常時 | 全体の上限 |
| 10% | 日曜～木曜 15:00、期間 24 時間 | ソウルの月曜～金曜（暦日） |
| 1 Node | 月曜～金曜 00:00、期間 9 時間 | ソウルの営業時間 09:00～18:00 |
| 0 Node | 毎月 1 日 00:00、期間 24 時間 | 明示的な **UTC** 月次凍結 |

それ以外の条件を満たす健全な Node が 20 個ある場合、この例では週末に新たな自発的 disruption を 6 件、平日の営業時間外に 2 件、営業時間中に 1 件、凍結中には 0 件まで許可します。これは例示的な policy であり、一般的な本番推奨値ではありません。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ops-calendar
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
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: ops-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        example: ops-lab
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: 30%
    - nodes: 10%
      schedule: 0 15 * * sun-thu
      duration: 24h
    - nodes: '1'
      schedule: 0 0 * * mon-fri
      duration: 9h
    - nodes: '0'
      schedule: 0 0 1 * *
      duration: 24h
  limits:
    cpu: '100'
    memory: 400Gi
```

以前の時間単位 cron の `9-18`/`9-21` 範囲や、繰り返す 48 時間の週末ウィンドウは、記載された時間を越えて重なっていました。schedule はウィンドウの開始時刻を指定します。長いウィンドウを再開させる対象の時間一覧ではありません。

## Node の置換とアプリケーション可用性

1 Node の budget は、対象となる正常な終了処理をレート制限します。期限到来、中断、修復が必ず順番に行われることは保証しません。`expireAfter` は最低稼働時間の保証ではなく、値を変更しても既存の NodeClaim は書き換わりません。Auto Mode の既定の有効期限/猶予動作と最大寿命も適用されます。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ops-rolling
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: ops-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        example: ops-lab
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 2m
    budgets:
    - nodes: '1'
  limits:
    cpu: '100'
    memory: 400Gi
```

空の Node の consolidation policy は drift や有効期限を無効にしません。`do-not-disrupt` は無期限の保持保証ではありません。Node と Pod の制御は適用範囲が異なり、明示または既定の termination grace period により、処理を妨げる Pod が drift や最終終了に及ぼす影響も変わります。メンテナンス時間帯に使う前に [disruption guide](https://karpenter.sh/v1.14/concepts/disruption/) を確認してください。

### PDB の例

次の namespace は、確認済みの Kubernetes バージョンに対して Restricted policy を固定します。イメージは UID/GID 101 で動作し、8080 を listen し、PID/一時ファイル用に `/tmp` を使います。コンテナの root filesystem が read-only でも、書き込み可能な emptyDir が必要です。このイメージの停止シグナルは SIGQUIT です。root で動作し port 80 を使う nginx image と同じ条件ではありません。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ops-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
  namespace: ops-lab
spec:
  minAvailable: 3
  selector:
    matchLabels:
      app: web-app
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: ops-lab
spec:
  replicas: 5
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: web
        image: nginxinc/nginx-unprivileged:1.30.6@sha256:455cebcadcac0b597cdeaab077d93fb8ad59a98f7ed001dcf8f8693154b5d3d3
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
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
        karpenter.sh/nodepool: ops-calendar
      tolerations:
      - key: ops-lab
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
```

正常な replica を 5 個 desired にして `minAvailable: 3` とすると、他の制約にもよりますが、自発的な Pod eviction を最大 2 つ許可します。`maxUnavailable: 1` は別の、より制限的な選択であり、同じ意味の別表記ではありません。

PDB は正常/Ready Pod を使って Eviction API の判断を制約します。replica を作成するものではなく、あらゆる障害や直接削除から保護するものでもありません。割合は切り上げられます。replica が 6 個の `minAvailable: "80%"` は正常な replica を 5 個要求し、replica が 1 個の `maxUnavailable: "30%"` はその 1 個の eviction を許可することがあります。

stateful system では、アプリケーション固有の quorum と readiness の意味に合わせてください。3 voter の多数決 system なら正常な member 2 個でよい場合がありますが、5 voter system では 3 個必要です。`minAvailable: 2` をすべての stateful workload に適用できるわけではありません。単一 replica の PDB は自発的な drain を意図的に阻止できますが、高可用性を作るものではありません。

## AZ 配置は容量やフェイルオーバーを保証しない

動的 pool の `limits.cpu` は合計上限であり、各 AZ の最低容量ではありません。例には候補 AZ を記載していますが、利用可能な配置は NodeClass の subnet、容量、スケジューリング制約で決まります。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ops-multi-az
spec:
  template:
    spec:
      requirements:
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - ap-northeast-2a
        - ap-northeast-2b
        - ap-northeast-2c
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: ops-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        example: ops-lab
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: high-availability-app
  namespace: ops-lab
spec:
  replicas: 6
  selector:
    matchLabels:
      app: ha-app
  template:
    metadata:
      labels:
        app: ha-app
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: ha-app
        minDomains: 2
        nodeAffinityPolicy: Honor
        nodeTaintsPolicy: Honor
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: ha-app
      containers:
      - name: app
        image: nginxinc/nginx-unprivileged:1.30.6@sha256:455cebcadcac0b597cdeaab077d93fb8ad59a98f7ed001dcf8f8693154b5d3d3
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
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
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: ops-multi-az
      tolerations:
      - key: ops-lab
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
      terminationGracePeriodSeconds: 60
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 128Mi
```

replica が 6 個あるだけでは、3 AZ に 2 個ずつ配置されたことを証明しません。この例には利用可能な failure domain が少なくとも 2 つ必要です。実際の subnet coverage と障害時 policy を評価した上でのみ調整してください。`DoNotSchedule` の hard constraint により AZ 障害時に Pod が Pending のままになることがあります。

各 Node に replica を 1 つずつ置く必要がある場合は、次の affinity 断片をレビュー済み Pod template に追加できます。この制約で replica が 9 個なら、利用可能な Node が少なくとも 9 個必要です。対応する topology と容量がなければ、3 AZ の可用性を証明しません。

```yaml
podAntiAffinity:
  requiredDuringSchedulingIgnoredDuringExecution:
  - labelSelector:
      matchLabels:
        app: ha-app
    topologyKey: kubernetes.io/hostname
```

active-active/standby 設計には、アプリケーション状態、health check、traffic/failover 制御も必要です。ARC zonal shift は Auto Mode でサポートされ、障害中の AZ で新しい容量が作られるのを避けられます。autoshift には別途構成が必要です。AZ に結び付いた volume や hard placement constraint を移動可能にする機能ではありません。

### 既存の容量予約

pool の名前を `reserved-capacity` にし、On-Demand を許可して CPU limit を設定しても、容量予約は作られません。承認済みの既存予約を消費するには、custom NodeClass でその予約を指定し、`reserved` capacity を許可します。例の予約 ID を置き換え、アカウント、AZ、type、status、permission、予約済みの残容量を確認してください。

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: reserved-nodeclass
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
  capacityReservationSelectorTerms:
  - id: cr-0123456789abcdef0
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: reserved-capacity
spec:
  template:
    spec:
      requirements:
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - ap-northeast-2a
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - reserved
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: reserved-nodeclass
      taints:
      - key: ops-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        example: ops-lab
  limits:
    cpu: '100'
    memory: 400Gi
```

これらの manifest は EC2 予約も固定数の Node も作成しません。予約は未使用でも料金が発生することがあります。Pod の需要とは独立した desired Node 数が必要な場合、Auto Mode は `spec.replicas` による static pool をサポートします。limits/weight/consolidation とスケーリングの意味は通常 pool と異なります。static-capacity reference を確認してください。desired 数を設定しても、プロビジョニング成功や健全な容量は保証されません。

## 監視はデータ発行元に合わせる

EKS control-plane metric、構成した Container Insights、自己管理の Prometheus exporter、Auto Mode component log は別々の interface です。以前の `karpenter_*` 名を含む `Karpenter` CloudWatch namespace が自動作成されると想定しないでください。

Auto Mode の管理対象 compute/storage/load balancer/IPAM log は、別途設定する Vended Logs 配信を使います。基本的な control-plane logging を有効にしても、管理対象 component の全 log が有効にはなりません。対象期間を限定し、IAM、配信先、料金を確認してください。

### 実際の metric metadata から dashboard を作成する

`AWS/EKS` control-plane namespace では、まず確認済みクラスターから実際に返される metric を検出します。

```bash
check_account
aws cloudwatch list-metrics --region "$AWS_REGION" --namespace AWS/EKS \
  --dimensions "Name=ClusterName,Value=$CLUSTER_NAME" --output json \
  > "$WORK_DIR/metric-catalog.json"
jq '.Metrics | to_entries | map({index:.key,metric:.value})' "$WORK_DIR/metric-catalog.json"
```

正確な catalog index と、その metric で文書化された適切な statistic を選んでください。次のローカル生成 script は、実際の namespace/dimension を維持し、widget region を含めます。対象 cluster の entry が見つからない場合や誤っている場合、架空の metric panel を作成せずエラーにします。

```bash
: "${METRIC_INDEX:?Choose an exact entry from the captured catalog}"
: "${METRIC_STAT:?Choose the documented statistic for that metric, such as Maximum}"
export METRIC_INDEX METRIC_STAT AWS_REGION CLUSTER_NAME
python3 - <<'PY'
import json, os, re
from pathlib import Path
folder = Path(os.environ["WORK_DIR"])
metrics = json.loads((folder / "metric-catalog.json").read_text())["Metrics"]
index = int(os.environ["METRIC_INDEX"])
if index < 0 or index >= len(metrics):
    raise SystemExit("Metric is absent; verify collection instead of creating an empty widget")
metric = metrics[index]
if metric["Namespace"] != "AWS/EKS" or not any(
    d["Name"] == "ClusterName" and d["Value"] == os.environ["CLUSTER_NAME"]
    for d in metric["Dimensions"]
):
    raise SystemExit("Metric catalog entry does not match the reviewed cluster")
stat = os.environ["METRIC_STAT"]
if stat not in {"Average", "Sum", "Minimum", "Maximum", "SampleCount"}:
    if not re.fullmatch(r"p[0-9]+(?:\.[0-9]+)?", stat) or not 0 <= float(stat[1:]) <= 100:
        raise SystemExit("Unsupported statistic for this template")
series = [metric["Namespace"], metric["MetricName"]]
for dim in sorted(metric["Dimensions"], key=lambda d: d["Name"]):
    series.extend([dim["Name"], dim["Value"]])
body = {"widgets": [{"type": "metric", "x": 0, "y": 0, "width": 12, "height": 6,
    "properties": {"title": metric["MetricName"], "region": os.environ["AWS_REGION"],
                   "view": "timeSeries", "metrics": [series], "stat": stat, "period": 60}}]}
(folder / "dashboard.json").write_text(json.dumps(body, indent=2) + "\n")
PY
```

承認済み手順で dashboard を作成/更新する前に `dashboard.json` を確認してください。catalog に存在することは、すべての時間帯に datapoint がある証拠ではありません。NodePool 数、provisioning latency、アプリケーション SLO には実際の発行元/instrumentation が必要です。Container Insights だけですべてのシグナルが得られると想定しないでください。

## Kubernetes の構造化診断

存在しない `.status.phase` ではなく NodeClaim condition を使い、Pending Pod をすべて Node 容量要求として扱わないでください。

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodeclaims -o json |
  jq '[.items[] | {name: .metadata.name, uid: .metadata.uid, node: .status.nodeName,
      pool: .metadata.labels["karpenter.sh/nodepool"], createdAt: .metadata.creationTimestamp,
      expireAfter: .spec.expireAfter, terminationGracePeriod: .spec.terminationGracePeriod,
      imageID: .status.imageID,
      conditions: [.status.conditions[]? | {type,status,reason,lastTransitionTime,observedGeneration}]}]'
```

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodepools -o json |
  jq '[.items[] | {name:.metadata.name,limits:.spec.limits,resources:.status.resources,
      requirements:.spec.template.spec.requirements,disruption:.spec.disruption,
      conditions:[.status.conditions[]? | {type,status,reason,observedGeneration}]}]'
```

```bash
: "${WORKLOAD_NAMESPACE:?Select the workload namespace}"
: "${POD_NAME:?Select the Pod}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$WORKLOAD_NAMESPACE" \
  get pod "$POD_NAME" -o json |
  jq '{name:.metadata.name,uid:.metadata.uid,node:.spec.nodeName,phase:.status.phase,
       nodeSelector:.spec.nodeSelector,affinity:.spec.affinity,tolerations:.spec.tolerations,
       conditions:[.status.conditions[]? | {type,status,reason,lastTransitionTime}],
       containers:[.status.containerStatuses[]? |
         {name,ready,restartCount,waitingReason:.state.waiting.reason}]}'
```

Node の分布を調べるには、人間向け table 列ではなく構造化 field を解析します。次の集計には割り当て済みだが未 Ready の Pod object も含まれ、Node が割り当てられていない object は別に数えます。

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pods -A -o json |
  jq '[.items[] | select(.status.phase != "Succeeded" and .status.phase != "Failed") |
       {node: (.spec.nodeName // "(unscheduled)"), namespace: .metadata.namespace, pod: .metadata.name}] |
      group_by(.node) | map({node: .[0].node, activePodObjects: length})'
```

metrics API が構成済みで正常な場合に限り `kubectl top` を使ってください。query に失敗しても metrics-server が存在しない証拠にはなりません。event reason と管理対象 compute log で、非互換 instance type、NodeClass readiness、IAM、network など実際の失敗を調べてください。`consolidateAfter` を短くしても Spot interruption の復旧は速くなりません。

### PDB の許容数は compliance 判定ではない

`disruptionsAllowed` が 0 でも、意図どおりで健全な場合があります。判断の前に generation が最新であること、および現在と desired の健全性を確認してください。

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pdb -A -o json |
  jq '[.items[] | {
    namespace: .metadata.namespace, name: .metadata.name,
    currentHealthy: .status.currentHealthy, desiredHealthy: .status.desiredHealthy,
    disruptionsAllowed: .status.disruptionsAllowed,
    assessment: (if .status.observedGeneration != .metadata.generation
                    or .status.currentHealthy == null or .status.desiredHealthy == null
                    or .status.disruptionsAllowed == null
                  then "UnknownOrStale"
                  elif .status.currentHealthy < .status.desiredHealthy then "BelowDesiredHealthy"
                  elif .status.disruptionsAllowed == 0 then "HealthyNoVoluntaryEvictions"
                  else "EvictionsPermitted" end)
  }]'
```

ワークロードの可用性要件と復旧計画を理解する前に、処理を妨げている PDB を削除または緩和しないでください。

### Node object の経過時間

Node object の作成時刻は EC2 の起動時刻でも AMI patch の経過時間でもありません。policy に応じて診断閾値を決めてください。以前の固定値「7 日より古い」script は時間を切り捨て、適切でない一律の上限を仮定していました。

```bash
: "${MAX_NODE_OBJECT_AGE_HOURS:?Set a reviewed diagnostic threshold in hours}"
export MAX_NODE_OBJECT_AGE_HOURS
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/compute-type=auto -o json |
  jq '{items:[.items[] | {name:.metadata.name,createdAt:.metadata.creationTimestamp}]}' \
  > "$WORK_DIR/node-times.json"
python3 - <<'PY'
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
limit = float(os.environ["MAX_NODE_OBJECT_AGE_HOURS"])
if not math.isfinite(limit) or limit <= 0:
    raise SystemExit("Set a finite positive threshold")
now = datetime.now(timezone.utc)
rows = []
for item in json.loads((Path(os.environ["WORK_DIR"]) / "node-times.json").read_text())["items"]:
    result = {"node": item["name"], "thresholdHours": limit}
    try:
        created = datetime.fromisoformat(item.get("createdAt").replace("Z", "+00:00"))
        if created.tzinfo is None or created > now:
            raise ValueError("timestamp is not usable")
        hours = (now - created).total_seconds() / 3600
        result.update(nodeObjectAgeHours=round(hours, 3), exceedsThreshold=hours > limit)
    except (ValueError, TypeError, AttributeError):
        result["assessment"] = "UnknownTimestamp"
    rows.append(result)
print(json.dumps(rows, indent=2))
PY
```

不明または未来の timestamp を健全として報告してはいけません。期限超過と判断する前に、観測した NodeClaim policy、image 情報、AWS のメンテナンス/セキュリティ状況を比較してください。このローカル report は CloudWatch alarm を作成しません。

## セキュリティ設定

Auto Mode は管理対象 Bottlerocket image と固定の IMDSv2/hop-limit 設定を選びます。以前の `amiFamily`、`metadataOptions`、`blockDeviceMappings`、および形式不正な KMS ARN の例は、Auto Mode の有効な NodeClass 構成ではありません。

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: ops-nodeclass
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
```

profile の Node role/access entry、実際の private routing、security-group rule を確認してください。tag だけでは network が制限されている証拠になりません。Node root/data EBS の暗号化が、アプリケーション PVC の暗号化を意味するものでもありません。customer-managed key や CA bundle が必要な場合は、[NodePool 構成](./02-nodepool-configuration.md) の有効な `ephemeralStorage.kmsKeyID`/証明書手順を使い、IAM と key policy を確認してください。

Restricted namespace の例では、互換性のある workload security context が必要です。host access を持つ Node-level monitoring agent を無理に配置したり、agent を動かすためにクラスター全体の security を無効にしたりしないでください。collector の個別 permission と namespace policy を確認します。

## 任意の Prometheus query と alert

次の例は**単一クラスター**、インストール済み kube-state-metrics collector、Linux node-exporter metric を前提とします。利用する前に:

- kube-state-metrics で Node label `karpenter.sh/nodepool` と `eks.amazonaws.com/compute-type` を allowlist にします。
- CPU series に `node` label が正しく対応していることを確認します。すべての node-exporter scrape 構成にこの label が自動で付くわけではありません。
- join/count の前に kube-state-metrics replica の重複を除きます。各 node に対して現在の NodePool label が 1 つ必要です。
- 複数クラスターでは全データソースに実際の cluster label を保持し、すべての grouping/join に含めます。

Node query は Auto Mode Node を filter します。Pod の pending/unschedulable signal はクラスター全体を対象とするため、Auto Mode に原因を帰属させる前に調査が必要です。以下の CPU は **Node ごとの non-idle time** であり、resource request 比率や容量加重 pool 平均ではありません。series がないことを使用量 0 と扱ってはいけません。

```promql
# nodes_by_pool
count by (label_karpenter_sh_nodepool) (max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"}))

# cpu
100 * (1 - avg by (node) (rate(node_cpu_seconds_total{mode="idle",node!=""}[5m])))
* on (node) group_left (label_karpenter_sh_nodepool)
max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"})

# pending
sum(max by (namespace, pod, uid) (kube_pod_status_phase{phase="Pending"}))

# unschedulable
sum(max by (namespace, pod, uid) (kube_pod_status_unschedulable))

# age
((time() - max by (node) (kube_node_created)) / 86400)
* on (node) group_left (label_karpenter_sh_nodepool)
max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"})

# not_ready
max by (node) (kube_node_status_condition{condition="Ready",status=~"false|unknown"})
* on (node) group_left (label_karpenter_sh_nodepool)
max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"})
```

Prometheus Operator を導入済みの場合は、次の rule を Prometheus instance が選択する namespace に置き、その `ruleSelector` に一致させます。閾値と期間は例示です。すべての provisioning failure が termination counter に現れると示す rule ではありません。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: auto-ops-example
  namespace: monitoring
spec:
  groups:
  - name: auto-ops-example
    rules:
    - alert: ReportedUnschedulablePods
      expr: sum(max by (namespace, pod, uid) (kube_pod_status_unschedulable)) > 10
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Reported unschedulable Pods exceed the example threshold
    - alert: AutoNodeNotReady
      expr: '(max by (node) (kube_node_status_condition{condition="Ready",status=~"false|unknown"})

        * on (node) group_left (label_karpenter_sh_nodepool)

        max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"}))
        == 1'
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: A registered Auto Mode node is not Ready
```

## 運用レビューの頻度

| 頻度 | 確認する証跡 |
|---|---|
| 毎日 | 継続する scheduling/NodeClaim error、Node condition、workload health、現在の PDB 許容数、collector の鮮度 |
| 毎週 | disruption/drift event、観測した Node/object の経過時間、実際の容量/Spot 分布、resource request、請求傾向 |
| 変更前/月次 | IAM/network/storage policy、互換性のあるソフトウェアと image 更新、検証済み復旧手順、quota、今後の workload 要件 |

以前の「Pending 0～5 件」、「CPU/memory 80% 未満」、「起動 90 秒未満」、「可用性 99.9%」、応答時間範囲は、未検証の計画用目安であり、Auto Mode の通常範囲や既定 SLO ではありません。すべての遷移や PDB 許容数 0 を違反と扱うのではなく、アプリケーションの目標と実測動作から閾値を決めてください。

## 参考資料

- [Auto Mode NodePool の動作](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Disruption budget、drift、termination](https://karpenter.sh/v1.14/concepts/disruption/)
- [PDB の構成](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [Topology spread constraint](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [Auto Mode の static capacity](https://docs.aws.amazon.com/eks/latest/userguide/auto-static-capacity.html)
- [NodeClass と容量予約の selector](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [EKS ARC zonal shift](https://docs.aws.amazon.com/eks/latest/userguide/zone-shift-enable.html)
- [管理対象 component log の配信](https://docs.aws.amazon.com/eks/latest/userguide/auto-managed-component-logs.html)
- [Control-plane metric と CloudWatch](https://aws.amazon.com/blogs/containers/proactive-amazon-eks-monitoring-with-amazon-cloudwatch-operator-and-aws-control-plane-metrics/)
- [CloudWatch dashboard の構造](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Dashboard-Body-Structure.html)
- [kube-state-metrics の Node metric](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/cluster/node-metrics.md)
- [kube-state-metrics の Pod metric](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/pod-metrics.md)
- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [非 root nginx image](https://github.com/nginx/docker-nginx-unprivileged)

< [前へ: Spot 戦略](./04-spot-strategies.md) | [目次](./README.md) | [次へ: コスト管理](./06-cost-management.md) >
