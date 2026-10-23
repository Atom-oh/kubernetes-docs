# NodePool の構成と最適化

> **サポート対象バージョン**: EKS Auto Mode GA、ベースライン例は EKS 1.36  
> **最終更新日**: 2026年10月21日

この章では、AWS が管理するデフォルト、カスタム NodePool の制約、AWS 固有の NodeClass API の違いを説明します。まず[はじめに](./01-getting-started.md)を完了し、意図したアカウントとコンテキストを使用してください。テンプレートを適用する前に、すべての IAM ロール名とインスタンスプロファイル名、ネットワークタグを確認してください。ここに示す容量上限は説明用の例であり、それでも多額のコストが発生する可能性があります。

NodePool の例は、リリース済み Karpenter 1.14.1 CRD の構造スキーマに照らして確認し、AWS 固有の NodeClass フィールドは AWS のドキュメントと比較しました。これによって Auto Mode の内部コントローラーのバージョンが特定されるわけではなく、稼働中のクラスターでの受付や準備完了が証明されるわけでもありません。この監査ではノードをプロビジョニングしていません。

## 組み込み NodePool を理解する

有効にすると、Auto Mode は次のプールを提供します。これらは AWS が管理するため、管理対象の設定を編集するのではなく、カスタムプールを作成してください。

| プール | アーキテクチャ | 容量とインスタンスの選択 | 用途 |
|------|--------------|----------------------------------|---------|
| `general-purpose` | `amd64` | オンデマンド、C/M/R ファミリー、第 5 世代以降 | 一般的なワークロード |
| `system` | `amd64` および `arm64` | オンデマンド、C/M/R ファミリー、第 5 世代以降 | `CriticalAddonsOnly` を許容する、クラスターに不可欠なワークロード |

組み込みの汎用プールでは Spot は**有効になっていません**。Spot や異なるアーキテクチャ／インスタンス制約が必要な場合は、カスタムプールを使用してください。Auto Mode はノードローカル DNS とサービスネットワーキング機能を提供するため、純粋な Auto Mode クラスターでは、system プールを構成するだけの目的で通常の CoreDNS/kube-proxy Pod を用意する必要はありません。混在クラスターでは、Auto Mode 以外のノード向けに従来の CoreDNS Deployment が引き続き必要です。

推測に基づくデフォルト YAML を適用するのではなく、実際の管理対象オブジェクトを調べて、障害発生時の設定と taint の詳細を確認してください。

```bash
kubectl --context "$CLUSTER_NAME" get nodepool general-purpose system -o yaml
kubectl --context "$CLUSTER_NAME" get nodeclass default -o yaml
```

AWS が `default` NodeClass を提供するには、少なくとも 1 つの組み込みプールを有効にする必要があります。両方とも無効にする場合は、独自の NodeClass を作成し、以下の参照先を更新してください。`computeConfig.nodePools` から組み込みプール名を削除すると、そのプールが削除され、プールのノードはドレイン後に終了します。新しいワークロードからプールを見えなくするだけではありません。

## カスタム NodePool を作成する

これらの例では、スケジューリング制約に焦点を当てるため、既存の `default` NodeClass を参照しています。この章の後半で説明するカスタム NodeClass を使用するには、先にそれを作成し、対象のプールにある `nodeClassRef.name` を変更してください。`template` 配下のすべてのラベルと taint は新しいノードに適用されます。NodePool のメタデータにだけ設定したラベルは、ノードには設定されません。

### コンピューティング最適化ワークロード

世代の条件 `Gt ["6"]` は第 7 世代以降を許可します。最新世代だけを選択する条件ではありません。この例では、x86 C ファミリーのオンデマンドインスタンスを許可し、メモリー最適化の例よりもこのプールのプロビジョニング優先度を高くしています。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: compute-optimized
  labels:
    workload-type: compute-intensive
spec:
  template:
    metadata:
      labels:
        workload-type: compute-intensive
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - c
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '6'
      - key: eks.amazonaws.com/instance-size
        operator: In
        values:
        - xlarge
        - 2xlarge
        - 4xlarge
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: '1000'
    memory: 4000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
  weight: 10
```

### メモリー最適化ワークロード

この例では、どちらのアーキテクチャでも第 6 世代以降の R ファミリーを許可します。スケジューラーが選択するアーキテクチャに、コンテナイメージとアプリケーションの依存関係が対応している必要があります。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: memory-optimized
  labels:
    workload-type: memory-intensive
spec:
  template:
    metadata:
      labels:
        workload-type: memory-intensive
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - r
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '5'
      - key: eks.amazonaws.com/instance-size
        operator: In
        values:
        - 2xlarge
        - 4xlarge
        - 8xlarge
        - 12xlarge
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: '500'
    memory: 8000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
  weight: 5
```

## AWS NodeClass を構成する

Auto Mode は `eks.amazonaws.com/v1`、kind `NodeClass` を使用します。そのフィールドは、セルフマネージドの AWS Karpenter `EC2NodeClass` とは異なります。この API に `amiFamily`、`blockDeviceMappings`、任意のシェル `userData`、`metadataOptions` をコピーしないでください。AWS が管理する Bottlerocket のバリアントが選択されます。

以下を `custom-nodeclass.yaml` として保存し、説明用のプロファイルとセレクターの値を確認済みのリソースに置き換えてください。`instanceProfile` がサポートされています。その名前は `eks` で始まる必要があります。代わりに `role` にノード IAM ロール名を設定することもできます。**`role` または `instanceProfile` のどちらか一方だけを指定してください。プロファイルに含まれるロールには**、適切な Auto Mode EKS アクセスエントリーと権限が必要です。設定済みのロールを再利用する場合、エントリーを重複して追加する必要はありません。新しいロールを使用する場合は、AWS NodeClass リファレンスに記載されているアクセスエントリーの手順に従ってください。

サブネットタグはリソースを選択するものであり、ルーティングや分離を確立するものではありません。VPC、AZ の利用可能性、ルートテーブル、セキュリティグループのルールを確認してください。`associatePublicIPAddress: false` はパブリック IP の割り当てを防ぎますが、ノードには引き続き適切なアウトバウンド接続が必要です。

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: custom-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      kubernetes.io/role/internal-elb: '1'
      Environment: production
  securityGroupSelectorTerms:
  - tags:
      kubernetes.io/cluster/my-cluster: owned
      Type: worker-node
  ephemeralStorage:
    size: 100Gi
    iops: 3000
    throughput: 125
  advancedNetworking:
    associatePublicIPAddress: false
  advancedCompute:
    kernel:
      sysctl:
        vm.max_map_count: 262144
  tags:
    Environment: production
    ManagedBy: eks-auto-mode
```

クラスターのロールが、`spec.tags` に設定したカスタムキーを使ってリソースを作成し、タグ付けできることを確認してください。NodeClass 自体が IAM 権限を付与するわけではありません。

`ephemeralStorage` はノードのエフェメラルストレージを構成するものであり、任意のブロックデバイスマッピングを設定するものではありません。`100Gi` のサイズと 3000 IOPS／125 MiB/s の設定は例です。現在の Auto Mode のフィールド制限、インスタンスストレージの動作、コストを確認してください。カスタマー KMS の設定は `ephemeralStorage.kmsKeyID` に指定し、ノードのルート／データ **EBS** ボリュームに適用します。ローカル NVMe インスタンスストアの暗号化に使用するキーを選択するものでも、アプリケーションの PVC の暗号化を設定するものでもありません。

以前のブートストラップ例では `vm.max_map_count` を変更していました。サポートされる代替手段は `advancedCompute.kernel.sysctl` で、ノードの起動時に適用されます。サポートされるカーネル設定を変更すると、既存ノードにはドリフトがマークされ、置き換えの対象になります。シェルから実行中のノードを即時にその場で更新する方法ではありません。この設定が必要なワークロードに限って構成し、障害発生時の動作を確認してください。

### Kubelet 設定

Auto Mode は独自の kubelet デフォルトを適用します。ワークロードで Pod 密度、退避、ログローテーション、OOM の動作を変える必要がある場合に限り、`spec.advancedCompute.kubelet` で上書きしてください。以下は AWS がドキュメント化している上書き設定の全項目です。セルフマネージドの Karpenter `EC2NodeClass` の `spec.kubelet` フィールドのうち、ここに記載されていないもの（例: `kubeReserved`、`systemReserved`、`clusterDNS`、`podsPerCore`、イメージ GC のしきい値）は Auto Mode NodeClass では公開されていません。

以下を `kubelet-nodeclass.yaml` として保存してください。値は説明用の例であり、推奨値ではありません。前の例と同様に、識別情報とセレクターの値を確認済みのリソースに置き換えてください。

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: kubelet-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      kubernetes.io/role/internal-elb: '1'
      Environment: production
  securityGroupSelectorTerms:
  - tags:
      kubernetes.io/cluster/my-cluster: owned
      Type: worker-node
  advancedCompute:
    kernel:
      sysctl:
        user.max_user_namespaces: 65536   # required because idsPerPod is set below
    kubelet:
      maxPods: 60
      podPidsLimit: 4096
      idsPerPod: 65536
      singleProcessOOMKill: false
      eviction:
        hard:
          memory.available: 100Mi
          nodefs.available: 10%
        soft:
          memory.available: 500Mi
          nodefs.available: 15%
        softGracePeriod:                  # required for every soft signal
          memory.available: 1m30s
          nodefs.available: 2m
        maxPodGracePeriod: 60
      logging:
        containerLogMaxSize: 10Mi
        containerLogMaxFiles: 5
      allowedUnsafeSysctls:
      - net.core.somaxconn
```

| フィールド | 意味 | 制約 |
|-------|---------|------------|
| `maxPods` | ノードあたりの Pod 数の上限 | 1～110。この設定値、インスタンスタイプで供給可能な IP アドレス数、Auto Mode の上限 110 のうち、最も小さい値が実効値 |
| `podPidsLimit` | Pod あたりのプロセス ID の最大数 | `-1` は上限を無効にします。それ以外は 100 以上が必要です（0～99 は拒否されます） |
| `idsPerPod` | kubelet が各 Pod のユーザー名前空間に割り当てる UID と GID | 65536～4294967295 の範囲で 65536 の倍数。同じ NodeClass の `advancedCompute.kernel.sysctl.user.max_user_namespaces` を 0 より大きくする必要があります |
| `singleProcessOOMKill` | OOM 時に、コンテナ内のプロセスをグループ単位ではなく一度に 1 つずつ終了させる | Kubernetes 1.32 以降が必要です。それより前のバージョンでは効果がなく、EKS は NodeClass に警告イベントを出力します |
| `eviction.hard` / `eviction.soft` | シグナルごとの退避しきい値。数量（`500Mi`）またはパーセンテージ（`10%`）で指定 | シグナル: `memory.available`、`nodefs.available`、`nodefs.inodesFree`、`imagefs.available`、`imagefs.inodesFree`、`pid.available` |
| `eviction.softGracePeriod` | ソフトしきい値が退避開始前に継続する必要がある時間 | ソフトしきい値を設定する各シグナルに必須 |
| `eviction.maxPodGracePeriod` | ソフトしきい値で退避される Pod の終了猶予期間の上限（秒） | `0` の場合、各 Pod の `terminationGracePeriodSeconds` を使用 |
| `logging.containerLogMaxSize` / `logging.containerLogMaxFiles` | コンテナログのローテーションサイズと保持するファイル数 | `containerLogMaxFiles` は 2 以上 |
| `allowedUnsafeSysctls` | ノード上の Pod が設定できる unsafe sysctl、または `*` で終わるパターン | 最大 64 項目。許可されるパターンは `kernel.shm*`、`kernel.msg*`、`kernel.sem`、`fs.mqueue.*`、`net.*` |

本番 NodeClass を変更する前に、次の動作を確認してください。

- **ノードはパッチ適用ではなく置き換えられます**。既存の NodeClass の kubelet 設定を変更すると、そのノードにドリフトがマークされ、EKS は新しい設定を使うノードに置き換えます。実行中のノードに設定がその場で適用されることはないため、先に障害予算と PDB を確認してください。
- **`maxPods` は上限値です。設定値がそのまま適用されると想定せず**、`kubectl get node <node> -o jsonpath='{.status.capacity.pods}'` を使って置き換え後のノードで結果を確認してください。
- **ソフトしきい値はハードしきい値より先に退避を発生させる必要があります**。同じシグナルのソフトしきい値は、ハードしきい値よりも制限が緩くなければなりません。数量とパーセンテージは混在できます。EKS はインスタンスタイプごとに両方を評価し、このルールに違反するインスタンスタイプを NodeClass と互換性がないものとして扱います。
- **`allowedUnsafeSysctls` は許可するだけです。ノード上の** Pod が sysctl を要求できるようにする設定であり、各 Pod でも `securityContext.sysctls` にその sysctl を記載する必要があります。ノードレベルのカーネル値は別途 `advancedCompute.kernel.sysctl` で設定します。

### 固定された IMDS セキュリティ設定

Auto Mode は IMDSv2 とホップ制限 1 を強制します。NodeClass からこれらのデフォルトを変更することはできません。通常の hostNetwork ではない Pod はこの経路で IMDS にアクセスできませんが、これがすべての Pod に対する隔離を保証するわけではありません。`hostNetwork` によって到達可能性が変わります。アプリケーションから AWS にアクセスする場合はワークロード ID を優先し、ノードメタデータに依存するのではなく、リージョンなどの設定を明示的に指定してください。

### カスタマー KMS、CA バンドル、個別の Pod ネットワーキング

途中で切れた証明書をマニフェストに貼り付けないでください。この任意の生成スクリプトは、確認済みの基本テンプレートを読み込み、承認済みのパブリック PEM バンドルを検証し、`certificateBundles[].data` に Base64 エンコードして、2 つ目の NodeClass を完全な形で生成します。実行には PyYAML を含む Python 3 が必要です。`NODE_KMS_KEY_ARN` と `CA_BUNDLE_FILE` を設定し、前の章で確認した `AWS_REGION`／`EXPECTED_ACCOUNT_ID` を引き続き使用してください。

CA の発行元、フィンガープリント、有効期間は別途承認してください。以下の構文チェックでは、信頼性、KMS 権限、クラウドリソースの存在は確認できません。適用する前に、キーのポリシーと IAM の許可、Pod ネットワークのタグ選択を確認してください。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the reviewed cluster region}"
: "${EXPECTED_ACCOUNT_ID:?Set the intended AWS account}"
: "${NODE_KMS_KEY_ARN:?Set the approved same-region customer-managed KMS key ARN}"
: "${CA_BUNDLE_FILE:?Set the path to an approved public CA PEM bundle}"
export AWS_REGION EXPECTED_ACCOUNT_ID NODE_KMS_KEY_ARN CA_BUNDLE_FILE
umask 077
python3 - <<'PY'
import base64, json, os, re, ssl
from pathlib import Path
import yaml

doc = yaml.safe_load(Path("custom-nodeclass.yaml").read_text())
if doc.get("kind") != "NodeClass" or doc.get("apiVersion") != "eks.amazonaws.com/v1":
    raise SystemExit("Expected the reviewed Auto Mode NodeClass template")
spec = doc["spec"]
if ("role" in spec) == ("instanceProfile" in spec):
    raise SystemExit("Set exactly one reviewed role or instanceProfile")
key = os.environ["NODE_KMS_KEY_ARN"]
prefix = "arn:aws:kms:" + os.environ["AWS_REGION"] + ":" + os.environ["EXPECTED_ACCOUNT_ID"] + ":key/"
if not key.startswith(prefix) or not re.fullmatch(r"(?:[a-f0-9-]{36}|mrk-[a-f0-9]{32})", key[len(prefix):]):
    raise SystemExit("KMS key ARN must match the reviewed account and region")
pem = Path(os.environ["CA_BUNDLE_FILE"]).read_bytes()
if b"PRIVATE KEY" in pem:
    raise SystemExit("Use public CA certificates only, never a private key")
ssl.create_default_context().load_verify_locations(cadata=pem.decode("ascii"))
doc["metadata"]["name"] = "secure-network-nodeclass"
spec["ephemeralStorage"]["kmsKeyID"] = key
spec["certificateBundles"] = [{"name": "corporate-ca",
                               "data": base64.b64encode(pem).decode("ascii")}]
spec["podSubnetSelectorTerms"] = [{"tags": {"Purpose": "pod-network"}}]
spec["podSecurityGroupSelectorTerms"] = [{"tags": {"Purpose": "pod-network"}}]
Path("secure-network-nodeclass.json").write_text(json.dumps(doc, indent=2) + "\n")
PY
```

| フィールド | 意味 |
|-------|---------|
| `ephemeralStorage.kmsKeyID` | ノードのルート／データ EBS ボリュームに使用するカスタマー管理キー。クラスターと同じリージョンのキーを使用 |
| `certificateBundles[].data` | ノードの信頼ストア用に Base64 エンコードされた証明書バンドル。すべてのアプリケーションのコンテナ信頼ストアが自動的に変更されるわけではありません |
| `podSubnetSelectorTerms` | この NodeClass 用に選択する個別の Pod サブネット |
| `podSecurityGroupSelectorTerms` | Pod ネットワークのセキュリティグループ。Pod サブネットセレクターと組み合わせて構成 |

Pod サブネットとセキュリティグループのセレクターは、互換性のある VPC/AZ の範囲を確保したうえで、両方を設定する必要があります。この構成は NodeClass 単位であり、namespace や ServiceAccount 単位ではありません。host-network のトラフィックはノードのネットワーキングを使用します。また、送信 SNAT によって送信元アドレスと適用されるセキュリティグループが変わる場合があります。すべてのトラフィックが分離されると主張する前に、ルーティング、SNAT、Pod 密度への影響を確認してください。

## ワークロードと環境を分離する

### フロントエンドとバックエンドのプール

taint によって、対応する toleration のない Pod がこれらのノードに配置されないようにします。toleration はスケジューリングを許可するだけです。ワークロードを指定したノードで実行する必要がある場合は、セレクターまたは必須アフィニティも追加してください。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: frontend
spec:
  template:
    metadata:
      labels:
        workload-tier: frontend
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
        - on-demand
      taints:
      - key: workload-tier
        value: frontend
        effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  weight: 10
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: backend
spec:
  template:
    metadata:
      labels:
        workload-tier: backend
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - r
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      taints:
      - key: workload-tier
        value: backend
        effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  weight: 10
  limits:
    cpu: '100'
    memory: 800Gi
```

たとえば、管理対象の `nodepool-lab` namespace を作成し、フロントエンドへの配置を確認する Pod にセレクターと toleration の両方を設定します。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend-placement-check
  namespace: nodepool-lab
spec:
  automountServiceAccountToken: false
  nodeSelector:
    workload-tier: frontend
  tolerations:
  - key: workload-tier
    operator: Equal
    value: frontend
    effect: NoSchedule
  containers:
  - name: nginx
    image: nginx:1.30.6
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
    readinessProbe:
      httpGet:
        path: /
        port: 80
      periodSeconds: 5
```

適用前に確認してください。この Pod によって課金対象のノードがプロビジョニングされる可能性があります。割り当てられたノード、準備状態、ノードラベルを確認したら、その namespace からテスト Pod を削除してください。`NoSchedule` は、すでに実行中の Pod を退避させません。また、ラベルと taint だけでは、信頼されていないテナント間のセキュリティ境界にはなりません。

### 開発用プール

現在の AWS 対応インスタンスタイプ一覧には、M ファミリーに加えて、バースト可能な T ファミリーも含まれています。古い Auto Mode の想定だけを根拠に T を除外しないでください。Auto Mode では 1 CPU より多い CPU が必要で、nano／micro／small サイズは除外されます。それでも、リージョンでのインスタンスタイプの提供状況、CPU クレジットの動作、ワークロードへの適合性を確認してください。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: dev-pool
spec:
  template:
    metadata:
      labels:
        environment: development
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - t
        - m
      - key: eks.amazonaws.com/instance-size
        operator: In
        values:
        - medium
        - large
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      taints:
      - key: environment
        value: development
        effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: '100'
    memory: 400Gi
  weight: 1
```

## リソース上限、重み、検証

`limits.cpu` と `limits.memory` はプール全体のリソース上限であり、ノード数の上限でも通貨建ての予算でもありません。CPU の値は引用符で囲み、GitOps における整数と文字列のドリフトを防いでください。たとえば、`memory: 4000Gi` は 4000 GiB（約 3.91 TiB）であり、正確に 4 TB という意味ではありません。

上流の Karpenter ドキュメントでは、結果整合性と、急速なプロビジョニング中に上限を超過する可能性が説明されています。これらのフィールドによって請求額が瞬時に上限内に収まると約束しないでください。置き換え用の余裕を確保し、使用量を監視し、管理環境での動作をテストしてください。

`weight` は、条件を満たすプール間のプロビジョニング優先度に影響します。ノードの Kubernetes スケジューラー優先度を高めたり、既存のワークロードを退避させたり、Pod に特定のプールを強制的に使用させたりするものではありません。ワークロードの制約を明示し、意図しない適用条件の重複を避けてください。

```bash
# Validate against the target cluster's actual schemas; no object is persisted.
kubectl --context "$CLUSTER_NAME" apply --dry-run=server -f custom-nodeclass.yaml
kubectl --context "$CLUSTER_NAME" apply --dry-run=server -f secure-network-nodeclass.json
# After an approved apply, inspect conditions rather than assuming readiness.
kubectl --context "$CLUSTER_NAME" get nodeclasses,nodepools
kubectl --context "$CLUSTER_NAME" describe nodeclass secure-network-nodeclass
kubectl --context "$CLUSTER_NAME" get nodeclaims
```

サーバー側の dry-run では受付の可否を確認できますが、IAM、ネットワーク接続、プロビジョニング、ストレージ、アプリケーションの動作は証明できません。準備状態が False または Unknown の条件を解消し、本番で使用する前に、制御されたワークロードで検証してください。

## 参考資料

- [組み込み NodePool](https://docs.aws.amazon.com/eks/latest/userguide/set-builtin-node-pools.html)
- [Auto Mode の NodePool フィールドとラベル](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Auto Mode NodeClass の仕様](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [管理対象インスタンスタイプと IMDS の制限](https://docs.aws.amazon.com/eks/latest/userguide/automode-learn-instances.html)
- [Auto Mode のノードセキュリティ](https://docs.aws.amazon.com/whitepapers/latest/security-overview-amazon-eks-auto-mode/eks-auto-mode-data-plane.html)
- [上流 Karpenter の NodePool 上限](https://karpenter.sh/docs/concepts/nodepools/)
- [Karpenter の重み付けプロビジョニング](https://karpenter.sh/docs/concepts/scheduling/#weighted-nodepools)
- [ノード CA、KMS、ネットワーク機能](https://aws.amazon.com/blogs/containers/new-amazon-eks-auto-mode-features-for-enhanced-security-network-control-and-performance/)

< [前へ: はじめに](./01-getting-started.md) | [目次](./README.md) | [次へ: スケーリングの動作](./03-scaling-behavior.md) >
