# EKS ストレージ

> **最終更新**: July 3, 2026

Amazon EKS でアプリケーションを実行する場合、データを保存・管理するためのさまざまなストレージオプションがあります。このドキュメントでは、EKS ストレージの基本概念と、Amazon EBS (Elastic Block Store) および Amazon EFS (Elastic File System) の使用方法について説明します。

## 目次

1. [Kubernetes ストレージの基本概念](04-eks-storage-part1.md#kubernetes-storage-basic-concepts)
2. [Amazon EKS ストレージオプションの概要](04-eks-storage-part1.md#amazon-eks-storage-options-overview)
3. [Amazon EBS を使用したストレージ](04-eks-storage-part1.md#storage-with-amazon-ebs)
4. [Amazon EFS を使用したストレージ](04-eks-storage-part1.md#storage-with-amazon-efs)
5. [StorageClass と動的プロビジョニング](04-eks-storage-part1.md#storage-classes-and-dynamic-provisioning)

## Kubernetes ストレージの基本概念

まず、Kubernetes でストレージを管理するための主要な概念を理解しましょう。

![コンテナから PVC、StorageClass、PV を経て、EBS、EFS、FSx、S3 のバックエンドへ至る Kubernetes ストレージ概念図。](../.gitbook/assets/en-eks-04-eks-storage-part1-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part1-0.html)

### Volume

Volume は Pod 内のコンテナにマウントできるディレクトリで、コンテナが再起動してもデータは保持されます。Volume のライフタイムは Pod のライフタイムと同じであり、Pod が削除されると Volume も削除されます。

### Persistent Volume (PV)

Persistent Volume は、管理者によってプロビジョニングされる、または StorageClass を通じて動的にプロビジョニングされるクラスターのストレージです。PV は Pod から独立したライフサイクルを持ち、Pod が削除されても保持されます。

### Persistent Volume Claim (PVC)

Persistent Volume Claim は、ユーザーからのストレージ要求です。PVC は特定のサイズとアクセスモードでストレージを要求し、この要求は適切な PV にバインドされます。

### StorageClass

StorageClass は、管理者が提供するストレージの「クラス」を記述します。StorageClass を使用すると、PVC の作成時に PV を動的にプロビジョニングできます。

### アクセスモード

Kubernetes は次のアクセスモードをサポートしています。

* **ReadWriteOnce (RWO)**: 単一のノードによって読み取り/書き込みとしてマウント可能
* **ReadOnlyMany (ROX)**: 複数のノードによって読み取り専用としてマウント可能
* **ReadWriteMany (RWX)**: 複数のノードによって読み取り/書き込みとしてマウント可能
* **ReadWriteOncePod (RWOP)**: 単一の Pod のみが読み取り/書き込みとしてマウント可能 (Kubernetes 1.22+)

## Amazon EKS ストレージオプションの概要

Amazon EKS では、さまざまな AWS ストレージサービスを活用して、コンテナ化されたアプリケーションにストレージを提供できます。

![EBS、EFS、FSx for Lustre と、それらの CSI Driver およびサポートされるアクセスモードを比較する EKS ストレージオプション図。](../.gitbook/assets/en-eks-04-eks-storage-part1-1.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part1-1.html)

### 主なストレージオプション

1. **Amazon EBS (Elastic Block Store)**
   * ブロックストレージ。単一ノードにマウント可能 (RWO)
   * 高性能で耐久性のあるブロックストレージ
   * データベース、ステートフルアプリケーションに適している
2. **Amazon EFS (Elastic File System)**
   * フルマネージド NFS ファイルシステム
   * 複数ノードから同時にマウント可能 (RWX)
   * 共有ファイルシステムを必要とするワークロードに適している
3. **Amazon FSx for Lustre**
   * 高性能ファイルシステム
   * 機械学習、HPC、ビッグデータ分析に適している
   * 複数ノードから同時にマウント可能 (RWX)
4. **Amazon S3 (Simple Storage Service)**
   * オブジェクトストレージ
   * Volume として直接マウントすることはできないが、S3 API を通じてアクセス可能
   * 大規模データストレージに適している
5. **EC2 Instance Store (ローカル NVMe)**
   * EC2 インスタンスに物理的に接続された一時的なローカル NVMe ストレージで、非常に低いレイテンシーを提供
   * EC2 Instance Store CSI Driver は 2026 年 5 月に Amazon EKS アドオンとして一般提供 (GA) になり、EKS Console/CLI から標準アドオンとしてインストールおよび管理できるようになりました（以前はコミュニティマニフェストによる手動インストールが必要でした）。この Driver は Volume のライフサイクルを自動管理し、運用上のオーバーヘッドを削減します
   * AI/ML の一時データ処理、Spark/Hadoop のローカルキャッシュ、高スループットログ処理、データベースのキャッシュ層に適している
   * コスト: Driver 自体は無料で、Instance Store を含む基盤 EC2 インスタンスに対してのみ課金されます（[出典](https://aws.amazon.com/about-aws/whats-new/2026/05/ec2-csi-eks/)）

### ストレージオプションの比較

| ストレージオプション | タイプ             | アクセスモード | パフォーマンス                   | ユースケース                                                       |
| ------------------ | ------------------ | -------------- | ----------------------------- | ------------------------------------------------------------------- |
| Amazon EBS         | ブロック           | RWO            | 高                             | データベース、ステートフルアプリケーション                         |
| Amazon EFS         | ファイル           | RWX            | 中                             | 共有ファイル、Web サーバー、CMS                                    |
| FSx for Lustre     | ファイル           | RWX            | 非常に高い                     | HPC、ML トレーニング、ビッグデータ                                 |
| Amazon S3          | オブジェクト       | API アクセス   | 中                             | バックアップ、アーカイブ、静的コンテンツ                           |
| EC2 Instance Store | ブロック (ローカル NVMe) | RWO、一時的 | 非常に高い (超低レイテンシー) | AI/ML 一時データ、ローカルキャッシュ、高スループットログ処理 |

## Amazon EBS を使用したストレージ

Amazon EBS は、EC2 インスタンスにアタッチできるブロックレベルのストレージ Volume を提供します。EKS では、EBS CSI (Container Storage Interface) Driver を介して EBS Volume を Kubernetes Pod にマウントできます。

![2 つのノード上の Pod が、各ノードローカルの CSI Driver を介して別々の EBS Volume をアタッチする EBS CSI アーキテクチャ図。](../.gitbook/assets/en-eks-04-eks-storage-part1-2.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part1-2.html)

### EBS CSI Driver のインストール

EKS で EBS Volume を使用するには、EBS CSI Driver をインストールする必要があります。この Driver は Amazon EKS アドオンとして提供されています。

```bash
# Install EBS CSI driver
eksctl create addon --name aws-ebs-csi-driver --cluster my-cluster --version latest

# Or using AWS CLI
aws eks create-addon --cluster-name my-cluster --addon-name aws-ebs-csi-driver --addon-version latest
```

### EBS StorageClass の作成

EBS Volume を動的にプロビジョニングするための StorageClass を作成します。ここでは gp3 Volume タイプを使用します。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  encrypted: "true"
  fsType: ext4
```

### Persistent Volume Claim (PVC) の作成

アプリケーションで使用する PVC を作成します。

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-claim
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 10Gi
```

### Pod での PVC の使用

作成した PVC を Pod にマウントします。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-ebs
spec:
  containers:
  - name: app
    image: nginx
    volumeMounts:
    - mountPath: "/data"
      name: ebs-volume
  volumes:
  - name: ebs-volume
    persistentVolumeClaim:
      claimName: ebs-claim
```

### EBS Volume スナップショット

EBS Volume のスナップショットを作成してデータをバックアップできます。

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: ebs-snapshot
spec:
  volumeSnapshotClassName: csi-aws-vsc
  source:
    persistentVolumeClaimName: ebs-claim
```

### EBS Volume の拡張

必要に応じて EBS Volume のサイズを拡張できます。

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-claim
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 20Gi  # Expanded from 10Gi to 20Gi
```

### EBS Volume タイプとパフォーマンス

Amazon EBS はさまざまな Volume タイプを提供します。

| Volume タイプ | 説明                     | ユースケース                                 |
| ----------- | ------------------------ | ------------------------------------------- |
| gp3         | 汎用 SSD                 | ほとんどのワークロードに適しており、費用対効果が高い |
| io2         | プロビジョンド IOPS SSD  | 高性能データベース                          |
| st1         | スループット最適化 HDD   | ビッグデータ、ログ処理                      |
| sc1         | コールド HDD             | アクセス頻度の低いデータ                    |

EKS では、gp3 Volume タイプが推奨されます。gp3 は一貫したパフォーマンスを提供しながら、費用対効果にも優れています。

## Amazon EFS を使用したストレージ

Amazon EFS は、複数の EC2 インスタンスから同時にアクセスできるフルマネージド NFS ファイルシステムです。EKS では、EFS CSI Driver を介して EFS ファイルシステムを複数の Pod に同時にマウントできます。

![複数ノード上の Pod が、CSI Driver を介して NFS 4.1 で 1 つの EFS ファイルシステムを共有する EFS CSI アーキテクチャ図。](../.gitbook/assets/en-eks-04-eks-storage-part1-3.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part1-3.html)

### EFS CSI Driver のインストール

EKS で EFS を使用するには、EFS CSI Driver をインストールする必要があります。

```bash
# Install EFS CSI driver
eksctl create addon --name aws-efs-csi-driver --cluster my-cluster --version latest

# Or using AWS CLI
aws eks create-addon --cluster-name my-cluster --addon-name aws-efs-csi-driver --addon-version latest
```

### EFS ファイルシステムの作成

AWS Management Console、AWS CLI、または AWS CloudFormation を使用して EFS ファイルシステムを作成します。

```bash
# Create EFS file system using AWS CLI
aws efs create-file-system \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --encrypted \
  --tags Key=Name,Value=MyEFSFileSystem

# Save file system ID
EFS_FS_ID=$(aws efs describe-file-systems --query "FileSystems[?Name=='MyEFSFileSystem'].FileSystemId" --output text)

# Get EKS cluster VPC ID
VPC_ID=$(aws eks describe-cluster --name my-cluster --query "cluster.resourcesVpcConfig.vpcId" --output text)

# Create security group
aws ec2 create-security-group \
  --group-name MyEFSSecurityGroup \
  --description "Security group for EFS mount targets" \
  --vpc-id $VPC_ID

SG_ID=$(aws ec2 describe-security-groups \
  --filters Name=group-name,Values=MyEFSSecurityGroup \
  --query "SecurityGroups[0].GroupId" --output text)

# Allow NFS traffic
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 2049 \
  --cidr 10.0.0.0/16

# Get subnet IDs
SUBNET_IDS=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "Subnets[*].SubnetId" --output text)

# Create mount target in each subnet
for SUBNET_ID in $SUBNET_IDS; do
  aws efs create-mount-target \
    --file-system-id $EFS_FS_ID \
    --subnet-id $SUBNET_ID \
    --security-groups $SG_ID
done
```

### EFS StorageClass の作成

EFS を使用するための StorageClass を作成します。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0  # Created EFS file system ID
  directoryPerms: "700"
```

### Persistent Volume Claim (PVC) の作成

EFS を使用するための PVC を作成します。

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: efs-claim
spec:
  accessModes:
    - ReadWriteMany  # Can read/write simultaneously from multiple nodes
  storageClassName: efs-sc
  resources:
    requests:
      storage: 5Gi
```

### Pod での EFS PVC の使用

作成した PVC を Pod にマウントします。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-efs
spec:
  containers:
  - name: app
    image: nginx
    volumeMounts:
    - mountPath: "/shared-data"
      name: efs-volume
  volumes:
  - name: efs-volume
    persistentVolumeClaim:
      claimName: efs-claim
```

### EFS アクセスポイント

EFS アクセスポイントを使用すると、特定のディレクトリへのアクセスを制限し、ユーザーおよびグループの権限を設定できます。

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: efs-pv
spec:
  capacity:
    storage: 5Gi
  volumeMode: Filesystem
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: efs-sc
  csi:
    driver: efs.csi.aws.com
    volumeHandle: fs-0123456789abcdef0::fsap-0123456789abcdef0
    # volumeHandle format: {EFS file system ID}::{EFS access point ID}
```

### EFS パフォーマンスモードとスループットモード

Amazon EFS は、2 つのパフォーマンスモードと 3 つのスループットモードを提供します。

**パフォーマンスモード**:

* **General Purpose**: ほとんどのワークロードに推奨
* **Max I/O**: 高い並列処理を必要とするワークロードに適している

**スループットモード**:

* **Bursting**: デフォルトモード。ファイルシステムサイズに基づくバーストクレジットを提供
* **Provisioned**: 一貫したスループットが必要な場合に使用
* **Elastic**: ワークロードに基づいてスループットを自動調整（推奨）

## StorageClass と動的プロビジョニング

Kubernetes StorageClass を使用すると、Persistent Volume を動的にプロビジョニングできます。EKS では、さまざまな AWS ストレージサービス用に StorageClass を設定できます。

![Pod の PVC リクエストから StorageClass と CSI Driver を経由し、PV の作成とバインドに至るストレージプロビジョニングワークフロー図。](../.gitbook/assets/en-eks-04-eks-storage-part1-4.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part1-4.html)

### Volume バインディングモード

StorageClass の `volumeBindingMode` フィールドは、PVC の作成時に PV をどのようにバインドするかを決定します。

* **Immediate**: PVC の作成時に直ちに PV をプロビジョニングしてバインドします。
* **WaitForFirstConsumer**: Pod が PVC を使用しようとするまで PV のプロビジョニングを遅延します。

EBS のようなノードローカルストレージでは、`WaitForFirstConsumer` の使用が推奨されます。これにより、Pod がスケジュールされるノードと同じアベイラビリティーゾーンに Volume が作成されます。

### デフォルト StorageClass の設定

特定の StorageClass をデフォルトとして設定すると、PVC で StorageClass が指定されていない場合でもその StorageClass を使用できます。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  encrypted: "true"
```

### StorageClass の例

**1. EBS gp3 StorageClass**

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  encrypted: "true"
  iops: "3000"
  throughput: "125"
```

**2. EFS StorageClass**

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: "700"
```

**3. FSx for Lustre StorageClass**

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre
provisioner: fsx.csi.aws.com
parameters:
  subnetId: subnet-0123456789abcdef0
  securityGroupIds: sg-0123456789abcdef0
  deploymentType: SCRATCH_2
  automaticBackupRetentionDays: "0"
  dailyAutomaticBackupStartTime: "00:00"
  perUnitStorageThroughput: "200"
  dataCompressionType: "NONE"
```

### 再利用ポリシー

Persistent Volume の再利用ポリシーは、PVC が削除されたときに PV とそのデータをどのように扱うかを決定します。

* **Delete**: PVC が削除されると、PV とそのデータも削除されます。
* **Retain**: PVC が削除されると、PV とデータは保持されます。管理者が手動でクリーンアップする必要があります。
* **Recycle**: 非推奨のポリシーです。代わりに動的プロビジョニングと StorageClass を使用してください。

StorageClass の `persistentVolumeReclaimPolicy` フィールドを使用して再利用ポリシーを設定できます。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3-retain
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
parameters:
  type: gp3
  encrypted: "true"
```

## まとめ

Amazon EKS では、さまざまなストレージオプションを使用して、アプリケーション要件を満たすストレージソリューションを構成できます。このドキュメントでは、EBS と EFS を中心に基本概念と設定方法を説明しました。次のドキュメントでは、FSx for Lustre と S3 を使用した高度なストレージ設定について説明します。

## クイズ

この章で学んだ内容を確認するには、[トピッククイズ](../quizzes/eks/04-eks-storage-part1-quiz.md)に挑戦してください。
