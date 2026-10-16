# Karpenter

> **対応バージョン**: Karpenter 1.14 LTS（例: 1.14.1）。互換性およびプロバイダーサポート表を使用して Kubernetes/EKS バージョンを選択してください。
> **最終更新**: October 12, 2026

## 目次
- [概要](#introduction)
- [アーキテクチャ](#architecture)
- [インストールと設定](#installation-and-configuration)
- [NodePool](#nodepool)
- [Node Classes](#node-classes)
- [中断処理](#interruption-handling)
- [統合](#integration)
- [Amazon EKS との統合](#integration-with-amazon-eks)
- [ベストプラクティス](#best-practices)
- [トラブルシューティング](#troubleshooting)
- [まとめ](#conclusion)

## 概要

Karpenter はオープンソースのノードオートスケーラーです。この章では、その AWS プロバイダーを使用して、互換性のある Kubernetes ワークロード用に EC2 キャパシティをプロビジョニングします。可用性と効率性は、制約、クラウドキャパシティ、ノード初期化、およびアプリケーション設計に依存します。

### Karpenter の主な利点

1. **迅速なスケーリング**: スケジュール不能なワークロード需要に応じてプロビジョニングを開始します。ノードとアプリケーションの Ready 状態に固定のレイテンシ保証はありません。
2. **コスト最適化**: ワークロードに最も適したインスタンスタイプの選択
3. **シンプルな設定**: 宣言的 API による容易な設定
4. **ワークロード中心の設計**: Pod 要件に基づくノードプロビジョニング
5. **クラウド統合**: クラウドプロバイダーの機能を活用
6. **効率的な Bin Packing**: リソース使用率を最適化
7. **柔軟なノード管理**: ノードライフサイクル管理と統合された中断処理

### 既存のオートスケーラーとの比較

| 機能 | Karpenter | Cluster Autoscaler | クラウドプロバイダー管理 Node Groups |
|---------|-----------|-------------------|---------------------------|
| スケーリング速度 | スケジューリング、EC2 キャパシティ、初期化に依存 | Node Group のスケーリングと初期化に依存 | スケーリングポリシー、キャパシティ、初期化に依存 |
| インスタンスタイプの選択 | 動的 | Node Group ベース | Node Group ベース |
| Bin Packing 効率 | ワークロード/制約に依存 | ワークロード/Node Group に依存 | scheduler とスケーリングコントローラーに依存 |
| 設定の複雑さ | 低 | 中 | 低 |
| クラウド統合 | プロバイダー固有の実装 | 複数のクラウドプロバイダー統合 | プロバイダーネイティブ |
| Node Group 管理 | 不要 | 必要 | 必要 |
| 中断処理 | 設定済みイベント処理とノードライフサイクル | プラットフォーム/統合に依存 | プラットフォーム固有の処理 |

> **注記**: EKS は 2026 年 4 月 8 日に Managed Node Group の warm-pool サポートを追加しました。事前初期化済みインスタンスは繰り返し行う初期化作業を減らせます。Stopped モードと Running モードでは遷移時間とコストが異なり、スケールイン時の再利用は任意です。AWS によると、Cluster Autoscaler 統合には追加設定は不要です。再開、ノードの Ready 状態、およびアプリケーション起動には依然として時間がかかります。これは EKS Managed Node Group/Auto Scaling の機能であり、Karpenter 管理プールではありません。

## アーキテクチャ

Karpenter は Kubernetes コントローラーとして動作し、スケジュール不能な Pod を検出して適切なノードをプロビジョニングします。

![Kubernetes クラスター内の Karpenter コントローラーがスケジュール不能な Pod を監視し、CEL で検証された NodePool および EC2NodeClass CRD を使用して、Kubernetes API とクラウドプロバイダー Instance API を呼び出しコンピュートインスタンスをプロビジョニングするアーキテクチャ図。](../.gitbook/assets/en-autoscaling-02-karpenter-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-02-karpenter-0.html)

### Karpenter のワークフロー

次の図は、EKS クラスターで Karpenter がどのように動作するかを示します。

![スケジュール不能な Pod が Kubernetes API 経由で Karpenter コントローラーに到達し、Karpenter が AWS EC2 API を照会してノードをリクエストし、新しいノードが登録されて最終的に Pod がスケジュールされるシーケンス図。](../.gitbook/assets/en-autoscaling-02-karpenter-1.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-02-karpenter-1.html)

### 主要コンポーネント

1. **Karpenter Controller**: スケジューリング需要をシミュレートし、NodeClaim を作成してノードライフサイクルを管理します。実際の Pod バインドは Kubernetes の scheduler が実行します。
2. **CRD CEL 検証**: NodePool と EC2NodeClass は CRD 内の CEL ルールで検証されます（admission/conversion webhook は Karpenter 1.1 で削除されました）。
3. **NodePool および NodeClaim CRD**: NodePool はポリシーを定義し、NodeClaim は個々のプロビジョニング済みノードの要件とライフサイクルを記録します。
4. **EC2NodeClass CRD**: プロビジョニングするノードの設定を定義します。
5. **Cloud Provider Integration**: クラウドプロバイダー API と統合し、コンピュートリソースを管理します。

### 動作の仕組み

1. Karpenter Controller がスケジュール不能な Pod を検出します。
2. Pod 要件（リソース、node selector、toleration など）を分析します。
3. NodePool および EC2NodeClass の設定に基づいて適切なノードタイプを決定します。
4. クラウドプロバイダー API を呼び出してノードをプロビジョニングします。
5. ノードが登録され Ready になると、Kubernetes scheduler は適格な Pod をバインドできます。Karpenter は kube-scheduler を置き換えません。
6. Consolidation、drift、expiration、手動削除、およびクラウド中断にはそれぞれ異なるトリガーと保護機構があります。これらはすべて SQS 中断イベントではありません。

## インストールと設定

apiVersion/kind を含まない YAML ブロックは、説明している NodePool または EC2NodeClass spec 用の設定フラグメントです。単独で kubectl apply できるドキュメントではありません。

これらは既存クラスター向けの独立した学習例であり、本番環境対応のデプロイメントバンドルではありません。繰り返されるオブジェクト名は代替案を表します。インストール前に IAM/OIDC、ノードアクセス、承認済みサブネット/security group、bootstrap キャパシティ、および中断キューを準備して検証してください。すべての YAML は `my-cluster` などのリテラルな例の名前を使用します。保存済み YAML ファイル内では kubectl は `${CLUSTER_NAME}` を展開しません。監査では AWS リソースのプロビジョニング、Karpenter のインストール、またはスケーリングの計測は行いませんでした。リリースが既に存在する場合、新規インストールコマンドは失敗します。既存のインストールは、バージョン付きアップグレード/CRD 移行ガイドに従う必要があります。

### 前提条件

- プラットフォームおよび Karpenter matrix でサポートされている Kubernetes バージョンを使用してください。公開済み matrix では、Kubernetes1.34 に Karpenter 1.6、1.35 に 1.9、1.36 に1.13 が最小バージョンとして示されています。これらの最小値は、古い Karpenter のすべての minor バージョンが維持されることを意味しません。matrix は現在、1.37 との互換性を確立していません。EKS バージョンの提供状況/サポートは別途確認する必要があります。
- 設定済みの kubectl
- クラウドプロバイダーの認証情報と権限
- Helm（任意）

### AWS EKS へのインストール

#### 1. IAM Role と Policy のセットアップ

このコマンドは、既存の controller role、node role、および API ベースの EKS 認証（API または API_AND_CONFIG_MAP）を前提とします。CONFIG_MAP 専用クラスターでは、list-access-entries ではなく、既存の aws-auth node mapping を確認する必要があります。付随的なセットアップ手順として認証モードを変更しないでください。node role は EC2 を信頼し、worker-node/ECR pull 権限（例: AmazonEKSWorkerNodePolicy および AmazonEC2ContainerRegistryPullOnly）が必要です。サポートされる場所では、VPC CNI に専用の identity を付与してください。SSM 権限は任意であり、設定済み agent が必要です。AmazonEKSClusterPolicy は Karpenter controller policy の代替ではありません。

```bash
# Set the existing cluster and Region; these commands only inspect AWS/Kubernetes.
export CLUSTER_NAME="my-cluster"
export AWS_REGION="us-west-2"
export KARPENTER_VERSION="1.14.1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
CLUSTER_ENDPOINT=$(aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" --query cluster.endpoint --output text)
export ACCOUNT_ID CLUSTER_ENDPOINT
kubectl config current-context
aws iam get-role --role-name "KarpenterControllerRole-${CLUSTER_NAME}" --query Role.AssumeRolePolicyDocument
aws iam get-role --role-name "KarpenterNodeRole-${CLUSTER_NAME}" --query Role.AssumeRolePolicyDocument
aws eks list-access-entries --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME"
```

#### 2. Helm を使用したインストール

参照するキューと bootstrap キャパシティを準備した後に、新規インストール例を一度だけ使用してください。アップグレードの場合は、バージョン付き移行ガイドを確認し、一致する CRD を更新してください（例: 個別に管理される karpenter-crd chart 経由）。controller chart のアップグレードだけでは、通常 CRD はアップグレードされません。既存の CRD インストールを移行する前に、所有権を検証してください。

```bash
# Run only after the prerequisites and the current kubectl context are verified.
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${ACCOUNT_ID:?Set the AWS account ID}"
: "${CLUSTER_ENDPOINT:?Set the matching EKS endpoint}"
KARPENTER_VERSION="1.14.1"
helm install karpenter oci://public.ecr.aws/karpenter/karpenter \
  --version "$KARPENTER_VERSION" \
  --namespace karpenter --create-namespace \
  --set-string 'serviceAccount.annotations.eks\.amazonaws\.com/role-arn'="arn:aws:iam::${ACCOUNT_ID}:role/KarpenterControllerRole-${CLUSTER_NAME}" \
  --set-string settings.clusterName="$CLUSTER_NAME" \
  --set-string settings.clusterEndpoint="$CLUSTER_ENDPOINT" \
  --set-string settings.interruptionQueue="$CLUSTER_NAME" \
  --wait --timeout 5m
```

#### 3. インストールの検証

```bash
kubectl get deployments,pods -n karpenter
kubectl rollout status deployment/karpenter -n karpenter --timeout=180s
kubectl get nodepools,ec2nodeclasses,nodeclaims
```

デフォルトの controller replica 2 個に対する例示的な出力（この監査で取得した実行結果ではありません）:
```
NAME                         READY   STATUS    RESTARTS   AGE
karpenter-<hash>-<id-1>      1/1     Running   0          1m
karpenter-<hash>-<id-2>      1/1     Running   0          1m
```

### 基本的な NodePool および EC2NodeClass 設定

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
  limits:
    cpu: '1000'
    memory: 1000Gi
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - m5.large
        - m5.xlarge
        - m5.2xlarge
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  role: KarpenterNodeRole-my-cluster
  amiSelectorTerms:
  - alias: al2023@latest
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  tags:
    karpenter.sh/discovery: my-cluster
  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 100Gi
      volumeType: gp3
      deleteOnTermination: true
      encrypted: true
```

## NodePool

NodePool は、Karpenter によるノードのプロビジョニング方法を定義する Kubernetes カスタムリソースです。以前の Provisioner に置き換わるものです。

### 基本的な NodePool 設定

次の特殊な taint は、対応するワークロード toleration を意図的に必要とします。設定された taint を削除することが検証済みの initializer を用意するまで、startupTaints は空にしてください。所有者のない startup taint を作ると、ノードが使用不能なままになる可能性があります。limits、初期化、および disruption の例は、実行中の本番 NodePool に加算する変更ではなく、代替案です。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    metadata:
      labels:
        environment: training
        app: web
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - m5.large
        - m5.xlarge
        - m5.2xlarge
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
      expireAfter: 720h
      taints:
      - key: example.com/special-taint
        value: 'true'
        effect: NoSchedule
      startupTaints: []
  limits:
    cpu: '1000'
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### 要件の設定

要件は、互いに、EC2NodeClass と、Pod の制約とで交差されます。amd64 と arm64 を許可しても、適格なインスタンスタイプ、AMI、およびコンテナイメージが両方をサポートしている場合にのみ役立ちます。適格な zone/capacity type のリストは均等な分割を保証しません。その目的にはワークロードの topology constraints を使用してください。

要件は Karpenter がプロビジョニングするノードの特性を定義します。

```yaml
template:
  spec:
    requirements:
    - key: karpenter.sh/capacity-type
      operator: In
      values:
      - on-demand
      - spot
    - key: kubernetes.io/arch
      operator: In
      values:
      - amd64
      - arm64
    - key: node.kubernetes.io/instance-type
      operator: In
      values:
      - m5.large
      - m5.xlarge
      - c5.large
      - m6g.large
      - c6g.large
    - key: topology.kubernetes.io/zone
      operator: In
      values:
      - us-west-2a
      - us-west-2b
      - us-west-2c
    - key: kubernetes.io/os
      operator: In
      values:
      - linux
```

### Limits の設定

`spec.limits` はプロビジョニング済みリソースの合計を制約しますが、並列プロビジョニングは結果整合性のあるチェックを使用するため、一時的に limit を超える可能性があります。厳密な請求上限ではありません。文字列の quantity は API/GitOps 間の型の差異を回避します。

```yaml
limits:
  cpu: '1000'
  memory: 1000Gi
  nvidia.com/gpu: '10'
```

### Experimental DRA Allocation Tracking (v1.13)

Core Karpenter v1.13 では DRA device-allocation tracking が追加されました。これは本番 DRA プロビジョニングを包括的に保証するものではありません。AWS1.14.1 chart のデフォルトは `settings.ignoreDRARequests: true` であり、upstream は正式な DRA サポートをまだ GA ではないと位置付けています。Kubernetes1.29 が最小であることは、互換性の十分な証拠ではありません。正確な Kubernetes resource API、DRA driver、ResourceClaims/ResourceSlices、および Karpenter 設定を検証してください。DRA claim を下記の device-plugin extended-resource 例と同一視しないでください。

### ノード有効期限の設定

`expireAfter` は、expiration による drain の開始時点を定義するものであり、置き換え完了時間を保証するものではありません。下記の任意の `terminationGracePeriod` は drain を制限しますが、PDB によってブロックされたものを含む残りの Pod を強制削除する可能性があります。その期限は、アプリケーションの shutdown と recovery 要件を検証した後にのみ選択してください。

```yaml
spec:
  template:
    spec:
      expireAfter: 720h
      terminationGracePeriod: 30m
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### NodeReadinessController Taint の認識 (v1.13)

Core Karpenter v1.13 は、初期化されていない管理対象ノードのスケジューリングシミュレーション中に、個別の NodeReadinessController が付与する `readiness.k8s.io/` taint を一時的なものとして認識します。初期化の完了としてマークする前にそれらの taint が消えるのを待機します。削除することも、Kubernetes scheduler による回避を許可することもありません。他の initializer taint には、正確な `startupTaints` 設定と、それらを削除する controller が依然として必要です。

### 2026 年 7 月更新: v1.14 リリース

2026 年 7 月 11 日にリリースされた Karpenter v1.14 の変更点:

- **CapacityBuffers API サポート**: alpha の capacity-buffer 統合です。`CapacityBuffer` はデフォルトで無効であり、対応する CRD/controller 設定が必要です。予約済みのヘッドルームは無料のキャパシティでもレイテンシ保証でもありません。
- **Preview instance type サポート**: 適格な preview offering を認識します。実際のプロビジョニングには依然として account/Region のアクセスと可用性が必要です。
- **Nitro Enclaves サポート**: NodeClaim resource request に `eks.amazonaws.com/nip-slots` が含まれると、プロバイダーは生成された launch-template の `EnclaveOptions.Enabled` を設定します。互換性のあるインスタンス、AMI、および device-plugin のセットアップは引き続き前提条件です。1.14.1 に `EC2NodeClass.spec.enclaveOptions` フィールドはありません。
- バグ修正: secondary ENI 上の primary IP の計上、Zonal Shift cache の hydrate の保証、AWS SDK client timeout の operator config への接続など

詳細は [v1.14.0 release notes](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.14.0) を参照してください。

2026 年 7 月 17 日、古いブランチには 1.3.8 や 1.11.3 を含む patch が提供されました。この過去の backport は、その間にあるすべての minor バージョンへの継続的なサポートを確立するものではありません。現行の support policy では LTS1.9 は 2027 年 2 月まで、LTS1.14 は 2027 年 7 月までとされています。通常の minor は次の minor までしかサポートされません。古いラインが維持されると想定するのではなく、サポート対象のラインを選び、その migration guidance に従ってください。

AWS の 2026 年 7 月 22 日の発表では、Karpenter/EKS Auto Mode 向けに EFA network-interface および placement-group 設定が追加されました。AWS Karpenter1.14.1 では、具体的なフィールドは `EC2NodeClass.spec.networkInterfaces` および `spec.placementGroupSelector` です（NodePool フィールドではありません）。EFA 専用 interface は VPC IP address を消費しませんが、device/card index0 の primary `interface` は引き続き必要です。既存の placement group を名前または ID で選択してください。その cluster/spread/partition strategy とサポートするインスタンスは配置を制約します。ここでの例は HPC ワークロードを設定または検証しません。

### 2026 年 8 月更新: v1.14.1 Patch リリース

v1.14 ラインの最初の patch である [v1.14.1](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.14.1) は、2026 年 8 月 21 日に公開されました。upstream `sigs.k8s.io/karpenter` バージョンを引き上げ、v1.14.0 以降の修正を cherry-pick した maintenance release です。

### 2026 年 10 月更新: v1.15.0 リリース

[v1.15.0](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.15.0) は 2026 年 10 月 10 日に公開されました。主な変更点:

- **Node repair が voluntary disruption になる**: node repair は disruption の仕組みに統合され、キャパシティ制約のある NodePool が最初に置き換えノードを準備できない場合は terminate-first repair になります。`ec2:RebootInstances` による reboot が repair action として追加され（`RebootForRepair` AWS feature gate の背後）、以前の repair controller は `--legacy-node-repair` flag を通じて引き続き利用できます。
- **KubeletConfiguration の CEL サポート**: `maxPodsExpression`、`kubeReserved`、`systemReserved` が CEL expression を受け付け、EC2NodeClass KubeletConfiguration フィールドが拡張されました。
- **より広範な DRA サポート**: 優先順位付き代替案のサポートに加え、NVIDIA および EFA driver DRA サポート。
- その他: `--aws-feature-gates` flag、デフォルトの pod topology spread awareness、プロビジョニング中の instance type volume limit の計上、`karpenter_pods_disrupted_total` などの新しい disruption metrics、および feature-gated pod deletion cost management controller。

support policy では通常の minor は次の minor までしかサポートされないため、v1.15.0 のリリースにより、v1.14 は LTS ラインとしてのみ継続します（2027 年 7 月まで）。詳細は [v1.15.0 release notes](https://github.com/aws/karpenter-provider-aws/releases/tag/v1.15.0) を参照してください。

## Node Classes

Node class は Karpenter がプロビジョニングするノードの設定を定義します。AWS では EC2NodeClass CRD を使用します。

### AWS EC2NodeClass の設定

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  tags:
    karpenter.sh/discovery: my-cluster
    environment: training
  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 100Gi
      volumeType: gp3
      deleteOnTermination: true
      encrypted: true
  role: KarpenterNodeRole-my-cluster
  amiSelectorTerms:
  - alias: al2023@latest
  userData: '#!/bin/bash

    echo "Hello from Karpenter node!"

    '
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 1
    httpTokens: required
```

### Subnet と Security Group の選択

Subnet と security group は selector term で選択します（複数の term は OR、1 つの term 内の tag は AND で結合されます）。

```yaml
subnetSelectorTerms:
- tags:
    karpenter.sh/discovery: my-cluster
    Name: private-*
securityGroupSelectorTerms:
- tags:
    karpenter.sh/discovery: my-cluster
```

### AMI の設定

Karpenter は `amiSelectorTerms` を通じて AMI を選択します。alias は family/version を選択します。**`@latest` はバージョン固定ではありません**。解決される AMI が変わり、drift を発生させる可能性があります。`@latest` のサンプルは学習例です。本番環境では、ロールアウト前に明示的にサポートされる AMI release（実際のリリース日を持つ `al2023@vYYYYMMDD`）または承認済み AMI ID を解決してテストしてください。AL2 EKS AMI は Kubernetes1.33+ 向けには公開されていません。以下の variant は代替案です。Custom AMI には、動作する bootstrap、registration taint、kubelet、CNI/runtime、および identity のセットアップが必要です。

```yaml
# Amazon Linux 2023
amiSelectorTerms:
  - alias: al2023@latest
---
# Bottlerocket
amiSelectorTerms:
  - alias: bottlerocket@latest
---
# Custom AMI (by ID) — amiFamily is required when no alias term is used
amiFamily: Custom
amiSelectorTerms:
  - id: "ami-0123456789abcdef0"
# Ubuntu: no v1 alias — use amiFamily: Custom with an id/tags/name term
```

### Block Device の設定

device mapping は AMI family 固有です。これらの AL2023 例では root device に /dev/xvda を使用しています。ほかの AMI では実際の layout を確認してください。追加 volume には明示的な filesystem/mount、または application storage plan が必要です。customer-managed KMS key にも適切な key/IAM 権限が必要です。

ノードの storage 設定を定義できます。

```yaml
blockDeviceMappings:
- deviceName: /dev/xvda
  ebs:
    volumeSize: 100Gi
    volumeType: gp3
    iops: 3000
    throughput: 125
    deleteOnTermination: true
    encrypted: true
    kmsKeyID: arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab
- deviceName: /dev/xvdb
  ebs:
    volumeSize: 500Gi
    volumeType: gp3
    deleteOnTermination: true
    encrypted: true
```

### User Data の設定

これらの shell user-data snippet は AL2023 を前提としています。AL2023 では Karpenter が生成した bootstrap/nodeadm 設定と custom data がマージされます。これは汎用的な Bottlerocket/Windows bootstrap として有効ではありません。起動のたびに無制限の package update を実行するのではなく、package を AMI に bake してテストしてください。設定、IAM、および network path なしで CloudWatch Agent をインストール/開始しても、telemetry collection は確立されません。

```yaml
userData: |
  #!/bin/bash
  set -euo pipefail
  # Only for a workload that requires this setting; keep node packages in a tested AMI.
  cat > /etc/sysctl.d/99-workload-map-count.conf <<'EOF'
  vm.max_map_count=262144
  EOF
  sysctl -p /etc/sysctl.d/99-workload-map-count.conf
```

### Node Consolidation プロセス

次の図は Karpenter の node consolidation プロセスを示しています。この機能はクラスター効率の最適化とコスト削減に重要です。

![概念的な consolidation: ワークロードが既存または置き換え後のキャパシティに収まるかをシミュレートし、必要な置き換えを Ready にしてから、Pod を eviction および再作成したうえで適格な古いノードを終了します。これは live Pod migration でも、3 対 1 の結果を保証するものでもありません。](../.gitbook/assets/en-autoscaling-02-karpenter-2.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-02-karpenter-2.html)

## 中断処理

設定済みの中断処理は、キャパシティを失う前に対応しようとします。通知、置き換えキャパシティ、shutdown deadline、およびアプリケーション recovery が結果を決定します。中断されない可用性は保証されません。

### 統合された中断処理

クラウド中断処理は consolidation/expiration とは別です。次のような signal を対象とします。

1. **Spot 中断警告**: 可能な場合は drain を開始し、置き換えキャパシティをリクエストします。notice window は recovery SLA を保証するものではありません。
2. **スケジュールされた health/maintenance event**: 影響を受けたインスタンスに対応します。
3. **インスタンス停止/終了 event**: サービスから離脱するキャパシティを reconcile します。
4. **EC2 instance-status failure**: 必要な EC2 API 権限を使用して health を検査します。rebalance recommendation 単独は event として公開され、taint/drain/terminate 操作を自動実行しません。

### 中断処理の設定

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default

      # Node expiration settings
      expireAfter: 720h  # 30 days
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### Draining の設定

Karpenter は通常、graceful draining 中に eviction を使用します。Helm settings は controller を設定します。NodePool disruption budget は voluntary consolidation/drift の開始を制限しますが、すべての同時ノード損失を制限するものではありません。30% budget は切り上げ後、deleting/not-ready node を差し引きます。厳密な 30% の上限ではありません。expiration、中断、および repair には異なる強制的な動作があり得ます。`interruptionQueue` を有効にする前に、名前付き SQS queue、EventBridge rule/target、queue policy、および controller 権限を設定してください。Helm field だけでそれらが作成されるわけではありません。

```yaml
settings:
  clusterName: my-cluster
  interruptionQueue: my-cluster
  batchMaxDuration: 10s
  batchIdleDuration: 1s
  featureGates:
    spotToSpotConsolidation: false
controller:
  resources:
    requests:
      cpu: 1
      memory: 1Gi
    limits:
      cpu: '1'
      memory: 1Gi
logLevel: info
```

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
      expireAfter: 720h
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
    budgets:
      - nodes: "30%"   # Voluntary budget: round up, then subtract deleting/not-ready nodes
```

### PDB (PodDisruptionBudget) 統合

PDB は healthy replica に従って voluntary eviction を制約します。replica を作成するものでも、アプリケーションの可用性を保証するものでもありません。下記の `minAvailable: 2` では、eviction が許可される前に十分な数の一致する healthy Pod が必要です。インスタンス損失と強制的な終了 deadline は依然として中断を引き起こす可能性があります。

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: default
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
```

## 統合

Karpenter はさまざまな Kubernetes およびクラウドサービスと統合します。

### Kubernetes 統合

#### 1. Pod Topology Spread Constraints

Karpenter はノードをプロビジョニングする際に Pod Topology Spread Constraints を考慮します。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-server
  namespace: default
spec:
  replicas: 10
  template:
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-server
      containers:
      - name: web-server
        image: nginx:1.30.4
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            memory: 256Mi
    metadata:
      labels:
        app: web-server
  selector:
    matchLabels:
      app: web-server
```

#### 2. Pod Affinity/Anti-Affinity

Karpenter は Pod Affinity および Anti-Affinity ルールを考慮します。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-server
  namespace: default
spec:
  replicas: 10
  template:
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - web-server
            topologyKey: kubernetes.io/hostname
      containers:
      - name: web-server
        image: nginx:1.30.4
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            memory: 256Mi
    metadata:
      labels:
        app: web-server
  selector:
    matchLabels:
      app: web-server
```

#### 3. Taint と Toleration

GPU の例には、互換性のある accelerated AMI、NVIDIA driver、および GPU taint を tolerate して nvidia.com/gpu を advertise する device-plugin DaemonSet が必要です。BusyBox Pod は GPU を予約する例を示すだけで、CUDA を実行または benchmark しません。実際の GPU application image を使用して別途検証してください。

Karpenter はノードをプロビジョニングする際に taint と toleration を考慮します。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu
spec:
  template:
    spec:
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - g4dn.xlarge
        - g4dn.2xlarge
      taints:
      - key: nvidia.com/gpu
        value: 'true'
        effect: NoSchedule
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gpu-app
  namespace: default
spec:
  replicas: 3
  template:
    spec:
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
      nodeSelector:
        karpenter.sh/nodepool: gpu
      containers:
      - name: gpu-allocation-demo
        image: busybox:1.37.0
        command:
        - sh
        - -c
        - sleep 3600
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            memory: 128Mi
            nvidia.com/gpu: 1
    metadata:
      labels:
        app: gpu-app
  selector:
    matchLabels:
      app: gpu-app
```

### AWS 統合

#### 1. EC2 Spot Instances

Karpenter はコストを最適化するために EC2 Spot instance をサポートします。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot
spec:
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: spot
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: spot
spec:
  role: KarpenterNodeRole-my-cluster
  amiSelectorTerms:
  - alias: al2023@latest
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
```

#### 2. EC2 Instance Profile

role と instanceProfile は相互排他的です。role を使用する場合、Karpenter は instance profile を管理するため、対応する IAM API 権限/接続性が必要です。クラスターから IAM endpoint への経路がない場合は、事前プロビジョニング済みの instanceProfile を使用してください。IAM に PrivateLink endpoint はありません。controller は引き続き node role に対する PassRole を必要とし、EKS node access は EC2 credential を持つこととは別です。

Karpenter はノードに IAM 権限を付与するため、EC2 instance profile を使用します。

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  instanceProfile: KarpenterNodeInstanceProfile-my-cluster
  amiSelectorTerms:
  - alias: al2023@latest
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
```

#### 3. Launch Template の置き換え (EC2NodeClass)

Karpenter v1 はユーザー指定の EC2 launch template を受け付けません（legacy の `launchTemplate` field は削除されました）。Karpenter は EC2NodeClass から launch template を自ら生成・管理するため、launch template に設定していたであろう値は EC2NodeClass で直接表現します。

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: node-config
spec:
  role: KarpenterNodeRole-my-cluster
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  amiSelectorTerms:
  - alias: al2023@latest
  userData: '#!/bin/bash

    echo "Hello from Karpenter node!"

    '
  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 100Gi
      volumeType: gp3
      deleteOnTermination: true
      encrypted: true
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 1
    httpTokens: required
```
## Amazon EKS との統合

Karpenter の AWS provider は、identity、network、node access、および bootstrap が設定されている場合に、EKS 管理コンピュートと並行して EC2 capacity をプロビジョニングできます。

![Amazon EKS クラスター内の Karpenter controller が IAM role を引き受けて EC2 API を直接呼び出し、Auto Scaling Group と Managed Node Group を経由せず EC2 instance を作成するアーキテクチャ図。](../.gitbook/assets/en-autoscaling-02-karpenter-3.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-02-karpenter-3.html)

### EKS クラスターの準備

すべての例の名前を一貫して置き換えてください。worker に適した subnet/security group のみを選択してください。すべての control-plane subnet に tag を付けることは安全な discovery strategy ではありません。ノードの起動を許可する前に、subnet route、security rule、CNI IP capacity、および必要な private endpoint を検証してください。

#### 1. クラスター Tag のセットアップ

infrastructure configuration では、承認された worker subnet と security group にのみ tag を付けてください。VPC tagging はそれらのリソースを選択するものではありません。discovery value は例（ここでは `my-cluster`）と一致する必要があります。tag だけでは private routing、適切な security rule、または十分な空き address を証明しません。NodePool を適用する前に、実際の resource と route を検査してください。

```bash
# Inspect resources that your infrastructure configuration has tagged for this cluster.
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
aws ec2 describe-subnets --region "$AWS_REGION" \
  --filters "Name=tag:karpenter.sh/discovery,Values=${CLUSTER_NAME}" \
  --query 'Subnets[].{ID:SubnetId,AZ:AvailabilityZone,FreeIPs:AvailableIpAddressCount,PublicIPOnLaunch:MapPublicIpOnLaunch,VPC:VpcId}'
aws ec2 describe-security-groups --region "$AWS_REGION" \
  --filters "Name=tag:karpenter.sh/discovery,Values=${CLUSTER_NAME}" \
  --query 'SecurityGroups[].{ID:GroupId,VPC:VpcId,Name:GroupName}'
# Inspect explicit and main route-table associations for the intended subnets.
aws ec2 describe-route-tables --region "$AWS_REGION" \
  --filters "Name=vpc-id,Values=$(aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" --query cluster.resourcesVpcConfig.vpcId --output text)"
```

#### 2. IAM Role のセットアップ

先に示した不完全な手書きの allow-all policy ではなく、下記のバージョン固有の controller policy および infrastructure reference を使用してください。controller credential（ここでは IRSA）は node credential および VPC CNI/workload identity とは別のものです。controller trust は、クラスター OIDC provider、`system:serviceaccount:karpenter:karpenter`、および `aud: sts.amazonaws.com` と一致する必要があります。このバージョンと選択した機能に必要な action/resource/condition のみを付与してください。API ベースの認証が有効な場合、通常 node role は `EC2_LINUX` access entry を通じて EKS への参加を許可される必要があります。検査コマンドで IAM role や access entry が作成されることはありません。

```bash
# Download a versioned reference for review; this does not create a CloudFormation stack.
KARPENTER_VERSION="1.14.1"
curl --fail --show-error --location \
  "https://raw.githubusercontent.com/aws/karpenter-provider-aws/v${KARPENTER_VERSION}/website/content/en/preview/getting-started/getting-started-with-karpenter/cloudformation.yaml" \
  --output karpenter-cloudformation-reference.yaml
# Inspect the existing role's attached and inline policies.
: "${CLUSTER_NAME:?Set the existing cluster name}"
aws iam list-attached-role-policies --role-name "KarpenterControllerRole-${CLUSTER_NAME}"
aws iam list-role-policies --role-name "KarpenterControllerRole-${CLUSTER_NAME}"
```

### EKS クラスターへの Karpenter のインストール

```bash
# Run only after the prerequisites and the current kubectl context are verified.
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${ACCOUNT_ID:?Set the AWS account ID}"
: "${CLUSTER_ENDPOINT:?Set the matching EKS endpoint}"
KARPENTER_VERSION="1.14.1"
helm install karpenter oci://public.ecr.aws/karpenter/karpenter \
  --version "$KARPENTER_VERSION" \
  --namespace karpenter --create-namespace \
  --set-string 'serviceAccount.annotations.eks\.amazonaws\.com/role-arn'="arn:aws:iam::${ACCOUNT_ID}:role/KarpenterControllerRole-${CLUSTER_NAME}" \
  --set-string settings.clusterName="$CLUSTER_NAME" \
  --set-string settings.clusterEndpoint="$CLUSTER_ENDPOINT" \
  --set-string settings.interruptionQueue="$CLUSTER_NAME" \
  --wait --timeout 5m
```

### EKS Managed Node Group との併用

Karpenter は EKS Managed Node Group と共存できます。以下の NodePool は別個の EC2 node をプロビジョニングします。Managed Node Group を管理するものではありません。controller は信頼できる bootstrap capacity 上に維持してください（デフォルト chart は Karpenter node を除外し、異なる host 上に 2 replica を要求します）。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: managed-ng
spec:
  template:
    metadata:
      labels:
        managed-by: karpenter
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - m5.large
        - m5.xlarge
      taints:
      - key: managed-by
        value: karpenter
        effect: NoSchedule
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: managed-ng
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: managed-ng
spec:
  role: KarpenterNodeRole-my-cluster
  amiSelectorTerms:
  - alias: al2023@latest
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  tags:
    karpenter.sh/discovery: my-cluster
```

### EKS Fargate との併用

Fargate は Kubernetes topologySpreadConstraints を実装せず、Kubernetes affinity/anti-affinity rule はそこで適用されません。デフォルト chart の EC2 placement constraint が Fargate AZ separation を保証すると想定しないでください。profile/subnet placement を個別に設計して検証してください。

選択対象を絞った Fargate profile には controller Pod を配置でき、Karpenter は EC2 worker をプロビジョニングできます。Karpenter は Fargate capacity を作成せず、その profile を管理しません。`default`/`kube-system` のすべてではなく、namespace `karpenter` と controller label を選択する profile を準備してください。JSON selector の形は `[{"namespace":"karpenter","labels":{"app.kubernetes.io/name":"karpenter"}}]` です。profile には独自の Pod execution role/private subnet が必要であり、controller AWS 権限には依然として IRSA が必要です（EKS Pod Identity は Fargate でサポートされません）。以下のコマンドは既存の profile を検査するだけです。

```bash
# Inspect an existing, narrowly selected controller Fargate profile.
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
aws eks describe-fargate-profile --region "$AWS_REGION" \
  --cluster-name "$CLUSTER_NAME" --fargate-profile-name karpenter-controller
```

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ec2
spec:
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: ec2
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: ec2
spec:
  role: KarpenterNodeRole-my-cluster
  amiSelectorTerms:
  - alias: al2023@latest
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
```

### AZ 障害への対応: Amazon ARC Zonal Shift 統合（2026 年 5 月）

Karpenter は、有効化済みの EKS ARC zonal-shift resource と統合できます。手動 zonal shift または設定済み autoshift が有効になると、Karpenter は shift された AZ で新しい capacity を回避します。これはすべての AZ 障害を独立して検出するものではなく、その AZ に workload を固定する Pod/PV requirement を上書きするものでもありません。

有効な shift 中、shift された AZ での voluntary disruption は停止します。その AZ へ Pod を移動することに依存する healthy-zone の disruption も防止されます。これはすべての healthy AZ におけるすべての voluntary disruption を無条件に停止するものではありません。EKS/ARC の前提条件、`eks:DescribeCluster`/ARC 権限、および `settings.enableZonalShift: true`（environment option `ENABLE_ZONAL_SHIFT`）を設定してください。autoshift には、さらに独自の opt-in/practice 設定が必要です。custom ARC CRD は不要で、shift が終了すると操作は再開されます。

### EKS コスト最適化

Karpenter を使用して EKS クラスターのコストを最適化できます。

![Node-group scaling と Karpenter の動的 capacity selection、consolidation、Spot option の概念的な比較。スケーリング速度やコスト削減について、測定済みまたは普遍的な順位付けは確立されていません。](../.gitbook/assets/en-autoscaling-02-karpenter-4.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-02-karpenter-4.html)

#### 1. Spot Instance の使用

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot
spec:
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: spot
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: spot
spec:
  role: KarpenterNodeRole-my-cluster
  amiSelectorTerms:
  - alias: al2023@latest
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
```

#### 2. 多様な Instance Type の使用

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: flexible
spec:
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
        - spot
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - m5.large
        - m5.xlarge
        - m5.2xlarge
        - m6g.large
        - m6g.xlarge
        - m6g.2xlarge
        - c5.large
        - c5.xlarge
        - c5.2xlarge
        - c6g.large
        - c6g.xlarge
        - c6g.2xlarge
        - r5.large
        - r5.xlarge
        - r5.2xlarge
        - r6g.large
        - r6g.xlarge
        - r6g.2xlarge
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

#### 3. Node Consolidation の有効化

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
```

## ベストプラクティス

![Karpenter のベストプラクティスを、パフォーマンス最適化、コスト最適化、可用性向上、セキュリティ強化のカテゴリ別にまとめた四つの並列リスト。](../.gitbook/assets/en-autoscaling-02-karpenter-5.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-02-karpenter-5.html)

### パフォーマンス最適化

1. **適切な Instance Type を選択**: ワークロードに適した instance type を選択します。
2. **多様な Instance Type を許可**: 可用性とコスト最適化のため、さまざまな instance type を許可します。
3. **適切な TTL を設定**: ワークロードパターンに合う TTL を設定します。
4. **Node Consolidation を有効化**: リソース使用率を最適化するため、node consolidation を有効にします。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: optimized
spec:
  template:
    spec:
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - m5.large
        - m5.xlarge
        - m5.2xlarge
        - c5.large
        - c5.xlarge
        - c5.2xlarge
        - r5.large
        - r5.xlarge
        - r5.2xlarge
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
      expireAfter: 720h
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### コスト最適化

1. **Spot Instance を活用**: コストを削減するために Spot instance を使用します。
2. **適切な Instance Size を選択**: ワークロードに適した instance size を選択します。
3. **空ノードの削除を評価**: 適格な worker NodePool はゼロまで縮小できます。controller/bootstrap compute と無関係なクラスターコストは残ります。
4. **ノード更新を計画**: expiration は現在の制約に従って適格な capacity をローテーションします。新しい instance type の自動選択や固定された AMI の patch は行いません。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-optimized
spec:
  template:
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
      expireAfter: 168h
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
```

### 可用性の向上

1. **複数の Availability Zone を使用**: 複数の availability zone にノードをデプロイします。
2. **On-demand と Spot Instance を混在**: 可用性とコストのバランスを取ります。
3. **適切な PDB を設定**: 冗長性と recovery 設計とともに、実際の healthy-replica の制限内で voluntary eviction を保護します。
4. **中断処理を設定してテスト**: 中断されないサービスを想定せず、notification path、shutdown deadline、置き換え capacity を検証します。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: high-availability
spec:
  template:
    spec:
      requirements:
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - us-west-2a
        - us-west-2b
        - us-west-2c
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
        - spot
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
      expireAfter: 720h
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 60s
```

## トラブルシューティング

### よくある問題

#### 1. ノードのプロビジョニング失敗

**症状**: Pod が Pending 状態のままで、ノードがプロビジョニングされません。

**解決策**:
- Karpenter log を確認する
- IAM 権限を検証する
- NodePool 設定を確認する

```bash
# Check Karpenter logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller

# Check NodePool status
kubectl describe nodepool <name>

# Check pod events
kubectl describe pod <name>
```

#### 2. ノード削除の問題

**症状**: ノードが期待どおりに削除されません。

**解決策**:
- TTL 設定を確認する
- node consolidation 設定を検証する
- Pod draining 状態を確認する

```bash
# Check node status
kubectl describe node <name>

# Check node labels
kubectl get node <name> --show-labels

# Check Karpenter logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller --since=30m
```

#### 3. Instance Type 選択の問題

**症状**: 予期しない instance type がプロビジョニングされます。

**解決策**:
- NodePool 要件を確認する
- Pod resource request を検証する
- availability zone の制約を確認する

```bash
# Check NodePool requirements
kubectl get nodepool <name> -o yaml

# Check pod resource requests
kubectl describe pod <name>

# Check node information
kubectl describe node <name>
```

### デバッグツール

```bash
# Check Karpenter version
kubectl get deployment -n karpenter karpenter -o jsonpath="{.spec.template.spec.containers[0].image}"

# Check Karpenter logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller

# Check NodePool list
kubectl get nodepools

# Check EC2NodeClass list
kubectl get ec2nodeclasses

# Check events
kubectl get events --sort-by='.lastTimestamp'

# Inspect the installed chart version and values before any optional log-level change.
helm list --namespace karpenter --filter '^karpenter$'
helm get values karpenter --namespace karpenter
kubectl get nodeclaims -o wide
```

## まとめ

Karpenter は、ワークロードおよびインフラストラクチャの制約に従ってノードのプロビジョニングとライフサイクルを自動化します。capacity management を改善できますが、可用性、パフォーマンス、およびコストの結果には、ワークロード固有の検証が必要です。

このドキュメントでは、Karpenter の基本概念、インストール方法、NodePool と EC2NodeClass の設定、中断処理、さまざまな統合、Amazon EKS との統合、ベストプラクティス、およびトラブルシューティングを取り上げました。

Karpenter を使用すると、クラスター管理を簡素化し、リソース使用率を最適化し、コストを削減できます。特に Amazon EKS のようなクラウド管理 Kubernetes 環境では、Karpenter の利点を最大化できます。

### 次のステップ

- Karpenter を使用したコスト最適化戦略を実装する
- さまざまなワークロードタイプに対して NodePool を設定する
- ハイブリッドクラスターアーキテクチャを設計する
- Karpenter をほかの Kubernetes ツールと統合する
- 高度なノードライフサイクル管理戦略を開発する

## 参考資料

- [Karpenter 公式ドキュメント](https://karpenter.sh/)
- [Karpenter AWS Provider リポジトリ](https://github.com/aws/karpenter-provider-aws)
- [Amazon EKS Workshop - Karpenter](https://www.eksworkshop.com/docs/autoscaling/compute/karpenter/)
- [AWS Blog - Karpenter](https://aws.amazon.com/blogs/aws/introducing-karpenter-an-open-source-high-performance-kubernetes-cluster-autoscaler/)
- [Karpenter ベストプラクティス](https://aws.github.io/aws-eks-best-practices/karpenter/)
- [Karpenter GitHub リリース](https://github.com/aws/karpenter-provider-aws/releases)
- [AWS What's New - Karpenter ARC Zonal Shift サポート](https://aws.amazon.com/about-aws/whats-new/2026/05/karpenter-arc-zonal-shift/)
- [AWS What's New - Amazon EKS Managed Node Group Warm Pool サポート](https://aws.amazon.com/about-aws/whats-new/2026/04/amazon-eks-managed-node-groups-ec2-warm-pools/)

## クイズ

この章で学んだ内容をテストするには、[トピッククイズ](../quizzes/autoscaling/06-karpenter-quiz.md)に挑戦してください。

この改訂で検証した一次参照資料: [Compatibility](https://karpenter.sh/v1.14/upgrading/compatibility/)、[NodePool](https://karpenter.sh/v1.14/concepts/nodepools/)、[EC2NodeClass](https://karpenter.sh/v1.14/concepts/nodeclasses/)、[Disruption](https://karpenter.sh/v1.14/concepts/disruption/)、[Support policy](https://github.com/aws/karpenter-provider-aws/blob/main/SUPPORT.md)、[Pinned Helm values](https://github.com/aws/karpenter-provider-aws/blob/v1.14.1/charts/karpenter/values.yaml)、[Readiness taints](https://github.com/kubernetes-sigs/karpenter/commit/05431485c90c76a3a662b678a46c1a8da330038d)、[Pinned DRA option](https://github.com/kubernetes-sigs/karpenter/blob/6e7eab7a0f48/pkg/operator/options/options.go)、[EKS node IAM](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html)、[Fargate profiles](https://docs.aws.amazon.com/eks/latest/userguide/fargate-profile.html)。
