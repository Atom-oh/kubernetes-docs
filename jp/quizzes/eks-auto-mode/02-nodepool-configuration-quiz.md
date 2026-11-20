# EKS Auto Mode NodePool 設定クイズ

> **関連ドキュメント**: [NodePool Configuration](../../eks-auto-mode/02-nodepool-configuration.md)

## 選択式問題

### 1. EKS Auto Mode が提供するオプションの組み込み NodePool は何ですか？

- A) default、worker
- B) general-purpose、system
- C) compute、memory
- D) primary、secondary

<details>
<summary>回答を表示</summary>

**回答: B) general-purpose、system**

**説明:**
有効にすると、`general-purpose` と `system` は第 5 世代以降の On-Demand C/M/R インスタンスを使用します。general-purpose は amd64 を使用し、system は amd64 と arm64 をサポートし、`CriticalAddonsOnly` taint が設定されています。Spot を使用する場合は、カスタムプールを使用してください。Auto Mode のローカル DNS／サービスネットワーキング機能は、system プールにスケジュールする必要がある通常の Pod ではありません。

```yaml
# eksctl configuration fragment
autoModeConfig:
  enabled: true
  nodePools: [general-purpose, system]
```

組み込み名を削除すると、その NodePool が削除され、管理対象ノードがドレイン／終了されます。両方を無効にする場合は、`default` が存在すると想定せず、カスタム NodeClass を用意する必要もあります。

</details>

### 2. Auto Mode ノードの IMDS はどのように設定されますか？

- A) NodeClass で `metadataOptions.httpTokens: optional` を設定する
- B) AWS が IMDSv2 とホップ制限 1 を強制し、NodeClass ではこれらの設定を上書きできない
- C) IMDSv2 を動作させるために、ホップ制限を 0 に設定する
- D) AL2023 を選択すると IMDS 認証が無効になる

<details>
<summary>回答を表示</summary>

**回答: B) AWS が IMDSv2 とホップ制限 1 を強制し、NodeClass ではこれらの設定を上書きできない**

**説明:**
管理対象インスタンスのデフォルトでは IMDSv2 とホップ制限 1 が必須で、Auto Mode では変更できません。以前の `metadataOptions` の例は、別の API のものでした。ホップ制限はホストネットワークを使用しない Pod を制限しますが、ホストネットワークを使用するワークロードを含むすべての Pod が隔離されることを保証するものではありません。ノード認証情報に頼るのではなく、ワークロード ID と明示的なリージョン／設定を使用してください。[管理対象インスタンスの制限事項](https://docs.aws.amazon.com/eks/latest/userguide/automode-learn-instances.html)を参照してください。

</details>

### 3. Auto Mode ノードのオペレーティングシステムイメージは誰が選択しますか？

- A) ユーザーが amiFamily で Amazon Linux 2 または Ubuntu を選択する
- B) AWS が適切な管理対象 Bottlerocket バリアントを選択する
- C) ユーザーが任意の Windows AMI を指定する
- D) NodePool の weight によって、Bottlerocket ではなく AL2023 が選択される

<details>
<summary>回答を表示</summary>

**回答: B) AWS が適切な管理対象 Bottlerocket バリアントを選択する**

**説明:**
Auto Mode は、AWS が管理する Bottlerocket バリアントを使用します。AWS NodeClass では、`amiFamily: AL2023` や `amiFamily: Bottlerocket` を選択する設定は公開されていません。ストレージ、ネットワーキング、証明書、サポートされるカーネル設定には、ドキュメントに記載された NodeClass 設定を使用してください。これらは任意の AMI 選択やシェルのユーザーデータとは異なります。

</details>

### 4. Auto Mode で GPU の製造元を選択する NodePool ラベルはどれですか？

- A) karpenter.k8s.aws/gpu-vendor
- B) eks.amazonaws.com/instance-gpu-manufacturer
- C) nvidia.com/gpu-family
- D) karpenter.sh/gpu-type

<details>
<summary>回答を表示</summary>

**回答: B) eks.amazonaws.com/instance-gpu-manufacturer**

**説明:**
AWS Auto Mode のラベル `eks.amazonaws.com/instance-gpu-manufacturer` を使用します。NVIDIA GPU ハードウェアの場合、要件には次のような設定を含められます。

```yaml
# Requirements fragment inside a complete NodePool
requirements:
  - key: eks.amazonaws.com/instance-category
    operator: In
    values: ["g", "p"]
  - key: eks.amazonaws.com/instance-gpu-manufacturer
    operator: In
    values: ["nvidia"]
```

ハードウェアを選択しても、コンテナに GPU が割り当てられるわけではありません。Pod は `nvidia.com/gpu` などの適切な拡張リソースを要求し、互換性のあるイメージ／ランタイムを使用する必要があります。この監査では GPU の実行は行っていません。

</details>

### 5. EC2 の第 6 世代以降を選択する条件はどれですか？

- A) node.kubernetes.io/instance-generation: "6"
- B) eks.amazonaws.com/instance-generation に Gt と値 "5" を指定する
- C) eks.amazonaws.com/generation: "6"
- D) instance-generation: 6

<details>
<summary>回答を表示</summary>

**回答: B) eks.amazonaws.com/instance-generation に Gt と値 "5" を指定する**

**説明:**
`Gt` は厳密な数値の下限を表すため、`Gt ["5"]` は第 6 世代以降を選択します。`In ["6"]` は第 6 世代のみを選択するため、同じ意味ではありません。どちらの条件も、利用可能な最新世代のみを意味するわけではありません。

```yaml
# Requirements fragment inside a complete NodePool
requirements:
  - key: eks.amazonaws.com/instance-generation
    operator: Gt
    values: ["5"]
```

</details>

### 6. NodeClass でプライベートサブネットを選択するにはどうすればよいですか？

- A) subnetType: private を設定する
- B) 確認済みのサブネット ID／タグを選択し、ルーティングと IP 設定を確認する
- C) privateSubnetsOnly: true を設定する
- D) networkType: private を設定する

<details>
<summary>回答を表示</summary>

**回答: B) 確認済みのサブネット ID／タグを選択し、ルーティングと IP 設定を確認する**

**説明:**
`subnetSelectorTerms` は ID またはタグによって選択します。`kubernetes.io/role/internal-elb` などのタグは慣例にすぎず、プライベートルートテーブルであることの証明にはなりません。各 term は選択肢として扱われ、1 つの term 内の複数のタグはすべて一致する必要があります。VPC／AZ の選択、ルート、パブリック IP の動作を確認してください。

```yaml
# Selection fragment; a complete NodeClass also needs identity and security groups
subnetSelectorTerms:
  - tags:
      kubernetes.io/role/internal-elb: "1"
      Environment: production
advancedNetworking:
  associatePublicIPAddress: false
```

`associatePublicIPAddress: false` を設定するとパブリック IP の割り当ては防げますが、NAT ルートや VPC エンドポイントが作成されるわけではありません。NodeClass の ID／セキュリティグループ設定をすべて指定し、準備状態を確認してください。

</details>

### 7. 既存の Auto Mode NodeClass で `maxPods` などの kubelet 設定を変更すると、どうなりますか？

- A) EKS が実行中のノードの kubelet を中断なくインプレースでパッチする
- B) 既存ノードは古い設定を維持し、新しいノードだけが変更後の設定を使用する
- C) NodeClass を使用するノードにドリフトがマークされ、EKS が新しい設定を使用するノードに置き換える
- D) SSH で各ノードの kubelet を再起動する必要がある

<details>
<summary>回答を表示</summary>

**回答: C) NodeClass を使用するノードにドリフトがマークされ、EKS が新しい設定を使用するノードに置き換える**

**説明:**
`spec.advancedCompute.kubelet` の kubelet 設定は、ノードの作成時に適用されます。これらを編集すると既存ノードにドリフトが発生するため、EKS は実行中のノードを変更するのではなく置き換えます。まず PDB と中断予算を確認してください。`maxPods` は上限にすぎず、有効な値は、設定値、インスタンスタイプが提供する IP アドレス数、Auto Mode のノードあたり 110 Pod という上限のうち、最も低い値になります。

```yaml
# NodeClass fragment
advancedCompute:
  kubelet:
    maxPods: 60
    podPidsLimit: 4096
```

</details>
