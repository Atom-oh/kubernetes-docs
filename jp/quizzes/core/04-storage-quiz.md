# ストレージクイズ

このクイズでは、Kubernetes のストレージ概念、ボリュームの種類、PersistentVolume、StorageClass などの理解を確認します。

## 選択問題

1. 通常の Pod が削除されて再作成されても、ライフサイクルが Pod から独立したアプリケーション用ストレージを提供するリソースはどれですか？
   - A) ConfigMap
   - B) Secret
   - C) PersistentVolume
   - D) emptyDir

<details>

<summary>解答を表示</summary>

**答え: C) PersistentVolume**

**解説:**
PersistentVolume (PV) は、クラスター管理者がプロビジョニングするか、StorageClass を用いて動的にプロビジョニングするクラスターのストレージです。Pod が再起動または削除されても PV のデータは保持されます。ConfigMap と Secret はそれぞれ設定データと機密情報を保存し、emptyDir は Pod の実行中だけ存在する一時ディレクトリです。
</details>

2. Kubernetes で PersistentVolume を要求するために使うリソースはどれですか？
   - A) VolumeRequest
   - B) PersistentVolumeClaim
   - C) StorageRequest
   - D) VolumeBinding

<details>

<summary>解答を表示</summary>

**答え: B) PersistentVolumeClaim**

**解説:**
PersistentVolumeClaim (PVC) は、ユーザーが PersistentVolume を要求するためのリソースです。PVC は、指定された容量とアクセスモードを持つストレージ要求を表します。Kubernetes は要件を満たす PV を見つけ、PVC とバインドします。
</details>

3. Kubernetes でボリュームを動的にプロビジョニングする際に使うリソースはどれですか？
   - A) VolumeProvisioner
   - B) StorageClass
   - C) DynamicVolume
   - D) AutoProvisioner

<details>

<summary>解答を表示</summary>

**答え: B) StorageClass**

**解説:**
StorageClass を使うと、管理者は提供するストレージのクラスを定義できます。各クラスは、サービスレベル、バックアップポリシー、またはクラスター管理者が定める任意のポリシーに対応できます。PVC の作成時に StorageClass を使って PV を動的にプロビジョニングできます。
</details>

4. 通常の Pod を削除すると、その Pod が参照していた別途作成済みの PVC も自動的に削除されますか？
   - A) Delete
   - B) Retain
   - C) Recycle
   - D) いいえ。別途作成した PVC は残る

<details>

<summary>解答を表示</summary>

**答え: D) いいえ。別途作成した PVC は残る**

**解説:**
別途作成した PVC は Pod に所有されていないため、その Pod を削除しても残ります。汎用エフェメラルボリュームの PVC は異なり、Pod に所有されて Pod とともにガベージコレクションされます。StatefulSet の `persistentVolumeClaimRetentionPolicy` は StatefulSet の削除時またはスケールダウン時にテンプレート由来の PVC を削除できます。その後のストレージのクリーンアップ方法は PV の reclaim policy で決まります。
</details>

5. 次のうち、PersistentVolume のアクセスモードではないものはどれですか？
   - A) ReadWriteOnce
   - B) ReadOnlyMany
   - C) ReadWriteMany
   - D) WriteOnlyMany

<details>

<summary>解答を表示</summary>

**答え: D) WriteOnlyMany**

**解説:**
Kubernetes の PersistentVolume アクセスモードは、ReadWriteOnce (RWO)、ReadOnlyMany (ROX)、ReadWriteMany (RWX)、ReadWriteOncePod (RWOP、CSI のみ) です。WriteOnlyMany というアクセスモードはありません。ReadWriteOnce は単一ノードでの読み書きマウント、ReadOnlyMany は複数ノードでの読み取り専用マウント、ReadWriteMany は複数ノードでの読み書きマウントを許可します。
</details>

6. ボリュームを削除せずにリソースを解放する PersistentVolume の Reclaim Policy はどれですか？
   - A) Delete
   - B) Retain
   - C) Recycle
   - D) Release

<details>

<summary>解答を表示</summary>

**答え: B) Retain**

**解説:**
Retain ポリシーは、PVC の削除後も PV とそのデータを保持します。ボリュームは「Released」状態になりますが、別の claim には利用できません。管理者がデータを手動でクリーンアップし、ボリュームを再利用可能にする必要があります。Delete ポリシーは PVC の削除時に PV と外部インフラストラクチャ (AWS EBS、GCE PD など) を削除します。Recycle ポリシーは非推奨であり、代わりに動的プロビジョニングを使用してください。
</details>

7. Kubernetes で一時ストレージを提供するボリュームタイプはどれですか？
   - A) hostPath
   - B) emptyDir
   - C) nfs
   - D) persistentVolumeClaim

<details>

<summary>解答を表示</summary>

**答え: B) emptyDir**

**解説:**
emptyDir ボリュームは Pod がノードに割り当てられたときに作成され、その Pod がそのノードで実行されている間だけ存在します。名前のとおり、最初は空です。Pod 内のすべてのコンテナは同じ emptyDir ボリューム内のファイルを読み書きできます。コンテナごとに同じパスまたは異なるパスへマウントできます。理由を問わず Pod がノードから取り除かれると、emptyDir のデータは完全に削除されます。
</details>

8. EKS Auto Mode ではない標準の Amazon EBS CSI ドライバーを示す provisioner はどれですか？
   - A) ebs.csi.aws.com
   - B) kubernetes.io/gce-pd
   - C) kubernetes.io/azure-disk
   - D) kubernetes.io/nfs

<details>

<summary>解答を表示</summary>

**答え: A) ebs.csi.aws.com**

**解説:**
標準の EBS CSI ドライバーでは `ebs.csi.aws.com` を使います。ドライバーと IAM 権限をインストール／設定する必要があります。クラスターに適切なデフォルト StorageClass が自動的に存在するとは限りません。EKS Auto Mode では `ebs.csi.eks.amazonaws.com` を使います。新しい例では、従来のインツリー provisioner を使わないでください。
</details>

9. StatefulSet のボリューム要求テンプレートに使う正しいフィールド名はどれですか？
   - A) volumeClaimTemplate
   - B) persistentVolumeClaimTemplate
   - C) volumeClaimTemplates
   - D) persistentVolumeClaimTemplates

<details>

<summary>解答を表示</summary>

**答え: C) volumeClaimTemplates**

**解説:**
StatefulSet は `volumeClaimTemplates` フィールドを使い、各 Pod 用の PVC を自動作成します。このテンプレートから StatefulSet の各レプリカ用の PVC が作られます。作成される PVC 名は `<volume-claim-template-name>-<pod-name>` の形式です。
</details>

10. Kubernetes における CSI (Container Storage Interface) の主な目的は何ですか？
    - A) コンテナ間の通信を標準化する
    - B) Kubernetes のコードベース外でストレージドライバーを開発できるようにする
    - C) コンテナイメージレジストリへのアクセスを標準化する
    - D) クラウドプロバイダー間のストレージ移行を自動化する

<details>

<summary>解答を表示</summary>

**答え: B) Kubernetes のコードベース外でストレージドライバーを開発できるようにする**

**解説:**
CSI (Container Storage Interface) は、コンテナオーケストレーションシステム (Kubernetes など) とストレージプロバイダー間の標準インターフェイスを定義します。主な目的は、ストレージドライバーの開発、デプロイ、管理を Kubernetes のコードベース外で行えるようにすることです。これにより、ストレージプロバイダーは Kubernetes のリリースサイクルから独立してプラグインを開発、保守できます。
</details>

## 応用問題

1. CSI (Container Storage Interface) ドライバーを使って Kubernetes に新しいストレージ種別を統合する方法と、その利点を説明してください。

<details>

<summary>解答を表示</summary>

**答え:**

**CSI ドライバーの導入方法:**

1. **CSI ドライバーをデプロイする**: CSI ドライバーは通常、次のコンポーネントで構成されます。
  - **Node Plugin DaemonSet**: 各ノードで実行され、ボリュームのマウント／アンマウントを行います。
  - **Controller Plugin Deployment/StatefulSet**: ボリュームの作成／削除／スナップショット操作を行います。
  - **RBAC リソース**: 必要な権限を設定します。

2. **StorageClass を作成する**: CSI ドライバーを使う StorageClass を定義します。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: csi-storage
provisioner: example.csi.k8s.io  # CSI driver name
parameters:
  # Driver-specific parameters
  type: ssd
  fsType: ext4
```

3. **CSI Volume Snapshot 対応を構成する** (任意):

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: csi-snapshot-class
driver: example.csi.k8s.io
deletionPolicy: Delete
```

4. **CSI ドライバーをテストする**: PVC を作成し、Pod にマウントして機能を確認します。

**CSI を使う利点:**

1. **独立した開発サイクル**: ストレージプロバイダーは Kubernetes のリリースサイクルから独立してドライバーを開発、デプロイできます。

2. **標準化されたインターフェイス**: CSI はコンテナオーケストレーションシステムとストレージプロバイダー間に標準インターフェイスを提供します。

3. **高度なストレージ機能**: ボリュームスナップショット、クローン、サイズ変更などの機能を標準化された方法でサポートします。

4. **セキュリティの強化**: Controller 側の IAM/RBAC 権限を必要な操作に限定します。CSI の Node Plugin はボリュームのマウントに特権付きのホストアクセスを必要とすることが多いため、その権限は別途確認してください。

5. **多様なストレージの選択肢**: クラウドプロバイダー、オープンソース、商用のストレージソリューションを簡単に統合できます。

6. **プラグインアーキテクチャ**: CSI ドライバーは必要に応じて追加、削除できます。

**実環境での導入例 (AWS EBS CSI Driver):**

```bash
# First install the EKS EBS CSI add-on with its IAM role using the official guide.
# Snapshot support additionally needs snapshot CRDs and the snapshot controller.

# Create StorageClass
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-sc
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  encrypted: "true"
EOF
```

CSI は Kubernetes ストレージエコシステムの中核であり、さまざまなストレージソリューションの統合と高度なストレージ機能の利用を可能にします。
</details>

2. StatefulSet と永続ストレージを使って高可用性データベースクラスターを設計してください。Kubernetes の責任範囲とデータベースのレプリケーションを区別し、バックアップと復旧の要件を説明してください。

<details>
<summary>解答を表示</summary>

**答え:**

1. 安定した Pod ID、headless Service、データベースメンバーごとの PVC を使用します。メンバーを複数のノード／ゾーンに分散します。各 EBS ボリュームは 1 つの Availability Zone に属するため、別のゾーンで復旧するには、復元済みボリュームまたはデータベースレプリケーションが必要です。
2. データベース Operator または独立して検証済みのレプリケーションシステムを構成し、一意のサーバー ID、初期データ同期、プライマリ選出、フェンシング、レプリケーション認証情報、クライアントのルーティングを扱います。StatefulSet のレプリカを 3 つにしただけでは、高可用性データベースにはなりません。
3. `ebs.csi.aws.com` を使って暗号化 EBS ボリュームをプロビジョニングし、`WaitForFirstConsumer`、適切な gp3 `iops` 値、意図的に選んだ reclaim policy を設定します。`Retain` は claim の削除後も基盤ストレージを保持しますが、バックアップではなく、あらゆる削除経路を防ぐものでもありません。
4. ConfigMap は `${HOSTNAME##*-}` のようなシェル式を展開しません。init container でインスタンスごとの設定を生成し、MySQL の起動後に SQL を実行します。exec probe はシェルを介さない限り `${VARIABLE}` を展開しません。
5. CSI スナップショットには snapshot CRD／controller をインストールし、EBS `VolumeSnapshotClass` を使います。一貫性のある復旧時点を得るため、書き込みを静止させるかデータベース対応バックアップを使い、復元時のサイズとドライバーの互換性を確認します。
6. 論理バックアップでは、互換性のあるデータベースツールとアップロードツールを含むイメージを使います (標準の MySQL イメージには AWS CLI が含まれません)。専用のデータベースバックアップユーザーと、範囲を絞った AWS ID を使います。dump／upload に失敗したら Job を失敗させ、成功したバックアップを Pod の外部に保持して、復元をテストします。Job 履歴の保持はバックアップファイルを保持しません。
7. レプリケーション遅延、ストレージ使用量、バックアップの経過時間／失敗、復元テストを監視します。目標復旧時点と目標復旧時間を文書化し、ノード障害とゾーン障害時のフェイルオーバーをテストします。

[EBS CSI のインストールガイド](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html) と、この章のスナップショット／保持の例を参照してください。

</details>

## まとめ

このクイズでは、Kubernetes のストレージ概念を確認しました。PersistentVolume、PersistentVolumeClaim、StorageClass、ボリュームの種類、アクセスモード、reclaim policy を扱いました。また、EKS のストレージ構成、CSI ドライバー、ボリュームスナップショットなどの応用事項も学びました。これらの概念を理解して活用することで、Kubernetes 上で信頼性と拡張性の高いストレージソリューションを構築できます。
