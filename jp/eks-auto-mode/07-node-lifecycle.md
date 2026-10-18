# ノードライフサイクル管理

> **対応バージョン**: EKS Auto Mode GA。例は EKS 1.36 を対象にレビュー済み
> **最終更新**: 2026年9月12日

有効期限、管理対象イメージの更新、アプリケーションの復旧は、それぞれノードライフサイクルの異なる側面です。Kubernetes の Node オブジェクトが新しくても、すべての CVE が修正済みであることや、ワークロードが準拠していることの証明にはなりません。ここに示す例は、公式情報とローカルのスキーマ／フィクスチャに照らしてレビューしたものであり、実際のノード入れ替え、クラウドリソースの変更、ベンチマークは実施していません。

## 有効期限と Auto Mode のライフタイム上限

`spec.template.spec.expireAfter` は、そのテンプレートから作成される NodeClaim の経過時間に基づく有効期限を決めます。旧 Provisioner 時代の `ttlSecondsUntilExpired` フィールドは、これらの `karpenter.sh/v1` NodePool では使用しません。

次の 3 つの設定を区別してください。

| 概念 | Auto Mode の動作 |
|---------|--------------------|
| 既定の有効期限 | AWS のドキュメントでは **336h（14日間）** です。7日間でも21日間でもありません |
| 終了猶予期間 | NodePool で省略した場合、Auto Mode は NodeClaim に **24h** を既定値として設定します。NodePool に表示されなくても NodeClaim を確認してください |
| マネージドインスタンスの最大ライフタイム | AWS は **21日間（504h）** を適用します。これは、その時点までノードが利用可能であるという保証ではありません |

上流 Karpenter の 720h という既定値を Auto Mode の既定値に置き換えてはいけません。より長い期間や上流の `Never` 構文を指定しても、Auto Mode のマネージドインスタンスを無期限に保持できるわけではありません。504h に長いドレイン時間を足して AWS の上限を延ばせると考えないでください。

以下の読み取り専用コマンドを実行する前に、[運用ガイド](./05-operations.md)のアカウント／コンテキスト確認とプライベートな `WORK_DIR` を使用してください。NodePool の例は、レビュー済みの `default` NodeClass を前提としています。これらは範囲を限定し、taint を付けたラボ設定です。一致するワークロードのセレクター／toleration と、アプリケーション復旧のテストが必要です。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: with-expiration
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
      - key: lifecycle-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        lifecycle-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
```

### 有効期限が実際に行うこと

有効期限は**強制的な中断トリガー**です。NodeClaim がポリシー上の経過時間に達すると終了／ドレインを開始し、事前に用意した代替ノードが Ready になるまで待つことはありません。NodePool の disruption budget は、有効期限による中断をレート制限しません。ワークロードコントローラーやプロビジョニング処理が必要に応じて代替容量を作成することはありますが、「新しいノードが Ready になってからドレインする」という従来の5段階の順序は保証されません。

終了コントローラーは通常の新規スケジューリングを停止し、Eviction API によるドレインを試み、ボリュームをデタッチしてインスタンスを終了します。PDB と Pod の `do-not-disrupt` はドレインに影響しますが、終了猶予期限と AWS の最大ライフタイムがあるため、可用性を無期限に保護することはできません。Pod のシャットダウン猶予期間とノードの終了猶予期間は別の設定です。ローカル／エフェメラルストレージ上のデータには、復旧手段を用意してください。

NodePool の `expireAfter` を変更しても、既存の NodeClaim の値は書き換わりません。変更によってドリフトが発生する場合があり、新しい値は置き換え後の NodeClaim に適用されます。別の中断方式で、ノードの期限より早く終了することもあります。1ノード分の budget を設定しても、複数ノードの期限が同時に来た場合に、必ず順番に処理されるわけではありません。

### 期間の選び方

以前の例にあった 24h、48h、72h、168h、336h は、環境ごとに選ぶポリシー値です。AWS の本番環境での既定値でも、PCI／HIPAA／SOC 2 が要求するローテーション間隔でもありません。以前の開発環境向け 504h の例は、サービス上限を表したものであり、`expireAfter` とドレイン時間の推奨値ではありません。

パッチ適用の緊急度、ワークロードのチェックポイント、キャッシュのウォームアップ、レプリカ／クォーラムの動作、利用可能な容量、復旧テストを踏まえてポリシーを選んでください。頻繁なローテーションは、イメージの pull、再スケジューリング、請求対象となる復旧作業を増やすことがあります。それ自体が特定の Spot インスタンスの EC2 中断確率を高めるわけではなく、新しいパッチがリリース直後に利用可能であることも保証しません。

## マネージド AMI と NodeClass の設定

Auto Mode は AWS 管理の **Bottlerocket バリアント**を使用します。AL2023 と Bottlerocket を切り替える `amiFamily`、カスタム `amiSelectorTerms`、任意の `userData`、SSH、SSM Session Manager アクセスは提供しません。これらのインターフェイスを、セルフマネージド Karpenter の EC2NodeClass や通常のマネージドノードグループ向け手順からコピーしてはいけません。

以下のサポート対象 NodeClass はストレージとネットワーク上の識別情報を設定します。AMI の選択や固定は行いません。

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: lifecycle-nodeclass
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

インスタンスプロファイルのロール／アクセスエントリと、実際に選択されるサブネット／セキュリティグループを確認し、`lifecycle-nodeclass` は対象の NodePool からのみ参照してください。Auto Mode の IMDSv2／hop limit 設定は AWS が管理するため、`metadataOptions` で上書きするフィールドではありません。`ephemeralStorage` を使用し、`blockDeviceMappings` は使わないでください。ノードのルート／データ EBS の暗号化は、アプリケーションの PVC が暗号化されている証拠にはなりません。サポートされるキー／証明書の設定については、[NodePool の設定](./02-nodepool-configuration.md)を参照してください。

### 過去の OS 比較を Auto Mode の選択肢と誤解しない

AL2023 は Fedora の一部の上流コンポーネントを取り入れた汎用 Amazon Linux ディストリビューションであり、単純に RHEL と同じものではありません。一般的な AL2023 や独立して運用する Bottlerocket ホストでは、ロックダウンされた Auto Mode ノードとは管理方法が異なります。Auto Mode は GPU ワークロードにもマネージドイメージを提供するため、「GPU には AL2023 が必要」という説明は当てはまりません。

以前の AL2023 の 40～60 秒、Bottlerocket の 20～30 秒／20～40 秒という起動時間の範囲、およびクイズに記載されていた 20～40 秒対15～25秒の範囲には、検証可能な測定根拠がありません。これらは過去の例として残すもので、OS の速度比較や、このマニフェストの起動時間予測として扱ってはいけません。イメージの pull、アーキテクチャ、インスタンスタイプ、ワークロードの Ready までの時間は、それぞれ別に測定してください。

## ドリフトとマネージドイメージの更新

AWS の説明では、Auto Mode の AMI はおおむね週次でリリースされ、条件を満たすノードはドリフトによって置き換えられます。この頻度は、CVE ごとのパッチ適用 SLA ではありません。別の EKS 最適化 AMI ファミリーのリリースが、自動的に Auto Mode のイメージ更新になるわけでもありません。

| 変更または観測内容 | 正しい解釈 |
|-----------------------|------------------------|
| Auto Mode のマネージド AMI 更新 | 既存の NodeClaim がドリフト状態になることがあります。実際の condition とロールアウト状況を確認してください |
| NodePool の要件変更 | すべての変更がドリフトを起こすわけではありません。互換性のある許容値を広げても、既存ノードが適合したままの場合があります |
| `expireAfter` テンプレートの変更 | 既存の NodeClaim は保存済みの値を保持し、置き換え後の NodeClaim に更新後のポリシーが適用されます |
| Weight、limits、disruption 設定 | 動作に関する設定であり、一律にドリフトを発生させるものではありません |
| NodeClass の望ましい状態の変更 | サポート対象フィールドを使用してください。タグの見た目を変更しても、緊急パッチが確実に適用されるわけではありません |
| `amiFamily`／`blockDeviceMappings` の変更 | これらは Auto Mode の有効な NodeClass フィールドではありません |

NodeClaim の `Drifted` condition を使用してください。ハッシュ注釈はドリフトを表す boolean status ではありません。また、condition が報告されていないからといって「ドリフトしていない」とは限りません。reason、遷移時刻、generation の情報を読み、現在のリソース状態と照合してください。

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodeclaims -o json |
jq '[.items[] | {
  name:.metadata.name,uid:.metadata.uid,node:.status.nodeName,
  createdAt:.metadata.creationTimestamp,deletionTimestamp:.metadata.deletionTimestamp,
  pool:.metadata.labels["karpenter.sh/nodepool"],
  expireAfter:.spec.expireAfter,terminationGracePeriod:.spec.terminationGracePeriod,
  imageID:.status.imageID,
  drift:([.status.conditions[]?|select(.type=="Drifted")|
    {status,reason,lastTransitionTime,observedGeneration}] |
    if length == 0 then {status:"NotReported"} else .[0] end),
  conditions:[.status.conditions[]?|{type,status,reason,lastTransitionTime,observedGeneration}]
}]'
```

ドリフトは、該当する disruption budget、スケジューリングの実現可能性、ドレイン制約に従う猶予付きの中断方式です。次の設定は、適用対象となる任意の中断を1件許可し、平日の UTC 00:00～08:00（ソウル時間 09:00～17:00）は**ドリフトのみ**を一時停止します。以前の `0 9-17`／`0 9-18` の時間単位スケジュールでは、長時間のウィンドウが重なって繰り返し開始していました。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: controlled-drift
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
      - key: lifecycle-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        lifecycle-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
    budgets:
    - nodes: '1'
    - nodes: '0'
      schedule: 0 0 * * mon-fri
      duration: 8h
      reasons:
      - Drifted
  limits:
    cpu: '100'
    memory: 400Gi
```

この設定は、有効期限、EC2 中断、修復を一時停止しません。`consolidateAfter` は統合に影響しますが、AMI パッチの期限には影響しません。Pod と Node の `do-not-disrupt` 注釈は異なるものです。Pod の注釈でドリフトを防げるかを評価するときは、Auto Mode の既定の NodeClaim 猶予期間も考慮してください。

## パッチ適用と緊急時の手動復旧

ノード OS と Auto Mode コンポーネントのパッチは AWS が管理します。一方、アプリケーション／コンテナの依存関係とワークロードのセキュリティは利用者が管理します。実際のイメージ情報、関連する AWS リリース／アドバイザリ、ロールアウトの進行状況、アプリケーションの検査結果を記録してください。タイムスタンプが新しいことや `SecurityPatch` タグがあることは、修正が含まれている証拠ではありません。

緊急の修復が必要な場合:

1. 必要なマネージドイメージ／修正がこのクラスターで利用可能か確認し、影響を受けるワークロードを特定します。
2. 使用するコンテキストで、**単一の NodeClaim UID**、Node との対応関係、NodePool、現在の condition、PDB、データの耐久性、余剰または調達可能な容量を確認します。
3. 要件を満たす場合は、マネージドドリフトのロールアウトを優先します。手動での置き換えが必要なら、レビュー済みの単一リソース保守手順を使用し、次のリソースに進む前に代替ノードとアプリケーションが Ready であることを確認します。
4. 変更のたびに健全性とイメージの証拠を再確認します。状態が不明、容量不足、またはアプリケーションの回帰があれば中止します。

次のコマンドは証拠を収集するだけです。

```bash
: "${NODECLAIM_NAME:?Select one NodeClaim for review}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodeclaim "$NODECLAIM_NAME" -o json |
  jq '{name:.metadata.name,uid:.metadata.uid,node:.status.nodeName,
       pool:.metadata.labels["karpenter.sh/nodepool"],imageID:.status.imageID,
       expireAfter:.spec.expireAfter,terminationGracePeriod:.spec.terminationGracePeriod,
       conditions:[.status.conditions[]?|{type,status,reason}]}'
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pdb -A -o json |
  jq '[.items[]|{namespace:.metadata.namespace,name:.metadata.name,
       observedGeneration:.status.observedGeneration,generation:.metadata.generation,
       currentHealthy:.status.currentHealthy,desiredHealthy:.status.desiredHealthy,
       disruptionsAllowed:.status.disruptionsAllowed}]'
```

`kubectl delete nodes -l ...` は一括削除要求であり、順番に行うローリングアップデートではありません。Node または NodeClaim の手動削除は NodePool budget に制限されません。`drain --delete-emptydir-data` はローカルデータを破棄する可能性があり、drain だけでは代替ノードが存在することを保証できません。したがって、以前のクイズにあった無制限の削除コマンドや、タグ変更を「パッチのトリガー」とする手順は、緊急時のランブックではありません。

## 統合、ドリフト、有効期限

| 方式 | トリガーと制御 |
|-----------|---------------------|
| 統合 | リクエスト／制約に基づく、より低コストで実現可能な配置。猶予付き中断の制御が適用されます |
| ドリフト | 既存の NodeClaim が、望ましいマネージド状態と一致しなくなった場合。猶予付き中断の制御が適用されます |
| 有効期限 | NodeClaim の経過時間が保存済みポリシーに達した場合。強制的なトリガーであり、NodePool budget に制約されません |

猶予付き中断を扱うコントローラーは、統合より先にドリフトを評価しますが、有効期限は別の強制的な経路です。「ドリフト > 有効期限 > 統合」という普遍的な優先順位や、最初に成立した condition を常に優先するという契約はありません。5日経過したノードが7日の有効期限より前に統合されることがあり、8日経過して期限に達したノードは、終了開始前に低使用率である必要はありません。

以下は代替となるラボ用ポリシーであり、コストやセキュリティ上の結果を保証するものではありません。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-priority
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
      expireAfter: 336h
      terminationGracePeriod: 24h
      taints:
      - key: lifecycle-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        lifecycle-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: security-priority
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
      expireAfter: 72h
      terminationGracePeriod: 24h
      taints:
      - key: lifecycle-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        lifecycle-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 10m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
```

`WhenEmpty` は統合の範囲を狭めますが、ドリフトや有効期限を無効にはしません。選択した有効期限と猶予期間に合わせてアプリケーション側を調整してください。ポリシー名だけで可用性を推測しないでください。

## Node オブジェクトの経過時間とイメージの証拠

`Node.metadata.creationTimestamp`、NodeClaim の作成時刻、EC2 の起動時刻は、それぞれ異なる観測値です。`Node.status.nodeInfo.osImage` は OS の説明であり、AMI ID ではありません。以前のスクリプトが CREATED／AGE の時刻列を繰り返し表示したり「セキュリティパッチ状態」の経過時間を示したりしても、パッチ状態の証明にはなりません。

対象の Node フィールドを取得し、移植可能な小数単位の経過時間と明示的なバケットを計算します。無効、欠落、タイムゾーンなし、または未来のタイムスタンプは不明のまま扱います。

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/compute-type=auto -o json |
jq '{items:[.items[] | {
  name:.metadata.name,uid:.metadata.uid,createdAt:.metadata.creationTimestamp,
  pool:.metadata.labels["karpenter.sh/nodepool"],
  osImage:.status.nodeInfo.osImage,kernelVersion:.status.nodeInfo.kernelVersion
}]}' > "$WORK_DIR/node-lifecycle.json"
```

```bash
python3 - <<'PY'
import json, os
from datetime import datetime, timezone
from pathlib import Path
now = datetime.now(timezone.utc)
rows = []
for item in json.loads((Path(os.environ["WORK_DIR"]) / "node-lifecycle.json").read_text())["items"]:
    result = {"node": item["name"], "pool": item.get("pool")}
    try:
        created = datetime.fromisoformat(item["createdAt"].replace("Z", "+00:00"))
        if created.tzinfo is None or created > now:
            raise ValueError("unusable timestamp")
        hours = (now - created).total_seconds() / 3600
        bucket = "<1d" if hours < 24 else "1d–<3d" if hours < 72 else "3d–<7d" if hours < 168 else ">=7d"
        result.update(nodeObjectAgeHours=round(hours, 3), bucket=bucket)
    except (KeyError, AttributeError, TypeError, ValueError):
        result["bucket"] = "UnknownTimestamp"
    rows.append(result)
summary = [{"bucket": bucket, "count": sum(row["bucket"] == bucket for row in rows)}
           for bucket in ("<1d", "1d–<3d", "3d–<7d", ">=7d", "UnknownTimestamp")]
print(json.dumps({"observedAt": now.isoformat(), "nodes": rows, "distribution": summary}, indent=2))
PY
```

バケットは `[0,1)`、`[1,3)`、`[3,7)`、`>=7` 日です。ちょうど7日は最後のバケットに含まれます。Node の一覧を正常に取得できた結果が空である場合と、API エラーを区別できます。このスナップショットは診断用であり、リアルタイム更新されるダッシュボードでも、パッチ準拠の確認でもありません。

### Prometheus と Grafana

kube-state-metrics をインストールし、`karpenter.sh/nodepool` と `eks.amazonaws.com/compute-type` を allowlist に追加します。以下の**単一クラスター用**ルールファイルは、重複スクレイプを排除し、Auto Mode のラベルを Node 作成時刻の gauge に結合します。マルチクラスターのクエリでは、すべての group／join に実際のクラスターラベルを残してください。メトリクスがない場合や未来のタイムスタンプは、経過時間がゼロの健全なノードとして扱いません。

経過時間アラートには、以前の10日間および標準偏差3というしきい値を**例示用の確認シグナル**として残しています。これは Auto Mode の既定値ではありません。複数の NodePool ポリシーと通常のオートスケーリングによって、経過時間の分布が広くなることがあります。これを Prometheus のルールファイルとして読み込むか、operator が選択する PrometheusRule の `spec` 以下にグループを配置してください。

```yaml
groups:
- name: node-lifecycle
  rules:
  - record: eks_auto:node_object_age_days
    expr: "(\n  ((time() - max by (node) (kube_node_created)) >= 0) / 86400\n) * on\
      \ (node) group_left (label_karpenter_sh_nodepool)\nmax by (node,label_karpenter_sh_nodepool)\
      \ (\n  kube_node_labels{label_karpenter_sh_nodepool!=\"\",label_eks_amazonaws_com_compute_type=\"\
      auto\"}\n)"
  - alert: ReviewNodeObjectAge
    expr: eks_auto:node_object_age_days > 10
    for: 1h
    labels:
      severity: warning
    annotations:
      summary: Review this node against its actual lifecycle policy
  - alert: ReviewNodeAgeSpread
    expr: stddev(eks_auto:node_object_age_days) > 3
    for: 4h
    labels:
      severity: info
    annotations:
      summary: Age spread is a review signal, not proof of failed rotation
```

```promql
# median_object_age_days
quantile(0.5, eks_auto:node_object_age_days)

# mean_by_pool
avg by (label_karpenter_sh_nodepool) (eks_auto:node_object_age_days)

# oldest_five
topk(5, eks_auto:node_object_age_days)

# less_than_1d
sum((eks_auto:node_object_age_days >= bool 0) * (eks_auto:node_object_age_days < bool 1))

# 1d_to_under_3d
sum((eks_auto:node_object_age_days >= bool 1) * (eks_auto:node_object_age_days < bool 3))

# 3d_to_under_7d
sum((eks_auto:node_object_age_days >= bool 3) * (eks_auto:node_object_age_days < bool 7))

# 7d_or_more
sum(eks_auto:node_object_age_days >= bool 7)
```

`kube_node_created` は時刻を表す gauge であり、ヒストグラム／カウンターではありません。既定で `kube_node_created_bucket` が用意されているわけではなく、`rate()` と `histogram_quantile()` を使ってもノード経過時間のヒストグラムは生成できません。現在の経過時間の中央値には `quantile()` を使い、棒グラフには明示的な boolean バケットを使用してください。これらのバケット合計は、観測された Node があってバケット内がゼロ件の場合にゼロを返します。入力が存在しない場合は、結果も存在しません。

| Grafana パネル | 根拠となるデータ |
|---------------|----------|
| 現在の経過時間分布 | 4つの明示的なバケットクエリ |
| NodePool ごとの平均／最古のノード | ラベル結合と `avg`／`topk` |
| 有効期限が近い NodeClaim | NodeClaim の実際の作成時刻と保存済み `expireAfter`。Node の経過時間だけでは不十分です |
| 置き換え率 | 設定済みのイベント／ログ履歴または検証済みカウンター発行元。現在のオブジェクト数からの推定ではありません |
| パッチのロールアウト | マネージドイメージ／リリース情報、NodeClaim の condition、アプリケーションの健全性 |

## 参考資料

- [Auto Mode の NodePool 既定値と終了猶予](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Auto Mode のセキュリティとインスタンスの最大ライフタイム](https://docs.aws.amazon.com/eks/latest/userguide/auto-security.html)
- [Auto Mode のマネージド OS と責任範囲](https://docs.aws.amazon.com/eks/latest/userguide/automode.html)
- [NodeClass でサポートされる設定](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [Karpenter の中断、期限切れ、ドリフト](https://karpenter.sh/v1.14/concepts/disruption/)
- [kube-state-metrics の Node メトリクス](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/cluster/node-metrics.md)
- [Prometheus の集約演算子](https://prometheus.io/docs/prometheus/latest/querying/operators/)
- [AL2023 と Fedora の関係](https://docs.aws.amazon.com/linux/al2023/ug/relationship-to-fedora.html)

< [前へ: コスト管理](./06-cost-management.md) | [目次](./README.md) | [次へ: ワークロード最適化](./08-workload-optimization.md) >
