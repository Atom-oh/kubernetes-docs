# EKS Auto Mode Operations Quiz

> **関連ドキュメント**: [Operations](../../eks-auto-mode/05-operations.md)

## 選択式問題

### 1. 営業時間中の node 中断を最小限に抑えるための NodePool Disruption Budget 設定はどれですか?

- A) `nodes: "100%"`
- B) schedule 付きの `nodes: "0"`
- C) `consolidateAfter: 0s`
- D) `consolidationPolicy: Never`

<details>
<summary>答えを表示</summary>

**答え: B) schedule 付きの `nodes: "0"`**

**解説:**
schedule と一緒に `nodes: "0"` を設定すると、特定の時間帯に node 中断を完全に防止できます。

```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
  budgets:
    # Default: Only 10% of total nodes can be disrupted simultaneously
    - nodes: "10%"

    # Business hours: No disruptions
    - nodes: "0"
      schedule: "0 9-18 * * mon-fri"  # Mon-Fri 9-18
      duration: 9h
```

</details>

### 2. PodDisruptionBudget (PDB) における `minAvailable: 80%` は何を意味しますか?

- A) 最大 80% の Pod を実行できる
- B) 最低 80% の Pod が常に running でなければならない
- C) Pod 保持の確率が 80%
- D) Pod を 80 秒間保護する

<details>
<summary>答えを表示</summary>

**答え: B) 最低 80% の Pod が常に running でなければならない**

**解説:**
PDB の `minAvailable` は、常に running でなければならない Pod の最小数または割合を指定します。

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  minAvailable: 80%
  selector:
    matchLabels:
      app: web
```

または、`maxUnavailable` を使用できます:
```yaml
spec:
  maxUnavailable: 1  # Only 1 Pod can be disrupted simultaneously
```

</details>

### 3. Auto Mode の node 問題を診断するとき、最初に確認すべき resource はどれですか?

- A) Pod logs
- B) NodeClaim status
- C) EC2 console
- D) CloudWatch metrics

<details>
<summary>答えを表示</summary>

**答え: B) NodeClaim status**

**解説:**
NodeClaim は、node provisioning のプロセスと status を追跡する key resource です。

```bash
# Check NodeClaim status
kubectl get nodeclaims

# Check details and events
kubectl describe nodeclaim <name>

# Check provisioning failure causes
kubectl get nodeclaims -o yaml | grep -A 10 status
```

典型的な troubleshooting の順序:
1. NodeClaim status を確認する
2. NodePool configuration を確認する
3. IAM roles/policies を検証する
4. subnets/security groups を検証する

</details>

### 4. do-not-disrupt annotation の正しい使い方はどれですか?

- A) `kubernetes.io/do-not-disrupt: "true"`
- B) `karpenter.sh/do-not-disrupt: "true"`
- C) `eks.amazonaws.com/no-disrupt: "true"`
- D) `node.kubernetes.io/exclude-disruption: "true"`

<details>
<summary>答えを表示</summary>

**答え: B) `karpenter.sh/do-not-disrupt: "true"`**

**解説:**
この annotation を Pod または Node に追加すると、Karpenter の consolidation または drift replacement から除外されます。

```yaml
# Apply to Pod
apiVersion: v1
kind: Pod
metadata:
  name: critical-pod
  annotations:
    karpenter.sh/do-not-disrupt: "true"
spec:
  containers:
    - name: app
      image: myapp:latest

# Apply to Node
kubectl annotate node <node-name> karpenter.sh/do-not-disrupt=true
```

</details>

### 5. Auto Mode cluster の node status を monitoring するための推奨 tool はどれですか?

- A) kubectl top nodes のみ
- B) Container Insights + kubectl の組み合わせ
- C) EC2 console で直接確認する
- D) AWS CLI のみ

<details>
<summary>答えを表示</summary>

**答え: B) Container Insights + kubectl の組み合わせ**

**解説:**
効果的な monitoring には tool を組み合わせて使用します。

```bash
# Real-time monitoring
watch -n 5 'echo "=== Pending Pods ===" && \
kubectl get pods -A --field-selector=status.phase=Pending && \
echo "=== Node Status ===" && kubectl get nodes -o wide'

# Check resource usage
kubectl top nodes
kubectl top pods -A

# Check NodePool status
kubectl get nodepools
kubectl describe nodepool <name>
```

Container Insights metrics:
- Node CPU/memory utilization
- Pod scheduling latency
- Container restart count

</details>

### 6. Day-2 operations で node updates を自動化するには、どの NodePool field を設定すべきですか?

- A) `autoUpdate: true`
- B) `expireAfter` setting
- C) `updatePolicy: Rolling`
- D) `refreshInterval: 24h`

<details>
<summary>答えを表示</summary>

**答え: B) `expireAfter` setting**

**解説:**
`expireAfter` を設定すると、指定した時間後に node が自動的に置き換えられ、最新の AMI と security patches が適用されます。

```yaml
spec:
  template:
    spec:
      expireAfter: 168h  # Auto-replace after 7 days
```

Day-2 operations automation settings:
- `expireAfter`: 定期的な node replacement
- `consolidationPolicy`: Cost optimization
- Disruption Budget: service impact の最小化

</details>

### 7. production environment での rolling updates に推奨される Disruption Budget 設定はどれですか?

- A) 高速 updates のための `nodes: "100%"`
- B) 段階的な updates のための `nodes: "10%"` または absolute value
- C) Disruption Budget を無効にする
- D) 中程度の速度のための `nodes: "50%"`

<details>
<summary>答えを表示</summary>

**答え: B) 段階的な updates のための `nodes: "10%"` または absolute value**

**解説:**
production environment では、service impact を最小限に抑えながら段階的に update します。

```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
  budgets:
    # Default: Gradual replacement at 10%
    - nodes: "10%"

    # Peak hours: More conservative
    - nodes: "1"
      schedule: "0 9-18 * * mon-fri"
      duration: 9h

    # Maintenance window: More aggressive
    - nodes: "30%"
      schedule: "0 2-4 * * sun"
      duration: 2h
```

</details>

### 8. Auto Mode node 関連の CloudWatch alarms における key metrics はどれですか?

- A) EC2 instance status のみ
- B) Pending Pod count、node provisioning time、workload availability
- C) Cost metrics のみ
- D) Network traffic のみ

<details>
<summary>答えを表示</summary>

**答え: B) Pending Pod count、node provisioning time、workload availability**

**解説:**
Auto Mode operations で monitoring すべき key metrics:

| Metric | Normal Range | Alarm Condition |
|--------|--------------|-----------------|
| Pending Pod count | 0-5 | > 10 for 5 min |
| Node provisioning time | < 90 sec | > 120 sec |
| Workload availability | > 99.9% | < 99.5% |
| API response time | < 200ms | > 500ms |

これらの metrics を自動的に収集するには、CloudWatch Container Insights を有効にします。

</details>
