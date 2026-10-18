# Karpenter クイズ

> **最終更新日**: 2026年9月11日

このクイズでは、Karpenter による node autoscaling の概念、NodePool／EC2NodeClass の設定、コスト最適化、Consolidation、Drift、interruption 対応、Amazon EKS との統合について確認します。

## 選択式問題

1. この AWS の例で、Karpenter と Cluster Autoscaler のアーキテクチャ上の違いはどれですか？
   - A) より高い Kubernetes version が必要
   - B) Auto Scaling Group を介さず、EC2 instance を直接プロビジョニングする
   - C) AWS のみをサポートし、他の cloud はサポートしない
   - D) CPU ベースのスケーリングだけをサポートする

<details>

<summary>回答を表示</summary>

**回答: B) Auto Scaling Group を介さず、EC2 instance を直接プロビジョニングする**

**解説:**
AWS provider を使う場合、Karpenter は Auto Scaling Group のサイズを調整する代わりに、NodeClaim を通じて EC2 の capacity（EC2 Fleet を含む）を要求します。Cluster Autoscaler は通常、設定済みの node group を調整します。選択される instance は Pod／NodePool／NodeClass の制約、quota、供給状況にも左右されます。API の起動要求から EC2 が起動するまで、Node が Ready になるまで、アプリケーションが Ready になるまでは別々の段階であり、数秒で完了する保証はありません。

</details>

2. Karpenter v1 API で node provisioning の方針（instance type、capacity type、disruption 設定）を定義する CRD はどれですか？
   - A) NodeClaim
   - B) NodePool
   - C) NodeTemplate
   - D) EC2NodeClass

<details>

<summary>回答を表示</summary>

**回答: B) NodePool**

**解説:**
`NodePool`（`karpenter.sh/v1`）は template の要件とライフサイクル方針を定義します。`expireAfter` は `spec.template.spec`、consolidation と budget は `spec.disruption` の下にあります。`EC2NodeClass`（`karpenter.k8s.aws/v1`）は `nodeClassRef` 経由で AWS 固有の設定を提供します。`NodeClaim` は個々の Node について、要求された capacity とライフサイクルを追跡します。

</details>

3. コスト最適化のため Spot instance を使うには、Karpenter をどう設定しますか？
   - A) `disruption.capacityType: spot` を設定する
   - B) requirements に `karpenter.sh/capacity-type: spot` を指定する
   - C) `nodeClassRef` に `spotEnabled: true` を設定する
   - D) limits に `spot: true` を設定する

<details>

<summary>回答を表示</summary>

**回答: B) requirements に `karpenter.sh/capacity-type: spot` を指定する**

**解説:**
NodePool の requirements では、spot、on-demand、設定されている場合は reserved capacity を許可できます。`In` 条件の values は集合であり、記述順で優先順位は決まりません。許可された capacity type の中では、利用可能な offering と制約に応じて、Karpenter は reserved、Spot、On-Demand の順に優先します。Spot の価格と中断リスクは変動するため、節約は保証されません。

</details>

4. Karpenter の Consolidation 機能は何を行いますか？
   - A) 複数の Node のログをまとめる
   - B) workload の制約を考慮し、Node の削除または低コストな Node への置き換えが可能か評価する
   - C) 複数の cluster を 1 つにまとめる
   - D) 複数の NodePool を 1 つにまとめる

<details>

<summary>回答を表示</summary>

**回答: B) workload の制約を考慮し、Node の削除または低コストな Node への置き換えが可能か評価する**

**解説:**
Consolidation は workload の制約と適用される disruption 制御を守りながら、実行可能な Node の削除や低コスト Node への置き換えを探します。Node の削除、より安価な Node への置き換え、複数 Node の統合があり、必ずしも Node 数が減るとは限りません。`WhenEmpty` は対象となる空の Node に限定します。`consolidateAfter` は関連する Pod の変更後、対象として評価されるまでの待機時間です。終了期限や CPU 使用率のしきい値を保証する設定ではありません。

</details>

5. Karpenter の `expireAfter` 設定の目的は何ですか？
   - A) Pod が Node 上で実行できる最長時間
   - B) Node の年齢が達したとき、期限切れによる drain を開始する値
   - C) Karpenter controller の cache の有効期間
   - D) NodePool 方針の有効期間

<details>

<summary>回答を表示</summary>

**回答: B) Node の年齢が達したとき、期限切れによる drain を開始する値**

**解説:**
Node が指定年齢に達すると、`expireAfter` による drain が始まります。`terminationGracePeriod` が設定されていない場合、PDB による阻止や `do-not-disrupt` Pod によって完了が遅れることがあります。設定済みの `terminationGracePeriod` に達すると、残る Pod が強制削除される場合があります。外部の interruption deadline によって capacity が失われることもあります。置き換えには、その時点で利用可能な AMI／instance type が使われ、必ず新しいものになるわけではありません。期限切れになっても、置き換え先が先に Ready になる保証はありません。

</details>

6. Karpenter の NodePool に対する resource limit を設定する field はどれですか？
   - A) `spec.template.limits`
   - B) `spec.limits`
   - C) `spec.maxResources`
   - D) `spec.resourceQuota`

<details>

<summary>回答を表示</summary>

**回答: B) `spec.limits`**

**解説:**
`spec.limits` は動的な NodePool 全体で使用できる resource の上限を制約します。`cpu: "1000"` のように数量を文字列で指定すると、API／GitOps 間の型の違いを避けられます。複数の provisioning が並行すると limit の確認に遅れが生じ、短時間の scale-out で上限を超える場合があります。厳密なコスト上限や請求上限ではありません。

</details>

7. Karpenter の Drift 機能は何を検出して処理しますか？
   - A) ネットワークトラフィックの変化
   - B) NodePool／EC2NodeClass の変更により、既存 Node が現在の設定と一致しない状態
   - C) Pod scheduling の drift
   - D) Kubernetes version の変更

<details>

<summary>回答を表示</summary>

**回答: B) NodePool／EC2NodeClass の変更により、既存 Node が現在の設定と一致しない状態**

**解説:**
Drift は、既存の NodeClaim を関連する希望設定または解決済み設定と比較します。たとえば weight や budget の変更だけでは drift が発生しない場合があります。また、変更可能な AMI selector は manifest を編集しなくても解決先が変わることがあります。drift の処理には disruption 制御が適用され、すべての Node が直ちに収束する保証はありません。Drift は v1 で安定しており、旧 drift feature gate は削除されています。

</details>

8. EC2NodeClass で Node の root volume のサイズと種類を指定する field はどれですか？
   - A) `spec.rootVolume`
   - B) `spec.blockDeviceMappings`
   - C) `spec.storage`
   - D) `spec.ebsConfig`

<details>

<summary>回答を表示</summary>

**回答: B) `spec.blockDeviceMappings`**

**解説:**
`spec.blockDeviceMappings` で EBS device を設定します。AL2023 の例では root mapping は `/dev/xvda` です。他の image では実際の AMI／family の構成を確認してください。Bottlerocket では別の data device が使われます。volume size、type、暗号化、KMS 権限を用途に合わせて設定します。EBS mapping を追加しただけでは、filesystem が自動的に format／mount されません。

</details>

## 短答式問題

9. Karpenter の scale-out latency を評価するとき、どの段階を計測する必要がありますか？

<details>

<summary>回答を表示</summary>

**回答: provisioning と readiness の各段階を計測します。共通の固定所要時間はありません。**

**解説:**
demand の検出と batching、EC2 request と capacity の確保、boot／bootstrap、Node の登録と Ready、続いて image pull とアプリケーションの Ready までを計測してください。IAM／API retry、IP capacity、storage、アプリケーション初期化は、それぞれ異なる段階に影響します。この文書には Cluster Autoscaler と普遍的に比較できる過去の実測時間はありません。

</details>

10. Karpenter に複数の NodePool がある場合、優先度はどう決まりますか？

<details>

<summary>回答を表示</summary>

**回答: `weight` field による相対的な優先度**

**解説:**
利用可能な動的 NodePool では、`spec.weight` を高くすると provisioning の優先度を上げられます。ただし scheduling batch、workload の要件、既存 capacity、NodePool limit、利用できない offering によって、別の pool が選ばれることがあります。Pod ごとの絶対的な保証や、Spot／On-Demand の固定比率ではありません。static NodePool には別の制約があります。1 つの pool 内の capacity type の優先順位は、配列の記載順とは独立しています。

</details>

11. Node を削除する際に、Pod の自発的な eviction を制限する Kubernetes resource は何ですか？

<details>

<summary>回答を表示</summary>

**回答: PDB（PodDisruptionBudget）**

**解説:**
PDB は、健全で selector に一致する replica 数に基づいて、自発的な eviction を制限します。PDB は replica を作成せず、予期しない instance loss、強制的な修復、設定済み `terminationGracePeriod` の期限切れも防ぎません。`minAvailable: 2` は eviction の制約であり、常に 2 Pod が起動中または応答可能である保証ではありません。

</details>

12. EC2NodeClass で使う subnet と security group を、Karpenter はどう選びますか？

<details>

<summary>回答を表示</summary>

**回答: サポート対象の tag／ID などを使う `subnetSelectorTerms` と `securityGroupSelectorTerms`**

**解説:**
selector にはサポートされる tag、明示的な resource ID、対応する場合は security group 名を指定できます。同じ term 内の条件は AND、複数の term は OR です。選択された AZ 内では通常、Karpenter は空き IP アドレスが最も多い一致 subnet を選びます。これだけで AZ 間の均等な配置や private routing が保証されるわけではありません。topology の制約、route、実際の security group を確認してください。

</details>

## ハンズオン問題

13. Spot と On-Demand の両方を許可し、m5／c5／r5 の instance type を使え、空の Node を 30 分後に consolidation の対象にできる動的 NodePool を記述してください。

<details>

<summary>回答を表示</summary>

**回答:**
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-optimized
spec:
  template:
    metadata:
      labels:
        nodepool: cost-optimized
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - m5.large
        - m5.xlarge
        - m5.2xlarge
        - c5.large
        - c5.xlarge
        - c5.2xlarge
        - r5.large
        - r5.xlarge
        - r5.2xlarge
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  limits:
    cpu: '1000'
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30m
  weight: 100
```

**解説:**
Spot の優先は、spot を先に書くことではなく、Karpenter の capacity-type policy によって決まります。選択可能な instance type を広げると選択肢は増えますが、供給は保証されません。`WhenEmpty` と `consolidateAfter: 30m` は、条件を満たす空の Node を待機後に候補にします。budget／PDB と reconciliation により、削除が遅れることがあります。`weight: 100` は相対的な優先度です。参照先の default EC2NodeClass と Node identity は事前に有効な状態にしてください。

</details>

14. 暗号化された 100Gi gp3 root volume、tag による subnet／security group の選択、IMDSv2 必須設定を備えた EC2NodeClass を記述してください。

<details>

<summary>回答を表示</summary>

**回答:**
```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: secure-nodeclass
spec:
  amiSelectorTerms:
  - alias: al2023@latest
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
      example.com/network-role: private
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  instanceProfile: KarpenterNodeInstanceProfile-my-cluster
  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 100Gi
      volumeType: gp3
      iops: 3000
      throughput: 125
      encrypted: true
      deleteOnTermination: true
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 1
    httpTokens: required
  tags:
    Environment: production
    ManagedBy: karpenter
```

**解説:**
これは AL2023 の学習用例です。`@latest` は解決される AMI を変えて drift を起こす場合があります。本番環境へ反映する前に、承認済みの release または AMI を固定してテストしてください。private を示す tag は独自の tag であり、route を確認済みの subnet に実際に付いている必要があります。IMDSv2 は複数の metadata 攻撃経路を減らしますが、SSRF をあらゆる場合に防ぐわけではありません。hop limit 1 は host network を使わない多くの container 経路を制限しますが、CNI／workload identity の設計と併せて検証してください。指定した instance profile、Node access、KMS／volume 設定、network 経路も前提条件です。

</details>

15. Karpenter の導入状態を確認し、provisioning の問題を調査する command を記述してください。

<details>

<summary>回答を表示</summary>

**回答:**
```bash
# 1. Check Karpenter pod status
kubectl get pods -n karpenter

# 2. Check Karpenter controller logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller

# 3. Check NodePool status
kubectl get nodepool
kubectl describe nodepool default

# 4. Check EC2NodeClass status
kubectl get ec2nodeclass
kubectl describe ec2nodeclass default

# 5. Check pods waiting to be scheduled
kubectl get pods --all-namespaces --field-selector status.phase=Pending

# 6. Check nodes created by Karpenter
kubectl get nodes -l karpenter.sh/nodepool

# 7. Check node details and labels/taints
kubectl describe node <node-name>

# 8. Check Karpenter events
kubectl get events --all-namespaces --sort-by='.metadata.creationTimestamp'
kubectl get nodeclaims -o wide

# 9. Check detailed provisioning logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller | grep -i "provisioning\|creating\|launching"

# 10. Forward the metrics endpoint; keep this terminal open until done.
kubectl port-forward -n karpenter svc/karpenter 8080:8080
```

port-forward の準備完了メッセージが表示されたら、別の terminal で次を実行します。

```bash
curl --fail --show-error http://127.0.0.1:8080/metrics | grep karpenter_
```

**解説:**
controller の readiness、NodePool／EC2NodeClass／NodeClaim の condition、Pod の scheduling event、AWS 側の前提条件をまとめて確認します。Pending は compute 不足と同じ意味ではなく、filter した log に行がないことも成功の証明ではありません。port-forward は別 terminal で実行し、準備完了を待ってから別 terminal で metrics を取得し、最後に Ctrl+C で停止してください。この metrics の直接読み取りに Prometheus server は不要です。ここに示す command は実際の cluster に対して実行していません。

</details>

---

**採点:**
- 正解数 13～15: 優秀（Karpenter の専門家レベル）
- 正解数 10～12: 良好（実務で活用可能）
- 正解数 7～9: 平均（追加学習を推奨）
- 正解数 0～6: 不十分（基本概念を復習）

[学習資料に戻る](../../autoscaling/02-karpenter.md)
