# EKS Auto Mode スケーリング動作クイズ

> **関連ドキュメント**: [スケーリング動作](../../eks-auto-mode/03-scaling-behavior.md)

## 選択問題

### 1. NodePool の `consolidationPolicy: WhenEmptyOrUnderutilized` はどのように動作しますか？

- A) 空の node (ノード) のみを削除する
- B) 空の node と利用率の低い node の両方を統合する
- C) 常にすべての node を維持する
- D) 特定の時刻にのみ node を削除する

<details>
<summary>解答を表示</summary>

**解答: B) 空の node と利用率の低い node の両方を統合する**

**解説:**
`WhenEmptyOrUnderutilized` ポリシーは、コストを最適化するために、空の node だけでなく利用率の低い node も統合します。これにより、複数の利用率の低い node 上の workload を、より少ない node に統合できます。

```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 1m  # Consolidate 1 minute after condition is met
```

**比較:**
- `WhenEmpty`: 空の node のみを削除する（保守的）
- `WhenEmptyOrUnderutilized`: 空の node + 利用率の低い node を統合する（積極的）

</details>

### 2. NodeClaim のステータスを確認する kubectl コマンドはどれですか？

- A) `kubectl get nodes --show-claims`
- B) `kubectl get nodeclaims`
- C) `kubectl describe karpenter claims`
- D) `kubectl get ec2-nodes`

<details>
<summary>解答を表示</summary>

**解答: B) `kubectl get nodeclaims`**

**解説:**
NodeClaim は、プロビジョニング中の node の状態を表す resource です。

```bash
# List NodeClaims
kubectl get nodeclaims

# Detailed information for specific NodeClaim
kubectl describe nodeclaim <name>

# View NodeClaims with node information
kubectl get nodeclaims -o wide
```

</details>

### 3. Auto Mode で Pending Pod が発生したとき、どの条件で node のプロビジョニングが開始されますか？

- A) Pod が 5 分を超えて Pending になっている場合
- B) NodePool の要件を満たす node がない場合
- C) node の総数がしきい値を下回った場合
- D) 手動のスケールアップコマンドが実行された場合

<details>
<summary>解答を表示</summary>

**解答: B) NodePool の要件を満たす node がない場合**

**解説:**
Auto Mode は Pending Pod の要件を分析し、適切な node が存在しない場合はすぐに新しい node をプロビジョニングします。

**プロビジョニングフロー:**
1. Pod が Pending 状態になる
2. Karpenter が Pod のリソースリクエスト、nodeSelector、affinity を分析する
3. 適切な NodePool の要件を確認する
4. 最適なインスタンスタイプを選択する
5. EC2 instance を起動する（40〜90 秒）

</details>

### 4. Consolidation が発生しないのはどのケースですか？

- A) node に do-not-disrupt annotation がある場合
- B) node に DaemonSet Pod しかない場合
- C) consolidateAfter の時間が経過していない場合
- D) 上記すべて

<details>
<summary>解答を表示</summary>

**解答: D) 上記すべて**

**解説:**
Consolidation は次の状況では発生しません。

1. **do-not-disrupt annotation**: この annotation がある node または Pod は Consolidation から除外されます
2. **DaemonSet Pod のみ**: DaemonSet はすべての node で実行されるため、空の node として扱われます
3. **consolidateAfter が経過していない**: 条件が満たされた後、指定された時間待機する必要があります

```yaml
metadata:
  annotations:
    karpenter.sh/do-not-disrupt: "true"
```

</details>

### 5. Drift 検出をトリガーする状況はどれですか？

- A) NodeClass spec が変更された場合
- B) 新しい AMI が利用可能になった場合
- C) security group が変更された場合
- D) 上記すべて

<details>
<summary>解答を表示</summary>

**解答: D) 上記すべて**

**解説:**
Drift 検出は、node の現在の状態が望ましい状態と異なる場合にトリガーされます。

- **NodeClass の変更**: AMI family、subnet、security group などが変更された
- **新しい AMI**: EKS optimized AMI が更新された
- **security group の変更**: 参照されている security group が変更された

Drift が検出されると、node は順番に置き換えられます。

</details>

### 6. node のプロビジョニング速度を最適化するために推奨される AMI family はどれですか？

- A) AL2023
- B) Bottlerocket
- C) Ubuntu
- D) Amazon Linux 2

<details>
<summary>解答を表示</summary>

**解答: B) Bottlerocket**

**解説:**
Bottlerocket は container 専用に設計された OS で、AL2023 よりも高速な起動時間を提供します。

**起動時間の比較:**
- **AL2023**: 20-40 seconds
- **Bottlerocket**: 15-25 seconds

Bottlerocket の追加の利点:
- 攻撃対象領域が小さい
- immutable file system
- 自動 security update

</details>
