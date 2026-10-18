# EKS ストレージクイズ - Part 2

> **最終更新日**: 2026年9月11日

このクイズでは、ストレージの選択、StatefulSet のクレーム、S3/Mountpoint、クローン、バックアップと復旧を扱います。例では、この章で準備したドライバーやクラス、および専用 namespace を再利用します。このレビューでは、クラウドリソースのプロビジョニング、データベースの復旧、性能ベンチマークを実施していません。実行する前に、所有者を確認し、プレースホルダーを置き換えてください。

## 選択問題

### 1. StatefulSet で ordinal ごとに個別の PVC を割り当てるには、どうすればよいですか？

- A. ConfigMap で各クレームに手動で名前を付ける
- B. volumeClaimTemplates を使う
- C. すべてのレプリカに同じデータベースディレクトリを使う
- D. CSI ドライバーを無効にする

<details>
<summary>回答を表示</summary>

**回答: B**

`volumeClaimTemplates` を使うと、StatefulSet の各 ordinal に `<template>-<statefulset>-<ordinal>` という名前のクレームが割り当てられます。Pod を再起動した場合、ストレージのトポロジーとクレームのライフサイクルに従って、通常は同じクレームが再利用されます。StatefulSet はレプリカ間でデータベースのデータをコピーしません。

`OrderedReady` は Pod 管理ポリシーの既定値で、`Parallel` はスケーリング時の動作を変えます。すべての PVC 作成・削除が Pod の順序どおりになるという一般的な保証はありません。PVC の保持は `persistentVolumeClaimRetentionPolicy` で設定でき、既定値は Retain です。Delete を選ぶと、スケールダウン時や削除時にクレームが削除される場合があります。PV の reclaimPolicy は、バックエンドのライフサイクルを決める別の設定です。

次の3レプリカの例は、それぞれ独立した永続マーカーファイルを示すだけです。**レプリケーションされたデータベースではありません**。Headless Service は Pod の識別に使います。この sleep 中のファイルデモは、例示用の Service ポートで HTTP サーバーを実装していません。この章で用意した `ebs-gp3` クラスを再利用してください。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: stateful-files
  namespace: storage-demo
spec:
  clusterIP: None
  selector:
    app: stateful-files
  ports:
  - name: unused-demo
    port: 8080
    targetPort: 8080
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: stateful-files
  namespace: storage-demo
spec:
  serviceName: stateful-files
  replicas: 3
  podManagementPolicy: OrderedReady
  selector:
    matchLabels:
      app: stateful-files
  persistentVolumeClaimRetentionPolicy:
    whenDeleted: Retain
    whenScaled: Retain
  template:
    metadata:
      labels:
        app: stateful-files
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
      - name: file-owner
        image: busybox:1.38.0
        command:
        - sh
        - -c
        args:
        - |
          set -eu
          if [ ! -e /data/owner ]; then (set -C; printf "%s\n" "$POD_NAME" > /data/owner); fi
          cat /data/owner
          sleep 3600
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
        env:
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
  volumeClaimTemplates:
  - metadata:
      name: data
      labels:
        storage-demo: stateful-files
    spec:
      accessModes:
      - ReadWriteOnce
      storageClassName: ebs-gp3
      resources:
        requests:
          storage: 10Gi
```



```bash
kubectl -n storage-demo get pvc -l storage-demo=stateful-files -o wide
```

claim-template のラベルにより、確認用の selector が意味を持ちます。保持されたクレームを通常の Pod クリーンアップとして削除しないでください。WFFC はスケジューリング条件に合う AZ を選びますが、EBS のデータをすべての AZ で利用可能にするわけではありません。RWO はノード単位のアクセス制約であり、1 Pod だけの利用を保証するものではありません。1 Pod に限定する必要がある場合は、サポートされる RWOP を使ってください。

</details>

### 2. EBS の性能を選ぶ際、何を基準にすべきですか？

- A. 常に io1 を選ぶ
- B. 実測したワークロード要件と、ボリューム／インスタンスの上限
- C. 常に最大容量をプロビジョニングする
- D. すべてのアプリケーションを1つの AZ に置く

<details>
<summary>回答を表示</summary>

**回答: B**

レイテンシー、IOPS、I/O サイズ、キュー深度、スループットを測定し、ボリュームとインスタンスの EBS 上限に合わせてください。個々のボリュームに十分な性能を設定していても、インスタンスが複数ボリュームのボトルネックになる場合があります。ファイルシステム、初期化、キャッシュ、アプリケーションの動作も影響します。

| タイプ | 公開されている現在の上限（条件あり） | 主な考慮点 |
|---|---|---|
| gp3 | リージョン: 80,000 IOPS / 2,000 MiB/s。Outposts はそれより低い | ベースラインは 3,000 IOPS / 125 MiB/s。追加性能は独立して有料設定できる |
| io1 | 64,000 IOPS / 1,000 MiB/s | インスタンスとサイズの上限を踏まえたプロビジョンド IOPS |
| io2 Block Express | 256,000 IOPS / 4,000 MiB/s | 対応する Nitro、サイズ、IOPS、ワークロード要件 |
| st1 | 500 MiB/s | スループット重視の HDD。シーケンシャル I/O とバースト動作を考慮 |
| sc1 | 250 MiB/s | アクセス頻度の低いデータ向けのシーケンシャル HDD |

以前の gp3 設定例である 16,000 IOPS / 1,000 MiB/s は引き続き有効ですが、現在の最大値を示すものではありません。gp2 はサイズによってベースライン／バースト性能が変わります。一方、gp3 の性能は所定の比率の範囲で別途設定できます。すべてのデータベース、ログ、Web サーバーに自動的に最適なボリュームタイプはありません。RAID0 は別途検討するトレードオフであり、後述するように CSI の既定の最適化ではありません。

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

</details>

### 3. FSx for Lustre の主なアーキテクチャ上の利点は何ですか？

- A. 常に最も低コストである
- B. ドライバーやネットワークの前提条件がない
- C. 適したワークロード向けの並列ファイルシステムである
- D. すべての PVC が必ず 1,000 GB/s に達する

<details>
<summary>回答を表示</summary>

**回答: C**

FSx for Lustre は、対応する HPC、ML、分析、メディア処理ワークロード向けのマネージド並列ファイルシステムです。デプロイタイプ、クライアント／カーネル、容量、プロビジョニングするスループット、ネットワークを合わせて選んでください。宣伝上の集約最大値は、任意の小さな PVC で得られる性能を表しません。

SCRATCH_1 と SCRATCH_2 は再現可能な一時データ向けです。SCRATCH_2 でも、PV を使うだけで永続サーバーのレプリケーションが得られるわけではありません。PERSISTENT_1 と PERSISTENT_2 では、選べるストレージやスループットが異なります。たとえば PERSISTENT_2 SSD は 125/250/500/1000 MB/s/TiB を提供します。汎用的な 200 MB/s/TiB や 1,000 GB/s という説明をすべてのファイルシステムに当てはめないでください。こうした過去の集約値は、このレビューで測定・検証したものではありません。

この章のとおり、マネージドアドオン、または所有者が管理する互換ドライバーを準備してください。次の例では、サポートされている `s3ImportPath` パラメーターを使います。インポート／エクスポートには、互換性のあるデプロイ、権限、リポジトリのポリシー／タスクが必要です。CSI で作成するだけでは、S3 との双方向同期は自動的に行われません。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre-import-demo
provisioner: fsx.csi.aws.com
reclaimPolicy: Retain
parameters:
  subnetId: subnet-0123456789abcdef0
  securityGroupIds: sg-0123456789abcdef0
  deploymentType: SCRATCH_2
  dataCompressionType: NONE
  s3ImportPath: s3://replace-with-owned-data-bucket/training/
```

PVC の要求が動的ファイルシステムの容量を決めます。StorageClass に汎用の storageCapacity フィールドがあるわけではありません。圧縮やストライピングは、データと並列度に対して測定してください。並列度やストライプ数を増やしたり、LZ4 を使ったりしても、常に性能が上がるとは限りません。互換性は EKS マネージドアドオンのカタログで確認してください。「EKS にネイティブ統合されていない」ことは、FSx を除外する正確な理由ではありません。

</details>

### 4. Mountpoint CSI で正しいプロビジョニング方法はどれですか？

- A. 動的な s3-sc がバケットを作成する
- B. 既存バケットに静的 PV/PVC をバインドする
- C. PVC の容量フィールドで S3 クォータを設定する
- D. ファイルシステム用 PVC が EFS ファイルシステムを自動作成する

<details>
<summary>回答を表示</summary>

**回答: B**

`s3.csi.aws.com` と既存バケットを使い、PV と PVC の両方で storageClassName を空にします。claimRef／volumeName を明示し、volumeHandle は一意にしてください。CLI オプションは PV の mountOptions に設定します。Kubernetes の容量メタデータは S3 の容量制限ではありません。

</details>

### 5. authenticationSource: pod の場合、どの ID が使われますか？

- A. 常にコントローラーの IAM ロール
- B. PV に埋め込んだ静的キー
- C. アプリケーションの ServiceAccount に対応する Pod Identity または IRSA
- D. PVC を作成した端末の認証情報

<details>
<summary>回答を表示</summary>

**回答: C**

CSI 2.8 は Pod 単位の Pod Identity と IRSA をサポートします。このボリュームではドライバーの認証情報は無視されます。ロール、関連付け／信頼設定、必要なエージェント、バケット／KMS 権限を用意してください。ServiceAccount にアノテーションを付けるだけでは IAM ロールになりません。

</details>

### 6. CSI v2 で設定した emptyDir キャッシュはどこに配置されますか？

- A. Mountpoint Pod
- B. 同じパスを持つ任意のアプリケーション Pod の emptyDir
- C. 必ず S3 バケット内
- D. GPU インスタンスの NVMe 上に自動的に配置

<details>
<summary>回答を表示</summary>

**回答: A**

`cache: emptyDir` や `cacheEmptyDirSizeLimit` などの cache volumeAttributes を使います。Memory は tmpfs の RAM を意味します。Mountpoint のメタデータ TTL は秒、単体版の max-cache-size は MiB、読み書きの part size はバイト単位です。バージョン固有のフラグが、組み込まれた Mountpoint バイナリーに合っていることを確認してください。

</details>

### 7. キャッシュされたマウントで、外部からの S3 の変更がすぐに見えないことがあるのはなぜですか？

- A. S3 のリスト整合性は常に結果整合性だから
- B. 設定したキャッシュ TTL により古い情報や存在しないという結果が残ることがあるから
- C. すべての S3 書き込みで CSI の再起動が必要だから
- D. PV の容量が小さすぎるから

<details>
<summary>回答を表示</summary>

**回答: B**

S3 は強い読み取り／リスト整合性を提供します。任意で有効にした Mountpoint のキャッシュにより、TTL が切れるまでクライアントから古い状態が見えることがあります。キャッシュの動作を S3 の整合性モデルと混同しないでください。再現性が重要な場合は、不変のデータセット用プレフィックスや適切なキャッシュ設定を使います。

</details>

### 8. EBS のネイティブ PVC クローンに必要な条件の組み合わせはどれですか？

- A. 任意の namespace と AZ
- B. 常にコピー元のクラスが継承される
- C. アプリケーションの調整なしで整合性が保たれる
- D. 対応するドライバー、同一 namespace／コピー元 AZ、互換モード、十分なコピー先サイズ

<details>
<summary>回答を表示</summary>

**回答: D**

EBS CSI 1.66 では、実際のネイティブボリュームコピー経路を使います。通常の PVC の dataSource は同じ namespace 内で指定します。EBS のコピー先はコピー元と同じ AZ になります。StorageClass を明示し、コピー元以上のサイズを要求してください。利用可能になった後もバックグラウンド初期化中の場合があります。必要な整合性を得るには、アプリケーションを静止させてください。

</details>

### 9. EBS CSI 1.66 の動的 Multi-Attach に合う例はどれですか？

- A. gp3 + RWO + multiAttachEnabled:true
- B. io2 + RWOP + 独立した ext4 書き込み
- C. io2 + RWX + 調整されたアプリケーション I/O を用いる raw Block
- D. 複数 AZ にまたがる任意の EBS タイプ

<details>
<summary>回答を表示</summary>

**回答: C**

このドライバーは io2 のマルチライター・ブロック機能を Multi-Attach に割り当てます。汎用の SC multiAttachEnabled スイッチはありません。対象となる Nitro インスタンスはボリュームと同じ AZ に配置する必要があります。デバイスを共有しただけでは、書き込み調整や自動フェンシングは提供されません。io2 は、サービス／ドライバーの条件を満たせばサイズや IOPS を変更できます。「サイズ変更不可」という一律の説明は正しくありません。

</details>

### 10. 所有者である Velero バックアップの期限が切れた場合、CSI スナップショットはどうなりますか？

- A. Velero が content の削除ポリシーを Delete に設定し、クラスが Retain でも削除できる
- B. Retain なら必ず永久に保持される
- C. PVC だけが削除される
- D. スナップショットが自動で移植可能な S3 オブジェクトになる

<details>
<summary>回答を表示</summary>

**回答: A**

Velero 1.18 は CSI スナップショットのライフサイクルを管理します。バックアップの TTL を意図的に設定し、必要に応じて別の保持／アーカイブ手段を使ってください。統合 CSI 機能を利用するには EnableCSI も必要です。バックアップのメタデータ、ネイティブ CSI スナップショット、コピーしたボリュームデータはそれぞれ別のものです。

</details>

## 短答問題

### 11. RAID0 で得られるものは何ですか？また、EKS の設計で何を考慮する必要がありますか？

<details>
<summary>回答を表示</summary>

**回答: 冗長性を伴わないストライピング**

RAID0 は複数のボリュームにブロックを分散し、利用可能な容量を集約します。メンバーの1つに障害が起きると、アレイ全体が利用不能になることがあります。バックアップや高可用性の仕組みではありません。アプリケーション、ファイルシステム、CPU、インスタンスの EBS 上限が許せば、同じ容量のボリューム2つで理論上は1つのボリュームの約2倍の性能を得られる可能性があります。これは理論上の上限であり、実測で2倍になったという結果ではありません。

ファイルシステムモードの PVC を `/volume1` にマウントしても、そこはディレクトリであり、mdadm 用の raw ディスクではありません。実際にブロックデバイスを構成するには `volumeMode: Block`、`volumeDevices`、正確なボリューム識別、許可されたストレージコンポーネント、および空デバイスの初期化と既存アレイの組み立てを明確に分ける手順が必要です。アプリケーションの再起動ごとにフォーマットしてはいけません。ノード／AZ 内のアタッチ、再スケジュール、権限、拡張、複数ボリュームの整合性を保ったバックアップと復元を計画してください。

以前の特権付き Pod で無条件に mdadm/mkfs を実行する例は、そのままコピーして使える手順ではありません。以前の2～4ボリュームや 4/64/128 KiB のストライプ例は、測定済みの値ではなく、検証前の調整候補です。この複雑さを受け入れる前に、適切な単一 gp3/io2 ボリューム、再現可能なインスタンスストアの一時データ、または FSx と比較してください。

</details>

### 12. EFS の rsize と wsize は何を制御しますか？

<details>
<summary>回答を表示</summary>

**回答: NFS の読み書き RPC ペイロードの最大サイズ**

TCP ソケットバッファーのサイズではありません。AWS は、サポートされる NFS/EFS マウント経路で `hard,timeo=600,retrans=2,noresvport` とともに、読み書きの両方に 1,048,576 バイト（1 MiB）を推奨しています。timeo の単位は10分の1秒なので、600 は60秒です。hard マウントでは、retrans=2 だからといって2回の試行後に操作を中止するわけではありません。ワークロードの根拠なしに、ランダム I/O やパケット損失に対して小さい値を勧めないでください。オプションは Pod の volume ではなく StorageClass/PV に設定します。EFS は nconnect をサポートしていません。

この章で所有・準備した EFS ファイルシステムとアクセスポイントの構成を再利用してください。

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

書き込みテストを許可されている場合は、確認済みの使い捨てディレクトリと一意のファイル名を使い、既存データを上書きしかねない予測可能な `/efs/testfile` は使わないでください。次の GNU dd 例は 64 MiB を書き込み、自分で作成したファイルとディレクトリだけを削除します。読み取りがクライアントキャッシュに当たる可能性があるため、この時間だけで EFS のキャッシュなしスループットを判断できません。

```bash
set -euo pipefail
: "${EFS_TEST_DIR:?Set an approved disposable directory on the verified EFS mount}"
test -d "$EFS_TEST_DIR" && test -w "$EFS_TEST_DIR"
EFS_TEST_PATH=$(mktemp -d "$EFS_TEST_DIR/efs-test.XXXXXX")
cleanup() { rm -f -- "$EFS_TEST_PATH/payload"; rmdir -- "$EFS_TEST_PATH"; }
trap cleanup EXIT
time dd if=/dev/zero of="$EFS_TEST_PATH/payload" bs=1M count=64 conv=fsync
time dd if="$EFS_TEST_PATH/payload" of=/dev/null bs=1M
```

このレビューでは EFS の性能テストを実施していません。クライアント／アプリケーションのレイテンシーや並列度と、適切な CloudWatch 統計値／期間で取得した EFS の TotalIOBytes、DataReadIOBytes、DataWriteIOBytes、MetadataIOBytes を照らし合わせてください。バイトカウンターを計測間隔で割るまでは、スループットレートではありません。

</details>

### 13. EBS の可用性 SLA と耐久性設計は、どのように異なりますか？

<details>
<summary>回答を表示</summary>

**回答: 示す性質と適用条件が異なります**

EBS の SLA は可用性／サービスクレジットに関する契約であり、一律の 99.999% データ耐久性 SLA ではありません。リージョン単位のコミットメントでは、条件を満たす複数 AZ の同時デプロイに対して 99.99% のしきい値を用い、単一ボリュームでは 99.9% を用います。無条件の保証とみなさず、契約上の定義、除外事項、クレジット条件を確認してください。

| 公開されている設計上の特性 | ボリュームタイプ |
|---|---|
| 99.8～99.9% の耐久性、0.1～0.2% の AFR | gp3/gp2/io1 および HDD タイプ |
| 99.999% の耐久性、0.001% の AFR | io2 Block Express |

この契約に io2 専用の「99.999% 可用性 SLA」はありません。AFR／設計上の耐久性は、特定のアプリケーションですべてのデータが失われる確率ではありません。破損、削除、バックアップ、復旧アーキテクチャも関係します。EBS のレプリケーションは1つの AZ 内で行われ、AZ 間のデータベースレプリケーションが自動で構成されるわけではありません。

必要に応じてアプリケーション整合性のあるバックアップを取り、独立した復旧ポイントを保持し、復元をテストして、ボリュームとアプリケーションの健全性を監視してください。AZ 障害から復旧する場合は、アクセス可能なスナップショットを許可された AZ に復元します。削除されたレコードの復旧には、適切な復旧ポイントまたはデータベースの PITR 機能を使います。ブロックスナップショットだけで任意の時点に復旧できるわけではありません。

リージョン間のスナップショットコピーには、別途、コピー元／コピー先と KMS の権限、および完了確認が必要です。次は実行済みの復旧テストではなく、例示用の作成コマンドです。利用してよいコピー元とコピー先を確認し、返された SnapshotId を記録して、コピー完了を確認するまでは利用できると判断しないでください。

```bash
set -euo pipefail
: "${SOURCE_REGION:?Set the source snapshot Region}"
: "${DESTINATION_REGION:?Set the recovery Region}"
: "${SOURCE_SNAPSHOT_ID:?Select an owned completed snapshot}"
: "${DESTINATION_KMS_KEY_ARN:?Set a usable customer managed key in the recovery Region}"
STATE=$(aws ec2 describe-snapshots --region "$SOURCE_REGION" \
  --snapshot-ids "$SOURCE_SNAPSHOT_ID" --query 'Snapshots[0].State' --output text)
test "$STATE" = completed || { echo "Snapshot is not completed"; exit 1; }
aws ec2 copy-snapshot --region "$DESTINATION_REGION" --source-region "$SOURCE_REGION" \
  --source-snapshot-id "$SOURCE_SNAPSHOT_ID" --encrypted --kms-key-id "$DESTINATION_KMS_KEY_ARN" \
  --description "Reviewed storage recovery copy" --output json
```

AWS CLI イメージに kubectl が含まれているとは限らず、Kubernetes／IAM 権限が自動で付与されるわけでもありません。未設定の CronJob ではなく、適切な範囲で Velero、Data Lifecycle Manager、AWS Backup などのサポートされるバックアップ管理手段を使ってください。各ストレージサービスの実際のストレージクラス／デプロイ条件に応じた SLA と耐久性設計を個別に比較します。サービス横断で一律のパーセンテージ表を作るのは誤解を招きます。

</details>

## 実践問題

### 14. 明確な制限を含むデータベースのストレージ／復旧ワークフローを設計してください。

<details>
<summary>回答を表示</summary>

**回答: 自動復旧の保証ではなく、レビュー済みの設計案**

高い I/O 需要、定期バックアップ、検証済みの復旧、制御された拡張を必要とする PostgreSQL ワークロードを想定します。以下は**トレーニング用の設計案**であり、テスト済みの本番デプロイではありません。専用の `database` namespace、準備済みの Secret `postgres-secret/password`、互換性のある EBS／スナップショットドライバー、所有者が管理する Velero を再利用します。リソースの所有者に確認せず、既存リソースに適用しないでください。

#### ストレージとデータベース

元の 25,000 IOPS の割り当ては、例示用の io2 設定として残しています。十分かどうかは測定とインスタンス上限の確認が必要です。暗号化には設定済み／既定の EBS キーを使います。カスタマーマネージドキーを選ぶ場合、架空の kmsKeyId ではなく、実際の ARN、キーポリシー、ドライバーへの権限を準備してください。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: postgres-io2
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: io2
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
  iops: '25000'
```



```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: database
spec:
  clusterIP: None
  selector:
    app: postgres
  ports:
  - name: postgres
    port: 5432
    targetPort: postgres
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: database
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  persistentVolumeClaimRetentionPolicy:
    whenDeleted: Retain
    whenScaled: Retain
  template:
    metadata:
      labels:
        app: postgres
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 999
        runAsGroup: 999
        fsGroup: 999
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: postgres
        image: postgres:14.24
        env:
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        - name: POSTGRES_PASSWORD_FILE
          value: /run/postgres-secret/password
        ports:
        - name: postgres
          containerPort: 5432
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - postgres
          periodSeconds: 5
        resources:
          requests:
            cpu: '2'
            memory: 4Gi
          limits:
            cpu: '4'
            memory: 8Gi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
        - name: socket
          mountPath: /var/run/postgresql
        - name: tmp
          mountPath: /tmp
        - name: password
          mountPath: /run/postgres-secret
          readOnly: true
      volumes:
      - name: socket
        emptyDir: {}
      - name: tmp
        emptyDir: {}
      - name: password
        secret:
          secretName: postgres-secret
          defaultMode: 288
          items:
          - key: password
            path: password
  volumeClaimTemplates:
  - metadata:
      name: data
      labels:
        app: postgres
        storage-review: database-demo
    spec:
      accessModes:
      - ReadWriteOnce
      storageClassName: postgres-io2
      resources:
        requests:
          storage: 100Gi
```

これは Part 1 で確認した PostgreSQL 14.24 イメージの仕様（UID/GID 999、マウントしたパスワードファイル、書き込み可能な socket/tmp ボリューム、PGDATA のサブディレクトリ）に基づいています。メジャーバージョン14のサポートは2026年11月12日に終了します。この教材用のバージョンを新規本番環境の既定値にしないでください。適切なサポート中のメジャーバージョンと移行計画を選び、テストしてください。StatefulSet が1レプリカでも高可用性にはなりません。pg_isready は接続可否の確認であり、データ整合性や復旧のテストではありません。

#### バックアップと保持

この章のスナップショットコントローラーの前提条件と `ebs-snapshot-class` を使います。手動の復旧ポイントを作成する前に、データベースを静止させるか、サポートされるデータベースバックアッププロトコルを使ってください。実際の StatefulSet クレーム名は **data-postgres-0** です。

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: postgres-review-snapshot
  namespace: database
  labels:
    storage-review: database-demo
spec:
  volumeSnapshotClassName: ebs-snapshot-class
  source:
    persistentVolumeClaimName: data-postgres-0
```

復旧可能と判断する前に、readyToUse、restoreSize、content、driver を確認してください。スナップショットの暗号化はコピー元／キー設定を引き継ぎます。VolumeSnapshotClass にサポートされない encrypted/tagSpecification キーを設定しても、暗号化の構成にはなりません。現在のドライバーは特定のスナップショットタグ用パラメーターをサポートしていますが、ボリュームクラスのパラメーターを流用せず、そのドライバーのリリースに照らして確認してください。

次の例は TTL を30日に設定する日次 Velero スケジュールを作成します。CSI クラスの選択とデータベース整合性フック／プロトコルを確認したうえで、バックアップ管理者を通じて適用してください。元のクラスが Retain でも Velero の TTL により CSI スナップショットが削除される場合があります。バックアップの失敗／欠落を監視し、定期的に復元をテストしてください。スケジュールを設定しただけでは復旧可能と証明できません。

```bash
velero schedule create database-daily --schedule="0 1 * * *" \
  --include-namespaces=database --ttl=720h0m0s -o yaml > database-backup-schedule-review.yaml
```

#### 上限付きの拡張計画

古いメトリクスに基づいて、6時間ごとに無条件で50%ずつ拡張しないでください。次のレビュー専用プランナーは、Bound 状態のクレーム、拡張可能な一致するクラス、保留中のリサイズがないこと、同じ PVC UID を特定する新しいメトリクス、有効なファイルシステムのバイト数を要求します。一般的な10進／2進の Kubernetes 数量に対応し、未対応の入力は拒否します。使用率が80%に達すると、要求容量の最低1.5倍を提案し、例示上限の500Gi、UID／resourceVersion／現在サイズの事前条件を適用します。Kubernetes に変更を加えることはありません。

対象オブジェクトから最新の `pvc.json` と `storageclass.json` を取得してください。`trusted-metrics.json` には、実際にマウントされたファイルシステムから得た namespace、pvcName、pvcUID、タイムゾーン付き observedAt、usedBytes、capacityBytes を含めます。呼び出し元が UID を指定しただけでは、メトリクスの由来を証明できません。運用者／コントローラーがレビュー済みのパッチを適用する前に、収集元とマウントの対応、クォータ、コスト、ドライバー制約を確認してください。

```python
"""Generate a review-only plan from captured PVC, StorageClass and trusted metrics."""
import datetime,decimal,json,math,re,sys
D=decimal.Decimal
def quantity(s):
    match=re.fullmatch(r'([+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))([EPTGMK]i|[EPTGMk]|m|[eE][+-]?[0-9]+)?',s)
    if not match:raise ValueError('Unsupported/nonpositive quantity: '+s)
    value,suffix=D(match[1]),match[2] or ''
    if suffix.endswith('i'):value*=D(1024)**('KMGTPE'.index(suffix[0])+1)
    elif suffix in ['k','M','G','T','P','E']:value*=D(1000)**('kMGTPE'.index(suffix)+1)
    elif suffix=='m':value/=1000
    elif suffix:value*=D(10)**int(suffix[1:])
    if value<=0:raise ValueError('Capacity must be positive')
    return value
def plan(pvc,sc,metrics,now):
    meta,spec,status=pvc['metadata'],pvc['spec'],pvc['status']
    if (meta['namespace'],meta['name'])!=('database','data-postgres-0'):
        raise ValueError('Unexpected PVC')
    if status.get('phase')!='Bound' or not spec.get('volumeName'):
        raise ValueError('PVC is not Bound')
    if sc['metadata']['name']!=spec['storageClassName'] or sc.get('allowVolumeExpansion') is not True:
        raise ValueError('StorageClass mismatch or expansion disabled')
    if any(c.get('status')=='True' and c.get('type') in ['Resizing','FileSystemResizePending'] for c in status.get('conditions',[])):
        raise ValueError('Resize is pending')
    if status.get('allocatedResourceStatuses',{}).get('storage'):
        raise ValueError('Storage allocation is pending')
    requested=quantity(spec['resources']['requests']['storage'])
    if requested!=quantity(status['capacity']['storage']):
        raise ValueError('Request and capacity differ; inspect before another resize')
    if (metrics['namespace'],metrics['pvcName'],metrics['pvcUID'])!=(meta['namespace'],meta['name'],meta['uid']):
        raise ValueError('Metrics identify a different PVC')
    seen=datetime.datetime.fromisoformat(metrics['observedAt'].replace('Z','+00:00'))
    if seen.tzinfo is None or not 0<=(now-seen).total_seconds()<=300:
        raise ValueError('Metrics are stale or future-dated')
    used,capacity=D(str(metrics['usedBytes'])),D(str(metrics['capacityBytes']))
    if not used.is_finite() or not capacity.is_finite() or not 0<=used<=capacity<=requested or capacity<=0:
        raise ValueError('Invalid filesystem metrics')
    if used/capacity<D('0.8'):return {'reviewOnly':True,'action':'none','reason':'Below 80%'}
    target=math.ceil(max(requested*D('1.5'),used/D('0.7'))/D(1024**3))
    if target>500:return {'reviewOnly':True,'action':'manual-review','reason':'Illustrative 500Gi cap exceeded'}
    return {'reviewOnly':True,'action':'propose-resize','target':str(target)+'Gi','patch':[
      {'op':'test','path':'/metadata/uid','value':meta['uid']},
      {'op':'test','path':'/metadata/resourceVersion','value':meta['resourceVersion']},
      {'op':'test','path':'/spec/resources/requests/storage','value':spec['resources']['requests']['storage']},
      {'op':'replace','path':'/spec/resources/requests/storage','value':str(target)+'Gi'}]}
if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('Usage: resize-plan.py pvc.json storageclass.json trusted-metrics.json')
    inputs=[]
    for name in sys.argv[1:]:
        with open(name) as f:inputs.append(json.load(f))
    print(json.dumps(plan(*inputs,datetime.datetime.now(datetime.timezone.utc)),indent=2))
```

リソースが変わったらプランを再生成してください。失敗した事前条件を削除したり、パッチ失敗後に成功を記録したりしないでください。承認済みの拡張後は PVC の condition と実際のファイルシステム容量を確認します。サポートされる所有権管理手順で、StatefulSet テンプレートの将来のクレーム容量も合わせてください。完了したように見せるため PV の容量を編集してはいけません。

#### 復旧用候補

再試行する Job に、復元の最初の手順として稼働中クレームのスケールダウンと削除をさせないでください。restoreSize 以上の別候補を使います。100Gi の例は、復旧ポイントがそれ以下のサイズであることを仮定しています。元のクレームを拡張済みなら、候補の容量も調整してください。

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-restore-candidate
  namespace: database
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: postgres-io2
  resources:
    requests:
      storage: 100Gi
  dataSource:
    name: postgres-review-snapshot
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
```

必要な認証情報／バージョンを備えた互換性のある PostgreSQL コンシューマーを分離して起動し、バインドと復旧を待ち、制御された切り替えの前にアプリケーションのクエリ／データを検証します。元データと切り戻し手順を維持してください。既存の復元済みデータベースに新しい POSTGRES_PASSWORD 変数を設定しても、認証情報はリセットされません。

#### 監視

PostgreSQL のポート5432はデータベースプロトコルを使い、Prometheus の HTTP ではありません。ラベルが `app: postgres-exporter` で、名前付き `metrics` ポート9187と適切な範囲のデータベース認証情報を備えた、レビュー済み postgres-exporter ワークロードを用意してください。次の Service と ServiceMonitor はその exporter を選択するだけで、インストールはしません。Prometheus がこの ServiceMonitor／namespace を選択すること、NetworkPolicy／TLS／認証設定が実際のデプロイと一致することを確認してください。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres-exporter
  namespace: database
  labels:
    monitoring: postgres-exporter
spec:
  selector:
    app: postgres-exporter
  ports:
  - name: metrics
    port: 9187
    targetPort: metrics
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: postgres-exporter
  namespace: database
spec:
  selector:
    matchLabels:
      monitoring: postgres-exporter
  namespaceSelector:
    matchNames:
    - database
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
```

バックアップの新しさ／失敗、ファイルシステムの空き、PVC リサイズエラー、実測した I/O レイテンシー／キュー上限に対してアラートを設定します。本番対応を主張するには、ワークロードに応じた HA、復元、認証情報ローテーション、負荷テストが別途必要です。

</details>

### 15. 新しいクローンが遅い場合と、S3 データセットの古い内容が見える場合、どのように調査しますか？

<details>
<summary>回答を表示</summary>

**回答: 初期化、キャッシュ、アプリケーション整合性を切り分ける**

EBS クローンでは、実際のドライバーバージョン、コピー元の AZ／サイズ、コピー状態、初期化の進行状況、プロビジョニング性能とインスタンス側の性能を確認してください。ネイティブコピーは利用可能になっても、バックグラウンド初期化が続く場合があります。ゼロ書き込みを行ったり、空のボリュームだと扱ったり、スナップショット専用の初期化高速化が使えると思い込んだりしないでください。

Mountpoint では、インストール済みの CSI／バイナリーバージョン、PV オプション、Pod の ID、バケット／プレフィックス、負の結果を含むキャッシュ TTL を調べます。S3 の強い整合性が、設定済みクライアントキャッシュを無効にするわけではありません。バケットタイプに対してアプリケーションの操作がサポートされるかも確認してください。append／rename の前提は、汎用バケットとディレクトリバケットで異なります。

この章の分離されたクローン用マーカーとバージョン管理された S3 データセットを使い、仮説を検証してください。過去のベンチマーク値は未検証の参考情報として扱い、後日テストが許可された場合は実環境で測定した値を記録します。読み取りテストやスナップショット作成だけでは、データベースのアプリケーション整合性は証明されません。

</details>

## 参考資料

- [章とソースに対応した例](../../eks/04-eks-storage-part2.md)
- [StatefulSet の PVC 保持](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [EBS ボリュームタイプ](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volume-types.html)
- [EBS SLA](https://aws.amazon.com/ebs/sla/)
- [EBS ネイティブコピー](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-copying-volume.html)
- [EFS マウント設定](https://docs.aws.amazon.com/efs/latest/ug/mounting-fs-nfs-mount-settings.html)
- [Mountpoint CSI の設定](https://github.com/awslabs/mountpoint-s3-csi-driver/blob/v2.8.0/docs/CONFIGURATION.md)
- [Velero CSI のライフサイクル](https://velero.io/docs/v1.18/csi/)
- [Prometheus Operator API](https://prometheus-operator.dev/docs/api-reference/api/)
- [PostgreSQL のバージョンポリシー](https://www.postgresql.org/support/versioning/)
