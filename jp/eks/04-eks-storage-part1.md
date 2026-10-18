# EKS ストレージ

> **最終更新日**: 2026年9月28日

Amazon EKS でアプリケーションを実行する際は、データを保存・管理するためにさまざまなストレージを選択できます。このページでは、EKS のストレージに関する基本概念と、Amazon EBS（Elastic Block Store）および Amazon EFS（Elastic File System）の利用方法を説明します。

## 目次

1. [Kubernetes ストレージの基本概念](04-eks-storage-part1.md#kubernetes-storage-basic-concepts)
2. [Amazon EKS のストレージオプション](04-eks-storage-part1.md#amazon-eks-storage-options-overview)
3. [Amazon EBS を使用したストレージ](04-eks-storage-part1.md#storage-with-amazon-ebs)
4. [Amazon EFS を使用したストレージ](04-eks-storage-part1.md#storage-with-amazon-efs)
5. [StorageClass と動的プロビジョニング](04-eks-storage-part1.md#storage-classes-and-dynamic-provisioning)

## Kubernetes ストレージの基本概念 {#kubernetes-storage-basic-concepts}

まず、Kubernetes でストレージを管理する際の主な概念を確認します。

![コンテナから PVC、StorageClass、PV を経由して EBS、EFS、FSx、S3 のバックエンドに至る Kubernetes ストレージ概念図。](../.gitbook/assets/en-eks-04-eks-storage-part1-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part1-0.html)

### Volume

Volume は、ファイルシステムとしてのマウント、または対応している場合は raw block デバイスとして、コンテナにストレージを提供します。ライフタイムは Volume の種類によって異なります。`emptyDir` はコンテナの再起動後も残りますが、Pod とともに削除されます。一方、PVC によって利用する永続 Volume は別途管理されるライフサイクルを持ちます。Pod を削除しても、基盤データが必ず削除されるわけではありません。

### Persistent Volume (PV)

Persistent Volume は、管理者がプロビジョニングするか、StorageClass を通じて動的にプロビジョニングするクラスターのストレージです。PV オブジェクトは Pod から独立していますが、データの保持は PVC の所有関係と reclaim policy によって決まります。たとえば、汎用的な ephemeral volume の PVC は、所有する Pod とともにガベージコレクションされることがあります。

### Persistent Volume Claim (PVC)

Persistent Volume Claim は、ユーザーによるストレージ要求です。PVC は容量とアクセスモードを指定してストレージを要求し、その要求は適切な PV にバインドされます。

PVC は名前空間に属し、通常は1つの PV にバインドされます。アクセスモードとバックエンドが許せば、同じ名前空間の複数の Pod がその Claim を使用できます。バインドしただけでは、アプリケーションレベルのファイル権限が付与されるわけでも、必要な容量や性能が確保されるわけでもありません。

### StorageClass

StorageClass は、管理者が提供するストレージの「クラス」を記述します。StorageClass を使うと、PVC の作成時に PV を動的にプロビジョニングできます。

### アクセスモード

Kubernetes は次のアクセスモードをサポートしています。

* **ReadWriteOnce (RWO)**: 1つのノードから読み書き可能な状態でマウントできます。
* **ReadOnlyMany (ROX)**: 複数のノードから読み取り専用でマウントできます。
* **ReadWriteMany (RWX)**: 複数のノードから読み書き可能な状態でマウントできます。
* **ReadWriteOncePod (RWOP)**: 対応する CSI スタックでは、クラスター全体で1つの Pod だけが読み書きできます。1.22 で導入され、1.29 で安定版になりました。

**RWO は「1つのノード」であり、「1つの Pod」ではありません**。同じノード上の複数の Pod が PVC を共有できます。RWOP は別の制約であり、対応する CSI サイドカーが必要です。他のアクセスモードは主にマッチングやマウント機能の判定に使われます。必要に応じて読み取り専用のマウントフラグ、ファイルシステム権限、サービス認可を使用してください。RWX であっても、複数プロセスによる書き込みがアプリケーション上安全になるわけではありません。

## Amazon EKS のストレージオプション {#amazon-eks-storage-options-overview}

Amazon EKS では、さまざまな AWS ストレージサービスを活用して、コンテナ化されたアプリケーションにストレージを提供できます。

![EBS、EFS、FSx for Lustre と、各 CSI Driver および対応するアクセスモードを比較する EKS ストレージオプション図。](../.gitbook/assets/en-eks-04-eks-storage-part1-1.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part1-1.html)

### 主なストレージオプション

1. **Amazon EBS (Elastic Block Store)**
   * AZ 単位のネットワークブロックストレージです。通常の gp3 ファイルシステム Volume は1ノードにアタッチして使用します（RWO、または互換性のある RWOP）。
   * 高性能で耐久性のあるブロックストレージです。
   * データベースやステートフルアプリケーションに適しています。
2. **Amazon EFS (Elastic File System)**
   * フルマネージド NFS ファイルシステムです。
   * 複数ノードから同時にマウントできます（RWX）。
   * 共有ファイルシステムが必要なワークロードに適しています。
3. **Amazon FSx for Lustre**
   * 高性能ファイルシステムです。
   * 機械学習、HPC、ビッグデータ分析に適しています。
   * 複数ノードから同時にマウントできます（RWX）。
4. **Amazon S3 (Simple Storage Service)**
   * オブジェクトストレージです。
   * S3 API、または公式の Mountpoint for Amazon S3 CSI Driver からアクセスできます（静的なバケットと限定的な POSIX インターフェイス）。S3 Files は EFS CSI 3.0 以降を使う別個の共有ファイルシステムオプションです。
   * 大規模なデータ保存に適しています。
5. **EC2 Instance Store (Local NVMe)**
   * EC2 インスタンスに物理的に接続された一時的なローカル NVMe ストレージで、レイテンシーが非常に低いのが特長です。
   * EC2 Instance Store CSI Driver は2026年5月5日に EKS アドオンとなりました。ローカル NVMe ストレージを Kubernetes PV として管理しますが、PV オブジェクトを作成しても、ノードの喪失や終了を越えて Instance Store のデータが保持されるわけではありません。インストール前にインスタンス、OS、アドオンの互換性を確認してください。
   * AI/ML の一時データ処理、Spark/Hadoop のローカルキャッシュ、高スループットのログ処理、データベースのキャッシュ層に適しています。
   * コスト面では、対応する EC2 インスタンスと関連 AWS リソースを計画してください。ローカルストレージは選択したインスタンスにひも付きます（[出典](https://aws.amazon.com/about-aws/whats-new/2026/05/ec2-csi-eks/)）。

### ストレージオプションの比較

性能は、容量、スループット/IOPS モード、クライアントやネットワークの上限、ワークロードに左右されます。以下は機能の比較であり、測定値による順位付けではありません。

| オプション | インターフェイス | 典型的な用途 | 主な制約 |
|---|---|---|---|
| EBS | ブロック/ファイルシステム | データベース、レプリカごとの状態 | 通常の Volume は1つの AZ に限定され、アタッチと整合性のルールが適用されます。 |
| EFS | 共有 NFS ファイルシステム | 共有ファイル | Regional と One Zone で特性が異なり、スループット、POSIX ID、マウントターゲットへの経路にも違いがあります。 |
| FSx for Lustre | 並列ファイルシステム | HPC/ML のデータセット | クライアント/カーネルの対応、デプロイタイプ、容量、プロビジョニング済みスループットを確認する必要があります。 |
| S3 + Mountpoint CSI | オブジェクト/ファイルインターフェイス | 大規模なオブジェクトデータセット | バケットは静的にプロビジョニングします。すべての POSIX 操作に対応するわけではありません。 |
| S3 Files + EFS CSI | S3 を基盤とする共有ファイルシステム | S3 データへのファイルベースアクセス | サービスと IAM の設定が別途必要です。EFS CSI 3.0 以降が必要で、コンピューティング環境にも制約があります。 |
| EC2 Instance Store CSI | ローカルブロック/ファイルシステム | 再構築可能なキャッシュ/スクラッチ領域 | データの存続期間はノードとローカルメディアに依存します。 |

[Mountpoint CSI](https://docs.aws.amazon.com/eks/latest/userguide/s3-csi.html) と [S3 Files](https://docs.aws.amazon.com/eks/latest/userguide/s3files-csi.html) では、セマンティクスと Controller/Node の IAM 要件が異なります。どちらも、トランザクション処理を行うデータベースのファイルシステムをそのまま置き換えるものではありません。

## Amazon EBS を使用したストレージ {#storage-with-amazon-ebs}

Amazon EBS は、EC2 インスタンスにアタッチできるブロックレベルの Volume を提供します。EKS では、EBS CSI (Container Storage Interface) Driver を介して EBS Volume を Kubernetes Pod にマウントできます。

<!-- Diagram repair pending: controller attach versus node mount path; see batch report.
![2つのノード上の Pod が、それぞれのノード上の CSI Driver を介して別個の EBS Volume をアタッチする EBS CSI アーキテクチャ図。](../.gitbook/assets/en-eks-04-eks-storage-part1-2.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part1-2.html)
-->

### EBS CSI Driver のインストール

通常の Linux EC2 ノードでは、インフラストラクチャの管理者を通じて互換性のある EBS CSI アドオンをインストールします。Auto Mode は `ebs.csi.eks.amazonaws.com` でブロックストレージを管理しますが、標準の `ebs.csi.aws.com` Volume とは Provisioner が異なります。バインド済み PVC や Driver をインプレースで書き換えて移行することはできません。既存の EBS Volume を再利用する場合は、テスト済みのバックアップ/スナップショット復元計画を使うか、[AWS の最新の移行ガイドにある、ワークロード停止、Retain、静的 PV/PVC 再作成の手順](https://docs.aws.amazon.com/eks/latest/userguide/migrate-auto.html)に従ってください。書き込みを再開する前に、バックアップからの復旧、Volume/AZ/KMS の所有関係、IAM/タグ権限、reclaim policy、finalizer、新しいバインドを検証します。EBS は Fargate Pod や Hybrid Nodes にはマウントできません。EBS Controller は Fargate で実行できますが、Node Plugin は実行できません。これは別のデプロイ/ID 設計です。

以下の共通手順は EBS または EFS に対応しています。この節では `CSI_ADDON_NAME=aws-ebs-csi-driver` を設定し、アドオンのカタログを確認して、互換性のあるバージョンを正確に指定してください。AWS API では、文字列 `latest` はアドオンのバージョンとして使えません。`eksctl --version latest` は別のツールが提供する利便機能です。
```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
: "${CSI_ADDON_NAME:?Use aws-ebs-csi-driver or aws-efs-csi-driver}"
case "$CSI_ADDON_NAME" in
  aws-ebs-csi-driver|aws-efs-csi-driver) ;;
  *) echo "Unexpected add-on"; exit 1 ;;
esac
KUBERNETES_VERSION=$(aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query cluster.version --output text)
CLUSTER_ENDPOINT=$(aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query cluster.endpoint --output text)
CURRENT_ENDPOINT=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
test "$CURRENT_ENDPOINT" = "$CLUSTER_ENDPOINT" || { echo "kubeconfig points to another cluster"; exit 1; }
aws eks describe-addon-versions --region "$AWS_REGION" --addon-name "$CSI_ADDON_NAME" \
  --kubernetes-version "$KUBERNETES_VERSION" --output json > csi-addon-versions.json
aws eks list-addons --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" --output json
```
インストール前に、対応するコンピューティング環境の Pod Identity Agent と、`kube-system/ebs-csi-controller-sa` 用の正確な Pod Identity ロール/信頼関係を準備してください。`AmazonEBSCSIDriverPolicyV2` または範囲を限定したポリシー、および必要なカスタマー管理キーの KMS 権限を確認します。IRSA を使う場合は、適切に範囲を限定した OIDC 信頼と `--service-account-role-arn` を使用します。ID の方式を確認せずに併用しないでください。コードは既存インストールを検出すると停止します。既存のインストールを上書きせず、その所有者の更新/引き継ぎ手順を使ってください。
```bash
set -euo pipefail
: "${CSI_ADDON_VERSION:?Choose a reviewed compatible version from csi-addon-versions.json}"
: "${CSI_ROLE_ARN:?Set the prepared Pod Identity role ARN}"
: "${CLUSTER_NAME:?Run the inspection step first}"
: "${AWS_REGION:?Run the inspection step first}"
: "${CSI_ADDON_NAME:?Run the inspection step first}"
case "$CSI_ADDON_NAME" in
  aws-ebs-csi-driver) CSI_SA=ebs-csi-controller-sa; CSI_PREFIX=ebs-csi ;;
  aws-efs-csi-driver) CSI_SA=efs-csi-controller-sa; CSI_PREFIX=efs-csi ;;
  *) echo "Unexpected add-on"; exit 1 ;;
esac
python3 - "$CSI_ADDON_NAME" "$CSI_ADDON_VERSION" <<'PY'
import json, sys
with open("csi-addon-versions.json") as stream:
    catalog = json.load(stream)
versions = [v["addonVersion"] for a in catalog["addons"]
            if a["addonName"] == sys.argv[1] for v in a["addonVersions"]]
if sys.argv[2] not in versions:
    raise SystemExit("Version not present in the inspected compatible catalog")
PY
aws eks list-addons --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --output json > csi-existing-addons.json
python3 - "$CSI_ADDON_NAME" <<'PY'
import json, sys
with open("csi-existing-addons.json") as stream:
    names = json.load(stream)["addons"]
if sys.argv[1] in names:
    raise SystemExit("Existing add-on: use its owner's update procedure")
PY
EXISTING_CSI=$(kubectl -n kube-system get "deployment/$CSI_PREFIX-controller" \
  "daemonset/$CSI_PREFIX-node" --ignore-not-found -o name)
test -z "$EXISTING_CSI" || { echo "Existing CSI installation: review its owner"; exit 1; }
aws eks describe-addon-configuration --region "$AWS_REGION" \
  --addon-name "$CSI_ADDON_NAME" --addon-version "$CSI_ADDON_VERSION"
aws eks create-addon --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --addon-name "$CSI_ADDON_NAME" --addon-version "$CSI_ADDON_VERSION" \
  --pod-identity-associations "serviceAccount=$CSI_SA,roleArn=$CSI_ROLE_ARN" \
  --resolve-conflicts NONE
aws eks wait addon-active --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --addon-name "$CSI_ADDON_NAME"
```
アドオンが Active であっても、アプリケーションから Volume のアタッチ、マウント、書き込み、復元ができることの証明にはなりません。専用の環境でこれらの操作を検証してください。この章の AWS コマンドを実行するとリソースが作成されますが、今回の監査で実施したのはローカルチェックのみです。

### EBS StorageClass の作成

EBS Volume を動的にプロビジョニングする StorageClass を作成します。ここでは gp3 Volume タイプを使用します。

この章の名前空間付きサンプルでは、同じ `storage-demo` 名前空間を使います。演習専用に新しい名前空間を作成してください。すでに存在する場合は、所有者を確認するまで作成を中止します。StorageClass と SnapshotClass はクラスター範囲のリソースなので、これらについても所有者を確認してください。以下のバージョンは例であり、本番環境向けのサイズ指定ではありません。
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: storage-demo
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
```
作成コマンドを実行する**前に**、名前空間のマニフェストを `storage-demo-namespace.yaml` として保存してください。データの保持方針を意識してください。以下の例では `Retain` を使うため、PVC を削除しても課金対象の AWS リソースが残ることがあります。
```bash
kubectl create -f storage-demo-namespace.yaml
```


```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: gp3
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
```

### Persistent Volume Claim (PVC) の作成

アプリケーションで使用する PVC を作成します。

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-claim
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 10Gi
```

### Pod で PVC を使用する

作成した PVC を Pod にマウントします。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-ebs
  namespace: storage-demo
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: busybox:1.38.0
    command:
    - sh
    - -c
    args:
    - test -w /data && touch /data/demo-marker && sync && sleep 3600
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    resources:
      requests:
        cpu: 10m
        memory: 16Mi
      limits:
        cpu: 100m
        memory: 64Mi
    volumeMounts:
    - name: data
      mountPath: /data
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: ebs-claim
```

### EBS Volume スナップショット

これらのリソースを使う前に、Snapshot CRD、互換性のある Snapshot Controller、Driver の Snapshotter コンポーネントを準備してください。管理者が管理するバージョン、またはレビュー済みの固定リリースを使い、`master` を指す可変のマニフェストは使わないでください。VolumeSnapshotClass の Driver は Volume の Provisioner と一致させます。スナップショットは特定時点のブロックコピーです。整合性が必要な場合は、アプリケーションを静止/フラッシュするか、対応するバックアップ手順を使ってください。
```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: ebs-snapshot-retain
driver: ebs.csi.aws.com
deletionPolicy: Retain
```

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: ebs-snapshot
  namespace: storage-demo
  labels:
    storage-demo: ebs
spec:
  volumeSnapshotClassName: ebs-snapshot-retain
  source:
    persistentVolumeClaimName: ebs-claim
```

```bash
set -euo pipefail
kubectl -n storage-demo wait --for=jsonpath='{.status.readyToUse}'=true \
  volumesnapshot/ebs-snapshot --timeout=300s
kubectl -n storage-demo get volumesnapshot ebs-snapshot -o yaml
```
復元するには、スナップショットと同じ名前空間に `status.restoreSize` 以上のサイズで新しい PVC を作成し、使用する Pod を作成して、復元データを確認します。この例の 20 Gi 要求量は、スナップショットがそれ以下のサイズであることを前提としています。`WaitForFirstConsumer` の場合、スケジューリングまで復元 PVC が Pending のままでも正常です。スナップショットの `deletionPolicy` と PV の `reclaimPolicy` は別の設定です。Retain を指定すると、バックエンドのスナップショットは管理者が整理するまで保持されます。
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-restored
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 20Gi
  dataSource:
    name: ebs-snapshot
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
```


### EBS Volume の拡張

StorageClass で拡張が許可され、Driver とファイルシステムが対応している必要があります。この 10 Gi の例では、所有者を通じて PVC の要求量だけを 20 Gi に増やしてください。縮小したり、サイズ変更を装うために PV の容量を手動で変更したりしないでください。PVC の状態/容量とマウント済みファイルシステムを検証します。`FileSystemResizePending` の場合、ドキュメントに記載された再マウント/再起動手順が必要なことがあります。
```bash
set -euo pipefail
kubectl -n storage-demo get pvc ebs-claim -o yaml
kubectl -n storage-demo patch pvc ebs-claim --type merge \
  -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
kubectl -n storage-demo describe pvc ebs-claim
```

### EBS Volume タイプとパフォーマンス

Amazon EBS には、さまざまな Volume タイプがあります。

| Volume タイプ | 説明 | ユースケース |
| ----------- | ------------------------ | ------------------------------------------- |
| gp3 | 汎用 SSD | 費用対効果が高く、ほとんどのワークロードに適しています。 |
| io2 | Provisioned IOPS SSD | 高性能データベース |
| st1 | スループット最適化 HDD | ビッグデータ、ログ処理 |
| sc1 | コールド HDD | アクセス頻度の低いデータ |

gp3 は一般的な出発点ですが、ワークロードとインスタンスの EBS 上限に合わせて容量、IOPS、スループットを選択してください。通常の gp3 ファイルシステム Volume は、複数ノードで共有するファイルシステムではありません。EBS CSI 1.66.0 には、`ReadWriteMany` 用の io2 **raw block** Multi-Attach 経路があります。互換性のあるノードと、アプリケーションレベルの調整/フェンシングが必要です。ext4/XFS を複数箇所から独立してマウントしても安全になるわけではありません。RWOP は RWO と別の機能であり、CSI サイドカーとの互換性も重要です。

## Amazon EFS を使用したストレージ {#storage-with-amazon-efs}

Amazon EFS は、複数の EC2 インスタンスから同時にアクセスできるフルマネージド NFS ファイルシステムです。EKS では、EFS CSI Driver を介して複数の Pod から EFS ファイルシステムを同時にマウントできます。

![複数ノード上の Pod が、CSI Driver を介して NFS 4.1 で1つの EFS ファイルシステムを共有する EFS CSI アーキテクチャ図。](../.gitbook/assets/en-eks-04-eks-storage-part1-3.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part1-3.html)

### EFS CSI Driver のインストール

対応する Linux EC2 コンピューティング環境では、前述のアドオン手順を使い、`CSI_ADDON_NAME=aws-efs-csi-driver` と互換性のある EFS アドオンバージョン、および `kube-system/efs-csi-controller-sa` 用のロールを準備してください。`AmazonEFSCSIDriverPolicy` または範囲を限定した同等のポリシーを確認します。Fargate はマネージド統合を通じて EFS をマウントし、動的ではなく静的プロビジョニングをサポートします。マネージド EFS CSI の対応表では Windows/Hybrid Nodes は対象外です。S3 Files は EFS CSI 3.0 以降を使いますが、Controller と Node の両方で別の IAM 要件があり、Fargate にも対応していません。

### 2026年9月の更新: EFS CSI Driver のマウントオプション注入 (CVE-2026-6437)

2026年9月25日、AWS は EFS CSI Driver のマウントオプション注入に関するセキュリティ情報 [CVE-2026-6437](https://aws.amazon.com/security/security-bulletins/2026-016-aws/) を公開しました。PersistentVolume 作成権限を持つ攻撃者は、未サニタイズの2つのフィールド、すなわち `volumeHandle` 内の Access Point ID と `mounttargetip` VolumeAttribute を介して任意のマウントオプションを注入できます。カンマ区切りの値が追加されると、マウントユーティリティーがそれらを個別のマウントオプションとして解釈するためです。EFS CSI Driver **v3.0.0 以前**が影響を受け、**v3.0.1** で修正されています。EKS マネージドアドオンを含め、Driver を v3.0.1 以降に更新してください。また、信頼されていないユーザーが任意のフィールド値を指定できないよう、PersistentVolume と StorageClass の作成権限を Kubernetes RBAC でクラスター管理者に限定してください。

### EFS ファイルシステムの作成

動的な `efs-ap` プロビジョニングは、**既存の**ファイルシステムに Access Point を作成します。ファイルシステムとマウントターゲットは、ネットワーク/ストレージの管理者を通じて用意してください。以下は任意の CLI 例で、暗号化された Regional ファイルシステムを新規作成し、**異なる2つの AZ** にそれぞれ1つずつマウントターゲットを作成します。クライアントが実際に使用するサブネットを選択してください。AZ を追加する場合は、すべてのサブネットではなく、各 AZ に1つのターゲットを追加する設計にします。すでに IaC の管理下にあるファイルシステムなら、この例ではなく既存の管理手順を使ってください。

実行前に、オペレーター権限、正しいリージョン/アカウント、到達可能なクライアント SG、DNS/NFS 経路を準備します。スクリプトは曖昧な Name タグで検索せず、API が返した ID を保存し、書き込みの前に VPC/AZ の選択を検証し、途中で失敗した場合も作成記録を保持します。一意で安定した作成トークンは、この作成要求専用のものを使います。既存トークンに対する応答が返っても、それを理由に別のファイルシステムを引き継いだり変更したりしてはいけません。部分的に作成されたリソースは確認して調整し、安易に再実行しないでください。
```bash
set -euo pipefail
umask 077
: "${CLUSTER_NAME:?Set the cluster name}"
: "${AWS_REGION:?Set the Region}"
: "${EFS_CREATION_TOKEN:?Set a unique, stable token for this new filesystem}"
: "${EFS_SUBNET_A:?Set the first approved subnet}"
: "${EFS_SUBNET_B:?Set a subnet in a different AZ}"
: "${NFS_CLIENT_SG_ID:?Set the SG of the actual NFS clients}"
EFS_SETUP_DIR=$(mktemp -d -t eks-efs-setup.XXXXXX)
printf 'Creation records: %s\n' "$EFS_SETUP_DIR"
VPC_ID=$(aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query cluster.resourcesVpcConfig.vpcId --output text)
aws ec2 describe-subnets --region "$AWS_REGION" \
  --subnet-ids "$EFS_SUBNET_A" "$EFS_SUBNET_B" --output json > "$EFS_SETUP_DIR/subnets.json"
aws ec2 describe-security-groups --region "$AWS_REGION" \
  --group-ids "$NFS_CLIENT_SG_ID" --output json > "$EFS_SETUP_DIR/client-sg.json"
python3 - "$EFS_SETUP_DIR" "$VPC_ID" "$EFS_CREATION_TOKEN" <<'PY'
import json, pathlib, sys
root, vpc, token = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
subnets = json.loads((root / "subnets.json").read_text())["Subnets"]
groups = json.loads((root / "client-sg.json").read_text())["SecurityGroups"]
if not 1 <= len(token) <= 64 or not token.isascii():
    raise SystemExit("Creation token must contain 1–64 ASCII characters")
if len(subnets) != 2 or len({s["SubnetId"] for s in subnets}) != 2:
    raise SystemExit("Exactly two distinct subnets are required")
if any(s["VpcId"] != vpc for s in subnets) or len({s["AvailabilityZoneId"] for s in subnets}) != 2:
    raise SystemExit("Subnets must be in the cluster VPC and different AZs")
if len(groups) != 1 or groups[0]["VpcId"] != vpc:
    raise SystemExit("The NFS client SG must belong to the cluster VPC")
PY
aws efs create-file-system --region "$AWS_REGION" --creation-token "$EFS_CREATION_TOKEN" \
  --performance-mode generalPurpose --throughput-mode elastic --encrypted \
  --tags Key=Name,Value=eks-storage-demo --output json > "$EFS_SETUP_DIR/filesystem-created.json"
EFS_FS_ID=$(python3 - "$EFS_SETUP_DIR/filesystem-created.json" <<'PY'
import json, sys
with open(sys.argv[1]) as stream:
    print(json.load(stream)["FileSystemId"])
PY
)
test -n "$EFS_FS_ID"
FS_READY=false
for ((attempt=0; attempt<60; attempt++)); do
  STATE=$(aws efs describe-file-systems --region "$AWS_REGION" --file-system-id "$EFS_FS_ID" \
    --query 'FileSystems[0].LifeCycleState' --output text)
  case "$STATE" in
    available) FS_READY=true; break ;;
    creating) sleep 5 ;;
    *) echo "Unexpected filesystem state: $STATE"; exit 1 ;;
  esac
done
test "$FS_READY" = true || { echo "Filesystem readiness timed out"; exit 1; }
aws ec2 create-security-group --region "$AWS_REGION" --group-name "efs-nfs-$EFS_FS_ID" \
  --description "NFS clients for $EFS_FS_ID" --vpc-id "$VPC_ID" \
  --output json > "$EFS_SETUP_DIR/sg-created.json"
EFS_SG_ID=$(python3 - "$EFS_SETUP_DIR/sg-created.json" <<'PY'
import json, sys
with open(sys.argv[1]) as stream:
    print(json.load(stream)["GroupId"])
PY
)
test -n "$EFS_SG_ID"
aws ec2 authorize-security-group-ingress --region "$AWS_REGION" --group-id "$EFS_SG_ID" \
  --protocol tcp --port 2049 --source-group "$NFS_CLIENT_SG_ID"
for SUBNET_ID in "$EFS_SUBNET_A" "$EFS_SUBNET_B"; do
  aws efs create-mount-target --region "$AWS_REGION" --file-system-id "$EFS_FS_ID" \
    --subnet-id "$SUBNET_ID" --security-groups "$EFS_SG_ID" --output json \
    > "$EFS_SETUP_DIR/mount-target-$SUBNET_ID.json"
done
TARGETS_READY=false
for ((attempt=0; attempt<60; attempt++)); do
  aws efs describe-mount-targets --region "$AWS_REGION" --file-system-id "$EFS_FS_ID" \
    --output json > "$EFS_SETUP_DIR/mount-targets.json"
  STATE=$(python3 - "$EFS_SETUP_DIR/mount-targets.json" <<'PY'
import json, sys
with open(sys.argv[1]) as stream:
    targets = json.load(stream)["MountTargets"]
states = [t["LifeCycleState"] for t in targets]
if any(s not in ("creating", "available") for s in states):
    raise SystemExit("Unexpected mount-target state")
print("available" if len(states) == 2 and all(s == "available" for s in states) else "creating")
PY
)
  if test "$STATE" = available; then TARGETS_READY=true; break; fi
  sleep 5
done
test "$TARGETS_READY" = true || { echo "Mount-target readiness timed out"; exit 1; }
printf 'Filesystem: %s\nMount-target SG: %s\nCreation records: %s\n' "$EFS_FS_ID" "$EFS_SG_ID" "$EFS_SETUP_DIR"
```
この例では、ライフサイクルが準備できるまで上限付きの Describe ポーリングを行います。Controller の CSI IAM ロールは、一般的なファイルシステム作成用ロールではありません。NFS のインバウンド通信には実際のクライアント SG を使い、選択した設計でマウント通信がノード ENI と Pod ENI のどちらから届くかを確認してください。

### EFS StorageClass の作成

EFS 用の StorageClass を作成します。ファイルシステム ID を取得済みの ID に置き換えてください。この例では Access Point 上の UID/GID を 1000 に固定し、ディレクトリを一意に保ちます。信頼境界に合わせて ID を選択してください。TLS を有効にしています。`iam` マウントオプションで使われるのは **CSI Node Pod の ID** であり、アプリケーションの ServiceAccount が自動的に使われるわけではありません。Controller のプロビジョニング権限とクライアントのマウント権限は別々です。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
reclaimPolicy: Retain
mountOptions:
- tls
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: '750'
  uid: '1000'
  gid: '1000'
  basePath: /storage-demo
  ensureUniqueDirectory: 'true'
```

### Persistent Volume Claim (PVC) の作成

EFS を利用する PVC を作成します。要求量 `5Gi` は Kubernetes のバインド用メタデータであり、EFS のディレクトリクォータや割り当て済み容量ではありません。利用を拡大する場合は、スループット/IOPS、Access Point のクォータ、コストも計画してください。

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: efs-claim
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: efs-sc
  resources:
    requests:
      storage: 5Gi
```

### Pod で EFS PVC を使用する

作成した PVC を Pod にマウントします。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-efs
  namespace: storage-demo
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: busybox:1.38.0
    command:
    - sh
    - -c
    args:
    - test -w /shared-data && touch /shared-data/demo-marker && sync && sleep 3600
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    resources:
      requests:
        cpu: 10m
        memory: 16Mi
      limits:
        cpu: 100m
        memory: 64Mi
    volumeMounts:
    - name: data
      mountPath: /shared-data
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: efs-claim
```

### EFS Access Point

Access Point は、クライアントに提示するルートディレクトリと強制する POSIX ID を設定します。ただし、それだけで完全な名前空間分離が実現するわけではありません。ファイルシステムの IAM ポリシーとネットワーク制御を使って、意図した Access Point、TLS、クライアント権限を強制してください。相互に信頼しないテナントが共有するクラスでは `reuseAccessPoint` を有効にしないでください。レビュー済みの Driver では、再利用トークンに名前空間ではなく PVC 名が使われるため、2つの Claim が同じデータを指す可能性があります。

この静的な例は、`storageClassName: ""` を指定して動的/デフォルトプロビジョニングを使わず、既存の Access Point に PVC を明示的にバインドします。先ほどの動的 Claim に代わる例です。Access Point のルートディレクトリと POSIX 権限は、あらかじめ適切に設定されている必要があります。利用する Pod では、`storage-demo` の `efs-static-claim` を参照してください。
```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: efs-static-pv
spec:
  capacity:
    storage: 5Gi
  volumeMode: Filesystem
  accessModes:
  - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: ''
  mountOptions:
  - tls
  csi:
    driver: efs.csi.aws.com
    volumeHandle: fs-0123456789abcdef0::fsap-0123456789abcdef0
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: efs-static-claim
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: ''
  volumeName: efs-static-pv
  resources:
    requests:
      storage: 5Gi
```


### EFS のパフォーマンスモードとスループットモード

- **General Purpose** は、すべてのファイルシステムに対して AWS が推奨するパフォーマンスモードです。**Max I/O** は旧世代のモードで、操作ごとのレイテンシーが高く、Elastic スループットまたは One Zone ファイルシステムとは併用できません。
- **Elastic** は需要に合わせてスループットを調整し、**Provisioned** は選択したスループットを予約し、**Bursting** は保存データ量/クレジットに応じて動作します。明示的に選択してください。コンソール/API のデフォルトを、すべてに共通する既定値とみなしてはいけません。
- Regional と One Zone では、障害時の特性と可用性が異なります。現在は One Zone でも Elastic スループットを利用できますが、単一 AZ の耐久性に関する考慮事項は変わりません。
- 実際のアクセスパターンとクライアントの上限を測定してください。ここでの説明は、このサンプルのレイテンシー/スループットを測定したものではありません。

## StorageClass と動的プロビジョニング {#storage-classes-and-dynamic-provisioning}

Kubernetes の StorageClass を使用すると、Persistent Volume を動的にプロビジョニングできます。EKS では、AWS のさまざまなストレージサービスに StorageClass を設定できます。

![Pod の PVC 要求から StorageClass と CSI Driver を経て、PV が作成・バインドされるストレージプロビジョニングのワークフロー図。](../.gitbook/assets/en-eks-04-eks-storage-part1-4.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part1-4.html)

### Volume バインディングモード

StorageClass の `volumeBindingMode` フィールドは、PVC 作成時に PV をどのようにバインドするかを決めます。

* **Immediate**: PVC 作成時に直ちに PV をプロビジョニングしてバインドします。
* **WaitForFirstConsumer**: Pod が PVC を使おうとするまで PV のプロビジョニングを遅らせます。

通常の AZ 範囲の EBS Volume では、スケジューラーの制約をプロビジョニング/バインドに反映できるよう `WaitForFirstConsumer` を優先してください。EBS はネットワーク接続型のブロックストレージであり、物理的な Instance Store メディアではありません。Driver にある別機能の、事前アタッチ済みノードローカルキャッシュモードとは異なります。遅延バインド中の PVC について、スケジューラーを迂回するために `spec.nodeName` を設定しないでください。代わりに `nodeSelector` などのスケジューラー制約を使います。

### デフォルト StorageClass の設定

PVC で `storageClassName` を省略すると、デフォルトクラスが適用されます。明示的に `storageClassName: ""` とすると適用対象外になります。既存のデフォルトは、その所有者を通じて確認してください。移行中は複数のデフォルトが存在してもかまいませんが、その場合は最も新しく作成されたものが選ばれます。移行後は意図したデフォルトを1つだけ残してください。既存のバインド済み Volume は移行されません。以下に続く各クラスの例はそれぞれ代替案であり、パラメーターを順に変更する手順ではありません。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3
  annotations:
    storageclass.kubernetes.io/is-default-class: 'true'
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: gp3
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
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
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: gp3
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
  iops: '3000'
  throughput: '125'
```

**2. EFS StorageClass**

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-sc
provisioner: efs.csi.aws.com
reclaimPolicy: Retain
mountOptions:
- tls
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: '750'
  uid: '1000'
  gid: '1000'
  basePath: /storage-demo
  ensureUniqueDirectory: 'true'
```

**3. FSx for Lustre StorageClass**

対応する FSx CSI/Controller IAM ロール、Lustre クライアント/カーネル、ネットワーク経路をあらかじめ準備してください。この最小構成の SCRATCH_2 クラスでは、永続データ向けのスループット設定やバックアップ設定を意図的に省いています。破棄可能、または再生成できるデータを使ってください。Retain を指定しても、スクラッチストレージが耐久性のあるバックアップになるわけではありません。CSI 1.10.0 では、選択した FSx デプロイが対応していれば、`s3ImportPath` は有効な任意パラメーターです。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre
provisioner: fsx.csi.aws.com
reclaimPolicy: Retain
parameters:
  subnetId: subnet-0123456789abcdef0
  securityGroupIds: sg-0123456789abcdef0
  deploymentType: SCRATCH_2
  dataCompressionType: NONE
```

### Reclaim Policy

PVC 削除時に PV とデータをどう扱うかは、Persistent Volume の reclaim policy によって決まります。

* **Delete**: Claim の解放/保護処理後、Provisioner が Driver に応じてバックエンドのクリーンアップを試みます。EBS では Volume が削除されます。EFS の動的プロビジョニングでは、通常、デフォルト設定ではファイルシステムやファイルではなく Access Point が削除されます。EFS Controller の `deleteAccessPointRootDir` 設定を変更すると、この動作が変わります。
* **Retain**: PVC を削除しても PV とデータは保持されます。管理者が手動でクリーンアップする必要があります。
* **Recycle**: 非推奨のポリシーです。代わりに動的プロビジョニングと StorageClass を使ってください。

StorageClass で指定するフィールドは **`reclaimPolicy`** です。**`persistentVolumeReclaimPolicy`** は PV の spec に属します。StorageClass が設定するのは、新しくプロビジョニングされる PV の初期ポリシーです。StorageClass を変更しても、既存の PV のポリシーは自動では更新されません。Claim を削除する前に、実際の各 PV とバックアップを確認してください。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3-retain
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: gp3
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
```

公式リファレンス: [EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)、[EFS CSI](https://docs.aws.amazon.com/eks/latest/userguide/efs-csi.html)、[Snapshot Controller](https://docs.aws.amazon.com/eks/latest/userguide/csi-snapshot-controller.html)、[EFS のパフォーマンス](https://docs.aws.amazon.com/efs/latest/ug/performance.html)、[Kubernetes PV](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)。

## まとめ

Amazon EKS では、さまざまなストレージオプションを使って、アプリケーションの要件に合ったストレージを構成できます。このページでは EBS と EFS を中心に、基本概念と設定方法を説明しました。次のページでは FSx for Lustre と S3 を使った高度なストレージ設定を扱います。

## クイズ

この章で学んだ内容を確認するには、[トピッククイズ](../quizzes/eks/04-eks-storage-part1-quiz.md)に挑戦してください。
