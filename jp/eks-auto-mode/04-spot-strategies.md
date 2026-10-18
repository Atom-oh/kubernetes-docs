# Spot Instance の活用戦略

> **対応バージョン**: EKS Auto Mode GA、例示する基準バージョンは EKS 1.36
> **最終更新**: 2026年9月12日

Spot は中断とキャパシティの不確実性を受け入れる代わりに、EC2 料金が低くなる可能性をもたらします。混合キャパシティ、多様化、レプリカはレジリエンスを高めることがありますが、いずれも単独で可用性やコスト削減を保証しません。前の章で確認したアカウント／コンテキストと NodeClass を使用してください。

マニフェストはスキーマに対してローカルで検査したラボ用の例であり、本番環境でのフェイルオーバー試験ではありません。無関係なワークロードが誤って配置されるのを減らすため、`spot-lab` taint／toleration と明示的な pool 選択を使います。Taint はテナント間のセキュリティ境界ではありません。適用前にレプリカ数とリソース上限を確認してください。これらの例は課金対象のノードを作成する場合があります。この監査では Spot instance をプロビジョニングしておらず、顧客の請求データも EC2 Spot Price History API も照会していません。

## 混合キャパシティと意図的なベースライン

以下の pool は Spot と On-Demand の両方を許可します。選択可能な pool 内では、Auto Mode は許可されたキャパシティタイプに優先順位を付けます。Spot と On-Demand の両方が許可され、利用可能な場合は Spot が優先されます。`reserved` も許可され、適合する予約がある場合は `reserved` の優先度がさらに高くなります。配列の順序や NodePool の weight で Spot の割合は決まりません。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: spot-lab
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: mixed-capacity
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
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '5'
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
      - key: spot-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        capacity-example: spot-lab
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spot-friendly-app
  namespace: spot-lab
spec:
  replicas: 10
  selector:
    matchLabels:
      app: spot-friendly
  template:
    metadata:
      labels:
        app: spot-friendly
    spec:
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
      containers:
      - name: app
        image: nginx:1.30.6
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        ports:
        - containerPort: 80
        readinessProbe:
          httpGet:
            path: /
            port: 80
          periodSeconds: 5
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: mixed-capacity
      tolerations:
      - key: spot-lab
        operator: Equal
        value: 'true'
        effect: NoSchedule
```

Pod の preferred affinity は希望であり、必須条件や予約ではありません。即時の On-Demand fallback、固定比率、または中断通知期間内の置き換えを約束するものではありません。既存キャパシティ、制約、クォータ、実際の利用可能性にも左右されます。

On-Demand を使う別のベースライン Deployment が必要な場合は、Pod template の Spot preference を、次のような必須選択に置き換え、ラボ用 toleration は残してください。適切な数のベースラインレプリカを稼働させてください。pool で On-Demand を許可するだけでは、予備キャパシティが常に確保されるわけではありません。

```yaml
nodeSelector:
  karpenter.sh/nodepool: mixed-capacity
  karpenter.sh/capacity-type: on-demand
tolerations:
- key: spot-lab
  operator: Equal
  value: 'true'
  effect: NoSchedule
```

この selector は意図的に `on-demand` を必須とし、`reserved` キャパシティは含みません。後でキャパシティ予約を使う場合は、label と予約設定を確認してください。On-Demand も、データ耐久性やキャパシティの可用性を保証するものではありません。

## 互換性のあるキャパシティを多様化する

Spot のキャパシティ pool は instance type と AZ の組み合わせで決まります。互換性のある type や AZ を増やすと割り当て先の選択肢は増えますが、中断が互いに独立するわけではなく、2つのアーキテクチャを列挙しただけでキャパシティが2倍になるわけでもありません。

この例では、上限を generation 7 に固定せず、generation 5 以降を許可します。制約を広げる前に、image、binary、storage、performance の互換性を確認してください。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: diversified-spot
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
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '4'
      - key: eks.amazonaws.com/instance-size
        operator: In
        values:
        - large
        - xlarge
        - 2xlarge
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: spot-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        capacity-example: spot-lab
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
  limits:
    cpu: '100'
    memory: 400Gi
```

`consolidationPolicy` と `consolidateAfter` は consolidation を制御するもので、EC2 interruption への反応時間を制御しません。複数のアーキテクチャを使うには、それぞれに対応した multi-architecture image と依存関係が必要です。generation や size を増やすのは、ワークロードに適しており、選択した AZ で利用できる場合に限り有効です。

## 自発的な disruption budget と EC2 interruption を分ける

Auto Mode は Spot interruption handling を標準で提供するため、この目的で追加の Node Termination Handler やユーザー管理の SQS queue は必要ありません。以前の壊れた NTH DaemonSet を Auto Mode node にデプロイしないでください。他の種類の node も併用する場合は、対象と権限を明確にして、それらの interruption handling を別途設定してください。

NodePool disruption budget は consolidation や drift など、自発的な disruption を制限します。EC2 による Spot キャパシティの回収を止めたり、通知時間を延ばしたり、置き換えキャパシティの準備を保証したりするものではありません。

該当する budget はすべて同時に適用され、最も制限の厳しい許容量に従います。以下の `10%` と `3` は選択肢ではありません。割合は切り上げられ、削除中または NotReady の node も許容量を消費します。他の条件を満たす健全な node が20個ある場合、これら2つの条件により、budget がゼロの時間帯以外に新たに自発的に disruption できるのは最大2個です。

この例では **韓国・ソウル時間 (KST) の月曜から金曜 09:00–18:00** を保護するため、**UTC 00:00** に9時間の window を開始します。Karpenter の budget schedule は UTC を使用します。以前の `0 9-18 * * mon-fri` は、18時に終わるのではなく、毎時新たな9時間 window を開始し、翌日まで disruption 禁止時間を延長していました。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot-with-disruption-budget
spec:
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
        - r
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: spot-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        capacity-example: spot-lab
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
    - nodes: '3'
    - nodes: '0'
      schedule: 0 0 * * mon-fri
      duration: 9h
  limits:
    cpu: '100'
    memory: 400Gi
```

運用カレンダーに合わせて window を調整してください。他の time zone や夏時間の変更には、意図した時刻への変換が必要です。自発的 disruption をゼロにする budget は、有用な保守作業を遅らせる場合があり、自発的でない interruption も止めません。

## 実際に使える時間内で graceful shutdown する

EC2 は通常、stop／terminate interruption の前に2分間の通知を出しますが、通知はベストエフォートです。Hibernation は直ちに開始する別の動作です。2分間をすべての Pod に保証された時間として扱わないでください。検知、eviction、アプリケーション処理、routing 変更にも時間が必要で、障害により通知処理ができないこともあります。

`terminationGracePeriodSeconds` は Kubernetes の shutdown 用 budget であり、EC2 の期限を延長しません。`preStop` は通常の stop signal が届く前に、この budget の中で実行されます。考えずに `sleep 90` を設定すると、120秒の budget の大半を浪費し、アプリケーションの shutdown や checkpoint を実装したことにもなりません。

以下は nginx 専用の例です。すぐに graceful quit を開始し、実際の HTTP readiness probe を使い、node 名を正しく記録します。別のアプリケーションでは、そのアプリケーション固有の stop-signal handler、readiness の切り替え、処理中作業の完了、永続 checkpoint を実装して試験してください。60秒は budget の上限例であり、実際に確保できる時間を保証しません。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spot-aware-app
  namespace: spot-lab
spec:
  replicas: 6
  selector:
    matchLabels:
      app: spot-aware
  template:
    metadata:
      labels:
        app: spot-aware
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: app
        image: nginx:1.30.6
        lifecycle:
          preStop:
            exec:
              command:
              - nginx
              - -s
              - quit
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        ports:
        - containerPort: 80
        readinessProbe:
          httpGet:
            path: /
            port: 80
          periodSeconds: 5
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: spot-aware
        minDomains: 2
        nodeAffinityPolicy: Honor
        nodeTaintsPolicy: Honor
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: spot-with-disruption-budget
      tolerations:
      - key: spot-lab
        operator: Equal
        value: 'true'
        effect: NoSchedule
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: spot-aware-budget
  namespace: spot-lab
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: spot-aware
```

`NODE_NAME` には Downward API 経由で node 名が設定されます。これは Spot かどうかを示す値ではなく、Downward API の Pod field から node label が自動的に公開されるわけでもありません。アプリケーションは通常、購入オプションにかかわらず graceful termination を処理する必要があります。キャパシティタイプが必要なら、node の IMDS credential に頼らず、確認済みの metadata をレビュー済みの方法で渡してください。

この例は2つの適格な AZ domain を必要とし、`maxSkew: 1` で6つのレプリカを分散します。AZ やキャパシティが利用できない場合、強制的な `DoNotSchedule` 制約によって Pod が Pending になることがあります。制約はキャパシティを生み出しません。3つの domain を必須にする前にトレードオフを確認してください。また、AZ spread により1つの AZ 内で instance type も分散されるとは限りません。

PDB はアプリケーション Pod の自発的な eviction を制限しますが、EC2 に回収される VM を維持できません。レプリカを増やすだけでは不十分です。traffic 処理、対象キャパシティ、topology、障害復旧も検証してください。

## ワークロードへの適合性

| ワークロード | 出発点と必要な検証 |
|----------|----------------------------------------|
| Stateless web／inference | interruption に耐えられる Spot capacity を使い、重要処理用のベースラインを意図的に用意して、latency／failover を試験する |
| Batch／CI | retry 可能で冪等な処理には Spot が適する場合がある。deadline が厳しい job には別のキャパシティが必要な場合がある |
| 長時間の training／stateful processing | 定期的な永続 checkpoint と、検証済みの resume／replay が必要。終了直前の checkpoint は保証されない |
| 単一 instance の database／重要な quorum | 明示的な復旧設計なしに interruption にさらさない。On-Demand だけでは local data を保護できない |
| 開発／test | cost limit を設け、キャパシティ不足を許容する。Spot のみの job が必ず開始できると考えない |

重要な state の唯一のコピーを、破棄される node-local storage に置かないでください。instance の購入オプションとは別に、耐久性のある storage、backup、復元を検証してください。

## 過去のコスト例であり、現在の見積もりではない

以前のガイドでは、Region、instance-hour の内訳、課金範囲、再現可能な測定条件なしに月額を掲載していました。以下は、現行 EKS version で測定した節約額ではなく、**未検証の教材用例**として残しています。

| 例 | 以前の On-Demand 額 | 以前の Spot 額 | 算術上の削減率 |
|---------|------------------------|-------------------|----------------------|
| Batch | $1,000／月 | $300／月 | 70% |
| 開発／test | $2,000／月 | $500／月 | 75% |
| CI/CD | $500／月 | $150／月 | 70% |
| 重要度の低い API | $3,000／月 | $1,200／月 | 60% |

AWS は EC2 Spot について最大90%の割引を案内していますが、最低割引率でもワークロード全体の節約保証でもありません。Spot Instance Advisor は直近1か月の interruption／節約データを AZ 間で平均した値を要約しており、反映が遅れる場合があります。価格計算には、現在の AZ 別 Spot Price History または実際の請求データを使ってください。過去の interruption band は次の job の予測ではありません。

同じ有用な作業、Region、期間、可用性目標をそろえて比較してください:

```text
Baseline total =
  sum(baseline On-Demand node-hours[type] * On-Demand rate[type])
  + other baseline costs

Actual total =
  sum(billed Spot node-hours[type, AZ] * time-weighted Spot rate[type, AZ])
  + sum(billed On-Demand fallback node-hours[type] * On-Demand rate[type])
  + other actual costs

Net savings = Baseline total - Actual total
```

時間単価には時間を一貫して用い、価格が変わる場合は実際に課金された利用期間で重み付けしてください。課金対象の Spot／fallback 時間には、実際に支払った retry、重複稼働、復旧作業を含めます。作業時間が課金時間に含まれている場合、一般的な「interruption overhead」を二重に差し引かないでください。

他の費用にも Auto Mode 管理料金、control plane 料金、EBS、networking／NAT、data transfer、logging、license を同じ条件で含めてください。Auto Mode 料金は EC2 の購入オプションに加算されます。以前の `interrupt count × recovery time × instance count` という近似式では、単位と interruption がすでに cluster 全体で数えられているかが曖昧でした。

## 運用上の検証

Spot に依存する前に、承認済み環境で interruption と復旧動作を試験してください。通知なし／遅延、代替キャパシティ不足、処理中の作業、image pull、storage 復旧、強制的な topology 制約を含めます。実際に失われた作業と復旧時の課金額を観測してください。この監査ではローカルの schema、schedule window、設定のみを確認しており、障害試験は実施していません。

## 参考資料

- [Spot interruption の通知](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-instance-termination-notices.html)
- [Auto Mode の標準 interruption handling](https://docs.aws.amazon.com/eks/latest/userguide/ml-node-pools.html)
- [キャパシティタイプの優先順位](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Karpenter の disruption budget と UTC schedule](https://karpenter.sh/v1.14/concepts/disruption/)
- [Pod termination と preStop](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Topology spread](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [Downward API field](https://kubernetes.io/docs/concepts/workloads/pods/downward-api/)
- [nginx の graceful shutdown](https://nginx.org/en/docs/control.html)
- [EC2 Spot の割引に関する案内](https://aws.amazon.com/ec2/spot/)
- [Spot Instance Advisor](https://aws.amazon.com/ec2/spot/instance-advisor/)
- [Spot price history API](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeSpotPriceHistory.html)
- [EKS Auto Mode の料金](https://aws.amazon.com/eks/pricing/)

< [前へ: Scaling Behavior](./03-scaling-behavior.md) | [目次](./README.md) | [次へ: Operations](./05-operations.md) >
