# 運用と管理

> **対応バージョン**: EKS 1.29+, EKS Auto Mode GA
> **最終更新**: February 19, 2026

このガイドでは、Disruption Budget（中断予算）、Rolling Replacement、モニタリング、トラブルシューティング、セキュリティのベストプラクティスなど、EKS Auto Mode の運用面について説明します。

---

## Disruption Budget 設定

安全な Node 置き換えのために Budget を設定します。

```yaml
# disruption-budget.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: production-pool
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
      # Default: only 10% of total nodes disrupted simultaneously
      - nodes: "10%"

      # Business hours: minimize disruptions
      - nodes: "1"
        schedule: "0 9-18 * * mon-fri"  # Mon-Fri 9-18
        duration: 9h

      # Weekends: allow more aggressive consolidation
      - nodes: "30%"
        schedule: "0 0 * * sat-sun"
        duration: 48h

      # Emergency maintenance window: no disruptions
      - nodes: "0"
        schedule: "0 0 1 * *"  # 1st of each month
        duration: 24h
```

---

## Rolling Replacement 戦略

```yaml
# rolling-replacement-strategy.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: rolling-replacement
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      # Node expiration time
      expireAfter: 168h  # 7 days
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 2m
    budgets:
      # Limit concurrent disrupted nodes for sequential replacement
      - nodes: "1"
```

### Node Replacement 戦略の比較

| 戦略 | ユースケース | 設定 | トレードオフ |
|----------|----------|---------------|------------|
| **Rolling (Conservative)** | 本番環境の重要用途 | `nodes: "1"` | 遅いがより安全 |
| **Rolling (Moderate)** | 標準的な本番環境 | `nodes: "10%"` | バランスの取れたアプローチ |
| **Aggressive** | Dev/Test、バッチ | `nodes: "30%"` | 高速だがリスクが高い |
| **Scheduled** | メンテナンスウィンドウ | 時間ベースの Budget | 予測可能な中断 |

### 各戦略を使用するタイミング

- **Rolling (Conservative)**: Stateful workload、データベース、重要な API
- **Rolling (Moderate)**: 標準的な Web Service、microservice
- **Aggressive**: CI/CD runner、バッチ処理、開発環境
- **Scheduled**: コンプライアンス要件、計画メンテナンス

---

## PodDisruptionBudget との統合

```yaml
# pdb-example.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
spec:
  # Minimum available Pods
  minAvailable: 3
  # Or maximum unavailable Pods
  # maxUnavailable: 1
  selector:
    matchLabels:
      app: web-app
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 5
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
        - name: web
          image: nginx:latest
          resources:
            requests:
              cpu: 500m
              memory: 256Mi
      # Graceful shutdown during node replacement
      terminationGracePeriodSeconds: 60
```

### PDB のベストプラクティス

| Workload タイプ | Replica 数 | PDB 設定 |
|---------------|----------|-------------------|
| Stateless (3+ replicas) | 3-10 | `minAvailable: N-1` または `maxUnavailable: 1` |
| Stateless (10+ replicas) | 10+ | `maxUnavailable: 10%` |
| Stateful | 3+ | `minAvailable: 2`（quorum を維持） |
| Singleton | 1 | PDB なし（または中断を許容） |

---

## Zone 障害への対応

### Multi-AZ Deployment 設定

```yaml
# multi-az-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: high-availability-app
spec:
  replicas: 6
  selector:
    matchLabels:
      app: ha-app
  template:
    metadata:
      labels:
        app: ha-app
    spec:
      # Availability zone distribution
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: ha-app
        # Node distribution
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: ha-app
      containers:
        - name: app
          image: my-app:latest
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
---
# NodePool for guaranteed minimum nodes per zone
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: multi-az-pool
spec:
  template:
    spec:
      requirements:
        - key: topology.kubernetes.io/zone
          operator: In
          values: ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  # Guarantee minimum capacity per zone
  limits:
    cpu: 1000
```

### Availability Zone 障害対応パターン

| パターン | 説明 | 実装 |
|---------|-------------|----------------|
| **Active-Active** | すべての AZ がトラフィックを処理 | `DoNotSchedule` を使用した `topologySpreadConstraints` |
| **Active-Standby** | セカンダリ AZ へフェイルオーバー | Pod anti-affinity + health check |
| **Capacity Reservation** | 事前にプロビジョニングされた Capacity | On-Demand Capacity Reservations |
| **Overflow** | 他の AZ へバースト | `ScheduleAnyway` 制約 |

---

## CloudWatch モニタリング

EKS Auto Mode はメトリクスを CloudWatch に自動的に送信します。

```bash
# CloudWatch metric namespaces
# - AWS/EKS
# - Karpenter

# Key metrics
# - karpenter_nodes_total: Total node count
# - karpenter_pods_pending: Pending Pod count
# - karpenter_nodeclaims_created: Created NodeClaim count
# - karpenter_nodeclaims_terminated: Terminated NodeClaim count
```

### CloudWatch Dashboard セットアップ

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "title": "Auto Mode Node Count",
        "metrics": [
          ["Karpenter", "karpenter_nodes_total", "cluster", "my-cluster"]
        ],
        "period": 60
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Pending Pods",
        "metrics": [
          ["Karpenter", "karpenter_pods_pending", "cluster", "my-cluster"]
        ],
        "period": 60
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Node Provisioning Time",
        "metrics": [
          ["Karpenter", "karpenter_nodeclaims_startup_duration_seconds", "cluster", "my-cluster"]
        ],
        "stat": "p99",
        "period": 300
      }
    }
  ]
}
```

---

## kubectl ベースの診断

```bash
# Check NodePool status
kubectl get nodepools
kubectl describe nodepool general-purpose

# Check NodeClaim status (nodes being provisioned)
kubectl get nodeclaims
kubectl describe nodeclaim <name>

# Check node status and labels
kubectl get nodes -o wide -L karpenter.sh/nodepool,karpenter.sh/capacity-type

# Check Pending Pods
kubectl get pods -A --field-selector=status.phase=Pending

# Check events
kubectl get events --sort-by='.lastTimestamp' | grep -E "karpenter|nodepool|nodeclaim"

# Node resource usage
kubectl top nodes

# Pod distribution by node
kubectl get pods -A -o wide | awk '{print $8}' | sort | uniq -c | sort -rn
```

---

## よくある問題と解決策

### 問題 1: Pod が Pending 状態のままになる

```bash
# Analyze cause
kubectl describe pod <pending-pod>

# Common causes:
# 1. Resource requests too large
# 2. NodePool limits exceeded
# 3. nodeSelector/affinity condition mismatch
# 4. taint/toleration mismatch

# Solution: Check NodePool limits
kubectl get nodepool -o yaml | grep -A5 limits

# Solution: Check nodeSelector conditions
kubectl get pod <pending-pod> -o yaml | grep -A10 nodeSelector
```

### 問題 2: Node Provisioning 失敗

```bash
# Check NodeClaim status
kubectl describe nodeclaim <name>

# Check error messages in events
kubectl get events --field-selector reason=FailedProvisioning

# Common causes:
# 1. Instance capacity shortage
# 2. Subnet IP exhaustion
# 3. IAM permission issues
# 4. Security group configuration errors

# Solution: Allow more diverse instance types
# Expand NodePool requirements
```

### 問題 3: Node Consolidation が機能しない

```bash
# Check Consolidation status
kubectl get nodeclaims -o custom-columns=\
NAME:.metadata.name,\
NODEPOOL:.metadata.labels.karpenter\\.sh/nodepool,\
PHASE:.status.phase,\
AGE:.metadata.creationTimestamp

# Check PodDisruptionBudget
kubectl get pdb -A

# Solution: Adjust PDB or check budgets settings
```

### 問題 4: Spot Interrupt 後の Pod Rescheduling 遅延

```bash
# Check Spot interrupt events
kubectl get events --sort-by='.lastTimestamp' | grep -i "spot\|interrupt"

# Solutions for fast re-provisioning:
# 1. Allow diverse instance types
# 2. Reduce consolidateAfter time
# 3. Use mixed Spot and On-Demand
```

---

## セキュリティのベストプラクティス

```yaml
# security-best-practices.yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: secure-nodeclass
spec:
  amiFamily: Bottlerocket  # Security-hardened OS

  # IMDSv2 required
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 1  # Block Pod IMDS access
    httpTokens: required

  # EBS encryption
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 100Gi
        volumeType: gp3
        encrypted: true
        kmsKeyId: arn:aws:kms:ap-northeast-2:123456789:key/xxx

  # Use only private subnets
  subnetSelectorTerms:
    - tags:
        kubernetes.io/role/internal-elb: "1"

  # Restrictive security groups
  securityGroupSelectorTerms:
    - tags:
        Type: worker-restricted
---
# Apply Pod Security Standards
apiVersion: v1
kind: Namespace
metadata:
  name: secure-namespace
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/warn: restricted
```

---

## Day-2 Operations チェックリスト

### 日次タスク

| タスク | コマンド/アクション | 目的 |
|------|----------------|---------|
| Pending Pod の確認 | `kubectl get pods -A --field-selector=status.phase=Pending` | スケジューリングの問題を特定 |
| Node ヘルスの確認 | `kubectl get nodes` | NotReady Node を検出 |
| Node Capacity の確認 | `kubectl top nodes` | リソース圧迫を監視 |
| Event の確認 | `kubectl get events --sort-by='.lastTimestamp'` | 警告/エラーを検出 |

### 週次タスク

| タスク | コマンド/アクション | 目的 |
|------|----------------|---------|
| Node age の確認 | `kubectl get nodes --sort-by='.metadata.creationTimestamp'` | Node の鮮度を追跡 |
| NodePool limits の監査 | `kubectl get nodepools -o yaml` | 適切な limits を確認 |
| Consolidation の確認 | CloudWatch メトリクスを確認 | コスト最適化を検証 |
| Spot 使用状況の確認 | Capacity type の分布を確認 | コスト/可用性を最適化 |

### 月次タスク

| タスク | コマンド/アクション | 目的 |
|------|----------------|---------|
| AMI バージョンの確認 | Node AMI ID を確認 | セキュリティパッチ適用 |
| Security group の監査 | NodeClass 設定を確認 | セキュリティコンプライアンス |
| コスト分析 | AWS Cost Explorer | Budget 追跡 |
| Capacity Planning | 使用傾向を確認 | 適切にスケール |

---

## 運用自動化

### 自動ローテーションアラート

```yaml
# CloudWatch Alarm for old nodes
# Create alarm when nodes exceed age threshold
```

```bash
# Script to check node ages
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.creationTimestamp}{"\n"}{end}' | \
while read name created; do
  age_days=$(( ($(date +%s) - $(date -d "$created" +%s)) / 86400 ))
  if [ $age_days -gt 7 ]; then
    echo "WARNING: Node $name is $age_days days old"
  fi
done
```

### PDB コンプライアンスモニタリング

```bash
# Check PDB status across all namespaces
kubectl get pdb -A -o custom-columns=\
NAMESPACE:.metadata.namespace,\
NAME:.metadata.name,\
MIN-AVAILABLE:.spec.minAvailable,\
MAX-UNAVAILABLE:.spec.maxUnavailable,\
CURRENT:.status.currentHealthy,\
DESIRED:.status.desiredHealthy,\
DISRUPTIONS-ALLOWED:.status.disruptionsAllowed
```

### Capacity Dashboard クエリ

Capacity monitoring のための主要な Prometheus クエリ:

```promql
# Total nodes by NodePool
count(kube_node_labels) by (label_karpenter_sh_nodepool)

# Node CPU utilization by pool
avg(1 - rate(node_cpu_seconds_total{mode="idle"}[5m])) by (node) * on(node) group_left(label_karpenter_sh_nodepool) kube_node_labels

# Pending pods over time
sum(kube_pod_status_phase{phase="Pending"})

# Node age distribution
(time() - kube_node_created) / 86400
```

---

## 運用サマリーチェックリスト

| 領域 | チェックリスト項目 | ステータス |
|------|----------------|--------|
| **設定** | NodePool limits 設定済み | |
| | Disruption Budget 設定済み | |
| | NodeClass セキュリティ設定レビュー済み | |
| **モニタリング** | CloudWatch dashboard 作成済み | |
| | Alarm 設定済み（Pending Pod、provisioning failure） | |
| | コストモニタリング設定済み | |
| **可用性** | PodDisruptionBudget 設定済み | |
| | Multi-AZ 分散検証済み | |
| | Spot/On-Demand 混在比率レビュー済み | |
| **コスト** | Spot instance 比率最適化済み | |
| | Consolidation policy レビュー済み | |
| | Resource requests/limits の適切性レビュー済み | |

---

< [前へ: Spot 戦略](./04-spot-strategies.md) | [目次](./README.md) | [次へ: コスト管理](./06-cost-management.md) >
