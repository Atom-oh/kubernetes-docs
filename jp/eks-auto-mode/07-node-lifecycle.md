# Node ライフサイクル管理

> **サポートされるバージョン**: EKS 1.29+, EKS Auto Mode GA
> **最終更新**: July 3, 2026

このガイドでは、expiration policy、AMI 管理、drift detection、Node freshness monitoring を含む、EKS Auto Mode における Node ライフサイクル管理について説明します。

---

## Node Expiration Policies (expireAfter)

`expireAfter` フィールドは、Node が自動的に置き換えられるまで実行できる期間を制御します。

### expireAfter の仕組み

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: with-expiration
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      # Set maximum node lifetime
      expireAfter: 168h  # Auto-replace after 7 days
```

### Expiration プロセス

1. Node が `expireAfter` の age に達する
2. Controller が Node を置き換え対象としてマークする
3. 新しい Node が最新の設定でプロビジョニングされる
4. PDBs を尊重しながら workload が移行される
5. 古い Node が drain され、terminate される

### Auto Mode の 21 日間の最大 Node Lifetime

EKS Auto Mode は Karpenter ベースの `expireAfter` default を使用し、Node は作成後の最大 age である **21 days (504h)** に達すると自動的に置き換えられます。より頻繁に置き換えるために `expireAfter` を 21 日未満に設定できますが、21 日より長く設定しても効果はありません — Auto Mode は 21 日をハードな上限として強制します。managed node group や self-managed Karpenter とは異なり、Node を無期限に保持することはできません。

長期間 state を保持する workload（cache warm-up に時間がかかる service、local storage に依存する stateful workload など）を実行する場合は、この 21 日の上限を前提として、Pod の rescheduling と data rebalancing 手順を事前に計画してください。

### 推奨される expireAfter 値

| ユースケース | expireAfter | 根拠 |
|----------|-------------|-----------|
| **Security-critical** | 24h - 72h | 頻繁な patching、compliance requirements |
| **Standard production** | 168h (7 days) | freshness と stability のバランス |
| **Cost-sensitive** | 336h (14 days) | replacement overhead を最小化（21 日の上限内） |
| **Development/Test** | 504h (21 days, maximum) | Node reuse を最大化。この値が強制される上限 |
| **Compliance (PCI/HIPAA)** | 72h - 168h | audit requirements を満たす |

### expireAfter 設定例

```yaml
# Security-first configuration
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: security-critical
spec:
  template:
    spec:
      expireAfter: 72h  # 3 days for security compliance
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: secure-nodeclass
---
# Cost-optimized configuration
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-optimized
spec:
  template:
    spec:
      expireAfter: 336h  # 14 days for cost efficiency
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
```

---

## AMI 管理戦略

### Auto Mode が AMI を選択する仕組み

EKS Auto Mode は、NodeClass 設定に基づいて AMI を自動的に選択し、管理します。

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: ami-managed
spec:
  # AMI family selection
  amiFamily: AL2023  # or Bottlerocket
```

### AMI Family 比較

| 機能 | AL2023 | Bottlerocket |
|---------|--------|--------------|
| Base OS | Amazon Linux 2023 | container 専用に構築された OS |
| Boot time | ~40-60 seconds | ~20-40 seconds |
| Attack surface | Standard | Minimal (read-only root) |
| Customization | Full (userData) | Limited (settings API) |
| Package manager | dnf | なし（immutable） |
| Security updates | Standard patching | Atomic updates |
| Use case | 一般的な workload | security-focused workload |

### AMI Family 選択ガイドライン

| Workload Type | Recommended AMI | Rationale |
|---------------|-----------------|-----------|
| General web services | AL2023 | 柔軟性、なじみのある tooling |
| Security-critical | Bottlerocket | 最小限の attack surface |
| Compliance (PCI/SOC2) | Bottlerocket | immutable infrastructure |
| GPU workloads | AL2023 | NVIDIA driver support |
| Custom kernel modules | AL2023 | OS への完全な access |
| Fast scaling | Bottlerocket | より高速な boot times |

### Custom AMI 設定

```yaml
# For specific AMI requirements
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: custom-ami
spec:
  amiFamily: AL2023

  # AMI selection by tags (if using custom AMIs)
  amiSelectorTerms:
    - tags:
        Name: my-custom-eks-ami
        Environment: production
```

---

## AMI 更新と Drift Detection

### AMI 更新が Drift をトリガーする仕組み

AWS が新しい AMI をリリースした場合、または NodeClass を更新した場合:

1. **AMI Release**: AWS が新しい EKS-optimized AMI を公開する
2. **Drift Detection**: Controller が AMI version mismatch を検出する
3. **Node Marking**: 既存の Node が "drifted" としてマークされる
4. **Replacement**: disruption settings に基づいて Node が置き換えられる

### Drift Detection トリガー

| 変更 | Drift をトリガー | Replacement Speed |
|--------|----------------|-------------------|
| New AMI version | Yes | disruption budget に基づく |
| NodeClass AMI family change | Yes | immediate scheduling |
| Security patch AMI | Yes | disruption budget に基づく |
| NodePool requirement change | Yes | consolidation に基づく |
| NodeClass block device change | Yes | 新しい Node のみ |

### Drift Status の監視

```bash
# Check for drifted nodes
kubectl get nodes -o custom-columns=\
NAME:.metadata.name,\
NODEPOOL:.metadata.labels.karpenter\\.sh/nodepool,\
AGE:.metadata.creationTimestamp,\
DRIFT:.metadata.annotations.karpenter\\.sh/drift-hash

# Check NodeClaim drift status
kubectl get nodeclaims -o wide

# Watch for drift events
kubectl get events --sort-by='.lastTimestamp' | grep -i drift
```

### Drift Replacement の制御

```yaml
# Slow drift replacement for stability
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: controlled-drift
spec:
  template:
    spec:
      expireAfter: 168h
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
    budgets:
      # Slow, controlled replacement
      - nodes: "1"
      # No replacement during business hours
      - nodes: "0"
        schedule: "0 9-17 * * mon-fri"
        duration: 8h
```

---

## Node Freshness Policies と Security Patching

### Node Freshness が重要な理由

| 懸念 | 影響 | Mitigation |
|---------|--------|------------|
| **Security patches** | patch されていない vulnerabilities | 短い expireAfter |
| **AMI updates** | 不足している features/fixes | drift replacement を有効化 |
| **Configuration drift** | 一貫性のない behavior | 定期的な Node rotation |
| **Compliance** | audit findings | 文書化された rotation policy |

### Security Patching 戦略

```yaml
# Security-focused NodePool
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: security-patched
spec:
  template:
    spec:
      # Maximum node age for security compliance
      expireAfter: 72h  # 3 days
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: secure-nodeclass
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
      # Allow faster replacement for security patches
      - nodes: "20%"
---
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: secure-nodeclass
spec:
  amiFamily: Bottlerocket  # Security-hardened OS

  metadataOptions:
    httpTokens: required  # IMDSv2 only
    httpPutResponseHopLimit: 1

  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        encrypted: true
        volumeType: gp3
```

---

## Consolidation と Expiration のトレードオフ

### それぞれが適用されるタイミング

| Mechanism | Trigger | Purpose | Priority |
|-----------|---------|---------|----------|
| **Consolidation** | Underutilization | cost optimization | 低い |
| **Expiration** | Age threshold | security/freshness | 高い |
| **Drift** | Configuration change | consistency | 最高 |

### Mechanism 間の相互作用

```
Node Lifecycle Priority:
1. Drift (immediate) - Configuration mismatch
2. Expiration (scheduled) - Age threshold reached
3. Consolidation (opportunistic) - Underutilization detected
```

### 優先度ごとの設定

```yaml
# Cost-priority (consolidation aggressive, expiration relaxed)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-priority
spec:
  template:
    spec:
      expireAfter: 336h  # 14 days - relaxed
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m  # Aggressive consolidation
---
# Security-priority (expiration aggressive, consolidation relaxed)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: security-priority
spec:
  template:
    spec:
      expireAfter: 72h  # 3 days - aggressive
  disruption:
    consolidationPolicy: WhenEmpty  # Relaxed consolidation
    consolidateAfter: 10m
```

---

## Node Age Distribution の監視

### kubectl ベースの監視

```bash
# List nodes with age
kubectl get nodes --sort-by='.metadata.creationTimestamp' \
  -o custom-columns=\
NAME:.metadata.name,\
NODEPOOL:.metadata.labels.karpenter\\.sh/nodepool,\
INSTANCE:.metadata.labels.node\\.kubernetes\\.io/instance-type,\
CREATED:.metadata.creationTimestamp,\
AGE:.metadata.creationTimestamp

# Calculate node ages in days
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.creationTimestamp}{"\n"}{end}' | \
while read name created; do
  age_seconds=$(($(date +%s) - $(date -d "$created" +%s)))
  age_days=$((age_seconds / 86400))
  age_hours=$(((age_seconds % 86400) / 3600))
  echo "$name: ${age_days}d ${age_hours}h"
done
```

### Prometheus/Grafana 監視

Node age に関する主要な Prometheus queries:

```promql
# Node age in days
(time() - kube_node_created) / 86400

# Nodes older than 7 days
count(((time() - kube_node_created) / 86400) > 7)

# Average node age by NodePool
avg((time() - kube_node_created) / 86400) by (label_karpenter_sh_nodepool)

# Node age distribution histogram
histogram_quantile(0.50,
  sum(rate(kube_node_created_bucket[24h])) by (le)
)
```

### Alerting Rules

```yaml
# Prometheus alerting rules for node age
groups:
  - name: node-lifecycle
    rules:
      - alert: NodeTooOld
        expr: (time() - kube_node_created) / 86400 > 10
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Node {{ $labels.node }} is older than 10 days"

      - alert: NodeAgeDistributionSkewed
        expr: stddev((time() - kube_node_created) / 86400) > 3
        for: 4h
        labels:
          severity: info
        annotations:
          summary: "Node ages are highly variable, check rotation"
```

### Node Age Dashboard

次の内容を含む Grafana dashboard を作成します:

| Panel | Query | Visualization |
|-------|-------|---------------|
| Node count by age bucket | Node age の histogram | Bar chart |
| Average age by NodePool | `avg by (nodepool)` | Stat panel |
| Oldest nodes | age による Top N | Table |
| Nodes expiring soon | expireAfter に近い age | Alert list |
| Replacement rate | 作成/終了された NodeClaims | Time series |

---

## Node Lifecycle Best Practices

| Practice | Recommendation |
|----------|----------------|
| Set expireAfter | 常に設定、default は 7 日 |
| Use Bottlerocket for security | 最小限の attack surface |
| Monitor node ages | expected age を超えた Node に alert |
| Respect PDBs | graceful workload migration を確保 |
| Stagger replacements | disruption budgets を使用 |
| Track AMI versions | security patches を監視 |

---

< [前へ: Cost Management](./06-cost-management.md) | [目次](./README.md) | [次へ: Workload Optimization](./08-workload-optimization.md) >
