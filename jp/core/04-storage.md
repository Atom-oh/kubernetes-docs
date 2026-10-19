# ストレージ

> **サポート対象バージョン**: Kubernetes 1.35、1.36、1.37
> **最終更新日**: 2026年10月16日

Kubernetesでは、ストレージはコンテナ化されたアプリケーションのデータを保存・管理するうえで重要な要素です。この章では、Volumes、Persistent Volumes、Persistent Volume Claims、Storage Classesなど、Kubernetesのストレージに関する概念を詳しく見ていきます。

## ラボ環境のセットアップ

このドキュメントの例を実行するには、次のツールと環境が必要です。

### 必要なツール
- APIサーバーとマイナーバージョンが1つ以内のkubectl
- 稼働中のKubernetesクラスター（EKS、minikube、kindなど）
- ストレージプロビジョナー（EKSの場合はEBS CSI driver）

最初の例ではデフォルトのStorageClassが必要です。デフォルトがない場合は、`storageClassName`をインストール済みのクラスに設定してください。以下のEKS EBSの例では、IAM権限を持つEC2ノード上の標準EBS CSI driverを使用します。Auto Modeでは`ebs.csi.eks.amazonaws.com`を使用します。EBSはFargateまたはHybrid Nodesにはマウントできません。以降のマニフェストは、それぞれに記載された前提条件を持つ独立した例として扱ってください。

### ストレージのサンプルセットアップ

```bash
# Create namespace
kubectl create namespace storage-demo

# Create a simple PVC and Pod
kubectl -n storage-demo apply -f - <<'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: data-pod
spec:
  containers:
  - name: data-container
    image: busybox
    command: ["sh", "-c", "while true; do echo $(date) >> /data/output.txt; sleep 5; done"]
    volumeMounts:
    - name: data-volume
      mountPath: /data
  volumes:
  - name: data-volume
    persistentVolumeClaim:
      claimName: data-pvc
EOF

# Check storage resources
kubectl -n storage-demo get pvc,pod
```

## 目次

1. [Volumes](#volumes)
2. [Persistent Volumes](#persistent-volumes)
3. [Persistent Volume Claims](#persistent-volume-claims)
4. [Storage Classes](#storage-classes)
5. [Dynamic Provisioning](#dynamic-provisioning)
6. [Volume Snapshots](#volume-snapshots)
7. [Volume Expansion](#volume-expansion)
8. [Projected Volumes](#projected-volumes)
9. [Generic Ephemeral Volumes](#generic-ephemeral-volumes)
10. [Block Volume Mode](#block-volume-mode)
11. [Volume Cloning](#volume-cloning)
12. [Storage ResourceQuota](#storage-resourcequota)
13. [EKSのストレージオプション](#storage-options-in-eks)

## Volumes

> **重要な概念**: KubernetesのVolumesは、Pod内のコンテナがデータを保存・共有するためのディレクトリです。コンテナが再起動してもデータを保持できます。

KubernetesのVolumesは、Pod内のコンテナがデータを保存・共有するためのディレクトリです。マウントの存続期間はPodの存続期間に対応しますが、バックエンドデータが保持されるかどうかはボリュームの種類によって異なります。emptyDirのデータはPodとともに削除されますが、永続ストレージはPodより長く存続できます。

### Kubernetesストレージアーキテクチャ

![PodはPersistentVolumeClaimを通じてストレージを要求します。PersistentVolumeClaimはStorageClassによってプロビジョニングされたPersistentVolumeにバインドされ、CSI Driverがそのボリュームをクラウド、ローカル、またはNFSの基盤ストレージにアタッチします。](../.gitbook/assets/en-core-04-storage-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-04-storage-0.html)

### Volumesが必要な理由

1. **コンテナ再起動後のデータ永続化**: コンテナが再起動するとファイルシステムはリセットされますが、Volumesを使用するとデータを保持できます。
2. **コンテナ間でのデータ共有**: 同じPod内の複数のコンテナは、Volumesを通じてデータを共有できます。

### 主なボリューム種類の比較

| ボリュームの種類 | ライフサイクル | データの永続性 | 用途 | 特徴 |
|------------|----------|-----------------|----------|----------|
| **emptyDir** | Pod | 一時的 | 一時データ、キャッシュ、チェックポイント | Podが削除されるとデータも削除される |
| **hostPath** | Node | Nodeレベル | Nodeのファイルシステムへのアクセス、監視 | セキュリティリスクがあるため、慎重に使用する |
| **configMap** | 設定 | 設定データ | アプリケーションの設定 | 設定データをボリュームとしてマウント |
| **secret** | 設定 | 機密データ | 証明書、パスワード | 機密データをボリュームとしてマウント |
| **persistentVolumeClaim** | クラスター | 永続的 | データベース、ファイルストレージ | Podの再起動や再スケジュール後もデータが保持される |

### emptyDir

`emptyDir`ボリュームは、PodがNodeに割り当てられると作成され、そのNode上でPodが実行されている間存続します。PodがNodeから削除されると、`emptyDir`内のデータは完全に削除されます。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-pd
spec:
  containers:
  - image: nginx
    name: test-container
    volumeMounts:
    - mountPath: /cache
      name: cache-volume
  volumes:
  - name: cache-volume
    emptyDir: {}
```

### hostPath

`hostPath`ボリュームは、Nodeのファイルシステム上のファイルまたはディレクトリをPodにマウントします。Nodeのファイルシステムへのアクセスが必要なPodに便利ですが、セキュリティリスクがあるため慎重に使用してください。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-hostpath
spec:
  containers:
  - image: nginx
    name: test-container
    volumeMounts:
    - mountPath: /test-pd
      name: test-volume
  volumes:
  - name: test-volume
    hostPath:
      path: /data
      type: Directory  # DirectoryOrCreate, Directory, FileOrCreate, File, Socket, CharDevice, BlockDevice
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-pd
spec:
  containers:
  - image: nginx
    name: test-container
    volumeMounts:
    - mountPath: /test-pd
      name: test-volume
  volumes:
  - name: test-volume
    hostPath:
      path: /data
      type: Directory
```

#### configMap

`configMap`ボリュームは、ConfigMapのデータをPodにマウントします。ConfigMapは、キーと値のペアで設定データを保存するために使用されます。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: configmap-pod
spec:
  containers:
  - name: test
    image: busybox
    volumeMounts:
    - name: config-vol
      mountPath: /etc/config
  volumes:
  - name: config-vol
    configMap:
      name: log-config
      items:
      - key: log_level
        path: log_level
```

#### secret

`secret`ボリュームは、SecretのデータをPodにマウントします。Secretsは、パスワード、トークン、キーなどの機密情報を保存するために使用されます。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secret-pod
spec:
  containers:
  - name: test
    image: busybox
    volumeMounts:
    - name: secret-vol
      mountPath: /etc/secret
      readOnly: true
  volumes:
  - name: secret-vol
    secret:
      secretName: mysecret
      items:
      - key: username
        path: my-username
```

#### nfs

`nfs`ボリュームは、既存のNFS（Network File System）共有をPodにマウントします。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nfs-pod
spec:
  containers:
  - name: test
    image: busybox
    volumeMounts:
    - name: nfs-vol
      mountPath: /mnt/nfs
  volumes:
  - name: nfs-vol
    nfs:
      server: nfs-server.example.com
      path: /share
```

#### persistentVolumeClaim

`persistentVolumeClaim`ボリュームは、PersistentVolumeClaimをPodにマウントします。最も一般的に使われるボリューム種類の1つです。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pvc-pod
spec:
  containers:
  - name: test
    image: busybox
    volumeMounts:
    - name: pvc-vol
      mountPath: /mnt/pvc
  volumes:
  - name: pvc-vol
    persistentVolumeClaim:
      claimName: my-pvc
```

#### CSI（Container Storage Interface）

CSI Volumesは、Kubernetesと外部ストレージシステムの間に標準インターフェースを提供します。CSIを使用することで、ストレージベンダーはKubernetesのコードを変更せずに独自のストレージドライバーを開発できます。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: csi-pod
spec:
  containers:
  - name: test
    image: busybox
    volumeMounts:
    - name: csi-vol
      mountPath: /mnt/csi
  volumes:
  - name: csi-vol
    csi:
      driver: csi-driver.example.com
      volumeAttributes:
        foo: bar
      nodePublishSecretRef:
        name: csi-secret
```

## Persistent Volumes

Persistent Volume（PV）は、管理者がプロビジョニングするか、Storage Classを使って動的にプロビジョニングするクラスターのストレージです。PVのライフサイクルはPodとは独立しており、Podが削除されてもPVは保持されます。

![静的プロビジョニングの流れでは、クラスター管理者が物理ストレージに接続されたPersistentVolumeを作成し、ユーザーのPersistentVolumeClaimがそのボリュームにバインドされ、PodがそのClaimをボリュームとして使用します。](../.gitbook/assets/en-core-04-storage-1.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-04-storage-1.html)

### PVの作成

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv0001
  labels:
    release: stable
    environment: dev
spec:
  capacity:
    storage: 10Gi
  volumeMode: Filesystem
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: slow
  mountOptions:
    - hard
    - nfsvers=4.1
  nfs:
    path: /tmp
    server: 172.17.0.2
```

### PVのアクセスモード

PVは次のアクセスモードをサポートします。

- **ReadWriteOnce（RWO）**: 1つのNodeがボリュームを読み書き可能な状態でマウントできます。
- **ReadOnlyMany（ROX）**: 複数のNodeがボリュームを読み取り専用でマウントできます。
- **ReadWriteMany（RWX）**: 複数のNodeがボリュームを読み書き可能な状態でマウントできます。
- **ReadWriteOncePod（RWOP）**: 1つのPodがボリュームを読み書き可能な状態でマウントできます（CSIのみ。v1.29から安定版）。

RWOが書き込み可能なマウントを制限する対象は1つの**Node**であり、1つのPodではありません。同じNode上の複数のPodでボリュームを共有できます。RWOPでは、対応するCSI driverを使用する場合に1つのPodのみが使用できます。アクセスモードはファイルシステムの権限の代わりにはなりません。

### PVの回収ポリシー

PVには次の回収ポリシーを設定できます。

- **Retain**: PVCが削除されても、PVとデータは保持されます。管理者が手動でクリーンアップする必要があります。
- **Delete**: PVCが削除されると、PVと外部ストレージ資産は自動的に削除されます。
- **Recycle**: PVCが削除されると、PV内のデータが削除され、PVが再び使用可能になります（非推奨）。

### PVのステータス

PVには次のステータスがあります。

- **Available**: Claimにまだバインドされていない使用可能なリソース。
- **Bound**: Claimにバインドされている状態。
- **Released**: Claimは削除されていますが、リソースはまだクラスターによって回収されていない状態。
- **Failed**: 自動回収に失敗した状態。

## Persistent Volume Claims

Persistent Volume Claim（PVC）は、ユーザーによるストレージの要求です。PVCはPVと似ていますが、ユーザーがストレージを要求する方法がPVCであり、管理者がストレージを提供する方法がPVです。

### PVCの作成

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: myclaim
spec:
  accessModes:
    - ReadWriteOnce
  volumeMode: Filesystem
  resources:
    requests:
      storage: 8Gi
  storageClassName: slow
  selector:
    matchLabels:
      release: "stable"
    matchExpressions:
      - {key: environment, operator: In, values: [dev]}
```

### PVCとPVのバインド

PVCが作成されると、KubernetesはPVCの要件（ストレージ容量、アクセスモード、ストレージクラス、セレクターなど）を満たすPVを見つけてバインドします。一致するPVがない場合、適切なStorageClassがあれば動的にプロビジョニングできます。空でないセレクター（上記の例など）を持つPVCは動的にプロビジョニングできないため、一致する静的PVがなければPendingのままになります。WaitForFirstConsumerの場合は、スケジューリングまで意図的にバインドが遅延されます。

### PVCの使用

PVCはPodのボリュームとして使用できます。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mypod
spec:
  containers:
    - name: myfrontend
      image: nginx
      volumeMounts:
      - mountPath: "/var/www/html"
        name: mypd
  volumes:
    - name: mypd
      persistentVolumeClaim:
        claimName: myclaim
```

## Storage Classes

Storage Classesは、管理者が提供するストレージの「クラス」を記述します。Storage Classesは、PVを動的にプロビジョニングするために使用されます。

![ユーザーのPersistentVolumeClaimがStorageClassを参照し、StorageClassがPersistentVolumeを動的にプロビジョニングします。Claimはそのボリュームにバインドされ、Podが使用し、最終的に物理ストレージに接続されます。](../.gitbook/assets/en-core-04-storage-2.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-04-storage-2.html)

### Storage Classの作成

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: standard
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  csi.storage.k8s.io/fstype: ext4
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
```

この例では、AWS EBS gp3ボリュームをプロビジョニングするStorageClassを作成します。

### プロビジョナー

Storage Classesでは、ボリュームのプロビジョニングに使用するプロビジョナーを指定します。現在のCSIプロビジョナーには次のものがあります。

- `ebs.csi.aws.com`: AWS EBS
- `efs.csi.aws.com`: AWS EFS
- `fsx.csi.aws.com`: FSx for Lustre
- `pd.csi.storage.gke.io`: Google Persistent Disk
- `disk.csi.azure.com` / `file.csi.azure.com`: Azure Disk/File
- `nfs.csi.k8s.io`: NFS CSI driver（既存のNFSサーバーが必要）

従来のインツリー型クラウドプラグインは削除または移行されています。適切なCSI driverをインストールしてください。Kubernetesには組み込みの`kubernetes.io/nfs`動的プロビジョナーはありません。

### ボリュームのバインドモード

Storage Classesは次のボリュームバインドモードをサポートします。

- **Immediate**: デフォルト。PVCの作成時にボリュームを直ちにプロビジョニングします。
- **WaitForFirstConsumer**: PodがPVCを使用しようとするまで、ボリュームのプロビジョニングを遅らせます。Podと同じゾーンにボリュームをプロビジョニングするのに役立ちます。

### デフォルトのStorage Class

クラスターにはデフォルトのStorage Classを設定できます。PVCでStorage Classが指定されていない場合、デフォルトのStorage Classが使用されます。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: standard
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
```

## Dynamic Provisioning

Dynamic Provisioningは、PVCの作成時にPVを自動作成する機能です。これにより、管理者が事前にPVを作成しなくても、ユーザーは必要なときにストレージを要求できます。

### Dynamic Provisioningの例

1. Storage Classを作成します。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  encrypted: "true"
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
```

2. PVCを作成します。

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: myclaim
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
  storageClassName: fast
```

3. PodでPVCを使用します。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mypod
spec:
  containers:
    - name: myfrontend
      image: nginx
      volumeMounts:
      - mountPath: "/var/www/html"
        name: mypd
  volumes:
    - name: mypd
      persistentVolumeClaim:
        claimName: myclaim
```

## Volume Snapshots

Kubernetesでは、PVの特定時点のコピーを作成するためにVolume Snapshotsをサポートしています。これはバックアップや復元のシナリオで役立ちます。

![Volume SnapshotはVolume Snapshot Classを参照して既存のPersistentVolumeClaimのスナップショットを取得します。そのスナップショットをデータソースとして使用する新しいPVCは、スナップショットから復元された新しいPVにバインドされます。](../.gitbook/assets/en-core-04-storage-3.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-04-storage-3.html)

snapshot CRD、snapshot controller、およびスナップショットに対応したCSI driverをインストールしてください。以下の例ではEBSを使用します。ソースPVCと復元先のStorageClassは、同じdriverを使用する必要があります。`readyToUse: true`になるまで待ち、スナップショットの復元サイズ以上の容量を要求してください。ストレージのスナップショットだけではデータベースの整合性は保証されません。書き込みを静止させるか、データベース対応のバックアップを使用してください。

### Volume Snapshot Class

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: ebs-snapclass
driver: ebs.csi.aws.com
deletionPolicy: Delete
```

### Volume Snapshotの作成

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: new-snapshot
spec:
  volumeSnapshotClassName: ebs-snapclass
  source:
    persistentVolumeClaimName: myclaim
```

### SnapshotからPVCを作成

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: restore-pvc
spec:
  storageClassName: standard
  dataSource:
    name: new-snapshot
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
```

## Volume Expansion

KubernetesではPVCのサイズを拡張できます。そのためには、Storage Classで`allowVolumeExpansion: true`を設定する必要があります。

![PersistentVolumeClaimを拡張するユーザーの要求はStorageClassを経由します。StorageClassはallowVolumeExpansionが有効かどうかを確認し、その後PersistentVolumeが基盤ディスクを拡張し、Podのファイルシステムも拡張されます。](../.gitbook/assets/en-core-04-storage-4.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-04-storage-4.html)

### PVCの拡張

拡張に対応したEBS StorageClass上にある既存の100Gi PVCの場合、要求サイズのみを変更します。

```bash
kubectl patch pvc myclaim --type merge -p '{"spec":{"resources":{"requests":{"storage":"120Gi"}}}}'
```

PVCのnamespaceと既存のStorageClassを使用してください。driverとファイルシステムが拡張に対応している必要があります。縮小はサポートされていません。バインド済みPVCのクラスを変更したり、サイズ変更を装うためにPVの容量を直接編集したりしないでください。

## Projected Volumes

Projected Volumesを使用すると、複数のボリュームソースを1つのボリュームマウントにまとめられます。Secret、ConfigMap、downwardAPI、serviceAccountTokenを1つのディレクトリにまとめて公開する場合に便利です。

### サポート対象のソース

- **secret**: Secretデータをマウント
- **configMap**: 設定データをマウント
- **downwardAPI**: Podとコンテナのメタデータを公開
- **serviceAccountToken**: 有効期限を設定できるService Accountトークンをマウント

### Projected Volumeの例

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: projected-volume-pod
spec:
  containers:
  - name: app
    image: busybox
    command: ["sh", "-c", "ls -la /etc/projected && sleep 3600"]
    volumeMounts:
    - name: all-in-one
      mountPath: /etc/projected
      readOnly: true
  volumes:
  - name: all-in-one
    projected:
      sources:
      - secret:
          name: db-credentials
          items:
          - key: username
            path: db/username
          - key: password
            path: db/password
      - configMap:
          name: app-config
          items:
          - key: config.yaml
            path: config/app.yaml
      - downwardAPI:
          items:
          - path: labels
            fieldRef:
              fieldPath: metadata.labels
          - path: cpu-request
            resourceFieldRef:
              containerName: app
              resource: requests.cpu
      - serviceAccountToken:
          path: token
          expirationSeconds: 3600
          audience: api
```

この設定では、次の内容を含む単一のボリュームが`/etc/projected`に作成されます。
- Secret由来の`/etc/projected/db/username`と`/etc/projected/db/password`
- ConfigMap由来の`/etc/projected/config/app.yaml`
- downwardAPI由来の`/etc/projected/labels`と`/etc/projected/cpu-request`
- 自動ローテーションされるService Accountトークンを含む`/etc/projected/token`

### Service Accountトークンの投影

Service Accountトークンの投影では、有効期間とaudienceが制限されたトークンを提供します。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: token-projected-pod
spec:
  serviceAccountName: my-service-account
  containers:
  - name: app
    image: myapp:latest
    volumeMounts:
    - name: token
      mountPath: /var/run/secrets/tokens
  volumes:
  - name: token
    projected:
      sources:
      - serviceAccountToken:
          path: api-token
          expirationSeconds: 7200  # 2 hours
          audience: my-api-service
```

投影されたトークンはローテーションされるため、アプリケーションはファイルを読み直す必要があります。明示的に指定した`audience`は、意図した検証側と一致している必要があります。Kubernetes APIへのアクセスに自動的に有効となるわけではありません。

## Generic Ephemeral Volumes

Generic Ephemeral Volumesは、Podのライフサイクルに連動するPVCのようなストレージを提供します。emptyDirとは異なり、Dynamic Provisioningを含むPVCとStorageClassの機能をすべて利用できます。

### emptyDirとの違い

| 特徴 | emptyDir | Generic Ephemeral Volume |
|---------|----------|--------------------------|
| **ストレージバックエンド** | Nodeのローカルストレージまたはメモリー | 任意のCSI driver |
| **プロビジョニング** | 自動、簡易 | StorageClassを使用した動的プロビジョニング |
| **サイズ制限** | sizeLimit（ソフト制限） | PVCの容量管理機能をすべて利用 |
| **スナップショット** | 非対応 | 対応（CSI driverがサポートする場合） |
| **ストレージ機能** | 基本機能 | CSIの全機能（暗号化、IOPSなど） |
| **永続性** | Podの削除時に失われる | PVCはPodとともに削除され、バックエンドの動作は回収ポリシーに従う |

### Generic Ephemeral Volumeの例

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: ephemeral-volume-pod
spec:
  containers:
  - name: app
    image: busybox
    command: ["sh", "-c", "dd if=/dev/zero of=/scratch/data bs=1M count=100 && sleep 3600"]
    volumeMounts:
    - name: scratch
      mountPath: /scratch
  volumes:
  - name: scratch
    ephemeral:
      volumeClaimTemplate:
        metadata:
          labels:
            type: scratch-storage
        spec:
          accessModes:
          - ReadWriteOnce
          storageClassName: fast-ssd
          resources:
            requests:
              storage: 10Gi
```

### ユースケース

1. **CI/CDパイプライン**: 容量が保証された一時的なビルド成果物
2. **データ処理**: 特定のパフォーマンス要件を満たすスクラッチ領域
3. **テスト**: CSI機能を利用する一時的なデータベースやキャッシュ
4. **機械学習**: 高性能ストレージ上の一時的なモデルチェックポイント

### Generic Ephemeral Volumesを使用したDeployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-training
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ml-training
  template:
    metadata:
      labels:
        app: ml-training
    spec:
      containers:
      - name: trainer
        image: ml-trainer:latest
        volumeMounts:
        - name: checkpoint-storage
          mountPath: /checkpoints
      volumes:
      - name: checkpoint-storage
        ephemeral:
          volumeClaimTemplate:
            spec:
              accessModes:
              - ReadWriteOnce
              storageClassName: high-iops
              resources:
                requests:
                  storage: 50Gi
```

Generic Ephemeral PVCはPodに所有され、Podとともにガベージコレクションされます。基盤データの削除動作はPVの回収ポリシーに従います。`Retain`の場合は、手動でクリーンアップするまでストレージが残ります。Podの消失後も保持する必要があるチェックポイントは、永続ストレージにエクスポートしてください。

## Block Volume Mode

Kubernetesでは、ファイルシステムボリュームに加えてraw blockボリュームもサポートしています。Blockボリュームはファイルシステムを介さずにraw blockデバイスとしてストレージを提供するため、独自のデータ配置を管理するアプリケーションに適しています。

### FilesystemモードとBlockモードの比較

| 項目 | Filesystem（デフォルト） | Block |
|--------|---------------------|-------|
| **volumeMode** | `Filesystem` | `Block` |
| **マウントの種類** | ディレクトリとしてマウント | デバイスファイルとして公開 |
| **ファイルシステム** | ext4、xfsなど | なし（raw） |
| **Pod内でのアクセス** | `/mnt/data/` | `/dev/xvda` |
| **用途** | 一般的なアプリケーション | データベース、特殊用途のアプリケーション |

### BlockモードのPVとPVC

```yaml
# PersistentVolume with Block mode
apiVersion: v1
kind: PersistentVolume
metadata:
  name: block-pv
spec:
  capacity:
    storage: 100Gi
  volumeMode: Block
  accessModes:
  - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: block-storage
  csi:
    driver: ebs.csi.aws.com
    volumeHandle: vol-0123456789abcdef0
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: topology.kubernetes.io/zone
          operator: In
          values: [us-west-2a]
---
# PersistentVolumeClaim for Block volume
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: block-pvc
spec:
  volumeMode: Block
  accessModes:
  - ReadWriteOnce
  storageClassName: block-storage
  resources:
    requests:
      storage: 100Gi
```

### PodでのBlock Volumesの使用

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: block-volume-pod
spec:
  containers:
  - name: database
    image: custom-database:latest
    volumeDevices:
    - name: data
      devicePath: /dev/xvda
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: block-pvc
```

注: Block Volumesでは、`volumeMounts`と`mountPath`の代わりに`volumeDevices`と`devicePath`を使用します。

### Block Volumesのユースケース

1. **特殊なストレージエンジン**: raw blockデバイス用に明示的に設計されたソフトウェアのみが対象です。通常のMySQL/PostgreSQLデータディレクトリにはファイルシステムが必要です。
2. **カスタムファイルシステム**: ZFSやLVMなどの特殊なファイルシステムを使用するアプリケーション
3. **高性能ストレージ**: ファイルシステムのオーバーヘッドなしで直接I/Oを必要とするアプリケーション
4. **ストレージ仮想化**: ソフトウェア定義ストレージソリューション

静的EBSボリュームIDとnodeAffinityのゾーンは、実際のボリュームとそのAvailability Zoneに置き換えてください。`custom-database`イメージは、raw blockデバイスをサポートするソフトウェアのプレースホルダーです。

## Volume Cloning

Volume Cloningは、既存のPVCの内容を持つ新しいPVCを作成します。テスト環境の作成、データの複製、ワークロードの移行に役立ちます。

### 前提条件

EBS CSIはv1.51.0からPVCクローンをサポートしています（[バージョン指定の例](https://github.com/kubernetes-sigs/aws-ebs-csi-driver/blob/v1.67.0/examples/kubernetes/clone/README.md)）。インストール済みのdriverとIAM権限を確認してください。FSx for Lustre CSIは`CLONE_VOLUME`を通知していません。EFSもサポートされていると推測しないでください。`kubectl get csidriver`ではCSI RPCの機能は確認できません。

- CSI driverがボリュームクローンをサポートしていること
- ソースPVCと宛先PVCが同じnamespaceにあること
- driverがサポートする場合は異なるStorageClassも使用できます。ソースはバインド済みで、使用中でないこと
- ソースと宛先のvolumeModeが同じであること

### PVCクローンの例

```yaml
# Source PVC (existing)
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: source-pvc
  namespace: production
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-sc
  resources:
    requests:
      storage: 100Gi
---
# Clone PVC using dataSource
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: cloned-pvc
  namespace: production
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-sc
  resources:
    requests:
      storage: 100Gi  # Must be >= source size
  dataSource:
    kind: PersistentVolumeClaim
    name: source-pvc
```

### クローンとスナップショットの比較

| 特徴 | Volume Cloning | Volume Snapshots |
|---------|---------------|------------------|
| **結果** | データを含む新しいPVC | Snapshotオブジェクト |
| **用途** | 使用可能なソースボリュームの複製 | 特定時点のバックアップ |
| **パフォーマンス** | driver/バックエンドに依存 | driver/バックエンドに依存 |
| **namespaceをまたぐ使用** | 不可 | 不可 |
| **ストレージのオーバーヘッド** | バックエンドに依存 | バックエンドに依存 |

### テスト用のクローン

最初に、`staging`内にバインド済みで整合性の取れた`staging-source-pvc`を作成してください。`dataSource`から`production`内のPVCを直接参照することはできません。クローンには、互換性のあるPostgreSQLデータディレクトリがあらかじめ含まれている必要があります。これは初期化の例ではありません。

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-db-clone
  namespace: staging
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-sc
  resources:
    requests:
      storage: 100Gi
  dataSource:
    kind: PersistentVolumeClaim
    name: staging-source-pvc
---
apiVersion: v1
kind: Pod
metadata:
  name: test-database
  namespace: staging
spec:
  containers:
  - name: postgres
    image: postgres:15
    volumeMounts:
    - name: data
      mountPath: /var/lib/postgresql/data
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: test-db-clone
```

## Storage ResourceQuota

ResourceQuotaは、PVCの数や総ストレージ容量を含め、namespace内のストレージ消費量を制限できます。

### ストレージ関連のクォータフィールド

| フィールド | 説明 |
|-------|-------------|
| **persistentvolumeclaims** | 許可されるPVCの合計数 |
| **requests.storage** | すべてのPVCの合計ストレージ容量 |
| **\<storage-class\>.storageclass.storage.k8s.io/requests.storage** | 特定のStorageClassに対するストレージ容量 |
| **\<storage-class\>.storageclass.storage.k8s.io/persistentvolumeclaims** | 特定のStorageClassに対するPVC数 |

### ResourceQuotaの例

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: storage-quota
  namespace: team-a
spec:
  hard:
    # Total limits
    persistentvolumeclaims: "10"
    requests.storage: "500Gi"

    # Per-StorageClass limits
    ebs-sc.storageclass.storage.k8s.io/requests.storage: "200Gi"
    ebs-sc.storageclass.storage.k8s.io/persistentvolumeclaims: "5"

    efs-sc.storageclass.storage.k8s.io/requests.storage: "300Gi"
    efs-sc.storageclass.storage.k8s.io/persistentvolumeclaims: "5"
```

### ResourceQuotaのステータス確認

```bash
# View quota status
kubectl get resourcequota storage-quota -n team-a -o yaml

# Example output
status:
  hard:
    persistentvolumeclaims: "10"
    requests.storage: "500Gi"
  used:
    persistentvolumeclaims: "3"
    requests.storage: "150Gi"
```

### ストレージ用のLimitRange

LimitRangeはPVCストレージ要求の最小値と最大値を適用できます。PVCの要求が指定されていない場合にデフォルト値を設定するものではありません。

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: storage-limits
  namespace: team-a
spec:
  limits:
  - type: PersistentVolumeClaim
    min:
      storage: 1Gi
    max:
      storage: 100Gi
```

これにより、次のことが保証されます。
- PVCの最小サイズは1Gi
- PVCの最大サイズは100Gi
- すべてのPVCでストレージを明示的に要求する必要があり、LimitRangeによるPVCのデフォルト値設定はありません

## EKSのストレージオプション

Amazon EKSではさまざまなストレージオプションを利用できます。各オプションは用途やパフォーマンス特性が異なるため、アプリケーションの要件に合ったストレージを選択することが重要です。

![Amazon EKSのPodは、EBSからブロックストレージ、EFSから共有ファイルストレージ、FSx for Lustreから高性能な並列ストレージを利用します。それぞれ専用のCSI driver、StorageClass、PersistentVolumeを通じてプロビジョニングされます。](../.gitbook/assets/en-core-04-storage-5.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-04-storage-5.html)

### Amazon EBS

Amazon EBS（Elastic Block Store）は、EC2インスタンスにアタッチできるブロックストレージボリュームを提供します。EKSではEBS CSI driverを使用して、EBSボリュームをKubernetes Podにマウントできます。

#### EBS CSI Driverのインストール

[ EKS driverのインストールガイド](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)に従って、互換性のあるアドオン/driverバージョンを選択し、PVCを作成する前にIAMロールとNodeの前提条件を設定してください。StorageClassだけではdriverはインストールされません。

#### EBS Storage Class

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-sc
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  csi.storage.k8s.io/fstype: ext4
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
```

#### EBSボリュームタイプ

Amazon EBSには、さまざまなボリュームタイプがあります。

1. **gp3**: 多くのワークロードに適した汎用SSDボリュームです。ベースラインとして3,000 IOPS、125 MiB/sを提供します。現在、リージョンごとのボリューム上限は最大80,000 IOPS、2,000 MiB/sですが、容量とIOPSの比率およびインスタンスの上限が適用されます。Outpostsの上限はより低くなります（[AWSの仕様](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)）。

2. **io2**: 高いIOPSを必要とするワークロードに適した高性能SSDボリュームです。現在のio2 Block Expressは、対応するNitroインスタンスで最大1,000 IOPS/GiB、256,000 IOPSをサポートします。ただし、インスタンスとボリュームの上限が適用されます（[AWSの仕様](https://docs.aws.amazon.com/ebs/latest/userguide/provisioned-iops.html)）。

3. **st1**: ビッグデータ、データウェアハウス、ログ処理など、スループットを多く必要とするワークロードに適したスループット最適化HDDボリュームです。

4. **sc1**: アクセス頻度の低いデータに適したコールドHDDボリュームです。

#### EBS Storage Classの例（gp3）

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
  encrypted: "true"
  kmsKeyId: "arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab"
volumeBindingMode: WaitForFirstConsumer
```

#### EBS Storage Classの例（io2）

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-io2
provisioner: ebs.csi.aws.com
parameters:
  type: io2
  iops: "10000"
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
```

### Amazon EFS

Amazon EFS（Elastic File System）は、複数のEC2インスタンスから同時にアクセスできるスケーラブルなファイルストレージを提供します。EFSはReadWriteManyアクセスモードをサポートしているため、複数のPodで同じボリュームを共有する場合に役立ちます。

#### EFS CSI Driverのインストール

[ EKS driverのインストールガイド](https://docs.aws.amazon.com/eks/latest/userguide/efs-csi.html)に従って、互換性のあるアドオン/driverバージョンを選択し、PVCを作成する前にIAMロールとNodeの前提条件を設定してください。StorageClassだけではdriverはインストールされません。

#### EFSファイルシステムの作成

EFSファイルシステムを作成するには、AWS Management Console、AWS CLI、またはAWS CloudFormationを使用できます。

AWS CLIの例:

```bash
# Create EFS file system
aws efs create-file-system \
  --creation-token eks-efs \
  --performance-mode generalPurpose \
  --encrypted \
  --throughput-mode bursting \
  --tags Key=Name,Value=EKS-EFS

# Store file system ID
FS_ID=$(aws efs describe-file-systems \
  --creation-token eks-efs \
  --query "FileSystems[0].FileSystemId" \
  --output text)

# Create one mount target per Availability Zone
aws efs create-mount-target \
  --file-system-id "$FS_ID" \
  --subnet-id subnet-0eabfaa81fb22bcaf \
  --security-groups sg-068000ccf82dfba88
```

#### EFS Storage Class

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-1234abcd
  directoryPerms: "700"
```

#### PVとPVCを使用したEFS Access Point

```yaml
# Persistent Volume
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
    volumeHandle: fs-1234abcd::fsap-0123456789abcdef
---
# Persistent Volume Claim
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: efs-pvc
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: efs-sc
  resources:
    requests:
      storage: 5Gi
```

ファイルシステムIDとAccess Point IDを置き換え、クライアントのセキュリティグループからマウントターゲットへのNFS TCP 2049を許可してください。Dynamic Provisioningでは既存のファイルシステム上にAccess Pointが作成されますが、ファイルシステム自体は作成されません。EFS PVCの容量はバインド用の値であり、PVCごとのクォータではありません。EFSは弾力的に拡張されます。Fargateがサポートするのは静的なEFSプロビジョニングのみです。

#### EFSのパフォーマンスモード

EFSには2つのパフォーマンスモードがあります。

1. **General Purpose**: ほとんどのファイルシステムワークロードに推奨されるデフォルトモードです。低レイテンシーを提供します。

2. **Max I/O**: 1操作あたりのレイテンシーがより高い旧世代のモードです。AWSは新しいワークロードにはGeneral Purposeを推奨しています。Max I/OはElasticスループットと互換性がありません。

#### EFSのスループットモード

EFSには3つのスループットモードがあります。

1. **Bursting**: ベーススループットはファイルシステムのサイズに基づいて割り当てられ、バーストクレジットにより一時的に高いスループットが得られます。

2. **Provisioned**: ファイルシステムのサイズに関係なく、指定されたスループットを提供します。

3. **Elastic**: ワークロードに応じてスループットを自動的に増減します。

### Amazon FSx for Lustre

Amazon FSx for Lustreは、高性能コンピューティングのワークロード向けに高性能なファイルシステムを提供します。FSx for Lustreは、大規模なデータ処理、機械学習、分析のワークロードに適しています。

#### FSx for Lustre CSI Driverのインストール

[EKS driverのインストールガイド](https://docs.aws.amazon.com/eks/latest/userguide/fsx-csi-create.html)に従って、互換性のあるアドオン/driverバージョンを選択し、PVCを作成する前にIAMロールとNodeの前提条件を設定してください。StorageClassだけではdriverはインストールされません。

#### FSx for Lustreファイルシステムの作成

AWS CLIの例:

```bash
aws fsx create-file-system \
  --file-system-type LUSTRE \
  --storage-capacity 1200 \
  --subnet-ids subnet-0eabfaa81fb22bcaf \
  --lustre-configuration DeploymentType=SCRATCH_2
```

#### FSx for Lustre Storage Class

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-sc
provisioner: fsx.csi.aws.com
parameters:
  subnetId: subnet-0eabfaa81fb22bcaf
  securityGroupIds: sg-068000ccf82dfba88
  deploymentType: SCRATCH_2
  dataCompressionType: "NONE"
  weeklyMaintenanceStartTime: "7:09:00"
```

#### FSx for LustreのDeploymentタイプ

FSx for Lustreには、一時ストレージと永続ストレージがあります。

- **SCRATCH_1 / SCRATCH_2**: データレプリケーションを行わない一時ストレージです。ファイルサーバーに障害が発生しても置き換えられず、影響を受けたデータが失われる可能性があります。SCRATCH_2でも、そのデータは自動的に復旧しません。
- **PERSISTENT_1 / PERSISTENT_2**: コンポーネントの自動交換に対応したレプリケーションストレージです。サポートされるストレージクラス、容量の増分、スループットオプション、リージョンはDeploymentタイプによって異なります。

Scratchのベースラインは200 MBps/TiBで、最大6倍までバーストできます。`PerUnitStorageThroughput`は永続SSD/HDD構成向けであり、SCRATCH_2向けではありません。永続SSDのオプションは、PERSISTENT_1では50/100/200 MBps/TiB、PERSISTENT_2では125/250/500/1000 MBps/TiBです。Intelligent-Tieringでは異なる容量/スループット構成が使用されます。サイズを選ぶ前に、[Deploymentの仕様](https://docs.aws.amazon.com/fsx/latest/LustreGuide/using-fsx-lustre.html)とAPIを確認してください。

### vLLMワークロード向けFSx for Lustreの設定

vLLM（LLMの推論・サービングエンジン）のような大規模AIモデルのワークロードには、高スループットかつ低レイテンシーのストレージが必要です。FSx for Lustreは、これらの要件を満たす理想的なソリューションです。

#### vLLM向けFSx for Lustre Storage Class

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre-vllm
provisioner: fsx.csi.aws.com
parameters:
  subnetId: subnet-0eabfaa81fb22bcaf
  securityGroupIds: sg-068000ccf82dfba88
  deploymentType: PERSISTENT_1
  perUnitStorageThroughput: "200"
  dataCompressionType: "NONE"
reclaimPolicy: Retain
volumeBindingMode: Immediate
```

FSx CSI driverは、`storageCapacity`というStorageClassパラメーターではなく、PVCの要求から容量を算出します。サブネットIDとセキュリティグループIDを置き換え、互換性のあるLustreクライアント/CSI driverをインストールし、要求容量が選択したDeploymentタイプで有効であることを確認してください。以下の推論イメージは、モデルサービングのコマンドを提供する必要があるプレースホルダーです。

#### vLLMワークロード用PVC

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vllm-model-storage
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 4800Gi
  storageClassName: fsx-lustre-vllm
```

#### vLLM Deploymentの例

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-inference
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm-inference
  template:
    metadata:
      labels:
        app: vllm-inference
    spec:
      nodeSelector:
        node.kubernetes.io/instance-type: g5.12xlarge
      containers:
      - name: vllm
        image: vllm-inference:latest
        resources:
          limits:
            nvidia.com/gpu: 4
          requests:
            nvidia.com/gpu: 4
            memory: "64Gi"
            cpu: "32"
        volumeMounts:
        - name: model-storage
          mountPath: /models
      volumes:
      - name: model-storage
        persistentVolumeClaim:
          claimName: vllm-model-storage
```

#### vLLMのパフォーマンス最適化のヒント

1. **適切なスループットの選択**: vLLMワークロードでは、モデルの読み込み時の同時実行数とデータセットへのアクセスを測定したうえで、スループットを選択することを推奨します。

2. **ストレージ容量の最適化**: モデルのサイズとデータセットのサイズを考慮して、十分なストレージ容量を割り当てます。

3. **ネットワークの最適化**: FSx for LustreファイルシステムとEKS Nodeが同じAvailability Zoneにあることを確認します。

4. **インスタンスタイプの選択**: vLLMワークロードのパフォーマンスを最適化するため、GPUインスタンス（例: g5.12xlarge）を使用します。

5. **メモリーの設定**: モデルのサイズに基づいて十分なメモリーを割り当てます。

6. **ファイルシステムのマウントオプション**: パフォーマンスを最適化するため、適切なマウントオプションを使用します。

   ```bash
   mount -t lustre -o noatime,flock fs-1234abcd.fsx.us-west-2.amazonaws.com@tcp:/fsx /mnt/fsx
   ```

### ストレージオプションの比較

| ストレージオプション | アクセスモード | 用途 | パフォーマンス | コスト | スケーラビリティ |
|---------------|-------------|----------|-------------|------|-------------|
| Amazon EBS | ReadWriteOnce | 1つのNodeにマウントするブロックストレージ | 中～高 | 中 | 限定的（単一Node） |
| Amazon EFS | ReadWriteMany | 複数のPodで共有するファイルストレージ | 中 | 中～高 | 高（複数Node） |
| Amazon FSx for Lustre | ReadWriteMany | HPC、ML、分析 | 非常に高い | 高 | 非常に高い（並列アクセス） |

### EKSストレージ選択ガイド

1. **1つのNodeにマウントするブロックストレージが必要な場合**: Amazon EBS
   - データベース
   - ステートフルアプリケーション
   - 単一Node上で実行するワークロード

2. **複数のPodで共有するファイルストレージが必要な場合**: Amazon EFS
   - Webサーバーのコンテンツ
   - 共有設定ファイル
   - 中規模のデータ処理

3. **高性能なファイルストレージが必要な場合**: Amazon FSx for Lustre
   - 大規模なデータ処理
   - 機械学習およびAIワークロード（vLLMなど）
   - 高性能コンピューティング（HPC）
   - ビッグデータ分析

## まとめ

この章では、Kubernetesのストレージに関する概念を学びました。VolumesはPod内のコンテナがデータを保存・共有する手段を提供し、Persistent VolumesとPersistent Volume ClaimsはPodとは独立したライフサイクルを持つストレージを提供します。Storage Classesを使うと、Dynamic Provisioningを通じて必要なときにストレージを要求できます。

EKSでは、Amazon EBS、Amazon EFS、Amazon FSx for Lustreなど、用途やパフォーマンス特性の異なるさまざまなストレージオプションを利用できます。vLLMのような大規模AIモデルのワークロードには、高スループットかつ低レイテンシーのFSx for Lustreが理想的な選択肢です。FSx for Lustreは複数のNodeから同時にデータへアクセスできる並列ファイルシステムであり、大規模なモデルの学習や推論タスクに適しています。

アプリケーションの要件に合ったストレージオプションを選ぶことが重要です。1つのNodeにマウントするブロックストレージが必要な場合はAmazon EBS、複数のPodで共有するファイルストレージが必要な場合はAmazon EFS、高性能なファイルストレージが必要な場合はAmazon FSx for Lustreを選択してください。

次の章では、Kubernetesの設定とSecretsについて学びます。

## クイズ

この章で学んだ内容を確認するには、[ストレージクイズ](../quizzes/core/04-storage-quiz.md)に挑戦してください。

## 参考資料

- [Kubernetes公式ドキュメント - Volumes](https://kubernetes.io/docs/concepts/storage/volumes/)
- [Kubernetes公式ドキュメント - Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [Kubernetes公式ドキュメント - Storage Classes](https://kubernetes.io/docs/concepts/storage/storage-classes/)
- [Kubernetes公式ドキュメント - Volume Snapshots](https://kubernetes.io/docs/concepts/storage/volume-snapshots/)
- [AWS EBS CSI Driver](https://github.com/kubernetes-sigs/aws-ebs-csi-driver)
- [AWS EFS CSI Driver](https://github.com/kubernetes-sigs/aws-efs-csi-driver)
- [AWS FSx for Lustre CSI Driver](https://github.com/kubernetes-sigs/aws-fsx-csi-driver)
- [AWSブログ - LLM推論ワークロードのスケーリング: Amazon EKS上でTensorRT-LLMとTritonを使用したマルチノードDeployment](https://aws.amazon.com/ko/blogs/hpc/scaling-your-llm-inference-workloads-multi-node-deployment-with-tensorrt-llm-and-triton-on-amazon-eks/)
- [AWS Workshop - GenAI FSx EKS](https://catalog.workshops.aws/genaifsxeks/en-US/200-module2-genai/210-deploy)
