# EKS Auto Mode Spot Strategies Quiz

> **関連ドキュメント**: [Spot Instance Strategies](../../eks-auto-mode/04-spot-strategies.md)

## 選択式問題

### 1. Spot Instance の中断リスクを分散するための最適な戦略は何ですか?

- A) 単一の instance type のみを使用する
- B) 多様な instance family、generation、size を使用する
- C) On-Demand のみを使用する
- D) 最も安価な instance のみを選択する

<details>
<summary>答えを表示</summary>

**答え: B) 多様な instance family、generation、size を使用する**

**解説:**
Spot Instance は capacity pool ごとに中断が発生します。多様な instance type を許可すると、複数の capacity pool から instance を取得できるため、中断リスクを分散できます。

```yaml
spec:
  template:
    spec:
      requirements:
        # Diverse instance families
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r", "i", "d"]
        # Diverse generations
        - key: karpenter.k8s.aws/instance-generation
          operator: In
          values: ["5", "6", "7"]
        # Diverse sizes
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["large", "xlarge", "2xlarge"]
        # Diverse architectures
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
```

</details>

### 2. Spot Instance と On-Demand Instance を区別する Karpenter label key は何ですか?

- A) `node.kubernetes.io/capacity-type`
- B) `karpenter.sh/capacity-type`
- C) `eks.amazonaws.com/instance-type`
- D) `karpenter.k8s.aws/spot-or-ondemand`

<details>
<summary>答えを表示</summary>

**答え: B) `karpenter.sh/capacity-type`**

**解説:**
この label により、Pod の nodeAffinity または NodePool requirements で Spot/On-Demand Instance を指定できます。

```yaml
# Setting Spot instance preference in Pod
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        preference:
          matchExpressions:
            - key: karpenter.sh/capacity-type
              operator: In
              values: ["spot"]
```

</details>

### 3. Spot Instance が中断される前にデフォルトで与えられる警告時間はどれですか?

- A) 30 秒
- B) 2 分
- C) 5 分
- D) 10 分

<details>
<summary>答えを表示</summary>

**答え: B) 2 分**

**解説:**
AWS Spot Instance は回収される前に 2 分前の警告が与えられます。Workload はこの時間内に正常に終了する必要があります。

**Spot Interrupt Handling のベストプラクティス:**
- Pod の terminationGracePeriodSeconds を 2 分以下に設定する
- application に SIGTERM handler を実装する
- stateless Workload を優先する
- checkpointing mechanism を実装する（batch job の場合）

</details>

### 4. Spot Instance に推奨されない Workload type はどれですか?

- A) Batch processing job
- B) Stateless web server
- C) Single-instance database
- D) Development/test environment

<details>
<summary>答えを表示</summary>

**答え: C) Single-instance database**

**解説:**
Single-instance database は中断時に可用性の問題が発生する可能性があるため、Spot には適していません。

**Spot に適した Workload:**
- Batch processing / Big data analytics
- CI/CD pipeline
- Stateless web server (Auto Scaling)
- Development/test environment
- Container-based microservice

**On-Demand が必要な Workload:**
- Database
- Message queue
- Cluster management component
- Long-running stateful job

</details>

### 5. NodePool で Spot と On-Demand を混在させる場合、Spot-first selection をどのように設定しますか?

- A) `spotPriority: high`
- B) weight value による NodePool priority 設定
- C) `capacityPriority: spot`
- D) `preferSpot: true`

<details>
<summary>答えを表示</summary>

**答え: B) weight value による NodePool priority 設定**

**解説:**
複数の NodePool を作成し、weight value で priority を指定します。より高い weight が先に使用されます。

```yaml
# Spot-first NodePool (weight: 100)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot-first
spec:
  weight: 100  # High priority
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
---
# On-Demand fallback NodePool (weight: 10)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ondemand-fallback
spec:
  weight: 10  # Low priority
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
```

</details>

### 6. Spot Instance は On-Demand と比較して最大でどの程度の削減率になりますか?

- A) 30-40%
- B) 50-60%
- C) 70-90%
- D) 95% 以上

<details>
<summary>答えを表示</summary>

**答え: C) 70-90%**

**解説:**
Spot Instance は On-Demand と比較して最大 70-90% のコスト削減を実現できます。

**Cost Optimization Strategy の組み合わせ:**
| Strategy | Expected Savings |
|----------|-----------------|
| Spot instances | 70-90% |
| Graviton (ARM) | ~20% |
| Spot + Graviton | Up to 90% |

ただし、Spot の削減率は instance type と availability zone によって異なります。

</details>
