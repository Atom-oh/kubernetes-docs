# Karpenter クイズ

このクイズでは、Karpenter node autoscaler の概念、NodePool/EC2NodeClass 設定、コスト最適化、Consolidation（統合）、Drift（ドリフト）、interruption handling、および Amazon EKS 統合についての理解を確認します。

## 選択式問題

1. 既存の Cluster Autoscaler と比較した Karpenter の最大の違いは何ですか？
   - A) より高い Kubernetes バージョン要件
   - B) Auto Scaling Groups を使わずに EC2 instance を直接プロビジョニングする
   - C) AWS のみをサポートし、他の cloud はサポートしない
   - D) CPU ベースのスケーリングのみをサポートする

<details>

<summary>答えを表示</summary>

**回答: B) Auto Scaling Groups を使わずに EC2 instance を直接プロビジョニングする**

**解説:**
Karpenter の最大の差別化要因は、Auto Scaling Groups (ASG) をバイパスし、EC2 Fleet API を直接使用して nodes をプロビジョニングすることです。Cluster Autoscaler は node groups/ASGs を通じてスケールするため、instance types は node group 設定によって制限されます。Karpenter は pod の要件に基づいてさまざまな選択肢から最適な instance type を動的に選択し、数秒以内に nodes をプロビジョニングできます。
</details>

2. Karpenter v1beta1 API で node provisioning policies を定義する CRD は何ですか？
   - A) Provisioner
   - B) NodePool
   - C) NodeTemplate
   - D) EC2NodeClass

<details>

<summary>答えを表示</summary>

**回答: B) NodePool**

**解説:**
Karpenter v1beta1 API では、以前の Provisioner CRD は NodePool に置き換えられました。NodePool は node provisioning policies（instance types、capacity types、architectures、availability zones など）と disruption settings（consolidation、expireAfter など）を定義します。EC2NodeClass は AWS 固有の設定（subnets、security groups、AMIs、block devices など）を定義し、NodePool は nodeClassRef を通じて EC2NodeClass を参照します。
</details>

3. コスト最適化のために Karpenter で Spot instances を使用するには、どのように設定しますか？
   - A) disruption.capacityType: spot
   - B) requirements で karpenter.sh/capacity-type: spot を指定する
   - C) nodeClassRef で spotEnabled: true を設定する
   - D) limits で spot: true を設定する

<details>

<summary>答えを表示</summary>

**回答: B) requirements で karpenter.sh/capacity-type: spot を指定する**

**解説:**
capacity type を指定するには、NodePool の `spec.template.spec.requirements` で `karpenter.sh/capacity-type` key を使用します。Spot instances のみの場合は `values: ["spot"]`、両方を許可する場合は `values: ["spot", "on-demand"]` を使用します。Karpenter は価格と可用性を考慮して最適な instances を選択します。Spot instances は On-Demand と比較して最大 90% のコスト削減が可能です。
</details>

4. Karpenter の Consolidation 機能は何をしますか？
   - A) 複数の nodes から logs を統合する
   - B) コスト削減のために、複数の nodes からの workloads をより少ない nodes に統合する
   - C) 複数の clusters を 1 つに統合する
   - D) 複数の NodePools を 1 つに統合する

<details>

<summary>答えを表示</summary>

**回答: B) コスト削減のために、複数の nodes からの workloads をより少ない nodes に統合する**

**解説:**
Consolidation は Karpenter の中核的なコスト最適化機能です。使用率の低い nodes からの workloads をより少ない nodes に統合（bin-pack）して、resource utilization を高め、コストを削減します。`consolidationPolicy: WhenEmpty` は空の nodes のみを削除しますが、`consolidationPolicy: WhenUnderutilized` は使用率が低い場合にも統合します。`consolidateAfter` は統合前の待機時間を設定します。
</details>

5. Karpenter の expireAfter 設定の目的は何ですか？
   - A) pod が node 上で実行できる最大時間
   - B) node 作成後、自動的に置き換えられるまでの最大時間
   - C) Karpenter controller の cache expiration time
   - D) NodePool policies の有効期間

<details>

<summary>答えを表示</summary>

**回答: B) node 作成後、自動的に置き換えられるまでの最大時間**

**解説:**
`expireAfter` 設定は node の最大寿命を定義します。たとえば、`expireAfter: 720h`（30 日）を設定すると、30 日後に nodes が自動的に置き換えられます。これは、security patches、AMI updates、より新しい instance types の活用のために nodes を定期的に更新する場合に役立ちます。Karpenter は既存 nodes を終了する前に workloads を他の nodes へ安全に移動するため、PDBs を尊重します。
</details>

6. Karpenter で NodePool の resource limits を設定する field は何ですか？
   - A) spec.template.limits
   - B) spec.limits
   - C) spec.maxResources
   - D) spec.resourceQuota

<details>

<summary>答えを表示</summary>

**回答: B) spec.limits**

**解説:**
NodePool の `spec.limits` は、その NodePool がプロビジョニングできる最大 resources を定義します。たとえば、`limits: { cpu: 1000, memory: 1000Gi }` は、合計 1000 CPU cores と 1000Gi memory までにプロビジョニングを制限します。これにより、コスト管理と cluster capacity management が可能になります。limits に達すると、Karpenter は追加の nodes をプロビジョニングしません。
</details>

7. Karpenter の Drift 機能は何を検出し、処理しますか？
   - A) Network traffic の変化
   - B) NodePool/EC2NodeClass の変更により、既存 nodes が現在の設定と一致しない状態
   - C) Pod scheduling drift
   - D) Kubernetes バージョンの変更

<details>

<summary>答えを表示</summary>

**回答: B) NodePool/EC2NodeClass の変更により、既存 nodes が現在の設定と一致しない状態**

**解説:**
Drift 機能は、NodePool または EC2NodeClass の設定が変更され、既存 nodes が新しい設定と一致しない場合に検出します。たとえば、AMI を更新したり security groups を変更したりすると、既存 nodes は「drifted」になります。Karpenter はこれらの nodes を段階的に置き換え、すべての cluster nodes が最新の設定を使用するようにします。`featureGates.drift=true` で有効化します。
</details>

8. EC2NodeClass で node の root volume size と type を設定する field は何ですか？
   - A) spec.rootVolume
   - B) spec.blockDeviceMappings
   - C) spec.storage
   - D) spec.ebsConfig

<details>

<summary>答えを表示</summary>

**回答: B) spec.blockDeviceMappings**

**解説:**
EC2NodeClass の `spec.blockDeviceMappings` は EBS volume configuration を定義します。`deviceName: /dev/xvda` で root volume を指定し、`ebs` subfield で `volumeSize`、`volumeType`、`iops`、`throughput`、`encrypted`、`kmsKeyID` などを設定します。たとえば、暗号化された 100Gi gp3 volume を使用するには、これらの attributes を適切に設定します。
</details>

## 短答式問題

9. Karpenter が unschedulable pod を検出し、適切な node をプロビジョニングする一般的な時間はどのくらいですか？

<details>

<summary>答えを表示</summary>

**回答: 数秒以内**

**解説:**
Karpenter は unschedulable pods を検出してから数秒以内に nodes をプロビジョニングします。これは、ASGs を通じたスケーリングに数分かかる Cluster Autoscaler とは対照的です。Karpenter の高速なスケーリングは、EC2 Fleet API を直接使用し、pod の要件を分析して最適な instances を即座に選択することに由来します。これは burst traffic や高速な scale-out を必要とする workloads にとって大きな利点です。
</details>

10. Karpenter で複数の NodePools が存在する場合、priority はどのように決定されますか？

<details>

<summary>答えを表示</summary>

**回答: weight field を使用した weight-based priority**

**解説:**
複数の NodePools が pod の要件を満たせる場合、`spec.weight` field を使用して priority を指定します。weight 値が高い NodePools が先に選択されます。たとえば、Spot instance NodePool に高い weight を、On-Demand NodePool に低い weight を設定すると、Karpenter はまず Spot を試し、利用できない場合に On-Demand を使用します。
</details>

11. nodes を削除する際に workload availability を確保するため、Karpenter が尊重する Kubernetes resource は何ですか？

<details>

<summary>答えを表示</summary>

**回答: PDB (PodDisruptionBudget)**

**解説:**
Karpenter は nodes を削除する際（consolidation、expiration、drift など）、PodDisruptionBudget (PDB) を尊重します。PDB は最小 application availability を定義し、Karpenter は PDB に違反しない範囲内でのみ nodes を drain します。たとえば、PDB 設定が `minAvailable: 2` の場合、Karpenter は nodes を削除している間も少なくとも 2 つの pods が常に実行されるようにします。
</details>

12. Karpenter は EC2NodeClass で使用する subnets と security groups をどのように選択しますか？

<details>

<summary>答えを表示</summary>

**回答: subnetSelectorTerms と securityGroupSelectorTerms による tag-based selection**

**解説:**
EC2NodeClass は subnets と security groups の tag-based selection に `subnetSelectorTerms` と `securityGroupSelectorTerms` を使用します。たとえば、`tags: { karpenter.sh/discovery: "my-cluster" }` はその tag を持つ resources を選択します。AWS resources には事前に tag を付けておく必要があり、複数の subnets が選択された場合、Karpenter は availability zone distribution のためにそれらを適切に分散します。
</details>

## ハンズオン問題

13. Spot instances を優先し、さまざまな instance types（m5、c5、r5 families）を許可し、空の nodes を 30 分後に削除する NodePool を書いてください。

<details>

<summary>答えを表示</summary>

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
          values: ["spot", "on-demand"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
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
        apiVersion: karpenter.k8s.aws/v1
        kind: EC2NodeClass
        name: default
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30m
  weight: 100
```

**解説:**
この NodePool はコスト最適化のために Spot instances を優先します（`capacity-type` で spot を先に記載）。さまざまな instance types を許可することで、Spot availability と price optimization が向上します。`consolidationPolicy: WhenEmpty` と `consolidateAfter: 30m` により、30 分間空だった nodes を削除します。`weight: 100` は他の NodePools より高い priority を設定するため、この NodePool が最初に選択されます。
</details>

14. 100Gi gp3 の暗号化 root volume、tag-based subnet/security group selection、IMDSv2 必須設定を持つ EC2NodeClass を書いてください。

<details>

<summary>答えを表示</summary>

**回答:**
```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: secure-nodeclass
spec:
  amiFamily: AL2

  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: "my-cluster"
        kubernetes.io/role: "private"

  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: "my-cluster"

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
    httpPutResponseHopLimit: 2
    httpTokens: required  # IMDSv2 required

  tags:
    Environment: production
    ManagedBy: karpenter
```

**解説:**
この EC2NodeClass は security best practices に従っています。`blockDeviceMappings` は暗号化された 100Gi gp3 volume を設定します。`metadataOptions.httpTokens: required` は、SSRF attacks を防ぐために IMDSv2 を必須にします。Tag-based selectors は private subnets のみを使用するように設定します。`instanceProfile` は事前に作成された IAM instance profile を参照します。
</details>

15. Karpenter installation status を確認し、provisioning issues をデバッグするための commands を書いてください。

<details>

<summary>答えを表示</summary>

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
kubectl get events --field-selector source=karpenter --sort-by='.lastTimestamp'

# 9. Check detailed provisioning logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller | grep -i "provisioning\|creating\|launching"

# 10. Check Karpenter metrics (if Prometheus is configured)
kubectl port-forward -n karpenter svc/karpenter 8080:8080 &
curl localhost:8080/metrics | grep karpenter_
```

**解説:**
Karpenter の問題をトラブルシュートする際は、複数の観点を確認します。まず controller pods が正常に実行されていることと、logs に errors がないことを確認します。NodePool と EC2NodeClass の status と configuration を確認します。Pending pods とその理由を確認します。一般的な問題には、IAM permissions の不足、subnet/security group tag の問題、instance limits などがあります。Karpenter events と metrics も診断に役立ちます。
</details>

---

**採点:**
- 13-15 正解: 優秀（Karpenter expert level）
- 10-12 正解: 良好（practical application capable）
- 7-9 正解: 平均（additional learning recommended）
- 0-6 正解: 不十分（basic concepts review needed）

[学習資料に戻る](../../autoscaling/02-karpenter.md)
