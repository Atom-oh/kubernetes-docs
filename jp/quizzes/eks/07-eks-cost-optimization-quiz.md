# Amazon EKS のコスト最適化クイズ

> **最終更新日**: 2026年10月16日

以下の例は互いに独立した設定案であり、連続して適用する構成や、実行済みのデプロイ、実測した削減効果を示すものではありません。同じワークロードにすべての例を順に適用しないでください。変更は既存リソースの管理者と調整し、プレースホルダーのアプリケーションイメージやアプリケーション固有のフックを置き換え、アカウント、コンテキスト、リージョン、互換性のあるコントローラーを確認し、運用に使う前に動作をテストしてください。

このクイズでは、Amazon EKS クラスターのコストを最適化する戦略、ツール、ベストプラクティスへの理解を確認します。

## クイズの概要
- コンピューティングリソースの最適化
- ストレージコストの最適化
- ネットワークコストの最適化
- クラスター管理コストの最適化
- コストの監視と分析
- コスト最適化のツールとベストプラクティス

## 選択問題

### 1. Amazon EKS のコンピューティングコストを最適化するうえで、最も効果的な戦略はどれですか？

- A. 常に最大サイズのインスタンスタイプを使う
- B. すべてのワークロードでオンデマンドインスタンスだけを使う
- C. Spot インスタンス、適正サイズへの調整、自動スケーリングを組み合わせる
- D. すべてのワークロードを単一のノードグループに集約する
<details>
<summary>回答を表示</summary>

**回答: C. Spot インスタンス、適正サイズへの調整、自動スケーリングを組み合わせる**

**解説:**
Amazon EKS のコンピューティングコストを最適化するには、Spot インスタンス、適正サイズへの調整、自動スケーリングを組み合わせるのが最も効果的です。中断への耐性と利用可能なキャパシティが許すワークロードに限って Spot を使い、節約額をワークロードの SLO に照らして確認します。この組み合わせや、広告される最大割引率によって、コスト低下や性能維持が保証されるわけではありません。

**主なコンピューティング最適化戦略:**

1. **Spot インスタンスの活用**:
   - オンデマンドと比べ、最大90%のコスト削減が可能
   - 障害許容性のあるワークロードに適する
   - 中断への対応を実装する

2. **適正サイズへの調整**:
   - 実際のリソース使用量に基づいてインスタンスを選択する
   - 過剰にプロビジョニングされたリソースをなくす
   - リソースのrequestsとlimitsを最適化する

3. **自動スケーリングの実装**:
   - Cluster AutoscalerまたはKarpenterによるノード単位のスケーリング
   - Horizontal Pod AutoscalerによるPod単位のスケーリング
   - 需要に応じたリソース調整

NodePoolとEC2NodeClassを使うには、互換性のあるKarpenterコントローラーとCRD、範囲を絞ったコントローラー用IAM権限、ノードロール、ディスカバリー用リソース、中断通知キューがすでに必要です。現在の互換性マトリクスでは、EKS 1.36にKarpenter 1.13以上が必要です。`al2023@latest`は参照先が変わるセレクターです。管理されたロールアウトでは、解決後のAMIを確認し、テスト済みのエイリアスまたはAMIに固定してください。インスタンス一覧とキャパシティ上限は説明用であり、支出上限ではありません。マネージドノードグループは独自に中断処理を行うため、Karpenter管理ノードに別のハンドラーを重ねないでください。

HPAにはリソースメトリクスとrequestsが必要です。CPUとメモリの目標を使う場合、HPAはより大きな希望レプリカ数を選びます。以下のVPAは**Off**であり、これらの分母を変えずに推奨値を示します。`Auto`は非推奨となり、`Recreate`などの明示的なモードが推奨されています。CPU/メモリの自動変更はHPAと調整してください。preStopフックは終了猶予期間を消費するため、Spotの期限内に終了できることやクリーンアップ成功を保証しません。

**実装方法:**

1. **Spot インスタンスを使うノードグループの作成**:
   ```bash
   # Create Spot Instance node group using eksctl
   eksctl create nodegroup \
     --cluster my-cluster \
     --region us-west-2 \
     --managed \
     --name spot-ng \
     --node-type m5.large \
     --nodes-min 2 \
     --nodes-max 10 \
     --spot
   ```

2. **Karpenterのデプロイと設定**:
   ```yaml
   # Karpenter NodePool
   apiVersion: karpenter.sh/v1
   kind: NodePool
   metadata:
     name: default
   spec:
     template:
       spec:
         requirements:
           - key: "karpenter.sh/capacity-type"
             operator: In
             values: ["spot"]
           - key: "kubernetes.io/arch"
             operator: In
             values: ["amd64"]
           - key: "kubernetes.io/os"
             operator: In
             values: ["linux"]
           - key: "node.kubernetes.io/instance-type"
             operator: In
             values: ["m5.large", "m5a.large", "m5d.large", "m5ad.large", "m4.large"]
         nodeClassRef:
           group: karpenter.k8s.aws
           kind: EC2NodeClass
           name: default
     limits:
       cpu: 1000
       memory: 1000Gi
     disruption:
       consolidationPolicy: WhenEmpty
       consolidateAfter: 30s
   ---
   # Karpenter NodeClass
   apiVersion: karpenter.k8s.aws/v1
   kind: EC2NodeClass
   metadata:
     name: default
   spec:
     amiSelectorTerms:
       - alias: al2023@latest
     role: KarpenterNodeRole
     subnetSelectorTerms:
       - tags:
           karpenter.sh/discovery: my-cluster
     securityGroupSelectorTerms:
       - tags:
           karpenter.sh/discovery: my-cluster
     tags:
       karpenter.sh/discovery: my-cluster
   ```

3. **Horizontal Pod Autoscalerの設定**:
   ```yaml
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: web-app
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: web-app
     minReplicas: 2
     maxReplicas: 10
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 70
     - type: Resource
       resource:
         name: memory
         target:
           type: Utilization
           averageUtilization: 80
   ```

4. **Vertical Pod Autoscalerの設定**:
   ```yaml
   apiVersion: autoscaling.k8s.io/v1
   kind: VerticalPodAutoscaler
   metadata:
     name: web-app-vpa
   spec:
     targetRef:
       apiVersion: "apps/v1"
       kind: Deployment
       name: web-app
     updatePolicy:
       updateMode: "Off"
     resourcePolicy:
       containerPolicies:
       - containerName: '*'
         minAllowed:
           cpu: 50m
           memory: 100Mi
         maxAllowed:
           cpu: 1
           memory: 1Gi
         controlledResources: ["cpu", "memory"]
   ```

**ワークロードの種類別の最適化戦略:**

1. **ステートレスアプリケーション**:
   - Spotインスタンスを優先する
   - 水平スケーリングを実装する
   - 複数のアベイラビリティーゾーンに分散して配置する

2. **ステートフルアプリケーション**:
   - オンデマンドとSpotインスタンスを組み合わせる
   - 適切なインスタンスタイプを選択する
   - ストレージ性能とコストのバランスを取る

3. **バッチジョブ**:
   - Spotインスタンスを最大限活用する
   - ジョブの再試行を実装する
   - 締め切りとキャパシティの可用性に合わせて実行をスケジュールする。オフピークのオンデマンド料金が一般に適用されるわけではありません。

**ベストプラクティス:**

1. **リソースのrequestsとlimitsを最適化する**:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
   spec:
     replicas: 3
     template:
       spec:
         containers:
         - name: web-app
           image: web-app:1.0
           resources:
             requests:
               cpu: 100m
               memory: 256Mi
             limits:
               cpu: 500m
               memory: 512Mi
       metadata:
         labels:
           app: web-app
     selector:
       matchLabels:
         app: web-app
   ```

2. **ノードアフィニティとPodの分散を最適化する**:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
   spec:
     replicas: 3
     template:
       spec:
         affinity:
           nodeAffinity:
             preferredDuringSchedulingIgnoredDuringExecution:
             - weight: 1
               preference:
                 matchExpressions:
                 - key: node.kubernetes.io/instance-type
                   operator: In
                   values:
                   - m5.large
                   - m5a.large
           podAntiAffinity:
             preferredDuringSchedulingIgnoredDuringExecution:
             - weight: 100
               podAffinityTerm:
                 labelSelector:
                   matchExpressions:
                   - key: app
                     operator: In
                     values:
                     - web-app
                 topologyKey: kubernetes.io/hostname
         containers:
         - name: web-app
           image: registry.example.com/team/web-app:REVIEWED_TAG
       metadata:
         labels:
           app: web-app
     selector:
       matchLabels:
         app: web-app
   ```

3. **Spotインスタンスの中断に対処する**:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
   spec:
     replicas: 3
     template:
       spec:
         terminationGracePeriodSeconds: 60
         containers:
         - name: web-app
           image: web-app:1.0
           lifecycle:
             preStop:
               exec:
                 command:
                 - /bin/sh
                 - -c
                 - sleep 10; /app/cleanup.sh
       metadata:
         labels:
           app: web-app
     selector:
       matchLabels:
         app: web-app
   ```

**実装上の追加考慮事項**

- eksctlの設定では、システムワークロード向けのオンデマンドグループと、分散させたSpotグループを既存クラスターに追加できます。ラベルだけではワークロードを分離できません。セレクターとtolerationを意図的に設定してください。システムコントローラーが起動する前に、起動時に必要な唯一のノードへtaintを設定しないでください。
- 既存のTerraformモジュールでは、`aws_eks_node_group`に`capacity_type = "SPOT"`と`scaling_config`を設定できます。クラスター、ノードIAMロールとポリシー、サブネット、プロバイダーはあらかじめ定義されている必要があります。`desired_size`をオートスケーラーが管理する方法を調整してください。
- EKSノードグループのタグは、Cluster Autoscalerがディスカバリーに使う**実際のASG**タグの代わりにはなりません。変更前にASGと既存タグの管理者を確認してください。オートスケーラーのポリシーは専用のコントローラーIDに付与します。ノードロールのアドオン権限を意図したIDとして使わないでください。
- AWSの読み取り/ディスカバリー操作と、2つのスケーリング書き込み操作を分けてください。公式の[EKSポリシー](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)のように、`autoscaling:SetDesiredCapacity`と`autoscaling:TerminateInstanceInAutoScalingGroup`を、レビュー済みの有効化タグやクラスター所有タグを持つASGに限定します。

次のeksctl断片は既存クラスターにノードグループを追加します。所有者のプライベートサブネット、ノードIAMポリシー、既存グループ/ASGタグを確認してください。単独でクラスターを作成する手順ではありません。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: system-ng
  instanceType: m5.large
  desiredCapacity: 2
  minSize: 2
  maxSize: 4
  labels:
    workload-type: system
  privateNetworking: true
- name: app-spot-ng
  instanceTypes:
  - m5.large
  - m5a.large
  - m5d.large
  - m4.large
  spot: true
  desiredCapacity: 3
  minSize: 1
  maxSize: 10
  labels:
    workload-type: application
  privateNetworking: true
```

Terraform断片は、名前付きのクラスター/ノードロールリソース、プライベートサブネット変数、プロバイダーが管理モジュールにすでにあることを前提としています。IAMポリシーは専用のコントローラーIDにアタッチしてください。

```hcl
# Spot managed node group
resource "aws_eks_node_group" "spot" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "spot-ng"
  node_role_arn   = aws_iam_role.node_role.arn
  subnet_ids      = var.private_subnet_ids

  capacity_type  = "SPOT"
  instance_types = ["m5.large", "m5a.large", "m5d.large", "m4.large"]

  scaling_config {
    desired_size = 3
    min_size     = 1
    max_size     = 10
  }

  labels = {
    "workload-type" = "application"
  }

  tags = {
    Team        = "platform"
    Environment = "development"
  }
}

# Cluster Autoscaler IAM policy
resource "aws_iam_policy" "cluster_autoscaler" {
  name        = "EKSClusterAutoscalerPolicy"
  description = "Policy for Cluster Autoscaler"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "autoscaling:DescribeAutoScalingGroups",
          "autoscaling:DescribeAutoScalingInstances",
          "autoscaling:DescribeLaunchConfigurations",
          "autoscaling:DescribeTags",
          "autoscaling:DescribeScalingActivities",
          "ec2:DescribeImages",
          "ec2:DescribeInstanceTypes",
          "ec2:GetInstanceTypesFromInstanceRequirements",
          "eks:DescribeNodegroup",
          "ec2:DescribeLaunchTemplateVersions"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "autoscaling:SetDesiredCapacity",
          "autoscaling:TerminateInstanceInAutoScalingGroup"
        ],
        Resource = "*",
        Condition = {
          StringEquals = {
            "aws:ResourceTag/k8s.io/cluster-autoscaler/enabled"                      = "true",
            "aws:ResourceTag/k8s.io/cluster-autoscaler/${aws_eks_cluster.main.name}" = "owned"
          }
        }
      }
    ]
  })
}
```

他の選択肢の問題点:
- **A. 常に最大サイズのインスタンスタイプを使う**: 不要なコストを伴う過剰プロビジョニングにつながり、ワークロード要件に合わないことがあります。
- **B. すべてのワークロードでオンデマンドインスタンスだけを使う**: オンデマンドインスタンスはSpotより高コストであり、多くのワークロードはSpot上でも効果的に実行できます。
- **D. すべてのワークロードを単一のノードグループに集約する**: 多様なワークロード要件を満たしにくくなり、リソース分離が不足し、コスト配分と最適化も難しくなります。
</details>

### 2. Amazon EKSのストレージコストを最適化するうえで、最も効果的な方法はどれですか？

- A. すべてのワークロードに最も安価なストレージタイプを使う
- B. すべてのデータをS3へ移行する
- C. ワークロード要件に合うストレージタイプを選び、ライフサイクル管理を実装する
- D. すべてのボリュームサイズを最小化する
<details>
<summary>回答を表示</summary>

**回答: C. ワークロード要件に合うストレージタイプを選び、ライフサイクル管理を実装する**

**解説:**
Amazon EKSのストレージコストを最適化するには、ワークロード要件に合うストレージタイプを選び、ライフサイクル管理を実装します。性能要件を満たしながらコストを抑え、データの価値とアクセスパターンに応じたストレージ階層を利用できます。

**主なストレージ最適化戦略:**

1. **ワークロードに適したストレージタイプを選ぶ**:
   - 高性能が必要な場合: io2、gp3 (EBS)
   - 共有アクセスが必要な場合: EFS
   - 大規模データ処理: FSx for Lustre
   - アーカイブデータ: S3、S3 Glacier

2. **ストレージのライフサイクル管理**:
   - 頻繁にアクセスするデータ: 高性能ストレージ
   - ときどきアクセスするデータ: 標準ストレージ
   - ほとんどアクセスしないデータ: 低コストのアーカイブストレージ

3. **ボリュームを効率的に管理する**:
   - 適切なボリュームサイズを設定する
   - 未使用ボリュームを特定して削除する
   - スナップショットのライフサイクルを管理する

StorageClassの例を使うには、CSIドライバーが導入済みで、IAM/KMS/トポロジー設定が正しい必要があります。`WaitForFirstConsumer`はEBSのプロビジョニングをスケジューリングに合わせます。`Retain`では解放後も所有者が処理するまで料金が発生します。バインド済みPVCは、クラスを変更したりインプレースで縮小したりできません。スナップショットからの復元や、サポート対象のボリュームタイプ変更には、所有者がレビューした移行と復元テストが必要です。Auto Modeは別のEBSプロビジョナーを使うため、標準CSIの例に黙って置き換えないでください。

`create-file-system`コマンドに`--lifecycle-policies`オプションはありません。既存ファイルシステムに対して`put-lifecycle-configuration`を使い、以下に示すように必要なポリシー配列全体を保持します。S3の移行では、最低保持期間/サイズ、リクエスト料金、バージョニング、復旧遅延も確認してください。ライフサイクル設定を置き換えるときは、無関係なルールを残します。

**実装方法:**

1. **EBSボリュームの最適化**:
   ```yaml
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: ebs-gp3
   provisioner: ebs.csi.aws.com
   parameters:
     type: gp3
     iops: '3000'
     throughput: '125'
     encrypted: 'true'
   allowVolumeExpansion: true
   volumeBindingMode: WaitForFirstConsumer
   reclaimPolicy: Retain
   ```

2. **EFSのライフサイクル管理**:
   ```bash
   set -euo pipefail
   : "${AWS_REGION:?Set the reviewed Region}"
   : "${FILE_SYSTEM_ID:?Set the existing reviewed EFS filesystem ID}"
   aws efs describe-lifecycle-configuration --region "$AWS_REGION" \
     --file-system-id "$FILE_SYSTEM_ID" --query LifecyclePolicies --output json \
     > efs-lifecycle-policies.json
   # Edit the exported array; an IA entry is {"TransitionToIA":"AFTER_30_DAYS"}.
   # Preserve required Archive/return-to-primary entries before submitting the whole policy.
   aws efs put-lifecycle-configuration --region "$AWS_REGION" \
     --file-system-id "$FILE_SYSTEM_ID" \
     --lifecycle-policies file://efs-lifecycle-policies.json
   ```

3. **S3ライフサイクルポリシー**:
   ```json
   {
     "Rules": [
       {
         "ID": "Move to IA after 30 days, Glacier after 90 days",
         "Status": "Enabled",
         "Transitions": [
           {
             "Days": 30,
             "StorageClass": "STANDARD_IA"
           },
           {
             "Days": 90,
             "StorageClass": "GLACIER"
           }
         ],
         "Expiration": {
           "Days": 365
         },
         "Filter": {
           "Prefix": "eks-backups/"
         }
       }
     ]
   }
   ```

4. **EBSスナップショットのライフサイクル管理**:
   ```yaml
   apiVersion: snapshot.storage.k8s.io/v1
   kind: VolumeSnapshotClass
   metadata:
     name: ebs-snapshot
   driver: ebs.csi.aws.com
   deletionPolicy: Delete
   ```

**スナップショットの定期取得とストレージの確認**

次のスナップショットスケジュールは、所有者が既存の`team-a/database-data` PVC、標準EBS CSIドライバー、スナップショットコントローラー/CRD、`ebs-snapshot`クラスを確認するまで停止状態です。マウントするテンプレートでは固定名の衝突を避けるため`generateName`を使います。RoleはこのNamespaceでのスナップショット作成を許可しますが、参照元PVCフィールドを制限するものではありません。アプリケーション整合性を保つための静止化と復元検証は別途必要です。Jobの成功で確認できるのはAPIリソースの作成までであり、スナップショットの準備完了ではありません。`readyToUse`とエラーを別々に監視してください。Job履歴の保持数によってVolumeSnapshot/EBSスナップショットが期限切れになることは**ありません**。スケジュールを有効にする前に保持期間と復旧の担当を定義してください。`deletionPolicy: Delete`では、Kubernetes側のスナップショットを削除すると、バックエンドのスナップショットも削除されます。

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: snapshot-creator
  namespace: team-a
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: snapshot-creator
  namespace: team-a
rules:
- apiGroups: ["snapshot.storage.k8s.io"]
  resources: ["volumesnapshots"]
  verbs: ["create"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: snapshot-creator
  namespace: team-a
subjects:
- kind: ServiceAccount
  name: snapshot-creator
  namespace: team-a
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: snapshot-creator
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: snapshot-templates
  namespace: team-a
data:
  snapshot.yaml: |
    apiVersion: snapshot.storage.k8s.io/v1
    kind: VolumeSnapshot
    metadata:
      generateName: database-data-
      namespace: team-a
    spec:
      volumeSnapshotClassName: ebs-snapshot
      source:
        persistentVolumeClaimName: database-data
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: volume-snapshot
  namespace: team-a
spec:
  suspend: true
  schedule: "0 1 * * *"
  timeZone: Etc/UTC
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 1800
  successfulJobsHistoryLimit: 1
  failedJobsHistoryLimit: 2
  jobTemplate:
    spec:
      backoffLimit: 0
      activeDeadlineSeconds: 120
      template:
        spec:
          serviceAccountName: snapshot-creator
          restartPolicy: Never
          securityContext:
            runAsNonRoot: true
            runAsUser: 65532
            seccompProfile:
              type: RuntimeDefault
          containers:
          - name: snapshot-creator
            image: registry.k8s.io/kubectl:v1.36.2
            command: ["kubectl"]
            args: ["create", "-f", "/snapshots/snapshot.yaml", "--namespace=team-a"]
            env:
            - name: HOME
              value: /tmp
            securityContext:
              allowPrivilegeEscalation: false
              readOnlyRootFilesystem: true
              capabilities:
                drop: ["ALL"]
            resources:
              requests:
                cpu: 10m
                memory: 32Mi
              limits:
                memory: 128Mi
            volumeMounts:
            - name: snapshots
              mountPath: /snapshots
              readOnly: true
            - name: tmp
              mountPath: /tmp
          volumes:
          - name: snapshots
            configMap:
              name: snapshot-templates
          - name: tmp
            emptyDir: {}
```

ストレージはアクセス方法と復旧目標に合わせます。データベースにはio2/gp3のIOPS、共有WebコンテンツにはEFS、ログ/アーカイブにはS3、分析/AIにはFSx for LustreやEBSのスループットが必要な場合があります。ホット/ウォーム/コールドは分類例であり、EBS→EFS→S3への自動移行パイプラインではありません。参照されている`efs-standard`/`ebs-io2`クラスは別途準備してください。EFSのPVC要求`100Gi`はファイルシステムのクォータを設定したり、その容量分を購入したりするものではありません。PVCラベルがAWSの請求タグに自動変換されることもありません。

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: hot-data
  namespace: team-a
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 10Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: warm-data
  namespace: team-a
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: efs-standard
  resources:
    requests:
      storage: 100Gi
```

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: database-data
  labels:
    app: database
    environment: production
    cost-center: cc-123
  namespace: team-a
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-io2
  resources:
    requests:
      storage: 100Gi
```

次のTerraform断片を使うには、設定済みのプロバイダー/呼び出し元IDと、レビュー済みのリソース所有関係が必要です。マウントターゲット、ネットワーク/IAMアクセス、アプリケーションのバックアップ、保持期間は別途準備します。本番用ストレージを完全にデプロイする例ではありません。

```hcl
# Standard EBS CSI gp3 StorageClass
resource "kubernetes_storage_class_v1" "ebs_gp3" {
  metadata {
    name = "ebs-gp3"
  }
  storage_provisioner = "ebs.csi.aws.com"
  parameters = {
    type       = "gp3"
    iops       = "3000"
    throughput = "125"
    encrypted  = "true"
  }
  allow_volume_expansion = true
  volume_binding_mode    = "WaitForFirstConsumer"
  reclaim_policy         = "Retain"
}

# Encrypted EFS filesystem
resource "aws_efs_file_system" "eks_efs" {
  creation_token = "eks-efs"
  encrypted      = true

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  tags = {
    Name = "eks-efs"
  }
}

# S3 bucket and lifecycle policy
resource "aws_s3_bucket" "eks_data" {
  bucket = "eks-data-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name = "eks-data"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "eks_data_lifecycle" {
  bucket = aws_s3_bucket.eks_data.id

  rule {
    id     = "archive-rule"
    status = "Enabled"

    filter {
      prefix = "eks-backups/"
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}
```

**PVC候補の読み取り専用インベントリ**

以下を`unreferenced_pvcs.py`として保存し、明示したコンテキスト/Namespaceのコマンドで実行します。指定した最新のPodスナップショットから参照されていないBound PVCを、`(namespace, name)`で比較して報告し、PVC以外のボリュームも処理します。Kubernetesに標準の`pv_used`アノテーションはありません。一覧取得はアトミックではなく、将来の利用者やスケールダウン済みコントローラー、保留中のジョブ、バックアップ/復旧要件を含まない場合があります。この出力だけで削除を決めてはいけません。EBS候補については[EKS06の質問6](06-eks-monitoring-logging-quiz.md)にある、アカウント/タグで範囲を絞ったクエリを使ってください。`available`は未接続を意味し、未使用とは限りません。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Select the reviewed cluster context}"
: "${KUBE_NAMESPACE:?Select the reviewed namespace}"
kubectl --context "$KUBE_CONTEXT" --namespace "$KUBE_NAMESPACE" \
  get pvc --chunk-size=500 -o json > pvcs.json
kubectl --context "$KUBE_CONTEXT" --namespace "$KUBE_NAMESPACE" \
  get pods --chunk-size=500 -o json > pods.json
python3 unreferenced_pvcs.py
```

```python
import json
from pathlib import Path


def unreferenced_claims(claims, pods):
    referenced = set()
    for pod in pods["items"]:
        namespace = pod["metadata"]["namespace"]
        for volume in pod.get("spec", {}).get("volumes") or []:
            claim = volume.get("persistentVolumeClaim")
            if claim:
                referenced.add((namespace, claim["claimName"]))
    result = []
    for claim in claims["items"]:
        metadata = claim["metadata"]
        identity = (metadata["namespace"], metadata["name"])
        if claim.get("status", {}).get("phase") != "Bound" or identity in referenced:
            continue
        spec = claim.get("spec", {})
        result.append({
            "namespace": identity[0],
            "name": identity[1],
            "storageClass": spec.get("storageClassName"),
            "requested": ((spec.get("resources") or {}).get("requests") or {}).get("storage"),
            "meaning": "not referenced by the supplied current Pod snapshot; review required",
        })
    return result


if __name__ == "__main__":
    claims = json.loads(Path("pvcs.json").read_text())
    pods = json.loads(Path("pods.json").read_text())
    print(json.dumps(unreferenced_claims(claims, pods), indent=2))
```

他の選択肢の問題点:
- **A. すべてのワークロードに最も安価なストレージタイプを使う**: 最安のストレージでは性能要件を満たせず、アプリケーション性能の低下やビジネスへの影響を招くことがあります。
- **B. すべてのデータをS3へ移行する**: S3は一部のデータには適しますが、低レイテンシーが必要なワークロードやブロックストレージを必要とするアプリケーションには適しません。
- **D. すべてのボリュームサイズを最小化する**: サイズを小さくしすぎると容量不足になります。また、gp2など一部のボリュームタイプはサイズによって性能が決まります。
</details>

### 3. Amazon EKSのネットワークコストを最適化するうえで、最も効果的な戦略はどれですか？

- A. すべてのトラフィックに最も高価なネットワーク帯域を使う
- B. すべてのサービスを単一のアベイラビリティーゾーンに配置する
- C. トラフィックパターンを最適化し、データ転送料を抑え、VPCエンドポイントを利用する
- D. すべてのネットワークトラフィックを遮断する
<details>
<summary>回答を表示</summary>

**回答: C. トラフィックパターンを最適化し、データ転送料を抑え、VPCエンドポイントを利用する**

**解説:**
Amazon EKSのネットワークコストを最適化するには、トラフィックパターンを最適化し、データ転送料を抑え、VPCエンドポイントを利用するのが効果的です。AWSのネットワーク料金体系を踏まえてトラフィック効率を高め、不要なコストを減らせます。

**主なネットワークコスト最適化戦略:**

1. **トラフィックパターンの最適化**:
   - アベイラビリティーゾーン間のトラフィックを減らす
   - リージョン間のトラフィックを減らす
   - ローカリティを考慮したルーティングを実装する

2. **データ転送料の抑制**:
   - 圧縮と効率的なデータ形式を使う
   - キャッシュを実装する
   - 不要なデータ転送をなくす

3. **VPCエンドポイントの利用**:
   - AWSサービスへプライベート接続する
   - インターネットゲートウェイを経由しない
   - データ転送料を抑える

Topology spreadはPodの配置を制御しますが、Serviceトラフィックの接続先エンドポイントを選ぶ機能ではありません。`spec.topologyKeys`は削除されています。この例は`trafficDistribution: PreferSameZone`（Kubernetes 1.35以降で安定版）をフォールバック付きで使います。ゾーン間通信がゼロになる保証ではありません。実際のプロキシ/CNIの動作と可用性制約を確認してください。

S3/DynamoDBのゲートウェイエンドポイントとインターフェイスエンドポイントでは料金体系が異なります。ECRからイメージを取得するには、`ecr.api`、`ecr.dkr`、S3への接続、プライベートDNS、対象のノード/PodからTCP 443で接続できるエンドポイントセキュリティグループが必要です。CLI例にはインターフェイスエンドポイントが1つだけ示されています。以下のTerraform断片のようにDKR用も用意してください。エンドポイントポリシーと実際のリージョン別通信/料金を確認してください。「プライベート」だから無料とは限りません。

**実装方法:**

1. **アベイラビリティーゾーンを考慮したPod配置**:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
   spec:
     replicas: 6
     template:
       spec:
         topologySpreadConstraints:
         - maxSkew: 1
           topologyKey: topology.kubernetes.io/zone
           whenUnsatisfiable: DoNotSchedule
           labelSelector:
             matchLabels:
               app: web-app
         containers:
         - name: web-app
           image: registry.example.com/team/web-app:REVIEWED_TAG
       metadata:
         labels:
           app: web-app
     selector:
       matchLabels:
         app: web-app
   ```

2. **Serviceトポロジールーティング**:
   ```yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: web-app
   spec:
     selector:
       app: web-app
     ports:
     - port: 80
       targetPort: 8080
     trafficDistribution: PreferSameZone
   ```

3. **VPCエンドポイントの設定**:
   ```bash
   # Create S3 VPC endpoint
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-12345678 \
     --service-name com.amazonaws.us-west-2.s3 \
     --route-table-ids rtb-12345678

   # Create DynamoDB VPC endpoint
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-12345678 \
     --service-name com.amazonaws.us-west-2.dynamodb \
     --route-table-ids rtb-12345678

   # Create ECR API VPC endpoint
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-12345678 \
     --service-name com.amazonaws.us-west-2.ecr.api \
     --vpc-endpoint-type Interface \
     --subnet-ids subnet-12345678 subnet-87654321 \
     --security-group-ids sg-12345678 \
     --private-dns-enabled
   ```

4. **Istioによるローカリティルーティング**:
   ```yaml
   apiVersion: networking.istio.io/v1
   kind: DestinationRule
   metadata:
     name: web-app
   spec:
     host: web-app
     trafficPolicy:
       loadBalancer:
         simple: LEAST_REQUEST
         localityLbSetting:
           enabled: true
       outlierDetection:
         consecutive5xxErrors: 5
         interval: 5s
         baseEjectionTime: 30s
   ```

Istioのローカリティフェイルオーバーには、エンドポイントのローカリティ情報とアウトライヤー検出が必要です。`failover.from/to`が指定するのは**リージョン**なので、ここへAZ名を指定するのは誤りです。上記のDestinationRuleは、アウトライヤー検出とともに同じゾーンを他のゾーン/リージョンより優先するデフォルトのローカリティ優先順位を使います。サンプルのエジェクション閾値はワークロードでテストしてください。これはkube-proxyのServiceトラフィック分散とは別の選択肢であり、転送料を減らすだけならサービスメッシュは必須ではありません。

**ルーティング、エンドポイント、請求の追加例**

NetworkPolicyは、同一Namespace内のfrontend→API→database通信と、標準CoreDNS Deploymentへの経路を許可します。ほかの必要な依存関係も追加し、CNIがポリシーを適用していることを確認してください。Auto ModeのノードローカルDNSなど別のリゾルバー経路には、個別に適切な許可が必要です。セレクターは実際の管理ラベルに合わせてください。

VirtualServiceは最初に一致するルールを評価するため、premiumの一致条件をcatch-allより前に置き、対応するDestinationRuleサブセットも定義します。ワークロードには該当するバージョンラベルが必要です。クライアントが送るエンドユーザーヘッダーは権限の証明になりません。認可はサーバー側で行ってください。EnvoyFilterは実際のingress gatewayのNamespace/ラベルを対象にし、インストール済みIstio/Envoyバージョンとの互換性確認が必要です。ゲートウェイでHTTP応答を圧縮します。アウトバウンドsidecarの圧縮機能を入れるだけではアップロードは圧縮されません。旧式のcontent_length/content_typeフィールドは非推奨ですが削除済みではありません。この例はresponse_direction_config/common_configを使います。CPU、レイテンシー、セキュリティ、プロトコルへの影響をテストしてください。

Terraform断片では、VPC、プライベートサブネット、エンドポイントセキュリティグループ、ルートテーブルが管理モジュールにすでに存在することを前提としています。NATとルート関連付けは引き続きそのVPCの所有者が管理します。複数AZで1つのゾーナルNATを共有するのは、可用性と転送料のトレードオフです。高可用性の標準的な節約策とは見なさず、リージョナルNATの選択肢は別途評価してください。

次のコードをnetwork_costs.pyとして保存してください。EXPECTED_CALLER_ACCOUNT、LINKED_ACCOUNT_ID、START_DATE、END_DATEを設定します。reviewed-usage-types.jsonにはCost Explorer/GetDimensionValuesから選んだ正確なUSAGE_TYPE値のJSON配列を入れてください。この例はus-east-1の商用AWS請求エンドポイントを使います。呼び出し元アカウントと読み取り権限を確認してください。APIクエリには料金が発生することがあります。GetCostAndUsageのディメンションではCONTAINSを使えないため、この補助コードは完全一致のEQUALSフィルターを使います。ページネーションを完了し、Decimalの金額、通貨単位、見積もり状態を保持します。結果が空または失敗した場合も、ネットワーク総コストがゼロとは判断できません。アカウント単位の行を特定のEKSクラスターに配賦するには、検証済みタグ/リソースの追加マッピングが必要です。対象は選択した使用タイプだけです。Service名やRegional/Region部分文字列の曖昧な照合では、インターネット、AZ間、リージョン間の料金を確実に分類できません。日付はUTCで、Endは排他的です。利用可能な履歴と請求確定状況を確認してください。従来の100/50/200 USDの閾値は説明用のトリアージ設定であり、一般的な最適化判断ではありません。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: database
spec:
  replicas: 3
  template:
    spec:
      affinity:
        podAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - api-server
              topologyKey: topology.kubernetes.io/zone
      containers:
      - name: database
        image: registry.example.com/team/database:REVIEWED_TAG
    metadata:
      labels:
        app: database
  selector:
    matchLabels:
      app: database
```

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-network-policy
spec:
  podSelector:
    matchLabels:
      app: api-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
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

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-service
spec:
  hosts:
  - api-service
  http:
  - match:
    - headers:
        end-user:
          exact: premium-user
    route:
    - destination:
        host: api-service
        subset: premium
  - route:
    - destination:
        host: api-service
        subset: v1
      weight: 90
    - destination:
        host: api-service
        subset: v2
      weight: 10
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-service-subsets
spec:
  host: api-service
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
  - name: premium
    labels:
      version: premium
```

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: compression-filter
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      istio: ingressgateway
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: GATEWAY
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.compressor
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.compressor.v3.Compressor
          response_direction_config:
            common_config:
              min_content_length: 100
              content_type:
              - application/json
              - text/html
          compressor_library:
            name: gzip
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.compression.gzip.compressor.v3.Gzip
              memory_level: 3
              window_bits: 10
              compression_level: BEST_COMPRESSION
              compression_strategy: DEFAULT_STRATEGY
```

```
+-------------------+    +-------------------+    +-------------------+
|                   |    |                   |    |                   |
|  VPC Endpoint     |    |  NAT Gateway      |    |  Internet         |
|  (AWS Services)   |    |  (External APIs)  |    |  Gateway          |
+-------------------+    +-------------------+    +-------------------+
        |                        |                        |
        v                        v                        v
+---------------------------------------------------------------+
|                                                               |
|                  EKS Cluster VPC                              |
|                                                               |
+---------------------------------------------------------------+
        |                        |                        |
        v                        v                        v
+-------------------+    +-------------------+    +-------------------+
|                   |    |                   |    |                   |
|  AZ-a             |    |  AZ-b             |    |  AZ-c             |
|  Workloads        |    |  Workloads        |    |  Workloads        |
|                   |    |                   |    |                   |
+-------------------+    +-------------------+    +-------------------+
        |                        |                        |
        v                        v                        v
+---------------------------------------------------------------+
|                                                               |
|                  Service Mesh                                 |
|                  (Locality-aware routing)                     |
|                                                               |
+---------------------------------------------------------------+
```

```hcl
# Gateway VPC endpoints
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.region}.s3"
  route_table_ids   = [aws_route_table.private.id]
  vpc_endpoint_type = "Gateway"

  tags = {
    Name = "s3-endpoint"
  }
}

resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.region}.dynamodb"
  route_table_ids   = [aws_route_table.private.id]
  vpc_endpoint_type = "Gateway"

  tags = {
    Name = "dynamodb-endpoint"
  }
}

# Interface VPC endpoints
resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.region}.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name = "ecr-api-endpoint"
  }
}

resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.region}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name = "ecr-dkr-endpoint"
  }
}
```

```python
import json
import os
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import boto3
from botocore.config import Config


def network_cost_rows(client, start, end, linked_account, usage_types):
    for value in [start, end]:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError("Use YYYY-MM-DD dates")
    if start >= end:
        raise ValueError("Start must precede exclusive End")
    if not re.fullmatch(r"[0-9]{12}", linked_account):
        raise ValueError("A reviewed linked account ID is required")
    if not isinstance(usage_types, list) or not usage_types or any(
        not isinstance(value, str) or not value.strip() for value in usage_types
    ):
        raise ValueError("Provide exact reviewed USAGE_TYPE values")
    request = {
        "TimePeriod": {"Start": start, "End": end},
        "Granularity": "DAILY",
        "Metrics": ["UnblendedCost"],
        "GroupBy": [
            {"Type": "DIMENSION", "Key": "SERVICE"},
            {"Type": "DIMENSION", "Key": "USAGE_TYPE"},
        ],
        "Filter": {
            "And": [
                {"Dimensions": {"Key": "LINKED_ACCOUNT", "Values": [linked_account],
                                "MatchOptions": ["EQUALS"]}},
                {"Dimensions": {"Key": "USAGE_TYPE", "Values": usage_types,
                                "MatchOptions": ["EQUALS"]}},
            ]
        },
    }
    rows = []
    seen_tokens = set()
    for _ in range(100):
        response = client.get_cost_and_usage(**request)
        for period in response["ResultsByTime"]:
            for group in period["Groups"]:
                service, usage_type = group["Keys"]
                metric = group["Metrics"]["UnblendedCost"]
                amount = Decimal(metric["Amount"])
                if not amount.is_finite() or not metric["Unit"]:
                    raise ValueError("Invalid monetary amount/unit")
                rows.append({
                    "start": period["TimePeriod"]["Start"],
                    "endExclusive": period["TimePeriod"]["End"],
                    "service": service,
                    "usageType": usage_type,
                    "amount": str(amount),
                    "unit": metric["Unit"],
                    "estimated": period.get("Estimated"),
                })
        token = response.get("NextPageToken")
        if not token:
            return rows
        if token in seen_tokens:
            raise RuntimeError("Repeated pagination token")
        seen_tokens.add(token)
        request["NextPageToken"] = token
    raise RuntimeError("Page limit exceeded; narrow the query")


def main():
    expected_caller = os.environ["EXPECTED_CALLER_ACCOUNT"]
    if not re.fullmatch(r"[0-9]{12}", expected_caller):
        raise ValueError("Set the reviewed calling account")
    session = boto3.Session(region_name="us-east-1")
    config = Config(connect_timeout=5, read_timeout=30,
                    retries={"mode": "standard", "total_max_attempts": 4})
    identity = session.client("sts", config=config).get_caller_identity()
    if identity["Account"] != expected_caller:
        raise RuntimeError("Calling account mismatch")
    usage_types = json.loads(Path("reviewed-usage-types.json").read_text())
    rows = network_cost_rows(
        session.client("ce", config=config),
        os.environ["START_DATE"], os.environ["END_DATE"],
        os.environ["LINKED_ACCOUNT_ID"], usage_types,
    )
    print(json.dumps({"basis": "UnblendedCost", "rows": rows}, indent=2))


if __name__ == "__main__":
    main()
```

他の選択肢の問題点:
- **A. すべてのトラフィックに最も高価なネットワーク帯域を使う**: 不要なコストが発生します。すべてのワークロードが広帯域を必要とするわけではありません。
- **B. すべてのサービスを単一のアベイラビリティーゾーンに配置する**: 重要なワークロードのマルチAZ可用性要件を満たせない場合があります。非重要環境で単一AZを選ぶ場合も、障害許容性を明示的に判断する必要があります。
- **D. すべてのネットワークトラフィックを遮断する**: 現実的ではなく、アプリケーションの機能を大きく制限します。
</details>

### 4. Amazon EKSのクラスター管理コストを最適化するうえで、最も効果的な方法はどれですか？

- A. クラスターをできるだけ多く作成する
- B. すべてのワークロードを単一クラスターに集約する
- C. ワークロード要件に基づいてクラスター数を最適化し、管理負荷を抑える
- D. クラスターを手作業で管理する
<details>
<summary>回答を表示</summary>

**回答: C. ワークロード要件に基づいてクラスター数を最適化し、管理負荷を抑える**

**解説:**
Amazon EKSのクラスター管理コストを最適化するには、ワークロード要件に基づいてクラスター数を最適化し、管理負荷を抑えるのが最も効果的です。ワークロードの分離とセキュリティ要件を満たしながら、管理コストと運用の複雑さのバランスを取れます。

**クラスター管理コストを最適化する主な戦略:**

1. **適切なクラスター数を維持する**:
   - ビジネス要件に基づいてクラスターを分ける
   - 開発、ステージング、本番など環境別に分ける
   - セキュリティとコンプライアンス要件を考慮する

2. **管理負荷を抑える**:
   - 自動化されたクラスター管理ツールを活用する
   - Infrastructure as Code (IaC)を実装する
   - 監視とログを一元化する

3. **クラスターリソースを最適化する**:
   - 適切なコントロールプレーン設定
   - 効率的なノードグループ管理
   - 共有サービスを活用する

eksctlの短いコマンドはクラスター作成の例であり、本番用のネットワーク/IAM設定一式ではありません。AWSカタログからEKSバージョンを選び、[作成ガイド](../../eks/02-eks-cluster-creation.md)でVPCとAPIエンドポイントの公開範囲を確認し、コントローラー権限には専用IDを使ってください。ノードグループのサイズ範囲を指定しても、オートスケーラーが導入されるわけでも、支出上限が設定されるわけでもありません。標準/延長サポート料金、任意のProvisioned Control Planeキャパシティ、共有管理依存関係も比較に影響します。

Terraformの例は、AWSプロバイダーの最低バージョンが**6.59**の確認済みモジュール**21.25.0**を使い、プロバイダーは6.69.1に固定しています。環境の値を推測したデフォルトは設けていません。管理対象のプライベートネットワークとAPI到達性、レビュー済みアクセスエントリ、IAM関連付け済みの互換性ある固定バージョンのアドオン、マネージドノードグループを指定してください。標準EC2ノードには適切なCNI/DNS/proxy経路が必要です。これはAuto Modeの例ではありません。desired-sizeを誰が管理するかをオートスケーラーと調整し、分離モデル上必要な場合はstate/provider IDを分けてください。plan/applyの実施や本番利用可能性を示すものではありません。

**実装方法:**

1. **最適化したEKSクラスター設定**:
   ```bash
   : "${EKS_VERSION:?Select a version offered by the AWS EKS support catalog}"
   # Create optimized cluster using eksctl
   eksctl create cluster \
     --name optimized-cluster \
     --region us-west-2 \
     --version "$EKS_VERSION" \
     --nodegroup-name standard-workers \
     --node-type m5.large \
     --nodes-min 2 \
     --nodes-max 10 \
     --managed
   ```

2. **Terraformによるクラスター管理の自動化**:
   ```hcl
   terraform {
     required_version = ">= 1.5.7"
     required_providers {
       aws = {
         source  = "hashicorp/aws"
         version = "= 6.69.1"
       }
     }
   }

   variable "region" { type = string }
   variable "account_id" { type = string }
   variable "cluster_name" { type = string }
   variable "environment" { type = string }
   variable "kubernetes_version" { type = string }
   variable "vpc_id" { type = string }
   variable "private_subnet_ids" { type = list(string) }
   variable "reviewed_addons" { type = any }
   variable "reviewed_access_entries" { type = any }
   variable "managed_groups" { type = any }

   provider "aws" {
     region              = var.region
     allowed_account_ids = [var.account_id]
   }

   module "eks" {
     source  = "terraform-aws-modules/eks/aws"
     version = "21.25.0"

     name                    = var.cluster_name
     kubernetes_version      = var.kubernetes_version
     endpoint_private_access = true
     endpoint_public_access  = false
     vpc_id                  = var.vpc_id
     subnet_ids              = var.private_subnet_ids

     addons                  = var.reviewed_addons
     access_entries          = var.reviewed_access_entries
     eks_managed_node_groups = var.managed_groups
     tags = {
       Environment = var.environment
       Terraform   = "true"
     }
   }
   ```

3. **GitOpsによるクラスター設定管理**:
   ```yaml
   apiVersion: argoproj.io/v1alpha1
   kind: Application
   metadata:
     name: cluster-config
     namespace: argocd
   spec:
     project: cluster-config
     source:
       repoURL: https://github.com/myorg/cluster-config.git
       targetRevision: REPLACE_WITH_REVIEWED_COMMIT_SHA
       path: configs
     destination:
       server: https://kubernetes.default.svc
       namespace: default
     syncPolicy:
       automated:
         enabled: false
         prune: false
         selfHeal: false
   ```

4. **マルチテナントクラスター設定**:
   ```yaml
   # Namespace resource quota
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: team-a-quota
     namespace: team-a
   spec:
     hard:
       requests.cpu: "10"
       requests.memory: 20Gi
       limits.cpu: "20"
       limits.memory: 40Gi
       pods: "50"
       services: "20"
       persistentvolumeclaims: "30"
   ```

**分離、環境入力、コンテキストに応じた証拠**

Argo CD Applicationの利用には、コントローラーが導入済みで、レビュー済みのリポジトリ/コミットがあり、リポジトリ、宛先、リソース種別を制限する`cluster-config` AppProjectを事前作成している必要があります。プレースホルダーのSHAとリポジトリは使用前に置き換えてください。初回レビューでは自動同期/プルーニングを無効にしています。必要な調整動作だけを所有者と確認して有効にしてください。共有の管理認証情報/コントローラーは、別々のクラスターにも障害やセキュリティ上の影響を広げる可能性があります。

ResourceQuotaはアドミッションとオブジェクト数を制限するもので、請求額やテナント認可を制御しません。NetworkPolicyは複数ポリシーが加算され、CNIによる適用が必要です。Namespaceの例では、`team-a`内、指定した共有Namespaceとの間、および標準CoreDNS Deploymentへの通信を許可します。ノードローカル/Auto ModeのDNSやほかの依存関係は個別に調整してください。共有APIの例では、`team-a`から`app: shared-api`ラベルを持つPodのTCP 8080だけを許可します。以前の広範なallow-allポリシーを残さず、既存ポリシーと整合させてください。RBAC、アドミッション、IAM、信頼境界は別々の制御です。

以下の環境別tfvarsは上記レビュー済みモジュールへの上書き値であり、提供されていない`./modules/eks-cluster`を呼び出す設定ではありません。各環境の入力に適切なアカウント/ネットワーク/バージョン/アドオン/アクセス値をマージし、環境ごとにstate/backendとIDを使います。インスタンス一覧と台数は例示です。中断許容度とリージョンの最新選択肢を確認してください。

収集スクリプトは1回の実行につき**明示した1つのコンテキスト**だけを扱います。`KUBE_CONTEXT`、`EXPECTED_API_SERVER`、`EXPECTED_CALLER_ACCOUNT`、`LINKED_ACCOUNT_ID`、`BILLING_TAG_KEY`、`BILLING_TAG_VALUE`、`START_DATE`、`END_DATE`を設定し、各クラスターで意図的に繰り返してください。APIサーバーURLがレビュー対象のEKSクラスターと一致する必要があります。あるコンテキストの要求リソースをすべてのクラスターの使用量として扱わず、実際のMetrics APIサンプルを時刻/期間/単位とともに保存し、タグで範囲を絞ったCost Explorerの全ページも取得します。Metrics Serverと読み取り権限が必要です。ノードのメトリクス欠損は使用量ゼロではなく、短時間のサンプルはピーク需要の履歴ではありません。

商用AWS請求エンドポイントを使い、End日は排他的です。利用できる請求履歴を選んでください。以前の2023年の日付は設定例であり、実測結果ではありません。タグのマッピングが請求データに存在する必要があり、タグなし/共有コストが含まれない場合があります。金額単位、コスト基準、見積もり状態を保持します。スクリプトは最初のグループだけから総額を推定したり、request/capacity比率を根拠に縮小を推奨したりしません。

大規模な共有クラスターは、重複するコントロールプレーン/共有サービスの負荷を減らせますが、調整の負担と障害影響を大きくします。小規模クラスターは個別の保守やワークロード境界を改善できる一方、キャパシティと運用が重複します。信頼関係、ワークロード、復旧要件に基づいて併用構成を選んでください。クラスター数だけで分離や総コスト削減が保証されるわけではありません。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: namespace-isolation
  namespace: team-a
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector: {}
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: shared-services
  egress:
  - to:
    - podSelector: {}
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: shared-services
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

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: shared-services
  labels:
    name: shared-services
    access: global
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-team-a
  namespace: shared-services
spec:
  podSelector:
    matchLabels:
      app: shared-api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: team-a
    ports:
    - protocol: TCP
      port: 8080
```

```hcl
# production.tfvars: merge with the production account/network/add-on/access inputs.
cluster_name = "production"
environment  = "production"
managed_groups = {
  critical = {
    instance_types = ["m5.large"]
    capacity_type  = "ON_DEMAND"
    min_size       = 3
    max_size       = 10
    desired_size   = 3
  }
  general = {
    instance_types = ["m5.large", "m5a.large"]
    capacity_type  = "SPOT"
    min_size       = 3
    max_size       = 20
    desired_size   = 3
  }
}
```

```hcl
# development.tfvars: use a separate state/backend and the development identity.
cluster_name = "development"
environment  = "development"
managed_groups = {
  default = {
    instance_types = ["m5.large", "m5a.large"]
    capacity_type  = "SPOT"
    min_size       = 1
    max_size       = 5
    desired_size   = 1
  }
}
```

```python
import json
import os
import re
import subprocess
from datetime import date
from pathlib import Path


def read_json(command):
    completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)
    return json.loads(completed.stdout)


def collect(context, expected_server, caller_account, linked_account, tag_key, tag_value, start, end,
            run=subprocess.run, query=read_json):
    if not all([context, expected_server, tag_key, tag_value]):
        raise ValueError("Explicit context, API server, and billing tag mapping are required")
    if not all(re.fullmatch(r"[0-9]{12}", account) for account in [caller_account, linked_account]):
        raise ValueError("Use reviewed 12-digit account IDs")
    if any(date.fromisoformat(value).isoformat() != value for value in [start, end]) or start >= end:
        raise ValueError("Use YYYY-MM-DD with Start before exclusive End")
    server = run(
        ["kubectl", "--context", context, "config", "view", "--minify",
         "--output", "jsonpath={.clusters[0].cluster.server}"],
        check=True, capture_output=True, text=True, timeout=30,
    ).stdout.strip()
    if server != expected_server:
        raise RuntimeError("Kubernetes context/API-server mismatch")
    identity = query(["aws", "sts", "get-caller-identity", "--region", "us-east-1",
                      "--output", "json", "--no-cli-pager"])
    if identity["Account"] != caller_account:
        raise RuntimeError("Calling AWS account mismatch")
    usage = query(["kubectl", "--context", context, "get", "--raw",
                   "/apis/metrics.k8s.io/v1beta1/nodes"])
    if usage.get("kind") != "NodeMetricsList" or not isinstance(usage.get("items"), list):
        raise ValueError("Unexpected node metrics response")
    expression = {"And": [
        {"Dimensions": {"Key": "LINKED_ACCOUNT", "Values": [linked_account], "MatchOptions": ["EQUALS"]}},
        {"Tags": {"Key": tag_key, "Values": [tag_value], "MatchOptions": ["EQUALS"]}},
    ]}
    base = [
        "aws", "ce", "get-cost-and-usage", "--region", "us-east-1",
        "--time-period", json.dumps({"Start": start, "End": end}),
        "--granularity", "MONTHLY", "--metrics", "UnblendedCost",
        "--group-by", "Type=DIMENSION,Key=SERVICE",
        "--filter", json.dumps(expression), "--output", "json", "--no-cli-pager",
    ]
    pages = []
    token = None
    seen = set()
    for _ in range(100):
        page = query(base + (["--next-page-token", token] if token else []))
        if not isinstance(page.get("ResultsByTime"), list):
            raise ValueError("Unexpected cost response")
        pages.append(page)
        token = page.get("NextPageToken")
        if not token:
            return {
                "context": context, "apiServer": server, "nodeUsage": usage,
                "billingScope": expression, "basis": "UnblendedCost", "costPages": pages,
            }
        if token in seen:
            raise RuntimeError("Repeated cost pagination token")
        seen.add(token)
    raise RuntimeError("Page limit exceeded; narrow the query")


if __name__ == "__main__":
    result = collect(
        os.environ["KUBE_CONTEXT"], os.environ["EXPECTED_API_SERVER"],
        os.environ["EXPECTED_CALLER_ACCOUNT"], os.environ["LINKED_ACCOUNT_ID"],
        os.environ["BILLING_TAG_KEY"], os.environ["BILLING_TAG_VALUE"],
        os.environ["START_DATE"], os.environ["END_DATE"],
    )
    Path("cluster-cost-and-usage.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Saved raw metrics and tag-scoped billing pages; no resizing recommendation was made.")
```

他の選択肢の問題点:
- **A. クラスターをできるだけ多く作成する**: クラスターごとのコントロールプレーン料金と管理負荷が増え、リソース使用率が下がります。
- **B. すべてのワークロードを単一クラスターに集約する**: 環境によっては適しますが、セキュリティ要件、ワークロード分離、障害の影響範囲を考慮できません。
- **D. クラスターを手作業で管理する**: 手作業はエラーの可能性を高め、一貫性を損ない、運用負荷を増やします。
</details>

### 5. Amazon EKSのコスト監視と配賦に最も効果的な方法はどれですか？

- A. AWSの請求書だけを確認する
- B. タグ付け戦略、コスト配賦ツール、継続的な監視を実装する
- C. すべてのリソースに同じコストを割り当てる
- D. コストを監視せずにリソースを利用する
<details>
<summary>回答を表示</summary>

**回答: B. タグ付け戦略、コスト配賦ツール、継続的な監視を実装する**

**解説:**
Amazon EKSでコストを監視/配賦するには、タグ付け戦略、コスト配賦ツール、継続的な監視を実装します。これによりコストを正確に追跡し、チームやプロジェクト別に配賦して、最適化の機会を特定できます。

**コスト監視と配賦の主な戦略:**

1. **包括的なタグ付け戦略**:
   - 事業部門、チーム、プロジェクト、環境ごとのタグ
   - 一貫したタグ付けルールを適用する
   - タグ付けを自動化する

2. **コスト配賦ツールの活用**:
   - AWS Cost ExplorerとAWS Budgets
   - KubecostやCloudHealthなどの専用ツール
   - カスタムダッシュボードとレポート

3. **継続的な監視と最適化**:
   - 定期的なコスト確認と分析
   - 異常検出とアラート
   - 最適化の推奨事項を実装する

Kubernetesラベル、AWSリソースタグ、有効化済みの請求タグは別物です。NamespaceラベルがPodやAWSリソースへ自動伝播することはありません。ワークロードラベルはPodテンプレートに設定してください。Organizationsのタグポリシー例は、EKSクラスターを含む対応リソース上で、設定済みタグキー/値を検証します。タグを追加したり、必須タグの適用を設定したりはしません。継承したポリシーを確認し、タグ欠落の制御は別途設けてください。請求タグの有効化/過去分の反映も別の操作です。過去最大12か月分を反映するには、その時点で実際に存在したタグが必要です。

以下のCURコマンドは**従来型CUR**を作成します。Cost ExplorerのダッシュボードでもCUR 2.0のエクスポートでもありません。AWSは従来型CURを引き続きサポートしています。新規設計では[FinOpsガイド](../../ops/13-finops-cost-platform.md)にあるData Exports/CUR 2.0を評価してください。従来型の例には、指定リージョンの既存バケット、レビュー済みCUR配信ポリシー、レポート権限が必要です。バケット、Glueスキーマ、Athena連携、ダッシュボードは作成しません。配信サービス専用ポリシーを使い、従来型サービスのポリシーをCUR 2.0の`bcm-data-exports`ポリシーで代用しないでください。

**実装方法:**

1. **タグ付け戦略の実装**:
   ```yaml
   apiVersion: v1
   kind: Namespace
   metadata:
     name: team-a
     labels:
       team: team-a
       cost-center: cc-123
       environment: production
       project: project-x
   ---
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
     namespace: team-a
     labels:
       app: web-app
       team: team-a
       cost-center: cc-123
       environment: production
       project: project-x
   spec:
     selector:
       matchLabels:
         app: web-app
     template:
       metadata:
         labels:
           app: web-app
           team: team-a
           cost-center: cc-123
           environment: production
           project: project-x
       spec:
         containers:
         - name: web-app
           image: registry.example.com/team/web-app:REVIEWED_TAG
   ```

2. **AWSタグポリシーの設定**:
   ```json
   {
     "tags": {
       "team": {
         "tag_key": {
           "@@assign": "team"
         },
         "tag_value": {
           "@@assign": [
             "team-a",
             "team-b",
             "platform"
           ]
         },
         "enforced_for": {
           "@@assign": [
             "ec2:instance",
             "ec2:volume",
             "eks:cluster"
           ]
         }
       },
       "cost-center": {
         "tag_key": {
           "@@assign": "cost-center"
         },
         "enforced_for": {
           "@@assign": [
             "ec2:instance",
             "ec2:volume",
             "eks:cluster"
           ]
         }
       },
       "environment": {
         "tag_key": {
           "@@assign": "environment"
         },
         "tag_value": {
           "@@assign": [
             "production",
             "staging",
             "development"
           ]
         },
         "enforced_for": {
           "@@assign": [
             "ec2:instance",
             "ec2:volume",
             "eks:cluster"
           ]
         }
       }
     }
   }
   ```

3. **Kubecostのインストールと設定**:
[ソースガイド](../../eks/07-eks-cost-optimization.md)にある確認済みKubecost 3.3.1の導入、または[EKS06の質問6](06-eks-monitoring-logging-quiz.md)にあるOpenCost 1.121.2/chart 2.5.31を使ってください。Kubecost 3.xはClickHouse/finops-agentによる直接収集を使います。2.xのPrometheus値やコマンドラインのライセンストークンはこの構成には含まれません。所有者のいるデプロイを1つ再利用し、移行、ライセンス、ストレージ要件を確認してください。

4. **従来型CURの配信設定**:
   ```bash
   # Create cost and usage report
   aws cur put-report-definition \
     --report-definition '{
       "ReportName": "eks-cost-report",
       "TimeUnit": "HOURLY",
       "Format": "Parquet",
       "Compression": "Parquet",
       "AdditionalSchemaElements": ["RESOURCES"],
       "S3Bucket": "my-cost-reports",
       "S3Prefix": "eks-costs",
       "S3Region": "us-east-1",
       "AdditionalArtifacts": ["ATHENA"],
       "RefreshClosedReports": true,
       "ReportVersioning": "OVERWRITE_REPORT"
     }'
   ```

**配賦の確認と追加設定**

Q4のコンテキスト/アカウント/タグで範囲を絞る収集ツールを再利用し、実際のMetrics APIサンプルと請求データを取得してください。requests/limitsは宣言設定であり実使用量ではありません。request/limit比が0.5未満でも、requestsを減らす根拠にはなりません。現在のレプリカ数と過去の使用量ではなく、同じワークロード、時間枠、単位、対象範囲を比較してください。チーム/コストセンターへの配賦ではタグなし/共有コストも調整します。運用レポート/アラートには[FinOpsガイド](../../ops/13-finops-cost-platform.md)の明示的な収集/検証手順を使い、失敗/欠損データをゼロとして扱わないでください。

以下にある1,000 USD/80%の予算は説明例です。実際に有効化したBudgetsのタグフィルター形式と対象範囲を確認してください。処理済み請求アラートは支出を強制停止する上限ではありません。Terraform断片には既存CURバケット、呼び出し元ID、プロバイダー、リージョン入力が必要です。所有者がAthenaの結果アクセス、保持/暗号化、Glueテーブル、クエリ権限を設定してください。Terraformは`aws_quicksight_dashboard`をサポートしますが、アカウントのエディション、データセット/テンプレート、権限は別途設定が必要です。

```bash
aws resourcegroupstaggingapi tag-resources --region us-west-2 \
  --resource-arn-list arn:aws:eks:us-west-2:123456789012:cluster/my-cluster \
  --tags team=platform,cost-center=cc-100,environment=production
```

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-a-production
  labels:
    team: team-a
    environment: production
    cost-center: cc-123
---
apiVersion: v1
kind: Namespace
metadata:
  name: team-a-development
  labels:
    team: team-a
    environment: development
    cost-center: cc-123
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  template:
    spec:
      containers:
      - name: web-app
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        image: registry.example.com/team/web-app:REVIEWED_TAG
    metadata:
      labels:
        app: web-app
  selector:
    matchLabels:
      app: web-app
```

```bash
aws budgets create-budget \
  --account-id 123456789012 \
  --budget '{
    "BudgetName": "EKS-Monthly",
    "BudgetLimit": {
      "Amount": "1000",
      "Unit": "USD"
    },
    "CostFilters": {
      "TagKeyValue": [
        "user:kubernetes.io/cluster/my-cluster$owned"
      ]
    },
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }' \
  --notifications-with-subscribers '[
    {
      "Notification": {
        "NotificationType": "ACTUAL",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 80,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [
        {
          "SubscriptionType": "EMAIL",
          "Address": "team@example.com"
        }
      ]
    }
  ]'
```

```hcl
resource "aws_cur_report_definition" "eks_cost" {
  report_name                = "eks-cost-report"
  time_unit                  = "HOURLY"
  format                     = "Parquet"
  compression                = "Parquet"
  additional_schema_elements = ["RESOURCES"]
  s3_bucket                  = aws_s3_bucket.cost_reports.id
  s3_prefix                  = "eks-costs"
  s3_region                  = "us-east-1"
  additional_artifacts       = ["ATHENA"]
  refresh_closed_reports     = true
  report_versioning          = "OVERWRITE_REPORT"
}

resource "aws_s3_bucket" "athena_results" {
  bucket = "eks-cost-athena-results-${data.aws_caller_identity.current.account_id}-${var.region}"

  tags = {
    Name = "EKS Cost Athena Results"
  }
}

resource "aws_athena_workgroup" "eks_cost" {
  name = "eks-cost-analysis"

  configuration {
    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.bucket}/output/"
    }
  }
}

```

リージョン別TagResources呼び出しでは対象リージョンを確認し、`FailedResourcesMap`を調べてください。CLIが成功終了しても、要求したすべてのリソースへのタグ付け成功は保証されません。請求配賦の根拠にする前に、実際のリソースタグを確認してください。

**配賦率の推定ダッシュボード**

これは1つのクラスターのPrometheusについて、CPU+メモリの配賦率をUSD/時間で瞬時に推定するものです。請求額でも、Namespace全体のコストでもありません。入力はOpenCostの配賦/価格メトリクス（この例では`job="opencost"`）と、kube-state-metricsのPodラベル（`job="kube-state-metrics"`）です。実際のjobラベルとCPU/メモリ/価格の対象範囲を確認してください。ServiceMonitorの適切なhonor-labels設定でエクスポーターのワークロードNamespaceラベルを保持します。共有バックエンドでは、すべての集計と結合で一貫したクラスターIDが必要です。

最初のvalues断片は、所有するkube-prometheus-stackリリースへマージします。Podのチームラベルは対象を絞り、Podテンプレートに設定してください。Namespaceラベルから自動生成はされません。チームラベルの欠落分は`unassigned`にまとめます。クエリは同一スクレイプの重複コピーを除きますが、価格/所有情報の競合は別途解決してください。この2つのコンポーネントにGPU、ストレージ、ネットワーク、コントロールプレーン、アイドル/共有配賦、割引、クレジット、税は含まれません。データ欠損はコストゼロを意味せず、時間当たりの率は月額ではありません。

PrometheusRuleのNamespace/releaseラベルはソースガイドのセレクターと一致させてください。ダッシュボードをプロビジョニングする前に、`REPLACE_WITH_PROMETHEUS_UID`をレビュー済みの単一クラスター用データソースに置き換えます。ConfigMapの`grafana_dashboard: "1"`ラベルはソースガイドのsidecarに対応し、そのJSONは以下に実際に含まれています。ルールの健全性、データ範囲、ダッシュボードクエリを確認してください。これらの例を実際の請求/Grafana環境へ接続したわけではありません。

```yaml
kube-state-metrics:
  metricLabelsAllowlist:
  - pods=[team]
```

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: eks-allocation-rate
  namespace: monitoring
  labels:
    release: monitoring
spec:
  groups:
  - name: eks-allocation-rate
    rules:
    - record: eks_review:pod_cpu_memory_cost_per_hour:sum
      expr: "sum by (namespace, pod) (\n  (\n    max by (namespace, pod, container,\
        \ node) (\n      container_cpu_allocation{job=\"opencost\"}\n    )\n    *\
        \ on (node) group_left\n    max by (node) (node_cpu_hourly_cost{job=\"opencost\"\
        })\n  )\n  +\n  (\n    max by (namespace, pod, container, node) (\n      container_memory_allocation_bytes{job=\"\
        opencost\"}\n    ) / 1073741824\n    * on (node) group_left\n    max by (node)\
        \ (node_ram_hourly_cost{job=\"opencost\"})\n  )\n)"
    - record: eks_review:team_cpu_memory_cost_per_hour:sum
      expr: "sum by (team) (\n  label_replace(\n    eks_review:pod_cpu_memory_cost_per_hour:sum\n\
        \    * on (namespace, pod) group_left (label_team)\n    max by (namespace,\
        \ pod, label_team) (kube_pod_labels{job=\"kube-state-metrics\",label_team!=\"\
        \"}),\n    \"team\", \"$1\", \"label_team\", \"(.+)\"\n  )\n  or\n  label_replace(\n\
        \    eks_review:pod_cpu_memory_cost_per_hour:sum\n    unless on (namespace,\
        \ pod) max by (namespace, pod, label_team) (kube_pod_labels{job=\"kube-state-metrics\"\
        ,label_team!=\"\"}),\n    \"team\", \"unassigned\", \"namespace\", \".*\"\n\
        \  )\n)"
```

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cost-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: '1'
data:
  cost-dashboard.json: "{\n  \"title\": \"Estimated CPU and memory allocation rate\"\
    ,\n  \"uid\": \"eks-allocation-rate\",\n  \"schemaVersion\": 39,\n  \"version\"\
    : 1,\n  \"refresh\": \"1m\",\n  \"time\": {\n    \"from\": \"now-6h\",\n    \"\
    to\": \"now\"\n  },\n  \"panels\": [\n    {\n      \"id\": 1,\n      \"title\"\
    : \"CPU + memory allocation by namespace (USD/hour)\",\n      \"type\": \"timeseries\"\
    ,\n      \"gridPos\": {\n        \"x\": 0,\n        \"y\": 0,\n        \"w\":\
    \ 12,\n        \"h\": 8\n      },\n      \"datasource\": {\n        \"type\":\
    \ \"prometheus\",\n        \"uid\": \"REPLACE_WITH_PROMETHEUS_UID\"\n      },\n\
    \      \"fieldConfig\": {\n        \"defaults\": {\n          \"unit\": \"currencyUSD\"\
    \n        },\n        \"overrides\": []\n      },\n      \"targets\": [\n    \
    \    {\n          \"refId\": \"A\",\n          \"expr\": \"sum by (namespace)\
    \ (eks_review:pod_cpu_memory_cost_per_hour:sum)\",\n          \"legendFormat\"\
    : \"{{namespace}}\"\n        }\n      ]\n    },\n    {\n      \"id\": 2,\n   \
    \   \"title\": \"CPU + memory allocation by team (USD/hour)\",\n      \"type\"\
    : \"timeseries\",\n      \"gridPos\": {\n        \"x\": 12,\n        \"y\": 0,\n\
    \        \"w\": 12,\n        \"h\": 8\n      },\n      \"datasource\": {\n   \
    \     \"type\": \"prometheus\",\n        \"uid\": \"REPLACE_WITH_PROMETHEUS_UID\"\
    \n      },\n      \"fieldConfig\": {\n        \"defaults\": {\n          \"unit\"\
    : \"currencyUSD\"\n        },\n        \"overrides\": []\n      },\n      \"targets\"\
    : [\n        {\n          \"refId\": \"A\",\n          \"expr\": \"eks_review:team_cpu_memory_cost_per_hour:sum\"\
    ,\n          \"legendFormat\": \"{{team}}\"\n        }\n      ]\n    }\n  ]\n}"
```

他の選択肢の問題点:
- **A. AWSの請求書だけを確認する**: AWSの請求書は高水準のコスト情報しか提供しないため、詳細な配賦や最適化機会を特定しにくくなります。
- **C. すべてのリソースに同じコストを割り当てる**: 実際のリソース使用量とコスト発生を正しく反映できず、チームやプロジェクトのコスト責任も明確になりません。
- **D. コストを監視せずにリソースを利用する**: コスト増加を早期に検出したり、最適化機会を特定したりできず、予算管理が難しくなります。
</details>

### 6. EKSのコスト最適化を拡張可能なワークフローとして進めるには、どの方法が最適ですか？

- A. 効果を測定せずに手作業でリソースを変更する
- B. 請求データだけを見てワークロードのテレメトリを無視する
- C. コスト可視化、リソーステレメトリ、適切な自動スケーリングを明確な所有関係のもとで組み合わせる
- D. 同じリソースに対して調整なしに複数の最適化ツールを動かす
<details>
<summary>回答を表示</summary>

**回答: C. コスト可視化、リソーステレメトリ、適切な自動スケーリングを明確な所有関係のもとで組み合わせる**

**解説:**
ここで挙げたツールは、それぞれをすべて導入する要件ではなく、相互に補完する役割の例です。コスト/テレメトリの経路を1つ選んで所有者を明確にし、ワークロードに適したスケーリングを使ってください。EKS Auto Mode、セルフマネージドKarpenter、Cluster Autoscalerのいずれかが、すでにノードキャパシティを管理している場合があります。所有権を分け、コントローラーが競合しないようにします。削減額とSLOが維持されることを測定してください。コストツールを導入しただけで、請求データがHPA/Karpenterのポリシーに自動連携されるわけではありません。

**主なコスト最適化ツールと機能:**

1. **Kubecost**:
   - Kubernetesリソースコストを可視化する
   - Namespace、Deployment、Service別にコストを配賦する
   - コスト最適化を推奨する
   - コスト予測と予算管理を行う

2. **Karpenter**:
   - ノードのプロビジョニングと管理をインテリジェントに行う
   - ワークロード、キャパシティ、料金の制約内でインスタンスを選択する
   - 実環境で検証すべきプロビジョニング/スケーリング動作を行う
   - Spotインスタンスの活用を最適化する

3. **AWS Cost Explorer**:
   - AWSサービス全体のコストを分析する
   - タグベースでコストを配賦する
   - コスト傾向を分析し予測する
   - Reserved InstanceとSavings Plansを推奨する

4. **Kubernetesの自動スケーリングツール**:
   - Horizontal Pod Autoscaler (HPA)
   - Vertical Pod Autoscaler (VPA)
   - Cluster Autoscaler
   - Cluster Proportional Autoscaler

**実装方法:**

1. **Kubecostのインストールと設定**:
Q5と[ソースガイド](../../eks/07-eks-cost-optimization.md)で確認したインストール方法と配賦データの前提条件を再利用してください。Kubecost 3.3.1は現在の`kubecost/kubecost`チャートとClickHouse/エージェントによる直接収集方式を使います。製品機能はエディションと設定に依存します。OpenCostは別の選択肢です。すでに所有者のいる構成に、2つ目の収集ツールをデプロイしないでください。

2. **Karpenterのインストールと設定**:
以下を`karpenter-values.yaml`として保存し、確認済みのアカウント/ロール/クラスター/エンドポイント/キューに置き換えて、[Karpenterガイド](../../autoscaling/02-karpenter.md)に従ってください。確認済みの例は1.14.1を使います。互換性マトリクスではEKS 1.36に1.13以上が必要です。これらは`settings.*`キーであり、無視される`controller.clusterName/clusterEndpoint`の値ではありません。IRSAの信頼条件は`system:serviceaccount:karpenter:karpenter`とそのaudienceに一致させます。競合するIRSA/Pod Identityの割り当てを併用しないでください。コントローラー/ノードIAM、ノードアクセス、サブネット/セキュリティグループ、中断キュー/イベント連携、安定した起動用キャパシティを先に準備します。新規HelmインストールとCRDのアップグレードでは、所有関係とライフサイクルの手順が異なります。コントローラーをアップグレードしただけでは既存CRDはアップグレードされません。

```yaml
serviceAccount:
  create: true
  name: karpenter
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/KarpenterControllerRole-my-cluster
settings:
  clusterName: my-cluster
  clusterEndpoint: https://REPLACE_WITH_REVIEWED_EKS_ENDPOINT
  interruptionQueue: my-cluster
```

```bash
: "${KUBE_CONTEXT:?Select the reviewed context matching the values file}"
KARPENTER_VERSION="1.14.1"
helm template karpenter oci://public.ecr.aws/karpenter/karpenter \
  --version "$KARPENTER_VERSION" --namespace karpenter \
  -f karpenter-values.yaml > karpenter-rendered.yaml
# Fresh installation only after the owned IAM, node access, queue, CRDs, and bootstrap capacity are ready.
helm install karpenter oci://public.ecr.aws/karpenter/karpenter \
  --kube-context "$KUBE_CONTEXT" \
  --version "$KARPENTER_VERSION" --namespace karpenter --create-namespace \
  -f karpenter-values.yaml --wait --timeout 5m
```

   ```yaml
   # Karpenter NodePool and NodeClass configuration
   apiVersion: karpenter.sh/v1
   kind: NodePool
   metadata:
     name: default
   spec:
     template:
       spec:
         requirements:
           - key: "karpenter.sh/capacity-type"
             operator: In
             values: ["spot", "on-demand"]
           - key: "kubernetes.io/arch"
             operator: In
             values: ["amd64"]
           - key: "kubernetes.io/os"
             operator: In
             values: ["linux"]
           - key: "node.kubernetes.io/instance-type"
             operator: In
             values: ["m5.large", "m5a.large", "m5d.large", "m4.large", "t3.large", "t3a.large"]
         nodeClassRef:
           group: karpenter.k8s.aws
           kind: EC2NodeClass
           name: default
     limits:
       cpu: 1000
       memory: 1000Gi
     disruption:
       consolidationPolicy: WhenEmpty
       consolidateAfter: 30s
   ---
   apiVersion: karpenter.k8s.aws/v1
   kind: EC2NodeClass
   metadata:
     name: default
   spec:
     amiSelectorTerms:
       - alias: al2023@latest
     role: KarpenterNodeRole
     subnetSelectorTerms:
       - tags:
           karpenter.sh/discovery: my-cluster
     securityGroupSelectorTerms:
       - tags:
           karpenter.sh/discovery: my-cluster
     tags:
       karpenter.sh/discovery: my-cluster
   ```

3. **Horizontal Pod Autoscalerを設定する**:
   ```yaml
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: web-app
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: web-app
     minReplicas: 2
     maxReplicas: 10
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 70
     - type: Resource
       resource:
         name: memory
         target:
           type: Utilization
           averageUtilization: 80
   ```

4. **Vertical Pod Autoscalerを設定する**:
   ```yaml
   apiVersion: autoscaling.k8s.io/v1
   kind: VerticalPodAutoscaler
   metadata:
     name: web-app-vpa
   spec:
     targetRef:
       apiVersion: "apps/v1"
       kind: Deployment
       name: web-app
     updatePolicy:
       updateMode: "Off"
     resourcePolicy:
       containerPolicies:
       - containerName: '*'
         minAllowed:
           cpu: 50m
           memory: 100Mi
         maxAllowed:
           cpu: 1
           memory: 1Gi
         controlledResources: ["cpu", "memory"]
   ```

**ツールの連携とワークフロー:**

1. **コストの可視化と分析**:
   - Kubecost: クラスター内のリソースコスト分析
   - AWS Cost Explorer: AWSサービス全体のコスト分析
   - 統合ダッシュボード: 全体的なコスト概要と傾向

2. **リソース最適化の自動化**:
   - Karpenter: 最適なノードのプロビジョニングと管理
   - HPA/VPA: ワークロードレベルのリソース最適化
   - Spotインスタンス: コスト効率のよいコンピューティングリソース

3. **コスト配賦と責任**:
   - タグベースのコスト配賦
   - Namespaceとラベルごとのコスト分析
   - チームとプロジェクトごとのコストレポート

4. **継続的な最適化と改善**:
   - コスト最適化の推奨事項を実装する
   - 定期的にコストを確認して分析する
   - コスト削減目標を設定し、進捗を追跡する

**所有関係のある連携とAPI検証**

VPAの例はOffを使い、HPAはCPU/メモリ使用率を分母にします。この制御ループを調整したうえで、自動的なrequests変更を有効にしてください。Cluster Proportional Autoscalerはクラスター規模のシグナルに応じてコンポーネントのレプリカ数を調整するもので、ノードプロビジョナーと同等ではありません。Karpenterの上限、インスタンス優先設定、統合までの待ち時間は、支出上限や終了時刻を保証しません。`al2023@latest`を不変と見なさず、解決後のAMIを調べて、管理された変更ではテスト済みのバージョン/IDに固定してください。

PriorityClassはスケジューリング/プリエンプションの優先度を制御します。コスト配賦や可用性を保証するものではありません。誰が優先度を割り当てられるかを管理してください。スケジューラーのプリエンプションがPDBを尊重するのはベストエフォートです。中断とワークロード復旧を確認してください。コントローラーを動かす前に、コスト観測と推奨事項に対してレビュー済みのポリシー/変更経路を明示する必要があります。アーキテクチャ図は連携を実装するものではありません。

Terraformの代替例では、Helm provider 3.3.0のvalues-file設定とAWS provider 6.69.1を使います。明示的なKubernetesコンテキストと、互換性のあるID、ストレージ、ライセンスシークレット参照を含むレビュー済みチャート値を指定します。これらの前提条件自体は作成しません。ライセンスやクラウド認証情報を平文でvaluesやstateに入れないでください。2つ目のマネージャーから再インストールせず、既存リリースの所有者と調整します。1,000 USD/80%の予算は例示であり、検証済みの請求タグフィルターを使いますが、支出上限ではありません。この監査ではクラスター/Helmのプロビジョニングも通知も実行していません。

以下のAPI例が対象とするのは、前の設定で使ったOpenCost 1.121.2です。Kubecost 3.xのURLを推測していません。`/allocation` APIが受け付ける集約キーは`namespace,controllerKind,controller`です。`deployment`は文書化された汎用集約キーではありません。レスポンスデータはallocation setのmap配列であり、Namespace/Deploymentの辞書ではありません。HTTP/APIエラーとデータ範囲を検証してください。空の結果はコストゼロや過剰プロビジョニングの証拠ではありません。配賦量、使用量、requests、byte-hours/core-hours、現在のレプリカ数は意味も対象期間も異なります。rightsizingを推奨する前に、バージョン別スキーマと比較可能なワークロードメトリクスを調べてください。生の配賦推定値を請求データやアイドル/共有コストのポリシーと照合してください。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  template:
    spec:
      containers:
      - name: web-app
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        image: registry.example.com/team/web-app:REVIEWED_TAG
    metadata:
      labels:
        app: web-app
  selector:
    matchLabels:
      app: web-app
```

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot-pool
spec:
  template:
    spec:
      requirements:
        - key: "karpenter.sh/capacity-type"
          operator: In
          values: ["spot"]
        - key: "node.kubernetes.io/instance-type"
          operator: In
          values: ["m5.large", "m5a.large", "m5d.large", "m4.large", "t3.large", "t3a.large"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  limits:
    cpu: 1000
    memory: 1000Gi
```

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: High priority pods
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: low-priority
value: 10000
globalDefault: false
description: Low priority pods
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: critical-app
spec:
  template:
    spec:
      priorityClassName: high-priority
      containers:
      - name: critical-app
        image: registry.example.com/team/critical-app:REVIEWED_TAG
    metadata:
      labels:
        app: critical-app
  selector:
    matchLabels:
      app: critical-app
```

```bash
aws budgets create-budget \
  --account-id 123456789012 \
  --budget '{
    "BudgetName": "EKS-Monthly",
    "BudgetLimit": {
      "Amount": "1000",
      "Unit": "USD"
    },
    "CostFilters": {
      "TagKeyValue": [
        "user:kubernetes.io/cluster/my-cluster$owned"
      ]
    },
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }' \
  --notifications-with-subscribers '[
    {
      "Notification": {
        "NotificationType": "ACTUAL",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 80,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [
        {
          "SubscriptionType": "EMAIL",
          "Address": "team@example.com"
        }
      ]
    }
  ]'
```

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "= 3.3.0"
    }
  }
}

variable "region" { type = string }
variable "account_id" { type = string }
variable "kubeconfig_path" { type = string }
variable "kube_context" { type = string }
variable "reviewed_kubecost_values_path" { type = string }
variable "reviewed_karpenter_values_path" { type = string }
variable "budget_name" { type = string }
variable "budget_tag_filter" {
  type        = string
  description = "Actual activated Budgets TagKeyValue, for example user:cluster$production."
}
variable "notification_email" {
  type        = string
  description = "Approved recipient; applying this configures real notifications."
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

provider "helm" {
  kubernetes = {
    config_path    = var.kubeconfig_path
    config_context = var.kube_context
  }
}

resource "helm_release" "kubecost" {
  name             = "kubecost"
  repository       = "https://kubecost.github.io/kubecost/"
  chart            = "kubecost"
  version          = "3.3.1"
  namespace        = "kubecost"
  create_namespace = true
  values           = [file(var.reviewed_kubecost_values_path)]
  wait             = true
  timeout          = 300
}

resource "helm_release" "karpenter" {
  name             = "karpenter"
  repository       = "oci://public.ecr.aws/karpenter"
  chart            = "karpenter"
  version          = "1.14.1"
  namespace        = "karpenter"
  create_namespace = true
  values           = [file(var.reviewed_karpenter_values_path)]
  wait             = true
  timeout          = 300
}

resource "aws_budgets_budget" "eks" {
  account_id   = var.account_id
  name         = var.budget_name
  budget_type  = "COST"
  limit_amount = "1000"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "TagKeyValue"
    values = [var.budget_tag_filter]
  }
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.notification_email]
  }
}
```

```bash
: "${KUBE_CONTEXT:?Select the reviewed OpenCost cluster context}"
# Terminal 1: authorized local access to the OpenCost 1.121.2 service from EKS06.
kubectl --context "$KUBE_CONTEXT" -n opencost port-forward --address 127.0.0.1 svc/opencost 9003:9003
```

```bash
curl --fail --silent --show-error --max-time 30 --get \
  http://127.0.0.1:9003/allocation \
  --data-urlencode 'window=1d' \
  --data-urlencode 'aggregate=namespace,controllerKind,controller' \
  --data-urlencode 'accumulate=true' > allocation.json
```

```python
import json
from pathlib import Path

response = json.loads(Path("allocation.json").read_text())
if response.get("code") != 200 or not isinstance(response.get("data"), list):
    raise ValueError("Unexpected allocation API response; do not replace failure with zero")
if not all(isinstance(allocation_set, dict) for allocation_set in response["data"]):
    raise ValueError("Expected an array of allocation-set maps")
if not response["data"] or not any(response["data"]):
    raise SystemExit("No allocation data for the selected window; investigate coverage")
else:
    print("Allocation response shape accepted; review units, window, and coverage before analysis")
```

他の選択肢では、測定、ワークロードのシグナル、または調整された所有関係が欠けています。競合するコントローラーは安定性とコスト予測性を損なうおそれがあります。
</details>
