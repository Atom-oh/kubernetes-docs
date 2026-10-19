# パート2: ストレージクラス

> **最終更新**: 2026年10月16日

このドキュメントはAmazon EKSストレージシリーズの第2部です。FSx for Lustre、Amazon S3、スナップショット、ボリューム拡張、パフォーマンス最適化を扱います。

## 目次

1. [Amazon FSx for Lustre](04-eks-storage-part2.md#amazon-fsx-for-lustre)
2. [Amazon S3ストレージ統合](04-eks-storage-part2.md#amazon-s3-storage-integration)
3. [スナップショットとバックアップ](04-eks-storage-part2.md#snapshots-and-backups)
4. [ボリューム拡張とリサイズ](04-eks-storage-part2.md#volume-expansion-and-resizing)
5. [ボリュームのクローン](04-eks-storage-part2.md#volume-cloning)
6. [Multi-Attach EBS](04-eks-storage-part2.md#multi-attach-ebs)
7. [Mountpoint for S3 CSIの詳細](04-eks-storage-part2.md#mountpoint-for-s3-csi-deep-dive)
8. [ストレージパフォーマンスの最適化](04-eks-storage-part2.md#storage-performance-optimization)

## Amazon FSx for Lustre

FSx for Lustreは、HPC、機械学習、分析など、サポート対象のワークロード向けの並列ファイルシステムです。性能はデプロイメント／ストレージ種別、容量、プロビジョニング済みスループット、クライアント、ネットワークに左右されます。小規模な例のファイルシステムが、宣伝されている集約最大性能をすべて発揮するわけではありません。

図は任意のS3データリポジトリ統合を示しています。インポート／エクスポートのポリシー、タスク、権限を設定する必要があります。CSIボリュームを作成しただけでは双方向の自動同期は確立されません。

![FSx CSIドライバー経由でFSx for Lustreをマウントする機械学習の学習・推論Podと、FSxからS3への同期を示すアーキテクチャ図。](../.gitbook/assets/en-eks-04-eks-storage-part2-0.png)

[🔍 インタラクティブ図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part2-0.html)

### FSx for Lustre CSIドライバーのインストール

インフラ所有者がサポートするEKSアドオン、または公開済みのHelmリリースを使用してください。以下のマネージドアドオン例では`CSI_ADDON_NAME=aws-fsx-csi-driver`を設定します。`kube-system/fsx-csi-controller-sa`用のロールを準備し、FSxドライバーに必要な権限とPod Identityの信頼設定／エージェントを確認します。IRSAもOIDC信頼と対応するアドオンのロールオプションで利用できます。Pod Identityエージェントが必要なのはその認証方式を使う場合であり、IRSAでは不要です。FargateはFSx CSIのサポート対象ノード環境ではありません。Linuxカーネル／Lustreクライアントと実際のコンピュート環境の対応状況を確認してください。

`eksctl --role-only`で作成するロールはKubernetesのServiceAccountではありません。マネージドアドオンはServiceAccountを作成します。Helmで導入する場合は、実際のアカウントを作成するか参照し、意図したIDを割り当ててください。アカウントを先に準備せずにロールだけ作成し、`serviceAccount.create=false`を指定してはいけません。
```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
: "${CSI_ADDON_NAME:?Use aws-fsx-csi-driver}"
case "$CSI_ADDON_NAME" in
  aws-fsx-csi-driver) ;;
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

```bash
set -euo pipefail
: "${CSI_ADDON_VERSION:?Choose a reviewed compatible version from csi-addon-versions.json}"
: "${CSI_ROLE_ARN:?Set the prepared Pod Identity role ARN}"
: "${CLUSTER_NAME:?Run the inspection step first}"
: "${AWS_REGION:?Run the inspection step first}"
: "${CSI_ADDON_NAME:?Run the inspection step first}"
case "$CSI_ADDON_NAME" in
  aws-fsx-csi-driver) CSI_SA=fsx-csi-controller-sa; CSI_PREFIX=fsx-csi ;;
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

既存のインストールがある場合、この手順はそこで停止し、所有者を通じて移行／更新してください。アドオンがActiveでも、ファイルシステムを正常にマウントできた証明にはなりません。以下の例では第1部専用の`storage-demo`名前空間を再利用し、クラスター全体に適用されるリソース名を確認してから使います。

### FSx for Lustreファイルシステムの作成

**動的プロビジョニングか静的プロビジョニングを選びます**。動的プロビジョニングではPVCからファイルシステムを作成します。動的StorageClassが既存ファイルシステムを引き継ぐと想定して、先に別のファイルシステムを作成しないでください。以下の任意の手動手順は静的プロビジョニング用です。サポート対象AZ内の承認済みサブネットと、必要なクライアント／ファイルシステム通信ルールを設定済みのLustreセキュリティグループを選びます。`Subnets[0]`を選んだり、TCP 988だけでサポートされる設計がすべて完成すると想定したりしないでください。この範囲を限定した例はクラスターと同じVPCを前提とします。接続VPCの設計には別途、ルーティングとセキュリティの確認が必要です。実行すると課金対象リソースが作成され、失敗時にも返却されたIDは保持されます。
```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the existing cluster}"
: "${AWS_REGION:?Set the filesystem Region}"
: "${FSX_SUBNET_ID:?Select an approved subnet in a supported AZ}"
: "${FSX_SECURITY_GROUP_ID:?Set the reviewed Lustre filesystem SG}"
: "${FSX_CREATION_TOKEN:?Set a unique stable token for this new filesystem}"
FSX_SETUP_DIR=$(mktemp -d -t eks-fsx-setup.XXXXXX)
printf 'Creation records: %s\n' "$FSX_SETUP_DIR"
VPC_ID=$(aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query cluster.resourcesVpcConfig.vpcId --output text)
aws ec2 describe-subnets --region "$AWS_REGION" --subnet-ids "$FSX_SUBNET_ID" \
  --output json > "$FSX_SETUP_DIR/subnet.json"
aws ec2 describe-security-groups --region "$AWS_REGION" --group-ids "$FSX_SECURITY_GROUP_ID" \
  --output json > "$FSX_SETUP_DIR/sg.json"
python3 - "$FSX_SETUP_DIR" "$VPC_ID" <<'PY'
import pathlib, json, sys
root, vpc = pathlib.Path(sys.argv[1]), sys.argv[2]
subnets = json.loads((root / "subnet.json").read_text())["Subnets"]
groups = json.loads((root / "sg.json").read_text())["SecurityGroups"]
if len(subnets) != 1 or len(groups) != 1 or subnets[0]["VpcId"] != vpc or groups[0]["VpcId"] != vpc:
    raise SystemExit("This example requires one subnet and SG in the cluster VPC")
PY
aws fsx create-file-system --region "$AWS_REGION" --file-system-type LUSTRE \
  --client-request-token "$FSX_CREATION_TOKEN" --storage-capacity 1200 --storage-type SSD \
  --subnet-ids "$FSX_SUBNET_ID" --security-group-ids "$FSX_SECURITY_GROUP_ID" \
  --lustre-configuration DeploymentType=SCRATCH_2,DataCompressionType=NONE \
  --tags Key=Name,Value=eks-lustre-demo --output json > "$FSX_SETUP_DIR/created.json"
FSX_FILE_SYSTEM_ID=$(python3 - "$FSX_SETUP_DIR/created.json" <<'PY'
import json, sys
with open(sys.argv[1]) as stream:
    print(json.load(stream)["FileSystem"]["FileSystemId"])
PY
)
FSX_READY=false
for ((attempt=0; attempt<60; attempt++)); do
  STATE=$(aws fsx describe-file-systems --region "$AWS_REGION" --file-system-ids "$FSX_FILE_SYSTEM_ID" \
    --query 'FileSystems[0].Lifecycle' --output text)
  case "$STATE" in
    AVAILABLE) FSX_READY=true; break ;;
    CREATING) sleep 10 ;;
    *) echo "Unexpected filesystem state: $STATE"; exit 1 ;;
  esac
done
test "$FSX_READY" = true || { echo "Filesystem creation still pending; inspect recorded ID"; exit 1; }
aws fsx describe-file-systems --region "$AWS_REGION" --file-system-ids "$FSX_FILE_SYSTEM_ID" \
  --query 'FileSystems[0].{Id:FileSystemId,State:Lifecycle,DNS:DNSName,MountName:LustreConfiguration.MountName,CapacityGiB:StorageCapacity}' \
  --output json > "$FSX_SETUP_DIR/available.json"
cat "$FSX_SETUP_DIR/available.json"
```

### FSx for Lustre StorageClassの作成

**動的**な方法では、実際のサブネットとセキュリティグループをStorageClassに設定します。容量はPVCの要求値で決まり、無視される`storageCapacity`クラスパラメーターでは決まりません。SCRATCH_2と、永続型専用の単位あたりスループット／バックアップ設定を組み合わせないでください。返却されたマウント名は静的PVのvolumeAttributesに設定し、`mountName`クラスパラメーターとして指定しません。
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre-sc
provisioner: fsx.csi.aws.com
reclaimPolicy: Retain
parameters:
  subnetId: subnet-0123456789abcdef0
  securityGroupIds: sg-0123456789abcdef0
  deploymentType: SCRATCH_2
  dataCompressionType: NONE
```

### PVCの作成とPodへのマウント

この読み取り専用コンシューマーで検証できるのは、マウントにアクセスできることだけです。GPUワークロードでもスループットベンチマークでもありません。この確認にCUDAイメージは不要です。UID/GID 1000用のファイルシステム権限と実際のクライアントネットワーク経路を準備してください。
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: fsx-claim
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: fsx-lustre-sc
  resources:
    requests:
      storage: 1200Gi
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-fsx
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
    - test -r /data && sleep 3600
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
      readOnly: true
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: fsx-claim
```

### FSx for Lustreをマウントする静的プロビジョニング

既存ファイルシステムの実際のID、DNSName、MountName、容量を使います。これは動的PVCの代替手順です。以下のプレースホルダーを検索結果の値に置き換えてから、予約済みの静的PV/PVCをバインドします。`storageClassName: ""`はデフォルトの動的プロビジョニングを防ぎます。コンシューマーは`fsx-static-claim`を使用します。
```bash
set -euo pipefail
: "${AWS_REGION:?Set the filesystem Region}"
: "${FSX_FILE_SYSTEM_ID:?Set the owned existing filesystem ID}"
aws fsx describe-file-systems --region "$AWS_REGION" --file-system-ids "$FSX_FILE_SYSTEM_ID" \
  --query 'FileSystems[0].{Id:FileSystemId,State:Lifecycle,DNS:DNSName,MountName:LustreConfiguration.MountName,CapacityGiB:StorageCapacity}' \
  --output json
```

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: fsx-lustre-static
spec:
  capacity:
    storage: 1200Gi
  volumeMode: Filesystem
  accessModes:
  - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: ''
  claimRef:
    namespace: storage-demo
    name: fsx-static-claim
  csi:
    driver: fsx.csi.aws.com
    volumeHandle: fs-0123456789abcdef0
    volumeAttributes:
      dnsname: replace-with-filesystem-dns.example.internal
      mountname: replace-with-mountname
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: fsx-static-claim
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: ''
  volumeName: fsx-lustre-static
  resources:
    requests:
      storage: 1200Gi
```

### FSx for Lustreのデプロイメント種別

- **SCRATCH_1／SCRATCH_2**は、一時的で再作成可能なデータ向けです。PVとしてマウントしただけでScratchに永続的なレプリケーション／復旧機能が備わるわけではありません。SCRATCH_2ではバースト／性能特性と暗号化の条件が異なります。
- **PERSISTENT_1／PERSISTENT_2**は、ストレージ、スループット、レイテンシーの特性が異なる永続型の選択肢です。PERSISTENT_2はすべてのリージョン／AZ構成で利用できるわけではありません。
- スループットの値は選択したデプロイメント／ストレージ種別に合わせます。PERSISTENT_2 SSDは125／250／500／1000 MB/s/TiBの選択肢をサポートしますが、他の組み合わせでは異なります。RetainはKubernetesのライフサイクルポリシーであり、Scratchストレージのデータ耐久性を高めるものではありません。

### vLLM向けFSx for Lustreの設定

vLLMはLLM推論／サービングのプロジェクトであり、「Vector Language Model」ではありません。以下はモデルファイル向けストレージ割り当ての例で、最適化済みまたは測定済みのvLLMデプロイではありません。モデルのロードは、ファイル形式、CPUによるデシリアライズ、キャッシュ状態、GPU初期化にも左右されます。すでに圧縮されたデータでは、さらに圧縮するとオーバーヘッドが増える場合があります。実測してください。
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre-vllm
provisioner: fsx.csi.aws.com
reclaimPolicy: Retain
parameters:
  subnetId: subnet-0123456789abcdef0
  securityGroupIds: sg-0123456789abcdef0
  deploymentType: PERSISTENT_2
  dataCompressionType: LZ4
  perUnitStorageThroughput: '1000'
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vllm-models
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: fsx-lustre-vllm
  resources:
    requests:
      storage: 4800Gi
```

## Amazon S3ストレージ統合 {#amazon-s3-storage-integration}

S3はオブジェクトストレージです。アプリケーションからAPIを直接利用でき、HadoopではS3Aを使えます。またMountpoint CSIでは既存バケットを、文書化された制限のあるファイルシステムインターフェイスとして公開できます。これらは相互に置き換え可能なPOSIXファイルシステムではありません。第1部で扱ったS3 Filesは別の統合方式であり、独自のEFS CSI要件があります。

![S3統合方式の図。アプリケーションPodはIRSAで認証情報を取得し、Mountpoint S3 CSIドライバーまたはAWS SDKを使ってS3にアクセスします。](../.gitbook/assets/en-eks-04-eks-storage-part2-1.png)

[🔍 インタラクティブ図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part2-1.html)

### Pod IdentityまたはIRSAを使ったS3アクセス

第1部専用の`storage-demo`名前空間を再利用します。既存のバケット、リージョン、対象バケット／プレフィックスに限定したIAMロールを準備してください。この例のポリシーは1つのバケットの一覧取得を許可し、読み取り対象を`training/`のみに限定します。書き込み権限は付与しません。SSE-KMSオブジェクトには適切なキーポリシーと、範囲を限定したKMS復号権限も必要です。バケットポリシー、エンドポイント、クロスアカウント信頼によって、さらに制限される場合があります。
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListOneBucket",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::replace-with-owned-data-bucket"
    },
    {
      "Sid": "ReadTrainingPrefix",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::replace-with-owned-data-bucket/training/*"
    }
  ]
}
```

以下のServiceAccountは**IRSA**の例です。プレースホルダーARNを、OIDC信頼がこのクラスター、`system:serviceaccount:storage-demo:s3-access-sa`、STS audienceだけを許可するよう準備したロールのARNに置き換えます。アノテーションだけでロールや信頼関係が作成されるわけではありません。**EKS Pod Identity**の場合はIRSAアノテーションを省略し、サポート対象エージェントを用意したうえで、このアプリケーションアカウント用の信頼関係を確認済みのAssociationを作成します。意図しないフォールバックとして両方を設定しないでください。マニフェストに静的AWSキーを含めないでください。
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-access-sa
  namespace: storage-demo
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::111122223333:role/storage-demo-s3-reader
```

### S3アクセス用のPod設定

この範囲を限定した読み取り専用の一覧取得Jobは、公式AWS CLIイメージと準備済みアカウントを使います。使用前にバケットとリージョンを置き換えてください。非特権CLIプロセスのため、書き込み可能な専用ディレクトリを使います。終了コードだけでは、アプリケーションが意図したすべてのオブジェクトを読める証明になりません。Jobとログを確認し、認可対象の代表的なオブジェクトを別途読み取ってください。
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: s3-read-check
  namespace: storage-demo
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 120
  template:
    spec:
      serviceAccountName: s3-access-sa
      restartPolicy: Never
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: reader
        image: public.ecr.aws/aws-cli/aws-cli:2.36.43
        command:
        - aws
        args:
        - s3api
        - list-objects-v2
        - --bucket
        - replace-with-owned-data-bucket
        - --prefix
        - training/
        - --max-items
        - '5'
        env:
        - name: AWS_REGION
          value: us-west-2
        - name: AWS_EC2_METADATA_DISABLED
          value: 'true'
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
        volumeMounts:
        - name: private-home
          mountPath: /root
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: private-home
        emptyDir: {}
      - name: tmp
        emptyDir: {}
```

### Hadoop S3Aアクセス

S3AはHadoopの`s3a://`ファイルシステム実装であり、Kubernetesのボリュームマウントではありません。Hadoop 3.5.0はAWS SDK for Java v2を使います。互換性のある`hadoop-common`／`hadoop-aws`のバージョンと、対応するshaded SDK bundleを含むイメージを構築してレビューしてください。以下のプレースホルダーは公開済みのすぐ使えるイメージではありません。イメージでは`hadoop`がPATH上にあり、`/opt/hadoop/etc/hadoop`を使え、UID 1000をサポートする必要があります。`hadoop-aws`は、必要な他のオプショナルツールと合わせて組み込みます。v2のデフォルト認証情報プロバイダーは、同梱SDKが対応していれば選択したワークロードIDを使えます。v1用の`com.amazonaws`プロバイダークラスを再利用しないでください。
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: hadoop-s3a-config
  namespace: storage-demo
data:
  core-site.xml: |
    <?xml version="1.0" encoding="UTF-8"?>
    <configuration>
      <property>
        <name>fs.s3a.aws.credentials.provider</name>
        <value>software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider</value>
      </property>
      <property>
        <name>fs.s3a.endpoint.region</name>
        <value>us-west-2</value>
      </property>
    </configuration>
---
apiVersion: batch/v1
kind: Job
metadata:
  name: hadoop-s3a-read-check
  namespace: storage-demo
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 120
  template:
    spec:
      serviceAccountName: s3-access-sa
      restartPolicy: Never
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: hadoop
        image: registry.example.com/reviewed-hadoop-s3a:3.5.0
        command:
        - hadoop
        args:
        - fs
        - -ls
        - s3a://replace-with-owned-data-bucket/training/
        env:
        - name: AWS_REGION
          value: us-west-2
        - name: AWS_EC2_METADATA_DISABLED
          value: 'true'
        - name: HADOOP_CONF_DIR
          value: /opt/hadoop/etc/hadoop
        - name: HADOOP_OPTIONAL_TOOLS
          value: hadoop-aws
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: hadoop-config
          mountPath: /opt/hadoop/etc/hadoop/core-site.xml
          subPath: core-site.xml
          readOnly: true
      volumes:
      - name: tmp
        emptyDir: {}
      - name: hadoop-config
        configMap:
          name: hadoop-s3a-config
```

1つのConfigMapキーをsubPathでマウントすると、イメージ内の他のHadoop設定ファイルを維持できます。subPathマウントにはConfigMapの更新が反映されないため、設定を変更した後はJobを作り直してください。

### 既存バケットをMountpoint CSIでマウントする

レビュー済みの上流の組み合わせは、CSI 2.8.0と同梱Mountpoint 1.23.0です。Standalone Mountpoint 1.24.0を導入しても、CSIイメージが自動で変わるわけではありません。実際のEKSアドオンのバージョンとコンピュート環境の互換性を確認してください。この上流CSIリリースにはKubernetes 1.31以降が必要で、AL2／Ubuntu 22.04はサポートされなくなりました。既存のインフラ所有者に運用を任せてください。マネージドアドオンや既存ドライバーの上にHelmで重ねて導入しないでください。

別の所有者がHelmで導入する場合は、まず**公開済みチャート**をレンダリングしてレビューします。`--kube-version`には実際のクラスターのバージョンを指定してください。Git checkoutにあるチャートはサポート対象の配布物ではありません。公開ガードを回避してはいけません。選択した所有者を通じてデプロイする前に、特権を持つノードコンポーネント、CRDの所有権、`mount-s3`名前空間を確認します。
```bash
set -euo pipefail
helm repo add aws-mountpoint-s3-csi-driver https://awslabs.github.io/mountpoint-s3-csi-driver
helm repo update aws-mountpoint-s3-csi-driver
helm template aws-mountpoint-s3-csi-driver \
  aws-mountpoint-s3-csi-driver/aws-mountpoint-s3-csi-driver \
  --version 2.8.0 --namespace kube-system --kube-version 1.36.0 --include-crds \
  > s3-driver-review.yaml
```

公開済みチャートはデフォルトで`s3-csi-driver-sa`と`s3-csi-driver-controller-sa`を作成します。以下のPVは**Pod単位の認証情報**として`s3-access-sa`を明示的に選択します。このボリュームではドライバー単位の認証情報は無視されます。IRSAとEKS Pod Identityの両方がサポートされています。準備完了と判断するには、Helmレンダリングが成功しただけでなく、実際のドライバーとID設定が必要です。

Mountpoint CSIでは、既存バケットに対する**静的プロビジョニング**を使います。古い例にある動的StorageClassは使いません。storageClassNameの両フィールドを空にし、PV/PVCの明示的な事前バインドとクラスター内で一意のvolumeHandleを設定します。容量フィールドはKubernetesのバインド用メタデータです。S3バケットの容量を作成したり制限したりしません。バケット、プレフィックス、リージョンをまとめて置き換えてください。読み取り専用マウントとIAM権限は別々の制御です。
```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: s3-training-pv
spec:
  capacity:
    storage: 1Ti
  volumeMode: Filesystem
  accessModes:
  - ReadOnlyMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: ''
  claimRef:
    namespace: storage-demo
    name: training-data
  mountOptions:
  - read-only
  - region us-west-2
  - prefix training/
  - allow-other
  - uid 1000
  - gid 1000
  - dir-mode 0750
  - file-mode 0440
  csi:
    driver: s3.csi.aws.com
    volumeHandle: storage-demo-s3-training-v1
    volumeAttributes:
      bucketName: replace-with-owned-data-bucket
      authenticationSource: pod
      stsRegion: us-west-2
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: training-data
  namespace: storage-demo
spec:
  accessModes:
  - ReadOnlyMany
  storageClassName: ''
  volumeName: s3-training-pv
  resources:
    requests:
      storage: 1Ti
```



```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-s3
  namespace: storage-demo
spec:
  serviceAccountName: s3-access-sa
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: reader
    image: busybox:1.38.0
    command:
    - sh
    - -c
    args:
    - ls -la /data && sleep 3600
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
      readOnly: true
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: training-data
      readOnly: true
```

マウントオプションでファイルシステム上の所有者をUID/GID 1000に対応付けます。S3オブジェクトの所有者は変わりません。`allow-other`は、ドライバーが作成したマウントへアプリケーションのUIDがアクセスできるようにします。このマウント済み読み取りパスでは、アプリケーションコンテナにAWS CLIやFUSE特権は不要です。

### S3のユースケース

データレイク、モデルリポジトリ、アーカイブ、静的アセット、監査オブジェクトにはS3を使えます。オブジェクトのバージョン、条件付きリクエスト、Mountpointのファイルシステム契約にない機能が必要ならAPIアクセスを選んでください。ランダム更新やPOSIXロックを必要とするデータベース用ディレクトリには、別のストレージ設計が必要です。

## スナップショットとバックアップ {#snapshots-and-backups}

CSIスナップショットを使うには、対象ドライバー／バックエンドが対応している必要があります。PVCがあるだけではスナップショット機能があるとは限りません。以下のEBS例ではブロックボリュームのある時点の状態を取得します。必要に応じてアプリケーションを静止／flushするか、データベースを認識したバックアップ／WALアーカイブを使ってください。スナップショットに成功しても、アプリケーション整合性やデータベースの任意時点復旧が保証されるわけではありません。

![元のPVCからVolumeSnapshotとSnapshotContentを経由してEBSスナップショットを取得し、新しいPVCへ復元する流れを示す図。](../.gitbook/assets/en-eks-04-eks-storage-part2-2.png)

[🔍 インタラクティブ図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part2-2.html)

### Snapshot Controllerの準備

まず既存のsnapshot CRD、コントローラーの所有者、CSI snapshotterを確認します。互換性のあるEKSアドオン、またはレビュー済みの固定バージョンのexternal-snapshotterリリースを使ってください。既存インストールにfloating masterのCRDを適用しないでください。external-snapshotter 8.6.0はレビュー対象とした上流の参照バージョンであり、すべてのアドオンに対する自動アップグレード先ではありません。第1部のドライバーと名前空間の前提条件も適用されます。
```bash
set -euo pipefail
kubectl get crd volumesnapshots.snapshot.storage.k8s.io \
  volumesnapshotcontents.snapshot.storage.k8s.io volumesnapshotclasses.snapshot.storage.k8s.io
kubectl -n storage-demo get pvc ebs-claim -o yaml
```

### SnapshotClassとスナップショットの作成

SnapshotClassのドライバーはPVのドライバーと一致させます。手動管理するこのクラスはRetainを使います。Kubernetes上のスナップショットを削除しても、保持対象のEBSスナップショットは自動削除されません。所有権と費用を追跡し、後述するVeleroのライフサイクルポリシーと混同しないでください。このEBS例では、空のsnapshotter-secretパラメーターは不要です。
```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: ebs-snapshot-class
driver: ebs.csi.aws.com
deletionPolicy: Retain
```



```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: ebs-part2-snapshot
  namespace: storage-demo
  labels:
    storage-demo: ebs
spec:
  volumeSnapshotClassName: ebs-snapshot-class
  source:
    persistentVolumeClaimName: ebs-claim
```



```bash
set -euo pipefail
kubectl -n storage-demo wait --for=jsonpath='{.status.readyToUse}'=true \
  volumesnapshot/ebs-part2-snapshot --timeout=300s
kubectl -n storage-demo get volumesnapshot ebs-part2-snapshot -o yaml
```

### 新しいPVCへの復元

`readyToUse=true`になったら、restoreSizeとバインド済みのcontent／driverを確認します。同じ名前空間に別名のPVCを作り、容量を少なくともrestoreSize以上にします。この20Giの例では、スナップショットのサイズがそれを超えない前提です。稼働中のclaimはそのままにしてください。WaitForFirstConsumerの場合、互換性のあるコンシューマーがスケジュールされるまで候補PVCがPendingのままになることがあります。隔離した環境で互換性のあるアプリケーションを使って復元データを確認してから、管理された切り替えを行ってください。
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-part2-restored
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 20Gi
  dataSource:
    name: ebs-part2-snapshot
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
```

### Veleroによるバックアップのスケジュール

レビュー済みの組み合わせはVelero 1.18.4とAWSプラグイン1.14.4です。インストール前にCLIリリースのチェックサムとプラグイン互換性を確認してください。CSI対応はVeleroに統合されていますが、この経路では引き続き`EnableCSI`が必要です。古い独立CSIプラグインを追加しないでください。プライベートなバックアップバケット／プレフィックス、ネットワークアクセス、範囲を限定したIAM／KMS権限、`velero/velero`用のIRSAロールを準備します。以下はリソースを作成せず、新規インストール用マニフェストをレビューするためにレンダリングします。
```bash
set -euo pipefail
: "${BACKUP_BUCKET:?Set the existing private backup bucket}"
: "${VELERO_ROLE_ARN:?Set the reviewed IRSA role for system:serviceaccount:velero:velero}"
: "${AWS_REGION:?Set the bucket/snapshot Region for this example}"
velero install --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.14.4 \
  --bucket "$BACKUP_BUCKET" --prefix eks-storage-demo \
  --backup-location-config "region=$AWS_REGION" \
  --snapshot-location-config "region=$AWS_REGION" \
  --features EnableCSI --no-secret \
  --sa-annotations "eks.amazonaws.com/role-arn=$VELERO_ROLE_ARN" \
  --dry-run -o yaml > velero-review.yaml
```

このCLIのdry-runでも、実際に有効なkubeconfigが必要です。レンダリングは認可テストやバックアップテストではありません。既存のVelero／CRDインストールを上書きしないでください。デフォルトのServiceAccountはIRSAアノテーション付きで作成されます。一方、`--service-account-name`を使うと既存のアカウントが選択され、`--sa-annotations`は無視されます。Pod Identityは独自のAssociation／エージェント設定が必要な代替手段です。静的認証情報ファイルは不要です。

CSIクラスを選ぶ場合、ドライバーごとにデフォルトクラスを1つだけラベル付けするか、サポートされているバックアップ／スケジュール用アノテーションでクラスを選択します。以下のクラスは既存クラスと合わせて確認してください。
```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: ebs-velero-snapshots
  labels:
    velero.io/csi-volumesnapshot-class: 'true'
driver: ebs.csi.aws.com
deletionPolicy: Retain
```

**VeleroはCSIバックアップスナップショットのライフサイクルを管理します**。バックアップの期限が切れるか削除されると、元のクラスがRetainでも、VeleroはVolumeSnapshotContentの削除ポリシーをDeleteに変更してスナップショットを削除します。バックアップのTTLと、それとは独立した保持／アーカイブ手順を慎重に決めてください。S3上のVeleroバックアップに、すべてのボリュームデータが必ず含まれるわけではありません。CSIスナップショット、ファイルシステムバックアップ、データ移動ツールは別の経路です。たとえばFSx CSI 1.10.0はCSIスナップショットを実装していません。サポートされるFSx／アプリケーションのバックアップ方式を使ってください。
```bash
set -euo pipefail
velero schedule create storage-demo-daily --schedule="0 1 * * *" \
  --include-namespaces=storage-demo --ttl=168h0m0s -o yaml > velero-schedule-review.yaml
```

スケジュール作成コマンドもYAMLを出力するだけです。レビュー済みスケジュールを所有者を通じてデプロイし、実際のBackup phase、エラー、スナップショット／データ移動ツールの完了、復元テストを確認してください。スケジュール済みスナップショットだけで、任意のデータベースPITRが可能になるわけではありません。

復旧時は、固定された過去の時刻ではなく、実際に検証済みのバックアップを選びます。`-o yaml`を付けても、このコマンドはAPI discoveryを行い、選択したBackupを読み込むため、対象クラスターへの読み取り権限が必要です。このマニフェストプレビューでは要求するリソース種別を限定し、名前空間を対応付けます。送信する前に依存関係とプラグインの復元アクションを確認してください。復旧先の名前空間が隔離されていること、名前の競合がないこと、StorageClass／CSIドライバー／KMS／AZの対応が正しいことを確認します。これだけで本番向けの完全な復旧手順になるわけではありません。
```bash
set -euo pipefail
: "${VERIFIED_BACKUP:?Choose an actual completed backup after checking its contents/errors}"
velero restore create storage-demo-recovery-review --from-backup "$VERIFIED_BACKUP" \
  --namespace-mappings storage-demo:storage-recovery \
  --include-namespaces storage-demo \
  --include-resources persistentvolumes,persistentvolumeclaims,volumesnapshots.snapshot.storage.k8s.io,volumesnapshotcontents.snapshot.storage.k8s.io \
  --restore-volumes=true -o yaml > velero-restore-review.yaml
```

候補データのアプリケーション検証が済んでから、復元したワークロードを起動してください。ロールバック経路も残します。クラスターをまたいでCSI復元するには、一致するドライバー名と、アクセス可能なスナップショット／キーが必要です。名前空間の対応付けだけではクラウドリソースを移植できません。

## ボリューム拡張とリサイズ {#volume-expansion-and-resizing}

![拡張を許可するStorageClass、PVCの編集、CSI呼び出し、EBSの拡張、ファイルシステムのリサイズを示す図。](../.gitbook/assets/en-eks-04-eks-storage-part2-3.png)

[🔍 インタラクティブ図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part2-3.html)

`allowVolumeExpansion: true`を設定し、対応するCSIドライバー／ファイルシステムを使います。バインド済みclaimの既存storageClassNameはそのままにしてください。これはサイズ変更用の切り替え設定ではありません。この例は第1部の`ebs-gp3`を再利用し、claim要求量だけを増やします。すでにclaimの要求量が大きい場合に縮小しないよう、現在の要求量と容量を先に確認します。
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

```bash
set -euo pipefail
kubectl -n storage-demo get pvc ebs-claim -o yaml
kubectl -n storage-demo patch pvc ebs-claim --type merge \
  -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
kubectl -n storage-demo describe pvc ebs-claim
```

対応している場合、CSIがバックエンドとファイルシステムを拡張します。PVCの状態条件、コントローラー／ノードのログ、マウント後の容量を確認してください。必要なら、ドライバーが文書化している再マウント／再起動手順に従います。アプリケーションコンテナ内の推測した`/dev/xvdf`に対して`resize2fs`を実行しないでください。サイズ変更を回避するためにPV容量を編集してはいけません。クォータ／費用の上限を計画し、前の拡張が保留中の間に自動拡張を繰り返さないでください。

## ボリュームのクローン {#volume-cloning}

現在のEBS CSIは`dataSource`とCSIのclone機能を通じたPVCクローンをサポートします。EBS CSI 1.67.0は、想定上の隠れたスナップショットではなく、ネイティブEBSボリュームコピー（`CopyVolumes`）を使います。使用前に、導入済みドライバー／アドオンが対応していることを確認してください。コピー先は独立したボリュームですが、使用可能になることと初期化が完了して最高の性能を発揮することは別です。

通常のPVC dataSource手順では、同じ名前空間にあるバインド済みのソース、互換性のあるvolume mode／ドライバーを使い、ソース以上の要求サイズを指定します。storageClassNameを明示してください。省略するとデフォルトクラスの規則が適用され、ソースから自動的に継承されるわけではありません。ネイティブEBSコピーはソースと同じAZに残ります。アプリケーションを適切に静止／flushしない限り、整合性はクラッシュ時点です。1つのソースから初期化できるコピーは一度に1つだけで、アカウント／リージョンのクォータも適用されます。

この専用トレーニング用ソースを使うことで、本番名前空間に未検証のデータベースクローンを起動するのを避けます。例のAZは、writerとreaderの**両方**で実際にサポートされるAZに置き換えてください。seed JobはソースPVCを使い、既存のマーカーを上書きせずに1つ作成してから終了します。
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-clone-source
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 10Gi
---
apiVersion: batch/v1
kind: Job
metadata:
  name: ebs-clone-seed
  namespace: storage-demo
spec:
  backoffLimit: 0
  template:
    metadata:
      labels:
        app: ebs-clone-seed
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      nodeSelector:
        topology.kubernetes.io/zone: us-west-2a
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: writer
        image: busybox:1.38.0
        command:
        - sh
        - -c
        args:
        - |
          set -eu
          (set -C; printf 'clone-demo\n' > /data/seed.txt)
          sync
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
          claimName: ebs-clone-source
```

```bash
kubectl -n storage-demo wait --for=condition=complete job/ebs-clone-seed --timeout=300s
kubectl -n storage-demo get pvc ebs-clone-source -o yaml
```

seed Jobの完了後、別のクローンと読み取り専用コンシューマーを作成します。マーカー確認は検証方法を示す例であり、このレビューではクラウドコピーを実行していません。データベースをコピーしても既存のデータベースパスワードはリセットされません。後でデータベースとして起動する場合、コピー先は互換性のあるデータベースバージョンを使う必要があります。
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-clone
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 10Gi
  dataSource:
    kind: PersistentVolumeClaim
    name: ebs-clone-source
---
apiVersion: v1
kind: Pod
metadata:
  name: app-with-clone
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
    - test "$(cat /data/seed.txt)" = clone-demo && sleep 3600
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
      readOnly: true
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: ebs-clone
  nodeSelector:
    topology.kubernetes.io/zone: us-west-2a
```
| 特性 | PVC／ネイティブボリュームコピー | スナップショットからの復元 |
|---|---|---|
| ソース | 既存ボリューム／PVC | 保持されたある時点のスナップショット |
| 準備状況 | バックグラウンド初期化の完了前に利用可能になる | スナップショット／復元と初期化の状態による |
| 配置 | ネイティブEBSコピーはソースAZに残る | 新しい復元ボリュームは許可された別のAZを指定できる |
| 整合性 | アプリケーションの静止が必要な場合がある | アプリケーションを認識したバックアップが必要な場合がある |
| 名前空間 | 通常のPVC dataSourceは同じ名前空間 | Snapshotオブジェクトは名前空間スコープ。名前空間／クラスター間のインポートには明示的にサポートされた手順が必要 |
| 費用／保持 | コピー処理と新規ボリュームに課金され、ライフサイクルも独立 | スナップショットストレージと復元ボリュームに課金され、削除ポリシーも別 |

手順が「1段階」か「2段階」かだけから、速度、ストレージのオーバーヘッド、RPOを推定しないでください。ネイティブボリュームコピーはFast Snapshot Restoreやプロビジョニング済み初期化レートをサポートしません。実際のコピー初期化に関するガイダンスに従ってください。

## Multi-Attach EBS

EC2サービスでは、条件を満たすio1／io2ボリュームを、同じAZ内の互換性のあるNitroインスタンス最大16台にMulti-Attachできます。ボリューム種別やリージョンにも制限があります。**EBS CSI 1.66.0の動的プロビジョニングでは、io2 + ReadWriteMany + volumeMode: Blockの組み合わせがサポートされ、この機能によってMulti-Attachが有効になります。** この方法では`multiAttachEnabled`はサポート対象StorageClassスイッチではありません。RWOPは1 Podに制限するモードであり、Multi-Attachのアクセスモードではありません。

共有ブロックデバイスには、アプリケーションの書き込み調整機能はありません。通常のext4／XFSを複数ノードからそれぞれ読み書きでマウントしてはいけません。適切な調整機能を持つアプリケーション／クラスター化ファイルシステムとfencing設計を使ってください。io2はNVMe予約を使ったfencingをサポートしますが、アプリケーション側で正しく利用する必要があります。以下のアタッチだけを行うデモでは**デバイスへのI/Oもフォーマットも行いません**。指定されたラベル／anti-affinityが機能するには、ボリュームのAZ内に条件を満たすノードが2台必要です。実際のワークロードには、スリープするコンテナでなく、レビュー済みのデバイスアクセスと調整が必要です。
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-io2-multi-attach
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: io2
  iops: '10000'
  encrypted: 'true'
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: shared-block-pvc
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteMany
  volumeMode: Block
  storageClassName: ebs-io2-multi-attach
  resources:
    requests:
      storage: 100Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: shared-block-a
  namespace: storage-demo
  labels:
    app: shared-block-demo
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app: shared-block-demo
        topologyKey: kubernetes.io/hostname
  containers:
  - name: attachment-only
    image: busybox:1.38.0
    command:
    - sleep
    - '3600'
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
    volumeDevices:
    - name: shared
      devicePath: /dev/ebs-shared
  volumes:
  - name: shared
    persistentVolumeClaim:
      claimName: shared-block-pvc
---
apiVersion: v1
kind: Pod
metadata:
  name: shared-block-b
  namespace: storage-demo
  labels:
    app: shared-block-demo
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app: shared-block-demo
        topologyKey: kubernetes.io/hostname
  containers:
  - name: attachment-only
    image: busybox:1.38.0
    command:
    - sleep
    - '3600'
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
    volumeDevices:
    - name: shared
      devicePath: /dev/ebs-shared
  volumes:
  - name: shared
    persistentVolumeClaim:
      claimName: shared-block-pvc
```

io2 Multi-Attachボリュームは、サービスの条件を満たせばサイズ／IOPSを変更できます。「オンラインリサイズ不可」という一律の主張は誤りです。io1では変更のサポート状況が異なります。Multi-Attachの有効化／無効化には、ボリュームを未アタッチ状態にする必要があります。また、安全にサイズ変更できるかはCSI／ファイルシステム／アプリケーションの対応状況で決まります。共有ボリュームの障害はアタッチされたすべてのインスタンスに影響する可能性があります。Retainやアタッチ設定はバックアップの代わりではありません。

## Mountpoint for S3 CSIの詳細 {#mountpoint-for-s3-csi-deep-dive}

以下の動作はCSI 2.8.0に同梱されるMountpoint 1.23.0を基準に確認しています。新しい単体版のオプションを採用する前に、実際に導入されているバージョンを確認してください。

### パフォーマンス特性

大きなオブジェクトのシーケンシャル読み取りと、新しいオブジェクトへのシーケンシャル書き込みは代表的な適合ワークロードです。Mountpointは自動的にプリフェッチします。ランダム範囲読み取りもサポートされますが、オブジェクトサイズ、リクエスト頻度、ネットワーク、キャッシュ状態、アプリケーションの並列度によって結果は変わります。既存オブジェクトへの任意のランダム書き込みは遅いだけの最適化方法ではなく、サポートされていません。

過去の数値（未検証）：以前の英語版には、再現可能な設定や追跡可能な出典のない以下の集約値が記載されていました。現在のサービス上限でも、このレビューで測定した結果でも、サイジング保証でもありません。過去の主張として記録します。

| 過去に記載された操作 | 元の主張 |
|---|---|
| 大きなファイルのシーケンシャル読み取り | 集約で最大100 Gbps |
| 新規ファイルへのシーケンシャル書き込み | 集約で最大50 Gbps |
| 小さな範囲のランダム読み取り | レイテンシーが高くスループットが低い。ワークロードによる |

以前の「優秀／良好／普通」という定性的な評価も、統制されたベンチマークではありませんでした。

### ファイルシステムと整合性の制限

- S3は読み取り／一覧取得に強い整合性を提供します。MountpointのキャッシュはTTLまで古いメタデータ／内容や、存在しないという情報を意図的に保持する場合があります。S3自体が結果整合性だと説明しないでください。
- 新しいファイルはシーケンシャルに書き込まれます。既存オブジェクトを置き換えるには`allow-overwrite`とtruncateを伴うopenが必要です。任意のランダム更新は引き続きサポートされません。
- Availability Zone内のS3 Express One Zoneディレクトリバケットでは、`incremental-upload`によるappendと、単一ファイルのアトミックなrenameが可能です。汎用バケットでは、このMountpointバージョンからファイルrenameを利用できません。ディレクトリrenameもサポートされません。Local Zone内のディレクトリバケットは機能サポートが異なります。置き換えのためのrenameにもoverwrite権限／オプションが必要です。
- 削除は`allow-delete`とIAM権限による明示的なオプトインが必要です。読み取り専用の例ではどちらも有効にしていません。appendは常に「新しいオブジェクトバージョンを作る」操作ではありません。
- ハード／シンボリックリンク、chmod/chown、拡張属性、POSIXロック、デバイスファイル、一般的なsparse fileの動作はサポートされません。これらの欠けている操作を前提としてデータベースの整合性を設計しないでください。

### キャッシュ設定

Mountpoint CLIオプションはStorageClassパラメーターでなく、**PV.spec.mountOptions**に記述します。値は`metadata-ttl 300`のようなオプション文字列です。Mountpoint 1.23では、メタデータTTLは秒、単体版の`max-cache-size`は**MiB**、read/write-part-sizeは**バイト**単位です。8 MiBは8,388,608バイトです。以前のprefetch-bytes、read-ahead、max-read-parallelism、max-cache-size-mb、cache-block-sizeの例は、1.23で有効なCLIフラグではありません。

CSI v2は、通常`mount-s3`にある**Mountpoint Pod**用のキャッシュストレージを作ります。アプリケーションPodのemptyDirがそのキャッシュになるわけではありません。以下の代替静的PVでは、ディスクベースのemptyDirキャッシュを10Giに設定し、サイズ上限はドライバーが適用します。Memoryを使うとNVMeではなくtmpfs上のRAMになります。実際のバケット／プレフィックス／リージョンに置き換え、別途事前バインドしたPVCを使用してください。
```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: s3-training-cached-pv
spec:
  capacity:
    storage: 1Ti
  volumeMode: Filesystem
  accessModes:
  - ReadOnlyMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: ''
  claimRef:
    namespace: storage-demo
    name: training-data-cached
  mountOptions:
  - read-only
  - region us-west-2
  - prefix training/
  - allow-other
  - uid 1000
  - gid 1000
  - dir-mode 0750
  - file-mode 0440
  - metadata-ttl 300
  - read-part-size 8388608
  csi:
    driver: s3.csi.aws.com
    volumeHandle: storage-demo-s3-training-cached-v1
    volumeAttributes:
      bucketName: replace-with-owned-data-bucket
      authenticationSource: pod
      stsRegion: us-west-2
      cache: emptyDir
      cacheEmptyDirSizeLimit: 10Gi
      cacheEmptyDirMedium: ''
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: training-data-cached
  namespace: storage-demo
spec:
  accessModes:
  - ReadOnlyMany
  storageClassName: ''
  volumeName: s3-training-cached-pv
  resources:
    requests:
      storage: 1Ti
```

300秒のTTLでは、その間に外部で行われた変更が見えない場合があります。変更を問題にする場合は、変更しない／バージョン管理したデータセットのプレフィックスを使います。キャッシュ内容はローカルストレージに平文で保存されるため、ノード／ストレージへのアクセスも脅威モデルに含めてください。トレーニングコンテナとは別に、キャッシュ容量、追い出し動作、Mountpoint Podのメモリを見積もります。`cache: ephemeral`とストレージクラス／要求値を使う一時PVCキャッシュもサポートされています。ライフサイクルと費用を評価してください。古いホストキャッシュパスを設定し、CSI v2でも使われると想定しないでください。

### 大規模データセットの学習例

これは**未実行の統合テンプレート**であり、最適化済みのp4dベンチマークではありません。レビュー済みのGPU対応イメージに`/opt/training/train.py`を含め、スケジュール可能なGPUを4基、対応するdevice plugin、前述のアカウントとキャッシュデータPVC、UID/GID 1000から書き込めるRWXの`reviewed-model-output-rwx` PVCを準備します。スクリプトは示された引数に対応し、それぞれ別の出力ディレクトリを作成する必要があります。デプロイ前にプレースホルダーをすべて解決してください。
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: s3-sharded-training
  namespace: storage-demo
spec:
  completions: 4
  parallelism: 4
  completionMode: Indexed
  backoffLimit: 0
  activeDeadlineSeconds: 7200
  template:
    spec:
      serviceAccountName: s3-access-sa
      restartPolicy: Never
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: trainer
        image: registry.example.com/reviewed-trainer:replace-me
        command:
        - sh
        - -c
        args:
        - exec python /opt/training/train.py --data-dir=/data --shard-index="$JOB_COMPLETION_INDEX"
          --shard-count=4 --output-dir="/models/$JOB_COMPLETION_INDEX"
        env:
        - name: JOB_COMPLETION_INDEX
          valueFrom:
            fieldRef:
              fieldPath: metadata.annotations['batch.kubernetes.io/job-completion-index']
        resources:
          requests:
            cpu: '4'
            memory: 16Gi
            nvidia.com/gpu: 1
          limits:
            cpu: '8'
            memory: 32Gi
            nvidia.com/gpu: 1
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: data
          mountPath: /data
          readOnly: true
        - name: output
          mountPath: /models
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: training-data-cached
          readOnly: true
      - name: output
        persistentVolumeClaim:
          claimName: reviewed-model-output-rwx
      - name: tmp
        emptyDir: {}
```

インデックス付きJobの4つの完了タスクは、それぞれGPUを1基使う独立したデータシャードです。分散学習におけるプロセスの合流（rendezvous）や勾配同期、副作用を伴う処理のexactly-once実行を保証するものではありません。出力処理を再試行しても安全な設計にしてください。以前の4 GPU／8 GPU例は異なる構成の説明であり、性能比較ではありません。測定済みの要件に基づき、実際のハードウェア／リソースを選びます。

### S3、EFS、FSxから選ぶ

| 検討事項 | Mountpoint／S3 | EFS | FSx for Lustre |
|---|---|---|---|
| インターフェイス | オブジェクトベースのファイルシステム機能 | マネージドNFSファイルシステム | 並列Lustreファイルシステム |
| 一般的な適合用途 | 大きく変更しない入力データセット | 共有アプリケーションファイル | サポート対象HPC／MLの並列I/O |
| 書き込み | 文書化されたシーケンシャル／上書き、およびバケットごとのappend制限 | アプリケーションによる調整を伴うファイルシステム書き込み | アプリケーションによる調整を伴うファイルシステム書き込み |
| サイジング根拠 | リクエスト構成、キャッシュ、ネットワーク、オブジェクト配置 | 性能／スループットモード、クライアント、アクセスパターン | デプロイメント、容量、スループット、クライアント、ストライピング |
| 費用／同時実行 | リクエスト、転送、キャッシュ、クライアント制限を測定 | スループット、ストレージ、クライアント制限を測定 | 割り当て、スループット、クライアント制限を測定 |

サービス名だけから、費用を一律に低／中／高とランク付けしたり、クライアント数が無制限と判断したりすることはできません。

## ストレージパフォーマンスの最適化 {#storage-performance-optimization}

EKSでストレージ性能を最適化する方法を見ていきます。

![データベース、Webサーバー、分析、機械学習のワークロードをEBS、EFS、FSx for Lustreに対応付けるストレージ性能調整の図。](../.gitbook/assets/en-eks-04-eks-storage-part2-4.png)

[🔍 インタラクティブ図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-04-eks-storage-part2-4.html)

### EBSのパフォーマンス最適化

ボリューム種別とプロビジョニング済みIOPS／スループットは、測定したワークロード要件とインスタンスのEBS上限に基づいて選びます。以前の16,000 IOPS／1,000 MiB/sは引き続き設定例として有効ですが、現在のgp3で普遍的な最大値ではありません。リージョンのgp3ではサイズ／IOPSの条件により最大80,000 IOPS／2,000 MiB/sをサポートし、Outpostsでは上限が低くなります。最大値までプロビジョニングすればよいとも、それだけで十分とも想定しないでください。

空のボリュームには初期化は不要です。スナップショットから復元したボリュームやネイティブコピーでは初期化遅延が発生することがあり、それぞれ手順も異なります。**既存データにゼロを書き込むのは破壊的であり、安全な初期化方法ではありません**。対象ボリュームを正確に特定してください。スナップショット復元では、対応するプロビジョニング済み初期化レート、Fast Snapshot Restore、文書化された読み取り方式を評価します。これらの高速化機能はネイティブコピーには適用されません。以下は認可されたノード環境でメタデータを確認するだけです。
```bash
lsblk -o NAME,SERIAL,SIZE,TYPE,MOUNTPOINT
```

### EFSのパフォーマンス最適化

AWSは、高い同時実行性を含むワークロードにGeneral Purposeパフォーマンスモードを推奨しています。Max I/Oはレイテンシーが高い旧世代の選択肢です。スループットモードは観測した需要に合わせます。マウントオプションは`Pod.spec.volumes`ではなくStorageClassまたはPVに設定します。

これは新しいclaim向けの代替クラスです。EFS helperが推奨するRPCサイズ1 MiB、hard mount、timeout、noresvportは出発点であり、ベンチマーク結果ではありません。`retrans=2`は再試行後にさらに復旧処理を行います。hard mountは2回の試行後にリクエストを放棄する設定ではありません。第1部に従ってファイルシステムIDとアクセスポイントのIDを準備してください。
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: efs-tuned
provisioner: efs.csi.aws.com
reclaimPolicy: Retain
mountOptions:
- tls
- rsize=1048576
- wsize=1048576
- hard
- timeo=600
- retrans=2
- noresvport
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: '750'
  uid: '1000'
  gid: '1000'
  basePath: /storage-demo
  ensureUniqueDirectory: 'true'
```

### FSx for Lustreのパフォーマンス最適化

デプロイメント／ストレージ種別、スループット、クライアント容量を合わせて選びます。ファイルサイズ、同時実行数、測定したボトルネックに基づいてLustreストライピングを計画してください。ストライプを増やせば常に速くなるわけではありません。サポートされるPV／StorageClassのマウントオプションを使い、互いに競合する`noatime`と`relatime`を併記せず、どちらかを選びます。圧縮効果はデータによって異なります。`s3ImportPath`はサポート対象CSIパラメーターですが、インポート／エクスポートの利用可否と自動化は選択したFSx統合方式によって異なります。

### vLLMワークロード向けストレージ最適化

クラスだけに`storageCapacity`フィールドを指定する方法ではなく、前述の明示的なクラス／PVC割り当てを再利用します。モデルのコールド／ウォームロード、メタデータアクセス、CPU／GPU初期化、複数コンシューマーの同時アクセスをベンチマークしてください。量子化やshardingはモデルのメモリ／計算特性とファイル配置を変えるもので、自動的なストレージ最適化ではありません。EFAが役立つのは、対応するファイルシステム／クライアントや通信スタックに限られます。EFA対応GPUインスタンスを選ぶだけで、すべてのストレージ経路が高速化するわけではありません。

## まとめ

このドキュメントでは、Amazon EKSにおけるFSx for Lustre、S3、スナップショット、ボリューム拡張、パフォーマンス最適化を扱いました。ストレージごとに特性と用途が異なるため、アプリケーション要件に応じて適切な方法を選択し、最適化してください。

次の部では、EKSストレージのモニタリング、トラブルシューティング、コスト最適化、セキュリティを扱います。

## 参考資料

* [Amazon FSx for Lustre CSI Driver](https://github.com/kubernetes-sigs/aws-fsx-csi-driver)
* [Amazon S3 CSI Driver](https://github.com/awslabs/mountpoint-s3-csi-driver)
* [Kubernetes Volume Snapshots](https://kubernetes.io/docs/concepts/storage/volume-snapshots/)
* [Velero Backup and Restore](https://velero.io/docs/)
* [Amazon EKS Storage Best Practices](https://docs.aws.amazon.com/eks/latest/best-practices/storage.html)

* [Mountpoint CSI 2.8設定](https://github.com/awslabs/mountpoint-s3-csi-driver/blob/v2.8.0/docs/CONFIGURATION.md)
* [Mountpoint CSI 2.8キャッシュ](https://github.com/awslabs/mountpoint-s3-csi-driver/blob/v2.8.0/docs/CACHING.md)
* [Mountpoint 1.23のファイルシステム仕様](https://github.com/awslabs/mountpoint-s3/blob/mountpoint-s3-1.23.0/doc/SEMANTICS.md)
* [Hadoop 3.5 S3A認証](https://hadoop.apache.org/docs/r3.5.0/hadoop-aws/tools/hadoop-aws/index.html)
* [Velero 1.18 CSIスナップショットのライフサイクル](https://velero.io/docs/v1.18/csi/)
* [Velero AWSプラグイン互換性](https://github.com/velero-io/velero-plugin-for-aws)
* [EBSネイティブコピー](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-copying-volume.html)
* [EBS Multi-Attach](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volumes-multi.html)
* [FSx CSIアドオンのID](https://docs.aws.amazon.com/eks/latest/userguide/fsx-csi-create.html)

## クイズ

この章の内容を確認するには、[トピッククイズ](../quizzes/eks/04-eks-storage-part2-quiz.md)に挑戦してください。
