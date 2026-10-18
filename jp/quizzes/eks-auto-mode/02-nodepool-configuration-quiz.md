# EKS Auto Mode NodePool 設定クイズ

> **関連ドキュメント**: [NodePool 設定](../../eks-auto-mode/02-nodepool-configuration.md)

## 選択問題

### 1. EKS Auto Mode が提供する任意選択の組み込み NodePool はどれですか？

- A) default、worker
- B) general-purpose、system
- C) compute、memory
- D) primary、secondary

<details>
<summary>解答を表示</summary>

**解答: B) general-purpose、system**

**解説:**
有効にすると、`general-purpose` と `system` は第 5 世代以降の On-Demand C/M/R インスタンスを使用します。general-purpose は amd64、system は amd64 と arm64 をサポートし、`CriticalAddonsOnly` taint が付与されます。Spot を使う場合はカスタムプールを使用してください。Auto Mode のローカル DNS／サービスネットワーク機能は、system プールにスケジュールする通常の Pod ではありません。

```yaml
# eksctl configuration fragment
autoModeConfig:
  enabled: true
  nodePools: [general-purpose, system]
```

組み込みプールの名前を削除すると、その NodePool も削除され、管理対象ノードは drain されて終了します。両方を無効にする場合は、`default` が存在すると想定せず、カスタム NodeClass を用意する必要があります。

</details>

### 2. Auto Mode ノードの IMDS はどのように設定されていますか？

- A) NodeClass で `metadataOptions.httpTokens: optional` を設定する
- B) AWS が IMDSv2 と hop limit 1 を強制し、NodeClass からこれらを上書きできない
- C) IMDSv2 を使うため hop limit を 0 にする
- D) AL2023 を選ぶと IMDS 認証が無効になる

<details>
<summary>解答を表示</summary>

**解答: B) AWS が IMDSv2 と hop limit 1 を強制し、NodeClass からこれらを上書きできない**

**解説:**
管理対象インスタンスの既定値では IMDSv2 と hop limit 1 が必須で、Auto Mode では変更できません。以前の `metadataOptions` の例は別の API のものでした。hop limit は hostNetwork を使わない Pod からのアクセスを制限しますが、hostNetwork のワークロードを含むすべての Pod が隔離される保証ではありません。ノード認証情報に頼らず、ワークロード ID とリージョンや設定の明示を使ってください。[管理対象インスタンスの制約](https://docs.aws.amazon.com/eks/latest/userguide/automode-learn-instances.html)を参照してください。

</details>

### 3. Auto Mode ノードのオペレーティングシステムイメージを選択するのは誰ですか？

- A) ユーザーが `amiFamily` で Amazon Linux 2 または Ubuntu を選ぶ
- B) AWS が適切な管理対象 Bottlerocket バリアントを選択する
- C) ユーザーが任意の Windows AMI を指定する
- D) NodePool の weight によって AL2023 と Bottlerocket のどちらを使うか決まる

<details>
<summary>解答を表示</summary>

**解答: B) AWS が適切な管理対象 Bottlerocket バリアントを選択する**

**解説:**
Auto Mode は AWS 管理の Bottlerocket バリアントを使用します。AWS NodeClass では `amiFamily: AL2023` や `amiFamily: Bottlerocket` を選択できません。ストレージ、ネットワーク、証明書、サポート対象のカーネル設定については、ドキュメントに記載された NodeClass の設定を使用してください。任意の AMI 選択やシェルの user data とは異なります。

</details>

### 4. Auto Mode で GPU の製造元を選択する NodePool ラベルはどれですか？

- A) karpenter.k8s.aws/gpu-vendor
- B) eks.amazonaws.com/instance-gpu-manufacturer
- C) nvidia.com/gpu-family
- D) karpenter.sh/gpu-type

<details>
<summary>解答を表示</summary>

**解答: B) eks.amazonaws.com/instance-gpu-manufacturer**

**解説:**
AWS Auto Mode のラベル `eks.amazonaws.com/instance-gpu-manufacturer` を使用します。NVIDIA GPU ハードウェアを使う場合、要件には次のように指定できます。

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

ハードウェアを選択しても、コンテナに GPU が割り当てられるわけではありません。Pod が `nvidia.com/gpu` などの適切な拡張リソースを要求し、互換性のあるイメージ／ランタイムを使う必要があります。この監査では GPU の実行確認をしていません。

</details>

### 5. EC2 の第 6 世代以降を選択する条件はどれですか？

- A) node.kubernetes.io/instance-generation: "6"
- B) eks.amazonaws.com/instance-generation に `Gt` と値 "5" を指定する
- C) eks.amazonaws.com/generation: "6"
- D) instance-generation: 6

<details>
<summary>解答を表示</summary>

**解答: B) eks.amazonaws.com/instance-generation に `Gt` と値 "5" を指定する**

**解説:**
`Gt` は数値の厳密な下限を表すため、`Gt ["5"]` は第 6 世代以降を選択します。`In ["6"]` は第 6 世代だけを選択し、同じ意味ではありません。どちらも最新世代だけを指定する条件ではありません。

```yaml
# Requirements fragment inside a complete NodePool
requirements:
  - key: eks.amazonaws.com/instance-generation
    operator: Gt
    values: ["5"]
```

</details>

### 6. NodeClass でプライベートサブネットを選択するにはどうすればよいですか？

- A) `subnetType: private` を設定する
- B) 確認済みのサブネット ID／タグを選び、ルートと IP 設定を検証する
- C) `privateSubnetsOnly: true` を設定する
- D) `networkType: private` を設定する

<details>
<summary>解答を表示</summary>

**解答: B) 確認済みのサブネット ID／タグを選び、ルートと IP 設定を検証する**

**解説:**
`subnetSelectorTerms` では ID またはタグを使って選択します。`kubernetes.io/role/internal-elb` などのタグは慣例であり、プライベートなルートテーブルを使っている証拠ではありません。複数の term は選択肢として扱われ、1 つの term 内の複数のタグはすべて一致する必要があります。VPC／AZ の選択、ルート、パブリック IP の動作を確認してください。

```yaml
# Selection fragment; a complete NodeClass also needs identity and security groups
subnetSelectorTerms:
  - tags:
      kubernetes.io/role/internal-elb: "1"
      Environment: production
advancedNetworking:
  associatePublicIPAddress: false
```

`associatePublicIPAddress: false` を設定しても、パブリック IP の割り当てが防がれるだけで、NAT ルートや VPC endpoint が作られるわけではありません。NodeClass に必要な identity と security group の設定をすべて用意し、Ready 状態を検証してください。

</details>
