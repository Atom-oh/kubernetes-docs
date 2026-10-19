# NodePool の設定と最適化

> **サポート対象バージョン**: EKS Auto Mode GA（例示の基準バージョン: EKS 1.36）
> **最終更新日**: 2026年9月12日

この章では、AWS が管理するデフォルト設定、カスタム NodePool の制約、および AWS 固有の NodeClass API を区別して説明します。先に[はじめに](./01-getting-started.md)を完了し、意図したアカウントとコンテキストを使用してください。テンプレートを適用する前に、IAM ロール/プロファイル名とネットワークタグをすべて確認してください。ここに示す容量上限は例であり、設定によっては依然として高額なコストが発生する可能性があります。

NodePool の例は、リリース済み Karpenter 1.14.1 CRD の構造スキーマに照らして確認し、AWS 固有の NodeClass フィールドは AWS のドキュメントと照合しました。この確認では、Auto Mode の内部コントローラーのバージョンを特定できず、稼働中クラスターでの Admission や Ready 状態も検証していません。この監査ではノードをプロビジョニングしていません。

## 組み込み NodePool を理解する

有効にすると、Auto Mode は次の NodePool を提供します。これらは AWS が管理するため、管理対象の設定を編集せず、必要に応じてカスタム NodePool を作成してください。

| NodePool | アーキテクチャ | 容量とインスタンスタイプの選択 | 用途 |
|------|--------------|----------------------------------|---------|
| `general-purpose` | `amd64` | オンデマンド、C/M/R ファミリー、第 5 世代以降 | 汎用ワークロード |
| `system` | `amd64`、`arm64` | オンデマンド、C/M/R ファミリー、第 5 世代以降 | `CriticalAddonsOnly` を許容する、クラスターに不可欠なワークロード |

組み込みの general-purpose NodePool では Spot は**有効になっていません**。Spot や異なるアーキテクチャ/インスタンス制約が必要な場合は、カスタム NodePool を使用してください。Auto Mode はノードローカル DNS とサービスネットワーキング機能を提供するため、Auto Mode のみのクラスターでは、system NodePool に Pod を配置する目的だけで通常の CoreDNS/kube-proxy Pod を動かす必要はありません。混在クラスターでは、Auto Mode 以外のノード向けに従来の CoreDNS Deployment が引き続き必要です。

推測でデフォルト YAML を適用せず、実際の管理対象オブジェクトで中断設定と taint の詳細を確認してください。

```bash
kubectl --context "$CLUSTER_NAME" get nodepool general-purpose system -o yaml
kubectl --context "$CLUSTER_NAME" get nodeclass default -o yaml
```

AWS が `default` NodeClass を提供するには、少なくとも 1 つの組み込み NodePool を有効にする必要があります。両方を無効にする場合は独自の NodeClass を作成し、以下の参照先を変更してください。`computeConfig.nodePools` から組み込み NodePool 名を削除すると、その NodePool とノードが削除され、ノードは drain/terminate されます。これは新しいワークロードに対して表示されなくなるだけではありません。

## カスタム NodePool を作成する

以下の例では、スケジューリング制約に焦点を当てるため既存の `default` NodeClass を参照します。この章の後半でカスタム NodeClass を使う場合は、先に作成してから、対象 NodePool の `nodeClassRef.name` を変更してください。`template` 配下のすべてのラベルと taint は新しいノードに適用されます。NodePool の metadata だけに付けたラベルはノードには付きません。

### コンピュート最適化ワークロード

世代を指定する条件 `Gt ["6"]` は、第 7 世代以降を許可します。最新世代だけに絞る条件ではありません。この例では x86 の C ファミリーのオンデマンドインスタンスを許可し、メモリ最適化の例より高いプロビジョニング優先度をこの NodePool に設定します。

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

### メモリ最適化ワークロード

この例では、いずれのアーキテクチャでも R ファミリーの第 6 世代以降を許可します。スケジューラーが選択するアーキテクチャに、コンテナイメージとアプリケーション依存関係が対応している必要があります。

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

## AWS NodeClass を設定する

Auto Mode は `eks.amazonaws.com/v1` と kind `NodeClass` を使用します。フィールドはセルフマネージド AWS Karpenter の `EC2NodeClass` とは異なります。この API に `amiFamily`、`blockDeviceMappings`、任意のシェル `userData`、`metadataOptions` をコピーしないでください。AWS が管理する Bottlerocket バリアントは AWS が選択します。

以下を `custom-nodeclass.yaml` として保存し、例示用のプロファイルとセレクターの値を、確認済みのリソースに置き換えてください。`instanceProfile` が使えますが、その名前は `eks` で始まる必要があります。代わりに、ノード IAM ロール名を `role` に指定できます。`role` と `instanceProfile` は**必ずどちらか一方だけ**を指定してください。プロファイルに含まれるロールには、適切な Auto Mode の EKS アクセスエントリと権限が必要です。設定済みのロールを再利用する場合、アクセスエントリを重複して作成する必要はありません。新しいロールを使う場合は、AWS NodeClass リファレンスに記載されたアクセスエントリの手順に従ってください。

サブネットタグはリソースを選択するものであり、ルーティングや分離を実現するものではありません。VPC、AZ の利用可否、ルートテーブル、セキュリティグループのルールを確認してください。`associatePublicIPAddress: false` はパブリック IP の割り当てを防ぎますが、ノードには適切なアウトバウンド接続が引き続き必要です。

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

クラスターのロールが `spec.tags` に指定するカスタムキーを使ってリソースを作成・タグ付けできることを確認してください。NodeClass 自体が IAM 権限を付与するわけではありません。

`ephemeralStorage` は任意のブロックデバイスマッピングではなく、ノードのエフェメラルストレージを設定します。`100Gi`、3000 IOPS、125 MiB/s は例示値です。Auto Mode の現在のフィールド上限、インスタンスストレージの動作、コストを確認してください。カスタマー KMS の設定は `ephemeralStorage.kmsKeyID` に指定し、ノードのルート/データ **EBS** ボリュームに適用します。ローカル NVMe インスタンスストアの暗号化キーを選択したり、アプリケーション PVC の暗号化を設定したりするものではありません。

以前のブートストラップ例では `vm.max_map_count` を変更していました。現在サポートされている代替手段は `advancedCompute.kernel.sysctl` で、ノード起動時に適用されます。サポート対象のカーネル設定を変更すると、既存ノードに drift が検出され、置き換えの対象になります。シェルから即時にインプレース変更するものではありません。この設定を必要とするワークロードに限って使用し、中断時の動作も確認してください。

### 固定された IMDS セキュリティ設定

Auto Mode では IMDSv2 と hop limit 1 が強制され、NodeClass からこれらのデフォルトを変更することはできません。通常の hostNetwork を使わない Pod はこの経路で IMDS に到達できませんが、これがすべての Pod の分離を保証するわけではありません。`hostNetwork` によって到達性が変わります。アプリケーションから AWS にアクセスする際はワークロード ID を優先し、ノードメタデータに依存せず、リージョンなどの設定を明示的に指定してください。

### カスタマー KMS、CA バンドル、Pod ネットワーキングの分離

途中で切れた証明書をマニフェストに貼り付けないでください。この任意のジェネレーターは、確認済みの基本テンプレートを読み込み、承認済みの公開 PEM バンドルを検証して `certificateBundles[].data` に Base64 エンコードし、2 つ目の NodeClass 全体を生成します。Python 3 と PyYAML が必要です。`NODE_KMS_KEY_ARN` と `CA_BUNDLE_FILE` を設定し、前章で確認した `AWS_REGION`/`EXPECTED_ACCOUNT_ID` を引き継いでください。

CA 発行者、フィンガープリント、有効期間は個別に承認してください。以下の構文チェックだけでは、証明書の信頼性、KMS 権限、クラウドリソースの存在は確認できません。生成結果を適用する前に、キーのポリシー/IAM 権限付与と Pod ネットワークのタグ選択を確認してください。

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
| `ephemeralStorage.kmsKeyID` | ノードのルート/データ EBS ボリューム用のカスタマー管理キー。クラスターと同じリージョンのキーを使用します |
| `certificateBundles[].data` | ノードの信頼設定に使う Base64 エンコード済み証明書バンドル。すべてのアプリケーションのコンテナ信頼ストアが自動的に変更されるわけではありません |
| `podSubnetSelectorTerms` | この NodeClass が選択する個別の Pod サブネット |
| `podSecurityGroupSelectorTerms` | Pod ネットワーク用セキュリティグループ。Pod サブネットセレクターと併せて設定します |

Pod サブネットとセキュリティグループのセレクターは一緒に設定し、VPC/AZ のカバレッジが互換でなければなりません。この設定単位は NodeClass であり、namespace や ServiceAccount ごとではありません。host-network トラフィックはノードネットワークを使います。egress SNAT によって送信元アドレスや適用されるセキュリティグループが変わることもあります。すべてのトラフィックが分離されていると判断する前に、ルーティング、SNAT、Pod 密度への影響を確認してください。

## ワークロードと環境を分離する

### フロントエンドとバックエンドの NodePool

taint により、一致する toleration がない Pod はこれらのノードに配置されません。toleration はスケジューリングを許可するだけです。ワークロードを指定のノードで実行する必要がある場合は、selector または必須の affinity も追加してください。

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

たとえば、所有する `nodepool-lab` namespace を作成し、フロントエンドの配置を確認する Pod に selector と toleration の両方を指定します。

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

適用前に確認してください。この Pod によって課金対象のノードがプロビジョニングされる可能性があります。割り当てられたノード、Ready 状態、ノードラベルを確認し、その後 namespace からテスト Pod を削除してください。`NoSchedule` は実行中の Pod を退避させません。また、ラベルと taint だけでは、信頼されていないテナント同士のセキュリティ境界にはなりません。

### 開発用 NodePool

現在の AWS サポート対象インスタンス一覧には、M ファミリーだけでなく T ファミリーのバースト可能インスタンスも含まれます。以前の Auto Mode に関する想定だけを理由に T ファミリーを除外しないでください。Auto Mode は 1 CPU を超えるインスタンスを必要とし、nano/micro/small サイズは対象外です。リージョンでのインスタンスタイプの利用可否、CPU クレジットの動作、ワークロードへの適合性は引き続き確認してください。

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

## リソース上限、重み付け、検証

`limits.cpu` と `limits.memory` は NodePool 全体のリソースを上限設定します。ノード数の上限でも通貨建ての予算でもありません。GitOps で整数と文字列がずれるのを防ぐため、CPU 量は引用符で囲んでください。たとえば `memory: 4000Gi` は 4000 GiB（約 3.91 TiB）であり、ちょうど 4 TB ではありません。

Upstream Karpenter のドキュメントでは、急速なプロビジョニング中に結果整合性により上限を超える可能性があると説明されています。これらのフィールドによって即時の課金上限が実現すると約束しないでください。置き換えに備えた余裕を残し、使用量を監視して、管理環境での動作をテストしてください。

`weight` は、利用可能な NodePool 間のプロビジョニング優先度に影響します。Kubernetes スケジューラーでノードの優先度を上げたり、既存ワークロードを退避させたり、Pod の配置先 NodePool を強制したりするものではありません。ワークロードの制約を明示し、意図しない重複を避けてください。

```bash
# Validate against the target cluster's actual schemas; no object is persisted.
kubectl --context "$CLUSTER_NAME" apply --dry-run=server -f custom-nodeclass.yaml
kubectl --context "$CLUSTER_NAME" apply --dry-run=server -f secure-network-nodeclass.json
# After an approved apply, inspect conditions rather than assuming readiness.
kubectl --context "$CLUSTER_NAME" get nodeclasses,nodepools
kubectl --context "$CLUSTER_NAME" describe nodeclass secure-network-nodeclass
kubectl --context "$CLUSTER_NAME" get nodeclaims
```

サーバー側 dry-run では Admission を確認できますが、IAM、ネットワーク接続、プロビジョニング、ストレージ、アプリケーションの動作は証明できません。本番利用の前に、false/unknown を示す Ready 条件を解消し、管理されたワークロードで検証してください。

## 参考資料

- [組み込み NodePool](https://docs.aws.amazon.com/eks/latest/userguide/set-builtin-node-pools.html)
- [Auto Mode の NodePool フィールドとラベル](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Auto Mode の NodeClass 仕様](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [管理対象インスタンスタイプと IMDS の制約](https://docs.aws.amazon.com/eks/latest/userguide/automode-learn-instances.html)
- [Auto Mode のノードセキュリティ](https://docs.aws.amazon.com/whitepapers/latest/security-overview-amazon-eks-auto-mode/eks-auto-mode-data-plane.html)
- [Upstream Karpenter の NodePool 上限](https://karpenter.sh/docs/concepts/nodepools/)
- [Karpenter の重み付けプロビジョニング](https://karpenter.sh/docs/concepts/scheduling/#weighted-nodepools)
- [Node CA、KMS、ネットワーク機能](https://aws.amazon.com/blogs/containers/new-amazon-eks-auto-mode-features-for-enhanced-security-network-control-and-performance/)

< [前へ: はじめに](./01-getting-started.md) | [目次](./README.md) | [次へ: スケーリング動作](./03-scaling-behavior.md) >
