# EKS Storage Quiz - Part 1

このクイズでは、persistent volumes、storage classes、dynamic provisioning を含む Amazon EKS のストレージ概念についての理解を確認します。

## Multiple Choice Questions

### 1. What storage driver is natively supported by Amazon EKS by default?

A. Amazon EFS CSI Driver B. Amazon EBS CSI Driver C. Amazon FSx for Lustre CSI Driver D. Amazon S3 CSI Driver

<details>

<summary>答えを表示</summary>

**解答: B. Amazon EBS CSI Driver**

**解説:** Amazon EKS でデフォルトでネイティブにサポートされているストレージドライバーは、Amazon EBS CSI (Container Storage Interface) Driver です。このドライバーにより、Amazon Elastic Block Store (EBS) ボリュームを Amazon EKS clusters の persistent storage として使用できます。

**主な機能:**

1.  **EKS Add-on として利用可能**: Amazon EBS CSI driver は、簡単なインストールと管理のために EKS add-on として提供されています。

    ```bash
    aws eks create-addon \
      --cluster-name my-cluster \
      --addon-name aws-ebs-csi-driver \
      --service-account-role-arn arn:aws:iam::111122223333:role/AmazonEKS_EBS_CSI_DriverRole
    ```
2.  **Dynamic Provisioning のサポート**: StorageClass を通じた EBS volumes の dynamic provisioning をサポートします。

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc
    provisioner: ebs.csi.aws.com
    volumeBindingMode: WaitForFirstConsumer
    parameters:
      type: gp3
      encrypted: "true"
    ```
3.  **Volume Snapshot のサポート**: volume snapshot と restore 機能をサポートします。

    ```yaml
    apiVersion: snapshot.storage.k8s.io/v1
    kind: VolumeSnapshot
    metadata:
      name: ebs-volume-snapshot
    spec:
      volumeSnapshotClassName: ebs-snapshot-class
      source:
        persistentVolumeClaimName: ebs-claim
    ```
4. **さまざまな EBS Volume Types**: gp2、gp3、io1、io2、sc1、st1 を含むさまざまな EBS volume types をサポートします。

**必要な IAM Permissions:**

EBS CSI driver が動作するには、次の IAM permissions が必要です:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateSnapshot",
        "ec2:AttachVolume",
        "ec2:DetachVolume",
        "ec2:ModifyVolume",
        "ec2:DescribeAvailabilityZones",
        "ec2:DescribeInstances",
        "ec2:DescribeSnapshots",
        "ec2:DescribeTags",
        "ec2:DescribeVolumes",
        "ec2:DescribeVolumesModifications"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateTags"
      ],
      "Resource": [
        "arn:aws:ec2:*:*:volume/*",
        "arn:aws:ec2:*:*:snapshot/*"
      ],
      "Condition": {
        "StringEquals": {
          "ec2:CreateAction": [
            "CreateVolume",
            "CreateSnapshot"
          ]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DeleteTags"
      ],
      "Resource": [
        "arn:aws:ec2:*:*:volume/*",
        "arn:aws:ec2:*:*:snapshot/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateVolume"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "aws:RequestTag/ebs.csi.aws.com/cluster": "true"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateVolume"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "aws:RequestTag/CSIVolumeName": "*"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DeleteVolume"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "ec2:ResourceTag/ebs.csi.aws.com/cluster": "true"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DeleteVolume"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "ec2:ResourceTag/CSIVolumeName": "*"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DeleteVolume"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "ec2:ResourceTag/kubernetes.io/created-for/pvc/name": "*"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DeleteSnapshot"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "ec2:ResourceTag/CSIVolumeSnapshotName": "*"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DeleteSnapshot"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "ec2:ResourceTag/ebs.csi.aws.com/cluster": "true"
        }
      }
    }
  ]
}
```

**制限事項:**

1. **Availability Zone の制限**: EBS volumes は単一の availability zone に制限されるため、pods は volume と同じ availability zone で実行する必要があります。
2. **Single Node Mount**: EBS volumes は一度に 1 つの node にのみ mount できます (ReadWriteOnce access mode)。
3. **Fargate の制限**: Amazon EKS Fargate は現在、EBS CSI driver をサポートしていません。

他の選択肢の問題点:

* **A. Amazon EFS CSI Driver**: EFS CSI driver は EKS でサポートされていますが、デフォルトではインストールされません。別途インストールする必要があります。
* **C. Amazon FSx for Lustre CSI Driver**: FSx for Lustre CSI driver は EKS でサポートされていますが、デフォルトではインストールされません。別途インストールする必要があります。
* **D. Amazon S3 CSI Driver**: 現在、公式の Amazon S3 CSI driver はありません。S3 は通常、CSI 経由で直接 mount するのではなく、S3 API を通じてアクセスします。

</details>

### 2. What is the most suitable storage solution when multiple pods in Amazon EKS need simultaneous read/write access?

A. Amazon EBS B. Amazon EFS C. Amazon S3 D. Amazon FSx for Lustre

<details>

<summary>答えを表示</summary>

**解答: B. Amazon EFS**

**解説:** Amazon EKS で複数の pods が同時に読み取り/書き込みアクセスを必要とする場合に最も適したストレージソリューションは、Amazon EFS (Elastic File System) です。EFS は ReadWriteMany (RWX) access mode をサポートする managed NFS (Network File System) service であり、複数の pods が同じ volume に対して同時に読み取りと書き込みを行えます。

**主な機能:**

1. **Multi-Availability Zone Access**: EFS は複数の availability zones にまたがってアクセスでき、異なる nodes や availability zones で実行されている pods が同じデータにアクセスできます。
2.  **ReadWriteMany のサポート**: EFS は ReadWriteMany (RWX) access mode をサポートし、複数の pods が同じ volume に対して同時に読み取りと書き込みを行えます。

    ```yaml
    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: efs-claim
    spec:
      accessModes:
        - ReadWriteMany
      storageClassName: efs-sc
      resources:
        requests:
          storage: 5Gi
    ```
3. **Scalability**: EFS は自動的にスケールするため、capacity planning が不要になります。
4. **耐久性と可用性**: 99.999999999% (11 9's) の耐久性と 99.99% の可用性を提供します。

**EFS CSI Driver Installation:**

```bash
# Install using Helm
helm repo add aws-efs-csi-driver https://kubernetes-sigs.github.io/aws-efs-csi-driver/
helm repo update
helm upgrade -i aws-efs-csi-driver aws-efs-csi-driver/aws-efs-csi-driver \
  --namespace kube-system \
  --set controller.serviceAccount.create=true \
  --set controller.serviceAccount.name=efs-csi-controller-sa
```

**EFS File System Creation:**

```bash
# Create EFS file system
aws efs create-file-system \
  --creation-token eks-efs \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --tags Key=Name,Value=EKS-EFS

# Create mount target
aws efs create-mount-target \
  --file-system-id fs-0123456789abcdef0 \
  --subnet-id subnet-0123456789abcdef0 \
  --security-groups sg-0123456789abcdef0
```

**StorageClass and PVC Configuration:**

```yaml
# Create StorageClass
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: "700"

# Create PVC
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: efs-claim
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: efs-sc
  resources:
    requests:
      storage: 5Gi
```

**ユースケース:**

1. **Shared File System**: 複数の pods が同じ files にアクセスする必要がある場合
2. **Web Server Content**: 複数の web server pods が同じ static content を提供する必要がある場合
3. **Log Aggregation**: 複数の pods が同じ log directory に書き込む場合
4. **CI/CD Pipelines**: build artifacts を共有する必要がある場合

**Performance Considerations:**

1. **Performance Modes**:
   * General Purpose: ほとんどの workloads に適しています
   * Max I/O: 高い throughput を必要とする workloads に適しています
2. **Throughput Modes**:
   * Bursting: デフォルトモードで、file system size に基づく burst credits を提供します
   * Provisioned: 一貫した throughput が必要な場合に特定の throughput を provision します
3. **Latency**: EFS は block storage より latency が高い場合があるため、latency-sensitive applications には適さない可能性があります。

**Security Considerations:**

1.  **Encryption**: EFS は転送中および保管時の暗号化をサポートします。

    ```bash
    aws efs create-file-system \
      --creation-token eks-efs \
      --encrypted \
      --kms-key-id 1234abcd-12ab-34cd-56ef-1234567890ab
    ```
2. **Access Control**: IAM policies、network ACLs、security groups を通じてアクセスを制御できます。
3. **Access Points**: EFS access points を使用して、特定の directories へのアクセスを制限できます。

他の選択肢の問題点:

* **A. Amazon EBS**: EBS は ReadWriteOnce (RWO) access mode のみをサポートするため、一度に 1 つの node にしか mount できません。
* **C. Amazon S3**: S3 は object storage であり file system ではないため、標準の file system interfaces を通じて直接 mount することはできません。
* **D. Amazon FSx for Lustre**: FSx for Lustre は high-performance workloads に適していますが、EFS と比較して setup がより複雑で cost も高くなります。

</details>

### 4. What is a limitation when using EBS volumes in Amazon EKS?

A. EBS volumes は複数の pods から同時に読み取り/書き込みアクセスできる B. EBS volumes は複数の availability zones にまたがってアクセスできる C. EBS volumes は一度に 1 つの pod からのみ読み取り/書き込みアクセスできる D. EBS volumes は Fargate pods で使用できる

<details>

<summary>答えを表示</summary>

**解答: C. EBS volumes は一度に 1 つの pod からのみ読み取り/書き込みアクセスできる**

**解説:** Amazon EBS (Elastic Block Store) volumes は、一度に 1 つの pod からのみ読み取り/書き込みアクセスできます。これは EBS の基本的な制限であり、EBS volumes は ReadWriteOnce (RWO) access mode のみをサポートするためです。

**主な制限事項:**

1. **Single Node Mount**: EBS volumes は一度に 1 つの EC2 instance にのみ mount できます。そのため、複数の nodes にまたがる pods は同じ EBS volume にアクセスできません。
2.  **Availability Zone の制限**: EBS volumes は作成された availability zone に制限されます。異なる availability zones の nodes で実行されている pods は、その volume にアクセスできません。

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc
    provisioner: ebs.csi.aws.com
    volumeBindingMode: WaitForFirstConsumer  # Delay volume creation until pod is scheduled
    ```
3. **Fargate 非互換**: Amazon EKS Fargate は現在 EBS volumes をサポートしていません。Fargate pods は EBS volumes を mount できません。
4.  **Access Mode の制限**: EBS は次の access mode のみをサポートします:

    * ReadWriteOnce (RWO): 単一 node による read-write mount

    ```yaml
    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: ebs-claim
    spec:
      accessModes:
        - ReadWriteOnce  # The only access mode supported by EBS
      storageClassName: ebs-sc
      resources:
        requests:
          storage: 10Gi
    ```

**これらの制限に対処する代替案:**

1.  **StatefulSet を使用する**: 各 pod に専用の EBS volumes を提供して stateful applications を実行します

    ```yaml
    apiVersion: apps/v1
    kind: StatefulSet
    metadata:
      name: web
    spec:
      serviceName: "nginx"
      replicas: 3
      selector:
        matchLabels:
          app: nginx
      template:
        metadata:
          labels:
            app: nginx
        spec:
          containers:
          - name: nginx
            image: nginx
            volumeMounts:
            - name: www
              mountPath: /usr/share/nginx/html
      volumeClaimTemplates:
      - metadata:
          name: www
        spec:
          accessModes: [ "ReadWriteOnce" ]
          storageClassName: ebs-sc
          resources:
            requests:
              storage: 10Gi
    ```
2. **Amazon EFS を使用する**: 複数の pods が同じ volume にアクセスする必要がある場合、ReadWriteMany (RWX) access mode をサポートする EFS を使用します
3. **Volume Replication**: 複数の pods からアクセスできるように、データを複数の EBS volumes に replicate します
4. **Topology-Aware Scheduling**: `volumeBindingMode: WaitForFirstConsumer` を使用して、pod が schedule された availability zone に volumes を作成します

**Availability Zone Considerations:**

1.  **Node Selector を使用する**: 特定の availability zones の nodes に pods を schedule します

    ```yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: az-pod
    spec:
      nodeSelector:
        topology.kubernetes.io/zone: us-west-2a
      containers:
      - name: app
        image: nginx
    ```
2.  **Volume Snapshot and Restore**: データを異なる availability zones に移動する必要がある場合は volume snapshots を使用します

    ```yaml
    apiVersion: snapshot.storage.k8s.io/v1
    kind: VolumeSnapshot
    metadata:
      name: ebs-snapshot
    spec:
      volumeSnapshotClassName: ebs-snapshot-class
      source:
        persistentVolumeClaimName: ebs-claim
    ```

**Best Practices:**

1. **適切な Storage の選択**: workload requirements に基づいて適切な storage type を選択します
   * Single pod access: EBS
   * Multi-pod access: EFS
   * High-performance workloads: FSx for Lustre
2. **Availability Zone-Aware Deployment**: pods と volumes が同じ availability zone にあることを確認します
3. **Volume Backup**: 定期的な snapshots でデータを保護します

他の選択肢の問題点:

* **A. EBS volumes は複数の pods から同時に読み取り/書き込みアクセスできる**: これは誤りです。EBS volumes は ReadWriteOnce (RWO) access mode のみをサポートします。
* **B. EBS volumes は複数の availability zones にまたがってアクセスできる**: これは誤りです。EBS volumes は作成された availability zone に制限されます。
* **D. EBS volumes は Fargate pods で使用できる**: これは誤りです。Amazon EKS Fargate は現在 EBS volumes をサポートしていません。

</details>

## Short Answer Questions

### 6. What access mode must be specified in a PersistentVolumeClaim for dynamic provisioning of EBS volumes in Amazon EKS?

<details>

<summary>答えを表示</summary>

**解答:** ReadWriteOnce (RWO)

**詳細な解説:**

Amazon EKS で EBS volumes の dynamic provisioning を行うために PersistentVolumeClaim (PVC) で指定する必要がある access mode は ReadWriteOnce (RWO) です。これは EBS volumes の基本的な特性によるもので、EBS volumes は一度に 1 つの node からのみ読み取り/書き込みアクセスできます。

**Access Mode Descriptions:**

1. **ReadWriteOnce (RWO)**: volume は単一 node によって read-write mode で mount できます。
2. **ReadOnlyMany (ROX)**: volume は複数の nodes によって read-only mode で mount できます。
3. **ReadWriteMany (RWX)**: volume は複数の nodes によって read-write mode で mount できます。

**EBS が RWO のみをサポートする理由:**

Amazon EBS は、一度に 1 つの EC2 instance にのみ attach されるように設計された block storage service です。これはハードウェアの制限ではなく、EBS service の設計上の特性です。そのため、EBS volumes は ReadWriteOnce access mode のみをサポートします。

**PVC Example:**

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-claim
spec:
  accessModes:
    - ReadWriteOnce  # The only access mode supported by EBS
  storageClassName: ebs-sc
  resources:
    requests:
      storage: 10Gi
```

**他の Access Modes が必要な場合の代替案:**

1. **ReadOnlyMany (ROX) が必要な場合:**
   * EBS snapshot を作成し、複数の read-only EBS volumes を作成します
   * 各 node に個別の read-only volumes を提供します
2.  **ReadWriteMany (RWX) が必要な場合:**

    * Amazon EFS (NFS-based file system) を使用します

    ```yaml
    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: efs-claim
    spec:
      accessModes:
        - ReadWriteMany
      storageClassName: efs-sc
      resources:
        requests:
          storage: 5Gi
    ```

**EBS Volumes を使用する際の考慮事項:**

1. **Pod Scheduling**: EBS volumes を使用する pods は、volume が attach されている nodes でのみ実行できます。
2. **Availability Zone の制限**: EBS volumes は作成された availability zone に制限されます。そのため、pods はその availability zone 内の nodes でのみ実行できます。
3.  **Volume Binding Mode**: pod が schedule された後に volumes を作成するため、`WaitForFirstConsumer` の使用が推奨されます。

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: ebs-sc
    provisioner: ebs.csi.aws.com
    volumeBindingMode: WaitForFirstConsumer
    ```
4. **StatefulSet との使用**: StatefulSet は各 pod に一意の PVCs を提供するため、EBS volumes との使用に適しています。

**Access Mode Selection Guide:**

| Storage Type   | ReadWriteOnce | ReadOnlyMany | ReadWriteMany |
| -------------- | ------------- | ------------ | ------------- |
| Amazon EBS     | ✓             | ✗            | ✗             |
| Amazon EFS     | ✓             | ✓            | ✓             |
| FSx for Lustre | ✓             | ✓            | ✓             |

EBS volumes を使用する場合は、常に ReadWriteOnce access mode を指定してください。複数の nodes からの同時アクセスが必要な場合は、EFS や FSx for Lustre などの代替案を検討してください。

</details>

### 7. What happens to the data when a pod using an EBS volume in Amazon EKS moves to a different node?

<details>

<summary>答えを表示</summary>

**解答:** EBS volume は以前の node から detach され、新しい node に attach されます。データは保持されますが、volume reattachment process 中に遅延が発生する可能性があります。

**詳細な解説:**

Amazon EKS で EBS volume を使用している pod が別の node に移動する場合 (例: node failure、scaling、updates などによる)、EBS volume は以前の node から detach され、新しい node に attach されます。この process 中、データは保持されますが、volume reattachment process 中に遅延が発生する可能性があります。

**Volume Reattachment Process:**

1. **Pod Termination**: pod は元の node で終了されます。
2. **Volume Detachment**: EBS volume は元の node から detach されます。
3. **Volume Attachment**: EBS volume は新しい node に attach されます。
4. **Pod Startup**: pod は新しい node で起動し、volume が mount されます。

**この Process の影響:**

1. **Delay Time**: Volume detachment と attachment operations は通常 10〜30 秒かかりますが、場合によってはさらに長くかかることがあります。
2. **Availability Zone の制限**: EBS volumes は作成された availability zone に制限されるため、pods は同じ availability zone 内の他の nodes にのみ移動できます。
3. **Data Persistence**: volume reattachment process 中もデータは保持され、失われません。

**この動作に対処するための戦略:**

1.  **PodDisruptionBudget を使用する**: 同時に中断される可能性のある pods の数を制限して可用性を確保します

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
2.  **適切な readinessProbe と livenessProbe を設定する**: volume が適切に mount され、application の準備が整うまで traffic reception を遅延させます

    ```yaml
    readinessProbe:
      exec:
        command:
        - cat
        - /data/ready
      initialDelaySeconds: 5
      periodSeconds: 5
    ```
3. **StatefulSet を使用する**: StatefulSet は順次 deployment と scaling を提供し、volume reattachment の影響を最小限に抑えます。
4.  **Volume Binding Mode を最適化する**: `WaitForFirstConsumer` を使用して、pod が schedule された availability zone に volumes を作成します

    ```yaml
    volumeBindingMode: WaitForFirstConsumer
    ```

**Availability Zone Considerations:**

1. **Multi-AZ Deployment**: 単一 AZ 障害に対する resilience のため、applications を複数の availability zones にまたがって deploy します
2.  **Topology Spread**: `topologySpreadConstraints` を使用して pods を複数の availability zones に分散します

    ```yaml
    topologySpreadConstraints:
    - maxSkew: 1
      topologyKey: topology.kubernetes.io/zone
      whenUnsatisfiable: DoNotSchedule
      labelSelector:
        matchLabels:
          app: my-app
    ```
3. **Availability Zone-Aware PDB**: availability zone ごとに個別の PodDisruptionBudgets を設定します

**Best Practices:**

1. **高速再起動のために Applications を最適化する**: applications が迅速に起動し初期化されるよう設計します
2.  **適切な Termination Grace Period を設定する**: applications が graceful に終了するための十分な時間を提供します

    ```yaml
    terminationGracePeriodSeconds: 60
    ```
3. **Critical Data の Backup Strategy**: 定期的な snapshots または backups を通じてデータを保護します
4. **Stateless Design を検討する**: 可能な場合は、node 移動の影響を最小化するために applications を stateless として設計します

EBS volume を使用する pod が nodes 間を移動する場合、データは保持されますが、volume reattachment process 中に遅延が発生する可能性があるため、これを考慮した application design と configuration が重要です。

</details>

### 9. What Kubernetes API resource is used to create EBS volume snapshots in Amazon EKS?

<details>

<summary>答えを表示</summary>

**解答:** VolumeSnapshot

**詳細な解説:**

Amazon EKS で EBS volume snapshots を作成するために使用される Kubernetes API resource は `VolumeSnapshot` です。この resource は Kubernetes Volume Snapshot API の一部であり、CSI (Container Storage Interface) drivers と連携して persistent volumes の point-in-time copies を作成します。

**VolumeSnapshot を使用するための前提条件:**

1. **EBS CSI Driver Installation**: AWS EBS CSI driver が cluster にインストールされている必要があります。
2.  **Snapshot Controller Installation**: Kubernetes snapshot controller が cluster にインストールされている必要があります。

    ```bash
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/client/config/crd/snapshot.storage.k8s.io_volumesnapshotclasses.yaml
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/client/config/crd/snapshot.storage.k8s.io_volumesnapshotcontents.yaml
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/client/config/crd/snapshot.storage.k8s.io_volumesnapshots.yaml
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/deploy/kubernetes/snapshot-controller/rbac-snapshot-controller.yaml
    kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/deploy/kubernetes/snapshot-controller/setup-snapshot-controller.yaml
    ```
3. **VolumeSnapshotClass を作成する**: snapshots の作成方法を定義する VolumeSnapshotClass を作成します。

**VolumeSnapshotClass Example:**

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: ebs-snapshot-class
driver: ebs.csi.aws.com
deletionPolicy: Delete
```

**VolumeSnapshot Creation Example:**

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: ebs-volume-snapshot
spec:
  volumeSnapshotClassName: ebs-snapshot-class
  source:
    persistentVolumeClaimName: ebs-claim
```

**Check Snapshot Status:**

```bash
kubectl get volumesnapshot ebs-volume-snapshot
```

**Create New PVC from Snapshot:**

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-claim-from-snapshot
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: ebs-sc
  resources:
    requests:
      storage: 10Gi
  dataSource:
    name: ebs-volume-snapshot
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
```

**VolumeSnapshot の主な利点:**

1. **Data Protection**: 重要なデータの point-in-time backups を作成します
2. **Disaster Recovery**: データ損失や破損時の recovery をサポートします
3. **Environment Replication**: development または test environments のために production data を replicate します
4. **Data Migration**: ある cluster から別の cluster へデータを移動します

**Snapshot Lifecycle Management:**

1.  **Automated Snapshot Creation**: CronJob を使用して定期的な snapshot creation を自動化します

    ```yaml
    apiVersion: batch/v1
    kind: CronJob
    metadata:
      name: volume-snapshot-job
    spec:
      schedule: "0 0 * * *"  # Daily at midnight
      jobTemplate:
        spec:
          template:
            spec:
              serviceAccountName: snapshot-creator
              containers:
              - name: snapshot-creator
                image: bitnami/kubectl:latest
                command:
                - /bin/sh
                - -c
                - |
                  cat <<EOF | kubectl apply -f -
                  apiVersion: snapshot.storage.k8s.io/v1
                  kind: VolumeSnapshot
                  metadata:
                    name: ebs-snapshot-$(date +%Y%m%d)
                  spec:
                    volumeSnapshotClassName: ebs-snapshot-class
                    source:
                      persistentVolumeClaimName: ebs-claim
                  EOF
              restartPolicy: OnFailure
    ```
2.  **Snapshot Retention Policy**: 古い snapshots を自動的に削除します

    ```yaml
    apiVersion: batch/v1
    kind: CronJob
    metadata:
      name: snapshot-cleanup-job
    spec:
      schedule: "0 1 * * *"  # Daily at 1 AM
      jobTemplate:
        spec:
          template:
            spec:
              serviceAccountName: snapshot-manager
              containers:
              - name: snapshot-cleaner
                image: bitnami/kubectl:latest
                command:
                - /bin/sh
                - -c
                - |
                  # Delete snapshots older than 30 days
                  kubectl get volumesnapshot -o json | jq -r '.items[] | select(.metadata.creationTimestamp | fromnow | contains("days") and (split(" ")[0] | tonumber) > 30) | .metadata.name' | xargs -r kubectl delete volumesnapshot
              restartPolicy: OnFailure
    ```

**Best Practices:**

1. **Regular Snapshots**: 重要なデータに対して定期的な snapshot schedules を設定します
2. **Test Snapshots**: backup の有効性を確認するため、snapshots からの restore を定期的にテストします
3. **Tagging**: 管理と cost tracking を容易にするため、snapshots に適切な tags を適用します
4. **Cost Monitoring**: EBS snapshots には追加料金が発生するため、cost を監視し最適化します
5. **Encryption**: sensitive data には encrypted snapshots を使用します

VolumeSnapshot API を使用すると、Kubernetes-native な方法で EBS volume snapshots を作成および管理でき、data protection と recovery strategies を効果的に実装できます。

</details>

## Hands-on Questions

### 10. Design a storage solution for applications with diverse storage requirements in an Amazon EKS cluster. Create storage classes and persistent volume claims that meet the following requirements:

* データベース向けの high-performance block storage
* 複数の pods 間で共有する必要がある configuration files
* AI/ML workloads 向けの high-performance parallel file system

<details>

<summary>答えを表示</summary>

**解答:**

Amazon EKS cluster における多様な storage requirements を満たす storage solution は次のとおりです:

### 1. High-Performance Block Storage for Databases (Amazon EBS gp3)

#### StorageClass Definition:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3-db
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  iops: "16000"  # Maximum IOPS
  throughput: "1000"  # Maximum throughput (MB/s)
  encrypted: "true"
allowVolumeExpansion: true
```

#### PersistentVolumeClaim Definition:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: database-data
  namespace: database
spec:
  accessModes:
    - ReadWriteOnce  # EBS can only be mounted to a single node
  storageClassName: ebs-gp3-db
  resources:
    requests:
      storage: 100Gi
```

#### Database Pod Example:

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: database
spec:
  serviceName: "postgres"
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:14
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
          limits:
            cpu: "4"
            memory: "8Gi"
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: ebs-gp3-db
      resources:
        requests:
          storage: 100Gi
```

**解説:**

* **gp3 Volume Type**: 最大 16,000 IOPS と 1,000MB/s throughput を提供し、database workloads に適しています。
* **WaitForFirstConsumer**: availability zone issues を防ぐため、pod scheduling まで volume creation を遅延させます。
* **Encryption**: data-at-rest security のために EBS volume encryption を有効にします。
* **Volume Expansion**: 将来の database size increases に備えて volume expansion を可能にします。
* **StatefulSet**: databases に対して stable network IDs と persistent storage を提供します。

### 2. Configuration Files Shared Across Multiple Pods (Amazon EFS)

#### EFS CSI Driver Installation:

```bash
helm repo add aws-efs-csi-driver https://kubernetes-sigs.github.io/aws-efs-csi-driver/
helm repo update
helm upgrade -i aws-efs-csi-driver aws-efs-csi-driver/aws-efs-csi-driver \
  --namespace kube-system \
  --set controller.serviceAccount.create=true \
  --set controller.serviceAccount.name=efs-csi-controller-sa
```

#### StorageClass Definition:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0  # Existing EFS file system ID
  directoryPerms: "700"
```

#### PersistentVolumeClaim Definition:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: config-storage
  namespace: application
spec:
  accessModes:
    - ReadWriteMany  # Multiple pods can read/write simultaneously
  storageClassName: efs-sc
  resources:
    requests:
      storage: 5Gi  # This value is symbolic as EFS auto-scales
```

#### Deployment Example Using Configuration Files:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: application
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: web-app
        image: nginx:latest
        volumeMounts:
        - name: config-volume
          mountPath: /etc/config
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "1"
            memory: "1Gi"
      volumes:
      - name: config-volume
        persistentVolumeClaim:
          claimName: config-storage
```

**解説:**

* **ReadWriteMany Access Mode**: EFS は複数の pods が同じ volume に対して同時に読み取りと書き込みを行うことをサポートします。
* **Multi-Availability Zone Support**: EFS は複数の availability zones にまたがってアクセスでき、node failures に対する resilience を提供します。
* **Auto Scaling**: EFS は使用量に基づいて自動的にスケールし、capacity planning の必要性をなくします。
* **Access Points**: EFS access points を使用して、特定の directories へのアクセスを制限できます。

### 3. High-Performance Parallel File System for AI/ML Workloads (Amazon FSx for Lustre)

#### FSx CSI Driver Installation:

```bash
helm repo add aws-fsx-csi-driver https://kubernetes-sigs.github.io/aws-fsx-csi-driver/
helm repo update
helm upgrade -i aws-fsx-csi-driver aws-fsx-csi-driver/aws-fsx-csi-driver \
  --namespace kube-system \
  --set controller.serviceAccount.create=true \
  --set controller.serviceAccount.name=fsx-csi-controller-sa
```

#### StorageClass Definition:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre
provisioner: fsx.csi.aws.com
parameters:
  subnetId: subnet-0123456789abcdef0  # Subnet for FSx file system
  securityGroupIds: sg-0123456789abcdef0  # Security group for FSx file system
  deploymentType: SCRATCH_2  # High-performance temporary storage
  perUnitStorageThroughput: "200"  # MB/s/TiB
  dataCompressionType: "LZ4"  # Enable data compression
  s3ImportPath: s3://ml-training-data-bucket/  # Optional: Import data from S3
mountOptions:
  - flock
```

#### PersistentVolumeClaim Definition:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ml-training-data
  namespace: ml-workloads
spec:
  accessModes:
    - ReadWriteMany  # Multiple pods can read/write simultaneously
  storageClassName: fsx-lustre
  resources:
    requests:
      storage: 1200Gi  # FSx for Lustre starts at minimum 1.2TiB
```

#### ML Training Job Example:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: ml-training
  namespace: ml-workloads
spec:
  parallelism: 4  # Number of parallel jobs
  template:
    spec:
      containers:
      - name: training
        image: tensorflow/tensorflow:latest-gpu
        command:
          - "python"
          - "/training/train.py"
        volumeMounts:
        - name: training-data
          mountPath: "/training"
        resources:
          limits:
            nvidia.com/gpu: 4  # GPU resource request
          requests:
            cpu: "8"
            memory: "32Gi"
      volumes:
      - name: training-data
        persistentVolumeClaim:
          claimName: ml-training-data
      restartPolicy: Never
  backoffLimit: 2
```

**解説:**

* **High Performance**: FSx for Lustre は数百 GB/s の throughput と数百万 IOPS を提供し、AI/ML workloads に適しています。
* **Parallel Access**: 複数の compute nodes が同じデータに同時にアクセスできるため、distributed training に最適です。
* **S3 Integration**: Training data は S3 に保存し、processing のために FSx for Lustre に import できます。
* **Data Compression**: storage efficiency を向上させるため LZ4 compression を使用します。
* **SCRATCH\_2 Deployment Type**: temporary processing 向けの high-performance で cost-effective なオプションです。

### Additional Considerations and Best Practices

#### 1. Backup and Disaster Recovery:

```yaml
# EBS volume snapshot creation
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: ebs-snapshot-class
driver: ebs.csi.aws.com
deletionPolicy: Retain

---
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: database-snapshot
  namespace: database
spec:
  volumeSnapshotClassName: ebs-snapshot-class
  source:
    persistentVolumeClaimName: database-data
```

#### 2. Monitoring and Alerting:

* storage usage、latency、throughput を監視するために CloudWatch alarms を設定します。
* Prometheus と Grafana を使用して storage metrics を可視化します。

#### 3. Cost Optimization:

* 未使用 volumes は削除前に削除するか snapshots を作成します。
* cost を最適化するため、適切な storage types と sizes を選択します。
* FSx for Lustre では、long-term storage が不要な場合は SCRATCH deployment type を使用します。

#### 4. Security:

* すべての volumes で encryption を有効にします。
* 適切な IAM permissions と security groups を設定します。
* volume access を制限するために PodSecurityPolicy または SecurityContext を使用します。

この design は、多様な workload requirements を満たす包括的な storage solution を提供します:

* databases 向けの high-performance EBS gp3 volumes
* configuration file sharing 向けに multi-read/write access をサポートする EFS
* AI/ML workloads 向けの high-performance parallel file system FSx for Lustre

各 storage solution は特定の workload requirements に合わせて最適化され、scalability、performance、cost efficiency を考慮して設計されています。

</details>
