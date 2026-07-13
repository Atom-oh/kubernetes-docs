# EKS Auto Mode Node ライフサイクルクイズ

> **関連ドキュメント**: [Node Lifecycle](../../eks-auto-mode/07-node-lifecycle.md)

## 選択問題

### 1. NodePool で Node を定期的に置き換えるための設定フィールド名は何ですか？

- A) `nodeLifetime`
- B) `maxAge`
- C) `expireAfter`
- D) `rotationPeriod`

<details>
<summary>回答を表示</summary>

**回答: C) `expireAfter`**

**解説:**
`expireAfter` フィールドを使用すると、セキュリティパッチや AMI 更新を適用するための定期的な Node 置き換えにおいて、最大 Node ライフタイムを設定できます。

```yaml
spec:
  template:
    spec:
      # Set maximum node lifetime
      expireAfter: 168h  # Auto-replace after 7 days
```

**一般的な設定:**
- 開発環境: 336h (14 日)
- Staging: 168h (7 日)
- Production: 72h ~ 168h (3-7 日)
- セキュリティが重要な環境: 24h ~ 48h (1-2 日)

</details>

### 2. expireAfter が設定された Node が期限切れになると何が起こりますか？

- A) Node が即座に削除される
- B) Node が cordon され、drain され、その後削除される
- C) 管理者に通知のみが送信される
- D) Node が自動的に再起動する

<details>
<summary>回答を表示</summary>

**回答: B) Node が cordon され、drain され、その後削除される**

**解説:**
Node が期限切れになると、Karpenter は graceful なプロセスを実行します。

1. **Cordon**: 新しい Pod スケジューリングをブロック
2. **Drain**: 既存の Pod を他の Node に移動
3. **Delete**: EC2 インスタンスを終了

このプロセス中は、PodDisruptionBudgets と Disruption Budgets が尊重されます。

```yaml
disruption:
  budgets:
    # Expiration-based replacement also follows this budget
    - nodes: "10%"
```

</details>

### 3. AL2023 と Bottlerocket のうち、より速い起動時間を提供する AMI はどれですか？

- A) AL2023
- B) Bottlerocket
- C) 同じ
- D) インスタンスタイプによる

<details>
<summary>回答を表示</summary>

**回答: B) Bottlerocket**

**解説:**
Bottlerocket はコンテナワークロード向けに最適化された OS であり、AL2023 より速い起動時間を提供します。

**起動時間の比較:**
| AMI | 起動時間 | 特徴 |
|-----|-----------|-----------------|
| AL2023 | 20-40 秒 | 汎用パッケージ、柔軟性 |
| Bottlerocket | 15-25 秒 | コンテナ専用、最小限の OS |

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: fast-boot
spec:
  amiFamily: Bottlerocket  # Fast boot
```

Bottlerocket の追加の利点:
- イミュータブルなルートファイルシステム
- 自動セキュリティ更新
- より小さい攻撃対象領域

</details>

### 4. AMI 更新によって既存の Node で Drift が検出されると何が起こりますか？

- A) Node がその場で自動的に更新される
- B) Node が新しい AMI で順次置き換えられる
- C) 管理者の承認後に置き換えられる
- D) 何も起こらない

<details>
<summary>回答を表示</summary>

**回答: B) Node が新しい AMI で順次置き換えられる**

**解説:**
新しい AMI が利用可能になると、EKS Auto Mode は Drift を検出し、Node を順次置き換えます。

**Drift 検出条件:**
- 新しい EKS optimized AMI のリリース
- NodeClass の amiFamily 変更
- Security group の変更
- Subnet 設定の変更

```yaml
# Drift-based replacement also follows Disruption Budget
disruption:
  budgets:
    - nodes: "10%"  # Only 10% replaced at a time
```

</details>

### 5. Node の鮮度を保つために expireAfter を短く設定する場合の潜在的なトレードオフは何ですか？

- A) コスト削減
- B) Node 置き換え頻度の増加による一時的なパフォーマンス低下の可能性
- C) セキュリティ脆弱性の増加
- D) Cluster の安定性向上

<details>
<summary>回答を表示</summary>

**回答: B) Node 置き換え頻度の増加による一時的なパフォーマンス低下の可能性**

**解説:**
短い expireAfter はセキュリティを強化しますが、次のようなトレードオフがあります。

**利点:**
- 最新のセキュリティパッチが適用される
- AMI 更新の迅速な適用
- Node drift の防止

**欠点:**
- Node 置き換え中の一時的な容量減少
- Pod の再スケジューリング増加
- Spot インスタンスでの追加中断の可能性

**推奨事項:**
```yaml
# Balanced setting
spec:
  template:
    spec:
      expireAfter: 168h  # 7 days
  disruption:
    budgets:
      - nodes: "10%"  # Limit concurrent replacement
```

</details>

### 6. Consolidation と Expiration が同時にトリガーされた場合、何が優先されますか？

- A) Consolidation が常に優先される
- B) Expiration が常に優先される
- C) Node 置き換え条件に先に到達したものが実行される
- D) 管理者が選択する必要がある

<details>
<summary>回答を表示</summary>

**回答: C) Node 置き換え条件に先に到達したものが実行される**

**解説:**
Karpenter は複数の disruption 理由を個別に評価し、条件が満たされたときに実行します。

**Disruption の優先順位（一般的な評価順序）:**
1. **Drift**: 設定変更または AMI 更新の検出
2. **Expiration**: expireAfter 時間の超過
3. **Consolidation**: 使用率の低い Node または空の Node

```yaml
# Example: 5-day-old underutilized node
# - expireAfter: 7 days -> Not expired yet
# - Consolidation condition met -> Replaced by Consolidation

# Example: 8-day-old normal utilization node
# - expireAfter: 7 days -> Expired
# - Replaced by Expiration
```

</details>

### 7. セキュリティパッチ適用のために Node をすぐに置き換える必要がある場合、どの方法を使用しますか？

- A) expireAfter を 0 に設定する
- B) Node に Drift annotation を追加する
- C) NodeClass を更新して Drift をトリガーする、または Node を drain する
- D) Cluster を再起動する

<details>
<summary>回答を表示</summary>

**回答: C) NodeClass を更新して Drift をトリガーする、または Node を drain する**

**解説:**
緊急のセキュリティパッチ適用方法:

**方法 1: NodeClass の更新（推奨）**
```yaml
# Trigger drift by changing tags or settings
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: default
spec:
  tags:
    SecurityPatch: "2025-02-19"  # Drift triggered by tag change
```

**方法 2: 手動 drain**
```bash
# Drain specific node
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# Delete node (Auto Mode provisions new node)
kubectl delete node <node-name>
```

**方法 3: ローリング置き換え**
```bash
# Sequentially replace all nodes
kubectl delete nodes -l karpenter.sh/nodepool=general-purpose
```

</details>

### 8. expireAfter を Never に設定するとどのような動作になりますか？

- A) Node が即座に期限切れになる
- B) 時間ベースの自動置き換えが無効になる
- C) 設定が無効化され、デフォルトが適用される
- D) エラーが発生する

<details>
<summary>回答を表示</summary>

**回答: B) 時間ベースの自動置き換えが無効になる**

**解説:**
`expireAfter: Never` を設定すると、時間ベースの Node expiration が無効になります。

```yaml
spec:
  template:
    spec:
      expireAfter: Never  # Disable time-based expiration
```

**注意事項:**
- Drift と Consolidation は引き続き機能する
- セキュリティパッチの適用が遅れる可能性がある
- 長時間実行されるワークロードにのみ推奨

**推奨されるユースケース:**
- Stateful ワークロード（データベース）
- 非常に長時間実行されるジョブ
- 手動メンテナンススケジュールがある環境

</details>
