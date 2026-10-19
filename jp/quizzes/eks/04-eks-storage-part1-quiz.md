# EKS ストレージクイズ - パート1

> **最終更新**: 2026年9月11日

解答は[ストレージ章](../../eks/04-eks-storage-part1.md)に記載された所有者と前提条件に基づいています。特に明記しない限り、例は一般的なLinux EC2ストレージを使用します。Auto Mode、Fargate、Hybridではサポート範囲が異なります。ローカルのスキーマ/モック検証は、AWSボリュームのアタッチ、データ復旧、本番性能の証明にはなりません。

### 1. プロビジョナー `ebs.csi.aws.com` で一般的なEBSボリュームを管理するドライバーはどれですか？

- A. Amazon EFS CSI Driver
- B. Amazon EBS CSI Driver
- C. FSx for Lustre CSI Driver
- D. Mountpoint for Amazon S3 CSI Driver

<details>
<summary>解答を表示</summary>

**解答: B. Amazon EBS CSI Driver**

このドライバーはEKSアドオンとして利用できますが、利用可能であることはすべてのクラスターに自動インストールされるという意味ではありません。EKS Auto Modeには、組み込みの `ebs.csi.eks.amazonaws.com` パスがあります。選択したコンピューティング方式、アドオンの管理者、Kubernetes/ドライバーの互換性、実際のインストール状態を確認してください。

コントローラー用のPod IdentityまたはIRSA信頼設定と、必要に応じてカスタマー管理KMSキーの権限を含む、レビュー済みの `AmazonEBSCSIDriverPolicyV2` またはスコープを絞った権限を準備します。過去のポリシーをコピーしても、現在のドライバーポリシーや信頼関係の代わりにはなりません。元の章にあるガード付きのカタログ/インストール手順を使い、AWS APIアドオンバージョンの文字列 `latest` を指定したり、別の所有者が管理するインストールを上書きしたりしないでください。

このクラスは、暗号化されたgp3、スケジューラーを考慮したプロビジョニング、拡張、意図的な保持を有効にします。
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
スナップショットには、さらにスナップショットCRD/コントローラーと対応するVolumeSnapshotClassが必要です。このドライバーは複数のEBSボリュームタイプをサポートし、それぞれにサイズ/性能の制約があります。通常のEBSボリュームは1つのAZ内に限られます。Fargate PodはEBSをマウントできませんが、別途設計したEBSコントローラーをFargate上で実行することはできます。EBSはHybrid Nodesと互換性がありません。

EFSとFSxにはそれぞれ対応するドライバーがあります。「公式のS3 CSIドライバーはない」という以前の説明は誤りでした。Mountpoint CSIは既存のS3バケットを限定的なPOSIXセマンティクスで公開し、S3 Filesは別の共有ファイルシステムインターフェイスをEFS CSI 3.0以降で提供します。

</details>

### 2. Lustreクライアントを使わず、Linuxノード間でファイルを共有するには、どのマネージドNFSサービスが適していますか？

- A. 通常のgp3ファイルシステム
- B. Amazon EFS
- C. S3オブジェクトのGET/PUT API
- D. FSx for Lustre

<details>
<summary>解答を表示</summary>

**解答: B. Amazon EFS**

EFSは共有NFSアクセスを提供し、RWXをサポートします。ただし、Podが複数あるというだけではEFSとは決まりません。RWOでも同じノード上の複数Podから利用でき、FSx for Lustreも共有に対応します。実際のプロトコル、一貫性、レイテンシー、スループット、耐久性、コストの要件で選択してください。

必要なコントローラーIAMロールと、既存の暗号化済みファイルシステムを備えた、サポート対象のEFS CSI構成を使います。実際のクライアントAZにマウントターゲットを用意し、各AZにつきサブネットは最大1つにします。SG、DNS、NFSの経路も整えます。元の章のセットアップではIDとAZ/VPCの所有関係を取得・確認します。異なる暗号化設定で同じ作成トークンを再利用しても、既存ファイルシステムがその場で暗号化されるわけではありません。
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
5 Giという要求値はバインディング用のメタデータであり、ディレクトリクォータではありません。アクセスポイントはPOSIX IDとルートディレクトリを強制しますが、許可されるアクセスはIAM/ファイルシステムポリシーとネットワーク制御で決まります。動的アクセスポイントのプロビジョニングはFargateの経路ではありません。Fargateではサポートされる静的統合を使います。TLS/クライアントのマウント認可と、コントローラーのプロビジョニング権限は別です。

EFS RegionalとOne Zoneでは障害特性が異なります。公表されている耐久性/設計目標やサービスレベルの約束は、このアプリケーションで測定された稼働率の保証ではありません。ストレージの自動拡張があっても、スループット/IOPS、クォータ、バックアップ、コストの計画は必要です。AWSはGeneral Purpose性能モードを推奨しています。Max I/Oは操作レイテンシーが高くなります。Elastic、Provisioned、Burstingは一律の既定値と考えず、要件に沿って選んでください。

静的なアプリケーション設定には、ConfigMap/Secretの方が適する場合があります。共有の可変ファイルには、アプリケーション側のロック/一貫性設計が必要です。S3 API、Mountpoint、S3 Filesはそれぞれ異なるインターフェイスです。S3のファイルアクセスを一括して否定しないでください。FSx for Lustreは別の並列ファイルシステムであり、セットアップが異なるだけで不適切になるわけではありません。

</details>

### 3. 一般的なEBSファイルシステムの制約を正しく説明している文はどれですか？

- A. 同じボリュームをどのAZにもアタッチできる
- B. Fargate Podは任意のEBSボリュームをマウントできる
- C. 1つのAZ内に限られ、RWOは同じノード上の複数Podで利用できる
- D. RWOはPodが必ず1つだけであることを保証する

<details>
<summary>解答を表示</summary>

**解答: C. ボリュームは1つのAZ内に限られ、RWOは同じノード上の複数Podで共有できます。**

RWOは「1つのノードから読み書き可能」という意味であり、「Podが1つだけ」という意味ではありません。同じAZ内の別ノードに置き換えたPodは、安全なデタッチ/アタッチ後に同じPVCを使用できます。同じボリュームをAZ間でアタッチすることはできません。スナップショットからの復元では対象AZに別のボリュームが作成されます。インプレース移動でも継続レプリケーションでもありません。
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
`WaitForFirstConsumer` を使い、スケジューリング制約を初期ボリューム配置に反映させます。バインド済みPVCはPVのトポロジー制約を引き継ぎます。ノードセレクターを変更してもデータは移動しません。StatefulSetのレプリカごとのPVCは別々のボリュームを作りますが、データベースのレプリケーションではありません。マルチAZ可用性には、アプリケーション/データのレプリケーションまたは復旧設計が必要です。

EBS CSI 1.66.0は、対応するインフラストラクチャとアプリケーションの連携を前提に、io2のraw-block Multi-Attach経路でRWXもサポートします。これは通常のgp3/ext4ボリュームをマルチノード共有ファイルシステムに変えるものではありません。Fargate Podは引き続きEBSをマウントできません。共有ファイルシステムが必要なら適切なものを使ってください。

</details>

### 4. 動的にプロビジョニングするEBSクレームは、必ずReadWriteOnceだけを使わなければなりませんか？

<details>
<summary>解答を表示</summary>

**解答: いいえ。通常の例はRWOですが、RWOPや特殊なraw-blockモードには別の要件があります。**

RWOPはRWOにはない、Podを1つに制限する機能を提供します。Kubernetes 1.29からstableで、互換性のあるCSI sidecar stackが必要です。CSIのアクセスモード変換では、新しいsingle-node capabilityを持たないドライバー向けにRWOPを `SINGLE_NODE_WRITER` に対応づけることがあります。ドライバー定数だけを見てもRWOP非対応とは判断できません。次は1 Podのワークロード向けの**別案のクレーム**です。
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ebs-exclusive
  namespace: storage-demo
spec:
  accessModes:
  - ReadWriteOncePod
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 10Gi
```
| モード | 意味 |
|---|---|
| RWO | 1つの読み書きノード。同じノード上の複数Podで共有できる |
| RWOP | 互換性のあるCSI/Kubernetesサポートのもと、クラスター全体で1 Podに制限 |
| RWX | バックエンド/ドライバーとアプリケーションが対応する場合にマルチノード書き込み |
| ROX | マルチノード読み取り機能。すべてのCSIドライバーが対応するわけではない |

アクセスモードが一致しても、ファイルシステム/IAM権限や明示的な読み取り専用マウントの代わりにはなりません。スナップショットから復元した別々のボリュームは独立したコピーであり、1つの共有ROXボリュームではありません。通常のext4/XFSを複数ライターから個別にマウントし、クラスター対応ストレージの代わりにしないでください。

</details>

### 5. EBSを使うPodが別ノードに置き換わったとき、何が起きますか？

<details>
<summary>解答を表示</summary>

**解答: 保持されたボリュームは同じAZ内で安全にデタッチ/アタッチできます。復旧時間とアプリケーション一貫性は確認が必要です。**

Kubernetesは置き換えPodを作成します。元のPodオブジェクトを移動させるわけではありません。単一アタッチのボリュームでは、新しいノードにアタッチする前に、旧ライターを停止/フェンスし、安全にデタッチする必要があります。ボリュームはライフサイクル設定に従って保持されますが、突然の障害では未フラッシュの書き込みが失われたり、ファイルシステム/データベースの復旧が必要になったりします。すべての書き込みが必ず残るとは言わないでください。

元の「10〜30秒」という再アタッチ時間には、ここでは検証済みの測定根拠がありません。**未検証の過去の推定値**として残されているもので、AWS SLAや復旧時間の保証ではありません。ノード障害の検出、フェンシング、コントローラーの再調整、ボリューム操作、アプリケーション起動にはさらに時間がかかる場合があります。

PDBが制約するのは該当する自発的な退避であり、ノード/AZ障害ではありません。実際のレプリカ数/クォーラムに合わせて設定してください。データベースのレプリカが1つなら、PDBを設定しても高可用性にはなりません。Readinessは永続的な `/data/ready` マーカーだけでなく、アプリケーションの準備状態を確認してください。Livenessはコンテナを再起動するもので、Serviceトラフィックを制御するものではありません。StatefulSetの順序制御やトポロジー分散で、1つのEBSボリュームがAZ間に複製されるわけではありません。AZごとのPDB案にも実際に一致するPodラベルが必要です。ノードのAZラベルが自動でPodに複製されるわけではありません。

可能な場合はグレースフルシャットダウンを使い、VolumeAttachment/Podイベントと実際のノード状態を診断し、文書化された復旧手順に従ってください。フェンシングせずに強制デタッチしたり、アタッチメントのメタデータを削除したりするのは、一般的な短縮策ではありません。独立したバックアップで、復元後のアプリケーションデータと復旧目標をテストしてください。

</details>

### 6. EBSスナップショットを要求するリソースと、バックアップを利用可能にする条件は何ですか？

<details>
<summary>解答を表示</summary>

**解答: `VolumeSnapshot`**

互換性のあるスナップショットCRD/コントローラーとEBS snapshotterを準備し、実際のプロビジョナーに一致するクラスを使います。アドオンの所有者を維持し、固定されていないmasterマニフェストを適用しないでください。スナップショットがreadyでもアプリケーションの復旧が証明されるわけではありません。整合性を保つにはデータベースに対応したバックアップ/静止化が必要な場合があります。
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
`status.restoreSize` 以上の容量で、同じnamespaceに新しいクレームとして復元します。WaitForFirstConsumerのバインディングには適切なconsumerを使い、データを検証してください。このマニフェストは上記の**固定名 `ebs-snapshot` を復元します**。別のスナップショットを復元する場合は名前を変更してください。
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
繰り返し作成する場合は、こちらのコマンドを使うと一意のスナップショットを作成し、readyになるまで待つ**別案**になります。生成された名前を記録してください。スケジュール実行には、意図した範囲に絞ったServiceAccount/RBAC、バージョン固定ツール、UTC/タイムゾーンの選択、重複実行防止、エラー/保持処理が必要です。ServiceAccountを指定しない古い例は、導入済みのバックアップシステムではありませんでした。
```bash
set -euo pipefail
SNAPSHOT_NAME="ebs-snapshot-$(date -u +%Y%m%d%H%M%S)-$RANDOM"
kubectl -n storage-demo create -f - <<EOF
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: $SNAPSHOT_NAME
  labels:
    storage-demo: ebs
spec:
  volumeSnapshotClassName: ebs-snapshot-retain
  source:
    persistentVolumeClaimName: ebs-claim
EOF
kubectl -n storage-demo wait --for=jsonpath='{.status.readyToUse}'=true \
  "volumesnapshot/$SNAPSHOT_NAME" --timeout=300s
```
保持処理では、絶対時刻を解析し、namespace、バックアップラベル、元のPVCで対象を絞ります。次は**レビュー専用の候補一覧**を生成し、何も削除しません。自動削除の前に、各バインド済みVolumeSnapshotContentのdeletionPolicy、所有者、依存関係、検証済みの復旧ポイントを確認してください。DeleteポリシーはAWSスナップショットを削除する可能性があります。Retainはスナップショットを保持し、ストレージ料金が残る場合があります。本番バックアップコントローラーには、UID/事前条件の処理と復旧テストが必要です。範囲を絞らないxargs削除パイプラインでは不十分です。
```bash
set -euo pipefail
kubectl -n storage-demo get volumesnapshots -l storage-demo=ebs \
  -o json > storage-demo-snapshots.json
python3 - storage-demo-snapshots.json <<'PY'
import datetime, json, sys
now = datetime.datetime.now(datetime.timezone.utc)
cutoff = now - datetime.timedelta(days=30)
with open(sys.argv[1]) as stream:
    snapshots = json.load(stream)["items"]
candidates = []
for snapshot in snapshots:
    meta, spec, status = snapshot["metadata"], snapshot["spec"], snapshot.get("status", {})
    if meta.get("namespace") != "storage-demo" or meta.get("labels", {}).get("storage-demo") != "ebs":
        continue
    if spec.get("source", {}).get("persistentVolumeClaimName") != "ebs-claim":
        continue
    if status.get("readyToUse") is not True or meta.get("deletionTimestamp"):
        continue
    created = datetime.datetime.fromisoformat(meta["creationTimestamp"].replace("Z", "+00:00"))
    if created.tzinfo is None:
        raise SystemExit("Snapshot timestamp must include a timezone")
    if created < cutoff:
        candidates.append({"name": meta["name"], "uid": meta["uid"],
                           "content": status.get("boundVolumeSnapshotContentName"),
                           "createdAt": meta["creationTimestamp"]})
print(json.dumps({"reviewOnly": True, "candidates": candidates}, indent=2))
PY
```
クラスター/アカウント/Region間でスナップショットを移すには、明示的なインポート/コピー、KMSアクセス、復元設定が必要です。本番データをテスト環境にコピーする場合も、同じアクセス/保持管理を適用してください。VolumeSnapshotオブジェクトの存在だけでなく、実際のデータを検証してください。

</details>

### 7. データベース、共有ファイル、並列MLデータ向けのストレージを設計してください。

<details>
<summary>解答を表示</summary>

**解答: 各要件に合わせて、前提条件を明示したバックエンドとライフサイクルを選びます。**

これはレビュー済みの構成ブループリントであり、**本番環境にデプロイされたシステムではありません**。まず `database`、`application`、`ml-workloads` namespace、互換性のあるCSIドライバーとIAMロール、KMS/ネットワーク権限、実際のEFS/FSx/S3リソース、イメージ/コンピューティングの互換性を作成/レビューしてください。StorageClassはクラスター全体のリソースです。以下の例は、1人の所有者が管理する別案です。容量、アプリケーション復旧、性能は対象環境でテストしてください。

**1. データベースのブロックストレージ。** 元の例示値である16,000 IOPS/1,000 MiB/sは維持しますが、gp3の一律の上限とは扱わないでください。現在のRegional gp3は、ボリュームサイズ/IOPS比とインスタンス上限の範囲内で最大80,000 IOPS/2,000 MiB/sをサポートします。Outpostsの上限は異なります。この値は構成の選択であり、ベンチマークでも、その費用がデータベースに必要だという証拠でもありません。
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3-db
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
parameters:
  type: gp3
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
  iops: '16000'
  throughput: '1000'
```
StatefulSetは `data` クレームテンプレートから **data-postgres-0** を作成します。元の未使用 `database-data` PVCを別途作成したり、その未使用クレームをスナップショットしたりしないでください。安全に管理する `password` キーを持つ `postgres-secret` を準備します。ここではパスワード値を指定しません。イメージはマウントされたファイルから読み取り、PGDATAはサブディレクトリを使います。これによりボリュームルートのファイルシステムメタデータが初期化を妨げません。
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
    spec:
      accessModes:
      - ReadWriteOnce
      storageClassName: ebs-gp3-db
      resources:
        requests:
          storage: 100Gi
```
この例はPostgreSQL 14の検証済み最新マイナーリリース14.24を使います。メジャー14のサポートは2026年11月12日に終了します。サポート対象バージョンへの移行をテストして計画し、本番では承認済みイメージのdigestを固定してください。この構成はレプリカ1つであり、レプリケーション/HAデータベースではありません。データベースレプリケーション設計なしにレプリカを増やしても解決しません。明示的なPVC保持ポリシーは、StatefulSet削除/縮小後もクレームを残すため、データとストレージ料金が残る場合があります。

アプリケーション整合性を保つバックアップ/静止化の後、データベースが実際に使うクレームをスナップショットします。クラスは前述の保持対象EBSスナップショットクラスです。
```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: database-snapshot
  namespace: database
  labels:
    backup-set: postgres-demo
spec:
  volumeSnapshotClassName: ebs-snapshot-retain
  source:
    persistentVolumeClaimName: data-postgres-0
```
**2. 共有ファイル。** 静的な設定にはConfigMap/Secretが適することがよくあります。変更可能な共有ファイルが必要なら、元の章にあるEFSクラスが別々のAPディレクトリとUID/GID 1000を提供します。ファイルシステムIDを置き換えて、クライアントパス/権限を検証してください。このクレームは5 Giクォータを課しません。
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
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: config-storage
  namespace: application
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: efs-sc
  resources:
    requests:
      storage: 5Gi
```
このseed Jobは機密情報ではないデモ設定だけを書き込み、既存ファイルを保持します。3つのreader Podは読み取り専用でマウントし、読み取れることを確認します。これはファイル配信のデモです。実際のアプリケーションでは設定を解析/再読み込みする必要があります。未設定のnginxに `/etc/config` をマウントしても、そのファイルをnginxが使うようにはなりません。
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: config-seed
  namespace: application
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: seed
        image: busybox:1.38.0
        command:
        - sh
        - -c
        args:
        - |
          set -eu
          if test -e /config/settings.txt; then
            echo "Existing settings preserved"
          else
            (set -C; printf 'MODE=demo\n' > /config/settings.txt)
          fi
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
        - name: config
          mountPath: /config
      volumes:
      - name: config
        persistentVolumeClaim:
          claimName: config-storage
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: config-reader
  namespace: application
spec:
  replicas: 3
  selector:
    matchLabels:
      app: config-reader
  template:
    metadata:
      labels:
        app: config-reader
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
      - name: reader
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
        readinessProbe:
          exec:
            command:
            - test
            - -r
            - /etc/config/settings.txt
        resources:
          requests:
            cpu: 10m
            memory: 16Mi
          limits:
            cpu: 100m
            memory: 64Mi
        volumeMounts:
        - name: config
          mountPath: /etc/config
          readOnly: true
      volumes:
      - name: config
        persistentVolumeClaim:
          claimName: config-storage
```
**3. 並列MLデータ。** サポート対象のLustreクライアント/kernel、CSI/IAM、ファイルシステム/S3統合を準備してください。このSCRATCH_2例は再生成可能なデータ向けです。永続ストレージ専用の単位当たりスループット設定や自動バックアップ設定は含みません。`s3ImportPath` はFSx CSI 1.10.0で有効なパラメーターです。所有権とアクセス権のあるデータセットのバケット/プレフィックスに置き換え、サポートされる統合/Region設定を確認してください。LZ4はストレージ機能であり、圧縮率やスループットの測定結果を示すものではありません。
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
  dataCompressionType: LZ4
  s3ImportPath: s3://example-training-data/dataset/
mountOptions:
- flock
```
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ml-training-data
  namespace: ml-workloads
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: fsx-lustre
  resources:
    requests:
      storage: 1200Gi
```
1200 Giのクレームは割当量の例です。ドライバーの丸めとサービス側の容量選択を確認してください。以下のJobは**テンプレート**です。実測済みで非rootのGPUイメージに置き換え、そのイメージが `/opt/training/train.py` を含み、指定引数を受け付けることを確認してから実行し、データセットを用意してください。学習コードはデータマウントで隠さず、イメージに含めます。4つのGPUを要求するPodを4つ並列に実行すると、要求CPU/メモリと該当クォータに加え、**GPUが16個必要**になる場合があります。Indexed completionは4つのタスクを識別しますが、分散学習/勾配同期を自動実装するものではありません。
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: ml-training
  namespace: ml-workloads
spec:
  parallelism: 4
  completions: 4
  completionMode: Indexed
  backoffLimit: 2
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: training
        image: registry.example.com/team/trainer:reviewed
        command:
        - python
        - /opt/training/train.py
        args:
        - --data-dir
        - /training
        - --shard-index
        - $(JOB_COMPLETION_INDEX)
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
        resources:
          limits:
            nvidia.com/gpu: '4'
          requests:
            cpu: '8'
            memory: 32Gi
        volumeMounts:
        - name: data
          mountPath: /training
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: ml-training-data
```
「数百GB/s」や「数百万IOPS」という元の集約性能の記述は、この小規模なSCRATCH_2例を測定したものではありません。これらを根拠にサイジングせず、代表的なワークロードで選択したファイルシステム/クライアント設定を検証してください。学習は実行していません。

**復旧、監視、コスト:** バックエンドとファイルシステム/アプリケーションのメトリクスを明示的に選び、実際のクォータ/スループット/レイテンシー/使用量を監視して、既知データで復元をテストします。PVやスナップショットを保持しても、バックアップスケジュールができるわけではありません。不要に見えるボリュームを削除する前に、所有者、参照先、検証済みの復旧コピーを確認してください。セキュリティにはPod Security admission/securityContext、スコープを絞ったIAM、TLS、ファイルシステム権限を使います。削除済みのPodSecurityPolicyは選択肢ではありません。このブループリントは本番準備完了も、最適なコスト/性能も示していません。

</details>

### 8. Podを削除すると、ボリュームデータも必ず削除されますか？

- A. はい。すべてのボリュームが削除される
- B. いいえ。ライフサイクルを確認する
- C. Podにコンテナが2つある場合のみ
- D. いいえ。すべてのボリュームが永続する

<details>
<summary>解答を表示</summary>

**解答: B. いいえ。ボリューム種別、PVCの所有関係、reclaim policyで決まります。**

emptyDirのデータはPod単位ですが、保持されるPVCベースのボリュームはPodより長く残る場合があります。汎用エフェメラルPVCはPodに所有されることがあります。物理的なインスタンスストアのデータは、CSIドライバーがPVとして公開していてもノード/メディアのライフサイクルに結びつきます。実在する2026年5月のEC2 Instance Store CSIアドオンを使っても、耐久性のあるレプリケートストレージにはなりません。

</details>

### 9. 5 Giを要求するEFS PVCは、ディレクトリに5 Giのクォータを設定しますか？

- A. はい。5 Giを超えると書き込みに失敗する
- B. はい。各アクセスポイントにブロックデバイスが割り当てられる
- C. いいえ。要求値はバインディング用のメタデータである
- D. directoryPermsを700にした場合のみ

<details>
<summary>解答を表示</summary>

**解答: C. いいえ。これはKubernetesの容量/バインディング用メタデータです。**

EFSは保存データに応じて拡張され、このクレームはディレクトリをその容量で事前割当/制限しません。ファイルシステムのスループット、アクセスポイント、クライアントの動作、保持、コストは別途計画してください。クォータを強制する必要がある場合は、アプリケーション/アカウント側の明示的な制御を使います。

</details>

### 10. StorageClassで初期reclaim policyを設定するフィールドはどれですか？

- A. `persistentVolumeReclaimPolicy`
- B. `reclaimPolicy`
- C. `deletionPolicy`
- D. `dataRetention`

<details>
<summary>解答を表示</summary>

**解答: B. `reclaimPolicy`**

`persistentVolumeReclaimPolicy` は `PersistentVolume.spec` のフィールドです。StorageClassのポリシーは新しくプロビジョニングされるPVにコピーされます。クラスを変更しても、既存のすべてのPVが自動的に変更されるわけではありません。スナップショットのdeletionPolicyは別のライフサイクル設定です。

</details>

### 11. 動的にプロビジョニングされたEFSアクセスポイントでDeleteを実行すると、通常は何が削除されますか？

- A. VPC内のすべてのファイルシステム
- B. 常にEFSファイルシステム全体
- C. アクセスポイント。ルートディレクトリの削除は任意
- D. AWSリソースは一切削除できない

<details>
<summary>解答を表示</summary>

**解答: C. アクセスポイントです。ディレクトリデータの削除はコントローラー設定に依存します。**

アクセスポイントプロビジョナーは通常、EFSファイルシステムを削除しません。レビューしたチャートでは `deleteAccessPointRootDir` の既定値はfalseです。有効にするとデータ削除の動作が変わります。クレームを削除する前に、実際のコントローラー値と共有/再利用されるアクセスポイントの所有関係を確認してください。

</details>

### 12. EKSからのS3アクセスについて、正しい説明はどれですか？

- A. 公式のS3 CSIドライバーは存在しない
- B. インターフェイスと前提条件はそれぞれ異なる
- C. Mountpointは新しいバケットを自動作成する
- D. すべてのS3マウントがあらゆるPOSIX操作に対応する

<details>
<summary>解答を表示</summary>

**解答: B. S3 API、Mountpoint CSI、S3 Filesではインターフェイスと要件が異なります。**

公式のMountpoint CSIは、限定されたPOSIXセマンティクスを持つファイルインターフェイスを通じて既存バケットをサポートします。S3 FilesはEFS CSI 3.0以降がサポートする別の共有ファイルシステムサービスであり、コントローラー/ノード権限も異なります。S3ベースの経路すべてで同じ操作、コンピューティング方式、プロビジョニングモデルが使えると考えないでください。

</details>

### 13. WaitForFirstConsumerのPVCが正当にPendingになり得るのはどのような場合ですか？

- A. すべてのCSIドライバーが壊れている
- B. 適切なconsumerがまだスケジュールされていない
- C. Retainによりバインドが禁止されている
- D. PVCで空のStorageClassを指定する必要がある

<details>
<summary>解答を表示</summary>

**解答: B. 適切なconsumerがまだスケジュールされていません。**

遅延バインディングでは、スケジューラーのトポロジー/リソース制約を配置に反映します。必ずしもストレージ障害ではありません。`spec.nodeName` を指定するとスケジューラーを迂回し、このバインディングフローを妨げる可能性があります。サポートされるスケジューリング制約を使ってください。StorageClassを変更したり、手動でボリュームを作ったりする前にイベントを確認します。

</details>

### 14. 互換性のあるCSIサポートのもとで、Podを1つに制限するアクセスモードはどれですか？

- A. ReadWriteOnce
- B. ReadWriteMany
- C. ReadOnlyMany
- D. ReadWriteOncePod

<details>
<summary>解答を表示</summary>

**解答: D. ReadWriteOncePod**

RWOは読み書きアタッチを1ノードに制限しますが、そのノード上では複数のPodが利用できます。RWOPは別の1 Podモードです。それでもアプリケーションの一貫性、バックアップ、認可の設計に代わるものではありません。同じクレームでRWOPと他のアクセスモードを組み合わせないでください。

</details>

### 15. 10 GiのEBS例をどう拡張し、復旧を確認すべきですか？

<details>
<summary>解答を表示</summary>

**解答: サポートされる拡張を許可し、PVCの要求容量を増やして、実際の容量を確認し、別の復元テストを行います。**

StorageClassのallowVolumeExpansionとドライバー/ファイルシステムのサポートを確認し、アプリケーション整合性を保つバックアップを取ってから、所有者を通じてクレームを拡張します。このデモの目標は20 Giです。ボリュームを縮小したり、サイズ変更を装うためにPV容量を書き換えたりしないでください。
```bash
set -euo pipefail
kubectl -n storage-demo get pvc ebs-claim -o yaml
kubectl -n storage-demo patch pvc ebs-claim --type merge \
  -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
kubectl -n storage-demo describe pvc ebs-claim
```
PVCのconditions/status、マウント済みファイルシステム、アプリケーションI/Oを確認します。ファイルシステム拡張が保留中なら、文書化された再マウント/再起動手順に従います。スナップショットを新しいクレームに復元し、適切なconsumerからマウントして、既知のアプリケーションデータを検証してください。PVC要求容量を増やすことやスナップショットオブジェクトがreadyになることだけでは、データ復旧テストの完了になりません。

</details>

公式リファレンス: [EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)、[EFS CSI](https://docs.aws.amazon.com/eks/latest/userguide/efs-csi.html)、[Kubernetes PV](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)、[gp3仕様](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)、[PostgreSQLサポート](https://www.postgresql.org/support/versioning/)、[S3 Files](https://docs.aws.amazon.com/eks/latest/userguide/s3files-csi.html)。
