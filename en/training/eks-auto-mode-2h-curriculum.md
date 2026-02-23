# EKS Auto Mode Operator Training Curriculum (2 Hours)

> **Audience**: Infrastructure/Platform Engineers operating EKS clusters
> **Prerequisites**: Kubernetes fundamentals, EKS operational experience
> **Last Updated**: February 23, 2026

---

## Learning Objectives

1. Understand the Karpenter-based internal architecture of EKS Auto Mode
2. Design NodePool/NodeClass configurations for workload-specific resource optimization
3. Achieve 60~90% cost savings through Spot + Graviton combinations
4. Monitor operations using the Observability stack (Prometheus/Loki/Tempo/Grafana)

---

## Coverage Analysis — Existing Guide Assessment

Assessment of existing kubernetes-docs guide coverage against operator-requested training topics.

| Topic | Coverage | Assessment | Reference Docs |
|-------|----------|------------|----------------|
| Terraform / Terragrunt | Terraform sufficient, Terragrunt lacking | Detailed Terraform 3-Layer architecture docs available. Terragrunt mentioned only 5 times briefly | [ops/01-infrastructure-setup.md](../ops/01-infrastructure-setup.md) |
| ArgoCD | Excellent | 9-file multi-file structure (installation through best practices) | [gitops/argocd/](../gitops/argocd/README.md) |
| EKS Auto Mode Internals | Sufficient | Karpenter-based architecture, NodePool, NodeClass in detail | [eks-auto-mode/](../eks-auto-mode/README.md) (10 docs) |
| EKS Auto Mode Resource Optimization | Sufficient | Cost management, Spot strategies, VPA, bin-packing | [eks-auto-mode/06-cost-management.md](../eks-auto-mode/06-cost-management.md) |
| Grafana Loki | Sufficient | ~1,344-line detailed doc (architecture, LogQL, performance tuning) | [observability/logging/01-loki.md](../observability/logging/01-loki.md) |
| Prometheus / Grafana | Sufficient | Prometheus ~1,446 lines, Grafana ~1,026 lines | [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md), [observability/grafana/README.md](../observability/grafana/README.md) |
| Amazon Managed Prometheus | Adequate | Remote Write + AMP integration section within Prometheus doc | [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) |
| Grafana Tempo | Sufficient | ~1,051-line detailed doc (TraceQL, S3 backend, correlation) | [observability/tracing/01-tempo.md](../observability/tracing/01-tempo.md) |
| Node Availability/Termination Monitoring | Partial | Scattered across multiple docs, no unified troubleshooting guide | [eks-auto-mode/05-operations.md](../eks-auto-mode/05-operations.md) |
| Logs/Metrics/Traces Data Correlation | Sufficient | 3 Pillars correlation, Exemplars, TraceID linking | [observability/09-observability-optimization.md](../observability/09-observability-optimization.md) |

### Gap Summary

| Gap | Impact | Mitigation |
|-----|--------|------------|
| No dedicated Terragrunt guide | Medium | Consider creating a separate document if the ops team uses Terragrunt |
| No unified node termination monitoring guide | Medium | Prepare slides covering Spot interruption detection → CloudWatch → Prometheus Alert → Grafana flow |
| No eks-auto-mode hands-on labs | Low | Consider adding lab scenarios: NodePool changes → Consolidation observation |

---

## Overall Structure (120 min)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Part 1: Understanding Auto Mode Internals                 (40min) │
├─────────────────────────────────────────────────────────────────────┤
│  Part 2: Resource Optimization Strategies                  (35min) │
├─────────────────────────────────────────────────────────────────────┤
│  Break                                                     (10min) │
├─────────────────────────────────────────────────────────────────────┤
│  Part 3: Operational Monitoring — Observability Stack      (25min) │
├─────────────────────────────────────────────────────────────────────┤
│  Part 4: IaC + GitOps Operational Workflow                 (10min) │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Part 1: Understanding Auto Mode Internals (40 min)

**Learning Objective**: Understand how Karpenter-based Auto Mode provisions and manages nodes internally.

### 1-1. Architecture Overview (10 min)

**Reference Docs**: [eks-auto-mode/README.md](../eks-auto-mode/README.md), [01-getting-started.md](../eks-auto-mode/01-getting-started.md)

**Key Content**:

- **Karpenter embedded in the EKS control plane** — no separate installation/management required
- Architecture comparison with existing management approaches (MNG, Self-managed)

```
EKS Control Plane (AWS-managed)
├── API Server
├── etcd
├── Controller Manager
└── Karpenter Controller  ← Auto Mode core

NodePool Resources
├── general-purpose (built-in)
├── system (built-in)
└── custom-pool (user-defined)

EC2 Instances (auto-managed)
├── m6i.2xl (On-Demand)
├── c7g.xl (Spot)
└── r6i.4xl (On-Demand)
```

**Key Takeaways**:
- Auto Mode = "Karpenter as a Service" — operators only manage NodePool CRDs
- Two default NodePools (general-purpose, system) are automatically created
- Can be enabled via eksctl, Terraform, or AWS CDK

---

### 1-2. NodePool & NodeClass Deep Dive (15 min)

**Reference Doc**: [02-nodepool-configuration.md](../eks-auto-mode/02-nodepool-configuration.md)

**Key Content**:

- Understanding **default NodePool** configurations (general-purpose, system)
- **Custom NodePool design** strategies
- AMI family selection: AL2023 vs Bottlerocket
- Controlling instance types with `requirements` syntax

**Example** — Custom NodePool definition:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: web-tier
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c"]           # General purpose / Compute optimized
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["5"]                # Generation 6+ only
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
```

**Key Takeaways**:
- The `requirements` syntax is the core of instance selection — `In`, `NotIn`, `Gt`, `Lt` operators
- NodeClass is AWS-managed in Auto Mode (`eks.amazonaws.com` group)
- Separating NodePools by workload characteristics is the first step to optimization

---

### 1-3. Scaling Behavior (15 min)

**Reference Doc**: [03-scaling-behavior.md](../eks-auto-mode/03-scaling-behavior.md)

**Key Content**:

- **Pod→Node provisioning flow**: Pending detection → NodePool evaluation → instance selection → provisioning (40~90 seconds)
- **Consolidation policies**: the core mechanism for cost optimization
- **Drift detection**: automatic node replacement when configurations change

**Consolidation Policy Comparison**:

| Policy | Behavior | Best For |
|--------|----------|----------|
| `WhenEmpty` | Removes only empty nodes | Stability-first (production) |
| `WhenEmptyOrUnderutilized` | Removes empty + consolidates underutilized nodes | Cost-first (dev/staging) |

**Key Takeaways**:
- Consolidation automatically performs bin-packing → no manual optimization needed
- Tune sensitivity with `consolidateAfter` (1m = aggressive, 30m = conservative)
- Drift detection automates gradual rolling replacement when NodePool changes

---

## Part 2: Resource Optimization Strategies (35 min)

**Learning Objective**: Acquire cost reduction and resource efficiency strategies applicable to production immediately.

### 2-1. Spot Instance Strategies (10 min)

**Reference Doc**: [04-spot-strategies.md](../eks-auto-mode/04-spot-strategies.md)

**Key Content**:

- **Diversification strategy**: specify broad instance families/generations/sizes to secure Spot availability
- **Interruption handling**: Karpenter automatically provisions replacement nodes
- **On-Demand mixing**: critical workloads on On-Demand, non-critical on Spot

```yaml
# Spot-only NodePool example
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r"]      # Diverse families
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["5"]                # Multiple generations
```

**Key Takeaways**:
- Spot saves **60~90%** compared to On-Demand
- Diversification is key — relying on specific instance types causes availability issues
- Use `do-not-disrupt` annotation to protect specific Pods

---

### 2-2. Cost Management (10 min)

**Reference Doc**: [06-cost-management.md](../eks-auto-mode/06-cost-management.md)

**Key Content**:

- **Graviton/ARM**: **~20% cost savings** at equivalent performance
- **Savings Plans**: integrate Compute Savings Plans with Auto Mode
- **Cost attribution**: Kubecost + tag-based team cost allocation
- **Optimization checklist**: immediately actionable items

**Cumulative Cost Savings**:

```
Baseline (On-Demand x86)               : $1,000/mo
├── Spot applied (60% savings)          : $400/mo
├── Graviton migration (20% additional) : $320/mo
└── Consolidation optimization (15%)    : $272/mo
                                          ─────────
                                          ~73% savings
```

**Key Takeaways**:
- Graviton instances are specified with `kubernetes.io/arch: arm64` requirement
- Optimization is impossible without cost monitoring — Kubecost or AWS Cost Explorer is essential
- Savings Plans must be purchased per Compute unit (not instance type) for Auto Mode compatibility

---

### 2-3. Workload-Specific Optimization (10 min)

**Reference Doc**: [08-workload-optimization.md](../eks-auto-mode/08-workload-optimization.md)

**Key Content**:

- **Web services**: HPA + Spot mix, AZ spread
- **Batch processing**: Spot-only NodePool, prefer large instances
- **GPU/AI/ML**: dedicated NodePool, fixed instance types (p/g families)
- **VPA integration**: automatic Right-sizing of resource requests

**NodePool Separation by Workload Tier**:

| Workload | NodePool | Capacity Type | Instance Categories |
|----------|----------|---------------|---------------------|
| System (CoreDNS, etc.) | system | On-Demand | m, c |
| Web services | web-tier | On-Demand + Spot | m, c, r |
| Batch processing | batch | Spot only | m, c, r (large sizes) |
| GPU workloads | gpu | On-Demand | p, g |

**Key Takeaways**:
- Separating NodePools by workload tier is the fundamental optimization pattern
- Map Pods to NodePools via `nodeSelector` or `nodeAffinity`
- For production, use VPA with `updateMode: Off` to review recommendations before manual application

---

### 2-4. Node Lifecycle (5 min)

**Reference Doc**: [07-node-lifecycle.md](../eks-auto-mode/07-node-lifecycle.md)

**Key Content**:

- `expireAfter` policy to limit maximum node lifetime
- Automated AMI updates — Drift detection automatically applies new AMIs
- Disruption Budget to limit concurrent node replacements

**Key Takeaways**:
- `expireAfter: 720h` (30 days) is a typical production setting
- Disruption Budget: `nodes: "10%"` → only 10% of nodes can be disrupted simultaneously
- Maintenance window settings allow node replacement only outside business hours

---

## Break (10 min)

---

## Part 3: Operational Monitoring — Observability Stack (25 min)

**Learning Objective**: Learn node availability monitoring and Logs/Metrics/Traces correlation methods in Auto Mode environments.

### 3-1. Node Monitoring (8 min)

**Reference Docs**: [eks-auto-mode/05-operations.md](../eks-auto-mode/05-operations.md), [observability/09-observability-optimization.md](../observability/09-observability-optimization.md)

**Key Content**:

- Checking Auto Mode node status (`kubectl get nodeclaims`)
- Spot interruption detection: CloudWatch Events → EventBridge → SNS/Lambda
- Prometheus alerting rules:

```yaml
# Core node alerting rules
groups:
  - name: node-health
    rules:
      - alert: NodeNotReady
        expr: kube_node_status_condition{condition="Ready",status="true"} == 0
        for: 5m
      - alert: NodeMemoryPressure
        expr: kube_node_status_condition{condition="MemoryPressure",status="true"} == 1
        for: 2m
      - alert: NodePoolNearCapacity
        expr: |
          count(karpenter_nodeclaims_state{state="launched"})
          / karpenter_nodepool_usage_limit > 0.8
        for: 10m
```

**Key Takeaways**:
- In Auto Mode, **node SSH access is unavailable** → high dependency on the Observability stack
- Monitor NodePool status, provisioning latency, and Consolidation activity via `karpenter_*` metrics
- Disruption Budget settings serve as a safety net during Spot interruptions

---

### 3-2. Three Pillars Correlation (8 min)

**Reference Docs**: [observability/09-observability-optimization.md](../observability/09-observability-optimization.md), [observability/grafana/README.md](../observability/grafana/README.md)

**Key Content**:

- **TraceID-based Logs↔Traces linking**: query Tempo traces from Loki using TraceID
- **Exemplars for Metrics→Traces**: jump directly from Prometheus metrics to related traces
- **Grafana unified dashboard**: connect all three data sources in a single dashboard

```
Incident Analysis Flow:

  Metrics (alert triggers)
      │
      ▼
  Logs (root cause identification)
      │
      ▼
  Traces (impact scope assessment)
```

**Grafana Data Source Linking Configuration**:

```yaml
# Grafana datasource configuration (key settings)
datasources:
  - name: Tempo
    type: tempo
    jsonData:
      tracesToLogs:
        datasourceUid: loki
        tags: ['service.name']
      tracesToMetrics:
        datasourceUid: prometheus
```

**Key Takeaways**:
- `tracesToLogs` and `tracesToMetrics` settings are the core of cross-datasource linking
- Loki labels must include `traceID` to enable reverse lookup (Logs→Traces)
- Enable Exemplars: Prometheus `--enable-feature=exemplar-storage`

---

### 3-3. Real-World Troubleshooting Scenarios (9 min)

**Reference Doc**: [eks-auto-mode/05-operations.md](../eks-auto-mode/05-operations.md) (troubleshooting section)

#### Scenario 1: "Pod is Pending but no node is being created"

```
Investigation order:
1. kubectl get nodeclaims → Check NodeClaim status
2. kubectl describe nodepool → Check NodePool limits
3. Karpenter metrics → karpenter_provisioner_scheduling_duration
4. CloudTrail → Check for EC2 RunInstances call failures
5. Common causes: insufficient instance capacity or subnet IP exhaustion
```

#### Scenario 2: "A node suddenly disappeared"

```
Investigation order:
1. kubectl get events → NodeClaim deletion events
2. Karpenter logs → Determine if cause was Consolidation/Drift/Expiry
3. CloudWatch Events → Check for Spot interruption notices
4. Grafana dashboard → Node count change graph at the relevant time
5. Common causes: Consolidation, Spot interruption, or expireAfter expiry
```

#### Scenario 3: "Response latency is increasing"

```
Investigation order:
1. Prometheus → Check RED metrics (Rate, Errors, Duration)
2. Grafana dashboard → p99 latency graph for the service
3. Tempo → Query slow traces (duration > 1s)
4. Loki → Query related logs using the TraceID
5. Node metrics → Check for CPU/Memory pressure
```

**Key Takeaways**:
- The **starting point differs by problem type**: infrastructure issues start with Metrics, application issues start with Traces
- `kubectl get nodeclaims` is the first debugging tool in Auto Mode environments
- CloudTrail logs provide the definitive answer to "why a node wasn't created"

---

## Part 4: IaC + GitOps Operational Workflow (10 min)

**Learning Objective**: Understand infrastructure management and deployment pipeline operations for Auto Mode clusters.

### 4-1. Terraform 3-Layer Architecture (5 min)

**Reference Doc**: [ops/01-infrastructure-setup.md](../ops/01-infrastructure-setup.md)

**Key Content**:

```
Terraform 3-Layer Structure:

Layer 0: 00-shared     → Common settings (backend.tf, variables.tf)
Layer 1: 01-network    → VPC, Subnets, NAT Gateway
Layer 2: 02-cluster    → EKS Auto Mode Cluster + NodePool
Layer 3: 03-platform   → Add-ons, Pod Identity, IRSA
```

**Key Takeaways**:
- Layer separation → minimize blast radius (network changes don't affect the cluster)
- Auto Mode activation is configured in the `02-cluster` layer via the `compute_config` block
- Independent `terraform apply` per layer → parallel work across teams

---

### 4-2. ArgoCD Operations (5 min)

**Reference Docs**: [gitops/argocd/02-applications.md](../gitops/argocd/02-applications.md), [gitops/argocd/04-applicationsets.md](../gitops/argocd/04-applicationsets.md)

**Key Content**:

- **App of Apps pattern**: a single root Application manages child Applications
- **ApplicationSet**: automated multi-cluster deployment using Generators
- **Sync Strategy**: Auto Sync + Self-Heal + Prune for GitOps automation

**Key Takeaways**:
- NodePool definitions can be managed in Git → auto-deployed via ArgoCD
- ApplicationSet's `Git Generator` creates Applications automatically based on directory structure
- Progressive Sync enables staged rollouts across clusters

---

## Post-Lecture Assessment

Quizzes are available for each part:

| Part | Quiz File |
|------|-----------|
| Part 1-1 | [quizzes/eks-auto-mode/01-getting-started-quiz.md](../quizzes/eks-auto-mode/01-getting-started-quiz.md) |
| Part 1-2 | [quizzes/eks-auto-mode/02-nodepool-configuration-quiz.md](../quizzes/eks-auto-mode/02-nodepool-configuration-quiz.md) |
| Part 1-3 | [quizzes/eks-auto-mode/03-scaling-behavior-quiz.md](../quizzes/eks-auto-mode/03-scaling-behavior-quiz.md) |
| Part 2-1 | [quizzes/eks-auto-mode/04-spot-strategies-quiz.md](../quizzes/eks-auto-mode/04-spot-strategies-quiz.md) |
| Part 2-2 | [quizzes/eks-auto-mode/06-cost-management-quiz.md](../quizzes/eks-auto-mode/06-cost-management-quiz.md) |
| Part 2-3 | [quizzes/eks-auto-mode/08-workload-optimization-quiz.md](../quizzes/eks-auto-mode/08-workload-optimization-quiz.md) |
| Part 2-4 | [quizzes/eks-auto-mode/07-node-lifecycle-quiz.md](../quizzes/eks-auto-mode/07-node-lifecycle-quiz.md) |
| Part 3 | [quizzes/eks-auto-mode/05-operations-quiz.md](../quizzes/eks-auto-mode/05-operations-quiz.md) |

---

## Preparation Recommendations

### Must-Have (Before the Lecture)

1. **Auto Mode Node Monitoring Integration Slide** — Prepare a single-flow diagram covering Spot Termination detection → CloudWatch Event → Prometheus Alert → Grafana Dashboard
   - Source: [eks-auto-mode/05-operations.md](../eks-auto-mode/05-operations.md) monitoring section
   - Source: [observability/09-observability-optimization.md](../observability/09-observability-optimization.md)

### Nice-to-Have

2. **Dedicated Terragrunt Guide** — Consider creating a separate document if the ops team uses Terragrunt (currently only 5 brief mentions)
3. **Hands-on Labs** — No hands-on labs exist for `eks-auto-mode/`:
   - NodePool changes → observe Consolidation behavior
   - Spot interruption simulation (using `aws fis`)
   - Karpenter metrics dashboard setup

---

## Additional Learning Resources

Advanced topics not covered in this curriculum:

| Topic | Reference Doc |
|-------|---------------|
| Migration from MNG to Auto Mode | [eks-auto-mode/09-migration-guide.md](../eks-auto-mode/09-migration-guide.md) |
| FluxCD Comparison | [gitops/02-fluxcd.md](../gitops/02-fluxcd.md) |
| Prometheus Operator (ServiceMonitor/PodMonitor) | [observability/metrics/01-prometheus.md](../observability/metrics/01-prometheus.md) |
| Loki LogQL Advanced | [observability/logging/01-loki.md](../observability/logging/01-loki.md) |
| Tempo TraceQL Advanced | [observability/tracing/01-tempo.md](../observability/tracing/01-tempo.md) |
| Alertmanager Configuration | [observability/alerting/01-alertmanager.md](../observability/alerting/01-alertmanager.md) |

---

## Verification Checklist

- [x] `en/eks-auto-mode/` directory — 10 documents confirmed (9 + 09-migration-guide.md)
- [x] `en/observability/09-observability-optimization.md` — 3 Pillars correlation section confirmed
- [x] `en/ops/01-infrastructure-setup.md` — Terraform 3-Layer + Auto Mode setup confirmed
- [x] `en/quizzes/eks-auto-mode/` — 9 quiz files available for post-lecture assessment
- [x] `en/observability/grafana/README.md` — data source linking configuration confirmed
- [x] `en/gitops/argocd/` — 10 documents (README + 01~09) confirmed
