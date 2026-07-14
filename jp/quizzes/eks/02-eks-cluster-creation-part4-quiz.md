# EKS Cluster Creation クイズ - Part 4

このクイズでは、Amazon EKS cluster 作成に関連する高度な設定、スケーラビリティ、運用トピックについての理解を確認します。cluster のスケーリング、自動化、コスト最適化、運用のベストプラクティスなどのトピックを扱います。

## 基本概念の問題

1. Amazon EKS cluster における Cluster Autoscaler と Karpenter の主な違いは何ですか？
   * A) Cluster Autoscaler は AWS service であり、Karpenter は open-source tool である
   * B) Cluster Autoscaler は node group level でスケールし、Karpenter は workload 要件に一致する個々の node を provision する
   * C) Cluster Autoscaler は CPU/memory 使用率に基づいてスケールし、Karpenter は pod 数に基づいてスケールする
   * D) Cluster Autoscaler は horizontal scaling のみをサポートし、Karpenter は vertical scaling もサポートする

<details>

<summary>回答を表示</summary>

**回答: B) Cluster Autoscaler は node group level でスケールし、Karpenter は workload 要件に一致する個々の node を provision する**

**解説:** Amazon EKS cluster における Cluster Autoscaler と Karpenter の主な違いは、スケーリングのアプローチにあります。Cluster Autoscaler は既存の Auto Scaling Groups (ASGs) に基づいて node group level でスケールする一方、Karpenter は workload 要件に一致する個々の node を直接 provision します。

**Cluster Autoscaler の特徴:**

1. **Node Group ベースのスケーリング**:
   * 事前定義された Auto Scaling Groups を使用してスケールする
   * node group 内で同じ instance type または mixed instance types を使用する
   *   例:

       ```yaml
       # Cluster Autoscaler Deployment
       apiVersion: apps/v1
       kind: Deployment
       metadata:
         name: cluster-autoscaler
         namespace: kube-system
       spec:
         replicas: 1
         selector:
           matchLabels:
             app: cluster-autoscaler
         template:
           metadata:
             labels:
               app: cluster-autoscaler
           spec:
             containers:
             - image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.23.0
               name: cluster-autoscaler
               command:
               - ./cluster-autoscaler
               - --v=4
               - --stderrthreshold=info
               - --cloud-provider=aws
               - --skip-nodes-with-local-storage=false
               - --expander=least-waste
               - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/my-cluster
       ```
2. **仕組み**:
   * schedule できない pod がある場合に node group を scale up する
   * node utilization が低い場合に node group を scale down する
   * ASG の min/max size 制限内で動作する
3. **制限事項**:
   * スケーリング速度が比較的遅い（2〜10分）
   * 事前定義された instance types に限定される
   * node group level でのみスケールできる

**Karpenter の特徴:**

1. **Workload ベースの provisioning**:
   * workload 要件に一致する最適な instance types を選択する
   * ASGs を使わずに EC2 instances を直接 provision する
   *   例:

       ```yaml
       # Karpenter Provisioner
       apiVersion: karpenter.sh/v1alpha5
       kind: NodePool
       metadata:
         name: default
       spec:
         template:
           spec:
             requirements:
               - key: karpenter.sh/capacity-type
                 operator: In
                 values: ["spot", "on-demand"]
               - key: kubernetes.io/arch
                 operator: In
                 values: ["amd64", "arm64"]
           - key: node.kubernetes.io/instance-type
             operator: In
             values: ["m5.large", "m5a.large", "m5d.large", "m5ad.large", "m6g.large"]
         limits:
           resources:
             cpu: 1000
             memory: 1000Gi
         provider:
           subnetSelector:
             karpenter.sh/discovery: "true"
           securityGroupSelector:
             karpenter.sh/discovery: "true"
         ttlSecondsAfterEmpty: 30
       ```
2. **仕組み**:
   * schedule できない pod の要件を分析する
   * 要件に一致する最適な instance types を選択する
   * instances を直接 provision し、pod を schedule する
   * 空になった node を自動的に終了する
3. **利点**:
   * 高速なスケーリング速度（1分未満）
   * workloads に最適化された instance types を選択する
   * コスト最適化（Spot instance の活用、right-sizing）
   * 設定がシンプル（ASG 管理が不要）

**両ツールの比較:**

| 特性                     | Cluster Autoscaler                  | Karpenter                                    |
| ------------------------ | ----------------------------------- | -------------------------------------------- |
| スケーリング単位         | Node Group (ASG)                    | 個々の Node                                  |
| Instance の選択          | 事前定義された instance types       | workload 要件に最適な instances             |
| スケーリング速度         | 遅い（2〜10分）                     | 速い（1分未満）                              |
| 設定の複雑さ             | 中（ASG configuration が必要）      | 低（Provisioner definition のみ必要）        |
| コスト最適化             | 限定的                              | 高い（workload に最適化された instance 選択）|
| 成熟度                   | 高い（古い project）                | 中（比較的新しい project）                   |

**他の選択肢の問題点:**

* **Cluster Autoscaler は AWS service であり、Karpenter は open-source tool である**: どちらも open-source tools です。Cluster Autoscaler は Kubernetes SIG Autoscaling によって管理されており、Karpenter は AWS によって開始されましたが、open-source project です。
* **Cluster Autoscaler は CPU/memory 使用率に基づいてスケールし、Karpenter は pod 数に基づいてスケールする**: どちらも基本的には schedule できない pod（Pending state）に基づいてスケールします。CPU/memory 使用率に基づくスケーリングは Horizontal Pod Autoscaler (HPA) の役割です。
* **Cluster Autoscaler は horizontal scaling のみをサポートし、Karpenter は vertical scaling もサポートする**: どちらも horizontal scaling（node 数の増加）のみをサポートします。Vertical scaling（node resources の増加）はサポートされていません。Pod level の vertical scaling は Vertical Pod Autoscaler (VPA) の役割です。

Cluster Autoscaler と Karpenter はどちらも EKS clusters の auto-scaling のための tools ですが、Karpenter はより高速で柔軟なスケーリングを提供し、workload 要件に一致する最適な instances を選択できます。

</details>

2. Amazon EKS cluster で node group を作成する際に使用できる有効な capacity types はどれですか？
   * A) Reserved, On-Demand, Spot
   * B) On-Demand, Spot, Dedicated
   * C) On-Demand, Spot
   * D) Standard, Burstable, Compute-Optimized

<details>

<summary>回答を表示</summary>

**回答: C) On-Demand, Spot**

**解説:** Amazon EKS node group を作成する際に利用可能な capacity types は On-Demand と Spot です。

**On-Demand Capacity Type:**

* **特徴**: 中断なしで安定して利用できる instances
* **料金**: 固定の時間単価で支払う
* **適した Workloads**:
  * 中断に敏感な production applications
  * Stateful workloads
  * Databases
  * 重要な business applications

**Spot Capacity Type:**

* **特徴**: AWS の余剰 capacity を活用し、AWS が capacity を回収すると中断される可能性がある
* **料金**: On-Demand と比較して最大 90% の割引
* **適した Workloads**:
  * fault-tolerant applications
  * Stateless workloads
  * Batch processing jobs
  * Development/test environments

**EKS Node Group 作成時に Capacity Type を指定する例:**

AWS CLI example:

```bash
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-spot-nodegroup \
  --scaling-config minSize=3,maxSize=10,desiredSize=5 \
  --subnets subnet-0a1b2c3d4e5f6g7h8 subnet-0a1b2c3d4e5f6g7h9 \
  --instance-types t3.medium t3a.medium \
  --capacity-type SPOT \
  --node-role arn:aws:iam::123456789012:role/EKS-NodeInstanceRole
```

eksctl example:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
nodeGroups:
  - name: ng-on-demand
    instanceType: m5.large
    desiredCapacity: 3
    capacityType: ON_DEMAND
  - name: ng-spot
    instanceType: m5.large
    desiredCapacity: 2
    capacityType: SPOT
    spotInstancePools: 3
```

**他の選択肢の問題点:**

* **Reserved, On-Demand, Spot**: "Reserved" は EC2 Reserved Instances を指しますが、EKS node groups 作成時に capacity type として直接指定することはできません。Reserved Instances は billing discount model であり、node group capacity type として直接選択することはできません。
* **On-Demand, Spot, Dedicated**: "Dedicated" は EC2 Dedicated Instances を指しますが、EKS node group capacity type として直接指定することはできません。Dedicated Instances は別個の tenancy settings で設定できます。
* **Standard, Burstable, Compute-Optimized**: これらは capacity types ではなく、EC2 instance family types を表します。instance types（例: t3.medium, m5.large, c5.xlarge）を選択する際に考慮される特性です。

**ベストプラクティス:**

1. **Mixed Capacity Strategy を使用する**:
   * 重要な workloads は On-Demand node groups に配置する
   * fault-tolerant workloads は Spot node groups に配置する
   * node affinity と tolerations を使用して workload placement を制御する
2. **Spot Instances 使用時の考慮事項**:
   * 複数の instance types を指定する（中断リスクを分散する）
   * 適切な interruption handling mechanisms を実装する（Pod Disruption Budgets、graceful shutdown hooks）
   * AWS Node Termination Handler を deploy する
3. **コスト最適化**:
   * On-Demand nodes に Savings Plans または Reserved Instances を適用する
   * Graviton (ARM) instances を検討する
   * 適切な instance sizes を選択する

</details>

3. Amazon EKS cluster で Fargate profile を設定する際、必須で指定する必要があるものは何ですか？
   * A) Instance type と capacity type
   * B) Namespace と label selector
   * C) Subnet ID と security group
   * D) Autoscaling settings と最大 pod 数

<details>

<summary>回答を表示</summary>

**回答: B) Namespace と label selector**

**解説:** Amazon EKS Fargate profile を設定する際に指定が必須の項目は、namespace と、任意で label selector です。EKS はこの情報を使用して、どの pods を Fargate 上で実行するかを判断します。

**Fargate Profile の構成要素:**

1. **必須構成要素**:
   * **Profile Name**: Fargate profile の一意の識別子
   * **Pod Execution Role**: Fargate infrastructure 上で pods を実行するために必要な IAM role
   * **Subnets**: Fargate pods が実行される private subnets（デフォルトでは cluster subnets を使用）
   * **Selectors**: namespaces と任意の labels で構成される配列
2. **Selector Configuration**:
   * **Namespace**: pod が属する Kubernetes namespace（必須）
   * **Labels**: key-value pair の Kubernetes labels（任意）

**Fargate Profile 作成例:**

AWS CLI example:

```bash
aws eks create-fargate-profile \
  --cluster-name my-cluster \
  --fargate-profile-name my-fargate-profile \
  --pod-execution-role-arn arn:aws:iam::123456789012:role/AmazonEKSFargatePodExecutionRole \
  --subnets subnet-0a1b2c3d4e5f6g7h8 subnet-0a1b2c3d4e5f6g7h9 \
  --selectors namespace=default,labels={app=nginx} namespace=kube-system,labels={k8s-app=kube-dns}
```

eksctl example:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
fargateProfiles:
  - name: fp-default
    selectors:
      - namespace: default
        labels:
          app: nginx
      - namespace: kube-system
        labels:
          k8s-app: kube-dns
```

**Fargate Profiles の仕組み:**

1. pod が作成されると、EKS は pod の namespace と labels を確認します。
2. pod の namespace と labels が Fargate profile の selectors と一致すると、その pod は Fargate infrastructure 上で実行されます。
3. 一致する Fargate profile が存在しない場合、pod は EC2 nodes に schedule される（利用可能な場合）か、Pending state のままになります。

**他の選択肢の問題点:**

* **Instance type と capacity type**: Fargate は serverless compute service のため、instance types や capacity types を指定する必要はありません。AWS が必要な compute resources を自動的に provision します。
* **Subnet ID と security group**: subnet ID は必要ですが、cluster subnets をデフォルトとして使用できます。Security groups は任意であり、指定しない場合は cluster の security groups が使用されます。
* **Autoscaling settings と最大 pod 数**: Fargate は pod ごとに自動的にスケールするため、別個の autoscaling settings は不要です。Pod 数は Kubernetes Deployments または HPA (Horizontal Pod Autoscaler) によって管理されます。

**Fargate 使用時の考慮事項:**

1. **コスト**: Fargate では、実際に使用した vCPU と memory resources に対してのみ支払います。idle nodes のコストは発生しません。
2. **制限事項**:
   * DaemonSet pods は Fargate でサポートされていません。
   * Privileged containers はサポートされていません。
   * HostNetwork、HostPort のような host network modes はサポートされていません。
   * persistent volumes については、Amazon EFS のみサポートされています。
3. **Use Cases**:
   * Batch processing jobs
   * Web applications
   * API servers
   * Microservices
   * Development/test environments

</details>

4. Amazon EKS cluster の node group を更新する際、「update configuration」で設定可能な項目ではないものはどれですか？
   * A) 最大 unavailable node 数
   * B) 最大 unavailable node 割合
   * C) Node replacement strategy
   * D) Node group update timeout

<details>

<summary>回答を表示</summary>

**回答: C) Node replacement strategy**

**解説:** "Node replacement strategy" は Amazon EKS node group update configuration における公式の設定項目ではありません。EKS managed node groups はデフォルトで rolling update approach を使用しており、この strategy を直接変更するオプションはありません。

**EKS Node Group Update Configuration で設定可能な項目:**

1. **maxUnavailable**:
   * update 中に同時に unavailable になってよい node の最大数
   * 絶対数（例: 1, 2, 3）または割合（例: 20%）として指定できる
   * デフォルト: 1
2. **maxUnavailablePercentage**:
   * update 中に同時に unavailable になってよい node の最大割合
   * 1〜100 の値として指定する
   * `maxUnavailable` と併用できない
3. **force**:
   * node group update を強制するかどうか
   * デフォルト: false
4. **Timeout**:
   * node group update operation の最大待機時間
   * デフォルト: 60分

**Node Group Update Configuration の例:**

AWS CLI example:

```bash
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --update-config maxUnavailable=2
```

Or specifying percentage:

```bash
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --update-config maxUnavailablePercentage=20
```

eksctl example:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: my-nodegroup
    updateConfig:
      maxUnavailable: 2
```

**Node Group Update Process:**

1. **Update Start**: AWS が node group update を開始します。
2. **Node Draining**: `maxUnavailable` setting に従って、指定された数の nodes を cordon し drain します。
3. **Node Termination**: drain された nodes を終了します。
4. **New Node Creation**: 新しい configuration の nodes を作成します。
5. **Repeat**: すべての nodes が update されるまで steps 2〜4 を繰り返します。

**他の選択肢の解説:**

* **Maximum unavailable (maxUnavailable) node count**: update 中に同時に unavailable になってよい nodes の最大数を指定する有効な setting です。
* **Maximum unavailable (maxUnavailable) node percentage**: update 中に同時に unavailable になってよい nodes の最大割合を指定する有効な setting です。
* **Node group update timeout**: node group update operation の最大待機時間を指定する有効な setting です。

**Node Group Update のベストプラクティス:**

1. **適切な maxUnavailable 値を設定する**:
   * 小さすぎると update 時間が長くなります。
   * 大きすぎると application availability に影響する可能性があります。
   * workload の特性と node group size を考慮して設定します。
2. **Pod Disruption Budgets (PDB) を設定する**:
   * 重要な workloads に PDBs を設定し、最小 availability を確保します。
   *   例:

       ```yaml
       apiVersion: policy/v1
       kind: PodDisruptionBudget
       metadata:
         name: app-pdb
       spec:
         minAvailable: 2  # or maxUnavailable: 1
         selector:
           matchLabels:
             app: my-app
       ```
3. **更新前にテストする**:
   * 重要な updates の前に test environment で検証します。
   * rollback plan を準備します。
4. **Monitoring**:
   * update 中に application status を監視します。
   * issues が発生した場合は update を一時停止または rollback します。

</details>

5. EKS cluster で Kubernetes versions を upgrade する際に version を「skipping」することについて、正しい記述はどれですか？
   * A) Minor versions は skip できるが、major versions はできない
   * B) Major versions は skip できるが、minor versions はできない
   * C) Major versions も minor versions も skip できない
   * D) Major versions と minor versions の両方を skip できる

<details>

<summary>回答を表示</summary>

**回答: C) Major versions も minor versions も skip できない**

**解説:** Amazon EKS cluster を upgrade する場合、major versions と minor versions の両方を順番に upgrade する必要があります。version の skipping はサポートされていません。

**EKS Version Upgrade ルール:**

1. **Sequential Upgrade Required**:
   * 各 Kubernetes version は、前の version から順番に upgrade する必要があります。
   * 例: 1.22 -> 1.23 -> 1.24（1.22 から 1.24 へ直接 upgrade することはできません）
2. **Supported Upgrade Paths**:
   * 現在の version から次の minor version にのみ upgrade できます
   * major versions も順番に upgrade する必要があります
3. **Control Plane と Node Version の差異**:
   * control plane は nodes より最大 2 minor versions 先行できます
   * nodes は control plane より最大 1 minor version 先行できます

**EKS Version Upgrade Process:**

1. **Upgrade Plan を策定する**:
   * 現在の version と target version の間の変更を確認する
   * application compatibility を検証する
   * upgrade schedule と rollback plan を策定する
2. **推奨 Upgrade 順序**:
   * Control plane upgrade
   * Add-on upgrades (CoreDNS, kube-proxy, VPC CNI, etc.)
   * Node group upgrades
3.  **Upgrade Command Examples**:

    Control plane upgrade using AWS CLI:

    ```bash
    aws eks update-cluster-version \
      --name my-cluster \
      --kubernetes-version 1.24
    ```

    Control plane upgrade using eksctl:

    ```bash
    eksctl upgrade cluster \
      --name=my-cluster \
      --version=1.24 \
      --approve
    ```

    Node group upgrade:

    ```bash
    aws eks update-nodegroup-version \
      --cluster-name my-cluster \
      --nodegroup-name my-nodegroup
    ```

**EKS Version Support Policy:**

1. **Support Period**:
   * 各 Kubernetes version は、EKS での release 後およそ 14 か月間サポートされます。
   * AWS は常に少なくとも 4 つの production Kubernetes versions のサポートを維持します。
2. **End of Support Notice**:
   * AWS は version support 終了の約 60 日前に発表します。
   * support 終了後も clusters は稼働し続けますが、security patches や bug fixes は受け取れません。
3. **Version Release Cycle**:
   * AWS は通常、upstream Kubernetes release 後 2〜3 か月以内に EKS で新しい versions をサポートします。

**Upgrade のベストプラクティス:**

1. **まず Test Environment で Upgrade する**:
   * production environment upgrade の前に test cluster で検証する
2. **Upgrade 前に Backup する**:
   * 重要な resources の etcd backup と YAML backup
3. **段階的な Upgrade**:
   * すべての node groups を一度に upgrade するのではなく、段階的に進める
4. **Upgrade 後に検証する**:
   * workloads が正常に動作していることを確認する
   * monitoring systems を確認する
   * logs を確認する
5. **最新 Version を維持する**:
   * 定期的な upgrade schedule を策定する
   * support end dates を追跡する

**他の選択肢の問題点:**

* **Minor versions は skip できるが、major versions はできない**: Minor versions も skip できません。順番に upgrade する必要があります。
* **Major versions は skip できるが、minor versions はできない**: Major versions も skip できません。順番に upgrade する必要があります。
* **Major versions と minor versions の両方を skip できる**: EKS では version skipping はサポートされていません。

</details>

## 短答問題

6. EKS cluster の node group の instance type を変更するには何が必要ですか？

<details>

<summary>回答と解説</summary>

EKS managed node group の instance type を変更するには、新しい node group を作成して workloads を移行し、その後既存の node group を削除する必要があります。managed node groups の instance types は作成後に直接変更できません。

一般的な手順は次のとおりです:

1. 目的の instance type を持つ新しい node group を作成する
2. 必要に応じて Pod Disruption Budgets (PDB) を設定する
3. 既存の nodes を cordon および drain して workloads を新しい nodes へ移行する
4. すべての workloads が新しい node group に移動したことを確認する
5. 既存の node group を削除する

self-managed node groups を使用している場合は、Auto Scaling Group の launch template を更新し、instance refresh を実行できます。

</details>

7. EKS cluster で Kubernetes API server への public access を無効化し、private access のみを許可するには、どの設定を変更する必要がありますか？

<details>

<summary>回答と解説</summary>

EKS cluster の API server への public access を無効化し、private access のみを許可するには、cluster の endpoint access settings を変更する必要があります:

1. AWS Management Console 経由:
   * EKS console に移動する
   * cluster を選択する
   * "Networking" tab を選択する
   * "Cluster endpoint access" section の "Edit" をクリックする
   * "Private" に設定する（public access を無効化し、private access を有効化）
2. AWS CLI を使用:

```bash
aws eks update-cluster-config \
    --region region-code \
    --name cluster-name \
    --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true
```

この設定を変更すると、Kubernetes API server は VPC 内からのみアクセスできます。したがって、VPC 内の systems または VPC に接続された networks のみが cluster を管理できます。

</details>

8. EKS cluster で利用可能な Kubernetes versions の一般的な support period はどれくらいですか？

<details>

<summary>回答と解説</summary>

Amazon EKS の各 Kubernetes version は通常、release 後およそ 14 か月間サポートされます。AWS は常に少なくとも 4 つの production Kubernetes versions をサポートするよう努めています。

EKS version support cycle は次のとおりです:

1. Initial release: AWS が新しい Kubernetes version を EKS で利用可能にする
2. Standard support: およそ 14 か月間、security patches と bug fixes が提供される
3. End of support announcement: AWS が version support 終了の約 60 日前に発表する
4. End of support: deprecated versions で実行されている clusters は自動的に upgrade されず、手動で upgrade する必要がある

AWS は Kubernetes community releases より少し遅れて新しい versions のサポートを開始しますが、support period は一般的に長くなっています。upstream Kubernetes project は各 version をおよそ 9 か月間サポートする一方、EKS はおよそ 14 か月間サポートします。

</details>

## ハンズオン問題

9. EKS cluster の node group に Auto Scaling settings を設定する方法を説明し、次の要件を満たす configuration を作成してください:

* Minimum node count: 2
* Maximum node count: 10
* Desired node count: 3
* CPU utilization に基づく scale out（CPU utilization が 75% を超えた場合）
* memory utilization に基づく scale out（memory utilization が 80% を超えた場合）

<details>

<summary>回答と解説</summary>

EKS node group の Auto Scaling settings を設定するには、次の手順に従います:

1. まず、node group 作成時、または既存 node group の Auto Scaling Group settings で、基本的なサイズを設定します:

```bash
aws eks create-nodegroup \
    --cluster-name my-cluster \
    --nodegroup-name my-nodegroup \
    --scaling-config minSize=2,maxSize=10,desiredSize=3 \
    # Other required parameters...
```

2. CPU および memory utilization ベースのスケーリングには、Cluster Autoscaler または Karpenter を設定するか、CloudWatch alarm ベースの policies を Auto Scaling Group に直接追加できます。

**Cluster Autoscaler Approach:**

Cluster Autoscaler Deployment YAML:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
  labels:
    app: cluster-autoscaler
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cluster-autoscaler
  template:
    metadata:
      labels:
        app: cluster-autoscaler
    spec:
      serviceAccountName: cluster-autoscaler
      containers:
      - image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.23.0
        name: cluster-autoscaler
        resources:
          limits:
            cpu: 100m
            memory: 300Mi
          requests:
            cpu: 100m
            memory: 300Mi
        command:
        - ./cluster-autoscaler
        - --v=4
        - --stderrthreshold=info
        - --cloud-provider=aws
        - --skip-nodes-with-local-storage=false
        - --expander=least-waste
        - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/my-cluster
        - --balance-similar-node-groups
        - --skip-nodes-with-system-pods=false
```

**CloudWatch Alarm-Based Auto Scaling Policies:**

CPU utilization-based scale out policy:

```bash
aws autoscaling put-scaling-policy \
    --auto-scaling-group-name my-nodegroup-xxx \
    --policy-name cpu-scale-out \
    --policy-type TargetTrackingScaling \
    --target-tracking-configuration file://cpu-policy.json
```

cpu-policy.json:

```json
{
  "TargetValue": 75.0,
  "PredefinedMetricSpecification": {
    "PredefinedMetricType": "ASGAverageCPUUtilization"
  }
}
```

Memory utilization-based scale out policy (requires CloudWatch custom metric):

```bash
# First need to set up agent to publish memory utilization as CloudWatch custom metric
aws autoscaling put-scaling-policy \
    --auto-scaling-group-name my-nodegroup-xxx \
    --policy-name memory-scale-out \
    --policy-type TargetTrackingScaling \
    --target-tracking-configuration file://memory-policy.json
```

memory-policy.json:

```json
{
  "TargetValue": 80.0,
  "CustomizedMetricSpecification": {
    "MetricName": "MemoryUtilization",
    "Namespace": "AWS/EC2",
    "Dimensions": [
      {
        "Name": "AutoScalingGroupName",
        "Value": "my-nodegroup-xxx"
      }
    ],
    "Statistic": "Average",
    "Unit": "Percent"
  }
}
```

実際の environments では、Kubernetes workloads には Cluster Autoscaler を使用する方が適しています。Cluster Autoscaler は pod resource requests に基づいて nodes をスケールし、より効率的なスケーリングを可能にします。

</details>

## 応用問題

10. EKS cluster で blue/green approach を使用して node groups を upgrade する strategy を説明し、この process 中に発生する可能性のある issues と solutions を提示してください。

<details>

<summary>回答と解説</summary>

#### EKS Node Group Blue/Green Upgrade Strategy

Blue/green deployment は、既存の environment（blue）と並行して新しい environment（green）を構築し、その後 traffic を新しい environment に切り替える approach です。EKS node groups に適用する場合、process は次のように進みます:

**Blue/Green Upgrade Steps:**

1. **Preparation Phase**:
   * 現在の node group configuration（labels, taints, tags など）を document 化する
   * 現在の workload status と resource requirements を特定する
2. **Create Green Environment**:
   * 新しい node group を作成する（upgraded AMI, Kubernetes version, instance type など）
   * 既存 node group と同じ labels と taints を適用する
   * 必要な追加 configuration（tags, IAM roles など）を適用する
3. **Testing**:
   * test workloads を新しい node group に deploy する
   * functionality と performance を検証する
4. **Traffic Transition**:
   * Pod Disruption Budget (PDB) settings を確認する
   * 既存 nodes を cordon する（新しい pod scheduling を防ぐ）
   * 既存 nodes を段階的に drain する（workloads を新しい nodes に移行する）
   * workload status を監視する
5. **Completion and Cleanup**:
   * すべての workloads が新しい nodes に移動したことを確認する
   * 既存 node group を削除する
   * 必要に応じて monitoring と alerts を更新する

**発生し得る Issues と Solutions:**

1. **Resource Shortage Issue**:
   * **Issue**: 新しい node group の作成中は二重の resources が必要となり、service quotas を超える可能性がある
   * **Solution**: 事前に service quotas を確認し、必要に応じて increase を request するか、小さな batches で段階的に upgrade する
2. **Stateful Workload Migration**:
   * **Issue**: persistent volumes を使用する Stateful workloads は、nodes 間で移動する際に問題が発生する可能性がある
   * **Solution**: PVC/PV settings を確認し、StatefulSets を使用し、適切な storage classes を使用し、backups を実行する
3. **Node Affinity and Pod Disruption**:
   * **Issue**: 一部の workloads は node affinity または pod anti-affinity により新しい nodes へ移動できない場合がある
   * **Solution**: pod specs の node affinity と anti-affinity rules を確認し、必要に応じて調整する
4. **Network Policies and Security Groups**:
   * **Issue**: 必要な network policies または security groups が新しい node group に適用されない可能性がある
   * **Solution**: security groups、network policies、CIDR ranges を含む network configuration を確認し、複製する
5. **DNS and Service Discovery Delays**:
   * **Issue**: node transition 中に一時的な DNS resolution delays や service discovery issues が発生する可能性がある
   * **Solution**: CoreDNS settings を最適化し、TTL values を調整し、service mesh を検討する
6. **Monitoring and Alert Gaps**:
   * **Issue**: monitoring agents または log collectors が新しい node group に自動的に install されない可能性がある
   * **Solution**: DaemonSet ベースの monitoring tools を使用し、node group launch template に agent installation scripts を含める
7. **Lack of Rollback Plan**:
   * **Issue**: upgrade が失敗した場合の rollback method がない
   * **Solution**: 既存 node group をすぐに削除せず、一定期間保持し、state snapshots を作成し、rollback procedures を document 化する

**Implementation Example (AWS CLI):**

```bash
# 1. Check current node group information
aws eks describe-nodegroup --cluster-name my-cluster --nodegroup-name blue-nodegroup

# 2. Create new node group (green)
aws eks create-nodegroup \
    --cluster-name my-cluster \
    --nodegroup-name green-nodegroup \
    --scaling-config minSize=3,maxSize=10,desiredSize=5 \
    --subnets subnet-xxxx subnet-yyyy \
    --instance-types t3.large \
    --ami-type AL2_x86_64 \
    --node-role arn:aws:iam::123456789012:role/EKS-NodeInstanceRole \
    --labels environment=prod,app=myapp \
    --tags "k8s.io/cluster-autoscaler/enabled=true,k8s.io/cluster-autoscaler/my-cluster=owned"

# 3. Check node group status
aws eks describe-nodegroup --cluster-name my-cluster --nodegroup-name green-nodegroup

# 4. Cordon existing nodes (using kubectl)
# Get node list
kubectl get nodes -l eks.amazonaws.com/nodegroup=blue-nodegroup

# Cordon each node
kubectl cordon <node-name>

# 5. Drain existing nodes
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# 6. Verify all pods have moved to new nodes
kubectl get pods -o wide

# 7. Delete existing node group
aws eks delete-nodegroup --cluster-name my-cluster --nodegroup-name blue-nodegroup
```

Blue/green upgrades は downtime を最小化し rollback capability を提供しますが、追加 resources が必要であり complexity も増します。十分な planning と testing が必要であり、特に large-scale production environments では段階的な approach が推奨されます。

</details>
