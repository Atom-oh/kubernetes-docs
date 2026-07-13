# EKS Auto Mode 移行ガイド クイズ

> **関連ドキュメント**: [移行ガイド](../../eks-auto-mode/09-migration-guide.md)

## 選択問題

### 1. managed node group から Auto Mode へ移行する際の最初のステップは何ですか？

- A) 既存の node group をすぐに削除する
- B) 現在の状態を分析する（node のリソース使用率、workload の分散を確認）
- C) Auto Mode NodePool を作成する
- D) すべての Pod を drain する

<details>
<summary>回答を表示</summary>

**回答: B) 現在の状態を分析する（node のリソース使用率、workload の分散を確認）**

**解説:**
移行の最初のステップは、現在の環境を十分に分析することです。

**移行ステップ:**
1. **現在の状態を分析する** - node group、リソース使用率、workload の分散を確認する
2. Auto Mode を有効にする
3. NodePool を設定する
4. workload を移行する
5. 既存の node group をスケールダウンする
6. 既存の node group を削除する
7. 検証して最適化する

```bash
# Check current node groups
eksctl get nodegroup --cluster my-cluster

# Analyze node resource usage
kubectl top nodes

# Check workload distribution
kubectl get pods -A -o wide | awk '{print $8}' | sort | uniq -c
```

</details>

### 2. 移行中に既存の node group と Auto Mode を共存させるにはどうしますか？

- A) 不可能で、順番に進める必要がある
- B) nodeSelector を使用して workload を分離する
- C) 別の cluster が必要
- D) AWS Support チケットが必要

<details>
<summary>回答を表示</summary>

**回答: B) nodeSelector を使用して workload を分離する**

**解説:**
共存期間中は、nodeSelector と affinity を使用して workload を分離します。

```yaml
# Workloads pinned to existing node groups
apiVersion: apps/v1
kind: Deployment
metadata:
  name: legacy-critical-app
spec:
  template:
    spec:
      nodeSelector:
        eks.amazonaws.com/nodegroup: old-nodegroup

---
# Workloads that can be migrated to Auto Mode
apiVersion: apps/v1
kind: Deployment
metadata:
  name: migrated-app
spec:
  template:
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: karpenter.sh/nodepool
                    operator: Exists
```

</details>

### 3. workload を段階的に移行する際の推奨順序はどれですか？

- A) Production -> Staging -> Development
- B) Development -> Staging -> Production（重要度の低い workload から）
- C) すべての workload を同時に移行する
- D) ランダムな順序

<details>
<summary>回答を表示</summary>

**回答: B) Development -> Staging -> Production（重要度の低い workload から）**

**解説:**
段階的な移行によりリスクを最小化できます。

```yaml
# Step 1: Migrate non-critical workloads
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dev-app
spec:
  template:
    spec:
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              preference:
                matchExpressions:
                  - key: node-type
                    operator: In
                    values: ["auto-mode"]
```

**移行順序:**
1. Development 環境の workload
2. Staging workload
3. Production の重要度の低い workload
4. Production の重要 workload

</details>

### 4. rollback が必要な場合の手順の順序はどれですか？

- A) cluster を削除して再作成する
- B) NodePool を削除する -> 既存の node group をスケールアップする -> workload を移行する
- C) AWS Support に連絡する
- D) Auto Mode のみを無効にする

<details>
<summary>回答を表示</summary>

**回答: B) NodePool を削除する -> 既存の node group をスケールアップする -> workload を移行する**

**解説:**
rollback は逆の順序で進めます。

```bash
#!/bin/bash
# rollback.sh

# 1. Disable Auto Mode NodePool
kubectl delete nodepool migration-pool

# 2. Scale up existing node groups
eksctl scale nodegroup \
    --cluster my-cluster \
    --name old-nodegroup \
    --nodes 10 \
    --nodes-min 3

# 3. Migrate workloads back to existing nodes
kubectl patch deployment migrated-app -p '
{
  "spec": {
    "template": {
      "spec": {
        "nodeSelector": {
          "eks.amazonaws.com/nodegroup": "old-nodegroup"
        },
        "affinity": null
      }
    }
  }
}'

# 4. Drain Auto Mode Pods
for node in $(kubectl get nodes -l karpenter.sh/nodepool=migration-pool -o name); do
    kubectl drain $node --ignore-daemonsets --delete-emptydir-data
done
```

</details>

### 5. 既存の node group を段階的にスケールダウンする推奨方法は何ですか？

- A) すぐに 0 までスケールダウンする
- B) 安定化確認を行いながら 50% ずつ段階的にスケールダウンする
- C) 1 だけスケールダウンする
- D) すべての node を同時に drain する

<details>
<summary>回答を表示</summary>

**回答: B) 安定化確認を行いながら 50% ずつ段階的にスケールダウンする**

**解説:**
段階的なスケールダウンにより、サービスへの影響を最小化できます。

```bash
#!/bin/bash
CLUSTER="my-cluster"
NODEGROUP="old-nodegroup"
CURRENT_SIZE=$(eksctl get nodegroup --cluster $CLUSTER --name $NODEGROUP -o json | jq -r '.[0].DesiredCapacity')

# Scale down by 50%
while [ $CURRENT_SIZE -gt 0 ]; do
    NEW_SIZE=$((CURRENT_SIZE / 2))
    if [ $NEW_SIZE -lt 1 ]; then
        NEW_SIZE=0
    fi

    echo "Scaling from $CURRENT_SIZE to $NEW_SIZE"
    eksctl scale nodegroup --cluster $CLUSTER --name $NODEGROUP \
        --nodes $NEW_SIZE --nodes-min 0

    # Wait for stabilization
    sleep 300

    # Check workload status
    kubectl get pods -A --field-selector=status.phase=Pending

    CURRENT_SIZE=$NEW_SIZE
done
```

</details>

### 6. 移行中に監視すべき主要な metric に該当しないものはどれですか？

- A) Pending Pod 数
- B) Node プロビジョニング時間
- C) EC2 instance コスト
- D) workload の可用性

<details>
<summary>回答を表示</summary>

**回答: C) EC2 instance コスト**

**解説:**
移行中はサービスの安定性が最優先であるため、次の metric を監視します。

| Metric | Normal Range | Alarm Condition |
|--------|--------------|-----------------|
| Pending Pod 数 | 0-5 | 5 分間 > 10 |
| Node プロビジョニング時間 | < 90 秒 | > 120 秒 |
| workload の可用性 | > 99.9% | < 99.5% |
| API 応答時間 | < 200ms | > 500ms |

コストは、移行完了後の最適化フェーズで確認します。

```bash
# Real-time monitoring
watch -n 5 'echo "=== Pending Pods ===" && \
kubectl get pods -A --field-selector=status.phase=Pending && \
echo "=== Node Status ===" && kubectl get nodes -o wide'
```

</details>

### 7. 移行完了後に確認する項目ではないものはどれですか？

- A) すべての workload が正常に実行されていることを確認する
- B) Auto Mode node 上の Pod 分散を確認する
- C) 既存の node group の削除完了
- D) NodePool の状態を確認する

<details>
<summary>回答を表示</summary>

**回答: C) 既存の node group の削除完了**

**解説:**
検証時点では、rollback の選択肢を維持するために既存の node group を保持します。安定性を確認した後に削除を進めます。

**検証チェックリスト:**
1. すべての Pod が Running 状態であることを確認する
2. Auto Mode node 上の workload 分散を確認する
3. NodePool と NodeClaim が正常な状態であること
4. Application のパフォーマンステスト
5. log と metric の収集が正常であること
6. **一定期間（1〜2 週間）安定性を確認した後、既存の node group を削除する**

</details>

### 8. Karpenter を直接使用している cluster から Auto Mode へ移行する際の注意点は何ですか？

- A) 直接移行できる
- B) 既存の Karpenter リソースと競合する可能性があるため、Karpenter を削除してから移行する
- C) 同時運用が推奨される
- D) 追加コストが発生する

<details>
<summary>回答を表示</summary>

**回答: B) 既存の Karpenter リソースと競合する可能性があるため、Karpenter を削除してから移行する**

**解説:**
Auto Mode は内部で Karpenter を使用するため、既存の self-managed Karpenter と競合する可能性があります。

**移行手順:**
1. 既存の Karpenter NodePool 設定をバックアップする
2. Karpenter 管理下の workload を一時的に managed node group に移行する
3. self-managed Karpenter を削除する
4. Auto Mode を有効にする
5. Auto Mode NodePool を設定する（バックアップを参照）
6. workload を移行する

```bash
# Verify before removing Karpenter
kubectl get nodepools
kubectl get nodeclaims
kubectl get nodes -l karpenter.sh/nodepool

# Remove Karpenter
helm uninstall karpenter -n karpenter
kubectl delete namespace karpenter
```

</details>
