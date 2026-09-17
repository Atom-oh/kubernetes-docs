# スケジューリング、Preemption、Eviction クイズ

このクイズでは、Kubernetes のスケジューリング、ノード選択、affinity、taint、優先度、eviction、disruption budget、descheduling を扱います。

## 多肢選択問題

1. 候補ノードを評価する際、filtering、scoring、binding のうち最初に行われるのはどれですか？
   - A) ノードの scoring
   - B) ノードの filtering
   - C) Pod の優先度の決定
   - D) Binding

<details>
<summary>回答を表示</summary>

**回答: B) ノードの filtering**

**解説:**
Scheduler は不適切なノードを filter し、実行可能なノードを score し、ノードを選択して Pod を bind します。Queueing やその他の framework extension point は、これらのステップを取り囲みます。
</details>

2. node affinity と Pod affinity の主な違いは何ですか？
   - A) node affinity は hard constraint のみをサポートし、Pod affinity は soft constraint のみをサポートする
   - B) node affinity は node label に一致させ、Pod affinity は一致する Pod に関連して配置する
   - C) node affinity は cluster 全体、Pod affinity は namespace 全体に適用される
   - D) Pod affinity だけが実行時に自動的に配置を変更する

<details>
<summary>回答を表示</summary>

**回答: B) node affinity は node label に一致させ、Pod affinity は一致する Pod に関連して配置する**

**解説:**
どちらも required ルールと preferred ルールをサポートします。Pod affinity は一致する Pod と topology key を使用して co-location を表現します。label が変更されても、IgnoredDuringExecution が Pod を自動的に eviction することはありません。
</details>

3. taint と toleration の目的は何ですか？
   - A) Pod が特定の 1 つのノードでのみ実行されることを保証する
   - B) 一致する toleration がない限り、ノードが Pod を排除できるようにする
   - C) Pod 間 affinity を設定する
   - D) cluster 利用率を自動的に最適化する

<details>
<summary>回答を表示</summary>

**回答: B) 一致する toleration がない限り、ノードが Pod を排除できるようにする**

**解説:**
Toleration により taint されたノードを検討できるようになりますが、Pod をそのノードへ引き寄せたり、配置を保証したりするものではありません。専用 workload には node affinity と組み合わせ、toleration を使用できるユーザーを制御してください。
</details>

4. Pod priority と preemption はどのように関係しますか？
   - A) より高い priority の Pod は、スケジューリング中により低い priority の Pod を preempt できる場合がある
   - B) Priority は CPU/memory allocation を直接設定する
   - C) Preemption は maintenance 中にのみ発生する
   - D) 両者は無関係である

<details>
<summary>回答を表示</summary>

**回答: A) より高い priority の Pod は、スケジューリング中により低い priority の Pod を preempt できる場合がある**

**解説:**
Pending 状態の Pod をスケジュール可能にできる場合、scheduler はより低い priority の victim を削除できます。これは capacity や配置を保証するものではありません。`preemptionPolicy: Never` を持つ PriorityClass は、他の Pod を preempt しません。
</details>

5. nodeSelector と node affinity はどのように異なりますか？
   - A) nodeSelector は hard constraint であり、node affinity は hard constraint と soft constraint をサポートする
   - B) nodeSelector は 1 つの label のみをサポートする
   - C) Node affinity は label value に一致させられない
   - D) nodeSelector はスケジューリング後にのみ適用される

<details>
<summary>回答を表示</summary>

**回答: A) nodeSelector は hard constraint であり、node affinity は hard constraint と soft constraint をサポートする**

**解説:**
Node affinity はさらに In、NotIn、Exists、DoesNotExist、Gt、Lt をサポートします。すべての nodeSelector エントリが一致する必要があります。Required node affinity は一致する必要があり、preferred ルールは score に影響します。
</details>

6. node-pressure eviction を一般的に引き起こす条件はどれですか？
   - A) Pod 自体の priority value が低い
   - B) ノードの memory、disk space、またはその他の監視対象 resource が不足している
   - C) Pod が単に長期間存在している
   - D) ReplicaSet の replica が多すぎる

<details>
<summary>回答を表示</summary>

**回答: B) ノードの memory、disk space、またはその他の監視対象 resource が不足している**

**解説:**
Kubelet は pressure signal を監視し、resource を reclaim して Pod を終了する場合があります。候補の順序では、request を超える使用量、Pod priority、相対使用量が考慮され、固定の QoS のみの順序ではありません。その他の eviction mechanism には drain と NoExecute taint があります。
</details>

7. DaemonSet Pod はどのように配置されますか？
   - A) 対象として適格な各ノードに 1 つの Pod
   - B) control-plane ノード上のみ
   - C) 常に kube-scheduler を bypass する
   - D) replica 数は適格なノード数と無関係である

<details>
<summary>回答を表示</summary>

**回答: A) 対象として適格な各ノードに 1 つの Pod**

**解説:**
DaemonSet controller は適格なノードを対象とする Pod を作成し、scheduler がそれらを bind します。Selector、affinity、toleration、capacity も依然として重要です。現在の DaemonSet を説明する際に、過去の direct-binding 動作を使用すべきではありません。
</details>

8. Pod レベルの resource 設定がない場合、すべての container で CPU request/limit が等しく、memory request/limit も等しいときに適用される QoS class はどれですか？
   - A) BestEffort
   - B) Burstable
   - C) Guaranteed
   - D) Critical

<details>
<summary>回答を表示</summary>

**回答: C) Guaranteed**

**解説:**
Guaranteed では、すべての container で CPU および memory の request/limit が等しくなります。BestEffort にはどちらもなく、中間的な構成は Burstable です。QoS は PriorityClass ではなく、あらゆる failure や pressure condition における存続を保証するものでもありません。
</details>

9. `node-role.kubernetes.io/control-plane:NoSchedule` で taint されたノードをスケジューリング対象として検討できるようにするものは何ですか？
   - A) node affinity のみ
   - B) Pod affinity のみ
   - C) 一致する toleration
   - D) より高い PriorityClass のみ

<details>
<summary>回答を表示</summary>

**回答: C) 一致する toleration**

**解説:**
Toleration は taint を許容しますが、resource とその他の配置 constraint は引き続き満たす必要があります。control-plane への配置は、意図した workload に対してのみ使用してください。

```yaml
tolerations:
- key: "node-role.kubernetes.io/control-plane"
  operator: "Exists"
  effect: "NoSchedule"
```
</details>

10. PodDisruptionBudget が主に制御するものは何ですか？
   - A) Container の resource consumption
   - B) Eviction API を介した voluntary eviction
   - C) Scheduling priority
   - D) Container の restart policy

<details>
<summary>回答を表示</summary>

**回答: B) Eviction API を介した voluntary eviction**

**解説:**
PDB は、通常の drain/descheduler operation を含む、許可される Eviction API request を制限します。直接的な Pod deletion、workload-controller rollout、node-pressure eviction はこの gate を bypass します。PDB は healthy な replica を作成せず、node failure を防ぐものでもありません。
</details>

## 短答問題

1. 少なくとも 3 つの scheduler Filter plugin を説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

- **NodeResourcesFit** は、要求された resource を node allocatable capacity および既存の request と照合します。
- **NodeAffinity** は required node selection rule を確認します。**NodeUnschedulable** は、関連する toleration が適用されない限り cordon されたノードを拒否します。
- **InterPodAffinity** は Pod affinity と anti-affinity の両方を確認します。**PodTopologySpread** は hard spread constraint を確認します。
- **TaintToleration** は taint を確認します。**NodePorts** は host-port conflict を検出します。
- **VolumeBinding** は PVC binding/topology を確認します。**NodeVolumeLimits** は CSI attachment limit を確認します。
- 直接割り当てられた `spec.nodeName` は通常 scheduler を bypass します。NodeName を最高優先度の filter と説明すべきではありません。

EBSLimits などの古い provider ごとの名前は、現在の CSI plugin 名ではありません。
</details>

2. 専用 GPU node に対して、node affinity と taint/toleration がどのように連携するか説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

Node affinity は workload を意図したノードに制限し、taint は一致する toleration がない Pod を排除します。たとえば、実際の GPU node に label を付け、一致する GPU label を必須にし、ノードを taint し、承認された GPU workload でのみその taint を tolerate します。

Toleration だけでは GPU node への配置を保証しません。GPU を予約するには、`nvidia.com/gpu: 1` のような GPU request と動作する device plugin も必要です。この分離が security boundary である場合は、toleration/label を追加できるユーザーを制限する必要があります。
</details>

3. Pod priority と preemption について、その制限を含めて説明してください。

<details>
<summary>回答を表示</summary>

**回答:**

PriorityClass を作成し、`spec.priorityClassName` で参照します。Scheduler queue は priority を使用し、より低い priority の victim を削除することで Pending Pod が実行可能になる場合、preemption はその victim を選択できます。

Scheduler は API を通じて victim の deletion を要求します。Kubelet/runtime が termination を実行します。Victim の termination により到着する Pod が遅延する可能性があり、nominated node は無条件の予約ではありません。Preemption は同じかより高い priority の Pod を削除せず、affinity または capacity constraint を解決できない場合もあります。

PDB は best-effort ベースで考慮され、保証はされません。ユーザー定義の priority value は 1,000,000,000 以下である必要があります。system class には予約済みのより高い value があります。単に kube-system で実行しているだけでは、Pod が exempt になるわけではありません。event を確認し、影響をテストしてください。

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: "This priority class should be used for critical production workloads."
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: critical-pod
spec:
  priorityClassName: high-priority
  containers:
  - name: web-server
    image: nginx
```
</details>

4. node-pressure eviction、Eviction API request、taint ベースの deletion を区別してください。

<details>
<summary>回答を表示</summary>

**回答:**

**Node pressure:** Kubelet は memory、filesystem、PID の可用性を監視し、Pod を終了する前に resource を reclaim する場合があります。一般的な Linux の hard default には、memory.available が 100Mi 未満、nodefs.available が 10% 未満、imagefs.available が 15% 未満、free inode が 5% 未満などがあります。PID には default の 10% threshold はありません。Windows の memory default は異なります。

**Soft と hard の比較:** Soft threshold とその grace period は明示的に設定する必要があります。Hard threshold は graceful period なしに Pod を終了できます。Soft termination も evictionMaxPodGracePeriod によって制限されます。default を override する場合は、意図したすべての threshold を保持してください。

**Eviction API:** 通常の drain と互換性のある automation は、policy/v1 Eviction request を送信します。PDB はこれらの request を gate します。直接的な Pod DELETE は異なり、PDB check を bypass します。

**Taint ベースの deletion:** NoExecute taint は、それを tolerate しない Pod を削除できます。通常の Pod には一般に 300 秒の not-ready/unreachable toleration があります。これは kubelet pressure eviction および Eviction API gate とは別のものです。

Eviction は Pod を終了させます。workload controller は新しい UID の replacement を作成する場合があります。同じ Pod を別の node に安全に移動する mechanism はありません。可用性には replica、storage/capacity planning、テスト済みの failure handling が必要です。
</details>

5. 現在の DaemonSet scheduling は Deployment Pod scheduling とどのように異なりますか？

<details>
<summary>回答を表示</summary>

**回答:**

DaemonSet controller は適格な各 node に対して 1 つの Pod を作成し、target-node affinity を設定します。Scheduler が binding を実行します。一方 Deployment は ReplicaSet を通じて望ましい replica 数を維持し、resource と constraint に基づいて配置します。Pod 数は node ごとに 1 つではありません。

DaemonSet は、期限のない not-ready/unreachable NoExecute toleration を含む、node condition に対する複数の自動 toleration を取得します。すべての resource constraint を bypass するわけではなく、taint されたすべての control-plane node で自動的に実行されるわけでもありません。
</details>

## ハンズオン問題

1. us-east-1a または us-east-1b を必須とし、m5.large node を優先する nginx:1.30.4 を使用した web-server という名前の Pod を作成してください。

<details>
<summary>回答を表示</summary>

**回答:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-server
spec:
  containers:
  - name: nginx
    image: nginx:1.30.4
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: topology.kubernetes.io/zone
            operator: In
            values:
            - us-east-1a
            - us-east-1b
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 1
        preference:
          matchExpressions:
          - key: node.kubernetes.io/instance-type
            operator: In
            values:
            - m5.large
```

Required node affinity は適格な zone を制限します。Preferred node affinity は m5.large に対する scoring preference を追加します。標準 label は cloud/node integration によって設定されます。選択した cluster node に実際にそれらがあることを確認してください。
</details>

2. worker-1 に dedicated=database:NoSchedule を taint し、postgres-db Pod に一致する toleration を与えてください。

<details>
<summary>回答を表示</summary>

**回答:**

```bash
kubectl taint nodes worker-1 dedicated=database:NoSchedule
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: postgres-db
spec:
  containers:
  - name: postgres
    image: postgres:17
    env:
    - name: POSTGRES_PASSWORD
      valueFrom:
        secretKeyRef:
          name: postgres-credentials
          key: password
  tolerations:
  - key: "dedicated"
    operator: "Equal"
    value: "database"
    effect: "NoSchedule"
```

最初に同じ namespace 内で password key を含む postgres-credentials を作成してください。この例は scheduling を示すものであり、永続 database storage はありません。永続的な利用には PVC を追加してください。Toleration は worker-1 を許可しますが、そこへの配置を強制するものではありません。
</details>

3. nginx:1.30.4 を使用する 3 replica の web-frontend Deployment を作成し、app=cache Pod と co-locate しつつ、自身の replica とは分離してください。

<details>
<summary>回答を表示</summary>

**回答:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
    spec:
      affinity:
        podAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - cache
            topologyKey: "kubernetes.io/hostname"
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - web-frontend
            topologyKey: "kubernetes.io/hostname"
      containers:
      - name: nginx
        image: nginx:1.30.4
```

Required Pod affinity と anti-affinity は namespace 内で適用されます。3 つすべての replica をスケジュールするには、少なくとも 3 つの適格な node に一致する cache Pod が存在する必要があります。そうでない場合、replica は Pending のままになる可能性があります。これらの rule は label の変更後に既存 Pod を自動的に移動しません。
</details>

4. value 100000 の high-priority と、request と limit の両方で CPU 500m、memory 512Mi を持つ Guaranteed QoS の critical-service Pod を作成してください。

<details>
<summary>回答を表示</summary>

**回答:**

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 100000
globalDefault: false
description: "This priority class is for critical services that should be scheduled first."
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: critical-service
spec:
  priorityClassName: high-priority
  containers:
  - name: nginx
    image: nginx:1.30.4
    resources:
      requests:
        cpu: 500m
        memory: 512Mi
      limits:
        cpu: 500m
        memory: 512Mi
```

Priority は queueing/preemption に影響します。container 上で CPU および memory の request/limit が等しい場合、container-level の Guaranteed criteria を満たします。priority も QoS も、node failure や eviction に対する免除を保証しません。
</details>

5. minAvailable: 2 で app=web-server Pod 用の web-pdb を作成してください。

<details>
<summary>回答を表示</summary>

**回答:**

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web-server
```

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: web-server
```

PDB は通常の Eviction API request を gate するため、voluntary eviction によって現在の健全性がその budget を下回ることはありません。代替の maxUnavailable: 1 は、望ましい replica が 3 つの場合にのみ同じ効果を持ちます。直接的な deletion、rolling update、involuntary failure は保護しません。
</details>

## 上級トピック

1. 選択した Pod に対して別の scheduler を実行する一般的な方法はどれですか？
   - A) policy を変更するたびに kube-scheduler を rebuild する
   - B) scheduler を deploy し、schedulerName で選択する
   - C) すべての Pod に任意の annotation を追加する
   - D) kubelet で local scheduling を有効にする

<details>
<summary>回答を表示</summary>

**回答: B) scheduler を deploy し、schedulerName で選択する**

**解説:**
一致する scheduler は、適切な RBAC と互換性のある configuration で実際に実行されている必要があります。schedulerName だけでは scheduler は install されません。Scheduler は Pod/node を watch して適格な Pending Pod を bind します。kubelet は配置を選択しません。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: custom-scheduled-pod
spec:
  schedulerName: my-custom-scheduler
  containers:
  - name: container
    image: nginx
```
</details>

2. Descheduler strategy ではないものはどれですか？
   - A) LowNodeUtilization
   - B) RemoveDuplicates
   - C) PodLifeTimeExtension
   - D) RemovePodsViolatingInterPodAntiAffinity

<details>
<summary>回答を表示</summary>

**回答: C) PodLifeTimeExtension**

**解説:**
PodLifeTime は一致する古い Pod を eviction します。その lifetime を延長するものではありません。その他の strategy には NodeAffinity、topology-spread、restart-count check があります。LowNodeUtilization は通常、要求 resource を node capacity と比較します。Descheduler は eviction を行います。controller が replacement を作成し、kube-scheduler が配置を選択しますが、別の node になるとは限りません。
</details>

3. 標準で自動適用される node-condition taint ではないものはどれですか？
   - A) node.kubernetes.io/not-ready
   - B) node.kubernetes.io/unreachable
   - C) node.kubernetes.io/disk-pressure
   - D) node.kubernetes.io/high-load

<details>
<summary>回答を表示</summary>

**回答: D) node.kubernetes.io/high-load**

**解説:**
現在の標準 taint には、not-ready、unreachable、memory-pressure、disk-pressure、pid-pressure、network-unavailable、unschedulable があります。古い out-of-disk taint は、現在の自動 taint ではありません。Pressure taint は一般に NoSchedule を使用します。not-ready/unreachable の NoExecute 動作と kubelet pressure eviction は別の mechanism です。
</details>

4. topology spread constraint に関する記述で誤っているものはどれですか？
   - A) label 付けされた zone、node、rack 間で Pod を分散できる
   - B) DoNotSchedule は global minimum に対して skew を評価する
   - C) ScheduleAnyway は spread preference を使用する
   - D) 既存の Pod を自動的に再配置する

<details>
<summary>回答を表示</summary>

**回答: D) 既存の Pod を自動的に再配置する**

**解説:**
Spread constraint は到着する Pod の scheduling に影響します。実行中の Pod を移動することはありません。DoNotSchedule では、maxSkew は target domain の一致する Pod 数を global minimum と比較します。適格な domain が minDomains より少ない場合、その minimum は 0 です。count に参加するよう、到着する Pod の label を labelSelector に一致させてください。Descheduler は適格な違反 Pod を eviction する場合がありますが、特定の replacement 配置を保証するものではありません。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: example-pod
  labels:
    app: web-server
spec:
  topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: web-server
  containers:
  - name: nginx
    image: nginx
```
</details>

5. QoS と eviction に関する記述で誤っているものはどれですか？
   - A) Guaranteed には適切で等しい CPU/memory request-limit configuration が必要である
   - B) Burstable は Guaranteed と BestEffort の間の configuration を対象とする
   - C) BestEffort には CPU/memory request または limit がない
   - D) Guaranteed Pod は pressure 下で常に最初に eviction される

<details>
<summary>回答を表示</summary>

**回答: D) Guaranteed Pod は pressure 下で常に最初に eviction される**

**解説:**
Kubelet は QoS を厳格な eviction sequence として使用しません。request を超える使用量、priority、request に対する相対使用量で順位付けします。disk pressure には異なる accounting があります。Guaranteed Pod も eviction されたり、failure 中に失われたりする可能性があります。QoS は resource から導出され、Pod field として直接割り当てられるものではありません。
</details>

6. batch-job workload が Karpenter/Cluster Autoscaler とともに実行され、consolidation のために完全に idle になる node 数を最大化する必要があります。どの `NodeResourcesFit` scoring strategy が最も適しており、その理由は何ですか？
   - A) `LeastAllocated`: すべての node 間で CPU/memory 使用量を均等化するため
   - B) `MostAllocated`: 新しい pod をすでに最も busy な node に詰め込み、他を空のままにするため
   - C) `LeastAllocated` と同じ linear curve を使用する `RequestedToCapacityRatio`
   - D) EKS では default scheduler の config を直接編集できるため、どちらの strategy も重要ではない

<details>
<summary>回答を表示</summary>

**回答: B) `MostAllocated`: 新しい pod をすでに最も busy な node に詰め込み、他を空のままにするため**

**解説:**
不均一な baseline load（CPU の 75%/37%/0%）を持つ使い捨ての 3-worker `kind` test で、これが確認されました。default の `LeastAllocated` scheduler は 6 つの新しい pod を最も空いている node に振り分け、3 node すべてを 75%/37%/37% にしました（scale down 可能な node はありません）。`scoringStrategy.type: MostAllocated` で設定された 2 番目の scheduler は、同じ 6 つの pod を最も busy な 2 node に振り分け（93%/56%/0%）、idle node を変更せず consolidation の対象として残しました。Amazon EKS の control plane は managed であるため、`MostAllocated` を適用するには追加の scheduler `Deployment` を実行し、default scheduler を直接編集するのではなく `schedulerName` で Pod をそこへ対象指定する必要があります。
</details>

[学習教材に戻る](../../core/08-scheduling-preemption-eviction.md)
